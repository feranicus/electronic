# -*- coding: utf-8 -*-
"""THE COLD START: giving the promotion gate something to consider, without moving the gate.

WHAT THIS FILE IS ABOUT. Measured on production, 2026-09-10:

    published_cycle 1   published_patterns 0
    enforce {unknown:0, none:3, armed:0, empty:2, active:0}

Three schedules proven to run by artifact, and a blocklist with nothing in it. The cause is not a
broken gate; it is an EMPTY QUEUE. `hub.mine()` proposes only paths the corpus CANNOT already name,
so an estate whose detector is good proposes nothing, and `ruleset.can_promote()` had never in its
life been handed a candidate to consider. A gate that is never called is indistinguishable from a
gate that always refuses, and the report said only "nothing promoted".

So the committed probe corpus is offered to the gate as ordinary candidates. The tests below exist
to prove that "ordinary" is literal:

  * the seed is DERIVED from `perseus.client.CLASSES` at call time, not retyped beside it. Proven by
    MUTATING the shared table and watching the seed change -- by construction, not by grepping for
    a comment. Two copies of one vocabulary is the defect this estate has paid for four times.
  * a seed clears `vet.vet()` or it is refused, on exactly the same barriers as a model's proposal;
  * a seed that matches something we SERVE is refused, and that is not hypothetical: `admin_panel`
    matches /api/admin/users, and `perseus_client.check()` has no never-block prefix, so a promoted
    `admin_panel` would have refused the administration API on five sites at once;
  * a seed cannot promote before its 24 hours, cannot promote without three vendors, cannot promote
    without a hostile match, and is refused outright by one legitimate match;
  * and -- the positive control, without which every refusal above could be passing for the wrong
    reason -- a seed that HAS soaked, HAS been corroborated and HAS matched only hostile traffic
    DOES promote. A negative test that passes because the subject never got off the ground measures
    nothing.

NOTHING HERE REACHES THE NETWORK OR A MODEL. Every event is a dict built in this file; `hub.seed`,
`ruleset.score_detection` and `hub.apply_rule_review` are all deterministic and ask no vendor
anything. `hub.ask_rule_review` -- the one function here that would spend money -- is never called.

WINDOWS. No `os.uname`, no `/proc`, no `fcntl`, no path handed to a POSIX shell, and no file is
written outside tmp_path. The clock is passed in explicitly everywhere it matters, so nothing here
is a race.
"""
import os
import re
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.join(ROOT, "perseus"), os.path.join(ROOT, "webapp", "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# IMPORTED THE WAY THE SYSTEMD UNIT RUNS IT -- `hub` as a script-level name, with the package
# directory on the path. `perseus.vet` and `vet` are two module objects loaded from one file, and a
# test that vetted through one while the code vetted through the other would be measuring a copy.
# So every assertion below goes through the SAME objects hub itself holds.
import hub as H                                    # noqa: E402
import perseus.client as PC                        # noqa: E402

R = H.RS
V = H.VET


# ── helpers ───────────────────────────────────────────────────────────────────────────────────
def ev(path, status=404, ts=None, ip="203.0.113.9"):
    """One observed request, in the shape collect() produces."""
    return {"ip": ip, "path": path, "status": status, "project": "cybergod",
            "_ts": ts if ts is not None else time.time()}


def cold():
    """A ruleset that blocks nothing: the state the estate was actually measured in."""
    rs = R.blank()
    assert R.summary(rs)["blocking"] == 0, "the fixture is not cold, so nothing below is about a cold start"
    return rs


def rule_named(rs, name):
    """The seeded rule whose pattern came from class `name`, or None."""
    want = dict((n, rx.pattern) for n, rx in PC.CLASSES).get(name)
    for r in rs.get("rules") or []:
        if r.get("pattern") == want:
            return r
    return None


def scored_for(scored, rule):
    """The scoring row for ONE rule.

    NEVER `scored[0]`. A seeded ruleset holds twenty patterns and several of them legitimately
    match the same probe path -- /wp-login.php is both `wordpress` and `php_probe` -- so an index
    is a position, and a check that asserts on a position rather than on the subject is one edit
    away from silently measuring a different rule.
    """
    for row in scored or []:
        if row.get("id") == rule.get("id"):
            return row
    return None


# =================================================================================================
# 1. ONE HOME. The seed is derived, not retyped.
# =================================================================================================
def test_the_seed_is_derived_from_the_shared_class_table_and_not_a_second_copy(monkeypatch):
    """PROVEN BY CONSTRUCTION, not by reading a comment.

    A retyped list would pass a subset check on the day it was written and drift the first time
    somebody edits `perseus.client`. So the test EDITS the shared table and requires the seed to
    change with it: only a derivation can do that, and only at call time.
    """
    base, provenance = R.seed_candidates()

    # PROVE THE FIXTURE FIRST. If the table could not be imported the seed is empty, and every
    # assertion below would pass vacuously against nothing at all.
    assert base, "no seed candidates at all: %s" % provenance
    assert "CLASSES" in provenance, provenance
    live = {rx.pattern for _n, rx in PC.CLASSES}
    assert live, "the shared class table is empty, so this test has no subject"

    # Nothing in the seed that is not in the table. This catches a hand-written extra.
    assert {c["pattern"] for c in base} <= live

    # ...and now the half a subset check cannot see: change the SOURCE and the seed must follow.
    novel = re.compile(r"(?i)^/zzz-seed-derivation-probe-zzz(?:$|/)")
    assert novel.pattern not in live, "the marker must not already exist or this proves nothing"
    monkeypatch.setattr(PC, "CLASSES", list(PC.CLASSES) + [("zzz_probe", novel)])

    after, _p = R.seed_candidates()
    assert novel.pattern in {c["pattern"] for c in after}, (
        "the seed did not follow the shared table, so it is a second copy of it")
    assert len(after) == len(base) + 1


def test_every_seed_rule_carries_its_provenance_in_the_ledger():
    """A rule nobody can explain is a rule nobody dares delete. `source` answers "why is this here"
    six weeks from now without anybody having to remember."""
    rs = cold()
    rep = H.seed(rs, known_good=[])
    assert rep["added"], "nothing was seeded, so there is no provenance to check: %s" % rep
    for r in rs["rules"]:
        assert r["source"] == R.SOURCE_SEED == "seed"
        assert r["evidence"] and "CLASSES" in r["evidence"][0]
        assert r["tier"] == R.TIER_DETECT, "a seed may never arrive already blocking"
        assert r["reviewers"] == [], (
            "a seed arrives with NO reviewers: writing vendor names onto a rule no vendor saw "
            "would be a forged quorum in the one ledger that has to be trustworthy")


# =================================================================================================
# 2. A SEED IS EXEMPT FROM NOTHING. It clears vet or it is refused.
# =================================================================================================
def test_a_seed_candidate_still_has_to_clear_vet(monkeypatch):
    """The barriers do not know what a seed is, and that is the point.

    The table is replaced with one good pattern and two that vet must refuse for two DIFFERENT
    reasons -- catastrophically broad, and a two-character fragment -- so one barrier working
    cannot carry the test. The third barrier, "does not compile", cannot be reached through a
    compiled CLASSES entry and is asserted against vet directly, which is the same call seed() makes.
    """
    junk = [("too_broad", re.compile(r".*")),
            ("fragment", re.compile(r"ab")),
            ("good_one", re.compile(r"/zzz-seed-only-probe-zzz\.php"))]

    # PROVE THE FIXTURE. Each pattern must already be refused (or accepted) by vet on its own,
    # or the seed test below would be measuring the seed rather than the barrier.
    assert V.vet(r".*")[0] is False
    assert V.vet(r"ab")[0] is False
    assert V.vet(r"/zzz-seed-only-probe-zzz\.php")[0] is True

    # An uncompilable pattern cannot be a compiled CLASSES entry, so it is tested through vet
    # directly -- the same call hub.seed() makes.
    assert V.vet(r"/(unclosed")[0] is False

    monkeypatch.setattr(PC, "CLASSES", junk)
    rs = cold()
    rep = H.seed(rs, known_good=[])

    assert [a["name"] for a in rep["added"]] == ["good_one"]
    assert sorted(r["name"] for r in rep["refused"]) == ["fragment", "too_broad"]
    assert len(rs["rules"]) == 1, "a refused seed must not reach the ruleset at all"
    # A REFUSAL THAT DOES NOT SAY WHY TEACHES NOTHING -- it is the most useful line in the delta.
    assert all(r["why"] for r in rep["refused"])


def test_a_seed_that_matches_a_route_we_serve_is_refused():
    """THE BARRIER THAT PROTECTS CUSTOMERS, and it is not hypothetical here.

    `admin_panel` is `/(admin|manager|phpmyadmin|adminer|cpanel|webadmin)`, which matches
    /api/admin/users -- a route we serve. `perseus_client.check()` consults the published patterns
    BEFORE the never-block prefixes are considered, so promoting this class would have refused the
    administration API on all five sites. The seed is not trusted past this barrier.
    """
    admin = dict((n, rx) for n, rx in PC.CLASSES).get("admin_panel")
    assert admin is not None, "the class this test is about no longer exists"

    # PROVE THE FIXTURE: the class really does match a path in the committed corpus.
    served = [g for g in V.KNOWN_GOOD if admin.search(g)]
    assert served, "admin_panel no longer matches anything we serve, so this test proves nothing"

    rs = cold()
    rep = H.seed(rs, known_good=[])
    refused = {r["name"]: r["why"] for r in rep["refused"]}
    assert "admin_panel" in refused, "a seed matching a served route was accepted"
    assert "we actually serve" in refused["admin_panel"]
    assert rule_named(rs, "admin_panel") is None


def test_the_observed_corpus_and_not_only_the_committed_one_refuses_a_seed():
    """Routes ship. The corpus that decides is the one publish() wrote from OBSERVED traffic, so a
    class that is safe against the committed routes must still be refused once we are seen serving
    something it matches. Same rule as the weekly re-vet, applied at the moment of seeding."""
    template = dict((n, rx) for n, rx in PC.CLASSES).get("template")
    assert template is not None

    # PROVE THE FIXTURE, BOTH WAYS. It must be ACCEPTED without the observed corpus, or the refusal
    # below would be caused by something else entirely and this test would measure that instead.
    ok_before, _w = V.vet(template.pattern)
    assert ok_before, "template is already refused by the committed corpus; pick another class"
    observed = ["//assets/index-abc123.js"]
    assert template.search(observed[0]), "the observed path does not match, so nothing flips"

    ok_after, why = V.vet(template.pattern, observed)
    assert not ok_after and "we actually serve" in why

    rs = cold()
    rep = H.seed(rs, known_good=observed)
    assert "template" in {r["name"] for r in rep["refused"]}
    assert rule_named(rs, "template") is None


def test_the_seed_is_a_cold_start_and_not_a_top_up():
    """Once a rule has earned TIER_BLOCK the estate is learning on its own; priming it again would
    only widen a queue that is already moving."""
    rs = cold()
    assert H.seed(rs, known_good=[])["added"], "the cold estate must seed, or the contrast is fake"

    warm = R.blank()
    warm["rules"] = [{"id": "r0-1", "pattern": r"/zzz-already-blocking-zzz", "tier": R.TIER_BLOCK,
                      "created": time.time() - 99 * 3600, "hits": 4, "clean_hits": 0,
                      "reviewers": ["a", "b", "c"], "source": R.SOURCE_MINED, "evidence": [],
                      "why": "", "promoted": time.time(), "demoted": None}]
    assert R.summary(warm)["blocking"] == 1, "the warm fixture does not block, so it is not warm"

    rep = H.seed(warm, known_good=[])
    assert rep["added"] == [] and "already blocking" in rep["skipped"]
    assert len(warm["rules"]) == 1


def test_a_seed_that_could_not_be_derived_is_reported_as_a_failed_read(monkeypatch):
    """A CHECK THAT CANNOT SEE ITS SUBJECT MUST NOT REPORT ITS OWN BLINDNESS AS A FINDING.
    "the class table would not import" and "there was nothing to seed" look identical from the
    outside and only one of them is good news."""
    monkeypatch.setattr(R, "_class_table", lambda: (None, ""))
    rs = cold()
    rep = H.seed(rs, known_good=[])
    assert rep["added"] == []
    assert "could not be imported" in rep["skipped"], rep["skipped"]
    assert rs["rules"] == []


# =================================================================================================
# 3. THE GATE IS NOT MOVED. Each clause, and then the positive control.
# =================================================================================================
def _seeded(known_good=None):
    """A cold estate, seeded, with the `wordpress` rule pulled out for the gate tests."""
    rs = cold()
    H.seed(rs, known_good=known_good or [])
    r = rule_named(rs, "wordpress")
    assert r is not None, "the wordpress class was not seeded, so the gate tests have no subject"
    assert r["tier"] == R.TIER_DETECT and not r["hits"] and not r["reviewers"]
    return rs, r


def test_a_seed_cannot_promote_before_its_soak():
    """MIN_DETECT_HOURS. Being committed code buys a rule a place in the queue and nothing else."""
    now = time.time()
    rs, r = _seeded()
    # Everything EXCEPT the soak is satisfied, so the soak is the only thing under test. A negative
    # test that passes because three other clauses also failed measures those clauses.
    r["created"] = now - 2 * 3600
    r["reviewers"] = ["vendor-a", "vendor-b", "vendor-c"]
    r["hits"], r["clean_hits"] = 7, 0

    clauses = [m["clause"] for m in R.shortfall(r, now)]
    assert clauses == ["soak"], clauses
    ok, why = R.promote(rs, r, now)
    assert not ok and "in detection" in why
    assert r["tier"] == R.TIER_DETECT

    short = R.shortfall(r, now)[0]
    assert short["need"] == R.MIN_DETECT_HOURS and short["have"] == pytest.approx(2.0, abs=0.1)
    assert "more in detection" in short["short"], "the report must say BY HOW MUCH, not just no"


def test_a_seed_cannot_promote_without_three_vendors():
    """A seed arrives with none, deliberately. It has to be corroborated like anything else."""
    now = time.time()
    rs, r = _seeded()
    r["created"] = now - 48 * 3600
    r["hits"], r["clean_hits"] = 7, 0
    r["reviewers"] = ["vendor-a", "vendor-b"]

    assert [m["clause"] for m in R.shortfall(r, now)] == ["quorum"]
    ok, why = R.promote(rs, r, now)
    assert not ok and "reviewer" in why
    assert R.shortfall(r, now)[0]["short"] == "1 more vendor(s) must agree"


def test_a_seed_cannot_promote_without_a_hostile_match():
    """Absence of evidence is never a finding, which is the oldest rule in this codebase."""
    now = time.time()
    rs, r = _seeded()
    r["created"] = now - 48 * 3600
    r["reviewers"] = ["vendor-a", "vendor-b", "vendor-c"]
    r["hits"], r["clean_hits"] = 0, 0

    assert [m["clause"] for m in R.shortfall(r, now)] == ["evidence"]
    ok, why = R.promote(rs, r, now)
    assert not ok and "never matched" in why


def test_one_legitimate_match_refuses_a_seed_outright():
    """THE CLAUSE THAT PROTECTS CUSTOMERS. There is no number of good days that earns this back,
    and the shortfall must not quote one."""
    now = time.time()
    rs, r = _seeded()
    r["created"] = now - 48 * 3600
    r["reviewers"] = ["vendor-a", "vendor-b", "vendor-c"]
    r["hits"], r["clean_hits"] = 40, 1

    miss = R.shortfall(r, now)
    assert [m["clause"] for m in miss] == ["clean"]
    assert "REFUSED OUTRIGHT" in miss[0]["short"]
    ok, why = R.promote(rs, r, now)
    assert not ok and "legitimate" in why


def test_a_soaked_corroborated_seed_that_matched_only_hostile_traffic_does_promote():
    """THE POSITIVE CONTROL, and every refusal above is worthless without it.

    Run end to end through the machinery the cycle uses -- seed, score against real observed
    traffic, record three vendor agreements, then ask the gate -- rather than by hand-setting the
    fields the gate reads. Hand-setting them would prove the arithmetic and nothing about whether
    anything ever reaches it, which is exactly how `record_hit()` came to be called by nothing
    outside the test suite for the whole life of this subsystem.
    """
    now = time.time()
    rs, r = _seeded()
    r["created"] = now - 48 * 3600           # it has been watching for two days
    r.pop("scored_until", None)

    # PROVE THE FIXTURE: nothing has been recorded yet, so the gate must currently refuse.
    assert not R.can_promote(r, now)[0]

    evs = [ev("/wp-login.php", 404, now - 3600),
           ev("/wp-content/plugins/x.php", 404, now - 3500),
           ev("/xmlrpc.php", 404, now - 3400)]
    assert all(re.search(r["pattern"], e["path"], re.I) for e in evs), \
        "the events do not match the rule, so scoring them proves nothing"

    row = scored_for(R.score_detection(rs, evs, served=[], now=now), r)
    assert row and row["hostile"] == 3 and row["clean"] == 0
    assert r["hits"] == 3 and r["clean_hits"] == 0

    # Three vendors agree. `apply_rule_review` is the only thing that may write a reviewer, and it
    # is a SET UNION, so one model cannot vote three times.
    votes = {r["id"]: {"keep": ["vendor-a", "vendor-b", "vendor-c"], "drop": [], "why": {}}}
    applied = H.apply_rule_review(rs, votes)
    assert applied["corroborated"] and r["reviewers"] == ["vendor-a", "vendor-b", "vendor-c"]

    assert R.shortfall(r, now) == [], R.shortfall(r, now)
    ok, why = R.promote(rs, r, now)
    assert ok, why
    assert r["tier"] == R.TIER_BLOCK and r["source"] == R.SOURCE_SEED
    assert any(h["action"] == "promoted" and h["id"] == r["id"] for h in rs["history"])

    # ...and only now does it reach a sidecar. publish() reads the BLOCK tier and nothing else.
    assert r["pattern"] in {rr["pattern"] for rr, _rx in R.active_patterns(rs, R.TIER_BLOCK)}


def test_one_vendor_answering_every_night_can_never_become_a_quorum():
    """The clause counts REVIEWERS, not VOTES. A set union is the whole reason a single vendor
    having a bad month cannot change what the estate refuses."""
    rs, r = _seeded()
    for _ in range(5):
        H.apply_rule_review(rs, {r["id"]: {"keep": ["vendor-a"], "drop": [], "why": {}}})
    assert r["reviewers"] == ["vendor-a"]
    assert any(m["clause"] == "quorum" for m in R.shortfall(r))


def test_three_vendors_refusing_a_pattern_retire_it():
    """Narrowing is the safe direction: retiring only ever REMOVES a refusal, so unlike promotion
    it cannot deny a real visitor and does not have to wait for a soak."""
    rs, r = _seeded()
    votes = {r["id"]: {"keep": ["vendor-d"], "drop": ["vendor-a", "vendor-b", "vendor-c"],
                       "why": {"vendor-a": "matches an ordinary blog path"}}}
    applied = H.apply_rule_review(rs, votes)
    assert applied["retired"] and r["tier"] == R.TIER_RETIRED
    assert r["reviewers"] == [], "a retired rule must not also collect the keep vote"
    assert R.shortfall(r)[0]["clause"] == "tier"


# =================================================================================================
# 4. SCORING. The half of the gate that had never been wired.
# =================================================================================================
def test_a_request_we_served_is_a_clean_hit_and_not_evidence():
    """A 404 on a stale route OF OURS is not evidence, however many there are -- the 2026-08-10
    lesson (two genuine visitors, 439 and 362 stale-link 404s each) applied to patterns instead of
    addresses. Both halves of the split are asserted, because a corpus on which everything scores
    the same way would pass while proving nothing."""
    now = time.time()
    rs, r = _seeded()
    r["created"] = now - 48 * 3600
    evs = [ev("/wp-login.php", 404, now - 60),          # hostile: unserved, and it missed
           ev("/wp-content/logo.png", 200, now - 61),   # clean: we answered it
           ev("/wp-json/oembed", 404, now - 62)]        # clean: we are observed serving this path
    served = ["/wp-json/oembed"]
    assert all(re.search(r["pattern"], e["path"], re.I) for e in evs), "no event matches the rule"

    got = scored_for(R.score_detection(rs, evs, served=served, now=now), r)
    assert got and got["hostile"] == 1 and got["clean"] == 2
    assert r["hits"] == 1 and r["clean_hits"] == 2
    assert [m["clause"] for m in R.shortfall(r, now)] == ["quorum", "clean"]


def test_the_same_traffic_is_never_counted_twice():
    """The daily cycle collects SEVEN days every single night. Without a watermark one hostile
    packet would earn the evidence clause seven times over, and 'it matched real traffic' would be
    a statement about how often we look rather than about what arrived."""
    now = time.time()
    rs, r = _seeded()
    r["created"] = now - 48 * 3600
    evs = [ev("/wp-login.php", 404, now - 3600) for _ in range(3)]

    first = scored_for(R.score_detection(rs, evs, served=[], now=now), r)
    assert first and first["hostile"] == 3, "the fixture recorded nothing on the first pass"
    second = R.score_detection(rs, evs, served=[], now=now)
    assert second == [], "the same events were scored a second time"
    assert r["hits"] == 3


def test_a_rule_is_never_scored_on_traffic_that_predates_it():
    """A rule that did not exist cannot have been watching.

    The soak clause claims a rule spent a day watching REAL traffic, and that must not be
    satisfiable retroactively out of yesterday's log.
    """
    now = time.time()
    rs, r = _seeded()
    r["created"] = now - 600                      # ten minutes old
    old = [ev("/wp-login.php", 404, now - 7200)]  # two hours ago
    assert re.search(r["pattern"], old[0]["path"], re.I), "the fixture event does not match"

    assert R.score_detection(rs, old, served=[], now=now) == []
    assert r["hits"] == 0

    # PROVE THE FIXTURE IS NOT SIMPLY INERT: the identical event, dated after the rule, IS counted.
    fresh = [ev("/wp-login.php", 404, now - 60)]
    row = scored_for(R.score_detection(rs, fresh, served=[], now=now), r)
    assert row and row["hostile"] == 1


# =================================================================================================
# 5. THE REPORT. "Nothing promoted" with no reason is the failure mode this repo keeps paying for.
# =================================================================================================
def test_the_report_names_the_clause_each_rule_is_short_of_and_by_how_much():
    now = time.time()
    rs, _r = _seeded()
    gate = R.gate_status(rs, now)

    assert gate["seeded"] == gate["detecting"] > 0
    assert gate["blocking"] == 0 and gate["ready"] == 0
    assert gate["unscored"] == gate["detecting"], (
        "a rule that has never been scored must be reported as UNKNOWN, not as zero matches")

    text = H.render({"gate": gate})
    assert "PROMOTION GATE" in text

    # THE HEADLINE NUMBERS ARE IN THE REPORT, not only in a JSON blob nobody opens.
    assert "%d blocking" % gate["blocking"] in text
    assert "%d in detection" % gate["detecting"] in text

    # WHICH CLAUSE, FOR THE WHOLE QUEUE. One line that answers "why is nothing blocking".
    assert "held by:" in text
    assert "soak %d" % gate["detecting"] in text
    assert "quorum %d" % gate["detecting"] in text
    assert "evidence %d" % gate["detecting"] in text

    # ...AND BY HOW MUCH, per rule, in full and NOT truncated mid-sentence.
    assert "short of soak" in text and "more in detection" in text
    assert "short of quorum" in text and "3 more vendor(s) must agree" in text
    assert "short of evidence" in text and "1 hostile match in real traffic" in text

    # OUR OWN BLINDNESS IS NAMED RATHER THAN SCORED AS ZERO.
    assert "never been scored" in text
    assert "UNKNOWN, not zero" in text


def test_the_report_does_not_claim_nothing_changed_on_a_cycle_that_seeded():
    """A verdict is read far more often than a body. 'NO EVIDENCE - nothing changed' on the night
    twenty patterns entered detection would teach the operator to stop reading the rest."""
    rs = cold()
    rep = H.seed(rs, known_good=[])
    assert rep["added"], "nothing was seeded, so there is no verdict to check"
    text = H.render({"seed": rep, "gate": R.gate_status(rs)})
    assert "SEEDED" in text and str(len(rep["added"])) in text
    assert "nothing. " not in text, (
        "the WHAT CHANGED section said nothing happened on the night twenty patterns entered "
        "detection; a verdict is read far more often than a body")
    # AND THE REFUSALS ARE AS LOUD AS THE ACCEPTANCES -- admin_panel is refused every time, and a
    # seed that was silently dropped would look exactly like a seed that was never offered.
    assert rep["refused"], "nothing was refused, so this half of the report has no subject"
    for r in rep["refused"]:
        assert "seed %s" % r["name"] in text, (
            "%s was refused and the report did not say so; a silently dropped seed looks exactly "
            "like a seed that was never offered" % r["name"])
