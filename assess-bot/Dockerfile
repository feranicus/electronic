# Dedicated Colt assessment Telegram bot — NO LLM. Runs the deterministic engine.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl nodejs npm python3-pip \
 && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/node && cd /opt/node && npm init -y >/dev/null 2>&1 && npm install pptxgenjs@^4 --no-audit --no-fund
ENV NODE_PATH=/opt/node/node_modules
RUN pip3 install --no-cache-dir --break-system-packages shodan python-telegram-bot
RUN pip3 install --no-cache-dir --break-system-packages google-auth requests
# engine (recon + 3 deck generators) + the bot
COPY hermes-skills/shodan-assessment /opt/shodan-skill
COPY colt_auth.py /opt/colt_auth.py
COPY assess-bot/bot.py /opt/bot.py
RUN mkdir -p /root/work
CMD ["python3", "/opt/bot.py"]
