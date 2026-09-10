# -*- coding: utf-8 -*-
"""The three schedules, and the one rule that survives all of them: code decides.

test_perseus_ruleset.py proves the ruleset BEHAVES and test_perseus_hub.py proves the daily cycle is
WIRED. This file covers the two things added for the automated SOC:

  * the WEEKLY pass -- re-vetting live rules against the routes as they are TODAY, and retiring what
    a month of traffic never matched. Neither judgement is sound on the daily cycle's two-day
    window, which is why it is a second unit on a second schedule rather than a flag.
  * PER-INCIDENT consensus -- four vendors asked about ONE live burst, while it is happening.

WHAT THESE TESTS ARE ACTUALLY FOR. Not "does the happy path work". Each one asserts a property that,
if it broke, would cost real money or deny a real visitor:
    a model verdict on its own can never make anything refuse a request;
    a dead model chain enforces nothing AND drops nothing;
    a scan storm cannot run up the model bill;
    the weekly unit is armed, distinct from the daily one, and PROVEN to have run.

NOTHING HERE REACHES THE NETWORK. `enrich` and `llm_meter` are replaced in sys.modules, the events
are dicts built in the test, and no ssh session, Loki query or droplet is involved. A test that
reaches the internet is not testing this repository.
"""
import io
import json
import os
import sys
import time
import tokenize
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "perseus"))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))


# ── fixtures ──────────────────────────────────────────────────────────────────────────────────
class FakePanel:
    """Four models that answer sanely and propose ONE narrow pattern each time."""
    calls = []
    proposal = {"name": "unknown_admin_probe", "pattern": r"/xxadminportalxx",
                "why": "guessing at an admin console we do not have"}
    usage = {"prompt_tokens": 1200, "completion_tokens": 500}
    usd_per_call = 0.0024
    raises = False

    @classmethod
    def reset(cls, **kw):
        cls.calls = []
        cls.raises = False
        cls.proposal = {"name": "unknown_admin_probe", "pattern": r"/xxadminportalxx",
                        "why": "guessing at an admin console we do not have"}
        cls.usd_per_call = 0.0024
        for k, v in kw.items():
            setattr(cls, k, v)

    # The four vendors, kept here as data so panel_models() can be proven to READ them rather than
    # carry its own copy. The real chain lives in enrich._FALLBACKS and nowhere else.
    MODELS = ["vendor-a", "vendor-b", "vendor-c", "vendor-d"]
    _FALLBACKS = MODELS

    @staticmethod
    def _call(prompt, model=None, max_tokens=0, timeout=0):
        FakePanel.calls.append(model)
        if FakePanel.raises:
            raise RuntimeError("vendor unreachable")
        return json.dumps({"technique": "wordlist scanning", "severity": "medium", "novel": True,
                           "assessment": "one source guessing at admin consoles.",
                           "proposals": [FakePanel.proposal]}), dict(FakePanel.usage)

    @staticmethod
    def _json(raw):
        return json.loads(raw)

    @staticmethod
    def cost_of(model, tin, tout):
        return FakePanel.usd_per_call


