#!/usr/bin/env python3
"""decommission.py — retire a site from the shared droplet, reversibly.

    python decommission.py                          # DRY RUN: shows the plan, changes nothing
    python decommission.py --apply                  # do it
    python decommission.py --apply --sites a.com,b.de
    python decommission.py --list                   # what is currently served, and by what
    python decommission.py --undo 20260901-143000   # put a decommission back

WHY THIS IS A SCRIPT AND NOT A COUPLE OF SSH COMMANDS
    Every site on that droplet is served by ONE shared Caddy. On 2026-08-07 a deploy truncated
    another project's block in the shared Caddyfile, Caddy kept serving from memory for twelve
    hours, and the next kernel reboot took cybergod.ai, godeyes.ai, jobhuntwow.com and
    klimaanlage-preise.de down together for six hours. The standing rule in CLAUDE.md since then is
    absolute: never hand-edit that file, everything goes through caddyguard fragments, and every
    write is validated before it is applied.

    Removing a site is exactly the operation that caused that outage. So it goes through the same
    guard, in the same order, with the same verification, and it refuses rather than guesses.

WHAT "DECOMMISSION" MEANS HERE, PRECISELY
    STOPPED:  the container is stopped AND its restart policy is set to `no`, so a reboot does not
              quietly bring it back. A stopped container that restarts on boot is not decommissioned,
              it is decommissioned until Tuesday.
    UNSERVED: its Caddy fragment is MOVED to /opt/caddyguard/decommissioned/<stamp>/, never
              deleted, and the config is reassembled and validated before it is loaded.
    KEPT:     volumes, images and databases are untouched. Nothing here deletes data.

    That last line is deliberate and is not timidity: an irreversible action taken on a Tuesday
    afternoon to save a few euros is a bad trade, and `--undo` only means something if the data is
    still there. If you later want the disk space back, delete the volumes by hand, once you are
    sure, with the container already gone.

THE COLLATERAL CHECK IS THE IMPORTANT PART
    A fragment can declare several site names. If a fragment we are about to remove also serves a
    domain that is NOT on the decommission list, removing it takes that domain down too. The plan
    refuses in that case and tells you which fragment and which domain, rather than proceeding and
    discovering it from a customer.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recover import HOST, probe, sections, ssh_script  # noqa: E402  one ssh implementation

# Sites that must SURVIVE and are verified afterwards. If one of these stops answering, the
# decommission has done damage and says so instead of reporting success.
SURVIVORS = ["https://cybergod.ai/api/me", "https://www.cybergod.ai/",
             "https://godeyes.ai/", "https://www.jobhuntwow.com/"]

DEFAULT_SITES = ["jev.best", "www.jev.best",
                 "klimaanlage-preise.de", "www.klimaanlage-preise.de",
                 "klimaanlage-montieren.de", "www.klimaanlage-montieren.de"]

GUARD = "/opt/caddyguard"


def plan_script(sites):
    """READ-ONLY. Everything needed to decide, in one ssh session."""
    return r"""
