"""The Fleet page must say what is ENFORCED, not only what is ALIVE -- and it must never print a
number for something it did not measure.

WHY THIS FILE EXISTS. The operator was told, correctly, that the Fleet page is observation and
almost nothing on it is enforcement. The evidence had been on the page for weeks and nobody read it
as a finding: every row said `enforcing cycle 0`. hub.cycle() sets rs["cycle"] to 1 on its FIRST
success, so cycle 0 on all five rows means no nightly cycle has ever completed -> publish() never
wrote a blocklist -> perseus_client.check() has been iterating an EMPTY pattern list on all five
sites since the day it was installed. The page rendered `live` throughout, and `live` was true.
It was answering the wrong question, in a vocabulary that made the right answer look like health.

Two properties are worth more than the rest of this file put together, and both have a named
incident behind them in docs/decisions:

  1. AN UNMEASURED VALUE IS A WORD, NEVER A ZERO. `_cycle()` used to return `patterns: 0` when the
     blocklist file could not be read at all. That is a confident statement ("perseus published
     nothing") manufactured out of our own blindness ("this container cannot see that file"), which
     is the logship defect wearing a dashboard. Every count that could mean "we cannot see" is now
     None, and the view renders None as a translated word.
  2. THE PAGE MUST NOT HANG OR 500. The only two things ever put on this request path were Loki
     queries and the Admin page was dead for both ships. The publish lookup reads a cache; a daemon
     thread fills it; a broken lookup degrades to "no query has completed" instead of a traceback.

tests/test_fleet.py is owned elsewhere and is NOT imported here -- these fixtures are deliberately
independent, so a change to that file cannot silently satisfy an assertion in this one.
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

FLEET_PY = os.path.join(ROOT, "webapp", "backend", "app", "fleet.py")
FLEET_JSX = os.path.join(ROOT, "webapp", "frontend", "src", "pages", "Fleet.jsx")
LOCALE_DIR = os.path.join(ROOT, "webapp", "frontend", "src", "locales")
LOCALES = ("en", "de", "it", "fr", "es", "pl")

# The four badges _status() can put in the `sidecar` column. Kept here as data AND asserted against
# fleet.py below, so this list cannot quietly go stale: a value the backend stops emitting fails the
# test that reads it, rather than leaving a dead translation nobody notices.
SIDECAR_BADGES = ("active", "stale", "not installed", "unverifiable")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """TESTS MUST NOT REACH THE INTERNET. Every path below is supposed to degrade without a Loki;
    a suite that quietly succeeds because a real one answered is measuring the wrong machine."""
    import urllib.request

    def offline(url, timeout=0):
        raise OSError("tests must not reach the internet")

    monkeypatch.setattr(urllib.request, "urlopen", offline)


def _setup(monkeypatch, tmp_path, rows=(), beats=None, blocklist=None):
    """Point the module at a tmp estate AND clear its module-level caches.

    The caches are globals and survive a test, so one case's stubbed answer would silently satisfy
    the next case's assertion -- the cross-test pollution this repository has already paid for once.
    """
    ev = os.path.join(str(tmp_path), "events.log")
    with open(ev, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    bd = os.path.join(str(tmp_path), "beats")
    os.makedirs(bd, exist_ok=True)
    # CLEAR IT. tmp_path is per-TEST, not per-call, and one test below calls _setup five times with
    # different beats. A leftover heartbeat file from the previous case would satisfy the next case's
    # assertion without anybody writing it -- the same cross-test pollution one scope down.
    for stale in os.listdir(bd):
        os.remove(os.path.join(bd, stale))
    for svc, doc in (beats or {}).items():
        with open(os.path.join(bd, "%s.json" % svc), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    bl = os.path.join(str(tmp_path), "blocklist.json")
    if blocklist is None:
        if os.path.exists(bl):
            os.remove(bl)
    elif isinstance(blocklist, str):
        with open(bl, "w", encoding="utf-8") as fh:       # a deliberately corrupt document
            fh.write(blocklist)
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


def _rows(monkeypatch, tmp_path, **kw):
    _setup(monkeypatch, tmp_path, **kw)
    return {p["service"]: p for p in fleet.status()["projects"]}


def _http(service, path="/", status=200, ip="203.0.113.9", ts=None):
    return {"evt": "http", "service": service, "ip": ip, "path": path, "status": status,
            "ts": int(ts or time.time())}


def _beat(service, cycle, age_s=5):
    return {"service": service, "ts": int(time.time()) - age_s, "cycle": cycle, "checks": 12}


# ============================================================ 1. THE BLOCKLIST: ONE READER, NO ZEROS

def test_an_unreadable_blocklist_reports_UNKNOWN_rules_and_never_zero(monkeypatch, tmp_path):
    """THE DEFECT THIS WHOLE FILE IS ABOUT. `patterns: 0` on the failure path is a statement about
    perseus assembled out of our own inability to open a file. Three states -- not mounted, corrupt,
    genuinely empty -- collapsed into one number that reads as the third."""
    _setup(monkeypatch, tmp_path, blocklist=None)
    c = fleet._cycle()
    assert c["readable"] is False
    assert c["patterns"] is None, "an unread file has no rule count, and %r is not None" % c["patterns"]
    assert c["cycle"] is None
    assert c["age_s"] is None
    assert c["enforcing"] is False
    assert c["err"], "the page must be able to say WHY it could not read it, not only that it did not"
    assert c["path"], "a diagnostic that does not name its subject sends the next person elsewhere"


def test_a_corrupt_blocklist_is_unreadable_not_empty(monkeypatch, tmp_path):
    """Half a JSON document is not a published ruleset with no rules in it."""
    _setup(monkeypatch, tmp_path, blocklist='{"cycle": 4, "patterns": [')
    c = fleet._cycle()
    assert c["readable"] is False and c["patterns"] is None and c["enforcing"] is False


def test_a_patterns_key_that_is_not_a_list_is_not_a_count(monkeypatch, tmp_path):
    """len() on a dict returns a plausible number for a document we did not understand, and a
    plausible wrong figure is worse than the honest blank it replaced."""
    _setup(monkeypatch, tmp_path, blocklist={"cycle": 4, "patterns": {"a": 1, "b": 2}})
    c = fleet._cycle()
    assert c["readable"] is True, "the file parsed; that part IS known"
    assert c["patterns"] is None, "a dict is not a rule list, so its length is not a rule count"


def test_a_real_blocklist_reports_real_numbers(monkeypatch, tmp_path):
    """The other half of rule 1: a value we DID measure must survive intact, including a zero."""
    _setup(monkeypatch, tmp_path,
           blocklist={"cycle": 4, "patterns": [{"id": "r1", "pattern": "/x"},
                                               {"id": "r2", "pattern": "/y"}]})
    c = fleet._cycle()
    assert c["readable"] is True and c["cycle"] == 4 and c["patterns"] == 2
    assert c["enforcing"] is True
    assert isinstance(c["age_s"], int) and c["age_s"] >= 0


def test_cycle_zero_and_an_empty_ruleset_both_enforce_nothing(monkeypatch, tmp_path):
    """`enforcing` is the operator's question, answered in ONE place so no caller re-derives it.
    A cycle that never completed and a cycle that armed no rules block exactly the same amount."""
    _setup(monkeypatch, tmp_path, blocklist={"cycle": 0, "patterns": [{"id": "r", "pattern": "/x"}]})
    assert fleet._cycle()["enforcing"] is False, "cycle 0 means no run ever completed"
    _setup(monkeypatch, tmp_path, blocklist={"cycle": 9, "patterns": []})
    c = fleet._cycle()
    assert c["enforcing"] is False and c["patterns"] == 0, "a MEASURED zero must still be a zero"


# ====================================================== 2. PER PROJECT: IS ANYTHING ENFORCED HERE?

def test_a_beating_sidecar_on_cycle_0_is_reported_as_enforcing_NOTHING(monkeypatch, tmp_path):
    """THE STATE THE ESTATE IS ACTUALLY IN. The client's cache initialises to cycle 0 and only moves
    when it has read a published blocklist, so a beat carrying 0 is the sidecar saying it has never
    loaded a ruleset. The row used to read `live` + `enforcing cycle 0` and looked like health."""
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", 0)})["colt-web"]
    assert r["state"] == "live" and r["sidecar"] == "active", "liveness is unchanged and still true"
    assert r["enforce"] == "none"
    assert r["enforce_cycle"] == 0
    assert r["enforce_patterns"] is None, "there is no rule count for a ruleset that was never loaded"
    assert "blocks NOTHING" in r["why"], \
        "the row must say it enforces nothing, in words: %r" % r["why"]


def test_a_project_with_no_heartbeat_reports_UNKNOWN_enforcement(monkeypatch, tmp_path):
    """Absence of evidence is never a finding. No beat means we cannot see what it runs; it does not
    mean it runs nothing."""
    r = _rows(monkeypatch, tmp_path, rows=[_http("jhw-web")])["jhw-web"]
    assert r["enforce"] == "unknown"
    assert r["enforce_cycle"] is None and r["enforce_patterns"] is None
    # `why` describes the LIVENESS state and for an unguarded project it talks about the missing
    # heartbeat. `enforce_why` is the sentence about ENFORCEMENT and every row carries one, which
    # is the point of shipping it as its own field rather than splicing it into `why` everywhere.
    assert "UNKNOWN" in r["enforce_why"], r["enforce_why"]
    assert "UNGUARDED" in r["why"], "the liveness sentence is unchanged"


def test_a_loaded_ruleset_with_rules_in_it_is_the_only_ACTIVE_state(monkeypatch, tmp_path):
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", 4)},
              blocklist={"cycle": 4, "patterns": [{"id": "a", "pattern": "/x"},
                                                  {"id": "b", "pattern": "/y"},
                                                  {"id": "c", "pattern": "/z"}]})["colt-web"]
    assert r["enforce"] == "active"
    assert r["enforce_cycle"] == 4 and r["enforce_patterns"] == 3
    assert "3 blocking rules" in r["why"]


def test_a_loaded_ruleset_containing_no_rules_is_drawn_apart_from_an_active_one(monkeypatch, tmp_path):
    """A cycle DID complete, and it armed nothing. That is a different fact from cycle 0 and from an
    unreadable file, and the count is a measured zero rather than a blank."""
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", 7)},
              blocklist={"cycle": 7, "patterns": []})["colt-web"]
    assert r["enforce"] == "empty"
    assert r["enforce_patterns"] == 0 and isinstance(r["enforce_patterns"], int)


def test_a_rule_count_is_never_taken_from_a_DIFFERENT_cycle(monkeypatch, tmp_path):
    """The beat is authoritative about what a project LOADED; the file is authoritative about what a
    cycle ARMED. Combining them across two different cycles produces a number about something else,
    and a number about something else is this page's whole failure mode."""
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", 3)},
              blocklist={"cycle": 8, "patterns": [{"id": "a", "pattern": "/x"}]})["colt-web"]
    assert r["enforce"] == "armed", "cycle 3 loaded, cycle 8 published: they are not the same document"
    assert r["enforce_patterns"] is None, "1 is the count for cycle 8, which this project is not running"
    assert r["enforce_cycle"] == 3


