#!/usr/bin/env python3
"""Perseus Shield + Automated SOC — the PRESALE deck.

WHY THIS EXISTS BESIDE build_perseus_shield_deck.py. That deck argues architecture to a technical
reader who already believes there is a problem. This one is for a first commercial meeting with a
prospect who does not, and who has heard the category pitched before.

THE BRIEF CAME FROM A REAL MEETING (2026-10-09, 123 minutes, four participants). Four lines from
it shaped every slide here, and three of them are objections rather than requirements:

  Miguel  "the description you gave me is something that I have been pitched like 50 times
           before, exactly the same. So I would need you guys to show me."
          -> SHOW, DO NOT CLAIM. Every section ends in something measured, and the two proof
             slides are receipts from our own estate with dates on them. No competitor is named
             and no comparative performance claim is made anywhere (UWG s6 / UCP Directive).

  Miguel  "if you have something acting on a firewall policy, there's a real risk of lockout"
          and "you won't be under attack anymore, but your business will be underground."
          -> THE BOUNDARIES SLIDE IS A FEATURE SLIDE, not a disclaimer. It is placed BEFORE the
             proof, because a buyer who fears the product cannot hear evidence for it.

  Miguel  "a reverse proxy has some issues... you will need a lot of redundancy, a lot of
           capacity, unless you are talking about a very small business."
          -> THE CONNECTION SLIDE LEADS WITH THAT OBJECTION and answers it by showing that inline
             is one of three modes, and the other two are not in the traffic path at all.

  Valery  "there is no correct way to deploy it. There are multiple ways, because it depends on
           customer infrastructure."
          -> ditto. The deck sells a choice, not a topology.

NARRATIVE SHAPE: Situation, Complication, Resolution, Proof, Offer. The classic consultative
sequence rather than a feature list, because the first meeting is about whether the problem is
real and whether we are safe to let near production.

EVERY NUMBER IS MEASURED. Each constant below names the file or the dated artefact it came from.
A number whose source cannot be named does not go on a customer slide.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  - one template implementation, reused
    AMBER, BODY, CYAN, Deck, GREEN, INDIGO, LINE, MONO, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from build_perseus_shield_deck import table  # noqa: E402  - one table implementation, reused

FOOT = "S4BIZ GROUP · CYBERGOD LLC · PERSEUS SHIELD · COMMERCIAL IN CONFIDENCE"

# ---- MEASURED CONSTANTS -------------------------------------------------------------------
#: perseus/client.py :: CLASSES, counted 2026-10-21. The file's own comment still says nineteen;
#: the list has twenty-one entries. The list was counted, the comment was not trusted.
N_CLASSES = 21
#: perseus/client.py :: HONEYTOKENS
N_HONEY = 5
#: webapp/backend/app/shield.py :: BLAST_CAP, MAX_TARPIT_CONCURRENT
BLAST_CAP_PCT, MAX_TARPIT = 20, 24
#: perseus/ruleset.py :: MIN_DETECT_HOURS, QUORUM, STEP_CAP, DORMANT_DAYS
SOAK_H, QUORUM, STEP_CAP_PCT, DORMANT_D = 24, 3, 25, 30
#: perseus/incident.py :: DAY_USD, MAX_PER_DAY
SOC_DAY_USD, SOC_MAX_INC = "0.30", 12
#: The weekly cycle report of 2026-10-18 05:20 UTC, quoted from the email it sent itself.
#: detecting 145 -> 84 and retired 333 -> 394 are the SAME 61 rules, so one number is quoted.
WK_DATE, WK_BLOCK, WK_RETIRED, WK_TOTAL, WK_WORST = "18 Oct 2026", 28, 61, 394, 224
#: One analyse_attacks run over the live event log of cybergod.ai.
LOG_REQ, LOG_SRC, LOG_SCAN = "156,511", "2,253", "604"

W, H = 13.333, 7.5
TITLE_CAP = 40          # measured on this template: 40 characters fit one line at this size


def _check(title, tail=""):
    row = (title if isinstance(title, str) else " ".join(t for t, _ in title)) + (tail or "")
    assert len(row) <= TITLE_CAP, "title row is %d chars, cap is %d: %r" % (len(row), TITLE_CAP, row)


def build(template, out):
    d = Deck(template)
    _orig = d.slide

    def slide(eyebrow, title, tail="", sub="", hero=False):
        _check(title, tail)
        return _orig(eyebrow, title, tail, sub, FOOT, hero)
    d.slide = slide

    # ================================================================= 1. cover
    s = d.slide("PERSEUS SHIELD  ·  AUTOMATED SOC",
                [("SEE IT.", WHITE), ("DECIDE IT.", WHITE), ("STOP IT.", VIOLET)],
                hero=True)
    _tb(s, 0.85, 4.05, 9.60, 1.00,
        "Continuous detection and automatic, reversible defence for companies that do not have a "
        "security operations centre and are not going to build one.", 15, BODY, TEXT)
    for i, (k, v) in enumerate([("DEPLOYS IN", "three ways,\none of them inline"),
                                ("DECIDES IN", "seconds,\nnot in a ticket queue"),
                                ("TOUCHES", "no firewall,\never")]):
        cx = 0.85 + i * 3.95          # ONE origin per card. The text boxes derive from it.
        _rect(s, cx, 5.35, 3.70, 1.05, fill=PANEL, line=LINE)
        _tb(s, cx + 0.20, 5.48, 3.30, 0.26, k, 9.5, CYAN, MONO, True, space=1.6)
        _tb(s, cx + 0.20, 5.76, 3.30, 0.56, v, 11, WHITE, TEXT)

    # ================================================================= 2. situation
    s = d.slide("THE SITUATION", "YOU CANNOT PROTECT", " WHAT YOU CANNOT SEE.",
                "The mid-sized estate: twenty sites, a firewall in each one, and nobody reading "
                "any of them together.")
    bullets(s, 0.85, 2.28, 6.05, [
        "EVERY BOX ALREADY SEES SOMETHING. The firewall, the WAF, the EDR. Each is right, and "
        "none of them talks to the others.",
        "NOBODY CORRELATES IT. One actor probing six sites over four days looks like six separate "
        "nuisances, and like one campaign on no console at all.",
        "THE ANSWER ON OFFER IS A SOC. People, a platform, a year of tuning, an analyst rota you "
        "cannot staff.",
        "SO NOTHING IS DONE. Not negligence: every option costs more than the risk feels worth, "
        "until the week it is not.",
    ], gap=1.12, size=10.5)
    _rect(s, 7.30, 2.28, 5.15, 4.10, fill=PANEL, line=LINE)
    _tb(s, 7.55, 2.44, 4.65, 0.30, "WHAT A WEEK LOOKS LIKE ON ONE SITE", 10, CYAN, MONO, True)
    _tb(s, 7.55, 2.84, 4.65, 3.30,
        "Our own front door, one analysis window:\n\n"
        "%s requests\n%s distinct sources\n%s behaved like scanners\n\n"
        "One small estate. No famous brand, nothing worth stealing.\n\n"
        "The traffic is automated, continuous and indifferent to your size.\n\n"
        "The question is not whether this reaches you. It is whether anyone would notice if it "
        "mattered." % (LOG_REQ, LOG_SRC, LOG_SCAN), 11, BODY, TEXT)

    # ================================================================= 3. complication
    s = d.slide("THE COMPLICATION", "YOU HAVE HEARD THIS", " BEFORE.",
                "Four reasons this category usually gets dismissed, and all four are fair.")
    for i, (k, kc, h, b) in enumerate([
            ("01", RED, "AUTOMATION THAT CAN LOCK YOU OUT",
             "Anything that writes a firewall rule can write the wrong one at 03:00. The failure "
             "mode is your own staff locked out, with nobody awake who knows which rule did it."),
            ("02", AMBER, "A POLICY NOBODY CAN READ",
             "A block whose reason cannot be explained gets switched off the first time it is "
             "inconvenient, and stays off."),
            ("03", VIOLET, "ALERTS THAT ARE NOT DECISIONS",
             "\u201cYou are under attack\u201d is not an instruction. Name the change, the box "
             "and the evidence."),
            ("04", CYAN, "A PILOT THAT COSTS A QUARTER",
             "If proving it works needs a procurement cycle, the proof never happens.")]):
        card(s, 0.85 + (i % 2) * 6.05, 2.28 + (i // 2) * 2.12, 5.60, 1.92, k, kc, h, b, bsize=10)

    # ================================================================= 4. what it is
    s = d.slide("THE RESOLUTION", "THREE LAYERS,", " ONE PRODUCT.",
                "Each layer is useful on its own, and each one feeds the next. You can stop after "
                "the first and still be better off than you are today.")
    lanes = [("SEE", CYAN, "OBSERVABILITY",
              "Every request, every site, one place. Classified into %d attack shapes on arrival, "
              "kept as evidence rather than as a counter." % N_CLASSES),
             ("DECIDE", VIOLET, "THE AUTOMATED SOC",
              "Correlation across sites and days, enriched with what the target is. Four models "
              "propose. Code decides which proposals become real."),
             ("ACT", GREEN, "ACTIVE DEFENCE",
              "Graduated, reversible enforcement at the HTTP layer, inside bounds an operator "
              "sets and the models cannot widen.")]
    for i, (k, col, head, body) in enumerate(lanes):
        x = 0.85 + i * 4.00
        _rect(s, x, 2.28, 3.75, 2.55, fill=PANEL, line=col, lw=1.25)
        _rect(s, x, 2.28, 3.75, 0.06, fill=col, line=None)
        _tb(s, x + 0.22, 2.46, 3.30, 0.28, k, 11, col, MONO, True, space=2.0)
        _tb(s, x + 0.22, 2.78, 3.30, 0.30, head, 13, WHITE, TEXT, True)
        _tb(s, x + 0.22, 3.16, 3.30, 1.55, body, 10, BODY, TEXT)
        if i < 2:
            _tb(s, x + 3.78, 3.30, 0.20, 0.30, "\u203a", 20, col, TEXT, True)
    _rect(s, 0.85, 5.08, 11.60, 1.35, fill=PANEL, line=LINE)
    _tb(s, 1.10, 5.22, 11.1, 0.28, "WHAT IT IS FOR, IN ONE SENTENCE", 10, CYAN, MONO, True)
    _tb(s, 1.10, 5.54, 11.1, 0.80,
        "To give a company without a SOC the three things a SOC produces: one view across every "
        "site, a decision about what matters, and a safe action taken quickly enough to matter. A "
        "human rota answers in hours. This answers while the scan is still running.",
        11.5, BODY, TEXT)

    # ================================================================= 5. how it connects
    s = d.slide("CONNECTION", "THREE WAYS IN.", " YOU CHOOSE.",
                "Inline is one option of three, and it is not the default.")
    rows = [("A. INLINE REVERSE PROXY",
             "In front of the application.",
             "Full enforcement. Needs capacity and redundancy sized to your traffic."),
            ("B. PORT MIRROR  ·  SPAN / TAP",
             "A copy of the traffic. Not in the path.",
             "Full detection. Enforcement handed to whatever already enforces."),
            ("C. YOUR EXISTING STREAMS",
             "Syslog and APIs from what you already run.",
             "Nothing new in the path. Deploys in an afternoon. Where pilots start.")]
    y = table(s, 0.85, 2.28, 11.60, ["Mode", "How it attaches", "What you get"],
              rows, [0.26, 0.30, 0.44], rh=0.64, size=10)
    _rect(s, 0.85, y + 0.22, 11.60, 1.26, fill=PANEL, line=LINE)
    _tb(s, 1.10, y + 0.34, 11.1, 0.26, "ON THE INLINE QUESTION", 10, AMBER, MONO, True)
    _tb(s, 1.10, y + 0.62, 11.1, 0.80,
        "An inline proxy needs capacity and redundancy sized to your traffic. That is why modes "
        "B and C exist, and why most engagements begin there. Detection does not need us in "
        "your traffic path. Only enforcement does, and it is the last thing we turn on.",
        11, BODY, TEXT)

    # ================================================================= 6. the SOC
    s = d.slide("THE AUTOMATED SOC", "WHAT AN ANALYST DOES,", " ON A LOOP.",
                "A SOC analyst builds correlations, reads alerts, triages them and recommends a "
                "change. This does the same work continuously, and shows it.")
    steps = [("1", "INGEST", "Requests, firewall and EDR events from every site, into one "
                             "stream."),
             ("2", "ENRICH", "IPAM, CMDB, org structure. The finance server and a test box are "
                             "not the same incident."),
             ("3", "CORRELATE", "Across sites and days. One actor on many distinct paths, not "
                                "one noisy visitor."),
             ("4", "PROPOSE", "Four models from four vendors propose a detection or a threshold "
                              "change."),
             ("5", "DECIDE", "Code applies it only if every barrier passes. %d of 4 must agree, "
                             "from different vendors." % QUORUM),
             ("6", "HAND OVER", "The change, the evidence, the next step, into your console or "
                                "chat channel.")]
    for i, (n, k, b) in enumerate(steps):
        x, yy = 0.85 + (i % 3) * 4.00, 2.28 + (i // 3) * 1.72
        _rect(s, x, yy, 3.75, 1.48, fill=PANEL, line=LINE)
        _tb(s, x + 0.22, yy + 0.16, 0.45, 0.28, n, 13, VIOLET, MONO, True)
        _tb(s, x + 0.78, yy + 0.18, 2.80, 0.28, k, 11.5, WHITE, TEXT, True)
        _tb(s, x + 0.22, yy + 0.58, 3.35, 1.00, b, 9.6, BODY, TEXT)
    _rect(s, 0.85, 5.88, 11.60, 0.86, fill=PANEL, line=VIOLET)
    _tb(s, 1.10, 6.00, 11.1, 0.64,
        "MODELS PROPOSE. CODE DECIDES. A model never blocks an address, never widens its own "
        "authority and never promotes its own proposal. The whole AI budget for this loop is "
        "capped at $%s a day." % SOC_DAY_USD, 11, BODY, TEXT)

    # ================================================================= 7. detection
    s = d.slide("DETECTION", "WHAT IT RECOGNISES,", " AND HOW.",
                "Signatures are the easy half. The engineering is in the second column: deciding "
                "that a pattern is an actor rather than a bad bookmark.")
    bullets(s, 0.85, 2.28, 6.05, [
        "%d ATTACK CLASSES on arrival: WordPress and PHP probing, .env and cloud-credential "
        "hunting, admin panels, shell and RCE, traversal, SQL injection, appliance interfaces." % N_CLASSES,
        "%d HONEYTOKENS, disallowed in robots.txt and linked from nowhere. A request for one is "
        "not a customer, which makes it the only zero-false-positive signal there is." % N_HONEY,
        "VARIETY, NOT VOLUME. Evidence accrues on DISTINCT paths, never on request counts. Two "
        "genuine visitors once produced 439 and 362 misses each.",
        "A NETWORK HORIZON, not only an address one. The actor that matters rotates addresses "
        "inside a range and never trips a per-address rule.",
    ], gap=1.12, size=10.5)
    _rect(s, 7.30, 2.28, 5.15, 4.10, fill=PANEL, line=LINE)
    _tb(s, 7.55, 2.44, 4.65, 0.30, "AND WHAT IT REFUSES TO CALL AN ATTACK", 10, CYAN, MONO, True)
    _tb(s, 7.55, 2.84, 4.65, 3.30,
        "A user agent is attacker-controlled, so it is never the evidence. The path is.\n\n"
        "A failed lookup reports UNKNOWN and claims nothing. A dead data source must never read "
        "as innocence.\n\n"
        "Every rule carries the reason it fired, in words a reviewer would use.", 11, BODY, TEXT)

    # ================================================================= 8. enforcement
    s = d.slide("ACTIVE DEFENCE", "GRADUATED,", " AND REVERSIBLE.",
                "Nothing jumps straight to refusal. Each step is survivable if it is wrong, and "
                "every one of them can be undone by a person in one action.")
    ladder = [("OBSERVE", CYAN, "Logged, classified, correlated. No effect on the request."),
              ("WATCH", INDIGO, "A pattern is armed but refuses nothing for %d hours, and must "
                                "match zero legitimate requests in that time." % SOAK_H),
              ("SLOW", VIOLET, "The response is delayed. A scanner's economics break; a person "
                               "notices a slow page at worst. At most %d at once." % MAX_TARPIT),
              ("REFUSE", GREEN, "Only after the pattern has earned it, and never beyond %d%% of "
                                "recent distinct visitors." % BLAST_CAP_PCT)]
    for i, (k, col, b) in enumerate(ladder):
        x = 0.85 + i * 2.98
        _rect(s, x, 2.28, 2.78, 1.70, fill=PANEL, line=col, lw=1.25)
        _rect(s, x, 2.28, 2.78, 0.06, fill=col, line=None)
        _tb(s, x + 0.20, 2.48, 2.40, 0.30, k, 12, WHITE, TEXT, True)
        _tb(s, x + 0.20, 2.86, 2.40, 1.00, b, 9.4, BODY, TEXT)
        if i < 3:
            _tb(s, x + 2.80, 2.92, 0.18, 0.30, "\u203a", 17, col, TEXT, True)
    _rect(s, 0.85, 4.26, 5.60, 2.15, fill=PANEL, line=LINE)
    _tb(s, 1.10, 4.40, 5.10, 0.28, "THE BOUNDS AN OPERATOR SETS", 10, CYAN, MONO, True)
    _tb(s, 1.10, 4.72, 5.10, 1.55,
        "Thresholds sit inside committed bounds, clamped when READ rather than when written, so "
        "a bad value cannot survive a restart.\n\n"
        "No threshold moves more than %d%% per cycle. A rule nothing matches for %d days retires "
        "itself." % (STEP_CAP_PCT, DORMANT_D), 11, BODY, TEXT)
    _rect(s, 6.85, 4.26, 5.60, 2.15, fill=PANEL, line=LINE)
    _tb(s, 7.10, 4.40, 5.10, 0.28, "AND WHAT HAPPENS WHEN IT IS WRONG", 10, AMBER, MONO, True)
    _tb(s, 7.10, 4.72, 5.10, 1.55,
        "A rule that refuses legitimate-looking traffic demotes itself, back to watching, and "
        "says so. Autonomy without a way back is a one-way door.\n\n"
        "Releasing somebody forgives the history that caused the block, not just the timer.",
        11, BODY, TEXT)

    # ================================================================= 9. boundaries
    s = d.slide("BOUNDARIES", "IT WILL NEVER TOUCH", " YOUR FIREWALL.",
                "Four limits that are designed in, not configured. None of them is tunable by us or "
                "by the models.")
    bullets(s, 0.85, 2.28, 6.05, [
        "NO FIREWALL RULES, EVER. No iptables, no nft, no ufw, no network device. Enforcement is "
        "HTTP-layer, in its own container. Removing Perseus removes every effect it ever had.",
        "AN AUTHENTICATED SESSION IS NEVER BLOCKED. Whoever is logged in stays logged in. A route "
        "you serve is slowed, never refused.",
        "IT NEVER SCANS BACK. Retaliation is a criminal offence under StGB \u00a7202a-d, EU "
        "Directive 2013/40 and the US CFAA. The lawful route is a provider complaint, which we "
        "draft and a person files.",
        "IT FAILS OPEN. Every internal error resolves to ALLOW. A control that can cause an "
        "outage is worse than no control.",
    ], gap=1.12, size=10.5)
    _rect(s, 7.30, 2.28, 5.15, 4.10, fill=PANEL, line=RED)
    _tb(s, 7.55, 2.44, 4.65, 0.30, "WHY THE LIMIT IS THE FEATURE", 10, RED, MONO, True)
    _tb(s, 7.55, 2.90, 4.65, 3.20,
        "Anything that can rewrite a firewall policy can write the wrong rule at three in the "
        "morning.\n\n"
        "Denying all entrance ends the attack and ends the trading day with it.\n\n"
        "So the useful output is never \u201cblock everything\u201d. It is the specific change "
        "to make, on which box, with the evidence beside it.", 11, BODY, TEXT)

    # ================================================================= 10. proof 1
    s = d.slide("PROOF", "IT RETIRES", " ITS OWN RULES.",
                "One weekly cycle, %s, quoted from the report it emails itself whether or not "
                "anyone is reading." % WK_DATE)
    for i, (v, lab, col) in enumerate([(str(WK_BLOCK), "rules enforcing,\nbefore and after", CYAN),
                                       (str(WK_RETIRED), "candidates retired\nthat week", VIOLET),
                                       (str(WK_WORST), "real paths the worst\none would have hit",
                                        AMBER),
                                       (str(WK_TOTAL), "retired to date,\nevidence kept", INDIGO)]):
        stat(s, 0.85 + i * 2.95, 2.30, 2.7, v, lab, col)
    rows = [("\\.php($|/)", "matches 224 paths we actually serve"),
            ("^/[a-z]+\\.php$", "matches 118 paths we actually serve"),
            ("\\.env[^/]*$", "matches 97 paths we actually serve"),
            ("^/(\\.env|config/database\\.php).*", "matches 41 paths we actually serve")]
    _tb(s, 0.85, 3.95, 6.60, 0.30, "RETIRED THAT WEEK, WITH THE REASON GIVEN", 10, CYAN, MONO, True)
    table(s, 0.85, 4.30, 6.60, ["Pattern", "Why it was retired"], rows, [0.42, 0.58],
          rh=0.36, size=9.0)
    _rect(s, 7.95, 3.95, 4.50, 2.45, fill=PANEL, line=LINE)
    _tb(s, 8.20, 4.10, 4.00, 0.30, "WHY THIS IS THE ARGUMENT", 10, AMBER, MONO, True)
    _tb(s, 8.20, 4.44, 4.00, 1.85,
        "Each pattern on the left is one a competent engineer would have written by hand and "
        "shipped on a Friday. Every one was caught against real traffic before it could refuse "
        "anybody.\n\n"
        "Enforcement stayed at %d while %d candidates were thrown out. The set that blocks does "
        "not grow because the system is busy." % (WK_BLOCK, WK_RETIRED), 10.5, BODY, TEXT)

    # ================================================================= 11. proof 2
    s = d.slide("PROOF", "SAID AT WHAT", " IT PROVES.",
                "Each figure with the method beside it, and with what it does not establish stated "
                "in the same row.")
    rows = [("%s requests analysed" % LOG_REQ, "One run against our own live event log.",
             "Volume, nothing more."),
            ("%s distinct sources" % LOG_SRC, "Unique addresses in that window.",
             "The population, not the threat."),
            ("%s behaved like scanners" % LOG_SCAN,
             "Classified on path variety, not on user agent.",
             "DETECTED. Not stopped: that log predates enforcement."),
            ("19 patterns were missing", "Found by the same measurement, then added.",
             "The corpus is pinned in tests so the gap cannot reopen.")]
    y = table(s, 0.85, 2.28, 11.60, ["Measured", "How", "What it does and does not prove"],
              rows, [0.26, 0.34, 0.40], rh=0.70, size=9.6)
    _rect(s, 0.85, y + 0.24, 11.60, 1.08, fill=PANEL, line=LINE)
    _tb(s, 1.10, y + 0.36, 11.1, 0.26, "THE LOOP THIS DESCRIBES", 10, CYAN, MONO, True)
    _tb(s, 1.10, y + 0.64, 11.1, 0.62,
        "Those sources were DETECTED, on a log written before enforcement shipped. Saying they "
        "were stopped would be an unsupported claim on a security product.\n\n"
        "Measure the log, find what the detector missed, close the gap, pin it so it cannot "
        "reopen. That loop runs on your traffic during the pilot, and you see both halves.",
        11, BODY, TEXT)

    # ================================================================= 12. fit
    s = d.slide("FIT", "IT ADDS.", " IT REPLACES NOTHING.",
                "Nothing here asks you to remove a control you already paid for, and nothing here "
                "competes with your firewall vendor.")
    rows = [("Next-generation firewalls, WAF", "Keep them. They are a data source and, in mode B "
             "or C, the thing that enforces what Perseus concludes."),
            ("EDR and endpoint tooling", "Keep it. Endpoint telemetry becomes one more stream in "
             "the correlation rather than a separate console."),
            ("SIEM, log platforms", "Keep them. Perseus can feed them, read from them, or run "
             "beside them. It is not a storage product."),
            ("An existing MSSP or SOC", "Keep it. This is the layer that answers in seconds so "
             "the human queue only sees what deserves a human.")]
    y = table(s, 0.85, 2.28, 11.60, ["What you already run", "What changes"], rows, [0.33, 0.67],
              rh=0.74)
    _rect(s, 0.85, y + 0.24, 11.60, 1.02, fill=PANEL, line=LINE)
    _tb(s, 1.10, y + 0.36, 11.1, 0.26, "WHERE IT GENUINELY DOES NOT FIT, STATED NOW", 10, AMBER,
        MONO, True)
    _tb(s, 1.10, y + 0.64, 11.1, 0.56,
        "Built for small and mid-sized estates. A very large fleet raises scaling questions we "
        "have not answered yet, and we would rather say so in the first meeting than the third.",
        11, BODY, TEXT)

    # ================================================================= 13. the offer
    s = d.slide("THE OFFER", "THIRTY DAYS,", " ENFORCEMENT OFF.",
                "The only honest way to sell a defence product is to let it be watched being "
                "wrong before it is allowed to act.")
    for i, (k, kc, h, b) in enumerate([
            ("WEEK 1", CYAN, "CONNECT, IN THE SAFEST MODE",
             "Streams or a mirror. Nothing enters your traffic path. Detection only, and the "
             "first correlations across sites usually arrive the same day."),
            ("WEEK 2", INDIGO, "YOU SEE WHAT IT WOULD HAVE DONE",
             "Every would-be action, with its evidence and its reason, and nothing acted on. This "
             "is where the false positives surface, which is the point of the exercise."),
            ("WEEK 3", VIOLET, "WE TUNE IT ON YOUR TRAFFIC",
             "Your routes, your bookmarks, your partner integrations. Bounds set with your team, "
             "in writing, before anything is armed."),
            ("WEEK 4", GREEN, "YOU DECIDE WHETHER IT ACTS",
             "Enforcement on, off, or on for one class and off for the rest. The decision is "
             "yours and it is reversible in one action.")]):
        card(s, 0.85 + (i % 2) * 6.05, 2.28 + (i // 2) * 2.10, 5.60, 1.90, k, kc, h, b, bsize=10)
    _rect(s, 0.85, 6.30, 11.60, 0.60, fill=PANEL, line=LINE)
    _tb(s, 1.10, 6.40, 11.1, 0.42,
        "At the end of thirty days you own the findings whether or not you buy anything, and "
        "removing Perseus removes every effect it ever had.", 11, BODY, TEXT)

    # ================================================================= 14. close
    # HERO SLIDES TAKE A COLOURED TITLE LIST, not a string: build_consensus_deck.slide() unpacks
    # (text, colour) pairs on the hero path. Read the signature after it raised, not before.
    s = d.slide("NEXT", [("WHAT WE NEED", WHITE), ("FROM YOU.", VIOLET)], hero=True)
    for i, (n, t) in enumerate([
            ("01", "One site to start with, and the name of the person who owns it."),
            ("02", "Which of the three connection modes your infrastructure allows."),
            ("03", "A list of the routes and partners that must never be refused."),
            ("04", "Thirty days, and one hour a week of somebody technical.")]):
        _rect(s, 0.85, 3.05 + i * 0.80, 11.60, 0.68, fill=PANEL, line=LINE)
        _tb(s, 1.10, 3.17 + i * 0.80, 0.50, 0.30, n, 12, CYAN, MONO, True)
        _tb(s, 1.80, 3.17 + i * 0.80, 10.4, 0.40, t, 12, WHITE, TEXT)
    _tb(s, 0.85, 6.50, 11.60, 0.38,
        "PERSEUS SHIELD · S4Biz Group · Cybergod LLC · feranicus@s4biz.io · +351 939 994 642",
        11, WHITE, MONO, True)

    return d.save(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Perseus_Presale_EN.pptx"))
    a = ap.parse_args()
    p = build(a.template, a.out)
    print("built: %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
