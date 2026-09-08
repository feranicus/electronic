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

print("\n== bgp.he.net: the source that answers when every JSON API is down (dcsolution.io) ==")
# The real failure: ripestat, ripe-db, caida, peeringdb AND bgpview all returned '-' on the
# dcsolution.io run, so the whole BGP/NIS2 half went blind on a hosting operator that plausibly
# announces its own space. bgp.he.net is HTML on a CDN and indexes every RIR, so it answers when
# the JSON hosts do not. This is the search-result table shape it renders, one row per AS.
# Seeded with the ONE brand token the engine actually derives ([auto] brand tokens: dcsolution),
# not a hand-spelled 'DC Solution'. The corroboration is strict about token boundaries by design --
# that is what keeps a co-tenant off the estate -- so the seed spelling is what the holders are
# matched against. DDOS-GUARD is included because it is the REAL holder of dcsolution's edge IPs and
# must NOT be adopted: the customer sits behind it, it does not own that AS.
HE_HTML = """
<table id="search"><tbody>
<tr><td><a href="/AS204601">AS204601</a></td><td>DCSOLUTION LTD</td><td>1,024</td></tr>
<tr><td><a href="/AS205123">AS205123</a></td><td>DCSOLUTION Networks</td><td>256</td></tr>
<tr><td><a href="/AS204601">AS204601</a></td><td>DCSOLUTION LTD</td><td>dup row, must dedupe</td></tr>
<tr><td><a href="/AS57724">AS57724</a></td><td>DDOS-GUARD LTD</td><td>the scrubber, not the target</td></tr>
<tr><td><a href="/AS12345">AS12345</a></td><td>Datacenter Solutions Unrelated Inc</td><td>512</td></tr>
<tr><td><a href="/AS49505">AS49505</a></td><td>Selectel / other tenant on the prefix</td></tr>
</tbody></table>
"""
A._get_html = lambda url, **k: HE_HTML     # no network: replay the captured HTML
del A.ERRORS[:]
he_list = A.he_net("dcsolution")
he = set(he_list)
check(204601 in he, "AS204601 (DCSOLUTION LTD) is parsed out of the HTML table")
check(205123 in he, "AS205123 (DCSOLUTION Networks) is parsed - a second AS on the same holder")
check(he_list.count(204601) == 1, "a duplicate row does not produce a duplicate ASN")
check(57724 not in he, "AS57724 (DDOS-GUARD) is NOT adopted - the customer sits behind it, does not own it")
check(12345 not in he, "'Datacenter Solutions Unrelated Inc' is NOT adopted - holder does not corroborate")
check(49505 not in he, "a co-tenant's AS on the same prefix is NOT adopted")
check(A.he_net("nonexistent-brand-xyz") == [], "no holder match -> nothing, never a substring grab")

print("\n== he_net is wired as a global peer, and total failure still reads as not-ok ==")
srcd = inspect.getsource(A.discover)
check("he_net" in srcd, "he_net is in the source chain")
check(srcd.index("he_net") < srcd.index("bgpview"),
      "he_net runs before the flaky bgpview it backstops")
check("failed < len(sources)" in srcd,
      "ok is derived from the source count, so adding a source cannot shift the threshold")
# with EVERY source raising, ok must be False (the exact dcsolution failure mode)
def _boom(*a, **k):
    raise OSError("[Errno -5] No address associated with hostname")
for nm in ("ripestat", "he_net", "ripe_db", "caida", "peeringdb", "bgpview"):
    setattr(A, nm, _boom)
res = A.discover("anything")
check(res["ok"] is False, "every source down -> ok=False (absence of evidence, never 'no ASN')")
check(res["asns"] == [], "...and no ASN is invented from a failed run")

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
