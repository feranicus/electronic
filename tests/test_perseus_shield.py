"""test_perseus_shield.py — the LOCAL shield that every project now carries.

WHAT THIS FILE EXISTS TO PROVE. Four of the five sites (jobhuntwow, jev.best,
klimaanlage-preise.de, s4biz.io) ran perseus/client.py as a pattern-list lookup against a list the
hub had never published, so they blocked NOTHING for their entire lives. The detection that works
lived in webapp/backend/app/shield.py, which is not copied anywhere. The table moved into the file
that IS copied, and the enforcement came with it.

THE FOUR THINGS THAT MATTER MORE THAN THE DETECTION, in order:
  1. a real person is never locked out -- not by volume, not while logged in, not on a page we
     actually serve;
  2. the control cannot reach the firewall, the network, or a credential, on a host it shares with
     Amnezia VPN;
  3. every decision is bounded, expiring and reversible, because no human is in this loop;
  4. every decision is VISIBLE, or it is not a control.

HOW THESE TESTS ARE WRITTEN. Each one proves its FIXTURE reproduces the condition before asserting
on the outcome -- a test that blocks nobody because the evidence never accumulated is a test of the
harness. Properties are asserted, never strings the source also contains. Nothing here touches the
network, the real event log, or a POSIX-only API: the suite runs on the operator's Windows box.
"""
import ast
import importlib.util
import json
import os
import pathlib
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "perseus", "client.py")

_BACKEND = os.path.join(ROOT, "webapp", "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


def _import_app():
    """Import webapp/backend/app even when the suite has already bound a bare namespace `app`.

    Same problem, same fix as tests/test_shield.py: conftest puts the repo root and the engine
    scripts on sys.path first and something in that order binds an `app` with no __init__, so the
    package is bound explicitly rather than by import order.
    """
    import importlib
    mod = sys.modules.get("app")
    if mod is not None and not getattr(mod, "__file__", None):
        for k in [k for k in sys.modules if k == "app" or k.startswith("app.")]:
            sys.modules.pop(k, None)
    if _BACKEND in sys.path:
        sys.path.remove(_BACKEND)
    sys.path.insert(0, _BACKEND)
    return importlib.import_module("app")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------------------------
# Reading the SOURCE FILE rather than the imported module, so a comparison is a measurement.
#
# `assert module_a.PROBE_RE.pattern == module_b.PROBE_RE.pattern` is worth nothing when one of them
# imported the other: it is `x == x` wearing a costume. These helpers parse perseus/client.py off
# disk and evaluate the literal, so the thing shield.py ended up with is compared against what the
# file DECLARES, independently of which of the three resolution candidates was taken.
# ---------------------------------------------------------------------------------------------
def _assigned_call_arg(src, name):
    """The first literal argument of `NAME = <something>(<literal>, ...)` at module level."""
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            if isinstance(node.value, ast.Call) and node.value.args:
                return ast.literal_eval(node.value.args[0])
    return None


def _assigned_literal(src, name):
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def _class_table(src):
    """[(class name, pattern text)] from the CLASSES list literal, without importing anything."""
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "CLASSES" for t in node.targets):
            out = []
            for elt in node.value.elts:
                out.append((ast.literal_eval(elt.elts[0]),
                            ast.literal_eval(elt.elts[1].args[0])))
            return out
    return None


# ---------------------------------------------------------------------------------------------
# THE FIXTURE. The module is imported once (it is stateless-on-disk by design), and every test gets
# it with its memory cleared and its three write paths redirected into tmp_path.
#
# REDIRECTING THE WRITES IS NOT TIDINESS. `EVENTS` and `BEAT_DIR` default to /var/log/colt/...,
# which on Windows resolves to C:\var\log\colt and would be CREATED by os.makedirs on the
# operator's own disk. A test that leaves marks on the machine that runs it is a test nobody trusts.
# ---------------------------------------------------------------------------------------------
@pytest.fixture
def pc(tmp_path, monkeypatch):
    import perseus.client as m
    monkeypatch.setattr(m, "EVENTS", str(tmp_path / "events.log"))
    monkeypatch.setattr(m, "BEAT_DIR", str(tmp_path / "beats"))
    monkeypatch.setattr(m, "BLOCKLIST", str(tmp_path / "no-such-blocklist.json"))
    monkeypatch.setattr(m, "LOCAL", True)
    monkeypatch.setattr(m, "ENFORCE", True)
    monkeypatch.setattr(m, "ENABLED", True)
    for d in (m._hits, m._fps, m._blocked, m._seen_ips, m._miss, m._slow,
              m._served, m._authed, m._recent, m._told):
        d.clear()
    m._tarpits[0] = 0
    m._catchall[0] = False
    m._CACHE["beat"] = time.time()          # no heartbeat write during a test
    m._CACHE["warned"] = False
    m._CACHE["thresholds"] = {}
    m._CACHE["loaded"] = time.time()        # _load() answers from cache, never stats a real file
    yield m
    for d in (m._hits, m._fps, m._blocked, m._seen_ips, m._miss, m._slow,
              m._served, m._authed, m._recent, m._told):
        d.clear()
    m._tarpits[0] = 0
    m._catchall[0] = False


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
# Four probe shapes, none of them a honeytoken (weight 6) and none of them our own route, so the
# arithmetic under test is exactly probe_path x 3. 2 paths = 6 (>= tarpit_after 5, < block_after
# 12); 4 paths = 12 (== block_after). Four distinct 404s also stays under NF_DISTINCT (6), so the
# not_found rule cannot quietly contribute and change what is being measured.
PROBES = ("/.env", "/.git/config", "/phpmyadmin/", "/xmlrpc.php")


