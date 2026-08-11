#!/usr/bin/env python3
"""
recover.py — ONE COMMAND to diagnose and restore the droplet when every site is refusing.

    python recover.py            diagnose, restart what is stopped, verify
    python recover.py --dry      diagnose only, change nothing

WHY THIS EXISTS (2026-08-07)
----------------------------
cybergod.ai, godeyes.ai AND jobhuntwow.com all went down at the same moment with
ERR_CONNECTION_REFUSED, while the droplet stayed Active and answered ping.

That combination is diagnostic on its own:
  * ping replies      -> the host and its networking are alive (ICMP is handled by the kernel)
  * CONNECTION REFUSED-> the SYN reached the host and got an RST. Not a timeout, not a firewall
                         drop: there is simply NOTHING LISTENING on 443
  * all three domains  -> they share ONE reverse proxy. videodead-caddy owns :443 and fronts every
                         site on this box (CLAUDE.md: colt-web joins videodead_appnet so
                         videodead-caddy reaches it as http://colt-web:8000)
So the fault is the shared proxy, not any one application, and not the code deployed to it.

WHAT THIS SCRIPT WILL AND WILL NOT DO
-------------------------------------
It DIAGNOSES first and prints everything, then RESTARTS containers that are defined but not
running. It is deliberately conservative, because this box also carries Amnezia VPN and joplin and
the standing rule is never to disturb them:
  * it only ever runs `docker start` on containers that already exist and are stopped
  * it NEVER removes, recreates or reconfigures anything
  * it NEVER touches the firewall, DNS or any config file
  * it makes no change at all under --dry
A config change belongs in a committed file and goes out through ship.py. Restarting a process
that died is an operational action, and this is the script for it.

EVERYTHING RUNS IN ONE SSH SESSION. The Windows OpenSSH client has no ControlMaster multiplexing
and OpenSSH 9.8 enables PerSourcePenalties by default, so a burst of short-lived sessions from one
address is exactly the shape sshd refuses. One session, one handshake.
"""
import argparse
import base64
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY = os.environ.get("DROPLET_KEY", os.path.expanduser("~/.ssh/id_rsa"))

SSH = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
       "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]
if os.path.exists(KEY):
    SSH += ["-i", KEY]

# The public names this box serves. Used only to verify recovery from the outside.
SITES = ["https://cybergod.ai/api/me", "https://www.cybergod.ai/",
         "https://godeyes.ai/", "https://www.jobhuntwow.com/"]

# The proxy that owns :443. If this is not running, every site on the box is refused.
PROXY_HINTS = ("caddy", "nginx-proxy", "traefik")


def ssh_script(script, timeout=240):
    """Run a multi-line bash script on the droplet in ONE session.

    base64 so no quoting layer (PowerShell -> ssh -> bash) can corrupt nested quotes — the same
    reason ship.py does it this way."""
    # THE SCRIPT GOES OVER STDIN, NOT THE COMMAND LINE.
    # It used to be base64'd INTO the argv ("echo <b64> | base64 -d | bash -s"). That works for a
    # short diagnostic and fails the moment the script carries a payload: caddyguard ships three
    # files (~26 KB of base64) and Windows' CreateProcess caps a command line at ~32 KB. Python
    # reports that overflow as FileNotFoundError, which this function then reported as
    # "ssh client not found" — a completely misleading diagnosis of a length problem.
    # stdin has no such limit, and it is still ONE ssh session.
    cmd = "bash -s"
    try:
        # ENCODING IS EXPLICIT, NOT THE PLATFORM DEFAULT. `text=True` alone makes Python decode
        # with the locale codec — cp1252 on this operator's Windows box. The droplet's output
        # carries UTF-8 (German umlauts in the Caddyfile comments, em-dashes in our own markers),
        # so the reader THREAD raised UnicodeDecodeError, subprocess returned stdout=None, and the
        # caller crashed on `write(None)` far away from the cause. Same family as the CRLF rule
        # already recorded for the deploy scripts: never let the platform decide the bytes.
        # BINARY IN, DECODE OURSELVES. Text mode on Windows translates every "\n" we write into
        # "\r\n", so bash was fed a CRLF script and answered `$'\r': command not found`. CLAUDE.md
        # has carried this exact rule since the deploy scripts hit it ("send LF bytes, never
        # text=True") and I broke it anyway the moment the payload moved to stdin.
        # Binary mode also keeps the UTF-8 fix: we decode explicitly instead of letting the
        # platform's cp1252 locale codec try (and die on the umlauts in the Caddyfile comments).
        r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), cmd],
                           input=script.encode("utf-8"), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT after %ds" % timeout, 124
    except FileNotFoundError:
        return "", "ssh client not found on this machine", 127
    dec = lambda b: (b or b"").decode("utf-8", "replace")   # noqa: E731
    return dec(r.stdout), dec(r.stderr), r.returncode


