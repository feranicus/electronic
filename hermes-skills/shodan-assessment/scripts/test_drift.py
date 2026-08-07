#!/usr/bin/env python3
"""test_drift.py - the config-drift check must catch the REAL fault and never a healthy box.

WHY THIS TEST EXISTS. The first version of `config_drift` md5'd `caddy adapt` against the admin
API's `GET /config/` and failed a perfectly healthy staging box, twice, blocking a deploy. Those
are two SERIALISATIONS of one config: `adapt` emits the adapter's JSON, the admin API re-marshals
from parsed Go structs, so key order differs and defaults are filled in. Byte equality was never
achievable - the check could only ever say DRIFT.

The tell was in its own output: the two hashes were IDENTICAL before and after a reboot. Caddy
re-reads its config at start, so a genuinely stale process CANNOT survive a restart. A check whose
result is unchanged by the event that would fix the fault is not measuring the fault.

So the check now compares WHAT IS SERVED - matched hostnames and terminal handlers - which is
stable under re-serialisation and is exactly what changes when a block is truncated or replaced.
"""
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "deploy", "caddyguard", "agent.py"))
_s = importlib.util.spec_from_file_location("cg_agent", AGENT)
ag = importlib.util.module_from_spec(_s)
_s.loader.exec_module(ag)

FAILED = []


