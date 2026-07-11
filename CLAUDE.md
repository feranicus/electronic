# Project conventions — feranicus/electronic (Colt cyber pre-sales automation)

## Operating principles (standing instructions — always follow)

1. **Full automation, no manual steps.** Every operational task must be a script or a GitHub
   Actions workflow that runs end-to-end. Never leave the user hand-editing files on the droplet,
   clicking through consoles, or copy-pasting multi-step command sequences. If a task needs doing
   more than once, it gets a script.
2. **GitHub is the single source of truth.** All code, workflows, and infra definitions live in
   this repo. The droplet and cloud resources are provisioned *from* the repo (Actions → SSH /
   APIs), never configured out-of-band. To change how something runs, change it here and let CI
   apply it.
3. **Secrets never touch git.** Runtime secrets (API tokens, Spaces keys, bot tokens, the shared
   access password, service-account JSON) live ONLY as encrypted **GitHub Actions secrets** and/or
   in the droplet's own env files (`chmod 600`). `.gitignore` blocks `*.env`, `*_sa.json`, etc.,
   and `gitleaks` runs in CI. The only credential in GitHub-as-code is the deploy SSH key (a secret).
4. **Non-destructive on the droplet.** Never disturb Amnezia VPN / VideoDead(jobhuntwow) / joplin.
   The colt-stack is an isolated compose project (`-p colt-stack`, `colt-*` names). No firewall
   changes. Patch automation only refreshes colt-stack images; other stacks get only shared OS/kernel
   patches.
5. **The LLM assists, it does not decide side effects.** DeepSeek (DO serverless) writes summaries,
   risk digests, and prose. It never decides whether to run `apt`, push, deploy, or reboot — those
   are deterministic code paths.

## The one irreducible human input
Cloud credentials can only be minted by the account owner. Provide them **once** as GitHub secrets;
after that, everything is automated and re-runnable from the Actions tab.

## How things run (all from the repo)
- **Deploy the bots:** `.github/workflows/deploy.yml` — build → Trivy scan → GHCR → SSH deploy
  (deploy job waits for `production` environment approval). Manual: `python deploy.py --reuse --yes`.
- **CI / security:** `ci.yml` (gitleaks working-tree scan, ruff, pytest), `security.yml` +
  `codeql.yml` (Trivy CLI report-only, CodeQL SAST), `dependabot.yml`.
- **Auto-patcher:** `patchwatch/` — backup-first, LLM-assisted droplet updater on a 3-day systemd
  timer. Zero-touch setup via `patchwatch/provision_patchwatch.py` or the
  `provision-patchwatch.yml` workflow.

## GitHub secrets used (set once)
`DROPLET_SSH_KEY`, `DROPLET_HOST`, `DROPLET_USER`, `DO_API_TOKEN`, `SPACES_KEY`, `SPACES_SECRET`,
`PATCH_TG_CHAT` (optional; else auto-discovered). Repo *variables* (non-secret): `SPACES_REGION`,
`SPACES_BUCKET`. Set them with `gh secret set NAME` / `gh variable set NAME`.

