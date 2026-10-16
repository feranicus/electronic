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


def _no_probe(*_a, **_kw):
    """TESTS MUST NOT OPEN SSH SESSIONS (defect class 18), and a 25-second timeout per call would
    make this file a coin flip (class 15). The ssh -v probe is exercised directly below with an
    injected runner; here it is replaced so the REPORT can be read on its own."""
    return [], []


def _sg(probe=_no_probe):
    spec = importlib.util.spec_from_file_location("_sg_for_test", STAGEGATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if probe is not None:
        mod.offered_identities = probe
    return mod


class _R:
    """A fake completed process. ssh writes its -v trace to STDERR."""

    def __init__(self, stderr="", stdout=""):
        self.stderr, self.stdout, self.returncode = stderr, stdout, 255


# VERBATIM shapes from OpenSSH 9.x. The two traces below are the whole point of the probe: they
# produce the SAME `Permission denied (publickey)` and need opposite repairs.
TRACE_OFFERED = """debug1: Connecting to 165.245.244.174 [165.245.244.174] port 22.
debug1: Will attempt key: /home/runner/.ssh/deploy_key ED25519 SHA256:7uwyj5gAAAA explicit
debug1: Offering public key: /home/runner/.ssh/deploy_key ED25519 SHA256:7uwyj5gAAAA explicit
debug1: Authentications that can continue: publickey
debug1: No more authentication methods to try.
root@165.245.244.174: Permission denied (publickey).
"""

TRACE_NOTHING = """debug1: Connecting to 165.245.244.174 [165.245.244.174] port 22.
debug1: identity file /root/.ssh/id_rsa type -1
debug1: Authentications that can continue: publickey
debug1: No more authentication methods to try.
root@165.245.244.174: Permission denied (publickey).
"""


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


# =============================================================================================
# MODULE ORDER IS EXECUTION ORDER.
#
# 2026-10-15. stagegate.main() began calling last_evidence(), which was defined BELOW
# `if __name__ == "__main__": sys.exit(main())`. An importer runs the whole module first, so
# ship.py (which imports stagegate and calls run()) never noticed. CI runs `python stagegate.py`,
# and died with NameError AFTER the gate had done its work. ruff F821 cannot catch it - the name
# IS defined at module level, just too late - so only executing the script finds it.
#
# The property is simple and general: the __main__ guard must be the LAST statement in the file.
# Derived across every root script that has one (defect class 35), not a list naming stagegate.
# =============================================================================================

def _root_scripts_with_a_main_guard():
    import ast
    out = []
    for fn in sorted(os.listdir(ROOT)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(ROOT, fn)
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except (OSError, SyntaxError):
            continue
        guards = [n for n in tree.body
                  if isinstance(n, ast.If) and "__main__" in ast.unparse(n.test)]
        if guards:
            out.append((fn, tree, guards[-1]))
    return out


def test_nothing_is_defined_after_the_main_guard():
    """A def or assignment below the guard does not exist yet when the guard runs. It is invisible
    to an importer (which executes the whole module before calling anything) and fatal to the
    script path - the asymmetry is exactly why this reached CI."""
    import ast
    scripts = _root_scripts_with_a_main_guard()
    assert scripts, "no root script has a __main__ guard; this guard is reading the wrong tree"
    offenders = {}
    for fn, tree, guard in scripts:
        late = [n for n in tree.body
                if n.lineno > guard.lineno
                and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                   ast.Assign, ast.AnnAssign))]
        if late:
            offenders[fn] = [getattr(n, "name", None)
                             or ast.unparse(getattr(n, "targets", [n])[0])
                             for n in late]
    assert not offenders, (
        "defined AFTER `if __name__ == \"__main__\"`, so it does not exist when the script runs "
        "its own main(): %s" % offenders)


