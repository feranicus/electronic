"""The adaptive defence may change itself. These tests are the reason that is survivable.

The operator chose "full auto within bounds" on 2026-09-07. That is a defensible choice ONLY if
the bounds are real, the vetting bites, and a rule that turns out to be wrong reverts itself. Each
of those is asserted here, and each was negative-tested by breaking it and watching this file fail.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from perseus import ruleset as R, vet as V          # noqa: E402


# ── bounds ───────────────────────────────────────────────────────────────────────────────
def test_a_threshold_outside_the_committed_range_cannot_be_read():
    """CLAMP ON READ. A hand-edited store, a corrupt file or anything that reached the JSON still
    cannot hand a consumer a value outside BOUNDS, because every consumer goes through
    thresholds(). ENRICH_MODELS had four homes and the stale one won for weeks; a constraint
    enforced at one write path is a constraint somebody eventually routes around."""
    rs = R.blank()
    rs["thresholds"]["ip_per_min"] = 100000
    assert R.thresholds(rs)["ip_per_min"] == R.BOUNDS["ip_per_min"][1]
    rs["thresholds"]["ip_per_min"] = 0
    assert R.thresholds(rs)["ip_per_min"] == R.BOUNDS["ip_per_min"][0]
    rs["thresholds"]["ip_per_min"] = "; DROP TABLE"
    assert R.thresholds(rs)["ip_per_min"] == R.DEFAULTS["ip_per_min"], "junk falls back, never crashes"


def test_an_unknown_key_never_becomes_a_threshold():
    assert R.clamp("not_a_real_key", 5) is None
    assert R.clamp("ip_per_min", None) is None


def test_a_missing_or_corrupt_store_still_yields_a_working_defence():
    """A file that will not parse must not disarm the estate. The committed defaults are a
    complete ruleset on their own."""
    rs = R.load("/nope/nope/perseus.json")
    assert R.thresholds(rs) == R.DEFAULTS and rs["rules"] == []


# ── promotion ────────────────────────────────────────────────────────────────────────────
def _proposed(hours_old=48, reviewers=("deepseek", "llama", "gemma"), hits=9, clean=0):
    rs = R.blank()
    r = R.propose(rs, r"/wp-admin/setup-config\.php", "wordpress install probe",
                  ["/wp-admin/setup-config.php"], list(reviewers))
    r["created"] = time.time() - hours_old * 3600
    r["hits"], r["clean_hits"] = hits, clean
    return rs, r


def test_a_vetted_corroborated_pattern_that_watched_for_a_day_is_promoted():
    rs, r = _proposed()
    ok, why = R.promote(rs, r)
    assert ok and r["tier"] == R.TIER_BLOCK, why
    assert any(h["action"] == "promoted" for h in rs["history"])


def test_a_pattern_cannot_block_on_its_first_day():
    """MIN_DETECT_HOURS. A rule watches real traffic before it is allowed to refuse any."""
    rs, r = _proposed(hours_old=2)
    ok, why = R.promote(rs, r)
    assert not ok and "in detection" in why and r["tier"] == R.TIER_DETECT


def test_two_reviewers_are_not_a_quorum():
    rs, r = _proposed(reviewers=("deepseek", "llama"))
    ok, why = R.promote(rs, r)
    assert not ok and "reviewer" in why


def test_a_pattern_that_never_matched_anything_is_not_promoted():
    """Nothing justifies blocking on a rule with no evidence behind it. Absence of evidence is
    never a finding, which is the oldest rule in this codebase."""
    rs, r = _proposed(hits=0)
    ok, why = R.promote(rs, r)
    assert not ok and "never matched" in why


def test_a_pattern_that_touched_legitimate_traffic_is_never_promoted():
    """THE ONE THAT PROTECTS CUSTOMERS. Two real visitors with 439 and 362 stale-link 404s would
    have been blocked by a naive rule on 2026-08-10. One legitimate-looking match is a refusal."""
    rs, r = _proposed(clean=1)
    ok, why = R.promote(rs, r)
    assert not ok and "legitimate" in why


# ── auto-revert: the safety net for full autonomy ────────────────────────────────────────
def test_a_blocking_rule_that_hurts_demotes_itself():
    rs, r = _proposed()
    R.promote(rs, r)
    assert r["tier"] == R.TIER_BLOCK
    R.record_hit(rs, r["id"], looked_legitimate=True)      # it refused somebody real
    demoted = R.review(rs)
    assert demoted and r["tier"] == R.TIER_DETECT, "a wrong rule must revert without a human"
    assert any(h["action"] == "demoted" and "legitimate" in h["why"] for h in rs["history"])


def test_a_demoted_rule_keeps_its_evidence_instead_of_vanishing():
    """Deleting it would let the next cycle propose exactly the same thing next week."""
    rs, r = _proposed()
    R.promote(rs, r); R.record_hit(rs, r["id"], looked_legitimate=True); R.review(rs)
    assert r["demoted"] and r["clean_hits"] == 1 and r["pattern"]


def test_review_leaves_a_healthy_blocking_rule_alone():
    rs, r = _proposed()
    R.promote(rs, r)
    R.record_hit(rs, r["id"])                              # another hostile match
    assert R.review(rs) == [] and r["tier"] == R.TIER_BLOCK


# ── tuning ───────────────────────────────────────────────────────────────────────────────
def test_tuning_needs_a_quorum_on_the_direction():
    rs = R.blank()
    before = R.thresholds(rs)["ip_per_min"]
    new, why = R.tune(rs, "ip_per_min", None, [12, 4, 20, 3])   # 2 up, 2 down
    assert new == before and "no quorum" in why


def test_tuning_uses_the_median_and_is_step_capped_and_clamped():
    """One bold model must not drag a threshold. Median of the agreeing side, then at most 25%."""
    rs = R.blank()
    new, _ = R.tune(rs, "ip_per_min", None, [30, 24, 40, 3])    # 3 up: median 30, cur 8
    assert new == 10, new                                       # 8 + cap(2), not 30
    rs2 = R.blank()
    R.tune(rs2, "ip_per_min", None, [99999, 99999, 99999])
    assert R.thresholds(rs2)["ip_per_min"] <= R.BOUNDS["ip_per_min"][1]


# ── vetting ──────────────────────────────────────────────────────────────────────────────
def test_a_pattern_matching_something_we_serve_is_refused():
    """The barrier that matters. Every real route of all six projects is in the corpus."""
    for bad in [r"/api", r"/api/chat", r".*", r"^/", r"/app", r"\.js$"]:
        ok, why = V.vet(bad)
        assert not ok, "%r was accepted: %s" % (bad, why)


def test_a_genuine_attack_pattern_is_accepted():
    for good in [r"/wp-admin/setup-config\.php", r"/\.aws/credentials", r"/phpmyadmin/",
                 r"/\.git/config", r"/cgi-bin/luci"]:
        ok, why = V.vet(good)
        assert ok, "%r was refused: %s" % (good, why)


def test_a_pattern_that_does_not_compile_is_refused_not_raised():
    ok, why = V.vet(r"/(unclosed")
    assert not ok and "compile" in why


def test_a_two_character_fragment_is_refused():
    """The 'struktur' inside 'infrastruktur' failure, which put a property group's whole estate
    into a telecoms company's report."""
    ok, why = V.vet(r"ab")
    assert not ok and "literal" in why


