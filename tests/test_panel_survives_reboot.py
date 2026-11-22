"""test_panel_survives_reboot.py — THE REVIEWER LIVES IN THE WRITABLE LAYER, AND THE REBOOT TEST
THROWS THAT LAYER AWAY.

WHAT HAPPENED (22 Nov 2026). The first ship in days to get past `modelcheck` finally reached the
staging gate, and the gate said:

    AI panel unavailable — gate decided by 44 deterministic checks (4 failed).
    STAGING GATE: NO-GO
    ...
    GOVERNANCE — the panel has a proposal. Nothing has been executed.
    No failed checks. Nothing to remediate.

Two lines apart: four failed, and no failed checks. Three defects, each with its own repair.

**1. THE PANEL CANNOT SURVIVE THE REBOOT IT IS ASKED TO JUDGE.** `run()` copies quorum.py into
colt-web with `docker cp` - the container's WRITABLE LAYER - and that copy happens BEFORE the
reboot test. Anything that replaces the container in between takes the reviewer with it, and the
panel then reports itself "unavailable" when the truth is that its own code is no longer in there.
The same run's `post_reboot_engine_fresh` proved the container's bytes had changed, which is
exactly that replacement. The copy is idempotent and free, so it is re-done in the same session as
the question, and the container is ASKED whether the file is there.

**2. THE FALLBACK VERDICT DROPPED THE FAILURES.** govern.py reads `verdict["failed"]`. The
fallback dict never had the key, so the governance step announced the opposite of the gate. That is
class 1: a check that cannot see its subject must not report its own blindness as a finding about
the system.

**3. "the container is NOT running what we sent" NAMES A SYMPTOM, NOT A CAUSE.** A stale build and
a replaced container produce the identical line and need opposite repairs. `container_identity`
prints the id, image and start time before and after the reboot, so the pair answers it.

NONE OF THIS WAS CAUSED BY THE MODEL CHANGE. The three previous ships exited at `modelcheck`
before the staging gate ran at all; fixing the chain head is what let the pipeline reach a stage
that had been failing unobserved.
"""
import ast
import importlib.util
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGEGATE = os.path.join(ROOT, "stagegate.py")


