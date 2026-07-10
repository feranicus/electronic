"""Auth glue: an in-memory colt_auth.Auth instance (email as uid) + signed session cookies.

colt_auth lives at the repo root locally, and at /opt/colt_auth.py inside the container.
We add both candidate locations to sys.path so `import colt_auth` works either way.
Session tokens are signed with itsdangerous (falls back to a plain HMAC signer if absent)."""
import os, sys, json, time, hmac, hashlib, base64
from pathlib import Path

from .settings import (
    DATA_DIR, SESSION_SECRET, SESSION_MAX_AGE, ALLOWED_EMAIL_DOMAIN, REPO_ROOT,
)

# --- locate colt_auth.py (repo root for local dev, /opt for container) ---
for _cand in (REPO_ROOT, Path("/opt"), Path(__file__).resolve().parent):
    if (_cand / "colt_auth.py").exists() and str(_cand) not in sys.path:
        sys.path.insert(0, str(_cand))
import colt_auth  # noqa: E402

# One shared Auth instance for the whole process (email is the uid).
_STORE_PATH = str(DATA_DIR / "web_authorized.json")


def _log(**k):
    k.setdefault("bot", "webapp")
    try:
        print(json.dumps(k), flush=True)
    except Exception:
        pass


AUTH = colt_auth.Auth("webapp", _STORE_PATH, log=_log)


def email_ok(email: str) -> bool:
    """Cheap domain guard before we even hit colt_auth (which does the strict regex + password)."""
    email = (email or "").strip().lower()
    return "@" in email and email.split("@", 1)[1] == ALLOWED_EMAIL_DOMAIN.lower()


# ---------------- signed session tokens ----------------
try:
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    _SER = URLSafeTimedSerializer(SESSION_SECRET, salt="colt-web-session")

    def make_session(email: str) -> str:
        return _SER.dumps({"email": email.lower()})

    def read_session(token: str):
        try:
            data = _SER.loads(token, max_age=SESSION_MAX_AGE)
            return (data or {}).get("email")
        except (BadSignature, SignatureExpired, Exception):
            return None

except Exception:  # pragma: no cover - itsdangerous should be installed
    def _sign(payload: str) -> str:
        sig = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return payload + "." + sig

    def make_session(email: str) -> str:
        body = base64.urlsafe_b64encode(
            json.dumps({"email": email.lower(), "ts": int(time.time())}).encode()
        ).decode()
        return _sign(body)

    def read_session(token: str):
        try:
            body, sig = token.rsplit(".", 1)
            exp = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(exp, sig):
                return None
            data = json.loads(base64.urlsafe_b64decode(body.encode()))
            if int(time.time()) - int(data.get("ts", 0)) > SESSION_MAX_AGE:
                return None
            return data.get("email")
        except Exception:
            return None