def _feed(m, ip, paths, status=404, ua=UA):
    for p in paths:
        m.watch(ip, p, status, ua, "GET")


def _events(pc_mod):
    """Every record written to the redirected event log, as parsed JSON."""
    path = pc_mod.EVENTS
    if not os.path.exists(path):
        return []
    out = []
    for line in _read(path).splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


# =============================================================================================
# 1. ONE IMPLEMENTATION. The table shield.py scores with is the table perseus/client.py declares.
# =============================================================================================

def test_shield_resolves_the_shared_table_and_says_where_from():
    """WIRING, not behaviour. shield.py can no longer define the regex, so if the resolution fails
    it detects nothing -- and that state must be readable rather than inferred from a quiet log."""
    _import_app()
    from app import shield as sh
    assert sh.DETECTION != "unavailable", (
        "shield.py could not resolve the shared detection table from any of its three candidates; "
        "probe detection would be OFF in production")
    assert sh.probe_shape("/wp-login.php") is True     # it resolved something that WORKS
    assert sh.probe_shape("/login") is False


def test_shield_probe_regex_is_the_one_the_source_file_declares():
    """The compiled pattern shield.py holds, against the literal parsed out of perseus/client.py.

    Compared against the FILE, not against the module shield imported, so this cannot degenerate
    into `x == x`. The mutation below proves the comparison discriminates at all.
    """
    _import_app()
    from app import shield as sh
    declared = _assigned_call_arg(_read(SOURCE), "PROBE_RE")
    assert declared, "perseus/client.py no longer declares PROBE_RE = re.compile(<literal>)"
    assert sh._PROBE_RE.pattern == declared

    # PROVE THE COMPARISON CAN FAIL. One alternation removed from the declared text must not
    # compare equal -- otherwise the assertion above would pass for any two strings.
    mutated = declared.replace(r"|/wp-json(?:$|/)", "", 1)
    assert mutated != declared, "the mutation did not change the text; the proof is void"
    assert sh._PROBE_RE.pattern != mutated


def test_shield_class_vocabulary_is_the_one_the_source_file_declares():
    """The corpus vocabulary must move with the scoring rules or the digest cannot explain a block."""
    _import_app()
    from app import shield as sh
    declared = _class_table(_read(SOURCE))
    assert declared and len(declared) >= 20
    assert [n for n, _ in sh.CLASSES] == [n for n, _ in declared]
    assert [rx.pattern for _n, rx in sh.CLASSES] == [p for _n, p in declared]


def test_honeytokens_are_the_source_files_honeytokens():
    _import_app()
    from app import shield as sh
    assert tuple(sh.HONEYTOKENS) == tuple(_assigned_literal(_read(SOURCE), "HONEYTOKENS"))


def test_distributed_copies_cannot_carry_a_different_table():
    """Every perseus_client.py in this repo is a COPY of perseus/client.py. A copy that carries the
    table must carry THE table.

    A copy that predates the shared table is not drift, it is a copy `perseus.py --clients` has not
    refreshed yet (ship.py runs that before this suite); it is reported rather than asserted on. A
    copy that has a DIFFERENT table is the failure this test exists for.
    """
    declared = _assigned_call_arg(_read(SOURCE), "PROBE_RE")
    # The two targets perseus.py::CLIENT_TARGETS names INSIDE this repository. The other three
    # projects live in sibling trees that are not present on every machine, so they are refreshed
    # and compared by `perseus.py --clients`, which ship.py runs before this suite.
    copies = [os.path.join(ROOT, "webapp", "backend", "app", "perseus_client.py"),
              os.path.join(ROOT, "jobhuntwow-app", "backend", "app", "perseus_client.py")]
    present = [p for p in copies if os.path.exists(p)]
    assert present, "no distributed copy found at all - perseus.py --clients has never run here"
    stale = []
    for p in present:
        got = _assigned_call_arg(_read(p), "PROBE_RE")
        if got is None:
            stale.append(p)
            continue
        assert got == declared, "%s carries a DIFFERENT detection table than perseus/client.py" % p
    if stale:
        print("copies still predating the shared table (perseus.py --clients refreshes them): %s"
              % ", ".join(stale))


