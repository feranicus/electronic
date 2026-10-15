"""A failing gate must NAME what went wrong (defect class 26).

THE INCIDENT, 2026-10-15. The deck-quality gate reported nine failures in CI and not one of them
said what was wrong. Every message looked like a different fault:

    FAIL  findings deck renders with a pathological scope string e._load (node:internal/...)
    FAIL  cbiq deck builds odule._load (node:internal/...)
    FAIL  geopol deck builds ule._load (node:internal/...)

"e._load", "odule._load", "ule._load" are the SAME string - `Module._load` - truncated at three
different offsets, because `build()` returned `stderr[-300:]`. Node prints the cause on the FIRST
line and the stack after it, so a tail slice keeps the stack and throws the cause away. The actual
message was `Error: Cannot find module 'pptxgenjs'`, which names both the problem and its fix.

Defect class 25 says to grep for the error VOCABULARY first and show context second. Its Python
form says a traceback's cause is its LAST line; node is the other way round, and that is exactly
why the rule is "find the cause", not "take an end of the string".
"""
import importlib.util
import os
import shutil

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TDQ = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts", "test_deck_quality.py")

# VERBATIM from the failing CI job (run 38793620910), which is the only fixture that proves this.
CI_STDERR = """node:internal/modules/cjs/loader:1143
  throw err;
  ^

Error: Cannot find module 'pptxgenjs'
Require stack:
- /home/gates/work/hermes-skills/shodan-assessment/scripts/build_findings_deck.js
    at Module._resolveFilename (node:internal/modules/cjs/loader:1140:15)
    at Module._load (node:internal/modules/cjs/loader:1096:12)
    at Function.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:164:12) {
  code: 'MODULE_NOT_FOUND',
  requireStack: [
    '/home/gates/work/hermes-skills/shodan-assessment/scripts/build_findings_deck.js'
  ]
}

Node.js v20.19.2
"""


def _tdq():
    """Import the gate module without running it (its work is behind `if __name__`)."""
    spec = importlib.util.spec_from_file_location("_tdq_for_test", TDQ)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_fixture_really_is_the_failure_we_are_fixing():
    """PROVE THE FIXTURE first (defect class 12). If the old slice did not mangle this input,
    the test below would be measuring nothing."""
    assert "Cannot find module 'pptxgenjs'" in CI_STDERR
    old = CI_STDERR[-300:]
    assert "Cannot find module" not in old, (
        "the 300-char tail keeps the cause on this input, so it does not reproduce the incident")
    assert "e._load" in old, "the fixture no longer reproduces the truncated-frame output"


def test_a_failed_build_names_the_missing_module():
    got = _tdq().node_error(CI_STDERR)
    assert "Cannot find module" in got and "pptxgenjs" in got, (
        "the gate still does not say what went wrong; it reported %r" % got)
    assert "e._load" not in got, "a mid-word stack fragment is being presented as the cause"


def test_the_repository_file_is_named_not_nodes_internals():
    """A cause with no location sends the next investigation down the wrong road. The useful
    frame is the one inside this repo, never one in node:internal."""
    got = _tdq().node_error(CI_STDERR)
    assert "build_findings_deck.js" in got, (
        "the message does not say WHICH builder failed: %r" % got)


def test_empty_stderr_says_so_instead_of_inventing_a_cause():
    """A check that cannot see its subject must not answer (defect class 1). Silence is a real
    outcome and must read as one, not as a blank line the operator skims past."""
    got = _tdq().node_error("")
    assert got and "no stderr" in got.lower(), got


def test_the_gate_actually_uses_it_at_the_call_site():
    """BEHAVIOUR AND WIRING (defect class 9), and anchor on the CALL SITE (class 4). Every test
    above calls node_error() directly, so all of them still passed when build() was reverted to
    `stderr[-300:]` - they were measuring a function nothing used. The property that matters is
    that the ONE place which reports a failed build goes through it."""
    import ast
    tree = ast.parse(open(TDQ, encoding="utf-8").read())
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build"]
    assert fn, "build() is gone; this test is no longer reading what reports a failed deck build"
    src = ast.unparse(fn[0])
    assert "node_error" in src, (
        "build() reports node's stderr without finding the cause in it. That is the 2026-10-15 "
        "incident: nine failures, none of which said what was wrong.")
    assert "[-300:]" not in src and "[-200:]" not in src, (
        "build() is slicing an end off stderr again; node puts the cause on the FIRST line")


def test_an_unrecognised_failure_is_not_swallowed():
    """A wildcard branch must FAIL loudly, never score an unknown answer as a pass (class 6).
    When no known error vocabulary matches, the leading lines still have to reach the operator."""
    got = _tdq().node_error("something nobody anticipated\nsecond line\n")
    assert "something nobody anticipated" in got, got


# =============================================================================================
# THE STAGING GATE MUST SAY WHY IT COULD NOT REACH THE TWIN.
#
# 2026-10-15, the first real pipeline run. The staging job failed with four lines, and the only
# evidence was `staging unreachable: ***@165.245.244.174: Permission denied (publickey).` - with
# the account masked, because DROPLET_USER is a secret. From that you cannot tell whether the
# droplet was down, the port was shut, no key was present, the wrong key was offered, or the right
# key simply was not authorized on THAT host. It was the last one.
# =============================================================================================

import subprocess as _sp

STAGEGATE = os.path.join(ROOT, "stagegate.py")


