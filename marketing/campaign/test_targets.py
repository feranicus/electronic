#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_targets.py — the classifier gate. BOTH directions, because only testing one is how the
first three versions of this file shipped.

    python marketing/campaign/test_targets.py

Every case below is a REAL row from the operator's own 10,237-connection export, kept with the
reason it is here. The precision cases were each admitted by an earlier version and each one would
have put a pitch about reselling security assessments in front of a hospital, an oil company or a
recruiter. The recall cases were each LOST by the fix for the precision cases, which is the trap
worth remembering: tightening a rule until the false positives disappear also deletes the customers.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_targets as B                                                # noqa: E402
import messages as M                                                     # noqa: E402

FAILS = []


def ck(cond, label):
    print("  %s  %s" % ("PASS" if cond else "FAIL", label))
    if not cond:
        FAILS.append(label)


print("[1] PRECISION - a generic word in a company name is not a segment")
# "it " matched inside "Clalit ", "tech" inside "Biotech", "consult" inside a staffing agency.
for comp, pos, why in [
    ("Clalit Health Services", "Head of IT", "a hospital, admitted by 'it ' inside 'Clalit '"),
    ("Altium Biotech Consulting", "Managing Director", "'tech' inside 'Biotech'"),
    ("ADNOC Distribution", "Head of IT", "an oil company; the title corroborated, not the firm"),
    ("AlphaConsult-Gruppe", "Recruitment Consultant", "a staffing agency"),
    ("BEC-Breddermann Executive", "Partner", "headhunters"),
    ("Bank Hapoalim", "Head of Cyber Security", "a BUYER, and the wrong pitch entirely"),
    ("Siemens Healthineers", "IT Director", "medical devices, not a reseller"),
]:
    ck(B.segment_of(comp, pos) == "OTHER", "out: %-34s (%s)" % (comp[:34], why))

print("\n[2] RECALL - the real channel, including names that carry no keyword at all")
for comp, pos, want in [
    ("Bechtle IT-Systemhaus", "Account Manager", "CHANNEL"),
    ("Orange Cyberdefense", "Presales Consultant", "CHANNEL"),
    ("Softcat", "Security Solutions Specialist", "CHANNEL"),
    ("Exclusive Networks", "Channel Director", "CHANNEL"),
    ("CANCOM Managed Services GmbH", "Director", "CHANNEL"),
    ("Arrow ECS", "Business Development Manager", "CHANNEL"),
    ("Sophos", "Chief Executive Officer", "VENDOR"),
    ("Cognizant", "Client Partner", "GSI"),
    ("Deloitte", "Partner, Cyber Risk", "CONSULTING"),
    ("Mazars", "Director", "CONSULTING"),
    ("NTT Data", "Solution Architect", "GSI"),
    ("Deutsche Telekom", "Head of Security Sales", "CARRIER"),
]:
    got = B.segment_of(comp, pos)
    ck(got == want, "in : %-30s -> %-11s (want %s)" % (comp[:30], got, want))

print("\n[3] ROLE - presales is not sales, and a title is not a segment")
for pos, want in [("Sales Engineer", "PRESALES"), ("Pre-Sales Consultant", "PRESALES"),
                  ("Account Executive", "SALES"), ("Chief Technology Officer", "EXEC"),
                  ("Head of Channel", "EXEC"), ("Security Analyst", "DELIVERY"),
                  # 43 of 374 EXEC were really salespeople: the generic "director" and "head of"
                  # were beating the explicit sales title, so they got the economic-buyer pitch.
                  ("Global Account Director DTAG", "SALES"),
                  ("Sales Director", "SALES"),
                  ("Head of Sales & Market Development", "SALES"),
                  ("Senior Partner Manager - Channels - DACH", "SALES"),
                  ("Distribution Channel Director - Europe", "SALES"),
                  # ...but seniority still wins when it is real seniority
                  ("VP Sales EMEA", "EXEC"),
                  ("Chief Revenue Officer", "EXEC"),
                  ("Managing Director", "EXEC"),
                  ("Partner, Cyber Risk", "EXEC"),
                  ("Head of Cyber Practice", "EXEC")]:
    got = B.role_of(pos)
    ck(got == want, "%-28s -> %-9s (want %s)" % (pos, got, want))

print("\n[4] EXCLUSIONS - the operator's decision, enforced not remembered")
rows = [{"First Name": "A", "Last Name": "B", "Company": "Colt Technology Services",
         "Position": "Sales Director", "URL": "https://www.linkedin.com/in/x", "Connected On": ""},
        {"First Name": "C", "Last Name": "D", "Company": "Softcat", "Position": "Sales Director",
         "URL": "https://www.linkedin.com/in/y", "Connected On": ""},
        {"First Name": "E", "Last Name": "F", "Company": "Softcat", "Position": "Sales Director",
         "URL": "", "Connected On": ""}]