def test_client_and_shield_agree_on_every_path_when_given_the_same_route_list():
    """Behavioural parity: one implementation, so the same inputs must give the same answers.

    The route predicate is the ONLY thing that differs between the two callers, so it is passed in
    explicitly here. Both directions are represented in the corpus and both are asserted non-empty:
    a corpus on which everything answers False would pass this test while proving nothing.
    """
    _import_app()
    from app import shield as sh
    import perseus.client as m
    corpus = ["/", "/login", "/app/admin", "/partners", "/assets/index-a1b2c3.js",
              "/robots.txt", "/api/me", "/api/wp-login.php", "/wp-login.php", "/.env",
              "/%2eenv", "/assets/../../.env", "/[workspace]/", "//slug", "/DOCS.md",
              "/@fs/etc/passwd", "/geoserver/web/", "/info", "/api/info", "/information",
              "/?XDEBUG_SESSION_START=phpstorm", "/1b7e06/", "/app/9f2c1a", "/kubeconfig"]
    got = {p: (sh.probe_shape(p), m.probe_shape(p, is_ours=sh.is_our_route)) for p in corpus}
    assert any(a for a, _b in got.values()), "corpus contains no probe at all"
    assert any(not a for a, _b in got.values()), "corpus contains no legitimate route at all"
    differ = {p: v for p, v in got.items() if v[0] != v[1]}
    assert not differ, "shield and client disagree: %r" % differ


def test_the_route_predicate_is_actually_consulted():
    """A client copied into a project that has not declared /app/admin must SCORE it; shield.py,
    which owns cybergod's route list, must not. That difference is the predicate doing its job --
    and it is why the parity test above has to pass the predicate in."""
    _import_app()
    from app import shield as sh
    import perseus.client as m
    assert sh.probe_shape("/app/admin") is False           # cybergod serves it
    assert m.probe_shape("/app/admin", is_ours=None) is True  # an unknown project does not


# =============================================================================================
# 2. VARIETY, NOT VOLUME. The rule the 439-404 and 362-404 visitors of 10 Aug 2026 paid for.
# =============================================================================================

def test_a_real_visitor_hammering_ONE_stale_path_is_never_blocked(pc):
    """Five hundred 404s on the SAME path is a person with a dead bookmark, not a scanner.

    THE FIXTURE IS PROVED FIRST. If the path chosen here were probe-shaped the test would be
    measuring the probe rule and would pass for the wrong reason, so that is asserted before a
    single request is fed.
    """
    ip, path = "203.0.113.7", "/old-blog-post-from-2019"
    assert pc.probe_shape(path, is_ours=pc.local_is_ours) is False, (
        "the fixture path is itself probe-shaped; this test would not be measuring volume")
    assert pc.is_honeytoken(path) is False

    for _ in range(500):
        pc.watch(ip, path, 404, UA, "GET")
        verdict, why = pc.decide(ip, path)
        assert verdict == "ALLOW", "a real visitor was %s after repeating one 404: %s" % (verdict, why)

    # THE MECHANISM, not just the outcome: variety is one, however large the volume.
    assert len(pc._miss.get(ip, {})) == 1
    assert pc.is_blocked(ip) is False
    assert pc.slow_scan(ip)[0] == 0          # a non-probe 404 records no long-window evidence


def test_the_same_volume_across_distinct_probe_paths_IS_blocked(pc):
    """The control for the test above. Same address, same count, VARIETY instead of repetition.

    Without this, "nobody was blocked" would be indistinguishable from "the shield does nothing",
    which is exactly the state four of these projects were in.
    """
    ip = "203.0.113.8"
    _feed(pc, ip, PROBES)
    verdict, why = pc.decide(ip, "/xmlrpc.php")
    assert verdict == "BLOCK", why
    assert pc.is_blocked(ip) is True


def test_a_low_and_slow_scan_crosses_the_long_window_the_five_minute_rule_throws_away(pc):
    """SLOW_DISTINCT distinct probe paths, fed with the fast window's evidence expired.

    THE FIXTURE IS PROVED: `_hits` is emptied after feeding, so the fast score is zero and the only
    thing that can convict is the 24-hour distinct-path count. Without that step this would be the
    fast rule again under another name.
    """
    ip = "203.0.113.9"
    want = pc.slow_distinct()
    paths = ["/probe-%d/.env" % i for i in range(want)]
    _feed(pc, ip, paths)
    assert pc.slow_scan(ip)[0] >= want
    pc._hits.clear()                                   # the five-minute evidence is gone
    assert pc._score(ip, time.time(), pc.cfg("window_s")) == (0, 0)
    verdict, why = pc.decide(ip, "/probe-0/.env")
    assert verdict == "BLOCK"
    assert str(want) in why and "probe paths" in why   # the decision states its own arithmetic

    rec = [e for e in _events(pc) if e.get("evt") == "perseus_shield_block"]
    assert rec and rec[-1]["rule"] == "slow_scan" and rec[-1]["distinct"] >= want


