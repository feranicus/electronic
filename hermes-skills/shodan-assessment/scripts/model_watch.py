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
def _key():
    """The inference key, delegated to enrich.resolve_key() so there is exactly ONE lookup.

    This function used to carry its own copy of the search. The copy made the CATALOG call work on
    the operator's PC while every PROBE still returned HTTP 401, because the probe runs through
    enrich._call and enrich had the old environment-only lookup. One secret, two homes, and the
    newer home won in one of the two places that mattered. The env-only fallback below exists for
    the case where enrich cannot be imported at all; it is narrower than the real resolver on
    purpose, and it says so rather than pretending to be the same check.
    """
    try:
        sys.path.insert(0, HERE)
        import enrich as _E
        return _E.resolve_key()
    except Exception:
        return os.environ.get("OPENAI_API_KEY") or os.environ.get("DO_INFERENCE_KEY") or ""


KEY = _key()

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
# Not text->JSON models: embeddings, rerankers, routers, image/audio/video.
#
# THE FIRST REAL BAKE-OFF PROBED FIVE EMBEDDING MODELS AND FOUR ROUTERS. `all-mini-lm-l6-v2`,
# `bge-m3`, `e5-large-v2`, `gte-large-en-v1.5` and `multi-qa-mpnet-base-dot-v1` are sentence
# encoders; `router:general` and its three siblings are not models at all. None of them says
# "embed" in its id, which is the only thing this pattern looked for, so all nine were sent the
# full enrichment prompt and reported in a table headed CONTRACT. A filter that recognises only
# the word for a thing, and not the names the thing actually has, is not a filter.
NON_TEXT_RE = re.compile(
    r"(embed|rerank|whisper|tts|stt|image|sdxl|flux|diffusion|video|wan\d|audio"
    r"|^router:|^all-mini|^bge-|^e5-|^gte-|mpnet|sentence|-encoder\b)", re.I)

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


OWNERS = {}          # model id -> owned_by, filled by catalog(). Empty until the call succeeds.


def catalog():
    """[model ids] this key can see, or [] if the call fails (fails closed - never guesses).

    SIDE EFFECT, DELIBERATE AND NAMED: fills OWNERS with the `owned_by` field the API already
    returns and this function used to throw away. The chain's whole reason for existing is FOUR
    VENDORS WITH NO SHARED FAILURE DOMAIN, so "which vendor is this" is the single most important
    property of a candidate, and deriving it from the id string is guesswork: `mimo-v2.5-pro` is
    Xiaomi and `reflection-beam` is Reflection AI, neither of which the id says. Ask the API.
    """
    if not KEY:
        return [], "no OPENAI_API_KEY in the environment"
    try:
        req = urllib.request.Request(BASE + "/models",
                                     headers={"Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8"))
        rows = [m for m in (j.get("data") or []) if m.get("id")]
        OWNERS.clear()
        for m in rows:
            OWNERS[str(m["id"])] = str(m.get("owned_by") or "?")
        return sorted({str(m["id"]) for m in rows}), ""
    except Exception as e:
        return [], "%s: %s" % (type(e).__name__, e)


# THE API'S owned_by IS THE GATEWAY, NOT THE MODEL VENDOR.
#
# This was built on `owned_by` on the reasoning that asking the API beats parsing a string. The
# first real run printed "Vendors still live in the chain: digitalocean" and a VENDOR column that
# said `digitalocean` on every row, because DigitalOcean's catalog reports itself as the owner of
# everything it serves. A column that renders the same value whatever the input is templated
# output, not a measurement, and it was about to be the column used to decide whether a
# replacement restores the four-vendor property the chain exists for.
#
# So the id prefix it is, with the table written down rather than guessed per call. owned_by is
# kept only as a fallback for an id this table does not know, and the gateway's own name is
# rejected there because it answers a different question.
VENDOR_BY_PREFIX = (
    ("deepseek", "deepseek"), ("llama", "meta"), ("gemma", "google"), ("kimi", "moonshot"),
    ("mistral", "mistral"), ("glm", "z.ai"), ("minimax", "minimax"), ("qwen", "alibaba"),
    ("mimo", "xiaomi"), ("nemotron", "nvidia"), ("nvidia", "nvidia"), ("reflection", "reflection"),
    ("arcee", "arcee"), ("openai", "openai"), ("anthropic", "anthropic"), ("typesafe", "typesafe"),
)


