#!/usr/bin/env python3
"""
set_secret.py — add/update ONE runtime secret EVERYWHERE it lives, then recreate its consumers.

WHY THIS EXISTS: secrets must never enter git (gitleaks blocks it, and compose files are committed).
The sanctioned home is the droplet's own `assess-bot/.env` (chmod 600) — which colt-web already
loads via `env_file:`. But "edit a file over SSH by hand" is exactly the kind of invisible change
that gets lost on the next deploy. So: one re-runnable script, no hand-editing, no command blobs.

  python set_secret.py ABUSEIPDB_KEY          # prompts, hidden input
  python set_secret.py --list                 # which secret NAMES exist on the droplet
  python set_secret.py --audit                # which key each env file / container holds (no writes)

The value is read with getpass and piped over stdin — it is never passed as an argv (argv is visible
in `ps` and lands in your shell history), never echoed, and never logged.

A CREDENTIAL HAS AS MANY HOMES AS SOMEBODY GAVE IT, AND THIS SCRIPT KNEW ABOUT ONE (22 Nov 2026).
    The new DigitalOcean key was installed correctly and `deepseek-v4.1-flash` still 403'd from
    surfaces nobody had looked at. MEASURED on this checkout:

        assess-bot/.env      OPENAI_API_KEY / DO_INFERENCE_KEY   sha256 b4bb02748df6   (new)
        cassandra-bot/.env   OPENAI_API_KEY                      sha256 9327f18662ac   (July)

    cassandra-bot loads its OWN env file (`env_file: cassandra-bot/.env` in all three compose
    files) and reads the same `OPENAI_API_KEY`. This script wrote one file, so the bot had been
    calling the inference API on a different, older credential for months — and `deploy.py`'s
    BOTS_SECRETS packs BOTH files, so every `--reuse` deploy re-shipped the stale one.

    TWO separate defects, each with its own repair:
      1. THE FILES. The credential is now written to every env file that already holds it, derived
         by reading the files (class 35), never from a list typed here. Files that do NOT hold it
         are NAMED rather than quietly written to: an env file with no inference key points at a
         service nobody configured, which is a different fault with a different repair.
      2. THE CONTAINERS. A container's environment is baked at CREATION. `docker restart` re-runs
         the process with the OLD environment, so a consumer that is merely restarted keeps the old
         credential and reports a perfectly accurate 403. Every consumer is RECREATED, and the set
         is derived from compose's own labels, confined to project `colt-stack` so the other stacks
         on this host are never touched (operating principle 4).

    And it VERIFIES, per container, by sha256 prefix — never key material, this repo is public.
    "Did the new key actually land?" was unanswerable before, which is why a 403 was read as a
    model-id problem for an afternoon.
"""
import argparse, base64, getpass, hashlib, os, re, subprocess, sys

HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", "")
SSH  = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"] + (["-i", KEY] if KEY and os.path.exists(KEY) else [])
ENVF  = "/opt/colt-stack/assess-bot/.env"
LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assess-bot", ".env")

# CRITICAL: `deploy.py --reuse` PACKS the local assess-bot/.env and extracts it over the droplet's
# copy. So a secret written only on the droplet is silently WIPED by the next bot deploy. The local
# file is the source of truth — write BOTH. (deploy_web_direct.py does not ship .env, which is why
# this was not obvious.) The local file is gitignored (`*.env`), so it never reaches the repo.

# The remote half. NAME, the name FAMILY and the primary env path travel in argv (all non-secret);
# the VALUE arrives on stdin and never appears in `ps` or a shell history.
#
# NO %-FORMATTING. This block used to be built with `% ENVF`, which meant every literal `%` in it
# had to be written `%%` (class 44) — a precondition that is invisible at the point of editing and
# has bitten this repo before. Everything variable is an argument now, so the script below is the
# script that runs.
FINGERPRINT = r'''
import hashlib, os, sys
v = os.environ.get(sys.argv[1]) or ""
print("   %-16s %s" % (sys.argv[2],
      ("set, %d chars, sha256 %s" % (len(v), hashlib.sha256(v.encode()).hexdigest()[:12]))
      if v else "MISSING"))
'''

