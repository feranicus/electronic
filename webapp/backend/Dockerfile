# Colt cyber pre-sales web app — FastAPI backend.
# Bundles the backend, colt_auth, and the deterministic assessment engine (recon + deck builders).
# The engine's decks are rendered by Node + pptxgenjs (same stack as assess-bot/Dockerfile).
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_PATH=/opt/node/node_modules \
    ENGINE=/opt/shodan-skill/scripts/run_assessment.py \
    DATA_DIR=/data \
    JOBS_DIR=/data/jobs \
    FRONTEND_DIST=/app/frontend/dist

# system deps: node/npm for the deck builders, ca-certs + curl
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl nodejs npm \
 && rm -rf /var/lib/apt/lists/*

# node runtime for pptxgenjs (matches assess-bot)
RUN mkdir -p /opt/node && cd /opt/node && npm init -y >/dev/null 2>&1 \
 && npm install pptxgenjs@^4 --no-audit --no-fund

WORKDIR /app

# backend python deps + the engine's own python deps (shodan recon)
COPY webapp/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir shodan mmh3 google-auth requests

# engine (recon + 3/4 deck generators) + shared auth module
COPY hermes-skills/shodan-assessment /opt/shodan-skill
COPY colt_auth.py /opt/colt_auth.py

# the backend app
COPY webapp/backend/app ./app

# built SPA (optional — tolerated if absent). Uncomment when the frontend is built:
# COPY webapp/frontend/dist ./frontend/dist

RUN mkdir -p /data/jobs
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
