"""test_deploy_failure_report.py — a failed deploy must say WHICH failure it was.

20 Nov 2026. The staging gate printed exactly this and stopped:

    [X] remote deploy failed (see output above)
        [!] staging build failed (exit 1)

There was no output above. The remote step had returned a non-zero exit code with ZERO bytes on
a stream that already folds stderr into stdout, so the one fact available - that ssh itself also
said nothing - was thrown away and replaced with a pointer to something that did not exist.

Empty-and-failed has two causes that look identical here and need opposite repairs: the payload
never reached a shell (connection refused or reset, the wrong key offered, a cut upload) or the
script ran and produced nothing. CLAUDE.md already requires a sentinel only a shell that really
ran can echo - `sshout()` has had one since the ensure_docker incident - and the deploy path,
which is the one that actually changes production, never had it.
"""
import ast
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = io.open(os.path.join(ROOT, "deploy_web_direct.py"), encoding="utf-8").read()


def _no_comments(src):
    """A check has matched its own explanatory comment five separate times here (class 4), and
    this file comments heavily about the very strings it asserts."""
    out, tree = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#")), None
    try:
        tree = ast.parse(src)
    except SyntaxError:                                           # pragma: no cover
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            d = ast.get_docstring(node, clean=False)
            if d:
                out = out.replace(d, "")
    return out


BODY = _no_comments(SRC)


def test_the_payload_carries_a_sentinel_a_shell_must_echo():
    assert '"echo REMOTE_SHELL_ALIVE"' in BODY, (
        "nothing proves the remote shell started, so an empty failure cannot be read")
    i_sent = BODY.index('"echo REMOTE_SHELL_ALIVE"')
    i_set = BODY.index('"set -e"', i_sent - 400 if i_sent > 400 else 0)
    assert i_sent < i_set, (
        "the sentinel must be printed BEFORE `set -e`, or the first failing line suppresses the "
        "one piece of evidence the report is built on")


def test_the_failure_report_distinguishes_the_two_causes():
    tail = BODY[BODY.index("if r.returncode:"):]
    tail = tail[:tail.index("sys.exit(1)")]
    assert "REMOTE_SHELL_ALIVE" in tail, "the report does not consult the sentinel"
    assert "ssh exit code" in tail and "bytes of output" in tail, (
        "the report must print what it measured, not just a verdict (class 5)")
    for branch in ("the failure is in the build", "never reached a shell"):
        assert branch in tail, "the report collapses two opposite causes into one sentence"
    assert "see output above" not in tail, (
        "the report still points at output that may not exist")


def test_the_reading_names_a_next_step():
    tail = BODY[BODY.index("if r.returncode:"):]
    assert "recover.py" in tail, (
        "a diagnosis with no next step leaves the operator where it found them")


def test_stderr_is_still_folded_in_so_an_empty_stream_is_evidence():
    """The report reasons from an empty stream, which is only sound while ssh's own stderr lands
    in it. Separate the streams and 'bytes of output: 0' stops meaning anything."""
    assert "stderr=subprocess.STDOUT" in BODY, (
        "stderr was split out, so an empty stdout no longer proves ssh said nothing")
