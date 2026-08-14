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
import os, re, time
from collections import deque

try:
    from . import notify, telemetry
except ImportError:                      # standalone import (tests)
    import notify, telemetry


def _i(name, d):
    try: return int(os.environ.get(name, d))
    except ValueError: return d


BOT_404            = os.environ.get("BOT_404", "1") != "0"
# DEFAULT CHANGED 2026-08: search engines are now allowed through.
# For months the default was "allow nobody", which meant Googlebot got a 404 on every page route.
# The consequence was not merely "we are not indexed" — Google kept serving a STALE snippet
# harvested from the old GitHub Pages landing ("colt — cyber pre-sales"), and could never refresh
# it, because refreshing requires a successful crawl. Editing the meta tags alone would have
# changed nothing at all.
# Google + Bing + DuckDuckGo, and the unfurlers that render the link card in LinkedIn/Slack/
# WhatsApp/Telegram. Every scraper, SEO-backlink harvester, AI-training crawler and vulnerability
# scanner still gets a 404. Keep this list in agreement with public/robots.txt.
BOT_404_ALLOW      = [x.strip().lower() for x in os.environ.get(
    "BOT_404_ALLOW",
    "googlebot,bingbot,duckduckbot,linkedinbot,slackbot,whatsapp,telegrambot"
).split(",") if x.strip()]
VISIT_NOTIFY       = os.environ.get("VISIT_NOTIFY", "1") != "0"
VISIT_DEDUPE_S     = _i("VISIT_DEDUPE_S", 6 * 3600)
VISIT_MAX_PER_HOUR = _i("VISIT_MAX_PER_HOUR", 30)

# Paths the gate must never touch. See the module docstring for why /api is here.
EXEMPT_PREFIXES = ("/api/", "/.well-known/")
# /sitemap.xml belongs here for the same reason /robots.txt does: a crawler fetches it BEFORE it
# has identified itself as anything we recognise, and 404-ing the sitemap silently kills indexing.
EXEMPT_EXACT    = ("/robots.txt", "/sitemap.xml", "/favicon.ico", "/healthz", "/health")

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
<p style="margin-top:18px;font-size:14px"><b>&#10095; cybergod.ai</b></p>
</div></body></html>"""


def _probe_path(path):
    """True when the PATH itself is scanner behaviour, whatever the user agent claims.

    Deliberately independent of main.py's `_is_probe`: this module must keep working if it is ever
    imported without the app, and the rule here is narrower on purpose — it only has to be right
    about paths a HUMAN would never request, because the only consequence is suppressing an alert.
    """
    # ONE DEFINITION, SHARED WITH THE SHIELD. Keeping a second, weaker copy here is how
    # //slug, /[workspace]/, /DOCS.md and /IAM.md all read as human page views on 10 Aug: the
    # shield knew they were scanner paths and this module did not. A value that two modules must
    # agree on has one home. The local fallback below only exists so visitors.py still works if it
    # is ever imported without the rest of the app.
    try:
        from . import shield
        return shield.is_probe_path(path)
    except Exception:
        pass
    p = str(path or "/").lower()
    if p.startswith("/.well-known/"):
        return False
    if re.search(r"(?:^|/)\.[^/]", p):        # /.svn /.git /.env /.aws /.ssh — dot-directories
        return True
    return any(h in p for h in (
        ".php", ".asp", ".jsp", ".cgi", ".sql", ".bak", ".db", ".sqlite", ".pem", ".key",
        "wp-", "wordpress", "phpmyadmin", "xmlrpc", "cgi-bin", "adminer", "actuator",
        "struts", "vendor/", "id_rsa", "credentials", "backup", "dump", "/null"))


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
        # CLASSIFY BY PATH, NOT ONLY BY USER AGENT. A scanner asked for /.svn/wc.db while
        # announcing itself as "Safari / iOS / mobile", so the UA-based bot check passed it through
        # and the alert claimed a person had arrived — on a path no person has ever typed. A user
        # agent is attacker-controlled; the path they asked for is the actual evidence.
        # ONE IP PRESENTING SEVERAL BROWSERS IS A SCANNER, AND THIS IS UNFAKEABLE-AWAY.
        # On 10 Aug 2026 a single address produced SIX "a person just opened cybergod.ai" alerts
        # in two seconds as Safari/macOS, Chrome/Linux, Chrome/macOS, Edge/Windows, Firefox/Windows
        # and Firefox/macOS. The dedupe key deliberately includes the client fingerprint (so a
        # phone and a laptop behind one office NAT are two visitors) -- which made UA ROTATION a
        # free way to flood the operator with six alerts. The rotation is the evidence: an attacker
        # varying the user agent to defeat per-client limits produces the one thing a real visitor
        # never does. shield.observe() has already recorded the fingerprints, so ask it.
        try:
            from . import shield as _sh
            if "ua_rotation" in _sh.observe(ev.get("ip"), path, ev.get("status", 200),
                                            cls or {}, ev.get("method", "GET")):
                notify._log(evt="visit_suppressed", reason="one IP, several browsers (UA rotation)",
                            ip=ev.get("ip", "-"), path=path, ua=(ev.get("ua") or "")[:120])
                return
        except Exception:
            pass
        if _probe_path(path):
            notify._log(evt="visit_suppressed", reason="probe path (spoofed UA)",
                        ip=ev.get("ip", "-"), path=path, ua=(ev.get("ua") or "")[:120])
            return
        # ONLY BULLETPROOF HOSTING AND SCANNERS ARE SUPPRESSED - THEY ARE NEVER A PERSON.
        # 45.148.10.5 (AS48090 TECHOFF / DMZHOST, bulletproof) triggered "A person just opened
        # cybergod.ai" from the same /24 that had probed /.env: that stays suppressed. But a VPN or
        # cloud address IS often a real person (Kaspersky/Nord exit through M247, GB Network
        # Solutions, ...), so we do NOT suppress those - we LABEL them, or the operator (and every
        # privacy-conscious prospect) becomes invisible. OFFLINE, and fails open: `unknown` is a
        # person. `_infra_label` is threaded into the alert body below.
        _infra_label = ""
        try:
            from . import ip_reputation as _rep
            _cls = _rep.classify(ev.get("ip"))
            _rep.observe(ev.get("ip"), hostile=False, path=path)     # record every sighting
            if _rep.never_human(_cls):
                notify._log(evt="visit_suppressed",
                            reason="not a person (%s)" % _cls.get("kind"),
                            ip=ev.get("ip", "-"), path=path,
                            provider=_cls.get("provider") or "-", kind=_cls.get("kind"))
                return
            if _rep.is_infrastructure(_cls):
                _infra_label = " (via %s%s)" % (
                    _cls.get("kind"),
                    (": %s" % _cls.get("provider")) if _cls.get("provider") else "")
        except Exception:
            pass
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
            "A person just opened cybergod.ai.%s" % _infra_label,
            "",
            "When    : %s" % time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now)),
            "Page    : %s" % path,
            "IP      : %s%s%s" % (ip, (" (%s)" % ev.get("country")) if ev.get("country") not in (None, "", "-") else "", _infra_label),
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
