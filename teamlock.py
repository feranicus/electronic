#!/usr/bin/env python3
"""teamlock.py - ONE deploy at a time, across every laptop and every CI runner.

THE PROBLEM THIS SOLVES. With one developer, `python ship.py` is safe because there is only one of
him. With two, two machines can pack two different commits and push them at the same droplet
minutes apart: the second `docker compose up -d --force-recreate` wins, the first developer's verify
passes against the second developer's containers, and the engine-hash check reports a stale image
nobody can explain. GitHub Actions already serialises ITSELF with a `concurrency:` group, but that
group cannot see a laptop running deploy_web_direct.py, and the two workflows used two different
group names so even CI could collide with CI.

THE LOCK IS ON THE DROPLET, not on GitHub and not on a laptop, because the droplet is the one thing
every deploy path has to touch. `mkdir` is atomic on POSIX: it either creates the directory or it
fails, with no window in between. That is the whole mechanism.

WHAT IT DELIBERATELY DOES NOT DO:
  * It is not a mutex for correctness inside one process (in-process locks do not serialise two
    processes anyway - CLAUDE.md defect class 40).
  * It never blocks and waits. A deploy that queues behind a 20-minute staging gate is a deploy the
    operator has stopped watching. It fails fast and names the holder.
  * It cannot be trusted to be released. A `finally` cannot survive SIGKILL, a laptop lid, or a
    cancelled Actions run (defect class 16), so STALENESS, not release, is what guarantees the lock
    eventually clears. Release is the fast path, not the correctness path.

    python teamlock.py --status          # who holds it, if anyone
    python teamlock.py --break           # drop a lock you are sure is dead
"""
import argparse
import base64
import getpass
import json
import os
import socket
import subprocess
import sys
import time

HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY = os.environ.get("SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))

LOCK = "/opt/colt-stack/.deploy.lock"

# A full ship (tests are local; this covers gate + web + bots + verify + caddyguard) runs ~15 min on
# a good day and ~25 when the staging gate reboots the twin. 45 minutes is comfortably past the
# worst honest run, so anything older is a dead holder, not a slow one.
STALE_S = int(os.environ.get("DEPLOY_LOCK_STALE_S", "2700"))


def who():
    """Identify the holder in a way the other developer can act on."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions/%s" % (os.environ.get("GITHUB_RUN_ID") or "?")
    try:
        return "%s@%s" % (getpass.getuser(), socket.gethostname())
    except Exception:
        return "unknown@unknown"


def _ssh(script, timeout=60):
    """Run one bash script on the droplet in ONE session. Payload in argv, never on stdin."""
    b = base64.b64encode(script.encode("utf-8")).decode("ascii")
    cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
           "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]
    if KEY and os.path.exists(KEY):
        cmd += ["-i", KEY]
    cmd += ["%s@%s" % (USER, HOST), "echo %s | base64 -d | bash -s" % b]
    r = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# -- the remote half -------------------------------------------------------------------------------
# One session does the whole decision: try to take it; if it is held, report the holder AND its age
# so the caller can tell a live deploy from a dead one; if it is stale, break and retake HERE, so
# the check and the retake cannot be interleaved by a third machine.
_ACQUIRE = r"""
set -u
D='%(lock)s'
OWNER='%(owner)s'
STALE=%(stale)d
NOW=$(date +%%s)
mkdir -p "$(dirname "$D")" 2>/dev/null || true
if mkdir "$D" 2>/dev/null; then
  printf '%%s\n' "$OWNER" > "$D/owner"; printf '%%s\n' "$NOW" > "$D/started"
  echo "RESULT=acquired"; exit 0
fi
H=$(cat "$D/owner" 2>/dev/null || echo unknown)
S=$(cat "$D/started" 2>/dev/null || echo 0)
AGE=$(( NOW - S ))
if [ "$S" -gt 0 ] && [ "$AGE" -lt "$STALE" ]; then
  echo "RESULT=held"; echo "HOLDER=$H"; echo "AGE=$AGE"; exit 0
fi
# Stale (or corrupt): break and retake in this same session.
rm -rf "$D" 2>/dev/null || true
if mkdir "$D" 2>/dev/null; then
  printf '%%s\n' "$OWNER" > "$D/owner"; printf '%%s\n' "$NOW" > "$D/started"
  echo "RESULT=acquired"; echo "BROKE=$H"; echo "BROKE_AGE=$AGE"; exit 0
fi
echo "RESULT=held"; echo "HOLDER=$H"; echo "AGE=$AGE"
"""

_RELEASE = r"""
set -u
D='%(lock)s'
H=$(cat "$D/owner" 2>/dev/null || echo unknown)
if [ "$H" = '%(owner)s' ] || [ '%(force)s' = '1' ]; then
  rm -rf "$D" 2>/dev/null || true; echo "RESULT=released"; echo "WAS=$H"
else
  echo "RESULT=not-mine"; echo "HOLDER=$H"
fi
"""

_STATUS = r"""
set -u
D='%(lock)s'
if [ -d "$D" ]; then
  echo "RESULT=held"
  echo "HOLDER=$(cat "$D/owner" 2>/dev/null || echo unknown)"
  echo "AGE=$(( $(date +%%s) - $(cat "$D/started" 2>/dev/null || echo 0) ))"
else
  echo "RESULT=free"
fi
"""


def _parse(out):
    d = {}
    for ln in (out or "").splitlines():
        if "=" in ln and not ln.startswith(" "):
            k, _, v = ln.partition("=")
            d[k.strip()] = v.strip()
    return d


def _fmt_age(s):
    try:
        s = int(s)
    except (TypeError, ValueError):
        return "unknown age"
    return "%dm%02ds" % (s // 60, s % 60) if s >= 60 else "%ds" % s


def acquire(owner=None, runner=_ssh, stale_s=None):
    """(ok, info). ok=False means somebody else is deploying RIGHT NOW; info names them.

    FAILS OPEN on an ssh/transport fault, deliberately. The lock exists to stop two humans colliding
    on a busy day, not to be a new way for a deploy to die. If the droplet cannot be reached the
    deploy that follows is going to fail anyway, with a better error than this one could give.
    """
    owner = owner or who()
    script = _ACQUIRE % {"lock": LOCK, "owner": owner,
                         "stale": int(stale_s if stale_s is not None else STALE_S)}
    try:
        rc, out = runner(script)
    except Exception as e:
        return True, {"RESULT": "unknown", "ERROR": "%s: %s" % (type(e).__name__, str(e)[:120])}
    d = _parse(out)
    if d.get("RESULT") == "held":
        return False, d
    if d.get("RESULT") != "acquired":
        return True, {"RESULT": "unknown", "ERROR": (out or "").strip()[:200] or "rc=%s" % rc}
    return True, d


def release(owner=None, runner=_ssh, force=False):
    owner = owner or who()
    try:
        rc, out = runner(_RELEASE % {"lock": LOCK, "owner": owner, "force": "1" if force else "0"})
        return _parse(out)
    except Exception as e:
        return {"RESULT": "error", "ERROR": type(e).__name__}


def status(runner=_ssh):
    try:
        rc, out = runner(_STATUS % {"lock": LOCK})
        d = _parse(out)
        if "RESULT" not in d:          # ssh answered, but not with our script's output
            d = {"RESULT": "error", "ERROR": (out or "").strip()[:200] or "rc=%s, no output" % rc}
        return d
    except Exception as e:
        return {"RESULT": "error", "ERROR": "%s: %s" % (type(e).__name__, str(e)[:160])}


class held:
    """Context manager. Prints what it did, so a blocked deploy is never a silent one.

    Usage:
        with teamlock.held("production deploy") as got:
            if not got:
                sys.exit(2)
            ...
    """

    def __init__(self, label, owner=None, runner=_ssh, dry=False):
        self.label, self.owner, self.runner, self.dry = label, owner or who(), runner, dry
        self.ok = False

    def __enter__(self):
        if self.dry:
            print("  deploy lock: DRY RUN, not taken")
            self.ok = True
            return True
        self.ok, info = acquire(self.owner, self.runner)
        if not self.ok:
            print("\n  [X] ANOTHER DEPLOY IS RUNNING — %s" % self.label)
            print("      holder : %s" % info.get("HOLDER", "unknown"))
            print("      running: %s" % _fmt_age(info.get("AGE")))
            print("      Wait for it to finish, then re-run. If you are certain it is dead:")
            print("          python teamlock.py --status      # confirm")
            print("          python teamlock.py --break       # then re-run python ship.py")
            return False
        if info.get("BROKE"):
            print("  deploy lock: broke a STALE lock from %s (%s old) and took it"
                  % (info["BROKE"], _fmt_age(info.get("BROKE_AGE"))))
        elif info.get("RESULT") == "unknown":
            print("  deploy lock: could not be checked (%s) — continuing, failing OPEN"
                  % info.get("ERROR", "?")[:80])
        else:
            print("  deploy lock: held by %s" % self.owner)
        return True

    def __exit__(self, *exc):
        if self.ok and not self.dry:
            r = release(self.owner, self.runner)
            if r.get("RESULT") == "released":
                print("  deploy lock: released")
        return False


def main():
    ap = argparse.ArgumentParser(description="the one-deploy-at-a-time lock on the droplet")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--break", dest="brk", action="store_true",
                    help="drop a lock you are SURE is dead (a crashed run, a closed laptop)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.brk:
        r = release(force=True)
        print(json.dumps(r) if a.json else
              ("broken (was held by %s)" % r.get("WAS", "?") if r.get("RESULT") == "released"
               else str(r)))
        return 0
    s = status()
    if a.json:
        print(json.dumps(s))
    elif s.get("RESULT") == "held":
        print("HELD by %s for %s" % (s.get("HOLDER", "?"), _fmt_age(s.get("AGE"))))
    elif s.get("RESULT") == "free":
        print("free")
    else:
        print("could not be read (%s)" % s.get("ERROR", "unknown"))
        print("  the lock lives on %s@%s at %s" % (USER, HOST, LOCK))
    return 0


if __name__ == "__main__":
    sys.exit(main())
