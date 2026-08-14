#!/usr/bin/env python3
"""enrich.py — ONE DO-Qwen call driven by the DELTAS BIBLE. Turns raw findings into a customer
pursuit-grade report: reframes prose, derives architecture/business context, adds STRENGTHS
and a service mitigation-mapping, writes exec_summary + a QA audit verdict. No Hermes. Facts
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
# ORDER IS EVIDENCE, NOT TASTE (2026-07). gemma-4-31B-it was HEAD and is the reason runs were slow:
# as head it takes the biggest slice (55% of the budget = 175s), then times out at exactly the cap,
# burning ~46% of the whole budget producing nothing — and it does this erratically on IDENTICAL
# input (measured: 53s/2758tok good · 81s timeout · 162s top-level-list · 4s '{}' · 175s timeout).
# It was also the ONLY model in the chain never measured by compare_models.py on the real prompt.
# The real-prompt bake-off measured deepseek-3.2 at 25.0s and llama-4-maverick at 44.6s, both
# contract-valid with good German. So: fastest-and-best measured goes first, the erratic one last.
# Re-decide with `python compare_models.py --lang de` + check_enrich.py — never from theory.
# CHAIN ORDER IS EVIDENCE, NOT TASTE (see CLAUDE.md "Model bake-off").
#   deepseek-v4-flash  $0.112/$0.224 per 1M  <- NEW HEAD. DO's published rate makes it ~4x cheaper
#                                               on input and ~6x on output than V3.2, same vendor
#                                               lineage, instruct (not a thinking model).
#   deepseek-3.2       $0.425/$1.36          <- proven on the REAL prompt: 25.0s, contract-valid,
#                                               good German. Demoted to backup, not deleted.
#   llama-4-maverick   $0.25/$0.87           <- DIFFERENT VENDOR (Meta): a 429 is provider-wide, so
#                                               the backup must not share a failure domain.
#   gemma-4-31B-it     $0.18/$0.50           <- last. Measured ERRATIC on identical input:
#                                               53s/2758tok good | 81s timeout | 162s top-level list
#                                               | 4s empty {}. Kept as a third chance only.
# NOT in the chain, deliberately: kimi-k3 (DO's changelog: "tuned for max thinking effort by
# default" -> breaks the strict-JSON contract, and DO has published no serverless rate for it).
# deepseek-v4-flash REMOVED: DigitalOcean's pricing page lists "DeepSeek V4 Flash" but that string
# is NOT an API model id — every call returned HTTP 404 and each assessment burned a wasted
# round-trip before silently degrading to deepseek-3.2. A marketing name is not a model id.
# `model_probe.py` now checks every chained id against the LIVE catalog and FAILS the deploy, so
# this class of mistake cannot reach production again. To adopt a V4 model, run inside the container:
#     docker exec colt-web python3 /opt/shodan-skill/scripts/model_probe.py --all
# and use the exact id it prints.
#
# KIMI DEMOTED FROM HEAD (lotto24.de, 2026-07) — measured, not preference. On one real run it:
#   * was rejected outright for `response_format` ("not supported for this model"), costing a round
#     trip before the 400-retry path even started (now pre-empted by MODEL_PARAMS["kimi"]["_drop"]);
#   * then consumed its ENTIRE 175s head slice and timed out, three separate times (serial chain,
#     shard 0, shard 1) — roughly 7.5 minutes of an 18-minute assessment, for zero output;
#   * and because the head takes 55% of the budget, its failure left deepseek only 112s and the last
#     two models 60s each, which is less than an 11000-token answer can physically take.
# The earlier note here predicted Kimi's downside was "bounded" because its failure mode was a fast
# 400. That prediction was wrong: the 400 is retried transparently and the retry then hangs.
# It stays in the chain — with the response_format constraint encoded, it may well answer fine — but
# the head slot belongs to the model MEASURED fastest and contract-valid on the real prompt
# (deepseek-3.2: 25.0s, valid German, compare_models.py). Put Kimi back with one env var if you
# want it: ENRICH_MODELS="kimi-k2.6,deepseek-3.2,llama-4-maverick,gemma-4-31B-it".
_FALLBACKS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]

# KIMI IS LAST, on measured evidence from the ecolines.net run — this reverses the earlier
# "keep it at position 2" decision, which was preference, not measurement.
# What it actually cost there: a 400 ("temperature must be 0.6"), then a retry that ran with
# thinking re-enabled, 46,801 characters of output, truncation at our max_tokens ceiling, an
# unparseable answer — and **164 seconds of a 175s slice consumed**, leaving llama-4-maverick
# only 118s. A model that fails is cheap; a model that fails SLOWLY starves the ones behind it.
# It stays in the chain (a fourth vendor is a real hedge against a provider-wide 429) but it can
# no longer eat the budget before a model that has been measured to work on the real prompt.

# KIMI IS HEAD, and this time on evidence rather than hope. `model_probe.py --model kimi-k2.6`
# tried six payload shapes and the API answered in one line:
#     HTTP 400 {"message":"temperature must be 1 for this model","type":"invalid_request_error"}
# We were sending temperature=0.35. That single constraint is the whole reason kimi-k2.5/k2.6
# looked broken for three rounds — the model was entitled and healthy throughout; we were
# discarding the error body that said so. MODEL_PARAMS now forces temperature=1.0 for kimi-*.
#
# WATCH THE FIRST RUN: the probe reported "ACCEPTED, 0 chars back" at max_tokens=300. Kimi reasons
# before answering, so a small ceiling can be consumed entirely by thinking. Production sends
# max_tokens=11000 with chat_template_kwargs.enable_thinking=false, so it should have room — but if
# `qwen` events show kimi returning empty, _contract_ok rejects it in seconds and deepseek-3.2
# takes over. Cost of being wrong is one fast failover, which is why head is an acceptable bet.
#
#   deepseek-3.2      fastest contract-valid model measured (870ms) — the safety net
#   llama-4-maverick  DIFFERENT VENDOR (Meta): a 429/outage is provider-wide, so the backup must
#                     not share a failure domain with the head
#   gemma-4-31B-it    last: measured erratic on identical input (53s good / 81s timeout / 4s empty)
#
# NOT chained: deepseek-4-flash (200 ok but 16s on a tiny prompt; note the id — "deepseek-v4-flash"
# 404s), kimi-k3 / glm-5.x / minimax / qwen3.5-397b (200 but JSON-invalid: thinking models),
# anthropic-* and commercial openai-gpt-* (403, visible but not entitled).

# KIMI-K2.6 IS NOT CHAINED YET — and the operator asked for it, so here is exactly why.
# It has now returned HTTP 400 through TWO DIFFERENT request shapes:
#   1. model_probe's raw payload  (model + temperature + max_tokens + messages)
#   2. THIS function's payload after the 400-retry already dropped `response_format` AND
#      `chat_template_kwargs` — i.e. the documented Kimi workaround did not rescue it.
# Two strikes with different payloads is evidence, not bad luck. Chaining it anyway would repeat
# the deepseek-v4-flash mistake: an unproven head that costs every assessment a wasted round-trip.
# It is NOT a 403/404, so the model exists and the key is entitled — something in the request is
# still wrong and we do not yet know what. Find out in one command, then promote it:
#     docker exec colt-web python3 /opt/shodan-skill/scripts/model_probe.py --model kimi-k2.6
# That prints the API's own error BODY for six payload shapes. When one is ACCEPTED, apply that
# shape here and move kimi-k2.6 to the head.
#
# Current order, all measured on the live catalog (model_probe --all):
#   deepseek-3.2      870ms, contract-valid  <- fastest valid model on the account
#   llama-4-maverick  3837ms, contract-valid, DIFFERENT VENDOR (a 429 is provider-wide)
#   gemma-4-31B-it    3615ms, contract-valid but measured erratic on identical input — last resort
# Also measured: deepseek-4-flash 200 ok but 16,043ms on a tiny prompt (id is deepseek-4-flash,
# NOT "deepseek-v4-flash", which 404s). kimi-k3 / glm-5.x / minimax / qwen3.5-397b: 200 but
# JSON-invalid (thinking models). anthropic-* and commercial openai-gpt-*: 403, not entitled.

# WHY THIS ORDER (from the operator's live `model_probe.py --all` against the real catalog):
#   kimi-k2.6        HEAD by operator preference. It EXISTS and the key is entitled — the probe got
#                    HTTP 400, not 403/404, i.e. the request SHAPE was rejected, not the model. The
#                    raw probe does not send the retry logic production uses; `_call()` below already
#                    does `if e.code in (400, 422): payload.pop("response_format")`, which is the
#                    documented cause of Kimi 400s. Risk of being wrong is ~280ms and an instant
#                    failover, not a 175s timeout — materially different from the deepseek-v4-flash
#                    phantom-id incident. UNPROVEN on the real 10k-char prompt: confirm with
#                    `model_probe.py --via-enrich` and `compare_models.py --lang de` after deploy.
#   deepseek-3.2     the SAFETY NET, and the fastest contract-valid model measured: 870ms, JSON ok.
#   llama-4-maverick DIFFERENT VENDOR (Meta) — a 429/outage is provider-wide, so the backup must not
#                    share a failure domain with the head.
#   gemma-4-31B-it   last: measured erratic on identical input (53s good / 81s timeout / 4s empty).
#
# NOT chained, with evidence from that same probe run:
#   deepseek-4-flash  200 ok but 16,043ms on a TINY prompt — cheap per token, slow per call.
#                     (Note the id: deepseek-4-flash, NOT "deepseek-v4-flash", which 404s.)
#   kimi-k3           200 but JSON-invalid — DO's changelog says "max thinking effort by default",
#                     the exact reasoning-model failure mode that breaks the strict-JSON contract.
#   glm-5/5.1/5.2, minimax-m2.5, qwen3.5-397b, nemotron-*  200 but JSON-invalid.
#   anthropic-*, openai-gpt-* (except oss)  HTTP 403 — visible in the catalog, NOT entitled.
#   openai-gpt-oss-120b, nemotron-3-super-120b, router:*   HTTP 429 — account quota.

def _chain():
    """ENRICH_MODELS wins outright. Otherwise a legacy single ENRICH_MODEL becomes the HEAD of the
    chain and the fallbacks are appended behind it — never a chain of one.
    (Bug this fixes: assess-bot/.env sets ENRICH_MODEL=deepseek-3.2, which silently collapsed the
    chain to ["deepseek-3.2"], so a DeepSeek read-timeout killed enrichment with no failover and the
    German deck fell back to English templates.)"""
    explicit = os.environ.get("ENRICH_MODELS", "").strip()
    if explicit:
        out = [m.strip() for m in explicit.split(",") if m.strip()]
        # A stale env var silently beating committed code is the exact class of bug this repo has
        # already paid for twice. If the droplet's ENRICH_MODELS disagrees with the committed order,
        # SAY SO — otherwise a carefully evidence-based chain change has no effect and nobody knows.
        if out != _FALLBACKS:
            print("[warn] ENRICH_MODELS env OVERRIDES the committed chain.\n"
                  "         env  : %s\n         repo : %s\n"
                  "       The env wins. If that is not deliberate, clear it so the repo is the source "
                  "of truth:  python set_secret.py ENRICH_MODELS   (enter the repo order)"
                  % (",".join(out), ",".join(_FALLBACKS)), file=sys.stderr)
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
    return ("Add pursuit deltas: architecture, business context, strengths, and remediation named "
            "as a VENDOR-NEUTRAL managed service category.")

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
NICHT uebersetzen (Eigennamen/IDs): Service-Kategorien (SASE, ZTNA, WAF, Managed Firewall,
IP Guardian, DPI/NDR, SD-WAN), Rahmenwerksnamen (FAIR, MITRE ATT&CK, NIST, BSI, ISO, TISAX, NIS2,
DORA, Admiralty, Monte-Carlo, Shodan, CISA KEV, EPSS, CVSS), CVE-Kennungen, Hostnamen, IPs, Ports,
Protokollnamen (RDP, Telnet, TLS, VPN) und Firmennamen.
Die JSON-SCHLUESSEL bleiben unveraendert englisch — nur die WERTE sind deutsch.
Fakten, Zahlen, IDs und Nachweise bleiben unveraendert.
"""

