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

from fastapi import FastAPI, Request, Response, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    JSONResponse, StreamingResponse, FileResponse, HTMLResponse, PlainTextResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import store, assistant, brand
from .auth import AUTH, make_session, read_session, email_ok, _log
# IMPORTED AFTER .auth ON PURPOSE: importing .auth is what puts the repo root (local dev) and /opt
# (container) on sys.path, so these two resolve in both places. Moving this line above it would
# work on the developer's machine and fail inside the image.
import colt_auth      # noqa: E402  — the shared gate: allow-list, admin list, password_ok
import user_store     # noqa: E402  — per-user credentials, shared with the Telegram bots
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

    # AFTER telemetry ON PURPOSE. Starlette makes the LAST middleware added the OUTERMOST, so
    # this one wraps the telemetry middleware and therefore also decorates the 404s that the
    # shield and the bot gate return before the app is ever reached. Installed first, it would
    # have left every blocked-scanner response bare. Asserted by tests/test_security_headers.py.
    from . import security_headers as _sec
    _sec.install(app)

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

        # TWO LOOPS, AND SPLITTING THEM IS THE POINT.
        # The first version applied the operator's Telegram taps inside the SIX-HOURLY panel loop.
        # So he tapped "Hold 24h", the bot said "Applying", and the confirmation that anything had
        # actually happened could be six hours away. A button that reports success and then goes
        # quiet for a working day is worse than no button: the next time it matters he will not
        # trust it. Applying a decision is a small file read; deliberating with four models is
        # expensive. They do not belong on the same clock.
        async def _decisions_loop():
            every = max(5, int(os.environ.get("SHIELD_APPLY_EVERY_S", 20)))
            while True:
                await _aio.sleep(every)
                try:
                    from . import shield, shield_console
                    shield_console.apply_decisions(shield)
                except Exception as exc:
                    print('{"evt":"shield_apply_error","err":"%s"}' % repr(exc)[:160], flush=True)

        async def _panel_loop():
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

        async def _digest_loop():
            """The DAILY digest: attacks per day, and what we could NOT classify.

            This is a different question from the panel's. The panel reviews decisions the shield
            already made, so it only ever sees traffic the detector understands; a genuinely new
            technique scores nothing, is never blocked, never becomes evidence, and is invisible
            exactly because it is new. attack_digest.unknowns() looks at the other side of that
            line. Once a day is the right cadence: a new scanner family is not an hourly event,
            and the four models cost tokens.
            """
            hour = max(0, min(23, int(os.environ.get("DIGEST_HOUR", 7))))
            while True:
                now = time.gmtime()
                secs = ((hour - now.tm_hour) % 24) * 3600 - now.tm_min * 60 - now.tm_sec
                await _aio.sleep(secs if secs > 60 else secs + 86400)
                try:
                    from . import attack_digest as _ad
                    await _aio.get_event_loop().run_in_executor(None, _ad.send, None)
                except Exception as exc:
                    print('{"evt":"digest_error","err":"%s"}' % repr(exc)[:160], flush=True)

        _aio.create_task(_decisions_loop())
        _aio.create_task(_panel_loop())
        _aio.create_task(_digest_loop())
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


class AdminUserReq(BaseModel):
    email: str
    password: str = ""        # blank -> the server generates one and returns it ONCE
    must_change: bool = True
    note: str = ""


class ChangePwReq(BaseModel):
    current_password: str = ""
    new_password: str


# ---------------- session helpers ----------------
def _current_email(request: Request):
    tok = request.cookies.get(SESSION_COOKIE)
    return read_session(tok) if tok else None


def _require_email(request: Request) -> str:
    email = _current_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="not authenticated")
    return email


def _must_change(email: str) -> bool:
    """Does this identity still owe us a password change?

    Read from the STORE on every request rather than trusted from the session cookie. A flag baked
    into the cookie at login would survive the change itself, and worse, would let an old cookie
    keep asserting a stale answer. The store is the only thing that knows.
    """
    try:
        import user_store
        rec = user_store.get(email)
        return bool(rec and rec.get("must_change"))
    except Exception:
        return False


