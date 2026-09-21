"""TIER 4: did a BROWSER ENGINE render the page -- and can this answer only ever point one way?

WHAT WAS THROWN AWAY BEFORE THIS EXISTED. `telemetry.SKIP_PATH_RE` dropped every static-asset
request before anything could read it, so a browser that fetched `/`, then the bundle, the
stylesheet, the manifest and the icons within two seconds, and an HTTP client that fetched the HTML
and stopped, landed in exactly the same bucket on the fleet page.

THE DANGEROUS HALF OF THIS CHANGE IS THE INVERSE, AND IT IS THE REASON HALF THIS FILE EXISTS. The
moment somebody reads `av == 0` as "no assets, therefore a script", this signal starts accusing the
first navigation from every address, every cached repeat visit and every page served inline -- which
is to say most real people, most of the time. So the constraint is stated in the module docstring
and asserted here as a PROPERTY across every path, rather than grepped for as a word: a check that
has matched its own explanatory comment has happened five separate times in this repository.

Each test below names the mutation that proves it can fail. Run them by breaking the thing, not by
reading the assertion.
"""
import ast
import io
import json
import os
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
sys.path.insert(0, ROOT)

from app import asset_trace as at          # noqa: E402
from app import client_truth as ct         # noqa: E402
from app import fleet                      # noqa: E402
from app import telemetry                  # noqa: E402

AT_SRC = os.path.join(ROOT, "webapp", "backend", "app", "asset_trace.py")
CLIENT_SRC = os.path.join(ROOT, "perseus", "client.py")
TELEMETRY_SRC = os.path.join(ROOT, "webapp", "backend", "app", "telemetry.py")

UA_CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/131.0.0.0 Safari/537.36")
UA_CURL = "curl/8.5.0"
FULL_SF = ct.SF_SITE | ct.SF_MODE | ct.SF_DEST | ct.SF_CHUA

# The assets a COLD production page view of cybergod.ai actually pulls, taken from
# webapp/frontend/dist/index.html and main.jsx rather than invented. An invented list is a list I
# would unconsciously make easy to pass.
COLD_PAGE_ASSETS = ("/assets/index-D8Hy6Z1b.css", "/assets/index-CeiMSUi4.js",
                    "/manifest.webmanifest", "/favicon.ico", "/icon.svg", "/sw.js")