def ok_(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        FAILED.append(msg)


def cfg(sites):
    routes = [{"match": [{"host": [h]}],
               "handle": [{"handler": "subroute", "routes": [{"handle": [x]}]}]}
              for h, x in sites]
    return {"apps": {"http": {"servers": {"srv0": {"listen": [":443"], "routes": routes}}}}}


def proxy(dial):
    return {"handler": "reverse_proxy", "upstreams": [{"dial": dial}]}


FILES = {"handler": "file_server"}
PROD = [("cybergod.ai", proxy("colt-web:8000")), ("jobhuntwow.com", proxy("jhw-web:8000"))]


def md5(o):
    return hashlib.md5(json.dumps(o, separators=(",", ":")).encode()).hexdigest()[:12]


print("=" * 78)
print("  config drift - semantic, not byte-equality")
print("=" * 78)

# 1. A HEALTHY BOX. Same config, different serialisation: reordered keys plus the defaults the
#    admin API fills in. This is the false positive that blocked a deploy twice.
disk = cfg(PROD)
run = json.loads(json.dumps(disk, sort_keys=True))
run["admin"] = {"listen": "localhost:2019"}
run["logging"] = {"logs": {"default": {"level": "INFO"}}}
run["apps"]["http"]["servers"]["srv0"]["automatic_https"] = {}
ok_(md5(disk) != md5(run), "a hash comparison DOES flag a healthy box (this is why it was wrong)")
ok_(ag._served(disk) == ag._served(run), "the semantic check does NOT flag a healthy box")

# 2. THE REAL 2026-08-07 SHAPE: the file lost jobhuntwow's block, the process still serves it.
truncated = cfg(PROD[:1])
ok_(ag._served(truncated) != ag._served(run), "a truncated block on disk IS caught")
d_hosts, _ = ag._served(truncated)
r_hosts, _ = ag._served(run)
ok_(r_hosts - d_hosts == {"jobhuntwow.com"}, "and it names the host that went missing")

# 3. THE OTHER REAL SHAPE: right hosts, WRONG handler - a reverse-proxy app served by file_server,
#    which returns an empty 200 and looks perfectly healthy to a status-code probe.
wrong = cfg([("cybergod.ai", proxy("colt-web:8000")), ("jobhuntwow.com", FILES)])
ok_(ag._served(wrong) != ag._served(run), "the right host with the WRONG handler is caught")
_, d_h = ag._served(wrong)
_, r_h = ag._served(run)
ok_("proxy:jhw-web:8000" in r_h - d_h and "file_server" in d_h - r_h,
   "and it names both sides of the handler difference")

# 4. A REBOOT CANNOT FIX A SERIALISATION DIFFERENCE - the proof the old check was broken.
ok_(ag._served(disk) == ag._served(run),
   "identical before and after a restart means it was never drift")

# 5. It must not crash on the shapes it will really meet.
ok_(ag._served({}) == (set(), set()), "an empty config yields empty sets, no exception")
ok_(ag._served({"apps": {"http": {"servers": {}}}}) == (set(), set()), "no servers is not a fault")

print("  semantic drift: correct in both directions")

# ---------------------------------------------------------------------------------------------
# HOP 1: THE BIND MOUNT. This is the hop that was NOT checked, and it is how a correct file and a
# dead site coexist. /etc/caddy/Caddyfile is a single-FILE mount, so it is pinned to an INODE.
# Anything replacing the file (mv, sed -i, tmp+rename) leaves the container reading the OLD inode:
#   * `caddy validate` passes  - it validates a freshly-mounted temp copy of the NEW text
#   * `caddy reload`  succeeds - and loads the OLD bytes
#   * the semantic drift check passes - BOTH its sides read from inside the container
# Three green lights over a dead site. Only a host-vs-container comparison can see it.
print()
print("=" * 78)
print("  bind-mount staleness - the hop that reported success over a dead site")
print("=" * 78)

CALLS = []


def fake_sh(cmd, **kw):
    CALLS.append(cmd)

    class R:
        returncode = 0
        stdout = ""
        stderr = ""
    r = R()
    if cmd[:2] == ["docker", "exec"] and "sha256sum" in cmd:
        r.stdout = "%s  /etc/caddy/Caddyfile" % STATE["container_sees"]
    elif cmd[:2] == ["docker", "restart"]:
        STATE["container_sees"] = STATE["host"]          # a restart re-resolves the mount
    elif cmd[:2] == ["docker", "exec"]:
        r.returncode = 0
    return r


STATE = {"host": "a" * 64, "container_sees": "a" * 64}
ag.sh = fake_sh
ag._sha_host = lambda p: STATE["host"]
ag.time = type("T", (), {"sleep": staticmethod(lambda n: None)})()

ok, msg = ag.mount_sync("videodead-caddy-1", fix=False)
ok_(ok, "matching hashes -> healthy: %s" % msg)

STATE["container_sees"] = "b" * 64                        # the inode was replaced
ok, msg = ag.mount_sync("videodead-caddy-1", fix=False)
ok_(not ok and "STALE MOUNT" in msg, "a replaced inode IS detected: %s" % msg)
ok_(not any(c[:2] == ["docker", "restart"] for c in CALLS),
    "fix=False never restarts - a read-only check must not blip every vhost")

CALLS.clear()
ok, msg = ag.mount_sync("videodead-caddy-1", fix=True)
ok_(ok and "repaired" in msg, "fix=True restarts and re-verifies: %s" % msg)
ok_(any(c[:2] == ["docker", "restart"] for c in CALLS), "and it actually restarted the proxy")

STATE["container_sees"] = "c" * 64


def stubborn(cmd, **kw):
    r = fake_sh(cmd, **kw)
    STATE["container_sees"] = "c" * 64                    # restart does NOT fix it
    if cmd[:2] == ["docker", "exec"] and "sha256sum" in cmd:
        r.stdout = "%s  /etc/caddy/Caddyfile" % STATE["container_sees"]
    return r


ag.sh = stubborn
ok, msg = ag.mount_sync("videodead-caddy-1", fix=True)
ok_(not ok and "STILL STALE" in msg,
    "an unfixable mount is reported, never silently passed: %s" % msg[:60])

ag.sh = fake_sh
ok_(ag.mount_sync("", fix=False)[0], "no container -> nothing to compare, not a failure")
ag._sha_in_container = lambda c: ""
ok_(ag.mount_sync("videodead-caddy-1", fix=False)[0],
    "unreadable container file -> SKIP, never a fabricated verdict")

print("=" * 78)
if FAILED:
    print("  %d CHECK(S) FAILED" % len(FAILED))
    sys.exit(1)
print("  ALL CHECKS PASSED - the mount hop can no longer report success over stale bytes")
print("=" * 78)
