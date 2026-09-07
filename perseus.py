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
        "systemctl daemon-reload && systemctl enable --now perseus.timer >/dev/null 2>&1 || true",
        "echo '#### TIMER'",
        "systemctl list-timers perseus.timer --no-pager 2>/dev/null | head -3 || echo '(no timer)'",
        "echo '#### STATE'",
        "ls -la /var/log/colt/perseus_*.json 2>/dev/null || echo '(no state yet - first run)'",
    ]) + "\n"


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
            say("[X] install failed rc=%s: %s" % (rc, err.strip()[:400]))
            return 1

    if a.install_only:
        say("")
        say("Installed. The timer runs the cycle daily at 04:40 UTC; `python perseus.py` runs one now.")
        return 0

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
