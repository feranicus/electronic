#!/usr/bin/env python3
"""
model_probe.py — does every model in the chain EXIST, and does it actually answer?

WHY THIS EXISTS
---------------
`deepseek-v4-flash` was put at the head of the enrichment chain from DigitalOcean's PRICING PAGE
("DeepSeek V4 Flash", $0.112/$0.224 per 1M). The API returned **HTTP 404: Not Found** on every
call, because a marketing name is not an API model id. Production discovered this, not CI:

    [warn] enrich deepseek-v4-flash attempt 1/1 (took 0s): <HTTPError 404: 'Not Found'>

CLAUDE.md already warned about exactly this — *"Catalog ids are exact and easy to get wrong: it is
`openai-gpt-oss-120b`, NOT `gpt-oss-120b`"* — and the mistake was repeated anyway, because nothing
CHECKED. `model_watch.py` runs at the end of ship.py but needs OPENAI_API_KEY, which lives on the
DROPLET and not on the operator's PC, so it silently printed "catalog unavailable — skipping" every
run. A check that cannot see the thing it checks is not a check.

WHAT THIS DOES
  1. EXISTENCE (free, no tokens): GET /v1/models and assert every id in the effective chain is
     present. A 404 model is a hard deploy failure — the head of the chain silently not existing
     means every assessment pays a wasted round-trip and quietly degrades to the backup.
  2. LIVENESS (real call, ~200 tokens each): send the actual enrichment contract to each model and
     record status / latency / whether the JSON contract held.
  3. SUGGESTION: if a chained id is missing, look for near-matches in the live catalog so the fix
     is obvious ("deepseek-v4-flash" -> did you mean "deepseek-v4"?).

    python model_probe.py                 # chain only: existence + liveness
    python model_probe.py --existence     # existence only, zero tokens
    python model_probe.py --all           # probe every text model in the catalog
    python model_probe.py --json

Exit codes: 0 ok · 2 a chained model does not exist · 3 the HEAD of the chain does not answer.
Designed to be run INSIDE the container:
    docker exec colt-web python3 /opt/shodan-skill/scripts/model_probe.py
"""
import argparse, difflib, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BASE = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("DO_INFERENCE_KEY") or ""
NON_TEXT = re.compile(r"(embed|rerank|whisper|tts|stt|image|sdxl|flux|diffusion|video|wan\d|audio)", re.I)

# The smallest prompt that still exercises the real contract: strict JSON, a findings array, prose.
CONTRACT = ('Return ONLY valid JSON, no prose outside it, shaped exactly as: '
            '{"exec_summary":"<one sentence>","findings":[{"id":"C1","what":"<one sentence>"}]}. '
            'The finding C1 is an internet-facing password manager on 217.110.51.7:443.')