def _read(p):
    with io.open(p, "r", encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(autouse=True)
def clean_ledger():
    """An in-process ledger is module state. A test that inherits the previous test's addresses is
    measuring the order pytest happened to pick."""
    at.reset()
    yield
    at.reset()


def _ev(**kw):
    """One `evt=http` record in the shape BOTH emitters write, tier 4 included."""
    ev = {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "203.0.113.9",
          "method": "GET", "path": "/", "status": 200, "ua": UA_CHROME, "bot": False,
          "hv": "1.1", "hvs": ct.HV_FROM_HOP, "sf": FULL_SF}
    ev.update(kw)
    return {k: v for k, v in ev.items() if v is not _ABSENT}


class _Absent(object):
    pass


_ABSENT = _Absent()


# =================================================================================================
# GROUP 1 -- THE LEDGER
# =================================================================================================

def test_a_browser_shaped_sequence_confirms_a_browser_engine():
    """The real cold page view: a navigation, then the bundle, the stylesheet and the icons.

    MUTATION THAT PROVES IT FAILS: make note() overwrite rather than accumulate
    (`_SEEN[who] = {key: now}`) and the count drops to 1, below the floor.
    """
    ip = "198.51.100.50"
    t = 1_000_000.0
    assert at.evidence(ip, now=t) == 0, "an address nobody has seen starts at zero"
    for i, p in enumerate(COLD_PAGE_ASSETS):
        at.note(ip, p, now=t + 0.1 * i)
    assert at.evidence(ip, now=t + 1) == len(COLD_PAGE_ASSETS)
    assert at.confirmed(ip, now=t + 1) is True
    # ...and the floor is genuinely below what the real page produces, which is the whole
    # justification for the number. If a build ever halves the asset count this still holds.
    assert at.MIN_ASSETS <= len(COLD_PAGE_ASSETS) - 2


def test_the_same_asset_fetched_repeatedly_is_one_asset():
    """DISTINCT paths, or a single image on a retry loop confirms a browser on its own.

    MUTATION: key the inner store by (path, ts) instead of path -> ten hits become ten assets.
    """
    ip = "198.51.100.51"
    t = 2_000_000.0
    for i in range(10):
        at.note(ip, "/assets/index-CeiMSUi4.js", now=t + i)
    assert at.evidence(ip, now=t + 10) == 1
    assert at.confirmed(ip, now=t + 10) is False


def test_old_entries_fall_out_of_the_window():
    """An asset fetched an hour ago says nothing about the page being rendered now.

    MUTATION: drop the `(now - t) < WINDOW_S` filter in evidence() and the stale three still count.
    """
    ip = "198.51.100.52"
    t = 3_000_000.0
    for p in COLD_PAGE_ASSETS[:3]:
        at.note(ip, p, now=t)
    assert at.confirmed(ip, now=t + at.WINDOW_S - 1) is True
    assert at.evidence(ip, now=t + at.WINDOW_S) == 0, "exactly at the window edge it is gone"
    assert at.confirmed(ip, now=t + at.WINDOW_S + 3600) is False
    # And a fresh fetch after the gap starts a new correlation rather than resurrecting the old.
    at.note(ip, COLD_PAGE_ASSETS[0], now=t + 3600)
    assert at.evidence(ip, now=t + 3600) == 1


def test_the_ledger_is_memory_bounded_against_a_source_rotating_flood():
    """A FLOOD MUST NOT TURN THIS INTO THE OUTAGE. Four times the ceiling, pushed in, and the
    ceiling holds after every single write.

    MUTATION: delete the eviction branch in _prune_locked and the table grows to 16,384.
    """
    t = 4_000_000.0
    n = at.MAX_TRACKED * 4
    for i in range(n):
        at.note("10.%d.%d.%d" % (i // 65536 % 256, i // 256 % 256, i % 256),
                "/assets/a%d.js" % i, now=t + i * 0.001)
        assert at.tracked() <= at.MAX_TRACKED, "the ceiling was exceeded at write %d" % i
    assert at.tracked() <= at.MAX_TRACKED
    assert at.tracked() > 0, "evicting EVERYTHING would be a bound that deleted the feature"


def test_the_per_address_path_ceiling_holds_and_never_hides_a_confirmation():
    """One address cannot grow without limit either -- and the cap is far above the floor, so it
    can never cap a count below a decision it would have changed.

    MUTATION: remove the per-address trim and the inner dict reaches 200.
    """
    ip = "198.51.100.53"
    t = 5_000_000.0
    for i in range(200):
        at.note(ip, "/assets/chunk-%d.js" % i, now=t + i * 0.01)
    assert at.evidence(ip, now=t + 3) == at.MAX_PATHS_PER_IP
    assert at.MAX_PATHS_PER_IP > at.MIN_ASSETS, "a cap at or below the floor would delete the signal"
    assert at.confirmed(ip, now=t + 3) is True


def test_concurrent_notes_from_many_threads_neither_raise_nor_corrupt(monkeypatch):
    """Both emitters are concurrent by construction: uvicorn workers, and an ASGI middleware on
    five sites at once.

    THE FIXTURE HAD TO BE BUILT BEFORE THIS MEASURED ANYTHING, AND THE FIRST TWO ATTEMPTS DID NOT.

    Attempt one asserted that an unlocked note() RAISES. It does not: note() swallows its own
    exceptions by design, so the corruption is silent and the assertion measured nothing. Attempt
    two sampled the ceiling from inside the worker, after note() returned, and caught the unlocked
    build 2 or 3 times in 4,800 writes, which is a coin flip dressed as a check.

    WHAT MAKES IT DECISIVE. The unsafe sequence is not the insert (a dict setitem is atomic under
    the GIL) but the read-modify-write inside the two prunes: both iterate and sort a mapping and
    then pop from it, and both leave the ceiling temporarily exceeded if another thread inserts in
    the middle. So the test observes from DEDICATED WATCHER THREADS that sample the two ceilings
    continuously rather than once per write, drives BOTH prunes at once (half the writes hammer one
    address to contend on the per-address trim, half rotate sources to contend on eviction), pushes
    the table ceiling down so the pressure branch runs on nearly every write, and cuts the
    interpreter's switch interval to a microsecond. Measured: 0 violations locked, 441 to 727
    violations unlocked over four runs. That is a margin, not a coincidence.

    MUTATION: replace `with _LOCK:` in note() with `if True:` and this goes red.
    """
    errors, viol, stop = [], [], [False]
    monkeypatch.setattr(at, "MAX_TRACKED", 512)
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    hot = "198.51.100.7"
    ips = ["10.%d.%d.%d" % (i // 65536 % 256, i // 256 % 256, i % 256) for i in range(1, 4000)]

    def watcher():
        while not stop[0]:
            n, m = at.tracked(), at.evidence(hot)
            if n > at.MAX_TRACKED:
                viol.append(("addresses", n))
            if m > at.MAX_PATHS_PER_IP:
                viol.append(("paths", m))

    def worker(k):
        try:
            for i in range(1500):
                if i % 2:
                    at.note(hot, "/assets/h%d-%d.js" % (k, i))
                else:
                    at.note(ips[(k * 37 + i) % len(ips)], "/assets/c%d.js" % (i % 40))
        except Exception as exc:            # pragma: no cover - the failure IS the finding
            errors.append(repr(exc))

    watchers = [threading.Thread(target=watcher) for _ in range(2)]
    workers = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
    try:
        for th in watchers + workers:
            th.start()
        for th in workers:
            th.join(timeout=180)
        assert not [th for th in workers if th.is_alive()], "a worker never finished"
    finally:
        stop[0] = True
        for th in watchers:
            th.join(timeout=30)
        sys.setswitchinterval(old_interval)
    assert not errors, "note() raised under concurrency: %s" % errors[:3]
    assert not viol, "the ledger was observed past its ceiling %d times: %s" % (len(viol), viol[:4])
    # ...and it still answers afterwards, rather than having been left in a shape that returns junk.
    assert at.tracked() <= at.MAX_TRACKED
    got = at.evidence(hot)
    assert isinstance(got, int) and 0 < got <= at.MAX_PATHS_PER_IP, "%r" % (got,)


def test_every_malformed_input_resolves_to_no_evidence_and_never_raises():
    """FAIL OPEN, ALWAYS. An error here is a fact about us, not about the client.

    NO IDENTITY-DEPENDENT SENTINELS HERE. An earlier draft fed `object()` in and asserted zero,
    which failed intermittently because CPython reuses the address of a collected object and
    `str(o)` therefore collided with a key written two lines above. That is the coin-flip test this
    repository already has a rule about, so the inputs are values with stable string forms.
    """
    for bad_ip, bad_path in ((None, "/a.js"), ("", "/a.js"), ("1.2.3.4", None), ("1.2.3.4", ""),
                             (0, 0), (b"\xff", b"\xff"), ([], {}), (1.5, True)):
        at.note(bad_ip, bad_path)            # must not raise
    for bad in (None, "", 0, [], {}, b"\xfe", 1.5):
        got = at.evidence(bad)
        assert isinstance(got, int) and got >= 0
        assert at.confirmed(bad) in (True, False)
    assert at.evidence("no-such-address") == 0 and at.confirmed("no-such-address") is False
    assert at.evidence("1.2.3.4", now="not-a-time") == 0


def test_the_ledger_cannot_reach_a_firewall_a_shield_or_a_ruleset():
    """The import floor as a PROPERTY. A module that imports neither `subprocess` nor `socket` nor
    anything in this estate that enforces cannot shell out to nft and cannot promote a rule.
    Amnezia VPN shares the production host (StGB 202a-303b, EU 2013/40, CFAA 1030).

    MUTATION: add `import socket` to asset_trace.py.
    """
    tree = ast.parse(_read(AT_SRC))
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    assert imported == {"threading", "time"}, "asset_trace.py grew an import: %s" % sorted(imported)
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            called.add(n.func.attr)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            called.add(n.func.id)
    assert not (called & {"decide", "observe", "block", "enter_tarpit", "promote", "system",
                          "popen", "run", "Popen", "emit", "_write", "open"}), sorted(called)


def test_the_module_docstring_states_the_one_way_constraint():
    """THE CONSTRAINT IS A CONTRACT WITH THE NEXT AUTHOR, so it has to be written where the next
    author reads. This is the one assertion in this file that IS about text, and it is about the
    text of the promise rather than about the behaviour, which is asserted everywhere else.

    MUTATION: delete the one-way paragraph from the docstring.
    """
    doc = (at.__doc__ or "").lower()
    assert "one-way positive" in doc
    assert "never be used to conclude that something is a script" in doc
    assert "evidence of nothing" in doc


# =================================================================================================
# GROUP 2 -- THE ONE-WAY PROPERTY, ASSERTED WHERE IT COULD ACTUALLY BE VIOLATED
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


def test_an_address_that_fetched_the_bundle_is_a_CONFIRMED_browser(monkeypatch, tmp_path):
    """RUNG 2. The line carries no usable fetch-metadata evidence at all -- it is the shape of a
    sibling project that has not redeployed the header work -- and it would have been UNJUDGED.
    The asset fetches confirm a browser engine and it becomes a visitor.

    MUTATION: make `_asset_confirms` return False unconditionally and this row goes back to
    unjudged, which is the precise gap tier 4 was built to close.
    """
    r = _fleet_rows(monkeypatch, tmp_path, [
        {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "198.51.100.70",
         "path": "/", "method": "GET", "status": 200, "ua": UA_CHROME, "bot": False,
         "av": at.MIN_ASSETS},
    ])["colt-web"]
    assert r["visitors_24h"] == 1, "a proven browser engine must not sit in the unjudged column"
    assert r["clients_24h"] == 0 and r["unjudged_24h"] == 0
    assert r["confirmed_24h"] == 1, "the payload must say WHICH half was proved rather than inferred"
    assert r["visitor_split"] == "measured"


def test_an_http_client_that_fetched_only_the_html_is_UNJUDGED_and_not_a_client(monkeypatch,
                                                                                tmp_path):
    """THE ASSERTION THIS WHOLE DESIGN TURNS ON, AND THE BUCKET IS NAMED EXPLICITLY.

    A zero is the normal state of a first navigation, a cached repeat visit and an inline page. It
    is NOT a finding. The address stays exactly where the other rungs put it: unjudged.

    MUTATION: add `elif r.get("av") == 0: p["clients"].add(ip)` to the counting and this goes red.
    """
    r = _fleet_rows(monkeypatch, tmp_path, [
        {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "198.51.100.71",
         "path": "/", "method": "GET", "status": 200, "ua": UA_CHROME, "bot": False, "av": 0},
    ])["colt-web"]
    assert r["unjudged_24h"] == 1, "a zero asset count must leave the address exactly where it was"
    assert r["clients_24h"] is None and r["visitors_24h"] is None
    assert r["addresses_24h"] == 1 and r["visitor_split"] == "none"


def test_a_zero_or_low_av_can_never_move_an_address_into_the_clients_bucket(monkeypatch, tmp_path):
    """THE PROPERTY, SWEPT ACROSS EVERY PATH THROUGH THE COUNTING RATHER THAN ONE CASE OF IT.

    Every combination of `av` below the floor against every other shape of record, and in not one
    of them may the client count be larger than the same record with the asset evidence removed.
    A regression that made a zero incriminating would have to survive all of them.

    MUTATION: as above; also `return int(av) < MIN_ASSETS` in `_asset_confirms` reverses the rung
    and several of these go red at once.
    """
    base = {"evt": "http", "ts": int(time.time()), "service": "colt-web", "path": "/",
            "method": "GET", "status": 200, "ua": UA_CHROME}
    shapes = [
        dict(bot=False, hv="1.1", hvs=ct.HV_FROM_HOP, sf=FULL_SF),   # determinable browser
        dict(bot=False, hv="1.1", hvs=ct.HV_FROM_HOP, sf=0),         # contradicting itself
        dict(bot=False),                                             # no header evidence at all
        dict(bot=True, ua=UA_CURL),                                  # honest tool
    ]
    for si, shape in enumerate(shapes):
        rows_without, rows_with = [], []
        for ai, av in enumerate((0, 1, at.MIN_ASSETS - 1)):
            ip = "198.51.100.%d" % (100 + si * 8 + ai)
            r0 = dict(base, ip=ip, **shape)
            rows_without.append(r0)
            rows_with.append(dict(r0, av=av))
        a = _fleet_rows(monkeypatch, tmp_path, rows_without)["colt-web"]
        b = _fleet_rows(monkeypatch, tmp_path, rows_with)["colt-web"]
        assert (b["clients_24h"] or 0) <= (a["clients_24h"] or 0), (
            "a low av added %r to the clients bucket" % (shape,))
        assert (b["visitors_24h"] or 0) >= (a["visitors_24h"] or 0), (
            "a low av took %r OUT of the visitors bucket" % (shape,))
        # AND THE RUNG ITSELF NEVER FIRES BELOW THE FLOOR. Without this the sweep above passes for
        # an INVERTED comparison (`av < MIN_ASSETS -> confirmed`), which promotes exactly the
        # addresses the design forbids promoting while still never touching the clients count.
        assert (b["confirmed_24h"] or 0) == (a["confirmed_24h"] or 0), (
            "an av below the floor was CONFIRMED as a browser: %r" % (shape,))
    for av in (0, 1, at.MIN_ASSETS - 1):
        assert fleet._asset_confirms(dict(base, ip="1.2.3.4", bot=False, av=av)) is False


def test_a_self_identified_bot_that_also_fetched_assets_is_still_a_client(monkeypatch, tmp_path):
    """PRECEDENCE, RUNG 1 OVER RUNG 2. A headless Chrome crawler fetches the bundle exactly as a
    person's Chrome does -- that is the honest limit of this signal -- so the moment it claims to
    be a bot, or contradicts its own user agent, that claim wins and asset evidence buys it
    nothing.

    MUTATION: move the `_asset_confirms` branch above the `r.get("bot")` branch in fleet.py and
    both halves of this go red.
    """
    # a) self-identified crawler, with a full cold page view behind it
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip="198.51.100.80", ua=UA_CURL, bot=True, sf=0,
            av=len(COLD_PAGE_ASSETS)),
    ])["colt-web"]
    assert r["clients_24h"] == 1 and r["visitors_24h"] == 0
    assert r["confirmed_24h"] == 0, "a client must never appear in the confirmed subset"

    # b) a client that contradicted its own user agent, same asset evidence
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip="198.51.100.81", ua=UA_CHROME, bot=False, sf=0,
            hv="1.1", hvs=ct.HV_FROM_CLIENT, av=len(COLD_PAGE_ASSETS)),
    ])["colt-web"]
    assert r["clients_24h"] == 1 and r["visitors_24h"] == 0 and r["confirmed_24h"] == 0

    # c) and the one-bucket rule still runs one way across LINES: a scanner that also renders the
    #    homepage in a real engine is a client for the window.
    ip = "198.51.100.82"
    r = _fleet_rows(monkeypatch, tmp_path, [
        _ev(service="colt-web", ip=ip, ua=UA_CHROME, bot=False, sf=FULL_SF, av=6, path="/"),
        _ev(service="colt-web", ip=ip, ua=UA_CURL, bot=True, sf=0, path="/wp-login.php"),
    ])["colt-web"]
    assert r["visitors_24h"] == 0 and r["clients_24h"] == 1 and r["addresses_24h"] == 1


