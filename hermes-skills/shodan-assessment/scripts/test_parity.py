#!/usr/bin/env python3
"""
test_parity.py — THE ACCEPTANCE TEST: the platform must not find less than manual Shodan work.

The operator's standing requirement, in his words:
    "I do not want to have any difference between what I harvest in shodan with manual filters
     and using our platform."

So this replays his ACTUAL angermann.de Shodan exports (fixtures/angermann_shodan_manual.json,
75 host:port harvested by hand) through the engine's ownership gate and classifier, and asserts:

  RECALL    — every host the operator proved is Angermann's is IN scope, and the crown-jewel
              findings are classified at the right severity.
  PRECISION — every host belonging to a co-tenant, a lookalike or a third party is OUT.

This is the test that would have caught all three of the failures the operator reported:
  * netbid.com / leaseback.de / buerosuche.de silently out of scope (group domains never scanned)
  * angermann.3cx.eu invisible (vendor-hosted tenant: brand in the label, apex owned by 3CX)
  * an internet-facing Passbolt vault filed as LOW/standard_service -> a deck reporting CRITICAL 0

    python test_parity.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("SHODAN_API_KEY", "test")
import shodan_recon as R                                                          # noqa: E402

FIX = os.path.join(HERE, "fixtures", "angermann_shodan_manual.json")
RECS = json.load(open(FIX, encoding="utf-8"))

SEED = "angermann.de"
BTOKS = {"angermann"}
# exactly what angermann.de publishes on its own structure page
GROUP = {"angermann-realestate.de", "angermann-consult.de", "buerosuche.de",
         "netbid.com", "nordleasing.com", "leaseback.de", "oaklins.com"}
STRUCTURE_KNOWN = True

FAILS = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


def _names(r):
    out = set(str(h).lower() for h in (r.get("hostnames") or []))
    c = ((r.get("ssl") or {}).get("cert") or {}).get("subject") or {}
    if c.get("CN"):
        out.add(str(c["CN"]).lower().lstrip("*."))
    return out


def in_scope(r):
    """Would the engine keep this host? name-based ownership OR the host's own whois org."""
    for n in _names(r):
        if R._owns_host(n, BTOKS, SEED, GROUP, STRUCTURE_KNOWN)[0]:
            return True
    if r.get("org") and R._org_is_the_target(r["org"], SEED):
        return True
    return False


by_ip = {}
for r in RECS:
    by_ip.setdefault(r["ip_str"], []).append(r)

print("== RECALL: every host the operator proved is Angermann's must be IN scope ==")
MUST_INCLUDE = {
    "217.110.51.2":   "angermann.de web (own whois org)",
    "217.110.51.7":   "passbolt.angermann.de - the PASSWORD VAULT",
    "87.234.246.51":  "netbid.com (group subsidiary)",
    "87.234.246.52":  "netbid.com (group subsidiary)",
    "136.243.14.241": "leaseback.de (group subsidiary)",
    "46.30.5.71":     "buerosuche.de (group subsidiary)",
    "185.58.227.251": "netbid.io mail cluster - EXPIRED cert on 7 ports",
    "94.16.117.249":  "angermann.3cx.eu - 3CX PBX on a VENDOR domain",
}
for ip, why in sorted(MUST_INCLUDE.items()):
    check(ip in by_ip and any(in_scope(r) for r in by_ip[ip]), "IN  %-16s %s" % (ip, why))

print("\n== PRECISION: co-tenants, lookalikes and third parties must be OUT ==")
MUST_EXCLUDE = {
    "217.110.51.18":  "Nordrheinische Aerzteversorgung (shared Colt /24 co-tenant)",
    "217.110.51.20":  "Nordrheinische Aerzteversorgung",
    "217.110.51.122": "FACT Informationssysteme (co-tenant)",
    "217.110.51.135": "Regus (co-tenant)",
    "217.110.51.61":  "NAGASE Europa (co-tenant)",
    "142.132.178.138": "ra-angermann.de - a LAW FIRM (surname lookalike)",
    "167.233.20.201": "ra-angermann.de - law firm",
    "178.77.85.84":   "angermann-webdesign.de - unrelated agency",
    "79.214.82.129":  "Zahnarztpraxis Angermann - a DENTAL PRACTICE",
}
for ip, why in sorted(MUST_EXCLUDE.items()):
    if ip not in by_ip:
        continue
    check(not any(in_scope(r) for r in by_ip[ip]), "OUT %-16s %s" % (ip, why))

print("\n== SEVERITY: the crown jewels must not be filed as routine ==")
CROWN = [("217.110.51.7", 443, "CRITICAL", "secrets_manager", "Passbolt password vault"),
         ("94.16.117.249", 5001, "HIGH", "pbx_exposed", "3CX PBX web client")]
for ip, port, sev, kind, label in CROWN:
    rec = next((r for r in by_ip.get(ip, []) if r.get("port") == port), None)
    if rec is None:
        check(False, "%s:%s present in the fixture" % (ip, port))
        continue
    got_sev, got_kind = R.classify(rec)
    check(got_sev == sev and got_kind == kind,
          "%-16s %s -> %s/%s (got %s/%s)" % (ip, label, sev, kind, got_sev, got_kind))

print("\n== NO OVER-TRIGGERING: a plain web server stays low ==")
plain = {"port": 443, "product": "nginx", "http": {"title": "Welcome to nginx!"}}
check(R.classify(plain)[0] in ("LOW", "MEDIUM"), "plain nginx is not escalated")

print("\n== SCOPE SHAPE: how much of the manual harvest do we now agree with? ==")
kept = [ip for ip, rs in by_ip.items() if any(in_scope(r) for r in rs)]
print("     manual harvest: %d IPs · engine keeps %d · drops %d"
      % (len(by_ip), len(kept), len(by_ip) - len(kept)))
check(len(kept) >= 8, "at least the 8 proven Angermann hosts are in scope")

print("\n" + "=" * 78)
print("  test_parity: %s" % ("ALL PASSED" if not FAILS else "%d FAILURE(S)" % len(FAILS)))
print("=" * 78)
sys.exit(1 if FAILS else 0)
