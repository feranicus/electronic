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
import re
import os
import subprocess
import sys
import time

from recover import SSH, USER, sections

HERE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.environ.get("STAGING_HOST", "165.245.244.174")
PROD = os.environ.get("DROPLET_HOST", "64.225.108.200")


def ssh_script(script, host=STAGING, timeout=900, retries=2):
    """One session, LF bytes over stdin, explicit UTF-8 out, and BACK OFF when sshd says no.

    See recover.ssh_script for the two bugs this shape exists to avoid (argv length limit, Windows
    CRLF translation). The retry is the third lesson, learned the hard way:

    OpenSSH 9.8 turns on PerSourcePenalties BY DEFAULT, penalties ACCRUE with repetition, and
    MaxStartups compounds it. This gate used to open ~30 short-lived sessions per run (one per
    reboot poll), which is precisely the shape sshd is designed to refuse — and the NEXT run then
    hung on its very first connection, long after the polling had stopped.
    So: fewer sessions (see run()), spaced further apart, and an exponential back-off here instead
    of hammering a host that is already penalising us.
    """
    delay = 15
    for attempt in range(retries + 1):
        try:
            r = subprocess.run(SSH + ["%s@%s" % (USER, host), "bash -s"],
                               input=script.encode("utf-8"), capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            if attempt < retries:
                time.sleep(delay); delay *= 2
                continue
            return "", "TIMEOUT after %ds (sshd throttling? penalties decay on their own)" % timeout, 124
        dec = lambda b: (b or b"").decode("utf-8", "replace")   # noqa: E731
        out, err = dec(r.stdout), dec(r.stderr)
        # A refused/reset connection with no output is the throttle signature. Real command
        # failures still produce output and must NOT be retried.
        if r.returncode == 255 and not out and attempt < retries:
            time.sleep(delay); delay *= 2
            continue
        return out, err, r.returncode
    return "", "unreachable", 255


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
# ONE CHECK = ONE LINE, ALWAYS. The parser splits on newlines, so a stray newline inside a detail
# does not just look untidy — it truncates the record and the rest is silently lost. Squash any
# embedded newline/pipe here rather than trusting every call site to be careful.
#
# `tr` IS THE PROTOCOL PROTECTION. `cut` IS ONLY A RUNAWAY GUARD, AND IT WAS SET FAR TOO LOW.
# It was `cut -c1-200`, which silently amputated every long detail AT THE SOURCE:
#     "...without restarting the contain|er, and the live fil"     (exactly 200 chars)
#     "...the running config compa|red to the file - so"           (exactly 200 chars)
# I "fixed" this truncation on the PYTHON side by wrapping instead of slicing, told the operator it
# was fixed, and the very next run printed the same amputated sentences - because the printer was
# never where the cut happened. kimi-k2.6 flagged it for a THIRD time and was right every time.
# Same disease as the three config hops: I fixed the hop I could see, and the fix's own test could
# only see that hop too.
# The cap stays, because `agent.py ... 2>&1` on a crash can dump a whole traceback into $3 and one
# CHECK line should not become 50 KB. It is now far above any real detail (longest measured ~300).
chk() { printf 'CHECK|%s|%s|%s\n' "$1" "$2" "$(printf '%s' "$3" | tr '\n|' '  ' | cut -c1-1000)"; }
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
  CADDYFILE=/opt/staging-caddy/Caddyfile CADDY_PORT=8080 \
    python3 /opt/caddyguard/agent.py check >/tmp/cg.out 2>&1
  # NEVER truncate a failure detail to the last 2 lines: the line that names the cause is usually
  # not the last one. Show the whole diagnosis (minus the alerting noise) — that omission turned a
  # port mismatch into "FAIL ... structural: ok validate: ok", which reads as a contradiction.
  [ $? -eq 0 ] && chk proxy_config yes "caddyguard watchdog (agent.py check, the SAME code the 10-minute timer runs on production): config valid, proxy running, :8080 bound, bind mount fresh, AND the running config compared to the file - so an external edit that was never reloaded is caught here too" \
                || chk proxy_config no "caddyguard: $(grep -v -i 'telegram' /tmp/cg.out | tr '\n' ' | ')"
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
RC=$?
# "IT RAN" IS NOT "IT WORKED" — an auditor model was right about this. Check the ARTIFACTS:
# the deck files must exist with real size, and the HTML must not leak undefined/NaN/empty
# headings. Same doctrine as the deck-quality gate: read the artifact, not the exit code.
if [ $RC -ne 0 ]; then
  chk engine_runs no "$(tail -3 /tmp/demo.out | tr '\n' ' ')"
else
  N=$(docker exec "$C" sh -c 'ls -1 /data/demo/*.pptx 2>/dev/null | wc -l')
  H=$(docker exec "$C" sh -c 'ls -1 /data/demo/*.html 2>/dev/null | head -1')
  # `grep -c` prints "0" AND exits 1 when nothing matches, so `|| echo 0` produced TWO lines.
  # `[ "0\n0" -eq 0 ]` is a syntax error -> the whole condition failed -> a passing artifact was
  # reported as broken, and the embedded newline also split the CHECK| line so the detail was
  # truncated. head -1 makes the value single-valued whatever grep decides to do.
  BAD=$(docker exec "$C" sh -c "grep -c -E 'undefined|NaN|\\[object Object\\]|<h1></h1>' '$H' 2>/dev/null" | head -1)
  BAD=${BAD:-0}
  SZ=$(docker exec "$C" sh -c "stat -c %s '$H' 2>/dev/null || echo 0")
  CV=$(docker exec "$C" sh -c "grep -o '<canvas' '$H' 2>/dev/null | wc -l" | head -1); CV=${CV:-0}
  if [ "${N:-0}" -ge 3 ] && [ "${SZ:-0}" -gt 20000 ] && [ "${BAD:-1}" -eq 0 ] && [ "${CV:-0}" -ge 5 ]; then
    chk engine_runs yes "${N} decks + ${CV} canvases, no undefined/NaN/blank-heading leaks (output CHECKED, not exit 0). html prose is model-authored so its SIZE varies by design and is not a signature"
  else
    chk engine_runs no "decks=${N} html=${SZ}b canvases=${CV} leaks=${BAD} — it ran but the OUTPUT is wrong"
  fi
fi

# ---- RAISED BY THE AUDIT PANEL, now checks rather than caveats -----------------------------
# kimi-k2.6: "engine_runs uses static fixtures... could be stale cached bytecode".
# Correct. Hash the engine files INSIDE the container and compare to what was just shipped.
# This is the same doctrine as the production engine_is_current() verify: a container that
# started is not the code that shipped.
docker exec "$C" sh -c 'cd /opt/shodan-skill && sha256sum scripts/shodan_recon.py scripts/enrich.py \
  scripts/run_assessment.py 2>/dev/null | md5sum | cut -c1-12' > /tmp/eh 2>/dev/null
EH=$(cat /tmp/eh 2>/dev/null)
LH=$(cd /opt/colt-stack/hermes-skills/shodan-assessment && sha256sum scripts/shodan_recon.py \
  scripts/enrich.py scripts/run_assessment.py 2>/dev/null | md5sum | cut -c1-12)
[ -n "$EH" ] && [ "$EH" = "$LH" ] && chk engine_fresh yes "container engine == shipped sources ($EH)" \
  || chk engine_fresh no "container=$EH shipped=$LH — the container is NOT running what we sent"

# kimi-k2.6: "no evidence caddy RE-READ its config after reboot vs recycling a cached one".
# Also correct, and it is the EXACT shape of the 2026-08-07 outage: a file that validates while
# the process serves something else entirely. Ask the running process what it is serving and
# compare it to the file on disk.
if docker ps --format '{{.Names}}' | grep -qi caddy; then
  CT=$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)
  docker exec "$CT" caddy adapt --config /etc/caddy/Caddyfile 2>/dev/null \
    | tr -d ' \n' | md5sum | cut -c1-12 > /tmp/ondisk
  docker exec "$CT" wget -qO- http://localhost:2019/config/ 2>/dev/null \
    | tr -d ' \n' | md5sum | cut -c1-12 > /tmp/running
  D=$(cat /tmp/ondisk 2>/dev/null); R=$(cat /tmp/running 2>/dev/null)
  # EMPTY = md5 of the empty string, TRUNCATED TO THE SAME 12 CHARS the hashes use. The first
  # version compared 16 chars against a 12-char value, so this guard never fired and an
  # unanswerable query was reported as "the process is serving a DIFFERENT config" — a confident,
  # wrong diagnosis. Derive it, never retype it.
  EMPTY=$(printf '' | md5sum | cut -c1-12)

  # SECOND, INDEPENDENT PROOF — and the one that always works.
  # Caddy reads its Caddyfile ONLY AT START. That single fact is the whole 2026-08-07 RCA, and it
  # is also what makes this provable without any API: if the process started AFTER the file was
  # last written, it necessarily read the bytes that are on disk now. Comparing timestamps needs
  # no admin endpoint, no wget inside the container, and no cooperation from the process.
  # A check that depends on ONE mechanism fails whenever that mechanism is unavailable — which is
  # exactly what happened here — so this is the primary and the API is the corroboration.
  STARTED=$(date -d "$(docker inspect -f '{{.State.StartedAt}}' "$CT" 2>/dev/null)" +%s 2>/dev/null)
  WRITTEN=$(stat -c %Y /opt/staging-caddy/Caddyfile 2>/dev/null)
  if [ -n "$STARTED" ] && [ -n "$WRITTEN" ] && [ "$STARTED" -gt "$WRITTEN" ]; then
    AGE=$((STARTED - WRITTEN))
    if [ -n "$R" ] && [ "$R" != "$EMPTY" ] && [ "$D" = "$R" ]; then
      chk config_write_ordering yes "started ${AGE}s AFTER the file was written, and the admin API agrees ($D)"
    elif [ -n "$R" ] && [ "$R" != "$EMPTY" ]; then
      chk config_write_ordering no "started after the write, but admin says disk=$D running=$R — a RELOAD lost it"
    else
      chk config_write_ordering yes "started ${AGE}s after the write; WHAT it read is proven by mount_fresh + config_drift, not by this timing"
    fi
  elif [ -n "$STARTED" ] && [ -n "$WRITTEN" ] && [ "$STARTED" -eq "$WRITTEN" ]; then
    # Same-second tie. The deploy writes the file and then starts the container, so the order IS
    # correct — but one-second timestamp resolution cannot PROVE it. Say exactly that rather than
    # asserting a fault. (The `sleep 1` in deploy_to_staging should make this branch unreachable;
    # it stays because a tie must never be reported as staleness again.)
    chk config_write_ordering yes "written and started in the same second; content proven by mount_fresh + config_drift"
  elif [ -n "$STARTED" ] && [ -n "$WRITTEN" ]; then
    chk config_write_ordering no "the process started $((WRITTEN - STARTED))s BEFORE the config was written — it is serving something else"
  else
    chk config_write_ordering no "cannot determine container start vs file mtime (started=$STARTED written=$WRITTEN)"
  fi
