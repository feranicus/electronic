#!/usr/bin/env python3
"""build_aisoc_commercial_deck.py — PERSEUS AI SOC, the deck a partner presents to a customer.

    python marketing/build_aisoc_commercial_deck.py [--audience partner|customer]
                                                    [--out PATH] [--template PATH]

Document 07 of the AI SOC pack. It is the meeting deck: the partner opens it in front of the
customer, and the same sixteen slides are the partner's own enablement, which is why the price
list, the discount ladder and the partner arithmetic are in it. Its shape follows
`partner program Cybergodai.pptx`: what it is, the problem, how it works, the boundary, who buys,
the alternative, how you earn, the price list, the ladder, the economics, who you sign with.

WHY --audience EXISTS
    The footer used to say PARTNER AND CUSTOMER PRESENTATION and the deck was genuinely carried
    into both rooms, which is exactly the problem. Slide 15 is the partner's buy price, the gross
    margin per customer and what fifty of them come to in a month, and the price list closes with
    the discount ladder that produces those numbers. In front of the customer that is the partner
    telling the buyer what the partner makes on the deal, and the deck gave nobody a way to avoid
    it short of deleting slides by hand in the taxi. One build cannot be safe for both audiences,
    so there are two: `--audience partner` is the enablement deck, unchanged, everything in it,
    and `--audience customer` drops slide 15, drops the tier and discount block from slide 13,
    and says CUSTOMER PRESENTATION in the footer. Both builds run the same guards and the page
    numbers stay contiguous, because a deck with a hole at 15 announces what was taken out.

It reuses build_consensus_deck.py's Deck/card/bullets/stat helpers and deck_chrome.py's guards, so
the S4biz template exists in exactly ONE implementation and the decks cannot drift apart. Same
reason build_perseus_shield_deck.py does it.

FIVE RULES THIS DECK OBEYS
--------------------------
1. NO UNSUBSTANTIATED COMPARISON AGAINST A NAMED PRODUCT. Perseus has been benchmarked against
   nobody. Slide 3 therefore compares CATEGORIES on what each is architecturally FOR, and every
   layer of the customer's existing stack is described as real and necessary. An unsubstantiated
   superiority claim is comparative advertising under UWG s.6 and the UCP Directive, and on a
   security product it is also self-refuting.

2. NO COMPETITOR PRICES AT ALL. This deck is customer-facing. FACTS s.15 exists and stays in the
   internal competitive analysis, where a partner can read it before the meeting.

3. NO COST OF DELIVERY AND NO MARGIN PER INCIDENT. On the partner build, slide 15 states partner
   buy price against list price, because that is the partner's own commercial information, and it
   is the slide --audience customer removes for precisely that reason. Our model spend is FACTS
   s.14 "for the internal documents only" and is not in here on either build, for the same reason
   no vendor prints its bill of materials.

4. NO AVAILABILITY OR RESPONSE FIGURE, ANYWHERE. FACTS s.18.1: the SLA has no Perseus-specific
   targets yet. The price list and the closing slide SAY SO rather than leaving the gap for the
   customer to find. A number nobody measured is worse than an admitted gap on a deck whose whole
   argument is that every number in it was measured.

5. NO EM DASHES AND NO EN DASHES ANYWHERE. Standing rule for customer-facing copy.

EVERY NUMBER, TRACED TO FACTS.md
--------------------------------
    s.1   four group entities, the three tax IDs, EIN on file, Estonia / English, the contact
    s.3   three loops; every 10 min, 04:40 UTC, Sunday 05:20 UTC; 5 rules retired; /@fs/ 99 paths
    s.4   promotion gate: 24 h, quorum 3 of 4, >=1 hostile, 0 clean; 79 hostile v 134 clean;
          ruleset 2 blocking / 7 detecting / 0 ready
    s.6   deepseek-3.2 DeepSeek, llama-4-maverick Meta, gemma-4-31B-it Google, kimi-k2.6 Moonshot;
          panel answered 0 of 4; a model call is 300 ms to 60 s
    s.7   22 attack classes; six distinct missed paths before a source scores
    s.9   the boundary: 20% blast cap over a floor of 5, the statutes, the two switches
    s.10  the six reports and their channels; 900 s cooldown, 12 an hour, edge-triggered;
          no Perseus Grafana board yet, described as roadmap
    s.12  the four deployment shapes, start at C, what is provided and what is not required
    s.13  42,369 requests in 14 days, about 3,026 a day, 2,685 distinct paths not served,
          .env 14,897 / WordPress 6,336 / backups 4,867, one actor 551 paths and 143 user agents,
          0 blocked that fortnight
    s.14  SENTRY 450, SHIELD 1200, CITADEL 2900, extra application 90, extra investigation 8,
          onboarding 0 / 2500 / 6500, review 200/h, workshop 2500/day, pilot free;
          allowances 120 / 360 / 360; Partner 10 / VAR 20 / Gold 30 / Platinum 40
    s.18  the SLA gap, stated on slides 13 and 16

The 40-character title cap is measured on THIS TEMPLATE'S render, not inherited: see _check_title.
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

FOOT = "S4BIZ GROUP · CYBERGOD LLC · PERSEUS AI SOC · PARTNER AND CUSTOMER PRESENTATION"
FOOT_CUSTOMER = "S4BIZ GROUP · CYBERGOD LLC · PERSEUS AI SOC · CUSTOMER PRESENTATION"
AUDIENCES = ("partner", "customer")

X, W = 0.55, 12.23        # left margin and content width, same as deck_chrome's column geometry
TITLE_MAX = 40

# ---- the numbers, in one place, each carrying its FACTS.md section ---------------------------
N_CLASSES, N_VENDORS, N_LOOPS = 22, 4, 3                      # s.7, s.6, s.3
REQ_14D, REQ_DAY, PATHS_UNSERVED = "42,369", "3,026", "2,685"  # s.13
HUNT_ENV, HUNT_WP, HUNT_BAK = "14,897", "6,336", "4,867"      # s.13
ACTOR_PATHS, ACTOR_UAS = "551", "143"                          # s.13
GATE_HOSTILE, GATE_CLEAN = "79", "134"                         # s.4
RETIRED, FS_PATHS = "five", "99"                               # s.3
P_SENTRY, P_SHIELD, P_CITADEL = "€450", "€1,200", "€2,900"     # s.14
P_APP, P_INVEST, P_HOUR, P_DAY = "€90", "€8", "€200", "€2,500"  # s.14
ONB_SENTRY, ONB_SHIELD, ONB_CITADEL = "€0", "€2,500", "€6,500"  # s.14
PLATINUM_BUY, PLATINUM_MARGIN, FIFTY = "€720", "€480", "€24,000"  # s.14, arithmetic on list


def _check_title(title, tail):
    """A fixed-height title row is arithmetic, not taste.

    deck_chrome.check_title caps at 50, which is the figure the consensus decks measured on their
    own longest titles. build_perseus_shield_deck.py re-measured it on this template at 30pt Arial
    Black and found 40 fits on one line while 49 wraps onto the sub-heading at y=1.55. This deck
    takes the same lower bound, because Arial Black glyph widths vary enough (W and M against I and
    T) that a character count is only a proxy in the first place.
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


