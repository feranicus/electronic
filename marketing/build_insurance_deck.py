#!/usr/bin/env python3
"""build_insurance_deck.py — the FOUR-SLIDE proposal for insurers. Cyber underwriting, not IT.

    python marketing/build_insurance_deck.py

WHY THIS IS A SEPARATE BUILDER AND NOT A THIRD ENTRY IN build_sector_proposal_deck.py
    The legal and accounting 4-pagers sell the same story to two audiences: you cannot see
    yourself from the outside, we show you, we help you fix it, Perseus watches what comes next.
    One builder, one SECTORS dict, because the narrative is identical and only the wording moves.

    An insurer is not that buyer. The subject of the assessment is not the insurer, it is the
    applicant, the renewal, the subsidiary, the counterparty. The questions are different (can I
    price this risk, can I see it before I bind, can I do it across a book), the output they care
    about is the money page rather than the findings page, and the one property that makes it
    possible at all — we never contact the assessed company — is a footnote in the other decks
    and the entire product here.

    Folding that into SECTORS would have meant a dict where half the keys only apply to one
    entry, which is how a shared skeleton turns into an if-tree. Same template, same palette,
    same chrome helpers, same layout gate, different argument.

WHAT IS REUSED, DELIBERATELY
    The Deck class, the palette, the column arithmetic and `_panel` are imported, never copied.
    A second copy of _panel would drift from the first the moment one of them was corrected,
    and the operator's decks have to look like each other on the same table.

HONESTY (the rules these decks are held to)
    * Every number is traced to a measurement, named in the comment beside it.
    * DORA is NOT claimed. The compliance module ships NIS2, CRA and the EU AI Act for the EU and
      the OSFI set for Canada. OSFI B-10 explicitly covers foreign insurance branches, so the
      Canadian claim is real. The EU financial-sector regime is a gap and the deck says so.
    * Accumulation across a book is described as scoped, because the data is there and the
      product is not.
    * No named competitor, no named client, no CVE identifiers, no em dashes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    BODY, CYAN, Deck, DISPLAY, GREEN, INK, LINE, MONO, MUTED, TEXT, VIOLET, WHITE, _rect, _tb,
    stat,
)
from build_sector_proposal_deck import _panel  # noqa: E402  — ONE HOME for the card
from deck_chrome import W2, W3, W4, X2, X3, X4, assert_layout, guarded  # noqa: E402

OUT = "S4biz_Cybergod_Insurance_4pager"
FOOT = ("S4biz Group · Cybergod LLC · for insurers · confidential · "
        "not legal, tax or underwriting advice")


def build(template, out):
    d = guarded(Deck(template), tail=CYAN)

    # ======================================= 01  YOU PRICE WHAT YOU CANNOT SEE ================
    # The underwriting gap, in the insurer's own terms. Everything on this slide is about the
    # APPLICANT, never about the insurer's own IT, which is the mistake the first draft made.
    s = d.slide("proposal · cyber underwriting",
                [("YOU PRICE WHAT", WHITE), ("YOU CANNOT", WHITE), ("SEE.", CYAN)],
                footer=FOOT, hero=True)
    _tb(s, 0.57, 4.25, 11.60, 0.60,
        "Cyber risk is underwritten on what the applicant says about itself. We show you what the "
        "attacker already sees, before you bind, without ever contacting them.",
        14, BODY, TEXT, space=1.3)
    for i, (kick, head, body) in enumerate([
            ("THE PROPOSAL FORM", "Is self-reported",
             "It is answered by the people with the least incentive to find a problem, and often "
             "by someone who has never seen the estate from outside."),
            ("THE QUESTIONNAIRE", "Ages immediately",
             "It describes one day. Certificates expire, subsidiaries get bought, a test server "
             "goes public, and the policy runs for twelve months."),
            ("THE BROKER", "Has no technical view",
             "They can tell you the turnover and the sector. They cannot tell you that the mail "
             "archive is reachable from the internet.")]):
        _panel(s, X3[i], 5.15, W3, 1.72, kick, CYAN, head, body, hsize=16, bsize=10)

    # ============================================== 02  WHAT YOU GET PER RISK =================
    s = d.slide("what you get", "An underwriting file on",
                " any company",
                "One input: the company name. No consent, no questionnaire, no contact.", FOOT)
    for i, (kick, head, body) in enumerate([
            # HEADS ARE ONE LINE. At 14pt in a 2.87in column a two-line head pushes into the
            # body box and the card reads as a wall. Measured by rendering, not guessed.
            ("01 · THE EXPOSURE", "The whole estate",
             "Every server, service, domain and subsidiary reachable from the internet, including "
             "the ones the applicant does not know about. Shared hosting is called shared hosting "
             "rather than counted as theirs."),
            ("02 · THE MONEY", "Priced in euros",
             "Open FAIR, 10 000 Monte-Carlo runs. Expected annual loss per finding, and the "
             "probable maximum loss kept separate as a capital number rather than averaged away "
             "into the mean."),
            ("03 · THE THREAT", "Who targets them",
             "The groups active against companies like this one, named, with sources, so the "
             "frequency side of the model is argued rather than assumed. No sector inferred from "
             "a hosting provider's name."),
            ("04 · THE EVIDENCE", "The raw observation",
             "Every finding carries what was actually seen. Your reinsurer or your engineer can "
             "challenge any single number, and a lookup that failed is reported as unknown "
             "instead of as a risk.")]):
        _panel(s, X4[i], 2.05, W4, 2.85, kick, CYAN, head, body, hsize=14, bsize=9.5)

    # THE GREEN STRIP IS THE PRODUCT. In the legal and accounting decks this is reassurance. For
    # an insurer it is the commercial unlock: an assessment that needs no permission can be run
    # pre-bind, on a risk you have not yet quoted, and on one you decline.
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, GREEN, None)
    _tb(s, 0.80, 5.44, 11.70, 0.30, "NOT ONE PACKET REACHES THE APPLICANT", 9, GREEN, MONO, True)
    _tb(s, 0.80, 5.76, 11.70, 0.60,
        "We read only what the company already publishes to the world. Nothing is sent to their "
        "network, so no authorisation is needed and nobody is notified. That is what makes this "
        "usable before you quote, and on risks you never write.",
        12, BODY, TEXT, space=1.28)

    # ================================================== 03  ACROSS THE BOOK ===================
    s = d.slide("at portfolio scale", "The same file, for every",
                " risk you carry",
                "Four uses, one engine. The economics are what make all four possible.", FOOT)
    for i, (kick, head, body) in enumerate([
            ("PRE-BIND", "Triage before you quote",
             "Run the submission the day it arrives. Price it, load it, or decline it with a "
             "technical reason the broker can read."),
            ("RENEWAL", "What changed in a year",
             "Run it again and compare. A new exposure that appeared in month three is the one "
             "the proposal form will never mention."),
            ("THIRD PARTIES", "Outside your governance",
             "Subsidiaries, brokers, MGAs, outsourcers and their subcontractors. The same view, "
             "on companies you have no contract with.")]):
        _panel(s, X3[i], 2.05, W3, 2.25, kick, VIOLET, head, body, hsize=17, bsize=10.5)

    # EVERY NUMBER HERE IS MEASURED, AND THE SOURCE IS NAMED IN THIS COMMENT:
    #   10 000  -> run_assessment.py: "Monte-Carlo CRQ (10k runs)", the method string on the deck
    #   3m 27s  -> a real run (verint, 11 Nov 2026): assess_done total_ms = 206 956
    #   0       -> the engine's non-negotiable; active probing needs ACTIVE_PROBE=1 AND a written
    #              authorisation reference, so the default path cannot send a packet
    #   305     -> cost_snapshot on that same run: assessments_total = 305
    for i, (v, lab) in enumerate([("10 000", "Monte-Carlo runs\nbehind every price"),
                                  ("3m 27s", "one full assessment,\nend to end"),
                                  ("0", "packets sent to\nthe assessed company"),
                                  ("305", "assessments run\nto date")]):
        stat(s, 0.55 + i * 3.10, 4.65, 2.88, v, lab, col=CYAN, vsize=22)

    _rect(s, 0.55, 5.95, 12.23, 0.78, INK, LINE)
    _rect(s, 0.55, 5.95, 12.23, 0.06, GREEN, None)
    _tb(s, 0.80, 6.18, 11.70, 0.46,
        "ACCUMULATION: every assessment already records the hoster, the network and the country. "
        "Reading that across a whole book shows where your insureds share one provider. Scoped, "
        "not yet built, and priced as a project.", 11, BODY, TEXT, space=1.26)

    # =================================================== 04  HOW IT PLUGS IN ==================
    s = d.slide("how you run it", "Your brand, your portal,",
                " your regulator",
                "Nothing here asks you to send your submissions to a third-party score vendor.",
                FOOT)
    _panel(s, X2[0], 2.00, W2, 2.35, "WHITE LABEL", CYAN, "It comes out as yours",
           "Your colours, your templates, your logo on every page. The underwriter and the broker "
           "see your document, not ours. Portal and API integration is scoped work, quoted "
           "separately.", hsize=17, bsize=10.5)
    _panel(s, X2[1], 2.00, W2, 2.35, "WHERE IT RUNS", GREEN, "In the EU, on our own metal",
           "Frankfurt. Company name, email and timestamps are all we process, under Art. 6(1)(b) "
           "and (f), logs kept 30 days. Documents in English, German, Russian and Portuguese.",
           hsize=17, bsize=10.5)

    # THE REGIME CLAIM, EXACTLY AS THE CODE SUPPORTS IT. compliance_enrich.JURISDICTIONS ships
    # NIS2 / CRA / EU AI Act for the EU and the OSFI set for Canada, where B-10 names foreign
    # insurance branches explicitly. DORA is not in the registry. Claiming it here would be the
    # one lie an insurer's compliance officer is guaranteed to catch.
    _rect(s, 0.55, 4.60, 12.23, 1.35, INK, LINE)
    _rect(s, 0.55, 4.60, 12.23, 0.06, VIOLET, None)
    _tb(s, 0.80, 4.84, 11.70, 0.28, "THE COMPLIANCE MODULE, AND ITS LIMIT", 9, VIOLET, MONO, True)
    _tb(s, 0.80, 5.14, 11.70, 0.70,
        "Today the engine grades a company against NIS2, the Cyber Resilience Act and the EU AI "
        "Act, and against the OSFI guidelines for Canada, where B-10 covers third-party risk for "
        "foreign insurance branches. DORA is not in the module yet. We would rather say that here "
        "than have your compliance team find it.", 11, BODY, TEXT, space=1.26)

    # ONE LINE, AND THE BUILD PROVES IT. This wrapped on the first render and the second line
    # landed on top of the footer. assert_layout checks the DECLARED box, which is 0.24 high and
    # therefore innocent; what overflowed was the rendered text. Mono is the one font where that
    # arithmetic is sound, because every glyph is the same width, so the budget below is a
    # measurement rather than an estimate: the sister decks fit 97 characters in this same 8.40in
    # box at 9.5pt, so 95 is the line that cannot wrap.
    _price = ("Assessment EUR 100  ·  monitoring EUR 200 / month  ·  "
              "white label and volume scoped")
    assert len(_price) <= 95, "the price line will wrap onto the footer: %d chars" % len(_price)
    _tb(s, 0.55, 6.80, 8.40, 0.24, _price, 9.5, MUTED, MONO)
    _tb(s, 9.20, 6.80, 3.58, 0.24, "feranicus@s4biz.io  ·  cybergod.ai", 9.5, CYAN, MONO)

    assert_layout(d)
    d.save(out)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx")
    if not os.path.exists(template):
        raise SystemExit("[X] template not found: %s" % template)
    print("built:", build(template, os.path.join(here, OUT + ".pptx")))


if __name__ == "__main__":
    main()
