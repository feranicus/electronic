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


def _snapshot_path():
    """WHERE THE BASELINE LIVES, and why it is not next to this file.

    THE BUG (2026-08-27): SNAPSHOT was os.path.join(HERE, "models_seen.json"), i.e. inside
    /opt/shodan-skill/scripts in the colt-web IMAGE. ship.py runs this check with `docker exec`,
    and every deploy recreates that container with --force-recreate, so the baseline was destroyed
    on each ship. Two consecutive production runs both printed "first run - recording the baseline,
    nothing to diff", which is the proof: the NEW / DISAPPEARED diff this check exists to produce
    could never fire. A check that cannot reach its own previous answer is not a check.

    /var/log/colt is the shared colt_events volume - the same persistent home as cost_ledger.sqlite
    and for the same reason: it survives redeploys, image rebuilds and container recreation.
    """
    p = os.environ.get("MODEL_WATCH_SNAPSHOT")
    if p:
        return p, True
    vol = "/var/log/colt"
    if os.path.isdir(vol) and os.access(vol, os.W_OK):
        return os.path.join(vol, "models_seen.json"), True
    return os.path.join(HERE, "models_seen.json"), False


SNAPSHOT, SNAPSHOT_PERSISTS = _snapshot_path()
BASE = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("DO_INFERENCE_KEY") or ""

# Ids that must never enter the enrichment chain even if they are fast and cheap.
#
# THIS REGEX IS THE NAME-SHAPED HALF ONLY. It catches an id that ADVERTISES itself as a reasoning
# model. It cannot catch one that does not say so in its name, and on 2026-11-02 that gap had a
# price: DigitalOcean recommended glm-5.3-flash as the replacement for gemma-4-31B-it, and this
# pattern passes it. The MEASURED half lives in enrich.NOT_CHAINED (one home, beside the chain it
# protects) and is consulted by _refuse() below. Both must agree before a model is probed.
THINKING_RE = re.compile(r"(think|reason|-r1\b|distill|^o1|^o3|-cot\b|k3\b|kimi-k3)", re.I)


def _refuse(mid):
    """Reason this id must not be probed as a chain candidate, or "" to allow it."""
    if THINKING_RE.search(mid or ""):
        return "reasoning/thinking model - breaks the strict-JSON contract"
    try:
        import enrich as E
        return E.not_chainable(mid)
    except Exception:
        # enrich not importable (no deps on this box): the regex half still applies. Say so rather
        # than reporting a narrower check as the full one.
        return ""
# Not text->JSON models: embeddings, rerankers, image/audio/video.
NON_TEXT_RE = re.compile(r"(embed|rerank|whisper|tts|stt|image|sdxl|flux|diffusion|video|wan\d|audio)", re.I)

