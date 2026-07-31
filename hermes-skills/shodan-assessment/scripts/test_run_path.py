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


def _install_routing_shodan(routes, default=()):
    """routes: [(substring_of_query, [records])] — first match wins. Mirrors the real API surface."""
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


print("\n== the lotto24.de failure: a malformed org: pivot must not own the estate ==")
# WHAT HAPPENED (2026-07). The whois org was "Lotto24 AG Hamburg, Germany". _LEGAL_SUFFIX is
# anchored with $, so nothing was stripped and the CITY AND COUNTRY went to Shodan as the identity
# anchor. `org:` is a full-text match, so org:"Lotto24 AG Hamburg, Germany" matched every
# Hamburg-registered netblock: +381 hosts against 15 the identity queries had proved. Every guard
# downstream then worked as designed and the run STILL died -- the co-tenant guard flagged 379,
# tripped its own >75% "never empty a deck" valve, refused, and the blow-out check aborted
# everything. The operator got nothing at all.
print("\n  (a) the address tail must never reach the pivot phrase")
for src, want in (("Lotto24 AG Hamburg, Germany", "Lotto24"),        # the bug
                  ("Lotto24 AG, Hamburg, Germany", "Lotto24"),
                  ("Deutsche Telekom AG Bonn, Germany", "Deutsche Telekom"),
                  ("S-KON Sales Kontor Hamburg GmbH", "S-KON Sales Kontor Hamburg"),  # no regress
                  ("Rosneft Deutschland GmbH", "Rosneft Deutschland"),  # country IS the name
                  ("AG Barr plc", "AG Barr")):                          # legal form leads
    got = R._org_core(src)
    check(got == want, "_org_core(%-34r) -> %r" % (src, got))

print("\n  (b) a pivot that dominates the estate is ROLLED BACK, and the run survives")
# 6 hosts are genuinely the target's; 400 are strangers a broad org: phrase dragged in. Each
# stranger carries the target's brand in its org so it passes per-host corroboration -- which is
# precisely the point: the budget is the defence that does NOT depend on spotting the bad string.
mine = [_h("203.0.113.%d" % n, "Lotto24", ["lotto24.de"]) for n in range(1, 7)]
junk = [_h("198.51.100.%d" % n, "Lotto24 AG Hamburg, Germany", []) for n in range(1, 201)]
junk += [_h("192.0.2.%d" % n, "Lotto24 AG Hamburg, Germany", []) for n in range(1, 201)]
# The identity query proves 6. Only the org: pivot returns the 400 strangers.
_install_routing_shodan([('net:"203.0.113', mine), ("org:", mine + junk)], default=mine)
importlib.reload(R)
i3 = dict(_ident(["203.0.113.1"]), seed="lotto24.de", company="Lotto24",
          domains=["lotto24.de"], brand_tokens=["lotto24"], group_domains=[],
          org="Lotto24 AG Hamburg, Germany", cert_orgs=["Lotto24 AG Hamburg, Germany"])
R.run(i3, [{"n": 1, "name": "pinned", "clause": 'net:"203.0.113.0/29"', "run": True, "cat": "pinned"}],
      "Lotto24")
rb = i3.get("pivots_rolled_back") or []
check(bool(rb), "an over-matching pivot is rolled back whole (%d rollback(s): %s)"
      % (len(rb), ", ".join("%s +%d" % (r["pivot"][:28], r["added"]) for r in rb[:2]) or "-"))
check(len(i3.get("scanned_ips") or []) <= 60,
      "the estate stays small after rollback (%d hosts, not 400+)" % len(i3.get("scanned_ips") or []))
check(not i3.get("scope_blowout"),
      "NO scope blow-out -> the operator gets a deck instead of 'assessment failed'")
check(bool(i3.get("pivot_budget")), "the budget actually used is recorded for observability")

print("\n" + "=" * 74)
print("  test_run_path: %s" % ("ALL PASSED" if not FAILS else "%d FAILURE(S)" % len(FAILS)))
print("=" * 74)
sys.exit(1 if FAILS else 0)
