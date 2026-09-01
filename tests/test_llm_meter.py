"""The AI spend meter and the daily cap.

THE INCIDENT (2026-09-01): DigitalOcean auto-recharged $5 three times in under two days while
`cost_report.py` reported a lifetime spend under a dollar. Neither number was dishonest. The
report was blind, because `cost_ledger.record()` is called from exactly one caller and nine others
spent money invisibly, four of them on timers nobody watches.

These tests pin the three properties that make that impossible to repeat:
  1. cost is priced PER DIRECTION, because no provider charges input and output the same;
  2. every call is counted at the ONE chokepoint, tagged with WHO made it;
  3. the day has a ceiling that is checked BEFORE the request, and it fails open on a storage
     fault but closed on the budget.
"""
import importlib
import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts")


@pytest.fixture()
def mod():
    """A fresh meter on a throwaway database.

    The module-level breaker and the day's warning flag are process state, so they are reset
    explicitly: reloading is not enough for `enrich`, which holds its own reference.
    """
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    db = os.path.join(tempfile.mkdtemp(prefix="meter-"), "m.sqlite")
    os.environ["LLM_METER_DB"] = db
    os.environ.setdefault("OPENAI_API_KEY", "x")
    import llm_meter
    importlib.reload(llm_meter)
    import enrich
    importlib.reload(enrich)
    llm_meter.DB_PATH = db
    llm_meter._broken[0] = False
    llm_meter._warned[0] = ""
    enrich.__dict__["llm_meter"] = llm_meter
    return enrich, llm_meter


# ------------------------------------------------------------------ pricing
def test_input_and_output_are_priced_separately(mod):
    """THE ARITHMETIC THAT MADE THE OLD NUMBER UNRECONCILABLE.

    The ledger used `(tokens_in + tokens_out) * 0.80 / 1e6`: one flat rate in both directions.
    DeepSeek 3.2 is $0.425 in and $1.36 out, a factor of 3.2 apart, and our workload is
    output-heavy by contract (~1.5k tokens of prose per finding).
    """
    E, _ = mod
    ri, ro = E.rate_for("deepseek-3.2")
    assert ro > ri * 2, "output must cost materially more than input, or this is the old flat rate"
    real = E.cost_of("deepseek-3.2", 3500, 8000)
    flat = (3500 + 8000) / 1e6 * 0.80
    assert real > flat, "the corrected arithmetic must not UNDERstate an output-heavy call"
    assert 0.010 < real < 0.015, "a full enrichment should be about a cent and a bit, got %.4f" % real


def test_an_unknown_model_is_priced_pessimistically(mod):
    """An unknown model must never look cheap, or the budget is a budget for an invented number.
    DO adds models continuously; model_watch exists precisely because the catalogue moves."""
    E, _ = mod
    unknown = E.cost_of("some-model-shipped-next-week", 3500, 8000)
    cheapest = min(E.cost_of(m, 3500, 8000) for m in E.RATES)
    assert unknown >= cheapest, "an unpriced model must not be the cheapest thing in the table"


def test_zero_tokens_cost_nothing(mod):
    E, _ = mod
    assert E.cost_of("deepseek-3.2", 0, 0) == 0.0


# ------------------------------------------------------------------ metering
def test_every_call_is_attributed_to_a_caller(mod):
    """WHO, not just how much. The question that could not be answered on 2026-09-01 was which
    part of the system was spending, and no data existed to answer it."""
    E, LM = mod
    for caller, tin, tout in (("shield_panel", 4000, 900), ("assistant", 2000, 1500),
                              ("run_assessment", 3500, 8000)):
        os.environ["LLM_CALLER"] = caller
        E._meter("deepseek-3.2", {"prompt_tokens": tin, "completion_tokens": tout})
    r = LM.report()
    seen = {c["caller"]: c for c in r["per_caller"]}
    assert set(seen) == {"shield_panel", "assistant", "run_assessment"}
    assert seen["run_assessment"]["usd"] > seen["shield_panel"]["usd"]
    assert sum(c["calls"] for c in r["per_caller"]) == 3