def _sg():
    spec = importlib.util.spec_from_file_location("_sg_for_test", STAGEGATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_unreachable_path_diagnoses_instead_of_slicing_the_error():
    """ANCHOR ON THE CALL SITE (defect class 4). The old line was
    `say("  staging unreachable: %s" % (err or "")[:200])` - a truncated string and nothing else."""
    import ast
    tree = ast.parse(open(STAGEGATE, encoding="utf-8").read())
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "unreachable_report" in fns, "the diagnosis is gone"
    body = ast.unparse(tree)
    assert "staging unreachable: %s" not in body or "unreachable_report" in body, body[:200]
    # The report must be what the failure path actually calls.
    callers = [ast.unparse(n) for n in ast.walk(tree)
               if isinstance(n, ast.Call) and "unreachable_report" in ast.unparse(n.func)]
    assert callers, "nothing calls unreachable_report; the failure path still prints a bare slice"


def test_it_separates_a_dead_droplet_from_a_refused_key():
    """Two faults that look identical in a one-line summary and share no cause. A diagnosis that
    cannot tell them apart sends the next investigation down the wrong road (class 26)."""
    sg = _sg()
    refused = sg.unreachable_report("127.0.0.1", "root@x: Permission denied (publickey).")
    assert "authorized_keys" in refused and "per-HOST" in refused, refused
    assert "ship.py --fix-ci-key" in refused, "it names no repair"

    down = sg.unreachable_report("127.0.0.1", "ssh: connect to host x port 22: Connection timed out")
    assert "Nothing is concluded about the key" in down, (
        "a dead droplet is being reported as a key problem: %s" % down)
    assert "authorized_keys" not in down


def test_an_unrecognised_ssh_failure_is_not_given_a_confident_reading():
    """A wildcard branch must not score an unknown as a known cause (defect class 6)."""
    sg = _sg()
    out = sg.unreachable_report("127.0.0.1", "ssh: something nobody has seen before")
    assert "not in the known set" in out, out
    assert "authorized_keys" not in out and "did not answer" not in out


def test_it_prints_a_fingerprint_and_never_key_material(tmp_path):
    """The fingerprint is the ONE value that lets a reader compare what the runner offered against
    what the host authorises - and it is public. The private half must never reach a CI log, which
    on this PUBLIC repository is readable by anyone."""
    # ABSENT IS NOT THE SAME AS FAILED (defect classes 2 and 10). The first version of this went
    # straight to `r.returncode != 0`, which the interpreter never reaches: subprocess RAISES
    # FileNotFoundError when the binary is not on PATH. So on a machine without ssh-keygen the
    # test did not skip, it CRASHED - a missing tool reported as a failing test. Found by actually
    # running the branch with ssh-keygen removed from PATH, which is also how the undefined
    # `pytest` name in it had survived: a branch nobody executes is a branch nobody has checked.
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen is not on PATH here; CI and the droplet cover this")
    key = str(tmp_path / "k")
    try:
        r = _sp.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "probe", "-f", key],
                    capture_output=True, timeout=60)
    except OSError as e:
        pytest.skip("ssh-keygen could not be run here (%s)" % type(e).__name__)
    if r.returncode != 0:
        pytest.skip("ssh-keygen refused to mint a test key here")
    sg = _sg()
    os.environ["SSH_KEY"] = key
    try:
        out = sg.unreachable_report("127.0.0.1", "root@x: Permission denied (publickey).")
    finally:
        os.environ.pop("SSH_KEY", None)
    assert "SHA256:" in out, "no fingerprint, so the offered identity is still unidentifiable"
    secret = open(key, encoding="utf-8").read()
    assert "PRIVATE KEY" not in out, "the diagnosis printed private key material into the log"
    for line in secret.splitlines():
        if len(line) > 20 and "PRIVATE KEY" not in line:
            assert line not in out, "a line of the private key leaked into the diagnosis"


def test_the_summary_puts_failures_first_and_is_silent_off_actions(tmp_path, monkeypatch):
    """A reader scans the top of a table. And none of this may change the operator's console: the
    directives are inert off Actions, so the gate keeps one behaviour and one home."""
    sg = _sg()
    checks = [{"name": "ok_one", "ok": True, "detail": "fine"},
              {"name": "broken", "ok": False, "detail": "proxy -> 502"},
              {"name": "ok_two", "ok": True, "detail": "fine"}]

    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    sg.summarise_for_ci("NO-GO", "digest", checks, "rebooted")      # must not raise

    path = tmp_path / "sum.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    sg.summarise_for_ci("NO-GO", "digest", checks, "rebooted")
    text = path.read_text(encoding="utf-8")
    assert text.index("broken") < text.index("ok_one"), (
        "the failed check is not at the top of the table:\n%s" % text)
    assert "**NO-GO**" in text, "the verdict is not at the top of the summary"
    assert "2 of 3 deterministic checks passed" in text, (
        "the count does not match the checks it was given:\n%s" % text)
    assert "3 of 3" not in text, "it reported every check as passing"

    # APPENDS. Other steps write to this file too; clobbering them is the same mistake as a
    # second home for a value.
    before = len(text)
    sg.summarise_for_ci("GO", "second", checks, None)
    assert len(path.read_text(encoding="utf-8")) > before, "the summary overwrote what was there"


def test_a_gate_with_no_checks_says_so_rather_than_implying_success(tmp_path, monkeypatch):
    """The unreachable run measures NOTHING. An empty table that renders like a clean sheet is
    defect class 7 - output that looks identical whether or not anything was measured."""
    sg = _sg()
    path = tmp_path / "sum.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    sg.summarise_for_ci("NO-GO", "", [], None)
    text = path.read_text(encoding="utf-8")
    assert "stopped before it could measure anything" in text, text
