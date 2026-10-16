# The deploy architecture, 2026-10-15

## What was actually wrong

Not an opinion — one real ship, measured from both logs:

| Container | Shipped by | When |
|---|---|---|
| `colt-web` | the **laptop**, built **on the production host** | 11:52:00Z |
| `colt-assessbot`, `colt-cassandra` | **GitHub Actions**, GHCR images `69617a3d561c` | 11:58:28Z |

Two owners, one droplet, six minutes apart. `teamlock` did not stop it because the laptop released
the lock at ~11:53 and CI started at 11:58. Nothing but timing kept them apart.

Three defects sat underneath that:

**1. The required check was weaker than the laptop gate.** The branch ruleset requires
`quality-and-secrets`. That job ran:

```
ruff check . || true          # a check that cannot FAIL is not a check   (defect class 3)
node --check *.js             # PARSE is not RUN                          (defect class 48)
python -m compileall <list>   # a hand-written subset that drifts         (defect class 35)
python -m pytest tests -q     # the unit suite only - none of the 37 engine gates
```

A commit `python ship.py` would refuse could turn that check green. A required status check weaker
than the local gate is worse than no check: it converts "somebody looked" into "a robot approved".

**2. The one internet-facing image was the one image CI never saw.** `colt-web` was compiled on the
production host at deploy time. `deploy_web_direct.py` already said so in a comment and mitigated it
by running Trivy on the droplet after the build. Scanning after the fact on production is not the
same as never putting an unscanned artifact there.

**3. Deploy logic had two homes.** `web-deploy.yml` carried inline `ssh`/`scp`/`docker compose`
doing what `deploy_web_direct.py` does. Two writers for the shared Caddyfile is how six domains go
down together.

## The architecture

```
 push to main
     │
     ▼
 ci.yml :: quality-and-secrets          ← THE GATE OF RECORD (the name the ruleset requires)
     │   docker build -f Dockerfile.ci          pinned toolchain, committed
     │   docker run --network none ... python ship.py --test
     │       └─ the operator's OWN test phase: 37 engine gates + 1069 unit tests
     │          no secrets, no network, SHIP_GATES_OFFLINE=1 forbids the one droplet write
     ▼
 pipeline.yml
     ├─ gate        waits for quality-and-secrets to be green on this SHA
     ├─ build       colt-web + colttechbot + cassandra, ONCE, tagged <sha12>
     │              SBOM + SLSA provenance attestation, pushed by digest
     ├─ scan        Trivy (pinned, checksum-verified) per image; CRITICAL stops the promotion
     ├─ staging     environment: staging · teamlock-grouped
     │              stagegate.py → deploy twin → health → REBOOT → re-verify → 4-model panel
     │              WEB_TAG makes the twin PULL the same artifact production will run
     └─ production  environment: production (required reviewer)
                    teamlock.py --acquire
                    deploy_web_direct.py --ghcr <sha12>     pulls, never builds
                    deploy.py --ghcr <sha12>                same commit, same artifacts
                    caddyguard.py                           shared proxy still healthy
                    teamlock.py --release  (if: always())
```

### The four properties, each asserted in `tests/test_pipeline_architecture.py`

1. **One gate.** CI runs `ship.py --test`, it does not re-list its gates. One home, two callers.
2. **One automatic path to production.** `deploy.yml` and `web-deploy.yml` are now
   `workflow_dispatch` only — a manual fallback, not a second robot.
3. **One artifact.** Staging and production run the same bytes CI built and Trivy scanned.
   Promotion selects a tag; it never rebuilds.
4. **One deploy at a time.** Both droplet jobs share the `production-droplet` concurrency group
   *and* take `teamlock`, because a concurrency group cannot see a laptop.

Fifteen mutations were run against those tests. Three escaped on the first attempt because the
assertions matched a step **name** ("Gates (python ship.py --test)") or an explanatory **comment**
("# --network none is deliberate") instead of the command — defect class 4, in the very file
written to prevent it. The tests now read `run:` only.

## Why CI does not re-list the gates

