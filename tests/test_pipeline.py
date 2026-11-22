"""test_pipeline.py — the channel-sales board: stages, the matcher, the sweep, and the routes.

THE STAGES ARE NOT MINE TO INVENT, and that is the first thing asserted here. They are verbatim
from `Herkos_Commercial_Process_Map_v0.1_DRAFT.docx` (HRK-COM-PRC-001, Assad Kondakji, 2 Oct 2026),
which is the document Dima named in the 20 Nov call: "that's the process map that Assad proposed -
I think we should organize it according to the stages." A board whose columns drift from that
document is a board that disagrees with the process everybody else is following.

The map has THREE TRACKS, not one funnel. A partner at R6 runs its own customers through H0-H9, so
`poc` means different things on different tracks and `mpa` exists on only one. Every test below
that touches a stage touches it beside a track, because that is the only way a stage is meaningful.
"""
import importlib
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
BACKEND = os.path.join(ROOT, "webapp", "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


@pytest.fixture()
def P(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "p.sqlite"))
    from app import pipeline
    importlib.reload(pipeline)
    yield pipeline
    monkeypatch.undo()
    importlib.reload(pipeline)


# ---------------------------------------------------------------------------------------------
# 1. THE STAGES, AGAINST THE DOCUMENT
# ---------------------------------------------------------------------------------------------
def test_the_partner_track_is_the_process_map_r1_to_r6(P):
    """These six are what the operator asked for - Introduction, Demo, NDA, Master Partner
    Agreement, POC/POV - and they are the map's own R1-R6, in its order."""
    got = [(s["code"], s["label"]) for s in P.stage_meta("partner") if s["code"] != "--"]
    assert got == [
        ("R1", "Intro + partner pitch"),
        ("R2", "NDA"),
        ("R3", "Partner PoC + Perseus demo"),
        ("R4", "LOI"),
        ("R5", "MPA + onboarding"),
        ("R6", "Co-selling"),
    ], got


def test_every_track_is_complete_and_ordered(P):
    """H0-H9 and P0-P10 are the customer tracks. A missing stage is a gate nobody can record
    passing, and the deal sits in the previous column looking stalled."""
    h = [s["code"] for s in P.stage_meta("herkos") if s["code"] != "--"]
    pp = [s["code"] for s in P.stage_meta("perseus") if s["code"] != "--"]
    assert h == ["H%d" % i for i in range(10)], h
    assert pp == ["P%d" % i for i in range(11)], pp


def test_every_stage_carries_its_gate_and_its_exit(P):
    """A stage that is only a noun is a stage two people fill in differently, and then the
    forecast is fiction. The map gives each one a test; the board shows it."""
    for track in ("partner", "herkos", "perseus"):
        for s in P.stage_meta(track):
            assert s["gate"], "%s/%s has no entry gate" % (track, s["key"])
            assert s["exit"], "%s/%s has no exit criterion" % (track, s["key"])


def test_a_stage_is_only_meaningful_beside_its_track(P):
    assert P.canon_stage("mpa", "partner") == "mpa"
    assert P.canon_stage("mpa", "perseus") == "", (
        "a partner stage was accepted on a Perseus deal - the card would land in a column that "
        "track does not render and would simply vanish")
    assert P.canon_stage("readiness", "perseus") == "readiness"
    assert P.canon_stage("readiness", "partner") == ""


def test_the_maps_own_codes_are_accepted_as_input(P):
    """Somebody reading the document will type R5. Refusing it would teach them the board
    disagrees with the document."""
    assert P.canon_stage("R5", "partner") == "mpa"
    assert P.canon_stage("h4", "herkos") == "poc"
    assert P.canon_stage("P10", "perseus") == "expand"


def test_a_renamed_stage_keeps_working(P):
    """jobhuntwow learned this when a rename made every card in the old column invisible: the row
    still said `submitted` and nothing matched it any more."""
    assert P.canon_stage("Master Partner Agreement", "partner") == "mpa"
    assert P.canon_stage("POV", "partner") == "poc"
    assert P.canon_stage("introduction", "partner") == "intro"
    assert P.canon_stage("wizard", "partner") == ""


