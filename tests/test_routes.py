"""test_routes.py — a page is not shipped until every layer that must know about it knows.

THE DEFECT THIS EXISTS FOR. Adding a public page to the React app touches FOUR files that live in
three different languages, and nothing connected them:

  1. webapp/frontend/src/App.jsx            registers the route
  2. webapp/frontend/src/components/MoreMenu.jsx  is the only way to reach it on a phone
  3. webapp/backend/app/main.py::_APP_ROUTES      or the backend classifies it as a SCANNER PROBE
  4. webapp/frontend/public/sitemap.xml           or Google never learns the page exists

Miss (3) and the page is served a 404 to some clients and its visits are logged as suppressed
probes. Miss (4) and the page is invisible to search. Both fail silently and neither shows up in a
build, a render test or a browser check by the person who just added the page and knows the URL.

CLAUDE.md already recorded "_APP_ROUTES must list every App.jsx route (it was already stale)" and
then it went stale again with /partners, because writing a rule down is not enforcing it. This is
the enforcement. Same doctrine as tests/test_doc_lang.py: follow the VALUE across every hop and
assert it at each one, and match the CONCEPT rather than the one spelling you just fixed.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FE = os.path.join(ROOT, "webapp", "frontend")
APP = os.path.join(FE, "src", "App.jsx")
MENU = os.path.join(FE, "src", "components", "MoreMenu.jsx")
MAIN = os.path.join(ROOT, "webapp", "backend", "app", "main.py")
SITEMAP = os.path.join(FE, "public", "sitemap.xml")


def _read(p):
    return open(p, encoding="utf-8").read()


def _routes():
    """Every path App.jsx registers, as the first path segment (which is what the backend keys on)."""
    return [m.group(1) for m in re.finditer(r'<Route\s+path="([^"]+)"', _read(APP))]


def _seg(route):
    return route.strip("/").split("/")[0]


# Owner-scoped or otherwise deliberately absent from the public sitemap.
PRIVATE = {"login", "app"}
# Reachable from the header without the More menu (brand link, buttons, tab bar).
REACHED_ELSEWHERE = {"", "demo", "login", "app"}


def test_every_route_is_known_to_the_backend():
    """A route the backend does not know is classified as a scanner probe and served a 404."""
    src = _read(MAIN)
    m = re.search(r"_APP_ROUTES\s*=\s*\{(.*?)\}", src, re.S)
    assert m, "_APP_ROUTES not found in main.py"
    known = set(re.findall(r'"([^"]*)"', m.group(1)))
    missing = sorted({_seg(r) for r in _routes()} - known)
    assert not missing, (
        "these App.jsx routes are absent from _APP_ROUTES, so main.py::_is_probe treats them as "
        "scanner probes: %s. The page would 404 for some clients and its visits would be logged "
        "as suppressed probes." % missing)


def test_every_public_route_is_in_the_sitemap():
    """A page absent from the sitemap is a page Google is never told about."""
    sm = _read(SITEMAP)
    listed = set(re.findall(r"<loc>https://cybergod\.ai/([^<]*)</loc>", sm))
    listed = {x.strip("/") for x in listed}
    want = {_seg(r) for r in _routes()} - PRIVATE
    missing = sorted(want - listed)
    assert not missing, "public routes missing from sitemap.xml: %s" % missing
    # And the reverse: a sitemap entry for a route that no longer exists feeds Google a 404.
    dead = sorted(listed - {_seg(r) for r in _routes()})
    assert not dead, "sitemap.xml lists routes App.jsx does not register: %s" % dead


def test_every_public_route_is_reachable_from_the_header():
    """On a phone the More menu is the ONLY route to these pages: plain nav links are hidden by
    `#hd nav a:not(.btn){display:none}` and the bottom tab bar is already full at six items."""
    menu = set(re.findall(r'\{\s*to:\s*"([^"]+)"', _read(MENU)))
    want = {r for r in _routes() if _seg(r) not in REACHED_ELSEWHERE}
    orphan = sorted(want - menu)
    assert not orphan, (
        "these routes exist but no header control reaches them, so they are unreachable on a "
        "phone: %s" % orphan)
    dead = sorted(menu - set(_routes()))
    assert not dead, "MoreMenu links to routes App.jsx does not register: %s" % dead


def test_every_public_page_keeps_the_phone_tab_bar():
    """A phone user must never land on a page with no bottom navigation.

    THE DEFECT (operator, 9 Aug 2026): the tab bar lived only on the landing page, so tapping
    anything in the More menu, or Demo, or even the bar's own "Open" tab, produced a screen with no
    navigation at all. In a standalone PWA the Android back button is not always shown, so that was
    a dead end. It is the same failure the More menu itself was created to fix, one level up.

    The cabinet is excluded ON PURPOSE: it has its own bottom navigation and two docked bars would
    overlap. That is a real distinction, so the test states it rather than skipping /app quietly.
    """
    pages = os.path.join(FE, "src", "pages")
    # DERIVED, NOT LISTED. A hardcoded set goes stale the moment a cabinet page is added - which is
    # exactly what happened when Admin.jsx and ChangePassword.jsx arrived and this test failed for
    # them despite them being cabinet pages with the sidebar's own bottom bar. Cabinet.jsx's imports
    # ARE the definition of "a cabinet page", so read them.
    cab_src = _read(os.path.join(pages, "Cabinet.jsx"))
    CABINET = {"Cabinet.jsx"} | {m + ".jsx" for m in
                                 re.findall(r'import\s+\w+\s+from\s+"\./(\w+)\.jsx"', cab_src)}
    missing = []
    for f in sorted(os.listdir(pages)):
        if not f.endswith(".jsx") or f in CABINET:
            continue
        if "<TabBar" not in _read(os.path.join(pages, f)):
            missing.append(f)
    assert not missing, (
        "these public pages do not render <TabBar/>, so a phone user reaching them has no bottom "
        "navigation and no way back: %s" % missing)

    # And the reverse: the cabinet must NOT render it, or two docked bars overlap.
    for f in sorted(CABINET):
        p = os.path.join(pages, f)
        if os.path.exists(p) and "<TabBar" in _read(p):
            raise AssertionError(
                "%s renders the public TabBar, but the cabinet already has its own bottom "
                "navigation. Two fixed bars at the bottom cover each other." % f)


def test_the_sitemap_and_robots_agree_with_the_bot_gate():
    """A crawler allowed by robots.txt but 404'd by the bot gate just burns crawl budget."""
    robots = _read(os.path.join(FE, "public", "robots.txt"))
    assert "sitemap.xml" in robots.lower(), "robots.txt does not point at the sitemap"
    # The bot gate's exemption list lives in visitors.py::EXEMPT_EXACT, NOT in main.py. The first
    # version of this assertion read main.py and failed on a system that was correct, which is the
    # same defect it exists to prevent: a check aimed at the wrong subject cannot pass for the
    # right reason. Read the file that actually holds the rule.
    vis = _read(os.path.join(ROOT, "webapp", "backend", "app", "visitors.py"))
    m = re.search(r"EXEMPT_EXACT\s*=\s*\((.*?)\)", vis, re.S)
    assert m, "EXEMPT_EXACT not found in visitors.py"
    exempt = set(re.findall(r'"([^"]+)"', m.group(1)))
    for p in ("/robots.txt", "/sitemap.xml"):
        assert p in exempt, (
            "%s is not exempt from the bot gate. A crawler fetches it BEFORE it has identified "
            "itself, so 404-ing it silently kills indexing." % p)
