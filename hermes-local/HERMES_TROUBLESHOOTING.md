# Hermes Agent — known issues & fixes (memorized, stop re-discovering)

Every failure we hit, its exact cause, and the fix. Check the container logs first:
`docker compose logs --since 15m hermes | Select-String "ERROR|429|context|not found|unexpected"`.

## Model requirements Hermes enforces
- **Context window ≥ 64,000 tokens (HARD).** Smaller models are rejected at startup
  (`ValueError: ... below the minimum 64,000 required`). GitHub issue #24140.
  Fix: use a ≥64K model, OR override `model.context_length` in config.yaml (see below).
- **Good tool-calling** — the agent lives on function calls. Prefer models built for tools.
- **Exact model id** — must match the endpoint's `/v1/models` list. DO ids are prefixed,
  e.g. `alibaba-qwen3-32b` (NOT `qwen3-32b`), `qwen3.5-397b-a17b`, `alibaba-qwen3-coder-flash`.

## Error → cause → fix
| Log message | Cause | Fix |
|---|---|---|
| `context window ... below the minimum 64,000` | model window < 64K (e.g. qwen3-32b = 32K) | pick a ≥64K model, or set `model.context_length` |
| `HTTP 429 rate_limit_exceeded` | model/endpoint capacity (huge model like 397B on shared serverless) — NOT balance/your volume | use a smaller model; or DO **Dedicated Inference**; or raise tier; or add a fallback provider |
| `Model X was not found in this custom endpoint's model listing` | wrong model id | use the exact id from `https://inference.do-ai.run/v1/models` (the `/model` command suggests the closest) |
| `Sorry, I encountered an unexpected error` (generic, in Telegram) | almost always one of the above — check logs for the real ValueError/HTTP code | fix per the real error in logs |

## Config levers (config.yaml in the hermes_data volume; most hot-reload)
- **`model.context_length: 65536`** — override the reported window. Hot-reloads on next message
  (no restart/`/reset`). Set it ≥64K but ≤ the endpoint's real served window. Command:
  `docker compose run --rm hermes hermes config set model.context_length 65536`
- **`fallback_providers:`** — list of backup provider/model so a 429 fails over instead of dying.
- **`compression.*`** — auto-compress long chats to stay under the window (hot-reloads).
- Keep turns small: disable browser tool (`hermes tools`), `/new` between jobs, use the
  one-command orchestrator (`run_assessment.py`) so the LLM does ~2 calls, not 60.

## Model choice for THIS bot (DO models on your access key)
| Model | Ctx | Size | Verdict |
|---|---|---|---|
| `qwen3.5-397b-a17b` | large | 397B | ✓ ctx ✓ tools — but **rate-limits** on serverless. Avoid for the bot. |
| `alibaba-qwen3-32b` | 32K | 32B | ✗ rejected (<64K) unless you override context_length |
| **`alibaba-qwen3-coder-flash`** | **256K** | 30B MoE (3B active) | ✅ **best**: big ctx, small→no rate-limit, built for tool-calling |
| `...-tts` | — | — | not a chat model, ignore |

**Decision: run the bot on `alibaba-qwen3-coder-flash`.** It uniquely satisfies all three Hermes
requirements (≥64K context, strong tools, small enough to avoid the 397B rate-limit).

## The working setup (do once)
```
# in Telegram — switch model (if "not found", use the exact id it suggests):
/model alibaba-qwen3-coder-flash
```
```powershell
# guarantee the 64K check passes regardless of what DO reports (harmless, hot-reloads):
docker compose run --rm hermes hermes config set model.context_length 65536
```
```
# in Telegram:
/reset
test          # should reply normally
/shodan-assessment keb.de
```

## Structural (production / never-fail)
- **DO Dedicated Inference** = your own provisioned throughput → even a big model never 429s.
- **fallback_providers** in config.yaml → automatic failover (e.g. Nous Portal / OpenRouter).
- Keep `run_assessment.py` as the one-shot so the model barely works = minimal exposure to limits.

## Sources
- Hermes 64K requirement / issue: https://github.com/NousResearch/hermes-agent/issues/24140
- Hermes context_length hot-reload + config: https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- Hermes FAQ/troubleshooting: https://hermes-agent.nousresearch.com/docs/reference/faq
- DO inference limits (tiers/rate): https://docs.digitalocean.com/products/inference/details/limits/
