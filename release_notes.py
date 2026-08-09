"""release_notes.py — gather the release facts here, have the four models write them up there.

A BUILDING BLOCK. ship.py calls it after a deploy has VERIFIED and the safe-point is tagged; the
operator never runs it separately (operating principle 7). `--print` and `--dry-run` exist for
debugging only.

THE SPLIT, and why it is not arbitrary:
  · THE FACTS are computed HERE, from git and from the gate results ship.py already holds. They are
    deterministic and they are the actual release notes. The models add prose on top.
  · THE MODELS AND THE DELIVERY are on the DROPLET, because that is where OPENAI_API_KEY, the Gmail
    API credentials and BOT_TOKEN live, and where they will keep living: secrets never enter git and
    never reach the operator's PC. So this ships the facts over ONE ssh session and lets
    `app.release_notes` inside colt-web do the asking and the sending.

ONE SSH SESSION. Windows OpenSSH has no ControlMaster and OpenSSH 9.8 enables PerSourcePenalties,
so a burst of short-lived sessions is exactly what sshd refuses. The facts go over stdin, in BINARY
mode, because Python text mode on Windows rewrites every \\n into \\r\\n and bash would then choke on
a CRLF payload -- a trap this repo has already hit twice.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
SSH_OPTS = ["-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15",
            "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]


def _git(*args, cwd=HERE):
    try:
        r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def gather(tag="", message="", staging="", tests=""):
    """Everything true about this release that can be computed without asking a model."""
    commit = _git("rev-parse", "--short", "HEAD")
    # The PREVIOUS safe-point is the honest baseline for "what changed": it is the last state that
    # actually reached production and verified, not the last commit somebody happened to make.
    prev = _git("rev-parse", "--short", "last-known-good^{commit}") or ""
    rng = ("%s..HEAD" % prev) if prev and prev != commit else "HEAD~5..HEAD"
    commits = [ln for ln in _git("log", "--no-merges", "--pretty=%h %s", rng).splitlines() if ln]
    files = [ln for ln in _git("diff", "--name-status", rng).splitlines() if ln]
    return {"commit": commit, "tag": tag or commit, "message": message,
            "staging": staging, "tests": tests,
            "commits": commits, "files": files[:40], "files_total": len(files),
            "previous": prev}


def send(facts, dry_run=False, timeout=300):
    """Pipe the facts into colt-web and let the four models write and deliver the notes."""
    payload = json.dumps(facts, ensure_ascii=False).encode("utf-8")
    cmd = ["ssh"] + SSH_OPTS + ["%s@%s" % (USER, HOST),
           "docker exec -i colt-web python3 -m app.release_notes" + (" --print" if dry_run else "")]
    try:
        # BINARY stdin. text=True would rewrite newlines on Windows and hand the container a CRLF
        # JSON payload; json.load survives that, but the same mistake broke a bash payload twice
        # before, so the pattern is kept consistent everywhere.
        r = subprocess.run(cmd, input=payload, capture_output=True, timeout=timeout)
        out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
        return r.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 1, "timed out after %ss asking the models for release notes" % timeout
    except Exception as e:
        return 1, "%s: %s" % (type(e).__name__, e)


def main():
    ap = argparse.ArgumentParser(description="Four-model release notes -> email + Telegram.")
    ap.add_argument("--tag", default="")
    ap.add_argument("-m", "--message", default="")
    ap.add_argument("--staging", default="")
    ap.add_argument("--tests", default="")
    ap.add_argument("--print", dest="dry", action="store_true",
                    help="render on the droplet and print, send nothing")
    ap.add_argument("--facts-only", action="store_true", help="show what would be sent, no ssh")
    a = ap.parse_args()

    facts = gather(a.tag, a.message, a.staging, a.tests)
    if a.facts_only:
        print(json.dumps(facts, indent=2, ensure_ascii=False))
        return 0

    print("  release notes: %d commit(s), %d file(s) changed since %s"
          % (len(facts["commits"]), facts["files_total"], facts["previous"] or "the last 5 commits"))
    rc, out = send(facts, dry_run=a.dry)
    for ln in (out or "").splitlines():
        print("    " + ln)
    if rc != 0:
        print("  [!] release notes were NOT delivered. The release itself is unaffected.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