def test_an_expensive_pattern_is_refused_by_measurement():
    """Catastrophic backtracking on a caller-controlled path turns the defence into the outage."""
    ok, why = V.vet(r"/(a+)+!$", budget_ms=1.0)
    assert not ok, why


def test_the_callers_own_routes_extend_the_corpus():
    ok, _ = V.vet(r"/kundenportal/rechnung")
    assert ok, "not in the base corpus, so accepted"
    ok2, why = V.vet(r"/kundenportal/rechnung", known_good=["/kundenportal/rechnung"])
    assert not ok2 and "we actually serve" in why


def test_vet_batch_reports_refusals_as_loudly_as_acceptances():
    acc, ref = V.vet_batch([{"pattern": r"/\.env\.backup"}, {"pattern": ".*"}])
    assert len(acc) == 1 and len(ref) == 1
    assert ref[0]["vet"] and acc[0]["vet"], "both carry the reason; a silent refusal teaches nothing"


# ── the write path, on the operator's platform ───────────────────────────────────────────
def test_atomic_write_survives_a_windows_style_lock(tmp_path, monkeypatch):
    """REPRODUCE WINDOWS ON LINUX, because the suite runs on his machine and the hub runs on ours.

    On POSIX a rename over an open file always succeeds. On WINDOWS os.replace raises
    PermissionError(13) while any handle is open, and perseus/client.py -- copied into six
    projects -- polls the blocklist this writes. A control that behaves differently on the platform
    the operator verifies it on is a control he has to take on trust."""
    import json as _j
    import os as _os
    real = _os.replace
    calls = {"n": 0}

    def windows_like(a, b):
        calls["n"] += 1
        if calls["n"] <= 5:
            raise PermissionError(13, "Access is denied")
        return real(a, b)

    monkeypatch.setattr(_os, "replace", windows_like)
    dest = str(tmp_path / "bl.json")
    assert R.atomic_write(dest, lambda fh: _j.dump({"ok": True}, fh))
    assert calls["n"] > 1, "the retry never fired, so this proved nothing"
    monkeypatch.setattr(_os, "replace", real)
    assert _j.load(open(dest, encoding="utf-8"))["ok"] is True


def test_atomic_write_reports_a_real_failure_instead_of_claiming_success(tmp_path, monkeypatch):
    """A retry loop that swallows every error would report a blocklist as published when it never
    landed -- the thin clients would then enforce yesterday's rules with nobody saying so."""
    import os as _os
    monkeypatch.setattr(_os, "replace",
                        lambda a, b: (_ for _ in ()).throw(OSError(28, "No space left")))
    assert R.atomic_write(str(tmp_path / "x.json"), lambda fh: fh.write("{}")) is False
    assert not [f for f in os.listdir(tmp_path) if ".tmp-" in f], "no temp litter may be left"


def test_every_perseus_write_goes_through_the_one_implementation():
    """WIRING. Three modules used to hand-roll temp+replace; a fix applied to one of them would
    have left the other two on the old behaviour -- the 'several homes' defect this repo records
    more than any other."""
    import ast
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "perseus")
    for name in ("hub.py", "abuse.py", "ruleset.py"):
        src = open(os.path.join(base, name), encoding="utf-8").read()
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "replace"
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
        if name == "ruleset.py":
            assert len(calls) == 1, "ruleset owns the ONE implementation"
        else:
            assert not calls, "%s must not hand-roll its own replace" % name