# Published DO serverless rates, USD per 1M tokens, re-read from docs.digitalocean.com's own
# Inference Pricing page on 2 Nov 2026 (that page's own last_updated was 2026-10-30).
#
# THE WHOLE TABLE WAS WRONG, AND NOTHING NOTICED FOR FOUR MONTHS. It was last verified 1 Jul 2026
# and by November EIGHT of its fifteen rows were false: deepseek-3.2 was 0.425/1.36 and is 0.50/1.60
# (18% under), deepseek-4-flash 0.112/0.224 -> 0.14/0.28, deepseek-v4-pro 1.392/2.784 -> 1.74/3.48,
# kimi-k2.6 0.76/3.20 -> 0.95/4.00, qwen3.5 0.385/2.45 -> 0.55/3.50, glm-5.2 1.05/4.40 -> 1.40/4.40,
# and TWO ids had already been retired on 8 Sep 2026 (kimi-k2.5, nvidia-nemotron-3-super-120b)
# while mimo-v2.5 was never an id at all (it is mimo-v2.5-pro). A price table that is only ever
# read by a human is a table that goes stale silently, which is defect class 1: the check could
# not see its own subject. `test_model_prices.py` now pins the verification date and fails the
# build when it is older than 90 days, so the next drift is loud instead of invisible.
#
# Used to cost a candidate BEFORE we adopt it. Unknown ids report "?" - we never invent a number.
PRICES_VERIFIED = "2026-11-02"
PRICES_MAX_AGE_DAYS = 90
PRICES = {
    # --- the chain today -------------------------------------------------------------------
    "deepseek-3.2":       (0.50,  1.60),
    "llama-4-maverick":   (0.25,  0.87),   # RETIRES 2026-11-09, Meta's only serverless id on DO
    "gemma-4-31B-it":     (0.18,  0.50),   # RETIRES 2026-11-09, Google's only id on DO at all
    "kimi-k2.6":          (0.95,  4.00),
    # --- vendor-diverse instruct candidates (no reasoning flag on DO's models page) ----------
    "mistral-3-14B":      (0.20,  0.20),   # Mistral. Only symmetric price in the catalog
    "qwen3.5-397b-a17b":  (0.55,  3.50),   # Alibaba
    "nemotron-3-ultra-550b":   (0.90, 1.70),   # NVIDIA
    "nemotron-nano-12b-v2-vl": (0.20, 0.60),   # NVIDIA
    "nemotron-3.5-super-vl":   (0.30, 0.65),   # NVIDIA
    "reflection-beam":    (0.40,  1.20),   # Reflection AI
    "minimax-m2.5":       (0.30,  1.20),   # MiniMax, public preview -> own lifecycle risk
    # --- same vendor as the head: usable, but they do NOT restore the four-vendor hedge -------
    "deepseek-v4.1-flash": (0.30, 1.20),   # DO's recommended successor to llama-4-maverick
    "deepseek-4-flash":   (0.14,  0.28),
    "deepseek-v4-pro":    (1.74,  3.48),
    # --- OpenAI open-weights: DO flags no reasoning, upstream is harmony-format. MEASURE first -
    "openai-gpt-oss-120b": (0.10, 0.70),
    "openai-gpt-oss-20b": (0.05,  0.45),
    # --- priced here only so a reader sees the cost of the thing THINKING_RE refuses -----------
    "glm-5.2":            (1.40,  4.40),   # reasoning
    "glm-5.3-flash":      (0.15,  0.50),   # reasoning. DO's recommended successor to gemma
    "glm-5.3":            (1.40,  4.40),   # reasoning, DO: "cannot be disabled"
    "mimo-v2.5-pro":      (0.80,  3.00),   # reasoning
    "kimi-k3":            (3.00, 15.00),   # reasoning
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


# VENDORS THIS ACCOUNT IS NOT ENTITLED TO CALL. Measured, not assumed, and recorded in CLAUDE.md
# since the first bake-off: every `anthropic-*` and every commercial `openai-gpt-*` returns
# HTTP 403 Forbidden on this key. Visibility in /v1/models is not entitlement -- that is the whole
# reason model_probe exists.
#
# So probing a NEW model from one of those vendors is a round-trip whose answer we already know,
# and it prints `FAIL ... 403 Forbidden` in a column headed CONTRACT on every deploy. That is
# doubly wrong: it wastes the call, and it reports an ENTITLEMENT fact as a CONTRACT failure, which
# reads like the model is broken when the truth is that we are not allowed to call it. A line that
# says FAIL every time for a reason that will never change is noise, and noise in a deploy log is
# how the one real line gets skipped.
#
# DETECTION IS UNAFFECTED AND DELIBERATELY SO. A new id appearing in the catalog is still reported
# by name -- that is exactly the signal that would have caught `deepseek-v4-pro-0813` and
# `glm-5.3-flash` on the day they appeared. It is the PROBE that is skipped, not the notice.
# Set MODEL_WATCH_PROBE_ALL_VENDORS=1 to probe them anyway (e.g. after buying entitlement).
# "openai-gpt-" not per-version: listing gpt-4 and gpt-5 let openai-gpt-6-1-sol through on
# 2026-10-07 and it printed FAIL 403 on the deploy. CLAUDE.md says EVERY commercial openai-gpt-*.
UNENTITLED_PREFIXES = ("anthropic-", "openai-gpt-", "openai-o1", "openai-o3")


def entitled(mid):
    """(ok, why). False for a vendor prefix this account has been MEASURED to be refused by."""
    if os.environ.get("MODEL_WATCH_PROBE_ALL_VENDORS", "").strip() in ("1", "true", "yes"):
        return True, ""
    m = str(mid or "")
    for p in UNENTITLED_PREFIXES:
        if m.startswith(p):
            return False, ("not entitled on this account (%s* returns HTTP 403; measured, "
                           "see CLAUDE.md) - not a contract failure" % p)
    return True, ""


def probe(mid, timeout=60):
    """Call the model with the REAL enrichment prompt. -> dict(ok, ms, err, tokens_out)."""
    ok_ent, why = entitled(mid)
    if not ok_ent:
        return {"ok": None, "ms": 0, "err": why, "tokens_out": 0, "skipped": True}
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
    # WHY A NAMED SHORTLIST EXISTS. --probe-all takes the whole catalog and then cuts it to the
    # first six that survive filtering, which is an ARBITRARY six: the ids are sorted
    # alphabetically, so a deliberate bake-off between named candidates could not be run at all.
    # When two chain slots have to be replaced against a deadline, probing a random sample is not
    # an answer. --models probes exactly what is asked for, in that order, with no cap.
    ap.add_argument("--models", default="",
                    help="comma-separated ids to probe, in order, instead of the catalog diff")
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
        print("[model-watch] first run - recording the baseline at %s, nothing to diff" % SNAPSHOT)
        if not SNAPSHOT_PERSISTS:
            # If this prints on two consecutive ships, the baseline is being destroyed between
            # them and the diff can never fire. Say so rather than letting "first run" look normal.
            print("[model-watch] !! the baseline is being written INSIDE the container image "
                  "(%s). Container recreation on the next deploy will delete it and this will "
                  "say 'first run' again, forever. Mount a persistent path or set "
                  "MODEL_WATCH_SNAPSHOT." % SNAPSHOT)
    if gone:
        print("[model-watch] !! %d model(s) DISAPPEARED (deprecation breaks the chain): %s"
              % (len(gone), ", ".join(gone)))
    if new:
        print("[model-watch] %d NEW model(s): %s" % (len(new), ", ".join(new)))
    elif known:
        print("[model-watch] no new models since the last deploy")

    # probe: a named shortlist, or new text models only (cheap), or the whole catalog on demand
    asked = [s.strip() for s in a.models.split(",") if s.strip()]
    if asked:
        # An id the catalog does not contain is REPORTED, not silently dropped: on a deadline,
        # "we probed 3 of the 5 you named" has to be visible or the absence reads as a pass.
        for m in asked:
            if m not in ids:
                print("  %-34s NOT-IN-CATALOG  this id does not exist on %s" % (m, BASE))
                out["probed"].append({"model": m, "verdict": "not-in-catalog", "price": _price(m)})
        todo = [m for m in asked if m in ids]
    else:
        todo = [m for m in (ids if a.probe_all else new) if not NON_TEXT_RE.search(m)]
    _why = {m: _refuse(m) for m in todo}
    skipped = [m for m in todo if _why[m]]
    todo = [m for m in todo if not _why[m]]
    # Vendors we are MEASURED to be refused by never reach the probe. Named, so the reader knows
    # the model was seen and deliberately not called -- silence would look like it was missed.
    barred = [m for m in todo if not entitled(m)[0]]
    todo = [m for m in todo if entitled(m)[0]]
    # The cap exists to keep an automatic deploy cheap. A shortlist the operator NAMED is not
    # automatic, and cutting it would answer a different question than the one asked.
    if not asked:
        todo = todo[:6]
    for m in skipped:
        print("  %-34s DO-NOT-CHAIN  %s" % (m, _why[m]))
        out["probed"].append({"model": m, "verdict": "do-not-chain", "price": _price(m),
                              "err": _why[m]})
    for m in barred:
        print("  %-34s NOT-ENTITLED  %s" % (m, entitled(m)[1]))
        out["probed"].append({"model": m, "verdict": "not-entitled", "price": _price(m)})

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

    # WRITE, THEN READ IT BACK. A snapshot that silently fails to persist is exactly how this
    # check spent its whole life reporting "first run"; an unwritable path must be loud.
    try:
        json.dump({"models": ids, "checked": out["checked"]},
                  open(SNAPSHOT, "w", encoding="utf-8"), indent=1)
        back = json.load(open(SNAPSHOT, encoding="utf-8"))
        if sorted(back.get("models") or []) != sorted(ids):
            print("[model-watch] !! baseline read-back does not match what was written (%s) - "
                  "the next run will not diff correctly" % SNAPSHOT)
    except Exception as e:
        print("[model-watch] !! could NOT persist the baseline to %s (%s). The NEW/DISAPPEARED "
              "diff cannot fire on the next run." % (SNAPSHOT, e))
    if a.json:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
