"""Human-in-the-loop channel: the agent asks the candidate for info it doesn't have.

V1 = Telegram (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID). V2 seam = 'web' (React cabinet via the
backend). Channel chosen by JHW_ASK_CHANNEL (default 'auto' -> telegram if configured, else none).
"""
from __future__ import annotations
import asyncio, os, time
import httpx

CHANNEL     = os.getenv("JHW_ASK_CHANNEL", "auto")
TG_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT     = os.getenv("TELEGRAM_CHAT_ID", "")
ASK_TIMEOUT = int(os.getenv("JHW_ASK_TIMEOUT", "600"))         # seconds to wait for a human reply
WEB_BASE    = os.getenv("JHW_ASK_WEB_BASE", "")                # V2: backend endpoint base


def channel() -> str:
    if CHANNEL != "auto":
        return CHANNEL
    if TG_TOKEN and TG_CHAT:
        return "telegram"
    return "none"


async def _telegram(question: str, timeout: int) -> str:
    base = f"https://api.telegram.org/bot{TG_TOKEN}"
    async with httpx.AsyncClient(timeout=40) as c:
        last = 0
        try:
            r = (await c.get(f"{base}/getUpdates", params={"timeout": 0})).json()
            for u in r.get("result", []):
                last = max(last, u["update_id"])
        except Exception:
            pass
        await c.get(f"{base}/sendMessage", params={
            "chat_id": TG_CHAT,
            "text": f"🤖 JobHuntWOW needs your input:\n\n{question}\n\nReply here with the value."})
        offset, deadline = last + 1, time.time() + timeout
        while time.time() < deadline:
            try:
                rr = (await c.get(f"{base}/getUpdates", params={"offset": offset, "timeout": 30})).json()
            except Exception:
                await asyncio.sleep(2); continue
            for u in rr.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message", {})
                if str(m.get("chat", {}).get("id")) == str(TG_CHAT) and m.get("text"):
                    ans = m["text"].strip()
                    await c.get(f"{base}/sendMessage", params={"chat_id": TG_CHAT, "text": "✅ Got it — thanks."})
                    return ans
    return ""


async def _web(question: str, timeout: int) -> str:
    """V2 stub: post the question to the backend and poll for the candidate's answer in the cabinet."""
    if not WEB_BASE:
        return ""
    async with httpx.AsyncClient(timeout=40) as c:
        try:
            r = await c.post(f"{WEB_BASE}/api/ask", json={"question": question})
            qid = r.json().get("id")
        except Exception:
            return ""
        deadline = time.time() + timeout
        while qid and time.time() < deadline:
            try:
                a = (await c.get(f"{WEB_BASE}/api/ask/{qid}")).json()
                if a.get("answer"):
                    return a["answer"].strip()
            except Exception:
                pass
            await asyncio.sleep(3)
    return ""


async def notify(message: str) -> None:
    """Fire-and-forget alert to the candidate (no waiting for a reply). Used whenever the driver
       stops, pauses, or gets stuck — so the human ALWAYS hears about it."""
    ch = channel()
    print(f"[notify/{ch}] {message}", flush=True)
    if ch != "telegram":
        return
    base = f"https://api.telegram.org/bot{TG_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            await c.get(f"{base}/sendMessage", params={"chat_id": TG_CHAT, "text": f"🤖 JobHuntWOW: {message}"})
    except Exception as e:
        print(f"[notify] send failed: {e}", flush=True)


async def ask_human(question: str, timeout: int | None = None) -> str:
    timeout = timeout or ASK_TIMEOUT
    ch = channel()
    print(f"[ask_human/{ch}] {question}", flush=True)
    if ch == "telegram":
        return await _telegram(question, timeout)
    if ch == "web":
        return await _web(question, timeout)
    return ""   # no channel configured -> agent leaves blank + notes it