def vendor(mid):
    """The MODEL vendor for this id, or '?' when nothing reliable says.

    '?' is a real answer here. A candidate whose vendor is unknown cannot be counted toward vendor
    diversity, and saying so is the point: the chain exists to survive one vendor's outage.
    """
    s = (mid or "").lower()
    for pref, name in VENDOR_BY_PREFIX:
        if s.startswith(pref):
            return name
    owner = (OWNERS.get(mid) or "").strip().lower()
    if owner and owner not in ("digitalocean", "do", "?", ""):
        return owner
    return "?"


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

# THE CARVE-OUT, AND IT COST US EVERY BAKE-OFF WE HAVE EVER RUN.
#
# The word in the rule above is COMMERCIAL. `openai-gpt-oss-120b` and `openai-gpt-oss-20b` are
# OpenAI's OPEN-WEIGHTS models, and they start with "openai-gpt-", so the prefix that was widened
# to catch gpt-6-1-sol swallowed them too. They have therefore never been probed, not once, and
# every run printed them as NOT-ENTITLED on evidence that was never gathered. A check that reports
# a conclusion it did not measure is the defect this file exists to prevent.
#
# DigitalOcean's own Inference Limits page is explicit: "Tier 1 and Tier 2 do not have access to
# any Anthropic models and OpenAI models (EXCEPT gpt-oss-120b and gpt-oss-20b)." So the one
# OpenAI family this account is documented to be allowed to call is precisely the family our own
# guard was hiding.
#
# enrich.not_chainable() already had this carve-out ("openai-gpt-" and "oss" not in s). Two homes
# for one rule, and they disagreed: the chain would have accepted gpt-oss while the probe refused
# to measure it.
ENTITLED_EXCEPTIONS = ("openai-gpt-oss",)


def entitled(mid):
    """(ok, why). False for a vendor prefix this account has been MEASURED to be refused by."""
    if os.environ.get("MODEL_WATCH_PROBE_ALL_VENDORS", "").strip() in ("1", "true", "yes"):
        return True, ""
    m = str(mid or "")
    for e in ENTITLED_EXCEPTIONS:
        if m.startswith(e):
            return True, ""
    for p in UNENTITLED_PREFIXES:
        if m.startswith(p):
            return False, ("not entitled on this account (%s* returns HTTP 403; measured, "
                           "see CLAUDE.md) - not a contract failure" % p)
    return True, ""


