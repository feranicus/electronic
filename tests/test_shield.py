"""test_shield.py — the active-defence guardrails, replayed against the REAL 10 Aug 2026 incident.

Every assertion here is a property the shield must keep no matter how the thresholds are tuned.
The four safety rails matter more than the detection: a security control that can break the site,
lock out every visitor, or reach the firewall on a host shared with Amnezia VPN is a worse outage
than the scanning it prevents.
"""
import importlib
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(ROOT, "webapp", "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


def _import_app():
    """Import webapp/backend/app, even when the whole suite has already resolved `app` elsewhere.

    Running tests/test_shield.py alone works; running `pytest tests/` did not, with
    `cannot import name 'shield' from 'app' (unknown location)` -- the tell for a NAMESPACE package.
    conftest.py puts the repo root and the engine scripts on sys.path first, and something in that
    order binds a bare `app` with no __init__. Rather than depend on import order across a shared
    suite, bind the package explicitly and drop whatever was there.
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


_import_app()

# THE ACTUAL REQUESTS, from the operator's Telegram alerts at 19:05:55-57 UTC on 10 Aug 2026.
# One IP in Andorra, six browsers, two seconds.
INCIDENT_IP = "195.178.110.199"
INCIDENT = [
    ("/",             {"browser": "Safari",  "os": "macOS",      "device": "desktop"}),
    ("//slug",        {"browser": "Chrome",  "os": "Linux",      "device": "desktop"}),
    ("/",             {"browser": "Chrome",  "os": "macOS",      "device": "desktop"}),
    ("/",             {"browser": "Edge",    "os": "Windows 10", "device": "desktop"}),
    ("/DOCS.md",      {"browser": "Firefox", "os": "Windows 10", "device": "desktop"}),
    ("/IAM.md",       {"browser": "Firefox", "os": "macOS",      "device": "desktop"}),
    ("/[workspace]/", {"browser": "Chrome",  "os": "Windows 10", "device": "desktop"}),
]


@pytest.fixture
def sh():
    """A fresh shield per test — the state is module-level, so it must not leak between cases."""
    _import_app()
    from app import shield
    importlib.reload(shield)
    shield._hits.clear(); shield._fps.clear()
    shield._blocked.clear(); shield._seen_ips.clear(); shield._tarpits[0] = 0
    return shield


# ------------------------------------------------------------------ detection
def test_the_real_incident_paths_are_recognised(sh):
    """//slug, /[workspace]/, /DOCS.md and /IAM.md all read as human page views on the day."""
    for p in ("//slug", "/[workspace]/", "/DOCS.md", "/IAM.md"):
        assert sh.is_probe_path(p), "%s is scanner behaviour, not a page a person types" % p
    for p in ("/.git/config", "/wp-login.php", "/.env", "/backup.zip"):
        assert sh.is_probe_path(p)


def test_real_pages_are_never_probes(sh):
    """A false positive here costs a customer their visit. These are the site's actual routes."""
    for p in ("/", "/partners", "/demo", "/contact", "/privacy", "/impressum", "/experience",
              "/login", "/app", "/app/compliance", "/api/me", "/sitemap.xml",
              "/.well-known/security.txt", "/media/cassandra.mp4", "/assets/index-a1b2c3.js"):
        assert not sh.is_probe_path(p), "%s is a real route and must never be treated as a probe" % p


def test_ua_rotation_alone_identifies_the_scanner(sh):
    """The evasion IS the evidence, and it fires before any 404 threshold is reached.

    Every path in this loop returns 200 and three of them are the legitimate home page, so nothing
    but the rotating fingerprint can convict here. A real visitor has one browser.
    """
    seen = []
    for path, cls in INCIDENT:
        seen = sh.observe(INCIDENT_IP, path, 200, cls)
    assert "ua_rotation" in seen, "six browsers from one address in two seconds is not a person"


def test_one_honest_visitor_is_never_touched(sh):
    """Twenty page views from one real browser must stay ALLOW. This is the false-positive test."""
    cls = {"browser": "Firefox", "os": "Windows 10", "device": "desktop"}
    for _ in range(20):
        for p in ("/", "/partners", "/demo", "/contact"):
            sh.observe("203.0.113.7", p, 200, cls)
    assert sh.decide("203.0.113.7", "/")[0] == "ALLOW"


def test_a_mistyped_url_is_not_an_attack(sh):
    """A few 404s from one browser is a stale bookmark, not a scan."""
    cls = {"browser": "Safari", "os": "iOS", "device": "mobile"}
    for _ in range(3):
        sh.observe("203.0.113.9", "/oldpage", 404, cls)
    assert sh.decide("203.0.113.9", "/")[0] == "ALLOW"


def test_a_honeytoken_is_proof(sh):
    """Linked from nowhere, Disallowed in robots.txt: fetching one cannot be an accident."""
    cls = {"browser": "Chrome", "os": "Linux", "device": "desktop"}
    for _ in range(3):
        sh.observe("203.0.113.11", "/wp-login.php", 404, cls)
    assert sh.decide("203.0.113.11", "/")[0] in ("TARPIT", "BLOCK")


def test_the_incident_escalates_to_a_block(sh):
    """Replayed end to end, the real scanner is stopped rather than merely reported."""
    for _ in range(3):
        for path, cls in INCIDENT:
            sh.observe(INCIDENT_IP, path, 404 if path != "/" else 200, cls)
    assert sh.decide(INCIDENT_IP, "/")[0] == "BLOCK"


# ------------------------------------------------------------------ the four safety rails
def test_never_blocks_acme_or_security_txt(sh):
    """Blocking /.well-known turns a scanner into a CERTIFICATE OUTAGE for every visitor."""
    for _ in range(50):
        sh.observe(INCIDENT_IP, "/.git/config", 404, {"browser": "x", "os": "y", "device": "z"})
    assert sh.decide(INCIDENT_IP, "/.well-known/acme-challenge/tok")[0] == "ALLOW"
    assert sh.decide(INCIDENT_IP, "/.well-known/security.txt")[0] == "ALLOW"


def test_the_blast_cap_refuses_a_mass_block(sh):
    """An automatic control that can block everybody is worse than no control.

    Same doctrine as the co-tenant guard's valve and the FP auditor's: narrow, never wipe.
    """
    cls = {"browser": "Chrome", "os": "Linux", "device": "desktop"}
    for i in range(10):
        ip = "198.51.100.%d" % i
        for _ in range(20):
            sh.observe(ip, "/.env", 404, cls)
    verdicts = [sh.decide("198.51.100.%d" % i, "/")[0] for i in range(10)]
    assert "TARPIT" in verdicts, "the cap must stop the shield blocking the whole internet"
    # The property is "it cannot block everybody", NOT "it blocks at most N%". A percentage of a
    # handful is not a rate — see shield.blast_ok(). A small absolute number is always allowed,
    # and past that the percentage governs; here that means some are blocked and some are not.
    assert 0 < len(sh._blocked) < 10, "some are stopped, and the guard still holds the line"


def test_blocks_expire_and_can_be_released_by_hand(sh):
    """Nothing here is permanent, and every automatic control needs a hand brake."""
    for _ in range(3):
        for path, cls in INCIDENT:
            sh.observe(INCIDENT_IP, path, 404, cls)
    assert sh.decide(INCIDENT_IP, "/")[0] == "BLOCK"
    assert sh.unblock(INCIDENT_IP) is True
    assert sh.decide(INCIDENT_IP, "/")[0] != "BLOCK"
    # An expired timer is not a block. Re-earn it first, then expire it, and prove the expiry
    # alone is enough for the address to be served again.
    for _ in range(3):
        for path, cls in INCIDENT:
            sh.observe(INCIDENT_IP, path, 404, cls)
    assert sh.decide(INCIDENT_IP, "/")[0] == "BLOCK"
    sh._blocked[INCIDENT_IP] = time.time() - 1
    sh._hits.pop(INCIDENT_IP, None)                         # the window has rolled past as well
    assert sh.decide(INCIDENT_IP, "/")[0] != "BLOCK", "nothing here may be permanent"


def test_it_fails_open(sh):
    """Any internal error must let the request through. Never the other way around."""
    sh._blocked = None                                     # sabotage the state entirely
    assert sh.decide(INCIDENT_IP, "/")[0] == "ALLOW"
    assert sh.observe(INCIDENT_IP, "/", 200, {}) == []


def test_the_kill_switch_and_the_allowlist(sh):
    # THE HISTORY IS INJECTED DIRECTLY, NOT VIA observe(). Both observe() and decide() honour the
    # allowlist, so driving this through observe() proves nothing about decide(): removing decide's
    # guard entirely still passed, because observe() had already refused to record anything. When
    # two guards sit on one path, a negative test must defeat BOTH or it is measuring the other one.
    now = time.time()
    hostile = [(now, "honeytoken")] * 30

    os.environ["SHIELD_ALLOW_IPS"] = INCIDENT_IP
    importlib.reload(sh)
    sh._hits[INCIDENT_IP] = list(hostile)
    sh._seen_ips[INCIDENT_IP] = now
    assert sh.decide(INCIDENT_IP, "/")[0] == "ALLOW", "an allowlisted address is never blocked"
    del os.environ["SHIELD_ALLOW_IPS"]

    os.environ["SHIELD"] = "off"
    importlib.reload(sh)
    sh._hits["1.2.3.4"] = list(hostile)
    sh._seen_ips["1.2.3.4"] = now
    assert sh.decide("1.2.3.4", "/")[0] == "ALLOW", "the kill switch stops enforcement dead"
    del os.environ["SHIELD"]
    importlib.reload(sh)


def test_the_tarpit_cannot_become_a_self_inflicted_dos(sh):
    """Every stalled request holds a connection. Past the cap we answer immediately instead."""
    assert sh.tarpit_seconds() > 0
    sh._tarpits[0] = sh.MAX_TARPIT_CONCURRENT
    assert sh.tarpit_seconds() == 0.0


def test_no_module_ever_touches_the_firewall(sh):
    """AMNEZIA VPN SHARES THIS HOST. Enforcement is HTTP-layer, inside colt-web, full stop.

    The standing rule was "detection only, because we do not touch the firewall". The firewall was
    always the objection -- not the blocking. A packet filter here would take down the VPN, SSH and
    four other sites; an HTTP 404 cannot.
    """
    import re
    bad = re.compile(r"\b(iptables|ip6tables|nft|ufw|firewall-cmd|route\s+add)\b")
    for name in ("shield.py", "shield_panel.py", "shield_tuning.py"):
        src = open(os.path.join(ROOT, "webapp", "backend", "app", name), encoding="utf-8").read()
        src = re.sub(r"#.*|\"\"\".*?\"\"\"", "", src, flags=re.S)   # prose may DISCUSS the rule
        assert not bad.search(src), "%s reaches for the firewall on a host shared with a VPN" % name


# ------------------------------------------------------------------ the panel's bounded powers
def test_a_model_can_never_leave_the_committed_bounds(sh):
    from app import shield_tuning
    shield_tuning.PATH = "/tmp/shield_tuning_test.json"
    shield_tuning.reset()
    applied, rejected = shield_tuning.propose(
        {"block_after": 100000, "window_s": 1, "blast_cap": 99, "nonsense": 5},
        "test", ["m"])
    assert applied == {}, "every one of those is outside the bounds or not a tunable key"
    assert any("outside the committed bounds" in r for r in rejected)
    assert any("not a tunable key" in r for r in rejected)


def test_a_model_cannot_swing_the_policy_in_one_step(sh):
    from app import shield_tuning
    shield_tuning.PATH = "/tmp/shield_tuning_test.json"
    shield_tuning.reset()
    cur = sh.cfg("block_after")
    applied, rejected = shield_tuning.propose({"block_after": cur * 3}, "test", ["m"])
    assert applied == {} and any("step" in r for r in rejected)
    small = max(sh.BOUNDS["block_after"][0], int(cur * 1.2))
    applied, _ = shield_tuning.propose({"block_after": small}, "test", ["m"])
    assert applied.get("block_after") == small, "a gradual, in-bounds change IS allowed"
    shield_tuning.reset()


def test_a_corrupt_tuning_file_falls_back_to_the_committed_defaults(sh):
    from app import shield_tuning
    shield_tuning.PATH = "/tmp/shield_tuning_corrupt.json"
    with open(shield_tuning.PATH, "w") as fh:
        fh.write("{not json at all")
    shield_tuning._cache["mtime"] = 0
    assert sh.cfg("block_after") == sh.DEFAULTS["block_after"]
    os.remove(shield_tuning.PATH)


def test_the_panel_needs_a_quorum_and_takes_the_median(sh):
    """One model shouting must not move policy; three agreeing must, and moderately."""
    from app import shield_panel
    cur = {"block_after": 12, "window_s": 300}

    lone = [{"propose": {"block_after": 20}}, {"propose": {}}, {"propose": {}}, {"propose": {}}]
    agreed, notes = shield_panel.consensus(lone, cur)
    assert agreed == {} and any("below the quorum" in n for n in notes)

    split = [{"propose": {"block_after": 20}}, {"propose": {"block_after": 18}},
             {"propose": {"block_after": 6}}, {"propose": {"block_after": 8}}]
    assert shield_panel.consensus(split, cur)[0] == {}, "a two-two split changes nothing"

    three = [{"propose": {"block_after": 30}}, {"propose": {"block_after": 15}},
             {"propose": {"block_after": 16}}, {"propose": {}}]
    agreed, _ = shield_panel.consensus(three, cur)
    assert agreed["block_after"] == 16, "the MEDIAN, so one bold model cannot drag the result"


def test_the_panel_is_the_same_four_models_as_every_other_gate(sh):
    """Four vendors, so a provider-wide 429 cannot silence the review."""
    from app import shield_panel
    quorum = open(os.path.join(ROOT, "deploy", "stagegate", "quorum.py"), encoding="utf-8").read()
    for m in shield_panel.MODELS:
        assert m in quorum, "%s is not one of the staging-gate panel models" % m
    assert len(shield_panel.MODELS) == 4


def test_the_panel_is_not_in_the_request_path(sh):
    """A model call is 300ms to 60s. In front of a request that IS a denial of service."""
    tele = open(os.path.join(ROOT, "webapp", "backend", "app", "telemetry.py"),
                encoding="utf-8").read()
    assert "shield_panel" not in tele, "the panel must never be reachable from the middleware"
    # STRIP THE PROSE FIRST. The docstring legitimately EXPLAINS why the panel is out of band and
    # names it; grepping raw source would fail on the very comment that documents the rule. The
    # brand gate learned this months ago and it has to be carried across every time.
    import re as _re
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "shield.py"), encoding="utf-8").read()
    src = _re.sub(r'"""(?:.|\n)*?"""|#.*', "", src)
    for forbidden in ("import enrich", "shield_panel", "urllib.request", "requests."):
        assert forbidden not in src, "shield.py must stay pure arithmetic: found %r" % forbidden