def test_ua_rotation_alone_never_convicts(pc):
    """Twelve user agents from one address, asking only for legitimate paths, is CI or an uptime
    check. The repository's own deploy verifier is exactly that shape and was blocked by the first
    version of this rule. Rotation is evidence of AUTOMATION, not of ATTACK.
    """
    ip = "203.0.113.10"
    agents = ["Mozilla/5.0 (Windows NT 10.0) Chrome/120", "Mozilla/5.0 (Macintosh) Safari/17",
              "Mozilla/5.0 (X11; Linux x86_64) Firefox/121", "Mozilla/5.0 (Android 14) Chrome/120",
              "Mozilla/5.0 (iPhone) Safari/17", "Mozilla/5.0 (Windows NT 10.0) Edg/120",
              "curl/8.5.0", "python-requests/2.31", "Go-http-client/2.0", "Wget/1.21"]
    for a in agents:
        reasons = pc.watch(ip, "/", 200, a, "GET")
    # THE FIXTURE IS PROVED: the rotation really was detected, so what follows is the SCORING
    # declining to convict on it, not the detector failing to see it.
    assert "ua_rotation" in reasons
    assert len(pc._fps[ip]) >= pc.cfg("ua_rotation_n")
    assert pc._score(ip, time.time(), pc.cfg("window_s"))[0] == 0
    assert pc.decide(ip, "/")[0] == "ALLOW"


# =============================================================================================
# 3. THE EXEMPTIONS THAT STOP US LOCKING A HUMAN OUT.
# =============================================================================================

def test_an_authenticated_session_is_never_blocked_and_never_tarpitted(pc):
    """Both verdicts, on identical evidence, so neither result can come from a difference in state.

    THE FIXTURE IS PROVED TWICE: the anonymous twin of each address must actually reach TARPIT and
    BLOCK first. A test where the evidence never accumulated would report "not tarpitted" for an
    address nothing was ever going to tarpit.
    """
    # --- tarpit-level evidence: two probe paths = 6, over tarpit_after (5), under block_after (12)
    anon_t, auth_t = "198.51.100.1", "198.51.100.2"
    _feed(pc, anon_t, PROBES[:2])
    _feed(pc, auth_t, PROBES[:2])
    assert pc.decide(anon_t, "/")[0] == "TARPIT", "the fixture did not reach tarpit level"
    assert pc.decide(auth_t, "/", authed=True)[0] == "ALLOW"

    # --- block-level evidence: four probe paths = 12
    anon_b, auth_b = "198.51.100.3", "198.51.100.4"
    _feed(pc, anon_b, PROBES)
    _feed(pc, auth_b, PROBES)
    # ASK ON A PATH WE DO NOT SERVE. Two things had to be read out of client.py to get this right,
    # and I guessed at both before reading them:
    #   1. `/` is A ROUTE WE SERVE, and a served route is SLOWED, never blocked - so a fully
    #      convicted address asking for `/` correctly returns TARPIT. The first version of this
    #      line read that correct behaviour as a broken fixture.
    #   2. `_blocked[ip]` is set inside `_decide_raw`, which only runs from decide(). `_feed()`
    #      calls watch(), which records evidence and takes no decision - so asking is_blocked()
    #      without ever calling decide() on a non-exempt path reports False on a fixture that was
    #      one call away from converting.
    assert pc.decide(anon_b, PROBES[0])[0] == "BLOCK", "the fixture did not reach block level"
    assert pc.is_blocked(anon_b) is True, "the block must be RECORDED, not merely returned"
    verdict, why = pc.decide(auth_b, "/", authed=True)
    assert verdict == "ALLOW"
    assert why, "an exemption that says nothing is how the operator lost an hour to a silent 404"

    # THE FINDING IS NOT ERASED. The address stays held for what it did; only the response to the
    # authenticated request is softened. An exemption that forgets is a hiding place.
    assert pc.is_blocked(auth_b) is True
    told = [e for e in _events(pc) if e.get("evt") == "perseus_shield_exempt"]
    assert told and any(e.get("reason") == "authenticated session" for e in told)


def test_authentication_is_PROVEN_by_the_application_not_claimed_by_a_header(pc):
    """A scanner spraying Authorization headers collects 401s and never earns the exemption; a
    credential the app answered 2xx to does. Both directions, on the module's own state."""
    sprayer, member = "198.51.100.5", "198.51.100.6"
    pc.watch(sprayer, "/admin", 401, UA, "GET", True)
    pc.watch(sprayer, "/admin", 403, UA, "GET", True)
    assert sprayer not in pc._authed

    pc.watch(member, "/dashboard", 200, UA, "GET", True)
    assert member in pc._authed