class FakeMeter:
    """A healthy meter. The unhealthy one is built inline by the test that needs it."""
    DAILY_USD = 3.0

    @staticmethod
    def spent_today():
        return 0.0

    @staticmethod
    def allow(estimate_usd=0.0):
        return True, ""


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Every path perseus writes to lands in a temp dir, and every model call is a fake.

    THE MODULES ARE POPPED AND RE-IMPORTED because every file in this package reads its state paths
    from the environment AT IMPORT TIME. A fixture that sets the environment after the import is a
    fixture that tests the previous test's temp directory -- and `perseus.ruleset` in particular is
    imported by hub as a PACKAGE member, so popping only the flat name leaves it pinned.
    """
    for k, v in (("PERSEUS_RULESET", "rs.json"), ("PERSEUS_BLOCKLIST", "bl.json"),
                 ("PERSEUS_ABUSE_STATE", "ab.json"), ("PERSEUS_ROUTES", "routes.json"),
                 ("PERSEUS_INCIDENTS", "incidents.json"), ("PERSEUS_WATCH_STATE", "watch.json"),
                 ("PERSEUS_WEEKLY_STATE", "weekly.json"), ("EVENTS_LOG", "events.log")):
        monkeypatch.setenv(k, str(tmp_path / v))
    for m in ("hub", "ruleset", "vet", "abuse", "incident",
              "perseus", "perseus.hub", "perseus.ruleset", "perseus.vet", "perseus.abuse",
              "perseus.incident"):
        monkeypatch.delitem(sys.modules, m, raising=False)

    FakePanel.reset()
    monkeypatch.setitem(sys.modules, "enrich", FakePanel)
    monkeypatch.setitem(sys.modules, "llm_meter", FakeMeter)

    import hub as H
    import incident as INC
    import ruleset as RS
    import vet as VET
    return types.SimpleNamespace(hub=H, inc=INC, rs=RS, vet=VET, tmp=tmp_path)


def noon():
    """A pass clock pinned to mid-day UTC, TODAY.

    The daily incident allowance is keyed on the UTC date, and several tests below step the clock
    forward by an hour or two. Started from the wall clock at 23:50 they would roll into a new day
    mid-test, reset the counter and score the cap as broken -- a coin flip that teaches the operator
    to re-run rather than to read. Pinned to noon it cannot, and it is still close enough to real
    time that the ledger's own 30-day pruning leaves the entries alone.
    """
    t = time.time()
    return t - (t % 86400) + 43200


def ev(ip, path, status=404, ago=60, project="cybergod", now=None):
    now = now or time.time()
    return {"ip": ip, "path": path, "status": status, "project": project, "_ts": now - ago}


def burst(ip, n=12, now=None, prefix="/wp-"):
    """One source, n DISTINCT unserved paths, inside the incident window."""
    return [ev(ip, "%s%02d.php" % (prefix, i), 404, 60, now=now) for i in range(n)]


def _code(path):
    """The file's CODE, with every comment and every string literal removed.

    A check that greps raw source matches its own explanatory comment, which has happened in this
    repository five separate times. Names survive tokenisation; prose does not.
    """
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        out.append(tok.string)
    return " ".join(out)


# ══ PER-INCIDENT CONSENSUS ════════════════════════════════════════════════════════════════════

def test_a_burst_is_variety_not_volume(sandbox):
    """The same discriminator as everywhere else in this estate. Two real visitors produced 439 and
    362 404s each on 2026-08-10, purely from our own stale links; a request COUNT would have called
    both of them incidents and blocked them."""
    now = time.time()
    loud = [ev("1.2.3.4", "/wp-login.php", 404, 60, now=now) for _ in range(500)]
    varied = burst("5.6.7.8", 12, now=now)
    ips = {i["ip"] for i in sandbox.inc.detect(loud + varied, sandbox.rs.blank(), now=now)}
    assert "5.6.7.8" in ips, "twelve distinct misses in a quarter of an hour is an incident"
    assert "1.2.3.4" not in ips, "five hundred requests for ONE path is a broken client"


def test_a_stale_burst_is_not_a_live_incident(sandbox):
    """The window is what makes this different from the daily miner. Yesterday's burst is the daily
    cycle's business; asking four models about it now would buy the same answer twice."""
    now = time.time()
    old = burst("9.9.9.9", 12, now=now)
    for e in old:
        e["_ts"] = now - 6 * 3600
    assert sandbox.inc.detect(old, sandbox.rs.blank(), now=now) == []


def test_a_model_verdict_alone_cannot_promote_anything(sandbox):
    """THE RULE THE WHOLE SUBSYSTEM RESTS ON. Four vendors agreeing at 09:11 that an address is
    hostile must change nothing about what the estate refuses at 09:12.

    Four things are asserted, and the third and fourth are the ones that matter: unanimous agreement
    plus a full detection period plus real hostile matches still promotes NOTHING while the rule has
    matched something that looked legitimate -- and the same rule DOES promote once that is untrue,
    which is what proves the gate is arithmetic rather than a refusal to ever act.
    """
    now = time.time()
    rep = sandbox.inc.run(events=burst("5.6.7.8", 12, now=now), now=now)
    assert rep["asked"] == 1
    assert len(FakePanel.calls) == 4, "one call per vendor, no more"

    rules = sandbox.rs.load()["rules"]
    assert len(rules) == 1, rules
    r = rules[0]
    assert r["tier"] == sandbox.rs.TIER_DETECT, "an incident may only ever propose DETECTION"
    assert r["promoted"] is None
    assert r["source"] == "incident-consensus"
    assert not [x for x in rules if x["tier"] == sandbox.rs.TIER_BLOCK]

    # 1. fresh: too young, whatever four vendors said.
    ok, why = sandbox.rs.can_promote(r, now)
    assert not ok and "detection" in why

    # 2. old enough and unanimous, but it has never matched anything.
    r["created"] = now - 48 * 3600
    ok, why = sandbox.rs.can_promote(r, now)
    assert not ok and "never matched" in why

    # 3. old, unanimous, matched hostile traffic -- AND one request that looked legitimate.
    r["hits"], r["clean_hits"] = 9, 1
    ok, why = sandbox.rs.can_promote(r, now)
    assert not ok and "looked legitimate" in why

    # 4. the same rule, with that one clean hit gone, DOES promote. Without this the three refusals
    #    above would also be satisfied by a gate that simply never says yes.
    r["clean_hits"] = 0
    ok, _why = sandbox.rs.can_promote(r, now)
    assert ok