def test_a_missing_blocklist_leaves_the_rule_count_unknown_not_zero(monkeypatch, tmp_path):
    r = _rows(monkeypatch, tmp_path,
              rows=[_http("colt-web")],
              beats={"colt-web": _beat("colt-web", 3)},
              blocklist=None)["colt-web"]
    assert r["enforce"] == "armed" and r["enforce_patterns"] is None


# ================================================ 3. WOULD AN ATTACK ON THIS PROJECT REACH ANYONE?

def test_alerting_coverage_is_stated_per_project(monkeypatch, tmp_path):
    """watch() pages from exactly the rows this page counts, so coverage is not a new measurement --
    it is the live/silent distinction said in the vocabulary the operator asked the question in."""
    rows = _rows(monkeypatch, tmp_path, rows=[_http("colt-web"), _http("jhw-web")])
    assert rows["colt-web"]["alerting"] == "self", "cybergod runs the rules and the notifier itself"
    assert rows["jhw-web"]["alerting"] == "covered", "its lines reach colt-web, which pages"
    assert rows["jev-web"]["alerting"] == "blind", \
        "nothing carries jev's lines here, so an attack on it pages nobody"


def test_an_own_log_project_is_BLIND_only_when_that_is_provable(monkeypatch, tmp_path):
    """THE HALF THAT IS EASY TO GET WRONG. This page reads a NON-BLOCKING cache; watch() waits for
    the same query. So an empty cache here proves nothing about the alerting loop -- unless the
    lookup is switched OFF, in which case _loki_events returns nothing to EVERY caller including the
    blocking one, and 'blind' is a deduction rather than a description of our own cold cache."""
    off = _rows(monkeypatch, tmp_path, rows=[_http("colt-web")])
    assert off["polara-web"]["alerting"] == "blind", \
        "with the traffic lookup off, watch() gets nothing either: that IS provable"

    _setup(monkeypatch, tmp_path, rows=[_http("colt-web")])
    monkeypatch.setattr(fleet, "LOKI_EVENTS_ON", True)
    on = {p["service"]: p for p in fleet.status()["projects"]}
    assert on["polara-web"]["alerting"] == "unknown", \
        "with the lookup on, a cold cache here is OUR blind spot, not the project's"


