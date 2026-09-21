"""Does the client's behaviour agree with the client's claim -- and does that answer stay LABELLING?

WHAT WAS MEASURED BEFORE ANY OF THIS WAS WRITTEN:
  * `fleet.status()` computed VISITORS as `len(set(ip))` over every `evt=http` line and never read
    the `bot` field sitting in the same record, so one `curl` was one visitor on the admin page.
  * `perseus/client.py::observe()` wrote a NARROWER line than colt-web's telemetry and carried no
    `bot` field at all, so any consumer asking `not e.get("bot")` read four entire projects as
    human.
  * the estate's only bot signal was `telemetry.classify_ua()`, a substring match on an
    attacker-controlled header, in a codebase whose own doctrine says the PATH is the evidence.

THE DANGEROUS HALF OF THIS CHANGE IS NOT THE DETECTION, IT IS THE TEMPTATION. A new signal about
who is hostile sits one line away from a new reason to refuse somebody, and refusing a real person
is the most expensive mistake this repository has made. So the tests below are in two groups:
the ones that check the arithmetic, and the ones that check it can never become enforcement. The
second group asserts PROPERTIES -- an address that contradicted itself a hundred times is still
ALLOWed by the shield, the module cannot name a firewall, the verdict object has no field a caller
could read as a decision -- rather than grepping for the word "block", because a check that matches
its own explanatory comment has happened five separate times in this repo already.
"""
import ast
import io
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
sys.path.insert(0, ROOT)

from app import client_truth as ct          # noqa: E402
from app import fleet                       # noqa: E402
from app import telemetry                   # noqa: E402

CLIENT_SRC = os.path.join(ROOT, "perseus", "client.py")
TELEMETRY_SRC = os.path.join(ROOT, "webapp", "backend", "app", "telemetry.py")
CT_SRC = os.path.join(ROOT, "webapp", "backend", "app", "client_truth.py")

# Real, current, unremarkable user agents. Copied from live lines rather than invented, because a
# UA I make up is a UA I will unconsciously make easy to classify.
UA_CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/131.0.0.0 Safari/537.36")
UA_FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
UA_EDGE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
           "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0")
UA_SAFARI_17 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Version/17.2 Safari/605.1.15")
UA_SAFARI_15 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Version/15.6 Safari/605.1.15")
UA_CHROME_OLD = ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) "
                 "Chrome/49.0.2623.112 Safari/537.36")
UA_CURL = "curl/8.5.0"

FULL_SF = ct.SF_SITE | ct.SF_MODE | ct.SF_DEST | ct.SF_CHUA


def _read(p):
    with io.open(p, "r", encoding="utf-8") as fh:
        return fh.read()


def _ev(**kw):
    """One `evt=http` record in the shape BOTH emitters write."""
    ev = {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "203.0.113.9",
          "method": "GET", "path": "/", "status": 200, "ua": UA_CHROME, "bot": False,
          "hv": "1.1", "hvs": ct.HV_FROM_HOP, "sf": FULL_SF}
    ev.update(kw)
    return {k: v for k, v in ev.items() if v is not _ABSENT}


class _Absent(object):
    pass


_ABSENT = _Absent()

# Four probe shapes, none of them a honeytoken and none of them one of our own routes, so the
# arithmetic is exactly probe_path x 3: two paths reach TARPIT, four reach BLOCK. Copied from
# test_perseus_shield.py, where the numbers are derived and explained.
PROBES = ("/.env", "/.git/config", "/phpmyadmin/", "/xmlrpc.php")
_ANON_PROBE = "198.51.100.90"


