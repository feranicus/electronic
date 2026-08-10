"""Cybergod.ai — Sales & Pre-Sales cyber-risk platform. FastAPI backend.

Turns the Telegram-bot logic into a web app:
  * colt_auth.Auth for zero-trust login (email + shared password + emailed 6-digit OTP),
    email used as the uid; success sets an httpOnly signed session cookie.
  * run_assessment.py driven as a subprocess; its stdout event lines are streamed to the
    browser over Server-Sent Events; decks (.pptx) are served as owner-scoped downloads.
  * cassandra assistant (DeepSeek + allowlisted live research) behind /api/assist.
  * serves the built SPA (webapp/frontend/dist) with SPA fallback.
"""
import subprocess, sys
import os
import re
import json
import time
import uuid
import asyncio
import threading
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
    ENGINE, COMPLIANCE_ENGINE, JOBS_DIR, FRONTEND_DIST, SESSION_COOKIE, SESSION_MAX_AGE,
    SESSION_COOKIE_SECURE, CORS_ORIGINS,
)

app = FastAPI(title="Cybergod.ai Sales & Pre-Sales API", version="1.0.0")

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

    # SHIELD REVIEW — the same four models, out of band, on a timer. Same reasoning as the daily
    # report: an in-app asyncio task, so there is no cron in the container and no systemd unit on
    # the droplet to drift out of this repo. It NEVER touches a request; it reads what the
    # deterministic shield already did and proposes bounded threshold changes.
    @app.on_event("startup")
    async def _start_shield_panel():
        import asyncio as _aio

        async def _loop():
            every = max(3600, int(os.environ.get("SHIELD_REVIEW_EVERY_S", 21600)))
            while True:
                await _aio.sleep(every)
                try:
                    from . import shield, shield_panel
                    # Nothing happened, so there is nothing to review and no tokens to spend.
                    if not (shield.state().get("blocked") or shield.state().get("watching")):
                        continue
                    await _aio.get_event_loop().run_in_executor(None, shield_panel.main)
                except Exception as exc:                    # a review must never kill the app
                    print('{"evt":"shield_panel_error","err":"%s"}' % repr(exc)[:160], flush=True)

        _aio.create_task(_loop())
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
    lang: str = "en"          # coerced by doc_lang() to what the engine can render
    # EXPLICIT OPERATOR ASSERTION. Seeding a shared zone (gov.ru, co.uk) is declined by default
    # because it would imply a single owner for thousands of independent bodies — the budget.gov.ru
    # incident. A regulator or researcher may legitimately want exactly that, so they can say so,
    # and the run is then labelled a ZONE SURVEY rather than an assessment of one company.
    zone_survey: bool = False


class RefineReq(BaseModel):
    # answers keyed by the clarify question's `maps_to` (clarify.py). The backend turns them into
    # run_assessment override flags — the frontend stays dumb, all parsing lives server-side.
    answers: dict = {}
    lang: str = "en"          # inherited from the parent run; the operator can also switch language


class ComplianceReq(BaseModel):
    company: str
    lang: str = "en"          # language of the compliance decks + HTML
    jurisdiction: str = ""    # "EU" | "CA" — WHICH REGIME SET is graded. Resolved through the
                              # engine's registry; an unknown value falls back to the EU set.


class ComplianceRefineReq(BaseModel):
    # answers keyed by compliance_clarify's `maps_to` (sector/size_band/sells_digital_products/...)
    answers: dict = {}
    lang: str = "en"
    jurisdiction: str = ""    # carried through the refine run, or the child re-grades against the
                              # WRONG regime set the moment the operator answers a question.


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
    # The operator asked to be told about EVERY sign-in. Threaded inside notify, so a slow
    # Telegram/Gmail call can never delay the user's login or block the event loop.
    try:
        from . import telemetry as _t, geoip as _g, notify as _n
        _ip = _t.client_ip(request)
        _n.notify_login(email, ip=_ip, ua=request.headers.get("user-agent", "")[:200],
                        country=(request.headers.get("cf-ipcountry") or _g.country(_ip)), how="web")
    except Exception:
        pass
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


