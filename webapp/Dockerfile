# ---- stage 1: build the React cabinet ----
FROM node:20-slim AS fe
WORKDIR /fe
COPY webapp/frontend/package.json webapp/frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY webapp/frontend/ ./
RUN npm run build

# ---- stage 2: FastAPI backend + the deck engine, serving the built SPA ----
FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl nodejs npm \
 && rm -rf /var/lib/apt/lists/*
# deck builders need pptxgenjs (same as assess-bot)
RUN mkdir -p /opt/node && cd /opt/node && npm init -y >/dev/null 2>&1 && npm install pptxgenjs@^4 --no-audit --no-fund
ENV NODE_PATH=/opt/node/node_modules
WORKDIR /app
COPY webapp/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir shodan mmh3 google-auth requests
COPY hermes-skills/shodan-assessment /opt/shodan-skill
COPY colt_auth.py /opt/colt_auth.py
COPY webapp/backend/app ./app
COPY --from=fe /fe/dist ./frontend_dist
ENV ENGINE=/opt/shodan-skill/scripts/run_assessment.py FRONTEND_DIST=/app/frontend_dist DATA_DIR=/data JOBS_DIR=/data/jobs
RUN mkdir -p /data/jobs
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
