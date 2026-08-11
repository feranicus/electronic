#!/usr/bin/env python3
"""build_competitive_deck.py — cybergod.ai against the market, honestly.

    python marketing/build_competitive_deck.py [--out PATH] [--template PATH]

SOURCES, ALL READ BEFORE A SINGLE SLIDE WAS WRITTEN:
  · Gartner, Magic Quadrant for Cyberthreat Intelligence Technologies, G00839252, 4 May 2026
    (the reprint the operator supplied). 17 vendors, placements extracted from the document itself.
  · The cybergod.ai partner and regulator deep dive (price list, delivery model, positioning).
  · cybergod.ai's own repository and event log for every operating number.
  · Third-party market estimates for vendors that publish no list price. LABELLED AS SUCH on the
    slide, because two of the sources found disagreed with each other by an order of magnitude.

THE TWO JUDGEMENTS THIS DECK MAKES, and the operator explicitly asked for them:

1. QUALYS, TENABLE AND RAPID7 ARE NOT OUR COMPETITORS. They sell vulnerability and exposure
   management: agents, scanners, credentials, deployment INSIDE the customer estate, priced per
   asset per year. cybergod.ai sends no packets, needs no access and is priced per run. A buyer
   choosing between them is not choosing between us. They appear here once, as an adjacency, and
   the deck says why rather than inflating the field to look impressive.

2. WE ARE NOT IN THE CTI MAGIC QUADRANT, AND ON TODAY'S CRITERIA WE WOULD NOT QUALIFY. The
   mandatory feature for that market is IoC coverage with maliciousness ratings and enrichment.
   We do not produce IoCs. Claiming a place on that chart would be the exact unsupported claim the
   engine's own design forbids.

NO LONG DASHES in any rendered string (operator standing rule).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from build_consensus_business_deck import table  # noqa: E402

FOOT = ("S4BIZ GROUP · CYBERGOD LLC · COMPETITIVE ANALYSIS · AUG 2026 · "
        "INTERNAL SALES MATERIAL, NOT FOR CUSTOMER DISTRIBUTION")
TITLE_MAX = 50


def _title(d, eyebrow, title, tail, sub, footer=FOOT):
    """Emit a slide, validating the title row width first.

    THE BUG THIS REPLACES: the first version checked the length and returned only the TITLE, and
    every call site passed just that, so the violet tail ("We are not one.") was silently dropped
    on all nine slides and the headlines rendered as fragments. The code looked perfectly
    reasonable; only the render showed it. Same class as every other defect in this repository, a
    helper whose contract was assumed rather than read.
    """
    n = len(title) + len(tail or "")
    if n > TITLE_MAX:
        raise SystemExit("[X] title row is %d chars and wraps onto the sub-heading (max %d): %r"
                         % (n, TITLE_MAX, title + (tail or "")))
    return d.slide(eyebrow, title, tail, sub=sub, footer=footer)


def build(template, out):
    d = Deck(template)

    # =============================================================== 01 TITLE
    d.slide("competitive analysis · august 2026",
            [("WHO WE BEAT.", WHITE), ("WHO BEATS US.", RED),
             ("AND WHO IS NOT", CYAN), ("EVEN IN THE RACE.", CYAN)],
            hero=True, footer=FOOT)

    # =============================================================== 02 THE CATEGORY QUESTION
    s = _title(d, "first, the honest part",
                "Three of the five names ", "are not rivals",
                sub="Vulnerability management and outside-in assessment are different businesses.")
    card(s, 0.55, 2.00, 3.90, 2.74, "not a competitor", RED, "Qualys · Tenable · Rapid7",
         "Vulnerability and exposure management. Agents, scanners, credentials, deployment inside "
         "the customer estate, priced per asset per year.\n\nThey answer what is wrong INSIDE my "
         "network. We answer what the internet can already see about this company, with no access "
         "at all.\n\nA buyer choosing them is not choosing between them and us.", bsize=9.2)
    card(s, 4.72, 2.00, 3.90, 2.74, "adjacent", AMBER, "Where they do touch us",
         "All three now ship an external attack surface module: Tenable ASM, Rapid7 Surface "
         "Command, Qualys CSAM. Those overlap our discovery.\n\nBut they are sold as an add-on to "
         "an existing platform contract, to a customer who already deployed the agents. The "
         "expansion motion is theirs. The cold prospect motion is ours.", bsize=9.2)
    card(s, 8.89, 2.00, 3.90, 2.74, "the real field", CYAN, "Outside-in, no deployment",
         "Bitsight. SecurityScorecard. Recorded Future. Palo Alto Cortex Xpanse. And the one that "
         "actually wins most of these deals today: a Big 4 or SI consultant with a spreadsheet and "
         "six weeks.\n\nThose five are the comparison that follows.", bsize=9.2)
    _tb(s, 0.55, 4.92, 12.20, 0.60,
        "Inflating the competitor list to look impressive is how a deck loses a technical audience "
        "in the first five minutes. Say who you do not compete with, and the rest is believed.",
        11, MUTED, TEXT, space=1.24)

    # =============================================================== 03 THE MQ, AND WHERE WE ARE NOT
    s = _title(d, "gartner cti mq · g00839252 · 4 may 2026",
                "17 vendors on the chart. ", "We are not one.",
                sub="Read the reprint. On the mandatory criteria we would not qualify today.")
    table(s, 0.55, 2.00, 7.40,
          ["Quadrant", "Vendors named by Gartner (2026 CTI MQ)"],
          [["LEADERS", "CrowdStrike · Google · Group-IB · Recorded Future · ZeroFox"],
           ["CHALLENGERS", "Cyble · Flashpoint"],
           ["VISIONARIES", "Bitsight · CYFIRMA · NSFOCUS · ReliaQuest · SOCRadar"],
           ["NICHE PLAYERS", "Axur (Infoblox) · CTM360 · Flare · Intel 471 · KELA"]],
          [0.26, 0.74], size=9.6, rh=0.50)
    card(s, 8.30, 2.00, 4.45, 2.55, "why we are absent", RED, "We do not make IoCs",
         "The mandatory feature for this market is indicator coverage (IPs, URLs, domains, hashes) "
         "with maliciousness ratings and enrichment. We produce none of that.\n\nWe consume public "
         "sources and write a board document. That is a different product, and claiming a place on "
         "this chart would be the sort of unsupported claim our own engine is built to refuse.",
         bsize=9.2)
    _rect(s, 0.55, 4.72, 12.20, 0.78, INK, AMBER, 1.4)
    _tb(s, 0.80, 4.84, 11.70, 0.58,
        "GARTNER'S OWN PLANNING ASSUMPTION, AND IT POINTS AWAY FROM US: by 2028 more than 50% of "
        "organisations adopting CTI will prioritise platforms that operationalise intelligence "
        "through automated rule generation, enforcement and takedown, over those that primarily "
        "deliver enrichment and reporting. We are reporting. That is a real strategic risk, on "
        "slide three rather than buried.", 9.5, BODY, TEXT, space=1.22)

    # =============================================================== 04 HEAD TO HEAD
    s = _title(d, "head to head",
                "The five that actually ", "sit opposite us",
                sub="Green is ours. Red is theirs. Most rows are not close in either direction.")
    table(s, 0.55, 1.96, 12.20,
          ["Capability", "cybergod", "Bitsight", "SecScorecard", "Recorded Fut.", "Cortex Xpanse", "Big 4 / SI"],
          [["Time to first board document", "5 to 7 min", "days", "days", "days", "days", "4 to 8 weeks"],
           ["Needs deployment or access", "none", "none", "none", "none", "none", "full access"],
           ["Packets sent to the target", "zero", "some", "some", "zero", "active scan", "n/a"],
           ["Continuous monitoring", "no", "yes", "yes", "yes", "yes", "no"],
           ["Own primary threat collection", "no", "partial", "partial", "yes", "partial", "no"],
           ["Risk quantified in euros", "yes", "partial", "partial", "no", "no", "yes"],
           ["Regulatory module (NIS2/CRA/AI Act)", "yes", "no", "no", "no", "no", "yes"],
           ["Adversarial multi-model review", "4 models", "no", "no", "no", "no", "peer review"],
           ["White-label to partner brand", "yes", "no", "no", "no", "no", "n/a"],
           ["Published list price", "yes", "no", "no", "no", "no", "day rate"]],
          [0.30, 0.118, 0.118, 0.118, 0.118, 0.118, 0.11], size=8.6, rh=0.345)

    # =============================================================== 05 WHERE WE WIN
    s = _title(d, "where we are better",
                "Speed, cost, and the ", "shape of the output",
                sub="Every figure here is ours and measured, not a market estimate.")
    stat(s, 0.55, 2.05, 2.60, "5 to 7 min", "COMPANY NAME TO FOUR\nBOARD DECKS", CYAN)
    stat(s, 3.35, 2.05, 2.60, "€100", "LIST PRICE PER RUN\nPARTNER FLOOR €60", CYAN)
    stat(s, 6.15, 2.05, 2.60, "~$0.005", "OUR AI COST PER RUN\nFROM THE COST LEDGER", GREEN)
    stat(s, 8.95, 2.05, 3.80, "0 packets", "SENT TO THE ASSESSED COMPANY\nNO AUTHORISATION NEEDED", GREEN)
    bullets(s, 0.55, 3.45, 12.20, [
        "THE OUTPUT IS A MEETING, NOT A DASHBOARD. Four pptx decks and an animated HTML report, in "
        "English, German or Russian. Ratings vendors hand an analyst a score and a portal; we hand "
        "a seller something they can open in front of a board.",
        "ZERO PACKETS MEANS NO PERMISSION. We can assess a PROSPECT before first contact. Every "
        "scanner-based competitor needs authorisation, which means the deal has already started.",
        "RISK IN EUROS, NOT A LETTER GRADE. C-BIQ converts each finding to an annual loss figure "
        "using the same maths an insurer prices with. A score of 720 does not survive a CFO.",
        "REGULATION IS IN THE PRODUCT. NIS2, CRA and the EU AI Act, plus OSFI, PIPEDA and Law 25 "
        "for Canada, graded per jurisdiction. None of the five ships this.",
    ], gap=0.62, size=10.2)

    # =============================================================== 06 WHERE WE LOSE
    s = _title(d, "where we are worse",
                "Six places a serious ", "buyer will push",
                sub="If this slide were missing, nothing else in the deck would be believable.")
    card(s, 0.55, 1.96, 3.90, 2.10, "gap 1", RED, "No continuous monitoring",
         "We are a point in time run. Bitsight and SecurityScorecard watch every day and alert on "
         "change. For a customer who wants to know when something NEW appears, we are the wrong "
         "product today.", bsize=9.2)
    card(s, 4.72, 1.96, 3.90, 2.10, "gap 2", RED, "No primary collection",
         "We read Shodan, Certificate Transparency and public DNS. Recorded Future, Google and "
         "CrowdStrike run their own dark web, malware and incident response collection. Our GEOPOL "
         "actor naming is model reasoning over public sources, and we say so.", bsize=9.2)
    card(s, 8.89, 1.96, 3.90, 2.10, "gap 3", RED, "No enforcement or takedown",
         "No detection rules, no blocking, no domain takedown. Gartner expects that to be the "
         "majority buying preference by 2028. This is the gap most likely to matter commercially.",
         bsize=9.2)
    card(s, 0.55, 4.20, 3.90, 1.94, "gap 4", AMBER, "No portfolio view",
         "Ratings vendors score thousands of third parties continuously for one customer. We assess "
         "one company per run.", bsize=9.2)
    card(s, 4.72, 4.20, 3.90, 1.94, "gap 5", AMBER, "No analyst desk",
         "No RFI service, no named intelligence analyst, no 24/7 support organisation behind the "
         "product.", bsize=9.2)
    card(s, 8.89, 4.20, 3.90, 1.94, "gap 6", AMBER, "No third-party assurance",
         "No Gartner placement, no SOC 2 or ISO 27001 certification, one region. A regulated buyer "
         "will ask for all three.", bsize=9.2)

    # =============================================================== 07 HOW WE ARE DIFFERENT
    s = _title(d, "the actual difference",
                "We do not sell to ", "the CISO",
                sub="Everyone else sells the risk team a subscription. We arm the person walking in.")
    card(s, 0.55, 2.02, 5.95, 2.35, "them", MUTED, "A platform for the defender",
         "Bought by the security or risk function, for their own estate or their own vendor "
         "portfolio. Annual subscription. Success looks like a dashboard somebody logs into on "
         "Monday. Sales cycle measured in quarters, and it starts after the relationship exists.",
         bsize=9.6)
    card(s, 6.75, 2.02, 6.00, 2.35, "us", CYAN, "A door opener for the seller",
         "Bought by an MSP, VAR, integrator or consultancy, about a company they do not yet have a "
         "relationship with. Priced per run so a first meeting costs 100 euros. Success looks like "
         "a second meeting. White-labelled, so the client sees the partner and not us.", bsize=9.6)
    _rect(s, 0.55, 4.52, 12.20, 1.70, INK, INDIGO, 1.6)
    _tb(s, 0.80, 4.66, 11.70, 0.24,
        "AND THE MECHANISM NOBODY ELSE HAS: FOUR MODELS, FOUR VENDORS", 9.5, INDIGO, MONO, True)
    _tb(s, 0.80, 4.94, 11.70, 1.16,
        "deepseek-3.2 · llama-4-maverick · gemma-4-31B-it · kimi-k2.6. Two write, two audit, and "
        "the auditor is never the author or the author's vendor, so a provider outage or a shared "
        "blind spot cannot take the whole review with it. Code decides every side effect; the "
        "models explain, argue and get overruled by arithmetic. Every invented CVE is stripped by a "
        "post-check before it can reach a slide, and the whole chain is chosen by measurement on "
        "the real prompt rather than by benchmark. Competitors run one model, or none.",
        9.6, BODY, TEXT, space=1.24)

    # =============================================================== 08 PRICE
    s = _title(d, "price",
                "Ours is published. ", "Theirs mostly is not.",
                sub="Which is itself the finding. Two sources for the same vendor disagreed 10x.")
    table(s, 0.55, 1.98, 12.20,
          ["Offer", "What it costs", "Source quality"],
          [["cybergod.ai, one run", "€100 list · €60 at Platinum partner tier", "PUBLISHED, ours"],
           ["cybergod.ai, report subscription", "€200 per month list · €120 partner floor", "PUBLISHED, ours"],
           ["cybergod.ai, findings review", "€200 per hour · workshop €2,500 per day", "PUBLISHED, ours"],
           ["Bitsight / SecurityScorecard", "not published. Enterprise quote only", "no public list"],
           ["Recorded Future", "not published. Commonly cited five figures per year", "third-party, unverified"],
           ["Cortex Xpanse", "not published. Quoted with the platform", "no public list"],
           ["Qualys / Tenable / Rapid7 (adjacent)", "roughly $17 to $38 per asset per year", "third-party estimate"],
           ["Big 4 or SI, NIS2 readiness", "€20,000 to €200,000 per engagement", "market rate card"],
           ["Germany's own NIS2 impact estimate", "€70,000 once, then €30,000 a year per entity", "legislative estimate"]],
          [0.34, 0.42, 0.24], size=9.0, rh=0.395)
    # THE NOTE SITS BELOW THE LAST ROW, NOT ON IT. Nine rows at 0.395 plus the 0.40 header ends
    # at 5.93, so the note starts at 6.04. The first version put it at 5.94 against 0.42 rows,
    # which is 6.16, and it printed straight through the final line.
    _tb(s, 0.55, 6.06, 12.20, 0.46,
        "Do not quote a competitor's price from this slide. Where a vendor publishes nothing, the "
        "numbers in circulation are resale blogs that contradict each other. The defensible line in "
        "a meeting is that ours is on a public price list and theirs is not.",
        9.4, AMBER, TEXT, space=1.22)

    # =============================================================== 09 DEAL BY DEAL
    s = _title(d, "who wins which deal",
                "Pick the fight ", "you win",
                sub="Told honestly, this is a qualification tool rather than a comparison chart.")
    table(s, 0.55, 1.98, 12.20,
          ["The buyer's actual question", "Who wins", "Why"],
          [["I need a board document about a prospect by Thursday", "CYBERGOD", "Minutes, 100 euros, no access needed"],
           ["I want my partner's logo on the assessment", "CYBERGOD", "White-label is in the model"],
           ["Am I ready for NIS2, and by when", "CYBERGOD", "Regulation graded per jurisdiction"],
           ["Tell me the moment something new is exposed", "BITSIGHT / SSC", "Continuous monitoring, we are point in time"],
           ["Score 4,000 suppliers every day", "BITSIGHT / SSC", "Portfolio scale is their whole product"],
           ["Who is targeting my sector, from primary sources", "RECORDED FUTURE", "They own the collection, we read public data"],
           ["Find every unknown asset across a global estate", "CORTEX XPANSE", "Years of internet-wide scan data"],
           ["Fix what is broken inside my network", "TENABLE / QUALYS", "Different market, not our fight"],
           ["I need a signed opinion my regulator accepts", "BIG 4", "Liability and attestation, which we do not offer"]],
          [0.46, 0.19, 0.35], size=9.2, rh=0.42)

    # =============================================================== 10 WHAT WOULD CHANGE THIS
    s = _title(d, "the roadmap that changes the answer",
                "Four builds ", "and the field narrows",
                sub="Ordered by how much competitive ground each one actually buys.")
    bullets(s, 0.55, 2.05, 12.20, [
        "CONTINUOUS RE-RUN AND CHANGE ALERTING. Closes gap 1, the one a buyer raises first. The "
        "engine already runs in minutes for a fraction of a cent, so this is scheduling and diffing "
        "rather than new science. Highest return of anything on this list.",
        "TAKEDOWN AND ENFORCEMENT WORKFLOW. Directly addresses Gartner's 2028 assumption. Partly "
        "built already: the active defence shield blocks and reports on our own estate, which is "
        "the mechanism, pointed at ourselves rather than at a customer.",
        "THIRD-PARTY PORTFOLIO MODE. One partner, many assessed companies, one view. Mostly a "
        "product surface over the engine we have, and it opens the supplier-risk budget.",
        "INDEPENDENT ASSURANCE. ISO 27001 or SOC 2, and a second region. Buys nothing technically "
        "and unblocks every regulated buyer, which is why it belongs on the list.",
    ], gap=0.72, size=10.4)
    _rect(s, 0.55, 5.44, 12.20, 0.86, INK, GREEN, 1.4)
    _tb(s, 0.80, 5.58, 11.70, 0.62,
        "None of the four requires beating a Leader at their own game. Each one removes a reason to "
        "say no to a product that already wins on speed, price and the shape of what it hands you.",
        10, WHITE, TEXT, space=1.22)

    d.save(out)
    print("  wrote %s" % out)
    return 0


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Cybergod_Competitive_Analysis.pptx"))
    a = ap.parse_args()
    return build(a.template, a.out)


if __name__ == "__main__":
    sys.exit(main())