# ============================================================== 4. WHAT WAS ACTUALLY REFUSED, IF ANY

def test_refusals_are_counted_only_where_the_lines_can_be_read(monkeypatch, tmp_path):
    """A 0 in an enforcement column reads as 'the defence ran and nothing got past'. For a project
    whose log we cannot open, that is manufactured reassurance."""
    now = int(time.time())
    rows = _rows(monkeypatch, tmp_path, rows=[
        _http("colt-web", "/.env", 429, ts=now),
        _http("colt-web", "/wp-login.php", 429, ts=now),
        _http("colt-web", "/", 200, ts=now),
        {"evt": "shield_block", "service": "colt-web", "ip": "45.148.10.5", "ts": now},
    ])
    c = rows["colt-web"]
    assert c["refused_429_24h"] == 2, "429 is the only answer perseus_client gives when it denies"
    assert c["refused_shield_24h"] == 1
    assert c["refused_24h"] == 3
    assert rows["jev-web"]["refused_24h"] is None, \
        "we read no line at all from jev, so 'nothing was refused' is not a thing we know"
    assert rows["jev-web"]["refused_429_24h"] is None
    assert rows["colt-web"]["requests_24h"] == 3, "the refusals are still requests"


def test_a_readable_project_with_no_refusals_reports_a_real_zero(monkeypatch, tmp_path):
    """The mirror image, and the reason `None` and `0` must both exist: we counted, and it was 0."""
    rows = _rows(monkeypatch, tmp_path, rows=[_http("colt-web", "/", 200)])
    assert rows["colt-web"]["refused_24h"] == 0
    assert isinstance(rows["colt-web"]["refused_24h"], int)


