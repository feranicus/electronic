# Joining this project

You are being added as a collaborator on `feranicus/electronic`, the platform behind cybergod.ai.
This page is everything you need for your first day and most days after that.

Read `README.md` first for what the system is. This page is only about how you work on it.

---

## What you get, and what you will never be given

You get write access to the repository. That is the whole list.

You will not be given the production SSH key, the droplet environment files, the shared bot
password, the Shodan key, the DigitalOcean model key, or the Spaces credentials. This is not about
trust. Those secrets exist in exactly two places, encrypted GitHub Actions secrets and the
droplets' own `chmod 600` env files, and every additional copy is another place one can leak from.
The repository is public, so that discipline is load bearing.

You do not need any of them, because you never deploy from your machine. CI deploys. Your job
finishes when a pull request goes green and merges, and the merge is what triggers the deploy.

If you ever find yourself needing a production credential to get work done, that is a design
problem worth raising rather than a credential worth copying.

---

## Day one

### 1. Accept the invitation

You will get a GitHub invitation by email. Accept it. You will have the **write** role, which lets
you push branches and open pull requests, and does not let you change repository settings, secrets,
branch protection or collaborators.

### 2. Install the toolchain

| tool | version | why |
|---|---|---|
| Python | 3.12 | CI pins 3.12; a different minor version can pass locally and fail there |
| Node.js | 20 | eight frontend gates run under it |
| Git | any current | |
| GitHub CLI (`gh`) | any current | the pull request flow drives it |

On Windows:

```
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
winget install Git.Git
winget install GitHub.cli
```

### 3. Authenticate the CLI

```
gh auth login
```

Choose GitHub.com, HTTPS, and authenticate in the browser. This is the only credential you set up,
and it is yours, tied to your own account.

### 4. Clone and check your setup

```
git clone https://github.com/feranicus/electronic.git
cd electronic
python ship.py --test
```

That last command runs the full gate battery with no network access to anything that matters and
no secrets. It takes a few minutes. Missing Python packages are installed for you. If it ends with
`ALL TESTS PASSED`, your machine is correctly set up.

### 5. Make the pull request flow your default

```
setx SHIP_FLOW pr
```

Open a new terminal afterwards so it takes effect. From then on `python ship.py` behaves as
`python ship.py --pr`, which is the path you should always use.

---

## The one command

```
python ship.py
```

That is the entire interface. There is no second script to remember. With `SHIP_FLOW=pr` set it
will:

1. Run every gate. Nothing proceeds if anything fails.
2. Create a `ship/...` branch and commit your work to it.
3. Push the branch and open a pull request.
4. Wait for the `quality-and-secrets` check on the pull request head.
5. Squash-merge it when that check is green.
6. Stop there.

Step 6 matters. The merge is a push to `main`, and a push to `main` starts the deploy pipeline. If
your laptop also deployed, one commit would deploy twice. In pull request mode your machine
deploys nothing at all, and the code only reaches a droplet through CI.

Use a message when the change deserves one:

```
python ship.py -m "fix the co-tenant guard on shared /24s"
```

### Useful narrower forms

| command | when |
|---|---|
| `python ship.py --test` | you want the gates without committing anything |
| `python ship.py --dry-run` | you want to see what would happen, touching nothing |

Everything else in the flag table in `README.md` belongs to the maintainer, not to you. In
particular `--direct`, `--no-stage`, `--no-test` and `--rollback` all skip protections that exist
because something went wrong once.

---

## When the gate fails

It will, and that is the gate doing its job. What happens:

- Your branch and your pull request stay exactly where they are. That is deliberate. They are the
  evidence.
- You fix the problem and run `python ship.py` again. Standing on a `ship/...` branch means
  **resume**: the same branch, the same pull request, no second branch cut from the first.
- Nothing merges while the check is unknown. Pending, cancelled, timed out and `skipped` are all
  treated as not green. A gate that did not run is not a gate that passed.

To read why it failed:

```
gh run list --repo feranicus/electronic --limit 5
gh run view <run-id> --log-failed
```

The Actions tab in the browser shows the same thing. Each failing gate writes a summary table on
the job page, and the staging gate also uploads its complete log as an artifact, because GitHub
truncates the middle of a long step and the middle is usually where the evidence is.

---

## How to write a change that passes

The gates encode about a hundred incidents. A few will catch you early, so they are worth knowing
before they do.

**Wire new capability into `ship.py`.** If you add a check, a migration or a provisioning step, it
goes into the orchestrator in the same change. A script someone has to remember to run separately
is treated as a bug here.

**A value has one home.** If a constant exists in code, configuration must not restate it. Values
with two homes drift, and the newer one always loses.

**Prove a new check can fail.** Break the thing it guards and watch it go red. A check whose
denominator comes from the thing it measures is not measuring anything.

**Keep tests off the network and off SSH.** `do_tests()` makes zero SSH calls and an AST test
asserts that, which is what makes the gate safe to run on a pull request with no secrets.

**Line endings and paths are platform business.** CI runs Linux, the maintainer runs Windows. A
Windows path handed to `bash` fails, and text-mode writes silently rewrite newlines. Fixtures that
get hashed, diffed or parsed are written as bytes.

**Never commit a credential or anything shaped like one.** gitleaks runs on every push and pull
request, and a leak fails the gate before the build. If you need secret-shaped text in a test,
assemble it at runtime rather than writing the literal.

`CLAUDE.md` in the repository root has the full list with the reason behind each one. It is long
because each line was paid for.

---

## Things not to do

- Do not push directly to `main`, and do not ask for the protection to be lifted for you. The
  required check cannot be satisfied by a direct push, which is the entire point.
- Do not deploy from your machine.
- Do not add a path to `.gitleaks.toml` to make a scan finding go away. Fix the content. The
  allowlist is capped at four entries and has its own guard.
- Do not run anything against a customer's infrastructure. The engine sends no packets to the
  company being assessed, and that claim is published in the terms of use, the Article 13 notice
  and the signed partner pack.
- Do not scan back, connect back, or build tooling for it, no matter what an attacker did first.
  German, EU, US and Canadian law all cover this, including mere possession of such tooling.
- Do not commit anything to `marketing/` expecting the `.pptx` to be stored. Deck files are
  gitignored on purpose; the builder script is the source of truth.

---

## If you need an account on the platform itself

Accounts are created by an administrator through `POST /api/admin/users`. The generated password is
shown once at creation and is never stored in readable form or emailed, since the one-time code
flow already uses that mailbox. Ask Evgeny; do not create one for yourself even if you can see the
route.

---

## Where things are written down

| file | what it holds |
|---|---|
| `README.md` | what the system is, how it ships, what runs on a schedule |
| `CLAUDE.md` | operating principles, settled facts, the recurring defect classes |
| `docs/decisions/` | the narrative behind every rule: what broke, what was measured |
| `.github/workflows/` | the nine workflows, which are the real specification of CI |

When a rule in `CLAUDE.md` matters and you want the story, search `docs/decisions/` for a phrase
from the rule. Every rule there was earned by an incident recorded here.

---

## Quick reference

```
python ship.py --test        gates only, nothing committed
python ship.py               branch, PR, wait for the gate, merge  (SHIP_FLOW=pr)
python ship.py -m "msg"      the same, with a commit message
gh run list --limit 5        recent CI runs
gh run view <id> --log-failed    why one failed
python recover.py            read-only outage triage, if asked to look
```
