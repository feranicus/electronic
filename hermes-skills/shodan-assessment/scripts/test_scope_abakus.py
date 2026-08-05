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



# =============================================================== 6. the generic-word brand
print("\n== 6. a brand that is a common word is refused as an ownership anchor ==")
# THE SECOND ABAKUS RUN (2026-08). With wa.me denied, the deck STILL claimed 192 IPs / 44 ASNs /
# 15 countries -- because "Abakus" is the German word for abacus and the name of dozens of
# unrelated firms. ssl:"abakus", http.title:"abakus" and http.html:"abakus" matched Cloudflare,
# Hetzner, OVH, Vultr, Scaleway, Infomaniak, Google and Amazon. Those clauses are cat="identity",
# so they ALSO skip the CDN drop and are never corroborated: nothing was checking them at all.
BRANDY = {"seed": "abakus-tk.de", "company": "abakusTK", "domains": ["abakus-tk.de"],
          "asns": [], "nets": [], "pinned": ["217.160.0.136"], "brand_tokens": ["abakus"],
          "group_domains": [], "org": "abakus-tk.de", "org_is_cdn": True, "org_is_carrier": False,
          "asn_holder": "IONOS", "shared_asns": [], "related_unscoped": [], "favicons": [],
          "issuers": [], "internal_cas": [], "cert_orgs": [], "jarms": [], "cpes": [],
          "org_variants": [], "brand_variants": ["abakus"], "brand": "abakus",
          "exclude_ips": [], "exclude_apexes": [], "ct_domains": []}

FB = R.build_filters(BRANDY)
_guarded = [f["clause"] for f in FB if f.get("guard") == "rarity"]
check(any(c.startswith('ssl:"') for c in _guarded), "ssl:\"brand\" is rarity-guarded")
check(any(c.startswith("http.title:") for c in _guarded), "http.title:\"brand\" is rarity-guarded")
check(any(c.startswith("http.html:") for c in _guarded), "http.html:\"brand\" is rarity-guarded")

# A common word matches the internet; a distinctive one does not. Both answers come from Shodan's
# own count(), so there is no word list to maintain and no language to get wrong.
COMMON = [_h("10.0.0.%d" % i, "Hetzner Online GmbH", ["something-abakus.de"]) for i in range(1, 40)]
_install_routing_shodan([('ssl:"abakus"', COMMON), ("http.title", COMMON), ("http.html", COMMON),
                         ("abakus-tk.de", IONOS)], default=[])
_fake = sys.modules["shodan"]
_realcount = _fake.Shodan.count
_fake.Shodan.count = lambda self, q, **k: {"total": 250000 if "abakus" in q and "-tk" not in q else 3}

BRANDY2 = dict(BRANDY); BRANDY2["related_unscoped"] = []
R.run(BRANDY2, R.build_filters(BRANDY2), audience="internal", limit_per_query=500)
_est = set(BRANDY2.get("scanned_ips") or [])
check(bool(BRANDY2.get("selectors_refused")),
      "the common-word selectors were refused (%s)"
      % ([s["clause"] for s in (BRANDY2.get("selectors_refused") or [])][:3]))
check(not any(str(i).startswith("10.0.0.") for i in _est),
      "no host arrived through a common-word brand selector")
check("217.160.0.136" in _est, "the genuine host still arrives through the precise clauses")
_fake.Shodan.count = _realcount


# =============================================================== 7. SaaS tenancies
print("\n== 7. a SaaS tenancy is never pinned as an owned host ==")
_orig_chain = R._cname_chain
R._cname_chain = lambda n: {
    "autodiscover.abakus-tk.de": ["autodiscover.outlook.com"],
    "webmail.abakus-tk.de": ["abakustk.mail.protection.outlook.com"],
    "exchange.abakus-tk.de": ["outlook.office365.com"],
    "auth.abakus-tk.de": ["login.microsoftonline.com"],
    "intranet.abakus-tk.de": [],
    "vpn.acme.de": ["vpn-edge.acme.de"],
}.get(n, [])
for n in ["autodiscover.abakus-tk.de", "webmail.abakus-tk.de", "exchange.abakus-tk.de",
          "auth.abakus-tk.de"]:
    check(R._is_saas_tenancy(n), "SaaS tenancy, not pinned: %s" % n)
for n in ["intranet.abakus-tk.de", "vpn.acme.de"]:
    check(not R._is_saas_tenancy(n), "genuinely the customer's own host, still pinned: %s" % n)
R._cname_chain = _orig_chain


