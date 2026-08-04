#!/usr/bin/env python3
"""
test_scope_abakus.py — the abakus-tk.de false-positive regression (2026-08).

WHAT HAPPENED
abakus-tk.de is a ~20-consultant telecoms reseller in Lubeck. Its entire external estate is ONE
shared IONOS elastic-SSL webhosting VIP plus Microsoft 365 and Zoho tenancies. It has no ASN and
no announced prefixes, and the engine printed exactly that on slide 1: `ASN - . 0 prefixes`.

The delivered deck nevertheless claimed 401 unique IPs, 42 ASNs and 49 countries. Of the 17
evidence IPs printed across the three decks, 16 belonged to third parties -- Oracle, AWS, OVH,
Contabo, Eircom, Facebook and four small Turkish/offshore hosters. The one genuine asset
(217.160.0.136, IONOS) was rated NIEDRIG, the lowest severity in the deck. 236 of the 348
inventoried hosts -- 68% -- were Meta Platforms.

The entire estate came from ONE line in the site footer:

    <a href="https://wa.me/01702206960">Chat</a>

FOUR DEFECTS, EACH TESTED BELOW
  1. group_discovery.STRUCTURE_HINTS matched `struktur` as a bare SUBSTRING, and `infrastruktur`
     contains `struktur`. `/it-infrastruktur/` -- the likeliest page on a TELECOMS provider's site
     -- was read as a corporate group-structure page, so every external link on it, including the
     site-wide WhatsApp footer button, was harvested as a "subsidiary".
  2. The suppression list lived only inside group_discovery and named `whatsapp.com` and `t.me`
     but not `wa.me`. A denylist in one module protects one code path.
  3. shodan_recon appended group domains STRAIGHT into scope, bypassing every gate -- and
     _owns_apex then returned True for them BECAUSE they were group domains. Discovery vouching
     for itself is not a gate.
  4. THE SYSTEMIC ONE. `identity_ips = set(hosts)` is the baseline every later guard measures
     against, and it is assigned AFTER the identity queries run. The poison arrived THROUGH an
     identity query (`hostname:".wa.me"`), so it became part of the baseline: scope_blowout
     compared 401 against 401 and could never fire, and the co-tenant guard exempted the Meta
     hosts because wa.me was registered as an owned apex. One bad domain disarmed every
     downstream check simultaneously.

The last section re-runs every earlier incident to prove none of the fixes cost recall.

    python test_scope_abakus.py
"""
import os, sys, types

os.environ.setdefault("SHODAN_API_KEY", "test")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILS = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


# =============================================================== 1. the page-selection bug
print("== 1. /infrastruktur/ is NOT a corporate group-structure page ==")
import group_discovery as G

def _is_structure(path):
    return bool(G.STRUCTURE_HINTS.search(path)) and not bool(G.ANTI_HINTS.search(path))

for p in ["/it-infrastruktur/", "/infrastruktur/", "/netzwerk-infrastruktur/",
          "/rechenzentrum-infrastruktur/", "/leistungen/cloud-infrastructure/",
          "/en/infrastructure/"]:
    check(not _is_structure(p), "rejected as a structure page: %s" % p)

# ...and the genuinely structural paths must still be accepted, or the angermann recall dies.
for p in ["/struktur/", "/unternehmensstruktur/", "/konzernstruktur/", "/gruppe/", "/group/",
          "/our-companies/", "/beteiligungen/", "/auf-einen-blick/"]:
    check(_is_structure(p), "still accepted as a structure page: %s" % p)


# =============================================================== 2. the denylist
print("\n== 2. shorteners, social and platform infrastructure can never be a subsidiary ==")
import scope_deny as D

for a in ["wa.me", "t.me", "bit.ly", "lnkd.in", "linktr.ee", "fb.me", "m.me", "rb.gy", "t.co",
          "whatsapp.com", "facebook.com", "instagram.com", "linkedin.com", "calendly.com",
          "spiegel.de", "heise.de", "cloudflare.com", "googleapis.com"]:
    check(D.is_denied(a), "denied: %-16s (%s)" % (a, D.why_denied(a)))