LANG_RU = """
=== ЯЗЫК / LANGUAGE — ОБЯЗАТЕЛЬНО ===
Пиши ВЕСЬ связный текст ИСКЛЮЧИТЕЛЬНО на русском языке (деловой регистр для CISO/CFO, обращение
на «вы», без канцелярита и без разговорных оборотов). Это относится к КАЖДОМУ значению полей:
exec_summary, what, why, rem, strengths, colt_mitigation, realComparable, lossScenario,
geopol_context, qa_note.
Переводи и профессиональную терминологию:
  ALE -> ожидаемые годовые потери (ОГП) · PML -> вероятный максимальный ущерб (ВМУ)
  LEF -> частота событий ущерба (ЧСУ) · TEF -> частота угрожающих событий (ЧУС)
  Loss Magnitude -> величина ущерба (ВУ) · Cost of Delay -> цена промедления (ЦП)
  ROSI -> рентабельность инвестиций в безопасность (РИБ) · Kill Chain -> цепочка атаки
  finding -> находка · exposure -> экспозиция · remediation -> устранение
  attack surface -> поверхность атаки · asset -> актив · threat actor -> субъект угрозы
НЕ переводить (имена собственные и идентификаторы): категории услуг (SASE, ZTNA, WAF, Managed
Firewall, IP Guardian, DPI/NDR, SD-WAN), названия методологий и стандартов (FAIR, MITRE ATT&CK,
NIST, BSI, ISO, TISAX, NIS2, DORA, Admiralty, Monte-Carlo, Shodan, CISA KEV, EPSS, CVSS),
идентификаторы CVE, имена хостов, IP-адреса, порты, названия протоколов (RDP, Telnet, TLS, VPN)
и названия компаний.
КЛЮЧИ JSON остаются английскими без изменений — на русском только ЗНАЧЕНИЯ.
Факты, числа, идентификаторы и доказательства остаются без изменений.
"""

