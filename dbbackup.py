#!/usr/bin/env python3
"""dbbackup.py — install and run the database backup on the droplet.

A BUILDING BLOCK, not a second command (operating principle 7). `python ship.py` calls this after
a verified deploy. It is runnable on its own only for restore work.

WHAT IT INSTALLS (idempotent)
    /opt/dbbackup/agent.py          the committed agent, shipped from this repo
    dbbackup.service / .timer       daily at 03:17 UTC + 5 minutes after boot, persistent so a
                                    droplet that was off still runs the missed backup

WHY A TIMER AND NOT A CRON IN A CONTAINER
    The databases live in docker volumes and the agent uses the sqlite3 ONLINE BACKUP API against
    the volume's host path, so it does not need any container to be running. A container cron
    would tie the backup to the health of the thing being backed up.

ONE SSH SESSION. Win32-OpenSSH has no ControlMaster, and OpenSSH 9.8 enables PerSourcePenalties by
default, so a burst of short-lived sessions from one address is exactly what sshd damps. The whole
install + first run + verify goes over a single connection, payload on STDIN (argv has a length
limit that has already broken one payload here) in BINARY mode (Windows text mode rewrites \\n to
\\r\\n and bash then chokes on $'\\r').

    python dbbackup.py                 install, run one backup, verify a restore
    python dbbackup.py --verify        verify a restore only (no new backup)
    python dbbackup.py --list          what backups exist on the droplet
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
Description=cybergod database backup (verified SQLite online backup, off-box copy)
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/dbbackup/agent.py backup
"""

TIMER = """[Unit]
Description=cybergod database backup, daily

[Timer]
OnCalendar=*-*-* 03:17:00
OnBootSec=5min
Persistent=true

[Install]
WantedBy=timers.target
"""


def build_script(agent_b64, do_backup, do_verify, do_list):
    return """set -u
mkdir -p /opt/dbbackup
echo '%s' | base64 -d > /opt/dbbackup/agent.py
chmod 700 /opt/dbbackup/agent.py
echo '%s' | base64 -d > /etc/systemd/system/dbbackup.service
echo '%s' | base64 -d > /etc/systemd/system/dbbackup.timer

echo '#### INSTALL'
if python3 -c 'import ast,sys; ast.parse(open("/opt/dbbackup/agent.py").read())' 2>/dev/null; then
  echo '   agent installed + parses'
else
  echo '   [X] agent does NOT parse - refusing to enable the timer'; exit 1
fi
python3 -c 'import boto3' 2>/dev/null && echo '   boto3 present (off-box upload possible)' \\
  || echo '   [!] boto3 missing - installing'
python3 -c 'import boto3' 2>/dev/null || pip3 install --quiet --break-system-packages boto3 2>/dev/null \\
  || apt-get install -y -qq python3-boto3 >/dev/null 2>&1 || true
python3 -c 'import boto3' 2>/dev/null && echo '   boto3 ok' || echo '   [!] boto3 STILL missing - local-only backups'

echo '#### DATABASES'
# ASK THE CONTAINER WHERE ITS DATA LIVES. This inventory used to run
#   docker volume inspect colt_webdata
# and print "[!] volume colt_webdata not found" on EVERY run, because Compose PREFIXES volume names
# (the real one is colt-stack_colt_webdata). deploy/dbbackup/agent.py was fixed to resolve through
# the container mount table and I did not carry the fix across - so the agent found and backed up
# both databases correctly while the inventory printed a scary warning about them being missing.
# Two homes for "where does this database live", one of them fixed: the same defect as ENRICH_MODELS
# having four homes, one level down. The suffix match is the fallback for a stopped container.
for c in colt-web; do
  docker inspect -f '{{range .Mounts}}{{.Destination}}|{{.Source}}{{"\\n"}}{{end}}' "$c" 2>/dev/null
done | awk -F'|' 'NF==2 {print $2}' | sort -u > /tmp/dbmounts
for v in colt_webdata colt_events; do
  docker volume ls --format '{{.Name}}' 2>/dev/null | grep -E "(^|_)${v}$" \
    | while read -r n; do docker volume inspect -f '{{.Mountpoint}}' "$n" 2>/dev/null; done
done >> /tmp/dbmounts
FOUND=0
for mp in $(sort -u /tmp/dbmounts); do
  for f in "$mp"/colt.sqlite "$mp"/cost_ledger.sqlite; do
    if [ -f "$f" ]; then printf '   %%-46s %%10d bytes\\n' "$f" "$(stat -c%%s "$f")"; FOUND=$((FOUND+1)); fi
  done
done
# Only NOW is silence worth reporting, and only when the app that owns the data is running -
# the same discriminator the agent uses to turn "nothing to do" into "I cannot see my subject".
if [ "$FOUND" -eq 0 ]; then
  if docker ps --format '{{.Names}}' | grep -qx colt-web; then
    echo "   [X] no database found while colt-web is RUNNING - the lookup is broken, not the estate empty"
  else
    echo "   [i] no database found and colt-web is not running (fresh box?)"
  fi
fi
rm -f /tmp/dbmounts

echo '#### BACKUP'
%s

echo '#### VERIFY_RESTORE'
%s

echo '#### LIST'
%s

echo '#### TIMER'
systemctl daemon-reload
systemctl enable --now dbbackup.timer >/dev/null 2>&1
systemctl list-timers dbbackup.timer --no-pager | head -3
echo '#### END'
""" % (agent_b64,
       base64.b64encode(SERVICE.encode()).decode(),
       base64.b64encode(TIMER.encode()).decode(),
       "python3 /opt/dbbackup/agent.py backup" if do_backup else "echo '   (skipped)'",
       "python3 /opt/dbbackup/agent.py verify-restore" if do_verify else "echo '   (skipped)'",
       "python3 /opt/dbbackup/agent.py list" if do_list else "echo '   (skipped)'")


