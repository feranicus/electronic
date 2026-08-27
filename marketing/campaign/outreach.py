#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""outreach.py — ONE command to work the campaign queue.

    python marketing/campaign/outreach.py                 # work today's queue
    python marketing/campaign/outreach.py --dry-run       # see the queue, open nothing
    python marketing/campaign/outreach.py --segment GSI   # one segment
    python marketing/campaign/outreach.py --limit 15
    python marketing/campaign/outreach.py --report        # what has been sent so far

WHAT IT DOES, and deliberately what it does NOT.

For each target in priority order it opens their LinkedIn profile in your normal browser, puts the
tailored message on your clipboard, prints the attachments to drag in, and waits. You read it, you
decide, you press send. Then you type s, k or q and it logs the outcome and moves on.

IT NEVER TOUCHES LINKEDIN ITSELF. No headless browser, no DOM, no injected clicks, no typing into
their page. LinkedIn's User Agreement section 8.2 prohibits automated access and automated
messaging, and enforcement is account termination. The asset this campaign runs on is a
ten-thousand-connection profile built over a career; a tool that risks it to save four seconds of
pasting is a bad trade, and it is not the tool I am willing to write.

There is a second reason, and it is the better one. A message a human read before sending is a
better message. The queue removes the tedious part, which is deciding who is next and what to say.
It leaves the part that actually earns the reply.

THE LOG IS THE POINT. sent.jsonl records who, when, which message and the outcome. It is what stops
a second run contacting the same person, it survives the terminal being closed, and it is the only
honest answer to "what did we actually send". Nothing is ever removed from it.

RATE. LinkedIn does not publish a message limit and it varies by account age and behaviour.
DAILY_CAP is 200 (operator decision, raised from an over-cautious 25). Everything here is a human
paste-and-click to an existing 1st-degree connection, which is the traffic LinkedIn tolerates most;
the tight limits are on connection REQUESTS and on automation, and this tool does neither. If
replies dry up or a warning appears, drop the cap rather than push through.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import messages as MSG                                                   # noqa: E402

TARGETS = os.path.join(HERE, "targets.json")
SENT = os.path.join(HERE, "sent.jsonl")
# THE CAP. Operator decision 2026-08-22: raised from 25 to 200. Every send here is a HUMAN
# paste-and-click on a message to an existing 1st-degree connection, which is the traffic
# LinkedIn tolerates most; the tight limits are on connection REQUESTS and on automation, and
# this tool does neither. Overridable per run with --limit or the OUTREACH_DAILY_CAP env var.
# The honest risk that remains: LinkedIn does not publish a number and it varies by account, so
# if replies stop or a warning appears, drop it rather than push through.
DAILY_CAP = int(os.environ.get("OUTREACH_DAILY_CAP", "200"))

# TWO ATTACHMENTS, NOT FIVE. A first cold message gets one document explaining the idea and one
# artifact proving it. The partner agreements, the SLA and the DPA are what you send when somebody
# says yes; leading with a contract pack answers a question nobody asked yet.
#
# The findings example is the Rosatom FINDINGS deck. OPERATOR DECISION 2026-08-22: send it as-is.
# Recorded because it is a decision and not a default. It is a real organisation's externally
# observable exposure, derived entirely from public sources with no packet sent to them, and it is
# going to third parties. That is the operator's call and he made it explicitly. What matters is
# that the framing in the message stays true: passive OSINT, public data, no access of any kind.
# A PDF, NOT THE DECK. Most of these are read on a phone inside LinkedIn, where a PDF opens inline
# and a .pptx has to be downloaded and opened in another app. That extra step is where a cold
# message dies. The pitch deck is what you send after they reply.
WANT = [
    ("the concept", "Cybergod_OnePager_EN.pdf"),
    ("findings example", "rosatom.ru_Shodan_Findings.pptx"),
]
# Searched in order. These are the folders the operator actually keeps things in, and the files
# live OUTSIDE this repository, so hardcoding one path is how the queue starts printing MISSING
# next to a document that is sitting on the disk. Same rule as asking docker where a mount comes
# from rather than assuming the production path.
SEARCH_DIRS = [
    HERE,
    os.path.join(ROOT, "marketing"),
    os.path.join(ROOT, "shodan-out"),
    os.path.join(os.path.expanduser("~"), "Downloads", "cybergod partnership"),
    os.path.join(os.path.expanduser("~"), "Downloads", "Rosatom"),
    os.path.join(os.path.dirname(ROOT), "cybergod partnership"),
    os.path.join(os.path.dirname(ROOT), "Rosatom"),
]


