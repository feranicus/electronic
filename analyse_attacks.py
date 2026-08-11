#!/usr/bin/env python3
"""analyse_attacks.py — what has ACTUALLY hit cybergod.ai, read from the real event log.

WHY THIS EXISTS. The shield was built from ONE incident (10 Aug, the UA-rotating scanner). Tuning a
defence to a single sample is how you get a detector that catches yesterday and misses tomorrow.
This reads every `evt=http` line colt-web has written, groups it by source, and reports which
sources behaved like attacks and WHAT they asked for — so the next detector is written from
evidence rather than from imagination.

READ-ONLY. One ssh, `docker exec colt-web` reading its own log. Nothing is changed on the droplet.

    python analyse_attacks.py                 # live, from the droplet
    python analyse_attacks.py --local FILE    # from a copy
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
SSH = ["-o", "ConnectTimeout=15", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]


def fetch():
    cmd = ["ssh"] + SSH + ["%s@%s" % (USER, HOST),
           "docker exec colt-web sh -c 'cat /var/log/colt/events.log 2>/dev/null | tail -200000'"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    if r.returncode != 0:
        sys.exit("[X] could not read the event log: %s" % (r.stderr or "")[:300])
    return r.stdout


# Behaviour classes. Each is a candidate DETECTOR: if a class is common and the shield does not
# already cover it, that is the gap.
# THE TABLE MOVED to webapp/backend/app/shield.py so the container can name a lane too.
# Imported, never re-declared: one vocabulary for the detector, the feed and this analysis.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp", "backend"))
from app.shield import CLASSES            # noqa: E402


from app.shield import classify   # noqa: E402,F811  (one implementation)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="read a copy instead of the droplet")
    ap.add_argument("--min-hits", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    raw = open(a.local, encoding="utf-8", errors="replace").read() if a.local else fetch()

    by_ip = collections.defaultdict(lambda: {
        "hits": 0, "404": 0, "401": 0, "paths": collections.Counter(),
        "uas": set(), "countries": set(), "classes": collections.Counter(), "first": "", "last": ""})
    alerts = collections.Counter()
    total = 0
    for ln in raw.splitlines():
        try:
            j = json.loads(ln)
        except Exception:
            continue
        if j.get("evt") == "security_alert":
            alerts[j.get("rule", "?")] += 1
            continue
        if j.get("evt") != "http":
            continue
        total += 1
        ip = j.get("ip") or "-"
        d = by_ip[ip]
        d["hits"] += 1
        st = str(j.get("status", ""))
        if st == "404":
            d["404"] += 1
        if st in ("401", "403"):
            d["401"] += 1
        p = j.get("path") or "/"
        d["paths"][p] += 1
        for c in classify(p):
            d["classes"][c] += 1
        if j.get("browser") or j.get("os"):
            d["uas"].add("%s/%s" % (j.get("browser"), j.get("os")))
        if j.get("country"):
            d["countries"].add(j["country"])
        d["last"] = j.get("ts", d["last"])
        d["first"] = d["first"] or j.get("ts", "")

    # HOSTILE = asked for something no visitor asks for, or rotated its identity, or 404-stormed.
    hostile = {ip: d for ip, d in by_ip.items()
               if d["classes"] or len(d["uas"]) >= 3 or d["404"] >= a.min_hits}
    if a.json:
        print(json.dumps({ip: {k: (dict(v) if isinstance(v, collections.Counter)
                                   else sorted(v) if isinstance(v, set) else v)
                               for k, v in d.items()} for ip, d in hostile.items()},
                         indent=2, default=str))
        return 0

    print("=" * 78)
    print("  WHAT HAS ACTUALLY HIT cybergod.ai")
    print("=" * 78)
    print("  %d http events · %d distinct sources · %d behaved like scanners"
          % (total, len(by_ip), len(hostile)))
    if alerts:
        print("  alerts already raised: %s"
              % ", ".join("%s x%d" % (k, v) for k, v in alerts.most_common()))

    cls_total = collections.Counter()
    for d in hostile.values():
        for c in d["classes"]:
            cls_total[c] += 1
    print("\n  ATTACK CLASSES SEEN (distinct sources per class)")
    if not cls_total:
        print("    none — no source asked for anything a visitor would not")
    for c, n in cls_total.most_common():
        print("    %-14s %d source(s)" % (c, n))

    print("\n  TOP SOURCES")
    for ip, d in sorted(hostile.items(), key=lambda kv: -kv[1]["hits"])[:15]:
        print("    %-22s %4d req  %3d x404  %d UA(s)  %s"
              % (ip, d["hits"], d["404"], len(d["uas"]),
                 ",".join(sorted(d["countries"])) or "-"))
        print("       classes: %s" % (", ".join(sorted(d["classes"])) or "-"))
        for p, n in d["paths"].most_common(6):
            print("         %4dx %s" % (n, p[:96]))

    # THE POINT OF THE WHOLE SCRIPT: which classes the shield already stops, and which it does not.
    sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
    try:
        from app import shield
        print("\n  COVERAGE — would the shield recognise these paths today?")
        gaps = collections.Counter()
        examples = collections.defaultdict(list)
        for ip, d in hostile.items():
            for p in d["paths"]:
                if classify(p) and not (shield.is_probe_path(p) or shield.is_honeytoken(p)):
                    for c in classify(p):
                        gaps[c] += 1
                        if p not in examples[c]:
                            examples[c].append(p)
        if not gaps:
            print("    every hostile path seen so far is already recognised")
        else:
            # NAME THE PATHS. The first version reported "php_probe 235 path(s)" and nothing else,
            # and I spent a cycle assuming the .php detector was broken when it was not: the real
            # cause was that /api/ is exempt, so ANY probe under /api/ was invisible. A diagnostic
            # that does not name its subject sends the next investigation down the wrong road.
            print("    NOT RECOGNISED — these are the detectors still to write:")
            for c, n in gaps.most_common():
                print("      %-14s %d path(s)" % (c, n))
                for ex in examples[c][:5]:
                    print("           %s" % ex[:100])
    except Exception as e:
        print("\n  [!] could not load the shield to compare (%s)" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