# ------------------------------------------------------------------ PUBLIC DEMO ---
# "Trojan Empire" — a FICTIONAL company with FABRICATED findings, open to anyone.
# Deliberately NOT gated behind auth and deliberately NOT running the engine:
#   * running the real pipeline for every anonymous visitor would burn Shodan query credits and
#     inference tokens, and a crawler could drain both;
#   * the data is invented anyway, so there is nothing to discover.
# The artifacts are pre-built once by scripts/demo_build.py using the SAME deterministic deck
# builders the paid product uses, then served as static files. Every host uses an RFC 5737
# documentation range (192.0.2.x / 198.51.100.x / 203.0.113.x) which can never route to a real
# machine, so a demo finding can never be mistaken for a live one.
DEMO_DIR = Path(os.environ.get("DEMO_DIR", "/data/demo"))
DEMO_COMPANY = "Trojan Empire"
DEMO_NOTICE = ("All results on this page are FABRICATED. Trojan Empire is a fictional company; "
               "every host, certificate, CVE and euro figure is invented to demonstrate the format "
               "of the deliverable. Nothing was scanned and no real organisation is described.")


def _demo_ready() -> bool:
    return DEMO_DIR.exists() and any(DEMO_DIR.glob("*.pptx"))


_DEMO_LOCK = threading.Lock()


def _ensure_demo() -> bool:
    """Build the demo artifacts once. Idempotent, serialised and best-effort.

    The LOCK is load-bearing, not decoration: /api/demo is public, so N simultaneous visitors on a
    cold volume would otherwise each fork node and write the same four files concurrently — a
    half-written .pptx served to the visitor who arrived second. One builder, everyone else waits,
    and the double-check inside the lock means the wait is a no-op once the first has finished.
    """
    if _demo_ready():
        return True
    with _DEMO_LOCK:
        if _demo_ready():
            return True
        try:
            DEMO_DIR.mkdir(parents=True, exist_ok=True)
            r = subprocess.run([sys.executable,
                                os.path.join(os.path.dirname(ENGINE), "demo_build.py"),
                                "--out", str(DEMO_DIR)],
                               capture_output=True, text=True, timeout=300)
            if not _demo_ready():
                # A demo that silently fails to build looks identical to "no demo exists". Say so.
                _log(evt="demo_build", result="error", rc=r.returncode,
                     err=(r.stderr or r.stdout or "")[-300:])
        except Exception as e:
            _log(evt="demo_build", result="error", err=repr(e)[:200])
    return _demo_ready()


@app.on_event("startup")
async def _warm_demo():
    """Build the demo at boot, off the request path, so the first visitor never waits ~40s."""
    asyncio.get_event_loop().run_in_executor(None, _ensure_demo)


@app.get("/api/demo")
def demo_meta():
    """Everything the Demo page needs: the notice, the company, and the artifact list."""
    ready = _ensure_demo()
    decks = []
    if ready:
        decks = [{"name": p.name, "url": "/api/demo/deck/%s" % p.name}
                 for p in sorted(DEMO_DIR.glob("*.pptx"))]
        decks += [{"name": p.name, "url": "/api/demo/deck/%s" % p.name}
                  for p in sorted(DEMO_DIR.glob("*_Animated*.html"))]
    return {"company": DEMO_COMPANY, "fabricated": True, "notice": DEMO_NOTICE,
            "ready": ready, "decks": decks,
            "access_contact": "feranicus@s4biz.io",
            "access_note": ("Live assessments against your own estate are available to "
                            "Cybergod partners and licensed customers.")}


@app.get("/api/demo/deck/{name}")
def demo_deck(name: str):
    low = name.lower()
    if "/" in name or "\\" in name or ".." in name or not (low.endswith(".pptx") or low.endswith(".html")):
        raise HTTPException(status_code=400, detail="bad filename")
    _ensure_demo()
    path = DEMO_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="demo artifact not found")
    media = ("text/html" if low.endswith(".html")
             else "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    return FileResponse(str(path), media_type=media, filename=name,
                        content_disposition_type=("inline" if low.endswith(".html") else "attachment"))


