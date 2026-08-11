#!/usr/bin/env python3
"""build_incident_slide.py — ONE slide: the 10 Aug 2026 incident, and what changed because of it.

    python marketing/build_incident_slide.py [--out PATH] [--template PATH]

EVERY FACT IS FROM THE OPERATOR'S OWN TELEGRAM ALERTS AND THE EVENT LOG, not from a summary:
  · 195.178.110.199, geolocated AD (Andorra), 19:05:55 to 19:05:57 UTC, 10 Aug 2026.
  · SIX distinct client fingerprints in two seconds: Safari/macOS, Chrome/Linux, Chrome/macOS,
    Edge/Windows 10, Firefox/Windows 10, Firefox/macOS.
  · Paths requested: /, //slug, /DOCS.md, /IAM.md, /[workspace]/.
  · The dirbruteforce rule fired correctly: 12 x 404 in 300s, UA claiming Chrome/126.0.0.0 on Linux.
  · The platform then sent SIX alerts each headed "A person just opened cybergod.ai", each ending
    "Bots are served a 404 and never reach this alert."

THE SLIDE'S POINT IS THAT SECOND FACT, and it is deliberately unflattering: the detection was
right and the response was nothing, while the alert text asserted something false six times over.
A slide that showed only the catch would be marketing. The reason to show the miss is that it is
the part a security buyer has also lived through.

NO LONG DASHES in any rendered string (operator standing rule, 10 Aug 2026).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb,
)

FOOT = "S4BIZ GROUP · CYBERGOD LLC · incident 2026-08-10 19:05 UTC · reconstructed from our own log"


def build(template, out):
    d = Deck(template)
    s = d.slide("incident · 10 aug 2026 · 19:05 utc",
                "Two seconds. Six browsers. ", "One address.",
                sub="The detector was right. The response was nothing. The alert said the opposite.",
                footer=FOOT)

    # ---------------------------------------------------------------- the timeline strip
    _rect(s, 0.55, 1.92, 12.20, 1.30, PANEL, LINE)
    _tb(s, 0.78, 2.06, 3.20, 0.22, "WHAT ARRIVED", 9, CYAN, MONO, True)
    _tb(s, 0.78, 2.34, 2.40, 0.70,
        "195.178.110.199\nAndorra\n19:05:55 to :57", 9.5, WHITE, MONO, space=1.30)

    # six fingerprints, one per column, so the eye counts them without being told
    fps = [("SAFARI", "macOS"), ("CHROME", "Linux"), ("CHROME", "macOS"),
           ("EDGE", "Win 10"), ("FIREFOX", "Win 10"), ("FIREFOX", "macOS")]
    x = 3.45
    for br, osn in fps:
        _rect(s, x, 2.30, 1.28, 0.72, INK, RED, 1.2)
        _tb(s, x + 0.06, 2.40, 1.16, 0.22, br, 8.5, RED, MONO, True)
        _tb(s, x + 0.06, 2.63, 1.16, 0.22, osn, 8.5, MUTED, MONO)
        x += 1.36

    _tb(s, 11.62, 2.34, 1.10, 0.70, "SIX\nCLIENTS", 13, RED, DISPLAY, True, space=1.10)

    # ---------------------------------------------------------------- three panels
    _rect(s, 0.55, 3.30, 3.95, 2.16, INK, LINE)
    _tb(s, 0.81, 3.46, 3.45, 0.22, "WHAT IT ASKED FOR", 9, AMBER, MONO, True)
    for i, p in enumerate(["/", "//slug", "/DOCS.md", "/IAM.md", "/[workspace]/"]):
        _tb(s, 0.81, 3.76 + i * 0.28, 3.45, 0.24, p, 10, WHITE, MONO)
    _tb(s, 0.81, 5.18, 3.45, 0.20,
        "Template placeholders. No human types these.", 8.5, MUTED, TEXT)

    _rect(s, 4.68, 3.30, 3.95, 2.16, INK, RED, 1.4)
    _tb(s, 4.94, 3.46, 3.45, 0.22, "WHAT WE DID ABOUT IT", 9, RED, MONO, True)
    _tb(s, 4.94, 3.76, 3.45, 1.62,
        "Nothing.\n\nThe brute force rule fired correctly at 12 x 404. Then the platform sent six "
        "alerts headed “A person just opened cybergod.ai”, each ending “bots are "
        "served a 404 and never reach this alert”.\n\nOne scanner. We said the opposite six "
        "times.",
        9.0, BODY, TEXT, space=1.20)

    _rect(s, 8.81, 3.30, 3.94, 2.16, INK, GREEN, 1.4)
    _tb(s, 9.07, 3.46, 3.44, 0.22, "WHAT RUNS NOW", 9, GREEN, MONO, True)
    _tb(s, 9.07, 3.76, 3.44, 1.62,
        "One address showing several browsers in seconds is a scanner. The evasion itself is the "
        "evidence.\n\nTarpit, then a timed block. A Telegram menu with six one tap escalations. "
        "Four models review it afterwards.\n\nSame request today: stopped in under two seconds.",
        9.0, BODY, TEXT, space=1.20)

    # ---------------------------------------------------------------- the lesson, stated plainly
    _rect(s, 0.55, 5.60, 12.20, 1.22, INK, INDIGO, 1.6)
    _tb(s, 0.81, 5.72, 11.70, 0.24,
        "THE PART WORTH KEEPING", 9, INDIGO, MONO, True)
    _tb(s, 0.81, 5.99, 11.70, 0.76,
        "A user agent is attacker controlled. The path is not. We had trusted the first and ignored "
        "the second, so a scanner announcing itself as six different people walked straight past a "
        "rule that was working. Reading the full log afterwards found 19 more classes we did not "
        "recognise. The detector was never the weak part; the assumption behind it was.",
        9.5, BODY, TEXT, space=1.24)

    d.save(out)
    print("  wrote %s" % out)
    return 0


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Cyber_Incident_10Aug.pptx"))
    a = ap.parse_args()
    return build(a.template, a.out)


if __name__ == "__main__":
    sys.exit(main())
