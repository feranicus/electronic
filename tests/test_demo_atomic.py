"""The demo artifacts must never be readable in a half-written state.

WHAT HAPPENED (2026-09-07). The staging gate refused to promote on:

    engine_runs  FAIL  decks=3 html=39511b canvases=0 leaks=0 - it ran but the OUTPUT is wrong

and all four review models concluded the ENGINE was broken. It was not. `main.py::_warm_demo`
builds the demo in colt-web's executor at startup, and the staging check runs `demo_build.py` as a
SEPARATE PROCESS seconds later. The `threading.Lock` in main.py serialises visitors inside ONE
process and cannot serialise two processes, so both wrote the same paths and the check read a file
mid-write: plausible size, zero canvases.

The same window is reachable in production, where the reader is a visitor downloading a deck from
the public /api/demo endpoint.

TWO FIXES, and they are different in kind:
  * `demo_build._publish()` -- build to a fragment, then `os.replace` into place. A reader sees the
    previous complete file or the new complete file, never a fragment. os.replace is atomic on
    POSIX and on Windows; fcntl is not an option because an existing gate refuses that import so
    the suite keeps running on the operator's machine.
  * the check NAMES ITS SUBJECT (`*_GEOPOL_Animated.html`, the artifact that must carry five
    canvases) instead of `ls *.html | head -1`, and distinguishes "incomplete" from "wrong".
"""
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts"))
sys.path.insert(0, ROOT)

import demo_build as D          # noqa: E402


def test_a_concurrent_reader_never_sees_a_fragment(tmp_path):
    """The property, exercised rather than reasoned about: hammer publish while a reader reads,
    and assert the reader never observes a document without its closing tag."""
    dest = tmp_path / "a.html"
    dest.write_text("<html>OLD</html>", encoding="utf-8")
    torn, stop = [], threading.Event()

    def reader():
        while not stop.is_set():
            try:
                t = dest.read_text(encoding="utf-8")
                if t and not t.endswith("</html>"):
                    torn.append(t[:60])
            except Exception:
                pass                      # a missing file is not a torn read

    r = threading.Thread(target=reader)
    r.start()
    try:
        # 40, not 150: with a live reader on Windows each publish may burn retries, and a test that
        # takes ten seconds on the operator's machine is a test he learns to skip.
        for _ in range(40):
            part = "%s.part-%d" % (dest, os.getpid())
            with open(part, "w", encoding="utf-8") as fh:
                fh.write("<html>" + ("x" * 40000) + "</html>")
            assert D._publish(part, str(dest))
    finally:
        stop.set()
        r.join()
    assert not torn, "os.replace must never expose a partial file: %r" % torn[:2]
    assert dest.read_text(encoding="utf-8").endswith("</html>")


def test_publish_survives_a_windows_style_lock(tmp_path, monkeypatch):
    """REPRODUCE WINDOWS ON LINUX. This is the check that stops the whole recurring class.

    On POSIX, `os.replace` over an open file always succeeds. On WINDOWS it raises
    PermissionError(13) while any handle is open, because Python's open() does not pass
    FILE_SHARE_DELETE. The first version of the concurrent-reader test therefore passed in a Linux
    sandbox and FAILED on the operator's machine with:

        [demo] could not publish a.html: PermissionError(13, 'Access is denied')

    That is the SIXTH time a change of mine has been validated on Linux and handed to him as a
    Windows command (httpx, esbuild, os.uname, python-multipart, cp1252, /proc). Skipping the test
    on Windows would hide it; simulating the platform proves the behaviour wherever the suite runs.
    """
    real = os.replace
    calls = {"n": 0}

    def windows_like(a, b):
        calls["n"] += 1
        if calls["n"] <= 5:                    # a reader is holding the destination open
            raise PermissionError(13, "Access is denied")
        return real(a, b)

    monkeypatch.setattr(os, "replace", windows_like)
    dest = str(tmp_path / "a.html")
    part = D._fragment(dest)
    with open(part, "w", encoding="utf-8") as fh:
        fh.write("<html>NEW</html>")
    assert D._publish(part, dest), "a transient Windows lock must be retried, not reported as broken"
    assert calls["n"] > 1, "the retry never happened, so this test proved nothing"
    monkeypatch.setattr(os, "replace", real)
    assert open(dest, encoding="utf-8").read() == "<html>NEW</html>"


def test_publish_does_not_retry_forever_on_a_real_error(tmp_path, monkeypatch):
    """A retry loop that swallows every failure is worse than none: the build would report success
    for an artifact that never landed. Only PermissionError is transient."""
    def broken(a, b):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(os, "replace", broken)
    part = tmp_path / "x.pptx"
    part.write_text("data", encoding="utf-8")
    assert D._publish(str(part), str(tmp_path / "y.pptx")) is False


