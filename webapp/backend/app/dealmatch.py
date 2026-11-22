"""dealmatch.py — WHICH DEAL IS THIS EMAIL ABOUT? Deterministic, explainable, refuses to guess.

    python -m app.dealmatch        run the self-test (wired into ship.py)

PORTED FROM jobhuntwow's `mailmatch.py`, which has been filing recruiter replies against job
applications since September. The arithmetic is the same because the problem is the same; the
nouns changed (an employer became a partner company, a posting became a deal) and the signals
that only make sense for a job board - the ATS host set, the posting id in the URL - went with
them. The self-test came too, with cases from THIS business.

WHY ARITHMETIC AND NOT A MODEL. A correlation that is WRONG is worse than none: it files
Paratus's pricing question under the New Cognito deal and the board starts lying, quietly, in the
one artefact two people use to agree what is happening. Every signal below is a fact about the
message compared to a fact about the deal, each weighted by how hard it is to be wrong about, and
the evidence comes back so the card can show WHY. There are four models in this estate and not one
of them is consulted here: there is nothing for them to add that counting cannot do, and a
confident wrong link is the exact failure mode the engine's own non-negotiables forbid.

THE SIGNALS, strongest first:
  4  the sender's DOMAIN is the deal's own company domain
  4  the message is from, or copied to, the named CONTACT on the deal
  3  the COMPANY name appears in the From display name, the subject or the body
  2  the deal REFERENCE (its id) appears anywhere in the message
  2  the deal's TITLE contributes 3+ significant words to the subject
  1  the message arrived after the deal was opened and inside the window

NOTHING MATCHES ON ONE WEAK SIGNAL. The floor is above "the company name appeared once", because
"Paratus" in an industry newsletter is not a message from Paratus. A tie is broken by the strongest
evidence and then by recency; still tied, the message is left UNFILED and says so. An honest "I do
not know which of these two" beats filing it under the wrong partner.
"""
import re
import time

# How far back a message may sit from the deal and still be about it. Channel deals run for
# quarters, not weeks - Projectale went from introduction to a signed distributor agreement across
# months - so the window is wider than a job application's.
WINDOW_DAYS = 365
MIN_SCORE = 5
# Free-mail and social domains: they say WHO SENT IT, never WHOSE DEAL it is about.
GENERIC_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com",
    "me.com", "gmx.de", "gmx.net", "web.de", "proton.me", "protonmail.com", "mail.com",
    "linkedin.com", "calendly.com", "docusign.net", "eversign.com", "hellosign.com",
}
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9&.+-]{1,}")
_LEGAL = re.compile(r"(?i)\b(gmbh|ag|ug|kg|ohg|se|ltd|limited|inc|corp|corporation|llc|plc|bv|nv|"
                    r"oy|ab|as|a/s|sa|srl|spa|s\.p\.a|oü|ou|sp\.? z ?o\.?o\.?|pty|lda|co)\b\.?")
_NOISE = {"the", "and", "for", "team", "group", "at", "of", "in", "we", "our", "re", "fwd"}


def norm(s):
    """Lowercased, legal-suffix-free, punctuation-free. Two spellings of one company must collide:
    `Stars4business OÜ` and `stars4business` are the same counterparty."""
    v = _LEGAL.sub(" ", str(s or "").lower())
    return " ".join(w for w in _WORD.findall(v) if w not in _NOISE)


def domain_of(addr):
    """The domain from `Name <a@b.com>` or `a@b.com`. '' when there is none to read."""
    m = re.search(r"[\w.+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", str(addr or ""))
    return m.group(1).lower().strip(".") if m else ""


