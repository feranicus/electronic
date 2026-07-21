# electronic — Colt cyber pre-sales automation

## The one command

```
cd "C:\Python SW\Linkedin Scraper"
python ship.py
```

`ship.py` is the ONLY script you run. It does, in order:

1. **Tests** — compile-checks every Python file, runs the CA-pivot regression
   (`test_ca_pivot.py`, the bibeltv.de false-positive incident) and `pytest tests/`.
   Nothing ships if any of it fails.
2. **Commit + push** — GitHub stays the single source of truth.
3. **Deploy** — web (`ship_web.py` -> GitHub Actions -> GHCR -> droplet -> Caddy) and
   bots (`deploy.py --reuse --yes`).
4. **Verify** — colt-* containers up, and `https://cybergod.ai/api/me` returns 401.

Flags narrow it, never split it:

| flag | effect |
|---|---|
| `--test` | tests only, deploy nothing |
| `--web` / `--bots` | deploy only that half |
| `--direct` | straight to the droplet, bypassing GitHub CI |
| `--dry-run` | print the plan, touch nothing |
| `-m "message"` | commit message |
| `--no-test` | skip the test gate (you had better have a reason) |

Every other script in this repo (`deploy.py`, `ship_web.py`, `deploy_web_direct.py`,
`set_secret.py`, `cost_report.py`, `probe_models.py`, `compare_models.py`, `check_enrich.py`)
is a building block. They remain runnable alone for debugging, but normal operation is
`python ship.py` and nothing else. **If a change adds a step, wire it into ship.py in the same
commit — a script the operator has to remember separately is a bug.**


**Type a company name in Telegram, get four boardroom-ready cyber-risk decks in ~2 minutes.**
So 30+ sales people can walk into any meeting prepared — even while the engineer who built it is on a beach.

Everything is one repo (single source of truth), deployed to a DigitalOcean droplet, multi-cloud,
observable, self-patching, and shipped with one command.

> Interactive architecture: open **`colt_platform_architecture.html`** (hosted at `cybergod.ai`).
> Motion version: `cyber_presales_architecture.gif` / `.mp4`.

---

## In one breath
1. **You ask** — `/assess Volkswagen AG` in Telegram. Nothing else.
2. **It looks** — finds everything that company exposes on the internet (public records only).
3. **It thinks** — scores the danger, prices it in €, names who'd attack them.
4. **You get decks** — four PowerPoints land back in your chat.

The killer feature: **one input.** You never type an IP, ASN or network — the engine resolves the
target's whole footprint itself (see *KISS rule* in `CLAUDE.md`).

## The two bots
| Bot | What it is | Try |
|-----|-----------|-----|
| **colttechbot** (`assess-bot/`) | the assessor — recon → score → 4 decks | `/assess <company or domain>` |
| **cassandra** (`cassandra-bot/`) | the AE assistant — live web research, MEDDPICC, outreach, help desk | `/research <topic>` |

## What happens inside `/assess`
1. **Footprint** — company name → ASNs+prefixes (bgpview.io + RIPEstat), brand domains & subdomains
   (crt.sh CT logs), cert-subject-O and favicon — all auto-resolved (`shodan_recon.autodiscover()`).
2. **Exposure** — Shodan sweep with **30+ super-filters** incl. the live **internal-CA issuer pivot**
   and the paid facets (`has_vuln`, `vuln:CVE`, `tag:ics`, `ssl.jarm`).
3. **Score** — deterministic classifier (CRITICAL→LOW), CISA-KEV aware, edge-appliance mgmt = CRITICAL,
   CDN/honeypot false-positives dropped.
4. **Decks** — DeepSeek (DO serverless) writes the prose; `pptxgenjs` templates lock the structure & maths:
   **Shodan Findings · C-BIQ (€ business impact) · GEOPOL (adversaries) · DELTAS (value bought back)**.

## Multi-cloud (each does its one best thing)
- **GitHub** — source of truth + CI/CD.
- **DigitalOcean** — droplet runtime (isolated `colt-stack`), serverless AI (**DeepSeek**), backups (**Spaces**).
- **Google Cloud** — Gmail API delivers the 2FA one-time codes over HTTPS (droplet blocks SMTP).
- **Tailscale** — private tunnel so CI can reach the firewalled droplet without opening a port.

