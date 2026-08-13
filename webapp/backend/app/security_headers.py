# -*- coding: utf-8 -*-
"""The security headers we were already reporting other people for not having.

HOW THIS WAS FOUND, because the honest version matters. A visitor alert arrived showing a real
iOS visitor with `Referrer: https://www.cybergod.ai/sw.js`. That is our own service worker: its
install handler calls `cache.addAll(["/", "/app", ...])`, and the browser attributes a fetch made
by a service worker to the SERVICE WORKER SCRIPT URL. Nothing was wrong. But looking at it, the
operator asked why nothing about the site was locked down, and the answer was worse than the
question: cybergod.ai sent NO HSTS, NO CSP, NO X-Frame-Options, NO X-Content-Type-Options, NO
Referrer-Policy and NO Permissions-Policy. Our own assessment engine had reported that exact
absence as a customer finding at abakus-tk.de. We were selling the observation and not making it.

WHY THIS IS IN THE APP AND NOT IN THE CADDYFILE. The proxy in front of us is SHARED with four
other sites, and on 2026-08-07 one bad edit to it took every domain on the box down together for
six hours. A header belongs to the application that knows what it serves, it ships inside the
image (so the engine-hash deploy verify covers it), and it can be tested with a TestClient in a
second. Editing the shared Caddyfile to add them would put five sites at risk to harden one.

WHAT A CSP ACTUALLY BUYS. `script-src 'self'` with no 'unsafe-inline' is the single largest XSS
mitigation available: it means an injected <script>, or an injected onclick=, does not run. It
cost one change to earn - defense.html's 20KB inline block moved to /defense.js - and that is
the whole reason the extraction was worth doing. Everything else here is cheap by comparison.

FAIL-OPEN, LIKE EVERY OTHER CONTROL HERE. Setting a header must never be able to break a
response. The whole body is wrapped; on any error the response goes out exactly as it was.
"""
import os

# --------------------------------------------------------------------------------------------
# THE POLICY. Every origin below is one the site DEMONSTRABLY loads; test_security_headers.py
# reads index.html and the stylesheet and fails if the page reaches an origin not listed here,
# or if this list grows an origin the page does not use. A CSP written from memory is a CSP that
# either breaks the site or permits things nobody checked.
# --------------------------------------------------------------------------------------------
FONT_CSS = "https://fonts.googleapis.com"
FONT_FILES = "https://fonts.gstatic.com"

CSP = "; ".join([
    "default-src 'self'",
    # No inline script, no eval, no CDN. An injected <script> or onclick= does not execute.
    "script-src 'self'",
    # 'unsafe-inline' IS required for styles: React writes style="..." attributes on elements,
    # and a nonce cannot be applied to an attribute. Inline CSS is a far smaller hazard than
    # inline script - it cannot call an API or read a cookie.
    "style-src 'self' 'unsafe-inline' " + FONT_CSS,
    "font-src 'self' data: " + FONT_FILES,
    "img-src 'self' data: blob:",
    "media-src 'self'",                    # the Cassandra hero video, same origin
    "connect-src 'self'",                  # XHR/fetch/EventSource: the SSE assessment stream
    "worker-src 'self'",                   # the service worker in the alert that started this
    "manifest-src 'self'",
    "object-src 'none'",                   # no Flash/applets, ever
    "frame-src 'none'",
    "frame-ancestors 'none'",              # modern clickjacking defence
    "base-uri 'none'",                     # stops <base href> hijacking every relative URL
    "form-action 'self'",                  # a stolen form cannot POST credentials off-site
    "upgrade-insecure-requests",
])

# Two years, subdomains included. NOT preloaded by default: submission to hstspreload.org is a
# one-way door that is slow and awkward to reverse, so it is a deliberate decision, taken once,
# rather than a side effect of deploying. Set HSTS_PRELOAD=1 when that decision is made.
_HSTS = "max-age=63072000; includeSubDomains"
if os.environ.get("HSTS_PRELOAD") == "1":
    _HSTS += "; preload"

HEADERS = {
    "Content-Security-Policy": CSP,
    "Strict-Transport-Security": _HSTS,
    "X-Content-Type-Options": "nosniff",          # stop MIME sniffing a .txt into a script
    "X-Frame-Options": "DENY",                    # legacy twin of frame-ancestors
    # The header in the alert that started this. Cross-origin, send only the origin - so an
    # outbound click never tells a third party which page, job or deck the user was looking at.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": ("accelerometer=(), autoplay=(self), camera=(), display-capture=(), "
                          "geolocation=(), gyroscope=(), magnetometer=(), microphone=(), "
                          "midi=(), payment=(), usb=(), xr-spatial-tracking=()"),
    "Cross-Origin-Opener-Policy": "same-origin",  # process isolation from any opener
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
    # Version disclosure is free reconnaissance. It is also the FIRST thing our own engine's
    # banner detectors read on a customer's estate.
    "Server": "cybergod",
}

# Anything under these prefixes is owner-scoped or live, and must never sit in a shared cache.
# The service worker already refuses to cache /api (see public/sw.js); this is the server side of
# the same rule, and it also covers caches we do not control - a corporate proxy, a CDN, a phone.
NO_STORE_PREFIXES = ("/api/",)


def install(app):
    """Outermost middleware: it must also decorate the 404s the shield and bot gate return.

    Starlette builds the stack so the LAST middleware added is the OUTERMOST, so this call has to
    come after telemetry.install(app) in main.py. test_security_headers.py asserts that ordering,
    because getting it wrong would silently leave every blocked-scanner response bare.
    """
    from starlette.middleware.base import BaseHTTPMiddleware

    class _SecurityHeaders(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            try:
                for k, v in HEADERS.items():
                    response.headers[k] = v
                path = request.url.path
                if any(path.startswith(p) for p in NO_STORE_PREFIXES):
                    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
                    response.headers["Pragma"] = "no-cache"
            except Exception:
                pass          # a header is never worth failing a response over
            return response

    app.add_middleware(_SecurityHeaders)