def catalog():
    if not KEY:
        return None, "no OPENAI_API_KEY in this environment (run me inside colt-web)"
    try:
        req = urllib.request.Request(BASE + "/models", headers={"Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(req, timeout=25) as r:
            j = json.loads(r.read().decode("utf-8"))
        return sorted({str(m.get("id")) for m in (j.get("data") or []) if m.get("id")}), ""
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


# Payload VARIANTS, tried in order until one is accepted. A 400 means the model exists and the key
# is entitled — the request shape is what it rejected. kimi-k2.5/k2.6 both returned HTTP 400 to the
# standard payload while every other open-weight model accepted it, so the probe must distinguish
# "model is broken" from "model wants a different request" instead of writing the model off.
_VARIANTS = [
    ("standard",           {"temperature": 0.2, "max_tokens": 300}),
    ("no-temperature",     {"max_tokens": 300}),
    ("no-max_tokens",      {"temperature": 0.2}),
    ("bare",               {}),
    ("large-max_tokens",   {"temperature": 0.2, "max_tokens": 1024}),
    ("temperature-1",      {"temperature": 1.0, "max_tokens": 300}),
]


def _post(model, extra, timeout):
    payload = dict(extra)
    # Apply the SAME per-model policy production uses, so the probe and enrich.py can never
    # disagree about what a model requires (Kimi: temperature must be 1).
    try:
        import enrich as _E
        payload.update(_E._model_params(model))
    except Exception:
        pass
    payload["model"] = model
    payload["messages"] = [{"role": "user", "content": CONTRACT}]
    req = urllib.request.Request(
        BASE + "/chat/completions", method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def call(model, timeout=45, variants=True):
    """One real contract call. -> dict(ok, http, ms, json_ok, err, tokens_out, variant).

    On HTTP 400 the API's own error BODY is captured and the alternative payload shapes are tried:
    a 400 is the server telling us what it wants, and discarding that message is how kimi-k2.6 got
    written off as broken when it is very likely fine.
    """
    t0 = time.time()
    tried, last_detail = [], ""
    for vname, extra in (_VARIANTS if variants else _VARIANTS[:1]):
        try:
            body = _post(model, extra, timeout)
            ms = int((time.time() - t0) * 1000)
            txt = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
            out_tok = ((body.get("usage") or {}).get("completion_tokens")) or len(txt) // 4
            try:
                j = json.loads(re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip())
                json_ok = isinstance(j, dict) and bool(j.get("findings") or j.get("exec_summary"))
            except Exception:
                json_ok = False
            return {"ok": True, "http": 200, "ms": ms, "json_ok": json_ok,
                    "err": "" if vname == "standard" else "accepted with payload=%s" % vname,
                    "tokens_out": out_tok, "variant": vname}
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = (e.read() or b"").decode("utf-8", "replace")[:200].replace("\n", " ")
            except Exception:
                pass
            tried.append("%s->%s" % (vname, e.code))
            if e.code != 400:                       # 403/404/429 are not payload problems
                return {"ok": False, "http": e.code, "ms": int((time.time() - t0) * 1000),
                        "json_ok": False, "err": ("HTTP %s %s" % (e.code, detail)).strip(),
                        "tokens_out": 0, "variant": vname}
            last_detail = detail
        except Exception as e:
            return {"ok": False, "http": 0, "ms": int((time.time() - t0) * 1000), "json_ok": False,
                    "err": str(e)[:70], "tokens_out": 0, "variant": vname}
    return {"ok": False, "http": 400, "ms": int((time.time() - t0) * 1000), "json_ok": False,
            "err": "400 on every payload shape [%s] :: %s" % (",".join(tried), last_detail[:110]),
            "tokens_out": 0, "variant": "none"}


def _legacy_call(model, timeout=45):
    t0 = time.time()
    payload = {"model": model, "temperature": 0.2, "max_tokens": 300,
               "messages": [{"role": "user", "content": CONTRACT}]}
    try:
        req = urllib.request.Request(
            BASE + "/chat/completions", method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8"))
        ms = int((time.time() - t0) * 1000)
        txt = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
        out_tok = ((body.get("usage") or {}).get("completion_tokens")) or len(txt) // 4
        try:
            j = json.loads(re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip())
            json_ok = isinstance(j, dict) and bool(j.get("findings") or j.get("exec_summary"))
        except Exception:
            json_ok = False
        return {"ok": True, "http": 200, "ms": ms, "json_ok": json_ok, "err": "",
                "tokens_out": out_tok}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http": e.code, "ms": int((time.time() - t0) * 1000),
                "json_ok": False, "err": "HTTP %s" % e.code, "tokens_out": 0}
    except Exception as e:
        return {"ok": False, "http": 0, "ms": int((time.time() - t0) * 1000), "json_ok": False,
                "err": str(e)[:70], "tokens_out": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--existence", action="store_true", help="catalog check only, zero tokens")
    ap.add_argument("--all", action="store_true", help="probe every text model in the catalog")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--model", help="probe ONE model through every payload variant and print the "
                                    "API's own error body (use this on a model that returns 400)")
    ap.add_argument("--via-enrich", action="store_true",
                    help="call through enrich._call — the REAL production path, which already "
                         "retries a 400 without response_format (my raw probe does not)")
    a = ap.parse_args()

    try:
        import enrich as E
        chain = list(E._chain())
    except Exception as e:
        print("[model-probe] cannot import enrich.py: %s" % e)
        return 0

    if a.model:
        print("[model-probe] deep-probing %r through %d payload variant(s)\n" % (a.model, len(_VARIANTS)))
        for vname, extra in _VARIANTS:
            try:
                body = _post(a.model, extra, a.timeout)
                txt = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
                print("  %-18s ACCEPTED  %d chars back" % (vname, len(txt)))
                print("\n[model-probe] %r works with payload=%s -> %s" % (a.model, vname, extra))
                return 0
            except urllib.error.HTTPError as e:
                det = ""
                try:
                    det = (e.read() or b"").decode("utf-8", "replace")[:300].replace("\n", " ")
                except Exception:
                    pass
                print("  %-18s HTTP %-4s %s" % (vname, e.code, det))
            except Exception as e:
                print("  %-18s ERR       %s" % (vname, str(e)[:90]))
        print("\n[model-probe] %r rejected EVERY payload shape — do not chain it." % a.model)
        return 3

    ids, err = catalog()
    report = {"base": BASE, "chain": chain, "catalog_error": err, "missing": [], "probes": []}

    if ids is None:
        print("[model-probe] catalog unavailable (%s)" % err)
        print("[model-probe] run me inside the container, where the key lives:")
        print("    docker exec colt-web python3 /opt/shodan-skill/scripts/model_probe.py")
        if a.json:
            print(json.dumps(report, indent=2))
        return 0

    print("[model-probe] %d models visible on %s" % (len(ids), BASE))
    print("\n== EXISTENCE (free) — every model in the chain must be in the catalog ==")
    have = set(ids)
    for m in chain:
        if m in have:
            print("  ok       %s" % m)
        else:
            near = difflib.get_close_matches(m, ids, n=3, cutoff=0.5)
            print("  MISSING  %-28s  <- 404s on every call.%s"
                  % (m, ("  Did you mean: " + ", ".join(near)) if near else ""))
            report["missing"].append({"model": m, "suggestions": near})

    if report["missing"] and chain and chain[0] == report["missing"][0]["model"]:
        print("\n  !! the HEAD of the chain does not exist — every assessment wastes a round-trip "
              "and silently degrades to the backup model.")

    if a.existence:
        if a.json:
            print(json.dumps(report, indent=2))
        return 2 if report["missing"] else 0

    targets = [m for m in ids if not NON_TEXT.search(m)] if a.all else chain
    print("\n== LIVENESS — a real contract call to each (%d model(s)) ==" % len(targets))
    print("  %-30s %-7s %-8s %-8s %s" % ("MODEL", "HTTP", "ms", "JSON", "note"))
    for m in targets:
        if m not in have:
            print("  %-30s %-7s %-8s %-8s %s" % (m, "404", "-", "-", "not in catalog"))
            report["probes"].append({"model": m, "http": 404, "ok": False})
            continue
        if a.via_enrich:
            # THE REAL PATH. enrich._call carries the retry logic production actually uses —
            # notably `if e.code in (400, 422): payload.pop("response_format")`. A model that 400s
            # my raw probe can still be perfectly healthy in production, which is exactly the
            # situation kimi-k2.5/k2.6 are in. Test what ships, not a simplification of it.
            t0 = time.time()
            try:
                import enrich as _E
                # _call returns a TUPLE (text, usage) — passing the tuple straight to _json is what
                # produced "'tuple' object has no attribute 'find'" for every model.
                raw, _usage = _E._call(CONTRACT, model=m, timeout=a.timeout)
                j = _E._json(raw)
                ok = isinstance(j, dict) and bool(j.get("exec_summary") or j.get("findings"))
                r = {"ok": True, "http": 200, "ms": int((time.time() - t0) * 1000),
                     "json_ok": ok, "err": "via enrich._call", "tokens_out": len(str(raw)) // 4}
            except Exception as _e:
                r = {"ok": False, "http": 0, "ms": int((time.time() - t0) * 1000),
                     "json_ok": False, "err": ("enrich._call: %s" % _e)[:90], "tokens_out": 0}
        else:
            r = call(m, a.timeout)
        print("  %-30s %-7s %-8s %-8s %s"
              % (m, r["http"] or "err", r["ms"], "ok" if r["json_ok"] else "no", r["err"]))
        r["model"] = m
        report["probes"].append(r)

    good = [p for p in report["probes"] if p.get("ok") and p.get("json_ok")]
    if good:
        good.sort(key=lambda p: p["ms"])
        print("\n[model-probe] contract-valid, fastest first: %s"
              % ", ".join("%s (%dms)" % (p["model"], p["ms"]) for p in good[:6]))
        if chain and good[0]["model"] != chain[0]:
            print("[model-probe] note: the fastest working model is %r but the chain head is %r"
                  % (good[0]["model"], chain[0]))

    if a.json:
        print(json.dumps(report, indent=2))
    if report["missing"]:
        return 2
    head_ok = any(p.get("model") == chain[0] and p.get("ok") for p in report["probes"]) if chain else True
    return 0 if head_ok else 3


if __name__ == "__main__":
    sys.exit(main())
