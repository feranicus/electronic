"""test_gate_claims.py — a check's detail must not cite evidence that does not exist yet.

THE FINDING (kimi-k2.6, staging panel, 22 Nov 2026). `config_write_ordering` passed with the
detail "WHAT it read is proven by mount_fresh + config_drift". Checks run in source order, and
both of those run LATER in the same gate - post-reboot it was check 38 citing checks 41 and 46. So
at the moment that PASS was printed, neither cited check had produced anything. The system was
healthy; the detail was not. The model said so plainly ("This is a check defect, not a system
defect") and it was right.

WHY IT MATTERS ENOUGH TO BE A BUILD GATE. Defect class 8: a name or a detail that overclaims
teaches the outage. An operator reading "proven by X" stops looking, and if X later fails he has
already been told the question was settled. The honest form is to say what THIS check measured and
where the other question is answered - which is what the detail says now.

WHAT THIS ASSERTS. For every `chk <name> yes|no "<detail>"` in stagegate.py, if the detail names
another check, that check must appear EARLIER in the file. Forward references are allowed only
when the detail makes no claim about them having run: the vocabulary list below is the test, and
it is deliberately small and literal, because a guard nobody can read is a guard nobody keeps.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "stagegate.py")

# Words that turn a mention into a CLAIM about evidence already in hand. "answered by X later",
# "X runs after this" and similar are fine: they point, they do not assert.
CLAIM = re.compile(r"\b(proven|proves|proved|confirmed|verified|established|covered)\b", re.I)

CHK = re.compile(r'chk\s+([a-z_][a-z0-9_]*)\s+(?:yes|no)\s+"(.*?)"', re.S)


def _checks():
    src = io.open(GATE, encoding="utf-8").read()
    out = []
    for m in CHK.finditer(src):
        out.append((m.start(), m.group(1), m.group(2)))
    return src, out


def test_the_gate_actually_contains_checks():
    """A CHECK THAT CANNOT SEE ITS SUBJECT IS NOT A CHECK (class 1). If the chk grammar ever
    changes, every assertion below would pass over an empty list and prove nothing."""
    _src, found = _checks()
    assert len(found) > 20, "only %d chk calls found - the parse is broken, not the gate" % len(found)
    names = {n for _p, n, _d in found}
    for expected in ("config_write_ordering", "mount_fresh", "config_drift"):
        assert expected in names, "%s is gone from the gate - this test is measuring nothing" % expected


def test_no_detail_claims_proof_from_a_check_that_has_not_run_yet():
    src, found = _checks()
    first = {}
    for pos, name, _d in found:
        first.setdefault(name, pos)

    problems = []
    for pos, name, detail in found:
        if not CLAIM.search(detail):
            continue
        for other, other_pos in first.items():
            if other == name or other not in detail:
                continue
            if other_pos > pos:
                problems.append(
                    "%s claims '%s' from %s, which runs LATER in the gate"
                    % (name, CLAIM.search(detail).group(0), other))
    assert not problems, (
        "a check detail cites evidence that does not exist when it prints:\n  "
        + "\n  ".join(problems)
        + "\nSay what THIS check measured and name where the other question is answered, "
          "without calling it proof already in hand.")


def test_the_guard_catches_the_exact_wording_that_was_shipped():
    """PROVE THE GATE BY BREAKING WHAT IT GUARDS (class 3). The original detail is replayed through
    the same matcher, so this test fails if the matcher is ever loosened into uselessness."""
    shipped = "started 21s after the write; WHAT it read is proven by mount_fresh + config_drift"
    assert CLAIM.search(shipped), "the claim vocabulary no longer matches the wording that shipped"
    assert "mount_fresh" in shipped
    # ...and the repaired wording must NOT trip it, or the fix would be unshippable.
    repaired = ("started 21s after the write, so it necessarily read the bytes on disk at that "
                "moment. This check measures ORDER ONLY. The CONTENT question is answered by "
                "mount_fresh and config_drift, which run LATER in this same gate")
    assert not CLAIM.search(repaired), (
        "the repaired detail still reads as a claim of proof: %s" % CLAIM.search(repaired).group(0))


# ---------------------------------------------------------------------------------------------
# THE OTHER HALF OF THE SAME PANEL: the reload doctrine's negative control.
# ---------------------------------------------------------------------------------------------
def test_the_bare_edit_experiment_is_wired_into_the_gate():
    """mistral-3-14B, same panel: guard_write_path_reloads asserts in prose that a bare file edit
    does not propagate, and nothing measured it. A clause carried only in a detail string is not a
    check (class 9 - behaviour AND wiring)."""
    src, found = _checks()
    names = [n for _p, n, _d in found]
    assert "bare_edit_does_not_propagate" in names, (
        "the negative control is not run by the gate, so the reload doctrine is still prose")
    # ANCHOR ON THE INVOCATION, NOT ON THE WORD. `"staleproof" in src` passed when the command was
    # replaced with `true`, because the verb's name still appeared in the comment explaining it -
    # a check matching its own explanatory prose, which this repo has done five separate times
    # (class 4). The property is that the variable the verdict is read from is ASSIGNED by running
    # the agent.
    assert re.search(r'SP=\$\(\s*python3 /opt/caddyguard/agent\.py staleproof', src), (
        "the gate does not actually run the experiment; the verdict comes from somewhere else")
    # A SKIP MUST NOT SCORE AS A PASS. We are inside the branch that already found a caddy
    # container, so an experiment that could not run means the gate learned nothing.
    i = src.index("bare_edit_does_not_propagate")
    window = src[max(0, i - 900):i + 900]
    assert re.search(r'SKIP\*\)\s*chk bare_edit_does_not_propagate no', window), (
        "a SKIP is scored as a pass - a check that cannot run is not a check (class 2)")


def test_the_experiment_never_touches_the_live_proxy():
    """The reason this clause went unmeasured for months is that the obvious test is an outage.
    Assert the properties that keep it cheap: a throwaway container, and the live source hashed
    before and after."""
    agent = io.open(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"), encoding="utf-8").read()
    i = agent.index("def cmd_staleproof(")
    j = agent.index("\ndef ", i + 10)
    body = agent[i:j]
    # IMPLICIT CONCATENATION HIDES A PHRASE FROM A SUBSTRING SEARCH. A message wrapped across two
    # source lines reads as "...does not " / "reproduce..." with a quote, a newline and an indent
    # between them, so grepping for the sentence finds nothing and reports it missing from code
    # that contains it. Join the pieces first, then look. (This file caught itself twice doing it.)
    joined = re.sub(r'"\s*\n\s*"', "", body)
    # The invocation is a LIST, not a shell string - grep for the shell form and this check reports
    # a missing throwaway container about code that has one. Assert the call the code makes.
    assert '"docker", "run"' in body and '"--rm"' in body, (
        "the experiment does not start a throwaway container")
    assert body.count("hashlib.sha256") >= 1 and "THE LIVE FILE CHANGED" in body, (
        "the live config's hash is not compared before and after")
    assert "docker rm -f" in body or '"rm", "-f"' in body, "the throwaway is never removed"
    # The vhosts must be unresolvable by construction: RFC 2606 reserves .invalid precisely so a
    # test name cannot collide with, or be routed to, something real.
    assert ".invalid" in body, "the experiment uses hostnames that could resolve somewhere"
    # And the three assertions that stop it passing for the wrong reason.
    for needed in ("the fixture does not reproduce", "A BARE FILE EDIT REACHED THE RUNNING CONFIG",
                   "did NOT publish"):
        assert needed in joined, "the experiment is missing an assertion: %r" % needed