# THE LANGUAGE REGISTRY. `LANG_DE if lang.startswith("de") else ""` was repeated in three files, so
# a third language meant finding and editing all three — and missing one would silently ship English
# prose inside a translated deck. One dict, one lookup, keyed on the 2-letter code.
LANG_BLOCKS = {"de": LANG_DE, "ru": LANG_RU}


def lang_block(lang):
    """The prompt instruction for `lang`, or "" for English / an unsupported code.

    A dictionary can translate deck chrome; it can never translate the per-company prose a model
    writes. So a deck language only truly exists once it has a block here — which is why
    deck_langs.py refuses to offer a language whose pieces are not all present.
    """
    return LANG_BLOCKS.get(str(lang or "en").strip().lower()[:2], "")

# PER-MODEL PARAMETER POLICY. Some models reject the generic payload outright. Moonshot's Kimi
# answers `HTTP 400 {"message":"temperature must be 1 for this model"}` to our standard
# temperature=0.35 — that single constraint is why kimi-k2.5/k2.6 looked broken for three rounds
# while being perfectly healthy and entitled. The API said so plainly; we were discarding the error
# body. Encode the requirement instead of guessing, and keep it next to the call that sends it.
MODEL_PARAMS = {
    # matches kimi-k2.5 / kimi-k2.6 / kimi-*
    #   temperature: the API rejects anything but 1.0 ("temperature must be 1 for this model")
    #   _drop response_format: lotto24.de logged, verbatim,
    #       "response_format type 'json_object' is not supported for this model"
    #     The 400-retry path did recover by re-posting without it, but that costs a whole round trip
    #     AND the retry then ran with no deadline of its own and hung for the full 175s cap. Encode
    #     the constraint so the request is right the FIRST time; do not pay to rediscover it.
    #
    # 2026-08 UPDATE, ecolines.net: the API now answers "temperature must be **0.6** for this model".
    # The required value CHANGED under us. That is why `_call` no longer trusts this number: it reads
    # the value out of the 400 body and re-sends with it. This entry is the fast path that avoids the
    # round trip; the parser is what keeps us correct when DO retunes the model again.
    "kimi": {"temperature": 0.6, "_drop": ["response_format"]},
}