def test_an_unproven_credential_is_slowed_but_never_refused(pc):
    """The way back for a REAL user whose address was blocked while they were away: the cookie is
    not proof, so it does not fully exempt, but a block would be a permanent lockout for the one
    person we most need not to lock out."""
    ip = "198.51.100.7"
    _feed(pc, ip, PROBES)
    assert pc.decide(ip, "/dashboard")[0] == "BLOCK"          # fixture proved
    assert pc.decide(ip, "/dashboard", credential=True)[0] == "TARPIT"


def test_a_route_we_serve_is_slowed_never_blocked(pc):
    """`is_our_route`'s contract has always said 'never blocked'. Refusing a real page is what locks
    a person out of the product; the tarpit answers the throughput half."""
    ip = "198.51.100.8"
    pc.watch("192.0.2.50", "/pricing", 200, UA, "GET")        # the app serves it: learned
    assert pc.local_is_ours("/pricing") is True
    _feed(pc, ip, PROBES)
    assert pc.decide(ip, "/pricing")[0] == "TARPIT"
    # ... and the block it earned is still in force everywhere else. Same call, same address.
    assert pc.decide(ip, "/not-a-page-we-have")[0] == "BLOCK"


def test_a_served_route_is_never_scored_even_on_its_first_request(pc):
    """A path that would otherwise look hostile but which THIS app answers 200 to.

    /admin matches the console rule, and plenty of projects serve exactly that. The status is known
    by the time watch() runs, so the route is learned before the shape is scored -- there is no
    first-request window in which a real page counts against its visitors.
    """
    ip = "198.51.100.9"
    assert pc.probe_shape("/admin", is_ours=pc.local_is_ours) is True     # fixture proved
    assert pc.watch(ip, "/admin", 200, UA, "GET") == []
    assert pc.local_is_ours("/admin") is True
    assert pc.probe_shape("/admin", is_ours=pc.local_is_ours) is False


def test_api_and_well_known_are_never_blocked_but_are_always_observed(pc):
    """The /api/ prefix became a hiding place three times: exemption from ACTION kept turning into
    exemption from OBSERVATION. Both halves are asserted here, in the same test, deliberately."""
    ip = "198.51.100.10"
    _feed(pc, ip, PROBES)
    assert pc.decide(ip, "/api/me")[0] == "ALLOW"
    assert pc.decide(ip, "/.well-known/acme-challenge/x")[0] == "ALLOW"
    # OBSERVED all the same: the shape is scored even where we will never act on it.
    assert pc.probe_shape("/api/wp-login.php", is_ours=pc.local_is_ours) is True
    assert pc.probe_shape("/api/../../.env", is_ours=pc.local_is_ours) is True
    # ... and the same evidence blocks anywhere else, so the exemption is the prefix, not the state.
    assert pc.decide(ip, "/vendor/phpunit/eval-stdin.php")[0] == "BLOCK"


def test_an_app_with_a_catch_all_disarms_itself_and_says_so(pc):
    """An SPA that answers 200 to everything makes 'a route we serve' meaningless, so enforcement
    turns itself off rather than risk refusing a real page. Fail-open, and STATED."""
    ip = "198.51.100.11"
    _feed(pc, ip, PROBES)
    assert pc.decide(ip, "/whatever")[0] == "BLOCK"           # fixture proved: it CAN enforce
    pc._blocked.clear()
    for p in ("/.env", "/wp-config.php", "/server-status"):
        pc.watch("192.0.2.60", p, 200, UA, "GET")             # the app serves every one of them
    assert pc._catchall[0] is True
    assert pc.decide(ip, "/whatever")[0] == "ALLOW"
    assert any(e.get("evt") == "perseus_shield_catchall" for e in _events(pc))
    assert pc.shield_state()["catchall"] is True              # and it is readable, not inferred


# =============================================================================================
# 4. BOUNDED, EXPIRING, REVERSIBLE -- because no human is in this loop.
# =============================================================================================

def test_a_block_expires_by_itself(pc):
    ip = "192.0.2.11"
    _feed(pc, ip, PROBES)
    assert pc.decide(ip, "/x.php")[0] == "BLOCK"
    held = pc.shield_state()["blocked"][ip]
    assert 0 < held <= pc.cfg("block_s") <= pc.BOUNDS["block_s"][1]