# =========================================================== 5. HAS THE BRAIN RUN? (evt=perseus_publish)

def test_the_publish_lookup_says_OFF_rather_than_reporting_zero_runs(monkeypatch, tmp_path):
    """'We did not ask' and 'we asked and there were none' are different facts. Only one of them is
    a finding about perseus."""
    _setup(monkeypatch, tmp_path)
    p = fleet._publish()
    assert p["lookup"] == "off"
    assert p["runs"] is None and p["ok"] is None and p["failed"] is None
    assert p["lookback_h"] >= 1, "the sentence has to be able to name its own window"


def test_a_loki_that_does_not_answer_is_not_a_brain_that_did_not_run(monkeypatch, tmp_path):
    """Reading a dead query as innocence is defect class 1, and this repository has done it before
    (whodunit read an empty Loki result as proof that nobody spent anything)."""
    _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(fleet, "_loki_fetch", lambda flt, start, limit: ([], False))
    fleet._publish_now()
    v = fleet._PUBLISH["val"]
    assert v["lookup"] == "no_answer"
    assert v["runs"] is None, "an unanswered query has no count, and %r is one" % v["runs"]
    assert fleet._PUBLISH["busy"] is False, "a refresh must release its own in-flight flag"


def test_an_answering_loki_with_no_publish_lines_IS_a_finding(monkeypatch, tmp_path):
    """The other side of the same coin, and the headline the operator needed: Loki answered, and it
    holds no publish line at all. THAT is a measured zero and it means the brain has never run."""
    _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(fleet, "_loki_fetch", lambda flt, start, limit: ([{"evt": "http"}], True))
    fleet._publish_now()
    v = fleet._PUBLISH["val"]
    assert v["lookup"] == "ok"
    assert v["runs"] == 0, "Loki answered; zero publish lines is a fact, not a blank"
    assert v["ok"] == 0 and v["failed"] == 0


