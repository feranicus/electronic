"""pipeline.py — the CHANNEL SALES board. Deals, stages, notes, and the mail filed against them.

    python -m app.pipeline            print the stage list and the schema, so it can be read

WHAT THIS IS, AND WHAT IT IS NOT
    It is the Pipedrive-shaped board the operator asked for, for CHANNEL sales: Projectale,
    New Cognito, Paratus - distributors and resellers, not end customers. A deal here is a
    PARTNERSHIP moving from a first conversation to a signed agreement and a first customer.

    It is not the jobhuntwow tracker with the words changed. That module is 1,235 lines and more
    than half of it is job-application domain - jd_fingerprint, ats_of, record_tailored, resume
    files, employer derivation from a posting URL. Copying it wholesale would import a domain model
    that does not fit and would rot in place, which is how a "reused" module becomes two modules
    nobody dares touch. What IS reused is the part that was hard to get right and is domain-free:
    the stage machinery with its legacy remap, notes, the mail-filing tables, and above all the
    deterministic matcher, which moved to dealmatch.py with the nouns changed and its self-test
    intact.

THE STAGES ARE ONE HOME
    STAGES_BY_TRACK below is the only list. The API serves it, the board renders what it served, and
    `canon_stage()` is the only thing that decides whether a value is a stage. A second copy in the
    frontend would drift the first time a stage is added, and the drift shows up as a column that
    silently drops its cards. CLAUDE.md: never translate an enum key - the LABEL is renamed at
    render time, the key travels on the wire.

WHERE IT LIVES
    `DATA_DIR/colt.sqlite`, the same database as the assessment history, because colt-web is the
    only writer and a second file is a second thing to back up. dbbackup.py already carries it.
"""
import json
import os
import re
import sqlite3
import sys
import threading
import time

from .settings import DATA_DIR

_LOCK = threading.Lock()


def db_path():
    return os.environ.get("PIPELINE_DB") or os.path.join(str(DATA_DIR), "colt.sqlite")


# ---------------------------------------------------------------------------------------------
# THE SALES LIFE CYCLE, TAKEN FROM THE PROCESS MAP RATHER THAN INVENTED.
#
# The operator asked for a channel-sales board "aligned in general with our Sales Life Cycle", and
# in the 20 Nov call Dima named the source: "that's the process map that Assad proposed - I think
# we should organize it according to the stages." That document is
# `Herkos_Commercial_Process_Map_v0.1_DRAFT.docx` (HRK-COM-PRC-001, 2 Oct 2026, Assad Kondakji),
# and the stage names, gates and exit criteria below are VERBATIM from it.
#
# THE MAP HAS THREE TRACKS, NOT ONE FUNNEL, and that is the part a flat column list would have
# destroyed: a partner at R6 "runs H0-H9 / P0-P10 with its own customers at its own prices", so
# the partner track and the customer tracks are different processes that happen to share a board.
# Collapsing them would have put "Pilot readiness" next to "MPA + onboarding" as if a deal could
# move between them. The board shows ONE track at a time.
#
# PARTNER is the default, because channel sales is what was asked for: Projectale, New Cognito,
# Paratus. The two customer tracks are here because direct prospects exist (Standard Bank was
# discussed in the same call) and because a partner's own deals run on them.
#
# EACH STAGE CARRIES ITS GATE AND ITS EXIT. That is what makes this a process map rather than a
# list of nouns: a column whose cards sit there for a month is answered by "the exit criterion was
# never met", and two people filling the board in differently is what happens when a stage is a
# word instead of a test. The text is the document's, trimmed to what fits a card.
# ---------------------------------------------------------------------------------------------
TRACKS = [
    ("partner", "Partner / channel", "resellers, MSSPs and integrators"),
    ("herkos", "Herkos (ASM)", "direct customer, attack-surface management"),
    ("perseus", "Perseus (AI SOC)", "direct customer, the AI SOC"),
]
DEFAULT_TRACK = TRACKS[0][0]