def _model_params(model):
    """Overrides this model REQUIRES, matched on an id prefix. May include `_drop`: [keys]."""
    m = str(model or "").lower()
    for key, over in MODEL_PARAMS.items():
        if m.startswith(key):
            return dict(over)
    return {}


def _post(payload, timeout=None):
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(payload).encode(),
          headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=(timeout or TIMEOUT)) as r:
        return json.loads(r.read())

# Measured generation rate on this account (~100 output tokens/second). Used to size a request to
# the time it is actually given: see _call's max_tokens note.
TOK_PER_S = int(os.environ.get("ENRICH_TOK_PER_S", "100"))


def feasible_max_tokens(seconds, ceiling=11000, floor=2500):
    """How many output tokens can realistically be generated inside `seconds`.

    THE lotto24.de ARITHMETIC. max_tokens was a flat 11000, which needs ~110s at the measured rate.
    The chain's per-call floor is 60s. So models 3 and 4 were ALWAYS handed a slice in which the
    request they were sent could not physically complete — 60s of guaranteed timeout each, twice,
    burning budget to produce nothing. All four models "failed"; two of them never had a chance.

    Asking for fewer tokens yields shorter prose, which is a real cost — but shorter real prose beats
    the templated text that a timeout leaves behind, and it beats spending the budget on nothing.
    """
    return int(max(floor, min(ceiling, seconds * TOK_PER_S * 0.8)))