def test_publish_runs_are_counted_and_failures_are_not_hidden(monkeypatch, tmp_path):
    """publish() prints on BOTH paths precisely so a silent failure is distinguishable from a silent
    success. Summing them into one 'runs' number would throw that away again."""
    _setup(monkeypatch, tmp_path)
    lines = [
        {"evt": "perseus_publish", "ok": True, "cycle": 3, "patterns": 11},
        {"evt": "perseus_publish", "ok": True, "cycle": 4, "patterns": 12},
        {"evt": "perseus_publish", "ok": False, "err": "PermissionError(13)"},
        {"evt": "http", "service": "colt-web"},
    ]
    monkeypatch.setattr(fleet, "_loki_fetch", lambda flt, start, limit: (lines, True))
    fleet._publish_now()
    v = fleet._PUBLISH["val"]
    assert v["runs"] == 3 and v["ok"] == 2 and v["failed"] == 1
    assert v["cycle"] == 4, "the highest cycle a SUCCESSFUL publish reported"
    assert "PermissionError" in (v["err"] or ""), "the failure has to carry its own cause"


def test_the_publish_query_asks_for_the_event_the_hub_actually_prints():
    """A filter that matches nothing fails silently and looks exactly like innocence. Anchored on
    the call site in fleet.py AND on the print in hub.py, so the two cannot drift apart."""
    src = _code(open(FLEET_PY, encoding="utf-8").read())
    assert 'perseus_publish' in src, "fleet.py no longer filters on the event the hub prints"
    hub = open(os.path.join(ROOT, "perseus", "hub.py"), encoding="utf-8").read()
    assert '"evt": "perseus_publish"' in hub, \
        "the hub renamed its event; fleet.py's line filter now matches nothing, silently"


# ================================================================= 6. THE PAGE MUST NOT HANG OR 500

def test_the_publish_lookup_never_runs_on_the_request_thread(monkeypatch, tmp_path):
    """A STATUS PAGE THAT HANGS IS ITS OWN OUTAGE. The Admin page was dead for two whole ships
    because a Loki query sat on this path. The request thread reads a cache and returns; a daemon
    thread does the fetch. Proven by identity of the thread that runs it, not by a stopwatch --
    a timing assertion is a coin flip that teaches the operator to re-run rather than read."""
    _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(fleet, "LOKI_PUBLISH_ON", True)
    started, where = threading.Event(), {}

    def spy():
        where["ident"] = threading.current_thread().ident
        started.set()

    monkeypatch.setattr(fleet, "_publish_now", spy)
    out = fleet._publish()                       # the request path
    assert out["lookup"] == "pending" and out["runs"] is None, \
        "a cold cache must render as 'no query has completed', never as zero runs"
    assert started.wait(5), "the background refresh never started at all"
    assert where["ident"] != threading.current_thread().ident, \
        "the fetch ran on the caller's thread: that is the hang, restored"


def test_a_broken_publish_lookup_cannot_500_the_page(monkeypatch, tmp_path):
    """PROVE THE GATE BY BREAKING THE THING IT GUARDS. Without the try in _status() this raises
    straight through status(), the route renders 'Could not read the fleet status', and three deploy
    cycles get spent guessing -- which is exactly what happened the last two times."""
    _setup(monkeypatch, tmp_path, rows=[_http("colt-web")])

    def boom(block=False):
        raise RuntimeError("the publish lookup exploded")

    monkeypatch.setattr(fleet, "_publish", boom)
    st = fleet.status()
    assert st["projects"], "the rest of the page must still render"
    assert st["publish_evt"]["lookup"] == "pending"
    assert st["publish_evt"]["runs"] is None
    assert "exploded" in (st["publish_evt"]["err"] or ""), \
        "the cause must travel in the payload instead of into a traceback"


def test_a_blocklist_that_cannot_be_read_cannot_break_the_page(monkeypatch, tmp_path):
    """Every enforcement claim on the page comes from one file read. It must degrade, never raise."""
    _setup(monkeypatch, tmp_path, rows=[_http("colt-web")],
           blocklist='{"cycle": ')                      # a truncated document, mid-write
    st = fleet.status()
    assert len(st["projects"]) == len(fleet.PROJECTS)
    assert st["published"]["patterns"] is None
    assert all(p["enforce"] in ("unknown", "none", "armed", "empty", "active")
               for p in st["projects"])