@pytest.fixture
def pc(tmp_path, monkeypatch):
    """perseus/client.py with its memory cleared and all three write paths inside tmp_path.

    REDIRECTING THE WRITES IS NOT TIDINESS: EVENTS and BEAT_DIR default to /var/log/colt/..., which
    on the operator's Windows box resolves to C:\\var\\log\\colt and would be CREATED. Same fixture
    as test_perseus_shield.py, restated rather than imported so this file runs on its own -- ship.py
    invokes it as part of the blocking active-defence gate.
    """
    import perseus.client as m
    monkeypatch.setattr(m, "EVENTS", str(tmp_path / "events.log"))
    monkeypatch.setattr(m, "BEAT_DIR", str(tmp_path / "beats"))
    monkeypatch.setattr(m, "BLOCKLIST", str(tmp_path / "no-such-blocklist.json"))
    monkeypatch.setattr(m, "LOCAL", True)
    monkeypatch.setattr(m, "ENFORCE", True)
    monkeypatch.setattr(m, "ENABLED", True)
    pools = (m._hits, m._fps, m._blocked, m._seen_ips, m._miss, m._slow,
             m._served, m._authed, m._recent, m._told)
    for d in pools:
        d.clear()
    m._tarpits[0] = 0
    m._catchall[0] = False
    m._CACHE["beat"] = time.time()
    m._CACHE["warned"] = False
    m._CACHE["thresholds"] = {}
    m._CACHE["loaded"] = time.time()
    yield m
    for d in pools:
        d.clear()
    m._tarpits[0] = 0
    m._catchall[0] = False


def _feed(m, ip, paths, status=404, ua=UA_CHROME):
    for p in paths:
        m.watch(ip, p, status, ua, "GET")


def _events(m):
    """Every record written to the redirected event log, as parsed JSON."""
    if not os.path.exists(m.EVENTS):
        return []
    out = []
    for line in _read(m.EVENTS).splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


# =================================================================================================
# GROUP 1 -- THE ARITHMETIC
# =================================================================================================

def test_a_browser_shaped_request_records_no_contradiction():
    """h2-capable UA, the full fetch-metadata set, nothing to complain about. This is the case that
    must NOT fire, and it is written first: a check whose false-positive case is an afterthought
    has already decided which way it will be wrong."""
    for ua in (UA_CHROME, UA_FIREFOX, UA_EDGE, UA_SAFARI_17):
        v = ct.evaluate(_ev(ua=ua))
        assert v.reasons == (), "%s was flagged: %r" % (ua[:40], v.reasons)
        assert v.determinable is True


def test_a_chrome_user_agent_with_no_fetch_metadata_at_all_contradicts_itself():
    """Chrome has sent Sec-Fetch-Site/Mode/Dest on every navigation since 76 (Aug 2019). A client
    claiming Chrome 131 and sending none of them is not Chrome 131."""
    v = ct.evaluate(_ev(sf=0))
    assert ct.REASON_NO_FETCH_METADATA in v.reasons
    assert v.determinable is True


def test_one_fetch_metadata_header_is_enough_to_clear_the_claim():
    """DELIBERATELY GENEROUS. The contradiction is 'sent NONE of them', not 'sent fewer than three'.
    A middlebox that strips one header is a thing that happens; a client that sends one of the three
    is not a Python script that has never heard of them."""
    for bit in (ct.SF_SITE, ct.SF_MODE, ct.SF_DEST):
        assert ct.evaluate(_ev(sf=bit)).reasons == ()


def test_sec_ch_ua_alone_does_not_clear_the_claim_and_is_never_required():
    """sec-ch-ua is a Chromium-only Client Hint. Requiring it would flag every Firefox and Safari
    user on the estate, so it is not in FETCH_METADATA_BITS -- and it does not substitute for the
    three that are."""
    assert ct.SF_CHUA & ct.FETCH_METADATA_BITS == 0
    assert ct.REASON_NO_FETCH_METADATA in ct.evaluate(_ev(sf=ct.SF_CHUA)).reasons
    assert ct.evaluate(_ev(ua=UA_FIREFOX, sf=ct.SF_SITE | ct.SF_MODE | ct.SF_DEST)).reasons == ()


def test_a_genuinely_old_browser_is_never_flagged_for_a_header_it_never_sent():
    """THE LEGITIMATE POPULATION, WHICH IS THE ONLY THING THAT MATTERS HERE. Chrome 49 predates
    fetch metadata by three years and Safari 15.6 predates it by two. They send nothing, correctly,
    and flagging them would be this check punishing somebody for owning an old machine."""
    assert ct.evaluate(_ev(ua=UA_CHROME_OLD, sf=0)).reasons == ()
    assert ct.evaluate(_ev(ua=UA_SAFARI_15, sf=0)).reasons == ()
    # ...and the floors themselves, so a future edit cannot quietly lower them.
    assert ct.FETCH_METADATA_SINCE["chrome"] >= 76 and ct.FETCH_METADATA_SINCE["firefox"] >= 90
    assert ct.FETCH_METADATA_SINCE["safari"] >= (16, 4)


