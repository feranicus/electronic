# Pre-Test Runbook — LinkedIn Verifier

## Before running the command

### 1. Refresh your LinkedIn cookies (CRITICAL)

Your exported cookies have `li_g_recent_logout=v=1&true` set — meaning your browser registered a logout event. The cookies may be stale. **Do this before running the script:**

1. Open Chrome/Edge, go to `https://www.linkedin.com/feed/`
2. Verify you can see your LinkedIn feed (not login page)
3. Re-export cookies using "Get cookies.txt LOCALLY" extension → JSON format
4. Replace `linkedin_cookies.json` in `C:\Python SW\Linkedin Scraper\`

**Alternatively:** Run the script with current cookies — the new preflight check will detect stale cookies, open a browser window, and let you log in manually. Save cookies automatically for next run.

### 2. Install dependencies (once)

```powershell
cd "C:\Python SW\Linkedin Scraper"
pip install playwright beautifulsoup4 openpyxl python-Levenshtein rich
playwright install chromium
```

### 3. Verify the input file is accessible

```powershell
dir "C:\Python SW\Linkedin Scraper\CIOX_Germany_2026_EDS_Stakeholders_v2_Verified.xlsx"
```

## Run command (paths with spaces — must be quoted)

```powershell
cd "C:\Python SW\Linkedin Scraper"

# Test mode — 5 profiles only
python linkedin_verifier.py --input "CIOX_Germany_2026_EDS_Stakeholders_v2_Verified.xlsx" --output "verified.xlsx" --test 5
```

**Do NOT use the backslash line-continuation (`\`) from the README — that's Linux syntax.** On PowerShell, use backtick (`` ` ``) or keep it on one line.

## What to watch for during the test

### On the terminal

- `[OK] Loaded N cookies` — good, cookies parsed
- `[Preflight] Checking login status...` — new preflight step
- `[OK] Logged in — cookies are valid.` — green light
- `⚠ Cookies are stale...` — the browser will open, log in manually, press Enter
- `selector matched: ...` — found the search result
- `[CHALLENGE] Detected` — LinkedIn put up a captcha. Solve it in the browser window that's open. Script auto-resumes after 10 min.

### In the browser window (headless=False on purpose)

You'll see a real Chromium browser open. **Do not close it.** Watch it navigate — if you see captcha, solve it manually.

### In the output file

After test completes, open `verified.xlsx`:
- `Status: verified` with green fill → confidence ≥0.70, URL confirmed
- `Status: candidate` with yellow fill → moderate match, spot-check the LinkedIn URL
- `Status: not_found` with red fill → no match. Check `Notes` column.
- `Status: challenge` → you hit a captcha mid-profile. Re-run, it resumes from checkpoint.

## Debugging if test fails

### "Cookies loaded 0" or similar
Open `linkedin_cookies.json` in a text editor. If it's a dict/object instead of array `[...]`, the export format is wrong. Re-export with "Get cookies.txt LOCALLY" extension in JSON mode.

### "Preflight: Cookies stale" every time
- Your LinkedIn account may have a flagged session
- Log in manually in the browser window when prompted
- The script will re-save fresh cookies

### "No results in people search" on every profile
- Selectors may have broken. Check `debug_no_results_*.html` files the script drops in the run folder
- Send one of those to me and I'll update selectors

### Browser won't launch / Chromium missing
```powershell
playwright install chromium --with-deps
```

## What the 5 test profiles will be

Based on sort order (1:1 meetings first, then tier, then company, then last name), the first 5 stakeholders processed will be from the 1:1 meeting list — these are your highest-priority verifications anyway. Good test cases because 3 of them should already match your pre-verified profiles (Zhitenev, Gerardin/Braconi, Knebel).

## After successful test

```powershell
# Full run on all 63 profiles
python linkedin_verifier.py --input "CIOX_Germany_2026_EDS_Stakeholders_v2_Verified.xlsx" --output "verified.xlsx"
```

Estimated runtime: 45–90 minutes depending on challenges. Checkpoint saves after each profile, so you can Ctrl+C and resume anytime.