## Security (secure by design)
- **Zero-trust auth** — `name.familyname@colt.net` + shared password **+ a one-time code emailed to that
  mailbox** (`colt_auth.py`). Knowing the password isn't enough — you must own the inbox.
- **Secrets never in git** — only on the droplet (`chmod 600 .env`) or as encrypted GitHub secrets;
  `gitleaks` blocks accidental commits.
- **Scanned before ship** — Trivy (deps+image), CodeQL SAST, ruff, pytest.
- **Non-destructive** — isolated `colt-stack` (`-p colt-stack`, `colt-*` names); Amnezia VPN / VideoDead /
  joplin and the firewall are never touched.

## Observability
Structured events → `events.log` → **promtail → Loki → your existing Grafana** (`godeyes.ai/observe`).
Dashboards: per-bot activity, auth audit trail, **colt-web / cybergod.ai** (logins, assessments,
assistant, live stream), and a **patchwatch deep-dive**. Import with
`python import_dashboard.py --all` (or the `import-dashboards.yml` workflow).

## Self-patching (`patchwatch/`)
Backup-first, LLM-assisted auto-patcher on a 3-day systemd timer: snapshot to Spaces (+ optional DO
droplet snapshot) → `apt` upgrade → DeepSeek risk digest (flags kernel/CVE items like GhostLock) →
Telegram + Grafana → reboot in a 4am window if a kernel fix needs it. Zero-touch setup:
`python patchwatch/provision_patchwatch.py` or the `provision-patchwatch.yml` workflow.

## Deploy / ship
```bash
python ship.py            # BOTS: repair + commit + push + rebuild + redeploy + verify
python ship_web.py        # WEB (cybergod.ai): release Pages + push + run CI + watch + verify
python deploy.py --reuse --yes   # just rebuild/redeploy the stack locally
git push origin main      # CI builds + Trivy-scans + pushes image to GHCR + deploys (via Tailscale)
```

## Web vector — cybergod.ai (browser app, no Telegram)
A second front door: a React cabinet (**landing + zero-trust login + New-Assessment + Assistant +
History**) served by `colt-web` (FastAPI + the same engine + `colt_auth`). Any Colt AE uses it at
**https://cybergod.ai/login** — same auth as the bots (`@colt.net` + password + emailed 6-digit code).

**How it ships (build in GitHub, run on the droplet):** push to `webapp/**` (or run `python ship_web.py`)
→ `.github/workflows/web-deploy.yml` builds `webapp/Dockerfile`, pushes `ghcr.io/feranicus/colt-web`,
Tailscale-SSHes the droplet, `docker compose -f docker-compose.web.yml pull && up -d`, appends the
committed `deploy/caddy/cybergod.caddy` vhost into the shared `videodead-caddy` (idempotent, auto-TLS),
reloads, and verifies `401`. Nothing is built on the droplet; nothing is hand-edited there.
**Full runbook + one-time setup: [`webapp/DEPLOY.md`](webapp/DEPLOY.md).**

- One host, one domain: DNS `A @/www → 64.225.108.200`; `videodead-caddy` owns `:443` and reverse-proxies
  `cybergod.ai → colt-web:8000` over the shared `videodead_appnet`. VideoDead/Amnezia/joplin untouched.
- **Do NOT run `publish_landing.py` for cybergod** — it re-adds the GitHub-Pages CNAME and re-claims the
  domain (that was the 404/502 flip-flop). The landing is served by the droplet. `webapp/unpublish_pages.py`
  releases the domain from Pages.

