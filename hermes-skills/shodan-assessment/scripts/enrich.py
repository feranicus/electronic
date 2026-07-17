#!/usr/bin/env python3
"""enrich.py — ONE DO-Qwen call driven by the DELTAS BIBLE. Turns raw findings into a Colt
pursuit-grade report: reframes prose, derives architecture/business context, adds STRENGTHS
and a Colt mitigation-mapping, writes exec_summary + a QA audit verdict. No Hermes. Facts
never changed. Safe fallback. Emits token/cost telemetry as a JSON event for Grafana/Loki."""
import os, re, sys, json, time, urllib.request, urllib.error
HERE  = os.path.dirname(os.path.abspath(__file__))
# MODEL CHAIN — tried in order. The first model that returns contract-valid JSON wins.
# A 429 from DO serverless is an ACCOUNT-level RPM/TPM quota (or an empty prepaid balance), so the
# retry is worthless without a *different* model to fall over to — hence a chain, not just attempts.
# Override per environment:  ENRICH_MODELS="deepseek-3.2,gpt-oss-120b,qwen3.5-397b-a17b"
# NOTE: DO Tier 1/2 accounts cannot call Anthropic/OpenAI models except gpt-oss-120b / gpt-oss-20b.
#       Run `python probe_models.py` to see what YOUR key can actually reach and which pass the
#       JSON contract — do not guess the chain.
# CHAIN — measured with `compare_models.py --lang de` on the REAL 14.6k prompt (2026-07):
#   gemma-4-31B-it    40.7s · German · 11/11 findings rewritten · 3 strengths · precedents ACCURATE
#                     (Capital One 2019, SolarWinds 2020, Colonial Pipeline 2021) · no invented CVE
#                                                                         <- HEAD (Google, Apache-2.0)
#   deepseek-3.2      25s on a 3-finding input, but TIMED OUT repeatedly on real runs; also
#                     hallucinated CVE-2021-44244 for Log4Shell          <- backup #1 (DeepSeek)
#   llama-4-maverick  44.6s, German, accurate but GENERIC precedents     <- backup #2 (Meta)
# THREE VENDORS. Measured failures: qwen3-32b + glm-5.2 = 180s timeout; kimi-k2.6 = no JSON;
# openai-gpt-oss-120b = 429 every time; anthropic-*/openai-gpt-5* = 403 on this tier.
_FALLBACKS = ["gemma-4-31B-it", "deepseek-3.2", "llama-4-maverick"]

def _chain():
    """ENRICH_MODELS wins outright. Otherwise a legacy single ENRICH_MODEL becomes the HEAD of the
    chain and the fallbacks are appended behind it — never a chain of one.
    (Bug this fixes: assess-bot/.env sets ENRICH_MODEL=deepseek-3.2, which silently collapsed the
    chain to ["deepseek-3.2"], so a DeepSeek read-timeout killed enrichment with no failover and the
    German deck fell back to English templates.)"""
    explicit = os.environ.get("ENRICH_MODELS", "").strip()
    if explicit:
        out = [m.strip() for m in explicit.split(",") if m.strip()]
    else:
        head = os.environ.get("ENRICH_MODEL", "").strip()
        out = ([head] if head else []) + _FALLBACKS
    seen, chain = set(), []
    for m in out:
        if m not in seen:
            seen.add(m); chain.append(m)
    return chain

MODELS = _chain()
MODEL = MODELS[0]                      # back-compat: telemetry/default naming
# per-1M-token price by model (USD). Unknown models fall back to QWEN_PRICE_PER_M.
try:
    PRICE_MAP = json.loads(os.environ.get("ENRICH_PRICE_MAP", "{}"))
except Exception:
    PRICE_MAP = {}
BASE  = os.environ.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
KEY   = os.environ.get("OPENAI_API_KEY", "")
PRICE = float(os.environ.get("QWEN_PRICE_PER_M", "0.65"))
TIMEOUT  = int(os.environ.get("ENRICH_TIMEOUT", "120"))   # per-call wall budget (< pipeline subprocess timeout)
# Attempts PER MODEL. With a multi-model chain, failover IS the retry — retrying the same slow model
# twice inside a fixed budget is what starved the chain on the Suzuki run (attempts=5, every model
# timed out, deck fell back to English templates). So: 1 attempt each when we have >=2 models, 2 only
# when there is nothing to fail over to.
def _attempts(n_models):
    env = os.environ.get("ENRICH_ATTEMPTS")
    if env:
        try: return max(1, int(env))
        except ValueError: pass
    return 1 if n_models >= 2 else 2

