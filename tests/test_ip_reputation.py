"""A visit from infrastructure is not a person, and a returning actor is one story.

These pin the behaviour the operator asked for after 45.148.10.5 (AS48090 TECHOFF / DMZHOST, a
bulletproof-hosting + VPN /24) triggered "A person just opened cybergod.ai" - from the same block
that had already probed /.env and /aws-ses.json.

Stdlib only. classify() and observe() make NO network call; enrich() is NOT tested against the
live network here (a test that reaches the internet is not testing this repository).
"""
import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "webapp", "backend", "app")


def _rep(store=None):
    if store:
        os.environ["REPUTE_STORE"] = store
    spec = importlib.util.spec_from_file_location("ip_reputation_t",
                                                  os.path.join(APP, "ip_reputation.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_actual_bulletproof_range_is_infrastructure_not_a_person():
    rep = _rep()
    cls = rep.classify("45.148.10.5")
    assert cls["kind"] == "bulletproof", cls
    assert rep.is_infrastructure(cls), "the /24 that probed us is being called a person"
    # the whole /24, not just .5
    assert rep.is_infrastructure(rep.classify("45.148.10.62"))


def test_a_research_scanner_is_named_and_a_residential_ip_is_left_alone():
    rep = _rep()
    assert rep.classify("216.144.248.1")["kind"] == "scanner"
    # a plausible residential address is UNKNOWN offline, and unknown is NOT infrastructure -
    # absence of evidence must never silently drop a real visitor.
    home = rep.classify("84.114.9.20")
    assert home["kind"] == "unknown"
    assert not rep.is_infrastructure(home), "a real visitor would be suppressed"


def test_internal_and_garbage_addresses_do_not_crash_or_flag():
    rep = _rep()
    assert rep.classify("127.0.0.1")["kind"] == "internal"
    assert rep.classify("10.0.0.5")["kind"] == "internal"
    assert rep.classify("not-an-ip")["kind"] == "unknown"
    assert not rep.is_infrastructure(rep.classify("not-an-ip"))


def test_a_returning_actor_is_recognised_across_days_by_its_network():
    work = tempfile.mkdtemp(prefix="rep-")
    try:
        rep = _rep(os.path.join(work, "reputation.json"))
        # two DIFFERENT addresses in the same /24, on two different days
        rep.observe("45.148.10.5", hostile=True, path="/.env", now=1_753_000_000)      # day A
        rep.observe("45.148.10.62", hostile=True, path="/aws-ses.json", now=1_754_000_000)  # day B
        off = rep.repeat_offenders(min_days=2)
        assert len(off) == 1, "the two addresses were not folded into one /24 actor"
        r = off[0]
        assert r["net"] == "45.148.10.0/24"
        assert len(r["days"]) == 2 and r["hostile"] == 2
        assert set(r["ips"]) == {"45.148.10.5", "45.148.10.62"}

        # a single-day scan is NOT a returning actor, however MANY probes it fires in that day.
        # This is the distinction between "returning across days" and "a burst" - the two rules
        # agree on the fixtures above, so without a same-day burst they are indistinguishable.
        for t in range(1_754_100_000, 1_754_100_050, 10):     # 5 hostile hits, all one UTC day
            rep.observe("203.0.113.9", hostile=True, path="/.git", now=t)
        burst = [x for x in rep.repeat_offenders(min_days=2) if x["net"] == "203.0.113.0/24"]
        assert not burst, ("a same-day burst was reported as a returning actor - the rule is "
                           "counting volume, not distinct days")
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def test_a_plain_visit_is_recorded_but_never_counts_as_hostile():
    work = tempfile.mkdtemp(prefix="rep2-")
    try:
        rep = _rep(os.path.join(work, "reputation.json"))
        rep.observe("45.148.10.5", hostile=False, path="/", now=1_753_000_000)
        rep.observe("45.148.10.5", hostile=False, path="/", now=1_754_000_000)
        assert rep.repeat_offenders(min_days=2) == [], "a non-hostile visit became an accusation"
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def test_the_complaint_drafter_produces_a_filable_document_and_sends_nothing():
    work = tempfile.mkdtemp(prefix="rep3-")
    try:
        os.environ["REPUTE_STORE"] = os.path.join(work, "reputation.json")
        rep = _rep(os.environ["REPUTE_STORE"])
        rep.observe("45.148.10.5", hostile=True, path="/.env", now=1_753_000_000)
        rep.observe("45.148.10.62", hostile=True, path="/aws-ses.json", now=1_754_000_000)

        spec = importlib.util.spec_from_file_location("abuse_report_t",
                                                      os.path.join(APP, "abuse_report.py"))
        ar = importlib.util.module_from_spec(spec)
        sys.path.insert(0, APP)
        spec.loader.exec_module(ar)

        r = rep.repeat_offenders(min_days=2)[0]
        text = ar.draft_complaint(r, holder="TECHOFF SRV LIMITED", abuse_email="abuse@x.com")
        assert "45.148.10.0/24" in text
        assert "T1595" in text, "no MITRE technique cited"
        assert "404" in text, "the 'no data was exposed' fact is missing"
        assert "abuse@x.com" in text
        # it is TEXT, not a transmission: nothing in the drafter opens a socket
        src = open(os.path.join(APP, "abuse_report.py"), encoding="utf-8").read()
        draft = src[src.index("def draft_complaint"):src.index("def complaints_for_repeat")]
        for banned in ("urllib", "urlopen", "requests", "socket", "smtp"):
            assert banned not in draft.lower(), \
                "the complaint DRAFTER must not reach the network (found %r)" % banned
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def test_classify_makes_no_network_call():
    """It runs on the request path, so it must never open a socket."""
    src = open(os.path.join(APP, "ip_reputation.py"), encoding="utf-8").read()
    body = src[src.index("def classify("):src.index("def is_infrastructure(")]
    assert "urlopen" not in body and "ripestat" not in body, \
        "classify() reaches the network - it cannot run inline on every request"


def test_visitors_suppresses_the_person_alert_for_infrastructure():
    """The wiring, not just the classifier: note_visit must consult ip_reputation and suppress."""
    src = open(os.path.join(APP, "visitors.py"), encoding="utf-8").read()
    body = "\n".join(l.split("#", 1)[0] for l in src.splitlines())
    assert "ip_reputation" in body and "is_infrastructure" in body, \
        "note_visit does not check whether the visitor is infrastructure"
    assert body.index("is_infrastructure") < body.index("A person just opened"), \
        "the infrastructure check runs AFTER the person alert is composed - too late"
