#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""modelcheck.py — does the chain I am ABOUT TO SHIP exist on the inference API? Ask before deploying.

    python modelcheck.py            exit 0 if every model in enrich._FALLBACKS is in the catalog

A BUILDING BLOCK of ship.py, never a second command (operating principle 7).

WHY THIS EXISTS, AND WHY IT RUNS BEFORE THE DEPLOY AND NOT AFTER.
    ship.py already asserts the chain exists in the live catalog - in do_verify(), which is STEP 5.
    By then the image is built, scanned, pushed through the staging gate and running in production.
    A model id that does not exist is therefore discovered by production, and the operator's repair
    is a second full deploy.

    That matters now because the chain head is being replaced (deepseek-3.2 is deprecated), and
    this repository already has the scar for exactly this mistake: `deepseek-v4-flash` was taken
    from DigitalOcean's PRICING PAGE, put at the head of the chain, and 404'd on every assessment
    for days while the chain silently degraded to the next model. A MARKETING NAME IS NOT AN API
    ID, and the only authority on an API id is the API.

WHERE IT ASKS FROM. The catalog needs the inference key, which lives in colt-web's environment and
    nowhere on this PC - that is why model_probe.py printed "catalog unavailable - skipping" on
    every local run for weeks, which is a check that cannot see its subject. So the question is
    asked INSIDE the running container, over one ssh session (class 43), against the REPO's chain
    rather than the container's: the container is still running the OLD image, and its own chain is
    not the thing being verified.

WHAT IT DOES NOT DO. It does not pick a model. `deepseek-v4-flash` got into the chain because a
    name looked right; a resolver that chooses the "closest" catalog entry would be the same
    mistake with more machinery. It reports what is missing, prints the ids that DO exist for that
    vendor, and stops.
"""
import base64
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
SSH = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
       "-o", "ConnectTimeout=15", "-o", "BatchMode=yes",
       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]

ENRICH = os.path.join(HERE, "hermes-skills", "shodan-assessment", "scripts", "enrich.py")


def repo_chain():
    """The chain as THIS CHECKOUT defines it. Read from the source rather than imported, because
    importing enrich.py pulls a dependency tree this script does not need and the operator's Python
    may not hold."""
    try:
        with open(ENRICH, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("_FALLBACKS = ["):
                    body = line.split("[", 1)[1].rsplit("]", 1)[0]
                    return [m.strip().strip("\"'") for m in body.split(",") if m.strip()]
    except OSError as e:
        raise SystemExit("[X] cannot read the chain from %s: %s" % (ENRICH, e))
    raise SystemExit("[X] no _FALLBACKS line in %s - the chain moved, and this check is blind"
                     % ENRICH)


# The remote half. It prints a verdict line per model and nothing else that a parser could confuse
# with one. `%s` is the chain, comma-joined, in argv.
REMOTE = r'''
import json, os, sys, urllib.request
want = [m for m in sys.argv[1].split(",") if m]
key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DO_INFERENCE_KEY") or ""
base = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
if not key:
    print("UNKNOWN no inference key inside this container"); raise SystemExit(3)
try:
    req = urllib.request.Request(base + "/models",
                                 headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=25) as r:
        ids = sorted({str(m.get("id")) for m in (json.load(r).get("data") or []) if m.get("id")})
except Exception as e:
    print("UNKNOWN catalog unreachable: %s: %s" % (type(e).__name__, e)); raise SystemExit(3)
print("CATALOG %d model(s) visible on %s" % (len(ids), base))
missing = []
for m in want:
    if m in ids:
        print("OK      %s" % m)
    else:
        print("MISSING %s" % m)
        missing.append(m)
for m in missing:
    # NAME THE ALTERNATIVES (class 26). "missing" alone sends the operator to guess again, which
    # is how the wrong id got in. Show what the vendor actually serves.
    stem = m.split("-")[0].lower()
    near = [i for i in ids if i.lower().startswith(stem)]
    print("NEAR    %s -> %s" % (m, ", ".join(near) if near else "(nothing from that vendor)"))
raise SystemExit(1 if missing else 0)
'''


def main():
    chain = repo_chain()
    print("  === modelcheck: does the chain in THIS checkout exist on the inference API? ===")
    print("  chain : %s" % " -> ".join(chain))
    b64 = base64.b64encode(REMOTE.encode("utf-8")).decode("ascii")
    # THE SCRIPT MUST REACH THE CONTAINER, not just the host. `docker exec <ct> <path>` resolves
    # the path INSIDE the container (class 55), where a host temp file does not exist - so the
    # script is piped to `python3 -` on stdin and the chain travels in argv. One ssh session.
    cmd = ("S=$(mktemp) && printf %%s '%s' | base64 -d > \"$S\" && "
           "docker exec -i colt-web python3 - '%s' < \"$S\"; rc=$?; rm -f \"$S\"; exit $rc"
           % (b64, ",".join(chain)))
    try:
        r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:
        print("  [!] could not ask the catalog (%s) - NOT a pass, and not a finding about the "
              "chain either." % type(e).__name__)
        return 3
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    for line in out.splitlines():
        print("  " + line.rstrip())
    if r.returncode == 0 and re.search(r"^OK\s", out, re.M):
        print("  every model in the chain exists on the API")
        return 0
    if r.returncode == 1:
        print("  [X] a model in the chain does NOT exist. Fix enrich.py::_FALLBACKS using the ids")
        print("      printed above - a marketing name is not an API id.")
        return 1
    # AN UNKNOWN IS NOT A PASS, and it is not a failure about the chain either. Say which.
    print("  [!] the catalog could not be read (rc=%s), so the chain is UNVERIFIED." % r.returncode)
    return 3


if __name__ == "__main__":
    sys.exit(main())
