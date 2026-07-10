"""Central config for the Colt web app backend — everything from env (same names the bots use)."""
import os
from pathlib import Path

# --- repo layout (for the default local engine path) ---
# app/ -> backend/ -> webapp/ -> repo root
_APP_DIR   = Path(__file__).resolve().parent
BACKEND_DIR = _APP_DIR.parent
WEBAPP_DIR  = BACKEND_DIR.parent
REPO_ROOT   = WEBAPP_DIR.parent

# --- data / sessions ---
DATA_DIR = Path(os.getenv("DATA_DIR", str(BACKEND_DIR / "data")))
JOBS_DIR = Path(os.getenv("JOBS_DIR", str(DATA_DIR / "jobs")))

# --- auth / session ---
SESSION_SECRET       = os.getenv("SESSION_SECRET", "dev-insecure-change-me")
SESSION_COOKIE       = os.getenv("SESSION_COOKIE", "colt_session")
SESSION_MAX_AGE      = int(os.getenv("SESSION_MAX_AGE", str(60 * 60 * 12)))  # 12h
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").lower() in ("1", "true", "yes")
ALLOWED_EMAIL_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "colt.net")

# COLT_BOT_PASSWORD / GMAIL_SENDER / GMAIL_SA_B64 / REQUIRE_2FA are consumed directly by colt_auth.

# --- assessment engine (subprocess) ---
# In the container the engine lives at /opt/shodan-skill/scripts/run_assessment.py.
# Locally, default to the repo copy so `python -m app.main` works out of the box.
_DEFAULT_ENGINE = REPO_ROOT / "hermes-skills" / "shodan-assessment" / "scripts" / "run_assessment.py"
ENGINE = os.getenv("ENGINE", str(_DEFAULT_ENGINE))

# --- assistant (cassandra / DeepSeek on DO serverless) ---
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
ASSIST_MODEL    = os.getenv("ASSIST_MODEL", os.getenv("ENRICH_MODEL", "deepseek-3.2"))
ASSIST_FALLBACK = os.getenv("ASSIST_FALLBACK_MODEL", "openai-gpt-oss-120b")
ASSIST_TIMEOUT  = int(os.getenv("ASSIST_TIMEOUT", "60"))
ASSIST_MAX_TOKENS = int(os.getenv("ASSIST_MAX_TOKENS", "1200"))

# --- SPA (built frontend) ---
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(WEBAPP_DIR / "frontend" / "dist")))

# --- CORS (dev convenience; prod serves SPA same-origin) ---
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")

DATA_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)