def resolve(fname):
    """Find an attachment by name across the known folders. None means it is genuinely absent."""
    for d in SEARCH_DIRS:
        p = os.path.join(d, fname)
        if os.path.exists(p):
            return p
    return None


def _clip(text):
    """Put the message on the clipboard, with the accents intact.

    WINDOWS IS THE AWKWARD ONE. `clip.exe` decodes its stdin using the CONSOLE CODE PAGE, which on
    a German Windows is cp1252, so piping UTF-8 or bare UTF-16 turns "Hi Göksal," into mojibake and
    the first thing the recipient sees is their own name spelled wrong. PowerShell's Set-Clipboard
    reading a UTF-8 file has no encoding to guess, so that is the primary path. clip.exe with an
    explicit BOM is the fallback, because modern clip does honour a BOM.

    This is the same lesson the deploy scripts already pay for: the byte that ends a line, and the
    codec that reads a pipe, are the platform's business and have to be stated rather than assumed.
    """
    if os.name == "nt":
        # BASE64 THROUGH ARGV, DECODED AS UTF-8 INSIDE POWERSHELL. There is no encoding to guess
        # anywhere on this path: base64 is pure ASCII so the command line cannot mangle it, and
        # PowerShell reconstructs the exact bytes. The previous version wrote a temp file and had
        # PowerShell re-read it, which added a file-encoding step for no benefit, and before that
        # it piped to clip.exe, which decodes stdin using the console code page and turns "Göksal"
        # into "G?ksal" on a German Windows.
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        ps = ("$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%s'));"
              "Set-Clipboard -Value $t" % b64)
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                               capture_output=True)
            if r.returncode == 0:
                return True
        except OSError:
            pass
        try:                                   # fallback: clip.exe, BOM first so it stops guessing
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            p.communicate(b"\xff\xfe" + text.encode("utf-16-le"))
            return p.returncode == 0
        except OSError:
            return False
    for cmd in (["pbcopy"], ["xclip", "-selection", "clipboard"], ["wl-copy"]):
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            if p.returncode == 0:
                return True
        except (OSError, FileNotFoundError):
            continue
    return False


def clipboard_selftest():
    """Write a string with real accents and READ IT BACK. Reproduce the thing, do not reason about
    it: a clipboard that silently mangles "Göksal" spells a stranger's name wrong in the first line
    of the first message they ever get from us, and nothing else in this script would notice."""
    probe = "Hi Göksal, Grüße aus München. Zażółć. 15 minutes?"
    if not _clip(probe):
        print("  [X] clipboard: could not write. You will have to copy each message by hand.")
        return False
    back = None
    try:
        if os.name == "nt":
            # THE READ-BACK WAS THE BROKEN HALF. PowerShell writes stdout using the CONSOLE output
            # encoding (cp850/cp1252 on a German Windows), not UTF-8, so `Get-Clipboard -Raw` piped
            # into Python mangles every accent on the way OUT even when the clipboard is perfect.
            # That is a check condemning its subject for the check's own defect, which this
            # repository has now paid for several times. Two fixes: force the console encoding to
            # UTF-8 first, and return the answer as BASE64 so no encoding step remains at all.
            ps = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
                  "$c=Get-Clipboard -Raw;"
                  "[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($c))")
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                               capture_output=True, text=True, encoding="ascii", errors="replace")
            raw = (r.stdout or "").strip()
            try:
                back = base64.b64decode(raw).decode("utf-8").strip() if raw else None
            except Exception:
                back = None
        else:
            for cmd in (["pbpaste"], ["xclip", "-selection", "clipboard", "-o"], ["wl-paste"]):
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       encoding="utf-8", errors="replace")
                    if r.returncode == 0:
                        back = (r.stdout or "").strip()
                        break
                except (OSError, FileNotFoundError):
                    continue
    except OSError:
        pass
    if back is None:
        print("  [!] clipboard: written, but it could not be read back to verify. Paste one "
              "message and check an accent by eye before trusting the rest.")
        return True
    if back == probe:
        print("  [OK] clipboard round-trip verified, accents intact")
        return True
    # A MISMATCH IS NOT AUTOMATICALLY THE CLIPBOARD'S FAULT, and saying it is cost real messages.
    # If only the ACCENTS differ while the ASCII skeleton matches, the far likelier explanation is
    # an encoding step in the verification, not a broken clipboard. Say which, and never tell the
    # operator to stop on evidence that weak.
    #
    # COMPARE THE SKELETON PROPERLY. The first version did
    #     "".join(c for c in back if c.isascii()) == "".join(c for c in probe if c.isascii())
    # which fails for the commonest corruption of all: an accent replaced by "?" survives the
    # isascii() filter and shows up as an extra character, so accent-only damage was reported as
    # "different TEXT" and the operator was told to stop. Drop the characters that sat where the
    # probe had an accent, then compare. Covers both substitution (ö -> ?) and mojibake (ö -> Ã¶).
    skeleton = "".join(c for c in probe if c.isascii())
    if len(back) == len(probe):
        same_ascii = all(b == p for b, p in zip(back, probe) if p.isascii())
    else:
        same_ascii = "".join(c for c in back if c.isascii()) == skeleton
    if same_ascii or "".join(c for c in back if c.isascii()) == skeleton:
        print("  [!] clipboard: the ASCII text round-trips but the accents do not survive the "
              "READ-BACK. That is usually this check, not your clipboard.")
        print("      Paste into the first message and look at the name before sending it.")
        return True
    print("  [X] clipboard is returning different TEXT, not just different accents.")
    print("      Sent: %r" % probe[:40])
    print("      Got : %r" % back[:40])
    print("      Copy the message text by hand until this is resolved.")
    return False


