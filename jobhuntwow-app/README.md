# JobHuntWOW — app v0.1

React cabinet + FastAPI backend. Hermes chat runs on **real Qwen** via DigitalOcean
Serverless Inference. LinkedIn scouting and the ATS Apply-Driver are wired as previews
(the agent core lands next, per the HLD/LLD).

## Run locally (Docker)
    cp .env.example .env      # put your doo_v1_... key in DO_INFERENCE_KEY
    docker compose up --build
    # app:  http://localhost:8090      api: proxied at /api

## Run locally (dev, hot reload)
    # backend
    cd backend && pip install -r requirements.txt && \
      DO_INFERENCE_KEY=doo_v1_... uvicorn app.main:app --reload
    # frontend (new terminal)
    cd frontend && npm install && npm run dev     # http://localhost:5173 (proxies /api)

## Deploy on your droplet (next to godeyes.ai)
1. Copy this folder to the droplet, put the key in `.env`.
2. `docker compose up -d --build`  (frontend published on :8090).
3. Add the block from `Caddy-snippet.txt` to /opt/videodead/Caddyfile, then
   `docker exec videodead-caddy-1 caddy reload --config /etc/caddy/Caddyfile`.
4. DNS: `CNAME app -> jobhuntwow.com`. Open https://app.jobhuntwow.com

## What's real vs preview in v0.1
- REAL: Hermes chat (streaming Qwen), model list from your key, connections store.
- PREVIEW: /api/scout (sample jobs), /api/apply (simulated step log). These are the
  extension points for the LinkedIn scout (reuse linkedin_verifier.py) and the
  Page-Agent ATS apply driver.

## Endpoints
GET  /api/health | GET /api/models | GET/POST /api/connections
POST /api/chat (stream) | POST /api/scout | POST /api/apply
