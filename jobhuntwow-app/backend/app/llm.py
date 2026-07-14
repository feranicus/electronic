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
    "driver":  "anthropic-claude-4.6-sonnet",   # browser navigation: tool-calling + vision
    "vision":  "nemotron-nano-12b-v2-vl",       # cheap screenshot fallback
    "content": "deepseek-3.2",                   # resume / cover-letter writing
    "extract": "llama3.3-70b-instruct",          # JD->requirements, profile->fields (JSON)
    "chat":    "deepseek-3.2",                   # Hermes assistant
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
