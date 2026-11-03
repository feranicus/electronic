#!/usr/bin/env python3
"""test_deck_langs_coverage.py - a language is offered only when its pack is COMPLETE.

WHY THIS FILE EXISTS
    deck_langs.py has always said "half a language is not a language", and until Portuguese was
    added it enforced that at the granularity of a FILE: `<code>.json` exists plus a LANG_* block
    exists -> the language is offered. A pack translated to 40% would have passed, and the customer
    would have received a deck in two languages at once, because an unknown string falls through to
    English by design and that fall-through is silent. Presence is not completeness (defect
    class 1: the check could not see its own subject).

    These tests pin the completeness gate AND the Portuguese pack that is the first thing to go
    through it.

PROVED BY MUTATION, not by passing. Each assertion was checked by breaking what it guards:
    * a pack with 60% of the keys                   -> test_partial_pack_is_refused FAILS without the gate
    * a pack whose values all equal their keys      -> test_stub_pack_is_refused FAILS without the gate
    * PACK_COVERAGE_MIN lowered to 0.0              -> test_partial_pack_is_refused FAILS
    * PACK_IDENTICAL_MAX raised to 1.0              -> test_stub_pack_is_refused FAILS
    * reference_keys() without the exclude argument -> test_a_pack_is_not_graded_against_itself FAILS
    * "pt" removed from enrich.LANG_BLOCKS          -> test_portuguese_is_offered FAILS
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import deck_langs                              # noqa: E402
import enrich                                  # noqa: E402

REF = os.path.join(HERE, "i18n", "de.json")


def _ref_strings():
    with open(REF, encoding="utf-8") as fh:
        return json.load(fh)["strings"]


def _write_pack(d, code, strings):
    with open(os.path.join(d, code + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"locale": code, "strings": strings}, fh, ensure_ascii=False)


@pytest.fixture
def fake_i18n(tmp_path, monkeypatch):
    """A scratch i18n dir carrying a real reference pack, so the denominator is honest."""
    monkeypatch.setattr(deck_langs, "I18N_DIR", str(tmp_path))
    deck_langs._CACHE.clear()
    _write_pack(str(tmp_path), "de", _ref_strings())       # the reference, always complete
    return str(tmp_path)


# --------------------------------------------------------------- the real packs on disk

def test_portuguese_is_offered():
    """The shipping check: pt must be a document language, end to end."""
    assert "pt" in deck_langs.doc_langs(), deck_langs.pack_report("pt")
    r = deck_langs.pack_report("pt")
    assert r["ok"], r["why"]
    assert r["coverage"] == 1.0, "pt covers %.1f%% of the reference" % (100 * r["coverage"])


def test_the_languages_that_already_shipped_still_ship():
    """A new gate must not evict German or Russian. This is the regression that would hurt most."""
    langs = deck_langs.doc_langs()
    for c in ("en", "de", "ru"):
        assert c in langs, "%s was dropped by the completeness gate: %s" % (c, deck_langs.pack_report(c))


def test_portuguese_has_a_prose_block_and_it_forbids_brazilian_forms():
    """A dictionary translates chrome; only the prompt block reaches the per-company prose."""
    blk = enrich.lang_block("pt")
    assert blk, "no LANG_PT prompt block: the deck chrome would wrap English paragraphs"
    low = blk.lower()
    assert "ficheiro" in low and "utilizador" in low, (
        "LANG_PT no longer pins European forms. A model left to itself writes Brazilian "
        "Portuguese, and an Angolan or Portuguese CISO reads that as a deck for somebody else.")


def test_portuguese_pack_shape():
    with open(os.path.join(HERE, "i18n", "pt.json"), encoding="utf-8") as fh:
        pt = json.load(fh)
    with open(REF, encoding="utf-8") as fh:
        de = json.load(fh)
    assert pt["locale"] == "pt-PT"
    assert set(pt["strings"]) == set(de["strings"]), "pt key set has drifted from the reference"
    assert len(pt["patterns"]) == len(de["patterns"])
    for i, (rx, _rep) in enumerate(pt["patterns"]):
        assert rx == de["patterns"][i][0], (
            "pattern %d: the regex half matches the ENGLISH source and must be byte-identical "
            "across packs; only the replacement is translated" % i)
    assert set(pt["counts"]["hosts"]) >= {"one", "other"}, "the pack must declare its own plurals"


def test_portuguese_preserves_placeholders():
    """A dropped %d or $1 renders a literal hole on a customer slide."""
    with open(os.path.join(HERE, "i18n", "pt.json"), encoding="utf-8") as fh:
        pt = json.load(fh)
    bad = []
    for k, v in pt["strings"].items():
        for p in ("%d", "%s"):
            if k.count(p) != v.count(p):
                bad.append((k[:40], p))
    assert not bad, bad
    for rx, rep in pt["patterns"]:
        for g in range(1, 7):
            if ("$%d" % g) in rep:
                assert rx.count("(") >= g, "pattern %r references $%d with too few groups" % (rx[:40], g)


def test_no_german_statute_name_survived_into_portuguese():
    """DSGVO is the German name. A Portuguese deck says RGPD, and this came back from review."""
    with open(os.path.join(HERE, "i18n", "pt.json"), encoding="utf-8") as fh:
        pt = json.load(fh)
    hits = [k[:50] for k, v in pt["strings"].items() if "DSGVO" in v]
    assert not hits, hits


# --------------------------------------------------------------- the gate itself

def test_partial_pack_is_refused(fake_i18n):
    ref = _ref_strings()
    half = {k: "xx " + k for k in list(ref)[:int(len(ref) * 0.6)]}
    _write_pack(fake_i18n, "zz", half)
    deck_langs._CACHE.clear()
    r = deck_langs.pack_report("zz")
    assert not r["ok"]
    assert "below the" in r["why"] and "missing keys" in r["why"], r["why"]


def test_stub_pack_is_refused(fake_i18n):
    """100% coverage, 0% translation. Coverage alone would score this a pass."""
    ref = _ref_strings()
    _write_pack(fake_i18n, "zz", {k: k for k in ref})
    deck_langs._CACHE.clear()
    r = deck_langs.pack_report("zz")
    assert r["coverage"] == 1.0, "the stub must pass coverage, or this proves the wrong thing"
    assert not r["ok"]
    assert "stub" in r["why"], r["why"]


def test_a_pack_is_not_graded_against_itself(fake_i18n):
    """A denominator produced by the thing under test is not a measurement (class 3)."""
    _write_pack(fake_i18n, "zz", {"only one string": "uma string"})
    deck_langs._CACHE.clear()
    assert len(deck_langs.reference_keys(exclude="zz")) == len(_ref_strings())
    r = deck_langs.pack_report("zz")
    assert not r["ok"] and r["ref"] > 1, (
        "a one-string pack scored itself against itself: ref=%d" % r["ref"])


def test_no_reference_is_reported_as_unknown_not_as_a_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(deck_langs, "I18N_DIR", str(tmp_path))
    deck_langs._CACHE.clear()
    _write_pack(str(tmp_path), "zz", {"a": "b"})
    r = deck_langs.pack_report("zz")
    assert not r["ok"] and "no reference pack" in r["why"], r["why"]


def test_report_states_the_numbers_not_just_a_verdict(fake_i18n):
    """Print the comparison you made (class 5)."""
    _write_pack(fake_i18n, "zz", {k: "x" for k in list(_ref_strings())[:10]})
    deck_langs._CACHE.clear()
    r = deck_langs.pack_report("zz")
    for field in ("keys", "ref", "coverage", "identical", "prose_block", "why"):
        assert field in r
    assert r["ref"] > 0 and "%" in r["why"]


def test_cache_follows_the_file(fake_i18n):
    """doc_langs() is on an HTTP path, so it caches. A cache that goes stale is a wrong answer."""
    p = os.path.join(fake_i18n, "zz.json")
    _write_pack(fake_i18n, "zz", {"a": "b"})
    deck_langs._CACHE.clear()
    assert len(deck_langs._strings(p)) == 1
    _write_pack(fake_i18n, "zz", {"a": "b", "c": "d", "e": "f"})
    os.utime(p, (0, 0))                        # force a different mtime, not merely a different size
    assert len(deck_langs._strings(p)) == 3, "the cache did not notice the file changing"