def test_an_absent_av_never_confirms_anything(monkeypatch, tmp_path):
    """`av` ABSENT means NOBODY LOOKED, and it must never be filled in with a number.

    Every line every project wrote before today carries no `av`. If the reader ever defaults the
    missing field to anything at or above the floor, the entire history of the estate becomes
    confirmed browsers overnight, which is a confident wrong figure manufactured out of our own
    ignorance rather than out of evidence. So the reader treats absent exactly as it treats a value
    below the floor: NOT CONFIRMED, leave the address where the other rungs put it. That is safe
    only because the signal is one-way, which is the reason it is safe to say so here.

    MUTATION: `av = r.get("av", _asset_trace.MIN_ASSETS)` in `_asset_confirms` and this goes red on
    both halves.
    """
    old = {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "198.51.100.90",
           "path": "/", "method": "GET", "status": 200, "ua": UA_CHROME, "bot": False,
           "hv": "1.1", "hvs": ct.HV_FROM_HOP, "sf": FULL_SF}
    assert fleet._asset_confirms(old) is False, "an absent av must never confirm"
    assert fleet._asset_confirms({}) is False and fleet._asset_confirms({"av": None}) is False
    r = _fleet_rows(monkeypatch, tmp_path, [dict(old)])["colt-web"]
    assert r["visitors_24h"] == 1, "the fetch-metadata rung still judges it, as it did before"
    assert r["confirmed_24h"] == 0, "nothing was PROVED about this address; only inferred"
    # ...and the line that DOES carry the evidence is confirmed, so the zero above is a measurement
    # rather than a rung that never fires.
    r2 = _fleet_rows(monkeypatch, tmp_path, [dict(old, av=at.MIN_ASSETS)])["colt-web"]
    assert r2["confirmed_24h"] == 1