# A denylist that is too greedy silently shrinks a real customer's estate -- the opposite failure,
# and the harder one to notice. Every domain from a real past engagement must survive.
for a in ["abakus-tk.de", "skon.de", "bibel.tv", "bibeltv.de", "angermann.de", "netbid.com",
          "netbid.io", "nordleasing.com", "leaseback.de", "buerosuche.de", "oaklins.com",
          "rightmart.de", "email-archiv-rightmart.de", "ecolines.net", "lotto24.de"]:
    check(not D.is_denied(a), "still allowed: %s" % a)

check(D.is_denied("wa.me") and not D.is_denied("wa-me.de"),
      "the shortener shape rule does not leak onto ordinary domains")


# =============================================================== 3. the ownership gate
print("\n== 3. the ownership gate refuses a denied apex even when discovery vouches for it ==")
import shodan_recon as R

TOK = {"abakus"}
ok, why = R._owns_apex("wa.me", TOK, "abakus-tk.de", group_domains=["wa.me"], structure_known=True)
check(not ok, "wa.me refused EVEN THOUGH it is in group_domains -- %s" % why)

ok, _ = R._owns_apex("abakus-tk.de", TOK, "abakus-tk.de")
check(ok, "the seed apex is still owned")

# A media or social company can legitimately BE the customer: the deny check must sit AFTER the
# seed test, never before it.
ok, _ = R._owns_apex("spiegel.de", {"spiegel"}, "spiegel.de")
check(ok, "a denied apex is still assessable when it IS the seed (deny runs after the seed test)")

# The angermann recall must be untouched: a real subsidiary with zero string overlap.
ok, why = R._owns_apex("netbid.com", {"angermann"}, "angermann.de",
                       group_domains=["netbid.com"], structure_known=True)
check(ok, "netbid.com still owned via the group-structure page -- %s" % why)
ok, why = R._owns_apex("netbid.io", {"angermann"}, "angermann.de",
                       group_domains=["netbid.com"], structure_known=True)
check(ok, "netbid.io still owned as a sibling TLD -- %s" % why)


# =============================================================== 4. the contribution budget
print("\n== 4. a discovered domain may enlarge the estate, never BE it ==")

def _h(ip, org, names, asn="AS32934"):
    return {"ip_str": ip, "port": 443, "org": org, "hostnames": list(names), "asn": asn,
            "product": "nginx", "data": "HTTP/1.1 200 OK", "transport": "tcp",
            "location": {"country_code": "US"}}


def _install_routing_shodan(routes, default=()):
    """routes: [(substring_of_query, [records])] - first match wins.
    A fake that returns every record for EVERY query cannot test a PER-QUERY rule; that bug made
    the first lotto24 assertion measure nothing."""
    fake = types.ModuleType("shodan")

    def _pick(q):
        for frag, recs in routes:
            if frag.lower() in str(q).lower():
                return recs
        return list(default)

    class _API:
        def __init__(self, *a, **k): pass
        def info(self): return {"plan": "basic", "query_credits": 100}
        def count(self, q, **k): return {"total": len(_pick(q))}
        def search(self, q, **k):
            r = _pick(q); return {"total": len(r), "matches": r}
        def search_cursor(self, q, **k):
            for r in _pick(q):
                yield r

    fake.Shodan = _API
    fake.APIError = Exception
    sys.modules["shodan"] = fake


# The real shape: the seed proves the single shared IONOS VIP; wa.me returns Meta's global edge.
IONOS = [_h("217.160.0.136", "IONOS SE", ["abakus-tk.de", "www.abakus-tk.de"], asn="AS8560")]
META = [_h("31.13.66.%d" % i, "Facebook, Inc.", ["wa.me"]) for i in range(1, 60)] + \
       [_h("102.132.99.%d" % i, "Facebook, Inc.", ["wa.me"]) for i in range(1, 60)]

