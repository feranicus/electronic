# jhw-agent

The **LLM-driven** local browser agent. Runs on the candidate's machine (residential IP, their real
logged-in LinkedIn session) — never in the cloud. See `../V1-PLAN.md` §1 and §4.

It does **not** use hardcoded selectors. At each step it reads the page and asks an LLM (a DO
Serverless model, reached through the droplet proxy) for the next action. The same agent therefore
handles LinkedIn *and* every ATS (Workday, SuccessFactors, Personio…).

- `agent.py` — the real agent (`browser-use` + Playwright). **Primary.**
- `scrape_job.py` — the old selector-only scraper. Kept only as a fast-path/debug reference.

## How the brains are reached
The agent never holds your DO billing key. It points at the backend's OpenAI-compatible proxy
(`/v1`), which injects the DO key and routes each request by role (`jhw-driver`, `jhw-content`…).
So you need the backend running (locally or on the droplet) and a shared `AGENT_PROXY_TOKEN`.

## Setup
1. **LinkedIn cookies** — export your logged-in session (a "Cookie-Editor"/"Get cookies.txt"
   extension, JSON) and save here as `linkedin_cookies.json`. Reuse the one you already have:
   ```bash
   cd "/mnt/c/Python SW/Linkedin Scraper/jobhuntwow-app/agent"
   cp "/mnt/c/Python SW/Linkedin Scraper/linkedin_cookies.json" ./linkedin_cookies.json
   ```
2. **Config** — `cp .env.example .env`, set `AGENT_PROXY_TOKEN` (must match the backend) and
   `JHW_PROXY_BASE` (`http://localhost:8000/v1` local, `https://app.jobhuntwow.com/v1` prod).

## Run — backend first (holds the DO key + proxy)
```bash
cd "/mnt/c/Python SW/Linkedin Scraper/jobhuntwow-app"
cp .env.example .env      # set DO_INFERENCE_KEY and AGENT_PROXY_TOKEN
docker compose up --build backend    # backend on :8000, proxy at /v1
```

## Run — the agent (Docker)
```bash
cd "/mnt/c/Python SW/Linkedin Scraper/jobhuntwow-app/agent"
mkdir -p out
docker compose build
docker compose run --rm agent scrape 4435446898 --out /out/job.json   # read the Red Hat JD
docker compose run --rm agent apply  4435446898                       # fill Workday -> STOP at Review
```
`apply` fills everything up to the final Review page and **stops** — a human clicks Submit.

## Note on browser-use version
`browser-use` moves fast; the `Agent`/`Browser`/`ChatOpenAI` import paths and the cookie-injection
accessor may differ slightly by version. If the first run throws an ImportError or an attribute
error on `browser.playwright_context`, tell me the version (`pip show browser-use`) and I'll pin the
exact binding — it's a small adjustment, isolated to `agent.py`.

## Env
| var | default | meaning |
|---|---|---|
| `JHW_PROXY_BASE` | `http://localhost:8000/v1` | where the OpenAI-compatible proxy lives |
| `AGENT_PROXY_TOKEN` | — | shared token the proxy checks (matches backend) |
| `LINKEDIN_COOKIES` | `linkedin_cookies.json` | candidate's exported session |
| `HEADLESS` | `false` | run Chromium headless |
