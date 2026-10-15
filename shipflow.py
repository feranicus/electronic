#!/usr/bin/env python3
"""shipflow.py - the pull-request path to main, as a building block ship.py drives.

WHY THIS EXISTS, and why it is not optional any more.

GitHub's rules reference: required status checks must pass "before collaborators can make changes
to a branch targeted by your ruleset". A freshly pushed commit has NO check runs yet, so a required
check can never be satisfied by a DIRECT push - which is why every ship printed

    remote: Bypassed rule violations for refs/heads/main:
    remote: - Required status check "quality-and-secrets" is expected.

The operator is an admin and bypasses it. A collaborator cannot, so their first `python ship.py`
would run 1069 tests, deploy to staging, and then be REJECTED at the push - after the staging gate,
before the safe-point. That is not a configuration wrinkle; it is the flow being wrong for two
people.

THE SHAPE: branch -> push -> PR -> WAIT for the gate -> merge. main only ever receives commits a
green `quality-and-secrets` has already seen, for everybody, with no bypass and no admin exception.

WHAT THIS DELIBERATELY DOES NOT DO:
  * It does not deploy. Merging to main triggers pipeline.yml, which is the ONE automatic path to
    production. If this merged AND ship.py then deployed directly, that would re-create the exact
    two-paths-one-droplet defect the pipeline was built to remove.
  * It never merges on an UNKNOWN check state. Pending, missing, cancelled and errored are all "not
    green", and a probe that cannot see its subject must not answer (defect class 1).
  * It does not invent a second command. ship.py calls this; the operator still types one thing.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("REPO", "feranicus/electronic")
BASE = os.environ.get("SHIP_BASE_BRANCH", "main")
GATE = os.environ.get("SHIP_GATE_CHECK", "quality-and-secrets")

# A ship's whole round trip: the gate builds the toolchain image and runs 37 engine gates plus the
# unit suite. Measured locally at 3-6 minutes; 25 gives headroom for a cold layer cache without
# letting a wedged run hold the operator's terminal forever.
GATE_TIMEOUT_S = int(os.environ.get("SHIP_GATE_TIMEOUT_S", "1500"))
POLL_S = int(os.environ.get("SHIP_GATE_POLL_S", "15"))


# --------------------------------------------------------------------------- plumbing
def _git(*args, **kw):
    return subprocess.run(["git"] + list(args), cwd=HERE, text=True, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=kw.get("timeout", 180))


def _gh(args, timeout=120, check=False):
    """One place that shells out to gh, so the failure message is written once."""
    if not shutil.which("gh"):
        sys.exit("[X] the GitHub CLI 'gh' is not installed, and the PR flow needs it.\n"
                 "    Install:  winget install GitHub.cli    then:  gh auth login")
    r = subprocess.run(["gh"] + args, cwd=HERE, text=True, capture_output=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    if check and r.returncode != 0:
        sys.exit("[X] gh %s failed: %s" % (" ".join(args[:2]), (r.stderr or r.stdout).strip()[:300]))
    return r


def slug(message, limit=28):
    s = re.sub(r"[^a-z0-9]+", "-", (message or "").lower()).strip("-")
    return (s[:limit].rstrip("-") or "change")


def branch_name(message, who=None, now=None):
    """ship/<user>-<stamp>-<slug>. The user is in the name because with two developers the first
    question about any branch is whose it is, and the stamp keeps a re-run from colliding with the
    branch its own previous attempt left behind."""
    who = who or os.environ.get("USER") or os.environ.get("USERNAME") or "dev"
    who = re.sub(r"[^A-Za-z0-9]+", "", who).lower() or "dev"
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now if now is not None else time.time()))
    return "ship/%s-%s-%s" % (who, stamp, slug(message))


# --------------------------------------------------------------------------- the gate verdict
def check_state(sha, runner=None):
    """(state, detail) for the required check on one commit.

    states: 'pass' | 'fail' | 'pending' | 'missing' | 'unknown'

    EVERYTHING THAT IS NOT GREEN IS NOT GREEN. 'missing' is its own state rather than being folded
    into pending, because "the gate has not started" and "the gate does not exist for this repo"
    look identical from here and only one of them is worth waiting for - so the caller gets to say
    so out loud instead of hanging on a check that will never arrive.
    """
    runner = runner or (lambda a: _gh(a))
    r = runner(["api", "repos/%s/commits/%s/check-runs" % (REPO, sha),
                "-H", "Accept: application/vnd.github+json"])
    if getattr(r, "returncode", 1) != 0:
        return "unknown", (getattr(r, "stderr", "") or getattr(r, "stdout", "") or "").strip()[:200]
    try:
        runs = json.loads(r.stdout or "{}").get("check_runs") or []
    except ValueError:
        return "unknown", "the check-runs response was not JSON"
    mine = [c for c in runs if c.get("name") == GATE]
    if not mine:
        return "missing", "no check run named %r on %s yet" % (GATE, sha[:12])
    # Newest first; a re-run supersedes its predecessor.
    mine.sort(key=lambda c: c.get("started_at") or "", reverse=True)
    c = mine[0]
    if c.get("status") != "completed":
        return "pending", "%s is %s" % (GATE, c.get("status"))
    concl = c.get("conclusion")
    if concl == "success":
        return "pass", c.get("html_url") or ""
    return "fail", "%s concluded %s  %s" % (GATE, concl, c.get("html_url") or "")


def wait_for_gate(sha, timeout_s=None, poll_s=None, runner=None, sleep=time.sleep, now=time.time):
    """Block until the gate is green. (ok, detail). Never returns ok on an unknown state."""
    timeout_s = GATE_TIMEOUT_S if timeout_s is None else timeout_s
    poll_s = POLL_S if poll_s is None else poll_s
    deadline = now() + timeout_s
    last = None
    while now() < deadline:
        state, detail = check_state(sha, runner)
        if state == "pass":
            return True, detail
        if state == "fail":
            return False, detail
        if detail != last:
            print("  gate: %s (%s)" % (state, detail))
            last = detail
        sleep(poll_s)
    return False, ("timed out after %ds waiting for %s on %s - the commit is pushed and the PR is "
                   "open, so re-run to pick it up where it stopped" % (timeout_s, GATE, sha[:12]))


# --------------------------------------------------------------------------- the flow
def current_sha():
    return (_git("rev-parse", "HEAD").stdout or "").strip()


def open_pr(branch, message, base=None):
    """Create the PR, or return the one that already exists for this branch. (number, url)."""
    base = base or BASE
    ex = _gh(["pr", "list", "--head", branch, "--state", "open",
              "--json", "number,url", "--repo", REPO])
    if ex.returncode == 0 and (ex.stdout or "").strip() not in ("", "[]"):
        try:
            d = json.loads(ex.stdout)[0]
            return d["number"], d["url"]
        except (ValueError, KeyError, IndexError):
            pass
    body = ("Opened by `python ship.py`.\n\n"
            "`main` is reached only through this path, because a required status check cannot be "
            "satisfied by a direct push: a fresh commit has no check runs yet. Merging triggers "
            "`pipeline.yml`, which is the one automatic path to production.\n")
    r = _gh(["pr", "create", "--repo", REPO, "--base", base, "--head", branch,
             "--title", message, "--body", body], check=True)
    url = (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else ""
    num = _gh(["pr", "view", branch, "--repo", REPO, "--json", "number", "-q", ".number"])
    return ((num.stdout or "").strip() or "?"), url


def merge_pr(number, method="squash"):
    """Merge, and DELETE the branch. (ok, detail).

    --squash keeps main linear, which is what makes `--rollback <tag>` mean one thing. The branch
    is deleted because a ship/ branch that outlives its merge is a stale pointer two developers
    will eventually both think is current.
    """
    r = _gh(["pr", "merge", str(number), "--repo", REPO, "--%s" % method, "--delete-branch"],
            timeout=180)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    if r.returncode != 0:
        return False, out[:300]
    return True, out[:200] or "merged"


def run(message, dry=False):
    """branch -> push -> PR -> wait for the gate -> merge. (ok, info).

    RESUMABLE BY CONSTRUCTION. Every step is idempotent or already-done-is-fine: the branch is
    created from the current HEAD, the PR is reused if it exists, and the gate is re-read rather
    than remembered. A laptop that dies mid-flow is recovered by running the same command again.
    """
    info = {}
    base_before = (_git("rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()

    # RESUME, RATHER THAN BRANCH OFF A BRANCH.
    #
    # A red gate deliberately leaves the branch and the PR in place - they are the evidence. The
    # first version of this then tried to cut a NEW ship/ branch from the old one on the next run,
    # which is wrong twice over: it orphans the open PR, and the second branch carries the first
    # one's history. "Resumable by construction" was a claim with nothing asserting it, which is
    # the same defect as a check that cannot fail. Being on a ship/ branch now MEANS resume.
    cur = base_before
    resuming = cur.startswith("ship/")

    st = (_git("status", "--porcelain").stdout or "").strip()
    if not st and not resuming:
        ahead = (_git("rev-list", "--count", "origin/%s..HEAD" % BASE).stdout or "0").strip()
        if ahead in ("0", ""):
            print("  (nothing to ship: the tree is clean and %s is not ahead of origin)" % BASE)
            return True, {"noop": True}

    br = cur if resuming else branch_name(message)
    info["branch"] = br
    if dry:
        print("  DRY RUN: would %s %s, open a PR, wait for %s, then merge"
              % ("resume" if resuming else "branch", br, GATE))
        return True, info

    if resuming:
        print("  resume : %s (a previous run left it open; its PR is reused)" % br)
    else:
        print("  branch : %s" % br)
        r = _git("checkout", "-b", br)
        if r.returncode != 0:
            return False, {"error": "could not create %s: %s" % (br, (r.stderr or "").strip()[:200])}

    _git("add", "-A")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HERE).returncode != 0:
        c = _git("commit", "-m", message)
        if c.returncode != 0:
            return False, {"error": "commit failed: %s" % (c.stderr or "")[:200]}

    p = _git("push", "-u", "origin", br, timeout=300)
    if p.returncode != 0:
        return False, {"error": "push failed: %s" % (p.stderr or "")[:300]}
    sha = current_sha()
    info["sha"] = sha
    print("  pushed : %s" % sha[:12])

    num, url = open_pr(br, message)
    info["pr"], info["url"] = num, url
    print("  PR     : #%s  %s" % (num, url))

    print("  waiting for %s (this is the same gate your laptop just ran)..." % GATE)
    ok, detail = wait_for_gate(sha)
    info["gate"] = detail
    if not ok:
        # LEAVE IT OPEN. The branch and the PR are the evidence, and deleting them would destroy
        # the only artefact that says what failed.
        return False, dict(info, error="gate not green: %s" % detail)
    print("  gate   : PASS")

    ok, detail = merge_pr(num)
    info["merge"] = detail
    if not ok:
        return False, dict(info, error="merge refused: %s" % detail)
    print("  merged : #%s (branch deleted)" % num)

    # Back to the base branch, fast-forwarded, so the next command starts where GitHub is.
    _git("checkout", base_before if base_before != br else BASE)
    _git("pull", "--ff-only", "origin", BASE, timeout=300)
    return True, info


def main():
    ap = argparse.ArgumentParser(description="open a gated PR to %s and merge it when green" % BASE)
    ap.add_argument("-m", "--message", default="ship: update")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ok, info = run(a.message, dry=a.dry_run)
    if not ok:
        print("\n[X] %s" % info.get("error", "the PR flow did not complete"))
        if info.get("url"):
            print("    The PR is open and the work is safe: %s" % info["url"])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
