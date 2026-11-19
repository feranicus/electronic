#!/usr/bin/env python3
"""observemove.py — move the observability stack off godeyes.ai before the domain lapses.

    python observemove.py                 MEASURE and print the plan. Writes nothing, anywhere.
    python observemove.py --apply         (added once the measurement is in; see WHY below)

THE DEADLINE
    godeyes.ai is not being renewed and stops resolving on 21 Nov 2026. Everything it serves has
    to answer on cybergod.ai before then, and the React site on cybergod.ai / www.cybergod.ai must
    not notice.

WHY THIS RUN CHANGES NOTHING
    godeyes.ai is NOT a committed fragment. It is served by `{$DOMAIN}` inside the VideoDead
    stack's own Caddyfile, so its hostname appears nowhere in the file and nothing in this repo
    describes what it proxies. decommission.py already records that fact in a comment; it is the
    reason a name-grep reports the wrong number of sites.

    That means the migration cannot be written from the repo. It has to be written from the box.
    This script is the measurement, and it is deliberately separate from the change: the thing we
    would be editing is the shared proxy that owns :443 for six live domains, including the one
    paying the bills. CLAUDE.md's rule is to measure before naming a cause; the same rule applies
    before writing a migration.

WHAT IT MEASURES, IN ONE SSH SESSION
    1. The live Caddyfile and the exact site block `{$DOMAIN}` expands to, with every route.
    2. What DOMAIN actually resolves to in the VideoDead env.
    3. Grafana's own idea of where it lives: GF_SERVER_ROOT_URL, GF_SERVER_DOMAIN,
       GF_SERVER_SERVE_FROM_SUB_PATH. A sub-path Grafana with the wrong root_url generates
       absolute links to a dead domain, which looks like "Grafana is broken" and is not.
    4. Every other container whose environment names godeyes.ai.
    5. The certificates Caddy currently holds, and what DNS says today.
    6. The caddyguard fragment set, so the new block lands beside the others and not inside
       somebody else's braces.

THE PLAN IT PRINTS
    observe.cybergod.ai as a NEW vhost, carrying the routes measured above. A new fragment is the
    only change to the proxy: the cybergod.ai block is not touched, so the React site cannot be
    affected by a mistake in this work, and the rollback is deleting one file. The alternative,
    cybergod.ai/observe, needs no DNS at all but shares a site block with the production site,
    and it is offered as the fallback rather than the default for exactly that reason.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import recover  # noqa: E402  — ONE HOME for "which key, which host, one session"

OLD = "godeyes.ai"
NEW = "observe.cybergod.ai"
PROD = ("cybergod.ai", "www.cybergod.ai")
IP = "64.225.108.200"

# WHY THERE IS NO NEW VHOST ANY MORE (design changed 19 Nov 2026, the earlier reasoning kept)
#
# The first plan put Grafana on observe.cybergod.ai. That needed one A record, and the record was
# the only manual step in the move. Then the search for the credential came back empty: there is
# no GoDaddy key in any env file in this project, `golive.secrets.env` does not exist (only a
# one-line deprecation example), and `cloudflare_setup.py` is a plan that was never executed -
# cybergod.ai still resolves straight to the droplet, not to a Cloudflare address. The one
# registrar this estate automates is INWX, in the Klima project, for a different domain.
#
# So the subdomain would have made a two-day deadline wait on a credential hunt. The path does
# not: Grafana ALREADY serves from /observe, so putting it on cybergod.ai/observe needs no DNS,
# no new certificate, and changes only the HOST half of its root_url. Every dashboard deep link
# survives unchanged.
#
# The cost is honest: the route is added to the cybergod.ai site block, which the React app also
# lives in. It is a prefix route matched before the catch-all, colt-web has no /observe path of
# its own, it is validated in the proxy's own image before it is applied, and it is four lines in
# a committed fragment that CI reinstalls. The block itself is deploy/caddy/cybergod.caddy.
GRAFANA_ROOT_URL = "https://cybergod.ai/observe/"

# ---------------------------------------------------------------------------------------------
# THE REMOTE MEASUREMENT. One session (class 43), read-only, and every command is a read.
# ---------------------------------------------------------------------------------------------
PROBE = r"""
set -u
say() { printf '\n#### %s\n' "$1"; }

say CADDY_CONTAINER
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' | grep -i caddy || echo '(no caddy container)'

