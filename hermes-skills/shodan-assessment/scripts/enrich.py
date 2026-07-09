#!/usr/bin/env python3
"""enrich.py — ONE DO-Qwen call driven by the DELTAS BIBLE. Turns raw findings into a Colt
pursuit-grade report: reframes prose, derives architecture/business context, adds STRENGTHS
and a Colt mitigation-mapping, writes exec_summary + a QA audit verdict. No Hermes. Facts
never changed. Safe fallback. Emits token/cost telemetry as a JSON event for Grafana/Loki."""
import os, sys, json, time, urllib.request, urllib.error
HERE  = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("ENRICH_MODEL", "qwen3.5-397b-a17b")
BASE  = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
KEY   = os.environ.get("OPENAI_API_KEY", "")
PRICE = float(os.environ.get("QWEN_PRICE_PER_M", "0.65"))
TIMEOUT  = int(os.environ.get("ENRICH_TIMEOUT", "120"))   # per-call wall budget (< pipeline subprocess timeout)
ATTEMPTS = int(os.environ.get("ENRICH_ATTEMPTS", "1"))    # keep 1 so we never blow the pipeline budget

def _bible():
    for name in ("LLM_DELTAS_BIBLE.md", "COLT_SHODAN_DECK_METHODOLOGY.md"):
        p = os.path.join(HERE, "..", "reference", name)
        if os.path.exists(p): return open(p, encoding="utf-8", errors="ignore").read()[:14000]
    return "Add Colt pursuit deltas: architecture, business context, strengths, Colt-product remediation."

PROMPT = """%s

=== RAW FINDINGS (facts verified — reframe, never alter) ===
%s

Now return ONLY the strict JSON from the OUTPUT CONTRACT above. No text around it."""

def _post(payload):
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(payload).encode(),
          headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())

def _call(text):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": text}],
               "temperature": 0.35, "max_tokens": 5000,
               "response_format": {"type": "json_object"},
               "chat_template_kwargs": {"enable_thinking": False}}
    try:
        d = _post(payload)
    except urllib.error.HTTPError:
        payload.pop("response_format", None)   # model may not accept it — raw_decode still saves us
        d = _post(payload)
    msg = d["choices"][0]["message"]
    txt = msg.get("content") or msg.get("reasoning_content") or ""
    # post-mortem log the raw model output so failures are debuggable (the "logs" to check)
    try:
        with open(os.path.join(os.environ.get("OUTDIR", "/root/work"), "enrich_last.json"), "w") as fh:
            json.dump({"model": MODEL, "finish": d["choices"][0].get("finish_reason"),
                       "usage": d.get("usage", {}), "raw": txt[:8000]}, fh, indent=2)
    except Exception: pass
    return txt, d.get("usage", {}) or {}

def _json(s):
    # Models often append text after the JSON object (-> json.loads "Extra data").
    # raw_decode reads the FIRST complete JSON object from the first '{' and ignores the rest.
    a = s.find("{")
    if a < 0: raise ValueError("no JSON object in model output")
    obj, _ = json.JSONDecoder().raw_decode(s[a:])
    return obj

def _emit(company, status, ti, to, cost, ms, error=""):
    print(json.dumps({"evt": "qwen", "company": company, "model": MODEL, "status": status,
                      "tokens_in": ti, "tokens_out": to, "cost_usd": cost, "ms": ms,
                      "error": error}), flush=True)

def enrich(fj):
    company = fj["target"].get("company", "?")
    if not KEY:
        fj["target"]["qwen"] = {"status": "skipped", "model": MODEL, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}
        _emit(company, "skipped", 0, 0, 0, 0); return fj, "no OPENAI_API_KEY — skipped"
    slim = {"company": company, "scope": fj["target"].get("scope", ""),
            "findings": [{"id": f["id"], "sev": f["sev"], "title": f["title"],
                          "evidence": f.get("evidence", [])} for f in fj["findings"]]}
    prompt = PROMPT % (_bible(), json.dumps(slim, ensure_ascii=False))
    last = ""
    for attempt in range(ATTEMPTS):
        try:
            t = time.time(); content, usage = _call(prompt); j = _json(content)
            ti = int(usage.get("prompt_tokens", 0)); to = int(usage.get("completion_tokens", 0))
            cost = round((ti + to) / 1e6 * PRICE, 6); ms = int((time.time() - t) * 1000)
            def _nid(v): return "".join(ch for ch in str(v).upper() if ch.isalnum())
            by_id = {_nid(x.get("id")): x for x in j.get("findings", [])}
            for f in fj["findings"]:
                x = by_id.get(_nid(f["id"]))
                if not x: continue
                for k in ("what", "why", "rem"):
                    if isinstance(x.get(k), list) and x[k]: f[k] = [str(v) for v in x[k]][:3]
                if x.get("realComparable"): f["realComparable"] = str(x["realComparable"])
            if j.get("exec_summary"): fj["target"]["exec_summary"] = str(j["exec_summary"])
            if j.get("qa_note"):      fj["target"]["qa_note"]      = str(j["qa_note"])
            if j.get("geopol_context"): fj["target"]["geopol_context"] = str(j["geopol_context"])
            if isinstance(j.get("strengths"), list) and j["strengths"]:
                fj["target"]["strengths"] = [str(s) for s in j["strengths"]][:5]
            if isinstance(j.get("colt_mitigation"), list) and j["colt_mitigation"]:
                fj["target"]["colt_mitigation"] = [
                    {"id": str(m.get("id","")), "finding": str(m.get("finding","")),
                     "colt": str(m.get("colt","")), "psf": str(m.get("psf","")), "oss": str(m.get("oss",""))}
                    for m in j["colt_mitigation"] if isinstance(m, dict)][:14]
            fj["target"]["qwen"] = {"status": "ok", "model": MODEL, "tokens_in": ti, "tokens_out": to, "cost_usd": cost, "ms": ms}
            _emit(company, "ok", ti, to, cost, ms)
            return fj, "enriched via DELTAS BIBLE (" + MODEL + ")"
        except Exception as e:
            import traceback; last = repr(e)
            traceback.print_exc(file=sys.stderr)   # full reason to stderr (captured by pipeline + logs)
            if attempt + 1 < ATTEMPTS: time.sleep(2 * (attempt + 1))
    fj["target"]["qwen"] = {"status": "fallback", "model": MODEL, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0, "error": last[:160]}
    _emit(company, "fallback", 0, 0, 0, 0, error=last[:160])
    return fj, "LLM unavailable (" + last[:120] + ") — kept templated text"

def main():
    p = sys.argv[1]
    os.environ.setdefault("OUTDIR", os.path.dirname(os.path.abspath(p)))
    fj = json.load(open(p)); fj, status = enrich(fj)
    json.dump(fj, open(p, "w"), indent=2, ensure_ascii=False)
    print("enrich:", status)
    if fj.get("target", {}).get("qa_note"): print(fj["target"]["qa_note"])

if __name__ == "__main__": main()