`do_tests()` is ~1000 lines invoking 37 gate scripts, each written because something reached a
customer. Copying that inventory into YAML creates two homes for "what must pass before we ship"
(defect class 32), and the newer one always loses. Measured by AST before relying on it: `do_tests()`
makes **zero** ssh calls, and the single branch that could write to the droplet (installing
`DO_API_TOKEN` via `set_secret`) now refuses out loud under `SHIP_GATES_OFFLINE=1`. A side-effect
free gate phase is what makes it safe for a runner to execute on every pull request.

## Secure by design, concretely

- **Least privilege.** `permissions: contents: read` at workflow level; `packages: write` /
  `id-token: write` / `attestations: write` only in the build job.
- **The gate holds no credential.** No secret is passed to the job that executes repository code,
  and it runs `--network none` as a non-root user. It cannot change anything because it has nothing
  to change anything with.
- **Provenance.** SLSA attestation per image, pushed to the registry, verifiable with
  `gh attestation verify oci://… --repo feranicus/electronic`.
- **The scanner is a dependency too.** Trivy is version-pinned and checksum-verified, in CI and on
  the droplet, because this scanner was compromised in Feb/Mar 2026.
- **The key install has one home.** `.github/actions/ssh-key` writes the secret from an env var as
  bytes, prints the installed key's **fingerprint** (public information), and refuses with a named
  cause before any deploy step if OpenSSH cannot derive its public half.

## Decided: the PR flow (`shipflow.py`)

`python ship.py --pr` (or `SHIP_FLOW=pr` to make it the default) replaces the direct push with:

```
branch ship/<user>-<stamp>-<slug>
  -> push
  -> open PR          (reuses an existing one, so a re-run resumes)
  -> WAIT for quality-and-secrets on that SHA
  -> squash merge + delete the branch
  -> pipeline.yml deploys
```

`main` then only ever receives commits a green gate has already seen — for everybody, with no
admin bypass and no `Bypassed rule violations` line.

**The merge is the deploy, and ship.py stops there.** `pipeline.yml` fires on push to `main`. If
PR mode also deployed from the laptop, one commit would again produce two deploys to one droplet —
the defect measured at the top of this document. A test asserts the PR branch of `main()` calls
none of `do_web`, `do_bots`, `do_verify`, `tag_known_good`.

**Nothing merges on an unknown state.** `check_state()` returns `pass` only for a completed check
whose conclusion is `success`. Pending, missing, cancelled, timed out, `action_required`, a null
conclusion, an unreachable API and a non-JSON response are all "not green". `skipped` is the one
that matters most: a `paths:` filter or a cancelled workflow produces it, and a gate that did not
run is not a gate that passed. Nine mutations were run against these guards, including "treat
skipped as green", "bad JSON reads as pass" and "timeout returns ok"; all nine fail the suite.

**Failure is recoverable.** A red gate leaves the branch and the PR in place — they are the only
artefact that says what failed — and the timeout message says the work is pushed and the command
is resumable.

## The ruleset setting that still needs your hand

From GitHub's own rules reference:

> "Required status checks ensure that all required CI tests are passing **before collaborators can
> make changes to a branch** targeted by your ruleset."

A freshly pushed commit has no check runs yet, so a required status check can never be satisfied by
a **direct push**. That is why every `ship.py` push prints `Bypassed rule violations`. As repo admin
you bypass it; a collaborator cannot, so their first `python ship.py` would run all 1069 tests,
deploy to staging, and then be **rejected at the push** — after the staging gate, before the
safe-point.

The PR flow above removes that wall: a PR's head commit **does** get check runs, so the rule is
satisfiable the normal way and nothing needs bypassing. Two settings still have to be changed by
hand, because only the repo owner can:

1. **Add the collaborator** with **write** access (not admin). Write is enough to open a PR, push a
   branch and merge a green one. Admin would let them edit rulesets and bypass the gate, which is
   the thing the gate exists to prevent.
2. **Turn on "Require a pull request before merging"** for `main`, and take yourself off the bypass
   list. Until you do, the direct path still works for you — which is convenient and is also how
   `main` ends up holding a commit the gate never saw. The flow is already written and tested;
   this setting is what makes it the *only* way in.

