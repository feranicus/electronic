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
6. **Deliver operations as scripts + document — NO command blobs.** Never hand the user long ad-hoc
   shell/heredoc command sequences to paste ("talmud commands"). Every operational step (build, run,
   deploy, diagnose, fix) must be a re-runnable **Python script** committed to the repo, invoked as
   `python <script> ...`, and any change (deps, Dockerfile, flags, config, architecture) must update
   the relevant **README.md** in the SAME change. KISS + full automation. (Applies to all projects.)

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

## HARD RULE — no one-off SSH edits, ever (they get lost)
Every change to the droplet MUST live in a committed artifact: a docker-compose file, a Dockerfile,
a committed config (e.g. deploy/caddy/cybergod.caddy), or a Python/GitHub-Actions script. NEVER fix
anything with an ad-hoc `ssh root@... "sed/docker ..."` one-liner — those are invisible to the repo
and vanish on the next deploy. If something on the droplet is wrong, fix the committed source and run
the ONE script that applies it:
  - via GitHub:  `python ship_web.py`   (build -> GHCR -> web-deploy.yml -> droplet)
  - direct:      `python deploy_web_direct.py`  (build on droplet + apply committed compose/caddy)
Both are idempotent and self-verifying (print colt-web image/networks + caddy dials + public 401).
deploy_web_direct.py already contains the FULL fix: build colt-web single-network (--force-recreate),
strip+rewrite the cybergod Caddy block from deploy/caddy/cybergod.caddy, normalize the site line,
validate, --force reload, verify. SSH is READ-ONLY diagnostics only. Windows note: run from WSL or
ensure the deploy scripts send LF bytes (never text=True) so bash isn't fed CRLF.

