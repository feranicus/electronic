#!/usr/bin/env python3
"""Colt assessment Telegram bot (colttechbot) — deterministic engine + ONE controlled
DeepSeek enrichment call. Zero-trust gate: every user must authenticate with a Colt-branded
email (name.familyname@colt.net) + a shared 99-char access password BEFORE using /assess.
Streams live phase progress, shows when the AI takes over (tokens + est cost), and re-emits
structured JSON events (incl. auth audit) for the Loki/Grafana observability stack."""
import os, json, time, asyncio, colt_auth
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN   = os.environ["BOT_TOKEN"]
ALLOWED = {x.strip() for x in os.environ.get("ALLOWED_USERS", "").split(",") if x.strip()}
OUTDIR  = os.environ.get("OUTDIR", "/root/work")
ENGINE  = "/opt/shodan-skill/scripts/run_assessment.py"
EVENTS  = os.environ.get("EVENTS_LOG", os.path.join(OUTDIR, "events.log"))
try: os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
except Exception: pass

# ---------------- zero-trust auth (email + password + email OTP 2FA — shared module) ----------------
AUTHFILE   = os.environ.get("AUTH_STORE", os.path.join(os.path.dirname(EVENTS), "authorized.json"))
QWEN_EVT_A = '"evt": "qwen"'; QWEN_EVT_B = '"evt":"qwen"'
BOT_NAME   = "colttechbot"
def _evfile(line):
    try:
        with open(EVENTS, "a") as fh: fh.write(line + "\n")
    except Exception: pass
def _evfile_json(line):
    # tag subprocess JSON events (qwen/phase/assess_done) with the bot for observability
    try:
        o = json.loads(line)
        if isinstance(o, dict):
            o.setdefault("bot", BOT_NAME); line = json.dumps(o)
    except Exception: pass
    _evfile(line)
def _log(**k):
    k.setdefault("bot", BOT_NAME)
    line = json.dumps(k); print(line, flush=True); _evfile(line)

AUTH = colt_auth.Auth(BOT_NAME, AUTHFILE, log=_log)   # email + password + email OTP 2FA

async def start(update, ctx):
    await update.message.reply_text(
        "\U0001f512 Colt Cyber Assessment bot (colttechbot) — zero-trust access.\n\n"
        "To use this bot you must authenticate with your Colt identity:\n"
        "  /auth name.familyname@colt.net <access-password>\n\n"
        "Example:\n  /auth jevgenijs.vainsteins@colt.net <password>\n\n"
        "After authentication:\n"
        "  /assess <company / domain / ASN>\n"
        "  e.g.  /assess keb.de\n"
        "  Behind a CDN?  /assess <company> --asn AS1234 --net 1.2.3.0/24\n"
        "  I will ask English or Deutsch; skip with  /assess <company> --lang de\n\n"
        "2-step: after /auth I email a 6-digit code to your Colt address; reply /verify <code>.\n"
        "⚠ Your /auth message contains a secret — delete it from this chat afterwards.")

async def auth(update, ctx):
    uid = update.effective_user.id
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /auth name.familyname@colt.net <access-password>")
        return
    email = ctx.args[0].strip(); pw = " ".join(ctx.args[1:]).strip()
    _, msg = AUTH.begin(uid, email, pw)               # validates, then emails a 6-digit code
    await update.message.reply_text(msg + "\n⚠ Delete your /auth message — it contains the password.")

async def verify(update, ctx):
    uid = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text("Usage: /verify <6-digit code from your Colt email>"); return
    _, msg = AUTH.verify(uid, ctx.args[0].strip())
    await update.message.reply_text(msg)

async def assess(update, ctx):
    """Collect the company, then ASK which language the documents should be in.
    Power users can skip the prompt entirely with:  /assess <company> --lang de"""
    uid = update.effective_user.id
    if not AUTH.is_authed(uid, ALLOWED):
        await update.message.reply_text(
            "\U0001f512 Not authenticated. Run:\n"
            "  /auth name.familyname@colt.net <access-password>\n"
            "then /verify <code> from the email I send you.")
        _log(evt="assess_denied", user=str(uid), ts=int(time.time())); return
    if not ctx.args:
        await update.message.reply_text("Usage: /assess <company / domain / ASN>")
        return
    _args = list(ctx.args)
    _i = next((k for k, t in enumerate(_args) if t.startswith('--')), len(_args))
    seed = ' '.join(_args[:_i]).strip(); extra = _args[_i:]   # multi-word company names -> one seed
    if not seed:
        await update.message.reply_text('Usage: /assess <company / domain / ASN>'); return

    # explicit --lang de/--lang en -> run straight away, no question
    if any(t == "--lang" or t.startswith("--lang=") for t in extra):
        await _run_assessment(update.message, ctx, uid, seed, extra); return

    # otherwise ask. The pending run is parked per-user (never global: two AEs can assess at once).
    ctx.user_data["pending"] = {"seed": seed, "extra": extra}
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("\U0001f1ec\U0001f1e7  English", callback_data="lang:en"),
        InlineKeyboardButton("\U0001f1e9\U0001f1ea  Deutsch", callback_data="lang:de"),
    ]])
    await update.message.reply_text(
        "\U0001f30d In which language should I write the 4 documents for *%s*?\n"
        "_Findings · C-BIQ · GEOPOL · DELTAS_" % seed,
        reply_markup=kb, parse_mode="Markdown")


