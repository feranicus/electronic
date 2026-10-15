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
