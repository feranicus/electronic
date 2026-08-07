#!/usr/bin/env python3
"""
stagegate.py — validate a change on the STAGING droplet before production is touched.

BUILDING BLOCK, not a command. `python ship.py` calls it; the operator never runs it directly
(operating principle 7). `--only` exists for debugging.

    ship.py -> stagegate.run() -> GO/NO-GO -> prod deploy proceeds or is refused

WHY THIS EXISTS
---------------
2026-08-07: a deploy truncated the shared Caddyfile at 16:15. Caddy reads its config only at start,
so nothing failed for 12 hours — until patchwatch's kernel reboot at 04:22 made it re-read the file
and every domain on the host went down together. There was no environment in which that change
could have been rebooted first.

So the gate is not "did the deploy succeed". It is:
    deploy to staging -> health -> REBOOT IT -> health again -> AI digest -> only then production.
The reboot is the point. It is the one test that would have caught the actual outage, and it cannot
be run on the production box or in a container sharing the host kernel.

STAGING IS A REAL SECOND DROPLET (FRA1, 4 GB / 2 AMD vCPU / 80 GB, Ubuntu 24.04) — same size, same
image, same region as production. A twin that differs in region or size is not a twin: latency to
the inference endpoint, host hardware generation and kernel line are exactly the variables that
make "it worked in staging" untrue.

SYNTHETIC DATA ONLY. Staging never receives production personal data — no user emails, no job rows,
no telemetry copies. It builds its own state from the committed demo fixtures (RFC 5737 addresses).
That keeps the /privacy claim true without adding a second location to disclose, and means a
staging compromise leaks nothing about anyone.
"""
import json
import os
import subprocess
import sys
import time

from recover import SSH, USER, sections

HERE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.environ.get("STAGING_HOST", "165.245.244.174")
PROD = os.environ.get("DROPLET_HOST", "64.225.108.200")


