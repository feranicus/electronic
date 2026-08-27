"""test_shield.py — the active-defence guardrails, replayed against the REAL 10 Aug 2026 incident.

Every assertion here is a property the shield must keep no matter how the thresholds are tuned.
The four safety rails matter more than the detection: a security control that can break the site,
lock out every visitor, or reach the firewall on a host shared with Amnezia VPN is a worse outage
than the scanning it prevents.
"""
import importlib
import os
import re
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    """Source of a repo file, for the checks that assert WIRING rather than behaviour."""
    with open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()
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


def test_the_deploy_verifier_is_never_blocked(sh):
    """THIS SHIPPED AND BROKE A DEPLOY. It is the most important test in this file.

    ship.py's bot-404 gate sends TWELVE different user agents from ONE address to prove the gate
    works, and asks only for `/` and `/api/me`. The shield read that as UA rotation, blocked the
    operator's own IP, and /api/me answered 404 to everybody from it:
        [X] /api/me returned 404 for GPTBot - expected 401
        RESULT: FAIL       https://cybergod.ai/api/me   HTTP 404
    Two fixes, and the second is a design correction rather than a threshold change:
      · /api/ joins /.well-known/ in NEVER_BLOCK_PREFIXES. visitors.py has exempted it since the
        day it was written; I did not carry the exemption across. Authentication protects /api/,
        and a 401 is already a refusal.
      · UA rotation now needs CORROBORATION. It proves AUTOMATION, not ATTACK. Monitoring, uptime
        checks and CI all rotate agents on legitimate paths.
    """
    UAS = ["Chrome", "iPhone", "Googlebot", "Bingbot", "GPTBot", "AhrefsBot",
           "Censys", "nuclei", "sqlmap", "curl", "python-requests", ""]
    for ua in UAS:                                   # exactly what check_bot_gate.py does
        for path in ("/", "/api/me"):
            sh.observe("203.0.113.42", path, 200 if path == "/" else 401,
                       {"browser": ua or "-", "os": "-", "device": "desktop"})
    assert sh.decide("203.0.113.42", "/api/me")[0] == "ALLOW", (
        "the deploy verifier must reach /api/me — every verifier in this repo asserts 401 there")
    assert sh.decide("203.0.113.42", "/")[0] == "ALLOW", (
        "rotating agents on legitimate paths is automation, not an attack")


def test_api_can_never_be_blocked_even_for_a_proven_scanner(sh):
    """Even a convicted attacker gets 401 on /api/, not 404. Auth is the control there."""
    for _ in range(5):
        for path, cls in INCIDENT:
            sh.observe(INCIDENT_IP, path, 404, cls)
    assert sh.decide(INCIDENT_IP, "/")[0] == "BLOCK"
    assert sh.decide(INCIDENT_IP, "/api/me")[0] == "ALLOW"
    assert sh.decide(INCIDENT_IP, "/.well-known/acme-challenge/x")[0] == "ALLOW"


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

# ------------------------------------------------------------------ the Telegram attack console
def test_the_menu_contains_no_offensive_action(sh):
    """There is no hack-back button, and there must never be one.

    Scanning or connecting back to the attacker is a criminal offence in every jurisdiction this
    platform operates in (DE StGB s.202a/303b, EU Directive 2013/40, US CFAA s.1030, Canada
    Criminal Code s.342.1). The address is also usually a compromised third party rather than the
    attacker. And one such packet would end the "not one packet is sent to the company being
    assessed" promise that /partners, the Terms of Use and the signed partner pack all rest on.
    """
    from app import shield_console as sc
    banned = ("scan", "nmap", "exploit", "attack", "hack", "retaliat", "counter", "probe_them",
              "portscan", "ddos", "flood")
    for key, a in sc.ACTIONS.items():
        blob = (key + " " + a["label"] + " " + a["what"]).lower()
        for b in banned:
            assert b not in blob, "action %r looks offensive (%r)" % (key, b)
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "shield_console.py"),
               encoding="utf-8").read()
    import re as _re
    code = _re.sub(r'"""(?:.|\n)*?"""|#.*', "", src)
    for b in ("socket.", "nmap", "urlopen(\"http://%s" % "", "masscan"):
        assert b not in code, "the console reaches out to the attacker: %r" % b


def test_every_escalation_is_time_boxed_or_reversible(sh):
    """Nothing an operator taps in a hurry may become permanent by accident."""
    from app import shield_console as sc
    assert set(sc.ACTIONS) == {"hold24", "net", "abuse", "strict", "deny", "release"}
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "shield_console.py"),
               encoding="utf-8").read()
    assert "86400" in src and "3600" in src, "the hold and the /24 must carry an explicit expiry"
    assert "ASK_TTL_S" in src, "an unanswered ask must expire rather than linger as authorisation"


