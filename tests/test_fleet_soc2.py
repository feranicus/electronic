"""TWO REPORTING DEFECTS ON THE FLEET PAGE, and the properties that stop them coming back.

Neither of these was a hole in the defence. Both were the page describing the defence wrongly,
which is the more expensive kind: a control that is working and reported as `off` gets "fixed",
and a control that is off and reported as fine never gets looked at.

  1. cybergod.ai READ `off` AND IS THE BEST-DEFENDED SITE IN THE ESTATE. perseus_client sets
     LOCAL=False when webapp/backend/app/shield.py sits beside it on disk -- true on colt-web and
     nowhere else -- and it does so BECAUSE the full shield is the stronger of the two: two
     independent blockers on one request path return two verdicts about one address and the
     client's has no console to release anybody from. The heartbeat carries `local: false`, the
     page read it as "present but not armed to act locally", and printed the exact opposite of the
     truth. `local: false` is a fact about the CLIENT'S COPY; it is not a fact about local
     enforcement, and the fix is to MEASURE the thing that does enforce rather than to special-case
     a service name.

  2. klima AND s4biz READ `partial` BECAUSE THEIR TRAFFIC NEVER REACHES THE BRAIN. The mechanism
     that would fix it exists and is deliberately OFF (PERSEUS_LOKI_EVENTS) because an earlier
     version of that lookup took the Admin page down twice and has never been observed working.
     The fix is not to flip it: it is for the row to NAME the switch, say it is off pending
     verification, and carry the one next action that would move it to `active`.

WHAT THIS FILE IS CAREFUL ABOUT, because the repository has paid for each one:

  * THE FIXTURE IS PROVEN BEFORE IT IS USED (defect class 12). The first test asserts that the real
    perseus_client, imported from the real package, really does stand down beside the real
    shield.py. Without that, every assertion below would be about a condition that does not exist.
  * THE MEASUREMENT CAN FAIL (defect class 3). _shield_facts is broken three separate ways -- off,
    not enforcing, no detection table -- and each one must still produce `off`. A fix that simply
    deleted the `off` state would pass a test that only ever checked the happy direction.
  * NOTHING HERE DEPENDS ON THE OPERATOR'S ENVIRONMENT (defect class 19/20). `_self_service()` is
    stubbed in the behavioural tests, and asserted against its ONE HOME in a test of its own, so a
    box with SERVICE set to something else fails loudly instead of skipping silently.

tests/test_fleet.py and tests/test_fleet_soc.py are NOT imported here; the fixtures below are
deliberately independent, so a change to either of those files cannot satisfy an assertion in this
one.
"""
import json
import os
import re
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
sys.path.insert(0, ROOT)

from app import fleet  # noqa: E402

FLEET_JSX = os.path.join(ROOT, "webapp", "frontend", "src", "pages", "Fleet.jsx")
LOCALE_DIR = os.path.join(ROOT, "webapp", "frontend", "src", "locales")
LOCALES = ("en", "de", "it", "fr", "es", "pl")

# The three states a row can be in that are not `active`. Written down so the coverage assertion
# below cannot quietly stop exercising one of them.
NOT_ACTIVE = ("off", "partial", "unknown")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """TESTS MUST NOT REACH THE INTERNET, and this one also COUNTS. status() is not allowed to make
    a network call on the request path at all -- both of the things that ever took this page down
    were Loki queries -- so a test that merely tolerated one would be measuring the wrong property.
    """
    import urllib.request
    calls = []

    def offline(url, timeout=0):
        calls.append(url)
        raise OSError("tests must not reach the internet")

    monkeypatch.setattr(urllib.request, "urlopen", offline)
    return calls