## Repo map
| Path | Purpose |
|------|---------|
| `assess-bot/` · `cassandra-bot/` | the two Telegram bots + Dockerfiles |
| `colt_auth.py` | shared zero-trust auth (email + password + Gmail-API OTP 2FA) |
| `hermes-skills/shodan-assessment/scripts/` | the engine: `shodan_recon.py` (recon+filters+autodiscovery), `run_assessment.py` (orchestrator), `build_{findings,cbiq,geopol,deltas}_deck.js`, `enrich.py` |
| `patchwatch/` | self-patcher (script, systemd units, zero-touch provisioner) |
| `obs/` | promtail + Grafana dashboards (reuse mode) |
| `tofu/` | OpenTofu IaC (DigitalOcean) |
| `.github/workflows/` | `ci.yml`, `security.yml`, `codeql.yml`, `deploy.yml`, `web-deploy.yml`, `provision-patchwatch.yml`, `import-dashboards.yml`, `dependabot.yml` |
| `deploy.py` · `ship.py` · `provision_patchwatch.py` · `setup_github_cicd.py` · `import_dashboard.py` | ops scripts |
| `webapp/` | the web app: React cabinet (`frontend/`) + FastAPI (`backend/`), `Dockerfile`, `DEPLOY.md`, `provision_web.py`, `unpublish_pages.py` |
| `deploy/caddy/cybergod.caddy` | committed reverse-proxy vhost for cybergod.ai (source of truth) |
| `ship_web.py` | one command: ship cybergod.ai end-to-end through CI |
| `docker-compose.reuse.yml` · `docker-compose.ghcr.yml` · `docker-compose.web.yml` | isolated `colt-stack` (bots build-local vs registry-image; web = CI image) |
| `colt_platform_architecture.html` | this architecture, explained A→Z |

## GitHub secrets (set once)
`DROPLET_SSH_KEY`, `DROPLET_HOST`, `DROPLET_USER`, `DO_API_TOKEN`, `SPACES_KEY`, `SPACES_SECRET`,
`GRAFANA_TOKEN`, `TS_AUTHKEY`, `PATCH_TG_CHAT` (optional). Repo variables: `SPACES_REGION`, `SPACES_BUCKET`,
`GRAFANA_URL`, `TAILNET_HOST`. Runtime app secrets (bot tokens, Shodan/DO keys, `COLT_BOT_PASSWORD`,
`GMAIL_SA_B64`) live **only** in the droplet's `.env` — never in git.

## Cost tracking (per assessment / per day / all-time)
Every completed assessment is appended to a persistent SQLite ledger on the droplet's shared
`colt_events` volume (`/var/log/colt/cost_ledger.sqlite`) by
`hermes-skills/shodan-assessment/scripts/cost_ledger.py`. Unlike Loki (which ages out with
retention), the ledger is the books-of-record for spend.

```
python cost_report.py                 # lifetime + per-day + per-company (read-only over SSH)
python cost_report.py --json          # machine-readable
python cost_report.py --no-backfill   # skip seeding history from events.log
python cost_report.py --local ledger.sqlite
```

Grafana ("Colt Bots Observability"):
- **Cost** row — cost today (24h), cost over the selected range, avg/assessment, cost per day (bars),
  cost per assessment by company (table). Bounded by Loki retention.
- **Lifetime (persistent ledger)** row — true all-time cost/assessments/avg/tokens, from the ledger's
  cumulative `cost_snapshot` event. Not bounded by retention.

Cost covers AI inference (DeepSeek/QWEN, ~$0.0065 per assessment). The Shodan plan and the droplet
are flat subscriptions and are intentionally out of scope.

## Document language (English / Hoch-Deutsch)
The same four decks (Findings · C-BIQ · GEOPOL · DELTAS) are produced in either language. The
customer is asked; nothing else changes.

```
python hermes-skills/shodan-assessment/scripts/run_assessment.py --seed keb.de --lang de
```

- **Web** (cybergod.ai → New Assessment): a "Document language" dropdown next to the company field.
- **Telegram**: `/assess keb.de` → tap **English** or **Deutsch**. Skip the prompt with
  `/assess keb.de --lang de`.

German decks are written with a `_DE` suffix (`ACME_C-BIQ_DE.pptx`) so both languages can coexist in
one output folder. English output is unchanged, byte-for-byte.

How it works (see `scripts/i18n/`): `deck_i18n.js` translates the deck chrome at the pptxgenjs
boundary from the committed dictionary `de.json`; `enrich.py` asks the model to write the prose in
German; `i18n.py` translates the engine's own deterministic strings before rendering. All three read
the same `de.json`, so a term can never be translated two different ways. Missing translations fall
back to English rather than failing.

