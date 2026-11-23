#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dealreg_panel.py — the four-model second opinion on "are these two registrations the same deal?"

WHAT IT IS FOR, AND WHAT IT IS NOT ALLOWED TO DO.
    `dealreg.duplicate_of()` decides. It compares registrable domain + country + product line
    inside an active protection window, and the partner who loses protection loses it to THAT, not
    to a model. This module exists because that key is exact and the world is not: a subsidiary
    registered under its own name and its own domain, a typo, a holding company, a reseller who
    typed the customer's marketing site instead of their corporate one. Those are REAL duplicates
    the key cannot see, and a programme that misses them pays a partner twice for one deal and
    then has to take one of the payments back.

    So the panel may do exactly two things:
      1. RAISE A FLAG on a pair the key did not match, for a HUMAN to look at. The flag changes
         nothing on its own - the registration keeps whatever state the deterministic path gave it.
      2. WRITE the plain-language reply the partner reads, from facts the code supplies.

    It may not approve, reject, expire, or mark anything a duplicate. `apply()` below is the only
    way its output reaches the database and it writes to ONE column, `panel`, which no decision
    reads. That is asserted by test, because this is exactly the boundary that erodes: the model is
    right often enough that wiring it to the verdict starts to feel like an improvement, and then
    a partner loses a deal to a sentence nobody can audit.

    Same doctrine as the engine's FP auditor ("an audit is a SIGNAL, not an authority; the auditor
    is never the author") and perseus/vet.py (models propose, code decides). This is the third
    place in the estate that needed it, which is why it is written out rather than assumed.

WHY FOUR, AND WHY FROM FOUR VENDORS. `enrich._FALLBACKS` is the one home for the chain and it is
    four models from four vendors precisely so a wrong answer is not a shared failure domain. A
    single model asked "are these the same company?" is confidently wrong in a way that correlates
    with how the question is phrased; four from four vendors disagreeing is the signal that a human
    should look. The quorum rule below is deliberately asymmetric: agreement is needed to RAISE a
    flag, never to clear one.
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _chain():
    """The live chain, read from its ONE home. Never a list retyped here (class 32)."""
    for p in ("/opt/shodan-skill/scripts",
              os.path.join(HERE, "..", "..", "..", "hermes-skills", "shodan-assessment",
                           "scripts")):
        p = os.path.abspath(p)
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    import enrich
    return list(getattr(enrich, "MODELS", None) or enrich._FALLBACKS), enrich


PROMPT = """You are reviewing two DEAL REGISTRATIONS submitted to a cybersecurity vendor by two
different resellers. Decide whether they describe THE SAME SALES OPPORTUNITY at the same end
customer, or two DIFFERENT opportunities that happen to involve the same customer.

Two registrations are the SAME opportunity when they concern the same end customer AND the same
purchase: the same product line, overlapping timing, the same project.

They are DIFFERENT when the customer is the same but the purchase is not: a different product
line, a different business unit with its own budget, a renewal versus a net-new project, or
projects whose expected close dates are far apart.

You are NOT deciding who gets the deal, and nothing you write changes either registration. A human
reads your answer. If you are unsure, say unsure - an unsure answer is useful and a confident wrong
one is not.

Answer with STRICT JSON and nothing else:
{"same": true|false|null, "confidence": "high"|"medium"|"low", "why": "<one or two sentences
naming the specific facts you relied on>"}

REGISTRATION A:
%s

REGISTRATION B:
%s
"""


def _slim(reg):
    """ONLY the fields the question needs. The model never sees the owner, the value or the
    contact: it is answering "same opportunity?", and a reseller's identity or a deal's size is not
    evidence for that. It is also the minimisation the dual-distribution information-exchange
    exposure calls for - a model prompt is a place data goes, and the fewer commercially sensitive
    fields leave the store the smaller that surface is."""
    return {"company": reg.get("company", ""), "domain": reg.get("domain", ""),
            "country": reg.get("country", ""), "product": reg.get("product", ""),
            "description": (reg.get("description") or "")[:800],
            "close_date": reg.get("close_date", ""), "stage": reg.get("stage", "")}


