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
7. **ONE ORCHESTRATOR. ONE COMMAND. ALWAYS.** ← the rule I keep breaking; stop breaking it.
   The user must NEVER be told to run two scripts. Not "run the test then deploy", not "run X then
   Y to verify" — **one** command, every time, in every project. All other scripts are BUILDING
   BLOCKS that the orchestrator calls as subprocesses; they stay individually runnable only for
   debugging, and the user should never need to.
   - In this repo the orchestrator is **`python ship.py`** = test -> commit -> push -> deploy web +
     bots -> verify. Flags narrow it (`--test`, `--web`, `--bots`, `--direct`, `--dry-run`,
     `-m "msg"`), they never split it. `ship_web.py`, `deploy.py`, `deploy_web_direct.py`,
     `test_ca_pivot.py`, `pytest` are all invoked BY ship.py.
   - New capability (a test, a check, a migration, a provisioning step)? **Wire it into ship.py in
     the same change.** A new script that the user has to remember to run separately is a bug.
   - If a reply is about to end with two `python ...` lines, that is the signal: go back and fold
     them into the orchestrator, then give the single command.

## GitHub really is the source of truth — ALWAYS push + tagged safe-points (2026-07)
BUG we hit: ship.py only pushed when IT made a new commit, so commits created outside a ship.py run
(or when the tree was already clean) NEVER reached GitHub — the PC silently drifted ahead of origin.
FIX: `do_git()` now ALWAYS `git push origin main` (prints how many local commits were unpushed),
even with nothing new to commit. Push is idempotent; skipping it breaks the source-of-truth promise.
SAFE-POINTS + ROLLBACK: after a deploy VERIFIES (engine current + /api/me 401), `tag_known_good()`
moves the `last-known-good` tag and writes a dated `good-YYYYMMDD-HHMMSS` tag, pushing both. To undo
any breakage: `python ship.py --rollback` (-> last-known-good) or `--rollback good-<stamp>` — it
`git reset --hard`s the PC (parking local mess in `git stash`) and redeploys that exact state to the
droplet. The droplet has no independent history; it is always rebuilt FROM the repo, so a good commit
on GitHub is the whole backup.

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

## STANDING RULE — always end with the exact command to run — and it is ONE command
After finishing ANY piece of work that the user must trigger, end the reply with a short, explicit
"Run this:" block containing the exact command, copy-paste ready, with the right working directory:

    cd "C:\Python SW\Linkedin Scraper"
    python ship.py

**Exactly ONE `python ...` line.** No vague "you can deploy now"; and never a list of steps like
"run the test, then deploy, then verify" — ship.py already does test -> commit -> push -> deploy ->
verify. If the work added a new step, WIRE IT INTO ship.py in the same change instead of telling the
user about it. If there is genuinely nothing to run, say "Nothing to run." explicitly.
(See operating principle 7. This has been raised repeatedly — treat two commands as a defect.)

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

## Deploy transport — DIRECT SSH from the PC, no Tailscale (2026-07, settled)
Port 22 on 64.225.108.200 is open to the internet and the operator has working SSH to it, so the
GitHub-Actions -> Tailscale -> droplet hop bought nothing and was the ONLY step that ever failed
("Ship compose + Caddy snippet", twice in a row, while Tailscale itself connected fine).
- **`python ship.py` now deploys the web app STRAIGHT FROM THE PC** via `deploy_web_direct.py`
  (~90s, self-verifying). `--ci` opts back into GitHub Actions.
- Tailscale is removed from ALL workflows (`web-deploy.yml`, `deploy.yml`,
  `provision-patchwatch.yml`); they ssh to `vars.DROPLET_HOST` (default 64.225.108.200).
- Every CI ssh/scp carries `ConnectTimeout=15 -o BatchMode=yes`, and the deploy job now begins with
  an explicit reachability probe that fails with a legible `::error::` instead of dying anonymously
  three steps later.
- GitHub remains the source of truth for CODE (ship.py commits+pushes first); only the image BUILD
  location moved. `TS_AUTHKEY` is now unused.

## HARD RULE — verify the DEPLOYED CODE, never just "the site answers"
The bibeltv.de fix was committed, tested and pushed — and the re-run STILL produced the pivot,
because the change never reached the container that runs web assessments:
- `web-deploy.yml` failed at "Ship compose + Caddy snippet"; `colt-web` stayed **Up 3 days**;
- `ship_web.py` ignored the non-zero exit of `gh run watch --exit-status` and printed **DONE**;
- both verifiers only checked `https://cybergod.ai/api/me == 401` — which a THREE-DAY-OLD container
  answers perfectly happily. A liveness probe is not a deploy proof.
- `deploy.py --reuse` did rebuild **colt-assessbot**, so Telegram had the fix while the WEB app did
  not. Two delivery paths, one updated: the engine lives in BOTH images
  (`webapp/Dockerfile` and `assess-bot/Dockerfile` each `COPY hermes-skills/... /opt/shodan-skill`).
RULE: after any deploy, prove the running container holds THIS repo's code by comparing
**sha256 of the engine files inside the container** against the local files —
`ship.py::engine_is_current()` over `ENGINE_FILES` (shodan_recon.py, run_assessment.py, enrich.py)
for BOTH `colt-web` and `colt-assessbot`. On mismatch ship.py self-heals via `deploy_web_direct.py`
and, if it is still stale, EXITS NON-ZERO instead of reporting success. `ship_web.py` now exits 1
when the workflow failed, even if the domain returns 401.
Corollary: never let a script print DONE on a path where a sub-step returned non-zero.

## 5th deliverable — BESPOKE animated GEOPOL HTML (2026-07, two-phase)
The generic combined-report HTML was rejected ("terrible"). The real deliverable matches the
hand-authored exemplars (BibelTV/Stratos/Rosneft `*_GEOPOL_Animated.html`): a 5-scene scrollytelling
page (exposed estate → who is coming → every way in → six moves arrive → secure by design) with five
inline canvas animations, count-up stat bars, teal-on-near-black Colt style.
- **Fixed shell** = `scripts/geopol_html/skeleton.html`, extracted byte-for-byte from the BibelTV
  exemplar: all CSS + the five canvas animations (c1/c2/c3/ddos/sbd) + the defense scenes s3/s4/s5.
  Scenes s1/s2 are placeholders; `{{COMPANY}}`/`{{COMPANY_UPPER}}` tokens elsewhere.
- **`build_geopol_html.js content.json out.html`** assembles the exact s1/s2 DOM (eyebrow, h1, sub,
  statbar, legend, caption) from a small content object and substitutes the company — the layout can
  never drift because only text/numbers are injected. Inline tokens: {hl}/{ink}/{red}/{amber}/{b}.
- **`author_geopol.py`** writes the two bespoke scenes with a DO model (Gemma/Llama/DeepSeek via
  `enrich._call`, the SAME key as the decks; `GEOPOL_HTML_MODEL` overrides), grounded ONLY in
  findings.json + geopol.json. Deterministic fallback so it NEVER blocks the run.
- **TWO PHASES.** run_assessment.py: phase 1 = the 3-4 decks (released), phase 2 (pct 92-99) =
  (a) `audit_fp.py` then (b) the GEOPOL HTML.
- **`audit_fp.py`** = the independent FP auditor: a model from a DIFFERENT vendor than the deck author
  (a 429/blind-spot is provider-wide) reviews every finding's evidence host and, with `--apply`,
  DROPS third-party/client hosts and the engine REBUILDS the findings deck. Emits `evt=fp_audit`.
- Web: `_collect_decks` globs `*_GEOPOL_Animated*.html`; the `.html` download is served inline.
- ship.py smoke-tests the artifact (no undefined/NaN/placeholders leak; all 5 canvases present).

## 5th deliverable — combined animated HTML report (2026-07)
Every run now also emits **`<Company>_Report{_DE}.html`** — one self-contained, dark, scroll-driven
page combining Findings + C-BIQ + GEOPOL in the Colt visual language (Inter/Unbounded/JetBrains Mono,
teal-on-near-black, three.js particle-network hero with a canvas fallback, scroll reveals, count-ups,
an animated loss-exceedance curve, per-actor threat cards, kill-chain timeline).
- Builder: `scripts/build_report_html.js findings.json cbiq.json geopol.json out.html` (Node, no npm
  deps; three.js pulled from the Cloudflare CDN at view time, canvas fallback if it fails).
- Wired into `run_assessment.py` as step 3c (pct 98), added to the DECKS list as the 5th line;
  `DECK_LANG=de` produces the German copy with the `_DE` suffix.
- DEFENSIVE BY CONTRACT: every field guarded; renders cleanly on a thin 5-host estate and on a
  findings-only run (no cbiq/geopol) — the C-BIQ and GEOPOL sections simply omit. Smoke-tested in
  ship.py (asserts no undefined/NaN/[object Object] and that sections are present).
- Web: `main.py::_collect_decks` also globs `*_Report*.html`; the deck download endpoint allows
  `.html` (served inline, text/html) alongside `.pptx` (attachment). Owner-scoped + traversal-guarded
  exactly as the decks are.

## classify() — edge appliances were being buried as LOW (skon.de run #6)
The org: pivot now FINDS the S-KON WatchGuard/Barracuda/SNMP hosts, but the deck still had 3 findings
because `classify()` dumped them into LOW 'standard_service': the WatchGuard has NO product banner and
its cert issuer is 'Firebox webCA', so nothing matched. FIX:
- `_appliance_hit()` detects an edge security appliance by product OR the tell-tale self-signed cert
  (issuer/subject CN/O) — watchguard/firebox/barracuda/sonicwall/fortigate/citrix/ivanti/palo alto/
  sophos/f5/etc. -> CRITICAL 'edge_appliance'. The WatchGuard's only anchor is that cert issuer.
- port 161/162 -> HIGH 'snmp_exposed' (SNMP is a mgmt protocol, never internet-facing).
- self_signed detection broadened: issuer==subject OR a device/private-CA issuer CN ('...webCA',
  '...Issuing CA') that is not a public CA and not an opaque public intermediate.
- New TEMPLATES entries for edge_appliance + snmp_exposed with rich WHY + Colt remediation.
Guarded by test_recall.py §15 (WatchGuard/Barracuda CRITICAL, SNMP HIGH, plain nginx NOT an appliance).

## Recon — org: pivot MUST strip the legal suffix (skon.de run #5, proven from the raw JSON)
The operator's own Shodan exports contained 8 S-KON hosts on three unscanned netblocks — the
WatchGuard Firebox (213.61.141.198), SNMP appliances (213.61.141.196-199), a Barracuda
(217.110.76.91). cybergod's org: pivot returned +0 because it queried org:"S-KON Sales Kontor
Hamburg GmbH" while Shodan stores the whois-org as "S-KON SALES KONTOR HAMBURG AG" — the wrong
LEGAL SUFFIX matched nothing. FIX (generalises to every company):
- `_org_core()` strips GmbH/AG/KG/SE/Ltd/Inc/LLC/S.p.A/… so org:"S-KON Sales Kontor Hamburg" matches
  every legal-form variant (Shodan org: is case-insensitive substring).
- run() now harvests the whois-ORG field (m.org) from swept hosts too, not just the cert subject-O —
  the WatchGuard is self-signed (cert O 'Firebox webCA') so its ONLY anchor is the netblock whois-org.