def test_the_incident_path_contains_no_way_to_write_a_blocking_tier(sandbox):
    """WIRING, not behaviour. The test above proves one scenario ends in DETECTION; this proves
    there is no branch anywhere in the module that could end anywhere else. A control that is
    correct in the case somebody tested is not a control."""
    code = _code(os.path.join(ROOT, "perseus", "incident.py"))
    assert "TIER_BLOCK" not in code, "the incident path must never name the blocking tier"
    assert "promote" not in code, "promotion is ruleset.can_promote()'s decision, a day later"


def test_a_proposal_that_matches_something_we_serve_is_refused_however_many_vendors_agree(sandbox):
    """vet.py, not the vote. Four models proposing a pattern that matches a live route is exactly
    the 2026-08-10 case: a 404-count rule that would have denied two genuine visitors."""
    now = time.time()
    FakePanel.reset(proposal={"name": "everything", "pattern": r"/api", "why": "broad"})
    rep = sandbox.inc.run(events=burst("5.6.7.8", 12, now=now), now=now)
    rec = rep["incidents"][0]
    assert rec["answered"] == 4, "all four answered; this is not a failure to ask"
    assert rec["proposed"] == [], "and not one of them installed anything"
    assert rec["refused"], "the refusal is reported, because it is the most useful line here"
    # RS.load() rather than a raw open: nothing was accepted, so nothing was saved, and a
    # FileNotFoundError here would be the test failing for a reason unrelated to the property.
    assert sandbox.rs.load()["rules"] == []


def test_a_dead_model_chain_enforces_nothing_and_drops_nothing(sandbox):
    """BOTH HALVES. An unreachable vendor must not become an enforcement action -- and it must not
    become silence either. logship reported success for a week while shipping an empty archive; an
    incident that ceases to exist because a provider had a bad afternoon is the same defect."""
    now = time.time()
    FakePanel.reset(raises=True)
    rep = sandbox.inc.run(events=burst("5.6.7.8", 12, now=now), now=now)

    rec = rep["incidents"][0]
    assert rec["status"] == "models-unreachable"
    assert rec["answered"] == 0
    assert rec["enforcement"] == "none"
    assert rec["proposed"] == []
    assert sandbox.rs.load()["rules"] == []

    # RECORDED, and findable by the report a human reads.
    assert rec["pending"] is True
    ledger = json.load(open(os.environ["PERSEUS_INCIDENTS"], encoding="utf-8"))
    assert any(x["fingerprint"] == rec["fingerprint"] for x in ledger["incidents"])
    summary = sandbox.inc.summarise(since=0)
    assert summary["pending"] == 1 and summary["unreachable"] == 1


def test_an_unreadable_meter_refuses_to_ask_at_all(sandbox, monkeypatch):
    """FAILS CLOSED, and deliberately the OPPOSITE WAY ROUND from enrich._call.

    enrich fails OPEN on a broken meter because refusing there degrades a customer's deck. Refusing
    here degrades a log line. An unmeasurable spend is precisely the condition that produced three
    $5 auto-recharges in two days while the cost report said the lifetime total was under a dollar.
    """
    broken = types.SimpleNamespace(DAILY_USD=3.0,
                                   spent_today=lambda: None,
                                   allow=lambda estimate_usd=0.0: (True, "failing open"))
    monkeypatch.setitem(sys.modules, "llm_meter", broken)
    now = time.time()
    rep = sandbox.inc.run(events=burst("5.6.7.8", 12, now=now), now=now)
    assert FakePanel.calls == [], "not one model call may be made when the spend cannot be counted"
    assert rep["incidents"][0]["status"] == "budget-stop"
    assert rep["incidents"][0]["pending"] is True


