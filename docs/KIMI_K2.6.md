# kimi-k2.6 — how we call it, what it requires, and what it is for

**Vendor:** Moonshot AI · **Reached via:** DigitalOcean serverless inference
(`https://inference.do-ai.run/v1`, OpenAI-compatible `/chat/completions`)
**Status in this system:** fourth vendor. Auditor on the review panel, last in the enrichment chain.

Every fact in this document was read out of the code, not remembered. Line references are to
`hermes-skills/shodan-assessment/scripts/enrich.py` unless stated otherwise.

---

## 1. The one thing to know first

**Kimi is not a normal model on this endpoint. It rejects three of the four parameters we send to
every other model.** It spent three separate review rounds being written off as "broken" or
"unavailable" while it was healthy and entitled the whole time — because we were discarding the
HTTP 400 body that told us exactly what it wanted.

Verbatim, from the API, on three different occasions:

```
HTTP 400 {"message":"temperature must be 1 for this model","type":"invalid_request_error"}
HTTP 400  response_format type 'json_object' is not supported for this model
HTTP 400 {"message":"temperature must be 0.6 for this model","type":"invalid_request_error"}
```

Note the first and third. **The required temperature CHANGED under us**, from 1.0 to 0.6. That is
why the constant is now a fast path and the *parser* is what keeps us correct.

---

## 2. Required parameters

Encoded in `enrich.MODEL_PARAMS`, matched on the **id prefix** `kimi` (so `kimi-k2.5`, `kimi-k2.6`
and any future `kimi-*` inherit it):

```python
MODEL_PARAMS = {
    "kimi": {"temperature": 0.6, "_drop": ["response_format"]},
}
```

| Parameter | Every other model | Kimi | Why |
|---|---|---|---|
| `temperature` | `0.35` | **`0.6`** | API rejects anything else. Value is read from the 400 body if it changes again. |
| `response_format` | `{"type":"json_object"}` | **dropped** | *"not supported for this model"*. Dropped pre-emptively, so we never pay the round trip. |
| `chat_template_kwargs` | `{"enable_thinking": false}` | **same, and load-bearing** | Kimi is a reasoning model. Without this it emits chain-of-thought until it hits the ceiling. |
| `max_tokens` | dropped when `response_format` is set (gateway rule) | **kept** | Kimi never sends `response_format`, so it keeps its feasibility ceiling. |

`_model_params(model)` returns a **copy** (`dict(over)`) so a caller mutating the payload cannot
corrupt the table for the next call.

### The `enable_thinking` trap — do not "fix" it

The 400 handler used to blanket-pop `chat_template_kwargs`. On the ecolines.net run that produced:

```
400 (temperature) → retry with thinking RE-ENABLED → 46,801 characters
→ finish_reason=length → truncated non-JSON → 164 seconds of a 175s slice, zero output
```

The blanket remedy for one 400 **caused** the next failure and starved llama-4-maverick down to
118s. `chat_template_kwargs` is now dropped **only if the server names it**:

```python
if "chat_template_kwargs" in (_b or "") or "enable_thinking" in (_b or ""):
    payload.pop("chat_template_kwargs", None)
```

**Rule: when an API rejects a request, repair what it named, in the direction it named it.** Never
strip fields until something works — that is how you disable a safeguard you did not know you had.

---

## 3. How we call it

There is exactly one entry point. Everything else goes through it:

```python
import enrich as E
raw, usage = E._call(prompt, model="kimi-k2.6", max_tokens=1800, timeout=90)
```

`_call` returns a **two-tuple** `(text, usage)`. Catching it in one name is a real bug we shipped
once — `enrich_parallel._call_shard` did `raw = E._call(prompt)`, handed the tuple to `_json()`,
and every shard died with `'tuple' object has no attribute 'find'` while the log blamed a model.

The four production call sites:

