# LinkedIn Stakeholder Verifier — Read First

Production-grade Playwright scraper for verifying LinkedIn (and Xing) profiles of EDS event stakeholders.

## Honest risk disclosure

LinkedIn's User Agreement (§8.2) prohibits scraping. This tool uses anti-detection techniques (stealth JS, human-like timing, session reuse, challenge detection) to minimise detection risk, but **cannot eliminate it**. Possible outcomes:

- **Most likely:** small batches (under ~40 profiles/day) run clean
- **Possible:** LinkedIn temporary rate-limit (captcha, 24h ban) → tool detects it, pauses, alerts you
- **Worst case:** permanent account restriction on the account whose cookies you use

**Recommendation:** do NOT use your primary/personal LinkedIn. Use a secondary account if possible, or accept the risk consciously. This is standard LinkedIn scraping guidance — not paranoia.

## Design choices (compared to the Oxford scraper)

| Feature | Oxford scraper | LinkedIn verifier |
|---|---|---|
| Delay between requests | 1.5–3.0s random | **2.25–4.5s random** (1.5× Oxford) |
| Long break pattern | none | every 15 profiles, 60–180s pause |
| Browser | requests (HTTP) | **Playwright Chromium, headless=False** |
| Session | cookie-less | **user's real session via cookies.json** |
| Human simulation | none | **mouse movement, scroll, variable timing** |
| Fingerprint spoofing | N/A | **navigator.webdriver removed, plugins, WebGL, UA rotation** |
| Challenge detection | N/A | **URL + content pattern match, 10-min human-solve pause** |
| Checkpoint/resume | yes | **yes** (JSON, saved after every profile) |

## Setup

```bash
# 1. Create a virtualenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install
pip install playwright beautifulsoup4 openpyxl python-Levenshtein rich
playwright install chromium

# 3. Export your LinkedIn cookies
#    - Install a browser extension: "Get cookies.txt LOCALLY" (Chrome/Firefox, open-source)
#    - Log in to linkedin.com
#    - Click the extension → Export → JSON format
#    - Save the exported file as linkedin_cookies.json next to this script

# 4. Prepare input Excel
#    Use the CIOX_Germany_2026_EDS_Stakeholders_*.xlsx file — it has a "Master List" sheet
```

## Run

```bash
# Test with first 5 stakeholders (do this FIRST to sanity-check cookies + detection)
python linkedin_verifier.py --input CIOX_Germany_2026_EDS_Stakeholders_v2_Verified.xlsx \
                             --output verified.xlsx --test 5

# Full run
python linkedin_verifier.py --input CIOX_Germany_2026_EDS_Stakeholders_v2_Verified.xlsx \
                             --output verified.xlsx

# Resume after interruption (uses verifier_checkpoint.json)
python linkedin_verifier.py --input ... --output ...   # just re-run, it skips done

# Reset checkpoint and start over
python linkedin_verifier.py --input ... --output ... --reset
```

## What happens on a challenge

If LinkedIn shows a security check:
1. Script detects it via URL pattern + page content
2. Logs `[CHALLENGE]`, pauses 10 minutes
3. **The browser stays open on your screen** — solve the captcha manually
4. Script continues once the pause ends

If you get banned mid-run: the checkpoint is safe. Fix the cookies (login again, re-export) and `--resume` (i.e., just re-run).

## Output

`verified.xlsx` has columns:
- Status: `verified` (confidence ≥ 0.70) / `candidate` (0.50–0.70) / `not_found` / `challenge` / `error`
- Confidence (0–1): weighted name 50% + company 25% + title 25% Levenshtein similarity
- LinkedIn URL, Matched Name, Matched Title, Matched Company
- Xing URL (fallback if LinkedIn didn't verify)
- Notes, Attempted At timestamp

**Spot-check everything labelled "candidate"** — these are moderate matches that need your eyeball before outreach.

## Logs

- `verifier.log` — full run log with timestamps
- `verifier_checkpoint.json` — per-profile state

## Legal / ToS caveat

This tool violates LinkedIn's ToS. Use at your own risk. For production prospecting that doesn't violate ToS, consider:
- LinkedIn Sales Navigator + manual research
- Apollo.io / Cognism / ZoomInfo (licensed data)
- Google `site:linkedin.com` searches (what this project's "verified manually" column uses)