def _call(text, model=None, timeout=None, max_tokens=None):
    model = model or MODEL
    payload = {"model": model, "messages": [{"role": "user", "content": text}],
               # 6500 TRUNCATED deepseek-3.2 mid-JSON on a 6-finding estate (finish_reason=length
               # at 13,290 chars -> JSONDecodeError -> failover to a model that writes far less,
               # which is what "very small amount of addon text" in the deck actually was. The
               # contract asks for 3 sentences of `why` plus three WHY-COLT/WHAT/HOW bodies per
               # finding: roughly 1.5k tokens EACH, so six findings simply do not fit in 6500.
               "temperature": 0.35, "max_tokens": 11000,  # rich rem bodies need room, but every extra
                                           # token is wall-clock: 8000 pushed a 13-finding
                                           # deck past the per-call budget.
               "response_format": {"type": "json_object"},
               "chat_template_kwargs": {"enable_thinking": False}}
    if max_tokens:
        payload["max_tokens"] = int(max_tokens)
    elif timeout:
        payload["max_tokens"] = feasible_max_tokens(timeout)
    _over = _model_params(model)             # e.g. Kimi demands temperature == 1
    for _k in _over.pop("_drop", []):        # ...and rejects response_format outright
        payload.pop(_k, None)
    payload.update(_over)

    # STRUCTURED OUTPUT AND A TOKEN CEILING ARE NOW MUTUALLY EXCLUSIVE ON THIS ENDPOINT.
    # Observed 2026-08-14 on deepseek-3.2, llama-4-maverick AND gemma-4-31B-it in the same run —
    # three vendors at once, so this is DO's gateway, not a model. Verbatim:
    #     "max_tokens cannot be set when response_format type is 'json_object'; omit max token
    #      limits for structured outputs to avoid truncated JSON responses"
    # WE KEEP THE STRUCTURED OUTPUT AND DROP THE CEILING, which is what the server advises and is
    # the right way round on our own evidence: a max_tokens cut lands MID-JSON (that is exactly the
    # `finish_reason=length` -> JSONDecodeError at char 13,290 / char 30,117 failures already in
    # CLAUDE.md), and a dirty truncated answer wastes the slice AND yields garbage. Losing the
    # ceiling costs us only the FEASIBILITY bound; wall-clock is still bounded by the per-call
    # timeout, and a timeout is a CLEAN failure that fails over to the next model.
    # Kimi is unaffected: it has response_format in `_drop`, so it keeps its ceiling.
    # Pre-empting the 400 here saves three wasted round-trips on every single assessment.
    if "response_format" in payload:
        payload.pop("max_tokens", None)
    try:
        d = _post(payload, timeout)
    except urllib.error.HTTPError as e:
        if e.code in (400, 422):
            # PRINT WHAT THE SERVER SAID. Discarding this body is exactly how "temperature must be 1
            # for this model" stayed invisible while Kimi was written off as broken.
            _b = ""                       # bound BEFORE the try: the remediation below reads it, and
                                          # a failed read must not turn a 400 into a NameError
            try:
                _b = (e.read() or b"").decode("utf-8", "replace")[:400].replace("\n", " ")
                if _b:
                    print("[warn] enrich %s: HTTP %d from the API -> %s" % (model, e.code, _b),
                          file=sys.stderr)
            except Exception:
                pass
            # TARGETED REMEDIATION, driven by what the server actually said.
            #
            # THE ecolines.net BUG: this used to blanket-pop `chat_template_kwargs` — which is the
            # ONLY thing suppressing kimi's chain-of-thought. So the retry re-enabled thinking, kimi
            # rambled to 46,801 chars, hit our max_tokens ceiling (finish_reason=length), came back
            # as truncated non-JSON, and burned 164s of a 175s slice for nothing. The blanket fix
            # for one 400 CAUSED the next failure.
            #
            # AND THE CONSTANT WAS STALE: the body said "temperature must be 0.6 for this model"
            # while MODEL_PARAMS hardcoded 1.0 (the value the API demanded last time we looked).
            # A number the server publishes on every rejection must be READ, not memorised — that
            # is the difference between fixing this once and fixing it every time DO retunes a model.
            _fix = []
            _m = re.search(r"temperature must be ([0-9.]+)", _b or "")
            if _m:
                try:
                    payload["temperature"] = float(_m.group(1)); _fix.append("temperature=" + _m.group(1))
                except ValueError:
                    pass
            # WHEN THE SERVER NAMES max_tokens, DROP max_tokens - not response_format.
            # The 2026-08-14 body was "max_tokens cannot be set when response_format type is
            # 'json_object'; omit max token limits for structured outputs to avoid truncated JSON".
            # Both fields are named, so the old `if "response_format" in body` matched first and
            # removed the JSON contract while KEEPING the ceiling the server had just objected to -
            # the exact inverse of the advice, and it re-creates the truncated-mid-JSON failure.
            # Same doctrine as the ecolines fix: repair WHAT THE SERVER NAMED, in the direction it
            # named it, never whichever field the first regex happens to hit.
            if "max_tokens" in (_b or ""):
                payload.pop("max_tokens", None); _fix.append("dropped max_tokens (kept JSON mode)")
            elif "response_format" in (_b or "") or not _fix:
                payload.pop("response_format", None); _fix.append("dropped response_format")
            # `chat_template_kwargs` is dropped ONLY if the server names it. Never speculatively:
            # removing it turns thinking back on, which is a far worse failure than a 400.
            if "chat_template_kwargs" in (_b or "") or "enable_thinking" in (_b or ""):
                payload.pop("chat_template_kwargs", None); _fix.append("dropped chat_template_kwargs")
            print("[warn] enrich %s: retrying with %s" % (model, ", ".join(_fix) or "no change"),
                  file=sys.stderr)
            d = _post(payload, timeout)
        else:
            raise                                   # 429/5xx must reach the retry/failover logic
    msg = d["choices"][0]["message"]
    txt = msg.get("content") or msg.get("reasoning_content") or ""
    # finish_reason == "length" means WE cut the model off at max_tokens — the JSON is then
    # truncated mid-string and the parser reports a misleading "bad response". rightmart.de:
    # deepseek-3.2 died on JSONDecodeError at char 30117 (~7.5k tokens) against max_tokens=6500.
    # Say which it is, so the next person raises the ceiling instead of blaming the model.
    _fin = d["choices"][0].get("finish_reason")
    if _fin == "length":
        print("[warn] enrich %s: OUTPUT TRUNCATED at max_tokens=%d (finish_reason=length, %d chars). "
              "This is OUR ceiling, not a model fault — raise max_tokens or send fewer findings."
              % (model, payload.get("max_tokens", 0), len(txt)), file=sys.stderr)
    globals()["_LAST_FINISH"] = _fin
    # post-mortem log the raw model output so failures are debuggable (the "logs" to check)
    try:
        with open(os.path.join(os.environ.get("OUTDIR", "/root/work"), "enrich_last.json"), "w") as fh:
            json.dump({"model": model, "finish": d["choices"][0].get("finish_reason"),
                       "usage": d.get("usage", {}), "raw": txt[:8000]}, fh, indent=2)
    except Exception: pass
    return txt, d.get("usage", {}) or {}

