#!/usr/bin/env python3
"""build_sector_proposal_deck.py — the FOUR-SLIDE proposal. Legal and accounting, one builder.

    python marketing/build_sector_proposal_deck.py --sector legal
    python marketing/build_sector_proposal_deck.py --sector accounting

WHY THIS REPLACES THE 18 AND 19 SLIDE VERSIONS
    Operator verdict, verbatim: "awful, no one will understand anything its too complicated".
    He was right. Those decks were documents, not pitches. A partner or a managing director gets
    through four slides in a meeting; they do not read nineteen. Worse, neither deck NAMED our own
    security stack, which is the thing we are actually selling.

    Structure, in the operator's own words:
        1. today you do not know how your IT looks to a hacker from outside
        2. we give you that view, who is coming, what it costs, and every technical issue
        3. we run a workshop on how to fix it: your own tools, open source, or commercial
        4. Perseus Shield: you cannot protect what you cannot see, and it gives you both

ONE BUILDER, TWO SECTORS. The two decks share a skeleton and differ only in a SECTORS dict. That
is deliberate: the previous pair were separate files, and separate files drift. The sector-specific
content is real in each case and not a find-and-replace, but the layout arithmetic has one home.

HONESTY, unchanged from the long versions:
  * Perseus numbers are measured on our own front door and are labelled as ours.
  * Peer evidence is real, from assessments we ran, anonymised. No client is named.
  * List prices are the real ones. Simulation and stack are scoped, not invented.
  * No named competitor, no CVE identifiers, no em dashes.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    BODY, CYAN, Deck, DISPLAY, GREEN, INK, LINE, MONO, MUTED, TEXT, VIOLET, WHITE, _rect, _tb,
    stat,
)
from deck_chrome import W2, W3, W4, X2, X3, X4, assert_layout, guarded  # noqa: E402

SECTORS = {
    "legal": {
        "who": "law firms",
        "file": "S4biz_Cybergod_Legal_4pager",
        "hero": [("YOU CANNOT PROTECT", WHITE), ("WHAT YOU CANNOT", WHITE), ("SEE.", CYAN)],
        "lede": "Today nobody in your firm knows how it looks to an attacker from the outside. "
                "We show you, and then we help you close it.",
        "actors": "Ransomware and extortion groups that target law firms for the client files, "
                  "not for the firm.",
        "worst": "Client files copied and published. Backups do not help.",
        "found": "At one firm we found a mail archive with years of client correspondence, open "
                 "to the internet, on an expired certificate.",
    },
    "accounting": {
        "who": "accounting, audit and tax practices",
        "file": "S4biz_Cybergod_Accounting_4pager",
        "hero": [("YOU CANNOT PROTECT", WHITE), ("WHAT YOU CANNOT", WHITE), ("SEE.", CYAN)],
        "lede": "Today nobody in your practice knows how it looks to an attacker from the "
                "outside. We show you, and then we help you close it.",
        "actors": "Fraud groups that send payment instructions in your name, and ransomware "
                  "crews that go for payroll and client books.",
        "worst": "Money leaves your client's account, in your name.",
        "found": "At one group we found the mail system on an expired certificate across seven "
                 "ports, and subsidiaries nobody had ever checked.",
    },
}


def _panel(s, x, y, w, h, kicker, kcol, head, body, hsize=15, bsize=10.5):
    """A card with SHORT text. The long decks used three-sentence bodies and the operator could
    not read them at a glance, which is the whole point of a four-page proposal."""
    _rect(s, x, y, w, h, INK, LINE)
    _rect(s, x, y, w, 0.06, kcol, None)
    _tb(s, x + 0.24, y + 0.24, w - 0.48, 0.24, kicker.upper(), 9, kcol, MONO, True)
    _tb(s, x + 0.24, y + 0.54, w - 0.48, 0.34, head, hsize, WHITE, DISPLAY, True)
    _tb(s, x + 0.24, y + 0.96, w - 0.48, h - 1.18, body, bsize, BODY, TEXT, space=1.28)


def build(template, out, cfg):
    d = guarded(Deck(template), tail=CYAN)
    FOOT = "S4biz Group · Cybergod LLC · proposal · confidential · not legal or tax advice"

    # =========================================== 01  YOU CANNOT SEE YOURSELF FROM OUTSIDE =====
    s = d.slide("proposal · %s" % cfg["who"], cfg["hero"], footer=FOOT, hero=True)
    _tb(s, 0.57, 4.25, 11.60, 0.60, cfg["lede"], 14, BODY, TEXT, space=1.3)
    for i, (kick, head, body) in enumerate([
            ("YOUR IT TEAM", "Sees the inside",
             "They know the servers they built. Not what is reachable from the internet today."),
            ("YOUR FIREWALL", "Sees ports",
             "It cannot tell you which of your systems a stranger can find and open."),
            ("NOBODY AT ALL", "Sees the outside",
             "No one in your organisation has ever looked at you the way an attacker does.")]):
        _panel(s, X3[i], 5.15, W3, 1.72, kick, CYAN, head, body, hsize=16, bsize=10)

    # ================================================================ 02  WHAT WE GIVE YOU =====
    s = d.slide("what you get", "We show you what the",
                " attacker sees",
                "One input: your company name. Five minutes later you have all four of these.",
                FOOT)
    for i, (kick, head, body) in enumerate([
            ("01 · THE OUTSIDE VIEW", "Your whole landscape",
             "Every server, service and domain that is reachable from the internet. Including the "
             "ones nobody remembers."),
            ("02 · WHO IS COMING", "The groups targeting you",
             cfg["actors"] + " Named, with sources."),
            ("03 · WHAT IT COSTS", "Every issue, in euros",
             "What a breach would actually cost you, per finding. " + cfg["worst"]),
            ("04 · THE FULL DEPTH", "Every technical issue",
             "The complete list, with the evidence for each one, so your IT can act on it "
             "immediately.")]):
        _panel(s, X4[i], 2.05, W4, 2.85, kick, CYAN, head, body, hsize=14, bsize=9.5)

    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, GREEN, None)
    _tb(s, 0.80, 5.44, 11.70, 0.30, "AND WE NEVER TOUCH YOUR SYSTEMS", 9, GREEN, MONO, True)
    _tb(s, 0.80, 5.76, 11.70, 0.60,
        "Not one packet is sent to your network. We read only what you already publish to the "
        "world. " + cfg["found"], 12, BODY, TEXT, space=1.28)

    # ============================================================= 03  HOW YOU FIX IT ==========
    s = d.slide("what you get", "Then we show you how to",
                " fix it",
                "A workshop with your own team. Not a report you file and forget.", FOOT)
    for i, (kick, head, body) in enumerate([
            ("OPTION 1", "Your own tools",
             "Most findings can be closed with what you have already bought. We show your team "
             "exactly which setting, on which product."),
            ("OPTION 2", "Open source",
             "Free, proven tools where you own nothing today. We deploy them and teach your "
             "people to run them."),
            ("OPTION 3", "Commercial products",
             "Where the first two genuinely cannot do the job, we say so and name what will. We "
             "sell no licences, so the advice is ours, not a vendor's.")]):
        _panel(s, X3[i], 2.05, W3, 2.55, kick, VIOLET, head, body, hsize=17, bsize=11)

    _rect(s, 0.55, 4.90, 12.23, 1.60, INK, LINE)
    _rect(s, 0.55, 4.90, 12.23, 0.06, VIOLET, None)
    _tb(s, 0.80, 5.15, 11.70, 1.10,
        "You leave the workshop with a fix for every finding, a cost for every fix, and your own "
        "engineers able to do it. Then we run the assessment again and show you it is gone.",
        14, WHITE, TEXT, space=1.3)

    # ========================================================= 04  PERSEUS SHIELD: SEE + STOP ==
    s = d.slide("the defence", "Perseus Shield sees it",
                " and stops it",
                "A new defence layer for what comes next, after the findings are closed.", FOOT)
    _rect(s, 0.55, 2.00, 12.23, 0.80, INK, LINE)
    _rect(s, 0.55, 2.00, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 2.24, 11.70, 0.44,
        "You cannot protect what you cannot see. Perseus gives you both.",
        18, WHITE, DISPLAY, True)

    _panel(s, X2[0], 3.00, W2, 2.30, "IT SHOWS YOU", CYAN, "Every attack against you",
           "Who is probing you, which path they asked for, and when. 13 attack classes, live, on "
           "one screen. Most companies have never seen this about themselves.", hsize=17, bsize=11)
    _panel(s, X2[1], 3.00, W2, 2.30, "IT STOPS THEM", GREEN, "Automatically, in milliseconds",
           "Slow them down, then block them. Every block is timed and expires by itself. No "
           "firewall change, ever, and no AI decides who gets blocked.", hsize=17, bsize=11)

    for i, (v, lab) in enumerate([("156,511", "requests we read\non our own site"),
                                  ("2,253", "different sources\nin one window"),
                                  ("604", "of them were\nscanning us"),
                                  ("30 days", "watching only, before\nit blocks anything")]):
        stat(s, 0.55 + i * 3.10, 5.55, 2.88, v, lab, col=CYAN, vsize=22)

    _tb(s, 0.55, 6.80, 8.40, 0.24,
        "Assessment EUR 100  ·  monitoring EUR 200 / month  ·  workshop EUR 2 500 / day  ·  "
        "Perseus scoped", 9.5, MUTED, MONO)
    _tb(s, 9.20, 6.80, 3.58, 0.24, "feranicus@s4biz.io  ·  cybergod.ai", 9.5, CYAN, MONO)

    assert_layout(d)
    d.save(out)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--sector", choices=sorted(SECTORS), required=True)
    ap.add_argument("--template",
                    default=os.path.join(here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg = SECTORS[a.sector]
    out = a.out or os.path.join(here, cfg["file"] + ".pptx")
    if not os.path.exists(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    print("built:", build(a.template, out, cfg))


if __name__ == "__main__":
    main()
