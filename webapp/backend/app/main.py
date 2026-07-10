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
from .auth import AUTH, make_session, read_session, email_ok
from .settings import (
    ENGINE, JOBS_DIR, FRONTEND_DIST, SESSION_COOKIE, SESSION_MAX_AGE,
    SESSION_COOKIE_SECURE, CORS_ORIGINS,
)

app = FastAPI(title="Colt Cyber Pre-Sales API", version="1.0.0")

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
def auth_begin(req: BeginReq):
    email = (req.email or "").strip().lower()
    # colt_auth.begin uses email as the uid; it also does the strict regex + password check.
    state, message = AUTH.begin(email, email, req.password or "")
    return {"state": state, "message": message}


@app.post("/api/auth/verify")
def auth_verify(req: VerifyReq):
    email = (req.email or "").strip().lower()
    ok, message = AUTH.verify(email, (req.code or "").strip())
    if not ok:
        return JSONResponse({"ok": False, "message": message})
    resp = JSONResponse({"ok": True, "email": email})
    _set_session_cookie(resp, email)
    return resp


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
def assess(req: AssessReq, request: Request):
    email = _require_email(request)
    company = (req.company or "").strip()
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    job_id = uuid.uuid4().hex
    _job_dir(email, job_id)  # pre-create owner-scoped dir
    store.create_job(job_id, email, company)
    return {"job_id": job_id}


def _deck_entry(job_id: str, path: Path) -> dict:
    return {"name": path.name, "url": f"/api/assess/{job_id}/deck/{path.name}"}


def _collect_decks(job_id: str, jobdir: Path) -> list:
    return [_deck_entry(job_id, p) for p in sorted(jobdir.glob("*.pptx"))]


async def _assess_stream(job_id: str, email: str):
    """Async generator yielding SSE `data:` frames from the engine subprocess."""
    job = store.get_job(job_id)
    if not job or job["email"] != email.lower():
        yield _sse({"evt": "error", "message": "job not found"})
        return

    jobdir = _job_dir(email, job_id)
    company = job["company"]

    if not Path(ENGINE).exists():
        store.finish_job(job_id, [], {}, status="error")
        yield _sse({"evt": "error", "message": f"engine not found at {ENGINE}"})
        return

    cmd = ["python3", ENGINE, "--seed", company, "--outdir", str(jobdir)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ},
        )
    except Exception as e:  # pragma: no cover
        store.finish_job(job_id, [], {}, status="error")
        yield _sse({"evt": "error", "message": f"failed to start engine: {e!r}"})
        return

    lines = []
    summary = {}
    completed = False
    assert proc.stdout is not None
    async for raw in proc.stdout:
        line = raw.decode("utf-8", "ignore").rstrip()
        if not line:
            continue
        lines.append(line)
        # capture the structured summary event
        if line.startswith("{"):
            try:
                o = json.loads(line)
                if isinstance(o, dict) and o.get("evt") == "assess_done":
                    summary = {
                        "company": o.get("company", company),
                        "critical": o.get("crit", 0),
                        "high": o.get("high", 0),
                        "medium": o.get("med", 0),
                        "low": o.get("low", 0),
                        "decks": o.get("decks", 0),
                        "qwen_used": o.get("qwen_used", False),
                    }
            except Exception:
                pass
        if "ASSESSMENT COMPLETE" in line:
            completed = True
        yield _sse({"evt": "progress", "line": line})

    await proc.wait()

    if not completed:
        store.finish_job(job_id, [], summary, status="error")
        tail = "\n".join(lines[-15:]) or "no output"
        yield _sse({"evt": "error", "message": "assessment failed", "detail": tail})
        return

    decks = _collect_decks(job_id, jobdir)
    store.finish_job(job_id, decks, summary, status="done")
    yield _sse({"evt": "done", "decks": decks, "summary": summary})


def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj) + "\n\n"


@app.get("/api/assess/{job_id}/events")
async def assess_events(job_id: str, request: Request):
    email = _require_email(request)
    return StreamingResponse(
        _assess_stream(job_id, email),
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
    # prevent path traversal — only a bare filename, must be a .pptx in the owner's jobdir
    if "/" in name or "\\" in name or ".." in name or not name.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="bad filename")
    jobdir = _job_dir(email, job_id)
    path = jobdir / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="deck not found")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=name,
    )


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
    index = _DIST / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    # tolerate dist/ being absent during dev
    return HTMLResponse(
        "<h1>Colt Cyber Pre-Sales</h1>"
        "<p>Frontend build not found (webapp/frontend/dist). The API is live under /api/.</p>",
        status_code=200,
    )
