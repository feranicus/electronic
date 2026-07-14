# JobHuntWOW app — project conventions for Claude / AI agents

## What this project is
The interactive JobHuntWOW cabinet: a **React (Vite)** front end + **FastAPI** back end. Hermes chat
runs on **real Qwen** via **DigitalOcean Serverless Inference** (OpenAI-compatible). Job Scout and the
ATS Apply-Driver are wired as endpoints; the heavy agent logic plugs in behind them.

This is a SEPARATE project from the Colt cyber pre-sales monorepo it was extracted from. It also has a
sibling repo, `jobhuntwow.com` (GitHub-Pages landing + Google-Apps-Script Gmail→Sheets tracker).
Do NOT reintroduce any Colt / Shodan / cybergod code here.

## Standing rules
1. **KISS.** Zero manual data entry is the product promise. Prefer automation + sane defaults over knobs.
2. **Secrets never in git.** `DO_INFERENCE_KEY` and any tokens live ONLY in `.env` (gitignored) or as
   deploy secrets. `.env.example` carries placeholders only.
3. **One input where possible.** The user gives intent (a chat message, a job query); the app resolves
   the rest.
4. **The LLM assists, it does not decide side effects.** Qwen writes text; deterministic code decides
   what gets stored, applied, or sent.
5. **Frontend renders safely.** Never render an unknown backend value straight into JSX — coerce to text
   (objects → readable string) so a shape change can't white-screen the cabinet.

## How it runs
- **Local:** `docker compose up --build` → app on `:8090`, backend proxied at `/api`.
- **Prod:** Docker on the droplet; the shared Caddy serves `app.jobhuntwow.com` → `frontend:80`; the
  frontend nginx proxies `/api` → `backend:8000`. See DEPLOY.md.

## API surface (keep stable)
`GET /api/health` · `GET /api/models` · `GET|POST /api/connections` · `POST /api/chat` (SSE stream) ·
`POST /api/scout` · `POST /api/apply`.

## Conventions
- Backend: Python 3.11+, FastAPI, `httpx` for the DO inference calls, JSON file store under `DATA_DIR`.
- Frontend: React + Vite, plain `fetch` in `src/api.js` with `credentials:'include'`.
- Adding a scout source = fill `backend/app/scout.py::search()`; keep the `{query,count,jobs,note}` shape.
- Adding an apply target = fill `/api/apply`; the agent must never auto-submit without an explicit user action.

## What NOT to do
- No secrets in git, no Colt/Shodan code, no breaking the `/api/*` contract the frontend depends on.
- Don't couple to the droplet's videodead stack beyond the one Caddy vhost + shared network.