def probe(mid, timeout=60, _retried=False):
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
        # READ THE SIGNATURE. enrich._call returns (text, usage_dict), NOT a string. Passing the
        # tuple to _json() raised "'tuple' object has no attribute 'find'" AFTER a perfectly good
        # 42 second call to deepseek-3.2, and the control then reported that crash as a verdict
        # about the credential. Seventeen times in this workstream a helper has returned a
        # different shape than assumed; this is eighteen.
        raw, usage = E._call(E.PROMPT + "\n\nRAW FINDINGS:\n" + json.dumps(fj)[:6000],
                             model=mid, timeout=timeout)
        ms = int((time.time() - t0) * 1000)
        j = E._json(raw)
        ok = isinstance(j, dict) and bool(j.get("exec_summary") or j.get("findings"))
        return {"ok": ok, "ms": ms, "err": "" if ok else "contract-invalid",
                "tokens_out": int((usage or {}).get("completion_tokens") or 0)
                              or len(str(raw)) // 4}
    except Exception as e:
        # AN AUTH FAILURE IS NOT A CONTRACT FAILURE, AND THE DIFFERENCE IS THE WHOLE VERDICT.
        # The first real bake-off printed nineteen rows of `FAIL ... HTTP Error 401: Unauthorized`
        # under a column headed CONTRACT, which reads as "these models cannot do the job" when the
        # truth was "we never authenticated". The 403 case already had this distinction and the
        # 401 case did not. Same rule as every other diagnostic here: report what was measured,
        # and never let an environment fault be rendered as a property of the subject.
        _code = getattr(e, "code", None)
        # 5xx AND 529 ARE TRANSIENT. DigitalOcean answers an overloaded model with 529, and the
        # control probe took that as a hard failure, aborted the whole bake-off and told the
        # operator to go fix probe(). An overloaded upstream says nothing about the model, the
        # key or this code; it says try again. Retry ONCE, because a probe is a read and reads
        # may retry (unlike anything that creates or deploys).
        if _code == 529 or (isinstance(_code, int) and 500 <= _code < 600):
            if not _retried:
                time.sleep(2.0)
                return probe(mid, timeout, _retried=True)
            return {"ok": None, "ms": int((time.time() - t0) * 1000), "transient": True,
                    "err": "HTTP %d twice: the model is overloaded or the gateway is unwell. "
                           "Transient. Nothing here is a verdict." % _code,
                    "tokens_out": 0}
        if _code in (401, 403):
            return {"ok": None, "ms": int((time.time() - t0) * 1000), "auth": True,
                    "err": ("HTTP %d: not permitted. DO's 403 body is identical for "
                            "key-scope, provider-terms and tier causes, so this says nothing "
                            "about the model itself." % _code),
                    "tokens_out": 0}
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
    # THE BAKE-OFF. --probe-all measures everything INCLUDING what we already run, then cuts the
    # list to an arbitrary alphabetical six. When two chain slots die on a published date and have
    # to be replaced against a deadline, the question is narrower and the cap is actively harmful:
    # measure every model we do NOT currently use, uncapped, and rank it.
    ap.add_argument("--unused", action="store_true",
                    help="probe every catalog model that is NOT in the current chain, uncapped")
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
    if a.unused and not asked:
        try:
            import enrich as _E
            _chain = list(_E.MODELS)
        except Exception as _e:
            print("[model-watch] cannot read the current chain (%s); --unused needs it to know "
                  "what 'unused' means" % type(_e).__name__)
            return 2
        asked = [m for m in ids if m not in _chain and not NON_TEXT_RE.search(m)]
        print("\n[model-watch] BAKE-OFF: %d catalog models, %d in the chain, %d to measure"
              % (len(ids), len(_chain), len(asked)))
        print("[model-watch] chain today: %s" % ", ".join(
            "%s%s" % (m, "" if m in ids else "  <-- NOT IN CATALOG, this slot is dead") for m in _chain))
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

    # THE CONTROL. Probe a model we KNOW works before measuring any candidate.
    #
    # The 10 November run reported ten candidates as AUTH/403 and nothing about why. The chain
    # models were excluded from the bake-off by definition, so the one measurement that
    # distinguishes "these ten models are unavailable to us" from "this credential cannot invoke
    # anything new" was never taken. A test whose fixture is unproven measures the fixture
    # (class 12), and a check that cannot see its subject must not answer (class 1).
    #
    # A DigitalOcean model access key is scoped to a model list AT CREATION and the scope cannot
    # be edited afterwards, so "works for the old models, 403 for every new one" is the expected
    # shape of a key that predates them. The control is what turns that from a guess into a
    # reading.
    _control = None
    if todo and not a.no_probe:
        try:
            import enrich as _E
            _control = next((m for m in _E.MODELS if m in ids), None)
        except Exception:
            _control = None
    if _control:
        _cr = probe(_control, a.timeout)
        _ok = bool(_cr.get("ok"))
        print("\n  CONTROL  %-26s %-9s %sms   (a model this chain already runs in production)"
              % (_control, "ok" if _ok else ("AUTH" if _cr.get("auth") else "FAIL"), _cr["ms"]))
        out["control"] = {"model": _control, "ok": _ok, "ms": _cr["ms"], "err": _cr["err"]}
        if not _ok:
            print("\n[model-watch] !! THE CONTROL FAILED, so this run can say NOTHING about any "
                  "candidate.")
            print("   %s is in the live chain and serves production. Result: %s"
                  % (_control, _cr["err"][:140]))
            # NAME ONLY THE CAUSE THE EVIDENCE SUPPORTS. The first version of this block printed
            # "the fault is in THIS RUN'S CREDENTIAL" for ANY control failure. It then said
            # exactly that about a TypeError in this file's own probe(), sending the reader to the
            # DigitalOcean console to fix a bug that lived here. A diagnostic that reports its own
            # blindness as a finding about the system is the defect this file exists to prevent.
            if _cr.get("auth"):
                print("   This was an HTTP refusal, so the cause is entitlement, not the model.")
                print("   A DigitalOcean model access key is scoped to a model list when it is")
                print("   created and the scope CANNOT be edited afterwards. Check it at")
                print("   cloud.digitalocean.com/model-studio/manage-keys (hover Models).")
            elif _cr.get("transient"):
                print("   The upstream was OVERLOADED (HTTP 529/5xx), twice. This says nothing")
                print("   about the key, the account or any model. Re-run in a few minutes.")
            else:
                print("   This was NOT an HTTP refusal, so it says nothing about the key or the")
                print("   account. The probe harness itself failed. Fix model_watch.probe()")
                print("   before reading anything else from this run.")
            print("   Nothing was measured and nothing was changed.")
            if a.json:
                print(json.dumps(out, indent=2))
            return 3
        print("  CONTROL passed, so a 403 below is a statement about that model, not about the key.")

    if todo and not a.no_probe:
        print("\n  %-34s %-9s %-8s %-14s %s" % ("MODEL", "CONTRACT", "ms", "$/1M in,out", "note"))
        for m in todo:
            r = probe(m, a.timeout)
            print("  %-34s %-9s %-8s %-14s %s"
                  % (m, "ok" if r["ok"] else ("AUTH" if r.get("auth") else
                                     ("BUSY" if r.get("transient") else "FAIL")),
                     r["ms"], _price(m), r["err"][:38]))
            out["probed"].append({"model": m,
                                  "verdict": "ok" if r["ok"] else
                                             ("auth" if r.get("auth") else
                                              ("busy" if r.get("transient") else "fail")),
                                  "ms": r["ms"], "price": _price(m), "err": r["err"]})
        _auth = [p for p in out["probed"] if p.get("verdict") == "auth"]
        _tried = [p for p in out["probed"] if p.get("verdict") in ("ok", "fail", "auth")]
        if _auth and len(_auth) == len(_tried):
            print("\n[model-watch] !! EVERY probe failed to authenticate (%d of %d). That is ONE "
                  "fault in this run's credentials, not %d verdicts about %d models. Nothing here "
                  "says anything about any model. Check the key the PROBE uses: it travels through "
                  "enrich.resolve_key(), not through this file."
                  % (len(_auth), len(_tried), len(_auth), len(_auth)))
        good = [p for p in out["probed"] if p.get("verdict") == "ok"]
        if good:
            good.sort(key=lambda p: p.get("ms", 1e9))
            print("\n[model-watch] contract-valid new candidate(s), fastest first: %s"
                  % ", ".join(p["model"] for p in good))
            print("[model-watch] to adopt, re-run the artifact bake-off FIRST "
                  "(python compare_models.py --lang de), then: python set_secret.py ENRICH_MODELS")

        if a.unused:
            # THE VERDICT TABLE. Fastest first, with the VENDOR beside it, because a replacement
            # that is quick and cheap but shares a vendor with the head does not restore the
            # property the chain exists for. Printed at the end so it is the last thing on screen
            # after a long run, and it states the comparison rather than a bare ranking.
            try:
                import enrich as _E
                _chain = list(_E.MODELS)
            except Exception:
                _chain = []
            _live = [m for m in _chain if m in ids]
            _have = {vendor(m) for m in _live}
            print("\n" + "=" * 94)
            print("  BAKE-OFF RESULT  (contract-valid only, fastest first)")
            print("=" * 94)
            print("  %-30s %-14s %-8s %-14s %s"
                  % ("MODEL", "VENDOR", "ms", "$/1M in,out", "RESTORES VENDOR DIVERSITY?"))
            if not good:
                print("  none of the %d measured models returned a contract-valid answer." % len(todo))
            for p in good:
                v = vendor(p["model"])
                new = v not in _have and v != "?"
                print("  %-30s %-14s %-8s %-14s %s"
                      % (p["model"][:30], v[:14], p.get("ms", "?"), _price(p["model"]),
                         "YES, new vendor" if new else
                         ("no, %s is already in the chain" % v if v != "?" else "unknown vendor")))
            print("")
            print("  Vendors still live in the chain: %s"
                  % (", ".join(sorted(_have)) if _have else "NONE, every slot is dead"))
            _dead = [m for m in _chain if m not in ids]
            if _dead:
                print("  DEAD SLOTS IN enrich._FALLBACKS RIGHT NOW: %s" % ", ".join(_dead))
                print("  Every assessment is spending one failed round trip per dead slot.")
            print("  Nothing has been changed. Adopt with: python set_secret.py ENRICH_MODELS")
            print("=" * 94)

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
