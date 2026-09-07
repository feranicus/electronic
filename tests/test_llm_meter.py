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


# ================================================================== Loki correlation
# The spike is over. Every other probe in cost_report.py is a SNAPSHOT -- `--trace` lists sockets
# open at the moment it runs, which is why it reported "only tailscale and sshd" and settled
# nothing. Loki is the only thing on this estate that holds the PAST.
def test_the_correlation_reads_the_event_the_engine_actually_emits(mod):
    """LogQL built from a guessed field name returns an empty series, which renders exactly like a
    quiet project. enrich.py emits evt=qwen carrying model/tokens_in/tokens_out/cost_usd in the
    LINE (promtail promotes only evt/bot/company/status to labels), so the numbers must be
    unwrapped with `| json` -- and that is asserted against the emitter, not from memory."""
    import cost_report as C
    src = open(os.path.join(SCRIPTS, "enrich.py"), encoding="utf-8").read()
    assert '"evt": "qwen"' in src, "the emitter changed; the queries below are now aimed at nothing"
    for field in ("tokens_out", "cost_usd"):
        assert field in src, "%s is no longer emitted" % field
    joined = " ".join(q for _t, q, _w in C.LOKI_QUERIES)
    assert 'evt="qwen"' in joined and "| json" in joined
    assert "unwrap cost_usd" in joined and "unwrap tokens_out" in joined
    # BY SERVICE, NOT BY JOB. jhw-web writes to the SAME events.log as cybergod (its compose says
    # "already tailed by colt-promtail"), so its lines live under job="coltbots" and are told apart
    # by the `service` field in the line. The first version of this assertion demanded
    # job="jobhuntwow" -- a label only a never-deployed promtail config would set -- and the
    # queries built to satisfy it returned zero for six days and were read as "not shipping".
    assert 'service="jhw-web"' in joined, "the sibling project on the shared key must be queried too"
    assert 'job="jobhuntwow"' not in joined, "that label was never deployed; querying it is blind"


def test_the_attack_overlay_is_present_so_the_hypothesis_can_be_tested(mod):
    """The operator asked whether the attacks are burning the AI budget. That is answerable only if
    attack volume and AI cost are plotted over the SAME window; a table of AI cost alone cannot
    confirm or refute it."""
    import cost_report as C
    titles = [t for t, _q, _w in C.LOKI_QUERIES]
    assert any("attack" in t.lower() for t in titles)
    assert any("cost" in t.lower() for t in titles)


def test_an_empty_series_renders_as_evidence_not_as_silence(mod, capsys):
    """'Loki holds no matching line' is a FINDING. Printing nothing makes it indistinguishable from
    a query that never ran -- the logship defect, which reported success for a week while shipping
    an empty archive."""
    import cost_report as C
    C.render_correlate({"loki": "videodead-loki-1",
                        "series": [{"title": "cybergod model calls, per model",
                                    "why": "w", "rows": []}]}, 10)
    out = capsys.readouterr().out
    assert "NONE. That is evidence" in out


def test_a_failed_correlation_does_not_read_as_a_quiet_window(mod, capsys):
    import cost_report as C
    C.render_correlate({"error": "no Loki container is running on 198.51.100.1"}, 10)
    out = capsys.readouterr().out
    assert "NOT 'nothing was happening'" in out


def test_the_correlation_states_what_jobhuntwow_evidence_covers(mod, capsys):
    """jhw's electronic.py receives `_usage` from call_model and DISCARDS it, so Loki holds its
    HTTP and security events and not one model call. Its AI spend therefore cannot be excluded the
    way cybergod's can, and a reader must be told that rather than left to infer a quiet project
    from an empty row."""
    import cost_report as C
    C.render_correlate({"loki": "l", "series": []}, 10)
    out = capsys.readouterr().out
    # jhw now EMITS llm_call, but only since 2026-09-06 -- so for the 1 and 3 Sep spike its model
    # rows are empty by construction, while its PROXY-HIT row is not. The renderer must say both.
    assert "jobhuntwow" in out and "since 2026-09-06" in out
    assert "since day one" in out, "the reader must be told the proxy-hit evidence predates the emitter"