def test_the_same_actor_doing_the_same_thing_is_one_incident(sandbox):
    """Re-asking an identical incident buys one more opinion and four more calls. The watch pass
    fires every ten minutes, so without this a single scanner is 576 calls a day."""
    now = noon()
    evs = burst("5.6.7.8", 12, now=now)
    sandbox.inc.run(events=evs, now=now)
    first = len(FakePanel.calls)
    rep = sandbox.inc.run(events=evs, now=now + 600)
    assert len(FakePanel.calls) == first, "the second pass must not re-ask"
    assert rep["skipped"], "and it must say why it held back"


def test_one_rented_range_does_not_buy_256_incidents(sandbox):
    """The same rule as the abuse gate: a /24 is one actor. A scanner walking its own range would
    otherwise clear the fingerprint dedupe on every address."""
    now = noon()
    sandbox.inc.run(events=burst("5.6.7.8", 12, now=now), now=now)
    first = len(FakePanel.calls)
    rep = sandbox.inc.run(events=burst("5.6.7.99", 12, now=now, prefix="/xy-"), now=now + 600)
    assert len(FakePanel.calls) == first
    assert any("5.6.7" in (s.get("why") or "") for s in rep["skipped"])


def test_one_storm_cannot_spend_more_than_the_per_pass_cap(sandbox):
    """MAX_PER_RUN. Ten simultaneous sources is one pass, not ten passes."""
    now = time.time()
    evs = []
    for k in range(10):
        evs += burst("10.0.%d.5" % k, 12, now=now, prefix="/p%d-" % k)
    rep = sandbox.inc.run(events=evs, now=now)
    assert rep["detected"] == 10, "all ten are DETECTED; detection is free and deterministic"
    assert rep["asked"] == sandbox.inc.MAX_PER_RUN
    assert len(FakePanel.calls) == sandbox.inc.MAX_PER_RUN * 4


def test_the_daily_incident_cap_holds_across_passes(sandbox):
    """THE CAP THAT BOUNDS THE BILL. MAX_PER_DAY incidents x 4 vendors is the hard ceiling on how
    many model calls a day of scanning can buy, and it holds across passes because the count lives
    in the ledger rather than in a process."""
    now = noon()
    for i in range(12):                       # twelve passes, two hours of the watch timer
        t = now + i * 600
        # THE EVIDENCE IS REBUILT AT EACH PASS TIME, because the incident window is 15 minutes and
        # the timer step is 10. Reusing one event list would have left every pass after the second
        # looking at traffic older than its own window, and the test would then have "passed"
        # by measuring nothing -- a fixture that does not reproduce the condition under test.
        evs = []
        for k in range(30):
            evs += burst("10.%d.7.5" % k, 12, now=t, prefix="/q%d-" % k)
        sandbox.inc.run(events=evs, now=t)
    cap = sandbox.inc.MAX_PER_DAY * 4
    assert len(FakePanel.calls) == cap, \
        "%d calls made, cap is %d" % (len(FakePanel.calls), cap)


def test_a_costly_answer_stops_the_pass_and_then_the_day(sandbox):
    """MEASURED DOLLARS, NOT ASSUMED TOKENS. This gateway drops max_tokens whenever response_format
    is json_object, so a token ceiling is not a ceiling here. The cap that binds is arithmetic on
    the usage the gateway itself returned."""
    now = noon()
    FakePanel.reset(usd_per_call=0.05)        # 4 vendors = $0.20 per incident

    def evidence(t):
        out = []
        for k in range(6):
            out += burst("172.16.%d.5" % k, 12, now=t, prefix="/r%d-" % k)
        return out

    rep1 = sandbox.inc.run(events=evidence(now), now=now)
    assert rep1["asked"] == 1, "the first incident already spends $0.20 of a $0.10 per-pass cap"
    assert any("per-pass" in (s.get("why") or "") for s in rep1["skipped"])

    rep2 = sandbox.inc.run(events=evidence(now + 600), now=now + 600)
    assert rep2["asked"] == 1                 # $0.20 spent, still under the $0.30 day cap
    rep3 = sandbox.inc.run(events=evidence(now + 1200), now=now + 1200)
    assert rep3["asked"] == 0, "$0.40 spent today is past the $0.30 incident cap"
    assert any("daily incident spend" in (s.get("why") or "") for s in rep3["skipped"])
    assert len(FakePanel.calls) == 8, "eight calls, and the ninth was never made"


