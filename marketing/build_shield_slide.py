#!/usr/bin/env python3
"""build_shield_slide.py — ONE slide: what actually hit cybergod.ai, and what now happens about it.

    python marketing/build_shield_slide.py [--out PATH] [--template PATH]

EVERY NUMBER IS MEASURED, and the provenance is on the slide itself:
  · 156,511 / 2,253 / 604 and the class breakdown come from `python analyse_attacks.py` reading
    colt-web's own event log on 10 Aug 2026.
  · 48/48 and 19 are the scanning-corpus coverage before and after that measurement.
  · 106 is the passing test count in this repository.

THE ONE THING THIS SLIDE MUST NOT CLAIM is that we "stopped 604 attacks". Those 604 were
DETECTED over the period the log covers; the shield shipped after them. Saying otherwise would be
the exact failure the assessment engine exists to prevent — a confident number with nothing behind
it — and on a slide about our own security discipline it would be self-refuting.
So the honest split is: DETECTED (604, historic) vs NOW STOPPED (every class of them, plus the 19
that were invisible until the log was read).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, card, stat,
)

FOOT = "S4BIZ GROUP · CYBERGOD LLC · measured on our own infrastructure, 10 Aug 2026"


def build(template, out):
    d = Deck(template)
    s = d.slide("live fire · cybergod.ai",
                "We read our own logs. ", "604 scanners read us first.",
                sub="156,511 requests · 2,253 sources · 11 attack classes · zero real visitors blocked",
                footer=FOOT)

    # ---- the headline numbers, left to right, in the order a reader asks them --------------
    stat(s, 0.55, 1.98, 2.30, "156,511", "REQUESTS ANALYSED\nfrom our own event log", CYAN)
    stat(s, 2.95, 1.98, 2.30, "604", "SOURCES THAT BEHAVED\nLIKE SCANNERS", AMBER)
    stat(s, 5.35, 1.98, 2.30, "48/48", "ATTACK PATH CLASSES\nNOW RECOGNISED", GREEN)
    stat(s, 7.75, 1.98, 2.30, "19", "DETECTION GAPS FOUND\nBY MEASURING, NOT GUESSING", VIOLET)
    stat(s, 10.15, 1.98, 2.60, "0", "REAL VISITORS BLOCKED\ntwo were one rule away", GREEN)

    # ---- what was actually out there ---------------------------------------------------------
    _rect(s, 0.55, 3.30, 6.05, 2.00, PANEL, LINE)
    _tb(s, 0.81, 3.48, 5.55, 0.24, "WHAT WAS ACTUALLY KNOCKING", 9, CYAN, MONO, True)
    rows = [("WordPress / PHP", "483", RED), ("Admin consoles", "162", RED),
            ("Shell + RCE chains", "113", RED), ("Secrets: .env .git .aws", "96", AMBER),
            ("Backups, API docs, routers", "79", AMBER)]
    yy = 3.80
    for name, n, col in rows:
        _tb(s, 0.81, yy, 4.30, 0.24, name, 10, BODY, TEXT)
        _tb(s, 5.20, yy, 1.10, 0.24, n, 11, col, MONO, True)
        yy += 0.29

    # ---- the practices, and WHY each one is there --------------------------------------------
    card(s, 6.85, 3.30, 2.90, 2.00, "detect", CYAN, "Evidence, not vibes",
         "Rotating user agents from one address is the one thing a real visitor never produces. "
         "The evasion IS the evidence.", bsize=9.2)
    card(s, 9.95, 3.30, 2.80, 2.00, "respond", VIOLET, "Slow, then stop",
         "Tarpit, then a time-boxed block. Reversible, expiring, HTTP-layer only. Nothing here "
         "touches a firewall.", bsize=9.2)

    # ---- the four models, and the honest boundary --------------------------------------------
    _rect(s, 0.55, 5.46, 12.20, 1.36, INK, INDIGO, 1.6)
    _tb(s, 0.81, 5.60, 11.70, 0.24,
        "FOUR MODELS, FOUR VENDORS  ·  deepseek-3.2  ·  llama-4-maverick  ·  gemma-4-31B-it  ·  kimi-k2.6",
        9.5, INDIGO, MONO, True)
    _tb(s, 0.81, 5.90, 11.70, 0.80,
        "They review every block out of band, write the incident report to Telegram, and may nudge six "
        "thresholds inside bounds committed in code. They are NOT in the request path: a model call is "
        "300ms to 60s, which in front of a request is itself a denial of service. Code decides; the panel "
        "explains, argues and is overruled by arithmetic. 106 tests gate every deploy.",
        9.5, BODY, TEXT, space=1.24)

    d.save(out)
    print("  wrote %s" % out)
    return 0


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    # The SAME template every S4biz deck is built from — one implementation, no drift.
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Cyber_LiveFire.pptx"))
    a = ap.parse_args()
    return build(a.template, a.out)


if __name__ == "__main__":
    sys.exit(main())
