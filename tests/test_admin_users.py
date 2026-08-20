"""Per-user credentials + the Administration page.

This is authentication code, so the tests assert PROPERTIES rather than the presence of strings:
what a wrong password does, what a disabled account does, what a broken store does, and who is
allowed to call the administrative routes. A test that greps for a variable name would pass against
a version of this feature that lets everybody in.

No httpx, no starlette.testclient (see the note in test_security_headers.py): the ASGI app is
called directly with the standard library so this runs on the operator's Windows Python too.
"""
import importlib
import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# RELOADING A MODULE OUTLIVES monkeypatch. These fixtures re-import colt_auth and user_store with
# a test environment; monkeypatch then restores the ENV VARIABLES but the modules keep the values
# they read at import time. That polluted test_auth.py: it set its own COLT_BOT_PASSWORD, got the
# one from this file, and two of its cases failed with "denied" - while passing in isolation, which
# is the signature of cross-test pollution. Reload once more on teardown so the next file imports a
# module built from ITS environment.
def _restore_modules():
    import colt_auth
    import user_store
    importlib.reload(user_store)
    importlib.reload(colt_auth)


@pytest.fixture()
def us(tmp_path, monkeypatch):
    """A user_store pointed at a scratch database, never the real one."""
    monkeypatch.setenv("USER_DB", str(tmp_path / "users.sqlite"))
    import user_store
    importlib.reload(user_store)
    yield user_store
    monkeypatch.undo()
    _restore_modules()


# ---------------------------------------------------------------------------------------------
# 1. THE CREDENTIAL STORE
# ---------------------------------------------------------------------------------------------

def test_the_plaintext_password_is_never_stored(us):
    us.set_password("a@s4biz.io", "correct horse battery")
    raw = open(us.db_path(), "rb").read()
    assert b"correct horse battery" not in raw, "the password is recoverable from the database file"
    # ...and no listing or lookup can hand it back either.
    assert "password" not in (us.get("a@s4biz.io") or {})
    assert all("password" not in r and "pw_hash" not in r for r in us.list_all())


def test_right_and_wrong_passwords(us):
    us.set_password("a@s4biz.io", "correct horse battery", must_change=False)
    assert us.check_password("a@s4biz.io", "correct horse battery") == (True, False)
    assert us.check_password("a@s4biz.io", "Correct horse battery") == (False, False)
    assert us.check_password("a@s4biz.io", "") == (False, False)
    assert us.check_password("nobody@s4biz.io", "correct horse battery") == (False, False)


def test_must_change_survives_until_the_user_changes_it(us):
    us.set_password("a@s4biz.io", "issued-by-the-admin", must_change=True)
    assert us.check_password("a@s4biz.io", "issued-by-the-admin") == (True, True)
    us.set_password("a@s4biz.io", "chosen-by-the-user", must_change=False)
    assert us.check_password("a@s4biz.io", "chosen-by-the-user") == (True, False)
    assert us.check_password("a@s4biz.io", "issued-by-the-admin")[0] is False, "the old one still works"


def test_a_disabled_account_cannot_log_in_and_does_not_fall_back(us):
    us.set_password("a@s4biz.io", "issued-by-the-admin", must_change=False)
    us.set_disabled("a@s4biz.io", True)
    assert us.check_password("a@s4biz.io", "issued-by-the-admin") == (False, False)
    # has_account must stay TRUE while disabled. If it went False, colt_auth would decide there is
    # no assigned password and admit the user on the SHARED one, which would make "disable" a
    # button that does nothing.
    assert us.has_account("a@s4biz.io") is True


def test_password_length_is_enforced(us):
    with pytest.raises(ValueError):
        us.set_password("a@s4biz.io", "short")


def test_generated_passwords_avoid_characters_that_get_misread(us):
    for _ in range(20):
        p = us.generate_password()
        assert len(p) >= us.MIN_PASSWORD_LEN
        assert not (set(p) & set("0O1lI")), "%r contains a character that is misread when relayed" % p


def test_delete_removes_the_credential(us):
    us.set_password("a@s4biz.io", "issued-by-the-admin")
    assert us.delete("a@s4biz.io") is True
    assert us.has_account("a@s4biz.io") is False
    assert us.delete("a@s4biz.io") is False


# ---------------------------------------------------------------------------------------------
# 2. THE GATE — which password wins, and what happens when the store breaks
# ---------------------------------------------------------------------------------------------