# ---------------------------------------------------------------------------------------------
# 2. THE BOARD
# ---------------------------------------------------------------------------------------------
def test_a_new_deal_lands_in_its_tracks_first_stage(P):
    d = P.create("Paratus", owner="jev@s4biz.io", country="NA")
    assert d["track"] == "partner" and d["stage"] == "intro"
    h = P.create("Standard Bank", track="herkos")
    assert h["stage"] == "contact", "the first stage is hardcoded rather than derived"


def test_a_nameless_deal_is_refused(P):
    assert P.create("   ") is None, "a deal nobody can name cannot be matched or found again"


def test_moving_a_card_is_recorded_as_history(P):
    """A board that only holds the current column cannot answer 'how long did the NDA take',
    which is the one question a channel pipeline exists to answer."""
    d = P.create("Projectale")
    P.set_stage(d["deal_id"], "nda", by="jev")
    P.set_stage(d["deal_id"], "mpa", by="jev")
    bodies = [n["body"] for n in P.notes_for(d["deal_id"])]
    assert "intro -> nda" in bodies and "nda -> mpa" in bodies, bodies


def test_a_stage_from_another_track_is_refused_with_a_reason(P):
    d = P.create("Projectale")
    ok, detail = P.set_stage(d["deal_id"], "readiness")
    assert not ok and "partner track" in detail, detail


def test_changing_track_re_homes_the_card(P):
    """The stages differ between tracks, so a deal moved while sitting in `mpa` would land in a
    column the new board does not have and disappear."""
    d = P.create("Projectale")
    P.set_stage(d["deal_id"], "mpa")
    assert P.set_fields(d["deal_id"], track="perseus")
    now = P.get(d["deal_id"])
    assert now["track"] == "perseus" and now["stage"] == "contact", now


def test_counts_show_every_column_even_at_zero(P):
    P.create("Paratus")
    c = P.counts("partner")
    assert set(c) == set(P.stage_keys("partner"))
    assert c["intro"] == 1 and c["mpa"] == 0, c


# ---------------------------------------------------------------------------------------------
# 3. THE MATCHER AND THE SWEEP
# ---------------------------------------------------------------------------------------------
def _msg(mid, frm, subject, ts, snippet=""):
    return {"id": mid, "internalDate": str(int(ts * 1000)), "snippet": snippet,
            "payload": {"headers": [{"name": "From", "value": frm},
                                    {"name": "Subject", "value": subject}]}}


def _fetcher(msgs):
    def fake(url, headers=None, params=None, timeout=20):
        if url.endswith("/messages"):
            return 200, {"messages": [{"id": m["id"]} for m in msgs]}
        for m in msgs:
            if url.endswith("/" + m["id"]):
                return 200, m
        return 404, {}
    return fake


def test_a_partners_reply_is_filed_and_a_newsletter_is_not(P, monkeypatch):
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")
    now = time.time()
    d = P.create("Projectale", domain="objectale.ch", contact="ud@objectale.ch",
                 title="Swiss distribution agreement")
    msgs = [_msg("m1", "Urs <ud@objectale.ch>", "Re: Swiss distribution agreement", now),
            _msg("m2", "news@telecomreview.africa", "Projectale in the news", now)]
    out = P.sweep(fetch=_fetcher(msgs))
    assert out["filed"] == 1 and out["unfiled"] == 1, out

    on_card = P.mails_for(d["deal_id"])
    assert len(on_card) == 1 and on_card[0]["msg_id"] == "m1"
    assert on_card[0]["evidence"], "the card cannot show WHY it was filed here"
    assert on_card[0]["kind"] == "agreement", on_card[0]["kind"]

    # THE UNFILED QUEUE IS THE POINT. A message that matched nothing is kept WITH ITS REASON:
    # dropping it would make the same message look like new activity on the next sweep.
    un = P.unfiled_mail()
    assert len(un) == 1 and un[0]["msg_id"] == "m2"
    assert any("unfiled:" in e for e in un[0]["evidence"]), un[0]["evidence"]