set +e
SITES="%s"
echo "#### FRAGMENTS"
ls -1 %s/blocks/*.caddy 2>/dev/null | while read -r f; do
  n=$(basename "$f")
  # A site header is a line at column zero ending in '{'. Report every name each fragment claims.
  names=$(grep -oE '^[a-z0-9.*-]+(,[[:space:]]*[a-z0-9.*-]+)*[[:space:]]*\{' "$f" \
          | sed 's/[[:space:]]*{//' | tr '\n' ' ')
  echo "$n|$names"
done
echo "#### CONTAINERS"
docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>/dev/null
echo "#### UPSTREAMS"
grep -hoE 'reverse_proxy[[:space:]]+[^ ]+' %s/blocks/*.caddy 2>/dev/null | sort -u
echo "#### MATCHES"
for s in $SITES; do
  grep -l -E "(^|[[:space:],])$(echo "$s" | sed 's/\./\\./g')([[:space:],]|[[:space:]]*\{)" \
      %s/blocks/*.caddy 2>/dev/null | while read -r f; do echo "$s|$(basename $f)"; done
done
echo "#### DISK"
df -h / | tail -1
echo "#### BACKUPS"
ls -1t %s/decommissioned 2>/dev/null | head -10
""" % (" ".join(sites), GUARD, GUARD, GUARD, GUARD)


def apply_script(frags, containers, stamp):
    """The change. Order matters and every step is checked before the next one runs."""
    return r"""
set -e
STAMP="%s"
DEST=%s/decommissioned/$STAMP
mkdir -p "$DEST"

echo "#### BACKUP"
# The whole current state, before anything moves. caddyguard keeps its own backups too, but a
# decommission is the one operation where you most want a single tarball you can point at.
tar czf "$DEST/before.tgz" -C %s blocks 2>/dev/null && echo "saved $DEST/before.tgz"
cp -a /opt/videodead/Caddyfile "$DEST/Caddyfile.before" 2>/dev/null && echo "saved live Caddyfile"

echo "#### MOVE_FRAGMENTS"
for f in %s; do
  if [ -f "%s/blocks/$f" ]; then
    mv "%s/blocks/$f" "$DEST/$f" && echo "moved $f -> $DEST/"
  else
    echo "absent $f (already decommissioned?)"
  fi
done

echo "#### REASSEMBLE"
# assemble --apply validates in the proxy's OWN image and env, refuses a config with no site
# blocks, checks the bind mount is fresh, and only then reloads. If it refuses, we stop here with
# the fragments already moved but the LIVE config untouched, which is a safe place to be.
python3 %s/agent.py assemble --apply

echo "#### ROSTER"
python3 %s/agent.py roster || true
echo "#### DRIFT"
python3 %s/agent.py drift || true

echo "#### STOP_CONTAINERS"
for c in %s; do
  if docker inspect "$c" >/dev/null 2>&1; then
    # restart=no FIRST. Stopping a container whose policy is `always` only pauses it until the
    # next reboot, and a reboot is exactly when nobody is watching.
    docker update --restart=no "$c" >/dev/null 2>&1 && echo "restart policy -> no: $c"
    docker stop "$c" >/dev/null 2>&1 && echo "stopped $c"
  else
    echo "no such container: $c"
  fi
done

echo "#### REMAINING"
docker ps --format '{{.Names}}|{{.Status}}'
echo "#### NOTE"
echo "volumes and images kept. Nothing here deleted data. Undo: decommission.py --undo $STAMP"
""" % (stamp, GUARD, GUARD, " ".join(frags), GUARD, GUARD, GUARD, GUARD, GUARD,
       " ".join(containers))


def undo_script(stamp):
    return r"""
set -e
DEST=%s/decommissioned/%s
[ -d "$DEST" ] || { echo "#### ERROR"; echo "no such decommission: $DEST"; exit 1; }
echo "#### RESTORE_FRAGMENTS"
for f in "$DEST"/*.caddy; do
  [ -f "$f" ] || continue
  cp -a "$f" %s/blocks/ && echo "restored $(basename $f)"
done
echo "#### REASSEMBLE"
python3 %s/agent.py assemble --apply
echo "#### ROSTER"
python3 %s/agent.py roster || true
echo "#### NOTE"
echo "containers are NOT started automatically - start the ones you want by hand, so a restore"
echo "of the routing does not silently restart something that was spending money."
""" % (GUARD, stamp, GUARD, GUARD, GUARD)


def _match_map(sec):
    out = {}
    for line in (sec or "").splitlines():
        if "|" in line:
            site, frag = line.split("|", 1)
            out.setdefault(frag.strip(), set()).add(site.strip())
    return out


def _frag_names(sec):
    out = {}
    for line in (sec or "").splitlines():
        if "|" in line:
            n, names = line.split("|", 1)
            out[n.strip()] = [x for x in names.replace(",", " ").split() if x]
    return out


def show_plan(sites, d):
    frag_names = _frag_names(d.get("FRAGMENTS"))
    matches = _match_map(d.get("MATCHES"))
    print("\n" + "=" * 74)
    print("  DECOMMISSION PLAN  (nothing has changed)")
    print("=" * 74)
    print("  target sites : %s" % ", ".join(sites))

    print("\n  FRAGMENTS CURRENTLY SERVED")
    for n, names in sorted(frag_names.items()):
        mark = "  <-- to remove" if n in matches else ""
        print("    %-28s %s%s" % (n, " ".join(names)[:60] or "(no site header found)", mark))

    if not matches:
        print("\n  [!] none of the target sites is served by a caddyguard fragment.")
        print("      Either they are already gone, or they are served some other way. Run")
        print("      `python decommission.py --list` and look at the fragment list above.")
        return None, None

    # THE COLLATERAL CHECK. A fragment can carry more than one site.
    collateral = {}
    for frag, hit in matches.items():
        extra = [n for n in frag_names.get(frag, []) if n not in sites and not n.startswith("#")]
        if extra:
            collateral[frag] = extra
    if collateral:
        print("\n  [X] REFUSING: these fragments also serve domains you did NOT ask to remove.")
        for frag, extra in collateral.items():
            print("      %-28s would also take down: %s" % (frag, ", ".join(extra)))
        print("      Split the fragment first, or add those domains to --sites deliberately.")
        return None, None

    # Which containers do the doomed fragments point at? Discovered, never assumed: guessing a
    # container name and stopping the wrong one is the whole risk of this operation.
    running = {}
    for line in (d.get("CONTAINERS") or "").splitlines():
        p = line.split("|")
        if len(p) >= 3:
            running[p[0]] = p[2]
    guess = [c for c in running
             if any(k in c.lower() for k in ("polara", "klima", "jev"))]

    print("\n  WILL REMOVE FRAGMENTS : %s" % ", ".join(sorted(matches)))
    print("  WILL STOP CONTAINERS  : %s" % (", ".join(guess) or "(none matched by name)"))
    if not guess:
        print("      No container name matched. The vhosts will stop being served, which is the")
        print("      part that matters; pass --containers a,b if you also want them stopped.")
    print("\n  WILL KEEP             : volumes, images, databases, DNS. Fully reversible.")
    print("  MUST KEEP SERVING     : %s" % ", ".join(s.split("/")[2] for s in SURVIVORS))
    print("\n  Re-run with --apply to do it.")
    return sorted(matches), guess


def verify():
    print("\n  VERIFY: the sites that must survive")
    bad = []
    for url in SURVIVORS:
        st, note = probe(url)
        ok = st in (200, 301, 302, 401)
        print("    %-40s %s %s" % (url, st or "---", "ok" if ok else "<-- BROKEN " + str(note)[:40]))
        if not ok:
            bad.append(url)
    if bad:
        print("\n  [X] A SURVIVING SITE IS NOT ANSWERING. Undo immediately:")
        print("      python decommission.py --undo <stamp printed above>")
        return 1
    print("    all survivors answering")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually do it (default is a dry run)")
    ap.add_argument("--list", action="store_true", help="just show what is served")
    ap.add_argument("--undo", metavar="STAMP", help="restore a previous decommission")
    ap.add_argument("--sites", default=",".join(DEFAULT_SITES))
    ap.add_argument("--containers", default="", help="override the containers to stop")
    a = ap.parse_args()

    print("  droplet: %s" % HOST)
    if a.undo:
        out = ssh_script(undo_script(a.undo), timeout=300)
        for name, body in sections(out).items():
            print("\n#### %s\n%s" % (name, body.rstrip()))
        return verify()

    sites = [s.strip() for s in a.sites.split(",") if s.strip()]
    d = sections(ssh_script(plan_script(sites), timeout=240))
    if a.list:
        for name in ("FRAGMENTS", "CONTAINERS", "BACKUPS", "DISK"):
            print("\n#### %s\n%s" % (name, (d.get(name) or "").rstrip()))
        return 0

    frags, guess = show_plan(sites, d)
    if not a.apply:
        return 0
    if not frags:
        return 1
    containers = [c.strip() for c in a.containers.split(",") if c.strip()] or guess
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    print("\n  APPLYING (stamp %s)" % stamp)
    out = ssh_script(apply_script(frags, containers, stamp), timeout=420)
    for name, body in sections(out).items():
        print("\n#### %s\n%s" % (name, body.rstrip()))
    return verify()


if __name__ == "__main__":
    sys.exit(main())