def ensure_targets():
    """Build or refresh the target list. ONE command for the whole campaign: the operator should
    never have to remember that build_targets.py exists, and a stale list is how somebody who
    changed jobs last month gets pitched at their old company."""
    csvs = [os.path.join(d, "Connections.csv") for d in SEARCH_DIRS + [HERE]]
    csvs = [p for p in csvs if os.path.exists(p)]
    fresh = (os.path.exists(TARGETS) and csvs
             and os.path.getmtime(TARGETS) >= os.path.getmtime(csvs[0]))
    if fresh:
        return
    if not csvs:
        if os.path.exists(TARGETS):
            print("  [!] no Connections.csv found, working from the existing list")
            return
        sys.exit("[X] no Connections.csv in any of:\n    " + "\n    ".join(SEARCH_DIRS))
    print("  building the target list from %s ..." % csvs[0])
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_targets.py"),
                        "--csv", csvs[0], "--out", HERE],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("[X] build_targets failed:\n" + (r.stderr or r.stdout))
    for ln in (r.stdout or "").splitlines():
        if ln.startswith(("connections read", "in-scope targets")):
            print("  " + ln)


def _load_sent():
    """Everyone already contacted, by profile URL. Absent file means nobody."""
    done = {}
    if os.path.exists(SENT):
        for ln in open(SENT, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
                done[r["url"]] = r
            except Exception:
                continue                       # a half-written line must not stop the campaign
    return done


def _log(rec):
    with open(SENT, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()                             # crash-safe: the record is on disk before the next open


def _today_count(done):
    d = datetime.now(timezone.utc).date().isoformat()
    return sum(1 for r in done.values()
               if r.get("outcome") == "sent" and (r.get("ts") or "").startswith(d))


def report(done):
    sent = [r for r in done.values() if r.get("outcome") == "sent"]
    print("contacted : %d" % len(sent))
    print("skipped   : %d" % sum(1 for r in done.values() if r.get("outcome") == "skip"))
    if not sent:
        return
    from collections import Counter
    for label, key in (("by segment", "segment"), ("by role", "role")):
        print("\n%s:" % label)
        for k, v in Counter(r.get(key) for r in sent).most_common():
            print("   %-12s %d" % (k, v))
    print("\nlast 10:")
    for r in sorted(sent, key=lambda x: x.get("ts", ""))[-10:]:
        print("   %s  %-26s %s" % (r.get("ts", "")[:16], (r.get("company") or "")[:26], r.get("name")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=DAILY_CAP)
    ap.add_argument("--segment", help="CHANNEL GSI CONSULTING VENDOR CARRIER HYPERSCALER")
    ap.add_argument("--role", help="EXEC SALES PRESALES")
    ap.add_argument("--dry-run", action="store_true", help="show the queue, open nothing")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--pick", help="match a name, company or profile URL. For a deliberate first "
                                   "send to somebody you choose rather than whoever is top.")
    a = ap.parse_args()

    ensure_targets()
    targets = json.load(open(TARGETS, encoding="utf-8"))
    done = _load_sent()

    if a.report:
        report(done)
        return

    q = [t for t in targets if t["url"] not in done]
    if a.segment:
        q = [t for t in q if t["segment"] == a.segment.upper()]
    if a.role:
        q = [t for t in q if t["role"] == a.role.upper()]
    if a.pick:
        k = a.pick.lower()
        q = [t for t in q if k in (t["first"] + " " + t["last"] + " " + t["company"] + " "
                                   + t["url"]).lower()]
        if not q:
            sys.exit("[X] --pick %r matched nobody who has not already been contacted." % a.pick)

    already = _today_count(done)
    room = max(0, DAILY_CAP - already)
    if room == 0 and not a.dry_run:
        sys.exit("[i] %d already sent today, which is the cap. Come back tomorrow." % already)
    q = q[:min(a.limit, room if not a.dry_run else a.limit)]

    # The one-pager is generated, so build it rather than reporting it missing. One command.
    if not resolve("Cybergod_OnePager_EN.pdf"):
        subprocess.run([sys.executable, os.path.join(HERE, "build_onepager.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    found = [(label, resolve(fn), fn) for label, fn in WANT]
    print("=" * 74)
    print("  cybergod.ai outreach queue")
    print("=" * 74)
    print("  targets remaining : %d" % len([t for t in targets if t["url"] not in done]))
    print("  this session      : %d   (already sent today: %d, cap %d)" % (len(q), already, DAILY_CAP))
    print("  attach to each message:")
    for label, path, fn in found:
        print("     %-8s %-17s %s" % ("OK" if path else "MISSING", label, path or fn))
    if any(p is None for _l, p, _f in found):
        print("     ^ searched: %s" % " | ".join(SEARCH_DIRS))
    print()

    if not a.dry_run:
        clipboard_selftest()
        print()

    if a.dry_run:
        for t in q:
            print("  %-11s %-8s %-30s %-24s %s"
                  % (t["segment"], t["role"], t["company"][:30],
                     (t["first"] + " " + t["last"])[:24], t["url"]))
        print("\n  dry run, nothing opened and nothing logged.")
        return

    for n, t in enumerate(q, 1):
        txt, key = MSG.render(t)
        if not txt:
            print("  [skip] %s: %s" % (t["company"], key))
            continue
        name = ("%s %s" % (t["first"], t["last"])).strip()
        print("-" * 74)
        print("  %d/%d  %s   %s" % (n, len(q), name, t["url"]))
        print("        %s | %s | %s" % (t["segment"], t["role"], t["company"][:40]))
        print("        template: %s   (%d chars)" % (key, len(txt)))
        print()
        print("\n".join("        " + l for l in txt.splitlines()))
        print()
        ok = _clip(txt)
        webbrowser.open(t["url"])
        print("        ---- in the browser ----")
        print("        1. Message  ->  paste  %s"
              % ("(Ctrl+V, it is on your clipboard)" if ok
                 else "BY HAND, the clipboard failed, copy the text above"))
        print("        2. check the name reads correctly, accents included")
        for label, path, fn in found:
            print("        3. attach   %-17s %s" % (label, path or "MISSING: " + fn))
        print("        4. send")

        try:
            ans = input("        [s]ent  [k]skip  [q]uit > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  stopped. Nothing lost, the log is written as you go.")
            return
        if ans.startswith("q"):
            print("  stopped at your request.")
            return
        _log({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "url": t["url"], "name": name, "company": t["company"],
              "segment": t["segment"], "role": t["role"], "template": key,
              "outcome": "sent" if ans.startswith("s") else "skip"})
        time.sleep(1)                          # human pace, not a burst

    print("-" * 74)
    print("  session done. `--report` for the running totals.")


if __name__ == "__main__":
    main()