ATTEMPTS = _attempts(len(MODELS))
BUDGET_S = int(os.environ.get("ENRICH_BUDGET_S", "245"))  # hard wall for the whole chain; run_assessment
                                                          # kills enrich at 260s, so stop before that.
BACKOFF  = float(os.environ.get("ENRICH_BACKOFF_S", "3")) # base for exponential backoff on 429/5xx

def _bible():
    for name in ("LLM_DELTAS_BIBLE.md", "COLT_SHODAN_DECK_METHODOLOGY.md"):
        p = os.path.join(HERE, "..", "reference", name)
        if os.path.exists(p): return open(p, encoding="utf-8", errors="ignore").read()[:14000]
    return "Add Colt pursuit deltas: architecture, business context, strengths, Colt-product remediation."

PROMPT = """%s
%s
=== RAW FINDINGS (facts verified — reframe, never alter) ===
%s

=== FACTUAL GUARDRAILS — a customer deck carries these claims ===
1. CVE IDs: cite a CVE identifier ONLY if that exact ID appears in the RAW FINDINGS above. NEVER
   write a CVE number from memory — a plausible-but-wrong ID (e.g. Log4Shell is CVE-2021-44228, not
   CVE-2021-44244) is worse than no ID. If you want to reference an incident whose CVE you are not
   certain of, name the incident and the YEAR and omit the CVE number entirely.
2. realComparable MUST be a REAL, PUBLIC, DATED incident (organisation + year + recorded impact).
   Prefer one that matches THIS finding's exposure class. If you cannot recall a genuine matching
   incident, return a shorter answer or omit the field — NEVER invent a company, date or figure.
3. Money figures in precedents: only well-documented public numbers. If it was a proposed/reduced
   fine, say so (e.g. "urspruenglich angekuendigt, spaeter reduziert").
4. Never state a vulnerability is exploited/present when the evidence only shows a version banner.

Now return ONLY the strict JSON from the OUTPUT CONTRACT above. No text around it."""

# The deck CHROME is translated by scripts/i18n/deck_i18n.js from a committed dictionary. The PROSE
# (exec_summary, what/why/rem, strengths, colt_mitigation, realComparable, geopol_context) is written
# by the model, so the language instruction has to go in the prompt — a dictionary can never cover it.
LANG_DE = """
=== SPRACHE / LANGUAGE — VERBINDLICH ===
Schreibe ALLE Fliesstexte AUSSCHLIESSLICH auf Hochdeutsch (formell, "Sie"-Form, Business-Register
fuer CISO/CFO). Das gilt fuer JEDEN Wert der Felder: exec_summary, what, why, rem, strengths,
colt_mitigation, realComparable, lossScenario, geopol_context, qa_note.
Uebersetze auch die Fachbegriffe ins Deutsche:
  ALE -> Schadenserwartungswert (SEW) · PML -> Wahrscheinlicher Hoechstschaden (WHS)
  LEF -> Schadensereignishaeufigkeit (SEH) · TEF -> Bedrohungsereignishaeufigkeit (BEH)
  Loss Magnitude -> Schadenshoehe (SH) · Cost of Delay -> Kosten der Verzoegerung (KdV)
  ROSI -> Rendite der Sicherheitsinvestition (RSI) · Kill Chain -> Angriffskette
  finding -> Befund · exposure -> Exposition · remediation -> Behebung
NICHT uebersetzen (Eigennamen/IDs): Colt-Produktnamen (Colt SASE, ZTNA, WAF, Managed Firewall,
IP Guardian, DPI/NDR, SD-WAN), Rahmenwerksnamen (FAIR, MITRE ATT&CK, NIST, BSI, ISO, TISAX, NIS2,
DORA, Admiralty, Monte-Carlo, Shodan, CISA KEV, EPSS, CVSS), CVE-Kennungen, Hostnamen, IPs, Ports,
Protokollnamen (RDP, Telnet, TLS, VPN) und Firmennamen.
Die JSON-SCHLUESSEL bleiben unveraendert englisch — nur die WERTE sind deutsch.
Fakten, Zahlen, IDs und Nachweise bleiben unveraendert.
"""

def _post(payload, timeout=None):
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(payload).encode(),
          headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=(timeout or TIMEOUT)) as r:
        return json.loads(r.read())

