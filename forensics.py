#!/usr/bin/env python3
"""
forensics.py — ONE COMMAND. Read-only night-timeline collector for the droplet.

    python forensics.py                        default window: the outage night (UTC)
    python forensics.py --since "2026-08-06 16:00" --until "2026-08-07 08:00"
    python forensics.py --save                 also write a timestamped .txt bundle

WHY THIS EXISTS (2026-08-07)
----------------------------
videodead-caddy crash-looped on a Caddyfile whose `jobhuntwow.com {` block had lost BOTH its
directives and its closing brace, ending mid-sentence inside a comment. That is not a config
someone wrote — it is a write that was CUT OFF, or a range-delete that removed too much.

The operator's timeline is the load-bearing fact: the stack was healthy through an assessment that
finished 18:06 UTC, and every site was refused by 06:00 UTC. Something acted in between. Naming the
crash is not the RCA; naming the WRITER is.

  Restoring first would destroy the evidence, so this script CHANGES NOTHING.
  It only reads. It does not start, stop, restart, edit or delete anything.

WHAT IT ANSWERS, in order of how likely each is to be the writer:
  1. Which processes wrote to disk in the window     (mtimes across /etc /opt /root /srv)
  2. Did an automated job run                        (systemd timers, cron, patchwatch, apt)
  3. Did a human connect                             (auth.log, root history with timestamps)
  4. Did the box run out of something                (disk, inodes, memory, OOM killer)
  5. What did Docker do, and when                    (per-container StartedAt/FinishedAt/RestartCount)
  6. What did the proxy say as it died               (its own logs, oldest first)
  7. Was the box under attack                        (colt-web telemetry + alerts for the window)
  8. Where does the Caddyfile actually come from     (mount source, siblings, backups, git)

EVERYTHING RUNS IN ONE SSH SESSION. Windows OpenSSH has no ControlMaster and OpenSSH 9.8 enables
PerSourcePenalties by default, so a burst of short sessions from one address is precisely what sshd
refuses. One session, one handshake. (Same rule as ship.py and recover.py.)
"""
import argparse
import datetime
import os
import sys

from recover import HOST, ssh_script, sections   # one implementation of the ssh plumbing

# The operator is in Batumi (UTC+4). Last good assessment 21:40-22:06 local = 17:40-18:06 UTC;
# the outage was found at 10:00 local = 06:00 UTC. Default window brackets that generously.
DEF_SINCE = "2026-08-06 16:00"
DEF_UNTIL = "2026-08-07 08:00"