def _normalise(j):
    """Make `findings` a flat list of DICTS, whatever the model nested.

    The Bezeq failure was NOT the top level (already fixed) — it was the entries: every consumer does
    `x.get("id")`, so ONE list inside findings raises AttributeError and throws away the whole answer.
    Models legitimately emit `findings: [[{...},{...}]]` (a nested batch) or a stray string. Flatten
    one level, keep the dicts, drop the rest — and say what was dropped instead of dying.
    """
    f = j.get("findings")
    if isinstance(f, list):
        flat, dropped = [], 0
        for x in f:
            if isinstance(x, dict):
                flat.append(x)
            elif isinstance(x, list):                       # nested batch -> flatten one level
                flat.extend([y for y in x if isinstance(y, dict)])
                dropped += sum(1 for y in x if not isinstance(y, dict))
            else:
                dropped += 1
        if dropped:
            print("[warn] enrich: dropped %d non-object entr(y/ies) from findings" % dropped,
                  file=sys.stderr)
        j["findings"] = flat
    elif f is not None and not isinstance(f, list):
        j["findings"] = []
    for k in ("strengths", "colt_mitigation"):
        if k in j and not isinstance(j[k], list):
            j[k] = []
    return j


def _contract_ok(j, tokens_out=None):
    """Did the model actually ANSWER, or just emit a well-formed nothing?

    gemma-4-31B-it returned `{}` in 4s (tokens_out=3). It parsed fine, so the tolerant parser marked
    the run "ok", set qwen_used=true, charged $0.0043 and built a DELTAS deck with no deltas — a
    SILENT quality failure, strictly worse than an honest fallback. Tolerate any SHAPE; never
    tolerate an EMPTY answer. If it is empty we raise, which fails over to the next model.
    """
    if not isinstance(j, dict):
        return False, "not a JSON object"
    if tokens_out is not None and int(tokens_out) < 50:
        return False, "model emitted only %s completion tokens (empty answer)" % tokens_out
    has_summary = bool(str(j.get("exec_summary") or "").strip())
    findings = [x for x in (j.get("findings") or []) if isinstance(x, dict) and x.get("id")]
    if not has_summary and not findings:
        return False, "no exec_summary and no usable findings (keys=%s)" % sorted(j)[:6]
    return True, ""


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
        return _normalise(obj)
    if isinstance(obj, list):
        # [ {exec_summary:..., findings:[...]} ]  -> unwrap the first dict that looks like ours
        for item in obj:
            if isinstance(item, dict) and ("exec_summary" in item or "findings" in item):
                return _normalise(item)
        # [ {id:C1,...}, {id:C2,...} ] -> a bare findings array; wrap it into the contract
        if obj and all(isinstance(x, dict) for x in obj) and any("id" in x for x in obj):
            return _normalise({"findings": obj})
        for item in obj:                       # last resort: any dict at all
            if isinstance(item, dict):
                return _normalise(item)
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
        if not isinstance(x, dict): continue
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
    prompt = PROMPT % (_bible(), lang_block(lang),
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
        # SIZE THE REQUEST TO THE SLICE. A flat max_tokens=11000 needs ~110s at the measured rate,
        # while the floor above hands out 60s — so on lotto24.de models 3 and 4 were each issued a
        # request that could not physically finish, and each burned its whole 60s timing out. Two of
        # the four "model failures" in that run were arithmetic, not models.
        _mt = feasible_max_tokens(per_call)
        if _mt < 11000:
            print("[enrich] %s: %ds slice -> max_tokens %d (a full 11000-token answer needs ~%ds)"
                  % (model, per_call, _mt, 11000 // max(1, TOK_PER_S)), file=sys.stderr)
        try:
            t = time.time()
            content, usage = _call(prompt, model, per_call, max_tokens=_mt); j = _json(content)
            ti = int(usage.get("prompt_tokens", 0)); to = int(usage.get("completion_tokens", 0))
            _ok, _why_bad = _contract_ok(j, to)
            if not _ok:
                raise ValueError("empty/contract-invalid answer: %s" % _why_bad)
            cost = round((ti + to) / 1e6 * _price(model), 6); ms = int((time.time() - t) * 1000)
            _bad_cves = _audit_cves(fj, j)          # strip hallucinated CVE ids before they reach a slide
            def _nid(v): return "".join(ch for ch in str(v).upper() if ch.isalnum())
            by_id = {_nid(x.get("id")): x for x in (j.get("findings") or [])
                     if isinstance(x, dict)}
            for f in fj["findings"]:
                x = by_id.get(_nid(f["id"]))
                if not x:
                    f.setdefault("_enriched", False)
                    continue
                # MARK IT. Without this flag nothing downstream can tell LLM prose from the canned
                # TEMPLATES fallback — which is why "coverage 0%" fired a pointless map-reduce
                # top-up on a run where deepseek-3.2 had in fact rewritten every finding.
                f["_enriched"] = True
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
            if isinstance(e, (AttributeError, TypeError, ValueError, KeyError)):
                # a PARSE failure, not a network one — record the shape so the next fix is not a guess
                try:
                    _shape = json.JSONDecoder().raw_decode(content[content.find("{") if content.find("{") >= 0 else content.find("["):])[0]
                    _desc = type(_shape).__name__
                    if isinstance(_shape, dict):
                        _desc += " keys=%s findings=%s" % (
                            sorted(_shape)[:6],
                            [type(x).__name__ for x in (_shape.get("findings") or [])][:6])
                    print("[warn] enrich %s: unusable answer shape -> %s (raw in enrich_last.json)"
                          % (model, _desc), file=sys.stderr)
                except Exception:
                    pass
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
                  else "returned an EMPTY answer" if "empty/contract-invalid" in last
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