- Two pivots: `ssl.cert.subject.o:"<full O>"` (proof by itself) + `org:"<suffix-stripped core>"`
  (corroborated per host: the host's own org must carry the phrase, or it ties back independently).
Guarded by test_recall.py §14. The raw JSON confirmed the host IS in Shodan — the miss was purely
the suffix, so this closes it for any target whose appliances live on a whois-org'd netblock.

## Recon — the org: pivot finds SELF-SIGNED edge appliances (skon.de run #4)
The cert-O pivot fired on skon.de ('S-KON Sales Kontor Hamburg GmbH') but returned +0 hosts — the
WatchGuard Firebox is SELF-SIGNED (cert O = 'Firebox webCA'), so `ssl.cert.subject.o:` can never
match it. Its NETBLOCK whois-org, however, IS the company. FIX: the cert-O harvest now runs TWO
queries per brand-token O — `ssl.cert.subject.o:"<O>"` AND `org:"<O>"`. The org: query finds hosts
whose whois netblock is the target (self-signed appliances, mail edges) that the cert query misses.
org: is broader so each host is corroborated (own ASN / brand domain / the O appearing in the host's
org field) before it is kept; the scope_blowout net still guards against over-match.
Also: `ship.py` now re-imports the Grafana dashboards after a bots deploy (`import_dashboard.py --all`,
best-effort, needs GRAFANA_URL+GRAFANA_TOKEN) — a panel edit in assess.json is invisible in Grafana
until re-imported, which is why the FP-audit panels never appeared.

## Recon depth + audit safety (skon.de run #3 — the Opus gap)
Opus's hand-made S-KON deck had 12 findings incl. a WatchGuard Firebox (C-01) on the Colt /30;
cybergod produced 2 and the audit dropped the one critical. Two root causes, both fixed:
1. **The crown-jewel host was never scanned.** skon.de fronts on Google with a DV cert (no
   subject-O), so the seed gave brand token `skon` only — never the strong
   `ssl.cert.subject.o:"S-KON Sales Kontor Hamburg GmbH"` anchor. FIX: `run()` now HARVESTS the cert
   subject-O from the SWEEP hosts (the WatchGuard presents the OV O) and re-pivots on
   `ssl.cert.subject.o:` when the O carries a brand token — pulling in the owned Colt-netblock hosts
   the seed cert never revealed. (Parallel to the internal-CA harvest; brand-token gated so it can't
   blow scope.)
2. **The audit dropped a legit scanned host.** `run()` now records `scanned_ips` (every host recon's
   ownership gate KEPT = owned by definition); `run_assessment` persists it to `target.owned`; and
   `audit_fp._host_is_off_estate()` never drops a host recon scanned. Recon is the ownership
   authority; the LLM auditor is a backstop that can flag but not overrule it.
Audit is now VISIBLE: run_assessment prints `FP-AUDIT: auditor=X vs deck-author=Y -> verdict/…`,
the `fp_audit` event carries author+auditor+verdict+dropped+refused, and Grafana has an
"FP audit" row (audits run, dropped, refused, dirty verdicts, + an auditor-vs-author ledger table).
NOTE (honest): closing the FULL Opus depth gap (detecting every category Opus writes — edge-appliance
class, HTTP/2 DoS, PKI hygiene, verbose banners as distinct findings) is iterative detector work in
`classify()`, tracked separately. This change restores the hosts + stops the audit deleting them.

## HARD RULE — the FP auditor may FLAG but must never gut the deck (skon.de, run #2)
The independent FP-audit LLM (audit_fp.py) turned a CORRECT skon.de run (19 real hosts, zero client
FPs) into an EMPTY deck: deepseek flagged all 3 findings and --apply dropped all 3 -> CRIT/HIGH/MED/
LOW all 0. Cause: the auditor made ownership calls with NO ownership data and rejected the legit
S-KON hosts because they sit on Google/Microsoft-365 shared IPs. An auto-fix that can empty a deck is
worse than no audit.
FIX — auto-fix is now corroborated + guardrailed:
- `run_assessment` persists the OWNED-SET into findings.json (`target.owned` = domains, pinned IPs,
  brand_tokens, asns, related_unscoped).
- `audit_fp._host_is_off_estate()` drops a flagged finding ONLY if the DETERMINISTIC owned-set agrees
  it is off-estate (evidence IP not pinned, no owned domain, no brand token). A pinned host is ours
  by definition. Missing owned-set -> never corroborated -> keep.
- HARD GUARDRAIL: never drop into an empty deck, and never drop >40% of findings — if the auditor
  over-flags, KEEP everything and record them as `refused`. `evt=fp_audit` now carries dropped+refused.
RULE: an audit is a SIGNAL, not an authority. The auditor is chosen to be a DIFFERENT model than the ACTUAL deck author (`target.qwen.model`, the model that won enrichment after any failover) — `_pick_auditor()` prefers a different vendor, guarantees a different id, and refuses to audit rather than self-audit. `FP_AUDIT_MODEL` overrides only if it is not the author. Guarded by test_recall.py §13. The LLM's flags are applied only where deterministic
ownership data confirms them, and can never empty or gut a deck. Guarded by test_recall.py §12.

## ZERO FALSE POSITIVES — the ownership gate (skon.de, 2026-07)
S-KON is a loyalty-platform operator: it runs white-label microsites (`vorteile.otto.de`,
`vorteile.mediamarkt.de`, `praemie.tng.de`, `aktion.eam.de`) FOR its clients. The recall step
(CertSpotter + cert-SAN + DNS probe) discovered all of them, pinned their ISP IPs, and produced a
**746-host** deck — 718 hosts on the clients' ISPs (TNG AS13101, DNS:NET AS15366) — for a customer
with **2 real hosts** (its two /29+/30 blocks under Colt AS8220). The client microsites are the
CLIENT's attack surface, never S-KON's.
FIX — every discovered domain/host now passes an OWNERSHIP GATE (`_owns_apex`), fail-closed:
- A discovered registrable apex enters scope ONLY if it == the seed apex OR its label carries a
  BRAND TOKEN. Tokens come from the seed label PLUS the seed's live TLS **cert subject-Organization**
  (`_cert_info` / `_brand_tokens_from`): seed `skon.de` gives `skon`; the OV cert O
  "S-KON Sales Kontor Hamburg GmbH" adds `kontor`, so saleskontor/praemienkontor/managementkontor/
  ekontor24 resolve as owned while otto.de / mediamarkt.de / tng.de / eam.de do NOT.
- `_MICROSITE_PREFIXES` (vorteile/praemie/aktion/bonus/...) on a non-brand apex are hard-excluded.
- The DNS probe runs on OWNED apexes only; pinned IPs come only from owned hostnames.
- Excluded apexes are recorded in `ident["related_unscoped"]` (context, never scanned/pinned).
POSITIVE SCOPE: the seed cert subject-O becomes the Shodan filter
`ssl.cert.subject.o:"<org>"` — the single highest-yield, near-zero-FP pivot (catches every
target-certificated host on any ASN). `cat="pinned"` on the pinned-host query bypasses run()'s
hoster/CDN drop, so legitimately-pinned S-KON hosts on Google/Host Europe survive.
RULE: a discovered domain is a CANDIDATE, not proof of ownership. On a platform/agency/hosting
target, only the brand-token / cert-O / owned-netblock set is in scope; a client's domain in the
customer's own deck is a false positive. Guarded by `scripts/test_recall.py` (§9-§11).

## RECALL — the other half of the bibeltv.de lesson (2026-07)
Fixing the scope blow-out swung the deck to the opposite failure: 5 hosts, 2 findings, and it MISSED
`gitlab.bibel.tv` (SCM) and `vpn.bibeltv.de` (remote-access edge, on **Colt AS8220** — the pursuit
hook). Precision without recall is just a different way of being wrong.
THREE CAUSES, all fixed in `shodan_recon.py`:
1. **A sibling DOMAIN was never discovered.** `bibel.tv` is a different registrable domain from
   `bibeltv.de`; CT enumeration of `%.bibeltv.de` can NEVER reveal it. Fix: `_cert_sans()` reads the
   seed's live TLS certificate and harvests the SAN list — a shared certificate IS evidence of common
   operation, which is the ownership standard a scope-widening step must meet.
2. **crt.sh was a single point of failure** — read-timeout, 404 and 503 on three consecutive runs,
   and it was the ONLY subdomain source. Fix: `_certspotter_domains()` (SSLMate, free, no API key)
   runs alongside it.
3. **Nothing asked DNS.** Fix: `_probe_subdomains()` resolves a curated ~60-name list
   (gitlab, vpn, mail, git, ci, jira, owa, ftp, autoconfig, ...) against every known apex. A name
   that RESOLVES is proof the host exists — one query each, passive, ~1s total.
**Resolved IPs go in `ident["pinned"]`, NOT `ident["nets"]`.** `run_net` is disabled whenever the
holder is a hoster/CDN (to stop a /16 Hetzner sweep), so anything added to `nets` is silently dropped
for exactly the shared-hosting targets this rescues. Filter #2b "Pinned hosts (DNS-resolved)" always
runs: a /32 the customer's own DNS points at is not a hoster range.
Identity clauses (cert-CN, hostname, http.host) are emitted for APEX domains only — `hostname:".bibel.tv"`
already covers `gitlab.bibel.tv`, so one clause per discovered subdomain just multiplies Shodan credit
burn. And never write `hostname:".<fqdn>"` for a full host — the leading dot means "under this domain".
RULE: on a shared-hosting target (no owned ASN) the ONLY valid scope is
**pinned host IPs + hostname/cert identity**. Guarded by `scripts/test_recall.py`.

## HARD RULE — a pivot must PROVE ownership (the bibeltv.de 1003-false-positive incident)
`bibeltv.de` shipped a deck claiming 1003 exposed IPs — cPanel resellers in Brazil, Shopify, AWS,
DigitalOcean droplets in Japan — for a small German broadcaster that actually has **5 hosts**. The
deck contradicted itself: the ASSET INVENTORY slide said "5 HOSTS · 2 ASNs" while the findings were
computed over 1003. Nothing in the pipeline objected.
CAUSE: the internal-CA pivot auto-harvests issuer CNs off the estate and re-searches Shodan for them.
Its only guard was a substring match against `PUBLIC_CAS` ("let's encrypt", "digicert", ...). But
**Let's Encrypt issues under bare codes R3/R10-R14/E1-E9 and Google Trust Services under
WR1/WE1/YR2** — CNs containing NO vendor name. `'R12'` and `'YR2'` were therefore taken for the
customer's PRIVATE CA and `ssl.cert.issuer.cn:"R12"` was run against ALL of Shodan.
2 pivots x 500 `limit_per_query` = 998, + the 5 real hosts = the 1003. The arithmetic is exact.
FIX (`shodan_recon._private_ca_ok`, tested by `scripts/test_ca_pivot.py`) — the gate **fails closed**:
1. extended `PUBLIC_CAS`; 2. `_OPAQUE_CA_RE` rejects short opaque codes (`R12`,`YR2`,`WE1`,`X3`);
3. the CN must carry a **brand token** (compared against a SQUASHED CN — "Bibel TV Issuing CA 01" vs
token `bibeltv` never matches with the space in it) or CA wording; 4. the decisive vendor-agnostic
test — `api.count()` on the issuer: anything signing **> PIVOT_MAX_HOSTS (2000)** hosts globally is
shared by definition; 5. if `count()` is unavailable, CA-wording alone is NOT enough (every public CA
has it) — only a brand token passes. Plus `_corroborates()`: a pivot may only ADD a host it can tie
back independently (own ASN / brand domain in rDNS or cert / brand in org).
SAFETY NET, independent of the gate: `run()` records `scope_blowout` when the final host set exceeds
`max(25, 4x)` the hosts the identity queries actually proved, and `run_assessment.py` then emits
`evt=scope_blowout` and **exits 3 rather than building decks from an unverified estate**.
RULE FOR EVERY FUTURE PIVOT: a pivot widens scope, so it must produce EVIDENCE OF OWNERSHIP, not just
a match. Never let a selector that can match the whole internet (a public CA, a shared hoster ASN, a
generic favicon, a common JARM) become an ownership anchor. Recall is cheap; a stranger's
infrastructure in a customer deck is not.
LATENT TWIN, also fixed: the domain-seed path re-checks the ASN holder against CDNS/CARRIERS, but the
NAME-seed path in `autodiscover()` never did — seeding "Bibel TV" instead of "bibeltv.de" would have
adopted AS24940 (Hetzner) as an OWNED ASN and swept every other tenant. Now both paths check.

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
UPDATE (2026-07): ConnectTimeout/ServerAlive only kill a DEAD transport, NOT a slow live
remote command — deploy.py hung 6+ min at 'checking docker' when sshd throttled the ~10th rapid
connection. FIX: every subprocess.run in deploy.py now has a hard `timeout=` (read-only probes 30s,
builds 600s, scp 300s); on TimeoutExpired it kills the process and fails legibly. `sshout()` retries
a timed-out read-only probe 3x with back-off so a transient sshd throttle can't kill the deploy.
ship.py ALSO skips the whole bots rebuild when colt-assessbot is already current (FORCE_BOTS=1 to
override). The web app deploys+verifies BEFORE the bots step, so it is live regardless.
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

## HARD RULE — parsing is not answering (remember; this one was silent)
After I made `_json()` tolerant of shape, `gemma-4-31B-it` returned `{}` in 4s (tokens_out=**3**).
It parsed fine -> status "ok", `qwen_used=true`, $0.0043 charged, and a DELTAS deck built with NO
deltas in it. A SILENT quality failure — strictly worse than an honest fallback, because the log
stops admitting anything is wrong and the deck ships empty.
`_contract_ok(j, tokens_out)` now runs on every answer: reject if not a dict, if completion tokens
< 50, or if there is no exec_summary AND no findings with an id. Rejection raises -> the chain fails
over. Tolerate any SHAPE; NEVER tolerate an EMPTY answer.
Bonus: an empty answer is rejected in ~4s, so the backup inherits almost the whole budget instead of
starving.
gemma on this account is ERRATIC on the same prompt: 53s/2758 tok (good) · 81s timeout · 162s ->
top-level list · 4s -> {}. If it keeps failing, re-run `python compare_models.py --lang de` and
consider promoting deepseek-3.2 back to head — but decide from `check_enrich.py`, not from theory.

## Assess clarification loop — deliver FIRST, then ask (2026-07; jobhuntwow gap->answer model)
The Assess flow is now conversational, modelled EXACTLY on jobhuntwow's Tailor (docs/TAILOR_LOGIC.md
§4): the four decks + animated GEOPOL HTML are delivered FIRST, THEN the engine surfaces what recon
could not resolve as clarification questions. The operator answers / adds facts and a REFINE run
re-scopes and rebuilds. Answers are the ONE sanctioned way scope changes after the first run — the
human asserts the fact, so the zero-false-positive ownership gate stays intact.
- Questions are DETERMINISTIC (`scripts/clarify.py::build(fj)`), NOT LLM — auditable, free, never
  hallucinates a domain. Each is machine-actionable via `maps_to`. Triggers: related_unscoped domains
  ("which are yours?"), no-owned-ASN / CDN-fronted ("known netblocks/ASNs?"), thin estate (<6 hosts,
  "known VPN/mail/gitlab hosts?"), a prune list of current findings ("anything NOT yours?"), and an
  always-present free-text notes box. run_assessment.py writes `clarify.json` to the jobdir at the end
  of every run and emits `evt=clarify`.
- Refine overrides (run_assessment.py): `--exclude-domain` (apex/host/IP force out of scope),
  `--pin` (exact host IP to scan), `--platform-operator` (keep client domains out), `--notes`
  (free-text -> enrich via COLT_NOTES + GEOPOL). Threaded into `shodan_recon.autodiscover(...,
  excludes=, pins=, platform_operator=)`: excludes force-unown an apex in `_consider_domain` and drop
  matching hosts (by IP or hostname/rDNS/cert-CN under the apex) in `run()` after all pivots; pins
  append to `ident["pinned"]` (scanned via the always-on pinned-host filter). Existing
  `--domain/--asn/--net/--org` already cover the INCLUDE side.
- Web: `GET /api/assess/{job}/clarify` returns the questions; `POST /api/assess/{job}/refine` maps
  answers (keyed by `maps_to`) -> flags via `main.py::_refine_flags` (IP->--pin, CIDR->--net,
  ASxxxx->--asn, domain->--domain, "not mine"->--exclude-domain) and launches a CHILD job that streams
  like the original. Frontend `NewAssessment.jsx` shows a "Refine this assessment" panel after the
  decks (checkbox chips for include/exclude, text fields, platform toggle, notes) -> `assessRefine`.
- Guarded by ship.py smoke (`clarify.build` on the sample: every question carries a valid `maps_to`,
  the notes question is always present). Deploys with the ONE command `python ship.py` (colt-web +
  colt-assessbot both carry the engine change; engine-hash verify proves the container holds it).

## Compliance module — NIS2 / CRA / EU AI Act (2026-07; 4th cabinet section)
A SECOND assessment type beside Assess/Assistant/History, same "one company-name input -> AI decks +
deliver-then-refine" UX as the security Assess. It grades a company against NIS2, the Cyber Resilience
Act and the EU AI Act and produces 3 regime decks + a combined roadmap deck + an animated HTML report
(EN/DE). Input is the COMPANY NAME ONLY: the LLM INFERS the scoping assumptions (sector, size band,
sells-digital-products?, builds/deploys-AI?, countries) and STATES them; the post-run clarification
loop is how the operator confirms/corrects them (answers OVERRIDE the inference).
- Engine (all in hermes-skills/shodan-assessment/scripts, so BOTH images already COPY it):
  `compliance_enrich.py` (LLM grounded ONLY in `compliance/EU_COMPLIANCE_REFERENCE.md` -> compliance.json;
  reuses enrich._call/_chain/_json; DETERMINISTIC fallback holds the FIXED facts — obligations,
  deadlines, penalty maxima are company-independent, so the decks are correct even with no model,
  applicability just reads "requires confirmation"); `build_compliance_deck.js` (ONE parametrized
  pptxgenjs builder for nis2|cra|aiact|roadmap, Colt palette, EN/DE via a local label map — does NOT
  use deck_i18n); `build_compliance_html.js` (self-contained animated report, no deps);
  `compliance_clarify.py` (deterministic questions: sector/size_band/sells_digital/builds_ai/countries/
  notes); `compliance_assess.py` (orchestrator: enrich -> 4 decks -> HTML -> clarify.json -> PROGRESS/
  events + "ASSESSMENT COMPLETE"; refine flags --sector/--size-band/--sells-digital/--builds-ai/
  --country/--notes).
- Backend: `settings.COMPLIANCE_ENGINE`; `_run_job(engine=, seed_flag=)` now selects the engine
  (compliance uses `--company`, security uses `--seed`); `POST /api/compliance` (start) +
  `POST /api/compliance/{job}/refine` (`_compliance_refine_flags`). The streaming/status/deck/clarify
  endpoints are SHARED (engine-agnostic, keyed by job_id) — no `kind` column needed, and `_collect_decks`
  already globs `*.pptx` + `*_Report*.html` which catches the compliance artifacts.
- Frontend: `pages/Compliance.jsx` (+ Sidebar nav + Cabinet route + api startCompliance/complianceRefine).
  Reuses the clarify panel; adds the `choice`/`yesno` question kinds.
- Ship: ship.py smoke builds the deterministic compliance.json + a regime deck + roadmap deck + HTML
  (no undefined/NaN leaks) + clarify; compliance_assess.py/compliance_enrich.py added to ENGINE_FILES
  so the engine-hash verify proves the container holds them. ONE command: `python ship.py`.
- NOT legal advice — the reference and every deck footer say so; deadlines/penalties are quoted from
  the primary legal texts as at 20 Jul 2026 and should be re-checked (national NIS2 transposition moves).

