#!/usr/bin/env python3
"""
compliance_enrich.py — produce compliance.json for a company across NIS2, CRA and the EU AI Act.

Mirrors the security engine: the LLM returns a STRUCTURED JSON blob (never prose the builders paste
blind), grounded ONLY in the committed reference (compliance/EU_COMPLIANCE_REFERENCE.md). Rendering is
deterministic (pptxgenjs + a Node HTML builder), so a weak model can produce weaker wording but never
a broken or unsafe deliverable.

Input is a COMPANY NAME only (the operator's choice). The model INFERS the scoping assumptions
(sector, size band, whether the company sells products with digital elements, whether it builds/uses
AI, countries) from its own knowledge and STATES them as assumptions — the post-run clarification loop
(compliance_clarify.py) is how the operator confirms/corrects them, exactly like the security Assess.

    python compliance_enrich.py "Acme AG" out/compliance.json [--lang en|de] [--overrides overrides.json]

The model chain, key and pricing are reused from enrich.py (same DigitalOcean inference). A
deterministic fallback ALWAYS yields a usable compliance.json: the obligations, deadlines and penalty
maxima are FIXED facts from the reference (company-independent), so even with no model the decks carry
the real regulatory content — applicability is simply marked "requires confirmation".
"""
import argparse, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE = os.path.join(HERE, "compliance", "EU_COMPLIANCE_REFERENCE.md")


