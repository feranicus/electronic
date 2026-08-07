#!/usr/bin/env python3
"""
govern.py — approve-then-execute remediation. BUILDING BLOCK; ship.py calls it on NO-GO.

THE EIGHT STEPS (the operator's design, implemented literally)
    1. The panel gives RCA + verdict + proposal      — model NAME shown against every line
    2. The operator approves (or declines)
    3. Execution is allowed on the TEST platform ONLY
    4. A 6-digit TOTP code (Google Authenticator) is required to execute
    5. The proposed action runs — on staging
    6. The staging checks are re-run
    7. The panel confirms whether the change actually worked
    8. The operator chooses: stop, or propagate to production (backup taken FIRST)

TWO THINGS MAKE THIS SAFE, AND NEITHER IS OPTIONAL
--------------------------------------------------
1. **The models never write shell.** They pick an action_id from a FIXED CATALOGUE below, with
   validated parameters. "Let the LLM run the commands it proposed" is otherwise a remote-code-
   execution primitive wearing a helpful hat, on a host carrying four live domains. The catalogue
   is the difference between an assistant and an incident. Anything not in it is refused, loudly,
   and shown to the operator as a manual step instead.
2. **TOTP proves a HUMAN is present.** Approval typed into a prompt can be automated away by the
   next script; a time-based code from a phone cannot. RFC 6238, stdlib only (hmac + base32), so
   it works with Google Authenticator / Authy / 1Password with no new dependency and no service to
   call. Enrol once: `python govern.py --enrol`.

WHY STAGING-ONLY EXECUTION IS THE WHOLE POINT
    Staging is a disposable twin holding synthetic data. A wrong action there costs a rebuild.
    The same action on production is the 2026-08-07 outage with a faster trigger. Production only
    ever receives a change that has been executed on staging, re-checked, re-reviewed, and then
    separately approved — and it is backed up first.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import struct
import subprocess
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(HERE, ".govern_totp")     # gitignored; chmod 600 on POSIX


# --------------------------------------------------------------------------- TOTP (RFC 6238)
def totp(secret_b32, when=None, step=30, digits=6):
    """Standard 6-digit TOTP. Deliberately hand-rolled from hmac+base32: it is ~15 lines, has no
    supply chain, and is verifiable against any authenticator app in ten seconds."""
    key = base64.b32decode(secret_b32.upper() + "=" * (-len(secret_b32) % 8))
    ctr = struct.pack(">Q", int((when or time.time()) // step))
    h = hmac.new(key, ctr, hashlib.sha1).digest()
    off = h[-1] & 0x0F
    code = (struct.unpack(">I", h[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def verify_totp(secret_b32, code, drift=1):
    """Accept the neighbouring windows too — phone clocks drift, and a governance gate that
    rejects a correct code because of 3 seconds of skew just teaches people to disable it."""
    now = time.time()
    got = "".join(ch for ch in str(code) if ch.isdigit())
    return any(hmac.compare_digest(totp(secret_b32, now + d * 30), got)
               for d in range(-drift, drift + 1))


def enrol():
    """One-time: generate a secret, print the otpauth:// URI to scan."""
    import secrets
    s = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
    with open(SECRET_FILE, "w") as fh:
        fh.write(s)
    try:
        os.chmod(SECRET_FILE, 0o600)
    except Exception:
        pass
    # NO %-FORMATTING HERE. The URI contains percent-ENCODED characters (%20), and Python read
    # "%2" as a format spec -> "TypeError: must be real number, not str". CLAUDE.md already carries
    # this rule from the `[100%]` progress line; the durable fix is not to escape it as %%20 but to
    # stop %-formatting a string that legitimately contains percent signs.
    who = urllib.parse.quote(os.environ.get("USERNAME") or "operator", safe="")
    uri = ("otpauth://totp/" + urllib.parse.quote("Cybergod governance:" + who, safe=":") +
           "?secret=" + s + "&issuer=Cybergod&algorithm=SHA1&digits=6&period=30")
    print("=" * 74)
    print("  TOTP ENROLMENT — scan this in Google Authenticator (or paste the secret)")
    print("=" * 74)
    print("  secret : %s" % s)
    print("  uri    : %s" % uri)
    print("\n  Saved to %s (chmod 600, gitignored — it never reaches the repo)." % SECRET_FILE)
    print("  Verify now: the current code is %s" % totp(s))
    return 0


def _secret():
    return open(SECRET_FILE).read().strip() if os.path.exists(SECRET_FILE) else ""


