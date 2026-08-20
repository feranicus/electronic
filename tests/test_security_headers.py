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

class _CIDict(dict):
    """Case-insensitive lookup, because HTTP header names are case-insensitive (RFC 9110 5.1).

    Raw ASGI emits header names as LOWERCASE bytes. httpx was quietly giving us a case-insensitive
    mapping, so dropping it made every `headers.get("Content-Security-Policy")` return None while
    the header was present as `content-security-policy`. The middleware was correct; the harness
    was not - which is worth stating, because a test failing for a harness reason looks exactly
    like a test failing for a real one.
    """

    def get(self, key, default=None):
        return dict.get(self, str(key).lower(), default)

    def __contains__(self, key):
        return dict.__contains__(self, str(key).lower())

    def __getitem__(self, key):
        return dict.__getitem__(self, str(key).lower())


class _Resp(object):
    """Just enough of a response object for these assertions."""

    def __init__(self, status, headers):
        self.status_code = status
        self.headers = _CIDict(headers)


def _get(path, ua="pytest"):
    """Call the ASGI app DIRECTLY. No starlette.testclient, and therefore no httpx.

    WHY THIS IS NOT A TestClient. `starlette.testclient` imports httpx, which is NOT a dependency
    of this application - it is a dependency of starlette's *testing* helper. It happened to be
    present in the sandbox where these tests were written and is absent on the operator's Windows
    Python, so the first version of this file FAILED HIS SHIP with
    "The starlette.testclient module requires the httpx package to be installed."
    That is the same root cause CLAUDE.md already records for three wasted ships: a check
    validated in one toolchain and handed to another. Adding httpx to requirements.txt would put
    a test-only library in the production image; telling the operator to pip install it would be
    an operator step, which operating principle 1 forbids. Calling the ASGI app directly needs
    nothing beyond the standard library and the app itself, so it runs anywhere the app does.

    It also deliberately does NOT run the lifespan, so the digest/panel background loops never
    start during tests - which TestClient would have done.
    """
    import asyncio
    from app import main

    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
        "headers": [(b"host", b"testserver"), (b"user-agent", ua.encode())],
        "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    got = {"status": 0, "headers": {}}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg.get("type") == "http.response.start":
            got["status"] = msg["status"]
            got["headers"] = {k.decode("latin-1"): v.decode("latin-1")
                              for k, v in msg.get("headers") or []}

    asyncio.run(main.app(scope, receive, send))
    return _Resp(got["status"], got["headers"])


def test_headers_reach_a_real_response():
    r = _get("/api/me")
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
    r = _get("/api/me")
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
    r = _get("/.env")                      # a probe path: answered 404 by the gate
    assert r.status_code == 404
    assert r.headers.get("Content-Security-Policy"), (
        "a blocked-scanner 404 went out with no security headers")


def test_the_server_banner_does_not_advertise_a_version():
    """Version disclosure is free reconnaissance, and it is the first thing our OWN engine's
    banner detectors read on a customer estate."""
    v = _get("/api/me").headers.get("Server", "")
    assert not re.search(r"\d+\.\d+", v), "the Server header leaks a version: %r" % v


def test_setting_a_header_can_never_break_a_response():
    """Fail-open, like every other control here. A site taken down by its own hardening is a
    worse outage than the attack the hardening prevents."""
    s = _read(ROOT, "webapp", "backend", "app", "security_headers.py")
    body = s[s.index("class _SecurityHeaders"):]
    assert "except Exception" in body, "the header middleware has no fail-open guard"


# ---------------------------------------------------------------------------------------------
# 3. THE TEST SUITE MUST RUN ON THE OPERATOR'S MACHINE. This is the structural guard.
# ---------------------------------------------------------------------------------------------

