#!/usr/bin/env python3
"""decommission.py — retire a site from the shared droplet, reversibly.

    python decommission.py --sites jev            # DRY RUN: shows the plan, changes nothing
    python decommission.py --sites jev --apply    # do it
    python decommission.py --sites a.com,b.de --apply
    python decommission.py --list                 # what is currently served, and by what
    python decommission.py --undo 20260901-143000 # put a decommission back

There is no default target: naming the site is the point, and a tool that retires something when
you give it no arguments is a loaded gun (see SITE_GROUPS).

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

    That refusal used to be the end of the road, which mattered because on this droplet most
    vhosts share `_base.caddy`: "retire jev.best" could only ever answer "no". A shared fragment is
    now EDITED instead — its target site blocks are lifted out by brace counting (never a
    line-based regex, which is the 2026-08-07 shape), the rest of the file is kept byte-for-byte,
    the ORIGINAL is archived under the stamp so `--undo` restores it unchanged, and the result is
    still validated and reloaded only by the guard. A header that lists a target name together
    with one we are keeping is still refused: that is a routing decision, not an edit.
"""
import argparse
import base64
import binascii
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recover import HOST, probe, sections, ssh_script  # noqa: E402  one ssh implementation

# Sites that must SURVIVE and are verified afterwards. If one of these stops answering, the
# decommission has done damage and says so instead of reporting success.
SURVIVORS = ["https://cybergod.ai/api/me", "https://www.cybergod.ai/",
             "https://godeyes.ai/", "https://www.jobhuntwow.com/"]

# NAMED GROUPS, NOT A DEFAULT TARGET LIST (2026-10-22).
#
# This used to be `DEFAULT_SITES`, and `--sites` defaulted to it: jev.best AND the two klimaanlage
# domains. So `python decommission.py --apply`, with no arguments, retired a live project that
# nobody had asked about. Dry-run-by-default protects the ACTION; nothing protected the TARGET.
# A destructive tool must not have a destructive default in either half.
#
# The property the old list really carried — never leave half a site served, because `www.` left
# behind trips the collateral check on the next run for a domain you believe is already gone — is
# now enforced by expand_sites() on whatever the operator names, instead of by remembering to type
# both. The groups are a convenience for the names we actually operate, nothing more.
SITE_GROUPS = {
    "jev": ["jev.best", "www.jev.best"],
    "klima": ["klimaanlage-preise.de", "www.klimaanlage-preise.de",
              "klimaanlage-montieren.de", "www.klimaanlage-montieren.de"],
}

GUARD = "/opt/caddyguard"


