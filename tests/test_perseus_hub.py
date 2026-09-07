"""The cycle: what it decides from evidence, and what it refuses to decide without it.

test_perseus_ruleset.py proves the ruleset BEHAVES. This file proves the cycle is WIRED to it --
that the tuning pass runs, that the abuse pass runs, that a dry run changes nothing, and that an
unobserved project is reported as blind rather than counted as quiet. A control that is correct
and unreachable is not a control; this repository has paid for that distinction more than once.

Every fixture here is stdlib. Nothing reaches the network, Loki, a model or a droplet: `collect`
is stubbed, `enrich` is a fake, and the RDAP lookup is replaced. A test that reaches the internet
is not testing this repository.
"""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "perseus"))


# ── fixtures ─────────────────────────────────────────────────────────────────────────────
class FakeEnrich:
    """Three models answer sanely, one answers far outside the committed range."""
    calls = []

    @staticmethod
    def _call(prompt, model=None, max_tokens=0, timeout=0):
        FakeEnrich.calls.append(model)
        v = 99999 if str(model).endswith("kimi-k2.6") else 10
        return json.dumps({"reasoning": "x", "thresholds": {"ip_per_min": v}}), {}

    @staticmethod
    def _json(raw):
        return json.loads(raw)


class FakePanelModels:
    MODELS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]


class FakeGuard:
    GUARD_PREAMBLE = "PREAMBLE"

    @staticmethod
    def fence(x, cap=0, max_lines=0):
        return "\n".join(x)


@pytest.fixture()
def hub(tmp_path, monkeypatch):
    """A hub whose every side effect lands in a temp dir."""
    monkeypatch.setenv("PERSEUS_RULESET", str(tmp_path / "rs.json"))
    monkeypatch.setenv("PERSEUS_ABUSE_STATE", str(tmp_path / "ab.json"))
    monkeypatch.setenv("PERSEUS_BLOCKLIST", str(tmp_path / "bl.json"))
    for m in ("hub", "ruleset", "abuse", "vet"):
        sys.modules.pop(m, None)
    sys.modules["enrich"] = FakeEnrich
    # IMPORT THE REAL `app` PACKAGE, then replace two of its members. The first version of this
    # fixture registered a fake `app` module, which SHADOWED the real one -- so `from app import
    # shield` failed inside actors() and it returned an empty list that looked like "no repeat
    # offenders". A fixture that blinds the function under test is a test of the fixture.
    sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
    import app                                          # noqa: F401  (the real package)
    monkeypatch.setitem(sys.modules, "app.shield_panel", FakePanelModels)
    monkeypatch.setitem(sys.modules, "app.llm_guard", FakeGuard)
    monkeypatch.setattr(app, "shield_panel", FakePanelModels, raising=False)
    monkeypatch.setattr(app, "llm_guard", FakeGuard, raising=False)
    import hub as H
    import incident_report as IR
    monkeypatch.setattr(IR, "rdap_abuse",
                        lambda ip, timeout=8: {"name": "Example Hoster",
                                               "abuse": ["abuse@example.net"]})
    H.__dict__["_TMP"] = tmp_path
    return H


def ev(ip, path, status, days_ago, project="cybergod", now=None):
    now = now or time.time()
    return {"ip": ip, "path": path, "status": status, "project": project,
            "_ts": now - days_ago * 86400}


# ── who gets reported ────────────────────────────────────────────────────────────────────
def test_a_burst_is_not_a_campaign(hub):
    """DISTINCT DAYS, never volume. Five hundred requests in an hour can be a broken client or a
    misconfigured monitor; the same address returning on three separate days is somebody working
    through an estate. Reporting the first is how a reporter stops being read."""
    burst = [ev("1.2.3.4", "/wp-login.php", 404, 0) for _ in range(500)]
    spread = [ev("5.6.7.8", "/.env", 404, 0), ev("5.6.7.8", "/.git/config", 404, 3),
              ev("5.6.7.8", "/phpinfo", 404, 5)]
    ips = {a["ip"] for a in hub.actors(burst + spread)}
    assert "5.6.7.8" in ips
    assert "1.2.3.4" not in ips


