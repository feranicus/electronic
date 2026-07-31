#!/usr/bin/env python3
"""
enrich_parallel.py — MAP-REDUCE enrichment with an enforced coverage contract.

THE DEFECT THIS FIXES (measured, not theorised)
-----------------------------------------------
One LLM call received the whole estate and returned prose for whichever findings it felt like.
Nothing enforced or measured completeness, so a model that rewrote finding C1 and stopped was
logged `status=ok` — and the remaining findings silently rendered canned TEMPLATES text, which is
visually indistinguishable in the deck. That is exactly the observed
"AI just added something to the first critical and then bubkes".

ARCHITECTURE (and why THIS shape of parallelism)
------------------------------------------------
The research is explicit that multi-agent LLM topologies are NOT uniformly better: one systematic
evaluation found ALL 28 multi-agent configurations degraded versus a single-agent baseline, from
-4.4% to -35.3%, with degradation concentrated in SEQUENTIAL or TIGHTLY COUPLED workflows because
of communication overhead and coordination error, at 4-220x the token cost
(arxiv.org/pdf/2603.12229). Gains appear where agents work on INDEPENDENT sub-problems and results
are aggregated (mdpi.com/2079-9292/14/24/4883, arxiv.org/pdf/2505.09787).

Findings are mutually independent — C1's prose does not depend on H2's. So this is a MAP-REDUCE
(embarrassingly parallel) topology, NOT a committee of debating agents:

        findings[]
            |  shard(SHARD_SIZE)            <- deterministic split, severity-interleaved
            v
    +-------+-------+-------+
    | map   | map   | map   |               <- N concurrent calls, each the FULL rich contract
    +-------+-------+-------+                  scoped to 2-3 findings (short prompt = fast, and
            |                                  no truncation, which is what killed whole-estate
            v                                  answers at max_tokens)
        reduce(merge by id)
            |
            v
    COVERAGE CONTRACT: every id must come back REWRITTEN.
    Missing ids -> one targeted retry round for only those ids.
    Still missing -> enrich_coverage < 1.0 is EMITTED and the caller decides.

Wall-clock is set by the SLOWEST shard, not the sum — so a 6-finding estate that took ~40s serially
completes in roughly one shard's time.

    python enrich_parallel.py findings.json -o findings.enriched.json
    python enrich_parallel.py findings.json --lang de --shard-size 3 --workers 4
"""
import argparse, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SHARD_SIZE = int(os.environ.get("ENRICH_SHARD_SIZE", "3"))
WORKERS = int(os.environ.get("ENRICH_WORKERS", "4"))
MIN_COVERAGE = float(os.environ.get("ENRICH_MIN_COVERAGE", "0.8"))


def _log(m):
    print(m, file=sys.stderr, flush=True)