def test_a_tap_is_recorded_by_the_bot_and_applied_by_the_app(sh):
    """Authorisation and enforcement live in different processes on purpose."""
    bot = open(os.path.join(ROOT, "assess-bot", "bot.py"), encoding="utf-8").read()
    # SCOPE THE CHECK TO THE HANDLER. The first version grepped the WHOLE file, and every other
    # handler already calls AUTH.is_authed — so deleting the check from shield_decide alone left
    # the string in place and the test passed on a file where anyone who learned the chat id could
    # change the site's defensive posture. Nth instance of a check aimed at the wrong subject.
    i = bot.index("async def shield_decide")
    j = bot.index("\ndef ", i) if "\ndef " in bot[i:] else len(bot)
    handler = bot[i:j]
    assert "shield_decisions.json" in handler, "the handler must record the choice"
    assert "AUTH.is_authed" in handler, (
        "the callback must be authenticated — a chat id alone cannot change defensive posture")
    for verb in ("_blocked[", "unblock(", "abuse_report"):
        assert verb not in handler, "the bot records the choice; it must not enforce it (%r)" % verb


def test_decisions_are_applied_and_are_operator_scoped(sh):
    """End to end over the real files: a tap becomes a state change, once."""
    import json as _json
    import tempfile as _tf
    from app import shield_console as sc
    d = _tf.mkdtemp()
    sc.PENDING = os.path.join(d, "pending.json")
    sc.DECISIONS = os.path.join(d, "decisions.json")
    with open(sc.PENDING, "w") as fh:
        _json.dump({"i1": {"ip": "203.0.113.55", "ts": time.time(), "path": "/x.php"}}, fh)
    with open(sc.DECISIONS, "w") as fh:
        _json.dump({"i1": {"action": "hold24", "by": "feranicus@s4biz.io"}}, fh)
    done = sc.apply_decisions(sh)
    assert any("24h" in x for x in done)
    assert sh._blocked.get("203.0.113.55", 0) > time.time() + 80000
    assert sc.apply_decisions(sh) == [], "a decision is consumed once, never replayed"


def test_a_wider_or_stricter_response_is_operator_only(sh):
    """The shield may never widen to a /24 or go strict on its own — a /24 can be a whole office."""
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "shield.py"), encoding="utf-8").read()
    body = src[src.index("def decide("):src.index("def tarpit_seconds(")]
    for name in ("BLOCK_NETS[", "STRICT_UNTIL[0] ="):
        assert name not in body, "decide() writes %s — that is operator-authorised state" % name
    assert "BLOCK_NETS.get" in body and "STRICT_UNTIL[0] >" in body, "but it must HONOUR them"

# =================================================================================================
# ARE THE GUARDRAILS ACTUALLY WIRED IN? Every test above proves shield.py BEHAVES correctly. None
# of them proves the middleware CALLS it, that the panel is scheduled, or that a decision reaches
# the app. A control that is correct and unreachable is not a control -- the same disease as the
# ruff gate that silently skipped and the check that could not see its subject.
# =================================================================================================
def test_the_shield_is_actually_in_the_request_path():
    tele = open(os.path.join(ROOT, "webapp", "backend", "app", "telemetry.py"),
                encoding="utf-8").read()
    i = tele.index("class _Telemetry")
    body = tele[i:]
    assert "shield" in body and "_sh.decide(" in body, "the middleware never asks the shield"
    assert "_sh.observe(" in body, "the middleware never feeds the shield what happened"
    # ANCHOR ON THE CALL, NOT THE PARAMETER NAME. `call_next` appears first in the method
    # SIGNATURE (`async def dispatch(self, request, call_next)`), so comparing against the bare
    # name compared decide() against position 80 and failed a correctly ordered file.
    assert body.index("_sh.decide(") < body.index("await call_next("), (
        "decide() must run BEFORE the app, or a blocked scanner still reaches application code")
    assert "except Exception" in body, "the shield call must be wrapped — it fails OPEN"


def test_the_panel_is_scheduled_and_decisions_are_applied():
    main = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    assert "shield_panel" in main, "the out-of-band review is never started"
    assert "shield_console.apply_decisions" in main, (
        "nothing applies what the operator taps on Telegram — the buttons would do nothing")
    assert "create_task" in main, "the review must be a background task, never in a request"