# --------------------------------------------------------------------------- action catalogue
# THE ONLY THINGS A MODEL MAY PROPOSE. Each entry: what it does, and the exact command, built from
# VALIDATED parameters — never from model-authored text. `prod` marks the ones that are also
# meaningful on production during step 8.
ACTIONS = {
    "restart_container": {
        "what": "Restart one container that is not running.",
        "params": {"name": r"^[a-zA-Z0-9_.-]{1,64}$"},
        "cmd": "docker restart {name} && sleep 5 && docker inspect -f '{{{{.State.Status}}}}' {name}",
        "prod": True,
    },
    "reassemble_proxy": {
        "what": "Rebuild the proxy config from the validated per-project fragments and reload.",
        "params": {},
        "cmd": "python3 /opt/caddyguard/agent.py assemble --apply",
        "prod": True,
    },
    "heal_proxy": {
        "what": "Run the caddyguard watchdog with self-heal.",
        "params": {},
        "cmd": "python3 /opt/caddyguard/agent.py check --heal",
        "prod": True,
    },
    "redeploy_web": {
        "what": "Rebuild and restart colt-web from the sources already on the host.",
        "params": {},
        "cmd": ("cd /opt/colt-stack && docker compose -p colt-stack -f docker-compose.web.yml "
                "up -d --build --force-recreate web"),
        "prod": False,        # production redeploys go through deploy_web_direct.py, not here
    },
    "set_env": {
        "what": "Set ONE runtime variable in the droplet env file and restart colt-web.",
        # The VALUE is never taken from the model — only the key it names, and the value the
        # OPERATOR types. A model that can write arbitrary env vars can write OPENAI_API_KEY.
        "params": {"key": r"^[A-Z][A-Z0-9_]{1,48}$"},
        "cmd": None,          # handled specially: prompts the operator for the value
        "prod": False,
    },
    "rerun_checks": {
        "what": "Re-run the staging health checks only. Changes nothing.",
        "params": {},
        "cmd": "true",
        "prod": False,
    },
}


def describe_catalogue():
    return "\n".join("  %-20s %s" % (k, v["what"]) for k, v in ACTIONS.items())


def validate(action_id, params):
    """(ok, message). Fails CLOSED: an unknown id or a parameter that does not match its pattern
    is refused and surfaced to the operator as a manual step."""
    import re
    spec = ACTIONS.get(action_id)
    if not spec:
        return False, "'%s' is not in the action catalogue — refusing. Do it manually." % action_id
    for key, pat in spec["params"].items():
        val = str((params or {}).get(key, ""))
        if not re.match(pat, val):
            return False, "parameter %s=%r does not match %s — refusing." % (key, val, pat)
    for extra in set((params or {}).keys()) - set(spec["params"].keys()):
        return False, "unexpected parameter %r — refusing." % extra
    return True, "ok"


# --------------------------------------------------------------------------- the loop
def _ask(prompt, valid=None):
    while True:
        a = input(prompt).strip().lower()
        if not valid or a in valid:
            return a
        print("   please answer one of: %s" % ", ".join(valid))


