#!/usr/bin/env python3
"""
test_enrich_grounding.py - AI prose must be about the finding it is attached to.

AS37468 / angolacables.co.ao (2026-10-07). The shard path built its prompt from the WHOLE findings
file and cut the JSON at 14,000 characters. For a transit carrier target.bgp alone is larger than
that (RIPEstat: 135 upstreams + 2,392 peers/downstreams for AS37468), so NO finding reached the
model. The prompt still demanded prose for "C1, C2, C3" and the model wrote BGP carrier diversity
onto an exposed-database finding. Every AI paragraph in those decks came from blind shards.

Asserts:
  0. FIXTURE PROOF: on this estate the OLD prompt construction really was blind.
  1. The shard prompt carries every finding's id, title and evidence, and none of target.bgp.
  2. The serial prompt carries the same payload (ONE builder, enrich.slim_payload).
  3. Shard: prose that names nothing of its finding is REJECTED (stays missing); grounded prose
     is accepted; an id the shard was not given is ignored.
  4. Serial merge applies the same gate.
  5. A shard that cannot see a finding is not sent at all (fails closed).
  6. No json.dumps(...)[:N] character slice remains in either enrichment module (AST).

    python test_enrich_grounding.py
"""
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("OPENAI_API_KEY", "test")

import enrich as E           # noqa: E402
import enrich_parallel as P  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("\n      " + detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(name)


DB = {"id": "C1", "sev": "CRITICAL", "title": "Exposed database: CVE-2026-18712 +156 more CVEs (26 hosts)",
      "evidence": ["102.130.68.217:9200  nginx", "185.148.113.121:3306  MySQL",
                   "102.211.152.221:5432  PostgreSQL 9.6.0 or later"]}
VPN = {"id": "C2", "sev": "CRITICAL", "title": "Exposed edge-security appliance - Check Point SVN foundation httpd (5 hosts)",
       "evidence": ["197.149.149.35:443  Check Point SVN foundation httpd"]}
MX = {"id": "C3", "sev": "CRITICAL", "title": "Self-hosted Exchange exposed",
      "evidence": ["mail.angolacables.co.ao 197.149.149.30:443  Microsoft Exchange OWA"]}
ESTATE = {"target": {"company": "Angola Cables", "scope": "ASN AS37468",
                     "bgp": {"all_upstreams": ["AS%d" % i for i in range(135)],
                             "per_asn": [{"asn": 37468,
                                          "upstreams": ["AS%d" % i for i in range(135)],
                                          "peers_or_downstreams": ["AS%d" % (i + 5000) for i in range(2392)]}],
                             "colt_remediation": ["Add a second, path-diverse transit provider"]}},
          "identity": {"nets": ["102.%d.0.0/16" % i for i in range(23)]}, "summary": {},
          "findings": [DB, VPN, MX]}

BGP_PROSE = {"what": "Network reconnaissance reveals no second independent BGP upstream or carrier "
                     "diversity; the estate's connectivity relies on a single operational path via AS37468.",
             "why": "A single point of failure leaves all internet-facing services vulnerable to a BGP route hijack.",
             "rem": [{"tag": "COLT", "title": "Carrier Diversity / 2nd BGP upstream",
                      "body": "A second BGP session on a physically separate path."}]}


def db_prose(fid="C1"):
    return {"id": fid, "what": "26 hosts expose MySQL on 3306, PostgreSQL on 5432 and a search API on 9200.",
            "why": "Directly reachable databases are the first thing ransomware crews enumerate.",
            "rem": [{"tag": "COLT", "title": "Close 3306/5432 at the edge", "body": "x" * 300}]}


# 0. fixture proof: the old construction was blind on this estate
sub = dict(ESTATE); sub["findings"] = [DB]
old = json.dumps(sub, ensure_ascii=False)[:14000]
check("fixture reproduces the defect: the OLD [:14000] prompt lacks the finding title (len %d)"
      % len(json.dumps(sub)), DB["title"] not in old and "AS5000" in old)

# 1. shard prompt sees the findings, not the BGP block
seen = []
E_call = E._call


def capture(answer):
    def _c(prompt, model=None, timeout=None, **kw):
        seen.append(prompt)
        return json.dumps({"findings": answer}), {"completion_tokens": 900}
    return _c


E._call = capture([])
P._call_shard(E, ESTATE, [DB, VPN, MX], "en", 0, "m", 10)
p = seen[-1]
missing = [x for x in ("C1", "C2", "C3", DB["title"], VPN["title"], "185.148.113.121:3306") if x not in p]
check("shard prompt carries every id, title and evidence line", not missing, "missing: %s" % missing)
check("shard prompt carries NONE of target.bgp (no 'AS5000', no 'peers_or_downstreams')",
      "AS5000" not in p and "peers_or_downstreams" not in p)

# 2. serial prompt uses the same payload
E._call = lambda prompt, model, timeout, max_tokens=None: (seen.append(prompt), (_ for _ in ()).throw(TimeoutError("timed out")))[1]
saved = (E.MODELS, E.ATTEMPTS, E.BUDGET_S)
E.MODELS, E.ATTEMPTS, E.BUDGET_S = ["m1"], 1, 10_000
try:
    E.enrich(json.loads(json.dumps(ESTATE)), "en")
except Exception:
    pass
sp = seen[-1]
check("serial prompt carries the same findings and none of target.bgp",
      DB["title"] in sp and "AS5000" not in sp)

# 3. shard grounding gate
E._call = capture([dict(BGP_PROSE, id="C1"), db_prose("C9")])
got, meta = P._call_shard(E, ESTATE, [DB], "en", 0, "m", 10)
check("shard: BGP prose on the database finding is REJECTED (got ids %s)" % sorted(got), "C1" not in got)
# Same answer carries a GOOD C1 and a stray C9: the stray must be dropped AND C1 kept. Checking
# only "C9 not in got" passed when the shard crashed on the stray id and returned nothing.
E._call = capture([db_prose("C1"), db_prose("C9")])
got, meta = P._call_shard(E, ESTATE, [DB], "en", 0, "m", 10)
check("shard: a stray id (C9) is dropped while the shard's own C1 is kept (got ids %s)" % sorted(got),
      "C9" not in got and "C1" in got)
E._call = capture([db_prose("C1")])
got, meta = P._call_shard(E, ESTATE, [DB], "en", 0, "m", 10)
check("shard: prose that names the finding's ports/products is ACCEPTED (got ids %s)" % sorted(got), "C1" in got)

# 4. serial merge gate
E._call = lambda prompt, model, timeout, max_tokens=None: (json.dumps(
    {"exec_summary": "s", "findings": [dict(BGP_PROSE, id="C1"),
                                       {"id": "C2", "what": "Five Check Point gateways expose their portal.",
                                        "why": "y", "rem": []}]}), {"completion_tokens": 900, "prompt_tokens": 10})
fj = json.loads(json.dumps(ESTATE))
try:
    fj, _ = E.enrich(fj, "en")
except Exception as e:
    print("      serial enrich raised %r" % e)
by = {f["id"]: f for f in fj["findings"]}
check("serial: BGP prose on C1 rejected, template kept (_enriched=%r)" % by["C1"].get("_enriched"),
      by["C1"].get("_enriched") is not True and "carrier" not in str(by["C1"].get("what", "")).lower())
check("serial: grounded prose on C2 accepted (_enriched=%r)" % by["C2"].get("_enriched"),
      by["C2"].get("_enriched") is True)
E.MODELS, E.ATTEMPTS, E.BUDGET_S = saved

# 5. fail closed when the payload cannot show a finding
real = E.slim_payload
E.slim_payload = lambda fj, findings=None: {"company": "x", "findings": []}
calls = []
E._call = lambda *a, **k: (calls.append(1), ("{}", {}))[1]
got, meta = P._call_shard(E, ESTATE, [DB], "en", 0, "m", 10)
E.slim_payload = real
check("a shard whose payload lacks its findings is NOT sent (calls=%d, error=%r)"
      % (len(calls), meta.get("error", "")[:50]), not calls and "refused" in meta.get("error", ""))
E._call = E_call

# 6. no character slice of a json.dumps in either module
bad = []
for fn in ("enrich.py", "enrich_parallel.py"):
    for n in ast.walk(ast.parse(open(os.path.join(HERE, fn), encoding="utf-8").read())):
        if (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)
                and isinstance(n.value, ast.Call) and getattr(n.value.func, "attr", "") == "dumps"):
            bad.append("%s:%d" % (fn, n.lineno))
check("no json.dumps(...)[:N] slice in the enrichment modules", not bad, "found at %s" % bad)

print()
if FAILS:
    print("FAIL  %d check(s): %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("PASS  AI prose is grounded in the finding it is attached to")
