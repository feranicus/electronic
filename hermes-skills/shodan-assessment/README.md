# Hermes skill: shodan-assessment

Teaches Hermes to build Colt-branded Cyber Security Assessments from live Shodan.

- `scripts/shodan_recon.py`  — Shodan API -> findings.json + findings.md (severity-classified)
- `scripts/build_findings_deck.js` — findings.json -> branded .pptx (Colt design system)
- `sample/findings.sample.json` — schema example (deck builds from this)
- `reference/` — Colt methodologies + design system + Shodan filter patterns
- `SKILL.md` — the agent instructions Hermes reads

## Deps (baked into the Hermes image via the updated Dockerfile)
- Node.js + `pptxgenjs` (deck)  ·  Python `shodan` (recon)

## Run standalone (test without Hermes)
    python3 scripts/shodan_recon.py --company "Example AG" --query 'org:"Example AG"' \
        --out findings.json --md findings.md          # needs SHODAN_API_KEY
    node scripts/build_findings_deck.js findings.json out.pptx

## Use inside Hermes
Mount this folder into the container's skills dir and set SHODAN_API_KEY, then just ask
Hermes: "Do a Shodan assessment for <company>, scope org:\"<company>\"".
