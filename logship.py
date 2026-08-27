#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""logship.py — install the off-box security-log archive on the droplet, in ONE ssh session.

    python logship.py            install the agent + systemd timer, run one ship, verify

A BUILDING BLOCK of ship.py, never a second command the operator runs by hand. It follows
dbbackup.py exactly: the agent is base64'd into argv, the whole install + first run + verify goes
over a SINGLE connection (sshd throttles rapid repeats), and it is idempotent.

WHAT IT INSTALLS
    /opt/logship/agent.py                 the shipper (deploy/logship/agent.py)
    logship.service / .timer              hourly + 2 min after boot, persistent

The agent ships NEW bytes of /var/log/colt/events.log to DigitalOcean Spaces under dated,
append-only keys. Credentials come from /etc/patchwatch/patchwatch.env, the same chmod-600 file
dbbackup uses; if they are absent it does nothing and says so. See deploy/logship/agent.py for why.
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
Description=cybergod off-box security-log archive (append-only to Spaces)
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/logship/agent.py ship
"""

TIMER = """[Unit]
Description=cybergod off-box security-log archive, hourly

[Timer]
OnCalendar=*-*-* *:07:00
OnBootSec=2min
Persistent=true

[Install]
WantedBy=timers.target
"""


def build_script(agent_b64, hostpath_b64):
    return """set -u
mkdir -p /opt/logship /opt/cybergod
echo '%s' | base64 -d > /opt/cybergod/hostpath.py
echo '%s' | base64 -d > /opt/logship/agent.py
chmod 700 /opt/logship/agent.py
echo '%s' | base64 -d > /etc/systemd/system/logship.service
echo '%s' | base64 -d > /etc/systemd/system/logship.timer

echo '#### INSTALL'
if python3 -c 'import ast; ast.parse(open("/opt/logship/agent.py").read())' 2>/dev/null; then
  echo '   agent installed + parses'
else
  echo '   [X] agent does NOT parse - refusing to enable the timer'; exit 1
fi
python3 -c 'import boto3' 2>/dev/null && echo '   boto3 present' \\
  || pip3 install --quiet --break-system-packages boto3 2>/dev/null \\
  || apt-get install -y -qq python3-boto3 >/dev/null 2>&1 || true
python3 -c 'import boto3' 2>/dev/null && echo '   boto3 ok' || echo '   [!] boto3 missing - shipping disabled'

echo '#### FIRST SHIP'
python3 /opt/logship/agent.py ship || echo '   ship returned non-zero'

echo '#### VERIFY'
python3 /opt/logship/agent.py verify || echo '   verify returned non-zero'

echo '#### TIMER'
systemctl daemon-reload
systemctl enable --now logship.timer >/dev/null 2>&1
systemctl list-timers logship.timer --no-pager | head -3
echo '#### END'
""" % (hostpath_b64, agent_b64,
       base64.b64encode(SERVICE.encode()).decode(),
       base64.b64encode(TIMER.encode()).decode())


def main():
    agent = os.path.join(HERE, "deploy", "logship", "agent.py")
    # ONE implementation of the container->host path resolution, shared with dbbackup. Shipping it
    # is not optional: the agent imports it with no local fallback, precisely so that a second copy
    # cannot drift away from the first the way this agent drifted away from dbbackup's fix.
    hostpath = os.path.join(HERE, "deploy", "hostpath.py")
    for p in (agent, hostpath):
        if not os.path.exists(p):
            sys.exit("[X] %s missing" % p)
    agent_b64 = base64.b64encode(open(agent, "rb").read()).decode()
    hostpath_b64 = base64.b64encode(open(hostpath, "rb").read()).decode()
    script = build_script(agent_b64, hostpath_b64)
    print("=== logship: installing the off-box security-log archive on %s ===" % HOST)
    r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), "bash -s"],
                       input=script.encode("utf-8"),          # BINARY: Windows text mode = CRLF = broken bash
                       capture_output=True, timeout=180)
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    print(out)
    if "#### END" not in out:
        print("[!] install did not reach the end marker")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