def build(since, until):
    return r"""
set +e
export LC_ALL=C
SINCE="%s"; UNTIL="%s"

echo "#### CLOCK"
echo "now_utc:  $(date -u '+%%F %%T')"
echo "tz:       $(cat /etc/timezone 2>/dev/null) / $(date '+%%Z %%z')"
echo "window:   $SINCE .. $UNTIL (host local time as journald sees it)"
echo "uptime:   $(uptime -p)  (booted $(uptime -s))"

echo "#### WROTE_IN_WINDOW"
# THE SINGLE MOST USEFUL QUESTION: what on disk was modified during the window? A truncated
# Caddyfile has an mtime, and whatever wrote it usually touched its own state/log at the same
# second. Sorted by time so the sequence is visible, not just the set.
for D in /etc /opt /root /srv /usr/local; do
  find "$D" -xdev -newermt "$SINCE" ! -newermt "$UNTIL" \
       -not -path '*/.git/*' -not -path '*/node_modules/*' \
       -printf '%%TY-%%Tm-%%Td %%TH:%%TM:%%TS %%10s %%p\n' 2>/dev/null
done | sort | cut -c1-160 | head -120
echo "-- total files touched:"
for D in /etc /opt /root /srv /usr/local; do
  find "$D" -xdev -newermt "$SINCE" ! -newermt "$UNTIL" -not -path '*/.git/*' \
       -not -path '*/node_modules/*' 2>/dev/null
done | wc -l

echo "#### CADDYFILE_PROVENANCE"
C=$(docker ps -a --format '{{.Names}}' | grep -i caddy | head -1)
echo "container: $C"
echo "-- mounts (where the file really lives on the host):"
docker inspect "$C" --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} rw={{.RW}}
{{end}}' 2>/dev/null
echo "-- image: $(docker inspect -f '{{.Config.Image}}' "$C" 2>/dev/null)"
SRC=$(docker inspect "$C" --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
[ -z "$SRC" ] && SRC=$(docker inspect "$C" --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
echo "-- host source: ${SRC:-<none: file lives INSIDE the container>}"
if [ -n "$SRC" ]; then
  ls -la --time-style=full-iso "$SRC" 2>/dev/null | head -20
  D=$SRC; [ -f "$SRC" ] && D=$(dirname "$SRC")
  echo "-- siblings / backups in $D:"
  ls -la --time-style=full-iso "$D" 2>/dev/null | head -30
  echo "-- git?"
  (cd "$D" && git log --oneline -8 2>/dev/null && git status --porcelain 2>/dev/null | head)
fi
echo "-- any Caddyfile anywhere on the host, with mtimes:"
find / -xdev -name 'Caddyfile*' -printf '%%TY-%%Tm-%%Td %%TH:%%TM:%%TS %%10s %%p\n' 2>/dev/null | sort | head -25

echo "#### TIMERS_AND_CRON"
systemctl list-timers --all --no-pager 2>/dev/null | head -25
echo "-- units that RAN in the window:"
journalctl --since "$SINCE" --until "$UNTIL" --no-pager -o short-iso 2>/dev/null \
  | grep -Ei 'Starting |Started |Stopping |Stopped |Reloading ' | head -60
echo "-- cron:"
crontab -l 2>/dev/null | grep -v '^#' | head -20
ls -la /etc/cron.d /etc/cron.daily 2>/dev/null | head -30
echo "-- at jobs:"; atq 2>/dev/null | head

echo "#### PATCHWATCH"
journalctl -u 'patchwatch*' --since "$SINCE" --until "$UNTIL" --no-pager -o short-iso 2>/dev/null | tail -60
ls -la /opt/patchwatch /var/log/patchwatch 2>/dev/null | head -20
find / -xdev -path '*patchwatch*' -newermt "$SINCE" ! -newermt "$UNTIL" \
     -printf '%%TY-%%Tm-%%Td %%TH:%%TM:%%TS %%p\n' 2>/dev/null | sort | head -20

echo "#### APT_AND_UPGRADES"
awk -v s="$SINCE" '/^Start-Date/{p=($2" "$3)>=s} p' /var/log/apt/history.log 2>/dev/null | tail -40
echo "-- unattended-upgrades:"
tail -40 /var/log/unattended-upgrades/unattended-upgrades.log 2>/dev/null
echo "-- reboot required: $([ -f /var/run/reboot-required ] && cat /var/run/reboot-required || echo no)"

echo "#### WHO_CONNECTED"
last -F -n 25 2>/dev/null | head -25
echo "-- sshd in window:"
journalctl -u ssh -u sshd --since "$SINCE" --until "$UNTIL" --no-pager -o short-iso 2>/dev/null \
  | grep -Ei 'accepted|failed|invalid|disconnect|refused|penalt' | head -50
echo "-- auth.log:"
grep -Ei 'accepted|sudo:|session opened' /var/log/auth.log 2>/dev/null | tail -30
echo "-- root shell history (timestamps only meaningful if HISTTIMEFORMAT was set):"
ls -la --time-style=full-iso /root/.bash_history 2>/dev/null
tail -40 /root/.bash_history 2>/dev/null

echo "#### RESOURCES"
df -h / /var 2>/dev/null; echo "-- inodes:"; df -i / /var 2>/dev/null
free -m
echo "-- docker disk:"; docker system df 2>/dev/null
echo "-- OOM / ENOSPC / IO errors in window:"
journalctl --since "$SINCE" --until "$UNTIL" --no-pager -o short-iso -p warning 2>/dev/null \
  | grep -Ei 'out of memory|oom|killed process|no space|read-only file system|i/o error|ext4|corrupt' | head -40
dmesg -T 2>/dev/null | grep -Ei 'oom|killed process|no space|i/o error' | tail -20

echo "#### DOCKER_TIMELINE"
echo "NAME|STATE|RESTARTS|STARTED|FINISHED|EXIT|OOMKILLED"
for n in $(docker ps -a --format '{{.Names}}'); do
  docker inspect "$n" --format '{{.Name}}|{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}|{{.State.FinishedAt}}|{{.State.ExitCode}}|{{.State.OOMKilled}}' 2>/dev/null
done | sed 's#^/##' | sort -t'|' -k4
echo "-- dockerd in window:"
journalctl -u docker --since "$SINCE" --until "$UNTIL" --no-pager -o short-iso 2>/dev/null | tail -50

echo "#### PROXY_LOGS_OLDEST_FIRST"
# The FIRST failure is the informative one. --tail shows the millionth repeat of the crash loop.
docker logs "$C" --since "$SINCE" --until "$UNTIL" 2>&1 | head -60
echo "-- ... and the current loop:"
docker logs "$C" --tail 12 2>&1

echo "#### OTHER_CONTAINER_LOGS"
for n in $(docker ps -a --format '{{.Names}}'); do
  case "$n" in *caddy*) continue;; esac
  L=$(docker logs "$n" --since "$SINCE" --until "$UNTIL" 2>&1 | grep -Ei 'error|fatal|panic|denied|refus|caddy|reload' | head -6)
  [ -n "$L" ] && { echo "== $n"; echo "$L"; }
done

echo "#### TRAFFIC_AND_ALERTS"
# Was the box being hammered? colt-web writes structured events to the shared colt_events volume.
EV=$(docker volume inspect colt_events -f '{{.Mountpoint}}' 2>/dev/null)/events.log
echo "events log: $EV  ($(ls -la --time-style=full-iso "$EV" 2>/dev/null | awk '{print $6,$7,$5}'))"
if [ -f "$EV" ]; then
  echo "-- security_alert lines in window:"
  grep '"security_alert"' "$EV" 2>/dev/null | tail -25 | cut -c1-220
  echo "-- request volume per hour (evt=http):"
  grep '"evt": *"http"' "$EV" 2>/dev/null | grep -o '"ts": *"[^"]*' | cut -c8-21 | sort | uniq -c | tail -30
  echo "-- top client IPs:"
  grep '"evt": *"http"' "$EV" 2>/dev/null | grep -o '"ip": *"[^"]*' | cut -d'"' -f4 | sort | uniq -c | sort -rn | head -15
  echo "-- last engine events:"
  grep -E '"(assess_done|assess_error|assess_refused)"' "$EV" 2>/dev/null | tail -8 | cut -c1-220
fi

echo "#### FIREWALL_AND_LISTENERS"
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(80|443|22)\s' || echo "NOTHING on 80/443"
ufw status 2>/dev/null | head -12
iptables -S 2>/dev/null | head -20
echo "END"
""" % (since, until)


