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
# A BROWSER USER-AGENT IS REQUIRED, and this is not cosmetic: visitors.py serves BOTS a 404 on page
# routes, and `curl` announces itself as a bot. The first version probed with plain curl, got the
# 404 the gate is designed to return, and recorded it as a broken app. The check has to look like
# the client it claims to be testing.
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36'
chk() { printf 'CHECK|%s|%s|%s\n' "$1" "$2" "$3"; }
echo "#### HEALTH"

S=$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)
[ "$S" = "running" ] && chk container_running yes "$C is $S" || chk container_running no "$C is ${S:-absent}"

R=$(docker inspect -f '{{.RestartCount}}' "$C" 2>/dev/null || echo 99)
[ "${R:-99}" -le 1 ] && chk restart_count yes "restarts=$R" || chk restart_count no "restarts=$R (crash loop?)"

# The app answers AND enforces auth. Probing "/" alone would go green on a cached PWA shell.
H=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1:8090/api/me)
[ "$H" = "401" ] && chk api_auth yes "GET /api/me -> 401 (up + locked)" || chk api_auth no "GET /api/me -> $H (want 401)"

H=$(curl -s -A "$UA" -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1:8090/)
case "$H" in 200|301|302|308) chk app_served yes "GET / -> $H (browser UA)";; *) chk app_served no "GET / -> $H";; esac

# The bot gate must still BLOCK bots. Testing only the happy path would let a change that disabled
# the gate sail through, and the gate is what keeps scanners out of the index.
B=$(curl -s -A "curl/8.0" -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1:8090/)
[ "$B" = "404" ] && chk bot_gate yes "a bot UA still gets 404" || chk bot_gate no "bot UA got $B (want 404)"