def ask(a, b, chain=None, call=None):
    """Ask every model in the chain. Returns one record per model - including the ones that failed,
    BY NAME, because "three of four answered" and "four of four answered" are different evidence
    and a panel that silently shrinks is the two-model quorum this estate has already shipped once.
    """
    models, enrich = (chain, None) if chain else _chain()
    prompt = PROMPT % (json.dumps(_slim(a), indent=2, ensure_ascii=False),
                       json.dumps(_slim(b), indent=2, ensure_ascii=False))
    out = []
    for m in models:
        try:
            if call is not None:
                raw = call(m, prompt)
            else:
                raw = enrich._call(m, prompt)            # the ONE metered chokepoint
            txt = raw if isinstance(raw, str) else json.dumps(raw)
            d = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            same = d.get("same")
            out.append({"model": m,
                        "same": same if same in (True, False, None) else None,
                        "confidence": str(d.get("confidence", "") or "").lower(),
                        "why": str(d.get("why", ""))[:400]})
        except Exception as e:
            out.append({"model": m, "same": None, "confidence": "",
                        "why": "", "error": "%s: %s" % (type(e).__name__, str(e)[:120])})
    return out


def verdict(answers, deterministic_hit):
    """Turn the panel into ONE of three outcomes, none of which is a decision.

    AGREEMENT IS REQUIRED TO RAISE A FLAG, NEVER TO CLEAR ONE, and the asymmetry is the whole
    design. A flag costs a human five minutes. NOT flagging a real duplicate costs a partner a deal
    and costs us the credibility of the programme. So:

      * the deterministic key already matched -> nothing to add; the code has decided.
      * at least two models say SAME and none says DIFFERENT with high confidence -> FLAG.
      * anything else -> quiet.

    An `unsure` or a crashed model counts as neither agreement nor objection. A panel where three
    models errored and one said "same" does not reach two and stays quiet, which is correct: that
    is one model's opinion wearing a panel's clothes.
    """
    answered = [a for a in answers if not a.get("error")]
    same = [a for a in answered if a.get("same") is True]
    diff_hi = [a for a in answered if a.get("same") is False and a.get("confidence") == "high"]
    if deterministic_hit:
        return {"flag": False, "reason": "the deterministic key already matched; code decided",
                "answered": len(answered), "agree_same": len(same)}
    if len(same) >= 2 and not diff_hi:
        return {"flag": True,
                "reason": ("%d of %d models that answered read these as the same opportunity, and "
                           "the domain/country/product key did not match them. A human should "
                           "look: this is the subsidiary-and-typo case the key cannot see."
                           % (len(same), len(answered))),
                "answered": len(answered), "agree_same": len(same),
                "why": [a["why"] for a in same if a.get("why")][:4]}
    return {"flag": False, "reason": "no quorum to flag", "answered": len(answered),
            "agree_same": len(same)}


def apply(reg_id, answers, v, db=None):
    """Write the panel's output where NOTHING reads it for a decision.

    ONE column, `panel`, on the registration. No state change, no expiry, no duplicate marking. If
    a future change makes a decision path read this column, the guard in tests/test_dealreg.py
    fails - that test is the real enforcement and this docstring is only the explanation.
    """
    import dealreg
    path = db or dealreg.db_path()
    blob = json.dumps({"answers": answers, "verdict": v}, ensure_ascii=False)
    c = sqlite3.connect(path, timeout=30)
    try:
        c.execute("UPDATE regs SET panel=? WHERE id=?", (blob, reg_id))
        c.execute("INSERT INTO events(reg_id, ts, actor, kind, detail) VALUES(?,?,?,?,?)",
                  (reg_id, __import__("time").time(), "panel",
                   "panel_flag" if v.get("flag") else "panel_quiet", v.get("reason", "")[:400]))
        c.commit()
    finally:
        c.close()
    return v


def review(candidate, others, call=None, chain=None):
    """The whole second opinion for one new registration, against the ones the key did NOT match.

    Bounded on purpose: the panel is asked about the most recent few candidates, not every
    registration ever filed. An unbounded LLM sweep over a growing table is a bill that grows with
    the table, and `llm_meter` would stop it at the budget anyway - better to be deliberate here
    than to be cut off mid-sweep somewhere unpredictable.
    """
    import dealreg
    pool = [o for o in others
            if o.get("id") != candidate.get("id")
            and o.get("state") in ("approved", "review", "submitted")
            and dealreg.match_key(o) != dealreg.match_key(candidate)][:5]
    found = []
    for other in pool:
        answers = ask(candidate, other, chain=chain, call=call)
        v = verdict(answers, deterministic_hit=False)
        if v.get("flag"):
            v["other_id"] = other.get("id")
            found.append({"answers": answers, "verdict": v})
    return found


if __name__ == "__main__":                 # LAST STATEMENT IN THE FILE (class 48)
    print(json.dumps({"chain": _chain()[0]}, indent=2))
