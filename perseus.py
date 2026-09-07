#!/usr/bin/env python3
"""perseus.py -- ONE command to install and run the shared security brain.

    python perseus.py                 # install/refresh the hub + timer, then run one cycle
    python perseus.py --dry-run       # decide everything, change nothing, print the report
    python perseus.py --status        # what the hub currently believes, no analysis
    python perseus.py --clients       # copy the thin client into every project that needs it

ONE COMMAND, per operating principle 7. This is a BUILDING BLOCK that ship.py may call; it is
never a second command the operator has to remember.

WHAT IT INSTALLS ON THE DROPLET
  /opt/perseus/                 the hub package (ruleset, vet, hub, abuse, client)
  perseus.timer                 daily at 04:40 UTC + 3 min after boot, Persistent=true so a
                                droplet that was off still runs the missed cycle
  /var/log/colt/perseus_*.json  ruleset, blocklist, abuse ledger, on the shared colt_events
                                volume every project already mounts

WHY A TIMER AND NOT A LOOP IN A CONTAINER: the same reason patchwatch and caddyguard are timers.
A crashed loop is silent; a timer that did not fire is visible in `systemctl list-timers`, and the
next boot picks it up.

WHY 04:40: after patchwatch's 03:xx window and after the 03:17 database backup, so a cycle never
competes with a kernel upgrade or a restore on a 4 GB box.

SAFE TO RE-RUN. Installing is idempotent; a cycle that cannot reach Loki or the models reports
that and changes nothing.
"""
import argparse
import base64
import io
import re
import os
import shutil
import subprocess
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
REMOTE = "/opt/perseus"

# Where the thin client goes in each project. The client is the ONLY file duplicated, and it is
# stateless, so it cannot meaningfully drift. Everything that decides lives in the hub.
# HERE is <root>/Linkedin Scraper, so the sibling projects live one level up. The first version
# used dirname(dirname(HERE)) and resolved to the drive root, which silently wrote nothing for
# Klima: a copy that quietly does nothing is how two projects drift apart.
_PARENT = os.path.dirname(HERE)
CLIENT_TARGETS = [
    (os.path.join(HERE, "webapp", "backend", "app"), "perseus_client.py"),
    (os.path.join(HERE, "jobhuntwow-app", "backend", "app"), "perseus_client.py"),
    (os.path.join(_PARENT, "Klima", "klima-shop", "backend", "app"), "perseus_client.py"),
    # jev.best lives in a different tree; PERSEUS_JEV overrides when it is not here.
    (os.environ.get("PERSEUS_JEV", r"C:\React SW\yantar\jev-best\webapp"), "perseus_client.py"),
    # s4biz.io was MISSING from this list entirely, so it never received the client and never
    # appeared as anything but "not installed". A target that is absent from the list is a project
    # that silently never gets the control.
    (os.environ.get("PERSEUS_S4BIZ",
                    r"C:\Users\feran\Downloads\S4biz new website\webapp\backend\app"),
     "perseus_client.py"),
]

SSH = ["-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
       "-o", "ConnectTimeout=15", "-o", "BatchMode=yes",
       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]


def say(m):
    print(m, flush=True)


def ssh_script(script, timeout=420):
    """One session, payload on STDIN as BYTES.

    STDIN, not argv: a payload in argv hits the ~32 KB Windows command-line cap and surfaces as
    FileNotFoundError, which this repo once diagnosed as 'ssh is missing' on a machine where ssh
    worked. BYTES, not text: Python text mode on Windows rewrites every \\n into \\r\\n and bash
    then dies on `$'\\r': command not found`."""
    p = subprocess.run(["ssh"] + SSH + ["%s@%s" % (USER, HOST), "bash -s"],
                       input=script.encode("utf-8"), capture_output=True, timeout=timeout)
    return (p.stdout or b"").decode("utf-8", "replace"), \
           (p.stderr or b"").decode("utf-8", "replace"), p.returncode