def registrable(domain):
    """The last two labels. Deliberately NOT a public-suffix implementation: this decides which
    card a mail appears on, not an ownership claim, and `psl.registrable()` belongs to the engine
    where a wrong answer puts a stranger in a customer's deck."""
    parts = [p for p in str(domain or "").lower().split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else ""


def _sig_words(text, min_len=4, limit=8):
    out = []
    for w in _WORD.findall(str(text or "").lower()):
        if len(w) >= min_len and w not in _NOISE and w not in out:
            out.append(w)
    return out[:limit]


def score_row(msg, deal, now=None):
    """(score, evidence[]) for ONE message against ONE deal. Pure; never raises."""
    now = now or time.time()
    ev, sc = [], 0
    frm = str(msg.get("from") or "")
    to = str(msg.get("to") or "") + " " + str(msg.get("cc") or "")
    reply = str(msg.get("reply_to") or "")
    subj = str(msg.get("subject") or "")
    body = str(msg.get("body") or msg.get("snippet") or "")
    hay = " \n ".join((frm, to, reply, subj, body)).lower()

    company = norm(deal.get("company"))
    cwords = [w for w in company.split() if len(w) >= 4]
    dealdom = registrable(str(deal.get("domain") or "").lower())
    opened = float(deal.get("created_ts") or 0)

    # 4 — THE COMPANY'S OWN DOMAIN. The single hardest signal to be wrong about: a message from
    # @paratus.africa is from Paratus.
    d = registrable(domain_of(reply) or domain_of(frm))
    if d and d not in GENERIC_DOMAINS:
        if dealdom and d == dealdom:
            sc += 4
            ev.append("the sender's domain (%s) is the deal's" % d)
        elif cwords and any(w in d.replace(".", " ").replace("-", " ") for w in cwords):
            sc += 4
            ev.append("the sender's domain (%s) carries the company name" % d)

    # 4 — THE NAMED CONTACT, in any header. A deal records who we deal with; a message to or from
    # that person is about that relationship even when they write from a personal address.
    contact = str(deal.get("contact") or "").strip().lower()
    cmail = re.findall(r"[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", contact)
    if cmail and any(a in hay for a in cmail):
        sc += 4
        ev.append("the deal's contact (%s) is on the message" % cmail[0])

    # 3 — THE COMPANY NAME, anywhere in the message.
    if cwords and all(w in hay for w in cwords[:2]):
        sc += 3
        ev.append("the company's name appears in the message")

    # 2 — THE DEAL REFERENCE. We put it in subjects ourselves, so when it comes back in a reply
    # chain it is conclusive about which deal - but only we ever write it, so it is not enough
    # alone to decide a message somebody else started.
    did = str(deal.get("deal_id") or "")
    if len(did) >= 10 and did.lower() in hay:
        sc += 2
        ev.append("the deal reference (%s) is in the message" % did)

    # 2 — THE TITLE. Three significant words, so "Partnership" alone proves nothing.
    tw = _sig_words(deal.get("title"))
    hit = [w for w in tw if w in subj.lower()]
    if len(hit) >= 3 or (tw and len(hit) >= 2 and len(tw) <= 3):
        sc += 2
        ev.append("the subject carries the deal title (%s)" % ", ".join(hit[:4]))

    # 1 — TIME. It cannot be about a deal that had not been opened yet.
    ts = float(msg.get("ts") or 0)
    if ts and opened:
        if ts < opened - 86400:
            return 0, ["the message predates the deal"]
        if ts - opened <= WINDOW_DAYS * 86400:
            sc += 1
            ev.append("it arrived %d day(s) after the deal was opened"
                      % int((ts - opened) / 86400))
    return sc, ev


def match(msg, deals, now=None, min_score=None):
    """Which deal is this message about? {deal_id, score, evidence, why_not} — never raises."""
    floor = MIN_SCORE if min_score is None else int(min_score)
    scored = []
    for d in deals or []:
        try:
            s, ev = score_row(msg, d, now)
        except Exception:
            s, ev = 0, []
        if s >= floor:
            scored.append((s, float(d.get("updated_ts") or d.get("created_ts") or 0), d, ev))
    if not scored:
        return {"deal_id": "", "score": 0, "evidence": [],
                "why_not": "no deal matched strongly enough (floor %d)" % floor}
    scored.sort(key=lambda t: (-t[0], -t[1]))
    best = scored[0]
    if len(scored) > 1 and scored[1][0] == best[0]:
        tied = [t[2].get("company") or t[2].get("deal_id") for t in scored[:3]]
        return {"deal_id": "", "score": best[0], "evidence": best[3],
                "why_not": "two deals match equally well (%s) - not filing it under either"
                           % ", ".join(str(x) for x in tied[:2])}
    return {"deal_id": best[2].get("deal_id") or "", "score": best[0], "evidence": best[3],
            "why_not": ""}


def classify(msg):
    """What KIND of message is this? LABELLING ONLY. It never decides a match and it never moves a
    card: the gates in the process map are signature events, and an email that says "NDA" is not an
    NDA that was signed. The operator moves the card; this only helps them find it."""
    s = (str(msg.get("subject") or "") + " " + str(msg.get("snippet") or "")).lower()
    if re.search(r"\b(nda|non[- ]disclosure|confidentiality agreement)\b", s):
        return "nda"
    if re.search(r"\b(mpa|master partner|partner agreement|reseller agreement|distribution "
                 r"agreement)\b", s):
        return "agreement"
    if re.search(r"\b(loi|letter of intent)\b", s):
        return "loi"
    if re.search(r"\b(poc|pov|proof of concept|proof of value|pilot)\b", s):
        return "poc"
    if re.search(r"\b(signed|countersigned|docusign|e-?sign|executed copy)\b", s):
        return "signature"
    if re.search(r"\b(invoice|purchase order|\bPO\b|payment|remittance)\b", s, re.I):
        return "invoice"
    if re.search(r"\b(price|pricing|quote|quotation|discount|tier|margin)\b", s):
        return "pricing"
    if re.search(r"\b(meeting|call|calendly|invite|agenda|reschedul)\b", s):
        return "meeting"
    return "mail"


# --------------------------------------------------------------------------- self-test
def _selftest():
    fails = []

    def ck(name, cond, detail=""):
        print(("  ok   " if cond else "  FAIL ") + name + ((" - " + detail) if detail else ""))
        if not cond:
            fails.append(name)

    now = time.time()
    day = 86400.0
    deals = [
        {"deal_id": "20260901-projectale", "company": "Projectale", "domain": "objectale.ch",
         "contact": "ud@objectale.ch", "title": "Swiss distribution agreement",
         "created_ts": now - 90 * day, "updated_ts": now - 2 * day},
        {"deal_id": "20261001-new-cognito", "company": "New Cognito", "domain": "newcognito.co.ao",
         "contact": "", "title": "Angola POV", "created_ts": now - 40 * day,
         "updated_ts": now - 5 * day},
    ]

    m = {"from": "Urs <ud@objectale.ch>", "subject": "Re: Swiss distribution agreement - signed",
         "snippet": "Attached the countersigned MPA.", "ts": now - day}
    r = match(m, deals)
    ck("a partner's own reply lands on their deal", r["deal_id"] == "20260901-projectale",
       "%s %s" % (r["deal_id"], r["evidence"]))
    ck("and it SAYS why", len(r["evidence"]) >= 2, str(r["evidence"]))

    news = {"from": "Africa Telecoms <news@telecomreview.africa>",
            "subject": "New Cognito expands into Zambia",
            "snippet": "New Cognito announced...", "ts": now - day}
    ck("a newsletter that merely NAMES the company is not a match",
       match(news, deals)["deal_id"] == "", match(news, deals)["why_not"])

    old = dict(m, ts=now - 200 * day)
    ck("a message that predates the deal is refused outright",
       match(old, deals)["deal_id"] == "", match(old, deals)["why_not"])

    tie = [dict(deals[0]), dict(deals[0], deal_id="20260901-projectale-2")]
    r4 = match(m, tie)
    ck("two deals that match equally well leave it UNFILED, with the reason",
       r4["deal_id"] == "" and "equally well" in r4["why_not"], r4["why_not"])

    gmail = {"from": "Urs Dietrich <urs.privat@gmail.com>",
             "to": "jev@s4biz.io, ud@objectale.ch",
             "subject": "quick question", "snippet": "about Projectale next steps",
             "ts": now - 3 * day}
    ck("a partner writing from a personal address still matches via the named contact",
       match(gmail, deals)["deal_id"] == "20260901-projectale",
       str(match(gmail, deals)["evidence"]))

    ck("a generic domain alone files nothing",
       match({"from": "a@gmail.com", "subject": "hello", "ts": now}, deals)["deal_id"] == "")

    ck("norm() collapses legal suffixes", norm("Stars4business OÜ") == norm("stars4business"),
       "%r vs %r" % (norm("Stars4business OÜ"), norm("stars4business")))
    ck("domain_of reads a display-name address",
       domain_of("Urs <ud@objectale.ch>") == "objectale.ch")
    ck("registrable trims the host", registrable("mail.eu.objectale.ch") == "objectale.ch")

    ck("an NDA is labelled", classify({"subject": "Mutual NDA for signature"}) == "nda")
    ck("a partner agreement is labelled",
       classify({"subject": "Master Partner Agreement draft"}) == "agreement")
    ck("an LOI is labelled", classify({"subject": "Letter of Intent"}) == "loi")
    ck("a POV is labelled", classify({"subject": "POV scope for Angola"}) == "poc")
    ck("pricing is labelled", classify({"subject": "Your tier and margin"}) == "pricing")
    ck("anything else is just mail, never a guess", classify({"subject": "hello there"}) == "mail")

    # THE RULE THAT MATTERS MOST, asserted rather than trusted: a label must never move a card.
    # The gates in the process map are signature events; an email SAYING "NDA" is not an NDA that
    # was signed, and a board that advanced itself on vocabulary would be fiction within a week.
    import inspect
    src = inspect.getsource(match) + inspect.getsource(score_row)
    ck("the matcher never consults the label", "classify" not in src)
    ck("and it never writes a stage", "stage" not in src)

    print("dealmatch selftest: %d check(s) failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
