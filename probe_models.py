#!/usr/bin/env python3
"""
probe_models.py — find out which models YOUR DigitalOcean key can actually reach, and which of them
survive the real enrichment contract. Then set ENRICH_MODELS from evidence instead of guesswork.

WHY THIS EXISTS
  There is no "best model for PowerPoint". The decks are rendered by deterministic JS (pptxgenjs);
  the LLM only returns a JSON blob of prose. So the only things that matter are:
     1. can we call it at all on this account/tier,
     2. does it return CONTRACT-VALID JSON (not prose, not markdown-fenced, not truncated),
     3. is the prose usable (and German when asked),
     4. latency + price.
  DO Tier 1/2 accounts cannot call Anthropic/OpenAI models at all (except gpt-oss-*), so the honest
  answer is account-specific. This probes it.

RUN (read-only; nothing on the droplet changes):
    python probe_models.py                 # probe via colt-web on the droplet (uses its key)
    python probe_models.py --local         # probe from here (needs OPENAI_API_KEY in the env)
    python probe_models.py --lang de       # also score German output
    python probe_models.py --json
"""
import argparse, json, os, subprocess, sys

HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", "")
SSH  = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"] + (
       ["-i", KEY] if KEY and os.path.exists(KEY) else [])
CT   = os.environ.get("COLT_CONTAINER", "colt-web")