def run(verdict, staging_host, prod_host, ssh_script, rerun_checks, notify=None):
    """The interactive gate. `verdict` is quorum.py's dict. Returns one of:
       'stopped' | 'fixed-staging' | 'promote' """
    failed = verdict.get("failed") or []
    models = [m for m in (verdict.get("models") or []) if m.get("diagnosis")]

    print("\n" + "=" * 74)
    print("  GOVERNANCE — the panel has a proposal. Nothing has been executed.")
    print("=" * 74)
    if not failed:
        print("  No failed checks. Nothing to remediate.")
        return "stopped"

    # STEP 1 — RCA + verdict + proposal, WITH THE MODEL NAME ON EVERY LINE.
    print("\n  FAILED (%d):" % len(failed))
    for c in failed:
        print("    x %-26s %s" % (c.get("name"), str(c.get("detail"))[:90]))
    print("\n  WHO SAID WHAT (governance panel — 2 soldiers, 2 auditors, one per vendor):")
    for m in (verdict.get("models") or []):
        print("    %-8s %-18s %s" % ("[%s]" % m.get("role", "?")[:7], m.get("model", "?"),
                                     m.get("verdict", "?").upper()))
        if m.get("diagnosis"):
            print("             RCA : %s" % m["diagnosis"])
        if m.get("proposed_fix"):
            print("             FIX : %s" % m["proposed_fix"])
    if not models:
        print("\n  No model produced a diagnosis. Nothing to approve.")
        return "stopped"

    print("\n  Actions the panel is ALLOWED to execute (anything else is a manual step):")
    print(describe_catalogue())

    # STEP 2 — approval.
    print("\n  Execution would happen on the TEST platform ONLY: %s" % staging_host)
    print("  Production (%s) is NOT touched by anything in this step." % prod_host)
    if _ask("\n  Approve an action on STAGING? [y/n] ", ["y", "n"]) != "y":
        print("  Declined. Nothing executed.")
        return "stopped"

    aid = input("  action id (from the list above): ").strip()
    spec = ACTIONS.get(aid)
    params = {}
    if spec:
        for key in spec["params"]:
            params[key] = input("    %s: " % key).strip()
    ok, msg = validate(aid, params)
    if not ok:
        print("  REFUSED: %s" % msg)
        return "stopped"

    # STEP 4 — TOTP. Proves a human is present, right now.
    sec = _secret()
    if not sec:
        print("\n  No TOTP secret enrolled. Run:  python govern.py --enrol")
        print("  Refusing to execute without a second factor.")
        return "stopped"
    if not verify_totp(sec, input("  6-digit code from your authenticator: ")):
        print("  Code rejected. Nothing executed.")
        return "stopped"

    # STEP 5 — execute, on staging.
    if aid == "set_env":
        val = input("    value for %s (typed by YOU, never by a model): " % params["key"])
        cmd = ("touch /opt/colt-stack/assess-bot/.env && "
               "sed -i '/^%s=/d' /opt/colt-stack/assess-bot/.env && "
               "printf '%s=%%s\\n' %s >> /opt/colt-stack/assess-bot/.env && "
               "docker restart colt-web" % (params["key"], params["key"],
                                            json.dumps(val)))
    else:
        cmd = spec["cmd"].format(**params)
    print("\n  EXECUTING ON STAGING: %s" % cmd[:160])
    out, err, rc = ssh_script("set -x\n" + cmd + "\n", host=staging_host, timeout=900)
    print("  " + ((out or "") + (err or "")).strip().replace("\n", "\n  ")[:2000])
    print("  exit=%s" % rc)

    # STEP 6 — re-run the checks.
    print("\n  Re-running the staging checks...")
    gate2, digest2 = rerun_checks()
    print("\n" + (digest2 or "").replace("\n", "\n  "))

    # STEP 7 — the panel confirms whether it actually worked. (rerun_checks already asked them.)
    print("\n  RESULT AFTER THE FIX: %s" % gate2)
    if notify:
        notify("cybergod governance: staging remediation %s" % gate2,
               "Action: %s %s\nExit: %s\n\n%s" % (aid, params, rc, digest2))

    # STEP 8 — stop, or promote to production (with a backup taken first).
    if gate2 != "GO":
        print("  Staging still does not validate. Production is NOT eligible.")
        return "stopped"
    print("\n  Staging is GREEN. You may now:")
    print("    1  stop here (the fix stays on staging only)")
    print("    2  propagate to PRODUCTION — a backup is taken BEFORE anything changes")
    if _ask("  choice [1/2] ", ["1", "2"]) == "1":
        return "fixed-staging"
    if not spec.get("prod"):
        print("  '%s' is not permitted against production from here." % aid)
        print("  Commit the equivalent change and run `python ship.py` — that is the audited path.")
        return "fixed-staging"
    if not verify_totp(sec, input("  PRODUCTION action — 6-digit code again: ")):
        print("  Code rejected. Production untouched.")
        return "stopped"

    print("\n  Backing up production BEFORE the change...")
    bkp = ("set -e\nB=/root/govern-backup-$(date +%Y%m%d-%H%M%S)\nmkdir -p $B\n"
           "cp /opt/videodead/Caddyfile $B/ 2>/dev/null || true\n"
           "cp /opt/colt-stack/assess-bot/.env $B/ 2>/dev/null || true\n"
           "docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}' > $B/containers.txt\n"
           "tar czf $B.tgz -C $(dirname $B) $(basename $B) && rm -rf $B\n"
           "echo \"backup: $B.tgz ($(du -h $B.tgz | cut -f1))\"\n")
    out, err, rc = ssh_script(bkp, host=prod_host, timeout=300)
    print("  " + ((out or "") + (err or "")).strip().replace("\n", "\n  ")[:600])
    if rc != 0:
        print("  BACKUP FAILED — refusing to touch production without one.")
        return "stopped"

    print("\n  EXECUTING ON PRODUCTION: %s" % cmd[:160])
    out, err, rc = ssh_script("set -x\n" + cmd + "\n", host=prod_host, timeout=900)
    print("  " + ((out or "") + (err or "")).strip().replace("\n", "\n  ")[:2000])
    if notify:
        notify("cybergod governance: PRODUCTION change applied",
               "Action: %s %s\nExit: %s\nBackup taken first.\n" % (aid, params, rc))
    return "promote"


def main():
    ap = argparse.ArgumentParser(description="Approve-then-execute remediation (staging first).")
    ap.add_argument("--enrol", action="store_true", help="set up Google Authenticator (one time)")
    ap.add_argument("--test-code", metavar="CODE", help="check a code against the enrolled secret")
    a = ap.parse_args()
    if a.enrol:
        return enrol()
    if a.test_code:
        s = _secret()
        if not s:
            print("not enrolled — run: python govern.py --enrol"); return 1
        print("VALID" if verify_totp(s, a.test_code) else "REJECTED")
        return 0
    print(__doc__)
    print("\nAction catalogue:\n" + describe_catalogue())
    print("\nEnrolled: %s" % ("yes" if _secret() else "NO — run: python govern.py --enrol"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