async def on_lang(update, ctx):
    """Language button pressed -> start the parked assessment."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not AUTH.is_authed(uid, ALLOWED):
        await q.edit_message_text("\U0001f512 Not authenticated."); return
    lang = "de" if q.data.endswith(":de") else "en"
    pending = (ctx.user_data or {}).pop("pending", None)
    if not pending:
        await q.edit_message_text("That request expired \u2014 send /assess <company> again."); return
    await q.edit_message_text("%s Language: %s \u2014 starting the assessment for %s ..." % (
        ("\U0001f1e9\U0001f1ea" if lang == "de" else "\U0001f1ec\U0001f1e7"),
        ("Hochdeutsch" if lang == "de" else "English"), pending["seed"]))
    await _run_assessment(q.message, ctx, uid, pending["seed"], pending["extra"] + ["--lang", lang])


async def _run_assessment(msg, ctx, uid, seed, extra):
    lang = "de" if "de" in [str(x).lower().replace("--lang=", "") for x in extra] else "en"
    _log(evt="assess_start", company=seed, user=str(uid), lang=lang,
         email=AUTH.authed.get(str(uid), {}).get("email", ""), ts=int(time.time()))
    status = await msg.reply_text("⏳ Assessing %s ..." % seed)
    steps = []

    cmd = ["python3", ENGINE, "--seed", seed, "--outdir", OUTDIR] + list(extra)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env={**os.environ})

    lines = []
    async for raw in proc.stdout:
        line = raw.decode("utf-8", "ignore").rstrip()
        if not line:
            continue
        lines.append(line)
        print(line, flush=True)
        if line.startswith("{"): _evfile_json(line)   # -> events.log -> promtail -> Loki -> Grafana
        if line.startswith("PROGRESS:"):
            steps.append("- " + line[len("PROGRESS:"):].strip())
            try:
                await status.edit_text(("⏳ %s\n" % seed) + "\n".join(steps[-8:]))
            except Exception:
                pass
    await proc.wait()
    out = "\n".join(lines)

    if "ASSESSMENT COMPLETE" not in out:
        _log(evt="error", company=seed, msg="pipeline failed")
        await msg.reply_text("❌ Failed:\n" + (out[-1500:] or "no output"))
        return

    summary = "\n".join(l for l in lines
                        if any(k in l for k in ("Company:", "Findings:", "Priced", "Threat actors", "QA:")))
    qwen = None
    for l in lines:
        if QWEN_EVT_A in l or QWEN_EVT_B in l:
            try:
                qwen = json.loads(l)
            except Exception:
                pass
    stat = ""
    if qwen:
        if qwen.get("status") == "ok":
            tok = qwen.get("tokens_in", 0) + qwen.get("tokens_out", 0)
            stat = "\n\U0001f9e0 AI enrichment: ON - %s - %s tokens - ~$%.4f (DO serverless)" % (
                qwen.get("model", ""), tok, qwen.get("cost_usd", 0))
        else:
            stat = "\n\U0001f9e0 AI enrichment: %s [%s] (templated text used - deck still valid)" % (
                qwen.get("status", "off"), (qwen.get("error", "") or "")[:120])
    await msg.reply_text("✅ Done.\n" + summary + stat)

    decks = [l.split("OK", 1)[1].strip() for l in lines
             if l.strip().startswith("OK") and l.strip().endswith(".pptx")]
    for path in decks:
        if os.path.exists(path):
            with open(path, "rb") as fh:
                await msg.reply_document(fh, filename=os.path.basename(path))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CommandHandler("assess", assess))
    app.add_handler(CallbackQueryHandler(on_lang, pattern=r"^lang:(en|de)$"))
    print("colttechbot polling (zero-trust auth enabled)...", flush=True)
    app.run_polling()

if __name__ == "__main__":
    main()
