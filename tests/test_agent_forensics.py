"""The client-behaviour classifier must SEPARATE the three shapes, or its verdicts are decoration.

A classifier that has only ever been shown cases it should accept is untested. These run the real
`classify()` over synthetic traces whose ground truth we know, and assert it puts each in the right
bucket AND refuses when there is nothing to measure.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import agent_forensics as F  # noqa: E402


def _verdict(kind):
    ev = F._synth(kind)
    return F.classify(F.analyse({"http": ev, "llm": ev}))[0]


def test_a_person_at_a_keyboard_is_not_called_a_bot():
    """The expensive error. Blocking or reporting a real customer costs far more than missing an
    automated one, which is why the false-positive direction is asserted first."""
    assert "PERSON" in _verdict("human")


def test_a_fixed_interval_loop_is_called_automated():
    assert "AUTOMATED" in _verdict("cron")


def test_an_agent_loop_is_distinguished_from_a_plain_script():
    """The whole question. If this collapses into the cron bucket the tool answers nothing that
    'the traffic was automated' did not already answer."""
    v = _verdict("agent")
    assert "AGENT-SHAPED" in v, v


def test_the_three_shapes_do_not_collapse_into_one_answer():
    """Guards the case where a future edit makes every trace score the same: three individually
    passing assertions could still all be reading one constant."""
    assert len({_verdict(k) for k in ("human", "cron", "agent")}) == 3


def test_a_metronome_does_not_get_credited_with_human_think_time():
    """On a fixed-interval loop the gap between a response finishing and the next request is set by
    the SCHEDULE, so reading it as think-time produced a spurious HUMAN-LIKE vote. A signal that is
    an artifact of another signal must be suppressed, not averaged in."""
    ev = F._synth("cron")
    _, votes, unknown = F.classify(F.analyse({"http": ev, "llm": ev}))
    assert not [w for t, w in votes if "think-time" in w], \
        "a timer's interval is not evidence that somebody read the answer"
    assert any("think time" in u for u in unknown), "and the suppression must be stated, not silent"


def test_a_polling_beat_is_not_credited_with_think_time():
    """THE REAL ACTOR SCORED A SPURIOUS 'HUMAN-LIKE' VOTE AND THIS IS WHY.

    It beat every ~6 minutes for 12 days with inter-arrival CV 0.77, and its think-time CV was
    0.771 -- identical. When the response is short next to the interval, the 'gap after the answer'
    IS the inter-arrival gap, so it measures the schedule and says nothing about a person. The
    original suppression only caught a metronome (CV < 0.35) and missed this."""
    # THE FIRST VERSION OF THIS FIXTURE PROVED NOTHING. Its inter-arrival CV was 0.265, so the OLD
    # metronome rule (CV < 0.35) already suppressed the vote and deleting the new rule changed
    # nothing. A negative test that passes because of a DIFFERENT guard measures that other guard.
    # The gaps below spread like the real actor's: CV comfortably above the metronome threshold.
    gaps = [60, 90, 140, 200, 300, 420, 600, 900, 240, 160]
    t, ev = 1000.0, []
    for i in range(150):
        ev.append({"_ts": t, "ms": 900, "path": "/api/chat", "evt": "http"})
        t += gaps[i % len(gaps)]
    sig = F.analyse({"http": ev, "llm": []})
    assert sig["regularity"] > 0.35, \
        "fixture must clear the metronome rule, or it tests that rule instead of this one"
    assert sig["dependency"] and abs(sig["dependency"]["cv"] - sig["regularity"]) < 0.05, \
        "fixture must reproduce the condition: think-time spread == inter-arrival spread"
    _, votes, unknown = F.classify(sig)
    assert not [w for t, w in votes if "think-time" in w], \
        "a polling interval is not evidence that somebody read the answer"
    assert any("think time" in u for u in unknown), "and the suppression must be stated"


def test_refusals_and_paths_are_surfaced():
    """The first real run reported 1,539 requests and 34 model calls and showed neither what the
    other 98% asked for nor whether it was being refused. That is the decisive cut: a client still
    beating after the locks went on is a retry loop with nobody watching."""
    ev = ([{"_ts": 1000.0 + i, "ms": 5, "path": "/api/chat", "evt": "http", "status": 401}
           for i in range(90)] +
          [{"_ts": 2000.0 + i, "ms": 5, "path": "/api/models", "evt": "http", "status": 200}
           for i in range(10)])
    out = F.render(F.analyse({"http": ev, "llm": []}), "1.2.3.4", 12)
    assert "401 x90" in out, "the response codes must be shown"
    # ASSERT THE ROW, NOT THE PATH. '/api/chat' also appears in the reconnaissance vote, so a bare
    # substring check passed while the path table was blanked out.
    assert "90  /api/chat" in out, "the top-paths table must name what was asked for, with counts"
    assert "90 of 100 refused" in out, "a refused client must be reported as refused"
    assert "retry loop" in out


def test_using_an_endpoint_before_reading_the_schema_is_not_reconnaissance():
    """A NEGATIVE interval meant the endpoint was called BEFORE the schema was read, and the tool
    still voted 'a program read the schema' while printing '-1000s'. It did not learn the API here.
    Found by a mutation run, in code I had just written."""
    ev = [{"_ts": 2000.0, "ms": 5, "path": "/api/chat", "evt": "http", "status": 200},
          {"_ts": 3000.0, "ms": 5, "path": "/api/models", "evt": "http", "status": 200}]
    sig = F.analyse({"http": ev, "llm": []})
    assert sig["recon"]["map_to_use_s"] is None
    _, votes, unknown = F.classify(sig)
    assert not [w for t, w in votes if "read the schema" in w], \
        "a negative interval is not evidence that a program read the schema"
    assert any("reconnaissance" in u for u in unknown), "and the reason must be stated"


def test_a_thin_model_call_ratio_is_not_blamed_on_the_client_when_we_started_late():
    """I NEARLY READ MY OWN INSTRUMENTATION DATE AS CLIENT BEHAVIOUR.

    The real run showed 34 llm_call events against 1,521 served requests, and the tool said 'most of
    this traffic never reached inference'. But evt=llm_call was added to jobhuntwow days before, and
    its writes were failing on a permission bug for most of that window -- so a thin ratio may be
    measuring WHEN WE STARTED LOOKING. Compare the coverage windows before drawing that conclusion."""
    http = [{"_ts": 1000.0 + i * 300, "ms": 50, "path": "/api/chat", "evt": "http", "status": 200}
            for i in range(400)]
    llm = [{"_ts": 1000.0 + 110000 + i * 60, "ms": 900, "model": "m", "tokens_in": 900,
            "status": "ok", "evt": "llm_call"} for i in range(20)]
    sig = F.analyse({"http": http, "llm": llm})
    assert sig["coverage"]["partial"] is True
    out = F.render(sig, "1.2.3.4", 12)
    assert "STARTED MEASURING" in out, "a coverage gap must be named before the client is blamed"
    assert "never reached inference" not in out


def test_full_coverage_lets_the_conclusion_stand():
    """The mirror. If the model-call log spans the traffic, a thin ratio IS about the client, and
    hedging it would be its own dishonesty."""
    http = [{"_ts": 1000.0 + i * 300, "ms": 50, "path": "/api/chat", "evt": "http", "status": 200}
            for i in range(400)]
    llm = [{"_ts": 1000.0 + i * 6000, "ms": 900, "model": "m", "tokens_in": 900, "status": "ok",
            "evt": "llm_call"} for i in range(20)]
    sig = F.analyse({"http": http, "llm": llm})
    assert sig["coverage"]["partial"] is False
    assert "genuinely did not reach inference" in F.render(sig, "1.2.3.4", 12)


def test_a_single_endpoint_client_is_reported_as_zero_reconnaissance():
    """1,539 requests, one path, nothing else ever probed. It arrived knowing where to go, which
    points at prior knowledge rather than opportunistic scanning. That is a finding, and the tool
    was reporting it only as 'recon: not determinable'."""
    ev = [{"_ts": 1000.0 + i * 300, "ms": 50, "path": "/api/chat", "evt": "http", "status": 200}
          for i in range(100)]
    out = F.render(F.analyse({"http": ev, "llm": []}), "1.2.3.4", 12)
    assert "ZERO RECONNAISSANCE" in out and "arrived knowing it" in out


def test_the_plateau_threshold_scales_with_the_clients_own_beat():
    """A fixed 5-minute break threshold reported 0.75h for a client whose longest silence in twelve
    days was SEVENTEEN MINUTES, because its median interval was 6.2 minutes -- so nearly every
    normal gap 'broke' the plateau and the number understated a client that never stopped."""
    ts = [1000.0 + i * 374 for i in range(400)]          # a ~6.2 min beat, like the real actor
    assert F.longest_plateau(ts) > 30, \
        "a steady 6-minute beat is one continuous run, not hundreds of broken ones"
    assert F.longest_plateau(ts, max_gap=300) < 1, "and the fixed threshold is what got that wrong"


def test_when_it_stopped_is_reported_without_guessing_why():
    """The real run's last day was 6 Sep while the window ran to the 7th: it had stopped, and that
    is worth stating. Why it stopped -- locked out, gave up, or finished -- is not decidable from
    these logs, so the tool must say when and refuse to say why."""
    import time as _t
    ev = [{"_ts": _t.time() - 40 * 3600 + i, "ms": 50, "path": "/api/chat", "evt": "http",
           "status": 200} for i in range(60)]
    out = F.render(F.analyse({"http": ev, "llm": []}), "1.2.3.4", 12)
    assert "LAST SEEN:" in out and "It has stopped" in out
    assert "not decidable from these logs" in out, "the tool must not invent a reason"


def test_nothing_to_measure_yields_no_verdict():
    """Absence of evidence is never a finding. Six requests cannot support an inter-arrival claim."""
    ev = F._synth("agent", n=3)
    verdict, votes, _ = F.classify(F.analyse({"http": ev, "llm": ev}))
    assert "INSUFFICIENT" in verdict or not votes, verdict


def test_an_empty_window_is_reported_as_blind_not_innocent():
    """The recurring defect this repository keeps paying for: a query that returned nothing being
    read as proof the client was clean."""
    out = F.render(F.analyse({"http": [], "llm": []}), "1.2.3.4", 12)
    assert "NO REQUESTS FOUND" in out and "not 'the client was innocent'" in out


def test_timing_comes_from_lokis_timestamp_not_the_app_field():
    """The app stamps `ts` with int(time.time()) -- one-second granularity, which would destroy the
    inter-arrival signal most of this analysis rests on. The nanosecond timestamp is Loki's."""
    raw = ('{"data":{"result":[{"values":[["1756000000123456789",'
           '"{\\"evt\\":\\"http\\",\\"ts\\":1756000000,\\"path\\":\\"/api/chat\\"}"]]}]}}')
    ev = F._parse(raw)
    assert len(ev) == 1
    assert abs(ev[0]["_ts"] - 1756000000.1234567) < 0.01, \
        "_ts must carry sub-second precision from Loki, not the app's whole-second ts"