def test_the_caller_is_inferred_when_nobody_passes_one(mod):
    """Threading a caller argument through nine call sites is nine chances to forget one, and the
    ones that forget are exactly the unattended timers. So it is inferred from the process."""
    E, LM = mod
    os.environ.pop("LLM_CALLER", None)
    assert E._caller(), "there must always be SOME attribution, never an empty string"
    E._meter("deepseek-3.2", {"prompt_tokens": 10, "completion_tokens": 10})
    assert LM.report()["per_caller"], "an unattributed call must still be counted"


# ------------------------------------------------------------------ the cap
def test_the_cap_refuses_before_the_request_is_sent(mod):
    """Counting afterwards produces a better post-mortem and exactly the same bill."""
    E, LM = mod
    os.environ["LLM_CALLER"] = "run_assessment"
    LM.DAILY_USD = 0.005                    # below the ~$0.012 a single real enrichment costs
    E._meter("deepseek-3.2", {"prompt_tokens": 3500, "completion_tokens": 8000})
    assert LM.spent_today() > LM.DAILY_USD, "fixture: the day must really be over budget"
    with pytest.raises(E.BudgetExceeded):
        E._call("this must never reach the network")


def test_the_budget_stop_is_its_own_exception_type(mod):
    """It must be distinguishable from a model failure: no other model and no retry can fix it,
    so the chain must not treat it as a reason to try three more models."""
    E, _ = mod
    assert not E._retryable(E.BudgetExceeded("x")), \
        "a budget stop must never be retried - that would be four refusals instead of one"


def test_a_broken_meter_fails_OPEN(mod):
    """A defensive counter that raises takes the product down to protect it, which is a worse
    outcome than the spend it was watching."""
    E, LM = mod
    LM._broken[0] = True
    ok, why = LM.allow()
    assert ok is True and "OPEN" in why
    assert LM.spent_today() is None, "unknown must stay distinguishable from zero"


def test_a_readable_meter_over_budget_fails_CLOSED(mod):
    """The other half of the same rule. Failing open when the meter WORKS is not a budget."""
    E, LM = mod
    LM._broken[0] = False
    LM.DAILY_USD = 0.001
    os.environ["LLM_CALLER"] = "assistant"
    E._meter("deepseek-3.2", {"prompt_tokens": 1000, "completion_tokens": 1000})
    ok, why = LM.allow()
    assert ok is False and "budget" in why.lower()


def test_unknown_and_zero_are_not_the_same_thing(mod):
    """Collapsing them is how a broken meter silently becomes an unlimited budget."""
    _, LM = mod
    LM._broken[0] = False
    assert LM.spent_today() == 0.0, "a quiet day is zero and the cap still applies"
    LM._broken[0] = True
    assert LM.spent_today() is None, "an unreadable meter is None, not zero"


def test_the_warning_fires_once_a_day_not_once_a_call(mod):
    """An alert per call during a busy hour is an outage of the operator's attention."""
    _, LM = mod
    LM.DAILY_USD, LM._warned[0] = 1.0, ""
    assert LM.should_warn(0.9) is True
    assert LM.should_warn(0.95) is False, "the second crossing must be silent"
    assert LM.should_warn(None) is False, "an unknown total must never raise an alarm"


# ------------------------------------------------------------------ wiring
def test_the_meter_is_wired_into_the_one_function_every_caller_uses(mod):
    """BEHAVIOUR IS TESTED ABOVE; THIS ASSERTS IT IS REACHABLE.

    A control that is correct and unreachable is not a control. shield.py's tests proved the
    detector worked for weeks while nothing asserted the middleware invoked it.
    """
    src = open(os.path.join(SCRIPTS, "enrich.py"), encoding="utf-8").read()
    i = src.index("def _call(")
    body = src[i:src.index("\ndef ", i + 10)]
    assert "llm_meter" in body and "allow()" in body, \
        "_call must consult the budget, or the cap is decoration"
    assert body.index("allow()") < body.index("_post(payload"), \
        "the budget must be checked BEFORE the request is sent, not after"
    assert "_meter(" in src[src.index("def _call("):], "the call must be recorded"