def _deck_langs_mod():
    """The engine's deck_langs module, loaded once. Returns None if unavailable."""
    global _DECK_LANGS
    if _DECK_LANGS is None:
        try:
            import importlib.util as _ilu
            _p = os.path.join(os.path.dirname(ENGINE), "deck_langs.py")
            _s = _ilu.spec_from_file_location("deck_langs", _p)
            _m = _ilu.module_from_spec(_s)
            _s.loader.exec_module(_m)
            _DECK_LANGS = _m
        except Exception:
            _DECK_LANGS = False
    return _DECK_LANGS or None


_DECK_LANGS = None


def doc_lang(requested, fallback=None):
    """Coerce a requested document language to one the ENGINE can actually render.

    THE BUG THIS REPLACES, and it is the whole reason Russian decks came out English:
        lang = doc_lang(req.lang)
    That line appeared FIVE times (assess, assess-refine, compliance, compliance-refine, and again
    in store.create_job). It hard-codes a two-language world, so `ru` was flattened to `en` at the
    API boundary — before the engine, which had just been generalised to N languages, ever saw it.
    The run log said `"lang": "en"` and the filenames carried no `_RU` suffix; the engine was
    innocent. Generalising the engine while leaving the request path on a `de`-only ternary is the
    same defect class as a value having four homes: one of them stays stale and silently wins.
    deck_langs.supported() is the single authority — it derives the answer from the dictionaries
    and prompt blocks actually present, and fails closed to English."""
    want = str(requested or fallback or "en").strip().lower()[:2]
    m = _deck_langs_mod()
    return m.supported(want) if m else ("de" if want == "de" else "en")


_COMPLIANCE_ENRICH = None


def _compliance_mod():
    """The engine's compliance_enrich module, loaded once. Returns None if unavailable."""
    global _COMPLIANCE_ENRICH
    if _COMPLIANCE_ENRICH is None:
        try:
            import importlib.util as _ilu
            _p = os.path.join(os.path.dirname(ENGINE), "compliance_enrich.py")
            _s = _ilu.spec_from_file_location("compliance_enrich", _p)
            _m = _ilu.module_from_spec(_s)
            _s.loader.exec_module(_m)
            _COMPLIANCE_ENRICH = _m
        except Exception:
            _COMPLIANCE_ENRICH = False
    return _COMPLIANCE_ENRICH or None


def jurisdiction_ok(want):
    """Resolve a requested jurisdiction through the ENGINE's registry, never a list in this file.

    This exists because of the `ru` incident: the engine gained a capability, the API flattened it
    on the way in, and the whole feature was invisible from the web while every engine test passed.
    A capability is not shipped until the process that does the work will accept it, so the API asks
    the engine what it supports rather than keeping its own copy.
    """
    m = _compliance_mod()
    if not m:
        return ""
    return m.jurisdiction(want)[0]


@app.get("/api/jurisdictions")
def jurisdictions():
    """Which regime sets the compliance engine can actually grade. Public capability list.

    Derived from compliance_enrich.JURISDICTIONS on disk — a hardcoded list in the frontend would
    be a second source of truth and would drift the moment a jurisdiction is added.
    """
    m = _compliance_mod()
    if not m:
        return {"jurisdictions": [{"code": "EU", "label": "EU", "regimes": 3}], "default": "EU"}
    out = []
    for code in m.JURISDICTIONS:
        j = m.JURISDICTIONS[code]
        out.append({"code": code, "label": j["label"], "title": j["title"],
                    "regimes": len(j["regimes"]), "decks": len(j["decks"]) + 1,
                    "names": [m.FIXED[k]["name"] for k in j["regimes"] if k in m.FIXED]})
    return {"jurisdictions": out, "default": m.DEFAULT_JURISDICTION}