def test_the_sweep_is_re_runnable(P, monkeypatch):
    """It reads a WINDOW, not a cursor, and msg_id is the primary key - so a crash halfway costs
    nothing and a second run files nothing twice."""
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")
    now = time.time()
    P.create("Projectale", domain="objectale.ch")
    msgs = [_msg("m1", "ud@objectale.ch", "Projectale next steps", now)]
    first = P.sweep(fetch=_fetcher(msgs))
    second = P.sweep(fetch=_fetcher(msgs))
    assert first["read"] == second["read"] == 1
    assert second["filed"] == 0 and second["already_seen"] == 1, second


def test_a_label_never_moves_a_card(P, monkeypatch):
    """THE GATES ARE SIGNATURE EVENTS. An email that says "NDA" is not an NDA that was signed; a
    board that advanced itself on vocabulary would be fiction within a week."""
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")
    now = time.time()
    d = P.create("Projectale", domain="objectale.ch")
    was = P.get(d["deal_id"])["stage"]
    P.sweep(fetch=_fetcher([_msg("m1", "ud@objectale.ch", "Mutual NDA signed and countersigned",
                                 now)]))
    assert P.get(d["deal_id"])["stage"] == was, "a message moved the card on its own"
    assert P.mails_for(d["deal_id"])[0]["kind"] == "nda", "the label was not recorded either"


def test_a_closed_deal_is_not_considered_by_the_matcher(P, monkeypatch):
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")
    now = time.time()
    d = P.create("Projectale", domain="objectale.ch")
    P.set_stage(d["deal_id"], "lost")
    out = P.sweep(fetch=_fetcher([_msg("m1", "ud@objectale.ch", "Projectale", now)]))
    assert out["deals_considered"] == 0, "a lost deal still attracts mail"


def test_the_operator_can_overrule_the_matcher(P, monkeypatch):
    """The matcher is a SIGNAL; the person decides. An automatic link nobody can undo is worse
    than no link at all."""
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")
    now = time.time()
    d = P.create("Paratus")
    P.sweep(fetch=_fetcher([_msg("m9", "someone@example.org", "hello", now)]))
    assert P.unfiled_mail()[0]["msg_id"] == "m9"
    assert P.file_mail("m9", d["deal_id"], by="jev")
    assert [m["msg_id"] for m in P.mails_for(d["deal_id"])] == ["m9"]


def test_deleting_a_deal_unfiles_its_mail_rather_than_dropping_it(P, monkeypatch):
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")
    now = time.time()
    d = P.create("Projectale", domain="objectale.ch")
    P.sweep(fetch=_fetcher([_msg("m1", "ud@objectale.ch", "Projectale", now)]))
    assert P.delete(d["deal_id"])
    assert [m["msg_id"] for m in P.unfiled_mail()] == ["m1"], (
        "the message was dropped, so the next sweep will file it again as new activity")


def test_a_mail_fault_never_touches_the_board(P, monkeypatch):
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")

    def boom(url, headers=None, params=None, timeout=20):
        raise RuntimeError("socket")

    P.create("Paratus")
    out = P.sweep(fetch=boom)
    assert out["read"] == 0 and out["filed"] == 0
    assert any("could not be listed" in n for n in out["notes"]), out["notes"]
    assert len(P.rows()) == 1, "the board changed because the mailbox did not answer"