def _estate(monkeypatch, tmp_path, rows=(), beats=None, blocklist=None):
    """Point fleet at a temporary estate and CLEAR its module-level caches.

    The caches are globals and outlive a test, so one case's answer would silently satisfy the
    next case's assertion.
    """
    ev = os.path.join(str(tmp_path), "events.log")
    with open(ev, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    bd = os.path.join(str(tmp_path), "beats")
    os.makedirs(bd, exist_ok=True)
    for stale in os.listdir(bd):                      # tmp_path is per-TEST, not per-call
        os.remove(os.path.join(bd, stale))
    for svc, doc in (beats or {}).items():
        with open(os.path.join(bd, "%s.json" % svc), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    bl = os.path.join(str(tmp_path), "blocklist.json")
    if blocklist is None:
        if os.path.exists(bl):
            os.remove(bl)
    else:
        with open(bl, "w", encoding="utf-8") as fh:
            json.dump(blocklist, fh)

    monkeypatch.setattr(fleet, "EVENTS", ev)
    monkeypatch.setattr(fleet, "BEAT_DIR", bd)
    monkeypatch.setattr(fleet, "BLOCKLIST", bl)
    monkeypatch.setattr(fleet, "LOKI_PUBLISH_ON", False)
    monkeypatch.setattr(fleet, "LOKI_EVENTS_ON", False)
    monkeypatch.delenv("LOKI_URL", raising=False)
    fleet._LOKI_CACHE.update(ts=0.0, beats={})
    fleet._LOKI_EVENTS.update(ts=0.0, rows=[], ok=False, partial=False, busy=False)
    fleet._PUBLISH.update(ts=0.0, busy=False)
    fleet._PUBLISH["val"] = {"lookup": "pending", "runs": None, "ok": None, "failed": None,
                             "cycle": None, "err": None}
    return bl


def _http(service, path="/", status=200, ip="203.0.113.44"):
    return {"evt": "http", "service": service, "ip": ip, "path": path, "status": status,
            "ts": int(time.time()) - 5}


def _beat(service, **kw):
    d = {"service": service, "ts": int(time.time()), "cycle": 3}
    d.update(kw)
    return d


def _loops(monkeypatch, daily=True, weekly=True, watch=True):
    """The three autonomous loops, under the test's control. `None` means UNREADABLE, which is a
    different fact from `False` (ran, but not recently) and the page must not merge them."""
    now = int(time.time())
    monkeypatch.setattr(fleet, "_cycle", lambda: {
        "cycle": 4 if daily else 0, "patterns": 2, "age_s": 60,
        "readable": True if daily is not None else False,
        "enforcing": bool(daily), "generated": now, "path": "x", "err": None})
    monkeypatch.setattr(fleet, "_fresh",
                        lambda p, m: ((weekly, 10) if "weekly" in p else (watch, 10)))


def _shield(monkeypatch, armed=True, enabled=True, enforcing=True,
            detection="app.perseus_client", measured=True, svc="colt-web", err=None):
    """The local-shield measurement, stubbed, so the BEHAVIOUR tests are deterministic on any box.
    `_shield_facts` itself is exercised against the real shield further down; this stub is the
    input to the verdict, not a substitute for measuring it."""
    facts = {"svc": svc, "measured": measured, "armed": armed, "enabled": enabled,
             "enforcing": enforcing, "detection": detection, "err": err}
    monkeypatch.setattr(fleet, "_shield_facts", lambda: dict(facts))
    return facts


def _rows(monkeypatch, tmp_path, **kw):
    _estate(monkeypatch, tmp_path, **kw)
    return {p["service"]: p for p in fleet.status()["projects"]}


# ============================================================ 1. PROVE THE FIXTURE BEFORE USING IT

def test_the_sidecar_really_does_stand_down_beside_the_real_shield():
    """PROVE THE CONDITION UNDER TEST EXISTS, from the real files, before testing the reporting of
    it. A fixture that does not reproduce the condition is a test of the fixture.

    This is the whole premise of defect 1: on colt-web the copied client sets LOCAL=False because
    shield.py is its sibling, so its heartbeat says `local: false` while the site has MORE local
    defence than any other, not less. If this ever stops being true, every assertion below is about
    a state the estate is not in and must be re-derived rather than trusted.
    """
    from app import perseus_client, shield
    assert os.path.dirname(os.path.abspath(perseus_client.__file__)) == \
        os.path.dirname(os.path.abspath(shield.__file__)), \
        "the client and the full shield are no longer siblings; the LOCAL=False premise is gone"
    assert perseus_client._shield_sibling() is True
    assert perseus_client.LOCAL is False, \
        ("the copied client is NOT standing down beside shield.py (PERSEUS_LOCAL set in this "
         "environment?). The defect this file is about cannot occur, so these tests prove nothing.")


def test_the_page_asks_for_itself_by_the_name_its_own_log_lines_carry():
    """ONE HOME for 'which project is this container'. If the page resolved the name from its own
    reading of the environment it could attribute a measurement to the wrong row, which is the
    hoster-identity defect on a dashboard."""
    from app import telemetry
    assert fleet._self_service() == telemetry.SERVICE
    assert fleet._self_service(), "an empty service name matches no row and measures nothing"


# ====================================================== 2. DEFECT 1: cybergod must not read `off`

def test_colt_web_with_shield_py_present_is_NOT_reported_off(monkeypatch, tmp_path):
    """THE DEFECT, STATED AS A PROPERTY. The heartbeat says local=false; the shield in this process
    says it is armed; the row must be reported on the SHIELD, not on the flag."""
    _shield(monkeypatch, armed=True)
    _loops(monkeypatch)
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})["colt-web"]
    assert r["soc"] != "off", r["soc_why"]
    assert r["soc_local_by"] == "shield", \
        "the local term must come from the measurement, not from the beat that reads backwards"
    # ...and with every other term satisfied it is not merely "not off", it is the top of the scale.
    assert r["soc"] == "active", r["soc_why"]
    assert r["soc_next"] == "", "an active row has nothing left to do"


