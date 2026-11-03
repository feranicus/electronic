#!/usr/bin/env python3
"""test_model_prices.py - the DO price table and the chain-refusal list must not go stale silently.

WHY THIS FILE EXISTS
    model_watch.PRICES was verified on 1 Jul 2026 and re-read on 2 Nov 2026. In those four months
    EIGHT of its fifteen rows had become false and TWO of its ids had been retired outright, and
    nothing anywhere said so, because the only consumer was a human reading a column in a deploy
    log. That is defect class 1 in its purest form: a check that cannot see its own subject.

    A date in a comment is not a guard. These tests make the date load-bearing.

WHAT IT ASSERTS
    1. The verification date is parseable, not in the future, and not older than the stated budget.
    2. Every model in the live chain (enrich.MODELS) has a price. A chain model priced "?" means
       the cost ledger is guessing about the thing we actually spend money on.
    3. enrich.not_chainable() refuses every family we have MEASURED as contract-breaking, and in
       particular refuses DigitalOcean's own recommended successor glm-5.3-flash, which the
       name-shaped THINKING_RE does not catch. This is the regression that would have let a
       reasoning model into the chain on a vendor's recommendation.
    4. It does NOT refuse the open-weights gpt-oss ids, which are a different thing from the
       commercial openai-gpt-* ids that return 403. A refusal list that over-matches silently
       removes candidates we may need.

PROVED BY MUTATION, not by passing
    Each assertion below was checked by breaking the thing it guards:
      * PRICES_VERIFIED set to 2026-01-01          -> test_prices_are_fresh FAILS
      * "glm-5" removed from enrich.NOT_CHAINED     -> test_refuses_measured_bad FAILS
      * not_chainable's gpt-oss carve-out removed   -> test_does_not_overmatch FAILS
      * a chain id deleted from PRICES              -> test_every_chain_model_is_priced FAILS
"""
import datetime
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import enrich                      # noqa: E402
import model_watch                 # noqa: E402


def test_prices_are_fresh():
    """The table's own verification date must be real, past, and inside the budget."""
    d = datetime.date.fromisoformat(model_watch.PRICES_VERIFIED)
    today = datetime.date.today()
    assert d <= today, "PRICES_VERIFIED is in the future: %s" % d
    age = (today - d).days
    assert age <= model_watch.PRICES_MAX_AGE_DAYS, (
        "model_watch.PRICES was last verified %s, %d days ago (budget %d). Re-read "
        "docs.digitalocean.com's Inference Pricing page, correct every row, and move the date. "
        "Eight of fifteen rows were wrong the last time this went unchecked."
        % (model_watch.PRICES_VERIFIED, age, model_watch.PRICES_MAX_AGE_DAYS))


def test_every_chain_model_is_priced():
    """A model we actually spend money on must not report its price as '?'."""
    missing = [m for m in enrich.MODELS if m not in model_watch.PRICES]
    assert not missing, (
        "chained but unpriced: %s. The cost ledger cannot cost what it cannot price."
        % ", ".join(missing))


@pytest.mark.parametrize("mid", [
    "glm-5.3-flash",      # DO's own recommended successor to gemma-4-31B-it
    "glm-5.3",
    "glm-5.2",
    "kimi-k3",
    "minimax-m3.1-flash",
    "qwen3.5-397b-a17b",
    "mimo-v2.5-pro",
    "anthropic-claude-sonnet-4.5",
])
def test_refuses_measured_bad(mid):
    """Every family measured as 200-but-JSON-invalid, or known 403, must be refused."""
    why = enrich.not_chainable(mid)
    assert why, "%s was NOT refused; it would be probed as a chain candidate" % mid


def test_the_regex_alone_would_have_missed_the_recommended_successor():
    """THE REGRESSION, pinned.

    This is the whole reason enrich.NOT_CHAINED exists as data. If somebody later decides the
    regex is sufficient and deletes the measured list, this test says what that costs.
    """
    assert not model_watch.THINKING_RE.search("glm-5.3-flash"), (
        "THINKING_RE now catches glm-5.3-flash. If that is deliberate, keep it AND keep "
        "NOT_CHAINED: the measured list covers ids whose names say nothing.")
    assert enrich.not_chainable("glm-5.3-flash"), "the measured list no longer covers it either"
    assert model_watch._refuse("glm-5.3-flash"), "model_watch would probe it"


@pytest.mark.parametrize("mid", [
    "openai-gpt-oss-120b",
    "openai-gpt-oss-20b",
    "mistral-3-14B",
    "deepseek-3.2",
    "nemotron-3-ultra-550b",
    "reflection-beam",
])
def test_does_not_overmatch(mid):
    """Candidates we may need must not be barred by a substring that was aimed at something else."""
    assert not enrich.not_chainable(mid), (
        "%s is refused, but nothing has been measured against it. An over-wide refusal list "
        "removes candidates silently, which is the same failure as an over-narrow one." % mid)


def test_commercial_openai_ids_are_still_barred():
    """The gpt-oss carve-out must not have opened the 403 door it was cut beside."""
    assert enrich.not_chainable("openai-gpt-5.2"), "commercial openai-gpt-* must stay barred (403)"


def test_refuse_is_the_one_home():
    """model_watch must ask enrich, not keep a second copy of the measured list."""
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "E.not_chainable" in src or "enrich.not_chainable" in src, (
        "model_watch._refuse no longer consults enrich.not_chainable: the measured list has "
        "grown a second home and the two will drift.")
