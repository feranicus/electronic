"""The AI spend spike detector.

THE CENTRAL PROPERTY, and the reason this file exists: a watcher built only on our own meter would
have reported a completely normal fortnight during the 2026-09-01 incident. >96% of the account's
tokens belonged to two model ids that appear in no configuration in this repository, so nothing we
meter would have moved. `test_a_caller_we_do_not_control_is_still_caught` pins that.
"""
import importlib
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
sys.path.insert(0, os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts"))

SW = pytest.importorskip("app.spend_watch")
LM = pytest.importorskip("llm_meter")


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A private meter and a private state file.

    The meter's DB path is read at IMPORT time into a module global, so setting the environment
    variable is not enough -- the module has to be reloaded, and reloaded AGAIN on teardown or the
    test password/path leaks into every later test in the session. That exact pollution has already
    cost this repository two mystery failures in test_auth.py.
    """
    monkeypatch.setenv("LLM_METER_DB", str(tmp_path / "meter.sqlite"))
    monkeypatch.delenv("DO_API_TOKEN", raising=False)
    lm = importlib.reload(LM)
    monkeypatch.setattr(SW, "STATE", str(tmp_path / "state.json"))
    yield lm
    monkeypatch.delenv("LLM_METER_DB", raising=False)
    importlib.reload(LM)


def _seed(lm, day_offset, caller, model, usd, n=1):
    """Write calls onto a specific day. `record()` always stamps today, so the day is corrected
    afterwards -- the alternative is freezing the clock, which would make every other call in the
    module lie about the time."""
    for _ in range(n):
        lm.record(caller, model, 1000, 500, usd)
    day = time.strftime("%Y-%m-%d", time.gmtime(time.time() - day_offset * 86400))
    if day_offset:
        with lm._connect() as c:
            c.execute("UPDATE calls SET day = ?, ts = ? WHERE day = ? AND ts > ?",
                      (day, time.time() - day_offset * 86400,
                       time.strftime("%Y-%m-%d", time.gmtime()), time.time() - 5))


def _quiet_history(lm, days=10, usd=0.01):
    for i in range(1, days + 1):
        _seed(lm, i, "assess", "deepseek-3.2", usd)


# ------------------------------------------------------------------ the baseline itself
def test_the_baseline_is_a_median_so_one_prior_spike_cannot_hide_the_next(env):
    """MEAN WOULD DEFEAT THE DETECTOR. The thing being measured is an outlier, and an outlier in the
    baseline window drags a mean up far enough to swallow the next one. Nine quiet days and one
    expensive day must still yield a quiet baseline."""
    per_day = [{"day": time.strftime("%Y-%m-%d", time.gmtime(time.time() - i * 86400)),
                "usd": (5.0 if i == 3 else 0.01)} for i in range(1, 11)]
    med, n = SW.baseline(per_day, time.strftime("%Y-%m-%d", time.gmtime()))
    assert n == 10
    assert med == pytest.approx(0.01), \
        "the median must ignore the one expensive day; a mean would report ~0.51 and hide a 20x rise"


def test_a_silent_day_counts_as_zero_and_does_not_raise_the_baseline(env):
    """Skipping days with no calls would quietly raise the baseline and hide a return to spending."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    per_day = [{"day": time.strftime("%Y-%m-%d", time.gmtime(time.time() - i * 86400)), "usd": 0.4}
               for i in (1, 2)]
    med, _ = SW.baseline(per_day, today)
    assert med == pytest.approx(0.0), "the eight silent days must pull the median to zero"


def test_today_is_excluded_from_its_own_baseline(env):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    per_day = [{"day": today, "usd": 9.0}] + [
        {"day": time.strftime("%Y-%m-%d", time.gmtime(time.time() - i * 86400)), "usd": 0.01}
        for i in range(1, 9)]
    med, n = SW.baseline(per_day, today)
    assert today not in [today] or med < 1.0, "today must not damp its own signal"
    assert n == 8


# ------------------------------------------------------------------ the verdict
def test_too_little_history_yields_no_verdict_rather_than_a_confident_one(env):
    """Absence of evidence is never a finding. With two days a median means nothing, and reporting
    a spike from it would train the operator to distrust the alarm."""
    lm = env
    _seed(lm, 1, "assess", "deepseek-3.2", 0.01)
    _seed(lm, 0, "assess", "deepseek-3.2", 5.0)
    v = SW.check()
    assert v["spike"] is False
    assert any("too little for a baseline" in n for n in v["notes"])


def test_a_ratio_on_pocket_change_is_not_an_alert(env):
    """$0.0005 -> $0.01 is a twentyfold rise and is noise. An alarm that is benign every time is
    how the one that matters gets read past."""
    lm = env
    for i in range(1, 9):
        _seed(lm, i, "assess", "deepseek-3.2", 0.0005)
    _seed(lm, 0, "assess", "deepseek-3.2", 0.01)
    v = SW.check()
    assert v["spike"] is False, "below SPIKE_MIN_USD a ratio is arithmetic on noise"