def test_release_forgives_the_history_not_just_the_timer(pc):
    """A hand brake that lifts the timer and leaves the evidence re-blocks on the next request.
    Its own regression test is what caught that, and this is that test, ported."""
    ip = "192.0.2.12"
    _feed(pc, ip, PROBES)
    assert pc.decide(ip, "/x.php")[0] == "BLOCK"
    assert pc.unblock(ip) is True
    assert pc.is_blocked(ip) is False
    assert pc.decide(ip, "/x.php")[0] == "ALLOW", "the release did not forgive the history"
    assert any(e.get("evt") == "perseus_shield_unblock" for e in _events(pc))


def test_the_blast_cap_refuses_to_hold_more_than_its_ceiling(pc, monkeypatch):
    """An automatic control that can block everybody is worse than no control. Narrow, never wipe."""
    monkeypatch.setattr(pc, "MAX_BLOCKS", 2)
    verdicts = []
    for i in range(3):
        ip = "192.0.2.%d" % (20 + i)
        _feed(pc, ip, PROBES)
        verdicts.append(pc.decide(ip, "/x.php")[0])
    assert verdicts[:2] == ["BLOCK", "BLOCK"], "the fixture never reached the ceiling"
    assert verdicts[2] == "TARPIT", "past the ceiling the shield must slow, not block"
    assert len(pc._blocked) == 2
    assert any(e.get("evt") == "perseus_shield_refused" for e in _events(pc))


def test_the_tarpit_has_a_concurrency_ceiling(pc):
    """Every stalled request holds a connection, so an uncapped tarpit is a self-inflicted denial
    of service: past the cap we answer immediately instead."""
    assert pc.tarpit_seconds() > 0                            # fixture proved
    for _ in range(pc.MAX_TARPIT_CONCURRENT):
        pc.enter_tarpit()
    assert pc.tarpit_seconds() == 0.0
    pc.leave_tarpit()
    assert pc.tarpit_seconds() > 0


def test_every_threshold_is_clamped_on_read_whatever_the_hub_publishes(pc):
    """Clamping on READ, not on write: a hand-edited, corrupt or future-version blocklist still
    cannot push the shield outside the range this file commits to. Three cases, because a test that
    only checks the clamp cannot tell a clamp from a constant."""
    lo, hi = pc.BOUNDS["block_s"]
    pc._CACHE["thresholds"] = {"block_minutes": 15}
    assert pc.cfg("block_s") == 900                # honoured: the hub's number is really read
    pc._CACHE["thresholds"] = {"block_minutes": 100000}
    assert pc.cfg("block_s") == hi                 # clamped high
    pc._CACHE["thresholds"] = {"block_minutes": 1}
    assert pc.cfg("block_s") == lo                 # clamped low

    slo, shi = pc.SLOW_DISTINCT_BOUNDS
    pc._CACHE["thresholds"] = {"slow_distinct": 9999}
    assert pc.slow_distinct() == shi
    pc._CACHE["thresholds"] = {"slow_distinct": 0}
    assert pc.slow_distinct() == slo


def test_the_long_window_evidence_per_address_is_bounded(pc, monkeypatch):
    """Enough to prove a scan, far short of keeping the attacker's own log for them.

    Asserted as EQUALITY, not `<=`: an address that recorded nothing at all would satisfy `<= 4`
    and prove only that the test ran.
    """
    monkeypatch.setattr(pc, "SLOW_MAX_PATHS", 4)
    ip = "198.18.0.1"
    for i in range(40):
        pc.watch(ip, "/probe-%d/.env" % i, 404, UA, "GET")
    assert len(pc._slow[ip]) == 4


def test_the_number_of_addresses_scored_is_bounded(pc, monkeypatch):
    """Past the ceiling a new address is simply not recorded, rather than growing memory without
    limit on input the attacker chooses. Equality again, and the ceiling is proved reachable."""
    monkeypatch.setattr(pc, "MAX_WATCHED", 5)
    for i in range(50):
        pc.watch("192.0.2.%d" % i, "/", 200, UA, "GET")
    assert len(pc._seen_ips) == 5


# =============================================================================================
# 5. IT FAILS OPEN, ALWAYS.
# =============================================================================================

def test_an_exception_anywhere_in_the_decision_path_allows_the_request(pc, monkeypatch):
    """A security control that breaks the site is a worse outage than the scanning it prevents.

    THE FIXTURE IS PROVED: the identical evidence on a twin address blocks, so the ALLOW below is
    the fail-open path and not an address that was never going to be refused.
    """
    proof, victim = "192.0.2.31", "192.0.2.32"
    _feed(pc, proof, PROBES)
    _feed(pc, victim, PROBES)
    assert pc.decide(proof, "/x.php")[0] == "BLOCK"

    def boom(*_a, **_k):
        raise RuntimeError("the scorer exploded")

    monkeypatch.setattr(pc, "_score", boom)
    assert pc.decide(victim, "/x.php") == ("ALLOW", "")


