"""
visitors.py — tell me when a real person arrives; give crawlers a 404.

Two jobs, both driven off the same user-agent classification telemetry.py already does:

  1. HUMAN VISIT ALERT — email + Telegram the moment a real person opens the site.
     De-duplicated per visitor per window: one human browsing five pages is ONE alert, not five.
     Capped per hour, because an alert flood is indistinguishable from no alerts at all.

  2. BOT 404 GATE — anything classified as a bot gets a 404 for the WEBSITE.

WHY THE GATE STOPS AT THE WEBSITE (this is deliberate, do not "tidy" it):
  `/api/*` is EXEMPT. Every deploy verifier in this repo — ship.py, deploy_web_direct.py and
  web-deploy.yml — proves the site is live by fetching `/api/me` and asserting **401**. They use
  curl / urllib, whose user agents classify as bots. 404-ing them would make every single deploy
  report itself broken, and the engine-hash/verify machinery exists precisely so a deploy can never
  lie. The API is zero-trust anyway: a crawler that reaches it gets 401 and learns nothing, and
  alerts.py already watches for 401/403 probing storms.
  `/.well-known/*` is EXEMPT so ACME/TLS renewal and RFC 9116 security.txt keep working.

TRADE-OFFS YOU ARE ACCEPTING BY LEAVING BOT_404=1 (both reversible with one env var):
  * Search engines get 404 → the site will not be indexed by Google/Bing. Fine for an
    access-restricted tool; fatal if you ever want to be found. Allow them with
    BOT_404_ALLOW="googlebot,bingbot".
  * Link unfurlers get 404 → a cybergod.ai link pasted into Slack/Telegram/WhatsApp shows no
    preview. Allow with BOT_404_ALLOW="slackbot,telegrambot,whatsapp,linkedinbot,discordbot".

Env:
  BOT_404=1|0                     serve 404 to bots on page routes (default 1)
  BOT_404_ALLOW="a,b"             substrings of bot_name that are let through (default: none)
  VISIT_NOTIFY=1|0                alert on human visits (default 1)
  VISIT_DEDUPE_S=21600            one alert per visitor per this many seconds (default 6h)
  VISIT_MAX_PER_HOUR=30           hard cap on visit alerts per hour
"""
import os, time
from collections import deque

try:
    from . import notify, telemetry
except ImportError:                      # standalone import (tests)
    import notify, telemetry


def _i(name, d):
    try: return int(os.environ.get(name, d))
    except ValueError: return d


BOT_404            = os.environ.get("BOT_404", "1") != "0"
BOT_404_ALLOW      = [x.strip().lower() for x in os.environ.get("BOT_404_ALLOW", "").split(",") if x.strip()]
VISIT_NOTIFY       = os.environ.get("VISIT_NOTIFY", "1") != "0"
VISIT_DEDUPE_S     = _i("VISIT_DEDUPE_S", 6 * 3600)
VISIT_MAX_PER_HOUR = _i("VISIT_MAX_PER_HOUR", 30)

# Paths the gate must never touch. See the module docstring for why /api is here.
EXEMPT_PREFIXES = ("/api/", "/.well-known/")
EXEMPT_EXACT    = ("/robots.txt", "/favicon.ico", "/healthz", "/health")

_seen = {}          # visitor key -> last-alerted ts
_sent = deque()     # timestamps of visit alerts, for the hourly cap


def classify(request):
    """-> the telemetry UA verdict dict for this request. Never raises."""
    try:
        return telemetry.classify_ua(request.headers.get("user-agent", ""))
    except Exception:
        return {"bot": False, "bot_name": "-", "browser": "-", "os": "-", "device": "unknown"}


def _exempt(path):
    return path.startswith(EXEMPT_PREFIXES) or path in EXEMPT_EXACT


def should_block(path, cls):
    """True if this request is a bot asking for the website and the gate is on."""
    if not BOT_404 or not cls.get("bot"):
        return False
    if _exempt(path or "/"):
        return False
    name = str(cls.get("bot_name") or "").lower()
    if any(a and a in name for a in BOT_404_ALLOW):
        return False
    return True