def test_an_unrecognised_user_agent_is_determinable_but_never_a_contradiction():
    """There is no mainstream-browser claim to contradict, so this module says nothing. The caller
    still has `bot` from classify_ua; inventing a second opinion here would be a signal made out of
    our own ignorance."""
    v = ct.evaluate(_ev(ua="SomeInternalMonitor/2", sf=0))
    assert v.reasons == () and v.determinable is True


def test_a_self_identified_tool_is_never_double_counted():
    """curl is already `bot: true` from classify_ua and is already in the clients column. A
    contradiction on top would put one address in one column twice."""
    assert ct.evaluate(_ev(ua=UA_CURL, bot=True, sf=0)).reasons == ()


def test_api_and_well_known_are_exempt_from_every_judgement_here():
    """Every deploy verifier in this repo proves the site is live by fetching /api/me with curl or
    urllib and asserting 401, and ACME needs /.well-known. Both are exempt from the bot gate for
    that reason and both are exempt from this."""
    for path in ("/api/me", "/api/admin/fleet", "/.well-known/acme-challenge/xyz"):
        assert ct.evaluate(_ev(path=path, sf=0)).reasons == ()


def test_the_exempt_prefixes_are_the_same_two_visitors_py_exempts():
    """ONE HOME, ENFORCED. client_truth.py must stay vendorable into a project that has no
    visitors.py, so the tuple is restated -- and restated values drift unless a test welds them."""
    from app import visitors
    assert tuple(ct.EXEMPT_PREFIXES) == tuple(visitors.EXEMPT_PREFIXES)


# ---- the protocol-version half, and the reason it is dormant ------------------------------------

def test_the_scope_http_version_can_never_convict_anybody():
    """THE MEASUREMENT THAT SHAPED THE DESIGN, PINNED SO IT CANNOT BE UNDONE BY ACCIDENT.

    The shared Caddy terminates TLS and opens a fresh upstream connection, and uvicorn implements no
    HTTP/2 at all, so `scope["http_version"]` is "1.1" for a Chrome visitor and for a Go program
    alike. Building the h2 contradiction on it would fire on 100% of real browsers: a check that
    cannot fail, pointed the other way. It arms only for a version a PROXY reported about the
    CLIENT."""
    v = ct.evaluate(_ev(hv="1.1", hvs=ct.HV_FROM_HOP, sf=FULL_SF))
    assert ct.REASON_HTTP11 not in v.reasons


def test_a_proxy_reported_http11_from_a_modern_browser_claim_IS_a_contradiction():
    """And when the proxy DOES tell us what the client spoke (one `header_up X-Client-Proto` line in
    the shared Caddy block), the check is live. This is what makes it a check that CAN fail rather
    than a paragraph of intent."""
    v = ct.evaluate(_ev(hv="1.1", hvs=ct.HV_FROM_CLIENT, sf=FULL_SF))
    assert v.reasons == (ct.REASON_HTTP11,)
    assert ct.evaluate(_ev(hv="HTTP/1.1", hvs=ct.HV_FROM_CLIENT, sf=FULL_SF)).reasons == (
        ct.REASON_HTTP11,), "the proxy may write it either way; both are the same fact"
    # h2 from the same client is the clean case and must stay clean.
    assert ct.evaluate(_ev(hv="2", hvs=ct.HV_FROM_CLIENT, sf=FULL_SF)).reasons == ()
    # ...and an old browser still gets the benefit of the doubt on its own protocol.
    assert ct.evaluate(_ev(ua=UA_CHROME_OLD, hv="1.1", hvs=ct.HV_FROM_CLIENT,
                           sf=FULL_SF)).reasons == ()


# ---- absence of evidence -------------------------------------------------------------------------

def test_a_record_with_no_hv_field_is_not_determinable():
    """An old line, or a sibling project that has not redeployed. NOT a bot, NOT a human, and
    absolutely not a default into either."""
    v = ct.evaluate(_ev(hv=_ABSENT, hvs=_ABSENT, sf=_ABSENT))
    assert v.reasons == () and v.determinable is False
    assert ct.has_evidence(_ev(hv=_ABSENT)) is False
    assert ct.has_evidence(_ev(sf=_ABSENT)) is False
    assert ct.has_evidence(_ev()) is True


