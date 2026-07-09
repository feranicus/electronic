# Testing the shodan-assessment skill in local Hermes (Docker)

Two stages: (1) prove the pipeline works directly in the image, (2) drive it from the Hermes chat.

## 0. One-time: rebuild the image (adds Node + pptxgenjs + Python shodan)
    cd "C:\Python SW\Linkedin Scraper\hermes-local"
    docker build -t hermes-local .

## Stage 1 — smoke test (no chat, zero ambiguity)
Runs recon + deck straight inside the container. Outputs land in `..\shodan-out`.

    # filters only (no key needed) — sanity check identity + the Top-10 filters
    .\test-shodan.ps1 -Seed "AS211483"

    # full run with your Shodan key — writes filters.md, findings.json/md, and the .pptx
    .\test-shodan.ps1 -Seed "keb.de" -ShodanKey "YOUR_SHODAN_KEY"

Check `..\shodan-out\filters.md` (the Super-Filters artifact) and the `*_Shodan_Findings.pptx`.

## Stage 2 — from the Hermes chat
    .\run-hermes-shodan.ps1 -OpenAIKey "doo_v1_..." -ShodanKey "YOUR_SHODAN_KEY"

The skill is mounted at `~/.hermes/skills/shodan-assessment`. Two things to know:
- Hermes needs its **shell / execute_code** tool ON to run the scripts. If it refuses,
  exit and run `... hermes setup tools` once to enable execute_code, then restart.
- Whether or not auto-skill-discovery kicks in, this always works — just tell Hermes:

      Read /root/.hermes/skills/shodan-assessment/SKILL.md and follow it for keb.de.
      Write outputs to /root/work.

  Hermes will: resolve identity -> build the filters -> run Shodan -> build the deck.
  The .pptx appears in `..\shodan-out` on Windows.

## Notes
- Secrets are passed with `-e` at run time; never baked into the image.
- `..\shodan-out` = `C:\Python SW\Linkedin Scraper\shodan-out`.
- Same image + skill deploy to the droplet later (hermes-droplet/).
