#!/usr/bin/env python3
"""
compliance_assess.py — the Compliance module orchestrator (parallel to run_assessment.py).

    python compliance_assess.py --company "Acme AG" --outdir OUT [--lang en|de] [refine overrides]

ONE input: a company name. The engine:
  1. compliance_enrich.build() -> compliance.json (LLM grounded in the committed EU reference; the
     model INFERS the scoping assumptions and states them; deterministic fallback always yields a
     usable file).
  2. builds FOUR decks via build_compliance_deck.js — NIS2, CRA, EU AI Act, and the combined Roadmap.
  3. builds the animated HTML report via build_compliance_html.js.
  4. writes clarify.json (compliance_clarify) so the web /refine loop can confirm/correct scope.

It streams PROGRESS: [nn%] lines and JSON events to stdout AND events.log exactly like run_assessment,
so the shared web SSE viewer + Grafana both work unchanged. Prints "==== ASSESSMENT COMPLETE ====" so
the backend job runner marks the job done and collects the decks.

REFINE overrides (from the clarification loop) arrive as flags and become operator-CONFIRMED facts that
OVERRIDE the model's inference: --sector, --size-band, --sells-digital yes|no, --builds-ai yes|no,
--country (repeatable), --notes.
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compliance_enrich as CE
import compliance_clarify as CC


def _safe(name):
    return "".join(c if (c.isalnum() or c in " -_") else "_" for c in str(name)).strip().replace(" ", "_") or "Target"


def _tristate(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("yes", "true", "1", "y"):
        return True
    if s in ("no", "false", "0", "n"):
        return False
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--company", required=True)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--lang", default=os.environ.get("DECK_LANG", "en"),
                    choices=["en", "de"])
    # refine overrides (operator-confirmed facts)
    ap.add_argument("--sector", default=None)
    ap.add_argument("--size-band", dest="size_band", default=None,
                    choices=[None, "micro", "small", "medium", "large"])
    ap.add_argument("--sells-digital", dest="sells_digital", default=None)
    ap.add_argument("--builds-ai", dest="builds_ai", default=None)
    ap.add_argument("--country", action="append", default=[])
    ap.add_argument("--notes", default="")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    lang = "de" if str(a.lang).lower().startswith("de") else "en"
    _L = "_DE" if lang == "de" else ""
    company = a.company.strip()
    safe = _safe(company)
    t0 = time.time()

    def _ev(**k):
        k.setdefault("ts", time.time()); k.setdefault("company", company)
        k.setdefault("user", os.environ.get("COLT_USER", ""))
        k.setdefault("service", os.environ.get("SERVICE", "compliance"))
        k.setdefault("bot", os.environ.get("SERVICE", "compliance"))
        line = json.dumps(k); print(line, flush=True)
        try:
            with open(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log"), "a") as fh:
                fh.write(line + "\n")
        except Exception:
            pass

    def _pg(m, pct=None):
        print(("PROGRESS: [%d%%] " % pct if pct is not None else "PROGRESS: ") + m, flush=True)
        try: _ev(evt="progress", pct=(pct if pct is not None else -1), msg=str(m)[:300])
        except Exception: pass

    _ev(evt="compliance_start", company=company, lang=lang)

    # assemble operator-confirmed overrides (only include what was actually supplied)
    assumptions = {}
    if a.sector: assumptions["sector"] = a.sector
    if a.size_band: assumptions["size_band"] = a.size_band
    if _tristate(a.sells_digital) is not None: assumptions["sells_digital_products"] = _tristate(a.sells_digital)
    if _tristate(a.builds_ai) is not None: assumptions["builds_or_deploys_ai"] = _tristate(a.builds_ai)
    if a.country: assumptions["countries"] = [c.strip().upper() for c in a.country if c.strip()]
    overrides = {}
    if assumptions: overrides["assumptions"] = assumptions
    if a.notes: overrides["notes"] = a.notes

    # 1) enrichment -> compliance.json
    _pg("Assessing scope against NIS2 / CRA / EU AI Act (AI)", 8)
    cj, status = CE.build(company, lang, overrides)
    cpath = os.path.join(a.outdir, "compliance.json")
    json.dump(cj, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    _ev(evt="compliance_enrich", company=company, status=status,
        nis2=cj["regimes"]["nis2"]["classification"], cra=cj["regimes"]["cra"]["classification"],
        aiact=cj["regimes"]["aiact"]["classification"])
    _pg("Regulatory analysis ready — building decks", 56)

    # 2) four decks
    decks = [("nis2", f"{safe}_NIS2_Compliance{_L}.pptx", 64),
             ("cra", f"{safe}_CRA_Compliance{_L}.pptx", 72),
             ("aiact", f"{safe}_AI_Act_Compliance{_L}.pptx", 80),
             ("roadmap", f"{safe}_Compliance_Roadmap{_L}.pptx", 88)]
    built = []
    for regime, fn, pct in decks:
        outp = os.path.join(a.outdir, fn)
        _pg("Building %s deck" % regime.upper(), pct)
        r = subprocess.run(["node", os.path.join(HERE, "build_compliance_deck.js"), cpath, outp, regime],
                           capture_output=True, text=True,
                           env=dict(os.environ, DECK_LANG=lang))
        ok = (r.returncode == 0 and os.path.exists(outp))
        if not ok:
            print("[warn] deck %s failed: %s" % (regime, (r.stderr or "").strip()[:300]), file=sys.stderr)
        built.append((ok, outp))

    # 3) animated HTML report
    _pg("Authoring the animated compliance report (HTML)", 94)
    hp = os.path.join(a.outdir, f"{safe}_Compliance_Report{_L}.html")
    try:
        r = subprocess.run(["node", os.path.join(HERE, "build_compliance_html.js"), cpath, hp],
                           capture_output=True, text=True, env=dict(os.environ, DECK_LANG=lang))
        if r.returncode == 0 and os.path.exists(hp):
            built.append((True, hp))
        else:
            print("[warn] compliance html failed: %s" % (r.stderr or "").strip()[:300], file=sys.stderr)
    except Exception as e:
        print("[warn] compliance html: %s" % e, file=sys.stderr)

    # 4) clarification questions (post-run refine loop)
    try:
        clar = CC.build(cj)
        json.dump(clar, open(os.path.join(a.outdir, "clarify.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        _ev(evt="clarify", company=company, questions=len(clar.get("questions") or []))
    except Exception as e:
        print("[warn] clarify: %s" % e, file=sys.stderr)

    n_ok = sum(1 for ok, _ in built if ok)
    ms = int((time.time() - t0) * 1000)
    _ev(evt="assess_done", kind="compliance", company=company, lang=lang, decks=n_ok,
        crit=0, high=0, med=0, low=0,
        nis2=cj["regimes"]["nis2"]["applies"], cra=cj["regimes"]["cra"]["applies"],
        aiact=cj["regimes"]["aiact"]["applies"], total_ms=ms)
    _pg("Compliance assessment complete", 100)
    print("==== ASSESSMENT COMPLETE ====")
    print("Company: %s  · NIS2 %s · CRA %s · AI Act %s" % (
        company, cj["regimes"]["nis2"]["classification"], cj["regimes"]["cra"]["classification"],
        cj["regimes"]["aiact"]["classification"]))
    print("DECKS:")
    for ok, p in built:
        print(("  OK  " if ok else "  FAIL") + p)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # observability: a crash must be as visible as a success (mirrors run_assessment)
        import traceback
        tb = traceback.extract_tb(sys.exc_info()[2])
        where = ("%s:%d" % (tb[-1].filename.split("/")[-1], tb[-1].lineno)) if tb else "?"
        try:
            evt = json.dumps({"evt": "assess_error", "kind": "compliance", "error": type(e).__name__,
                              "message": str(e)[:300], "where": where})
            print(evt, flush=True)
            with open(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log"), "a") as fh:
                fh.write(evt + "\n")
        except Exception:
            pass
        print("PROGRESS: [100%] FAILED — %s: %s" % (type(e).__name__, str(e)[:200]), flush=True)
        raise