def test_the_measured_scanning_corpus_is_covered():
    """Written from what scanners ACTUALLY send, and re-measured here on every deploy.

    19 of these 48 were unrecognised when the corpus was first run against the shield. That is why
    analyse_attacks.py exists: it repeats this comparison against OUR OWN event log, so the next
    detector is written from evidence rather than from memory.
    """
    from app import shield as sh
    corpus = [
        "/wp-login.php", "/xmlrpc.php", "/.env", "/.git/config", "/.aws/credentials",
        "/.ssh/id_rsa", "/phpmyadmin/", "/adminer.php", "/admin/", "/manager/html", "/cpanel",
        "/actuator/env", "/swagger-ui.html", "/graphql", "/api-docs", "/v2/api-docs",
        "/cgi-bin/luci", "/boaform/admin/formLogin", "/goform/setSysTools", "/HNAP1/",
        "/solr/admin/info/system", "/jenkins/script", "/hudson", "/backup.zip", "/db.sql",
        "/config.old", "/web.config", "/.DS_Store", "/?XDEBUG_SESSION_START=phpstorm",
        "/server-status", "/../../../../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd",
        "/login.action", "/autodiscover/autodiscover.xml", "/telescope/requests",
        "/_ignition/execute-solution", "/DOCS.md", "/IAM.md", "//slug", "/[workspace]/",
        "/.npmrc", "/.dockercfg",
    ]
    missed = [p for p in corpus if not (sh.is_probe_path(p) or sh.is_honeytoken(p))]
    assert not missed, "the shield no longer recognises known mass-scanning paths: %s" % missed[:6]


def test_no_real_route_is_ever_treated_as_an_attack():
    """The other direction, and the one that costs a customer their visit."""
    from app import shield as sh
    for p in ("/", "/partners", "/demo", "/experience", "/contact", "/privacy", "/impressum",
              "/app", "/app/compliance", "/app/history", "/login", "/api/me", "/api/langs",
              "/sitemap.xml", "/robots.txt", "/.well-known/security.txt", "/media/cassandra.mp4",
              "/assets/index-abc123.js", "/manifest.webmanifest", "/sw.js", "/icon-192.png"):
        assert not sh.is_probe_path(p), "%s is a real route of ours" % p

# =================================================================================================
# WRITTEN FROM THE REAL LOG (analyse_attacks.py, 10 Aug 2026): 156,511 requests, 2,253 sources,
# 604 of them scanners. Three defects that only appeared once the actual traffic was measured.
# =================================================================================================
def test_api_is_not_a_hiding_place(sh):
    """The exemption that stops us blocking /api/ must not stop us SCORING what happens there.

    /api/ is never blocked — every deploy verifier asserts 401 on /api/me. The first version
    returned False from is_probe_path for anything beneath it, so /api/wp-login.php, /api/.env and
    /api/../../etc/passwd scored NOTHING: an attacker who prefixed every probe with /api/ was
    invisible. Shape is now always scored; the exemption only governs whether we may act.
    """
    for p in ("/api/wp-login.php", "/api/.env", "/api/../../etc/passwd", "/api/admin.php"):
        assert sh.probe_shape(p), "%s is scanner behaviour wherever it is sent" % p
        assert not sh.is_probe_path(p), "%s must still never be BLOCKED on" % p
    cls = {"browser": "Chrome", "os": "Linux", "device": "desktop"}
    for _ in range(6):
        for p in ("/api/wp-login.php", "/api/.env", "/api/admin.php"):
            sh.observe("198.51.100.77", p, 404, cls)
    assert sh.decide("198.51.100.77", "/")[0] == "BLOCK", (
        "a scanner hiding under /api/ must still be stopped everywhere else")
    assert sh.decide("198.51.100.77", "/api/me")[0] == "ALLOW", "but /api/ itself stays reachable"


def test_the_single_encoded_dot(sh):
    """185.177.72.56/.66/.67 each asked for /%2eenv five times. One %2e IS a dot."""
    assert sh.probe_shape("/%2eenv"), "/%2eenv is /.env wearing a costume"
    assert sh.probe_shape("/%2egit/config")