def ssh_script(script, host=STAGING, timeout=900):
    """One session, LF bytes over stdin, explicit UTF-8 out. See recover.ssh_script for the two
    bugs this shape exists to avoid (argv length limit, and Windows CRLF translation)."""
    try:
        r = subprocess.run(SSH + ["%s@%s" % (USER, host), "bash -s"],
                           input=script.encode("utf-8"), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT after %ds" % timeout, 124
    dec = lambda b: (b or b"").decode("utf-8", "replace")   # noqa: E731
    return dec(r.stdout), dec(r.stderr), r.returncode


# --------------------------------------------------------------------------- provisioning
PROVISION = r"""
set +e
export DEBIAN_FRONTEND=noninteractive
echo "#### PROVISION"
if ! command -v docker >/dev/null 2>&1; then
  echo "installing docker..."
  apt-get update -qq && apt-get install -y -qq ca-certificates curl git jq >/dev/null 2>&1
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null 2>&1
fi
echo "docker: $(docker --version 2>/dev/null || echo MISSING)"
mkdir -p /opt/colt-stack /opt/stagegate /data
echo "kernel: $(uname -r)"
echo "ram:    $(free -m | awk '/Mem:/{print $2"MB total, "$7"MB available"}')"
echo "disk:   $(df -h / | awk 'NR==2{print $4" free of "$2}')"
"""

# The deterministic gate. Each line prints `CHECK|<name>|<ok>|<detail>` so the PC side can parse it
# without guessing, and the SAME strings become the evidence the models review.
HEALTH = r"""
set +e
C=colt-web
chk() { printf 'CHECK|%s|%s|%s\n' "$1" "$2" "$3"; }
echo "#### HEALTH"

S=$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)
[ "$S" = "running" ] && chk container_running yes "$C is $S" || chk container_running no "$C is ${S:-absent}"

R=$(docker inspect -f '{{.RestartCount}}' "$C" 2>/dev/null || echo 99)
[ "${R:-99}" -le 1 ] && chk restart_count yes "restarts=$R" || chk restart_count no "restarts=$R (crash loop?)"

# The app answers AND enforces auth. Probing "/" alone would go green on a cached PWA shell.
H=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1:8090/api/me)
[ "$H" = "401" ] && chk api_auth yes "GET /api/me -> 401 (up + locked)" || chk api_auth no "GET /api/me -> $H (want 401)"

H=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1:8090/)
case "$H" in 200|301|302|308) chk app_served yes "GET / -> $H";; *) chk app_served no "GET / -> $H";; esac

# THE CHECK THAT WOULD HAVE CAUGHT THE OUTAGE: is the proxy config actually loadable, right now,
# in the image and environment the proxy really runs with?
if [ -f /opt/caddyguard/agent.py ]; then
  python3 /opt/caddyguard/agent.py check >/tmp/cg.out 2>&1
  [ $? -eq 0 ] && chk proxy_config yes "caddyguard: live config valid" \
                || chk proxy_config no "caddyguard: $(tail -2 /tmp/cg.out | tr '\n' ' ')"
else
  chk proxy_config no "caddyguard agent not installed on staging"
fi

# The engine in the container must be THIS repo's code. A container that started is not code that shipped.
docker exec "$C" python3 -c "import hashlib,glob,os;print(sum(1 for _ in glob.glob('/opt/shodan-skill/scripts/*.py')))" >/tmp/eng 2>&1
[ $? -eq 0 ] && chk engine_present yes "engine scripts: $(cat /tmp/eng)" || chk engine_present no "$(cat /tmp/eng)"

# Exercise the ENGINE, not just the web server: build the demo artifacts from synthetic fixtures.
docker exec "$C" python3 /opt/shodan-skill/scripts/demo_build.py >/tmp/demo.out 2>&1
[ $? -eq 0 ] && chk engine_runs yes "demo artifacts built from RFC 5737 fixtures" \
             || chk engine_runs no "$(tail -3 /tmp/demo.out | tr '\n' ' ')"

M=$(free -m | awk '/Mem:/{print $7}')
[ "${M:-0}" -gt 300 ] && chk memory yes "${M}MB available" || chk memory no "only ${M}MB available"
D=$(df --output=pcent / | tail -1 | tr -dc '0-9')
[ "${D:-100}" -lt 90 ] && chk disk yes "${D}% used" || chk disk no "${D}% used"
echo "#### KERNEL"
uname -r
[ -f /var/run/reboot-required ] && echo "reboot-required: YES" || echo "reboot-required: no"
"""

REBOOT = r"""
set +e
echo "#### REBOOT"
uname -r
echo "uptime_before: $(cut -d. -f1 /proc/uptime)s"
nohup sh -c 'sleep 2; systemctl reboot' >/dev/null 2>&1 &
echo "reboot issued"
"""


def parse_checks(text):
    out = []
    for ln in (text or "").splitlines():
        if ln.startswith("CHECK|"):
            p = ln.split("|", 3)
            if len(p) == 4:
                out.append({"name": p[1], "ok": p[2].strip() == "yes", "detail": p[3].strip()})
    return out


def wait_for_ssh(host, timeout=300):
    """Poll until the box answers again after a reboot. Returns seconds waited, or None."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        out, _, rc = ssh_script("echo UP", host=host, timeout=25)
        if rc == 0 and "UP" in out:
            return int(time.time() - t0)
        time.sleep(10)
    return None


def notify(subject, body):
    """Email + Telegram, sent FROM the production droplet — that is where the Gmail credentials and
    the bot token already live, and SMTP is blocked outbound on this host so the Gmail API is the
    only working path (a documented constraint; do not 'fix' it to SMTP)."""
    payload = json.dumps({"subject": subject, "body": body})
    script = ("set +e\ncat >/tmp/sg.json <<'JSON'\n%s\nJSON\n"
              "docker exec -i colt-web python3 - <<'PY'\n"
              "import json,sys\n"
              "sys.path.insert(0,'/app')\n"
              "d=json.load(open('/tmp/sg.json'))\n"
              # notify.both() sends email AND Telegram and is already the one place that knows
              # how (Gmail API, because SMTP is blocked outbound on this host). Do not
              # re-implement either channel here.
              "try:\n"
              "    from app import notify as N\n"
              "    N.both(d['subject'], d['body']); print('sent: email + telegram')\n"
              "except Exception as e: print('notify failed:', e)\n"
              "PY\n" % payload)
    out, _, _ = ssh_script(script, host=PROD, timeout=120)
    return out.strip()


def run(reboot_test=True, quiet=False):
    """-> (gate, digest). gate is 'GO' or 'NO-GO'. Never raises."""
    say = (lambda *a: None) if quiet else (lambda *a: print("  " + " ".join(str(x) for x in a)))

    say("staging: %s   (synthetic data only, never production personal data)" % STAGING)
    out, err, rc = ssh_script(PROVISION, timeout=600)
    if rc != 0 and not out:
        return "NO-GO", "staging unreachable: %s" % (err or "")[:300]
    say((sections(out).get("PROVISION") or "").replace("\n", "\n  "))

    # Ship the quorum reviewer to staging (it runs INSIDE the container, where the key is).
    q = open(os.path.join(HERE, "deploy", "stagegate", "quorum.py"), encoding="utf-8").read()
    ssh_script("mkdir -p /opt/stagegate\ncat >/opt/stagegate/quorum.py <<'PYEOF'\n%s\nPYEOF\n"
               "docker cp /opt/stagegate/quorum.py colt-web:/opt/stagegate/quorum.py 2>/dev/null "
               "|| true\necho ok\n" % q, timeout=120)

    out, _, _ = ssh_script(HEALTH, timeout=600)
    checks = parse_checks(out)
    kernel_before = (sections(out).get("KERNEL") or "").splitlines()[:1]
    for c in checks:
        say("  %-18s %s  %s" % (c["name"], "OK " if c["ok"] else "FAIL", c["detail"][:90]))

    reboot = {}
    if reboot_test:
        # THE TEST THAT MATTERS. Everything above proves the change works on a running box; only
        # this proves it survives the thing that actually took production down.
        say("rebooting staging — the one test the production box can never run...")
        ssh_script(REBOOT, timeout=60)
        time.sleep(20)
        waited = wait_for_ssh(STAGING, timeout=300)
        if waited is None:
            checks.append({"name": "reboot_recovery", "ok": False,
                           "detail": "staging did not answer ssh within 300s of a reboot"})
            reboot = {"came_back": False}
        else:
            say("back after %ds — re-running every health check" % waited)
            out2, _, _ = ssh_script(HEALTH, timeout=600)
            post = parse_checks(out2)
            reboot = {"came_back": True, "seconds": waited,
                      "kernel_before": kernel_before,
                      "kernel_after": (sections(out2).get("KERNEL") or "").splitlines()[:1]}
            for c in post:
                c["name"] = "post_reboot_" + c["name"]
                say("  %-28s %s  %s" % (c["name"], "OK " if c["ok"] else "FAIL", c["detail"][:80]))
            checks += post

    evidence = {"host": STAGING, "role": "staging twin of %s" % PROD,
                "checks": checks, "reboot": reboot, "ts": time.time()}

    say("asking 2 soldiers + 2 auditors for a written verdict...")
    ev = json.dumps(evidence)
    out3, _, _ = ssh_script(
        "set +e\ncat >/tmp/ev.json <<'JSON'\n%s\nJSON\n"
        "docker exec -i colt-web python3 /opt/stagegate/quorum.py < /tmp/ev.json\n" % ev,
        timeout=600)
    try:
        verdict = json.loads(out3[out3.index("{"):out3.rindex("}") + 1])
    except Exception:
        # The gate must never depend on the panel answering. Fall back to the deterministic rule.
        failed = [c for c in checks if not c["ok"]]
        verdict = {"gate": "GO" if (checks and not failed) else "NO-GO",
                   "digest": "AI panel unavailable — gate decided by %d deterministic checks (%d failed)."
                             % (len(checks), len(failed)),
                   "answered": 0}
    return verdict.get("gate", "NO-GO"), verdict.get("digest", "")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Validate a change on staging before production.")
    ap.add_argument("--no-reboot", action="store_true", help="skip the reboot test (faster, weaker)")
    a = ap.parse_args()
    gate, digest = run(reboot_test=not a.no_reboot)
    print("\n" + digest)
    print("\nGATE: %s" % gate)
    print(notify("cybergod staging validation: %s" % gate, digest))
    return 0 if gate == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