def test_a_research_scanner_is_never_reported(hub):
    """Censys and Shodan are not abuse. Reporting them discredits every other complaint we file,
    and the credibility is the only thing that makes a complaint work at all."""
    import abuse as AB
    a = {"ip": "9.9.9.9", "days": {"a": 1, "b": 1}, "holder": "Censys, Inc."}
    ok, why = AB.eligible(a, {})
    assert not ok and "research" in why


def test_one_rented_range_is_reported_once(hub):
    """A /24 is one actor. Reporting its 256 addresses separately is spam with our name on it,
    and volume is precisely what damages the sending reputation of the domain that carries our
    one-time passwords."""
    import abuse as AB
    a = {"ip": "5.6.7.8", "days": {"a": 1, "b": 1}, "holder": "Example Hoster"}
    now = time.time()
    assert AB.eligible(a, {}, now)[0]
    st = AB.record_sent(a, {}, now)
    ok, why = AB.eligible(dict(a, ip="5.6.7.99"), st, now)
    assert not ok and "dedupe" in why


# ── what the numbers may become ──────────────────────────────────────────────────────────
def test_a_vote_outside_the_range_is_discarded_not_clamped(hub):
    """DISCARDED, not clamped. Clamping a nonsense answer would silently turn it into a valid
    vote and let it count toward the quorum -- a model that answered 99999 would then be
    indistinguishable from one that answered sensibly."""
    import ruleset as RS
    votes = hub.ask_thresholds(
        {"days": 2, "total": 100, "sources": 9, "top_clean": 40, "top_hostile": 80,
         "top_probe": 14}, RS.blank())
    assert votes["ip_per_min"] == [10, 10, 10], votes


def test_a_unanimous_absurd_vote_still_cannot_move_a_number_far(hub):
    """The step cap and the clamp are independent of the quorum. Four models agreeing on nonsense
    move the number by at most 25%, and never outside the committed range."""
    import ruleset as RS
    rs = RS.blank()
    before = RS.thresholds(rs)["ip_per_min"]
    after, _why = RS.tune(rs, "ip_per_min", None, [9999, 9999, 9999, 9999])
    assert after <= before * 1.26
    assert RS.BOUNDS["ip_per_min"][0] <= after <= RS.BOUNDS["ip_per_min"][1]


def test_a_silent_panel_changes_no_numbers(hub, monkeypatch):
    """If no model answered, the cycle has no opinion to act on. A quota outage must not be able
    to move a threshold, in either direction."""
    monkeypatch.setattr(hub, "collect", lambda host, days: ([ev("9.9.9.9", "/.env", 404, 0)], [], ""))
    monkeypatch.setattr(hub, "ask_panel", lambda unk: [{"model": "-", "ok": False, "error": "x"}])
    rep, _rs = hub.cycle(days=2, dry_run=True)
    assert rep["tuned"] == []


# ── what a dry run may do ────────────────────────────────────────────────────────────────
def test_a_dry_run_decides_out_loud_and_writes_nothing(hub, monkeypatch, tmp_path):
    """It must still REPORT what tonight's real cycle would do. A dry run that skipped the
    decision would tell the operator nothing, which is the whole reason to have one."""
    import ruleset as RS
    store, blocklist = tmp_path / "rs.json", tmp_path / "bl.json"
    RS.save(RS.blank(), str(store))
    before = store.read_bytes()
    monkeypatch.setattr(hub, "collect", lambda host, days: ([ev("9.9.9.9", "/.env", 404, 0)], [], ""))
    rep, _rs = hub.cycle(days=2, dry_run=True)
    assert store.read_bytes() == before, "the store must be byte-identical after a dry run"
    assert not blocklist.exists(), "a dry run must not publish a blocklist"
    assert "abuse" in rep and "tuned" in rep, "it still reports what it would have done"


