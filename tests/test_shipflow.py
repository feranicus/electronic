"""test_shipflow.py - main is reached only through a green gate, and the merge is the deploy.

WHY THE PR FLOW EXISTS. From GitHub's own rules reference: required status checks must pass
"before collaborators can make changes to a branch targeted by your ruleset". A freshly pushed
commit has no check runs yet, so a required check can NEVER be satisfied by a direct push. That is
the `Bypassed rule violations` line printed on every ship, and it is why a collaborator's
`python ship.py` would run 1069 tests, deploy to staging, and then be rejected AT THE PUSH - after
the staging gate and before the safe-point.

The two properties this file defends:

  1. NOTHING MERGES ON AN UNKNOWN STATE. Pending, missing, cancelled, errored, an unreachable API
     and a non-JSON response are all "not green". A probe that cannot see its subject must not
     answer (defect class 1) - and here answering wrongly means putting unreviewed code on main.

  2. THE MERGE IS THE DEPLOY. pipeline.yml fires on push to main. If ship.py also deployed in PR
     mode there would again be two paths to one droplet, which is the defect measured on
     2026-10-15 (laptop shipped colt-web 11:52Z, CI shipped the bots 11:58Z).

Nothing here reaches the network: `gh` is replaced by a fake whose canned answers are the shapes
the real API returns.
"""
import ast
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import shipflow  # noqa: E402


class R:
    """What subprocess.run returns, narrowed to what shipflow reads."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def runs(*check_runs):
    return lambda args: R(json.dumps({"check_runs": list(check_runs)}))


def gate(status="completed", conclusion="success", name=None, started="2026-10-15T10:00:00Z"):
    return {"name": name or shipflow.GATE, "status": status, "conclusion": conclusion,
            "started_at": started, "html_url": "https://example.invalid/run/1"}


# ----------------------------------------------------------------- the verdict
def test_a_green_gate_is_the_only_pass():
    """Prove the fixture first (defect class 12): if 'pass' were unreachable, every negative
    below would be measuring nothing."""
    assert shipflow.check_state("abc", runs(gate()))[0] == "pass"


@pytest.mark.parametrize("state,run_", [
    ("pending", gate(status="in_progress", conclusion=None)),
    ("pending", gate(status="queued", conclusion=None)),
    ("fail", gate(conclusion="failure")),
    ("fail", gate(conclusion="cancelled")),
    ("fail", gate(conclusion="timed_out")),
    ("fail", gate(conclusion="action_required")),
    ("fail", gate(conclusion="skipped")),
    ("fail", gate(conclusion=None)),
])
def test_everything_that_is_not_success_is_not_a_pass(state, run_):
    """A WILDCARD BRANCH MUST FAIL (defect class 6). `skipped` is the one that matters most: a
    gate that did not run is not a gate that passed, and it is exactly what a `paths:` filter or a
    cancelled workflow produces."""
    got, _ = shipflow.check_state("abc", runs(run_))
    assert got == state, "conclusion %r read as %r" % (run_.get("conclusion"), got)


def test_a_check_for_a_different_job_is_not_our_gate():
    """Another workflow's green check must never be mistaken for the required one."""
    got, detail = shipflow.check_state("abc", runs(gate(name="codeql"), gate(name="uptime")))
    assert got == "missing", detail


def test_an_unreachable_api_is_unknown_not_pass():
    got, _ = shipflow.check_state("abc", lambda a: R("", "gh: could not resolve host", 1))
    assert got == "unknown"


def test_a_non_json_answer_is_unknown_not_pass():
    """An HTML error page parsed as 'no check runs' would read as missing and then, after the
    timeout, look like a transient - when the real answer is "we never saw the gate"."""
    got, detail = shipflow.check_state("abc", lambda a: R("<html>502 Bad Gateway</html>"))
    assert got == "unknown", detail


def test_the_newest_run_wins_so_a_re_run_supersedes_a_failure():
    old = gate(conclusion="failure", started="2026-10-15T09:00:00Z")
    new = gate(conclusion="success", started="2026-10-15T10:00:00Z")
    assert shipflow.check_state("abc", runs(old, new))[0] == "pass"
    assert shipflow.check_state("abc", runs(new, old))[0] == "pass", "order of the array leaked in"


# ----------------------------------------------------------------- waiting
def test_waiting_never_returns_ok_on_a_timeout():
    """A timeout is an UNKNOWN outcome, not a pass (defect class 41)."""
    t = {"now": 0.0}
    ok, detail = shipflow.wait_for_gate(
        "abc", timeout_s=30, poll_s=10,
        runner=runs(gate(status="in_progress", conclusion=None)),
        sleep=lambda s: t.__setitem__("now", t["now"] + s), now=lambda: t["now"])
    assert ok is False
    assert "timed out" in detail and "re-run" in detail, (
        "the timeout does not tell the operator the work is safe and resumable: %s" % detail)


