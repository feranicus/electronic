#!/usr/bin/env python3
"""build_cybergod_pitch_deck.py — the cybergod.ai pitch, in the S4biz template.

    python marketing/build_cybergod_pitch_deck.py [--out PATH] [--template PATH]

WHAT THIS IS. The operator's two-page CYBERGOD PITCH, rebuilt as a deck in S4biz colours, with one
to two slides explaining EACH artifact a run produces: the security assessment, C-BIQ, GEOPOL, the
compliance grading and the animated report. A prospect who is shown four deliverables and told
nothing about them cannot buy any of them.

IT REUSES build_consensus_deck's Deck/card/bullets/stat, so the S4biz template exists in exactly
ONE implementation across all three decks and they cannot drift apart. Same doctrine as legal.jsx
and the contract pack: a value with two homes is the defect this repository pays for most often.

THREE CONTENT RULES, carried over from the consensus deck and applied again here.

1. NO PRICES. Not ours, anyway. /partners carries none, the partner pack carries none, and a price
   on a deck that circulates is a negotiating position given away for free and stale the day a tier
   changes. The regulatory FINES are on the slides because they are law and they are the point.

2. EVERY NUMBER IS OURS AND MEASURED, OR EXTERNAL AND DATED. The regulatory dates and penalty
   ceilings are read out of scripts/compliance/EU_COMPLIANCE_REFERENCE.md and the JURISDICTIONS
   registry in compliance_enrich.py, not remembered. Two of them have already passed as at the
   build date and the deck says so rather than presenting them as future deadlines, because a
   prospect who checks one date and finds it wrong stops checking the rest.

3. WHAT THE PRODUCT IS NOT GETS ITS OWN SLIDE. Public sources only, no packet sent, not a
   penetration test, not a certification. That is the promise the whole product rests on: it is why
   an assessment needs no authorisation from the target, and it is the first thing a large
   customer's security team asks about. Burying it in a footnote would be the one dishonest slide
   in the deck.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from pptx.util import Inches, Pt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx")
OUT = os.path.join(HERE, "S4biz_Cybergod_Pitch.pptx")

FOOT = "S4BIZ GROUP  ·  CYBERGOD.AI  ·  SALES AND PARTNER BRIEFING  ·  COMMERCIAL IN CONFIDENCE"

# Observed to fit the 0.70in title row at 30pt Arial Black. 53 characters wraps and lands on the
# sub-heading; 49 fits. The cap is the lower end of that measured interval, not a guess.
TITLE_MAX = 50


def _check_title(title, tail):
    n = len(title) + len(tail or "")
    if n > TITLE_MAX:
        raise SystemExit("[X] title is %d characters and wraps onto the sub-heading (max %d): %r"
                         % (n, TITLE_MAX, (title + (tail or ""))))
    return n


def build(template, out):
    d = Deck(template)
    _orig = d.slide

    def _guarded(eyebrow, title, title_tail=None, sub=None, footer="", hero=False):
        if not hero:
            _check_title(title, title_tail)
        return _orig(eyebrow, title, title_tail, sub, footer, hero)

    d.slide = _guarded

    # =========================================================================================
    # 01 — HERO
    # =========================================================================================
    s = d.slide("cybergod.ai  ·  external cyber risk, priced and attributed",
                [("TYPE A NAME.", WHITE), ("SEE THEIR FUTURE.", CYAN)],
                footer=FOOT, hero=True)
    _tb(s, 0.52, 4.35, 8.10, 1.10,
        "Their exposed systems. The price of their breach in euros. The name of the group that "
        "would hit them. And the date the regulator starts counting.\n"
        "You get all of it before the coffee arrives.", 13, BODY, TEXT, space=1.35)
    for i, (v, l, c) in enumerate((("1", "INPUT\nA COMPANY NAME", CYAN),
                                   ("5", "ARTIFACTS\nOUT OF ONE RUN", VIOLET),
                                   ("0", "PACKETS SENT\nTO THE TARGET", GREEN))):
        stat(s, 9.05 + i * 1.35, 4.45, 1.25, v, l, c, 34)

    # =========================================================================================
    # 02 — THE OLD WAY / THE NEW WAY
    # =========================================================================================
    s = d.slide("the problem", "Discovery takes five weeks.", " You have one meeting.",
                sub="Your competitor is in that room asking \"tell me about your environment\". "
                    "You are opening a laptop and showing the prospect their own firewall.",
                footer=FOOT)
    _rect(s, 0.50, 2.15, 6.05, 4.10, PANEL, LINE)
    _rect(s, 6.78, 2.15, 6.05, 4.10, INK, CYAN)
    _tb(s, 0.76, 2.38, 5.53, 0.28, "THE OLD WAY  ·  EVERYONE ELSE", 9.5, MUTED, MONO, True)
    _tb(s, 7.04, 2.38, 5.53, 0.28, "THE NEW WAY  ·  YOU", 9.5, CYAN, MONO, True)
    bullets(s, 0.76, 2.85, 5.53, [
        "Discovery calls to find out what they even have.",
        "Wait for a technical resource who is booked three weeks out.",
        "Ask for permission, scope, and a signed test window.",
        "Weeks pass. The deal goes cold.",
        "The CFO asks \"why should I care?\" and nobody has a number.",
    ], dot=MUTED, size=10.5)
    bullets(s, 7.04, 2.85, 5.53, [
        "You already know what they have, before the first call.",
        "No technical resource. No permission. No wait.",
        "Nothing is sent to them, so nothing needs approving.",
        "Minutes. The first meeting IS the deal.",
        "The CFO gets the number, in euros, with the method attached.",
    ], dot=CYAN, size=10.5)

    # =========================================================================================
    # 03 — ONE NAME IN, FIVE ARTIFACTS OUT
    # =========================================================================================
    s = d.slide("what a run produces", "One name in.", " Five artifacts out.",
                sub="Every run produces the same set. Each one answers a different person's "
                    "question, which is why there are five and not one.",
                footer=FOOT)
    art = [
        ("01", CYAN, "SECURITY ASSESSMENT",
         "What of them is reachable from the internet, ranked by severity, each finding carrying "
         "the evidence that proves it.\nFor: the security lead."),
        ("02", VIOLET, "C-BIQ",
         "That exposure priced in euros: expected annual loss, worst plausible loss, and the "
         "return on fixing it.\nFor: the CFO and the board."),
        ("03", INDIGO, "GEOPOL",
         "Who would plausibly attack them, why, and by which route. Actors, motive, kill chain.\n"
         "For: the CISO and the risk committee."),
    ]
    for i, (k, c, h, b) in enumerate(art):
        card(s, 0.50 + i * 4.28, 2.15, 3.95, 2.05, k, c, h, b, bsize=9.5)
    art2 = [
        ("04", GREEN, "COMPLIANCE GRADING",
         "Which regimes bite, what the duties are, where the gaps are, and the maximum fine.\n"
         "For: legal, and whoever is personally liable."),
        ("05", AMBER, "ANIMATED REPORT + RUN LOG",
         "A scrollytelling web page an executive will actually read, and a log of exactly what the "
         "engine did.\nFor: the room, and for anyone who asks how."),
    ]
    for i, (k, c, h, b) in enumerate(art2):
        card(s, 0.50 + i * 6.42, 4.40, 6.09, 1.90, k, c, h, b, bsize=9.5)

    # =========================================================================================
    # 04 — SECURITY ASSESSMENT, WHAT IT IS
    # =========================================================================================
    s = d.slide("deliverable 01", "The security assessment", ", in plain words",
                sub="What of this company can a stranger on the internet reach today, and what "
                    "would they do with it.",
                footer=FOOT)
    _tb(s, 0.55, 2.10, 7.55, 1.40,
        "The engine resolves the whole estate from one name: the address space they announce, the "
        "domains and subdomains their certificates reveal, the group companies their own website "
        "publishes. It then reads what public internet scan data already knows about each host, "
        "and classifies what it finds.", 11.5, BODY, TEXT, space=1.32)
    bullets(s, 0.55, 3.55, 7.55, [
        "Every finding carries an EVIDENCE ANCHOR: the address, the port, the banner or the "
        "certificate that proves it. No finding without evidence.",
        "Severity is CRITICAL, HIGH, MEDIUM or LOW, and those four colours mean the same thing on "
        "every deck we have ever produced.",
        "Each one answers three questions: what it is, why it matters in business terms, and three "
        "to five ways to remove it, managed service first.",
        "The regulatory framework set is chosen from the customer's own country, so a Swiss bank "
        "is not shown NIS2 and a UAE ministry is not shown GDPR.",
    ], size=10.5, gap=0.62)
    card(s, 8.35, 2.10, 4.48, 4.20, "THE HARD PART", CYAN, "Not finding things.\nRefusing them.",
         "Anyone can list hosts near a company name. The work is proving each one is THEIRS: an "
         "ownership gate on every discovered domain, a co-tenant guard on shared address space, an "
         "attribution gate on multi-tenant hosting, a per-domain budget so one bad link cannot "
         "become the estate, and a false-positive audit by a model from a different vendor than "
         "the one that wrote the deck.\n\nA stranger's server in a customer's report is the one "
         "mistake that ends the meeting.", bsize=9.5)

    # =========================================================================================
    # 05 — SECURITY ASSESSMENT, WHAT IS ON THE PAGE
    # =========================================================================================
    s = d.slide("deliverable 01", "What is actually on the slides",
                sub="Eighteen pages. This is the spine of it, and the order is deliberate: "
                    "inventory, then index, then one page per finding.",
                footer=FOOT)
    rows = [
        ("ASSET INVENTORY", "Unique addresses, autonomous systems, countries, operators. The "
                            "picture of the estate before a single judgement is made."),
        ("FINDINGS INDEX", "Every finding on one page, by severity, with its evidence anchor. "
                           "This is the page people photograph."),
        ("ONE PAGE PER FINDING", "What it is. Why it matters, in three sentences with the "
                                 "attacker action, the business consequence and the regulation. "
                                 "Then three to five remediations."),
        ("METHODOLOGY", "What was queried, what was excluded, and how many candidate hosts the "
                        "guards dropped. The number that is usually large."),
        ("CLARIFY", "What recon could NOT resolve, put to the operator as questions. Answering "
                    "them re-scopes the run and rebuilds the deck."),
    ]
    y = 2.15
    for i, (k, v) in enumerate(rows):
        _rect(s, 0.50, y, 12.33, 0.80, PANEL if i % 2 else INK, LINE)
        _tb(s, 0.76, y + 0.20, 3.05, 0.40, k, 11, CYAN, DISPLAY, True)
        _tb(s, 4.00, y + 0.16, 8.60, 0.60, v, 10, BODY, TEXT, space=1.24)
        y += 0.87

    # =========================================================================================
    # 06 — C-BIQ, WHAT IT IS
    # =========================================================================================
    s = d.slide("deliverable 02", "C-BIQ", ": the exposure, priced in euros",
                sub="Cyber Business-Impact Quantification. The step that turns each exposure into "
                    "the currency the business already runs on.",
                footer=FOOT)
    _tb(s, 0.55, 2.10, 7.55, 1.25,
        "A heat map tells a board that something is red. It does not tell them what it costs, so "
        "it cannot be compared against any other item competing for the same money. C-BIQ prices "
        "each finding using published methods, from evidence the assessment already gathered.",
        11.5, BODY, TEXT, space=1.32)
    for i, (k, c, h, b) in enumerate((
            ("BUILT ON", CYAN, "Open FAIR\nNIST IR 8286D",
             "Public, auditable standards. Not an invented score, and not a vendor's proprietary "
             "index that nobody can check."),
            ("METHOD", VIOLET, "Monte-Carlo\n50,000 runs",
             "Three-point estimates per loss bucket, sampled lognormally, so the answer is a "
             "distribution and not a single confident number."),
            ("ANCHORED TO", INDIGO, "Dated public\nincidents",
             "Every estimate ties back to a real, dated event at a comparable organisation, or it "
             "is not made."))):
        card(s, 0.50 + i * 4.28, 3.55, 3.95, 2.60, k, c, h, b, bsize=9.5)
    _rect(s, 8.35, 2.05, 4.48, 1.35, INK, CYAN)
    _tb(s, 8.61, 2.24, 3.96, 0.30, "THE ONE SENTENCE", 9, CYAN, MONO, True)
    _tb(s, 8.61, 2.55, 3.96, 0.75,
        "\"If nothing changes, this exposure costs you a number, and here is the working.\"",
        12, WHITE, DISPLAY, True, space=1.15)

    # =========================================================================================
    # 07 — C-BIQ, THE THREE NUMBERS
    # =========================================================================================
    s = d.slide("deliverable 02", "Three numbers, never blended",
                sub="Each answers a different question and a different person. Averaging them, "
                    "which most tools do, destroys all three.",
                footer=FOOT)
    nums = [
        ("ALE", CYAN, "ANNUALISED LOSS EXPECTANCY",
         "The mean expected loss per year.\n\nUse it for: the security budget. It is the number "
         "that compares cleanly against the cost of a control."),
        ("PML", VIOLET, "PROBABLE MAXIMUM LOSS",
         "The bad year, not the average one.\n\nUse it for: insurance limits and the board's "
         "appetite conversation. Nobody buys cover for the mean."),
        ("ROSI", GREEN, "RETURN ON SECURITY INVESTMENT",
         "Loss before, minus loss after, minus what the fix cost.\n\nUse it for: choosing between "
         "two fixes. It is the only one of the three that ranks options."),
    ]
    for i, (k, c, h, b) in enumerate(nums):
        card(s, 0.50 + i * 4.28, 2.15, 3.95, 2.70, k, c, h, b, bsize=9.5)
    _rect(s, 0.50, 5.10, 12.33, 1.18, PANEL, LINE)
    _tb(s, 0.76, 5.28, 11.81, 0.30, "AND THE CURVE, WHICH IS THE PART PEOPLE REMEMBER",
        9.5, CYAN, MONO, True)
    _tb(s, 0.76, 5.58, 11.81, 0.60,
        "The deck draws a loss-exceedance curve: the probability of losing at least X. A control "
        "moves the whole curve to the left, and that single picture does more in a board meeting "
        "than any table. It also makes the estimate falsifiable, which a score never is.",
        10, BODY, TEXT, space=1.26)

    # =========================================================================================
    # 08 — GEOPOL, WHAT IT IS
    # =========================================================================================
    s = d.slide("deliverable 03", "GEOPOL", ": who would attack, and why",
                sub="Exposure is only half the sentence. The other half is whether anyone has a "
                    "reason to walk through it.",
                footer=FOOT)
    _tb(s, 0.55, 2.10, 7.55, 1.25,
        "Two companies with identical exposure do not carry identical risk. A regional logistics "
        "firm and a defence supplier are not equally interesting to a state actor, and a payments "
        "processor is not equally interesting to a ransomware crew. GEOPOL says who, why, and by "
        "which route.", 11.5, BODY, TEXT, space=1.32)
    bullets(s, 0.55, 3.55, 7.55, [
        "THREAT ACTORS, banded by capability: nation-state, organised crime, hacktivist, insider. "
        "Each with the motive that makes this company a target.",
        "MITRE ATT&CK techniques mapped to the exposure that was actually found, not a generic "
        "list of everything an attacker could theoretically do.",
        "A KILL CHAIN for the most plausible route, step by step, ending at the asset that would "
        "actually hurt.",
        "Sector, geography and supply-chain drivers, with the sourcing graded so the reader can "
        "see how confident each judgement is.",
    ], size=10.5, gap=0.62)
    card(s, 8.35, 2.10, 4.48, 4.20, "FRAMEWORKS", INDIGO,
         "Three published\nframeworks",
         "MITRE ATT&CK for technique. The Diamond Model for adversary, infrastructure, victim and "
         "capability. Admiralty grading for how much weight to put on each source. Used the way an "
         "intelligence analyst uses them, not as a logo on a slide.\n\nThe grading matters: it is "
         "the "
         "difference between an assessment and an assertion. A reader can disagree with a "
         "conclusion and see exactly which evidence to argue with.", bsize=9.5)

    # =========================================================================================
    # 09 — COMPLIANCE
    # =========================================================================================
    s = d.slide("deliverable 04", "The second business", " nobody is selling yet",
                sub="Three EU laws turned every mid-size company on the continent into a funded, "
                    "deadline-driven buyer. This is not the security budget.",
                footer=FOOT)
    _tb(s, 0.55, 2.05, 12.28, 0.50,
        "It is a board-level compliance budget, signed off by people who are now personally "
        "liable. Type the company name and the platform grades which regimes bite, what the "
        "duties are, where the gaps are and what the maximum fine is.", 11, BODY, TEXT, space=1.28)
    hdr = ["REGIME", "WHO IT CATCHES", "MAXIMUM FINE", "WHERE THE CLOCK IS"]
    rows = [
        ("NIS2", "18 sectors, medium-sized and up", "EUR 10m / 2% of turnover",
         "Germany's grace period ended 31 Jul 2026. Live now.", CYAN),
        ("Cyber Resilience Act", "Anyone selling a product with digital elements",
         "EUR 15m / 2.5% of turnover",
         "Reporting duties begin 11 Sep 2026. Full regime 11 Dec 2027.", AMBER),
        ("EU AI Act", "Anyone building or deploying AI", "EUR 35m / 7% of turnover",
         "High-risk obligations have applied since 2 Aug 2026.", RED),
    ]
    x = [0.50, 3.15, 7.05, 9.55]
    wd = [2.55, 3.80, 2.40, 3.28]
    _rect(s, 0.50, 2.72, 12.33, 0.42, PANEL, LINE)
    for i, hcell in enumerate(hdr):
        _tb(s, x[i] + 0.16, 2.79, wd[i] - 0.20, 0.28, hcell, 9, CYAN, MONO, True)
    y = 3.18
    for name, who, fine, clock, col in rows:
        _rect(s, 0.50, y, 12.33, 0.98, INK, LINE)
        _rect(s, 0.50, y, 0.055, 0.98, col, None)
        _tb(s, x[0] + 0.16, y + 0.26, wd[0] - 0.20, 0.44, name, 12.5, WHITE, DISPLAY, True)
        _tb(s, x[1] + 0.16, y + 0.20, wd[1] - 0.20, 0.60, who, 10, BODY, TEXT, space=1.22)
        _tb(s, x[2] + 0.16, y + 0.28, wd[2] - 0.20, 0.40, fine, 11, col, DISPLAY, True)
        _tb(s, x[3] + 0.16, y + 0.20, wd[3] - 0.20, 0.60, clock, 9.5, BODY, TEXT, space=1.22)
        y += 1.05
    _tb(s, 0.55, 6.42, 12.28, 0.45,
        "Read the fine column again, then say it out loud in a meeting: seven per cent of global "
        "turnover, and the clock is already running. Two of these three are live today and the "
        "third starts reporting in weeks. Canada is graded too, against OSFI B-13, E-21, B-10, "
        "PIPEDA and Quebec Law 25.", 9.5, MUTED, TEXT, space=1.24)

    # =========================================================================================
    # 10 — THE ANIMATED REPORT AND THE RUN LOG
    # =========================================================================================
    s = d.slide("deliverable 05", "The page they read", " and the receipt",
                sub="A deck gets forwarded and skimmed. The animated report gets read to the end, "
                    "and the run log is what survives a procurement challenge.",
                footer=FOOT)
    card(s, 0.50, 2.15, 6.05, 4.10, "THE ANIMATED REPORT", AMBER,
         "A web page, not a PDF",
         "Five scenes that scroll: the exposed estate, who is coming, every way in, the six moves "
         "that arrive, and secure by design. Real animation, count-up figures, the whole thing in "
         "one self-contained file with nothing to install.\n\nIt exists because the deck is for "
         "the meeting and this is for the twenty minutes afterwards, when the person who was not "
         "in the room opens the link. That is usually the person with the budget.", bsize=10)
    card(s, 6.78, 2.15, 6.05, 4.10, "THE RUN LOG", GREEN,
         "The methodology receipt",
         "Every phase, every timing, every source queried, and every point where the engine "
         "REFUSED to conclude: a domain that did not corroborate, an ASN it could not verify, an "
         "estate it declined to attribute.\n\nIt is the strongest trust artifact in the product "
         "and it costs nothing to produce. It is also redacted by an allow-list before a customer "
         "sees it, so it carries the method without carrying our internals.", bsize=10)

    # =========================================================================================
    # 11 — WHAT IT IS NOT
    # =========================================================================================
    s = d.slide("the honest slide", "What this is not",
                sub="The first question a serious security team asks. Getting it wrong once "
                    "costs the account, so it is on its own page.",
                footer=FOOT)
    nots = [
        ("NOT A PENETRATION TEST", "No port scan. No vulnerability probe. No authentication "
                                   "attempt. Not one packet is sent to the organisation being "
                                   "assessed."),
        ("NOT A CERTIFICATION", "It is not an audit opinion, not an ISO certificate and not legal "
                                "advice. It is an assessment of what public information showed at "
                                "a point in time."),
        ("NOT A GUARANTEE", "We do not claim to find every exposure. A public source can be "
                            "incomplete, and we say so on the page rather than in a footnote."),
        ("NOT A SCORE", "No proprietary letter grade. Every number is decomposed so it can be "
                        "argued with, which is the only kind of number a board should accept."),
    ]
    for i, (h, b) in enumerate(nots):
        card(s, 0.50 + (i % 2) * 6.42, 2.15 + (i // 2) * 2.10, 6.05, 1.90,
             "%02d" % (i + 1), RED, h, b, bsize=9.5)
    _tb(s, 0.55, 6.42, 12.28, 0.45,
        "This is not modesty. Reading public sources only is what makes an assessment possible "
        "WITHOUT the target's authorisation, which is the entire reason you can run one before "
        "the first meeting.", 10, CYAN, TEXT, space=1.24)

    # =========================================================================================
    # 12 — HOW IT WORKS
    # =========================================================================================
    s = d.slide("under the hood", "One name. Four models.", " Code decides.",
                sub="The models write the prose and argue about the judgement calls. They never "
                    "decide whether something ships.",
                footer=FOOT)
    steps = [
        ("1", "RESOLVE", "From one name: address space, certificates, group structure, DNS. "
                         "Nothing is typed in by an operator."),
        ("2", "GUARD", "Ownership gate, co-tenant guard, attribution gate, per-domain budget. "
                       "Most candidate hosts are refused here."),
        ("3", "CLASSIFY", "Deterministic detectors turn evidence into findings with severities. "
                          "No model is involved in this step."),
        ("4", "WRITE", "A model writes the business prose. A model from a DIFFERENT VENDOR then "
                       "audits it for false positives."),
        ("5", "RENDER", "Five artifacts, in the reader's language, in the partner's branding if "
                        "they have uploaded a template."),
    ]
    for i, (n, h, b) in enumerate(steps):
        x = 0.50 + i * 2.53
        _rect(s, x, 2.20, 2.36, 3.35, INK, LINE)
        _tb(s, x + 0.22, 2.42, 1.90, 0.45, n, 22, CYAN, DISPLAY, True)
        _tb(s, x + 0.22, 2.95, 1.94, 0.32, h, 12, WHITE, DISPLAY, True)
        _tb(s, x + 0.22, 3.35, 1.94, 2.00, b, 9, BODY, TEXT, space=1.26)
        if i < len(steps) - 1:
            _tb(s, x + 2.33, 3.55, 0.24, 0.30, ">", 14, VIOLET, MONO, True)
    _rect(s, 0.50, 5.75, 12.33, 0.90, PANEL, VIOLET)
    _tb(s, 0.76, 5.92, 11.81, 0.60,
        "THE AUDITOR IS NEVER THE AUTHOR, AND NEVER THE SAME VENDOR. A model reviewing its own "
        "work agrees with itself, and a provider-wide outage or quota limit takes down every "
        "model behind one badge at the same moment. Four vendors, so no shared failure domain.",
        10, BODY, TEXT, space=1.26)

    # =========================================================================================
    # 13 — WHY THE OUTPUT CAN BE TRUSTED
    # =========================================================================================
    s = d.slide("credibility", "Why you can put your name on it",
                sub="Every one of these exists because it was got wrong once, in a real customer "
                    "deck, and the fix was made into a check that fails the build.",
                footer=FOOT)
    bullets(s, 0.50, 2.20, 6.05, [
        "NO FINDING WITHOUT EVIDENCE. Every claim names the address, port, banner or certificate "
        "behind it.",
        "ABSENCE OF EVIDENCE IS NEVER A FINDING. A lookup that fails is reported as unknown, not "
        "as a customer weakness.",
        "NO INVENTED IDENTIFIERS. Any CVE the model writes is cross-checked against the CVEs "
        "actually present in the scan evidence, and stripped if it is not there.",
        "THE REGULATOR MATCHES THE CUSTOMER. The framework set follows their country, so nobody "
        "is shown a law that does not apply to them.",
    ], size=10.5, gap=0.66)
    bullets(s, 6.78, 2.20, 6.05, [
        "SEVERITY COLOURS ARE NEVER RE-BRANDED. Critical stays red even in a partner's own "
        "palette, because those colours carry meaning for the reader.",
        "AN EMPTY RESULT IS AN HONEST RESULT. \"Nothing of yours is externally observable\" is a "
        "true and saleable finding for a company that lives on shared hosting.",
        "THE COST OF EVERY RUN IS RECORDED in a ledger that survives log retention, so the "
        "economics are a fact rather than an estimate.",
        "THE ENGINE IS VERIFIED BY HASH after every deploy, so the container that answers is "
        "provably running the code that was tested.",
    ], size=10.5, gap=0.66, dot=VIOLET)

    # =========================================================================================
    # 14 — CLOSE
    # =========================================================================================
    s = d.slide("next", [("PICK A COMPANY.", WHITE), ("WATCH.", CYAN)],
                footer=FOOT, hero=True)
    _tb(s, 0.52, 4.30, 7.90, 1.00,
        "Bring a name to the next call. Any name: a prospect, a customer, your own group. The run "
        "takes minutes and nothing is sent to them, so there is nothing to arrange first.",
        13, BODY, TEXT, space=1.35)
    for i, (h, b) in enumerate((("SEE IT", "cybergod.ai/demo\nReal deliverables, invented company"),
                                ("RUN IT", "An account, and a name to type"),
                                ("SELL IT", "Your brand on every artifact"))):
        _rect(s, 8.60 + i * 1.45, 4.28, 1.32, 1.55, INK, LINE)
        _tb(s, 8.76 + i * 1.45, 4.46, 1.05, 0.30, h, 11, CYAN, DISPLAY, True)
        _tb(s, 8.76 + i * 1.45, 4.80, 1.05, 0.95, b, 8, BODY, TEXT, space=1.2)
    _tb(s, 0.52, 5.60, 7.90, 0.40, "www.cybergod.ai", 16, CYAN, DISPLAY, True)

    return d.save(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--template", default=TEMPLATE)
    a = ap.parse_args(argv)
    if not os.path.isfile(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    p = build(a.template, a.out)
    print("wrote %s (%.0f KB)" % (p, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