def test_a_real_visitor_with_many_404s_is_not_an_attacker(sh):
    """THE FALSE POSITIVE THE LOG EXPOSED, and it would have hit two real people.

    212.58.119.138 (Germany, 439x404) and 46.116.177.24 (Israel, 362x404) asked only for OUR OWN
    routes — /api/me, /, /app, /api/demo, /media/cassandra.mp4. They are visitors. On a 404 count
    alone both would have been blocked.
    VARIETY is the discriminator: a person misses the same few stale paths; a scanner misses
    hundreds of different ones.
    """
    cls = {"browser": "Chrome", "os": "Windows 10", "device": "desktop"}
    for _ in range(60):                       # sixty misses, on three stale paths
        for p in ("/old-link", "/favicon-32.png", "/app/gone"):
            sh.observe("212.58.119.138", p, 404, cls)
    assert sh.decide("212.58.119.138", "/")[0] == "ALLOW", (
        "a person with a stale bookmark is not an attacker, however often they reload")

    for i in range(12):                       # twelve DIFFERENT misses = enumeration
        sh.observe("198.51.100.99", "/scan-%d" % i, 404, cls)
    assert sh.decide("198.51.100.99", "/")[0] in ("TARPIT", "BLOCK"), (
        "many DISTINCT misses is enumeration and must still be caught")


def test_the_real_scanner_paths_from_the_log(sh):
    """Sampled from the sources analyse_attacks.py actually found on the box."""
    for p in ("/php8.php", "/wp-mail.php", "/alfa.php", "/lock360.php", "/ops.php", "/mini.php",
              "/wp-content/plugins/hellopress/wp_filemanager.php", "/this_is_a_new_hello_world.php",
              "/wp-json/batch/v1", "//wp-json/batch/v1", "/adminfuns.php", "/autoload_classmap.php"):
        assert sh.probe_shape(p), "%s was sent by a real scanner against this site" % p

def test_every_shield_event_is_visible_in_grafana():
    """An event nobody can see is not observability.

    The shield emitted six event types for a full day and NOT ONE appeared in any dashboard —
    `grep shield obs/grafana/dashboards/webapp.json` returned 0. The operator could be under
    attack, the shield could be stopping it, and Grafana would show nothing at all.
    Same disease as every other check in this repo that could not see its own subject.
    """
    import json as _json
    import re as _re
    dash = open(os.path.join(ROOT, "obs", "grafana", "dashboards", "webapp.json"),
                encoding="utf-8").read()
    _json.loads(dash)                                    # it must still be valid JSON

    src = open(os.path.join(ROOT, "webapp", "backend", "app", "shield.py"), encoding="utf-8").read()
    src += open(os.path.join(ROOT, "webapp", "backend", "app", "shield_console.py"),
                encoding="utf-8").read()
    src += open(os.path.join(ROOT, "webapp", "backend", "app", "shield_tuning.py"),
                encoding="utf-8").read()
    emitted = set(_re.findall(r'evt=["\'](shield_[a-z_]+)["\']', src))
    emitted |= set(_re.findall(r'_ev\(["\'](shield_[a-z_]+)["\']', src))
    assert emitted, "no shield events found in the source — read this test's premise again"

    # The raw-log panel uses a regex (evt=~`shield_.*`), which covers every one of them.
    covers_all = "shield_.*" in dash
    missing = [e for e in sorted(emitted) if e not in dash]
    assert covers_all or not missing, (
        "these shield events reach the log but no Grafana panel: %s" % missing)
    for must in ("shield_block", "shield_ask", "shield_refused", "shield_tuned"):
        assert must in dash, "%s deserves its own panel — it is a decision, not noise" % must



# --------------------------------------------------------------------------------------
# S7. THE OPERATOR MUST GET A CONFIRMATION, AND IT MUST BE TRUE
#
# The console shipped working: a real UNDER ATTACK alert with six buttons, tapped on a phone.
# What it did NOT have was proof that a tap reached the system. apply_decisions() ran only
# inside the SIX-HOURLY panel loop, so the bot said "Applying" and the confirmation could be a
# working day away. Silence after a tap is indistinguishable from failure, and a control the
# operator has learned not to trust is worse than no control.
# --------------------------------------------------------------------------------------

def test_decisions_apply_on_their_own_fast_loop():
    """The cheap action and the expensive deliberation must not share a clock."""
    s = _src("webapp/backend/app/main.py")
    assert "_decisions_loop" in s and "_panel_loop" in s, "the two loops were merged again"
    assert "_aio.create_task(_decisions_loop())" in s, "the decision loop is never started"
    # The apply loop must be seconds, not hours. Read the floor the code actually enforces.
    m = re.search(r'SHIELD_APPLY_EVERY_S["\']?,\s*(\d+)', s)
    assert m and int(m.group(1)) <= 60, "a tap must be applied within a minute, not a shift"
    # And apply_decisions must no longer be buried in the panel loop.
    panel = s[s.index("async def _panel_loop"):]
    assert "apply_decisions" not in panel, "applying is back inside the 6-hourly panel loop"