def main():
    args = sys.argv[1:]
    only_verify = "--verify" in args
    only_list = "--list" in args
    do_backup = not (only_verify or only_list)

    agent = os.path.join(HERE, "deploy", "dbbackup", "agent.py")
    if not os.path.exists(agent):
        print("[X] missing %s" % agent); return 1
    with open(agent, "rb") as fh:
        agent_b64 = base64.b64encode(fh.read()).decode()

    script = build_script(agent_b64, do_backup, do_backup or only_verify, True)

    print("=" * 78)
    print("  DATABASE BACKUP  -  %s" % HOST)
    print("  sqlite3 online backup, verified copy, off-box if configured, restore PROVED")
    print("=" * 78)
    try:
        p = subprocess.run(SSH + ["%s@%s" % (USER, HOST), "bash -s"],
                           input=script.encode("utf-8"),   # BINARY: never let Windows add \r
                           capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        print("[X] timed out talking to the droplet"); return 1
    except FileNotFoundError:
        print("[X] ssh client not found on this machine"); return 1

    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace").strip()
    for ln in out.splitlines():
        if ln.startswith("####"):
            print("\n--- %s ---" % ln[5:])
        else:
            print(ln)
    if err:
        print("\n[stderr] %s" % err[:500])
    if p.returncode != 0:
        print("\n[X] backup run FAILED (exit %d)" % p.returncode)
        return p.returncode
    if "#### END" not in out:
        print("\n[X] the remote script did not finish")
        return 1
    print("\n" + "=" * 78)
    print("  Restore (deliberate, never automatic):")
    print("    ssh %s@%s 'python3 /opt/dbbackup/agent.py list'" % (USER, HOST))
    print("    ssh %s@%s 'python3 /opt/dbbackup/agent.py restore "
          "/var/backups/cybergod-db/<file>.gz colt_events cost_ledger.sqlite'" % (USER, HOST))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
