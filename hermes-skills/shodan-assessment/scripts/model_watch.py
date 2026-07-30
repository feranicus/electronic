#!/usr/bin/env python3
"""
model_watch.py — does DigitalOcean have anything NEW, and does it answer fast enough?

WHY (the standing lesson, now automated)
----------------------------------------
The enrichment chain is chosen from EVIDENCE, never from taste or vendor marketing
(CLAUDE.md: "Model bake-off - decide deck quality with the artifact"). But that evidence goes
stale silently: DO ships models continuously, the account's entitlements change, and a model that
was fast last month can be slow today. Nothing in the pipeline ever noticed. Two real consequences
we already paid for:

  * gemma-4-31B-it sat at the HEAD of the chain, took 55% of the enrichment budget, and returned
    an empty {} in 1 second — for weeks, because nothing re-measured it.
  * DeepSeek V4 Flash and V4 Pro shipped while we were still on V3.2. V4 Flash is priced at
    $0.112/$0.224 per 1M vs V3.2's $0.425/$1.36 — roughly 4-6x cheaper — and we never looked.

So the catalog check becomes part of the deploy, exactly like the engine-hash verify: it runs on
every `python ship.py`, it is CHEAP (one GET plus a short probe of genuinely new ids), and it is a
WARNING, never a blocker. A new model is information, not a broken build — failing the deploy over
DO's release schedule would be absurd.

WHAT IT DOES
  1. GET {BASE}/v1/models             -> the ids this key can actually SEE
  2. diff against models_seen.json    -> NEW ids, and ids that DISAPPEARED (deprecations bite too)
  3. probe the new ones with the REAL enrichment contract (imports enrich._call, never a toy
     prompt — latency ranking INVERTS with prompt size; that is measured, not theoretical:
     maverick was 3.3s on a toy probe and 44.6s on the real 10,640-char prompt)
  4. print a verdict table + a suggested ENRICH_MODELS line, and refresh the snapshot

HARD RULE IT ENFORCES (from CLAUDE.md, encoded here so a human cannot forget it)
  Reasoning / "thinking" models break the strict-JSON contract. deepseek-r1-distill-llama-70b and
  qwen3.5-397b-a17b both returned bad-contract answers because they emit thinking then truncate.
  Any id matching THINKING_RE is reported but flagged DO-NOT-CHAIN. Kimi K3 is the live example:
  DigitalOcean's own changelog says it is "tuned for max thinking effort by default", which is
  precisely the failure mode - excellent for long-horizon agentic research, wrong for a strict
  JSON contract inside a 380s budget.

USAGE
    python model_watch.py                 # diff + probe new ids   (what ship.py runs)
    python model_watch.py --probe-all     # re-measure the whole shortlist, not just new ids
    python model_watch.py --json
    python model_watch.py --no-probe      # catalog diff only, zero token spend
"""
import argparse, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "models_seen.json")
BASE = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("DO_INFERENCE_KEY") or ""

# Ids that must never enter the enrichment chain even if they are fast and cheap.
THINKING_RE = re.compile(r"(think|reason|-r1\b|distill|^o1|^o3|-cot\b|k3\b|kimi-k3)", re.I)
# Not text->JSON models: embeddings, rerankers, image/audio/video.
NON_TEXT_RE = re.compile(r"(embed|rerank|whisper|tts|stt|image|sdxl|flux|diffusion|video|wan\d|audio)", re.I)

# Published DO serverless rates, USD per 1M tokens (docs.digitalocean.com, verified 1 Jul 2026).
# Used to cost a candidate BEFORE we adopt it. Unknown ids simply report price "?" - we never
# invent a number for a customer-facing cost ledger.
PRICES = {
    "deepseek-v4-flash":  (0.112, 0.224),
    "deepseek-v4-pro":    (1.392, 2.784),
    "deepseek-3.2":       (0.425, 1.36),
    "llama-4-maverick":   (0.25,  0.87),
    "gemma-4-31B-it":     (0.18,  0.50),
    "openai-gpt-oss-120b": (0.10, 0.70),
    "openai-gpt-oss-20b": (0.05,  0.45),
    "kimi-k2.5":          (0.375, 2.025),
    "kimi-k2.6":          (0.76,  3.20),
    "mimo-v2.5":          (0.105, 0.28),
    "nvidia-nemotron-3-super-120b": (0.21, 0.455),
    "mistral-3-14B":      (0.20,  0.20),
    "qwen3.5-397b-a17b":  (0.385, 2.45),
    "glm-5.2":            (1.05,  4.40),
}


def catalog():
    """[model ids] this key can see, or [] if the call fails (fails closed - never guesses)."""
    if not KEY:
        return [], "no OPENAI_API_KEY in the environment"
    try:
        req = urllib.request.Request(BASE + "/models",
                                     headers={"Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8"))
        ids = sorted({str(m.get("id")) for m in (j.get("data") or []) if m.get("id")})
        return ids, ""
    except Exception as e:
        return [], "%s: %s" % (type(e).__name__, e)