# This runs INSIDE the container (it has OPENAI_API_KEY + OPENAI_BASE_URL already).
REMOTE_PROBE = r'''
import json, os, time, urllib.request, urllib.error
BASE = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
KEY  = os.environ.get("OPENAI_API_KEY", "")
LANG = os.environ.get("PROBE_LANG", "en")
if not KEY:
    print(json.dumps({"error": "no OPENAI_API_KEY in the container"})); raise SystemExit

def _req(url, data=None, timeout=60):
    r = urllib.request.Request(url, data=(json.dumps(data).encode() if data else None),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as h:
        return json.loads(h.read())

# 1) what does this key actually see?
try:
    catalog = [m.get("id") for m in _req(BASE + "/models").get("data", [])]
except Exception as e:
    catalog = []; print("[warn] /models failed: %r" % e)

# 2) the REAL contract: same shape enrich.py demands
CONTRACT = ("Return ONLY strict JSON, no prose, no markdown fence: "
            '{"exec_summary": "<2 sentences>", '
            '"findings":[{"id":"C1","what":["..."],"why":["..."],"rem":["..."],"realComparable":"..."}], '
            '"strengths":["..."]} '
            "Subject: an internet-exposed PostgreSQL database found on a manufacturer's edge.")
if LANG == "de":
    CONTRACT += " Schreibe ALLE Fliesstexte auf Hochdeutsch (Sie-Form). JSON-Schluessel bleiben englisch."

# Testing all ~74 models would take an hour. Score the catalog against a preference list instead:
# what we need is FAST + SMART + strict JSON + good German. Reasoning/coding/embedding/image models
# are useless here. Ordered best-guess first; only ones actually present in the catalog are probed.
PREFERRED = [
    # fast + smart, strong German, excellent instruction-following
    "anthropic-claude-haiku-4.5", "anthropic-claude-4.5-sonnet", "anthropic-claude-4.6-sonnet",
    "anthropic-claude-5-sonnet", "anthropic-claude-fable-5",
    # openai-family on DO
    "openai-gpt-5-mini", "openai-gpt-5", "gpt-oss-120b", "gpt-oss-20b",
    # open-weight workhorses (cheapest)
    "deepseek-3.2", "deepseek-r1-distill-llama-70b", "qwen3.5-397b-a17b", "alibaba-qwen3-32b",
    "llama3.3-70b-instruct", "mistral-nemo-instruct-2407",
]
_SKIP = ("embed", "rerank", "whisper", "tts", "image", "guard", "mini-lm", "bge-", "all-mini")

def _vendor(m):
    m = m.lower()
    for v in ("anthropic", "openai", "gpt-oss", "deepseek", "qwen", "llama", "mistral", "google", "fal"):
        if v in m: return "gpt-oss" if v == "gpt-oss" else v
    return "other"

env_models = [m for m in (os.environ.get("PROBE_MODELS", "").split(",")) if m.strip()]
if env_models:
    CANDIDATES = env_models
else:
    inc = [m for m in PREFERRED if m in catalog]
    # anything in the catalog from a vendor we have no candidate for yet (so we never miss a family)
    have = {_vendor(m) for m in inc}
    for m in catalog:
        if any(x in m.lower() for x in _SKIP): continue
        if _vendor(m) not in have:
            inc.append(m); have.add(_vendor(m))
    CANDIDATES = inc[:10]
print("catalog: %d models | probing %d candidates" % (len(catalog), len(CANDIDATES)))

out = []
for m in CANDIDATES:
    m = m.strip()
    if not m: continue
    rec = {"model": m, "vendor": _vendor(m)}
    t = time.time()
    try:
        d = _req(BASE + "/chat/completions", {
            "model": m, "messages": [{"role": "user", "content": CONTRACT}],
            "temperature": 0.3, "max_tokens": 700,
            "response_format": {"type": "json_object"}}, timeout=90)
        rec["ms"] = int((time.time() - t) * 1000)
        msg = d["choices"][0]["message"]
        txt = msg.get("content") or msg.get("reasoning_content") or ""
        u = d.get("usage", {}) or {}
        rec["tokens_in"] = u.get("prompt_tokens", 0); rec["tokens_out"] = u.get("completion_tokens", 0)
        rec["finish"] = d["choices"][0].get("finish_reason")
        # contract checks
        try:
            a = txt.find("{")
            j, _ = json.JSONDecoder().raw_decode(txt[a:])
            rec["json_ok"] = True
            rec["has_keys"] = sorted(set(j.keys()) & {"exec_summary", "findings", "strengths"})
            rec["contract_ok"] = ("exec_summary" in j and isinstance(j.get("findings"), list))
            body = json.dumps(j, ensure_ascii=False)
            rec["fenced"] = txt.strip().startswith("```")
            if LANG == "de":
                de = sum(w in body for w in ("Datenbank", "exponiert", "Internet", "Sie", "Behebung",
                                             "Risiko", "Angreifer", "Schaden"))
                en = sum(w in body for w in (" the ", " is ", " and ", "database", "exposed"))
                rec["german"] = (de > en)
            rec["sample"] = str(j.get("exec_summary", ""))[:150]
        except Exception as e:
            rec["json_ok"] = False; rec["contract_ok"] = False; rec["sample"] = txt[:150]
        rec["status"] = "ok" if rec.get("contract_ok") else "bad-contract"
    except urllib.error.HTTPError as e:
        rec["status"] = "http-%d" % e.code
        rec["error"] = {401: "no access on this tier/key", 429: "account RPM/TPM quota or empty prepaid balance",
                        404: "model not on this endpoint"}.get(e.code, e.reason)
    except Exception as e:
        rec["status"] = "error"; rec["error"] = repr(e)[:120]
    out.append(rec)

print("PROBE_JSON_START")
print(json.dumps({"catalog": catalog, "results": out}, indent=1))
'''


def run_remote(lang, models):
    # each var needs its OWN -e; a single "-e A=1 B=2" makes docker read B=2 as the container name
    # (that was the "No such container: PROBE_MODELS=" error).
    env = "-e PROBE_LANG=%s" % lang
    if models:
        env += " -e PROBE_MODELS=%s" % models
    cmd = SSH + ["%s@%s" % (USER, HOST),
                 "docker exec %s -i %s python3 -" % (env, CT)]
    r = subprocess.run(cmd, input=REMOTE_PROBE.encode("utf-8"), capture_output=True)
    out = r.stdout.decode("utf-8", "ignore")
    if "PROBE_JSON_START" not in out:
        sys.exit("[X] probe failed:\n" + (r.stderr.decode("utf-8", "ignore")[:600] or out[:600]))
    return json.loads(out.split("PROBE_JSON_START", 1)[1])