def test_the_panel_is_read_from_the_committed_chain_not_restated(sandbox, monkeypatch):
    """ONE HOME. ENRICH_MODELS having four homes is the defect that cost a week of investigation;
    a fifth home inside the security brain would be the same mistake wearing a badge.

    Proven by SUBSTITUTION rather than by grep: the chain is replaced with four ids that exist
    nowhere in this repository, and they must come out the other end.
    """
    sentinel = ["zz-alpha", "zz-beta", "zz-gamma", "zz-delta", "zz-epsilon"]
    monkeypatch.setitem(sys.modules, "enrich",
                        types.SimpleNamespace(MODELS=list(sentinel), _FALLBACKS=list(sentinel)))
    got = sandbox.inc.panel_models()
    assert got == sentinel[:sandbox.inc.PANEL_MAX], got
    assert len(got) == 4, "four vendors: the cost arithmetic in this module assumes that number"


def test_the_incident_prompt_fences_the_attacker_chosen_paths(sandbox):
    """A path that reads like an instruction IS the attack. The fence is the only thing that makes
    it read as content, and a prompt built without llm_guard is not sent at all."""
    from app import llm_guard as G
    now = time.time()
    inc = sandbox.inc.detect(burst("5.6.7.8", 12, now=now), sandbox.rs.blank(), now=now)[0]
    prompt = sandbox.inc.build_prompt(inc)
    assert G.FENCE_OPEN in prompt and G.FENCE_CLOSE in prompt
    assert prompt.startswith(G.GUARD_PREAMBLE), "the instructions live OUTSIDE the markers"


def test_a_pass_that_cannot_read_the_log_reports_blindness_rather_than_quiet(sandbox):
    """BLIND IS NOT CLEAN. A missing events log and a quiet ten minutes look identical from the
    outside, and only one of them is good news."""
    rep = sandbox.inc.run(log=str(sandbox.tmp / "does-not-exist.log"))
    assert rep["blind"], "a log it cannot read must be stated"
    assert rep["detected"] == 0 and rep["asked"] == 0
    assert FakePanel.calls == []


def test_a_log_tail_too_short_for_the_window_is_reported_as_blind_too(sandbox, monkeypatch):
    """The reader takes a BOUNDED tail of an unbounded append-only log, because loading the whole
    file every ten minutes would OOM the box it defends. But running out of bytes and a quiet
    quarter of an hour are different facts, and only one of them is good news."""
    log = sandbox.tmp / "big.log"
    now = time.time()
    with io.open(log, "w", encoding="utf-8", newline="\n") as fh:
        for i in range(200):
            fh.write(json.dumps({"evt": "http", "ts": now - 30, "ip": "5.6.7.8",
                                 "path": "/p%d" % i, "status": 404}) + "\n")

    evs, err = sandbox.inc.recent_events(str(log), now=now)
    assert err == "" and len(evs) == 200, "the whole window fits, so nothing is amiss"

    monkeypatch.setattr(sandbox.inc, "TAIL_BYTES", 2000)
    evs, err = sandbox.inc.recent_events(str(log), now=now)
    assert "NOT read" in err, "a window the reader could not cover must be stated"
    assert evs, "and it still returns everything it COULD read"


def test_an_unanswered_incident_reaches_the_daily_report(sandbox, monkeypatch):
    """NOT A SILENT DROP, end to end. The watch pass records it; the daily report, which is what a
    human actually reads, has to say so."""
    now = time.time()
    FakePanel.reset(raises=True)
    sandbox.inc.run(events=burst("5.6.7.8", 12, now=now), now=now)

    monkeypatch.setattr(sandbox.hub, "collect",
                        lambda host, days: ([ev("9.9.9.9", "/.env", 404, 60)], [], ""))
    rep, _rs = sandbox.hub.cycle(days=2, dry_run=True)
    assert rep["incidents"]["pending"] == 1
    assert "PENDING" in sandbox.hub.render(rep)


