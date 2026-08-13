#!/usr/bin/env python3
"""secaudit.py — what are we actually running, and how far behind is it?

    python secaudit.py              # both droplets
    python secaudit.py --prod       # production only
    python secaudit.py --staging    # staging only
    python secaudit.py --json       # machine-readable

READ-ONLY. It installs nothing, changes nothing, restarts nothing. SSH is for diagnostics.

WHY THIS EXISTS (July/August 2026, two stories that are really one story).

1. THE 432-CVE WEEK. The Linux kernel CVE team published 432 CVEs across a Sunday and Monday
   (The Register, 22 Jul 2026). Akamai's Jan Schaumann put the useful part on oss-sec: "this
   onslaught really shows it's not feasible to attempt to prioritize individual kernel changes",
   and the only workable answer is "automated, regular, and frequent updates that pull in all
   changes within a given time window". Greg Kroah-Hartman's framing explains the volume: at the
   level the kernel runs, almost any bug that can affect a running system meets the CVE
   definition, so every stable bugfix that qualifies gets an ID.
   THE CONSEQUENCE FOR US: triaging 432 kernel CVEs is not a plan, it is a way to look busy.
   The only number that matters is CADENCE, and cadence is measurable: is the running kernel the
   newest installed kernel, is a reboot pending, how many security packages are queued, and is
   the thing that applies them actually alive. That is what this script measures.

2. THE TRIVY -> LiteLLM CHAIN. Aqua's Trivy was compromised (late Feb 2026, disclosed 1 Mar,
   second wave ~16-21 Mar with a malicious v0.69.4 and 76 of 77 trivy-action tags force-pushed).
   The malware scraped Runner.Worker process memory for every secret in the job. LiteLLM was then
   compromised *because its CI installed the poisoned Trivy automatically* — 2,500+ organisations
   and 434,000 pipelines downstream, from one unrevoked token, three tools deep.
   THE CONSEQUENCE FOR US: a scanner is a supply-chain dependency like any other. Ours is
   installed by piping a script from a moving branch into a shell, in a job that holds the
   droplet SSH key. See sec_supplychain_test.py for what now guards that.

WE WERE NOT AFFECTED BY EITHER, and the evidence is dates, not optimism:
  · this repository's first commit is 2026-07-09; the malicious Trivy window was Feb-Mar 2026,
    so no workflow of ours could ever have run against it;
  · we do not use trivy-action or setup-trivy, which were the worst-hit vectors;
  · we do not depend on LiteLLM at all — enrich.py posts to the inference endpoint with stdlib
    urllib, and the backend has seven dependencies, none of which reach it.
The IOC check (a public repo named "tpcp-docs" in the org) still belongs to the operator, because
the sandbox that wrote this has no route to GitHub, and a lookup that cannot run is not a check.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PROD = os.environ.get("DROPLET_HOST", "64.225.108.200")
STAGING = os.environ.get("STAGING_HOST", "165.245.244.174")
USER = os.environ.get("DROPLET_USER", "root")
SSH = ["-o", "ConnectTimeout=12", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]

# ONE SSH SESSION PER HOST. sshd throttles rapid repeats (MaxStartups, and PerSourcePenalties is
# on by default since OpenSSH 9.8), and the Windows client has no ControlMaster to reuse a
# connection. CLAUDE.md has paid for this lesson twice; every probe below is one script.
AUDIT = r"""
set +e
export LC_ALL=C
echo "#### HOST"
. /etc/os-release 2>/dev/null; echo "distro: $PRETTY_NAME"
echo "uptime: $(uptime -p 2>/dev/null)"
echo "#### KERNEL"
echo "running: $(uname -r)"
NEWEST=$(ls -1 /boot/vmlinuz-* 2>/dev/null | sed 's|.*vmlinuz-||' | sort -V | tail -1)
echo "newest_installed: ${NEWEST:-unknown}"
if [ -n "$NEWEST" ] && [ "$NEWEST" != "$(uname -r)" ]; then
  echo "kernel_stale: YES  (running $(uname -r), installed $NEWEST)"
else
  echo "kernel_stale: no"
fi
if [ -f /var/run/reboot-required ]; then
  echo "reboot_required: YES"
  sed 's/^/  pkg: /' /var/run/reboot-required.pkgs 2>/dev/null | head -10
else
  echo "reboot_required: no"
fi
echo "#### PENDING
"
apt-get -s upgrade 2>/dev/null > /tmp/_up
echo "total_upgradable: $(grep -c '^Inst' /tmp/_up)"
echo "security: $(grep -ci '^Inst.*securit' /tmp/_up)"
grep -i '^Inst.*securit' /tmp/_up 2>/dev/null | awk '{print "  - "$2" "$3}' | head -12
echo "#### APPLIERS"
echo "unattended-upgrades: $(systemctl is-enabled unattended-upgrades 2>/dev/null || echo absent)"
echo "patchwatch_timer: $(systemctl is-enabled patchwatch.timer 2>/dev/null || echo absent)"
systemctl list-timers patchwatch.timer --no-pager 2>/dev/null | sed -n '2p' | sed 's/^/  next: /'
echo "patchwatch_reboot_gate: $(grep -c 'reboot_blocked' /opt/patchwatch/patchwatch.py 2>/dev/null)"
echo "#### DOCKER"
echo "engine: $(docker --version 2>/dev/null | sed 's/Docker version //')"
echo "containers:"
docker ps --format '  {{.Names}}  {{.Image}}  up {{.RunningFor}}' 2>/dev/null
echo "#### BASE IMAGE AGE"
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
  IM=$(docker inspect -f '{{.Config.Image}}' "$c" 2>/dev/null)
  CR=$(docker image inspect -f '{{.Created}}' "$IM" 2>/dev/null | cut -c1-10)
  echo "  $c: image=$IM built=${CR:-unknown}"