def test_the_fleet_page_survives_the_ledger_being_absent(monkeypatch, tmp_path):
    """AN OPTIONAL LOOKUP MAY MAKE A PAGE MORE ACCURATE, NEVER LESS, AND NEVER 500 IT. Without
    asset_trace the CONFIRMED promotion is simply not applied and the row falls back to what the
    header evidence said, which is where it already was.

    THERE ARE TWO GUARDS ON THIS PATH AND BOTH HAVE TO BE DEFEATED FOR THE MUTATION TO BITE, which
    is the point: `_asset_confirms` checks for the missing module AND wraps everything in a
    fail-open except, so removing either one alone changes nothing. A negative test that passes
    because of the OTHER guard measures that other guard.

    MUTATION (both together): delete `if _asset_trace is None: return False` and change the
    trailing `except Exception: return False` to `raise`. status() then raises AttributeError and
    the admin page 500s, which is the outage this shape is written to prevent.
    """
    monkeypatch.setattr(fleet, "_asset_trace", None)
    r = _fleet_rows(monkeypatch, tmp_path, [
        {"evt": "http", "ts": int(time.time()), "service": "colt-web", "ip": "198.51.100.91",
         "path": "/", "method": "GET", "status": 200, "ua": UA_CHROME, "bot": False, "av": 9},
    ])["colt-web"]
    assert r["addresses_24h"] == 1, "the address total never depended on the lookup"
    assert r["unjudged_24h"] == 1 and r["visitor_split"] == "none"
    assert fleet._asset_confirms({"av": 99}) is False, \
        "with the ledger gone there is no floor to compare against, so nothing is confirmed"