# =============================================================== 8. the co-tenant valve
print("\n== 8. the co-tenant valve no longer disarms itself on shared hosting ==")
# Real numbers from the run: 182 of 192 flagged (95%), valve refused, all 182 kept.
MIXED = [_h("217.160.0.136", "abakusTK", ["abakus-tk.de"], asn="AS8560")] + \
        [_h("52.98.253.%d" % i, "Microsoft Corporation", ["outlook.com"], asn="AS8075")
         for i in range(1, 40)]
_install_routing_shodan([("abakus-tk.de", MIXED)], default=[])

SHARED = dict(BRANDY)
SHARED.update({"asns": [], "nets": [], "pinned": ["217.160.0.136"], "brand_variants": [],
               "related_unscoped": [], "domains": ["abakus-tk.de"]})
SHARED.pop("scanned_ips", None)
R.run(SHARED, R.build_filters(SHARED), audience="internal", limit_per_query=500)
_s = set(SHARED.get("scanned_ips") or [])
check(not SHARED.get("cotenants_refused"),
      "no ASN and no prefixes -> a mass co-tenant drop is EXPECTED, not a malfunction")
check("217.160.0.136" in _s, "the customer's own pinned host survives the drop")
check(len(_s) < 10, "Microsoft's shared front ends are gone: %d host(s) left" % len(_s))

# ...but where the target DOES own address space, a 95% drop still means the whois data is the
# suspect, and the valve must still refuse. That is the lotto24/angermann doctrine, unchanged.
# NOTE the co-tenants here are ORDINARY COMPANIES, not providers - which is what the real shared
# Colt /24 held (a doctors' pension fund, FACT, Regus). Using a hoster's name instead would be
# unrealistic AND would be handled earlier by the attribution gate, so the valve would never run.
OWNED_MIX = [_h("217.110.51.2", "Horst F.G. Angermann GmbH", ["angermann.de"], asn="AS8220")] + \
            [_h("217.110.51.%d" % i, "NORDRHEINISCHE AERZTEVERSORGUNG", ["naev.de"], asn="AS8220")
             for i in range(20, 60)]
OWNED = dict(SHARED)
OWNED.update({"asns": ["AS8220"], "nets": ["217.110.51.0/24"], "related_unscoped": [],
              "domains": ["angermann.de"], "pinned": ["217.110.51.2"],
              "brand_tokens": ["angermann"], "seed": "angermann.de"})
OWNED.pop("scanned_ips", None); OWNED.pop("cotenants_refused", None)
_install_routing_shodan([("217.110.51", OWNED_MIX), ("angermann.de", OWNED_MIX)], default=[])
R.run(OWNED, R.build_filters(OWNED), audience="internal", limit_per_query=500)
check(bool(OWNED.get("cotenants_refused")),
      "with its own ASN/prefixes the valve still refuses a 95% drop (whois is the suspect)")



# =============================================================== 9. the attribution gate
print("\n== 9. a record on a shared VIP must NAME the customer to become a finding ==")
# The operator pulled Shodan's real records for abakus-tk.de's two addresses. Verbatim:
#   217.160.0.136           :80  http.host = mlslight.com
#   217.160.0.136           :443 hostnames  = bboca.de
#   2001:8d8:100f:f000::269 :443 http.host = www.stefan-ried.de, cert CN *.stefan-ried.de
# Not one names abakus-tk.de. The VIP requires SNI, so Shodan can never see the customer's vhost.
def _rec(ip, port, org, host=None, hostnames=(), cn=None):
    m = {"ip_str": ip, "port": port, "org": org, "transport": "tcp", "product": "nginx",
         "hostnames": list(hostnames), "http": {"host": host} if host else {},
         "location": {"country_code": "DE"}, "asn": "AS8560"}
    if cn:
        m["ssl"] = {"cert": {"subject": {"CN": cn}}}
    return m


VIP = [
    _rec("217.160.0.136", 80, "IONOS SE", host="mlslight.com",
         hostnames=["217-160-0-136.elastic-ssl.ui-r.com", "mlslight.com"]),
    _rec("217.160.0.136", 443, "IONOS SE", host="217.160.0.136",
         hostnames=["217-160-0-136.elastic-ssl.ui-r.com", "bboca.de"]),
    _rec("217.160.0.136", 8443, "IONOS SE", host="www.abakus-tk.de",
         hostnames=["abakus-tk.de"], cn="*.abakus-tk.de"),
]
_install_routing_shodan([("abakus-tk.de", VIP), ("217.160.0.136", VIP)], default=[])

ATTR = dict(BRANDY)
ATTR.update({"domains": ["abakus-tk.de"], "pinned": ["217.160.0.136"], "brand_variants": [],
             "related_unscoped": [], "asns": [], "nets": []})
ATTR.pop("scanned_ips", None)
R.run(ATTR, R.build_filters(ATTR), audience="internal", limit_per_query=500)