def test_status_with_the_MODULE_DEFAULTS_still_answers_with_the_soc_fields(monkeypatch):
    """No monkeypatched paths: the shape the container actually runs. /var/log/colt does not exist
    on this machine, and every one of those reads is supposed to degrade to a STATE, never to an
    exception. This is the test whose absence let a 500 ship green three times."""
    fleet._LOKI_CACHE.update(ts=0.0, beats={})
    fleet._LOKI_EVENTS.update(ts=0.0, rows=[], ok=False, partial=False, busy=False)
    st = fleet.status()
    assert st["published"]["patterns"] is None, "no blocklist here, so no rule count"
    assert isinstance(st["enforcing"], int) and st["enforcing"] == 0
    assert st["tarpit_recorded"] is False
    assert st["publish_evt"]["lookup"] in ("off", "pending", "no_answer", "ok")
    for p in st["projects"]:
        assert p["enforce"] in ("unknown", "none", "armed", "empty", "active"), p
        assert p["alerting"] in ("self", "covered", "unknown", "blind"), p
        assert p["enforce_why"], "every row must carry its own reason on the degraded path too"


def test_the_fleet_totals_separate_GUARDED_from_ENFORCING(monkeypatch, tmp_path):
    """`5 guarded` sat above five rows that blocked nothing, and it was not wrong -- it was
    answering a different question. Both numbers now exist, and they disagree on purpose."""
    _setup(monkeypatch, tmp_path,
           rows=[_http("colt-web"), _http("jhw-web")],
           beats={"colt-web": _beat("colt-web", 0), "jhw-web": _beat("jhw-web", 0)})
    st = fleet.status()
    assert st["guarded"] == 2, "two sidecars are beating"
    assert st["enforcing"] == 0, "...and neither of them is enforcing a single rule"
    assert st["alerting_blind"] >= 1
    assert st["enforce_unknown"] == 3, "the three projects with no heartbeat are UNKNOWN, not zero"


def test_the_page_reports_its_own_soc_state_on_every_call(monkeypatch, tmp_path):
    """THE OBSERVER MUST BE OBSERVED. `enforcing` moving from 0 to 5 is the most important state
    change on this estate; discovering it by opening a page is how it stayed at 0 for weeks."""
    seen = []
    monkeypatch.setattr(fleet, "_emit", lambda **k: seen.append(k))
    _setup(monkeypatch, tmp_path, rows=[_http("colt-web")],
           beats={"colt-web": _beat("colt-web", 0)})
    fleet.status()
    assert len(seen) == 1
    e = seen[0]
    assert sum(e["enforce"].values()) == len(fleet.PROJECTS), "the histogram must cover every row"
    assert e["enforce"]["none"] == 1 and e["enforce"]["unknown"] == 4
    assert sum(e["alerting"].values()) == len(fleet.PROJECTS)
    assert e["published_patterns"] is None and e["published_readable"] is False
    assert e["publish_lookup"] == "off" and e["publish_runs"] is None


def test_the_tarpit_is_declared_NOT_DETERMINABLE_rather_than_counted():
    """shield.decide() returns TARPIT and telemetry.py sleeps on it. NEITHER writes an event, so no
    log this page can read holds a tarpit. Rendering a 0 would be an invented finding; the page says
    so in words. Asserted against shield.py, so adding such an event fails this test loudly."""
    sh = _code(open(os.path.join(ROOT, "webapp", "backend", "app", "shield.py"),
                    encoding="utf-8").read())
    assert not re.search(r'_ev\(\s*"[a-z_]*tarpit', sh), \
        "shield.py now emits a tarpit event: count it, and drop the disclaimer from the page"
    fl = _code(open(FLEET_PY, encoding="utf-8").read())
    assert '"tarpit_recorded": False' in fl, \
        "the disclaimer flag must come from the backend, so one edit removes it"


# ==================================================================== 7. WIRING: THE VIEW AND THE UI

def _code(src):
    """PYTHON with its comments AND its docstrings removed.

    A check in this repository has matched its own explanatory comment five separate times, and the
    comments and docstrings in fleet.py quote every identifier these tests look for. The docstrings
    go too: defect class 4 says comments AND docstrings, and it says so because grepping a docstring
    proved a rule that the code did not implement.

    It deliberately does NOT strip /* */ -- that is JavaScript syntax, and a Python file containing
    a regex with a slash-star in it would have a chunk silently deleted, which makes a `not
    re.search(...)` assertion pass for the wrong reason. Different language, different function."""
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))