def test_nothing_in_this_tier_can_block_tarpit_score_or_propose_a_rule():
    """The property as a grep over the CALL SITES rather than over prose: neither the ledger nor
    the counting may name anything that enforces, and the sidecar's ledger may not either.

    MUTATION: call `_sh.observe` or `decide` from `_asset_confirms`.
    """
    forbidden = {"decide", "enter_tarpit", "leave_tarpit", "tarpit_seconds", "is_blocked",
                 "can_promote", "promote", "system", "popen", "Popen"}
    for src, names in ((AT_SRC, None), (os.path.join(ROOT, "webapp", "backend", "app", "fleet.py"),
                                        ("_asset_confirms",))):
        tree = ast.parse(_read(src))
        if names:
            tree = [n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name in names]
            assert tree, "the function under test vanished from %s" % src
        else:
            tree = [tree]
        for node in tree:
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    nm = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                    assert nm not in forbidden, "%s calls %s" % (src, nm)


# =================================================================================================
# GROUP 3 -- THE EMITTERS, AND THE VALUES THE TWO COPIES MAY NOT DISAGREE ON
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


def test_the_sidecar_and_this_module_agree_on_the_constants():
    """`perseus/client.py` may not import asset_trace -- its import floor is a security control --
    so the four numbers live in two files. This is the weld, same device the SF_* bitmask uses.

    MUTATION: change ASSET_WINDOW_S to 60 in perseus/client.py.
    """
    pairs = (("WINDOW_S", "ASSET_WINDOW_S"), ("MIN_ASSETS", "ASSET_MIN_ASSETS"),
             ("MAX_TRACKED", "ASSET_MAX_TRACKED"),
             ("MAX_PATHS_PER_IP", "ASSET_MAX_PATHS_PER_IP"),
             ("_SWEEP_S", "_ASSET_SWEEP_S"))
    mine = _consts(_read(AT_SRC), tuple(a for a, _ in pairs))
    theirs = _consts(_read(CLIENT_SRC), tuple(b for _, b in pairs))
    for a, b in pairs:
        assert a in mine, "asset_trace.py stopped declaring %s" % a
        assert b in theirs, "perseus/client.py stopped declaring %s" % b
        assert mine[a] == theirs[b], "%s (%r) has drifted from %s (%r)" % (a, mine[a], b, theirs[b])