# A real 404 — same visual language as the site, no hint that anything was filtered.
NOT_FOUND_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>404 — not found</title>
<meta name="robots" content="noindex,nofollow"><style>
html,body{height:100%;margin:0}
body{background:#0a1526;color:#eaf1fb;font-family:Inter,"Segoe UI",Arial,sans-serif;
display:grid;place-items:center;text-align:center;padding:24px}
h1{font-size:64px;margin:0;font-weight:800;letter-spacing:-2px}
p{color:#93a9ce;margin:10px 0 0;font-size:16px}
b{color:#00B2A9;font-weight:800}
</style></head><body><div>
<h1>404</h1><p>This page could not be found.</p>
<p style="margin-top:18px;font-size:14px"><b>&#10095; colt</b></p>
</div></body></html>"""


def _key(ip, cls):
    """One human = one alert. Keyed on IP plus a coarse client fingerprint, so a phone and a laptop
    on the same office NAT are still two visitors, while one person clicking around is one."""
    return "%s|%s|%s" % (ip or "-", cls.get("browser") or "-", cls.get("os") or "-")


def note_visit(ev, cls):
    """Called after a HUMAN page response. De-duplicates, caps, then alerts. Never raises."""
    if not VISIT_NOTIFY:
        return
    try:
        path = ev.get("path") or "/"
        if path.startswith(EXEMPT_PREFIXES) or path in EXEMPT_EXACT:
            return
        if int(ev.get("status", 0)) >= 400:
            return                                   # errors are the alert engine's business
        if ev.get("user"):
            return                                   # signed-in people already trigger a login alert
        ip = ev.get("ip", "-")
        now = time.time()
        k = _key(ip, cls)
        if now - _seen.get(k, 0) < VISIT_DEDUPE_S:
            return                                   # same visitor, still inside the window
        while _sent and _sent[0] < now - 3600:
            _sent.popleft()
        if len(_sent) >= VISIT_MAX_PER_HOUR:
            notify._log(evt="visit_suppressed", reason="cap %d/h reached" % VISIT_MAX_PER_HOUR, ip=ip)
            return
        _seen[k] = now
        _sent.append(now)
        if len(_seen) > 4000:                        # keep the dedupe table bounded
            for old in [kk for kk, ts in _seen.items() if now - ts > VISIT_DEDUPE_S]:
                _seen.pop(old, None)

        notify._log(evt="visit_notice", ip=ip, country=ev.get("country"), path=path,
                    browser=cls.get("browser"), os=cls.get("os"), device=cls.get("device"),
                    ref=ev.get("ref"))
        body = "\n".join([
            "A person just opened cybergod.ai.",
            "",
            "When    : %s" % time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now)),
            "Page    : %s" % path,
            "IP      : %s%s" % (ip, (" (%s)" % ev.get("country")) if ev.get("country") not in (None, "", "-") else ""),
            "Client  : %s / %s / %s" % (cls.get("browser"), cls.get("os"), cls.get("device")),
            "Referrer: %s" % (ev.get("ref") or "direct"),
            "Language: %s" % (ev.get("lang") or "-"),
            "",
            "Bots are served a 404 and never reach this alert.",
            "One alert per visitor per %d hour(s)." % max(1, VISIT_DEDUPE_S // 3600),
        ])
        notify.fire_and_forget(notify.both, "Visitor on cybergod.ai — %s" % path, body)
    except Exception:
        pass


def note_block(ev, cls):
    """A bot was served the 404. Logged only — never alerted, or a single crawler would spam you."""
    try:
        notify._log(evt="bot_blocked", ip=ev.get("ip"), country=ev.get("country"),
                    path=ev.get("path"), bot_name=cls.get("bot_name"), ua=(ev.get("ua") or "")[:160])
    except Exception:
        pass