def test_a_row_measured_through_shield_py_SAYS_it_was(monkeypatch, tmp_path):
    """A DIAGNOSTIC THAT DOES NOT NAME ITS SUBJECT SENDS THE NEXT INVESTIGATION DOWN THE WRONG ROAD.
    When the local term came from shield.py the reason must say so, and say which detection table
    it resolved -- otherwise the next person reading `partial` cannot tell which half is wrong."""
    _shield(monkeypatch, armed=True, detection="app.perseus_client")
    _loops(monkeypatch, weekly=False)                 # one loop stale, so the row is `partial`
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})["colt-web"]
    assert r["soc"] == "partial"
    assert "shield.py" in r["soc_why"] and "app.perseus_client" in r["soc_why"], r["soc_why"]
    assert "perseus-weekly" in r["soc_next"], r["soc_next"]


def test_the_beat_flag_alone_would_still_have_said_off(monkeypatch, tmp_path):
    """THE NEGATIVE CONTROL FOR THE TEST ABOVE. Same fixture, shield measurement withdrawn (the
    import failed, so `measured` is false). The page falls back to the heartbeat and reports `off`
    -- which is the OLD behaviour, still reachable, and still what happens when we genuinely cannot
    measure. Without this, the test above could be passing because the `off` state was deleted."""
    _shield(monkeypatch, measured=False, armed=False, enabled=None, enforcing=None,
            detection=None, err="ImportError('shield')")
    _loops(monkeypatch)
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})["colt-web"]
    assert r["soc"] == "off"
    assert r["soc_local_by"] == "beat"


@pytest.mark.parametrize("broken,expect", [
    (dict(armed=False, enabled=False), "SHIELD=on"),
    (dict(armed=False, enforcing=False), "SHIELD_ENFORCE=on"),
    (dict(armed=False, detection="unavailable"), "detection table"),
])
def test_a_shield_that_is_measurably_not_armed_is_still_OFF(monkeypatch, tmp_path, broken, expect):
    """PROVE THE GATE BY BREAKING THE THING IT GUARDS. Three separate ways for the shield to be
    off, each defeated on its own with the other two healthy, so a pass cannot come from some other
    guard. `detection == "unavailable"` is the one that matters most: the shield is up, it is
    enforcing, and it is scoring NOTHING because the shared table could not be imported. A control
    that is off must never look like a control that found nothing."""
    _shield(monkeypatch, **broken)
    _loops(monkeypatch)
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})["colt-web"]
    assert r["soc"] == "off", r["soc_why"]
    assert r["soc_local_by"] == "shield"
    assert "shield.py" in r["soc_why"], "the row must name what it measured: %r" % r["soc_why"]
    assert expect in r["soc_next"], \
        "the row must name the ONE thing that is wrong, not a generic remedy: %r" % r["soc_next"]


