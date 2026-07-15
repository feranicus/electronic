#!/usr/bin/env python3
"""
bgp_resilience.py -- BGP / ASN resilience module for the Colt pre-sales engine.

Given the org's origin ASN(s) (from shodan_recon autodiscover) it builds a bgp.he.net-style
resilience picture using ONLY free, no-key sources:
  * RIPEstat  as-overview / announced-prefixes / asn-neighbours  (holder, IP space, upstreams+peers)
  * PeeringDB netixlan / netfac                                   (IX + facility diversity)
  * CAIDA AS-Rank                                                 (global rank + customer cone)

Core metric: distinct UPSTREAM (transit) ASNs = "homing degree".
  0 own ASN (announces only inside the ISP's ASN) -> NO routing autonomy  (highest risk)
  1 upstream  -> single-homed                     (HIGH availability risk)
  2 upstreams -> dual-homed                        (MEDIUM)
  3+          -> multi-homed                        (LOW)

We map single-homing to a NIS2 Art 21(2)(c) business-continuity / redundancy GAP (per CIR 2024/2690
Annex sec 4) -- framed as a demonstrable resilience weakness, NOT a black-letter violation -- and
attach the applicable fine band. Output is a dict the deck generators render.

CLI:  python3 bgp_resilience.py <ASN|org> [ASN2 ...]     # prints JSON
"""
import os, sys, json, time, urllib.request, urllib.error

UA = {"User-Agent": "colt-presales-bgp/1.0"}

# NIS2 administrative fine caps (Art 34) — on GLOBAL GROUP turnover, higher-of.
NIS2_FINES = {
    "essential": {"eur": 10_000_000, "pct": 2.0},
    "important": {"eur": 7_000_000,  "pct": 1.4},
}

# Every failed lookup is recorded. This is the difference between "this org has no BGP redundancy"
# (a finding we can defend) and "we could not reach RIPE/bgpview" (not a finding at all).
_FETCH_ERRORS = []

def _get_json(url, tries=3, timeout=15):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e; time.sleep(1.2 * (i + 1))   # backoff: cures transient DNS/rate blips
    print(f"[warn] bgp fetch failed {url}: {last}", file=sys.stderr)
    _FETCH_ERRORS.append({"url": url.split("?")[0], "error": repr(last)[:120]})
    return {}

def _asnum(a):
    s = str(a).upper().replace("AS", "").strip()
    return int(s) if s.isdigit() else None

