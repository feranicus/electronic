# Dedicated Colt assessment Telegram bot — NO LLM. Runs the deterministic engine.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl nodejs npm python3-pip \
 && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/node && cd /opt/node && npm init -y >/dev/null 2>&1 && npm install pptxgenjs@^4 --no-audit --no-fund
ENV NODE_PATH=/opt/node/node_modules
# DEPENDENCIES COME FROM COMMITTED, PINNED MANIFESTS — never from package names on this line.
# A RUN line listing names is a cache key that never changes, so the layer stops re-resolving and
# the versions inside it freeze at whatever "latest" meant the day it was first built. That is how
# colttechbot shipped certifi 2026.7.22 into run #12's CRITICAL finding while colt-web, same
# sources same run, held 2026.10.19. The reasoning is written out in the engine manifest.
COPY hermes-skills/shodan-assessment/requirements.txt /tmp/engine-requirements.txt
COPY assess-bot/requirements.txt /tmp/bot-requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages \
      -r /tmp/engine-requirements.txt -r /tmp/bot-requirements.txt
# engine (recon + 3 deck generators) + the bot
COPY hermes-skills/shodan-assessment /opt/shodan-skill
COPY colt_auth.py /opt/colt_auth.py
COPY user_store.py /opt/user_store.py
COPY assess-bot/bot.py /opt/bot.py
RUN mkdir -p /root/work
CMD ["python3", "/opt/bot.py"]
