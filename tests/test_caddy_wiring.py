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
"""
import os
import re
import shutil
import subprocess
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CADDY_DIR = os.path.join(ROOT, "deploy", "caddy")
DEPLOY = os.path.join(ROOT, "deploy_web_direct.py")

pytestmark = pytest.mark.skipif(shutil.which("sed") is None,
                                reason="sed is not available on this machine")


def _sed_commands():
    """The `sed -i ... "$CF"` lines the deploy actually runs, taken from the script.

    Extracted, never retyped: a test that reimplements the thing it checks proves nothing about
    what ships. Comments are stripped first, so the explanation of the REMOVED blunt sed (which
    quotes it verbatim) cannot be mistaken for a live command - that exact false positive has
    already cost this repo several cycles.
    """
    src = open(DEPLOY, encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    return re.findall(r'"(sed -i .*?\$CF\\")"', code)


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

        cmds = _sed_commands()
        assert cmds, "no sed commands found in deploy_web_direct.py - the extractor is broken"
        for c in cmds:
            subprocess.run(c.replace('\\"$CF\\"', cf), shell=True, check=True, timeout=60)
        # ...then the deploy appends our committed block back
        with open(cf, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(blocks["cybergod.caddy"])

        after_text = open(cf, encoding="utf-8").read()
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
    bad = [c for c in _sed_commands()
           if re.search(r"/[^/]*/,\s*/", c) and "BEGIN" not in c]
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
        for c in _sed_commands():
            subprocess.run(c.replace('\\"$CF\\"', cf), shell=True, check=True, timeout=60)
        mid = open(cf, encoding="utf-8").read()
        assert "STALE-UPSTREAM" not in mid, "the old cybergod block was not removed"
        with open(cf, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(blocks["cybergod.caddy"])
        end = open(cf, encoding="utf-8").read()
        assert end.count("# colt:cybergod BEGIN") == 1, "the block was duplicated"
        assert "colt-web:8000" in end, "the fresh block was not installed"
    finally:
        shutil.rmtree(work, ignore_errors=True)
