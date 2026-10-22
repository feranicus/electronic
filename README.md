# electronic

The platform behind **cybergod.ai**. An external attack-surface assessment engine, a web app, two
Telegram bots, and the automation that ships all of it.

One input goes in, a company name. The engine finds what that company exposes to the internet using
public records only, grades the risk, writes the prose with four different vendors' models, and
returns a set of decks. Not one packet is sent to the company being assessed.

Two droplets, nine workflows, one orchestrator, 1,179 automated checks, and four models that never
decide anything.

| | |
|---|---|
| [A. The estate](#a-the-estate) | two droplets, what runs on them, and the twin that gets rebooted |
| [B. How it ships](#b-how-it-ships) | the one command, why CI exists, the five jobs, every workflow, the clock |
| [C. What must pass](#c-what-must-pass) | the gate battery and the suite, grouped by what each part defends |
| [D. The models](#d-the-models) | four vendors, what stops a confident wrong answer, and what the spend controls are |
| [Day one](#day-one) | six commands, in order, none of which need permission from anyone |

---

# A. The estate

## Two droplets, built identical on purpose

| | production | staging twin |
|---|---|---|
| region and size | FRA1, 4 GB, 2 AMD vCPU, 80 GB, Ubuntu 24.04 | the same, deliberately |
| what it runs | the live product | the release gate |
| proxy | the shared `videodead-caddy-1` on :443 | its own `staging-caddy` on :8080 |
| deployed by | `deploy_web_direct.py` | the same script, with `DROPLET_HOST` set |
| rebooted | never, to prove a config | on every ship |

A twin that differs in region or size is not a twin. Latency to the inference endpoint, host
hardware generation and kernel line are exactly the variables that make "it worked in staging"
untrue. The addresses of both machines are in `CLAUDE.md`.

The production droplet is still named `ubuntu-s-1vcpu-1gb-fra1-01` because that was its size when
it was created. Read the spec, never the name.

## What actually runs on production

```
                  INTERNET
                     |  :443
            videodead-caddy-1          shared reverse proxy, owns :443 for six domains
                     |                 network: videodead_appnet
                 colt-web              FastAPI + React, 127.0.0.1:8090 -> 8000
                                       image: .../electronic/colt-web:<sha>

   network: colt (its own)
       colt-assessbot                  Telegram, /assess. Same engine image, second delivery path
       colt-cassandra                  Telegram assistant
       colt-promtail                   ships logs to the shared Loki

   VOLUME colt_events  ->  /var/log/colt
       colt.sqlite          jobs and users
       cost_ledger.sqlite   the books of record, one row per completed assessment
       llm_meter.sqlite     the daily spend cap
       events.log           telemetry, shield, fleet
```

Two things on that box are shared, and therefore fragile. `videodead-caddy-1` owns :443 for every
domain, so its death is a total outage and never an application fault. `videodead-loki-1` is the
only thing holding the past; open sockets and container start times cannot answer a question about
yesterday.

The host also carries Amnezia VPN, VideoDead, jobhuntwow, jev, klima and s4biz. None of them are
ours to disturb, and nothing here changes a firewall rule.

Secrets never travel through git. They live in `assess-bot/.env` on the droplet at mode 600, and
the staging gate copies that file from production to the twin over SSH. To change one:

```
python set_secret.py NAME        # value on STDIN, never in argv
```

## The twin, and the decision it produces

The twin receives the same commit, the same image, and the committed Caddy block, then:

```
deploy the commit  ->  42 deterministic checks  ->  REBOOT  ->  all 42 again as post_reboot_*
```

The reboot is the point. Caddy reads its configuration only at start. On 2026-08-14 a deploy
truncated the shared Caddyfile at 16:15 and nothing failed for twelve hours, until a 04:22 kernel
reboot made it re-read the file and six domains went down together. Production can never be
rebooted to prove a config. The twin can.

The gate waits for the `boot_id` to **change**, not merely for SSH to answer. A check that reported
before the reboot and goes silent afterwards fails the gate. Thirty-five of thirty-five passing
while six checks never reported is the defect that bought that rule.

Two soldier models and two auditor models then write a verdict. The GO or NO-GO is computed from
the deterministic checks alone. The panel can turn a GO into a NO-GO. It can never turn a NO-GO
into a GO.

---

# B. How it ships

## The one command

```
cd "C:\Python SW\Linkedin Scraper"
python ship.py
```

Five numbered phases, with the staging gate between two and three:

| phase | what it does |
|---|---|
| 1/5 TESTS | the gate battery. Nothing ships if any of it fails. |
| 2/5 COMMIT + PUSH | git is the single source of truth, so the commit happens before any deploy. |
| STAGING GATE | the twin, the reboot, 42 checks twice. NO-GO exits 2 and production is untouched. |
| 3/5 DEPLOY WEB | cybergod.ai (`colt-web`). |
| 4/5 DEPLOY BOTS | `colt-stack`, the assessment bot and Cassandra. |
| 5/5 VERIFY | container hashes, `GET /api/me` returns 401, security headers, the bot gate. |

After phase five, a tail that runs on every ship: `caddyguard.py` reassembles and validates the
shared proxy and can fail the run; `perseus.py --install-only`, `dbbackup.py`, `logship.py`,
`secaudit.py` and `model_watch.py` never block; the commit is tagged `last-known-good` and
`good-YYYYMMDD-HHMMSS` and both are pushed; then four models write the release notes, which are
sent by Gmail API and Telegram.

### Flags narrow it. They never split it.

| flag | effect |
|---|---|
| `--test` | the gate battery only, change nothing |
| `--web` / `--bots` | deploy one half |
| `--pr` | branch, PR, wait for the gate, squash-merge, then stop. The merge is the deploy. |
| `--direct` | deploy straight to the droplet over SSH. This is the default. |
| `--ci` | route the deploy through Actions instead of SSH. Your laptop still drives it. |
| `--no-stage` | skip the twin |
| `--fast-stage` | validate on the twin but skip the reboot, which is the weaker half |
| `--dry-run` | print every command, touch nothing |
| `--no-preview` | ship a frontend change without previewing it |
| `--no-test` | skip the gate battery. You had better have a reason. |
| `--rollback [REF]` | restore `last-known-good` or a dated tag and redeploy it |
| `--fix-ci-key` | prove the deploy key works, then write it to the GitHub secret |
| `-m "message"` | commit message, also quoted in the release notes |

`--pr` and `--ci` sound alike and are not. `--pr` hands the deploy to CI and your machine deploys
nothing. `--ci` keeps the deploy yours and changes only how it reaches the droplet.

## Why CI exists

Until October 2026 every deploy to cybergod.ai began on one Windows PC in one room.

**Before.** `python ship.py` ran the tests, built the image *on the production droplet*, deployed it
and verified it. Three consequences nobody chose: the only internet-facing image in the stack was
the one image CI never saw, a second developer could not deploy without that PC, and "it passed on
my machine" was the only evidence there was.

**After.** A push to `main` starts five workflows. One of them, `pipeline.yml`, is the deploy. The
image is built once by CI and scanned there, staging and production pull those bytes by immutable
tag, and the laptop is one way in rather than the only way in.

**What deliberately did not change.** CI does not re-implement the orchestrator. It calls this
repository's own scripts as subprocesses: `ship.py --test`, `stagegate.py`, `deploy_web_direct.py`,
`caddyguard.py`. There is one definition of what a gate means and one definition of what a deploy
does. A YAML copy of those gates would drift within a week, and the drift would stay invisible
until it mattered.

## What one push starts

Five workflows, in parallel, answering different questions:

| workflow | what it is |
|---|---|
| `pipeline.yml` | the deploy. Five jobs, roughly twelve minutes. |
| `ci.yml` | the gate of record: `quality-and-secrets`, which is gitleaks plus `ship.py --test` |
| `codeql.yml` | GitHub code scanning, also weekly on Tuesdays |
| `security.yml` | Trivy filesystem and IaC, hadolint, pip-audit. Also Mondays. Report only. |
| `import-dashboards.yml` | re-imports the Grafana dashboards when they change |

**Only one of them can deploy.** `deploy.yml` and `web-deploy.yml` still exist and are now
`workflow_dispatch` only, because one push used to fire two of them and produce two deploys to one
droplet six minutes apart.

**The gate of record is separate on purpose.** GitHub's branch ruleset names exactly one required
check, `quality-and-secrets`, and it lives in `ci.yml`. The pipeline's first job does not re-run it.
It waits for that exact check on that exact commit. Two definitions of "green" would eventually
disagree.

**A required check cannot be satisfied by a direct push.** GitHub's own rule is that checks must
pass before a collaborator changes the branch, and a brand-new commit has no check runs yet. That
is the `Bypassed rule violations` line on every direct ship. `python ship.py --pr` is the answer,
because a pull request's head commit does get check runs. Nothing merges on an unknown state, and
`skipped` in particular is not a pass.

## The pipeline, in five jobs

```
gate  ->  build + sign  ->  scan  ->  staging + reboot  ->  production
```

**One artifact.** `colt-web` used to be compiled on production, so the one internet-facing image
was the one CI never saw. CI now builds it once, pushes to GHCR, Trivy scans that image, and both
staging and production pull it. `WEB_IMAGE` and `WEB_TAG` carry both halves of the name, with
`ghcr.py` as their one home. An immutable tag means what was tested and what is running cannot
drift apart.

**One gate, and it can actually fail.** `quality-and-secrets` decides what "main is protected"
means. It used to mean `ruff check . || true`, a check with no way to fail. It now runs
`python ship.py --test` inside `Dockerfile.ci`, with no secrets, `--network none`, against a
read-only checkout it copies first. gitleaks runs beside it, and a leak stops the gate with build,
scan, staging and production skipped behind it.

**Two people, one droplet.** `teamlock.py` is a `mkdir` on the droplet itself, the only thing every
deploy path touches. It covers the staging gate and both production deploys, fails open if the
droplet is unreachable, and clears by staleness after 45 minutes rather than by trusting a
`finally`. CI takes the same lock, because a GitHub concurrency group cannot see a laptop.
Production additionally waits on a human approving the `production` environment.

## Inside each job

| job | limit and privilege | steps |
|---|---|---|
| 1 gate | 30 min, no secrets | checkout, then wait for `quality-and-secrets` on this commit. `ci.yml` does the work: gitleaks, build `Dockerfile.ci`, `python ship.py --test` with `--network none` over a read-only mount. |
| 2 build | 60 min, `packages: write` | checkout, buildx, login to ghcr.io, tag is the first 12 of the SHA, build `colt-web`, `colttechbot` and `cassandra`, attest provenance three times via keyless Sigstore, one SBOM per image. |
| 3 scan | 30 min, matrix of 3 | install Trivy pinned and checksum-verified, because the scanner is itself a supply-chain risk. HIGH is reported, CRITICAL fails the job, nothing is promoted. |
| 4 staging | 45 min, `environment: staging` | install the deploy key, run `stagegate.py`: pull the same image, 42 checks, reboot the twin, all 42 again, four models write a verdict, tee the full log to a 14-day artifact. |
| 5 production | 45 min, `environment: production` | wait for a human to approve, `teamlock.py --acquire`, deploy `colt-web` pulled and never built here, deploy the bots, caddyguard health check, release the lock with `if: always()`. |

**Least privilege is measured per job.** Only `build` may write packages. `scan`, `staging` and
`production` may only read them. `gate` is given no secrets and no network. A job that cannot reach
the droplet cannot break it, and a token that cannot push an image cannot replace one.

**Why the gate is safe on any pull request.** `do_tests()` makes zero SSH calls, asserted by an AST
test rather than promised in a comment, and the one branch that would write to the droplet refuses
out loud under `SHIP_GATES_OFFLINE=1`.

## Every workflow

| workflow | started by | what it does | class |
|---|---|---|---|
| `pipeline.yml` | push to main, dispatch | gate, build, scan, staging, production | deploys |
| `ci.yml` | push, PR, dispatch | `quality-and-secrets`: gitleaks plus `ship.py --test` | the gate |
| `codeql.yml` | push, PR, Tuesdays 06:00 | GitHub code scanning, results in the Security tab | reports |
| `security.yml` | push, PR, Mondays 06:00 | Trivy FS and IaC, hadolint, pip-audit, report only | reports |
| `uptime.yml` | every 10 minutes | probes every public endpoint from outside, alerts Telegram | watches |
| `import-dashboards.yml` | push to main, dispatch | re-imports the Grafana dashboards | config |
| `deploy.yml` | dispatch only | the older stack deploy, kept as a manual escape hatch | deploys |
| `web-deploy.yml` | dispatch only | the older web deploy, same reason | deploys |
| `provision-patchwatch.yml` | dispatch only | installs the unattended-patch timer | provision |

## The clock

Two schedulers, chosen by what each thing needs to survive.

GitHub cron, which keeps running when the droplet does not:

```
*/10 * * * *   uptime.yml      probe every public endpoint from outside, alert Telegram
0 6 * * 1      security.yml    Trivy, hadolint, pip-audit
0 6 * * 2      codeql.yml      GitHub code scanning
               Dependabot raises its own pull requests continuously
```

systemd on the droplet, for the things that have to be there:

```
every 10 min   caddyguard      validate the shared config, compare the three hops, self-heal
                               from the committed fragments
daily 04:40    perseus --cycle      propose detections
Sun 05:20      perseus --weekly     re-vet live rules, retire what a month never matched
every 10 min   perseus --watch      four-vendor consensus on one live incident
nightly        patchwatch, which refuses to reboot into an invalid config, dbbackup, logship
```

The uptime probe runs off-box deliberately. A watchdog that lives on the thing it watches reports
nothing at all when that thing is down.

**Where to look when something fires.** The Actions tab, the run, the failing job. Every gate
writes a `$GITHUB_STEP_SUMMARY` table, and the staging gate also uploads its complete log as an
artifact, because GitHub truncates the middle of a long step and the middle is where the evidence
usually is.

## The orchestrator's reach

Everything `ship.py` calls, so that no step is a second command anyone has to remember.

| group | what it runs |
|---|---|
| gates, phase 1 | compile every `.py`, ruff F821/F811/F822, 16 engine regression scripts, 8 node gates, `pytest tests/`, `authz_audit.py --local`, `demo_build.py`, `gen_sbom.py --check` |
| deploy | `stagegate.py`, `deploy_web_direct.py --ghcr`, `ghcr.py`, `teamlock.py`, `shipflow.py`, `deploy.py --reuse --yes`, `import_dashboard.py`, `govern.py` on a NO-GO |
| infrastructure | `caddyguard.py`, `dbbackup.py`, `logship.py`, `secaudit.py`, `perseus.py --install-only`, `model_watch.py`, `ci_key.py` |
| record | git add, commit, push, tag `last-known-good` and `good-<stamp>`, `release_notes.py`, `ui_preview_stamp.py` |

If a capability is not wired in here, it does not run. New check, new migration, new provisioning
step: it goes into `ship.py` in the same change.

---

# C. What must pass

## The gate battery, phase 1/5

Before anything else, `py_compile` over every `.py` in the engine, the repository root and
`webapp/backend/app`, which catches a truncated file, and ruff F821/F811/F822, the undefined-name
gate, added after a `NameError` reached a customer run.

**Sixteen engine regression scripts**, each named for the incident it prevents:

| script | what it pins |
|---|---|
| `test_ca_pivot.py` | false positives. bibeltv.de, 1003 wrong IPs from a public CA |
| `test_recall.py` | false negatives, the opposite bug on the same customer |
| `test_parity.py` | the engine must not find less than manual Shodan work |
| `test_run_path.py` | recon end to end against a mocked API |
| `test_recon_budget.py` | recon stays bounded. caixabank.es, 22 minutes |
| `test_enrich_deadline.py` | enrichment stays bounded. AS37468, 19 minutes |
| `test_enrich_grounding.py` | prose must name something of its own finding. AS37468 |
| `test_scope_abakus.py` | one footer link became 236 Meta hosts |
| `test_classify_adpolice.py`, `test_asn_enterprise.py`, `test_passive_checks.py`, `test_drift.py` | classification, ASN sourcing, passive checks, config drift |
| `test_deck_quality.py`, `test_engine_i18n.py`, `test_white_label.py`, `test_compliance_ca.py` | the delivered artifact, six languages, partner branding, the Canadian regime set |

**Eight node gates** over the frontend:

```
api_contract.mjs     getJSON versus postJSON shape
canvas_smoke.mjs     900 frames, no exception, every colour valid
header_layout.mjs    row arithmetic in the longest language
contrast_gate.mjs    WCAG against the shipped stylesheet
partners_gate.mjs    six locales, no prices, no legal entities
i18n_catalogue.mjs   per-locale gaps across two key spaces
run_i18n_audit.mjs   16 pages by 6 languages
shipped_shell.mjs    no source maps, no secrets, no comments in dist/
```

Exit 2 from one of those means the toolchain is unusable and the gate skips. Exit 1 means a real
defect and the ship stops. A gate that cannot run is not a gate.

Any failure exits before phase 2. Nothing is committed, nothing is pushed, nothing is deployed. A
gate that crashes is reported differently from a gate that finds something, so read the verdict
line rather than the stack.

## The suite

59 modules, 1,138 test functions, which parametrisation expands to 1,179 cases at run time, counted
on 2026-10-16. Grouped by what they defend rather than by file name:

| group | modules | the rule they hold |
|---|---|---|
| access and identity | `test_auth`, `test_admin_users`, `test_quota`, `test_routes`, `test_set_secret` | every `/api/admin/*` route refuses a non-admin. Hiding a nav item is presentation, not control. |
| active defence | `test_shield`, seven `test_perseus_*`, `test_client_truth`, `test_asset_trace`, `test_ip_reputation`, `test_attack_digest` | never iptables, never block a logged-in user |
| deploy integrity | `test_deploy_immutability`, `test_deploy_parity`, `test_caddy_wiring`, `test_decommission`, `test_gate_integrity`, `test_hostpath` | what deploys is the commit, never the working tree |
| money | `test_llm_meter`, `test_spend_watch`, `test_jhw_llm_events` | the daily cap, the spike detector, and proof of what each project spent |
| output and language | `test_doc_lang`, `test_jurisdiction_path`, `test_white_label_api`, `test_proteus`, `test_run_log`, `test_release_notes` | a capability the API discards is invisible to every engine test |
| the watchers | `test_fleet`, `test_fleet_cli`, `test_fleet_soc`, `test_outside_view`, `test_supplychain`, `test_console_encoding`, `test_claude_md_size` | the observer must itself be observed |

Six modules need a POSIX shell and skip with a stated reason on Windows, gated by
`shell_harness_allowed()`, which has one home. CI runs them for real. No module requires a docker
binary, and none reaches the internet, because a test that silently needs the network is a test of
the network.

---

# D. The models

## Four vendors, so no shared failure domain

`enrich._FALLBACKS` is the one home. Compose must not restate it, and `ship.py` deletes any
override from the droplet `.env`.

| model | vendor | measured throughput |
|---|---|---|
| `deepseek-3.2` | DeepSeek | 20 tok/s |
| `llama-4-maverick` | Meta | 5 tok/s |
| `gemma-4-31B-it` | Google | 9 tok/s |
| `kimi-k2.6` | Moonshot | 9 tok/s |

Those numbers are `enrich.MODEL_TOK_S`, measured rather than assumed. An earlier version assumed
100 tok/s, and the arithmetic that followed reported all four models as having failed when the real
problem was that the request could never have finished in its own timeout.

## How one assessment gets written

1. **Feasibility check.** Findings times 600 tokens, against what the fastest model can write in
   its slice. Too big, and the whole-estate call is never issued; the shards take over.
2. **Serial chain.** The head model gets 55% of the remaining budget. Two consecutive timeouts end
   the chain, because the prompt is the same each time, so it is the prompt that is wrong rather
   than the vendor.
3. **Map-reduce top-up.** Three findings per shard, four workers, shards spread across vendors and
   interleaved by severity.
4. **Coverage contract.** Missing ids get one retry on a different model. Under 420 characters
   counts as thin, not as covered.

## What stops a confident wrong answer

`grounded()` requires the prose to name something of its own finding: a port, a CVE, a product, an
address. Naming nothing means rejection, and the template text is kept. On AS37468 a model wrote
BGP prose onto a database finding, which is the incident behind the rule.

`_audit_cves()` cites a CVE only if it appears in the raw findings. The rest are stripped and
logged as `hallucination_guard`.

`slim_payload()` means the model sees findings and evidence only. Never the whole file, and never a
character-sliced JSON blob.

## Budgets, committed default against what is deployed

```
ENRICH_TIMEOUT    per call        code 120 s    droplet 175 s
ENRICH_BUDGET_S   serial chain    code 245 s    droplet 380 s
ENRICH_WALL_S     whole phase     540 s         (enrich_parallel.WALL_S_DEFAULT)
RECON_BUDGET_S    recon           300 s         (shodan_recon.ReconBudget)
```

Shard ceiling 150 s, shard floor 45 s, below which the call is not issued at all, and the
subprocess is killed at 430 s. Read both numbers before diagnosing a timeout.

## Models propose. Code decides.

The same four models appear in six places, and in none of them do they decide a side effect.

| where | the models write | the code decides |
|---|---|---|
| enrichment | the finding prose | severity, evidence and CVE ids are engine facts |
| staging gate | two soldiers and two auditors write a verdict | GO or NO-GO comes from 42 deterministic checks |
| release notes | readable prose and a risk read | commits, files and hashes are computed by git |
| shield panel | proposes threshold changes | 3-of-4 consensus, median value, clamped to committed bounds |
| false-positive auditor | flags a finding as a third party's | dropped only if deterministic ownership data agrees |
| white label | picks brand colour against decoration | colours and fonts are extracted from `theme1.xml` |

A 429, an outage or a truncated answer cannot block a correct release. A hallucinated objection
cannot stall a good deploy. A model in an agreeable mood cannot wave through a container that is
not running.

## Spend

Three controls, three different questions, built in this order because each one proved the previous
insufficient.

**`llm_meter.py`, the hard ceiling.** Daily cap $3.00, warning at 60%, single-call alert at $0.15.
Hooked at `enrich._call`, the one chokepoint. `allow()` runs before the request and `record()`
after. It fails open on a storage fault and closed on the budget, and a refusal falls back to
template text.

**`spend_watch.py`, the spike detector.** Hourly, against a median baseline over 14 days. A spike is
4x baseline with a floor of $0.10, an account-level threshold of $2.00 and an unattributed threshold
of $1.00, with a six-hour cooldown. It reads two sources: our own meter and the DigitalOcean
balance. The second is the point, because it sees callers we do not control.

**`cost_ledger.py`, the books of record.** SQLite on the shared `colt_events` volume, so it survives
every rebuild. One row per completed assessment: company, cost, tokens, model, severity counts,
user. Loki ages out under retention. This does not. Every write is best effort.

**The incident that built the third one.** Two models, `deepseek-v4-pro-0813` and `glm-5.3-flash`,
appeared in no configuration in this repository or in jobhuntwow, and took more than 96% of the
account's tokens. A meter that counts only our own calls would never have seen them. That is why
the watcher reads the DigitalOcean balance as well, and why five projects sharing one model key is
a known open item: that vendor's per-key usage cannot attribute the invoice until scoped keys are
minted in the console.

---

# Day one

In this order. None of it needs permission from anyone.

```
1.  read CLAUDE.md top to bottom     the operating principles and the defect classes
2.  python ship.py --test            the whole gate battery, changes nothing. Minutes, not seconds.
3.  python ship.py --dry-run         every command the pipeline would run, touching no droplet
4.  python fleet.py                  read-only: alive, wired in, beating, taking traffic, attacked
5.  python recover.py                read-only outage triage. Learn it before you need it.
6.  read docs/decisions/HISTORY-*.md the evidence behind the rules
```

New collaborators should read `docs/DEVELOPER-ONBOARDING.md`, which covers the pull request flow,
what they will and will not be given, and why.

## Six rules you will be held to

These are not style preferences. Each is the shape of a defect that already happened here.

**One home.** A value with several homes drifts, and the newer one always loses. `ENRICH_MODELS`
once had four.

**One command.** If an instruction ends with two `python` lines, the second belongs inside
`ship.py`. A step the operator has to remember is a bug.

**A check that cannot fail is not a check.** Prove a gate by breaking the thing it guards. If the
denominator comes from the thing being measured, it is not a measurement.

**Absence of evidence is never a finding.** A failed lookup reports `UNKNOWN` and claims no gap. A
dead DNS resolver once produced a CRITICAL.

**Read the delivered artifact.** Rich finding text is not a good deck. Open the file. Every one of
those defects was invisible in the logs and obvious in the artifact.

**Secrets never touch git.** `set_secret.py`, value on stdin, never in argv. gitleaks runs in CI,
and `tests/test_secret_scan.py` sweeps every tracked file with gitleaks' own rules so a leak is
caught on the laptop rather than by a red pipeline.

---

# Diagnostics

Read-only, one SSH session each, run from the operator's PC.

| command | question it answers |
|---|---|
| `python recover.py` | outage triage: ports, crash loops, Caddy validation, probes from outside |
| `python fleet.py` | per project: code present, wired in, beating, taking traffic, under attack |
| `python cost_report.py` | AI spend. `--trace` who can spend, `--whodunit` who did, `--correlate` |
| `python agent_forensics.py` | is this actor a human, a script, or an agent |
| `python authz_audit.py` | does every route refuse an anonymous caller |
| `python incident_report.py` | assemble a forensics package for an exposure |
| `python secaudit.py` | kernel, reboot and patch posture, and staging-versus-production drift |
| `python decommission.py --sites <name>` | retire a vhost from the shared proxy. Dry run by default, no default target, and a fragment shared with other domains is edited rather than deleted |

---

# Repository map

```
hermes-skills/shodan-assessment/scripts/   the engine: discovery, ownership gates, enrichment,
                                           the false-positive auditor, deck and HTML builders, i18n
webapp/backend/app/                        FastAPI: auth, telemetry, the shield, spend metering,
                                           alerting, fleet status, white label
webapp/frontend/src/                       React in six languages, with its gates in tools/
perseus/                                   the detection hub: ruleset, vetting, abuse reports
deploy/                                    committed Caddy fragments and the sidecar agents
tests/                                     the suite
.github/workflows/                         nine workflows, the real specification of CI
docs/decisions/                            the narrative behind every rule in CLAUDE.md
marketing/                                 deck builders. The .pptx files themselves are ignored.
```

Root scripts worth knowing: `ship.py`, `stagegate.py`, `deploy_web_direct.py`, `ghcr.py`,
`teamlock.py`, `shipflow.py`, `ci_key.py`, `caddyguard.py`, `perseus.py`, `set_secret.py`.

---

# Honest limits

Shodan cannot see a virtual host behind an SNI-only front end, so "shared hosting, not externally
observable" is sometimes the correct and complete answer. No public API is authoritative across all
five RIRs, which is why `clarify.py` always asks before claiming address space. DKIM is
presence-only: a selector cannot be enumerated, so "not found" means not determinable. The five
projects share one DigitalOcean model access key, so that vendor's per-key usage cannot attribute
the invoice, and scoped per-project keys remain a console job.

---

`CLAUDE.md` carries the operating principles, the settled facts and the recurring defect classes,
and a test caps its size so it stays readable. The evidence behind every rule in it, including what
broke and what was measured, lives in `docs/decisions/`.
