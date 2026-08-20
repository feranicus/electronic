"""White Label over the API: upload, isolation between partners, and the engine wiring.

Real requests through the ASGI app with a real signed session cookie, for the reason recorded in
test_admin_users.py: a grep proves a gate is WRITTEN, only a request proves it is REACHED.

No httpx and no starlette.testclient — the multipart body is assembled by hand here so this runs on
the operator's Windows Python, which has neither.
"""
import asyncio
import json as _json
import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "webapp", "backend"),
          os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from test_proteus import make_pptx, png                                  # noqa: E402

BOUNDARY = "----cybergodtestboundary"


@pytest.fixture()
def brands(tmp_path, monkeypatch):
    """Point the brand store at a scratch directory, never the real shared volume."""
    monkeypatch.setenv("BRAND_DIR", str(tmp_path / "brands"))
    import importlib
    from app import brand as B
    importlib.reload(B)
    yield B


def multipart(fields, files):
    """(body, content_type). files = [(field, filename, bytes)]."""
    out = b""
    for k, v in fields.items():
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                % (BOUNDARY, k, v)).encode()
    for field, filename, blob in files:
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                "Content-Type: application/octet-stream\r\n\r\n" % (BOUNDARY, field, filename)).encode()
        out += blob + b"\r\n"
    out += ("--%s--\r\n" % BOUNDARY).encode()
    return out, "multipart/form-data; boundary=" + BOUNDARY


