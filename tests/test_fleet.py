"""The fleet page must distinguish BLIND from QUIET, and the endpoint must be admin-only.

WHY THIS EXISTS. The operator asked why he receives nothing on Telegram from jev.best, jobhuntwow or
polara. Three facts, measured not assumed:
  * `perseus_client.py` was copied into jobhuntwow and jev.best and imported by NOTHING;
  * even wired, that client is enforcement-only -- no telemetry, no alerting;
  * every alert he gets comes from colt-web's notify.py, which those projects do not run.
So nothing was broken. Nothing was built. This module makes that state visible, and the test that
matters most is the one asserting SILENT is never rendered as healthy.
"""
import asyncio
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
sys.path.insert(0, ROOT)

from app import fleet  # noqa: E402


def _events(tmp, rows):
    p = os.path.join(tmp, "events.log")
    with open(p, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return p


def _setup(monkeypatch, tmp_path, rows, beats):
    ev = _events(str(tmp_path), rows)
    bd = os.path.join(str(tmp_path), "beats")
    os.makedirs(bd, exist_ok=True)
    for svc, doc in (beats or {}).items():
        with open(os.path.join(bd, "%s.json" % svc), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
    monkeypatch.setattr(fleet, "EVENTS", ev)
    monkeypatch.setattr(fleet, "BEAT_DIR", bd)
    monkeypatch.setattr(fleet, "BLOCKLIST", os.path.join(str(tmp_path), "nope.json"))


def test_a_project_with_no_logs_is_silent_not_quiet(monkeypatch, tmp_path):
    """THE ASSERTION THIS FILE EXISTS FOR. A project shipping no logs must never render as a
    healthy one with zero attacks -- that is the same defect as a backup reporting success while
    copying nothing."""
    now = int(time.time())
    _setup(monkeypatch, tmp_path,
           [{"ts": now - 60, "evt": "http", "service": "colt-web", "ip": "1.2.3.4", "path": "/"}],
           {})
    st = fleet.status()
    by = {p["service"]: p for p in st["projects"]}
    assert by["jev-web"]["state"] == "silent"
    assert "BLIND" in by["jev-web"]["why"]
    assert by["jev-web"]["attacks_24h"] == 0 and by["jev-web"]["requests_24h"] == 0
    assert st["blind"] >= 1
    assert "never that it is safe" in st["caveat"]


def test_logging_without_a_heartbeat_is_observed_and_unguarded(monkeypatch, tmp_path):
    """The state jobhuntwow and jev.best are actually in: we can see them, nothing is defending
    them. Collapsing this into 'OK' is what let it sit unnoticed."""
    now = int(time.time())
    _setup(monkeypatch, tmp_path,
           [{"ts": now - 30, "evt": "http", "service": "jhw-web", "ip": "9.9.9.9", "path": "/"}],
           {})
    by = {p["service"]: p for p in fleet.status()["projects"]}
    assert by["jhw-web"]["state"] == "observed"
    assert by["jhw-web"]["sidecar"] == "not installed"
    assert "UNGUARDED" in by["jhw-web"]["why"]


def test_a_fresh_heartbeat_makes_it_live(monkeypatch, tmp_path):
    now = int(time.time())
    _setup(monkeypatch, tmp_path,
           [{"ts": now - 30, "evt": "http", "service": "colt-web", "ip": "1.1.1.1", "path": "/"}],
           {"colt-web": {"service": "colt-web", "ts": now - 10, "cycle": 5, "checks": 42}})
    by = {p["service"]: p for p in fleet.status()["projects"]}
    assert by["colt-web"]["state"] == "live"
    assert by["colt-web"]["sidecar"] == "active"
    assert by["colt-web"]["sidecar_cycle"] == 5


def test_a_stale_heartbeat_is_not_active(monkeypatch, tmp_path):
    """A sidecar that stopped beating an hour ago is a dead sidecar. Reporting it as active because
    a file exists is the 'a control that is correct and unreachable is not a control' defect with a
    green light on top."""
    now = int(time.time())
    _setup(monkeypatch, tmp_path,
           [{"ts": now - 30, "evt": "http", "service": "colt-web", "ip": "1.1.1.1", "path": "/"}],
           {"colt-web": {"service": "colt-web", "ts": now - 4000, "cycle": 5}})
    by = {p["service"]: p for p in fleet.status()["projects"]}
    assert by["colt-web"]["sidecar"] == "stale"
    assert by["colt-web"]["state"] == "observed"


def test_the_project_list_is_committed_so_an_absence_can_be_noticed(monkeypatch, tmp_path):
    """A list built from whatever appears in the log could never report a project as missing -- it
    would simply stop mentioning it. Every committed project must appear in every response."""
    _setup(monkeypatch, tmp_path, [], {})
    got = {p["service"] for p in fleet.status()["projects"]}
    assert got == {p["service"] for p in fleet.PROJECTS}
    assert "jev-web" in got and "polara-web" in got


def test_attack_counting_uses_the_one_shield_implementation(monkeypatch, tmp_path):
    """probe_shape is the single detector. A second copy here would drift from the thing that
    actually blocks, which is how the coverage metric became circular once already."""
    now = int(time.time())
    _setup(monkeypatch, tmp_path, [
        {"ts": now - 10, "evt": "http", "service": "colt-web", "ip": "1.1.1.1", "path": "/.env"},
        {"ts": now - 10, "evt": "http", "service": "colt-web", "ip": "1.1.1.1", "path": "/app"},
    ], {})
    by = {p["service"]: p for p in fleet.status()["projects"]}
    assert by["colt-web"]["requests_24h"] == 2
    assert by["colt-web"]["attacks_24h"] == 1, "/.env is a probe, /app is not"


def test_an_unreadable_events_log_does_not_crash_the_page(monkeypatch, tmp_path):
    """A status page that 500s is a status page nobody can use during the incident it exists for."""
    monkeypatch.setattr(fleet, "EVENTS", os.path.join(str(tmp_path), "missing.log"))
    monkeypatch.setattr(fleet, "BEAT_DIR", os.path.join(str(tmp_path), "missing"))
    st = fleet.status()
    assert len(st["projects"]) == len(fleet.PROJECTS)
    # Not all "silent" any more: the two projects that keep their OWN event volume are `elsewhere`,
    # which is the honest label. What must hold is that NONE of them claims to be healthy.
    assert all(p["state"] in ("silent", "elsewhere") for p in st["projects"])
    assert not [p for p in st["projects"] if p["state"] in ("live", "observed")]


def test_the_endpoint_is_admin_only():
    """Hiding a tab is presentation. The route must depend on _require_admin, or anyone can issue
    the request the tab would have issued."""
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    i = src.index('@app.get("/api/admin/fleet")')
    body = src[i:i + 900]
    body = "\n".join(l for l in body.splitlines() if not l.strip().startswith("#"))
    assert "_require_admin(request)" in body


def test_the_fleet_watch_is_edge_triggered():
    """A project silent for a month must not page every hour. An alert that fires every time is how
    the one that matters gets read past -- already paid for with the roster warning and the 8/10
    bot-gate line."""
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    i = src.index("async def _fleet_loop()")
    body = src[i:src.index("_aio.create_task(_decisions_loop())")]
    code = "\n".join(l for l in body.splitlines() if not l.strip().startswith("#"))
    assert "was is not None and was != p[\"state\"]" in code, \
        "the alert must fire on a CHANGE of state, never on the state itself"
    assert "if changed:" in code
    assert "_aio.create_task(_fleet_loop())" in src, "and the loop must actually be started"


def test_the_client_heartbeat_is_rate_limited_and_fails_open():
    """The heartbeat is what makes 'is the sidecar connected' measurable. It must never become a
    disk write per request, and it must never raise into a request path."""
    src = open(os.path.join(ROOT, "perseus", "client.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    assert 'if now - _CACHE["beat"] < BEAT_S:' in code, "a heartbeat per request is a disk write per request"
    i = code.index("def _beat(")
    beat = code[i:code.index("def check(")]
    assert "except Exception:" in beat and "os.replace(" in beat, \
        "it must be atomic and must swallow every failure"
    assert "_beat(" in code[code.index("def check("):], "check() must actually leave a trace"


# ---------------------------------------------------------------------------------------------
# THE SIDECAR ITSELF: it must BLOCK, REPORT and BEAT, and it must be WIRED IN.
#
# The operator's complaint was not that the page was missing -- it was that jev.best, jobhuntwow
# and polara say nothing. The client could only ever block; it had no way to report, and it was
# imported by nothing. Both halves are asserted here, because behaviour without wiring is exactly
# the state that produced the silence.
# ---------------------------------------------------------------------------------------------
import importlib


def _client(tmp_path, monkeypatch, patterns=()):
    monkeypatch.setenv("EVENTS_LOG", str(tmp_path / "events.log"))
    monkeypatch.setenv("PERSEUS_BEATS", str(tmp_path / "beats"))
    monkeypatch.setenv("PERSEUS_BLOCKLIST", str(tmp_path / "bl.json"))
    monkeypatch.setenv("PERSEUS_RELOAD_S", "0")
    monkeypatch.setenv("SERVICE", "jhw-web")
    with open(str(tmp_path / "bl.json"), "w", encoding="utf-8") as fh:
        json.dump({"cycle": 9, "patterns": [{"id": "r1", "pattern": p} for p in patterns],
                   "thresholds": {}}, fh)
    sys.path.insert(0, os.path.join(ROOT, "perseus"))
    import client as C
    return importlib.reload(C)


async def _ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def _call(C, path, app=_ok_app, xff=b"5.6.7.8, 10.0.0.1"):
    out = []

    async def send(m):
        out.append(m)

    async def recv():
        return {"type": "http.request", "body": b""}

    scope = {"type": "http", "path": path, "method": "GET", "client": ("10.0.0.1", 1),
             "headers": [(b"x-forwarded-for", xff), (b"user-agent", b"curl/8")]}
    asyncio.run(C.Middleware(app)(scope, recv, send))
    return out[0]["status"]


def _lines(tmp_path):
    p = str(tmp_path / "events.log")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def test_the_sidecar_reports_every_request(tmp_path, monkeypatch):
    """The half that was missing entirely. Without this line nothing downstream can ever say who
    visited jev.best, which is the question that was asked."""
    C = _client(tmp_path, monkeypatch)
    assert _call(C, "/app") == 200
    rows = _lines(tmp_path)
    assert len(rows) == 1 and rows[0]["evt"] == "http" and rows[0]["service"] == "jhw-web"
    assert rows[0]["path"] == "/app" and rows[0]["status"] == 200


def test_the_sidecar_blocks_and_still_reports(tmp_path, monkeypatch):
    """A blocked request is the MOST interesting one. Reporting only what got through would hide
    exactly the traffic the operator wants to know about."""
    C = _client(tmp_path, monkeypatch, patterns=[r"/\.env$"])
    assert _call(C, "/.env") == 429
    rows = _lines(tmp_path)
    assert rows and rows[-1]["status"] == 429 and rows[-1]["path"] == "/.env"


def test_the_client_ip_is_the_first_forwarded_entry(tmp_path, monkeypatch):
    """Exactly one proxy sits in front of every site on this box. Taking the last entry would
    record the proxy and make every visitor look like 10.0.0.1."""
    C = _client(tmp_path, monkeypatch)
    _call(C, "/")
    assert _lines(tmp_path)[0]["ip"] == "5.6.7.8"


def test_an_app_that_raises_still_gets_reported(tmp_path, monkeypatch):
    """The request that crashed the app is evidence too. A `finally` is what keeps it."""
    C = _client(tmp_path, monkeypatch)

    async def boom(scope, receive, send):
        raise RuntimeError("kaboom")

    try:
        _call(C, "/crash", app=boom)
    except RuntimeError:
        pass
    assert any(r["path"] == "/crash" for r in _lines(tmp_path))


def test_the_sidecar_never_takes_the_site_down(tmp_path, monkeypatch):
    """An unwritable event log must not turn telemetry into an outage -- and it must SAY SO once,
    because jobhuntwow ran its whole life with that write silently failing."""
    C = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(C, "EVENTS", os.path.join(str(tmp_path), "nope", "deep", "x.log"))
    assert _call(C, "/still-serves") == 200


def test_ip_hashing_is_available_for_gdpr(tmp_path, monkeypatch):
    """An IP is personal data (CJEU C-582/14 Breyer). Hashing keeps correlation and drops the
    identifier; it is off by default only because forensics were explicitly asked for."""
    monkeypatch.setenv("PERSEUS_HASH_IPS", "1")
    C = _client(tmp_path, monkeypatch)
    _call(C, "/")
    ip = _lines(tmp_path)[0]["ip"]
    assert ip.startswith("h:") and "5.6.7.8" not in ip


def test_the_sidecar_holds_no_telegram_credentials():
    """ONE BRAIN. Five copies of a bot token is the 'one value, several homes' defect, and five
    copies of the rules is five things that drift. The client reports; colt-web decides and pages."""
    src = open(os.path.join(ROOT, "perseus", "client.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    for forbidden in ("BOT_TOKEN", "api.telegram.org", "sendMessage", "smtplib"):
        assert forbidden not in code, "the thin client must never learn to send: %s" % forbidden


def test_copying_the_client_also_wires_it_in(tmp_path):
    """THE DEFECT THAT CAUSED THE SILENCE. perseus_client.py sat in two projects imported by
    NOTHING while the copy step printed 'copied'. Copying a file is not installing a control."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("perseus_cli", os.path.join(ROOT, "perseus.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = str(tmp_path)
    with open(os.path.join(d, "main.py"), "w", encoding="utf-8") as fh:
        fh.write('from fastapi import FastAPI\napp = FastAPI(title="x")\n\n@app.get("/")\ndef r(): return 1\n')
    assert m.wire_middleware(d) == ("main.py", "WIRED")
    assert m.wire_middleware(d)[1] == "already wired", "wiring must be idempotent"
    src = open(os.path.join(d, "main.py"), encoding="utf-8").read()
    __import__("ast").parse(src)                      # the rewritten module must still parse
    assert "app.add_middleware(perseus_client.Middleware)" in src
    # AND IT MUST REFUSE RATHER THAN GUESS. A silent no-op here is the failure being fixed.
    empty = str(tmp_path / "empty")
    os.makedirs(empty, exist_ok=True)
    fn, how = m.wire_middleware(empty)
    assert fn is None and "by hand" in how


def test_the_brain_alerts_on_another_projects_scanner(tmp_path, monkeypatch):
    """The rules and the credentials stay in ONE place: the other projects emit evt=http, colt-web
    reads it and pages. Five copies of alerts.py is five things that drift."""
    now = int(time.time())
    rows = [{"ts": now - 5, "evt": "http", "service": "jhw-web", "ip": "9.9.9.9", "path": p}
            for p in ("/.env", "/wp-login.php", "/.git/config", "/phpinfo", "/vendor/phpunit")]
    _setup(monkeypatch, tmp_path, rows, {})
    sent = []
    fleet.watch(0, lambda m: sent.append(m))
    assert sent and "SCANNER" in sent[0] and "9.9.9.9" in sent[0]
    assert "jobhuntwow.com" in sent[0], "the alert must name the project, not the service id"


def test_a_real_visitor_on_another_project_is_not_alerted(tmp_path, monkeypatch):
    """VARIETY, NOT VOLUME. One address missing the same stale link many times is a person; two
    real visitors were nearly blocked on 10 Aug for exactly this."""
    now = int(time.time())
    # THE FIRST VERSION OF THIS FIXTURE PROVED NOTHING. It used /app, which is not probe-shaped
    # at all, so it never reached the variety threshold and lowering that threshold to 1 changed
    # nothing. To test a threshold the fixture has to actually be counted BY it: one probe-shaped
    # path, hit many times, is a stale inbound link or one opportunistic try -- not a scan.
    rows = ([{"ts": now - 5, "evt": "http", "service": "jhw-web", "ip": "8.8.8.8", "path": "/.env"}
             for _ in range(60)] +
            [{"ts": now - 5, "evt": "http", "service": "jhw-web", "ip": "8.8.8.8", "path": "/app"}
             for _ in range(200)])
    _setup(monkeypatch, tmp_path, rows, {})
    sent = []
    fleet.watch(0, lambda m: sent.append(m))
    assert not sent, "an ordinary visitor must never page the operator: %r" % sent[:1]


def test_the_brain_does_not_double_alert_on_cybergod_itself(tmp_path, monkeypatch):
    """colt-web already alerts on its own traffic through alerts.py. Two paths would double every
    message, and a doubled alert is how an operator learns to ignore alerts."""
    now = int(time.time())
    rows = [{"ts": now - 5, "evt": "http", "service": "colt-web", "ip": "9.9.9.9", "path": p}
            for p in ("/.env", "/wp-login.php", "/.git/config", "/phpinfo", "/vendor/x")]
    _setup(monkeypatch, tmp_path, rows, {})
    sent = []
    fleet.watch(0, lambda m: sent.append(m))
    assert not sent


def test_the_watch_advances_so_it_cannot_re_alert(tmp_path, monkeypatch):
    """An alert loop that re-reads the same lines pages forever about one scanner."""
    now = int(time.time())
    rows = [{"ts": now - 5, "evt": "http", "service": "jhw-web", "ip": "9.9.9.9", "path": p}
            for p in ("/.env", "/wp-login.php", "/.git/config", "/phpinfo")]
    _setup(monkeypatch, tmp_path, rows, {})
    sent = []
    ts = fleet.watch(0, lambda m: sent.append(m))
    assert len(sent) == 1 and ts >= now - 5
    fleet.watch(ts, lambda m: sent.append(m))
    assert len(sent) == 1, "the same lines must not alert twice"


def test_wiring_into_a_PACKAGE_uses_a_relative_import():
    """THE DEFECT THE FLEET PAGE CAUGHT ON ITS FIRST REAL RUN.

    cybergod deployed with the middleware wired and still showed `sidecar: not installed`. The
    page was right: `webapp/backend/app` has an __init__.py and every sibling is imported with
    `from . import store, assistant, brand`. My auto-wiring emitted a BARE `import perseus_client`,
    which raises ModuleNotFoundError there -- and the wrapper's `except` swallowed it, so colt-web
    ran UNGUARDED while the deploy reported success.

    CLAUDE.md already records exactly this: "app is a PACKAGE -- use `from . import telemetry`; a
    bare `import telemetry` fails at runtime and the except-swallow would hide it."
    """
    import ast
    import importlib.util
    import tempfile
    spec = importlib.util.spec_from_file_location("pcli", os.path.join(ROOT, "perseus.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    pkg = tempfile.mkdtemp()
    open(os.path.join(pkg, "__init__.py"), "w").close()
    with open(os.path.join(pkg, "main.py"), "w", encoding="utf-8") as fh:
        fh.write('from fastapi import FastAPI\napp = FastAPI(title="x")\n')
    assert m.wire_middleware(pkg)[1] == "WIRED"
    src = open(os.path.join(pkg, "main.py"), encoding="utf-8").read()
    ast.parse(src)
    assert "from . import perseus_client" in src, "a package needs a RELATIVE import"

    plain = tempfile.mkdtemp()                       # no __init__.py -> bare import is correct
    with open(os.path.join(plain, "main.py"), "w", encoding="utf-8") as fh:
        fh.write('from fastapi import FastAPI\napp = FastAPI()\n')
    m.wire_middleware(plain)
    src = open(os.path.join(plain, "main.py"), encoding="utf-8").read()
    assert "from . import" not in src and "import perseus_client" in src


def test_a_multiline_fastapi_constructor_is_found():
    """It reported 'no ASGI app found' for jobhuntwow, Klima AND jev.best, because it required the
    whole `app = FastAPI(...)` call on one line and all three span several."""
    import ast
    import importlib.util
    import tempfile
    spec = importlib.util.spec_from_file_location("pcli", os.path.join(ROOT, "perseus.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "main.py"), "w", encoding="utf-8") as fh:
        fh.write('from fastapi import FastAPI\napp = FastAPI(\n    title="x (y)",\n'
                 '    docs_url=None,\n)\n\n@app.get("/")\ndef r(): return 1\n')
    assert m.wire_middleware(d)[1] == "WIRED"
    src = open(os.path.join(d, "main.py"), encoding="utf-8").read()
    ast.parse(src)                                   # the rewritten module must still parse
    assert src.index("add_middleware") > src.index("docs_url=None"), \
        "the insert must land AFTER the whole call, not inside it"


def test_the_live_cybergod_wiring_is_a_relative_import():
    """The file that actually shipped unguarded. Assert the deployed shape, not just the generator."""
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    i = src.index("app.add_middleware(perseus_client.Middleware)")
    block = src[max(0, i - 300):i]
    assert "from . import perseus_client" in block, \
        "app/ is a package: a bare import raises and the except-swallow hides it"


def test_a_swallowed_wiring_failure_is_printed_loudly():
    """It must never fail silently again. The whole incident is that the deploy said success while
    the control was not installed."""
    src = open(os.path.join(ROOT, "perseus.py"), encoding="utf-8").read()
    assert "PERSEUS SIDECAR NOT WIRED" in src


def test_a_project_with_its_OWN_event_volume_is_still_seen(monkeypatch, tmp_path):
    """THE BLIND SPOT WAS MINE, NOT THEIRS.

    klima writes to `polara_events` and s4biz to `s4biz_events` -- their own volumes, each with its
    own promtail. Reading only `colt_events` reported both as "no log line at all, we CANNOT SEE
    this project", which was a true statement about where I was looking and a false one about them.
    Same family as the Loki query that returned nothing because it was malformed.

    colt-web now mounts those volumes read-only and fleet reads every one it can reach.
    """
    now = int(time.time())
    shared = os.path.join(str(tmp_path), "colt.log")
    polara = os.path.join(str(tmp_path), "polara.log")
    for path, svc in ((shared, "colt-web"), (polara, "polara-web")):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": now - 30, "evt": "http", "service": svc,
                                 "ip": "1.1.1.1", "path": "/"}) + "\n")
    monkeypatch.setattr(fleet, "EVENTS", shared)
    monkeypatch.setattr(fleet, "EXTRA_EVENTS", [polara])
    monkeypatch.setattr(fleet, "BEAT_DIR", os.path.join(str(tmp_path), "beats"))
    by = {p["service"]: p for p in fleet.status()["projects"]}
    assert by["polara-web"]["state"] != "silent", \
        "a project on its own volume must not read as unseeable once we mount it"
    assert by["polara-web"]["requests_24h"] == 1
    assert by["colt-web"]["requests_24h"] == 1, "the shared log must still be read"


def test_an_unmounted_extra_log_is_skipped_not_fatal(monkeypatch, tmp_path):
    """A box where a project is not deployed has no such volume. The page must still render."""
    now = int(time.time())
    shared = os.path.join(str(tmp_path), "colt.log")
    with open(shared, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": now - 30, "evt": "http", "service": "colt-web",
                             "ip": "1.1.1.1", "path": "/"}) + "\n")
    monkeypatch.setattr(fleet, "EVENTS", shared)
    monkeypatch.setattr(fleet, "EXTRA_EVENTS", ["/nope/never/events.log"])
    monkeypatch.setattr(fleet, "BEAT_DIR", os.path.join(str(tmp_path), "beats"))
    assert fleet.status()["projects"]


def test_the_service_names_match_what_each_project_actually_stamps():
    """jev-api is the CONTAINER; it stamps `service=jev-web`. Looking for the container name is why
    a project with lines in the log read as unseeable. The list must hold the STAMPED value."""
    svcs = {p["service"] for p in fleet.PROJECTS}
    assert "jev-web" in svcs and "jev-api" not in svcs


def test_cybergods_deploy_never_depends_on_a_sibling_project():
    """THE STAGING GATE CAUGHT THIS AND PRODUCTION WAS NEVER TOUCHED.

        external volume "klima-shop_polara_events" not found
        [X] remote deploy failed ... STAGING GATE: NO-GO

    I mounted klima's and s4biz's event volumes into colt-web with `external: true` so the Fleet
    page could read them. Two defects in one change:
      1. I GUESSED the compose project prefix. This repository already records that lesson from
         dbbackup -- compose prefixes volume names with the project name, and the only honest way
         to know one is to ASK docker. I quoted that rule in the commit that broke it.
      2. Far worse: `external: true` makes colt-web UNDEPLOYABLE anywhere the volume is absent.
         Staging does not run Klima, so cybergod's own deploy required a sibling to exist.

    A STATUS PAGE IS NEVER WORTH COUPLING A DEPLOY. The page reports `elsewhere` instead, and
    `python fleet.py` reads every project's own log over ssh, where no coupling is needed.
    """
    src = open(os.path.join(ROOT, "docker-compose.web.yml"), encoding="utf-8").read()
    for vol in ("polara_events", "s4biz_events"):
        assert vol not in src, \
            "colt-web must not require %s: a missing sibling volume blocks its own deploy" % vol


def test_a_project_that_keeps_its_own_log_is_ELSEWHERE_not_blind(monkeypatch, tmp_path):
    """Collapsing this into SILENT would repeat the error the page exists to prevent: reporting
    where WE looked as a fact about THEM. klima and s4biz write to their own event volumes."""
    now = int(time.time())
    _setup(monkeypatch, tmp_path,
           [{"ts": now - 30, "evt": "http", "service": "colt-web", "ip": "1.1.1.1", "path": "/"}],
           {})
    monkeypatch.setattr(fleet, "EXTRA_EVENTS", [])
    st = fleet.status()
    by = {p["service"]: p for p in st["projects"]}
    for svc in ("polara-web", "s4biz-web"):
        assert by[svc]["state"] == "elsewhere", by[svc]
        assert "own event volume" in by[svc]["why"]
        assert "fleet.py" in by[svc]["why"], "it must say how to actually read them"
        assert "BLIND" not in by[svc]["why"]
    assert st["elsewhere"] == 2
    # jev.best writes to the SHARED volume, so its absence really is blindness.
    assert by["jev-web"]["state"] == "silent"


# ------------------------------------------------------- the namespace-package trap (2026-09-07)
# `__init__.py` ALONE IS THE WRONG DISCRIMINATOR. jobhuntwow's backend/app has none and is still a
# package: Python 3 namespace packages make `from . import x` work, and serve.py imports it as
# `app.main`. The old heuristic emitted a bare import there, which cannot resolve from /app, so the
# wrapper's except would have swallowed it and a project taking ~6000 attacks a day would have
# stayed UNGUARDED while the deploy reported success -- the same shape that left cybergod bare.

def _perseus_script():
    """NOTE: `import perseus` gets the perseus/ PACKAGE, not the root perseus.py SCRIPT -- the repo
    has both and the package wins. Load the script by path or every assertion below silently
    measures the wrong module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "perseus_script", os.path.join(ROOT, "perseus.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _wire(tmp_path, main_src, init=False):
    perseus = _perseus_script()
    d = tmp_path / "app"
    d.mkdir()
    if init:
        (d / "__init__.py").write_text("", encoding="utf-8")
    (d / "main.py").write_text(main_src, encoding="utf-8")
    perseus.wire_middleware(str(d))
    return (d / "main.py").read_text(encoding="utf-8")


def test_a_namespace_package_gets_the_relative_import(tmp_path):
    """No __init__.py, but it imports its siblings relatively -- that is a package by construction."""
    out = _wire(tmp_path, "from . import store\napp = FastAPI(\n    title='x',\n)\n")
    assert "from . import perseus_client" in out
    assert "\n    import perseus_client\n" not in out


def test_a_genuinely_flat_module_dir_keeps_the_bare_import(tmp_path):
    """jev.best's webapp is a flat directory on sys.path; a relative import would fail there."""
    out = _wire(tmp_path, "import os\napp = FastAPI()\n")
    assert "\n    import perseus_client\n" in out
    assert "from . import perseus_client" not in out


def test_the_emitted_import_actually_resolves_in_the_real_layout(tmp_path):
    """STRING MATCHING IS NOT PROOF. Reproduce jobhuntwow's container layout -- WORKDIR /app, the
    package at /app/app, the sidecar at /app/app/perseus_client.py, entered via `app.main` -- and
    RUN it. The bare form raises ModuleNotFoundError here; that is the whole defect."""
    import subprocess
    root = tmp_path / "root"
    (root / "app").mkdir(parents=True)
    (root / "app" / "perseus_client.py").write_text("Middleware = object\n", encoding="utf-8")
    (root / "app" / "main.py").write_text(
        "from . import perseus_client\napp = perseus_client.Middleware\n", encoding="utf-8")
    (root / "serve.py").write_text("from app import main\nprint('IMPORTED OK')\n", encoding="utf-8")
    r = subprocess.run([sys.executable, "serve.py"], cwd=str(root),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0 and "IMPORTED OK" in (r.stdout or ""), \
        "the relative form must resolve in the real layout: %s" % (r.stderr or "")[-300:]

    # ...and prove the OLD form genuinely fails, or the test above proves nothing.
    (root / "app" / "main.py").write_text(
        "import perseus_client\napp = perseus_client.Middleware\n", encoding="utf-8")
    r2 = subprocess.run([sys.executable, "serve.py"], cwd=str(root),
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r2.returncode != 0 and "ModuleNotFoundError" in (r2.stderr or ""), \
        "the bare form must FAIL here, otherwise this fixture is not reproducing the defect"


def test_every_project_carries_the_import_form_its_own_layout_needs():
    """The five real projects, checked against the rule rather than against a remembered answer."""
    perseus = _perseus_script()
    for d, _name in perseus.CLIENT_TARGETS:   # (dir, filename) tuples, not strings
        p = os.path.join(d, "main.py")
        if not os.path.exists(p):
            continue
        s = open(p, encoding="utf-8").read()
        if "perseus_client" not in s:
            continue
        pkg = (os.path.exists(os.path.join(d, "__init__.py"))
               or re.search(r"^\s*from\s+\.\s*import\s|^\s*from\s+\.\w", s, re.M) is not None)
        want = "from . import perseus_client" if pkg else "import perseus_client"
        got = re.search(r"^\s*(from \. import perseus_client|import perseus_client)$", s, re.M)
        assert got and got.group(1) == want, \
            "%s is wired as %r but its layout needs %r" % (d, got and got.group(1), want)


# --------------------------------------------------------------- the fleet rollout (2026-09-07)
# The sidecar was wired into five repos and running in one container. `--rollout` deploys the other
# four through their OWN orchestrators, because reimplementing a project's deploy is the "two homes
# for one job" defect, and their ship.py already owns their tests, staging gate and commit.

def test_the_rollout_never_deploys_cybergod_into_itself():
    """ship.py already deployed colt-web; including it here would recurse."""
    perseus = _perseus_script()
    roots = [r.lower() for _n, r, _a in perseus.ROLLOUT]
    assert not any(r.rstrip("\\/").endswith("linkedin scraper") for r in roots), \
        "cybergod's own repo must not be in the rollout list"
    assert {n for n, _r, _a in perseus.ROLLOUT} == {
        "jobhuntwow.com", "jev.best", "jev.best (api)",
        "klimaanlage-preise.de", "s4biz.io"}


def test_every_rollout_entry_calls_that_project_s_real_orchestrator():
    """A verb this repo invented is a rollout that dies on its own launcher."""
    perseus = _perseus_script()
    for name, root, argv in perseus.ROLLOUT:
        if not os.path.isdir(root):
            continue                       # not checked out on this machine; --rollout says so
        assert os.path.exists(os.path.join(root, argv[0])), \
            "%s: %s does not exist" % (name, argv[0])


def test_one_failing_project_does_not_abandon_the_rest(tmp_path, monkeypatch, capsys):
    """These are independent products. A broken build in one must not leave the others unguarded."""
    perseus = _perseus_script()
    for n in ("a", "b", "c"):
        (tmp_path / n).mkdir()
        (tmp_path / n / "ship.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(perseus, "ROLLOUT", [
        ("a", str(tmp_path / "a"), ["ship.py"]),
        ("b", str(tmp_path / "b"), ["ship.py"]),          # this one fails
        ("c", str(tmp_path / "c"), ["ship.py"]),
    ])
    seen = []

    class _R:
        def __init__(self, rc): self.returncode = rc

    def fake_run(argv, cwd=None, **kw):
        seen.append(os.path.basename(cwd))
        return _R(1 if cwd.endswith("b") else 0)

    monkeypatch.setattr(perseus.subprocess, "run", fake_run)
    monkeypatch.setattr(perseus, "ssh_script", lambda *a, **k: ("END", "", 0))
    rc = perseus.cmd_rollout()
    assert seen == ["a", "b", "c"], "the loop stopped early: %r" % (seen,)
    assert rc == 1, "a failed project must be reflected in the exit code"
    out = capsys.readouterr().out
    assert "FAILED   b" in out and "OK       a" in out and "OK       c" in out


def test_a_project_that_is_not_on_this_machine_is_skipped_not_crashed(tmp_path, monkeypatch, capsys):
    perseus = _perseus_script()
    monkeypatch.setattr(perseus, "ROLLOUT", [("ghost", str(tmp_path / "nope"), ["ship.py"])])
    monkeypatch.setattr(perseus, "ssh_script", lambda *a, **k: ("END", "", 0))
    called = []
    monkeypatch.setattr(perseus.subprocess, "run", lambda *a, **k: called.append(1))
    assert perseus.cmd_rollout() == 0, "a missing checkout is not a failure"
    assert not called, "nothing may be executed for a project that is not here"
    assert "SKIPPED  ghost" in capsys.readouterr().out


def test_the_rollout_proves_itself_from_the_heartbeat(tmp_path, monkeypatch, capsys):
    """A deploy returning 0 says the build worked. Only a beat says the middleware is RUNNING."""
    perseus = _perseus_script()
    monkeypatch.setattr(perseus, "ROLLOUT", [])
    asked = {}

    def fake_ssh(script, **kw):
        asked["script"] = script
        return ("  jhw-web  09:12:00Z\n  jev-web  09:12:01Z\nEND", "", 0)

    monkeypatch.setattr(perseus, "ssh_script", fake_ssh)
    perseus.cmd_rollout()
    out = capsys.readouterr().out
    assert "perseus_beats" in asked["script"], "it must read the real heartbeat directory"
    assert "jhw-web" in out and "jev-web" in out
    # ...and it must not silently imply klima/s4biz are broken: they write elsewhere by design.
    low = out.lower()
    assert "own event volumes" in low and "fleet.py" in low


def test_jev_rebuilds_the_container_that_actually_holds_the_middleware():
    """`jev.py deploy` builds jev-web (the Caddy front). The wired module is webapp/main.py, which
    Dockerfile.api builds into jev-api -- so deploy ALONE rebuilds the one container that does not
    carry the sidecar, and the Fleet page kept reading 'not installed' after a green run."""
    perseus = _perseus_script()
    verbs = [tuple(a) for n, _r, a in perseus.ROLLOUT if n.startswith("jev.best")]
    assert ("jev.py", "api") in verbs, "jev-api is never rebuilt, so the middleware never ships"
    assert ("jev.py", "deploy") in verbs


def test_the_heartbeat_directory_is_created_writable_for_non_root_containers():
    """jobhuntwow and s4biz run as uid 10001; os.makedirs() in a root-owned 0755 directory on the
    shared volume raises PermissionError. The installer runs as root, so it creates it 1777."""
    perseus = _perseus_script()
    script = perseus.install_script("Zm9v")
    src = re.sub(r"#.*", "", script)          # our own comments must not satisfy this
    assert "perseus_beats" in src and "1777" in src,         "the beats directory must be created world-writable by the root installer"


def test_a_beat_that_cannot_be_written_says_so_instead_of_vanishing(tmp_path, monkeypatch, capsys):
    """A swallowed heartbeat failure is indistinguishable from 'never deployed' -- which is exactly
    what the Fleet page showed for jobhuntwow after a perfect deploy."""
    import importlib
    monkeypatch.setenv("PERSEUS_BEATS", str(tmp_path / "afile" / "beats"))
    (tmp_path / "afile").write_text("not a directory", encoding="utf-8")
    from perseus import client as pc
    importlib.reload(pc)
    pc._CACHE["beat"] = 0
    pc._beat(1)
    out = capsys.readouterr().out
    assert "perseus_beat_unwritable" in out, "the failure must be announced once"
    pc._CACHE["beat"] = 0
    pc._beat(1)
    assert out.count("perseus_beat_unwritable") == 1, "once, not once per request"


def test_the_rollout_installs_the_heartbeat_directory_before_it_deploys():
    """The rollout ENDS by reading the beats directory; the installer is what creates it 1777 so a
    container running as uid 10001 can write. Skipping the install made the rollout verify itself
    against a directory that did not exist -- a check measuring the absence of its own precondition.
    """
    perseus = _perseus_script()
    src = re.sub(r"#.*", "", inspect_source(perseus))
    branch = src[src.index("if a.rollout:"):src.index("return cmd_rollout()")]
    assert "install_script" in branch and "ssh_script" in branch, \
        "the rollout must install the hub (and the beats dir) before deploying"


def inspect_source(mod):
    import inspect as _i
    return _i.getsource(mod)