## HARD RULE — the HOSTER's identity is never the TARGET's (rightmart.de, 2026-07)
rightmart.de shipped a deck with **1,417 IPs "in scope" and 78 evidence IPs, ZERO of them the
customer's** — every one belonged to IP-Projects (its shared hoster) and that hoster's other tenants.
The customer's real estate (`pve.` Proxmox hypervisor, `akte.` case-file system, `api.` on a Bremen
carrier line) was DISCOVERED and printed in the log, then buried under the hoster's address space.
ONE decision caused all of it, and it cascaded:
1. `resolve_identity` adopted **AS48314** (holder "IP-PROJECTS Michael Sebastian Schinzel trading as
   IP-Projects GmbH & Co. KG", ~130 prefixes) as rightmart's own ASN — the old gate only refused
   holders in CDNS/CARRIERS, and no keyword list can ever name every hoster. 24 of ITS prefixes were
   swept as if the customer owned them.
2. The seed's cert-O and netblock whois are the HOSTER's, so `_brand_tokens_from` harvested
   `michael, projects, schinzel, sebastian, trading` as the customer's "brand tokens".
3. `_brandish()` then read those tokens back out of hoster org strings and authorised THREE org:
   pivots — `+343`, `+120` (**Marcus Hoffmann / VCServer Network, a completely unrelated hosting
   company**, matched purely on the tokenised phrase "trading as"), `+119` = **+582 hosts**.
FIX — one principle, applied at every anchor: **an identity anchor must CORROBORATE the seed brand.**
`_org_is_the_target(org, seed_ref)` squashes both and requires the seed label to appear in the org
(or a distinctive org token inside the seed label). Fails CLOSED with no seed label.
  * `_brand_tokens_from` — an org contributes tokens ONLY if it corroborates; otherwise it logs the
    refusal and contributes nothing. S-KON still works ('S-KON Sales Kontor' contains 'skon' -> keeps
    'kontor'); rightmart's hoster contributes nothing.
  * `resolve_identity` — the seed IP's ASN is adopted ONLY if the holder corroborates AND is not
    provider-shaped. Otherwise -> `shared_asns`, `org_is_cdn=True` (reusing the proven "cert/hostname
    only" path), no prefixes swept.
  * `autodiscover` name-seed ASN loop — same gate.
  * cert-O pivot — `ssl.cert.subject.o:` is the HIGHEST-precision pivot when the O is the target's and
    the LOWEST when it is the hoster's Plesk cert. Rejected unless it corroborates.
  * `_looks_like_provider()` — SECONDARY signal only: "trading as"/hosting/rootserver/datacenter
    markers, CDNS/CARRIERS, or **>20 announced prefixes** (no SMB announces 130).
RULE FOR EVERY FUTURE ANCHOR: a name that arrives from infrastructure the customer merely RENTS
(whois-org, netblock holder, hoster cert-O, PTR domain) is evidence about the PROVIDER, not the
customer. Guarded by `test_recall.py` §16.
STILL OPEN from the rightmart forensics (not yet implemented): FP audit is not blocking when
`auditor=none` (D5); vuln findings/KEV badges are not suppressed when the plan skipped `vuln:` (D6);
ASN-holder names on the inventory slide are not re-resolved at render time (D7); slide counts come
from more than one metrics object (D8); framework set is not bound to the detected industry (D9).

## Certificates are the highest-yield identity source — harvest CN + SAN (rightmart.de, 2026-07)
The operator's own Shodan export found 13 real rightmart hosts by CERTIFICATE CN that the run never
surfaced — including the whole engagement's best finding: **`email-archiv-rightmart.de`**, a mailcow
mail archive on IMAPS/993 with a SELF-SIGNED, **EXPIRED** certificate. For a §203-StGB law firm that
is privileged client correspondence.
WHY IT WAS INVISIBLE: it is a SEPARATE REGISTRABLE DOMAIN, not a subdomain — CT enumeration of
`%.rightmart.de` can never return it, and the DNS probe list never guesses it. Its certificate names
it outright. Identical class to the bibeltv.de -> bibel.tv sibling.
FIX: `_cert_names(m)` extracts subject-CN + every subjectAltName from each swept host, and `run()`
harvests them BEFORE the org pivots. A name whose apex passes `_owns_apex` (brand token / seed apex)
is added to `ident["domains"]` and its host IP is PINNED — a cert naming the target is proof of
ownership. A co-tenant's cert can never drag its own domain in, because the ownership gate still runs.
GOTCHA: Shodan stores the SAN extension with the raw DER length prefix attached, sometimes as real
control bytes and sometimes as the LITERAL text `\x0c`. Blank both to a space before the regex or you
extract `x0crightmart.de` instead of `rightmart.de`. Guarded by test_recall.py §17.

## Enrichment chain order is EVIDENCE, not taste — gemma demoted (2026-07)
Why gemma-4-31B-it "fails a lot": it was the HEAD of the chain, so it took the largest slice of the
budget (55% = 175s), timed out at exactly that cap, and burned ~46% of the whole enrichment budget
producing nothing — leaving deepseek only 112s. It is also erratic on IDENTICAL input (measured:
53s/2758 tok good · 81s timeout · 162s top-level list · 4s `{}` · 175s timeout), and it was the ONLY
model in the chain **never measured by compare_models.py on the real prompt**.
The real-prompt bake-off measured deepseek-3.2 at 25.0s and llama-4-maverick at 44.6s, both
contract-valid with good German. So `_FALLBACKS` is now
`["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it"]` — fastest-and-best measured first, erratic
last (kept as a third chance, not deleted).
ALSO: a `finish_reason == "length"` is OUR max_tokens ceiling truncating the JSON mid-string, not a
model fault — it surfaced on rightmart as `JSONDecodeError at char 30117` against max_tokens=6500 and
was reported as a generic "bad response". `_call()` now says so explicitly. Raise max_tokens or send
fewer findings; do not blame the model. Re-decide order with `compare_models.py` + `check_enrich.py`.

## angermann.de — the brand-token gate failed in BOTH directions (2026-07, group discovery)
The deck found **1 of the customer's 8 domains** and added 2 that belong to a law firm. ONE
mechanism caused both halves: `_owns_apex`'s brand token.
- too LOOSE: "Angermann" is a SURNAME -> ra-angermann.de (Rechtsanwalt), renner-angermann.de,
  angermann-webdesign.de and a *Zahnarztpraxis Angermann* all matched.
- too TIGHT: the subsidiaries trade as **NetBid / Nord Leasing / leaseback / buerosuche** — ZERO
  string overlap with the seed — so CT, cert-SANs and the DNS probe could never reach them. They
  held the best findings in the engagement (netbid.io mail cluster: **expired cert on 7 ports**).
FIX = `scripts/group_discovery.py`: crawl the customer's OWN site for its group-structure pages
(struktur/gruppe/companies/auf-einen-blick/...) and harvest the external domains they link to. A
first-party published roster is STRONGER ownership evidence than a substring, and it works in both
directions:
- **recall**: a domain on the structure page is owned even with a totally different name;
- **precision**: when a structure WAS published, a lookalike apex absent from it is positive
  evidence it is someone else's -> rejected as `lookalike`, surfaced via clarify.py for the
  operator to confirm. Never silently dropped.
- **fails closed**: no structure page (or no network) -> `structure_known=False` -> the historic
  brand-token behaviour is untouched, so the S-KON `kontor` recall is unaffected. An outage must
  never silently shrink a customer's estate.
Group domains are ALSO put to the operator, because a group page lists joint ventures and global
network brands the customer does not run (Angermann's M&A arm trades as Oaklins Germany AG, but
oaklins.com is a worldwide network's shared infrastructure).

## CO-TENANT GUARD — a netblock is not a customer (angermann.de)
`217.110.51.0/24` is a **shared Colt /24**: Angermann holds .2 and .7; the rest is Nordrheinische
Aerzteversorgung (a doctors' pension fund), FACT, NAGASE, Regus and Mane — with their SNMP,
MikroTik Winbox and Exchange exposure. Shodan carries a **per-IP whois org**, so the discriminator
was already in the data. `run()` now keeps a host only if its OWN org corroborates the target, or
it carries one of the target's names, or an identity query found it. Replayed against the real
export: **2 Angermann IPs kept, 22 co-tenants dropped.** Guarded by test_recall.py S18.

## model_watch.py — the catalog check is now part of every deploy
The chain is chosen from EVIDENCE, but that evidence goes stale silently: gemma sat at the head
returning empty answers for weeks, and **DeepSeek V4 Flash ($0.112/$0.224 per 1M) shipped while we
still run V3.2 ($0.425/$1.36)** — ~4-6x cheaper — and nothing looked. `ship.py` now ends with
`model_watch.py`: GET /v1/models, diff against committed `models_seen.json`, report NEW and
DISAPPEARED ids, and probe new text models with the REAL enrichment contract (never a toy prompt —
latency ranking INVERTS with prompt size: maverick 3.3s toy vs 44.6s real). **Non-blocking by
design**: a new model is information, not a broken build.
**Kimi K3 is auto-flagged DO-NOT-CHAIN.** DO's own changelog says it is "tuned for max thinking
effort by default" — exactly the reasoning-model failure mode that already broke the strict-JSON
contract with deepseek-r1-distill and qwen3.5-397b. DO has **not published a K3 serverless rate**
(pricing page verified 1 Jul 2026 lists K2.5 and K2.6 only). It is a candidate for ATTRIBUTION
research (1M context, long-horizon agentic), never for the deck-prose JSON contract.

## The angermann NameError outage — why unit tests did not catch it (2026-07, HARD RULE)
I shipped `if seed_apex:` into `shodan_recon.run()` where the local is `_seed_apex0`. Production
crashed on every assessment. test_recall/test_ca_pivot/pytest ALL passed, because they exercise
HELPERS (`_owns_apex`, `_org_is_the_target`, `_apex`) and NOTHING executed `run()`. A NameError only
fires when the line runs.
THREE gates added, in ship.py, in this order:
1. **`ruff check --select F821,F811,F822`** over engine + webapp + root. Catches undefined names
   STATICALLY in under a second. F-rules (pyflakes) only — real bugs, never style. F401 excluded:
   an unused import is not an outage. This alone would have stopped the incident.
2. **`scripts/test_run_path.py`** — EXECUTES `run()` against a mocked `shodan` module and asserts the
   co-tenant guard's outcome on the real shared Colt /24. GOTCHA: the engine calls
   `api.search_cursor()`, so a stub providing only `.search()` silently yields ZERO hosts and the
   test passes while testing nothing. Filter dicts also need `"run": True` or the sweep is skipped.
3. The error handler itself was broken: `print("PROGRESS: [100%] FAILED — %s: %s" % (...))` raises
   `ValueError: unsupported format character ']'` because `%]` is read as a format spec. So the real
   traceback was MASKED by a second exception. Fixed to `[100%%]`. **RULE: a literal % in a
   %-formatted string must be `%%` — and the failure path must be exercised, not assumed.**

## group_discovery — the first cut harvested M&A CLIENTS (2026-07, tightened)
Loose hints (`gruppe|unternehmen|portfolio|about`) matched EIGHT pages on the live angermann.de —
newsroom, references, careers, history — and returned 15 "subsidiaries" including **spiegel.de** (a
press mention), **xing-share.com** (a share widget) and **bewatec.com / vesselbid.com /
clarus-am.com / einkaufsfinanzierer.com / executive-solutions.de** (M&A TRANSACTION CLIENTS of the
Oaklins arm). Putting an M&A client's estate in the adviser's deck is exactly the S-KON failure.
FIXES: STRUCTURE_HINTS is now narrow and matched against the URL **path** only (anchor text is
useless — "Gruppe" is in every German nav); ANTI_HINTS hard-excludes
newsroom/presse/referenz/transaktion/projekt/objekt/karriere/archiv/historie/team/kontakt/impressum;
WIDGET_RE drops share widgets (but NOT `utm_` — a campaign param is normal on a legitimate internal
link, and matching it silently deleted the real subsidiary buerosuche.de); major DACH + global MEDIA
domains are in NOISE_APEX; MAX_PAGES 8 -> 4. Verified 7/7 subsidiaries, 0/8 traps.

## Co-tenant guard — `identity_ips` is NOT proof of ownership
`identity_ips = set(hosts)` is assigned AFTER every filter has run, so on a net/prefix sweep it
contains the co-tenants too. Skipping on it meant the guard never fired. Only a **pinned** host
(resolved from the target's own DNS) is ours by definition. Guardrail, same doctrine as audit_fp:
if the guard would drop >75% of hosts it REFUSES and keeps everything (`cotenants_refused`) — an
automatic filter that can empty a deck is worse than no filter. Guarded by test_run_path.py.

## A2Z RECON STRATEGY — the five things that close the manual-vs-platform gap (2026-07)
The operator's acceptance criterion, verbatim: *"I do not want to have any difference between what
I harvest in shodan with manual filters and using our platform."* That is now a TEST
(`scripts/test_parity.py`, wired into ship.py) that replays his real angermann.de exports (75
host:port) and FAILS THE DEPLOY on any regression. The five changes, in order of impact:

**1. Subsidiaries must be SCANNED, not merely "owned".**  `group_domains` was consulted by the
ownership gate but never added to `ident["domains"]` — and `ident["domains"]` is what drives CT
enumeration, the DNS probe and the `hostname:`/cert-CN clauses. netbid.com was "owned" and never
searched, which is why the second angermann deck was byte-identical to the first. Each subsidiary is
now a first-class seed with its own CT enumeration and subdomain probe.

**2. Sibling TLDs of a published group domain.**  The structure page names netbid.com; the group's
MAIL cluster (expired cert on SEVEN ports — the best finding in the engagement) is netbid.io.
Matched on EXACT registrable label, so netbid-fake.com can never qualify.

**3. Vendor-hosted tenants (`_owns_host`).**  angermann.de's 3CX PBX is `angermann.3cx.eu` on
netcup — the apex belongs to 3CX, so `_owns_apex` rejected it, yet the certificate names the
customer outright. TENANT_APEX covers 3CX/M365/Zoom/Atlassian/Azure/Heroku-class vendor domains and
requires the label to EQUAL a brand token. **Consumer dynamic-DNS is deliberately EXCLUDED**
(dyndns.org, ddns.net, no-ip.org, synology.me): anyone can register any label there, and including
them admitted `praxisangermann.dyndns.org` — a DENTAL PRACTICE — into a property group's deck.

**4. High-value management planes (`_high_value_hit`), checked BEFORE the port buckets.**
217.110.51.7 served *"Passbolt | Open source password manager for teams"* behind nginx on 443, so
classify() filed it as `standard_service` and the deck reported **CRITICAL 0** while an
internet-facing PASSWORD VAULT sat on the perimeter. New CRITICAL detectors: `secrets_manager`
(Passbolt/Vaultwarden/Bitwarden/Vault/Keycloak/CyberArk), `nas_exposed` (Synology/QNAP/TrueNAS —
the #1 SME ransomware target), `backup_console` (Veeam/Acronis — own the backups, own the recovery);
HIGH: `pbx_exposed` (3CX/Asterisk/FreePBX — toll fraud + the CVE-2023-29059 supply chain). Detection
is by product AND http.title AND cert CN, because a reverse proxy hides the product. Each has a full
TEMPLATES entry (3 why-sentences + 3 Colt-first remediation objects), so the decks are not empty.

**5. The chain is now cheapest-proven-first, and the droplet can no longer override it silently.**
`_FALLBACKS = deepseek-v4-flash -> deepseek-3.2 -> llama-4-maverick -> gemma-4-31B-it`.
V4 Flash is $0.112/$0.224 per 1M vs V3.2's $0.425/$1.36 (~4-6x cheaper, same vendor lineage,
instruct not thinking). gemma is LAST because it is measured erratic on identical input.
**ship.py now AUTO-CORRECTS a drifted `ENRICH_MODELS` on the droplet** (sed + colt-web restart)
instead of printing "run set_secret.py" — a stale env var beat the committed chain for weeks and
kept gemma at the head, and telling the operator to run a second script breaks the one-command rule.

STILL OPEN (honest): the 3CX host reaches scope via `_owns_host`, but nothing yet ENUMERATES vendor
tenant space proactively (we find it only if a cert or CT record names it). A `ssl.cert.subject.CN:
"<brand>.<vendor>"` sweep per TENANT_APEX entry is the next increment.

## ENRICH_MODELS — the chain was hardcoded in COMPOSE, which beats everything (2026-07)
deepseek-v4-flash never ran even after `_FALLBACKS` was changed AND deployed. Cause: BOTH
`docker-compose.web.yml` and `docker-compose.reuse.yml` carried
`- ENRICH_MODELS=gemma-4-31B-it,deepseek-3.2,llama-4-maverick` under `environment:`, and compose
`environment:` BEATS `env_file:`. So the committed chain could never take effect, and
`set_secret.py ENRICH_MODELS` (which writes assess-bot/.env) could not override it either. Two
sources of truth for one value = the bug; gemma stayed at the head for weeks as a result.
FIX: the compose lines are DELETED (with a comment saying why). `enrich.py::_FALLBACKS` is now the
single default; `.env` remains the per-deployment override. ship.py gained a static guard that
FAILS the deploy if `- ENRICH_MODELS=` reappears in any compose file, and its drift check now
DELETES a stale .env override instead of rewriting it.
RULE: if a value has a documented home in code, compose must not restate it.

## DNS probe scope — recall is cheap, speculative probing is not
Feeding subsidiaries into discovery took the angermann run 27s -> 181s and produced 122 "live"
subdomains, 14 of them under oaklins.com (a GLOBAL M&A network whose careers-nl / porto2026 /
bedrijf-verkopen infrastructure is not the customer's). The ~60-name wordlist costs one DNS query
per name PER APEX. Now the speculative probe runs ONLY on the seed and brand-carrying apexes;
non-brand group domains still get full CT enumeration (which is what actually found the real
netbid/leaseback/nordleasing names). ~63% fewer DNS queries, same recall.

## /api/diag + engine_config.py — stop guessing where config lives (2026-07, operator's fix)
The operator: *"maybe its a good idea to make some sort of API? and not to hard code things and
then try to guess where they are and what is working or not"* — correct, and this cost three
deploys. The enrichment chain had **FOUR** homes and we found them one at a time:
  1. `enrich.py::_FALLBACKS`            the committed, evidence-based default
  2. `docker-compose.*.yml environment:` BEATS env_file — silently defeated (1) for weeks
  3. `.env ENRICH_MODELS`               documented per-deployment override
  4. `.env ENRICH_MODEL` **(singular, LEGACY)** — prepended as the chain HEAD by `_chain()`, so it
     silently REORDERS the chain. This is why deepseek-v4-flash sat at position 2 and was never
     called even after (2) was deleted: 3.2 was promoted to head and won on attempt 1.
`scripts/engine_config.py` RESOLVES the effective config and reports it WITH PROVENANCE — chain,
head, every source and whether they conflict, plus detectors loaded, budgets and engine file
sha256. It never re-implements logic: it imports `enrich._chain()` and asks. Served at
**GET /api/diag** (authenticated) and printed by every `python ship.py`. ship.py now deletes BOTH
`ENRICH_MODEL` and `ENRICH_MODELS` from the droplet .env.

## Deck title slide — a summary belongs in the footer, an inventory does not
Once group discovery started enumerating the whole corporate group, `target.scope` interpolated
EVERY domain: ~4,000 characters rendered into a 3.1-inch DATA SOURCE footer box, which is what
"all the letters are on top of each other" was. `_scope_line()` now emits
`ASN — · 0 prefixes · 7 domains: a.de, b.de +5 more (144 hostnames)` (90 chars). The full
inventory already has its own slide. Also separated the two creed text boxes (they overlapped by
0.01in).

## deploy.py — sshd THROTTLING is what kills the bots step (2026-07)
`python ship.py` failed at `printf 'LOKI_URL=...' > .env` — a trivial write — after 90s. The droplet
was healthy; OpenSSH simply refused the ~13th rapid connection (MaxStartups / PerSourcePenalties).
CLAUDE.md ALREADY recorded the cause ("deploy.py opens ~12 separate ssh sessions... prefer the
single-connection pattern") and it had never been applied to deploy.py itself.
FIX, three parts:
- `inspect()` batches the whole read-only inventory into ONE session (was five).
- configure + build + `ps` is ONE session (was three) with a 900s ceiling for the compose build.
- `ssh()` retries once after 5s on a timeout/refusal, so a transient throttle costs seconds, not
  the deploy. Session count 18 -> 12.
NOTE: the WEB app deploys BEFORE the bots, in a single-session script (deploy_web_direct.py), which
is why cybergod.ai was already updated when this failed. Only colt-assessbot (Telegram) was stale.

## A gate that silently skips is not a gate
ship.py printed `[!] ruff not installed - static name check SKIPPED` on every run on the operator's
machine. That check is the one that would have caught the angermann NameError outage, and it had
been skipping since the day it was added. ship.py now pip-installs ruff once and re-runs the check
(operating principle 1: no manual steps).

## A phantom model id — "DeepSeek V4 Flash" is not `deepseek-v4-flash` (2026-07)
I put `deepseek-v4-flash` at the HEAD of the chain from DigitalOcean's PRICING PAGE. The API
returned **HTTP 404 on every call**: a marketing name is not an API model id. Each assessment burned
a wasted round-trip and silently degraded to deepseek-3.2. CLAUDE.md ALREADY warned about this
("Catalog ids are exact and easy to get wrong: it is `openai-gpt-oss-120b`, NOT `gpt-oss-120b`") —
repeated anyway, because NOTHING CHECKED.
Why model_watch.py did not catch it: it needs OPENAI_API_KEY, which lives on the DROPLET, not the
operator's PC, so it printed "catalog unavailable - skipping" every single run. **A check that
cannot see the thing it checks is not a check** — same class as the silently-skipped ruff gate.
FIX: `scripts/model_probe.py` runs INSIDE colt-web (`docker exec`, where the key is) and asserts
every id in the effective chain exists in the live `/v1/models` catalog. Free, zero tokens, and
BLOCKING — ship.py exits non-zero on a MISSING id and prints difflib near-matches so the correct id
is obvious. `--all` probes every text model with the real JSON contract for latency + validity.
Chain is back to the MEASURED `deepseek-3.2 -> llama-4-maverick -> gemma-4-31B-it`.

## Enrichment coverage was measured against a flag nobody set
`run_assessment` computed coverage from `_enriched`, but only enrich_parallel.py ever set it —
enrich.py did not. So a run where deepseek-3.2 rewrote ALL SIX findings measured **0%** and fired a
pointless map-reduce top-up (which then also 404'd on the phantom head model). enrich.py now sets
`f["_enriched"] = True` on every finding it rewrites, so the coverage number is honest and the
top-up only fires when the model genuinely under-delivered.

## Model chain — kimi-k2.6 at head, from a LIVE 66-model probe (2026-07)
`model_probe.py --all` inside colt-web measured the whole catalog with a real contract call. Facts:
- **`deepseek-v4-flash` does not exist; `deepseek-4-flash` does** (200 ok, but 16,043ms on a TINY
  prompt). The pricing-page name was never an API id.
- **`kimi-k2.5`/`kimi-k2.6` return HTTP 400, NOT 403/404** — they exist and the key is entitled; the
  request SHAPE was rejected. `enrich._call()` already retries `if e.code in (400,422)` by dropping
  `response_format`, which is the documented cause, so Kimi is very likely healthy in production
  even though the raw probe fails. model_probe gained `--via-enrich` to test the REAL path, plus
  payload-variant retries and capture of the API's error BODY (discarding it is how Kimi got written
  off twice).
- Entitlement map: anthropic-* and commercial openai-gpt-* = **403** (visible != entitled);
  openai-gpt-oss-120b / nemotron-3-super-120b / router:* = **429** (account quota).
- Contract-valid and fast: deepseek-3.2 **870ms**, qwen3-coder-flash 894ms, mistral-3-14B 1334ms,
  mimo-v2.5-pro 1838ms, gemma 3615ms, maverick 3837ms.
- 200-but-JSON-INVALID: kimi-k3, glm-5/5.1/5.2, minimax-m2.5, qwen3.5-397b, nemotron-*,
  deepseek-r1-distill. Reasoning/thinking models keep failing the strict-JSON contract.
CHAIN: `kimi-k2.6 -> deepseek-3.2 -> llama-4-maverick -> gemma-4-31B-it`. Kimi is head by operator
preference and is UNPROVEN on the real 10k-char prompt — its failure mode is a ~280ms 400 and an
instant failover, not a 175s timeout, so the downside is bounded. Confirm with
`model_probe.py --via-enrich` and `compare_models.py --lang de`; latency ranking INVERTS with prompt
size, so the toy-probe numbers above rank validity, not real-workload speed.

## Deck text overflow — the boxes were sized for the OLD contract (2026-07)
"the text is slipping": on the FINDING slides `why` ran straight through the confidentiality footer
and each remediation body ran into the row beneath it. Cause is arithmetic, not rendering:
- WHY box  w4.55 h0.46 @8.0pt  = ~243 chars, but the enrichment bible demands 3 full sentences
  (~400-500). Footer sits at y5.32; the box started at 4.82 and overflowed straight into it.
- rem body w3.85 h0.30 @7.4pt  = ~148 chars, but the rem contract demands WHY COLT / WHAT YOU GET /
  HOW (~450). Worse, `rowH` was a FIXED 0.62in sized for five rows, so a typical three-row finding
  left 1.24in of the column EMPTY while its text overflowed.
FIX: `fitText(t,w,h,pt)` computes real capacity (~0.5*pt/char wide, ~1.25*pt/line high, 72pt/inch)
and trims on a word boundary with an ellipsis; rem rows now use an ADAPTIVE rowH
(`min(1.05, (5.24-2.06)/rows)`), so 3 rows get 370 chars of body instead of 148.
TEST GAP THAT LET IT SHIP: test_deck_quality only inspected SLIDE 1. It now walks EVERY slide and
additionally asserts no body text crosses y5.32 (the footer). Verified against real 502-char
deepseek `why` + 449-char COLT bodies: worst ratio 0.99x, zero footer collisions.

## max_tokens truncated the head model — that is the "thin deck" (2026-07)
`[warn] OUTPUT TRUNCATED at max_tokens=6500 (finish_reason=length, 13290 chars)` then
`JSONDecodeError at char 13290`. deepseek-3.2 did not fail: WE cut it off mid-JSON. The chain then
failed over to llama-4-maverick, which COMPLETED but wrote only 2,367 output tokens for six
findings (~395/finding vs deepseek's ~1,500) — that is exactly the "very small amount of addon
text" in the deck. The rich contract (3 sentences of `why` + three WHY-COLT/WHAT/HOW bodies) needs
roughly 1.5k tokens per finding, so six findings never fit in 6500. Raised to **11000**
(~108s at the measured 102 tok/s, inside the 175s head cap with 67s headroom).
SECOND, DEEPER BUG: coverage measured PRESENCE, not DEPTH. maverick rewrote all six findings, so
`_enriched` was true for every one, coverage read **100%**, and the map-reduce top-up never fired
on a deck that was visibly thin. `run_assessment` now computes `_depth(f)` (what + why + rem
titles/bodies) and only counts a finding as covered above `ENRICH_MIN_CHARS` (default 420).
Measured: a deepseek finding scores ~2,190 chars, a maverick one ~260 — so a thin run now reads 0%
coverage and the parallel shards fill it in.
RULE: "the model answered" is not "the model delivered". Measure the artifact, not the status code.

## Kimi solved — "temperature must be 1 for this model" (2026-07)
Three rounds of treating kimi-k2.5/k2.6 as broken, and the API had been saying why the whole time:
    HTTP 400 {"message":"temperature must be 1 for this model","type":"invalid_request_error"}
We send temperature=0.35. That is the ENTIRE bug. It was invisible because both the probe and
`enrich._call` discarded the HTTPError BODY — the one field that contained the answer.
FIXES:
- `enrich.MODEL_PARAMS` = per-model REQUIRED overrides, matched on id prefix (`kimi` -> temperature
  1.0), applied in `_call` before the request. Encode the constraint; do not guess at it.
- `_call` now PRINTS the API's error body on any 400/422 before retrying.
- `model_probe._post` imports the same `_model_params`, so probe and production can never disagree
  about what a model requires.
- Chain: `kimi-k2.6 -> deepseek-3.2 -> llama-4-maverick -> gemma-4-31B-it`.
CAVEAT TO WATCH: the probe reported "ACCEPTED, 0 chars back" at max_tokens=300 — Kimi reasons
before answering and a small ceiling can be entirely consumed by thinking. Production sends
max_tokens=11000 with enable_thinking=false, so it should have room; if `qwen` events show kimi
returning empty, `_contract_ok` rejects it in seconds and deepseek-3.2 takes over.
RULE (third time this exact lesson has cost a round): NEVER discard an API error body. A 4xx is the
server telling you what it wants.

## Public DEMO — "Trojan Empire" (/demo, 2026-07)
A fourth front door beside Assess / Compliance / Assistant, open to ANONYMOUS visitors: the real
deliverables, built by the real deck builders, from FABRICATED data for a fictional company.
- **PRE-BAKED, never a live run.** `scripts/demo_build.py` writes findings.json -> `RA.derive_cbiq`
  / `RA.derive_geopol` -> the 3 pptx builders + `author_geopol.py`, once, into `/data/demo` (the
  persistent `colt_webdata` volume). Running the engine per visitor would burn Shodan credits and
  inference tokens on an invented company and a crawler could drain both; and the numbers are
  invented anyway, so there is nothing to discover. `_ensure_demo()` builds under a
  `threading.Lock` (public endpoint = concurrent cold visitors = half-written .pptx) and an
  `on_event("startup")` executor warms it so the first visitor never waits ~40s.
- **SAFETY = RFC 5737.** Every fixture IP is in 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24,
  reserved by the IETF so it can never route to a real host. A real address in that fixture would
  be an unsolicited, unauthorised public exposure claim about a stranger's machine. ship.py greps
  the fixture SOURCE for dotted quads and FAILS THE DEPLOY on anything outside those ranges.
- **Honesty is in the artifacts, not only on the page.** The decks carry the FABRICATED notice on a
  slide and demo_build injects a fixed gold banner into the animated HTML — those files get
  forwarded by email and a link carries none of /demo's context. ship.py asserts both.
- **A file existing is not a file being right.** The first cut called `build_geopol_html.js` with a
  content file that was NEVER WRITTEN; node rendered the bare skeleton, a 35KB html appeared, the
  build printed success — and every headline was `<h1></h1>`. Fixed by going through
  `author_geopol.py` (deterministic path, no model needed) exactly as run_assessment does, plus a
  self-check that DELETES a hollow shell. ship.py now asserts 0 blank headings, 5 canvases, the
  company name and the banner.
- Endpoints are public and engine-free: `GET /api/demo` (meta + artifact list) and
  `GET /api/demo/deck/{name}` (traversal-guarded, .pptx attachment / .html inline).
  `webapp/frontend/src/pages/Demo.jsx` + route `/demo` + a `.btn` nav link on Landing (it must be a
  `.btn` — the phone rule `#hd nav a:not(.btn){display:none}` would hide a plain link, and this is
  the one entry point an anonymous visitor can use). Access note: live assessments are Colt
  employees + Colt Partners only -> jevgenijs.vainsteins@colt.net.
- `_APP_ROUTES` in main.py::_is_probe must list every App.jsx route (it was already stale).
- NOTE, deliberate and unchanged: `BOT_404=1` serves crawlers a 404 on page routes, so /demo is
  NOT indexable by Google. Flip with `BOT_404_ALLOW="googlebot,bingbot"` if the demo should be
  found by search; that is a product decision, not a bug.

## The /demo hero is a Cassandra FILM, not an illustration (2026-07)
Two hand-drawn Trojan horses were rejected ("beyond terrible ... it doesnt look like horse"). A flat
geometric rebuild read better but still was not good enough. The operator supplied a 10s cinematic
clip of Cassandra on the walls of Troy; that is now the hero and the SVG is DELETED (no dead code).
- Assets are COMMITTED binaries: `webapp/frontend/public/media/cassandra.mp4` (2.4MB, h264/aac,
  1280x720, remuxed with `-movflags +faststart`) + `cassandra-poster.jpg` (frame 0). vite copies
  `public/` verbatim, so they land in `dist/media/` and are served by main.py's `spa()` static branch.
- **Autoplay MUST be muted** — every browser blocks audible autoplay, and a hero that silently
  refuses to start is worse than none. The clip has real audio (mean -24.4 dB), so there is an
  explicit sound toggle. `playsInline` stops iOS grabbing fullscreen. `prefers-reduced-motion` gets
  the poster + controls, no autoplay.
- **faststart is verified, not assumed**: if `mdat` precedes `moov` the browser buffers the whole
  file before the first frame. ship.py reads the header and FAILS the deploy on a bad layout.
- **Range requests were checked, not trusted**: Safari will not play a `<video>` served as a single
  200 blob. Starlette 0.46 `FileResponse` answers `206 + Content-Range` — proven with a TestClient
  request against the same class `spa()` uses, not by reading release notes.
- `sw.js` does not match `.mp4`/`.jpg`, so the service worker passes the video straight through —
  caching it would both bloat the shell cache and break range/seek.
- ship.py gate: every `"/media/..."` string in Demo.jsx must exist in `public/`, be >10KB, and the
  mp4 must be faststart. vite never validates a src string and SSR renders it as text, so a missing
  binary is invisible until a customer sees a black box.

LESSON KEPT FROM THE ABANDONED AVATAR: when judging a visual, RENDER IT AND LOOK — `cairosvg` -> PNG
-> read the image, iterate. Nine versions were judged from pixels, and the final SVG was re-rendered
*as emitted by the React component* to prove the JSX matched the approved artwork. Same doctrine as
the engine-hash deploy verify: check the artifact, not the intention. (It still was not good enough,
which is the other half of the lesson: iterate against a human, not against your own taste.)

## lotto24.de — a whois ADDRESS became the identity anchor (2026-07)
`org:"Lotto24 AG Hamburg, Germany"` returned **+381 hosts** against 15 the identity queries had
proved, and the whole assessment died with "assessment failed" — no decks at all.
ROOT CAUSE: `_LEGAL_SUFFIX` is anchored with `$`, so it strips a legal form only at the END of the
string. That org ends in "Germany", so NOTHING was stripped and the CITY AND COUNTRY were shipped to
Shodan as the anchor. `org:` is a FULL-TEXT match, not string equality, so "Hamburg, Germany" matched
every Hamburg-registered netblock.
FIX 1 — `_org_core()` truncates at a MID-STRING legal form. The discriminator is POSITIONAL and is a
property of company registration, not a heuristic: in a registered name the legal form comes LAST, so
anything after a mid-string one is address.
  "Lotto24 AG Hamburg, Germany"     -> AG is mid-string -> "Lotto24"
  "S-KON Sales Kontor Hamburg GmbH" -> GmbH is final    -> "S-KON Sales Kontor Hamburg"  (unchanged)
  "Rosneft Deutschland GmbH"        -> GmbH is final    -> "Rosneft Deutschland"          (unchanged)
This is exactly why a place-name word list CANNOT work: "Deutschland" is part of Rosneft's registered
name while "Hamburg" is Lotto24's address. Only position tells them apart.
FIX 2 (the important one) — **PER-PIVOT BUDGET + WHOLE-PIVOT ROLLBACK**. Every downstream guard
worked exactly as designed and the run still died: the co-tenant guard correctly flagged 379 of the
381, hit its own >75% "an automatic filter must never empty a deck" valve, refused, and the
scope-blowout check then aborted everything. Three correct guards composed into a total failure.
RULE: a pivot exists to WIDEN scope at the margin; it may never OWN the estate. `_accept_pivot()`
collects each pivot's hosts and rolls the WHOLE pivot back (hosts + its ASNs, so a bad selector
cannot widen a later sweep) when it adds more than `max(PIVOT_MAX_ADD=60, 3 x identity_hosts)`.
Recorded in `ident["pivots_rolled_back"]`. Replayed on the real numbers: 381 > 60 -> rolled back ->
estate ~23 -> under the blow-out threshold of 60 -> **the decks build**. This defence does not depend
on anyone having spotted the bad string, which is the point.
FIX 3 — the co-tenant guard reported "dropped 379 of 783" on an estate of 404: it computed the
denominator AFTER the restore loop, double-counting. Snapshot before restoring. A guard that
misreports its own arithmetic sends the next investigation down the wrong path.
Guarded by test_run_path.py (the lotto24 section). NOTE the test bug this exposed: the original fake
`shodan` returned every record for EVERY query, so the identity sweep already held the junk and a
per-pivot assertion measured nothing — `_install_routing_shodan()` routes by query substring. A fake
that cannot tell the queries apart cannot test a per-query rule.

## lotto24.de round 2 — 0% enrichment coverage, 18 minutes, a template deck (2026-07)
The scope fix worked (decks built), but every finding rendered CANNED TEXT: `coverage 0/6 = 0%`,
`qwen_used: false`, `total_ms 1119415`. FOUR independent faults, none of them "the model was bad":

1. **The map-reduce top-up had NEVER worked, in any run.** `enrich._call()` returns `(text, usage)`;
   `enrich_parallel._call_shard` did `raw = E._call(prompt)` and handed the TUPLE to `_json()`:
       'tuple' object has no attribute 'find'
   Every shard errored, every time, and the log blamed a model. FIX: `raw, _usage = E._call(...)`.
   A two-value return caught in one name is invisible until something calls a string method.
2. **Two of the four "model timeouts" were ARITHMETIC.** `max_tokens` is 11000 = ~110s at the
   measured ~100 tok/s, while the chain's per-call FLOOR is 60s. So models 3 and 4 were each issued
   a request that could not physically complete, and each burned its full 60s failing.
   FIX: `feasible_max_tokens(seconds)` sizes the request to the slice it was given (60s -> 4800 tok).
   Shorter real prose beats template text, and it beats spending the budget on nothing.
   RULE: never issue a request whose completion time exceeds its own timeout.
3. **Kimi was rejected for `response_format` and then hung.** The API said, verbatim,
   "response_format type 'json_object' is not supported for this model". The 400-retry recovered but
   cost a round trip, and the retry then consumed the whole 175s head slice — three times over
   (serial chain + both shards) = ~7.5 min of an 18-min run for zero output. FIX: `MODEL_PARAMS`
   gained `_drop`, so kimi is never SENT response_format. Encode a known constraint; do not pay a
   400 every call to rediscover it.
4. **Kimi DEMOTED from head** — on evidence, reversing the earlier "its downside is bounded" note,
   which was wrong: the fast 400 is retried transparently and the retry hangs. Head is now
   `deepseek-3.2` (measured 25.0s, contract-valid, good German on the REAL prompt). Kimi stays in
   the chain. Restore it with ENRICH_MODELS if a future probe justifies it.
   Also: shards inherited `E.MODEL` (the head) with NO failover, so the top-up hit the identical
   wall the serial chain had just hit — `_call_shard` now takes an explicit model and the targeted
   retry uses a DIFFERENT one.
Guarded by test_recall.py §19 (shard returns findings · every slice can finish · kimi's payload ·
chain head). LESSON: "the model failed" is a conclusion, not an observation — check whether the
request we sent could ever have succeeded.

## The shards were sent a prompt with NO CONTRACT (lotto24.de DE run, 2026-07)
The tuple fix worked — `COVERAGE 6/6 = 100%` in 33s — and the deck was STILL thin. Measured from
the delivered .pptx, finding H1: `what` 38 chars (a template sentence), `why` 259 chars (ONE
sentence; the contract demands three), and ONE `rem` row where the slide renders five.
ROOT CAUSE: `enrich.PROMPT` is a **%-FORMAT TEMPLATE** with three placeholders
(bible, language block, findings). The serial path does `PROMPT % (_bible(), lang, slim)` = 12,844
chars. `enrich_parallel._call_shard` CONCATENATED instead: `E.PROMPT + E.LANG_DE + "..."` = 2,462
chars — so three literal `%s` were sent to the model AND the entire 10,435-char DELTAS BIBLE (the
rules that demand 3 sentences of `why` and 3-5 WHY-COLT/WHAT/HOW `rem` objects) was DROPPED. The
model was asked for a vague rewrite and delivered exactly that.
FIXES:
- `_call_shard` now formats the prompt the same way the serial path does, plus the subset clause.
- **Coverage measures DEPTH, not presence, on BOTH sides.** run_assessment already applied a
  `_depth()` >= ENRICH_MIN_CHARS floor to the serial call; enrich_parallel scored its own coverage
  as "did an id come back", so thin shards reported 100% and the caller stopped worrying.
- Each shard now records `tokens_out` and `tok/s`. Every timeout diagnosis so far has turned on the
  account's real throughput and we have been estimating it; now it is in the log.
STILL OPEN (measured, not yet fixed): the MONOLITHIC 6-finding call has now failed 8/8 model
attempts across two runs (deepseek 175s, kimi 112s, maverick 60s, gemma 60s — twice), while
3-finding shards succeed in ~30s. The single whole-estate call is too large to complete on this
endpoint and burns ~407s of every run before the shards rescue it. The fix is to make sharding the
PRIMARY path and leave the serial chain only the short estate-level prose (exec_summary/strengths).
Decide it from the new tok/s telemetry rather than from theory.

## Rebrand: Cybergod LLC / S4Biz Group — customer-facing only (2026-07)
The product is no longer presented as Colt. NOTHING a customer sees says Colt; infrastructure names
(`colt-web`, `colt-assessbot`, `colt-stack`, `colt_events`, `colt_auth.py`) are DELIBERATELY
unchanged — they are cosmetic internally and renaming them would touch compose, the deploy scripts,
the Caddy block and every Grafana query for zero customer benefit.
- **The `COLT` remediation tag is an ENUM and was NOT renamed.** It is a lookup key in `tagMap`,
  `TAGWORDS` and enrich's tag validation; renaming an enum makes rows silently vanish (the standing
  hard rule). Instead `tagLabel = {COLT: "MANAGED", ...}` rebrands the CHIP TEXT at render time.
  Same doctrine as the i18n rule about severity enums. `coltControl` is likewise a JSON key shared by
  the engine and the builders — only its VALUE is rendered, so the key stays.
- **Remediation is now VENDOR-NEUTRAL** ("Managed Firewall", "SASE / ZTNA", "Managed DDoS
  protection") instead of naming Colt products. That is not a compromise: the audience is resellers
  who sell their OWN stack, and a VAR selling Fortinet will not hand a customer a competitor's
  product name.
- Per-slide wordmark "colt" -> "cybergod.ai" in all five deck builders. The box was 0.85in wide and
  the new string is ~3x longer, so each was widened to 2.05in and the font dropped — a wordmark that
  clips is worse than one that is stale.
- ship.py has a BRAND GATE over EVERY surface a user touches, not just the web pages: 6 rendered
  decks (EN+DE), 5 React pages, `index.html` (browser tab), `manifest.webmanifest` (the name a PHONE
  puts on the home screen), BOTH Telegram bots, and the OTP email subject. It greps the RENDERED
  artifact and strips code comments — grepping raw source would false-positive on the enum forever.
  THE FIRST PASS MISSED FOUR OF THOSE (PWA manifest, tab title, both bots, OTP subject) because I
  only looked at React pages and deck builders. A rebrand is not "the website"; it is every string
  that reaches a human. The Cassandra SYSTEM PROMPT was the sharpest one: it is not a comment, it is
  the instruction that made the assistant describe itself as Colt in every reply.
- Marketing (`marketing/*.md`, the release GIF) carries Cybergod LLC · S4Biz Group and
  WhatsApp +351 939 994 642. The access gate no longer mentions employees of anyone.

## The dot-directory scanner gap + WhatsApp as a real channel (2026-07)
**THE LEAK.** A scanner asked for `/.svn/wc.db` and got **200**, then triggered a "a person just
opened cybergod.ai" alert. Two independent defects:
1. `_is_probe` looked for the substring `"/."` AFTER `strip("/")` had removed the leading slash, so
   `.svn/wc.db` never matched. `.aws/credentials` and `.ssh/id_rsa` leaked identically — the three
   highest-value paths a scanner asks for (source, cloud keys, private keys). FIX: `_DOTSEG`
   matches any path SEGMENT starting with a dot; `/.well-known/` is the one exemption (ACME,
   security.txt). Extra hints added: .db .sqlite .pem .key id_rsa credentials backup dump.
2. **The visitor alert trusted the USER AGENT.** The scanner announced itself as "Safari / iOS /
   mobile", so the UA-based bot check passed and the alert claimed a human had arrived — on a path
   no human has ever typed. RULE: a user agent is ATTACKER-CONTROLLED; the path they requested is
   the evidence. `visitors._probe_path()` now suppresses the alert by PATH regardless of UA, and
   logs `visit_suppressed reason="probe path (spoofed UA)"` so the sighting is still queryable.
Deliberately NOT added: IP blocking or firewall rules. Amnezia VPN shares this host and the standing
rule is detection-only. The 404 + AbuseIPDB (opt-in) remain the response; Cloudflare WAF is the
documented next step if volume justifies it.
NOTE: `/null` in the logs is OUR bug class, not an attack — referrer was our own /login. It is now
classified as a probe so it stops paging, but if it recurs from real browsers, find the null href.

**WHATSAPP.** `OPERATOR.whatsapp` (wa.me deep link) joins email/LinkedIn/Telegram/GitHub as a
first-class channel: a card on /contact (listed FIRST — shortest time-to-reply), a prefilled deep
link on /demo, and `WhatsAppFab` — a floating button on the public pages. The FAB exists because the
phone tab bar already holds six items and a seventh makes every target too small; contact is an
ACTION, not a place. Before it, the installed PWA had NO way to contact anyone at all. It clears the
tab bar with `bottom: calc(76px + env(safe-area-inset-bottom))`.
**A BLIND SUBSTITUTION BUG WORTH REMEMBERING:** the Colt rebrand replaced the email address inside
`href={`mailto:${CONTACT}...`}` with the string "WhatsApp +351 939 994 642", producing
`mailto:WhatsApp +351...` — a dead link — and mangled the Telegram demo's `/auth` line the same way.
Search-and-replace across code must be verified on the RENDERED output, which is how both were found.

## Site-wide German + real navigation (2026-07)
**NAVIGATION.** Only the landing page had a header. /demo, /contact, /privacy, /impressum and /login
were DEAD ENDS — the only way out was the browser back button, which an installed PWA does not even
show. A visitor arriving on /demo from LinkedIn had no route to anything else. `components/
SiteHeader.jsx` is now on every public page. On pages other than the landing page the section
anchors render as `/#edge` links rather than in-page jumps that would silently do nothing.

**ONE LANGUAGE SWITCH FOR THE WHOLE SITE.** `legal.jsx::useLegalLang()` already existed, already
defaulted from the browser (de* -> German) and already persisted to `localStorage.cg_legal_lang`.
`i18n.jsx` REUSES that exact hook and key rather than introducing a second store — two language
states is precisely the drift legal.jsx was created to prevent. The toggle lives in SiteHeader, so
switching it moves the marketing copy AND the privacy text together.
- `tr(lang,key)` falls back EN -> key, never throws. An incomplete translation degrades to readable
  English, exactly like `deck_i18n.js`. `I18N_STATS()` reports coverage so a gap is a number.
- The Assess screen's DOCUMENT language now defaults from the site language (it was hardcoded "en",
  so every German user re-picked it on every run) but stays overridable — the reader's language and
  the customer's are not always the same.

**TELEGRAM CANNOT SHARE localStorage**, so "switch them together" cannot mean one control. The
honest equivalent: every surface defaults from the SAME signal — the user's own client language —
and remembers a per-user override.
- Both bots gained `/lang de|en`, persisted (assess-bot writes `lang.json` next to the auth store).
- Default is Telegram's `language_code`, so a German user gets German without asking.
- assess-bot: a user who has run `/lang` is NOT asked the language question again on every /assess.
- cassandra: language is enforced in the SYSTEM PROMPT (`LANG_INSTRUCTION`), not by translating a
  few canned strings — for an LLM assistant, translating the wrapper while every generated answer
  stays English is worse than not translating at all.

## The language toggle only moved the component it lived in (2026-07)
Symptom, reported from the live site: "when I move to German I need to refresh the page or move to
contact and only then everything is in german". Same in reverse.
CAUSE: `useLegalLang()` was a plain `useState`. Every component that called it got its OWN
independent copy — SiteHeader, Landing, Demo, Privacy and NewAssessment each held a separate piece
of state seeded from localStorage. Clicking the toggle set the HEADER's copy and re-rendered the
header; nothing else was subscribed to anything, so nothing else could know. The other components
only picked up the new value when they happened to REMOUNT, which is exactly what navigating to
another page or refreshing does. The state was never shared, so there was nothing to notify.
FIX: ONE module-scope store in legal.jsx (`getLang`/`setLang`/`subscribe`) read through
**`useSyncExternalStore`** — React's supported way to subscribe to an external mutable source. One
writer, many readers, all of them re-render on change. No context provider to wrap the tree in, and
every existing caller of `useLegalLang()` got the fix without being touched.
Also: `setLang` writes `document.documentElement.lang` (a11y + browser spellcheck), and `subscribe`
listens for the `storage` event so a SECOND OPEN TAB switches with the first.
RULE: a value that more than one component renders is APPLICATION state, not component state.
`useState` inside a shared hook silently gives every caller a private copy — it compiles, it renders,
and it is wrong only when two components disagree.
Guarded by an SSR test that flips the store between two renders and asserts BOTH pages changed.

## Mobile header + tab bar: measure the row, do not eyeball it (2026-07)
The phone header wrapped onto three lines and the buttons overlapped the brand. Two regressions,
both introduced by me in the same change:
1. **The tab bar got the NAV labels.** It used to read Why / Live / Machine; I swapped in
   `nav.why` = "Why it matters", so six labels sharing a 360px row each wrapped to two lines.
   FIX: separate `tab.*` keys, SHORT by contract (<=8 chars, asserted in both languages). A tab
   label and a nav link label are different strings for a reason.
2. **"Deutsch / English" is ~110px of text** — a third of a 360px header on its own. FIX: each
   toggle button renders BOTH labels (`<span class="lg">Deutsch</span><span class="sm">DE</span>`)
   and CSS picks by width. No JS, no resize listener, no second source of truth; `aria-label` keeps
   the full word for screen readers.
3. **The header CTA was a duplicate.** Measured: brand 158 + toggle 70 + Demo 50 + "Open the app"
   112 + gaps = 422px, which does not fit even a 412px phone. The bottom tab bar's last item is
   already Open -> /login, so the header CTA is hidden on every phone: the row becomes 326px.
RULE: a fixed-height horizontal bar is an arithmetic problem. Add up brand + every control + gaps
against 360px BEFORE shipping — the guard here is a test that computes the row width in both
languages, because German is systematically longer and will overflow first.

## The COLT AS8220 deck — four defects found by READING the delivered file (2026-07)
The findings slides were finally RICH (1.7-2.4k chars each: the shard-prompt fix worked, 12/12
coverage at 55 tok/s). The defects were everywhere else, and three of them were mine.
1. **TWO SLIDES OF THE SAME DECK DISAGREED.** Executive summary: 21 COUNTRIES. Asset inventory:
   1 COUNTRY. Cause: each inventory row stores its countries as a COMMA-JOINED STRING
   ("AT,AU,BE,CH,..."), and the builder counted DISTINCT STRINGS — one row, one string, "1".
   FIX: use `sum.countries`, the number the engine already publishes; only derive it (splitting on
   commas) when that is absent. This is the D8 "counts come from more than one metrics object"
   item, now closed for the country tile.
2. **The COUNTRY CELL was unreadable** — 21 codes in a 1.1in column, truncated mid-word
   ("...,HK,I"). Now "AT, AU, BE +18".
3. **The AI wrote "Colt" because WE TOLD IT TO.** The rebrand fixed the deterministic TEMPLATES but
   not the model's INSTRUCTIONS: `reference/LLM_DELTAS_BIBLE.md` said "named Colt product", listed a
   Colt product catalogue, and labelled the remediation body "WHY COLT" — which the model copied
   verbatim onto the slide ("WHY COLT: ... Colt structurally removes ... our Tier-1 backbone").
   RULE: **a prompt is a string that reaches a human, via the model.** The bible is now
   vendor-neutral, the label is "WHY THIS SERVICE", and a VOICE section forbids "our backbone" /
   first-person ownership — the reader is a reseller delivering with their own stack.
   The `COLT` tag enum and the `colt_mitigation` JSON key are UNCHANGED (lookup keys).
4. **"COLT COLT Technology Services Group Limited"** — registries store an ASN handle ("COLT") and
   an org name ("Colt Technology Services..."); joined, the leading token repeats. `_dedupe_lead()`
   collapses an exact repeated first word. Also "0 domains: —" now reads "scope: routed estate (no
   domains resolved)": no domains is a legitimate ASN-seeded outcome, not missing data.
Guarded by test_deck_quality.py §6, which rebuilds the exact COLT shape and asserts the two slides
agree. LESSON: the findings text being good is not the deck being good — read every slide.

## /login layers overlapping — injecting a header into a GRID makes it a GRID ITEM (2026-07)
`.iam` is `display:grid; grid-template-columns:1.05fr 1fr`. I added `<SiteHeader/>` as its FIRST
CHILD, so the header became grid item #1 and took the LEFT CELL; the brand panel slid into column 2
and the sign-in card dropped to row 2 — which on screen looks exactly like "one layer traversing
over the other". Nothing was z-index or positioning; it was the grid re-flowing.
FIX: `.iam-page` flex column wraps header + `.iam`, so the header is a SIBLING of the grid, and
`.iam-page > .iam{flex:1;min-height:0}` overrides the base `min-height:100vh` — otherwise the grid
demands a SECOND full viewport below the header and the page scrolls for nothing. Exactly the class
of bug already recorded for the mobile bottom bar that inherited `height:100vh` from the sidebar.
RULE: before adding a child to an existing container, check its `display`. In a grid or flex parent
a new child is a LAYOUT PARTICIPANT, not an overlay. Guarded by an SSR test that asserts, on every
public page, that `id="hd"` appears BEFORE any grid/flex layout box.
Also wired the whole login page (13 strings) to the dictionary — it was still hardcoded English,
which the German assertion caught.

## Landing/Demo German — the rest of the page (2026-07)
Only the hero and creed were translated; everything below stayed English. Three things were needed.
1. **A gettext-style dictionary.** `DE_BY_EN` in i18n.jsx is keyed by the ENGLISH SOURCE STRING, and
   `useTx()` returns `tx(en)`. ~120 strings, many long sentences embedded in JS data arrays: inventing
   a key per string would be 120 chances to mistype one and silently ship a blank. The English text
   IS the key, so a missing translation degrades to the original sentence.
2. **The map + deep-dive are built with `innerHTML` inside `useEffect(..., [])`.** Translating them
   changed nothing until a reload, because the effect never re-ran. FIX: `[lang, tx]` deps AND
   `dw.innerHTML = ""` before rebuilding — without the clear, the second run APPENDS a duplicate
   copy of every card.
3. **Never regex-wrap JSX text across a whole file.** A blanket `>Text<` replacement also matched
   inside the DD/NODES arrays, which hold HTML as JS STRINGS, and corrupted them into a parse error.
   The pass is now scoped to the component's `return (...)` block only (`s.rindex("\n  return (")`).
VERIFIED BY MEASUREMENT, not by eye: an SSR render in German counts English function-words per page
(the|your|and|with|from|what|...). Landing 4%, Demo 0%, Login 3%, Contact/Privacy/Impressum 0% — the
residue is proper nouns and code identifiers. Switching back to English is asserted in the same test.

## Raw i18n KEYS shipped to the screen — two dictionaries, one mistake (2026-07)
The live site rendered `q3.h`, `earn.01h`, `earn.01b`, `demo.t1h`, `touch.body` as literal text, in
BOTH languages, destroying the "Where it earns its place" and "How it works, technically" sections.
CAUSE: i18n.jsx has TWO dictionaries with different key spaces —
  * `EN`/`DE`      keyed by a DOTTED KEY, read by `t(key)`
  * `DE_BY_EN`     keyed by the ENGLISH SOURCE STRING, read by `tx(englishText)`
I added the new copy to `DE_BY_EN` but wired the components with `t()`. `tr()` falls back
EN -> key, so with the key absent from EN it printed the key itself — and the English site broke
exactly as badly as the German one, which is the tell that it was never a translation gap.
FIX: those keys now live in `EN` and `DE` (English text AND German text), removed from `DE_BY_EN`.
GUARD (this is the part that matters): an SSR test renders all 6 public pages in BOTH languages and
FAILS if the rendered text matches `/(nav|tab|hero|creed|demo|login|lede|q3|clocks|touch|earn|faq)\.[a-z0-9]+/`.
A fallback that silently prints the key is worse than a crash — it looks like content.
RULE: if a translation layer has more than one key space, every new string needs to state WHICH one
it belongs to, and a test must assert that no key ever reaches the DOM.
Coverage after the fix (measured on the rendered page): Landing 2% English function-words, Demo 0%,
Contact/Privacy/Impressum 0%, Login 3% — residue is proper nouns and code identifiers.

## Six languages — and the three bugs that produced "mixed English/German" (2026-08)
Reported: *"текст в перемешку английский с немецким и есть куски которые повторяются"*. Three
independent defects, none visible to `vite build`:
1. **A trailing-space mismatch.** The page renders `tx("What you cannot see is ")` (trailing space —
   the next word sits in a coloured `<span>`) while the dictionary key was written trimmed. Exact
   lookup missed, the sentence fell back to English, and a German headline ended in English. It hit
   five strings. FIX: `padded()` in i18n.jsx trims for the lookup and re-attaches the caller's own
   whitespace, which makes the whole class impossible.
2. **The duplicated chunks were a HOOK IDENTITY bug.** `useTx()` returned a fresh arrow every render;
   Landing.jsx lists `tx` in a `useEffect` dependency array, so the effect re-ran on EVERY render and
   appended the architecture map again each time. FIX: `useCallback([lang])` + clear `#edges`/`#nodes`
   before rebuilding. RULE: any function handed to a dependency array must be memoised, and any
   `innerHTML` container rebuilt in an effect must be cleared first.
3. **Most of the site was never in the dictionary at all.** 123 of 203 by-English strings and the
   ENTIRE cabinet (NewAssessment/Compliance/Assistant/History/Sidebar — 0 `t()` calls) were hardcoded
   English, so a German user logged in and the product switched language.
CATALOGUE = the UNION of a source scan and an SSR recording (`tools/i18n_catalogue.mjs`): a regex
misses strings that reach `tx()` from a variable (the DD/NODES/STEPS/CONV arrays), an SSR render
misses effect-only callers. 201 keyed + 203 by-English = **404 strings x 6 locales, all at 100%**.
STRUCTURE: `locales/{en,de,it,fr,es,pl}.js` (`keyed` + `byEn`), `legal-locales/*.jsx` for the legal
pages (German stays NORMATIVE; the others say so in their first sentence). `legal.jsx::localised()`
resolves reader-language -> English -> German through a Proxy, so a missing translation degrades
instead of white-screening on `t.h1`.
GATE (`ship.py`, before the brand gate): catalogue `--check` must be 100% in every locale, then
`tools/i18n_audit.jsx` renders **11 pages x 6 languages** and FAILS on a raw dotted key in the DOM, a
leaked `undefined`, a `tab.*` label over 8 chars in ANY language, or >6% English function-words.
It also renders Landing en -> de -> en and asserts the markup is byte-identical (defect 2's guard).

## Interface language != DOCUMENT language (the honest scoping, 2026-08)
The site speaks six languages; the DECK ENGINE speaks two. A deck language needs
`scripts/i18n/<lang>.json` AND the `i18n.py` post-pass AND a `LANG_*` block in `enrich.py` — the
per-company prose is written by a model, so a dictionary can never cover it.
`scripts/deck_langs.py` is the single source of truth and DERIVES the list from the dictionaries on
disk (never a constant): `doc_langs()`, `supported(lang)` (coerces anything else to `en`),
`catalogue()`. Served at **`GET /api/langs`** (public capability list) and consumed by
`docLangs.js::useDocLangs()`; the Assess/Compliance selectors are built from it and show a one-line
notice, in the reader's language, when their language is not a document language.
BEFORE THIS: the Assess screen defaulted the document language from `localStorage.cg_legal_lang`, so
an Italian reader silently sent `--lang it`, the engine fell back to English, and nothing said so.
Same split in the bots: `/lang` sets the INTERFACE (6 codes, defaulted from Telegram's
`language_code`); the document keyboard is built from `doc_langs()`; every `--lang` path — including
the `--lang xx` power-user shortcut — goes through `doc_supported()` first.
ADDING A LANGUAGE IS NOW: drop the json + the enrich block, and the UI and the bot pick it up with no
frontend change. Market rationale for it/fr/es/pl (and why pt/ja/ar lost) is in **LANGUAGES.md**.

## The LangToggle is a MENU because a row of six is 330px (2026-08)
Two buttons ("Deutsch | English") already cost ~110px of a 360px header. Six flat buttons would wrap
the header onto three lines — the arithmetic defect already recorded twice for the mobile nav. The
trigger is a fixed measurable object: short code + full name on desktop (~92px), short code alone on
a phone (~46px), chosen in CSS so there is no resize listener and no second source of truth.
NOT a native `<select>`: the closed box renders the SELECTED option's full text, which cannot be
shortened per breakpoint, so the width would swing between "EN" and "Français".

## A CHECK MUST RUN WHERE THE TOOLCHAIN IS CORRECT BY CONSTRUCTION (2026-08, three wasted ships)
THE REAL ROOT CAUSE of three consecutive failed `python ship.py` runs, which I misdiagnosed twice as
three separate small bugs: **I validated every fix in a Linux sandbox mounted on the SAME shared
folder, then handed the operator a Windows command.** `webapp/frontend/node_modules` in that folder
is Linux-native, and npm ships PER-PLATFORM binaries as optional dependencies — so esbuild died with
`The package "@esbuild/win32-x64" could not be found`. Every "fix" I shipped was green on my side and
impossible on his. Rerunning the whole test suite to discover that is expensive and it is HIS time.
FIX, structural, not another patch:
- The render audit now runs in **`webapp/Dockerfile`'s fe stage** (`RUN node tools/i18n_catalogue.mjs
  --check && node tools/run_i18n_audit.mjs`), which does a fresh `npm install` on linux/amd64. The
  toolchain is correct by construction, there is no operator setup to drift, a failure fails the
  image and therefore the deploy, and it is still ONE command.
- `run_i18n_audit.mjs` distinguishes **exit 1 (a real defect) from exit 2 (toolchain unusable here)**.
  ship.py fails on 1 and only NOTES 2. Conflating them would either block the operator over a
  toolchain he never installed, or silently swallow a genuine translation defect.
- `.dockerignore` now re-excludes `webapp/frontend/{node_modules,dist,ssrtmp}`. It whitelisted the
  whole `webapp` tree, and `COPY webapp/frontend/ ./` runs AFTER `npm install` — so the host's
  node_modules was being copied straight OVER the image's fresh install. The image had been built
  with whatever platform the operator's folder happened to hold. Same disease, one layer down.
- `esbuild` is now a DECLARED devDependency (it was only hoisted from vite); relying on hoisting for
  a load-bearing import is a silent dependency on npm's layout.
VERIFICATION THAT ACTUALLY PROVES IT: rehearse the Dockerfile stage in a temp dir — copy only
package.json + lock, `npm install` fresh, copy the source WITHOUT node_modules, then run the gate and
`npm run build`. That reproduces the image's environment instead of the dev's. All three exit codes
(0 / 1 / 2) were also exercised deliberately.
RULE: before telling the operator to run anything, ask *"on which machine, with which toolchain?"*.
A check that cannot run on the invoking platform is not a check — and a green run in the dev sandbox
is not evidence about the operator's box. Prefer putting a gate inside the container/CI that already
installs its own dependencies over asking a human to repair a local toolchain.

## The i18n gate failed three times on ITS OWN PLUMBING before it ever checked a translation (2026-08)
Three consecutive `python ship.py` runs died in the new gate, and not one of them was a real defect
in the thing being checked. Every failure was a path or contract I ASSUMED instead of reading:
1. **`npx --no-install node`** — npx treats `node` as a PACKAGE to fetch and aborts
   non-interactively ("npx canceled due to missing packages: node@26.5.1"). Call `node` directly;
   npx is for package binaries, never for the runtime itself.
2. **`run()` in ship.py returns an `int`, not a CompletedProcess.** I called `.returncode` on it ->
   `AttributeError: 'int' object has no attribute 'returncode'`. It also STREAMS rather than
   captures. Read the helper before using it — this is the same rule as "never anchor an edit on a
   line you did not just read".
3. **Two Windows-only assumptions that pass on Linux by accident:**
   - `import(path.join(SRC, "locales", "de.js"))` -> on Windows the absolute path starts `C:`, which
     Node's ESM loader reads as a URL SCHEME: `ERR_UNSUPPORTED_ESM_URL_SCHEME ... protocol 'c:'`.
     **Any dynamic `import()` of a filesystem path must go through `pathToFileURL(p).href`.**
   - `node_modules/.bin/esbuild` is a PLATFORM SHIM (symlink on Linux, `esbuild.cmd` on Windows,
     absent entirely in this install). Probing for it printed "esbuild missing - run npm install" on
     a machine where esbuild was installed and working. **Import the package's JS API instead** —
     `tools/run_i18n_audit.mjs` does the bundle+run in one cross-platform command, which is also why
     ship.py now invokes ONE node script rather than an esbuild path plus a node path.
RULE: a gate that fails on its own launcher is worse than no gate — it trains you to ignore it. Any
new check must be exercised on the OPERATOR's platform path, not only in the dev sandbox.
ALSO: React logs the `useLayoutEffect does nothing on the server` warning once per component per
render — 66 renders produced ~2,700 lines of stack traces that buried the gate's own output. The
audit filters exactly that string and `Invalid DOM property`; everything else still prints, so a
real error cannot hide behind the filter.
NEGATIVE TEST, because a gate that only ever goes green is unproven: breaking `tab.machine` to 15
chars and deleting `q3.h` from it.js was verified to exit 1 from BOTH the catalogue and the audit,
and to go back to 0 on restore. Note the bundle inlines the locale files, so the audit MUST rebuild
every run (run_i18n_audit.mjs always does) or it audits yesterday's dictionaries.

## ecolines.net — a blanket 400-remedy CAUSED the next failure (2026-08)
Symptom: kimi-k2.6 burned **164s of a 175s slice** and returned garbage, leaving llama-4-maverick
only 118s. Three findings, and the middle one is the real bug:
1. **The constant was stale.** The API answered `"temperature must be 0.6 for this model"` while
   `MODEL_PARAMS["kimi"]` hardcoded 1.0 — the value it demanded the LAST time we looked. A number
   the server publishes on every rejection must be READ, not memorised.
2. **The 400 handler disabled the protection that was working.** It blanket-popped
   `chat_template_kwargs`, which is the ONLY thing suppressing kimi's chain-of-thought. The retry
   therefore ran with thinking ON -> 46,801 chars -> `finish_reason=length` at our max_tokens
   ceiling -> truncated non-JSON -> `model returned list, not the JSON object contract`. The generic
   remedy for one error created a worse one. FIX: `_call` now parses the body and applies a TARGETED
   fix — re-send the temperature the server named; drop `response_format` only when implicated; drop
   `chat_template_kwargs` ONLY if the server actually names it. Never speculatively.
3. **kimi demoted to LAST** (was position 2, kept there on preference rather than measurement).
   A model that fails is cheap; a model that fails SLOWLY starves the models behind it. It stays in
   the chain because a fourth vendor is a real hedge against a provider-wide 429.
Guarded by test_recall.py §21 (temperature re-sent from the body · thinking still suppressed on the
retry · chat_template_kwargs dropped only when named) and the updated §19.
RULE: when an API rejects a request, fix WHAT IT NAMED. Stripping fields until something works is
how you disable a safeguard you did not know you had.
NOT bugs, for the record — these lines in the ecolines log are the guards working as designed:
Cloudflare AS13335 refused as an ownership anchor, crt.sh 404 covered by CertSpotter, ASN discovery
reported UNKNOWN rather than "none", and the co-tenant guard dropping ALEKSANDRA UN KO, SIA.

## Russian as the THIRD deck language — and what "add a language" actually costs (2026-08)
The operator asked for the four decks and the animated HTML in Russian. The dictionary was the easy
part; the plumbing was hardcoded to `de` in SIX places (`deck_i18n.js` LANG/PACK/LOCALE/money/dfmt,
`i18n.py` t/translate_json/translate_file, `enrich.py`, `enrich_parallel.py`, `run_assessment.py`
x5, `compliance_enrich.py`, `compliance_assess.py`, `build_compliance_deck.js`, `creed.js`).
LANGUAGE IS NOW DATA, NOT A BRANCH: a 2-letter code selects `<code>.json`, and the PACK declares its
own `locale`, `dateFormat` and `units`. `enrich.LANG_BLOCKS` + `lang_block(code)` is the one registry
for prose instructions; `creed.js` uses a table, not a ternary chain.
**A REGRESSION I ALMOST SHIPPED:** removing `if (LANG === "de")` from `dfmt()` silently switched
German decks to ISO dates, because de.json had no `dateFormat`. The rule did not disappear — it had
to MOVE INTO the dictionary. When you delete a branch, check what knowledge died with it.
`deck_langs.doc_langs()` now requires BOTH halves (chrome dictionary AND a LANG_* prose block) and
fails closed: half a language is not a language.
GATE: ship.py renders every CLAIMED language from the sample fixture with `DECK_I18N_AUDIT=1` and
fails if any string **the German pack covers** is still English — German is the reference locale, so
that comparison is the definition of a gap. Proven by deleting `CRITICAL` from ru.json (gate -> 1 gap)
and restoring it. `/api/langs` is a capability CLAIM; an untested claim is how `--lang it` once
reached an engine that answered in English.
TWO PRE-EXISTING DEFECTS THIS SURFACED, both invisible until a second locale existed:
  * 48 customer-visible TEMPLATES strings (finding titles, the three `why` sentences, remediation
    bodies) were in NEITHER pack — so a degraded run shipped English findings inside a German deck.
    Now in both. They are the DETERMINISTIC FALLBACK, which is exactly the path nobody renders.
  * `shodan_recon.py` TEMPLATES still said **"WHY COLT:"** 10 times and named Colt in 5 remediation
    bodies. The brand gate never caught it because it builds its decks from a fixture that already
    contains LLM prose — **the fallback path was never rendered by the gate**. Same class as the
    Cyrillic gap: a check that cannot see the artifact it checks is not a check.
Also fixed: the UI enumerated "in English or Hoch-Deutsch" in prose across six locales — a second
source of truth that went stale the moment Russian shipped. Prose must never restate what the
selector already lists.

## api.js has TWO return contracts — and I got it wrong twice (2026-08)
Symptom the operator saw: the Document-language selector offered **English only**, right after
Russian shipped and with German already working. Nothing was wrong with the engine or the
dictionaries; `GET /api/langs` returned `{ui:[...], doc:[en,de,ru]}` correctly.
THE BUG: `webapp/frontend/src/api.js` exposes two helpers with DIFFERENT contracts —
    getJSON(path)  -> the PARSED BODY        (throws on 401 / network)
    postJSON(path) -> { ok, status, data }
`docLangs.js` did `const { ok, data } = await getLangs()`. `getLangs` is getJSON-backed, so BOTH
names were `undefined`, the guard `if (ok && ...)` never passed, and the hook fell back to its
English-only default. It compiles, it runs, it renders — it is only wrong at the moment it executes.
Same root cause as calling `.returncode` on ship.py's `run()` (which returns an int): **assuming a
helper's contract instead of reading it.**
THE SCAN FOUND A SECOND, PRE-EXISTING INSTANCE: `NewAssessment.jsx` read `{ok, data}` from
`assessStatus()`, so the re-attach path ALWAYS bailed and deleted `cg_job` — a phone that evicted the
tab could never rejoin a running assessment, which is the entire reason the job id is stored.
GATE: `webapp/frontend/tools/api_contract.mjs` parses api.js, classifies every export as
getJSON- or postJSON-backed, and fails on any call site that destructures `{ok|data|status}` from a
getJSON-backed call (and on a postJSON result whose `.data` is never read). Pure static analysis, no
toolchain, so it runs on the operator's machine AND in the image build. Wired into ship.py and
`webapp/Dockerfile`. Proven by a negative test: reintroducing the exact line exits 1, restoring it
exits 0.
RULE: when a module exports more than one fetch helper, their return shapes MUST be asserted by a
check, not by memory — the failure mode is a feature silently disappearing, not an error.

## SSH SESSION COUNT is the ONLY lever on Windows — researched, not guessed (2026-08)
Three ship.py runs hung at the very end, AFTER a fully successful deploy. I patched the symptom
twice (a hard timeout, then a per-run hash cache) and it simply moved to the next ssh call. The
actual constraint, verified:
  * **The Windows OpenSSH client has NO ControlMaster/ControlPersist multiplexing.**
    PowerShell/Win32-OpenSSH issue #1328 is still open. So the textbook fix — reuse ONE TCP
    connection for every command — does not exist on the operator's machine. Every `ssh()` is a full
    TCP + kex + auth handshake.
  * **OpenSSH 9.8 (Jul 2024) enables `PerSourcePenalties` by DEFAULT.** sshd records a penalty
    against a source ADDRESS, penalties ACCRUE with repetition, and further connections are refused
    while one is live. With `MaxStartups` (10:30:100) on top, a burst of short-lived sessions from
    one IP is exactly the shape both mechanisms exist to damp.
Therefore the only available lever is OPEN FEWER SESSIONS — which is the rule CLAUDE.md already
carried ("prefer the single-connection pattern for anything new") and which deploy_web_direct.py has
always obeyed, and it is the ONE script that never hangs.
FIX: `ssh_script(script)` runs a multi-line bash script in ONE session, base64'd so no quoting layer
(PowerShell -> ssh -> bash) can corrupt nested quotes; `_sections()` splits the output on
`#### NAME` delimiters. `_prime_sha_cache([...])` hashes the engine in SEVERAL containers in one
call. 5/5 VERIFY now does docker ps + both engine hashes + the model probe + the .env read in ONE
session instead of five. MEASURED on a fake droplet: the post-deploy part of ship.py went from
**7 sessions to 2**.
RULE FOR ANYTHING NEW: never add an `ssh()` call to a step that already opens one — add a section to
its batch. A second handshake is not free; on this platform it is the one that gets refused.

## 5/5 VERIFY hung because it re-asked a question already answered (2026-08)
The deploy SUCCEEDED — colt-web up, engine CURRENT, `public via caddy = 401`, the in-image i18n
gates green — and then ship.py sat silent for minutes on the LAST probe. Two defects:
1. **`engine_is_current()` ran FIVE times in one ship** (colt-web twice, colt-assessbot three times):
   deploy, self-heal check, bots skip-check, then AGAIN in 5/5 VERIFY. Each is a fresh ssh +
   docker exec, and sshd throttles rapid repeats (MaxStartups / PerSourcePenalties) — CLAUDE.md has
   said "prefer the single-connection pattern" since deploy.py hit the same wall. FIX: `_SHA_CACHE`
   memoises the hashes PER RUN; the three call sites that follow a (re)deploy pass `fresh=True`, the
   rest reuse the answer already paid for. Measured: 4 call sites -> **2 ssh sessions**. Read-only
   probes also drop from a 180s to a 60s timeout: three minutes of silence teaches the operator to
   distrust the tool.
2. **`ssh()` had no `timeout` parameter but do_verify was passing one** — `ssh(..., timeout=90)`
   raised TypeError inside a `try/except`, so the model-existence probe silently never ran. Same
   class as the ruff gate that skipped for weeks and the esbuild path that "was missing" on a machine
   where esbuild worked: **a check that cannot execute is not a check.**
RULE: before adding a probe, ask whether this run already knows the answer. A redundant remote call
is not free — it is the one that gets throttled.

## ecolines.ru — the engine spoke Russian; the API never let it (2026-08)
The operator picked «Русский», the decks came out ENGLISH, and the run log said it plainly:
`{"evt":"assess_done", "lang":"en"}` with filenames carrying no `_RU` suffix. The engine was
INNOCENT — `run_assessment._doc_lang("ru")` returns `ru` and renders correctly in isolation.
THE BUG was one line, in the layer IN FRONT of the engine:
    lang = "de" if str(req.lang or "en").lower().startswith("de") else "en"
in `webapp/backend/app/main.py`, in **five places** (assess, assess-refine, compliance,
compliance-refine) plus once more inside `store.create_job`. `ru` was flattened to `en` at the API
boundary, before the engine ever saw it — and again on the way into the database, so even a fixed
API would have lost it.
ROOT CAUSE, and it is the pattern not the line: **I generalised the engine to N languages and did
not walk the request path.** Same defect class as a value having four homes — generalise one layer,
leave the layer in front on a two-language ternary, and the stale one silently wins. `deck_langs
.supported()` is now the single authority, reached through `main.doc_lang()`; the store persists the
decision instead of re-making it.
SECOND HOP, SAME DISEASE (rt-solar.ru, an hour later): with the API fixed, `ru` reached the engine
and argparse killed the run — `run_assessment.py` still declared `choices=["en","de"]`, and so did
`compliance_assess.py`. That is a SIXTH home for the language set, in a shape my first guard did not
match: I had grepped for `startswith("de")` and the literal pair looks nothing like it. Both now
derive their choices from `deck_langs.doc_langs()`.
LESSON ABOUT THE GUARD ITSELF: a test written against the ONE SPELLING you just fixed will miss the
next spelling of the same concept. `tests/test_doc_lang.py` now matches the CONCEPT — a hand-written
language list in any form (`startswith("de")`, `choices=[...,"de"]`, a bare `("en","de")` literal) —
AND runs the real CLI with `--lang <code>` for every language `/api/langs` advertises. A capability
is not shipped until the process that does the work will accept it.
GUARD: `tests/test_doc_lang.py` asserts the RULE, not the line — no module on the request path
(webapp/backend/app + engine scripts) may contain a `startswith("de")` coercion in CODE (comments
that describe the removed pattern are stripped first), every language `deck_langs` OFFERS must pass
through `supported()` unchanged, everything it cannot render must fail closed to English, and
`create_job` must not re-coerce. Proven by a negative test: reintroducing the exact line fails the
suite, restoring it passes.
RULE: when you generalise a capability, follow the VALUE end-to-end — UI -> API -> persistence ->
engine — and assert it at each hop. A capability the engine has and the API discards is invisible in
every test that only exercises the engine.

## budget.gov.ru — ONE line made the whole Russian government one customer (2026-08)
The operator asked for **budget.gov.ru** and received a deck covering duma.gov.ru, nalog.gov.ru,
minfin.gov.ru, mchs.gov.ru, fssp.gov.ru, fsb-adjacent hosts and ~120 more: **203 IPs, 12 findings,
EUR 11-28M of priced risk**, and the report even renamed the customer to `gov.ru`.
THE CAUSE, one line:
    def _apex(d):
        p = d.split('.'); return ".".join(p[-2:])
`budget.gov.ru` -> `gov.ru`. So did every ministry. The ownership gate — the thing the entire
zero-false-positive design rests on — then agreed they were all the same organisation. The same line
turns `bbc.co.uk` into `co.uk` and `example.com.au` into `com.au`.
`gov.ru` / `co.uk` / `com.au` are **PUBLIC SUFFIXES**: nobody owns them, anyone may register under
them. Two names sharing one share NOTHING. This did not merely widen scope, it inverted the meaning
of the ownership test.
FIX — `scripts/psl.py`, three barriers, each independent:
1. **`_apex()` is now the REGISTRABLE domain (eTLD+1).** Preferred source is the OFFICIAL list at
   `scripts/data/public_suffix_list.dat` (fetch it with `python update_psl.py`); absent that, a
   committed STRUCTURAL rule — under a two-letter ccTLD, a second label from the small set of
   ADMINISTRATIVE labels (gov, co, com, ac, edu, mil, gouv, govt, ...) is a suffix, not a
   registration. The rule encodes the CLASS, not a hand-typed zone list that would go stale.
2. **A public suffix may not be SEEDED.** `resolve_identity("gov.ru")` now refuses with an
   explanation instead of confidently assessing a country.
3. **No brand tokens -> no pivot, at all.** The run logged `brand tokens: (none)` (the bad apex made
   `gov` legal-form noise), and with nothing to corroborate against, the rarity test alone admitted
   **'Russian Trusted Sub CA'** — a NATIONAL certificate authority — as "the customer's private CA",
   pulling in +44 hosts. RARITY IS NOT OWNERSHIP: an issuer can be rare in Shodan's index and still
   belong to somebody else entirely. When we hold no distinctive token, every downstream
   corroboration is a no-op, so the honest answer is to widen nothing.
FAIL DIRECTION: when unsure, take MORE labels, i.e. a NARROWER estate. A narrow estate misses some of
the customer's own hosts (a recall bug); a wide one puts a stranger's infrastructure in their deck.
Guarded by test_recall.py §22, including a regression pass over EVERY earlier incident domain
(skon.de, bibel.tv, otto.de, ecolines.net, email-archiv-rightmart.de, angermann.3cx.eu) to prove the
PSL changes none of them.
RULE: "the last two labels" is never the registrable domain. Any ownership decision keyed on a
domain must go through psl.registrable().


## A refusal is a FORK, not a failure — and the operator may overrule it (2026-08)
Right after the PSL fix landed, the operator typed `gov.ru` and got a red "assessment failed". The
guard was CORRECT (a public suffix has no owner), but the presentation was wrong in two ways:
1. **It looked like a crash.** A deliberate decline rendered as `assess_error` with a traceback tells
   the operator the tool broke, when it had just protected them from a deck full of strangers.
   FIX: `shodan_recon.ScopeRefused` carries `code` + `reason` + `hint`; run_assessment emits
   `evt=assess_refused` and exits **4** (distinct from a real failure); the web app renders an amber
   panel with the reason, the next step and a button — never `.err` red.
2. **It was an absolute NO.** "Show me every Russian federal body" is a legitimate request from a
   regulator or a threat researcher. Refusing it outright is the tool substituting its judgement for
   the operator's. FIX: `--allow-public-suffix` (UI: "Survey the whole zone anyway",
   `AssessReq.zone_survey`) — declined BY DEFAULT so a typo or a misunderstanding is caught, honoured
   on an EXPLICIT assertion, and `ident["zone_survey"]` marks the run so the artifact says it covers
   many independent organisations rather than implying one customer.
RULE: a guard that cannot be overridden by an informed operator is a bug, and a guard that presents
its decision as a malfunction is a different bug. Give the reason, the next step, and the override.
Same doctrine as the clarify loop: the human asserts the fact, the system records that they did.

## abakus-tk.de — ONE href in a footer became 68% of the "attack surface" (2026-08)
A 20-consultant Lübeck telecoms reseller whose ENTIRE estate is one shared IONOS elastic-SSL VIP
plus M365/Zoho was shipped a deck claiming **401 IPs · 42 ASNs · 49 countries**. 16 of the 17
evidence IPs were third parties (Oracle, AWS, OVH, Contabo, Eircom, Facebook, four TR/offshore
hosters); the ONE real host was rated NIEDRIG, the lowest in the deck. **236 of 348 inventoried
hosts — 68% — were Meta.** The C-BIQ priced €2.5–6.8M SEW / €90M PML / 736% RSI entirely off H2,
whose seven evidence IPs are all strangers'. GEOPOL profiled German automotive (TISAX, UNECE R155,
VW/Winnti) for a company that resells SIP trunks.
ROOT CAUSE, exact and reproducible: `group_discovery.STRUCTURE_HINTS` matched `struktur` as a BARE
SUBSTRING — and **`infrastruktur` contains `struktur`**. So `/it-infrastruktur/`, the likeliest page
path on a TELECOMS provider's website, was read as a corporate group-structure page, every external
link on it was harvested as a "subsidiary", and the site-wide WhatsApp footer button
(`<a href="https://wa.me/…">Chat</a>`) put **wa.me** into scope as a first-class seed →
`hostname:".wa.me"` → Meta's global edge. The module written to fix a PROPERTY group broke on a
telecoms company because "Infrastruktur" is that company's product.
**WHY EVERY GUARD STAYED SILENT — the part that matters.** The guards are not independent; all
three key off the same assertion:
  * `identity_ips = set(hosts)` is assigned AFTER the identity queries. The poison arrived THROUGH
    an identity query, so it became the baseline: `scope_blowout` compared 401 against 401.
  * the co-tenant guard puts `group_domains` into `_own_aps`, so every host carrying `wa.me` was
    explicitly EXEMPTED as "carries one of the customer's own names".
  * `_accept_pivot` (PIVOT_MAX_ADD) guards pivots only; these hosts were not a pivot.
  * `_owns_apex` returned True for wa.me *because it was in group_domains* — discovery vouching for
    itself is not a gate.
FOUR FIXES, in `scripts/`:
1. `group_discovery.STRUCTURE_HINTS` anchors the generic tokens with `(?<![a-z])…(?![a-z])` and
   keeps the real German compounds (konzern-/unternehmens-/firmen-struktur) listed explicitly;
   `infra` leads ANTI_HINTS as a second, independent barrier.
2. **NEW `scope_deny.py`** — the authoritative shortener/social/SaaS/platform/media denylist,
   enforced BOTH at harvest (group_discovery) AND at the ownership gate (`_owns_apex`), because a
   denylist that lives in one module protects one code path. Runs AFTER the seed test so a media or
   social company can still BE the customer. `_SHORT_SHAPE` is deliberately narrow (1–2 char label
   on me/ly/gy/gd/co/to/cc) — an earlier draft allowed 3 chars and .io/.ai and would have denied a
   real startup, which is the opposite failure and the harder one to notice.
3. group domains no longer bypass the gate: they are refused if denied or a public suffix. Group
   membership still WINS inside `_owns_apex`, so the angermann netbid.com recall is untouched.
   `_structure_known` now needs **≥2** named companies — one link is a mis-selected page, not a
   published roster (and treating it as authoritative would also switch on lookalike rejection).
4. **PER-DOMAIN CONTRIBUTION BUDGET** (`DOMAIN_MAX_ADD`, default 40; budget =
   `max(40, 3 × seed_proved)`). `build_filters` tags each identity clause with the `dom` that
   produced it; `run()` measures what each DISCOVERED domain contributed EXCLUSIVELY and rolls the
   whole domain back — hosts, `ident["domains"]`, `group_domains` — recording it in
   `domains_rolled_back` + `related_unscoped`. This is the generalisation of the lotto24 per-pivot
   budget to IDENTITY queries, and it is the only guard that holds when the other three fail.
RULE: **a discovered domain may ENLARGE the estate; it may never BE the estate.** And a guard whose
baseline is computed after the untrusted input has been merged is not a guard.
Guarded by `scripts/test_scope_abakus.py` (wired into ship.py, BLOCKING): replays the failure
(118 Meta hosts → rolled back, 1 IONOS host kept), proves the recall side (netbid.com/netbid.io
survive, every past-incident domain still allowed), and was verified to FAIL with
`DOMAIN_MAX_ADD=99999` — a gate that only ever goes green is unproven.

## abakus-tk.de round 2 — a DICTIONARY WORD as an ownership anchor (2026-08)
With `wa.me` denied, the re-run STILL produced **192 IPs · 44 ASNs · 15 countries** for a company the
same log correctly described as `ASN — · 0 prefixes`. Inventory: IONOS 94 · Microsoft 11 · AWS 10 ·
DigitalOcean 9 · Hetzner 8 · OVH 5 · Cloudflare 4 · Google 4 · Infomaniak 3 · Scaleway 2 · Vultr 2.
THREE COMPOUNDING CAUSES, all now fixed:
1. **`ssl:"abakus"` / `http.title:"abakus"` / `http.html:"abakus"` — "Abakus" is the German word for
   abacus** and the trading name of dozens of unrelated firms (ABAKUS Internet Marketing, Abakus
   Consulting …). `http.html:` is the worst: it matches any page whose BODY contains the word.
   These clauses are `cat="identity"`, so they ALSO bypass the CDN/hoster drop in `run()` and are
   never put through `_corroborates` — **nothing was checking them at all.** The rule
   ("never let a selector that can match the whole internet become an ownership anchor") was
   encoded for the CA pivot after bibeltv, via `api.count()` in `_private_ca_ok`, and never applied
   to the brand selectors, which are the same shape. FIX: `guard="rarity"` on those clauses +
   `_selector_is_distinctive()` in run(), refusing anything matching > `BRAND_MAX_HOSTS` (2000)
   globally. Vendor-agnostic, no word list, one count() call, and it runs BEFORE the query so no
   credits are burned. Fails OPEN (count() is plan-dependent) and logs when it cannot check.
   Recorded in `ident["selectors_refused"]`.
2. **The DNS probe PINNED SaaS tenancies.** `autodiscover/webmail/exchange/auth.abakus-tk.de` all
   CNAME into Microsoft 365, so the probe pinned Microsoft's shared Exchange Online front ends
   (52.98.x.x, 40.99.x.x) — and `cat="pinned"` deliberately bypasses the hoster drop (that exemption
   exists so a legitimately-pinned S-KON host on shared infra is not discarded), so every co-tenant
   on those front ends came with them. FIX: `_cname_chain()` (getaddrinfo throws the CNAME chain
   away; `gethostbyname_ex` keeps it) + `_is_saas_tenancy()` against `SAAS_CNAME`. A name that
   CNAMEs into a provider platform is recorded in `ident["saas_tenancies"]` and never pinned.
   **The customer's DNS pointing at Microsoft means they USE Microsoft.** It is not an address they
   own, nobody can remediate it, and everything on it belongs to other tenants.
3. **The co-tenant guard was RIGHT and its own valve overruled it** — flagged 182 of 192 (95%),
   then refused because >75%. That threshold encodes an assumption that only holds when the target
   HAS address space: there, a mass drop means the whois data is wrong. On a target with no ASN and
   no prefixes, co-tenants dominating is the EXPECTED result. FIX: the valve now refuses only if the
   drop would EMPTY the deck, or if it is a mass drop AND the target owns ASNs/prefixes (the
   lotto24/angermann doctrine, unchanged and still tested).
ALSO SEEN, same root cause as (1): `abakusconsulting.co.uk` — a different UK company — entered scope
because "abakus" is a substring of "abakusconsulting" and the name appeared on a **shared IONOS
elastic-SSL certificate**. The cert-name discovery comment claims "a shared-hosting neighbour's cert
can never drag its own domain into scope"; that holds only while the brand token is distinctive.
RULE: **a brand token is an ownership anchor only if it is RARE.** Test rarity against the index,
never against intuition — the engineer who picks the token speaks the language and cannot hear that
it is a common word.
Guarded by test_scope_abakus.py §6-§8 (generic-word refusal, SaaS-tenancy pinning, valve behaviour
with and without owned address space).

## PINNING PROVES THE ADDRESS, NOT THE OBSERVATION (abakus-tk.de, proved 2026-08)
The operator pulled Shodan's ACTUAL records for abakus-tk.de's two addresses. Verbatim:
```
217.160.0.136           :80   http.host = mlslight.com
217.160.0.136           :443  hostnames  = bboca.de
2001:8d8:100f:f000::269 :80   http.host = cpi-projects.co.uk
2001:8d8:100f:f000::269 :443  http.host = www.stefan-ried.de   cert CN *.stefan-ried.de
```
**Not one record names abakus-tk.de.** The deck's "Standard services exposed - nginx" finding was a
stranger's private blog. Both IPs are legitimately PINNED (the customer's own DNS resolves there)
and pinned hosts deliberately bypass the hoster drop — that exemption exists so a real S-KON host on
shared infra is not discarded — so every co-tenant observation was inherited as the customer's.
MECHANISM, verified by hand: the IONOS elastic-SSL VIP **requires SNI**.
`openssl s_client -connect 217.160.0.136:443 -servername abakus-tk.de` returns `CN=*.abakus-tk.de`;
the same command WITHOUT `-servername` aborts with `tlsv1 alert internal error` (alert 80) and no
certificate at all. Shodan scans by IP with whatever hostname it happens to know, so the customer's
vhost is structurally invisible to it. No filter set can fix that — it is the ground truth of the
target, and the honest deck line is "shared hosting, not externally observable", not a finding.
FIX — `_record_names(m)` + `_names_the_target()` + the attribution gate in `run()`: on
provider/multi-tenant infrastructure (`_is(org, CDNS)` or `_looks_like_provider`) a record may only
become a finding if it identifies itself with one of the customer's own names (rDNS, HTTP Host,
domains, cert CN/SAN). Dropped records are recorded in `ident["records_unattributable"]`.
FAILS OPEN in the one ambiguous case: a record carrying NO names at all cannot be shown to be a
co-tenant's either, so it is KEPT — same doctrine as the co-tenant guard's "no org recorded -> no
evidence -> keep", and it is what protects the S-KON WatchGuard whose only anchor is a self-signed
certificate.
RULE: **pinning proves the ADDRESS is theirs; it does not make every OBSERVATION on it theirs.**
Guarded by test_scope_abakus.py §9 (the real co-tenant records dropped, the record naming the
customer kept, the no-names record kept).
WHAT THE RIGHT ANSWER LOOKS LIKE: one curl with the correct SNI produced the first genuinely
attributable technical finding of the whole engagement —
`curl -sSI --resolve abakus-tk.de:443:217.160.0.136 https://abakus-tk.de/` returns Apache +
PHP/8.3.32 + WordPress + The Events Calendar, `Set-Cookie: ZPORTALSESSID` with **no Secure and no
SameSite**, and **no HSTS, CSP, X-Frame-Options or X-Content-Type-Options at all**. That is their
application, on their vhost, and every line of it is remediable by them. Shodan could never see it.
