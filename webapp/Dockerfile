# ---- stage 1: build the React cabinet ----
FROM node:20-slim AS fe
WORKDIR /fe
COPY webapp/frontend/package.json webapp/frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY webapp/frontend/ ./
# i18n GATE — it lives HERE, not in ship.py, and that is deliberate.
#
# The SSR audit needs esbuild, whose binary is a PER-PLATFORM optional dependency. The operator's
# node_modules is Linux-native (it is a shared folder), so on Windows the build fails with
# "@esbuild/win32-x64 could not be found" — a gate that cannot run on the machine that invokes it.
# This stage does a fresh `npm install` inside linux/amd64, so the toolchain is correct by
# construction and no operator setup exists to drift. A failure here fails the image, which fails
# the deploy: nothing broken can ship, and there is still exactly ONE command.
#
# `--check` fails if any of the six locales is incomplete; run_i18n_audit.mjs renders 13 pages x 6
# languages and fails on a raw dotted key in the DOM, a leaked undefined, an over-length tab label,
# or English function-word residue above 6% (i.e. sentences silently falling back).
# partners_gate.mjs compares all six /partners locales against the English reference (a translator
# can drop a column without breaking the build) and enforces the content rules, including the
# standing NO PRICES ON A PUBLIC PAGE rule, in every language.
RUN node tools/canvas_smoke.mjs public/defense.html 900 \
 && node tools/api_contract.mjs && node tools/header_layout.mjs \
    && node tools/contrast_gate.mjs && node tools/partners_gate.mjs \
    && node tools/i18n_catalogue.mjs --check && node tools/run_i18n_audit.mjs
RUN npm run build
# WHAT THE WORLD CAN READ. View-source cannot be disabled - it shows bytes the browser already
# has, and curl or DevTools give the same thing - so the only question that matters is what is in
# those bytes. This runs AFTER the build because it measures dist/, not the source: no source maps
# (a shipped .map hands over the entire original source), no secrets or droplet IPs in the bundle,
# no HTML comments in the shell (ours named the bot-gate mechanism and its file), and the JSON-LD
# must survive. Inside the image, so it runs on a toolchain that is correct by construction.
RUN node tools/shipped_shell.mjs

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
# THE BRAIN HAS TO BE IN THE CONTAINER THAT RUNS IT.
# perseus.py installs the package to /opt/perseus ON THE HOST, and then writes a systemd unit whose
# ExecStart is `docker exec colt-web python3 /opt/perseus/perseus/hub.py --cycle`. colt-web mounts
# only colt_webdata:/data and colt_events:/var/log/colt, so that path does not exist inside it and
# the daily cycle has failed with "No such file or directory" EVERY NIGHT since it was installed.
# That is why every project reports `enforcing cycle 0`: hub.cycle() increments to 1 on its first
# successful run, so cycle 0 means no cycle has ever completed, so publish() has never written a
# blocklist, so check() iterates an empty pattern list and allows everything on all five sites.
# The 4-model consensus, the promotion gate and the abuse reporting were all built and none of them
# has ever executed in production.
# Shipped in the IMAGE, like the engine above, so the artifact carries its own code and there is no
# host path to drift.
COPY perseus /opt/perseus/perseus
COPY colt_auth.py /opt/colt_auth.py
COPY user_store.py /opt/user_store.py
COPY webapp/backend/app ./app
COPY --from=fe /fe/dist ./frontend_dist
ENV ENGINE=/opt/shodan-skill/scripts/run_assessment.py FRONTEND_DIST=/app/frontend_dist DATA_DIR=/data JOBS_DIR=/data/jobs
RUN mkdir -p /data/jobs
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