# ---------------------------------------------------------------------------------------------
# 4. THE ROUTES, THROUGH THE REAL REQUEST PATH.
#    The greps prove a gate is written; only a request proves it is REACHED (class 9).
# ---------------------------------------------------------------------------------------------
def _request(path, method="GET", email=None, body=None):
    import asyncio
    sys.path.insert(0, BACKEND)
    from app import main
    from app.auth import make_session

    raw = json.dumps(body or {}).encode()
    headers = [(b"host", b"testserver"), (b"content-type", b"application/json")]
    if email:
        headers.append((b"cookie", ("colt_session=" + make_session(email)).encode()))
    p, _, q = path.partition("?")
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
             "scheme": "http", "path": p, "raw_path": p.encode(), "query_string": q.encode(),
             "root_path": "", "headers": headers,
             "client": ("127.0.0.1", 1), "server": ("testserver", 80)}
    got = {"status": 0, "body": b""}

    async def receive():
        return {"type": "http.request", "body": raw, "more_body": False}

    async def send(msg):
        if msg.get("type") == "http.response.start":
            got["status"] = msg["status"]
        elif msg.get("type") == "http.response.body":
            got["body"] += msg.get("body") or b""

    asyncio.run(main.app(scope, receive, send))
    try:
        got["json"] = json.loads(got["body"] or b"{}")
    except Exception:
        got["json"] = {}
    return got


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "p.sqlite"))
    monkeypatch.setenv("USER_DB", str(tmp_path / "u.sqlite"))
    import user_store
    importlib.reload(user_store)
    from app import pipeline
    importlib.reload(pipeline)
    sys.path.insert(0, BACKEND)
    from app import main
    monkeypatch.setattr(main, "user_store", user_store, raising=False)
    monkeypatch.setattr(main, "_pipeline", pipeline, raising=False)
    yield pipeline, user_store
    monkeypatch.undo()
    importlib.reload(user_store)
    importlib.reload(pipeline)


def test_an_anonymous_caller_is_refused_by_every_pipeline_route(api):
    for path, method in (("/api/pipeline", "GET"), ("/api/pipeline", "POST"),
                         ("/api/pipeline/x", "GET"), ("/api/pipeline/x", "PATCH"),
                         ("/api/pipeline/x", "DELETE"), ("/api/pipeline/sweep", "POST")):
        r = _request(path, method, email=None, body={"company": "x"})
        assert r["status"] in (401, 403), "%s %s leaked (%d)" % (method, path, r["status"])


def test_a_plain_user_cannot_open_the_board(api):
    """"just for users that are part of S4biz" is a PERMISSION, not a domain check: a `user` does
    not hold pipeline.view, so the board refuses even though the address is on s4biz.io."""
    r = _request("/api/pipeline", "GET", email="nobody.special@s4biz.io")
    assert r["status"] == 403, r["json"]


def test_a_sales_rep_can_open_it_and_move_a_card(api):
    """The mirror image: a gate that refuses everybody is not a gate either."""
    _pipeline, us = api
    us.set_role("rep@s4biz.io", "sales_rep")
    board = _request("/api/pipeline", "GET", email="rep@s4biz.io")
    assert board["status"] == 200, board["json"]
    assert board["json"]["track"] == "partner"
    assert [s["code"] for s in board["json"]["stages"]][:2] == ["R1", "R2"]

    made = _request("/api/pipeline", "POST", email="rep@s4biz.io", body={"company": "Paratus"})
    assert made["status"] == 200, made["json"]
    did = made["json"]["deal_id"]

    moved = _request("/api/pipeline/" + did, "PATCH", email="rep@s4biz.io", body={"stage": "nda"})
    assert moved["status"] == 200 and moved["json"]["stage"] == "nda", moved["json"]


def test_a_refused_move_answers_with_the_reason(api):
    """The board moves the card optimistically and puts it back on a refusal; a bare 400 would
    leave the operator watching a card jump with no explanation."""
    _pipeline, us = api
    us.set_role("rep@s4biz.io", "sales_rep")
    made = _request("/api/pipeline", "POST", email="rep@s4biz.io", body={"company": "Paratus"})
    r = _request("/api/pipeline/" + made["json"]["deal_id"], "PATCH", email="rep@s4biz.io",
                 body={"stage": "readiness"})
    assert r["status"] == 400 and "partner track" in r["json"].get("detail", ""), r["json"]