def req(path, method="GET", email=None, body=b"", ctype="application/json"):
    from app import main
    from app.auth import make_session
    headers = [(b"host", b"testserver"), (b"content-type", ctype.encode()),
               (b"content-length", str(len(body)).encode())]
    if email:
        headers.append((b"cookie", ("colt_session=" + make_session(email)).encode()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
             "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": b"",
             "root_path": "", "headers": headers,
             "client": ("127.0.0.1", 1), "server": ("testserver", 80)}
    got = {"status": 0, "body": b"", "headers": {}}

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(msg):
        if msg.get("type") == "http.response.start":
            got["status"] = msg["status"]
            got["headers"] = {k.decode().lower(): v.decode() for k, v in msg.get("headers", [])}
        elif msg.get("type") == "http.response.body":
            got["body"] += msg.get("body") or b""

    asyncio.run(main.app(scope, receive, send))
    try:
        got["json"] = _json.loads(got["body"] or b"{}")
    except Exception:
        got["json"] = {}
    return got


ME = "feranicus@s4biz.io"
OTHER = "someone.else@s4biz.io"


def upload(email=ME, template=True, logo=None, name="Acme Security GmbH", panel="0"):
    files = []
    if template:
        files.append(("template", "acme.pptx", make_pptx()))
    if logo is not None:
        files.append(("logo", "logo.png", logo))
    b, ct = multipart({"name": name, "panel": panel}, files)
    return req("/api/brand", "POST", email=email, body=b, ctype=ct)


def finish(**kw):
    """Start an upload and wait for the job. The POST only registers the work now."""
    r = upload(**kw)
    assert r["status"] == 200, r["json"]
    return _drain(r["json"]["job"])


def test_a_brand_is_owner_scoped_end_to_end(brands):
    assert req("/api/brand")["status"] == 401, "anonymous callers get nothing"

    r = req("/api/brand", email=ME)
    assert r["status"] == 200 and r["json"]["active"] is False

    # The upload now returns a JOB and the theme arrives when it finishes — see the progress
    # section below for why. `finish()` starts one and waits for it.
    j = finish()
    pal = j["brand"]["palette"]
    assert pal["brandDark"] == "C8102E", "the partner's accent1 became their dark stop"
    assert j["brand"]["name"] == "Acme Security GmbH"

    r = req("/api/brand", email=ME)
    assert r["status"] == 200 and r["json"]["active"] is True

    # ISOLATION: a second partner sees nothing of the first. There is no identifier in any of these
    # routes for a caller to tamper with — the path is derived from the session.
    assert req("/api/brand", email=OTHER)["json"]["active"] is False
    assert req("/api/brand/logo", email=OTHER)["status"] == 404

    r = req("/api/brand", "DELETE", email=ME)
    assert r["status"] == 200 and r["json"]["existed"] is True
    assert req("/api/brand", email=ME)["json"]["active"] is False


def test_the_logo_round_trips_and_is_served_only_to_its_owner(brands):
    assert finish(logo=png(300, 80))["error"] == ""
    r = req("/api/brand/logo", email=ME)
    assert r["status"] == 200
    assert r["headers"].get("content-type", "").startswith("image/png")
    assert r["body"][:8] == b"\x89PNG\r\n\x1a\n"
    assert req("/api/brand/logo", email=OTHER)["status"] == 404


def test_an_svg_logo_is_refused_with_a_reason(brands):
    r = upload(logo=b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>')
    assert r["status"] == 400
    assert "SVG" in r["json"].get("detail", ""), r["json"]
    # ...and the refusal left NOTHING behind. A half-written brand renders broken decks for every
    # assessment that user starts afterwards.
    assert req("/api/brand", email=ME)["json"]["active"] is False


def test_a_file_that_is_not_a_presentation_is_refused(brands):
    b, ct = multipart({"name": "x", "panel": "0"},
                      [("template", "notes.txt", b"this is not a pptx")])
    r = req("/api/brand", "POST", email=ME, body=b, ctype=ct)
    assert r["status"] == 400
    assert req("/api/brand", email=ME)["json"]["active"] is False


def test_severity_colours_never_reach_the_stored_theme(brands):
    assert finish()["error"] == ""
    pal = req("/api/brand", email=ME)["json"]["brand"]["palette"]
    assert not (set(pal) & {"crit", "high", "med", "low"})


def test_the_engine_run_is_told_about_the_brand(brands):
    """THE WIRING. proteus can be perfect and brand.js can be perfect, and if _run_job does not put
    BRAND_THEME in the engine's environment the partner still gets our colours. A control that is
    correct and unreachable is not a control."""
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    src = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
    i = src.find("create_subprocess_exec")
    assert i > 0
    call = src[i:i + 600]
    assert "brand.env_for(email)" in call, (
        "the engine subprocess is not given the user's brand; every artifact would render unbranded")
    assert "COLT_USER" in call, "the requester stamp must survive alongside it"


def test_the_brand_theme_path_is_what_the_builders_read(brands):
    """The contract between the API and brand.js is one environment variable pointing at one file.
    If they ever disagree about its name, branding silently stops."""
    assert finish()["error"] == ""
    env = brands.env_for(ME)
    assert list(env) == ["BRAND_THEME"] and os.path.isfile(env["BRAND_THEME"])
    js = open(os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts", "brand.js"),
              encoding="utf-8").read()
    assert "process.env.BRAND_THEME" in js
    theme = _json.load(open(env["BRAND_THEME"], encoding="utf-8"))
    assert theme["owner"] == ME, "the stored theme records who it belongs to"


def test_uploading_a_new_template_replaces_the_old_logo(brands):
    """A stale mark from a previous upload sitting on a partner's new brand is the kind of defect
    nobody reports and everybody sees."""
    assert finish(logo=png(300, 80))["error"] == ""
    assert req("/api/brand/logo", email=ME)["status"] == 200
    # The replacement template has no logo on its master — only a 1200x800 photograph on slide 1.
    # A PHOTOGRAPH IS NOT A LOGO, and the first version of the heuristic adopted it: this test is
    # what caught that, and it would have put a stock image on every slide of every report.
    b, ct = multipart({"name": "Acme", "panel": "0"},
                      [("template", "a.pptx", make_pptx(with_logo=False))])
    r2 = req("/api/brand", "POST", email=ME, body=b, ctype=ct)
    assert r2["status"] == 200
    assert _drain(r2["json"]["job"])["error"] == ""
    assert req("/api/brand/logo", email=ME)["status"] == 404, (
        "the old logo survived a new upload, or a photograph was adopted as the mark")


# ---------------------------------------------------------------------------------------------
# PROGRESS. The first real use of this page sat on "Reading your template…" for ever, because the
# preview's read-only rail destroyed the POST, the fetch rejected, and nothing cleared the busy
# flag. The upload now returns a JOB and the page polls it, so a slow model is visible as a line
# that has not arrived rather than as a spinner that never stops.
# ---------------------------------------------------------------------------------------------
def _drain(job, tries=200):
    for _ in range(tries):
        s = req("/api/brand/job/" + job, email=ME)["json"]
        if s.get("done"):
            return s
        import time as _t
        _t.sleep(0.05)
    raise AssertionError("the job never reported done — this is the hang the feature exists to fix")


def test_the_upload_returns_a_job_and_reports_phases(brands):
    r = upload()
    assert r["status"] == 200 and r["json"].get("job"), r["json"]
    s = _drain(r["json"]["job"])
    assert s["error"] == "", s
    assert s["pct"] == 100 and s["done"] is True
    msgs = " | ".join(l["msg"] for l in s["lines"])
    assert "reading the file" in msgs
    assert "theme colours" in msgs, msgs
    assert "saved" in msgs, msgs
    assert s["brand"]["palette"]["brandDark"] == "C8102E"


def test_a_failure_inside_the_job_still_finishes_it(brands):
    """The cheap refusals are synchronous (see the SVG test above). This is the OTHER path: a
    failure discovered after the job has started must still reach done=100 — a job that never
    finishes is the original hang, and the page would spin for ever waiting for it."""
    import app.brand as B
    real = B.save
    B.save = lambda *a, **k: (_ for _ in ()).throw(ValueError("the disk went away"))
    try:
        r = upload()
        assert r["status"] == 200
        s = _drain(r["json"]["job"])
        assert s["done"] is True and s["pct"] == 100
        assert "disk went away" in s["error"]
        assert any("refused" in l["msg"] for l in s["lines"])
    finally:
        B.save = real


def test_a_job_is_owner_scoped(brands):
    """A job id is not an authorisation. Another partner must not be able to watch this upload."""
    r = upload()
    job = r["json"]["job"]
    _drain(job)
    assert req("/api/brand/job/" + job, email=OTHER)["status"] == 404
    assert req("/api/brand/job/" + job)["status"] == 401
    assert req("/api/brand/job/nosuchjob", email=ME)["status"] == 404


def test_since_returns_only_the_new_lines(brands):
    """The page polls once a second; re-sending the whole log every time would grow without bound."""
    s = _drain(upload()["json"]["job"])
    total = s["total"]
    assert total > 2
    later = req("/api/brand/job/x", email=ME)  # 404 path, just to be explicit it is not reused
    assert later["status"] == 404
