"""Colt cyber pre-sales web app — FastAPI backend.

Turns the Telegram-bot logic into a web app:
  * colt_auth.Auth for zero-trust login (email + shared password + emailed 6-digit OTP),
    email used as the uid; success sets an httpOnly signed session cookie.
  * run_assessment.py driven as a subprocess; its stdout event lines are streamed to the
    browser over Server-Sent Events; decks (.pptx) are served as owner-scoped downloads.
  * cassandra assistant (DeepSeek + allowlisted live research) behind /api/assist.
  * serves the built SPA (webapp/frontend/dist) with SPA fallback.
"""
import os
import re
import json
import time
import uuid
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    JSONResponse, StreamingResponse, FileResponse, HTMLResponse, PlainTextResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import store, assistant
from .auth import AUTH, make_session, read_session, email_ok, _log
from .settings import (
    ENGINE, JOBS_DIR, FRONTEND_DIST, SESSION_COOKIE, SESSION_MAX_AGE,
    SESSION_COOKIE_SECURE, CORS_ORIGINS,
)

app = FastAPI(title="Colt Cyber Pre-Sales API", version="1.0.0")

# ---- visitor telemetry + security alerting -------------------------------------------------------
# One JSON event per request (ip/device/bot/status/ms) -> Loki -> Grafana "Visitor Log", and the same
# event feeds the alert rules (DDoS, scanners, IDOR probing, exfil). Detection only: it never blocks
# a request and never touches the firewall (Amnezia VPN shares this host).
try:
    from . import telemetry as _telemetry, alerts as _alerts

    def _session_user(request):
        try:
            tok = request.cookies.get(SESSION_COOKIE)
            return read_session(tok) if tok else ""
        except Exception:
            return ""

    _telemetry.install(app, _session_user)

    # daily "who used the platform and what did they run" report -> ALERT_EMAIL at 07:00 UTC.
    # In-app task on purpose: no cron inside the container, no systemd unit on the droplet that would
    # drift out of this repo.
    from . import daily_report as _daily

    @app.on_event("startup")
    async def _start_daily_report():
        import asyncio as _aio
        _aio.create_task(_daily.scheduler())
except Exception as _e:  # telemetry must never stop the app from booting
    print('{"evt":"telemetry_init","result":"error","err":"%s"}' % repr(_e)[:120], flush=True)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in CORS_ORIGINS.split(",")] if CORS_ORIGINS != "*" else ["*"],
        allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
    )


# ---------------- models ----------------
class BeginReq(BaseModel):
    email: str
    password: str


class VerifyReq(BaseModel):
    email: str
    code: str


class AssessReq(BaseModel):
    company: str
    lang: str = "en"          # "en" | "de" — language of the 4 generated decks


class RefineReq(BaseModel):
    # answers keyed by the clarify question's `maps_to` (clarify.py). The backend turns them into
    # run_assessment override flags — the frontend stays dumb, all parsing lives server-side.
    answers: dict = {}
    lang: str = "en"          # inherited from the parent run; the operator can also switch language


class AssistReq(BaseModel):
    message: str


# ---------------- session helpers ----------------
def _current_email(request: Request):
    tok = request.cookies.get(SESSION_COOKIE)
    return read_session(tok) if tok else None


def _require_email(request: Request) -> str:
    email = _current_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="not authenticated")
    return email


def _set_session_cookie(resp: Response, email: str) -> None:
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=make_session(email),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


# ---------------- auth ----------------
@app.post("/api/auth/begin")
def auth_begin(req: BeginReq, request: Request):
    email = (req.email or "").strip().lower()
    # colt_auth.begin uses email as the uid; it also does the strict regex + password check.
    state, message = AUTH.begin(email, email, req.password or "")
    try:
        from . import telemetry as _t, alerts as _a
        ip = _t.client_ip(request); ua = request.headers.get("user-agent", "")
        if state in ("error", "denied", "locked"):
            # wrong password / not an allowed identity -> forensics + alert past the threshold
            _a.observe_login_failure(email, ip, state, ua)
        elif state in ("otp_sent", "authed"):
            _a.observe_login_success(email, ip, ua)
    except Exception:
        pass
    return {"state": state, "message": message}


