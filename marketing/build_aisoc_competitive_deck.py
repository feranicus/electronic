#!/usr/bin/env python3
"""build_aisoc_competitive_deck.py — PERSEUS AI SOC, the competitive picture, told honestly.

    python marketing/build_aisoc_competitive_deck.py [--out PATH] [--template PATH]

Document 05 of the AI SOC pack. INTERNAL AND PARTNER ONLY, per FACTS.md section 17, which is why
the footer says so on every slide rather than only on the cover.

It reuses build_consensus_deck.py's Deck/card/bullets/stat helpers and deck_chrome.py's guards, so
the S4biz template exists in exactly ONE implementation and the decks cannot drift apart. Same
reason build_perseus_shield_deck.py does it.

THE STRUCTURE IS BORROWED ON PURPOSE. S4biz_Cybergod_Competitive_Analysis.pptx works because of
the order it puts things in: who is NOT a competitor, then the category, then head to head, then
where we are better, then WHERE WE ARE WORSE, then the real difference, then price, then who wins
which deal, then the roadmap. The "worse" slide is the load-bearing one. Without it a buyer reads
the other ten as marketing and discounts all of them. That sequence is kept here.

FIVE RULES THIS DECK OBEYS
--------------------------
1. NO UNSUBSTANTIATED COMPARISON AGAINST A NAMED PRODUCT. Perseus has been benchmarked against
   nobody. Slide 06 therefore compares CATEGORIES (WAF, DDoS scrubbing, MDR service, AI SOC
   triage, Perseus) on what each is architecturally FOR, which is checkable against the vendors'
   own documentation and cannot be refuted by a competitor's next release, and it says so on the
   slide. An unsubstantiated superiority claim against a named product is comparative advertising
   under UWG s.6 and the UCP Directive. It would also poison this engine's own evidence
   discipline, which is the thing being sold.

2. A PRICE AND A SILENCE ARE BOTH FACTS ABOUT DISCLOSURE. Naming a competitor's published price,
   and naming a vendor that publishes none, are statements about what is on a public page. Neither
   is a comparative claim. That is the whole licence for slides 03, 04 and 05.

3. EVERY NUMBER IS TRACED. Sources below. Nothing from FACTS.md section 15.4 appears anywhere in
   this file: those are self-declared marketplace placeholders and content-farm fabrications, each
   confirmed absent from the vendor's own pages, and one of them (AirMDR "per user") has the wrong
   unit for the right vendor, which is exactly how a fabricated figure gets repeated.

4. WHAT WE DO NOT HAVE IS ON A SLIDE, WITH A DATE. Six gaps, slide 08, straight out of the open
   items register. An availability figure for Perseus does not exist yet, so none is quoted here.

5. NO EM DASHES AND NO EN DASHES ANYWHERE IN SLIDE TEXT. Standing rule for anything a human reads.
   Banned words too: delve, leverage, robust, seamless, landscape, testament, underscore, pivotal.

TRACED NUMBERS — every figure on a slide, and where it came from
----------------------------------------------------------------
FACTS.md is C:\\Users\\feran\\Downloads\\cybergod partnership\\aisoc_pack\\_src\\FACTS.md, v1.0,
17 September 2026. Section numbers below are its sections.

  11 vendor-published price points found      FACTS 15.1, counted: Blumira, Field Effect,
                                              CrowdStrike, SentinelOne, Defender for Business,
                                              Defender Suite, AirMDR, Cloudflare, AWS WAF, AWS
                                              Shield Advanced, Microsoft Sentinel
  16 vendors publishing no price at all       FACTS 15.3, counted from the quote-only list
  300 asset floor, cheapest listed MDR SKU    FACTS 15.5, Rapid7 MDR Essential
  EUR 1,200 / month, SHIELD, published        FACTS 14 price list, effective 17 September 2026
  EUR 450 / 1,200 / 2,900 a month             FACTS 14, SENTRY / SHIELD / CITADEL
  EUR 90 per extra application, EUR 8 per     FACTS 14
    investigation, EUR 200 an hour
  free 30-day detection-only pilot            FACTS 14 price list, and FACTS 12 shape C
  Blumira $12 / $16 / $21 per employee        FACTS 15.1, blumira.com/pricing
  Field Effect $5 to $25 per user             FACTS 15.1, fieldeffect.com/products/mdr/pricing
  CrowdStrike $7.99 / $14.99 / $19.99,        FACTS 15.1, crowdstrike.com/en-us/pricing
    Go capped at 100 devices
  SentinelOne $69.99 to $229.99 a year,       FACTS 15.1, sentinelone.com/platform-packages
    footnote scopes it to 5 to 100 seats
  Defender for Business $3.00, 300-user       FACTS 15.1, microsoft.com
    ceiling
  Cloudflare $20 Pro / $200 Business          FACTS 15.1, cloudflare.com/plans
    per domain
  AWS WAF $430 a month worked example         FACTS 15.1, aws.amazon.com/waf/pricing, AWS's own
    (3 ACLs, 21 rules, 35M requests)          example with bot control
  Microsoft Sentinel $4.30 to $5.59 per GB    FACTS 15.1, prices.azure.com / learn.microsoft.com
  AirMDR $4.00 per investigation              FACTS 15.1, airmdr.com/fast
  Rapid7 $73,000 a year at 300 assets,        FACTS 15.2 and 15.5, AWS Marketplace rate card
    = $20.28 per asset a month
  Arctic Wolf $44,000 a year up to 100        FACTS 15.2 and 15.5, marketplace rate card
    users, = $36.67 per user a month
  Red Canary $120 per endpoint a year         FACTS 15.2, marketplace rate card
  Prophet Security $10 per investigation      FACTS 15.2, $50,000 a year for 5,000
  Simbian $10 per alert                       FACTS 15.2, $10,000 a year per 1,000
  Huntress $2.99 to $184 per endpoint,        FACTS 15.3, vendor statements, attributed as such
    Expel glossary $10 to $30 per device
  Huntress 50-agent minimum                   FACTS 15.5
  Gartner MDR Market Guide, paywalled,        FACTS 15.3
    no public band
  EUR 12 a head at 100 people, EUR 2.40 at    FACTS 15.6, arithmetic on the SHIELD list price
    500, on SHIELD
  4 models, 4 vendors: deepseek-3.2,          FACTS 6, enrich._FALLBACKS
    llama-4-maverick, gemma-4-31B-it,
    kimi-k2.6
  panel answered 0 of 4                       FACTS 6 and 13, measured 2026-09-13
  79 hostile against 134 clean, refused       FACTS 4 and 13, measured 2026-09-13 weekly cycle
  2 blocking, 7 detecting, 0 ready            FACTS 13 and 18 item 7, at 2026-09-13
  5 rules retired, /@fs/ matched 99 paths     FACTS 3 and 13, 2026-09-13 weekly cycle
    we serve
  24 hours in detection, 3 of 4 quorum,       FACTS 4, the promotion gate
    1 hostile hit, exactly 0 clean hits
  six integers the panel may propose          FACTS 4, ruleset.BOUNDS, hub set
  10 minute watch loop, 04:40 daily,          FACTS 3
    Sunday 05:20 weekly
  no SLA targets, no ISO 27001, no SOC 2,     FACTS 18 items 1, 2, 6, 7, 8
    one region, no reference customer,
    Grafana board is roadmap
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  - one template implementation, reused
    AMBER, BODY, CYAN, Deck, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from deck_chrome import X2, W2, X3, W3, X4, W4, assert_layout, guarded  # noqa: E402

FOOT = ("S4BIZ GROUP · CYBERGOD LLC · PERSEUS AI SOC · INTERNAL SALES MATERIAL, "
        "NOT FOR CUSTOMER DISTRIBUTION")

# Verified 17 September 2026. FACTS.md section 15 carries the source for every one of these.
N_VENDOR_PUB = 11          # 15.1, counted
N_NO_PRICE = 16            # 15.3, counted
RAPID7_FLOOR = "300"       # 15.5, assets on the cheapest transactable SKU
OUR_LIST = "€1,200"        # 14, SHIELD list price a month

# MEASURED ON THIS DECK'S OWN RENDER, deliberately tighter than deck_chrome.TITLE_MAX.
# deck_chrome caps at 50 because that is what the proposal decks measured. This deck's titles run
# through more capital W and M glyphs (WHO, WORSE, CATEGORY, COMPARED), and Arial Black glyph
# widths vary enough that a character count is only a proxy. 40 is the low end of the band that
# was observed to fit on one line here, and the low end is the one to take: a title that wraps
# lands on the sub-heading at y=1.55 and nothing in the build notices.
TITLE_MAX = 40


def table(s, x, y, w, cols, rows, widths, head_col=CYAN, size=9.2, rh=0.44):
    """Plain table. Column widths are FRACTIONS of w and must sum to 1."""
    assert abs(sum(widths) - 1.0) < 0.01, "column widths must sum to 1"
    cx = x
    for c, fr in zip(cols, widths):
        _tb(s, cx, y, w * fr - 0.08, 0.28, c.upper(), 8.4, head_col, MONO, True)
        cx += w * fr
    _rect(s, x, y + 0.30, w, 0.012, fill=LINE, line=None)
    yy = y + 0.40
    for r in rows:
        cx = x
        for cell, fr in zip(r, widths):
            txt = cell[0] if isinstance(cell, tuple) else cell
            col = cell[1] if isinstance(cell, tuple) else BODY
            _tb(s, cx, yy, w * fr - 0.08, rh, txt, size, col, TEXT)
            cx += w * fr
        yy += rh
    return yy


def _strict_titles(deck, cap=TITLE_MAX):
    """Tighten deck_chrome's title cap for this deck, without forking its guard.

    guarded() installs the shared 50-character check and the tail recolour. This wraps the result
    rather than replacing it, so both checks run and a new slide cannot get past either. Written
    this way because the alternative, copying check_title with a different constant, is exactly
    the drift deck_chrome exists to stop.
    """
    original = deck.slide

    def _slide(eyebrow, title, title_tail=None, sub=None, footer="", hero=False):
        if not hero:
            n = len(title) + len(title_tail or "")
            if n > cap:
                raise SystemExit("[X] title is %d characters, this deck's cap is %d: %r"
                                 % (n, cap, title + (title_tail or "")))
        return original(eyebrow, title, title_tail, sub, footer, hero)

    deck.slide = _slide
    return deck


def build(template, out):
    d = _strict_titles(guarded(Deck(template), tail=VIOLET))

    # ------------------------------------------------------------------ 01. cover
    s = d.slide("PERSEUS AI SOC · COMPETITIVE ANALYSIS · 17 SEPTEMBER 2026",
                [("WHO WE COMPETE WITH.", WHITE),
                 ("WHO WE DO NOT.", WHITE),
                 ("AND WHAT THE CATEGORY", WHITE),
                 ("WILL NOT TELL YOU.", VIOLET)],
                None,
                "Internal and partner enablement. Every competitor figure in here carries the "
                "page it came from and the class of source it is. Nothing in here compares "
                "Perseus to a named product, because nothing has been benchmarked against one.",
                FOOT, True)
    _tb(s, 0.85, 4.58, 11.6, 0.30, "WHY THIS DECK LOOKS LIKE THIS", 10.5, CYAN, MONO, True)
    _tb(s, 0.85, 4.88, 11.6, 0.72,
        "The research pass found more invented MDR prices than real ones. So the discipline is "
        "the product here too: a price is quoted only where the vendor published it, a silence is "
        "reported as a silence, and the slide that says where we lose comes before the slide that "
        "says where we win.", 11.5, BODY, TEXT)
    for i, (v, lab, col) in enumerate([
            (str(N_VENDOR_PUB), "competitor prices\npublished by the vendor", CYAN),
            (str(N_NO_PRICE), "named vendors publishing\nno price at all", AMBER),
            (RAPID7_FLOOR, "asset floor on the cheapest\nlisted MDR rate card", VIOLET),
            (OUR_LIST, "our SHIELD list, published\nwith the whole rate card", GREEN)]):
        stat(s, 0.85 + i * 2.95, 5.85, 2.7, v, lab, col, vsize=26)

    # ------------------------------------------------------------------ 02. who is not a rival
    s = d.slide("FIRST, THE HONEST PART", "ENDPOINT WORK IS NOT", " OUR WORK.",
                "Three fields get named in the same sentence as this product. Only one of them is "
                "a field we are actually in.")
    for i, (k, kc, h, b) in enumerate([
            ("NOT A COMPETITOR", RED, "ENDPOINT\nDETECTION",
             "CrowdStrike, SentinelOne, Microsoft Defender. An agent on every laptop and server, "
             "priced per device: CrowdStrike from $7.99 a device a month, SentinelOne from $69.99 "
             "an endpoint a year, Defender for Business at $3.00 a user. We install nothing on an "
             "endpoint and inspect nothing below HTTP. A buyer choosing between those two is not "
             "choosing between either of them and us."),
            ("ADJACENT", AMBER, "MDR\nSERVICES",
             "Arctic Wolf, Rapid7, Expel, eSentire, Sophos. These overlap on the outcome, because "
             "somebody watches and somebody responds. They do not overlap on the unit, which is "
             "headcount, or on the deployment, which is agents plus log shipping to a vendor SOC. "
             "In a real deal this is where we are compared, and most of the time honestly losing "
             "it is the right answer."),
            ("THE FIELD WE ARE IN", CYAN, "HTTP CLIENT BEHAVIOUR,\nAND AI SOC TRIAGE",
             "Two things sit opposite us. Client-behaviour defence at the HTTP layer, where "
             "Cloudflare Bot Management and Fastly publish nothing. And the AI SOC triage "
             "startups: AirMDR at $4 an investigation, Prophet at $10, Simbian at $10 an alert, "
             "plus Dropzone AI, Torq, Conifers, Exaforce and StrikeReady. They triage alerts "
             "somebody else raised. We raise them and act on them."),
    ]):
        card(s, X3[i], 1.95, W3, 3.55, k, kc, h, b, bsize=9.2)
    _rect(s, 0.55, 5.70, 12.23, 1.20, fill=PANEL, line=LINE)
    _tb(s, 0.80, 5.86, 11.73, 0.95,
        "THE TEST FOR WHETHER SOMEBODY IS A COMPETITOR is not whether the buyer mentions them in "
        "the same meeting. It is whether the two products answer the same question with the same "
        "unit of sale. An agent on a laptop priced per device and a control in front of an "
        "application priced per application do not, however similar the marketing reads. Saying "
        "that out loud early is what makes the rest of the deck worth reading.",
        10.5, WHITE, TEXT, space=1.22)

    # ------------------------------------------------------------------ 03. the silence
    s = d.slide("DISCLOSURE", "MOST OF THE FIELD", " PUBLISHES NOTHING.",
                "A statement about what is on a public page. It is not a claim about quality, and "
                "it does not need to be.")
    _tb(s, X2[0], 1.92, W2, 0.28, "QUOTE ONLY. NO PUBLIC RATE, CHECKED 17 SEPTEMBER 2026",
        9.5, CYAN, MONO, True)
    bullets(s, X2[0], 2.28, W2, [
        "Arctic Wolf · Rapid7 · Expel · eSentire · Sophos MDR",
        "CrowdStrike Falcon Complete · SentinelOne Vigilance · Microsoft Defender Experts",
        "Red Canary, whose pricing page now redirects to a contact form",
        "Splunk: Cloud, Enterprise and Enterprise Security are all quote only, and the workload "
        "calculator outputs a unit count and never a currency figure",
        "Imperva: no pricing page exists at all and /pricing/ is a hard 404",
        "Cloudflare Bot Management · Fastly Next-Gen WAF and Bot Management",
        "Dropzone AI · Torq · Intezer",
    ], gap=0.48, size=10, dot=AMBER)
    _rect(s, X2[1], 1.92, W2, 2.30, fill=INK, line=LINE)
    _tb(s, X2[1] + 0.26, 2.12, W2 - 0.52, 0.28, "AND THERE IS NO ANALYST BENCHMARK EITHER",
        9.5, RED, MONO, True)
    _tb(s, X2[1] + 0.26, 2.48, W2 - 0.52, 1.60,
        "There is no analyst-grade public per-endpoint benchmark. Gartner's Market Guide for MDR "
        "is paywalled and vendor gated and publishes no price band publicly. The ranges that "
        "circulate in sales conversations as \"Gartner says\" trace back to content farms: "
        "mdrcost.com, mdrproviders.io, zerometric.net, costbench.com, comparedge.com, edrcost.com "
        "and several more. Each figure on those sites was checked against the vendor's own pages "
        "and found absent. Do not repeat one, even once, even casually.",
        9.5, BODY, TEXT, space=1.24)
    _rect(s, X2[1], 4.34, W2, 1.42, fill=INK, line=LINE)
    _tb(s, X2[1] + 0.26, 4.54, W2 - 0.52, 0.28, "THE TWO RANGES THAT ARE CITABLE",
        9.5, CYAN, MONO, True)
    _tb(s, X2[1] + 0.26, 4.90, W2 - 0.52, 0.76,
        "Both are vendor statements and must be attributed as vendor statements. Huntress "
        "publishes $2.99 to $184 per endpoint per month for EDR core licensing on its own pricing "
        "page. Expel's glossary offers $10 to $30 per device per month as market commentary.",
        9.5, BODY, TEXT, space=1.24)
    _rect(s, 0.55, 5.94, 12.23, 0.96, fill=PANEL, line=LINE)
    _tb(s, 0.80, 6.10, 11.73, 0.70,
        "THE LINE TO USE IN THE ROOM: ours is on a published price list and most of theirs is not. "
        "That is a fact about disclosure, checkable by the buyer in a browser while you are still "
        "in the meeting. It is not a claim that we are better, and it must not be delivered as "
        "one, because the moment it is, it stops being checkable.",
        10.5, WHITE, TEXT, space=1.22)

    # ------------------------------------------------------------------ 04. what they charge
    s = d.slide("PRICE, WITH SOURCE CLASS", "WHAT THE CATEGORY", " CHARGES.",
                "Verified 17 September 2026. Every row carries its source class, because the "
                "class decides what may be said out loud.")
    # ELEVEN ROWS, AND THE ROW COUNT IS THE CONSTRAINT. The first render carried thirteen at a
    # 0.34in step and the note panel at y=6.00 printed straight through the last two rows, which
    # is the fixed-row-height arithmetic defect this repository keeps paying for: 1.88 header plus
    # 0.40 plus 13 x 0.34 ends at 6.70, not at 6.00. Eleven rows at 0.36 end at 6.24 and the panel
    # starts at 6.30. The two rows that came out (Field Effect, Microsoft Sentinel) are in the note
    # instead, so no evidence was dropped to make the arithmetic work.
    VP, ML = ("vendor published", GREEN), ("marketplace list", AMBER)
    rows = [
        ("Blumira", "$12 / $16 / $21", "per employee a month. Detect / Respond / Automate", VP),
        ("CrowdStrike", "$7.99 / $14.99 / $19.99", "per device a month. Go caps at 100 devices", VP),
        ("SentinelOne", "$69.99 to $229.99", "per endpoint a year, scoped to 5 to 100 seats", VP),
        ("Defender for Business", "$3.00", "per user a month, with a 300-user ceiling", VP),
        ("Cloudflare", "$20 Pro, $200 Business", "per domain a month. The only per-domain rate found", VP),
        ("AWS WAF", "$430 a month", "AWS's own example: 3 ACLs, 21 rules, 35M requests", VP),
        ("AirMDR", "$4.00", "per investigation. The only AI SOC vendor with a rate", VP),
        ("Rapid7 MDR Essential", "$20.28", "per asset a month, from $73,000 a year at 300 assets", ML),
        ("Arctic Wolf MDR Basic", "$36.67", "per user a month, from $44,000 a year up to 100 users", ML),
        ("Prophet Security", "$10.00", "per investigation, from $50,000 a year for 5,000", ML),
        ("Simbian", "$10.00", "per alert, from $10,000 a year per 1,000 alerts", ML),
    ]
    table(s, 0.55, 1.88, 12.23,
          ["Vendor", "Published rate", "Unit, as the vendor states it", "Source class"],
          rows, [0.19, 0.20, 0.43, 0.18], rh=0.36)
    _rect(s, 0.55, 6.16, 12.23, 0.74, fill=PANEL, line=LINE)
    _tb(s, 0.80, 6.28, 11.73, 0.56,
        "VENDOR PUBLISHED is the vendor's own site. MARKETPLACE LIST is a vendor-authored rate "
        "card on AWS or Azure Marketplace, better evidence than any aggregated estimate and still "
        "not a published price. Two more from vendor pages: Field Effect $5 to $25 per user a "
        "month, which states it never charges by device, and Microsoft Sentinel $4.30 to $5.59 per "
        "GB ingested, which the buyer already pays. Ours: SENTRY €450, SHIELD €1,200, CITADEL "
        "€2,900 a month, €90 an extra application, €8 an investigation, free 30-day pilot.",
        9.6, WHITE, TEXT, space=1.16)

    # ------------------------------------------------------------------ 05. the minimum size
    s = d.slide("THE MINIMUM-SIZE FINDING", "PRICED BY HEADCOUNT,", " AND IT SHOWS.",
                "Our buyer is 50 to 500 seats. Several of the best-known names cannot sell to the "
                "bottom of that range at a published rate.")
    rows = [
        ("Rapid7", "Cheapest transactable SKU starts at 300 assets and $73,000 a year. The two "
                   "tiers above it start at 500",
         ("50 to 150 seats cannot buy the listed rate card at all", RED)),
        ("Arctic Wolf", "The only public rate caps at 100 users",
         ("100 to 500 seats has no public rate whatsoever", RED)),
        ("Defender for Business", "A 300-user ceiling, which is a ceiling and not a floor",
         ("300 to 500 seats is pushed to the $12 SKU, four times the unit price", AMBER)),
        ("SentinelOne", "The list rate is footnoted as being for 5 to 100 workstations",
         ("Above 100 workstations is quoted off list", AMBER)),
        ("Huntress", "A 50-agent minimum",
         ("Fits, at the floor", GREEN)),
    ]
    table(s, 0.55, 1.95, 12.23, ["Vendor", "The barrier, as published", "Effect at 50 to 500 seats"],
          rows, [0.18, 0.44, 0.38], rh=0.62)
    _rect(s, 0.55, 5.35, 12.23, 1.55, fill=PANEL, line=LINE)
    _tb(s, 0.80, 5.52, 11.73, 0.28, "STATE IT AS A CATEGORY FACT, NOT AS A HIT ON ONE VENDOR",
        9.5, CYAN, MONO, True)
    _tb(s, 0.80, 5.88, 11.73, 0.92,
        "The MDR category is structured around headcount, and its published rate cards thin out "
        "badly below a few hundred seats. That is a description of how the category prices "
        "itself, and each vendor above says so on its own page. Perseus is priced per protected "
        "application, so the same list price applies at 40 seats and at 4,000. At 100 people "
        "SHIELD is €12 a head a month; at 500 people the same €1,200 is €2.40 a head. Say why "
        "rather than claiming a win: the price does not follow headcount because the product does "
        "not touch headcount, and it is not doing the endpoint work those products do.",
        10, WHITE, TEXT, space=1.20)

    # ------------------------------------------------------------------ 06. architecture
    s = d.slide("CATEGORIES, NOT PRODUCTS", "COMPARED ON ARCHITECTURE,", " NOT CLAIMS.",
                "What each category is structurally for. No product is named and no product has "
                "been benchmarked.")
    rows = [
        ("Unit of judgement", "The single request", "Traffic volume", "The endpoint and its logs",
         "An alert somebody else raised", ("The client, over time", CYAN)),
        ("Decision latency", "Inline, per request", "Seconds, inline", "Minutes to hours, human",
         "Minutes, into a queue", ("Enforcement inline, review on a 10 minute loop", CYAN)),
        ("Where it runs", "Edge or vendor cloud", "Vendor scrubbing centre", "Vendor SOC, plus agents",
         "Vendor SaaS", ("The customer's own infrastructure", CYAN)),
        ("Who tunes it", "You, or the vendor on a release cycle", "The vendor",
         "Vendor analysts", "The vendor's model",
         ("A daily loop and a weekly re-vet, gated by code", CYAN)),
        ("Escalation to a human", "An alert", "A status page", "An analyst. That is the product",
         "A queue for your analyst", ("Telegram, only when the action has reach or cost", CYAN)),
        ("Does data leave the estate", "Yes", "Yes", "Yes, logs and telemetry", "Yes",
         ("No", GREEN)),
        ("Agent on an endpoint", "No", "No", "Normally yes", "No, it reads your SIEM",
         ("No", GREEN)),
    ]
    table(s, 0.55, 1.88, 12.23,
          ["Dimension", "WAF", "DDoS scrubbing", "MDR service", "AI SOC triage", "PERSEUS"],
          rows, [0.20, 0.15, 0.16, 0.16, 0.16, 0.17], size=8.0, rh=0.54)
    _rect(s, 0.55, 5.98, 12.23, 0.92, fill=PANEL, line=LINE)
    _tb(s, 0.80, 6.12, 11.73, 0.70,
        "READ THIS ALOUD WITH THE TABLE. We have benchmarked Perseus against no named product, so "
        "this compares what each category is structurally for. Every cell is checkable against "
        "the vendors' own documentation, and none of it can be refuted by a competitor's next "
        "release. Nothing here says Perseus is better, faster or more accurate than anything. "
        "Under UWG s.6 and the UCP Directive a comparative claim has to be substantiated, and "
        "ours is not, so we do not make one.",
        10, WHITE, TEXT, space=1.20)

    # ------------------------------------------------------------------ 07. where we are better
    s = d.slide("STRUCTURAL, AND MEASURED", "WHERE WE ARE", " BETTER.",
                "Only things that are true by construction or were measured on a dated run. No "
                "item on this slide is a comparison to a named product.")
    bullets(s, X2[0], 1.92, W2, [
        "PRICED PER APPLICATION, NOT PER HEAD. SENTRY €450, SHIELD €1,200, CITADEL €2,900 a "
        "month. The same list price applies at 40 seats and at 4,000, which is why it can be "
        "bought at 50 seats at all.",
        "IT RUNS ON THE CUSTOMER'S OWN INFRASTRUCTURE. No log shipping, no telemetry export, "
        "nothing leaves the estate to be judged somewhere else.",
        "NO AGENT AND NO MAINTENANCE WINDOW. One file copied in and one middleware line, wrapped "
        "so that a failure prints PERSEUS SIDECAR NOT WIRED rather than failing the boot. The "
        "sidecar is standard library only, so no new dependency enters the application.",
        "THE PROMOTION GATE REFUSES ON ONE CLEAN HIT. A rule needs 24 hours in detection, 3 of 4 "
        "reviewers agreeing, at least one confirmed hostile match, and exactly zero matches "
        "against traffic we really serve. On 13 September 2026 a candidate with 79 hostile hits "
        "and 134 hits from real visitors was refused outright.",
    ], gap=0.50, size=9.8)
    bullets(s, X2[1], 1.92, W2, [
        "FOUR MODELS FROM FOUR VENDORS, so a rate limit or an outage is not a shared failure "
        "domain. On 13 September 2026 the panel answered 0 of 4 times and nothing broke, because "
        "the models advise and the code decides.",
        "THE PRICE LIST IS PUBLISHED IN FULL, including onboarding, the per-investigation rate, "
        "the hourly review rate and the partner discount ladder at 10 / 20 / 30 / 40 per cent.",
        "A FREE 30-DAY DETECTION-ONLY PILOT. Enforcement is never switched on during it, so there "
        "is nothing to reverse, and the customer watches it be wrong before trusting it to be "
        "right.",
        "IT DEMOTES ITS OWN RULES. The weekly re-vet on 13 September 2026 retired five, one of "
        "which had come to match 99 paths our own build output serves. Left alone it would have "
        "broken the site while every dashboard stayed green.",
    ], gap=0.50, size=9.8)
    _rect(s, 0.55, 5.66, 12.23, 1.24, fill=PANEL, line=LINE)
    _tb(s, 0.80, 5.82, 11.73, 0.98,
        "WHY THE LIST IS SHORT AND SPECIFIC. Every line above is either a property of how the "
        "thing is built, which a buyer can verify by reading the deployment, or a number from a "
        "dated run that we can produce. There is no line here of the form \"faster than\" or "
        "\"more accurate than\", because we have run no comparison that would support one. A "
        "buyer who finds one unsupported claim on this slide is right to discount the other seven, "
        "and on a security product that is the correct instinct.",
        10, WHITE, TEXT, space=1.20)

    # ------------------------------------------------------------------ 08. where we are worse
    s = d.slide("SIX GAPS A BUYER WILL FIND", "WHERE WE ARE", " WORSE.",
                "If this slide were missing, nothing else in the deck would be believable. Every "
                "item is in the open-items register and dated.")
    gaps = [
        ("01", RED, "NO SLA\nTARGETS",
         "The existing SLA was written for the assessment engine, where the measurable thing is "
         "run completion time. Perseus needs its own: blocklist freshness, loop completion, alert "
         "latency, time to reverse an action. Until those are agreed, quote no availability "
         "figure for Perseus anywhere."),
        ("02", RED, "NO ISO 27001,\nNO SOC 2",
         "No independent assurance of any kind, and one hosting region. A regulated buyer asks "
         "for all three inside the first hour. The honest answer is that it is on the roadmap and "
         "it is not done."),
        ("03", AMBER, "NO REFERENCE\nCUSTOMER",
         "None for this product. Not one. The free 30-day pilot in the price list exists precisely "
         "because of that, and it is the only thing that closes this gap."),
        ("04", AMBER, "A SHORT ENFORCEMENT\nRECORD",
         "Perseus has been enforcing on our own estate and not on a customer's, and the gate is "
         "strict enough that very few rules promote. Two blocking rules, seven in detection, none "
         "ready, as at 13 September 2026. Describe the gate as the product and do not imply a "
         "production record we lack."),
        ("05", RED, "HTTP\nLAYER ONLY",
         "It sees nothing on an endpoint, nothing in email, nothing in identity, and nothing below "
         "HTTP. That is most of what an MDR service covers. It adds to the controls a customer "
         "already owns and replaces none of them, and a buyer who wants one throat to choke across "
         "all four surfaces is not buying this."),
        ("06", AMBER, "NO 24/7\nANALYST DESK",
         "There is no staffed human desk behind it. Alerts reach a named person on Telegram with "
         "action buttons, and an engineer is bookable at €200 an hour, which is a different "
         "product from a rota of analysts covering nights and weekends."),
    ]
    # 2.48in cards on rows at 1.88 and 4.42. The body box is h minus 1.15 minus the 0.24in a
    # two-line head costs, so 1.09in, which at 8.8pt and this width is six lines. Every body above
    # was cut to five. The second row ends at 6.90 against the footer rule at 7.04.
    for i, (k, kc, h, b) in enumerate(gaps):
        card(s, X3[i % 3], 1.88 if i < 3 else 4.42, W3, 2.48, k, kc, h, b, bsize=8.8)

    # ------------------------------------------------------------------ 09. the actual difference
    s = d.slide("THE ACTUAL DIFFERENCE", "A SERVICE,", " OR A CONTROL.",
                "Not a feature argument. The two things are bought by different people, priced on "
                "different units, and succeed at different events.")
    card(s, X2[0], 1.92, W2, 2.05, "THEM", AMBER, "A SERVICE, SOLD TO\nA SECURITY FUNCTION",
         "The unit of sale is headcount, so the price follows the size of the company. The buyer "
         "is staffing a function they do not have. Success looks like an analyst reading a queue "
         "and answering it faster than last quarter.", bsize=9.6)
    card(s, X2[1], 1.92, W2, 2.05, "US", CYAN, "A CONTROL, INSTALLED IN\nFRONT OF AN APPLICATION",
         "The unit of sale is the application, so the price follows how many are exposed. It "
         "decides for itself inside bounds committed in code, and asks a named human only when "
         "the action has reach or cost.", bsize=9.6)
    _tb(s, 0.55, 4.14, 12.23, 0.28, "AND THE MECHANISM: FOUR MODELS, FOUR VENDORS, NO SHARED "
        "FAILURE DOMAIN", 9.5, CYAN, MONO, True)
    _rect(s, 0.55, 4.46, 12.23, 0.74, fill=INK, line=LINE)
    for i, (m, v) in enumerate([("deepseek-3.2", "DeepSeek"), ("llama-4-maverick", "Meta"),
                                ("gemma-4-31B-it", "Google"), ("kimi-k2.6", "Moonshot")]):
        _tb(s, X4[i] + 0.26, 4.58, W4 - 0.30, 0.26, m, 11, WHITE, MONO, True)
        _tb(s, X4[i] + 0.26, 4.86, W4 - 0.30, 0.24, v.upper(), 8.4, MUTED, MONO)
    _rect(s, 0.55, 5.34, 12.23, 1.56, fill=PANEL, line=LINE)
    _tb(s, 0.80, 5.50, 11.73, 1.26,
        "MODELS PROPOSE, CODE DECIDES. The panel may propose detection patterns and values for six "
        "integers inside committed bounds. It may not block or unblock an address, change those "
        "bounds, touch the blast cap, the allow-list or the kill switch, and no model call ever "
        "sits in the request path. A rate limit or an outage is provider-wide, so a four-model "
        "panel on one vendor is four hats on one head, and a model that is simply wrong is "
        "contradicted by three others rather than believed. The proof is the boring run: on 13 "
        "September 2026 the panel answered 0 of 4 times because vendors were down or rate limited, "
        "and the control kept working. A security control that stops working when a language model "
        "is unavailable is a single point of failure with a friendly personality.",
        10, WHITE, TEXT, space=1.18)

    # ------------------------------------------------------------------ 10. who wins which deal
    s = d.slide("QUALIFICATION", "PICK THE FIGHT", " YOU WIN.",
                "Told honestly this is a qualification tool and not a comparison chart. Two of the "
                "seven rows are ours to walk away from.")
    rows = [
        ("\"I need somebody watching my endpoints 24/7\"", ("MDR", AMBER),
         "Agents, a staffed desk and out-of-hours cover. We have none of the three."),
        ("\"I need a SOC team I do not have\"", ("MDR", AMBER),
         "They are selling people and we are selling a control. Do not argue with this one."),
        ("\"Something is hammering my web application and my WAF is not stopping it\"",
         ("PERSEUS", GREEN),
         "Client behaviour over time at the HTTP layer is exactly what this judges."),
        ("\"I have 60 staff and nobody will quote me\"", ("PERSEUS", GREEN),
         "The published rate cards thin out below a few hundred seats. Ours does not move with "
         "headcount at all."),
        ("\"I need defences that change faster than quarterly\"", ("PERSEUS", GREEN),
         "A 10 minute watch loop, a daily cycle at 04:40 and a weekly re-vet, all gated by code "
         "that demotes its own rules."),
        ("\"I need a signed attestation my regulator accepts\"", ("A BIG 4 FIRM", RED),
         "No ISO 27001, no SOC 2, one region. Partner on it or walk away, but do not promise it."),
        ("\"I need to score 4,000 suppliers\"", ("NOT OUR MARKET", RED),
         "That is third-party risk scoring. Different product, different buyer, and we do not "
         "have it."),
    ]
    table(s, 0.55, 1.95, 12.23,
          ["What the buyer actually says", "Who wins", "Why, in one line"],
          rows, [0.38, 0.15, 0.47], rh=0.52)
    _rect(s, 0.55, 5.90, 12.23, 1.00, fill=PANEL, line=LINE)
    _tb(s, 0.80, 6.06, 11.73, 0.76,
        "HOW TO USE THIS IN THE FIRST CALL. Ask what the buyer is trying to stop happening, then "
        "read the left column back to them. Conceding the first two rows inside five minutes is "
        "what buys the credibility to be believed on the middle three, and the last two are worth "
        "more as a referral to somebody who can do them than as a proposal we cannot deliver.",
        10, WHITE, TEXT, space=1.20)

    # ------------------------------------------------------------------ 11. the four builds
    s = d.slide("ROADMAP, BY GROUND BOUGHT", "FOUR BUILDS THAT", " CHANGE THE ANSWER.",
                "Ordered by how much competitive ground each one actually buys, which is not the "
                "same as ordered by effort.")
    for i, (k, kc, h, b) in enumerate([
            ("01 · FIRST", CYAN, "PERSEUS SLA\nTARGETS",
             "Blocklist publication freshness, loop completion, incident alert latency, and the "
             "time to reverse an enforcement action. First because it is the cheapest of the four "
             "and unblocks the most: no availability figure can be quoted until these exist."),
            ("02", VIOLET, "A GRAFANA BOARD\nFOR THE EVENTS",
             "Every decision is already a structured event in Loki and is queryable today, and the "
             "existing boards cover the web app and the assessment engine. A Perseus board is not "
             "built, so it is described as roadmap in every document, including this one."),
            ("03", INDIGO, "INDEPENDENT\nASSURANCE",
             "ISO 27001 or SOC 2, and a second hosting region. The longest build of the four and "
             "the one that opens the regulated segment, which is where the budgets are. Today the "
             "answer to all three questions is no, and a regulated buyer asks all three."),
            ("04", GREEN, "A FIRST REFERENCE\nCUSTOMER",
             "Out of the free 30-day detection-only pilot. This one cannot be built, only earned, "
             "which is why the pilot is free and why it runs detection only: a customer who has "
             "watched it be wrong is the only person who can say it works."),
    ]):
        card(s, X4[i], 1.92, W4, 2.65, k, kc, h, b, bsize=8.8)
    _rect(s, 0.55, 4.76, 12.23, 2.14, fill=PANEL, line=LINE)
    _tb(s, 0.80, 4.94, 11.73, 0.28, "WHAT CHANGES WHEN EACH ONE LANDS", 9.5, CYAN, MONO, True)
    bullets(s, 0.80, 5.28, 11.73, [
        "SLA targets turn \"we cannot give you a number\" into a number, which is the single "
        "sentence that currently ends serious conversations early.",
        "The Grafana board removes the only place in the product where the honest description is "
        "weaker than the thing itself: the events are all there and today nobody can see them on "
        "a board.",
        "Independent assurance and a second region move us from \"interesting\" to \"procurable\" "
        "for a regulated buyer, and nothing else on this list does that.",
        "One reference customer answers the question no architecture slide can answer, and it is "
        "the only item here whose delivery date is not ours to set.",
    ], gap=0.40, size=9.6, dot=VIOLET)

    assert_layout(d)
    return d.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(
        os.path.expanduser("~"), "Downloads", "cybergod partnership", "aisoc_pack",
        "05_Perseus_AI_SOC_Competitive_Analysis_EN.pptx"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    p = build(a.template, a.out)
    print("built: %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
