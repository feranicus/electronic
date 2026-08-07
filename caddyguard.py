#!/usr/bin/env python3
"""
caddyguard.py — ONE COMMAND. Install the shared-proxy guardrails and restore jobhuntwow.

    python caddyguard.py                install everything, restore jhw, verify
    python caddyguard.py --check        read-only: what is installed, is the live config healthy
    python caddyguard.py --no-restore   install the guardrails, leave jobhuntwow alone

WHAT IT DOES (the fix for the 2026-08-07 outage, end to end)
------------------------------------------------------------
RCA, three sentences: a deploy at 16:15:56 UTC on 6 Aug rewrote the SHARED /opt/videodead/Caddyfile
and truncated jobhuntwow's block (directives and closing brace gone). Nothing noticed, because
Caddy reads its config only at start — the running process served from memory for 12 hours.
Patchwatch's kernel upgrade rebooted the box at 04:22:42 on 7 Aug; Caddy re-read the file, rejected
it, and every domain on the host went down together.

This installs the three properties that make that impossible, plus the two that make it visible:

  1. ISOLATION      — the monolith becomes GENERATED. Each project owns exactly one fragment under
                      /opt/caddyguard/blocks/. A project can no longer delete another's bytes
                      because it never touches them. (Fragment+assembler rather than conf.d/import:
                      the container bind-mounts a single FILE, so an import directory would need a
                      new mount, i.e. editing videodead's compose and RECREATING the shared proxy —
                      a deliberate outage of every site in order to fix an outage.)
  2. WRITE-TIME     — nothing reaches the live file until `caddy validate` accepts it, run in the
     VALIDATION      container's OWN image AND environment, plus a brace-balance and marker-pairing
                      check that would have caught this exact defect with no container at all.
  3. RUNTIME        — a systemd timer validates the LIVE file every 10 minutes and 2 minutes after
     DETECTION       boot, alerts to Telegram, and self-heals by rebuilding from the fragments.
  4. REBOOT GATE    — patchwatch now refuses to reboot while the proxy config is invalid. The
                      reboot was the detonator and it was ours.
  5. EXTERNAL EYES  — .github/workflows/uptime.yml probes all four domains from GitHub every 10
                      minutes. Monitoring that lives on the box cannot report the box being down;
                      nothing told the operator for ~6 hours.

RESTORE: jobhuntwow's block survived the repair as an EMPTY site block, because its directives were
genuinely gone from the file. They still exist in /opt/videodead/Caddyfile.bak.1786032956 — the
backup the offending deploy took of the GOOD file, seconds before it wrote the bad one. The agent
picks the newest backup whose jhw block is brace-balanced, so it can never restore rubble.

ONE SSH SESSION. Windows OpenSSH has no ControlMaster and OpenSSH 9.8 enables PerSourcePenalties,
so a burst of short sessions is what sshd refuses. Everything below is a single base64'd script.
"""
import argparse
import base64
import os
import sys

from recover import HOST, SITES, ssh_script, sections, probe

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "deploy", "caddyguard")


def _b64(path):
    return base64.b64encode(open(path, "rb").read()).decode()