def test_every_malformed_input_resolves_to_no_reasons_and_never_raises():
    """FAIL OPEN, ALWAYS. An error in this path is a fact about us, not about the client."""
    for bad in (None, [], "", 0, {"path": None}, {"path": "/", "ua": None, "hv": 1, "sf": "x"},
                {"path": "/", "ua": UA_CHROME, "hv": "1.1", "sf": None}):
        v = ct.evaluate(bad)
        assert v.reasons == ()


# =================================================================================================
# GROUP 2 -- IT MUST NEVER BECOME ENFORCEMENT
# =================================================================================================

def test_the_verdict_object_carries_no_decision_and_one_cannot_be_added():
    """THE PROPERTY, not a string. A caller that wanted to enforce on this would have to write the
    decision in its own file, where a reviewer sees it. __slots__ closes the runtime back door."""
    v = ct.evaluate(_ev(sf=0))
    assert set(ct.Verdict.__slots__) == {"reasons", "determinable"}
    assert set(v.as_dict()) == {"reasons", "determinable"}
    with pytest.raises(AttributeError):
        v.block = True
    # and nothing in the shape is truthy-as-a-decision: the reasons are plain strings.
    assert all(isinstance(r, str) for r in v.reasons)


def test_client_truth_cannot_reach_a_firewall_a_shield_or_a_ruleset():
    """The import floor as a PROPERTY: a module that imports neither `subprocess` nor `socket` nor
    anything in this estate that enforces cannot shell out to nft and cannot promote a rule. Amnezia
    VPN shares the production host (StGB 202a-303b, EU 2013/40, CFAA 1030)."""
    tree = ast.parse(_read(CT_SRC))
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    assert imported == {"re"}, "client_truth.py grew an import: %s" % sorted(imported)
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            called.add(n.func.attr)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            called.add(n.func.id)
    assert not (called & {"decide", "observe", "block", "enter_tarpit", "promote", "system",
                          "popen", "run", "Popen"})


def test_a_contradiction_is_never_an_input_to_any_enforcement_decision(pc):
    """THE ONE THAT MATTERS, AND IT IS A PROPERTY OF THE DECISION PATH, NOT A STRING.

    THE FIXTURE IS PROVED FIRST (this repo has scored mutations as 'caught' against an already-red
    suite and tested fixtures that never reproduced the condition). An address with genuine probe
    evidence must actually convert to BLOCK, or 'not blocked' below would be a statement about a
    decision path that was never armed.

    Then the subject: two hundred requests from one address, every single one of them contradicting
    its own user agent, to a route the site SERVES, answered 200. No probe path, no 404, no user
    agent rotation -- nothing the shield has ever scored. If contradiction had been wired into
    enforcement anywhere (the local shield, the tarpit, a promoted rule) this address would be
    refused or slowed. Every verdict is asserted, including on paths that WOULD convict a real
    scanner, and the event log is then checked to contain no refusal of any kind for it.
    """
    assert pc.decide(_ANON_PROBE, PROBES[0])[0] == "ALLOW", "an unseen address starts clean"
    _feed(pc, _ANON_PROBE, PROBES)
    assert pc.decide(_ANON_PROBE, PROBES[0])[0] == "BLOCK", \
        "the enforcement path is not armed, so nothing below is a measurement"

    ip = "198.51.100.91"
    spoofed = _ev(ip=ip, ua=UA_CHROME, sf=0, hv="1.1", hvs=ct.HV_FROM_CLIENT, path="/")
    assert ct.evaluate(spoofed).reasons, "the fixture does not reproduce the contradiction"
    for _ in range(200):
        pc.watch(ip, "/", 200, UA_CHROME, "GET")
        pc.observe(ip, "/", 200, 3, UA_CHROME, "", "GET",
                   hv="1.1", hvs=pc.HV_FROM_CLIENT, sf=0)
    for path in PROBES + ("/", "/app/admin"):
        verdict, why = pc.decide(ip, path)
        assert verdict == "ALLOW", (
            "a self-contradicting client was %s on %s (%s). Labelling must never become "
            "enforcement." % (verdict, path, why))
    assert pc.is_blocked(ip) is False
    shield_evts = [e for e in _events(pc) if str(e.get("evt", "")).startswith("perseus_shield_")]
    # NOT A VACUOUS FILTER. The proven twin above DID convert, so refusal events exist in this log;
    # a filter that found nothing at all would pass this assertion while measuring nothing.
    assert shield_evts, "no shield event was written at all, so the filter below proves nothing"
    assert not [e for e in shield_evts if str(e.get("ip", "")) == ip], \
        "a refusal event was written for a client that only contradicted itself"


