"""Role -> model routing for DigitalOcean Serverless Inference (OpenAI-compatible).

One place decides which DO model serves which task. Ids are exact DO slugs (see
https://docs.digitalocean.com/products/inference/details/models/) and are overridable via env,
so swapping a role's model is a one-line change with no code edits.
"""
import os
import httpx
from .settings import DO_BASE_URL, DO_KEY

# role -> DO model slug (env override: JHW_MODEL_<ROLE>)
DEFAULT_MODELS = {
    # V2 ARCHITECTURE: deterministic Playwright autofill drives the ATS; the LLM only ANSWERS
    # free-text screening questions (plain text) and does tailoring/extraction. No browser-driving
    # LLM in the hot path, so we pick RELIABLE instruct models over "agentic" ones.
    # Reliability ranking (2026, first-attempt-correct): Qwen3.5 ~94% > GLM-5.2 ~91% > DeepSeek 3.2.
    # DeepSeek-4-FLASH is a routing model and produced malformed JSON here — removed from the path.
    "answer":  "deepseek-3.2",              # screening-question answers (proven reliable text)
    "content": "deepseek-v4-pro",           # resume / cover-letter writing (quality)
    "content_fb": "deepseek-3.2",
    "extract": "deepseek-3.2",              # JD->fields structured (reliable JSON; was v4-flash)
    "extract_fb": "glm-5.2",
    "chat":    "deepseek-3.2",
    # Fallback LLM chain (only used if a non-Workday ATS still needs the old browser-use path):
    "driver":  "qwen3.5-397b-a17b",         # most reliable tool-caller
    "driver2": "glm-5.2",                   # reliable tool-caller
    "driver3": "deepseek-3.2",              # reliable text last resort
    "vision":  "nemotron-nano-12b-v2-vl",
}


def model_for(role: str) -> str:
    """Resolve a role name to a concrete DO model slug (env can override each role)."""
    env = os.getenv(f"JHW_MODEL_{role.upper()}")
    if env:
        return env
    return DEFAULT_MODELS.get(role, DEFAULT_MODELS["content"])


def routing_table() -> dict:
    return {r: model_for(r) for r in DEFAULT_MODELS}


def _headers():
    return {"Authorization": f"Bearer {DO_KEY}", "Content-Type": "application/json"}


async def complete(role: str, messages: list[dict], *, temperature: float = 0.3,
                   max_tokens: int | None = None, json_mode: bool = False) -> str:
    """Non-streaming completion for backend tasks (tailoring, extraction, field mapping)."""
    if not DO_KEY:
        raise RuntimeError("DO_INFERENCE_KEY is not set on the server")
    payload: dict = {
        "model": model_for(role),
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{DO_BASE_URL}/chat/completions", headers=_headers(), json=payload)
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"]
