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

# THE CONTRADICTION CHECK'S BIT VALUES HAVE ONE HOME AND THIS IS NOT IT. Imported, both ways,
# because this module is loaded as `app.telemetry` in the container and as bare `telemetry` by the
# tests. If it cannot be imported at all the `sf` field is simply not written, which the reader
# renders as NOT DETERMINABLE -- a missing field is honest, a locally invented bit order is drift.
try:
    from . import client_truth
except ImportError:                      # standalone import (tests)
    try:
        import client_truth
    except ImportError:
        client_truth = None

# THE ASSET LEDGER, same both-ways import and the same degradation. If it cannot be imported the
# `av` field is simply not written, which the reader renders as "we never looked" -- and since the
# signal is one-way positive, losing it costs some addresses their CONFIRMED badge and costs
# nobody anything else. It can never turn an address into a client by being absent.
try:
    from . import asset_trace
except ImportError:                      # standalone import (tests)
    try:
        import asset_trace
    except ImportError:
        asset_trace = None

EVENTS_LOG   = os.environ.get("EVENTS_LOG", "")
SERVICE      = os.environ.get("SERVICE", "colt-web")
HASH_IPS     = os.environ.get("TELEMETRY_HASH_IPS", "0") == "1"
IP_SALT      = os.environ.get("TELEMETRY_IP_SALT", "colt-cybergod")
# static assets would drown the log and tell us nothing about a visitor
# A SUBRESOURCE IS NOT A PAGE VISIT.
# 2026-08-22: the operator was alerted that "a person just opened cybergod.ai" with the page given
# as `/manifest.webmanifest`. A real person HAD opened the site (the referrer proves it) and their
# browser then fetched the PWA manifest, but the alert named the manifest as the page they
# visited. `.webmanifest` was simply not in this list. Same class as the `sw.js` referrer alert
# already recorded: the browser fetches things on the visitor's behalf and those fetches are not
# navigations. Extensions added: webmanifest, webp/avif/gif (images), mp4/webm (the hero video),
# json/txt/xml (manifests, robots, sitemap) and eot/otf (fonts).
#
# THE PATTERN IS A NAMED LITERAL, not an inline argument to re.compile, because it now has a SECOND
# reader. perseus/client.py cannot import this module (it is copied into projects that do not have
# it) so it restates the pattern, and `test_asset_trace.py` reads both files off disk with `ast` and
# fails the build if the two ever drift. A literal can be compared; a compiled object cannot.
SKIP_PATH_PAT = (r"\.(css|js|mjs|map|png|jpe?g|gif|webp|avif|svg|ico|woff2?|ttf|otf|eot"
                 r"|webmanifest|mp4|webm|json|txt|xml)$")
SKIP_PATH_RE = re.compile(SKIP_PATH_PAT, re.I)

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


def _proto(request):
    """-> (version, source). WHOSE version it is travels WITH it, or it is not a measurement.

    A diagnostic that does not name its subject sends the next investigation down the wrong road,
    and this field has two possible subjects. The shared Caddy terminates TLS and opens a FRESH
    upstream connection to colt-web, and uvicorn implements no HTTP/2 at all, so the ASGI scope's
    `http_version` is "1.1" for a Chrome visitor and for a Go program alike: it describes the last
    hop, not the client. If the proxy is ever configured to forward what the client actually spoke
    (`header_up X-Client-Proto {http.request.proto}`), THAT is a fact about the client and is
    stamped `p`. client_truth.py refuses to draw any conclusion from an `s`.

    Never raises: this runs inside the observer of every request.
    """
    try:
        fwd = request.headers.get(client_truth.HV_CLIENT_HEADER) if client_truth else None
        if fwd:
            return (str(fwd)[:12], client_truth.HV_FROM_CLIENT)
    except Exception:
        pass
    try:
        v = (request.scope or {}).get("http_version")
        if not v:
            return (None, None)
        return (str(v)[:12], client_truth.HV_FROM_HOP if client_truth else "s")
    except Exception:
        return (None, None)


def _sf(request):
    """-> the fetch-metadata presence bitmask, or None when we could not look. Never raises."""
    if client_truth is None:
        return None
    try:
        return client_truth.sf_mask(request.headers.get)
    except Exception:
        return None