_install_routing_shodan([("abakus-tk.de", IONOS), ("wa.me", META)], default=[])

ident = {"seed": "abakus-tk.de", "company": "abakusTK",
         # wa.me is FORCED into the domain list here, simulating a future harvester that gets past
         # sections 1-3. This section proves the budget stops it WITHOUT relying on any of them.
         "domains": ["abakus-tk.de", "wa.me"],
         "asns": [], "nets": [], "pinned": [], "brand_tokens": ["abakus"],
         "group_domains": ["wa.me"], "group_pages": ["https://x/it-infrastruktur/"],
         "org": "abakusTK", "org_is_cdn": False, "org_is_carrier": False, "asn_holder": "",
         "shared_asns": [], "related_unscoped": [], "favicons": [], "issuers": [],
         "internal_cas": [], "cert_orgs": [], "jarms": [], "cpes": [], "org_variants": [],
         "brand_variants": [], "exclude_ips": [], "exclude_apexes": [], "ct_domains": []}

F = R.build_filters(ident)
_dom_tagged = [f for f in F if f.get("dom")]
check(bool(_dom_tagged), "identity clauses are tagged with the domain that produced them")
check(any(f.get("dom") == "wa.me" for f in F), "the wa.me clauses are attributable to wa.me")

# run() returns the FINDINGS object; the surviving estate is recorded in ident["scanned_ips"].
R.run(ident, F, audience="internal", limit_per_query=500)
_hosts = set(ident.get("scanned_ips") or [])
_n = len(_hosts)

check(bool(ident.get("domains_rolled_back")),
      "wa.me was ROLLED BACK (%s)" % (ident.get("domains_rolled_back") or "NOT ROLLED BACK"))
check(_n <= 5, "estate is the real one, not Meta's: %d host(s) kept" % _n)
check(not any(str(ip).startswith(("31.13.", "102.132.")) for ip in _hosts),
      "no Meta edge address survives into the estate")
check("217.160.0.136" in _hosts, "the one genuine IONOS host is still there")
check("wa.me" not in [str(d) for d in (ident.get("domains") or [])],
      "wa.me is removed from ident['domains'] so the co-tenant guard cannot re-exempt it")
check("wa.me" in (ident.get("related_unscoped") or []),
      "wa.me is recorded as related-but-unscoped rather than silently vanishing")


# =============================================================== 5. recall is not collateral damage
print("\n== 5. a legitimate subsidiary is NOT rolled back ==")
NETBID = [_h("87.234.246.%d" % i, "Netbid Industrie Auktion AG", ["netbid.com"], asn="AS8560")
          for i in range(50, 58)]
ANG = [_h("217.110.51.%d" % i, "Horst F.G. Angermann GmbH", ["angermann.de"], asn="AS8220")
       for i in (2, 7)]
_install_routing_shodan([("angermann.de", ANG), ("netbid.com", NETBID)], default=[])

ident2 = dict(ident)
ident2.update({"seed": "angermann.de", "domains": ["angermann.de", "netbid.com"],
               "brand_tokens": ["angermann"], "group_domains": ["netbid.com"],
               "related_unscoped": [], "org": "Horst F.G. Angermann GmbH"})
ident2.pop("domains_rolled_back", None)

F2 = R.build_filters(ident2)
R.run(ident2, F2, audience="internal", limit_per_query=500)
_h2 = set(ident2.get("scanned_ips") or [])
check(not ident2.get("domains_rolled_back"),
      "netbid.com survived: 8 hosts against a budget of %d" % ident2.get("domain_budget", 0))
check(any(str(ip).startswith("87.234.246.") for ip in _h2),
      "the netbid mail cluster is still in scope (the angermann engagement's best finding)")


print("\n" + ("FAILED: %d" % len(FAILS) if FAILS else "ALL ABAKUS SCOPE CHECKS PASSED"))
for f in FAILS:
    print("   - " + f)
sys.exit(1 if FAILS else 0)