def build(template, out, audience="partner"):
    if audience not in AUDIENCES:
        raise SystemExit("[X] unknown audience %r, expected one of %s" % (audience, AUDIENCES))
    partner = audience == "partner"
    # The footer is the one piece of chrome that names the room the deck is in, so it is derived
    # from the audience once and every slide reads it from here. Two constants and a flag beats
    # sixteen call sites each passing the right string.
    foot = FOOT if partner else FOOT_CUSTOMER

    d = guarded(Deck(template), tail=VIOLET)
    _orig = d.slide

    def slide(eyebrow, title, title_tail="", sub="", footer=None, hero=False):
        # The stricter 40-char cap runs BEFORE deck_chrome's 50, so the tighter rule is the one
        # that reports. Wrapping here rather than calling it at 16 sites means a NEW slide cannot
        # forget it, which is the difference between a rule and a habit.
        if not hero:
            _check_title(title, title_tail)
        return _orig(eyebrow, title, title_tail, sub, foot if footer is None else footer, hero)
    d.slide = slide

    # ---------------------------------------------------------------- 1. hero
    s = d.slide("PERSEUS AI SOC",
                [("IT DECIDES FOR ITSELF.", WHITE),
                 ("AT THREE IN THE MORNING.", WHITE),
                 ("ON YOUR OWN INFRASTRUCTURE.", VIOLET)],
                None, "", foot, True)
    _tb(s, X, 4.62, W, 0.30, "WHAT THIS IS", 10.5, CYAN, MONO, True)
    _tb(s, X, 4.92, W, 0.78,
        "An automated security operations centre that runs on the customer's own infrastructure, "
        "decides for itself what to do about each attack, and revises its own defences every day "
        "and every week without a human in the loop. Four language models from four independent "
        "vendors review each incident and propose. Deterministic code decides every side effect.",
        11.5, BODY, TEXT)
    for i, (v, lab, col) in enumerate([
            (str(N_CLASSES), "attack classes\nrecognised by pattern", CYAN),
            (str(N_VENDORS), "models, one each from\nfour independent vendors", VIOLET),
            (str(N_LOOPS), "autonomous loops\nnobody sets an alarm for", INDIGO),
            ("0", "firewall changes\never made", GREEN)]):
        stat(s, X + i * 3.06, 5.88, 2.90, v, lab, col)

    # ---------------------------------------------------------------- 2. the problem
    s = d.slide("THE PROBLEM", "WE ARE NOT A TARGET.", " WE ARE AN ADDRESS.",
                "Fourteen days of attack-shaped traffic, measured on our own estate. Source: the "
                "attack digest of 13 September 2026.")
    for i, (v, lab, col) in enumerate([
            (REQ_14D, "attack-shaped requests\nin fourteen days", CYAN),
            (REQ_DAY, "a day, at companies\nnobody has heard of", VIOLET),
            (ACTOR_PATHS, "distinct paths\nfrom a single actor", INDIGO),
            (ACTOR_UAS, "browsers that one\nactor announced", AMBER)]):
        stat(s, X + i * 3.06, 1.95, 2.90, v, lab, col)
    rows = [(".env secrets", HUNT_ENV,
             "Application secrets in a file that should never be served. The most requested thing on the estate."),
            ("WordPress paths", HUNT_WP,
             "Asked for on sites that have never run WordPress. The scan does not check first."),
            ("Backup archives", HUNT_BAK,
             "A .zip or a .sql left beside the application is the whole database in one request.")]
    table(s, X, 3.30, W, ["What they hunted", "Requests", "What it tells you"],
          rows, [0.26, 0.14, 0.60])
    panel(s, X, 5.30, W, 1.05, "AND NOTHING WAS BLOCKED THAT FORTNIGHT",
          "%s distinct paths were requested that we do not serve. Zero blocks was the correct "
          "outcome: the candidate rules had not yet earned the right to block. Nobody chose us. "
          "An address range was walked, and the customer sits in one too." % PATHS_UNSERVED,
          10.5, CYAN, WHITE)
    _tb(s, X, 6.50, W, 0.40,
        "Say DETECTED, never stopped. These are the requests that arrived and what the classifier "
        "recognised them as, on a live estate of six unrelated domains on one host.",
        10, MUTED, TEXT)

    # ---------------------------------------------------------------- 3. why the stack misses it
    s = d.slide("THE GAP", "NOBODY IS WATCHING", " THE CLIENT.",
                "Every layer below is real, necessary and keeps its budget. None of them is shaped "
                "to answer the question a scanner poses.")
    rows = [("Network firewall", "Ports and addresses",
             "Cannot see a URL path. Port 443 is open by design, and the scan arrives through it."),
            ("WAF", "The payload of one request",
             "Judges each request on its own merits. It does not model one client across many requests over time."),
            ("DDoS scrubbing", "Volume",
             "A four request reconnaissance scan is not volume. It passes cleanly, exactly as it should."),
            ("EDR", "The host, after landing",
             "Engages once something is already executing on the machine. The scanner is still outside."),
            ("SIEM", "Everything, later",
             "Correlates after the fact, for a human who reads it afterwards.")]
    table(s, X, 1.95, W, ["Layer", "What it judges", "Why a scanner walks past it"],
          rows, [0.20, 0.22, 0.58], rh=0.50)
    panel(s, X, 5.10, W, 1.10, "THE GAP IS BEHAVIOUR OVER TIME, FROM ONE CLIENT",
          "One request for /.env is noise. Four requests for four different secrets files, from "
          "one address announcing six browsers, is an attack in progress. That sentence needs a "
          "model of the client, held over time, and it is the one thing none of the layers above "
          "was built to keep.", 10.5, CYAN, WHITE)
    _tb(s, X, 6.35, W, 0.55,
        "Perseus is HTTP layer only and deliberately narrow. It adds one question to the stack. It "
        "answers nothing the other layers already answer, and it takes nothing away from them.",
        10, MUTED, TEXT)

    # ---------------------------------------------------------------- 4. what it is
    s = d.slide("WHAT IT IS", "MODELS PROPOSE.", " CODE DECIDES.",
                "One paragraph, and the sentence the whole product should survive being reduced "
                "to.")
    _tb(s, X, 1.95, W, 0.95,
        "Perseus AI SOC is an automated security operations centre that runs on the customer's own "
        "infrastructure, decides for itself what to do about each attack, and revises its own "
        "defences every day and every week without a human in the loop. Four language models from "
        "four independent vendors review each incident and propose. Deterministic code decides "
        "every side effect, and the decision on the request path is arithmetic.",
        11.5, BODY, TEXT)
    for i, (h, b, c) in enumerate([
            ("IT ADDS, IT REPLACES NOTHING",
             "The firewall, the WAF, the CDN, the EDR and the SIEM all stay exactly as they are. "
             "Perseus is a high quality source for the SIEM, not a competitor for its budget.", CYAN),
            ("NO AGENT, ANYWHERE",
             "Nothing is installed on an endpoint, on a laptop or on a server the customer runs. "
             "One file goes next to the protected application and the brain runs beside it.", VIOLET),
            ("NEVER A FIREWALL CHANGE",
             "No iptables, no nftables, no ufw, no ACL, no rule push to anything. Enforcement is "
             "HTTP layer, inside our own process, and it is asserted by test on every deploy.", INDIGO)]):
        card(s, X3[i], 3.05, W3, 2.10, "0%d" % (i + 1), c, h, b, bsize=9.6)
    panel(s, X, 5.45, W, 1.05, "WHY IT IS CALLED PERSEUS",
          "Perseus beat the Gorgon without ever looking at her directly. He watched the reflection "
          "in a polished shield. A user agent is attacker controlled and it lies. The paths a "
          "client asks for are the reflection, and they cannot be faked without abandoning the "
          "attack. The name is the mechanism.", 10.5, CYAN, WHITE)

    # ---------------------------------------------------------------- 5. how it works
    s = d.slide("HOW IT WORKS", "OBSERVE. CORROBORATE.", " ACT. ASK.",
                "Four steps. The first three are arithmetic and happen in microseconds. The fourth "
                "reaches a named human.")
    for i, (k, kc, h, b) in enumerate([
            ("01", CYAN, "OBSERVE",
             "Every request is classified against %d attack classes by regular expression, not by "
             "inference: WordPress, PHP probes, .env and .git, admin panels, traversal, SQLi, XSS, "
             "shell and RCE, backup files, cloud metadata, honeytoken paths and more." % N_CLASSES),
            ("02", VIOLET, "CORROBORATE",
             "Signals must agree before they convict. A rotating fingerprint proves automation, not "
             "attack, so it scores only alongside a second hostile signal. A source scores only "
             "after missing on six or more distinct paths. Your uptime checks look like automation "
             "too."),
            ("03", INDIGO, "ACT, INSIDE A TIME BOX",
             "Tarpit first, then a timed HTTP block, then the alert. Every automatic block expires "
             "by itself. Nothing the shield does on its own is permanent and nothing needs a human "
             "to undo it."),
            ("04", GREEN, "ASK, FOR ANYTHING BIGGER",
             "A 24 hour hold, widening to a /24, an abuse report: those reach a named human on "
             "Telegram with the evidence attached, and they expire unanswered after two hours. "
             "Nothing waits on a person indefinitely.")]):
        card(s, X2[i % 2], 1.95 + (i // 2) * 2.10, W2, 1.95, k, kc, h, b)
    _tb(s, X, 6.20, W, 0.60,
        "NO MODEL CALL IS EVER IN THE REQUEST PATH. A model call takes 300 ms to 60 s, and in "
        "front of a request that is itself a denial of service that is the outage. The panel "
        "reviews what the shield DID, out of band, on a timer.", 10.5, AMBER, TEXT, True)

    # ---------------------------------------------------------------- 6. the three loops
    s = d.slide("AUTONOMY", "THREE LOOPS.", " NOBODY SETS AN ALARM.",
                "Systemd timers on the customer's own box. Both calendar strings are pinned by "
                "test, so this schedule is the schedule that ships.")
    rows = [("Per incident", "every 10 minutes",
             "Groups one source's distinct missed paths inside a 15 minute window and asks the four model panel about ONE live incident.",
             ("Proposes into detection only. It has no path to blocking.", CYAN)),
            ("Daily", "04:40 UTC",
             "Scores yesterday's traffic against every live rule, demotes what misfired, mines candidates, vets them, promotes what has earned it, tunes thresholds, files abuse reports, publishes the blocklist.",
             ("Promote, demote, tune inside committed bounds, publish.", CYAN)),
            ("Weekly", "Sunday 05:20 UTC",
             "Re-vets every live rule against THIS week's routes, retires what a month never matched, then runs a seven day daily cycle.",
             ("Demote, retire, and everything the daily cycle may do.", CYAN))]
    table(s, X, 1.95, W, ["Loop", "When", "What it does", "What it may change"],
          rows, [0.13, 0.15, 0.44, 0.28], rh=0.90)
    panel(s, X, 5.30, W, 1.25, "WHY THE WEEKLY LOOP EXISTS",
          "Attack patterns do not go stale. Customer applications move, and a rule that was a clean "
          "attack signature in July can start matching paths the application itself now serves. On "
          "13 September 2026 the weekly cycle retired %s rules. One of them matched /@fs/ and by "
          "that date matched %s paths our own build output serves. Left alone it would have broken "
          "the site while every dashboard stayed green." % (RETIRED, FS_PATHS), 10.5, CYAN, WHITE)
    _tb(s, X, 6.65, W, 0.32,
        "Both timers are persistent, so a run missed while the machine was down executes at boot "
        "rather than being skipped.", 10, MUTED, TEXT)

    # ---------------------------------------------------------------- 7. the promotion gate
    s = d.slide("THE GATE", "FIVE CONDITIONS.", " ALL FIVE, OR NOTHING.",
                "A rule moves from detection to blocking only when every one of these is "
                "satisfied. The clauses live once, in the code that judges them.")
    rows = [("Currently in detection", "tier is detect",
             "Nothing promotes from nowhere."),
            ("Time served in detection", "at least 24 hours",
             "A rule earns the right to block by being watched first."),
            ("Independent agreement", "3 of the 4 reviewers, one per vendor",
             "One model cannot carry a rule on its own."),
            ("Real hostile evidence", "at least 1 confirmed hostile match",
             "A rule with no attack behind it is a guess with a regular expression."),
            (("Collateral damage", WHITE), ("exactly zero clean matches", CYAN),
             ("Absolute. The code quotes no shortfall for this one, because there is none.", CYAN))]
    table(s, X, 1.95, W, ["Condition", "Value", "Why it is there"],
          rows, [0.24, 0.30, 0.46], rh=0.50)
    panel(s, X, 4.85, W, 1.25, "THE WORKED EXAMPLE, 13 SEPTEMBER 2026",
          "A candidate rule matching WordPress paths had %s hostile hits behind it, which is "
          "tempting evidence. It also had %s hits from real visitors. It was refused outright, by "
          "arithmetic, after four models had proposed it. The ruleset that week: 2 blocking, 7 in "
          "detection, 0 ready to promote. That is the gate working, not a bad week."
          % (GATE_HOSTILE, GATE_CLEAN), 10.5, CYAN, WHITE)
    _tb(s, X, 6.25, W, 0.60,
        "One legitimate hit kills a candidate permanently and no number of good days earns it back. "
        "The review that opens the daily and the weekly loop also DEMOTES any blocking rule that "
        "has since refused something legitimate. Full autonomy with no way back is a one way door.",
        10, MUTED, TEXT)

    # ---------------------------------------------------------------- 8. four models, four vendors
    s = d.slide("THE PANEL", "FOUR MODELS.", " FOUR VENDORS.",
                "One model each from four independent providers, reviewing what the shield did and "
                "proposing what it should do next.")
    for i, (kick, head, body, col) in enumerate([
            ("MODEL 01", "DeepSeek", "deepseek-3.2", CYAN),
            ("MODEL 02", "Meta", "llama-4-maverick", VIOLET),
            ("MODEL 03", "Google", "gemma-4-31B-it", INDIGO),
            ("MODEL 04", "Moonshot", "kimi-k2.6", GREEN)]):
        card(s, X4[i], 1.95, W4, 1.40, kick, col, head, body, bsize=10)
    panel(s, X2[0], 3.60, W2, 2.15, "ADVISORY IN BOTH DIRECTIONS",
          "The panel may propose detection patterns and values for six integers, and every value it "
          "proposes is clamped to a committed range on read. It may not block or unblock an "
          "address, change the bounds, touch the blast cap, the allow list, the kill switch or the "
          "never block path list. It cannot force a good change through and it cannot wave a bad "
          "one past the gate.")
    panel(s, X2[1], 3.60, W2, 2.15, "THE WEEK THEY ALL WENT QUIET",
          "On 13 September 2026 the panel answered 0 of 4 times. Vendors were down or rate "
          "limiting. Nothing broke, because the models advise and the code decides. This is the "
          "most useful fact in the pack: a security control that stops working when a language "
          "model is unavailable is a single point of failure with a friendly personality.",
          10.5, AMBER, BODY)
    _tb(s, X, 6.00, W, 0.80,
        "FOUR VENDORS, NO SHARED FAILURE DOMAIN. A rate limit or an outage is provider wide, so a "
        "four model panel on one vendor is four hats on one head. It also means a model that is "
        "simply wrong is contradicted by three others rather than believed. The proposals are "
        "vetted by five fail closed barriers before the gate ever sees them, and both halves, "
        "accepted and refused, appear in the daily report.", 10.5, BODY, TEXT)

    # ---------------------------------------------------------------- 9. what it will never do
    # The sub is ONE LINE at 11.5pt in a 12.10in box, which is about 145 characters. A longer one
    # wraps and the second line lands 0.08in above the first content row at y=1.95.
    s = d.slide("THE BOUNDARY", "WHAT IT WILL NEVER DO.", " A FEATURE.",
                "Every line below is asserted by a test or by the shape of the code. A boundary "
                "the buyer has to discover during an incident is not a boundary.")
    bullets(s, X2[0], 1.95, W2, [
        "IT NEVER TOUCHES A FIREWALL. No iptables, no nftables, no ufw, no firewall-cmd, no ACL, "
        "no rule push to anything. Enforced by a test that greps the modules after stripping "
        "comments and docstrings.",
        "IT NEVER BLOCKS AN AUTHENTICATED SESSION, and never tarpits one. The evidence is still "
        "recorded. Refusing a real page locks a real person out.",
        "IT NEVER BLOCKS /.well-known/ OR /api/. Blocking the first turns a scanner into a "
        "certificate outage for every domain on the host. On the second, authentication is the "
        "control and a 401 is already a refusal. An exemption from enforcement is never an "
        "exemption from observation.",
        "IT CANNOT CAUSE A MASS OUTAGE. The blast cap refuses to block more than 20 percent of "
        "recently seen distinct visitors beyond a floor of 5 absolute blocks. Over the cap the "
        "verdict degrades to a tarpit.",
        "IT FAILS OPEN, ALWAYS. Every internal error in the decision path resolves to ALLOW. A "
        "route the customer actually serves is slowed, never blocked. Two switches sit above "
        "everything and neither is tunable by the panel.",
    ], gap=0.60, size=10.5)
    panel(s, X2[1], 1.95, W2, 3.35, "SCANNING BACK, CONNECTING BACK, HACK BACK",
          "Not a feature, not a roadmap item, not behind a flag. There is no button for it and "
          "there will not be one.\n\n"
          "Criminal under StGB 202a, 202b, 303a, 303b and 202c, which covers possession and "
          "creation of the tooling, EU Directive 2013/40, US CFAA 1030 and Canada CC 342.1.\n\n"
          "The attacking address is usually a compromised third party, so the lawful answer and "
          "the effective answer are the same answer: a complaint to the provider, drafted "
          "automatically and filed by a person.", 10.5, RED, BODY)
    panel(s, X2[1], 5.45, W2, 1.35, "AND WHAT IT IS NOT",
          "It is not a WAF. It is not a DDoS scrubber. It is not an IPS. It is not EDR. It inspects "
          "nothing below HTTP. It replaces nothing you already own.", 10.5, AMBER, WHITE)

    # ---------------------------------------------------------------- 10. deployment
    s = d.slide("DEPLOYMENT", "FOUR SHAPES.", " NONE NEEDS A WINDOW.",
                "Pick the shape that fits the estate. Whichever one is picked, start with "
                "enforcement off.")
    for i, (kick, head, body, col) in enumerate([
            ("A", "REVERSE PROXY", "Perseus runs inside the proxy that already fronts the sites. "
             "This is how we run it ourselves, in front of six unrelated domains on one host.", CYAN),
            ("B", "LEGACY SIDECAR", "Perseus terminates in front of an application nobody wants to "
             "touch and passes traffic through. The application is unmodified and unaware.", VIOLET),
            ("C", "DETECTION ONLY", "Enforcement off, telemetry on. It watches and reports without "
             "ever refusing a request. This is where every engagement starts.", GREEN),
            ("D", "FEED THEIR EDGE", "Every decision is a structured event. Export it to the SIEM, "
             "hand the blocklist to the edge they already run. Perseus decides, their estate "
             "enforces.", INDIGO)]):
        card(s, X4[i], 1.95, W4, 2.30, kick, col, head, body, bsize=9.6)
    panel(s, X2[0], 4.50, W2, 1.50, "WHAT THE CUSTOMER PROVIDES",
          "An ASGI application, or a reverse proxy we can run middleware inside. Shape B covers "
          "anything else. A writable volume for the event log and the published blocklist. Two "
          "environment variables, to name the service and the log path. Everything else has a "
          "default.")
    panel(s, X2[1], 4.50, W2, 1.50, "WHAT IS NOT REQUIRED",
          "A credential. An API token. An outbound network call from the protected application. "
          "Firewall access. Root. A new software dependency. A change to the application's own "
          "code. A maintenance window. An agent on anything.", 10.5, GREEN, BODY)
    _tb(s, X, 6.15, W, 0.55,
        "START AT C. A defence nobody has watched being wrong is a defence nobody can trust to be "
        "right, and detection only costs nothing to reverse. The installer then PROVES the brain "
        "by asking the container for a published blocklist newer than 48 hours, and exits non zero "
        "if it cannot get one.", 10, MUTED, TEXT)

    # ---------------------------------------------------------------- 11. what you receive
    s = d.slide("REPORTING", "WHAT ARRIVES,", " AND WHEN.",
                "Six outputs. Five reach a person, one reaches the log the customer already "
                "queries.")
    rows = [("Daily attack digest", "Telegram and email", "07:00 UTC"),
            ("Daily cycle report", "Telegram and email", "after 04:40 UTC"),
            ("Weekly cycle report", "Telegram and email", "after Sunday 05:20 UTC"),
            ("Live incident alert, with action buttons", "Telegram", "as it happens"),
            ("Fleet state change", "Telegram", "on transition only"),
            ("Every decision as a structured event", "stdout to Loki, queryable in Grafana",
             "continuously")]
    table(s, X, 1.95, W, ["Report", "Channel", "When"], rows, [0.36, 0.34, 0.30])
    panel(s, X, 5.25, W, 1.15, "WHY IT DOES NOT BECOME NOISE",
          "A 900 second cooldown per rule and subject, a storm cap of 12 alerts an hour, and state "
          "changes are edge triggered so a steady state never pages twice. An alert nobody receives "
          "is not an alert, and a warning that fires on every run teaches the operator to read past "
          "the one that matters.", 10.5, CYAN, WHITE)
    _tb(s, X, 6.55, W, 0.40,
        "The digest also names what it could NOT name: how many of the four models answered, and "
        "the scanning shapes the classifier does not yet recognise. A dedicated Grafana board for "
        "the Perseus stream is roadmap and is not built yet.", 10, MUTED, TEXT)

    # ---------------------------------------------------------------- 12. the first thirty days
    s = d.slide("THE PILOT", "THE FIRST THIRTY DAYS.", " FREE.",
                "Detection only, once per customer, no commitment attached to it. Here is what "
                "each week actually looks like.")
    for i, (kick, head, body, col) in enumerate([
            ("WEEK 1", "DEPLOY", "Enforcement off, telemetry on. One file copied next to the "
             "application, one middleware line, the brain installed beside it. No maintenance "
             "window.", CYAN),
            ("WEEKS 2 AND 3", "WATCH IT BE WRONG", "Your own monitoring, CI, partners and crawlers "
             "are exactly the traffic that exposes a bad rule. Candidates sit in detection with "
             "their hostile and clean counts in view.", VIOLET),
            ("WEEK 4", "TURN IT ON", "You choose which classes enforce and at which thresholds, "
             "inside the committed bounds. Both switches above the whole system stay in your "
             "hands.", INDIGO),
            ("FROM THEN ON", "THE LOOPS RUN", "Every ten minutes, daily at 04:40 UTC, weekly on "
             "Sunday at 05:20 UTC. The reports arrive whether or not anything happened.", GREEN)]):
        card(s, X4[i], 1.95, W4, 2.30, kick, col, head, body, bsize=9.6)
    panel(s, X, 4.50, W, 1.50, "WHY IT STARTS WITH ENFORCEMENT OFF",
          "The switch that runs the pilot stops enforcement and keeps detection, telemetry and "
          "reporting running, so the customer sees every verdict Perseus WOULD have applied without "
          "a single request being refused. Four weeks of that is how a team learns whether the gate "
          "is strict enough for their traffic, and it is the only honest way to find out. Turning "
          "enforcement on afterwards is one variable, and turning it back off is the same "
          "variable.", 10.5, CYAN, WHITE)
    _tb(s, X, 6.15, W, 0.40,
        "Two things to check first on any quiet pilot: whether the brain can read that "
        "application's request lines at all, and whether a catch all route is answering probe "
        "requests 2xx and disarming local enforcement by design.", 10, MUTED, TEXT)

    # ---------------------------------------------------------------- 13. the price list
    s = d.slide("COMMERCIALS", "THE PRICE LIST.", " PUBLISHED.",
                "European reference, effective 17 September 2026. Monthly subscription on an "
                "annual term, because the defences change daily.")
    rows = [("SENTRY", "Detection only, full reporting", "up to 3 protected applications",
             "120 a month", (P_SENTRY + " / month", CYAN)),
            ("SHIELD", "Autonomous enforcement", "up to 10 protected applications",
             "360 a month", (P_SHIELD + " / month", CYAN)),
            ("CITADEL", "Enforcement, legacy integration, named engineer",
             "up to 25 protected applications", "360 a month", (P_CITADEL + " / month", CYAN))]
    table(s, X, 1.95, W, ["Tier", "What it is", "Unit", "Investigations included", "List"],
          rows, [0.12, 0.30, 0.22, 0.19, 0.17], rh=0.50)
    rows = [("Additional protected application", P_APP + " each, per month"),
            ("Autonomous investigations beyond the allowance", P_INVEST + " each"),
            ("Onboarding: SENTRY / SHIELD / CITADEL",
             " / ".join([ONB_SENTRY, ONB_SHIELD, ONB_CITADEL])),
            ("Incident review with the engineer", P_HOUR + " per hour"),
            ("Tuning and handover workshop", P_DAY + " per day"),
            ("30 day pilot, detection only", ("free, once per customer", GREEN))]
    table(s, X2[0], 4.10, W2, ["Also on the list", "Price"], rows, [0.62, 0.38], rh=0.38)
    note = ("The unit is the protected internet facing application. The price does not scale with "
            "headcount, because the product does not touch headcount. That is a statement about "
            "the unit of sale and not a claim to be cheaper than anybody. No availability or "
            "response target is quoted in this deck: the SLA has no Perseus specific targets yet.")
    if partner:
        rows = [("Partner", "10%", "€1,080 per month"),
                ("VAR", "20%", "€960 per month"),
                ("Gold", "30%", "€840 per month"),
                ("Platinum", "40%", (PLATINUM_BUY + " per month", CYAN))]
        table(s, X2[1], 4.10, W2, ["Partner tier", "Discount", "SHIELD at that tier"],
              rows, [0.34, 0.26, 0.40], rh=0.38)
        _tb(s, X2[1], 6.15, W2, 0.75, note, 9.5, MUTED, TEXT)
    else:
        # The discount block owned the right column from 4.10 to 6.02 and the note sat under it at
        # 6.15. Deleting the block and leaving everything else where it was would print a table
        # down the left and two thirds of a blank slide down the right, so the note takes the
        # column the block vacated, and it reads at the same 10.5pt as every other standing
        # paragraph in the deck rather than at the 9.5pt it needed as a footnote.
        # ARITHMETIC, so it is centred against its neighbour rather than floating: the table on the
        # left runs 4.10 to 6.78 and its centre is 5.44. The note is five lines at 10.5pt in a
        # 6.00in column, about 0.84in, so a box at 4.95 puts its centre at 5.37. It ends at 6.05,
        # a full inch clear of the footer at 7.04, and assert_layout() enforces that on both builds.
        _tb(s, X2[1], 4.95, W2, 1.10, note, 10.5, MUTED, TEXT)

    # ---------------------------------------------------------------- 14. the upsell ladder
    s = d.slide("THE LADDER", "FROM A €100 RUN", " TO A CONTRACT.",
                "The joint motion with cybergod.ai. Every rung is priced on the same published "
                "card, and each one is the evidence for the next.")
    rows = [("01", "A cybergod.ai assessment run. The customer's estate as an attacker sees it, "
             "with not one packet sent to their infrastructure.", ("€100 per run", CYAN)),
            ("02", "Findings review with the engineer who built the engine.", (P_HOUR + " per hour", CYAN)),
            ("03", "Perseus pilot. Thirty days, detection only, once per customer.", ("free", GREEN)),
            ("04", "SENTRY or SHIELD. Monthly subscription on an annual term.",
             (P_SENTRY + " or " + P_SHIELD + " a month", CYAN)),
            ("05", "Tuning and handover workshop, on site or remote.", (P_DAY + " per day", CYAN)),
            ("06", "CITADEL, with legacy integration and a named engineer.", (P_CITADEL + " a month", CYAN)),
            ("07", "Remediation of what the assessment and the loops actually found.",
             ("scoped per case", MUTED))]
    table(s, X, 1.95, W, ["Rung", "What it is", "Price"], rows, [0.07, 0.63, 0.30], rh=0.48)
    panel(s, X, 5.95, W, 0.95, "WHY THE LADDER HOLDS TOGETHER",
          "The assessment tells the customer what is exposed on the day it runs. Perseus watches "
          "what arrives at it every day afterwards. Each rung is scoped from what the rung below "
          "it found, which is why every one of them is quoted off the same published card instead "
          "of being negotiated from nothing.", 10.5, CYAN, WHITE)

    # ---------------------------------------------------------------- 15. partner economics
    # PARTNER BUILD ONLY. This is the partner's buy price, the partner's margin and the partner's
    # book of fifty customers. Deck.slide() increments self.n, so the slide that follows simply
    # takes 15 and the page numbers stay contiguous with no renumbering anywhere.
    if partner:
        s = d.slide("PARTNER ECONOMICS", "THE ARITHMETIC,", " AT LIST PRICE.",
                    "SHIELD as the worked example, because it is the tier most customers land on "
                    "after a detection only pilot.")
        for i, (v, lab, col) in enumerate([
                (P_SHIELD, "SHIELD list price\nper month", MUTED),
                (PLATINUM_BUY, "what a Platinum partner\nbuys it at", CYAN),
                (PLATINUM_MARGIN, "gross margin per customer\nper month, at list", VIOLET),
                (FIFTY, "a month across\nfifty customers", GREEN)]):
            stat(s, X + i * 3.06, 1.95, 2.90, v, lab, col)
        rows = [("Partner", "10%", "€1,080", "€120", "€6,000"),
                ("VAR", "20%", "€960", "€240", "€12,000"),
                ("Gold", "30%", "€840", "€360", "€18,000"),
                (("Platinum", WHITE), ("40%", CYAN), (PLATINUM_BUY, CYAN),
                 (PLATINUM_MARGIN, CYAN), (FIFTY, CYAN))]
        table(s, X, 3.25, W, ["Tier", "Discount", "Buy price", "Margin per customer",
                              "Fifty customers on SHIELD"],
              rows, [0.18, 0.14, 0.20, 0.24, 0.24], rh=0.46)
        panel(s, X, 5.70, W, 1.15, "WHY THE LINE KEEPS RENEWING",
              "Gross margin at list price, on a subscription the customer renews without a renewal "
              "conversation, because the defence they are paying for is not the one they bought "
              "last month. Delivery is close to nothing: the three loops run themselves and no "
              "analyst sits behind them. The services rungs, the review, the workshop and the "
              "remediation, are the partner's existing business, now arriving with evidence "
              "attached instead of a brochure.", 10.5, CYAN, WHITE)

    # ---------------------------------------------------------------- 16. who you sign with
    s = d.slide("NEXT STEP", "REAL COMPANIES.", " A CLEAR NEXT STEP.",
                "Four entities, one contracting party, and three ways to spend the next twenty "
                "minutes.")
    rows = [(("Stars4business OÜ", WHITE), "Estonia",
             ("EU hub, consultancy, CONTRACTING ENTITY", CYAN), "VAT EE102156878"),
            ("S4biz UG (haftungsbeschränkt)", "Germany", "Software development",
             "USt-IdNr. DE361822318"),
            ("S4BIZ Lda", "Portugal", "Iberia operations", "NIF 518007596"),
            ("CyberGod LLC", "Delaware, USA", "Cyber and cloud", "EIN on file")]
    table(s, X, 1.95, W, ["Entity", "Country", "Role", "Tax ID"],
          rows, [0.28, 0.16, 0.34, 0.22], rh=0.40)
    _tb(s, X, 4.05, W, 0.60,
        "You sign with Stars4business OÜ. Governing law Estonia, binding language English, data in "
        "the EU on servers in Frankfurt.\n"
        "No availability or response target is quoted anywhere in this pack: the SLA has no "
        "Perseus specific service targets yet, and inventing one would be the only number in the "
        "deck that nobody measured.", 10, MUTED, TEXT)
    for i, (kick, head, body, col) in enumerate([
            ("01", "SEE IT RUNNING", "Against our own live estate, with the last digest and the "
             "last weekly cycle open beside it.", CYAN),
            ("02", "TWENTY MINUTES", "With the architect who wrote it rather than with a "
             "salesperson. Bring the hard question.", VIOLET),
            ("03", "START THE PILOT", "Thirty days, detection only, free, and reversible on the "
             "afternoon you change your mind.", GREEN)]):
        card(s, X3[i], 4.70, W3, 1.65, kick, col, head, body, bsize=10)
    _rect(s, X, 6.45, W, 0.52, fill=PANEL, line=LINE)
    _tb(s, X + 0.25, 6.56, W - 0.50, 0.32,
        "PERSEUS AI SOC · Evgeny 'Jev' Vainshtein, Principal Architect · feranicus@s4biz.io · "
        "cybergod.ai", 11, WHITE, MONO, True)

    assert_layout(d)
    return d.save(out)


DEFAULT_OUT = os.path.join(
    os.path.expanduser("~"), "Downloads", "cybergod partnership", "aisoc_pack",
    "07_Perseus_AI_SOC_Commercial_Presentation_EN.pptx")


def default_out(audience):
    """Where a build lands when --out is not given.

    The partner build keeps the pack's existing filename, because build_pack.py and the START HERE
    guide both name it. The customer build lands beside it with _CUSTOMER before the extension:
    two files that differ in what they are allowed to show must not differ only by which one was
    rendered last into the same path.
    """
    if audience == "partner":
        return DEFAULT_OUT
    root, ext = os.path.splitext(DEFAULT_OUT)
    return root + "_CUSTOMER" + ext


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--audience", choices=AUDIENCES, default="partner",
                    help="partner: everything, including the economics slide and the discount "
                         "ladder. customer: neither, and a CUSTOMER PRESENTATION footer.")
    ap.add_argument("--out", default=None,
                    help="explicit path wins over the per-audience default")
    a = ap.parse_args()
    out = a.out or default_out(a.audience)
    if not os.path.exists(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    # The pack directory is the delivery target and may not exist on a fresh machine. Create it
    # rather than failing three minutes of rendering on a missing folder.
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    p = build(a.template, out, a.audience)
    print("built: %s (%s audience, %.1f KB)"
          % (p, a.audience, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