def main():
    ap = argparse.ArgumentParser(description="Read-only forensic timeline for the droplet outage.")
    ap.add_argument("--since", default=DEF_SINCE)
    ap.add_argument("--until", default=DEF_UNTIL)
    ap.add_argument("--save", action="store_true", help="write the raw bundle to a .txt file")
    a = ap.parse_args()

    print("=" * 78)
    print("FORENSICS  %s   window %s .. %s UTC" % (HOST, a.since, a.until))
    print("READ-ONLY: this script starts, stops, edits and deletes nothing.")
    print("=" * 78)

    out, err, rc = ssh_script(build(a.since, a.until), timeout=420)
    out = out or ""
    if rc != 0 and not out:
        print("ssh failed (rc=%s): %s" % (rc, (err or "").strip()[:400]))
        return 2

    sec = sections(out)
    order = ["CLOCK", "WROTE_IN_WINDOW", "CADDYFILE_PROVENANCE", "TIMERS_AND_CRON", "PATCHWATCH",
             "APT_AND_UPGRADES", "WHO_CONNECTED", "RESOURCES", "DOCKER_TIMELINE",
             "PROXY_LOGS_OLDEST_FIRST", "OTHER_CONTAINER_LOGS", "TRAFFIC_AND_ALERTS",
             "FIREWALL_AND_LISTENERS"]
    for k in order:
        if k in sec:
            print("\n" + "-" * 78)
            print("## %s" % k)
            print("-" * 78)
            print(sec[k] or "(empty)")

    if (err or "").strip():
        print("\n[stderr] " + err.strip()[:600])

    if a.save:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "forensics-%s.txt" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S"))
        open(p, "w", encoding="utf-8", errors="replace").write(out)
        print("\nraw bundle saved: %s" % p)

    print("\n" + "=" * 78)
    print("READ THIS FIRST: '## WROTE_IN_WINDOW'. The process that truncated the Caddyfile almost")
    print("always touched its own state or log in the same second. Match the Caddyfile's mtime")
    print("against that list before believing any theory, including mine.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