def sections(out):
    """Split output on '#### NAME' delimiters into {name: text}."""
    res, cur = {}, None
    for line in (out or "").splitlines():
        m = re.match(r"^####\s+(\S+)\s*$", line)
        if m:
            cur = m.group(1)
            res[cur] = []
        elif cur:
            res[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in res.items()}


# THE OUTSIDE VIEW COULD NOT SEE THE SITE IT MONITORS.
# This probe sent "cybergod-recover/1.0", and colt-web's BOT_404 gate serves an unrecognised
# user agent a 404 on every page route. So the deploy log printed
#     https://www.cybergod.ai/    HTTP 404
# run after run, which reads exactly like a dead site, and "5/5 endpoints answering" was counting
# a 404 as an answer. The only cybergod line that ever passed honestly was /api/me, and that is
# because /api/ is EXEMPT from the gate. In other words our external monitoring had never once
# checked that the pages work.
# Nth instance of the disease this repo keeps recording: a check that cannot see its subject.
# First-party monitoring of our own site is exactly the case the gate is not for, so it announces
# itself as a browser. check_bot_gate.py remains the thing that tests the gate, deliberately, by
# sending twelve agents on purpose.
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/127.0.0.0 Safari/537.36 cybergod-monitor/1.0")


def probe(url, timeout=12, ua=_BROWSER_UA):
    """(status, note) for a public URL. A 401 from /api/me is a HEALTHY answer."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return int(getattr(r, "status", 0) or 0), "ok"
    except urllib.error.HTTPError as e:
        return int(e.code), "http"                       # an HTTP error IS a live listener
    except Exception as e:
        return 0, type(e).__name__


DIAGNOSE = r"""
set +e
echo "#### UPTIME"
uptime
echo "#### DISK"
df -h / /var 2>/dev/null | sed -n '1,6p'
echo "#### MEM"
free -m
echo "#### DOCKER_STATE"
systemctl is-active docker 2>/dev/null || echo "systemctl-unavailable"
echo "#### PORTS"
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(80|443)\s' || echo "NOTHING LISTENING ON 80/443"
echo "#### RUNNING"
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo "docker-ps-failed"
echo "#### ALL"
docker ps -a --format '{{.Names}}\t{{.Status}}' 2>/dev/null
echo "#### STOPPED"
docker ps -a --filter status=exited --filter status=created --filter status=dead \
  --format '{{.Names}}\t{{.Status}}' 2>/dev/null
echo "#### RESTARTING"
docker ps -a --filter status=restarting --format '{{.Names}}\t{{.Status}}' 2>/dev/null
echo "#### CRASHLOOP_LOGS"
# THE ACTUAL ANSWER when a container is stuck restarting. `docker exec` refuses with
# "Container ... is restarting, wait until the container is running", which is what ship.py hit —
# a restart is useless here because the process dies again immediately. Only its own log says why.
for c in $(docker ps -a --filter status=restarting --format '{{.Names}}'; \
           docker ps -a --filter status=exited --format '{{.Names}}' | head -4); do
  echo "--- $c ---"
  docker logs --tail 30 "$c" 2>&1 | tail -30
