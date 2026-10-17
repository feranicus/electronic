# electronic

The platform behind **cybergod.ai**: an external attack-surface assessment engine, a web app, two
Telegram bots, and the automation that ships all of it.

You give it one input, a company name. It finds what that company exposes to the internet using
public records only, grades the risk, writes the prose with four different vendors' models, and
returns a set of decks. Not one packet is ever sent to the company being assessed.

Everything lives in this repository. The droplets are provisioned from here, never configured by
hand, and one command ships the lot.

---

## The one command

```
cd "C:\Python SW\Linkedin Scraper"
python ship.py
```

That is the whole interface. `ship.py` runs five numbered phases in order:

| phase | what it does |
|---|---|
| 1/5 TESTS | compile every Python file, run the engine regressions, the node gates, and `pytest tests/`. Nothing ships if any of it fails. |
| 2/5 COMMIT + PUSH | GitHub is the single source of truth, so the commit happens before anything is deployed. |
| 3/5 DEPLOY WEB | cybergod.ai (`colt-web`). |
| 4/5 DEPLOY BOTS | the assessment bot and Cassandra (`colt-stack`). |
| 5/5 VERIFY | container hashes, `GET /api/me` returns 401, security headers present, bot gate behaving. |

Between phase 2 and phase 3 sits the **staging gate**, described below. After phase 5 a tail of
infrastructure verbs runs: the shared proxy is reassembled and validated, databases are backed up
off-box, logs are archived, the kernel posture is checked, a safe point is tagged, and four models
write the release notes, which are sent by Gmail API and Telegram.

### Flags narrow it. They never split it.

| flag | effect |
|---|---|
| `--test` | run the gate battery only, change nothing |
| `--web` / `--bots` | deploy one half |
| `--pr` | reach main through a gated pull request instead of pushing to it |
| `--direct` | deploy straight to the droplet over SSH (this is the default) |
| `--ci` | deploy through GitHub Actions instead of over SSH (slower) |
| `--no-stage` | skip the staging validation and go straight to production |
| `--fast-stage` | validate on staging but skip the reboot test (faster, and weaker) |
| `--dry-run` | print the plan, touch nothing |
| `--no-preview` | ship a frontend change without previewing it locally first |
| `--no-test` | skip the test gate (you had better have a reason) |
| `--rollback [REF]` | restore a known-good state and redeploy it, default `last-known-good` |
| `--fix-ci-key` | prove the deploy key works, then write it to the GitHub secret |
| `-m "message"` | commit message, also quoted in the release notes |

Every other script here is a building block that `ship.py` calls as a subprocess. They stay
individually runnable for debugging, and in normal operation you should never need one. If a
change adds a step, wire it into `ship.py` in the same commit. A script the operator has to
remember separately is a bug.

---

## How code reaches production

There are two paths, and since October 2026 the second one is the automatic one.

### Path A: the laptop

`python ship.py` tests, commits, pushes, validates on the staging twin, deploys, verifies.
This is the direct path. It is what you run day to day, and it is the escape hatch for the day
the pipeline itself is what is broken.

### Path B: GitHub Actions

A push to `main` starts five workflows in parallel. One of them, `pipeline.yml`, is the deploy:

```
gate  ->  build + sign  ->  scan  ->  staging + reboot  ->  production
```

| job | what it does | permissions |
|---|---|---|
| `gate` | waits for `quality-and-secrets` to pass on this exact commit | no secrets |
| `build` | builds three images once, pushes to GHCR, attests provenance via Sigstore, emits an SBOM | `packages: write` |
| `scan` | Trivy across all three images. HIGH is reported, CRITICAL fails the job and nothing is promoted | `packages: read` |
| `staging` | deploys the twin, runs 42 checks, **reboots it**, runs all 42 again, four models write a verdict | `packages: read` |
| `production` | waits for a human to approve the environment, takes the deploy lock, pulls the scanned image, releases the lock | `packages: read` |

CI does not re-implement the orchestrator. It calls this repository's own scripts as subprocesses
(`ship.py --test`, `stagegate.py`, `deploy_web_direct.py`, `caddyguard.py`), so there is exactly one
definition of what a gate means and one definition of what a deploy does. A YAML copy of those
gates would drift within a week, and the drift would stay invisible until it mattered.

### Why a pull request, and when

GitHub requires a status check to pass *before* a collaborator changes a protected branch, and a
brand-new commit has no check runs yet. That is why a direct push logs `Bypassed rule violations`.
`python ship.py --pr` solves it properly: branch, push, open a PR, wait for `quality-and-secrets`
on the PR head, squash-merge. The merge is itself a push to main, so the merge is the deploy and
PR mode stops there rather than deploying a second time. Nothing merges on an unknown state, and a
`skipped` check is not a pass.

