# Project conventions — feranicus/electronic (Cybergod LLC / S4Biz Group)

## READ THIS FIRST — where the rest of this file went (2026-09-09)

This file used to be **646 KB / 7,950 lines / 307 sections**. It is re-injected into the model's
context on EVERY turn, so it was spending ~160,000 tokens before the operator typed anything, and
that is what produced *"This conversation is too long to continue."*

Nothing was deleted. The full narrative history — every incident, every root cause, every measured
number, verbatim — is at:

    docs/decisions/HISTORY-2026-07-to-2026-09-10.md

**This file now carries only what must be true on EVERY turn**: the operating principles, the
settled facts, and the defect classes as one-line rules. The history is the EVIDENCE for those
rules and is read on demand, not on every turn.

**HOW TO USE THE HISTORY.** When a rule below matters and you need the story — what broke, what was
measured, which fixture proved it — `grep` the history file for the phrase in the rule. Every rule
here was earned by an incident recorded there; searching for the key words in the rule finds it.

**HOW TO ADD TO IT.** A new incident goes in `docs/decisions/<YYYY-MM>.md`, in the same voice and
detail as the history file. It gets **at most one line here**, and only if it is a rule that must
be obeyed on every turn. If a section here grows past a few lines, the story belongs in the month
file and the rule belongs here. `tests/test_claude_md_size.py` FAILS THE BUILD if this file passes
the size budget, because a rule that is only written down goes stale, and this one already did.

---

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
   in the droplet's own env files (`chmod 600`). `.gitignore` blocks `*.env`, `*_sa.json`, `data/`,
   `*.sqlite`, and `gitleaks` runs in CI. The only credential in GitHub-as-code is the deploy SSH
   key (a secret).
4. **Non-destructive on the droplet.** Never disturb Amnezia VPN / VideoDead / joplin. The
   colt-stack is an isolated compose project (`-p colt-stack`, `colt-*` names). No firewall
   changes. Patch automation only refreshes colt-stack images; other stacks get only shared
   OS/kernel patches.
5. **The LLM assists, it does not decide side effects.** The models write summaries, risk digests
   and prose. They never decide whether to run `apt`, push, deploy, reboot, block an address or
   promote a release — those are deterministic code paths.
6. **Deliver operations as scripts + document — NO command blobs.** Never hand the user long ad-hoc
   shell/heredoc sequences to paste ("talmud commands"). Every operational step (build, run,
   deploy, diagnose, fix) is a re-runnable **Python script** committed here, invoked as
   `python <script> ...`, and any change (deps, Dockerfile, flags, config, architecture) updates
   the relevant **README.md** in the SAME change. KISS + full automation. (All projects.)
7. **ONE ORCHESTRATOR. ONE COMMAND. ALWAYS.** ← the rule I keep breaking; stop breaking it.
   The user must NEVER be told to run two scripts. Not "run the test then deploy", not "run X then
   Y to verify" — **one** command, every time, in every project. All other scripts are BUILDING
   BLOCKS that the orchestrator calls as subprocesses; they stay individually runnable only for
   debugging, and the user should never need to.
   - In this repo the orchestrator is **`python ship.py`** = test -> commit -> push -> staging gate
     -> deploy -> verify -> safe-point -> release notes. Flags narrow it (`--test`, `--web`,
     `--bots`, `--direct`, `--dry-run`, `--no-stage`, `--no-preview`, `--rollback`, `-m "msg"`),
     they never split it. `ship_web.py`, `deploy.py`, `deploy_web_direct.py`, `stagegate.py`,
     `caddyguard.py`, `dbbackup.py`, `perseus.py --install-only`, `secaudit.py`, `model_watch.py`,
     `release_notes.py` and `pytest` are all invoked BY ship.py.
   - New capability (a test, a check, a migration, a provisioning step)? **Wire it into ship.py in
     the same change.** A new script the user has to remember to run separately is a bug.
   - If a reply is about to end with two `python ...` lines, that is the signal: go back and fold
     them into the orchestrator, then give the single command.

## TWO DEVELOPERS (2026-10) — what a second pair of hands changes

`teamlock.py` is the ONE deploy lock, a `mkdir` on the droplet itself (`/opt/colt-stack/.deploy.lock`),
because the droplet is the only thing every deploy path touches. It covers the staging gate AND both
production deploys, fails OPEN if the droplet is unreachable, and clears by STALENESS (45 min), never
by trusting a `finally`. Both CI workflows share ONE concurrency group, `production-droplet`, and
the CI deploy job takes the SAME lock (`--acquire` / `--release if: always()`) because a
concurrency group cannot see a laptop. `ship.py` refuses to deploy off `main`
(`SHIP_ALLOW_BRANCH=1`), refuses to commit on a tree behind origin (`SHIP_ALLOW_BEHIND=1`), prints
every path `git add -A` will take grouped by area, and refuses `--rollback last-known-good` when
that pointer is another developer's deploy (`SHIP_ALLOW_OTHERS_ROLLBACK=1`).
`tests/test_teamwork.py`

**A CREDENTIAL NOBODY CAN READ BACK MUST BE PROVEN BEFORE IT IS WRITTEN.** `setup_github_cicd.py`
uploaded `DROPLET_SSH_KEY` from a file it never parsed, so every CI deploy for weeks died at the
first ssh ("error in libcrypto") while the next step blamed the droplet. `ci_key.py` is the ONE home
for "is this a key": shape -> `ssh-keygen -y -P "" </dev/null` -> one real ssh -> only then
`gh secret set` with the value on **stdin**. An UNKNOWN at any step is not a pass.
**The actual cause was a PASSPHRASE**, which a modern OpenSSH key hides: no `ENCRYPTED` header, the
cipher name in the clear inside the base64 (`openssh_cipher()`, "none" = usable), so a header-only
check passes it to a runner with no keyboard. **A check must never prompt** — asking for the
passphrase turned his correct one into "incorrect passphrase supplied", reading as a corrupt key. `--fix-ci-key` MINTS a dedicated passphrase-less key, authorizes it
(public half only, `grep -qxF ... ||`, verified on the box) and ships; his own key is never read,
copied or changed. Every workflow that installs the key validates it first. A POSIX-shell test
harness uses `shell_harness_allowed()` (ONE HOME, test_teamwork.py), never `shutil.which("bash")`:
here `bash` is WSL's bash.exe and a stripped `env=` makes WSL fail in UTF-16 — inherit
`os.environ`, override only what the test needs.
**A SECRET HAS SEVERAL HOMES AND GITHUB PICKS, NOT YOU.** Per GitHub's reference the lowest-level
secret wins, and org/repo secrets are read when a run is QUEUED while environment secrets are read
when the JOB STARTS. deploy.yml's deploy job declares `environment: production`, so a correct
`gh secret set --repo` can land in a scope that job never reads, and the log looks identical to
"the fix failed". `ci_key.scopes()` MEASURES where it is defined (it was repository-only, so
precedence was NOT the cause — the measurement is why that was not built on),
`environments_used_by_workflows()` derives the targets, `push_everywhere()` writes all of them.
Every workflow prints the installed key's FINGERPRINT (public) first; that line named the cause.
**A PRIVATE KEY IS BYTES.** `subprocess.run(input=<str>, text=True)` wraps stdin in a TextIOWrapper
with newline=None, rewriting every `\n` as `os.linesep` — `\r\n` on Windows — so every upload from
this PC mangled the key. `setup_github_cicd.py` had the same shape from day one. `read_key_bytes()`
+ bytes on stdin; text-mode READ is equally banned (universal newlines silently repair the input).
**THE TWO OpenSSH BUILDS DISAGREE, which is why this was invisible** (MEASURED 2026-10-15, same
bytes): **Linux** OpenSSH, which the runner uses, gives rc 255 "error in libcrypto"; **Win32**
gives rc 0 and prints the public key. So `ssh-keygen` here can NEVER catch this class —
`key_shape()` rejects any `\r` itself, carrying the RUNNER's rule, and the CRLF experiment skips
where the local OpenSSH is tolerant (detected, not `sys.platform`). Class 21 both directions, and
it applies to FIXTURES: `Path.write_text` translates too (an AST test forbids it). On Windows
`os.chmod(0o600)` does NOT make a private ACL, so ssh-keygen refuses on "Bad permissions" before
reading a byte: let it CREATE the file, rewrite only the content, run the control first.
[2026-10-14/15] `tests/test_ci_key.py`