def test_a_real_spike_against_a_quiet_baseline_fires(env):
    lm = env
    _quiet_history(lm, days=10, usd=0.01)
    _seed(lm, 0, "assess", "deepseek-3.2", 0.30, n=3)
    v = SW.check()
    assert v["spike"] is True
    assert any("median" in r for r in v["reasons"])


def test_a_model_never_called_before_is_named_in_the_alert(env):
    """THE DIAGNOSIS, NOT JUST THE ALARM. An alert saying 'spend is up' costs the reader the same
    investigation from scratch. Naming the model that appeared from nothing is the whole answer."""
    lm = env
    _quiet_history(lm, days=10, usd=0.02)
    _seed(lm, 0, "agent", "glm-5.3-flash", 0.02)
    v = SW.check()
    assert v["spike"] is True
    assert any("never called before" in r and "glm-5.3-flash" in r for r in v["reasons"])
    assert any(m["model"] == "glm-5.3-flash" and m["new"] for m in v["models"])
    assert "NEW" in SW.render(v), "the rendered message must carry the marker, not just the dict"


def test_a_model_we_already_use_is_not_reported_as_new(env):
    lm = env
    _quiet_history(lm, days=10, usd=0.02)
    _seed(lm, 0, "assess", "deepseek-3.2", 0.02)
    v = SW.check()
    assert not any(m.get("new") for m in v["models"])


# ------------------------------------------------------------------ THE ONE THAT MATTERS
def test_a_caller_we_do_not_control_is_still_caught(env, monkeypatch):
    """THE 2026-09-01 INCIDENT, REPRODUCED. Our own meter is perfectly quiet -- because the spender
    was not us -- and the account still moved. A meter-only watcher reports a normal fortnight while
    the invoice triples, which is the 'check that cannot see its subject' defect this repository
    keeps paying for. The account delta is the only signal that covers a caller we do not control:
    another project on the shared key, or a GenAI agent created in the DigitalOcean console, which
    runs on their infrastructure and appears in no repository and on no droplet.
    """
    lm = env
    _quiet_history(lm, days=10, usd=0.01)
    _seed(lm, 0, "assess", "deepseek-3.2", 0.01)

    meter_only = SW.check()
    assert meter_only["spike"] is False, "precondition: our own spend really is normal"

    monkeypatch.setattr(SW, "account_spend", lambda: (4.10, "$4.10 in 1.0h"))
    v = SW.check()
    assert v["spike"] is True, "the account moved 4 dollars; that must not go unreported"
    assert any("ACCOUNT" in r for r in v["reasons"])
    assert any("UNATTRIBUTED" in r for r in v["reasons"]), \
        "the gap between account spend and metered spend IS the diagnosis and must be stated"
    assert "console" in SW.render(v), "the message must point at where such a caller can hide"


def test_a_missing_do_token_says_so_instead_of_reporting_zero(env):
    """'I could not look' and 'nothing was spent' must never render the same. That conflation is
    exactly what let logship report success for a week while shipping nothing off-box."""
    delta, why = SW.account_spend()
    assert delta is None
    assert "DO_API_TOKEN" in why
    v = SW.check()
    assert any("DO_API_TOKEN" in n for n in v["notes"])


def test_a_first_balance_reading_is_not_a_delta(env, monkeypatch):
    """A delta needs two readings. Treating the first as a delta would report the whole
    month-to-date figure as one hour's spend and alarm on every fresh deployment."""
    monkeypatch.setenv("DO_API_TOKEN", "t")
    seen = {"n": 0}

    class _R:
        def __init__(self, payload):
            self._p = payload

        def read(self):
            return json.dumps(self._p).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _open(req, timeout=0):
        seen["n"] += 1
        return _R({"month_to_date_usage": "12.00" if seen["n"] == 1 else "16.10"})

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", _open)
    d1, why1 = SW.account_spend()
    assert d1 is None and "first reading" in why1
    d2, _ = SW.account_spend()
    assert d2 == pytest.approx(4.10), "the second reading is the first real delta"


def test_a_billing_month_rollover_is_not_a_negative_spike(env, monkeypatch):
    SW._save_state({"mtd_usage": 40.0, "mtd_ts": time.time() - 3600})
    monkeypatch.setenv("DO_API_TOKEN", "t")

    class _R:
        def read(self):
            return b'{"month_to_date_usage": "0.40"}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _R())
    d, why = SW.account_spend()
    assert d is None and "reset" in why