def test_no_test_imports_a_library_the_app_does_not_declare():
    """A GREEN RUN IN THE DEV SANDBOX IS NOT EVIDENCE ABOUT THE OPERATOR'S BOX.

    The first version of this file used starlette.testclient, which imports httpx. httpx was
    present in the sandbox where it was written and absent on the operator's Windows Python, so
    `python ship.py` died with "The starlette.testclient module requires the httpx package" and
    refused to deploy - correctly. CLAUDE.md already records this exact root cause for three
    earlier wasted ships. Writing the rule down did not stop it happening a fourth time, so it is
    a test now.

    The rule: a test may import the standard library, pytest, anything in requirements.txt, and
    this repository's own modules. Nothing else. If a check needs a library the application does
    not ship, either the check is wrong or the library belongs in requirements - and putting a
    test-only library into the production image is its own defect.
    """
    declared = set()
    with open(os.path.join(ROOT, "webapp", "backend", "requirements.txt"), encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.split("#")[0].strip()
            if ln:
                declared.add(re.split(r"[=<>\[]", ln)[0].strip().lower())
    # Libraries that are only ever available because something else pulled them in. httpx is the
    # one that actually bit us; the others are the same shape and would bite the same way.
    NOT_OURS = {"httpx", "starlette.testclient", "anyio", "trio", "respx", "freezegun",
                "hypothesis", "faker", "responses"}
    offenders = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if not fn.startswith("test_") or not fn.endswith(".py"):
            continue
        src = _read(ROOT, "tests", fn)
        # Only real import statements. A docstring explaining why we do NOT use httpx is not an
        # import, and an earlier version of this check would have flagged the paragraph above it.
        for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", src, re.M):
            mod = m.group(1)
            top = mod.split(".")[0].lower()
            if mod.lower() in NOT_OURS or top in NOT_OURS:
                offenders.append("%s imports %s" % (fn, mod))
    assert not offenders, (
        "these tests need a library the application does not declare, so they cannot run on a "
        "machine that only installed requirements.txt: %s" % offenders)
    assert "fastapi" in declared and "starlette" in declared, (
        "requirements.txt no longer declares the web stack these tests exercise")


def test_the_asgi_harness_needs_nothing_beyond_the_standard_library():
    """Prove the replacement is actually dependency-free, rather than trusting that it is."""
    src = _read(ROOT, "tests", "test_security_headers.py")
    body = src[src.index("def _get("):src.index("def test_headers_reach_a_real_response")]
    code = "\n".join(ln for ln in body.splitlines() if not ln.strip().startswith("#"))
    code = re.sub(r'"""[\s\S]*?"""', "", code)          # drop the docstring before searching
    for mod in re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", code, re.M):
        assert mod.split(".")[0] in ("asyncio", "app"), (
            "the ASGI harness imports %s; it must need only the stdlib and the app itself" % mod)


def test_every_declared_runtime_dependency_is_installed_here():
    """A bare `pytest` run must fail LEGIBLY when the local interpreter is missing an app dependency.

    THE SIXTH INSTANCE OF ONE ROOT CAUSE. The suite imports the FastAPI app, so the app's own
    dependencies have to be importable on whatever machine runs the tests — but they are installed
    on the DROPLET by the Dockerfile and nothing installed them here. Adding `python-multipart` for
    the White Label upload gave the author a green run and the operator 21 failures, every one of
    them reading "Form data requires python-multipart", which looks like a code defect and is not.
    Same shape as the httpx incident, the esbuild incident and the os.uname() incident.

    `python ship.py` now installs anything missing before the tests run. This test is for the
    person who runs pytest directly: it names the package and the fix instead of letting fastapi
    raise from four frames deep inside a route decorator.
    """
    from importlib import metadata as md
    req = os.path.join(ROOT, "webapp", "backend", "requirements.txt")
    missing = []
    for raw in open(req, encoding="utf-8"):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name = line
        for sep in ("[", "<", ">", "=", "!", "~", ";", " "):
            name = name.split(sep, 1)[0]
        try:
            md.distribution(name.strip())
        except Exception:
            missing.append(line)
    assert not missing, (
        "webapp/backend/requirements.txt declares %d package(s) this interpreter does not have: %s\n"
        "The tests import the app, so they cannot pass without them. `python ship.py` installs them "
        "automatically; to do it by hand: pip install %s"
        % (len(missing), ", ".join(missing), " ".join('"%s"' % m for m in missing)))
