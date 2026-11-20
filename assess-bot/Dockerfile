# Dedicated Colt assessment Telegram bot — NO LLM. Runs the deterministic engine.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
# APT MUST RETRY, AND IT MUST SAY WHAT WENT WRONG.
#
# Run #<pipeline 19 Nov 2026> died here: `exit code 100`, after 17m04s, on a layer that takes
# under a minute when the mirror is healthy. Exit 100 is apt's generic "an error occurred" and
# carries no cause; the cause is on the `E:` lines, and seventeen minutes is the signature of
# fetch retries against a sick mirror rather than of a missing package, which fails in seconds.
# colt-web, built from the same sources in the same run, succeeded: it is python:3.12-slim and
# pulls from deb.debian.org, while this image is ubuntu:24.04 and pulls from the Ubuntu archive.
# Same minute, same runner, different mirror, different outcome.
#
# So: bound the retries instead of letting the default behaviour burn the job's clock, and make
# the failure name itself rather than leaving `exit code 100` as the whole report (class 26).
# This is NOT a claim that the mirror was the cause. It is the change that makes the next run
# either succeed or print the evidence to decide on.
RUN set -eu; \
    printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' \
      > /etc/apt/apt.conf.d/99-retries; \
    apt-get update 2>/tmp/apt.err || { echo "=== apt-get update failed ==="; cat /tmp/apt.err; exit 100; }; \
    apt-get install -y --no-install-recommends \
      ca-certificates curl nodejs npm python3-pip 2>/tmp/apt.err \
      || { echo "=== apt-get install failed ==="; cat /tmp/apt.err; exit 100; }; \
    rm -rf /var/lib/apt/lists/* /tmp/apt.err
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