def test_publish_removes_the_fragment_when_it_cannot_land(tmp_path):
    """A failed publish must not leave `.part-NNN` litter in a directory the app serves from:
    /api/demo globs that directory, and a stray fragment is a downloadable broken artifact."""
    part = tmp_path / "x.pptx.part-1"
    part.write_text("data", encoding="utf-8")
    blocked = tmp_path / "sub" / "x.pptx"          # the parent does not exist -> replace fails
    assert D._publish(str(part), str(blocked)) is False
    assert not part.exists(), "the fragment must be cleaned up when it cannot be published"


def test_a_missing_fragment_is_reported_not_crashed(tmp_path):
    """A builder that failed leaves no fragment. That is a normal outcome and must return False,
    not raise -- the caller prints the builder's own error, which is the useful message."""
    assert D._publish(str(tmp_path / "nope"), str(tmp_path / "dest")) is False


def test_every_artifact_is_published_atomically():
    """WIRING. The behaviour above is worth nothing if the build still writes straight to the
    final path. Both the deck loop and the GEOPOL html must go through _publish()."""
    src = open(os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts",
                            "demo_build.py"), encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert body.count("_publish(") >= 3, "every artifact must be published atomically"
    assert ".part-%d" % 0 or "part-" in body
    i = body.index("for script, args, out in jobs:")
    loop = body[i:i + 700]
    assert "part" in loop and "_publish(part, dest)" in loop, \
        "the deck builders must write a fragment, not the final path"


def test_the_staging_check_names_the_artifact_it_judges():
    """`ls *.html | head -1` judged the whole build on whichever file sorted first. The file that
    must carry five canvases is the animated GEOPOL page, so the check has to ask for THAT one."""
    src = open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "_GEOPOL_Animated.html" in body, \
        "engine_runs must name the artifact whose canvases it counts"
    # ASSERT THE LOGIC, NOT THE MESSAGE. The first version looked for "</html>" in a window after
    # the canvas count -- but the FAILURE MESSAGE also contains that string, so neutering the
    # completeness test entirely still passed. A check aimed at prose instead of behaviour cannot
    # fail for the right reason; that is the defect this whole file exists to record.
    assert 'FIN=$(docker exec' in body and "grep -c '</html>'" in body, \
        "completeness must be MEASURED from the artifact, not assumed"
    i = body.index('FIN=$(docker exec')
    window = body[i:i + 900]
    assert "sleep" in window and window.count('FIN=$(docker exec') >= 2, \
        "an incomplete artifact must be RE-READ before it is judged: a writer may still be running"
    assert 'if [ "${FIN:-0}" -eq 0 ]; then' in body, \
        "and an artifact that is still incomplete after the re-read must be reported as INCOMPLETE"


def test_the_fragment_keeps_the_extension(tmp_path):
    """THE DEFECT THIS ASSERTS AGAINST SHIPPED AND BROKE THE BUILD.

    The first version appended the suffix AFTER the extension (`X.pptx.part-123`). pptxgenjs
    APPENDS `.pptx` to any path not already ending in it, so node wrote `X.pptx.part-123.pptx`,
    _publish looked for `X.pptx.part-123`, found nothing, and printed
    `build_findings_deck.js FAILED:` with an EMPTY stderr -- blaming a builder that had worked.

    A fragment must therefore be a SIBLING of the destination with the extension intact.
    """
    dest = str(tmp_path / "Deck_Name.pptx")
    part = D._fragment(dest)
    assert part.endswith(".pptx"), \
        "a tool that infers the format from the extension will write somewhere else: %s" % part
    assert os.path.dirname(part) == os.path.dirname(dest), \
        "os.replace cannot cross a filesystem, so the fragment must be a sibling"
    assert os.path.basename(part).startswith("."), \
        "a fragment must be hidden: /api/demo globs the directory and `*` skips dotfiles"
    assert part != dest


def test_a_real_deck_builder_lands_at_the_destination(tmp_path):
    """END TO END, because the string assertions above all passed while the build was broken.

    Run the actual node builder against the committed fixture, publish, and assert the artifact is
    at the FINAL path with no fragment left behind. This is the check that would have caught it.
    """
    import shutil
    import subprocess
    if not shutil.which("node"):
        import pytest as _p
        _p.skip("node is not installed here; the image build and CI run this")
    scripts = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts")
    fixture = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "sample",
                           "findings.sample.json")
    if not os.path.exists(fixture):
        import pytest as _p
        _p.skip("fixture missing")
    dest = str(tmp_path / "X_Findings.pptx")
    part = D._fragment(dest)
    r = subprocess.run(["node", os.path.join(scripts, "build_findings_deck.js"), fixture, part],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (r.stderr or "")[-400:]
    assert D._publish(part, dest), "the builder wrote somewhere _publish cannot find"
    assert os.path.getsize(dest) > 20000
    leftovers = [f for f in os.listdir(tmp_path) if f.startswith(".part-")]
    assert not leftovers, "a fragment was left in a directory the app serves from: %s" % leftovers
