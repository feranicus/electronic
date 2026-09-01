"""jobhuntwow must be able to prove what it spent.

THE GAP THIS CLOSES. When the shared DigitalOcean model key produced a spend spike on 2026-09-01,
Loki could answer for cybergod (its engine emits `evt=qwen` per call with the model and both token
counts) and could not answer for jobhuntwow, which emitted no model event at all:

    electronic.py:104   txt, _usage, _fin = await RC.call_model(...)      <- usage discarded
    llm.py::complete    return data["choices"][0]["message"]["content"]   <- usage never read

So jhw showed HTTP and security events beside a silence that reads exactly like a quiet project.
It could be neither blamed nor cleared, which is the worst of both.
"""
import ast
import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JHW = os.path.join(ROOT, "jobhuntwow-app", "backend", "app")
if not os.path.isdir(JHW):
    pytest.skip("jobhuntwow-app is not checked out beside this repo", allow_module_level=True)
sys.path.insert(0, JHW)

E = pytest.importorskip("llm_events")


def _src(name):
    return io.open(os.path.join(JHW, name), encoding="utf-8").read()


# ------------------------------------------------------------------ pricing
def test_input_and_output_are_priced_separately(monkeypatch):
    """A single blended rate is wrong by a factor of three on this workload: DeepSeek 3.2 is $0.425
    in and $1.36 out, and these calls are output-heavy. The sibling project priced both directions
    the same for weeks and its lifetime cost could never be reconciled with a bank statement."""
    a = E.cost_of("deepseek-3.2", 1_000_000, 0)
    b = E.cost_of("deepseek-3.2", 0, 1_000_000)
    assert a == pytest.approx(0.425) and b == pytest.approx(1.36)
    assert b > a * 3, "output must cost materially more than input, as the vendor charges it"


def test_an_unknown_model_is_priced_pessimistically():
    """AN UNPRICED MODEL MUST NOT LOOK CHEAP. The entire point of this emitter is to notice a caller
    nobody configured -- `glm-5.3-flash` and `deepseek-v4-pro-0813` appear in no configuration in
    either project -- and rounding an unknown down would hide exactly that."""
    ri, ro, known = E.rate_for("glm-5.3-flash")
    assert known is False
    assert ri == max(r[0] for r in E.RATES.values())
    assert ro == max(r[1] for r in E.RATES.values())


def test_a_snapshot_suffix_still_matches_its_family():
    """DigitalOcean serves dated snapshots. `deepseek-3.2-0813` is the model we priced, and failing
    to match it would report our own everyday traffic as an unknown model every single call, which
    would make the `unknown_model` flag useless the day it matters."""
    ri, _ro, known = E.rate_for("deepseek-3.2-0813")
    assert known is True and ri == pytest.approx(0.425)


def test_an_unknown_model_is_flagged_on_the_line_itself(tmp_path, monkeypatch):
    """A Loki query has to be able to find this WITHOUT knowing in advance what to look for. That is
    the difference between catching the next incident in an hour and catching it from an invoice."""
    monkeypatch.setattr(E, "EVENTS_LOG", str(tmp_path / "e.log"))
    ev = E.record("some-model-nobody-configured", {"prompt_tokens": 10, "completion_tokens": 5})
    assert ev["unknown_model"] is True and ev["priced"] is False
    line = json.loads(io.open(str(tmp_path / "e.log"), encoding="utf-8").read().strip())
    assert line["unknown_model"] is True


def test_a_known_model_carries_no_false_alarm(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "EVENTS_LOG", str(tmp_path / "e.log"))
    ev = E.record("deepseek-3.2", {"prompt_tokens": 10, "completion_tokens": 5})
    assert "unknown_model" not in ev and ev["priced"] is True


