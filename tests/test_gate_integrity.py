"""test_gate_integrity.py — the gate must not be able to lie, and a unanimous panel must be heard.

THE INCIDENT THIS PINS (2026-08-07, promoted to production on a green gate):

    mount_fresh    OK   container reads the current file (3af610cdeb71) - bind mount is not stale
    config_drift   OK   drift check unavailable: STALE MOUNT STALE MOUNT: host= container=3af610cdeb71
    GATE: GO (33/33)
    ...all four reviewers: NO-GO, all four naming config_drift...
    STAGING GATE: GO   -> deployed to production

Three separate defects composed into a false green:

  1. `agent.py` hashed a HARDCODED host path (production's /opt/videodead/Caddyfile). Staging's
     proxy mounts a different file, so the host hash came back EMPTY and mount_sync read "no file"
     as "stale mount". Absence of evidence became a finding — the oldest rule in this repo.
  2. `stagegate`'s case statement had a catch-all that scored an UNRECOGNISED verdict as a PASS
     (`chk config_drift yes "drift check unavailable: $D"`). A fallback that turns an unknown
     answer into success is strictly worse than having no check at all.
  3. Nothing noticed that a check reporting PASS had "STALE MOUNT" in its own detail. All four
     models did notice, in four different sentences — and the architecture gave their unanimous
     dissent no power to stop anything.

The fixes are asserted below. Note what is NOT changed: models still cannot veto a release. The
deterministic checks decide. What is new is that UNANIMOUS dissent against a green gate halts and
asks a human, because that specific pattern has now twice meant "a check is lying".
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_s = importlib.util.spec_from_file_location("stagegate", os.path.join(ROOT, "stagegate.py"))
sg = importlib.util.module_from_spec(_s)
sys.modules["stagegate"] = sg
_s.loader.exec_module(sg)


# ---------------------------------------------------------------- 1. the self-contradiction rule
def test_the_exact_line_that_shipped_is_now_a_failure():
    """Verbatim from the 2026-08-07 run. It reported PASS; it must now be a FAILURE."""
    line = ("CHECK|config_drift|yes|drift check unavailable: STALE MOUNT STALE MOUNT: "
            "host= container=3af610cdeb71    the cont")
    (c,) = sg.parse_checks(line)
    assert c["ok"] is False, "the line that fooled the gate still passes"
    assert "SELF-CONTRADICTORY" in c["detail"]
    assert "stale" in c["detail"].lower()


def test_healthy_details_are_not_flagged():
    """A guard that cries wolf gets ignored. These are all REAL passing details from live runs."""
    benign = [
        "CHECK|config_drift|yes|running config serves exactly what the file says (11 host(s), 9 handler(s))",
        "CHECK|config_drift|yes|running config == file on disk (e774f8ef1e33) - no silent drift",
        "CHECK|mount_fresh|yes|container reads the current file (3af610cdeb71) - bind mount is not stale",
        "CHECK|config_drift|yes|admin API unreachable (nothing to compare - not a fault)",
        "CHECK|engine_runs|yes|3 decks + 39256b html, zero undefined/NaN leaks (output CHECKED, not just exit 0)",
        "CHECK|api_auth|yes|GET /api/me -> 401 (up + locked)",
        "CHECK|bot_gate|yes|a bot UA still gets 404",
        "CHECK|restart_count|yes|restarts=0",
    ]
    for ln in benign:
        (c,) = sg.parse_checks(ln)
        assert c["ok"] is True, "false positive on a healthy check: %s" % c["detail"]


def test_a_genuine_failure_stays_a_failure():
    (c,) = sg.parse_checks("CHECK|proxy_routes|no|proxy -> colt-web -> 000")
    assert c["ok"] is False


def test_the_rule_is_general_not_a_patch_for_one_string():
    """Any PASS whose detail describes a failure, in any wording, must be demoted."""
    for detail in ("check unavailable: something went wrong",
                   "could not read the running config",
                   "unrecognised drift verdict",
                   "the proxy is serving a replaced inode",
                   "reload failed, falling back"):
        (c,) = sg.parse_checks("CHECK|x|yes|%s" % detail)
        assert c["ok"] is False, "not demoted: %r" % detail


# ---------------------------------------------------------------- 2. no catch-all pass in bash
def test_no_branch_in_HEALTH_scores_an_unknown_answer_as_a_pass():
    """The bash gate must not contain a wildcard branch that reports success.

    This is the defect in its original form: `*) chk config_drift yes "..."`. Grepping for the
    shape rather than the exact string means a future check cannot reintroduce it under a new name.
    """
    health = re.search(r'HEALTH\s*=\s*r?"""(.*?)"""', open(os.path.join(ROOT, "stagegate.py"),
                                                           encoding="utf-8").read(), re.S).group(1)
    bad = re.findall(r"^\s*\*\)\s*chk\s+\w+\s+yes\b.*$", health, re.M)
    assert not bad, "a wildcard branch reports PASS on an unknown answer: %s" % bad


# ---------------------------------------------------------------- 3. unanimous dissent halts
def _verdict(gate, verdicts):
    return {"gate": gate, "digest": "d",
            "reviews": [{"model": "m%d" % i, "verdict": v} for i, v in enumerate(verdicts)]}


def test_unanimous_no_go_against_a_green_gate_halts(monkeypatch=None):
    os.environ.pop("OVERRIDE_PANEL", None)
    g, d = sg._decide_from_verdict(_verdict("GO", ["no-go"] * 4))
    assert g == "NO-GO", "4/4 dissent against a green gate still promoted"
    assert "HALTED" in d and "OVERRIDE_PANEL" in d


def test_a_split_panel_does_not_block():
    """Models must NOT get a veto. One dissenter, or two, cannot stop a green gate."""
    os.environ.pop("OVERRIDE_PANEL", None)
    for vs in (["go", "no-go", "go", "go"], ["no-go", "no-go", "go", "unsure"],
               ["go", "go", "go", "unsure"]):
        g, _ = sg._decide_from_verdict(_verdict("GO", vs))
        assert g == "GO", "a split panel blocked the release: %s" % vs


def test_an_unavailable_panel_never_blocks():
    """A 429 or an outage must not be able to stop a good release."""
    os.environ.pop("OVERRIDE_PANEL", None)
    g, _ = sg._decide_from_verdict({"gate": "GO", "digest": "d", "reviews": []})
    assert g == "GO"
    g, _ = sg._decide_from_verdict({"gate": "GO", "digest": "d", "reviews":
                                    [{"model": "a", "verdict": "no-go"}]})
    assert g == "GO", "a single reviewer must not be a quorum"


def test_the_override_is_explicit_and_works():
    os.environ["OVERRIDE_PANEL"] = "1"
    try:
        g, _ = sg._decide_from_verdict(_verdict("GO", ["no-go"] * 4))
        assert g == "GO", "the documented override does not work"
    finally:
        os.environ.pop("OVERRIDE_PANEL", None)


def test_a_failed_gate_is_never_rescued_by_a_happy_panel():
    os.environ.pop("OVERRIDE_PANEL", None)
    g, _ = sg._decide_from_verdict(_verdict("NO-GO", ["go"] * 4))
    assert g == "NO-GO", "an agreeable panel overrode a failing deterministic gate"


# ---------------------------------------------------------------- 4. the agent's own defect
def test_missing_host_file_is_a_skip_not_a_stale_mount():
    """Absence of evidence is never a finding — the rule this repo has held since bgp_resilience."""
    _a = importlib.util.spec_from_file_location(
        "cg_agent", os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    ag = importlib.util.module_from_spec(_a)
    _a.loader.exec_module(ag)
    ag.mount_source = lambda c: "/nonexistent/Caddyfile"
    ag._sha_in_container = lambda c: "3af610cdeb71" + "0" * 52
    ok, msg = ag.mount_sync("staging-caddy", fix=False)
    assert ok is True, "a missing host file is still reported as a stale mount: %s" % msg
    assert "nothing to compare" in msg
    # And the message must NOT be the one that broke the gate.
    assert not msg.startswith("STALE MOUNT")


def test_the_mount_source_is_asked_for_not_assumed():
    src = open(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"), encoding="utf-8").read()
    assert "def mount_source(" in src, "the host path is still assumed rather than resolved"
    assert "mount_source(c) or LIVE" in src, "mount_sync does not use the resolved source"