def build(restore, check_only):
    agent = _b64(os.path.join(GUARD, "agent.py"))
    svc = _b64(os.path.join(GUARD, "caddyguard.service"))
    tmr = _b64(os.path.join(GUARD, "caddyguard.timer"))
    return r"""
set +e
export LC_ALL=C

echo "#### INSTALL"
mkdir -p /opt/caddyguard/blocks /opt/caddyguard/backups
echo '%s' | base64 -d > /opt/caddyguard/agent.py
chmod 755 /opt/caddyguard/agent.py
echo '%s' | base64 -d > /etc/systemd/system/caddyguard.service
echo '%s' | base64 -d > /etc/systemd/system/caddyguard.timer
python3 -c "import ast;ast.parse(open('/opt/caddyguard/agent.py').read())" \
  && echo "agent installed + parses" || { echo "AGENT DID NOT PARSE - aborting"; exit 1; }

if [ "%s" = "check" ]; then
  echo "#### STATE"
  python3 /opt/caddyguard/agent.py show
  systemctl list-timers caddyguard.timer --no-pager 2>/dev/null | head -3
  echo "#### CHECK"
  python3 /opt/caddyguard/agent.py check
  exit 0
fi

echo "#### MIGRATE"
# Split the live monolith into per-project fragments. Idempotent: re-running just re-splits
# whatever is live, which is by definition the current truth.
python3 /opt/caddyguard/agent.py migrate

echo "#### RESTORE"
if [ "%s" = "yes" ]; then
  python3 /opt/caddyguard/agent.py restore jhw:jobhuntwow
else
  echo "skipped (--no-restore)"
fi

echo "#### ASSEMBLE"
python3 /opt/caddyguard/agent.py assemble --apply

echo "#### TIMER"
systemctl daemon-reload
systemctl enable --now caddyguard.timer >/dev/null 2>&1 && echo "caddyguard.timer enabled"
systemctl list-timers caddyguard.timer --no-pager 2>/dev/null | head -3
echo "-- first run:"
systemctl start caddyguard.service
journalctl -u caddyguard.service --no-pager -n 8 -o cat 2>/dev/null

echo "#### PATCHWATCH_GATE"
# The gate lives in patchwatch.py in the repo; report whether the droplet's copy already has it so
# the operator knows to run the patchwatch provisioner if it does not.
if grep -q "reboot_blocked" /opt/patchwatch/patchwatch.py 2>/dev/null; then
  echo "reboot gate PRESENT in /opt/patchwatch/patchwatch.py"
else
  echo "reboot gate MISSING on the droplet — run: python patchwatch/provision_patchwatch.py"
  echo "(the guardrail is committed; the droplet copy is refreshed by that provisioner)"
fi

echo "#### VERIFY"
python3 /opt/caddyguard/agent.py show
echo "-- listeners:"
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(80|443)\s' || echo "NOTHING on 80/443"
echo "-- proxy:"
docker ps -a --filter name=caddy --format '{{.Names}}\t{{.Status}}'
echo "-- local probes:"
for u in https://cybergod.ai/api/me https://godeyes.ai/ https://www.jobhuntwow.com/ https://jobhuntwow.com/ https://klimaanlage-preise.de/; do
  printf '   %%-42s %%s\n' "$u" "$(curl -sk -o /dev/null -w '%%{http_code}' --max-time 12 "$u")"
done
echo "END"
""" % (agent, svc, tmr, "check" if check_only else "install", "yes" if restore else "no")


def main():
    ap = argparse.ArgumentParser(description="Install shared-proxy guardrails; restore jobhuntwow.")
    ap.add_argument("--check", action="store_true", help="read-only status, change nothing")
    ap.add_argument("--no-restore", action="store_true", help="do not restore the jhw block")
    a = ap.parse_args()

    print("=" * 78)
    print("CADDY GUARD  ·  %s" % HOST)
    print("isolation · write-time validation · runtime watchdog · reboot gate · external eyes")
    print("=" * 78)

    out, err, rc = ssh_script(build(not a.no_restore, a.check), timeout=600)
    if not out:
        print("ssh failed (rc=%s): %s" % (rc, (err or "").strip()[:400]))
        return 2

    for k in ("INSTALL", "STATE", "MIGRATE", "RESTORE", "ASSEMBLE", "TIMER",
              "PATCHWATCH_GATE", "CHECK", "VERIFY"):
        s = sections(out).get(k)
        if s:
            print("\n--- %s ---" % k)
            print("   " + s.replace("\n", "\n   "))
    if (err or "").strip():
        print("\n[stderr] " + err.strip()[:500])

    print("\n--- OUTSIDE VIEW ---")
    good = 0
    for u in SITES + ["https://jobhuntwow.com/"]:
        st, note = probe(u)
        # 401 from /api/me is the HEALTHY answer for the authenticated endpoint.
        ok = st and st < 500
        good += 1 if ok else 0
        print("   %-42s %s" % (u, ("HTTP %d" % st) if st else note))

    print("\n" + "=" * 78)
    print("%d/%d endpoints answering." % (good, len(SITES) + 1))
    print("From now on: no project writes the shared file. Each writes its own fragment via")
    print("`caddyguard write <name> <file>` and the guard assembles, validates and reloads.")
    print("=" * 78)
    return 0 if good == len(SITES) + 1 else 1


if __name__ == "__main__":
    sys.exit(main())
