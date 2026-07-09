# Rate-limiting — root cause & enterprise fix (CONFIRMED from logs)

## Symptom
`The model provider is rate-limiting requests` — persistent `HTTP 429 rate_limit_exceeded_error`,
even on the first request of a fresh chat.

## Confirmed diagnosis (from Hermes logs + DO dashboard, 6 Jul 2026)
- Error body: `{'type':'rate_limit_exceeded_error','status_code':429}` — a pure rate limit.
- **Balance is fine:** $12.63 prepaid remaining, MTD spend $5.89. NOT a billing/balance issue.
- **Account is Tier 2:** 120 RPM / 500K–750K TPM.
- Each request ≈ **~18,000 tokens**; request rate is near-zero (dashboard Requests/sec Max 0).

18K tokens sent infrequently cannot exceed a 500K-TPM account limit. Therefore the throttle is
**at the model, not the account**: `qwen3.5-397b-a17b` is a giant MoE with its own tight
serverless throughput/capacity cap, so it returns 429 on almost any call regardless of your quota.

**Root cause = using the 397B model on shared serverless.** Not balance. Not your volume.

---

## THE FIX (do this first — it resolves it)
**Switch Hermes to a smaller DigitalOcean model.** The agent only runs one command and relays
files — it does not need a 397B model. A smaller model has far higher serverless throughput and
does not 429.

- Fastest (live, in Telegram): `/model openai-gpt-oss-120b`
- Or CLI: `docker compose run --rm hermes hermes model` → pick the smaller model → `docker compose up -d`
- Tier-2-accessible candidates (confirm exact id in DO **Model Catalog**):
  `openai-gpt-oss-120b`, `openai-gpt-oss-20b`, `llama3.3-70b-instruct`.
  (DO docs: Tier 1/2 have access to `gpt-oss-120b` and `gpt-oss-20b`.)

## Reinforcements (belt & suspenders)
- **Disable the browser tool** (`docker compose run --rm hermes hermes tools`) — it inflates every
  turn (~18K tokens) with tool schemas/DOM. Shodan runs via the API script, so the browser isn't
  needed for assessments. Smaller turns = more headroom.
- **Keep the one-command orchestrator** `run_assessment.py` — ~2 LLM calls instead of a 60-step loop.
- **`/new` between jobs** to keep context small.

## Structural (production / 24-7 bot — once and for all)
- **DO Dedicated Inference** — a provisioned endpoint with YOUR own throughput; even a large model
  won't be throttled. Point Hermes' `OPENAI_BASE_URL` at it. (Inference → Use Dedicated Inference.)
- **Multi-provider failover** in Hermes (Nous Portal / OpenRouter / a second DO endpoint) so a 429
  auto-fails-over and never blocks the AE.
- Optionally raise the account tier (cloud.digitalocean.com/limits) — but with a smaller model the
  Tier-2 limits are already ample.

## Recommended path
1. **Now:** `/model openai-gpt-oss-120b` (or llama3.3-70b) + disable browser. 429s stop.
2. **Production:** Dedicated Inference for guaranteed throughput.
3. **Always-on:** add a fallback provider.

## Sources
- DigitalOcean — Inference Limits (tiers, prepaid, Tier-1/2 gpt-oss access):
  https://docs.digitalocean.com/products/inference/details/limits/
- DigitalOcean — Dedicated Inference:
  https://docs.digitalocean.com/products/inference/how-to/use-dedicated-inference/