def test_a_sidecar_that_is_GENUINELY_unarmed_is_still_OFF(monkeypatch, tmp_path):
    """THE FIX MUST NOT HAVE DELETED THE STATE. jobhuntwow is not this container, so nothing about
    shield.py in this process says anything about it; its own heartbeat says it is not armed and
    that is the answer. Reporting it as anything else would be lending our posture to a sibling."""
    _shield(monkeypatch, armed=True)                  # armed HERE, and irrelevant THERE
    _loops(monkeypatch)
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("jhw-web")],
              beats={"jhw-web": _beat("jhw-web", local=False, enforcing=False)})["jhw-web"]
    assert r["soc"] == "off", r["soc_why"]
    assert r["soc_local_by"] == "beat"
    assert "PERSEUS_LOCAL" in r["soc_next"] and "jhw-web" in r["soc_next"]


def test_the_measurement_is_never_lent_to_another_project(monkeypatch, tmp_path):
    """The same property said the other way round: an ARMED shield in this process must not raise a
    sibling's row, and a BROKEN one must not lower it. Only the row for this container may move."""
    _loops(monkeypatch)
    beats = {"jhw-web": _beat("jhw-web", local=True, enforcing=True)}
    rows = [_http("jhw-web")]
    _shield(monkeypatch, armed=True)
    a = _rows(monkeypatch, tmp_path, rows=rows, beats=beats)["jhw-web"]
    _shield(monkeypatch, armed=False, enabled=False)
    b = _rows(monkeypatch, tmp_path, rows=rows, beats=beats)["jhw-web"]
    assert a["soc"] == b["soc"] and a["soc_local_by"] == b["soc_local_by"] == "beat"


def test_an_absent_local_flag_is_still_UNKNOWN_and_never_off(monkeypatch, tmp_path):
    """A heartbeat that predates the local shield carries no `local` key at all. Absence of
    evidence is not evidence, and it is not the inverted flag this change is about either -- the
    measurement substitutes for a flag that says FALSE, never for a flag that is missing."""
    _shield(monkeypatch, armed=True)
    _loops(monkeypatch)
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web")})["colt-web"]
    assert r["soc"] == "unknown", r["soc_why"]
    assert r["soc_next"], "even an unknown row must name the step that would make it measurable"


# ================================== 3. _shield_facts ITSELF: it measures, and it is able to fail

def test_the_shield_measurement_reads_the_three_fields_shield_py_actually_publishes():
    """READ THE SIGNATURE. This function is built on shield.state() returning `enabled`,
    `enforcing` and `detection`; asserting the contract here means a rename in shield.py fails
    LOUDLY instead of silently degrading every row to `off`."""
    from app import shield
    st = shield.state()
    assert isinstance(st, dict)
    for k in ("enabled", "enforcing", "detection"):
        assert k in st, "shield.state() no longer publishes %r; fleet.py reads it" % k
    assert isinstance(st["detection"], str) and st["detection"], \
        "detection must NAME where the table came from, or `unavailable`"


def test_the_shield_measurement_can_fail(monkeypatch):
    """A CHECK THAT CANNOT FAIL IS NOT A CHECK. Each of the three facts is defeated on its own."""
    from app import shield
    base = {"enabled": True, "enforcing": True, "detection": "app.perseus_client"}
    monkeypatch.setattr(shield, "state", lambda: dict(base))
    assert fleet._shield_facts()["armed"] is True, "the positive control must pass first"
    for kill in ({"enabled": False}, {"enforcing": False}, {"detection": "unavailable"},
                 {"detection": ""}):
        monkeypatch.setattr(shield, "state", lambda k=kill: dict(base, **k))
        f = fleet._shield_facts()
        assert f["measured"] is True and f["armed"] is False, \
            "%r left the shield reported as armed" % kill


def test_a_shield_that_cannot_be_asked_is_UNMEASURED_not_UNARMED(monkeypatch):
    """Our own blindness is never a verdict about the system. An exception and a hostile return
    shape both land on `measured: false` with the cause NAMED, so the caller falls back to the
    heartbeat rather than inventing an answer."""
    from app import shield

    def boom():
        raise RuntimeError("the shield exploded")

    monkeypatch.setattr(shield, "state", boom)
    f = fleet._shield_facts()
    assert f["measured"] is False and f["armed"] is False
    assert "exploded" in (f["err"] or ""), "the cause must travel in the payload"

    monkeypatch.setattr(shield, "state", lambda: ["not", "a", "mapping"])
    f = fleet._shield_facts()
    assert f["measured"] is False and f["err"], "an unexpected shape is not a measurement"