Audit which strings are not yet translated:
```
DECK_LANG=de DECK_I18N_AUDIT=1 DECK_I18N_AUDIT_OUT=/tmp/audit.json \
  node hermes-skills/shodan-assessment/scripts/build_cbiq_deck.js cbiq.json /tmp/out.pptx
```

## Choosing the enrichment model (and surviving a 429)
The LLM writes only the deck PROSE (JSON); the slides themselves are deterministic JS. So pick the
model on: reachable on your DO tier, contract-valid JSON, German quality, latency, price.

```
python probe_models.py            # what your key can reach + which pass the real contract
python probe_models.py --lang de  # also check the German output
```

It prints an `ENRICH_MODELS="a,b,c"` line — put it in `assess-bot/.env` on the droplet. enrich.py
retries each model with backoff (honouring `Retry-After`), then fails over to the next, inside a
230s budget.

A `429` from DO serverless is an **account** RPM/TPM quota (Tier 1/2 = 120 RPM) or an empty prepaid
balance — not a model fault. Tier 1/2 cannot use Anthropic/OpenAI models except `gpt-oss-*`.
Check https://cloud.digitalocean.com/limits.

## Which model should write the decks? (bake-off, not benchmarks)
The LLM writes only the deck PROSE; the slides are deterministic JS. So the question is never "which
model scores higher on MMLU" — it is "whose German loss-narrative would a CISO believe, and does it
fill the contract fields". Two commands answer it with evidence:

```
python probe_models.py --list        # every model this DO key can see (1 API call)
python probe_models.py --lang de     # which ones pass the REAL contract, how fast -> ENRICH_MODELS line
python compare_models.py --lang de   # SAME findings.json through each model, prose side by side
```

`compare_models.py` imports the real `enrich.py` prompt (DELTAS bible + LANG_DE + strict JSON), so
what you read is exactly what would land on slide 2. It reports latency, cost, whether the output is
actually German, how many findings were rewritten, and — the one that matters — the `realComparable`
dated public breach each model cites. A model returning 0 precedents leaves your C-BIQ slides
templated; a model inventing one is worse.

Measured on this account (2026-07): `deepseek-3.2` head (37B active, current knowledge),
`llama-4-maverick` backup (17B active, ~4x faster, German is an officially supported language, but
knowledge cutoff Aug-2024 -> cannot cite recent breaches), `openai-gpt-oss-120b` third (Apache-2.0,
5.1B active, reasoning model -> shakiest on strict JSON). anthropic-*/openai-gpt-5* are http-403 on a
DO Tier 1/2 key regardless of being visible in the catalog.

## Mobile (Android + iPhone)
One responsive PWA — no app store, no second codebase.

**Install:** Android/Chrome shows an install prompt (or menu -> "Install app"). iPhone/Safari:
Share -> "Add to Home Screen". Either way it launches standalone, no browser chrome, with the Colt
chevron icon.

**Assessments survive the phone:** the engine runs server-side and the SSE stream is only a viewer,
so locking the screen, switching apps or refreshing no longer cancels a run — the client reconnects
(`Last-Event-ID`) and catches up. `GET /api/assess/{id}/status` polls the same truth.

## Secrets on the droplet (never in git)
Runtime secrets live ONLY in the droplet's `assess-bot/.env` (chmod 600), which colt-web and the bots
load via `env_file:`. Never in the repo, never in docker-compose (those are committed; gitleaks blocks
secrets in CI).

```
python set_secret.py ABUSEIPDB_KEY     # prompts, hidden input, restarts colt-web, verifies
python set_secret.py --list            # which secret NAMES exist (names only, never values)
```
The value is typed at a hidden prompt and piped over stdin — never an argv (visible in `ps` and your
shell history), never echoed, never written locally.

Get a free AbuseIPDB key: https://www.abuseipdb.com/account/api — without it, hostile IPs are still
detected and reported to you in the daily digest; nothing is submitted to third parties.
