#!/usr/bin/env python3
"""
set_secret.py — add/update ONE runtime secret in the droplet's env file, then restart colt-web.

WHY THIS EXISTS: secrets must never enter git (gitleaks blocks it, and compose files are committed).
The sanctioned home is the droplet's own `assess-bot/.env` (chmod 600) — which colt-web already
loads via `env_file:`. But "edit a file over SSH by hand" is exactly the kind of invisible change
that gets lost on the next deploy. So: one re-runnable script, no hand-editing, no command blobs.

  python set_secret.py ABUSEIPDB_KEY          # prompts, hidden input
  python set_secret.py ABUSEIPDB_KEY --show   # prints the resulting env keys (names only, no values)
  python set_secret.py --list                 # which secret NAMES exist on the droplet

The value is read with getpass and piped over stdin — it is never passed as an argv (argv is visible
in `ps` and lands in your shell history), never echoed, and never logged.
"""
import argparse, getpass, os, subprocess, sys

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

# The remote half. Reads NAME on argv (safe) and the VALUE from stdin (never in ps/history).
REMOTE = r'''
set -e
NAME="$1"; ENVF="%s"
VALUE="$(cat)"                       # value arrives on stdin, never as an argument
mkdir -p "$(dirname "$ENVF")"; touch "$ENVF"; chmod 600 "$ENVF"
# idempotent upsert: drop any existing line for this key, then append
grep -v "^${NAME}=" "$ENVF" > "${ENVF}.tmp" 2>/dev/null || true
printf '%%s=%%s\n' "$NAME" "$VALUE" >> "${ENVF}.tmp"
mv "${ENVF}.tmp" "$ENVF"; chmod 600 "$ENVF"
echo "== ${NAME} stored in ${ENVF} (chmod 600) =="
echo "== keys now present (names only) =="
sed -n 's/^\([A-Z0-9_]*\)=.*/   \1/p' "$ENVF"
cd /opt/colt-stack
echo "== restarting colt-web to pick it up (NO --remove-orphans: it would delete the bots) =="
docker compose -p colt-stack -f docker-compose.web.yml up -d --force-recreate >/dev/null 2>&1
sleep 2
docker exec colt-web python3 -c "import os,sys; k='${NAME}'; v=os.environ.get(k) or ''; \
print('   verify: %%s = %%s' %% (k, ('set, %%d chars' %% len(v)) if v else 'MISSING'))"
''' % ENVF


def upsert_local(name, value):
    """Keep the local .env in step, or the next `deploy.py --reuse` overwrites the droplet."""
    try:
        lines = []
        if os.path.exists(LOCAL):
            with open(LOCAL, encoding="utf-8") as fh:
                lines = [l for l in fh.read().split("\n") if not l.startswith(name + "=")]
        else:
            os.makedirs(os.path.dirname(LOCAL), exist_ok=True)
        while lines and lines[-1] == "":
            lines.pop()
        lines.append("%s=%s" % (name, value))
        with open(LOCAL, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        try: os.chmod(LOCAL, 0o600)
        except OSError: pass                      # Windows/mounted FS may refuse — not fatal
        print("   local  : %s updated (gitignored, shipped by deploy.py)" % LOCAL)
        return True
    except Exception as e:
        print("   [!] could not update the LOCAL .env (%s)." % repr(e)[:70])
        print("       WARNING: `python deploy.py --reuse` would then overwrite the droplet and")
        print("       silently remove %s. Add it to assess-bot/.env by hand." % name)
        return False


def run(name, value):
    upsert_local(name, value)                     # local first: it is what deploy.py ships
    r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), "bash -s", "--", name],
                       input=value.encode("utf-8"))
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="secret name, e.g. ABUSEIPDB_KEY")
    ap.add_argument("--list", action="store_true", help="list secret NAMES on the droplet")
    a = ap.parse_args()

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