# ══ THE WEEKLY CYCLE ══════════════════════════════════════════════════════════════════════════

def test_the_weekly_retires_a_rule_that_no_longer_matches_only_attackers(sandbox):
    """THE JOB THAT ONLY A LONGER LOOK-BACK CAN DO. A pattern is vetted once, against the routes
    that existed on the day it was proposed. Routes ship. Nothing in the daily cycle ever looks
    again, because vet.py is only ever consulted about NEW proposals.

    The control rule is the important half: if the pass retired everything, this test would pass
    for the wrong reason.
    """
    now = time.time()
    rs = sandbox.rs.blank()
    rs["rules"] = [
        {"id": "r1", "pattern": "/kundenportal", "tier": sandbox.rs.TIER_BLOCK,
         "created": now - 40 * 86400, "promoted": now - 39 * 86400, "demoted": None,
         "hits": 4, "clean_hits": 0, "reviewers": ["a", "b", "c"], "why": "", "evidence": []},
        {"id": "r2", "pattern": r"/wp-login\.php", "tier": sandbox.rs.TIER_BLOCK,
         "created": now - 40 * 86400, "promoted": now - 39 * 86400, "demoted": None,
         "hits": 7, "clean_hits": 0, "reviewers": ["a", "b", "c"], "why": "", "evidence": []},
    ]
    sandbox.rs.save(rs)
    # The route shipped on Tuesday. publish() writes this file from what the estate was OBSERVED
    # serving, which is the only statement of "our routes" that keeps up with a deploy.
    with io.open(os.environ["PERSEUS_ROUTES"], "w", encoding="utf-8") as fh:
        json.dump({"generated": now, "served": ["/kundenportal", "/kundenportal/login"]}, fh)

    rep, _rs = sandbox.hub.weekly(dry_run=False, panel=False)
    after = {r["id"]: r["tier"] for r in
             json.load(open(os.environ["PERSEUS_RULESET"], encoding="utf-8"))["rules"]}
    assert after["r1"] == sandbox.rs.TIER_RETIRED, "it now refuses a page we serve"
    assert after["r2"] == sandbox.rs.TIER_BLOCK, "and the other rule was left alone"
    assert [r["id"] for r in rep["revetted"]] == ["r1"]

    published = json.load(open(os.environ["PERSEUS_BLOCKLIST"], encoding="utf-8"))
    pats = [p["pattern"] for p in published["patterns"]]
    assert "/kundenportal" not in pats, "the retirement has to REACH the five sidecars"
    assert r"/wp-login\.php" in pats


def test_the_weekly_retires_what_a_month_of_traffic_never_matched(sandbox):
    """A rule nobody has ever matched is compiled on every client reload and evaluated on every
    request of six properties, and it is evidence of nothing. The AGE FLOOR is what makes this
    safe: without it the pass would retire the whole detection queue before it ever reached its
    own promotion test."""
    now = time.time()
    rs = sandbox.rs.blank()
    rs["rules"] = [
        {"id": "old", "pattern": "/zzzdormantzzz", "tier": sandbox.rs.TIER_DETECT,
         "created": now - 40 * 86400, "promoted": None, "demoted": None,
         "hits": 0, "clean_hits": 0, "reviewers": [], "why": "", "evidence": []},
        {"id": "young", "pattern": "/zzzfreshzzz", "tier": sandbox.rs.TIER_DETECT,
         "created": now - 2 * 86400, "promoted": None, "demoted": None,
         "hits": 0, "clean_hits": 0, "reviewers": [], "why": "", "evidence": []},
    ]
    sandbox.rs.save(rs)
    rep, _rs = sandbox.hub.weekly(dry_run=False, panel=False)
    after = {r["id"]: r["tier"] for r in
             json.load(open(os.environ["PERSEUS_RULESET"], encoding="utf-8"))["rules"]}
    assert after["old"] == sandbox.rs.TIER_RETIRED
    assert after["young"] == sandbox.rs.TIER_DETECT, \
        "a rule two days old has not been tested by traffic and must not be called dormant"
    assert [r["id"] for r in rep["retired"]] == ["old"]