def pack():
    """The perseus package, as a base64 tarball carried inside the remote script."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name in ("ruleset.py", "vet.py", "hub.py", "abuse.py", "client.py", "__init__.py"):
            p = os.path.join(HERE, "perseus", name)
            if os.path.exists(p):
                tf.add(p, arcname="perseus/" + name)
        for extra in ("recover.py",):
            p = os.path.join(HERE, extra)
            if os.path.exists(p):
                tf.add(p, arcname=extra)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def install_script(blob):
    return "\n".join([
        "set -e",
        "mkdir -p %s /var/log/colt" % REMOTE,
        "cd %s" % REMOTE,
        "base64 -d > /tmp/perseus.tgz <<'B64EOF'",
        blob,
        "B64EOF",
        "tar -xzf /tmp/perseus.tgz -C %s && rm -f /tmp/perseus.tgz" % REMOTE,
        "echo '#### INSTALLED'",
        "python3 -c \"import sys; sys.path.insert(0,'%s'); from perseus import ruleset, vet, hub, abuse; "
        "print('modules import cleanly')\"" % REMOTE,
        # The service runs the cycle INSIDE colt-web, where OPENAI_API_KEY, the Telegram token and
        # the Gmail credentials already live. The hub itself needs no secrets of its own, so there
        # is no new credential home -- the defect this repo has paid for repeatedly.
        "cat > /etc/systemd/system/perseus.service <<'EOF'",
        "[Unit]",
        "Description=Perseus - daily cross-project security cycle",
        "After=docker.service",
        "[Service]",
        "Type=oneshot",
        "ExecStart=/usr/bin/docker exec colt-web python3 /opt/perseus/perseus/hub.py --cycle",
        "TimeoutStartSec=900",
        "EOF",
        "cat > /etc/systemd/system/perseus.timer <<'EOF'",
        "[Unit]",
        "Description=Perseus daily cycle",
        "[Timer]",
        "OnCalendar=*-*-* 04:40:00 UTC",
        "OnBootSec=3min",
        "Persistent=true",
        "[Install]",
        "WantedBy=timers.target",
        "EOF",
        # `|| true` USED TO SWALLOW THE FAILURE HERE, and `list-timers` printed a header with no
        # row -- which is exactly what a timer that is NOT armed looks like, while the script still
        # said "Installed.". Ask systemd what the state IS, and say so.
        "systemctl daemon-reload",
        "systemctl enable --now perseus.timer 2>&1 | sed 's/^/    enable: /' || true",
        "echo '#### TIMER'",
        "EN=$(systemctl is-enabled perseus.timer 2>&1); AC=$(systemctl is-active perseus.timer 2>&1)",
        "echo \"    is-enabled=$EN  is-active=$AC\"",
        "if [ \"$EN\" = enabled ] && [ \"$AC\" = active ]; then",
        "  systemctl list-timers perseus.timer --no-pager 2>/dev/null | sed -n '2p' "
        "|| echo '    (armed, but list-timers printed nothing)'",
        "  echo '    TIMER_OK'",
        "else",
        "  echo '    TIMER_NOT_ARMED - the hub is installed but nothing will run it nightly'",
        "  systemctl status perseus.timer --no-pager -l 2>&1 | tail -12 | sed 's/^/      /'",
        "fi",
        "echo '#### STATE'",
        "ls -la /var/log/colt/perseus_*.json 2>/dev/null || echo '(no state yet - first run)'",
    ]) + "\n"


APP_FILES = ("main.py", "app.py", "server.py", "api.py")
WIRE_MARK = "perseus_client.Middleware"


def _call_end(s, i):
    """Index just past the closing paren of a call that starts at s[i:]. FastAPI is routinely
    constructed across several lines, and a matcher that demands the whole call on one line reported
    'no ASGI app found' for three real projects."""
    d, j, q = 0, s.index("(", i), None
    while j < len(s):
        c = s[j]
        if q:
            if c == "\\":
                j += 2
                continue
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return j + 1
        j += 1
    return -1


def wire_middleware(pkg_dir):
    """COPYING A FILE IS NOT INSTALLING A CONTROL.

    perseus_client.py sat in jobhuntwow and jev.best for days, imported by NOTHING, while this
    script printed "copied" and the operator waited for alerts that could never come. That is the
    rule this repository already carries -- a control that is correct and unreachable is not a
    control -- and the copy step made it look done.

    TWO THINGS THE FIRST VERSION GOT WRONG, both visible on the Fleet page as "not installed":

    1. IT EMITTED A BARE `import perseus_client` INTO A PACKAGE. `webapp/backend/app` has an
       __init__.py and every sibling is imported with `from . import store, assistant, brand`. A
       bare import raises ModuleNotFoundError there, the wrapper's `except` swallowed it, and
       cybergod ran UNGUARDED while the deploy reported success. CLAUDE.md already records exactly
       this: "app is a PACKAGE -- use `from . import telemetry`; a bare `import telemetry` fails at
       runtime and the except-swallow would hide it." So: package -> relative import.

    2. IT REQUIRED `app = FastAPI(...)` ON ONE LINE. Three real projects construct it across
       several, so it reported "no ASGI app found" for all of them. `_call_end` walks to the real
       closing paren instead.

    Idempotent on a marker, and it REFUSES with a printed instruction rather than silently doing
    nothing when there is no app to attach to -- a silent no-op here is the failure being fixed."""
    is_pkg = os.path.exists(os.path.join(pkg_dir, "__init__.py"))
    imp = "from . import perseus_client" if is_pkg else "import perseus_client"
    for fn in APP_FILES:
        p = os.path.join(pkg_dir, fn)
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding="utf-8").read()
        if WIRE_MARK in s:
            return (fn, "already wired")
        m = re.search(r"^app\s*=\s*(?:FastAPI|Starlette)\s*\(", s, re.M)
        if not m:
            continue
        end = _call_end(s, m.start())
        if end < 0:
            continue
        nl = s.find("\n", end)
        end = len(s) if nl < 0 else nl + 1
        add = ("\n# PERSEUS SIDECAR — blocks what the hub published and reports every request to the\n"
               "# shared event log, which is what makes this project visible in cybergod.ai ->\n"
               "# Admin -> Fleet and what lets the ONE alerting brain page the operator about it.\n"
               "# It holds no credentials and sends nothing itself. Wrapped because a defence that\n"
               "# stops the site it protects is worse than no defence -- but the failure is PRINTED,\n"
               "# because a swallowed import is how this ran unguarded while reporting success.\n"
               "try:\n"
               "    %s\n"
               "    app.add_middleware(perseus_client.Middleware)\n"
               "except Exception as _perseus_exc:  # never take the app down over telemetry\n"
               "    print('PERSEUS SIDECAR NOT WIRED: %%r' %% (_perseus_exc,), flush=True)\n" % imp)
        s = s[:end] + add + s[end:]
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        return (fn, "WIRED")
    return (None, "no ASGI app found - wire it by hand: app.add_middleware(perseus_client.Middleware)")


def copy_clients():
    """Copy the thin client into each project. Reports what changed and what was already current;
    a copy that silently does nothing is how two projects drift apart."""
    src = os.path.join(HERE, "perseus", "client.py")
    body = io.open(src, encoding="utf-8").read()
    n_new = n_same = 0
    for d, name in CLIENT_TARGETS:
        if not os.path.isdir(d):
            say("  [!] %s does not exist here - copy perseus/client.py there by hand" % d)
            continue
        dst = os.path.join(d, name)
        cur = io.open(dst, encoding="utf-8").read() if os.path.exists(dst) else None
        if cur == body:
            say("  same    %s" % dst)
            n_same += 1
            continue
        with io.open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        say("  updated %s" % dst)
        n_new += 1
    say("  %d updated, %d already current" % (n_new, n_same))
    # AND WIRE IT IN. A copied file that nothing imports is what left jobhuntwow and jev.best
    # silent for days while this step printed "copied".
    say("-- wiring the middleware into each project's ASGI app --")
    wired = 0
    for d, _name in CLIENT_TARGETS:
        if not os.path.isdir(d):
            continue
        fn, how = wire_middleware(d)
        if how == "WIRED":
            wired += 1
        say("  %-8s %s%s" % (how if how != "no ASGI app found - wire it by hand: "
                             "app.add_middleware(perseus_client.Middleware)" else "MANUAL",
                             d, ("  (%s)" % fn) if fn else ""))
        if fn is None:
            say("      %s" % how)
    say("  %d newly wired" % wired)
    return n_new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--clients", action="store_true")
    ap.add_argument("--no-install", action="store_true")
    # INSTALL ONLY: refresh the code + timer and run NO cycle. This is what ship.py calls.
    # A full cycle costs four model calls and ~2 minutes; putting that in every deploy would
    # bill the account for a decision the 04:40 timer is about to make anyway.
    ap.add_argument("--install-only", action="store_true")
    ap.add_argument("--days", type=int, default=2)
    a = ap.parse_args()

    say("=" * 74)
    say("  PERSEUS - one brain for six properties   target %s@%s" % (USER, HOST))
    say("=" * 74)

    if a.clients:
        say("-- thin client into each project --")
        copy_clients()
        return 0

    if a.status or a.dry_run:
        # Local decision path: no install, no changes on the droplet.
        from perseus import hub
        rep, _rs = hub.cycle(days=a.days, dry_run=True)
        say(hub.render(rep))
        return 0

    if not a.no_install:
        say("-- install / refresh the hub --")
        if not shutil.which("ssh"):
            say("[X] no ssh client on this machine"); return 1
        out, err, rc = ssh_script(install_script(pack()))
        say(out.strip() or "(no output)")
        if rc != 0:
            # A TRACEBACK'S CAUSE IS ITS LAST LINE, NEVER ITS FIRST. The previous version printed
            # `err[:400]`, which on a Python failure is "Traceback (most recent call last):" and
            # the frames -- everything except the exception. A diagnostic that does not name its
            # subject sends the next investigation down the wrong road, and this one cost a
            # deploy cycle.
            blob = ((out or "") + "\n" + (err or "")).strip()
            tail = [l for l in blob.splitlines() if l.strip()][-12:]
            say("[X] install failed rc=%s. Last %d line(s) of the remote output:" % (rc, len(tail)))
            for l in tail:
                say("    " + l)
            return 1

    if a.install_only:
        say("")
        # DO NOT CLAIM THE TIMER IS ARMED WITHOUT EVIDENCE. `out` carries the state systemd
        # reported; a "TIMER_OK" marker is the only thing that proves the nightly cycle will fire.
        if "TIMER_OK" in out:
            say("Installed and ARMED. Daily at 04:40 UTC; `python perseus.py` runs one now.")
            return 0
        say("[!] Installed, but the TIMER IS NOT ARMED - the hub will not run by itself.")
        say("    The state systemd reported is above. Nothing else was changed.")
        return 1

    say("")
    say("-- one cycle now --")
    out, err, rc = ssh_script(
        "docker exec colt-web python3 /opt/perseus/perseus/hub.py --cycle --days %d 2>&1 || "
        "echo 'CYCLE_FAILED rc='$?\n" % a.days, timeout=600)
    say(out.strip() or "(no output)")
    if "CYCLE_FAILED" in out:
        say("[!] the cycle did not complete. NOTHING was changed; that is the safe direction.")
        return 1
    say("")
    say("Timer: daily 04:40 UTC. Report goes to Telegram. `python perseus.py --status` any time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