Keep `ship.py --direct` for the day the pipeline itself is what is broken. That is a deliberate
override by an informed operator, which is different from a bypass nobody decided on.

### Residual risks, named rather than papered over

- **The deploy key is root on a shared droplet.** `colt_ci` lives in `DROPLET_SSH_KEY`, and that
  box also runs Amnezia VPN, VideoDead, joplin and six public domains. Write access to this repo is
  therefore effectively root on production, via any workflow that can read the secret. The
  `production` environment's required reviewer is what stands between a merged PR and that key.
- **Squash merge creates a new commit** that was never gated in that exact form, so `ci.yml` runs
  again on `main` and `pipeline.yml` waits for it. That is correct, not redundant.
- **The gate image is unproven until the first CI run.** `Dockerfile.ci` has not been built
  anywhere yet; `ship.py --test` was verified to run headlessly offline on Linux, but the container
  build itself has never executed.

Also still unexplained, from `caddyguard`: `jobhw.org` and `www.jobhw.org` are served by the shared
proxy but are not on the committed roster.

---

## 2026-10-16 — the laptop's own login is not evidence about the runner

`python ship.py --fix-ci-key` ran `ci_key.check(_kp)` first and did nothing when it passed. That
reads as reasonable and is wrong: `check()` proves THIS MACHINE can open an ssh session to each
droplet. It says nothing about whether the CI key's public half is still in that droplet's
`authorized_keys`, because the operator's own identity is what opened the door.

The consequence, on four consecutive pipeline runs: the staging job failed
`***@165.245.244.174: Permission denied (publickey)`, and every re-run of `--fix-ci-key` reported
the key healthy on both hosts and changed nothing.

### What the new diagnosis eliminated, by measurement

`stagegate.unreachable_report()` printed enough to kill three hypotheses outright:

* **the account** — the report's own sentence contained the literal word `root`, and GitHub
  rendered it `***`. Actions masks secret VALUES, so the redaction itself proved
  `secrets.DROPLET_USER == "root"`. Both sides use the same account.