def test_confirmation_is_read_back_from_shield_state(sh):
    """A confirmation that would print identically whether or not anything happened is not a
    confirmation. Each line is re-read out of the shield AFTER the write."""
    import json as _json
    import tempfile as _tf
    from app import shield_console as sc
    d = _tf.mkdtemp()
    sc.PENDING, sc.DECISIONS = os.path.join(d, "p.json"), os.path.join(d, "d.json")
    _json.dump({"i1": {"ip": "203.0.113.9", "ts": time.time(), "path": "/x.php"}},
               open(sc.PENDING, "w"))
    _json.dump({"i1": {"action": "net", "by": "feranicus@s4biz.io"}}, open(sc.DECISIONS, "w"))
    done = sc.apply_decisions(sh)
    assert done and "203.0.113.0/24" in done[0]
    # The state it reported is the state the request path will actually consult.
    assert "203.0.113" in sh.BLOCK_NETS, "reported blocked, but decide() will never see it"


def test_a_failed_action_is_reported_not_swallowed(sh):
    """Silence must never be able to mean failure."""
    import json as _json
    import tempfile as _tf
    from app import shield_console as sc
    d = _tf.mkdtemp()
    sc.PENDING, sc.DECISIONS = os.path.join(d, "p.json"), os.path.join(d, "d.json")
    # A /24 of an IPv6 address is meaningless: the action cannot be carried out.
    _json.dump({"i1": {"ip": "2001:db8::1", "ts": time.time(), "path": ""}}, open(sc.PENDING, "w"))
    _json.dump({"i1": {"action": "net", "by": "x@y"}}, open(sc.DECISIONS, "w"))
    sent = []
    from app import notify
    notify.telegram = lambda t, **k: sent.append(t)
    sc.apply_decisions(sh)
    assert sent and "NOT APPLIED" in sent[0], "a failed action reported nothing to the operator"


def test_every_button_changes_something_the_request_path_reads(sh):
    """The console offers six actions. A button that writes a name decide() never consults is a
    lie told with a confirmation attached, which is the worst of both."""
    import ast as _ast
    t = _ast.parse(_src("webapp/backend/app/shield.py"))
    onpath = set()
    for f in [n for n in t.body if isinstance(n, _ast.FunctionDef)]:
        if f.name in ("decide", "observe", "probe_shape", "tarpit_seconds"):
            onpath |= {x.id for x in _ast.walk(f) if isinstance(x, _ast.Name)}
    for g in ("BLOCK_NETS", "STRICT_UNTIL", "EXTRA_PROBE_PATHS", "ALLOW_IPS", "_blocked"):
        assert g in onpath, "%s is written by a button but never read on the request path" % g


def test_the_bot_does_not_promise_what_it_cannot_verify():
    """The bot RECORDS, colt-web ENFORCES: separate processes, deliberately. So the bot cannot
    honestly say 'Applying'. Saying what silence means is what makes silence useful."""
    s = _src("assess-bot/bot.py")
    h = s[s.index("def shield_decide"):s.index("def shield_decide") + 3000]
    assert "Applying." not in h, "the bot claims an outcome it has no way to check"
    assert "colt-web is not running" in h, "silence after a tap is left ambiguous"


# ==============================================================================================
# THE 2026-08-22 DIGEST GAP. analyse_attacks.py had been printing these in its "NEW OR
# UNRECOGNISED" section for days while the blocker scored none of them, which is why the digest
# kept reporting a low block count against 33,430 attack-shaped requests. The corpus naming a
# class is worthless while probe_shape() cannot score it; these two must move together.
# ==============================================================================================

# Verbatim from the operator's own 14-day digest, 2026-08-21.
_DIGEST_GAP = [
    "/1.php7", "/about.php525", "/alfa-rex.php7", "/randkeyword.PhP7",   # php version suffixes
    "/@fs/etc/passwd", "/@fs/proc/self/environ",                          # Vite dev-server LFI
    "//firebase/init.json", "/service-account.json", "/Dockerfile",       # cloud creds + build
    "/1b7e06/", "/2ff83958/", "/3fa375/",                                 # root hex spray
]