# ------------------------------------------------------------------ the event itself
def test_the_event_reaches_the_file_promtail_tails(tmp_path, monkeypatch):
    """STDOUT IS NOT ENOUGH. promtail tails the FILE. The sibling project lost every live assessment
    from Grafana to exactly this assumption: `_ev` was print-only and had worked by ACCIDENT,
    because a different container's stdout happened to be scraped."""
    log = tmp_path / "events.log"
    monkeypatch.setattr(E, "EVENTS_LOG", str(log))
    E.record("deepseek-3.2", {"prompt_tokens": 1200, "completion_tokens": 800},
             caller="tailor.call_model", ms=2500)
    d = json.loads(io.open(str(log), encoding="utf-8").read().strip())
    assert d["evt"] == "llm_call"
    assert d["model"] == "deepseek-3.2" and d["caller"] == "tailor.call_model"
    assert d["tokens_in"] == 1200 and d["tokens_out"] == 800
    assert d["cost_usd"] > 0 and d["ms"] == 2500
    assert "service" in d and "ts" in d


def test_both_token_spellings_are_read(tmp_path, monkeypatch):
    """OpenAI-compatible gateways use prompt/completion_tokens; some use input/output_tokens.
    Reading only one spelling records a real call as zero tokens, which is worse than not recording
    it -- a confident zero is evidence of innocence that was never measured."""
    monkeypatch.setattr(E, "EVENTS_LOG", str(tmp_path / "e.log"))
    a = E.record("deepseek-3.2", {"input_tokens": 7, "output_tokens": 9})
    assert a["tokens_in"] == 7 and a["tokens_out"] == 9


def test_a_missing_usage_block_records_zero_and_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "EVENTS_LOG", str(tmp_path / "e.log"))
    for bad in (None, {}, "not a dict", []):
        ev = E.record("deepseek-3.2", bad)
        assert ev is not None and ev["tokens_in"] == 0


def test_recording_can_never_raise(monkeypatch):
    """Observation must never take a user's tailoring run down. An unattributed dollar is a far
    better outcome than a failed run."""
    monkeypatch.setattr(E, "EVENTS_LOG", "/nope/nope/nope.log")
    assert E.record("m", {"prompt_tokens": 1}) is not None      # unwritable path: still returns

    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(E, "cost_of", boom)
    assert E.record("m", {"prompt_tokens": 1}) is None          # and swallows a real failure


# ------------------------------------------------------------------ THE WIRING
def test_both_chokepoints_are_metered():
    """A METER ON ONE OF TWO CHOKEPOINTS IS WORSE THAN NONE: it produces a confident number that is
    half the truth. `llm.complete` serves the backend tasks and `resume_consensus.call_model` serves
    the tailor chain; both post to DO_BASE_URL. This is the 'two homes, one wired up' defect that
    has cost the sibling project four separate incidents."""
    for f in ("llm.py", "resume_consensus.py"):
        s = _src(f)
        assert "llm_events" in s, "%s does not meter its model calls" % f
        assert "llm_events.record(" in s, "%s imports the emitter without calling it" % f


def test_the_meter_sits_after_the_response_not_before():
    """Recording before the answer arrives would log a call that may never have completed, and log
    zero tokens for every one that did."""
    s = _src("llm.py")
    assert s.index("data = r.json()") < s.index("llm_events.record("), \
        "the usage block only exists once the response has been parsed"


def test_no_call_to_the_inference_endpoint_bypasses_the_meter():
    """Derive the chokepoints from the SOURCE rather than trusting a list in this test. A third
    caller added later must either be metered or fail here -- otherwise this check silently shrinks
    to cover less of the codebase every time the codebase grows."""
    unmetered = []
    for fn in sorted(os.listdir(JHW)):
        if not fn.endswith(".py") or fn == "llm_events.py":
            continue
        s = _src(fn)
        # Strip comments: the prose in these files legitimately discusses the endpoint, and the
        # brand gate, recover.py and the caddyguard TAMPER check have each already been caught
        # false-positiving on their own explanatory comments.
        code = "\n".join(ln.split("#")[0] for ln in s.splitlines())
        if "chat/completions" in code and "llm_events" not in code:
            unmetered.append(fn)
    assert not unmetered, ("these post to the inference endpoint without metering it: %s"
                           % ", ".join(unmetered))