---

## The staging gate

A real second droplet, same size, same image, same region as production, deliberately. It holds
synthetic data only, built from committed fixtures using RFC 5737 addresses, so a compromise there
leaks nothing about anyone.

The gate is not "did the deploy succeed". It is:

```
deploy to the twin  ->  health  ->  REBOOT IT  ->  health again  ->  AI digest  ->  GO / NO-GO
```

The reboot is the point. On 2026-08-14 a deploy truncated the shared Caddy config at 16:15. Caddy
reads its configuration only at start, so nothing failed for twelve hours, until a 04:22 kernel
reboot made it re-read the file and six domains went down together. There was no environment in
which that change could have been rebooted first. Now there is.

A NO-GO stops the ship and production is never touched.

---

## One artifact

`colt-web` used to be compiled on the production droplet, which meant the only internet-facing
image in the stack was the one image CI never saw. Scanning it after the fact was a reasonable
mitigation, and it stays, but it is a different thing from never putting an unscanned artifact in
front of the internet.

CI now builds the image once, Trivy scans that image, GHCR holds it, and staging and production
both pull those exact bytes by immutable tag. Both halves of the image name travel together
(`WEB_IMAGE` and `WEB_TAG`), because passing only the tag once left the repository half to a
default that pointed at a different package. GHCR answers an unauthorised request for a private
package with 404 rather than 401, so a wrong name and a missing login produce an identical error
with opposite repairs. `ghcr.py` is the one home for the reference, and its `report()` asks the
registry both anonymously and with a token so the difference between those answers becomes the
diagnosis.

---

## Secrets

Runtime secrets live only as encrypted GitHub Actions secrets and in the droplet's own env files
(`chmod 600`). They never touch git. `.gitignore` blocks `*.env`, `*_sa.json`, `data/` and
`*.sqlite`, and gitleaks runs in CI on every push and pull request.

```
python set_secret.py NAME        # value on STDIN, never on the command line
```

A value in `argv` is visible in `ps` to every user on the box, which is why the remote script
travels in argv and the value travels on stdin. The two are mutually exclusive.

Three files are allowlisted in `.gitleaks.toml` because their job is to contain secret-shaped text:
the key detector, its synthetic fixtures, and the list of tokens the LLM guard must redact. An
allowlist is a new hole, so it ships with its own guard: `tests/test_secret_scan.py` hands every PEM
block in each allowlisted file to `ssh-keygen -y` and fails if one actually parses, and it sweeps
every other tracked file with gitleaks' own two regexes so a leak is caught on the laptop rather
than by a red pipeline.

This repository is public. Treat every log, every fixture and every committed string accordingly.

---

## Tests

```
python ship.py --test
```

59 test modules, 1,138 test functions, which parametrisation expands to 1,179 cases at run time
(counted 2026-10-16). Six modules need a POSIX shell and skip with a stated reason on Windows; CI
runs them for real. No module requires a docker binary, and none reaches the internet.

The gate battery also compiles every Python file in process from bytes, runs the engine's own
regression suites, eight node tools covering layout, contrast, i18n and the shipped bundle, and
`authz_audit.py --local`, which proves every non-public route refuses an anonymous caller.

`do_tests()` makes zero SSH calls. That is asserted by an AST test rather than promised in a
comment, which is what makes the gate safe to run on a fork's pull request with no secrets at all.

---

## Diagnostics

All read-only, one SSH session each, run from the operator's PC.

| command | question it answers |
|---|---|
| `python recover.py` | outage triage: ports, crash loops, Caddy validation, probes from outside |
| `python fleet.py` | per project: is the code present, wired in, beating, taking traffic, under attack |
| `python cost_report.py` | AI spend. `--trace` who can spend, `--whodunit` who did, `--correlate` |
| `python agent_forensics.py` | is this actor a human, a script, or an agent |
| `python authz_audit.py` | does every route refuse an anonymous caller |
| `python incident_report.py` | assemble a forensics package for an exposure |
| `python secaudit.py` | kernel, reboot and patch posture, plus staging-versus-production drift |
| `python decommission.py` | retire a vhost from the shared proxy (dry run by default) |

---

## What runs on a schedule

Two schedulers, chosen by what each thing needs to survive.

GitHub cron, which keeps running even when the droplet does not:

```
*/10 * * * *   uptime.yml      probe every public endpoint from outside, alert Telegram
0 6 * * 1      security.yml    Trivy filesystem and IaC, hadolint, pip-audit
0 6 * * 2      codeql.yml      GitHub code scanning
```

systemd on the droplet, for the things that have to be there:

