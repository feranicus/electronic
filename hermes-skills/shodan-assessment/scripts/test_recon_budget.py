#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_recon_budget.py -- the recon phase is bounded by a wall clock, and a truncated recon says so.

THE INCIDENT (caixabank.es, 2026-09-30). A run sat at 55% "Shodan recon + Top-10 super-filters"
for over 22 minutes: 32 certificate-discovered domains, ~400 hostnames, one whois-org pivot
adding +477 hosts, and Shodan throttling the basic plan between pages. Enrichment had a ceiling
(ENRICH_TIMEOUT / ENRICH_BUDGET_S / the 430 s kill); recon had none. The UI promised two minutes.

WHAT THIS PROVES, each with a mutation that was run by hand to show the check can fail:
  1. Recon stops at the budget and returns what it has. The stub Shodan advances a FAKE clock on
     every page it serves, so elapsed is deterministic and the test never sleeps.
  2. ONCE THE BUDGET IS SPENT, NOT ONE MORE REQUEST IS ISSUED. The stub records the clock at the
     moment each request starts; the budget check must sit at loop boundaries BEFORE the next
     unit of work, so no request may start at or after the deadline. (A request already in
     flight is always allowed to finish -- that is also asserted: the page being served when the
     clock crossed the line is kept.)
  3. A run under budget has NO `recon_truncated` key on ident and NO `partial_estate` in the
     summary -- absent, not None, not {}.
  4. A truncated run carries the partial-estate statement in the summary, `scanner_blind` and
     `no_attributable_estate` are NOT claimed, and the deck renders the statement.
  5. FAIL OPEN: a garbage or negative RECON_BUDGET_S applies the default; a clock that raises
     never truncates; a run never aborts because of the budget.
  6. The identity-discovery loops (DNS probe, CT-name resolution) obey the same budget.
  7. The web UI no longer tells the operator that refreshing cancels the run, in every locale.

    python test_recon_budget.py
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import zipfile

os.environ.setdefault("SHODAN_API_KEY", "test")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FAILS = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


# ------------------------------------------------------------------ the fake clock + fake Shodan
class Clock:
    """A monotonic clock the STUB advances. Nothing in this test sleeps."""
    def __init__(self):
        self.t = 0.0
        self.broken = False

    def __call__(self):
        if self.broken:
            raise RuntimeError("clock unavailable")
        return self.t


CLOCK = Clock()
CALLS = []            # (kind, query, clock_at_issue) for every request the stub served


def _host(ip, names=("caixabank.es",)):
    return {"ip_str": ip, "port": 443, "org": "CaixaBank SA", "hostnames": list(names),
            "product": "nginx", "data": "HTTP/1.1 200 OK", "transport": "tcp",
            "asn": "AS15436"}