def test_waiting_stops_the_moment_it_is_green():
    seq = [gate(status="queued", conclusion=None), gate(status="in_progress", conclusion=None),
           gate()]
    calls = {"n": 0}

    def runner(args):
        c = seq[min(calls["n"], len(seq) - 1)]
        calls["n"] += 1
        return R(json.dumps({"check_runs": [c]}))

    t = {"now": 0.0}
    ok, _ = shipflow.wait_for_gate("abc", timeout_s=600, poll_s=5, runner=runner,
                                   sleep=lambda s: t.__setitem__("now", t["now"] + s),
                                   now=lambda: t["now"])
    assert ok is True and calls["n"] == 3


def test_a_failing_gate_is_reported_at_once_and_not_waited_out():
    t = {"now": 0.0}
    ok, detail = shipflow.wait_for_gate(
        "abc", timeout_s=600, poll_s=5, runner=runs(gate(conclusion="failure")),
        sleep=lambda s: t.__setitem__("now", t["now"] + 600), now=lambda: t["now"])
    assert ok is False and "failure" in detail
    assert t["now"] == 0.0, "it slept after an answer it already had"


# ----------------------------------------------------------------- branch naming
def test_the_branch_names_the_person_and_cannot_collide_with_its_own_retry():
    a = shipflow.branch_name("fix the deck", who="feran", now=1_760_000_000)
    b = shipflow.branch_name("fix the deck", who="feran", now=1_760_000_060)
    assert a.startswith("ship/feran-") and a != b
    assert "fix-the-deck" in a
    assert " " not in a and ".." not in a, "not a legal git ref: %r" % a


@pytest.mark.parametrize("msg", ["", "   ", "!!!", "ship: engine + web update", "ÄÖÜ"])
def test_a_branch_name_is_always_a_legal_ref(msg):
    import re
    n = shipflow.branch_name(msg, who="dev", now=0)
    assert re.fullmatch(r"ship/[a-z0-9]+-\d{8}-\d{6}-[a-z0-9-]+", n), n


# ----------------------------------------------------------------- the wiring in ship.py
def _main_src():
    tree = ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read())
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    return ast.unparse(fn)


def test_pr_mode_hands_deployment_to_the_pipeline_and_does_not_deploy_itself():
    """THE PROPERTY THAT MATTERS. Merging triggers pipeline.yml. If ship.py deployed as well, one
    commit would again produce two deploys to one droplet."""
    src = _main_src()
    blocks = [n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.If) and "_flow_pr" in ast.unparse(n.test)]
    assert blocks, "ship.py has no PR-mode branch"
    body = ast.unparse(blocks[0])
    assert "shipflow.run" in body, "PR mode does not use the gated flow"
    for forbidden in ("do_web(", "do_bots(", "do_verify(", "tag_known_good("):
        assert forbidden not in body, (
            "PR mode still deploys from the laptop (%s), so a merge would deploy twice" % forbidden)
    assert "return" in body, "PR mode falls through into the direct deploy path"


def test_pr_mode_still_runs_the_collaboration_guards():
    """Branch, stale-tree and rollback-author guards are not made redundant by a PR."""
    blocks = [n for n in ast.walk(ast.parse(_main_src()))
              if isinstance(n, ast.If) and "_flow_pr" in ast.unparse(n.test)]
    assert "collaboration_guards" in ast.unparse(blocks[0])


def test_it_is_still_one_command():
    """ONE ORCHESTRATOR, ONE COMMAND (operating principle 7). The PR flow is a building block
    ship.py drives; shipflow.py stays runnable alone only for debugging."""
    src = _main_src()
    assert "import shipflow" in src, "ship.py does not drive the flow; the operator would have to"
    blocks = [n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.If) and "_flow_pr" in ast.unparse(n.test)]
    body = ast.unparse(blocks[0])
    assert "python shipflow.py" not in body, "it tells the operator to run a second script"


def test_the_flow_can_be_made_the_default_without_a_code_change():
    assert "SHIP_FLOW" in _main_src(), "there is no way to make the PR flow the default"


# ----------------------------------------------------------------- failure is recoverable
def test_a_failed_gate_leaves_the_pr_open_rather_than_destroying_the_evidence():
    src = ast.unparse(ast.parse(open(os.path.join(ROOT, "shipflow.py"), encoding="utf-8").read()))
    i = src.index("gate not green")
    window = src[max(0, i - 600):i]
    for destructive in ("push --delete", "branch -D", "pr close", "reset --hard"):
        assert destructive not in window, (
            "a failed gate destroys the branch or PR that holds the evidence: %r" % destructive)