# Added because a mutation run proved the committed test did NOT cover these: deleting the whole
# credential-and-debug extension rule changed nothing and the suite stayed green. _DIGEST_GAP only
# held `/service-account.json`, which the separate filename rule catches, so the extension rule was
# untested and therefore deletable. A rule with no test is a rule somebody removes by accident.
_CREDS_AND_DEBUG = [
    "/terraform.tfstate", "/prod.tfvars", "/kubeconfig", "/cert.pfx", "/store.p12",
    "/keystore.jks", "/elmah.axd", "/trace.axd", "/_profiler/latest", "/debugbar/open",
    "/.git-credentials", "/firebase.json", "/credentials.json", "/secrets.json",
]


def test_the_digest_gap_is_closed(sh):
    """Every path our own digest could name but not block."""
    missed = [p for p in _DIGEST_GAP if not sh.probe_shape(p)]
    assert not missed, "still invisible to the blocker: %s" % missed


def test_credential_and_debug_paths_are_scored(sh):
    missed = [p for p in _CREDS_AND_DEBUG if not sh.probe_shape(p)]
    assert not missed, "credential/debug probes not scored: %s" % missed


def test_the_corpus_can_name_what_the_blocker_scores(sh):
    """A class with no scoring rule is a name for something we cannot stop. Both directions."""
    for p in _DIGEST_GAP:
        if p in ("/1.php7", "/about.php525", "/alfa-rex.php7", "/randkeyword.PhP7"):
            continue          # scored by shape; the corpus names these under php_probe only when
                              # the extension is bare .php, which is fine: naming is for reporting
        assert sh.classify(p), "%s is blockable but the digest cannot name it" % p


def test_the_admin_cannot_be_blocked_from_the_admin_page(sh):
    """/app/admin matched the admin-console rule and came back ACTIONABLE, so the administrator
    moving around their own page accumulated probe_path at weight 3 and could have blocked
    themselves out of the one page only they can reach. Same family as the 439-404 real visitor."""
    assert not sh.probe_shape("/app/admin")
    assert not sh.is_probe_path("/app/admin")


def test_our_own_certificate_renewal_is_not_an_attack(sh):
    """`/.well-known/` is IANA-registered and we serve it deliberately. The dot-directory rule was
    matching it, so every Let's Encrypt validation and security.txt fetch scored probe_path and
    inflated the attack figures in the daily digest."""
    for p in ("/.well-known/security.txt", "/.well-known/acme-challenge/xYz123",
              "/.well-known/sbom.cdx.json"):
        assert not sh.probe_shape(p), p


def test_an_exempt_prefix_is_not_a_hiding_place(sh):
    """The `/api/` lesson, applied to every prefix this shield trusts. The first version of
    is_our_route() returned True for anything under /assets/, so /assets/../../.env was waved
    through before the traversal rule could fire."""
    for p in ("/assets/../../.env", "/media/../../.git/config", "/app/..%2f..%2f.env",
              "/assets/..\\..\\.env", "/.well-knownX/.env", "/.well-known/../.env",
              "/.well-known/shell.php", "/appX/admin"):
        assert sh.probe_shape(p), "%s slipped through a prefix exemption" % p


def test_our_route_list_still_covers_the_application(sh):
    """shield.OUR_TOP is a COPY of main.py::_APP_ROUTES, kept separate so the request path does not
    import the application module. A copy drifts, so assert it. Adding a page without adding it
    here arms the shield against a real customer route."""
    import re
    src = open(os.path.join(_BACKEND, "app", "main.py"), encoding="utf-8").read()
    m = re.search(r"_APP_ROUTES\s*=\s*\{(.*?)\}", src, re.S)
    assert m, "could not read _APP_ROUTES from main.py"
    routes = set(re.findall(r'"([^"]*)"', m.group(1)))
    missing = routes - set(sh.OUR_TOP)
    assert not missing, "routes the shield does not know are ours: %s" % sorted(missing)


# ==============================================================================================
# A BARE ZERO IS NOT A REPORT (2026-08-22). For fourteen days the digest read "33430 attack-shaped
# requests, 0 blocked (0%)" beside Telegram alerts saying blocks were happening, and that line
# could not distinguish "the shield is off" from "below threshold" from "blind". It was blind.
# ==============================================================================================

def _digest():
    """The digest module, imported the same way every other test here imports the app package.
    `import attack_digest` fails: it lives inside the `app` package, not on sys.path."""
    _import_app()
    from app import attack_digest
    return attack_digest


_STATS = {"series": [{"day": "2026-08-21", "attacks": 1117, "blocked": 0,
                      "visits": 73, "sources": 15}],
          "classes": {"php_probe": 24069}, "countries": {},
          "samples": ["/wp-login.php", "/.env", "/1.php7", "/@fs/etc/passwd", "/Dockerfile",
                      "/service-account.json", "/1b7e06/", "/backup.sql", "/swagger.json"]}