fi

# gemma-4-31B-it: "not tested under load... concurrency bottlenecks".
# A modest burst: 40 concurrent requests. Not a load test — it is a concurrency SMOKE test, and
# it catches the failure that matters here (a proxy or worker pool that 5xx's under parallelism).
for i in $(seq 1 40); do
  curl -s -o /dev/null -w '%{http_code}\n' --max-time 20 http://127.0.0.1:8090/api/me &
done > /tmp/burst 2>/dev/null; wait
OK4=$(grep -c '^401$' /tmp/burst 2>/dev/null || echo 0)
BAD=$(grep -cv '^401$' /tmp/burst 2>/dev/null || echo 0)
[ "${OK4:-0}" -ge 38 ] && chk concurrency yes "40 parallel requests -> ${OK4}x401, ${BAD} other" \
  || chk concurrency no "40 parallel requests -> only ${OK4}x401, ${BAD} other (5xx under load?)"

# ---- KIMI'S "CONFIG DRIFT UNDETECTED", now a real check --------------------------------------
# Her point: caddy reads config only at start, so an edit AFTER startup is silently unapplied and
# nothing notices until the next restart. That is precisely the 2026-08-07 mechanism. With the
# admin API enabled we can now ask the RUNNING process what it serves and compare it to the file.
#
# THE FIRST VERSION OF THIS CHECK WAS BROKEN AND FAILED A HEALTHY BOX. It md5'd `caddy adapt`
# against `GET /config/`. Those are two SERIALISATIONS of one config — adapt emits the adapter's
# JSON, the admin API re-marshals from Go structs (reordered keys, filled-in defaults) — so byte
# equality was never achievable and the check could only ever say DRIFT. The proof was in its own
# output: the two hashes were IDENTICAL before and after a reboot. Caddy re-reads its config at
# start, so a genuinely stale process cannot survive a restart. A check whose result is unchanged
# by the event that would fix the fault is not measuring the fault.
# It now compares WHAT IS SERVED (hostnames + terminal handlers), via ONE implementation in the
# caddyguard agent that production uses too.
#
# MOUNT STALENESS - the hop that let a correct file sit in front of a dead site for hours.
# /etc/caddy/Caddyfile is a single-FILE bind mount, pinned to an inode. Replace the file instead
# of truncating it and the container reads the OLD inode forever: validate passes (it validates a
# fresh temp copy), reload succeeds (loading old bytes), and the semantic drift check passes
# (both its sides read from inside the container). This is the ONLY comparison that spans the
# mount, so staging must exercise it before production ever does.
if docker ps --format '{{.Names}}' | grep -qi caddy; then
  CT=$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)
  CF=$(docker inspect "$CT" --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}')
  if [ -n "$CF" ]; then
    HS=$(sha256sum "$CF" | cut -c1-12)
    CS=$(docker exec "$CT" sha256sum /etc/caddy/Caddyfile 2>/dev/null | cut -c1-12)
    [ "$HS" = "$CS" ] \
      && chk mount_fresh yes "container reads the current file ($HS) - bind mount is not stale" \
      || chk mount_fresh no  "STALE MOUNT: host=$HS container=$CS - the proxy is serving a replaced inode"
  else
    chk mount_fresh yes "no single-file Caddyfile mount on this box - nothing to compare"
  fi
