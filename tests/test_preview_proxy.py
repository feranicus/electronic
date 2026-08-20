"""The local preview's read-only rail: what it lets through, and what it must never let through.

WHY THIS FILE EXISTS. The guard originally refused EVERY non-GET request, which also refused
POST /api/auth/begin — so no logged-in page could be opened in the preview at all, and the standing
rule "look at a UI change before shipping it" was unfollowable for the whole cabinet. The operator
hit it directly. Narrowing a security rail is exactly the kind of change that quietly widens later,
so the allow-list is pinned here.

The rail is enforced in vite.config.js, which is JavaScript. These tests read that file rather than
run it: node is not guaranteed on the machine running pytest, and the property being asserted is
"which paths are on the list", which is a fact about the source. The behavioural half (a real POST
being destroyed) is exercised by running the dev server, which is what the operator does.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "webapp", "frontend", "vite.config.js")


def _src():
    return open(CFG, encoding="utf-8").read()


def _allow_list():
    s = _src()
    i = s.find("const ALLOW_WRITE")
    assert i > 0, "the preview proxy has no ALLOW_WRITE list; the rail may have been removed"
    block = s[i:s.find("]", i)]
    return set(re.findall(r'"(/api/[^"]+)"', block))


def test_signing_in_is_allowed_so_logged_in_pages_can_be_looked_at():
    allow = _allow_list()
    for p in ("/api/auth/begin", "/api/auth/verify"):
        assert p in allow, (
            "%s is refused by the preview, so no cabinet page can be opened locally and the "
            "look-before-you-ship rule cannot be followed" % p)


def test_everything_with_a_cost_or_a_consequence_is_still_refused():
    """The rail exists so a stray click in a colour preview cannot spend money or change an
    account. These are the paths that would."""
    allow = _allow_list()
    for p in ("/api/assess", "/api/compliance",
              "/api/admin/users", "/api/auth/change-password"):
        assert p not in allow, (
            "%s is on the preview's write allow-list; a local page could now spend credits or "
            "change a real account on the live site" % p)


def test_the_allow_list_is_matched_exactly_not_by_prefix():
    """A prefix match on '/api/auth' would silently admit /api/auth/change-password, which is a
    real credential change and belongs on the live site."""
    s = _src()
    assert "ALLOW_WRITE.has(path)" in s, (
        "the allow-list is not matched with an exact Set lookup; a startsWith/prefix test would "
        "admit paths nobody put on the list")
    assert "startsWith" not in s.split("ALLOW_WRITE")[1][:600], (
        "a prefix match crept into the preview's write guard")


def test_the_guard_still_refuses_by_default():
    """The default must remain DENY: only the listed paths pass, everything else is destroyed."""
    s = _src()
    i = s.find("proxy.on(\"proxyReq\"")
    assert i > 0
    body = s[i:i + 900]
    assert "proxyReq.destroy()" in body, "the preview no longer refuses unlisted writes"
    assert "res.writeHead(405" in body, "a refused write no longer says why"


def test_the_guard_only_applies_when_pointed_at_a_remote_target():
    """Against a LOCAL backend there is nothing to protect and the preview must behave normally."""
    s = _src()
    assert "if (!READONLY) return;" in s, (
        "the read-only guard is unconditional; running the preview against a local backend would "
        "then refuse writes for no reason")