* **the key identity** — the runner's fingerprint, `SHA256:7uwyj5g…
  github-actions-deploy-cybergod (ED25519)`, is byte-for-byte the one the laptop authenticated
  with.
* **the key file** — `.github/actions/ssh-key` writes it with `printf '%s\n'` from an env var,
  `chmod 600`s it, and refuses the job unless `ssh-keygen -y -P ""` derives its public half. So
  it is neither mangled nor unreadable nor too-permissive.

`tcp/22` was `OPEN`. What remains is the one thing none of those can see: the public half is not
in `root@165.245.244.174:~/.ssh/authorized_keys` at the moment CI runs.

### The fix

`--fix-ci-key` now calls `ci_key.authorize_everywhere()` BEFORE `check()`, unconditionally. It is
idempotent by construction (`grep -qxF … ||`) and costs one ssh per host. The rule: **assert the
remote state, never deduce it from a door that opens for you.**

### A mutation escaped first

The guard asserted that no enclosing `if` whose test contains the string `"check"` wraps the
authorize call. The obvious revert walks straight past it, because the reverted code reads

    _ok_key = bool(_kp) and ci_key.check(_kp)
    if not _ok_key:
        _ok_authz, _rows = ci_key.authorize_everywhere(_kp)

and `not _ok_key` contains no `"check"` at all. Defect class 4, committed by me while writing a
guard against defect class 4. SOURCE ORDER is the property and is unambiguous: the first
`authorize_everywhere` line number must precede the first `ci_key.check` line number. The same
mutation now fails.

---

## 2026-10-16 — an unexpected vhost must name its source, and 73% of the proxy is unversioned

caddyguard's roster check reported, on four consecutive ships:

    [!] 2 host(s) served that are NOT on the committed roster: jobhw.org, www.jobhw.org
        On a shared proxy an unexpected vhost claims traffic and certificates for a name nobody
        committed. Add it to the roster, or find out who wrote it.

Nobody ever found out who wrote it. The check was telling the operator to go looking for a fact it
already held: the guard ASSEMBLES the live file from the fragments in `FRAG`, so whichever
fragment declares that hostname was one `os.listdir` away. Four runs of an unactionable warning is
precisely the benign-every-time alert CLAUDE.md names as the enemy — it teaches the operator to
read past the line that matters.

`_declared_in()` answers it, and separates two cases with opposite remedies:

* **declared in a fragment** — that fragment is on the droplet; if it has no committed source,
  part of the shared config is unversioned (operating principle 2).
* **declared by NO fragment** — something wrote around the guard, and the next `assemble` silently
  drops the vhost. Reporting that as "declared in X" would be a lie with an outage attached.

It refuses to answer when it cannot read `FRAG` (class 1), and matches site HEADERS rather than
substrings, so a hostname in a comment or in an `upstream` is not mistaken for a declaration.

### The larger finding, measured while fixing it

The proxy assembles from five fragments. Only TWO have a committed source in `deploy/caddy/`:

| fragment on the droplet | lines | committed source |
|---|---|---|
| `_base`            | 95 | **no** |
| `colt__cybergod`   |  7 | yes — `deploy/caddy/cybergod.caddy` |
| `jhw__jobhuntwow`  | 44 | yes — `deploy/caddy/jobhuntwow.caddy` |
| `polara__klima`    | 16 | **no** |
| `s4biz__site`      | 27 | **no** |

138 of 189 lines — 73% — of the shared reverse proxy's configuration exist only on the droplet.
The RESTORE step compares exactly two fragments against committed blocks, which is why its output
only ever mentions `jhw` and `colt`. CLAUDE.md's claim that "the fragment is also compared to the
committed block" is true for two projects out of five, and `jobhw.org` is simply the first symptom
of the gap that is visible from outside.

Closing it means pulling `_base`, `polara__klima` and `s4biz__site` into `deploy/caddy/` — which
needs a read of the droplet, and a careful one: Caddy fragments can carry basicauth hashes and
header tokens, so they go through gitleaks and a human read before they are committed, never a
blind `scp` into git.

---

## 2026-10-16 — the cause: `-i` was never passed, because two files disagreed on the variable name

Four pipeline runs died on `***@165.245.244.174: Permission denied (publickey)`. Every check said
the key was fine, and every check was right — about the wrong thing.

`recover.py`, which `stagegate.py` imports its ssh command from, built it like this:

    KEY = os.environ.get("DROPLET_KEY", os.path.expanduser("~/.ssh/id_rsa"))
    SSH = ["ssh", ...]
    if os.path.exists(KEY):
        SSH += ["-i", KEY]

`deploy.py` — the production path — reads a DIFFERENT variable:

    SSH_KEY = os.environ.get("SSH_KEY", "")
    SSH_OPTS = (["-i", SSH_KEY] if SSH_KEY else []) + [...]

Every workflow exports `SSH_KEY`. **Nothing in the repository exports `DROPLET_KEY`.** So on a
runner, `KEY` fell back to `~/.ssh/id_rsa`, which does not exist there, the `if` was False, and
`-i` was silently dropped. Under `BatchMode=yes` with no agent, ssh then offered no identity at
all and the droplet answered exactly what it should: `Permission denied (publickey)`.

That is why CI could deploy PRODUCTION and never STAGING. The two paths were never using the same
ssh command.

### Why four rounds of diagnosis missed it

Every piece of evidence examined the **artifact** and none examined the **invocation**:

* the composite action wrote the key, `chmod 600`, and proved it with `ssh-keygen -y` — true;
* `unreachable_report()` printed its fingerprint, `SHA256:7uwyj5g…` — true;
* `--fix-ci-key` confirmed the public half was present in `root@165.245.244.174`'s
  `authorized_keys`, and that this laptop could authenticate with it — true.

All three describe a key that ssh was never told to use. Defect class 1, in the diagnostic itself:
a probe that cannot see its subject must not answer, and "the key file is good" is not an answer to
"which identity did ssh offer".

Two classes caused it and one hid it:

* **32 (ONE HOME)** — "which private key" had two homes, `SSH_KEY` and `DROPLET_KEY`, and the
  newer one lost.
* **37** — `if os.path.exists(KEY)` is a feature behind a derived condition that fails silently.
* **1** — every check looked at the file.

### The fix

`recover.ssh_identity()` is the one home: precedence `SSH_KEY` → `DROPLET_KEY` (kept so nothing
that set it breaks) → `~/.ssh/id_rsa` if it exists → `("", "none (ssh will choose)")`. A NAMED key
is always passed with `-i`, even when the path is missing, so OpenSSH's own error names the file
instead of this module quietly offering nothing. The empty case reports itself as empty.

`unreachable_report()` now prints an `offering` line — the identity ssh is actually given and
where it came from — above the fingerprint, and flags a mismatch when `SSH_KEY` is set but
something else is being passed. With no identity named it says so in as many words.

### Guards

`tests/test_ssh_identity.py`, with the workflow pairing DERIVED rather than hand-listed: a
workflow that INSTALLS the deploy key must NAME a variable the resolver reads. Mutations caught:
reading `DROPLET_KEY` only, re-gating `-i` on the file existing, making "no identity" look like a
path, and stripping the `SSH_KEY` lines from `pipeline.yml`.

Two of my own guards were wrong first, both class 4. One looked for `'"-i"'` in `ast.unparse`
output, which normalises quotes to single. The other scoped workflows by grepping for
`python <script>.py` and flagged `uptime.yml` — whose only match is the advisory text of its own
alert, "Run: python recover.py --fix-caddy". That workflow probes from outside the droplet
deliberately and rightly has no key.

---

## 2026-10-16 — "not found" from GHCR means two unrelated things

### What happened

The `-i` fix from earlier the same day worked. The staging job's own log proves it:

```
19 == preflight: ssh ***@165.245.244.174 (hard 25s timeout, 3 tries) ==
20   ssh OK — containers: staging-caddy, colt-web, s4biz-promtail, s4biz-web
```

Then it died four lines later on something else entirely:

```
23  Image ghcr.io/feranicus/colt-web:c6d051e729cc Pulling
24  failed to resolve reference "ghcr.io/feranicus/colt-web:c6d051e729cc": not found
28 [X] the GHCR deploy failed (rc=1). Compose is idempotent; re-run.
37    [!] staging build failed (exit 1)
41 GATE: NO-GO
```

The operator's reaction was the correct one: *"it's clear that we are walking in circles."* Three
failures in a row, three different causes, and each log named the symptom rather than the subject.

### The cause

`pipeline.yml` sets `IMAGE_OWNER: ghcr.io/${{ github.repository }}`. `github.repository` is
`feranicus/electronic`, so the build job pushes:

    ghcr.io/feranicus/electronic/colt-web:<sha>

The pull came from `docker-compose.web.yml`, which hardcoded:

    ghcr.io/feranicus/colt-web:${WEB_TAG:-latest}

Two different GHCR packages. The pipeline threaded `WEB_TAG` from the build job to the droplet and
nothing else — the **repository** half of the name was written out independently in three files
(`docker-compose.web.yml`, `.github/workflows/web-deploy.yml`, `deploy_web_direct.py`), none of
which the new pipeline updated. Defect class 32, and the newer home lost as it always does.

### Why it cost a whole run instead of one line

**GHCR answers an unauthenticated request for a private package with 404, not 401.** That is
deliberate — otherwise anyone could enumerate private packages by probing for 403s. The
consequence is that docker's `not found` covers two faults with nothing in common:

| what is actually true | what docker prints | correct repair |
|---|---|---|
| the tag was never pushed under this name | `not found` | fix the name / the build |
| the tag is there, we may not see it | `not found` | log in, or make the package public |

Nothing in the pipeline could tell them apart, so the one error message was equally consistent
with "the build is broken", "the droplet has no credentials", and "the package is private". That
ambiguity, not the missing log volume, is what produced the circling.

### What was built

**`ghcr.py` — one home for the name and for the diagnosis.**

* `ref()` / `split()` assemble and parse the reference in one place. `split()` handles a repository
  of any depth, because `feranicus/colt-web` and `feranicus/electronic/colt-web` differing only by
  a path segment is exactly what made the two names look interchangeable.
* `report()` asks the registry the same question twice — anonymously and with a token — and makes
  **the difference between the two answers** the diagnosis. It also lists the tags that *do* exist,
  which on its own would have ended this run in one step. Where it has no evidence (no token, dead
  registry) it says so and concludes nothing, rather than guessing a cause (class 1).

**The actual fix.** `docker-compose.web.yml` now reads `${WEB_IMAGE:-…}:${WEB_TAG:-latest}`;
`remote_ghcr()` exports both halves and echoes the full reference before pulling; `pipeline.yml`
passes `WEB_IMAGE: ${{ env.IMAGE_OWNER }}/colt-web` — derived from the same variable the build job
pushes to, so the two cannot drift.

**Authentication, and saying when there is none.** `remote_ghcr()` now runs `docker login ghcr.io`
with the token on **stdin** (never argv) when one is present, and prints an explicit warning when
one is not — because an anonymous pull of a private package fails as "not found", and a silent
skip there is a diagnosis nobody can make (class 37). The staging job also gained
`packages: read`: without it the token is valid and still 404s, which is the same dead end by
another route.

### The guard, and the bug inside the fix

`tests/test_image_ref.py` derives both spellings out of `pipeline.yml` and fails if they differ —
it does not restate either (class 35). Twelve mutations were run; all twelve fail the suite,
including reverting the original bug.

Two of those mutations found defects in my own work:

1. **The permissions guard sliced the file at `"staging:"` and `"\n  production"`.** The second
   anchor did not match, so the slice kept the rest of the file — including the *production* job's
   `packages: read`. Removing the permission from the staging job passed. Replaced with a real
   YAML parse of `jobs["staging"]["permissions"]`. A guard reading the wrong region is measuring
   something, just not its subject (classes 1 and 4).

2. **`printf '%%s'` in a concatenated string.** Written out of habit, but that string is assembled
   with `+`, not `%`-formatted, so the doubling never collapses: the shell would have received
   `printf '%%s'` and piped the two characters `%s` to `docker login` as the password. The login
   fails, a private package then answers 404, and the deploy reports **a missing tag** — the exact
   dead end this entire change exists to remove, reintroduced by the fix for it.

   Defect class 44 already says a literal `%` must be `%%` *only in a %-formatted string*. The
   precondition is the whole rule and I dropped it. Nothing in the Python source looked wrong;
   only the generated artifact did (class 49). Two tests now read the generated script: one
   asserts the token reaches the login line, one runs `bash -n` over the whole thing.

### Still open

* 138 of 189 lines (73%) of the shared proxy config exist only on the droplet — 2 of 5 fragments
  have a committed source. `jhw__jobhuntwow.caddy` declares `jobhw.org` and reports as matching its
  committed block, while `deploy/caddy/jobhuntwow.caddy` contains no such hostname. That
  contradiction means the "matches the committed block" comparison may not measure what it claims.
  Closing this needs a careful read of the droplet: fragments can carry basicauth hashes and header
  tokens, so gitleaks and a human review come before anything is committed — never a blind `scp`
  into git.

### Postscript: the gate caught two more defects, both mine, both in the guard

The first real `python ship.py` after the change above failed on my own new test:

```
FAILED tests/test_image_ref.py::test_the_generated_script_is_valid_shell
  AssertionError: the droplet would get invalid shell:
    /bin/bash: C:UsersferanAppDataLocalTemptmpm4jo1z39.sh: No such file or directory
  assert 127 == 0
