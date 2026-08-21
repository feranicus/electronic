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

## The ZONE is a finding source when Shodan is blind (abakus-tk.de, 2026-08)
On a target whose whole estate is shared hosting, Shodan can produce NOTHING attributable: every
record on the IONOS VIP belonged to a co-tenant, and the customer's own vhost is invisible because
the front end requires SNI. The engine therefore had a structural blind spot — it could only ever
report other people's hosts or nothing at all. **The DNS zone, however, is unambiguously theirs.**
Two pure-DNS checks were added, and on abakus-tk.de BOTH fire:
1. **`no_caa`** — `_caa(domain)` over DoH (stdlib cannot query type 257). `[]` = queried OK and
   genuinely empty -> MEDIUM finding. **`None` = the lookup FAILED -> no finding at all**, per the
   standing rule that absence of evidence is never a finding.
2. **`dns_no_service`** — a name that resolves but has NO record anywhere in the sweep. Deliberately
   worded "possible dangling DNS" and NOT asserted: Shodan not holding a record is not proof a host
   is gone. `clarify.py` puts it to the operator (`stale_dns` -> `exclude_hosts`); their answer is
   what turns a candidate into a finding. SaaS tenancies are skipped — they were never the
   customer's host to begin with.
THE TWO COMPOUND, and that is the sellable part: with no CAA, whoever is reassigned a dangling
address can complete an HTTP-01/TLS-ALPN challenge and obtain a **genuine, browser-trusted
certificate** for the customer's own subdomain. Neither finding needs a single packet sent to the
customer.
GROUND TRUTH THAT PROVED IT: `nmap --reason` against 212.72.175.108/109/110 returned
`host-unreach from 212.53.200.102` — and RIPEstat shows 212.53.200.102 is **Artfiles' own router**
(AS8893, the same holder as the target block). An ICMP host-unreachable from the LAST-HOP router
means the prefix is routed but nothing answers ARP: the hosts are GONE, not firewalled. A firewall
gives `no-response` or `reset`. `intranet.abakus-tk.de` and `dev.abakus-tk.de` are dangling.
ALSO FOUND, by reading the WordPress REST API the operator queried by hand: `/wp-json/wp/v2/users`
returns HTTP 200 with two usernames (`abakustk_admin`, `lennox`) AND a second brand domain in the
admin's profile — **abakus-tk.online**, which resolves to the same IONOS VIP and which no recon
path had discovered. App-layer checks like this are NOT implemented: fetching a customer page is
sending packets to their infrastructure, and "not one packet" is a product promise, not a default
to change silently. If it is ever added it must be an explicit per-engagement opt-in with the ToU
wording changed in the same edit.
Guarded by test_scope_abakus.py §10 (CAA empty -> finding; CAA lookup failed -> NO finding; dead
names flagged; a name with an observable service not flagged).

## The last abakus false positive: a NEIGHBOUR'S certificate on a shared VIP (2026-08)
The re-run went 192 IPs -> 1 and the attribution gate dropped 174 co-tenant records
(tagesklinik-hamburg.net, rh-it-beratung.com, reikidosmundos.com). One bad finding survived:
H1, four CVEs on `2a00:da00:100f:f000::206` — which is **abakusconsulting.co.uk**, a UK consulting
firm. It entered through `_cert_names` harvesting on a swept host:
`_owns_apex("abakusconsulting.co.uk", tokens={"abakus"})` -> the squashed label is
"abakusconsulting", "abakus" is a substring -> OWNED.
The code comment there claimed "a shared-hosting neighbour's cert can never drag its own domain into
scope". **That holds only while the brand token is DISTINCTIVE** — and "abakus" is the German word
for abacus. The rarity gate added for Shodan brand SELECTORS did not cover `_owns_apex`'s token test.
FIX, and it is a principle rather than a threshold: a certificate is STRONG evidence of common
operation when it **also names the customer** (that is exactly how bibeltv.de reached bibel.tv, via
a shared SAN). It is WEAK evidence when it names only the other party AND the host is provider /
multi-tenant infrastructure — then all that has been observed is that two customers of the same
hoster have similar-looking names. So a cert-name discovery admitted ONLY by a brand-token substring
is refused when the host is shared and the certificate does not also name an owned domain; recorded
in `ident["cert_names_refused"]`. Guarded by test_scope_abakus.py §11, which asserts BOTH directions
(abakusconsulting refused, bibel.tv still scoped).

## D8/A11 CLOSED — the inventory is derived from the FINAL estate (2026-08)
The same deck printed **"1 UNIQUE IPS · 47 ASNS · 15 COUNTRIES"** on slide 2 and
**"144 HOSTS · 12 OPERATORS · 12 ASNs"** on slide 5. One host cannot span 47 autonomous systems.
CAUSE: `inv`, `asns` and `countries` were accumulated DURING the query loop and never re-derived, so
they still counted every record the attribution gate, the co-tenant guard and the domain/pivot
rollbacks had since removed. Every guard worked; the metrics object simply predated them.
FIX: rebuild `inv`/`asns`/`countries` from the surviving `hosts` dict after all guards have run.
ONE source for these numbers. Guarded by test_scope_abakus.py §12 (inventory hosts may never exceed
unique IPs; the ASN count must be consistent with the surviving host count).
RULE: any headline number must be computed AFTER the last thing that can change it. A count taken
mid-pipeline is a claim about a state the deck never describes.

## An EMPTY estate is an honest outcome — the valve inverted (abakus-tk.de, 2026-08, CORRECTION)
The cert-name fix worked (`abakusconsulting.co.uk` refused, scope back to ONE domain) and the run
got WORSE: **25 IPs, 6 findings, EUR 6-16M priced** on a 20-person reseller. One log line explains it:
```
co-tenant guard REFUSED: it would have dropped 25 of 25 hosts (100%) - keeping everything
```
The attribution gate had already removed every record on the IONOS VIP — that day Shodan's records
for it named `pro-tec.org` and `www.parcarmeen.com`, NOT abakus — so the 25 hosts left really were
all strangers. The guard identified all 25 correctly and then refused, because dropping them would
empty the deck. Those 25 strangers became six findings.
**The "never empty a deck" invariant was the bug.** It was written for lotto24.de, where a malformed
`org:` pivot injected 381 strangers and refusing at least left the operator something. That case is
now handled UPSTREAM by the per-pivot and per-domain budgets, so emptiness no longer has to be
prevented at the co-tenant guard — and preventing it there guarantees the worst possible deck on the
most common target shape we see.
RULE: **"nothing of yours is externally observable" is a TRUE, defensible and saleable result** for a
company whose whole presence is shared hosting and SaaS. A deck full of other people's servers is
none of those things. Emptiness is no longer a refusal trigger; the only surviving refusal is the
narrow lotto24/angermann one — a mass drop on a target that OWNS address space means the whois data
is the suspect, not the estate. Pinned hosts and hosts carrying the customer's own names are exempt
before the guard runs, so for it to empty the estate every remaining host must be unpinned, unnamed
and whois-owned by somebody else, which is the definition of "they are strangers".
`ident["no_attributable_estate"]` is set and logged so a zero reads as a finding, not a broken run.
NOTE THE TEST INVERSION: `test_run_path.py`'s "the guard must never EMPTY a deck" assertion was
DELIBERATELY inverted, with the reasoning kept in the file. A test that encodes a doctrine must be
rewritten when the doctrine is corrected — deleting it would lose why.
Guarded by test_scope_abakus.py §13 and the rewritten test_run_path.py section (both directions:
no address space -> drop; own address space -> still refuse).

## adpolice.gov.ae — three defects, all in data we already had (2026-08)
A four-finding deck for Abu Dhabi Police. One finding was a false positive, one was the most serious
exposure in the engagement WRONGLY LABELLED, and the framework list cited EU and automotive law at
an Emirati police force.

**D1 — THE TLS NEGATION BUG. The widest false-positive source in the product's history.**
Shodan's `ssl.versions` array lists every protocol tested and marks the UNSUPPORTED ones with a
leading minus:
```
5.194.255.186:443   ['-TLSv1','-SSLv2','-SSLv3','-TLSv1.1','TLSv1.2','-TLSv1.3']   <- TLS1.2 ONLY
151.253.157.21:443  [ 'TLSv1','-SSLv2','-SSLv3', 'TLSv1.1','TLSv1.2','-TLSv1.3']   <- genuinely legacy
```
`classify()` did `v.lstrip("-")` — it STRIPPED the sign and then matched — so a host that had
explicitly DISABLED TLS 1.0 was reported as offering it. Every modern host lists its disabled
protocols, so this fired on essentially every host the engine ever saw. **Every deck already
delivered is suspect on any TLS finding.** FIX: filter on the SIGN, never on membership —
`enabled = [v for v in versions if not v.startswith("-")]`.

**D2 — the service was named from the PORT, not the REDIRECT CHAIN.**
`151.253.157.21:443` was reported as "a mail service gateway". Its own Shodan record contained:
```
301 -> https://mediahubtest.adpolice.gov.ae/otmm/ux-html/index.html
302 -> /otdsws/login?logon_appname=Digital+Asset+Management+CE+25.4
```
OpenText Media Management behind OpenText Directory Services — and the hostname says **test**. The
one internet-facing host the force owns under its own certificate is a NON-PRODUCTION media
repository, and it was rated Medium for a TLS issue that was itself half false.
FIX: `_redirect_trail(m)` feeds `http.redirects[].location/host`, `http.location` and `http.host`
into `_hay()`, plus two new detectors — `ecm_exposed` (OpenText/Documentum/SharePoint/Alfresco/
FileNet/AEM class) and `nonprod_exposed` (test/dev/staging/uat/sandbox/demo). Non-production is
HIGH on its own and CRITICAL when it is also a content platform. The non-prod token is DELIMITED
(`(?<![a-z])test(?![a-z])`) so "attestation", "protest", "devices" and "labour" do not trigger it —
a substring rule there would fire on half the internet.
RULE: **`http.redirects`, `http.location`, `http.title` and `http.host` identify a service far more
reliably than `product` and `port`. Read them before naming an asset.**

**D3 — the framework set was hardcoded to a German automotive supplier.** TISAX and UNECE R155
(vehicle type-approval) plus NIS2 and GDPR, in front of a UAE police force — the THIRD recurrence
of D9/A7. FIX: `build_findings_deck.js` selects the regime set from `d.target.country`, which
`shodan_recon` now publishes (the dominant country of the surviving estate, or the ccTLD).
AE -> UAE IA Standards / ADDA-ADSIC; GB -> NCSC Cyber Essentials / UK GDPR; CH -> revFADP /
NCSC-CH; EU -> NIS2 / GDPR (+ BSI TR-02102 for DE); everything else -> ISO 27001 / NIST CSF.
RULE: citing the wrong regulator is worse than citing none — it tells the reader the document was
not written for them.

**D4 — the attribution gate did not fire on a shared GOVERNMENT platform.** `5.194.255.186` was
reported as ADP's "core portal". It presents cert CN `tamm.abudhabi`, O `Department of Government
Enablement` — the shared TAMM platform where the police are one tenant of ~160. The gate keyed on
"does the holder look like a hoster", and a government digital authority does not (16 announced
prefixes, under the >20 threshold). FIX: the rule is not about the holder. **If the customer owns
NO ASN and NO prefixes, nothing can be attributed by IP at all, and identity — a name or a
certificate — is the only evidence available.** `_no_space` now forces the gate on.

**D5 — my own `dns_no_service` detector asserted from absence.** It flagged `mail.`,
`autodiscover.` and `media.` as possible dangling DNS because their IPs were absent from Shodan.
All three are alive; the force's MX hosts are absent from every export too, because Shodan indexes
what it has scanned and mail infrastructure frequently is not. It was raised as MEDIUM on the
strength of abakus-tk.de, where `nmap --reason` had independently proved `host-unreach`.
FIX: demoted to a clarify question only (`stale_dns`), never an automatic finding. The operator's
answer is what turns it into one on a refine run. I broke the repo's oldest standing rule with a
detector I wrote three days earlier — absence of evidence is never a finding.

Guarded by `scripts/test_classify_adpolice.py` (wired into ship.py, BLOCKING): the two real
ssl.versions arrays, the real OpenText redirect chain, the delimited non-prod token against four
substring traps, the per-jurisdiction regime sets, and that dangling DNS is a question.

## Royal Bank of Canada — ASN discovery was DACH-shaped, and enterprises are not (2026-08)
RBC announces at least TWELVE autonomous systems (bgp.he.net: AS400736, AS400717, AS399410,
AS399409, AS398669, AS36256, AS32176, AS20069, AS16731, AS16730, AS16729, AS11544). The engine
found **two**, both from PeeringDB, and reported `scope: ASN AS399409,AS16729 · 1 prefixes`.
ROOT CAUSE — every source was RIPE-region shaped:
  * `ripe_db` searches rest.db.ripe.net, which covers the RIPE region only. **RBC is ARIN** -> "-"
  * `caida` returned nothing
  * `bgpview` does not resolve inside the container (documented, long-standing)
  * `peeringdb` lists only networks that PEER PUBLICLY -> 2 of 12
Fine for a Mittelstand target; structurally blind on every North American, Asian and Gulf
enterprise — i.e. on exactly the accounts worth the most.
FIX: **`asn_sources.ripestat()`** using RIPEstat `searchcomplete`, which indexes EVERY RIR, placed
FIRST in the chain so a RIPE-only failure can never decide the answer. It matches on the AS HANDLE
prefix rather than the holder description, so `_terms()` derives the acronym as well as the full
name ("Royal Bank of Canada" -> also "RBC"), and `_relevant()` then corroborates the HOLDER — which
is what keeps Bosch (China), Raiffeisenbank, Republic Bank & Trust, Red Bend Catholic College and
the RBC Convention Centre out, all of which share the handle prefix. Verified live: 2 -> 7 ASNs.
Also: `discover()` cap raised 12 -> **40**. A bank, carrier or government legitimately announces
dozens; a cap tuned for a Mittelstand target silently truncates the estate of every large account.
HONEST LIMIT: no public API is authoritative across all five RIRs, so 7 of 12 is better, not
complete. `clarify.py` therefore ALWAYS asks on a target with its own address space — it prints
what was found and invites the operator to paste what is missing (`confirm_asns` -> `include_asns`
-> `--asn`). The operator can read the full list off bgp.he.net in ten seconds, and that answer is
worth more than another heuristic.
RULE FOR ENTERPRISE ACCOUNTS: a discovery chain must be checked against a target OUTSIDE the region
it was built for before it is trusted. Every source here answered "-" without erroring, so the run
looked healthy while returning a sixth of the estate.
Guarded by `scripts/test_asn_enterprise.py` (wired into ship.py, BLOCKING): replays the REAL
captured searchcomplete response, asserts all 7 RBC ASNs are found AND that the six same-prefix
strangers are refused, plus that a DACH target does not regress.

## Per-user assessment quota + two evaluation accounts (2026-08)
Whitelisted `mr.nvisinc@gmail.com` (NVIS Inc) and `mordechai.rabinovich@rbc.com` (RBC), each capped
at **5 assessments**. There was no quota mechanism at all before this.
WHERE IT LIVES: `colt_auth.USER_QUOTAS`, beside `PARTNER_EMAILS`. "Who may use this" and "how much"
are the same question, and answering them in two files is how they drift apart. Addresses and
quotas are NOT secrets, so committing them makes them auditable in git and reviewable in a PR,
which an env var on a droplet never is. `USER_QUOTAS="a@x.com=10"` overrides at runtime.
Absent from the map = unlimited, so no existing user is affected.
**rbc.com is deliberately NOT in PARTNER_DOMAINS.** Only the named person was asked for; trusting
the domain would admit ~90,000 bank staff and could not be undone quietly afterwards.
BOTH FRONT DOORS ENFORCE IT, or the other one is simply the way around the cap:
  * web - `main._enforce_quota()` on BOTH `/api/assess` and `/api/compliance`, counting
    `store.count_jobs(email)`. Checked BEFORE the job row is created, so a refused attempt does not
    consume a slot or appear in History. Refusal is a 429 carrying the actual numbers.
  * Telegram - `bot.py` cannot see colt-web's jobs table, so it counts
    `cost_ledger.count_for_user()` on the shared `colt_events` volume, which both containers mount.
Counting includes failed and running jobs: counting only successes would let an evaluation account
retry forever on a target that legitimately produces nothing, and ignoring running jobs could be
beaten by firing several at once. Assess and Compliance share one allowance.
Both lookups fail OPEN - a quota check must never take an assessment down.
Guarded by `tests/test_quota.py`: the two accounts can log in, both are capped at 5, case and
whitespace do not bypass it, `someone.else@rbc.com` is refused, existing users stay unlimited, and
both front doors are asserted to enforce.
NOTE: ruff's F821 gate caught a missing `sys` import in the bot path during this change - the gate
added after the angermann NameError outage, doing exactly its job.

## THE DROPLET IS 4 GB / 2 vCPU / 80 GB — the NAME LIES (remember, 2026-08)
The droplet is called **`ubuntu-s-1vcpu-1gb-fra1-01`**, which is the size it was CREATED at. It has
since been resized and is now **4 GB RAM / 2 AMD vCPUs / 80 GB, FRA1, $28/mo**, public IP
64.225.108.200. I read the NAME off the DigitalOcean page and diagnosed an outage as memory
pressure on a 1 GB box. That was wrong and the operator corrected it.
RULE: a resource name is a label somebody typed once, not a fact about the resource. Read the spec
line ("4 GB / 2 AMD vCPUs / 80 GB"), never the name.
Consequence for triage: memory is NOT the default explanation on this host. 4 GB with ~54% used is
comfortable for Amnezia VPN + VideoDead + joplin + the colt stack.

## ALL SITES REFUSED = the SHARED PROXY, and a RESTART LOOP is not fixed by restarting (2026-08)
cybergod.ai, godeyes.ai and jobhuntwow.com all returned ERR_CONNECTION_REFUSED at the same moment
while the droplet answered ping. Three facts identify the fault without logging in:
  * ping replies -> host and networking are alive (ICMP is kernel-side)
  * CONNECTION REFUSED, not a timeout -> the SYN reached the host and got an RST: nothing is
    LISTENING on 443. A firewall drop or a dead host gives a timeout instead.
  * all three domains at once -> they share ONE reverse proxy. videodead-caddy owns :443 and
    fronts every site on this box, so its death is a total outage and never an application fault.
THE ACTUAL STATE was a CRASH LOOP, revealed by ship.py rather than by any check we had:
```
Error response from daemon: Container aa0e468c... is restarting, wait until the container is running
ssh OK - containers: colt-web, colt-assessbot, colt-cassandra, polara-web, jhw-web   <- no caddy
```
`docker exec` refuses on a restarting container, which is exactly where `deploy_web_direct.py` died
at the "wire cybergod.ai into the shared caddy" step. **A restart cannot fix a crash loop** — the
process dies again immediately — so `docker start` is the wrong reflex and it destroys the evidence.
Only the container's OWN log says why. The two causes that actually occur here:
  1. **Port conflict** — another container grabbed :80/:443 first, so the proxy cannot bind and
     exits. Note `polara-web` and `jhw-web` now run on this box; anything publishing 80/443
     directly collides with the shared proxy. `docker ps -a --format '{{.Names}}\t{{.Ports}}'`
     makes the collision visible instead of inferred.
  2. **A Caddyfile it cannot parse** — `deploy_web_direct.py` APPENDS the committed cybergod block
     into videodead's Caddyfile, so one malformed append takes every site on the box down together.
     Fix the committed snippet and redeploy; never hand-edit the file on the droplet.
## THE REPORTED LINE IS NOT THE FAULT — count the braces first (2026-08-07)
videodead-caddy crash-looped on `Caddyfile:90: unrecognized directive: klimaanlage-preise.de,` and
line 90 is a perfectly valid site header. The real defect was 11 lines earlier: `jobhuntwow.com {`
at line 79 had lost its directives AND its closing `}`, so everything below it parsed as that
block's contents. My own diagnostic had printed the answer — **`braces: open=22 close=21`** — and I
acted on the line number instead. Commenting out line 90 would have disabled a working site and
left the cause in place.
- `fix_unclosed_block()` runs BEFORE any line-number repair: on an imbalance it inserts the missing
  `}` at the first UNINDENTED `# <marker> END` or next site header reached while still inside a
  block. Unindented is load-bearing — a nested `log {` legitimately opens a brace at depth > 0.
- **The validator must be the container's OWN image.** The first version ran `caddy:latest`, pulled
  a NEWER Caddy, and returned an unrelated complaint (`wrong argument count after 'email', line 3`)
  that the running version never makes — so no line matched, the repair aborted and restored the
  backup. A validator on a different version is not a validator. `docker inspect -f
  '{{.Config.Image}}'` on the live container.
RULE: when a parser reports a line, first ask whether the file's STRUCTURE is intact. An unbalanced
delimiter makes every subsequent line a plausible-looking liar.

## A LATENT CONFIG IS A TIME BOMB — the write and the outage are separated by a REBOOT (2026-08-07)
The operator was right and I was wrong to reason from the crash: the stack was healthy through an
assessment that finished 18:06 UTC, and every site was refused by 06:00 UTC. `uptime` gave the
missing event — **`up 3:01` at 07:24 UTC = the droplet rebooted ~04:23 UTC**, every container "Up 3
hours", and the Telegram alert stream stops at 04:15:08 UTC.
**Caddy reads its Caddyfile ONCE, at start.** So a Caddyfile damaged at ANY earlier time is
completely invisible while the process keeps serving from its in-memory config — no error, no
alert, no symptom — until the next restart detonates it. The reboot did not cause the damage; it
merely exposed it. Anything that looks for "what changed just before the outage" will therefore
find nothing, which is exactly how this wasted a diagnostic cycle.
CONSEQUENCES, all of them structural:
- `forensics.py` exists to answer WHO WROTE THE FILE AND WHEN, not what the parser is complaining
  about: mtimes across /etc /opt /root /srv sorted chronologically, systemd timers + units started
  in the window, patchwatch, apt/unattended-upgrades (an auto-reboot is a prime suspect), ssh
  logins, disk/inode/OOM, per-container StartedAt/RestartCount, and the proxy's log OLDEST-FIRST
  (`--tail` only shows the millionth repeat of the loop). It is READ-ONLY.
- `recover.py --fix-caddy` now captures that timeline BEFORE it repairs anything — a fix overwrites
  the evidence that explains the fault, and one ssh round-trip is cheap next to losing the RCA.
- THE REAL GAP THIS EXPOSES: nothing validates the shared Caddyfile at WRITE time. Every project on
  this box (colt, polara/klima, jhw, jev) appends a managed block into videodead's Caddyfile, so any
  one of them can silently truncate another's block and nobody learns until a reboot. The fix is a
  post-write `caddy validate` + brace-balance check in EVERY appender, and a watchdog that validates
  the live file on a timer instead of waiting for a restart to discover it.