def _mod():
    spec = importlib.util.spec_from_file_location("stagegate_t", STAGEGATE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _src():
    return io.open(STAGEGATE, encoding="utf-8").read()


def _code():
    """Source with comments and docstrings removed — a check has matched its own explanatory
    comment five separate times in this repo (class 4)."""
    src = _src()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            d = ast.get_docstring(node, clean=False)
            if d:
                src = src.replace(d, "")
    return "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))


# --------------------------------------------------------------------------- 1. the reviewer

def test_the_reviewer_is_shipped_again_in_the_session_that_asks_the_panel():
    """THE DEFECT VERBATIM. One `docker cp` before a reboot is not a reviewer that is there after
    it. Anchored on the CALL SITE: the ssh_script that runs quorum.py must itself carry ship_q."""
    code = _code()
    i = code.index("python3 /opt/stagegate/quorum.py < /tmp/ev.json")
    # walk back to the ssh_script( that owns this payload
    start = code.rindex("ssh_script(", 0, i)
    call = code[start:i]
    assert "ship_q" in call, (
        "the panel is asked in a session that does not re-ship quorum.py, so any container "
        "replacement between the copy and the question silently disables the panel:\n"
        + call[-400:])


def test_the_container_is_asked_whether_the_reviewer_is_actually_there():
    """A probe that cannot see its subject must not answer (class 1). Without this, a missing
    reviewer and a dead gateway are the same sentence."""
    code = _code()
    assert "docker exec colt-web test -f /opt/stagegate/quorum.py" in code, (
        "nothing verifies the reviewer reached the container")
    assert "PANEL_NO_REVIEWER" in code, "the missing-reviewer case has no distinguishable marker"


def test_a_missing_reviewer_is_diagnosed_rather_than_called_unavailable():
    m = _mod()
    checks = [{"name": "a", "ok": True}, {"name": "b", "ok": False, "detail": "x"}]
    v = m.fallback_verdict(checks, "PANEL_NO_REVIEWER: /opt/stagegate/quorum.py is not in ...")
    assert "REPLACED" in v["digest"], v["digest"]
    assert "container_identity" in v["digest"], (
        "it does not point at the evidence that answers the question")
    # and the generic case stays honest about not knowing
    v2 = m.fallback_verdict(checks, "")
    assert v2["digest"].startswith("AI panel unavailable"), v2["digest"]
    assert "REPLACED" not in v2["digest"], (
        "it invented a cause for a panel that simply did not answer")


# --------------------------------------------------------------------------- 2. the fallback

def test_the_fallback_verdict_carries_the_failed_checks():
    """THE CONTRADICTION. govern.py reads verdict['failed']; without it the governance step says
    'No failed checks' under a gate that just counted four."""
    m = _mod()
    checks = [{"name": "ok_one", "ok": True},
              {"name": "post_reboot_api_auth", "ok": False, "detail": "GET /api/me -> 000"},
              {"name": "post_reboot_engine_fresh", "ok": False, "detail": "container=a shipped=b"}]
    v = m.fallback_verdict(checks, "")
    assert v["gate"] == "NO-GO", v
    assert len(v["failed"]) == 2, v
    assert {c["name"] for c in v["failed"]} == {"post_reboot_api_auth",
                                                "post_reboot_engine_fresh"}, v
    assert "(2 failed)" in v["digest"], v["digest"]


def test_governance_reports_the_same_failures_the_gate_counted(capsys):
    """BEHAVIOUR AND WIRING (class 9). The fallback carrying the key is half of it; govern.py
    actually rendering them is the other half, and that is the line the operator read."""
    m = _mod()
    spec = importlib.util.spec_from_file_location("govern_t", os.path.join(ROOT, "govern.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    checks = [{"name": "post_reboot_api_auth", "ok": False, "detail": "GET /api/me -> 000"}]
    v = m.fallback_verdict(checks, "")
    g.run(v, "staging", "prod", lambda *a, **k: ("", "", 0), lambda *a, **k: None)
    out = capsys.readouterr().out
    assert "No failed checks" not in out, (
        "governance contradicted the gate - the exact line the operator saw:\n" + out)
    assert "post_reboot_api_auth" in out, out


def test_an_all_green_run_still_says_there_is_nothing_to_remediate(capsys):
    """A warning that fires on every run trains the operator to read past the one that matters."""
    m = _mod()
    spec = importlib.util.spec_from_file_location("govern_t2", os.path.join(ROOT, "govern.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    v = m.fallback_verdict([{"name": "a", "ok": True}], "")
    assert v["gate"] == "GO", v
    g.run(v, "staging", "prod", lambda *a, **k: ("", "", 0), lambda *a, **k: None)
    assert "No failed checks" in capsys.readouterr().out


def test_no_checks_at_all_is_not_a_pass():
    """A cut-short run must never be counted as a smaller pass."""
    m = _mod()
    assert m.fallback_verdict([], "")["gate"] == "NO-GO"


# --------------------------------------------------------------------------- 3. the race

def test_the_post_reboot_run_waits_for_the_APP_not_just_for_sshd():
    """THE CAUSE, and the reason this is intermittent rather than new.

    `wait_for_reboot()` waits for a new boot_id over ssh — the BOX. sshd answers in seconds;
    colt-web is python + uvicorn + the engine coming up behind docker's restart policy. The health
    run started the moment ssh answered, so the first three probes hit a port nothing was listening
    on yet (000), while `concurrency` — probing THE SAME 127.0.0.1:8090 a few checks later — got
    forty 401s. The app was not down, it was not up YET.

    That is a race (class 15), which is why the gate passed at 20:01 and failed at 21:15 with
    nothing relevant changed in between."""
    code = _code()
    i = code.index("post = parse_checks(out2)")
    call = code[code.rindex("ssh_script(", 0, i):i]
    assert "wait_for_app=True" in call, (
        "the post-reboot health run does not wait for the app, so it races colt-web's start:\n"
        + call)


def test_the_wait_is_bounded_and_a_timeout_is_a_failure_carrying_the_number():
    """A readiness wait that hides a genuinely dead app is a worse bug than the race it fixes."""
    m = _mod()
    w = m.READY_WAIT
    assert "chk app_ready no" in w, "running out of time is not reported as a failure"
    assert "${_t}s" in w, "neither branch reports how long it actually waited"
    assert "seq 1 90" in w, "the wait is unbounded"
    assert "chk app_ready yes" in w and "after ${_t}s" in w, (
        "the PASS does not say how long the app took, so a box that is degrading towards the "
        "limit looks identical to a healthy one until the day it trips")


def test_the_wait_runs_after_chk_is_defined_and_only_after_the_reboot():
    """`chk` is the CHECK-line protocol and has ONE definition. Prepending the wait to the whole
    script would run it before that function exists."""
    m = _mod()
    with_wait = m.health_script(wait_for_app=True)
    assert with_wait.index("chk() {") < with_wait.index("app_ready"), (
        "the readiness wait calls chk before chk is defined")
    assert "app_ready" not in m.health_script(), (
        "the pre-reboot run also waits, which measures nothing and hides a slow first start")
    assert m.health_script() == m.HEALTH, "the no-wait path is no longer the plain script"


def test_the_anchor_is_proven_rather_than_assumed():
    """A silent no-op injection would put the gate straight back into the race it was built to
    close, and nothing would say so (class 37)."""
    import pytest
    m = _mod()
    real, m.HEALTH = m.HEALTH, "no preamble here"
    try:
        with pytest.raises(AssertionError):
            m.health_script(wait_for_app=True)
    finally:
        m.HEALTH = real


# --------------------------------------------------------------------------- 4. identity

def test_the_health_run_prints_which_container_and_image_answered():
    """engine_fresh says the bytes differ. A stale build and a REPLACED container produce that
    same line and need opposite repairs, so the identity is printed either way - before and after
    the reboot, because one id means nothing without the other to compare it to (class 26)."""
    health = _src()
    assert "chk container_identity" in health, "the container's identity is never reported"
    for field in ("{{.Id}}", "{{.Image}}", "{{.State.StartedAt}}",
                  "{{json .NetworkSettings.Ports}}"):
        assert field in health, "container_identity does not report %s" % field
    # It must sit inside HEALTH, which is what the post_reboot_ pass re-runs; a check that only
    # runs once cannot answer a question about a change across the reboot.
    body = re.search(r"HEALTH\s*=\s*r?['\"]{3}(.*?)['\"]{3}", health, re.S)
    assert body and "container_identity" in body.group(1), (
        "container_identity is not in the HEALTH script, so it never gets a post_reboot_ twin - "
        "and a single identity line cannot show a replacement")