def test_no_caller_reaches_the_inference_endpoint_around_the_meter(mod):
    """enrich._post() is the raw HTTP layer under _call. Anything reaching it from outside would
    spend money the meter cannot see, which is the exact defect being fixed.

    MY FIRST VERSION OF THIS CHECK WAS AIMED AT THE WRONG SUBJECT and named two innocent files.
    It matched any function called `_post`, so `asn_sources.py` was flagged for posting to RIPE
    and CAIDA, which have nothing to do with inference and cost nothing. A check that cannot tell
    its subject from a same-named neighbour produces exactly the sort of false alarm that gets a
    gate switched off. It now matches only enrich's own `_post`, reached through an import.
    """
    import re
    offenders = []
    for name in sorted(os.listdir(SCRIPTS)):
        if not name.endswith(".py") or name in ("enrich.py", "llm_meter.py"):
            continue
        src = open(os.path.join(SCRIPTS, name), encoding="utf-8").read()
        src = re.sub(r"#.*", "", src)          # comments discuss _post legitimately
        if re.search(r"\b(?:E|enrich)\s*\.\s*_post\s*\(", src):
            offenders.append(name)
    assert not offenders, ("these reach the endpoint around _call: %s" % offenders)


def test_the_operator_diagnostics_that_spend_are_named_and_deliberate(mod):
    """model_probe.py has its OWN _post and calls the real endpoint on `--all`.

    It is not wired through the meter and that is a decision, not an oversight: it is invoked by
    hand, it prints what it measured, and routing it through the daily cap would let a diagnostic
    run lock out production for the rest of the day. What matters is that it stays the ONLY such
    file, so this test fails if a second unmetered spender appears beside it.
    """
    import re
    spenders = []
    for name in sorted(os.listdir(SCRIPTS)):
        if not name.endswith(".py") or name in ("enrich.py", "llm_meter.py"):
            continue
        src = re.sub(r"#.*", "", open(os.path.join(SCRIPTS, name), encoding="utf-8").read())
        if "chat/completions" in src:
            spenders.append(name)
    assert spenders == ["model_probe.py"], \
        ("a new file talks to the inference endpoint directly. Route it through enrich._call so "
         "it is metered and capped, or add it here with a reason: %s" % spenders)


# ------------------------------------------------------------------ the trace helper
def test_the_remote_trace_unpacks_ssh_script_correctly(mod, monkeypatch):
    """`recover.ssh_script` returns (stdout, stderr, returncode), NOT a string.

    THE DEFECT THIS PINS, which shipped and failed on the operator's first run:
        [!] production: 'tuple' object has no attribute 'splitlines'
    I assumed a bare string and then "defended" the guess with `isinstance(out, str)`. That is not
    a defence: a tuple is truthy, so it sailed past the guard into sections() and died there.
    Guessing a helper's contract and writing a guard around the guess is worse than reading the
    helper -- this is the same family as calling .returncode on ship.py's run() (an int) and
    destructuring {ok, data} from a getJSON-backed call.
    """
    import cost_report as C
    calls = {}

    def fake(script, timeout=None):
        calls["script"] = script
        return ("#### CONTAINERS\ncolt-web|img|Up 2h|\n#### KEYS\ncolt-web|K|sha256:aa|len=7\n",
                "", 0)

    monkeypatch.setattr(C, "ssh_script", fake, raising=False)
    import recover
    monkeypatch.setattr(recover, "ssh_script", fake)
    d = C.trace_remote("198.51.100.1", "test")
    assert "error" not in d, d
    assert "colt-web" in d.get("CONTAINERS", ""), "sections() must receive stdout, not the tuple"
    assert "deepseek-v4-pro" in calls["script"], "the model pattern must reach the remote script"


def test_a_failed_ssh_is_reported_not_swallowed(mod, monkeypatch):
    """A non-zero rc with no output must say so. Returning an empty section map would render as
    'no data' and read like a clean box, which is the logship defect one level over."""
    import cost_report as C
    import recover
    monkeypatch.setattr(recover, "ssh_script", lambda s, timeout=None: ("", "permission denied", 255))
    d = C.trace_remote("198.51.100.1", "test")
    assert "error" in d and "255" in d["error"]