## HARD RULE — never `--remove-orphans` on a subset compose in a shared project
docker-compose.web.yml defines ONLY `web`, but runs in project `colt-stack` alongside the bots +
promtail (docker-compose.reuse.yml). `docker compose -p colt-stack -f docker-compose.web.yml up
--remove-orphans` DELETES colt-promtail + colt-assessbot + colt-cassandra (they look like orphans to
that file). That is why Grafana went empty (promtail gone) and the Telegram bots died. NEVER use
--remove-orphans when deploying a single service into the shared colt-stack project. Removed it from
deploy_web_direct.py AND web-deploy.yml. To restore promtail + bots: `python deploy.py --reuse --yes`
(reuse.yml no longer contains `web`, so it won't touch colt-web).

## IAM — who can log in (bots + web share ONE gate)
`colt_auth.email_allowed()` is the single source of truth used by BOTH the Telegram bots and colt-web:
- any Colt AE matching `name.familyname@colt.net` (EMAIL_RE), OR
- a named partner in `colt_auth.PARTNER_EMAILS`  -> currently `ud@objectale.ch` (Objectale), OR
- anyone on a trusted domain in `colt_auth.PARTNER_DOMAINS` -> currently `s4biz.io` (whole domain).
Emails/domains are not secrets, so the defaults are committed = auditable. Domain match is EXACT
(`x@s4biz.io.evil.com` is rejected). Add more WITHOUT a code change via env, comma-separated, in
assess-bot/.env on the droplet (colt-web loads the same file):
`EXTRA_ALLOWED_EMAILS="a@x.ch,b@y.com"` and/or `EXTRA_ALLOWED_DOMAINS="foo.io,bar.com"`.
`webapp/backend/app/auth.py::email_ok()` delegates to `colt_auth.email_allowed()` so web and bots can
never disagree. Auth is unchanged otherwise: shared password + a 6-digit OTP emailed (Gmail API) to that
mailbox — a partner still needs to control their own inbox AND know COLT_BOT_PASSWORD.

## Cost observability (remember)
Cost data comes from the `assess_done` event: `company` + `qwen_cost_usd` (+ crit/high/med/low,
qwen_model, total_ms). The `qwen` event (enrich.py) carries `tokens_in/tokens_out/cost_usd/status`.
Grafana "Colt Bots Observability" has a **Cost** row driven by those:
- Cost today (24h)         -> sum(sum_over_time(... evt=assess_done | unwrap qwen_cost_usd [1d]))
- Cost selected range      -> same with [$__range]  (set range = Last 1 year for "all-time")
- Avg cost / assessment    -> sum(cost[$__range]) / sum(count assess_done [$__range])
- Cost per day             -> timeseries, panel interval pinned to 1d, bars
- Cost per assessment      -> table, sum by (company) (... [$__range])
"All-time" = the dashboard range (bounded by Loki retention) — there is no infinite lookback.
Panel titles MUST state the window (24h vs selected range); mixing them is what looked like a
"discrepancy". Stats set noValue="0" (so quiet != "No data") and multi-query panels name series via
byFrameRefID overrides (else Grafana shows "Value #A").

## Cost ledger — TRUE all-time cost (remember; Loki is NOT the books of record)
Loki ages out with retention, so "cost since the beginning of time" can never come from logs.
Source of truth = **SQLite ledger** `hermes-skills/shodan-assessment/scripts/cost_ledger.py` at
`/var/log/colt/cost_ledger.sqlite` on the PERSISTENT shared `colt_events` volume (mounted by BOTH
the bots and colt-web) -> survives redeploys, image rebuilds and Loki retention.
- `run_assessment.py` calls `cost_ledger.record(...)` right after `assess_done`, then emits a
  cumulative `cost_snapshot` event (lifetime_usd, assessments_total, avg_usd, tokens_*_total).
- Grafana shows lifetime via `last_over_time(... evt=cost_snapshot | unwrap lifetime_usd [$__range])`
  — a CUMULATIVE snapshot, so it stays correct even after Loki drops the old lines. NO new
  datasource/plugin needed (no Infinity/SQLite plugin, no Prometheus scrape of colt-web).
- `python cost_report.py` = the one command: READ-ONLY ssh + `docker exec colt-web python3
  /opt/shodan-skill/scripts/cost_ledger.py --backfill --snapshot` -> prints lifetime / per-day /
  per-company. `--backfill` seeds pre-ledger history from events.log and is IDEMPOTENT (dedupe on
  ts+company), so re-running never double-counts. `--json` for machines, `--local PATH` for a copy.
- Cost = AI inference only (DeepSeek/QWEN ~$0.0065/assessment). Shodan plan + droplet are flat
  subscriptions, not per-assessment, so they are deliberately NOT in the ledger.

## Deck language (EN / DE) — remember; do NOT hoist strings again
The customer picks the language; the SAME 4 decks are produced in English or Hoch-Deutsch.
- ONE input to the engine: `run_assessment.py --lang en|de` (default en). Web + bots both pass it.
- Three streams of text, ONE committed dictionary `scripts/i18n/de.json`:
  1. **Deck chrome** (~530 literals hardcoded in the 4 .js builders) -> `scripts/i18n/deck_i18n.js`.
     It does NOT hoist strings: it wraps `pptx.addSlide` and translates at the addText/addTable
     boundary. Each builder opts in with ONE line: `const pres = I18N.install(new pptxgen())`.
     Unknown strings fall through to English (never crash). `DECK_I18N_AUDIT=1` +
     `DECK_I18N_AUDIT_OUT=/tmp/a.json` dumps untranslated strings — that is how de.json was harvested.
  2. **LLM prose** (exec_summary/what/why/rem/strengths/...) -> `enrich.py` LANG_DE prompt block.
     A dictionary can never cover this; it is per-company text.
  3. **Engine-deterministic prose** (finding titles, Colt controls, bucket names) ->
     `scripts/i18n/i18n.py` post-pass over findings/cbiq/geopol.json BEFORE the decks render.
- **HARD RULE — never translate ENUM/LOOKUP keys.** `findings[].sev` ("CRITICAL"), geopol
  `actors[].band` ("NATION-STATE"), tier/status/phase are matched by the builders for grouping and
  colour maps. Translating them makes findings SILENTLY VANISH (findings deck fell 23 -> 8 pages).
  They live in `i18n.py::_SKIP_KEYS` and are translated at RENDER time only (display-only).
- German runs ~30% longer and every box has a hardcoded w/h: `deck_i18n.js::fitSize()` computes an
  explicit smaller fontSize (deterministic, works in every renderer) and also sets `fit:"shrink"`
  (pptxgenjs 4.0.1 emits a bare `<a:normAutofit/>` which only PowerPoint honours). Hand-set sizes for
  the Arial Black display headlines live in `de.json.sizes`.
- Glossary (full Eindeutschung, user's choice): ALE->SEW · PML->WHS · LEF->SEH · TEF->BEH · LM->SH ·
  CoD->KdV · ROSI->RSI · Kill Chain->Angriffskette. Proper nouns (FAIR, MITRE ATT&CK, NIST, BSI,
  Colt product names, CVE IDs, Shodan) are NOT translated.
- **EN is zero-diff**: `LANG==="en"` bypasses the wrapper entirely, so English decks are byte-for-byte
  what they were. DE decks are written with a `_DE` filename suffix so EN/DE never overwrite.
- Web: `AssessReq.lang` -> `store.create_job(..., lang)` (persisted — the POST only registers the job,
  the SSE stream launches the engine later and re-reads the row) -> `--lang`. The jobs table gets an
  `ALTER TABLE ... ADD COLUMN lang` migration; without it every existing deployment 500s.
- Telegram: `/assess <company>` -> inline keyboard (English/Deutsch) -> `CallbackQueryHandler`;
  pending run parked in `ctx.user_data` (per-user, so two AEs can assess at once).
  Power-user shortcut, no prompt: `/assess <company> --lang de`.

## LLM model chain + the "no false findings" rule (remember)
**There is no "best model for PPT".** The 4 decks are rendered by deterministic JS (pptxgenjs); the
LLM only returns a JSON blob of prose. So the selection criteria are ONLY: reachable on this DO
account/tier · contract-valid JSON · usable business prose · German when asked · latency · price.
- `enrich.py` takes a CHAIN: `ENRICH_MODELS="deepseek-3.2,gpt-oss-120b,qwen3.5-397b-a17b"`
  (falls back to ENRICH_MODEL, then a built-in default). Per model: `ENRICH_ATTEMPTS` (2) with
  exponential backoff honouring `Retry-After`; then FAILOVER to the next model. Whole chain is
  bounded by `ENRICH_BUDGET_S` (230s) because run_assessment kills enrich at 260s.
  Telemetry: the `qwen` event now carries `attempts`, `chain`, and the model that actually WON;
  `qwen.failover=true` when the head of the chain was skipped. Cost uses `ENRICH_PRICE_MAP` per model.
- **A 429 from DO serverless is an ACCOUNT-level RPM/TPM quota** (Tier 1/2 = 120 RPM) or an empty
  prepaid balance — retrying the SAME model cannot fix it, only a different model or a quota/balance
  change. **DO Tier 1/2 cannot call Anthropic/OpenAI models at all except gpt-oss-120b / gpt-oss-20b.**
- `python probe_models.py` = the one command to pick the chain from EVIDENCE: dumps the full catalog
  grouped by vendor, probes a curated shortlist (fast+smart only; skips embed/rerank/image), calls
  each with the REAL enrichment contract, scores json_ok / contract_ok / German / latency, then
  prints the exact `ENRICH_MODELS=` line. `--local`, `--lang de`, `--models a,b`, `--json`.
- **The backup MUST be a different VENDOR.** A 429/outage is provider-wide, so deepseek->deepseek is
  not a backup. probe_models recommends the best model PER VENDOR for exactly this reason.
- **DEADLINE-AWARE TIMEOUT (critical).** assess-bot/.env had `ENRICH_TIMEOUT=200` with a 230s budget,
  so a hanging DeepSeek ate the whole budget and NO backup ever ran (that is how the SGS run died).
  Each call now gets `min(ENRICH_TIMEOUT, remaining_budget / models_left)`, floor 35s — the head is
  capped (~76s on a 3-model chain) so the backup always has budget.
- The account is NOT DO Tier 1/2: `/v1/models` shows 74 models incl. anthropic-claude-opus-4.8 /
  claude-5-sonnet / fable-5. Visibility != entitlement — probe_models proves which actually answer.
- Shodan key is fine; the PLAN is `basic` (Freelancer): `vuln:` needs Small Business+, `tag:` needs
  Corporate. `shodan_recon.shodan_plan()` calls api-info once and SKIPS those queries on a plan that
  cannot run them (saves query credits, kills the scary warnings). Upgrading lights them up again.
- ASN discovery is multi-source (`asn_sources.py`): RIPE DB (authoritative for DACH) + CAIDA AS Rank
  + PeeringDB + bgpview LAST. bgpview.io is the only host that fails to resolve in the container
  ("Errno -5"), while stat.ripe.net answers in 1ms — never depend on one API for a load-bearing fact.

## Model bake-off — decide deck quality with the artifact (remember)
`python compare_models.py --lang de` runs the SAME findings.json through each model using the REAL
enrich.py prompt (imports E.PROMPT/E.LANG_DE/E._bible/E._call — never re-implements it) and prints
exec_summary + realComparable side by side with ms/cost/German/field-fill counts. Benchmarks do not
measure "credible German CISO prose"; this does. Cheapest+fastest is not the win condition.
Key insight that settled head-of-chain: llama-4-maverick is 4x faster but its knowledge cutoff is
Aug-2024, and `realComparable` requires a REAL, DATED public breach from model knowledge — a stale or
invented precedent in a customer deck is the worst failure mode. deepseek-3.2 (37B active, newer)
stays head; maverick is the fast fallback.

## HARD RULE — absence of evidence is never a finding
`bgp_resilience.py` graded **Cogent (AS174, a tier-1 transit network)** as
`CRITICAL / no-ASN / 0 upstreams` — purely because container DNS died, so bgpview/crt.sh returned
nothing and `has_own_asn = bool(asns)` read the empty list as "zero routing autonomy". That is a
false claim in a customer-facing deck.
RULE: when a lookup FAILS, report `UNKNOWN / data-unavailable` and claim NO NIS2 gap. Only grade
CRITICAL/HIGH from a SUCCESSFUL lookup. `assess(asns, org, discovery_ok=)` + `_FETCH_ERRORS` +
`data_ok` in bgp.json enforce it; run_assessment passes `discovery_ok` from whether autodiscovery
actually returned asns/nets/ct_domains, and warns loudly when data_ok is false. This applies to EVERY
future module: never infer a customer weakness from a failed API call.

## Web UX — the assessment progress bar (remember)
A ~2min job with only a spinner makes people refresh, which CANCELS the run (the SSE stream is what
drives the engine). So:
- `run_assessment.py::_pg(msg, pct)` stamps every phase line: `PROGRESS: [56%] BGP/ASN resilience...`
  Milestone ladder = 4/8/56/62/89/91/97/99/100, weighted by REAL wall-clock (recon ~60-80s of a ~2min
  run = the bulk; enrichment ~30-60s; deck render ~10s). `_pg(msg)` without pct still works.
- `NewAssessment.jsx` parses `[nn%]`, then EASES toward the next milestone (1.5% of the gap per 400ms)
  and stops 1% short of it — so during the 75s recon the bar still creeps 8% -> ~53% instead of
  freezing, but never pre-announces a phase. It snaps forward on a real milestone and never regresses.
- Also shows the phase label, an elapsed clock, and "refreshing cancels the run".
- The Telegram bot is unaffected: it prints the line verbatim, `[56%]` included.

## Enrichment model chain — PROVEN on this account (2026-07, do not re-litigate)
`python probe_models.py --lang de` measured it. Do not guess; re-run the probe if DO changes tiers.
- **anthropic-* and commercial openai-gpt-5* = http-403 Forbidden on this key.** 74 models are
  VISIBLE in /v1/models but Tier 1/2 cannot CALL them. gpt-oss-* is the documented exception.
  So the chain is OPEN-WEIGHT only. (Visibility != entitlement. This is why we probe.)
- **Reasoning/thinking models break the strict-JSON contract**: `deepseek-r1-distill-llama-70b` and
  `qwen3.5-397b-a17b` both returned bad-contract at 700 tok (they emit thinking, then truncate).
  Never put a *-thinking / *-distill / o1 / o3 model in the chain. Instruct models only.
- Measured: `deepseek-3.2` = contract-valid + German OK, ~63s (slow -> a faster backup has value).
- CHAIN (`_FALLBACKS` in enrich.py, override with ENRICH_MODELS) — MEASURED 2026-07:
  `deepseek-3.2` (head; ok, German OK, 12.4s — but 63s on an earlier probe: latency swings wildly)
  -> `llama-4-maverick` (ok, German OK, **3.3s**, Meta open weights)
  -> `openai-gpt-oss-120b` (Apache-2.0; only openai id Tier 1/2 may call; probed 429 = transient
  account quota). THREE VENDORS = no shared failure domain.
  Also measured: glm-5.2 = valid JSON but answered ENGLISH under a one-line DE instruction (the real
  LANG_DE prompt is far stronger, so likely a false negative); glm-5.1 + minimax-m2.5 = not JSON;
  kimi-k2.5/k2.6 = http-400 because the probe sent `response_format` (enrich.py retries without it).
- Catalog ids are exact and easy to get wrong: it is `openai-gpt-oss-120b`, NOT `gpt-oss-120b`
  (that mistake made the probe skip the one usable open model). Other open-weight options present:
  glm-5/5.1/5.2, kimi-k2.5/k2.6, llama-4-maverick, minimax-m2.5, mistral-3-14B, gemma-4-31B-it,
  nvidia-nemotron-3-super-120b, deepseek-4-flash.

## Bake-off RESULTS on the REAL prompt (2026-07) — supersedes the toy-probe numbers
`compare_models.py --lang de`, same findings.json, real 10,640-char prompt, ~4,100 output tokens:
| model | ms | cost | German | rewritten | strengths | precedents |
|---|---|---|---|---|---|---|
| deepseek-3.2 | **25,046** | $0.0037 | yes | 3 | 2 | 3 |
| llama-4-maverick | **44,611** | $0.0033 | yes | 3 | 1 | 3 |
| openai-gpt-oss-120b | http-429 (every attempt) | — | — | — | — | — |
- **Maverick is SLOWER on the real workload (44.6s vs 25.0s)** — the opposite of the probe's toy
  prompt (3.3s vs 12.4s). NEVER pick a model on a synthetic probe; latency ranking inverts with
  prompt size. deepseek-3.2 stays HEAD on both speed AND quality.
- Quality: deepseek names the actual finding (2 nginx hosts, CVE-2023-44487 on KEV) + NIS2 Art.21 /
  DSGVO Art.32 and argues structural fixes. Maverick is generic ("mehrere Sicherheitsrisiken").
- **deepseek HALLUCINATED a CVE**: wrote CVE-2021-44244 for Log4Shell (real: CVE-2021-44228).
  Maverick's precedents (Norsk Hydro €70M/LockerGoga, NHS WannaCry £92M, Change Healthcare $2.45B)
  were factually ACCURATE but generic/not tied to the findings. So: neither model is "just better".
- `openai-gpt-oss-120b` = 429 on every attempt on this account -> useless as backup; replace it.

## HARD RULE — no invented identifiers in a customer deck
Two layers in enrich.py, because a prompt rule is a request not a guarantee:
1. PROMPT guardrails: cite a CVE ONLY if that exact ID appears in the RAW FINDINGS; name incident +
   year instead when unsure; never invent a company/date/figure; flag proposed-vs-final fines.
2. `_audit_cves(fj, j)` post-check: every CVE in realComparable/lossScenario is cross-checked against
   the CVEs actually present in the scan evidence. Unverifiable ones are STRIPPED (prose kept), a
   `[warn]` is printed, `qwen.cves_stripped` is set and an `evt=hallucination_guard` event is emitted.
Never "fix" a hallucination by silently rewriting prose — strip the claim and surface it.

## Failures must be observable (remember)
The Yamaha run died on `TypeError: sequence item 0: expected str instance, int found` and Grafana
showed NOTHING — because an unhandled exception killed the engine before `assess_done` was emitted.
That is why "11 requested / 1 completed" had no explanation.
- `run_assessment.py` now wraps `main()` and emits `evt=assess_error` (company, error type, message,
  source line) to BOTH stdout and EVENTS_LOG, then re-raises so the exit code/traceback are unchanged.
  It also prints `PROGRESS: [100%] FAILED — ...` so the web progress bar resolves instead of hanging.
- Dashboard row "Failures — why an assessment died": failed 24h / range, hallucinated-CVEs-stripped,
  LLM fallbacks, plus a table of company | error | message | where.
- RULE: any future long-running path must emit a structured error event. A crash has to be as visible
  as a success, or the dashboard lies by omission.

## HARD RULE — ident["asns"] holds "AS1234" STRINGS
`build_filters` does `",".join(ident["asns"])`. `asn_sources.discover()` returns ints (clean API), so
shodan_recon converts at the boundary: `["AS%d" % a for a in res["asns"]]`. The join is also
defensive now. Mixing the two crashed the whole Yamaha assessment for one type slip.

## Deck depth — why Colt / what you get / how (remember)
Complaint: "the amount of text is super small, needs more meat, especially WHY COLT and what it gives
the customer". Root cause was the CONTRACT, not the model:
- `build_findings_deck.js` already renders up to 5 rich remediation rows `{tag,title,body}` (bold
  title + body underneath, tag one of COLT/PSF/OSS/VENDOR). The bible only asked for
  `"rem":["Colt product name"]` — a bare string. The slide had room nobody filled.
- FIX: LLM_DELTAS_BIBLE.md now demands 3-5 rem OBJECTS, COLT first, each body answering in order:
  WHY COLT (what it structurally removes, why a patch does not) · WHAT THEY GET (outcome in customer
  terms) · HOW (delivered/operated). Plus `why` = 2-3 FULL sentences with attacker action + business
  consequence + regulation article ("Credential attacks; panel-CVE surface" is explicitly rejected),
  `what` = full sentences, `exec_summary` must END with the Colt hook.
- BUG that would have silently blocked it: enrich.py did `[str(v) for v in x[k]][:3]` over
  what/why/rem — `str()` on a dict yields "{'tag': ...}". `rem` is now handled separately, tags are
  validated against COLT/PSF/OSS/VENDOR, capped at 5 (the deck draws 5).
- `max_tokens` 5000 -> 8000: the richer bodies need the room (gemma used 2758 out on the thin contract).
- Depth must never be padding: every sentence carries a fact, a number, an article or an outcome.

## Visitor telemetry + security alerting (cybergod.ai) — remember
Three modules in `webapp/backend/app/`, all detection-only (they NEVER block a request and never
touch the firewall — Amnezia VPN shares this host):
- `telemetry.py` — one `evt=http` per request: ip · country · method · path · status · ms · ua ·
  browser · os · device · bot/bot_name · ref · user. Static assets skipped. Client IP = FIRST
  X-Forwarded-For entry (exactly one proxy, videodead-caddy, sits in front). `TELEMETRY_HASH_IPS=1`
  stores salted hashes instead (GDPR minimisation) — off by default because forensics were asked for.
- `notify.py` — Telegram (BOT_TOKEN, ALERT_TG_CHAT or every authed uid) + email via the **Gmail API**
  (SMTP is BLOCKED outbound on this droplet — never "fix" this to SMTP). Never raises.
- `alerts.py` — in-memory sliding windows. 11 rules: login_failed(>2) · password_spray · otp_bruteforce
  · assess_burst(>5 companies) · ddos(>300 req/min from >40 IPs) · ip_burst · path_probe(/.env,/.git)
  · dir_bruteforce · authz_probe(401/403 storm = IDOR) · download_burst(exfil) · session_multi_ip ·
  new_ip_login(INFO). Every rule has a 15-min cooldown per rule+subject AND a 12/hour global storm cap
  — an alert flood is a second outage and gets muted, which is how real incidents get missed.
- Wired in `main.py`: middleware + hooks in auth_begin (fail/success), auth_verify (OTP fail),
  assess (company burst). **`app` is a PACKAGE — use `from . import telemetry`; a bare
  `import telemetry` fails at runtime and the except-swallow would hide it.**
- Config lives in docker-compose.web.yml `environment:` (beats env_file) — no droplet hand-editing.
- Grafana: `obs/grafana/dashboards/webapp.json` rows "Visitors" (visits/unique/humans-vs-bots/devices,
  traffic-per-minute, VISITOR LOG table, top IPs, bots seen) and "Security" (criticals, suppressed,
  delivery failures, alert log with full forensics, auth audit).
- Watch **"Alert delivery failures"**: non-zero means alerts are not reaching you = flying blind.

## Frontend — a passing `vite build` does NOT mean the page works (remember)
`/app` went WHITE while the build was green: NewAssessment threw `useLegalLang is not defined` at
RUNTIME because my import line never got inserted — the real import is `from "../api.js"` (with the
extension) and my anchor searched for `from "../api"`, so the replace silently no-op'd. esbuild/vite
never catch that: an undefined identifier is legal JS until it executes.
RULE: after touching a page component, prove it RENDERS, not just compiles:
  cd webapp/frontend && mkdir -p ssrtmp && (entry.jsx that renderToString's the page)
  ./node_modules/.bin/esbuild ssrtmp/entry.jsx --bundle --outfile=ssrtmp/out.cjs --platform=node \
      --format=cjs --jsx=automatic --loader:.css=empty && node ssrtmp/out.cjs
It prints "RENDER OK" or the exact crash. `ssrtmp/` is gitignored.
Second lesson (same root cause as the store.py `lang` bug): never anchor a code edit on prose or on a
line you did not just read — anchor on something structural, and ASSERT the replace happened.

## GDPR / privacy — the claims are load-bearing (remember)
**ALL privacy/GDPR copy is BILINGUAL (DE + EN) and lives in ONE file: `webapp/frontend/src/legal.jsx`**
(`PRIVACY` = the /privacy page, `NOTICE` = the Art.13 notice on the Assess screen, `useLegalLang()` +
`<LangToggle/>`). German is the REFERENCE text (German customers/regulator), English is the
translation. Language follows the browser (de* -> German), reader-overridable, remembered in
localStorage `cg_legal_lang`. NEVER hardcode legal copy in a page — page and notice must not drift.
`webapp/frontend/src/pages/Privacy.jsx` (route `/privacy`) just renders `PRIVACY[lang]`; the Assess
notice renders `NOTICE[lang]`, is acknowledged once per browser -> `POST /api/privacy/ack` ->
`evt=privacy_ack` for Art. 5(2) accountability.
- **SCOPE (corrected — the user was right):** a privacy notice covers the DATA SUBJECT'S personal
  data, i.e. the platform USER. Shodan/RIPE/crt.sh get the TARGET COMPANY name; the LLM endpoint gets
  the technical findings. Neither receives a user identity, so neither is a recipient of personal data
  and neither belongs in an Art. 44 transfer disclosure. Do not re-add them as "transfers".
- **The claim "Ihre Daten bleiben in der EU" is TRUE and may stand**: app, DB, sessions, decks and
  logs are all on the FRA1 (Frankfurt) droplet, no replication outside the EU.
- **The ONE genuine disclosure: Google (Gmail API)** — it receives the USER'S EMAIL ADDRESS to send
  the OTP and the daily report. That is an Art. 28 processor + a US transfer (covered by the EU-US
  Data Privacy Framework adequacy decision, Art. 45). It must stay named on /privacy.
- The analysis pipeline is described separately as "how it works", NOT as a transfer warning.
- The page states **30-day log retention** — that is enforced by **Loki's retention config**, not by
  colt-web. If Loki keeps logs longer, the page is lying. Verify before showing this to a customer.
- Geo is **country-level only** (Art. 5(1)(c)): `geoip.py` uses DB-IP Country-Lite (.mmdb, MaxMind-DB
  format) — free, NO licence key (GeoLite2 would need a MaxMind account = another secret). Lazily
  downloaded to /data (persistent volume) and auto-refreshed monthly, so `docker build` never depends
  on it. Licence CC-BY-4.0 -> the DB-IP credit on /privacy is REQUIRED, do not remove it.
- `TELEMETRY_HASH_IPS=1` swaps raw IPs for salted hashes (keeps correlation, drops the identifier).
  Currently 0 because forensics were requested — that is a deliberate, documented choice.

## Daily access report (remember)
`webapp/backend/app/daily_report.py` -> emailed to ALERT_EMAIL at DAILY_REPORT_HOUR (07:00 UTC) by an
in-app asyncio task started in main.py. No cron in the container, no systemd unit to drift out of the
repo. It recomputes the next fire time each loop, so a restart cannot double-send.
Sources: the jobs SQLite (who ran what, language, status, deck count) + events.log (logins ok/fail,
visitors, countries, security alerts, AI cost). Manual run:
  `docker exec colt-web python3 -m app.daily_report --print`   (print only, no email)

## Mobile — one responsive PWA, NOT React Native / NOT a second frontend (settled, do not re-litigate)
Decision: make the ONE React app responsive + installable. Rejected: React Native (second codebase,
Play Store account/signing/review, every feature built twice, and it still cannot run a 5-min job in
the background) and a separate mobile HTML build (two frontends that drift — the exact failure that
`legal.jsx` and `de.json` exist to prevent).

**The real mobile blocker was architectural, not CSS:** `_assess_stream` USED TO SPAWN THE ENGINE, so
closing the tab / locking a phone / refreshing cancelled the generator and KILLED a 5-minute run.
Now: `POST /api/assess` -> `asyncio.create_task(_run_job(...))` owns the run server-side, writing
every line to `<jobdir>/run.log` and finalising the DB row. `_assess_stream` is only a VIEWER that
tails run.log. Frames carry `id:` (the line number) so the browser replays `Last-Event-ID` on
reconnect and resumes with no duplicates. `GET /api/assess/{id}/status` is the polling fallback.
`es.onerror` must NOT close the EventSource — closing it defeats the browser's auto-reconnect.
`localStorage.cg_job` lets a phone that evicted the tab re-attach (do NOT preload lines from /status
when re-attaching: a fresh EventSource sends no Last-Event-ID, so the stream replays from 0 and you
would double every line).

Mobile CSS rules that are easy to get wrong (all in styles.css @media max-width:720px):
- inputs MUST be >=16px or **iOS Safari zooms the whole page on focus**;
- `100vh` is wrong on phones (hides under the URL bar) -> `100dvh`;
- respect the notch/home indicator: `viewport-fit=cover` + `env(safe-area-inset-*)`;
- **When repurposing a component with CSS, RESET the properties you are not overriding.** The
  desktop `.side` sets `height:100vh`. The mobile rule changed position/bottom/flex-direction but not
  height — so the "bottom bar" stayed 100vh tall: it COVERED .main (screen looked empty), swallowed
  every tap (nothing clickable) and centred the icons mid-screen. One missing `height:auto` produced
  three symptoms that each looked like a different bug. Always diff the base rule when overriding.
- never `*{max-width:100%}` — it silently caps svgs/inputs/grid children; scope it to img,svg,pre,table
- the sidebar becomes a fixed bottom tab bar (same DOM, CSS only — Sidebar.jsx renders a phone-only
  `.topbar` for brand+logout so the bottom bar is pure navigation);
- never `user-scalable=no` (accessibility).

The LANDING PAGE (`Landing.jsx`, route `/`) is part of the SPA — it is React, NOT a static HTML page,
so it is already covered by the manifest + service worker. Do NOT rebuild it as a separate mobile
HTML file: it would lose the SPA routing/PWA and start drifting. It only ever needed CSS. Its header
(`#hd .wrap`) is a FIXED 58px flex row with brand + 4 section links + a CTA — at 360px those wrapped
inside the 58px box and collided with the brand. Fix: hide the section anchors on a phone (the page is
one scroll anyway), keep brand + one CTA. Also removed a stale `@media(max-width:820px)` that forced
`.side{position:static}` and fought the mobile bottom bar.

PWA: `public/manifest.webmanifest` (standalone, start_url /app, 192+512 icons — Chrome needs both to
offer install, plus `purpose:maskable` because Android crops to a squircle) + `public/sw.js`.
**HARD RULE — the service worker must NEVER cache `/api/`**: decks are owner-scoped behind a session
cookie and the assessment is a live stream; a cached API response is a correctness AND privacy bug.
iOS ignores the manifest icons: it needs `apple-touch-icon` PNGs, and they must be **opaque**
(iOS composites alpha to BLACK) — hence the flattened 180/167/152 variants.

## Enrichment BUDGET — why Huawei produced an English deck (remember; do not shrink these again)
Symptom: `gemma 81s -> timeout · deepseek 81s -> timeout · maverick 82s -> timeout` = English templates.
Cause was ARITHMETIC, not the models: the per-call timeout was `min(ENRICH_TIMEOUT, remaining/models_left)`
= 245/3 = **81s each**, while a 13-finding estate with the RICH rem contract (WHY COLT / WHAT YOU GET /
HOW, max_tokens 8000) needs well past that. I capped every model below the job's actual duration.
Fixed:
- **head-weighted allocation**: the head gets ~55% of what is left (`share = 0.55 if models_left>1`),
  not 1/N — it is the model we want to WIN. Huawei numbers now: 175s / 112s / 93s.
- `ENRICH_TIMEOUT=175`, `ENRICH_BUDGET_S=380` (compose, both web + bots), and run_assessment's enrich
  subprocess timeout raised 270 -> **430** — the pipeline must allow the budget it grants, or it kills
  the chain mid-answer.
- `max_tokens` 8000 -> **6500** and `ENRICH_EVIDENCE_CAP=6`: every extra token is wall-clock. The model
  needs a few concrete host:port examples to be specific, not all 3,971 — capping evidence bounds the
  prompt on big estates (Huawei: 7 ASNs / 71 prefixes / 3971 IPs) without hurting the prose.
RULE: latency scales with FINDINGS x OUTPUT DEPTH. If you deepen the contract, re-check the budget —
otherwise you silently trade German prose for English templates.

## HARD RULE — promtail reads /logs/events.log, NOT stdout (remember)
Live assessments vanished from Grafana the moment colt-web started running the engine as a background
task. Cause: `run_assessment._ev()` was `print(json.dumps(k))` — print ONLY. Promtail tails
`/logs/events.log`; it never reads stdout. It used to work by ACCIDENT: the engine ran inside
colt-assessbot, whose docker stdout is scraped and happens to match `container=~".*assess-bot.*"`.
Under colt-web the engine's stdout is a PIPE (read by the SSE viewer), so nothing reached Loki.
FIX: `_ev()` now writes to stdout AND EVENTS_LOG, and `_pg()` also emits `evt=progress` with `pct`
+ `msg`, so the phase ladder (4/8/56/62/91/99) and every failover are queryable. New dashboard row
"Live assessments — phase by phase".
RULE: never rely on who owns our stdout. If an event must reach Grafana, WRITE IT TO EVENTS_LOG.

## Secrets — `python set_secret.py NAME` (remember; never hand-edit .env over SSH)
Runtime secrets belong ONLY in the droplet's `/opt/colt-stack/assess-bot/.env` (chmod 600), loaded by
colt-web + both bots via env_file. `set_secret.py` upserts one key idempotently, restarts colt-web
(NEVER with --remove-orphans) and verifies it inside the container. The VALUE goes over stdin, never
argv (argv shows in `ps` + shell history). `--list` prints NAMES only, never values.
**LANDMINE:** `deploy.py --reuse` PACKS the local `assess-bot/.env` and extracts it OVER the
droplet's copy (`--exclude env` does NOT match `.env`), while `deploy_web_direct.py` does not ship it
at all. So the LOCAL assess-bot/.env is the source of truth: a secret written only on the droplet is
silently wiped by the next bot deploy. `set_secret.py` therefore upserts BOTH (local first). The local
file is gitignored (`*.env`) so it never reaches the repo; `.env.example` documents the NAMES.

## Attacker digest + abuse reporting (remember; the user asked for third-party auto-reporting — DON'T)
- `webapp/backend/app/threat_intel.py` turns evt=http/security_alert into a per-IP digest with a
  DETERMINISTIC MITRE ATT&CK map (path_probe->T1595.003, ip_burst->T1595.001, login_failed->T1110.001,
  ...). A static table beats an LLM here: the technique is unambiguous, and it is free + reliable.
  It also names the abuse desk per cloud (Azure->abuse@microsoft.com, Censys->abuse@censys.io).
- Folded into the DAILY report (daily_report.py) which now goes to BOTH feranicus@s4biz.io AND
  jevgenijs.vainsteins@colt.net (ALERT_EMAIL is a comma list; notify.email sends to all).
- **Third-party reporting = AbuseIPDB ONLY, opt-in** (`abuse_report.py`, needs `ABUSEIPDB_KEY`).
  DO NOT auto-email BSI/ENISA/ISP abuse desks daily: they don't ingest individual-operator reports,
  and a server that mass-mails abuse gets its OWN domain blocklisted (fatal — it sends OTP over the
  same domain). VirusTotal is for scanning URLs/files, not IP reports. AbuseIPDB is the correct
  community channel; it dedupes per IP (24h) and skips research scanners (Censys/Shodan).
- `security.txt` (RFC 9116, /.well-known/) is the honest monitoring+abuse notice — NOT a page
  claiming false live feeds to BSI/EU/VirusTotal (that would be a compliance-vendor own-goal).

## Cloudflare (planned — see deploy/CLOUDFLARE.md)
Front the SHARED videodead-caddy with Cloudflare free: WAF managed rules + one block rule on
.php/wp-/.env/.git kills today's whole scanner digest; DDoS absorbed; CF-IPCountry fills the country
field. HTTP(S) only -> Amnezia VPN (UDP) + SSH bypass it, untouched. Client IP already reads
CF-Connecting-IP first (telemetry.py). One human step: move GoDaddy nameservers to Cloudflare.
Shared blast radius: it also fronts VideoDead/jobhuntwow — deliberate, documented.

## HARD RULE — every ssh in every script MUST fail fast (remember)
`deploy.py` hung for **40 minutes** at "=== prerequisites (guarded) ===" with zero output. Cause:
its SSH_OPTS had only StrictHostKeyChecking+LogLevel — **no ConnectTimeout, no BatchMode** — and the
hang was inside `sshout()`, which runs with `echo=False`, so not even the command was printed. Same
defect I had already fixed in deploy_web_direct.py and did not carry over.
RULE for EVERY script that shells out to ssh/scp:
  `-o ConnectTimeout=10 -o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4`
Also: a silent read-only probe that returns "" because SSH DIED must NOT be read as "not installed" —
`sshout()` now exits loudly instead, or ensure_docker() would try to apt-install docker over a broken
link. And any long/silent step must print what it is doing BEFORE it blocks.
NOTE: deploy.py opens ~12 separate ssh sessions (sshd throttles rapid repeats); deploy_web_direct.py
uses ONE. Prefer the single-connection pattern for anything new.

## Enrichment JSON — models do not always return an OBJECT (remember)
Bezeq: `gemma-4-31B-it` answered fine after 162s, then `AttributeError("'list' object has no
attribute 'get'")` — it returned a top-level ARRAY `[{...}]` and `_json()` handed the list straight
to `j.get("findings")`. A GOOD answer was thrown away, 162s of the budget burned, both backups then
starved -> English templates. It was MY parser, not the model.
`_json()` + `_normalise()` now handle what models actually emit: object · `[{object}]` (unwrap) ·
bare findings array (wrap) · trailing prose · ```json fences · **and the entries themselves**:
`findings: [[{..},{..}]]` (nested batch -> flatten one level) or a stray string (dropped, logged).
THE SECOND FIX WAS THE REAL ONE: the top-level was already handled, but every consumer does
`x.get("id")`, so ONE list inside `findings` still raised AttributeError and binned the whole answer.
Both consumers (`_audit_cves`, `by_id`) now skip non-dicts as well.
On any parse failure enrich prints the ACTUAL shape (type + keys + entry types); `python
check_enrich.py` reads `<jobdir>/enrich_last.json` off the droplet and shows the raw answer +
finish_reason ('length' = WE truncated it -> raise max_tokens, not a parser bug). STOP GUESSING AT
SHAPES — read enrich_last.json.
Also: the failover line reported the CAP ("bad response after 175s") instead of the real duration —
now prints `took Ns, cap Ns` and the `qwen_attempt` event carries `took_s`. Never report a timeout
number that is not the measured one.

## WHO ordered a run — COLT_USER (remember)
Grafana showed a company with no requester. The engine's events had no user: colt-web/bot never
passed one. Now `env={**os.environ, "COLT_USER": email}` in BOTH `main.py::_run_job` (session email)
and `bot.py::_run_assessment` (authenticated Telegram email); `run_assessment._ev()` stamps
`user` on every event, and enrich's `qwen` event too. Dashboard: live progress shows
`user -> company [pct%] msg`, plus a "Who ordered assessments" table (sum by user, company).
The cost ledger already keyed on COLT_USER — it was simply never set, so cost was unattributed too.