fi

if docker ps --format '{{.Names}}' | grep -qi caddy; then
  D=$(python3 /opt/caddyguard/agent.py drift 2>&1 | tr '\n|' '  ' | cut -c1-800)
  # THE ROSTER CHECK USED TO BE INERT ON STAGING, and both auditors on the panel said so
  # (kimi-k2.6 and gemma-4-31B-it, 8 Aug 2026). It was invoked with CADDY_EXPECT="", and
  # agent.py::cmd_roster returns SKIP when the expected list is empty — so on the ONE box whose
  # entire job is to validate the committed cybergod snippet before production sees it, the check
  # that asks "is the domain actually served?" could never do anything. A check that always skips
  # is not a check; that lesson is written in CLAUDE.md three times over.
  #
  # Staging serves exactly one vhost: the committed deploy/caddy/cybergod.caddy block on :8080,
  # which is why the probes above send `Host: cybergod.ai`. So that IS the expected roster here.
  RO=$(CADDY_EXPECT="cybergod.ai" python3 /opt/caddyguard/agent.py roster 2>&1 | tr '\n|' '  ' | cut -c1-800)
  # ADMIN API EXPOSURE. Raised by kimi-k2.6 and checked by nobody: every drift/roster check READS
  # the admin API and the deploy WRITES through it, so if it were ever bound off-loopback or the
  # port published, whoever reached it would own the shared proxy while every check stayed green.
  AD=$(python3 /opt/caddyguard/agent.py admin 2>&1 | tr '\n|' '  ' | cut -c1-800)
  case "$AD" in
    OK*)   chk admin_api_closed yes "${AD#OK }" ;;
    SKIP*) chk admin_api_closed no  "could not check the admin API: ${AD#SKIP }" ;;
    *)     chk admin_api_closed no  "$AD" ;;
  esac
  # THE REFUSAL PATH. kimi-k2.6, 2026-08-13: every config check here exercises the HAPPY path, so
  # nothing proves the validator can say no. An earlier attempt at this wrote a broken fragment
  # into the live blocks directory and took staging down; agent.py selftest instead feeds garbage
  # to validate(), which writes a temp dir and runs a THROWAWAY container, and then asserts the
  # live file's hash is unchanged. It also requires the LIVE config to still validate in the same
  # breath, because a validator that rejects everything passes "does it reject garbage" perfectly.
  ST=$(python3 /opt/caddyguard/agent.py selftest 2>&1 | tr '\n|' '  ' | cut -c1-800)
  case "$ST" in
    OK*)   chk refuses_bad_config yes "${ST#OK }" ;;
    SKIP*) chk refuses_bad_config no  "could not exercise the validator: ${ST#SKIP }" ;;
    *)     chk refuses_bad_config no  "$ST" ;;
  esac
  case "$RO" in
    OK*) chk vhost_roster yes "${RO}" ;;
    # We are inside `if docker ps | grep caddy`, so a SKIP here cannot mean "no proxy". It means
    # the admin API was unreachable or the config would not parse: the check could not SEE its
    # subject, which is a failure to report, not a pass to wave through.
    SKIP*) chk vhost_roster no "the roster check could not run: ${RO#SKIP }" ;;
    *)   chk vhost_roster no  "$RO" ;;
  esac

  case "$D" in
    OK*)    chk config_drift yes "${D#OK }" ;;
    SKIP*)  chk config_drift yes "${D#SKIP } (nothing to compare - not a fault)" ;;
    # AN UNRECOGNISED VERDICT IS NOT A PASS. This branch used to read `chk config_drift yes
    # "drift check unavailable: $D"` and it is what let a 4-of-4 NO-GO panel be overruled by a
    # green gate on 2026-08-07: agent.py printed "STALE MOUNT ..." (itself a bug), that matched
    # none of the three known prefixes, and the catch-all scored the failure as SUCCESS.
    # A fallback that turns an unknown answer into a pass is strictly worse than no check.
    *)      chk config_drift no  "unrecognised drift verdict (treated as FAILURE): $D" ;;
  esac

