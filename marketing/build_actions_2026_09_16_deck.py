#!/usr/bin/env python3
"""build_actions_2026_09_16_deck.py — the internal action tracker from the call of 16 Sept 2026.

    python marketing/build_actions_2026_09_16_deck.py [--out PATH] [--template PATH]

WHAT THIS IS
    Ten slides recording what Assad Kondakji, Dima Diall and Jev (Evgeny Vainshtein) decided in a
    260 minute call on 16 September 2026, what has already been delivered in the two days since,
    and what each of the three is now carrying. It is INTERNAL. It is not a customer deck, it is
    not a partner deck, and the footer says so on every page.

    It reuses build_consensus_deck.py's Deck/card/bullets/stat helpers and deck_chrome.py's
    guards, so the S4biz template exists in exactly ONE implementation and this deck cannot drift
    away from the commercial pack it reports on. Same reason build_aisoc_commercial_deck.py and
    build_perseus_shield_deck.py do it.

THE RULE THIS DECK EXISTS TO OBEY: DO NOT INVENT A DATE
    A tracker whose dates were guessed is worse than no tracker, because the guesses get quoted
    back in the next call as commitments somebody made. The call set almost no deadlines. Exactly
    three timings were actually said and only those three appear anywhere in this build:

        17 September 2026   the AI SOC documentation pack was built (Jev, "in the same manner as
                            the cybergod.ai documents"), and the investor deck was started the
                            same day, which in the call was "tomorrow"
        from end September  corporate budget planning starts now and finalises end September
        into November       through October and November. That is the window slide 9 describes.

    Every other cell in the WHEN column reads "To set", "Next" or "Ongoing". `TO_SET` is a module
    constant so that a future edit adding a real date has to change one place and has to mean it.
    There is no fourth date in this file. Grep it.

THE SECOND RULE: SLIDE 3 IS A DELIVERY, NOT A PLAN
    In the call Jev said the automated SOC had a presentation and a competitive analysis and
    nothing else, and undertook to build the rest. That is done, and the deck has to READ as done,
    because the whole point of showing it is that the largest open item from the call closed
    before the deck was written. Slide 3 therefore carries a GREEN completion bar above the table,
    GREEN in the document column, and the word COMPLETE at the top. Colour carries status
    throughout: GREEN done, AMBER in progress, CYAN or VIOLET not started, RED only for something
    that blocks other work (exactly one cell, the contract signature on slide 8).

THE THIRD RULE: NO COMPETITOR IS NAMED AND NO COMPETITOR PRICE IS QUOTED
    Slide 4 publishes our own SOC price list and says the rates were benchmarked, with the
    reasoning in document 06. Document 06 is internal and stays internal. Naming a competitor and
    a number on a slide that circulates is how an unsubstantiated comparative claim leaves the
    building (UWG s.6 / UCP Directive), and this deck has no benchmark of its own to stand on.

AND THE HOUSE RULES
    No em dashes and no en dashes anywhere in slide text. No delve, leverage, robust, seamless,
    landscape, testament, underscore, pivotal. No closing aphorism: slide 10 ends on where the
    next contact happens and what the group is waiting to see, which is a fact and not a line.

The 40 character title cap is measured on THIS TEMPLATE'S render at 30pt Arial Black, not
inherited from deck_chrome's 50: see _check_title.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  - one template implementation, reused
    AMBER, BODY, CYAN, Deck, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from deck_chrome import W2, W3, W4, X2, X3, X4, assert_layout, guarded  # noqa: E402

FOOT = "S4BIZ GROUP · ACTIONS FROM THE CALL OF 16 SEPTEMBER 2026 · INTERNAL"

X, W = 0.55, 12.23        # left margin and content width, same as deck_chrome's column geometry
TITLE_MAX = 40

# ---- the only three timings the call actually produced ---------------------------------------
D_BUILT = "17 September"          # the AI SOC pack, and the investor deck started the same day
TO_SET = "To set"                 # everything else. Not a placeholder: it is the accurate answer.

# ---- the SOC price list, as it now stands in document 06 -------------------------------------
P_SENTRY, P_SHIELD, P_CITADEL = "EUR 450 a month", "EUR 1,200 a month", "EUR 2,900 a month"
TIER_LADDER = "Partner 10 percent. VAR 20 percent. Gold 30 percent. Platinum 40 percent."


def _check_title(title, tail):
    """A fixed height title row is arithmetic, not taste.

    deck_chrome.check_title caps at 50, the figure the consensus decks measured on their own
    longest titles. build_perseus_shield_deck.py re-measured it on this template at 30pt Arial
    Black and found 40 fits on one line while 49 wraps onto the sub-heading at y=1.55. This deck
    takes the same lower bound, because Arial Black glyph widths vary enough (W and M against I
    and T) that a character count is only ever a proxy.
    """
    if not isinstance(title, str):
        return
    n = len(title) + len(tail or "")
    if n > TITLE_MAX:
        raise SystemExit("[X] title row is %d chars, cap is %d: %r"
                         % (n, TITLE_MAX, title + (tail or "")))


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


def panel(s, x, y, w, h, kicker, text, size=10.5, kcol=CYAN, tcol=BODY):
    """A titled panel. The kicker is the label, the text is the argument."""
    _rect(s, x, y, w, h, fill=PANEL, line=LINE)
    _tb(s, x + 0.25, y + 0.14, w - 0.50, 0.28, kicker.upper(), 10, kcol, MONO, True)
    _tb(s, x + 0.25, y + 0.48, w - 0.50, h - 0.62, text, size, tcol, TEXT)


def build(template, out):
    d = guarded(Deck(template), tail=VIOLET)
    _orig = d.slide

    def slide(eyebrow, title, title_tail="", sub="", footer=None, hero=False):
        # The stricter 40 char cap runs BEFORE deck_chrome's 50, so the tighter rule is the one
        # that reports. Wrapping here rather than calling it at ten sites means a NEW slide
        # cannot forget it, which is the difference between a rule and a habit.
        if not hero:
            _check_title(title, title_tail)
        return _orig(eyebrow, title, title_tail, sub, FOOT if footer is None else footer, hero)
    d.slide = slide

    # ---------------------------------------------------------------- 1. hero
    s = d.slide("S4BIZ GROUP · ACTION TRACKER · 18 SEPTEMBER 2026",
                [("WHAT EACH OF US OWNS.", WHITE),
                 ("FROM THE CALL OF", WHITE),
                 ("16 SEPTEMBER.", VIOLET)],
                None, "", FOOT, True)
    _tb(s, X, 4.62, W, 0.30, "WHAT THIS IS", 10.5, CYAN, MONO, True)
    _tb(s, X, 4.92, W, 0.78,
        "Three people, 260 minutes, and the actions each of them took at the end of it. Assad "
        "Kondakji, Dima Diall and Jev. This is the internal tracker: what was decided, what has "
        "already been delivered since the call, what each owner is now carrying, and the five "
        "decisions none of them can close alone.",
        11.5, BODY, TEXT)
    for i, (v, lab, col) in enumerate([
            ("9", "documents delivered\nsince the call", GREEN),
            ("3", "owners, and every\naction has one", CYAN),
            ("3", "products in\nthe portfolio", VIOLET),
            ("1", "brand decision\nstill open", AMBER)]):
        stat(s, X + i * 3.06, 5.88, 2.90, v, lab, col)

    # ---------------------------------------------------------------- 2. where we landed
    s = d.slide("WHERE WE LANDED", "SEVEN THINGS WERE", " SETTLED.",
                "The decisions actually taken on the call, so the actions on the slides after "
                "this one have their context.")
    rows = [(("Pricing shape for cybergod.ai", WHITE),
             "A list price with partner discount tiers, and the subscription is the thing we sell."),
            (("The single run is not free", WHITE),
             "Five free runs during a partner pilot, then EUR 100 per report."),
            (("The report subscription", WHITE),
             "Priced per company, not per seat."),
            (("White label", WHITE),
             "A higher price, and a volume commitment with it."),
            (("Angola is a pilot", WHITE),
             "Not the destination. Standard pricing across the continent."),
            (("Three products in the portfolio", WHITE),
             "The assessment engine, the automated SOC, and a breach and attack simulation platform."),
            (("Meetings", WHITE),
             "Escalation only. Everything else runs in the Telegram group.")]
    table(s, X, 1.95, W, ["Decision", "What it means"], rows, [0.34, 0.66], rh=0.50)
    panel(s, X, 5.98, W, 0.86, "WHAT THE DECISIONS DO NOT INCLUDE",
          "Dates. The call set almost none, and none has been invented here. Where a timing was "
          "actually said it appears. Everywhere else this deck says to set.", 10.5, AMBER, WHITE)

    # ---------------------------------------------------------------- 3. the AI SOC pack, done
    s = d.slide("DONE SINCE THE CALL", "THE AI SOC PACK IS", " BUILT.",
                "In the call the automated SOC had a presentation and a competitive analysis and "
                "nothing else. The rest now exists.")
    _rect(s, X, 1.88, W, 0.46, fill=PANEL, line=LINE)
    _tb(s, X + 0.25, 1.98, W - 0.50, 0.28,
        "COMPLETE · NINE ARTIFACTS · BUILT 17 SEPTEMBER 2026 · NOTHING ON THIS SLIDE IS PENDING",
        10.5, GREEN, MONO, True)
    rows = [(("00 Pack guide", GREEN), "Internal and the partner's sales lead",
             "On partner onboarding"),
            (("01 Product sheet, two pages", GREEN), "Anyone, no NDA", "First contact"),
            (("02 Service description", GREEN), "A prospect evaluating", "After the first call"),
            (("03 White paper", GREEN), "CISO, security architect", "After the NDA"),
            (("04 Operations manual", GREEN), "Whoever runs it", "At pilot start"),
            (("05 Competitive analysis", GREEN), ("Internal and partner only", AMBER),
             "Partner enablement"),
            (("06 Pricing and rationale", GREEN), ("Internal and partner only", AMBER),
             "Before the commercial conversation"),
            (("07 Commercial presentation", GREEN), "Partner cut and customer cut",
             "The meeting")]
    table(s, X, 2.48, W, ["Document", "Audience", "When it goes out"],
          rows, [0.36, 0.34, 0.30], head_col=GREEN, rh=0.42)
    _tb(s, X, 6.34, W, 0.48,
        "The product is Perseus AI SOC. The pack was built from a single authoritative facts file, "
        "with the same converter and the same deck template as the cybergod.ai pack, so the two "
        "packs cannot drift apart. Two of the nine never go to a customer, and document 07 ships "
        "in a partner cut and a customer cut because the partner cut carries the discount ladder.",
        10, MUTED, TEXT)

    # ---------------------------------------------------------------- 4. the SOC price list
    s = d.slide("ALSO DONE", "THE SOC PRICE LIST", " EXISTS.",
                "Assad asked for pricing for the automated SOC on the call. This is it, and the "
                "reasoning behind every rate is document 06.")
    rows = [(("SENTRY", CYAN), "Detection only, up to 3 protected applications",
             (P_SENTRY, WHITE)),
            (("SHIELD", VIOLET), "Autonomous enforcement, up to 10 protected applications",
             (P_SHIELD, WHITE)),
            (("CITADEL", INDIGO),
             "Enforcement, integration with the controls already in place, and a named engineer, "
             "up to 25 applications", (P_CITADEL, WHITE)),
            (("PILOT", GREEN), "30 days, detection only, once per customer", ("Free", GREEN))]
    table(s, X, 1.95, W, ["Tier", "What it covers", "Price"], rows, [0.20, 0.54, 0.26], rh=0.50)
    panel(s, X, 4.50, W, 1.10, "PARTNER TIERS, UNCHANGED FROM THE CYBERGOD.AI CONTRACT",
          TIER_LADDER + " It is the same ladder that already governs the assessment engine, so a "
          "partner learns one discount structure and not two, and a partner selling both products "
          "quotes them off the same arithmetic.", 10.5, CYAN, WHITE)
    _tb(s, X, 5.75, W, 0.62,
        "The unit is the protected application and not the employee, so the same list price "
        "applies at 40 staff and at 4,000. The rates were benchmarked against published rates in "
        "the category, and that benchmark sits in document 06, which is internal and stays "
        "internal.", 10, MUTED, TEXT)

    # ---------------------------------------------------------------- 5. Jev
    s = d.slide("OWNER: JEV (EVGENY VAINSHTEIN)", "WHAT JEV OWNS", " NOW.",
                "Two of these closed the day after the call. The rest are open, and only one of "
                "them has a date.")
    rows = [("Build the missing AI SOC documentation, in the same manner as the cybergod.ai pack",
             ("DONE", GREEN), (D_BUILT, GREEN)),
            ("Define pricing for the automated SOC",
             ("DONE, in document 06", GREEN), (D_BUILT, GREEN)),
            ("Put all documents where Assad can reach them, for his checklist pass",
             ("OPEN", CYAN), ("Next", CYAN)),
            ("Decide the brand architecture across all three products and the public site",
             ("OPEN", VIOLET), (TO_SET, MUTED)),
            ("Build the BAS documentation and pricing, the third product",
             ("OPEN", VIOLET), (TO_SET, MUTED)),
            ("Investor deck", ("IN PROGRESS", AMBER), ("Started " + D_BUILT, AMBER)),
            ("Send Dima the analyst reference for the external attack surface category name",
             ("OPEN", CYAN), (TO_SET, MUTED)),
            ("Name the two pre-sales people who can run a demo",
             ("OPEN", CYAN), (TO_SET, MUTED)),
            ("Answer the questions coming back from Assad's checklist pass",
             ("OPEN", CYAN), ("Ongoing", CYAN))]
    table(s, X, 1.88, W, ["Action", "Status", "When"], rows, [0.60, 0.22, 0.18], rh=0.44)
    _tb(s, X, 6.34, W, 0.48,
        "On the brand: Assad's point is that a partner receives an NDA from a company and not from "
        "a product, and that a separate product brand makes the story harder to tell. He also "
        "found a fantasy game platform on a similar name. The question is whether all three "
        "products sit under the S4biz master brand and whether the public site is S4biz.",
        10, MUTED, TEXT)

    # ---------------------------------------------------------------- 6. Assad
    s = d.slide("OWNER: ASSAD KONDAKJI", "WHAT ASSAD OWNS", " NOW.",
                "The commercial and market side. Seven items, all open, and the call put a date on "
                "none of them.")
    bullets(s, X, 1.95, W, [
        "Produce the revised price list from the whiteboard, including that the report "
        "subscription is priced per company, then iterate on it with Jev",
        "Work the marketing and sales documents, and run Jev's documents against his own "
        "checklist to see what needs adjusting for this market",
        "Build the document repository and map each document to a stage of the sales pipeline, "
        "light through to deep, with the deep material released only after signature",
        "Build the revenue and business model for Angola specifically",
        "Settle the competitive positioning against the two providers already active in the "
        "region, as a flanking approach rather than a frontal replacement",
        "Trial the CRM himself on the free tier and report back",
        "Keep opening conversations, with material to follow up on"], dot=CYAN)
    panel(s, X, 5.75, W, 1.05, "STATUS ON ALL SEVEN: OPEN, AND NO DATE WAS SET",
          "The revised price list is the one Jev is waiting on, because the partner conversations "
          "are held until the cybergod.ai list is ratified. The checklist pass is what feeds "
          "Jev's own last action.", 10.5, AMBER, WHITE)

    # ---------------------------------------------------------------- 7. Dima
    s = d.slide("OWNER: DIMA DIALL", "WHAT DIMA OWNS", " NOW.",
                "Contract, pipeline and the investor conversation. Six items, all open, and the "
                "call put a date on none of them.")
    bullets(s, X, 1.95, W, [
        "Evaluate Pipedrive, specifically the automation, so that LinkedIn can drive lead "
        "generation and content can be produced out of it",
        "Send Jev the finalised NDA, backdated to the first meeting. It still needs Jev's company "
        "address and a few company details",
        "Draft the larger agreement in parallel with getting the NDA signed",
        "Continue with the lawyers already approached across Africa and the one in New York",
        "Set up pipeline management so that nothing falls through the cracks",
        "He is speaking to an investor contact, and the investor deck is the dependency"],
        dot=VIOLET)
    panel(s, X, 5.25, W, 1.10, "THE NDA IS THE FIRST GATE",
          "Every other conversation sits behind signature. The NDA needs Jev's company address and "
          "a few company details before it can go out, and the larger agreement is being drafted "
          "alongside it rather than after it.", 10.5, RED, WHITE)
    _tb(s, X, 6.45, W, 0.38,
        "The investor deck is where Dima and Jev meet: Jev started it on 17 September and Dima's "
        "investor contact is waiting on it. Neither of them named a date for the finished deck.",
        10, MUTED, TEXT)

    # ---------------------------------------------------------------- 8. open decisions
    s = d.slide("OPEN DECISIONS", "FIVE THINGS NOBODY", " OWNS ALONE.",
                "The things one person cannot close. Listed in the order they block other work.")
    rows = [("Brand architecture: one master brand, or product brands",
             ("Jev decides, Assad and Dima advise", VIOLET),
             "Every document, the NDA and the website depend on it"),
            ("A local entity or a local partner of record for Angola",
             ("All three", CYAN),
             "Companies there struggle to pay abroad, and it changes who invoices"),
            ("Ratify the cybergod.ai price list",
             ("Assad drafts, Jev approves", AMBER),
             "The partner conversations are waiting on it"),
            ("Pricing for the BAS product",
             ("Jev", VIOLET),
             "The third product cannot be sold without it"),
            ("NDA and partner contract signature",
             ("Dima drives", RED),
             "It is the first gate on every other conversation")]
    table(s, X, 1.95, W, ["Decision", "Who decides", "Why it is blocking"],
          rows, [0.34, 0.22, 0.44], rh=0.54)
    panel(s, X, 5.25, W, 1.15, "NONE OF THESE HAS A DATE EITHER",
          "The call did not set one. The brand decision is first because it is upstream of the "
          "documents that are already written and of the NDA that is already drafted, and every "
          "week it stays open is a week of material that may have to be reissued.", 10.5, AMBER,
          WHITE)
    _tb(s, X, 6.48, W, 0.36,
        "Colour on this slide carries the owner and the class of decision. Red marks the one item "
        "that gates every other conversation, not a failure by anybody.", 10, MUTED, TEXT)

    # ---------------------------------------------------------------- 9. the clock
    s = d.slide("THE CLOCK", "BUDGETS CLOSE", " IN NOVEMBER.",
                "Assad's framing of why the pace matters, and the only window in this deck with a "
                "shape to it.")
    for i, (k, kc, h, b) in enumerate([
            ("01", CYAN, "PLANNING HAS\nALREADY STARTED",
             "Corporate budget planning is running now, in the weeks around the call. That is the "
             "window everything in this deck is racing."),
            ("02", AMBER, "THEY FINALISE FROM\nEND SEPTEMBER",
             "Budgets finalise from the end of September, through October and November. After "
             "that the money for the year is allocated."),
            ("03", VIOLET, "2027 IS WHAT IS\nON THE TABLE",
             "For this to land in a 2027 budget the conversation has to be open before those "
             "budgets close. An open conversation is the ask here, not a signature.")]):
        card(s, X3[i], 2.05, W3, 2.40, k, kc, h, b, bsize=10)
    panel(s, X, 4.65, W, 1.05, "AND THE WEEK OF THE CALL WAS SHORT",
          "A public holiday took two days out of it. That is part of why the work moved into the "
          "Telegram group and the meetings were cut back to escalation only.", 10.5, CYAN, WHITE)
    _tb(s, X, 5.90, W, 0.62,
        "No deadline was set on the call for any action in this deck. The only dates in it are "
        "the two that were actually said: the AI SOC pack was built on 17 September, and the "
        "investor deck was started the same day.", 10, MUTED, TEXT)

    # ---------------------------------------------------------------- 10. how we work now
    s = d.slide("HOW WE WORK NOW", "TELEGRAM FIRST.", " MEETINGS LAST.",
                "The working agreement the call ended on, because the meetings themselves were "
                "slowing the work down.")
    for i, (k, kc, h, b) in enumerate([
            ("01", CYAN, "TELEGRAM IS THE\nDEFAULT CHANNEL",
             "Progress happens in the group. Documents, prices, questions and the answers to them "
             "all go there, and they go there as they happen."),
            ("02", AMBER, "MEETINGS ARE\nESCALATION ONLY",
             "A call gets made when something is not moving. It is not on a calendar and it is "
             "not a status round."),
            ("03", VIOLET, "BILATERAL FOR\nCONTENT AND MARKET",
             "Assad and Jev talk content and market questions between the two of them. All three "
             "meet only when it concerns the business."),
            ("04", GREEN, "OFFLINE WHEREVER\nIT CAN RUN OFFLINE",
             "Anything that does not need a call runs without one. The meetings were slowing the "
             "work, which is the reason this changed at all.")]):
        card(s, X2[i % 2], 1.92 + (i // 2) * 2.04, W2, 1.95, k, kc, h, b, bsize=10)
    # The closing panel has to clear the footer rule at 7.04 with room to spare, and its own text
    # box is h-0.62, so a panel shorter than about 0.80in has no line height left for its text.
    # That is why the card rows moved up by 0.03 and 0.06 rather than the panel being squeezed.
    panel(s, X, 6.03, W, 0.84, "NEXT CONTACT",
          "In the Telegram group, not in a scheduled call. What the group is waiting to see is the "
          "revised price list, the document repository and the signed NDA.", 10.5, CYAN, WHITE)

    assert_layout(d)
    return d.save(out)


DEFAULT_OUT = os.path.join(
    os.path.expanduser("~"), "Downloads", "cybergod partnership",
    "S4biz_Action_Items_2026-09-16.pptx")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args()
    if not os.path.exists(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    # The delivery folder may not exist on a fresh machine. Create it rather than failing the
    # whole render on a missing directory.
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    p = build(a.template, a.out)
    print("built: %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
