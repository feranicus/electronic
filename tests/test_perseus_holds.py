"""test_perseus_holds.py -- the operator's own channel to the four sibling projects.

WHAT THIS FILE EXISTS TO PROVE. `perseus/client.py::check(ip, path)` accepted an `ip` argument from
the day it was written and NEVER ONCE READ IT: every decision this estate's thin client could make
was about a PATH. So when the operator watched one source hammering jobhuntwow.com there was no
channel at all by which "hold that /24 for an hour" could reach jobhuntwow, jev.best,
klimaanlage-preise.de or s4biz.io. The hub can publish a PATTERN tonight; it cannot publish a
decision about an ADDRESS now. SECTION C2 of the client is that channel, and this file is its proof.

THE FOUR THINGS THAT MATTER MORE THAN THE BLOCKING, in order -- the same four the local shield is
held to, because a hold is a stronger act than anything the shield decides on its own:

  1. A REAL PERSON IS NEVER LOCKED OUT. Not on /.well-known/ (which would be a CERTIFICATE outage
     for every domain on the shared proxy), not on /api/ (which every deploy verifier probes), and
     not while logged in.
  2. IT CANNOT REACH THE FIREWALL. Amnezia VPN shares this host. Enforcement is HTTP-layer, inside
     our own process, or it does not happen -- StGB §202a/§202b/§303a/§303b, EU Directive 2013/40,
     CFAA §1030. Nothing here scans back, connects back, or shells out.
  3. EVERY HOLD IS BOUNDED, EXPIRING AND NARROW. `until` is mandatory, may not be in the past, and
     may not be further ahead than the 24-hour ceiling the shield already commits to. There is no
     permanent hold and there is no way to write one. A prefix broader than the committed floor is
     refused, because an operator control that can refuse everybody is worse than no control.
  4. EVERY HOLD IS VISIBLE, or it is not a control -- and visible ONCE, because a line on every
     request trains the operator to read past the one that matters.

AND THE FAIL-OPEN DISCIPLINE ABOVE ALL OF IT. A missing file, a corrupt file, a permission error, a
malformed row, an unparseable address: every one of them SERVES the request. There is exactly one
safe direction here.

HOW THESE TESTS ARE WRITTEN.
  * Every negative proves its FIXTURE first. A test that blocks nobody because the hold never
    loaded is a test of the harness; so each "is not blocked" assertion sits beside the identical
    request that IS blocked, in the same test, from the same file.
  * The CIDR parser is checked against the stdlib `ipaddress` module as an ORACLE, case by case,
    including the cases where we are deliberately stricter. `ipaddress` may not be imported by
    perseus/client.py itself -- tests/test_perseus_shield.py commits that file to a stdlib floor of
    {asyncio, json, os, re, threading, time, hashlib} and asserts it -- so the arithmetic is written
    out there and graded against the stdlib here.
  * Nothing reaches the network, nothing writes outside tmp_path, and no POSIX-only API is used:
    the suite runs on the operator's Windows box.
"""
import ipaddress
import json
import os
import time

import pytest

import perseus.client as pcmod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "perseus", "client.py")

SERVICE = "jhw-web"
NEUTRAL = "/pricing"          # not a probe shape, not a honeytoken, not a never-block prefix


# =============================================================================================
# THE FIXTURE.
#
# LOCAL IS DELIBERATELY OFF. With the local shield standing down, `check()` is the ONLY thing in
# this module that can refuse a request -- so every refusal below is attributable to the hold and
# to nothing else. One test at the end arms the local shield as well, to prove the two coexist.
#
# Every write path is redirected into tmp_path. EVENTS and BEAT_DIR default to /var/log/colt/...,
# which on Windows resolves to C:\var\log\colt and would be CREATED on the operator's own disk.
# =============================================================================================
@pytest.fixture
def pc(tmp_path, monkeypatch):
    m = pcmod
    monkeypatch.setattr(m, "EVENTS", str(tmp_path / "events.log"))
    monkeypatch.setattr(m, "BEAT_DIR", str(tmp_path / "beats"))
    monkeypatch.setattr(m, "BLOCKLIST", str(tmp_path / "no-such-blocklist.json"))
    monkeypatch.setattr(m, "HOLDS", str(tmp_path / "perseus_holds.json"))
    monkeypatch.setattr(m, "SERVICE", SERVICE)
    monkeypatch.setattr(m, "ALLOW_IPS", set())
    monkeypatch.setattr(m, "ENABLED", True)
    monkeypatch.setattr(m, "ENFORCE", True)
    monkeypatch.setattr(m, "LOCAL", False)
    # The blocklist cache answers from memory: no disk read, no published pattern, no heartbeat.
    m._CACHE.update(loaded=time.time(), beat=time.time(), mtime=0.0, patterns=[], cycle=0,
                    thresholds={}, warned=False)
    _reset(m)
    for d in (m._hits, m._fps, m._blocked, m._seen_ips, m._miss, m._slow,
              m._served, m._authed, m._recent, m._told):
        d.clear()
    yield m
    _reset(m)
    for d in (m._hits, m._fps, m._blocked, m._seen_ips, m._miss, m._slow,
              m._served, m._authed, m._recent, m._told):
        d.clear()


def _reset(m):
    """Forget everything the holds reader believes AND force the next call to hit the disk.

    `mtime = -1.0` rather than 0.0 on purpose: a real file's mtime can legitimately be 0.0 on a
    filesystem with a broken clock, and a cache that compared equal to it would skip the read and
    turn the whole suite green for the wrong reason. The caching discipline has its own tests
    below, which set the cache deliberately instead of resetting it.
    """
    m._HOLDS.update(mtime=-1.0, loaded=0.0, holds=[], generated=0, dropped=0, refused={},
                    reported=None)


def _hold(cidr, service=SERVICE, ttl=3600, why="operator: Block /24 1h", by="telegram", **over):
    row = {"cidr": cidr, "service": service, "until": time.time() + ttl, "why": why, "by": by}
    row.update(over)
    return row