def test_the_weekly_does_real_work_with_no_models_and_no_evidence(sandbox):
    """A weekly job that can only run when Loki, the panel and the budget are all healthy is a
    weekly job that does not run in the weeks anybody needed it. The maintenance half reads the
    ruleset, which is on the shared volume, and needs nothing else."""
    now = time.time()
    rs = sandbox.rs.blank()
    rs["rules"] = [{"id": "old", "pattern": "/zzzdormantzzz", "tier": sandbox.rs.TIER_DETECT,
                    "created": now - 40 * 86400, "promoted": None, "demoted": None,
                    "hits": 0, "clean_hits": 0, "reviewers": [], "why": "", "evidence": []}]
    sandbox.rs.save(rs)
    rep, _rs = sandbox.hub.weekly(dry_run=False, panel=False)
    assert FakePanel.calls == [], "--no-panel must not ask a single model"
    assert rep["retired"], "and it still did the work"
    state = json.load(open(os.environ["PERSEUS_WEEKLY_STATE"], encoding="utf-8"))
    assert state["runs"] == 1 and state["retired"] == 1


def test_a_weekly_dry_run_writes_nothing(sandbox):
    """Same contract as the daily dry run: decide out loud, change nothing."""
    now = time.time()
    rs = sandbox.rs.blank()
    rs["rules"] = [{"id": "old", "pattern": "/zzzdormantzzz", "tier": sandbox.rs.TIER_DETECT,
                    "created": now - 40 * 86400, "promoted": None, "demoted": None,
                    "hits": 0, "clean_hits": 0, "reviewers": [], "why": "", "evidence": []}]
    sandbox.rs.save(rs)
    before = io.open(os.environ["PERSEUS_RULESET"], "rb").read()
    rep, _rs = sandbox.hub.weekly(dry_run=True, panel=False)
    assert io.open(os.environ["PERSEUS_RULESET"], "rb").read() == before
    assert not os.path.exists(os.environ["PERSEUS_WEEKLY_STATE"])
    assert rep["retired"], "it still reports what the real pass would do"


def test_the_weekly_says_what_corpus_it_judged_against(sandbox):
    """PRINT THE COMPARISON YOU MADE. With no observed corpus the pass is WEAKER, not equivalent:
    fewer rules are caught matching something we serve. A report that hid that would be a report
    that quietly downgraded itself."""
    rep, _rs = sandbox.hub.weekly(dry_run=True, panel=False)
    assert rep["revet_corpus_age_h"] is None
    assert any("corpus" in e for e in rep["errors"])
    assert "MISSING" in sandbox.hub.render_weekly(rep)


def test_publish_never_blanks_the_route_corpus(sandbox):
    """A cycle that saw nothing must not overwrite the corpus with an empty one, or the next weekly
    pass re-vets every live rule against an empty world and retires nothing. Same rule as the Caddy
    fragment that must never be truncated by a failed substitution."""
    rs = sandbox.rs.blank()
    sandbox.hub.publish(rs, [ev("1.1.1.1", "/kundenportal", 200)])
    first = json.load(open(os.environ["PERSEUS_ROUTES"], encoding="utf-8"))
    assert first["served"] == ["/kundenportal"]
    sandbox.hub.publish(rs, [])
    assert json.load(open(os.environ["PERSEUS_ROUTES"], encoding="utf-8"))["served"] == \
        ["/kundenportal"]


# ══ THE UNITS, WHICH IS THE HALF A BEHAVIOUR TEST CANNOT SEE ═══════════════════════════════════

