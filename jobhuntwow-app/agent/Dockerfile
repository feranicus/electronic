# jhw-agent — runs on the CANDIDATE's machine (residential IP, their LinkedIn session).
# Playwright's image ships Chromium + all system deps.
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /agent
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stealth.py scrape_job.py agent.py ./

# Cookies, .env and output are mounted at runtime, never baked in.
ENTRYPOINT ["python", "agent.py"]