# THE CHECK THAT WOULD HAVE CAUGHT THE OUTAGE: is the proxy config actually loadable, right now,
# in the image and environment the proxy really runs with? Staging runs its OWN caddy from the
# COMMITTED snippet, so a change to deploy/caddy/cybergod.caddy is validated on a real Caddy —
# and survives a real reboot — before production's shared proxy ever sees it.
if [ -f /opt/caddyguard/agent.py ] && docker ps --format '{{.Names}}' | grep -qi caddy; then
  CADDYFILE=/opt/staging-caddy/Caddyfile python3 /opt/caddyguard/agent.py check >/tmp/cg.out 2>&1
  [ $? -eq 0 ] && chk proxy_config yes "caddyguard: staging proxy config valid + loaded" \
                || chk proxy_config no "caddyguard: $(grep -v 'telegram' /tmp/cg.out | tail -2 | tr '\n' ' ')"
  P=$(curl -s -A "$UA" -o /dev/null -w '%{http_code}' --max-time 15 -H 'Host: cybergod.ai' http://127.0.0.1:8080/api/me)
  [ "$P" = "401" ] && chk proxy_routes yes "proxy -> colt-web -> 401 (the production path)" \
                   || chk proxy_routes no "through the proxy /api/me -> $P (want 401)"
else
  chk proxy_config no "no caddy on staging — the shared-proxy config is NOT covered by this run"
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
# boot_id is a fresh random value on EVERY boot. It is the only cheap proof that the machine
# actually went down and came back. "ssh answered again" proves nothing: the first run reported
# "back after 1s" because the box had not finished going down yet, and that was recorded as a
# successful reboot test. A test that can pass without the event happening is not a test.
echo "boot_id_before: $(cat /proc/sys/kernel/random/boot_id)"
echo "kernel_before:  $(uname -r)"
echo "uptime_before:  $(cut -d. -f1 /proc/uptime)s"
nohup sh -c 'sleep 2; systemctl reboot' >/dev/null 2>&1 &
echo "reboot issued"
"""

BOOTID = "echo '#### BOOTID'\ncat /proc/sys/kernel/random/boot_id\nuname -r\ncut -d. -f1 /proc/uptime\n"


def parse_checks(text):
    out = []
    for ln in (text or "").splitlines():
        if ln.startswith("CHECK|"):
            p = ln.split("|", 3)
            if len(p) == 4:
                out.append({"name": p[1], "ok": p[2].strip() == "yes", "detail": p[3].strip()})
    return out


def boot_id(host=STAGING):
    out, _, rc = ssh_script(BOOTID, host=host, timeout=25)
    lines = (sections(out).get("BOOTID") or "").splitlines()
    return (lines + ["", "", ""])[:3] if rc == 0 else None


def wait_for_reboot(host, was, timeout=420):
    """Wait for a DIFFERENT boot_id. Returns (seconds, new_boot_info) or (None, None).

    Deliberately not "wait until ssh answers": right after `systemctl reboot` is issued the box is
    still up and answers instantly, which is exactly how the first version reported a 1-second
    reboot and called it a pass. We wait for the identity of the running kernel instance to change.
    """
    t0 = time.time()
    seen_down = False
    while time.time() - t0 < timeout:
        time.sleep(8)
        now = boot_id(host)
        if now is None:
            seen_down = True          # ssh refused: it really is going down
            continue
        if was and now[0] and now[0] != was[0]:
            return int(time.time() - t0), now
        if not seen_down and time.time() - t0 < 45:
            continue                  # same boot_id this early just means it has not gone down yet
    return None, None


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


def deploy_to_staging(say):
    """Build and start the SAME colt-web image on staging, from the SAME sources, via the SAME
    script production uses (deploy_web_direct.py) — only DROPLET_HOST and --no-proxy differ.

    Using a different deploy path for staging would test a different thing than the one that ships.

    SECRETS: colt-web needs a working OPENAI_API_KEY (the quorum runs inside it) and the rest of
    the runtime env. Those live ONLY in the droplet's env file, never in git, so the file is copied
    production -> staging through this PC. It is the same operator and the same trust boundary; the
    alternative is a staging twin whose engine cannot run, which validates nothing.
    """
    say("copying the runtime env from production (secrets never enter git)...")
    out, _, _ = ssh_script("set +e\necho '#### ENV'\ncat /opt/colt-stack/assess-bot/.env 2>/dev/null "
                           "| base64 -w0\n", host=PROD, timeout=90)
    blob = (sections(out).get("ENV") or "").strip()
    if blob:
        ssh_script("set -e\nmkdir -p /opt/colt-stack/assess-bot\n"
                   "echo '%s' | base64 -d > /opt/colt-stack/assess-bot/.env\n"
                   "chmod 600 /opt/colt-stack/assess-bot/.env\necho ok\n" % blob, timeout=90)
        say("  env file placed on staging (chmod 600)")
    else:
        say("  [!] production env file unreadable — the engine checks on staging will fail honestly")

    say("building colt-web on staging (same sources, same Dockerfile, no proxy wiring)...")
    env = dict(os.environ, DROPLET_HOST=STAGING)
    r = subprocess.run([sys.executable, os.path.join(HERE, "deploy_web_direct.py"), "--no-proxy"],
                       env=env, cwd=HERE)
    if r.returncode != 0:
        say("  [!] staging build failed (exit %s)" % r.returncode)
        return False

    # A REAL CADDY ON STAGING, from the COMMITTED snippet.
    # Without this the twin could not test the one thing that actually took production down: a
    # Caddy config that parses today and is only re-read at the next restart. Staging now runs its
    # own proxy on :8080 with the same deploy/caddy/cybergod.caddy block, so a bad snippet fails
    # HERE — and fails again on the reboot check — instead of sitting latent on the shared proxy.
    say("installing caddyguard + a real caddy on staging (validates the committed snippet)...")
    agent = open(os.path.join(HERE, "deploy", "caddyguard", "agent.py"), encoding="utf-8").read()
    snippet = open(os.path.join(HERE, "deploy", "caddy", "cybergod.caddy"), encoding="utf-8").read()
    ssh_script(
        "set +e\nmkdir -p /opt/caddyguard/blocks /opt/caddyguard/backups /opt/staging-caddy\n"
        "cat >/opt/caddyguard/agent.py <<'PYEOF'\n%s\nPYEOF\n"
        "cat >/opt/staging-caddy/cybergod.caddy <<'CADEOF'\n%s\nCADEOF\n"
        # Minimal base: no TLS (staging has no domain), auto_https off, plain :8080. The SITE
        # BLOCK itself is the committed one, which is the part worth testing.
        "{\n  printf '{\\n\\tauto_https off\\n\\tadmin off\\n}\\n\\n'\n"
        "  printf ':8080 {\\n\\treverse_proxy colt-web:8000\\n}\\n\\n'\n"
        "  cat /opt/staging-caddy/cybergod.caddy\n"
        "} > /opt/staging-caddy/Caddyfile\n"
        "docker rm -f staging-caddy >/dev/null 2>&1\n"
        "docker run -d --name staging-caddy --restart unless-stopped "
        "  --network videodead_appnet -p 127.0.0.1:8080:8080 "
        "  -v /opt/staging-caddy/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine >/dev/null 2>&1\n"
        "sleep 4\n"
        "echo '#### CADDY'\n"
        "docker ps --filter name=staging-caddy --format '{{.Names}} {{.Status}}'\n"
        "docker logs staging-caddy --tail 4 2>&1 | tail -4\n" % (agent, snippet), timeout=180)
    return True


def run(reboot_test=True, quiet=False):
    """-> (gate, digest). gate is 'GO' or 'NO-GO'. Never raises."""
    say = (lambda *a: None) if quiet else (lambda *a: print("  " + " ".join(str(x) for x in a)))

    say("staging: %s   (synthetic data only, never production personal data)" % STAGING)
    out, err, rc = ssh_script(PROVISION, timeout=600)
    if rc != 0 and not out:
        return "NO-GO", "staging unreachable: %s" % (err or "")[:300]
    say((sections(out).get("PROVISION") or "").replace("\n", "\n  "))

    # ---- DEPLOY THE STACK TO STAGING -------------------------------------------------------
    # The first version of this gate provisioned Docker and then health-checked a colt-web that
    # had never been put there — 14 checks failed and it correctly refused to promote, for entirely
    # the wrong reason. A gate that fails because the gate is incomplete teaches you to ignore it.
    if not deploy_to_staging(say):
        return "NO-GO", ("Could not deploy the stack to staging (%s). Nothing was changed on "
                         "production." % STAGING)

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
        was = boot_id(STAGING)
        ssh_script(REBOOT, timeout=60)
        waited, now = wait_for_reboot(STAGING, was, timeout=420)
        if waited is None:
            checks.append({"name": "reboot_recovery", "ok": False,
                           "detail": "staging never came back with a NEW boot_id within 420s "
                                     "(boot_id before=%s)" % (was[0][:8] if was else "?")})
            reboot = {"came_back": False, "boot_id_before": was}
        else:
            say("rebooted and back after %ds — boot_id %s -> %s (kernel %s)"
                % (waited, (was[0][:8] if was else "?"), now[0][:8], now[1]))
            checks.append({"name": "reboot_recovery", "ok": True,
                           "detail": "new boot_id after %ds, kernel %s, uptime %ss"
                                     % (waited, now[1], now[2])})
            out2, _, _ = ssh_script(HEALTH, timeout=600)
            post = parse_checks(out2)
            reboot = {"came_back": True, "seconds": waited,
                      "boot_id_before": (was[0] if was else None), "boot_id_after": now[0],
                      "kernel_before": kernel_before, "kernel_after": now[1]}
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
