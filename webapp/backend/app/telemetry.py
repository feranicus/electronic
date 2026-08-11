"""
telemetry.py — one JSON event per HTTP request hitting cybergod.ai.

Emits evt="http": ts · ip · country · method · path · status · ms · ua · browser · os · device ·
bot(true/false) · bot_name · ref · user(if signed in). Goes to stdout + EVENTS_LOG -> promtail ->
Loki -> Grafana. That is the "Visitor Log" table, plus everything the alert rules need.

PRIVACY (say it out loud): an IP address is personal data under GDPR/DSGVO. You are logging it for
security monitoring, which is a legitimate-interest basis — but it needs a retention limit, and Loki
retention is what enforces it here. Set TELEMETRY_HASH_IPS=1 to store a salted hash instead of the
raw IP (you keep 'same visitor?' correlation and lose the identifier). Raw is the default because
you asked for forensics.
"""
import asyncio, hashlib, json, os, re, time

EVENTS_LOG   = os.environ.get("EVENTS_LOG", "")
SERVICE      = os.environ.get("SERVICE", "colt-web")
HASH_IPS     = os.environ.get("TELEMETRY_HASH_IPS", "0") == "1"
IP_SALT      = os.environ.get("TELEMETRY_IP_SALT", "colt-cybergod")
# static assets would drown the log and tell us nothing about a visitor
SKIP_PATH_RE = re.compile(r"\.(css|js|map|png|jpe?g|svg|ico|woff2?|ttf)$", re.I)

_BOTS = [
    ("googlebot", "Googlebot"), ("bingbot", "Bingbot"), ("yandex", "YandexBot"),
    ("duckduckbot", "DuckDuckBot"), ("baiduspider", "Baiduspider"), ("slurp", "Yahoo Slurp"),
    ("ahrefs", "AhrefsBot"), ("semrush", "SemrushBot"), ("mj12bot", "MJ12bot"), ("dotbot", "DotBot"),
    ("petalbot", "PetalBot"), ("bytespider", "Bytespider"), ("gptbot", "GPTBot"),
    ("claudebot", "ClaudeBot"), ("ccbot", "CCBot"), ("perplexity", "PerplexityBot"),
    ("facebookexternalhit", "Facebook"), ("twitterbot", "Twitterbot"), ("linkedinbot", "LinkedInBot"),
    ("telegrambot", "TelegramBot"), ("whatsapp", "WhatsApp"), ("discordbot", "Discordbot"),
    # scanners / tooling — these are the interesting ones
    ("censys", "Censys"), ("shodan", "Shodan"), ("zgrab", "zgrab"), ("masscan", "masscan"),
    ("nmap", "nmap"), ("nuclei", "nuclei"), ("sqlmap", "sqlmap"), ("nikto", "Nikto"),
    ("dirbuster", "DirBuster"), ("gobuster", "gobuster"), ("wpscan", "WPScan"),
    ("curl", "curl"), ("wget", "wget"), ("python-requests", "python-requests"),
    ("go-http-client", "Go-http-client"), ("java/", "Java"), ("libwww-perl", "libwww-perl"),
    ("headlesschrome", "HeadlessChrome"), ("phantomjs", "PhantomJS"), ("scrapy", "Scrapy"),
]
_OS = [("windows nt 11", "Windows 11"), ("windows nt 10", "Windows 10"), ("windows", "Windows"),
       ("iphone", "iOS"), ("ipad", "iPadOS"), ("android", "Android"),
       ("mac os x", "macOS"), ("cros", "ChromeOS"), ("linux", "Linux")]
_BROWSER = [("edg/", "Edge"), ("opr/", "Opera"), ("chrome/", "Chrome"), ("firefox/", "Firefox"),
            ("safari/", "Safari")]


def client_ip(request):
    """Real client IP.
    Order: CF-Connecting-IP (set by Cloudflare when it fronts us) -> first X-Forwarded-For entry
    (videodead-caddy appends) -> socket peer. CF-Connecting-IP is authoritative when present because
    only Cloudflare sets it and it reaches us via the trusted Caddy hop."""
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "-")


def _maybe_hash(ip):
    if not HASH_IPS or not ip or ip == "-":
        return ip
    return "h:" + hashlib.sha256((IP_SALT + ip).encode()).hexdigest()[:16]


def _country(ip):
    """Country from the local DB-IP database. Never let geo lookup break a request."""
    try:
        try:
            from . import geoip
        except ImportError:
            import geoip
        return geoip.country(ip)
    except Exception:
        return "-"


def classify_ua(ua):
    u = (ua or "").lower()
    if not u.strip():
        return {"bot": True, "bot_name": "no-user-agent", "browser": "-", "os": "-", "device": "unknown"}
    for pat, name in _BOTS:
        if pat in u:
            return {"bot": True, "bot_name": name, "browser": "-", "os": "-", "device": "bot"}
    os_ = next((n for p, n in _OS if p in u), "-")
    br = next((n for p, n in _BROWSER if p in u), "-")
    device = "mobile" if ("mobile" in u or "iphone" in u or "android" in u) else \
             ("tablet" if "ipad" in u else "desktop")
    # a "browser" with no browser token and no OS is almost certainly tooling
    bot = (br == "-" and os_ == "-")
    return {"bot": bot, "bot_name": "unknown-client" if bot else "-",
            "browser": br, "os": os_, "device": device}