def test_the_digest_reports_coverage_not_just_a_zero(sh):
    line = _digest()._explain_block_rate(_STATS, 0)
    assert "coverage" in line, "the digest must say how much of the traffic is even scorable"
    assert "100%" in line, "every sampled path should be scorable after the gap fix: %s" % line


def test_a_coverage_gap_is_named_as_the_reason_for_zero(sh, monkeypatch):
    """The state this file shipped in: half the traffic unscorable, and the summary said only 0."""
    real = sh.probe_shape
    monkeypatch.setattr(sh, "probe_shape", lambda p: real(p) and "@fs" not in p
                        and "php7" not in p and "Dockerfile" not in p
                        and "service-account" not in p and "1b7e06" not in p)
    line = _digest()._explain_block_rate(_STATS, 0)
    assert "CANNOT BE SCORED" in line, \
        "a zero caused by blindness must SAY so rather than printing a bare 0: %s" % line


def test_the_digest_says_when_the_shield_is_simply_off(sh, monkeypatch):
    monkeypatch.setattr(sh, "ENABLED", False)
    assert "SHIELD=off" in _digest()._explain_block_rate(_STATS, 0)
    monkeypatch.setattr(sh, "ENABLED", True)
    monkeypatch.setattr(sh, "ENFORCE", False)
    assert "detection only" in _digest()._explain_block_rate(_STATS, 0)

# ==============================================================================================
# THE 2026-08-26 DIGEST: 43,621 attack-shaped requests, coverage 100%, ZERO blocked. The detector
# was NOT blind this time. The evidence expired faster than the scanner accumulated it:
#   window 300s / block_after 12 / probe_path weight 3 -> 4 probes inside ONE five-minute window,
#   while the three biggest sources ran at 0.53-0.55 per window and one had been at it 12 days.
# The fix is a SECOND, 24-hour horizon keyed on DISTINCT PROBE PATHS, which is the one thing an
# ordinary visitor never produces.
# ==============================================================================================

_SLOW_PROBES = ["/wp-login.php", "/.env", "/1.php7", "/@fs/etc/passwd", "/Dockerfile",
                "/service-account.json", "/backup.sql", "/swagger.json", "/shell.php",
                "/administrator/index.php", "/.git/config", "/terraform.tfstate"]
_CLS = {"browser": "Chrome", "os": "Linux", "device": "desktop"}


def test_a_low_and_slow_scan_is_caught(sh):
    """The pace that defeated the five-minute window.

    THE PACING IS THE TEST. The first version of this called observe() twelve times in a row and
    then asserted BLOCK, which passed even with the slow rule deleted, because twelve probes in
    one instant trip the FAST window on their own. It was defence in depth answering, not the
    thing under test. A negative test that passes because of a different guard proves nothing.

    So the fast evidence is aged out deliberately, which is exactly the real-world condition:
    158.23.147.79 asked for 319 distinct paths at 0.55 per five-minute window, so at any moment
    its recent-hits list was effectively empty while its 24-hour footprint was enormous.
    """
    ip = "158.23.147.79"
    for p in _SLOW_PROBES:
        sh.observe(ip, p, 404, _CLS)
    # Age every FAST hit past the window, leaving only the 24-hour distinct-path record.
    old = time.time() - (sh.cfg("window_s") * 3)
    sh._hits[ip] = [(old, r) for (_t, r) in sh._hits.get(ip, [])]
    sh._miss[ip] = {p: old for p in sh._miss.get(ip, {})}
    assert sh._score(ip, time.time(), sh.cfg("window_s"))[0] < sh.cfg("tarpit_after"), (
        "the fast window must be empty, or this test is measuring the wrong rule")
    assert sh.slow_scan(ip) >= sh.SLOW_DISTINCT
    assert sh.decide(ip, "/")[0] == "BLOCK"


def test_the_slow_window_never_touches_a_real_visitor(sh):
    """THE SAFETY ARGUMENT, and it is the whole reason this rule is allowed to exist: only
    PROBE-SHAPED paths are recorded. On 10 Aug two genuine visitors produced 439 and 362 404s each
    on our own stale routes; a volume rule would have blocked both."""
    ours = ["/", "/app", "/partners", "/demo", "/contact", "/privacy", "/impressum",
            "/experience", "/app/history", "/app/compliance"]
    for i in range(400):
        sh.observe("203.0.113.55", ours[i % len(ours)], 404,
                   {"browser": "Firefox", "os": "Windows 10", "device": "desktop"})
    assert sh.slow_scan("203.0.113.55") == 0, "a visitor's 404s must never enter the slow window"
    assert sh.decide("203.0.113.55", "/")[0] == "ALLOW"