@app.post("/api/auth/verify")
def auth_verify(req: VerifyReq, request: Request):
    email = (req.email or "").strip().lower()
    ok, message = AUTH.verify(email, (req.code or "").strip())
    if not ok:
        try:
            from . import telemetry as _t, alerts as _a
            _a.observe_otp_failure(email, _t.client_ip(request))
        except Exception:
            pass
        return JSONResponse({"ok": False, "message": message})
    resp = JSONResponse({"ok": True, "email": email})
    _set_session_cookie(resp, email)
    return resp


@app.post("/api/privacy/ack")
def privacy_ack(request: Request):
    """Record that the Art.13 data-processing notice was displayed and accepted.
    GDPR Art. 5(2) accountability: being able to SHOW that you informed people is the point."""
    try:
        from . import telemetry as _t
        email = ""
        try:
            tok = request.cookies.get(SESSION_COOKIE)
            email = (read_session(tok) or "") if tok else ""
        except Exception:
            pass
        _log(evt="privacy_ack", user=email, ip=_t.client_ip(request),
             ua=request.headers.get("user-agent", "")[:160], notice="art13-v1")
    except Exception:
        pass
    return {"ok": True}


@app.post("/api/auth/logout")
def auth_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@app.get("/api/me")
def me(request: Request):
    email = _current_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="not authenticated")
    return {"email": email}


# ---------------- assessment ----------------
def _job_dir(email: str, job_id: str) -> Path:
    safe_email = re.sub(r"[^a-z0-9._-]", "_", email.lower())
    d = Path(JOBS_DIR) / safe_email / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


@app.post("/api/assess")
async def assess(req: AssessReq, request: Request):
    email = _require_email(request)
    company = (req.company or "").strip()
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    lang = "de" if str(req.lang or "en").lower().startswith("de") else "en"
    job_id = uuid.uuid4().hex
    _job_dir(email, job_id)  # pre-create owner-scoped dir
    store.create_job(job_id, email, company, lang)
    _log(evt="assess_request", user=email, company=company, job=job_id, lang=lang)
    try:
        from . import telemetry as _t, alerts as _a
        _a.observe_assess(email, company, _t.client_ip(request))
    except Exception:
        pass
    # Start the engine NOW, server-side, detached from any HTTP connection.
    # It used to be the SSE generator that spawned the subprocess — so closing the tab, refreshing,
    # or a phone locking its screen cancelled the generator and killed a 5-minute run. The job is now
    # owned by the server; the stream is just a viewer.
    asyncio.create_task(_run_job(job_id, email, company, lang))
    return {"job_id": job_id}


def _deck_entry(job_id: str, path: Path) -> dict:
    return {"name": path.name, "url": f"/api/assess/{job_id}/deck/{path.name}"}


def _collect_decks(job_id: str, jobdir: Path) -> list:
    # .pptx decks first, then the combined _Report.html artifact (5th deliverable).
    out = [_deck_entry(job_id, p) for p in sorted(jobdir.glob("*.pptx"))]
    # the 5th deliverable — bespoke animated GEOPOL HTML (also accept the older _Report name)
    out += [_deck_entry(job_id, p) for p in sorted(jobdir.glob("*_GEOPOL_Animated*.html"))]
    out += [_deck_entry(job_id, p) for p in sorted(jobdir.glob("*_Report*.html"))]
    return out


_RUNNING: dict = {}          # job_id -> asyncio.Task, so we can see what is in flight