**A PROBE THAT CANNOT SEE ITS SUBJECT MUST NOT ANSWER.** `deploy.run()` folds stderr into stdout,
so a failed ssh made `sshout()` return ssh's own error text as the probe's ANSWER: `ensure_docker()`
read it as "docker is missing" and ran `apt-get install docker-ce` against production. `sshout` now
appends a sentinel only a shell that really ran can echo, and exits otherwise.
[2026-10-14] `tests/test_probe_fail_closed.py`

## THE PIPELINE (2026-10-15) — CI runs the orchestrator, it does not re-implement it

**ONE GATE.** `ci.yml::quality-and-secrets` is the name the ruleset requires, so it decides what
"main is protected" MEANS — and it used to mean `ruff check . || true` (a check that cannot fail),
`node --check` (PARSE is not RUN) and the unit suite ONLY, so a commit ship.py refuses could turn it
green. It now builds `Dockerfile.ci` (the pinned toolchain) and runs **`python ship.py --test`** —
the operator's own phase, never a YAML copy of its 37 gates (ONE HOME). Safe on every PR because
`do_tests()` makes ZERO ssh calls (measured by AST) and the one droplet-writing branch refuses out
loud under `SHIP_GATES_OFFLINE=1`. The gate gets **no secrets** and `--network none`.

**ONE AUTOMATIC PATH.** `pipeline.yml` = gate -> build once -> scan -> staging (reboot gate) ->
production (approval + teamlock). `deploy.yml` / `web-deploy.yml` are `workflow_dispatch` ONLY now:
one push used to produce TWO deploys to one droplet six minutes apart.

**ONE ARTIFACT.** colt-web was COMPILED ON PRODUCTION, so the only internet-facing image was the one
CI never saw. `deploy_web_direct.py --ghcr TAG` pulls the built, scanned image (`remote_ghcr()`;
the build path is byte-identical and untouched, asserted), and `WEB_IMAGE`+`WEB_TAG` make staging
rehearse the SAME bytes. CI calls the repo's scripts — stagegate.py, deploy*.py, caddyguard.py —
never inline ssh.

