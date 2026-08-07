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

SIDE BENEFIT worth knowing: `git archive` emits the REPOSITORY bytes (LF), not the Windows
working-copy bytes (CRLF), so the deployed artifact stops depending on which platform packed it.
"""
import os
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    problem stated in the least useful possible way. On Windows `git archive` applies
    core.autocrlf and emits CRLF while `git show` emits the raw LF blob — a real portability
    defect (the artifact would differ by platform), but one you could stare at that diff for a
    while without seeing."""
    if packed == head:
        return
    if packed.replace(b"\r\n", b"\n") == head:
        raise AssertionError(
            "%s: the pack has CRLF line endings, HEAD has LF. `git archive` is applying "
            "core.autocrlf, so the artifact would differ between a Windows and a Linux packer. "
            "Pass -c core.autocrlf=false -c core.eol=lf." % path)
    raise AssertionError("%s: packed content differs from HEAD (not just line endings)" % path)


def test_the_pack_is_the_commit_not_the_working_copy():
    ns = _mod()
    tgz = ns["pack"]()
    try:
        with tarfile.open(tgz) as t:
            for path in ("webapp/frontend/src/pages/Landing.jsx",
                         "webapp/backend/app/main.py",
                         "colt_auth.py"):
                head = _head(path)
                if head is None:
                    continue
                _same(t.extractfile(path).read(), head, path)
    finally:
        os.unlink(tgz)


def test_an_edit_during_a_ship_cannot_change_what_deploys():
    """The actual 2026-08-07 mechanism, reproduced."""
    ns = _mod()
    target = os.path.join(ROOT, "webapp", "frontend", "src", "pages", "Landing.jsx")
    rel = "webapp/frontend/src/pages/Landing.jsx"
    head = _head(rel)
    if head is None:
        return
    before = open(target, "rb").read()
    try:
        # Simulate the editor writing mid-deploy.
        with open(target, "ab") as fh:
            fh.write(b"\n// TRANSIENT EDIT MADE WHILE A SHIP WAS RUNNING\n")
        tgz = ns["pack"]()
        try:
            with tarfile.open(tgz) as t:
                packed = t.extractfile(rel).read()
        finally:
            os.unlink(tgz)
        assert b"TRANSIENT EDIT" not in packed, "a mid-flight edit leaked into the deploy"
        _same(packed, head, rel)
    finally:
        with open(target, "wb") as fh:
            fh.write(before)


def test_staging_and_production_get_identical_bytes():
    """Two packs of the same HEAD must be byte-identical in CONTENT.

    (The gzip container carries an mtime, so compare the members, not the file.)
    """
    ns = _mod()
    a, b = ns["pack"](), ns["pack"]()
    try:
        with tarfile.open(a) as ta, tarfile.open(b) as tb:
            na, nb = sorted(ta.getnames()), sorted(tb.getnames())
            assert na == nb, "the two packs contain different files"
            for n in na:
                ma = ta.getmember(n)
                if not ma.isfile():
                    continue
                assert ta.extractfile(n).read() == tb.extractfile(n).read(), n
    finally:
        os.unlink(a); os.unlink(b)


def test_exclusions_still_hold():
    ns = _mod()
    tgz = ns["pack"]()
    try:
        names = tarfile.open(tgz).getnames()
        for junk in ("node_modules", "__pycache__", "dist", ".git"):
            hit = [n for n in names if junk in n.split("/")]
            assert not hit, "%s leaked into the pack: %s" % (junk, hit[:2])
        # ...and the things that MUST ship are there.
        for need in ("webapp/frontend/src/pages/Landing.jsx", "colt_auth.py",
                     "docker-compose.web.yml"):
            assert need in names, "missing from the pack: %s" % need
    finally:
        os.unlink(tgz)


def test_a_dirty_tree_is_reported_not_silently_shipped():
    """The operator must be told that their uncommitted edits are NOT what deploys."""
    ns = _mod()
    clean, sha, dirty = ns["_tree_state"]()
    assert sha, "HEAD could not be resolved - the pack would fall back to the working tree"
    for d in dirty:
        # A diagnostic that misreports a path sends the next investigation down the wrong road.
        assert not d.startswith(" "), "dirty path is mis-sliced: %r" % d
        assert os.path.exists(os.path.join(ROOT, d)) or d.endswith("/"), "phantom path: %r" % d