def _install_script():
    import importlib.util
    spec = importlib.util.spec_from_file_location("perseus_cli", os.path.join(ROOT, "perseus.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    return cli, cli.install_script("BLOB")


def test_the_weekly_timer_exists_and_is_a_different_unit_on_a_different_schedule():
    """A FLAG ON THE DAILY UNIT WOULD NOT BE A WEEKLY CYCLE. The operator asked for daily AND
    weekly, and 'the daily job sometimes does more' is neither auditable in `systemctl list-timers`
    nor recoverable when the daily one is wedged."""
    _cli, s = _install_script()
    assert "/etc/systemd/system/perseus-weekly.service" in s
    assert "/etc/systemd/system/perseus-weekly.timer" in s
    assert "hub.py --weekly" in s

    # DERIVE the distinctness, never eyeball it: three units, three schedules, no two the same.
    cal = [l.strip() for l in s.splitlines() if l.strip().startswith("OnCalendar=")]
    assert len(cal) == len(set(cal)) == 3, cal
    assert "OnCalendar=*-*-* 04:40:00 UTC" in cal, "the daily schedule must not have moved"
    assert "OnCalendar=Sun *-*-* 05:20:00 UTC" in cal
    execs = [l.strip() for l in s.splitlines() if l.strip().startswith("ExecStart=")]
    assert len(execs) == len(set(execs)) == 3, execs


def test_the_weekly_timer_is_armed_and_the_state_is_queried_not_assumed():
    """`systemctl enable --now ... || true` swallowed the failure once already, and `list-timers`
    then printed a header with no row -- which is exactly what an unarmed timer looks like -- while
    the script said "Installed."."""
    _cli, s = _install_script()
    assert "systemctl enable --now perseus-weekly.timer" in s
    assert "$(systemctl is-enabled perseus-weekly.timer" in s
    assert "$(systemctl is-active perseus-weekly.timer" in s
    assert "WEEKLY_TIMER_OK" in s
    assert "systemctl enable --now perseus-watch.timer" in s
    assert "$(systemctl is-enabled perseus-watch.timer" in s
    assert "WATCH_TIMER_OK" in s


def test_the_install_proves_each_new_job_RAN_not_merely_that_it_is_armed():
    """TIMER_OK says systemd will CALL something. It said exactly that every night for weeks while
    the daily cycle died on ENOENT inside the container. So each unit is asked, AT THE PATH IT
    WRITES, INSIDE THE CONTAINER, whether it has produced anything recently."""
    _cli, s = _install_script()
    for probe, marker in (("perseus_weekly.json", "WEEKLY_DEAD"),
                          ("perseus_watch.json", "WATCH_DEAD")):
        assert "docker exec colt-web python3 -c" in s
        assert probe in s, "the %s check must read the artifact, not the unit file" % marker
        i = s.find(marker)
        assert i != -1, "there must be a named failure for %s" % probe
        assert "exit 1" in s[i:i + 600], "and it must fail the install under set -e"
    # The bootstrap must not bill the account on every ship.
    assert "hub.py --weekly --no-panel" in s
    assert "hub.py --watch --no-panel" in s


def test_install_only_reports_every_unarmed_unit_by_name():
    """Reporting "armed" because ONE marker answered is how a half-installed SOC reads as a healthy
    one, and the missing unit is always the one nobody was watching."""
    src = io.open(os.path.join(ROOT, "perseus.py"), encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    i = body.index("if a.install_only:")
    branch = body[i:i + 700]
    for mark in ("TIMER_OK", "WEEKLY_TIMER_OK", "WATCH_TIMER_OK"):
        assert mark in branch, "%s is not required before the install claims success" % mark
    assert "return 1" in branch


def test_the_incident_module_writes_through_the_one_atomic_implementation():
    """Same rule test_perseus_ruleset.py already enforces for hub/abuse/ruleset, extended to the new
    file. A fourth hand-rolled temp+replace is a fourth place for the Windows PermissionError retry
    to be missing, and perseus/client.py polls these files from six projects."""
    import ast
    src = io.open(os.path.join(ROOT, "perseus", "incident.py"), encoding="utf-8").read()
    calls = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "replace"
             and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
    assert not calls, "incident.py must not hand-roll its own replace"


def test_the_watch_verb_is_wired_from_the_hub_to_the_incident_pass(sandbox, monkeypatch):
    """WIRING, which no behaviour test can see. shield.py was fully tested while nothing asserted
    the middleware ever called it; the systemd unit runs `hub.py --watch`, so that verb has to
    reach incident.run()."""
    seen = {}

    def _run(**kw):
        seen.update(kw)
        return {"incidents": [], "skipped": [], "errors": []}
    monkeypatch.setattr(sandbox.inc, "run", _run)
    sandbox.hub.watch(dry_run=True, ask_models=False)
    assert seen.get("dry_run") is True and seen.get("ask_models") is False


def test_the_shipped_package_carries_the_incident_module():
    """A file that is not in pack() is a file the droplet never receives, and the hub would then
    die on `import incident` -- the same shape as the ENOENT that killed the nightly cycle."""
    import base64
    import tarfile
    cli, s = _install_script()
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(cli.pack())), mode="r:gz") as tf:
        names = tf.getnames()
    assert "perseus/incident.py" in names, names
    assert "incident" in s, "the install's own import check must name it too"