async def _run_job(job_id: str, email: str, company: str, lang: str, overrides: list = None):
    """Own the engine run. Writes every line to <jobdir>/run.log and finalises the DB row.
    Nothing here depends on an HTTP client being connected.

    `overrides` are extra run_assessment.py flags from the post-run clarification loop (a REFINE run):
    --domain / --exclude-domain / --pin / --asn / --net / --platform-operator / --notes. They are the
    sanctioned way scope changes after the first run — the operator asserted the fact, so the
    zero-false-positive ownership gate stays intact."""
    jobdir = _job_dir(email, job_id)
    logp = jobdir / "run.log"
    _RUNNING[job_id] = asyncio.current_task()

    def _w(line: str):
        try:
            with open(logp, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass

    if not Path(ENGINE).exists():
        _w(json.dumps({"evt": "error", "message": f"engine not found at {ENGINE}"}))
        store.finish_job(job_id, [], {}, status="error"); _RUNNING.pop(job_id, None); return

    cmd = ["python3", "-u", ENGINE, "--seed", company, "--outdir", str(jobdir), "--lang", lang]
    cmd += list(overrides or [])
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            # COLT_USER -> the engine stamps every event + the cost ledger with the requester,
            # so Grafana can answer "which AE ran this?" and cost is attributable per person.
            env={**os.environ, "COLT_USER": email})
    except Exception as e:
        _w(json.dumps({"evt": "error", "message": f"failed to start engine: {e!r}"}))
        store.finish_job(job_id, [], {}, status="error"); _RUNNING.pop(job_id, None); return

    summary, completed, tail = {}, False, []
    assert proc.stdout is not None
    try:
        async for raw in proc.stdout:
            line = raw.decode("utf-8", "ignore").rstrip()
            if not line:
                continue
            _w(line)
            tail.append(line); tail[:] = tail[-15:]
            if line.startswith("{"):
                try:
                    o = json.loads(line)
                    if isinstance(o, dict) and o.get("evt") == "assess_done":
                        summary = {"company": o.get("company", company), "critical": o.get("crit", 0),
                                   "high": o.get("high", 0), "medium": o.get("med", 0),
                                   "low": o.get("low", 0), "decks": o.get("decks", 0),
                                   "qwen_used": o.get("qwen_used", False)}
                except Exception:
                    pass
            if "ASSESSMENT COMPLETE" in line:
                completed = True
        await proc.wait()
    except asyncio.CancelledError:
        try: proc.kill()
        except Exception: pass
        store.finish_job(job_id, [], summary, status="error")
        _RUNNING.pop(job_id, None); raise
    except Exception as e:
        _w(json.dumps({"evt": "error", "message": repr(e)[:200]}))

    if completed:
        decks = _collect_decks(job_id, jobdir)
        store.finish_job(job_id, decks, summary, status="done")
    else:
        _w(json.dumps({"evt": "error", "message": "assessment failed",
                       "detail": "\n".join(tail) or "no output"}))
        store.finish_job(job_id, [], summary, status="error")
    _RUNNING.pop(job_id, None)