done
echo "#### TRIVY ON HOST"
command -v trivy >/dev/null 2>&1 && trivy --version 2>/dev/null | head -1 || echo "not installed (CI only)"
echo "#### END"
"""


def run(host, timeout=180):
    """One session, script over STDIN in BINARY mode.

    Text mode on Windows rewrites every \n into \r\n and bash then dies on $'\r'. That is a
    documented scar in this repo, not a hypothetical.
    """
    cmd = ["ssh"] + SSH + ["%s@%s" % (USER, host), "bash -s"]
    try:
        p = subprocess.run(cmd, input=AUDIT.encode("utf-8"), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %ds" % timeout
    except FileNotFoundError:
        return 127, "ssh client not found on this machine"


def parse(out):
    """Pull the decidable facts out. Anything we could not read stays UNKNOWN and is never
    reported as healthy — absence of evidence is not a clean bill of health."""
    f = {"kernel_stale": None, "reboot_required": None, "security": None,
         "unattended": None, "patchwatch": None, "running": None, "distro": None}
    for ln in out.splitlines():
        s = ln.strip()
        if s.startswith("distro:"):            f["distro"] = s.split(":", 1)[1].strip()
        elif s.startswith("running:"):         f["running"] = s.split(":", 1)[1].strip()
        elif s.startswith("kernel_stale:"):    f["kernel_stale"] = s.split(":", 1)[1].strip()
        elif s.startswith("reboot_required:"): f["reboot_required"] = s.split(":", 1)[1].strip()
        elif s.startswith("security:"):        f["security"] = s.split(":", 1)[1].strip()
        elif s.startswith("unattended-upgrades:"): f["unattended"] = s.split(":", 1)[1].strip()
        elif s.startswith("patchwatch_timer:"):    f["patchwatch"] = s.split(":", 1)[1].strip()
    return f


def verdict(name, f):
    """Cadence, not a CVE count. The kernel team's own volume makes per-CVE triage meaningless;
    what decides risk is whether the newest installed kernel is the one running."""
    bad, warn = [], []
    if f["kernel_stale"] is None:
        warn.append("could not read kernel state")
    elif f["kernel_stale"].startswith("YES"):
        bad.append("running kernel is NOT the newest installed: %s" % f["kernel_stale"])
    if f["reboot_required"] == "YES":
        bad.append("a reboot is pending, so patches applied are not yet in effect")
    try:
        if f["security"] is not None and int(f["security"]) > 0:
            warn.append("%s security package(s) queued" % f["security"])
    except ValueError:
        pass
    # "not-found" is what `systemctl is-enabled` PRINTS for a unit that does not exist, and the
    # first version of this check only knew about None and "absent". So the 2026-08-13 run
    # reported STAGING as "OK, nothing queued" while printing `patchwatch_timer: not-found` two
    # lines above it: nothing applies security updates to that box unattended, and the audit said
    # it was fine. A check that cannot recognise its subject's own answer is not a check.
    # Anything that is not positively enabled counts as absent.
    if str(f["patchwatch"] or "").strip() not in ("enabled", "enabled-runtime", "static"):
        warn.append("patchwatch timer %s (nothing applies updates unattended)"
                    % (f["patchwatch"] or "unreadable"))
    return bad, warn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod", action="store_true")
    ap.add_argument("--staging", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    targets = []
    if a.prod or not (a.prod or a.staging):
        targets.append(("production", PROD))
    if a.staging or not (a.prod or a.staging):
        targets.append(("staging", STAGING))

    results, rc = {}, 0
    for name, host in targets:
        code, out = run(host)
        if code != 0 and "#### HOST" not in out:
            print("\n[%s] %s UNREACHABLE: %s" % (name, host, out.strip()[:120]))
            results[name] = {"reachable": False, "error": out.strip()[:200]}
            rc = max(rc, 1)
            continue
        f = parse(out)
        bad, warn = verdict(name, f)
        results[name] = dict(f, reachable=True, blocking=bad, warnings=warn)
        if not a.json:
            print("\n" + "=" * 78)
            print("  %s   %s" % (name.upper(), host))
            print("=" * 78)
            print(out.rstrip())
            for b in bad:
                print("  [X] %s" % b)
            for w in warn:
                print("  [!] %s" % w)
            if not bad and not warn:
                print("  OK  running the newest installed kernel, no reboot pending, "
                      "nothing queued")
        if bad:
            rc = max(rc, 2)

    if a.json:
        print(json.dumps(results, indent=2))
    else:
        print("\n" + "-" * 78)
        print("  CADENCE IS THE ANSWER, NOT TRIAGE. 432 kernel CVEs in two days cannot be")
        print("  prioritised one by one; what decides exposure is whether the newest installed")
        print("  kernel is the one actually running, and whether anything applies updates when")
        print("  nobody is looking. Both are printed above for each host.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