_ua = ATTR.get("records_unattributable") or []
_names = {d["name"] for d in _ua}
check(bool(_ua), "unattributable records were dropped and recorded (%d)" % len(_ua))
check(any("mlslight" in n for n in _names), "mlslight.com dropped - it is a co-tenant, not abakus")
check(any("bboca" in n for n in _names), "bboca.de dropped - co-tenant")
check("217.160.0.136" in set(ATTR.get("scanned_ips") or []),
      "the IP itself is KEPT: the record naming abakus-tk.de survives the gate")

# Fail-open case: a record with no names at all cannot be shown to be somebody else's. This is what
# protects the S-KON WatchGuard, whose only anchor is a self-signed certificate.
NONAME = [_rec("85.158.4.40", 443, "ScaleUp Technologies GmbH")]
_install_routing_shodan([("abakus-tk.de", NONAME)], default=[])
ATTR2 = dict(ATTR); ATTR2.update({"pinned": ["85.158.4.40"], "related_unscoped": []})
ATTR2.pop("scanned_ips", None); ATTR2.pop("records_unattributable", None)
R.run(ATTR2, R.build_filters(ATTR2), audience="internal", limit_per_query=500)
check("85.158.4.40" in set(ATTR2.get("scanned_ips") or []),
      "a record with NO names is kept - absence of evidence is never a finding")



# =============================================================== 10. DNS-derived findings
print("\n== 10. the zone produces findings when Shodan cannot ==")
# On abakus-tk.de every Shodan record belonged to a co-tenant, so the sweep can yield nothing
# attributable. The ZONE is unambiguously theirs, and it held two real findings: no CAA at all,
# and two names (intranet., dev.) resolving to addresses where Artfiles' own router answers
# host-unreachable -- verified by the operator with `nmap --reason`.
_install_routing_shodan([("abakus-tk.de", IONOS)], default=[])
_orig_caa, _orig_chain2 = R._caa, R._cname_chain
R._caa = lambda d: []                       # queried OK, genuinely no CAA published
R._cname_chain = lambda n: []               # nothing is a SaaS tenancy in this fixture

DNSF = dict(BRANDY)
DNSF.update({"domains": ["abakus-tk.de"], "pinned": ["217.160.0.136"], "brand_variants": [],
             "related_unscoped": [], "asns": [], "nets": [],
             "resolved": {"intranet.abakus-tk.de": ["212.72.175.109"],
                          "dev.abakus-tk.de": ["212.72.175.110"],
                          "www.abakus-tk.de": ["217.160.0.136"]}})
for k in ("scanned_ips", "records_unattributable", "resolved_no_service"):
    DNSF.pop(k, None)
_out = R.run(DNSF, R.build_filters(DNSF), audience="internal", limit_per_query=500)
_fts = {f.get("ft") for f in (_out.get("findings") or [])}
_titles = [f.get("title", "") for f in (_out.get("findings") or [])]

check("no_caa" in _fts, "missing CAA is a finding: %s" % [t for t in _titles if "CAA" in t][:1])
check("dns_no_service" in _fts, "names that resolve with no observable service are surfaced")
_ns = {d["name"] for d in (DNSF.get("resolved_no_service") or [])}
check("intranet.abakus-tk.de" in _ns and "dev.abakus-tk.de" in _ns,
      "both dead names flagged: %s" % sorted(_ns))
check("www.abakus-tk.de" not in _ns,
      "a name that DOES have an observable service is not flagged")

# A FAILED CAA lookup must never become a finding. Absence of evidence is never a finding.
R._caa = lambda d: None
DNSF2 = dict(DNSF)
for k in ("scanned_ips", "records_unattributable", "resolved_no_service"):
    DNSF2.pop(k, None)
DNSF2["resolved"] = {}
_out2 = R.run(DNSF2, R.build_filters(DNSF2), audience="internal", limit_per_query=500)
check("no_caa" not in {f.get("ft") for f in (_out2.get("findings") or [])},
      "a FAILED CAA lookup claims nothing (absence of evidence is never a finding)")
R._caa, R._cname_chain = _orig_caa, _orig_chain2



# =============================================================== 11. cert-name on a shared VIP
print("\n== 11. a neighbour's certificate on a shared VIP is not ownership ==")
# The one false positive left in the 2026-08-05 re-run: abakusconsulting.co.uk, a UK consulting
# firm, entered scope because "abakus" is a substring of "abakusconsulting" and its certificate sat
# on the same IONOS elastic-SSL VIP. It became a first-class seed and produced the deck's only
# remaining bad finding (H1, four CVEs on 2a00:da00:100f:f000::206).
def _certrec(ip, org, cn, sans):
    return {"ip_str": ip, "port": 443, "org": org, "transport": "tcp", "product": "nginx",
            "hostnames": [], "http": {}, "asn": "AS8560", "location": {"country_code": "GB"},
            "ssl": {"cert": {"subject": {"CN": cn},
                             "extensions": [{"name": "subjectAltName",
                                             "data": ",".join("DNS:" + s for s in sans)}]}}}