# ============================= 4. DEFECT 2: a blind row must name the switch, and the next action

def test_a_blind_own_log_project_names_the_env_var_and_says_it_is_off_pending_verification(
        monkeypatch, tmp_path):
    """klima and s4biz. The mechanism that would clear this exists and is OFF on purpose; the row's
    job is to say WHICH switch and WHY it is off, not to describe the gap in general terms."""
    _shield(monkeypatch, armed=True)
    _loops(monkeypatch)
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"polara-web": _beat("polara-web", local=True, enforcing=True)})["polara-web"]
    assert r["alerting"] == "blind", "the fixture did not reach the blind branch (%s)" % r["alerting"]
    assert r["soc"] == "partial"
    assert "PERSEUS_LOKI_EVENTS" in r["soc_why"] and "pending verification" in r["soc_why"]
    assert r["soc_next"] == "set PERSEUS_LOKI_EVENTS=1 on colt-web (off pending verification)", \
        r["soc_next"]


def test_the_switch_is_still_OFF_by_default(monkeypatch, tmp_path):
    """THE ROW REPORTS THE SWITCH; IT DOES NOT FLIP IT. The lookup took the Admin page down twice
    and has never been observed working, so the committed default stays off and this test is what
    stops a later 'while we are here' from changing it quietly."""
    # COMMENTS AND DOCSTRINGS STRIPPED FIRST. A check in this repository has matched its own
    # explanatory comment five separate times, and fleet.py's comments quote this very name.
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "fleet.py"), encoding="utf-8").read()
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    assert 'os.environ.get("PERSEUS_LOKI_EVENTS", "0") == "1"' in src, \
        "the traffic lookup no longer defaults OFF; that default is a retreat to a working state"


def test_a_project_that_ships_no_line_at_all_gets_a_different_next_action(monkeypatch, tmp_path):
    """TWO GAPS, ONE WORD. An own-log project is blind because the lookup is off; anything else is
    blind because it ships nothing this container can read. Naming the env var for the second would
    be a remedy for a state it is not in -- an invented finding, one column over."""
    _shield(monkeypatch, armed=True)
    _loops(monkeypatch)
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"jev-web": _beat("jev-web", local=True, enforcing=True)})["jev-web"]
    assert r["alerting"] == "blind" and r["soc"] == "partial"
    assert "PERSEUS_LOKI_EVENTS" not in r["soc_next"], \
        "jev.best writes to the SHARED log; that switch would not clear it"
    assert "jev-web" in r["soc_next"] and "evt=http" in r["soc_next"]


# ================================================================= 5. soc_next, as a whole property

def _battery(monkeypatch, tmp_path):
    """Every SOC state this page can produce, from real fixtures rather than from a list somebody
    typed. Returns the rows, so the assertions below are made against what the code DID."""
    got = []
    cases = [
        # active: armed, alerting=self, all three loops current
        (dict(armed=True), dict(daily=True, weekly=True, watch=True),
         dict(rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})),
        # off: a sibling whose own beat says it is not armed
        (dict(armed=True), dict(),
         dict(rows=[_http("jhw-web")],
              beats={"jhw-web": _beat("jhw-web", local=False, enforcing=False)})),
        # off: this container, measured, and measurably not armed
        (dict(armed=False, enforcing=False), dict(),
         dict(rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})),
        # partial: blind because the traffic lookup is off
        (dict(armed=True), dict(),
         dict(rows=[_http("colt-web")],
              beats={"polara-web": _beat("polara-web", local=True, enforcing=True)})),
        # partial: a loop that ran, but not recently
        (dict(armed=True), dict(weekly=False),
         dict(rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})),
        # partial: a loop whose state file cannot be read at all
        (dict(armed=True), dict(weekly=None, watch=None),
         dict(rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})),
        # unknown: a heartbeat that cannot report whether it can act
        (dict(armed=True), dict(),
         dict(rows=[_http("colt-web")], beats={"colt-web": _beat("colt-web")})),
        # unknown: no heartbeat at all, on a project whose beat lives on its own volume
        (dict(armed=True), dict(),
         dict(rows=[_http("colt-web")], beats={})),
    ]
    for sh, lp, est in cases:
        _shield(monkeypatch, **sh)
        _loops(monkeypatch, **lp)
        got.extend(_rows(monkeypatch, tmp_path, **est).values())
    return got