```

Two separate mistakes, both already written down as rules I had just re-read:

1. **I gated on `shutil.which("bash")`.** CLAUDE.md says, in the TWO DEVELOPERS section: *"A
   POSIX-shell test harness uses `shell_harness_allowed()` (ONE HOME, test_teamwork.py), never
   `shutil.which("bash")`: here `bash` is WSL's bash.exe."* On this operator's box `which` answers
   yes, so the harness ran under WSL — testing the emulation layer, which is the thing that rule
   exists to prevent.

2. **I handed `bash -n` a Windows path.** `tempfile.mkstemp()` returns `C:\Users\...`; WSL stripped
   the backslashes and could not open it. Defect class 22 names this exact case ("a Windows path
   passed to `bash -n`"). rc 127 is a *missing file*, and the assertion rendered it as **"the
   droplet would get invalid shell"** — the diagnostic blaming its subject for its own blindness,
   which is class 1, in the very change whose whole purpose was to stop that happening.

The repair is not a skip. The script now goes to `bash -n` on **stdin as bytes**, so there is no
path to translate and no newline for the platform to rewrite (classes 21 and 43), and the module
gate is `shell_harness_allowed()`. CI parses the script for real; Windows skips with a reason.

Coverage was checked rather than assumed: the `printf '%%s'` mutation is still caught on a machine
with no usable bash, because the test that reads the generated login line is pure Python. Only the
syntax parse is CI-only.

Worth stating plainly, because it is the argument for the whole pipeline: three of the defects in
this document were found by the operator's own gate running on his own machine, not by review and
not by me. A gate that can fail is the only thing that has reliably caught my work.

### Run #8: the gate caught a leak I wrote into the leak test

`quality-and-secrets` failed in 8 seconds:

```
Finding:     + "REDACTED\n")
RuleID:      private-key
File:        tests/test_gate_diagnostics.py
Line:        480
leaks found: 1
```

Build, scan, staging and production were **skipped**, not failed — the gate is `needs:` for all of
them. Nothing in the pipeline regressed; it stopped exactly where it is designed to stop.

The finding is `test_the_trace_can_never_carry_private_key_material`, the test asserting the ssh -v
probe never relays key material. To have something to filter, it built a payload containing a
complete BEGIN/END armour pair. gitleaks' `private-key` rule spans everything between those two
delimiters, so the fixture *is* the finding. CLAUDE.md already carried this exact lesson from
2026-10-15 ("a BEGIN/END pair inside a COMMENT, since the rule spans everything between"); I wrote
one anyway, in code rather than a comment.

The armour is now assembled at runtime (`"-" * 5 + "%s OPENSSH PRIVATE KEY" + "-" * 5`), so the
literal `-----BEGIN` never appears in source while the string handed to the probe is byte-identical
to real armour. That distinction matters: `ci_key.py`, whose job is to *match* these delimiters,
keeps them literal and is path-allowlisted for that reason. A fixture has no such need, and
allowlisting a third test file would have been the tempting, wrong fix.

Rebuilding the payload also made the next assertion vacuous — it still named the old base64 body,
which the payload no longer contained, so it could never fail again (class 3). Fixed in the same
change.

#### The actual gap

`test_this_file_is_not_itself_a_finding` has carried gitleaks' real regexes since the allowlist was
written, and it only ever read **one file: its own**. `ship.py --test` runs no gitleaks (the binary
is a CI step), so a leak in any other file was invisible on the laptop until CI said so — and by
then it costs a full pipeline run.

A rule enforced on one file is not a rule, it is an exception. `test_NO_tracked_file_trips_the_
scanner_unless_it_is_allowlisted` now sweeps every tracked file with the same two regexes, skipping
only what `.gitleaks.toml` genuinely exempts (derived from the config, never retyped). It needs no
gitleaks binary, so it runs identically on the laptop and in CI.

It is deliberately not a replacement for gitleaks — two rules against roughly 150. It is the early
warning, so a leak is reported by a local test rather than by a red pipeline.

Proven the only way that counts: re-introducing the verbatim run-#8 armour makes it fail, naming
`tests/test_gate_diagnostics.py:496  rule=private-key`; a planted PAT in `recover.py` fails as
`recover.py:695  rule=github-pat`. The first mutation I tried was invalid — it replaced the armour
with a `%s` form that never contains the literal `-----BEGIN`, so it violated no property and
"escaped" meaninglessly (class 13). The faithful mutation is the one above.
