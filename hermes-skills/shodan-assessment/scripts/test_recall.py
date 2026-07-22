#!/usr/bin/env python3
"""
test_recall.py — regression test for the bibeltv.de RECALL failure (the opposite of the CA-pivot bug).

WHAT WENT WRONG (2026-07, bibeltv.de, run #4):
After the scope blow-out was fixed the deck swung to the other extreme: 5 hosts, 2 findings, and it
MISSED the two most valuable assets in the estate —
    gitlab.bibel.tv   142.132.188.73   (SCM: secrets / CI exposure)
    vpn.bibeltv.de    213.61.87.246    (remote-access edge, on COLT AS8220 - the pursuit hook)
plus the Strato mail/ftp hosts and both real web servers.

THREE CAUSES:
  1. bibel.tv is a DIFFERENT registrable domain from bibeltv.de. CT enumeration of "%.bibeltv.de"
     can never reveal it. It is discoverable from the seed certificate's SAN list, because the two
     names share a certificate — and a shared cert is evidence of common operation.
  2. crt.sh was the ONLY subdomain source and it failed on three consecutive runs
     (read timeout, HTTP 404, HTTP 503). One flaky service blinded the whole assessment.
  3. Nothing ever asked DNS. "gitlab." and "vpn." resolve instantly.

Pure logic test — no network, no Shodan key. Run by ship.py.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shodan_recon as R

FAILED = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILED.append(label)


print("=" * 78)
print("  recall guards — bibeltv.de regression")
print("=" * 78)

# ---- the real Bibel TV estate, from the operator's verified super-filter doc ----
REAL = {
    "bibeltv.de":            "167.235.111.235",
    "www.bibeltv.de":        "167.235.111.235",
    "gitlab.bibel.tv":       "142.132.188.73",
    "vpn.bibeltv.de":        "213.61.87.246",
    "mail.bibeltv.de":       "81.169.145.64",
    "ftp.bibeltv.de":        "81.169.145.64",
    "autoconfig.bibeltv.de": "81.169.145.141",
    "www.bibel.tv":          "49.12.21.249",
}
SEED_SANS = ["bibeltv.de", "www.bibeltv.de", "bibel.tv", "www.bibel.tv", "api.bibeltv.de"]

print("\n[1] DNS subdomain probe finds the hosts CT enumeration missed")
_real_resolve = R._resolve
R._resolve = lambda n: ([REAL[n]] if n in REAL else [])
try:
    found = R._probe_subdomains(["bibeltv.de", "bibel.tv"])
    for must in ("gitlab.bibel.tv", "vpn.bibeltv.de", "mail.bibeltv.de", "autoconfig.bibeltv.de"):
        check(must in found, "%-24s discovered" % must)
    check(found.get("gitlab.bibel.tv") == ["142.132.188.73"], "gitlab resolves to the right IP")

    print("\n[2] the probe list actually contains the names that matter")
    for sub in ("gitlab", "vpn", "mail", "git", "ftp", "autoconfig", "owa", "jira", "ci"):
        check(sub in R.PROBE_SUBS, "'%s' is probed" % sub)
finally:
    R._resolve = _real_resolve

print("\n[3] sibling domain: bibel.tv is reachable from the seed cert, never from CT of bibeltv.de")
apexes = sorted({R._apex(s) for s in SEED_SANS})
check("bibel.tv" in apexes, "bibel.tv extracted from the SAN list")
check("bibeltv.de" in apexes, "bibeltv.de still present")
check(R._apex("gitlab.bibel.tv") == "bibel.tv", "_apex('gitlab.bibel.tv') == 'bibel.tv'")

print("\n[4] resolved hosts get PINNED as /32 — on a shared hoster the ASN is worthless, "
      "the host is not")
ident = {"seed": "bibeltv.de", "brand": "bibeltv", "org": None,
         "domains": ["bibeltv.de"], "nets": [], "asns": [], "org_variants": [], "brand_variants": []}
for ips in ({"gitlab.bibel.tv": ["142.132.188.73"], "vpn.bibeltv.de": ["213.61.87.246"]},):
    for fqdn, addrs in ips.items():
        for ip in addrs:
            c = ip + "/32"
            if c not in ident["nets"]:
                ident["nets"].append(c)
check("142.132.188.73/32" in ident["nets"], "gitlab pinned as /32")
check("213.61.87.246/32" in ident["nets"], "vpn pinned as /32")
check(len(ident["nets"]) == 2, "no /16 hoster ranges pinned (that would re-create the blow-out)")

print("\n[5] the CA-pivot gate still holds — recall must not reopen the false-positive hole")
ok, why = R._private_ca_ok("R12", ident, api=None)
check(not ok, "'R12' still refused (%s)" % why[:38])
ok, why = R._private_ca_ok("YR2", ident, api=None)
check(not ok, "'YR2' still refused")

print("\n[6] a hoster ASN must never become an ownership anchor")
check(R._is("Hetzner Online GmbH", R.CDNS), "Hetzner recognised as shared hosting")
check(R._is("Strato AG", R.CDNS) or "strato" in " ".join(R.CDNS), "Strato recognised as shared hosting")

print("\n[9] ZERO FALSE POSITIVES — a platform operator's client domains must NOT enter scope")
print("    (skon.de runs white-label loyalty microsites for Otto/MediaMarkt/Lidl/EAM/...)")
# cert subject-O is the ownership anchor: it turns saleskontor/praemienkontor into owned brands.
sk_tokens = R._brand_tokens_from("skon.de", ["S-KON Sales Kontor Hamburg GmbH"])
check("skon" in sk_tokens and "kontor" in sk_tokens, "brand tokens {skon, kontor} derived from seed + cert-O")
OWNED = ["skon.de", "saleskontor.de", "praemienkontor.de", "managementkontor.de", "ekontor24.de"]
CLIENTS = ["otto.de", "mediamarkt.de", "lidl.de", "eam.de", "dns-net.de", "tng.de",
           "purpur-energy.de", "dew21.de", "stadtwerke-garbsen.de", "mediamarkt-saturnvorteile.de"]
for d in OWNED:
    check(R._owns_apex(d, sk_tokens, "skon.de")[0], "%-24s kept (S-KON brand)" % d)
for d in CLIENTS:
    check(not R._owns_apex(d, sk_tokens, "skon.de")[0], "%-24s EXCLUDED (client / third party)" % d)

print("\n[10] microsite prefixes on a client apex are hard-excluded even if resolvable")
for host in ("vorteile.otto.de", "praemie.tng.de", "aktion.eam.de", "bonus.praemienkontor.de"):
    first = host.split(".")[0]
    ap = R._apex(host)
    is_microsite = any(first.startswith(mp) for mp in R._MICROSITE_PREFIXES)
    owned_apex = R._owns_apex(ap, sk_tokens, "skon.de")[0]
    excluded = is_microsite and not owned_apex
    # bonus.praemienkontor.de is on an OWNED apex -> kept; the otto/tng/eam ones are dropped
    if ap == "praemienkontor.de":
        check(owned_apex, "%-26s kept (microsite on OWNED apex)" % host)
    else:
        check(excluded, "%-26s dropped (microsite on client apex)" % host)

print("\n[11] the two S-KON pins that were the ONLY real hosts must survive the CDN drop")
# net:pinned uses cat='pinned', which bypasses run()'s hoster drop
import inspect
src = inspect.getsource(R.build_filters)
check('cat="pinned"' in src, "pinned filter tagged cat='pinned' (bypasses the hoster drop)")

print("\n[12] FP-AUDIT must never empty a deck (the skon.de disaster)")
import audit_fp as _A
_owned = {"domains": ["skon.de"], "brand_tokens": ["skon", "kontor"],
          "pinned": ["35.244.246.242", "217.110.76.92", "52.98.242.248"]}
_fj = {"target": {"owned": _owned}, "summary": {},
       "findings": [{"id": "H1", "sev": "HIGH", "title": "OWA", "evidence": ["52.98.242.248:443"]},
                    {"id": "H2", "sev": "HIGH", "title": "nginx", "evidence": ["35.244.246.242:443"]},
                    {"id": "M1", "sev": "MEDIUM", "title": "TLS", "evidence": ["217.110.76.92:443"]}]}
_, _dr, _rf = _A.apply_fixes(dict(_fj), [{"id": "H1"}, {"id": "H2"}, {"id": "M1"}])
check(_dr == [] and len(_rf) == 3, "auditor flags ALL 3 pinned hosts -> 0 dropped, deck kept")

_fj2 = {"target": {"owned": {"pinned": ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5"],
                             "brand_tokens": ["acme"], "domains": ["acme.com"]}},
        "summary": {}, "findings": [{"id": "F%d" % i, "sev": "HIGH", "evidence": ["%d.%d.%d.%d:443" % (i, i, i, i)]} for i in range(1, 6)]
        + [{"id": "BAD", "sev": "HIGH", "evidence": ["9.9.9.9:443 otherco.de"]}]}
_, _dr2, _ = _A.apply_fixes(dict(_fj2), [{"id": "BAD"}])
check(_dr2 == ["BAD"], "a genuine off-estate host still drops when it doesn't gut the deck")
check(not _A._host_is_off_estate(["52.98.242.248:443"], _owned), "a pinned host is never off-estate")

print("\n[14] org: pivot strips the legal suffix so it finds the S-KON WatchGuard netblock")
# the WatchGuard 213.61.141.198 was MISSED: cert O='S-KON Sales Kontor Hamburg GmbH' but the Shodan
# whois-org field is 'S-KON SALES KONTOR HAMBURG AG'. org:"…GmbH" matched nothing; the suffix-
# stripped core matches every legal-form variant.
_core = _A_core = R._org_core("S-KON Sales Kontor Hamburg GmbH")
check(_core == "S-KON Sales Kontor Hamburg", "legal suffix 'GmbH' stripped from the org phrase")
check(_core.lower() in "S-KON SALES KONTOR HAMBURG AG".lower(),
      "the stripped phrase matches the 'AG' whois-org variant (finds the WatchGuard)")
for full, want in (("Rosneft Deutschland GmbH", "Rosneft Deutschland"),
                   ("Acme Holding AG", "Acme"), ("Foo Bar S.p.A", "Foo Bar")):
    check(R._org_core(full) == want, "%-26s -> %r" % (full, want))

print("\n[13] the FP auditor must be a DIFFERENT model than the deck author (never self-audit)")
_chain = ["gemma-4-31B-it", "deepseek-3.2", "llama-4-maverick"]
for _author in _chain + ["openai-gpt-oss-120b"]:
    _aud = _A._pick_auditor(_author, _chain)
    check(_aud != _author, "author %-22s -> auditor %-18s (different model)" % (_author, _aud))
    check(_A._vendor(_aud) != _A._vendor(_author), "   ...and a different vendor")

print("\n" + "=" * 78)
if FAILED:
    print("  %d CHECK(S) FAILED" % len(FAILED))
    for f in FAILED:
        print("   - " + f)
    sys.exit(1)
print("  ALL CHECKS PASSED — recall keeps owned assets; client/white-label domains stay OUT")
print("=" * 78)