def test_stagegate_main_only_calls_names_that_exist_by_then():
    """The specific failure, anchored on the CALL SITE (defect class 4). The general rule above is
    what prevents it; this says out loud which function broke and why, so a future reader does not
    have to rediscover that `main()` runs before the bottom of the file."""
    import ast
    tree = ast.parse(open(STAGEGATE, encoding="utf-8").read())
    guard = [n for n in tree.body if isinstance(n, ast.If) and "__main__" in ast.unparse(n.test)][-1]
    defined_before = {n.name: n.lineno for n in tree.body
                      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and n.lineno < guard.lineno}
    main = [n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    called = {c.func.id for c in ast.walk(main)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    module_level = {n.name for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    too_late = sorted(n for n in called & module_level if n not in defined_before)
    assert not too_late, (
        "stagegate.main() calls %s, which this module defines only AFTER the __main__ guard - "
        "`python stagegate.py` raises NameError, while importing it hides that" % too_late)


# ---------------------------------------------------------------------------------------------
# THE ssh -v PROBE, 2026-10-16.
#
# The operator asked whether stagegate.log held more detail than the step log. It does not: the
# workflow runs `python stagegate.py 2>&1 | tee stagegate.log`, so the artifact is the same
# stream, and the four failing runs died ~35 lines in with nothing truncated. The real gap was
# not log VOLUME, it was that nothing measured what ssh put on the wire. `offering` says which
# key we NAMED; only ssh's own -v trace says which key, if any, was PRESENTED.
# ---------------------------------------------------------------------------------------------


def test_a_key_that_was_offered_and_refused_points_at_authorisation():
    sg = _sg(probe=None)
    offered, _notes = sg.offered_identities("1.2.3.4", user="root",
                                            runner=lambda c: _R(stderr=TRACE_OFFERED))
    assert len(offered) == 1 and "deploy_key" in offered[0], offered
    assert "SHA256:" in offered[0], "no fingerprint, so the reader cannot compare it to the host"


def test_a_key_that_was_never_offered_is_reported_as_an_ABSENCE():
    """THE 2026-10-16 FAILURE. `-i` was dropped, so ssh presented nothing - and every check at
    the time was examining the key FILE, which was perfect. This trace has no Offering line."""
    sg = _sg(probe=None)
    offered, notes = sg.offered_identities("1.2.3.4", user="root",
                                           runner=lambda c: _R(stderr=TRACE_NOTHING))
    assert offered == [], "an Offering line was invented from a trace that has none: %s" % offered
    assert any("type -1" in n for n in notes), (
        "the trace says the only identity file could not be loaded (type -1) and the probe "
        "dropped that line - it is the evidence: %s" % notes)


def test_the_report_tells_the_two_apart_in_its_own_words():
    """BEHAVIOUR AND WIRING (class 9). The probe being right is worth nothing if the report reads
    both traces the same way. These two strings are what a reader at 3am actually sees."""
    denied = "root@x: Permission denied (publickey)."

    nothing = _sg(probe=lambda *a, **k: ([], ["debug1: identity file /root/.ssh/id_rsa type -1"]))
    out = nothing.unreachable_report("127.0.0.1", denied)
    assert "NO public key reached the wire" in out, out
    assert "not what the host permits" in out, (
        "it offered nothing and the report still sends the reader to authorized_keys: %s" % out)

    was = _sg(probe=lambda *a, **k: (["debug1: Offering public key: /k ED25519 SHA256:zz"], []))
    out2 = was.unreachable_report("127.0.0.1", denied)
    assert "a key WAS presented" in out2, out2
    assert "NO public key reached the wire" not in out2, out2


def test_the_probe_is_only_run_on_an_AUTH_failure():
    """A timeout never reaches the auth stage. Probing there spends a second ssh session (class
    43) to report an absence that means nothing, and "no key was offered" about a DEAD droplet is
    the class-1 error the whole function exists to prevent."""
    calls = []

    def _spy(*a, **k):
        calls.append(a)
        return [], []

    sg = _sg(probe=_spy)
    sg.unreachable_report("127.0.0.1", "ssh: connect to host x port 22: Connection timed out")
    assert calls == [], "the probe ran on a network failure: %s" % (calls,)
    sg.unreachable_report("127.0.0.1", "root@x: Permission denied (publickey).")
    assert calls, "the probe did NOT run on an authentication failure - it is wired to nothing"


def test_the_probe_asks_for_a_trace_instead_of_silencing_itself():
    """recover.SSH carries `-o LogLevel=ERROR` so a healthy run stays quiet, and -o beats -v. A
    probe that inherits it reads an empty trace and concludes 'nothing was offered' about every
    failure on earth. MEASURE the command (class 4: anchor on what is actually built)."""
    sg = _sg(probe=None)
    seen = {}

    def _capture(cmd):
        seen["cmd"] = cmd
        return _R(stderr=TRACE_OFFERED)

    sg.offered_identities("1.2.3.4", user="root",
                          ssh_cmd=["ssh", "-o", "LogLevel=ERROR", "-o", "BatchMode=yes",
                                   "-i", "/home/runner/.ssh/deploy_key"],
                          runner=_capture)
    cmd = seen["cmd"]
    levels = [cmd[i + 1] for i, t in enumerate(cmd)
              if t == "-o" and i + 1 < len(cmd) and cmd[i + 1].lower().startswith("loglevel")]
    assert levels == ["LogLevel=DEBUG1"], (
        "the probe would run at %s, which prints no debug1 lines at all: %s" % (levels, cmd))
    assert "-v" in cmd, cmd
    # THE IDENTITY MUST SURVIVE. A probe that drops -i reproduces the very bug it diagnoses and
    # would report "nothing offered" for a perfectly wired run.
    assert "-i" in cmd and cmd[cmd.index("-i") + 1] == "/home/runner/.ssh/deploy_key", cmd


def test_the_probe_uses_the_SAME_command_the_gate_uses():
    """ONE HOME (class 32). If the probe assembles its own ssh invocation it stops being evidence
    about the real one - which is the entire reason it exists."""
    import ast
    src = open(STAGEGATE, encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "offered_identities")
    body = ast.unparse(fn)
    assert "SSH" in body, "the probe does not start from recover.SSH, so it proves nothing"
    assert "'ssh'" not in body.replace("'ssh -v'", ""), (
        "the probe hand-rolls an ssh command instead of reusing the gate's: %s" % body[:300])


def test_the_probe_fails_OPEN_and_concludes_nothing():
    """A probe that cannot see its subject must not answer (class 1), and a crash in a DIAGNOSTIC
    must never replace the failure it was called to explain (class 10)."""
    sg = _sg(probe=None)

    def _boom(_cmd):
        raise OSError("ssh is not on PATH")

    offered, notes = sg.offered_identities("1.2.3.4", user="root", runner=_boom)
    assert offered == [] and notes and "nothing concluded" in notes[0].lower(), notes

    offered, notes = sg.offered_identities("1.2.3.4", user="root", runner=lambda c: _R(stderr=""))
    assert offered == [] and any("nothing concluded" in n.lower() for n in notes), (
        "an EMPTY trace was read as proof that no key was offered: %s" % notes)


# PEM ARMOUR, ASSEMBLED AT RUNTIME - never written as a literal pair in this file.
#
# gitleaks' `private-key` rule spans EVERYTHING between a BEGIN and an END delimiter, so writing
# both out, even inside a test whose entire purpose is to prove that material never leaks, IS a
# finding: `quality-and-secrets` failed run #8 on this exact line, blocking the whole pipeline
# before the build. CLAUDE.md already carries the rule ("a BEGIN/END pair inside a COMMENT, since
# the rule spans everything between") and I wrote one anyway, in code this time.
#
# The dashes are built with `"-" * 5`, so the literal `-----BEGIN` never appears in the source and
# the scanner has nothing to match - while the string the test actually feeds the probe is
# byte-identical to real armour, which is the only thing that makes the test meaningful. This is
# NOT obfuscation to dodge the scanner: ci_key.py, whose JOB is to match these delimiters, keeps
# them literal and is path-allowlisted for that reason. A fixture has no such need.
_ARMOUR = "-" * 5 + "%s OPENSSH PRIVATE KEY" + "-" * 5


def test_the_trace_can_never_carry_private_key_material():
    """This repository is PUBLIC and so are its CI logs. ssh -v does not print private bytes, but
    the probe must not relay them even if something upstream does."""
    sg = _sg(probe=None)
    poisoned = (TRACE_OFFERED
                + (_ARMOUR % "BEGIN") + "\n"
                + "bm90LWEta2V5LXN5bnRoZXRpYy1maXh0dXJlLWZvci10aGlzLXRlc3Qtb25seQ==\n"
                + (_ARMOUR % "END") + "\n")
    offered, notes = sg.offered_identities("1.2.3.4", user="root",
                                           runner=lambda c: _R(stderr=poisoned))
    blob = "\n".join(offered + notes)
    assert "PRIVATE KEY" not in blob, "the probe relayed private key armour into a public log"
    # ASSERT THE BODY WE ACTUALLY FED (class 3). When the armour was rebuilt above, this line
    # still named the OLD base64 string - absent from the payload, so it could never fail again.
    assert "bm90LWEta2V5" not in blob, "the probe relayed the key body"
    assert offered, "the real evidence was thrown away along with the noise"