REMOTE = r'''
NAME="$1"; FAMILY="$2"; PRIMARY="$3"; FPRINT="$4"
VALUE="$(cat)"                       # value arrives on stdin, never as an argument
set -e
mkdir -p "$(dirname "$PRIMARY")"; touch "$PRIMARY"; chmod 600 "$PRIMARY"

# --- 1. WHERE DOES THIS CREDENTIAL ALREADY LIVE? -----------------------------------------------
# DERIVED by reading the files (class 35), never from a list typed into this script - which is the
# exact defect being repaired: cassandra-bot/.env held its own, older OPENAI_API_KEY for months
# because only assess-bot/.env was ever written.
# The stack root is DERIVED from the primary env path, which is this script's one home for it
# (`ENVF`). A second literal /opt/colt-stack here would be a value with two homes, and it also made
# this block untestable anywhere but the droplet - a check that cannot run is not a check (class 2).
ROOT="$(dirname "$(dirname "$PRIMARY")")"
FILES="$PRIMARY"
for f in "$ROOT"/*/.env; do
  [ -f "$f" ] || continue
  [ "$f" = "$PRIMARY" ] && continue
  if grep -qE "^($FAMILY)=" "$f" 2>/dev/null; then FILES="$FILES $f"; fi
done

echo "== ${NAME}: writing every env file that holds this credential =="
for f in $FILES; do
  grep -v "^${NAME}=" "$f" > "${f}.tmp" 2>/dev/null || true
  printf '%s=%s\n' "$NAME" "$VALUE" >> "${f}.tmp"
  mv "${f}.tmp" "$f"; chmod 600 "$f"
  echo "   wrote   $f"
done
# NAME the files it does NOT live in. An env file with no inference key points at a service nobody
# configured - a different fault with a different repair, and writing to it silently would hide it.
for f in "$ROOT"/*/.env; do
  [ -f "$f" ] || continue
  case " $FILES " in *" $f "*) ;; *) echo "   skipped $f  (this credential has never lived in it)";; esac
done

# --- 2. RECREATE THE CONSUMERS, EACH FROM ITS OWN DEFINITION ------------------------------------
# A CONTAINER'S ENVIRONMENT IS BAKED AT CREATION. `docker restart` re-executes the process with the
# OLD environment, so a merely-restarted consumer keeps the stale credential and then reports an
# entirely accurate 403. The set is derived from compose's own labels and filtered to project
# colt-stack: Amnezia VPN, VideoDead and joplin share this host and are never touched (principle 4).
#
# AND IT IS RECREATED PER SERVICE, NOT PER FILE, WHICH THE FIRST VERSION GOT WRONG AND PROVED ON
# PRODUCTION. Several compose files define the SAME services: docker-compose.ghcr.yml PULLS the
# built-and-scanned image, docker-compose.reuse.yml BUILDS locally. Looping over every file and
# running a bare `up -d` applied each definition in turn, so the bots were recreated from ghcr.yml
# and then AGAIN from reuse.yml - last one wins, and the only internet-facing artifact silently
# stopped being the one CI scanned ("ONE ARTIFACT"). The run after it showed ghcr.yml no longer
# claimed by any container, which is how it was caught.
# A container's OWN labels carry the exact -f list it was created from. Rebuilding that invocation
# and naming only that service reproduces its definition instead of choosing between definitions.
PAIRS="$(docker ps -q --filter label=com.docker.compose.project=colt-stack \
         | xargs -r -n1 docker inspect \
             -f '{{index .Config.Labels "com.docker.compose.service"}}|{{index .Config.Labels "com.docker.compose.project.config_files"}}' \
         | grep -v '^|' | sort -u)"
cd "$ROOT"
if [ -z "$PAIRS" ]; then
  echo "== no running colt-stack container reports a compose service - NOTHING was recreated =="
  echo "   the env files above are correct; the containers still hold the OLD value."
else
  echo "== recreating colt-stack services (env is baked at creation, so a restart is not enough) =="
  for cfgset in $(echo "$PAIRS" | cut -d'|' -f2- | sort -u); do
    SVCS="$(echo "$PAIRS" | awk -F'|' -v s="$cfgset" '$2==s{print $1}' | sort -u | tr '\n' ' ')"
    FARGS=""; MISSING=""
    for f in $(echo "$cfgset" | tr ',' ' '); do
      if [ -f "$f" ]; then FARGS="$FARGS -f $f"; else MISSING="$MISSING $f"; fi
    done
    if [ -n "$MISSING" ]; then
      echo "   skipped $SVCS - compose file(s) absent from disk:$MISSING"
      echo "   [!] these containers still hold the OLD value"
      continue
    fi
    # NO --remove-orphans: one compose file does not know another's services and would delete them.
    if docker compose -p colt-stack $FARGS up -d --force-recreate $SVCS >/dev/null 2>&1; then
      echo "   recreated $SVCS from $cfgset"
    else
      echo "   [!] FAILED to recreate $SVCS - they still hold the OLD value"
    fi
  done
  sleep 3
fi

# --- 3. VERIFY, PER CONTAINER -------------------------------------------------------------------
# A fingerprint, never key material: this repository is public. "Did the new key actually land?" is
# the first question a 403 cannot answer.
echo "== which value does each colt-stack container hold now? (sha256 prefix) =="
printf '%s' "$FPRINT" | base64 -d > /tmp/.fp.py
for ct in $(docker ps --format '{{.Names}}' --filter label=com.docker.compose.project=colt-stack | sort); do
  # PROVENANCE BESIDE THE CREDENTIAL. Recreating a container is also the moment its image can
  # change, and that change is invisible unless it is printed: a ghcr.io ref is the artifact CI
  # built and scanned, a bare local tag is one that never passed a scanner. This line is what
  # caught the per-file recreate replacing the scanned bots with locally-built ones.
  echo "   $ct  image $(docker inspect -f '{{.Config.Image}}' "$ct" 2>/dev/null)"
  if ! docker exec "$ct" sh -c 'command -v python3 >/dev/null 2>&1'; then
    echo "   $ct  (no python3 in this image - cannot be asked)"
    continue
  fi
  # The name travels in argv; the VALUE is read from the container's OWN environment, which is the
  # only thing that answers "what does this process actually hold".
  docker exec -i "$ct" python3 - "$NAME" "$ct" < /tmp/.fp.py 2>/dev/null \
    || echo "   $ct  (could not be asked)"
done
rm -f /tmp/.fp.py
'''