# (key, code, label, gate to enter, exit criterion)
STAGES_BY_TRACK = {
    "partner": [
        ("intro", "R1", "Intro + partner pitch", "none",
         "interest in a model: referral, resale, white-label or infrastructure"),
        ("nda", "R2", "NDA", "NDA signed", "agrees to evaluate"),
        ("poc", "R3", "Partner PoC + Perseus demo", "PoC Agreement signed", "PoC report signed"),
        ("loi", "R4", "LOI", "PoC says proceed", "LOI signed"),
        ("mpa", "R5", "MPA + onboarding", "MPA, Schedules 1-2, DPA signed",
         "first deal registered; at least 2 trained first-line contacts"),
        ("coselling", "R6", "Co-selling", "active",
         "runs its own customers at its own prices; tier reviewed quarterly"),
    ],
    "herkos": [
        ("contact", "H0", "First contact", "none", "prospect accepts a discovery meeting"),
        ("discovery", "H1", "Discovery meeting + demo", "none (no NDA)",
         "named sponsor, use case and timeline"),
        ("qualification", "H2", "Qualification + deal registration", "qualified at H1",
         "NDA signed by both parties"),
        ("evaluation", "H3", "Technical evaluation", "NDA signed",
         "success criteria agreed (PoC Schedule 2)"),
        ("poc", "H4", "Proof of Concept (free)", "PoC Agreement signed, Schedules 1-2 filled",
         "PoC report signed: proceed / extend / close"),
        ("loi", "H5", "Letter of Intent", "PoC report says proceed", "LOI countersigned"),
        ("pilot", "H6", "Pilot (paid, customer-facing)", "LOI + Pilot Agreement + DPA signed",
         "pilot success criteria met"),
        ("contract", "H7", "Contract", "pilot criteria met", "signed by both parties"),
        ("payment", "H8", "Invoice + payment", "contract signed",
         "payment received; seats fully provisioned"),
        ("delivery", "H9", "Delivery + expansion", "paid", "renewal or upsell"),
    ],
    "perseus": [
        ("contact", "P0", "First contact", "none", "prospect accepts a discovery meeting"),
        ("discovery", "P1", "Discovery + live demo", "none (no NDA)",
         "technical fit plausible; sponsor and CISO identified"),
        ("qualification", "P2", "Qualification + deal registration", "fit at P1", "NDA signed"),
        ("review", "P3", "Technical + security review", "NDA signed",
         "CISO agrees to detection-only install; pilot apps named"),
        ("readiness", "P4", "Pilot readiness", "CISO approval", "Pilot Agreement + DPA signed"),
        ("pilot", "P5", "Free 30-day pilot (detection only)", "P4 signed",
         "pilot report: attack volume, classes to enforce, chosen tier"),
        ("proposal", "P6", "Proposal (+ LOI if wanted)", "pilot report reviewed", "quote accepted"),
        ("contract", "P7", "Contract", "quote accepted", "signed by both parties"),
        ("payment", "P8", "Invoice + payment", "contract signed", "onboarding fee paid"),
        ("golive", "P9", "Onboarding + enforcement go-live", "fee paid",
         "enforcement live for the agreed classes"),
        ("expand", "P10", "Run, review, expand", "live", "renewal or upsell"),
    ],
}

# LOST IS NOT IN THE PROCESS MAP, and it has to be on the board: a deal that ends has to go
# somewhere or it sits in its last stage forever and the forecast counts it. It is a per-track
# terminal column rather than a stage of the process, which is why it is defined here and not
# above - the map describes how a deal PROGRESSES, not how it stops.
LOST = ("lost", "--", "Lost", "ended", "the reason belongs in a note")
CLOSED = {"lost"}


def tracks():
    return [{"key": k, "label": lab, "about": a} for k, lab, a in TRACKS]


def canon_track(track):
    t = str(track or "").strip().lower()
    return t if t in STAGES_BY_TRACK else ""


def stages_for(track):
    """Every column of one track, in order, LOST last. ONE HOME; the API serves this and the
    board renders what it served."""
    t = canon_track(track) or DEFAULT_TRACK
    return list(STAGES_BY_TRACK[t]) + [LOST]


def stage_keys(track):
    return tuple(k for k, _c, _l, _g, _x in stages_for(track))


def first_stage(track):
    """Where a new deal lands. DERIVED from the map's own first row, never typed twice."""
    return stages_for(track)[0][0]


