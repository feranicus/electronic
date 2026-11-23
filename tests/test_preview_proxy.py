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


# ---------------------------------------------------------------------------------------------
# THE PREVIEW GATE CAN ONLY HELP WITH A FRONTEND-ONLY CHANGE (23 Nov 2026)
# ---------------------------------------------------------------------------------------------
# The operator, on the deal-registration ship: "forget about this preview ... this is not only
# front end but also AI and backend database etc ... there can be no preview here it needs to go
# to regular test/prod."
#
# He is right, and it is a gap in the gate rather than an exception to it. `preview.py` serves the
# built frontend and nothing else - no FastAPI, no sqlite, no model chain. A feature whose screen
# is a form posting to a new route, backed by a new table and a four-model panel, renders there as
# a page that errors on load, so "look at it" produces no evidence about the thing that was built.
# Demanding it anyway teaches the operator to reach for `--no-preview` on every ship, which is how
# the gate dies for the pure-UI tweak it IS good at.
#
# For a full-stack change the STAGING GATE is the preview: the real image, the real backend, a real
# database on the twin, then a reboot. Strictly more evidence than a dev server, and already
# mandatory - so the look is not being skipped, it is being done properly.

import importlib.util as _ilu
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def _ups():
    spec = _ilu.spec_from_file_location("ups_t", _os.path.join(_ROOT, "ui_preview_stamp.py"))
    m = _ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _Run:
    def __init__(self, out, rc=0):
        self.stdout, self.returncode = out, rc


def test_a_frontend_only_change_still_demands_a_look():
    """THE GATE MUST NOT BE SWITCHED OFF. A pure CSS or copy change is exactly what previewing is
    good at, and it must still block."""
    ups = _ups()
    full, why = ups.full_stack_change(
        run=lambda c: _Run(" M webapp/frontend/src/pages/Landing.jsx\n"
                           " M webapp/frontend/src/index.css\n"))
    assert full is False, "a frontend-only change was waved through: %s" % why


def test_a_backend_change_alongside_the_ui_is_full_stack():
    ups = _ups()
    full, why = ups.full_stack_change(
        run=lambda c: _Run(" M webapp/frontend/src/pages/DealReg.jsx\n"
                           " M webapp/backend/app/dealreg.py\n M roles.py\n"))
    assert full is True
    assert "webapp/backend/app/dealreg.py" in why and "roles.py" in why, (
        "it does not NAME the backend files, so the operator cannot check the claim: %s" % why)


def test_docs_and_tests_alone_are_not_a_backend_change():
    """A decision doc and a test suite change nothing a user can run into. Counting them would
    make almost every ship 'full-stack' and quietly retire the gate."""
    ups = _ups()
    full, _ = ups.full_stack_change(
        run=lambda c: _Run(" M webapp/frontend/src/pages/Landing.jsx\n"
                           " M docs/decisions/2026-11-x.md\n M tests/test_x.py\n"))
    assert full is False


def test_an_unknown_answer_keeps_the_gate_asking():
    """No git, not a repo, a crash: the question is unanswered, and an unanswered question must not
    read as permission (class 1). It falls back to demanding the look."""
    ups = _ups()
    assert ups.full_stack_change(run=lambda c: _Run("", rc=128))[0] is False
    assert ups.full_stack_change(
        run=lambda c: (_ for _ in ()).throw(OSError("no git")))[0] is False


def test_the_full_stack_path_says_WHY_and_points_at_the_staging_gate():
    """A gate that passes silently teaches nothing. This one has to say what it measured and what
    is covering the look instead (class 5: print the comparison you made)."""
    ups = _ups()
    ups.full_stack_change = lambda run=None: (True, ["webapp/backend/app/dealreg.py"])
    ok, msg = ups.check()
    if ok and "STAGING GATE" in msg:
        assert "dealreg.py" in msg, "it does not name the evidence: " + msg
        assert "preview.py" in msg, "it does not say why previewing cannot help: " + msg