def _place(m, holds, raw=None):
    """Write the holds file and make the next read see it. Returns the path."""
    p = m.HOLDS
    text = raw if raw is not None else json.dumps(
        {"generated": int(time.time()), "holds": holds})
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    _reset(m)
    return p


def _rewrite(m, text, due=False):
    """Replace the holds file IN PLACE, keeping whatever the reader already believes.

    THE mtime IS BUMPED DELIBERATELY. A second write inside the same filesystem timestamp tick is
    invisible to the mtime gate, so a test that rewrote the file and then asserted "the reader kept
    the old holds" would pass without the reader ever having TRIED to parse the new contents -- a
    denominator produced by the thing being measured. `due` decides whether a read is owed at all,
    which is the other half of the discipline and has its own test.
    """
    prev = os.stat(m.HOLDS).st_mtime
    with open(m.HOLDS, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.utime(m.HOLDS, (prev + 5, prev + 5))
    if due:
        m._HOLDS["loaded"] = 0.0


def _events(m):
    if not os.path.exists(m.EVENTS):
        return []
    out = []
    with open(m.EVENTS, encoding="utf-8") as fh:
        for line in fh:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _evts(m, name):
    return [e for e in _events(m) if e.get("evt") == name]


# =============================================================================================
# 1. THE ARITHMETIC. Graded against the stdlib, case by case, in both directions.
# =============================================================================================

# (literal, does the stdlib accept it) -- every one of these must be decided the SAME WAY by
# perseus/client.py::_parse_cidr, and where it is accepted, to the SAME network and prefix.
ORACLE = [
    ("104.28.222.0/24", True), ("104.28.222.5/24", True), ("1.2.3.4", True),
    ("0.0.0.0/0", True), ("255.255.255.255", True), ("10.0.0.0/8", True),
    ("192.0.2.0/31", True), ("192.0.2.1/32", True),
    ("010.1.1.1", False), ("1.2.3.04", False), ("1.2.3.256", False), ("1.2.3", False),
    ("1.2.3.4.5", False), ("1.2.3.4/33", False), ("1.2.3.4/", False), ("1.2.3.4/-1", False),
    ("", False), ("not-an-address", False), ("\u0663.1.1.1", False), ("1.2.3.x", False),
    ("::", True), ("::1", True), ("2001:db8::/32", True), ("2001:db8::1/64", True),
    ("::ffff:1.2.3.4", True), ("1:2:3:4:5:6:7:8", True), ("1:2:3:4:5:6:1.2.3.4", True),
    ("1:2:3:4:5:6:7::", True), ("::/0", True),
    ("1:2:3:4:5:6:7:8:9", False), ("1:2:3:4:5:6:7:8::", False), ("1::2::3", False),
    ("1:2:3:4:5:6:7:8/129", False), (":1:2:3:4:5:6:7", False), ("12345::", False),
    ("1:2:3:4:5:6:7:8:", False), ("::g", False),
]


def test_the_cidr_parser_decides_exactly_what_the_stdlib_decides():
    """THE ORACLE. `ipaddress` cannot be imported by the client -- the committed stdlib floor in
    tests/test_perseus_shield.py forbids it and that floor is what proves the file cannot reach a
    socket or a subprocess. So the arithmetic is written out in the client and graded HERE against
    the module that owns the answer.

    The comparison is on the RESULT, not on acceptance alone: an accepted literal must produce the
    same network integer and the same prefix length, or a hold would cover addresses the operator
    never named.
    """
    # PROVE THE TABLE DISCRIMINATES. A table that is all-accept or all-reject would let a parser
    # that says yes to everything, or no to everything, pass this test.
    assert sum(1 for _s, ok in ORACLE if ok) >= 15
    assert sum(1 for _s, ok in ORACLE if not ok) >= 15

    for text, want_ok in ORACLE:
        try:
            net = ipaddress.ip_network(text, strict=False)
        except Exception:
            net = None
        assert (net is not None) is want_ok, (
            "the ORACLE table is wrong about %r, not the parser" % text)

        got = pcmod._parse_cidr(text)
        if net is None:
            assert got is None, "%r is refused by ipaddress and accepted by _parse_cidr" % text
            continue
        assert got is not None, "%r is accepted by ipaddress and refused by _parse_cidr" % text
        ver, base, _mask, prefix = got
        assert ver == net.version, text
        assert base == int(net.network_address), text
        assert prefix == net.prefixlen, text


def test_a_bare_address_is_a_32_or_a_128():
    """The contract says so, and a bare address is the commonest hold there is."""
    assert pcmod._parse_cidr("1.2.3.4")[3] == 32
    assert pcmod._parse_cidr("2001:db8::1")[3] == 128


def test_the_two_places_we_are_deliberately_stricter_than_the_stdlib():
    """BOTH DIVERGENCES ARE TOWARDS REFUSING, which is the fail-open direction: a hold we cannot
    parse holds nobody. Written down rather than discovered later by somebody comparing the two.

    A SCOPE ID names an interface. `fe80::1%eth0` is meaningful only on the machine that named it
    and can never be the source address of a request arriving over the internet -- yet `ipaddress`
    accepts it and quietly discards the scope, which would make a hold on one machine's link-local
    address a hold on every machine's.

    A DOTTED NETMASK is a second way to write a prefix. One home, one syntax: the producer writes
    /nn and nothing else has to be kept in agreement with it.
    """
    assert ipaddress.ip_network("fe80::1%eth0", strict=False).prefixlen == 128   # the stdlib takes it
    assert pcmod._parse_cidr("fe80::1%eth0") is None                             # we do not

    assert ipaddress.ip_network("1.2.3.4/255.255.255.0", strict=False).prefixlen == 24
    assert pcmod._parse_cidr("1.2.3.4/255.255.255.0") is None


def test_surrounding_whitespace_is_forgiven_and_means_the_same_network():
    """The ONE place we are looser, and it is a typing convenience with no consequence: the network
    is identical to the trimmed form, so nothing wider is ever covered."""
    with pytest.raises(ValueError):
        ipaddress.ip_network(" 1.2.3.4 ")
    assert pcmod._parse_cidr(" 1.2.3.4 ") == pcmod._parse_cidr("1.2.3.4")


def test_host_bits_below_the_prefix_are_masked_off_not_refused():
    """`ip_network(..., strict=False)`. An operator who types the address he is looking at with /24
    after it means that /24, and refusing his intent over a pedantic detail is how a control gets
    worked around rather than used."""
    assert pcmod._parse_cidr("104.28.222.5/24") == pcmod._parse_cidr("104.28.222.0/24")


# =============================================================================================
# 2. A HOLD REFUSES A MATCHING ADDRESS -- AND THE POSITIVE CONTROL THAT IT WOULD NOT HAVE.
# =============================================================================================

def test_a_hold_refuses_a_matching_address_and_the_same_request_is_served_without_it(pc):
    """THE POSITIVE CONTROL IS IN THE SAME TEST, FIRST. Without it every refusal below could be
    passing for some entirely different reason -- a pattern, the local shield, a disabled client --
    and the test would still be green."""
    ip = "104.28.222.55"

    # BEFORE: no holds file at all. This request is SERVED.
    allowed, retry, why = pc.check(ip, NEUTRAL)
    assert (allowed, retry, why) == (True, 0, ""), "the control failed: something else refuses"

    _place(pc, [_hold("104.28.222.0/24")])

    allowed, retry, why = pc.check(ip, NEUTRAL)
    assert allowed is False
    assert 0 < retry <= 3600, retry                       # what is LEFT of the hold, not a constant
    assert "104.28.222.0/24" in why and "operator" in why.lower(), why

    # An address OUTSIDE the /24 is untouched. A hold is narrow or it is not a hold.
    assert pc.check("104.28.223.55", NEUTRAL)[0] is True
    assert pc.check("104.28.221.255", NEUTRAL)[0] is True
    # ... and the two edges of the /24 are inside it.
    assert pc.check("104.28.222.0", NEUTRAL)[0] is False
    assert pc.check("104.28.222.255", NEUTRAL)[0] is False


def test_a_single_address_hold_covers_that_address_and_nothing_next_to_it(pc):
    _place(pc, [_hold("198.51.100.7")])
    assert pc.check("198.51.100.7", NEUTRAL)[0] is False
    assert pc.check("198.51.100.6", NEUTRAL)[0] is True
    assert pc.check("198.51.100.8", NEUTRAL)[0] is True


def test_an_ipv6_hold_holds_ipv6_and_does_not_leak_across_families(pc):
    """The two families are compared separately. An integer that matches in 32 bits must never
    match a 128-bit network that happens to share its low bits."""
    _place(pc, [_hold("2001:db8:abcd::/48")])
    assert pc.check("2001:db8:abcd::1", NEUTRAL)[0] is False
    assert pc.check("2001:db8:abce::1", NEUTRAL)[0] is True
    assert pc.check("1.2.3.4", NEUTRAL)[0] is True

    _reset(pc)
    _place(pc, [_hold("0.0.0.1/32")])                     # integer 1, as is "::1"
    assert pc.check("0.0.0.1", NEUTRAL)[0] is False
    assert pc.check("::1", NEUTRAL)[0] is True, "a v4 hold matched a v6 address"


def test_an_address_we_cannot_parse_is_held_by_nobody(pc):
    """An unparseable client address is an UNKNOWN, and absence of evidence is never a finding."""
    _place(pc, [_hold("0.0.0.0/16"), _hold("104.28.222.0/24")])
    for junk in ("", None, "unknown", "1.2.3", "::gg", "[2001:db8::1]"):
        assert pc.check(junk, NEUTRAL)[0] is True, junk
    # PROVE THE FIXTURE: the holds really are loaded, so the ALLOWs above are about the address.
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False


# =============================================================================================
# 3. EXPIRY. There is no permanent hold and there is no way to write one.
# =============================================================================================

def test_an_expired_hold_refuses_nobody(pc):
    ip = "104.28.222.55"

    # PROVE THE FIXTURE: the identical row with a FUTURE until does refuse this address.
    _place(pc, [_hold("104.28.222.0/24", ttl=3600)])
    assert pc.check(ip, NEUTRAL)[0] is False, "the fixture never held anybody; the test is void"

    _place(pc, [_hold("104.28.222.0/24", ttl=-1)])
    assert pc.check(ip, NEUTRAL)[0] is True
    assert pc.holds_state()["active"] == 0


def test_a_hold_with_no_until_at_all_refuses_nobody(pc):
    ip = "104.28.222.55"
    good = _hold("104.28.222.0/24")
    _place(pc, [good])
    assert pc.check(ip, NEUTRAL)[0] is False                  # fixture proved

    for bad in ({k: v for k, v in good.items() if k != "until"},
                dict(good, until=None), dict(good, until="3600"), dict(good, until=True),
                dict(good, until=[]), dict(good, until=float("nan"))):
        _place(pc, [bad])
        assert pc.check(ip, NEUTRAL)[0] is True, bad.get("until")


def test_a_hold_further_ahead_than_the_ceiling_is_refused(pc):
    """`until` being mandatory does not by itself prevent a permanent hold: `now + 10 years` is
    permanent wearing a costume. The ceiling is the same 24 hours BOUNDS["block_s"] already commits
    to for an automatic block, and it is committed in code so the environment cannot raise it."""
    assert pc.HOLD_MAX_S == pc.BOUNDS["block_s"][1] == 86400

    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24", ttl=86000)])         # just inside the ceiling
    assert pc.check(ip, NEUTRAL)[0] is False

    _place(pc, [_hold("104.28.222.0/24", ttl=86400 * 3650)])  # ten years
    assert pc.check(ip, NEUTRAL)[0] is True
    assert any("ahead" in k for k in pc.holds_state()["refused"]), pc.holds_state()["refused"]


def test_a_hold_that_runs_out_between_two_reads_stops_holding(pc):
    """EXPIRY IS RE-CHECKED AT MATCH TIME, NOT ONLY AT PARSE TIME. The file is cached until its
    mtime changes, which on a quiet day is hours; a hold checked only when it was parsed would keep
    refusing an address long after the operator's hour was up.

    THE CLOCK IS NOT SLEPT ON. A test that waits for a real second is a test that sometimes fails
    on a loaded machine; the hold is edited in the loaded cache instead, which is exactly the state
    the reader would be in.
    """
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24", ttl=3600)])
    assert pc.check(ip, NEUTRAL)[0] is False

    # The file has NOT changed and the cache is NOT re-read; only the clock has moved past `until`.
    pc._HOLDS["holds"][0]["until"] = time.time() - 1
    pc._HOLDS["loaded"] = time.time()                         # no re-read is due
    assert pc.check(ip, NEUTRAL)[0] is True
    assert pc.holds_state()["active"] == 0


# =============================================================================================
# 4. SCOPE. A hold names ONE project, or every project.
# =============================================================================================

def test_a_hold_scoped_to_another_service_is_ignored(pc):
    ip = "104.28.222.55"

    # PROVE THE FIXTURE, twice: our own name holds, and the wildcard holds.
    _place(pc, [_hold("104.28.222.0/24", service=SERVICE)])
    assert pc.check(ip, NEUTRAL)[0] is False, "a hold naming this service did not hold"
    _place(pc, [_hold("104.28.222.0/24", service="*")])
    assert pc.check(ip, NEUTRAL)[0] is False, "a wildcard hold did not hold"

    for other in ("jev-api", "colt-web", "JHW-WEB", "jhw", "jhw-web ", "*jhw-web"):
        _place(pc, [_hold("104.28.222.0/24", service=other)])
        assert pc.check(ip, NEUTRAL)[0] is True, other
    # ... and a missing or non-string service is ambiguous, so it is refused rather than guessed.
    for bad in (None, "", 1, ["*"]):
        _place(pc, [dict(_hold("104.28.222.0/24"), service=bad)])
        assert pc.check(ip, NEUTRAL)[0] is True, bad


def test_another_services_holds_do_not_eat_this_services_cap(pc):
    """A hold that can never apply here is dropped before the cap is counted. Otherwise a busy
    operator holding addresses on jev.best would silently stop jobhuntwow honouring its own."""
    rows = [_hold("203.0.113.%d" % i, service="jev-api") for i in range(pc.MAX_HOLDS + 50)]
    rows.append(_hold("104.28.222.0/24"))
    _place(pc, rows)
    assert pc.holds_state()["active"] == 1
    assert pc.holds_state()["over_cap"] == 0
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False


# =============================================================================================
# 5. THE EXEMPTIONS. A hold must never lock a real person out.
# =============================================================================================

def test_the_never_block_prefixes_are_served_under_a_hold(pc):
    """Blocking /.well-known/ turns one hold into a CERTIFICATE outage for every domain on the
    shared proxy -- ACME renewal and RFC 9116 live there. Blocking /api/ breaks the 401 probe every
    deploy verifier makes. NEVER_BLOCK_PREFIXES is the one list, and the hold path reads THAT list
    rather than a second copy of it.
    """
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24")])

    # PROVE THE FIXTURE: an ordinary path from the same address, in the same breath, IS refused.
    assert pc.check(ip, NEUTRAL)[0] is False

    for prefix in pc.NEVER_BLOCK_PREFIXES:
        assert prefix in ("/.well-known/", "/api/")
    for path in ("/api/me", "/api/admin/users", "/.well-known/acme-challenge/tok",
                 "/.well-known/security.txt", "/API/ME", "/api/", "/api/wp-login.php"):
        assert pc.check(ip, path)[0] is True, path


def test_an_authenticated_session_is_served_under_a_hold(pc):
    """PROVEN, not claimed. `authed` reaches this function only because the APPLICATION ITSELF
    answered 2xx to a credential this address presented; a scanner spraying Authorization headers
    collects 401s and never earns it."""
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check(ip, NEUTRAL, authed=False)[0] is False    # fixture proved
    assert pc.check(ip, NEUTRAL, authed=True)[0] is True
    assert pc.check(ip, "/app/jobs", authed=True)[0] is True


def test_an_unproven_credential_does_NOT_release_a_hold(pc):
    """THE DELIBERATE DIVERGENCE FROM decide(). The local shield downgrades its own BLOCK to a
    tarpit when a cookie is present, because that is the way back for a real customer whose address
    it convicted while they were away. A HOLD does not, because a cookie is trivially forged and a
    refusal any scanner can shrug off by sending one is not a refusal.

    The cost is real and it is named: a logged-OUT person inside a held network is refused until the
    hold runs out. That is why a hold is short-lived by construction and why a human places it.
    """
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24")])
    # `credential` is not even a parameter of check(): there is no argument that could soften this.
    assert "credential" not in pc.check.__code__.co_varnames
    assert pc.check(ip, NEUTRAL, authed=False)[0] is False


def test_an_allowlisted_address_is_served_under_a_hold(pc, monkeypatch):
    """PERSEUS_ALLOW_IPS is the operator's own address and whatever the project added. The same
    operator places the holds; the committed exemption wins over the transient instruction."""
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check(ip, NEUTRAL)[0] is False                  # fixture proved
    monkeypatch.setattr(pc, "ALLOW_IPS", {ip})
    assert pc.check(ip, NEUTRAL)[0] is True
    assert pc.check("104.28.222.56", NEUTRAL)[0] is False, "the exemption covered the neighbours"


def test_with_enforcement_off_a_hold_only_says_what_it_would_have_done(pc, monkeypatch):
    """PERSEUS_ENFORCE=0 is how a new project is WATCHED before it is armed. It is the master arm
    switch for acting on a verdict, and a hold is a verdict; the alternative -- an operator
    instruction that overrides the arm switch -- would mean a project the operator believes is in
    observation mode can refuse traffic."""
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check(ip, NEUTRAL)[0] is False                  # fixture proved
    monkeypatch.setattr(pc, "ENFORCE", False)
    assert pc.check(ip, NEUTRAL)[0] is True
    assert len(_evts(pc, "perseus_shield_would_hold")) == 1, "it went quiet instead of saying so"


def test_the_whole_client_being_disabled_disables_holds_too(pc, monkeypatch):
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check(ip, NEUTRAL)[0] is False
    monkeypatch.setattr(pc, "ENABLED", False)
    assert pc.check(ip, NEUTRAL) == (True, 0, "")


# =============================================================================================
# 6. ONE BAD ROW MUST NOT RELEASE THE ADDRESSES BESIDE IT.
# =============================================================================================

def test_a_malformed_cidr_does_not_discard_the_valid_entries_beside_it(pc):
    """Exactly the discipline `_load()` already applies to a bad PATTERN: skip the row, keep the
    file. A hold list that collapses on one typo hands the operator's whole instruction back."""
    # PROVE THE ROWS REALLY ARE MALFORMED, rather than trusting that they look it.
    for junk in ("not-an-address", "999.1.1.1", "1.2.3.4/33", "", "10.0.0.0/../.."):
        assert pcmod._parse_cidr(junk) is None, junk

    rows = [_hold("not-an-address"),
            _hold("104.28.222.0/24"),               # good, between two bad ones
            _hold("999.1.1.1"),
            _hold("2001:db8:abcd::/48"),            # good
            _hold("1.2.3.4/33"),
            {"cidr": "203.0.113.0/24"},             # no service, no until
            "a string where an object should be",
            None]
    _place(pc, rows)

    assert pc.check("104.28.222.55", NEUTRAL)[0] is False, "a valid hold was lost with the bad ones"
    assert pc.check("2001:db8:abcd::99", NEUTRAL)[0] is False
    assert pc.check("203.0.113.9", NEUTRAL)[0] is True
    st = pc.holds_state()
    assert st["active"] == 2
    assert sum(st["refused"].values()) == 6, st["refused"]


def test_a_hold_broader_than_the_floor_is_refused(pc):
    """AN OPERATOR CONTROL THAT CAN REFUSE EVERYBODY IS WORSE THAN NO CONTROL. 0.0.0.0/0 is the
    whole internet and 10.0.0.0/8 is sixteen million strangers; the producer's unit is an address
    or a /24. Refusing costs the operator a second, narrower hold -- not refusing costs a customer
    their site, with no human watching four of these five.
    """
    assert pc.HOLD_MIN_PREFIX == {4: 16, 6: 32}

    # PROVE THE FIXTURE: the parser ACCEPTS these; it is the hold reader that refuses them.
    for wide in ("0.0.0.0/0", "10.0.0.0/8", "::/0", "2001:db8::/16"):
        assert pcmod._parse_cidr(wide) is not None, wide

    _place(pc, [_hold("0.0.0.0/0"), _hold("10.0.0.0/8"), _hold("::/0"), _hold("2001:db8::/16")])
    assert pc.holds_state()["active"] == 0
    for ip in ("1.2.3.4", "10.1.2.3", "2001:db8::1", "::1"):
        assert pc.check(ip, NEUTRAL)[0] is True, ip
    assert sum(pc.holds_state()["refused"].values()) == 4

    # ... and the floor itself is honoured, so the refusal above is about WIDTH and not about /16.
    _place(pc, [_hold("10.0.0.0/16"), _hold("2001:db8::/32")])
    assert pc.holds_state()["active"] == 2
    assert pc.check("10.0.5.6", NEUTRAL)[0] is False
    assert pc.check("2001:db8::1", NEUTRAL)[0] is False
    assert pc.check("10.1.5.6", NEUTRAL)[0] is True


def test_the_cap_holds_and_says_so(pc):
    """Bounded for the same two reasons MAX_BLOCKS is: memory, and blast radius. Past the cap we
    honour the first MAX_HOLDS and ANNOUNCE it -- silently honouring a prefix of the operator's
    file is a control that quietly stopped working, which is the defect this estate has paid for
    more than any other."""
    assert pc.MAX_HOLDS == 256, "the cap the contract names"
    n = pc.MAX_HOLDS + 44
    # One distinct /32 per row, in file order, so "which rows survived the cap" is countable:
    # row i is 10.1.<i // 256>.<i % 256>.
    rows = [_hold("10.1.%d.%d" % (i // 256, i % 256), why="hold %d" % i) for i in range(n)]
    _place(pc, rows)

    st = pc.holds_state()
    assert st["active"] == pc.MAX_HOLDS
    assert st["over_cap"] == 44
    assert pc.check("10.1.0.0", NEUTRAL)[0] is False, "the first hold was not honoured"
    assert pc.check("10.1.0.255", NEUTRAL)[0] is False          # row 255, the last honoured one..
    assert pc.check("10.1.1.0", NEUTRAL)[0] is True             # ..row 256 is the first one dropped
    assert pc.check("10.1.1.43", NEUTRAL)[0] is True            # ..and so is the last, row 299

    # IT SAYS SO. A cap nobody can see biting is indistinguishable from a cap that never bit.
    said = _evts(pc, "perseus_holds_refused")
    assert len(said) == 1 and said[0]["over_cap"] == 44 and said[0]["cap"] == 256, said


def test_the_refusals_are_reported_once_per_version_of_the_file(pc):
    """EDGE-TRIGGERED. A warning on every reload trains the operator to read past the one that
    matters; a warning that never fires is not a warning. The mtime is the edge."""
    _place(pc, [_hold("not-an-address"), _hold("104.28.222.0/24")])
    for _ in range(20):
        pc._HOLDS["loaded"] = 0.0                              # a read is due, every time
        assert pc.check("104.28.222.55", NEUTRAL)[0] is False
    assert len(_evts(pc, "perseus_holds_refused")) == 1, "it re-reported a steady state"

    # A NEW VERSION OF THE FILE REPORTS AGAIN -- otherwise the first bad file would silence every
    # later one, and the operator's second typo would be invisible.
    _place(pc, [_hold("also-not-an-address"), _hold("104.28.222.0/24")])
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False
    assert len(_evts(pc, "perseus_holds_refused")) == 2


def test_a_clean_file_says_nothing(pc):
    """BENIGN-EVERY-TIME IS THE ENEMY. The refusal line must not fire on an ordinary hold list."""
    _place(pc, [_hold("104.28.222.0/24"), _hold("2001:db8::/32")])
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False
    assert _evts(pc, "perseus_holds_refused") == []


# =============================================================================================
# 7. FAIL OPEN. Every read failure serves the request.
# =============================================================================================

def test_an_absent_holds_file_changes_nothing_and_raises_nothing(pc):
    assert not os.path.exists(pc.HOLDS)
    assert pc.check("104.28.222.55", NEUTRAL) == (True, 0, "")
    assert pc.is_held("104.28.222.55") is False
    assert pc.active_holds() == []
    assert pc.holds_state()["active"] == 0
    assert _events(pc) == [], "an absent file is the normal state and must be silent"


def test_a_corrupt_file_keeps_the_holds_we_already_had(pc):
    """NEVER CLEAR ON A READ FAILURE -- the same rule `_load()` follows for the blocklist. A file
    caught half-written by the producer must not release every address the operator held."""
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False      # fixture proved

    for corrupt in ('{"generated": 1, "holds": [', "", "\x00\x01\x02", "not json at all",
                    "[]"):
        _rewrite(pc, corrupt, due=True)
        assert pc.check("104.28.222.55", NEUTRAL)[0] is False, (
            "a corrupt file released the addresses we were already holding: %r" % corrupt)
    assert pc.holds_state()["active"] == 1

    # PROVE THE READER WAS REALLY TRYING. The identical write path, with VALID contents that lift
    # the hold, does change the answer -- so the six refusals above are the reader failing to parse
    # and keeping what it had, not the reader never looking.
    _rewrite(pc, json.dumps({"generated": 2, "holds": []}), due=True)
    assert pc.check("104.28.222.55", NEUTRAL)[0] is True


def test_a_file_that_cannot_be_OPENED_keeps_the_holds_we_already_had(pc, tmp_path):
    """A DIRECTORY WHERE A FILE SHOULD BE. os.stat succeeds and open() raises -- IsADirectoryError
    on Linux, PermissionError on Windows -- which is the same shape as the uid-10001-vs-root
    permission fault that silently discarded jobhuntwow's event log for its whole life. Reproduced
    identically on both platforms without a POSIX-only call and without chmod.
    """
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False      # fixture proved

    d = tmp_path / "holds_is_a_directory"
    d.mkdir()
    pc.HOLDS = str(d)
    pc._HOLDS["loaded"] = 0.0
    with pytest.raises(OSError):                               # PROVE THE FIXTURE REALLY FAILS
        open(str(d), encoding="utf-8").read()
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False
    assert pc.holds_state()["active"] == 1


def test_a_hold_row_that_explodes_on_read_does_not_take_the_others_with_it(pc):
    """A row shaped like nothing we imagined. `_parse_hold` is wrapped per row, so an exception is
    ONE skipped hold, never the file."""
    class Exploding(dict):
        def get(self, *a, **k):
            raise RuntimeError("boom")

    # PROVE THE FIXTURE EXPLODES, or this test measures the harness.
    with pytest.raises(RuntimeError):
        pcmod._parse_hold(Exploding(), time.time())

    pc._HOLDS.update(loaded=time.time(), mtime=1.0,
                     holds=[], refused={}, dropped=0, reported=None)
    rows = [Exploding(), _hold("104.28.222.0/24")]
    good, refused = [], {}
    for row in rows:                                           # the loader's own per-row discipline
        try:
            entry, kind = pcmod._parse_hold(row, time.time())
        except Exception as exc:
            entry, kind = None, "unreadable row (%s)" % type(exc).__name__
        if entry is not None:
            good.append(entry)
        elif kind:
            refused[kind] = refused.get(kind, 0) + 1
    assert len(good) == 1 and sum(refused.values()) == 1

    # ... and end to end, through the real reader, from a real file.
    _place(pc, [{"cidr": {"nested": "object"}, "service": SERVICE, "until": time.time() + 60},
                _hold("104.28.222.0/24")])
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False


def test_nothing_in_the_hold_path_can_raise_out_of_check(pc, monkeypatch):
    """THE LAST LINE OF DEFENCE. A defence that 500s the site it protects is worse than none, so
    the whole hold path is inside check()'s own try -- proven by making the reader itself throw."""
    def boom(*_a, **_k):
        raise RuntimeError("the reader is broken")
    monkeypatch.setattr(pc, "_load_holds", boom)
    assert pc.check("104.28.222.55", NEUTRAL) == (True, 0, "")
    assert pc.hold_for("104.28.222.55") is None
    assert pc.is_held("104.28.222.55") is False
    assert pc.active_holds() == []
    assert pc.holds_state()["active"] == 0


# =============================================================================================
# 8. THE CACHING DISCIPLINE. Never a disk read per request; never a stale hold forever.
# =============================================================================================

def test_the_file_is_not_re_read_on_every_request(pc):
    """A list consulted on every request must never become a disk read on every request -- the same
    rule, and the same RELOAD_S, as the blocklist reader.

    MEASURED, not asserted from the source: the file on disk is REPLACED and the answer does not
    change, which can only be true if the replacement was never read.
    """
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False
    loaded_at = pc._HOLDS["loaded"]
    assert loaded_at > 0

    _rewrite(pc, json.dumps({"generated": 1, "holds": []}))     # the operator lifted the hold...
    for _ in range(50):
        assert pc.check("104.28.222.55", NEUTRAL)[0] is False   # ...and we have not looked yet
    assert pc._HOLDS["loaded"] == loaded_at, "it re-read the file inside RELOAD_S"

    pc._HOLDS["loaded"] = time.time() - pc.RELOAD_S - 1         # now a read is due
    assert pc.check("104.28.222.55", NEUTRAL)[0] is True


def test_an_unchanged_mtime_is_not_re_parsed(pc):
    """The second half of the discipline: even when a read is DUE, an unchanged mtime costs one
    os.stat and nothing else. Proven by rewriting the contents while pinning the mtime -- if the
    file were re-parsed, the new contents would win."""
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False
    st = os.stat(pc.HOLDS)

    with open(pc.HOLDS, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"generated": 2, "holds": []}))
    os.utime(pc.HOLDS, (st.st_atime, st.st_mtime))             # same mtime, different contents
    pc._HOLDS["loaded"] = 0.0
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False

    os.utime(pc.HOLDS, (st.st_atime, st.st_mtime + 5))         # a real change
    pc._HOLDS["loaded"] = 0.0
    assert pc.check("104.28.222.55", NEUTRAL)[0] is True


# =============================================================================================
# 9. IT IS VISIBLE, AND IT IS VISIBLE ONCE.
# =============================================================================================

def test_a_matched_hold_emits_one_line_through_the_existing_writer(pc, capsys):
    """THE SAME WRITER `observe()` USES. Same shape, same file, same stdout as `evt=http`, so
    colt-web's brain and Loki both see it without either learning a new format -- and no Telegram,
    no token, no network, because alerting lives in colt-web and must never live in five repos.

    ONE LINE, NOT ONE PER REQUEST. A held address may make hundreds of requests.
    """
    ip = "104.28.222.55"
    _place(pc, [_hold("104.28.222.0/24", why="operator: Block /24 1h", by="telegram")])
    for _ in range(50):
        assert pc.check(ip, NEUTRAL)[0] is False

    lines = _evts(pc, "perseus_shield_hold")
    assert len(lines) == 1, "one line per request is how the line that matters gets read past"
    rec = lines[0]
    assert rec["ip"] == ip and rec["service"] == SERVICE
    assert rec["cidr"] == "104.28.222.0/24"
    assert rec["why"] == "operator: Block /24 1h" and rec["by"] == "telegram"
    assert rec["scope"] == SERVICE and 0 < rec["seconds"] <= 3600
    assert rec["path"] == NEUTRAL
    # stdout too: the docker json-file driver scrapes it, which is the only reason the jobhuntwow
    # abuse could be reconstructed when the shared-volume write was broken.
    assert '"perseus_shield_hold"' in capsys.readouterr().out

    # A DIFFERENT ADDRESS IS A DIFFERENT EDGE.
    assert pc.check("104.28.222.56", NEUTRAL)[0] is False
    assert len(_evts(pc, "perseus_shield_hold")) == 2


def test_the_exemptions_are_announced_and_not_silent(pc):
    """AN EXEMPTION FROM ENFORCEMENT MUST NEVER BECOME AN EXEMPTION FROM OBSERVATION. /api/ became
    a hiding place three times in this codebase by being quietly waved through."""
    _place(pc, [_hold("104.28.222.0/24")])

    assert pc.check("104.28.222.10", "/api/me")[0] is True
    assert pc.check("104.28.222.11", NEUTRAL, authed=True)[0] is True
    said = _evts(pc, "perseus_shield_hold_exempt")
    assert len(said) == 2, said
    assert {s["ip"] for s in said} == {"104.28.222.10", "104.28.222.11"}
    assert any("prefix" in s["reason"] for s in said)
    assert any("authenticated" in s["reason"] for s in said)
    for s in said:
        assert s["cidr"] == "104.28.222.0/24", "a line that does not NAME its subject teaches nothing"


def test_the_channel_reports_itself_in_the_state_and_in_the_heartbeat(pc, capsys):
    """THE OBSERVER MUST BE OBSERVED. A feature nobody has seen working is off, and the Fleet page
    is where the operator looks. Absence of this number there means exactly one thing: that project
    is not running a version that has holds."""
    _place(pc, [_hold("104.28.222.0/24"), _hold("2001:db8::/32", ttl=-5)])

    st = pc.shield_state()["holds"]
    assert st["file"] == pc.HOLDS and st["cap"] == pc.MAX_HOLDS
    assert st["active"] == 1 and st["cidrs"] == ["104.28.222.0/24"]
    assert st["age_s"] is not None and st["generated"] > 0
    assert pc.status()["shield"]["holds"]["active"] == 1

    # A COSMETIC FIELD MAY NEVER DECIDE THE ANSWER. A producer that stamps `generated` with a
    # string must not make the status page report zero held addresses while one is held -- a wrong
    # status is worse than none, and this is the shape in which a nice-to-have becomes an outage.
    pc._HOLDS["generated"] = "yesterday"
    assert pc.shield_state()["holds"]["active"] == 1
    assert pc.shield_state()["holds"]["generated"] == 0

    pc._CACHE["beat"] = 0.0                                    # a heartbeat is due
    pc.check("104.28.222.55", NEUTRAL)
    beats = [json.loads(l) for l in capsys.readouterr().out.splitlines()
             if l.startswith("{") and '"perseus_beat"' in l]
    assert beats and beats[-1]["holds"] == 1, beats


# =============================================================================================
# 10. THE PATTERN PATH IS UNCHANGED, AND THE TWO SHIELDS COEXIST.
# =============================================================================================

def test_the_published_pattern_path_is_untouched(pc):
    """The hub's half of check() must behave exactly as it did: same evaluation, same order, same
    60-second retry window, same reason string. Holds are an ADDITION, not a rewrite."""
    import re
    pc._CACHE.update(patterns=[("r-7", re.compile(r"/wp-login\.php", re.I))], cycle=9,
                     loaded=time.time())
    allowed, retry, why = pc.check("192.0.2.1", "/wp-login.php")
    assert (allowed, retry) == (False, 60)
    assert why == "perseus rule r-7 (cycle 9)"

    # AND THE PATTERN WINS OVER A HOLD, because a rule four models agreed on and a promotion gate
    # approved is a stronger statement than one operator keystroke -- and because reversing the
    # order would change what the hub's half returns for a held address.
    _place(pc, [_hold("192.0.2.0/24")])
    pc._CACHE.update(loaded=time.time())
    assert pc.check("192.0.2.1", "/wp-login.php")[2] == "perseus rule r-7 (cycle 9)"
    assert pc.check("192.0.2.1", NEUTRAL)[2].startswith("operator hold")


def test_holds_are_honoured_where_the_local_shield_stands_down_and_where_it_is_armed(
        pc, monkeypatch):
    """LOCAL IS OFF ON cybergod.ai (shield.py is its sibling there) and ON everywhere else. A hold
    is delivered by the hub's CHANNEL, not by the local shield, so it must not be gated on LOCAL --
    otherwise the one site with an operator console would be the one site that ignores him."""
    _place(pc, [_hold("104.28.222.0/24", service="*")])
    assert pc.LOCAL is False
    assert pc.check("104.28.222.55", NEUTRAL)[0] is False

    monkeypatch.setattr(pc, "LOCAL", True)
    assert pc.check("104.28.222.56", NEUTRAL)[0] is False

    # ... and an app with a catch-all, which disarms the LOCAL shield entirely, still honours it:
    # "this app serves every path" says nothing about whether the operator wants an address held.
    pc._catchall[0] = True
    try:
        assert pc.decide("104.28.222.57", NEUTRAL)[0] == "ALLOW"    # the local shield is off...
        assert pc.check("104.28.222.57", NEUTRAL)[0] is False       # ...and the hold still holds
    finally:
        pc._catchall[0] = False


def test_the_local_shields_own_verdict_is_not_polluted_by_a_hold(pc, monkeypatch):
    """`_decide_raw` is a pure function of LOCALLY RECORDED state and must stay one. Folding an
    external operator decision into it would mean the evidence a project records changes because
    somebody typed a command on a phone, and one request would emit two decision lines."""
    monkeypatch.setattr(pc, "LOCAL", True)
    _place(pc, [_hold("104.28.222.0/24")])
    assert pc.decide("104.28.222.55", NEUTRAL) == ("ALLOW", "")
    assert pc.is_blocked("104.28.222.55") is False
    assert pc.shield_state()["blocked"] == {}


# =============================================================================================
# 11. IT STILL CANNOT REACH THE FIREWALL OR THE NETWORK.
# =============================================================================================

def test_the_holds_code_added_no_way_to_reach_a_firewall_or_a_socket():
    """Amnezia VPN shares this host. The shield never touches iptables/nft/ufw -- StGB
    §202a/§202b/§303a/§303b, EU Directive 2013/40, CFAA §1030 -- and detection and reporting scale
    where retaliation is illegal and pointless.

    THE PROPERTY, not a grep for the word: a module that imports neither `subprocess` nor `socket`
    cannot shell out to nft and cannot connect back to anything. This is the same floor
    tests/test_perseus_shield.py commits to, restated here because the holds reader is new code on
    that file's most privileged path -- and it is the reason `ipaddress` is NOT imported there and
    the arithmetic is graded against it from this file instead.
    """
    import ast
    with open(SOURCE, encoding="utf-8") as fh:
        src = fh.read()
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert names <= {"asyncio", "json", "os", "re", "threading", "time", "hashlib"}, sorted(names)

    # PROVE THE CHECK DISCRIMINATES: the same walk over a module that DOES shell out must fail it.
    bad = "import subprocess\nsubprocess.run(['nft', 'add'])\n"
    bad_names = {a.name for n in ast.walk(ast.parse(bad)) if isinstance(n, ast.Import)
                 for a in n.names}
    assert not bad_names <= {"asyncio", "json", "os", "re", "threading", "time", "hashlib"}

    # NO CALL SITE THAT COULD EXECUTE ANYTHING, even without importing subprocess.
    calls = {"%s.%s" % (n.func.value.id, n.func.attr)
             for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and isinstance(n.func.value, ast.Name)}
    assert not (calls & {"os.system", "os.popen", "os.execv", "os.execvp", "os.execl",
                         "os.spawnv", "os.spawnl", "os.fork", "os.startfile"}), sorted(calls)

    # AND NO FIREWALL COMMAND HIDING IN A STRING THE CODE COULD PASS TO ONE.
    #
    # THE DOCSTRINGS AND THE COMMENTS ARE EXCLUDED, AND THAT IS THE WHOLE POINT. A plain grep for
    # "iptables" over this file matches the paragraph that EXPLAINS why there is no iptables --
    # a check matching its own explanatory comment has happened five separate times in this
    # codebase and it did again in the first draft of this test. Comments never reach the AST;
    # docstrings do, so they are subtracted by identity.
    tree = ast.parse(src)
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docs.add(id(body[0].value))
    live = [n.value.lower() for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]
    assert live, "no executable string literals were found at all; the subtraction is too greedy"
    for word in ("iptables", "nft", "ufw", "route add", "/sbin/"):
        hits = [s for s in live if word in s]
        assert not hits, "%r appears in an executable string literal: %r" % (word, hits[:3])

    # PROVE THE SUBTRACTION STILL CATCHES A REAL ONE: the same walk over a module whose docstring
    # promises no firewall while its code names one must FAIL.
    planted = ast.parse('"""we never touch iptables."""\nCMD = "iptables -A INPUT -j DROP"\n')
    pdocs = {id(planted.body[0].value)}
    plive = [n.value.lower() for n in ast.walk(planted)
             if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in pdocs]
    assert [s for s in plive if "iptables" in s], "the check cannot fail, so it is not a check"
