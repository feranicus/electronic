# v3 Workflow — What's New

## What's in v3

1. **`CIOX_Germany_2026_EDS_Stakeholders_v3_Verified.xlsx`** — consolidated master file
2. **`linkedin_verifier.py`** — extended with `--google-fallback` mode
3. **`debug_no_results_*.html`** files — can be deleted, they've been analysed

## Three key new things

### 1. Trip Report wins at the top

Sheet **"Executive Summary"** leads with Champion + 2 Cyber Opps (Audrey, Ofelia, Denesh). Sheet **"Priority Follow-Up"** lists them + all 1:1s in priority order.

### 2. New Tier 1 rule: only CxO / Director / Head of

**Tier 1 (44 people):** CEO/CIO/CTO/CISO/BISO/VP/MD/Director/Head of — plus 3 Trip-Report flagged.
**Tier 2 (8):** Architects, senior managers, portfolio managers — influencers but not final decision makers.
**Tier 3 (11):** AI researchers, legal, consultants — nurture only.

### 3. Verification status merged from scraper

The Master List LinkedIn column now shows:
- **VERIFIED** (green, 3 people): HIGH confidence cross-referenced via web search
- **SCRAPER-FOUND** / **CANDIDATE** (yellow, ~48 people): Playwright captured URL but didn't verify on profile page. **Spot-check before outreach.**
- **UNVERIFIED** (red, ~12 people): LinkedIn returned 0 results. Use Google Dork column.

## How to finish the verification — run Google fallback

Your scraper already ran and filled the checkpoint. The problem: LinkedIn returns "0 results" when you give it `"Full Name" "Long Company Name"` — so ~12 profiles came back `not_found` even though they exist.

**Google indexes LinkedIn profiles, tolerates bots much better.** New mode:

```powershell
cd "C:\Python SW\Linkedin Scraper"

# Run Google fallback on profiles that failed LinkedIn search
python linkedin_verifier.py --input "CIOX_Germany_2026_EDS_Stakeholders_v2_Verified.xlsx" --output "verified.xlsx" --google-fallback
```

This will:
- Skip anyone already verified or candidate
- For each `not_found` / unprocessed profile: search Google with `site:linkedin.com/in/ "Name" "Company"`
- If no hits, fall back to broader `site:linkedin.com/in/ "Name"`
- Extract top 5 linkedin.com/in/ URLs, score each against name+company+URL slug
- Save highest confidence to checkpoint + Excel

Timing: ~8-12 seconds per profile (Google is fast), probably 5-10 minutes total for all 12.

## After Google fallback is done

Re-run the build script to regenerate v3 with the new URLs:

Not needed — just tell me when you're done and upload the updated `verified.xlsx`, and I'll consolidate into v3 again.

OR, do the quick manual pass:

1. Open `CIOX_Germany_2026_EDS_Stakeholders_v3_Verified.xlsx`
2. Sheet **"Unverified — Google Search"**
3. Click the "Google (precise)" link for each row — Google opens in new tab
4. Copy the LinkedIn URL from top result back into Master List column S (LinkedIn URL)

For the 14 priority people (Champion + Cyber Opps + 1:1s) — do this before any outreach.

## Command summary

```powershell
# Check status anytime
python linkedin_verifier.py --input "...v2...xlsx" --status

# Standard run (LinkedIn search)
python linkedin_verifier.py --input "...v2...xlsx" --output "verified.xlsx"

# Retry candidates/not_founds on LinkedIn (second pass with improved logic)
python linkedin_verifier.py --input "...v2...xlsx" --output "verified.xlsx" --retry-failed

# Google fallback (recommended next step)
python linkedin_verifier.py --input "...v2...xlsx" --output "verified.xlsx" --google-fallback

# Reset from scratch (rarely needed)
python linkedin_verifier.py --input "...v2...xlsx" --output "verified.xlsx" --reset
```

## Risk note on --google-fallback

Google's bot detection is far milder than LinkedIn's — mainly cookie consent prompts (which the script handles) and rare `sorry/index` interstitial pages (rate-limit style). The script uses the same human-like delays (2.25-4.5s) and fingerprint spoofing as the LinkedIn path. If you hit a `sorry.google.com` page, wait 15-30 minutes and re-run — checkpoint will pick up where it left off.