@app.get("/api/langs")
def langs():
    """Which languages the UI ships in, and which the DECK ENGINE can actually produce.

    These are DIFFERENT SETS and conflating them ships a lie. The interface now speaks six languages;
    a deck language additionally needs a `scripts/i18n/<lang>.json`, an i18n.py post-pass and a LANG_*
    prompt block in enrich.py — so today the decks are English and German only. Before this endpoint
    the Assess screen defaulted the document language from the SITE language, which meant an Italian
    reader silently sent `--lang it`, the engine fell back to English, and nothing said so.

    Derived from the dictionaries on disk (deck_langs.doc_langs()), never from a constant in the
    frontend: a hardcoded list in the UI is a second source of truth and would drift the moment a
    dictionary is added or removed. Public — it is a capability list, not configuration.
    """
    ui = ["en", "de", "it", "fr", "es", "pl"]
    try:
        _m = _deck_langs_mod()
        if _m:
            return {"ui": ui, "doc": _m.catalogue()}
        raise RuntimeError("deck_langs unavailable")
    except Exception:
        # Never fail the Assess screen over a capability probe: English always works.
        return {"ui": ui, "doc": [{"code": "en", "name": "English"}]}


@app.get("/api/diag")
def diag(request: Request):
    """What is ACTUALLY in force in this container — chain, detectors, budgets, engine hashes.

    Exists because the enrichment chain had FOUR possible homes (committed _FALLBACKS, compose
    `environment:`, .env ENRICH_MODELS, legacy .env ENRICH_MODEL) and answering "which model will
    run?" meant SSH-ing in and reading five files. Authenticated: it reports configuration and
    file hashes, which is operational detail, not public information.
    """
    email = _current_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        import importlib.util as _ilu
        _p = os.path.join(os.path.dirname(ENGINE), "engine_config.py")
        _s = _ilu.spec_from_file_location("engine_config", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)
        return _m.collect()
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e)}


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


def _enforce_quota(email: str) -> None:
    """Refuse to start a run once an evaluation account has used its allowance.

    The quota lives in colt_auth beside the allow-list, because "who may use this" and "how much"
    are the same question and answering them in two places is how they drift apart. Absent from the
    map = unlimited, so every existing user is unaffected.
    Enforced HERE, before the job row is created, so a refused attempt does not consume a slot and
    does not appear in History as a run that never happened. Refusal is a 429 with the numbers in
    it, not a generic error: the person should be able to see exactly where they stand.
    """
    try:
        import colt_auth
        cap = colt_auth.quota_for(email)
    except Exception:
        return                              # never let a quota lookup break an assessment
    if not cap:
        return
    used = store.count_jobs(email)
    if used >= cap:
        _log(evt="quota_exceeded", user=email, used=used, cap=cap)
        raise HTTPException(
            status_code=429,
            detail=("Assessment limit reached: %d of %d used. This is an evaluation account. "
                    "Contact feranicus@s4biz.io to raise the limit." % (used, cap)))
    if used + 1 == cap:
        _log(evt="quota_last", user=email, used=used + 1, cap=cap)


@app.post("/api/assess")
async def assess(req: AssessReq, request: Request):
    email = _require_email(request)
    company = (req.company or "").strip()
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    _enforce_quota(email)
    lang = doc_lang(req.lang)
    job_id = uuid.uuid4().hex
    _job_dir(email, job_id)  # pre-create owner-scoped dir
    store.create_job(job_id, email, company, lang)
    _log(evt="assess_request", user=email, company=company, job=job_id, lang=lang)
    try:
        from . import telemetry as _t2, notify as _n2
        _n2.notify_report(email, company, kind="security assessment", phase="started",
                          ip=_t2.client_ip(request), extra={"lang": lang, "job": job_id[:8]})
    except Exception:
        pass
    try:
        from . import telemetry as _t, alerts as _a
        _a.observe_assess(email, company, _t.client_ip(request))
    except Exception:
        pass
    # Start the engine NOW, server-side, detached from any HTTP connection.
    # It used to be the SSE generator that spawned the subprocess — so closing the tab, refreshing,
    # or a phone locking its screen cancelled the generator and killed a 5-minute run. The job is now
    # owned by the server; the stream is just a viewer.
    _ov = ["--allow-public-suffix"] if req.zone_survey else None
    asyncio.create_task(_run_job(job_id, email, company, lang, overrides=_ov))
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


