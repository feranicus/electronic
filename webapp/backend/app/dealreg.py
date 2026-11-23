#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dealreg.py — deal registration: a reseller tells us about a large deal BEFORE it closes, and in
return gets price protection, a discount and dedicated support on it. One partner per opportunity.

NOBODY HAS WRITTEN THIS DOWN YET, AND THAT IS RECORDED RATHER THAN HIDDEN.
    `Herkos_Commercial_Process_Map_v0.1_DRAFT.docx` defines the three pipeline TRACKS (partner
    R1-R6, Herkos H0-H9, Perseus P0-P10) and `pipeline.py` carries them verbatim, because a
    process the business already wrote down is not mine to invent (class 59). It says NOTHING
    about deal registration. MEASURED 23 Nov 2026: no document in this repository contains the
    phrase.
    So the rules below are the CHANNEL-SALES MARKET STANDARD, researched from vendors' own
    programme guides (Check Point, Sophos, Barracuda, Veeam, Zscaler, Nutanix, Fortinet, Dell,
    Microsoft, AWS), not the business's own policy. Every number is a DEFAULT with a named source
    in `docs/decisions/2026-11-deal-registration.md`. When Assad writes the real programme guide,
    this module is where it lands, and the defaults are replaced by his numbers - not argued with.

THE FOUR RULES THAT ARE NOT DEFAULTS. These are doctrine, and a change to any of them is a legal
and commercial decision, not a configuration change.

 1. **A REGISTRATION IS AN INCENTIVE, NEVER A PROHIBITION.** Losing a registration costs a partner
    the DISCOUNT, the PROTECTION and the dedicated support. It NEVER costs them the right to quote
    that customer, to be supplied, or to be given a price. `refused_protection()` is the only thing
    this module can do to a second partner.
    This is both the market standard - Nutanix: the second partner "may still obtain a standard-
    price quote"; Barracuda and Proofpoint the same - and the only defensible position under EU
    competition law. A programme OPERATED so that a non-registering reseller is refused supply or
    refused a quote for "their" account stops being a supplier's pricing decision and becomes
    customer allocation (Art. 4(b)/(d) VBER), and blocking a reseller from answering an unsolicited
    enquiry is a restriction of a PASSIVE sale, which is hardcore and voids the block exemption for
    the whole agreement regardless of market share. The sentence is cheap to write and the
    behaviour is expensive to retrofit, so it is enforced by test.
    NOT LEGAL ADVICE: the decision doc records this as researched doctrine for counsel to confirm.

 2. **OPPORTUNITY-SCOPED, NEVER ACCOUNT-SCOPED.** Protection attaches to ONE opportunity at one
    customer, not to the customer. A second partner may hold a DIFFERENT opportunity at the same
    end customer, and a renewal or a second project is a new registration. Zscaler states it
    hardest ("granted by opportunity, not by account"); Cisco, Barracuda, Veeam and Fortinet all
    say the same. Account-scoped lockout is the minority model, it manufactures a false duplicate
    every time a customer runs two unrelated projects, and it is the shape that looks most like
    customer allocation.

 3. **DETERMINISTIC CODE DECIDES; THE MODELS ARE A SIGNAL.** The duplicate verdict that costs a
    partner money is computed by `duplicate_of()` from the match key below - no model is consulted
    and none can be. The four-vendor panel in `panel.py` may only RAISE A FLAG for a human on a
    near-miss the key cannot see (a subsidiary under another name, a typo'd domain) and WRITE the
    reply the first-registering partner reads. It cannot grant, refuse or revoke protection. Same
    doctrine as the engine's FP auditor: "an audit is a SIGNAL, not an authority", and as
    perseus/vet.py: models propose, code decides.

 4. **A DUPLICATE IS A FORK, NOT A FAILURE.** Nutanix publishes two distinct denial codes, and the
    second is the one that matters: "same end user, DIFFERENT deal, but insufficient information to
    distinguish it." That is a REQUEST TO THE PARTNER, not a refusal, and it goes to `returned`,
    which is fixable, never to `rejected`, which is terminal. Conflating the two inflates the
    rejection rate and reads as arbitrary.

WHAT IDENTIFIES A DEAL. Every source that addresses it agrees on the registrable domain, never the
    typed company name ("a partner submitting at acme.com triggers a duplicate regardless of how
    the company name was entered"). `_apex()` here is `psl.registrable()` - the SAME eTLD+1 home
    the engine uses, because "the last two labels" turns budget.gov.ru into gov.ru, and here that
    would make one ministry's registration block every other ministry's.
"""
import json
import os
import re
import sqlite3
import time
import uuid

# ---------------------------------------------------------------------------- the match key

def _apex(host):
    """The registrable domain (eTLD+1). ONE HOME: the engine's psl, never a label count.

    A naive "last two labels" makes `budget.gov.ru` into `gov.ru`, so the first ministry to
    register would hold protection against the entire Russian government - a false duplicate for
    every other public body on that suffix. The engine already paid for this lesson.
    """
    h = (host or "").strip().lower()
    h = re.sub(r"^[a-z]+://", "", h).split("/")[0].split("?")[0].split("@")[-1]
    h = h.split(":")[0].strip(".")
    if not h or "." not in h:
        return ""
    try:
        import sys
        for p in ("/opt/shodan-skill/scripts",
                  os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "..", "..", "hermes-skills", "shodan-assessment", "scripts")):
            p = os.path.abspath(p)
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        import psl
        return (psl.registrable(h) or "").lower()
    except Exception:
        # A FAILED LOOKUP IS NOT A FINDING (the engine's first non-negotiable). Returning a guess
        # here would invent a duplicate; returning "" means this registration simply cannot be
        # matched by domain and the caller says so out loud.
        return ""


# PRODUCT LINES. The second dimension of the match key: the same customer buying Herkos and buying
# Perseus is two opportunities, and one partner registering the first must not block the other.
PRODUCT_LINES = ["herkos", "perseus", "both"]


def canon_product(p):
    p = (p or "").strip().lower()
    return p if p in PRODUCT_LINES else ""


# ---------------------------------------------------------------------------- the state machine
#
# TWO ORTHOGONAL MACHINES, which is the single best structural idea in the researched material and
# is independently settled practice at AWS, Channeltivity, ZINFI and Zift: the VENDOR's verdict and
# the PARTNER's sales stage are different questions and must not share a column. Collapsing them is
# how "approved" comes to mean "approved, and also still only a prospect".
#
#   STATES   - ours. What we decided about the registration.
#   STAGES   - theirs. Where the deal is in their sales cycle. Never used for any decision here.
STATES = [
    ("submitted",  "Submitted",       "received, not yet looked at"),
    ("review",     "Under review",    "a human is checking it"),
    ("returned",   "More info needed", "FIXABLE: the partner can complete it and resubmit"),
    ("approved",   "Approved",        "protected until the expiry date"),
    ("rejected",   "Rejected",        "terminal, with a reason"),
    ("duplicate",  "Already registered", "another partner got here first - protection only"),
    ("expired",    "Expired",         "the protection window ran out"),
    ("won",        "Closed won",      ""),
    ("lost",       "Closed lost",     ""),
]
STATE_KEYS = [s[0] for s in STATES]

# Permitted transitions, published as a table the way Microsoft publishes theirs. A move that is
# not in this table is refused BY NAME, so an impossible state change reads as a bug report rather
# than as silence.
NEXT_STATE = {
    "submitted": {"review", "approved", "returned", "rejected", "duplicate"},
    "review":    {"approved", "returned", "rejected", "duplicate"},
    "returned":  {"submitted", "review", "rejected"},
    "approved":  {"won", "lost", "expired", "rejected"},
    "duplicate": {"review", "approved"},      # the first registration may collapse; this one revives
    "rejected":  set(),
    "expired":   set(),                        # re-register from scratch, like Check Point
    "won":       set(),
    "lost":      set(),
}

TERMINAL = {k for k, v in NEXT_STATE.items() if not v}

# The partner's own sales stage. Theirs to set, ours to never decide on.
STAGES = ["prospect", "qualified", "technical_validation", "proposal", "committed"]

# ---------------------------------------------------------------------------- the numbers
#
# DEFAULTS WITH SOURCES, not inventions. Each is overridable from the environment so the programme
# can change without a deploy, and every one is printed by `config()` with its provenance - the
# same discipline as the engine's effective-chain report.
PROTECTION_DAYS = int(os.environ.get("DEALREG_PROTECTION_DAYS", "90"))   # modal window: Fortinet,
#   Check Point, Sophos, Barracuda, SonicWall, Dell, Lenovo EMEA all publish 90.
EXTENSION_DAYS = int(os.environ.get("DEALREG_EXTENSION_DAYS", "90"))     # Dell: partner-initiated.
MAX_TOTAL_DAYS = int(os.environ.get("DEALREG_MAX_TOTAL_DAYS", "270"))    # Dell: 90 + 2x90 cap.
REMIND_DAYS = [30, 15, 1]                                                # Barracuda's published
#   cadence. Reminders are what stop a partner losing protection to a date nobody watched.
DECISION_SLA_DAYS = int(os.environ.get("DEALREG_SLA_DAYS", "5"))         # Sophos publishes five
#   business days and hedges it ("in der Regel"); Microsoft commits to five and is the only vendor
#   that publishes a symmetric obligation on itself. The honest finding from the research is that
#   most security vendors publish NO SLA at all, so this is a target we choose, not a market norm.
#
# NO MINIMUM DEAL SIZE. Deliberate, and the research is unambiguous that this is the direction of
# travel rather than a gap: Check Point abolished its $20K minimum, Sophos removed ALL minimums
# globally in Jan 2026, and Veeam, Rapid7 and Tenable publish none. A minimum mostly teaches small
# partners not to bother registering, which costs the vendor the pipeline visibility the programme
# exists to buy.
MIN_DEAL_VALUE = 0

# The clock starts at APPROVAL, not submission. Dell documents its own drift between the two and
# the current terms run from approval; Check Point, Sophos, Veeam and Rapid7 all do the same.
# Whichever is chosen it must be stated on the form, so `config()` reports it.
CLOCK_STARTS = "approval"


def config():
    """The EFFECTIVE programme terms with provenance - never a constant retyped into a UI string.

    The deck, the partner pack and the form all read this, so a term cannot be changed in one place
    and stay stale in another (class 32). Printed by the admin page and by the decision doc's own
    test, which is what keeps the prose and the code from drifting apart.
    """
    def _src(name, default):
        return "env:%s" % name if os.environ.get(name) else "default (see 2026-11-deal-registration.md)"
    return {
        "protection_days": PROTECTION_DAYS, "protection_src": _src("DEALREG_PROTECTION_DAYS", 90),
        "extension_days": EXTENSION_DAYS, "max_total_days": MAX_TOTAL_DAYS,
        "remind_days": list(REMIND_DAYS), "sla_days": DECISION_SLA_DAYS,
        "min_deal_value": MIN_DEAL_VALUE, "clock_starts": CLOCK_STARTS,
        "scope": "opportunity",          # never "account" - see doctrine 2
        "second_partner": "may always quote; loses protection only",   # doctrine 1, in the API
    }


# ---------------------------------------------------------------------------- duplicate detection

def match_key(reg):
    """The tuple two registrations are compared on. Domain, country and product line.

    NOT the typed company name: "Müller GmbH", "Mueller GmbH" and "MUELLER" are one customer and
    three strings. The name is kept as a SECONDARY signal for the panel to reason about, never as
    the key.
    """
    return (_apex(reg.get("domain") or ""),
            (reg.get("country") or "").strip().upper(),
            canon_product(reg.get("product")))


def duplicate_of(candidate, existing, now=None):
    """Is `candidate` already protected by one of `existing`? THE DECISION. No model is consulted.

    Returns the protecting registration plus the EVIDENCE for it, or None. The evidence exists so
    the partner is told WHY rather than just "no": a refusal a partner cannot check is a refusal
    they will escalate to a human every single time.

    An EMPTY domain never matches anything. That is deliberate and it is the engine's rule: a
    failed lookup reports UNKNOWN and claims no finding. Matching two blank keys to each other
    would hand the first partner with an unparseable domain protection over every other one.
    """
    now = time.time() if now is None else now
    ck = match_key(candidate)
    if not ck[0]:
        return None
    for e in existing:
        if e.get("id") and e.get("id") == candidate.get("id"):
            continue
        if e.get("state") != "approved":
            continue                       # only an APPROVED registration protects anything
        if e.get("expires_at") and float(e["expires_at"]) < now:
            continue                       # expired protection is not protection
        if match_key(e) != ck:
            continue
        return {"id": e["id"], "owner": e.get("owner", ""),
                "expires_at": e.get("expires_at"),
                "evidence": ["same registrable domain: %s" % ck[0],
                             "same country: %s" % (ck[1] or "(none given)"),
                             "same product line: %s" % (ck[2] or "(none given)"),
                             "their registration is approved and still inside its window"]}


def distinguishable(candidate, protecting):
    """Could this be a DIFFERENT opportunity at the same customer? Then it is `returned`, not
    `duplicate` - Nutanix's second denial code, and the one that keeps the programme honest.

    This never decides either. It asks whether the partner has given us enough to TELL the two
    apart; if they have not, the answer to them is "distinguish it", not "no".
    """
    desc = (candidate.get("description") or "").strip()
    close = candidate.get("close_date") or ""
    return bool(len(desc) >= 40 and close)


# ---------------------------------------------------------------------------- storage

def db_path():
    return os.environ.get("DEALREG_DB") or os.path.join(
        os.environ.get("DATA_DIR", "/data"), "dealreg.sqlite")


def _conn():
    p = db_path()
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(p, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS regs (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, owner_org TEXT NOT NULL DEFAULT '',
        company TEXT NOT NULL DEFAULT '', domain TEXT NOT NULL DEFAULT '',
        country TEXT NOT NULL DEFAULT '', product TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '', value_eur REAL NOT NULL DEFAULT 0,
        close_date TEXT NOT NULL DEFAULT '', contact TEXT NOT NULL DEFAULT '',
        competitor TEXT NOT NULL DEFAULT '', stage TEXT NOT NULL DEFAULT 'prospect',
        state TEXT NOT NULL DEFAULT 'submitted', reason TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL, decided_at REAL, expires_at REAL,
        extensions INTEGER NOT NULL DEFAULT 0, dup_of TEXT NOT NULL DEFAULT '',
        panel TEXT NOT NULL DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, reg_id TEXT NOT NULL, ts REAL NOT NULL,
        actor TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '')""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_regs_state ON regs(state)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_events_reg ON events(reg_id)")
    return c


def _row(r):
    d = dict(r)
    d["panel"] = json.loads(d.get("panel") or "null") if d.get("panel") else None
    return d


def _event(c, reg_id, kind, actor="", detail=""):
    c.execute("INSERT INTO events(reg_id, ts, actor, kind, detail) VALUES(?,?,?,?,?)",
              (reg_id, time.time(), actor or "", kind, detail or ""))


def submit(owner, **f):
    """A partner registers a deal. Always accepted into `submitted` - AWS's rule, and the right
    one: "no submission is turned away." Quality is scored and adjudicated, not refused at the door,
    because a partner who cannot get a deal INTO the system simply stops telling you about deals.

    The duplicate check runs here and is RECORDED, but it does not reject: it sets the state to
    `duplicate` with the protecting registration named, and that state still carries the explicit
    "you may quote this customer" fact (doctrine 1).
    """
    if not (owner or "").strip():
        raise ValueError("a registration must have an owner - it is the thing being protected")
    rid = "DR-" + uuid.uuid4().hex[:10].upper()
    now = time.time()
    rec = {"id": rid, "owner": owner.strip().lower(),
           "owner_org": (owner.split("@")[-1] or "").strip().lower(),
           "company": (f.get("company") or "").strip(),
           "domain": (f.get("domain") or "").strip().lower(),
           "country": (f.get("country") or "").strip().upper(),
           "product": canon_product(f.get("product")),
           "description": (f.get("description") or "").strip(),
           "value_eur": float(f.get("value_eur") or 0),
           "close_date": (f.get("close_date") or "").strip(),
           "contact": (f.get("contact") or "").strip(),
           "competitor": (f.get("competitor") or "").strip(),
           "stage": (f.get("stage") or "prospect").strip().lower(),
           "state": "submitted", "created_at": now}
    with _conn() as c:
        prot = duplicate_of(rec, [_row(r) for r in c.execute("SELECT * FROM regs")], now=now)
        if prot:
            if distinguishable(rec, prot):
                rec["state"] = "review"
                rec["reason"] = ("same customer and product line as %s, but described well enough "
                                 "to be a different opportunity - a human decides" % prot["id"])
            else:
                rec["state"] = "duplicate"
                rec["dup_of"] = prot["id"]
                rec["reason"] = refused_protection(prot)["message"]
        cols = ",".join(rec)
        c.execute("INSERT INTO regs(%s) VALUES(%s)" % (cols, ",".join("?" * len(rec))),
                  tuple(rec.values()))
        _event(c, rid, "submitted", owner, rec.get("reason", ""))
    return rid


def refused_protection(protecting):
    """THE ONLY THING THAT HAPPENS TO THE SECOND PARTNER, and the wording is doctrine 1 in a string.

    It says what they lost (protection, the registered discount, dedicated support) and - in the
    same breath, not in a footnote - what they did NOT lose. A partner who reads this and concludes
    they are barred from the customer would be reading a restriction we never imposed and may not
    impose, so the sentence is asserted by test.
    """
    return {"protected_by": protecting.get("id", ""),
            "evidence": protecting.get("evidence", []),
            "message": ("This opportunity is already registered by another partner, so the "
                        "registered discount, the protection and the dedicated deal support go to "
                        "them. You remain free to quote this customer on standard terms, and we "
                        "will supply and price you for it exactly as usual. If this is a "
                        "DIFFERENT project at the same customer, say what distinguishes it and we "
                        "will register it separately.")}


def decide(reg_id, state, by="", reason=""):
    """Move a registration. Refuses an impossible transition BY NAME, and starts the clock on
    approval. `by` is recorded on every move: who decided is part of the decision."""
    state = (state or "").strip().lower()
    if state not in STATE_KEYS:
        raise ValueError("unknown state %r - the states are %s" % (state, ", ".join(STATE_KEYS)))
    with _conn() as c:
        cur = c.execute("SELECT * FROM regs WHERE id=?", (reg_id,)).fetchone()
        if not cur:
            raise KeyError(reg_id)
        was = cur["state"]
        if state not in NEXT_STATE.get(was, set()):
            raise ValueError("%s cannot go from %r to %r (allowed: %s)"
                             % (reg_id, was, state,
                                ", ".join(sorted(NEXT_STATE.get(was, set())) or ["nothing"])))
        now = time.time()
        exp = cur["expires_at"]
        if state == "approved":
            exp = now + PROTECTION_DAYS * 86400     # the clock starts at APPROVAL
        c.execute("UPDATE regs SET state=?, reason=?, decided_at=?, expires_at=? WHERE id=?",
                  (state, reason or "", now, exp, reg_id))
        _event(c, reg_id, state, by, reason or "")
    return True


def extend(reg_id, by="", days=None):
    """One partner-initiated extension at a time, capped in total. Dell's model: in-tool, and a
    HARD cumulative ceiling, because an unbounded extension is a registration that never expires
    and an account quietly locked up for a year is the shape competition law dislikes most."""
    days = EXTENSION_DAYS if days is None else int(days)
    with _conn() as c:
        r = c.execute("SELECT * FROM regs WHERE id=?", (reg_id,)).fetchone()
        if not r:
            raise KeyError(reg_id)
        if r["state"] != "approved":
            raise ValueError("only an approved registration can be extended (this one is %r)"
                             % r["state"])
        total = PROTECTION_DAYS + (r["extensions"] + 1) * days
        if total > MAX_TOTAL_DAYS:
            raise ValueError("that would take this registration to %d days of protection; the cap "
                             "is %d. Re-register instead, and it is judged on its own merits."
                             % (total, MAX_TOTAL_DAYS))
        c.execute("UPDATE regs SET expires_at=?, extensions=extensions+1 WHERE id=?",
                  ((r["expires_at"] or time.time()) + days * 86400, reg_id))
        _event(c, reg_id, "extended", by, "+%d days" % days)
    return True


def sweep(now=None):
    """Expire what has run out. A TIMER, not a human: protection nobody is tracking is protection
    that quietly becomes permanent, which is the account-lockout shape doctrine 2 refuses.

    Returns the ids expired and the ones due a reminder, so the caller can notify. It does not send
    anything itself - a store that mails is a store that cannot be tested.
    """
    now = time.time() if now is None else now
    expired, remind = [], []
    with _conn() as c:
        for r in c.execute("SELECT * FROM regs WHERE state='approved'"):
            if not r["expires_at"]:
                continue
            left = (float(r["expires_at"]) - now) / 86400.0
            if left <= 0:
                c.execute("UPDATE regs SET state='expired' WHERE id=?", (r["id"],))
                _event(c, r["id"], "expired", "sweep", "protection window ended")
                expired.append(r["id"])
            elif any(abs(left - d) < 0.5 for d in REMIND_DAYS):
                remind.append({"id": r["id"], "owner": r["owner"], "days_left": round(left)})
    return {"expired": expired, "remind": remind}


def get(reg_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM regs WHERE id=?", (reg_id,)).fetchone()
        return _row(r) if r else None


def events_for(reg_id, limit=200):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM events WHERE reg_id=? ORDER BY ts DESC LIMIT ?", (reg_id, int(limit)))]


def visible_to(email, role_perms, limit=500):
    """WHO SEES WHAT. The RBAC rule the operator asked for, in one place.

    Anyone holding `dealreg.view.all` - every S4biz account - sees every registration, because
    adjudicating "who got here first" is impossible from a partial view and because an S4biz seller
    needs to know an account is spoken for before promising it to someone else.
    A partner sees THEIR OWN and nothing else. That is not only need-to-know: a registration names
    an end customer, a value, a close date and the incumbent competitor, and routing that to a
    rival reseller would be competitor-to-competitor disclosure made THROUGH us.
    """
    perms = set(role_perms or ())
    with _conn() as c:
        if "dealreg.view.all" in perms:
            rows = c.execute("SELECT * FROM regs ORDER BY created_at DESC LIMIT ?",
                             (int(limit),)).fetchall()
        else:
            rows = c.execute("SELECT * FROM regs WHERE owner=? ORDER BY created_at DESC LIMIT ?",
                             ((email or "").strip().lower(), int(limit))).fetchall()
    return [_row(r) for r in rows]


def board(email, role_perms):
    """The columns the page renders: one per STATE, in the published order, with the terms."""
    regs = visible_to(email, role_perms)
    cols = {k: [] for k in STATE_KEYS}
    for r in regs:
        cols.setdefault(r["state"], []).append(r)
    return {"states": [{"key": k, "label": lab, "about": ab} for k, lab, ab in STATES],
            "columns": cols, "config": config(),
            "can_decide": "dealreg.decide" in set(role_perms or ()),
            "sees_all": "dealreg.view.all" in set(role_perms or ())}


def build_router(require_submit, require_view, require_decide, perms_of):
    """Routes. Built HERE from dependencies passed in, so the permissions come from roles.py
    through main's `_require_perm` - one home for the policy - and this module stays testable with
    no auth stack bolted to it. Same shape as pipeline.build_router().

    `perms_of` is how a route learns what the CALLER may see, because `visible_to()` needs the
    permission set, not the role name: the scoping rule lives in one function and every route
    reads it rather than re-deriving who-sees-what per endpoint (which is how one endpoint ends up
    leaking the set the other three protect).
    """
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel

    r = APIRouter(prefix="/api/dealreg", tags=["dealreg"])

    class NewReg(BaseModel):
        company: str = ""
        domain: str = ""
        country: str = ""
        product: str = ""
        description: str = ""
        value_eur: float = 0
        close_date: str = ""
        contact: str = ""
        competitor: str = ""
        stage: str = "prospect"

    class Decision(BaseModel):
        state: str = ""
        reason: str = ""

    @r.get("/board")
    def _board(email: str = Depends(require_view)):
        return board(email, perms_of(email))

    @r.get("/config")
    def _config(email: str = Depends(require_view)):
        return config()

    @r.post("")
    def _submit(body: NewReg, email: str = Depends(require_submit)):
        if not (body.company or "").strip() or not (body.domain or "").strip():
            # The domain is the match key. Without it this registration can never be compared to
            # anyone else's, so accepting it would be promising a protection we cannot operate.
            raise HTTPException(422, "a company name and the customer's web domain are required: "
                                     "the domain is what tells two registrations apart")
        rid = submit(email, **body.model_dump())
        return get(rid)

    @r.get("/{reg_id}")
    def _get(reg_id: str, email: str = Depends(require_view)):
        rec = get(reg_id)
        perms = perms_of(email)
        if not rec or ("dealreg.view.all" not in set(perms) and rec["owner"] != email.lower()):
            # 404, NOT 403, on someone else's registration. A 403 confirms the id exists, and an
            # id is a fact about a rival's pipeline - the one thing this permission split exists
            # to withhold.
            raise HTTPException(404, "no such registration")
        return dict(rec, events=events_for(reg_id))

    @r.post("/{reg_id}/decide")
    def _decide(reg_id: str, body: Decision, email: str = Depends(require_decide)):
        try:
            decide(reg_id, body.state, by=email, reason=body.reason)
        except KeyError:
            raise HTTPException(404, "no such registration")
        except ValueError as e:
            raise HTTPException(409, str(e))
        return get(reg_id)

    @r.post("/{reg_id}/extend")
    def _extend(reg_id: str, email: str = Depends(require_decide)):
        try:
            extend(reg_id, by=email)
        except KeyError:
            raise HTTPException(404, "no such registration")
        except ValueError as e:
            raise HTTPException(409, str(e))
        return get(reg_id)

    @r.post("/sweep")
    def _sweep(email: str = Depends(require_decide)):
        return sweep()

    return r


if __name__ == "__main__":                 # LAST STATEMENT IN THE FILE (class 48)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sweep":
        print(json.dumps(sweep(), indent=2))
    else:
        print(json.dumps(config(), indent=2))