def test_the_correlation_targets_the_host_by_module_attribute(mod, monkeypatch):
    """recover.py does `HOST = os.environ.get("DROPLET_HOST", ...)` at IMPORT time, so setting the
    environment variable after importing it changes nothing. That defect already shipped once: the
    trace's "staging" block came back a verbatim copy of production, and two identical blocks under
    different headings read as corroboration when they are one measurement twice."""
    import cost_report as C
    import recover
    seen = {}

    def fake(script, timeout=None):
        seen["host"] = recover.HOST
        return ("#### LOKI\nNONE\n", "", 0)

    monkeypatch.setattr(recover, "ssh_script", fake)
    before = recover.HOST
    C.loki_correlate("198.51.100.7", days=3)
    assert seen["host"] == "198.51.100.7", "the query must be sent to the host that was asked for"
    assert recover.HOST == before, "and the module attribute must be restored afterwards"


def test_the_correlation_unpacks_ssh_script_as_three_values(mod, monkeypatch):
    import cost_report as C
    import recover
    monkeypatch.setattr(recover, "ssh_script",
                        lambda s, timeout=None: ("", "connect: network unreachable", 255))
    d = C.loki_correlate("198.51.100.7", days=3)
    assert "error" in d and "255" in d["error"], "a dead transport must be reported, not rendered"


def test_a_blind_query_is_never_reported_as_innocence(mod, capsys):
    """THE TRAP THIS CLOSES, and it decides a real operational action.

    If jobhuntwow's promtail is not shipping, every jhw row is empty -- and the renderer's own
    "NONE. That is evidence" line would then read as PROOF THE PROXY WAS NOT CALLED. It is not; it
    is the query failing to see its subject. Acting on it means either rotating the DO key for
    nothing, or clearing the one project that could actually have spent the money.

    Same disease as logship reporting success for a week while shipping an empty archive, applied
    to an investigation instead of a backup."""
    import cost_report as C
    C.render_correlate({"loki": "l", "series": [
        {"title": "CAN WE SEE jobhuntwow AT ALL (any line, any type)", "why": "w", "rows": []},
        {"title": "CAN WE SEE cybergod AT ALL (any line, any type)", "why": "w",
         "rows": [{"name": "(total)", "total": 900.0, "points": []}]},
        {"title": "WHO called the jobhuntwow LLM proxy (by source IP)", "why": "w", "rows": []},
    ]}, 10)
    out = capsys.readouterr().out
    assert "NOT SHIPPING TO LOKI: jobhuntwow" in out
    assert "BLIND, not innocent" in out
    assert out.index("NOT SHIPPING") < out.index("WHO called"), \
        "the warning must come BEFORE the rows it invalidates, or it is read too late"
    assert "%s" not in out, "a dangling format placeholder would print literally"


def test_a_visible_project_raises_no_false_alarm(mod, capsys):
    """A banner on every run is a banner nobody reads."""
    import cost_report as C
    C.render_correlate({"loki": "l", "series": [
        {"title": "CAN WE SEE jobhuntwow AT ALL (any line, any type)", "why": "w",
         "rows": [{"name": "(total)", "total": 8123.0, "points": []}]},
        {"title": "CAN WE SEE cybergod AT ALL (any line, any type)", "why": "w",
         "rows": [{"name": "(total)", "total": 900.0, "points": []}]},
    ]}, 10)
    out = capsys.readouterr().out
    assert "NOT SHIPPING" not in out and "BLIND" not in out


def test_the_visibility_probes_run_before_everything_else(mod):
    """They decide how every other row is read, so they must be asked first -- and they must query
    the whole stream, not a filtered subset, or an empty filter would look like a dead shipper."""
    import cost_report as C
    t0, q0, _w0 = C.LOKI_QUERIES[0]
    t1, q1, _w1 = C.LOKI_QUERIES[1]
    assert t0.startswith("CAN WE SEE ") and t1.startswith("CAN WE SEE ")
    # "Unfiltered" means no evt/path/status filter -- the probe must count EVERY line of the
    # project, or an empty filtered subset would look like a dead shipper. The service selector is
    # the project boundary itself, not a filter on it.
    for q in (q0, q1):
        assert 'evt=' not in q and 'path=' not in q and 'status=' not in q, "the probe must be unfiltered"
    assert 'service="jhw-web"' in q0 and 'service!="jhw-web"' in q1