# ---- DOES A CONFIG *CHANGE* ACTUALLY PROPAGATE? --------------------------------------------
# kimi-k2.6 (9 Aug 2026): "no check exercises the reload path; config_drift compares running
# against file, but nothing proves hop 2 updates when the file CHANGES."
#
# Half wrong: every deploy writes, applies and then runs config_drift, on both boxes. But the
# valuable half is right -- each run writes essentially the SAME config, so drift passing does
# not prove a DIFFERENT config would propagate. That is precisely the 6 Aug failure mode: the
# file changed and the running process kept serving the old bytes for twelve hours.
#
# So: add a real vhost through the guard's own validate-then-apply path, prove it becomes
# SERVED without a reboot, then remove it and prove it is gone. This is safe here in a way it
# would not be on production -- the fragment is VALID (unlike the negative test that took
# staging down in an earlier round), it goes through the same validation every project uses,
# and the revert runs unconditionally.
# The container name and the staging Caddyfile path are NOT assumed: they are read the same way
# the proxy_config check above reads them. Using a $CADDY variable that this script never defines
# is exactly the "assume a name instead of reading it" defect that has cost this session four
# separate rounds.
CADDY_C=$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)
if [ -z "$CADDY_C" ] || [ ! -f /opt/caddyguard/agent.py ]; then
  chk guard_write_path_reloads yes "no caddy on this box - nothing to propagate (not a fault)"