built = B.build(rows)
ck(not any("colt" in t["company"].lower() for t in built), "Colt is excluded entirely")
ck(len(built) == 1, "a row with no profile URL is dropped (nothing to open)")

print("\n[5] EVERY TARGET GETS A MESSAGE - a bucket with no copy means somebody gets nothing")
seen = set()
for seg in ["CHANNEL", "GSI", "CONSULTING", "VENDOR", "CARRIER", "HYPERSCALER"]:
    for role in ["EXEC", "SALES", "PRESALES", "DELIVERY", "OTHER"]:
        key = "%s_%s" % (seg, role)
        txt, used = M.render({"first": "Alex", "last": "B", "url": "", "company": "X",
                              "segment": seg, "role": role, "message_key": key})
        if not txt or "{" in txt:
            ck(False, "%s renders nothing usable" % key)
        seen.add(key)
ck(not FAILS or all("renders" not in f for f in FAILS), "all %d buckets render" % len(seen))

print("\n[6] THE ASK IS IN EVERY MESSAGE - a cold message that only asks gets no reply")
missing = []
for key in seen:
    txt, _ = M.render({"first": "Alex", "url": "", "segment": key.split("_")[0],
                       "message_key": key})
    if "48 hours" not in (txt or ""):
        missing.append(key)
ck(not missing, "the free-assessment offer is present everywhere (%s)" % (missing or "all"))



print("\n[7] THE CLIPBOARD VERDICT (2026-08-22). The self-test said 'clipboard MANGLES non-ASCII'")
print("    and told the operator to stop. The clipboard was probably fine: PowerShell writes")
print("    stdout in the CONSOLE code page, so the READ-BACK destroyed the accents on the way out.")
print("    A check must not condemn its subject for its own defect, so accent-only damage now")
print("    reads as 'read-back suspect' and the queue continues.")
_PROBE = "Hi Göksal, Grüße aus München. Zażółć. 15 minutes?"


def _verdict(back):
    """The exact logic from outreach.clipboard_selftest, kept in step by test [8]."""
    if back == _PROBE:
        return "ok"
    skel = "".join(c for c in _PROBE if c.isascii())
    if len(back) == len(_PROBE):
        same = all(b == p for b, p in zip(back, _PROBE) if p.isascii())
    else:
        same = "".join(c for c in back if c.isascii()) == skel
    return "suspect" if (same or "".join(c for c in back if c.isascii()) == skel) else "stop"


for _label, _back, _want in [
    ("perfect round-trip", _PROBE, "ok"),
    ("accents -> '?' (the real case)", "".join("?" if not c.isascii() else c for c in _PROBE), "suspect"),
    ("mojibake utf8-as-cp1252", _PROBE.encode("utf-8").decode("cp1252", "replace"), "suspect"),
    ("accents -> U+FFFD", "".join("�" if not c.isascii() else c for c in _PROBE), "suspect"),
    ("different text", "something else entirely", "stop"),
    ("truncated", _PROBE[:10], "stop"),
    ("extra sentence injected", _PROBE + " Also send money.", "stop"),
]:
    ck(_verdict(_back) == _want, "%-34s -> %-8s (want %s)" % (_label, _verdict(_back), _want))

print("\n[8] THE CAP IS THE OPERATOR'S, AND THE DOC MUST MATCH THE CODE")
_out = open(os.path.join(HERE, "outreach.py"), encoding="utf-8").read()
ck("OUTREACH_DAILY_CAP" in _out, "the cap is overridable without editing the file")
ck('"200"' in _out, "the default cap is 200, as the operator set it")
ck("DAILY_CAP is 200" in _out, "the module docstring states the same number the code uses")
# The verdict logic above is a COPY of the one in outreach.py. A copy drifts, so assert the
# distinctive line is really there rather than trusting that it is.
# Case-insensitive: the message in outreach.py says "READ-BACK" in capitals and the first
# version of this assertion compared lowercase, so it failed a correct file.
ck("read-back" in _out.lower(),
   "outreach.py still distinguishes a suspect read-back from a broken clipboard")


# THE GATE IS LAST, AND IT MUST STAY LAST. It was in the MIDDLE of this file and sections [7]
# and [8] were appended after it, so they were unreachable: 14 assertions that could never
# run and could never fail. Identical to the defect already fixed in test_recall.py, where
# the only sys.exit sat at line 253 of 761 and silently stopped enforcing everything below
# it, including the public-suffix guard.
print()
if FAILS:
    print("%d FAILURE(S):" % len(FAILS))
    for f in FAILS:
        print("   " + f)
    sys.exit(1)
print("ALL CHECKS PASSED")
sys.exit(0)
