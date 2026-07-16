#!/usr/bin/env python3
"""
diagnose_engine.py — answer three questions with EVIDENCE, read-only, from inside colt-web:

  1. WHICH Shodan key is the container actually using, and WHAT PLAN is it?
     (Shodan's `vuln:` filter needs a Small Business subscription or higher; `tag:` needs Corporate.
      A one-off "Membership" is paid but does NOT unlock them — that is the usual surprise.)
  2. Is container DNS broken?  (bgpview.io failing to resolve is why every BGP slide says UNKNOWN.)
  3. Can we reach the LLM endpoint, and how slow is it?

Nothing is changed on the droplet.  Usage:  python diagnose_engine.py
"""
import os, subprocess, sys

HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", "")
SSH  = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"] + (["-i", KEY] if KEY and os.path.exists(KEY) else [])
CT   = os.environ.get("COLT_CONTAINER", "colt-web")

PROBE = r'''
import json, os, socket, time, urllib.request, urllib.error

def line(t): print("\n" + t + "\n" + "-" * len(t))

line("1. SHODAN — which key, which plan?")
k = os.environ.get("SHODAN_API_KEY", "")
if not k:
    print("  [X] SHODAN_API_KEY is NOT SET in this container -> the engine ran unauthenticated.")
else:
    print("  key in container : %s...%s  (len %d)" % (k[:4], k[-4:], len(k)))
    try:
        with urllib.request.urlopen("https://api.shodan.io/api-info?key=" + k, timeout=20) as r:
            info = json.loads(r.read())
        print("  plan             : %s" % info.get("plan"))
        print("  query credits    : %s   scan credits: %s" % (info.get("query_credits"), info.get("scan_credits")))
        print("  monitored ips    : %s" % info.get("monitored_ips"))
        print("  unlocked         : %s   (False = free/limited key)" % info.get("unlocked"))
        plan = str(info.get("plan"))
        # Shodan filter entitlements
        vuln_ok = plan in ("corp", "stream-100", "dev", "edu", "smallbiz", "freelancer", "small-business")
        print("\n  -> `vuln:` filter needs Small Business+ ; `tag:` needs Corporate.")
        print("  -> your plan reports as '%s'." % plan)
        if plan in ("oss", "dev", "member"):
            print("     '%s' is the one-off Membership / free tier: PAID but does NOT include vuln:/tag:." % plan)
            print("     Those two warnings are correct and are NOT a key-wiring bug.")
    except Exception as e:
        print("  [X] api-info failed: %r" % e)

line("2. DNS — why every BGP slide says UNKNOWN")
print("  /etc/resolv.conf:")
try:
    for l in open("/etc/resolv.conf"):
        if l.strip() and not l.startswith("#"): print("    " + l.rstrip())
except Exception as e:
    print("    unreadable: %r" % e)
for h in ("bgpview.io", "stat.ripe.net", "crt.sh", "api.shodan.io", "inference.do-ai.run"):
    t = time.time()
    try:
        ip = socket.gethostbyname(h)
        print("  %-22s -> %-15s  %dms" % (h, ip, int((time.time()-t)*1000)))
    except Exception as e:
        print("  %-22s -> [X] %s" % (h, e))

line("3. ASN discovery — can we replace the dead bgpview with RIPE/CAIDA/PeeringDB?")
import urllib.parse
def _j(u, t=20):
    r = urllib.request.Request(u, headers={"User-Agent": "colt-cyber-presales/1.0"})
    with urllib.request.urlopen(r, timeout=t) as h: return json.loads(h.read())
term = os.environ.get("PROBE_ORG", "Colt Technology Services")
print("  test org: %s" % term)
try:
    d = _j("https://rest.db.ripe.net/search.json?query-string=%s&type-filter=aut-num&flags=no-referenced"
           % urllib.parse.quote(term))
    n = len((d.get("objects", {}) or {}).get("object", []) or [])
    print("  RIPE DB       : OK  (%d aut-num objects)" % n)
except Exception as e:
    print("  RIPE DB       : [X] %r" % e)
try:
    q = {"query": '{ asns(name: "%s", first: 5) { edges { node { asn asnName } } } }' % term}
    r = urllib.request.Request("https://api.asrank.caida.org/v2/graphql", data=json.dumps(q).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=25) as h: d = json.loads(h.read())
    e_ = ((d.get("data") or {}).get("asns") or {}).get("edges") or []
    print("  CAIDA AS Rank : OK  -> %s" % [(x["node"]["asn"], x["node"].get("asnName")) for x in e_[:3]])
except Exception as e:
    print("  CAIDA AS Rank : [X] %r" % e)
try:
    d = _j("https://www.peeringdb.com/api/net?name__contains=%s&limit=5" % urllib.parse.quote(term))
    print("  PeeringDB     : OK  -> %s" % [(n_["asn"], n_["name"]) for n_ in d.get("data", [])[:3]])
except Exception as e:
    print("  PeeringDB     : [X] %r" % e)
try:
    d = _j("https://api.bgpview.io/search?query_term=" + urllib.parse.quote(term))
    print("  bgpview.io    : OK  (%d asns)" % len((d.get("data", {}) or {}).get("asns", []) or []))
except Exception as e:
    print("  bgpview.io    : [X] %r   <- the dead source we no longer depend on" % e)

line("4. LLM endpoint reachability")
base = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
key  = os.environ.get("OPENAI_API_KEY", "")
print("  base: %s | key set: %s" % (base, bool(key)))
print("  ENRICH_MODEL(S) in env: %r / %r" % (os.environ.get("ENRICH_MODEL"), os.environ.get("ENRICH_MODELS")))
print("  ENRICH_ATTEMPTS=%r  ENRICH_TIMEOUT=%r" % (os.environ.get("ENRICH_ATTEMPTS"), os.environ.get("ENRICH_TIMEOUT")))
if key:
    t = time.time()
    try:
        rq = urllib.request.Request(base + "/models", headers={"Authorization": "Bearer " + key})
        with urllib.request.urlopen(rq, timeout=25) as r:
            ms = [m.get("id") for m in json.loads(r.read()).get("data", [])]
        print("  /models OK in %dms -> %d models visible" % (int((time.time()-t)*1000), len(ms)))
        print("  first 12: %s" % ", ".join(ms[:12]))
    except Exception as e:
        print("  [X] /models failed after %dms: %r" % (int((time.time()-t)*1000), e))
'''

def main():
    tgt = "%s@%s" % (USER, HOST)
    r = subprocess.run(SSH + [tgt, "docker exec -i %s python3 -" % CT],
                       input=PROBE.encode("utf-8"))
    sys.exit(r.returncode)

if __name__ == "__main__":
    main()