def expand_sites(raw):
    """Names or group keys -> the full set, with every apex/www pair completed.

    `--sites jev.best` means jev.best AND www.jev.best. Leaving the www variant served is not a
    smaller decommission, it is a half-finished one that still answers."""
    out = []
    for item in raw:
        item = item.strip().lower()
        if not item:
            continue
        for name in SITE_GROUPS.get(item, [item]):
            if name not in out:
                out.append(name)
    for name in list(out):
        partner = name[4:] if name.startswith("www.") else "www." + name
        if partner not in out:
            out.append(partner)
    return out


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
echo "#### FRAGTEXT"
# The CONTENT of every fragment, base64 so no Caddy directive can collide with this script's own
# '#### NAME' delimiters and no newline convention can survive the trip (class 21). The laptop
# needs the text because a site that shares a fragment with others can still be retired - by
# removing its site BLOCKS and keeping the rest - and that edit is computed here, where it can be
# read and tested, never by a regex running on production.
ls -1 %s/blocks/*.caddy 2>/dev/null | while read -r f; do
  echo "$(basename "$f")|$(base64 -w0 < "$f")"
done
echo "#### DISK"
df -h / | tail -1
echo "#### BACKUPS"
ls -1t %s/decommissioned 2>/dev/null | head -10
""" % (" ".join(sites), GUARD, GUARD, GUARD, GUARD, GUARD)


def apply_script(frags, containers, stamp, edits=None):
    """The change. Order matters and every step is checked before the next one runs.

    `edits` is {fragment: new_text} for fragments that are SHARED: the original file is archived
    under the stamp exactly as `mv` would archive a removed one, and the reduced version is written
    into blocks/. Undo therefore needs no new code — it copies every .caddy in the archive back,
    which restores an edited fragment to its original content just as it restores a removed one.

    The write is a temp file plus `mv` inside blocks/, never an in-place edit. Nothing here touches
    /opt/videodead/Caddyfile: that file is a single-file bind mount whose inode the proxy holds
    open, and it is written only by `agent.py assemble --apply`, which validates in the proxy's own
    image and environment first."""
    writes = ""
    for name, text in sorted((edits or {}).items()):
        writes += (
            'echo "%s"\n'
            # `echo`, not `printf %%s`: the payload is base64 (A-Za-z0-9+/=), so there is nothing
            # for the shell to interpret, and a bare `printf %%s` in a generated script is
            # indistinguishable from an unformatted placeholder that never got substituted - which
            # is the exact defect tests/test_decommission.py scans every generated script for.
            'echo "%s" | base64 -d > "$DEST/%s.new"\n'
            '[ -s "$DEST/%s.new" ] || { echo "refusing: empty replacement for %s"; exit 1; }\n'
            'cp -a "%s/blocks/%s" "$DEST/%s"\n'
            'mv "$DEST/%s.new" "%s/blocks/%s"\n'
            % (("edited %s (original archived)" % name),
               base64.b64encode(text.encode("utf-8")).decode("ascii"), name,
               name, name,
               GUARD, name, name,
               name, GUARD, name))
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

echo "#### EDIT_FRAGMENTS"
%s
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
""" % (stamp, GUARD, GUARD, " ".join(frags) or "__none__", GUARD, GUARD,
       writes or 'echo "no shared fragment needed editing"',
       GUARD, GUARD, GUARD, " ".join(containers) or "__none__")


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


def _frag_text(sec):
    """{fragment name: text} from the base64 the plan collected."""
    out = {}
    for line in (sec or "").splitlines():
        if "|" not in line:
            continue
        name, b64 = line.split("|", 1)
        b64 = b64.strip()
        if not b64:
            continue
        try:
            out[name.strip()] = base64.b64decode(b64).decode("utf-8", "replace")
        except (ValueError, binascii.Error):
            continue
    return out


def split_fragment(text, sites):
    """(kept, removed, refusal) — the fragment with the target site blocks taken out.

    WHY THIS EXISTS. The collateral check refuses to delete a fragment that also serves a domain
    nobody asked about, which is correct and was, until now, the end of the road: on this droplet
    most vhosts live in `_base.caddy` together, so "retire jev.best" produced a refusal and no way
    forward. Removing the SITE BLOCKS and keeping the rest is the operation that was missing.

    A site block is a header at column zero ending in `{`, then everything up to the matching
    close brace. Braces are counted, never matched by a regex: a `handle { }` nested three deep is
    ordinary Caddy and a line-based rule would cut the fragment in half, which is precisely the
    2026-08-07 shape.

    It REFUSES (returns a reason, changes nothing) when:
      * one header lists a target name AND a name we are keeping — the two cannot be separated
        without rewriting someone else's routing, so a human decides;
      * a block never closes, which means our brace counting disagrees with Caddy's parser and the
        only safe answer is to stop.
    The caller still validates the result through the guard; this function is not the authority,
    it only proposes."""
    lines = text.splitlines(True)
    kept, removed = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([A-Za-z0-9*][A-Za-z0-9.,*:\-\s]*?)\s*\{\s*$", line)
        names = []
        if m and not line.startswith((" ", "\t")):
            names = [n.strip().lower() for n in m.group(1).split(",") if n.strip()]
        hit = [n for n in names if n in sites]
        if not hit:
            kept.append(line)
            i += 1
            continue
        other = [n for n in names if n not in sites]
        if other:
            return None, None, (
                "the site header `%s` lists %s together with %s - one block cannot be removed for "
                "one name and kept for another. Split that header first, or add %s to --sites."
                % (line.strip(), ", ".join(hit), ", ".join(other), ", ".join(other)))
        depth, block = 0, []
        while i < len(lines):
            block.append(lines[i])
            depth += lines[i].count("{") - lines[i].count("}")
            i += 1
            if depth <= 0:
                break
        if depth > 0:
            return None, None, (
                "the block starting `%s` never closes - brace counting disagrees with Caddy's "
                "parser, so nothing is changed." % line.strip())
        removed.append("".join(block))
    if not removed:
        return None, None, "no site block in this fragment declares any of the target names"
    return "".join(kept), "".join(removed), None


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

    # THE COLLATERAL CHECK. A fragment can carry more than one site. Removing the whole file would
    # take the others down with it, so such a fragment is EDITED instead: its target site blocks
    # move out, everything else stays byte-for-byte.
    texts = _frag_text(d.get("FRAGTEXT"))
    whole, extract, refused = [], {}, {}
    for frag in sorted(matches):
        extra = [n for n in frag_names.get(frag, []) if n not in sites and not n.startswith("#")]
        if not extra:
            whole.append(frag)
            continue
        text = texts.get(frag)
        if text is None:
            refused[frag] = ("also serves %s, and the plan could not read the fragment's text, "
                             "so no edit can be proposed" % ", ".join(extra))
            continue
        kept, removed, why = split_fragment(text, sites)
        if why:
            refused[frag] = "also serves %s: %s" % (", ".join(extra), why)
        else:
            extract[frag] = (kept, removed, extra)

    if refused:
        print("\n  [X] REFUSING: these fragments cannot be separated safely.")
        for frag, why in refused.items():
            print("      %-28s %s" % (frag, why))
        return None, None

    # Which containers do the doomed site blocks point at? READ FROM THE CONFIG, not guessed from
    # the container's name. The old rule was `any(k in name for k in ("polara","klima","jev"))` -
    # a substring list with three hardcoded homes that would stop `jev-archive` and miss a
    # container whose name does not contain its domain. The routing already says which upstream
    # serves the block being removed; that is the authority.
    running = {}
    for line in (d.get("CONTAINERS") or "").splitlines():
        p = line.split("|")
        if len(p) >= 3:
            running[p[0]] = p[2]
    doomed_text = "".join([texts.get(f, "") for f in whole]
                          + [removed for _, (_, removed, _) in sorted(extract.items())])
    upstreams = set(re.findall(r"reverse_proxy\s+(?:[^\n{]*?\s)?([A-Za-z0-9_.-]+):\d+",
                               doomed_text))
    guess = sorted(c for c in running if c in upstreams)
    derived = bool(guess)
    if not guess:
        guess = sorted(c for c in running
                       if any(s.split(".")[0] in c.lower() for s in sites if "." in s))

    print("\n  WILL REMOVE FRAGMENTS : %s" % (", ".join(whole) or "(none - all are shared)"))
    if extract:
        print("  WILL EDIT FRAGMENTS   : (site blocks taken out, the rest kept byte-for-byte)")
        for frag, (_, removed, extra) in sorted(extract.items()):
            print("      %-26s -%d line(s); keeps %s"
                  % (frag, len(removed.splitlines()), ", ".join(extra)[:48]))
    print("  WILL STOP CONTAINERS  : %s%s"
          % (", ".join(guess) or "(none matched)",
             "" if derived else "   <-- matched by NAME, not by the routing: check this list"))
    if not guess:
        print("      No container matched. The vhosts will stop being served, which is the")
        print("      part that matters; pass --containers a,b if you also want them stopped.")
    print("\n  WILL KEEP             : volumes, images, databases, DNS. Fully reversible.")
    survivors = _survivor_urls(frag_names, sites)
    print("  MUST KEEP SERVING     : %s" % ", ".join(s.split("/")[2] for s in survivors))
    print("\n  Re-run with --apply to do it.")
    return (whole, extract), guess


def _survivor_urls(frag_names, sites):
    """Every name the proxy serves that we are NOT removing, plus the pinned floor.

    DERIVED, because a hardcoded survivor list measures the day it was written. SURVIVORS stays as
    a floor so the check can never become empty (a check that cannot fail is not a check), and
    because those four are the sites the 2026-08-07 outage actually took down."""
    out = list(SURVIVORS)
    have = {u.split("/")[2] for u in out}
    for names in frag_names.values():
        for n in names:
            n = n.strip().lower()
            if (not n or n.startswith(("#", "*", ":")) or n in sites or n in have
                    or "." not in n):
                continue
            have.add(n)
            out.append("https://%s/" % n)
    return out


def verify(survivors=None):
    print("\n  VERIFY: the sites that must survive")
    bad = []
    for url in (survivors or SURVIVORS):
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
    ap.add_argument("--sites", default="",
                    help="names or a group key (%s). www./apex partners are added automatically."
                         % ", ".join(sorted(SITE_GROUPS)))
    ap.add_argument("--containers", default="", help="override the containers to stop")
    a = ap.parse_args()

    print("  droplet: %s" % HOST)
    if a.undo:
        out = ssh_script(undo_script(a.undo), timeout=300)
        for name, body in sections(out).items():
            print("\n#### %s\n%s" % (name, body.rstrip()))
        return verify()

    sites = expand_sites(a.sites.split(","))
    if not sites and not a.list:
        print("\n  [X] no target. This tool has no default target on purpose: it used to have one,"
              "\n      and `--apply` with no arguments would have retired klimaanlage-preise.de"
              "\n      along with jev.best. Name what you mean:\n")
        for key, names in sorted(SITE_GROUPS.items()):
            print("      python decommission.py --sites %-9s# %s" % (key, ", ".join(names)))
        print("      python decommission.py --list         # what is served right now")
        return 2

    d = sections(ssh_script(plan_script(sites or ["__none__"]), timeout=240))
    if a.list:
        for name in ("FRAGMENTS", "CONTAINERS", "BACKUPS", "DISK"):
            print("\n#### %s\n%s" % (name, (d.get(name) or "").rstrip()))
        return 0

    plan, guess = show_plan(sites, d)
    if not a.apply:
        return 0
    if not plan:
        return 1
    whole, extract = plan
    survivors = _survivor_urls(_frag_names(d.get("FRAGMENTS")), sites)
    containers = [c.strip() for c in a.containers.split(",") if c.strip()] or guess
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    print("\n  APPLYING (stamp %s)" % stamp)
    edits = {frag: kept for frag, (kept, _, _) in extract.items()}
    out = ssh_script(apply_script(whole, containers, stamp, edits), timeout=420)
    for name, body in sections(out).items():
        print("\n#### %s\n%s" % (name, body.rstrip()))
    return verify(survivors)


if __name__ == "__main__":
    sys.exit(main())