async def _run_job(job_id: str, email: str, company: str, lang: str, overrides: list = None,
                   engine: str = None, seed_flag: str = "--seed"):
    """Own the engine run. Writes every line to <jobdir>/run.log and finalises the DB row.
    Nothing here depends on an HTTP client being connected.

    `engine`/`seed_flag` select which engine runs: the security engine (run_assessment.py, --seed) or
    the compliance engine (compliance_assess.py, --company). Both stream PROGRESS/JSON the same way and
    print "ASSESSMENT COMPLETE", so the shared SSE viewer + deck collection work for both.

    `overrides` are extra engine flags from the post-run clarification loop (a REFINE run). They are the
    sanctioned way scope changes after the first run — the operator asserted the fact."""
    engine = engine or ENGINE
    jobdir = _job_dir(email, job_id)
    logp = jobdir / "run.log"
    _RUNNING[job_id] = asyncio.current_task()

    def _w(line: str):
        try:
            with open(logp, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass

    if not Path(engine).exists():
        _w(json.dumps({"evt": "error", "message": f"engine not found at {engine}"}))
        store.finish_job(job_id, [], {}, status="error"); _RUNNING.pop(job_id, None); return

    cmd = ["python3", "-u", engine, seed_flag, company, "--outdir", str(jobdir), "--lang", lang]
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
        try:
            from . import notify as _n3
            _kind = "compliance assessment" if engine != ENGINE else "security assessment"
            _extra = {"files": len(decks), "lang": lang}
            for _k in ("critical", "high", "medium", "low"):
                if summary.get(_k) is not None:
                    _extra[_k] = summary.get(_k)
            _n3.notify_report(email, company, kind=_kind, phase="finished", extra=_extra)
        except Exception:
            pass
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
    lang = doc_lang(req.lang, parent.get("lang"))
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


# ---------------------------------------------------------------- COMPLIANCE MODULE ---
# NIS2 / Cyber Resilience Act / EU AI Act. Same shape as Assess: one company-name input -> the
# compliance engine (compliance_assess.py) produces 3 regime decks + a roadmap deck + an animated HTML
# report, then surfaces clarification questions the operator answers to refine scope. The shared
# streaming/status/deck/clarify endpoints are engine-agnostic (they read the job's run.log + jobdir);
# only START and REFINE need to know the engine, so only those are compliance-specific.

def _compliance_refine_flags(answers: dict) -> list:
    """Map compliance clarify answers (keyed by `maps_to`) into compliance_assess.py flags."""
    a = answers or {}
    flags: list = []
    sector = str(a.get("sector") or "").strip()
    if sector:
        flags += ["--sector", sector[:160]]
    size = str(a.get("size_band") or "").strip().lower()
    if size in ("micro", "small", "medium", "large"):
        flags += ["--size-band", size]
    if a.get("sells_digital_products") is not None:
        flags += ["--sells-digital", "yes" if a.get("sells_digital_products") in (True, "true", "yes", "on", 1, "1") else "no"]
    if a.get("builds_or_deploys_ai") is not None:
        flags += ["--builds-ai", "yes" if a.get("builds_or_deploys_ai") in (True, "true", "yes", "on", 1, "1") else "no"]
    for tok in _split_tokens(a.get("countries")):
        c = re.sub(r"[^A-Za-z]", "", tok).upper()[:2]
        if len(c) == 2:
            flags += ["--country", c]
    notes = str(a.get("notes") or "").strip()
    if notes:
        flags += ["--notes", notes[:2000]]
    return flags


@app.post("/api/compliance")
async def compliance(req: ComplianceReq, request: Request):
    email = _require_email(request)
    company = (req.company or "").strip()
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    _enforce_quota(email)          # Assess and Compliance share one allowance
    lang = doc_lang(req.lang)
    job_id = uuid.uuid4().hex
    _job_dir(email, job_id)
    store.create_job(job_id, email, company, lang)
    _log(evt="compliance_request", user=email, company=company, job=job_id, lang=lang)
    try:
        from . import telemetry as _t2, notify as _n2
        _n2.notify_report(email, company, kind="compliance assessment", phase="started",
                          ip=_t2.client_ip(request), extra={"lang": lang, "job": job_id[:8]})
    except Exception:
        pass
    try:
        from . import telemetry as _t, alerts as _a
        _a.observe_assess(email, company, _t.client_ip(request))
    except Exception:
        pass
    _j = jurisdiction_ok(req.jurisdiction)
    asyncio.create_task(_run_job(job_id, email, company, lang,
                                 overrides=(["--jurisdiction", _j] if _j else []),
                                 engine=COMPLIANCE_ENGINE, seed_flag="--company"))
    return {"job_id": job_id, "jurisdiction": _j}


@app.post("/api/compliance/{job_id}/refine")
async def compliance_refine(job_id: str, req: ComplianceRefineReq, request: Request):
    """Answer the compliance clarification questions -> a NEW child run, re-scoped with the
    operator-confirmed facts (which OVERRIDE the model's inference)."""
    email = _require_email(request)
    parent = store.get_job(job_id)
    if not parent or parent["email"] != email.lower():
        raise HTTPException(status_code=404, detail="job not found")
    flags = _compliance_refine_flags(req.answers)
    if not flags:
        raise HTTPException(status_code=400, detail="no changes supplied")
    company = parent.get("company") or ""
    lang = doc_lang(req.lang, parent.get("lang"))
    child_id = uuid.uuid4().hex
    cdir = _job_dir(email, child_id)
    store.create_job(child_id, email, company, lang)
    try:
        (cdir / "refine_request.json").write_text(
            json.dumps({"parent": job_id, "answers": req.answers, "flags": flags}, ensure_ascii=False),
            encoding="utf-8")
    except Exception:
        pass
    _log(evt="compliance_refine", user=email, company=company, job=child_id, parent=job_id,
         flags=len(flags))
    _j = jurisdiction_ok(req.jurisdiction)
    asyncio.create_task(_run_job(child_id, email, company, lang,
                                 overrides=(["--jurisdiction", _j] if _j else []) + flags,
                                 engine=COMPLIANCE_ENGINE, seed_flag="--company"))
    return {"job_id": child_id, "parent": job_id, "jurisdiction": _j}


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
# Keep this in step with App.jsx's <Route> list. It was already stale (impressum/contact were
# missing) — harmless only because _is_probe ALSO requires a probe hint, but a whitelist that does
# not list the real routes is a trap waiting for the first route whose name contains ".git" or "sh".
_APP_ROUTES = {"", "login", "app", "privacy", "impressum", "contact", "demo",
               "experience", "partners"}
_PROBE_HINT = (".php", ".asp", ".aspx", ".jsp", ".cgi", ".env", ".git", ".sql", ".bak", ".old",
               ".zip", ".tar", ".gz", ".yml", ".yaml", ".ini", ".conf", ".sh", ".py", ".rb",
               ".db", ".sqlite", ".pem", ".key", ".log", ".swp", ".htpasswd",
               "wp-", "wordpress", "phpmyadmin", "xmlrpc", "vendor/", "cgi-bin", "shell",
               "adminer", "solr", "actuator", "struts", "config.json", "credentials",
               "id_rsa", "backup", "dump")

# THE DOT-DIRECTORY GAP (found in production, 2026-07). A scanner asked for `/.svn/wc.db` and got
# 200 — because the old rule looked for the substring "/." while `strip("/")` had already removed
# the LEADING slash, so ".svn/wc.db" never matched. `.aws/credentials` and `.ssh/id_rsa` leaked the
# same way. These are the highest-value paths a scanner asks for: a readable .svn or .git working
# copy leaks SOURCE, .aws leaks cloud keys, .ssh leaks private keys.
# Any path SEGMENT beginning with a dot is a probe. We serve no dotfiles; /.well-known is exempt
# because ACME and security.txt legitimately live there.
_DOTSEG = re.compile(r"(?:^|/)\.[^/]")


def _is_probe(path: str) -> bool:
    p = path.lower().strip("/")
    if not p:
        return False
    root = p.split("/", 1)[0]
    if root in _APP_ROUTES:
        return False
    if p.startswith(".well-known/"):
        return False
    if _DOTSEG.search("/" + p):
        return True
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
        "<h1>cybergod.ai</h1>"
        "<p>Frontend build not found (webapp/frontend/dist). The API is live under /api/.</p>",
        status_code=200,
    )
