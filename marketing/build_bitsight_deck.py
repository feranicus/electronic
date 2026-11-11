#!/usr/bin/env python3
"""build_bitsight_deck.py — cybergod.ai (Herkos) beside BitSight, for the Kisso meeting.

    python marketing/build_bitsight_deck.py [--out PATH] [--template PATH]

WHAT THIS DECK IS FOR
    A working session with someone who knows BitSight from the inside and has offered to (a) say
    where our differentiation is genuinely strong, (b) make an internal introduction if the
    technology is complementary, (c) sharpen our positioning, and (d) open investor doors including
    Singtel Innov8. The deck follows HIS agenda, point for point, because he wrote it.

THE RULE THIS DECK IS BUILT ON, AND IT IS THE REPO'S OWN
    "No unsubstantiated comparative claims." We have never benchmarked Herkos against BitSight.
    So this deck argues ARCHITECTURE and SCOPE, never superiority, and it says out loud where
    BitSight is ahead and where we do not play at all. In a room with a BitSight insider that is
    not modesty, it is the only position that survives ten minutes.

    Two capabilities he explicitly asked about — deep/dark-web intelligence and supply-chain
    assets — WE DO NOT HAVE. Measured, not estimated: a sweep of the engine for dark web, onion,
    stealer, breach data, credential leak, supply chain, third party and vendor risk returns
    nothing. Claiming either would be the one mistake this meeting cannot survive, and it would
    also throw away the actual opportunity, which is that the gap is the complementarity.

EVERY BITSIGHT FACT HERE IS SOURCED, AND THE SOURCE CLASS IS ON THE SLIDE
    [BS] BitSight's own page, white paper or press release · [P] primary filing or government
    record · [AC] peer-reviewed or preprint academic work · [3P] third party.
    Primary document is "How Bitsight Calculates Security Ratings", January 2026, BitSight's own
    PDF. Where two BitSight pages disagree with each other, the deck says so and shows both.

NUMBERS WE DELIBERATELY DO NOT PUT ON A SLIDE
    * Any false-positive rate or attribution-accuracy figure, for them or for us. Nobody in this
      category publishes one. A number here would be invented, and he would know it.
    * Any claim that we find more assets than BitSight. We have not run the comparison. The deck
      PROPOSES the comparison instead, which is what he asked for.

NO LONG DASHES in any rendered string (operator standing rule).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, MONO, MUTED, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from build_consensus_business_deck import table  # noqa: E402

FOOT = ("S4BIZ GROUP · CYBERGOD LLC · HERKOS BESIDE BITSIGHT · NOV 2026 · "
        "DISCUSSION MATERIAL, SOURCES ON THE FINAL SLIDE")


def _src(s, text, y=6.62):
    """The source line. Every factual slide carries one, in the template's muted mono."""
    _tb(s, 0.55, y, 11.20, 0.28, text, 8.0, MUTED, MONO)