def _jsx(src):
    """JAVASCRIPT with its // lines and its /* */ blocks removed, for the same reason."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))


def test_the_view_renders_every_unmeasurable_value_through_the_unknown_helper():
    """A view that prints `{p.refused_24h}` renders `null` as an empty cell, which looks like a
    rendering fault, or `0` if anyone ever 'fixes' it with `?? 0` -- and that fix is the original
    defect restored. n() is the ONE place the null-to-word conversion happens."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    assert "function SocPanel(" in body, "the panel is gone; the rest of this test proves nothing"
    panel = body[body.index("function SocPanel("):]
    for field in ("enforce_cycle", "enforce_patterns", "refused_24h"):
        assert re.search(r"\bn\(p\.%s,\s*t\)" % field, panel), \
            "p.%s must go through n(), or an unmeasured value renders as a number" % field
    for name in ("pubCycle", "pubPatterns"):
        assert re.search(r"\bn\(%s,\s*t\)" % name, panel), "%s must go through n()" % name
    assert "agoOr(pubAge, t)" in panel, "an unknown age must be a word, not the dash used for '0s'"
    assert "?? 0" not in panel, "coalescing an unmeasured value to zero is the whole defect"


def test_the_blocklist_numbers_are_gated_on_the_readable_flag():
    """THE ROUTE'S OWN ERROR PATH SENDS `patterns: 0` WITH NO `readable`. main.py builds that
    fallback when status() throws, and it is a number for something nobody measured. A panel that
    read pub.patterns directly would print "blocking rules: 0" directly underneath its own banner
    saying the file could not be read -- two halves of one screen disagreeing, which is how a raw
    enum once reached a customer slide."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    panel = body[body.index("function SocPanel("):]
    assert "const readable = pub.readable === true;" in panel, \
        "presence of a value is not evidence it was measured; the flag says which"
    for name, field in (("pubCycle", "cycle"), ("pubPatterns", "patterns"), ("pubAge", "age_s")):
        assert re.search(r"const %s = readable \? pub\.%s : null;" % (name, field), panel), \
            "%s must be null unless the backend says the blocklist was READ" % name


def test_the_unknown_helper_keeps_a_measured_zero_as_a_zero():
    """The other half. If n() used a falsy test, `0` would print as 'unknown' and the page would
    hide the one number that matters most: zero rules, actually measured."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    fn = body[body.index("function n(v, t)"):]
    fn = fn[:fn.index("}")]
    assert "=== null" in fn and "=== undefined" in fn, \
        "n() must test for null/undefined explicitly; a falsy test swallows a measured 0"
    assert "String(v)" in fn


def test_the_panel_is_reachable_from_the_view_the_gate_renders():
    """FleetView is deliberately separated from the fetch so a fixture can prove it. A panel that is
    correct and unrendered is not a panel -- a control that is correct and unreachable is not a
    control, one layer up."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    assert "export function FleetView(" in body, "the gate renders FleetView; keep it exported"
    assert "<SocPanel" in body, "the panel is defined and never rendered"
    assert body.index("export function FleetView(") < body.index("<SocPanel"), \
        "SocPanel must hang off FleetView's tree, not off the fetching default export"


# ====================================================================== 8. SIX LANGUAGES, ENFORCED

def _locale_keys(code):
    """Presence of a dotted key, read from the file's TEXT.

    Deliberately not a JS parse: these files are ES modules with comments and the only question
    asked here is whether the key is defined, one per line, which a line-anchored regex answers
    without a Node toolchain the operator's Windows box may not have."""
    src = open(os.path.join(LOCALE_DIR, "%s.js" % code), encoding="utf-8").read()
    src = "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))
    return set(re.findall(r'^\s*"([A-Za-z0-9_.]+)"\s*:', src, re.M))


def _tone_map(body, name):
    m = re.search(r"const %s = \{([^}]*)\}" % name, body)
    assert m, "%s is gone from Fleet.jsx" % name
    return set(re.findall(r"(\w+)\s*:", m.group(1)))


def test_every_string_the_panel_renders_exists_in_all_six_languages():
    """The build FAILS on a missing key and a raw dotted key on screen looks like content, so this
    is the cheap Python mirror of tools/i18n_catalogue.mjs --check: it runs without node, on the
    operator's machine, in the same suite as the backend change that introduced the keys.

    The COMPOSED keys (`"fleet.e." + p.enforce`) are derived from the tone maps rather than typed
    out again here, because counting the wiring points by hand is how the fourth one gets missed."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    need = set(re.findall(r't\(\s*"([A-Za-z0-9_.]+)"\s*\)', body))
    for k in _tone_map(body, "ETONE"):
        need.add("fleet.e." + k)
    for k in _tone_map(body, "ATONE"):
        need.add("fleet.a." + k)
        need.add("fleet.a." + k + "Why")
    for k in _tone_map(body, "TONE"):
        need.add("fleet.s." + k)
    assert len(need) > 30, "the key sweep found almost nothing; the regex has stopped matching"

    for code in LOCALES:
        have = _locale_keys(code)
        missing = sorted(k for k in need if k not in have)
        assert not missing, "locales/%s.js is missing %d key(s): %s" % (
            code, len(missing), ", ".join(missing[:12]))


def test_every_sidecar_badge_the_backend_can_emit_has_a_label(monkeypatch, tmp_path):
    """THE BUG THIS CAUGHT. `unverifiable` has been produced by _status() since the own-log projects
    got their own badge and NO locale carried the key, so that cell printed the raw string
    `fleet.sc.unverifiable` on the live admin page. The composed key hid it from every regex sweep
    over t("literal") calls."""
    src = _code(open(FLEET_PY, encoding="utf-8").read())
    for badge in SIDECAR_BADGES:
        assert '"%s"' % badge in src, \
            "_status() no longer emits the %r badge; this list is stale" % badge
    for code in LOCALES:
        have = _locale_keys(code)
        for badge in SIDECAR_BADGES:
            key = "fleet.sc." + badge.replace(" ", "_")
            assert key in have, "locales/%s.js has no label for the %r badge" % (code, badge)


def test_the_view_knows_every_enum_the_backend_can_emit(monkeypatch, tmp_path):
    """An enum value with no tone and no label renders a raw key. The exact sets are written down
    here AND checked against what a battery of real fixtures actually produces, because a hardcoded
    list on its own only proves that somebody typed it."""
    body = _jsx(open(FLEET_JSX, encoding="utf-8").read())
    assert _tone_map(body, "ETONE") == {"unknown", "none", "armed", "empty", "active"}
    assert _tone_map(body, "ATONE") == {"self", "covered", "unknown", "blind"}

    produced_e, produced_a = set(), set()
    cases = [
        dict(rows=[_http("colt-web")], beats={}, blocklist=None),
        dict(rows=[_http("colt-web")], beats={"colt-web": _beat("colt-web", 0)}, blocklist=None),
        dict(rows=[_http("colt-web")], beats={"colt-web": _beat("colt-web", 2)}, blocklist=None),
        dict(rows=[_http("colt-web")], beats={"colt-web": _beat("colt-web", 2)},
             blocklist={"cycle": 2, "patterns": []}),
        dict(rows=[_http("colt-web"), _http("jhw-web")],
             beats={"colt-web": _beat("colt-web", 2)},
             blocklist={"cycle": 2, "patterns": [{"id": "a", "pattern": "/x"}]}),
    ]
    for kw in cases:
        for p in _rows(monkeypatch, tmp_path, **kw).values():
            produced_e.add(p["enforce"])
            produced_a.add(p["alerting"])
    assert produced_e <= _tone_map(body, "ETONE"), "the backend emits %r, the view has no tone for it" % (
        produced_e - _tone_map(body, "ETONE"))
    assert produced_a <= _tone_map(body, "ATONE")
    # ...and the battery must actually be worth something: five enforcement states exist and this
    # loop is supposed to have walked most of them, not repeated one.
    assert len(produced_e) >= 4, "the fixtures only produced %r; they prove almost nothing" % produced_e


def test_no_new_string_carries_an_html_entity_or_an_em_dash():
    """React ESCAPES a string that reaches the DOM through t(), so `&rsquo;` is printed verbatim --
    it shipped that way once, in five locale files at the same time. The em dash is banned outright
    in copy a customer can see."""
    for code in LOCALES:
        src = open(os.path.join(LOCALE_DIR, "%s.js" % code), encoding="utf-8").read()
        for line in src.splitlines():
            if not re.match(r'^\s*"(fleet\.(soc|e\.|a\.|bl|pub|col|sc\.'
                            r'|unknown|tarpit|enforcingN|alertBlindN))', line):
                continue
            assert not re.search(r"&(?:[a-zA-Z]{2,8}|#\d{2,5});", line), \
                "HTML entity in %s.js: %s" % (code, line.strip()[:90])
            assert "—" not in line, "em dash in %s.js: %s" % (code, line.strip()[:90])