def test_soc_next_is_empty_when_active_and_concrete_when_not(monkeypatch, tmp_path):
    """THE PROPERTY THE FIELD EXISTS FOR. Empty is a MEASURED "nothing to do"; anything else must
    name one thing somebody could actually do. A detail that renders identically whether or not
    anything was measured is templated output, so the strings are also checked for being DIFFERENT
    from one another."""
    rows = _battery(monkeypatch, tmp_path)
    produced = {r["soc"] for r in rows}
    assert produced == {"active", "off", "partial", "unknown"}, \
        "the battery only produced %r; it proves almost nothing" % sorted(produced)

    for r in rows:
        if r["soc"] == "active":
            assert r["soc_next"] == "", \
                "%s is active and still carries a next action: %r" % (r["service"], r["soc_next"])
            continue
        nxt = r["soc_next"]
        assert isinstance(nxt, str) and len(nxt) >= 12, \
            "%s is %s with no usable next action: %r" % (r["service"], r["soc"], nxt)
        # CONCRETE means it names a thing: the service, an environment variable, a command, or the
        # loop that is stale. A sentence that could be printed for any row is not an action.
        assert any(tok in nxt for tok in (r["service"], "PERSEUS_", "SHIELD", "perseus",
                                          "python fleet.py")), \
            "%s: %r names nothing anybody could act on" % (r["service"], nxt)
        assert "\n" not in nxt and len(nxt) <= 130, \
            "the operator asked for less text, not a paragraph: %r" % nxt

    distinct = {r["soc_next"] for r in rows if r["soc"] in NOT_ACTIVE}
    assert len(distinct) >= 5, \
        "only %d distinct next actions across every non-active state: %r" % (len(distinct), distinct)


def test_every_row_carries_the_field_on_the_degraded_path_too(monkeypatch, tmp_path):
    """No blocklist, no beats, no loops readable: the shape the container runs on a bad day. A
    field that only exists when everything works is a field the operator never sees."""
    _estate(monkeypatch, tmp_path)
    for p in fleet.status()["projects"]:
        assert "soc_next" in p and isinstance(p["soc_next"], str)
        assert p["soc_why"], "a one-word verdict with no reason is unreadable on a bad day"
        assert p["soc_local_by"] in ("shield", "beat")


# ============================================================ 6. status() STILL CANNOT BLOCK OR RAISE

def test_status_makes_no_network_call_and_returns_promptly(monkeypatch, tmp_path, _no_network):
    """THE PAGE MUST NEVER WAIT. Both things that ever took this page down were Loki queries on the
    request path, and the shield measurement added here is in-process by design. The assertion is
    on the CALL, not only on the clock: a timing bound alone would pass on a fast day."""
    _shield(monkeypatch, armed=True)
    _loops(monkeypatch)
    _estate(monkeypatch, tmp_path, rows=[_http("colt-web")],
            beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})
    done, err = [], []

    def run():
        try:
            done.append(fleet.status())
        except Exception as exc:                      # pragma: no cover - reported, not swallowed
            err.append(exc)

    th = threading.Thread(target=run, daemon=True)
    t0 = time.time()
    th.start()
    th.join(20)                                       # generous: this normally runs in milliseconds
    assert not err, "status() raised: %r" % (err[0],)
    assert done, "status() did not return within 20s of a request path that makes no IO"
    assert not _no_network, "status() reached the network: %r" % _no_network[:3]
    assert time.time() - t0 < 20


