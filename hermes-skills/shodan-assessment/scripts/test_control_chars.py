#!/usr/bin/env python3
"""test_control_chars.py - corrupt model output must never reach a customer artifact.

THE INCIDENT (verint, Portuguese, 2026-11-03)
    The animated GEOPOL report went to the operator with "administra\\x7f\\x103o" where
    "administração" belonged, and 57 control characters across one page: ç -> \\x7f, ã -> \\x10,
    í and é -> \\x11, á -> \\x1f, õ -> \\x15.

    It was NOT an encoding bug, and the elimination matters because "it's a charset problem" is
    where the next person will start:
      * the file decoded as valid UTF-8 and carried <meta charset="utf-8">;
      * "Múltiplas" in the SAME SENTENCE was intact, so nothing global happened to the document;
      * an exhaustive search over every encode/decode pair in Python's codec set reproduces the
        mapping with NONE of them;
      * and the same letter mapped two different ways in two places (é -> "\\x116" in "também",
        é -> "\\x11b" three words later), so there is no transform to invert.
    The model emitted corrupt bytes. Every layer downstream passed them on, because escaping HTML
    and translating chrome are different questions from "is this text".

TWO CONTROLS, AND THEY ARE NOT THE SAME CONTROL
    1. enrich._contract_ok() REFUSES the answer, so the chain fails over to the next model. This is
       the real fix: corruption that ate a cedilla ate letters too, so there is nothing to repair.
    2. i18n/safe_text.js strips at the artifact boundary. This is the floor, and it exists for text
       that never went through a model: Shodan banners, PTR names, certificate subjects.
    A test for one is not a test for the other, so both are below.

PROVED BY MUTATION
    * _CTRL_RE emptied                         -> test_contract_refuses_control_chars FAILS
    * the ctl check deleted from _contract_ok  -> test_contract_refuses_control_chars FAILS
    * \\t\\n\\r added to _CTRL_RE               -> test_ordinary_whitespace_is_not_a_control FAILS
    * stripControls removed from esc()         -> test_html_builder_cannot_emit_controls FAILS
    * stripControls moved below the LANG==="en" early return -> test_t_strips_for_english FAILS
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import enrich                                   # noqa: E402

# The real bytes, lifted from the delivered file rather than invented.
VERINT = "Múltiplas portas de administra\x7f\x103o expostas na infraestrutura IP."
NODE = os.path.join(HERE, "..", "node_modules")


def _node(script):
    env = dict(os.environ, NODE_PATH=os.path.abspath(NODE))
    return subprocess.run([ "node", "-e", script], cwd=HERE, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)


# --------------------------------------------------------------- detection

def test_the_fixture_really_is_corrupt():
    """Prove the fixture before trusting any test that uses it (class 12)."""
    assert enrich.control_chars(VERINT), "the fixture carries no control character; it proves nothing"
    assert "ú" in VERINT, "the intact 'ú' is part of the evidence and must stay in the fixture"


def test_control_chars_reports_path_and_context():
    """A diagnostic that does not NAME its subject sends the next investigation elsewhere."""
    hits = enrich.control_chars({"findings": [{"why": VERINT}]})
    assert hits, "nothing found in a nested structure"
    path, cp, ctx = hits[0]
    assert path == "findings[0].why", path
    assert cp == 0x7F, hex(cp)
    assert "administra" in ctx, ctx


def test_ordinary_whitespace_is_not_a_control():
    """Tab, newline and carriage return are text. Flagging them would fail every real answer."""
    assert not enrich.control_chars("line one\nline two\tcolumn\r\n")


def test_clean_portuguese_passes():
    """The happy path. A guard that also refuses correct Portuguese is worse than no guard."""
    assert not enrich.control_chars(
        "Múltiplas portas de administração expostas na infraestrutura IP. "
        "A constatação crítica é um ponto de entrada; também há painéis de gestão.")


# --------------------------------------------------------------- control 1: the chain refuses

def test_contract_refuses_control_chars():
    ok, why = enrich._contract_ok({"exec_summary": VERINT}, tokens_out=900)
    assert not ok, "a corrupt answer passed the contract and would have been shipped"
    assert "control character" in why and "U+007F" in why, why
    assert "administra" in why, "the diagnostic must quote the evidence, not just count it"


def test_contract_still_accepts_a_good_answer():
    ok, why = enrich._contract_ok(
        {"exec_summary": "A constatação crítica é um ponto de entrada em equipamento de perímetro."},
        tokens_out=900)
    assert ok, why


def test_contract_refusal_is_a_failover_not_a_crash():
    """The refusal must return the same shape as every other refusal, so the chain moves on."""
    r = enrich._contract_ok({"exec_summary": VERINT}, tokens_out=900)
    assert isinstance(r, tuple) and len(r) == 2 and r[0] is False and isinstance(r[1], str)


def test_strip_controls_does_not_pretend_to_repair():
    """It removes, it does not invent. 'administrao' is still wrong and must stay visibly wrong."""
    out = enrich.strip_controls(VERINT)
    assert not enrich.control_chars(out)
    assert "administra3o" in out, out
    assert "administração" not in out, "strip_controls must never fabricate the missing letters"


# --------------------------------------------------------------- control 2: the artifact floor

@pytest.mark.skipif(not os.path.isdir(NODE), reason="node_modules not present in this checkout")
def test_js_strip_and_count():
    r = _node('const s=require("./i18n/safe_text");'
              'const v="a\\u007fb\\u0010c\\td";'
              'console.log(JSON.stringify([s.stripControls(v), s.countControls(v)]));')
    assert r.returncode == 0, r.stderr
    out, n = json.loads(r.stdout.strip())
    assert out == "abc\td", repr(out)
    assert n == 2


@pytest.mark.skipif(not os.path.isdir(NODE), reason="node_modules not present in this checkout")
def test_t_strips_for_english():
    """THE EARLY-RETURN TRAP. T() returns immediately when LANG==='en'; a strip placed after that
    line protects five languages and not the sixth, and English is the default."""
    r = _node('process.env.DECK_LANG="en";'
              'const d=require("./i18n/deck_i18n");'
              'console.log(JSON.stringify(d.T("administra\\u007f\\u00103o")));')
    assert r.returncode == 0, r.stderr
    assert "\x7f" not in json.loads(r.stdout.strip()), "English decks skip the strip"


@pytest.mark.skipif(not os.path.isdir(NODE), reason="node_modules not present in this checkout")
@pytest.mark.parametrize("lang", ["en", "pt", "de"])
def test_html_builder_cannot_emit_controls(tmp_path, lang):
    """End to end, against the real builder, in every document language."""
    # POISON A FIELD THE BUILDER ACTUALLY RENDERS, IN THE SHAPE IT ACTUALLY READS.
    #
    # Two false starts, both of which left this test unable to fail (class 3, found by mutation):
    #   1. poisoning "any string over 25 characters" hit fields the page never prints;
    #   2. feeding it sample/geopol.sample.json, which is the content model for the PPTX geopol
    #      DECK, not for this builder — build_geopol_html.js reads C.company / C.title / C.sceneN,
    #      found none of them, rendered its own defaults, and happily produced 35 KB of clean HTML
    #      that had nothing to do with the input. Removing stripControls from esc() kept it GREEN.
    # The builder's own header documents the shape; this fixture follows it.
    MARK = "ZQX"                                  # survives escaping, cannot occur naturally
    data = {
        "company": "Example AG",
        "title": MARK + " GEOPOL",
        "scene1": {"eyebrow": "Scene 01 · The exposed estate",
                   "h1": MARK + " " + VERINT,
                   "sub": MARK + " " + VERINT,
                   "stats": [{"n": "8", "l": MARK + " " + VERINT}],
                   "caption": MARK + " " + VERINT},
        "scene2": {"h1": MARK + " " + VERINT, "sub": MARK + " " + VERINT},
    }
    src2 = tmp_path / "poisoned.json"
    src2.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert enrich.control_chars(json.loads(src2.read_text(encoding="utf-8"))), \
        "the poisoned input carries no control character; the fixture proves nothing"

    out = tmp_path / ("report_%s.html" % lang)
    env = dict(os.environ, NODE_PATH=os.path.abspath(NODE), DECK_LANG=lang)
    r = subprocess.run(["node", os.path.join(HERE, "build_geopol_html.js"), str(src2), str(out)],
                       cwd=HERE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    html = out.read_text(encoding="utf-8")

    # PROVE THE POISON TRAVELLED. Without this the test passes when the builder silently drops the
    # field, which is the exact way it was passing before.
    assert MARK in html, ("the poisoned field never reached the page, so this asserts nothing "
                          "about the strip; poison a field the builder renders")
    bad = enrich.control_chars(html)
    assert not bad, "%d control character(s) reached the HTML, first %r" % (len(bad), bad[:1])