else
  # NON-DESTRUCTIVE BY CONSTRUCTION. The previous version rebuilt the Caddyfile from
  # /opt/caddyguard/blocks/ via `assemble --apply` -- and STAGING IS NOT FRAGMENT-MANAGED: its
  # Caddyfile is composed directly by the provisioning step above, so blocks/ held nothing but the
  # probe. The reassembly was therefore EMPTY, it was written over the live config, Caddy kept
  # serving from memory, and the reboot detonated it: post_reboot_proxy_routes 000 and an empty
  # roster. I reproduced the 2026-08-07 outage with the check built to detect it.
  # Now: snapshot the exact bytes, APPEND the probe to the config that is actually live, apply it
  # through the guard's own validate -> write -> mount-check -> reload path, then restore the
  # snapshot byte-for-byte and VERIFY the restore. Nothing is ever rebuilt from an assumption
  # about where this box keeps its configuration.
  PROBE="cg-reload-probe.invalid"
  CF=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' "$CADDY_C" 2>/dev/null)
  if [ -z "$CF" ] || [ ! -f "$CF" ]; then
    chk guard_write_path_reloads yes "SKIP the proxy does not bind-mount a Caddyfile - nothing to test"
  else
  cp -p "$CF" /tmp/cg_snapshot.caddy
  python3 - "$CF" "$PROBE" <<'PYEOF' >/tmp/cg_prop.log 2>&1
import os, sys
cf, probe = sys.argv[1], sys.argv[2]
os.environ["CADDYFILE"] = cf
sys.path.insert(0, "/opt/caddyguard")
import agent
original = agent.read(cf)
ok, msg = agent.apply(original.rstrip("\n") + "\n\nhttp://%s {\n\trespond \"reload-probe\" 200\n}\n" % probe,
                      "propagation probe")
