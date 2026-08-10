#!/usr/bin/env python3
"""build_consensus_business_deck.py — the 4-model consensus as a BUSINESS capability.

Audience: sales and partners. The engineering deep-dive (build_consensus_deck.py) argues the
mechanism; this one argues the market. It reuses that file's Deck/card/bullets/stat helpers, so the
S4biz template exists in exactly ONE implementation and the two decks cannot drift apart.

    python marketing/build_consensus_business_deck.py [--out PATH] [--template PATH]

THREE RULES THIS DECK OBEYS, all of them decided with the operator (9 Aug 2026):

1. NO UNSUBSTANTIATED COMPARISON AGAINST A NAMED PRODUCT. We have never benchmarked against
   Claude, ChatGPT or Gemini, so the comparison slide argues ARCHITECTURE, which is structurally
   true and checkable, plus our OWN catch ledger. An unsubstantiated superiority claim against a
   named competitor is comparative advertising under UWG §6 and the UCP Directive, and it is
   exactly what a bank's or a ministry's counsel asks for the methodology behind. The architecture
   argument is stronger anyway: it cannot be refuted by a new model release.

2. EVERY NUMBER IS EITHER OURS AND MEASURED, OR EXTERNAL AND CITED. The operating numbers come
   from this repository and the live cost ledger. The market figures carry their source ON THE
   SLIDE and are labelled ILLUSTRATIVE, because they are benchmarks for comparable services, not
   our quotes. Nothing here is invented, which is the same discipline the assessment engine
   enforces on itself: no finding without evidence.

3. INTELLIGENCE SERVICES ARE ADDRESSED BY MISSION, NOT AS PROSPECTS. Naming an agency as a target
   in a document that circulates is a problem in itself. The slides describe the mission (national
   CERT, counter-intelligence vetting, critical-infrastructure protection) and list the services
   once, as the category of buyer.
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
from pptx.enum.text import PP_ALIGN  # noqa: E402

FOOT = "S4BIZ GROUP · CYBERGOD LLC · INTERNAL SALES + PARTNER MATERIAL · NOT FOR CUSTOMER DISTRIBUTION"


def table(s, x, y, w, cols, rows, widths, head_col=CYAN, size=9.2, rh=0.42):
    """A plain table. Column widths are FRACTIONS of w and must sum to 1."""
    assert abs(sum(widths) - 1.0) < 0.01, "column widths must sum to 1"
    cx = x
    for c, fr in zip(cols, widths):
        _tb(s, cx, y, w * fr, 0.28, c.upper(), 8.6, head_col, MONO, True)
        cx += w * fr
    _rect(s, x, y + 0.30, w, 0.012, LINE, None)
    yy = y + 0.40
    for i, row in enumerate(rows):
        if i % 2 == 1:
            _rect(s, x - 0.08, yy - 0.05, w + 0.16, rh, PANEL, None)
        cx = x
        for cell, fr in zip(row, widths):
            _tb(s, cx, yy, w * fr - 0.10, rh, cell, size, BODY, TEXT, space=1.15)
            cx += w * fr
        yy += rh
    return yy


# MEASURED FROM THE ACTUAL RENDER, not chosen. Two observations bound it:
#   49 chars ("Government, law enforcement and national security") renders on ONE line;
#   53 chars ("Ten industries where 'confidently wrong' is expensive") WRAPS and the second line
#   lands on the sub-heading at y=1.55.
# So the true limit is somewhere in 49..52. The cap is set at the lower end of that interval
# rather than bumped until the build went green -- picking 49 because it is observed to fit, not
# because it makes my next title pass.
TITLE_MAX = 50


def _check_title(title, tail):
    """A fixed-height title row is arithmetic, not taste.

    The box is 0.70in at 30pt, so a second line needs ~1.04in and lands on the sub-heading at
    y=1.55. Slide 11 shipped exactly that collision in the first render. Same defect class as the
    site header row, which this repository has already paid for twice.
    """
    n = len(title) + len(tail or "")
    if n > TITLE_MAX:
        raise SystemExit(
            "[X] title is %d characters and wraps onto the sub-heading (max %d): %r"
            % (n, TITLE_MAX, (title + (tail or ""))))
    return n


def build(template, out):
    d = Deck(template)

    # Every non-hero title goes through the width check. Wrapping the method here keeps the guard
    # impossible to forget on a new slide, rather than relying on me remembering to call it.
    _orig_slide = d.slide

    def _guarded(eyebrow, title, title_tail=None, sub=None, footer="", hero=False):
        if not hero:
            _check_title(title, title_tail)
        return _orig_slide(eyebrow, title, title_tail, sub, footer, hero)

    d.slide = _guarded

    # =========================================================================================
    # 01 — TITLE
    # =========================================================================================
    d.slide("S4biz · Cybergod · sales + partner briefing · August 2026",
            [("FOUR MODELS.", WHITE), ("ONE VERDICT.", VIOLET),
             ("EVERY PROCESS YOU RUN.", CYAN)],
            hero=True, footer=FOOT)

    # =========================================================================================
    # 02 — THE ONE IDEA
    # =========================================================================================
    s = d.slide("the problem", "One model is one ", "point of failure",
                sub="Not a capability problem. A structural one.", footer=FOOT)
    card(s, 0.55, 2.05, 3.90, 3.05, "single model", RED, "One opinion",
         "It has one training corpus, one set of blind spots and one failure mode. When it is "
         "wrong it is wrong CONFIDENTLY, in fluent prose, with no signal that anything is "
         "different from when it is right.")
    card(s, 4.72, 2.05, 3.90, 3.05, "self-review", AMBER, "Marking its own work",
         "Asking the same model to check its own answer inherits the same blind spot. It agrees "
         "with itself for the same reason it was wrong: the flaw is in the model, not in the "
         "effort it applied.")
    card(s, 8.89, 2.05, 3.90, 3.05, "one vendor", RED, "One outage",
         "A rate limit, a policy change or a capacity incident is provider-wide. When your one "
         "model is unavailable, so is the entire control that depended on it.")
    _tb(s, 0.55, 5.45, 12.20, 0.90,
        "The question is not whether AI is good enough. It is: WHO CHECKS IT, and what happens "
        "on the day it is confidently wrong in something you shipped, filed or reported?",
        14, WHITE, DISPLAY, True, space=1.20)

    # =========================================================================================
    # 03 — HOW IT WORKS
    # =========================================================================================
    s = d.slide("the mechanism", "Two build. Two attack. ", "Code decides.",
                sub="The same pattern works for code, tests, findings, configuration and reports.",
                footer=FOOT)
    card(s, 0.55, 2.00, 2.95, 2.30, "step 1", CYAN, "Two soldiers",
         "Two models from two vendors produce the work independently. Not a discussion: two "
         "separate attempts at the same job.", bsize=9.5)
    card(s, 3.75, 2.00, 2.95, 2.30, "step 2", VIOLET, "Two auditors",
         "Two DIFFERENT models from two other vendors review it. The auditor is never the author "
         "and never the author's vendor.", bsize=9.5)
    card(s, 6.95, 2.00, 2.95, 2.30, "step 3", INDIGO, "Deterministic gate",
         "Code decides pass or fail against measurable checks. The models supply reasoning and "
         "dissent. They never hold the switch.", bsize=9.5)
    card(s, 10.15, 2.00, 2.62, 2.30, "step 4", GREEN, "Written record",
         "Every verdict, agreement and dissent is recorded and delivered. An auditor can read why "
         "a decision was made.", bsize=9.5)
    _rect(s, 0.55, 4.60, 12.22, 0.012, LINE, None)
    _tb(s, 0.55, 4.80, 12.20, 0.40, "WHY THE GATE IS CODE AND NOT A MODEL", 11, CYAN, MONO, True)
    bullets(s, 0.55, 5.25, 12.20, [
        "A rate-limited model must never be able to block a good release, and an agreeable model "
        "must never be able to wave through a broken one. Both directions are failure.",
        "Models are a SIGNAL, not an authority. When three of four agree and the measurement "
        "disagrees, the measurement wins and the disagreement is escalated to a human.",
    ], size=10.5)

    # =========================================================================================
    # 04 — FOUR VENDORS, NOT FOUR PROMPTS
    # =========================================================================================
    s = d.slide("the design rule", "Four vendors. ", "Not four hats on one model.",
                sub="This is the difference between a real control and the appearance of one.",
                footer=FOOT)
    bullets(s, 0.60, 2.05, 6.00, [
        "NO SHARED FAILURE DOMAIN. A provider-wide rate limit or outage silences one voice, not "
        "the panel. We have watched exactly this happen and the review continued.",
        "NO SHARED BLIND SPOT. Different corpora and different training regimes fail on different "
        "inputs. Four hats on one model share every weakness the model has.",
        "NO SHARED REFUSAL. Vendors draw safety and policy lines differently. One vendor "
        "declining a legitimate task does not stop the work.",
        "NO SHARED COMMERCIAL RISK. Pricing, terms and availability change. Four vendors is also "
        "a procurement position, not only an engineering one.",
    ], size=10.5, gap=0.60)
    card(s, 7.00, 2.05, 5.75, 2.05, "the rule we enforce", VIOLET,
         "The auditor is never the author",
         "Our own code refuses to let a model review its own output, and prefers an auditor from a "
         "different vendor. If it cannot find one, it declines to audit rather than pretend.",
         bsize=10)
    card(s, 7.00, 4.30, 5.75, 2.05, "and the honest limit", AMBER,
         "Consensus is not truth",
         "Four models can agree and still be wrong. That is precisely why the gate is "
         "deterministic and why every verdict is written down for a human to read.", bsize=10)

    # =========================================================================================
    # 05 — OUR OWN LEDGER: WHAT IT CAUGHT
    # =========================================================================================
    s = d.slide("evidence", "What the panel actually ", "caught in our own build",
                sub="Not a study. Our own engineering record, kept because we act on it.",
                footer=FOOT)
    rows = [
        ["Identified a disabled admin interface from an md5 hash alone",
         "One model recognised d41d8cd98f00 as the hash of the EMPTY STRING", "Config exposure"],
        ["Twice caught a check whose DETAIL contradicted its own VERDICT",
         "The tell for 'the check is broken, not the system'", "False confidence"],
        ["'Passing the test proves it ran, not that it was correct'",
         "Produced a content check on the artefact, not just an exit code", "Silent failure"],
        ["'One bad block takes every domain down'",
         "Produced config-drift detection and a refusal path", "Total outage"],
        ["'A vhost that appears should fail, like one that disappears'",
         "Produced unexpected-host reporting on a shared estate", "Traffic hijack"],
        ["'Nothing proves a CHANGED config reaches the running process'",
         "Produced a live propagation test on the staging twin", "Latent outage"],
    ]
    table(s, 0.60, 2.05, 12.15, ["what a reviewer said", "what it produced", "class of failure"],
          rows, [0.42, 0.40, 0.18], rh=0.62)
    _tb(s, 0.60, 6.15, 12.15, 0.60,
        "Every one of these became a permanent automated check. That is the compounding return: "
        "the panel does not just catch the defect, it converts it into something that can never "
        "recur silently.", 11, WHITE, TEXT, space=1.25)

    # =========================================================================================
    # 06 — AND WHERE IT WAS WRONG
    # =========================================================================================
    s = d.slide("evidence", "And where the panel was ", "wrong",
                sub="We publish this because a vendor who only shows you the wins is selling you "
                    "something else.", footer=FOOT)
    card(s, 0.55, 2.05, 3.90, 2.55, "wrong", RED, "Inverted a check",
         "One reviewer argued a check meant the opposite of what it measured. It was refuted by "
         "the check's own output, not by opinion.", bsize=9.5)
    card(s, 4.72, 2.05, 3.90, 2.55, "wrong", RED, "Invented architecture",
         "Proposed fixes to a job queue, an environment variable and a Kubernetes manifest, none "
         "of which exist in the system it was reviewing.", bsize=9.5)
    card(s, 8.89, 2.05, 3.90, 2.55, "weak", AMBER, "Restated the problem",
         "One model repeatedly described the failure back as its own diagnosis, adding no "
         "information.", bsize=9.5)
    _tb(s, 0.55, 4.95, 12.20, 0.35, "THE PATTERN, AND IT IS THE PRODUCT INSIGHT", 11, CYAN, MONO, True)
    bullets(s, 0.55, 5.35, 12.20, [
        "Models reason WELL from evidence placed in front of them, and UNRELIABLY when "
        "extrapolating to things they cannot see. So: give them more evidence, never more authority.",
        "That single sentence is why the gate is deterministic, why dissent is recorded rather "
        "than resolved, and why a human sees the disagreement.",
    ], size=10.5)

    # =========================================================================================
    # 07 — SINGLE AI vs CONSENSUS  (architecture, no benchmark claim)
    # =========================================================================================
    s = d.slide("comparison", "One model, or ", "an adversarial panel",
                sub="Compared on architecture, which is checkable. We have not benchmarked against "
                    "named products and do not claim to have.", footer=FOOT)
    rows = [
        ["Failure domain", "One vendor: an outage or rate limit stops the control",
         "Four vendors: the review continues on three"],
        ["Blind spots", "One corpus, one set of systematic errors",
         "Different corpora fail on different inputs"],
        ["Review", "Self-review inherits the same blind spot",
         "Auditor is never the author, and prefers another vendor"],
        ["Who decides", "The model's confidence is the signal",
         "Deterministic checks decide; models advise"],
        ["Disagreement", "Invisible: one answer, no dissent to see",
         "Recorded and delivered, including the minority view"],
        ["Being wrong", "Fluent and confident, indistinguishable from right",
         "Contradicted by three others and by measurement"],
        ["Auditability", "A prompt and an answer", "A written verdict per reviewer, per release"],
    ]
    table(s, 0.60, 2.10, 12.15, ["dimension", "single model (any vendor)", "4-model consensus"],
          rows, [0.20, 0.40, 0.40], rh=0.56)
    _tb(s, 0.60, 6.30, 12.15, 0.50,
        "Frontier models are excellent and getting better. None of the rows above is fixed by a "
        "better model, because every one of them is a property of using exactly one.",
        11, WHITE, TEXT, space=1.2)

    # =========================================================================================
    # 08 — FOUR PROCESSES
    # =========================================================================================
    s = d.slide("where it applies", "The same pattern, ", "four business processes",
                sub="The pattern is domain-independent: produce, review adversarially, decide "
                    "deterministically, record.", footer=FOOT)
    card(s, 0.55, 2.00, 2.95, 2.45, "development", CYAN, "Code + design",
         "Two models implement, two review for defects, security and maintainability. Tests and "
         "linters decide. Dissent goes to the reviewer, not to the merge button.", bsize=9.2)
    card(s, 3.75, 2.00, 2.95, 2.45, "testing", VIOLET, "Test + evidence",
         "One model writes tests, another attacks them: does this test PASS when the behaviour is "
         "broken? Vacuous tests are the defect nobody sees.", bsize=9.2)
    card(s, 6.95, 2.00, 2.95, 2.45, "cyber security", INDIGO, "Findings + triage",
         "One model writes the finding, a different vendor audits it for false positives. "
         "Ownership evidence decides what ships to the customer.", bsize=9.2)
    card(s, 10.15, 2.00, 2.62, 2.45, "observability", GREEN, "Incident + RCA",
         "Panel reads the telemetry and proposes causes. Measurement confirms or refutes. The "
         "disagreement is often the fastest route to the answer.", bsize=9.2)
    _tb(s, 0.55, 4.75, 12.20, 0.35, "THE COMMON FAILURE IN ALL FOUR", 11, CYAN, MONO, True)
    bullets(s, 0.55, 5.15, 12.20, [
        "Something passes that should not have. A test that cannot fail. A finding nobody checked. "
        "A dashboard that is green because the check stopped running.",
        "One reviewer with a different blind spot is the cheapest possible way to find it, and it "
        "costs a fraction of the work being reviewed.",
    ], size=10.5)

    # =========================================================================================
    # 09 — OUR OWN NUMBERS
    # =========================================================================================
    s = d.slide("our own usage", "What it costs us, ", "measured",
                sub="From this system's own repository and live cost ledger, August 2026. Not "
                    "projections.", footer=FOOT)
    stat(s, 0.60, 2.05, 2.30, "43", "DETERMINISTIC CHECKS\nTHE PANEL REVIEWS\nEVERY RELEASE")
    stat(s, 3.05, 2.05, 2.30, "426", "AUTOMATED ASSERTIONS\nBEHIND THEM\n(64 UNIT + 362 ENGINE)", VIOLET)
    stat(s, 5.50, 2.05, 2.30, "11", "ENGINE REGRESSION\nSUITES, EACH FROM\nA REAL INCIDENT", INDIGO)
    stat(s, 7.95, 2.05, 2.30, "170", "DEFECT CLASSES\nDOCUMENTED AND\nPERMANENTLY GATED", GREEN)
    stat(s, 10.40, 2.05, 2.35, "4", "VENDORS, SO NO\nSINGLE OUTAGE\nSILENCES REVIEW", CYAN)
    _rect(s, 0.60, 4.10, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 4.30, 12.15, 0.35, "AND WHAT THE AI ITSELF COSTS TO RUN", 11, CYAN, MONO, True)
    stat(s, 0.60, 4.72, 3.00, "$0.0049", "AVERAGE AI COST PER\nCOMPLETED ASSESSMENT", GREEN, vsize=26)
    stat(s, 3.90, 4.72, 3.00, "183", "ASSESSMENTS RUN\nON THAT LEDGER", WHITE, vsize=26)
    stat(s, 7.20, 4.72, 3.00, "$0.89", "TOTAL AI SPEND,\nLIFETIME, ALL RUNS", CYAN, vsize=26)
    _tb(s, 10.45, 4.72, 2.30, 1.30,
        "Four models cost roughly four inference calls. The reviewed work is worth thousands of "
        "times that.", 10, BODY, TEXT, space=1.25)

    # =========================================================================================
    # 10 — THE ECONOMICS
    # =========================================================================================
    s = d.slide("the economics", "Why one caught defect ", "pays for the year",
                sub="External benchmarks, cited. Illustrative of scale, not a quotation.",
                footer=FOOT)
    card(s, 0.55, 2.05, 3.90, 2.65, "defect economics", CYAN, "1x -> 100x",
         "A defect costs about 1x to fix in design, 6.5x in implementation, 15x in testing and "
         "60-100x after release. Adversarial review moves the catch to the left of that curve.\n"
         "Source: IBM Systems Sciences Institute; corroborated by NIST and Capers Jones.",
         bsize=9.2)
    card(s, 4.72, 2.05, 3.90, 2.65, "breach economics", RED, "$4.44m",
         "Global average cost of a data breach in 2025, falling 9% year on year, with faster "
         "detection and automation cited as the main driver. United States average: $10.22m.\n"
         "Source: IBM Cost of a Data Breach Report 2025.", bsize=9.2)
    card(s, 8.89, 2.05, 3.90, 2.65, "assurance spend", VIOLET, "$5k-$30k",
         "Typical external penetration test or attack-surface engagement, with an all-types "
         "average near $18.3k and external network scope commonly $5k-$20k.\n"
         "Source: published 2026 pricing guides, aggregated.", bsize=9.2)
    _tb(s, 0.55, 5.00, 12.20, 1.10,
        "THE ARGUMENT IN ONE LINE: the review costs cents, the defect costs multiples of the "
        "build, and the incident costs multiples of the year. You are not buying AI. You are "
        "buying the thing that stops a confident answer becoming an incident.",
        13.5, WHITE, DISPLAY, True, space=1.22)

    # =========================================================================================
    # 11 — TOP 10 INDUSTRIES
    # =========================================================================================
    s = d.slide("market", "Ten industries, ", "ranked by cost of error",
                sub="Ranked by how directly a confident wrong answer converts into loss.",
                footer=FOOT)
    rows = [
        ["1", "Financial services", "Model risk, credit and AML decisions, regulatory reporting",
         "Dissent must be evidenced, not resolved"],
        ["2", "Pharmaceutical / life sciences", "GxP validation, batch review, submission dossiers",
         "Every automated decision needs an audit trail"],
        ["3", "Automotive / manufacturing", "Supplier code, OT segmentation, type-approval evidence",
         "A production stop dwarfs the software cost"],
        ["4", "Telecommunications", "Network change review, config drift, service assurance",
         "One bad config reaches every subscriber"],
        ["5", "Government + defence", "Assessment, vetting, procurement and infrastructure review",
         "Sovereign control and a written record"],
        ["6", "Energy + utilities", "Grid and plant OT exposure, NIS2 duties", "Safety, not data"],
        ["7", "Healthcare providers", "Clinical systems, device estates, patient data",
         "Availability is a clinical outcome"],
        ["8", "Insurance", "Underwriting logic, claims automation, cyber risk pricing",
         "Systematic bias compounds silently"],
        ["9", "Logistics + transport", "Scheduling, customs data, terminal OT", "Delay is the loss"],
        ["10", "Professional + legal services", "Due diligence, disclosure review, client reporting",
         "One invented citation ends a career"],
    ]
    table(s, 0.60, 2.05, 12.15, ["#", "industry", "where the panel is applied", "why it matters here"],
          rows, [0.04, 0.22, 0.40, 0.34], rh=0.44)

    # =========================================================================================
    # 12 — PHARMA + FSI
    # =========================================================================================
    s = d.slide("use cases", "Pharmaceutical ", "and financial services",
                sub="Both are regulated on the same principle: you must be able to show WHY a "
                    "decision was made.", footer=FOOT)
    _tb(s, 0.55, 1.95, 6.00, 0.32, "PHARMACEUTICAL / LIFE SCIENCES", 11, CYAN, MONO, True)
    bullets(s, 0.55, 2.35, 6.00, [
        "COMPUTERISED SYSTEM VALIDATION. Two models draft the validation evidence, two attack it "
        "for gaps. Deterministic checks confirm the artefacts exist and match the system.",
        "SUBMISSION AND DOSSIER REVIEW. An independent reviewer that is not the author, applied "
        "before a regulator applies one.",
        "MANUFACTURING OT EXPOSURE. Plant and building systems reachable from the internet, where "
        "the loss event is a stopped batch and a spoiled lot, not a data leak.",
        "SUPPLIER AND CDMO ASSURANCE. Continuous external review of partners who touch product "
        "data, at a cost that permits doing it for all of them.",
    ], size=9.8, gap=0.56)
    _tb(s, 6.95, 1.95, 5.80, 0.32, "FINANCIAL SERVICES", 11, VIOLET, MONO, True)
    bullets(s, 6.95, 2.35, 5.80, [
        "MODEL RISK MANAGEMENT. Regulators already require independent challenge of models. An "
        "adversarial panel is that challenge, applied continuously rather than annually.",
        "CHANGE AND RELEASE CONTROL. Two implementers, two reviewers, deterministic gate, written "
        "record: the shape supervisors already ask for.",
        "THIRD-PARTY AND SUPPLY-CHAIN RISK. External assessment of every counterparty, priced so "
        "that the whole book is covered rather than the top twenty.",
        "REGULATORY REPORTING. A second and third opinion before a filing, with dissent preserved "
        "for the file rather than averaged away.",
    ], size=9.8, gap=0.56, dot=VIOLET)

    # =========================================================================================
    # 13 — AUTOMOTIVE + TELECOM
    # =========================================================================================
    s = d.slide("use cases", "Automotive ", "and telecommunications",
                sub="Two industries where the loss event is production or service, not records.",
                footer=FOOT)
    _tb(s, 0.55, 1.95, 6.00, 0.32, "AUTOMOTIVE / MANUFACTURING", 11, CYAN, MONO, True)
    bullets(s, 0.55, 2.35, 6.00, [
        "OT AND PLANT EXPOSURE. Building services, ventilation, access control and automation "
        "reachable from the internet. The Jaguar Land Rover intrusion of September 2025 halted "
        "vehicle production for weeks; the Cyber Monitoring Centre assessed roughly GBP 1.9bn of "
        "UK economic damage across more than 5,000 organisations.",
        "SUPPLIER CODE AND FIRMWARE REVIEW. Adversarial review of what arrives from tier-one and "
        "tier-two suppliers, before it is in a vehicle.",
        "TYPE-APPROVAL AND TISAX EVIDENCE. Independent challenge of the evidence pack before the "
        "auditor provides it for free.",
    ], size=9.8, gap=0.56)
    _tb(s, 6.95, 1.95, 5.80, 0.32, "TELECOMMUNICATIONS", 11, VIOLET, MONO, True)
    bullets(s, 6.95, 2.35, 5.80, [
        "NETWORK CHANGE REVIEW. A configuration change reaches every subscriber at once. Two "
        "reviewers and a deterministic check before it is applied.",
        "CONFIG DRIFT ON SHARED INFRASTRUCTURE. What is RUNNING versus what the file says. We "
        "built this for ourselves after a shared proxy served stale configuration for twelve "
        "hours without a single alert.",
        "SERVICE ASSURANCE AND RCA. Panel-generated hypotheses, confirmed by measurement, during "
        "an incident when the on-call engineer is one person.",
        "WHOLESALE AND PARTNER ESTATES. External assessment of every interconnect partner.",
    ], size=9.8, gap=0.56, dot=VIOLET)

    # =========================================================================================
    # 14 — GOVERNMENT / LAW ENFORCEMENT / NATIONAL SECURITY
    # =========================================================================================
    s = d.slide("public sector", "Government, law enforcement ", "and national security",
                sub="Described by MISSION. Named services are the category of buyer, not "
                    "prospects, and no engagement is implied.", footer=FOOT)
    rows = [
        ["National CERT / CSIRT",
         "Continuous external review of the national critical-infrastructure estate; operators "
         "notified of exposure they cannot see themselves",
         "Volume without proportional headcount"],
        ["Law enforcement, cyber unit",
         "Attribution support, infrastructure mapping from public sources, adversarial review of "
         "an analyst's hypothesis before it becomes a line of enquiry",
         "A second opinion that never gets tired"],
        ["Counter-intelligence / vetting",
         "Assessment of a supplier's or a candidate organisation's external footprint from public "
         "data only, with the evidence recorded",
         "Repeatable, defensible, no packets sent"],
        ["Critical-infrastructure protection",
         "Sector-wide exposure review: energy, water, transport, health",
         "Priced so the whole sector is covered"],
        ["Ministry / agency internal IT",
         "Development, testing and change control under an adversarial panel with a written record",
         "Audit trail by construction"],
    ]
    table(s, 0.60, 2.05, 12.15, ["mission", "how the panel is used", "why consensus specifically"],
          rows, [0.20, 0.52, 0.28], rh=0.68)
    _tb(s, 0.60, 5.85, 12.15, 1.00,
        "THE SOVEREIGNTY POINT, WHICH IS OFTEN THE DECIDING ONE: the panel is model-agnostic. It "
        "runs on whichever four providers a jurisdiction permits, including self-hosted "
        "open-weight models, and the deterministic gate is code you can read. Buyers in Germany, "
        "Israel, Ukraine, Uzbekistan, Kazakhstan and Azerbaijan face different constraints on "
        "which vendors may be used at all; the architecture does not care, and that is the point.",
        10.5, BODY, TEXT, space=1.25)

    # =========================================================================================
    # 15 — SELL ME THE PEN
    # =========================================================================================
    s = d.slide("how to sell it", "Sell me the ", "pen",
                sub="Do not sell four models. Create the need, then be the only answer to it.",
                footer=FOOT)
    card(s, 0.55, 2.00, 3.90, 2.30, "1. the question", CYAN, "Ask, do not pitch",
         "\"When your AI is confidently wrong in something you shipped or filed, who catches it, "
         "and how long does it take?\" Then stop talking. Most buyers have no answer.", bsize=9.5)
    card(s, 4.72, 2.00, 3.90, 2.30, "2. the tension", VIOLET, "Name the gap",
         "They already use AI. Their control for it is a human who is busy and trusts fluent "
         "prose. The gap is not capability, it is that nobody is checking.", bsize=9.5)
    card(s, 8.89, 2.00, 3.90, 2.30, "3. the answer", GREEN, "One sentence",
         "\"An adversarial panel where the auditor is never the author, and where code, not "
         "confidence, decides.\" That is the whole product.", bsize=9.5)
    _tb(s, 0.55, 4.60, 12.20, 0.35, "THE THREE LINES THAT CLOSE IT", 11, CYAN, MONO, True)
    bullets(s, 0.55, 5.00, 12.20, [
        "\"We are not selling you intelligence. You already have that. We are selling you "
        "DISAGREEMENT, on purpose, and a record of it.\"",
        "\"If four models from four vendors agree AND the measurement agrees, you can act. If they "
        "disagree, you have learned something before your customer did.\"",
        "\"Here is what it caught in our own build, and here is where it was wrong.\" Showing the "
        "misses is what makes the catches believable.",
    ], size=10.5, gap=0.55)

    # =========================================================================================
    # 16 — REVENUE MODEL
    # =========================================================================================
    s = d.slide("commercials", "Where the ", "revenue comes from",
                sub="ILLUSTRATIVE. Figures are external benchmarks for comparable services, not "
                    "our rates and not a quotation. Partners set their own.", footer=FOOT)
    rows = [
        ["Assessment, per engagement",
         "Comparable market: $5k-$20k external scope, ~$18.3k all-types average",
         "Volume: the panel makes many small engagements viable"],
        ["Change report, recurring",
         "Monthly or quarterly re-run showing only what changed",
         "The annuity. This is the line that compounds"],
        ["Remediation and services attach",
         "The assessment names the work; the work is the margin",
         "Typically the largest line for a service partner"],
        ["Licence resale",
         "Sold in packs or unlimited, earned on in its own right",
         "Margin without delivery effort"],
        ["Process assurance retainer",
         "Panel applied to the customer's own development, testing or change control",
         "Highest value, longest contract, hardest to displace"],
        ["White-label / OEM",
         "The panel inside the partner's own product or portal",
         "Platform economics rather than project economics"],
    ]
    y = table(s, 0.60, 2.05, 12.15, ["revenue line", "illustrative basis (sourced)", "why it works"],
              rows, [0.24, 0.44, 0.32], rh=0.58)
    _rect(s, 0.60, y + 0.10, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, y + 0.28, 12.15, 0.90,
        "THE ARITHMETIC THAT MATTERS: AI cost per assessment measured on our own ledger is "
        "$0.0049. Against a comparable market engagement of $5,000 the inference cost is under "
        "one thousandth of one per cent. Delivery effort and expertise are the real cost, which "
        "is exactly why volume is the strategy and why a partner keeps the margin.",
        10.5, WHITE, TEXT, space=1.25)

    # =========================================================================================
    # 17 — WHAT A PARTNER ACTUALLY SELLS
    # =========================================================================================
    s = d.slide("partner motion", "Four rungs. ", "Start low, climb.",
                sub="Each rung is a separate sale and each one qualifies the next.", footer=FOOT)
    card(s, 0.55, 2.05, 2.95, 2.60, "rung 1", CYAN, "One finding",
         "Send ONE real finding, not the report. It proves the capability in a single message and "
         "costs nothing to produce.", bsize=9.5)
    card(s, 3.75, 2.05, 2.95, 2.60, "rung 2", VIOLET, "The assessment",
         "The four documents plus the web report, under the partner's own name. Priced. This is "
         "the first invoice.", bsize=9.5)
    card(s, 6.95, 2.05, 2.95, 2.60, "rung 3", INDIGO, "The change report",
         "Recurring re-run showing only what changed since last time. The annuity, and the reason "
         "the account manager has a call each month.", bsize=9.5)
    card(s, 10.15, 2.05, 2.62, 2.60, "rung 4", GREEN, "Process assurance",
         "The panel applied to the customer's own development, testing and change control. The "
         "contract that does not get cancelled.", bsize=9.5)
    _tb(s, 0.55, 4.95, 12.20, 1.20,
        "WHY THE FIRST RUNG IS FREE AND WHY THAT IS NOT A DISCOUNT: one specific, verifiable "
        "finding about the prospect's own estate converts better than any deck, because it is "
        "about them. It also costs cents to produce, so a seller can do it for every account in "
        "their territory in a week. That asymmetry, not the price, is the commercial advantage.",
        11, WHITE, TEXT, space=1.25)

    # =========================================================================================
    # 18 — HOW TO START
    # =========================================================================================
    s = d.slide("next step", "What happens in the ", "next thirty days",
                sub="", footer=FOOT)
    bullets(s, 0.60, 2.10, 12.15, [
        "WEEK 1  ·  Pick five accounts in your territory. We produce one real finding for each, "
        "from public sources only, with no permission required and no packets sent to them.",
        "WEEK 2  ·  You send the findings. Not a deck, not a brochure: one specific, verifiable "
        "fact about their own estate, with the evidence attached.",
        "WEEK 3  ·  The conversations that come back become full assessments under your name. We "
        "support the first two calls with you.",
        "WEEK 4  ·  Agree the recurring change report on the first customer, and identify the one "
        "internal process where they would benefit from the panel themselves.",
    ], size=11.5, gap=0.80)
    _rect(s, 0.60, 5.75, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 5.95, 12.15, 0.80,
        "The only thing we need from you to begin is five company names. There is nothing to "
        "install, no access to grant, and nothing to ask the prospect for.",
        13, WHITE, DISPLAY, True, space=1.2)

    # =========================================================================================
    # 19 — SOURCES + CAVEATS
    # =========================================================================================
    s = d.slide("sources", "Sources ", "and what this deck does not claim",
                sub="", footer=FOOT)
    _tb(s, 0.60, 1.95, 6.00, 0.32, "EXTERNAL FIGURES", 11, CYAN, MONO, True)
    bullets(s, 0.60, 2.35, 6.00, [
        "Breach cost: IBM Cost of a Data Breach Report 2025. Global average $4.44m, down 9% year "
        "on year; United States average $10.22m.",
        "Defect cost multiplier: IBM Systems Sciences Institute (1x design, 6.5x implementation, "
        "15x testing, 60-100x post-release); direction corroborated by NIST and by Capers Jones.",
        "Assessment pricing: aggregated published 2026 penetration-testing pricing guides. "
        "$5k-$20k external scope, ~$18.3k all-types average.",
        "Jaguar Land Rover: Cyber Monitoring Centre assessment, October 2025.",
    ], size=9.5, gap=0.62)
    _tb(s, 6.95, 1.95, 5.80, 0.32, "OUR OWN FIGURES", 11, VIOLET, MONO, True)
    bullets(s, 6.95, 2.35, 5.80, [
        "Operating numbers are read from this system's own repository and live cost ledger in "
        "August 2026: 43 deterministic checks, 426 automated assertions, 11 regression suites, "
        "170 documented defect classes, 183 assessments at $0.0049 average AI cost.",
        "The catch ledger is our own engineering record, kept contemporaneously, including the "
        "cases where the panel was wrong.",
    ], size=9.5, gap=0.62, dot=VIOLET)
    _rect(s, 0.60, 5.30, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 5.50, 12.15, 1.30,
        "WHAT THIS DECK DOES NOT CLAIM. We have not run a controlled benchmark against Claude, "
        "ChatGPT or Gemini, and nothing here should be read as one. The comparison is "
        "architectural: it describes what follows from using one model rather than four, and every "
        "row of it can be checked without trusting us. Those products are excellent and improving; "
        "none of the properties we describe is fixed by a better model, because each is a "
        "consequence of using exactly one.",
        10.5, BODY, TEXT, space=1.28)

    # =========================================================================================
    # 20 — CLOSE
    # =========================================================================================
    d.slide("close",
            [("YOU ALREADY HAVE", MUTED), ("INTELLIGENCE.", WHITE),
             ("WE SELL YOU", MUTED), ("DISAGREEMENT.", CYAN)],
            hero=True, footer=FOOT)

    return d.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Consensus_For_Business.pptx"))
    a = ap.parse_args()
    p = build(a.template, a.out)
    print("built: %s" % p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
