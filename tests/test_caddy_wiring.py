"""The deploy must rewrite ONLY its own block in the shared Caddyfile.

THE INCIDENT (2026-08-14). Every `python ship.py` ended with a Telegram alert:

    CADDY: the LIVE shared config is DAMAGED
    jhw:jobhuntwow 14 lines, 3 open vs 2 close
    ... the open question is WHICH project wrote this, because it will do it again.

The answer was OURS. `deploy_web_direct.py` ran, after the correct marker-based delete, a blunt

    sed -i '/cybergod/,/^}/d' "$CF"

which deletes from the FIRST line containing "cybergod" to the next `}` at column 0. Line 14 of
jobhuntwow.caddy is a COMMENT reading "1:1 with cybergod.ai's traffic board", so the range opened
inside somebody else's block and ran to the closing brace of `jobhuntwow.com {`: 26 lines became
14 and the braces went unbalanced. caddyguard repaired it every time, so the only visible symptom
was an alert that looked benign - which is exactly how a real one gets ignored.

WHAT THIS PINS: run the deploy's ACTUAL caddy-wiring commands, extracted from the script rather
than retyped, against a monolith built from the REAL committed blocks, and assert that every block
except ours is byte-identical afterwards.

Stdlib only, and it needs `sed` - skipped cleanly where that is unavailable so it can never be a
false failure on a machine without it.

THE SECOND INCIDENT (2026-10-15). The wiring grew two lines on the front that ASK THE CONTAINER
where its Caddyfile actually is (`docker ps` then `docker inspect`, per defect class 39 - never
assume a path or a compose prefix). Correct in production, and it silently broke this test: the
extracted segment re-assigned `$CF` over the temp file the fixture had just prepared, and on any
machine without a docker binary the whole sequence died at `rc 127` under `set -e`. Nothing noticed
because the one gate that would have run it had been failing earlier, at gitleaks.

So the fix is to SIMULATE docker, not to cut those lines out of the segment (defect class 20 - a
skip hides the defect from the machine that needs it, and trimming the segment would quietly stop
covering the shipped discovery). A stub `docker` answers `ps` with a container name and `inspect`
with the fixture's own path, and the test asserts the stub was really called - so if the deploy ever
goes back to assuming a path, this fails instead of passing vacuously.
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile

import pytest

from test_teamwork import shell_harness_allowed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CADDY_DIR = os.path.join(ROOT, "deploy", "caddy")
DEPLOY = os.path.join(ROOT, "deploy_web_direct.py")

# The wiring is a bash SEQUENCE sharing a shell variable, so it needs a real POSIX shell as well as
# sed. `shutil.which("bash")` is NOT that gate and CLAUDE.md says so: on the operator's Windows box
# that resolves to WSL's bash.exe, which tests the emulation rather than the droplet. ONE HOME for
# the decision, shared with the teamlock harness. So this whole module is skipped on his PC and it
# is CI and the droplet that exercise it - worth knowing before trusting a green local run.
_SHELL_OK, _SHELL_WHY = shell_harness_allowed()
pytestmark = pytest.mark.skipif(not _SHELL_OK or shutil.which("sed") is None,
                                reason=_SHELL_WHY or "needs sed; not present on this machine")


def _docker_stub(work, cf):
    """A fake `docker` on PATH that points the wiring at `cf`, plus the env to run it with.

    The shipped segment asks the container where its Caddyfile is mounted. That is the right
    behaviour and it must stay under test, so rather than removing those two lines from what is
    measured, this answers them. Returns (env, logpath); the log is how the test proves the stub was
    actually consulted (defect class 12 - prove the fixture, or a wiring that went back to assuming
    a path would read as a pass).
    """
    binf = os.path.join(work, "bin")
    os.makedirs(binf, exist_ok=True)
    log = os.path.join(work, "docker.log")
    stub = os.path.join(binf, "docker")
    with open(stub, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('#!/bin/sh\n'
                 'echo "$@" >> "$DOCKER_STUB_LOG"\n'
                 'case "$1" in\n'
                 '  ps)      echo videodead-caddy-1 ;;\n'
                 # The real `docker inspect --format` prints the mount SOURCE on the host. Here that
                 # is the fixture's Caddyfile, which is the whole point: the wiring then rewrites a
                 # file the test controls instead of a real shared proxy's config.
                 '  inspect) printf \'%s\\n\' "$DOCKER_STUB_CF" ;;\n'
                 '  *)       echo "stub docker: unexpected verb $1" >&2; exit 97 ;;\n'
                 'esac\n')
    os.chmod(stub, os.stat(stub).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    env = dict(os.environ)          # INHERIT, override only what the test needs
    env["PATH"] = binf + os.pathsep + env.get("PATH", "")
    env["DOCKER_STUB_LOG"] = log
    env["DOCKER_STUB_CF"] = cf
    return env, log


def _assert_stub_was_consulted(log):
    verbs = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
    assert "ps" in verbs and "inspect" in verbs, (
        "the wiring no longer ASKS the container where its Caddyfile is mounted (stub saw: %r). "
        "That is defect class 39 - a path assumed instead of measured - and it is also the reason "
        "this test can trust the file it just inspected." % verbs)


def _wiring_script():
    """The caddy-wiring SEQUENCE the deploy actually runs, taken from the RENDERED remote script.

    THE ORIGINAL REASONING STANDS and is kept above: a range delete keyed on a word that appears in
    another project's prose destroyed jobhuntwow's block on every deploy. That is still what this
    file pins.

    REWRITTEN 2026-09-10, per defect class 17. The doctrine changed underneath it, so the test
    changed with it rather than being deleted. The deploy no longer uses `sed -i` ANYWHERE:
    `sed -i` does not edit in place, it writes a temp file and renames it, which gives the file a
    NEW INODE. /etc/caddy/Caddyfile is a single-FILE bind mount, so the proxy follows the OLD inode
    and reads a file nobody can see; the only repair is restarting the shared proxy that owns :443
    for every domain, which is how one ship briefly dropped all six sites. The wiring is now `sed`
    as a FILTER into a shell variable, a size floor, and `>` to truncate the existing inode.

    So the extractor takes the whole SEGMENT rather than individual commands: these lines share a
    shell variable and mean nothing run separately. Rendered, not retyped, for the same reason as
    before - and reading the rendered bash also avoids the escaping trap that made an earlier
    version of this extractor match the Python source instead of the script.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("_dwd_caddy", DEPLOY)
    dwd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dwd)
    lines = dwd.remote(True).splitlines()
    start = next((i for i, l in enumerate(lines)
                  if "wire cybergod.ai into the shared caddy" in l), None)
    end = next((i for i, l in enumerate(lines)
                if start is not None and i > start and "caddy validate" in l), None)
    assert start is not None and end is not None, (
        "the caddy-wiring segment could not be located in the rendered deploy script; its markers "
        "moved, so this test is no longer reading what ships. Re-anchor it, do not delete it.")
    return "\n".join(l for l in lines[start + 1:end] if not l.strip().startswith("#"))


