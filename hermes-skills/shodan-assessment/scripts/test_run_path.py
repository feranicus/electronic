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

# ---------------------------------------------------------------------------------------------
# HERMETIC BY DEFAULT. run() performs three NETWORK lookups the older tests never had to think
# about: CertSpotter (Certificate Transparency), CAA over DNS-over-HTTPS, and the email
# authentication records. Left live, one `python ship.py` made ~14 CertSpotter calls and got HTTP
# 429 on every one -- burning the free tier's hourly budget that REAL assessments depend on.
#
# IT MUST BE RE-APPLIED AFTER EVERY importlib.reload(R). A reload rebuilds the module from source
# and restores the real functions, silently undoing the stub: the first version of this patched
# once at the top and the suite still made three live calls.
def _offline():
    R._certspotter_issuances = lambda *a, **k: []
    R._caa = lambda *a, **k: None                  # None = "could not ask" -> claims nothing
    try:
        import email_auth as _EA
        _EA.assess = lambda domain, txt_of=None: {"domain": domain, "issues": [], "context": [],
                                                  "spf": "unknown", "dmarc": "unknown",
                                                  "mta_sts": "unknown", "dkim_selectors": []}
    except Exception:
        pass


_offline()


ident = _ident(["217.110.51.2"])
try:
    R.run(ident, NET, "Internal")
    check(True, "run() completes without NameError")
except NameError as e:
    check(False, "run() raised NameError: %s" % e)
    print("\n%d FAILURE(S)" % len(FAILS)); sys.exit(1)

kept = set(ident.get("scanned_ips") or [])
# Assert the OUTCOME, not which guard produced it. Two gates now exclude a co-tenant and either is
# a correct answer: the attribution gate (the record names somebody else on shared/no-own-space
# infrastructure) runs first, and the co-tenant guard (whois org does not corroborate) second.
# The earlier version of this test named the mechanism, so tightening the earlier gate broke it
# while the behaviour it cares about was still exactly right.
excluded = ({c["ip"] for c in (ident.get("cotenants_dropped") or [])} |
            {r["ip"] for r in (ident.get("records_unattributable") or [])})
check("217.110.51.2" in kept, "Angermann's own .2 is KEPT (whois org corroborates)")
check("217.110.51.7" in kept, "Angermann's own .7 is KEPT")
check("87.234.246.51" in kept, "netbid.com is KEPT (a group-structure domain)")
for ip, who in (("217.110.51.18", "Nordrheinische Aerzteversorgung"),
                ("217.110.51.122", "FACT"), ("217.110.51.135", "Regus")):
    check(ip not in kept and ip in excluded,
          "%s (%s) is excluded from the estate and recorded" % (ip, who))

print("\n== an EMPTY estate is an honest outcome (doctrine CORRECTED 2026-08) ==")
# THIS ASSERTION USED TO BE THE OPPOSITE, and the inversion is deliberate.
#
# The old rule was "the guard must never empty a deck": if every remaining host looked foreign, it
# refused and kept them all. That was written for lotto24.de, where a malformed org: pivot injected
# 381 strangers and refusing at least left the operator with something.
#
# On abakus-tk.de (2026-08-05) the same rule produced the worst deck of the engagement. The
# attribution gate had already removed every record on the customer's shared IONOS VIP -- that day
# Shodan's records for it named pro-tec.org and parcarmeen.com -- so the 25 hosts left really were
# ALL strangers. The valve refused, and those 25 became SIX findings and a EUR 6-16M price tag on a
# 20-person telecoms reseller.
#
# "Nothing of yours is externally observable" is a TRUE, defensible and saleable result for a
# company whose whole presence is shared hosting and SaaS. A deck full of other people's servers is
# none of those things. The lotto24 case is now handled upstream by the per-pivot and per-domain
# budgets, so emptiness no longer has to be prevented here.
# The surviving refusal is narrower and still tested below: a mass drop on a target that OWNS
# address space means the whois data is the suspect, not the estate.
recs2 = [_h("10.0.0.%d" % n, "Some Other Company GmbH", ["other.de"]) for n in range(1, 6)]
_install_fake_shodan(recs2)
import importlib
importlib.reload(R)
_offline()
i2 = _ident([])
i2["asns"], i2["nets"] = [], []          # no address space of its own -> the abakus shape
R.run(i2, [{"n": 1, "name": "net", "clause": 'net:"10.0.0.0/24"', "run": True, "cat": "sweep"}],
      "Internal")
check(not (i2.get("scanned_ips") or []),
      "with no address space of its own, strangers are DROPPED even if that empties the estate")
check(not i2.get("cotenants_refused"),
      "emptiness alone is no longer a reason to keep other companies' hosts")
check(bool(i2.get("no_attributable_estate")),
      "the empty outcome is stated explicitly rather than left as a silent zero")

print("\n  ...but a target that OWNS address space still gets the lotto24 refusal")
i2b = _ident([])
i2b["asns"], i2b["nets"] = ["AS8220"], ["10.0.0.0/24"]
_install_fake_shodan(recs2)
importlib.reload(R)
_offline()
R.run(i2b, [{"n": 1, "name": "net", "clause": 'net:"10.0.0.0/24"', "run": True, "cat": "sweep"}],
      "Internal")
check(bool(i2b.get("cotenants_refused")),
      "own ASN/prefixes + a mass drop -> the whois data is the suspect, keep everything and say so")


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
_offline()
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