def stage_meta(track):
    return [{"key": k, "code": c, "label": lab, "gate": g, "exit": x, "closed": k in CLOSED}
            for k, c, lab, g, x in stages_for(track)]


# A stage that was renamed keeps working, and the process map's own CODES are accepted as input:
# somebody reading the document will type R5, and refusing it would teach them the board disagrees
# with the document. jobhuntwow learned the rename half of this when a renamed stage made every
# card in the old column invisible - the row still said `submitted` and nothing matched it.
LEGACY_STAGES = {
    "introduction": "intro", "first_contact": "contact", "new": "intro",
    "demo": "discovery", "demo_stage": "discovery", "presentation": "discovery",
    "master_partner_agreement": "mpa", "agreement": "mpa",
    "pov": "poc", "poc_pov": "poc", "proof_of_concept": "poc",
    "won": "coselling", "signed": "mpa", "active": "coselling", "partner": "coselling",
    "closed_lost": "lost", "dead": "lost",
}


def canon_stage(stage, track=None):
    """The stage this value MEANS within this track, or '' if it means nothing here.

    TRACK-AWARE ON PURPOSE. `poc` is a stage of all three tracks and `mpa` of only one, so a
    stage name is only meaningful beside its track: accepting `mpa` on a Perseus deal would put a
    card in a column that track does not render, and it would vanish from the board.
    """
    v = str(stage or "").strip().lower().replace(" ", "_").replace("-", "_")
    keys = stage_keys(track)
    if v in keys:
        return v
    by_code = {c.lower(): k for k, c, _l, _g, _x in stages_for(track)}
    if v in by_code:
        return by_code[v]
    mapped = LEGACY_STAGES.get(v, "")
    return mapped if mapped in keys else ""


def _log(**k):
    try:
        from .telemetry import log_event
        log_event(**k)
    except Exception:
        # PRINT ONCE RATHER THAN SWALLOW (class 38). An observability write that fails silently is
        # a blind spot you only discover when you need the line that was never written.
        try:
            print(json.dumps(dict(k, evt_fallback="pipeline")), flush=True)
        except Exception:
            pass