def emit(**k):
    k.setdefault("ts", time.time()); k.setdefault("service", SERVICE); k.setdefault("bot_svc", "webapp")
    line = json.dumps(k)
    try: print(line, flush=True)
    except Exception: pass
    if EVENTS_LOG:
        try:
            with open(EVENTS_LOG, "a") as fh: fh.write(line + "\n")
        except Exception: pass


def install(app, session_email_fn=None):
    """One middleware, every request. Must never break the request it observes."""
    from starlette.middleware.base import BaseHTTPMiddleware

    class _Telemetry(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            t0 = time.time()
            # Bot gate FIRST: classify the client and, if it is a crawler asking for the website,
            # answer 404 without ever touching the app. /api and /.well-known are exempt — see
            # visitors.py for why (the deploy verifiers assert 401 on /api/me).
            try:
                from . import visitors as _v
            except ImportError:
                _v = None
            cls = _v.classify(request) if _v else None

            # ACTIVE DEFENCE, BEFORE THE APP. shield.decide() is pure in-memory arithmetic over
            # what this IP has already done, so it costs microseconds and cannot call out to
            # anything. It is deliberately placed here, ahead of the bot gate, so a confirmed
            # scanner never reaches application code at all.
            # FAIL-OPEN BY CONSTRUCTION: every call is wrapped, and shield.decide() itself returns
            # ALLOW on any internal error. A security control that breaks the site is a worse
            # outage than the scanning it prevents.
            try:
                from . import shield as _sh
            except Exception:
                _sh = None
            if _sh is not None:
                try:
                    _ip = client_ip(request)
                    _verdict, _why = _sh.decide(_ip, request.url.path)
                    if _verdict == "BLOCK":
                        from starlette.responses import HTMLResponse
                        _safe_emit(request, 404, t0, session_email_fn, cls=cls, blocked=True)
                        return HTMLResponse(_v.NOT_FOUND_HTML if _v else "", status_code=404)
                    if _verdict == "TARPIT":
                        # Cheap for us, expensive for them: a scanner's throughput collapses while
                        # a mistaken human just sees a slow page. The concurrency cap inside
                        # tarpit_seconds() is what stops this becoming a self-inflicted DoS.
                        _delay = _sh.tarpit_seconds()
                        if _delay > 0:
                            _sh.enter_tarpit()
                            try:
                                await asyncio.sleep(_delay)
                            finally:
                                _sh.leave_tarpit()
                except Exception:
                    pass                                  # fail open, always

            if _v is not None and cls and _v.should_block(request.url.path, cls):
                from starlette.responses import HTMLResponse
                _safe_emit(request, 404, t0, session_email_fn, cls=cls, blocked=True)
                return HTMLResponse(_v.NOT_FOUND_HTML, status_code=404)
            try:
                response = await call_next(request)
                status = response.status_code
            except Exception:
                _safe_emit(request, 500, t0, session_email_fn, cls=cls)
                raise
            _safe_emit(request, status, t0, session_email_fn, cls=cls)
            if _sh is not None:
                try:
                    _ip = client_ip(request)
                    _pth = request.url.path
                    _sh.observe(_ip, _pth, status, cls or {}, request.method)
                    # PUBLIC SIEGE FEED. Only ATTACK-SHAPED requests, and the address is truncated
                    # inside siege.record() on the way in - an ordinary visitor never reaches it.
                    _lane = _sh.lane_of(_pth)
                    if _lane:
                        from . import siege as _sg
                        _cc = ""
                        try:
                            from . import geoip as _gi
                            _cc = _gi.country(_ip) or ""
                        except Exception:
                            pass
                        _sg.record(_ip, _pth, _lane, bool(_sh.is_blocked(_ip)), status, _cc)
                except Exception:
                    pass
            return response

    def _safe_emit(request, status, t0, fn, cls=None, blocked=False):
        try:
            path = request.url.path
            if SKIP_PATH_RE.search(path) and not blocked:
                return
            ua = request.headers.get("user-agent", "")
            c = cls or classify_ua(ua)
            ip = client_ip(request)
            user = ""
            try:
                if fn: user = fn(request) or ""
            except Exception:
                user = ""
            ev = dict(evt="http", ip=_maybe_hash(ip), method=request.method, path=path[:200],
                      status=status, ms=int((time.time() - t0) * 1000), ua=ua[:220],
                      browser=c["browser"], os=c["os"], device=c["device"],
                      bot=c["bot"], bot_name=c["bot_name"],
                      ref=(request.headers.get("referer") or "")[:160],
                      lang=(request.headers.get("accept-language") or "")[:40].split(",")[0],
                      # Caddy/Cloudflare-style country header if a proxy ever sets one
                      # Cloudflare provides the country for free (cf-ipcountry); DB-IP is the fallback
                      country=(request.headers.get("cf-ipcountry")
                               or request.headers.get("x-country")
                               or _country(ip)),
                      user=user)
            emit(**ev)
            try:
                try:
                    from . import alerts
                except ImportError:
                    import alerts
                alerts.observe_http(ev)      # rate rules live here, not in the request path logic
            except Exception:
                pass
            # who actually arrived: alert on a real person, log the bots we turned away
            try:
                try:
                    from . import visitors as _vv
                except ImportError:
                    import visitors as _vv
                if blocked:
                    _vv.note_block(ev, c)
                elif not c.get("bot"):
                    _vv.note_visit(ev, c)
            except Exception:
                pass
        except Exception:
            pass

    app.add_middleware(_Telemetry)
    return app