def test_an_exception_in_observation_never_reaches_the_request(pc, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("the detector exploded")

    monkeypatch.setattr(pc, "probe_shape", boom)
    assert pc.watch("192.0.2.33", "/.env", 404, UA, "GET") == []


def test_a_broken_event_log_costs_a_line_not_a_request(pc, monkeypatch):
    """An observability write that swallows its own failure is a self-inflicted blind spot, so the
    first failure prints -- but it must never propagate into the decision."""
    monkeypatch.setattr(pc, "EVENTS", os.path.join(str(pc.BEAT_DIR), "nope", "deeper", "e.log"))
    ip = "192.0.2.34"
    _feed(pc, ip, PROBES)
    assert pc.decide(ip, "/x.php")[0] == "BLOCK"
    assert pc._CACHE["warned"] is True


# =============================================================================================
# 6. IT CANNOT REACH THE FIREWALL, THE NETWORK, OR A CREDENTIAL.
# =============================================================================================

def _imported_modules(src):
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _attribute_calls(src):
    """{'os.system', 'socket.socket', ...} for every dotted call in the file."""
    out = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                out.add("%s.%s" % (node.func.value.id, node.func.attr))
    return out


def test_the_client_imports_nothing_that_could_reach_a_firewall_or_the_network():
    """THE PROPERTY, not a grep for the word 'iptables'. Amnezia VPN shares this host: enforcement
    is HTTP-layer inside our own process or it does not happen (StGB §202a-§303b, EU 2013/40,
    CFAA §1030). A module that cannot import subprocess or socket cannot shell out to nft, and
    cannot connect back to anything either."""
    allowed = {"asyncio", "json", "os", "re", "threading", "time", "hashlib"}
    got = _imported_modules(_read(SOURCE))
    assert got <= allowed, "perseus/client.py imported something outside the stdlib floor: %s" % (
        sorted(got - allowed),)
    forbidden = {"os.system", "os.popen", "os.execv", "os.execvp", "os.spawnv", "os.fork"}
    assert not (_attribute_calls(_read(SOURCE)) & forbidden)


def test_the_client_holds_no_credential_and_cannot_page_anybody():
    """Alerting stays in colt-web. A bot token in five repositories is the 'one value, several
    homes' defect this estate has already paid for -- so the client reports and colt-web decides."""
    consts = {c.value for c in ast.walk(ast.parse(_read(SOURCE)))
              if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    for needle in ("api.telegram.org", "sendMessage", "smtp", "Bearer "):
        assert not any(needle.lower() in s.lower() for s in consts), (
            "%s appears as a literal in the thin client" % needle)
    assert "notify" not in _imported_modules(_read(SOURCE))


def test_the_client_uses_no_posix_only_api():
    """The suite runs on the operator's WINDOWS box. os.uname, os.getuid, fcntl and /proc are how a
    module passes in a Linux sandbox and fails on the machine that runs the tests."""
    src = _read(SOURCE)
    assert not (_imported_modules(src) & {"fcntl", "pwd", "grp", "termios", "resource"})
    assert not (_attribute_calls(src) & {"os.uname", "os.getuid", "os.getgid", "os.geteuid",
                                         "os.getpgid", "os.fchmod"})
    consts = [c.value for c in ast.walk(ast.parse(src))
              if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    assert not [s for s in consts if s.startswith("/proc/")]


def test_the_client_imports_cleanly_from_a_bare_interpreter(tmp_path):
    """A file copied into five projects must import with nothing installed and nothing configured.

    Loaded from a COPY on disk under its own name, which is also the exact shape of the projects
    that receive it -- and copied in BINARY, because a fixture that will be executed must not be
    rewritten by the platform's line-ending rules.
    """
    dst = tmp_path / "lonely" / "perseus_client.py"
    dst.parent.mkdir(parents=True)
    dst.write_bytes(pathlib.Path(SOURCE).read_bytes())
    spec = importlib.util.spec_from_file_location("perseus_client_isolated", str(dst))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.check) and callable(mod.decide) and callable(mod.observe)
    assert mod.PROBE_RE.search("/wp-login.php")


# =============================================================================================
# 7. TWO SHIELDS ON ONE REQUEST PATH IS A BUG, AND THE CLIENT DETECTS THAT ITSELF.
# =============================================================================================

def _load_copy(tmp_path, name, with_shield):
    d = tmp_path / name
    d.mkdir()
    (d / "perseus_client.py").write_bytes(pathlib.Path(SOURCE).read_bytes())
    if with_shield:
        (d / "shield.py").write_bytes(b"# a full shield lives here\n")
    spec = importlib.util.spec_from_file_location("pc_" + name, str(d / "perseus_client.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_local_enforcement_defaults_off_beside_a_full_shield_and_on_everywhere_else(
        tmp_path, monkeypatch):
    """cybergod.ai has shield.py with an operator console, a persistent evidence store and a
    Telegram escalation. Two independent blockers would reach two verdicts on one address and only
    one of them could be released. The four projects that have no shield.py get this one, armed.

    BOTH DIRECTIONS, from the REAL file, loaded twice from two directories that differ in exactly
    one thing.
    """
    monkeypatch.delenv("PERSEUS_LOCAL", raising=False)
    assert _load_copy(tmp_path, "alone", False).LOCAL is True
    assert _load_copy(tmp_path, "beside_shield", True).LOCAL is False


def test_the_operator_can_override_the_default_in_either_direction(tmp_path, monkeypatch):
    monkeypatch.setenv("PERSEUS_LOCAL", "1")
    assert _load_copy(tmp_path, "forced_on", True).LOCAL is True
    monkeypatch.setenv("PERSEUS_LOCAL", "0")
    assert _load_copy(tmp_path, "forced_off", False).LOCAL is False


def test_the_real_distributed_copies_land_on_the_right_side_of_that_rule():
    """WIRING, measured against the actual repository rather than against the rule's own logic:
    colt-web has a shield.py beside its copy and jobhuntwow does not, so one defers and one arms."""
    beside_shield = os.path.join(ROOT, "webapp", "backend", "app")
    no_shield = os.path.join(ROOT, "jobhuntwow-app", "backend", "app")
    assert os.path.exists(os.path.join(beside_shield, "perseus_client.py"))
    assert os.path.exists(os.path.join(beside_shield, "shield.py"))
    assert os.path.exists(os.path.join(no_shield, "perseus_client.py"))
    assert not os.path.exists(os.path.join(no_shield, "shield.py"))


# =============================================================================================
# 8. EVERY DECISION IS VISIBLE. A control nobody can see is not a control.
# =============================================================================================

def test_a_block_is_written_to_stdout_AND_to_the_shared_event_log(pc, capsys):
    """Two destinations, deliberately. Loki scrapes the container's stdout, and colt-web's brain
    reads the shared events file; a project whose volume write is broken must still be observable.
    """
    ip = "192.0.2.41"
    _feed(pc, ip, PROBES)
    before = [e for e in _events(pc) if e.get("evt", "").startswith("perseus_shield_")]
    assert not before, "the fixture had already emitted a decision; this proves nothing"

    assert pc.decide(ip, "/x.php")[0] == "BLOCK"

    out = capsys.readouterr().out
    on_stdout = [json.loads(l) for l in out.splitlines()
                 if l.startswith("{") and '"perseus_shield_block"' in l]
    in_log = [e for e in _events(pc) if e.get("evt") == "perseus_shield_block"]
    assert on_stdout, "the decision never reached stdout, so Loki would never see it"
    assert in_log, "the decision never reached the shared event log"
    for rec in (on_stdout[-1], in_log[-1]):
        assert rec["ip"] == ip and rec["service"] == pc.SERVICE
        assert rec["seconds"] == pc.cfg("block_s")
        assert rec["rule"] == "fast" and rec["score"] >= pc.cfg("block_after")
        assert rec["paths"], "a decision that does not name its evidence teaches nothing"


def test_a_steady_state_is_never_re_emitted(pc):
    """An alert that fires on every request is how the one that matters gets read past. The exempt
    line in particular would fire on every request a logged-in person makes."""
    ip = "192.0.2.42"
    _feed(pc, ip, PROBES)
    for _ in range(25):
        pc.decide(ip, "/dashboard", credential=True)
    lines = [e for e in _events(pc) if e.get("evt") == "perseus_shield_credential"]
    assert len(lines) == 1


def test_the_heartbeat_reports_whether_the_local_shield_can_actually_act(pc):
    """A feature nobody has seen working is off. The Fleet page could show a connected sidecar and
    say nothing about whether it is armed, which is the state four projects were already in."""
    pc._CACHE["beat"] = 0.0
    pc._beat(7)
    beat = json.loads(_read(os.path.join(str(pc.BEAT_DIR), "%s.json" % pc.SERVICE)))
    assert beat["evt"] == "perseus_beat" and beat["cycle"] == 7
    for key in ("local", "enforcing", "catchall", "blocked", "watching"):
        assert key in beat, "the heartbeat cannot report on a shield it does not mention: %s" % key


def test_status_exposes_the_shield_including_what_it_cannot_do(pc):
    """The in-memory store is a real limitation against colt-web's slow_store.py, and it is NAMED.
    A number that cannot fall, or a gap that is never stated, is how a fortnight of zero blocks got
    read as a quiet fortnight."""
    st = pc.status()["shield"]
    assert st["persistent"] is False
    assert st["local"] is True and st["enforcing"] is True
    assert st["config"]["block_after"] == pc.cfg("block_after")
    assert st["bounds"]["block_after"] == list(pc.BOUNDS["block_after"])