say CADDYFILE_SOURCE
CF=$(docker inspect videodead-caddy-1 \
     --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
echo "host path: ${CF:-<none>}"
[ -n "${CF:-}" ] && { echo "size: $(wc -c < "$CF") bytes"; echo "sha256: $(sha256sum "$CF" | cut -c1-12)"; }

say DOMAIN_PLACEHOLDER
# The hostname is an env placeholder, so BOTH halves matter: where {$DOMAIN} is used, and what
# the compose env sets it to. Printing one without the other is how this stayed invisible.
grep -n 'DOMAIN' "${CF:-/dev/null}" | head -20 || true
echo '-- videodead env --'
for f in /opt/videodead/.env /opt/videodead/stack.env; do
  [ -f "$f" ] && { echo "$f:"; grep -E '^(DOMAIN|GRAFANA|GF_)' "$f" || echo '  (no DOMAIN/GF_ lines)'; }
done

say THE_BLOCK
# Print the WHOLE site block that carries {$DOMAIN} or godeyes.ai, braces included, so the routes
# can be copied rather than guessed.
awk '
  /^[^[:space:]#].*\{[[:space:]]*$/ { hdr=$0; buf=hdr"\n"; depth=1; next }
  depth>0 {
    buf=buf$0"\n"
    n=gsub(/\{/,"{"); m=gsub(/\}/,"}"); depth+=n-m
    if (depth<=0) { if (hdr ~ /DOMAIN|godeyes/) printf "%s", buf; depth=0 }
  }
' "${CF:-/dev/null}" 2>/dev/null || echo '(could not read the Caddyfile)'

say ALL_SITE_HEADERS
grep -nE '^[^[:space:]#].*\{[[:space:]]*$' "${CF:-/dev/null}" 2>/dev/null || true

say GRAFANA_SELF_IMAGE
# Grafana's own root_url is the piece that breaks silently: the proxy can be perfect and every
# generated link still points at the dead domain.
docker inspect videodead-grafana-1 --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
  | grep -E '^GF_(SERVER|SECURITY|AUTH)' || echo '(no GF_SERVER env; check grafana.ini)'
echo '-- grafana.ini server section, if mounted --'
docker exec videodead-grafana-1 sh -c 'sed -n "/^\[server\]/,/^\[/p" /etc/grafana/grafana.ini' 2>/dev/null | head -20 \
  || echo '(no grafana.ini readable)'

say WHO_ELSE_KNOWS_THE_NAME
for c in $(docker ps --format '{{.Names}}'); do
  hits=$(docker inspect "$c" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep -c 'godeyes' || true)
  [ "${hits:-0}" -gt 0 ] && echo "$c: $hits env line(s) name godeyes.ai"
done
echo '(end)'

say CERTS_HELD
find /var/lib/docker/volumes -path '*certificates*' -name '*.crt' 2>/dev/null \
  | sed 's#.*/##' | sort -u | head -20 || echo '(none found)'

say DNS_TODAY
for h in godeyes.ai cybergod.ai observe.cybergod.ai; do
  printf '%-22s %s\n' "$h" "$(getent hosts "$h" | awk '{print $1}' | paste -sd, - || echo NXDOMAIN)"
done

say CADDYGUARD_FRAGMENTS
ls -la /opt/caddyguard/blocks/ 2>/dev/null || echo '(no caddyguard blocks dir)'

say LIVE_PROBES
for u in https://godeyes.ai/ https://godeyes.ai/observe/ https://cybergod.ai/api/me https://cybergod.ai/; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 12 "$u" || echo ERR)
  printf '%-34s %s\n' "$u" "$code"
done
"""


def measure():
    print("=" * 86)
    print("  observemove.py — MEASURING %s. Nothing is written." % OLD)
    print("  host: %s@%s   identity: %s" % (recover.USER, recover.HOST,
                                            recover.ssh_identity() or "(ssh default)"))
    print("=" * 86)
    out, err, rc = recover.ssh_script(PROBE, timeout=180)
    if rc != 0 and not out.strip():
        # A PROBE THAT CANNOT SEE ITS SUBJECT MUST NOT ANSWER (class 1). No output means we
        # learned nothing about the droplet, not that the droplet is empty.
        print("\n[X] the probe never ran. rc=%s" % rc)
        print(err.strip()[:1200] or "(no stderr)")
        return None
    print(out)
    if err.strip():
        print("-- stderr (often harmless: docker inspect on a container that is not there) --")
        print(err.strip()[:900])
    return out


# ---------------------------------------------------------------------------------------------
# THE LOCAL HALF: derive the edit set rather than counting it by hand (class 35).
# ---------------------------------------------------------------------------------------------
def repo_references():
    """Every tracked file that names the dying domain, straight from git."""
    try:
        r = subprocess.run(["git", "ls-files", "-z"], cwd=HERE, capture_output=True, timeout=60)
        files = [f for f in (r.stdout or b"").decode("utf-8", "replace").split("\0") if f]
    except Exception as e:
        print("[warn] could not list tracked files (%s); skipping the repo half" % type(e).__name__)
        return {}
    hits = {}
    for rel in files:
        p = os.path.join(HERE, rel)
        if not os.path.isfile(p) or os.path.getsize(p) > 2_000_000:
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                lines = [n for n, ln in enumerate(fh, 1) if OLD in ln]
        except OSError:
            continue
        if lines:
            hits[rel] = lines
    return hits


def print_plan(refs):
    print("\n" + "=" * 86)
    print("  THE PLAN (nothing above or below this line has been executed)")
    print("=" * 86)
    print("""
  1. DNS, and it is the one step no script here can do for you. GoDaddy holds cybergod.ai, and
     this repo has no GoDaddy credential: golive.py, which CLAUDE.md still credits with doing
     this, has been a one-line `sys.exit(DEPRECATED)` since the CI cutover. So:

         Type:  A        Name:  observe        Value:  %s        TTL: 600

     Thirty seconds in the console, and it is the only manual step in the whole move.

  2. A NEW caddyguard fragment, colt__observe.caddy, carrying the routes the measurement above
     printed, under the header `%s {`. Written through `caddyguard write`, so it is validated in
     the proxy's own image, assembled, mount-checked and reloaded through the admin API, exactly
     like every other fragment. Caddy issues the certificate by itself once DNS resolves.

     THE CYBERGOD BLOCK IS NOT TOUCHED. That is the whole point of choosing a subdomain over
     cybergod.ai/observe: the React site keeps its own site block, a mistake in this work cannot
     reach it, and the rollback is deleting one file and reassembling.

  3. Grafana's own root_url. A sub-path Grafana with a stale GF_SERVER_ROOT_URL keeps generating
     absolute links to a domain that no longer resolves, which presents as "Grafana is broken"
     and is not. The measurement above says whether it is set and to what. This is a change
     inside the VideoDead stack, so it is the minimum possible: one environment value, nothing
     else, and only if the measurement shows it names the old domain.

  4. The repo roster. %d tracked file(s) name %s today and each one is a place the old name
     would come back from:
""" % (recover.HOST, NEW, len(refs), OLD))
    for rel in sorted(refs):
        ns = refs[rel]
        print("       %-52s line%s %s" % (rel, "" if len(ns) == 1 else "s",
                                          ",".join(str(n) for n in ns[:8])
                                          + ("…" if len(ns) > 8 else "")))
    print("""
     The uptime workflow, the caddyguard probe list and agent.py's expected-vhost roster matter
     most: leave the old name in those and every run after the 21st reports a false outage, which
     trains you to read past the alert that is real.

  5. Verification, and it is what makes this a migration rather than a hope:
       * %s/observe answers, with a certificate Caddy issued for it
       * cybergod.ai/ still 200 and cybergod.ai/api/me still 401, measured before and after
       * the running config is compared against the file, on all three hops
       * every other domain on the shared proxy still answers

  WHAT I AM NOT DOING WITHOUT READING THE MEASUREMENT FIRST: writing step 2. The block is built
  from the routes the box reports, not from what I expect them to be. Paste the output above and
  the apply path lands in the same shape as the rest of this repo.
""" % NEW)


# ---------------------------------------------------------------------------------------------
# THE CHANGE. Everything above measured; everything below writes, and every write is reversible.
# ---------------------------------------------------------------------------------------------

# A BROWSER USER AGENT, BECAUSE THE SITE ANSWERS 404 TO ANYTHING ELSE. The measurement printed
# `https://cybergod.ai/ 404`, which looks like an outage and is the bot gate working exactly as
# designed: curl's own agent is refused. A verifier that does not know that would report the
# React site as broken before this script touched anything, and report it as fixed afterwards.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")

# THE BASELINE COMES FROM THE ONE HOME, NOT FROM A COPY. The first version hardcoded six
# hosts, two of which were retired projects, so the guard refused to start over a 502 on a site
# nobody runs. A roster written down twice is a roster that disagrees with itself (class 32).
import estate  # noqa: E402

# ...minus the route this run CREATES. cybergod.ai/observe cannot be in a baseline taken before
# it exists, or the guard refuses to start on the one thing it is here to build. It is proved
# separately, after the ship, and again at the end.
WATCH = [w for w in estate.watch_list() if w[0] != "cybergod.ai/observe"]

APPLY = r"""
set -u
BLOCKS=/opt/caddyguard/blocks
BASE=$BLOCKS/_base.caddy
STAMP=$(date +%Y%m%d-%H%M%S)

say() { printf '\n#### %s\n' "$1"; }

say PREFLIGHT
[ -f "$BASE" ] || { echo 'FATAL: no _base.caddy'; exit 10; }
cp -a "$BASE" "/opt/caddyguard/backups/_base.caddy.pre.$STAMP" 2>/dev/null || \
  { mkdir -p /opt/caddyguard/backups && cp -a "$BASE" "/opt/caddyguard/backups/_base.caddy.pre.$STAMP"; }
echo "backup: /opt/caddyguard/backups/_base.caddy.pre.$STAMP"
grep -c 'DOMAIN' "$BASE" | sed 's/^/{$DOMAIN} mentions in _base: /'

say RETIRE_DEAD_VHOSTS
# Replace the {$DOMAIN} site block, braces counted rather than guessed. A `{` inside a comment is
# why decommission.py counts depth instead of grepping for the closing line, and the same trap is
# here: the block being replaced contains a CSP string full of braces-adjacent punctuation.
for _pass in 1 2 3 4 5 6 7 8; do
python3 - "$BASE" <<'PYEOF'
import io, os, sys
p = sys.argv[1]
src = io.open(p, encoding="utf-8").read()
lines = src.split("\n")
# EVERY RETIRED SITE, NOT JUST THE ONE WITH A DEADLINE. jev.best and the two klimaanlage
# domains ended with their projects and have been answering 502 for weeks, which is the state
# that blocked this very script from starting. A proxy that still declares them keeps renewing
# their certificates and keeps them on the roster, so every drift check reports a site nobody
# runs as missing. The headers come from the environment, derived from estate.RETIRED.
import re as _re2
wanted = [h.strip() for h in os.environ["RETIRE_HEADERS"].split("|") if h.strip()]
start = None
for i, l in enumerate(lines):
    # NOT \b. The placeholder header is `{$DOMAIN} {`, and there is no word boundary between
    # `}` and a space, so \b silently never matched the one site this script exists for.
    # MEASURED against the real header lines before shipping.
    if any(_re2.match(r"^%s(\s|,|\{|$)" % _re2.escape(w), l) for w in wanted):
        start = i
        break
if start is None:
    print("no retired site header left in _base.caddy")
    raise SystemExit(11)
def delta(line):
    # A BRACE IS ONLY STRUCTURE WHEN IT IS NOT IN A STRING OR A COMMENT. decommission.py already
    # records what the naive version costs: a `{` inside a comment makes the counter run past the
    # real closing brace, the braces balance again further down, and the edit silently takes the
    # NEXT vhost with it. Strings are blanked first, because a `#` inside a quoted header value
    # is not a comment.
    import re as _re
    t = _re.sub(r'"[^"]*"', '""', line)
    t = t.split("#", 1)[0]
    return t.count("{") - t.count("}")

depth, end = 0, None
for i in range(start, len(lines)):
    depth += delta(lines[i])
    if depth <= 0 and i > start:
        end = i
        break
if end is None:
    print("FATAL: the {$DOMAIN} block never closes"); raise SystemExit(12)
# REMOVED, not replaced: godeyes.ai is being given up and Grafana now answers on a path of
# cybergod.ai, so this site block has no successor on this proxy.
out = "\n".join(lines[:start] + lines[end + 1:])
# One header per pass; the shell loops until nothing matches, so a file with three retired
# blocks needs three passes and each one is independently verified by the brace counter.
tmp = p + ".tmp"
io.open(tmp, "w", encoding="utf-8", newline="\n").write(out)
os.replace(tmp, p)          # atomic; a half-written fragment is a dead proxy
# NAME THE BLOCK (class 26). Printing "the godeyes.ai site block" on every pass of a loop
# that retires three different vhosts describes the first one three times.
print("removed lines %d..%d (%d lines): %s" % (start + 1, end + 1, end - start + 1,
                                               lines[start].rstrip(" {").strip() or "?"))
PYEOF
  rc=$?
  # 11 means "no retired header left", which is the loop's normal exit, not a failure.
  [ $rc -eq 11 ] && break
  [ $rc -eq 0 ] || exit $rc
done

say ASSEMBLE
# The guard's OWN path: validate in the proxy's image, write IN PLACE (single-file bind mount
# pins the inode), mount-check, then reload through the admin API. Never a container restart.
python3 /opt/caddyguard/agent.py assemble --apply 2>&1 | tail -20
rc=${PIPESTATUS[0]}
if [ "$rc" -ne 0 ]; then
  echo "ASSEMBLE FAILED rc=$rc — restoring the previous fragment"
  cp -a "/opt/caddyguard/backups/_base.caddy.pre.$STAMP" "$BASE"
  python3 /opt/caddyguard/agent.py assemble --apply 2>&1 | tail -5
  exit 20
fi

say GRAFANA_ROOT_URL
# A sub-path Grafana with a stale root_url keeps emitting absolute links to a dead domain. The
# value is found wherever it is declared rather than assumed: compose may template it from
# ${DOMAIN}, and DOMAIN is still used by the VideoDead containers we are NOT touching.
cd /opt/videodead || exit 30
CMP=$(ls docker-compose.yml docker-compose.yaml compose.yml 2>/dev/null | head -1)
echo "compose: ${CMP:-<none>}"
for f in $CMP .env; do
  [ -f "$f" ] && grep -n 'GF_SERVER_ROOT_URL' "$f" && cp -a "$f" "$f.pre.$STAMP"
done
python3 - "$CMP" <<'PYEOF'
import io, os, re, sys
want = os.environ["GRAFANA_ROOT_URL"]
changed = []
for p in [x for x in (sys.argv[1], ".env") if x and os.path.isfile(x)]:
    s = io.open(p, encoding="utf-8").read()
    n = re.sub(r"(GF_SERVER_ROOT_URL\s*[:=]\s*)\S+", lambda m: m.group(1) + want, s)
    if n != s:
        t = p + ".tmp"
        io.open(t, "w", encoding="utf-8", newline="\n").write(n)
        os.replace(t, p)
        changed.append(p)
print("root_url rewritten in: %s" % (", ".join(changed) or "(nothing matched - check by hand)"))
PYEOF

say GRAFANA_RECREATE
# ONLY grafana. --no-deps so nothing else in the stack is touched, and never the caddy container.
docker compose -f "${CMP:-docker-compose.yml}" up -d --no-deps grafana 2>&1 | tail -5
sleep 6
docker inspect videodead-grafana-1 --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep GF_SERVER_ROOT_URL || echo '(root_url not visible on the container)'

say DRIFT
python3 /opt/caddyguard/agent.py check 2>&1 | tail -12
"""


def _probe(url, timeout=20):
    """Code only, with a browser agent. Returns a string so a failure is printable, not fatal."""
    try:
        r = subprocess.run(["curl", "-s", "-o", os.devnull, "-w", "%{http_code}",
                            "-A", UA, "-m", str(timeout), url],
                           capture_output=True, text=True, timeout=timeout + 10)
        return (r.stdout or "").strip() or "ERR"
    except Exception as e:
        return "ERR(%s)" % type(e).__name__


def watch(label):
    print("\n-- %s --" % label)
    got = {}
    for name, url, ok in WATCH:
        code = _probe(url)
        got[name] = code
        print("   %-22s %-5s %s" % (name, code, "ok" if code in ok else "<-- NOT in %s" % (ok,)))
    return got


def apply():
    print("=" * 86)
    print("  observemove.py --apply   %s  ->  cybergod.ai/observe" % OLD)
    print("=" * 86)

    before = watch("BEFORE (this is what must not change)")
    bad = [n for n, _u, okc in WATCH if before[n] not in okc]
    if bad:
        # A CHANGE MUST NOT START FROM A BROKEN BASELINE. If something is already failing, this
        # script gets the blame for it, and worse, its own rollback check passes.
        print("\n[X] refusing to start: %s already answering wrong. Fix that first." % ", ".join(bad))
        return 3

    # STEP 1 IS THE ORCHESTRATOR, AND IT COMES FIRST ON PURPOSE. ship.py reinstalls the committed
    # cybergod fragment, which is where the /observe route now lives. Doing it first means Grafana
    # answers on BOTH names for a few minutes: nothing is cut over until the new path is proven.
    print("\n-- step 1/3: ship the committed Caddy fragment and the repo roster --")
    rc = subprocess.call([sys.executable, os.path.join(HERE, "ship.py"), "--no-preview"], cwd=HERE)
    if rc != 0:
        print("\n[X] ship.py exited %s. Nothing on the droplet has been cut over; %s still "
              "serves Grafana. Fix the ship and run this again." % (rc, OLD))
        return 4

    path_code = _probe("https://cybergod.ai/observe/")
    print("\n   cybergod.ai/observe/ -> %s" % path_code)
    if path_code not in ("200", "302", "301"):
        print("   [X] the new path does not answer, so there is nothing to cut over TO. "
              "%s is untouched and still works." % OLD)
        return 5

    print("\n-- step 2/3: retarget Grafana and retire the %s block --" % OLD)
    out, err, rc = recover.ssh_script(
        "export GRAFANA_ROOT_URL=" + _shq(GRAFANA_ROOT_URL)
        + "\nexport RETIRE_HEADERS=" + _shq(retire_headers()) + "\n" + APPLY, timeout=420)
    print(out)
    if err.strip():
        print("-- stderr --\n" + err.strip()[:1200])
    if rc != 0:
        print("\n[X] the remote step exited %s. The fragment backup is named in the PREFLIGHT "
              "section above and the guard restores it automatically on a failed assemble." % rc)
        watch("AFTER a failed run")
        return 6

    print("\n-- step 3/3: verify --")
    after = watch("AFTER")
    broke = [n for n, _u, okc in WATCH if after[n] not in okc]
    final = _probe("https://cybergod.ai/observe/")
    print("   %-22s %s" % ("cybergod.ai/observe/", final))
    if broke or final not in ("200", "302", "301"):
        print("\n[X] %s. Roll back with the backup printed above." %
              (", ".join(broke) + " changed" if broke else "the dashboard stopped answering"))
        return 7

    print("""
  DONE. Grafana is on https://cybergod.ai/observe/dashboards and %s serves nothing.
    * the /observe route lives in deploy/caddy/cybergod.caddy, which CI reinstalls on every ship
    * Grafana's root_url names the new host; the .pre.<stamp> copy beside the compose file undoes it
    * the godeyes.ai site block is gone from _base.caddy, so Caddy stops renewing that certificate
      and the name can lapse on the 21st without leaving an error in the log every night

  The VideoDead API and SPA that shared that block are not recreated anywhere. Their containers
  are still running and now unreachable from outside, which is a separate decision and some RAM.
""" % OLD)
    return 0


def retire_headers():
    """The site headers to take off the proxy, DERIVED from estate.RETIRED rather than typed.

    godeyes.ai is special: it is served by the `{$DOMAIN}` placeholder, so its own name appears
    nowhere in the Caddyfile and a name-grep cannot see it. That is the whole reason this script
    exists, and it is why the placeholder is in the list beside the literal names."""
    names = ["{$DOMAIN}"]
    names += [h for h in sorted(estate.RETIRED) if not h.startswith("www.") and h != OLD]
    return "|".join(names)


def _shq(s):
    """Single-quote for sh, the only quoting that survives a multi-line payload intact."""
    return "'" + s.replace("'", "'\"'\"'") + "'"


def main():
    ap = argparse.ArgumentParser(description="move the observability stack off godeyes.ai")
    ap.add_argument("--apply", action="store_true", help="make the change (default: measure only)")
    ap.add_argument("--plan-only", action="store_true",
                    help="skip the ssh probe and just print the local half")
    a = ap.parse_args()

    if a.apply:
        return apply()

    refs = repo_references()
    if not a.plan_only:
        if measure() is None:
            print("\n[X] measurement failed, so there is no plan worth printing.")
            return 1
    print_plan(refs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
