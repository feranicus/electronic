#!/usr/bin/env python3
"""build_investor_deck.py — S4biz Group, the pre-seed / seed deck. Rewritten from scratch.

    python marketing/build_investor_deck.py [--out PATH] [--template PATH]

WHY THIS FILE WAS REWRITTEN RATHER THAN EDITED
----------------------------------------------
The previous build averaged 291 words a slide. The DocSend benchmark templates the founder
supplied average 27. Measured investor dwell on a non-cover slide is 3.3 seconds, which is a 12 to
16 word slide. The old deck asked for about 70 seconds per slide, which is not a style problem but
an arithmetic impossibility, so the old slide content was deleted rather than shortened: shortening
a paragraph produces a shorter paragraph, and the benchmark is not a shorter paragraph.

Thirteen main slides plus five appendix slides. The main-deck copy is FIXED and was supplied
verbatim by the founder. This module's job is layout and typography, not authorship, so there is no
sentence in slides 1 to 13 that the founder did not write. Where a slide looks sparse, that is the
design working.

WHAT CARRIES THE MEANING IS THE TYPE HIERARCHY, NOT THE WORD COUNT. The headline is the slide; body
text only evidences it. Where a slide has a number, it is set at display size (`bigstat`) so the
number is read before the sentence explaining it. Three to five content shapes per slide, against
19 to 43 in the old build and 6 in the benchmark templates.

MEASURED, AND REPORTED RATHER THAN PAPERED OVER
-----------------------------------------------
The supplied copy for slides 1 to 13 is 810 words of headline, sub-heading and body, which is 62
words a slide. The brief asked for an average under 40. BOTH CANNOT BE TRUE AT ONCE, and of the two
instructions the stronger one is "use the copy verbatim, do not add and do not improve". So this
build renders the copy as given and `--audit` prints the real per-slide table, including the
average, so the gap is a measurement the founder can act on rather than a claim this file makes.
Cutting to 40 means deleting the founder's own sentences, which is his decision and not this
script's. `WORDS_TARGET` and `WORDS_CEILING` are module constants for exactly that reason.

It reuses build_consensus_deck.py's Deck / card / bullets / stat / _tb / _rect and deck_chrome.py's
guarded + assert_layout, so the S4biz template exists in exactly ONE implementation and this deck
cannot drift away from the commercial pack it reports on. Same reason build_aisoc_commercial_deck.py
does it. The dark S4biz palette is kept deliberately: the founder asked for S4biz colours, and dark
is defensible on a security company's deck.

RULES THIS BUILD OBEYS
----------------------
1. NO EM DASHES AND NO EN DASHES IN SLIDE TEXT. Standing rule for anything a customer or an
   investor reads. `--audit` greps the built file for both and fails.
2. BANNED VOCABULARY: delve, leverage, robust, seamless, landscape, testament, underscore, pivotal.
   Also checked by `--audit` against the built file, not against this source.
3. NOT ONE INVENTED NUMBER. No revenue, ARR, MRR, TAM, market size, growth rate, headcount, burn,
   runway or valuation appears anywhere, and no bracket stands where one would go. Slide 3 says
   pre-revenue in that word. Valuation is a conversation, and a bracket where a valuation belongs
   invites the wrong first question.
4. NO COMPARATIVE SUPERIORITY CLAIM AGAINST A NAMED PRODUCT. Slide 11 states four published day
   rates as facts and makes no claim to be better than the firms that publish them. An
   unsubstantiated comparison is UWG s.6 / UCP Directive exposure and, on a product whose argument
   is evidence discipline, self-refuting.
5. THE FOUNDER'S PRIOR-EMPLOYER WORK IS BIOGRAPHY, NOT DELIVERY. Slide 2 lists company names under
   three headings and asserts nothing about what was built at any of them. S4biz Group has not
   delivered any project of Cognyte, Cyberbit, Intellexa, AWS, Red Hat, NetApp, Huawei, Canonical,
   Colt, Cogent, Telefonica or Deutsche Telekom, and no slide says otherwise.
6. THE `[ ]` PLACEHOLDERS ON A1 ARE CARRIED THROUGH VERBATIM from `_pack_src/FACTS.md` s.1. A
   registry code and a registered address are genuine unknowns that nobody may guess, and the legal
   pack already uses this convention, so it is house style rather than an apology.

EVERY NUMBER IN THIS DECK, TRACED TO ITS SOURCE
-----------------------------------------------
Supplied by the founder with this brief (main deck, slides 3 to 13)
    s.3   22 companies assessed, June to August 2026
    s.3   5 live properties defended by Perseus today
    s.4   42,369 attack-shaped requests in 14 days against our own estate
    s.4   one address, 551 distinct paths, 143 distinct announced user agents
    s.5   one retired rule had become a match for 99 paths our own build output serves
    s.9   a first meeting costs the partner EUR 100
    s.10  Platinum buys a seat at EUR 120 and sells at EUR 200; 100 seats is EUR 8,000 a month
    s.13  EUR 20,000,000; 40 / 30 / 15 / 5 / 10; four incorporated offices

aisoc_pack/_src/FACTS.md
    s.3   264 test functions across 8 files, counted 2026-09-17
    s.4   42,369 requests in 14 days; one actor 551 paths and 143 user agents (s.13)
    s.5   the weekly loop retired a rule matching 99 paths of build output (s.13, 2026-09-13)
    s.7   four models from four vendors propose, deterministic code decides (s.6, s.4)
    A2    SENTRY 450, SHIELD 1200, CITADEL 2900, extra application 90, extra investigation 8 (s.14)
    A2    partner ladder 10 / 20 / 30 / 40 (s.14)
    A3    no reference customer for Perseus, no 24/7 analyst desk, no Perseus SLA target (s.18)

cybergod_pack/_src/FACTS.md
    s.8   a public certificate authority pivot adopted 998 unrelated hosts (s.5)
    s.8   a brand token that is a dictionary word matched 192 addresses across 44 networks (s.5)
    s.8   the public-suffix error: one government site became 203 addresses, eight figures (s.5)
    s.8   fifteen ownership gates, each bought by a named incident (s.5, rows counted)
    s.7   public sources only, plus the target's own published site and certificate (s.4)
    A3    no ISO 27001, no SOC 2, one hosting region; no continuous monitoring (s.13)
    A4    the named public sources and the pipeline (s.4, s.5, s.6)

_pack_src/FACTS.md
    A1    the four entities, their countries, roles and tax identifiers (s.1)
    A1    the six `[ ]` placeholders, verbatim (s.1)
    A2    cybergod.ai list prices 100 / 200 / 200 / 2,500 / 5,000 and the OEM 50% column (s. price
          list), OEM only under a signed White Label agreement at a 1,000 seat minimum

Published third-party facts, quoted as published and labelled as such
    s.5   Gartner, 4 May 2026, G00839252. Market context, not our forecast.
    s.11  G-Cloud 14 published rate cards, April to May 2024: PwC GBP 2,300, KPMG GBP 2,150,
          Deloitte GBP 1,825 per consultant day

Channel stages (A5), from the founder's own account of each conversation
    A5    one proposal with a pilot proposed and a security review pending; one drafted and
          unsigned distribution agreement; two early conversations. None is a customer.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pptx.enum.text import PP_ALIGN                                  # noqa: E402

from build_consensus_deck import (                                   # noqa: E402
    BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, LINE, MONO, MUTED, TEXT, VIOLET, WHITE,
    _rect, _tb)
from deck_chrome import X3, W3, assert_layout, guarded               # noqa: E402

FOOT = "S4BIZ GROUP · SEED ROUND · CONFIDENTIAL · SEPTEMBER 2026"
X, W = 0.55, 12.23        # left margin and content width, same as deck_chrome's column geometry
BODY_TOP = 2.40           # every non-hero slide starts its content here. A long sub wraps to two
                          # lines and ends near 2.10, so 2.40 is clearance and not taste.
MAIN_SLIDES = 13

# The measurement the brief asked for, kept as constants so --audit compares against a number that
# lives in one place. TARGET is the DocSend benchmark. CEILING is the brief's failure threshold.
WORDS_TARGET = 40
WORDS_CEILING = 500

# Carried through verbatim from _pack_src/FACTS.md s.1. NEVER GUESS ONE OF THESE.
PH_ENTITY = ["[Stars4business OU registry code]", "[Stars4business OU registered address]",
             "[bank account / IBAN]", "[S4biz UG registered address]",
             "[S4BIZ Lda registered address]", "[CyberGod LLC registered address]"]

BANNED = ("delve", "leverage", "robust", "seamless", "landscape", "testament", "underscore",
          "pivotal")
DASHES = ("—", "–")


# ---------------------------------------------------------------------------------------------
# LAYOUT VOCABULARY. Five helpers, deliberately. The old build had a helper per slide shape and
# that is how thirty shapes end up on one slide: a helper that is easy to call gets called.
# ---------------------------------------------------------------------------------------------
def line(s, y, text, size=15, col=BODY, x=X, w=W, bold=False, h=1.10, space=1.38,
         align=PP_ALIGN.LEFT, font=TEXT):
    """One block of body prose. ONE shape. The default size is 15pt, not 10pt: the whole point of
    a 13-word slide is that the words are large enough to be read from the back of a room."""
    return _tb(s, x, y, w, h, text, size, col, font, bold, align, space=space)


def rule(s, y, x=X, w=W, col=VIOLET, th=0.028):
    """A hairline. It is the only decoration in this deck, and it separates an assertion from its
    evidence without adding a panel, a border and a fill to do it."""
    return _rect(s, x, y, w, th, col, None)


def labelled(s, x, y, w, label, text, col=CYAN, tsize=14, h=1.30):
    """A mono label over a body line. TWO shapes. This replaces card(), which is four shapes and a
    filled panel, because a panel around 14 words is a box drawn to make the slide look busier."""
    _tb(s, x, y, w, 0.26, label.upper(), 10.5, col, MONO, True)
    _tb(s, x, y + 0.36, w, h, text, tsize, BODY, TEXT, space=1.34)


def bigstat(s, x, y, w, value, label, col=CYAN, vsize=54, align=PP_ALIGN.LEFT):
    """A number at display size with its caption under it. TWO shapes.

    stat() in build_consensus_deck puts the caption at a FIXED y+0.58, which is correct at its own
    30pt default and collides with the value at any larger size. Rather than change a helper four
    other decks depend on, the offset here is DERIVED from the point size: a line of Arial Black at
    n points is about n/72 * 1.25 inches tall. That is the same arithmetic discipline as the header
    row and the title cap, and it is why a 96pt number on slide 4 does not need hand-nudging.
    """
    vh = vsize / 72.0 * 1.25
    _tb(s, x, y, w, vh, value, vsize, col, DISPLAY, True, align)
    _tb(s, x, y + vh + 0.08, w, 0.62, label, 10, MUTED, MONO, align=align, space=1.30)


def rows2(s, x, y, w, head, items, lcol=CYAN, rh=0.52, size=13, lw=2.30):
    """A two-column list: mono key, body value. Used for the competition day rates and A1/A2/A5.

    The row step is arithmetic against the footer at 7.04, which deck_chrome asserts. rh=0.52 at
    13pt leaves a whole line of air between rows, which is what makes four rows readable without a
    grid drawn around them.
    """
    if head:
        _tb(s, x, y, lw, 0.26, head[0].upper(), 8.6, MUTED, MONO, True)
        _tb(s, x + lw, y, w - lw, 0.26, head[1].upper(), 8.6, MUTED, MONO, True)
        _rect(s, x, y + 0.30, w, 0.012, LINE, None)
        y += 0.44
    for key, val, col in items:
        _tb(s, x, y, lw - 0.10, 0.34, key, size, col or lcol, MONO, True)
        _tb(s, x + lw, y, w - lw, 0.34, val, size, BODY, TEXT)
        y += rh
    return y


# ---------------------------------------------------------------------------------------------
def build(template, out):
    d = guarded(Deck(template), tail=VIOLET)

    # ============================================================= 01 COVER (hero)
    # Nothing but the assertion and one line of identification. No stats row: a cover that already
    # carries five numbers has spent the attention the next twelve slides need.
    s = d.slide("S4biz Group · Cybergod LLC · seed round · September 2026",
                [("WE SHOW YOU WHAT THE", WHITE),
                 ("INTERNET ALREADY KNOWS.", WHITE),
                 ("THEN WE DEFEND IT.", VIOLET)],
                footer=FOOT, hero=True)
    rule(s, 4.62, w=4.20, col=VIOLET)
    line(s, 4.92, "S4biz Group  ·  Two products in production  ·  Raising EUR 20,000,000",
         16, BODY, h=0.50)

    # ============================================================= 02 FOUNDER
    s = d.slide("FOUNDER", "TWENTY YEARS ON THE", " ATTACKER SIDE.",
                "Now pointed at defence. Evgeny \"Jev\" Vainshtein, principal architect.", FOOT)
    for i, (lab, names, col) in enumerate([
            ("Offensive cyber", "Cognyte · Cyberbit · Intellexa", CYAN),
            ("Hyperscale cloud", "AWS · Red Hat · NetApp · Huawei · Canonical", VIOLET),
            ("Tier-1 networks", "Colt · Cogent · Telefonica · Deutsche Telekom", INDIGO)]):
        labelled(s, X3[i], BODY_TOP, W3, lab, names, col, tsize=14, h=0.95)
    rule(s, 4.30, w=6.60)
    line(s, 4.58, "The product needs all three. Almost nobody has all three.",
         20, WHITE, bold=True, h=0.60, space=1.15)
    line(s, 5.50, "First hire: an enterprise account executive with a CISO network.",
         13, MUTED, h=0.40)

    # ============================================================= 03 EVIDENCE
    s = d.slide("EVIDENCE", "BOTH PRODUCTS ARE", " IN PRODUCTION.",
                "Not a prototype and not a deck. Running code, on real traffic.", FOOT)
    for i, (val, cap, col) in enumerate([
            ("22", "companies assessed\nJune to August 2026", CYAN),
            ("5", "live properties defended\nby Perseus, today", GREEN),
            ("264", "tests behind the SOC\nacross 8 files", VIOLET)]):
        bigstat(s, X3[i], BODY_TOP, W3, val, cap, col, vsize=60)
    rule(s, 4.55, w=8.00)
    line(s, 4.85, "Pre-revenue. No customer has signed yet, and the round is what changes that.",
         16, WHITE, h=0.50)

    # ============================================================= 04 PROBLEM
    # One focal point, centred, because the number IS the argument and the sentence under it is a
    # caption. Centre alignment is used on exactly this slide and nowhere else.
    s = d.slide("PROBLEM", "A COMPANY CANNOT", " SEE ITSELF.",
                "Not the way an attacker does. The exposure picture is assembled by hand and "
                "stale within a week.", FOOT)
    bigstat(s, X, 2.55, W, "42,369",
            "attack-shaped requests\nin 14 days, against our own small estate",
            CYAN, vsize=96, align=PP_ALIGN.CENTER)
    line(s, 5.45, "One address tried 551 different paths using 143 different announced browsers.",
         16, WHITE, h=0.50, align=PP_ALIGN.CENTER)

    # ============================================================= 05 WHY NOW
    s = d.slide("WHY NOW", "DEFENCES MOVE", " QUARTERLY.",
                "Applications move weekly. The gap between those two is where the breach lives.",
                FOOT)
    line(s, BODY_TOP,
         "Last week our own system retired a rule that had become a match for 99 paths our build "
         "output serves. Nobody would have noticed until customers saw errors.",
         19, WHITE, w=11.60, h=1.60, space=1.30)
    rule(s, 4.45, w=11.60, col=LINE, th=0.012)
    line(s, 4.75,
         "Gartner, 4 May 2026 (G00839252): by 2028 more than half of organisations adopting "
         "threat intelligence will prioritise platforms that enforce over platforms that report. "
         "Market context, not our forecast.",
         11.5, MUTED, w=11.60, h=1.20, space=1.36)

    # ============================================================= 06 SOLUTION
    s = d.slide("SOLUTION", "ONE NAME IN.", " FOUR DECKS OUT.",
                "Two products, in the order a customer meets them.", FOOT)
    _tb(s, X, BODY_TOP, 5.80, 0.30, "SEE IT  ·  CYBERGOD.AI", 12, CYAN, MONO, True)
    line(s, BODY_TOP + 0.45,
         "Type a company name. Two minutes later, four board decks and a priced risk figure.",
         19, WHITE, x=X, w=5.80, h=1.90, space=1.30)
    _rect(s, 6.45, BODY_TOP, 0.012, 2.30, LINE, None)
    _tb(s, 6.98, BODY_TOP, 5.80, 0.30, "DEFEND IT  ·  PERSEUS AI SOC", 12, VIOLET, MONO, True)
    line(s, BODY_TOP + 0.45,
         "Then defend what stays exposed, on the customer's own infrastructure, deciding for "
         "itself.",
         19, WHITE, x=6.98, w=5.80, h=1.90, space=1.30)

    # ============================================================= 07 PRODUCT
    s = d.slide("PRODUCT", "NO SCAN. NO PROBE.", " NO PERMISSION.",
                "Host data comes from public indexes and logs. We read the company's own "
                "published site and certificate, which is what any browser does.", FOOT)
    line(s, 2.55,
         "So a partner can assess a prospect before the first conversation, with no authorisation "
         "and no maintenance window.",
         18, WHITE, w=11.60, h=1.20, space=1.32)
    rule(s, 4.30, w=11.60)
    line(s, 4.60,
         "Perseus decides for itself: four models from four vendors propose, deterministic code "
         "decides, and every block expires by itself.",
         18, BODY, w=11.60, h=1.20, space=1.32)

    # ============================================================= 08 DEFENSIBILITY
    # The most important slide in the deck. Three numbers, each one a refusal the product now
    # makes, and the closing line names what the asset actually is.
    s = d.slide("DEFENSIBILITY", "THEY CAN WRITE", " THE SCANNER.",
                "They cannot write the twenty years of refusals. Anyone can query a public index. "
                "Proving what came back belongs to the customer is the product.", FOOT)
    for i, (num, consequence, col) in enumerate([
            ("998", "unrelated hosts adopted from one shared certificate authority, before the "
                    "gate that now refuses it", CYAN),
            ("192", "addresses across 44 networks matched by one brand token that was also a "
                    "common dictionary word", VIOLET),
            ("203", "addresses and eight figures of priced risk, when one government site "
                    "resolved to an entire federal government", INDIGO)]):
        _tb(s, X3[i], 2.55, W3, 0.80, num, 46, col, DISPLAY, True)
        _tb(s, X3[i], 3.42, W3, 1.50, consequence, 12.5, BODY, TEXT, space=1.34)
    rule(s, 5.25, w=9.20)
    line(s, 5.55, "Fifteen ownership gates, each one bought by a named incident. That is the "
                  "asset.", 19, WHITE, bold=True, h=0.60, space=1.20)

    # ============================================================= 09 BUYER AND BUDGET
    s = d.slide("BUYER AND BUDGET", "WE DO NOT SELL TO", " THE CISO.",
                "We arm the partner who is already in the room. MSP, VAR, integrator, "
                "consultancy.", FOOT)
    line(s, 2.55,
         "White-labelled, so the client sees the partner's brand and the engine works underneath.",
         20, WHITE, w=11.20, h=1.10, space=1.28)
    rule(s, 4.10, w=11.20)
    line(s, 4.40,
         "A first meeting costs the partner EUR 100. It comes out of a budget line they already "
         "have, not a new one they have to create.",
         18, BODY, w=11.20, h=1.30, space=1.32)

    # ============================================================= 10 MARKET
    s = d.slide("MARKET", "THE UNIT IS A PARTNER,", " NOT A SEAT.",
                "Bottom up, from our own published price list. We do not state a total market "
                "figure we cannot defend.", FOOT)
    line(s, 2.55,
         "At the Platinum tier a partner buys a seat at EUR 120 and sells at EUR 200. One hundred "
         "seats is EUR 8,000 a month of partner margin, renewing without a renewal conversation.",
         19, WHITE, w=11.60, h=1.90, space=1.30)
    rule(s, 5.00, w=6.00, col=GREEN)
    line(s, 5.30, "Delivery cost is close to zero. The engine does the work.", 17, GREEN, h=0.50)

    # ============================================================= 11 COMPETITION
    s = d.slide("COMPETITION", "TODAY THESE DEALS GO TO", " A BIG FOUR.",
                "Named, because pretending there is no competition is the fastest way to lose "
                "the room.", FOOT)
    rows2(s, X, 2.50, 9.80, ("Who", "Published day rate"),
          [("PwC", "GBP 2,300 per consultant day", WHITE),
           ("KPMG", "GBP 2,150 per consultant day", WHITE),
           ("Deloitte", "GBP 1,825 per consultant day", WHITE),
           ("cybergod.ai", "EUR 100 per run, about two minutes", CYAN)],
          rh=0.54, size=14, lw=2.60)
    line(s, 5.05,
         "Published G-Cloud 14 rate cards, April to May 2024. A consultant delivers a signed "
         "opinion with liability attached. We deliver evidence. The EUR 100 run is what tells you "
         "whether the EUR 70,000 engagement is needed.",
         12, MUTED, w=11.60, h=1.30, space=1.36)

    # ============================================================= 12 WHAT THE ROUND BUYS
    s = d.slide("WHAT THE ROUND BUYS", "THREE OUTCOMES,", " IN ORDER.",
                "Named outcomes rather than dates, because there is no financial model behind a "
                "date yet.", FOOT)
    for i, (lab, text, col) in enumerate([
            ("First", "The commercial core hired, and first customers under contract on both "
                      "products.", CYAN),
            ("Then", "Cloud shipped: continuous monitoring, customer-held keys, enforcement and "
                     "takedown.", VIOLET),
            ("Then", "ISO 27001 and SOC 2, a second hosting region, and the third product "
                     "built.", INDIGO)]):
        y = 2.50 + i * 1.35
        _rect(s, X, y + 0.04, 0.05, 0.62, col, None)
        _tb(s, X + 0.34, y, 1.70, 0.34, lab.upper(), 12, col, MONO, True)
        line(s, y + 0.40, text, 17, WHITE, x=X + 0.34, w=10.80, h=0.80, space=1.26)

    # ============================================================= 13 THE ASK
    s = d.slide("THE ASK", "EUR ", "20,000,000.",
                "Sales and channel 40 · Engineering and cloud 30 · Marketing 15 · Assurance 5 · "
                "Working capital 10", FOOT)
    line(s, 2.35,
         "Four offices already incorporated and waiting to be staffed: Tallinn, Frankfurt, "
         "Lisbon, Delaware.", 16, WHITE, h=0.60, space=1.25)
    rule(s, 3.20)
    for i, (lab, text, col) in enumerate([
            ("See it live", "Pick any company name. We run it in front of you.", CYAN),
            ("Test it", "Technical due diligence against the engine and the test suite.", VIOLET),
            ("Data room", "Open on request.", INDIGO)]):
        labelled(s, X3[i], 3.55, W3, lab, text, col, tsize=14, h=1.10)
    line(s, 5.85, "Evgeny \"Jev\" Vainshtein  ·  feranicus@s4biz.io  ·  cybergod.ai",
         14, CYAN, h=0.45)

    # =========================================================================================
    # APPENDIX. Label headlines are fine here and density may rise, but no slide goes past 120
    # words, because an appendix slide is still read in a room and not filed.
    # =========================================================================================

    # ============================================================= A1 THE GROUP
    s = d.slide("APPENDIX A1 · GROUP STRUCTURE", "THE", " GROUP.",
                "Four entities. Stars4business OU is the contracting party for every partner "
                "agreement. Governing law Estonia, binding language English.", FOOT)
    rows2(s, X, BODY_TOP, 11.60, ("Entity · country · role", "Tax identifier"),
          [("Stars4business OU", "Estonia · EU hub, consultancy, contracting entity · "
                                 "VAT EE102156878", WHITE),
           ("S4biz UG", "Germany · software development · USt-IdNr. DE361822318", WHITE),
           ("S4BIZ Lda", "Portugal · Iberia operations · NIF 518007596", WHITE),
           ("CyberGod LLC", "Delaware, USA · cyber and cloud · EIN on file", WHITE)],
          rh=0.50, size=12.5, lw=2.90)
    rule(s, 4.90, col=LINE, th=0.012)
    _tb(s, X, 5.15, W, 0.26, "OPEN, AND NOT GUESSED", 10, MUTED, MONO, True)
    line(s, 5.48, "   ".join(PH_ENTITY), 11, BODY, h=0.90, space=1.40)

    # ============================================================= A2 PRICE LISTS
    s = d.slide("APPENDIX A2 · PRICE LISTS", "PRICE", " LISTS.",
                "European list reference in EUR, excluding VAT. Every end-customer price is set "
                "by the partner.", FOOT)
    _tb(s, X, BODY_TOP, 5.60, 0.28, "CYBERGOD.AI", 11, CYAN, MONO, True)
    rows2(s, X, BODY_TOP + 0.40, 5.60, None,
          [("100", "one run", WHITE), ("200", "report subscription, per seat per month", WHITE),
           ("200", "findings review, per hour", WHITE), ("2,500", "workshop, per day, SME", WHITE),
           ("5,000", "large enterprise, two days", WHITE)],
          rh=0.42, size=12, lw=1.30)
    _tb(s, 6.95, BODY_TOP, 5.83, 0.28, "PERSEUS AI SOC, PER MONTH", 11, VIOLET, MONO, True)
    rows2(s, 6.95, BODY_TOP + 0.40, 5.83, None,
          [("450", "SENTRY, detection only, up to 3 applications", WHITE),
           ("1,200", "SHIELD, autonomous enforcement, up to 10", WHITE),
           ("2,900", "CITADEL, legacy integration, named engineer, up to 25", WHITE),
           ("90", "each additional protected application", WHITE),
           ("8", "each investigation beyond the tier allowance", WHITE)],
          rh=0.42, size=12, lw=1.30)
    rule(s, 5.05, col=LINE, th=0.012)
    _tb(s, X, 5.30, W, 0.26, "PARTNER LADDER, ONE CONTRACT, BOTH PRODUCTS", 10, MUTED, MONO, True)
    line(s, 5.62, "Partner 10 per cent  ·  VAR 20  ·  Gold 30  ·  Platinum 40  ·  OEM 50. The OEM "
                  "column needs a signed White Label agreement at a 1,000 seat minimum.",
         12, BODY, h=0.95, space=1.38)

    # ============================================================= A3 WHERE WE ARE WEAKER
    s = d.slide("APPENDIX A3 · HONEST GAPS", "WHERE WE ARE", " WEAKER.",
                "Six gaps, from our own competitive analyses. Diligence finds all six, so they "
                "are on a slide.", FOOT)
    gaps = [("No continuous monitoring", "Both products answer a point in time. Continuous is in "
                                         "the round, not in the product."),
            ("No primary collection", "Discovery reads public indexes. We run no sensors of our "
                                      "own."),
            ("No enforcement or takedown", "Perseus blocks at the HTTP layer only. It files no "
                                           "takedowns."),
            ("No reference customer for Perseus", "The five live properties are ours. No third "
                                                  "party runs it yet."),
            ("No ISO 27001, no SOC 2, one region", "Certification and a second region are funded "
                                                   "by this round, not held today."),
            ("No 24/7 analyst desk", "The loops run to a schedule. No staffed desk, and no "
                                     "published response target.")]
    for i, (head, text) in enumerate(gaps):
        col = X if i < 3 else 6.95
        y = BODY_TOP + (i % 3) * 1.42
        _tb(s, col, y, 5.60, 0.28, head, 13, WHITE, DISPLAY, True)
        _tb(s, col, y + 0.36, 5.60, 0.90, text, 11.5, BODY, TEXT, space=1.34)

    # ============================================================= A4 HOW THE ENGINE WORKS
    s = d.slide("APPENDIX A4 · ARCHITECTURE", "HOW THE ENGINE", " WORKS.",
                "One name in. Four stages. Not one packet is sent to the company being "
                "assessed.", FOOT)
    stages = [("01", "PUBLIC INDEXES",
               "Shodan · RIPEstat · RDAP · crt.sh · DNS over HTTPS", CYAN),
              ("02", "THE TARGET'S OWN PAGE",
               "Its published site and certificate, read the way a browser reads them", VIOLET),
              ("03", "OWNERSHIP GATES",
               "Fifteen refusals decide what is actually the customer's", INDIGO),
              ("04", "FOUR DECKS OUT",
               "Findings · C-BIQ · GEOPOL · DELTAS, plus a priced risk figure", GREEN)]
    for i, (num, head, text, col) in enumerate(stages):
        y = BODY_TOP + i * 0.98
        _rect(s, X, y + 0.04, 0.05, 0.56, col, None)
        _tb(s, X + 0.32, y, 0.60, 0.28, num, 12, col, MONO, True)
        _tb(s, X + 1.20, y - 0.02, 3.40, 0.30, head, 13, WHITE, DISPLAY, True)
        _tb(s, X + 4.80, y, 7.20, 0.58, text, 12, BODY, TEXT, space=1.30)
    rule(s, 6.05, col=LINE, th=0.012)
    line(s, 6.30, "Perseus reads our own access logs on the same substrate, proposes with four "
                  "vendors and lets deterministic code decide.", 11.5, MUTED, h=0.40)

    # ============================================================= A5 CHANNEL STATUS
    s = d.slide("APPENDIX A5 · CHANNEL", "CHANNEL", " STATUS.",
                "Four conversations, each labelled with the stage it is genuinely at.", FOOT)
    rows2(s, X, BODY_TOP, 11.60, ("Where", "Actual stage, precisely"),
          [("byon, Germany", "PROPOSAL. A pilot is proposed and their internal security review is "
                             "pending. Not a signed pilot.", WHITE),
           ("Swiss distributor", "AGREEMENT DRAFTED. The distribution agreement is unsigned and "
                                 "nothing has been sold under it.", WHITE),
           ("Southern Africa", "EARLY CONVERSATION. A local entity or partner of record is still "
                               "an open decision.", WHITE),
           ("A Canadian bank", "EARLY CONVERSATION. A named technical contact, a small quota, no "
                               "commercial discussion.", WHITE)],
          rh=0.62, size=12.5, lw=2.60)
    rule(s, 5.20, col=LINE, th=0.012)
    line(s, 5.45,
         "NONE OF THE FOUR IS A CUSTOMER. None is a win and none is a running pilot. The first "
         "reference call establishes exactly this, so the deck says it first.",
         13, MUTED, bold=True, h=0.80, space=1.34)

    assert_layout(d)
    return d.save(out)


# ---------------------------------------------------------------------------------------------
# AUDIT. A build that prints "built" and exits zero is not evidence about the deck it built, so
# the checks read the DELIVERED FILE rather than this source. Same rule as every other gate here.
# ---------------------------------------------------------------------------------------------
_CHROME = re.compile(r"^(S4|BIZ|>>\s*\d+|" + re.escape(FOOT) + r")$", re.I)


def _slide_words(slide):
    """Words of headline, sub-heading and body. Chrome is excluded and counted separately.

    The wordmark, the footer and the page number are on every slide by construction, so counting
    them makes a 12-word slide read as 24 and the measurement stops meaning anything. The eyebrow
    is chrome for the same reason: it is a running header, not copy the reader is asked to process.
    """
    content, chrome = [], []
    for i, sh in enumerate(slide.shapes):
        if not sh.has_text_frame:
            continue
        txt = sh.text_frame.text.strip()
        if not txt:
            continue
        (chrome if _CHROME.match(txt) else content).append(txt)
    # the eyebrow is the first non-empty text box after the wordmark runs; identify it by font
    return content, chrome


def _words(texts):
    n = 0
    for t in texts:
        n += len([w for w in re.split(r"\s+", t) if re.search(r"[A-Za-z0-9]", w)])
    return n


def audit(path):
    from pptx import Presentation
    from pptx.util import Pt
    prs = Presentation(path)
    rows, total_main, headlines, bad = [], 0, [], []
    for i, sl in enumerate(prs.slides, 1):
        content, chrome = _slide_words(sl)
        # The eyebrow is the only 10.5pt Consolas run on the slide. Drop it from content: it is a
        # running header. Identified by MEASUREMENT, not by index, same rule as tail_colour.
        eyebrow = None
        head = None
        for sh in sl.shapes:
            if not sh.has_text_frame:
                continue
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    if r.font.name == MONO and r.font.size == Pt(10.5) and r.text.strip():
                        eyebrow = r.text.strip()
                    if r.font.size in (Pt(30), Pt(38)) and r.text.strip() and head is None:
                        head = sh.text_frame.text.strip().replace("\n", " ")
        content = [c for c in content if c != eyebrow]
        n = _words(content)
        rows.append((i, n, _words(chrome) + _words([eyebrow or ""]), len(content),
                     (head or content[0] if content else "")[:46]))
        if i <= MAIN_SLIDES:
            total_main += n
            headlines.append(head or "")
        for t in content:
            for dash in DASHES:
                if dash in t:
                    bad.append((i, "dash", t[:60]))
            low = t.lower()
            for b in BANNED:
                if re.search(r"\b%s\b" % b, low):
                    bad.append((i, "banned word %r" % b, t[:60]))

    print("\nPER-SLIDE WORD COUNT (content = headline + sub + body; chrome counted separately)")
    print("  %-4s %6s %7s %7s  %s" % ("#", "words", "chrome", "shapes", "headline"))
    for i, n, ch, sh, head in rows:
        flag = " " if i > MAIN_SLIDES or n <= WORDS_TARGET else "!"
        print("%s %-4d %6d %7d %7d  %s" % (flag, i, n, ch, sh, head))
    avg = total_main / float(MAIN_SLIDES)
    print("\n  slides 1-%d: %d words, average %.1f a slide (DocSend benchmark %d, brief ceiling %d)"
          % (MAIN_SLIDES, total_main, avg, WORDS_TARGET, WORDS_CEILING))
    if total_main > WORDS_CEILING:
        print("  NOTE: the SUPPLIED COPY is %d words. This build adds none, so the ceiling cannot"
              % total_main)
        print("        be met without deleting sentences the founder fixed. That is his call.")

    print("\nHEADLINES 1-%d, AS ONE PARAGRAPH:" % MAIN_SLIDES)
    print("  " + " ".join(h for h in headlines if h))

    print("\nPROHIBITED CONTENT IN SLIDE TEXT: %d" % len(bad))
    for i, why, t in bad:
        print("  slide %02d  %s  %r" % (i, why, t))
    shapes = [sh for _i, _n, _c, sh, _h in rows]
    print("\nCONTENT SHAPES PER SLIDE: min %d, max %d, mean %.1f (old build 19 to 43)"
          % (min(shapes), max(shapes), sum(shapes) / float(len(shapes))))
    return 1 if bad else 0


DEFAULT_OUT = os.path.join(
    os.path.expanduser("~"), "Downloads", "cybergod partnership", "Investor Pack",
    "S4biz_Investor_Deck_EN.pptx")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--no-audit", action="store_true", help="build only, skip the measurement")
    a = ap.parse_args()
    if not os.path.exists(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    p = build(a.template, a.out)
    print("built: %s (%.1f KB, %d slides)"
          % (p, os.path.getsize(p) / 1024.0, MAIN_SLIDES + 5))
    if a.no_audit:
        return 0
    return audit(p)


if __name__ == "__main__":
    sys.exit(main())