# ================================================================== --whodunit: one verdict
def _wd(monkeypatch, jhw, colt, proxy_rows, err=None):
    import cost_report as C
    V = lambda p, n: {"title": "CAN WE SEE %s AT ALL (any line, any type)" % p, "why": "w",  # noqa: E731
                      "rows": ([{"name": "(total)", "total": n, "points": []}] if n else [])}
    series = [V("jobhuntwow", jhw), V("cybergod", colt),
              {"title": "WHO called the jobhuntwow LLM proxy (by source IP)", "why": "w",
               "rows": proxy_rows}]
    monkeypatch.setattr(C, "loki_correlate",
                        lambda h, days=10: ({"error": err} if err
                                            else {"loki": "l", "series": series}))
    return C.whodunit("h", 10)


def test_proxy_hits_name_the_spender(mod, monkeypatch):
    """The decisive branch. jhw's telemetry has logged every /v1/chat/completions hit with its
    source address since the day it was written; nobody had asked."""
    w = _wd(monkeypatch, 8123, 51231, [{"name": "203.0.113.44", "total": 381.0, "points": []}])
    assert w["verdict"] == "THE PROXY IS THE PATH"
    assert w["proxy_sources"][0]["ip"] == "203.0.113.44"
    assert "AGENT_PROXY_TOKEN" in w["action"]


def test_visible_and_zero_hits_means_rotate_the_key(mod, monkeypatch):
    """The OTHER decisive branch, and it must not be softened: if the project IS observable and
    shows no proxy calls, nothing we run spent that money. The only remaining explanation is the
    raw key being used somewhere we do not control, and no code change fixes that."""
    w = _wd(monkeypatch, 8123, 51231, [])
    assert w["verdict"] == "NOT THE PROXY - ROTATE THE KEY"
    assert "ROTATE" in w["action"] and "per project" in w["action"].lower()


def test_a_blind_project_never_yields_a_verdict(mod, monkeypatch):
    """THE ONE THAT PREVENTS A WRONG ACTION. Zero proxy hits from a project that is not shipping
    is the query failing to see its subject, not proof of innocence -- and acting on it would mean
    rotating a key for nothing. It must NOT reach the rotate verdict."""
    w = _wd(monkeypatch, 0, 51231, [])
    assert w["verdict"] == "BLIND - NOT INNOCENT"
    assert "ROTATE" not in w["action"].upper()
    assert "Decide NOTHING" in w["action"]


def test_a_failed_query_is_not_a_verdict(mod, monkeypatch):
    w = _wd(monkeypatch, 0, 0, [], err="no Loki container is running")
    assert w["verdict"] == "CANNOT DECIDE" and "not evidence" in w["action"]


def test_a_refused_model_pages_immediately(mod):
    """A LOG LINE NOBODY IS WATCHING WASTES THE ONE EVENT WE HAVE BEEN WAITING FOR. The refusal is
    the smoking gun: it carries who asked, from where, for what -- and it costs nothing because the
    request was blocked. It has to reach a phone, not a file."""
    p = os.path.join(ROOT, "jobhuntwow-app", "backend", "app", "proxy.py")
    if not os.path.exists(p):
        import pytest as _p
        _p.skip("jobhuntwow-app not checked out")
    s = open(p, encoding="utf-8").read()
    i = s.index('caller="proxy.REFUSED"')
    j = s.index("raise HTTPException(403", i)
    seg = s[i:j]
    assert "notify.telegram(" in seg, "a refusal must alert, not only log"
    # SCOPE TO THE ALERT'S OWN ARGUMENTS. The first version searched the whole refusal block for
    # "ip", which matched the `user=ip` in the llm_events.record call above it -- so a mutation
    # that replaced the address in the ALERT with a literal still passed. Aimed next to its subject.
    alert = seg.split("notify.telegram(", 1)[1]
    assert "ip or" in alert, "the ALERT itself must carry the client address, not just the log line"
    assert "requested" in alert, "and the model that was asked for"
    for md in ("*", "`", "_bold"):
        assert md not in seg.split("notify.telegram(")[1][:400], \
            "no Markdown: an attacker-controlled model id or IP with an underscore makes Telegram " \
            "reject the whole message, losing the one alert that matters most"


