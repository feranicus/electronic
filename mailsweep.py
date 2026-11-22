#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mailsweep.py — install the pipeline's mail sweep on the droplet, in ONE ssh session.

    python mailsweep.py          install the systemd timer, run one sweep, show the schedule

A BUILDING BLOCK of ship.py, never a second command the operator runs by hand (operating
principle 7). It follows logship.py and dbbackup.py exactly: the whole install + first run +
verify goes over a SINGLE connection (sshd throttles rapid repeats, class 43), and it is
idempotent.

WHY A TIMER AND NOT A BUTTON. The board has a "Read mail now" button, and a button is a feature
somebody has to remember. The point of filing mail against deals is that the board is RIGHT when
you open it, not that it becomes right if you press something first. A feature nobody has seen
working is off (class 53), so this also makes the sweep observable: every run writes
`evt=pipeline_sweep` through the app's own log, which is what the fleet page and Loki read.

WHAT IT INSTALLS
    mailsweep.service / .timer            every 15 minutes, 5 min after boot, persistent

THE WORK HAPPENS INSIDE colt-web, by `docker exec`, because the sweep needs the app's modules, its
database and its env - the credentials are in the container's environment and nowhere on the host.
`docker exec <ct> <path>` resolves INSIDE the container (class 55), and `python3 -m app.pipeline`
is in the image because the image is what carries the app.

IT IS SAFE WHEN THE FEATURE IS OFF. With PIPELINE_MAIL_READ unset the module prints what is
missing and exits 0, so installing the timer before the Workspace scope is granted costs nothing
and the schedule is already there on the day it is.
"""
import base64
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
SSH = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
       "-o", "ConnectTimeout=15", "-o", "BatchMode=yes",
       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]

SERVICE = """[Unit]
Description=cybergod pipeline - read the Workspace mailboxes and file mail against deals
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
# A HARD CEILING (class 42). The sweep is bounded by its own query window, but a hung HTTPS call
# to Gmail must not leave a systemd job running until the next one starts.
TimeoutStartSec=300
ExecStart=/usr/bin/docker exec colt-web python3 -m app.pipeline sweep
"""

TIMER = """[Unit]
Description=cybergod pipeline mail sweep, every 15 minutes

[Timer]
OnCalendar=*:0/15
OnBootSec=5min
# A missed window is caught up on the next boot: a droplet that was down for an hour should not
# silently skip the mail that arrived while it was.
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
"""


def build_script():
    return """set -u
echo '%s' | base64 -d > /etc/systemd/system/mailsweep.service
echo '%s' | base64 -d > /etc/systemd/system/mailsweep.timer

echo '#### PRECONDITION'
# A TIMER POINTED AT A CONTAINER THAT IS NOT THERE fires every 15 minutes and fails every time,
# which trains the operator to ignore systemd. Check first and say so.
if docker ps --format '{{.Names}}' | grep -qx colt-web; then
  echo '   colt-web is running'
else
  echo '   [X] colt-web is not running - refusing to enable a timer that cannot work'; exit 1
fi

echo '#### FIRST SWEEP'
docker exec colt-web python3 -m app.pipeline sweep || echo '   sweep returned non-zero'

echo '#### TIMER'
systemctl daemon-reload
systemctl enable --now mailsweep.timer >/dev/null 2>&1
systemctl list-timers mailsweep.timer --no-pager | head -3
echo '#### END'
""" % (base64.b64encode(SERVICE.encode()).decode(),
       base64.b64encode(TIMER.encode()).decode())


def main():
    script = build_script()
    print("  === mailsweep: installing the pipeline mail sweep on %s ===" % HOST)
    # PAYLOAD IN ARGV, never on stdin: `bash -s` reads its SCRIPT from stdin, so the two are
    # mutually exclusive and this pattern keeps stdin free.
    r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), "bash -lc %s"
                              % _q(script)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=420)
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.splitlines():
        print("  " + line)
    if r.returncode != 0:
        print("  [!] mailsweep install returned %s - the board still works, the sweep is manual"
              % r.returncode)
    return r.returncode


def _q(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    sys.exit(main())