def local_env_files():
    """Every local env file `deploy.py` packs — read from deploy.py's own list, not retyped.

    ONE HOME (class 32). `deploy.BOTS_SECRETS` already decides which files are shipped to the
    droplet; a second copy of that list here is how `cassandra-bot/.env` ended up outside this
    script's world in the first place.
    """
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.py")
    rels = []
    try:
        with open(src, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("BOTS_SECRETS"):
                    body = line.split("[", 1)[1].rsplit("]", 1)[0]
                    rels = [p.strip().strip("\"'") for p in body.split(",") if p.strip()]
                    break
    except OSError:
        pass
    if not rels:
        # A derivation that silently returns nothing is class 37. Say so and fall back to the one
        # file we are certain of rather than pretending the set is empty.
        print("   [!] could not read BOTS_SECRETS from deploy.py - falling back to assess-bot/.env")
        rels = ["assess-bot/.env"]
    root = os.path.dirname(os.path.abspath(__file__))
    return [os.path.join(root, *r.split("/")) for r in rels]


def key_homes(family=None):
    """(path, name, sha256-prefix, length) for every place a credential lives locally.

    Used by `--audit` and by ship.py, which reports divergence without blocking: a split
    credential is a silent 403 on whichever surface holds the older half.
    """
    fam = set(family or TWINS)
    out = []
    for p in local_env_files():
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    n, _, v = line.partition("=")
                    if n.strip() in fam:
                        v = v.strip()
                        out.append((p, n.strip(), hashlib.sha256(v.encode()).hexdigest()[:12],
                                    len(v)))
        except OSError:
            continue
    return out


def upsert_local(name, value, family):
    """Write the value into every local env file that already holds this credential.

    WHY EVERY FILE, NOT JUST assess-bot/.env: `deploy.py --reuse` PACKS the local copies and
    extracts them over the droplet's, so a file left behind here silently re-ships a stale key on
    the next bot deploy. That is how cassandra-bot kept a July credential through three key
    rotations. The primary is always written (it is the file colt-web loads); the others are written
    only where the credential already lives, and the rest are named.
    """
    ok = True
    targets = [LOCAL]
    for p in local_env_files():
        if os.path.abspath(p) == os.path.abspath(LOCAL) or not os.path.exists(p):
            continue
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if any(re.search(r"(?m)^%s=" % re.escape(n), text) for n in family):
            targets.append(p)
        else:
            print("   local  : %s skipped (this credential has never lived in it)" % p)
    for path in targets:
        try:
            lines = []
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    lines = [l for l in fh.read().split("\n")
                             if not l.startswith(name + "=")]
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
            while lines and lines[-1] == "":
                lines.pop()
            lines.append("%s=%s" % (name, value))
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            try: os.chmod(path, 0o600)
            except OSError: pass                  # Windows/mounted FS may refuse — not fatal
            print("   local  : %s updated (gitignored, shipped by deploy.py)" % path)
        except Exception as e:
            ok = False
            print("   [!] could not update %s (%s)." % (path, repr(e)[:70]))
            print("       WARNING: `python deploy.py --reuse` would then overwrite the droplet and")
            print("       silently restore the OLD %s. Fix it by hand." % name)
    return ok


def remote_command(name, family):
    """The command ssh runs on the droplet.

    THE BUG THIS FIXES (2026-08-14): the old line was
        subprocess.run(SSH + [host, "bash -s", "--", name], input=value)
    `bash -s` reads its SCRIPT from stdin, but the code piped the VALUE into stdin - so the droplet
    ran the API KEY as a command ("bash: line 1: <key>: command not found") and the REMOTE script
    was never sent. The secret also reached the droplet's shell.
    FIX: the script travels in ARGV (base64'd, into a temp file so no quoting layer can corrupt it);
    stdin is left free for the VALUE, which is what `VALUE="$(cat)"` in the script reads. The value
    therefore never appears in argv, in `ps`, or in any shell history - only the NAME and the
    (non-secret) script do.
    """
    b64 = base64.b64encode(REMOTE.encode("utf-8")).decode("ascii")
    fp = base64.b64encode(FINGERPRINT.encode("utf-8")).decode("ascii")
    # decode the script to a temp file, run it with the four non-secret arguments, keep the exit
    # code, clean up. The fingerprint probe travels base64'd too, so no quoting layer can corrupt it
    # on its way into the container.
    return ("S=$(mktemp) && printf %%s '%s' | base64 -d > \"$S\" && "
            "bash \"$S\" '%s' '%s' '%s' '%s'; rc=$?; rm -f \"$S\"; exit $rc"
            % (b64, name, "|".join(sorted(family)), ENVF, fp))


# ONE CREDENTIAL, TWO NAMES - so setting one of them is how the stale twin is born.
#
# The engine resolves its inference key by trying OPENAI_API_KEY then DO_INFERENCE_KEY, and
# enrich.py carries the scar in a comment: `set_secret.py OPENAI_API_KEY` installed a NEW key while
# the OLD one stayed parked in DO_INFERENCE_KEY, the file-order resolver picked the stale one, and
# the bake-off's own fingerprint proved it (3c6b3a6a832e vs 5847c2bbe7cd). Writing one name and
# leaving the other is not a half-done job, it is a credential that looks right and silently is
# not. So either name writes BOTH, and the warning about divergent twins can no longer be reached
# through this script.
TWINS = {"OPENAI_API_KEY", "DO_INFERENCE_KEY"}


def names_for(name):
    """Every name this value must be written under. One home for 'which names mean the key'."""
    return sorted(TWINS) if name in TWINS else [name]


def run(name, value):
    rc = 0
    targets = names_for(name)
    family = set(targets)
    if len(targets) > 1:
        print("   note   : %s is the inference key, which the engine reads under %s - writing "
              "both so neither can go stale." % (name, " and ".join(targets)))
    before = key_homes(family)
    if len({f[2] for f in before}) > 1:
        print("   note   : this credential is currently SPLIT across its homes - %s"
              % ", ".join("%s=%s" % (os.path.basename(os.path.dirname(p)), fp)
                          for p, _n, fp, _l in before))
    for n in targets:
        upsert_local(n, value, family)            # local first: it is what deploy.py ships
        r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), remote_command(n, family)],
                           input=value.encode("utf-8"))  # VALUE only on stdin, never in argv
        rc = rc or r.returncode
    after = key_homes(family)
    fps = {f[2] for f in after}
    print("   local homes now: %s" % (", ".join(sorted(fps)) or "(none found)"))
    if len(fps) > 1:
        print("   [!] still SPLIT locally. `deploy.py --reuse` ships these files, so the older half")
        print("       will be restored on the next bot deploy. Homes: %s"
              % ", ".join("%s -> %s" % (p, fp) for p, _n, fp, _l in after))
        rc = rc or 4
    return rc


