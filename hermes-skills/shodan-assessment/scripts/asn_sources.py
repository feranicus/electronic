#!/usr/bin/env python3
"""
asn_sources.py — company name -> origin ASNs, from MULTIPLE authoritative sources.

WHY: discovery used to be bgpview.io ONLY, and bgpview.io stopped resolving inside the container
("[Errno -5] No address associated with hostname") while stat.ripe.net answered in 1ms. One dead
source => asns=0 => no ASN scoping, no BGP/NIS2 slide, and (before the UNKNOWN fix) a false
CRITICAL. Never depend on one API for a load-bearing fact.

Sources, queried in order, results merged:
  1. RIPE DB      (rest.db.ripe.net)     — authoritative for the RIPE region (all of DACH). Best
                                           for Colt's market. Searches aut-num + org objects.
  2. CAIDA AS Rank (api.asrank.caida.org) — global, GraphQL, ranks by customer cone.
  3. PeeringDB    (peeringdb.com/api)    — operator-maintained; great for carriers/ISPs.
  4. bgpview.io                          — kept LAST: it is what bgp.he.net exposes as JSON, but it
                                           is the flaky one. If it resolves, it still contributes.

Every source is independently error-trapped: one dead API degrades the result, never kills it.
`errors` tells the caller which sources failed, so absence-of-evidence is never read as evidence.

CLI:  python asn_sources.py "SGS"   ->  JSON {asns, per_source, errors}
"""
import json, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "colt-cyber-presales/1.0 (+ASN discovery)"}
ERRORS = []


def _get(url, timeout=20, headers=None):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _post(url, payload, timeout=25):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _norm(name):
    """Loose company-name match: 'SGS SA' ~ 'SGS'. Avoids matching 'SGS' inside 'SGSFOO'."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _relevant(seed, holder):
    a, b = _norm(seed), _norm(holder)
    if not a or not b:
        return False
    return a == b or (" %s " % a) in (" %s " % b)      # whole-token containment only


def ripe_db(term, cap=12):
    """RIPE database aut-num search — authoritative for Europe/DACH."""
    out = []
    try:
        d = _get("https://rest.db.ripe.net/search.json?query-string=%s&type-filter=aut-num&flags=no-referenced"
                 % urllib.parse.quote(term))
        for obj in (d.get("objects", {}) or {}).get("object", []) or []:
            attrs = {a.get("name"): a.get("value")
                     for a in (obj.get("attributes", {}) or {}).get("attribute", []) or []}
            asn, holder = attrs.get("aut-num"), (attrs.get("as-name") or attrs.get("descr") or "")
            if asn and (_relevant(term, holder) or _relevant(term, attrs.get("descr", ""))):
                n = int(re.sub(r"\D", "", asn) or 0)
                if n and n not in out:
                    out.append(n)
            if len(out) >= cap:
                break
    except Exception as e:
        ERRORS.append({"source": "ripe-db", "error": repr(e)[:120]})
    return out


def caida(term, cap=12):
    """CAIDA AS Rank GraphQL — global, name search, ranked by customer cone."""
    out = []
    try:
        q = {"query": '{ asns(name: "%s", first: %d) { edges { node { asn asnName organization '
                      '{ orgName } } } } }' % (term.replace('"', ""), cap)}
        d = _post("https://api.asrank.caida.org/v2/graphql", q)
        for e in (((d.get("data") or {}).get("asns") or {}).get("edges") or []):
            n = e.get("node") or {}
            holder = n.get("asnName") or ((n.get("organization") or {}).get("orgName") or "")
            if n.get("asn") and _relevant(term, holder):
                v = int(n["asn"])
                if v not in out:
                    out.append(v)
    except Exception as e:
        ERRORS.append({"source": "caida", "error": repr(e)[:120]})
    return out


def peeringdb(term, cap=12):
    """PeeringDB network search — operator-maintained, strong for carriers."""
    out = []
    try:
        d = _get("https://www.peeringdb.com/api/net?name__contains=%s&limit=%d"
                 % (urllib.parse.quote(term), cap))
        for n in d.get("data", []) or []:
            if n.get("asn") and _relevant(term, n.get("name", "")):
                v = int(n["asn"])
                if v not in out:
                    out.append(v)
    except Exception as e:
        ERRORS.append({"source": "peeringdb", "error": repr(e)[:120]})
    return out


def bgpview(term, cap=12):
    """bgpview.io — the JSON face of what bgp.he.net shows. Flaky DNS; kept as a bonus source."""
    out = []
    try:
        d = _get("https://api.bgpview.io/search?query_term=" + urllib.parse.quote(term))
        for a in ((d.get("data", {}) or {}).get("asns", []) or [])[:cap]:
            holder = a.get("description") or a.get("name") or ""
            if a.get("asn") and _relevant(term, holder):
                v = int(a["asn"])
                if v not in out:
                    out.append(v)
    except Exception as e:
        ERRORS.append({"source": "bgpview", "error": repr(e)[:120]})
    return out


def discover(term, cap=12):
    """Merge every source. Returns {asns, per_source, errors, ok}."""
    del ERRORS[:]
    per = {}
    for name, fn in (("ripe-db", ripe_db), ("caida", caida), ("peeringdb", peeringdb), ("bgpview", bgpview)):
        try:
            per[name] = fn(term, cap)
        except Exception as e:
            per[name] = []
            ERRORS.append({"source": name, "error": repr(e)[:120]})
        print("[asn] %-9s %-28s -> %s" % (name, term[:28], per[name] or "-"), file=sys.stderr)
    merged = []
    for lst in per.values():
        for a in lst:
            if a not in merged:
                merged.append(a)
    # ok = at least one source ANSWERED (empty answer from a live source is still an answer)
    ok = len(ERRORS) < 4
    return {"asns": merged[:cap], "per_source": per, "errors": list(ERRORS), "ok": ok}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: asn_sources.py <company name>"); sys.exit(1)
    print(json.dumps(discover(" ".join(sys.argv[1:])), indent=2))