def test_sweeping_the_mailboxes_needs_more_than_pipeline_edit(api):
    """Reading somebody's mailbox is a different act from moving a card, so it is a different
    verb: pipeline.admin, which a sales rep does not hold."""
    _pipeline, us = api
    us.set_role("rep@s4biz.io", "sales_rep")
    assert _request("/api/pipeline/sweep", "POST", email="rep@s4biz.io")["status"] == 403
    us.set_role("boss@s4biz.io", "s4biz_power")
    assert _request("/api/pipeline/sweep", "POST", email="boss@s4biz.io")["status"] == 200


def test_the_board_says_when_the_mail_reader_is_off(api):
    """A feature guarded by `if configured():` fails silently by construction (class 37). The
    screen says it is off and what is missing, rather than looking like a board nobody writes to.
    """
    _pipeline, us = api
    us.set_role("rep@s4biz.io", "sales_rep")
    b = _request("/api/pipeline", "GET", email="rep@s4biz.io")["json"]
    assert "mail" in b and b["mail"].get("note"), b.get("mail")
    assert "gmail.readonly" in b["mail"]["note"], (
        "the note does not name the console step a domain admin has to take")


def test_the_cabinet_gates_the_board_on_the_verb_not_a_domain():
    """BEHAVIOUR AND WIRING (class 9). The route and the nav item must both ask for the verb;
    an email-domain check in the frontend would be a second authorisation model with no server
    behind it."""
    import io as _io
    cab = _io.open(os.path.join(ROOT, "webapp", "frontend", "src", "pages", "Cabinet.jsx"),
                   encoding="utf-8").read()
    side = _io.open(os.path.join(ROOT, "webapp", "frontend", "src", "components", "Sidebar.jsx"),
                    encoding="utf-8").read()
    assert 'includes("pipeline.view")' in cab, "the route is not gated on the permission"
    assert 'includes("pipeline.view")' in side, "the nav item is not gated on the permission"
    for wrong in ("s4biz.io", "@colt.net", "endsWith("):
        assert wrong not in cab.split("pipeline")[1][:400], (
            "the cabinet gates the board on a domain rather than a verb: %r" % wrong)


def test_two_deals_that_match_equally_well_leave_the_mail_UNFILED(P, monkeypatch):
    """THE REFUSAL IS THE FEATURE, and it was the one property the mutation sweep could reach but
    this file could not: deleting the tie branch left all 26 tests green, because the only thing
    asserting it was dealmatch's own self-test, which pytest never ran.

    Filing Paratus's pricing question under the wrong Paratus deal is worse than leaving it in the
    queue: the board starts lying quietly, in the one artefact two people use to agree what is
    happening."""
    monkeypatch.setenv("PIPELINE_MAILBOXES", "dima@s4biz.io")
    now = time.time()
    # Two deals with the SAME company and domain - two regions, two products, which is legitimate
    # and is exactly when a human cannot tell either, let alone a score.
    a = P.create("Paratus", domain="paratus.africa", title="Namibia")
    b = P.create("Paratus", domain="paratus.africa", title="Botswana")
    assert a["deal_id"] != b["deal_id"]
    out = P.sweep(fetch=_fetcher([_msg("m1", "sales@paratus.africa", "Paratus - pricing", now)]))
    assert out["filed"] == 0 and out["unfiled"] == 1, out
    assert not P.mails_for(a["deal_id"]) and not P.mails_for(b["deal_id"])
    why = " ".join(P.unfiled_mail()[0]["evidence"])
    assert "equally well" in why, why


# ---------------------------------------------------------------------------------------------
# 5. THE MODULES' OWN SELF-TESTS, RUN BY THE SUITE.
#    They were written with the modules and they are thorough - and until this ran them, a `python
#    -m app.dealmatch` nobody executes is a check that cannot fail (class 3). ship.py runs them too,
#    so they are reached on both machines.
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("mod", ["app.dealmatch", "app.gmail_read"])
def test_the_module_selftests_pass(mod, capsys):
    m = importlib.import_module(mod)
    assert m._selftest() == 0, capsys.readouterr().out
