#!/usr/bin/env python3
"""perseus.py -- ONE command to install and run the shared security brain.

    python perseus.py                 # install/refresh the hub + timer, then run one cycle
    python perseus.py --dry-run       # decide everything, change nothing, print the report
    python perseus.py --status        # what the hub currently believes, no analysis
    python perseus.py --clients       # copy the thin client into every project that needs it

ONE COMMAND, per operating principle 7. This is a BUILDING BLOCK that ship.py may call; it is
never a second command the operator has to remember.

WHAT IT INSTALLS ON THE DROPLET
  /opt/perseus/                 the hub package (ruleset, vet, hub, abuse, incident, client)
  perseus.timer                 DAILY at 04:40 UTC + 3 min after boot, Persistent=true so a
                                droplet that was off still runs the missed cycle
  perseus-weekly.timer          WEEKLY, Sunday 05:20 UTC, Persistent=true. Re-vets every live rule
                                against the routes as they are TODAY and retires anything a month
                                of traffic never matched -- neither judgement is sound on the
                                daily cycle's two-day window.
  perseus-watch.timer           EVERY 10 MINUTES. The per-incident panel: four vendors are asked
                                about ONE live burst, while it is happening. It spends nothing
                                unless an incident clears every gate in perseus/incident.py, which
                                cap it at 12 incidents / $0.30 a day.
  /var/log/colt/perseus_*.json  ruleset, blocklist, abuse ledger, weekly record, watch record and
                                incident ledger, on the shared colt_events volume every project
                                already mounts

WHY TIMERS AND NOT A LOOP IN A CONTAINER: the same reason patchwatch and caddyguard are timers.
A crashed loop is silent; a timer that did not fire is visible in `systemctl list-timers`, and the
next boot picks it up.

WHY 04:40: after patchwatch's 03:xx window and after the 03:17 database backup, so a cycle never
competes with a kernel upgrade or a restore on a 4 GB box. WHY THE WEEKLY IS 40 MINUTES LATER: the
daily cycle can run for minutes and the two must never overlap on that same 4 GB box.

EVERY UNIT IS PROVEN, NOT ASSUMED. "armed" says systemd will CALL something; the install also asks
the CONTAINER whether each job has actually produced its artifact recently, and fails otherwise.
That gap is why the nightly cycle died on ENOENT for weeks behind a green `list-timers`.

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
        for name in ("ruleset.py", "vet.py", "hub.py", "abuse.py", "client.py", "incident.py",
                     "__init__.py"):
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
        # THE HEARTBEAT DIRECTORY MUST BE WRITABLE BY A NON-ROOT CONTAINER.
        # jobhuntwow (USER jhw, uid 10001) and s4biz (uid 10001) deployed the sidecar correctly and
        # still showed "not installed", because `_beat()` calls os.makedirs() inside a ROOT-OWNED
        # 0755 directory on the shared volume: PermissionError, swallowed, no heartbeat, and the
        # Fleet page honestly reported what it could see. That is the same UID-10001-vs-root defect
        # that made jobhuntwow's telemetry silent for its whole life, hitting the beat this time.
        # Created here because THIS runs as root; 1777 is /tmp's mode -- any container may write its
        # own beat, and the sticky bit stops one project deleting another's.
        "install -d -m 1777 /var/lib/docker/volumes/colt-stack_colt_events/_data/perseus_beats "
        "2>/dev/null || true",
        "install -d -m 1777 /var/log/colt/perseus_beats 2>/dev/null || true",
        "cd %s" % REMOTE,
        "base64 -d > /tmp/perseus.tgz <<'B64EOF'",
        blob,
        "B64EOF",
        "tar -xzf /tmp/perseus.tgz -C %s && rm -f /tmp/perseus.tgz" % REMOTE,
        "echo '#### INSTALLED'",
        "python3 -c \"import sys; sys.path.insert(0,'%s'); from perseus import ruleset, vet, hub, "
        "abuse, incident; print('modules import cleanly')\"" % REMOTE,
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
        # ── THE WEEKLY UNIT ──────────────────────────────────────────────────────────────────
        # A DISTINCT UNIT ON A DISTINCT SCHEDULE, not a flag on the daily one, because the work is
        # different: re-vetting every live rule against TODAY's routes, and retiring anything a
        # month of traffic never matched. Neither judgement is sound on a two-day window.
        #
        # SUNDAY 05:20 UTC. Forty minutes AFTER the daily 04:40 so the two never overlap on a 4 GB
        # box (the daily can run for minutes), and after patchwatch's 03:xx window and the 03:17
        # database backup for the same reason 04:40 was chosen. Persistent=true, so a droplet that
        # was off on Sunday runs the missed pass when it comes back rather than skipping a week.
        "cat > /etc/systemd/system/perseus-weekly.service <<'EOF'",
        "[Unit]",
        "Description=Perseus - weekly re-vetting and retirement pass",
        "After=docker.service",
        "[Service]",
        "Type=oneshot",
        "ExecStart=/usr/bin/docker exec colt-web python3 /opt/perseus/perseus/hub.py --weekly",
        "TimeoutStartSec=1800",
        "EOF",
        "cat > /etc/systemd/system/perseus-weekly.timer <<'EOF'",
        "[Unit]",
        "Description=Perseus weekly cycle",
        "[Timer]",
        "OnCalendar=Sun *-*-* 05:20:00 UTC",
        "Persistent=true",
        "[Install]",
        "WantedBy=timers.target",
        "EOF",
        # ── THE WATCH UNIT ───────────────────────────────────────────────────────────────────
        # EVERY TEN MINUTES. This is the per-incident panel: it reads the SHARED events log inside
        # the container (no ssh, no Loki round trip), and asks the four vendors about a burst while
        # it is still happening. It spends nothing unless an incident clears every gate in
        # incident.py, and those gates cap it at 12 incidents / $0.30 a day -- the arithmetic is
        # written out above MAX_PER_DAY in perseus/incident.py.
        "cat > /etc/systemd/system/perseus-watch.service <<'EOF'",
        "[Unit]",
        "Description=Perseus - live incident watch, four-vendor consensus per incident",
        "After=docker.service",
        "[Service]",
        "Type=oneshot",
        "ExecStart=/usr/bin/docker exec colt-web python3 /opt/perseus/perseus/hub.py --watch",
        "TimeoutStartSec=600",
        "EOF",
        "cat > /etc/systemd/system/perseus-watch.timer <<'EOF'",
        "[Unit]",
        "Description=Perseus live incident watch",
        "[Timer]",
        "OnCalendar=*-*-* *:00/10:00 UTC",
        "OnBootSec=5min",
        "Persistent=false",
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
        # THE SAME QUESTION, ASKED SEPARATELY OF EACH UNIT. Written out three times rather than
        # looped, deliberately: each block NAMES the unit it measured, so a marker in the output can
        # never be read as evidence about a different timer. A diagnostic that does not name its
        # subject sends the next investigation down the wrong road.
        "systemctl enable --now perseus-weekly.timer 2>&1 | sed 's/^/    enable: /' || true",
        "echo '#### WEEKLY_TIMER'",
        "WEN=$(systemctl is-enabled perseus-weekly.timer 2>&1); "
        "WAC=$(systemctl is-active perseus-weekly.timer 2>&1)",
        "echo \"    is-enabled=$WEN  is-active=$WAC\"",
        "if [ \"$WEN\" = enabled ] && [ \"$WAC\" = active ]; then",
        "  systemctl list-timers perseus-weekly.timer --no-pager 2>/dev/null | sed -n '2p' "
        "|| echo '    (armed, but list-timers printed nothing)'",
        "  echo '    WEEKLY_TIMER_OK'",
        "else",
        "  echo '    WEEKLY_TIMER_NOT_ARMED - nothing will re-vet the rules or retire dead ones'",
        "  systemctl status perseus-weekly.timer --no-pager -l 2>&1 | tail -12 | sed 's/^/      /'",
        "fi",
        "systemctl enable --now perseus-watch.timer 2>&1 | sed 's/^/    enable: /' || true",
        "echo '#### WATCH_TIMER'",
        "SEN=$(systemctl is-enabled perseus-watch.timer 2>&1); "
        "SAC=$(systemctl is-active perseus-watch.timer 2>&1)",
        "echo \"    is-enabled=$SEN  is-active=$SAC\"",
        "if [ \"$SEN\" = enabled ] && [ \"$SAC\" = active ]; then",
        "  systemctl list-timers perseus-watch.timer --no-pager 2>/dev/null | sed -n '2p' "
        "|| echo '    (armed, but list-timers printed nothing)'",
        "  echo '    WATCH_TIMER_OK'",
        "else",
        "  echo '    WATCH_TIMER_NOT_ARMED - no incident will be reviewed while it is happening'",
        "  systemctl status perseus-watch.timer --no-pager -l 2>&1 | tail -12 | sed 's/^/      /'",
        "fi",
        # ---- DID THE BRAIN EVER ACTUALLY RUN? ------------------------------------------------
        # "TIMER_OK" says systemd will CALL something. It says nothing about whether that something
        # works, and it did not: ExecStart runs `docker exec colt-web ... /opt/perseus/...`, the
        # package was installed to /opt/perseus ON THE HOST, and colt-web mounts only /data and
        # /var/log/colt -- so every nightly run died on "No such file or directory" and printed
        # "daily cycle armed" on every ship. Every project has been reporting `enforcing cycle 0`
        # ever since, which means an EMPTY blocklist, which means the sidecars block NOTHING.
        #
        # The old line here made it worse: it listed /var/log/colt/perseus_*.json on the HOST. That
        # directory is not the volume (the volume is under /var/lib/docker/volumes/...), so it said
        # "(no state yet - first run)" every single time. A message printed on every run means the
        # thing has never once executed - this repository's own defect class 2, in its own installer.
        #
        # So: ASK THE CONTAINER, at the exact path the five thin clients read, and FAIL under set -e.
        "echo '#### BRAIN'",
        "BL=/var/log/colt/perseus_blocklist.json",
        "if ! docker exec colt-web test -f \"$BL\"; then",
        "  echo '    no blocklist yet - running ONE cycle now to bootstrap (this can take minutes)'",
        "  docker exec colt-web python3 /opt/perseus/perseus/hub.py --cycle 2>&1 "
        "| tail -25 | sed 's/^/      /' || true",
        "fi",
        # The property, read where the CLIENTS read it: a published blocklist whose cycle is >= 1.
        # hub.cycle() does rs["cycle"] = old + 1, so cycle 0 can only mean "never published".
        "docker exec colt-web python3 -c \"import json,time,os;"
        "p='/var/log/colt/perseus_blocklist.json';"
        "d=json.load(open(p));c=int(d.get('cycle') or 0);n=len(d.get('patterns') or []);"
        "age=int(time.time()-os.path.getmtime(p));"
        "print('    BLOCKLIST cycle=%d patterns=%d age=%dh' % (c,n,age//3600));"
        "raise SystemExit(0 if c>=1 and age < 48*3600 else 1)\" || {",
        "  echo '    BRAIN_DEAD: no blocklist with cycle>=1 newer than 48h at that path.';",
        "  echo '    The five sidecars are therefore enforcing an EMPTY pattern list.';",
        "  echo '    Last run:'; systemctl status perseus.service --no-pager -l 2>&1 "
        "| tail -15 | sed 's/^/      /';",
        "  exit 1;",
        "}",
        # ---- AND THE SAME QUESTION OF THE TWO NEW UNITS -------------------------------------
        # "armed" says systemd will CALL something; it says nothing about whether that something
        # works. That gap is the entire reason the nightly cycle died on ENOENT for weeks while
        # every ship printed "daily cycle armed". So each new unit gets the same treatment: ask
        # THE CONTAINER, at the path the job writes, and fail the install under set -e.
        #
        # THE BOOTSTRAP IS DELIBERATELY FREE. Both are run with --no-panel, which does the whole
        # deterministic half and asks no model, so proving the units costs nothing on every ship.
        # A proof that bills the account is a proof somebody will eventually switch off.
        "echo '#### WEEKLY'",
        "WS=/var/log/colt/perseus_weekly.json",
        "if ! docker exec colt-web test -f \"$WS\"; then",
        "  echo '    no weekly record yet - running the deterministic half now (no model is asked)'",
        "  docker exec colt-web python3 /opt/perseus/perseus/hub.py --weekly --no-panel 2>&1 "
        "| tail -20 | sed 's/^/      /' || true",
        "fi",
        "docker exec colt-web python3 -c \"import json,time,os;"
        "p='/var/log/colt/perseus_weekly.json';"
        "d=json.load(open(p));r=int(d.get('runs') or 0);"
        "age=int(time.time()-float(d.get('ts') or 0));"
        "print('    WEEKLY runs=%d age=%dh verdict=%s' % (r,age//3600,d.get('verdict')));"
        "raise SystemExit(0 if r>=1 and age < 8*86400 else 1)\" || {",
        "  echo '    WEEKLY_DEAD: no weekly pass has completed in the last 8 days.';",
        "  echo '    Nothing is re-vetting live rules against the routes as they are TODAY.';",
        "  echo '    Last run:'; systemctl status perseus-weekly.service --no-pager -l 2>&1 "
        "| tail -15 | sed 's/^/      /';",
        "  exit 1;",
        "}",
        "echo '#### WATCH'",
        "WT=/var/log/colt/perseus_watch.json",
        "if ! docker exec colt-web test -f \"$WT\"; then",
        "  echo '    no watch record yet - running one pass now (no model is asked)'",
        "  docker exec colt-web python3 /opt/perseus/perseus/hub.py --watch --no-panel 2>&1 "
        "| tail -20 | sed 's/^/      /' || true",
        "fi",
        # ONE HOUR, not one day: this unit fires every ten minutes, so an hour of silence is six
        # missed passes and is already a fault. A staleness window far wider than the schedule is a
        # check that cannot fail.
        "docker exec colt-web python3 -c \"import json,time,os;"
        "p='/var/log/colt/perseus_watch.json';"
        "d=json.load(open(p));r=int(d.get('runs') or 0);"
        "age=int(time.time()-float(d.get('ts') or 0));"
        "print('    WATCH runs=%d age=%dmin detected=%s asked=%s blind=%r'"
        " % (r,age//60,d.get('detected'),d.get('asked'),d.get('blind')));"
        "raise SystemExit(0 if r>=1 and age < 3600 else 1)\" || {",
        "  echo '    WATCH_DEAD: no incident pass has completed in the last hour, and it runs "
        "every 10 minutes.';",
        "  echo '    No live incident is being reviewed while it is happening.';",
        "  echo '    Last run:'; systemctl status perseus-watch.service --no-pager -l 2>&1 "
        "| tail -15 | sed 's/^/      /';",
        "  exit 1;",
        "}",
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
    # `__init__.py` ALONE IS THE WRONG DISCRIMINATOR (2026-09-07). jobhuntwow's backend/app has NO
    # __init__.py and is still a package: Python 3 namespace packages make `from . import x` work,
    # and serve.py imports it as `app.main`. So this emitted a bare import there, which cannot
    # resolve -- the sidecar file lives at /app/app/perseus_client.py while sys.path holds /app --
    # and the wrapper's `except` would have swallowed it, leaving the project with 5992 attacks a
    # day UNGUARDED while the deploy reported success. Reproduced in a temp tree before fixing.
    # THE EVIDENCE IS IN THE FILE, NOT THE FILESYSTEM: a module that already imports its siblings
    # relatively is a package by construction, whatever the directory contains.
    for fn in APP_FILES:
        p = os.path.join(pkg_dir, fn)
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding="utf-8").read()
        if WIRE_MARK in s:
            return (fn, "already wired")
        is_pkg = (os.path.exists(os.path.join(pkg_dir, "__init__.py"))
                  or re.search(r"^\s*from\s+\.\s*import\s|^\s*from\s+\.\w", s, re.M) is not None)
        imp = "from . import perseus_client" if is_pkg else "import perseus_client"
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


# EVERY PROJECT, AND THE COMMAND THAT PROJECT USES TO DEPLOY ITSELF. Each entry invokes that
# project's OWN orchestrator -- reimplementing a deploy is the "two homes for one job" defect this
# estate has paid for repeatedly, and their ship.py already owns their tests, their staging gate
# and their commit.
#
# CYBERGOD IS IN THIS LIST, AND IT IS LAST. It used to be excluded, with a comment claiming that
# calling it from here "would recurse". THAT WAS SIMPLY FALSE: ship.py invokes `perseus.py
# --clients` and `perseus.py --install-only`, never `--rollout`, and --install-only returns before
# the cycle. Nothing recursed; a wrong comment kept a project out of a fleet command.
#
# The cost of that mistake was two full rounds of "I still see 2 missing". The Fleet page is SERVED
# BY cybergod (colt-web), so a rollout that deploys the four siblings and not cybergod updates the
# sidecars and NOT the page that reports on them -- it can never show its own work. Twice the
# operator watched a green rollout leave two rows reading "not installed", because the badge those
# rows needed was in the repo and not in the running container.
# LAST, deliberately: the page should be rebuilt after the things it describes, not before.
ROLLOUT = [
    ("jobhuntwow.com",         os.path.join(HERE, "jobhuntwow-app"),          ["ship.py"]),
    # TWO STEPS FOR jev.best, and that is not padding. `jev.py deploy` builds jev-web (the Caddy
    # front). The wired module is `webapp/main.py`, which Dockerfile.api builds into **jev-api** --
    # so deploy alone rebuilds the one container that does NOT carry the middleware, and the Fleet
    # page kept reading "not installed" after a green run. Read the compose file, not the name.
    ("jev.best",               os.environ.get("PERSEUS_JEV_ROOT",
                                              r"C:\React SW\yantar\jev-best"), ["jev.py", "deploy"]),
    ("jev.best (api)",         os.environ.get("PERSEUS_JEV_ROOT",
                                              r"C:\React SW\yantar\jev-best"), ["jev.py", "api"]),
    ("klimaanlage-preise.de",  os.environ.get("PERSEUS_KLIMA_ROOT",
                                              os.path.join(_PARENT, "Klima", "klima-shop")),
     ["ship.py"]),
    # s4biz has a have-you-looked gate on its frontend. This rollout changes no UI there, so the gate
    # is waived with --no-preview rather than allowed to block a headless run. (This comment used to
    # say s4biz was "skipped explicitly" while the entry below deployed it -- a comment that
    # contradicts the line under it is worse than no comment, because it is read instead of the code.)
    ("s4biz.io",               os.environ.get("PERSEUS_S4BIZ_ROOT",
                                              r"C:\Users\feran\Downloads\S4biz new website"),
     ["ship.py", "--no-preview"]),
    # CYBERGOD LAST. No --no-preview here: this repo's own frontend is the one the have-you-looked
    # gate exists for, and waiving it from a fleet command is how a UI change ships unseen. If the
    # gate stops the run it prints the one line that clears it.
    ("cybergod.ai (the Fleet page itself)", HERE, ["ship.py"]),
]


def cmd_rollout():
    """Deploy the sidecar to every OTHER project, in one command.

    WHY THIS EXISTS. `--clients` copies the file and `wire_middleware` edits the source, but a
    container keeps running the image it was built from. So the Fleet page correctly read
    "not installed" for four projects while this script printed "already wired" for all five --
    the code was in the repo and not in the running process. Nothing was broken; nothing was
    deployed.

    SEQUENTIAL, NOT PARALLEL, and that is measured rather than cautious: the droplet is 3.8 GB with
    ~190 MB free and ~2.1 GB in cache, and every one of these builds a docker image on that same
    box. Four at once would thrash and can OOM a live site -- taking production down to roll out a
    defence is the worst possible trade.

    ONE FAILURE DOES NOT STOP THE REST. These are independent products; a broken build in one must
    not leave the other three unguarded. Each result is reported and the exit code reflects the set.
    """
    ok, failed, missing, needlook = [], [], [], []
    for name, root, argv in ROLLOUT:
        say("")
        say("=" * 74)
        say("  ROLLOUT  %s" % name)
        say("  %s>  python %s" % (root, " ".join(argv)))
        say("=" * 74)
        if not os.path.isdir(root):
            say("  [!] %s does not exist on this machine - skipped" % root)
            missing.append(name)
            continue
        script = os.path.join(root, argv[0])
        if not os.path.exists(script):
            say("  [!] %s not found - this project's orchestrator has moved" % script)
            missing.append(name)
            continue
        # STREAMED, NOT CAPTURED. Each of these runs for minutes; a silent subprocess is
        # indistinguishable from a hung one, which is the spinner defect one level up.
        rc = subprocess.run([sys.executable, script] + argv[1:], cwd=root).returncode
        # EXIT 2 IS NOT A FAILURE, IT IS A QUESTION. ship.py returns 2 when the frontend changed
        # and nobody has looked at it - the operator's own standing rule, deliberately not waived
        # from a fleet command. Reporting that as "FAILED rc=2" alongside four real deploys is a
        # lie about what happened and buries the ONE line that clears it. Measured 2026-09-10:
        # the rollout deployed five projects and then reported a self-imposed gate as a failure,
        # so the Fleet page kept rendering the OLD UI while the summary said 5 deployed 1 failed.
        if rc == 2:
            needlook.append(name)
            say("  -> %s: NEEDS A LOOK (the frontend changed and has not been previewed)" % name)
        else:
            (ok if rc == 0 else failed).append(name)
            say("  -> %s: %s" % (name, "OK" if rc == 0 else "FAILED rc=%d" % rc))

    say("")
    say("=" * 74)
    say("  ROLLOUT RESULT   %d deployed · %d failed · %d awaiting a look · %d not on this machine"
        % (len(ok), len(failed), len(needlook), len(missing)))
    for n in ok:
        say("    OK        %s" % n)
    for n in failed:
        say("    FAILED    %s" % n)
    for n in needlook:
        say("    NEEDS A LOOK  %s" % n)
    for n in missing:
        say("    SKIPPED   %s" % n)
    if needlook:
        # THE ONE LINE THAT CLEARS IT, at the bottom where the operator is already looking.
        say("")
        say("  Its UI changed and nobody has seen it. Look, then ship:")
        say('      cd "%s"' % HERE)
        say("      python preview.py          # then: python ship.py")
        say("  Or skip the look deliberately:  python ship.py --no-preview")

    # PROVE IT FROM THE HEARTBEAT, NOT FROM THE EXIT CODE. A deploy returning 0 says the build
    # succeeded; only a beat says the middleware is actually running inside the container.
    say("")
    say("-- heartbeats on the SHARED volume (what the Fleet page reads) --")
    out, err, rc = ssh_script(
        "ls -1 /var/lib/docker/volumes/colt-stack_colt_events/_data/perseus_beats/*.json "
        "2>/dev/null | while read f; do echo \"  $(basename $f .json)  $(date -u -r $f "
        "+%H:%M:%SZ)\"; done; echo END")
    say((out or "").replace("END", "").strip() or "  (no beats yet - allow ~60s for the first one)")
    if rc != 0 and err.strip():
        say("  [!] could not read the beats: %s" % err.strip()[-200:])
    say("  NOTE klima and s4biz write to their OWN event volumes, so their beat FILE never lands")
    say("       here and never will: mounting a sibling's volume is the `external:` coupling the")
    say("       staging gate refused, and a status page is not worth an undeployable deploy.")
    say("       They are still PROVEN, by the second channel: the sidecar prints its heartbeat to")
    say("       stdout, this box's promtail ships every container's stdout to the shared Loki, and")
    say("       the Fleet page reads it there -- those rows say `elsewhere · active`. If Loki is")
    say("       down they degrade to `unverifiable`, never to a claim. `python fleet.py` reads")
    say("       every project's own log over ssh and is the ground truth that needs neither.")
    # 2 for "a project is waiting on the operator's eyes", the same code ship.py uses, so a script
    # wrapping this can tell an UNFINISHED rollout from a BROKEN one. A real failure still wins.
    return 1 if failed else (2 if needlook else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollout", action="store_true",
                    help="deploy the sidecar to every OTHER project, via each project's own "
                         "orchestrator, one after another")
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

    if a.rollout:
        # Refresh the file and the wiring FIRST, so the deploys below carry the current sidecar.
        # copy_clients() ALSO wires the middleware -- the copy and the wiring are one step on
        # purpose, because a copied file that nothing imports is the exact state being fixed.
        say("-- thin client + middleware into each project --")
        copy_clients()
        # INSTALL FIRST, THEN DEPLOY. The rollout ENDS by reading the heartbeat directory, and the
        # installer is what CREATES it 1777 so a container running as uid 10001 can write its own
        # beat. Skipping the install meant the rollout verified itself against a directory that did
        # not exist yet and reported every project as not beating -- a check measuring the absence
        # of its own precondition. One ssh, idempotent, and it must run BEFORE the deploys so the
        # containers find the directory when they start.
        if not a.no_install and shutil.which("ssh"):
            say("-- hub + heartbeat directory (must exist before the projects start) --")
            out, err, rc = ssh_script(install_script(pack()))
            say((out or "").strip()[-800:] or "(no output)")
            if rc != 0:
                say("[!] hub install rc=%s -- continuing; the deploys do not depend on it"
                    % rc + ("\n    " + (err or "").strip().splitlines()[-1][:160] if err else ""))
        return cmd_rollout()

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
        # DO NOT CLAIM A TIMER IS ARMED WITHOUT EVIDENCE. `out` carries the state systemd
        # reported; each marker is the only thing that proves its own unit will fire.
        #
        # ALL THREE, NAMED SEPARATELY. Reporting "armed" because ONE of them answered is how a
        # partially-installed SOC reads as a healthy one -- and the missing unit is always the one
        # nobody was watching. `WEEKLY_TIMER_OK` deliberately contains `TIMER_OK` as a substring,
        # so the DAILY test is anchored on its own line marker below rather than on `in out`.
        missing = [n for n, mark in (("daily 04:40 UTC", "\n    TIMER_OK"),
                                     ("weekly Sun 05:20 UTC", "WEEKLY_TIMER_OK"),
                                     ("watch every 10 min", "WATCH_TIMER_OK"))
                   if mark not in out]
        if missing:
            say("[!] Installed, but NOT ARMED: %s" % ", ".join(missing))
            say("    The state systemd reported is above. Nothing else was changed.")
            return 1
        say("Installed and ARMED: daily 04:40 UTC, weekly Sun 05:20 UTC, watch every 10 min.")
        say("`python perseus.py` runs one daily cycle now.")
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