def _blocks():
    out = {}
    for f in sorted(os.listdir(CADDY_DIR)):
        if f.endswith(".caddy"):
            out[f] = open(os.path.join(CADDY_DIR, f), encoding="utf-8").read()
    return out


def _monolith(blocks):
    base = ('# _base — the shared proxy\n{\n\temail ops@example.com\n}\n\n'
            'godeyes.ai {\n\trespond "hi"\n}\n\n')
    return base + "\n".join(blocks.values())


def _braces(text):
    return text.count("{"), text.count("}")


def _block_of(text, name):
    m = re.search(r"^# %s BEGIN.*?^# %s END$" % (re.escape(name), re.escape(name)),
                  text, re.S | re.M)
    return m.group(0) if m else ""


def test_the_wiring_touches_only_our_own_block():
    blocks = _blocks()
    assert "jobhuntwow.caddy" in blocks and "cybergod.caddy" in blocks, sorted(blocks)
    work = tempfile.mkdtemp(prefix="caddywire-")
    try:
        cf = os.path.join(work, "Caddyfile")
        with open(cf, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_monolith(blocks))
        before = {n: _block_of(open(cf, encoding="utf-8").read(), n)
                  for n in ("jhw:jobhuntwow", "polara:klima")}

        script = _wiring_script()
        assert "$CF" in script, "the wiring no longer names $CF - the extractor is reading the " \
                                "wrong segment and this test would pass against nothing"
        # PROVE THE INODE SURVIVES. That is the whole point of the rewrite: the old `sed -i` gave
        # the file a new one and the shared proxy kept reading the old. On a filesystem without
        # inode numbers this is 0 and the comparison is vacuous, so it is only asserted when real.
        ino_before = os.stat(cf).st_ino
        # cwd=ROOT because the wiring does `cat deploy/caddy/cybergod.caddy`, a repo-relative path.
        # The appended block is part of the extracted segment now, so the test no longer appends it.
        env, log = _docker_stub(work, cf)
        subprocess.run(["bash", "-c", "set -e\nCF=%s\n%s" % (cf, script)],
                       cwd=ROOT, check=True, timeout=60, env=env)
        _assert_stub_was_consulted(log)

        after_text = open(cf, encoding="utf-8").read()
        if ino_before:
            assert os.stat(cf).st_ino == ino_before, (
                "the wiring REPLACED the file's inode. /etc/caddy/Caddyfile is a single-file bind "
                "mount, so the running proxy would keep reading the old one and the only repair is "
                "restarting the process that owns :443 for every domain on the box.")
        assert blocks["cybergod.caddy"].strip().splitlines()[0] in after_text, \
            "our own block is missing after the wiring - it deleted and never re-added it"
        for name, was in before.items():
            if not was:
                continue
            now = _block_of(after_text, name)
            assert now == was, (
                "the deploy altered %s, which belongs to another project. This is the recurring "
                "'LIVE shared config is DAMAGED' alert: %d lines -> %d, braces %s -> %s"
                % (name, was.count("\n") + 1, now.count("\n") + 1, _braces(was), _braces(now)))

        o, c = _braces(after_text)
        assert o == c, "the whole file is unbalanced after wiring: %d open vs %d close" % (o, c)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_no_range_delete_keyed_on_a_word_that_appears_in_prose():
    """The specific shape that caused it. A marker delete is bounded and unambiguous; a delete
    that starts at any line MENTIONING a word will eventually start inside somebody else's
    comment - and here it already did, on every deploy."""
    # Reads the RENDERED wiring now, for the same reason as the test above: the deploy stopped
    # using `sed -i`, so an extractor looking for that spelling found nothing and this check went
    # quietly vacuous. A range delete is the shape that hurts, whether or not the -i flag is on it.
    ranges = re.findall(r"sed[^\n]*?(/[^/\n]*/\s*,\s*/[^/\n]*/)\s*d", _wiring_script())
    assert ranges, ("no range delete found in the wiring at all. That is either a real improvement "
                    "or a broken extractor, and the two must not look alike - re-read the segment.")
    bad = [r for r in ranges if "BEGIN" not in r or "END" not in r]
    assert not bad, (
        "a range delete is not bounded by BEGIN/END markers, so it can start inside another "
        "project's block: %s" % bad)


