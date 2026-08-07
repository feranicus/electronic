"""
notify.py — one place that can reach a human: Telegram + email.

Reuses what already works on this droplet:
  * Gmail API over HTTPS (service account + domain-wide delegation) — the droplet BLOCKS SMTP ports,
    which is why colt_auth sends OTPs this way. Same mechanism, same credentials.
  * The Telegram bot token the assess-bot already has (colt-web loads assess-bot/.env).

Never raises: an alert that crashes the request it is warning about is worse than no alert.
"""
import json, os, time, urllib.parse, urllib.request

TG_TOKEN   = os.environ.get("BOT_TOKEN", "")
ALERT_CHAT = os.environ.get("ALERT_TG_CHAT", "")          # numeric chat id; auto-discovered if empty
# Comma-separated list -> every address here gets every alert + the daily report.
# 2026-08: the colt.net recipient was removed (the operator left Colt); do not re-add it.
ALERT_MAIL = os.environ.get("ALERT_EMAIL", "feranicus@s4biz.io")
ALERT_MAILS = [e.strip() for e in ALERT_MAIL.split(",") if e.strip()]
GMAIL_SENDER = os.environ.get("GMAIL_SENDER", "")
GMAIL_SA_B64 = os.environ.get("GMAIL_SA_B64", "")
AUTH_STORE = os.environ.get("AUTH_STORE", "/data/web_authorized.json")


def _log(**k):
    k.setdefault("ts", time.time()); k.setdefault("service", os.environ.get("SERVICE", "colt-web"))
    k.setdefault("bot", "webapp")
    line = json.dumps(k)
    try: print(line, flush=True)
    except Exception: pass
    try:
        p = os.environ.get("EVENTS_LOG", "")
        if p:
            with open(p, "a") as fh: fh.write(line + "\n")
    except Exception: pass


def _tg_chats():
    """Explicit ALERT_TG_CHAT wins. Otherwise alert every authenticated operator we know about —
    better to over-notify the owner than to have a silent security alert."""
    if ALERT_CHAT:
        return [c.strip() for c in ALERT_CHAT.split(",") if c.strip()]
    out = []
    for p in (AUTH_STORE, "/var/log/colt/authorized.json"):
        try:
            for uid in (json.load(open(p)) or {}):
                if str(uid).lstrip("-").isdigit() and str(uid) not in out:
                    out.append(str(uid))
        except Exception:
            pass
    return out


def telegram(text):
    if not TG_TOKEN:
        return False
    ok = False
    for chat in _tg_chats():
        try:
            data = urllib.parse.urlencode({"chat_id": chat, "text": text[:3900],
                                           "parse_mode": "Markdown",
                                           "disable_web_page_preview": "true"}).encode()
            req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % TG_TOKEN, data=data)
            with urllib.request.urlopen(req, timeout=12) as r:
                ok = (r.status == 200) or ok
        except Exception as e:
            _log(evt="alert_delivery", channel="telegram", chat=str(chat), result="error", err=repr(e)[:160])
    return ok


def email(subject, body, to=None):
    """Gmail API (HTTPS). SMTP is blocked outbound on this droplet — do not 'fix' this to SMTP.
    `to` may be a comma list or a python list; every recipient gets it."""
    if to is None:
        to = ALERT_MAILS
    if isinstance(to, str):
        to = [x.strip() for x in to.split(",") if x.strip()]
    to = ", ".join(to)
    if not (GMAIL_SENDER and GMAIL_SA_B64):
        _log(evt="alert_delivery", channel="email", result="skipped", err="GMAIL_SENDER/GMAIL_SA_B64 not set")
        return False
    try:
        import base64
        from email.message import EmailMessage
        import requests
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request as GRequest
        msg = EmailMessage()
        msg["Subject"] = subject[:200]; msg["From"] = GMAIL_SENDER; msg["To"] = to
        msg.set_content(body)
        info = json.loads(base64.b64decode(GMAIL_SA_B64))
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/gmail.send"], subject=GMAIL_SENDER)
        creds.refresh(GRequest())
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        r = requests.post("https://gmail.googleapis.com/gmail/v1/users/%s/messages/send" % GMAIL_SENDER,
                          headers={"Authorization": "Bearer " + creds.token,
                                   "Content-Type": "application/json"},
                          json={"raw": raw}, timeout=20)
        if r.status_code in (200, 202):
            return True
        _log(evt="alert_delivery", channel="email", result="error", status=r.status_code, err=r.text[:200])
    except Exception as e:
        _log(evt="alert_delivery", channel="email", result="error", err=repr(e)[:200])
    return False


def both(subject, body):
    """Fire both channels. Independent: email failing must not silence Telegram."""
    t = telegram("🚨 *%s*\n\n%s" % (subject, body))
    e = email("[cybergod.ai] " + subject, body)
    _log(evt="alert_delivery", channel="both", telegram=bool(t), email=bool(e), subject=subject[:120])
    return t or e


# ---------------------------------------------------------------- operator activity feed
# "Tell me every time someone logs in, and every time someone runs a report."
# These are INFORMATIONAL, not security alerts: they deliberately bypass alerts.py's cooldown and
# storm-cap (that machinery exists to stop an attack flooding you; a login you asked to see must
# never be silently suppressed). Volume is bounded by the size of the allow-list, not by the internet.
#
# NOTHING here may block the FastAPI event loop: telegram()/email() do synchronous network I/O, so
# always dispatch through fire_and_forget().
import threading

NOTIFY_LOGINS  = os.environ.get("NOTIFY_LOGINS", "1") != "0"
NOTIFY_REPORTS = os.environ.get("NOTIFY_REPORTS", "1") != "0"


def fire_and_forget(fn, *a, **kw):
    """Run a blocking notification on a daemon thread. Never raises into the caller."""
    try:
        threading.Thread(target=lambda: _safe(fn, *a, **kw), daemon=True).start()
    except Exception:
        pass


def _safe(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except Exception as e:
        _log(evt="alert_delivery", channel="thread", result="error", err=repr(e)[:160])


def _stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def notify_login(email, ip="", ua="", country="", how="web"):
    """Every successful sign-in."""
    if not NOTIFY_LOGINS:
        return
    _log(evt="login_notice", user=email, ip=ip, country=country, how=how)
    body = ("\n".join([
        "%s just signed in to cybergod.ai." % email,
        "",
        "When    : %s" % _stamp(),
        "Via     : %s" % how,
        "IP      : %s%s" % (ip or "-", (" (%s)" % country) if country else ""),
        "Device  : %s" % ((ua or "-")[:160]),
        "",
        "If this was not expected, rotate the shared password.",
    ]))
    fire_and_forget(both, "Login — %s" % email, body)


def notify_report(email, company, kind="assessment", phase="started", ip="", extra=None):
    """Every report run: once when it starts, once when it finishes."""
    if not NOTIFY_REPORTS:
        return
    extra = extra or {}
    _log(evt="report_notice", user=email, company=company, kind=kind, phase=phase, **{
        k: v for k, v in extra.items() if isinstance(v, (str, int, float, bool))})
    lines = ["%s %s a %s for %s." % (email, "started" if phase == "started" else "finished", kind, company),
             "", "When    : %s" % _stamp(), "Company : %s" % company, "Type    : %s" % kind]
    if ip:
        lines.append("IP      : %s" % ip)
    for k, v in extra.items():
        lines.append("%-8s: %s" % (k[:8], v))
    icon = "▶" if phase == "started" else "✅"
    fire_and_forget(both, "%s Report %s — %s (%s)" % (icon, phase, company, email), "\n".join(lines))