def _call(text, model=None, timeout=None):
    model = model or MODEL
    payload = {"model": model, "messages": [{"role": "user", "content": text}],
               "temperature": 0.35, "max_tokens": 6500,   # rich rem bodies need room, but every extra
                                           # token is wall-clock: 8000 pushed a 13-finding
                                           # deck past the per-call budget.
               "response_format": {"type": "json_object"},
               "chat_template_kwargs": {"enable_thinking": False}}
    try:
        d = _post(payload, timeout)
    except urllib.error.HTTPError as e:
        if e.code in (400, 422):
            payload.pop("response_format", None)   # model may not accept it — raw_decode still saves us
            payload.pop("chat_template_kwargs", None)
            d = _post(payload, timeout)
        else:
            raise                                   # 429/5xx must reach the retry/failover logic
    msg = d["choices"][0]["message"]
    txt = msg.get("content") or msg.get("reasoning_content") or ""
    # post-mortem log the raw model output so failures are debuggable (the "logs" to check)
    try:
        with open(os.path.join(os.environ.get("OUTDIR", "/root/work"), "enrich_last.json"), "w") as fh:
            json.dump({"model": model, "finish": d["choices"][0].get("finish_reason"),
                       "usage": d.get("usage", {}), "raw": txt[:8000]}, fh, indent=2)
    except Exception: pass
    return txt, d.get("usage", {}) or {}

def _json(s):
    """Parse the model's answer into the OBJECT we expect, tolerating the shapes models really emit.

    Models append prose after the JSON (-> json.loads "Extra data"), so raw_decode reads the first
    complete value and ignores the rest. But that value is not always an object: gemma-4-31B-it
    returned a top-level ARRAY [{...}] on the Bezeq run, and `j.get("findings")` raised
    AttributeError('list' object has no attribute 'get') — throwing away a perfectly good 162s
    answer and starving the rest of the chain. Normalise instead of failing over.
    """
    a = s.find("{")
    b = s.find("[")
    start = min(x for x in (a, b) if x >= 0) if (a >= 0 or b >= 0) else -1
    if start < 0:
        raise ValueError("no JSON value in model output")
    obj, _ = json.JSONDecoder().raw_decode(s[start:])

    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        # [ {exec_summary:..., findings:[...]} ]  -> unwrap the first dict that looks like ours
        for item in obj:
            if isinstance(item, dict) and ("exec_summary" in item or "findings" in item):
                return item
        # [ {id:C1,...}, {id:C2,...} ] -> a bare findings array; wrap it into the contract
        if obj and all(isinstance(x, dict) for x in obj) and any("id" in x for x in obj):
            return {"findings": obj}
        for item in obj:                       # last resort: any dict at all
            if isinstance(item, dict):
                return item
    raise ValueError("model returned %s, not the JSON object contract" % type(obj).__name__)

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.I)

def _audit_cves(fj, j):
    """A prompt rule is a request, not a guarantee. Cross-check every CVE the model wrote against the
    CVEs that actually appear in the scan evidence. Anything else was recalled from memory and may be
    wrong (deepseek-3.2 emitted CVE-2021-44244 for Log4Shell; the real ID is CVE-2021-44228).
    We do NOT silently rewrite the prose — we strip the unverifiable ID and flag it, because a wrong
    identifier in a customer deck is worse than no identifier."""
    known = set()
    for f in fj.get("findings", []):
        blob = json.dumps(f, ensure_ascii=False)
        known.update(x.upper() for x in _CVE_RE.findall(blob))
    invented, checked = [], 0
    for x in (j.get("findings") or []):
        for k in ("realComparable", "lossScenario"):
            v = x.get(k)
            if not isinstance(v, str):
                continue
            checked += 1
            for cve in _CVE_RE.findall(v):
                if cve.upper() not in known:
                    invented.append(cve.upper())
                    # keep the sentence, drop the unverifiable identifier
                    v = v.replace(cve, "").replace("  ", " ").replace("( )", "").replace("·  ·", "·")
            x[k] = v.strip(" ·-")
    if invented:
        print("[warn] enrich: %d CVE id(s) cited from model memory, not present in the scan evidence "
              "-> stripped from the deck: %s" % (len(invented), ", ".join(sorted(set(invented)))),
              file=sys.stderr)
    return sorted(set(invented))


def _emit(company, status, ti, to, cost, ms, error="", model=None, attempts=0, chain=None):
    print(json.dumps({"evt": "qwen", "company": company, "user": os.environ.get("COLT_USER", ""),
                      "model": model or MODEL, "status": status,
                      "tokens_in": ti, "tokens_out": to, "cost_usd": cost, "ms": ms,
                      "attempts": attempts, "chain": chain or MODELS, "error": error}), flush=True)