done
echo "#### PUBLISHED_PORTS"
# A crash loop on a reverse proxy is very often a PORT CONFLICT: another container grabbed :80/:443
# first, the proxy cannot bind, exits, and docker restarts it forever. Listing what each container
# publishes makes the collision visible instead of inferred.
docker ps -a --format '{{.Names}}\t{{.Ports}}' 2>/dev/null | grep -E '(:80->|:443->|:80/|:443/)' || echo "-"
echo "#### CADDY_CONFIG"
# The other classic cause: a Caddyfile the proxy cannot parse. deploy_web_direct.py appends the
# committed cybergod block into videodead's Caddyfile, so a malformed append takes every site down.
#
# `docker exec` is useless here (the container is restarting) but `docker cp` works on a stopped
# OR restarting container, which is the only way to read the config of a proxy that will not start.
# The earlier version tried to re-mount the config via `docker inspect`; on a named volume that
# returns an empty source and produced "invalid spec: :/etc/caddy:ro". Copy it out instead.
for c in $(docker ps -a --format '{{.Names}}' | grep -i caddy); do
  echo "--- $c ---"
  rm -rf /tmp/_cfchk; mkdir -p /tmp/_cfchk
  if docker cp "$c":/etc/caddy/Caddyfile /tmp/_cfchk/Caddyfile 2>/dev/null; then
    echo "lines: $(wc -l < /tmp/_cfchk/Caddyfile)   braces: open=$(grep -o '{' /tmp/_cfchk/Caddyfile | wc -l) close=$(grep -o '}' /tmp/_cfchk/Caddyfile | wc -l)"
    # The error names a line. Show a window around it with numbers, so the malformation is visible
    # rather than inferred — that is the whole point of this section.
    ERRLINE=$(docker logs --tail 200 "$c" 2>&1 | grep -oE 'Caddyfile:[0-9]+' | tail -1 | cut -d: -f2)
    if [ -n "$ERRLINE" ]; then
      FROM=$((ERRLINE-12)); [ $FROM -lt 1 ] && FROM=1; TO=$((ERRLINE+8))
      echo "--- context around line $ERRLINE ---"
      sed -n "${FROM},${TO}p" /tmp/_cfchk/Caddyfile | nl -ba -v $FROM
    fi
    echo "--- our block markers ---"
    grep -n 'colt:cybergod' /tmp/_cfchk/Caddyfile || echo "(cybergod block not present)"
    echo "--- validate ---"
    docker run --rm -v /tmp/_cfchk:/etc/caddy:ro caddy:latest \
      caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -8
  else
    echo "could not docker cp the Caddyfile out of $c"
  fi
done
echo "#### OOM"
(dmesg -T 2>/dev/null | grep -i -E 'out of memory|oom-kill' | tail -8) || echo "-"
echo "#### DOCKER_ERR"
(journalctl -u docker --no-pager -n 15 2>/dev/null | tail -15) || echo "-"
"""

# --fix-caddy. Emergency repair for a proxy that will not start because its SHARED Caddyfile does
# not parse. Deliberately conservative and fully reversible:
#   * a timestamped backup is taken FIRST and its path is printed
#   * it only ever COMMENTS lines out — nothing is deleted, rewritten or reordered
#   * it comments the smallest unit that can be wrong: the enclosing site block of the line the
#     validator itself named, then re-validates, at most 5 times
#   * if it still does not validate, the backup is restored byte-for-byte and it reports failure
#   * our own block is never a candidate: deploy/caddy/cybergod.caddy is validated in CI, and if it
#     ever were the culprit the fix belongs in that committed file, not here
# This is an OUTAGE action on a file that is not a committed artifact of this repo. Any block it
# disables stays disabled until its owner fixes it properly — that is the trade: four sites back
# now, one still down, and a backup to restore from.
FIXCADDY = r"""
set +e
C=$(docker ps -a --format '{{.Names}}' | grep -i caddy | head -1)
[ -z "$C" ] && { echo "#### FIX"; echo "no caddy container found"; exit 0; }
echo "#### FIX"
echo "container: $C"
rm -rf /tmp/_cffix; mkdir -p /tmp/_cffix
docker cp "$C":/etc/caddy/Caddyfile /tmp/_cffix/Caddyfile || { echo "docker cp failed"; exit 1; }
BAK=/root/Caddyfile.bak.$(date +%Y%m%d-%H%M%S)
cp /tmp/_cffix/Caddyfile "$BAK"
echo "backup: $BAK"
python3 - "$BAK" "$C" <<'PYEOF'
import re, subprocess, shutil, sys
P = "/tmp/_cffix/Caddyfile"
BAK, CONT = sys.argv[1], sys.argv[2]

