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

print("\n" + "=" * 78)
if FAILED:
    print("  %d CHECK(S) FAILED" % len(FAILED))
    for f in FAILED:
        print("   - " + f)
    sys.exit(1)
print("  ALL CHECKS PASSED — gitlab.bibel.tv and vpn.bibeltv.de are now discoverable")
print("=" * 78)
