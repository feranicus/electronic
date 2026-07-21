#!/usr/bin/env python3
"""
test_ca_pivot.py — regression test for the bibeltv.de false-positive incident.

    python hermes-skills/shodan-assessment/scripts/test_ca_pivot.py

WHAT WENT WRONG (2026-07, bibeltv.de):
The internal-CA pivot harvests issuer CNs off the estate and re-searches Shodan for them. Its only
guard was a substring match against PUBLIC_CAS ("let's encrypt", "digicert", ...). But Let's Encrypt
issues under bare codes (R3, R10-R14, E1-E9) and Google Trust Services under WR1/WE1/YR2 — CNs that
contain NO vendor name. So 'R12' and 'YR2' were classified as the customer's PRIVATE CA, and
`ssl.cert.issuer.cn:"R12"` was run against all of Shodan. ~998 unrelated hosts (cPanel resellers in
Brazil, Shopify, DigitalOcean droplets in Japan, AWS) were adopted as a small German broadcaster's
estate: 1003 IPs in the findings against 5 hosts on the asset-inventory slide.

No Shodan key needed — these are pure functions.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shodan_recon as R

FAILED = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILED.append(label)


def ident_for(seed, domains, brand=None, org=None):
    return {"seed": seed, "brand": brand, "org": org, "domains": domains,
            "org_variants": [], "brand_variants": []}


print("=" * 78)
print("  internal-CA pivot gate — bibeltv.de regression")
print("=" * 78)

bibel = ident_for("bibeltv.de", ["bibeltv.de"], brand="bibeltv")

print("\n[1] the exact CNs that caused the incident must be REFUSED")
for cn in ("R12", "YR2"):
    ok, why = R._private_ca_ok(cn, bibel, api=None)
    check(not ok, "%-28s refused (%s)" % (repr(cn), why))

print("\n[2] every other public intermediate shape must be REFUSED")
for cn in ("R3", "R10", "R11", "R13", "R14", "E1", "E5", "E6", "WR1", "WR2", "WE1",
           "YR1", "YR4", "X1", "X3", "GTS CA 1P5", "Let's Encrypt Authority X3",
           "DigiCert TLS RSA SHA256 2020 CA1", "Sectigo RSA Domain Validation Secure Server CA",
           "cPanel, Inc. Certification Authority", "Amazon RSA 2048 M02",
           "Google Trust Services LLC", "ZeroSSL RSA Domain Secure Site CA"):
    ok, why = R._private_ca_ok(cn, bibel, api=None)
    check(not ok, "%-46s refused (%s)" % (repr(cn), why[:34]))

print("\n[3] a GENUINE private CA carrying the customer's brand must be ALLOWED")
for cn in ("Bibel TV Issuing CA 01", "bibeltv Root CA", "BIBELTV-INTERNAL-CA"):
    ok, why = R._private_ca_ok(cn, bibel, api=None)
    check(ok, "%-30s allowed" % repr(cn))

print("\n[4] CA wording WITHOUT a brand token is refused when rarity cannot be checked")
# api=None => count() unavailable. CA wording alone is not enough: every public CA has it too.
for cn in ("Internal Issuing CA 02", "Corporate Root Certificate Authority"):
    ok, why = R._private_ca_ok(cn, bibel, api=None)
    check(not ok, "%-40s refused without rarity check" % repr(cn))


class FakeAPI:
    """Stands in for shodan.Shodan.count()."""
    def __init__(self, total): self.total = total
    def count(self, q): return {"total": self.total}


print("\n[5] the rarity gate is what makes this vendor-agnostic")
ok, why = R._private_ca_ok("Internal Issuing CA 02", bibel, api=FakeAPI(120))
check(ok, "unbranded CA signing 120 hosts    -> allowed (plausibly private)")
ok, why = R._private_ca_ok("Internal Issuing CA 02", bibel, api=FakeAPI(9_500_000))
check(not ok, "same CN signing 9.5M hosts        -> refused (%s)" % why[:40])
# even a brand-token CN must lose to overwhelming global usage
ok, why = R._private_ca_ok("Bibel TV Issuing CA 01", bibel, api=FakeAPI(4_000_000))
check(not ok, "branded CN signing 4M hosts       -> refused (shared)")


class BoomAPI:
    def count(self, q): raise RuntimeError("quota")


print("\n[6] when count() errors the gate fails CLOSED, not open")
ok, _ = R._private_ca_ok("Internal Issuing CA 02", bibel, api=BoomAPI())
check(not ok, "unbranded CN + count() error      -> refused")
ok, _ = R._private_ca_ok("Bibel TV Issuing CA 01", bibel, api=BoomAPI())
check(ok, "branded CN + count() error       -> allowed (brand is its own evidence)")

print("\n[7] corroboration: a pivot may not import hosts with no tie to the target")
own = {"AS24940"}
tied_asn = {"asn": 24940, "hostnames": [], "org": "Hetzner Online GmbH"}
tied_dom = {"asn": 999, "hostnames": ["www.bibeltv.de"], "org": "Whatever"}
stranger = {"asn": 14061, "hostnames": ["droplet.example.jp"], "org": "DigitalOcean"}
shopify = {"asn": 20473, "hostnames": ["shops.myshopify.com"], "org": "Choopa"}
check(R._corroborates(tied_asn, bibel, own), "host in the target's own ASN      -> kept")
check(R._corroborates(tied_dom, bibel, own), "host whose rDNS is bibeltv.de     -> kept")
check(not R._corroborates(stranger, bibel, own), "random DigitalOcean droplet (JP)  -> rejected")
check(not R._corroborates(shopify, bibel, own), "random Shopify host               -> rejected")

print("\n[8] brand tokens ignore legal-form noise")
toks = R._brand_tokens(ident_for("Bibel TV GmbH", ["bibeltv.de"], org="Bibel TV GmbH"))
check("bibeltv" in toks, "'bibeltv' extracted from the domain")
check("gmbh" not in toks, "'gmbh' excluded (would match half of Germany)")

print("\n" + "=" * 78)
if FAILED:
    print("  %d CHECK(S) FAILED" % len(FAILED))
    for f in FAILED:
        print("   - " + f)
    sys.exit(1)
print("  ALL CHECKS PASSED — the bibeltv.de pivot can no longer happen")
print("=" * 78)