# ------------------------------------------------------------------ the FILE outranks the index
def _wd_file(monkeypatch, jhw_loki, file_txt, proxy_rows=()):
    """whodunit with a stubbed droplet: Loki says one thing, the raw events.log says another."""
    import cost_report as C
    V = lambda p, n: {"title": "CAN WE SEE %s AT ALL (any line, any type)" % p, "why": "w",  # noqa: E731
                      "rows": ([{"name": "(total)", "total": n, "points": []}] if n else [])}
    series = [V("jobhuntwow", jhw_loki), V("cybergod", 5000),
              {"title": "WHO called the jobhuntwow LLM proxy (by source IP)", "why": "w",
               "rows": list(proxy_rows)}]
    monkeypatch.setattr(C, "loki_correlate",
                        lambda h, days=10: {"loki": "l", "series": series,
                                            "file": C.file_evidence(file_txt, 0)})
    return C.whodunit("h", 10)


_FILE_OK = ("jhw_mount=/var/lib/docker/volumes/colt-stack_colt_events/_data\n"
            "jhw_env=EVENTS_LOG=/var/log/colt/events.log\njhw_env=SERVICE=jhw-web\n"
            "file=/var/lib/docker/volumes/colt-stack_colt_events/_data/events.log size=9\n"
            "jhw_lines=1234\n"
            'jhw_first={"evt": "http", "service": "jhw-web", "ts": 1756000000}\n'
            'jhw_last={"evt": "http", "service": "jhw-web", "ts": 1757000000}\n')
_HIT = ('proxy={"evt": "http", "service": "jhw-web", "ip": "203.0.113.9", '
        '"path": "/v1/chat/completions", "status": 200, "ts": 1756800000}\n')


def test_the_raw_file_outranks_a_blind_index(mod, monkeypatch):
    """THE 2026-09-06 DEFECT. whodunit printed BLIND twice from the Loki index while the raw
    events.log on the same droplet held every jhw-web line and the proxy hits with their source
    addresses. Loki is a VIEW over that file; when they disagree the file decides and the
    disagreement is reported as an indexing gap, not as a silent project."""
    w = _wd_file(monkeypatch, 0, _FILE_OK + _HIT)
    assert w["verdict"] == "THE PROXY IS THE PATH", w["verdict"]
    assert w["proxy_sources"][0]["ip"] == "203.0.113.9"
    assert "INDEXING gap" in w["note"]


def test_a_writing_project_with_no_hits_in_the_file_reaches_rotate(mod, monkeypatch):
    w = _wd_file(monkeypatch, 0, _FILE_OK)
    assert w["verdict"] == "NOT THE PROXY - ROTATE THE KEY"


def test_truly_blind_names_the_broken_hop(mod, monkeypatch):
    """A project that has written nothing anywhere is still blind, and the message must say
    WHICH hop is broken (mount / env / file), because 'fix the log shipper' sent the operator to
    a promtail that was never the problem."""
    w = _wd_file(monkeypatch, 0, "jhw_mount=NONE\nfile=/x/events.log size=1\njhw_lines=0\n")
    assert w["verdict"] == "BLIND - NOT INNOCENT" and "does not mount" in w["action"]
    w = _wd_file(monkeypatch, 0, "jhw_mount=/v\nfile=/x/events.log size=1\njhw_lines=0\n")
    assert "no EVENTS_LOG" in w["action"]


def test_the_droplet_script_reads_the_file_before_loki(mod):
    """The FILE section must not sit behind the 'no Loki -> exit' line, or a box without Loki
    loses the primary source too. And the whole thing must still be valid bash."""
    import cost_report as C, subprocess, shutil
    s = C._loki_script(C.LOKI_QUERIES, "1", "2", "3600")
    assert s.index('#### FILE') < s.index('[ -z "$L" ] && exit 0')
    assert "/v1/chat/completions" in s and '"service": "jhw-web"' in s
    if shutil.which("bash"):
        r = subprocess.run(["bash", "-n"], input=s.encode(), capture_output=True)
        assert r.returncode == 0, r.stderr.decode()[:200]