def test_our_own_block_is_still_actually_replaced():
    """The other direction: removing the blunt sed must not stop the wiring from working."""
    blocks = _blocks()
    work = tempfile.mkdtemp(prefix="caddywire2-")
    try:
        cf = os.path.join(work, "Caddyfile")
        stale = blocks["cybergod.caddy"].replace("colt-web:8000", "STALE-UPSTREAM:9999")
        with open(cf, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_monolith(dict(blocks, **{"cybergod.caddy": stale})))
        # The wiring now removes AND re-adds our block in one sequence (the `cat` is inside it), so
        # this no longer appends the fresh block by hand. cwd=ROOT because that cat is a
        # repo-relative path.
        env, log = _docker_stub(work, cf)
        subprocess.run(["bash", "-c", "set -e\nCF=%s\n%s" % (cf, _wiring_script())],
                       cwd=ROOT, check=True, timeout=60, env=env)
        _assert_stub_was_consulted(log)
        end = open(cf, encoding="utf-8").read()
        assert "STALE-UPSTREAM" not in end, "the old cybergod block was not removed"
        assert end.count("# colt:cybergod BEGIN") == 1, "the block was duplicated"
        assert "colt-web:8000" in end, "the fresh block was not installed"
    finally:
        shutil.rmtree(work, ignore_errors=True)
