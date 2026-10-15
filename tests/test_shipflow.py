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


# ----------------------------------------------------------------- RESUME (the defect of 2026-10-15)
# A red gate on PR #19 left the operator ON the ship/ branch, which is correct: the branch and the
# PR are the evidence of what failed. The next `python ship.py --pr` then did two wrong things, and
# his own guard caught the louder one:
#
#   [!] you are on branch 'ship/feran-...', not 'main'.
#   [X] refusing to deploy from 'ship/feran-...'.
#
#   1. ship.py called collaboration_guards(deploying=True). That guard is fatal off main because
#      MAIN IS WHAT DEPLOYS - but in PR mode the laptop deploys nothing, and standing on a ship/
#      branch is the normal mid-flow state.
#   2. shipflow would have cut a SECOND ship/ branch from the first, orphaning the open PR and
#      carrying the old branch's history into the new one.
#
# "Resumable by construction" was in the docstring with nothing asserting it - a claim, not a
# property (defect class 3). These tests run the real thing against a real git repo.

@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway git repo with an origin, so the flow runs for real instead of against mocks."""
    import subprocess as sp
    if not __import__("shutil").which("git"):
        pytest.skip("git not available")
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    sp.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
    sp.run(["git", "clone", str(origin), str(work)], check=True, capture_output=True)
    for k, v in (("user.email", "t@example.invalid"), ("user.name", "T"), ("commit.gpgsign", "false")):
        sp.run(["git", "-C", str(work), "config", k, v], check=True, capture_output=True)
    (work / "a.txt").write_bytes(b"one\n")
    sp.run(["git", "-C", str(work), "add", "-A"], check=True, capture_output=True)
    sp.run(["git", "-C", str(work), "commit", "-m", "init"], check=True, capture_output=True)
    sp.run(["git", "-C", str(work), "push", "-u", "origin", "main"], check=True, capture_output=True)
    monkeypatch.setattr(shipflow, "HERE", str(work))
    return work


def test_a_red_gate_leaves_you_on_the_branch_and_the_next_run_resumes_it(repo, monkeypatch):
    """THE PROPERTY. Two runs, one branch, one PR - not a second branch cut from the first."""
    seen = {"prs": [], "merged": []}
    monkeypatch.setattr(shipflow, "open_pr",
                        lambda br, msg, base=None: (seen["prs"].append(br), (7, "url"))[1])
    monkeypatch.setattr(shipflow, "merge_pr",
                        lambda n, method="squash": (seen["merged"].append(n), (True, "merged"))[1])

    # Run 1: the gate fails. The flow must stop and leave us standing on the branch.
    monkeypatch.setattr(shipflow, "wait_for_gate", lambda *a, **k: (False, "concluded failure"))
    (repo / "b.txt").write_bytes(b"two\n")
    ok, info = shipflow.run("first try")
    assert ok is False and "gate not green" in info["error"]
    first = info["branch"]
    on = (shipflow._git("rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
    assert on == first, "a red gate did not leave the work on its branch (on %r)" % on

    # Run 2: the fix lands, the gate is green. SAME branch, SAME PR.
    monkeypatch.setattr(shipflow, "wait_for_gate", lambda *a, **k: (True, "ok"))
    (repo / "b.txt").write_bytes(b"two, fixed\n")
    ok, info2 = shipflow.run("second try")
    assert ok is True, info2
    assert info2["branch"] == first, (
        "the second run cut a NEW branch (%s) instead of resuming %s, orphaning the open PR"
        % (info2["branch"], first))
    assert seen["prs"] == [first, first], "open_pr was not asked for the same branch twice"
    assert seen["merged"] == [7]


def test_resuming_returns_to_main_after_the_merge(repo, monkeypatch):
    monkeypatch.setattr(shipflow, "open_pr", lambda br, msg, base=None: (3, "url"))
    monkeypatch.setattr(shipflow, "merge_pr", lambda n, method="squash": (True, "merged"))
    monkeypatch.setattr(shipflow, "wait_for_gate", lambda *a, **k: (False, "failure"))
    (repo / "c.txt").write_bytes(b"x\n")
    shipflow.run("one")
    monkeypatch.setattr(shipflow, "wait_for_gate", lambda *a, **k: (True, "ok"))
    (repo / "c.txt").write_bytes(b"y\n")
    assert shipflow.run("two")[0] is True
    on = (shipflow._git("rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
    assert on == "main", "after a resumed merge the operator is left on %r, not main" % on


def test_pr_mode_does_not_use_the_deploying_branch_guard():
    """collaboration_guards(deploying=True) is fatal off main because MAIN IS WHAT DEPLOYS. PR
    mode deploys nothing from the laptop, so passing True made the flow refuse to resume the very
    branch a red gate is meant to leave behind."""
    blocks = [n for n in ast.walk(ast.parse(_main_src()))
              if isinstance(n, ast.If) and "_flow_pr" in ast.unparse(n.test)]
    body = ast.unparse(blocks[0])
    assert "collaboration_guards(deploying=False)" in body, (
        "PR mode still uses the deploying guard; it cannot resume its own branch")
    assert "collaboration_guards(deploying=True)" not in body


# ----------------------------------------------------------------- failure is recoverable
def test_a_failed_gate_leaves_the_pr_open_rather_than_destroying_the_evidence():
    src = ast.unparse(ast.parse(open(os.path.join(ROOT, "shipflow.py"), encoding="utf-8").read()))
    i = src.index("gate not green")
    window = src[max(0, i - 600):i]
    for destructive in ("push --delete", "branch -D", "pr close", "reset --hard"):
        assert destructive not in window, (
            "a failed gate destroys the branch or PR that holds the evidence: %r" % destructive)
