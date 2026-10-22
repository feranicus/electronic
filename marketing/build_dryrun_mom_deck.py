#!/usr/bin/env python3
"""Minutes of the 21 October 2026 dry-run session, as a deck.

SOURCE: the Tactiq transcript of the session (205 minutes, six participants). Everything on these
slides is drawn from that transcript. Where a view belongs to one participant it is attributed,
because in minutes the attribution is the content; this is the opposite rule to the customer deck,
where the same quotations were stripped out.

VOICE: minutes, not marketing. No persuasion, no adjectives we cannot support, and the criticism
is recorded at full strength rather than softened. A set of minutes that flatters the product is
worth nothing to the people who have to act on it.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402
    AMBER, BODY, CYAN, Deck, GREEN, INDIGO, LINE, MONO, PANEL, RED, TEXT, VIOLET, WHITE,
    _rect, _tb, bullets, card,
)
from build_perseus_shield_deck import table  # noqa: E402

FOOT = "S4BIZ GROUP · CYBERGOD LLC · MINUTES · INTERNAL"
DATE, MINS = "21 October 2026", 205
PEOPLE = "Assad Kondakji · Dima Diall · Ivo · Jev · Marcos Fonseca · Miguel"
TITLE_CAP = 40


def build(template, out):
    d = Deck(template)
    _orig = d.slide

    def slide(eyebrow, title, tail="", sub="", hero=False):
        row = (title if isinstance(title, str) else " ".join(t for t, _ in title)) + (tail or "")
        assert len(row) <= TITLE_CAP, "title row %d chars: %r" % (len(row), row)
        return _orig(eyebrow, title, tail, sub, FOOT, hero)
    d.slide = slide

    # ---------------------------------------------------------------- 1. cover
    s = d.slide("MINUTES  ·  DRY RUN", [("CYBERGOD", WHITE), ("DRY RUN.", VIOLET)], hero=True)
    _tb(s, 0.85, 4.15, 9.60, 0.90,
        "Product walkthrough and critical review with the Angola team. "
        "%s, %d minutes." % (DATE, MINS), 15, BODY, TEXT)
    _tb(s, 0.85, 5.20, 11.60, 0.30, "PRESENT", 10, CYAN, MONO, True, space=1.8)
    _tb(s, 0.85, 5.52, 11.60, 0.40, PEOPLE, 13, WHITE, TEXT)
    _rect(s, 0.85, 6.10, 11.60, 0.70, fill=PANEL, line=LINE)
    _tb(s, 1.10, 6.24, 11.1, 0.46,
        "Outcome: the walkthrough held. One substantial product criticism was raised and accepted, "
        "and it is the subject of slides 4 to 6.", 12, WHITE, TEXT)

    # ---------------------------------------------------------------- 2. what was shown
    s = d.slide("SESSION", "WHAT WAS WALKED", " THROUGH.",
                "One input, a company name. Roughly five to ten minutes later the artefacts are "
                "on screen, which is what makes it usable inside a live meeting.")
    rows = [("External assessment",
             "What the company exposes to the internet, from public records only."),
            ("GEOPOL, darknet view",
             "Which named groups exploit those specific weaknesses, how, and why this company."),
            ("Compliance set",
             "Per-company decks against the laws and frameworks that apply to it."),
            ("Risk priced in euros",
             "Annual loss expectancy and maximum loss per incident, with the method shown. "
             "Currency is configurable."),
            ("Perseus active defence",
             "The continuous half: detection, and graduated reversible enforcement.")]
    y = table(s, 0.85, 2.22, 11.60, ["Artefact", "What it answers"], rows, [0.30, 0.70], rh=0.50)
    _rect(s, 0.85, y + 0.20, 11.60, 1.12, fill=PANEL, line=LINE)
    _tb(s, 1.10, y + 0.32, 11.1, 0.28, "THE TWO COMMERCIAL ROUTES DISCUSSED", 10, CYAN, MONO, True)
    _tb(s, 1.10, y + 0.62, 11.1, 0.66,
        "Direct to end customers, any B2B company from small and mid-sized upward. Preferred "
        "route is through managed service providers, who run the assessments and upsell "
        "remediation to their own customers. A cyber-insurance use of the same toolset was also "
        "raised.", 11, BODY, TEXT)

    # ---------------------------------------------------------------- 3. what landed
    s = d.slide("RECEIVED WELL", "WHAT THE ROOM", " ACCEPTED.",
                "Recorded so the criticism that follows is read in proportion.")
    for i, (k, kc, h, b) in enumerate([
            ("01", GREEN, "ONE INPUT, ARTEFACTS IN MINUTES",
             "A company name produces the full set during the meeting. Nobody disputed that this "
             "changes how a first sales conversation can be run."),
            ("02", GREEN, "RISK PRICED IN MONEY",
             "Annual loss expectancy and maximum loss per incident. The argument that a CFO reads "
             "numbers while IT reads findings was accepted."),
            ("03", GREEN, "NAMED ADVERSARIES, NOT CATEGORIES",
             "The darknet view attributes specific weaknesses to specific groups rather than "
             "describing threat types in the abstract."),
            ("04", GREEN, "REMEDIATION IS PART OF THE OUTPUT",
             "Geofencing and dynamic DNS were shown as concrete next steps, which is also the "
             "upsell surface for a service provider.")]):
        card(s, 0.85 + (i % 2) * 6.05, 2.28 + (i // 2) * 2.10, 5.60, 1.90, k, kc, h, b, bsize=10)

    # ---------------------------------------------------------------- 4. the critique
    s = d.slide("THE CRITIQUE", "EXPOSURE IS NOT", " RISK.",
                "Raised by Miguel, supported by Ivo. This is the main output of the session and "
                "it is a product point rather than a presentation point.")
    bullets(s, 0.85, 2.28, 6.05, [
        "A RISK VALUE NEEDS SOMETHING BEHIND IT. Calling an exposed site medium or high is hard "
        "to justify unless the report can show what supports the rating.",
        "HIS EXAMPLE: a contractor working on their own portal, agreed in the contract. That is "
        "exposure. With no vulnerability behind it, it is not risk.",
        "IVO, AGREEING: without visible support for the finding, we sound like every other "
        "consultant saying the client is about to die tomorrow.",
        "IVO, ALSO: lack of security on a presentation site can be a serious compliance issue on "
        "its own. Both things are true, which is why the report has to separate them.",
    ], gap=1.12, size=10.5)
    _rect(s, 7.30, 2.28, 5.15, 4.10, fill=PANEL, line=RED)
    _tb(s, 7.55, 2.44, 4.65, 0.30, "WHY IT MATTERS COMMERCIALLY", 10, RED, MONO, True)
    _tb(s, 7.55, 2.90, 4.65, 3.20,
        "The market is saturated with vendors claiming everything is critical.\n\n"
        "Ivo's words: so much hype that it becomes hard to believe a finding when it is "
        "genuinely true.\n\n"
        "A report that cannot show its working is read as more of the same, however accurate it "
        "happens to be.\n\n"
        "The fix is therefore a selling feature, not a correction.", 11, BODY, TEXT)

    # ---------------------------------------------------------------- 5. the live example
    s = d.slide("EVIDENCE", "A CRITICAL THAT DID NOT", " HOLD.",
                "Worked through live, on screen, during the session.")
    _rect(s, 0.85, 2.28, 11.60, 1.55, fill=PANEL, line=AMBER)
    _tb(s, 1.10, 2.42, 11.1, 0.28, "WHAT HAPPENED", 10, AMBER, MONO, True)
    _tb(s, 1.10, 2.76, 11.1, 0.95,
        "A finding was graded critical: an Exchange server published to the internet and past end "
        "of support. Technically accurate as stated. On examination the host was known, managed "
        "and already a deliberate decision on the customer side, so the grading did not survive "
        "scrutiny in the room.", 12, BODY, TEXT)
    for i, (k, kc, h, b) in enumerate([
            ("CONSEQUENCE", RED, "IT COSTS CONFIDENCE IN THE WHOLE REPORT",
             "Miguel's point: a finding that is hard to justify on the page lowers trust in every "
             "other finding beside it, including the correct ones."),
            ("THE ASK", VIOLET, "SHOW WHAT SUPPORTS THE RATING",
             "Not more findings. Fewer, with the reasoning attached, so a reviewer can see why "
             "this one is critical and that one is not.")]):
        card(s, 0.85 + i * 6.05, 4.10, 5.60, 2.05, k, kc, h, b, bsize=10.5)

    # ---------------------------------------------------------------- 6. the proposal
    s = d.slide("PROPOSAL", "THE VERIFICATION", " PASS.",
                "Miguel's suggestion, and the one concrete feature request from the session.")
    for i, (n, k, b) in enumerate([
            ("1", "THE LONG LIST", "What every other vendor hands over. Everything that could "
                                   "matter, unranked by evidence."),
            ("2", "ONE ACTION", "A verification pass, run live during the presentation, which "
                                "narrows the list to findings with support behind them."),
            ("3", "THE SHORT LIST", "Far fewer items, each one carrying the reason it survived. "
                                    "This is the comparison the salesperson makes."),
            ("4", "EITHER RESULT SELLS", "If the long list collapses, the engine proved its "
                                         "value. If a finding is confirmed live, that is the "
                                         "demonstration.")]):
        x = 0.85 + i * 2.98
        _rect(s, x, 2.28, 2.78, 2.30, fill=PANEL, line=VIOLET if i else LINE)
        _tb(s, x + 0.20, 2.44, 0.40, 0.28, n, 13, VIOLET, MONO, True)
        _tb(s, x + 0.20, 2.80, 2.40, 0.30, k, 11.5, WHITE, TEXT, True)
        _tb(s, x + 0.20, 3.18, 2.40, 1.25, b, 9.6, BODY, TEXT)
    _rect(s, 0.85, 4.86, 11.60, 1.55, fill=PANEL, line=LINE)
    _tb(s, 1.10, 5.00, 11.1, 0.28, "THE CONSTRAINT WE RAISED, AND HE ACCEPTED", 10, CYAN, MONO,
        True)
    _tb(s, 1.10, 5.34, 11.1, 1.00,
        "Verification that touches the customer's network needs their written authorisation "
        "first, and the engine deliberately sends no packet to the target without it. Miguel "
        "accepted that constraint without argument. The open question is therefore how much "
        "verification is possible from public evidence alone, which is a design question for us "
        "rather than a disagreement with him.", 11.5, BODY, TEXT)

    # ---------------------------------------------------------------- 7. actions
    s = d.slide("ACTIONS", "WHAT HAPPENS", " NEXT.",
                "Owners as understood in the room. Correct anything mis-recorded here before this "
                "is circulated further.")
    rows = [("Specify the verification pass",
             "What can be confirmed from public evidence, what needs written authorisation, and "
             "how each finding shows its support.", "Jev"),
            ("Separate exposure from risk in the report",
             "Two distinct ratings, so a contractor portal with no vulnerability stops reading as "
             "a risk finding.", "Jev"),
            ("Re-check the critical grading rules",
             "Starting with the end-of-support case that did not hold, and what evidence should "
             "have been required before grading it.", "Jev"),
            ("Circulate summary and transcript",
             "AI-generated summary plus the full transcript to all participants.", "Dima"),
            ("Confirm the commercial route",
             "Managed service provider channel against direct, and whether the insurance use is "
             "pursued now or later.", "Dima, Ivo")]
    table(s, 0.85, 2.28, 11.60, ["Action", "Detail", "Owner"], rows, [0.26, 0.58, 0.16], rh=0.76)

    # ---------------------------------------------------------------- 8. close
    s = d.slide("SUMMARY", [("ONE SENTENCE.", WHITE)], hero=True)
    _rect(s, 0.85, 3.10, 11.60, 1.70, fill=PANEL, line=VIOLET)
    _tb(s, 1.20, 3.32, 11.0, 1.30,
        "The walkthrough and the commercial story were accepted. The product change the room "
        "asked for is to show the evidence behind each rating and to stop presenting exposure as "
        "if it were risk, because in a market this noisy an unsupported finding is read as noise "
        "even when it is correct.", 15, WHITE, TEXT)
    _tb(s, 0.85, 5.15, 11.60, 0.30, "RECORDED BY", 10, CYAN, MONO, True, space=1.8)
    _tb(s, 0.85, 5.47, 11.60, 0.70,
        "Minutes taken from the session transcript of %s. Attributions are as recorded; if a view "
        "is mis-assigned, say so and this will be reissued." % DATE, 12, BODY, TEXT)

    return d.save(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_DryRun_MoM_2026-10-21.pptx"))
    a = ap.parse_args()
    p = build(a.template, a.out)
    print("built: %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
