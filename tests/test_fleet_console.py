"""The four sibling projects get cybergod's console, and the console must not be able to hurt them.

WHAT CHANGED (2026-09-17). The operator received two different messages about the same class of
event: cybergod's came with a menu he could press, and jobhuntwow's / jev's / klima's / s4biz's came
as flat text, because colt-web has no code inside those projects' request paths. It now has
`perseus_holds.json` -- a file their sidecars already poll -- so the sibling alert carries the same
buttons, scoped to one project and bounded in time.

WHY THE TESTS IN THIS FILE ARE THE ONES THAT MATTER. A callback that reaches this bot can now stop
traffic on five production sites. That is a bigger blast radius than anything else on this console,
so the cases below are about AUTHORISATION and BOUNDS first and features second:

  * a callback from the wrong chat changes nothing, and says so;
  * a hold without an expiry, or with one past the ceiling, cannot be written by ANY path;
  * the write is atomic, because five sidecars read it while we write it;
  * an address already held does not page the operator again;
  * nothing on the menu connects back to the source, and that is asserted against the ACTION TABLE
    rather than against prose, because prose is not a control.

NO INTERNET. The Telegram transport is a list; notify.telegram is replaced; AbuseIPDB is never
called. Nothing here touches /var/log/colt: every path is a tmp_path.
"""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
sys.path.insert(0, ROOT)

from app import fleet, notify, shield_console  # noqa: E402

OPERATOR_CHAT = "1234567"
ADMIN = "feranicus@s4biz.io"
IP = "104.28.222.17"
SVC = "jhw-web"
NAME = "jobhuntwow.com"
PROBES = ["/.env", "/wp-login.php", "/.git/config", "/phpinfo", "/vendor/phpunit"]


class FakeShield:
    """Only what apply_decisions' trailer actually touches. It must never be reachable from a fleet
    action -- several cases below assert exactly that, so this object doubles as the tripwire."""

    def __init__(self):
        self.ALLOW_IPS = set()
        self.BLOCK_NETS = {}
        self.STRICT_UNTIL = [0]
        self.EXTRA_PROBE_PATHS = set()
        self._blocked = {}

    def state(self):
        return {"blocked": dict(self._blocked), "watching": 0, "enforcing": True}

    def unblock(self, ip):
        self._blocked.pop(ip, None)

    def probe_shape(self, path):
        return True


class Telegram:
    """A transport with notify.telegram's SIGNATURE -- the keyboard branch is chosen by reading it,
    so a stub without `reply_markup` would silently exercise the legacy path instead."""

    def __init__(self):
        self.sent = []

    def __call__(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))
        return True

    @property
    def texts(self):
        return [t for t, _m in self.sent]

    @property
    def menus(self):
        return [m for _t, m in self.sent if m]