def run_local(lang, models):
    g = {"__name__": "__main__"}
    os.environ["PROBE_LANG"] = lang
    if models: os.environ["PROBE_MODELS"] = models
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(REMOTE_PROBE, "probe", "exec"), g)
    out = buf.getvalue()
    return json.loads(out.split("PROBE_JSON_START", 1)[1])


def _vendor_local(m):
    m = m.lower()
    for v in ("anthropic", "openai", "gpt-oss", "deepseek", "qwen", "llama", "mistral", "google", "fal"):
        if v in m: return v
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="probe from this machine instead of the droplet")
    ap.add_argument("--lang", default="en", choices=["en", "de"])
    ap.add_argument("--models", default="", help="comma-separated shortlist (default: whole catalog)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    d = run_local(a.lang, a.models) if a.local else run_remote(a.lang, a.models)
    if a.json:
        print(json.dumps(d, indent=2)); return

    print("\n" + "=" * 78)
    print("  MODEL PROBE — what this account can actually use for deck enrichment (lang=%s)" % a.lang)
    print("=" * 78)
    cat = d.get("catalog") or []
    print("  catalog visible to this key: %d model(s)" % len(cat))
    if cat:
        byv = {}
        for m in cat:
            byv.setdefault(_vendor_local(m), []).append(m)
        for v in sorted(byv):
            print("    %-10s %s" % (v, ", ".join(sorted(byv[v]))[:150]))
    rows = d.get("results") or []
    print("\n  %-30s %-14s %7s %8s %6s  %s" % ("model", "status", "ms", "tok_out", "JSON", "note"))
    print("  " + "-" * 76)
    ok = []
    for r in sorted(rows, key=lambda x: (x.get("status") != "ok", x.get("ms") or 9e9)):
        note = r.get("error", "")
        if r.get("status") == "ok":
            note = ("German OK" if r.get("german") else ("NOT German!" if a.lang == "de" else "contract OK"))
            ok.append(r)
        print("  %-30s %-14s %7s %8s %6s  %s" % (
            r["model"][:30], r.get("status", "?"), r.get("ms", "-"), r.get("tokens_out", "-"),
            "yes" if r.get("json_ok") else "no", note[:24]))
    if ok:
        # RULE: the backup MUST be a different vendor. A 429/outage is usually provider-wide, so
        # "deepseek -> another deepseek" is not a backup at all. Pick the best per vendor, then order
        # by latency: fastest good model heads the chain, different-vendor backups behind it.
        best_per_vendor, seen = [], set()
        for x in ok:
            v = x.get("vendor", "other")
            if v not in seen:
                seen.add(v); best_per_vendor.append(x)
        chain_models = [x["model"] for x in best_per_vendor[:3]]
        print("\n  Passed the REAL enrichment contract (fastest first):")
        for x in ok[:6]:
            print("    %-30s %-10s %5dms  %s" % (x["model"], x.get("vendor", "?"), x.get("ms", 0),
                                                 x.get("sample", "")[:52]))
        print("\n  Recommended chain — best model per VENDOR, so one provider's 429 cannot kill")
        print("  the whole chain (that is what a backup is for):")
        for i, x in enumerate(best_per_vendor[:3]):
            print("    %d. %-28s %-10s %5dms" % (i + 1, x["model"], x.get("vendor", "?"), x.get("ms", 0)))
        print("\n  Put this in assess-bot/.env on the droplet, then redeploy:")
        print("    ENRICH_MODELS=\"%s\"" % ",".join(chain_models))
        print("    ENRICH_TIMEOUT=90        # per call; the chain is deadline-aware inside a 230s budget")
        print("    # (remove/ignore ENRICH_MODEL — a single value now just heads the chain)")
    else:
        print("\n  NOTHING passed. If everything says http-429, that is an ACCOUNT quota or an empty")
        print("  prepaid balance — a different model will not help. Check")
        print("  https://cloud.digitalocean.com/limits and the serverless prepaid balance.")
    print()


if __name__ == "__main__":
    main()