@pytest.fixture()
def ca(tmp_path, monkeypatch):
    monkeypatch.setenv("USER_DB", str(tmp_path / "users.sqlite"))
    monkeypatch.setenv("COLT_BOT_PASSWORD", "the-old-shared-secret")
    import user_store
    importlib.reload(user_store)
    import colt_auth
    importlib.reload(colt_auth)
    yield colt_auth
    monkeypatch.undo()
    _restore_modules()


def test_no_assigned_password_means_the_shared_one_still_works(ca):
    """The operator chose backward compatibility: nobody is locked out the moment this deploys."""
    assert ca.password_ok("someone@s4biz.io", "the-old-shared-secret") == (True, False)
    assert ca.password_ok("someone@s4biz.io", "wrong")[0] is False


def test_an_assigned_password_wins_and_the_shared_one_stops_working_for_them(ca):
    """This is what makes the Administration page mean anything: resetting or revoking one person
    cannot be sidestepped by falling back to the secret everybody knows."""
    import user_store
    user_store.set_password("named@s4biz.io", "their-own-password", must_change=False)
    assert ca.password_ok("named@s4biz.io", "their-own-password") == (True, False)
    assert ca.password_ok("named@s4biz.io", "the-old-shared-secret")[0] is False


def test_must_change_is_reported_through_the_gate(ca):
    import user_store
    user_store.set_password("named@s4biz.io", "issued-by-the-admin", must_change=True)
    assert ca.password_ok("named@s4biz.io", "issued-by-the-admin") == (True, True)


def test_a_broken_store_refuses_rather_than_promoting_everyone_to_the_shared_password(ca,
                                                                                      monkeypatch):
    """A database problem must not become an authentication bypass."""
    import user_store

    def boom(_e):
        raise RuntimeError("disk gone")

    monkeypatch.setattr(user_store, "has_account", boom)
    assert ca.password_ok("named@s4biz.io", "the-old-shared-secret") == (False, False)


def test_only_the_committed_administrator_is_an_administrator(ca):
    assert ca.is_admin("feranicus@s4biz.io") is True
    assert ca.is_admin("FERANICUS@S4BIZ.IO") is True, "the address is case-folded"
    for other in ("someone.else@s4biz.io", "ud@objectale.ch", "a.b@colt.net", "", None):
        assert ca.is_admin(other) is False, "%r must not be an administrator" % (other,)


def test_an_extra_administrator_can_be_added_without_a_code_change(tmp_path, monkeypatch):
    monkeypatch.setenv("USER_DB", str(tmp_path / "u.sqlite"))
    monkeypatch.setenv("EXTRA_ADMIN_EMAILS", "second@s4biz.io")
    import colt_auth
    importlib.reload(colt_auth)
    try:
        assert colt_auth.is_admin("second@s4biz.io") is True
        assert colt_auth.is_admin("feranicus@s4biz.io") is True, "the committed one still applies"
    finally:
        monkeypatch.undo()
        _restore_modules()          # same reason as the fixtures: a reload outlives monkeypatch


def test_the_allow_list_still_decides_who_may_exist(ca):
    """Per-user passwords are a SECOND factor of authorisation, not a replacement for the first."""
    import user_store
    user_store.set_password("stranger@example.com", "a-perfectly-good-password", must_change=False)
    assert ca.password_ok("stranger@example.com", "a-perfectly-good-password")[0] is True
    assert ca.email_allowed("stranger@example.com") is False, (
        "email_allowed is what Auth.begin checks alongside the password; an address off the list "
        "must not become reachable just because a credential exists for it")


# ---------------------------------------------------------------------------------------------
# 3. THE ROUTES — authorisation is server-side, not a hidden menu item
# ---------------------------------------------------------------------------------------------

def _src(rel):
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()


def _no_comments(s):
    return "\n".join(ln for ln in s.split("\n") if not ln.lstrip().startswith("#"))


def test_every_admin_route_is_gated_server_side():
    """Grep the CODE, not the comments: the prose in this file legitimately discusses the rule."""
    src = _no_comments(_src("webapp/backend/app/main.py"))
    blocks = src.split("@app.")
    admin = [b for b in blocks if '"/api/admin' in b.split("\n")[0]]
    assert len(admin) >= 4, "expected the admin routes; found %d" % len(admin)
    for b in admin:
        route = b.split("\n")[0]
        assert "_require_admin(request)" in b, "%s is not gated by _require_admin" % route


def test_the_forced_change_blocks_the_functional_endpoints():
    """_require_ready is the enforcement. Without it on these routes, a user who owes a password
    change could still run assessments with curl and a session cookie."""
    src = _no_comments(_src("webapp/backend/app/main.py"))
    for route in ('"/api/assess"', '"/api/compliance"', '"/api/history"', '"/api/assist"'):
        i = src.find(route)
        assert i > 0, "route %s not found" % route
        body = src[i:i + 1200]
        assert "_require_ready(request)" in body, "%s does not require a settled password" % route


