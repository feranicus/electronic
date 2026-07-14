"""jhw-agent — the LLM-driven browser agent (runs on the CANDIDATE's machine).

Replaces the brittle selector scraper. Uses `browser-use` to pursue a GOAL by reading each page
(accessibility tree + screenshot) and letting the LLM decide the next action. The LLM is served by
the DO models through the droplet proxy (see backend/app/proxy.py) — the DO key never lands here.

Two goals for V1:
    scrape  <job>   -> read a LinkedIn job posting, return structured JD JSON
    apply   <job>   -> drive LinkedIn Apply -> company ATS, fill, STOP at Review (human submits)

Usage:
    python agent.py scrape 4435446898 --out job.json
    python agent.py apply  4435446898        (V1 step 4 — fills through Review, never submits)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys

# browser-use ships its own Playwright integration; we feed it a stealth browser + our proxy LLM.
try:
    from browser_use import Agent, Browser, ChatOpenAI
except Exception as e:  # pragma: no cover
    sys.exit(
        "[ERR] browser-use not installed. It's in requirements.txt — run the Docker build, "
        f"or `pip install browser-use`. ({e})"
    )

# ---- config (all overridable via env / .env) ----
PROXY_BASE = os.getenv("JHW_PROXY_BASE", "http://localhost:8000/v1")  # droplet /v1 in prod
AGENT_TOKEN = os.getenv("AGENT_PROXY_TOKEN", "")                      # per-candidate token
COOKIES_PATH = os.getenv("LINKEDIN_COOKIES", "linkedin_cookies.json")
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")

JOB_URL = "https://www.linkedin.com/jobs/view/{job_id}/"


def parse_job_id(arg: str) -> str:
    m = re.search(r"(\d{6,})", arg)
    if not m:
        sys.exit(f"[ERR] Could not find a job id in '{arg}'")
    return m.group(1)


def _llm(role_alias: str) -> "ChatOpenAI":
    """A ChatOpenAI pointed at OUR proxy; the alias (jhw-driver/jhw-vision) is routed server-side."""
    if not AGENT_TOKEN:
        print("[WARN] AGENT_PROXY_TOKEN not set — the proxy will reject calls.", file=sys.stderr)
    return ChatOpenAI(model=role_alias, base_url=PROXY_BASE, api_key=AGENT_TOKEN or "none")


def _load_cookie_json() -> list[dict]:
    try:
        with open(COOKIES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[WARN] no cookies at {COOKIES_PATH} — LinkedIn will authwall.", file=sys.stderr)
        return []


async def _make_browser() -> "Browser":
    """Stealth Chromium with the candidate's LinkedIn session preloaded."""
    browser = Browser(
        headless=HEADLESS,
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    await browser.start()
    cookies = _load_cookie_json()
    if cookies:
        # browser-use exposes the Playwright context; add the real session cookies.
        ctx = browser.playwright_context
        norm = []
        ss = {"strict": "Strict", "lax": "Lax", "none": "None",
              "no_restriction": "None", "unspecified": "Lax", "": "Lax"}
        for c in cookies:
            if not c.get("name") or c.get("value") is None:
                continue
            norm.append({
                "name": c["name"], "value": c["value"],
                "domain": c.get("domain", ".linkedin.com"), "path": c.get("path", "/"),
                "expires": -1 if c.get("session") else c.get("expirationDate", c.get("expires", -1)),
                "httpOnly": c.get("httpOnly", False), "secure": c.get("secure", True),
                "sameSite": ss.get(str(c.get("sameSite", "")).lower().strip(), "Lax"),
            })
        await ctx.add_cookies(norm)
        print(f"[OK] loaded {len(norm)} LinkedIn cookies")
    return browser


SCRAPE_TASK = """Go to {url}. This is a LinkedIn job posting and you are logged in as the candidate.
Read the full job. Expand any 'see more' on the description. Then return ONLY a JSON object with:
  title, company, location, workplace_type (remote/hybrid/onsite if shown),
  apply_type ('easy_apply' if the button says Easy Apply, else 'external'),
  description (the full text of the role/responsibilities/requirements).
Do not invent fields. If something isn't shown, use an empty string."""

APPLY_TASK = """You are applying to the LinkedIn job at {url} on behalf of the candidate.
Steps: click Apply. If it routes to a company ATS (e.g. Workday) in a new tab, continue there.
Create or sign in to the candidate's account if required (ask the human for a password if needed).
Fill My Information, Experience, Education and screening questions from the candidate profile.
When a required field is missing from the profile, STOP and ask the human for it.
CRITICAL: fill everything up to the final Review page, then STOP. NEVER click the final Submit —
a human does that. Report the current state and what still needs review."""


async def run_scrape(job_id: str, out: str | None):
    url = JOB_URL.format(job_id=job_id)
    browser = await _make_browser()
    try:
        agent = Agent(task=SCRAPE_TASK.format(url=url), llm=_llm("jhw-driver"), browser=browser)
        history = await agent.run(max_steps=20)
        final = history.final_result() if hasattr(history, "final_result") else str(history)
        # try to parse the JSON the model returned
        data = None
        if final:
            m = re.search(r"\{.*\}", final, re.S)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    pass
        result = data or {"raw": final, "job_id": job_id, "url": url}
        result.setdefault("job_id", job_id)
        result.setdefault("url", url)
        print(json.dumps(result, indent=2, ensure_ascii=False)[:1500])
        if out:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"[OK] wrote {out}")
    finally:
        await browser.stop()


async def run_apply(job_id: str):
    url = JOB_URL.format(job_id=job_id)
    browser = await _make_browser()
    try:
        agent = Agent(task=APPLY_TASK.format(url=url), llm=_llm("jhw-driver"), browser=browser)
        history = await agent.run(max_steps=60)
        print(history.final_result() if hasattr(history, "final_result") else str(history))
    finally:
        await browser.stop()


def main():
    ap = argparse.ArgumentParser(description="jhw-agent — LLM-driven LinkedIn/ATS agent")
    ap.add_argument("goal", choices=["scrape", "apply"])
    ap.add_argument("job", help="LinkedIn job id or /jobs/view/ URL")
    ap.add_argument("--out", default="", help="write scrape JSON here")
    args = ap.parse_args()
    job_id = parse_job_id(args.job)
    if args.goal == "scrape":
        asyncio.run(run_scrape(job_id, args.out or None))
    else:
        asyncio.run(run_apply(job_id))


if __name__ == "__main__":
    main()
