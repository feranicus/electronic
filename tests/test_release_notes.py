"""test_release_notes.py — the release notes must actually be written AND actually be sent.

STANDING RULE (operator, 9 Aug 2026): every release, the same four panel models write the notes,
and they go to feranicus@s4biz.io through the Gmail API gateway and to Telegram.

This exists because the rule is worthless if it lives only in prose. The recurring failure in this
repo is not a check that reports the wrong answer; it is a check that quietly stops running —
the ruff gate that skipped for weeks, the model probe that could not see its own key, the roster
check that was always SKIP. So: assert the wiring, not the intention.
"""
import ast
import importlib.util as ilu
import os
import re
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIP = os.path.join(ROOT, "ship.py")
LOCAL = os.path.join(ROOT, "release_notes.py")
REMOTE = os.path.join(ROOT, "webapp", "backend", "app", "release_notes.py")


def _read(p):
    return open(p, encoding="utf-8").read()


def _rn():
    sys.modules.setdefault("app", types.ModuleType("app"))
    spec = ilu.spec_from_file_location("rn_under_test", REMOTE)
    m = ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_same_four_models_that_review_the_gate_write_the_notes():
    """Four vendors, so a provider-wide 429 cannot silence the whole panel."""
    q = _read(os.path.join(ROOT, "deploy", "stagegate", "quorum.py"))
    # CASE-SENSITIVE was wrong: `gemma-4-31B-it` has a capital B, so [a-z0-9.-]+ matched nothing
    # for it and the panel silently came back as three models. A model id is not lowercase by
    # convention, and assuming it is made this check quietly measure the wrong set.
    panel = set(re.findall(r'"([A-Za-z0-9.\-]+)"', "".join(
        re.findall(r"^(?:SOLDIERS|AUDITORS)\s*=\s*\[[^\]]*\]", q, re.M))))
    assert len(panel) == 4, (
        "expected 4 panel models, read %d from quorum.py: %s. If the panel legitimately changed "
        "size, the release notes must change with it." % (len(panel), sorted(panel)))
    assert set(_rn().MODELS) == panel, (
        "the release notes are written by a different set of models than the staging panel: "
        "%s vs %s. One list, or they drift." % (sorted(_rn().MODELS), sorted(panel)))


def test_ship_py_sends_them_on_every_release():
    """A rule that lives only in CLAUDE.md is a rule that stops happening."""
    s = _read(SHIP)
    assert "release_notes.py" in s, (
        "ship.py no longer sends the release notes. Every release must produce them.")
    # It must run AFTER the safe-point tag: notes that name a tag which does not exist are wrong,
    # and notes for a deploy that never verified are worse than none.
    # ANCHOR ON THE CALL SITE, NOT THE NAME. `s.index("tag_known_good()")` matches the DEFINITION
    # (`def tag_known_good():` contains that substring), which is always near the top of the file,
    # so the comparison was true no matter where the notes ran. A check that cannot fail is not a
    # check -- the same defect this file exists to prevent.
    assert s.index("_tag = tag_known_good()") < s.index("release_notes.py"), (
        "release notes are generated BEFORE the safe-point is tagged, so they would name a tag "
        "that does not exist yet")
    # And it must not be able to fail the ship.
    tail = s[s.index("release_notes.py"):s.index("release_notes.py") + 1400]
    assert "except Exception" in tail, (
        "the release-notes step is not wrapped: a rate-limited model or a mail outage would turn "
        "a verified release into a failed one")


def test_both_channels_are_used_and_they_are_independent():
    src = _read(REMOTE)
    assert "notify.telegram(" in src and "notify.email(" in src, (
        "the notes must go to BOTH the Gmail API gateway and Telegram")
    # Called separately on purpose: notify.both() would be fine, but the point is that one
    # channel failing must not silence the other, so they are dispatched independently.
    t = src.index("notify.telegram(")
    e = src.index("notify.email(")
    assert abs(t - e) < 400, "the two channels drifted apart in the code"
    # SMTP is BLOCKED outbound on this droplet. Anyone "fixing" the mail path to SMTP breaks it.
    assert "smtplib" not in src, (
        "SMTP is blocked outbound on this host — mail must go through the Gmail API in notify.py")


def test_the_notes_are_correct_even_when_every_model_fails():
    """The deterministic facts ARE the release notes; the models add prose on top.

    Same doctrine as the deck: enrichment failing must degrade the prose, never the facts.
    """
    rn = _rn()
    facts = {"commit": "abc1234", "tag": "good-20260809-1300", "message": "a real change",
             "staging": "GO", "tests": "56 passed",
             "commits": ["abc1234 a real change"], "files": ["M\tship.py"], "files_total": 1}
    body = rn.compose(facts, [{"model": m, "error": "HTTP 429"} for m in rn.MODELS])
    assert "0 of 4 models" in body, "the notes must say how many models actually answered"
    for must in ("abc1234", "good-20260809-1300", "a real change", "GO", "56 passed", "ship.py"):
        assert must in body, "a deterministic fact (%s) vanished when the models failed" % must


def test_it_is_a_building_block_not_a_second_command():
    """Operating principle 7: the operator runs ONE command, `python ship.py`."""
    src = _read(LOCAL)
    assert "BUILDING BLOCK" in src, (
        "release_notes.py must document that ship.py calls it and the operator does not")
    # The facts gatherer must be pure: it may read git, but it must not need the droplet to
    # produce them, or `--facts-only` could never be used to debug a delivery failure.
    tree = ast.parse(src)
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert {"gather", "send"} <= names, "gather() and send() must stay separable"