def test_the_logql_query_is_url_encoded():
    """THE DEFECT THIS ASSERTS AGAINST SHIPPED AND REPORTED '0 requests' FOR AN ACTOR WITH 1,538.

    The first version interpolated raw LogQL -- braces, quotes, pipes, spaces -- straight into a
    query string. Loki rejected it, no streams came back, and the emptiness was rendered as a
    measurement. Encode with cost_report._enc, the one encoder."""
    s = F._script("1.2.3.4", 1, 2)
    assert "%7Bcontainer" in s, "the selector must be URL-encoded before it reaches wget"
    assert '{container=~".*jhw-web.*"} |=' not in s, "a raw LogQL query will be rejected by Loki"
    assert "%221.2.3.4%22" in s, "the address filter must be encoded too"


def test_a_query_loki_never_answered_is_not_zero_requests():
    """An error body, an empty body or a non-success envelope means the question was never asked.
    Rendering that as 'no requests' is how a failed lookup becomes an innocence finding."""
    assert F._answered('{"status":"success","data":{"result":[]}}') is True
    for bad in ("", "parse error at line 1", '{"status":"error","error":"bad"}', "<html>502</html>"):
        assert F._answered(bad) is False, bad


def test_an_unshipped_stream_is_blindness_not_innocence():
    """If the unfiltered probe is empty the container shipped nothing, so every conclusion below it
    would be about our own blindness. collect() must refuse rather than return an empty analysis."""
    src = open(os.path.join(ROOT, "agent_forensics.py"), encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    i = body.index("probe = _parse(")
    window = body[i:i + 600]
    assert "if not probe:" in window and "return None" in window, \
        "an empty stream must abort the analysis, not produce a clean-looking zero"
    assert "OUR blindness" in window


def test_the_report_states_what_it_cannot_establish():
    """Prompt bodies are deliberately not logged. A forensic report that does not say so invites
    the reader to believe intent was measured."""
    ev = F._synth("agent")
    out = F.render(F.analyse({"http": ev, "llm": ev}), "1.2.3.4", 12)
    for must in ("CANNOT TELL YOU", "not logged", "An address is not a person"):
        assert must in out, must