def test_the_emitter_is_importable_without_the_web_stack():
    """It has to run inside the container AND be checkable here. `llm_events` imports only json, os
    and time -- no httpx, no fastapi -- so a test of it is not a test of the whole application."""
    tree = ast.parse(_src("llm_events.py"))
    imports = {n.names[0].name.split(".")[0] for n in ast.walk(tree)
               if isinstance(n, ast.Import)}
    assert imports <= {"json", "os", "time"}, "stdlib only: %s" % sorted(imports)


def test_the_emitter_records_and_does_not_enforce():
    """NOT A BUDGET. The sibling enforces a daily cap inside its own `_call`; the equivalent for
    this service is a separate decision with its own blast radius. Bolting enforcement onto an
    emitter is how a logging bug becomes an outage."""
    s = _src("llm_events.py")
    for verb in ("raise ", "BudgetExceeded", "sys.exit"):
        assert verb not in s, "the emitter must observe, never block (%s)" % verb


def test_unknown_tokens_are_not_recorded_as_zero(tmp_path, monkeypatch):
    """ZERO IS A MEASUREMENT; UNKNOWN IS NOT.

    A streamed response carries no `usage` block unless the request asked for
    `stream_options.include_usage`, and adding that would change the bytes a client receives on an
    endpoint whose own comment says never to reframe SSE by hand (doing so already broke Hermes
    once). So a stream records the call and marks the tokens unknown. Writing 0 instead would make
    a busy external client look free and would poison any sum built from these lines -- the same
    rule as llm_meter.spent_today() returning None rather than 0.0.
    """
    monkeypatch.setattr(E, "EVENTS_LOG", str(tmp_path / "e.log"))
    unk = E.record("deepseek-3.2", None, caller="proxy.chat_completions.stream", status="stream")
    assert unk["tokens_known"] is False and unk["cost_usd"] == 0.0
    real = E.record("deepseek-3.2", {"prompt_tokens": 0, "completion_tokens": 0})
    assert real["tokens_known"] is True, "an explicit zero from the API IS a measurement"
    lines = [json.loads(x) for x in
             io.open(str(tmp_path / "e.log"), encoding="utf-8").read().strip().splitlines()]
    assert [x["tokens_known"] for x in lines] == [False, True]


def test_the_proxy_is_metered_because_it_spends_our_key_for_someone_else():
    """THE MOST IMPORTANT CHOKEPOINT OF THE FOUR. proxy.py forwards to DigitalOcean using OUR key,
    so any client holding the proxy token spends on this account without a key of its own. An
    external caller is invisible until the thing it comes through writes a line -- and that is
    exactly the shape of the 2026-09-01 incident, where two model ids in no configuration anywhere
    accounted for >96% of the tokens.

    Both branches must be metered: a meter on the non-streaming path alone would clear the project
    of spend made over the streaming one.
    """
    s = _src("proxy.py")
    assert s.count("llm_events.record(") >= 2, \
        "both the streaming and non-streaming branches must record"
    assert "proxy.chat_completions.stream" in s, "the streaming branch is unmetered"


def test_the_proxy_still_fails_the_way_it_used_to_on_a_non_json_body():
    """A BEHAVIOUR CHANGE MUST NOT RIDE ALONG WITH A LOGGING PATCH. That line was
    `JSONResponse(r.json(), ...)`, so a non-JSON body raised. Swallowing it now to return an empty
    200-shaped object would be a silent change nobody asked for."""
    s = _src("proxy.py")
    i = s.index("_body = r.json()")
    assert "raise" in s[i:i + 700], "the original failure mode must be preserved explicitly"