def shard(findings, size=SHARD_SIZE):
    """Split findings into batches, INTERLEAVED by severity.

    Round-robin rather than contiguous slicing, so no single shard gets all the CRITICALs. If one
    shard fails we lose a spread of findings rather than the entire critical section, and every
    shard's prompt contains a comparable mix (which keeps the per-call latency even).
    """
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    ranked = sorted(findings, key=lambda f: (order.get(str(f.get("sev", "")).upper(), 9),
                                             str(f.get("id", ""))))
    n = max(1, (len(ranked) + size - 1) // size)
    buckets = [[] for _ in range(n)]
    for i, f in enumerate(ranked):
        buckets[i % n].append(f)
    return [b for b in buckets if b]


def _call_shard(E, fj, batch, lang, idx, model=None, timeout=None):
    """One map task: full contract, but only this batch's findings. Returns (dict_by_id, meta).

    `model` is explicit because the shards used to inherit E.MODEL — the HEAD of the chain — with no
    failover of any kind. On lotto24.de the head was a model that could not answer at all, so all
    three top-up attempts hit exactly the same wall the serial chain had just hit.
    """
    sub = dict(fj)
    sub["findings"] = batch
    ids = [f.get("id") for f in batch]
    t0 = time.time()
    prompt = E.PROMPT + (E.LANG_DE if str(lang).lower().startswith("de") else "")
    prompt += ("\n\nYou are enriching a SUBSET of the estate. You MUST return a rewritten object "
               "for EVERY one of these finding ids, with no omissions: %s\n\nRAW FINDINGS:\n%s"
               % (", ".join(str(i) for i in ids), json.dumps(sub, ensure_ascii=False)[:14000]))
    try:
        # E._call returns (text, usage). Passing the TUPLE to _json() raised
        #     'tuple' object has no attribute 'find'
        # inside every shard, so the map-reduce top-up has NEVER once succeeded — it reported
        # "0/3 ids ... ERROR" and the deck fell back to template text. It looked like a model
        # problem in the logs; it was a two-value return being caught in one name.
        raw, _usage = E._call(prompt, model=model, timeout=timeout)
        j = E._json(raw)
        if not isinstance(j, dict):
            j = {}
        got = {}
        for x in (j.get("findings") or []):
            if isinstance(x, dict) and x.get("id"):
                got[str(x["id"])] = x
        return got, {"shard": idx, "ids": ids, "returned": sorted(got),
                     "ms": int((time.time() - t0) * 1000), "exec": j.get("exec_summary") or "",
                     "extra": {k: v for k, v in j.items()
                               if k in ("geopol_context", "strengths", "posture")}}
    except Exception as e:
        return {}, {"shard": idx, "ids": ids, "returned": [], "error": str(e)[:120],
                    "ms": int((time.time() - t0) * 1000)}


def run(fj, lang="en", shard_size=SHARD_SIZE, workers=WORKERS):
    """Map-reduce enrich. Returns (merged_findings_by_id, report)."""
    import enrich as E
    findings = [f for f in (fj.get("findings") or []) if isinstance(f, dict) and f.get("id")]
    if not findings:
        return {}, {"coverage": 1.0, "total": 0, "rewritten": 0, "shards": []}

    batches = shard(findings, shard_size)
    _log("[enrich-mr] %d finding(s) -> %d shard(s) of <=%d, %d worker(s)"
         % (len(findings), len(batches), shard_size, workers))

    # A shard is SMALL (<= shard_size findings), so it needs far less wall-clock than the monolithic
    # call — give it a cap that is actually achievable rather than inheriting the chain's.
    _per = int(os.environ.get("ENRICH_SHARD_TIMEOUT", "150"))
    _chain = list(getattr(E, "MODELS", None) or [getattr(E, "MODEL", None)])

    merged, metas = {}, []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(batches)))) as pool:
        futs = {pool.submit(_call_shard, E, fj, b, lang, i, _chain[0], _per): i
                for i, b in enumerate(batches)}
        for fut in as_completed(futs):
            got, meta = fut.result()
            merged.update(got)
            metas.append(meta)
            _log("[enrich-mr]   shard %d: %d/%d ids in %dms%s"
                 % (meta["shard"], len(meta["returned"]), len(meta["ids"]), meta["ms"],
                    "  ERROR: " + meta["error"] if meta.get("error") else ""))

    # ---- COVERAGE CONTRACT: retry ONLY the ids nobody returned --------------------------------
    want = {str(f["id"]) for f in findings}
    missing = sorted(want - set(merged))
    if missing:
        _log("[enrich-mr] %d finding(s) not rewritten -> targeted retry: %s"
             % (len(missing), ", ".join(missing)))
        retry = [f for f in findings if str(f["id"]) in set(missing)]
        # FAIL OVER TO A DIFFERENT MODEL on the retry. Re-asking the model that just failed to answer
        # is not a retry, it is the same call again — which is precisely what produced three
        # identical failures on lotto24.de. A different vendor does not share the failure domain.
        for _bi, b in enumerate(shard(retry, max(1, shard_size - 1))):
            _alt = _chain[min(_bi + 1, len(_chain) - 1)] if len(_chain) > 1 else _chain[0]
            got, meta = _call_shard(E, fj, b, lang, 900 + _bi, _alt, _per)
            merged.update(got)
            metas.append(meta)
            _log("[enrich-mr]   retry via %s: %d/%d ids%s"
                 % (_alt, len(meta["returned"]), len(meta["ids"]),
                    "  ERROR: " + meta["error"] if meta.get("error") else ""))

    rewritten = len(set(merged) & want)
    cov = rewritten / float(len(want)) if want else 1.0
    report = {"coverage": round(cov, 3), "total": len(want), "rewritten": rewritten,
              "missing": sorted(want - set(merged)), "shards": metas,
              "exec_summary": next((m["exec"] for m in metas if m.get("exec")), ""),
              "wall_ms": max([m["ms"] for m in metas] or [0]),
              "serial_ms_equiv": sum(m["ms"] for m in metas)}
    _log("[enrich-mr] COVERAGE %d/%d = %.0f%%  (wall %dms vs %dms serial-equivalent)"
         % (rewritten, len(want), cov * 100, report["wall_ms"], report["serial_ms_equiv"]))
    if cov < MIN_COVERAGE:
        _log("[enrich-mr] !! coverage %.0f%% is BELOW the %.0f%% floor — the deck would render "
             "template text for %d finding(s). Caller should treat this as a quality failure."
             % (cov * 100, MIN_COVERAGE * 100, len(report["missing"])))
    return merged, report


def apply(fj, merged):
    """Merge rewritten prose back onto the findings, preserving engine-owned facts.

    HARD RULE (CLAUDE.md): the LLM rewrites PROSE only. Severity, evidence and CVE ids are engine
    facts and are never taken from the model.
    """
    KEEP_ENGINE = ("id", "sev", "evidence", "cves", "kind", "hosts")
    out = []
    for f in (fj.get("findings") or []):
        if not isinstance(f, dict):
            continue
        x = merged.get(str(f.get("id")))
        if not x:
            f["_enriched"] = False
            out.append(f)
            continue
        nf = dict(f)
        for k, v in x.items():
            if k in KEEP_ENGINE:
                continue
            nf[k] = v
        nf["_enriched"] = True
        out.append(nf)
    fj["findings"] = out
    return fj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("-o", "--out")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--shard-size", type=int, default=SHARD_SIZE)
    ap.add_argument("--workers", type=int, default=WORKERS)
    a = ap.parse_args()
    fj = json.load(open(a.findings, encoding="utf-8"))
    merged, rep = run(fj, a.lang, a.shard_size, a.workers)
    fj = apply(fj, merged)
    fj.setdefault("target", {})["enrich_coverage"] = rep["coverage"]
    txt = json.dumps(fj, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt)
        print(json.dumps({k: v for k, v in rep.items() if k != "shards"}, indent=2))
    else:
        print(txt)
    return 0 if rep["coverage"] >= MIN_COVERAGE else 2


if __name__ == "__main__":
    sys.exit(main())