def test_no_reason_code_from_this_module_appears_in_any_enforcing_table():
    """A reason must not be able to leak into a rule by NAME either. The hub promotes patterns; if
    one of these enum keys ever turns up in the ruleset, vet.py or the shield's class table, the
    labelling has grown teeth somewhere nobody looked."""
    reasons = {ct.REASON_HTTP11, ct.REASON_NO_FETCH_METADATA}
    for rel in ("perseus/client.py", "perseus/ruleset.py", "perseus/vet.py", "perseus/hub.py",
                "webapp/backend/app/shield.py"):
        p = os.path.join(ROOT, *rel.split("/"))
        if not os.path.exists(p):
            continue
        src = _read(p)
        for r in reasons:
            assert r not in src, "%s names the labelling reason %r" % (rel, r)


def test_an_authenticated_session_is_still_never_blocked_and_never_tarpitted(pc):
    """The rule predates this change and must survive it.

    A signed-in operator behind a header-stripping corporate proxy contradicts itself on EVERY
    request, so this is the exact shape of the person this change could plausibly lock out. Both
    verdicts are asserted on identical evidence, and the anonymous twin proves the fixture reached
    tarpit and block level first -- otherwise "not tarpitted" would describe an address nothing was
    ever going to tarpit.

    Refusing a real person is a LOCKOUT, not an outage: nothing alerts, and the operator spent an
    hour on the last one. There is one safe direction here.
    """
    anon_t, auth_t = "198.51.100.1", "198.51.100.2"
    for ip in (anon_t, auth_t):
        _feed(pc, ip, PROBES[:2])
        pc.observe(ip, "/", 200, 3, UA_CHROME, "", "GET",
                   hv="1.1", hvs=pc.HV_FROM_CLIENT, sf=0)      # and contradicting, throughout
    assert pc.decide(anon_t, "/")[0] == "TARPIT", "the fixture did not reach tarpit level"
    assert pc.decide(auth_t, "/", authed=True)[0] == "ALLOW"

    anon_b, auth_b = "198.51.100.3", "198.51.100.4"
    for ip in (anon_b, auth_b):
        _feed(pc, ip, PROBES)
        pc.observe(ip, "/", 200, 3, UA_CHROME, "", "GET",
                   hv="1.1", hvs=pc.HV_FROM_CLIENT, sf=0)
    assert pc.decide(anon_b, PROBES[0])[0] == "BLOCK", "the fixture did not reach block level"
    verdict, why = pc.decide(auth_b, "/", authed=True)
    assert verdict == "ALLOW" and why, "an exemption that says nothing is a silent 404"


# =================================================================================================
# GROUP 3 -- THE TWO EMITTERS, AND THE VALUES THEY ARE NOT ALLOWED TO DISAGREE ON
# =================================================================================================

def _consts(src, names):
    """Top-level `NAME = <literal>` values, read OFF DISK with ast. Reading the FILE rather than
    importing the module is the difference between a comparison and `x == x` in a costume."""
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names:
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:
                pass
    return out


def test_the_sidecar_and_this_module_agree_on_the_bitmask():
    """`perseus/client.py` may not import client_truth -- its import floor is a security control --
    so the four bit values live in two files. This is the weld."""
    names = ("SF_SITE", "SF_MODE", "SF_DEST", "SF_CHUA", "HV_FROM_CLIENT", "HV_FROM_HOP",
             "HV_CLIENT_HEADER")
    mine = _consts(_read(CT_SRC), names)
    theirs = _consts(_read(CLIENT_SRC), names)
    assert set(mine) == set(names), "client_truth.py stopped declaring %s" % sorted(
        set(names) - set(mine))
    assert mine == theirs, "the sidecar and the reader disagree: %r vs %r" % (mine, theirs)


def test_the_sidecars_bot_tables_are_telemetrys_bot_tables():
    """`observe()` carried NO `bot` field, which is why every sibling project read as human. It now
    classifies, with the SAME tables classify_ua uses -- restated because the client may import
    nothing, and welded here because a restated table drifts."""
    tel = _consts(_read(TELEMETRY_SRC), ("_BOTS", "_OS", "_BROWSER"))
    cli = _consts(_read(CLIENT_SRC), ("_BOT_UA", "_OS_UA", "_BROWSER_UA"))
    assert tuple(p for p, _ in tel["_BOTS"]) == tuple(cli["_BOT_UA"])
    assert tuple(p for p, _ in tel["_OS"]) == tuple(cli["_OS_UA"])
    assert tuple(p for p, _ in tel["_BROWSER"]) == tuple(cli["_BROWSER_UA"])


