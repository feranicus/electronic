#!/usr/bin/env python3
"""
test_run_path.py — EXECUTE shodan_recon.run() end-to-end against a mocked Shodan API.

WHY THIS EXISTS
The angermann.de outage was a one-word NameError (`seed_apex` where the local is `_seed_apex0`).
Every existing test passed, because they all exercise HELPER functions — _owns_apex, _org_is_the_target,
_apex — and never execute run(). A NameError only fires when the line runs. `ruff --select F821`
now catches that statically in ship.py, but a static check cannot prove BEHAVIOUR, so this test
drives the real function with a fake `shodan` module and asserts the co-tenant guard's outcome
on the actual shared Colt /24 from the angermann engagement.

    python test_run_path.py
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


def _install_fake_shodan(recs):
    """The engine uses api.search_cursor(); a stub with only .search() silently yields NO hosts."""
    fake = types.ModuleType("shodan")

    class _API:
        def __init__(self, *a, **k): pass
        def info(self): return {"plan": "basic", "query_credits": 100}
        def count(self, q, **k): return {"total": len(recs)}
        def search(self, q, **k): return {"total": len(recs), "matches": recs}
        def search_cursor(self, q, **k):
            for r in recs:
                yield r

    fake.Shodan = _API
    fake.APIError = Exception
    sys.modules["shodan"] = fake


def _ident(pinned):
    return {"seed": "angermann.de", "company": "Angermann", "domains": ["angermann.de"],
            "asns": [], "nets": [], "pinned": list(pinned), "brand_tokens": ["angermann"],
            "group_domains": ["netbid.com"], "group_pages": ["https://example/struktur"],
            "org": "Horst F.G. Angermann GmbH", "org_is_cdn": False, "shared_asns": [],
            "related_unscoped": [], "favicons": [], "issuers": [], "cert_orgs": [],
            "jarms": [], "cpes": [], "exclude_ips": [], "exclude_apexes": [], "ct_domains": []}


def _h(ip, org, names):
    return {"ip_str": ip, "port": 443, "org": org, "hostnames": list(names),
            "product": "nginx", "data": "HTTP/1.1 200 OK", "transport": "tcp"}


NET = [{"n": 1, "name": "net sweep", "clause": 'net:"217.110.51.0/24"', "run": True, "cat": "sweep"}]

print("== run() executes at all (the NameError regression) ==")
# The REAL shared Colt /24: Angermann holds .2/.7; the rest is a doctors' pension fund, FACT, Regus.
recs = [_h("217.110.51.2", "Horst F.G. Angermann GmbH", ["angermann.de"]),
        _h("217.110.51.7", "Horst F.G. Angermann GmbH", ["angermann.de"]),
        _h("217.110.51.18", "NORDRHEINISCHE AERZTEVERSORGUNG", ["naev.de"]),
        _h("217.110.51.122", "FACT Informationssysteme und Consulting GmbH", ["fact.de"]),
        _h("217.110.51.135", "Regus Gmbh and Co Kg", []),
        _h("87.234.246.51", "Netbid Industrie Aukrion AG", ["netbid.com"])]
_install_fake_shodan(recs)
import shodan_recon as R

ident = _ident(["217.110.51.2"])
try:
    R.run(ident, NET, "Internal")
    check(True, "run() completes without NameError")
except NameError as e:
    check(False, "run() raised NameError: %s" % e)
    print("\n%d FAILURE(S)" % len(FAILS)); sys.exit(1)

kept = set(ident.get("scanned_ips") or [])
dropped = {c["ip"] for c in (ident.get("cotenants_dropped") or [])}
check("217.110.51.2" in kept, "co-tenant guard KEEPS Angermann's own .2 (whois org corroborates)")
check("217.110.51.7" in kept, "co-tenant guard KEEPS Angermann's own .7")
check("87.234.246.51" in kept, "co-tenant guard KEEPS netbid.com (a group-structure domain)")
for ip, who in (("217.110.51.18", "Nordrheinische Aerzteversorgung"),
                ("217.110.51.122", "FACT"), ("217.110.51.135", "Regus")):
    check(ip in dropped and ip not in kept, "co-tenant guard DROPS %s (%s)" % (ip, who))

print("\n== the guard must never EMPTY a deck (audit_fp doctrine) ==")
recs2 = [_h("10.0.0.%d" % n, "Some Other Company GmbH", ["other.de"]) for n in range(1, 6)]
_install_fake_shodan(recs2)
import importlib
importlib.reload(R)
i2 = _ident([])
R.run(i2, [{"n": 1, "name": "net", "clause": 'net:"10.0.0.0/24"', "run": True, "cat": "sweep"}],
      "Internal")
check(len(i2.get("scanned_ips") or []) > 0,
      "when EVERY host looks foreign the guard refuses rather than shipping an empty deck")
check(not (i2.get("cotenants_dropped") or []), "nothing was dropped on the refusal path")
check(bool(i2.get("cotenants_refused")), "the refusal is recorded for observability")

print("\n" + "=" * 74)
print("  test_run_path: %s" % ("ALL PASSED" if not FAILS else "%d FAILURE(S)" % len(FAILS)))
print("=" * 74)
sys.exit(1 if FAILS else 0)