def test_change_password_stays_reachable_while_a_change_is_owed():
    """Otherwise the forced state is a locked door with no handle."""
    src = _no_comments(_src("webapp/backend/app/main.py"))
    i = src.find('"/api/auth/change-password"')
    assert i > 0
    body = src[i:i + 1500]
    assert "_require_email(request)" in body
    assert "_require_ready(request)" not in body, (
        "change-password must NOT require a settled password; that is the state it exists to leave")


def test_must_change_is_read_from_the_store_not_from_the_session_cookie():
    """A flag baked into the cookie at login would survive the change itself."""
    src = _no_comments(_src("webapp/backend/app/main.py"))
    i = src.find("def _must_change(")
    assert i > 0
    body = src[i:i + 700]
    assert "user_store.get(" in body
    assert "read_session" not in body


def _request(path, method="GET", email=None, body=None):
    """Call the ASGI app directly, optionally carrying a real signed session cookie.

    THIS IS THE CHECK THAT MATTERS. The static greps below assert that the gate is WRITTEN; only a
    real request proves it is REACHED. A negative test showed the difference: renaming
    _require_admin's definition left every call site's text intact, so the grep still passed while
    the app would have raised NameError. Behaviour, not text.
    """
    import asyncio
    import json as _json
    sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
    from app import main
    from app.auth import make_session

    raw = _json.dumps(body or {}).encode()
    headers = [(b"host", b"testserver"), (b"content-type", b"application/json")]
    if email:
        headers.append((b"cookie", ("colt_session=" + make_session(email)).encode()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
             "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": b"",
             "root_path": "", "headers": headers,
             "client": ("127.0.0.1", 1), "server": ("testserver", 80)}
    got = {"status": 0, "body": b""}

    async def receive():
        return {"type": "http.request", "body": raw, "more_body": False}

    async def send(msg):
        if msg.get("type") == "http.response.start":
            got["status"] = msg["status"]
        elif msg.get("type") == "http.response.body":
            got["body"] += msg.get("body") or b""

    asyncio.run(main.app(scope, receive, send))
    try:
        got["json"] = _json.loads(got["body"] or b"{}")
    except Exception:
        got["json"] = {}
    return got


def test_a_non_admin_session_is_refused_by_every_admin_route():
    for path, method in (("/api/admin/users", "GET"),
                         ("/api/admin/users", "POST"),
                         ("/api/admin/users/x@y.com/disable", "POST"),
                         ("/api/admin/users/x@y.com", "DELETE")):
        r = _request(path, method, email="someone.else@s4biz.io",
                     body={"email": "new@s4biz.io"})
        assert r["status"] == 403, "%s %s allowed a non-administrator (%d)" % (
            method, path, r["status"])


def test_an_anonymous_caller_is_refused_by_every_admin_route():
    for path, method in (("/api/admin/users", "GET"), ("/api/admin/users", "POST")):
        r = _request(path, method, email=None, body={"email": "new@s4biz.io"})
        assert r["status"] in (401, 403), "%s %s leaked to an anonymous caller" % (method, path)


def test_the_administrator_can_actually_use_the_page(tmp_path, monkeypatch):
    """The mirror image: a gate that refuses everybody is not a gate either."""
    monkeypatch.setenv("USER_DB", str(tmp_path / "u.sqlite"))
    import user_store
    importlib.reload(user_store)
    r = _request("/api/admin/users", "GET", email="feranicus@s4biz.io")
    assert r["status"] == 200, "the administrator cannot open the page (%d)" % r["status"]
    assert "users" in r["json"]


def test_the_administrator_is_not_exempt_from_the_forced_change(tmp_path, monkeypatch):
    """Found by a negative test: _require_admin built on _require_email instead of _require_ready
    would have let an administrator who owes a password change carry on administering. The rule has
    to apply to the person who wrote it, or it is advice."""
    monkeypatch.setenv("USER_DB", str(tmp_path / "u.sqlite"))
    import user_store
    importlib.reload(user_store)
    sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
    from app import main
    monkeypatch.setattr(main, "user_store", user_store, raising=False)
    user_store.set_password("feranicus@s4biz.io", "issued-to-the-admin", must_change=True)
    r = _request("/api/admin/users", "GET", email="feranicus@s4biz.io")
    assert r["status"] == 403 and r["json"].get("detail") == "password_change_required", (
        "an administrator owing a password change still reached the admin page (%d %r)"
        % (r["status"], r["json"]))


def test_a_functional_endpoint_refuses_while_a_password_change_is_owed(tmp_path, monkeypatch):
    """The forced change is enforced by the SERVER, not by which screen the SPA renders."""
    monkeypatch.setenv("USER_DB", str(tmp_path / "u.sqlite"))
    import user_store
    importlib.reload(user_store)
    sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
    from app import main
    importlib.reload(main) if False else None      # module already imported; store is what changes
    _orig_us = main.user_store
    main.user_store = user_store                   # point main at the scratch store
    monkeypatch.setattr(main, "user_store", user_store, raising=False)
    del _orig_us                                    # monkeypatch owns the restore now
    user_store.set_password("owing@s4biz.io", "issued-by-the-admin", must_change=True)
    r = _request("/api/history", "GET", email="owing@s4biz.io")
    assert r["status"] == 403 and r["json"].get("detail") == "password_change_required", (
        "a user who owes a password change reached /api/history (%d %r)" % (r["status"], r["json"]))
    # ...and the change-password route itself must still be reachable, or it is a locked door.
    r2 = _request("/api/auth/change-password", "POST", email="owing@s4biz.io",
                  body={"new_password": "a-password-they-chose"})
    assert r2["status"] == 200, "change-password is blocked by the state it exists to leave (%d)" % r2["status"]
    assert user_store.check_password("owing@s4biz.io", "a-password-they-chose") == (True, False)


def test_api_me_reports_admin_and_must_change():
    import asyncio
    sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
    from app import main

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET",
             "scheme": "http", "path": "/api/me", "raw_path": b"/api/me", "query_string": b"",
             "root_path": "", "headers": [(b"host", b"testserver")],
             "client": ("127.0.0.1", 1), "server": ("testserver", 80)}
    got = {}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg.get("type") == "http.response.start":
            got["status"] = msg["status"]

    asyncio.run(main.app(scope, receive, send))
    assert got["status"] == 401, "anonymous /api/me must stay 401 — the deploy verifiers assert it"


