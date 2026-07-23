#!/usr/bin/env python3
"""
compliance_clarify.py — post-run clarification questions for the Compliance flow.

Same interaction model as the security Assess (clarify.py) and jobhuntwow's Tailor: the decks are
delivered FIRST, then the engine asks the operator to confirm/correct the scoping assumptions the LLM
INFERRED from the company name. Because compliance applicability depends on facts the model can only
guess (sector, size band, whether the company sells digital products, whether it builds/uses AI, which
countries), those confirmations are the sanctioned way scope changes — a REFINE run re-scopes with the
operator-asserted facts, which OVERRIDE the inference.

    python compliance_clarify.py compliance.json [-o clarify.json]

Deterministic and machine-actionable: each question carries a `maps_to` the backend turns into an
override the engine re-runs with.
"""
import argparse, json, os, sys


def _load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def build(cj):
    a = cj.get("assumptions") or {}
    company = cj.get("company") or "the company"
    regimes = cj.get("regimes") or {}

    def _cls(k):
        return (regimes.get(k) or {}).get("classification", "—")

    qs = [
        {"id": "sector", "kind": "text", "title": "What is your primary sector?",
         "body": ("This decides NIS2 scope (Annex I 'high-criticality' -> can be an Essential entity; "
                  "Annex II -> Important). I assumed: %s." % (a.get("sector") or "not confirmed")),
         "placeholder": "e.g. Manufacturing (medical devices), Energy, Digital infrastructure, Banking",
         "maps_to": "sector"},

        {"id": "size_band", "kind": "choice", "title": "How large is the group (consolidated)?",
         "body": ("NIS2 applies to medium+ entities (≥250 staff, or >€50m turnover AND >€43m "
                  "balance sheet at group level). I assumed: %s." % (a.get("size_band") or "unknown")),
         "options": ["micro", "small", "medium", "large"],
         "maps_to": "size_band"},

        {"id": "sells_digital_products", "kind": "yesno",
         "title": "Do you sell products with digital elements?",
         "body": ("Hardware, software, apps, IoT or their cloud back-ends -> Cyber Resilience Act scope "
                  "(current classification: %s). MDR medical devices are carved out." % _cls("cra")),
         "maps_to": "sells_digital_products"},

        {"id": "builds_or_deploys_ai", "kind": "yesno",
         "title": "Do you build or deploy AI systems?",
         "body": ("Any AI you provide or use in a professional capacity -> EU AI Act scope (current "
                  "classification: %s). This includes embedded AI and general-purpose models." % _cls("aiact")),
         "maps_to": "builds_or_deploys_ai"},

        {"id": "countries", "kind": "text", "title": "Which EU countries do you operate in?",
         "body": ("NIS2 is transposed per Member State with different registration deadlines, so the "
                  "deadline calendar depends on where you operate. I assumed: %s."
                  % (", ".join(a.get("countries") or []) or "not confirmed")),
         "placeholder": "e.g. DE, IT, PL, NL",
         "maps_to": "countries"},

        {"id": "notes", "kind": "text", "title": "Anything else that affects scope?",
         "body": ("Free text: MDR/DORA/GDPR overlaps, specific products, an AI use-case (recruitment, "
                  "credit scoring, biometrics), or systems to exclude — I will factor it into the rebuild."),
         "placeholder": "e.g. We make an AI-based diagnostic device (MDR); we also run a credit-scoring model.",
         "maps_to": "notes"},
    ]

    return {
        "company": company,
        "summary": {
            "nis2": _cls("nis2"), "cra": _cls("cra"), "aiact": _cls("aiact"),
            "assumed_size": a.get("size_band") or "unknown",
        },
        "questions": qs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compliance")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    cj = _load(a.compliance)
    if not cj:
        print("compliance_clarify: could not read %s" % a.compliance, file=sys.stderr)
        sys.exit(1)
    out = build(cj)
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt)
        print("compliance_clarify: wrote %d question(s) -> %s" % (len(out["questions"]), a.out), file=sys.stderr)
    else:
        print(txt)


if __name__ == "__main__":
    main()