def _ref_text():
    try:
        return open(REFERENCE, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


# ---------------------------------------------------------------- FIXED regulatory facts ---
# These come verbatim from the reference and DO NOT depend on the company. They anchor the
# deterministic fallback and are also handed to the model as the ground truth it must not contradict.
FIXED = {
    "nis2": {
        "name": "NIS2 — Directive (EU) 2022/2555",
        "instrument": "Directive (via national law)",
        "regulates": "Cybersecurity of organisations (18 sectors)",
        "obligations": [
            {"ref": "Art. 20", "title": "Governance & management liability",
             "detail": "Management bodies must approve the risk-management measures, oversee implementation, follow training, and can be held personally liable."},
            {"ref": "Art. 21(2)", "title": "Risk-management measures (10 minimum)",
             "detail": "Risk-analysis & IS-security policies; incident handling; business continuity/backup/DR/crisis; supply-chain security; secure acquisition/development incl. vulnerability handling; effectiveness assessment; cyber hygiene & training; cryptography/encryption; HR security, access control, asset management; MFA & secured comms."},
            {"ref": "Art. 21(3)", "title": "Supply-chain security",
             "detail": "Take account of vulnerabilities and cybersecurity practices of each direct supplier, including secure development."},
            {"ref": "Art. 23", "title": "Incident reporting — 24h / 72h / 1 month",
             "detail": "Early warning within 24h, incident notification within 72h, final report within one month, for any incident with a significant impact."},
            {"ref": "Art. 3(3)-(4)", "title": "Registration / notification",
             "detail": "Register with the national authority (name, contacts, IP ranges, sector, Member States); notify changes within two weeks."},
        ],
        "deadlines": [
            {"date": "2026-03-06", "label": "German NIS2 registration statutory deadline (BSI grace to 31 Jul 2026)"},
            {"date": "2026-08-15", "label": "Netherlands NIS2 law in force"},
            {"date": "2026-09-30", "label": "Sweden NIS2 registration deadline"},
            {"date": "2026-10-01", "label": "Austria NIS2 law in force"},
            {"date": "2026-10-03", "label": "Poland NIS2 registration deadline"},
            {"date": "2026-12-31", "label": "Austria NIS2 registration deadline"},
        ],
        "penalty": {"essential": "€10m or 2% of worldwide turnover",
                    "important": "€7m or 1.4% of worldwide turnover",
                    "note": "Essential entities also face temporary management bans and suspension of authorisation (Art. 32(5)); late registration is a separate offence (DE up to €500k)."},
    },
    "cra": {
        "name": "Cyber Resilience Act — Regulation (EU) 2024/2847",
        "instrument": "Regulation (directly applicable)",
        "regulates": "Cybersecurity of products with digital elements (PDE)",
        "obligations": [
            {"ref": "Annex I Part I", "title": "Security by design",
             "detail": "No known exploitable vulnerabilities; secure-by-default; access protection; confidentiality/integrity/availability; data minimisation; attack-surface reduction; security logging; fixable via security updates."},
            {"ref": "Annex I Part II", "title": "Vulnerability handling + SBOM",
             "detail": "Identify & document components (SBOM); remediate without delay via free updates; regular testing; coordinated vulnerability disclosure; public disclosure of fixed vulnerabilities; secure update distribution."},
            {"ref": "Art. 13", "title": "Support period & CE marking",
             "detail": "Security updates for the expected product life, at least 5 years; technical documentation, EU declaration of conformity and CE marking before market placement."},
            {"ref": "Art. 14", "title": "Reporting — 24h / 72h / 14 days",
             "detail": "Report actively exploited vulnerabilities & severe incidents to CSIRT + ENISA via the single platform: early warning 24h, notification 72h, final report 14 days."},
        ],
        "deadlines": [
            {"date": "2026-09-11", "label": "CRA incident & vulnerability reporting begins (Art. 14)"},
            {"date": "2027-12-11", "label": "CRA full product requirements apply (Annex I, conformity, CE)"},
        ],
        "penalty": {"essential": "€15m or 2.5% of worldwide turnover",
                    "important": "€10m or 2% (other obligations); €5m or 1% (misleading info)",
                    "note": "Market surveillance can order products withdrawn or recalled. MDR-regulated medical devices are carved out (Art. 2(2)(a))."},
    },
    "aiact": {
        "name": "EU AI Act — Regulation (EU) 2024/1689",
        "instrument": "Regulation (directly applicable)",
        "regulates": "AI systems by risk tier",
        "obligations": [
            {"ref": "Art. 5", "title": "Prohibited practices (live since 2 Feb 2025)",
             "detail": "No manipulative/deceptive AI, social scoring, untargeted face-scraping, workplace/education emotion inference, sensitive biometric categorisation, or (narrow exceptions) real-time remote biometric ID."},
            {"ref": "Art. 8-17", "title": "High-risk provider duties",
             "detail": "Risk-management system; data governance & bias examination; technical documentation; automatic logging; transparency to deployers; human oversight; accuracy/robustness/cybersecurity; quality-management system; EU-database registration; conformity assessment + CE marking."},
            {"ref": "Art. 26-27", "title": "Deployer duties",
             "detail": "Use per instructions; ensure human oversight; monitor and suspend/report risks; keep logs; inform affected persons; fundamental-rights impact assessment where required."},
            {"ref": "Art. 50", "title": "Transparency (limited-risk)",
             "detail": "Tell people they are interacting with AI; label AI-generated/manipulated content and deepfakes; disclose emotion-recognition/biometric-categorisation use."},
            {"ref": "Art. 53-55", "title": "General-purpose AI (GPAI)",
             "detail": "Technical documentation; downstream information; copyright policy; public training-data summary; systemic-risk models add evaluation/red-teaming, risk mitigation, incident reporting and cybersecurity."},
        ],
        "deadlines": [
            {"date": "2025-02-02", "label": "Prohibited practices + AI-literacy duties apply"},
            {"date": "2025-08-02", "label": "GPAI obligations, governance & penalties apply"},
            {"date": "2026-08-02", "label": "General application: high-risk (Annex III) + transparency"},
            {"date": "2027-08-02", "label": "Embedded high-risk (Annex I) + pre-2025 GPAI"},
        ],
        "penalty": {"essential": "€35m or 7% of worldwide turnover (Art. 5 breaches)",
                    "important": "€15m or 3% (operator/high-risk/transparency duties); €7.5m or 1% (misleading info)",
                    "note": "GPAI model fines up to €15m or 3% (Art. 101); SMEs pay the LOWER of the fixed amount or the percentage."},
    },
}

_ORDER = ["nis2", "cra", "aiact"]


def _skeleton(company, lang, assumptions=None):
    """Deterministic compliance.json from the FIXED facts. Always correct; the safety net."""
    a = assumptions or {}
    regimes = {}
    for k in _ORDER:
        f = FIXED[k]
        regimes[k] = {
            "key": k, "name": f["name"], "instrument": f["instrument"], "regulates": f["regulates"],
            "applies": "unclear",
            "classification": "Requires confirmation",
            "rationale": ("Scope depends on the company's sector, size and product/AI profile — "
                          "confirm via the clarification questions to finalise the classification."),
            "obligations": list(f["obligations"]),
            "gaps": [],
            "deadlines": list(f["deadlines"]),
            "penalty": f["penalty"],
            "colt": _colt_defaults(k),
        }
    return {
        "company": company, "generated": datetime.date.today().isoformat(), "lang": lang,
        "assumptions": {
            "sector": a.get("sector") or "Not yet confirmed",
            "size_band": a.get("size_band") or "unknown",
            "sells_digital_products": a.get("sells_digital_products"),
            "builds_or_deploys_ai": a.get("builds_or_deploys_ai"),
            "countries": a.get("countries") or [],
            "note": "Company-independent obligations, deadlines and penalties are shown verbatim from "
                    "the primary legal texts. Applicability requires confirmation of sector/size/profile.",
        },
        "regimes": regimes,
        "roadmap": {
            "exec_summary": ("This assessment maps %s against NIS2, the Cyber Resilience Act and the EU "
                             "AI Act. Confirm the scoping assumptions to finalise which duties bite and "
                             "by when." % company),
            "phases": [
                {"when": "0-3 months", "items": ["Confirm scope & entity classification per regime",
                                                 "Register with the relevant national NIS2 authority",
                                                 "Stand up 24h/72h incident-reporting runbooks"]},
                {"when": "3-9 months", "items": ["Close Art. 21 risk-management gaps (MFA, backup/DR, supply-chain)",
                                                 "Build the product SBOM & vulnerability-handling process (CRA)",
                                                 "Inventory AI systems and classify by AI-Act risk tier"]},
                {"when": "9-18 months", "items": ["Complete CRA conformity + CE for products with digital elements",
                                                  "Meet AI-Act high-risk duties for any Annex III system",
                                                  "Independent effectiveness review & board sign-off"]},
            ],
            "priorities": [],
        },
        "source": "compliance/EU_COMPLIANCE_REFERENCE.md (compiled 20 Jul 2026)",
    }


def _colt_defaults(k):
    if k == "nis2":
        return [{"title": "Managed Detection & Response + SOC", "body": "Delivers Art. 21(2) incident handling and the 24h/72h reporting evidence trail."},
                {"title": "Colt SASE / ZTNA + Managed Firewall", "body": "Access control, MFA and secure connectivity for Art. 21(2)(i)/(j)."},
                {"title": "Backup, DR & network resilience", "body": "Business-continuity controls (Art. 21(2)(c)) with dual-homing and tested recovery."}]
    if k == "cra":
        return [{"title": "Secure-by-design advisory + SBOM tooling", "body": "Vulnerability-handling process and SBOM to meet Annex I Part II."},
                {"title": "Managed vulnerability disclosure & update delivery", "body": "Coordinated disclosure and secure update distribution across the 5-year support window."}]
    return [{"title": "AI governance & risk-management framework", "body": "Art. 9 risk-management system, logging and human-oversight design for high-risk AI."},
            {"title": "Model security & red-teaming", "body": "Art. 15 accuracy/robustness/cybersecurity and adversarial testing for AI systems."}]


PROMPT = """You are a Colt cyber & compliance pre-sales analyst. Using ONLY the reference below, assess
%(company)s against three EU regimes: NIS2, the Cyber Resilience Act (CRA) and the EU AI Act.

Return ONLY strict JSON, no prose, no markdown. British English%(lang)s.

STEP 1 — INFER the company profile from your own knowledge of %(company)s and STATE it as assumptions
(you have no company questionnaire; the operator will confirm/correct these afterwards):
sector, size_band (micro|small|medium|large), whether it SELLS products with digital elements
(hardware/software/apps/IoT), whether it BUILDS or DEPLOYS AI, and its main countries of operation.
If confirmed facts are provided under CONFIRMED, they OVERRIDE your inference and you must not contradict them.

STEP 2 — For EACH regime decide applicability from those assumptions and the reference's scope rules,
then produce the analysis. NEVER invent an article number, deadline, penalty figure or fine that is not
in the reference. The obligations/deadlines/penalty maxima are FIXED — reproduce them faithfully; your
job is the company-specific applicability, rationale, GAPS and Colt remediation.

Return this EXACT shape:
{
 "assumptions": {"sector":"", "size_band":"", "sells_digital_products":true, "builds_or_deploys_ai":false,
                 "countries":["DE"], "note":"Inferred from public information; confirm to finalise scope."},
 "regimes": {
   "nis2": {"applies": true, "classification":"Essential|Important|Out of scope|Unclear",
            "rationale":"2-3 sentences tying sector+size to the essential/important test",
            "gaps":[{"sev":"HIGH|MEDIUM|LOW","title":"","detail":"attacker/impact + the article","article":"Art. 23"}],
            "colt":[{"title":"Colt service","body":"what it delivers, mapped to the article"}]},
   "cra":   {"applies": true, "classification":"Default self-assessment|Important (Class I/II)|Critical|Out of scope|Unclear",
            "rationale":"tie product profile to the PDE test + MDR carve-out if relevant",
            "gaps":[...], "colt":[...]},
   "aiact": {"applies": true, "classification":"Prohibited|High-risk|Limited-risk (transparency)|Minimal|GPAI|Out of scope|Unclear",
            "rationale":"tie AI use to the tier (Annex III use case if any)",
            "gaps":[...], "colt":[...]}
 },
 "roadmap": {"exec_summary":"3-4 sentences for a board: combined exposure, the nearest hard deadline, the biggest gap",
             "priorities":[{"regime":"AI Act","action":"","why":"deadline/penalty","colt":"the Colt service"}]}
}
Give 3-5 gaps and 2-3 colt items per APPLICABLE regime; [] for an out-of-scope regime. Every gap
sentence must carry an attacker action or a business/deadline consequence AND the article — no filler.

CONFIRMED (operator-asserted facts; override your inference):
%(confirmed)s

=== REFERENCE (the ONLY permitted source of articles, deadlines and penalties) ===
%(reference)s
"""

LANG_DE = (" — schreibe ALLE Fliesstexte (rationale, gaps, colt, exec_summary, assumptions.note, "
           "priorities) auf formellem Hochdeutsch (Sie-Form). JSON-Schluessel und Artikel-/"
           "Verordnungsnummern bleiben englisch/original. Uebersetze NICHT: NIS2, CRA, AI Act, Colt-"
           "Produktnamen, CVE/Artikel-IDs, Eigennamen.")


def _merge(base, model):
    """Overlay the model's per-regime analysis onto the deterministic skeleton, keeping FIXED facts."""
    a = model.get("assumptions")
    if isinstance(a, dict):
        for k, v in a.items():
            if v not in (None, "", []):
                base["assumptions"][k] = v
    mr = model.get("regimes") or {}
    for k in _ORDER:
        m = mr.get(k)
        if not isinstance(m, dict):
            continue
        r = base["regimes"][k]
        if m.get("applies") is not None:
            r["applies"] = m["applies"]
        for fld in ("classification", "rationale"):
            if str(m.get(fld) or "").strip():
                r[fld] = m[fld]
        if isinstance(m.get("gaps"), list) and m["gaps"]:
            r["gaps"] = [g for g in m["gaps"] if isinstance(g, dict)][:6]
        if isinstance(m.get("colt"), list) and m["colt"]:
            r["colt"] = [c for c in m["colt"] if isinstance(c, dict)][:4]
    rm = model.get("roadmap") or {}
    if str(rm.get("exec_summary") or "").strip():
        base["roadmap"]["exec_summary"] = rm["exec_summary"]
    if isinstance(rm.get("priorities"), list) and rm["priorities"]:
        base["roadmap"]["priorities"] = [p for p in rm["priorities"] if isinstance(p, dict)][:8]
    return base


def build(company, lang="en", overrides=None):
    """Return compliance.json. Tries the DO model chain; falls back to the deterministic skeleton."""
    overrides = overrides or {}
    base = _skeleton(company, lang, overrides.get("assumptions"))
    if not os.environ.get("OPENAI_API_KEY"):
        base["assumptions"]["note"] += "  (LLM not configured — deterministic scope shown.)"
        return base, "no OPENAI_API_KEY — deterministic"
    try:
        sys.path.insert(0, HERE)
        import enrich as E
        prompt = PROMPT % {
            "company": company,
            "lang": (LANG_DE if str(lang).lower().startswith("de") else ""),
            "confirmed": json.dumps(overrides, ensure_ascii=False) if overrides else "(none supplied)",
            "reference": _ref_text()[:16000],
        }
        chain = E._chain() or ["gemma-4-31B-it"]
        last = ""
        for model in chain[:3]:
            try:
                txt, usage = E._call(prompt, model=model,
                                     timeout=int(os.environ.get("COMPLIANCE_TIMEOUT", "150")))
                j = E._json(txt)
                if isinstance(j, dict) and (j.get("regimes") or j.get("assumptions")):
                    out = _merge(base, j)
                    out["model"] = model
                    print("[compliance] enriched via %s (%s tok)"
                          % (model, (usage or {}).get("completion_tokens", "?")), file=sys.stderr)
                    return out, "ok:%s" % model
                last = "empty/'%s'" % (str(j)[:80])
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, str(e)[:120])
                print("[compliance] model %s failed (%s) — trying next" % (model, last), file=sys.stderr)
        base["assumptions"]["note"] += "  (LLM chain failed: %s — deterministic scope shown.)" % last
        return base, "fallback:%s" % last
    except Exception as e:
        print("[compliance] enrich unavailable (%s) — deterministic" % type(e).__name__, file=sys.stderr)
        return base, "deterministic"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("company")
    ap.add_argument("out")
    ap.add_argument("--lang", default=os.environ.get("DECK_LANG", "en"))
    ap.add_argument("--overrides", help="JSON file of operator-confirmed facts")
    a = ap.parse_args()
    ov = {}
    if a.overrides and os.path.exists(a.overrides):
        try: ov = json.load(open(a.overrides, encoding="utf-8"))
        except Exception: pass
    out, status = build(a.company, a.lang, ov)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("compliance_enrich: %s -> %s" % (status, a.out), file=sys.stderr)


if __name__ == "__main__":
    main()