| Where | Role | Call |
|---|---|---|
| `deploy/stagegate/quorum.py` | **auditor** on the staging panel | `E._call(prompt, model=m, max_tokens=1800, timeout=90)` |
| `webapp/backend/app/shield_panel.py` | reviewer of shield decisions | `E._call(PROMPT % (...), model=m, max_tokens=900, timeout=90)` |
| `webapp/backend/app/release_notes.py` | release-note writer | `E._call(PROMPT % facts, model=m, max_tokens=900, timeout=90)` |
| `enrich._FALLBACKS` | **last** in the deck-prose chain | via `_chain()`, budget-sliced |

```python
# deploy/stagegate/quorum.py
SOLDIERS = ["deepseek-3.2", "llama-4-maverick"]
AUDITORS = ["gemma-4-31B-it", "kimi-k2.6"]

# shield_panel.py and release_notes.py
MODELS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]

# enrich.py
_FALLBACKS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]
```

A test asserts the quorum list and the release-notes list are **identical**, so they cannot drift.

### Vendor identity

`audit_fp._vendor()` maps `kimi` → `moonshot`, so the FP auditor can guarantee a **different
vendor** than the model that wrote the deck. A 429 or a blind spot is provider-wide; deepseek
auditing deepseek is not an audit.

---

## 4. Why it is LAST in the enrichment chain

This reverses an earlier decision that was preference, not measurement. From `enrich.py`:

> A model that fails is cheap; a model that fails **slowly** starves the ones behind it.

On ecolines.net kimi consumed **164 seconds of a 175-second head slice** and returned garbage. The
head of the chain gets 55% of the enrichment budget (`share = 0.55 if models_left > 1`), so its
failure left deepseek 112s and the last two 60s each — less than an 11,000-token answer can
physically take. Four "model timeouts" in that run, two of which were pure arithmetic.

It stays in the chain because **a fourth vendor is a real hedge against a provider-wide 429**. It
just can no longer eat the budget ahead of a model measured to work on the real prompt
(deepseek-3.2: 25.0s, contract-valid, good German, via `compare_models.py`).

To put it back at the head for an experiment, one env var — no code change:

```
ENRICH_MODELS="kimi-k2.6,deepseek-3.2,llama-4-maverick,gemma-4-31B-it"
```

⚠️ `ENRICH_MODEL` (singular, legacy) is **prepended as the chain head** by `_chain()`. It has
silently reordered the chain before. `ship.py` deletes both keys from the droplet `.env`.

---

## 5. Commands

### Probe it directly

```bash
# does it exist in the live catalog, and does it answer the real contract?
docker exec colt-web python3 /opt/shodan-skill/scripts/model_probe.py --model kimi-k2.6

# through the REAL enrich path (applies MODEL_PARAMS) rather than a raw POST
docker exec colt-web python3 /opt/shodan-skill/scripts/model_probe.py --model kimi-k2.6 --via-enrich

# existence only, zero tokens
docker exec colt-web python3 /opt/shodan-skill/scripts/model_probe.py --existence
```

`--via-enrich` exists **because kimi was written off twice by a raw probe.** The raw probe sends
`response_format` and `temperature=0.35` and gets a 400; production does neither. A probe that does
not reproduce the production path proves nothing about production.

### Read what it actually returned

```bash
python check_enrich.py                      # reads <jobdir>/enrich_last.json off the droplet
```

`_call` writes `enrich_last.json` on every call: model, `finish_reason`, usage, and the first 8,000
characters of the raw answer. **`finish_reason == "length"` is our ceiling, not a model fault** —
raise `max_tokens` or send fewer findings. Stop guessing at shapes; read the file.

### Run the panels

```bash
# staging review panel (kimi = auditor). Reads evidence JSON on stdin.
docker exec -i colt-web python3 /opt/stagegate/quorum.py < evidence.json

# shield tuning panel, print only
docker exec colt-web python3 -m app.shield_panel --print

# release notes (4 models, Gmail API + Telegram)
docker exec colt-web python3 -m app.release_notes
```

All of these run **inside `colt-web`** because `OPENAI_API_KEY` lives on the droplet and
deliberately never enters git or the operator's PC.

### Compare it on the real workload

```bash
python compare_models.py --lang de
```

Runs the same `findings.json` through each model with the real 10,640-character prompt.
**Never judge from a toy probe: latency ranking inverts with prompt size** (maverick was 3.3s on a
toy prompt and 44.6s on the real one).