def test_the_slow_window_ages_out(sh):
    """A scanner that stopped yesterday must be forgotten, or this becomes a permanent blocklist
    and an unbounded memory leak."""
    import time as _t
    old = _t.time() - (sh.SLOW_WINDOW_S + 3600)
    sh._slow["198.51.100.9"] = {"/p%d" % i: old for i in range(sh.SLOW_DISTINCT + 8)}
    assert sh.slow_scan("198.51.100.9") == 0
    assert "198.51.100.9" not in sh._slow, "expired entries must be dropped, not just ignored"


def test_the_slow_window_is_bounded(sh):
    """The input is chosen by the attacker, so the state it can create must be capped."""
    for i in range(sh.SLOW_MAX_PATHS + 50):
        sh.observe("203.0.113.77", "/.env%d" % i, 404, _CLS)
    assert len(sh._slow.get("203.0.113.77", {})) <= sh.SLOW_MAX_PATHS


def test_the_app_prefix_is_not_a_hiding_place(sh):
    """I INTRODUCED THIS ON 22 AUG. `/app/` was a blanket prefix exemption added to stop the shield
    blocking the administrator from `/app/admin`, and it exempted everything an attacker could
    append to it. Fifth instance of the same defect in this file."""
    for p in ("/app/wp-login.php", "/app/.env", "/assets/.env", "/media/../../.git/config",
              "/app/../.env"):
        assert sh.probe_shape(p), "%s must be scored, not exempted by a prefix" % p
    for p in ("/app/admin", "/app/history", "/app/compliance", "/app/assistant", "/app/brand",
              "/app/password", "/assets/index-a1b2c3.js", "/media/cassandra.mp4"):
        assert not sh.probe_shape(p), "%s is a real route/asset" % p


def test_a_404_on_our_own_route_is_never_evidence(sh):
    """A stale bookmark is not a scan however many of them there are. The distinct-path floor alone
    was not enough: a visitor with eight old bookmarks clears a floor of six."""
    for p in ("/", "/app", "/partners", "/oldpage", "/app/history"):
        assert sh.is_our_route(p) or not sh.probe_shape(p)
    sh._miss.clear()
    for i in range(50):
        sh.observe("203.0.113.61", "/partners", 404, _CLS)
    assert sh.decide("203.0.113.61", "/")[0] == "ALLOW"


def test_the_new_config_and_wp_patterns(sh):
    """From the 2026-08-26 digest's own unrecognised list."""
    for p in ("/amplifyconfiguration.json", "/application.properties", "/appsettings.json",
              "/appsettings.Production.json", "/blog/wp/v2/users", "/wp-json/wp/v2/users"):
        assert sh.probe_shape(p), p


def test_the_unanchored_json_proposal_stays_refused(sh):
    """The panel proposed `/\.(env|json|properties|py)$`. Unanchored `\.json$` matches the SBOM we
    now serve at /.well-known/sbom.cdx.json. Accepting it would have made a published compliance
    artifact look like an attack, and blocked anyone who fetched it."""
    for p in ("/.well-known/sbom.cdx.json", "/manifest.webmanifest", "/assets/data-a1b2.json"):
        assert not sh.probe_shape(p), "%s is ours and must never score" % p


def test_the_bot_gate_observes_before_it_returns():
    """The gate 404s and returns; observe() came AFTER call_next, so anything the gate handled left
    no trace in the shield's memory. A self-declared scanner could enumerate forever."""
    src = _src("webapp/backend/app/telemetry.py")
    i = src.index("_v.should_block")
    j = src.index("return HTMLResponse(_v.NOT_FOUND_HTML, status_code=404)", i)
    assert "_sh.observe(" in src[i:j], (
        "the bot-gate branch must call shield.observe() before returning, or the shield never "
        "learns from a request the gate handled")


def test_our_own_directories_are_not_reported_as_attacks():
    """/.well-known/ and /assets/ were listed as UNRECOGNISED attacker behaviour on the operator's
    digest. _ours() rstripped the slash before the prefix test."""
    _import_app()
    from app import attack_digest as ad
    for p in ("/.well-known/", "/assets/", "/media/", "/api/"):
        assert ad._ours(p), "%s is our own path and must not be reported as an anomaly" % p
    for p in ("/images/", "/chosen", "/search/label/PHP-Shells"):
        assert not ad._ours(p), "%s is not ours" % p
