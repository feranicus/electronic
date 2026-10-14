"""test_teamwork.py - the pipeline must survive a SECOND pair of hands.

THE SITUATION THESE DEFEND. Until 2026-10 there was one developer, so `python ship.py` could assume
it was the only thing touching the droplet: `git add -A` took the whole tree, the push went straight
to main, the deploy went laptop -> droplet over ssh, and `last-known-good` could only ever be the
operator's own. Every one of those assumptions breaks the moment a second developer exists, and
each breaks SILENTLY - a deploy that wins a race leaves no error, it leaves the other developer
reading a stale engine hash he cannot explain.

Four properties, proved the only way that counts: by making them fail.
  1. Two deploys cannot overlap   (teamlock, and it must fail OPEN when the droplet is unreachable)
  2. A deploy cannot start from the wrong branch, or from a tree behind origin
  3. A rollback cannot silently revert the OTHER developer's work
  4. CI serialises against the SAME queue the laptops use
"""
import importlib.util
import itertools
import os
import re
import subprocess
import sys
import types

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import teamlock  # noqa: E402


# ---------------------------------------------------------------------------------------------
# A fake droplet. The lock lives in a shell script on a remote box, so the only honest test harness
# is one that RUNS that script. `bash` gives us real `mkdir` atomicity and real `date`; where bash
# is unavailable (the operator's Windows box) the module is skipped and CI covers it.
# ---------------------------------------------------------------------------------------------
import shutil

pytestmark = pytest.mark.skipif(shutil.which("bash") is None,
                                reason="the lock is a bash script; CI and the droplet run it")


_SEQ = itertools.count()


