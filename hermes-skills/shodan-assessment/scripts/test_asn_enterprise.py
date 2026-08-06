#!/usr/bin/env python3
"""
test_asn_enterprise.py — the Royal Bank of Canada ASN-discovery regression (2026-08).

RBC announces at least TWELVE autonomous systems (bgp.he.net: AS400736, AS400717, AS399410,
AS399409, AS398669, AS36256, AS32176, AS20069, AS16731, AS16730, AS16729, AS11544). The engine
found TWO, both from PeeringDB, and reported "scope: ASN AS399409,AS16729 - 1 prefixes".

ROOT CAUSE: every source was RIPE/DACH-shaped.
  ripe_db   covers only the RIPE region  -> RBC is ARIN, returns nothing
  caida     returned nothing
  bgpview   does not resolve in the container (a known, documented outage)
  peeringdb lists only networks that PEER PUBLICLY -> 2 of 12
That is fine for a Mittelstand target and structurally blind on any North American, Asian or
Gulf enterprise, i.e. on exactly the accounts worth the most.

FIX: RIPEstat searchcomplete, which indexes EVERY RIR. This test runs the real captured API
response through the parser, so it verifies behaviour without needing the network.

    python test_asn_enterprise.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asn_sources as A                                                      # noqa: E402

FAILS = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


# The REAL response from stat.ripe.net searchcomplete?resource=RBC, captured 2026-08-06.
REAL = {"data": {"categories": [{"category": "ASNs", "suggestions": [
    {"value": "AS7961",   "description": "RBC - Raw Bandwidth Communications, Inc."},
    {"value": "AS11544",  "description": "RBC1-ASN6 - Royal Bank of Canada"},
    {"value": "AS19416",  "description": "RBC-NY - RBC CAPITAL MARKETS CORPORATION"},
    {"value": "AS36256",  "description": "RBC-CAN-01 - Royal Bank of Canada"},
    {"value": "AS36333",  "description": "RBCORP - Republic Bank & Trust Company"},
    {"value": "AS38378",  "description": "RBCN-NET - Bosch (China) Investment Ltd."},
    {"value": "AS198519", "description": "RBcz Raiffeisenbank a.s."},
    {"value": "AS142613", "description": "RBCC-AS-AP - Red Bend Catholic College"},
    {"value": "AS395338", "description": "RBCCC-01 - RBC Convention Centre Winnipeg"},
    {"value": "AS398669", "description": "RBC-CA-TOR - Royal Bank of Canada"},
    {"value": "AS399409", "description": "RBC-CANADA-2 - Royal Bank of Canada"},
    {"value": "AS399410", "description": "RBC-SYDNEY - Royal Bank of Canada"},
    {"value": "AS400717", "description": "RBC-SG - Royal Bank of Canada"},
    {"value": "AS400736", "description": "RBC-CL-2 - Royal Bank of Canada"},
]}]}}

print("== the acronym is derived, because searchcomplete matches the AS HANDLE ==")
t = A._terms("Royal Bank of Canada")
check("RBC" in t, "acronym RBC derived from the company name: %s" % t)
check("Royal Bank of Canada" in t, "the full name is still queried")
check(len(t) <= 4, "query variants are bounded (%d)" % len(t))

print("\n== the real API response is parsed, and only RBC's own ASNs survive ==")
A._get = lambda url, **k: REAL          # no network: replay the captured response
del A.ERRORS[:]
got = set(A.ripestat("Royal Bank of Canada"))

for n in (11544, 36256, 398669, 399409, 399410, 400717, 400736):
    check(n in got, "AS%d (Royal Bank of Canada) is discovered" % n)

for n, who in ((7961, "Raw Bandwidth Communications"), (36333, "Republic Bank & Trust"),
               (38378, "Bosch China"), (198519, "Raiffeisenbank"),
               (142613, "Red Bend Catholic College"), (395338, "RBC Convention Centre")):
    check(n not in got, "AS%d (%s) is NOT adopted - the handle matches, the holder does not" % (n, who))

check(len(got) >= 7, "at least 7 ASNs found where the old chain found 2 (got %d)" % len(got))

print("\n== the cap no longer truncates an enterprise estate ==")
import inspect                                                               # noqa: E402
src = inspect.getsource(A.discover)
check("cap=40" in src, "discover() caps at 40, not 12 - a bank legitimately has dozens")
check("ripestat" in src, "ripestat is wired into the source chain")
check(src.index("ripestat") < src.index("ripe-db"),
      "the global source runs FIRST, so a RIPE-only failure cannot decide the answer")

print("\n== a DACH target must not regress ==")
t2 = A._terms("abakus TK Service GmbH")
check("abakus TK Service GmbH" in t2, "the full name is queried for a German SMB too")
check(A._relevant("abakus TK Service GmbH", "abakus TK Service GmbH"), "exact holder still matches")
check(not A._relevant("Royal Bank of Canada", "RBC CAPITAL MARKETS CORPORATION"),
      "a differently-named legal entity is not silently adopted")

print("\n" + ("FAILED: %d" % len(FAILS) if FAILS else "ALL ENTERPRISE ASN CHECKS PASSED"))
for f in FAILS:
    print("   - " + f)
sys.exit(1 if FAILS else 0)