def test_the_sidecar_and_telemetry_agree_on_what_a_static_asset_IS():
    """The predicate lives in telemetry (it is telemetry's skip decision) and is restated in the
    sidecar, which may import nothing. A drift here means one emitter records an asset the other
    calls a navigation, and the same visitor then gets two different answers.

    MUTATION: drop `|webmanifest` from either pattern.
    """
    mine = _consts(_read(TELEMETRY_SRC), ("SKIP_PATH_PAT",))
    theirs = _consts(_read(CLIENT_SRC), ("ASSET_SUFFIX_PAT",))
    assert "SKIP_PATH_PAT" in mine and "ASSET_SUFFIX_PAT" in theirs
    assert mine["SKIP_PATH_PAT"] == theirs["ASSET_SUFFIX_PAT"]
    # ...and it is the pattern the live regex is actually built from, not a decorative twin.
    import re as _re
    assert telemetry.SKIP_PATH_RE.pattern == mine["SKIP_PATH_PAT"]
    for p in COLD_PAGE_ASSETS:
        assert _re.search(theirs["ASSET_SUFFIX_PAT"], p, _re.I), "%s is not seen as an asset" % p
    for p in ("/", "/app", "/partners", "/api/me"):
        assert not _re.search(theirs["ASSET_SUFFIX_PAT"], p, _re.I), "%s is not a navigation" % p