# ---------- RIPEstat ----------
def ripe_overview(asn):
    d = _get_json(f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{asn}").get("data", {})
    return {"holder": d.get("holder"), "announced": d.get("announced")}

def ripe_prefixes(asn):
    d = _get_json(f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}").get("data", {})
    pfx = [p["prefix"] for p in d.get("prefixes", [])]
    v4 = [p for p in pfx if ":" not in p]; v6 = [p for p in pfx if ":" in p]
    ips = 0
    for p in v4:
        try: ips += 2 ** (32 - int(p.split("/")[1]))
        except Exception: pass
    return {"prefixes_v4": len(v4), "prefixes_v6": len(v6), "ipv4_addresses": ips}

def ripe_upstreams(asn):
    """Distinct UPSTREAM (transit provider) ASNs = RIPEstat 'left' neighbours."""
    d = _get_json(f"https://stat.ripe.net/data/asn-neighbours/data.json?resource=AS{asn}").get("data", {})
    ups, peers = {}, {}
    for n in d.get("neighbours", []):
        na = n.get("asn"); t = (n.get("type") or "").lower()
        if na is None: continue
        (ups if t == "left" else peers)[na] = n.get("power", 1)
    return {"upstreams": sorted(ups), "peers_or_downstreams": sorted(peers)}

# ---------- PeeringDB (IX / facility diversity) ----------
def peeringdb(asn):
    try:
        ix = _get_json(f"https://www.peeringdb.com/api/netixlan?asn={asn}").get("data", [])
        fac = _get_json(f"https://www.peeringdb.com/api/netfac?asn={asn}").get("data", [])
        return {"ix_count": len({x.get("ix_id") for x in ix}),
                "ix_names": sorted({x.get("name") for x in ix if x.get("name")})[:12],
                "facility_count": len({x.get("fac_id") for x in fac})}
    except Exception:
        return {"ix_count": 0, "ix_names": [], "facility_count": 0}

# ---------- CAIDA AS-Rank ----------
def caida(asn):
    d = _get_json(f"https://api.asrank.caida.org/v2/restful/asns/{asn}").get("data", {})
    a = (d or {}).get("asn") or {}
    cone = a.get("cone") or {}
    return {"rank": a.get("rank"), "customer_cone_asns": cone.get("numberAsns")}

def _verdict(homing_degree, has_own_asn, ix_count, data_ok=True):
    # HARD RULE: absence of evidence is NOT evidence of absence. If the ASN/upstream lookup failed
    # (DNS down in the container, bgpview 502, RIPE timeout) we know NOTHING about this org's routing
    # — reporting CRITICAL there put a false claim in a customer deck (Cogent = AS174, a tier-1
    # transit network, was graded "no-ASN / 0 upstreams / CRITICAL" purely because DNS failed).
    if not data_ok:
        return ("UNKNOWN", "data-unavailable",
                "BGP resilience could not be determined: the ASN/upstream lookup failed "
                "(no answer from bgpview / RIPEstat). This is NOT a finding — re-run when the "
                "lookup services are reachable before drawing any conclusion.")
    if not has_own_asn:
        return ("HIGH", "no-own-asn",
                "No originating ASN was found for this org: it most likely announces inside its "
                "ISP's ASN (no routing autonomy). Confirm with the customer before presenting — an "
                "org can also hold address space under a parent or subsidiary name.")
    if homing_degree <= 1:
        return ("HIGH", "single-homed",
                "One transit upstream — a single carrier or link failure takes the whole WAN down.")
    if homing_degree == 2:
        return ("MEDIUM", "dual-homed",
                "Two upstreams — basic redundancy, but check the two are truly diverse (carrier + path).")
    return ("LOW", "multi-homed",
            f"{homing_degree} upstreams — good routing diversity."
            + ("" if ix_count else " (no public IX presence noted.)"))

def assess(asns, org=None, discovery_ok=None):
    """discovery_ok: did upstream ASN discovery (bgpview/crt.sh/RIPE) actually succeed?
    Pass False (or leave None with zero ASNs) and we report UNKNOWN rather than inventing a gap."""
    del _FETCH_ERRORS[:]
    asns = [x for x in (_asnum(a) for a in (asns or [])) if x]
    per, all_ups = [], set()
    for asn in asns:
        ov = ripe_overview(asn); px = ripe_prefixes(asn); up = ripe_upstreams(asn)
        pdb = peeringdb(asn); cd = caida(asn)
        all_ups.update(up["upstreams"])
        per.append({"asn": asn, "holder": ov["holder"], **px, **up, **pdb, **cd})
    has_own_asn = bool(asns)
    homing = len(all_ups)
    ix_total = sum(p.get("ix_count", 0) for p in per)

    # data_ok is False when: discovery explicitly failed, OR we have no ASNs at all (an empty list
    # proves nothing on its own), OR we had ASNs but every RIPE upstream call errored out.
    lookups_failed = bool(_FETCH_ERRORS)
    if discovery_ok is False:
        data_ok = False
    elif not asns:
        data_ok = False                      # nothing to reason from — never grade this
    elif lookups_failed and not all_ups:
        data_ok = False                      # had ASNs, but the upstream data never arrived
    else:
        data_ok = True
    rag, status, why = _verdict(homing, has_own_asn, ix_total, data_ok)
    nis2 = {
        "control": "Art 21(2)(c) business continuity / redundancy (CIR 2024/2690, Annex sec.4)",
        # only claim a gap on evidence we actually have
        "gap": (data_ok and status == "single-homed"),
        "finding": (("Single upstream is a demonstrable network-availability & continuity gap against "
                     "NIS2 Art 21(2)(c). Not a per-se violation, but a documented weakness a regulator "
                     "or auditor would flag.")
                    if (data_ok and status == "single-homed") else
                    ("No NIS2 finding is claimed: BGP resilience was not determined." if not data_ok
                     else "No single-homing gap observed against NIS2 Art 21(2)(c).")),
        "fine_band": NIS2_FINES,
        "note": "Entity class (essential vs important) is decided by sector+size — set in the compliance module.",
    }
    remediation = ["Add a second, path-diverse transit provider (Colt IP Access / dual-upstream)",
                   "Terminate on two geographically separate Colt PoPs",
                   "Layer managed DDoS + SD-WAN for automatic failover",
                   "Document it in the Art 21 BC/DR plan to close the audit gap"]
    return {"org": org, "origin_asns": asns, "has_own_asn": has_own_asn,
            "data_ok": data_ok, "lookup_errors": list(_FETCH_ERRORS),
            "homing_degree": homing, "all_upstreams": sorted(all_ups),
            "ix_presence": ix_total, "rag": rag, "homing_status": status, "why": why,
            "per_asn": per, "nis2": nis2, "colt_remediation": remediation}

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: bgp_resilience.py <ASN|org> [ASN2 ...]"); sys.exit(1)
    asn_args = [a for a in args if _asnum(a)]
    org_arg = next((a for a in args if not _asnum(a)), None)
    print(json.dumps(assess(asn_args or args, org_arg), indent=2, ensure_ascii=False))