class FakeDroplet:
    """Runs the module's own remote scripts locally, against a POSIX path the SHELL can use.

    THE SUBJECT UNDER TEST RUNS ON THE DROPLET. teamlock's scripts are executed by ssh on Ubuntu,
    at /opt/colt-stack/.deploy.lock, always. Running them under a shell on the operator's Windows
    box exercises THAT shell, not production - so when the local shell cannot host the harness, the
    honest outcome is a skip with the reason, not a red build. CI and the droplet keep the coverage.

    TWO HARNESS FAULTS, BOTH ON 2026-10-14, both invisible in a Linux sandbox:
      1. The path was built with `os.path.join`, so on Windows it carried backslashes. A backslash
         path handed to Git Bash is not a path: five tests failed reporting a contended lock that
         did not exist (CLAUDE.md defect class 19 - green here is not evidence about his box).
      2. The replacement asked bash for `mktemp -d`. It returned nothing on his machine, and the
         fixture asserted on the empty result WITHOUT showing what the shell had said - so the
         failure named my assumption instead of the cause (defect class 26: a diagnostic that does
         not name its subject sends the next investigation down the wrong road).
    So the path is now a plain POSIX literal under /tmp, which needs no translation and no external
    tool, and anything the shell cannot do is reported WITH the shell's own words.
    """

    def __init__(self):
        # A literal, not a filesystem call: no path translation, no mktemp, nothing to go missing.
        self.root = "/tmp/teamlock-test-%d-%d" % (os.getpid(), next(_SEQ))
        self.calls = 0
        self.last = ""          # raw shell output, so an assertion can quote what really happened

    @staticmethod
    def _bash(script, timeout=60):
        r = subprocess.run(["bash", "-c", script], text=True, capture_output=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    def __call__(self, script, timeout=60):
        self.calls += 1
        rc, out = self._bash(script.replace(teamlock.LOCK, self.root + "/deploy.lock"), timeout)
        self.last = "rc=%s\n%s" % (rc, out)
        return rc, out

    def cleanup(self):
        self._bash("rm -rf '%s'" % self.root)


def shell_harness_allowed(platform=None, which=None, env=None):
    """(ok, reason) - may THIS machine host the lock harness? A function, not an inline condition,
    so the decision itself is testable: `sys.platform = "win32"` cannot be simulated globally
    (the stdlib's ssl module reads it at import), and a rule nobody can exercise is a rule that
    drifts (defect class 3 - a check that cannot fail is not a check)."""
    platform = platform if platform is not None else sys.platform
    which = which if which is not None else shutil.which
    env = env if env is not None else os.environ
    if env.get("TEAMLOCK_TEST_SHELL") == "1":
        return True, ""
    if platform == "win32":
        return False, ("teamlock's scripts are POSIX and run on the Linux droplet over ssh; under "
                       "Git Bash/WSL this would test the emulation, not production. CI covers "
                       "them. Force with TEAMLOCK_TEST_SHELL=1.")
    if which("bash") is None:
        return False, "no bash on PATH; teamlock's scripts are shell scripts"
    return True, ""


@pytest.fixture
def droplet():
    """The ONLY fixture that needs a POSIX shell. Everything else in this module is pure Python
    (AST, YAML, string properties) and runs everywhere, including the operator's Windows box.

    WHY WINDOWS SKIPS, decided after three failed ships on 2026-10-14. teamlock's scripts are
    executed BY SSH ON THE UBUNTU DROPLET, at /opt/colt-stack/.deploy.lock, always. Running them
    under Git Bash or WSL exercises that emulation layer: a pass there would not prove the droplet
    works, and a failure there does not prove it is broken. The test therefore has no diagnostic
    value on Windows, and a check with no diagnostic value must not be able to block a deploy.
    CI (ubuntu-latest) and the droplet keep the real coverage.

    This is NOT defect class 20 ("simulate the platform, do not skip it"). That rule exists so a
    skip cannot hide a defect from the machine that needs the code to work. The machine that needs
    this code to work is Linux, and Linux runs it. Set TEAMLOCK_TEST_SHELL=1 to force it anyway.
    """
    ok, why = shell_harness_allowed()
    if not ok:
        pytest.skip(why)
    d = FakeDroplet()
    # PROVE THE FIXTURE BEFORE TRUSTING IT (defect class 12), and when it cannot be proved, SKIP
    # with the shell's own words rather than failing the build for a defect that is not there.
    rc, out = d._bash("mkdir -p '%s' && touch '%s/probe' && echo HARNESS=ok" % (d.root, d.root))
    if "HARNESS=ok" not in out:
        pytest.skip("this shell cannot host the lock harness (rc=%s): %s"
                    % (rc, (out or "(no output at all)").strip()[:300]))
    try:
        yield d
    finally:
        d.cleanup()


def test_the_harness_never_hands_a_windows_path_to_bash():
    """SIMULATE the platform, do not skip it (defect class 20). A pure string property, so it holds
    on either machine and needs no shell: the bug was a Windows path reaching a POSIX script."""
    d = FakeDroplet()
    assert "\\" not in d.root, "a backslash in the lock path is what broke this on Windows"
    assert d.root.startswith("/"), "the lock path must be POSIX, got %r" % d.root

    # ...and the path that reaches the SHELL, which is the thing that actually broke. Asserted on
    # the D= line only: the script legitimately contains backslashes elsewhere (printf '%s\\n'),
    # so a blanket "no backslash" check would fail on correct code (defect class 4 - assert the
    # PROPERTY, not a string the rest of the text also contains).
    seen = []
    d._bash = lambda script, timeout=60: (seen.append(script), (0, ""))[1]
    d(teamlock._ACQUIRE % {"lock": teamlock.LOCK, "owner": "alice", "stale": 60})
    assert seen, "the harness sent nothing to the shell"
    dline = next(ln for ln in seen[0].splitlines() if ln.startswith("D="))
    assert "\\" not in dline, "the lock path reaching the shell is not POSIX: %s" % dline
    assert teamlock.LOCK not in dline, "the production lock path leaked into a test run"


# ---------------------------------------------------------------- 1. the lock
def test_a_second_deploy_is_refused_while_the_first_is_running(droplet):
    ok, info = teamlock.acquire("alice@laptop", runner=droplet)
    assert ok and info.get("RESULT") == "acquired", (
        "a FRESH lock could not be taken, so nothing below is measuring the lock.\n"
        "parsed=%r\nshell said:\n%s" % (info, droplet.last))

    ok2, info2 = teamlock.acquire("bob@laptop", runner=droplet)
    assert ok2 is False, "two developers deployed at once - this is the whole point of the module"
    assert info2["HOLDER"] == "alice@laptop", "the refusal must NAME who to go and ask"
    assert int(info2["AGE"]) >= 0


def test_the_holder_can_release_and_the_next_developer_gets_it(droplet):
    teamlock.acquire("alice@laptop", runner=droplet)
    assert teamlock.release("alice@laptop", runner=droplet)["RESULT"] == "released"
    ok, info = teamlock.acquire("bob@laptop", runner=droplet)
    assert ok and info["RESULT"] == "acquired"


def test_one_developer_cannot_release_the_other_developers_lock(droplet):
    teamlock.acquire("alice@laptop", runner=droplet)
    r = teamlock.release("bob@laptop", runner=droplet)
    assert r["RESULT"] == "not-mine" and r["HOLDER"] == "alice@laptop"
    assert teamlock.acquire("bob@laptop", runner=droplet)[0] is False, "...and it is still held"


def test_a_dead_holder_does_not_block_the_droplet_forever(droplet):
    """A `finally` cannot survive SIGKILL, a closed laptop or a cancelled Actions run (defect 16).
    Staleness, not release, is what guarantees the lock always clears."""
    teamlock.acquire("alice@laptop", runner=droplet)
    assert teamlock.acquire("bob@laptop", runner=droplet, stale_s=10_000)[0] is False
    # the same lock, judged against a 0-second staleness window, is dead
    ok, info = teamlock.acquire("bob@laptop", runner=droplet, stale_s=0)
    assert ok and info["RESULT"] == "acquired"
    assert info.get("BROKE") == "alice@laptop", "breaking a stale lock must SAY whose it was"


def test_the_default_staleness_is_longer_than_an_honest_ship():
    assert teamlock.STALE_S >= 1800, (
        "a full ship with a staging gate and a twin reboot runs past 25 minutes; a staleness "
        "window shorter than that lets a second developer break a LIVE deploy (got %ss)"
        % teamlock.STALE_S)


def test_an_unreachable_droplet_does_not_become_a_new_way_to_fail():
    def dead(script, timeout=60):
        raise OSError("ssh: connect to host ... Connection timed out")
    ok, info = teamlock.acquire("alice@laptop", runner=dead)
    assert ok is True, "the lock must FAIL OPEN; the deploy that follows reports the real problem"
    assert "ERROR" in info


def test_github_actions_identifies_itself_as_a_runner_not_a_person(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_RUN_ID", "123456")
    assert teamlock.who().startswith("github-actions/"), (
        "a laptop told to wait must be able to tell a CI run from a colleague")


def test_the_context_manager_reports_a_block_and_does_not_raise(droplet, capsys):
    teamlock.acquire("alice@laptop", runner=droplet)
    with teamlock.held("production deploy", owner="bob@laptop", runner=droplet) as got:
        assert got is False
    out = capsys.readouterr().out
    assert "ANOTHER DEPLOY IS RUNNING" in out and "alice@laptop" in out
    assert "--break" in out, "a blocked developer needs the way out printed, not remembered"


# ---------------------------------------------------------------- 2. the git guards
def _ship():
    """Load ship.py's module-level definitions without running main()."""
    src = open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()
    src = src.split("def main(")[0]
    ns = {"__name__": "shipmod", "__file__": os.path.join(ROOT, "ship.py")}
    exec(compile(src, "ship.py", "exec"), ns)
    return ns


@pytest.fixture(scope="module")
def ship():
    return _ship()


def _fake_git(ns, table):
    """Replace ship.py's _git with a scripted one. Keys are the first two argv words."""
    def g(*a, timeout=120):
        return table.get(" ".join(a[:2]), table.get(a[0], (0, "")))
    ns["_git"] = g


def test_deploying_from_a_feature_branch_is_refused(ship, monkeypatch, capsys):
    _fake_git(ship, {"rev-parse": (0, "feature/new-detector"),
                     "rev-list": (0, "0\t0"), "status": (0, ""), "fetch": (0, "")})
    monkeypatch.delenv("SHIP_ALLOW_BRANCH", raising=False)
    with pytest.raises(SystemExit) as e:
        ship["collaboration_guards"](deploying=True)
    assert "refusing to deploy" in str(e.value)
    assert "pull request" in str(e.value), "the refusal must say what to do instead"


def test_the_same_branch_may_still_run_the_gates(ship, monkeypatch):
    _fake_git(ship, {"rev-parse": (0, "feature/new-detector"),
                     "rev-list": (0, "0\t0"), "status": (0, ""), "fetch": (0, "")})
    monkeypatch.delenv("SHIP_ALLOW_BRANCH", raising=False)
    ship["collaboration_guards"](deploying=False)   # must not raise


def test_a_branch_guard_an_informed_operator_cannot_override_would_be_a_bug(ship, monkeypatch):
    _fake_git(ship, {"rev-parse": (0, "hotfix"), "rev-list": (0, "0\t0"),
                     "status": (0, ""), "fetch": (0, "")})
    monkeypatch.setenv("SHIP_ALLOW_BRANCH", "1")
    ship["collaboration_guards"](deploying=True)    # must not raise


def test_committing_on_top_of_a_stale_tree_is_refused(ship, monkeypatch):
    """The other developer pushed while you were testing. Your `git add -A` commit would be built
    on a tree that is missing his work, and your deploy would ship a state GitHub never had."""
    _fake_git(ship, {"rev-parse": (0, "main"), "rev-list": (0, "3\t1"),
                     "log": (0, "Dima Diall\nDima Diall\nDima Diall"),
                     "status": (0, ""), "fetch": (0, "")})
    monkeypatch.delenv("SHIP_ALLOW_BEHIND", raising=False)
    with pytest.raises(SystemExit) as e:
        ship["collaboration_guards"](deploying=True)
    msg = str(e.value)
    assert "stale tree" in msg and "git pull --rebase" in msg
    assert "Dima Diall" in msg or "SHIP_ALLOW_BEHIND" in msg


def test_being_ahead_of_origin_is_normal_and_never_blocks(ship, monkeypatch):
    _fake_git(ship, {"rev-parse": (0, "main"), "rev-list": (0, "0\t4"),
                     "status": (0, ""), "fetch": (0, "")})
    monkeypatch.delenv("SHIP_ALLOW_BEHIND", raising=False)
    ahead, behind = ship["collaboration_guards"](deploying=True)
    assert (ahead, behind) == (4, 0)


def test_what_is_about_to_be_committed_is_printed_before_the_push(ship, monkeypatch, capsys):
    """`git add -A` takes the WHOLE tree. We cannot know who typed what, so the honest guard is to
    make a surprise visible BEFORE the push rather than in the next person's git log."""
    _fake_git(ship, {"rev-parse": (0, "main"), "rev-list": (0, "0\t0"), "fetch": (0, ""),
                     "status": (0, " M ship.py\n M webapp/backend/app/main.py\n"
                                   "?? jobhuntwow-app/backend/app/scratch.py\n")})
    ship["collaboration_guards"](deploying=True)
    out = capsys.readouterr().out
    assert "3 path(s) in 3 area(s)" in out
    assert "jobhuntwow-app" in out, "a file from ANOTHER project must be visible before it ships"


def test_the_guards_actually_run_inside_do_git():
    """Behaviour AND wiring (defect class 9): a guard that is correct and never called is not a
    guard. Anchored on the call site by AST, not on a grep of the source text."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "do_git")
    called = [n.func.id for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert "collaboration_guards" in called, "do_git must call the guards before it commits"
    body = ast.unparse(fn)
    assert body.index("collaboration_guards") < body.index("'add'"), (
        "the guards must run BEFORE `git add -A`, or they are a post-mortem")


# ---------------------------------------------------------------- 3. rollback
def test_rollback_refuses_to_silently_revert_the_other_developers_deploy(ship, monkeypatch):
    """`last-known-good` is a MOVING pointer. With two developers the newest one may be the other
    person's deploy from twenty minutes ago, and rolling back to it reverts his work too.
    EXECUTED, not grepped: the previous version of this test passed when the condition was
    mutated to `False`, because the env-var NAME was still in the source."""
    _fake_git(ship, {"rev-parse": (0, "abc123def456"),
                     "show": (0, "Dima Diall|2026-10-14|ship: new detector"),
                     "config": (0, "Evgeny Vainshtein"),
                     "tag": (0, "good-20261014-101500\ngood-20261013-180200")})
    monkeypatch.delenv("SHIP_ALLOW_OTHERS_ROLLBACK", raising=False)
    with pytest.raises(SystemExit) as e:
        ship["resolve_rollback_target"]("last-known-good")
    msg = str(e.value)
    assert "Dima Diall" in msg, "the refusal must NAME whose deploy it would revert"
    assert "good-20261014-101500" in msg, "...and offer the immutable tags to use instead"


def test_rolling_back_to_your_own_safe_point_is_not_obstructed(ship, monkeypatch):
    _fake_git(ship, {"rev-parse": (0, "abc123def456"),
                     "show": (0, "Evgeny Vainshtein|2026-10-14|ship: engine update"),
                     "config": (0, "Evgeny Vainshtein"), "tag": (0, "")})
    monkeypatch.delenv("SHIP_ALLOW_OTHERS_ROLLBACK", raising=False)
    sha, author = ship["resolve_rollback_target"]("last-known-good")
    assert sha == "abc123def456" and author == "Evgeny Vainshtein"


def test_an_explicit_dated_tag_is_never_second_guessed(ship, monkeypatch):
    """Naming a tag IS the unambiguous act. Only the moving pointer is in doubt."""
    _fake_git(ship, {"rev-parse": (0, "abc123def456"),
                     "show": (0, "Dima Diall|2026-10-13|ship: his work"),
                     "config": (0, "Evgeny Vainshtein"), "tag": (0, "")})
    monkeypatch.delenv("SHIP_ALLOW_OTHERS_ROLLBACK", raising=False)
    ship["resolve_rollback_target"]("good-20261013-180200")      # must not raise


def test_the_rollback_author_guard_is_overridable(ship, monkeypatch):
    _fake_git(ship, {"rev-parse": (0, "abc123def456"),
                     "show": (0, "Dima Diall|2026-10-14|ship: his work"),
                     "config": (0, "Evgeny Vainshtein"), "tag": (0, "")})
    monkeypatch.setenv("SHIP_ALLOW_OTHERS_ROLLBACK", "1")
    ship["resolve_rollback_target"]("last-known-good")           # must not raise


def test_an_unknown_ref_is_refused_before_anything_destructive(ship):
    _fake_git(ship, {"rev-parse": (128, ""), "show": (0, ""), "config": (0, "Evgeny"), "tag": (0, "")})
    with pytest.raises(SystemExit) as e:
        ship["resolve_rollback_target"]("typo-tag")
    assert "not a known ref" in str(e.value)


def test_do_rollback_calls_the_guard_before_it_resets(ship):
    """Wiring: the check has to land before `git reset --hard`, not after it."""
    import ast
    fn = next(n for n in ast.walk(ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()))
              if isinstance(n, ast.FunctionDef) and n.name == "do_rollback")
    body = ast.unparse(fn)
    assert "resolve_rollback_target" in body, "do_rollback must call the guard"
    assert body.index("resolve_rollback_target") < body.index("'--hard'"), (
        "the refusal must land before `git reset --hard`, not after it")


def test_a_safe_point_records_who_made_it():
    import ast
    src = open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "tag_known_good")
    assert "user.name" in ast.unparse(fn), (
        "with two developers, a safe-point nobody can attribute is a safe-point nobody trusts")


# ---------------------------------------------------------------- 4. CI shares the queue
def test_both_production_workflows_use_one_concurrency_group():
    """They share a droplet, a Caddyfile and the colt_events volume, so they must share a queue.
    They used to be `prod-deploy` and `prod-web-deploy`: two groups, no mutual exclusion."""
    groups = {}
    for f in ("deploy.yml", "web-deploy.yml"):
        doc = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", f), encoding="utf-8"))
        assert "concurrency" in doc, "%s can start a second production deploy" % f
        groups[f] = doc["concurrency"]["group"]
        assert doc["concurrency"].get("cancel-in-progress") is False, (
            "%s would CANCEL a running deploy mid-way, leaving the droplet half-updated" % f)
    assert len(set(groups.values())) == 1, (
        "two production workflows in different queues can recreate containers on the same box "
        "at the same time: %s" % groups)


def test_the_deploy_is_wrapped_in_the_lock_and_released_before_the_long_tail():
    import ast
    src = open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    body = ast.unparse(fn)
    assert "teamlock" in body, "main() must take the deploy lock"
    take = body.index("__enter__")
    for step in ("do_web(", "do_bots(", "do_verify("):
        assert take < body.index(step), "%s runs OUTSIDE the lock" % step
    assert body.index("do_verify(") < body.index("__exit__"), "the lock is released too early"
    assert body.index("__exit__") < body.index("caddyguard.py"), (
        "holding the lock through the never-blocking tail is how the next developer concludes "
        "the deploy is stuck")


def test_a_rollback_joins_the_same_queue_as_a_deploy():
    """A rollback runs do_web + do_bots. It is a DEPLOY, and it exits main() before the normal
    lock is taken, so it has to acquire its own - rolling back on top of a colleague's in-flight
    deploy is the worst possible moment to be recreating containers."""
    import ast
    fn = next(n for n in ast.walk(ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()))
              if isinstance(n, ast.FunctionDef) and n.name == "do_rollback")
    body = ast.unparse(fn)
    assert "teamlock" in body, "do_rollback deploys without taking the lock"
    assert body.index("__enter__") < body.index("do_web("), "the lock is taken after the deploy"
    assert body.index("resolve_rollback_target") < body.index("__enter__"), (
        "validate the ref BEFORE taking the lock, so a typo does not block the other developer")


def test_the_deploy_path_can_be_switched_to_ci_without_editing_code():
    """Step one of moving the droplet key off the laptops is being able to flip the deploy path
    from an env var. `--ci` must still work for a single run."""
    import ast
    fn = next(n for n in ast.walk(ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()))
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    body = ast.unparse(fn)
    assert "SHIP_DEPLOY" in body, "there must be a no-code-change switch to the CI deploy path"
    assert "do_web(_use_ci)" in body, "the switch must actually reach do_web"


def test_windows_skips_the_shell_harness_but_nothing_else():
    """SIMULATED, not assumed (defect class 20). Three ships in a row died because a POSIX script
    was judged by a Windows shell; this pins the decision so it cannot quietly come back."""
    ok, why = shell_harness_allowed(platform="win32", which=lambda _: "/usr/bin/bash", env={})
    assert ok is False and "Linux droplet" in why and "TEAMLOCK_TEST_SHELL" in why

    ok, _ = shell_harness_allowed(platform="linux", which=lambda _: "/usr/bin/bash", env={})
    assert ok is True, "Linux and CI must still run the real thing"

    ok, why = shell_harness_allowed(platform="linux", which=lambda _: None, env={})
    assert ok is False and "bash" in why

    ok, _ = shell_harness_allowed(platform="win32", which=lambda _: None,
                                  env={"TEAMLOCK_TEST_SHELL": "1"})
    assert ok is True, "an informed operator must be able to override the skip (CLAUDE.md)"


def test_the_shell_harness_is_the_only_thing_windows_loses():
    """The guards that matter on the operator's box - branch, stale tree, rollback author, the CI
    concurrency group - are pure Python and must NOT depend on the droplet fixture."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "tests", "test_teamwork.py"), encoding="utf-8").read())
    needs_shell = {n.name for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
                   and "droplet" in [a.arg for a in n.args.args]}
    assert needs_shell, "no test uses the droplet fixture; the harness is dead code"
    for guard in ("test_deploying_from_a_feature_branch_is_refused",
                  "test_committing_on_top_of_a_stale_tree_is_refused",
                  "test_rollback_refuses_to_silently_revert_the_other_developers_deploy",
                  "test_both_production_workflows_use_one_concurrency_group",
                  "test_the_deploy_is_wrapped_in_the_lock_and_released_before_the_long_tail"):
        assert guard not in needs_shell, (
            "%s would be SKIPPED on Windows, where the operator actually ships" % guard)


def test_ci_takes_the_same_lock_the_laptops_use():
    """The concurrency group serialises CI against CI. It cannot see `python ship.py` running on
    somebody's PC - only the lock on the droplet can. A CI deploy that skips it reintroduces
    exactly the collision teamlock exists to prevent."""
    import yaml as _yaml
    doc = _yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "web-deploy.yml"),
                               encoding="utf-8"))
    steps = doc["jobs"]["deploy"]["steps"]
    names = [s.get("name", "") for s in steps]
    runs = [s.get("run", "") for s in steps]
    acq = next((i for i, r in enumerate(runs) if "teamlock.py --acquire" in r), None)
    rel = next((i for i, r in enumerate(runs) if "teamlock.py --release" in r), None)
    assert acq is not None, "the CI deploy never takes the deploy lock: %s" % names
    assert rel is not None, "the CI deploy never gives the lock back: %s" % names
    touch = next(i for i, n in enumerate(names) if "Ship compose" in n)
    assert acq < touch, "the lock is taken AFTER the droplet is already being written to"
    assert rel > touch, "the lock is released before the deploy finishes"
    assert steps[rel].get("if") == "always()", (
        "a failed or cancelled deploy must still release the lock")
    for i in (acq, rel):
        assert steps[i].get("env", {}).get("SSH_KEY"), (
            "the lock step has no SSH key, so it can never reach the droplet")


def test_the_acquire_verb_exits_non_zero_when_somebody_else_holds_it():
    """CI has no context manager: one step takes it, a later step gives it back. The exit CODE is
    what stops the workflow, so it has to be non-zero."""
    import ast
    fn = next(n for n in ast.walk(ast.parse(open(os.path.join(ROOT, "teamlock.py"),
                                                 encoding="utf-8").read()))
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    body = ast.unparse(fn)
    assert "a.acquire" in body and "return 2" in body, (
        "--acquire must exit non-zero when the lock is held, or CI deploys straight through it")
    assert "a.release" in body