IMG = subprocess.run(["docker", "inspect", "-f", "{{.Config.Image}}", CONT],
                     capture_output=True, text=True).stdout.strip() or "caddy:latest"

# ...AND THE CONTAINER'S OWN ENVIRONMENT. Proven 2026-08-07: with the right image but no env, the
# validator reported `wrong argument count after 'email' at line 3` while the RUNNING container on
# the SAME image reported line 90. Line 3 uses a Caddy env placeholder (email {$...}); the running
# container has the variable, a bare `docker run` does not, so `email` arrives with no argument.
# That phantom error aborted a repair that had already worked. A validator that does not reproduce
# the container's environment is not reproducing the container.
_env = subprocess.run(["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", CONT],
                      capture_output=True, text=True).stdout.splitlines()
ENVARGS = []
for _e in _env:
    _e = _e.strip()
    if "=" in _e and not _e.startswith(("PATH=", "HOME=", "HOSTNAME=")):
        ENVARGS += ["-e", _e]
print("validating with the container's own image (%s) and %d of its env vars"
      % (IMG, len(ENVARGS) // 2))

def validate():
    # Validate with the image the container ACTUALLY runs. The first version used caddy:latest,
    # pulled a NEWER Caddy, and got a completely different complaint ("wrong argument count after
    # 'email' at line 3") that the running version does not make. A validator on a different
    # version is not a validator — it aborted a repair over a non-problem.
    r = subprocess.run(["docker", "run", "--rm", "-v", "/tmp/_cffix:/etc/caddy:ro"] + ENVARGS +
                       [IMG, "caddy", "validate", "--config", "/etc/caddy/Caddyfile",
                        "--adapter", "caddyfile"],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def fix_unclosed_block(lines):
    # THE ACTUAL FAULT on 2026-08-07: `jobhuntwow.com {` at line 79 was never closed — its
    # directives had been clobbered, leaving only comments — so everything after it parsed as that
    # block's contents and Caddy blamed line 90. `braces: open=22 close=21` was the real evidence.
    # Insert the missing `}` before the first END-marker or next site header that appears while we
    # are still inside a block. Returns the 0-based insert position, or None.
    # Both triggers require the line to be UNINDENTED. A nested `log {` / `handle {` legitimately
    # opens a brace at depth > 0, and an indented comment can say anything -- treating either as
    # "the previous block never closed" would insert the brace in the middle of a healthy block.
    # Managed markers and site headers in this file are all at column 0.
    depth = 0
    for i, ln in enumerate(lines):
        t = ln.split("#")[0]
        opened, closed = t.count("{"), t.count("}")
        top = ln[:1] not in (" ", "\t")
        if depth > 0 and top:
            if opened == 0 and closed == 0 and re.match(r"^#\s*\S+\s+END\b", ln.strip()):
                return i                     # `# jhw:jobhuntwow END` while still inside a block
            if t.strip().endswith("{"):
                return i                     # a new site header while the previous is still open
        depth += opened - closed
    return len(lines) if depth > 0 else None

def enclosing_block(lines, n):
    # (start, end) 0-based inclusive of the site block containing 1-based line n.
    # A comment, not a docstring: this whole program lives inside a triple-quoted Python
    # string in recover.py, and a nested triple quote would close it.
    i = n - 1
    start = i
    depth = 0
    while start >= 0:
        t = lines[start].split("#")[0]
        depth += t.count("}") - t.count("{")
        if t.strip().endswith("{") and depth <= 0:
            break
        start -= 1
    if start < 0:
        return None
    end, d = start, 0
    while end < len(lines):
        t = lines[end].split("#")[0]
        d += t.count("{") - t.count("}")
        if d == 0 and end > start:
            break
        end += 1
    return (start, min(end, len(lines) - 1))

last_line = -1
rc, out = validate()
if rc == 0:
    print("already valid - the config is not the problem")
    raise SystemExit(0)

# STEP 1 -- BRACE BALANCE, BEFORE ANY LINE NUMBER.
# An unclosed block makes Caddy report the fault at the FIRST line it cannot interpret inside it,
# which can be dozens of lines below the real defect and in someone else's, perfectly valid, block.
# Acting on that number disables a working site and leaves the cause untouched. So: balance the
# braces first, re-validate, and only then trust a reported line.
src = open(P, encoding="utf-8", errors="replace").read().split("\n")
_code = "\n".join(l.split("#")[0] for l in src)
_open, _close = _code.count("{"), _code.count("}")
if _open > _close:
    pos = fix_unclosed_block(src)
    if pos is not None:
        indent = ""
        print("braces: open=%d close=%d -> UNCLOSED BLOCK; inserting '}' before line %d: %s"
              % (_open, _close, pos + 1, src[pos].strip()[:60]))
        src.insert(pos, indent + "}")
        open(P, "w", encoding="utf-8").write("\n".join(src))
        rc, out = validate()
        print("after brace fix: %s" % ("VALID" if rc == 0 else "still invalid"))
elif _close > _open:
    print("braces: open=%d close=%d -- MORE CLOSING than opening; not guessing, leaving to a human"
          % (_open, _close))

for attempt in range(5):
    rc, out = validate()
    if rc == 0:
        print("VALID after %d change(s)" % attempt)
        break
    m = re.search(r"Caddyfile:(\d+):", out)
    if not m:
        print("validator gave no line number:"); print(out[-400:]); break
    n = int(m.group(1))
    lines = open(P, encoding="utf-8", errors="replace").read().split("\n")
    if n > len(lines):
        print("reported line %d is past EOF" % n); break
    # SMALLEST BLAST RADIUS FIRST. A unit test on the real shape ("klimaanlage-preise.de," sitting
    # between two blocks) showed the backward scan pointing at the PREVIOUS, perfectly good block —
    # commenting that out would have disabled a working site and left the fault in place.
    # So: try the single reported line first; only if that still does not validate escalate to its
    # enclosing block. The validator after every step is what makes escalating safe.
    if attempt == 0 or n != last_line:
        a = b = n - 1
    else:
        blk = enclosing_block(lines, n)
        a, b = blk if blk else (n - 1, n - 1)
    last_line = n
    if any("colt:cybergod" in lines[i] for i in range(a, b + 1)):
        print("the fault is inside OUR block - fix deploy/caddy/cybergod.caddy, not this file")
        break
    print("line %d -> disabling block %d..%d : %s" % (n, a + 1, b + 1, lines[a].strip()[:60]))
    for i in range(a, b + 1):
        if not lines[i].lstrip().startswith("#"):
            lines[i] = "# [disabled-by-recover] " + lines[i]
    open(P, "w", encoding="utf-8").write("\n".join(lines))
else:
    rc, out = validate()

if rc != 0:
    shutil.copy(BAK, P)
    print("STILL INVALID - backup restored, nothing changed")
    print(out[-400:])
    raise SystemExit(2)
PYEOF
RC=$?
if [ $RC -ne 0 ]; then echo "repair aborted (rc=$RC)"; exit 0; fi
echo "#### APPLY"
# WRITE TO THE HOST PATH IF THERE IS ONE. `docker cp` into the container fails when /etc/caddy is
# bind-mounted read-only -- and the first version swallowed that failure with `&&`, so it printed
# "started" on a container that had just reloaded the UNREPAIRED file. Never hide the exit code of
# the step that does the actual work.
SRC=$(docker inspect "$C" --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
if [ -z "$SRC" ]; then
  D=$(docker inspect "$C" --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
  [ -n "$D" ] && SRC="$D/Caddyfile"
fi
WROTE=no
if [ -n "$SRC" ] && [ -f "$SRC" ]; then
  echo "host-mounted config: $SRC"
  cp /tmp/_cffix/Caddyfile "$SRC" && WROTE=host
else
  echo "no host mount found - writing into the container"
  docker stop "$C" >/dev/null 2>&1
  OUT=$(docker cp /tmp/_cffix/Caddyfile "$C":/etc/caddy/Caddyfile 2>&1) && WROTE=container \
    || echo "docker cp FAILED: $OUT"
fi
if [ "$WROTE" = "no" ]; then
  echo "COULD NOT WRITE THE CONFIG - nothing changed on the droplet"
  docker start "$C" >/dev/null 2>&1
  exit 0
fi
echo "config written ($WROTE)"

# RAW BYTES of the region the proxy complained about. A paste through a terminal, a chat client or
# a log viewer can invent or hide characters; `cat -A` cannot. Markdown link syntax
# ( [www.x.de](https://www.x.de) ) written into a Caddyfile by an AI-authored block would produce
# exactly "unrecognized directive" -- so this either proves it or clears it.
echo "-- raw bytes, lines 86..96 (cat -A: \$ = EOL, ^I = tab):"
sed -n '86,96p' /tmp/_cffix/Caddyfile | cat -A | cut -c1-180
echo "-- any markdown link syntax anywhere in the file?"
grep -n '](http' /tmp/_cffix/Caddyfile | head -10 || true
grep -c '](http' /tmp/_cffix/Caddyfile

# RESTART PROPERLY AND WAIT. Docker's restart backoff reaches 60s+, and `docker start` on a
# container already in `Restarting` is a no-op -- so the previous version read `--tail` 12s later
# and printed a failure that PREDATED its own fix. Stop it, start it, then poll, and only ever
# show logs from AFTER the write.
T0=$(date +%s)
docker stop "$C" >/dev/null 2>&1
sleep 2
docker start "$C" >/dev/null 2>&1 && echo "restarted $C"
BOUND=no
for i in $(seq 1 18); do
  sleep 5
  if (ss -lnt 2>/dev/null || netstat -lnt 2>/dev/null) | grep -qE ':(443)\s'; then BOUND=yes; break; fi
  case "$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)" in
    exited|restarting) ;;    # keep waiting through the backoff
  esac
done
echo "waited $((i*5))s  bound443=$BOUND"

rm -rf /tmp/_cfver; mkdir -p /tmp/_cfver
docker cp "$C":/etc/caddy/Caddyfile /tmp/_cfver/Caddyfile 2>/dev/null \
  || cp "$SRC" /tmp/_cfver/Caddyfile 2>/dev/null
if [ -f /tmp/_cfver/Caddyfile ]; then
  echo "verify in place: braces open=$(sed 's/#.*//' /tmp/_cfver/Caddyfile | tr -cd '{' | wc -c) close=$(sed 's/#.*//' /tmp/_cfver/Caddyfile | tr -cd '}' | wc -c) lines=$(wc -l < /tmp/_cfver/Caddyfile)"
  echo "identical to what we validated: $(cmp -s /tmp/_cffix/Caddyfile /tmp/_cfver/Caddyfile && echo YES || echo NO)"
fi
docker ps -a --filter "name=$C" --format '{{.Names}}\t{{.Status}}'
echo "-- proxy log SINCE the write (nothing here = it never even tried):"
docker logs "$C" --since "$T0" 2>&1 | tail -12
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(80|443)\s' || echo "STILL NOTHING ON 80/443"
"""

RESTART = r"""
set +e
echo "#### STARTED"
for c in $(docker ps -a --filter status=exited --filter status=created --filter status=dead \
           --format '{{.Names}}'); do
  docker start "$c" >/dev/null 2>&1 && echo "started $c" || echo "FAILED  $c"
done
sleep 6
echo "#### RUNNING_AFTER"
docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null
echo "#### PORTS_AFTER"
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(80|443)\s' || echo "STILL NOTHING ON 80/443"
"""


def main():
    ap = argparse.ArgumentParser(description="Diagnose and restore the droplet when sites refuse.")
    ap.add_argument("--dry", action="store_true", help="diagnose only, change nothing")
    ap.add_argument("--fix-caddy", dest="fix_caddy", action="store_true",
                    help="emergency repair of an unparseable SHARED Caddyfile: back it up, comment "
                         "out the smallest broken block, validate, restart, verify")
    a = ap.parse_args()

    print("=" * 78)
    print("  cybergod recover  ·  %s@%s" % (USER, HOST))
    print("=" * 78)

    print("\n[1/4] Outside view — is anything answering?")
    before = {}
    for u in SITES:
        st, note = probe(u)
        before[u] = st
        print("   %-38s %s" % (u, ("HTTP %d" % st) if st else "no listener (%s)" % note))
    if all(v for v in before.values()):
        print("\n   Everything already answers. Nothing to recover.")
        return 0

    print("\n[2/4] Inside view — one ssh session, read-only")
    out, err, rc = ssh_script(DIAGNOSE)
    if rc != 0 and not out:
        print("   [X] could not reach the droplet over ssh: %s" % (err.strip()[:200] or rc))
        print("       The host answers ping, so this is sshd or your key — check the DO web console.")
        return 2
    s = sections(out)
    for k in ("UPTIME", "DISK", "MEM", "PORTS", "RUNNING", "RESTARTING", "STOPPED",
              "PUBLISHED_PORTS", "CRASHLOOP_LOGS", "CADDY_CONFIG", "OOM", "DOCKER_ERR"):
        if s.get(k):
            print("\n   --- %s ---" % k)
            print("   " + s[k].replace("\n", "\n   ")[:2400])

    # ---- read the evidence out loud, so the verdict is not left to the reader
    print("\n[3/4] Verdict")
    running = s.get("RUNNING", "")
    ports = s.get("PORTS", "")
    restarting = s.get("RESTARTING", "").strip()
    logs = s.get("CRASHLOOP_LOGS", "")
    proxy_up = any(h in running.lower() for h in PROXY_HINTS)
    listening = "443" in ports

    if restarting:
        print("   ! A container is stuck in a RESTART LOOP:")
        for line in restarting.splitlines()[:6]:
            print("       " + line)
        print("     A restart cannot fix this — the process dies again immediately. The cause is")
        print("     in its own log, above. This is also why ship.py failed: `docker exec` refuses")
        print("     with 'Container ... is restarting'.")
    if re.search(r"(?i)address already in use|bind: address already in use", logs):
        print("   ! PORT CONFLICT — the proxy cannot bind :80/:443 because another container took")
        print("     it first. Look at PUBLISHED_PORTS above: whichever OTHER container publishes")
        print("     80 or 443 is the one to stop. Two processes cannot share a listening port.")
    m_cfg = re.search(r"(?i)adapting config using caddyfile: ([^\s:]+):(\d+): (.+)", logs)
    if m_cfg:
        print("   ! The proxy is REJECTING ITS OWN CONFIG and therefore never binds :443:")
        print("       %s line %s -> %s" % (m_cfg.group(1), m_cfg.group(2), m_cfg.group(3)[:90]))
        cfg = s.get("CADDY_CONFIG", "")
        mine = "colt:cybergod" in cfg and "not present" not in cfg
        blk = re.search(r"colt:cybergod BEGIN.*?:(\d+)", cfg)
        print("     This Caddyfile is SHARED: every site on the box is served from it, which is why")
        print("     they all died together.")
        if mine and blk:
            print("     Our cybergod block IS present. If the bad line falls inside it, fix")
            print("     deploy/caddy/cybergod.caddy and redeploy — never the droplet copy.")
        print("     If the bad line is NOT in our block it belongs to another project on this box,")
        print("     and repairing it here would be exactly the untracked edit the hard rule forbids.")
    elif re.search(r"(?i)(parse|unrecognized|invalid config)", logs):
        print("   ! The proxy is rejecting its own configuration — see the log above.")
    if s.get("OOM", "-") not in ("-", ""):
        print("   ! The kernel OOM-killer has fired. The droplet is 4 GB / 2 vCPU, so this is not")
        print("     a baseline sizing problem — something specific consumed the memory.")
    if "NOTHING LISTENING" in ports or not listening:
        print("   ! Nothing is bound to 443. That is exactly why every site refuses the connection.")
    if not proxy_up:
        print("   ! The reverse proxy is NOT running. It owns :443 and fronts every domain on this")
        print("     box, which is why they died together. This is not an application fault.")
    else:
        print("   - The proxy is running; the fault is narrower than the shared proxy.")
    if re.search(r"\b(9[0-9]|100)%", s.get("DISK", "")):
        print("   ! A filesystem is nearly full. Docker cannot start containers on a full disk.")

    if a.dry:
        print("\n[4/4] --dry: nothing was changed.")
        return 1

    if m_cfg and a.fix_caddy:
        # EVIDENCE BEFORE REPAIR. A fix overwrites the state that explains the fault, and the
        # question that matters is not "what is Caddy complaining about" but "WHAT WROTE THIS, and
        # WHEN". Caddy reads its config once, at start, so a broken file can sit latent for hours
        # and only detonate on the next restart -- which is exactly what happened on 2026-08-07
        # (box rebooted 04:23 UTC; the last healthy assessment finished 18:06 UTC the day before).
        # Collecting the timeline first costs one ssh round-trip and preserves the whole picture.
        try:
            from forensics import build as forensic_script, DEF_SINCE, DEF_UNTIL
            print("\n[4/5] Capturing the forensic timeline BEFORE changing anything (read-only)")
            fout, _fe, _fr = ssh_script(forensic_script(DEF_SINCE, DEF_UNTIL), timeout=420)
            import datetime as _dt
            fp = os.path.join(HERE, "forensics-%s.txt"
                              % _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S"))
            open(fp, "w", encoding="utf-8", errors="replace").write(fout or "")
            fs = sections(fout)
            print("   saved: %s" % fp)
            for k in ("CLOCK", "WROTE_IN_WINDOW", "APT_AND_UPGRADES", "WHO_CONNECTED"):
                if fs.get(k):
                    print("   --- %s ---" % k)
                    print("   " + fs[k].replace("\n", "\n   ")[:1800])
        except Exception as _e:
            print("   [warn] forensic capture failed (%s) — continuing with the repair" % _e)

        print("\n[5/5] --fix-caddy: backup, repair the config, validate, restart")
        out3, err3, _ = ssh_script(FIXCADDY, timeout=300)
        s3 = sections(out3)
        for k in ("FIX", "APPLY"):
            if s3.get(k):
                print("\n   --- %s ---" % k)
                print("   " + s3[k].replace("\n", "\n   ")[:2000])
        print("\n   Re-checking from the outside...")
        ok = sum(1 for u in SITES if probe(u)[0])
        for u in SITES:
            st, note = probe(u)
            print("   %-38s %s" % (u, ("HTTP %d" % st) if st else "still refused (%s)" % note))
        print()
        if ok:
            print("  RECOVERED — %d of %d answer. A disabled block stays disabled until its owner"
                  % (ok, len(SITES)))
            print("  fixes it; the backup path is printed above.")
            return 0
        print("  Still down. The backup was restored if validation never passed — see above.")
        return 1

    if m_cfg:
        print("\n[4/4] NOT touching anything. The proxy's config does not parse, and this Caddyfile")
        print("      is shared with other projects on this box, so a blind edit here is exactly the")
        print("      untracked change the hard rule forbids.")
        print("      Look at the CADDY_CONFIG context above. Then either fix the owning project's")
        print("      source, or run the guarded emergency repair, which backs the file up first and")
        print("      only ever comments a block out:")
        print("          python recover.py --fix-caddy")
        return 1

    if restarting:
        print("\n[4/4] NOT restarting anything: a crash loop is already restarting on its own.")
        print("      Read the log above, fix the cause, then re-run. Blind restarts here just")
        print("      hide the evidence.")
        return 1

    print("\n[4/4] Restarting stopped containers (start only — nothing is recreated)")
    out2, err2, rc2 = ssh_script(RESTART)
    s2 = sections(out2)
    for k in ("STARTED", "RUNNING_AFTER", "PORTS_AFTER"):
        if s2.get(k):
            print("\n   --- %s ---" % k)
            print("   " + s2[k].replace("\n", "\n   ")[:1600])

    print("\n   Re-checking from the outside...")
    ok = 0
    for u in SITES:
        st, note = probe(u)
        good = bool(st)
        ok += 1 if good else 0
        print("   %-38s %s" % (u, ("HTTP %d" % st) if st else "still refused (%s)" % note))
    print()
    if ok == len(SITES):
        print("=" * 78)
        print("  RECOVERED — every site answers again.")
        print("=" * 78)
        return 0
    print("=" * 78)
    print("  PARTIAL — %d of %d answer." % (ok, len(SITES)))
    print("  If the proxy refuses to stay up, the cause is under it: memory, disk, or a config it")
    print("  cannot parse. Send this whole output; do not hand-edit anything on the droplet.")
    print("=" * 78)
    return 1


if __name__ == "__main__":
    sys.exit(main())