def _require_ready(request: Request) -> str:
    """Authenticated AND not owing a password change.

    THIS IS THE ENFORCEMENT. Routing the browser to a change-password screen is presentation: the
    endpoints it would otherwise call are still reachable with curl and the session cookie. Every
    functional endpoint depends on THIS, so a user who has not set their own password cannot run an
    assessment, read history or download a deck no matter what client they use.
    """
    email = _require_email(request)
    if _must_change(email):
        raise HTTPException(status_code=403, detail="password_change_required")
    return email


def _require_admin(request: Request) -> str:
    """Authenticated, ready, AND on the committed administrator list.

    Checked here on the server for every administrative route. Hiding the menu item is not
    authorisation — anyone can issue the request the menu would have issued.
    """
    email = _require_ready(request)
    try:
        import colt_auth
        if colt_auth.is_admin(email):
            return email
    except Exception:
        pass
    _log(evt="admin_denied", user=email)
    raise HTTPException(status_code=403, detail="administrator access required")


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



@app.get("/api/siege")
def api_siege(since: int = None):
    """PUBLIC, REDACTED live attack feed for the siege page.

    Everything here is already anonymised by siege.record() on the way IN: addresses truncated to
    a /24, ordinary visitor traffic never recorded at all, paths echoed only when they match the
    probe corpus with no query string. No user, no session, no user agent.
    Cheap by construction: an in-memory ring buffer with a short snapshot cache, so a public
    endpoint cannot be used to make the server work.
    """
    from . import siege
    return siege.snapshot(since)

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
    is_admin = False
    try:
        import colt_auth
        is_admin = colt_auth.is_admin(email)
    except Exception:
        pass
    # `must_change` is advisory to the UI only. The refusal itself lives in _require_ready, so a
    # client that ignores this field gains nothing.
    return {"email": email, "is_admin": is_admin, "must_change": _must_change(email)}