def test_the_client_import_floor_is_still_exactly_the_seven_permitted_modules():
    """Restated here as well as in test_perseus_shield.py ON PURPOSE. This change is the second
    most likely thing ever to break it -- the obvious implementation is `import asset_trace` -- and
    the test that would catch it lives in a file a reader of this one need not open.

    MUTATION: add `import collections` to perseus/client.py.
    """
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


def test_an_asset_produces_NO_NEW_LOG_LINE(monkeypatch):
    """THE WHOLE AFFORDABILITY ARGUMENT. Assets were dropped from the log because they would drown
    it, and that reason has not changed: the fact is kept in memory and leaves as one integer.

    The emitter is asserted NOT CALLED, which is the property, rather than the log being asserted
    small, which would pass for an emitter that wrote a shorter line.

    MUTATION: move the `asset_trace.note()` call to AFTER the `return` (it then never runs, and
    the follow-up assertion on the count goes red), or delete the `return` (the emitter fires and
    this assertion goes red).
    """
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    seen = []
    monkeypatch.setattr(telemetry, "emit", lambda **k: seen.append(k))
    app = Starlette(routes=[Route("/", lambda r: PlainTextResponse("ok")),
                            Route("/assets/index-CeiMSUi4.js", lambda r: PlainTextResponse("x")),
                            Route("/favicon.ico", lambda r: PlainTextResponse("x")),
                            Route("/manifest.webmanifest", lambda r: PlainTextResponse("x"))])
    telemetry.install(app)
    for p in ("/assets/index-CeiMSUi4.js", "/favicon.ico", "/manifest.webmanifest"):
        _asgi_get(app, p, [("user-agent", UA_CHROME)])
    assert seen == [], "a static asset wrote a log line: %r" % seen[:2]
    # ...and the fact was nonetheless recorded, or the assertion above would pass for a change
    # that simply deleted the feature.
    assert at.evidence("203.0.113.55") == 3


def test_telemetry_stamps_av_on_the_navigation_that_follows_the_assets(monkeypatch):
    """FOLLOW THE VALUE END TO END. A field the emitter drops is invisible to every reader test in
    this file and every one of them would still pass.

    MUTATION: remove `av=_av(ip)` from the record and the first assertion goes red; return 0
    instead of None from `_av` when asset_trace is missing and the omission assertion goes red.
    """
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    seen = []
    monkeypatch.setattr(telemetry, "emit", lambda **k: seen.append(k))
    routes = [Route("/", lambda r: PlainTextResponse("ok"))]
    routes += [Route(p, lambda r: PlainTextResponse("x")) for p in COLD_PAGE_ASSETS]
    app = Starlette(routes=routes)
    telemetry.install(app)

    _asgi_get(app, "/", [("user-agent", UA_CHROME)])
    first = [e for e in seen if e.get("evt") == "http"][-1]
    assert first["av"] == 0, "the FIRST navigation legitimately has no assets behind it yet"

    for p in COLD_PAGE_ASSETS:
        _asgi_get(app, p, [("user-agent", UA_CHROME)])
    _asgi_get(app, "/", [("user-agent", UA_CHROME)])
    second = [e for e in seen if e.get("evt") == "http"][-1]
    assert second["av"] == len(COLD_PAGE_ASSETS)
    assert second["av"] >= at.MIN_ASSETS and fleet._asset_confirms(second) is True

    # AND THE FIELD IS OMITTED, NEVER DEFAULTED, WHEN THE LEDGER IS NOT THERE. `av` absent and
    # `av: 0` are different facts, exactly as `sf` already distinguishes them.
    monkeypatch.setattr(telemetry, "asset_trace", None)
    _asgi_get(app, "/", [("user-agent", UA_CHROME)])
    third = [e for e in seen if e.get("evt") == "http"][-1]
    assert "av" not in third, "an unmeasured field must be ABSENT, not 0"