def _conn():
    p = db_path()
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(p, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS deals (
                     deal_id    TEXT PRIMARY KEY,
                     company    TEXT NOT NULL,
                     track      TEXT NOT NULL DEFAULT 'partner',
                     country    TEXT NOT NULL DEFAULT '',
                     domain     TEXT NOT NULL DEFAULT '',
                     contact    TEXT NOT NULL DEFAULT '',
                     title      TEXT NOT NULL DEFAULT '',
                     stage      TEXT NOT NULL,
                     owner      TEXT NOT NULL DEFAULT '',
                     created_ts REAL,
                     updated_ts REAL,
                     note       TEXT NOT NULL DEFAULT ''
                 )""")
    c.execute("""CREATE TABLE IF NOT EXISTS deal_notes (
                     note_id  TEXT PRIMARY KEY,
                     deal_id  TEXT NOT NULL,
                     body     TEXT NOT NULL,
                     kind     TEXT NOT NULL DEFAULT 'note',
                     author   TEXT NOT NULL DEFAULT '',
                     ts       REAL
                 )""")
    # FILED MAIL. `msg_id` is the primary key so the same message can never be filed twice, which
    # is what makes the reader safe to re-run: it reads a window, not a cursor, and a crash in the
    # middle costs nothing. `deal_id` is '' for a message that matched nothing - kept, not dropped,
    # because "we saw it and could not place it" is the queue the operator actually works.
    c.execute("""CREATE TABLE IF NOT EXISTS deal_mail (
                     msg_id   TEXT PRIMARY KEY,
                     deal_id  TEXT NOT NULL DEFAULT '',
                     mailbox  TEXT NOT NULL DEFAULT '',
                     sender   TEXT NOT NULL DEFAULT '',
                     subject  TEXT NOT NULL DEFAULT '',
                     snippet  TEXT NOT NULL DEFAULT '',
                     kind     TEXT NOT NULL DEFAULT 'mail',
                     score    INTEGER NOT NULL DEFAULT 0,
                     evidence TEXT NOT NULL DEFAULT '[]',
                     ts       REAL
                 )""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_notes_deal ON deal_notes(deal_id)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_mail_deal ON deal_mail(deal_id)")
    c.commit()
    return c


def available():
    try:
        _conn().close()
        return True
    except Exception:
        return False


def _now():
    return time.time()


def _mkid(company):
    slug = re.sub(r"[^a-z0-9]+", "-", str(company or "").lower()).strip("-")[:28] or "deal"
    return "%s-%s" % (time.strftime("%Y%m%d"), slug)


def create(company, owner="", **f):
    """A new deal, in the first stage. Returns the row, or None when the company is empty - a
    nameless deal cannot be matched to anything and cannot be found again."""
    name = str(company or "").strip()
    if not name:
        return None
    did = _mkid(name)
    now = _now()
    c = _conn()
    try:
        # A SECOND DEAL FOR THE SAME COMPANY ON THE SAME DAY IS LEGITIMATE (two regions, two
        # products), so the id is made unique rather than refused.
        base, n = did, 1
        while c.execute("SELECT 1 FROM deals WHERE deal_id=?", (did,)).fetchone():
            n += 1
            did = "%s-%d" % (base, n)
        track = canon_track(f.get("track")) or DEFAULT_TRACK
        c.execute("""INSERT INTO deals (deal_id, company, track, country, domain, contact, title,
                                        stage, owner, created_ts, updated_ts, note)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (did, name, track, str(f.get("country") or ""),
                   str(f.get("domain") or "").lower(),
                   str(f.get("contact") or ""), str(f.get("title") or ""),
                   canon_stage(f.get("stage"), track) or first_stage(track), str(owner or ""),
                   now, now, str(f.get("note") or "")))
        c.commit()
    finally:
        c.close()
    _log(evt="deal_created", deal=did, company=name, user=owner)
    return get(did)


def set_stage(deal_id, stage, by=""):
    """Move a card. Returns (ok, detail). A stage nobody defined is REFUSED, not stored: the board
    would render an empty column and the card would be gone from every other one."""
    c = _conn()
    try:
        row = c.execute("SELECT stage, track FROM deals WHERE deal_id=?", (deal_id,)).fetchone()
        if not row:
            return False, "no such deal"
        was, track = row["stage"], row["track"]
        # THE DEAL'S OWN TRACK DECIDES. `mpa` is a partner stage and `pilot` is not; accepting a
        # stage from another track would file the card in a column this board never renders, and
        # it would simply disappear.
        s = canon_stage(stage, track)
        if not s:
            return False, "%r is not a stage of the %s track" % (stage, track)
        c.execute("UPDATE deals SET stage=?, updated_ts=? WHERE deal_id=?", (s, _now(), deal_id))
        c.commit()
    finally:
        c.close()
    if was != s:
        # THE MOVE IS THE HISTORY. A board that only holds the current column cannot answer "how
        # long did the NDA take", which is the one question a channel pipeline exists to answer.
        add_note(deal_id, "%s -> %s" % (was, s), kind="stage", author=by)
    _log(evt="deal_stage", deal=deal_id, user=by, was=was, now=s)
    return True, s


def set_fields(deal_id, by="", **f):
    cols = {k: v for k, v in f.items()
            if k in ("company", "country", "domain", "contact", "title", "note", "owner", "track")
            and v is not None}
    if not cols:
        return False
    if "domain" in cols:
        cols["domain"] = str(cols["domain"]).strip().lower()
    if "track" in cols:
        t = canon_track(cols["track"])
        if not t:
            return False
        cols["track"] = t
        # CHANGING TRACK RE-HOMES THE CARD. The stages differ between tracks, so a deal moved from
        # Herkos to Partner while sitting in `evaluation` would land in a column the partner board
        # does not have and vanish. It restarts at the new track's first stage, which is honest:
        # the process it is in really did change.
        cur = get(deal_id)
        if cur and cur.get("track") != t:
            cols["stage"] = first_stage(t)
    c = _conn()
    try:
        sets = ", ".join("%s=?" % k for k in cols) + ", updated_ts=?"
        cur = c.execute("UPDATE deals SET %s WHERE deal_id=?" % sets,
                        tuple(cols.values()) + (_now(), deal_id))
        c.commit()
        ok = cur.rowcount > 0
    finally:
        c.close()
    if ok:
        _log(evt="deal_edited", deal=deal_id, user=by, fields=sorted(cols))
    return ok


def delete(deal_id, by=""):
    c = _conn()
    try:
        cur = c.execute("DELETE FROM deals WHERE deal_id=?", (deal_id,))
        c.execute("DELETE FROM deal_notes WHERE deal_id=?", (deal_id,))
        # MAIL IS NOT DELETED, IT IS UNFILED. The message was really received; dropping it would
        # make the same message match again on the next read and look like new activity.
        c.execute("UPDATE deal_mail SET deal_id='' WHERE deal_id=?", (deal_id,))
        c.commit()
        ok = cur.rowcount > 0
    finally:
        c.close()
    _log(evt="deal_deleted", deal=deal_id, user=by, existed=ok)
    return ok


def _row(r):
    return {"deal_id": r["deal_id"], "company": r["company"], "track": r["track"],
            "country": r["country"],
            "domain": r["domain"], "contact": r["contact"], "title": r["title"],
            "stage": r["stage"], "owner": r["owner"], "created_ts": r["created_ts"],
            "updated_ts": r["updated_ts"], "note": r["note"]}


def get(deal_id):
    c = _conn()
    try:
        r = c.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,)).fetchone()
        return _row(r) if r else None
    finally:
        c.close()


def rows(track=None, include_closed=True):
    c = _conn()
    try:
        out = [_row(r) for r in c.execute("SELECT * FROM deals ORDER BY updated_ts DESC")]
    finally:
        c.close()
    t = canon_track(track)
    if t:
        out = [d for d in out if d["track"] == t]
    if not include_closed:
        out = [d for d in out if d["stage"] not in CLOSED]
    return out


def add_note(deal_id, body, kind="note", author=""):
    text = str(body or "").strip()
    if not text:
        return None
    nid = "%d-%s" % (int(_now() * 1000), re.sub(r"\W", "", str(kind))[:8] or "note")
    c = _conn()
    try:
        c.execute("INSERT INTO deal_notes (note_id, deal_id, body, kind, author, ts) "
                  "VALUES (?,?,?,?,?,?)", (nid, deal_id, text[:4000], str(kind), str(author or ""),
                                           _now()))
        c.execute("UPDATE deals SET updated_ts=? WHERE deal_id=?", (_now(), deal_id))
        c.commit()
    finally:
        c.close()
    return nid


def notes_for(deal_id, limit=200):
    c = _conn()
    try:
        return [{"note_id": r["note_id"], "body": r["body"], "kind": r["kind"],
                 "author": r["author"], "ts": r["ts"]}
                for r in c.execute("SELECT * FROM deal_notes WHERE deal_id=? "
                                   "ORDER BY ts DESC LIMIT ?", (deal_id, int(limit)))]
    finally:
        c.close()


def delete_note(deal_id, note_id):
    c = _conn()
    try:
        cur = c.execute("DELETE FROM deal_notes WHERE deal_id=? AND note_id=?",
                        (deal_id, note_id))
        c.commit()
        return cur.rowcount > 0
    finally:
        c.close()


# ------------------------------------------------------------------------------- filed mail
def mail_seen(msg_id):
    c = _conn()
    try:
        return c.execute("SELECT 1 FROM deal_mail WHERE msg_id=?",
                         (str(msg_id),)).fetchone() is not None
    finally:
        c.close()


def record_mail(msg, verdict, mailbox=""):
    """File one message. `verdict` comes from dealmatch.match(); a verdict with no deal is still
    RECORDED, with its reason, because the unfiled queue is the operator's actual inbox here."""
    mid = str((msg or {}).get("id") or "").strip()
    if not mid:
        return False
    v = verdict or {}
    c = _conn()
    try:
        c.execute("""INSERT INTO deal_mail (msg_id, deal_id, mailbox, sender, subject, snippet,
                                            kind, score, evidence, ts)
                     VALUES (?,?,?,?,?,?,?,?,?,?)
                     ON CONFLICT(msg_id) DO UPDATE SET deal_id=excluded.deal_id,
                        score=excluded.score, evidence=excluded.evidence, kind=excluded.kind""",
                  (mid, str(v.get("deal_id") or ""), str(mailbox or ""),
                   str(msg.get("from") or "")[:300], str(msg.get("subject") or "")[:400],
                   str(msg.get("snippet") or "")[:800],
                   str(v.get("kind") or "mail"), int(v.get("score") or 0),
                   json.dumps(list(v.get("evidence") or [])[:8]),
                   float(msg.get("ts") or _now())))
        if v.get("deal_id"):
            c.execute("UPDATE deals SET updated_ts=? WHERE deal_id=?", (_now(), v["deal_id"]))
        c.commit()
    finally:
        c.close()
    return True


def mails_for(deal_id, limit=50):
    c = _conn()
    try:
        return [_mail(r) for r in c.execute(
            "SELECT * FROM deal_mail WHERE deal_id=? ORDER BY ts DESC LIMIT ?",
            (deal_id, int(limit)))]
    finally:
        c.close()


def unfiled_mail(limit=40):
    c = _conn()
    try:
        return [_mail(r) for r in c.execute(
            "SELECT * FROM deal_mail WHERE deal_id='' ORDER BY ts DESC LIMIT ?", (int(limit),))]
    finally:
        c.close()


def file_mail(msg_id, deal_id, by=""):
    """The operator overruling the matcher, in either direction. An automatic link the person
    cannot undo is worse than no link at all."""
    c = _conn()
    try:
        cur = c.execute("UPDATE deal_mail SET deal_id=? WHERE msg_id=?",
                        (str(deal_id or ""), str(msg_id)))
        c.commit()
        ok = cur.rowcount > 0
    finally:
        c.close()
    if ok:
        _log(evt="mail_filed", msg=str(msg_id)[:40], deal=str(deal_id or "") or None, user=by,
             by_hand=True)
    return ok


def _mail(r):
    try:
        ev = json.loads(r["evidence"] or "[]")
    except Exception:
        ev = []
    return {"msg_id": r["msg_id"], "deal_id": r["deal_id"], "mailbox": r["mailbox"],
            "sender": r["sender"], "subject": r["subject"], "snippet": r["snippet"],
            "kind": r["kind"], "score": r["score"], "evidence": ev, "ts": r["ts"]}


def sweep(days=None, fetch=None, limit=None):
    """Read the configured mailboxes, match each message against the OPEN deals, file what matches.

    RE-RUNNABLE BY CONSTRUCTION. It reads a WINDOW, not a cursor, and `msg_id` is the primary key
    of deal_mail - so a crash halfway costs nothing and a second run files nothing twice. A cursor
    would have to be stored, kept consistent with a mailbox nobody here controls, and repaired by
    hand when it drifted.

    A MESSAGE THAT MATCHES NOTHING IS STILL RECORDED, with the matcher's reason. That queue is the
    point: "we saw it and could not place it" is work for a person, and dropping it would make the
    same message look like new activity on the next sweep.

    The label from dealmatch.classify() is stored and NEVER acted on. The gates in the process map
    are signature events; an email that says "NDA" is not an NDA that was signed, and a board that
    advanced itself on vocabulary would be fiction within a week.
    """
    from . import dealmatch, gmail_read
    msgs, notes = gmail_read.fetch_recent(days=days, fetch=fetch, limit=limit)
    open_deals = [d for d in rows() if d["stage"] not in CLOSED]
    filed = unfiled = skipped = 0
    for m in msgs:
        if mail_seen(m.get("id")):
            skipped += 1
            continue
        v = dealmatch.match(m, open_deals)
        v["kind"] = dealmatch.classify(m)
        if not v.get("deal_id") and v.get("why_not"):
            v.setdefault("evidence", [])
            v["evidence"] = list(v["evidence"]) + ["unfiled: " + v["why_not"]]
        record_mail(m, v, mailbox=m.get("mailbox", ""))
        if v.get("deal_id"):
            filed += 1
        else:
            unfiled += 1
    out = {"read": len(msgs), "filed": filed, "unfiled": unfiled, "already_seen": skipped,
           "deals_considered": len(open_deals), "notes": notes}
    _log(evt="pipeline_sweep", **{k: v for k, v in out.items() if k != "notes"})
    return out


def counts(track=None):
    """Cards per stage for ONE track, every stage present even at zero - a column missing from a
    summary reads as a stage nobody uses rather than a stage nobody has reached."""
    t = canon_track(track) or DEFAULT_TRACK
    out = {k: 0 for k in stage_keys(t)}
    for d in rows():
        if d["track"] == t and d["stage"] in out:
            out[d["stage"]] += 1
    return out


# ---------------------------------------------------------------------------------------------
# THE ROUTER. Built, not declared, so the PERMISSIONS ARE INJECTED: main.py passes
# `_require_perm("pipeline.view")` and friends, which read roles.py. The policy therefore has one
# home and this module can be exercised in a test without an auth stack.
#
# EVERY ROUTE DEMANDS A VERB, never an identity. `pipeline.view` reads, `pipeline.edit` writes,
# `pipeline.admin` sweeps the mailboxes and re-files by hand - the three verbs roles.py already
# defines, held today by admin, s4biz_power, reseller_admin and sales_rep. That is the operator's
# "just for users that are part of S4biz": it is a permission, not a domain check, so adding a
# partner's sales person later is a role change rather than a code change.
# ---------------------------------------------------------------------------------------------
def build_router(require_view, require_edit, require_admin):
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel

    class DealReq(BaseModel):
        company: str = ""
        track: str = ""
        country: str = ""
        domain: str = ""
        contact: str = ""
        title: str = ""
        note: str = ""

    class PatchReq(BaseModel):
        stage: str = ""
        company: str = ""
        track: str = ""
        country: str = ""
        domain: str = ""
        contact: str = ""
        title: str = ""
        note: str = ""

    class NoteReq(BaseModel):
        body: str = ""

    class FileReq(BaseModel):
        deal_id: str = ""

    r = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

    @r.get("")
    def board(track: str = "", user=Depends(require_view)):
        """The whole board for one track: the columns, the cards, and what is waiting to be filed.

        ONE REQUEST, ONE SNAPSHOT (class 56). The columns, the cards and the counts are read once
        and derived from the same list; reading the store twice inside one handler lets a sweep
        land in between and the halves then describe different moments.
        """
        t = canon_track(track) or DEFAULT_TRACK
        deals = rows(track=t)
        by_stage = {}
        for d in deals:
            by_stage.setdefault(d["stage"], []).append(d)
        return {"track": t, "tracks": tracks(), "stages": stage_meta(t),
                "deals": deals,
                "counts": {k: len(by_stage.get(k, [])) for k in stage_keys(t)},
                "unfiled": unfiled_mail(limit=20),
                "mail": _mail_status()}

    @r.post("")
    def new_deal(req: DealReq, user=Depends(require_edit)):
        d = create(req.company, owner=user, track=req.track, country=req.country,
                   domain=req.domain, contact=req.contact, title=req.title, note=req.note)
        if not d:
            raise HTTPException(status_code=400, detail="a deal needs a company name")
        return d

    @r.get("/{deal_id}")
    def one(deal_id: str, user=Depends(require_view)):
        d = get(deal_id)
        if not d:
            raise HTTPException(status_code=404, detail="no such deal")
        return {"deal": d, "notes": notes_for(deal_id), "mail": mails_for(deal_id),
                "stages": stage_meta(d["track"])}

    @r.patch("/{deal_id}")
    def edit(deal_id: str, req: PatchReq, user=Depends(require_edit)):
        if not get(deal_id):
            raise HTTPException(status_code=404, detail="no such deal")
        if req.stage:
            ok, detail = set_stage(deal_id, req.stage, by=user)
            if not ok:
                # THE BOARD MOVES THE CARD OPTIMISTICALLY, so a refusal has to carry a reason the
                # UI can show when it puts the card back. "400" alone would leave the operator
                # watching a card jump with no explanation.
                raise HTTPException(status_code=400, detail=detail)
        fields = {k: v for k, v in req.model_dump().items()
                  if k != "stage" and v not in ("", None)}
        if fields:
            set_fields(deal_id, by=user, **fields)
        return get(deal_id)

    @r.delete("/{deal_id}")
    def drop(deal_id: str, user=Depends(require_edit)):
        return {"ok": delete(deal_id, by=user)}

    @r.post("/{deal_id}/notes")
    def note(deal_id: str, req: NoteReq, user=Depends(require_edit)):
        if not get(deal_id):
            raise HTTPException(status_code=404, detail="no such deal")
        nid = add_note(deal_id, req.body, author=user)
        if not nid:
            raise HTTPException(status_code=400, detail="an empty note is not a note")
        return {"ok": True, "note_id": nid, "notes": notes_for(deal_id)}

    @r.delete("/{deal_id}/notes/{note_id}")
    def unnote(deal_id: str, note_id: str, user=Depends(require_edit)):
        return {"ok": delete_note(deal_id, note_id), "notes": notes_for(deal_id)}

    @r.post("/mail/{msg_id}/file")
    def refile(msg_id: str, req: FileReq, user=Depends(require_admin)):
        """The operator overruling the matcher, in either direction. An automatic link a person
        cannot undo is worse than no link: the matcher is a SIGNAL, the person decides."""
        if req.deal_id and not get(req.deal_id):
            raise HTTPException(status_code=404, detail="no such deal")
        if not file_mail(msg_id, req.deal_id, by=user):
            raise HTTPException(status_code=404, detail="no such message")
        return {"ok": True}

    @r.post("/sweep")
    def do_sweep(days: int = 0, user=Depends(require_admin)):
        """Read the mailboxes now. Bounded, re-runnable, and it reports what it did rather than
        'ok' - a sync that cannot say how many it read and how many it could not place is a sync
        nobody can debug."""
        return sweep(days=days or None)

    return r


def _mail_status():
    """What the board shows about the reader. A feature guarded by `if configured():` fails
    silently by construction (class 37), so the screen says when it is off and what is missing."""
    try:
        from . import gmail_read
        return gmail_read.status()
    except Exception as e:
        return {"enabled": False, "note": "the mail reader could not be loaded: %r" % (e,)}


def _cli_sweep():
    """`python -m app.pipeline sweep` - what the systemd timer runs through `docker exec`.

    IT SAYS WHAT IT DID, AND WHY NOT. A timer whose output is silence cannot be told apart from a
    timer that was never installed, and `if configured():` fails silently by construction
    (class 37). Being switched off is not a fault, so that path prints the reason and exits 0; a
    real fault exits non-zero and systemd records it.
    """
    from . import gmail_read
    if not gmail_read.configured():
        print("mailsweep: OFF - %s" % gmail_read.status()["note"])
        return 0
    out = sweep()
    print("mailsweep: read %(read)d, filed %(filed)d, unfiled %(unfiled)d, "
          "already seen %(already_seen)d, against %(deals_considered)d open deal(s)" % out)
    for n in out["notes"]:
        print("   %s" % n)
    return 0


# THE GUARD IS THE LAST STATEMENT IN THE FILE, and that is a rule rather than a style: module
# order is execution order, so a `__main__` block placed mid-file runs where it APPEARS and every
# def below it does not exist yet. Invisible to an importer, fatal to `python -m app.pipeline`.
# This block used to sit above build_router() (class 48).
if __name__ == "__main__":                                      # pragma: no cover
    if len(sys.argv) > 1 and sys.argv[1] == "sweep":
        sys.exit(_cli_sweep())
    for t, lab, about in TRACKS:
        print("\n%s - %s (%s)%s" % (t.upper(), lab, about,
                                    "   [default]" if t == DEFAULT_TRACK else ""))
        for st in stage_meta(t):
            print("   %-4s %-14s %-34s gate: %s" % (st["code"], st["key"], st["label"], st["gate"]))
    print("\nlegacy keys remapped: %s" % ", ".join(sorted(LEGACY_STAGES)))
    print("source: Herkos_Commercial_Process_Map_v0.1_DRAFT.docx (HRK-COM-PRC-001, Assad Kondakji)")
    print("database: %s" % db_path())