@pytest.fixture
def console(tmp_path, monkeypatch):
    """The console, pointed entirely at a temporary estate, with delivery captured."""
    monkeypatch.setattr(shield_console, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(shield_console, "PENDING", str(tmp_path / "shield_pending.json"))
    monkeypatch.setattr(shield_console, "DECISIONS", str(tmp_path / "shield_decisions.json"))
    monkeypatch.setattr(shield_console, "HOLDS", str(tmp_path / "perseus_holds.json"))
    monkeypatch.setenv("ALERT_TG_CHAT", OPERATOR_CHAT)
    monkeypatch.setenv("EVENTS_LOG", str(tmp_path / "events.log"))
    shield_console._fleet_muted.clear()
    shield_console._last_announced.clear()

    tg = Telegram()
    monkeypatch.setattr(notify, "telegram", tg)
    logs = []
    monkeypatch.setattr(notify, "_log", lambda **k: logs.append(k))
    tg.logs = logs
    return tg


def _announce(tg, ip=IP, svc=SVC, name=NAME, paths=None, now=None):
    return shield_console.announce_fleet(name, svc, ip, paths or PROBES, send=tg, now=now)


def _decide(incident, action, **choice):
    """Write what the bot would have written into the shared decisions file."""
    choice.setdefault("ts", time.time())
    choice["action"] = action
    with open(shield_console.DECISIONS, "w", encoding="utf-8") as fh:
        json.dump({incident: choice}, fh)


def _holds():
    try:
        with open(shield_console.HOLDS, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _evts(tg, name):
    return [k for k in tg.logs if k.get("evt") == name]


# ------------------------------------------------------------------ authorisation
def test_a_callback_from_the_wrong_chat_changes_nothing_and_is_refused(console):
    """THE WHOLE RISK OF THIS FEATURE IN ONE CASE. Anyone who learns the bot's username can send it
    a callback; the acting process must verify the ORIGIN itself rather than inherit a check it
    cannot see. The identity beside the chat id is deliberately not a rescue: a mismatched origin is
    positive evidence, not a missing field."""
    tg = console
    incident = _announce(tg)
    assert incident, "the fixture must produce an ask, or this proves nothing"
    _decide(incident, "fhold24", chat="999999", by=ADMIN)

    shield_console.apply_decisions(FakeShield())

    doc = _holds()
    assert not (doc or {}).get("holds"), "a callback from a foreign chat wrote a hold: %r" % doc
    refusals = _evts(tg, "fleet_hold_refused")
    assert refusals, "the refusal was not logged; a refusal nobody can see is not a control"
    assert refusals[0]["chat"] == "999999" and refusals[0]["ip"] == IP
    assert "REFUSED" in tg.texts[-1] and "999999" in tg.texts[-1], tg.texts[-1]


def test_an_unset_operator_chat_does_not_mean_any_chat(console, monkeypatch):
    """FAIL CLOSED. With ALERT_TG_CHAT empty there is nothing to verify a chat id against, and
    'we could not check' must never resolve to 'allowed'."""
    monkeypatch.setenv("ALERT_TG_CHAT", "")
    ok, why = shield_console.authorised({"chat": "999999"})
    assert ok is False and "ALERT_TG_CHAT" in why, why


def test_a_bot_user_who_is_not_an_administrator_cannot_hold_another_site(console):
    """The bot's own gate admits Colt AEs and partners, because they may run an assessment. A hold
    reaches four OTHER production sites, so this console is narrower than the gate above it."""
    tg = console
    incident = _announce(tg)
    _decide(incident, "fhold1", by="some.ae@colt.net")
    shield_console.apply_decisions(FakeShield())
    assert not (_holds() or {}).get("holds")
    assert "not an administrator" in tg.texts[-1], tg.texts[-1]


def test_a_decision_with_no_origin_at_all_is_refused(console):
    ok, why = shield_console.authorised({"action": "fhold24"})
    assert ok is False and "neither" in why, why


# ------------------------------------------------------------------ a valid action
def test_a_valid_callback_writes_a_bounded_hold_for_the_right_project(console):
    """The positive case, and every field of the contract the sidecars read."""
    tg = console
    t0 = time.time()
    incident = _announce(tg)
    _decide(incident, "fhold24", chat=OPERATOR_CHAT)
    shield_console.apply_decisions(FakeShield())

    doc = _holds()
    assert doc and isinstance(doc.get("generated"), int)
    assert len(doc["holds"]) == 1, doc
    h = doc["holds"][0]
    assert h["cidr"] == "104.28.222.17/32"
    assert h["service"] == SVC, "a hold must be scoped to ONE project, not the estate"
    assert h["by"] == "telegram"
    assert "Hold 24h" in h["why"]
    assert t0 < h["until"] <= t0 + shield_console.MAX_HOLD_S + 1, h


def test_block_a_24_holds_the_network_not_the_estate(console):
    tg = console
    incident = _announce(tg)
    _decide(incident, "fnet1", chat=OPERATOR_CHAT)
    shield_console.apply_decisions(FakeShield())
    h = _holds()["holds"][0]
    assert h["cidr"] == "104.28.222.0/24" and h["service"] == SVC
    assert h["until"] - time.time() <= 3600 + 1


def test_the_admin_identity_the_bot_records_today_is_accepted(console):
    """The bot writes `by`, not `chat`. If this path did not work every button on the sibling menu
    would be decorative -- which is worse than no button."""
    tg = console
    incident = _announce(tg)
    _decide(incident, "fhold1", by=ADMIN)
    shield_console.apply_decisions(FakeShield())
    assert len(_holds()["holds"]) == 1


def test_a_fleet_action_never_reaches_cybergods_own_shield(console):
    """The two action tables are disjoint on purpose. A sibling's tap must not change cybergod.ai's
    posture, and cybergod's `strict` must not be applicable to a sibling incident."""
    assert not (set(shield_console.ACTIONS) & set(shield_console.FLEET_ACTIONS))
    tg = console
    sh = FakeShield()
    incident = _announce(tg)
    _decide(incident, "fhold24", chat=OPERATOR_CHAT)
    shield_console.apply_decisions(sh)
    assert not sh._blocked and not sh.BLOCK_NETS and sh.STRICT_UNTIL[0] == 0
    assert not sh.EXTRA_PROBE_PATHS and not sh.ALLOW_IPS

    _decide(incident, "strict", chat=OPERATOR_CHAT)   # cybergod's key, on a fleet incident
    shield_console.apply_decisions(sh)
    assert sh.STRICT_UNTIL[0] == 0, "a cybergod action was applied through a sibling's menu"


# ------------------------------------------------------------------ the bounds
def test_no_path_can_write_a_hold_without_an_expiry(console):
    """`until` is MANDATORY and the check lives in the WRITER, not in the five callers -- a bound
    every caller has to remember is a bound the sixth caller will not have."""
    written, rejected = shield_console._write_holds(
        [{"cidr": "1.2.3.4/32", "service": SVC, "why": "operator: forever", "by": "telegram"}])
    assert written == [] and rejected and "until" in rejected[0], rejected
    assert not (_holds() or {}).get("holds")


def test_no_path_can_write_a_hold_beyond_the_maximum(console):
    now = time.time()
    written, rejected = shield_console._write_holds(
        [{"cidr": "1.2.3.4/32", "service": SVC, "until": int(now + 10 * 86400),
          "why": "operator: ten days", "by": "telegram"}])
    assert written == [] and rejected and "maximum" in rejected[0], rejected


def test_a_hold_in_the_past_is_not_a_hold(console):
    written, rejected = shield_console._write_holds(
        [{"cidr": "1.2.3.4/32", "service": SVC, "until": int(time.time() - 10)}])
    assert written == [] and "future" in rejected[0], rejected


def test_an_over_long_request_is_clamped_rather_than_refused(console):
    """add_hold clamps; the writer then re-checks. Two gates, and the second one is the one a future
    caller inherits for free."""
    rec, note, _n = shield_console.add_hold("1.2.3.4/32", SVC, 10 * 86400, "Hold forever")
    assert rec is not None, note
    assert rec["until"] - time.time() <= shield_console.MAX_HOLD_S + 1


def test_the_environment_can_lower_a_bound_and_never_raise_one(monkeypatch):
    """A limit a droplet .env can widen is not a limit, and that file is the least reviewed surface
    in the estate."""
    assert shield_console._bounded_env("X", shield_console.HOLD_CEILING_S, 60,
                                       shield_console.HOLD_CEILING_S) == 86400
    monkeypatch.setenv("X", str(365 * 86400))
    assert shield_console._bounded_env("X", shield_console.HOLD_CEILING_S, 60,
                                       shield_console.HOLD_CEILING_S) == shield_console.HOLD_CEILING_S
    monkeypatch.setenv("X", "600")
    assert shield_console._bounded_env("X", shield_console.HOLD_CEILING_S, 60,
                                       shield_console.HOLD_CEILING_S) == 600
    monkeypatch.setenv("X", "not a number")
    assert shield_console._bounded_env("X", 900, 60, 86400) == 900


def test_every_menu_duration_is_inside_the_ceiling(console):
    """DERIVE N FROM THE TABLE. Counting the buttons by hand is how the fourth one is missed."""
    durations = [spec["hold"][1] for spec in shield_console.FLEET_ACTIONS.values()
                 if spec["hold"][0] in ("ip", "net")]
    assert durations, "the menu offers no hold at all"
    for d in durations:
        assert shield_console.HOLD_FLOOR_S <= d <= shield_console.MAX_HOLD_S, d


def test_a_hold_wider_than_a_24_is_refused(console):
    written, rejected = shield_console._write_holds(
        [{"cidr": "104.28.0.0/16", "service": SVC, "until": int(time.time() + 600)}])
    assert written == [] and "/24" in rejected[0], rejected


def test_the_live_hold_cap_refuses_rather_than_silently_evicting(console, monkeypatch):
    monkeypatch.setattr(shield_console, "MAX_HOLDS", 3)
    now = time.time()
    many = [{"cidr": "10.0.0.%d/32" % i, "service": SVC, "until": int(now + 600)}
            for i in range(6)]
    written, rejected = shield_console._write_holds(many, now)
    assert len(written) == 3 and len(rejected) == 3
    assert all("cap of 3" in r for r in rejected), rejected
    assert len(_holds()["holds"]) == 3


def test_expired_holds_do_not_survive_the_next_write(console):
    now = time.time()
    shield_console._write_holds([{"cidr": "10.0.0.1/32", "service": SVC, "until": int(now + 120)}],
                                now)
    assert shield_console.held("10.0.0.1", SVC, now) is True
    assert shield_console.held("10.0.0.1", SVC, now + 300) is False, "a hold must lapse by itself"
    assert shield_console.live_holds(now + 300) == []


# ------------------------------------------------------------------ atomicity
def test_the_holds_file_is_written_atomically(console, monkeypatch):
    """FIVE SIDECARS READ THIS WHILE WE WRITE IT. A truncated document parses as 'no holds', which
    would disarm every project silently -- the worst possible failure direction."""
    calls = []
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda a, b: (calls.append((a, b)), real(a, b))[1])
    shield_console._write_holds(
        [{"cidr": "1.2.3.4/32", "service": SVC, "until": int(time.time() + 600)}])
    assert calls, "the holds file was written in place, not renamed over"
    src, dst = calls[-1]
    assert dst == shield_console.HOLDS
    assert os.path.dirname(src) == os.path.dirname(dst), (
        "the temp file must sit in the SAME directory, or the rename is a cross-device copy and "
        "stops being atomic")


def test_a_crash_half_way_through_leaves_the_previous_file_intact(console, monkeypatch):
    """Prove the fixture first: write a good file, break the serialiser, and assert a READER still
    sees the good one."""
    now = time.time()
    shield_console._write_holds([{"cidr": "9.9.9.9/32", "service": SVC, "until": int(now + 600)}],
                                now)
    good = _holds()
    assert good["holds"], "the fixture did not establish a previous good file"

    def boom(*a, **k):
        a[1].write('{"generated": 0, "hol')      # a real half-written document
        raise IOError("disk went away")

    monkeypatch.setattr(shield_console.json, "dump", boom)
    written, rejected = shield_console._write_holds(
        [{"cidr": "8.8.8.8/32", "service": SVC, "until": int(now + 600)}], now)
    assert written == [] and rejected
    assert _holds() == good, "a reader could have seen a truncated holds file"
    assert shield_console.held("9.9.9.9", SVC, now) is True


# ------------------------------------------------------------------ the confirmation
def test_the_confirmation_names_the_target_and_the_expiry(console):
    """A confirmation that reads the same whether or not anything happened is not a confirmation.
    This one is composed from the record READ BACK off disk."""
    tg = console
    incident = _announce(tg)
    _decide(incident, "fhold24", chat=OPERATOR_CHAT)
    shield_console.apply_decisions(FakeShield())

    h = _holds()["holds"][0]
    msg = tg.texts[-1]
    assert "APPLIED" in msg
    assert "104.28.222.17/32" in msg, msg
    assert NAME in msg, msg
    assert "until %s UTC" % shield_console._hhmm(h["until"]) in msg, msg
    assert "24h" in msg and "expires by itself" in msg, msg
    assert "Fleet holds: 1 of %d" % shield_console.MAX_HOLDS in msg, msg


def test_a_failed_action_is_reported_and_never_swallowed(console):
    """Silence after a tap is indistinguishable from success."""
    tg = console
    incident = shield_console.announce_fleet(NAME, SVC, "2a01:4f8::1", PROBES, send=tg)
    _decide(incident, "fnet1", chat=OPERATOR_CHAT)      # /24 on an IPv6 address
    shield_console.apply_decisions(FakeShield())
    assert "NOT APPLIED" in tg.texts[-1] and "IPv6" in tg.texts[-1], tg.texts[-1]
    assert not (_holds() or {}).get("holds")


def test_false_alarm_releases_this_projects_holds_and_says_until_when(console):
    tg = console
    incident = _announce(tg)
    _decide(incident, "fhold24", chat=OPERATOR_CHAT)
    shield_console.apply_decisions(FakeShield())
    assert len(_holds()["holds"]) == 1

    incident2 = _announce(tg, now=time.time() + shield_console.ASK_TTL_S + 60)
    assert incident2 is None, "a held source must not produce a second ask"
    _decide(incident, "frelease", chat=OPERATOR_CHAT)
    # the ask was consumed by the first apply; re-register it the way the console would
    shield_console._write(shield_console.PENDING, {incident: {
        "kind": "fleet", "ip": IP, "service": SVC, "name": NAME, "ts": time.time(),
        "paths": PROBES}})
    shield_console.apply_decisions(FakeShield())
    assert not _holds()["holds"], "False alarm did not release the hold"
    assert "released" in tg.texts[-1] and IP in tg.texts[-1], tg.texts[-1]
    assert "until" in tg.texts[-1] and "UTC" in tg.texts[-1], tg.texts[-1]


def test_a_star_hold_is_never_released_by_one_projects_false_alarm(console):
    now = time.time()
    shield_console._write_holds([{"cidr": "%s/32" % IP, "service": "*", "until": int(now + 600)}],
                                now)
    removed, remaining = shield_console.release_holds(IP, SVC, now)
    assert removed == 0 and remaining == 1, (
        "one project's dismissal must not unblock the address on the other four")


# ------------------------------------------------------------------ edge-triggering
def test_a_source_already_held_does_not_re_alert(console):
    """The operator used to get the same SCANNER line every five minutes for as long as the scan
    lasted. Prove the fixture can fire before proving it is suppressed."""
    tg = console
    now = time.time()
    assert _announce(tg, now=now) is not None, "the control case must alert"
    shield_console._write(shield_console.PENDING, {})       # clear the open ask

    shield_console._write_holds([{"cidr": "%s/32" % IP, "service": SVC, "until": int(now + 3600)}],
                                now)
    before = len(tg.sent)
    assert _announce(tg, now=now + 300) is None
    assert _announce(tg, now=now + 600) is None
    assert len(tg.sent) == before, "a held source paged the operator again"
    assert _evts(tg, "fleet_ask_suppressed"), "the suppression must be observable"
    assert "already held" in _evts(tg, "fleet_ask_suppressed")[0]["reason"]


def test_a_hold_on_another_project_does_not_suppress_this_one(console):
    """A hold is scoped to one project; so is the silence it buys."""
    tg = console
    now = time.time()
    shield_console._write_holds([{"cidr": "%s/32" % IP, "service": "jev-web",
                                  "until": int(now + 3600)}], now)
    assert _announce(tg, now=now) is not None, "klima's hold silenced jobhuntwow's alert"


def test_an_unanswered_menu_is_not_sent_twice(console):
    tg = console
    now = time.time()
    assert _announce(tg, now=now) is not None
    assert _announce(tg, now=now + 300) is None, "a second identical menu is noise"
    assert _announce(tg, now=now + shield_console.ASK_TTL_S + 60) is not None, (
        "once the ask has EXPIRED unanswered the operator must be told again")


def test_a_dismissed_source_stays_quiet_for_the_stated_window(console):
    tg = console
    now = time.time()
    shield_console._fleet_muted[(SVC, IP)] = now + 3600
    assert _announce(tg, now=now) is None
    assert _announce(tg, now=now + 3700) is not None, "the mute must lapse, not latch"


def test_watch_still_pages_through_the_console_end_to_end(tmp_path, monkeypatch, console):
    """FOLLOW THE VALUE END TO END. fleet.watch -> shield_console.announce_fleet -> the transport,
    with the menu attached, is the whole point of the change."""
    tg = console
    now = int(time.time())
    rows = [{"ts": now - 5, "evt": "http", "service": SVC, "ip": IP, "path": p} for p in PROBES]
    ev = tmp_path / "ev.log"
    ev.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(fleet, "EVENTS", str(ev))
    monkeypatch.setattr(fleet, "BEAT_DIR", str(tmp_path / "beats"))
    fleet._LOKI_EVENTS.update(ts=0.0, rows=[], ok=False, partial=False, busy=False)

    fleet.watch(0, tg)
    assert tg.menus, "the sibling alert arrived with no buttons at all"
    assert "SCANNER on %s" % NAME in tg.texts[0] and IP in tg.texts[0]


def test_a_transport_without_buttons_gets_exactly_the_old_line(console):
    """A message that describes a menu it is not showing is worse than the flat line it replaced,
    and the branch is chosen by READING the signature rather than by catching a TypeError."""
    plain = []
    assert shield_console._accepts_markup(plain.append) is False
    assert shield_console._accepts_markup(notify.telegram) is True
    assert shield_console.announce_fleet(NAME, SVC, IP, PROBES, send=plain.append) is None
    assert plain == [shield_console.fleet_text(NAME, IP, sorted(PROBES))]
    assert not os.path.exists(shield_console.PENDING), (
        "an ask nobody can answer must not be registered: it would suppress the next real alert")


# ------------------------------------------------------------------ the law
def test_no_menu_entry_offers_any_form_of_connecting_back(console):
    """ASSERTED AGAINST THE ACTION TABLE, NOT AGAINST PROSE. Every entry must resolve to one of a
    CLOSED set of deliverable effects, none of which emits a packet toward the source:
    a hold in a file the target's own sidecar reads, a complaint to the address's provider, or the
    removal of a hold. StGB s.202a/202b/202c criminalises even preparing the alternative."""
    deliverable = {"ip", "net", "abuse", "release"}
    for key, spec in shield_console.FLEET_ACTIONS.items():
        assert spec["hold"][0] in deliverable, (key, spec)
    banned = ("scan", "probe", "connect", "counter", "hack", "retaliat", "strike", "exploit",
              "shell", "payload", "nmap")
    for key, spec in shield_console.FLEET_ACTIONS.items():
        blob = ("%s %s" % (spec["label"], spec["what"])).lower()
        for word in banned:
            assert word not in blob, "%s reads like a counter-attack: %r" % (key, blob)


def test_the_alert_keeps_saying_why_counter_attack_is_not_offered(console):
    tg = console
    _announce(tg)
    msg = tg.texts[0]
    assert "Counter-attack is not on this menu" in msg
    assert "criminal offence" in msg
    assert "compromised third party" in msg


def test_the_menu_is_deliverable_and_fits_the_api(console):
    """A button that does nothing is worse than no button, and a callback_data over 64 bytes is a
    button Telegram silently drops. DERIVE the count from the table."""
    tg = console
    _announce(tg)
    kb = tg.menus[0]["inline_keyboard"]
    keys = [b["callback_data"].split(":")[-1] for row in kb for b in row]
    assert sorted(keys) == sorted(shield_console.FLEET_ACTIONS), keys
    for row in kb:
        for b in row:
            assert len(b["callback_data"].encode("utf-8")) <= 64, b
    assert "strict" not in keys and "deny" not in keys, (
        "cybergod's in-process shield actions cannot be honoured for a sibling and must not appear")


def test_the_sibling_alert_never_claims_something_already_happened(console):
    """cybergod's message opens with 'ALREADY DONE, automatically'. Nothing is done automatically on
    a sibling -- colt-web has no code in its request path -- and saying otherwise would be the
    templated-output defect pointed at the operator."""
    tg = console
    _announce(tg)
    assert "NOTHING has been done automatically" in tg.texts[0]
    assert "ALREADY DONE" not in tg.texts[0]