def _price(model):
    return float(PRICE_MAP.get(model, PRICE))

def _retryable(e):
    """429 = account RPM/TPM quota; 5xx/timeouts = transient. Both are worth a retry / failover."""
    if isinstance(e, urllib.error.HTTPError):
        return e.code == 429 or 500 <= e.code < 600
    return isinstance(e, (urllib.error.URLError, TimeoutError, OSError))

def enrich(fj, lang="en"):
    company = fj["target"].get("company", "?")
    if not KEY:
        fj["target"]["qwen"] = {"status": "skipped", "model": MODEL, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}
        _emit(company, "skipped", 0, 0, 0, 0); return fj, "no OPENAI_API_KEY — skipped"
    # Cap the evidence per finding: the model needs a few concrete host:port examples to be specific,
    # not all 3,971. On a large estate the full list bloats the prompt (and therefore the latency)
    # without making the prose any better.
    _ev_cap = int(os.environ.get("ENRICH_EVIDENCE_CAP", "6"))
    slim = {"company": company, "scope": fj["target"].get("scope", "")[:300],
            "findings": [{"id": f["id"], "sev": f["sev"], "title": f["title"],
                          "evidence": (f.get("evidence", []) or [])[:_ev_cap]}
                         for f in fj["findings"]]}
    prompt = PROMPT % (_bible(), (LANG_DE if str(lang).lower().startswith("de") else ""),
                       json.dumps(slim, ensure_ascii=False))
    last = ""
    t0_chain = time.time()
    tried = 0
    for mi, model in enumerate(MODELS):
      for attempt in range(ATTEMPTS):
        if time.time() - t0_chain > BUDGET_S:
            last = last or "budget exhausted"
            print("[warn] enrich: %ds budget exhausted — stopping chain" % BUDGET_S, file=sys.stderr)
            break
        tried += 1
        # DEADLINE-AWARE TIMEOUT. With ENRICH_TIMEOUT=200 and a 230s budget, one slow model ate the
        # ENTIRE budget and the backup never ran (that is exactly how the SGS run died with
        # chain=[deepseek] and no failover). Each call may only use its fair share of what is left,
        # so there is always time for the next model.
        left = BUDGET_S - (time.time() - t0_chain)
        models_left = max(1, len(MODELS) - mi)
        # ALLOCATION. Splitting the budget evenly (left/models_left) gave every model 81s on the
        # Huawei run — below the time a 13-finding deck actually needs with the rich WHY-COLT/WHAT/HOW
        # contract, so all three timed out and the deck fell back to English templates.
        # The head is the model we WANT to win: give it ~55% of what is left, and only start
        # shrinking when the chain is nearly exhausted. Floor 60s, ceiling ENRICH_TIMEOUT.
        share = 0.55 if models_left > 1 else 1.0
        per_call = int(max(60, min(TIMEOUT, left * share)))
        if left < 30:
            last = last or "budget exhausted"; break
        try:
            t = time.time(); content, usage = _call(prompt, model, per_call); j = _json(content)
            ti = int(usage.get("prompt_tokens", 0)); to = int(usage.get("completion_tokens", 0))
            cost = round((ti + to) / 1e6 * _price(model), 6); ms = int((time.time() - t) * 1000)
            _bad_cves = _audit_cves(fj, j)          # strip hallucinated CVE ids before they reach a slide
            def _nid(v): return "".join(ch for ch in str(v).upper() if ch.isalnum())
            by_id = {_nid(x.get("id")): x for x in j.get("findings", [])}
            for f in fj["findings"]:
                x = by_id.get(_nid(f["id"]))
                if not x: continue
                for k in ("what", "why"):
                    if isinstance(x.get(k), list) and x[k]:
                        f[k] = [str(v) for v in x[k]][:3]
                # `rem` may be rich objects {tag,title,body} — the findings deck renders title bold with
                # the body underneath (up to 5 rows). str() would have turned them into "{'tag': ...}".
                if isinstance(x.get("rem"), list) and x["rem"]:
                    _rem = []
                    for v in x["rem"][:5]:
                        if isinstance(v, dict):
                            _tag = str(v.get("tag", "COLT")).upper()
                            if _tag not in ("COLT", "PSF", "OSS", "VENDOR"): _tag = "COLT"
                            _rem.append({"tag": _tag, "title": str(v.get("title", ""))[:120],
                                         "body": str(v.get("body", ""))[:400]})
                        else:
                            _rem.append(str(v))
                    f["rem"] = _rem
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
            fj["target"]["qwen"] = {"status": "ok", "model": model, "tokens_in": ti, "tokens_out": to,
                                    "cost_usd": cost, "ms": ms, "attempts": tried,
                                    "failover": (mi > 0), "chain": MODELS,
                                    "cves_stripped": _bad_cves}
            if mi > 0:
                print("PROGRESS: [88%%] AI enrichment recovered on %s (%s failed) — deck stays full quality"
                      % (model, ", ".join(MODELS[:mi])), flush=True)
            _emit(company, "ok", ti, to, cost, ms, model=model, attempts=tried)
            if _bad_cves:
                print(json.dumps({"evt": "hallucination_guard", "company": company,
                                  "model": model, "cves_stripped": _bad_cves}), flush=True)
            return fj, "enriched via DELTAS BIBLE (%s%s)" % (model, "  [failover]" if mi else "")
        except Exception as e:
            last = repr(e)
            code = getattr(e, "code", None)
            _took = int(time.time() - t)
            print("[warn] enrich %s attempt %d/%d (took %ds, cap %ds, %ds budget left): %s"
                  % (model, attempt + 1, ATTEMPTS, _took, per_call,
                     int(BUDGET_S - (time.time() - t0_chain)), last[:160]), file=sys.stderr)
            if not _retryable(e):
                break                      # bad model name / contract error -> next model immediately
            if attempt + 1 < ATTEMPTS:
                # 429 = account quota: honour Retry-After when DO sends it, else exponential backoff
                wait = BACKOFF * (2 ** attempt)
                try:
                    ra = e.headers.get("Retry-After") if hasattr(e, "headers") and e.headers else None
                    if ra: wait = min(float(ra), 30)
                except Exception: pass
                left = BUDGET_S - (time.time() - t0_chain)
                if wait >= left: break     # no point sleeping past the budget -> fail over now
                print("[info] enrich: %s -> retry in %.0fs" % ("429 quota" if code == 429 else "error", wait),
                      file=sys.stderr)
                time.sleep(wait)
      if time.time() - t0_chain > BUDGET_S: break
      if mi + 1 < len(MODELS):
          # Operator-visible on the web progress bar AND in telegram: say WHICH model died, WHY, and
          # what we are switching to. "shitty fallback" with no explanation is what this replaces.
          _why = ("timed out" if "timed out" in last.lower() or "timeout" in last.lower()
                  else "rate-limited (429)" if "429" in last
                  else "refused (403)" if "403" in last
                  else "bad response")
          _pct = 62 + int(26 * (mi + 1) / max(1, len(MODELS)))
          # report what it ACTUALLY took, not the cap — "bad response after 175s" was misleading
          # when the model answered in 162s and it was our parser that rejected it.
          _took = int(time.time() - t)
          print("PROGRESS: [%d%%] AI model %s %s after %ds — switching to %s"
                % (_pct, model, _why, _took, MODELS[mi + 1]), flush=True)
          print(json.dumps({"evt": "qwen_attempt", "company": company, "model": model,
                            "status": "failover", "reason": _why, "error": last[:200],
                            "timeout_s": per_call, "took_s": _took, "next_model": MODELS[mi + 1],
                            "attempt": tried, "chain": MODELS}), flush=True)

    fj["target"]["qwen"] = {"status": "fallback", "model": MODELS[0], "tokens_in": 0, "tokens_out": 0,
                            "cost_usd": 0, "attempts": tried, "chain": MODELS, "error": last[:160]}
    _emit(company, "fallback", 0, 0, 0, 0, error=last[:160], attempts=tried)
    return fj, "LLM unavailable across %d model(s) %s (%s) — kept templated text" % (
        len(MODELS), MODELS, last[:120])

def main():
    p = sys.argv[1]
    # language: 2nd positional arg wins, else DECK_LANG (run_assessment passes it in the env)
    lang = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("DECK_LANG", "en")
    os.environ.setdefault("OUTDIR", os.path.dirname(os.path.abspath(p)))
    fj = json.load(open(p)); fj, status = enrich(fj, lang)
    json.dump(fj, open(p, "w"), indent=2, ensure_ascii=False)
    print("enrich:", status)
    if fj.get("target", {}).get("qa_note"): print(fj["target"]["qa_note"])

if __name__ == "__main__": main()