def _load_snapshot():
    try:
        return json.load(open(SNAPSHOT, encoding="utf-8"))
    except Exception:
        return {"models": [], "checked": None}


def _price(mid):
    p = PRICES.get(mid)
    return "$%.3f/$%.3f" % p if p else "?"


def probe(mid, timeout=60):
    """Call the model with the REAL enrichment prompt. -> dict(ok, ms, err, tokens_out)."""
    try:
        sys.path.insert(0, HERE)
        import enrich as E
    except Exception as e:
        return {"ok": False, "ms": 0, "err": "enrich import failed: %s" % e, "tokens_out": 0}
    sample = os.path.join(HERE, "..", "sample", "findings.sample.json")
    try:
        fj = json.load(open(sample, encoding="utf-8"))
    except Exception:
        fj = {"findings": [{"id": "C1", "sev": "CRITICAL", "title": "Exposed VPN",
                            "evidence": ["1.2.3.4:443"]}], "target": {"company": "ProbeCo"}}
    t0 = time.time()
    try:
        raw = E._call(E.PROMPT + "\n\nRAW FINDINGS:\n" + json.dumps(fj)[:6000],
                      model=mid, timeout=timeout)
        ms = int((time.time() - t0) * 1000)
        j = E._json(raw)
        ok = isinstance(j, dict) and bool(j.get("exec_summary") or j.get("findings"))
        return {"ok": ok, "ms": ms, "err": "" if ok else "contract-invalid",
                "tokens_out": len(str(raw)) // 4}
    except Exception as e:
        return {"ok": False, "ms": int((time.time() - t0) * 1000),
                "err": str(e)[:90], "tokens_out": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-probe", action="store_true")
    ap.add_argument("--probe-all", action="store_true")
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()

    ids, err = catalog()
    snap = _load_snapshot()
    known = set(snap.get("models") or [])
    out = {"base": BASE, "error": err, "total": len(ids),
           "new": [], "gone": [], "probed": [], "checked": time.strftime("%Y-%m-%dT%H:%M:%SZ")}

    if err:
        print("[model-watch] catalog unavailable (%s) - skipping (this is not a deploy failure)" % err)
        if a.json:
            print(json.dumps(out, indent=2))
        return 0

    new = sorted(set(ids) - known) if known else []
    gone = sorted(known - set(ids))
    out["new"], out["gone"] = new, gone

    print("[model-watch] %d models visible on %s" % (len(ids), BASE))
    if not known:
        print("[model-watch] first run - recording the baseline, nothing to diff")
    if gone:
        print("[model-watch] !! %d model(s) DISAPPEARED (deprecation breaks the chain): %s"
              % (len(gone), ", ".join(gone)))
    if new:
        print("[model-watch] %d NEW model(s): %s" % (len(new), ", ".join(new)))
    elif known:
        print("[model-watch] no new models since the last deploy")

    # probe: new text models only (cheap), or the whole shortlist on demand
    todo = [m for m in (ids if a.probe_all else new)
            if not NON_TEXT_RE.search(m)]
    skipped = [m for m in todo if THINKING_RE.search(m)]
    todo = [m for m in todo if not THINKING_RE.search(m)][:6]
    for m in skipped:
        print("  %-34s DO-NOT-CHAIN  reasoning/thinking model - breaks the strict-JSON contract"
              % m)
        out["probed"].append({"model": m, "verdict": "do-not-chain", "price": _price(m)})

    if todo and not a.no_probe:
        print("\n  %-34s %-9s %-8s %-14s %s" % ("MODEL", "CONTRACT", "ms", "$/1M in,out", "note"))
        for m in todo:
            r = probe(m, a.timeout)
            print("  %-34s %-9s %-8s %-14s %s"
                  % (m, "ok" if r["ok"] else "FAIL", r["ms"], _price(m), r["err"][:38]))
            out["probed"].append({"model": m, "verdict": "ok" if r["ok"] else "fail",
                                  "ms": r["ms"], "price": _price(m), "err": r["err"]})
        good = [p for p in out["probed"] if p.get("verdict") == "ok"]
        if good:
            good.sort(key=lambda p: p.get("ms", 1e9))
            print("\n[model-watch] contract-valid new candidate(s), fastest first: %s"
                  % ", ".join(p["model"] for p in good))
            print("[model-watch] to adopt, re-run the artifact bake-off FIRST "
                  "(python compare_models.py --lang de), then: python set_secret.py ENRICH_MODELS")

    json.dump({"models": ids, "checked": out["checked"]},
              open(SNAPSHOT, "w", encoding="utf-8"), indent=1)
    if a.json:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