## A VALIDATOR MUST REPRODUCE THE CONTAINER'S ENVIRONMENT, NOT JUST ITS IMAGE (2026-08-07)
With the image fixed to `caddy:2-alpine` (the container's own), the validator STILL disagreed with
the running container: it said `wrong argument count after 'email' at /etc/caddy/Caddyfile:3` while
the container said line 90. Same file, same version. The difference was ENV: line 3 uses a Caddy env
placeholder (`email {$...}`), the running container has the variable, a bare `docker run` does not,
so `email` arrives with zero arguments. That phantom error aborted a repair that had ALREADY
succeeded (`open=20 close=19 -> inserting '}' before line 83`) and restored the backup.
FIX: `validate()` passes the container's own `.Config.Env` (minus PATH/HOME/HOSTNAME) with `-e`.
RULE: reproducing a container means image **and** environment (and mounts, and workdir). This is the
third instance of the same disease — the ruff gate that silently skipped, the esbuild path that was
"missing" on a machine where esbuild worked, and now a validator that could not see what the process
sees. A check that does not reproduce its subject is not a check.
CONSEQUENCE HERE: closing the brace restores cybergod.ai, godeyes.ai and klimaanlage-preise.de.
jobhuntwow.com comes back as an EMPTY block — its directives were clobbered and must be restored
from its own deploy; recover.py will not invent routing for another project.

## caddyguard — the shared Caddyfile is now GENERATED, not edited (2026-08-07, `python caddyguard.py`)
CONFIRMED RCA: a deploy at **16:15:56 UTC 6 Aug** rewrote `/opt/videodead/Caddyfile` and truncated
jobhuntwow's block (directives + closing `}` gone); `/opt/videodead/Caddyfile.bak.1786032956` is that
deploy's own backup, taken seconds before. Caddy served from MEMORY for 12h. Patchwatch's
`apt full-upgrade` at 04:21:14 upgraded the kernel (6.8.0-136 -> 137) and rebooted at **04:22:42**;
Caddy re-read the file and every domain died together. Last interactive SSH was 15 July — no human.
FIVE guardrails, all installed by the ONE command `python caddyguard.py`:
1. **ISOLATION.** `/opt/caddyguard/blocks/<project>.caddy` fragments; the monolith is ASSEMBLED.
   A project can no longer delete another's bytes because it never touches them. NOT conf.d+import:
   the container bind-mounts a single FILE, so an import dir needs a new mount = recreating the
   shared proxy = an outage of every site to fix an outage.
2. **WRITE-TIME VALIDATION.** `caddy validate` in the container's own image AND env, plus
   brace-balance + marker-pairing (`# x BEGIN`/`END`) — the structural check alone catches the exact
   2026-08-07 defect with no container at all. Refuse + rollback on failure.
3. **RUNTIME WATCHDOG.** `caddyguard.timer` every 10min + `OnBootSec=2min` (a reboot is exactly when
   latent damage detonates). Alerts to Telegram and self-heals by re-assembling from fragments.
4. **REBOOT GATE.** `patchwatch.py` now runs `caddyguard check --heal` before `shutdown -r` and
   REFUSES to reboot on an invalid proxy config. The reboot was the detonator and it was ours.
5. **EXTERNAL EYES.** `.github/workflows/uptime.yml`, every 10min, OFF-BOX. Grafana/Loki/colt-web
   alerting all live behind the proxy that died — monitoring inside the failure domain is mute
   exactly when it matters. Nothing told the operator for ~6h.
**IN-PLACE WRITES ONLY** (`open(...,"w")`, never `mv`): a single-file bind mount pins the INODE, so
replacing the file leaves the container reading the old one forever.
Guarded by a test that replays the real shape: structural rejects it, a klima write leaves the jhw
fragment byte-identical, restore SKIPS a newer backup whose block is rubble and takes the balanced
one, and a fragment carrying another project's markers is refused.

## STAGING TWIN — a second droplet, and the reboot is the whole point (2026-08)
The 2026-08-07 outage had no environment in which the change could be REBOOTED before production.
`stagegate.py` (a BUILDING BLOCK; ship.py calls it before the prod deploy) fixes exactly that:
deploy to staging -> health -> **reboot it** -> health again -> AI digest -> only then production.
- **STAGING = 165.245.244.174**, FRA1, 4 GB / 2 AMD vCPU / 80 GB, Ubuntu 24.04 — deliberately the
  SAME size, image and region as prod. A twin that differs in region or size is not a twin: latency
  to the inference endpoint, host hardware generation and kernel line are precisely the variables
  that make "it worked in staging" untrue. Canada was rejected for staging (it is a DR idea, not a
  staging one) and because /privacy claims EU-only data.
- **SYNTHETIC DATA ONLY.** Staging builds its state from the committed RFC 5737 demo fixtures. No
  production personal data crosses over, so the EU-only claim needs no second location disclosed.
- **An LXC on the prod box was rejected**: 4 GB with ~1.8 GB free cannot hold a twin, and a
  container sharing the host kernel cannot validate a kernel reboot — the one thing we need to test.
- **The gate is DETERMINISTIC.** `quorum.py` runs INSIDE colt-web on staging (that is where
  OPENAI_API_KEY lives) and asks 2 soldiers (deepseek, maverick) + 2 auditors (gemma, kimi), one per
  vendor, for a written verdict. They produce the REASONING and the risk digest; the GO/NO-GO comes
  from the checks. Operating principle 5, and it fails safe both ways: a 429 cannot block a good
  release, and an agreeable model cannot wave through a dead container. Dissent is surfaced loudly.
- ship.py EXITS 2 and touches nothing in production on NO-GO. `--no-stage` overrides deliberately,
  `--fast-stage` skips only the reboot (weaker — say so).
- A broken GATE must never become a broken DEPLOY: an exception in stagegate is reported and the
  ship continues. Same doctrine as the FP auditor — a check is a signal, not an authority.
FIRST RUN CAUGHT TWO DEFECTS IN THE GATE ITSELF (both fixed; the gate correctly refused to promote):
1. **It never DEPLOYED to staging.** It installed Docker and then health-checked a `colt-web` that
   had never been put there — 14 checks failed for entirely the wrong reason. `deploy_to_staging()`
   now runs the SAME `deploy_web_direct.py` production uses, with `DROPLET_HOST=<staging>` and a new
   `--no-proxy` flag (the twin has no shared caddy to wire into). Using a different deploy path for
   staging would test something other than what ships. It also creates the external
   `videodead_appnet` (compose declares it external; on a fresh box it does not exist) and copies
   the runtime `.env` prod -> staging, because the engine needs a real OPENAI_API_KEY to run at all.
2. **The reboot test could pass without a reboot.** It waited for ssh to answer, and right after
   `systemctl reboot` is issued the box is still up — so it reported "back after 1s" and scored a
   pass. Now it compares `/proc/sys/kernel/random/boot_id`, which is regenerated on every boot, and
   requires it to CHANGE. RULE: a test that can pass without the event happening is not a test.

## SEO — the tags were the SECOND cause; the bot gate was the first (2026-08)
Google showed "colt — cyber pre-sales" for cybergod.ai months after the rebrand. Editing meta tags
would have changed NOTHING: `BOT_404=1` with an empty `BOT_404_ALLOW` served **Googlebot a 404**, so
Google could never re-crawl and kept serving a snippet harvested from the old GitHub Pages landing.
- `visitors.py` default is now `googlebot,bingbot,duckduckbot,linkedinbot,slackbot,whatsapp,
  telegrambot`. Everything else — scrapers, SEO harvesters, AI-training crawlers, vuln scanners —
  still gets a 404. `/sitemap.xml` joined `/robots.txt` in EXEMPT_EXACT: a crawler fetches it before
  it has identified itself, and 404-ing the sitemap silently kills indexing.
- `index.html` carries title/description/canonical/robots + OG + Twitter + **JSON-LD**
  (Organization / WebSite / SoftwareApplication). The JSON-LD is what earns a rich result instead of
  a bare blue link, and it is the highest-leverage SEO item on a single-page app.
- `public/robots.txt` and `public/sitemap.xml` must AGREE with the bot gate — a crawler allowed in
  robots.txt but 404'd by the gate just burns crawl budget. Only public routes are in the sitemap;
  /app and /login are owner-scoped and would only ever index a 401.
- Product scope is **"Sales and Pre-Sales"**, not pre-sales: `login.h1a` in all six locales, the
  Cassandra system prompts, legal.jsx, and the API title.

## A PROMPT AND A DEFAULT ARE BOTH CUSTOMER-FACING (2026-08)
Two Colt leaks survived the rebrand because the brand gate greps RENDERED artifacts:
1. `assistant.py::SYSTEM_PROMPT` said "senior Colt Technology Services (DACH) pre-sales assistant" —
   so Cassandra introduced herself as a Colt assistant in every reply. A system prompt is a string
   that reaches a human, via the model.
2. `notify.py::ALERT_MAIL` DEFAULTED to `feranicus@s4biz.io,jevgenijs.vainsteins@colt.net`. Removing
   the address from compose was not enough: if `ALERT_EMAIL` is ever unset (fresh deploy, wiped
   .env) the default silently resumes mailing a former employer platform telemetry and security
   alerts — a data-protection problem, not just noise. **A default IS configuration.**
Also fixed: `/api/demo`'s public `access_contact`, the login denial message, the alerts digest.
LEFT DELIBERATELY: `ALLOWED_EMAIL_DOMAIN=colt.net` still lets Colt AEs LOG IN, and the internal
docker names (`colt-web`, `colt-net`, `colt_auth.py`). Removing the login domain would lock out
current users and is a business decision, not a rebrand.

## STANDING RULE — the audit panel's findings get ACTED ON, every run (operator's instruction)
When the staging panel raises something and I AGREE it is correct, it becomes a check or a fix in
the SAME change — not a note, not a "known gap". The operator asked for this explicitly, and the
record justifies it: the panel has already caught defects I would have chased for another cycle.
  * kimi-k2.6 diagnosed `d41d8cd98f00` as the md5 of the EMPTY STRING, which identified a disabled
    admin API from the hash alone. Best single catch of the incident.
  * deepseek + gemma twice spotted that a check's DETAIL contradicted its own VERDICT — the tell
    for "the check is broken, not the system". Both times they were right.
  * kimi's "engine_runs proves invocation, not correctness" produced the artifact-content check.
  * kimi's "config drift is undetected" and "one bad block takes every domain down" produced
    `config_drift` (running config vs disk, via the admin API) and `bad_block_refused` (a NEGATIVE
    test: write a deliberately broken fragment, prove it is REFUSED and the live file is unchanged).
AGREEING IS THE OPERATIVE WORD — the panel is advisory and it is wrong often enough to matter:
  * kimi inverted config_reread ("started AFTER the write means stale") — the opposite of the truth.
  * kimi invented an engine job queue, an ENGINE_MODE env var and a k8s manifest, none of which
    exist in this system.
  * llama-4-maverick repeatedly restates the failure as its own diagnosis ("the engine is not
    running correctly") without adding information.
PATTERN WORTH KEEPING: the panel is strong reasoning FROM evidence in front of it and unreliable
when extrapolating to architecture it cannot see. So: feed it more evidence, never more authority.
Implement what is right, say plainly what is wrong and why, and never let a NO-GO from a model
override a deterministic check — in either direction.

## caddyguard is a BUILDING BLOCK of ship.py — and the argv length limit that hid as "ssh missing"
I shipped `python caddyguard.py` as a SECOND command. That is operating principle 7, broken again:
the operator runs `python ship.py`, full stop. caddyguard is now invoked BY ship.py after verify,
and is idempotent so a routine deploy is safe — `restore` only acts when a fragment is missing,
empty or unbalanced (otherwise a normal ship would silently overwrite a project's live config with
whatever an old backup held). `--force` overrides; guarded by a test asserting both directions.
THE BUG THAT MADE IT FAIL: `ssh_script` base64'd the script INTO argv (`echo <b64> | base64 -d |
bash -s`). Fine for a diagnostic; caddyguard ships three files (~26 KB of base64) and Windows caps
a command line at ~32 KB. Python surfaces that overflow as **FileNotFoundError**, which the handler
reported as **"ssh client not found on this machine"** — a perfectly confident, completely wrong
diagnosis on a machine where ssh works. FIX: the script goes over **stdin** (`ssh host 'bash -s'`,
`input=script`); no length limit, still ONE session.
RULE: never put a payload in argv. And when an error names a missing *program*, check whether the
*command line* is the thing that is wrong.
THEN THE NEXT RUN FAILED ON `$'\r': command not found` — moving the payload to stdin re-exposed the
CRLF trap this file has warned about since deploy.py: **Python text mode on Windows rewrites every
`\n` we write into `\r\n`**, so bash got a CRLF script. `input=script.encode("utf-8")` in BINARY
mode (decoding stdout ourselves) fixes it and keeps the UTF-8 handling. Guarded by a test that
sends the real payload to `bash -s` as bytes and asserts the umlauts survive.
`forensics-*.txt` is gitignored — it is diagnostic output (host inventory, IPs, log excerpts),
never source, and three of them were accidentally committed.

`recover.py` is the one command: it probes from outside, then in ONE ssh session reads uptime,
disk, memory, who is bound to 80/443, running/stopped/RESTARTING containers, `docker logs` for
every crash-looping container, published-port collisions, and a `caddy validate` of the live
config. It states the verdict in words, and it REFUSES to restart anything when a crash loop is
present — blind restarts there just hide the cause.

## jobhuntwow.com — I fixed the WRONG LAYER, twice, and the header said so (2026-08-07)
The site returned `HTTP/1.1 200 OK`, `Server: Caddy`, **`Content-Length: 0`**. I wrote a Caddy block
that served `/srv/jobhuntwow` with `file_server`, shipped it, and claimed success. Twice.
**THE TELL I WALKED PAST: my block contained `-Server` (strip the header) and the response still
carried `Server: Caddy`.** A header that should have been removed and was not means the block you
are looking at is NOT the block serving the request. That single line disproved my diagnosis before
I ever deployed it.
ROOT CAUSE OF THE WRONG FIX: two sources described jobhuntwow and I picked the older one.
`deploy_jobhuntwow_caddy.py` (July) provisions a STATIC one-pager — real, but superseded.
`jobhuntwow-app/docs/CADDY_ARCHITECTURE.md` (dated 2026-08-07) describes what actually runs: a
FastAPI app with SSE behind `reverse_proxy jhw-web:8000 { flush_interval -1 }`. Serving a FastAPI
app with `file_server` over an empty directory produces exactly an empty 200. **When two documents
disagree, the DATED one that describes the running system wins — check which, do not pick the one
you found first.**
THE DEEPER FIX — jobhuntwow is a DIFFERENT PROJECT with its own orchestrator (`python jhw.py
deploy` -> deploy_direct.py -> deploy/fix_caddy.py) and its own committed snippet at
`jobhuntwow-app/deploy/caddy/jobhuntwow.caddy`. Keeping a second copy in THIS repo and pushing it
on every ship would make the two projects overwrite each other forever — the "a value with two
homes" defect (ENRICH_MODELS, four homes) one level up. `caddyguard.jhw_snippet()` therefore reads
**their** file when the sibling checkout is present; `deploy/caddy/jobhuntwow.caddy` is a
byte-identical fallback for a machine without it. caddyguard runs `migrate` (re-split the live
monolith) BEFORE `assemble`, so a jhw deploy that appends to the monolith is captured, never
reverted.
THREE CHECKS ADDED, each aimed at a thing that looked green while the site was blank:
  * **the fragment is compared to the committed block** (`cmp -s`), not probed for a keyword. The
    old predicate asked "does it contain file_server" — wrong content AND the wrong shape of
    question.
  * **the UPSTREAM is checked, not just the config**: jhw-web running · on `videodead_appnet` · on
    ONE network only (two networks -> Docker DNS hands caddy an unreachable IP -> intermittent
    502s, per CADDY_ARCHITECTURE.md rule 2) · and caddy's own `wget http://jhw-web:8000/`.
    A perfect Caddyfile in front of a dead container is an empty 200.
  * **probes report BYTES, not just the status code.** `200` was the whole problem. Anything under
    200 bytes on a 2xx/3xx is flagged `EMPTY BODY, the upstream is not answering`.
  * **production drift**: `caddy adapt` (disk) vs the admin API (running) — the file was right and
    the process was serving something else, which is the 2026-08-07 mechanism. On a mismatch it
    force-loads via `POST /load`. kimi raised this for staging; it belonged on prod.
ALSO REMOVED: stagegate's `bad_block_refused` "negative test" wrote a deliberately broken fragment
into the LIVE `/opt/caddyguard/blocks/` and re-assembled the running config — it took staging-caddy
down and reported `post_reboot_proxy_routes 000`. **A negative test that mutates production-shaped
state is not a test, it is an outage with a pass/fail label.** `config_drift` stays because it only
reads.

## THE CHECK WAS BROKEN, NOT THE SYSTEM — config_drift blocked two clean deploys (2026-08-07)
`config_drift` md5'd `caddy adapt --config /etc/caddy/Caddyfile` against the admin API's
`GET /config/` and reported DRIFT on a healthy staging box, twice, taking the gate to NO-GO and
refusing to promote a good build. All four panel models agreed the system was broken and proposed
fixes for a fault that did not exist. **They were all wrong, and so was I.**
Those two endpoints are two SERIALISATIONS of ONE config: `adapt` emits the adapter's JSON; the
admin API re-marshals from parsed Go structs, reordering keys and filling in defaults (`admin`,
`logging`, `automatic_https`). Byte equality was never achievable, so the check could only ever
fail — it was a false positive by construction, on every box, forever.
**THE TELL WAS IN ITS OWN OUTPUT: the two hashes were IDENTICAL before and after the reboot.**
Caddy re-reads its config at start, so a genuinely stale process CANNOT survive a restart — that
is the entire mechanism of the 6 Aug outage. A check whose result is unchanged by the event that
would fix the fault is not measuring the fault. That single observation settles it without needing
to know anything about Caddy's JSON.
FIX: `agent.py drift` compares WHAT IS SERVED — the set of matched hostnames and the set of
terminal handlers (proxy upstreams, file_server, respond, root). Stable under re-serialisation, and
it is exactly what changes when a block is truncated or replaced. ONE implementation: stagegate's
`config_drift` and caddyguard's production DRIFT step both shell out to it, so the gate and the
repair can never disagree. `admin off` or an unparseable config prints SKIP — a check that cannot
see its subject must say so, not invent a verdict.
Guarded by `test_drift.py` (wired into ship.py, BLOCKING) which pins BOTH directions: the healthy
re-serialisation is not flagged, the 6 Aug truncation is caught by name, and the file_server-in-
front-of-a-FastAPI-app shape is caught by handler. Proven by deleting the handler comparison —
2 failures — and restoring it.
ON THE PANEL: this is the counterexample to trusting it. kimi's diagnosis ("the container restart
logic does not re-read the updated config file") is refuted by the check's own reboot evidence, and
deepseek/gemma/maverick each restated the failure as a cause. The standing rule stands — act on
what the panel gets RIGHT — but the deterministic checks decide, and when a check contradicts
physics, suspect the check. Kimi did land one true observation worth keeping: `config_reread`
passes on TIMING (started N seconds after the write) and therefore proves startup ordering, not
that the right file was read. The semantic drift check is what actually answers that question.

## A CHECK YOU CANNOT SEE IS NOT A CHECK — and a probe that discards the body proves nothing
Two defects in one caddyguard run, both mine, both the same disease as the ruff gate that silently
skipped for weeks:
1. **The DRIFT section ran on the droplet and was never printed.** `caddyguard.main()` iterated a
   HARDCODED tuple of section names, so a section the remote script emits but the list does not
   mention is dropped on the floor. Two homes for "which sections exist". FIX: print every section
   `sections()` returns, in emission order (`recover.sections` is an ordered dict, asserted by a
   test) — adding a section to the script is now the only edit needed.
2. **The jhw upstream probe was `wget -qS -O /dev/null`.** It reported `HTTP/1.1 200 OK` for an app
   that may be returning NOTHING — the precise failure under investigation. I had written the rule
   ("probes report BYTES, not just the status code") one screen earlier and then broke it in the
   next function. FIX: `wget -qO- ... | wc -c` on `/` AND `/api/health`, plus the container's
   health state and image/start time. That is decisive: **0 bytes from `jhw-web:8000` itself means
   the fault is inside that container (its own project, `python jhw.py deploy`), not in the shared
   proxy; N>0 bytes upstream with 0 bytes publicly means the proxy is dropping it and it is mine.**
   Until that number exists, either claim is a guess.
Also: a 3xx has NO BODY BY DESIGN, so flagging `www.jobhuntwow.com`'s 301 as "EMPTY BODY" was
noise — and noise in a diagnostic is how the one real line gets skipped.
`_selftest()` earned its keep again: `printf '%-12s'` inside the %-formatted template raised
TypeError and the run aborted with "Nothing was sent to the droplet" instead of shipping a broken
script. Every literal % in that template must be doubled.

## THE BIND-MOUNT HOP — three green lights over a dead site (2026-08-07, the jobhuntwow finish)
The operator restored jobhuntwow with its OWN orchestrator (`python jhw.py deploy`) and that run
printed the answer my whole investigation had missed:
```
[!] caddy is reading a STALE copy of the Caddyfile (bind-mount inode was replaced)
    host file : 979f0bd3...   in caddy : f4aaa45a...
-> restarting caddy so the bind mount re-resolves the path
```
`/etc/caddy/Caddyfile` is a single-FILE bind mount, so the container is pinned to an INODE. Once
something replaces the file rather than truncating it, the container reads the OLD inode forever —
and EVERY layer I had built reported success over it:
  * `caddy validate` passes — it validates a freshly-mounted TEMP COPY of the new text, never the
    file the running container actually reads;
  * `caddy reload` succeeds — and loads the STALE bytes;
  * my new semantic drift check passes — because BOTH of its sides (`caddy adapt` and the admin
    API) read from INSIDE the container, so they agree perfectly on the wrong config;
  * the watchdog passes — the file is valid and the container is running.
Four checks, all honest, all measuring hops that were fine. **CONFIG HAS THREE HOPS and a check
must say which one it measured:** host file -> container file (crosses the MOUNT) -> running config
(crosses the RELOAD) -> what is actually SERVED. I had built hops 2 and 3 and never hop 1 — even
though `deploy_direct.py` in the jobhuntwow project had solved it months ago with a plain
host-vs-container sha256, and CLAUDE.md already carried the inode rule in prose.
FIX — `agent.py::mount_sync()`, used in three places so no path can skip it:
  * `apply()` calls it AFTER writing and BEFORE reloading, and REFUSES (rolling the file back)
    rather than reloading into a mount the proxy cannot see;
  * `cmd_check --heal` (the 10-minute watchdog) treats a stale mount as UNHEALTHY and restarts to
    re-resolve it — a restart is the only thing that re-resolves a single-file mount, so it is done
    only when the hashes actually disagree, since it blips every vhost on the box;
  * `cmd_drift` checks hop 1 FIRST and names the broken hop instead of reporting a generic OK.
  Failure to repair is reported, never swallowed: `STILL STALE after restart` says the mount source
  is not the file we are writing.
DEV/TEST AND PROD BOTH: stagegate gains `mount_fresh` so the twin exercises it before production
ever does, and caddyguard runs the same agent code on prod. ONE implementation.
THE LLM PANEL got the facts, not more authority: `quorum.ARCH` now states the three hops, that
validate proves nothing about hops 1-2, that adapt-vs-admin-API are two serialisations and can
never be byte-equal, that a fault surviving a reboot is not staleness, and that there is no k8s /
config-map / hot-reload watcher in this system so it must not propose one. On the config_drift
false positive all four models invented plausible fixes for a non-existent fault; they were
reasoning without a map. Deterministic checks still decide.
HONEST ACCOUNTING: I did not truncate the jhw block — `migrate` found it already at braces 0/0,
which is the 6 Aug damage. But my run REPORTED SUCCESS while the site stayed dead, twice, because
every check I owned was on the wrong side of the mount. Guarded by test_drift.py (detected ·
repaired by restart · unfixable reported · read-only never restarts · no-container and unreadable
both SKIP), proven by disabling the comparison and watching the suite fail.

## THE PANEL SAID NO-GO 4/4 AND IT SHIPPED ANYWAY — three defects, one false green (2026-08-07)
The operator: *"all consensys models said No-Go but some how it was still passed to the prod? WTF?"*
He is right, and this time **the panel was correct and the deterministic gate was lying.** The two
lines that matter, verbatim from the run:
```
mount_fresh    OK   container reads the current file (3af610cdeb71) - bind mount is not stale
config_drift   OK   drift check unavailable: STALE MOUNT STALE MOUNT: host= container=3af610cdeb71
```
`host=` is EMPTY. Three separate defects composed into 33/33 GREEN:
1. **`agent.py::mount_sync` hashed a HARDCODED host path.** `LIVE` defaults to production's
   `/opt/videodead/Caddyfile`; the staging proxy mounts a different file, so `_sha_host` returned
   `""` and the check read *"there is no file here"* as *"the mount is stale"*. Absence of evidence
   became a finding — the oldest rule in this repo, broken by me, in a guard I wrote to enforce it.
   FIX: `mount_source(c)` asks DOCKER where the container's own mount comes from (which is exactly
   what stagegate's `mount_fresh` already did correctly — two implementations of one question, one
   right and one wrong), and a missing host file now returns SKIP.
2. **A catch-all branch scored an UNRECOGNISED verdict as a PASS.** `*) chk config_drift yes
   "drift check unavailable: $D"`. The agent printed `STALE MOUNT ...`, which matched none of
   `OK*`/`SKIP*`/`DRIFT*`, so the fallback turned a failure into a success. **A fallback that
   converts an unknown answer into a pass is strictly worse than having no check at all** — it is
   the same disease as an i18n fallback printing the key, one level up and far more dangerous.
   FIX: the wildcard now FAILS, and `test_gate_integrity.py` greps the bash for the SHAPE
   `*) chk … yes` so it cannot be reintroduced under another name.
3. **Nothing noticed that a check reporting PASS contained "STALE MOUNT" in its own detail.**
   All four models noticed, in four different sentences. deepseek and gemma had made the identical
   observation about a different check the day before. **A signal the panel produces reliably
   belongs in the deterministic layer, where it can block.** FIX: `self_contradictory()` demotes
   any PASS whose detail carries failure language (stale/drift/unavailable/cannot/failed/broken/
   replaced inode/…), with a `_BENIGN` allow-list so "no silent drift" and "bind mount is not
   stale" do not flag themselves.
**GOVERNANCE, CHANGED DELIBERATELY AND NARROWLY.** Models still cannot veto a release — a 429 must
never block a good deploy and an agreeable model must never wave through a dead container; both
directions are asserted. What is new: **a UNANIMOUS panel (>=3 reviewers, all NO-GO) against a
GREEN gate now HALTS**, printing why and requiring `OVERRIDE_PANEL=1`. Rationale: that exact
pattern has now twice meant *a check is lying*, and it must reach a human BEFORE production rather
than in a note after it. A split panel still does not block.
`_decide_from_verdict()` was EXTRACTED from `run()` as a pure function — the decision had been
buried inside a 90-line routine needing two droplets to exercise, which is precisely how the
catch-all shipped unverified. Guarded by `tests/test_gate_integrity.py` (12 tests), proven by
reintroducing all four defects one at a time and watching each be caught.
FOOTNOTE, in fairness to the deploy: production was never actually broken. `LIVE` exists on prod,
so the prod DRIFT step correctly printed *"running config serves exactly what the file says
(11 hosts, 9 handlers)"*. The system was fine; **the gate was not**, and a gate that cannot be
trusted when it is green is worth nothing when it is red.

## TWO LANGUAGE BARS, AND A HEADER ROW I DID NOT RE-MEASURE (2026-08-07)
The operator photographed both: `/contact` showing a language selector in the header AND another
in the page body, and the German `/experience` with "Zur Anwendung" sitting on top of the "Wer wir
sind" heading.
1. **The duplicate control.** Every legal page rendered its own `<LangToggle/>` in `.legal-head`
   from the days before SiteHeader existed. Once the header carried the site-wide toggle, that
   second one became a second control for one value — the "two homes" smell, in the UI. Removed
   from Contact / Impressum / Privacy / Experience; the header's is the only one. NOT removed from
   NewAssessment: that one lives INSIDE the Art. 13 privacy notice and is a different control in a
   different context, so the guard is scoped to "a page that renders SiteHeader must not also
   render a LangToggle" rather than the blunter rule that would have flagged it.
2. **THE HEADER ROW IS ARITHMETIC AND I ADDED A CONTROL WITHOUT RE-MEASURING.** CLAUDE.md already
   said, twice, that a fixed-height flex bar must be added up — brand + every control + gaps — in
   the LONGEST language, because German is systematically longer and overflows first. I added
   `nav.about` to the nav and shipped. Measured after the fact: German went from 834px to 914px
   against a `.wrap` inner width of 1136px at full size — and the row has no `flex-wrap:nowrap`,
   so at a narrower viewport it wrapped, and the second line escaped the fixed 58px box and landed
   on the page content.
FIX, one component for both problems: **`MoreMenu`** collapses Who we are / Contact / Impressum /
Privacy behind a single trigger. On desktop the row gets SHORTER than before those links existed
(de 914 -> 834). On a phone it is the only route to those pages at all, because
`#hd nav a:not(.btn){display:none}` hides plain links and the bottom tab bar is already full at six
items — which is what the operator asked for. The trigger shows the word on a wide screen and a
glyph on a phone, chosen in CSS so there is no resize listener and no second breakpoint to keep in
sync (same pattern as the language toggle's Deutsch/DE).
Also: `flex-wrap:nowrap` on `#hd .wrap` so a fixed-height row can never put a second line over the
page, and plain nav links now hide below **1000px**, not 720px — there was a band between the two
where the row could still overflow and nothing measured it.
GATE: `tools/header_layout.mjs`, wired into ship.py AND the frontend image build. It computes the
row width in all six languages at three breakpoints against the budget READ FROM THE CSS
(`.wrap` max-width 1180 minus 22px padding each side), asserts the menu reaches every page, and
asserts exactly one language toggle exists. Proven by reintroducing both defects and watching each
fail. RULE, now enforced rather than written down: adding anything to the header means running the
measurement, and the measurement is part of the build.

## THE ARCHITECTURE MAP, THE CONSENSUS SECTION, AND ONE CLAIM I WOULD NOT WRITE (2026-08-07)
The landing map predated half the system. Added five nodes and nine edges: SCOPE GUARDS (the
ownership gate / PSL / co-tenant / per-domain budget — the accuracy story and the hardest-won code
in the product), AI CONSENSUS, STAGING TWIN, PROXY GUARD, COST LEDGER; COMPLIANCE relabelled
"EU + Canada regimes"; viewBox 700 -> 790 so the new row is inside the canvas. A diagram that omits
half the system is not neutral — it is a claim about the architecture that is no longer true.

New landing section `#consensus`, six defensible advantages: no shared failure domain (four
vendors, not four hats on one), the auditor is never the author and never the same vendor, code
decides and models advise, no identifier reaches a slide without evidence, cost counted per run in
a ledger, and chain order set by measurement on the REAL prompt (rankings invert between a toy
prompt and a 13k-character one). Deliberately NOT added to the nav: the header row is at budget and
`header_layout.mjs` would have failed the build — the discipline working as intended.

**THE OPERATOR ASKED FOR "our consensus works better than Claude, you can't argue with that" ON THE
SITE. I DID NOT WRITE IT, AND SAID SO.** Three reasons, in order of weight: (1) it has not been
measured against anything — there is no benchmark in this repo comparing the panel to any named
competitor, and the product's entire credibility rests on "absence of evidence is never a finding"
and "no invented identifiers"; a marketing page that violates the discipline the engine enforces
poisons the engine's own claims. (2) Comparative advertising naming a competitor needs
substantiation under UWG s.6 and the UCP Directive — an unmeasured superiority claim against a
named product is the kind of thing a bank's counsel notices. (3) It is not needed: multi-vendor
adversarial review with a deterministic gate IS the differentiator, and every sentence of it is
true and evidenced. If a comparison is wanted later, the honest route is `compare_models.py`
extended to a published methodology and a dated result — that would be worth far more than the
assertion.

KIMI'S PANEL FEEDBACK, ACTED ON (the standing rule):
  * AGREED — `config_reread` asserted ORDERING ("started 1s after the file was written") and its
    own detail quoted "caddy reads config only at start", describing the hazard while claiming
    success. Now that `mount_fresh` proves hop 1 and the semantic `config_drift` proves hops 2-3,
    the timing-only PASS was redundant and misleading; it now names the checks that actually prove
    content instead of implying it proves it itself.
  * AGREED, AND IT WAS A REAL GAP — nothing asserted WHICH domains are served. `config_drift`
    compares disk to running, so a deploy that rewrites the file AND reloads leaves both sides
    agreeing on an estate missing a customer's domain: the 6 Aug shape one level up. New
    `agent.py roster` checks the running config against a COMMITTED list of expected vhosts,
    wired into caddyguard (prod) and stagegate (`vhost_roster`, scoped by CADDY_EXPECT so staging's
    single vhost does not fail against production's six). Verified against the real shape: removing
    the jobhuntwow block is caught by name.
  * DISAGREED — "config_drift uses an unstable hash comparison / '2 hosts, 1 handler' is too
    coarse". It compares SETS of hostnames and terminal handlers, not counts and not hashes; the
    counts are only the printed summary. The hash comparison Kimi is remembering was removed
    earlier the same day, for exactly the reason it gives.

## IT PASSED STAGING AND FAILED PRODUCTION BECAUSE IT WAS NEVER THE SAME CODE (2026-08-07)
One `python ship.py`, one commit, three different answers from the SAME check:
```
local tests   : catalogue 253 keyed + 203 by-English = 456   PASS
staging build : catalogue 253 keyed + 203 by-English = 456   PASS   <- and the AI panel said GO
production    : catalogue 253 keyed + 213 by-English = 466   FAIL, 11 missing per locale
```
A commit cannot produce three catalogues. **It was never the same code.** `pack()` read the
WORKING DIRECTORY, and ship.py reads that directory FIVE separate times — test it, commit it, push
it, pack it for staging, pack it AGAIN for production. An editor (mine — I was still writing
translation files while the operator ran the ship I had just told him to run) changed the tree
between the staging pack and the production pack. The pack sizes recorded it: 4639 KB then 4640 KB,
docker context 389 KB then 429 KB.
**So the staging gate was not wrong and the panel was not wrong — they validated a DIFFERENT
ARTEFACT.** A green staging run says nothing about production if the two were handed different
bytes, and neither does a safe-point tag that names a commit nobody deployed.
FIX — `deploy_web_direct.pack()` now packs `git archive HEAD`: the COMMIT, which is immutable. The
tested tree, the staging input, the production input and the `good-*` tag are then provably the
same bytes, and a mid-flight edit simply does not ship until it is committed. A dirty tree is
reported ("packing the COMMIT abc1234, not your working copy") rather than silently shipped, and
`_keep()` is now the single exclusion rule shared by both the archive path and the fallback.
SIDE BENEFIT: `git archive` emits REPOSITORY bytes (LF), not the Windows working-copy CRLF, so the
deployed artefact stops depending on which platform packed it.
PROCESS LESSON, MINE: **do not edit the working tree while the operator is running a deploy.**
Finish, verify, tell them to run it, then stop touching files. The code fix makes the failure mode
harmless, but the discipline is what stops the confusion.
Guarded by `tests/test_deploy_immutability.py` (5 tests): the pack equals HEAD; an edit made during
a ship cannot reach the deploy; two packs of one HEAD are byte-identical in content; exclusions
still hold; a dirty tree is reported with real paths. Proven by restoring the working-tree pack and
watching the suite fail.
ALSO FIXED: `_tree_state()` sliced `ln[3:]` off `git status --porcelain` and printed
"eploy_web_direct.py". A diagnostic that misreports a path sends the next investigation down the
wrong road — same class as the co-tenant guard that misreported its own denominator.

## THE ANDROID "⋮" CIRCLE — a control that inherits the wrong geometry (2026-08-07)
Photographed on a phone: the MoreMenu trigger rendered as a hollow circle beside the language
pill, reading as a broken element rather than a menu. Cause is arithmetic, again: it reused
`.btn sm ghost`, which is `border:1.5px solid var(--line)` + `border-radius:999px` +
`min-height:34px` wrapped around a **~6px glyph**. A 999px radius on a box that is 26px wide and
34px tall IS a circle. It also carried a heavier border and a different height than the
`.lang-trigger` sitting next to it, so the two controls did not read as siblings.
FIX: `.more-t` is no longer a `.btn`. It mirrors `.lang-trigger` field for field — border,
radius, min-height, font-size, font-weight, padding, background — so the pair are visibly the same
family, and the glyph is an inline SVG rather than the "⋮" CHARACTER (a text glyph inherits
line-height and font metrics and renders differently on every Android font, which is what made it
look mis-centred). Phone: 41x34px, ratio 1.21 — a pill, not a circle.
GATE: `tools/header_layout.mjs` now also asserts the CONTROL's geometry, not just the row's — the
six properties must match `.lang-trigger`, and the trigger may never be a `.btn` again.

**TWO OF MY OWN CHECKS WERE VACUOUS AND THE NEGATIVE TEST IS WHAT EXPOSED THEM:**
1. A comparison printed `match` for six properties while reading `<missing>` from BOTH rules — it
   was comparing two absent values. The extractor now RAISES when a selector is not found, so a
   check can never "pass" by failing to read its subject.
2. The `.btn` detector read `mm.match(/className="([^"]*)"/)[1]` — the FIRST className in the file,
   which is the wrapper `<div className="moremenu">`, not the button. It could never see the
   trigger's class. It now slices the `<button>` element specifically. **A check aimed at the wrong
   element is a check that cannot fail** — same family as validating a temp copy instead of the
   mounted file.
3. And the harness itself: the first negative test asserted BEFORE restoring, so when it (correctly)
   reported MISS it left the working tree holding the broken class, and the next baseline run failed
   for a reason that had nothing to do with the code. Any harness that mutates real files must
   restore in a `finally` — the same lesson as "a negative test that mutates production-shaped state
   is an outage with a pass/fail label", one level down.

## `git archive` APPLIES autocrlf — the commit-pack fix was half a fix (2026-08-07)
`tests/test_deploy_immutability.py` failed on the operator's Windows box while passing in a Linux
sandbox, with the least useful possible message: `At index 52 diff: b'\r' != b'\n'`.
CAUSE: **`git archive` performs the same end-of-line conversion as a checkout.** With
`core.autocrlf=true` (the Windows default) it emits CRLF, while `git show HEAD:path` emits the raw
LF blob. So packing the commit made the artefact immutable but NOT platform-independent — a
Windows packer and a Linux packer would still ship different bytes, which is one of the two things
the change was supposed to guarantee. The test earned its keep on its first real run.
FIX: `git -c core.autocrlf=false -c core.eol=lf archive …`. `-c` outranks the repo and global
config, so the archive is repository bytes on every OS.
**MEASURED, NOT READ OFF THE DOCS** — and the measurement corrected me twice:
  * `-c core.eol=lf` ALONE does nothing: with autocrlf=true still set, the archive was still 562
    CRLF pairs. Only `core.autocrlf=false` suppresses it. Had I "fixed" it with `eol` alone the
    bug would have survived behind a green local run.
  * A Linux sandbox cannot reproduce this at all. The proof is a temp `git clone` with
    `core.autocrlf=true` written into ITS OWN config file (never the shared `.git`): without the
    flags 562 CRLF and != HEAD, with them 0 CRLF and == HEAD.
Also: the test now DIAGNOSES this case by name ("the pack has CRLF, HEAD has LF — pass
-c core.autocrlf=false") instead of printing a byte index. A failure message that does not name the
mechanism costs the next person the same hour it cost me.

## A z-index INSIDE a stacking context is not a z-index on the page (2026-08-07, filmed)
The operator filmed the phone: eight taps on the More button, no menu, ever. It worked perfectly
on desktop, which made it look like a touch-event problem. It was not. Measured on the live page:
    .more-p   z-index 60   trapped: true       <- sealed inside #hd
    #hd       z-index 20   position: sticky    <- sticky + z-index = a STACKING CONTEXT
    <video>   top: 123px                       <- exactly where the panel drops
`.more-p`'s 60 only ordered it against its SIBLINGS; against the page the whole header competed at
20. And Android promotes a `<video>` to a hardware overlay layer, which paints above
non-composited content regardless of paint order — so on /demo, where the video starts immediately
below the header, the panel opened UNDERNEATH it every time. On desktop the video is
`position:static` and loses to any positioned element, so the identical code was visibly fine. The
bug needed BOTH a stacking context and a composited overlay, which is why it only ever appeared on
the one page, on the one platform.
FIX: the panel renders through a **portal to `<body>`**, `position:fixed`, on its own layer — no
ancestor stacking context, no ancestor clip. Outside-click is a real `.more-bd` BACKDROP element,
not a `document` mousedown listener attached in an effect: a listener races the very gesture that
opened the menu and has to be reasoned about per platform, an element simply receives the tap.
RULE: a dropdown/popover anchored inside a sticky or transformed ancestor must be portalled. And
`z-index: 60` means nothing until you know which stacking context it is in.

## MEASURE THE ARTIFACT, NOT YOUR OWN NUMBER (the same button, same day)
I had "fixed" this button once and asserted `ratio 1.21 — a pill, not a circle`. The video shows a
circle. A 39x34 box with `border-radius:999px` IS a circle to the eye; I had invented a threshold
that let my own change pass. The label is what makes it read as a menu, so the label is now shown
at EVERY breakpoint and `header_layout.mjs` pays for it in the 360px arithmetic (worst locale: pl,
337px of 360px) instead of hiding it and calling the result a pill.
Also: three MEASUREMENT errors of mine on the way to the diagnosis, all worth remembering —
  * reading `aria-expanded` synchronously after `.click()` shows the STALE value (React batches),
    so my first two probes "proved" the button was dead when it was working;
  * `resize_window` moved the OS window, not the CSS viewport (`innerWidth` stayed 1280), so the
    "phone" run measured desktop;
  * the operator's VIDEO was the decisive evidence and I reached for it fourth instead of first.
    `ffmpeg -vf fps=2,crop=...,tile=` turns a 5-second clip into a contact sheet you can read.

## An entity in a t()/tx() string reaches the screen verbatim (2026-08-07)
The live page read "Compliance deadlines live in somebody&rsquo;s inbox." JSX parses entities in
LITERAL text (`<div>&mdash;</div>`), but a string that arrives through `t()`/`tx()` is a JS string
and React ESCAPES it. The English source string is also the KEY, so the same broken text sat in
five locale files. The new gate in `i18n_catalogue.mjs` found **20 more instances nobody had
reported** — "Swipe the map sideways to explore &rarr;" and the FRA1 hosting line, in every
language. Fixing only inside `tx("...")` arguments matters: a bare `&mdash;` in JSX literal text is
correct and a blanket replace would have broken it.

## ONE STRING, ONE KEY SPACE — the duplicated block on the landing page (2026-08-07)
The three FAQ cards rendered TWICE: once keyed (`q3.h` + `faq.1q..3a`, translated in all six
locales) and once again as by-English literals under "Fair questions". Identical content, two key
spaces — the exact disease the single dictionary exists to prevent, and every visitor could see it.
GATE: a string that is both a keyed VALUE and a by-English KEY now fails the catalogue. Scoped to
prose (>=40 chars) after the first cut flagged "Impressum" and "Open the app" — a short label
legitimately appears as a nav key AND as literal text elsewhere; that is reuse, not duplication.
A gate tuned so tightly that it cries wolf gets switched off, which is worse than not having it.

## A `finally` cannot survive SIGKILL — self-heal instead (2026-08-07)
`test_deploy_immutability` appends a marker to a REAL tracked file and restores it in a `finally`.
Two runs were killed on timeout mid-test and left `// TRANSIENT EDIT ...` sitting in Landing.jsx —
which then made the NEXT run fail for a completely unrelated reason and cost a diagnostic cycle.
Any harness that mutates real files now also `_heal()`s on import: one file read, and a killed run
can never contaminate the next one or the deploy. Same family as "a negative test that mutates
production-shaped state is an outage with a pass/fail label".
ALSO: that file called `pack()` SIX times (~5s each locally, ~40s on a network mount) on every
`python ship.py`. Module-scoped fixtures cut it to TWO, and the second pack does double duty — a
pack of HEAD taken from a DIRTY tree must equal a pack of HEAD taken from a clean one, which
proves the mid-flight-edit property and the staging==production property with one archive. A test
suite the operator waits through is a test suite that gets skipped.

## Canada — the compliance engine is JURISDICTION-KEYED, not a second code path (2026-08, RBC)
`compliance_enrich._ORDER` was a flat `["nis2","cra","aiact"]`, so Canada fell through to the
generic ISO 27001 / NIST CSF default while `build_findings_deck.js` had ALREADY been taught to pick
its framework set from `d.target.country`. One half of the product knew about jurisdictions and the
other did not.
NOW: `JURISDICTIONS` is one registry — reference document, ordered regime list, the SUBSET that gets
its own deck, prompt framing, eyebrow. `compliance.json` carries its own `order`/`decks`/`eyebrow`,
so **the deck builders contain no regime constant at all** and a new country is a registry entry
plus a reference document. Fails CLOSED to the EU set: an unknown code must never yield an empty
regime list, because a deck with no regimes looks finished.
CANADA = OSFI B-13 · E-21 · B-10 · Integrity & Security · Incident Reporting Advisory · PIPEDA ·
Quebec Law 25 · CCSPA (8 graded, 4 + roadmap rendered — a bank does not want eight single-guideline
decks). `--jurisdiction`, or inferred from `--country CA`.
**The reference's §6.4 "must never appear" list is now a BUILD GATE** (`test_compliance_ca.py`,
wired into ship.py): no OSFI fine (its tools are supervisory), no live CCSPA obligation or 72-hour
clock (Part 2 not in force, Schedule 2 empty), no $1M individual AMP (halved at committee), no
PIPEDA penalty attached to the breach itself rather than to KNOWINGLY failing to report, no
assertion that Law 25 binds a federally chartered bank. Research produced that list; a rule that
lives only in a markdown file is a rule the next edit breaks.
FOUR THINGS THE RENDER CAUGHT THAT THE TESTS DID NOT — read the artifact, always:
  * the eyebrow said **"EU DIGITAL & CYBER COMPLIANCE"** on a Canadian bank's deck, on every slide;
  * the title said **"Three regimes at a glance"** above eight rows;
  * `(p.essential).split(" of ")[0]` was written to shorten "€10m or 2% of worldwide turnover" and
    rendered Quebec's "Greater of $25,000,000 or 4%…" as the single word **"Greater"** — the number
    deleted. Strip the trailing basis phrase; never split on the first " of ";
  * **"NEAREST DEADLINE" showed the EARLIEST date**, so E-21 advertised 1 Sep 2025 (past) while the
    live 1 Sep 2026 milestone sat one row down in the same data. Prefer the next FUTURE date.
Also fixed here: the incident-reporting advisory is a STANDING 24-hour obligation, so it now carries
NO dated entry — publishing today's date in a deadline column invents a deadline.
NEGATIVE-TESTED (six mutations, all caught), and the negative test **exposed two of my own checks as
vacuous**: an OSFI-fine regex anchored on the literal "osfi" with an 80-character window never
reached the penalty field 400 characters later, and the CCSPA check read only `classification`,
which the deterministic path never sets to "Applies" anyway. Assert the PROPERTY on every member of
the set, not a symptom via regex.
BRAND LEAK CLOSED: `_colt_defaults` shipped "Colt SASE / ZTNA" and the PROMPT opened "You are a Colt
… analyst" — the DETERMINISTIC fallback and the instruction, i.e. exactly the two paths the brand
gate never rendered (it checks 6 security decks). The `colt` JSON key is a LOOKUP KEY read by
build_compliance_deck.js and is deliberately NOT renamed; only the values and the rendered label
changed. Same doctrine as the COLT->MANAGED tag.

## A CAPABILITY THE API DISCARDS IS NOT SHIPPED — the jurisdiction, found on the live screen (2026-08)
I built the Canadian regime set, the `--jurisdiction` flag, eight regimes of facts, a blocking §6.4
gate and five rendered decks. Every engine test passed. The operator then opened
cybergod.ai/app/compliance and asked where it was — because `ComplianceReq` had no `jurisdiction`
field and `/api/compliance` never passed one to the engine. **The feature was unreachable from the
product.**
This is the SAME SHAPE as the `ru` incident already in this file: the engine could render Russian
decks while main.py flattened the language to `en` at the API boundary. I wrote that rule down and
then broke it in the same way three weeks later, because I tested the engine and never walked the
request path.
NOW: `/api/jurisdictions` (public capability list, read from `compliance_enrich.JURISDICTIONS` —
never a list in the frontend), `jurisdiction` on BOTH `ComplianceReq` and `ComplianceRefineReq`
(the refine run must carry it or the child re-grades against the wrong regime set the moment the
operator answers a question), `jurisdiction_ok()` resolving through the ENGINE's registry, and a
selector on the Compliance page fed from the endpoint. The page's lede no longer names
"NIS2 / CRA / EU AI Act" in JSX — it composes the regime names from the API, because prose that
restates the selector is a second source of truth that is simply false for Canada.
GUARD: `tests/test_jurisdiction_path.py` asserts the value survives ALL THREE HOPS — engine accepts
every jurisdiction it advertises and fails closed on junk; the API model has the field AND every
`_run_job(... COMPLIANCE_ENGINE ...)` launch carries `--jurisdiction`; the frontend sends it on
start AND refine and holds no hardcoded regime list. Proven by five mutations, including the exact
defect the operator found. RULE, restated because writing it down once was not enough: **follow the
VALUE end-to-end — UI -> API -> persistence -> engine — and assert it at each hop.**

## ONE JURISDICTION, FOUR HARDCODED HOMES — and the check that could not see them (2026-08-08)
The Canadian regime set shipped, the four OSFI/PIPEDA decks built correctly, and the operator
opened `Royal_Bank_of_Canada_Compliance_Report.html` to find **NIS2, the Cyber Resilience Act and
the EU AI Act** on a Canadian bank's report. I had fixed `build_compliance_deck.js` and never
audited `build_compliance_html.js` at all.
FOUR SEPARATE HOMES, each a different code path, each needing its own fix:
  1. `build_compliance_html.js` — `["nis2","cra","aiact"]` in FOUR arrays, `REG` name map, and
     `<title>… — EU Compliance</title>`;
  2. its HERO block — a second hardcoded eyebrow and a `<div class="sub">NIS2 · CRA · EU AI Act`,
     which survived fixing the four arrays;
  3. the deck's TITLE SLIDE — `L("eyebrow")` and `["SOURCE", "EU primary law (see appendix)"]`,
     a different function from `content()`, so fixing the content eyebrow did not touch it;
  4. the roadmap cover subline, literally `"NIS2 " + MIDDOT + " CRA " + MIDDOT + " EU AI Act"`.
All four are now DATA carried by compliance.json (`order`, regime `name`, `eyebrow`,
`source_line`, `citation`), so a jurisdiction is one registry entry and no builder holds a regime
constant.
**WHY THE TEST DID NOT CATCH IT.** `test_compliance_ca.py` §6 asserted the report RENDERED and
carried no `undefined`/`NaN`/Colt — never that it named the right regimes. It is the recurring
disease in this repo: a check that cannot see the thing it checks. It now greps the RENDERED html
and the RENDERED deck text for EU regime names and fails on any of them.
**AND TWO BAD MEASUREMENTS OF MINE, in five minutes.** After the first fix I grepped the output and
declared it clean — twice wrongly: once because `| head -8` on a count-sorted list truncated the
NIS2 rows off the bottom, once because `grep -o ".\{70\}NIS2.\{70\}"` needs 70 characters of
context ON THE SAME LINE and the string sat near a line end. **For a presence check use a plain
substring, never a padded regex, and never truncate the output you are judging.** The test found
what my greps missed, which is the entire argument for having it.

## A HINT UNDER A FIELD CHANGES THAT FIELD'S HEIGHT (2026-08-08)
`/app/compliance` looked misaligned on desktop: the JURISDICTION label sat visibly higher than
COMPANY NAME and DOCUMENT LANGUAGE. Nothing was wrong with the select. `.assess-row` is
`align-items:flex-end`, so controls line up by their BOTTOM edge — and the jurisdiction field
carries a hint ("8 regimes graded · 5 decks") underneath, which made that field taller, pushed its
bottom down and its label up. FIX: on desktop the hint is `position:absolute; top:100%`, so every
field has the same intrinsic height, with `padding-bottom` on the row reserving the space once.
Mobile keeps the stacked flow, where the hint belongs in the layout — which is why the phone
screenshot looked correct while the desktop one did not.
RULE: in a `flex-end` row, anything appended BELOW a control silently moves that control up.


## /partners — long-form prose is DATA, and adding a page touches four layers (2026-08)
"Who it is for": fourteen one-page arguments (managed service providers, resellers, systems
integrators, cybersecurity vendors, consulting firms, telecoms operators, small and mid-sized
companies, large enterprises, law firms, insurers, regulators, white-label, embedded/OEM, contact),
in all six interface languages, reachable from the More menu.

**IT IS DATA, NOT MARKUP.** `Partners.jsx` holds ZERO copy; it renders an object from
`partners-locales/<lang>.js`. So the layout exists once and a translation can only change words. A
translator cannot move a box, drop a column or reorder the page, because none of those things are
in the file they edit. Same doctrine as `build_geopol_html.js` (fixed shell, text injected) and the
reason `legal-locales/` exists. `partners-locales/index.js` falls back WHOLE-ARRAY, never per index:
`sections` is an array whose order is the page order, so an index-wise merge would silently pair the
German "For resellers" with the English "For law firms" the moment one locale gained a section.
`tools/partners_gate.mjs` is what makes that safe, by proving the arrays are parallel.

**NOT in the shared string catalogue.** ~450 sentences that appear on one page would triple
`gap.*.json` and bury a genuinely missing nav label under four hundred marketing sentences. Only
CHROME goes in the shared keyed space: `nav.partners` and `prt.situation/complication/answer`.

**STRUCTURE, RESEARCHED RATHER THAN ASSERTED.** The first draft claimed "consulting-grade" with
nothing behind it, and the operator called it: *"did you really went to the internet and checked all
the consulting companies that I mentioned and made a consensus...? I do not think so right?"* He was
correct. The rebuild is on the published method: the Minto Pyramid (lead with one governing thought,
three or four grouped supports, evidence under each), Situation / Complication / Answer as the
executive-summary spine, ACTION TITLES (a heading states a conclusion, it does not name a topic),
and the "so what" test, which cut ~30% of the copy. The `.pscr` block IS that spine and the gate
fails a section that has no Answer, because a page without a governing thought is a list of features.
RULE: do not describe your own output with a quality adjective you have not checked. Look up the
method, then say which one you used.

**FOUR LAYERS, and three of them fail SILENTLY** (now `tests/test_routes.py`, blocking):
  1. `App.jsx` registers the route.
  2. `MoreMenu.jsx` is the ONLY way to reach it on a phone (`#hd nav a:not(.btn){display:none}` and
     the tab bar is full at six).
  3. `main.py::_APP_ROUTES` — omit it and `_is_probe` classifies the page as a SCANNER PROBE: 404 to
     some clients, visits logged as suppressed.
  4. `public/sitemap.xml` — omit it and Google is never told the page exists.
CLAUDE.md already said "_APP_ROUTES must list every App.jsx route (it was already stale)" and it went
stale again, because writing a rule down is not enforcing it.

**THE HEADER'S MENU CHECK WAS VACUOUS AND THIS CAUGHT IT.** `header_layout.mjs` looped over a
HARDCODED list of four routes and then printed that same literal as if it were a finding:
`console.log("  menu reaches: /experience /contact /impressum /privacy")`. Adding a fifth item
changed nothing and it still said OK. It now reads the routes App.jsx registers and the items
MoreMenu renders, asserts every public route is reachable and every menu link is a real route, and
prints what it FOUND. Nth instance of the same disease: a check that restates its own expectation
instead of reading its subject.

**THE GATE'S FIRST RUN FAILED ON THE GATE.** `partners_gate.mjs` reported a 36-word sentence that
is really two: `"…finding.** An address…"` ends the first sentence with `.**`, so a split on "full
stop then whitespace" never fires. Strip the emphasis markers before splitting — measure what the
READER sees, not what the source file looks like. Six negative tests (translated lookup key, a price
in German copy, a dropped bullet, an HTML entity, a long dash, a locale copied from English) were
each verified to FAIL the gate and the tree restored.

**CONTENT RULES, enforced in every language rather than remembered:** no prices/discounts/seat
counts anywhere (a price on a public page is a negotiating position given away for free and goes
stale the day a tier changes); no long dashes; no unexpanded abbreviation in the English source; no
sentence over 30 words; no HTML entity (React escapes a string that arrives as data, so `&rsquo;`
reaches the screen verbatim — that already shipped once from five locale files at the same time); no
named customer. A "translated" locale must also DIFFER from English on >90% of its long strings,
because a copy passes every structural check perfectly.

**`.p-main{min-width:0}` is load-bearing.** A grid item defaults to `min-width:auto`, so one long
German compound noun or a URL forces the column wider than its `1fr` track and the whole page gains
a horizontal scrollbar. German and Polish surface it first.

## LIGHT THEME — the site stopped looking like Colt (2026-08-08, approved from a study)
The palette was still `#0a1526 + #00B2A9`: Colt's. The wordmark had been rebranded months earlier
and the colours never were, so the site kept reading as the company we no longer present as.

**THE S4BIZ COLOURS WERE COUNTED, NOT SAMPLED.** Unzipped the capability brief and tallied every
`srgbClr` across every slide: `#22D3EE` cyan (77), `#8B5CF6` violet (62), `#4F46E5` indigo (41).
That is the family the site now uses. Reading a palette out of the source file takes a minute and
removes the whole argument about whether it "feels" like the deck.

**LIGHT, and the two reasons that are not taste:**
  * `/partners` is ~5,000 words. Light text on dark pushes the eye toward scotopic vision and gives
    readers with astigmatism halation (a glow around letters). Long-form reading belongs on light.
  * A phone at 300:1 indoors falls **below 2:1 in direct sunlight**. A dark page has almost no
    contrast budget left; a light one keeps most of it. Partner sellers read this outdoors.
Dark is KEPT, deliberately, for three things that are not prose: the log stream (machine output you
scan for a changing line), the architecture map (a schematic, and the one place the deck's
full-strength cyan belongs) and the login brand panel (a first impression, no reading).

**THE VARIABLE NAMES DID NOT CHANGE.** `--navy` is now the light canvas and `--teal` is cyan. There
are ~250 `var()` references; renaming them would be a 250-site edit for zero user benefit and every
chance of missing one. Same doctrine as the `COLT` remediation tag and the severity enums: a lookup
key is not a label, and the rendered colour is what the customer sees.

**ONE RULE CARRIES THE CONVERSION ARGUMENT: a solid `--cta` rectangle means "click this".**
The research is unanimous that no hue converts better in the abstract; what converts is being the
single most distinct element on screen. Share the colour with links and headings and the effect is
gone. As TEXT or inside a gradient indigo is fine (it never reads as a clickable block); as a large
FILL it is buttons only. **I broke this myself within the hour**, on a chat bubble and a progress
bar, and only the gate caught it. Those moved to violet.

**`tools/contrast_gate.mjs` (BLOCKING, in ship.py and the image build)** measures the SHIPPED
stylesheet, not a design document: 33 pairs against WCAG 2.x, the reserved-colour rule, the
old-brand-creeps-back rule, and faint white overlays. It earned its keep four times:
  1. It **rejected two of my own colours before they shipped** — `#6B7A94` muted (4.08:1) and
     `#0891B2` cyan (3.68:1), both under the 4.5:1 body minimum. Now `#5C6B85` and `#0E7490`.
  2. `rgba(255,255,255,.04)` LIGHTENS a dark surface and is INVISIBLE on a light one. 18 of them
     were in the sheet. **Alpha is the discriminator**: the gate's own first run flagged
     `#hd.s{background:rgba(255,255,255,.92)}`, which is the header's white surface and entirely
     correct. Only alpha < 0.5 is suspect.
  3. Its first reserved-colour check asked "does ANYTHING use `background:var(--cta)`" rather than
     "does **`.btn`** use it". A negative test blanked the button and the gate passed a site whose
     primary call to action was white on white. **A check has to name its subject.**
  4. Five negative tests, each verified to fail and then restored.

**TWO HARDCODED LISTS OF THE SAME FIVE COLOURS.** The architecture map's categories were written
once in the SVG builder and again in the legend beneath it. Changing the palette meant editing both
and nothing would have complained if only one was edited. Now one exported `MAP_C`.

HONEST LIMIT: I could not screenshot. Playwright's and puppeteer's browser downloads are both
blocked from the sandbox, so the visual judgement is the operator's, from
`preview/theme_light_all.html` (every public page, real component, real production CSS). Everything
I *could* verify mechanically is in the gate. Do not mistake a passing gate for "it looks good".

## `python preview.py` — see it on YOUR machine before it ships (2026-08-08)
A SECOND verb, not a second deploy command. `python ship.py` still deploys; preview.py never
touches the droplet, never builds an image, never pushes. Operating principle 7 is about there
being ONE way to deploy, and this is not a deploy.

  python preview.py            dev server, live reload, opens the browser
  python preview.py --build    build and serve the BUILT files, exactly what would ship
  python preview.py --offline  no API at all
  python preview.py --port N

**IT ALSO LISTENS ON THE LAN AND PRINTS THE PHONE ADDRESS.** The whole argument for the light
theme was a phone in daylight. Judging it on a monitor indoors tests the one condition it was not
chosen for.

**THE /api PROXY IS READ-ONLY, AND THAT IS A SAFETY RAIL NOT A NICETY.** The public pages need
real data (/api/demo, /api/langs, /api/jurisdictions), so the dev server proxies /api to the LIVE
site. The browser may still hold a live session cookie, so one click on "Run assessment" would
start a REAL job, burn Shodan credits and inference tokens and consume an evaluation account's
quota, from what the operator believes is a local colour preview. GET and HEAD pass; everything
else is refused IN vite.config.js before it leaves the machine, with a message saying why.
Proven with a stand-in upstream: GET reached it, POST and DELETE returned 405 locally.

**TWO PLATFORM TRAPS, BOTH ALREADY IN THIS FILE, BOTH HIT AGAIN:**
1. **Never `npm run dev`.** `npm run` resolves through `node_modules/.bin/vite`, a PLATFORM SHIM:
   a symlink on Linux, a `.cmd` on Windows, and absent entirely if an install was interrupted. It
   failed here with `sh: 1: vite: not found` on a machine where vite itself loaded perfectly.
   preview.py calls `node node_modules/vite/bin/vite.js` directly. One path, every platform.
2. **Detect a broken toolchain by RUNNING it, not by looking for a file.** My first version checked
   for a directory named `@esbuild/<platform>` and reported "installed for a different platform" on
   Linux, where esbuild demonstrably worked: after an install `@esbuild/` holds one TEMPORARY
   directory per platform with a random suffix, so the name I looked for is not the name there. It
   would have wiped a healthy node_modules on every run. `toolchain_runs()` now executes
   `vite --version` and reinstalls only if that actually fails.

## THE PHONE'S OWN CHROME IS NOT THE WEBSITE (2026-08-08, photographed on an Android)
The site went light and the INSTALLED APP did not. The operator's screenshot showed a light page
framed by a dark bar top and bottom. Five things were still on the old palette, and NONE of them is
in the part of styles.css a "make the site light" pass naturally touches:
  1. `.topbar` (the phone-only cabinet header)        `rgba(13,20,38,.92)`
  2. `.side` as the cabinet's bottom navigation       `rgba(13,20,38,.96)`
  3. `.tabbar` (the landing page's six-item bar)      `rgba(8,16,32,.88)`
  4. **`manifest.webmanifest` `theme_color: #0C544E`** — the previous brand's teal. This is the
     colour ANDROID PAINTS THE STATUS BAR of the installed app, and `background_color` was the dark
     splash screen, so every cold start flashed the old brand.
  5. **The icons.** `icon.svg` / `icon-maskable.svg` were `#0C544E` with a `#00B2A9` chevron: the
     tile on the home screen, the single most visible brand asset, months after the rebrand.

**THE SHAPE IS MATERIAL DESIGN 3's NAVIGATION BAR**, because that is what an Android user's eye
expects: a SURFACE-coloured bar rather than a black one, no elevation shadow, and the active
destination marked by a PILL BEHIND THE ICON in a contrasting container colour, not by a glowing
line. https://m3.material.io/components/navigation-bar/overview  A glow is a dark-theme device: it
needs darkness to read against and on white it is a grey smudge. The pill is also a bigger target
for the eye and does not depend on colour perception alone.

**ONE COLOURED SURFACE, AND IT IS THE TOP BAR.** ~56px, no reading, on screen the whole session:
that is the app's identity, so it takes the brand gradient with a cyan chevron. The BOTTOM bar
stays light because that is where every tap lands and legibility beats decoration. Buttons ON the
gradient are translucent-white pills, not `.btn.ghost` — a `--line` border vanishes into a
saturated field.

**`tools/make_icons.py` is now the one command for all seven icon files.** Two SVG sources plus
five PNGs that Android and iOS actually install. Regenerating by hand is how five of them stayed on
the old brand. The apple-touch PNGs are FLATTENED to opaque, because iOS composites alpha to BLACK
(already recorded once; regenerating is exactly when that gets forgotten).

**contrast_gate.mjs now covers the app chrome too**, and it is the part I would have missed again:
manifest `theme_color` must equal the brand and must AGREE with the `theme-color` meta in
index.html (one value, two files, guaranteed to drift); `background_color` must be the page canvas;
`apple-mobile-web-app-status-bar-style` must not be `black-translucent` (it forces WHITE status
text over a now-light bar); and the icon SVGs must carry no retired brand colour. Four negative
tests, all caught.

**A CHECK POINTED AT THE WRONG RULE, FOR THE THIRD TIME THIS SESSION.** Verifying the phone styles,
I sliced the file to `@media (max-width: 720px)` and searched it — but there is an EARLIER media
query of the same width, so the slice swept up the BASE rule `.topbar{display:none}` and reported
the gradient missing while it sat ten lines below. A selector legitimately has several rules. The
right question is "does ANY rule for this selector set this property", never "does the first one".

## THE SAME MISS, TWICE: A SELECTOR HAS MORE THAN ONE RULE (2026-08-08)
After the phone bars were fixed, the operator photographed the LANDING page: still a dark bar on
top. `#hd` has TWO rules, a desktop one and a `@media (max-width:720px)` override, and the light
conversion changed only the first. That is the identical mistake made an hour earlier on `.topbar`,
and identical to the `@media` slice that made my verification read `.topbar{display:none}`.
RULE, now enforced rather than written down: the question is **"does ANY rule for this selector set
this property"**, never "does the first one".

**THE CHECK THAT SHOULD HAVE EXISTED FIRST.** Converting a site to light is dozens of edits, and
nothing was asking the obvious question: *is any surface still dark?* `contrast_gate.mjs` now walks
every rule and fails on a literal dark background outside a named allowlist. Verified against both
real defects: reverting `#hd` or `.side` to their old navy now fails the build by selector name.
It found four more on its first run, of which two were genuine exemptions (`.phone` is a device
bezel in an illustration, `.more-bd` is the scrim behind the menu sheet) and two were the check's
own bug.

**ALPHA IS THE DISCRIMINATOR, FOR THE SECOND TIME IN ONE SESSION.** The new check flagged
`.creed`'s `rgba(79,70,229,.07)`, which is a 7% indigo wash on a light page, not a dark surface.
The white-overlay check had learned this exact lesson an hour before and I did not carry it across
when writing the new one. Anything under half opacity is a tint over what is beneath it and must
not be judged as a surface.

**PHONE CHROME IS NOW CONSISTENT:** the landing header and the cabinet top bar are both the brand
gradient on a phone, because there the header is app chrome. Desktop keeps the light glass bar: a
full-bleed saturated band across 1400px above a light hero is heavy, and there it is navigation.
Every control inside a gradient bar needs re-treating (translucent white, not `--line` borders,
which vanish into a saturated field).

**AND THE SAME BUG A FOURTH TIME, IN header_layout.mjs.** Its `block(sel)` did
`css.indexOf(sel + "{")`: a SUBSTRING match on the FIRST occurrence. When the phone header became a
gradient it gained `#hd .btn.ghost,#hd .lang-trigger,#hd .more-t{...}`, which contains the literal
`.more-t{` but NOT `.lang-trigger{` (that entry is followed by a comma), so one control was read
from the mobile rule and the other from the base rule and it reported a mismatch on a pair that
renders identically. `block()` now merges EVERY rule for the selector in source order.
Fixing it surfaced a mismatch that had been shipping all along: `.more-t` was `7px 12px` / weight
600 and `.lang-trigger` `7px 9px` / weight 700, and the old extractor could not see it because it
only ever compared the FIRST rule of each, and those two happened to agree. Both are now `7px 11px`
/ weight 700. **A check that reads one rule of a multi-rule selector is not just wrong when it
fails; it is wrong when it passes.**

## WHITE TEXT ON A WHITE PANEL — and the mirror check that was missing (2026-08-09)
Reported on both the phone and the desktop: the More menu opened and the items were invisible.
Cause, measured: `.more-p a{color:#e8eefb}` and `.lang-list button{color:#e8eefb}` were dark-theme
leftovers, while I had changed those panels' background to `var(--card)`. **1.16:1.** Not "hard to
read": gone. Three more of the same leftover were hiding in `.refused`, `.prog-notice` and
`.legal-todo`.

**THE FIX THE OPERATOR ASKED FOR IS THE RIGHT ONE.** Both floating panels now use the SAME brand
gradient as /login and the phone header, with white text. Measured, white holds across every stop:
indigo 6.29:1, violet 5.70:1, magenta 4.71:1. A floating panel is the one element that can land
over ANY background, so giving it its own opaque saturated surface is what makes it safe by
construction rather than by luck.

**THE GATE WAS BLIND BY CONSTRUCTION.** Check 5b asks "is any surface still dark". It is
structurally incapable of seeing "is any TEXT still light", which is the same defect reflected. A
palette conversion breaks in both directions and needs a check in both directions. New check 5c.

**THE QUESTION IS NOT "IS THIS TEXT LIGHT".** Plenty of light text is correct: a button label, a
coloured chip. It is *does anything give this text a dark or saturated surface* — the rule itself,
an ancestor in the selector, or a named exception. The blunt first version flagged `.btn`, `.pill`
and `.tour`, all white-on-indigo and perfectly fine.

**THREE DEFECTS IN MY OWN CHECK, each found by a negative test:**
 1. `var(--grad)` does not contain the word "gradient", and the palette map holds only HEX values,
    so the resolver defaulted the token to white and everything on the brand gradient looked light.
 2. **A blanket exemption for one question silenced a different question.** I reused `DARK_OK` (the
    white-OVERLAY allowlist, which now contains `.more-p` and `.lang-list`) for the light-text
    check, so those two selectors were skipped entirely. The negative test reintroduced the exact
    reported bug and the gate said nothing. 5c now has its own narrow list and lets `covered()`
    decide everything else.
 3. `.iam-tag` sits on the login gradient, but its ancestor is in the DOM, not in the selector
    string, so `covered()` could not see it and it had to be named.

**AND IT FOUND A REAL ONE I HAD NOT NOTICED:** `.dd .num`, the deep-dive badge, puts `color:#fff`
on a background set INLINE from `MAP_C`. Those five are deliberately bright so they read on the
dark architecture map, and white on them measures 1.67:1 to 2.72:1. Now `#0B1030`, which is 6.8:1
to 11.1:1. Same fix as the map's own badge number, which I had already corrected once.

## STANDING RULE — look at a UI change before you ship it, ENFORCED (2026-08-09)
Operator instruction: before `python ship.py`, any frontend UI/UX change is previewed locally with
`python preview.py` and LOOKED AT. Every time.

**IT IS A GATE, NOT A LINE IN THIS FILE.** This session shipped four colour defects that a
ten-second look would have caught and no automated check could: a dark bar framing a light page
(twice, `.topbar` then `#hd`), white text on a white More menu, and a badge at 1.67:1. Every gate
was green each time. A gate can measure contrast and structure; it cannot see. And this file is
already full of rules that went stale precisely because they were only written down.

`ui_preview_stamp.py` is shared by both scripts so the rule cannot drift between them:
  · `preview.py` writes `.ui-preview-stamp` = sha256 of every UI file (src/**.jsx|js|css,
    public/**, index.html) when the server starts.
  · `ship.py` recomputes it. Match -> proceed. Mismatch -> STOP, print `python preview.py`, exit 2.
  · After a verified deploy it records the shipped hash, so an unchanged UI never asks again. You
    are only stopped when there is something NEW to look at.
  · `--no-preview` overrides deliberately. A broken guard never becomes a broken deploy: any
    exception in the check is reported and the ship continues (same doctrine as the FP auditor).

**A HASH, NOT A TIMESTAMP.** "A preview happened at some point" is a different claim from "THIS
frontend was previewed" — the same distinction as `config_reread` proving startup ordering rather
than content, and the same doctrine as the engine-hash deploy verify. Scope is deliberately narrow:
a backend or engine edit must not send the operator to a browser for nothing, or the gate becomes
noise and gets switched off.

**AND THE TEST MUST NOT DISARM THE THING IT TESTED.** Verifying this, I wrote a stamp by hand to
prove the pass path works, which left a VALID stamp behind and would have let the next ship through
without a look. Deleted. Same family as the harness that left a `TRANSIENT EDIT` marker in
Landing.jsx after a timeout.

## THE PANEL, 8 Aug 2026: one point right out of four, and it was the one to act on
kimi-k2.6 voted NO-GO against a 35/35 green gate. Reviewed against the code, not the prose:

**WRONG (and the SECOND time kimi has made this exact error).** "config_drift compares `caddy adapt`
against the admin API, which are never byte-identical, so the check is broken." It does not.
`agent.py::cmd_drift` compares `d_hosts == r_hosts and d_h == r_h`: the SETS of matched hostnames
and terminal handlers, which are stable under re-serialisation. Its own output says so, printing
`(11 host(s), 9 handler(s))`. The hash comparison kimi is describing was real, was a false positive
by construction, and was REMOVED the day before. Kimi is quoting the ARCH briefing's explanation of
why the old method was wrong and attributing it to the current check. Feeding the panel more
evidence about the system's history apparently also gives it more rope.

**PARTLY RIGHT, ALREADY LABELLED.** "config_reread only proves timing." True, and the check's own
detail says exactly that and names `mount_fresh` + `config_drift` as the checks that prove content.
An honest label is not a defect.

**WRONG ON PRODUCTION.** "No check exercises the reload path; only startup." The production deploy
does `POST /load` via the admin API (`ADMIN_LOAD_OK`) and THEN runs `config_drift`, which is
precisely "did the reload take". Kimi's model of the system is missing that step.

**RIGHT, AND FIXED.** `vhost_roster` was SKIP on staging, both before and after the reboot. It was
invoked with `CADDY_EXPECT=""`, and `cmd_roster` returns SKIP on an empty list — so on the ONE box
whose entire job is to validate the committed cybergod snippet before production sees it, the check
that asks "is the domain actually served?" could never fire. gemma raised the same thing. Staging
now passes `CADDY_EXPECT="cybergod.ai"` (the single vhost its probes already send a Host header
for), and a SKIP inside the `docker ps | grep caddy` branch is now a FAILURE, because there a SKIP
cannot mean "no proxy" — it means the check could not see its subject.

**WHAT NOBODY ON THE PANEL FLAGGED, AND IT IS THE BIGGEST ITEM IN THE RUN:**
`PATCHWATCH_GATE: reboot gate MISSING on the droplet`. That is the guardrail that refuses to reboot
into an invalid proxy config, and it is not installed because `DO_API_TOKEN` is unset. It is the
*exact* 6 Aug mechanism: patchwatch upgraded the kernel and rebooted at 04:22 into a Caddyfile that
had been damaged twelve hours earlier, and every domain on the box died together. Four models read
that deploy log and none of them mentioned it. The panel reasons well about what it is shown and
does not notice what is absent — one more reason the deterministic checks decide.

## The phone More menu opens under its own button, not as a bottom sheet (2026-08-09)
Filmed by the operator: on the installed app the More panel slid up from the bottom of the screen
while the LANGUAGE menu beside it opened directly under its trigger. Two adjacent controls, two
different behaviours. `MoreMenu.jsx` passed `style={undefined}` on a phone and `.more-p.sheet`
positioned it `bottom:12px;left:12px;right:12px`.
Now anchored on every screen from the trigger's measured rect. `.sheet` keeps ONLY what was right
about the sheet treatment, the larger tap targets, and the grab handle is gone because an anchored
menu is not draggable. Still portalled and `fixed`, so the Android stacking-context bug stays fixed.
RULE: a menu belongs next to the control that opened it. Distance between cause and effect is what
made this read as a different component.

## THE PANEL, 9 Aug 2026: three of four held up, and one was a real SECURITY gap
The roster fix from the previous run worked (`vhost_roster OK all 1 expected domain(s) are served`,
before and after the reboot), which is why the panel moved on to sharper points. Reviewed against
the code, not the prose:

**RIGHT, and it is the `config_reread` disease again.** `proxy_config` printed "valid + loaded"
while `agent.py check` only VALIDATES and heals; what proves LOADED is `config_drift`. A PASS whose
wording implies more than it measured is the exact defect already fixed once in this file. The
label now says VALID + healthy and names the check that proves loading.

**RIGHT, and NEW.** "Comparing host and handler SETS is coarse: a routing change could pass."
`_served()` collected hostnames, proxy upstreams, file_server, respond and root, so a fragment
rewritten to route `/api` somewhere else kept the same hosts and the same handler TYPES and drifted
undetected. Path matchers are now part of the comparison; they are stable under re-serialisation,
so they can be compared safely. (Note this is a DIFFERENT claim from kimi's previous, wrong one
that the check hash-compares two serialisations. That one is still wrong.)

**RIGHT, NEW, AND THE BEST CATCH THE PANEL HAS PRODUCED.** *"No check verifies admin API
accessibility or its authentication."* Every drift and roster check READS
`http://127.0.0.1:2019/config/`, and the deploy WRITES through it (`POST /load`). That endpoint
replaces the running configuration for EVERY domain on the box and has no authentication of its
own: Caddy's only protection is that it binds to loopback by default. **Nothing asserted it still
did.** One `admin { listen :2019 }` in any project's fragment, or a published port, and whoever
reached it would own the shared proxy while every check in the file reported green. New
`agent.py admin` asserts both independently: what the RUNNING config binds the admin endpoint to,
and whether Docker publishes the port. Wired into stagegate (`admin_api_closed`) and the production
caddyguard run. Six cases exercised against real config shapes: default/localhost/127.0.0.1 pass,
`:2019` and `0.0.0.0:2019` fail, and a docker-published port fails.

**WRONG.** "No check sends traffic through the shared proxy from outside." Production ends with
`--- OUTSIDE VIEW ---`, five external probes against the real names. Staging has no public name by
design.

PROCESS NOTE, MINE: twice today an edit script asserted an anchor AFTER making earlier replacements
in memory and threw before writing, silently losing the earlier edits. Validate every anchor FIRST,
then edit, then write.

## The phone tab bar now lives on EVERY public page (2026-08-09, operator report)
Filmed: tapping anything in the More menu, or Demo, or even the bar's own "Open" tab, landed on a
screen with NO bottom navigation. In a standalone PWA the Android back button is not always shown,
so that was a dead end. It is the same failure the More menu was created to fix, one level up.

CAUSE: `TabBar` was rendered only by Landing.jsx, which also owned the tab list, the active state
and the click handler. The tabs are SECTIONS OF THE LANDING PAGE, so the component had no meaning
anywhere else.

FIX: `TabBar` is self-contained. It owns the tab list (`tabsFor(t)`, imported by Landing so the two
cannot drift) and behaves by route: on `/` it scrolls in place and Landing's scroll-spy lights the
tab; anywhere else it navigates to `/#<id>`. An in-page jump to a section that does not exist on
this page would silently do nothing, which is the trap SiteHeader's nav anchors already document.
Landing gained a mount effect that scrolls to `window.location.hash`, because React Router does not
do it and without it the tab appears to have done nothing.

TWO THINGS THAT ARE EASY TO MISS HERE:
  * **A fixed bar takes no space in the flow.** Every page it now appears on needed
    `padding-bottom:calc(var(--tabbar) + var(--sab) + 24px)`, or the last paragraph and the footer
    links sit underneath it and cannot be tapped. Landing already had that rule; the other seven
    pages did not. Same class as the mobile bottom bar that kept `height:100vh`.
  * **The login card is vertically centred**, so page padding would push it off centre. The
    clearance goes on `.iam-page > .iam` instead.

NOT IN THE CABINET. /app has its own bottom navigation and two docked bars would cover each other.
`tests/test_routes.py` asserts BOTH directions — every public page renders it, no cabinet page
does — and states the distinction rather than skipping /app quietly. Proven by SSR (8 public pages
x 1 bar x 6 tabs, /app none) and by two negative tests.

## THE PANEL, 9 Aug 2026 (second run): one right, one refuted for the THIRD time, and the item
## nobody has ever flagged
Gate 37/37 GO. deepseek + maverick GO, gemma UNSURE (its JSON did not parse: "Unterminated
string"), kimi UNSURE with three risks. Reviewed against the code:

**REFUTED, THIRD CONSECUTIVE RUN.** *"No check compares served hostnames/handlers against the file
at a semantic level (only hash + host count)."* `agent.py::_served()` compares SETS of hostnames,
terminal handlers AND path matchers; the "(11 hosts, 11 handlers)" is a printed summary, not the
comparison, and the byte-hash method was deleted on 7 Aug. **But this is MY defect, not kimi's.**
The ARCH briefing explained why a hash comparison is a false positive and never said what
config_drift actually DOES, so a reviewer reasoning from that map lands on the removed method every
time. ARCH now states, per check, exactly what is measured. Guarded by test_gate_integrity.py.
RULE: feeding the panel more evidence works; feeding it a map with a hole in it costs a slot every
run. If a reviewer makes the same wrong call three times, fix the briefing.

**RIGHT, AND ABOUT THE NAME.** *"config_reread's timing claim does not prove Caddy restarted vs
reloaded."* The detail string already said so, but a check's NAME is read far more often than its
detail, and a name that promises content while measuring ordering is the `config_reread` disease
one level down. Renamed **`config_write_ordering`**. A disclaimer is not a substitute for an
honest name.

**PARTLY RIGHT: certificate renewal.** The load-test half is out of scope (staging has no public
name). The cert half was real and it was the *shape* of gap this file keeps recording: caddyguard
PRINTED "60 days left" and flagged under 14, and **the exit code was unaffected and nothing off-box
looked at all**. A lapsed certificate takes EVERY domain on the shared proxy down at the same
instant, and it is the one outage that arrives on a published schedule. Now: under 7 days (or no
certificate presented) FAILS the run, and `.github/workflows/uptime.yml` checks expiry from OUTSIDE
every 10 minutes, because the box's own monitoring sits behind the proxy it monitors. Caddy renews
at 30 days, so under 10 means renewal has been failing for three weeks.

**AND THE ITEM NO PANEL HAS EVER MENTIONED, for the second run running:**
`PATCHWATCH_GATE: reboot gate MISSING on the droplet`. That is the literal 6 Aug mechanism — a
kernel reboot detonating a Caddyfile damaged twelve hours earlier — and it stayed uninstalled
across several ships because caddyguard printed *"run: python patchwatch/provision_patchwatch.py"*,
which is (a) a SECOND command and (b) hard-`die()`s without `DO_API_TOKEN`.
**The token was never needed.** It buys droplet SNAPSHOTS and a Spaces bucket; the gate is pure
code, and patchwatch's credentials live in `/etc/patchwatch/patchwatch.env`, which installing the
code never touches. So the guardrail against the exact outage this whole subsystem exists to
prevent was blocked for weeks by a dependency it does not have. caddyguard now ships the committed
`patchwatch.py` in its own existing ssh session, backs up the old copy, and VERIFIES the result
parses and contains `reboot_blocked` before keeping it — overwriting a droplet's patch automation
with a file that does not parse would silently disable unattended security updates. If patchwatch
is absent entirely it says so and installs nothing: nothing reboots the box unattended, so there is
nothing to gate.
RULE: when a guardrail reports itself missing run after run, ask what is BLOCKING it before adding
another reminder. A required credential that is not actually required is an operator step invented
by accident, and it violates operating principles 1 and 7 at once.

**MY OWN CHECK FALSE-POSITIVED ON ITS OWN COMMENT.** The new assertion "the gate must not depend on
a cloud credential" matched the comment EXPLAINING why the credential is unnecessary, and failed a
correct file. Strip comments before grepping source — the brand gate learned this months ago and I
did not carry it across. Every one of the five new assertions was negative-tested by reintroducing
its defect.

**PANEL INTEGRITY, worth watching:** gemma returned malformed JSON, so only 3 of 4 reviewers
answered. The "unanimous NO-GO halts a green gate" rule needs >=3 reviewers, so one more dropout
disarms it silently.

## CertSpotter WAS a check — it was just a name source, and it was losing recall (2026-08-09)
The operator asked why CertSpotter is not one of our assessment checks. It is: `_certspotter_domains`
has been the second CT source since the bibeltv.de incident (crt.sh returned timeout/404/503 on three
consecutive runs, and one CT source is a single point of failure). But it harvested NAMES ONLY and
discarded everything else the API returns. Two defects and one missed capability:

1. **THE RECALL BUG, confirmed from SSLMate's own documentation, not guessed.** *"If the `after`
   parameter is empty or omitted, the API will return the LEAST-recently-discovered issuances."* So
   one call plus `[:200]` returned the OLDEST 200 certificates of the estate — the exact opposite of
   what recon wants. On any domain with more than a page of history the recently-issued names, which
   are the live hosts, were never seen. Now pages with `after=<last id>`, bounded by
   `CERTSPOTTER_PAGES` (free tier is rate-limited hourly; `CERTSPOTTER_TOKEN` raises it).
2. **`issuer.caa_domains` is published by SSLMate precisely so a caller can compare an issuer
   against the domain's CAA record set** — and we already had `_caa()` from the abakus work. Both
   halves existed and had never been joined. New MEDIUM finding `cert_unauthorised`: live,
   publicly-trusted certificates whose issuer the domain's own CAA record does not authorise. The
   usual cause is not an attack, it is a certificate bought outside the process everyone believes is
   mandatory — which is a real finding, and one the customer can act on. Zero packets to the target.
3. The endpoint returns **only UNEXPIRED** issuances, so this is a view of the CURRENT certificate
   estate and nothing may be claimed from it about historic or expired certificates.

**IT FAILS CLOSED IN FIVE PLACES**, because a false accusation of mis-issuance is the worst thing
this engine could put in a customer deck: no CAA published (that is the `no_caa` finding instead) ·
CAA lookup failed (absence of evidence is never a finding) · `issuer.caa_domains` null (SSLMate does
not know, so no claim) · a SUBDOMAIN with its own CAA re-checked before any accusation, since CAA
resolves at the closest name · and a BLAST-RADIUS GUARD: if EVERY live certificate is unauthorised
the likelier explanation is the CAA record itself (`0 issue ";"` authorises nobody and is a common
misconfiguration), so it is reported as a policy conflict rather than as mass mis-issuance. Same
doctrine as the co-tenant guard and the FP auditor.

**THE BUG THAT WOULD HAVE SILENTLY DISABLED THE WHOLE SOURCE:** I called `_get_json(..., headers=)`
without reading its signature — it had none. That TypeError raises INSIDE the caller's own
`except Exception`, so the second CT source would have died on every run while printing a warning
that blamed the network. Third time this session I assumed a helper's contract instead of reading
it (`run()` returns an int, `getJSON` vs `postJSON`, now this). Guarded by test_recall.py §23, which
asserts the signature explicitly.
NEGATIVE-TESTED, and one of the negative tests was itself uninformative: removing the first
fail-closed guard changed nothing because a second guard downstream also catches it. Removing BOTH
does fail. **A negative test that passes because of defence in depth is not proof the check works —
remove every guard on the path before believing it.**

## ship.py had a SECOND home for the patchwatch gate, and it shouted over the working one (2026-08-09)
The run that installed the reboot gate successfully (`reboot gate INSTALLED and parses`) then
printed `[X] DO_API_TOKEN is required` and `the droplet can still reboot into a broken proxy
config`. Both were true statements about a stale code path: ship.py still shelled out to
`provision_patchwatch.py` whenever caddyguard reported the gate missing, and that provisioner
hard-fails without a cloud token the gate does not need. So a deploy that had just SUCCEEDED at the
thing reported that it had failed. Removed; caddyguard owns the gate and folds the verdict into its
own exit code. Two homes for one job, with the stale one louder than the working one.

## The preview stamp meant "previewed ON THIS OPERATING SYSTEM" (2026-08-09)
Investigating why the gate reported a changed frontend on a tree git called clean, the answer was
not a changed file: `ui_hash()` hashed RAW BYTES, and a Windows checkout (CRLF in the working copy,
because core.autocrlf rewrites on checkout) and a Linux checkout of the SAME COMMIT produce
different digests. So the stamp could only ever be evaluated on the machine that wrote it, and my
readings of it from the sandbox were noise I had been reporting as if they meant something.
Text extensions are now line-ending-normalised before hashing; binaries deliberately are NOT,
because a PNG can legitimately contain the bytes 0d 0a and "normalising" it corrupts the digest.
THIRD APPEARANCE OF THIS TRAP: `git archive` applying autocrlf made the deploy artefact
platform-dependent, and before that a CRLF payload broke a bash script over ssh. Content is
content; the byte that ends a line is the platform's business.
NOTE: changing the hash function invalidates the existing stamp, so the next ship asks for one
preview that was arguably already done. That is a one-off and it is the honest direction to fail.

## ns03.ru — the passive half of an active playbook, and the line we do not cross (2026-08-09)
The operator ran a hand-built recon script against a pharmaceutical target and asked for the maximum
feature set out of it, "if this is legal by EU, USA, Canada, Germany". The techniques split along a
line that matters far more than jurisdiction.

**WHAT THE LAW ACTUALLY TURNS ON IS AUTHORISATION, NOT THE COUNTRY.** With written authorisation
from the party that controls the asset, every technique in that script is lawful in all four.
Without it: Germany §202a/§202b StGB (and §303b for anything disruptive), EU Directive 2013/40/EU
("access without right"), USA CFAA §1030 (Van Buren narrowed it to gates-up-or-down; a public page
is generally fine, an authentication endpoint is a gate), Canada Criminal Code s.342.1. **And the
binding constraint is not even the law: it is that "not one packet is sent to the company being
assessed" is on /partners, in the Terms of Use, in the Article 13 notice and in the signed partner
pack, and it is the reason no customer authorisation is needed at all.** Operator decision: ship
the passive tier, BUILD the active tier but leave it OFF.

**PASSIVE, SHIPPED (zero packets — public DNS, public certificate logs, a banner already stored):**
- `email_auth.py` — SPF / DMARC / DKIM / MTA-STS. The biggest gap the engine had: a domain with no
  DMARC is forgeable without a single exposed host, and that forgery is the delivery mechanism for
  the invoice fraud the C-BIQ deck prices. ns03.ru has a correct SPF and NO DMARC at all.
  **DKIM IS PRESENCE-ONLY, BY CONTRACT**: a selector is arbitrary (`s1`, `google`, `mandrill2024`)
  and cannot be enumerated, so a key that is found is context and one that is not found is reported
  as NOT DETERMINABLE. Claiming "DKIM missing" would be a false accusation of a missing control.
- `cert_intel.py` — revoked-but-still-resolving (ns03 had two: iiko, oo), near-expiry, and
  shared-certificate blast radius (one key served the gateway + mail + autodiscover + a site
  gateway). `revoked` is NULLABLE: null means the status is UNKNOWN, never "revoked".
- `naming.py` — learn the target's own grammar from CT (`srv-<site>-<role>`, `<service>.<site>`),
  then generate from its own vocabulary. **Language follows the TARGET**, derived from ccTLD and
  estate countries, per the operator: if the company does not operate somewhere that speaks the
  language, there is no reason to spend queries asking in it. A `.ru` target earns Russian
  (`kotel`, `skud`, `energo` — in no English wordlist); a `.com` with no country evidence gets
  English only, not all seven.
- `active_probe.eol_from_banner()` + the `eol_software` detector — the highest-value item in the
  whole playbook (Exchange build -> CU -> end-of-support) delivered from a banner a scan engine
  ALREADY stored, so it costs nothing and touches nobody. **The honesty caveat is carried into the
  finding verbatim from the source engagement: OWA exposes major.minor.build only, so the finding
  names the cumulative update and NEVER a patch level.**

**ACTIVE, BUILT AND SHUT.** `active_probe.enabled()` requires `ACTIVE_PROBE=1` **AND**
`ACTIVE_PROBE_AUTH=<written authorisation reference>`. Deliberately not one boolean: a flag says
somebody wanted it, a reference says somebody is accountable, and the reference is what a court, a
customer or an insurer asks for. It is recorded in the run and printed into the artifact, so a deck
built from active data always carries the authority it was collected under.

**FOUR MEASUREMENT ERRORS OF MINE, all the same disease and all worth remembering:**
1. **A stale `.pyc` made a restored file behave like the mutated one.** After a negative test
   `cp`-restored `cert_intel.py`, Python kept loading bytecode compiled from the BROKEN version —
   on this mounted filesystem the mtime granularity is coarse enough that cache validation passed.
   I chased a phantom bug in correct code for several minutes. **Any harness that mutates a module
   must `rm -rf __pycache__` after restoring**, or the "restored" run tests yesterday's bytecode.
2. **My negative-test harness counted `FAIL` lines**, so a mutation that CRASHED the module scored
   zero failures and read as "not caught". Three results were meaningless until it distinguished
   caught / not-caught / crashed.
3. **A mutation whose anchor never matched** reported "the guard does not catch this" about a guard
   that catches it perfectly (`choices=_langs`, not `choices=deck_langs.doc_langs()`). Assert the
   replacement happened.
4. **`check(... is False or True, ...)`** — an assertion that cannot fail, in my own new test file,
   for the exact property I was most worried about.

**AND THE `expiring` RULE THAT IS BETTER THAN THE SOURCE SCRIPT.** The ns03 run read the SERVED
certificate and reported nextcloud as 31 days from expiry. CT shows a NEWER certificate already
issued for that name, running to 2026-10-03. Reporting the served one would raise an outage that
renewal has already prevented, so `expiring()` takes the LATEST certificate per name. (The gap
between "issued" and "served" is itself a finding, but proving it needs the active tier.)

`tests/test_doc_lang.py` now exempts `test_*.py` from the hardcoded-language-set scan — narrowly,
by filename prefix — because a test asserting `== ["en","de"]` is the assertion, not an offender,
and `naming.py`'s wordlist languages are a different concept from the DOCUMENT language set. Both
directions re-verified: argparse pinned back to `["en","de"]` still fails, and a literal in an
engine module still fails.

## STANDING RULE — every release, the FOUR models write the release notes and they are SENT
Operator instruction, 9 Aug 2026: *"every new release the same 4 models need to write release notes
and send it using our Gmail API gateway to feranicus@s4biz.io and also to my telegram."*

THE SAME FOUR as the staging panel — `deepseek-3.2 · llama-4-maverick · gemma-4-31B-it · kimi-k2.6`
— and for the same reason: four vendors means no shared failure domain, so a provider-wide 429
cannot silence the panel and a model that is wrong about the release is contradicted by three
others. `tests/test_release_notes.py` asserts the two lists are IDENTICAL, so they cannot drift.

WHERE IT RUNS, and why it is split in two:
  · `release_notes.py` (PC, a BUILDING BLOCK of ship.py — never a second command) gathers the
    DETERMINISTIC facts: commits and files since the previous `last-known-good` tag (the honest
    baseline is the last state that actually reached production, not the last commit somebody
    made), the staging verdict, the test result, the new safe-point tag.
  · `webapp/backend/app/release_notes.py` (INSIDE colt-web) asks the models and sends. It has to
    be there: `OPENAI_API_KEY`, the Gmail API credentials and `BOT_TOKEN` all live on the droplet
    and deliberately never enter git or the operator's PC. One ssh session, facts over stdin in
    BINARY mode (Windows text mode would rewrite every \n into \r\n).
  · **SMTP IS BLOCKED OUTBOUND ON THIS DROPLET.** Mail goes through the Gmail API in `notify.py`.
    The test greps for `smtplib` and fails, because "fixing" this to SMTP has an obvious appeal
    and would silently stop every release note.

TWO RULES IT OBEYS:
  · **THE DETERMINISTIC FACTS ARE THE NOTES.** The models add prose on top. With all four failing
    the notes still go out and are still correct, and they say `0 of 4 models` — the same doctrine
    that keeps a deck honest when enrichment dies.
  · **IT CAN NEVER FAIL A DEPLOY.** It runs LAST, after verification and after the safe-point tag,
    wrapped, returning 0 even on a delivery failure. The models sit behind a rate-limited endpoint
    and the mail gateway is a third party; neither having a bad day may turn a verified release
    into a failed one. A signal, not an authority — as with the FP auditor and the staging panel.

TWO VACUOUS CHECKS OF MINE, both caught by writing the negative test:
  1. The panel-comparison regex was `[a-z0-9.\-]+`, and `gemma-4-31B-it` has a capital B — so it
     read three models and compared the wrong set. **A model id is not lowercase by convention.**
  2. The ordering assertion was `s.index("tag_known_good()") < s.index("release_notes.py")`, but
     `def tag_known_good():` CONTAINS that substring, so it matched the definition near the top of
     the file and was true wherever the notes ran. Anchor on the CALL SITE (`_tag = tag_known_good()`).
     Nth instance of the same disease: a check aimed at the wrong subject cannot fail.

## A NEW FINDING SOURCE BROKE A TEST THAT WAS RIGHT, AND MADE THE SUITE HIT THE INTERNET (2026-08-09)
`python ship.py` refused to deploy, correctly, on one line:
```
  FAIL  no findings are invented from other companies' hosts (1)
[X] SCOPE REGRESSION - a discovered domain can own the estate again. Do not ship.
```
It was not a scope regression. The abakus §13 fixture is an estate where every host belongs to a
stranger and ZERO survive; the new ZONE-derived findings (no_caa, dmarc_weak) then fired from the
customer's OWN DNS, which is correct and is the entire point of that feature — on a target whose
whole estate is shared hosting, the zone is the only thing that is unambiguously theirs.

**THE TEST'S MEASUREMENT WAS THE PROBLEM, NOT ITS DOCTRINE.** It excluded `("no_caa",
"dns_no_service")` BY NAME, so every future zone-derived finding class had to be remembered there
or it failed a correct build. An exemption list is also the wrong shape in the other direction: it
would let a genuine HOST finding through under a newly exempted name. It now asserts the PROPERTY —
no finding may cite a stranger's address as evidence, and every surviving finding must be about the
customer's own zone. Proven by neutering `_names_the_target()` so the attribution gate keeps
everything: 3 failures, including the two named co-tenants.
RULE: when a system grows a new, legitimate source of findings, fix the test to measure the
property rather than adding the new type to an exemption list.

**AND THE DEFECT I ACTUALLY INTRODUCED: the test suite started calling the internet.** `run()` now
performs three network lookups the older tests never had to think about — CertSpotter, CAA over
DoH, and the email-authentication records. The run log shows the result: **~14 CertSpotter calls in
one `ship.py`, every one HTTP 429**, burning the free tier's hourly budget that REAL assessments
depend on, and making the suite slow and weather-dependent. A test that reaches the internet is not
testing this repository.
`_offline()` in test_scope_abakus.py and test_run_path.py stubs all three before any `run()` call;
the checks that genuinely exercise those paths inject their own fixtures (`email_auth.assess` and
the `cert_intel` functions take a lookup callable for exactly this reason).
**IT MUST BE RE-APPLIED AFTER EVERY `importlib.reload(R)`.** A reload rebuilds the module from
source and restores the real functions, silently undoing the stub — the first version patched once
at the top and the suite still made three live calls. Measured both times, not assumed.

## ns03.ru — CT told us the name EXISTS; nothing ever checked whether it RESOLVES (2026-08-09)
The delivered deck said **CRIT 0 · HIGH 0 · MED 1 · LOW 0, IPs 0** and carried a single `no_caa`
finding. The run log shows Certificate Transparency returning **11 issuances / 13 names** for the
domain — `srv-kap-gt`, `ventil.nzn`, `ventil2.nzn`, `ing.nzn`, `iiko.nzn`, `oo`, `nextcloud` — and
the operator was right that none of them reached the deck.

**ROOT CAUSE, one line of missing work.** A CT-discovered name was added to `domains` so it could
become a Shodan `hostname:` clause, and that was ALL that ever happened to it. Only the ~60-word
`_probe_subdomains` wordlist was resolved. The consequences compounded:
  · nothing from CT was pinned, so the estate was 4 addresses instead of the real host set;
  · nothing from CT reached `ident["resolved"]`, and **`cert_intel` joins every one of its findings
    against exactly that map** — so the TWO REVOKED CERTIFICATES (`iiko.nzn`, `oo`) that this
    feature was built for produced NOTHING, on the very engagement it was built from;
  · the shared-key blast radius (one certificate over gateway + mail + autodiscover + srv-kap-gt)
    was invisible for the same reason.
CT records INTENT: somebody requested a certificate for that name. Checking whether it also
RESOLVES costs one DNS query and is the whole difference between a name and a host. Measured on the
real data: **6 resolved names -> 13**, and revoked-but-live findings **0 -> 2**.

**AND THE NAMING MINER HAD BEEN SKIPPING ITSELF ON EVERY RUN.** It read `ident["domains"]` and
`ident["ct_domains"]`. The first is not populated until `merge_variants()` at the END of
resolve_identity — i.e. AFTER the miner runs — and the second **has never existed anywhere in the
codebase**. So the grammar saw one apex, found no site codes, and the `if _gram.get("sites")` guard
skipped the whole block silently. There is no `[auto] naming convention:` line anywhere in the
ns03.ru log, which is what a silent skip looks like: nothing. FOURTH time this session I assumed a
key or a signature instead of reading it (`run()` returns an int · `getJSON` vs `postJSON` ·
`_get_json` had no `headers` · now this).
RULE, restated because it keeps costing: **a feature guarded by `if <derived thing>:` fails
silently by construction.** Either log the skip, or assert the wiring in a test — §24 now does both.

Guarded by test_recall.py §24, which asserts the property AND the wiring, and was verified in both
directions: removing the CT-resolution block fails, and pointing the miner back at the dead key
fails. One assertion of mine had to be corrected in the process — I claimed the CT names reveal
addresses the wordlist never reached, and on this target they do not (the wordlist already had all
four). The gain is the NAMES, which is what makes a certificate joinable to a host at all.

## ns03.ru — the deck said the customer has NOTHING, and OT was not rated at all (2026-08-09)
With the CT names resolved the run found 3 findings instead of 1, and the two revoked certificates
finally landed. Reading the DELIVERED deck showed three more defects, two of them mine.

**1. "0 UNIQUE IPS · 0 ASNS · 0 COUNTRIES" — to a customer with 12 live hostnames on 4 addresses.**
Every one of those addresses is theirs (their own DNS resolves to it) and every name carries a
certificate they requested. What was actually zero is what SHODAN saw, because the estate is
SNI-only and filters scanners — which the operator's own playbook documents as the NORMAL outcome
on this shape of target, not an anomaly. Telling a customer they have no internet presence is false
and it is the most damaging sentence this deck can print. The engine now publishes `dns_hosts`,
`dns_addresses` and `scanner_blind`, and the deck swaps its tiles to "HOSTS FROM DNS + CT /
scanner saw none: SNI-only or filtered" when the scanner is blind.

**2. A raw enum on a customer-facing slide: "COLT: SASE/SSE with ZTNA".** The LOW/baseline table
built its ACTION cell from `rem.tag + ": " + rem.title` while every other surface goes through
`tagLabel[...]`. The rebrand renamed the LABEL and deliberately kept `COLT` as a lookup key, so any
code path that prints the key instead of the label leaks the old brand. The brand gate missed it
because its fixture has no LOW finding carrying a COLT tag — **a gate is only as good as the shapes
its fixture contains.**

**3. OT/BMS exposure was not a finding at all, and the operator is right that it is CRITICAL.**
ns03.ru published certificates for `ventil.nzn` (ventilation), `ventil2.nzn` and `ing.nzn`
(инженерные системы) at a named production branch. Those are plant systems, and the class of
incident they enable does not leak data, it STOPS PRODUCTION: Jaguar Land Rover's September 2025
compromise halted vehicle manufacturing for weeks, with the Cyber Monitoring Centre assessing
~GBP 1.9bn of UK economic damage across 5,000+ organisations and ~GBP 108m per week of lost output
at the manufacturer. New `ot_exposed` finding, CRITICAL, mapped to IEC 62443.
**IT IS EVIDENCE-BASED, NOT INFERRED.** The evidence is the customer's own DNS record plus the
certificate they requested; the finding does not claim the service is vulnerable or even confirm
what it is, and one of its three remediation items is to confirm the inventory — because a name is
strong evidence of function and is not an inventory.
**AMBIGUOUS TOKENS NEED CORROBORATION.** `ing` is Russian for building services and is also inside
marketing, hosting and a thousand surnames — on its own it is exactly the common-word anchor the
abakus incident forbade. It is admitted ONLY when it shares a site zone with a name that matched a
strong OT word. And zone membership CORROBORATES; it does not ADMIT: `iiko.nzn` (a restaurant
point-of-sale platform) sits in the same zone and is correctly left out. That last case was the one
negative test my first version did not catch, because my own fixture never asserted it.

## THE PANEL, 9 Aug 2026 (third run): one NO-GO, one wrong mechanism, two real improvements
kimi-k2.6 returned NO-GO against a 37/37 green gate. The unanimity rule did not fire (1 of 4), and
the note printed for the operator to read. Reviewed against the code:

**WRONG MECHANISM, RIGHT DOCTRINE.** *"admin_api_closed is broken: localhost inside a container is
reachable from any other container on the same Docker network namespace."* It is not — each
container has its OWN network namespace, so `localhost` inside videodead-caddy is not addressable
from colt-web, and only `network_mode: container:`/`service:` sharing would change that, which
nothing here uses. **But the constructive half stands and it is this file's own doctrine: a check
that REASONS about its subject is weaker than one that REPRODUCES it.** `cmd_admin` now actually
attempts `http://<caddy-bridge-ip>:2019/config/` from a different running container and reports
EXPOSED if it answers. Inference became measurement.

**RIGHT, AND NEW.** *"vhost_roster says 'all 1 expected domain(s) are served (2 host(s) total)' —
the extra host is unexplained. By symmetric logic, a vhost that silently APPEARS should also be a
failure."* Correct. The roster's premise is that a disappearing vhost is a failure; on a SHARED
proxy an appearing one means something is claiming traffic and certificates for a name nobody
committed. Extras are now named. Deliberately a WARNING, not a failure: launching a site is a
normal operation and a gate that fails every launch is switched off within a week.

**HALF WRONG, AND THE HALF THAT WAS RIGHT WAS THE MOST VALUABLE ITEM.** *"No check exercises the
reload path."* It does — every deploy writes, applies via `POST /load`, then runs config_drift, on
both boxes. But each run writes essentially the SAME config, so drift passing never proved a
DIFFERENT one would propagate, and that is exactly the 6 Aug mechanism: the file changed and the
process served the old bytes for twelve hours. New staging check `config_change_propagates` adds a
real vhost through the guard's own validate-then-apply path, proves it reaches the RUNNING config
without a reboot, removes it and proves it is gone. Safe here in a way it would not be on
production: the fragment is VALID (unlike the negative test that took staging down in an earlier
round), and **the revert runs before the verdict**, so a failure cannot leave staging serving it.

TWO MISTAKES OF MINE WHILE DOING IT, both the same one:
  · I wrote `docker exec "$CADDY"` into the staging script using a variable that script never
    defines. The container name is now READ the same way the check above it reads it.
  · The test asserting the admin probe searched for the literal `"docker exec"`, but `sh()` takes
    an ARGV LIST, so that string never appears — it failed a correct file. Assume the shape of the
    code and you write a check that cannot pass for the right reason.
Also fixed: `datetime.utcnow()` in the release notes, which printed a DeprecationWarning into every
release.

## The sales/partner consensus deck — and the title row is arithmetic, for the third time (2026-08-09)
`marketing/build_consensus_business_deck.py` argues the MARKET for the 4-model panel; the existing
`build_consensus_deck.py` argues the mechanism. The new file IMPORTS the old one's Deck/card/
bullets/stat helpers, so the S4biz template exists in exactly one implementation and the two decks
cannot drift.

THREE CONTENT RULES, decided with the operator and enforced in the file's own docstring:
1. **No unsubstantiated comparison against a named product.** We have never benchmarked against
   Claude, ChatGPT or Gemini. The comparison slide argues ARCHITECTURE — what follows from using
   one model rather than four — which is checkable without trusting us, plus our own catch ledger.
   An unsubstantiated superiority claim against a named competitor is comparative advertising under
   UWG §6 and the UCP Directive. The architecture argument is also strictly stronger: it cannot be
   refuted by a new model release.
2. **Every number is ours and measured, or external and cited on the slide.** Operating figures are
   read out of this repository and the live cost ledger (43 deterministic checks, 426 assertions,
   11 regression suites, 170 documented defect classes, 183 assessments at $0.0049 average AI
   cost). Market figures carry their source and are labelled ILLUSTRATIVE because they are
   benchmarks for comparable services, not our quotes.
3. **Intelligence services by MISSION, never as prospects.** Naming an agency as a target in a
   document that circulates is a problem in itself.

THE DECK SHOWS ITS OWN MISSES. Slide 6 is where the panel was WRONG (inverted a check, invented a
Kubernetes manifest that does not exist, restated the problem as diagnosis). That is not modesty:
showing the misses is what makes the catches believable, and it is the same doctrine the engine
applies to itself.

**THE DEFECT THE RENDER CAUGHT, and it is the third instance of one lesson.** Slide 11's title was
53 characters, wrapped onto a second line at 30pt Arial Black, and that line landed on top of the
sub-heading. A fixed-height title row is an ARITHMETIC problem, exactly like the site header row
that this repo has already paid for twice. `_check_title` now fails the BUILD, and it is wired by
wrapping `d.slide` so a new slide cannot forget to call it.
**THE CAP WAS SET FROM THE RENDER, NOT CHOSEN.** 49 chars is observed to fit on one line; 53 is
observed to wrap. So the limit lies in 49..52 and the cap is 50 — the lower end. My first attempt
set it to 48, the guard immediately failed a title that demonstrably fits, and the honest response
was to re-read the evidence rather than bump the number until the build went green.
RULE, restated: judge a visual by RENDERING it. `soffice --headless --convert-to pdf` plus
pdf2image gives a contact sheet of every slide in seconds, and it is the only thing that would have
caught this.

## The consensus METHOD deck — sell the algorithm, not the product (2026-08-09)
The operator corrected a misread: he does not want cybergod.ai pitched. He wants the consensus
ALGORITHM sold as a decision method engineered into a customer's own business process, with revenue
in the shape of the Uzbekistan secure-handset programme — development, integration, testing,
support. `marketing/build_consensus_method_deck.py` is that deck; it reuses the same S4biz template
helpers, so there is still exactly ONE template implementation across three decks.

**"STOP GUESSING AND STOP JUST ESTIMATING."** The operator's instruction was to go to Gartner,
McKinsey, Bain and BCG and fact-check. Every market figure on the deck is from a named, dated,
published source printed ON THE SLIDE:
  · Gartner 25 Jun 2025 — >40% of agentic AI projects cancelled by end-2027; named causes are cost,
    unclear value and INADEQUATE RISK CONTROLS; only ~130 of thousands of agentic vendors are real.
    That third cause is the whole wedge: the method IS the risk control.
  · Gartner 11 Mar 2026 — multi-agent outperformance by 2028; by 2030 half of agent failures trace
    to insufficient governance RUNTIME enforcement.
  · Gartner 17 Mar 2026 — 80%+ of governments deploying AI agents for routine decisions by 2028.
  · Gartner 19 May 2026 — worldwide AI spending $2.59tn in 2026, +47%.
  · McKinsey State of AI 2025 — 88% adoption, only ~39% reporting ANY EBIT impact, most below 5%.
  · McKinsey / BCG-Wellcome — in-silico development up to 60% trial development cost and 40% cycle
    time; up to 50% early discovery cost; 25-50% early R&D time.
  · McKinsey product-launch research — launch failure above 40%, and NO correlation between launch
    spend and success. That second half is the argument, not the first.

**THE POLYGRAPH FINDING IS THE STRONGEST SLIDE IN THE DECK, and it is a limitation, not a claim.**
The National Research Council (2003) put the median accuracy index at 0.86 but rated the evidence
quality low and concluded that at low base rates screening produces large numbers of FALSE
POSITIVES. Paired with RAND RR1408 — Analysis of Competing Hypotheses reduced confirmation bias for
people WITHOUT an intelligence background and not for those with one — it makes the case that
structure has to be enforced by the system rather than left to an experienced officer's discipline.
Citing the weakness of the incumbent instrument sells better than asserting the strength of ours.

**HONEST LIMITS ARE ON THEIR OWN SLIDE.** Every percentage is a third-party SECTOR BENCHMARK for a
class of technique, not a result we have produced and not a forecast for any engagement. Phase 4 of
the delivery model exists precisely so the number a customer relies on is measured on their OWN
historical cases. That is also the phase competitors skip, because it is the phase that can fail,
which is why it is the one that wins the deal.

## ns03.ru — the Exchange the engine could not see, and the names no certificate covers (2026-08-09)
The operator's own browser was looking at an **Outlook Web Access sign-in page on 80.246.245.158**,
served over a certificate the browser marked Not secure, while the engine reported nothing about
it. Two findings, both derivable from data the run ALREADY HELD.

**1. SELF-HOSTED EXCHANGE, CRITICAL, and the dates are the argument.** Every Exchange detector we
had read a scan-engine BANNER, and this estate has no scan-engine record at all — so the most
attacked platform in the enterprise produced silence. The passive discriminator is AUTODISCOVER: it
is an Exchange-specific service name, and an organisation on Microsoft 365 CNAMEs it into
Microsoft's platform. When it resolves to an address the customer owns, the mail platform is
on-premises and its web endpoints are internet-facing. `_is_saas_tenancy()` already existed to tell
those apart — the two halves had simply never been joined.
Severity is CRITICAL because of two published dates: Exchange Server 2016 and 2019 reached end of
support on **14 October 2025**, and the one-time Extended Security Update option ran out on
**14 April 2026**. An installation running today has NO security update available at any price.
CORROBORATION IS REQUIRED, and the negative test is what proved it matters: `mail.` and `webmail.`
are generic names every hosted provider uses, so autodiscover is the only anchor and it must be
joined by a cert SAN, a sibling name or the MX before anything is claimed. The finding states that
DNS proves EXPOSURE, not version, and one of its three remediation items is to confirm the build.

**2. LIVE NAMES NO CERTIFICATE COVERS, MEDIUM.** `vpn.ns03.ru` and `www.ns03.ru` resolve but no
unexpired certificate in CT covers them, which is exactly the browser warning in the operator's
screenshot. The second-order effect is the real finding: staff who must click through a certificate
warning to do their job will dismiss the one that matters. Wildcards are honoured (`*.x.de` covers
`vpn.x.de`) and with no CT data at all the check claims nothing.

**AND THE FIFTH TIME I ASSUMED A KEY.** The Exchange check was written against `ident["mx"]`, which
nothing in this codebase has ever set. The corroboration would have silently fallen back to its
other two paths and nobody would have noticed. `_mx()` now exists and populates it — one DoH query,
no packets. Read the data, or create it; do not reference it and hope.
Guarded by test_passive_checks.py §6, negative-tested in five directions.

## THE GATE SAID NO-GO ON A HEALTHY BOX, TWICE, AND BOTH FAULTS WERE IN THE CHECKS (2026-08-10)
A verified build was refused promotion on 4 failing checks. Production was never touched, which is
the gate working. But nothing was wrong with the system: `admin_api_closed` and
`config_change_propagates` (each counted twice, pre- and post-reboot) were both defective.

**1. A VERDICT THAT IS NOT IN A FIXED POSITION IS NOT MACHINE-READABLE.** `cmd_admin` printed a
diagnostic line — `   probed from colt-web -> 172.18.0.2:2019: no answer (isolated, measured not
assumed)` — BEFORE its verdict. The caller flattens the output and matches `case "$AD" in OK*)`, so
a CORRECT result never matched, fell through to the wildcard, and the wildcard had (correctly) been
made a FAILURE the day before. The detail string even ended in `OK admin API is loopback-only`, so
the check reported FAIL while quoting its own pass. gemma-4-31B-it named this exactly.
RULE: the verdict is the FIRST line; notes are INDENTED and come after. Indentation is what
distinguishes them, so the guard is "every line starting at column zero must be a verdict token".
That rule immediately caught a second instance: `cmd_drift` printed `[!] no caddy container` and
returned 0 — a SKIP wearing a pass's clothes.

**2. `agent.py assemble` WITHOUT `--apply` WRITES NOTHING AND RELOADS NOTHING.**
`cmd_assemble(do_apply)` only calls `apply()` when the flag is present. `config_change_propagates`
wrote a probe vhost, called plain `assemble`, then asserted the vhost had reached the running
config. It never could. So the check reported the 2026-08-07 latent-outage mechanism "reproduced
live" on a box where nothing was wrong. Fixed at BOTH call sites (the write and the revert).
kimi-k2.6 was right that the check was broken by construction, and its reasoning was the sharpest
thing in the run: `config_drift` PASSES (running == file) while this check claims the change never
reached the running config — both cannot be true. Its proposed FIX was wrong (call `caddy reload`
directly); the guard's own validate-then-apply path is what production uses, and testing anything
else would prove nothing about production. deepseek, maverick and gemma all proposed adding a
reload to the SYSTEM, i.e. they fixed the thing that was not broken.

**AND A STATIC CHECK COULD NOT CATCH DEFECT 1.** My first guard walked the AST for string literals.
The mutation that reproduces the real bug prints a FORMATTED note (`print(n)`), which is not a
literal, so the AST check skipped it and went green on a file carrying the exact defect. Replaced
with a FUNCTIONAL test: stub docker to describe a healthy box, RUN `cmd_admin`, read line 1. Same
doctrine that produced the container-to-container admin probe in the first place — a check that
reasons about its subject is weaker than one that reproduces it.
Guarded by tests/test_gate_integrity.py, all three negative-tested (note-before-verdict, bare note
returning 0, assemble without --apply).

## I REPRODUCED THE 6 AUG OUTAGE WITH THE CHECK BUILT TO DETECT IT (2026-08-10)
The previous fix made `config_change_propagates` call `agent.py assemble --apply` — correct as far
as it went, and it destroyed the staging proxy. **STAGING IS NOT FRAGMENT-MANAGED**: its Caddyfile
is composed directly by the provisioning step in stagegate.py, so `/opt/caddyguard/blocks/` held
nothing but the probe fragment. The reassembly was therefore EMPTY, `apply()` wrote it, Caddy kept
serving from memory, and the reboot detonated it:
```
post_reboot_proxy_routes   FAIL  through the proxy /api/me -> 000
post_reboot_vhost_roster   FAIL  MISSING the running proxy does not serve: cybergod.ai   serving:
post_reboot_mount_fresh    OK    container reads the current file (01ba4719c80b)
```
**`01ba4719c80b` is the sha256 of a single newline.** The file was empty and every hop-level check
happily agreed the empty file was being served faithfully. That is the exact 2026-08-07 mechanism,
caused by me, in the check written to prevent it — and CLAUDE.md already carried the rule it broke:
*a negative test that mutates production-shaped state is an outage with a pass/fail label.*

THREE FIXES, in order of blast radius:
1. **`apply()` REFUSES a config with no site blocks over a proxy that is currently serving sites.**
   This is the one that matters: it lives in `apply()`, so it protects caddyguard, the 10-minute
   watchdog and every future caller, not just the check that failed. `site_blocks()` is text-level
   on purpose — it guards the write that happens BEFORE any container, admin API or `caddy adapt`
   is consulted, so it must work with none of them available. Same doctrine as the co-tenant guard
   and the FP auditor: an automatic process may narrow, it may not wipe. `CADDYGUARD_ALLOW_EMPTY=1`
   is the deliberate, named escape.
2. **The check is non-destructive by construction.** It now READS the proxy's own bind-mount source
   (`docker inspect`, never an assumed path), snapshots the live bytes, APPENDS the probe vhost to
   the config that is actually live, applies through the guard's real validate → write →
   mount-check → reload path, then restores the snapshot and **verifies it with `cmp`**. A failed
   restore is a FAILURE, not a silent pass.
3. **An EMPTY running config is DEGENERATE, not the absence of drift.** `config_drift` compared
   `set() == set()` and reported OK on "0 host(s), 0 handler(s)" while the proxy served nothing.
   gemma-4-31B-it and kimi-k2.6 both caught this on the same run and were right: equal emptiness
   compares fine and means the box is down.

**THE PANEL, HONESTLY SCORED:** all four said NO-GO and all four were right that the system was
broken — this time it genuinely was. gemma named the mechanism exactly ("the Caddyfile is empty or
devoid of vhosts after reboot"). kimi added the sharpest structural point, that a drift check
reporting zero hosts should never pass. deepseek and maverick restated the failure without adding a
cause, which is their recurring pattern.

**AND TWO OF MY OWN CHECKS WERE WRONG IN THE SAME SESSION:**
  * The `config_drift` assertion GREPPED THE SOURCE for its message string, so a mutation that
    neutered the condition (`if False:`) left the string in place and the check went green on a
    file carrying the exact defect. Replaced with a functional test that stubs `caddy adapt` and
    the admin API and RUNS `cmd_drift`. Third time this session a static assertion could not see
    the thing it was aimed at.
  * `test_deploy_immutability`'s phantom-path assertion fired on a LibreOffice lock file that
    `git add -A` committed while a deck was open and that vanished when the app closed. The repo
    hygiene bug was real (now gitignored repo-wide — the existing rule was scoped to `docs/`, and
    my `grep -q` for it MATCHED that narrower rule and silently skipped the append). But a staged
    DELETION legitimately does not exist on disk, so the assertion now distinguishes a deletion
    from a mis-slice by asking whether the path is in HEAD.
Guarded by test_drift.py (12 assertions, the four apply() properties proven against a real
Caddyfile) and tests/test_gate_integrity.py. Negative-tested in seven directions, each verified to
fail and then restored.

## ACTIVE DEFENCE — the shield, and why the models are NOT in the request path (2026-08-10)
The operator asked for the 4-model consensus to be applied to security, "not only to report but
actively stop". THE INCIDENT that prompted it: 19:05:55-57 UTC, one IP (195.178.110.199, Andorra)
produced SIX "a person just opened cybergod.ai" alerts in two seconds while announcing SIX
different browsers — Safari/macOS, Chrome/Linux, Chrome/macOS, Edge/Windows, Firefox/Windows,
Firefox/macOS — asking for `//slug`, `/[workspace]/`, `/DOCS.md`, `/IAM.md`. The dirbruteforce rule
fired correctly and then the platform did nothing and mailed the operator six times.

**THE MODELS ARE OUT OF BAND, AND THAT IS THE DESIGN, NOT A LIMITATION.** A model call is 300ms to
60s: in front of a request that IS a denial of service, and the panel's own failure modes (429,
timeout) would become site outages. It also breaks operating principle 5, which is the product's
public claim. So: `shield.py` decides inline in pure arithmetic; `shield_panel.py` runs on a timer,
reviews what the shield DID, and proposes bounded changes. Exactly the stagegate pattern.

**WHY BLOCKING IS SAFE HERE AT ALL.** The standing rule was "detection only, because we do not
touch the firewall" — the FIREWALL was always the objection, not the blocking. Amnezia VPN (UDP),
SSH and the other four sites never pass through colt-web, so HTTP-layer enforcement inside our own
container cannot reach them. `tests/test_shield.py` greps the three modules (comments stripped —
the prose legitimately discusses the rule) and fails on any iptables/nft/ufw call.

**FIVE RAILS, each negative-tested by removing it and watching the suite fail:**
never blocks `/.well-known/` (that would turn a scanner into a CERTIFICATE outage) · never blocks
the site's own routes · fails OPEN on any internal error · every block is time-boxed and expires ·
a blast cap refuses a mass block · kill switch + allowlist · tarpit concurrency cap.

**THE STRONGEST SIGNAL IS UA ROTATION, AND IT IS UNFAKEABLE-AWAY.** An attacker varying the user
agent to defeat per-client limits produces the one thing a real visitor never produces: several
distinct browser/OS fingerprints from one address in seconds. The evasion IS the evidence. It
convicted this scanner on its second request, before any 404 threshold. It is also why the operator
got six alerts: `visitors._key()` includes the fingerprint (deliberately, so two people behind one
office NAT are two visitors), which made rotation a free way to flood him.

**THREE DEFECTS MY OWN TESTS CAUGHT, all of which would have shipped:**
1. **The blast cap made blocking arithmetically impossible.** With one scanner and one honest
   visitor, blocking the scanner is 50% of traffic, so a 20% cap could never fire — on exactly the
   traffic profile this site has. A percentage of a handful is not a rate. Fixed: a small ABSOLUTE
   number of blocks is always allowed; the percentage governs only once there are enough to be a
   pattern.
2. **The manual unblock did nothing.** It popped the timer but left the history that caused the
   block, so the next request re-scored and re-blocked instantly. Releasing somebody means
   forgiving what they did, or it is not a release.
3. **A negative test passed because of defence in depth.** The allowlist is enforced in BOTH
   observe() and decide(); deleting decide's guard still passed, because observe() had already
   refused to record anything. When two guards sit on one path, a negative test must defeat BOTH or
   it is measuring the other one. (Same lesson as the CertSpotter fail-closed test.)

**WHAT THE PANEL MAY DO** (operator's choice: "auto-tune within committed bounds"): propose values
for SIX integers, inside ranges committed in `shield.BOUNDS` and enforced by `shield.cfg()` on every
READ — so a corrupt, hand-edited or hostile tuning file still cannot leave the range. It needs a
QUORUM of 3 of 4 agreeing on the DIRECTION, and the applied value is the MEDIAN, so one bold model
cannot drag the result. Steps over 25% are refused. It cannot block or unblock an address, change
the bounds, the blast cap, the allowlist or the kill switch.

**STANDARDS**: NIST SP 800-53r5 SI-4, SI-10, SC-5, AC-7 · NIST SP 800-63B 5.2.2 · OWASP ASVS 14.6 ·
OWASP Automated Threat Handbook OAT-011/OAT-014 · MITRE ATT&CK T1595.001/.003, T1110.001.

## THE SHIELD BLOCKED OUR OWN DEPLOY VERIFIER (2026-08-10, shipped and caught in production)
The first shield release FAILED its own deploy:
```
[X] /api/me returned 404 for GPTBot - expected 401     RESULT: FAIL
https://cybergod.ai/api/me   HTTP 404      (was 401)
```
`check_bot_gate.py` sends TWELVE user agents from ONE address to prove the bot gate works. The
shield read that as UA rotation, blocked the operator's own IP, and /api/me answered 404 to
everything from it. Two defects, and the second is a design correction rather than a threshold:
1. **`/api/` was missing from NEVER_BLOCK_PREFIXES.** visitors.py has exempted it since the day it
   was written — *"every deploy verifier in this repo asserts 401 on /api/me"* — and I did not carry
   the exemption across. Authentication is the control on /api/; a 401 is already a refusal.
2. **UA ROTATION NEEDS CORROBORATION.** It proves AUTOMATION, not ATTACK. Monitoring, uptime checks
   and CI all rotate agents on legitimate paths. It now scores only when at least one other hostile
   signal is present. On the real 10 Aug incident the rotation arrived WITH four probe paths and a
   row of 404s, so nothing is lost there.
3. **A PATH WE WILL NEVER BLOCK ON MUST NOT BE SCORED ON EITHER.** `/api/me` returns 401 to every
   anonymous caller — the React app itself requests it on every logged-out page load — so counting
   that as an "authz probe" was scoring ordinary visitors.
RULE: before shipping an inline control, list the traffic THIS REPOSITORY generates against itself
(deploy verifiers, uptime workflow, the SPA's own calls) and check the control against it. I tested
the attacker and not the tooling.

## The Telegram attack console — three tiers, and the third has no button (2026-08-10)
Operator requirement: see clearly when under attack, have the models report what they are doing, be
ASKED before anything stronger, with a menu to approve.
- **AUTO** (no question): tarpit, 15-minute HTTP block, alert. Waiting for a human to approve a
  15-minute 404 means the scan finishes before the phone unlocks.
- **ASK** (one tap, expires in 2h unanswered): Hold 24h · Block /24 1h · Report abuse (AbuseIPDB) ·
  Strict 1h · Ban this path · False alarm (release + allow). A /24 is up to 256 addresses and may
  be a whole office or a mobile carrier, so the shield may HONOUR that state but never write it.
- **NEVER**: scanning or connecting back. Criminal under DE StGB §202a/§303b, EU Directive 2013/40,
  US CFAA §1030, Canada CC s.342.1; the address is usually a compromised third party; and one such
  packet ends the "not one packet" promise on /partners, in the ToU and in the signed partner pack.
  Guarded by a test that fails if an offensive-looking action is ever added.
PLUMBING: colt-web writes the pending ask to the shared `colt_events` volume and sends the keyboard;
**colt-assessbot owns the callback** because it already long-polls Telegram — a second getUpdates
consumer would steal its messages — and writes the answer back to the same volume, which both
containers already mount read-write. The bot RECORDS; colt-web ENFORCES. Authorisation and
enforcement in separate processes, so a bug in the bot cannot block anybody, and the callback is
authenticated (`AUTH.is_authed`) because a leaked chat id must not change defensive posture.
`notify.telegram()` drops Markdown when a keyboard is attached: an attacker-supplied path can
contain `_` or `*`, Telegram rejects the whole message as malformed entities, and the alert that
matters most is the one that silently never arrives.
TWO OF MY OWN CHECKS WERE AIMED AT THE WRONG SCOPE AGAIN: the callback-authentication test grepped
the WHOLE bot file, where every other handler already calls `AUTH.is_authed`, so deleting the check
from `shield_decide` alone still passed. Scope the grep to the handler.

## THE GUARDRAILS ARE TESTED FOR BEHAVIOUR *AND* FOR BEING WIRED IN (2026-08-10)
Every shield test proved shield.py BEHAVES correctly. None proved the middleware CALLS it, that the
panel is scheduled, or that a Telegram tap reaches the app. A control that is correct and
unreachable is not a control — the same disease as the ruff gate that silently skipped. Four new
blocking assertions in tests/test_shield.py, each negative-tested:
  · the middleware calls `decide()` BEFORE `await call_next(` (a blocked scanner must not reach
    application code) and `observe()` after — anchored on the CALL, because `call_next` also
    appears in the method signature and comparing against the bare name failed a correct file;
  · main.py schedules the panel as a background task AND calls `shield_console.apply_decisions`,
    without which every button on the Telegram console would silently do nothing;
  · a 42-path MASS-SCANNING CORPUS (OWASP OAT-014, CISA advisories, public honeypot feeds) is all
    recognised — 19 of them were NOT when first measured, which is how the detector list was
    written from evidence rather than memory;
  · none of OUR 21 real routes is ever treated as an attack.
`analyse_attacks.py` repeats that same corpus-vs-shield comparison against the REAL event log
(`docker exec colt-web`, read-only, one ssh), groups every source by behaviour and prints the
classes the shield does NOT yet recognise. That is the loop: measure the log, close the gap, keep
the corpus in the test so it cannot reopen.
NEGATIVE-TEST NOTE, and it cost a cycle: my first mutation "moved" the shield after the app by
inserting it just BEFORE `call_next` — still correct ordering, so the test rightly passed and I
briefly believed the check was broken. A mutation that does not actually violate the property
proves nothing about the check.

## THE REAL LOG SAID SOMETHING THE DESIGN DID NOT (2026-08-10, analyse_attacks.py first run)
156,511 requests · 2,253 sources · **604 behaved like scanners**. Classes by distinct source:
wordpress 483 · php_probe 481 · admin_panel 162 · shell_rce 113 · template 100 · env_secrets 96 ·
backup_file 45 · api_docs 28 · iot_router 6 · traversal 6. Alerts already raised: path_probe x212,
dir_bruteforce x208, authz_probe x85, ip_burst x71. Three defects, none of which theory found:

1. **`/api/` HAD BECOME A HIDING PLACE.** It is never blocked (every deploy verifier asserts 401 on
   /api/me), and `is_probe_path` returned False for everything beneath it — so `/api/wp-login.php`,
   `/api/.env` and `/api/../../etc/passwd` scored NOTHING. An attacker who prefixed every probe with
   `/api/` was invisible. FIX: `probe_shape()` (pure pattern, no exemptions) is what SCORES;
   `is_probe_path()` (shape minus the exemption) is what decides whether we may ACT. An exemption
   about ENFORCEMENT must never silently become an exemption from OBSERVATION.
2. **The single-encoded dot.** 185.177.72.56/.66/.67 each sent `/%2eenv` five times. The rule only
   matched `%2e%2e` (double). One `%2e` IS a dot, so that is `/.env` wearing a costume.
3. **A 404 COUNT ALONE WOULD HAVE BLOCKED TWO REAL PEOPLE.** 212.58.119.138 (Germany, 439 x404) and
   46.116.177.24 (Israel, 362 x404) asked only for OUR OWN routes — /api/me, /, /app, /api/demo,
   /media/cassandra.mp4. They are visitors. VARIETY is the discriminator: a person misses the same
   few stale paths, a scanner misses hundreds of DIFFERENT ones. A 404 now scores only once an
   address has missed on >= NF_DISTINCT (6) DISTINCT paths inside the window.

**AND MY OWN DIAGNOSTIC WAS THE THING THAT COST A CYCLE.** The coverage report said
`php_probe 235 path(s)` and nothing more, so I assumed the `.php` detector was broken — it was not;
every `.php` path tested True. The real cause was defect 1, and the report could not show it because
it never NAMED a path. It now prints five examples per class. A diagnostic that does not name its
subject sends the next investigation down the wrong road — the same rule already recorded for the
co-tenant guard's arithmetic and the mis-sliced dirty path.
RULE: build the detector from ONE incident, then MEASURE against the whole log before believing it.
Guarded by tests/test_shield.py, negative-tested in both directions (the hiding place, and the
404-only false positive).

## STANDING RULE — public-facing copy must not read as AI-written (operator, 2026-08-10)
The instruction, verbatim: *"never put this shit in the posts — and always fact check and make posts
as human as possible remove all stuff that will for sure pin point it as AI"*.

**BANNED OUTRIGHT: the em dash (—).** It is the single clearest tell, and the operator has now said
so twice: `partners_gate.mjs` already fails the build on "no long dashes" for /partners. The rule is
now global for every post, caption, LinkedIn draft and piece of marketing copy. Use a comma, a full
stop, brackets, or restructure the sentence. Never an em dash, never an en dash used as punctuation.

THE OTHER TELLS, which matter as much and are harder to see:
  · **"It's not X, it's Y"** and its cousins ("Not a breach. Just the internet doing what the
    internet does"). Perfectly balanced antithesis is the most recognisable AI cadence there is.
  · **Rule of three everywhere.** Three items, three clauses, three sentences per paragraph. Real
    writing is lumpy: two here, five there, one on its own.
  · **Uniform sentence length.** Vary it hard. A four-word sentence next to a forty-word one.
  · **A neat aphorism as the closing line.** "Measure your own traffic this week. You will not enjoy
    it, and you will be better for it." Nobody talks like that. Stop the post when the point is made.
  · **Systematic emoji placement** (one per bullet, one per section header). Use two or three, where
    a person would actually put them, or none.
  · **Signposting**: "Here's the thing", "The uncomfortable part", "But here's what matters".
  · Vocabulary: delve, leverage, robust, seamless, landscape, testament, underscore, pivotal.
  · **Bullet symmetry.** If every bullet is the same length and grammatical shape, a human did not
    write them.
FACT CHECK IS NOT OPTIONAL: every number in a post is traced to the measurement that produced it
before the post is written, and the post must not claim more than the measurement supports. The
live-fire post says 604 scanners were DETECTED, never "stopped", because the shield shipped after
the log was written. On a security post an unsupported number is self-refuting.

## The run log became a DELIVERABLE, and the raw one can never be it (2026-08-11)
Operator asked for the full per-company run log in History, downloadable by the assessed company.
Good idea: the log is a methodology receipt. It shows the timings, what was found, and every place
the engine REFUSED to conclude ("does NOT corroborate", "ASNs unknown, NOT 'none'", "absence of
evidence is never a finding", "NO ATTRIBUTABLE ESTATE ... that is a finding, not a failure"), plus
which model wrote the prose and which DIFFERENT-VENDOR model audited it. That is the strongest
trust artifact in the product and it costs nothing to produce.
THE RAW LOG CANNOT BE HANDED OVER. It carries the operator's email on every structured line,
internal paths naming him and the job id, and `cost_snapshot` — which on the sberautotech run read
193 assessments, $0.95 lifetime, $0.0049 average. Giving the assessed company the exact AI cost of
the report they are invoiced for, plus the size of the whole book, is not a privacy leak. It is a
negotiating position given away for free.
`scripts/run_log.py` builds the customer copy. **TWO LAYERS, AND THE ALLOW-LIST IS THE PRIMARY
ONE**: only recognised events and line shapes are rendered, with named keys only; the regex
redaction is a backstop. Its own negative tests proved the split — deleting the email regex or
un-dropping cost_snapshot changes nothing (neither ever reaches the renderer), while removing the
allow-list leaks instantly. The line to protect is the final `continue`.
DELIVERY: written by `main._run_job` after the engine exits, because the engine's stdout IS
run.log and it cannot read the file it is still writing. `_collect_decks` globs `*_Run_Log_*.txt`;
the download endpoint allows `.txt` ONLY when the name carries `_run_log_`, so `run.log` itself is
never reachable. Served text/plain inline. A failure to build it can never fail a completed
assessment.
Guarded by tests/test_run_log.py against the REAL sberautotech.ru run.

## THE BUTTON WORKED AND THE CONFIRMATION WAS SIX HOURS AWAY (2026-08-11)
The Telegram attack console shipped and fired for real: `UNDER ATTACK 136.67.108.237, probe_path,
/.vite/manifest.json, /api/graphql, /dist/.vite/manifest.json, /graphql`, tarpitted then blocked
15 minutes automatically, six buttons offered. The operator asked the right question: *"I need
confirmation from bot or 4llms when I press the button then it's indeed propagated to the system."*
He could not have known it, but there was no such confirmation on any useful timescale.
CAUSE: `apply_decisions()` was called INSIDE the six-hourly panel loop
(`SHIELD_REVIEW_EVERY_S=21600`). So a tap was recorded, the bot replied "Applying.", and nothing
happened until the next panel pass. **Applying a decision is a small file read; deliberating with
four models is expensive. They do not belong on the same clock.** Split into `_decisions_loop`
(20s, no model calls) and `_panel_loop` (6h, unchanged).
FOUR PROPERTIES, each negative-tested:
1. **THE CONFIRMATION IS READ BACK OUT OF SHIELD STATE AFTER THE WRITE.** The first version
   printed "Applied: holding 1.2.3.4 for 24h", which is the same sentence whether or not anything
   happened. Now each line re-reads the actual expiry, the actual block-list size, the actual
   strict deadline; a disagreement is reported instead.
2. **ABSOLUTE UTC, NOT A COUNTDOWN.** "Expires in 23h 59m" is arithmetic the operator cannot check
   against anything. "until 21:01 UTC" is something he can hold the system to tomorrow.
3. **A FAILED ACTION IS REPORTED.** Silence after a tap is indistinguishable from success, and the
   whole value of this console is that its statements can be trusted. `NOT APPLIED` lines carry the
   reason (`2001:db8::1: not an IPv4 address, cannot widen to a /24`).
4. **THE BOT NO LONGER PROMISES WHAT IT CANNOT VERIFY.** The bot RECORDS and colt-web ENFORCES, in
   separate processes deliberately, so "Applying." was a claim the bot had no way to check. It now
   says the platform confirms within ~20s and that **no confirmation means colt-web is not
   running** — which makes SILENCE INTERPRETABLE instead of ambiguous.
AND THE DEEPEST VERSION OF THE OPERATOR'S QUESTION: a button that writes a name `decide()` never
consults is a lie with a confirmation attached. Asserted by AST that all five globals the six
actions write (`_blocked`, `BLOCK_NETS`, `STRICT_UNTIL`, `EXTRA_PROBE_PATHS`, `ALLOW_IPS`) are read
on the request path. My first attempt at that measurement used a 2600-character window per function
and gave a FALSE PASS by overlapping into the next function; `ast` gives the real answer. Nth
instance of a check aimed at the wrong subject.
TWO INVENTED NAMES IN ONE CHANGE (`_ev`, then `_src` in the test file) — the sixth and seventh time
in this workstream I have referenced a helper without reading it. `notify._log` is the real event
logger and every other event in that module already went through it.

## THE OUTSIDE VIEW COULD NOT SEE THE SITE, AND THE OFF-BOX MONITOR ACCEPTED A 404 (2026-08-11)
Reviewing the previous ship's log. The panel's four models produced one genuinely useful point
between them; the worst defect in the run was in a line all four read past:
```
--- OUTSIDE VIEW ---
   https://www.cybergod.ai/     HTTP 404
5/5 endpoints answering.
```
CAUSE: `recover.probe()` sent `User-Agent: cybergod-recover/1.0`, and colt-web's BOT_404 gate
serves an unrecognised agent a 404 on every PAGE route. So the external check was measuring the
BOT GATE, not the site, and counting the 404 as an answer. The only cybergod line that ever
passed honestly was `/api/me`, and only because `/api/` is EXEMPT from the gate. **Our external
monitoring had never once verified that the pages work.**
FAR WORSE, in `.github/workflows/uptime.yml`: the same bare-curl blind spot, and `404` had been
added to the ACCEPTED status set for www.cybergod.ai to stop it complaining. Widening an
expectation to match a broken probe is how a monitor comes to accept an outage — and this is the
ONE monitor that runs off-box, precisely because everything on the droplet sits behind the proxy
it is watching. A completely dead front page would have been reported healthy.
FIX: both probes announce a browser (first-party monitoring of our own site is exactly the case
the gate is not for; `check_bot_gate.py` remains the thing that tests the gate, by sending twelve
agents deliberately). `404` removed from every accepted set, and `https://cybergod.ai/` added as
its own target — `/api/me` proves the backend and auth, and can pass while every human-facing
page is broken.
Guarded by `tests/test_outside_view.py`, five negative tests, all caught.

THE PANEL, 11 Aug 2026 (39/39 GO, kimi NO-GO):
- **RIGHT, and cheap.** `post_reboot_config_change_propagates` said "without a reboot" while
  carrying a `post_reboot_` prefix, so the detail read as contradicting its own execution
  context. The claim is about the MECHANISM, not about when the check ran. Reworded.
- **RIGHT ABOUT THE SYMPTOM, WRONG ABOUT THE CAUSE, and worth acting on anyway.** It flagged the
  artifact being 39084b pre-reboot and 39329b post-reboot as possible drift or a race. The cause
  is benign and knowable: the GEOPOL page's prose is written by a MODEL, so two runs of identical
  code produce different words. But **a number that legitimately varies must not be printed as if
  it were a signature** — it cost a review slot and would cost a human ten minutes. `engine_runs`
  now reports the canvas count and the leak check (and asserts >=5 canvases, which is what a
  hollow shell looks like) and says outright that the size varies by design.
- **WRONG, and it is the same wrong call for the fourth run running.** "The check claims restored
  byte-for-byte, but adapt and the admin API are never byte-identical." The restore comparison is
  `cmp -s` between the FILE snapshot and the restored FILE. Kimi keeps reaching for the ARCH
  briefing's explanation of the removed hash method and attaching it to whichever check is
  nearest.
- **MOSTLY ALREADY COVERED.** "admin_api_closed only probes from colt-web and nothing checks the
  Caddyfile does not publish 2019." `cmd_admin` reads what the RUNNING config binds admin to and
  whether Docker publishes the port, and the probe from colt-web is a real cross-container test.
- **OUT OF SCOPE.** TLS/SNI on staging: staging has no public name. Production checks expiry.
ALSO CLOSED: the roster warning ("4 host(s) served that are NOT on the committed roster:
jev.best, klimaanlage-montieren.de, www.*") had fired benignly on several consecutive ships.
Both are the operator's own sites, so they are now committed. **A warning that is benign every
single time is training to ignore the one that is not**, which defeats the roster's entire purpose.
AND MY OWN CHECK FALSE-POSITIVED ON MY OWN COMMENT — the assertion that the retired user agent is
gone matched the comment EXPLAINING that it was removed, and failed a correct file. The brand gate
learned to strip comments before grepping months ago and I did not carry it across. Second defect
in the same file: the expectation regexes contain `|`, so `line.split("|")` unpacked into too many
values and the check crashed instead of measuring.

## WE WERE TRUNCATING THE REVIEWER AND CALLING IT AN ERRATIC MODEL (2026-08-11)
The run was clean, and the line worth acting on was in the deterministic output, not the panel:
```
  REVIEW PANEL (3 of 4 answered):
    [auditor] gemma-4-31B-it     UNSURE
          . did not answer: Unterminated string starting at: line 1 column 2 (char 1)
```
"Unterminated string" is JSON cut mid-string, which is OUR `max_tokens` ceiling — the identical
lesson already recorded for enrich.py ("a `finish_reason == length` is OUR ceiling truncating the
JSON, not a model fault"). `quorum._ask` asked for **900 tokens** while the panel's own contract
permits 3 reasons + 3 risks at 400 chars each plus two 500-char fields = **~1020 tokens of content
before any JSON structure**. So a reviewer that answered FULLY was guaranteed to be cut off, and
the failure was then reported as "did not answer", which is how gemma acquired a reputation for
being erratic across two reviews. Raised to 1800, and a truncated answer now says whose fault it is.
**AND THE SAFEGUARD COULD SILENTLY SWITCH ITSELF OFF.** The rule that HALTS a green gate on a
unanimous NO-GO requires `len(revs) >= 3`. gemma has now dropped out twice, so the panel is one
dropout from that protection being disarmed with nothing said. `quorum` now prints
`!! PANEL BELOW QUORUM: N of 4 answered ... it CANNOT FIRE this run`, naming the non-answers, and a
test asserts the warning threshold still matches the quorum the rule actually uses.
RULE: a safeguard that cannot fire must announce it. Silence is indistinguishable from "it passed".

## TWO WARNINGS THAT WERE BENIGN EVERY SINGLE RUN (2026-08-11)
Both trained the operator to read past a warning line, which is exactly how a real one gets missed:
- `[!] 8/10 bots blocked — the rest may be in BOT_404_ALLOW`. Googlebot and Bingbot are allowed
  BY DESIGN (404-ing Googlebot is what kept a stale pre-rebrand snippet in Google's index for
  months). 8/10 is the CORRECT state. It now warns only when a bot OUTSIDE the deliberate
  allow-list gets through.
- `[!] 4 host(s) NOT on the committed roster: jev.best, klimaanlage-montieren.de, www.*` — both
  the operator's own sites, now committed.

## A CHECK THAT PRINTS "SKIPPING" ON EVERY RUN HAS NEVER RUN (2026-08-11)
`[model-watch] catalog unavailable (no OPENAI_API_KEY) - skipping` has appeared on every single
deploy since the check was written. The key lives on the DROPLET and never on the operator's PC,
so the NEW/DISAPPEARED-model diff that model_watch exists to produce **has never once been
computed** — the same disease as the ruff gate that silently skipped for weeks and the esbuild
path that was "missing" on a machine where esbuild worked. `model_probe.py` had ALREADY solved
this by running inside colt-web; ship.py now falls back to the same place instead of printing an
excuse. Non-blocking by design: a new model is information, not a broken build.

MY OWN CHECKS, THREE DEFECTS IN ONE CHANGE, all found by the negative tests:
1. `sshout()` does not exist in ship.py — the EIGHTH invented name in this workstream. The helper
   is `ssh()`, and it returns its output. Read the signature; do not assume it.
2. The model_watch assertion sliced around the FIRST occurrence of the filename, which is a
   COMMENT about it, and failed a correct file. Anchor on the CALL SITE.
3. The bot-gate assertion measured the warning's MESSAGE while the defect lives in its CONDITION,
   so a mutation restoring the unconditional comparison passed. **A check aimed at a string when
   the bug is in the logic cannot fail for the right reason.**

## THE PANEL, 11 Aug 2026 (second run): one right, one refuted for the THIRD time, and the item
## nobody has ever flagged
Gate 39/39 GO. deepseek + maverick GO, gemma UNSURE (its JSON did not parse: "Unterminated
string"), kimi UNSURE with three risks. Reviewed against the code:

**REFUTED, THIRD CONSECUTIVE RUN.** *"No check compares served hostnames/handlers against the file
at a semantic level (only hash + host count)."* `agent.py::_served()` compares SETS of hostnames,
terminal handlers AND path matchers; the "(11 hosts, 11 handlers)" is a printed summary, not the
comparison, and the byte-hash method was deleted on 7 Aug. **But this is MY defect, not kimi's.**
The ARCH briefing explained why a hash comparison is a false positive and never said what
config_drift actually DOES, so a reviewer reasoning from that map lands on the removed method every
time. ARCH now states, per check, exactly what is measured. Guarded by test_gate_integrity.py.
RULE: feeding the panel more evidence works; feeding it a map with a hole in it costs a slot every
run. If a reviewer makes the same wrong call three times, fix the briefing.

**RIGHT, AND ABOUT THE NAME.** *"config_reread's timing claim does not prove Caddy restarted vs
reloaded."* The detail string already said so, but a check's NAME is read far more often than its
detail, and a name that promises content while measuring ordering is the `config_reread` disease
one level down. Renamed **`config_write_ordering`**. A disclaimer is not a substitute for an
honest name.

**PARTLY RIGHT: certificate renewal.** The load-test half is out of scope (staging has no public
name). The cert half was real and it was the *shape* of gap this file keeps recording: caddyguard
PRINTED "60 days left" and flagged under 14, and **the exit code was unaffected and nothing off-box
looked at all**. A lapsed certificate takes EVERY domain on the shared proxy down at the same
instant, and it is the one outage that arrives on a published schedule. Now: under 7 days (or no
certificate presented) FAILS the run, and `.github/workflows/uptime.yml` checks expiry from OUTSIDE
every 10 minutes, because the box's own monitoring sits behind the proxy it monitors. Caddy renews
at 30 days, so under 10 means renewal has been failing for three weeks.

**AND THE ITEM NO PANEL HAS EVER MENTIONED, for the second run running:**
`PATCHWATCH_GATE: reboot gate MISSING on the droplet`. That is the literal 6 Aug mechanism — a
kernel reboot detonating a Caddyfile damaged twelve hours earlier — and it stayed uninstalled
across several ships because caddyguard printed *"run: python patchwatch/provision_patchwatch.py"*,
which is (a) a SECOND command and (b) hard-`die()`s without `DO_API_TOKEN`.
**The token was never needed.** It buys droplet SNAPSHOTS and a Spaces bucket; the gate is pure
code, and patchwatch's credentials live in `/etc/patchwatch/patchwatch.env`, which installing the
code never touches. So the guardrail against the exact outage this whole subsystem exists to
prevent was blocked for weeks by a dependency it does not have.

## A DETAIL STRING THAT TEACHES THE OUTAGE IS A DEFECT (2026-08-11)
kimi returned NO-GO against a 39/39 gate on `config_change_propagates`, arguing the check "claims
reload-free propagation works" while Caddy reads its config only at start or on an explicit reload,
and that this "trains operators to believe file edits auto-propagate".
**Wrong about the mechanism: right about the wording, and the wording is mine.** The check goes
through `agent.apply()` — the guard's real validate -> write -> mount-check -> EXPLICIT reload path
— so the implementation was never reload-free. But the detail I wrote the day before said
*"a config change propagated to the running config with no restart"*, and that sentence, read on
its own in a deploy log, says a bare file edit is enough. **That belief IS the 2026-08-07 outage**:
a config edited at 16:15 and silently unapplied until a kernel reboot detonated it twelve hours
later. Same defect class as `config_reread` promising more than it measured, one level down.
The detail now names the mechanism and states outright that a bare file edit does NOT propagate.
Guarded by a test that fails if any pass branch claims propagation without saying how.
AND THE WRONG-SUBJECT DEFECT, THIRD TIME IN TWO DAYS: there are THREE `chk config_change_propagates
yes` branches and my first test grabbed `[0]`, which is the "no caddy on this box" case, failing a
correct file. It now selects every branch that actually makes the propagation claim and asserts the
property on all of them.

## CONSISTENCY IS NOT AUTHENTICITY — the config was never checked against the REPO (2026-08-11)
Raised by kimi-k2.6 on a 39/39 GO run, and it is the best structural point the panel has produced
since the admin-API one: *"No check validates that the Caddyfile on disk matches the repo. An
attacker with host access could edit the file and mount_fresh + config_drift would BOTH pass,
showing the running config matches the attacked file."*
Correct, and caddyguard made it worse BY DESIGN: `migrate` re-splits whatever is LIVE into
fragments, so a hand-edit is captured as a fragment and `assemble` writes it straight back — the
edit survives every ship. Only the jhw block was ever compared to its committed counterpart, and
`deploy/caddy/cybergod.caddy` is committed too and was never checked.
FIX: every fragment with a committed block is now compared to it, the difference is printed by
NAME with a diff, and the committed block is reinstalled. This is the only check on the box that
asks *"is this OUR config"* rather than *"do the three hops agree with each other"*.
RULE: hop checks prove CONSISTENCY. Nothing about them proves the file is the one we wrote.
Guarded by test_gate_integrity.py, which derives the list from `deploy/caddy/*.caddy` so a NEW
committed block cannot be added without a comparison (it fails with "add it to the map").

MY OWN CHECK MATCHED A COMMENT, FOR THE THIRD TIME IN THREE DAYS. The `TAMPER` assertion passed
against a mutation that removed the word from the line the operator SEES, because "TAMPER CHECK —
CONSISTENCY IS NOT AUTHENTICITY" is a bash comment inside the shipped script. Strip comments, then
assert on what is echoed. The brand gate learned this months ago; recover.py relearned it on
Monday; this is the third instance.
Also: my first render assertion was `"%s" not in script.replace("%%","")`, which is naive — the
RENDERED script legitimately contains 11 `%s` from bash `printf '%-12s %s'` and `date +%s`. It
failed a correct file until I looked at what it had actually matched.

## THE RUN THAT CONFIRMED THREE DIAGNOSES (2026-08-11, f12e270)
- `[model-watch] first run - recording the baseline, nothing to diff` — printed the FIRST time the
  check has ever executed, which is the proof that "catalog unavailable - skipping" on every
  previous deploy meant exactly what it said.
- `www.cybergod.ai HTTP 200` (was 404 on every run) and `all 10 expected domain(s) are served`
  (was a 4-host warning) — the monitoring and roster fixes landed.
- `bots blocked: 8/10` with NO warning line — the intended allow-list is now respected.
- `[!] working tree is DIRTY ... packing the COMMIT f12e270, not your working copy` — the
  immutability guard behaving exactly as designed, and saying so.

## A BLACK RECTANGLE THAT PARSED, BUILT AND SHIPPED (2026-08-11, defense.html)
The operator opened the page and got a black screen with **3,637 console errors**, all identical:
```
Uncaught SyntaxError: Failed to execute 'addColorStop' on 'CanvasGradient':
The value provided ('rgba(FF3B57') could not be parsed as a color.   at glow -> roster -> frame
```
CAUSE, and it is entirely mine: a half-written line left in `roster()` -
`glow(232,L.y,30,L.c.replace(")",",.9)").replace("#","rgba(")||L.c,.0); /* no-op guard */`
`"#FF3B57"` contains no `)`, so the first replace does nothing and the second yields
**`rgba(FF3B57`**. It threw on the FIRST call of the FIRST frame, so the render loop died before
anything was drawn. `hexa()`, the correct helper, sits two lines below it.
**WHY EVERY CHECK I RAN SAID FINE.** `node --check` only PARSES - an invalid value is legal
JavaScript until it executes. The offline composition render redraws the maths in PIL and never
executes the page's own JavaScript, so it happily produced a beautiful picture of a page that
could not run. CLAUDE.md ALREADY carried the rule from the `/app` white-screen incident - *"a
passing vite build does NOT mean the page works ... an undefined identifier is legal JS until it
executes"* - and I checked syntax instead of running the thing.
FIX: `webapp/frontend/tools/canvas_smoke.mjs` EXECUTES the real render loop for 900 frames (the
whole 41s timeline, every act) against a stub 2D context that validates every colour reaching
`fillStyle`/`strokeStyle`/`shadowColor`/`addColorStop` and fails on any exception. Wired into
ship.py AND into `webapp/Dockerfile`'s fe stage, so it also runs on the toolchain that is correct
by construction. Proven by reintroducing the operator's exact bug (caught, by name), a typo'd
helper (caught) and an undefined colour (caught).
RULE: for anything that draws, PARSE is not RUN and a static render of the same maths is not the
page. Execute the loop.

## THE PUBLIC SIEGE FEED — redaction is the precondition, not a feature (2026-08-11)
`/defense.html` now plays REAL requests. `webapp/backend/app/siege.py` is an in-memory ring buffer
fed by the telemetry middleware at the SAME point the shield observes, so the feed and the detector
can never disagree about what an attack is; the page polls `GET /api/siege?since=<seq>` every 2.5s.
Near-real-time with no log parsing and no disk I/O.
**THE ENDPOINT IS WORLD-READABLE AND THE STREAM CARRIES ORDINARY VISITORS, so four rules are
enforced in code, each negative-tested:**
1. **An IP address is PERSONAL DATA** (GDPR; CJEU C-582/14 Breyer) and "they attacked us" is not a
   lawful basis for publishing it. Truncated to a /24 (IPv4) or /48 (IPv6) **on the way IN**, so a
   later bug in the endpoint cannot leak what was never stored.
2. **Only attack-shaped requests are recorded at all.** A human reading the site never appears,
   not even anonymised.
3. **A raw path is an exfiltration vector** — the attacker controls it and it can carry an email,
   a token or a session id in a query string. Echoed ONLY when it matches a strict shape with no
   query; otherwise the class name is shown and the path is discarded.
4. **No user, no session, no referrer, no user agent.** A UA is attacker-controlled free text.
Bounded buffer + cached snapshot, because a public endpoint that recomputes is a lever for making
our own server work - an unusually embarrassing way to be taken down given what the page is about.
**HONESTY IN THE ANIMATION.** A live shot is NOT drawn as "blocked" unless `shield.is_blocked()`
says the source is actually held. The shield blocks a SOURCE after it scores; a first probe from a
new address is DETECTED and answered. Drawing both as interceptions would be the same overclaim as
saying the 604 were "stopped".
**ONE CLASS VOCABULARY.** The table lived only in `analyse_attacks.py`, which is a repo-root ops
script NOT copied into the image - so the feed could not name a lane without a second copy, and a
second copy is how ENRICH_MODELS ended up with four homes. `CLASSES` + `classify()` + `lane_of()`
moved into `shield.py`; analyse_attacks.py imports them. This does NOT make the gap analysis
circular: that compares this CORPUS against `probe_shape()`, a separate regex.
MY OWN ERRORS, ALL CAUGHT BY WRITING THE CHECKS: `shield.is_blocked()` did not exist and my first
wiring inferred it from `status == 404` - which the BOT GATE also returns, so ordinary crawler
traffic would have been coloured as blocks. And `probe_shape()` returns a BOOLEAN, not a class
name (ninth assumed signature in this workstream), so every event would have landed in one lane.
NEGATIVE-TEST NOTE: the query-string guard is doubled (explicit `?` check + the `_SAFE_PATH`
character class). Removing either alone leaves the other holding and the mutation looks green -
defeat BOTH before believing it.

## THE TRIVY -> LiteLLM CHAIN, AND THE 432-CVE WEEK (2026-08-13)
Two stories the operator sent, and they are really one story about cadence and dependencies.

**WE WERE NOT AFFECTED BY EITHER, and the evidence is dates, not optimism:**
  · Aqua's **Trivy** was compromised late Feb 2026 (disclosed 1 Mar; the rotation was NOT atomic so
    a still-valid token took the newly rotated secrets; a second wave ~16-21 Mar pushed a malicious
    **v0.69.4** to GHCR, ECR Public and Docker Hub, force-pushed **76 of 77 trivy-action tags** and
    every setup-trivy tag, with a payload that dumped **Runner.Worker process memory**).
  · **LiteLLM was compromised BECAUSE its CI installed the poisoned Trivy automatically** — 2,500+
    organisations and 434,000 pipelines, "one unrevoked token, three tools deep" (CloudSEK).
  · This repository's **first commit is 2026-07-09**, months after the window, so no workflow of
    ours could ever have run against it. We never used trivy-action or setup-trivy. And we have
    **no LiteLLM dependency at all**: enrich.py posts to the inference endpoint with stdlib
    urllib, and the backend has seven requirements, none of which reach it.

**BUT THE SHAPE OF THE FAILURE WAS LIVE IN OUR CI.** Both workflows ran
`curl .../aquasecurity/trivy/main/contrib/install.sh | sh` — an installer from a MOVING BRANCH,
taking whatever the newest release happened to be, in a job holding `DROPLET_SSH_KEY`. Our own
comment called it a feature ("CLI, no fragile action pins"). That is precisely the LiteLLM
mechanism. Now: pinned to **0.69.3** (a version Aqua confirmed clean), the tarball's **sha256
verified against the signed checksums file BEFORE the binary is executed**, and a test that fails
if a moving ref, v0.69.4, trivy-action or setup-trivy ever reappear.

**TRIVY HAD NEVER FAILED A BUILD.** All four invocations used `--exit-code 0`, and deploy.yml
documented the intent in its own step name ("report-only; flip --exit-code to 1 to gate") without
ever doing it — the same disease as the ruff gate that silently skipped for weeks. Now CRITICAL
exits 1 and HIGH still reports, because a gate that fires on everything is switched off within a
week. `.trivyignore` exists and the test **requires a reason and a date** per entry: an
unexplained allowlist is `--exit-code 0` wearing a hat.

**AND THE IMAGE THE SCANNER HAD NEVER SEEN.** Trivy scanned colttechbot and cassandra in CI.
`colt-web` is built by `deploy_web_direct.py` ON THE DROPLET, so it never went through CI at all —
the only INTERNET-FACING image was the only unscanned one. It is now scanned where it is built,
and the verdict is CONSUMED: the first cut echoed `TRIVY_CRITICAL_FAIL` and nothing read it, which
is the prints-but-does-not-gate defect this whole change set out to fix.

**THE 432 CVEs ARE A CADENCE QUESTION, NOT A TRIAGE QUESTION.** Schaumann (Akamai) on oss-sec:
"this onslaught really shows it's not feasible to attempt to prioritize individual kernel changes";
Kroah-Hartman's framing explains the volume (at the level the kernel runs, almost any bug that can
affect a running system meets the CVE definition). So `secaudit.py` does not count CVEs. It
measures the only things that decide exposure: **is the running kernel the newest installed one, is
a reboot pending, how many security packages are queued, is anything applying updates unattended.**
READ-ONLY, one ssh session per host, wired into ship.py as a building block, non-blocking.

**MY OWN DEFECTS IN THIS CHANGE, all caught by checking rather than assuming:**
1. **Valid YAML, broken shell.** Replacing a one-line `run:` with two commands produced a plain
   scalar, and YAML FOLDS those into one string: `trivy image ... trivy image ...` as a single
   nonsense command. `yaml.safe_load` was perfectly happy. Parsing is not correctness, again.
   Fixed with `run: |`; the guard asserts LINES >= COMMANDS.
2. **My own guard for (1) was vacuous.** It asserted every line starts with "trivy" — but after
   folding there is exactly ONE line and it does start with "trivy". The negative test is what
   exposed it. Assert the COUNT, not the shape.
3. **I reported a failed lookup as a finding.** The sandbox has no route to GitHub, so the
   `tpcp-docs` IOC check returned HTTP 000 and my script printed "INVESTIGATE". A lookup that
   cannot run is not a check — the oldest rule in this file, broken by me, in a security review.
RULE FOR SCANNERS GENERALLY: **the scanner is a supply-chain dependency like any other.** Pin it,
verify it, and make it able to fail — a scanner nobody gates on is a log file with a licence.

## WE WERE SELLING THE FINDING AND NOT MAKING IT (2026-08-13, security headers)
A visitor alert arrived: iOS Safari, page `/`, `Referrer: https://www.cybergod.ai/sw.js`. The
operator asked why it was not treated as dangerous. **It was not an attack, and the shield was
right to ignore it.** sw.js's install handler calls `cache.addAll(["/", "/app", ...])`, and a
browser attributes a fetch made by a service worker to the SERVICE WORKER SCRIPT URL. It was our
own code pre-caching the shell for a real person. `probe_shape("/sw.js")` is False, correctly:
blocking it would have blocked a visitor, which is the failure mode the 439-404 and 362-404 real
visitors in the 10 Aug log already taught us to avoid. The panel did nothing because there was
nothing to do, and because it reviews decisions out of band every 6h - it does not classify visits.
**BUT THE QUESTION WAS RIGHT AND THE ANSWER WAS EMBARRASSING.** cybergod.ai sent **no HSTS, no CSP,
no X-Frame-Options, no X-Content-Type-Options, no Referrer-Policy, no Permissions-Policy** - the
exact absence our own engine reported as a customer finding at abakus-tk.de, quoted in this file.
A `Referrer-Policy` would also have stopped the sw.js referrer being sent at all, so the alert was
literally an instance of the missing header.
- `webapp/backend/app/security_headers.py`, **in the app, NOT the shared Caddyfile** - one bad edit
  to that file took every domain on the box down for six hours on 6 Aug; a header belongs to the
  app that knows what it serves, ships inside the image (so the engine-hash verify covers it), and
  is testable with a TestClient in a second.
- Installed **after** telemetry, because Starlette makes the LAST middleware the OUTERMOST - so it
  also decorates the 404s the shield and bot gate return before the app runs, which is most of our
  traffic. Asserted by test, since getting it backwards fails silently.
- **`script-src 'self'` with no 'unsafe-inline'** is the only line here worth real money: an
  injected `<script>` or `onclick=` does not execute. It cost one change - defense.html's 20KB
  inline block became `/defense.js` - and that is why the extraction was worth doing.
  `style-src` keeps 'unsafe-inline' because React writes `style="..."` ATTRIBUTES and a nonce
  cannot apply to an attribute; inline CSS cannot call an API or read a cookie.
- `Cache-Control: no-store` on `/api/`: sw.js already refuses to cache it, this binds the caches we
  do NOT control (a corporate proxy, a CDN, a phone).
**THE CENTRAL TEST DOES NOT CHECK THAT A POLICY EXISTS.** It reads index.html and styles.css,
extracts every external origin the pages actually load, and requires the policy to permit each one
AND to permit nothing else. A CSP written from memory either blocks a font the site needs or
quietly allows an origin nobody reviewed.
**AND THAT TEST WAS BLIND ON ITS FIRST RUN.** Its "this is a navigation, not a subresource"
exclusion was `href="(https://...)"`, which also swallowed
`<link href="https://fonts.googleapis.com/css2?..." rel="stylesheet">` - a SUBRESOURCE, and the
single origin most likely to break the site. Removing the fonts origin from the policy changed
nothing. Only an `<a href>` is a navigation: **anchor on the ELEMENT, never on the attribute.**
Nth instance of a check aimed at the wrong subject. 12 negative tests, all caught after the fix.
`ship.py` now also reads the headers off the LIVE site (with a browser UA - BOT_404 serves an
unrecognised agent a 404, the blind spot that let www.cybergod.ai report healthy while returning
404 for weeks). The middleware setting them and the deployed response carrying them are different
claims, and a proxy sits in between.
ON "VIEW SOURCE IS OPEN": that is not a defect and cannot be closed. Every SPA ships its JavaScript
to the browser to run it; minification is not secrecy. The security boundary is the SERVER - the
session cookie, `/api/me`, owner-scoped decks - and `/app`'s HTML shell contains no data. What was
genuinely worth fixing is that the shell was served with no policy at all, which is now fixed.

## A PANEL THAT REVIEWS ITS OWN DECISIONS CANNOT SEE A NEW ATTACK (2026-08-13, attack_digest.py)
shield_panel answers "are the thresholds right" every 6h. It cannot answer "what is NEW", because
it only ever sees traffic the classifier already understands: a technique our corpus does not name
scores nothing, is never blocked, never becomes evidence, and is invisible **precisely because it
is new**. A blind spot with a feedback loop.
`attack_digest.unknowns()` looks at the other side of the line - sources that missed on many
DISTINCT paths (evidence the classifier does not produce), minus everything the corpus already
names. What survives is, by construction, a technique we cannot yet detect. Daily digest = attacks
per day (sparkline), classes, origins, the unknowns, and what the four models propose; delivered by
the Gmail API (SMTP is blocked outbound) and plain Telegram (an attacker controls the path text, so
Markdown would let a stray `_` make Telegram reject the whole message).
**THE MODELS PROPOSE, THEY NEVER INSTALL.** A model-authored regex on the blocking path could deny
real visitors. `vet()` refuses, deterministically and before a human is asked: anything matching our
own routes (verified: `.*`, `/app`, `^/api/`, `^/$`, `\.js$` all refused), anything that is not a
valid regex, anything matching everything. Survivors need an operator tap, and then become
DETECTION, never an automatic block. Two vendors agreeing outranks one.
**VARIETY, NOT VOLUME.** The first cut flagged a simulated real visitor with 450 404s on our own
routes - the 10 Aug shape exactly - because our routes are not probe shapes either and survived the
"unrecognised" filter. `_ours()` reads `main._APP_ROUTES`, the same list `_is_probe` uses, so a new
page cannot be a route for one and an anomaly for the other.
**A NEGATIVE TEST THAT PASSES BECAUSE OF DEFENCE IN DEPTH MEASURES THE OTHER GUARD.** Removing the
distinct-path floor changed nothing, because `_ours()` was also protecting that visitor. The floor
needed its own fixture where it is the ONLY guard: two odd paths, neither ours, neither a probe
shape, repeated 30 times - a stale inbound link, which is a support question and not an attack.
Then removing the floor fails. 9 negative tests, all caught.
ALSO: `sp.E` does not exist - shield_panel imports enrich INSIDE `_ask()`, so it is not a module
attribute; and `notify.telegram(text, reply_markup=None)` has no `markdown=`. Tenth and eleventh
invented signatures in this workstream. And `_time.gmtime()` in the new scheduler was a NameError
(`time` is imported plain) sitting OUTSIDE the try, which would have killed the task silently -
the angermann class, caught by the ruff F821 gate that exists because of it.

## THE 2026-08-13 RUN — the two worst items were ones NO model flagged
Gate 39/39, panel 4/4 GO. kimi raised three risks. Reviewed against the code:

**RIGHT, and cheap.** *"config_change_propagates detail is truncated mid-word."* `stagegate.py`
printed `c["detail"][:90]`, so FOUR checks were cut mid-sentence — "(that it is actually LOADED is
p", "not by t", "probed from colt-web -> 1". The detail is where a check states WHAT it measured,
so truncating it destroys exactly the evidence the check exists to provide, silently, on the
PASSING path. It also feeds the panel, so a reviewer reads half the facts — which is how the same
wrong call gets made three runs running. Now wrapped, never cut.

**PARTLY RIGHT, and the safe version was buildable.** *"No check exercises the Caddyfile under
ERROR conditions."* True. An earlier attempt at this wrote a broken fragment into the LIVE blocks
directory and took staging down, which is why it was removed. But `validate(text)` writes a temp
dir and runs a THROWAWAY container — it never touches the live file — so garbage can be fed to it
with zero risk. New `agent.py selftest`: an unbalanced config and junk must be REFUSED, the LIVE
config must still VALIDATE in the same breath (a validator that rejects everything passes a
reject-the-garbage test perfectly and is useless), the empty-config refusal must be armed, and the
live file's sha256 must be unchanged afterwards.

**WRONG.** *"No check for partial reload failures leaving Caddy with mixed old/new config."*
Caddy's `POST /load` replaces the whole config or fails; there is no mixed state to test.

**AND THE TWO NOBODY MENTIONED, both visible in the log:**
1. **`jhw:jobhuntwow 14 lines braces 3/2 <-- UNBALANCED`** — captured from the LIVE shared
   Caddyfile. migrate splits whatever is currently live, so that is not a bad fragment: it is
   proof the file on disk was damaged at that moment, which is the 6 Aug outage in its latent
   phase. Caddy reads config only at start, so the process kept serving from memory and nothing
   looked wrong. It was PRINTED, inside a table, and quietly repaired. **Silent repair of
   recurring damage means the thing causing it is never found.** `cmd_migrate` now `notify()`s.
   It still returns 0: restore fixes it, and failing a deploy over damage we just healed would
   train the operator to reach for `--force`.
2. **Trivy's three HIGH starlette CVEs, and OUR OWN PIN was what blocked the patch.**
   `fastapi==0.115.*` caps `starlette<0.47.0`, so 0.46.2 was the maximum resolvable and every fix
   needs >=0.49.1. CVE-2026-48818 (SSRF + NTLM credential theft via UNC paths in **StaticFiles**)
   is NOT theoretical here — `main.py` mounts StaticFiles on /assets — and CVE-2025-62727 (Range
   header merging) touches the FileResponse that serves the hero video. Verified both BEFORE
   upgrading rather than assuming they applied. fastapi 0.141 removed the cap; the whole suite was
   then run against fastapi 0.141.1 + starlette 1.6.0, because a green import is not a green app.
   This is the scanner earning its keep on its first real run, one day after being made able to fail.
3. **`patchwatch_timer: not-found` on STAGING, reported as OK.** `systemctl is-enabled` prints
   `not-found` for a missing unit and my check only knew `absent` and `None`, so the audit said
   "nothing queued" about a box where nothing applies security updates unattended. Anything not
   positively enabled now warns. Nth instance of a check that cannot recognise its subject's own
   answer.

**FOUR DEFECTS IN MY OWN WORK, all found by measuring rather than trusting:**
`socket` and `hashlib` were used and never imported (the ruff F821 gate caught both — it exists
because of the angermann outage); `site_blocks()` returns a LIST and I compared it to an integer,
which would have raised TypeError the first time the new check ran on the droplet; and
`cmd_selftest` crashed instead of skipping when docker was absent.
**AND FOUR WEAK ASSERTIONS OF MY OWN, each exposed by a negative test:** asserting
`len(site_blocks(` was present *somewhere* passed when one of two calls was unwrapped; asserting a
verdict name appeared *somewhere* passed when one of three branches was renamed; and grepping the
raw stagegate source for `agent.py selftest` passed when the line was commented out AND when it
was renamed, because **my own comment above it contains the same words**. Strip comments before
grepping — the brand gate, recover.py and the caddyguard TAMPER check have each already taught
this, and this is the fourth time.
**A `finally` STILL CANNOT SURVIVE A KILL.** My negative-test harness was killed by a timeout (my
own fault: a recursive `__pycache__` glob over the whole mounted repo) and left `if not live_ok:`
replaced with `if False:` in agent.py. My first "the tree is clean" check looked at a diffstat and
three greps and missed it; the next baseline run failed and found it. Scan for every marker the
harness could have written, not a sample.

## A FOURTH WASTED SHIP FROM THE SAME ROOT CAUSE — httpx (2026-08-13)
`python ship.py` refused to deploy, correctly, on four failures:
```
RuntimeError: The starlette.testclient module requires the httpx package to be installed.
4 failed, 176 passed
```
`starlette.testclient` imports **httpx**, which is NOT a dependency of this application — it is a
dependency of starlette's TESTING helper. It happened to be installed in the Linux sandbox where
the security-header tests were written, and is absent from the operator's Windows Python 3.13. So
the tests were unrunnable on the only machine that matters, and I had verified them everywhere
except there.
CLAUDE.md ALREADY carries this exact root cause, under a heading that begins "A CHECK MUST RUN
WHERE THE TOOLCHAIN IS CORRECT BY CONSTRUCTION (three wasted ships)". Writing the rule down a
fourth time would not have helped, so it is now a TEST.
**THE FIX IS NOT `pip install httpx`.** That is an operator step (operating principle 1), and
putting a test-only library into requirements.txt would ship it in the production image. The
harness now calls the ASGI app DIRECTLY with ~20 lines of stdlib asyncio: a scope dict, a
`receive` that returns an empty body, a `send` that records the status and headers. It needs
nothing beyond the standard library and the app, so it runs anywhere the app runs. It also does
NOT run the lifespan, so the digest/panel background loops never start during tests — which
TestClient did.
**AND THE SECOND FAILURE THE FIRST FIX EXPOSED:** raw ASGI emits header names as LOWERCASE bytes.
httpx had been quietly providing a case-insensitive mapping, so `headers.get(
"Content-Security-Policy")` returned None while `content-security-policy` sat right there. The
middleware was correct and the harness was not — worth stating, because a test failing for a
harness reason looks exactly like one failing for a real reason. `_CIDict` now lowercases on
lookup, which is what RFC 9110 §5.1 says a header table is anyway.
GUARD: `test_no_test_imports_a_library_the_app_does_not_declare` parses every `tests/test_*.py`
for real import statements (comments and docstrings excluded — the paragraph above would have
tripped a naive version) and fails on anything outside the standard library, pytest,
requirements.txt and this repo. Plus a second test asserting the ASGI harness itself imports only
`asyncio` and `app`.
VERIFICATION THAT ACTUALLY PROVES IT: a venv built WITHOUT httpx, reproducing the operator's
machine rather than the dev's. 186 tests pass there, and also on the stack that does have httpx.
Four negative tests, each reintroducing a real defect (the httpx import, the testclient import, a
non-stdlib import inside the harness, dropping the case-insensitive headers), all caught.
NOTE ON THE GUARD'S ONE BLIND SPOT, stated rather than hidden: if the offending import is in the
SAME file as the guard, the module fails to collect and the guard never runs. The suite still
fails loudly (pytest exit 2) so the ship is still blocked, but the message is a crash rather than
a diagnosis. Verified separately that an offending import in ANOTHER file is caught and named.
RULE, restated for the fourth time and now enforced: **before telling the operator to run
anything, ask which machine and which toolchain.** A green run in the dev sandbox is not evidence
about his box.

## I SHIPPED THE *SAME* HARDCODED-PATH DEFECT `mount_source()` EXISTS TO PREVENT (2026-08-13)
The staging gate went NO-GO on `refuses_bad_config`, pre- and post-reboot, and REFUSED to promote.
Production was never touched. All four review models diagnosed it correctly and unanimously: the
CHECK was broken, not the system — every other check passed, the site served traffic, and
`config_drift` proved the running config matched the file.
THE CAUSE, and it is humiliating: `cmd_selftest()` read `LIVE`, which defaults to PRODUCTION's
`/opt/videodead/Caddyfile`. Staging's proxy mounts a different path, so `read()` returned `""`,
`site_blocks("")` was 0, validating an empty string errored with "adapting config", and the check
announced "the LIVE config does not validate" about a demonstrably healthy box.
**That is the identical defect `mount_source()` was written to fix on 11 Aug, three functions
above in the same file, whose docstring says NEVER ASSUME LIVE in capital letters.** It is also
absence of evidence being turned into a finding, which is the oldest rule in this repository, in a
guard I wrote to prove other things fail safely.
FIX: ask docker where THIS container's `/etc/caddy/Caddyfile` comes from (`mount_source(c) or
LIVE`), read that, and SKIP — not FAIL — when there is nothing readable there. Verified against a
reproduced staging shape (LIVE absent, real mount elsewhere) and in all four behavioural
directions: honest validator passes, a validator that accepts junk fails, one that rejects
everything fails, and a mutation of the file during the "read-only" selftest fails.
Guarded by test_gate_integrity.py: `mount_source(` must be used, `read(LIVE)` must not appear, and
the empty-source SKIP branch must exist. Both negative-tested.
WHAT THE GATE GOT RIGHT: it failed closed, printed the failing checks, showed four independent
diagnoses that all named the real cause, and offered only staging-scoped actions. The correct
answer to its prompt was `n` — no panel action can fix a code defect, and the panel's own proposal
said so.
RULE, now enforced rather than written down for a second time: any check that reads a path on a
droplet must ASK for that path, never assume the production default. A check that cannot see its
subject reports the absence as a fault, and that is worse than having no check.

## A CHECK'S DETAIL IS PARSED BY ANOTHER CHECK — keep failure vocabulary out of a PASS (2026-08-13)
The path fix worked: `refuses_bad_config` correctly reported
`OK ... (/opt/staging-caddy/Caddyfile, 2 site block(s)), source file untouched`.
And the gate STILL went NO-GO, because stagegate's `self_contradictory()` demoter scans a PASS
detail for failure vocabulary and `refus` is on that list — matching inside the word "refuses",
which is this check's SUCCESS condition and its own name. A correct pass was flipped to a failure
and a good release was refused, twice.
kimi-k2.6 diagnosed it exactly: *"the check's own string parsing ('refus' matching 'refused' in
the detail description) flips the verdict to false."* All four models agreed it was a check
defect, not a system defect, and they were right.
TWO FIXES, and the second is the one that generalises:
1. **A detail states what was OBSERVED, not what the check is called.** "unbalanced config
   rejected, junk rejected, live config accepted" carries the same information with no failure
   vocabulary. Restating the check's own name in its detail adds nothing a reader did not already
   have from the name, and here it cost a deploy cycle.
2. **The demoter now reports its match IN CONTEXT.** It returned the bare regex match, so the
   failure read `detail says 'refus'` — five characters, no context, inside a sentence describing
   correct behaviour. It took a model reasoning from first principles to work that out; the
   message should simply have said it. Now: `'refus' in ...still accepts the live one...`.
DELIBERATELY NOT DONE: exempting a contradiction word when it appears in the check's own NAME.
That would have fixed this instance and blinded `config_drift` to a detail saying "drift" while
claiming PASS — which is the 2026-08-07 incident this whole demoter exists to catch.
GUARD: `test_the_selftest_pass_detail_does_not_trip_the_contradiction_demoter` RUNS cmd_selftest
against a healthy fixture and feeds its real PASS detail to the real `self_contradictory()`. Both
halves were individually correct, so only running them together catches this class. Four negative
tests, including reintroducing the exact wording that broke the deploy.
ON KIMI'S SECOND POINT (mount_fresh showing the same hash before and after the reboot, called
"suspicious"): the hash is the same because THE FILE IS THE SAME. Identical pre/post results are
what proves the check measures real state rather than a cache — CLAUDE.md already records exactly
that reasoning for config_drift, which kimi itself made in an earlier run. Its proposed fix (write
a nonce into the file) would mean MUTATING the live shared config to test it, which is the thing
that took staging down in an earlier round.

## THE THREE WARNINGS FROM A SUCCESSFUL DEPLOY — two were defects in my own new checks (2026-08-13)
The ship worked: 41/41 staging checks, GO, production live, `refuses_bad_config` finally correct.
It ended `FINISHED WITH WARNINGS`, and two of the three were mine.

**1. THE HEADER CHECK ANNOUNCED ITSELF AS A BOT.** `could not read the live security headers:
HTTPError 404`. It sent `Mozilla/5.0 (compatible; cybergod-verify)`, and `(compatible;` is the
classic crawler marker, so `visitors.classify()` called it a bot and BOT_404 answered 404. The
check then reported failure about a site that was serving every header perfectly. **CLAUDE.md
already records this exact blind spot** — it is what let www.cybergod.ai report healthy while
returning 404 for weeks — and I wrote the warning comment directly above the line and then walked
into it. FIX: `import check_bot_gate; BROWSER[1]`. ONE browser UA in the repo, unable to drift.

**2. THE DAMAGED-CONFIG ALERT FIRED AND NOBODY RECEIVED IT.** The new migrate alert correctly
detected `jhw:jobhuntwow braces 3/2 <-- UNBALANCED` in the LIVE shared Caddyfile — the 6 Aug
latent-outage shape, caught early, exactly as designed — and then printed
`[warn] no telegram credentials - alert not sent`. **An alert nobody receives is not an alert.**
The agent runs on the HOST, which has no token; colt-web has one AND resolves the chat the full
way (ALERT_TG_CHAT, else every authenticated uid). So `notify()` now falls back to
`docker exec -i colt-web python3 -c "from app import notify; notify.telegram(sys.stdin.read())"`.
Text over STDIN, never argv: it can contain an attacker-shaped path, and argv has a length limit
that already broke one payload here. Giving the agent its own copy of the token would have been a
SECOND home for a credential, which is the defect this repo has paid for repeatedly.

**3. `patchwatch timer not-found` ON STAGING — a true fact, and the wrong question.**
Staging is a DISPOSABLE TWIN, rebuilt from production every ship; an unattended patcher there
could reboot it mid-validation. A warning that fires benignly every run trains the operator to
ignore the one that does not. What ACTUALLY matters is whether the twin's KERNEL MATCHES
production's, because the reboot test is the entire reason staging exists and a reboot on a
different kernel validates something that will never ship. So the per-host warning is now scoped
to production, and `secaudit.main()` compares the two kernels across hosts and reports TWIN DRIFT.
Ask the question that has consequences, not the one that is merely true.

**AND TWO WEAK ASSERTIONS OF MINE, both exposed by the negative tests:** the notifier check
asserted `notify.telegram` but not `from app import notify`, so deleting the import left a command
that could never run and the test still passed; and my first verification of the twin comparison
RE-IMPLEMENTED the expression in the test instead of calling `secaudit.main()`, proving nothing
about the code that ships. The rewritten test stubs `run()` and `sys.argv` and executes the real
path. Five negative tests, all caught after the fixes.

## THE 10-MINUTE WATCHDOG CHECKED EVERY HOP BUT THE ONE THAT CAUSED THE OUTAGE (2026-08-13)
kimi-k2.6, on a 41/41 GO run, and it is the sharpest gap the panel has found since the admin API:
*"No check verifies that an external edit to /etc/caddy/Caddyfile triggers auto-reload. The
2026-08-07 outage involved exactly this: 12 hours of silent unapplied config."*
Confirmed by inspection. `cmd_check` — the thing the systemd timer runs every 10 minutes — verified
that the file is VALID, the proxy is RUNNING, :443 is BOUND, and the container can SEE the file
(hop 1, `mount_sync`). **It never asked whether the running process was SERVING that file.** So a
config that is valid on disk and was simply never reloaded was invisible to the watchdog until the
next ship or the next reboot. That is the 6 Aug mechanism with the invalidity removed — and Caddy
reads its config only at start, so "valid on disk" is the state that outage was in for twelve hours.
The entire point of a 10-minute timer is to turn a 12-hour latent window into a 10-minute one, and
it was only doing that for the half of the problem `validate` happens to catch.
FIX: `cmd_check` now runs `cmd_drift()` — REUSING it, not reimplementing it, so the timer and the
deploy can never disagree about what drift means — folds the result into the verdict, and with
`--heal` re-applies the validated live config. Guarded by test_drift.py, negative-tested in four
directions (no comparison · detected-but-not-alerted · drift dropped from the verdict · cmd_drift
not called at all), each verified to fail and then restored.

**MY OWN TWIN-KERNEL CHECK RAN, ANSWERED CORRECTLY, AND WAS THROWN AWAY.** ship.py filtered
secaudit's output through a HARDCODED LIST of the phrases I happened to think of when I wrote it.
My new comparison prints `OK  staging and production run the SAME kernel`; the list matched
`OK  running`. So the result was computed on the droplet and dropped here, and on screen a healthy
twin was indistinguishable from a check that never ran. Same defect as the caddyguard DRIFT section
that executed and was never printed, and the same shape as `_APP_ROUTES` going stale: two homes for
"which lines matter", and the newer one always loses.
FIX: `ship.secaudit_line_matters()` — a NAMED function, because a predicate buried inline cannot be
tested. A verdict is any line carrying a MARKER (`[X]`, `[!]`, `OK `), which is a property of the
output format, so a new check inherits it for free; the keyword list survives only for fact lines
that carry no marker. The test does NOT re-implement it (that proves nothing about what ships): it
runs the REAL `secaudit.main()` over stubbed droplets and feeds its REAL output to the REAL
predicate, in both the twins-agree and twins-drifted directions.

**AND `config_change_propagates` WAS RENAMED TO `guard_write_path_reloads`** — kimi again, same
class as the earlier `config_reread` → `config_write_ordering` rename. The check exercises the
guard's own validate → write → mount-check → reload path; it says nothing about an external edit.
A name is read far more often than a detail string, and a name that overclaims is how an operator
comes to believe a bare file edit propagates. That belief IS the 6 Aug outage.

**SIX DEFECTS OF MY OWN IN ONE SESSION, five of them in the checks rather than the code:**
1. **I appended pytest-shaped functions to a file that has its own `ok_()` runner.** They parsed,
   the suite went green, and NOT ONE of them ever executed. The ruff gate cannot see this and
   neither can a passing run — only counting the check's own output does. Nth instance of "a check
   that cannot run is not a check", this time self-inflicted in the same breath as fixing one.
2. **`src[index("def cmd_check("):index("def cmd_write(")]`** — `cmd_write` is DEFINED EARLIER in
   the file, so the slice ran backwards and measured an empty string. Anchor on the NEXT `\ndef `,
   never on a function name whose position you assumed.
3. **`replace(a, b, 1)` mutated the wrong function.** `notify("\n".join(detail))` appears in
   `cmd_migrate` too, and cmd_migrate comes first, so my negative test muted the wrong alert,
   reported NOT CAUGHT, and I nearly "fixed" a working assertion. A mutation must be scoped to the
   function it claims to break.
4. **A stub that spoke a format the parser never accepts.** `parse()` reads `key: value`; I wrote
   `key=value`, so every fact came back None and the twin comparison had nothing to compare. A
   fixture that cannot be parsed is a test of the fixture.
5. **`_strip_comments` does not exist in that file** — the TWELFTH invented name in this workstream.
6. **A `glob("**/__pycache__", recursive=True)` over a repo containing node_modules** timed the
   harness out, and a SIGKILL cannot run `finally`, so a muted `TWIN DRIFT` line was left in
   secaudit.py. Caught only because I scanned for EVERY marker the harness could have written
   rather than eyeballing a diffstat. Restore immediately after each mutation, not in a `finally`.
RULE, restated: after any harness that edits real files, grep for every marker it could have left.
A "clean" diffstat is not a clean tree when the interesting change is one line long.

## THE TEST FAILED ONLY ON WINDOWS, AND THE PASSING HALF WAS A FALSE PASS (2026-08-13)
`python ship.py` refused to deploy, correctly, on one line:
```
  FAIL  a healthy proxy (running config == file) is NOT flagged
[X] DRIFT CHECK REGRESSION - the staging gate would block or miss wrongly. Do not ship.
```
Green in my sandbox, red on the operator's box. The fixture wrote its temp Caddyfile with
`open(path, "w")` — Python TEXT mode, which on Windows rewrites every `\n` into `\r\n` — while the
stub for "what the container sees" hashed an LF string. So `mount_sync` compared CRLF bytes against
an LF hash, reported a STALE MOUNT, and `cmd_check` called a perfectly healthy box unhealthy.
**AND THE DRIFT CASE PASSED FOR ENTIRELY THE WRONG REASON**: it wanted rc=1 and got rc=1, but from
the phantom mount mismatch, not from detecting drift. A false pass is the more dangerous half —
the failing assertion at least announces itself.
FOURTH APPEARANCE OF THIS TRAP HERE: `git archive` applying autocrlf made the deploy artefact
platform-dependent; a CRLF payload over ssh broke a bash script; the preview stamp hashed raw bytes
so it meant "previewed on this operating system". Content is content; the byte that ends a line is
the platform's business.
TWO FIXES, and the second is the one that generalises:
1. **The stub now models the mount honestly** — the container reads the SAME MOUNTED FILE, so it
   hashes what is actually on disk instead of a hardcoded string. A fixture that does not model
   reality is a test of the fixture. (Same class as the secaudit stub that spoke `key=value` at a
   parser reading `key: value`.)
2. **The line ending is now a PARAMETER.** Every watchdog assertion runs under LF and CRLF and the
   verdict must be identical, plus an explicit `"STALE MOUNT" not in output` so a line-ending
   artefact can never again be mistaken for a drift verdict. A platform difference now fails in the
   test, not on the operator's machine.
RULE: any fixture written to disk that will be hashed, diffed or fed to a parser must be written in
BINARY with explicit bytes. And when a test only exercises one platform's line ending, it is
testing one platform.

**AND A GAP THE MUTATIONS FOUND: BEHAVIOUR WAS TESTED, WIRING WAS NOT.** `mount_sync` has eight
dedicated assertions — all in ISOLATION. Stubbing out the CALL inside `cmd_check` went completely
unnoticed, because the dedicated tests invoke `mount_sync` directly and never ask whether the
watchdog still consults it. A control that is correct and unreachable is not a control; identical
to the shield tests that proved shield.py behaves while nothing asserted the middleware invokes it.
Two assertions added: the watchdog must consult the mount hop, and it must pass `fix=bool(heal)` so
a read-only run cannot restart the proxy and blip every vhost on the box.
Six mutations, all verified to fail and then restored: no drift comparison · drift dropped from the
verdict · detected-but-not-alerted · cmd_drift not called · mount check removed · read-only run
made destructive.

## THE PANEL, 13 Aug 2026 (post-deploy): the roster was RIGHT and its OUTPUT was not
Deploy clean, 41/41, three of four GO. kimi returned NO-GO on one line it read literally:
```
  vhost_roster  OK  all 1 expected domain(s) are served (2 host(s) total)
```
Its conclusion — *"a defect in the check logic: it verifies expected hosts exist but does NOT flag
unexpected hosts as an error"* — is WRONG about the code. `cmd_roster` has warned about surplus
vhosts since 9 Aug, when kimi itself made the symmetry argument that produced the feature. The
second host was `www.cybergod.ai` (production's eleventh was `www.klimaanlage-preise.de`), both
`www.` variants of committed domains, which the exemption three lines above allows deliberately.
**BUT THE OUTPUT NEVER SAID SO, AND THAT PART IS MINE.** A count that legitimately differs from
its expectation, printed with no explanation, is indistinguishable from a check that is simply not
looking. It has now cost a review slot twice in three days — the model-authored GEOPOL artifact's
varying SIZE was the identical shape on 11 Aug. FIX: the roster names the exempted variants
(`+1 www/subdomain variant(s) of committed domains, expected: www.cybergod.ai`). The logic is
untouched: a foreign vhost is still named and warned, a disappeared one still fails. Guarded by
test_drift.py against the exact shape both boxes printed, negative-tested in three directions
(count unexplained again · foreign vhost no longer named · a www variant wrongly warned about).
RULE: print the explanation next to the number, not in the source comment. The reader of a deploy
log — human or model — has only the line.

**KIMI'S SECOND RISK WAS ALREADY FIXED, AND MY OWN DETAIL STRING HID IT.** *"No check verifies
that the explicit caddy reload actually succeeds... an external edit is unverified for staging."*
The watchdog gained exactly that comparison in the previous commit, and staging's `proxy_config`
runs `agent.py check`, so staging HAS been covering hops 1-3 including the external-edit case. Its
detail still read *"(that it is actually LOADED is proven by config_drift, not here)"*, which was
true before the change and false after it. **A stale detail underclaims as badly as a name
overclaims** — same family as `config_reread` -> `config_write_ordering`, one direction over.
Rewritten to say what it now measures, and checked against `self_contradictory()` so a correct
pass cannot be demoted by its own wording (the 13 Aug NO-GO class).

**THIRD RISK, NOT ACTED ON, WITH THE REASON.** *"restart_count reads Docker's counter, not whether
caddy restarted internally or a signal-based reload failed."* True and already covered elsewhere:
a failed reload leaves the OLD config running, which is precisely what `config_drift` compares. A
second check measuring the same fault through a weaker signal is noise.

**AND A SIGNATURE I GUESSED TWICE IN ONE MINUTE.** `self_contradictory` takes the check DICT, not
`(name, detail)` and not the detail string. Two TypeErrors before I read six lines of the function
I was calling. Thirteenth in this workstream; the fix is always the same and always cheaper than
the guess.

## THE GATEWAY MADE structured-output AND max_tokens MUTUALLY EXCLUSIVE (2026-08-14)
Three vendors returned the same 400 in ONE release-notes run — deepseek-3.2, llama-4-maverick AND
gemma-4-31B-it — so this is DO's gateway, not a model. Verbatim:
```
max_tokens cannot be set when response_format type is 'json_object';
omit max token limits for structured outputs to avoid truncated JSON responses
```
Nothing broke: the 400-retry recovered. But it cost THREE wasted round-trips on every call, and
**the retry repaired the wrong field.** `if "response_format" in body` matched first (the message
names both), so it dropped the JSON contract and KEPT the ceiling the server had just objected to —
the exact inverse of the advice, and it re-creates our own worst failure mode: a max_tokens cut
lands MID-JSON (`finish_reason=length` -> JSONDecodeError at char 13,290 and char 30,117, both
already in this file).
FIX, in the direction the server named: keep `response_format`, drop `max_tokens`. We lose only the
FEASIBILITY bound; wall clock is still held by the per-call timeout, and a timeout is a CLEAN
failover while truncated JSON is a dirty one that wastes the slice AND yields garbage. The 400 is
also PRE-EMPTED in the payload builder, so the three wasted round-trips are gone. Kimi is
unaffected — it has `response_format` in `_drop`, so it keeps its ceiling.
RULE, restated for the third time: when an API rejects a request, repair WHAT IT NAMED, in the
direction it named it — never whichever field the first regex happens to hit.
Guarded by test_recall.py §25 (pre-empted for all three · JSON kept · kimi untouched · the retry
drops max_tokens when named · a body naming response_format alone still drops response_format).

## THE WORST "CHECK THAT CANNOT FAIL" YET: 73 OF THEM, INCLUDING THE budget.gov.ru GUARD
Found while adding §25. `test_recall.py`'s ONLY `sys.exit(1)` sat in the MIDDLE of the file, at
line 253 of 761. Everything below it — S18 and sections [19] to [25], **including [22], the
public-suffix guard that stopped the whole-Russian-government blow-out** — printed FAIL and the
script still exited 0, so `python ship.py` deployed anyway.
MEASURED, NOT INFERRED. Breaking [22] so that two Russian ministries resolve to the same owner (the
literal incident) gave `FAIL lines=1, rc=0`. Breaking an EARLY check gave rc=1. The mid-file banner
also printed "ALL CHECKS PASSED" with 73 checks still to come.
This is the worst shape of the recurring disease because new sections are APPENDED: the checks it
silently stopped enforcing were always the newest and least proven.
FIX: the real gate is now the LAST thing in the file, `check()` counts what it ran, and the
mid-file block is labelled a fail-fast for sections 1-13 rather than a completion banner.
GENERALISED so it cannot recur anywhere: `tests/test_gate_integrity.py` walks every
`hermes-skills/.../test_*.py` and fails if the last exit precedes the last check. Negative-tested
in both directions — deleting the final gate is caught, and appending one new check after it is
caught, which is exactly how this would rot again.
NOTE: test_run_path.py LOOKED broken to a naive grep for `sys.exit(1)` (13 checks after it) but is
fine — that hit is a fail-fast inside an exception handler and its real gate, `sys.exit(1 if FAILS
else 0)`, is last. Grep for the CONCEPT, not one spelling.

**FIVE MISTAKES OF MINE IN THIS ONE CHANGE, all the same family:**
1. I appended the new section using `s.rindex('print("=" * 78)')` and it landed BEFORE `enrich` is
   imported, so the file crashed at `E._post` and every section after it — including [22] — never
   ran. My first mutation test therefore measured nothing.
2. `ok_` does not exist in test_recall.py; that file's runner is `check`. Fourteenth invented name.
3. `TOTAL_CHECKS` did not exist either — I referenced a counter instead of adding one.
4. `timeout ... python3 x.py | tail; echo "rc=$?"` reads TAIL's status, not Python's. I read rc=0
   off a crashed run and nearly concluded the opposite of the truth. Redirect to a file, then echo.
5. My cross-file scan grepped the literal `sys.exit(1)` and so misclassified two files. The
   property is "the last exit follows the last check", and that is what the guard now asserts.

## THE BOOKS OF RECORD HAD NO BACKUP — `dbbackup.py` (2026-08-14)
Two SQLite files hold the only things this system cannot regenerate: `colt.sqlite` (who ran what,
when, in which language) and `cost_ledger.sqlite` (the TRUE all-time cost, which exists precisely
BECAUSE Loki ages out). `git` is the backup for code; NOTHING backed up these.
patchwatch is not a counter-argument. It tars the docker volumes before an upgrade, which is
better than nothing, but (a) it runs only before a patch, (b) it `tar`s a LIVE file and SQLite in
WAL mode can be mid-transaction, so the copy inside may be torn, and (c) nobody has ever opened one
to find out. A backup nobody has restored is a folder.
WHAT SHIPPED: `deploy/dbbackup/agent.py` on a daily systemd timer (03:17 UTC + 5 min after boot,
`Persistent=true` so a droplet that was off still runs the missed one), installed by `dbbackup.py`
in ONE ssh session with the payload on stdin in BINARY mode. It is a BUILDING BLOCK of ship.py, not
a second command, and non-blocking: a backup problem is information, not a reason to refuse a
verified deploy.
  * sqlite3's ONLINE BACKUP API (`Connection.backup()`), never cp/tar. Guarded by a test.
  * VERIFIES THE COPY: `PRAGMA integrity_check` plus per-table row counts. A copy that fails is
    DELETED and alerted, because a corrupt backup is worse than none: it buys false confidence.
  * OFF-BOX or it says so, loudly. Credentials come from `/etc/patchwatch/patchwatch.env`, which
    already exists and is chmod 600 — NOT a second credential home.
  * `verify-restore` performs a real restore into a temp dir every run, and `restore` is explicit,
    keeps the file it replaces, and refuses a backup that fails integrity_check.
  * Alerts through colt-web (`docker exec -i`, text over STDIN), because the host has no token.

**THE DESIGN BUG THE MEASUREMENT CAUGHT, and it would have been worse than no backup.** The first
version compared the copy's row counts to a SINGLE pre-backup read. The source is LIVE, so rows
commit between the count and the copy: on a busy night that comparison fails, the good backup is
deleted and an alert fires. A check that false-alarms on a healthy system is worse than no check,
because it trains you to ignore the one that matters. The invariant is now a WINDOW — the copy must
hold at least what existed before the copy and no more than what exists after — which is sound
because both tables are append-mostly.
**AND THE ONE FUNCTION EXISTS FOR THE CASE IT CRASHED ON:** a badly corrupt file does not return a
non-"ok" `integrity_check`, it RAISES `sqlite3.DatabaseError: database disk image is malformed`.
`verify()` let that propagate, so the exact scenario it was written for produced a traceback rather
than a report. Everything is wrapped now.

**THREE OF MY OWN TESTS WERE VACUOUS, and only the mutation run exposed them:**
1. The live-writer test caught the exact-equality defect ONLY WHEN THE RACE HAPPENED, so on a fast
   machine it passed against broken code. Now the window is forced deterministically: commit rows
   BETWEEN reading `before` and taking the copy. **A test that depends on a race is not a test.**
2. Nothing asserted that a copy failing verification is DELETED. Removing the `os.unlink` went
   unnoticed, leaving exactly the file you would reach for in an incident.
3. The ship.py wiring check grepped for the bare string `dbbackup.py`, which also appears in a
   `print()` line, so breaking the real call site passed. Anchor on the CALL
   (`os.path.join(HERE, "dbbackup.py")`), never on a filename that appears in prose.
Seven mutations, all verified to fail and then restored.
ALSO: running it by hand as non-root died with a raw `PermissionError`. A traceback is not a
diagnosis; it now names the cause and the fix.

## VIEW-SOURCE CANNOT BE DISABLED — so measure what is IN the source (2026-08-14)
The operator asked, twice, why view-source still works on cybergod.ai including /app. The honest
answer has two halves, and the second one is the actionable one.

**IT CANNOT BE TURNED OFF, BY ANYONE.** view-source shows bytes the browser ALREADY HAS. There is
no header, no CSP directive and no server setting that removes it; curl, DevTools, the disk cache,
or any proxy return the same bytes, and blocking right-click is theatre that Ctrl+U defeats. Every
SPA on the internet ships its JavaScript to the browser in order to run it — Gmail, banks,
Salesforce. Minification is not secrecy.

**SO THE SECURITY BOUNDARY IS THE SERVER, AND IT IS WHERE IT SHOULD BE.** `main.py::spa()` returns
the SAME `index.html` for `/` and for `/app`: a 4.7 KB shell with meta tags, JSON-LD and a script
tag. MEASURED: zero customer data, zero job ids, zero emails. Every assessment, deck and history
row arrives over `/api/*` behind the session cookie, and `/api/me` answers 401 to anonymous callers
on every deploy verify. Somebody reading /app's source learns the marketing copy and a bundle
filename.

**WHAT WAS ACTUALLY WORTH FIXING, found by measuring rather than arguing:**
  * NO SOURCE MAPS (verified: vite's build default is false, and 0 `.map` files in dist). This is
    the one that would have been a real finding — a shipped `.map` hands over the entire original
    source, comments included.
  * NO SECRETS in the bundle (verified against droplet IPs, OpenAI/GitHub/Grafana/Telegram/AWS key
    shapes). The only "Shodan" strings are the GDPR data-source disclosure on /privacy, which is
    required to be there.
  * **HTML COMMENTS DID SHIP, and they were mine.** `index.html` explained the bot gate by name —
    `BOT_404=1` and "See visitors.py" — delivered to every visitor including the scanners that gate
    exists to keep out. Not a vulnerability; free information handed to an attacker for nothing.
FIX: a `transformIndexHtml` plugin with `apply: "build"` strips HTML comments on the way into
dist/. The comments STAY in the source, because explaining WHY is the point of them and the dev
server still shows them. `<script type="application/ld+json">` is an ELEMENT, not a comment, so the
structured data that earns the rich search result survives — asserted, because a greedy strip there
would silently cost the SEO work.
GATE: `tools/shipped_shell.mjs` measures dist/ — no maps, no secrets, no comments, JSON-LD and the
meta tags intact — wired into ship.py AND `webapp/Dockerfile` after `npm run build`, so it runs on
the toolchain that is correct by construction. Exit 2 (no dist/) is a NOTE, exit 1 is a defect.
Five negative tests, all caught.
RULE: when asked to hide something the web cannot hide, do not argue the general point. Measure
what is exposed, fix whatever genuinely should not be there, and say plainly which part is
impossible and why.

## RIGHT-CLICK GUARD — the operator asked for a deterrent, not a proof (2026-08-14)
I answered the wrong question twice. He knows view-source cannot be disabled; he asked for the
standard commercial treatment — intercept right-click, show a branded notice that the content is
protected IP — which he has shipped on his own sites. `components/ContentGuard.jsx`, mounted once
above the routes so it covers the public pages AND the cabinet and survives navigation.
Intercepted: contextmenu, Ctrl+U, Ctrl+S, Ctrl+Shift+I/J/C, F12, and dragging an image out.

**FOUR THINGS IT MUST NOT BREAK, and each would be a real defect:**
1. **FORM FIELDS.** The cabinet's whole job is typing a company name and people PASTE it. Blocking
   the context menu inside an input removes paste, spellcheck and undo. Inputs, textareas, selects
   and contenteditable are exempt — including a child element inside one, which is why the check
   uses `closest()` and not just `tagName`.
2. **COPYING RESULTS.** Selection and Ctrl+C are deliberately untouched. A partner reading the
   5,000-word /partners page, or an operator copying a job id out of the run log, is doing what the
   product is for. Blocking copy is the user-hostile version and buys nothing.
3. **ACCESSIBILITY.** Only the listed shortcuts are caught; Tab/arrows/Enter/Escape and Ctrl+P are
   untouched, and the notice is `role="status"` + `aria-live` rather than a focus trap.
4. **THE LANGUAGE.** It is a string that reaches a human, so it is in the keyed dictionary in all
   six locales and names the IP owner. A hardcoded English notice would fail the i18n audit.
DevTools is deliberately NOT chased past the keyboard shortcuts: the menu opens it anyway, so a
detection loop would burn CPU on every visitor to inconvenience nobody. Do the honest 90% cleanly.
VERIFIED BY EXECUTION, not by compiling: the real predicates are pulled out of the component and
run against a stub DOM (15 cases: blocked where intended, ALLOWED in every editable shape, and
copy/paste/select-all/print/Tab explicitly not blocked), plus an SSR render on /, /app, /partners
and /demo in four languages asserting the notice text appears translated and no raw key leaks.

**AND THE FIFTEENTH ASSUMED SIGNATURE IN THIS WORKSTREAM.** `useT()` returns
`[lang, setLang, t]`, not a function. `const t = useT()` compiled fine and died at render with
`TypeError: t is not a function` — the /app white-screen class again, caught only because the SSR
render EXECUTES the page. Read the helper; do not guess it.

## `os.uname()` — THE FIFTH WASTED SHIP FROM THE SAME ROOT CAUSE (2026-08-14)
`python ship.py` refused to deploy, correctly, after a clean 198-check engine run:
```
AttributeError: module 'os' has no attribute 'uname'. Did you mean: 'name'?
2 failed, 205 passed
```
**`os.uname()` is POSIX-only.** The agent RUNS on the Linux droplet, so production was never
affected — but the TESTS run on the operator's Windows box, and the call sat on the FAILURE path
(the alert line), which is the one place a backup tool has to be reliable. Both failing tests were
the two that exercise a failed backup.
This is the same root cause as the httpx incident and the esbuild incident before it, and
CLAUDE.md already carries the rule in two places: *a check that cannot run on the invoking platform
is not a check*, and *before telling the operator to run anything, ask which machine and which
toolchain*. Writing it down a fifth time would not help, so it is a TEST now.
FIX: `HOSTNAME = socket.gethostname()` (stdlib, identical on the droplet), plus
`datetime.utcnow()` -> `datetime.now(timezone.utc)` because six deprecation warnings per run were
burying the real output.
GUARD: `test_no_posix_only_api_in_code_the_tests_exercise` walks the AST for `os.uname/getuid/
geteuid/fork/getpwuid` and for `pwd/grp/fcntl/termios/resource` imports. AST rather than grep, so
a comment discussing the removed call cannot false-positive — the mistake already made four times
in this repo. Negative-tested in three directions, all caught.
VERIFICATION THAT ACTUALLY PROVES IT: `del os.uname` before importing the agent, then run the
failure path. That reproduces Windows precisely for this API rather than trusting the fix.
RULE, now enforced: anything the test suite EXECUTES must be importable and runnable on Windows,
even when it only ever ships to Linux.

## THE BACKUP'S FIRST PRODUCTION RUN BACKED UP NOTHING AND EXITED 0 (2026-08-14)
The deploy log, verbatim:
```
--- DATABASES ---   [!] volume colt_webdata not found
                    [!] volume colt_events not found
--- BACKUP ---      SKIP not present in volume colt_webdata (nothing to back up yet)
```
Both databases exist; the ledger holds 193 assessments. **Docker Compose PREFIXES volumes with the
project name**, so the real volumes are `colt-stack_colt_webdata` and `colt-stack_colt_events` —
and `docker-compose.web.yml` says exactly that in a comment I did not read. The agent looked up the
unprefixed names, found nothing, and reported success. That is the worst possible outcome for a
backup tool: the operator now believes the books of record are safe.
TWO FIXES, and the second matters more than the first:
1. **ASK THE CONTAINER, never assume a name.** `volume_path()` reads colt-web's own mount table
   (`docker inspect .Mounts`) and maps `/var/log/colt/cost_ledger.sqlite` to its host path. That is
   prefix-agnostic, so renaming the Compose project cannot break it again. Same rule caddyguard's
   `mount_source()` already enforced, and I did not carry it across. The volume-name fallback (for
   a stopped container) now matches by SUFFIX for the same reason.
2. **FINDING NOTHING ON A LIVE BOX IS A FAILURE.** A fresh deployment legitimately has no databases
   yet, so the discriminator is whether the APP IS RUNNING: if colt-web is up, those files exist by
   definition and not finding them means the LOOKUP is broken, not the estate empty. It now exits 1
   and alerts, naming the container and printing the `docker inspect` command that shows the truth.
   My own test `test_a_missing_database_is_a_skip_not_a_failure` had encoded "missing = SKIP =
   success", which is right on a fresh box and catastrophic on a live one.
RULE: a tool that reports success for work it did not do is worse than one that crashes. When
"nothing to do" and "I cannot see my subject" produce the same output, they must be distinguished
by something external — here, whether the process that owns the data is running.
Guarded by three FUNCTIONAL tests (mount-table resolution with the volume list deliberately
useless; the Compose-prefixed fallback; nothing-found-while-running). The first replaced a static
`".Mounts" in source` assertion that passed against a mutation which kept the string and disabled
the branch — the wrong-subject defect again. Three mutations, all caught.

## Trivy 0.69.3 vs 0.73.0 — the banner is noise, the pin is deliberate
The "a newer Trivy is available" notice printed TWICE per deploy. `--skip-version-check` silences
it. The pin is NOT stale-by-accident: 0.69.3 is the last release Aqua confirmed clean after the
Feb–Mar 2026 supply-chain compromise, and the install verifies the tarball's sha256 against the
signed checksums file before executing it. The VULNERABILITY DATABASE updates independently of the
binary, so findings are current on either version. An upgrade is therefore a deliberate, reviewed
change to `TRIVY_VERSION` in deploy.yml / security.yml / deploy_web_direct.py — never something to
be nudged into by a banner printed by the tool asking to update itself.

## THE RECURRING "SHARED CONFIG IS DAMAGED" ALERT WAS US, EVERY DEPLOY (2026-08-14)
The alert fired after every single `python ship.py`:
```
CADDY: the LIVE shared config is DAMAGED
jhw:jobhuntwow 14 lines, 3 open vs 2 close
... the open question is WHICH project wrote this, because it will do it again.
```
It was `deploy_web_direct.py`. After the CORRECT marker-based delete it also ran a blunt
```
sed -i '/cybergod/,/^}/d' "$CF"
```
which deletes from the FIRST line containing "cybergod" to the next `}` at column 0. **Line 14 of
`deploy/caddy/jobhuntwow.caddy` is a COMMENT** reading *"1:1 with cybergod.ai's traffic board"*, so
the range opened inside another project's block and ran to the closing brace of `jobhuntwow.com {`.
Reproduced exactly against the real committed blocks: 26 lines -> 14, braces unbalanced. That is
the reported symptom, to the line.
The blunt sed was belt-and-braces for a legacy UNMARKED cybergod block that has not existed for
months. Deleted; the marker delete is bounded, unambiguous and sufficient.
**WHY IT SURVIVED SO LONG:** caddyguard repaired it seconds later on every run, so the only symptom
was an alert that looked benign each time. An alert that is benign every time is exactly how the
one that matters gets ignored - which is the whole reason this alert exists.
RULE: never delete a RANGE from a shared file using a word that can appear in prose. Markers exist
so the boundaries are unambiguous; a keyword match will eventually start inside somebody's comment.
Guarded by `tests/test_caddy_wiring.py`, which EXTRACTS the deploy's real `sed -i` commands from
the script (never retyped, comments stripped so the explanation of the removed line cannot
false-positive), runs them against a monolith built from the REAL committed blocks, and asserts
every other project's block is byte-identical afterwards - plus that no range delete is unbounded,
and that our own block is still genuinely replaced. Proven by reintroducing the exact line: caught.

## IP REPUTATION — a visit from infrastructure is not a person (2026-08-14, 45.148.10.x)
The visitor alert said "A person just opened cybergod.ai" for 45.148.10.5 — AS48090 (TECHOFF SRV
LIMITED) / DMZHOST Amsterdam, bulletproof hosting + VPN exit, the SAME /24 that had probed /.env
and /aws-ses.json on 21 Jul and again 10 Aug. Calling it a person is the spoofed-trust bug again,
this time on the SOURCE rather than the user agent. The operator asked for four lawful capabilities;
all four shipped, and the offensive parts he also asked for were declined with reasons (below).
- **`ip_reputation.py`** — passive classifier at TWO speeds. `classify(ip)` is OFFLINE (a committed
  ASN/CIDR list of known hoster/VPN/bulletproof/cloud/scanner ranges) and safe on the request path;
  `enrich(ip)` adds the live RIPEstat ASN holder for the digest/report path only. It FAILS OPEN:
  `unknown` is treated as a person, so a real residential visitor is never silently dropped.
- **visitors.py mislabel fix** — `note_visit` now suppresses the "a person" alert when the source
  classifies as infrastructure, logging `visit_suppressed reason="infrastructure not a person"`.
  The check runs BEFORE the alert is composed (asserted).
- **alerts.py** — every security alert records the source /24 as HOSTILE in the reputation store,
  so a returning actor is recognised across days. Best-effort, never affects whether the alert fires.
- **repeat-offender memory** — keyed on the /24 (or /48), persisted on the shared colt_events volume
  like the cost ledger, so a rotating single address in one hosting block is still ONE actor.
  `repeat_offenders(min_days=2)` counts DISTINCT DAYS, not burst volume (guarded).
- **attack_digest** — surfaces returning actors as one line each with the infra verdict.
- **abuse_report.draft_complaint / complaints_for_repeat_offenders** — the four models draft a
  human-reviewed evidence package (IP/24, ASN holder + abuse desk from enrich(), first/last seen,
  paths, MITRE T1595) for the operator to FILE. Nothing is auto-sent; the drafter reaches no
  network at all (guarded). AbuseIPDB auto-submission stays the existing opt-in `abuse_report`
  path (needs ABUSEIPDB_KEY).

**WHAT WAS DECLINED, AND WHY IT IS NOT CLOSE.** Hacking back, active-scanning the attacker to find
"the real IP", or anything meant to harm/expose them: criminal where we operate — StGB §202a/§202b
(access/interception without authorisation), §303a/§303b (data alteration / computer sabotage), and
§202c which criminalises even POSSESSING/BUILDING the tooling with that intent; EU Directive
2013/40, US CFAA. It is also technically impossible: traceroute/nmap cannot see "behind" a VPN or
hoster — the packets terminate at the provider, so the only lawful path to the human is a complaint
to that provider, which enrich() names but never sends. VirusTotal is for files/URLs, not IP abuse
reports. BSI/CISA/CERTs act on evidence packages from a named reporter, not automated pings, and a
server that mass-mails abuse desks gets its own domain blocklisted — fatal when that domain sends
the login OTP.
RULE: detection and reporting scale; retaliation is illegal and pointless. Classify passively,
name the abuse desk, draft the complaint, let a human file it.
Guarded by tests/test_ip_reputation.py (offline classify, fail-open on unknown, /24 folding,
distinct-days-not-burst, drafter sends nothing, wiring order). Five mutations, all caught.

## set_secret.py PIPED THE VALUE TO `bash -s`, WHICH READS ITS SCRIPT FROM STDIN (2026-08-14)
`python set_secret.py ABUSEIPDB_KEY` printed, on the DROPLET:
    bash: line 1: 02ff4d68...: command not found
`run()` did `subprocess.run(SSH + [host, "bash -s", "--", name], input=value)`. **`bash -s` reads
its SCRIPT from stdin** - and the code piped the VALUE (the API key) there. So the droplet executed
the key as a command, the real REMOTE upsert script was never sent, and the secret reached the
droplet's shell. The local .env WAS written (that half worked), so the key looked half-applied: set
locally, absent on the droplet - which is exactly why AbuseIPDB showed the key "Never used".
FIX: `remote_command(name)` embeds the REMOTE script in ARGV (base64'd into a temp file so no
quoting layer corrupts it) and leaves stdin FREE for the value, which is what `VALUE="$(cat)"`
reads. The value now travels only on stdin - never in argv, `ps`, or shell history - and only the
NAME and the non-secret script are visible.
RULE: `bash -s` and "pipe the value on stdin" are mutually exclusive; the script has to travel in
argv. This is the same doctrine as caddyguard/dbbackup shipping their payload base64'd in argv with
data on stdin.
Guarded by tests/test_set_secret.py: the value never appears in the remote command, the embedded
script reads it from stdin, an end-to-end bash run upserts it idempotently, AND run() itself is
exercised with a stubbed subprocess to prove the WIRING (value on stdin, script in argv, no
`bash -s`). Proven by reintroducing the exact `bash -s` line: caught.

## USER ADMINISTRATION — per-user passwords, and the four rails around them (2026-08-20)
The operator asked for an Administration section, visible only to him, to create users, assign and
reset passwords, keep MFA, and see everyone registered. That is a change to AUTHENTICATION, so the
decisions matter more than the screen.

**THE MODEL.** `user_store.py` (repo root, beside colt_auth.py) is a SQLite credential store at
`/var/log/colt/users.sqlite` on the shared, persistent `colt_events` volume — the same volume and
the same reasoning as `cost_ledger.sqlite`, mounted read-write by colt-web AND both bots so all
three consult ONE store and can never disagree about a password. Passwords are stored as
scrypt(n=2**14, r=8, p=1) with a 32-byte salt; the plaintext is returned ONCE to the administrator
and never again.
- **`colt_auth.password_ok(email, pw) -> (ok, must_change)`** is the single gate, used by
  `Auth.begin`, so the bots and the web app share it. THE RULE, chosen by the operator: an ASSIGNED
  password WINS and the shared `COLT_BOT_PASSWORD` remains a fallback ONLY for identities that do
  not have one. That is what makes the page mean anything — resetting or revoking one person cannot
  be sidestepped by falling back to the secret everybody knows — while nobody is locked out on the
  day it deploys.
- **A DISABLED ACCOUNT STILL COUNTS AS EXISTING** (`has_account` returns True). If it did not,
  disabling somebody would hand them the shared password and "Disable" would be a button that does
  nothing. Guarded by a test.
- **A BROKEN STORE REFUSES.** If the database cannot be read, `password_ok` returns False rather
  than promoting everyone back to the shared password: a database problem must not become an
  authentication bypass.
- **TIMING.** `check_password` runs the same scrypt cost against a dummy salt on a miss, so "no such
  user" and "wrong password" take the same time and the endpoint cannot be used to enumerate
  addresses.
- **ADMIN LIST IS COMMITTED**, `colt_auth.ADMIN_EMAILS = {"feranicus@s4biz.io"}`, beside
  PARTNER_EMAILS and USER_QUOTAS — the same question (who may use this, how much, who decides)
  belongs in one place, and an address is not a secret, so committing it makes it auditable in git.
  `EXTRA_ADMIN_EMAILS` extends it without a code change.

**AUTHORISATION IS SERVER-SIDE, AND THE NAV ITEM IS NOT THE CONTROL.** Every `/api/admin/*` route
depends on `_require_admin`. Hiding a menu is presentation: anyone can issue the request the menu
would have issued. Likewise the forced first-login change is enforced by `_require_ready`, which
every functional endpoint now depends on and which returns 403 `password_change_required` — routing
the browser to a change-password screen would leave those endpoints reachable with curl and a
cookie. `/api/auth/change-password` deliberately depends on `_require_email`, NOT `_require_ready`,
or the forced state is a locked door with no handle.

**THE PASSWORD IS NOT EMAILED.** The OTP already proves control of that mailbox; sending the
password there too would put both factors in one channel. It is shown once in the UI and relayed by
the operator over a channel they choose. `generate_password()` excludes 0/O/1/l/I because a password
that has to be re-sent after being misread ends up in more places than it should.

**FIVE OF MY OWN DEFECTS, EACH CAUGHT BY A GATE OR A NEGATIVE TEST:**
1. `colt_auth` used in `change_password` without importing it — caught by the ruff F821 gate.
2. Static greps asserting `_require_admin(request)` appears in each route body PASSED when the
   function's DEFINITION was renamed: the call text is unchanged and the app would only fail at
   runtime. Replaced with real requests through the ASGI app carrying a signed session cookie.
   **Behaviour, not text** — the same lesson as validating a temp copy instead of the mounted file.
3. `_require_admin` built on `_require_email` would have exempted the ADMINISTRATOR from the forced
   password change. Found by a negative test; the rule has to apply to the person who wrote it.
4. **MY TEST FIXTURE POLLUTED test_auth.py.** It reloads `colt_auth` with a test password;
   `monkeypatch` restores the ENV but the module keeps what it read at import. Two cases in
   test_auth failed with "denied" while passing in isolation — the signature of cross-test
   pollution. A fixture that reloads a module must reload it again on teardown.
5. The field markup was invented (`<label className="fld"><span>`) instead of read from the
   neighbouring page (`<div className="fld"><div className="label">`, `className="input"`), so it
   would have rendered unstyled.

**IT WAS FOUR WIRING POINTS, NOT THREE — and I wrote "three" one paragraph before the staging
build proved otherwise.** `deploy_web_direct.INCLUDE` is a SEPARATE allow-list deciding what is
packed into the tarball sent to the droplet; `colt_auth.py` is named there explicitly and
`user_store.py` was not, so the file never arrived and the image build died with
`COPY user_store.py /opt/user_store.py -> "/user_store.py": not found`. The staging gate caught it
and production was never touched, which is the gate doing exactly its job. My test could not see
it: it asserted the Dockerfiles and `.dockerignore` and had no idea a fourth list existed.
`test_every_root_file_a_dockerfile_copies_is_actually_packed_to_the_droplet` now DERIVES the set
from the Dockerfiles' own `COPY` lines and asserts each is in INCLUDE, and the tarball was then
opened to confirm the file is really in it — the artifact, not the code. Negative-tested.
RULE: when a change needs N edits, the check must DERIVE N from something authoritative. Counting
them by hand in a commit message is how the fourth one is missed.

**AND A CREDENTIAL DATABASE GOT COMMITTED.** `data/users.sqlite` appeared in the ship commit:
`user_store.db_path()` falls back to `<repo>/data/users.sqlite` when `USER_DB` is unset, and a test
run created it. It was empty (schema only, zero rows, verified before deleting), but a user database
must never be in git even so. Removed with `git rm --cached`; `data/` and `*.sqlite` are now
gitignored.

**THREE WIRING POINTS, NOT ONE.** `user_store.py` had to be added to `webapp/Dockerfile`,
`assess-bot/Dockerfile`, `cassandra-bot/Dockerfile` AND whitelisted in `.dockerignore` (which starts
with `*`). An image with colt_auth but not user_store would silently fall back to the shared
password for users who have their own. Asserted by a test that derives the list from the Dockerfiles.
**And the render audit's page list was hardcoded**, so Admin.jsx and ChangePassword.jsx were not
render-checked until they were added — `vite build` accepts an undefined identifier, which is how
/app once went white. Same for `test_routes.py`'s cabinet set, now DERIVED from Cabinet.jsx's
imports rather than listed.

## aminagroup.com — ONE `if not _nm:` SHIPPED ANOTHER COMPANY'S FIREWALL AS THE CRITICAL (2026-08-17)
AMINA Bank AG (Zug, FINMA-regulated digital-asset bank, formerly SEBA) received a deck where **four
of six findings were false positives, including the CRITICAL and the HIGH**, and the narrative
described a German manufacturer. An independent review re-verified every finding from RIR registry
data; I re-verified its central claim before changing anything:
```
83.111.84.114 -> inetnum 83.111.84.112/28  netname PERI-EMIRNET  descr "Peri llc"
                 P.O. Box 27933, Dubai, UAE   mnt-by ETISALAT-MNT   origin AS5384
114.84.111.83.in-addr.arpa -> NXDOMAIN (no PTR at all)
```
A German formwork manufacturer's UAE subsidiary, on Etisalat. C1 was their FortiGate.

**ROOT CAUSE, one line — `shodan_recon.run()`'s attribution gate:**
```python
_nm = _record_names(m)
if not _nm:
    _kept.append(m); continue     # no names at all -> cannot disprove ownership
```
`_record_names` requires a dot, so a record with no rDNS, no HTTP Host and no certificate names
returns the empty set. That is precisely what a FortiGate on :541, a bare Apache and a cPanel
:2087 look like — so C1 (PERI), H1 (smartTrade's own trading cloud) and L1 (a WHM port on WPEngine
shared hosting) were all waved through by the same branch.
**The block CONTRADICTED ITS OWN COMMENT FOUR LINES UP**, which says that when a customer owns no
ASN and no prefix "identity — a name or a certificate — is the ONLY evidence available". A record
with no names carries no identity. Keeping it is not "absence of evidence is never a finding"; it is
absence of any basis for attribution.
FIX — the fail-open now survives only where it was EARNED, behind two independent barriers:
  1. **No address space -> a nameless record is dropped.** (`asns` and `nets` both empty.)
  2. **A stranger's name already seen on this address -> no fail-open**, computed in a FIRST PASS
     before any decision. On 141.193.213.21 the gate dropped **323** records for naming strangers
     (nwpewaf.com and friends) and then kept a nameless one on the same IP. A guard whose baseline
     is computed while it is still consuming the untrusted input is not a guard.
It still protects the S-KON WatchGuard — a self-signed Firebox (cert `Firebox webCA`, no dotted
name) on S-KON's own Colt /29, i.e. a customer that DOES own space with no stranger on the address.

**THREE MORE DEFECTS, EACH A "TWO HOMES, ONE WIRED UP":**
* `ident["saas_tenancies"]` was written and **read by nothing**. The log decided
  `SaaS tenancy NOT pinned: autodiscover.aminagroup.io` and five lines later raised M2,
  `1 live name(s) covered by NO certificate: autodiscover.aminagroup.io`. It CNAMEs to
  `autodiscover.outlook.com`; Microsoft terminates TLS under its own certificate, so the customer
  has no certificate for it and is not supposed to. The sibling call `onprem_exchange(..., is_saas=)`
  already took the predicate; `uncovered_names()` on the next line never did.
* **THE HOSTER'S COUNTRY IS NOT THE CUSTOMER'S.** `_cc` was the dominant country of the ASN
  inventory — which, for an estate that is entirely Cloudflare/WPEngine/ti&m/Microsoft, describes
  the SUPPLIERS. Same rule already enforced for whois-org, cert-O and netblock holders, one level
  over. When the customer owns no space the ccTLD is the only country signal that is theirs, and a
  generic TLD means we do not know — which is honest, and makes the deck fall back to
  ISO 27001 / NIST CSF instead of naming a regulator that does not supervise them.
* **THE FP AUDIT WAS STRUCTURALLY INCAPABLE OF CATCHING ANY OF IT.** llama-4-maverick returned
  `verdict=dirty flagged=4 dropped=0 refused=4` — it flagged the false positives CORRECTLY and every
  flag was refused, because `audit_fp` grants immunity to anything in `scanned_ips` ("recon is the
  ownership authority") and the false positives were in `scanned_ips`. That premise holds only where
  recon HAD ownership evidence; on a no-space target it is circular. `vetted` is now empty unless
  the customer owns address space. Pins keep immunity unconditionally — their own DNS resolving
  there IS evidence. (`owned` gained `nets`: S-KON's ASN is refused as carrier space, so `asns` can
  be empty while the customer demonstrably owns address space.)

**THE PROMPT IS A STRING THAT REACHES A HUMAN, VIA THE MODEL** — recorded before, and this is the
sharpest instance yet. The asset-inventory slide lists ASN holders, so slide 5 read `Peri llc`. The
model recognised PERI as a German industrial manufacturer and built the sector, the jurisdiction and
the threat model on it: *"lower quartile of DACH manufacturing peers"*, *"NIS2 Article 21 for KRITIS
operators"*, GEOPOL driver *"German finance / KRITIS-adjacent"*, jurisdiction **BaFin/BAIT**,
rationale *"arms-to-Ukraine"* — at a Swiss bank. **One bad attribution became the narrative of three
decks.** `enrich.PROMPT` guardrail 5 now forbids inferring sector, country or regulator from
infrastructure holder names, and says to write sector-neutral prose naming only ISO 27001 / NIST CSF
when the findings do not state the sector. Citing the wrong regulator discredits every correct
finding beside it.

**WHAT THE ENGINE GOT RIGHT, for the record:** `onlinebanking.aminagroup.com` ->
**91.198.58.148** (Hypothekarbank Lenzburg, AMINA's Finstar core-banking provider — verified) was
filed as "resolves with no observable service" and NOT raised. That is the standing rule working:
Shodan holding no record is absence of evidence. The supply-chain concentration it implies is a
genuine gap in what we SAY, not a bug in what we claim.

Guarded by test_scope_abakus.py §14 plus a corrected §9. **§9's assertion was DELIBERATELY
INVERTED** — it read *"a record with NO names is kept - absence of evidence is never a finding"* on
a fixture with `asns=[] nets=[]`, i.e. it encoded exactly this defect. The old reasoning is kept in
the file, because deleting it would lose why. Five mutations run, each verified to fail with the
RIGHT assertion and then restored; 233 pytest + 7 engine suites green.
FIXTURE LESSON: my first barrier-2 fixture used org `"WPEngine, Inc."`, which carries no
hosting/datacenter marker and announces few prefixes — so `_looks_like_provider` never matched, the
gate never engaged, and the test failed against correct code. In the real run the trigger was
`_no_space`. A fixture that does not reproduce the condition under test is a test of the fixture.

### The re-run: 17 IPs -> 4, and TWO MORE DEFECTS ONLY THE ARTIFACT SHOWED (2026-08-17)
The fixes worked — PERI, smartTrade's WHM port and the WPEngine cPanel port are gone, CRIT 0, 339
records dropped by the gate, `country NOT inferred from the estate`, and the hallucination guard
stripped an invented CVE-2017-5638. Reading the delivered deck found two things the log could not:
1. **UNKNOWN IS NOT THE EU.** `build_findings_deck.js` had
   `else if (!cc || EU.indexOf(cc) >= 0)`, so a country the engine had DELIBERATELY refused to
   determine fell into the EU branch and the deck cited **NIS2 Art. 21 and GDPR Art. 32 at a Swiss
   bank**. NIS2 does not apply in Switzerland. Having just fixed the engine to stop adopting the
   hoster's country, the deck supplied the wrong jurisdiction anyway from the empty value — the
   fourth recurrence of D9/A7, this time hiding in the fallback. `!cc ||` removed; unknown now falls
   through to the jurisdiction-neutral set. VERIFIED BY RENDERING, not by reading the branch:
   UNKNOWN -> ISO 27001 / NIST CSF / KEV · DE -> NIS2 + GDPR + BSI · CH -> revFADP + NCSC-CH ·
   CA -> OSFI. Note CH already had a correct branch, so the neutral set is only ever reached when we
   genuinely do not know — and the operator can supply the country through the clarify/refine loop.
2. **"0 DROPPED FALSE-POS" on the methodology slide while the gate dropped 339 records.**
   `dropped` counted only honeypot and CDN drops; the attribution gate's tally was never added. The
   deck advertised that the false-positive machinery had done nothing on precisely the run where it
   did the most. A methodology slide that understates its own filtering is a credibility problem.
STILL OPEN, and it is a judgement call rather than a bug: H1's two evidence hosts (172.97.126.45 =
smartTrade Technologies AS18919, 62.12.132.67 = ti&m services AG AS15623) are AMINA's SUPPLIERS. The
records carry AMINA's names, so the attribution gate keeps them correctly — it is their application
on a supplier's platform. But the finding text says "directly from the corporate IP space" (it is
not), calls them "non-production" from a hostname inference presented as an observation, and the
remediation tells AMINA to put ZTNA in front of infrastructure it does not control. The title says
"(3 hosts)" while the evidence lists two and the prose says "three ... on the IP 172.97.126.45" —
three statements of the count, none agreeing.

## THE ADMINISTRATION PAGE COULD NOT ADD ANYONE — the gate refused its own purpose (2026-08-20)
First real use of the new page, and creating `feranicus@gmail.com` returned:
```
feranicus@gmail.com is not on the access list. Add the address or its domain to
colt_auth.PARTNER_EMAILS / PARTNER_DOMAINS first.
```
That refusal was mine, deliberate, and wrong. It meant the page whose entire purpose is to grant
access could only ever grant it to somebody a committed Python set ALREADY allowed — so adding a
genuinely new user was: edit code, commit, ship, come back. Operating principle 1 (no manual steps)
and principle 7 (one command) both, in the one screen built to avoid them. The test file even
encoded the mistake as doctrine: *"per-user passwords are a SECOND factor of authorisation, not a
replacement for the first"* — true as a sentence, and it made the feature useless.
It is also the "two homes for one decision" defect that this file keeps paying for (ENRICH_MODELS
had four; the language set had six). "Who may log in" was answered in `colt_auth.PARTNER_EMAILS`
AND in the credential store, and the newer home lost.
FIX: **`email_allowed()` gains a fourth source — an ENABLED account in `user_store`.** An
administrator deliberately creating a named account is a STRONGER and better-audited authorisation
act than the domain rule beside it: the row records who granted it and when, it names one person
instead of admitting everyone at a domain forever, and it is revoked on the same screen. The
committed lists are unchanged and still carry the bulk cases.
FOUR PROPERTIES, each negative-tested:
  * **disabled != authorised.** `_has_enabled_account()` reads `disabled`; `has_account()`
    deliberately does NOT (it counts a disabled row so that person cannot fall back to the shared
    password). The two look interchangeable and are opposites — using the wrong one turns "disable"
    into "take the password away and leave them authorised".
  * **fails CLOSED.** An unreadable store grants nothing; the committed lists still apply. The new
    source can only ever ADD, so a database problem cannot become a bypass in either direction.
  * **deleting withdraws access** for an address that is not otherwise listed.
  * **it does not weaken anything.** attacker@gmail.com, a suffix attack on a partner domain and a
    non-listed address at a partner's domain are all still refused.
The pre-check in `admin_create_user` is gone, with a test asserting `email_allowed` does not
reappear in that function — if it returns, the page stops being able to add anyone new.
RULE: before shipping a screen that grants something, try to grant something with it. The gate that
protects a feature must not be the thing that makes the feature impossible.

## WHITE LABEL / Proteus — a partner's own PowerPoint becomes the theme (2026-08-20)
A VAR, MSP or vendor uploads their template; every deck and HTML report they generate afterwards
carries their colours, fonts and logo. `proteus.py` is the engine (the god who takes any form while
remaining the same substance), "White Label" is the UI and the OEM agreement's word for it —
the same split as Perseus Shield over shield.py.

**MOST OF THIS IS PARSING, NOT AN LLM, AND THAT IS THE DESIGN.** A .pptx is a ZIP of XML: the exact
brand colours are in `ppt/theme/theme1.xml` (`clrScheme` dk1/lt1/accent1-6, remembering that dk1/lt1
are usually `sysClr` whose real value is `@lastClr`), the fonts in `fontScheme`, the logo in
`ppt/media/`, the organisation in `docProps/app.xml <Company>`. Asking a model to GUESS hex codes
would be slower, cost money, hallucinate a shade and answer differently every upload — the phantom
`deepseek-v4-flash` mistake one layer up. So there is NO model in `extract()`.
The panel answers only what parsing cannot: which accent is the brand vs decoration, which image is
the logo vs a stock photo, light or dark house style. Quorum of the models that answer, a vote naming
a colour that is NOT IN THE FILE is discarded, below two answers it falls back to a deterministic
heuristic — an upload must never fail because an inference account hit its quota.

**THE LUMINANCE RAMP IS THE PART THAT IS EASY TO GET WRONG.** The builders do not use one brand
colour, they use a triple: `teal` is a LIGHT accent carrying DARK text, `tealDark` is a DARK fill
carrying LIGHT text. Dropping a partner's navy into `teal` would put dark text on a dark fill on
every slide at once. So `ramp()` places the brand at the stop matching ITS OWN luminance and derives
the other two by binary search toward white/black to hit our reference luminances (0.52 / 0.29 /
0.07). Binary search, not a fixed step: luminance is a 2.4-power curve, so "lighten by 20%" lands
somewhere different depending on where you start, which is how a lighter shade comes out darker than
the one below it. Verified across eight brands including pure white and pure black: every ramp
ordered, every stop ≥4.5:1.

**brand.js MAPS BY VALUE, NOT BY KEY**, which is what makes it small. Any default whose VALUE is one
of our three stops is a brand surface wherever it appears, so `teal`, `tealDark` and `evBg:"0C544E"`
are themed for free while crit/high/med/low/ink/divider are untouched because their values are not
in the ramp. **Severity colours are ENUMS**: a partner whose brand is red does not get green
criticals, and that property now holds by construction rather than by a list somebody maintains.
One `require` + one wrapped `{...}` + one `BRAND.mark()` per builder — the deck_i18n doctrine, which
was written after a failed attempt to hoist 530 literals: translate (here, re-colour) at the
boundary, never fork the builders.

**FOUR THINGS THE MEASUREMENTS CHANGED, all of which would otherwise have shipped:**
1. **A 263 KB logo turned a 498 KB deck into 5.2 MB.** pptxgenjs writes a separate `ppt/media` entry
   per `addImage`, so an 18-slide deck carries 18 copies. The first cap was 4 MB = a 72 MB artifact
   nobody can email, with nothing saying why. Now 150 KB, and the arithmetic is in the refusal.
2. **Two real templates reported their author as "PptxGenJS" and "Steve Canny"** (a rendering
   library, and the author of python-pptx). Either would have gone on a partner's title slide. And
   `dc:title` produced the wordmark "Why Redevco Needs Breach & Attack Simula". Only `<Company>` is
   used; otherwise the field stays EMPTY and a human types it. Metadata is a suggestion, never a
   value we put in front of a customer unconfirmed.
3. **A 1200x800 PHOTOGRAPH was adopted as the logo** by the first heuristic (anything referenced
   with an aspect over 0.5). Caught by the API test. On the slide MASTER is decisive; otherwise a
   logo is wide (>=1.2) and under half a megapixel.
4. **A template still on the stock Office palette** is reported as carrying no brand colour rather
   than confidently themed in Microsoft's default blue.

**SECURITY.** The upload is an attacker-shaped ZIP: total and per-member uncompressed sizes are
checked BEFORE any member is read (the cap is on the compressed file; a 25 MB zip can declare 10 GB).
Logos are validated from the HEADER — magic bytes plus declared dimensions — with no image-decoding
library added, because a decoder is a large new attack surface for a small job and every dependency
is one Trivy reports on forever. **SVG is refused outright**: it carries script and external entities
and would be inlined into the animated HTML report. `python-multipart>=0.0.18` is pinned
deliberately (CVE-2024-24762 ReDoS, CVE-2024-53981 DoS), not merely "latest".

**STORAGE IS ON THE SHARED `colt_events` VOLUME**, like cost_ledger.sqlite and users.sqlite, so a
Telegram-initiated assessment renders in the same branding as one from the cabinet. `colt_webdata`
is the obvious home and is WRONG: only colt-web mounts it, and the bots would silently produce
unbranded decks. `BRAND_THEME` is set ONCE in `_run_job`/`bot.py` and every builder subprocess
inherits it, so five artifacts cannot come out half-branded. **The uploaded .pptx is NOT kept** —
we have taken a palette, two font names and one image, and keeping customer files we have no use for
is storage we would have to defend, disclose and delete on request.

**THE GATE (`scripts/test_white_label.py`, blocking in ship.py) BUILDS REAL DECKS AND READS THEM
BACK**, because the colour arithmetic being right is not the deck being right. Two of its assertions
protect EXISTING customers rather than partners: **an unbranded build is byte-identical, on all 18
slides, to one from before this feature existed**, and severity counts are unchanged. Also: all
189/231/230 branded surfaces mapped with zero of our stops surviving, our wordmark reduced from 18
occurrences to the single attribution line, the logo actually embedded, and an unreadable or missing
theme degrading to OUR palette rather than failing the run.
MEASUREMENT NOTE: completeness is measured against a NO-LOGO theme deliberately. With a logo the
counts legitimately differ because the image REPLACES 18 brand-coloured wordmark text elements — my
first assertion conflated "was every surface mapped" with "did the logo replace the wordmark" and
failed on correct code.

## THE UPLOAD BUTTON SPUN FOR EVER AND THE PAGE COULD NOT SAY WHY (2026-08-20)
First real use of White Label: "Reading your template…" and nothing else, ever. The operator's own
preview log had the answer in it:
```
2:27:00 PM [vite] http proxy error: /api/brand
Error: socket hang up
```
THREE defects, and the first is the one that matters:
1. **`setBrand` had no error path.** The preview's read-only rail destroys an unlisted write, the
   fetch REJECTS, and the exception propagated out of `submit()` before `setBusy(false)` ever ran.
   So the one thing the page could not do was tell you it had failed. Any `await` on a network call
   in a handler that sets a busy flag needs a `catch` that clears it — a rejected fetch is not an
   error response, it is no response at all, and `r.ok` is never reached. A test now asserts every
   exit from submit/poll clears the flag.
2. **`/api/brand` was not on the preview's ALLOW_WRITE list**, so the one page you would open the
   preview to test was the one page that could not work there. Same trap that created the list:
   uploading a brand costs nothing, consumes no quota, touches nobody else's account and is undone
   by "Remove branding". Added, with the reasoning next to it.
3. **A minute of silence is indistinguishable from a hang.** With the panel on, four models at a 45s
   timeout is up to a minute even in parallel. That is exactly what the assessment progress bar
   exists for, and this had a spinner.
NOW: `POST /api/brand` returns a JOB and the work runs in an executor; the page polls
`/api/brand/job/{id}` and shows a bar plus a log — which model answered, which is still out, what
was decided. **The failure path ALWAYS reaches done=100** (a `finally`), because a job that never
finishes is the original defect wearing a different hat.
- **POLL, NOT SSE, deliberately.** The assessment stream is minutes long, resumable and survives a
  phone locking, which is what justifies EventSource + Last-Event-ID + a reconnect path. This is
  under a minute with the page open in front of the person who started it; a poll has no reconnect
  semantics to get wrong, and `since` keeps each response to the new lines only.
- **THE PANEL IS NOW PARALLEL.** Four models at 45s serially is up to THREE MINUTES; in parallel the
  wall clock is the slowest model. They are independent by construction — same question, same file,
  none sees another's answer — so there was nothing to serialise. Measured 0.31s vs 1.2s on a stub.
  Vote order is re-sorted to the chain order afterwards so a tie-break cannot depend on who
  answered first.
- **`brand.precheck()` — ONE implementation, TWO callers.** The cheap refusals (not a zip, not a
  deck, a zip bomb, a bad logo) are milliseconds, so they answer synchronously with a 400 and a
  reason instead of becoming a job you have to watch to learn it was never going to work. `save()`
  calls it too: an endpoint that validated separately would drift from what save() accepts, and a
  save() that trusted the endpoint would be unsafe called from anywhere else.
RULE: any handler that sets a busy flag before an `await` must clear it on EVERY path, including a
rejected promise. And any operation that can exceed a few seconds needs a phase feed, not a spinner
— the operator cannot tell "working" from "stuck", and neither can you.

## A DECLARED DEPENDENCY THE OPERATOR'S PYTHON DID NOT HAVE — the SIXTH instance (2026-08-20)
`python ship.py` refused to deploy on 21 failures, every one of them:
```
RuntimeError: Form data requires "python-multipart" to be installed.
```
White Label's upload needs multipart, it is declared in `webapp/backend/requirements.txt`, and the
DROPLET has it because the Dockerfile pip-installs that file. Nothing ever installed it on the
machine that runs the tests — and the test suite IMPORTS the FastAPI app, so every test that
touches main.py died on a message that reads like a code defect and is not.
I installed it in my own sandbox and never on his. Green here, red there.
SAME ROOT CAUSE AS: the httpx incident, the esbuild/win32 incident, the `os.uname()` incident, and
the three wasted ships already recorded under "A CHECK MUST RUN WHERE THE TOOLCHAIN IS CORRECT BY
CONSTRUCTION". The rule was written down four times and broken a fifth, so it is now CODE.
FIX — `ship.py::ensure_app_requirements()`, called at the TOP of the test phase, before any test
can import the app. It is the same remedy ship.py already applies to ruff, and for the same reason:
telling the operator to run pip is a manual step (operating principle 1) and will be forgotten by
whoever clones this next.
  * DELIBERATELY NARROW: only packages MISSING ENTIRELY are installed, never upgraded. A blanket
    `pip install -r requirements.txt` on a developer machine can move fastapi or starlette under
    whatever else lives in that interpreter — a bigger problem than the one being solved. Version
    drift is answered by the image build, which installs from a clean base every time.
  * `tests/test_security_headers.py` gained a companion assertion so a BARE `pytest` run fails
    legibly, naming the package and the fix, instead of raising from four frames inside a route
    decorator.
**AND MY FIX HAD THE REPO'S FAVOURITE BUG IN IT.** The first version called `importlib.metadata`
in ship.py's OWN interpreter — which measures the wrong subject. A negative test in a clean venv
proved it: it reported `google-auth` missing (true only in my sandbox) and MISSED
`python-multipart`, which was the entire point of the change. It now runs the probe INSIDE the
target interpreter with `subprocess`. Same defect class as validating a temp copy instead of the
mounted file, and as `cmd_selftest` reading the production path on staging.
VERIFICATION THAT ACTUALLY PROVES IT: a clean venv with the app's dependencies EXCEPT
python-multipart — i.e. the operator's box reproduced — then app import fails with his exact error,
`ensure_app_requirements(py)` installs exactly one package, app import succeeds, and a second call
prints nothing.
RULE, now enforced rather than written down: when a change adds a runtime dependency, the machine
that runs the tests has to get it automatically. Ask "which interpreter?" before every probe.

## THE BRAND IS NOT IN THE THEME — a generated deck keeps it in the SHAPES (2026-08-20, S4biz)
The operator uploaded the S4biz capability brief and every artifact came back in **#4472C4 —
Microsoft's default Office blue** — for a company whose brand is cyan. All four panel models chose
that blue, and **all four were right about the wrong evidence**, because the theme slots were the
only thing I showed them. This is an evidence-gathering bug of mine, not a model failure.

MEASURED ON THE REAL FILE:
```
ppt/theme/theme1.xml  accent1..6 = 4472C4 ED7D31 A5A5A5 FFC000 5B9BD5 70AD47   <- stock Office 2013
ppt/slides/*.xml      #C7CDDA x89  #22D3EE x77  #FFFFFF x69  #8B5CF6 x62  #4F46E5 x41  #2B3042 x57
```
**THE ASSUMPTION THAT WAS WRONG:** "a partner's brand lives in `theme1.xml`". True for a deck
authored FROM a corporate PowerPoint template. FALSE for a deck produced by a GENERATOR —
pptxgenjs, python-pptx, a Canva / Figma / Google Slides export — which leaves the stock theme
untouched and paints every shape with an explicit `<a:srgbClr>`. That is not an edge case; it is
what every design-led company's deck looks like, and it is what OUR OWN decks look like.
CLAUDE.md already recorded doing this by hand ("the S4BIZ COLOURS WERE COUNTED, NOT SAMPLED...
tallied every srgbClr across every slide: #22D3EE cyan (77)") — I did the right thing once
manually and then did not build it into the tool.

FIX, in three parts, and the middle one is the subtle one:
1. **`extract()` harvests the colours the slides, layouts and masters actually paint with**, with
   counts. Both sources are now on the table.
2. **CHROMA FILTERS BEFORE FREQUENCY ORDERS.** The most-used colour in that file is #C7CDDA at 89
   uses — a pale grey-blue hairline. Ranking by frequency alone would have made THAT the brand,
   which is a worse answer than the blue. `is_brandable()` requires HSV saturation >= 0.35 and
   luminance in 0.05..0.85, which drops the greys, the white and the near-black page backgrounds
   (#14161F, #1B1F2C, #2B3042 are saturated enough to pass chroma on their own).
3. **THE SOURCE IS CHOSEN, NOT AVERAGED.** A CUSTOM theme is authoritative — somebody set those
   accents on purpose. A STOCK theme states nothing, so the shapes are authoritative instead.
   `brand_candidates()` returns one list with the evidence for each entry ("theme accent1" /
   "used 77 times in the slides") and the heuristic takes the first.
AND THE PANEL IS SHOWN ALL OF IT: `_facts_for_panel` now prints the slide table with counts and
says outright when the theme is stock; `judge()`'s `allowed` set was widened to include the slide
colours, because showing the models the evidence is useless if the answer they give from it is
then discarded as "not one of the file's colours". Both halves were needed.
RESULT on the real brief, from the DETERMINISTIC path alone: **#22D3EE**, no panel required.

ALSO FIXED, same file: every image in that deck is a 1920x1080 full-slide render (it was exported
picture-per-slide), so the logo rule correctly refused all of them — and said nothing, which reads
as the feature being broken. It now explains that there is no mark in the file and to upload one.

RULE: when a model gets something wrong, check what it was SHOWN before concluding it was wrong.
Four vendors agreeing on a bad answer is much more likely to mean the evidence was bad than that
four independent models failed the same way.
Guarded by test_proteus.py: the stock-theme-plus-painted-shapes shape yields the cyan, frequency
alone would have picked the grey, a CUSTOM theme still beats the slides, the panel may vote for a
slide colour, a colourless deck says so, and full-slide renders are refused WITH a reason.

## THE GATE PASSED AND THEN DIED PRINTING ITS OWN PASS (2026-08-21, cp1252)
The engine i18n gate reported PASS for all 237 German strings and all 237 Russian ones, and then:
```
  PASS ru: composed titles translate (template + product + host count)   0 of 33 fail
  UnicodeEncodeError: 'charmap' codec can't encode characters in position 65-68
[X] ENGINE i18n REGRESSION - a document language we advertise would ship English finding text.
```
**Every translation was correct.** A Windows console is cp1252, the check prints WHAT IT COMPARED,
and for Russian that detail is Cyrillic (`singular 'хост' vs plural 'хостов'`) — so `print()` raised,
the gate exited non-zero, and ship.py blamed the translations. The operator's reply was "полная ж".
TWO SEPARATE DEFECTS:
1. **The gate depended on the console encoding.** SIXTH instance of the root cause this file already
   records under "A CHECK MUST RUN WHERE THE TOOLCHAIN IS CORRECT BY CONSTRUCTION" (httpx,
   esbuild/win32, `os.uname`, python-multipart, …): validated in a UTF-8 sandbox, handed to the
   operator's box. Fixed at the ONE place that launches every gate — ship.py sets
   `PYTHONIOENCODING` (read at interpreter start, so it affects CHILDREN) **and** reconfigures its
   OWN streams (it prints the children's captured output). Both halves are needed; neither alone is
   enough. The gate also reconfigures itself, for anyone running it directly.
2. **ship.py could not tell a CRASH from a FINDING.** A check that raised has said NOTHING about its
   subject, and reporting it as a defect in the subject sends the next hour down the wrong road.
   `gate_failed()` now distinguishes them: a traceback with no verdict line prints
   "THE … GATE CRASHED - this is NOT a finding about …" and names the exception.
RULE: **a gate must be able to render its own PASS on the operator's console.** A check that blocks
a good deploy and names the wrong culprit is worse than no check.
Guarded by `tests/test_console_encoding.py`, which REPRODUCES the console (`PYTHONIOENCODING=cp1252`)
rather than reasoning about it, and asserts both directions of the crash/regression message. Four
mutations, each verified to fail and restore — including one that "fixes" the crash by DROPPING the
Cyrillic evidence, which is silently losing the thing the check exists to show.

## TWO CONTAINERS, ONE COMMIT, DIFFERENT BYTES — and the verify said they matched (2026-08-21)
From the 2026-08-20 ship log. One `python ship.py`, one commit, and the two containers it deployed
ended up running different engine files:
```
scripts/proteus.py        colt-web fbed443dfcea   colt-assessbot 26ab2bf3a805
scripts/creed.js          colt-web 472e6a8c7985   colt-assessbot 73c14617e33c
scripts/pptx_preview.py   colt-web 0b111a71374d   colt-assessbot MISSING
```
and directly underneath that list the run printed **`OK  colt-assessbot engine matches the repo`**.
Local hashes were measured afterwards: all three match colt-web, so the BOTS were the stale side.

**CAUSE 1 — THE TWO PATHS PACKED DIFFERENTLY.** `deploy_web_direct.py` packs `git archive HEAD`
with `core.autocrlf=false` (repository bytes, immutable commit). `deploy.py` tar'd the operator's
WORKING COPY. On Windows git checks files out with CRLF, so the SAME commit hashes differently
through the two paths, and any uncommitted edit shipped to the bots only. The promise recorded in
this file — *"packing the COMMIT … staging and prod get identical bytes"* — was true of the web app
and false of the bots, which is precisely the disagreement the engine-hash verify exists to detect.
FIX: ONE mechanism, TWO scopes. `pack(include=…, extra=…)` is the only implementation; `deploy.py`
passes `BOTS_INCLUDE` (compose + both bot Dockerfiles + obs/, none of which the web tree contains).
Sharing the FILE LIST would break the bots build outright — the shareable thing is the mechanism.
**The secrets split is deliberate:** `assess-bot/.env` is gitignored, so `git archive` can never
contain it and packing only the commit would have SILENTLY stopped shipping runtime secrets — a
behaviour change smuggled in as a side effect of a determinism fix. `extra=BOTS_SECRETS` adds it
on top. Code from the commit, secrets from the machine.

**CAUSE 2 — THE PRINTOUT WAS NOT THE COMPARISON.** The verify dumped the remote probe's raw output
and printed a verdict computed separately, so the human read one thing and the gate decided on
another. Reproducing `engine_is_current()` against that exact output returns ok=False, which means
the two were never looking at the same data. RULE: **print the comparison you made, never a raw
dump plus a conclusion** — `print_engine_comparison()` renders file / container / repo per line, so
a MISSING physically cannot sit above an OK. The probe is now `echo=False`.
Two silent-pass holes closed in the same function: a file absent from the REPO used to `continue`
(the gate shrinking itself without saying so — absence of evidence is never a pass), and an EMPTY
probe (ssh throttled) was indistinguishable from a match; both now fail with a named reason.

Guarded by `tests/test_deploy_parity.py` (9 tests): both packs must agree on the files that really
diverged, the bots pack must contain what the bots build from, the web pack must NOT be widened to
the bots tree, untracked secrets must still ship, and the three gate holes must each fail.
**AND MY OWN ASSERTION MATCHED ITS OWN COMMENT — the fourth time in this repo.** The
`core.autocrlf=false` check grepped the raw file, and the paragraph explaining that flag contains
the string, so deleting the real arguments left the comment behind and the check passed against a
file carrying the exact defect. Strip comments, then assert. Seven mutations, each verified to fail
and then restored.
**A `finally` STILL CANNOT SURVIVE A KILL:** the mutation harness was timed out mid-run and left
`core.pager=cat` in deploy_web_direct.py. Found only by scanning for EVERY marker the harness could
have written rather than eyeballing a diffstat — same lesson as the `TRANSIENT EDIT` incident.

## A COMPOSED STRING IS NOT A DICTIONARY KEY — 60% of the engine shipped in English (2026-08-21)
bottomline.com received a GERMAN deck with English finding titles on three of ten slides. Measured
across the packs: **15 of 33 TEMPLATES titles and 143 of 237 customer-visible engine strings had no
translation in EITHER German or Russian**, and every one belonged to a detector added after the
packs were written.
ROOT CAUSE: `shodan_recon` builds every title at render time as
`"<template title><extra> (<n> hosts)"`, so the string that reaches `t()` can never be a key. The
packs worked around it with ONE HAND-WRITTEN REGEX PER DETECTOR PER LANGUAGE — a second and third
edit, in two other files, that nothing asserted. So it was forgotten every single time.
FIX — translate the PARTS, not the whole: `_composed()` sends the head through the dictionary
(where the plain template title already lives), leaves the product name alone as a proper noun, and
renders the host count from the pack. **THE SPLIT POINT CANNOT BE GUESSED BY ONE REGEX** and my
first version proved it: several titles CONTAIN an em dash ("No CAA record — any certificate
authority may issue…"), so a non-greedy head split at the wrong one; a greedy head fails the
opposite way when a product IS appended. Try the candidate splits and take the one the dictionary
recognises — the regex proposes, the dictionary decides. 23 legacy regexes deleted per pack; a new
detector now needs its plain title translated and nothing else.
- **THE PACK DECLARES ITS OWN GRAMMAR.** The old regexes hardcoded the plural, producing "(1 Hosts)"
  in German and "(хостов: 1)" in Russian. `_plural()` applies the Slavic three-form rule when the
  pack supplies `few` and one/other otherwise. Hardcoding "add an s" is an English rule applied to
  every language; hardcoding the Slavic rule is a Russian rule applied to German.
- **INLINE LABELS NEED THEIR OWN PASS.** A remediation body reads "WHY THIS SERVICE: … WHAT YOU GET:
  … HOW: …". `t()` RETURNS ON THE FIRST PATTERN THAT MATCHES, so as ordinary patterns one label
  would be translated and two left English. They shipped in English 11 times in one deck.
- WHY IT STAYED INVISIBLE: the model writes over most of these strings on a good run. The gap only
  shows on findings the enrichment did not reach — i.e. the runs where the customer is already
  getting less. **/api/langs is a CAPABILITY CLAIM**: advertising a document language means the
  DETERMINISTIC path renders in it, not just the model's prose.
GATE: `test_engine_i18n.py` (blocking) asserts, per advertised language, that every TEMPLATES
title/why/rem translates, that the real COMPOSED shape translates (not just the plain template —
the plain template being present is what everybody assumed and is not what reaches the slide), that
the count is declined, that each label is translated, and that English is byte-for-byte unchanged.
**MY OWN PLURAL CHECK COULD NOT FAIL.** It compared the two rendered titles and required "(1 " to
appear — which "(1 Hosts)" satisfies perfectly — so it PASSED against a pack mutated to exactly the
defect it is named for. It now compares the NOUN. Nth instance of a check aimed next to its subject.

## THE CONTRACT DID NOT FIT THE BOX — 46 truncated text boxes (2026-08-21)
Same deck, extracted: **46 text boxes ended in an ellipsis**, including a remediation title reading
"Managed SASE/SSE mit ZTNA — Entfernt die öffentliche…". Nothing was broken. `fitText` trims on a
word boundary when text exceeds its box, and the ARITHMETIC had never been compared:
  * `why` box holds **243 chars**; the bible demanded three full sentences (~450).
  * `rem` body holds **370 chars at three rows and 148 at five**, because `rowH` is adaptive
    (`min(1.05, (5.24-2.06)/rows)`) — the bible asked for 3-5, so asking for five was asking for a
    third of the space per row. Five entries is not more content, it is the same content truncated.
  * `enrich.py` then applied a BLUNT `[:120]` / `[:400]`, above the box and mid-word, so the text
    was truncated TWICE, neither time readably.
FIX: `REM_ROWS = 3`, budgets stated in `LLM_DELTAS_BIBLE.md` so the model is told what it has (with
the note that German and Russian run ~30% longer), and `_clamp()` cutting on a SENTENCE boundary.
A sentence that does not fit WHOLE is DROPPED, not trimmed — two complete thoughts read better than
two and a half, which is the entire reason for doing this here instead of letting the deck cut. A
TITLE is cut at its separator, because the service NAME is what the row is for. The last-resort
word cut appends an ellipsis rather than a full stop: a fabricated sentence end tells the reader the
thought finished when it did not.
**THE PATH THAT BUILT THIS DECK APPLIED NONE OF IT.** `enrich_parallel.apply()` copied the model's
fields on VERBATIM — no tag validation, no row cap, no clamp — and it is the path that runs whenever
the monolithic call fails, which is most large estates. Same normalisation, two homes, one wired up.
`enrich.normalise_prose()` is now the only implementation and both paths call it.
GATE: `test_deck_quality.length_budgets()` DERIVES the capacity from `build_findings_deck.js`, so
moving a box fails the build instead of silently re-opening this; it also asserts the bible states
the same numbers (a budget the model is never told about is one it cannot meet) and that BOTH paths
enforce them. Five mutations, including `REM_ROWS = 5` and the old 450-char `why`, each verified to
fail by name and then restored.
ALSO: every shard was sent to `_chain[0]`, so four parallel calls shared ONE failure domain — on
this run the head model had just burned its full 175s cap in the serial chain returning nothing, and
all four shards then timed out together at 150s before the targeted retry could start. The rule that
a backup must be a DIFFERENT VENDOR was written for the serial chain and never carried across to the
shards. Round-robin bounds a vendor's bad minute to 1/N of the work.

## WHITE LABEL, THE SECOND PASS: a colour table the mapping never saw, and stock fonts (2026-08-20)
The cyan fix worked and the delivered deck still was not right. Reading the ARTIFACT found two more,
both the same disease one level down.

**1. OUR TEAL LEAKED ONTO A PARTNER'S DECK: `00D7BD` x11 and `0C544E` x11 survived.**
`brand.js::palette()` maps BY VALUE, which is what makes it small — but it only ever saw the object
passed THROUGH it. `build_findings_deck.js` has a SECOND colour table:
```
const tagMap = { VENDOR:[...], COLT:["00D7BD","121212"], PSF:["0C544E","FFFFFF"], OSS:[...] };
```
Eleven remediation chips, eleven of our teal, on a partner's customer-facing report.
FIX: `recolor()` walks strings, arrays and nested objects, and `tagMap` goes through it. Mapping by
value is right; mapping by value in ONE PLACE is not. `creed.js` also carried the RETIRED Colt teal
`00B2A9` as a dormant default — replaced.
**AND THE GATE PASSED ANYWAY**, because `findings.sample.json` produces no finding with a COLT or
PSF tag. A gate is only as good as the shapes its fixture contains — the same lesson the brand gate
already taught when it missed a LOW/COLT row. The gate now injects one chip of each tag, and a unit
test asserts NO builder holds a reference stop outside something `BRAND` maps.

**2. THE FONTS WERE MICROSOFT'S, PRESENTED AS THE PARTNER'S.** The White Label page read
"Fonts: Calibri Light / Calibri" under the heading "Colours read from your template". Those are the
STOCK Office font scheme, exactly as the accents were. Harvesting the slides does not rescue this
one: the S4biz brief's shapes use Arial / Arial Black / Consolas, which are the GENERATOR's
fallbacks, not a brand typeface. So the honest answer differs from the colour case:
`_fonts_for()` uses a face only when it is DISTINCTIVE (not in a generic/system list, not a `+mn-lt`
theme reference); otherwise it keeps OUR fonts and says the file carried no brand typography.
Dressing a system font up as the partner's is the same false claim as reading a brand colour out of
a stock palette, and "absence of evidence is never a finding" applies to typography too.

TWO FIXTURE DEFECTS OF MINE, both found by the tests failing against CORRECT code:
  * the STOCK theme fixture swapped only the COLOURS, so it still carried "Gill Sans MT" — the font
    assertion was measuring a file that genuinely had a brand typeface. A stock deck is stock all
    the way down.
  * the "no stop outside the mapping" test stripped `BRAND.recolor({...})` but not
    `BRAND.recolor("...")`, which is how creed.js passes a single value.
RULE, restated: when a partner's artifact is wrong, read the ARTIFACT. Both of these were invisible
in the theme.json and in the White Label page, and obvious in thirty seconds of counting colours and
typefaces in the delivered .pptx.