---

## 6. Failure modes and what they mean

| Symptom | Cause | Action |
|---|---|---|
| `HTTP 400 temperature must be N` | DO retuned the model | None — `_call` reads N from the body and re-sends. Update `MODEL_PARAMS` to skip the round trip. |
| `HTTP 400 response_format ... not supported` | `_drop` was removed | Restore `"_drop": ["response_format"]`. |
| 46k characters, `finish_reason=length` | thinking was re-enabled | `chat_template_kwargs` was dropped speculatively. Do not. |
| `Unterminated string starting at: line 1 column 2` | **our** `max_tokens` truncated it | Raise the ceiling. This is not "the model did not answer". |
| `ACCEPTED, 0 chars back` | ceiling consumed entirely by reasoning | Ceiling too small (seen at `max_tokens=300`). Production sends 900–1800 with thinking off. |
| Slow failure eating a whole slice | it is at the head of the chain | Put it back at the end. |

The truncation case is worth stressing: `quorum._ask` used to send **900 tokens** while the panel's
own contract permits 3 reasons + 3 risks at 400 chars each plus two 500-char fields — roughly
**1,020 tokens of content before any JSON structure**. A reviewer that answered *fully* was
guaranteed to be cut off, and the failure was reported as *"did not answer"*. Kimi and gemma both
acquired reputations for being erratic that way. `quorum` now sends 1,800 and the error message
names us:

```python
if "Unterminated" in why or "Expecting" in why or "char 1" in why:
    why = ("answer was CUT OFF mid-JSON — that is our max_tokens ceiling, not the model "
           "(raise it in quorum._ask): %s" % why)
```

---

## 7. Governance — it advises, it never decides

Kimi has **no authority over any deploy, block or threshold.**

- **Staging gate:** deterministic checks decide GO/NO-GO. The panel supplies reasoning and risk.
  A 429 must never block a good release; an agreeable model must never wave through a dead
  container. Both directions are asserted by tests.
- **The one exception, and it is narrow:** when **2 or more reviewers dissent** (no-go or unsure)
  **and at least one is a hard no-go**, against a *green* gate, the ship **halts** and requires
  `OVERRIDE_PANEL=1`. That pattern has repeatedly meant *a check is lying*, and it must reach a
  human before production, not in a note afterwards.
- **Shield tuning:** it may propose values for six integers only, inside bounds committed in
  `shield.BOUNDS` and clamped on every **read**. Quorum of 3 of 4 on the *direction*; the applied
  value is the **median**, so one bold model cannot drag the result; steps over 25% refused. It
  cannot block or unblock an address, change the bounds, the blast cap, the allowlist or the kill
  switch.
- **It is never in the request path.** A model call is 300 ms to 60 s. In front of a request that
  *is* a denial of service, that is the outage. The shield decides inline in pure arithmetic; the
  panel reviews out of band.

---

## 8. Track record — read this before trusting or dismissing it

Kimi is the **sharpest structural reviewer on the panel and the most confidently wrong one.** Both
halves are load-bearing.

### Where it was right (and each became code)

- Identified a disabled admin API **from the hash alone** — recognised `d41d8cd98f00` as the md5 of
  the empty string. Best single catch the panel has produced.
- *"No check verifies admin API accessibility or its authentication."* Every drift and roster check
  reads `http://127.0.0.1:2019/config/` and the deploy **writes** through it — an endpoint that can
  replace the running config for every domain on the box, with no authentication of its own.
  Nothing asserted it was still loopback-only. → `agent.py admin`.
- *"`config_change_propagates` is broken by construction"* — and it was: `agent.py assemble`
  without `--apply` writes nothing and reloads nothing, so the assertion could never pass.
- *"A vhost that silently APPEARS should also be a failure."* → surplus-vhost warning in the roster.
- *"config_reread only proves timing."* → renamed `config_write_ordering`, then
  `guard_write_path_reloads`. A name is read far more often than a detail string.
- Post-reboot check details truncated — flagged **three consecutive runs**, right every time.
- *"The Caddyfile on disk is never compared to the repo."* Hop checks prove *consistency*; nothing
  proved *authenticity*. → the TAMPER comparison against committed blocks.