def test_the_two_bot_classifiers_return_the_same_answer_for_the_same_agent():
    """BEHAVIOUR, not only the table. Same corpus, both implementations, every answer identical."""
    import perseus.client as pc
    corpus = [UA_CHROME, UA_FIREFOX, UA_EDGE, UA_SAFARI_17, UA_SAFARI_15, UA_CHROME_OLD, UA_CURL,
              "", "   ", "Wget/1.21.4", "python-requests/2.31.0", "Go-http-client/1.1",
              "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
              # GOOGLEBOT SMARTPHONE. The one corpus entry that the FALLBACK cannot catch: it names
              # Chrome AND Android, so "no browser token and no OS token" says nothing about it and
              # only the `googlebot` token in the table makes it a bot. Without a line of this shape
              # the behavioural comparison passes for a table that has drifted, which is the
              # negative-test-passing-because-of-another-guard defect.
              "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 "
              "(compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
              "Mozilla/5.0 (compatible; bingbot/2.0)", "Mozilla/5.0 (compatible; Nmap Scripting)",
              "zgrab/0.x", "Java/17.0.1", "SomeInternalMonitor/2", "Mozilla/5.0",
              "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) Version/17.2 Mobile Safari/604.1"]
    for ua in corpus:
        assert pc.ua_bot(ua) == telemetry.classify_ua(ua)["bot"], (
            "the sidecar and colt-web disagree about %r" % ua)


def test_the_client_import_floor_is_still_exactly_the_seven_permitted_modules():
    """Restated here as well as in test_perseus_shield.py ON PURPOSE. This change is the most
    likely thing ever to break it -- the obvious implementation is `import client_truth` -- and the
    test that would catch it lives in a different file that a reader of this one need not open."""
    tree = ast.parse(_read(CLIENT_SRC))
    got = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            got |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            if n.level:                       # a relative import would pull in a package
                got.add(".")
            got.add((n.module or "").split(".")[0])
    got.discard("")
    assert got == {"asyncio", "json", "os", "re", "threading", "time", "hashlib"}, (
        "perseus/client.py import floor moved: %s" % sorted(got))


def test_the_sidecar_writes_the_evidence_and_omits_what_it_could_not_measure(monkeypatch):
    """`observe()` is the sibling projects' only voice. It must carry `bot` -- and it must OMIT a
    field it could not measure rather than defaulting it, because `sf: 0` (we looked, nothing came)
    and no `sf` at all (nobody looked) are different facts and only one is a signal."""
    import perseus.client as pc
    written = []
    monkeypatch.setattr(pc, "_write", lambda d: written.append(d))
    monkeypatch.setattr(pc, "ENABLED", True)
    pc.observe("203.0.113.1", "/", 200, 5, UA_CHROME, "", "GET",
               hv="1.1", hvs=pc.HV_FROM_HOP, sf=pc.SF_SITE | pc.SF_MODE | pc.SF_DEST)
    pc.observe("203.0.113.2", "/", 200, 5, UA_CURL, "", "GET")
    rich, bare = written
    assert rich["bot"] is False and rich["sf"] == 7 and rich["hvs"] == "s"
    assert bare["bot"] is True, "a curl line that says nothing is how four projects read as human"
    assert "sf" not in bare and "hv" not in bare, "an unmeasured field must be ABSENT, not 0"


def _asgi_get(app, path="/", headers=(), http_version="1.1"):
    """Call an ASGI app DIRECTLY. No starlette.testclient, and therefore no httpx.

    httpx is a dependency of starlette's TESTING helper, not of this application. It is present in
    the sandbox this was written in and absent on the operator's Windows Python, so importing it
    would fail his ship with "The starlette.testclient module requires the httpx package" -- the
    root cause CLAUDE.md already records for several wasted ships, and which
    `test_security_headers.py::test_no_test_imports_a_library_the_app_does_not_declare` now fails
    the build on. This harness is the same shape as the one that file already uses.
    """
    import asyncio
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.1"},
             "http_version": http_version, "method": "GET", "scheme": "http",
             "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
             "headers": [(b"host", b"testserver")]
                        + [(k.encode(), v.encode()) for k, v in headers],
             "client": ("203.0.113.55", 4242), "server": ("testserver", 80)}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        return None

    asyncio.run(app(scope, receive, send))


