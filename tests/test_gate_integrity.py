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


# ============================================================================================
def _read(path):
    return open(path, encoding="utf-8").read()


# The panel keeps proposing fixes for checks that already work, because the briefing it is given
# describes the TRAP without describing the IMPLEMENTATION. kimi-k2.6 has now claimed three runs
# running that config_drift hash-compares two serialisations. It does not, and has not since
# 7 Aug 2026. That is a defect in the map we hand the reviewers, not in their reasoning.
# ============================================================================================
def test_the_panel_is_told_what_each_check_measures():
    arch = _read(os.path.join(ROOT, "deploy", "stagegate", "quorum.py"))
    i = arch.find("ARCH = ")
    assert i > 0, "ARCH briefing not found in quorum.py"
    block = arch[i:i + 4000]
    for check in ("mount_fresh", "config_drift", "vhost_roster", "admin_api_closed"):
        assert check in block, (
            "the ARCH briefing does not say what %s measures, so a reviewer can only guess. "
            "Three panels in a row have spent a slot on a refuted claim for exactly this "
            "reason." % check)
    assert "does NOT hash" in block or "not hash" in block, (
        "the briefing must state that config_drift compares SETS, not hashes — otherwise a "
        "reviewer reads the 'a hash comparison is a false positive' warning and attributes the "
        "removed method to the current check.")


def test_no_check_name_claims_more_than_it_measures():
    """A check's NAME is read far more often than its detail text.

    `config_reread` asserted only that the process started after the file was written. It proves
    ORDERING; the name promised content. kimi was right that renaming it is the honest fix, and a
    detail string saying "this does not prove what my name says" is not a substitute.
    """
    sg = _read(os.path.join(ROOT, "stagegate.py"))
    assert "config_reread" not in sg, (
        "config_reread is back. It measures write/start ORDERING only — name it for what it "
        "measures (config_write_ordering), or make it actually prove a re-read.")
    assert "config_write_ordering" in sg, "the ordering check disappeared entirely"


def test_certificate_expiry_is_a_gate_and_is_also_checked_off_box():
    """A lapsed certificate takes EVERY domain on the shared proxy down at the same instant, and
    it is the one outage that arrives on a published schedule. It used to be printed only."""
    cg = _read(os.path.join(ROOT, "caddyguard.py"))
    assert "CERT GATE FAILED" in cg, "caddyguard no longer gates on certificate expiry"
    assert "warn.append" in cg and "return 1" in cg, (
        "the cert/reboot verdicts are printed but not folded into the exit code — a line in a "
        "400-line deploy log is a fact nobody reads, not a warning.")

    up = _read(os.path.join(ROOT, ".github", "workflows", "uptime.yml"))
    assert "x509" in up and "enddate" in up, (
        "certificate expiry is not checked OFF-BOX. The droplet's own monitoring sits behind the "
        "proxy it monitors, so it is mute exactly when it matters.")


def test_the_reboot_gate_installs_itself_without_a_cloud_credential():
    """The 6 Aug outage mechanism: patchwatch rebooted into a damaged Caddyfile.

    The gate was reported MISSING across several ships because it was gated behind
    `provision_patchwatch.py`, which hard-fails without DO_API_TOKEN. That token buys SNAPSHOTS and
    Spaces backups; the gate is pure code, and patchwatch's credentials live in
    /etc/patchwatch/patchwatch.env, which installing the code never touches.
    """
    cg = _read(os.path.join(ROOT, "caddyguard.py"))
    assert "/opt/patchwatch/patchwatch.py" in cg and "base64 -d > /opt/patchwatch" in cg, (
        "caddyguard no longer installs the reboot gate. Telling the operator to run a second "
        "script breaks the one-command rule AND leaves the guardrail uninstalled.")
    # STRIP COMMENTS FIRST. The first version of this assertion matched the comment that EXPLAINS
    # why the token is not needed, and failed on a file that was correct. Same false positive the
    # brand gate already learned to avoid: grep the code, not the prose about the code.
    code = "\n".join(ln for ln in cg.splitlines() if not ln.lstrip().startswith("#"))
    assert "DO_API_TOKEN" not in code, (
        "the reboot gate depends on a cloud credential again. That token buys snapshots and "
        "Spaces backups; the gate is pure code and patchwatch's own env file holds its secrets.")
    # It must verify what it installed rather than assuming the copy worked.
    assert "does not parse" in cg and "restoring the previous copy" in cg, (
        "the installer does not validate what it wrote. Overwriting a droplet's patch automation "
        "with a file that does not parse would disable unattended security updates silently.")
