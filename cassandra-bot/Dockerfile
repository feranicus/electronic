# Cassandra — Colt AE assistant bot (Python, DeepSeek-backed, zero-trust).
# Ships Playwright/Chromium for the JS-render FALLBACK (cheap HTTP is tried first).
# Set ENABLE_BROWSER=0 in .env to disable the browser fallback (lighter, HTTP-only).
FROM python:3.12-slim
RUN pip install --no-cache-dir "python-telegram-bot>=21,<22" playwright \
 && playwright install --with-deps chromium
RUN pip install --no-cache-dir google-auth requests   # Gmail API (HTTPS) for OTP; separate layer keeps Chromium cached
COPY colt_auth.py /opt/colt_auth.py
COPY cassandra-bot/cassandra_bot.py /opt/cassandra_bot.py
CMD ["python3", "/opt/cassandra_bot.py"]