# ---------------- password self-service ----------------
@app.post("/api/auth/change-password")
def change_password(req: ChangePwReq, request: Request):
    """Set your own password. Deliberately reachable while a change is OWED (it depends on
    _require_email, not _require_ready) or the forced-change state would be a locked door with no
    handle."""
    email = _require_email(request)
    new = (req.new_password or "").strip()
    if len(new) < user_store.MIN_PASSWORD_LEN:
        raise HTTPException(status_code=400,
                            detail="password must be at least %d characters" % user_store.MIN_PASSWORD_LEN)
    owed = _must_change(email)
    # PROVE IT IS STILL YOU. A session cookie is a bearer token: if it were enough on its own, a
    # borrowed laptop would be a password change. The one exception is the very first login on an
    # administrator-issued password, where the user has just proved the old password AND the OTP
    # minutes ago and is being forced to replace it.
    if not owed:
        ok, _ = colt_auth.password_ok(email, req.current_password or "")
        if not ok:
            _log(evt="password_change", user=email, result="bad_current")
            raise HTTPException(status_code=403, detail="current password is incorrect")
    try:
        user_store.set_password(email, new, must_change=False, by=email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _log(evt="password_change", user=email, result="ok", was_forced=owed)
    return {"ok": True}


# ---------------- administration ----------------
# Every route below depends on _require_admin. The committed list is colt_auth.ADMIN_EMAILS.
@app.get("/api/admin/users")
def admin_users(request: Request):
    """Everyone who can reach cybergod.ai, from all three sources that decide it.

    A list built only from the credential table would omit every user who signed in with the shared
    password, which is most of them today — and "who is registered" would then be a comforting
    subset rather than an answer.
    """
    _require_admin(request)
    accounts = {u["email"]: dict(u, source="assigned") for u in user_store.list_all()}
    # Everyone who has ever completed email + password + OTP. This is the de-facto register.
    for uid, rec in (getattr(AUTH, "authed", {}) or {}).items():
        e = (rec or {}).get("email") or uid
        e = str(e).strip().lower()
        if not e:
            continue
        row = accounts.setdefault(e, {"email": e, "must_change": False, "disabled": False,
                                      "created_ts": None, "updated_ts": None, "created_by": "",
                                      "note": "", "source": "self-served"})
        row["last_login_ts"] = (rec or {}).get("ts")
    out = []
    for e, row in accounts.items():
        row.setdefault("last_login_ts", None)
        row["has_password"] = row.get("source") == "assigned"
        row["is_admin"] = colt_auth.is_admin(e)
        row["allowed"] = colt_auth.email_allowed(e)
        row["quota"] = colt_auth.quota_for(e)
        try:
            row["assessments"] = store.count_jobs(e)
        except Exception:
            row["assessments"] = None
        out.append(row)
    out.sort(key=lambda r: (not r["is_admin"], r["email"]))
    return {"users": out, "store_ok": user_store.available(),
            "min_password_len": user_store.MIN_PASSWORD_LEN,
            "shared_password_active": bool(colt_auth.COLT_PW)}


@app.post("/api/admin/users")
def admin_create_user(req: AdminUserReq, request: Request):
    """Create an account or reset a password. The plaintext is returned HERE and nowhere else.

    It is not emailed: mailing a password puts it in two mailboxes and a transit log for as long as
    those exist, and the OTP already proves control of the mailbox, so mailing the password there
    would collapse two factors into one channel.
    """
    admin = _require_admin(request)
    email = (req.email or "").strip().lower()
    # NO ALLOW-LIST PRE-CHECK. Creating the account IS the act of authorisation: colt_auth
    # .email_allowed() treats an enabled row in the credential store as a source in its own right.
    # An earlier version refused any address outside the committed sets and told the operator to
    # edit colt_auth.PARTNER_EMAILS and redeploy first — which made this page unable to do the one
    # thing it exists for, and put the decision in two places with the newer one losing.
    # The address itself is still validated (user_store.set_password requires a real one), the
    # administrator is still authenticated and authorised, and the act is logged below with WHO
    # granted it. Revocation is disable or delete on this same screen.
    pw = (req.password or "").strip() or user_store.generate_password()
    try:
        rec = user_store.set_password(email, pw, must_change=bool(req.must_change),
                                      by=admin, note=(req.note or "").strip() or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _log(evt="admin_user_set", user=admin, target=email, must_change=bool(req.must_change))
    return {"ok": True, "user": rec, "password": pw}      # shown once, never stored


@app.post("/api/admin/users/{email}/disable")
def admin_disable(email: str, request: Request, disabled: bool = True):
    admin = _require_admin(request)
    target = (email or "").strip().lower()
    if disabled and colt_auth.is_admin(target):
        # Locking the last administrator out of the administration page is not a state anyone can
        # recover from through the product.
        raise HTTPException(status_code=400, detail="an administrator account cannot be disabled here")
    rec = user_store.set_disabled(target, disabled)
    if rec is None:
        raise HTTPException(status_code=404, detail="no assigned account for %s" % target)
    _log(evt="admin_user_disable", user=admin, target=target, disabled=disabled)
    return {"ok": True, "user": rec}


@app.delete("/api/admin/users/{email}")
def admin_delete(email: str, request: Request):
    """Remove the assigned password. NOTE this does not revoke access on its own: if the address is
    still on the allow-list it falls back to the shared password. The UI says so."""
    admin = _require_admin(request)
    target = (email or "").strip().lower()
    if colt_auth.is_admin(target):
        raise HTTPException(status_code=400, detail="an administrator account cannot be removed here")
    ok = user_store.delete(target)
    _log(evt="admin_user_delete", user=admin, target=target, existed=ok)
    return {"ok": ok}


# ---------------- White Label (Proteus) ----------------
# A partner uploads their own PowerPoint; we read the palette, fonts and logo out of it and every
# artifact they generate afterwards carries their design. Owner-scoped throughout: a brand belongs
# to the identity that uploaded it and there is no route that takes an email from the caller.
@app.get("/api/brand")
def brand_get(request: Request):
    email = _require_ready(request)
    t = brand.get(email)
    if not t:
        return {"active": False, "max_logo_kb": proteus_max_logo_kb()}
    return {"active": True, "brand": _brand_public(t), "max_logo_kb": proteus_max_logo_kb()}


def proteus_max_logo_kb():
    from proteus import MAX_LOGO_BYTES
    return MAX_LOGO_BYTES // 1024


def _brand_public(t):
    """What the cabinet may see. The panel's per-model votes are included deliberately — the
    partner should be able to read WHY their colour was chosen and disagree with it — but nothing
    here is a secret and nothing here is another user's."""
    return {k: t.get(k) for k in
            ("name", "wordmark", "palette", "palette_why", "fonts", "logo", "logo_w", "logo_h",
             "mode", "powered_by", "decided_by", "why", "votes", "warnings", "updated_ts",
             "has_logo")}


@app.post("/api/brand")
async def brand_set(request: Request,
                    template: UploadFile = File(None),
                    logo: UploadFile = File(None),
                    name: str = Form(""),
                    panel: str = Form("1"),
                    brand_light: str = Form(""),
                    brand_mid: str = Form(""),
                    brand_dark: str = Form(""),
                    heading: str = Form(""),
                    body: str = Form("")):
    email = _require_ready(request)
    # Read with a hard ceiling rather than trusting Content-Length: the cap has to be enforced on
    # the bytes we actually took, not on a number the client sent.
    from proteus import MAX_UPLOAD
    tpl = await template.read(MAX_UPLOAD + 1) if template is not None else None
    lg = await logo.read(MAX_UPLOAD + 1) if logo is not None else None
    for blob, what in ((tpl, "template"), (lg, "logo")):
        if blob is not None and len(blob) > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="%s is larger than %d MB"
                                % (what, MAX_UPLOAD // (1024 * 1024)))
    # RETURN IMMEDIATELY AND REPORT PROGRESS, rather than holding the request open.
    #
    # With the panel on, four models at a 45s timeout is up to a minute of wall clock even in
    # parallel, and a spinner that says nothing for a minute is indistinguishable from a hang. That
    # is the same lesson the assessment progress bar was built from: a long job with no visible
    # phase makes people refresh. The work is CPU/network-bound and synchronous, so it goes to a
    # worker thread; the event loop stays free to answer the poll.
    # The cheap refusals happen NOW, synchronously: a file that is not a presentation, or a logo
    # we will not accept, is answered with a 400 and a reason instead of becoming a job the
    # operator has to watch in order to learn it was never going to work.
    try:
        brand.precheck(tpl or None, lg or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _log(evt="brand_error", user=email, error=repr(e)[:200])
        raise HTTPException(status_code=400, detail="could not read that file: %r" % (e,))

    job = uuid.uuid4().hex[:12]
    st = {"pct": 0, "lines": [], "done": False, "error": "", "brand": None, "warnings": [],
          "user": email, "started": time.time()}
    _BRAND_JOBS[job] = st
    _brand_jobs_gc()

    def say(pct, msg):
        st["pct"] = max(st["pct"], int(pct))
        st["lines"].append({"pct": st["pct"], "msg": str(msg)[:300], "t": time.time() - st["started"]})
        del st["lines"][:-200]

    # The partner's own word about their palette. Everything the machine reads out of a deck is a
    # PROPOSAL; these fields are the human correcting it, and the same doctrine as the assessment's
    # clarify/refine loop applies — the assertion wins and is recorded. Validated in proteus, which
    # ignores anything that is not a six-digit hex, so a junk value cannot reach a slide.
    ov = {"brandLight": brand_light, "brandMid": brand_mid, "brandDark": brand_dark,
          "heading": heading, "body": body, "wordmark": name}
    ov = {k: v for k, v in ov.items() if str(v or "").strip()}

    def work():
        try:
            theme, warnings = brand.save(email, template=tpl or None, logo=lg or None,
                                         name=name, use_panel=str(panel) != "0", on=say,
                                         overrides=ov or None)
            st["brand"] = _brand_public(theme)
            st["warnings"] = warnings
            _log(evt="brand_set", user=email, name=theme.get("name", ""),
                 decided_by=theme.get("decided_by", ""), warnings=len(warnings))
        except ValueError as e:
            st["error"] = str(e)
            say(100, "refused: " + str(e))
        except Exception as e:
            st["error"] = "could not read that file: %r" % (e,)
            say(100, st["error"])
            _log(evt="brand_error", user=email, error=repr(e)[:200])
        finally:
            # ALWAYS. A job that never reports done leaves the page spinning for ever, which is the
            # exact defect this endpoint was rewritten to fix.
            st["pct"] = 100
            st["done"] = True

    asyncio.get_event_loop().run_in_executor(None, work)
    return {"ok": True, "job": job}


# In-memory and deliberately so: this is a 60-second progress feed, not a record. It is rebuilt on
# restart, and the THEME itself is already on disk by the time a job finishes — losing the progress
# of an in-flight upload costs a re-upload, while persisting it would be a second store to reason
# about for no benefit.
_BRAND_JOBS = {}


def _brand_jobs_gc():
    old = [k for k, v in _BRAND_JOBS.items() if time.time() - v.get("started", 0) > 1800]
    for k in old:
        _BRAND_JOBS.pop(k, None)


@app.get("/api/brand/job/{job}")
def brand_job(job: str, request: Request, since: int = 0):
    """Poll, not SSE, and that is a considered choice.

    The assessment stream is minutes long, resumable and survives a phone locking, which is what
    justifies EventSource plus Last-Event-ID plus a reconnect path. This is under a minute and the
    page is open in front of the person who started it. A poll every second has no reconnect
    semantics to get wrong, and `since` keeps each response to the new lines only.
    """
    email = _require_ready(request)
    st = _BRAND_JOBS.get(job)
    if not st:
        raise HTTPException(status_code=404, detail="no such upload")
    if st.get("user") != email:
        # Owner-scoped like everything else here: a job id is not an authorisation.
        raise HTTPException(status_code=404, detail="no such upload")
    return {"pct": st["pct"], "done": st["done"], "error": st["error"],
            "brand": st["brand"], "warnings": st["warnings"],
            "lines": st["lines"][max(0, int(since or 0)):], "total": len(st["lines"])}


@app.get("/api/brand/preview")
def brand_preview(request: Request, brand_light: str = "", brand_mid: str = "",
                  brand_dark: str = "", slide: int = 1):
    """The partner's own cover slide, as SVG, before anything is committed.

    NO EXTRACTOR IS RIGHT FOR EVERY DECK, and two wrong readings reached the operator before anyone
    looked at a slide: Microsoft's default blue on the first pass, and a synthesised dark fill within
    (1,-2,15) of the palette we had just retired on the second. The durable fix is not a cleverer
    heuristic, it is showing the artifact and letting a human say no.

    The three query parameters let the page preview an EDIT that has not been saved, so the loop is
    change -> look -> change, rather than save-and-hope. They go through proteus like any other
    override, which drops anything that is not a colour.
    """
    email = _require_ready(request)
    t = brand.get(email)
    if not t or t.get("broken"):
        raise HTTPException(status_code=404, detail="no brand to preview yet")
    ov = {"brandLight": brand_light, "brandMid": brand_mid, "brandDark": brand_dark}
    ov = {k: v for k, v in ov.items() if str(v or "").strip()}
    if ov:
        import proteus
        pal = dict(t.get("palette") or {})
        for k, v in ov.items():
            h = proteus._hex(v)
            if h:
                pal[k] = h
        # The ink is MEASURED against whatever they typed, here as everywhere else. Echoing back a
        # preview with white text on a colour that cannot carry it would be a lie in the one place
        # the partner is relying on us to be literal.
        pal["onBrandLight"] = proteus.ink_for(pal["brandLight"])
        pal["onBrandMid"] = proteus.ink_for(pal["brandMid"])
        pal["onBrandDark"] = proteus.ink_for(pal["brandDark"])
        t = dict(t, palette=pal)
    try:
        svg = brand.preview(email, theme=t, slide=max(1, min(int(slide or 1), 12)))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _log(evt="brand_error", user=email, error=repr(e)[:200])
        raise HTTPException(status_code=500, detail="the preview could not be rendered")
    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


@app.delete("/api/brand")
def brand_delete(request: Request):
    email = _require_ready(request)
    existed = brand.delete(email)
    _log(evt="brand_delete", user=email, existed=existed)
    return {"ok": True, "existed": existed}


@app.get("/api/brand/logo")
def brand_logo(request: Request):
    """The partner's own logo, to preview it. Owner-scoped: the path is derived from the SESSION,
    never from anything the caller sends, so there is no identifier to tamper with."""
    email = _require_ready(request)
    p = brand.logo_path(email)
    if not p:
        raise HTTPException(status_code=404, detail="no logo")
    return FileResponse(p, media_type="image/png",
                        headers={"Cache-Control": "no-store"})


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
    email = _require_ready(request)
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
    # THE RUN LOG, as a customer-readable txt. It is written by the engine from run.log with the
    # operator's email, our internal paths and the COST LEDGER stripped out. See
    # scripts/run_log.py for exactly what is removed and why: handing a customer the per-run AI
    # cost and the lifetime assessment count is worse than a privacy leak, it is a negotiating
    # position given away. The raw run.log is NEVER offered here.
    out += [_deck_entry(job_id, p) for p in sorted(jobdir.glob("*_Run_Log_*.txt"))]
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
            # BRAND_THEME -> White Label. Set HERE, once, for the whole engine run: every deck and
            # HTML builder is a subprocess of this one and inherits os.environ, so the five
            # artifacts cannot end up half-branded. Absent when the user has no brand, and the
            # builders then render exactly as they always did.
            env={**os.environ, "COLT_USER": email, **brand.env_for(email)})
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
        # THE CUSTOMER RUN LOG, written here rather than in the engine because the engine's stdout
        # IS run.log: it cannot read the file it is still writing. Redaction lives in the engine's
        # scripts/run_log.py so the rules travel with the engine and are tested with it.
        try:
            import importlib.util as _ilu
            _rl_path = os.path.join(os.path.dirname(ENGINE), "run_log.py")
            _spec = _ilu.spec_from_file_location("run_log", _rl_path)
            _rl = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_rl)
            _rl.write(logp.read_text(encoding="utf-8", errors="replace"), company, lang, str(jobdir))
        except Exception as _e:
            # A missing log must never fail a completed assessment. The decks are the deliverable.
            print('{"evt":"run_log_error","err":"%s"}' % repr(_e)[:140], flush=True)
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
    email = _require_ready(request)
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
    email = _require_ready(request)
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
    email = _require_ready(request)
    job = store.get_job(job_id)
    if not job or job["email"] != email.lower():
        raise HTTPException(status_code=404, detail="not found")
    # prevent path traversal — only a bare filename; allow the .pptx decks, the _Report.html,
    # and the GENERATED customer run log. `.txt` is gated on the _Run_Log_ marker on purpose:
    # run.log itself carries the operator's email on every line and must never be reachable here.
    low = name.lower()
    if ("/" in name or "\\" in name or ".." in name
            or not (low.endswith(".pptx") or low.endswith(".html")
                    or (low.endswith(".txt") and "_run_log_" in low))):
        raise HTTPException(status_code=400, detail="bad filename")
    jobdir = _job_dir(email, job_id)
    path = jobdir / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="deck not found")
    media = ("text/html" if low.endswith(".html")
             else "text/plain; charset=utf-8" if low.endswith(".txt")
             else "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    # HTML report and the run log open in the browser; decks download as attachments.
    disp = "inline" if (low.endswith(".html") or low.endswith(".txt")) else "attachment"
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
    email = _require_ready(request)
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
    email = _require_ready(request)
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
    email = _require_ready(request)
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
    email = _require_ready(request)
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
    email = _require_ready(request)
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
    _require_ready(request)
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