def test_blind_is_not_clean(hub, monkeypatch):
    """A project that produced no lines has not been observed, and every conclusion about it is
    invalid. Counting it as quiet is how jobhuntwow was neither blamed nor cleared for a week."""
    monkeypatch.setattr(hub, "collect", lambda host, days: ([], list(hub.PROJECTS), ""))
    rep, _rs = hub.cycle(days=2, dry_run=True)
    assert rep["verdict"].startswith("NO EVIDENCE")
    assert "BLIND, NOT CLEAN" in hub.render(rep)


# ── the wiring, which behaviour tests cannot see ─────────────────────────────────────────
def test_the_cycle_actually_runs_the_tuning_and_abuse_passes(hub, monkeypatch):
    """WIRING, not behaviour. Every pass above is proven in isolation; this asserts the cycle
    CALLS them. shield.py was fully tested while nothing asserted the middleware invoked it."""
    called = {}
    monkeypatch.setattr(hub, "collect",
                        lambda host, days: ([ev("5.6.7.8", "/.env", 404, d) for d in (0, 2, 4)], [], ""))
    # `setdefault(...) or {}` returns True, not {} -- a stub whose return value is wrong makes the
    # code under test fail for a reason that has nothing to do with the property being asserted.
    def _tuned(stats, rs, models=None):
        called["tuned"] = True
        return {}

    def _abuse(acts, dry_run=False, now=None):
        called["abuse"] = True
        return {"abuseipdb": [], "sent": [], "skipped": [], "errors": []}
    monkeypatch.setattr(hub, "ask_thresholds", _tuned)
    import abuse as AB
    monkeypatch.setattr(AB, "run", _abuse)
    monkeypatch.setattr(hub, "ask_panel", lambda unk: [{"model": "m", "ok": True}])
    rep, _rs = hub.cycle(days=2, dry_run=True)
    assert called.get("tuned"), "the threshold pass is not wired into the cycle"
    assert called.get("abuse"), "the abuse pass is not wired into the cycle"
    assert rep.get("actors"), "the actors were never assembled"


def test_the_wider_window_is_collected_in_one_query(hub, monkeypatch):
    """The abuse gate counts DISTINCT DAYS and cannot see two of them inside a two-day window.
    Two queries for one fact set would be two round trips; the cycle takes the wider window once
    and slices the recent part locally."""
    seen = {}

    def _c(host, days):
        seen["days"] = days
        return [], list(hub.PROJECTS), ""
    monkeypatch.setattr(hub, "collect", _c)
    hub.cycle(days=2, dry_run=True)
    assert seen["days"] >= hub.ABUSE_DAYS


def test_the_report_names_what_it_refused_to_report_and_why(hub, monkeypatch):
    """A silent skip teaches nothing. The skip reasons are the most useful lines in the daily
    report: each one is a gate stating, in words, why an address was held back."""
    monkeypatch.setattr(hub, "collect",
                        lambda host, days: ([ev("5.6.7.8", "/.env", 404, d) for d in (0, 2, 4)], [], ""))
    rep, _rs = hub.cycle(days=2, dry_run=True)
    txt = hub.render(rep)
    assert "CONSEQUENCE FOR THE ATTACKER" in txt
    assert "repeat offenders seen on" in txt


def test_a_report_nobody_received_is_not_reported_as_delivered(hub, monkeypatch, capsys):
    """DELIVERED IS NOT SENT. Both helpers return truthy only on real delivery, so the cycle asks
    them rather than reporting success because the import worked. logship reported success for a
    week while shipping an empty archive; the spend watcher set `alerted` when notify merely
    imported. A muted channel must be queryable, not silent."""
    import app.notify as N
    monkeypatch.setattr(N, "telegram", lambda *a, **k: False)
    monkeypatch.setattr(N, "email", lambda *a, **k: False)
    monkeypatch.setattr(hub, "collect", lambda host, days: ([ev("9.9.9.9", "/.env", 404, 0)], [], ""))
    monkeypatch.setattr(sys, "argv", ["hub.py", "--cycle"])
    hub.main()
    out = capsys.readouterr().out
    assert "undelivered" in out, "a failed delivery must be stated, not swallowed"

    monkeypatch.setattr(N, "telegram", lambda *a, **k: True)
    hub.main()
    assert "report delivered: telegram=True" in capsys.readouterr().out