### Where it was wrong

- Claimed **3–4 times** that `config_drift` hash-compares `caddy adapt` against the admin API. It
  compares **sets** of hostnames, terminal handlers and path matchers; the hash method was deleted
  on 7 Aug. **This one is our defect, not its.** The ARCH briefing explained why the hash method
  was wrong and never said what the check actually does, so a reviewer reasoning from that map
  lands on the removed method every time. → ARCH now states, per check, exactly what is measured.
- Invented a Kubernetes manifest, an engine job queue and an `ENGINE_MODE` env var for a system
  that has none of them.
- Wrong that `localhost` inside a container is reachable from another container on the same Docker
  network — each container has its own network namespace. *(The constructive half of that note
  still landed: a check that **reasons** about its subject is weaker than one that **reproduces**
  it, so the admin probe now really dials the bridge IP from a different container.)*
- Inverted `config_reread` ("started AFTER the write means stale") — the opposite of the truth.
- Read `vhost_roster OK all 1 expected domain(s) are served (2 host(s) total)` as a logic defect.
  The surplus warning had existed since it asked for it; the **output** simply never explained the
  exempted `www.` variant. Our defect again.

**The pattern:** strong reasoning *from* evidence in front of it, unreliable when extrapolating to
architecture it cannot see. So: **feed it more evidence, never more authority.** And if it makes
the same wrong call three runs running, fix the briefing — that is a hole in our map, not a flaw in
the reviewer.

---

## 9. Tests that pin this behaviour

`hermes-skills/shodan-assessment/scripts/test_recall.py` — §19, §21, §25:

```
kimi is sent temperature=0.6 and NO response_format (the API rejects both)
kimi is sent enable_thinking=False - it is a reasoning model and will otherwise ramble
kimi is LAST - it burned 164s of a 175s slice on ecolines.net and starved the next model
kimi keeps its feasibility ceiling - it never sends response_format
the retry re-sends the temperature the SERVER named
chat_template_kwargs is dropped ONLY when the server names it
```

`tests/test_gate_integrity.py` asserts the quorum panel and the release-notes panel list the same
four models, and that the quorum warning threshold matches the rule that actually fires.

⚠️ **A model id is not lowercase by convention.** A regex of `[a-z0-9.\-]+` written to compare the
two panel lists silently read three models instead of four, because `gemma-4-31B-it` has a capital
B. The comparison was of the wrong set and passed anyway.

---

## 10. Adding or replacing a kimi model

1. `model_probe.py --existence` — **a marketing name is not an API id.** `deepseek-v4-flash` was
   taken off a pricing page and 404'd on every call for weeks.
2. `model_probe.py --model <id> --via-enrich` — proves it through the production payload.
3. `compare_models.py --lang de` — the real prompt, not a toy one.
4. Only then edit `_FALLBACKS`. If the new id needs different parameters, add a `MODEL_PARAMS`
   prefix entry **and** a `test_recall.py` assertion in the same change.
5. `python ship.py` — one command. It resolves the effective chain with provenance
   (`GET /api/diag`) and fails the deploy on a chained id that does not exist.

**Do not chain `kimi-k3`.** DO's own changelog says it is *"tuned for max thinking effort by
default"* — the reasoning-model failure mode that has already broken the strict-JSON contract with
`deepseek-r1-distill` and `qwen3.5-397b`. DO has published no serverless rate for it. It is a
candidate for attribution research (1M context, long-horizon agentic), never for the deck-prose
JSON contract. `model_watch.py` auto-flags it **DO-NOT-CHAIN**.

---

## 11. The three rules this model taught us

1. **Never discard an API error body.** A 4xx is the server telling you what it wants. Three rounds
   of treating kimi as broken, and the answer was in a field we were throwing away.
2. **Repair what the server named, in the direction it named it.** A blanket remedy for one 400
   disabled the safeguard that made the next call work.
3. **"The model failed" is a conclusion, not an observation.** Check whether the request we sent
   could ever have succeeded — the ceiling, the slice, the parameters. Twice it could not.