def test_docker_stdout_stream_answers_when_the_file_cannot(mod, monkeypatch):
    """jhw-web runs as UID 10001 and the shared events.log is root 0644, so it has NEVER written a
    line there; every append is a swallowed PermissionError. The same line goes to stdout first,
    and videodead-promtail scrapes docker stdout into Loki under a `container` label. That stream
    must count as visibility AND as a source of proxy hits, or the verdict stays BLIND forever."""
    import cost_report as C
    V = lambda p, n: {"title": "CAN WE SEE %s AT ALL (x)" % p, "why": "w",  # noqa: E731
                      "rows": ([{"name": "(total)", "total": n, "points": []}] if n else [])}
    series = [V("jobhuntwow", 0), V("cybergod", 5000), V("jobhuntwow-stdout", 40000),
              {"title": "WHO called the jobhuntwow LLM proxy (by source IP)", "why": "w", "rows": []},
              {"title": "WHO called the jobhuntwow LLM proxy (by source IP, from docker stdout)",
               "why": "w", "rows": [{"name": "203.0.113.77", "total": 512.0, "points": []}]}]
    monkeypatch.setattr(C, "loki_correlate",
                        lambda h, days=10: {"loki": "l", "series": series,
                                            "file": C.file_evidence(_FILE_OK.replace("1234", "0"), 0)})
    w = C.whodunit("h", 10)
    assert w["verdict"] == "THE PROXY IS THE PATH", (w["verdict"], w["action"])
    assert w["proxy_sources"][0]["ip"] == "203.0.113.77" and w["proxy_hits"] == 512
    titles = [q[0] for q in C.LOKI_QUERIES]
    assert any("jobhuntwow-stdout" in t for t in titles)
    assert any('container=~".*jhw-web.*"' in q[1] and "/v1/chat/completions" in q[1]
               for q in C.LOKI_QUERIES)


def test_substring_evidence_beats_a_json_shaped_zero(mod, monkeypatch):
    """The question the operator actually asked: we know the MODEL NAMES and the DATES. Search
    every stream by substring, return the LINES, and let that outrank a metric row that only
    counts lines whose JSON happens to have the fields we assumed."""
    import cost_report as C, recover, json as J
    now = 1757000000
    def fake(script, timeout=0):
        out = ["#### FILE", _FILE_OK.replace("1234", "0"), "#### LOKI", "videodead-loki-1"]
        for i, _ in enumerate(C.LOKI_QUERIES):
            n = 99310 if "jobhuntwow-stdout" in C.LOKI_QUERIES[i][0] else (5000 if "cybergod AT ALL" in C.LOKI_QUERIES[i][0] else 0)
            out += ["#### Q%d" % i, J.dumps({"data": {"result": ([{"metric": {}, "values": [[str(now), str(n)]]}] if n else [])}})]
        for i, (t, _q, _l) in enumerate(C.LOKI_SAMPLES):
            lines = []
            if "proxy path" in t:
                lines = [[str(now * 10**9), '{"log":"{\\"evt\\": \\"http\\", \\"ip\\": \\"203.0.113.5\\", \\"path\\": \\"/v1/chat/completions\\"}\\n","stream":"stdout"}']]
            if "deepseek-v4-pro, ANY" in t:
                lines = [[str(now * 10**9), '[proxy] deepseek-v4-pro-0813 forwarded']]
            out += ["#### S%d" % i, J.dumps({"data": {"resultType": "streams", "result": ([{"stream": {"container": "jhw-web"}, "values": lines}] if lines else [])}})]
        for i, _ in enumerate(C.LOKI_HOURLY):
            out += ["#### H%d" % i, J.dumps({"data": {"result": [{"metric": {"container": "jhw-web"}, "values": [[str(now), "3"], [str(now + 3600), "0"]]}]}})]
        return "\n".join(out), "", 0
    monkeypatch.setattr(recover, "ssh_script", fake)
    w = C.whodunit("h", 10)
    assert w["proxy_hits"] == 1 and "SUBSTRING" in w["note"], (w["proxy_hits"], w["note"])
    assert w["verdict"] != "NOT THE PROXY - ROTATE THE KEY", "a wrapped line shape must not read as innocence"
    hit = [x for x in w["samples"] if "deepseek-v4-pro, ANY" in x["title"]][0]
    assert hit["lines"] and hit["lines"][0][1] == "jhw-web"
    assert w["hourly"][0]["rows"][0]["points"] == [(now, 3.0)]