async def _assess_stream(job_id: str, email: str, start_line: int = 0):
    """SSE viewer over <jobdir>/run.log. Resumable: each frame carries an `id:` (the line number),
    so on reconnect the browser sends Last-Event-ID and we resume exactly where it left off —
    no duplicate lines, no lost progress, and the run itself never depended on this connection."""
    job = store.get_job(job_id)
    if not job or job["email"] != email.lower():
        yield _sse({"evt": "error", "message": "job not found"})
        return

    jobdir = _job_dir(email, job_id)
    logp = jobdir / "run.log"
    n = 0                      # lines emitted so far
    idle = 0.0

    while True:
        if logp.exists():
            try:
                with open(logp, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().split("\n")
            except Exception:
                lines = []
            while n < len(lines) - 1:            # last element is the partial/empty tail
                line = lines[n]; n += 1
                if n <= start_line:              # already delivered before the reconnect
                    continue
                if line.strip():
                    yield _sse({"evt": "progress", "line": line}, eid=n)

        job = store.get_job(job_id) or {}
        status = job.get("status", "running")
        if status != "running":
            # drain whatever landed between the last read and the status flip
            await asyncio.sleep(0.2)
            if logp.exists():
                try:
                    with open(logp, "r", encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().split("\n")
                except Exception:
                    lines = []
                while n < len(lines) - 1:
                    line = lines[n]; n += 1
                    if n > start_line and line.strip():
                        yield _sse({"evt": "progress", "line": line}, eid=n)
            if status == "done":
                yield _sse({"evt": "done", "decks": job.get("decks") or [],
                            "summary": job.get("summary") or {}})
            else:
                yield _sse({"evt": "error", "message": "assessment failed",
                            "detail": "see the log above"})
            return

        await asyncio.sleep(0.4)
        idle += 0.4
        if idle >= 15:                            # keep proxies + mobile radios from idling us out
            idle = 0.0
            yield ": keepalive\n\n"


def _sse(obj: dict, eid: int = None) -> str:
    # `id:` makes the stream RESUMABLE — the browser replays it back as Last-Event-ID on reconnect.
    head = ("id: %d\n" % eid) if eid is not None else ""
    return head + "data: " + json.dumps(obj) + "\n\n"


@app.get("/api/assess/{job_id}/status")
def assess_status(job_id: str, request: Request):
    """Polling fallback: works when SSE is impossible (locked phone, dead radio, proxy that buffers).
    The truth lives in the DB + run.log, not in a connection."""
    email = _require_email(request)
    job = store.get_job(job_id)
    if not job or job["email"] != email.lower():
        raise HTTPException(status_code=404, detail="job not found")
    logp = _job_dir(email, job_id) / "run.log"
    lines = []
    if logp.exists():
        try:
            lines = [l for l in logp.read_text(encoding="utf-8", errors="replace").split("\n") if l.strip()]
        except Exception:
            pass
    return {"status": job.get("status"), "company": job.get("company"), "lang": job.get("lang"),
            "lines": lines, "decks": job.get("decks") or [], "summary": job.get("summary") or {},
            "running": job_id in _RUNNING}


@app.get("/api/assess/{job_id}/events")
async def assess_events(job_id: str, request: Request):
    email = _require_email(request)
    # Standard SSE resume: the browser sends back the last id it saw.
    try:
        start_line = int(request.headers.get("last-event-id") or 0)
    except ValueError:
        start_line = 0
    return StreamingResponse(
        _assess_stream(job_id, email, start_line),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/assess/{job_id}/deck/{name}")
def assess_deck(job_id: str, name: str, request: Request):
    email = _require_email(request)
    job = store.get_job(job_id)
    if not job or job["email"] != email.lower():
        raise HTTPException(status_code=404, detail="not found")
    # prevent path traversal — only a bare filename; allow the .pptx decks and the _Report.html
    low = name.lower()
    if "/" in name or "\\" in name or ".." in name or not (low.endswith(".pptx") or low.endswith(".html")):
        raise HTTPException(status_code=400, detail="bad filename")
    jobdir = _job_dir(email, job_id)
    path = jobdir / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="deck not found")
    media = ("text/html" if low.endswith(".html")
             else "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    # HTML report opens in the browser; decks download as attachments.
    disp = "inline" if low.endswith(".html") else "attachment"
    return FileResponse(str(path), media_type=media, filename=name,
                        content_disposition_type=disp)


# ---------------------------------------------------------------- clarify + refine ---
# jobhuntwow gap->answer model (docs/TAILOR_LOGIC.md §4): deliver the artifacts first, then let the
# operator answer clarification questions / add facts and REFINE. clarify.json is written by the
# engine at the end of every run; /refine turns answers into override flags and re-runs the engine.

_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_CIDR_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$")
_ASN_RE = re.compile(r"^AS?\d+$", re.I)


def _split_tokens(v) -> list:
    """Accept a list OR a free-text string ('a, b; c') and return clean tokens."""
    if isinstance(v, list):
        items = v
    else:
        items = re.split(r"[,\n;]+", str(v or ""))
    return [t.strip() for t in items if str(t).strip()]


def _refine_flags(answers: dict) -> list:
    """Map clarify answers (keyed by the question's `maps_to`) into run_assessment.py flags.

    All parsing lives here so the frontend just posts the raw answers. A token that looks like an IP
    becomes --pin, a CIDR becomes --net, an ASxxxx becomes --asn, otherwise a domain (--domain), and
    'not mine' answers become --exclude-domain (autodiscover normalises IP vs apex)."""
    flags: list = []
    a = answers or {}

    def _host_of(tok: str) -> str:
        return tok.split()[0].split(":")[0].strip()   # "1.2.3.4:443 nginx" -> "1.2.3.4"

    for tok in _split_tokens(a.get("include_domains")):
        flags += ["--domain", _host_of(tok)]
    for tok in _split_tokens(a.get("include_nets")):
        flags += ["--net", tok]
    for tok in _split_tokens(a.get("include_asns")):
        flags += ["--asn", tok]

    # free-text "known netblocks or ASNs" — split by shape
    for tok in _split_tokens(a.get("netblocks_or_asns")):
        if _CIDR_RE.match(tok):
            flags += ["--net", tok]
        elif _ASN_RE.match(tok):
            flags += ["--asn", "AS" + re.sub(r"\D", "", tok)]
        elif _IP_RE.match(tok):
            flags += ["--pin", tok]
        elif "." in tok:
            flags += ["--domain", _host_of(tok)]

    # free-text "extra hosts/domains to add"
    for tok in _split_tokens(a.get("hosts_or_domains")):
        h = _host_of(tok)
        if _IP_RE.match(h):
            flags += ["--pin", h]
        elif _CIDR_RE.match(h):
            flags += ["--net", h]
        elif "." in h:
            flags += ["--domain", h]

    # "these are NOT mine" — from the exclude checkboxes (host:port) or a free-text list
    for tok in _split_tokens(a.get("exclude_hosts")) + _split_tokens(a.get("exclude_domains")):
        flags += ["--exclude-domain", _host_of(tok)]

    if a.get("platform_operator") in (True, "true", "yes", "on", 1, "1"):
        flags += ["--platform-operator"]

    notes = str(a.get("notes") or "").strip()
    if notes:
        flags += ["--notes", notes[:2000]]

    return flags


@app.get("/api/assess/{job_id}/clarify")
def assess_clarify(job_id: str, request: Request):
    """Return the post-run clarification questions (clarify.json) for a finished job."""
    email = _require_email(request)
    job = store.get_job(job_id)
    if not job or job["email"] != email.lower():
        raise HTTPException(status_code=404, detail="job not found")
    p = _job_dir(email, job_id) / "clarify.json"
    if not p.exists():
        return {"questions": [], "summary": {}, "company": job.get("company")}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"questions": [], "summary": {}, "company": job.get("company")}


@app.post("/api/assess/{job_id}/refine")
async def assess_refine(job_id: str, req: RefineReq, request: Request):
    """Answer the clarification questions -> a NEW child run, correctly re-scoped.

    We re-run the whole engine (from --seed company) with the answer-derived override flags rather
    than patching the old artifacts: recon is where scope is decided, so the clean way to change
    scope is to re-resolve it with the operator's asserted facts. The child streams exactly like the
    original assessment (same /events + /status)."""
    email = _require_email(request)
    parent = store.get_job(job_id)
    if not parent or parent["email"] != email.lower():
        raise HTTPException(status_code=404, detail="job not found")

    flags = _refine_flags(req.answers)
    if not flags:
        raise HTTPException(status_code=400, detail="no changes supplied")

    company = parent.get("company") or ""
    lang = "de" if str(req.lang or parent.get("lang") or "en").lower().startswith("de") else "en"
    child_id = uuid.uuid4().hex
    cdir = _job_dir(email, child_id)
    store.create_job(child_id, email, company, lang)
    # provenance: what the operator asserted, and which run it refines
    try:
        (cdir / "refine_request.json").write_text(
            json.dumps({"parent": job_id, "answers": req.answers, "flags": flags}, ensure_ascii=False),
            encoding="utf-8")
    except Exception:
        pass
    _log(evt="assess_refine", user=email, company=company, job=child_id, parent=job_id,
         flags=len(flags))
    asyncio.create_task(_run_job(child_id, email, company, lang, overrides=flags))
    return {"job_id": child_id, "parent": job_id}


@app.get("/api/history")
def history(request: Request):
    email = _require_email(request)
    out = []
    for j in store.history(email):
        out.append({
            "job_id": j["job_id"],
            "company": j["company"],
            "date": j["created"],
            "status": j["status"],
            "decks": j["decks"],
            "summary": j.get("summary", {}),
        })
    return out


# ---------------- assistant (cassandra) ----------------
@app.post("/api/assist")
async def assist(req: AssistReq, request: Request):
    _require_email(request)
    message = (req.message or "").strip()
    if not message:
        return {"reply": "(say something and I'll help)"}
    _log(evt="assist_query", chars=len(message))
    try:
        reply = await asyncio.to_thread(assistant.assist, message)
    except Exception as e:
        reply = ("The inference service is busy right now (I tried the primary and the fallback). "
                 "Give it a few seconds and resend.  [%s]" % (repr(e)[:120]))
    return {"reply": reply}


# ---------------- SPA (built frontend) ----------------
_DIST = Path(FRONTEND_DIST)
if (_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")


# A single-page app catch-all answers 200 to EVERYTHING, which is wrong twice over:
#   1. a scanner walking a wordlist (/file6.php, /wp-includes/..., /.env) gets 200 on every entry, so
#      its report says our host "has" all of it — free advertising that we look like a soft target;
#   2. our own path_probe / dir_bruteforce alert rules key on 404/403, so the textbook case they were
#      written for never fired.
# Real SPA routes are a short, known list. Everything else that looks like a FILE (has an extension)
# or matches a known probe gets an honest 404.
_APP_ROUTES = {"", "login", "app", "privacy"}
_PROBE_HINT = (".php", ".asp", ".aspx", ".jsp", ".cgi", ".env", ".git", ".sql", ".bak", ".old",
               ".zip", ".tar", ".gz", ".yml", ".yaml", ".ini", ".conf", ".sh", ".py", ".rb",
               "wp-", "wordpress", "phpmyadmin", "xmlrpc", "vendor/", "cgi-bin", "shell",
               "adminer", "solr", "actuator", "struts", "/.")


def _is_probe(path: str) -> bool:
    p = path.lower().strip("/")
    if not p:
        return False
    root = p.split("/", 1)[0]
    if root in _APP_ROUTES:
        return False
    return any(h in p for h in _PROBE_HINT)


@app.get("/{full_path:path}")
def spa(full_path: str):
    # never shadow the API namespace
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="not found")
    # serve a real static file if it exists (favicon, etc.)
    if full_path:
        candidate = _DIST / full_path
        if candidate.is_file() and _DIST in candidate.resolve().parents:
            return FileResponse(str(candidate))
    # obvious scanner bait -> 404. It never existed; say so.
    if _is_probe(full_path):
        raise HTTPException(status_code=404, detail="not found")
    index = _DIST / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    # tolerate dist/ being absent during dev
    return HTMLResponse(
        "<h1>Colt Cyber Pre-Sales</h1>"
        "<p>Frontend build not found (webapp/frontend/dist). The API is live under /api/.</p>",
        status_code=200,
    )