def audit():
    """Which value does each local home hold? No writes, no ssh, no key material."""
    rows = key_homes()
    if not rows:
        print("  no inference key found in any file deploy.py ships - that is itself the finding.")
        return 1
    print("  === inference key homes (sha256 prefix, never the key) ===")
    for p, n, fp, ln in rows:
        print("  %-48s %-18s %d chars  %s" % (p, n, ln, fp))
    fps = {r[2] for r in rows}
    if len(fps) == 1:
        print("  all %d home(s) hold the SAME credential" % len(rows))
        return 0
    print("  [X] SPLIT across %d different values. Whichever surface holds the older one answers"
          % len(fps))
    print("      HTTP 403 for any model granted only to the newer key - an accurate reply to a")
    print("      stale credential, which reads exactly like a wrong model id. Repair:")
    print("      python set_secret.py OPENAI_API_KEY")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="secret name, e.g. ABUSEIPDB_KEY")
    ap.add_argument("--list", action="store_true", help="list secret NAMES on the droplet")
    ap.add_argument("--audit", action="store_true",
                    help="which value each local env file holds (fingerprints, no writes)")
    a = ap.parse_args()

    if a.audit:
        sys.exit(audit())
    if a.list:
        subprocess.run(SSH + ["%s@%s" % (USER, HOST),
                              "sed -n 's/^\\([A-Z0-9_]*\\)=.*/   \\1/p' %s" % ENVF])
        return
    if not a.name:
        ap.error("give a secret name, e.g.  python set_secret.py ABUSEIPDB_KEY")

    print("Paste the value for %s (input hidden, not echoed, not stored locally):" % a.name)
    value = getpass.getpass("  %s = " % a.name).strip()
    if not value:
        sys.exit("[X] empty value — nothing changed.")
    if len(value) < 8:
        print("[!] that looks short for an API key — continuing anyway.")
    sys.exit(run(a.name, value))


if __name__ == "__main__":
    main()