def test_telemetry_emits_the_same_three_fields_from_a_real_request(monkeypatch):
    """FOLLOW THE VALUE END TO END: UI -> API -> persistence -> engine, asserted at each hop. A
    field the emitter drops is invisible to every reader test in this file, and the reader tests
    would all still pass."""
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    seen = []
    monkeypatch.setattr(telemetry, "emit", lambda **k: seen.append(k))
    app = Starlette(routes=[Route("/", lambda r: PlainTextResponse("ok"))])
    telemetry.install(app)
    _asgi_get(app, "/", [("user-agent", UA_CHROME), ("sec-fetch-site", "none"),
                         ("sec-fetch-mode", "navigate"), ("sec-fetch-dest", "document")])
    _asgi_get(app, "/", [("user-agent", UA_CHROME)])
    _asgi_get(app, "/", [("user-agent", UA_CHROME), ("x-client-proto", "HTTP/2.0")])
    browser, naked, fwd = [e for e in seen if e.get("evt") == "http"][:3]
    assert browser["sf"] == ct.SF_SITE | ct.SF_MODE | ct.SF_DEST
    assert browser["hvs"] == ct.HV_FROM_HOP and browser["hv"] == "1.1", \
        "the scope version is the PROXY hop and must be stamped as such"
    assert naked["sf"] == 0, "a measured zero is the signal; it must be written, not omitted"
    assert fwd["hvs"] == ct.HV_FROM_CLIENT and fwd["hv"] == "HTTP/2.0"
    # ...and the claim it is compared against is still in the same record.
    assert browser["bot"] is False and "ua" in browser


# =================================================================================================
# GROUP 4 -- THE COLUMN THE OPERATOR ACTUALLY READS
# =================================================================================================

def _fleet_rows(monkeypatch, tmp_path, rows):
    p = os.path.join(str(tmp_path), "events.log")
    with io.open(p, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    bd = os.path.join(str(tmp_path), "beats")
    os.makedirs(bd, exist_ok=True)
    monkeypatch.setattr(fleet, "EVENTS", p)
    monkeypatch.setattr(fleet, "BEAT_DIR", bd)
    monkeypatch.setattr(fleet, "BLOCKLIST", os.path.join(str(tmp_path), "nope.json"))
    fleet._LOKI_CACHE["ts"] = 0.0
    fleet._LOKI_CACHE["beats"] = {}
    fleet._LOKI_EVENTS.update(ts=0.0, rows=[], ok=False, partial=False, busy=False)
    monkeypatch.delenv("LOKI_URL", raising=False)
    return {x["service"]: x for x in fleet.status()["projects"]}


def test_a_curl_one_liner_is_a_client_and_not_a_visitor(monkeypatch, tmp_path):
    """THE DEFECT, STATED AS A TEST. `len(set(ip))` counted this as a visitor on the admin page,
    with `bot: true` sitting in the very same record."""
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip="198.51.100.10", ua=UA_CURL, bot=True, sf=0),
    ])["colt-web"]
    assert r["clients_24h"] == 1 and r["visitors_24h"] == 0
    assert r["addresses_24h"] == 1 and r["visitor_split"] == "measured"


def test_a_real_browser_is_a_visitor(monkeypatch, tmp_path):
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip="198.51.100.11", ua=UA_CHROME, bot=False, sf=FULL_SF,
            hv="2", hvs=ct.HV_FROM_CLIENT),
    ])["colt-web"]
    assert r["visitors_24h"] == 1 and r["clients_24h"] == 0
    assert r["visitor_split"] == "measured"


def test_a_spoofed_chrome_is_counted_as_a_client_not_a_visitor(monkeypatch, tmp_path):
    """Chrome 131 in the header, HTTP/1.1 on the wire, not one fetch-metadata header. The user agent
    says visitor; the behaviour says otherwise, and the behaviour is the thing that cost something
    to produce."""
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip="198.51.100.12", ua=UA_CHROME, bot=False, sf=0,
            hv="1.1", hvs=ct.HV_FROM_CLIENT),
    ])["colt-web"]
    assert r["visitors_24h"] == 0, "a self-contradicting client must not reach the visitor count"
    assert r["clients_24h"] == 1