# (a) shared hoster + the cert names ONLY the neighbour -> refuse
NEIGH = [_certrec("2a00:da00:100f:f000::206", "1&1 IONOS SE", "*.abakusconsulting.co.uk",
                  ["*.abakusconsulting.co.uk", "abakusconsulting.co.uk"])]
_install_routing_shodan([("abakus-tk.de", NEIGH)], default=[])
CN1 = dict(BRANDY)
CN1.update({"domains": ["abakus-tk.de"], "pinned": [], "brand_variants": [],
            "brand_tokens": ["abakus"], "related_unscoped": [], "asns": [], "nets": []})
for k in ("scanned_ips", "cert_names_found", "cert_names_refused"):
    CN1.pop(k, None)
R.run(CN1, R.build_filters(CN1), audience="internal", limit_per_query=500)
check(not any("abakusconsulting" in str(d) for d in (CN1.get("domains") or [])),
      "abakusconsulting.co.uk is NOT scoped from a neighbour's cert on a shared VIP")
check(any("abakusconsulting" in str(x) for x in (CN1.get("cert_names_refused") or [])),
      "the refusal is recorded rather than silently dropped")

# (b) the bibeltv.de recall: the SAME certificate names the customer too -> that is real evidence
#     of common operation and must still bring the sibling domain into scope.
SIB = [_certrec("1.2.3.4", "1&1 IONOS SE", "bibeltv.de",
                ["bibeltv.de", "www.bibeltv.de", "bibel.tv"])]
_install_routing_shodan([("bibeltv.de", SIB)], default=[])
CN2 = dict(BRANDY)
# brand_tokens carries "bibel" as well as "bibeltv" because _brand_tokens_from() harvests the cert
# subject-O ("Bibel TV ...") -- that is what the real run had, and without it the fixture would be
# testing a target the engine never saw.
CN2.update({"seed": "bibeltv.de", "domains": ["bibeltv.de"], "pinned": [], "brand_variants": [],
            "brand_tokens": ["bibeltv", "bibel"], "related_unscoped": [], "asns": [], "nets": []})
for k in ("scanned_ips", "cert_names_found", "cert_names_refused"):
    CN2.pop(k, None)
R.run(CN2, R.build_filters(CN2), audience="internal", limit_per_query=500)
check(any("bibel.tv" in str(d) for d in (CN2.get("domains") or [])),
      "bibel.tv IS still scoped: the same certificate names the customer (shared SAN = common operation)")


# =============================================================== 12. one source for the counts
print("\n== 12. the inventory is derived from the FINAL estate, not the raw sweep ==")
# The 2026-08-05 deck said "1 UNIQUE IPS - 47 ASNS - 15 COUNTRIES" on slide 2 and "144 HOSTS -
# 12 ASNs" on slide 5. One host cannot span 47 autonomous systems. inv/asns/countries were
# accumulated during the query loop and never re-derived after the guards removed records.
MIX2 = [_h("217.160.0.136", "IONOS SE", ["abakus-tk.de"], asn="AS8560")] + \
       [_h("10.9.%d.1" % i, "Hetzner Online GmbH", ["someone-else-%d.de" % i], asn="AS24940")
        for i in range(1, 30)]
_install_routing_shodan([("abakus-tk.de", MIX2)], default=[])
INVT = dict(BRANDY)
INVT.update({"domains": ["abakus-tk.de"], "pinned": ["217.160.0.136"], "brand_variants": [],
             "related_unscoped": [], "asns": [], "nets": []})
INVT.pop("scanned_ips", None)
_o3 = R.run(INVT, R.build_filters(INVT), audience="internal", limit_per_query=500)
_s3 = _o3.get("summary") or {}
_ips3, _asns3 = _s3.get("unique_ips"), _s3.get("asns")
_inv_hosts = sum(int(r.get("hosts") or 0) for r in (_s3.get("inventory") or []))
check(_inv_hosts <= (_ips3 or 0),
      "inventory hosts (%s) never exceed unique IPs (%s)" % (_inv_hosts, _ips3))
check((_asns3 or 0) <= max(1, _ips3 or 0),
      "ASN count (%s) is consistent with %s surviving host(s)" % (_asns3, _ips3))


print("\n" + ("FAILED: %d" % len(FAILS) if FAILS else "ALL ABAKUS SCOPE CHECKS PASSED"))
for f in FAILS:
    print("   - " + f)
sys.exit(1 if FAILS else 0)
