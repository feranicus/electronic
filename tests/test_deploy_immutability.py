"""test_deploy_immutability.py — what deploys must be the COMMIT, never the working tree.

THE INCIDENT (2026-08-07). One `python ship.py` run, one commit, three different results:

    local tests   : catalogue 253 keyed + 203 by-English = 456   PASS
    staging build : catalogue 253 keyed + 203 by-English = 456   PASS  (panel said GO)
    production    : catalogue 253 keyed + 213 by-English = 466   FAIL, 11 missing per locale

The same commit cannot produce three catalogues, and it did not: **it was never the same code.**
`pack()` read the WORKING DIRECTORY, and ship.py reads that directory five separate times —
test it, commit it, push it, pack it for staging, pack it again for production. An editor was
writing translation files across that window, so staging validated one tree and production tried
to build a different one ninety seconds later.

That is why staging passed and production failed, and it is why the AI panel's GO meant nothing
here: the panel reviewed a healthy staging box running code that production never received.

THE FIX: pack from `git archive HEAD`. The commit is immutable, so the tested tree, the staging
input, the production input and the safe-point tag are all provably the same bytes. A mid-flight
edit can no longer change what ships — it simply does not ship until it is committed.

PLATFORM PORTABILITY, the half of the fix the first version missed: `git archive` applies the same
end-of-line conversion as a checkout, so with `core.autocrlf=true` (the Windows default) it emits
CRLF while `git show` emits the raw LF blob. The artifact would then still differ by who packed it.
`git -c core.autocrlf=false -c core.eol=lf archive` forces repository bytes on every OS. Measured,
not read off the docs: `core.eol=lf` ALONE changes nothing — only `autocrlf=false` suppresses it.

COST NOTE: `pack()` runs `git archive` over the whole repo and is the slowest thing in this file
(~5s on a local disk, ~40s on a network mount). It used to be called SIX times here, on every
`python ship.py`. It is now called TWICE, and the second pack does double duty — see
`packed_dirty`. A test suite the operator waits through is a test suite that gets skipped.
"""
import os
import subprocess
import tarfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANDING = "webapp/frontend/src/pages/Landing.jsx"
MARKER = "\n// TRANSIENT EDIT MADE WHILE A SHIP WAS RUNNING\n"


def _heal():
    """Strip a marker left by a run that was KILLED before its teardown could run.

    `packed_dirty` edits a real tracked file and restores it in a `finally` — but a `finally`
    cannot survive SIGKILL, so a Ctrl-C or a CI timeout leaves the operator's working tree holding
    a stray comment in Landing.jsx. That happened twice while writing this. Self-healing on import
    costs one file read and means a killed run can never contaminate the next one, or the deploy.
    """
    p = os.path.join(ROOT, *LANDING.split("/"))
    try:
        s = open(p, encoding="utf-8").read()
    except OSError:
        return
    if MARKER in s:
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(s.replace(MARKER, ""))
        print("[heal] removed %d leftover test marker(s) from %s" % (s.count(MARKER), LANDING))


_heal()


def _mod():
    """Load deploy_web_direct's top-level definitions without running main()."""
    src = open(os.path.join(ROOT, "deploy_web_direct.py"), encoding="utf-8").read()
    src = src.split("def remote(")[0]
    ns = {"__name__": "dwd", "__file__": os.path.join(ROOT, "deploy_web_direct.py")}
    exec(compile(src, "deploy_web_direct.py", "exec"), ns)
    return ns