# ---------------------------------------------------------------------------------------------
# 4. WIRING — a shared module reaches three images, not one
# ---------------------------------------------------------------------------------------------

def test_user_store_ships_in_every_image_that_ships_colt_auth():
    """colt_auth and user_store are one gate. An image with only half of it would silently fall
    back to the shared password for users who have their own."""
    for df in ("webapp/Dockerfile", "assess-bot/Dockerfile", "cassandra-bot/Dockerfile"):
        s = _src(df)
        if "colt_auth.py /opt/colt_auth.py" not in s:
            continue
        assert "user_store.py /opt/user_store.py" in s, (
            "%s copies colt_auth.py but not user_store.py" % df)


def test_the_build_context_is_not_filtered_out():
    """.dockerignore starts with `*`, so a file that is not whitelisted never reaches the build and
    the COPY above fails at image-build time."""
    s = _src(".dockerignore")
    assert "!user_store.py" in s, "user_store.py is excluded from the docker build context"


def test_every_root_file_a_dockerfile_copies_is_actually_packed_to_the_droplet():
    """THE FOURTH WIRING POINT, and the one that failed the staging build.

    deploy_web_direct.INCLUDE decides what is packed into the tarball sent to the droplet. It is a
    SEPARATE list from .dockerignore, and adding user_store.py to the Dockerfiles and to
    .dockerignore was not enough: the build died with
        COPY user_store.py /opt/user_store.py -> "/user_store.py": not found
    because the file was never shipped. Derived from the Dockerfiles rather than listed, so the
    next root-level module cannot repeat it.
    """
    import re as _re
    sys.path.insert(0, ROOT)
    import deploy_web_direct

    wanted = set()
    for df in ("webapp/Dockerfile", "assess-bot/Dockerfile", "cassandra-bot/Dockerfile"):
        for src_path in _re.findall(r"^COPY\s+(?:--from=\S+\s+)?(\S+)\s+\S+\s*$",
                                    _src(df), _re.M):
            # Root-level FILES only. Directories and paths inside them are covered by the
            # directory entries already in INCLUDE.
            if "/" not in src_path and os.path.isfile(os.path.join(ROOT, src_path)):
                wanted.add(src_path)
    assert wanted, "no root-level COPY sources found; the regex stopped matching the Dockerfiles"
    missing = sorted(f for f in wanted if f not in deploy_web_direct.INCLUDE)
    assert not missing, (
        "these files are COPYd by a Dockerfile but are NOT in deploy_web_direct.INCLUDE, so they "
        "never reach the droplet and the image build fails: %s" % missing)