def test_the_sidecar_records_assets_and_stamps_av_on_navigations(monkeypatch):
    """The SAME arithmetic on the other emitter, over its own ledger, because a capability colt-web
    has and the sidecar discards is invisible to every colt-web test.

    MUTATION: pass `av=None` in the sidecar's three observe() calls and the navigation stops
    carrying the count.
    """
    import perseus.client as pc
    written = []
    monkeypatch.setattr(pc, "_write", lambda d: written.append(d))
    monkeypatch.setattr(pc, "ENABLED", True)
    pc._assets.clear()
    pc._assets_last.clear()
    ip = "203.0.113.77"
    for p in COLD_PAGE_ASSETS:
        pc.asset_note(ip, p)
    assert pc.asset_evidence(ip) == len(COLD_PAGE_ASSETS)
    pc.observe(ip, "/", 200, 5, UA_CHROME, "", "GET", av=pc.asset_evidence(ip))
    pc.observe("203.0.113.78", "/", 200, 5, UA_CHROME, "", "GET")
    rich, bare = written
    assert rich["av"] == len(COLD_PAGE_ASSETS)
    assert "av" not in bare, "an unmeasured field must be ABSENT, not 0"
    # A measured zero IS written: it is the difference between looking and not looking.
    pc.observe("203.0.113.79", "/", 200, 5, UA_CHROME, "", "GET", av=0)
    assert written[-1]["av"] == 0
    pc._assets.clear()
    pc._assets_last.clear()


def test_the_sidecars_own_ledger_is_memory_bounded_too():
    """THE COPY IS A SECOND IMPLEMENTATION AND A SECOND FLOOD SURFACE. The constants are welded by
    ast below, but a constant that nothing enforces is a comment: this file runs on five sites'
    request paths at once and a source-rotating scanner must not turn it into the outage.

    MUTATION: delete the eviction branch in `_asset_prune` and the table grows past the ceiling.
    """
    import perseus.client as pc
    pc._assets.clear()
    pc._assets_last.clear()
    try:
        t = 6_000_000.0
        n = pc.ASSET_MAX_TRACKED * 2
        for i in range(n):
            pc.asset_note("10.%d.%d.%d" % (i // 65536 % 256, i // 256 % 256, i % 256),
                          "/assets/a%d.js" % i, now=t + i * 0.001)
            assert len(pc._assets) <= pc.ASSET_MAX_TRACKED, "ceiling exceeded at write %d" % i
        assert len(pc._assets) > 0, "evicting EVERYTHING would be a bound that deleted the feature"
        # per-address ceiling, same as the module's
        for i in range(200):
            pc.asset_note("198.51.100.8", "/assets/chunk-%d.js" % i, now=t + 10 + i * 0.01)
        assert pc.asset_evidence("198.51.100.8", now=t + 12) == pc.ASSET_MAX_PATHS_PER_IP
        # and the window
        # the newest of those 200 was written at t+11.99, so the window closes just after that
        assert pc.asset_evidence("198.51.100.8", now=t + 12 + pc.ASSET_WINDOW_S) == 0
    finally:
        pc._assets.clear()
        pc._assets_last.clear()


def _asgi_get(app, path="/", headers=(), http_version="1.1"):
    """Call an ASGI app DIRECTLY. No starlette.testclient, and therefore no httpx.

    httpx is a dependency of starlette's TESTING helper, not of this application. It is present in
    the sandbox this was written in and absent on the operator's Windows Python, so importing it
    would fail his ship with "The starlette.testclient module requires the httpx package" -- the
    root cause CLAUDE.md already records for several wasted ships. Same harness test_client_truth.py
    and test_security_headers.py already use.
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