def _av(ip):
    """-> distinct assets this address has fetched recently, or None when we could not look.

    ONE-WAY POSITIVE. A count at or above asset_trace.MIN_ASSETS CONFIRMS a browser engine; a zero
    confirms nothing, because a first navigation, a cached repeat visit and an inline page all
    produce a zero. `av` ABSENT and `av == 0` are different facts, exactly as `sf` already
    distinguishes them, so None is returned when the ledger is unavailable and the field is then
    omitted rather than defaulted. Never raises.
    """
    if asset_trace is None:
        return None
    try:
        return int(asset_trace.evidence(ip))
    except Exception:
        return None


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
                    # A SIGNED SESSION IS A KNOWN HUMAN, so the shield is told before it decides.
                    # Without this the operator was served our own branded 404 on /app/admin while
                    # logged in as the administrator, with no message anywhere -- see
                    # shield.decide() for the elimination that identified it. A request carrying no
                    # cookie costs a dict lookup, so a scanner flood never reaches the verify.
                    _authed = False
                    try:
                        _authed = bool(session_email_fn(request))
                    except Exception:
                        _authed = False
                    _verdict, _why = _sh.decide(_ip, request.url.path, authed=_authed)
                    if _verdict == "TARPIT" and _authed:
                        # Slowing a logged-in operator's own console to a crawl is the same lockout
                        # in a politer form, and it would be just as silent.
                        _verdict = "ALLOW"
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
                # OBSERVE BEFORE RETURNING. This early return used to skip shield.observe()
                # entirely, so every request the bot gate handled left NO TRACE in the shield's
                # memory: a self-declared scanner could enumerate the site forever and never
                # accumulate a single hit, because the thing that answered it never told the thing
                # that counts. Fourth instance of "an exemption became a blind spot" in this
                # codebase, this time at the middleware layer rather than inside a matcher.
                try:
                    if _sh is not None:                   # already imported above; do NOT invent
                        _sh.observe(client_ip(request), request.url.path, 404, cls or {},
                                    request.method)
                except Exception:
                    pass                                  # fail open, always
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
                # THE ONE THING THIS EARLY RETURN USED TO THROW AWAY. A subresource is not a page
                # visit and must not be logged as one -- that part is unchanged and the line is
                # still not written -- but the FACT that this address pulled the bundle, the
                # stylesheet and the icons is the strongest server-side proof there is that a
                # browser engine rendered the page it was given. Recorded in memory, costing zero
                # log lines, and read back below as `av`. ONE-WAY POSITIVE: see asset_trace.py.
                if asset_trace is not None:
                    try:
                        asset_trace.note(client_ip(request), path)
                    except Exception:
                        pass              # fail open, always
                return
            ua = request.headers.get("user-agent", "")
            c = cls or classify_ua(ua)
            ip = client_ip(request)
            user = ""
            try:
                if fn: user = fn(request) or ""
            except Exception:
                user = ""
            # ---- EVIDENCE THAT IS NOT FREE TO FAKE, alongside the claim that is ------------------
            # `bot` below is a substring match on an attacker-controlled header. These two fields
            # are what a caller compares it against; see client_truth.py for why each one is only
            # evidence under a stated condition. Written unconditionally so that "we looked and the
            # client sent none" (sf == 0) stays distinguishable from "nobody ever looked" (no sf
            # key at all), which is the whole basis of the unknown column on the fleet page.
            hv, hvs, sf = _proto(request) + (_sf(request),)
            ev = dict(evt="http", ip=_maybe_hash(ip), method=request.method, path=path[:200],
                      status=status, ms=int((time.time() - t0) * 1000), ua=ua[:220],
                      browser=c["browser"], os=c["os"], device=c["device"],
                      bot=c["bot"], bot_name=c["bot_name"],
                      hv=hv, hvs=hvs, sf=sf, av=_av(ip),
                      ref=(request.headers.get("referer") or "")[:160],
                      lang=(request.headers.get("accept-language") or "")[:40].split(",")[0],
                      # Caddy/Cloudflare-style country header if a proxy ever sets one
                      # Cloudflare provides the country for free (cf-ipcountry); DB-IP is the fallback
                      country=(request.headers.get("cf-ipcountry")
                               or request.headers.get("x-country")
                               or _country(ip)),
                      user=user)
            # A FIELD WE COULD NOT MEASURE IS OMITTED, NEVER WRITTEN AS A DEFAULT. `sf: 0` means
            # the client sent no fetch-metadata header; `sf` absent means client_truth could not be
            # imported and nobody looked. Writing 0 for the second would manufacture a signal out
            # of our own failure, which is the "absence of evidence is never a finding" rule at the
            # emitter instead of at the reader. `av` obeys the same rule for the same reason --
            # though `av: 0` is not a signal in EITHER direction, since the ledger only ever
            # confirms a browser and never accuses one.
            for _k in ("hv", "hvs", "sf", "av"):
                if ev.get(_k) is None:
                    ev.pop(_k, None)
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