## Assessment bot UX — KEEP IT SIMPLE (KISS, standing rule)
The user gives **one input: a company name or domain.** The engine resolves the *entire* recon
anchor block itself — ASNs + prefixes (bgpview.io + RIPEstat), brand domains & subdomains (crt.sh
CT logs), cert subject-O, favicon hash, and the internal-CA issuer pivot (auto-harvested live from
the Shodan sweep's cert issuers). NEVER require the operator to hand-feed `--asn/--net/--issuer/
--cert-org/--favicon` — those exist only as optional overrides. `run_assessment.py` calls
`shodan_recon.autodiscover()`, not bare `merge_variants()`. If a future change makes the operator
type infrastructure details, it's wrong — auto-resolve it.

## Web vector — cybergod.ai (ADDITIVE, all via CI/CD)
The Telegram bots stay. `webapp/` is a SECOND front door: FastAPI backend (reuses `colt_auth` +
`run_assessment.py` engine + cassandra's assistant) serving a React cabinet (landing + zero-trust
login + New-Assessment/Assistant/History). Container `colt-web` runs in the isolated `colt-stack`
on `127.0.0.1:8090`. Deploy is 100% CI/CD: pushing `webapp/**` triggers `web-deploy.yml` →
Tailscale → `deploy.py --reuse` (builds colt-web) → `webapp/provision_web.py`, which sets DNS via
the DO API and AUTO-DETECTS the droplet's reverse proxy to wire `cybergod.ai` with TLS WITHOUT
disturbing VideoDead. NEVER ask the operator to SSH in and edit a proxy/DNS by hand — provision_web
figures it out. cybergod.ai is served from the droplet, not GitHub.

## cybergod.ai DNS — REMEMBERED (do not re-ask)
DNS is at **GoDaddy** (ns07/ns08.domaincontrol.com); the apex A-records point to **GitHub Pages**
(185.199.108-111.153) and it serves the `feranicus.github.io` repo. So:
- The **landing** is published to GitHub Pages with `publish_landing.py` — a plain git push to the
  Pages repo. NO api key, NO DNS change. Use this to update cybergod.ai's visible page instantly.
- The **interactive app** (login/cabinet) is a backend and MUST run on the droplet. Pointing the
  domain at the droplet is the ONE thing no script can do without a DNS credential — that is the
  internet's ownership model, not a code limit. It needs either a GoDaddy API key OR nameservers
  moved to DigitalOcean, ONCE. Do not keep offering both every turn — state it once and move on.

## cybergod.ai — SETTLED go-live (remember; do not re-litigate)
`python golive.py` is THE one command. It automates end-to-end:
  1) deploy.py --reuse  -> colt-web on the droplet (isolated colt-stack; never touches
     VideoDead/Amnezia/joplin), 2) GoDaddy DNS via API, 3) provision_web.py proxy + Caddy
     auto-TLS, 4) verify. Re-runnable, hands-off.
- Droplet PUBLIC IP: **64.225.108.200**. cybergod.ai must A-record to this for /login to work.
- WHY /login 404s otherwise: cybergod.ai's A-records point at GitHub Pages (185.199.108-111.153),
  which serves static files only and cannot run the React login -> 404. Pointing the name at the
  droplet is the fix; only the domain owner can do it (it needs a DNS credential — not a code limit).
- The ONE irreducible human input = a **GoDaddy API key** (https://developer.godaddy.com/keys),
  pasted ONCE into `golive.secrets.env` (gitignored; copy from golive.secrets.env.example). With it,
  golive.py changes DNS automatically = zero browser steps. Without it, golive still deploys+TLS and
  prints the exact 2-line manual GoDaddy change. Either way it's ONE script. Do NOT keep re-explaining.
- Alternative (equivalent): subdomain app.cybergod.ai -> 64.225.108.200, leaves apex on Pages.

## cybergod.ai — CI/CD SETTLED (2026-07, remember; this supersedes ad-hoc SSH)
Build in GitHub, ship to droplet. NO building on the droplet, NO hand-editing its Caddyfile.
- Pipeline: `.github/workflows/web-deploy.yml` = build `webapp/Dockerfile` -> push
  `ghcr.io/feranicus/colt-web:{latest,sha}` -> Tailscale SSH to droplet ->
  `docker compose -p colt-stack -f docker-compose.web.yml pull && up -d` -> append committed
  `deploy/caddy/cybergod.caddy` block (markers `# colt:cybergod BEGIN/END`, idempotent) into
  videodead's Caddyfile -> `caddy reload` -> verify 401. Triggered by push to webapp/**,
  deploy/caddy/**, docker-compose.web.yml, colt_auth.py (or Run workflow).
- `colt-web` joins EXISTING `videodead_appnet` (external) so videodead-caddy (owns :443) reaches
  it as `http://colt-web:8000`. uvicorn binds 0.0.0.0:8000 (Dockerfile CMD). Do not touch VideoDead.
- ROOT CAUSE of the 404/502 flip-flop: publish_landing.py pushed a CNAME (cybergod.ai) to the
  GitHub Pages repo, so GitHub kept CLAIMING the domain while DNS was cached. FIX =
  `python webapp/unpublish_pages.py` + clear Settings->Pages->Custom domain. DO NOT run
  publish_landing.py for cybergod anymore; the landing is served by the droplet.
- Full doc: `webapp/DEPLOY.md`. One-time human inputs: DNS A @/www -> 64.225.108.200;
  make GHCR colt-web package public (or CI logs in); secrets TS_AUTHKEY/DROPLET_SSH_KEY/DROPLET_USER.
- The `.dockerignore` whitelists (`*` then `!dir`) MUST include `!webapp` or the web build COPY fails.

## cybergod.ai — ONE COMMAND (remember; automate, never hand-hold)
`python ship_web.py` does the whole web deploy hands-off via `gh`: releases the domain from GitHub
Pages (unpublish_pages.py + `gh api DELETE /repos/feranicus/feranicus/pages`), commits+pushes,
`gh workflow run web-deploy.yml` + `gh run watch`, then verifies https://cybergod.ai/api/me == 401.
Requirement: `gh` installed + `gh auth login` (one-time). GHCR pull needs no "make public" click —
the image carries `org.opencontainers.image.source=…/electronic` (links to the public repo) and the
deploy step also `docker login`s with the workflow token. Everything documented in README.md +
webapp/DEPLOY.md. FUTURE RULE: any new ops need = a script + a README/DEPLOY.md update, never a
list of manual steps in chat.

## STANDING RULE — always end with the exact command to run
After finishing ANY piece of work that the user must trigger, end the reply with a short, explicit
"Run this:" block containing the exact command(s), copy-paste ready, with the right working directory
(e.g. `cd "C:\Python SW\Linkedin Scraper"` then `python ship_web.py`). No vague "you can deploy now" —
give the literal command. If there is genuinely nothing to run, say "Nothing to run." explicitly.

## cybergod.ai — web observability (remember)
colt-web emits JSON events (logins via colt_auth, assess_request, assist_query) to
`/var/log/colt/events.log` on the shared `colt_events` volume (`EVENTS_LOG`, `SERVICE=colt-web`);
colt-promtail already tails it -> Loki -> Grafana. Dashboard `obs/grafana/dashboards/webapp.json`
auto-imports via import-dashboards.yml. Labels: service=colt-web, bot=webapp, evt=*. The
web-deploy.yml ssh/scp MUST carry `-o StrictHostKeyChecking=accept-new` (host-key verify was the
"Ship compose" failure). docker-compose.web.yml mounts colt_events + sets EVENTS_LOG/SERVICE.

## STANDING RULE — CI is the single source of truth (no droplet SSH quick-fixes)
When cybergod.ai/web breaks, DO NOT hand-edit the droplet over SSH. Fix the committed files
(docker-compose.web.yml, deploy/caddy/cybergod.caddy, webapp/**, web-deploy.yml) and let CI apply
them via `python ship_web.py`. The droplet is a deploy TARGET, never a source. colt-web runs from the
GHCR image on `videodead_appnet` ONLY (docker-compose.web.yml) so videodead-caddy reaches it at
colt-web:8000. The deploy job needs `permissions: packages: read` to pull the image. SSH is for
READ-ONLY diagnostics only (docker ps/logs), never config changes.

## cybergod.ai — the 502 root cause (single-network rule, remember)
Intermittent 502 = colt-web was on TWO docker networks (colt + videodead_appnet). Docker DNS returns
both IPs; videodead-caddy randomly dialed the unreachable colt-net IP. FIX/RULE: colt-web is defined
ONLY in docker-compose.web.yml on ONLY videodead_appnet; web-deploy.yml does `up -d --force-recreate`.
Removed the web+caddy services from docker-compose.reuse.yml so there is a single source. Never
`docker network connect` colt-web to a 2nd network or define it in another compose file.