def _install_shodan(records_per_query, page_cost_s, page=100):
    """Every query serves `records_per_query` records in pages of `page`; each PAGE advances the
    clock by `page_cost_s` at the moment the page is fetched (the HTTP call)."""
    fake = types.ModuleType("shodan")

    class _API:
        def __init__(self, *a, **k): pass
        def info(self): return {"plan": "basic", "query_credits": 100}
        def count(self, q, **k):
            CALLS.append(("count", q, CLOCK.t)); return {"total": 5}
        def search(self, q, **k):
            CALLS.append(("search", q, CLOCK.t)); return {"total": 0, "matches": []}
        def search_cursor(self, q, **k):
            tag = re.sub(r"[^a-z0-9]", "", q.lower())[:12]
            n = 0
            while n < records_per_query:
                CALLS.append(("page", q, CLOCK.t))       # the HTTP call starts NOW
                CLOCK.t += page_cost_s                   # ...and takes this long
                for i in range(min(page, records_per_query - n)):
                    yield _host("10.%d.%d.%d" % (len(CALLS) % 250, (n + i) // 250, (n + i) % 250))
                n += page
    fake.Shodan = _API
    fake.APIError = Exception
    sys.modules["shodan"] = fake


def _offline(R):
    R._certspotter_issuances = lambda *a, **k: []
    R._caa = lambda *a, **k: None
    try:
        import email_auth as _EA
        _EA.assess = lambda domain, txt_of=None: {"domain": domain, "issues": [], "context": [],
                                                  "spf": "unknown", "dmarc": "unknown",
                                                  "mta_sts": "unknown", "dkim_selectors": []}
    except Exception:
        pass


def _ident():
    return {"seed": "caixabank.es", "company": "CaixaBank", "domains": ["caixabank.es"],
            "asns": ["AS15436"], "nets": ["10.0.0.0/8"], "pinned": [], "brand_tokens": ["caixabank"],
            "group_domains": [], "group_pages": [], "org": "CaixaBank SA", "org_is_cdn": False,
            "shared_asns": [], "related_unscoped": [], "favicons": [], "issuers": [],
            "cert_orgs": [], "jarms": [], "cpes": [], "exclude_ips": [], "exclude_apexes": [],
            "ct_domains": [], "resolved": {"www.caixabank.es": ["10.0.0.1"]}}


def _filters(n):
    return [{"n": i, "name": "q%d" % i, "clause": 'hostname:"q%d.caixabank.es"' % i,
             "run": True, "cat": "identity"} for i in range(n)]


def _fresh(budget_s, records_per_query=300, page_cost_s=10.0):
    """A reloaded engine with a fresh budget bound to the fake clock."""
    import importlib
    CLOCK.t = 0.0; CLOCK.broken = False; del CALLS[:]
    _install_shodan(records_per_query, page_cost_s)
    import shodan_recon as R
    importlib.reload(R)
    _offline(R)
    # Started here, as run_assessment starts it before identity resolution: the clock covers the
    # whole recon phase, not just run().
    R.recon_budget(reset=True, budget_s=budget_s, clock=CLOCK).start()
    return R


# ================================================================================================
print("== 1. recon stops at the budget and keeps what it gathered ==")
# 20 queries x 3 pages x 10 s = 600 s of Shodan time against a 100 s budget.
R = _fresh(budget_s=100)
ident = _ident()
out = R.run(ident, _filters(20), "Internal")
tr = ident.get("recon_truncated")
check(isinstance(tr, dict) and tr, "ident['recon_truncated'] is populated: %s"
      % (json.dumps({k: v for k, v in (tr or {}).items() if k != "skipped"}) if tr else "MISSING"))
check(tr and tr.get("budget_s") == 100, "the record names the budget (100 s)")
check(tr and tr.get("elapsed_s") is not None and tr["elapsed_s"] >= 100,
      "the record names the elapsed time at the stop (%s s)" % (tr or {}).get("elapsed_s"))
check(tr and tr.get("phase") == "Shodan queries" and tr.get("unit") == "queries",
      "the record names the phase and the unit (%s / %s)" % ((tr or {}).get("phase"), (tr or {}).get("unit")))
check(tr and tr.get("pending", 0) > 0 and tr.get("done", 0) < 20,
      "the record says how much was NOT done: %s of %s done, %s pending"
      % ((tr or {}).get("done"), (tr or {}).get("total"), (tr or {}).get("pending")))
check(len(ident.get("scanned_ips") or []) > 0,
      "everything gathered before the stop is KEPT (%d hosts)" % len(ident.get("scanned_ips") or []))
check(CLOCK.t < 600, "elapsed is bounded: the stub clock reads %.0f s, not the 600 s a full run costs" % CLOCK.t)

print("\n== 2. once the budget is spent, no new request starts (the boundary property) ==")
late = [c for c in CALLS if c[2] >= 100]
check(not late, "no request was ISSUED at or after the 100 s deadline (%d late: %s)"
      % (len(late), late[:2]))
# The page that was in flight when the clock crossed the line: issued at 90 s, served at 100 s.
# Its records must be in the estate -- an in-flight call is never interrupted.
inflight = [c for c in CALLS if c[2] < 100 and c[2] + 10 >= 100]
check(bool(inflight), "a page WAS in flight when the deadline passed (issued at %s)"
      % ([c[2] for c in inflight] or "none"))
check(bool(tr) and tr.get("hosts_queried", 0) > 0,
      "hosts_queried counts the hosts held at the moment of the stop (%s)" % (tr or {}).get("hosts_queried"))
check(getattr(R.recon_budget(), "checks", 0) > 0,
      "the boundary check actually RAN (%d times)" % R.recon_budget().checks)

print("\n== 3. a run under budget has NO truncation key -- absent, not None, not {} ==")
R = _fresh(budget_s=10_000)
ident_ok = _ident()
out_ok = R.run(ident_ok, _filters(3), "Internal")
check("recon_truncated" not in ident_ok, "ident has no 'recon_truncated' key at all")
check("partial_estate" not in out_ok["summary"], "summary has no 'partial_estate' key at all")
_qpages = [c for c in CALLS if c[0] == "page" and c[1].startswith("hostname:")]
_ppages = [c for c in CALLS if c[0] == "page" and c[1].startswith("org:")]
check(len(_qpages) == 9, "all 3 queries ran to completion (%d query pages = 3 x 3)" % len(_qpages))
check(len(_ppages) == 3, "...and the whois-org pivot ran too (%d pivot pages): nothing was cut" % len(_ppages))
check(R.recon_budget().checks > 0, "...and the check still ran on every boundary (%d)" % R.recon_budget().checks)

print("\n== 4. the truncation reaches the customer ==")
pe = out["summary"].get("partial_estate")
check(isinstance(pe, dict) and "statement" in pe, "summary.partial_estate carries a statement")
st = (pe or {}).get("statement", "")
check(st.startswith("Partial estate: recon stopped at the time budget"),
      "the statement says PARTIAL ESTATE and names the budget: %r" % st[:90])
check(re.search(r"\b%d of %d Shodan queries completed\b" % (tr["done"], tr["total"]), st) is not None,
      "the statement says N of M queries completed (%d of %d)" % (tr["done"], tr["total"]))
check("unknown, not absent" in st, "the statement says unqueried hosts are UNKNOWN, not absent")
check(len((pe or {}).get("sentences") or []) == 3, "three sentences, so the deck packs translate each by pattern")
check("\u2014" not in st, "no em dash in customer-facing copy")

# Truncated before ANY host arrived: the scanner is not "blind", the clock stopped it.
R = _fresh(budget_s=5, records_per_query=100, page_cost_s=10.0)
ident_b = _ident()
CLOCK.t = 6.0                                     # identity resolution already spent the budget
out_b = R.run(ident_b, _filters(4), "Internal")
check(not (ident_b.get("scanned_ips") or []), "fixture: nothing was gathered (budget spent before the first query)")
check(out_b["summary"]["scanner_blind"] is False,
      "scanner_blind is NOT claimed on a truncated run (DNS proves hosts, but the scanner never asked)")
check("no_attributable_estate" not in ident_b,
      "no_attributable_estate is NOT claimed on a truncated run (an empty set means the clock, not the estate)")
check("resolved_no_service" not in ident_b,
      "no 'possible retired host' candidates from a run that never queried them")
check(not [c for c in CALLS if c[0] == "page"], "and not one Shodan page was fetched")

print("\n== 4b. the findings deck renders the partial-estate statement ==")
sample = json.load(io.open(os.path.join(HERE, "..", "sample", "findings.sample.json"), encoding="utf-8"))
sample.setdefault("summary", {})["partial_estate"] = pe
sample["target"].pop("exec_summary", None)
tmp = tempfile.mkdtemp()
pj = os.path.join(tmp, "partial.json")
io.open(pj, "w", encoding="utf-8").write(json.dumps(sample, ensure_ascii=False))
pptx = os.path.join(tmp, "partial.pptx")
r = subprocess.run(["node", os.path.join(HERE, "build_findings_deck.js"), pj, pptx],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                   env={**os.environ, "DECK_LANG": "en"})
check(os.path.exists(pptx), "deck builds with a partial_estate summary%s"
      % ("" if os.path.exists(pptx) else " " + (r.stderr or "")[-200:]))
if os.path.exists(pptx):
    z = zipfile.ZipFile(pptx)
    s2 = z.read("ppt/slides/slide2.xml").decode("utf8")
    txt2 = "".join(re.findall(r"<a:t>(.*?)</a:t>", s2, re.S))
    check("Partial estate." in txt2, "slide 2 carries the 'Partial estate.' banner")
    check("Shodan queries completed" in txt2, "slide 2 says how many queries completed")
    check("unknown, not absent" in txt2, "slide 2 says unqueried hosts are unknown, not absent")
    check("Partial estate: recon stopped" in txt2,
          "the deterministic exec paragraph leads with the statement when no model prose exists")
    # and NOT on a complete run
    sample["summary"].pop("partial_estate")
    io.open(pj, "w", encoding="utf-8").write(json.dumps(sample, ensure_ascii=False))
    pptx2 = os.path.join(tmp, "complete.pptx")
    subprocess.run(["node", os.path.join(HERE, "build_findings_deck.js"), pj, pptx2],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                   env={**os.environ, "DECK_LANG": "en"})
    t2 = "".join(re.findall(r"<a:t>(.*?)</a:t>", zipfile.ZipFile(pptx2).read("ppt/slides/slide2.xml").decode("utf8"), re.S))
    check("Partial estate" not in t2 and "Passive only." in t2,
          "a complete run keeps the passive-only strip and never says partial")
    # German: the pattern pack translates each sentence
    sample["summary"]["partial_estate"] = pe
    io.open(pj, "w", encoding="utf-8").write(json.dumps(sample, ensure_ascii=False))
    pptx3 = os.path.join(tmp, "partial_de.pptx")
    subprocess.run(["node", os.path.join(HERE, "build_findings_deck.js"), pj, pptx3],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                   env={**os.environ, "DECK_LANG": "de"})
    t3 = "".join(re.findall(r"<a:t>(.*?)</a:t>", zipfile.ZipFile(pptx3).read("ppt/slides/slide2.xml").decode("utf8"), re.S))
    check("Unvollst" in t3 and "Shodan-Abfragen abgeschlossen" in t3,
          "the German deck renders the statement in German (not English pass-through)")

print("\n== 5. fail open ==")
for bad in ("abc", "-5", "0", ""):
    os.environ["RECON_BUDGET_S"] = bad
    try:
        b = R.ReconBudget()
        check(b.budget_s == R.RECON_BUDGET_S_DEFAULT and b.source == "default",
              "RECON_BUDGET_S=%r -> default %d s (%s)" % (bad, b.budget_s, b.source))
    except Exception as e:                       # a CRASH is reported as a finding, not a traceback
        check(False, "RECON_BUDGET_S=%r raised %s: %s (must fail OPEN to the default)"
              % (bad, type(e).__name__, e))
os.environ["RECON_BUDGET_S"] = "45"
b = R.ReconBudget()
check(b.budget_s == 45 and b.source == "env", "RECON_BUDGET_S=45 -> 45 s from the env")
os.environ.pop("RECON_BUDGET_S", None)
check(R.RECON_BUDGET_S_DEFAULT == 300,
      "the default is 300 s: 2x the '2-3 min' the UI states for recon, under enrichment's 380 s")

R = _fresh(budget_s=50)
CLOCK.broken = True                              # the clock raises on every read
ident_c = _ident()
try:
    R.run(ident_c, _filters(3), "Internal")
    ok = True
except Exception as e:
    ok = False; print("    raised: %r" % e)
check(ok, "a clock that raises never aborts a run")
check("recon_truncated" not in ident_c, "...and never truncates (fail OPEN: default to 'not exhausted')")
CLOCK.broken = False

print("\n== 6. identity discovery obeys the same budget ==")
R = _fresh(budget_s=30)
seen = []
def _slow_resolve(name):
    seen.append((name, CLOCK.t)); CLOCK.t += 10.0; return []
R._resolve = _slow_resolve
ident_d = {"seed": "x"}
found = R._probe_subdomains(["caixabank.es", "caixabank.com"],
                            stop=lambda d, t: R.recon_budget().check(ident_d, "identity discovery", "DNS probes", d, t))
late = [s for s in seen if s[1] >= 30]
check(len(seen) == 3 and not late,
      "DNS probe: 3 lookups issued (0, 10, 20 s), none at or after the 30 s deadline; %d total names skipped"
      % (2 * len(R.PROBE_SUBS) - len(seen)))
check(ident_d.get("recon_truncated", {}).get("phase") == "identity discovery",
      "the truncation is recorded on ident with phase 'identity discovery'")
check(isinstance(found, dict), "the probe returns the (partial) map rather than raising")

print("\n== 7. the web UI no longer says refreshing cancels the run ==")
LOC = os.path.join(HERE, "..", "..", "..", "webapp", "frontend", "src", "locales")
CANCEL = re.compile(r"cancel|annul|bricht|abbr|anuluj|przerywa", re.I)
for lang in ("en", "de", "it", "fr", "es", "pl"):
    src = io.open(os.path.join(LOC, lang + ".js"), encoding="utf-8").read()
    vals = {}
    for key in ("assess.noteKeepOpen", "comp.note", "assess.statusWorking", "assess.noteShort"):
        m = re.search(r'"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key), src)
        vals[key] = json.loads('"%s"' % m.group(1)) if m else None
    check(all(vals.values()), "%s: all four strings present" % lang)
    check(vals["assess.noteKeepOpen"] and not CANCEL.search(vals["assess.noteKeepOpen"]),
          "%s: assess.noteKeepOpen does not say refreshing cancels: %r" % (lang, (vals["assess.noteKeepOpen"] or "")[:70]))
    check(vals["comp.note"] and not CANCEL.search(vals["comp.note"]),
          "%s: comp.note does not say refreshing cancels" % lang)
    for key in vals:
        check(vals[key] is not None and "\u2014" not in vals[key],
              "%s: %s carries no em dash" % (lang, key))
en = io.open(os.path.join(LOC, "en.js"), encoding="utf-8").read()
m = re.search(r'"assess.statusWorking":\s*"((?:[^"\\]|\\.)*)"', en)
sw = json.loads('"%s"' % m.group(1)) if m else ""
check("usually takes about two minutes" not in sw and "typical" in sw.lower() and "bounded" in sw.lower(),
      "en: the status line says two minutes is TYPICAL and large estates are BOUNDED: %r" % sw)
jsx = io.open(os.path.join(HERE, "..", "..", "..", "webapp", "frontend", "src", "pages", "NewAssessment.jsx"),
              encoding="utf-8").read()
check("refreshing cancels" not in jsx, "NewAssessment.jsx carries no hardcoded 'refreshing cancels'")

print("\n== 8. wiring: run_assessment starts the clock, passes progress, emits the event ==")
ra = io.open(os.path.join(HERE, "run_assessment.py"), encoding="utf-8").read()
ra_code = "\n".join(l for l in ra.splitlines() if not l.strip().startswith("#"))
check("R.recon_budget(reset=True).start()" in ra_code, "run_assessment starts the recon budget before identity resolution")
check(re.search(r"R\.run\([^)]*progress=", ra_code) is not None, "run_assessment passes a progress callback into R.run")
check('evt="recon_truncated"' in ra_code, "run_assessment emits evt=recon_truncated")
ec = io.open(os.path.join(HERE, "engine_config.py"), encoding="utf-8").read()
check('"RECON_BUDGET_S"' in ec, "engine_config reports the effective RECON_BUDGET_S")
en_py = io.open(os.path.join(HERE, "enrich.py"), encoding="utf-8").read()
check('slim["partial_estate"]' in en_py and "partial_estate" in en_py.split("PROMPT = ")[1].split('"""')[1],
      "enrich.py passes the statement to the model AND the prompt instructs it to state the partial estate")

print()
if FAILS:
    print("=" * 78 + "\n  test_recon_budget: %d FAILURE(S)" % len(FAILS))
    for f in FAILS:
        print("    - " + f)
    print("=" * 78)
    sys.exit(1)
print("=" * 78 + "\n  test_recon_budget: ALL PASSED -- recon is bounded, truncation is first-class data\n" + "=" * 78)
