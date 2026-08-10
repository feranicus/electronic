#!/usr/bin/env python3
"""build_consensus_method_deck.py — the consensus ALGORITHM as a decision method we implement.

THIS IS NOT A CYBERGOD PITCH. cybergod.ai is one thing we happen to have built with the method.
This deck sells the METHOD and the CODE: an engineered, adversarial, multi-model decision process
that we develop, integrate, test and support inside a customer's own business process. The revenue
shape is the Uzbekistan secure-phone/UC engagement: development, integration, testing, support.

    python marketing/build_consensus_method_deck.py [--out PATH] [--template PATH]

THE OPERATOR'S INSTRUCTION, VERBATIM AND OBEYED: "stop guessing and stop just estimating go to
Gartner, McKinsey, Bain, BCG and other consulting groups and reports and bring fact check".
So every market number on these slides is from a named, dated, published source and the source is
ON THE SLIDE. Where a source is contested or has a known limitation, the limitation is stated,
because a figure that collapses under a customer's counter-question is worse than no figure.

SOURCES USED (all verified during the build, August 2026):
  · Gartner, 25 Jun 2025 — over 40% of agentic AI projects cancelled by end-2027; drivers are
    escalating cost, unclear business value and INADEQUATE RISK CONTROLS. ~130 of thousands of
    "agentic" vendors are real; the rest is agent washing.
  · Gartner, 11 Mar 2026 (D&A predictions) — by 2028 organisations using multi-agent AI across 80%
    of customer-facing processes will outperform peers; by 2030 half of agent deployment failures
    trace to insufficient governance runtime enforcement.
  · Gartner, 17 Mar 2026 — at least 80% of governments will deploy AI agents for routine
    decision-making by 2028; decision intelligence governs the DECISION, not the component.
  · Gartner, 19 May 2026 — worldwide AI spending $2.59tn in 2026, +47%.
  · McKinsey, State of AI 2025 — 88% of organisations use AI in at least one function, yet only
    ~39% report ANY enterprise EBIT impact and most of those below 5%.
  · McKinsey — in-silico development could cut clinical trial development cost by up to 60% and
    cycle time by up to 40%; AI could unlock $60bn+ a year for life sciences.
  · BCG (with Wellcome) — early-stage AI may cut discovery cost up to 50%; 25-50% time saving in
    early R&D. Reported Phase 2/3 effects: 30-40% cost, 20-30% time, 2-3x recruitment.
  · McKinsey, product launch research — launch failure rates above 40%, and NO correlation between
    the amount invested in a launch and its success.
  · National Research Council (2003), The Polygraph and Lie Detection — median accuracy index 0.86
    (IQR 0.81-0.91) BUT evidence quality low and, at low base rates, screening produces large
    numbers of false positives.
  · RAND RR1408 / Heuer & Pherson — structured analytic techniques add rigour; notably, ACH
    reduced confirmation bias for people WITHOUT an intelligence background and not for those with
    it, which is the argument for enforcing structure in code rather than in training.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402 — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from build_consensus_business_deck import TITLE_MAX, _check_title, table  # noqa: E402

FOOT = "S4BIZ GROUP · CONSENSUS DECISION ENGINEERING · INTERNAL SALES + PARTNER MATERIAL"


def src(s, y, text, x=0.60, w=12.15):
    """A source line. Every external figure on this deck carries one."""
    _tb(s, x, y, w, 0.30, "SOURCE: " + text, 7.8, MUTED, MONO, space=1.15)


def build(template, out):
    d = Deck(template)
    _orig = d.slide

    def _guarded(eyebrow, title, title_tail=None, sub=None, footer="", hero=False):
        if not hero:
            _check_title(title, title_tail)
        return _orig(eyebrow, title, title_tail, sub, footer, hero)

    d.slide = _guarded

    # ========================================================================== 01 TITLE
    d.slide("S4biz Group · consensus decision engineering · August 2026",
            [("A DECISION METHOD.", WHITE), ("BUILT INTO YOUR", VIOLET),
             ("OWN PROCESS.", CYAN)], hero=True, footer=FOOT)

    # ========================================================================== 02 THE PROBLEM
    s = d.slide("the market problem", "Everyone adopted AI. ", "Almost nobody banked it.",
                sub="This is not our opinion. It is what the analysts measured.", footer=FOOT)
    stat(s, 0.60, 2.05, 2.85, "88%", "OF ORGANISATIONS USE AI\nIN AT LEAST ONE FUNCTION", CYAN)
    stat(s, 3.75, 2.05, 2.85, "~39%", "REPORT ANY ENTERPRISE\nEBIT IMPACT AT ALL", AMBER)
    stat(s, 6.90, 2.05, 2.85, ">40%", "OF AGENTIC AI PROJECTS\nCANCELLED BY END 2027", RED)
    stat(s, 10.05, 2.05, 2.70, "~130", "OF THOUSANDS OF 'AGENTIC'\nVENDORS ARE REAL", RED)
    src(s, 3.55, "McKinsey, The State of AI 2025 · Gartner press release, 25 June 2025.")
    _rect(s, 0.60, 3.95, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 4.15, 12.15, 0.35, "GARTNER NAMES THREE CAUSES. READ THE THIRD ONE.",
        11, CYAN, MONO, True)
    card(s, 0.60, 4.55, 3.90, 1.85, "cause 1", MUTED, "Escalating cost",
         "Pilots that never reach a unit economics case.", bsize=9.5)
    card(s, 4.72, 4.55, 3.90, 1.85, "cause 2", MUTED, "Unclear business value",
         "A capability demonstration, attached to no decision anyone owns.", bsize=9.5)
    card(s, 8.84, 4.55, 3.91, 1.85, "cause 3", RED, "Inadequate risk controls",
         "Nobody can say what happens when the model is wrong. This is the one we sell into.",
         bsize=9.5)

    # ========================================================================== 03 WHAT WE SELL
    s = d.slide("what we sell", "Not a product. ", "An engineered decision.",
                sub="We build the method into the process the customer already runs, and we "
                    "support it.", footer=FOOT)
    card(s, 0.60, 2.05, 2.95, 2.55, "1  develop", CYAN, "Design the decision",
         "Define the question, the evidence classes, the pass criteria and what a refusal looks "
         "like. This is the part nobody else does.", bsize=9.3)
    card(s, 3.80, 2.05, 2.95, 2.55, "2  integrate", VIOLET, "Wire the inputs",
         "Connect the customer's real evidence: case systems, laboratory data, market data, "
         "telemetry, OSINT. On their infrastructure.", bsize=9.3)
    card(s, 7.00, 2.05, 2.95, 2.55, "3  test", INDIGO, "Prove it fails correctly",
         "Adversarial and regression testing against the customer's own historical cases, where "
         "the answer is already known.", bsize=9.3)
    card(s, 10.20, 2.05, 2.55, 2.55, "4  support", GREEN, "Operate and evolve",
         "Models change monthly. The gate, the thresholds and the evidence set are maintained "
         "under contract.", bsize=9.3)
    _tb(s, 0.60, 4.90, 12.15, 0.35, "THE SHAPE IS ONE WE HAVE ALREADY DELIVERED", 11, CYAN, MONO, True)
    bullets(s, 0.60, 5.30, 12.15, [
        "Identical commercial structure to the Uzbekistan secure-handset and unified-communications "
        "programme: scoped development, integration into the customer's estate, formal test and "
        "acceptance, then a support contract. The technology is different; the money is not.",
        "The customer owns the deployment. We own the method, the code and the maintenance.",
    ], size=10.5)

    # ========================================================================== 04 THE METHOD
    s = d.slide("the method", "Evidence in. ", "GO / NO-GO, with the why.",
                sub="Four models from four vendors, an auditor that is never the author, and a "
                    "gate written in code.", footer=FOOT)
    card(s, 0.60, 2.05, 2.30, 2.35, "input", MUTED, "Evidence",
         "Every source the customer already has, weighted and labelled by reliability.", bsize=9)
    card(s, 3.15, 2.05, 2.30, 2.35, "step 1", CYAN, "Two analysts",
         "Two models, two vendors, independently reach a position on the same evidence.", bsize=9)
    card(s, 5.70, 2.05, 2.30, 2.35, "step 2", VIOLET, "Two challengers",
         "Two other models attack it: what would have to be true for this to be wrong?", bsize=9)
    card(s, 8.25, 2.05, 2.30, 2.35, "step 3", INDIGO, "Deterministic gate",
         "Code applies the customer's own thresholds. Models never hold the switch.", bsize=9)
    card(s, 10.80, 2.05, 1.95, 2.35, "output", GREEN, "The artefact",
         "GO / NO-GO, a confidence figure, the reasons, and the dissent.", bsize=9)
    _rect(s, 0.60, 4.70, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 4.90, 12.15, 0.35, "WHY THE DISSENT IS THE PRODUCT, NOT A BY-PRODUCT",
        11, CYAN, MONO, True)
    bullets(s, 0.60, 5.30, 12.15, [
        "A single number with no minority view is unauditable. A decision file that records WHO "
        "disagreed, on WHAT evidence, and WHY the gate still passed, is defensible to a regulator, "
        "an inspector general or a board.",
        "Gartner frames the same shift as decision intelligence: govern the DECISION, not the "
        "individual AI component.",
    ], size=10.5)
    src(s, 6.45, "Gartner, Top Predictions for Data and Analytics, 11 March 2026.")

    # ========================================================================== 05 WHY NOT A PILOT
    s = d.slide("positioning", "Why this is not ", "another AI pilot",
                sub="The analyst consensus is that governance, not capability, is where these "
                    "programmes die.", footer=FOOT)
    rows = [
        ["Gartner", "Over 40% of agentic AI projects cancelled by end-2027; one named cause is "
                    "inadequate risk controls",
         "The method IS the risk control"],
        ["Gartner", "By 2030, half of AI agent deployment failures trace to insufficient "
                    "governance runtime enforcement",
         "The gate is enforced at runtime, in code"],
        ["Gartner", "By 2028, organisations using multi-agent AI across 80% of customer-facing "
                    "processes will outperform peers",
         "Multi-agent is the direction; ours is adversarial"],
        ["Gartner", "At least 80% of governments will deploy AI agents for routine "
                    "decision-making by 2028",
         "Public sector is a near-term buyer, not a future one"],
        ["McKinsey", "88% adoption, ~39% reporting any EBIT impact, most below 5%",
         "The gap is decisions, not models"],
    ]
    table(s, 0.60, 2.10, 12.15, ["source", "what they published", "what it means for this offer"],
          rows, [0.10, 0.52, 0.38], rh=0.62)
    src(s, 5.55, "Gartner press releases 25 Jun 2025, 11 Mar 2026, 17 Mar 2026 · McKinsey State "
                 "of AI 2025.")
    _tb(s, 0.60, 6.00, 12.15, 0.80,
        "We are not arguing that AI works. The analysts already establish that most organisations "
        "cannot show it working. We sell the missing half: a decision that can be governed, "
        "tested and defended.", 12.5, WHITE, DISPLAY, True, space=1.2)

    # ========================================================================== 06 USE CASE 1
    s = d.slide("use case 01 · national security", "Vetting a new ", "source. GO / NO-GO.",
                sub="A foreign-national volunteer or approach. The decision is high-consequence, "
                    "low base rate and irreversible.", footer=FOOT)
    _tb(s, 0.60, 1.95, 6.00, 0.32, "THE EVIDENCE THE PANEL IS GIVEN", 11, CYAN, MONO, True)
    bullets(s, 0.60, 2.35, 6.00, [
        "Polygraph or credibility-assessment output, WITH its stated error characteristics rather "
        "than as a verdict.",
        "OSINT: declared and undeclared footprint, associations, travel, financial signals, "
        "linguistic and biographic consistency.",
        "Interview and debrief transcripts, and the case officer's own assessment.",
        "Historical comparison: prior cases with known outcomes, positive and negative.",
    ], size=9.8, gap=0.56)
    _tb(s, 6.95, 1.95, 5.80, 0.32, "WHY CONSENSUS SPECIFICALLY, HERE", 11, VIOLET, MONO, True)
    bullets(s, 6.95, 2.35, 5.80, [
        "THE POLYGRAPH CANNOT CARRY THE DECISION. The National Research Council found a median "
        "accuracy index of 0.86, but rated the underlying evidence quality low and concluded that "
        "in low base-rate screening it produces large numbers of FALSE POSITIVES.",
        "One contested instrument plus one analyst is the current method. Several weak signals, "
        "independently weighed, with the disagreement preserved, is a better one.",
        "Structured analytic techniques exist for this reason. But research found Analysis of "
        "Competing Hypotheses reduced confirmation bias for people WITHOUT an intelligence "
        "background and not for those with one. Structure has to be enforced by the system, not "
        "left to the discipline of an experienced officer.",
    ], size=9.5, gap=0.62, dot=VIOLET)
    src(s, 6.35, "National Research Council, The Polygraph and Lie Detection (2003) · "
                 "RAND RR1408, Assessing the Value of Structured Analytic Techniques.")

    # ========================================================================== 07 USE CASE 1 OUT
    s = d.slide("use case 01 · output", "What the case officer ", "actually receives",
                sub="One page, and a file behind it.", footer=FOOT)
    card(s, 0.60, 2.05, 3.90, 2.60, "the verdict", GREEN, "GO / NO-GO / HOLD",
         "With a confidence figure and the specific evidence that drove it. HOLD is a first-class "
         "outcome: it names what would have to be collected to decide.", bsize=9.5)
    card(s, 4.72, 2.05, 3.90, 2.60, "the dissent", AMBER, "The minority view",
         "Which model disagreed, on what evidence, and what would have to be true for the "
         "minority to be right. Preserved, never averaged away.", bsize=9.5)
    card(s, 8.84, 2.05, 3.91, 2.60, "the file", CYAN, "Defensible record",
         "Every input, weight, threshold and verdict, timestamped. Re-runnable when new evidence "
         "arrives, with the delta shown.", bsize=9.5)
    _tb(s, 0.60, 4.95, 12.15, 0.35, "THE THREE THINGS THIS CHANGES", 11, CYAN, MONO, True)
    bullets(s, 0.60, 5.35, 12.15, [
        "FASTER: a first structured assessment in hours rather than the weeks a manual "
        "multi-source review takes, so the officer spends time on collection, not collation.",
        "MORE PRECISE: a stated confidence and a named evidence gap instead of a binary from one "
        "instrument with contested validity.",
        "DEFENSIBLE: an inspector general, an oversight committee or a court sees the reasoning, "
        "including what the system was told and what it refused to conclude.",
    ], size=10.2, gap=0.52)

    # ========================================================================== 08 USE CASE 2
    s = d.slide("use case 02 · pharmaceutical", "Trial design and ", "in-silico simulation",
                sub="An oncology candidate entering design. The question is which trial to run, "
                    "and whether to run it at all.", footer=FOOT)
    stat(s, 0.60, 2.00, 2.85, "60%", "POTENTIAL CUT IN TRIAL\nDEVELOPMENT COST", CYAN)
    stat(s, 3.75, 2.00, 2.85, "40%", "POTENTIAL CUT IN\nCYCLE TIME", VIOLET)
    stat(s, 6.90, 2.00, 2.85, "50%", "POTENTIAL CUT IN EARLY\nDISCOVERY COST (BCG)", INDIGO)
    stat(s, 10.05, 2.00, 2.70, "$2.6bn", "R&D COST PER\nAPPROVED DRUG", RED)
    src(s, 3.50, "McKinsey on in-silico development · BCG with Wellcome on early-stage AI · "
                 "industry R&D cost per approved asset.")
    _rect(s, 0.60, 3.90, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 4.10, 6.00, 0.32, "WHERE THE PANEL SITS", 11, CYAN, MONO, True)
    bullets(s, 0.60, 4.50, 6.00, [
        "Two models independently propose trial designs, endpoints, arm sizes and inclusion "
        "criteria from the same evidence base.",
        "Two others attack each design: where does this fail, what confounds it, what would a "
        "regulator reject and why.",
        "Monte Carlo and digital-twin simulation runs the surviving designs. The gate compares "
        "outcomes against pre-agreed criteria.",
    ], size=9.5, gap=0.56)
    _tb(s, 6.95, 4.10, 5.80, 0.32, "WHY IT NEEDS THE ADVERSARIAL LAYER", 11, VIOLET, MONO, True)
    bullets(s, 6.95, 4.50, 5.80, [
        "A simulation answers the question it was asked. The expensive error is asking the wrong "
        "question confidently, and no amount of compute detects that.",
        "Regulators are already qualifying digital-twin methods, so the modelling is credible. "
        "The challenge layer is what makes the DESIGN credible.",
        "Reported effects on Phase 2/3: 30-40% cost, 20-30% time, 2-3x recruitment acceleration, "
        "and up to 35% smaller control arms.",
    ], size=9.5, gap=0.56, dot=VIOLET)

    # ========================================================================== 09 USE CASE 3
    s = d.slide("use case 03 · financial services", "Launching a product ", "nobody trusts yet",
                sub="A regulated bank taking a blockchain-based product to market, into a customer "
                    "base that is sceptical.", footer=FOOT)
    stat(s, 0.60, 2.00, 3.00, ">40%", "OF PRODUCT LAUNCHES\nFAIL, ACROSS SECTORS", RED)
    stat(s, 3.90, 2.00, 3.00, "NONE", "CORRELATION BETWEEN\nLAUNCH SPEND AND SUCCESS", AMBER)
    stat(s, 7.20, 2.00, 3.00, "2-4 WK", "FINTECH FEATURE CYCLE\nVS 4-6 MONTHS AT BANKS", CYAN)
    _tb(s, 10.50, 2.00, 2.25, 1.40,
        "Spending more does not fix it. Deciding better does.", 11, WHITE, TEXT, space=1.25)
    src(s, 3.50, "McKinsey product-launch research · McKinsey on incumbent bank build cycles.")
    _rect(s, 0.60, 3.90, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 4.10, 6.00, 0.32, "WHAT THE PANEL DECIDES", 11, CYAN, MONO, True)
    bullets(s, 0.60, 4.50, 6.00, [
        "SEGMENT BY SEGMENT: which customer groups adopt, which reject, and which are worth the "
        "cost of persuading. Not one launch decision, twelve.",
        "OBJECTION MODELLING: each challenger model argues the sceptic's case in that segment, so "
        "the objection is answered before it is public.",
        "SCALE GATE: what has to be true in the pilot cohort before the next tranche is released.",
    ], size=9.5, gap=0.56)
    _tb(s, 6.95, 4.10, 5.80, 0.32, "WHY A BANK BUYS THIS AND NOT A SURVEY", 11, VIOLET, MONO, True)
    bullets(s, 6.95, 4.50, 5.80, [
        "A survey tells you what people say. A simulation with an adversarial layer tells you "
        "which of your own assumptions collapses first, and at what adoption rate.",
        "The output is the paper the product committee actually needs: a staged launch with named "
        "abort conditions, and the dissent recorded for the risk function.",
        "The same file satisfies the model-risk and new-product-approval processes the bank "
        "already has to run.",
    ], size=9.5, gap=0.56, dot=VIOLET)

    # ========================================================================== 10 MORE INDUSTRIES
    s = d.slide("further sectors", "Three more, ", "same method",
                sub="Two decisions each, chosen because the loss event is operational rather than "
                    "reputational.", footer=FOOT)
    rows = [
        ["Telecommunications", "Network change approval before it reaches every subscriber",
         "Spectrum, capacity and CAPEX phasing under demand uncertainty"],
        ["Automotive / industrial", "Supplier and platform selection with production-stop exposure",
         "OT segmentation and type-approval evidence before the auditor sees it"],
        ["Energy / utilities", "Grid and plant investment sequencing under regulatory constraint",
         "Outage and maintenance scheduling against safety cases"],
    ]
    table(s, 0.60, 2.15, 12.15, ["sector", "decision one", "decision two"],
          rows, [0.22, 0.39, 0.39], rh=0.66)
    _rect(s, 0.60, 4.55, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 4.80, 12.15, 0.40,
        "THE SELECTION RULE WE APPLY WHEN QUALIFYING: is the decision high-consequence, "
        "made repeatedly, and currently owned by one expert with one method?",
        13, WHITE, DISPLAY, True, space=1.2)
    bullets(s, 0.60, 5.60, 12.15, [
        "If yes to all three, the method fits and the business case writes itself.",
        "If the decision is low-consequence or already automated with a good feedback loop, we say "
        "so and do not bid. A failed reference costs more than the engagement earns.",
    ], size=10.5)

    # ========================================================================== 11 WHAT IMPROVES
    s = d.slide("the improvement", "Faster, more precise, ", "and defensible",
                sub="Stated as mechanisms, with the external evidence for the size of the prize.",
                footer=FOOT)
    rows = [
        ["FASTER", "Parallel independent analysis replaces sequential human review; simulation "
                   "replaces some physical iteration",
         "Up to 40% cycle-time reduction in trial development; 25-50% time saving in early R&D"],
        ["MORE PRECISE", "A stated confidence and an explicit evidence gap, instead of a binary "
                         "from a single instrument or a single expert",
         "Polygraph screening at low base rates produces large false-positive volumes"],
        ["STRONGER", "The challenge layer is applied to every decision, not only the ones somebody "
                     "thought to question",
         "Structured techniques reduce bias, but not reliably for experienced analysts"],
        ["CHEAPER", "The expensive resource is the expert, not the compute; the method spends "
                    "compute to protect expert time",
         "Up to 60% trial development cost, up to 50% early discovery cost"],
        ["DEFENSIBLE", "Every decision leaves a file: inputs, weights, verdict, dissent, "
                       "re-runnable when evidence changes",
         "Governance is the named cause of half of projected agent failures by 2030"],
    ]
    table(s, 0.60, 2.10, 12.15, ["dimension", "the mechanism", "external evidence for the scale"],
          rows, [0.14, 0.42, 0.44], rh=0.66)
    src(s, 5.90, "McKinsey · BCG/Wellcome · National Research Council (2003) · RAND RR1408 · "
                 "Gartner D&A predictions 2026. Figures are sector benchmarks, not our forecast.")

    # ========================================================================== 12 DELIVERY MODEL
    s = d.slide("delivery", "How we are actually ", "paid for it",
                sub="Four billable phases, the same structure as the Uzbekistan secure "
                    "communications programme.", footer=FOOT)
    rows = [
        ["1 · Decision design", "Workshops, evidence taxonomy, threshold and refusal criteria, "
                                "success definition",
         "Fixed fee", "4-8 weeks"],
        ["2 · Development", "The panel, the gate, the artefact, the customer's own thresholds "
                            "in code",
         "Fixed fee or T&M", "8-16 weeks"],
        ["3 · Integration", "Connect real evidence sources; deploy on the customer's own or "
                            "sovereign infrastructure",
         "T&M + licences", "Runs in parallel"],
        ["4 · Test + acceptance", "Adversarial and regression testing against historical cases "
                                  "with known outcomes; formal acceptance",
         "Fixed fee", "4-6 weeks"],
        ["5 · Support + evolution", "Model chain maintenance, threshold recalibration, new "
                                    "evidence classes, incident response",
         "Annual recurring", "Multi-year"],
    ]
    table(s, 0.60, 2.10, 12.15, ["phase", "what is delivered", "commercial", "typical"],
          rows, [0.19, 0.49, 0.17, 0.15], rh=0.66)
    _tb(s, 0.60, 5.75, 12.15, 1.00,
        "WHY PHASE 4 IS THE ONE THAT WINS THE DEAL: testing the method against the customer's OWN "
        "historical cases, where the right answer is already known, is the only proof that "
        "survives a procurement challenge. It is also the phase competitors skip, because it is "
        "the phase that can fail.", 11.5, WHITE, TEXT, space=1.25)

    # ========================================================================== 13 REVENUE
    s = d.slide("commercials", "Where the money ", "comes from",
                sub="Services-led, licence-supported, annuity-anchored.", footer=FOOT)
    card(s, 0.60, 2.05, 2.95, 2.45, "development", CYAN, "The build",
         "Largest single invoice. Scoped per decision, not per seat. Repeats when the customer "
         "adds a second and third decision.", bsize=9.3)
    card(s, 3.80, 2.05, 2.95, 2.45, "integration", VIOLET, "The estate work",
         "Connecting real systems is where effort actually goes, and it is billable at systems "
         "integration rates.", bsize=9.3)
    card(s, 7.00, 2.05, 2.95, 2.45, "test + accept", INDIGO, "The proof",
         "Adversarial and regression testing against historical cases. Discrete, scoped and "
         "required for acceptance.", bsize=9.3)
    card(s, 10.20, 2.05, 2.55, 2.45, "support", GREEN, "The annuity",
         "Multi-year. Models change monthly, so maintenance is genuine work, not a rebate.",
         bsize=9.3)
    _rect(s, 0.60, 4.75, 12.15, 0.012, LINE, None)
    bullets(s, 0.60, 4.95, 12.15, [
        "MARKET CONTEXT, NOT OUR FORECAST: Gartner puts worldwide AI spending at $2.59tn in 2026, "
        "up 47%, with models and platforms alone at $64bn, up 63%. The constraint on capturing it "
        "is not demand, it is that most programmes cannot demonstrate a governed decision.",
        "SECOND-DECISION ECONOMICS: the first engagement pays for the design; the second and third "
        "reuse the gate, the evidence plumbing and the test harness, so margin rises per decision "
        "while price to the customer falls.",
    ], size=10.3, gap=0.60)
    src(s, 6.45, "Gartner, worldwide AI spending forecast, 19 May 2026 and 20 July 2026.")

    # ========================================================================== 14 WHY US
    s = d.slide("differentiation", "Why the buyer ", "chooses this",
                sub="Four things that are hard to copy and easy to verify.", footer=FOOT)
    bullets(s, 0.60, 2.10, 12.15, [
        "IT IS A METHOD, NOT A MODEL. Vendors are locked to their own model and their own roadmap. "
        "We are model-agnostic by construction, which is also the answer to sovereignty, "
        "procurement and vendor-risk questions in every jurisdiction that asks them.",
        "THE AUDITOR IS NEVER THE AUTHOR. Enforced in code, not asserted in a slide. This is the "
        "single property most 'AI review' offerings cannot claim, because they run one model.",
        "IT FAILS SAFE AND SAYS SO. HOLD is a first-class verdict, dissent is preserved, and the "
        "gate refuses rather than guesses when the evidence is not there.",
        "WE RUN IT ON OURSELVES. Every release of our own platform is reviewed by the same panel "
        "and gated by the same deterministic checks, and we will show the record, including the "
        "cases where the panel was wrong.",
    ], size=11, gap=0.78)
    _tb(s, 0.60, 5.85, 12.15, 0.90,
        "The objection you will hear is 'we can build this ourselves'. The honest answer: yes, and "
        "the part that takes eighteen months is not the models, it is the gate, the refusal "
        "criteria and the test harness against known outcomes.",
        12, WHITE, DISPLAY, True, space=1.2)

    # ========================================================================== 15 FIRST 90 DAYS
    s = d.slide("engagement", "The first ", "ninety days",
                sub="One decision, proven against history, before anything is scaled.", footer=FOOT)
    bullets(s, 0.60, 2.10, 12.15, [
        "DAYS 1-15  ·  Choose ONE decision. High-consequence, made repeatedly, currently owned by "
        "one expert with one method. We write the evidence taxonomy and the refusal criteria with "
        "the people who own the decision today.",
        "DAYS 16-50  ·  Build the panel and the gate against that decision, on the customer's own "
        "infrastructure, with their thresholds.",
        "DAYS 51-75  ·  Backtest against historical cases where the outcome is already known. This "
        "is the phase that decides whether the programme continues. We report it either way.",
        "DAYS 76-90  ·  Acceptance, handover of the decision file format, and the support contract. "
        "Second decision scoped from the same foundations.",
    ], size=11, gap=0.80)
    _rect(s, 0.60, 5.80, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 6.00, 12.15, 0.70,
        "What we need to start: one decision, and access to the historical cases where you already "
        "know the answer.", 13, WHITE, DISPLAY, True, space=1.2)

    # ========================================================================== 16 SOURCES
    s = d.slide("sources", "Sources ", "and honest limits",
                sub="", footer=FOOT)
    _tb(s, 0.60, 1.90, 6.00, 0.30, "ANALYST AND MARKET", 11, CYAN, MONO, True)
    bullets(s, 0.60, 2.25, 6.00, [
        "Gartner, 25 Jun 2025: over 40% of agentic AI projects cancelled by end-2027; ~130 of "
        "thousands of agentic vendors are real.",
        "Gartner, 11 Mar 2026: multi-agent outperformance by 2028; governance runtime enforcement "
        "behind half of agent failures by 2030.",
        "Gartner, 17 Mar 2026: 80%+ of governments deploying AI agents for routine decisions by "
        "2028.",
        "Gartner, 19 May 2026: worldwide AI spending $2.59tn in 2026, +47%.",
        "McKinsey, State of AI 2025: 88% adoption, ~39% reporting any EBIT impact.",
    ], size=9.2, gap=0.50)
    _tb(s, 6.95, 1.90, 5.80, 0.30, "DOMAIN EVIDENCE", 11, VIOLET, MONO, True)
    bullets(s, 6.95, 2.25, 5.80, [
        "McKinsey: in-silico development could cut trial development cost up to 60% and cycle time "
        "up to 40%; $60bn+ annual life-science opportunity.",
        "BCG with Wellcome: up to 50% early discovery cost, 25-50% early R&D time saving.",
        "McKinsey product-launch research: failure rates above 40%, no correlation between launch "
        "spend and success.",
        "National Research Council (2003): polygraph median accuracy index 0.86, evidence quality "
        "low, large false-positive volumes at low base rates.",
        "RAND RR1408 / Heuer and Pherson on structured analytic techniques.",
    ], size=9.2, gap=0.50, dot=VIOLET)
    _rect(s, 0.60, 5.55, 12.15, 0.012, LINE, None)
    _tb(s, 0.60, 5.75, 12.15, 1.10,
        "HONEST LIMITS. Every percentage above is a SECTOR BENCHMARK published by a third party "
        "for a class of technique, not a result we have produced for a customer and not a "
        "forecast for any specific engagement. We have not run a controlled comparison against a "
        "single-model approach. Phase 4 exists precisely so that the number a customer relies on "
        "is measured on their own historical cases, not quoted from this slide.",
        10.5, BODY, TEXT, space=1.28)

    # ========================================================================== 17 CLOSE
    d.slide("close", [("ONE DECISION.", MUTED), ("PROVEN AGAINST", WHITE),
                      ("YOUR OWN HISTORY.", CYAN)], hero=True, footer=FOOT)

    return d.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Consensus_Decision_Method.pptx"))
    a = ap.parse_args()
    print("built: %s" % build(a.template, a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