```
every 10 min   caddyguard      validate the shared proxy config, compare three hops, self-heal
daily 04:40    perseus --cycle     propose detections
Sun 05:20      perseus --weekly    re-vet live rules, retire what a month never matched
every 10 min   perseus --watch     four-vendor consensus on one live incident
nightly        patchwatch, dbbackup, logship
```

The uptime probe runs off-box on purpose. A watchdog that lives on the thing it watches reports
nothing at all when that thing is down.

---

## Repository map

```
hermes-skills/shodan-assessment/scripts/   the engine: discovery, ownership gates, enrichment,
                                           false-positive audit, deck and HTML builders, i18n
webapp/backend/app/                        FastAPI: auth, telemetry, the shield, spend metering,
                                           alerting, fleet status, white label
webapp/frontend/src/                       React in six languages, with its own gates in tools/
perseus/                                   the detection hub: ruleset, vetting, abuse reports
deploy/                                    committed Caddy fragments and the sidecar agents
tests/                                     the suite
.github/workflows/                         nine workflows (see below)
docs/decisions/                            the narrative history behind every rule in CLAUDE.md
marketing/                                 deck builders; the .pptx files themselves are ignored
```

Root scripts worth knowing: `ship.py` (the orchestrator), `stagegate.py` (the twin and its gate),
`deploy_web_direct.py`, `ghcr.py`, `teamlock.py`, `shipflow.py`, `ci_key.py`, `caddyguard.py`,
`perseus.py`, `set_secret.py`.

### The nine workflows

| workflow | started by | what it does |
|---|---|---|
| `pipeline.yml` | push to main, dispatch | the deploy: gate, build, scan, staging, production |
| `ci.yml` | push, PR, dispatch | `quality-and-secrets`: gitleaks plus `ship.py --test` in a pinned image |
| `codeql.yml` | push, PR, Tuesdays 06:00 | GitHub code scanning |
| `security.yml` | push, PR, Mondays 06:00 | Trivy, hadolint, pip-audit, report only |
| `uptime.yml` | every 10 minutes | probes every public endpoint from outside |
| `import-dashboards.yml` | push to main, dispatch | re-imports the Grafana dashboards |
| `deploy.yml` | dispatch only | the older stack deploy, kept as a manual escape hatch |
| `web-deploy.yml` | dispatch only | the older web deploy, same reason |
| `provision-patchwatch.yml` | dispatch only | installs the unattended-patch timer |

`deploy.yml` and `web-deploy.yml` became dispatch-only deliberately. One push used to start two of
them against one droplet, six minutes apart.

---

## Two developers

`teamlock.py` is the one deploy lock, and it is a `mkdir` on the droplet itself, because the
droplet is the only thing every deploy path touches. It covers the staging gate and both
production deploys, fails open if the droplet is unreachable, and clears by staleness after 45
minutes rather than by trusting a `finally` block. CI takes the same lock, since a GitHub
concurrency group cannot see a laptop.

`ship.py` also refuses to deploy off `main`, refuses to commit on a tree behind origin, prints
every path `git add -A` is about to take grouped by area, and refuses to roll back to a
`last-known-good` pointer that belongs to the other developer. Each refusal names the environment
variable that overrides it, because a guard an informed operator cannot override is its own bug.

---

## Operating rules

These are not style preferences. Each one was paid for by an incident, and the full story for each
is in `docs/decisions/`.

- Full automation. If a task needs doing twice, it gets a script, not a sequence of commands to
  paste.
- One orchestrator, one command. Any new capability is wired into `ship.py` in the same change.
- Secrets never touch git.
- Nothing on the droplet disturbs the neighbouring stacks, and nothing touches the firewall.
- The models write prose. They never decide a side effect: whether to deploy, reboot, block an
  address or promote a release is always deterministic code.
- Absence of evidence is never a finding. A failed lookup reports `UNKNOWN / data-unavailable` and
  claims no gap.
- A check that cannot fail is not a check, and a check that cannot see its subject must not answer.

---

## Honest limits

Shodan cannot see a virtual host behind an SNI-only front end, so "shared hosting, not externally
observable" is sometimes the correct and complete answer. No public API is authoritative across all
five RIRs, which is why `clarify.py` always asks before claiming address space. DKIM is
presence-only: a selector cannot be enumerated, so "not found" means not determinable. The five
projects share one DigitalOcean model access key, so that vendor's own per-key usage cannot
attribute the invoice, and scoped per-project keys remain a console job.

---

## Where the rest is written down

`CLAUDE.md` carries the operating principles, the settled facts and the recurring defect classes,
and it is size-capped by a test so that it stays readable. The evidence behind every rule in it,
including what broke and what was measured, lives in `docs/decisions/`.