print("APPLY %s %s" % (ok, msg))
PYEOF
  SERVED_AFTER=$(docker exec "$CADDY_C" wget -qO- http://127.0.0.1:2019/config/ 2>/dev/null | grep -c "$PROBE")
  # THE RESTORE IS UNCONDITIONAL and byte-exact: the snapshot is put back and re-applied, whatever
  # happened above. A test that can leave a proxy serving something the operator did not commit is
  # an outage with a pass/fail label.
  cp -p /tmp/cg_snapshot.caddy "$CF"
  python3 - "$CF" <<'PYEOF' >>/tmp/cg_prop.log 2>&1
import os, sys
os.environ["CADDYFILE"] = sys.argv[1]
sys.path.insert(0, "/opt/caddyguard")
import agent
ok, msg = agent.apply(agent.read(sys.argv[1]), "restore after propagation probe")
print("RESTORE %s %s" % (ok, msg))
PYEOF
  SERVED_GONE=$(docker exec "$CADDY_C" wget -qO- http://127.0.0.1:2019/config/ 2>/dev/null | grep -c "$PROBE")
  RESTORED=$(cmp -s /tmp/cg_snapshot.caddy "$CF" && echo yes || echo no)
  if [ "$RESTORED" != "yes" ]; then
    chk guard_write_path_reloads no "the probe ran but the config was NOT restored byte-for-byte - $CF differs from the snapshot"
  elif [ "${SERVED_AFTER:-0}" -ge 1 ] && [ "${SERVED_GONE:-1}" -eq 0 ]; then
    chk guard_write_path_reloads yes "a change written through the guard's OWN path (validate -> write -> mount-check -> EXPLICIT caddy reload, via agent.apply) reached the running config without restarting the container, and the live file was then restored and cmp-verified byte-for-byte. NOTE: a bare file edit does NOT propagate - Caddy reads its config at start or on reload, which is why the write goes through apply()"
  elif [ "${SERVED_AFTER:-0}" -lt 1 ]; then
    chk guard_write_path_reloads no "a new vhost was written and applied but NEVER reached the running config - that is the 2026-08-07 latent-outage mechanism, reproduced live. $(tail -2 /tmp/cg_prop.log | tr '\n' ' ')"
  else
    chk guard_write_path_reloads no "the probe vhost was removed from disk but is STILL in the running config - a deletion does not propagate"
  fi
  fi
fi

fi

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


# Words that mean "this went wrong". If they appear in the DETAIL of a check that reported a
# PASS, the check is contradicting itself and cannot be trusted in either direction.
_CONTRADICTION = re.compile(
    r"(?i)\b(stale|drift(?!\s+check\s+(?:ok|passed))|unrecognis|unrecogniz|unavailable|cannot|"
    r"could not|failed|failure|broken|replaced inode|old bytes|not in force|refus)")
# Phrases that legitimately contain a scary word while describing a HEALTHY outcome. Without
# these, "no silent drift" and "bind mount is not stale" would flag themselves.
_BENIGN = re.compile(r"(?i)(no silent drift|not stale|nothing to compare|no drift|"
                     r"zero undefined|not just exit 0|single-file mount not in use)")


def say_check(say, c, pad=18, width=90):
    """Print ONE check, WRAPPING the detail rather than truncating it.

    `say` is passed in because it is a LOCAL built in run() (quiet mode swaps it for a no-op), the
    same way deploy_to_staging(say) takes it. My first version assumed it was module scope and died
    with NameError the moment it ran - read the helper, do not guess its binding.

    ONE implementation, because there were two and only one of them was fixed. The pre-reboot loop
    was corrected to wrap on 2026-08-13 (kimi-k2.6 flagged the mid-word cuts and was right); the
    POST-reboot loop twelve lines below it kept `detail[:80]` and went on truncating every
    `post_reboot_*` line for three more releases, in the same function, under a comment explaining
    why truncating is wrong.

    Why it matters at all: the detail is where a check states WHAT it measured. Cutting it destroys
    exactly the evidence the check exists to provide, silently, on the PASSING path where nobody
    looks twice. It also feeds the review panel, so a reviewer reading half a sentence reasons from
    half the facts - which is how the same wrong call gets made three runs running.

    Fixing a formatting defect in one of two copies is the "one home for a value" rule wearing a
    different hat. There is now one copy.
    """
    d = str(c.get("detail") or "")
    say("  %-*s %s  %s" % (pad, c["name"], "OK " if c["ok"] else "FAIL", d[:width]))
    rest = d[width:]
    while rest:
        say("  %-*s      %s" % (pad, "", rest[:width]))
        rest = rest[width:]


def self_contradictory(c):
    """A check that says PASS while its detail describes a failure is a BROKEN CHECK.

    Returns "" or a human-readable fragment SHOWING THE MATCH IN CONTEXT. It used to return the
    bare regex match, so a false positive printed `detail says 'refus'` — five characters, out of
    any context, matched inside the word "refuses" in a detail that was describing correct
    behaviour. It took a model to work that out from first principles; the message should simply
    have said it. Print what matched AND what surrounds it, so the next false positive is a
    ten-second diagnosis instead of a deploy cycle.
    """
    if not c["ok"]:
        return ""
    d = c["detail"]
    if _BENIGN.search(d):
        return ""
    m = _CONTRADICTION.search(d)
    if not m:
        return ""
    a, b = max(0, m.start() - 28), min(len(d), m.end() + 28)
    return "%r in ...%s..." % (m.group(0), d[a:b].strip())


def _decide_from_verdict(verdict):
    """(gate, digest) — the FINAL promotion decision. Pure: no ssh, no droplet, fully testable.

    UNANIMOUS PANEL DISSENT AGAINST A GREEN GATE IS ITSELF EVIDENCE.
    The deterministic checks still DECIDE. Models must never veto a good release over a 429 or a
    bad mood, and an agreeable model must never wave through a dead container — both directions
    are asserted in the tests. But on 2026-08-07 all four reviewers said NO-GO, all four named
    config_drift, all four were RIGHT (the check was scoring a failure as a pass), and the run
    promoted to production anyway with a one-line note. When EVERY independent reviewer
    contradicts a green gate, the gate is the thing under suspicion, and that has to reach a human
    BEFORE production rather than in a paragraph after it. So: halt, and require an explicit
    override. A quorum is >= 3 reviewers, so a single answer is never enough to stop a release.
    """
    gate = verdict.get("gate", "NO-GO")
    revs = verdict.get("reviews") or []
    dissent = [r for r in revs if str(r.get("verdict", "")).lower().replace("_", "-") == "no-go"]
    verdict["unanimous_dissent"] = bool(revs) and len(dissent) == len(revs) and len(revs) >= 3
    if gate == "GO" and verdict["unanimous_dissent"] and not os.environ.get("OVERRIDE_PANEL"):
        names = ", ".join(str(r.get("model", "?")) for r in revs)
        verdict["gate"] = gate = "NO-GO"
        verdict["digest"] = (
            "HALTED: every deterministic check passed, but ALL %d reviewers (%s) said NO-GO.\n"
            "A unanimous panel against a green gate usually means a CHECK is lying, not that the "
            "system is fine - that is exactly what happened on 2026-08-07.\n"
            "Read their reasons above. To promote anyway: set OVERRIDE_PANEL=1 and re-run.\n\n"
            % (len(revs), names)) + verdict.get("digest", "")
    return gate, verdict.get("digest", "")


def parse_checks(text):
    out = []
    for ln in (text or "").splitlines():
        if ln.startswith("CHECK|"):
            p = ln.split("|", 3)
            if len(p) == 4:
                c = {"name": p[1], "ok": p[2].strip() == "yes", "detail": p[3].strip()}
                word = self_contradictory(c)
                if word:
                    # Demote it. The system may well be fine; the CHECK is not, and a check we
                    # cannot trust must not be counted as evidence that we may promote.
                    c["ok"] = False
                    c["detail"] = ("SELF-CONTRADICTORY CHECK (said PASS, detail says %r) -> "
                                   "treated as FAILURE: %s" % (word, c["detail"]))
                out.append(c)
    return out


def boot_id(host=STAGING, quiet=False):
    # retries=0 while polling a rebooting box: a refusal there is EXPECTED (that is the signal we
    # are waiting for), and retrying it would triple the handshake count for no information.
    out, _, rc = ssh_script(BOOTID, host=host, timeout=25, retries=0 if quiet else 1)
    lines = (sections(out).get("BOOTID") or "").splitlines()
    return (lines + ["", "", ""])[:3] if rc == 0 else None


def wait_for_reboot(host, was, timeout=420):
    """Wait for a DIFFERENT boot_id. Returns (seconds, new_boot_info) or (None, None).

    Deliberately not "wait until ssh answers": right after `systemctl reboot` is issued the box is
    still up and answers instantly, which is exactly how the first version reported a 1-second
    reboot and called it a pass. We wait for the identity of the running kernel instance to change.
    """
    # SLEEP FIRST, AND SLEEP LONG. A DO droplet takes ~25-40s to come back, so polling every 8s
    # bought nothing but ~30 extra ssh handshakes per run — enough to trip PerSourcePenalties and
    # make the NEXT run hang on its first connection. 30s spacing costs at most 30s of wall clock
    # and cuts the handshake count by ~4x.
    t0 = time.time()
    seen_down = False
    time.sleep(25)                    # it is definitely not back yet; do not even ask
    while time.time() - t0 < timeout:
        now = boot_id(host, quiet=True)
        if now is None:
            seen_down = True          # ssh refused: it really is going down
        elif was and now[0] and now[0] != was[0]:
            return int(time.time() - t0), now
        elif seen_down or time.time() - t0 > 60:
            pass                      # back up but same boot_id -> keep waiting (or it never went)
        time.sleep(30)
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

    # ONE SESSION for provision + env. Every extra handshake feeds PerSourcePenalties, and this
    # gate was opening four before the build had even started.
    setup = PROVISION
    if blob:
        setup += ("\nmkdir -p /opt/colt-stack/assess-bot\n"
                  "echo '%s' | base64 -d > /opt/colt-stack/assess-bot/.env\n"
                  "chmod 600 /opt/colt-stack/assess-bot/.env\n"
                  "echo 'env file placed (chmod 600)'\n" % blob)
    else:
        setup += "\necho '[!] production env unreadable - engine checks will fail honestly'\n"
    out, err, rc = ssh_script(setup, timeout=600)
    if rc != 0 and not out:
        say("  staging unreachable: %s" % (err or "")[:200])
        return False
    say((sections(out).get("PROVISION") or "").replace("\n", "\n  "))

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
        # ADMIN API ON (localhost, inside the container). I originally wrote `admin off` here, which
        # made the config_write_ordering check unpassable BY CONSTRUCTION: it asks the running process what
        # config it is serving, and with the admin API disabled there is nobody to ask. A check that
        # cannot succeed is not a check — the same disease as the ruff gate that silently skipped.
        # Production already runs with the admin API enabled (deploy_web_direct POSTs to /load).
        "{\n  printf '{\\n\\tauto_https off\\n\\tadmin localhost:2019\\n}\\n\\n'\n"
        "  printf ':8080 {\\n\\treverse_proxy colt-web:8000\\n}\\n\\n'\n"
        "  cat /opt/staging-caddy/cybergod.caddy\n"
        "} > /opt/staging-caddy/Caddyfile\n"
        # ONE SECOND BETWEEN THE WRITE AND THE START. Filesystem mtimes and docker's StartedAt are
        # both whole seconds, so writing the config and starting the container inside the same
        # second makes their order UNPROVABLE — and the config_write_ordering check then reported
        # "started 0s BEFORE the config was written" on a system that was demonstrably fine.
        # Removing the ambiguity is the honest fix; widening the comparison to >= would only hide it.
        "sleep 1\n"
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

    # ---- DEPLOY THE STACK TO STAGING -------------------------------------------------------
    # The first version of this gate provisioned Docker and then health-checked a colt-web that
    # had never been put there — 14 checks failed and it correctly refused to promote, for entirely
    # the wrong reason. A gate that fails because the gate is incomplete teaches you to ignore it.
    if not deploy_to_staging(say):
        return "NO-GO", ("Could not deploy the stack to staging (%s). Nothing was changed on "
                         "production." % STAGING)

    # Ship the quorum reviewer AND run the health checks in ONE session (it runs INSIDE the
    # container, where the inference key is). Two calls here used to be two handshakes.
    q = open(os.path.join(HERE, "deploy", "stagegate", "quorum.py"), encoding="utf-8").read()
    ship_q = ("mkdir -p /opt/stagegate\ncat >/opt/stagegate/quorum.py <<'PYEOF'\n%s\nPYEOF\n"
              "docker exec colt-web mkdir -p /opt/stagegate 2>/dev/null || true\n"
              "docker cp /opt/stagegate/quorum.py colt-web:/opt/stagegate/quorum.py "
              "2>/dev/null || true\n" % q)
    out, _, _ = ssh_script(ship_q + HEALTH, timeout=600)
    checks = parse_checks(out)
    kernel_before = (sections(out).get("KERNEL") or "").splitlines()[:1]
    for c in checks:
        say_check(say, c)

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
                say_check(say, c, pad=28)
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
        globals()["_LAST_VERDICT"] = verdict     # govern.py reads the full panel output from here
    except Exception:
        # The gate must never depend on the panel answering. Fall back to the deterministic rule.
        failed = [c for c in checks if not c["ok"]]
        verdict = {"gate": "GO" if (checks and not failed) else "NO-GO",
                   "digest": "AI panel unavailable — gate decided by %d deterministic checks (%d failed)."
                             % (len(checks), len(failed)),
                   "answered": 0}
    return _decide_from_verdict(verdict)


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


_LAST_VERDICT = {}


def last_verdict():
    """The full panel output from the most recent run() — read by govern.py so the governance
    loop shows the SAME diagnoses the digest did, rather than asking the models a second time."""
    return _LAST_VERDICT