def _head(path):
    r = subprocess.run(["git", "show", "HEAD:" + path], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def _same(packed, head, path):
    """Assert equality, and when it fails say WHY in one line instead of a byte index.

    The first version reported `At index 52 diff: b'\\r' != b'\\n'`, which is a line-ending
    problem stated in the least useful possible way. A failure message that does not name the
    mechanism costs the next person the hour it cost me."""
    if packed == head:
        return
    if packed.replace(b"\r\n", b"\n") == head:
        raise AssertionError(
            "%s: the pack has CRLF line endings, HEAD has LF. `git archive` is applying "
            "core.autocrlf, so the artifact would differ between a Windows and a Linux packer. "
            "Pass -c core.autocrlf=false -c core.eol=lf." % path)
    raise AssertionError("%s: packed content differs from HEAD (not just line endings)" % path)


@pytest.fixture(scope="module")
def dwd():
    return _mod()


@pytest.fixture(scope="module")
def packed(dwd):
    """ONE pack of a clean HEAD, shared by every test that only needs to read it."""
    tgz = dwd["pack"]()
    try:
        with tarfile.open(tgz) as t:
            yield {"names": t.getnames(),
                   "read": {n: t.extractfile(n).read()
                            for n in t.getnames() if t.getmember(n).isfile()}}
    finally:
        os.unlink(tgz)


@pytest.fixture(scope="module")
def packed_dirty(dwd):
    """A SECOND pack, taken while the working tree is deliberately dirty.

    This one fixture proves two things at once, which is why there is no third pack:
      * a mid-flight edit cannot reach the deploy (the 2026-08-07 mechanism), and
      * two packs of the same HEAD are byte-identical (staging and production get the same bytes)
    — because a pack of HEAD taken from a DIRTY tree must equal a pack of HEAD taken from a clean
    one. If packing ever silently fell back to the working copy, both assertions break together.
    """
    target = os.path.join(ROOT, *LANDING.split("/"))
    before = open(target, "rb").read()
    try:
        with open(target, "ab") as fh:
            fh.write(MARKER.encode())
        tgz = dwd["pack"]()
        try:
            with tarfile.open(tgz) as t:
                yield {n: t.extractfile(n).read()
                       for n in t.getnames() if t.getmember(n).isfile()}
        finally:
            os.unlink(tgz)
    finally:
        # Restore in a finally: a harness that mutates real files and asserts first leaves the
        # tree holding the defect when it fails, and the next run fails for an unrelated reason.
        with open(target, "wb") as fh:
            fh.write(before)


def test_the_pack_is_the_commit_not_the_working_copy(packed):
    checked = 0
    for path in (LANDING, "webapp/backend/app/main.py", "colt_auth.py"):
        head = _head(path)
        if head is None:
            continue
        _same(packed["read"][path], head, path)
        checked += 1
    assert checked, "no files were compared - the test would pass vacuously"


def test_an_edit_during_a_ship_cannot_change_what_deploys(packed_dirty):
    """The actual 2026-08-07 mechanism, reproduced."""
    head = _head(LANDING)
    if head is None:
        pytest.skip("Landing.jsx not in HEAD")
    assert b"TRANSIENT EDIT" not in packed_dirty[LANDING], "a mid-flight edit leaked into the deploy"
    _same(packed_dirty[LANDING], head, LANDING)


def test_staging_and_production_get_identical_bytes(packed, packed_dirty):
    """Two packs of the same HEAD must be byte-identical in CONTENT.

    (The gzip container carries an mtime, so compare the members, not the file.)
    """
    assert sorted(packed["read"]) == sorted(packed_dirty), "the two packs contain different files"
    for n, b in packed["read"].items():
        assert b == packed_dirty[n], n


def test_exclusions_still_hold(packed):
    for junk in ("node_modules", "__pycache__", "dist", ".git"):
        hit = [n for n in packed["names"] if junk in n.split("/")]
        assert not hit, "%s leaked into the pack: %s" % (junk, hit[:2])
    for need in (LANDING, "colt_auth.py", "docker-compose.web.yml"):
        assert need in packed["names"], "missing from the pack: %s" % need


def test_a_dirty_tree_is_reported_not_silently_shipped(dwd):
    """The operator must be told that their uncommitted edits are NOT what deploys."""
    clean, sha, dirty = dwd["_tree_state"]()
    assert sha, "HEAD could not be resolved - the pack would fall back to the working tree"
    for d in dirty:
        # A diagnostic that misreports a path sends the next investigation down the wrong road.
        assert not d.startswith(" "), "dirty path is mis-sliced: %r" % d
        assert os.path.exists(os.path.join(ROOT, d)) or d.endswith("/"), "phantom path: %r" % d


def test_the_archive_is_forced_to_repository_line_endings():
    """Pin the FLAGS, because the failure is invisible on Linux.

    A Linux sandbox cannot reproduce this at all — it passed there before and after the fix — so
    the only guard that works on every machine is asserting the flags are present. Verified
    separately against a temp clone with core.autocrlf=true in its own config: without the flags
    562 CRLF pairs and != HEAD, with them 0 and == HEAD.
    """
    src = open(os.path.join(ROOT, "deploy_web_direct.py"), encoding="utf-8").read()
    i = src.index('"archive"')
    call = src[max(0, i - 400):i]
    assert "core.autocrlf=false" in call, (
        "git archive is not forced to core.autocrlf=false - on Windows it will emit CRLF and the "
        "deployed artifact will differ from the one a Linux packer produces")
