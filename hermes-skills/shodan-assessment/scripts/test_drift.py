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

# =================================================================================================
# [E] A LIVE PROXY MAY NEVER BE EMPTIED BY AN AUTOMATIC PROCESS (10 Aug 2026).
#
# Caused by the check written to detect the very thing it caused. A staging check ran
# `agent.py assemble --apply` on a box whose /opt/caddyguard/blocks/ was EMPTY -- staging composes
# its Caddyfile directly and is NOT fragment-managed -- so the assembly contained nothing, apply()
# wrote it, Caddy carried on serving from memory, and the reboot detonated it:
# post_reboot_proxy_routes 000, roster MISSING cybergod.ai, and config_drift reporting OK on
# "0 host(s), 0 handler(s)". The Caddyfile hash was 01ba4719c80b = the sha256 of ONE NEWLINE.
# The guard lives in apply(), so it protects every caller rather than the one check that failed.
# =================================================================================================
print("")
print("=" * 78)
print("[E] a live proxy may never be emptied by an automatic process")

import tempfile as _tf
import types as _ty

_d = _tf.mkdtemp()
_cf = os.path.join(_d, "Caddyfile")
_REAL = ("{\n\tauto_https off\n\tadmin localhost:2019\n}\n\n"
         ":8080 {\n\treverse_proxy colt-web:8000\n}\n\n"
         "cybergod.ai {\n\treverse_proxy colt-web:8000\n}\n")
open(_cf, "w").write(_REAL)

# LIVE is bound from the environment at import, so the module is re-imported against a temp file.
os.environ["CADDYFILE"] = _cf
_s2 = importlib.util.spec_from_file_location("cg_agent_empty", AGENT)
ag2 = importlib.util.module_from_spec(_s2)
_s2.loader.exec_module(ag2)

ok_(ag2.site_blocks(_REAL) == [":8080", "cybergod.ai"],
    "site_blocks reads site headers and ignores the global options block")
ok_(ag2.site_blocks("\n") == [] and ag2.site_blocks("") == [],
    "an empty file has no sites (01ba4719c80b is the sha256 of one newline)")
ok_(ag2.site_blocks("# cybergod.ai {\n") == [],
    "a commented-out site header is not a site")

ag2.container = lambda *a, **k: "staging-caddy"
ag2.acceptable = lambda t, c=None: (True, "valid")
ag2.backup = lambda w: "/tmp/bak"
ag2.mount_sync = lambda c: (True, "fresh")
ag2.sh = lambda cmd, **kw: _ty.SimpleNamespace(stdout="running", stderr="", returncode=0)

_ok, _msg = ag2.apply("\n", "assemble")
ok_(_ok is False and "NO sites" in _msg, "an EMPTY assembly is REFUSED over a live proxy")
ok_(open(_cf).read() == _REAL, "and the live file is untouched by the refusal")

_ok, _ = ag2.apply(_REAL + "\nhttp://probe.invalid {\n\trespond \"x\" 200\n}\n", "probe")
ok_(_ok is True and "probe.invalid" in open(_cf).read(),
    "a legitimate ADDITION still applies - this is not a blanket freeze")

_ok, _ = ag2.apply(_REAL, "restore")
ok_(_ok is True and open(_cf).read() == _REAL,
    "the snapshot restores byte-for-byte (the revert path the probe depends on)")

os.environ["CADDYGUARD_ALLOW_EMPTY"] = "1"
_ok, _ = ag2.apply("\n", "deliberate")
del os.environ["CADDYGUARD_ALLOW_EMPTY"]
ok_(_ok is True, "CADDYGUARD_ALLOW_EMPTY is the deliberate, explicit escape")

# An EMPTY running config is degenerate, not the absence of drift (gemma + kimi, same run).
# RUN the command; do not grep the source. The first version of this assertion searched for the
# message string, so a mutation that neutered the CONDITION (`if False:`) left the string in place
# and the check went green on a file carrying the exact defect. Third time this session that a
# static assertion could not see the thing it was aimed at.
import io as _io
import contextlib as _cl


def _drift_says(disk_json, run_json):
    ag2.container = lambda *a, **k: "staging-caddy"
    ag2.mount_sync = lambda c, fix=True: (True, "fresh")

    def _sh(cmd, **kw):
        j = " ".join(cmd)
        if "adapt" in j:
            return _ty.SimpleNamespace(stdout=disk_json, stderr="", returncode=0)
        if "2019" in j:
            return _ty.SimpleNamespace(stdout=run_json, stderr="", returncode=0)
        return _ty.SimpleNamespace(stdout="running", stderr="", returncode=0)

    ag2.sh = _sh
    buf = _io.StringIO()
    with _cl.redirect_stdout(buf):
        rc = ag2.cmd_drift()
    return rc, buf.getvalue()


_EMPTY = json.dumps({"apps": {"http": {"servers": {}}}})
_LIVE = json.dumps({"apps": {"http": {"servers": {"srv0": {"routes": [
    {"match": [{"host": ["cybergod.ai"]}],
     "handle": [{"handler": "reverse_proxy", "upstreams": [{"dial": "colt-web:8000"}]}]}]}}}}})

_rc, _out = _drift_says(_EMPTY, _EMPTY)
ok_(_rc == 1 and "NO hosts" in _out,
    "an EMPTY running config is a FAILURE, not 'no drift' (empty == empty compares fine and "
    "means the proxy is serving nothing)")
_rc, _out = _drift_says(_LIVE, _LIVE)
ok_(_rc == 0 and _out.startswith("OK"),
    "a healthy box that really does serve its file is still a clean pass")
_rc, _out = _drift_says(_LIVE, _EMPTY)
ok_(_rc == 1, "file serves a host but the running process serves none -> caught")

# And the stagegate check must never again rebuild from an assumption about where this box keeps
# its configuration, nor merely hope that its restore worked.
_sg = open(os.path.normpath(os.path.join(HERE, "..", "..", "..", "stagegate.py")), encoding="utf-8").read()
_body = _sg[_sg.index("config_change_propagates"):]
ok_("agent.py assemble" not in _body,
    "the propagation check no longer rebuilds the config from fragments")
ok_("cmp -s /tmp/cg_snapshot.caddy" in _body, "it snapshots the live bytes and VERIFIES the restore")
ok_("NOT restored byte-for-byte" in _body, "a failed restore is a FAILURE, not a silent pass")


print("=" * 78)
if FAILED:
    print("  %d CHECK(S) FAILED" % len(FAILED))
    sys.exit(1)
print("  ALL CHECKS PASSED - the mount hop can no longer report success over stale bytes")
print("=" * 78)
