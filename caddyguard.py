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


# JOBHUNTWOW IS A DIFFERENT PROJECT AND OWNS ITS OWN BLOCK.
# jobhuntwow-app/deploy/caddy/jobhuntwow.caddy is the snippet ITS deploy (`python jhw.py deploy`
# -> deploy_direct.py -> deploy/fix_caddy.py) writes into the shared Caddyfile. If this repo kept
# a second copy and pushed it every ship, the two projects would overwrite each other forever —
# that is the "a value with two homes" defect this file exists to prevent, one level up.
# So: prefer THEIR file when the sibling checkout is present; the local copy is only a fallback
# for a machine that does not have it. Same block either way, one authority.
JHW_APP = os.path.join(HERE, "jobhuntwow-app", "deploy", "caddy", "jobhuntwow.caddy")
JHW_FALLBACK = os.path.join(HERE, "deploy", "caddy", "jobhuntwow.caddy")


def jhw_snippet():
    return JHW_APP if os.path.exists(JHW_APP) else JHW_FALLBACK


def build(restore, check_only):
    agent = _b64(os.path.join(GUARD, "agent.py"))
    svc = _b64(os.path.join(GUARD, "caddyguard.service"))
    tmr = _b64(os.path.join(GUARD, "caddyguard.timer"))
    jhw = _b64(jhw_snippet())
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
  # THE REPO IS THE SOURCE OF TRUTH, NOT THE BACKUPS.
  # Every backup on this droplet was taken AFTER the 6 Aug damage, so "restore from the newest
  # good backup" could never recover jobhuntwow — there was no good backup left. The committed
  # block is authoritative, exactly as it already is for colt:cybergod. Ship it, then let the
  # routing predicate decide whether the live fragment needs replacing.
  echo '%s' | base64 -d > /tmp/jhw.caddy
  # COMPARE TO THE COMMITTED BLOCK, do not guess at its contents. The previous version asked
  # "does it contain file_server" — which was both wrong (jobhuntwow is a reverse proxy) and the
  # wrong SHAPE of question. The repo is authoritative; if the live fragment differs, replace it.
  if ! cmp -s /tmp/jhw.caddy /opt/caddyguard/blocks/jhw__jobhuntwow.caddy 2>/dev/null; then
    echo "jhw fragment differs from the committed block — installing the COMMITTED one"
    cp /tmp/jhw.caddy /opt/caddyguard/blocks/jhw__jobhuntwow.caddy
  else
    echo "jhw fragment already matches the committed block"
  fi
  python3 /opt/caddyguard/agent.py restore jhw:jobhuntwow

  # THE UPSTREAM CONTRACT (CADDY_ARCHITECTURE.md 2). A perfect Caddyfile in front of a missing or
  # unreachable app container still returns an empty 200 — which is exactly what the operator saw.
  # Check the thing the config points AT, not only the config.
  echo "-- jobhuntwow upstream (jhw-web:8000):"
  if docker ps --format '{{.Names}}' | grep -qx jhw-web; then
    echo "   jhw-web is running"
    NETS=$(docker inspect jhw-web --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}')
    N=$(echo $NETS | wc -w)
    echo "   networks: $NETS(count=$N)"
    case "$NETS" in
      *videodead_appnet*) [ "$N" -eq 1 ] \
          && echo "   OK: on videodead_appnet and on ONE network only" \
          || echo "   [!] on $N networks - Docker DNS can hand caddy an unreachable IP (intermittent 502s)" ;;
      *) echo "   [!] NOT on videodead_appnet - caddy cannot resolve jhw-web at all" ;;
    esac
    CT=$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)
    # MEASURE THE BODY, not the status line. A 200 with an empty body is the whole symptom, and a
    # probe that discards the body cannot tell the two apart. This is decisive: if the upstream
    # itself returns 0 bytes the fault is INSIDE jhw-web (its own project), not in this proxy.
    for path in / /api/health; do
      B=$(docker exec "$CT" wget -qO- "http://jhw-web:8000$path" 2>/dev/null | wc -c)
      H=$(docker exec "$CT" wget -qS -O /dev/null "http://jhw-web:8000$path" 2>&1 | grep -m1 HTTP/ | tr -d '\r')
      printf '   upstream %%-12s %%s  %%s bytes%%s\n' "$path" "${H:-NO ANSWER}" "$B" \
        "$([ "$B" -lt 200 ] && echo '   <- EMPTY: jhw-web itself is serving nothing' || true)"
    done
    echo "   jhw-web health : $(docker inspect jhw-web -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}' 2>/dev/null)"
    echo "   jhw-web image  : $(docker inspect jhw-web -f '{{.Config.Image}} started {{.State.StartedAt}}' 2>/dev/null)"
  else
    echo "   [!] jhw-web is NOT running - nothing to reverse_proxy to. Start it from ITS own project."
    docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -i jhw || true
  fi
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

