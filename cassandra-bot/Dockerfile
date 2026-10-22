# Cassandra — Colt AE assistant bot (Python, DeepSeek-backed, zero-trust).
# Ships Playwright/Chromium for the JS-render FALLBACK (cheap HTTP is tried first).
# Set ENABLE_BROWSER=0 in .env to disable the browser fallback (lighter, HTTP-only).
FROM python:3.12-slim
# Pinned manifest, not package names — see cassandra-bot/requirements.txt for why.
COPY cassandra-bot/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && playwright install --with-deps chromium
COPY colt_auth.py /opt/colt_auth.py
COPY user_store.py /opt/user_store.py
COPY cassandra-bot/cassandra_bot.py /opt/cassandra_bot.py
CMD ["python3", "/opt/cassandra_bot.py"]