**A REQUIRED STATUS CHECK CANNOT BE SATISFIED BY A DIRECT PUSH** (GitHub: checks must pass "before
collaborators can make changes to a branch"; a new commit has no check runs yet). That is the
`Bypassed rule violations` line on every ship, and why a COLLABORATOR's push would be rejected
AFTER the staging gate. **`shipflow.py` is the answer**: `python ship.py --pr` (or `SHIP_FLOW=pr`)
does branch -> push -> PR -> WAIT for the gate -> squash-merge, so main only receives commits a
green gate has seen, with no bypass. A PR's head commit DOES get check runs, which is what makes
the rule satisfiable. **The merge IS the deploy** — pipeline.yml fires on push to main, so PR mode
STOPS there (asserted: the branch calls no do_web/do_bots/do_verify/tag_known_good) or one commit
deploys twice. Nothing merges on an UNKNOWN state: pending/missing/cancelled/timed_out/
action_required/null/dead-API/non-JSON are all not-green, **`skipped` especially** — a gate that
did not run is not a gate that passed. `--direct` stays for the day the pipeline is what is broken.
Owner-only: add the collaborator with **write** (never admin), and require a PR before merging with
yourself OFF the bypass list.
**A RED GATE LEAVES YOU ON THE BRANCH, SO THE NEXT RUN MUST RESUME IT.** PR #19's gate failed,
correctly leaving the branch and PR standing — and the next `ship.py --pr` hit his OWN guard,
"refusing to deploy from 'ship/…'". Two defects: PR mode called `collaboration_guards(
deploying=True)`, fatal off main because MAIN IS WHAT DEPLOYS (in PR mode the laptop deploys
nothing, so `deploying=False`); and shipflow would have cut a SECOND ship/ branch off the first,
orphaning the open PR. "Resumable by construction" was a docstring claim with nothing asserting it.
Standing on a `ship/` branch now MEANS resume — same branch, same PR — proved against a real
throwaway git repo, all four mutations caught.
`tests/test_shipflow.py` · `tests/test_pipeline_architecture.py` ·
`docs/decisions/2026-10-pipeline-architecture.md`

**THE SECRET SCANNER HAD BEEN RED FOR TWO MONTHS AND NOBODY SAW IT.** The first run that actually
blocked a merge (PR #19) reported 5 gitleaks findings; the oldest has been in the tree since
2026-08-22. The bypass made a failing scanner invisible — "an alert nobody gets is not an alert",
proven on this repo. All 5 are code ABOUT secrets (the delimiters `ci_key.py` matches on, synthetic key fixtures, the
token list the LLM guard must redact), so they are PATH-allowlisted in `.gitleaks.toml` — never
obfuscated, because hiding from the scanner teaches the next person to do it too. **An allowlist
is a new hole, so it ships with its own guard**: `tests/test_secret_scan.py` hands every PEM block
in each allowlisted file to `ssh-keygen -y` — OpenSSH decides, not a regex — and fails if one
PARSES, if a token is undocumented, if an entry is stale, or if the list grows. Two of my versions
could not fail: a greedy `.*?` returned ONE 25 KB "block" (class 13), and re-wrapping every body
in OPENSSH armour made a real RSA PEM unparseable for the WRONG reason. Keep the armour label;
handle the one-line escaped form a service-account JSON uses. **AND THE GUARD ITSELF STAYS UNDER THE SCANNER** — twice gitleaks
flagged it (the synthetic PAT written literally; a BEGIN/END pair in a COMMENT, since the rule
spans everything between). Allowlisting the guard was the tempting fix and the wrong one: who
guards the guard. Pin the token as `SYNTHETIC_SHA256`, describe armour in prose, and
`test_this_file_is_not_itself_a_finding` asserts it against gitleaks' OWN regexes so it fails
locally, not in CI. All four mutations caught. **BUT IT READ ONE FILE — ITS OWN**, so when I wrote
an armour pair into test_gate_diagnostics.py the laptop saw nothing (`ship.py --test` runs no
gitleaks) and run #8 died at the gate, skipping build/scan/staging/production behind it. A rule
enforced on one file is an exception. The sweep now covers every TRACKED file, allowlist derived
from the config, no binary needed — proved by re-introducing the verbatim run-#8 armour.
[2026-10-16]
The repo is **PUBLIC**; `gmail_sa.json` / `colt-bots-*.json` hold REAL keys, are gitignored and
never committed (asserted via `git ls-files -z` — tracked paths here contain spaces and `.split()`
shreds them). `tests/test_secret_scan.py`

**A TEST THAT CANNOT RUN ANYWHERE HAS NO BASELINE, AND NOBODY NOTICES.** `test_caddy_wiring.py`
pins the 2026-08-14 "LIVE shared config is DAMAGED" incident, but the wiring later grew the
`docker ps` / `docker inspect` lines that ASK the container where its Caddyfile is: the extracted
segment re-assigned `$CF` over the fixture's temp file and, with no docker, died `rc 127` under
`set -e`. Skipped on Windows, never reached in CI, so two red tests sat unseen. **SIMULATE docker, do not trim the segment** (class 20): a stub answers `ps`/`inspect`
with the fixture's own path, and the test asserts the stub WAS consulted. The module gate is
`shell_harness_allowed()` (ONE HOME), never `shutil.which("bash")`. Mutations caught: the bare-word
range delete, the assumed path, `sed -i` restoring the inode swap.
[2026-10-15] `tests/test_caddy_wiring.py`

**124 FILES "BROKEN", NONE OF THEM BROKEN.** The first gate run past gitleaks failed the compile
check on EVERY python file: `py_compile` writes the .pyc beside the source, the checkout belongs to
the runner, the container is uid 10001 — EACCES on `__pycache__`, swallowed, rendered as a syntax
verdict with no reason printed (classes 1 and 26; the image even sets `PYTHONDONTWRITEBYTECODE=1`,
which py_compile ignores by design). MEASURED: a file holding `x = 1` fails identically in a
read-only directory. Compile IN-PROCESS from BYTES — no write, no subprocess, and `compile()`
raises on exactly what the gate is for. `do_tests()` also refreshes the git index and regenerates a
stale SBOM, so CI mounts the checkout **`:ro`** and the gate runs against a copy it owns
(`GATE_WORKDIR`) — side-effect freedom as a mount option, not a comment.
[2026-10-15] `tests/test_pipeline_architecture.py`

**"NO node_modules ARE NEEDED" WAS MEASURED OVER ONE DIRECTORY.** True of
`webapp/frontend/tools/*.mjs` (builtins only), false of the engine's five deck builders, which all
`require("pptxgenjs")` — the gate died `MODULE_NOT_FOUND` on the first deck. His box hides it:
`hermes-skills/shodan-assessment/node_modules` is gitignored, so only a fresh checkout shows it.
Dockerfile.ci runs **`npm ci`** from the COMMITTED lockfile (ONE HOME, pptxgenjs 4.0.1) and sets
`NODE_PATH`, because the gate runs against a COPY with no node_modules (MEASURED both ways). The
guard DERIVES the dependency set from every `require`/`import` in gate-run JS — class 35.
**AND THE GATE MUST SAY WHAT BROKE**: `build()` returned `stderr[-300:]`, but node puts the cause
on the FIRST line, so nine failures reported `e._load` / `odule._load` / `ule._load` — one string
cut at three offsets, read as three faults. `node_error()` finds the error vocabulary, then the
frame in this repo. Two of my guards could not fail: the Dockerfile assertions matched the COMMENT
explaining them (class 4, sixth time), and the node_error tests never touched the CALL SITE
(class 9). All four mutations now fail.
[2026-10-15] `tests/test_gate_diagnostics.py`

**HIS GREEN SUITE WAS TESTING A STACK THAT DOES NOT SHIP.** Four tests passed on his PC and failed
in CI, one root cause each, all the same shape — the laptop is not the runner.
**(a) A FLOOR IS NOT A PIN.** `starlette>=1.3.1` let image and laptop land on different releases;
which responses poll for a client disconnect changed between them, so the white-label harness —
which answered `http.request` FOREVER, wrong on every version — raised `Unexpected message
received` only in CI. ASGI says one body then `http.disconnect`; `_receive_for()` is the ONE HOME
and a contract test pins it, because a tolerant starlette passes the endpoint tests anyway. Pinned
`starlette==1.7.0`; a test forbids a floor on anything serving HTTP.
**(b) `ensure_app_requirements()` INSTALLS MISSING, NEVER UPGRADES** (still right), but its
docstring claimed drift "is answered by the image build" — it is not.
`report_requirement_drift()` is wired into ship.py, NAMES each mismatch, silent when they agree,
never blocks.
**(c) A TZ-MIXED DATE IS A PRODUCTION BUG.** `spend_watch.baseline()` parsed with local `mktime`
and formatted with UTC `gmtime`, dropping a real day east of Greenwich (MEASURED: UTC 0.20, Berlin
0.00). The droplet is UTC so the alert was never wrong there; his test asserted the buggy 0.00.
`calendar.timegm`, plus a four-timezone test.
**(d) `jobhuntwow-app/` IS GITIGNORED** — zero tracked files, so asserting its paths answered
"wiring is wrong" when the truth was "not in this checkout" (class 1). In-repo half always
asserted; sibling half skips with a reason. [2026-10-15]

**A CREDENTIAL IS PER-HOST AND PER-ACCOUNT.** `provision()` authorized the CI key on its DEFAULT
host only, so the twin never had it. `deploy_hosts()` DERIVES the list (production `ci_key.HOST`,
staging `stagegate.STAGING`, neither retyped) and says so aloud if staging cannot be derived
(class 37); `authorize_everywhere()` writes all, `check()` proves all, an UNKNOWN on any blocks
`--push`. **The repair must fit the fault**: `ensure_usable()` authorizes first and mints only when
OpenSSH refuses the key. [2026-10-15] `tests/test_ci_key.py`

**FOUR LINES IS NOT A FAILURE REPORT.** That staging job printed `staging unreachable: ***@…:
Permission denied (publickey).` and stopped — a 200-char SLICE of stderr with the account masked,
since DROPLET_USER is a secret. Dead droplet, shut port, missing key, wrong key and unauthorized
key all look identical in that line. `unreachable_report()` MEASURES instead: tcp/22 open or not
(network vs auth, which share no cause), the FINGERPRINT of the identity offered (public — never
key material, this repo is public), ssh's own lines in FULL, then a reading only where the evidence
supports one, naming the repair. **Plus GitHub-native output, emitted BY stagegate.py so the gate
keeps one home and the console is unchanged off Actions**: `::error::` naming the gate, a
`$GITHUB_STEP_SUMMARY` table from `last_evidence()` (same numbers, failures first, appended never
clobbered), and the log tee'd to an artifact (`set -o pipefail`, class 42) because GitHub truncates
long runs. [2026-10-15] `tests/test_gate_diagnostics.py`

**ASSERT THE REMOTE STATE, NEVER DEDUCE IT FROM A DOOR THAT OPENS FOR YOU.** `--fix-ci-key`
re-authorizes BEFORE `check()`, which only proves THIS machine can log in; asserted on source ORDER.
`tests/test_ci_key.py`

**`-i` WAS NEVER PASSED — "which key" had TWO HOMES.** deploy.py read `SSH_KEY`; recover.py (whose
SSH stagegate imports) read `DROPLET_KEY`, which nothing exports, then dropped `-i` when the
`~/.ssh/id_rsa` default was absent. CI deployed production and never staging for four runs, while
`ssh-keygen -y`, the fingerprint and the authorized_keys proof were all TRUE and all about a key
ssh was never told to use — CHECK THE INVOCATION, NOT THE ARTIFACT (class 1).
`recover.ssh_identity()` is the one home; a NAMED key is always offered. **Then read ssh's OWN
account**: `offered_identities()` parses `ssh -v`, on an auth failure only (a timeout never reaches
auth), because "offered nothing" and "offered this, refused" print the identical line and need
opposite repairs; it must drop the inherited `-o LogLevel=ERROR` (or it silences its own trace) and
keep `-i` (or it reproduces the bug). Log VOLUME was never the gap: `stagegate.log` tees the step
log. [2026-10-16] `tests/test_ssh_identity.py` · `tests/test_gate_diagnostics.py`

**"not found" FROM GHCR MEANS TWO UNRELATED THINGS, AND SO DOES "denied".** Staging died pulling
colt-web: CI pushes to `${{ github.repository }}/colt-web` and only `WEB_TAG` was threaded - the
REPOSITORY half was hardcoded in three files (cls 32). GHCR answers
an unauthorised request for a PRIVATE package with **404, not 401**, so a wrong name and a missing
login are ONE message with opposite repairs. `ghcr.py` is the one home for the ref and for
`report()`, which asks anonymously AND with a token and makes the DIFFERENCE the diagnosis, naming
the tags that do exist. Pass BOTH halves, give the job `packages: read`, token on **stdin**, and
SAY SO when pulling anonymously (class 37).
**A STALE CREDENTIAL IS WORSE THAN NONE** [#10]: `GHCR_TOKEN` reached staging only, so
production pulled anonymously, met the droplet's expired ghcr login from the retired
web-deploy.yml and said `denied` for an image the diagnosis proved pullable (`anonymous HTTP
200`). docker sends whatever `~/.docker/config.json` holds, so the anonymous path must
`docker logout ghcr.io` FIRST. The guard DERIVES every GHCR-pulling step and demands a token.
`tests/test_image_ref.py`

**AN UNEXPECTED VHOST NAMES ITS FRAGMENT** (`_declared_in()`), or says none does. MEASURED: 2 of 5
fragments have a committed source; 138 proxy lines live only on the droplet. [2026-10-16]
`tests/test_vhost_attribution.py`

**A PACKAGE NAME ON A `RUN` LINE IS A VERSION NOBODY WROTE DOWN; THE CACHE FREEZES IT.** Run #12:
certifi 2026.7.22 CRITICAL in colttechbot, 2026.10.19 in colt-web, same commit. Every
image installs `-r` a committed exact-pinned manifest (certifi BY NAME though transitive); the
root requirements.txt no Dockerfile read is retired; dependabot/SBOM lists are DERIVED.
[2026-10-22] `tests/test_image_dependencies.py`

## STANDING RULE — always end with the exact command to run — and it is ONE command

After finishing ANY piece of work the user must trigger, end the reply with the exact command,
copy-paste ready, with the right working directory:

    cd "C:\Python SW\Linkedin Scraper"
    python ship.py

**Exactly ONE `python ...` line.** If the work added a new step, WIRE IT INTO ship.py in the same
change instead of telling the user about it. If there is genuinely nothing to run, say
"Nothing to run." explicitly.

## STANDING RULES the operator has given directly (do not re-litigate)

- **"If I ask you something just do it, do not stop and wait for bullshit."** AskUserQuestion is
  for a genuine fork that cannot be resolved from the code or that reverses one of his own
  documented rules. It is NOT for "shall I continue" or "want me to build the next part". Finish
  the work, then report what was built and what it measured.
- **Look at a UI change before shipping it.** `python preview.py` and actually LOOK. Enforced by
  `ui_preview_stamp.py`: ship.py stops with exit 2 when the frontend hash changed since the last
  preview. `--no-preview` overrides deliberately.
- **Every release, the four models write the release notes and they are SENT** (Gmail API to
  feranicus@s4biz.io + Telegram). Same four as the staging panel; asserted identical by test.
- **The staging panel's findings get ACTED ON.** When the panel is right, it becomes a check or a
  fix in the SAME change — never a note. It is advisory and it is wrong often enough to matter, so
  say plainly which half is wrong and why; a model verdict never overrides a deterministic check,
  in either direction.
- **Public-facing copy must not read as AI-written.** BANNED: the em dash, "it's not X it's Y",
  rule-of-three everywhere, uniform sentence length, a neat aphorism as the closing line,
  systematic emoji placement, signposting ("here's the thing"), delve/leverage/robust/seamless/
  landscape/testament/underscore/pivotal, and bullets of identical length and grammar. Every number
  in a post is traced to the measurement that produced it before the post is written.
- **No unsubstantiated comparative claims.** We have never benchmarked the panel against Claude,
  ChatGPT or Gemini, so the site argues ARCHITECTURE, not superiority (UWG §6 / UCP Directive, and
  it would poison the engine's own evidence discipline).

## THE ONE IRREDUCIBLE HUMAN INPUT

Cloud credentials can only be minted by the account owner. Provide them **once** (GitHub secrets /
`golive.secrets.env` / the DO console); after that everything is automated and re-runnable.
Console-only jobs that no script can do: creating scoped per-project DO model access keys, moving
nameservers, and making a GHCR package public.

---

# SETTLED FACTS — do not re-derive, do not re-ask

## The estate

| Fact | Value |
|---|---|
| Production droplet | **64.225.108.200**, FRA1, **4 GB / 2 AMD vCPU / 80 GB** |
| Its name lies | `ubuntu-s-1vcpu-1gb-fra1-01` is the size it was CREATED at. Read the spec, never the name. |
| Staging twin | **165.245.244.174**, FRA1, same size/image/region deliberately |
| Public sites on the shared proxy | cybergod.ai · jobhuntwow.com · jev.best · klimaanlage-preise.de (+ montieren) · s4biz.io · godeyes.ai |
| Shared reverse proxy | `videodead-caddy-1` owns :443 for EVERY site. Its death is a total outage and never an application fault. |
| cybergod.ai DNS | **GoDaddy** (ns07/ns08.domaincontrol.com). `python golive.py` automates it with a GoDaddy API key in `golive.secrets.env`. Do NOT run publish_landing.py for cybergod. |
| Engine images | The engine lives in BOTH `webapp/Dockerfile` (colt-web) and `assess-bot/Dockerfile` (colt-assessbot). Two delivery paths; update both. |
| Event volumes | colt_events (cybergod, jobhuntwow, jev) · polara_events (klima) · s4biz_events (s4biz). Compose PREFIXES volume names with the project; ASK docker, never assume. |
| Loki | ONE instance, `videodead-loki-1`. Every promtail pushes to it. It is the shared substrate and the only thing that holds the PAST. |
| SMTP | **BLOCKED outbound.** Mail goes through the Gmail API in `notify.py`. Never "fix" this to smtplib. |

## The one command per project

    cybergod.ai          cd "C:\Python SW\Linkedin Scraper"        python ship.py
    jobhuntwow.com       cd jobhuntwow-app                          python ship.py
    jev.best             cd "C:\React SW\yantar\jev-best"          python jev.py deploy   (+ jev.py api)
    klimaanlage-preise   cd "C:\Python SW\Klima\klima-shop"        python ship.py
    s4biz.io             cd "...\S4biz new website"                python ship.py
    the whole fleet      cd "C:\Python SW\Linkedin Scraper"        python perseus.py --rollout

`jhw.py deploy` is NOT a subcommand and never was. jev's middleware lives in the **jev-api** image,
so `jev.py deploy` alone does not ship it.

## Diagnostic verbs (READ-ONLY, one ssh session each, from the operator's PC)

    python recover.py            outage triage: ports, crash loops, caddy validate, outside probes
    python fleet.py              per-project: code present? wired in? beating? traffic? attacks?
    python cost_report.py        AI spend; --trace (who can spend) · --whodunit (who did) · --correlate
    python agent_forensics.py    is an actor a human, a script, or an agent
    python authz_audit.py        every route answers 401 anonymously; --local runs it in-process
    python incident_report.py    forensics package for an exposure
    python secaudit.py           kernel/reboot/patch posture, and staging-vs-production twin drift
    python decommission.py       retire a vhost from the shared proxy (dry run by default)

## IAM, quotas, administration

`colt_auth.email_allowed()` is the ONE gate for the bots AND the web app. Four sources:
Colt AE `name.familyname@colt.net` · `PARTNER_EMAILS` (`ud@objectale.ch`) · `PARTNER_DOMAINS`
(`s4biz.io`) · **an ENABLED account in `user_store`** (an administrator creating a named account IS
an authorisation act; it fails CLOSED and can only ever ADD). Extend without code via
`EXTRA_ALLOWED_EMAILS` / `EXTRA_ALLOWED_DOMAINS` in the droplet `.env`.

- `ADMIN_EMAILS = {"feranicus@s4biz.io"}`, committed beside PARTNER_EMAILS and USER_QUOTAS, because
  "who may use this / how much / who decides" is one question and answering it in two files is how
  they drift. Addresses are not secrets; committing them makes them auditable.
- `USER_QUOTAS`: `mr.nvisinc@gmail.com` and `mordechai.rabinovich@rbc.com` capped at 5 each.
  **rbc.com is deliberately NOT in PARTNER_DOMAINS** (that would admit ~90,000 bank staff).
  Both front doors enforce; counting includes failed and running jobs; the lookup fails OPEN.
- Passwords: scrypt in `user_store` on the shared volume. An ASSIGNED password WINS; the shared
  `COLT_BOT_PASSWORD` is a fallback only for identities without one. A DISABLED account still
  counts as existing (or disabling would hand the person the shared password). A broken store
  REFUSES. The password is shown once and never emailed — the OTP already uses that mailbox.
- Authorisation is server-side: every `/api/admin/*` route depends on `_require_admin`, every
  functional route on `_require_ready`. Hiding a nav item is presentation, not a control.

## Secrets

`python set_secret.py NAME` — value on **stdin**, never argv. It upserts BOTH the local
`assess-bot/.env` (the source of truth: `deploy.py --reuse` packs it over the droplet's copy) and
the droplet's `/opt/colt-stack/assess-bot/.env`. `bash -s` reads its SCRIPT from stdin, so the
remote script travels in argv and the value on stdin — the two are mutually exclusive.

## The model chain and its budget

`enrich._FALLBACKS` = **deepseek-3.2 -> llama-4-maverick -> gemma-4-31B-it -> kimi-k2.6**, four
vendors so no shared failure domain. It is the ONE home: compose must not restate it (ship.py fails
the deploy if `- ENRICH_MODELS=` reappears) and ship.py deletes `ENRICH_MODEL`/`ENRICH_MODELS` from
the droplet .env. `GET /api/diag` + `engine_config.py` report the EFFECTIVE config with provenance.

- Entitlement is not visibility: every `anthropic-*` and commercial `openai-gpt-*` returns **403**
  on this account. `model_watch.entitled()` skips probing them and says why.
- Reasoning/thinking models break the strict-JSON contract. Instruct models only.
- Per-model required parameters live in `MODEL_PARAMS` (kimi: the temperature the server names,
  and `response_format` in `_drop`). A 4xx body is the server telling you what it wants — repair
  WHAT IT NAMED, never strip fields until something works.
- This gateway makes `max_tokens` and `response_format:json_object` MUTUALLY EXCLUSIVE. Keep the
  JSON contract, drop the ceiling; a truncated answer is a dirty failure, a timeout is a clean one.
- Budgets: `ENRICH_TIMEOUT=175`, `ENRICH_BUDGET_S=380`, head-weighted 55%, subprocess kill at 430s.
  Never issue a request whose completion time exceeds its own timeout. Throughput has ONE home,
  `enrich.MODEL_TOK_S` (measured 5-26 tok/s, NOT the 100 once assumed) x `TOKENS_PER_FINDING` 600:
  the whole-estate call is skipped when it cannot fit, shards are sized per model, and every run
  logs the rate it measured and flags a table >2x off. [AS37468: all 4 models 'failed' = arithmetic]
- **Recon is bounded too**: `RECON_BUDGET_S` (default 300, ONE home `shodan_recon.ReconBudget`),
  checked at loop boundaries only, fails OPEN, and a stop is `ident["recon_truncated"]` ->
  `summary.partial_estate` -> the deck. A truncated scan never reads as "nothing else is exposed".
  [caixabank.es, 22 min at 55%]
- **So is the whole enrichment phase**: `ENRICH_WALL_S` (default 540, ONE home
  `enrich_parallel.WALL_S_DEFAULT`) from the start of enrich.py; every shard AND retry is sized from
  that deadline when it starts, a call under 45s is not issued, cut ids stay template text and
  `target.enrich_truncated` says so. Two consecutive chain timeouts hand over to the shards. [AS37468]
- **The model sees ONLY `enrich.slim_payload()`** (both paths, never `json.dumps(...)[:N]`), a shard
  that cannot see its findings is not sent, and `enrich.grounded()` rejects prose naming nothing of
  its finding (port, product, CVE, title word): template beats a confident wrong paragraph. [AS37468]
- Cost: `llm_meter.py` at `enrich._call` — the ONE chokepoint, per-direction pricing, unknown model
  priced at the dearest rate we know, `allow()` checked BEFORE the request, fails OPEN on a storage
  fault and CLOSED on the budget. `spend_watch.py` compares a MEDIAN baseline against the DO
  balance delta hourly and names models that are NEW today.

## Shodan plan

`basic` (Freelancer): `vuln:` needs Small Business+, `tag:` needs Corporate. `shodan_plan()` calls
api-info once and SKIPS those queries rather than printing scary warnings.

---

# THE ENGINE'S NON-NEGOTIABLES (zero false positives)

The whole product rests on these. Each was paid for by a customer-facing incident; grep the history
for the domain named in brackets.

- **Absence of evidence is never a finding.** A FAILED lookup reports `UNKNOWN / data-unavailable`
  and claims no gap. [Cogent AS174 graded CRITICAL from a dead DNS resolver]
- **A pivot must PROVE ownership, not just match.** Never let a selector that can match the whole
  internet (a public CA, a shared hoster ASN, a generic favicon, a common word) become an ownership
  anchor. `api.count()` > 2000 = shared by definition. [bibeltv.de, 1003 false IPs]
- **A brand token is an anchor only if it is RARE.** Test rarity against the index, never against
  intuition — the engineer who picks the token speaks the language and cannot hear that it is a
  dictionary word. [abakus = abacus]
- **The HOSTER's identity is never the TARGET's.** whois-org, netblock holder, hoster cert-O and
  PTR domain are evidence about the PROVIDER. Same for the COUNTRY. [rightmart.de, aminagroup.com]
- **`_apex()` is the REGISTRABLE domain (eTLD+1), via `psl.registrable()`.** "The last two labels"
  turns budget.gov.ru into gov.ru and makes a government one customer. When unsure take MORE
  labels: a narrow estate is a recall bug, a wide one puts strangers in a customer's deck.
- **Pinning proves the ADDRESS, not the OBSERVATION.** On provider/multi-tenant infrastructure a
  record becomes a finding only if it names the customer. Fails OPEN only where that was EARNED —
  the customer owns address space AND no stranger's name is already on that address.
- **A discovered domain may ENLARGE the estate; it may never BE the estate.** Per-pivot
  (`PIVOT_MAX_ADD`) and per-domain (`DOMAIN_MAX_ADD`) budgets with whole-unit rollback. A guard
  whose baseline is computed AFTER the untrusted input is merged is not a guard.
- **An audit is a SIGNAL, not an authority.** The FP auditor may flag; deterministic ownership data
  decides. The auditor is never the author and never the author's vendor.
- **An EMPTY estate is an honest, saleable outcome.** "Nothing of yours is externally observable"
  is true and defensible for a shared-hosting customer; a deck full of other people's servers is
  not. Emptiness is not a refusal trigger.
- **A refusal is a FORK, not a failure.** `ScopeRefused` -> exit 4 -> an amber panel with the
  reason, the next step and an explicit operator override. A guard an informed operator cannot
  override is a bug, and one that presents its decision as a malfunction is a different bug.
- **No invented identifiers.** A CVE is cited only if it appears in the raw findings; `_audit_cves`
  strips the rest and emits `hallucination_guard`.
- **A prompt is a string that reaches a human, via the model.** The bible, the system prompts and
  every default are customer-facing surfaces. Guardrail 5 forbids inferring sector, country or
  regulator from infrastructure holder names.
- **Never translate ENUM/LOOKUP keys** (`sev`, `band`, tier, the `COLT` remediation tag). Rename
  the LABEL at render time; translating a key makes rows silently vanish.
- **Headline numbers are computed AFTER the last thing that can change them.** A count taken
  mid-pipeline describes a state the deck never had.
- **Not one packet is sent to the company being assessed.** It is on /partners, in the ToU, in the
  Art. 13 notice and in the signed partner pack, and it is why no customer authorisation is needed.
  `active_probe.enabled()` requires `ACTIVE_PROBE=1` **AND** `ACTIVE_PROBE_AUTH=<written
  authorisation reference>` — a flag says somebody wanted it, a reference says somebody is
  accountable.

---

# DEFENCE AND LAW

- **Detection and reporting scale; retaliation is illegal and pointless.** NEVER scan back, connect
  back, or build tooling for it: StGB §202a/§202b/§303a/§303b and **§202c (possession/creation)**,
  EU Directive 2013/40, US CFAA §1030, Canada CC s.342.1. The lawful path to a human is a complaint
  to the provider, drafted by us and FILED by a person.
- **The shield never touches iptables/nft/ufw.** Amnezia VPN shares the host; enforcement is
  HTTP-layer inside our own container. Asserted by test.
- **An authenticated session is never blocked or tarpitted**, and a route we SERVE is slowed, never
  blocked. Refusing a real page locks a real person out. The evidence is unchanged either way, and
  the exemption is ANNOUNCED.
- **A user agent is attacker-controlled; the PATH is the evidence.** So is the referrer, and so is
  the source: a visit from hosting/VPN infrastructure is not "a person".
- **VARIETY, NOT VOLUME.** A person misses the same few stale paths; a scanner misses hundreds of
  different ones. Two real visitors with 439 and 362 404s are the reason.
- **An exemption from ENFORCEMENT must never become an exemption from OBSERVATION.** `/api/` is
  never blocked (every deploy verifier asserts 401 on /api/me) and it became a hiding place.
- **Models propose, code decides.** `perseus/vet.py` (five fail-closed barriers) plus
  `ruleset.can_promote()` (24h in detection, 3-of-4 quorum across vendors, at least one hostile
  match, ZERO clean hits) and `thresholds()` clamped ON READ. `review()` auto-demotes a rule that
  refused legitimate-looking traffic: full autonomy without a way back is a one-way door.
- **A route that forwards a caller-chosen model id to a paid API is a payment endpoint.** It needs
  authentication AND an allowlist, and the list has ONE home.
- **Deny by default, and PROVE it.** In a framework where a route is public unless somebody
  remembers, an open endpoint is a matter of time. `authz_audit.py --local` is wired into ship.py.
- **Alerts must be received, and benign-every-time is the enemy.** An alert nobody gets is not an
  alert; a warning that fires on every run trains the operator to read past the one that matters.
  Edge-trigger state changes; never re-page a steady state.

---

# THE RECURRING DEFECT CLASSES — the checklist that actually prevents repeats

Every one of these has cost at least one deploy cycle, most of them several. Read this list before
writing a check, a fixture or a diagnostic.

## About checks

1. **A check that cannot see its subject is not a check.** It must not report its own blindness as
   a finding about the system. (logship shipped an empty archive for a week and exited 0; whodunit
   read a dead Loki query as innocence; the coverage metric graded its own homework.)
2. **A check that cannot RUN is not a check.** "skipping", "catalog unavailable", "not installed"
   printed on every run means it has never once executed. And a branch nobody executes is a branch
   nobody has checked: a skip guard written as `subprocess.run([tool...]); if rc != 0: skip` never
   reaches that `if` — subprocess RAISES FileNotFoundError when the tool is absent, so the machine
   it exists for CRASHES instead of skipping. Gate on `shutil.which()` and catch OSError. [2026-10-15,
   found by removing ssh-keygen from PATH, which also exposed an undefined `pytest` the F821 gate
   had just caught in the same dead branch]
3. **A check that cannot FAIL is not a check.** If the denominator is produced by the thing being
   measured, it is not a measurement. Prove a gate by breaking the thing it guards.
4. **Assert the PROPERTY, never a string the error text also contains, and never a position.**
   Anchor on the CALL SITE, resolve cross-module calls by AST, strip comments AND docstrings before
   grepping — a check has matched its own explanatory comment five separate times here.
5. **Print the comparison you made, never a raw dump plus a separately computed verdict.**
6. **A verdict is the FIRST line at column zero; notes are indented and come after.** A wildcard
   branch must FAIL, never score an unrecognised answer as a pass.
7. **A detail that renders identically whether or not anything was measured is templated output.**
   And a PASS detail must not carry failure vocabulary — another check parses it.
8. **A name is read far more often than a detail.** A check whose name overclaims teaches the
   outage (`config_reread` -> `config_write_ordering`; `config_change_propagates` ->
   `guard_write_path_reloads`).
9. **Behaviour AND wiring.** shield.py was fully tested while nothing asserted the middleware
   called it. A control that is correct and unreachable is not a control.
10. **A gate must render its own PASS on the operator's console** (cp1252) and must distinguish a
    CRASH from a FINDING.
11. **The last exit must follow the last check.** 73 checks once ran after the only `sys.exit(1)`.

## About tests and fixtures

12. **A fixture that does not reproduce the condition under test is a test of the fixture.** Prove
    the fixture first (assert the breaker actually broke).
13. **A negative test that passes because of ANOTHER guard measures that other guard.** Defeat
    every guard on the path. And a mutation that does not violate the property proves nothing.
14. **Run the BASELINE first.** A suite that is already red scores every mutation as "caught".
15. **A test that depends on a race, or on a four-digit needle in a haystack containing a clock, is
    a coin flip that teaches the operator to re-run rather than read.**
16. **A `finally` cannot survive SIGKILL, and `open(path,"w")` truncates before it validates its
    own arguments.** Any harness that edits real files writes to a temp file and `os.replace`s it,
    self-heals on import, and is followed by a scan for EVERY marker it could have left.
17. **A test that encodes a doctrine must be REWRITTEN when the doctrine is corrected**, with the
    old reasoning kept beside it — deleting it loses why.
18. **Tests must not reach the internet**, and the stub must be re-applied after every
    `importlib.reload`.

## About platform (eight wasted ships, one root cause)

19. **Ask "which machine, which interpreter, which toolchain?" before telling the operator to run
    anything.** Green in a Linux sandbox is not evidence about his Windows box. Prefer a gate
    inside the container/CI that installs its own dependencies.
20. **SIMULATE the platform, do not skip it.** `monkeypatch.setattr(os, "replace", windows_like)`
    proves Windows behaviour on Linux. A `sys.platform` skip hides the defect from the one machine
    that needs it.
21. **Line endings are the platform's business.** Any fixture that will be hashed, diffed or parsed
    is written in BINARY. `git archive` applies autocrlf unless you pass
    `-c core.autocrlf=false -c core.eol=lf`. Payloads to `bash` go over stdin as BYTES.
22. **POSIX-only APIs** (`os.uname`, `/proc`, `fcntl`, a Windows path passed to `bash -n`) fail on
    the machine that runs the tests. Guarded by an AST test.
23. **Console encoding**: ship.py sets `PYTHONIOENCODING`, reconfigures its own streams, and every
    `subprocess.run` passes `encoding="utf-8", errors="replace"`.
24. **A declared dependency the operator's Python lacks is an operator step.**
    `ensure_app_requirements()` installs MISSING packages only, never upgrades.

## About diagnosis

25. **A traceback's cause is its LAST line.** `tail -N` of a build log shows stack frames; grep for
    the error vocabulary FIRST, then show context.
26. **A diagnostic that does not NAME its subject sends the next investigation down the wrong
    road.** Print the path, the model, the address, the arithmetic.
27. **When a number surprises you, read the vendor's own breakdown before auditing your own code.**
28. **Source that NAMES a thing proves it COULD happen; it does not prove a process DID.** When
    half the evidence-gathering fails, say so instead of concluding from the half that worked.
29. **Before naming a cause, ask what would have to be TRUE for it to be the cause** — not what
    merely fits. Measure, then fix. I have twice started building on an unverified cause.
30. **A snapshot cannot answer a question about the past.** Loki holds the past; open sockets and
    container start times do not.
31. **Both terms of a ratio must be measured over the same period**, or the number describes when
    we started looking.

## About code and configuration

32. **ONE HOME.** A value with several homes drifts and the newer one always loses (ENRICH_MODELS
    had four; the document language had six; the shield's class table had two). If a value has a
    documented home in code, compose must not restate it, and prose must never restate what a
    selector already lists.
33. **A fix recorded in one project's CLAUDE.md is not applied to the sibling until somebody
    applies it.** For a platform- or estate-shaped defect, grep BOTH repos for the same shape.
34. **Follow the VALUE end-to-end — UI -> API -> persistence -> engine — and assert it at each
    hop.** A capability the engine has and the API discards is invisible to every engine test.
35. **When a change needs N edits, DERIVE N from something authoritative.** Counting by hand is how
    the fourth wiring point is missed (`_APP_ROUTES`, `.dockerignore`, `INCLUDE`, the sitemap).
36. **READ the signature.** Seventeen times in this workstream I have called a helper that returns
    a different shape than I assumed (`run()` -> int, `ssh_script()` -> 3-tuple, `getJSON` vs
    `postJSON`, `useT()` -> a 3-tuple, `classify()` -> a list). Writing a guard around a guess is
    worse than reading six lines, because it looks like care.
37. **A feature guarded by `if <derived thing>:` fails silently by construction.** Log the skip or
    assert the wiring.
38. **`except: pass` on an observability write is a self-inflicted blind spot.** Print once.
    A swallowed exception returning a plausible default is indistinguishable from a measurement.
39. **A silent write to the wrong place is worse than a permission error.** `os.makedirs` succeeds
    into a container's ephemeral overlay. ASK the container where its log/mount/volume actually is;
    never assume a path or a compose prefix.
40. **In-process locks do not serialise two processes.** Anything a `docker exec` can touch is
    written atomically (temp + `os.replace`, with the extension preserved — pptxgenjs, ffmpeg and
    pandoc rewrite a path whose extension they do not recognise).
41. **Never retry a non-idempotent remote command.** A timeout is an UNKNOWN outcome, not a
    failure. Reads and probes may retry; anything that creates, extracts, deletes or deploys
    reports the unknown state instead.
42. **Every remote call needs a HARD `timeout=`** sized to what that call legitimately takes, and
    **never judge success through a pipe** (`cmd > log 2>&1; rc=$?; tail log; exit $rc`).
43. **SSH SESSION COUNT is the only lever on Windows** (no ControlMaster; OpenSSH 9.8 enables
    PerSourcePenalties by default). Never add an `ssh()` to a step that already opens one — add a
    section to its batch. Payload in argv, data on stdin.
44. **A literal `%` must be `%%` — but only in a %-FORMATTED string.** The rule has a precondition.
45. **A layout row is ARITHMETIC.** Add up brand + every control + gaps in the LONGEST language
    before shipping; German and Polish overflow first. `tools/header_layout.mjs` measures it.
46. **In a grid or flex parent a new child is a LAYOUT PARTICIPANT, not an overlay**, and a
    `z-index` means nothing until you know which stacking context it is in. A popover inside a
    sticky ancestor must be portalled.
47. **A selector legitimately has SEVERAL rules.** The question is "does ANY rule set this
    property", never "does the first one".
48. **PARSE is not RUN.** An undefined identifier and an invalid colour are legal JavaScript until
    they execute. Render the page, execute the loop, read the artifact.
    **IMPORT is not RUN either, and MODULE ORDER IS EXECUTION ORDER.** `if __name__ == "__main__"`
    fires where it APPEARS, so a def below it does not exist when that module's own main() runs —
    invisible to an importer, fatal to `python <script>.py`. ship.py imports stagegate and calls
    run(), so only CI could see `NameError: last_evidence`; ruff F821 cannot, the name IS defined,
    merely later. The guard must be the LAST statement in the file (asserted across every root
    script), and a script path is verified by RUNNING it as a script. [2026-10-15]
49. **READ THE DELIVERED ARTIFACT.** Rich finding text is not a good deck. Two slides of one deck
    disagreed; a raw enum reached a customer slide; 46 text boxes were truncated; a partner's deck
    kept our teal. Every one was invisible in the logs and obvious in the file.
50. **An OPTIONAL lookup may make a page more accurate, never less — and never slower than that
    page's own budget.** It parses inside its own `try`, it cannot raise past its caller, and it
    never runs on a request path: a background refresh fills a cache, the request reads it. A status
    page that hangs is its own outage, and a 500 from a nice-to-have is worse than the gap it filled.
51. **A route that COMPUTES is not verified by a route that answers 401.** Liveness is not the
    feature. If a deploy does not exercise the page, the page ships broken behind a green suite —
    and it did, three times. Run it where it runs, with the real env, and let `set -e` fail the ship.
52. **A handler must be able to describe its own failure.** A 500 with an empty body costs rounds
    of guessing: catch, print the traceback, and RENDER the cause with no invented rows.
53. **THE OBSERVER MUST BE OBSERVED, and a feature nobody has seen working is OFF.** The fleet page
    was the one request on the box with no telemetry of its own, so when it broke there was nothing
    to read and I guessed for three ships. Every call now emits `evt=fleet_status` through the same
    writer as access logging (and must not count its own lines as traffic), and the watch loop pages
    on the transition. A lookup that has never been observed succeeding defaults off, behind an env
    var, not behind a redeploy.
54. **A single-FILE bind mount follows an INODE, so `sed -i` is not an in-place edit.** It writes a
    temp file and renames it; the container then reads a file nobody can see, and the only repair is
    restarting the shared proxy that owns :443 for every domain. Filter to a variable and truncate
    the existing inode with `>`, after a size floor so a failed substitution cannot blank it.
55. **`docker exec <ct> <path>` resolves inside the CONTAINER, so the container's image must carry
    that path.** perseus.service ran the hub from `/opt/perseus`, which existed only on the HOST;
    it died on ENOENT every night for weeks while the installer printed "daily cycle armed", and the
    five sidecars enforced an empty blocklist the whole time. Ask the container, at the path the
    clients read, and fail the ship on `cycle 0`.
56. **One response is built from ONE snapshot.** Reading the same cache twice inside one handler
    lets a refresh land in between and the two halves then describe different moments — `live`
    beside zero traffic. Read once, pass it down.

---

# WHAT LIVES WHERE (the map, so nothing has to be rediscovered)

## cybergod.ai (this repo)

- `hermes-skills/shodan-assessment/scripts/` — the ENGINE. `run_assessment.py` (orchestrator),
  `shodan_recon.py` (discovery + ownership gates + `classify()`), `enrich.py` + `enrich_parallel.py`
  (LLM prose, the ONE chokepoint for spend), `audit_fp.py`, `clarify.py`, `psl.py`, `scope_deny.py`,
  `group_discovery.py`, `asn_sources.py`, `email_auth.py`, `cert_intel.py`, `naming.py`,
  `active_probe.py`, `compliance_*.py`, `build_*_deck.js`, `build_*_html.js`, `deck_i18n.js`,
  `i18n/`, `deck_langs.py`, `proteus.py` (White Label), `run_log.py`, `demo_build.py`,
  `cost_ledger.py`, `engine_config.py`, `model_probe.py`.
- `webapp/backend/app/` — FastAPI. `main.py`, `auth.py`, `store.py`, `telemetry.py`, `visitors.py`,
  `alerts.py`, `notify.py`, `shield.py` + `shield_panel.py` + `shield_console.py`, `slow_store.py`,
  `siege.py`, `fleet.py`, `brand.py`, `llm_meter.py`, `llm_events.py`, `spend_watch.py`,
  `attack_digest.py`, `threat_intel.py`, `abuse_report.py`, `ip_reputation.py`,
  `security_headers.py`, `daily_report.py`, `release_notes.py`, `geoip.py`, `perseus_client.py`.
- `webapp/frontend/src/` — React. `i18n.jsx` + `locales/` + `legal.jsx` + `legal-locales/` +
  `partners-locales/` (six UI languages, 100% enforced), `components/`, `pages/`, `styles.css`.
  Gates in `tools/`: i18n_catalogue, i18n_audit, header_layout, contrast_gate, canvas_smoke,
  api_contract, shipped_shell, partners_gate, render_gate.
- `perseus/` — the hub (`hub.py`, `ruleset.py`, `vet.py`, `abuse.py`, `incident.py`, `client.py`).
  Three timers, three verbs: `--cycle` daily 04:40 · `--weekly` Sun 05:20 (re-vet live rules against
  today's routes, retire what a month never matched) · `--watch` every 10 min (four-vendor consensus
  on ONE live incident; proposes DETECTION only, capped at 12 incidents / $0.30 a day).
- `deploy/` — `caddy/*.caddy` (committed blocks), `caddyguard/agent.py`, `dbbackup/agent.py`,
  `logship/agent.py`, `hostpath.py` (the ONE volume/mount resolver).
- Root verbs: `ship.py` (the orchestrator) and the diagnostics listed above.

## The proxy, and the outage that shaped everything

The shared Caddyfile is **GENERATED, not edited**: `/opt/caddyguard/blocks/<project>.caddy`
fragments, assembled, validated in the container's own image AND env, written IN PLACE (a
single-file bind mount pins the inode), reloaded through the admin API, then compared.

**CONFIG HAS THREE HOPS and a check must say which one it measured:** host file -> container file
(the MOUNT) -> running config (the RELOAD) -> what is SERVED. `caddy validate` proves none of them.
Consistency across the hops is not AUTHENTICITY — the fragment is also compared to the committed
block. Caddy reads its config only at start, so a file damaged at 16:15 can serve happily from
memory until a 04:22 kernel reboot takes six domains down together. That is why the watchdog runs
every 10 minutes, why patchwatch refuses to reboot into an invalid config, and why the uptime
workflow runs OFF-BOX.

---

# LANGUAGES

- **Interface: six** (en, de, it, fr, es, pl), 100% enforced by the catalogue + audit gates.
- **Documents: three** (en, de, ru). A document language needs `scripts/i18n/<code>.json` AND a
  `LANG_*` block in `enrich.py`; `deck_langs.doc_langs()` derives the list and fails closed —
  half a language is not a language. Served at `GET /api/langs`; `/api/jurisdictions` likewise.
- Interface language != document language. Prose must never restate what the selector lists.
- A COMPOSED string is not a dictionary key: translate the PARTS (the regex proposes, the
  dictionary decides) and let the pack declare its own plural grammar.

---

# COMPLIANCE

`compliance_enrich.JURISDICTIONS` is ONE registry (reference document, ordered regimes, which get
their own deck, prompt framing, eyebrow). `compliance.json` carries `order`/`decks`/`eyebrow`, so
**no deck builder holds a regime constant**. Fails CLOSED to the EU set. EU = NIS2 / CRA / EU AI
Act; CA = OSFI B-13 · E-21 · B-10 · Integrity & Security · Incident Reporting · PIPEDA · Law 25 ·
CCSPA. The reference's §6.4 "must never appear" list is a BUILD GATE. Not legal advice, and the
framework set on the findings deck is chosen from `d.target.country` — UNKNOWN is NOT the EU.

---

# HONEST LIMITS (state these, do not paper over them)

- Shodan cannot see a vhost behind an SNI-only front end. "Shared hosting, not externally
  observable" is the honest line.
- No public API is authoritative across all five RIRs; `clarify.py` always asks on a target with
  its own address space.
- DKIM is presence-only: a selector cannot be enumerated, so "not found" is NOT DETERMINABLE.
- view-source cannot be disabled by anyone. The boundary is the SERVER; what was worth fixing was
  source maps, secrets in the bundle and shipped HTML comments, and all three are now gated.
- The five projects share ONE DigitalOcean model access key, so DO's own per-key usage cannot
  attribute the invoice. Scoped, VPC-restricted per-project keys are a console job.