echo "#### DRIFT"
# THE RUNNING PROCESS vs THE FILE. jobhuntwow stayed blank for hours because the file was right
# and the process was serving something else; `caddy reload` reported success. Compares WHAT IS
# SERVED, not bytes - see agent.py::cmd_drift for why a hash comparison is always a false positive.
python3 /opt/caddyguard/agent.py drift
if python3 /opt/caddyguard/agent.py drift 2>/dev/null | grep -q '^DRIFT'; then
  echo "-> forcing a full admin-API load so the process matches the file"
  CT=$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)
  # `caddy reload` IS the admin-API load - it adapts the file and POSTs it to /load itself.
  # (busybox wget in caddy:2-alpine has no --post-file, so hand-rolling the POST would fail.)
  docker exec "$CT" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile && echo FORCED_LOAD_OK \
    || echo "   [!] reload refused - the file is invalid; caddyguard check --heal will rebuild it"
  sleep 3
  python3 /opt/caddyguard/agent.py drift
fi

echo "#### VERIFY"
python3 /opt/caddyguard/agent.py show
echo "-- listeners:"
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(80|443)\s' || echo "NOTHING on 80/443"
echo "-- proxy:"
docker ps -a --filter name=caddy --format '{{.Names}}\t{{.Status}}'
echo "-- TLS certificate expiry (a lapsed cert takes EVERY domain down together):"
for d in cybergod.ai godeyes.ai jobhuntwow.com klimaanlage-preise.de; do
  END=$(echo | openssl s_client -connect 127.0.0.1:443 -servername "$d" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
  if [ -n "$END" ]; then
    LEFT=$(( ( $(date -d "$END" +%%s) - $(date +%%s) ) / 86400 ))
    if [ "$LEFT" -lt 14 ]; then printf '   [!] %%-28s %%s days left  <- RENEW\n' "$d" "$LEFT"
    else printf '   %%-32s %%s days left\n' "$d" "$LEFT"; fi
  else
    printf '   [!] %%-28s no certificate presented\n' "$d"
  fi
done
echo "-- local probes (code + BYTES: an empty 200 is what 'the site is dead' looks like):"
for u in https://cybergod.ai/api/me https://godeyes.ai/ https://www.jobhuntwow.com/ https://jobhuntwow.com/ https://klimaanlage-preise.de/; do
  R=$(curl -sk -o /tmp/body -w '%%{http_code} %%{size_download}' --max-time 12 "$u")
  CODE=${R%% *}; BYTES=${R##* }
  FLAG=""
  case "$CODE" in
    2*)      [ "$BYTES" -lt 200 ] && FLAG="   <- EMPTY BODY, the upstream is not answering" ;;
    3*|401)  : ;;   # a redirect legitimately has no body; 401 is the healthy answer for /api/me
    *)       FLAG="   <- FAILED" ;;
  esac
  printf '   %%-42s %%s  %%s bytes%%s\n' "$u" "$CODE" "$BYTES" "$FLAG"
done
echo "END"
""" % (agent, svc, tmr, "check" if check_only else "install",
       "yes" if restore else "no", jhw)


def _selftest():
    """RENDER THE SCRIPT BEFORE SHIPPING IT.

    This function exists because I broke it exactly this way: a `printf '%-28s'` added to a
    %-FORMATTED string, so Python consumed the spec and build() raised — and the failure was
    invisible because the caller only echoed stdout. CLAUDE.md has carried the "a literal % must
    be %%" rule since the `[100%%]` progress line; a rule that is not enforced is a rule that gets
    broken. Rendering both variants costs microseconds and makes the class impossible to ship.
    """
    for restore in (True, False):
        for check in (True, False):
            try:
                out = build(restore, check)
            except (TypeError, ValueError) as e:
                sys.exit("[X] caddyguard script does not render (%s: %s)\n"
                         "    Almost certainly a bare %% inside the %%-formatted template — it must "
                         "be %%%%.\n    Nothing was sent to the droplet." % (type(e).__name__, e))
            # NOTE: the RENDERED script legitimately contains shell format specs — `printf '%s'`
            # is ordinary shell. Asserting their absence confuses the shell's specs with Python's
            # and fails on correct output. The only thing worth asserting here is that Python's
            # own substitution completed without raising; a bare % in the template is exactly
            # what makes it raise.
            # The script's final line is  echo "END"  — quote included, so endswith("END") is
            # off by one character. Match the line, not a suffix.
            if 'echo "END"' not in out:
                sys.exit("[X] caddyguard script rendered truncated — refusing to send it.")
    return True


def main():
    _selftest()
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

    # Print EVERY section the remote script emitted, in the order it emitted them. A hardcoded
    # list here silently swallowed the DRIFT section on its first run: the check executed on the
    # droplet and nobody ever saw the answer. A second home for "which sections exist" is exactly
    # the drift this file exists to prevent.
    for k, sec in sections(out).items():
        if sec.strip():
            print("\n--- %s ---" % k)
            print("   " + sec.replace("\n", "\n   "))
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
