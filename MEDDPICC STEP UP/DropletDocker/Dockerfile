# MEDDPICC STEP UP — Gmail API sender + cron (runs Mon & Fri on the droplet).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends cron tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY send.py recipients.json /app/

# Cron schedule (Mon & Fri 09:00, container TZ). System-cron format (has the user field).
COPY crontab /etc/cron.d/meddpicc
RUN chmod 0644 /etc/cron.d/meddpicc

# Dump env for cron jobs, then run cron in the foreground so the container stays up.
CMD ["bash","-lc","printenv | grep -E 'SENDER|REPLY_TO|CC|ATTACHMENT|TOKEN_FILE|RECIPIENTS_FILE|GO_LIVE|TEST_EMAIL|SENDER_NAME|TZ' > /etc/environment && cron -f"]