def test_a_line_with_no_evidence_is_unjudged_and_counted_as_neither(monkeypatch, tmp_path):
    """Every line every sibling project wrote before this shipped. The row says so; it does not
    guess, and it does not print a zero that reads as 'nobody came'."""
    r = _fleet_rows(monkeypatch, tmp_path, [
        {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "198.51.100.13",
         "path": "/", "method": "GET", "status": 200, "ua": UA_CHROME},
    ])["colt-web"]
    assert r["visitors_24h"] is None and r["clients_24h"] is None
    assert r["unjudged_24h"] == 1 and r["addresses_24h"] == 1
    assert r["visitor_split"] == "none"


def test_a_mixed_project_says_partial_rather_than_pretending(monkeypatch, tmp_path):
    """The state the fleet will ACTUALLY be in the day this ships: some lines new, most lines old.
    A number that means different things per row is the defect this page already had."""
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip="198.51.100.20", sf=FULL_SF),
        _ev(service="colt-web", ip="198.51.100.21", ua=UA_CURL, bot=True, sf=0),
        {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "198.51.100.22",
         "path": "/", "method": "GET", "status": 200, "ua": UA_CHROME},
    ])["colt-web"]
    assert (r["visitors_24h"], r["clients_24h"], r["unjudged_24h"]) == (1, 1, 1)
    assert r["addresses_24h"] == 3 and r["visitor_split"] == "partial"


def test_an_address_that_ever_looked_like_a_client_never_counts_as_a_visitor(monkeypatch, tmp_path):
    """A scanner that also fetches the homepage with a clean header set must not buy itself a place
    in the visitor count. Precedence runs one way only, and the direction is the conservative one."""
    ip = "198.51.100.30"
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip=ip, ua=UA_CHROME, sf=FULL_SF, path="/"),
        _ev(service="colt-web", ip=ip, ua=UA_CHROME, sf=0, path="/wp-login.php"),
    ])["colt-web"]
    assert r["visitors_24h"] == 0 and r["clients_24h"] == 1 and r["addresses_24h"] == 1


def test_a_project_we_cannot_read_reports_null_and_not_zero(monkeypatch, tmp_path):
    """Same rule `refused_24h` already obeys. 'We counted and found none' and 'we could not look'
    are the two facts this whole module exists to keep apart."""
    rows = _fleet_rows(monkeypatch, tmp_path, [])
    for svc in ("jhw-web", "jev-web"):
        assert rows[svc]["visitors_24h"] is None and rows[svc]["clients_24h"] is None
        assert rows[svc]["addresses_24h"] == 0 and rows[svc]["visitor_split"] == "none"


def test_the_fleet_page_survives_client_truth_being_absent(monkeypatch, tmp_path):
    """AN OPTIONAL LOOKUP MAY MAKE A PAGE MORE ACCURATE, NEVER LESS, AND NEVER 500 IT. Without the
    contradiction check every row degrades to `none`, which is exactly the honest answer when the
    thing that would have judged the lines is not there."""
    monkeypatch.setattr(fleet, "_client_truth", None)
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip="198.51.100.40", sf=FULL_SF),
    ])["colt-web"]
    assert r["visitor_split"] == "none" and r["visitors_24h"] is None
    assert r["addresses_24h"] == 1, "the address total never depended on the lookup"


def test_every_new_label_exists_in_all_six_interface_locales():
    """The catalogue gate enforces 100%, and it runs in node. This is the same assertion in the
    suite the operator actually reads, so a missing key is a named failure instead of a raw
    `fleet.vs.none` printed on the live admin page -- which has happened here before."""
    import re as _re
    keys = ("fleet.cli", "fleet.vsUnknown", "fleet.vsAddr", "fleet.vsUnjudged",
            "fleet.vs.measured", "fleet.vs.partial", "fleet.vs.none")
    for code in ("en", "de", "it", "fr", "es", "pl"):
        src = _read(os.path.join(ROOT, "webapp", "frontend", "src", "locales", "%s.js" % code))
        for k in keys:
            assert _re.search(r'"%s"\s*:' % _re.escape(k), src), "%s is missing %s" % (code, k)
