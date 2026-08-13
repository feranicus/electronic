"""We reported a customer for having none of these. We had none of them either.

The finding, in our own words, from the abakus-tk.de engagement in CLAUDE.md:
    "Set-Cookie: ZPORTALSESSID with no Secure and no SameSite, and no HSTS, CSP, X-Frame-Options
     or X-Content-Type-Options at all."
cybergod.ai sent exactly the same nothing, for months, while selling the observation.

THE HARD PART OF A CSP IS NOT WRITING IT, IT IS NOT BREAKING THE SITE. So the central test here
does not check that a policy exists - it reads the FRONTEND'S OWN SOURCE, extracts every external
origin the pages actually load, and requires the policy to permit each one. A CSP written from
memory either blocks a font the site needs, or quietly permits an origin nobody checked. Both are
found by comparing the policy against the artifact instead of against an intention.

Every assertion is negative-tested.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
FE = os.path.join(ROOT, "webapp", "frontend")

from app import security_headers as SH  # noqa: E402


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def _directive(name):
    for part in SH.CSP.split(";"):
        part = part.strip()
        if part == name or part.startswith(name + " "):
            return part[len(name):].strip()
    return None


# ---------------------------------------------------------------------------------------------
# 1. THE POLICY MUST MATCH THE SITE. Measured against the frontend, not against a belief.
# ---------------------------------------------------------------------------------------------

def test_every_origin_the_frontend_loads_is_permitted():
    """Read the real pages and stylesheet; require the CSP to allow what they reach for."""
    blob = ""
    for rel in ("index.html", "src/styles.css", "public/defense.html"):
        p = os.path.join(FE, rel)
        if os.path.exists(p):
            blob += _read(p)
    origins = set(re.findall(r"https://[a-z0-9.-]+\.[a-z]{2,}", blob))
    # Only an <a href> is a NAVIGATION, which no fetch directive governs. This exclusion was
    # first written as a bare href= and therefore also swallowed
    #     <link href="https://fonts.googleapis.com/css2?..." rel="stylesheet">
    # which is a SUBRESOURCE and is exactly what a bad style-src breaks. The negative test caught
    # it: removing the fonts origin from the policy changed nothing, because the check could not
    # see it. Anchor on the element, never on the attribute.
    linked = set(re.findall(r'<a\s[^>]*href="(https://[a-z0-9.-]+\.[a-z]{2,})', blob))
    schema_only = {"https://schema.org", "https://cybergod.ai", "https://www.cybergod.ai"}
    loaded = {o for o in origins if o not in linked and o not in schema_only}
    for o in loaded:
        assert o in SH.CSP, (
            "the frontend loads %s and the CSP does not permit it, so that request will be "
            "BLOCKED in the browser. Add it to the matching directive or stop loading it." % o)


def test_the_policy_permits_nothing_the_site_does_not_use():
    """The other direction. A permitted origin nobody uses is an unreviewed hole."""
    blob = "".join(_read(os.path.join(FE, r)) for r in ("index.html", "src/styles.css")
                   if os.path.exists(os.path.join(FE, r)))
    for o in re.findall(r"https://[a-z0-9.-]+\.[a-z]{2,}", SH.CSP):
        assert o in blob, (
            "the CSP permits %s but nothing in the frontend loads it; remove it rather than "
            "carrying a permission no one can justify" % o)


def test_script_src_forbids_inline_and_eval():
    """This is the directive that actually stops an injected <script> from running. Everything
    else in the policy is worth less than this one line."""
    s = _directive("script-src")
    assert s is not None, "there is no script-src at all"
    for bad in ("'unsafe-inline'", "'unsafe-eval'", "data:", "*"):
        assert bad not in s, "script-src permits %s, which defeats the point of having one" % bad


def test_no_page_carries_an_inline_script_that_the_policy_would_block():
    """defense.html shipped a 20KB inline block. Under script-src 'self' the page would have been
    a black rectangle in production and green in every test. JSON-LD is exempt: a script element
    whose type is not a JavaScript MIME type is a data block, is never executed, and CSP's script
    directives do not apply to it."""
    for rel in ("index.html", "public/defense.html"):
        p = os.path.join(FE, rel)
        if not os.path.exists(p):
            continue
        html = _read(p)
        for m in re.finditer(r"<script([^>]*)>([\s\S]*?)</script>", html):
            attrs, body = m.group(1), m.group(2).strip()
            if "src=" in attrs or "application/ld+json" in attrs:
                continue
            assert not body, (
                "%s has an executable inline <script> (%d chars); script-src 'self' will block "
                "it. Move it to its own file, as defense.js already is." % (rel, len(body)))
        assert not re.search(r"<[a-z]+[^>]*\son(click|load|error|mouse\w+)=", html), (
            "%s has an inline event handler attribute, which script-src 'self' blocks" % rel)


def test_the_hard_directives_are_all_present():
    for d, want in (("frame-ancestors", "'none'"), ("object-src", "'none'"),
                    ("base-uri", "'none'"), ("form-action", "'self'"),
                    ("default-src", "'self'")):
        assert _directive(d) == want, "%s should be %s, is %r" % (d, want, _directive(d))


# ---------------------------------------------------------------------------------------------
# 2. THE HEADERS THEMSELVES, on a real response from the real app.
# ---------------------------------------------------------------------------------------------

def _client():
    from starlette.testclient import TestClient
    from app import main
    return TestClient(main.app)


def test_headers_reach_a_real_response():
    r = _client().get("/api/me")
    assert r.status_code == 401, "the deploy verifiers assert 401 here; that must not change"
    for h in ("Content-Security-Policy", "Strict-Transport-Security", "X-Content-Type-Options",
              "X-Frame-Options", "Referrer-Policy", "Permissions-Policy",
              "Cross-Origin-Opener-Policy"):
        assert r.headers.get(h), "%s is missing from a live response" % h
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "max-age=" in r.headers["Strict-Transport-Security"]


def test_owner_scoped_api_responses_are_never_cached():
    """The service worker already refuses to cache /api. This is the server half of that rule,
    and it also binds caches we do not control: a corporate proxy, a CDN, a phone."""
    r = _client().get("/api/me")
    cc = r.headers.get("Cache-Control", "")
    assert "no-store" in cc, "an owner-scoped API response is cacheable: %r" % cc


def test_a_blocked_scanner_response_is_decorated_too():
    """The shield and the bot gate return 404 BEFORE the app runs. If the header middleware were
    installed inside them, every one of those responses would go out bare - which is most of our
    traffic. Starlette makes the LAST middleware added the OUTERMOST, so the order is the test."""
    s = _read(ROOT, "webapp", "backend", "app", "main.py")
    i_tel = s.index("_telemetry.install(")
    i_sec = s.index("_sec.install(")
    assert i_sec > i_tel, (
        "security_headers.install() runs BEFORE telemetry.install(), so it is the INNER "
        "middleware and cannot decorate the 404s the shield returns")
    r = _client().get("/.env")                      # a probe path: answered 404 by the gate
    assert r.status_code == 404
    assert r.headers.get("Content-Security-Policy"), (
        "a blocked-scanner 404 went out with no security headers")


def test_the_server_banner_does_not_advertise_a_version():
    """Version disclosure is free reconnaissance, and it is the first thing our OWN engine's
    banner detectors read on a customer estate."""
    v = _client().get("/api/me").headers.get("Server", "")
    assert not re.search(r"\d+\.\d+", v), "the Server header leaks a version: %r" % v


def test_setting_a_header_can_never_break_a_response():
    """Fail-open, like every other control here. A site taken down by its own hardening is a
    worse outage than the attack the hardening prevents."""
    s = _read(ROOT, "webapp", "backend", "app", "security_headers.py")
    body = s[s.index("class _SecurityHeaders"):]
    assert "except Exception" in body, "the header middleware has no fail-open guard"
