#!/usr/bin/env python3
"""
engine_config.py — ONE place that answers "what is actually in force right now?"

WHY THIS EXISTS (the operator's diagnosis, and he was right)
------------------------------------------------------------
    "maybe its a good idea to make some sort of API? and not to hard code things and then
     try to guess where they are and what is working or not"

The enrichment chain alone had FOUR possible homes, and we burned three deploys discovering them
one at a time:

  1. enrich.py::_FALLBACKS                     the committed, documented, evidence-based default
  2. docker-compose.*.yml `environment:`       BEATS env_file — silently defeated (1) for weeks
  3. assess-bot/.env  ENRICH_MODELS            the documented per-deployment override
  4. assess-bot/.env  ENRICH_MODEL  (singular) LEGACY — promotes one model to HEAD and reorders
                                               the chain, which is why deepseek-v4-flash sat at
                                               position 2 and was never called

Every one of those is invisible from the outside. You cannot fix what you cannot see, and reading
five files on a droplet to answer "which model will run?" is exactly the guessing the operator is
tired of. So: RESOLVE the value once, report it WITH ITS PROVENANCE, and expose it over the API.

    python engine_config.py                 # human table
    python engine_config.py --json          # machine
    GET /api/diag                           # same payload, owner-scoped (webapp/backend/app/main.py)

DESIGN RULE: this module NEVER decides anything. It only reports what the real code would do, by
importing the real modules. A diagnostic that reimplements the logic it is diagnosing is a lie
waiting to happen — the engine-hash lesson all over again.
"""
import argparse, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _sha(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]
    except Exception:
        return None


def enrichment():
    """The model chain AS THE ENGINE WILL ACTUALLY BUILD IT, plus where each input came from."""
    out = {"effective": [], "sources": {}, "conflict": False, "notes": []}
    try:
        import enrich as E
    except Exception as e:
        out["notes"].append("enrich.py not importable: %s" % e)
        return out

    repo = list(getattr(E, "_FALLBACKS", []))
    env_models = os.environ.get("ENRICH_MODELS", "").strip()
    env_model = os.environ.get("ENRICH_MODEL", "").strip()

    out["sources"] = {
        "repo:enrich.py::_FALLBACKS": repo,
        "env:ENRICH_MODELS": [m.strip() for m in env_models.split(",") if m.strip()] or None,
        "env:ENRICH_MODEL (legacy, reorders the chain)": env_model or None,
    }
    # Ask the REAL function; never re-derive it here.
    out["effective"] = list(E._chain())

    if env_models:
        out["conflict"] = out["effective"] != repo
        out["notes"].append("ENRICH_MODELS is set and wins outright over the committed chain.")
    if env_model:
        out["conflict"] = out["effective"] != repo
        out["notes"].append(
            "ENRICH_MODEL=%r is LEGACY: it is prepended as the chain HEAD, so it silently "
            "REORDERS the committed order. This is why the intended head model may never run. "
            "Clear it unless the reorder is deliberate." % env_model)
    if out["effective"] and repo and out["effective"][0] != repo[0]:
        out["notes"].append("HEAD MISMATCH: repo wants %r, runtime will use %r."
                            % (repo[0], out["effective"][0]))
    out["head"] = out["effective"][0] if out["effective"] else None
    out["prices_usd_per_1m"] = getattr(E, "PRICE_MAP", {}) or {}
    return out


def detectors():
    """Which high-value classifiers are compiled in — so 'why was CRIT 0?' is answerable."""
    try:
        import shodan_recon as R
    except Exception as e:
        return {"error": str(e)}
    kinds = sorted(getattr(R, "TEMPLATES", {}).keys())
    hv = [k for k in ("secrets_manager", "nas_exposed", "backup_console", "pbx_exposed")
          if k in kinds]
    return {"template_kinds": len(kinds), "high_value_detectors": hv,
            "has_owns_host": hasattr(R, "_owns_host"),
            "has_cotenant_guard": "cotenants_dropped" in open(
                os.path.join(HERE, "shodan_recon.py"), encoding="utf-8").read(),
            "tenant_apex_count": len(getattr(R, "TENANT_APEX", ()))}


def budgets():
    """The timeout arithmetic that silently produced English decks when it did not add up."""
    g = lambda k, d: os.environ.get(k, d)                                        # noqa: E731
    return {"ENRICH_TIMEOUT": g("ENRICH_TIMEOUT", "(default)"),
            "ENRICH_BUDGET_S": g("ENRICH_BUDGET_S", "(default)"),
            "ENRICH_ATTEMPTS": g("ENRICH_ATTEMPTS", "(default)"),
            "ENRICH_EVIDENCE_CAP": g("ENRICH_EVIDENCE_CAP", "(default)")}


def versions():
    """sha256 of the engine files, so 'is the container running THIS code?' is answerable."""
    files = ["shodan_recon.py", "run_assessment.py", "enrich.py", "group_discovery.py",
             "clarify.py", "compliance_assess.py", "compliance_enrich.py", "creed.js"]
    return {f: _sha(os.path.join(HERE, f)) for f in files if os.path.exists(os.path.join(HERE, f))}


def collect():
    return {"enrichment": enrichment(), "detectors": detectors(),
            "budgets": budgets(), "engine_sha256": versions(),
            "shodan_key_present": bool(os.environ.get("SHODAN_API_KEY")),
            "inference_base": os.environ.get("OPENAI_BASE_URL",
                                             "https://inference.do-ai.run/v1")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = collect()
    if a.json:
        print(json.dumps(d, indent=2, ensure_ascii=False))
        return 0
    e = d["enrichment"]
    print("\n=== ENRICHMENT CHAIN (what will ACTUALLY run) ===")
    print("  effective : %s" % " -> ".join(e["effective"]))
    print("  head      : %s" % e.get("head"))
    print("\n  provenance:")
    for k, v in e["sources"].items():
        print("    %-46s %s" % (k, v if v else "(not set)"))
    if e["notes"]:
        print("\n  NOTES:")
        for n in e["notes"]:
            print("    ! " + n)
    print("\n=== DETECTORS ===")
    for k, v in d["detectors"].items():
        print("  %-24s %s" % (k, v))
    print("\n=== BUDGETS ===")
    for k, v in d["budgets"].items():
        print("  %-24s %s" % (k, v))
    print("\n=== ENGINE FILE HASHES ===")
    for k, v in d["engine_sha256"].items():
        print("  %-26s %s" % (k, v))
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