# ------------------------------------------------------------------ delivery
def test_the_cooldown_stops_an_hourly_check_flooding_the_channel(env, monkeypatch):
    """A spike lasts hours and the check runs hourly. Without a cooldown the day it matters
    produces twenty identical messages and the operator mutes the channel."""
    sent = []
    monkeypatch.setattr(SW, "check", lambda: {"ts": time.time(), "spike": True, "reasons": ["x"],
                                              "notes": [], "today_usd": 1.0, "baseline_usd": 0.01,
                                              "baseline_days": 9, "models": [], "callers": []})
    # Patch the module the code ACTUALLY reaches. `from . import notify` succeeds inside the
    # package, so a fake registered as a bare top-level "notify" is never consulted -- the first
    # version of this test did that, the real notify ran, and it passed for the wrong reason while
    # nothing was delivered.
    import app.notify as real
    monkeypatch.setattr(real, "telegram", lambda t, **k: sent.append(t) or True)
    monkeypatch.setattr(real, "email", lambda s, b, **k: sent.append(s) or True)
    v1 = SW.run_once()
    assert v1["alerted"] is True and sent
    n = len(sent)
    v2 = SW.run_once()
    assert v2["alerted"] is False and len(sent) == n
    assert any("cooldown" in x for x in v2["notes"])


def test_an_undelivered_alert_is_not_reported_as_alerted(env, monkeypatch):
    """AN ALERT NOBODY RECEIVES IS NOT AN ALERT. The first version set `alerted` True whenever
    notify merely imported, so a container with no Telegram token and no Gmail credentials would
    report that it had warned somebody about a spend spike. That is the same 'success for work it
    did not do' defect that let logship ship an empty archive for a week while exiting 0."""
    monkeypatch.setattr(SW, "check", lambda: {"ts": time.time(), "spike": True, "reasons": ["x"],
                                              "notes": [], "today_usd": 1.0, "baseline_usd": 0.01,
                                              "baseline_days": 9, "models": [], "callers": []})
    import app.notify as real
    monkeypatch.setattr(real, "telegram", lambda t, **k: False)
    monkeypatch.setattr(real, "email", lambda s, b, **k: False)
    v = SW.run_once()
    assert v["alerted"] is False
    assert v["delivery"] == {"telegram": False, "email": False}


def test_one_working_channel_still_counts_as_delivered(env, monkeypatch):
    """Telegram up and Gmail down still means the operator was told."""
    monkeypatch.setattr(SW, "check", lambda: {"ts": time.time(), "spike": True, "reasons": ["x"],
                                              "notes": [], "today_usd": 1.0, "baseline_usd": 0.01,
                                              "baseline_days": 9, "models": [], "callers": []})
    import app.notify as real
    monkeypatch.setattr(real, "telegram", lambda t, **k: True)
    monkeypatch.setattr(real, "email", lambda s, b, **k: False)
    assert SW.run_once()["alerted"] is True


def test_the_state_survives_a_container_recreate(env, tmp_path):
    """A cooldown in a module global is reset by every deploy, and this container is force-recreated
    on every ship. That is the identical defect that made the shield's fourteen-day slow window
    unreachable until it was moved to disk."""
    SW._save_state({"last_alert": 1234.0})
    assert os.path.exists(SW.STATE)
    assert SW._load_state().get("last_alert") == 1234.0


def test_the_message_carries_no_markdown(env):
    """An attacker-shaped model id or caller name can contain an underscore; Telegram then rejects
    the whole message as malformed entities and the alert that matters most never arrives."""
    lm = env
    _quiet_history(lm, days=10, usd=0.02)
    _seed(lm, 0, "a_b", "some_model_v2", 0.5)
    body = SW.render(SW.check())
    assert "*" not in body and "`" not in body and "_b" in body


def test_nothing_here_can_raise(env, monkeypatch):
    """Observation must never take the product down. Enforcement is llm_meter.allow()."""
    monkeypatch.setattr(SW, "_meter", lambda: None)
    monkeypatch.setattr(SW, "STATE", "/nope/nope/nope.json")
    v = SW.check()
    assert v["spike"] is False
    assert any("not importable" in n for n in v["notes"])
    assert isinstance(SW.render(v), str)


def test_the_watcher_is_actually_started_by_the_app():
    """A CONTROL THAT IS CORRECT AND UNREACHABLE IS NOT A CONTROL. Every behavioural test above
    calls spend_watch directly, so all of them would still pass with the loop deleted from main.py
    -- which is exactly how `do_agents()` came to be a fully written function that nothing ever
    called, and how the shield's middleware wiring went untested while shield.py was proven correct.
    Assert the CALL, not the filename: `spend_watch` appears in the docstring above it too."""
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    assert "_aio.create_task(_spend_loop())" in src, \
        "the spend watcher must be started at boot beside the other background loops"
    assert "_sw.run_once" in src, "the loop must call run_once, not merely import the module"


def test_an_unreadable_meter_is_reported_not_read_as_a_quiet_day(env, monkeypatch):
    """A meter that has stopped recording looks exactly like a quiet fortnight unless it says so."""
    monkeypatch.setattr(SW._meter(), "report",
                        lambda days=14: {"healthy": False, "today_usd": 0.0, "per_day": [],
                                         "per_caller": [], "per_model": []})
    v = SW.check()
    assert any("UNHEALTHY" in n for n in v["notes"])