def test_a_classifier_it_cannot_load_is_reported_not_returned_as_empty(hub, monkeypatch):
    """"No repeat offenders" and "I could not load the classifier" look identical from outside,
    and only one of them is good news. logship reported success for a week while shipping an empty
    archive; dbbackup made the same mistake and was fixed; this is the same rule for actors()."""
    import builtins
    real = builtins.__import__

    def _no_shield(name, *a, **k):
        if name == "app" and a and "shield" in (a[2] or ()):
            raise ImportError("boom")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", _no_shield)
    with pytest.raises(RuntimeError, match="shield unavailable"):
        hub.actors([ev("5.6.7.8", "/.env", 404, 0)])


def test_the_cycle_turns_that_into_a_reported_error_not_a_crash(hub, monkeypatch):
    """It must not take the whole cycle down either: the rest of the defence still has work to do.
    Reported, and the abuse pass simply has nobody to report."""
    def _boom(events, window_days=None, now=None):
        raise RuntimeError("shield unavailable, so no actor could be classified")
    monkeypatch.setattr(hub, "actors", _boom)
    monkeypatch.setattr(hub, "collect", lambda host, days: ([ev("9.9.9.9", "/.env", 404, 0)], [], ""))
    rep, _rs = hub.cycle(days=2, dry_run=True)
    assert any("shield unavailable" in e for e in rep["errors"])
    assert rep["actors"] == [] and rep["abuse"]["sent"] == []


# ── the deploy wiring, which is how the hub sat undeployed after a green ship ─────────────
def test_ship_py_installs_the_hub():
    """THE DEFECT THIS ASSERTS AGAINST ACTUALLY HAPPENED. ship.py copied the thin client and never
    installed the brain, so a fully green deploy left the estate with no daily review and nothing
    said so. Telling the operator to "also run perseus.py" is a second command (operating
    principle 7); the fix is the call, and this is the check that it is still there."""
    src = open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    # Anchor on BOTH halves separately: the real call is
    # `[sys.executable, os.path.join(HERE, "perseus.py"), "--install-only"]`, so a single literal
    # with a comma between them never matches. This assertion was RED at baseline, which made the
    # mutation harness score every mutation as "caught" for free -- a test that is already failing
    # cannot tell you anything about a change.
    assert '"perseus.py"' in body and '"--install-only"' in body, \
        "ship.py must install the perseus hub, not merely refresh the thin client"
    i_py, i_flag = body.rfind('"perseus.py"'), body.rfind('"--install-only"')
    assert 0 < i_py < i_flag < i_py + 200, \
        "the --install-only flag must be on the perseus.py invocation, not somewhere unrelated"


def test_install_only_returns_before_the_cycle():
    """INSTALL must not run a cycle. A cycle is four model calls and about two minutes, and the
    04:40 timer is about to make that same decision; billing the account on every deploy for a
    decision already scheduled is exactly the waste this subsystem exists to notice."""
    import ast
    src = open(os.path.join(ROOT, "perseus.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    body = ast.get_source_segment(src, fn)
    i_guard, i_cycle = body.find("if a.install_only:"), body.find("-- one cycle now --")
    assert i_guard != -1, "the --install-only guard is gone"
    assert i_cycle != -1, "the cycle marker moved; re-anchor this check"
    assert i_guard < i_cycle, "--install-only must return BEFORE the cycle"
    assert "return 0" in body[i_guard:i_cycle], "the guard must actually return"
