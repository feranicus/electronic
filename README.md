# electronic — Colt cyber pre-sales automation

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