def test_a_shield_that_raises_cannot_take_the_page_down(monkeypatch, tmp_path):
    """PROVE THE GATE BY BREAKING THE THING IT GUARDS. Without the try inside _shield_facts this
    raises straight through status(), the route renders 'Could not read the fleet status', and the
    Admin page is dead for the third time over an optional lookup."""
    from app import shield

    def boom():
        raise RuntimeError("shield.state blew up")

    monkeypatch.setattr(shield, "state", boom)
    _loops(monkeypatch)
    _estate(monkeypatch, tmp_path, rows=[_http("colt-web")],
            beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})
    st = fleet.status()
    assert len(st["projects"]) == len(fleet.PROJECTS), "the rest of the page must still render"
    assert st["local_shield"]["measured"] is False
    assert "blew up" in (st["local_shield"]["err"] or "")
    assert st["projects"][0]["soc"] in ("unknown", "off", "partial", "active")


def test_status_with_the_MODULE_DEFAULTS_still_answers(monkeypatch):
    """No monkeypatched paths at all: the shape the container actually runs. /var/log/colt does not
    exist on this machine and every read is supposed to degrade to a STATE, never to an exception.
    This is the test whose absence let a 500 ship green three times."""
    fleet._LOKI_CACHE.update(ts=0.0, beats={})
    fleet._LOKI_EVENTS.update(ts=0.0, rows=[], ok=False, partial=False, busy=False)
    st = fleet.status()
    assert isinstance(st["local_shield"], dict)
    for p in st["projects"]:
        assert p["soc"] in ("unknown", "off", "partial", "active"), p
        assert isinstance(p["soc_next"], str)


# ======================================================================= 7. WIRING AND SIX LANGUAGES

def _jsx(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))


def test_the_view_actually_renders_the_next_action():
    """A CONTROL THAT IS CORRECT AND UNREACHABLE IS NOT A CONTROL, and a field nobody has seen on
    screen is off. Asserted on the rendered tree, not on the backend alone."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    assert "p.soc_next" in body, "the backend computes soc_next and the view never reads it"
    assert 't("fleet.socNext")' in body, "the label must come from the catalogue, not from a literal"
    panel = body[body.index("function SocPanel("):]
    assert "p.soc_next" in panel, "it belongs in the SOC panel, beside the verdict it explains"


def test_the_row_still_carries_no_paragraph():
    """The operator: "the too much text is terrible". The reason stays on `title`; the next action
    is ONE line for the whole panel, not a column and not a sentence per row."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    assert "title={p.soc_why}" in body, "the verdict must still carry its reason on title"
    assert '<div className="fleet-why">{p.soc_why}</div>' not in body, \
        "the SOC reason is back as body text; it belongs on title="
    assert '<div className="fleet-why">{p.soc_next}</div>' not in body


def test_the_label_exists_and_is_filled_in_all_six_languages():
    """The build FAILS on a missing key and a raw dotted key on screen looks like content. This is
    the cheap Python mirror of the catalogue gate, in the same suite as the change that added it."""
    for code in LOCALES:
        src = open(os.path.join(LOCALE_DIR, "%s.js" % code), encoding="utf-8").read()
        src = "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))
        m = re.search(r'^\s*"fleet\.socNext"\s*:\s*"([^"]*)"', src, re.M)
        assert m, "locales/%s.js has no fleet.socNext" % code
        assert m.group(1).strip(), "locales/%s.js: fleet.socNext is empty" % code
        assert "—" not in m.group(1), "em dash in %s.js" % code
        assert not re.search(r"&(?:[a-zA-Z]{2,8}|#\d{2,5});", m.group(1)), \
            "HTML entity in %s.js: React escapes it and it ships verbatim" % code


def test_the_measurement_is_written_down_on_every_call(monkeypatch, tmp_path):
    """THE OBSERVER MUST BE OBSERVED. `off` on cybergod went unread because nothing recorded WHY
    the local term was false. A change in that is now a change in Loki, not a discovery on a page.
    """
    seen = []
    monkeypatch.setattr(fleet, "_emit", lambda **k: seen.append(k))
    _shield(monkeypatch, armed=True)
    _loops(monkeypatch)
    _estate(monkeypatch, tmp_path, rows=[_http("colt-web")],
            beats={"colt-web": _beat("colt-web", local=False, enforcing=True)})
    fleet.status()
    assert len(seen) == 1, "one line per call; the page must not become its own traffic"
    e = seen[0]
    assert e["shield_measured"] is True and e["shield_armed"] is True
    assert e["shield_detection"] == "app.perseus_client"
    assert isinstance(e["soc_next_open"], int) and e["soc_next_open"] >= 1