def build(template, out):
    d = Deck(template)

    # ---------------------------------------------------------------- 01 hero
    s = d.slide("S4BIZ GROUP · CYBERGOD LLC", [
        ("Herkos beside BitSight.", WHITE),
        ("Where we overlap, where we do not,", CYAN),
        ("and what that makes possible.", VIOLET),
    ], hero=True, footer=FOOT)
    _tb(s, 0.55, 4.70, 11.60, 1.30,
        "Prepared for the agenda you set. We have never benchmarked Herkos against BitSight, so "
        "nothing here claims we are better. It argues architecture and scope, names the two things "
        "you asked about that we do not do at all, and proposes the live comparison that would "
        "settle the rest.", 13, BODY, TEXT)

    # ---------------------------------------------------------------- 02 context
    s = d.slide("AGENDA ITEM 1", "S4biz and the two products", None,
                "One engine that looks outward with no access, one that watches a live estate.",
                FOOT)
    card(s, 0.55, 2.10, 5.90, 2.05, "HERKOS · ASM", CYAN,
         "External attack surface, from public record only",
         "Builds an evidenced picture of a company's internet facing estate from third party "
         "indexes and public logs, grades it, writes the prose with a four model chain and "
         "produces board and technical reports in about two minutes.")
    card(s, 6.85, 2.10, 5.90, 2.05, "PERSEUS · AGENTIC SOC", VIOLET,
         "Detection that proposes, code that decides",
         "Four vendor model consensus on live incidents, proposing detection rules only. Five fail "
         "closed barriers plus a quorum before any rule promotes, and automatic demotion of a rule "
         "that refuses legitimate traffic.")
    card(s, 0.55, 4.40, 5.90, 1.95, "THE COMPANY", INDIGO,
         "Stars4business OU, Estonia",
         "Small, self funded, shipping. Five production domains on one estate, a deploy pipeline "
         "with a gate that runs the operator's own test phase, and an engine whose design rules are "
         "written down because each was paid for by an incident.")
    card(s, 6.85, 4.40, 5.90, 1.95, "WHY THIS MEETING", AMBER,
         "Complementary, not competitive, is the hypothesis",
         "You asked whether our coverage is superior or complementary. We think the honest answer "
         "is complementary, and the rest of this deck is the evidence for that rather than a pitch "
         "against your platform.")
    _src(s, "SOURCE: CYBERGOD.AI ENGINE AND REPOSITORY, MEASURED 6 NOV 2026")

    # ---------------------------------------------------------------- 03 honest scope
    s = d.slide("BEFORE THE COMPARISON", "What we are comparing, and what we are not", None,
                "BitSight sells three families. Herkos sits inside one band of one of them.", FOOT)
    table(s, 0.55, 2.15, 12.20,
          ["BitSight family", "What it is", "Does Herkos compete?"],
          [["Security Posture Management",
            "Own organisation rating, asset management, EASM, benchmarking, subsidiaries",
            "Partly. EASM only, and EASM is a capability band inside SPM, not a SKU"],
           ["Third Party Risk Management",
            "Portfolio monitoring of vendors, intake and questionnaire workflow, remediation",
            "No. We have no portfolio, no vendor graph, no workflow"],
           ["Cyber Threat Intelligence",
            "Identity, attack surface, vulnerability, ransomware and brand intelligence",
            "No. We have no dark web collection of any kind"]],
          [0.254, 0.459, 0.287])
    _tb(s, 0.55, 4.55, 12.20, 1.60,
        "This slide is first on purpose. BitSight is a ratings and portfolio business with an EASM "
        "capability attached; Herkos is an evidence engine for one company's external estate. A "
        "comparison that pretends the two products have the same shape would waste your time, and "
        "the parts where we genuinely overlap are narrow enough to test properly in one session.",
        12, BODY, TEXT)
    _src(s, "SOURCE: BITSIGHT PRICING AND PACKAGING PAGE AND PRODUCT PAGES [BS], READ 6 NOV 2026")

    # ---------------------------------------------------------------- 04 the live comparison
    s = d.slide("AGENDA ITEM 2", "The live comparison, and how to", " make it fair",
                "You pick the company. We run it cold, in the room.", FOOT)
    bullets(s, 0.55, 2.15, 6.10, [
        "YOU CHOOSE THE TARGET, not us. A company BitSight already rates, so both sides have "
        "something to show. Ideally one you know well enough to adjudicate.",
        "WE RUN HERKOS COLD on the stage, from the domain only. About two minutes, no prior "
        "knowledge, no access, no preparation.",
        "BOTH LISTS GO ON ONE SCREEN. Assets each side found, assets only one side found, and "
        "anything either side attributed to the target that is not theirs.",
        "THE INTERESTING COLUMN IS THE THIRD ONE. Agreement is not informative. Disagreement is "
        "where the two architectures are visible.",
    ], gap=0.95, size=10.5)
    card(s, 7.05, 2.15, 5.70, 1.75, "WHAT WOULD COUNT AS A RESULT FOR US", GREEN,
         "Nothing in our list belongs to a third party",
         "We would rather return a smaller estate than a wrong one. If we name an asset that is "
         "not the target's, that is a defect and we will treat it as one in front of you.")
    card(s, 7.05, 4.10, 5.70, 1.75, "WHAT WOULD COUNT AS A RESULT FOR YOU", AMBER,
         "Breadth, history and the portfolio view",
         "Twelve months of rated history, peer comparison, and a vendor portfolio are things a "
         "single cold run cannot produce and should not pretend to.")
    _src(s, "METHOD PROPOSED, NOT YET RUN. NO BENCHMARK BETWEEN THE TWO PRODUCTS EXISTS TODAY")

    # ---------------------------------------------------------------- 05 collection architecture
    s = d.slide("AGENDA ITEM 3 · COLLECTION", "The one architectural difference", " that is documented",
                "Not a claim about quality. A difference in what each engine is allowed to do.",
                FOOT)
    card(s, 0.55, 2.10, 5.90, 2.35, "BITSIGHT, IN ITS OWN WORDS", INDIGO,
         "Listening, and actively looking",
         "\"What we learn by actively looking: we use non intrusive probes and queries to observe "
         "open ports; server software, configuration and versions; known vulnerabilities (CVEs); "
         "DNS records, including SPF and DKIM; web applications.\" Plus sensors, sinkholes and "
         "over 100 partner feeds.")
    card(s, 6.85, 2.10, 5.90, 2.35, "HERKOS", CYAN,
         "Third party record, and the customer's own front door",
         "No scanning, no probing and no authentication attempt against the assessed company. Host "
         "and service data comes from third party indexes and public logs. The engine reads the "
         "customer's published website and the certificate their web server serves, which is what "
         "any browser does.")
    _tb(s, 0.55, 4.75, 12.20, 1.60,
        "Why it matters commercially rather than technically: an engine that sends no probe needs "
        "no change request, no maintenance window, no notice and no customer authorisation, which "
        "is what lets a partner assess a prospect it has no relationship with. It is also why we "
        "can say in a contract that not one packet is sent in anger. Active probing is a better "
        "signal in many cases. It is simply a different permission model.", 12, BODY, TEXT)
    _src(s, "SOURCE: \"HOW BITSIGHT CALCULATES SECURITY RATINGS\", JAN 2026, P. 4 [BS] · CYBERGOD "
            "ENGINE, MEASURED")

    # ---------------------------------------------------------------- 06 what the rating is
    s = d.slide("AGENDA ITEM 3 · THE SCORE", "What the 250 to 900 number", " is made of",
                "Published by BitSight. Worth knowing precisely, because we deliberately produce no score.",
                FOOT)
    stat(s, 0.55, 2.20, 2.70, "70%", "DILIGENCE\nexternally observable configuration", CYAN)
    stat(s, 3.45, 2.20, 2.70, "27%", "COMPROMISED SYSTEMS\ninferred infection, via sinkholes", VIOLET)
    stat(s, 6.35, 2.20, 2.70, "2.5%", "USER BEHAVIOUR\nfile sharing", AMBER)
    stat(s, 9.25, 2.20, 3.50, "A to F", "PERCENTILE BANDS\nA is the top 10% of the population", GREEN)
    bullets(s, 0.55, 4.40, 12.20, [
        "It is a PERCENTILE, renormalised daily, rounded down to ten points because BitSight says "
        "the number should not convey a false sense of precision.",
        "Diligence findings persist for 60 days when a state change cannot be confirmed, and stale "
        "IP registration carries a 90 day grace period.",
        "BitSight's own two documents give the category weights as 27/70.5 and 26/71.5. The "
        "structure is the point, not the decimal.",
    ], gap=0.60, size=10.5, dot=VIOLET)
    _src(s, "SOURCE: BITSIGHT WHITE PAPER JAN 2026 AND HELP CENTRE ARTICLE UPDATED 19 DEC 2025 [BS]")

    # ---------------------------------------------------------------- 07 score vs evidence
    s = d.slide("AGENDA ITEM 4", "Performance, or exposure", None,
                "BitSight draws this distinction itself. It is the clearest statement of the two roles.",
                FOOT)
    _rect(s, 0.55, 2.10, 12.20, 1.15, INK)
    _tb(s, 0.80, 2.25, 11.70, 0.90,
        "\"Exposure may change rapidly ... in contrast, performance tends to change relatively "
        "slowly.\"   BitSight, How Bitsight Calculates Security Ratings, January 2026",
        12.5, WHITE, TEXT, True)
    table(s, 0.55, 3.55, 12.20,
          ["", "A rating answers", "Herkos answers"],
          [["Question", "How has this organisation performed, relative to others",
            "What is observable about this organisation right now, and what proves it"],
           ["Unit", "One number per organisation per day",
            "A finding, with the public record it came from attached"],
           ["Movement", "Can improve when the rated population gets worse",
            "Changes only when the observed estate changes"],
           ["Best use", "Portfolio triage, trend, procurement threshold, board reporting",
            "The conversation after the triage, where somebody asks what exactly is wrong"]],
          [0.156, 0.385, 0.459])
    _src(s, "SOURCE: BITSIGHT WHITE PAPER JAN 2026 [BS]. THE RIGHT COLUMN IS OUR DESIGN, NOT A "
            "COMPARATIVE CLAIM")

    # ---------------------------------------------------------------- 08 attribution
    s = d.slide("AGENDA ITEM 3 · ASSET DISCOVERY", "Attribution is the whole game", None,
                "Both engines use similar heuristics. The difference is what happens when they fail.",
                FOOT)
    table(s, 0.55, 2.15, 12.20,
          ["", "BitSight, as published", "Herkos"],
          [["Sources", "RIR records, ASN and BGP, passive DNS, certificates, human review",
            "Shodan, Certificate Transparency, RIPEstat, RDAP, PeeringDB, BGPView, CAIDA, HE"],
           ["Shared hosting", "CIDR assigned only when solely or primarily used by the company",
            "A selector matching over 2,000 hosts is shared by definition and cannot anchor"],
           ["Certificates", "Exclusive domains only, retrieved without SNI, PTR checked for CDN",
            "Same shape, plus the rule that a pin proves the address, never the observation"],
           ["When unsure", "Finding stands; rated company appeals with evidence",
            "Reports UNKNOWN and claims no gap. Absence of evidence is never a finding"],
           ["Hoster identity", "Not separately published",
            "Never the target's. Netblock holder and PTR domain are evidence about the provider"]],
          [0.156, 0.410, 0.434])
    _tb(s, 0.55, 5.55, 12.20, 0.95,
        "Their heuristics are the correct ones and we use the same family. We are not claiming "
        "they are naive. The honest difference is the burden of proof: in a ratings product the "
        "rated company appeals, in ours the engine refuses to assert in the first place and a "
        "refusal is a visible outcome rather than a silent one.", 11.5, BODY, TEXT)
    _src(s, "SOURCE: BITSIGHT IP/CIDR MAPPING PROCESS ARTICLE [BS] · CYBERGOD ENGINE RULES, MEASURED")

    # ---------------------------------------------------------------- 09 dark web
    s = d.slide("AGENDA ITEM 3 · DARK WEB", "We do not do this at all", None,
                "You asked specifically. The answer is no, and the detail is worth a minute.", FOOT)
    card(s, 0.55, 2.10, 5.90, 2.45, "BITSIGHT", INDIGO,
         "Cybersixgill, acquired for $115m, closed Dec 2024",
         "1,000+ underground forums and marketplaces crawled, 1B+ compromised credentials, "
         "stealer malware logs named as the source, brand intelligence with takedown, and a "
         "services tier that purchases listed items and engages actors.")
    card(s, 6.85, 2.10, 5.90, 2.45, "HERKOS", RED,
         "Zero. No collection, no feed, no partner",
         "A sweep of the engine for dark web, onion, stealer, breach data, credential leak and "
         "paste sources returns nothing. There is no roadmap item and no partial capability to "
         "oversell. This is a clean gap.")
    _rect(s, 0.55, 4.90, 12.20, 1.45, INK)
    _tb(s, 0.80, 5.05, 11.70, 1.20,
        "THE DETAIL THAT MAKES THIS INTERESTING RATHER THAN EMBARRASSING: in BitSight's own rating, "
        "Exposed Credentials is INFORMATIONAL and does not affect the score, and the stated reason "
        "is that many sites do not validate email addresses, so attributing a leaked record to a "
        "company's employees is unreliable. So dark web data sits beside the rating in both "
        "products. In yours it is a separately priced family; in ours it is absent.",
        11.5, WHITE, TEXT)
    _src(s, "SOURCE: BITSIGHT CTI PAGE AND WHITE PAPER JAN 2026 [BS] · ACQUISITION PRICE "
            "TECHCRUNCH, SECURITYWEEK, CYBERSCOOP [3P]")

    # ---------------------------------------------------------------- 10 supply chain
    s = d.slide("AGENDA ITEM 3 · SUPPLY CHAIN", "We do not do this either", None,
                "No portfolio, no vendor graph, no fourth party inference.", FOOT)
    bullets(s, 0.55, 2.15, 6.10, [
        "BITSIGHT: 40M+ rated organisations, 40,000 pre built vendor profiles, folders and tiers, "
        "daily re rating, rule based alerts and a REST API.",
        "FOURTH PARTY is marketed as automatic discovery of product usage. The mechanism appears "
        "to be technographic inference; no methodology or accuracy figure is published.",
        "HERKOS: one company per run. A partner can run many companies, but there is no portfolio "
        "object, no continuous monitoring and no relationship graph.",
        "WE WOULD RATHER SAY SO than describe repeated single runs as supply chain visibility.",
    ], gap=0.95, size=10.5, dot=AMBER)
    card(s, 7.05, 2.15, 5.70, 3.70, "ONE NUMBER TO CORRECT, GENTLY", VIOLET,
         "40M+, not 325M+",
         "The 325M+ figure on the BitSight homepage traces to the Implied Cyber Threat indicator "
         "built with Moody's on the Orbis firmographic database, which is an inherent risk "
         "indicator over Orbis entities rather than 325M BitSight ratings. The rated figure "
         "BitSight states elsewhere is 40M+, and the partners page says 350M+. We mention it only "
         "because we would want the same correction made about our own numbers.", bsize=10)
    _src(s, "SOURCE: BITSIGHT ABOUT, HOMEPAGE, TPRM AND PARTNERS PAGES, AWS MARKETPLACE LISTING [BS]")

    # ---------------------------------------------------------------- 11 differentiation
    s = d.slide("AGENDA ITEM 4", "Where we are genuinely", " differentiated",
                "Four claims. Each is a design rule in the code, not a marketing line.", FOOT)
    card(s, 0.55, 2.10, 6.00, 1.85, "01 · PERMISSION MODEL", CYAN,
         "No packet in anger, so no authorisation needed",
         "Contractual, not aspirational: active probing requires both a flag and a written "
         "authorisation reference, and neither is set. A partner can assess a prospect it has "
         "never spoken to.")
    card(s, 6.75, 2.10, 6.00, 1.85, "02 · REFUSAL AS A FEATURE", VIOLET,
         "A failed lookup reports UNKNOWN and claims no gap",
         "An empty estate is an honest, saleable outcome. A deck full of another company's servers "
         "is not. The engine would rather return nothing than return a stranger.")
    card(s, 0.55, 4.15, 6.00, 1.85, "03 · EVIDENCE TO THE RECORD", GREEN,
         "Every finding carries the public record it came from",
         "No invented identifiers: a CVE reaches a report only if it is in the raw findings, and a "
         "guard strips the rest. The model writes prose, deterministic code decides facts.")
    card(s, 6.75, 4.15, 6.00, 1.85, "04 · THE ARTEFACT IS THE PRODUCT", AMBER,
         "Four boardroom decks and a report in about two minutes",
         "In the customer's language, with the regulatory framing for their jurisdiction. English, "
         "German, Russian and Portuguese today. The output is the deliverable, not a dashboard "
         "export.")
    _src(s, "SOURCE: CYBERGOD ENGINE DESIGN RULES AND TEST SUITE, MEASURED 6 NOV 2026")

    # ---------------------------------------------------------------- 12 where they are ahead
    s = d.slide("AGENDA ITEM 4 · THE OTHER HALF", "Where BitSight is ahead of us", None,
                "If this slide were missing you should not believe the previous one.", FOOT)
    table(s, 0.55, 2.15, 12.20,
          ["Dimension", "BitSight", "Us"],
          [["History", "12+ months of rated history on 40M+ organisations", "The run you just did"],
           ["Breadth of signal", "Sinkhole telemetry, sensors, 100+ partner feeds",
            "Public indexes and logs only"],
           ["Portfolio", "40,000 vendor profiles, continuous monitoring, alerting", "None"],
           ["Dark web", "Cybersixgill, 1,000+ sources", "None"],
           ["Assurance", "Enterprise programme, 3,500+ customers, 120+ government institutions",
            "No ISO 27001, no SOC 2, one hosting region, no named reference customer"],
           ["Validation", "Marsh McLennan study across 365,000 organisations",
            "No published validation study of any kind"]],
          [0.197, 0.443, 0.360])
    _tb(s, 0.55, 5.78, 12.20, 0.72,
        "The assurance row is the one that costs us deals today and we are not going to discover it "
        "in front of you. It is also the row a partnership fixes fastest.", 11.5, BODY, TEXT)
    _src(s, "SOURCE: BITSIGHT ABOUT PAGE AND PRESS [BS] · MARSH MCLENNAN STUDY OCT 2022 [3P] · OUR "
            "OWN CAPABILITY FACTS")

    # ---------------------------------------------------------------- 13 the fit
    s = d.slide("AGENDA ITEM 5", "Three shapes a fit could take", None,
                "Ordered by how little either side has to change. There is precedent for all three.",
                FOOT)
    card(s, 0.55, 2.10, 4.00, 3.10, "A · INTEGRATION", CYAN,
         "Herkos reads the customer's BitSight data",
         "The evidence pack we build gains rated history and portfolio context; the rating gains a "
         "drill down that explains itself. This is exactly how Brinqa, Netskope and the GRC "
         "vendors already work with you, against the customer's own licence.", bsize=9.5)
    card(s, 4.72, 2.10, 4.00, 3.10, "B · TECHNOLOGY ALLIANCE", VIOLET,
         "Listed integration, like Censys or IONIX",
         "BitSight already lists Censys, Randori, CyCognito, IONIX, Tenable and Qualys as "
         "complementary discovery and enrichment. The precedent for an attack surface vendor "
         "becoming a listed alliance partner is established, and we would be the small one.",
         bsize=9.5)
    card(s, 8.90, 2.10, 3.85, 3.10, "C · OEM OR DATA", AMBER,
         "The hardest, and we say so",
         "Public precedent for embedding BitSight data exists only with Moody's and S&P Global, "
         "and the default posture in every public artefact is display only, no redistribution. We "
         "raise it to ask the question, not to propose it.", bsize=9.5)
    _tb(s, 0.55, 5.38, 12.20, 1.10,
        "WHAT WE ARE NOT ASKING FOR: your platform as a lead generation channel. You said that "
        "explicitly and we agree with it. The thing worth testing is whether an evidence engine "
        "with no score and no portfolio makes a rating more useful to the same buyer, and that is "
        "a technical question with a technical answer.", 11.5, BODY, TEXT)
    _src(s, "SOURCE: BITSIGHT INTEGRATIONS DIRECTORIES AND MOODY'S PRODUCT TERMS [BS] · MOODY'S "
            "FY2025 10-K [P]")

    # ---------------------------------------------------------------- 14 commercial shape
    s = d.slide("CONTEXT", "Different units, not a price comparison", None,
                "Shown so nobody has to guess what the other side costs.", FOOT)
    table(s, 0.55, 2.15, 12.20,
          ["", "BitSight", "Herkos"],
          [["Unit", "Subscription, banded by vendors monitored or tier",
            "Per company assessed, or per seat per month"],
           ["Published price",
            "AWS Marketplace SPM Enterprise, $138,550 per licence per year [P]",
            "100 EUR per run, 200 EUR per seat per month, list"],
           ["Observed range",
            "US federal awards roughly $56k to $155k per agency per year [P]",
            "Partner tier buys at 90 and 180 EUR"],
           ["Who sells", "Direct plus resellers, MSSP programme, marketplaces",
            "Partners only in several markets, including Angola"]],
          [0.156, 0.451, 0.393])
    _tb(s, 0.55, 5.10, 12.20, 1.40,
        "These are not competing line items. A 140,000 dollar portfolio subscription and a 100 euro "
        "run are bought by different people for different reasons, and in most accounts the run is "
        "what happens before anybody has a budget conversation at all. That is the commercial "
        "shape of the complementarity, if it exists.", 12, BODY, TEXT)
    _src(s, "SOURCE: AWS MARKETPLACE LISTING AND USASPENDING.GOV AWARD RECORDS [P] · S4BIZ PRICE LIST")

    # ---------------------------------------------------------------- 15 asks
    s = d.slide("AGENDA ITEM 6", "What we are asking you for", None,
                "In your own words, with what we would do with each.", FOOT)
    bullets(s, 0.55, 2.15, 12.20, [
        "TELL US WHERE THE DIFFERENTIATION IS REALLY STRONG, and where we are repeating what the "
        "category already says. We will take the second answer as seriously as the first.",
        "THE LIVE COMPARISON, on a target you choose. If our list contains anything that is not "
        "the target's, say so in the room and we will fix it as a defect.",
        "AN INTERNAL INTRODUCTION, only if the comparison shows the technology is complementary. "
        "Route B on the previous slide is the realistic shape.",
        "POSITIONING IN A CROWDED ASM MARKET: what is sufficiently unique for a customer, for a "
        "partner, and for an investor. Those are three different answers and we would like all three.",
        "INVESTOR DOORS, including Singtel Innov8 if you see a fit. Worth noting Singtel appears "
        "in BitSight's own 2016 channel announcement, so the relationship is not new ground.",
    ], gap=0.88, size=10.5, dot=CYAN)
    _src(s, "SOURCE: AGENDA AND INTERESTS AS PROVIDED · SINGTEL NAMED IN BITSIGHT CHANNEL PRESS "
            "RELEASE 2016 [BS]")

    # ---------------------------------------------------------------- 16 sources
    s = d.slide("METHOD", "Sources, and what we refused to put", " on a slide",
                "So that every number in this deck can be checked before the meeting.", FOOT)
    bullets(s, 0.55, 2.10, 6.10, [
        "PRIMARY: How Bitsight Calculates Security Ratings, January 2026, BitSight's own PDF.",
        "BitSight help centre: rating calculation, IP and CIDR mapping, threat research process, "
        "API documentation and endpoints.",
        "BitSight pricing and packaging, product, integrations, partners and about pages.",
        "Moody's FY2025 10-K and Q3 2026 10-Q, AWS Marketplace listing, USAspending.gov awards.",
        "Marsh McLennan correlation study, Oct 2022. Academic work by Edwards, Jacobs and Forrest; "
        "Woods and Boehme; Liu et al.",
    ], gap=0.70, size=9.8, dot=INDIGO)
    card(s, 7.05, 2.10, 5.70, 2.00, "DELIBERATELY ABSENT", RED,
         "Any accuracy or false positive number",
         "No vendor, analyst or academic publishes a false positive rate or an attribution accuracy "
         "figure for any product in this category, ours included. A number here would have been "
         "invented.", bsize=9.5)
    card(s, 7.05, 4.30, 5.70, 2.00, "ALSO DELIBERATELY ABSENT", RED,
         "Any claim that we find more than you",
         "We have not run the comparison. Slide four proposes it instead. If the result goes "
         "against us we would rather learn it in this room than in a customer's.", bsize=9.5)
    _src(s, "ALL SOURCES READ 6 NOV 2026. SOURCE CLASS MARKED ON EACH SLIDE: [BS] BITSIGHT OWN, "
            "[P] PRIMARY FILING, [AC] ACADEMIC, [3P] THIRD PARTY")

    return d.save(out)


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Herkos_vs_BitSight.pptx"))
    a = ap.parse_args()
    out = build(a.template, a.out)
    print("[ok] %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
