"""The public siege feed must be incapable of publishing somebody's data.

This endpoint is WORLD-READABLE and it is fed by the same request stream that carries ordinary
visitors. An IP address is personal data under GDPR (CJEU C-582/14 Breyer), and an attacker
controls the path, which can carry a query string with an email, a token or a session id.
So the assertions here are not style: they are the reason the feature is allowed to exist.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))


def _fresh():
    import importlib
    from app import siege
    importlib.reload(siege)
    return siege


def test_a_full_ip_is_never_stored_let_alone_served():
    sg = _fresh()
    sg.record("203.0.113.77", "/wp-login.php", "wordpress", True, 404, "DE")
    blob = repr(sg.snapshot(None))
    assert "203.0.113.77" not in blob, "the full address reached the payload"
    assert "203.0.113.0/24" in blob, "the /24 is missing — redaction changed shape"
    # and it is not hiding in the buffer either: truncation happens on the way IN
    assert "203.0.113.77" not in repr(sg._buf)


def test_ipv6_is_truncated_too():
    sg = _fresh()
    sg.record("2001:db8:1234:5678::1", "/.env", "env_secrets", False)
    blob = repr(sg.snapshot(None))
    assert "5678" not in blob and "::1" not in blob.replace("::/48", ""), "IPv6 leaked host bits"
    assert "/48" in blob


def test_a_query_string_is_never_echoed():
    """The single highest-risk field. An attacker chooses it."""
    sg = _fresh()
    sg.record("198.51.100.9", "/wp-login.php?email=someone@example.com&token=abc123",
              "wordpress", True)
    blob = repr(sg.snapshot(None))
    for leak in ("someone@example.com", "token", "abc123", "?"):
        assert leak not in blob, "the query string reached the public feed: %r" % leak
    # NOTE FOR THE NEXT NEGATIVE TEST: this is guarded TWICE - the explicit "?" check and the
    # _SAFE_PATH character class, which also excludes "?". Removing either one alone leaves the
    # other holding, so a single-guard mutation passes and proves nothing. Defeat BOTH.


def test_a_weird_path_falls_back_to_the_class():
    sg = _fresh()
    sg.record("198.51.100.9", "/" + "A" * 400, "php_probe", True)
    ev = sg.snapshot(None)["events"][0]
    assert ev["path"] is None, "an unbounded path was echoed"
    assert ev["lane"] == "php_probe", "the class must still be reported"


def test_only_attack_shaped_requests_are_recorded():
    """An ordinary visitor must never appear, not even anonymised."""
    sg = _fresh()
    sg.record("198.51.100.9", "/app", None, False)
    sg.record("198.51.100.9", "/", None, False)
    sg.record("198.51.100.9", "/api/me", None, False)
    assert sg.snapshot(None)["events"] == [], "ordinary traffic entered the public feed"


def test_no_user_agent_no_user_no_session_in_the_payload():
    sg = _fresh()
    sg.record("198.51.100.9", "/.git/config", "env_secrets", True, 404, "NL")
    ev = sg.snapshot(None)["events"][0]
    assert set(ev) <= {"id", "lane", "net", "cc", "path", "blocked", "t"}, \
        "an unexpected field appeared in the public payload: %s" % sorted(ev)


def test_the_feed_is_bounded_and_cheap():
    sg = _fresh()
    for i in range(sg.MAX_EVENTS + 250):
        sg.record("198.51.100.%d" % (i % 250), "/wp-login.php", "wordpress", True)
    assert len(sg._buf) <= sg.MAX_EVENTS, "the ring buffer is unbounded"
    a = sg.snapshot(5)
    b = sg.snapshot(5)
    assert a is b, "the snapshot is not cached — a public endpoint that recomputes is a lever"


def test_one_class_vocabulary_not_two():
    """The table lived only in analyse_attacks.py, which is not in the image. Duplicating it is
    how ENRICH_MODELS ended up with four homes."""
    from app.shield import CLASSES, lane_of
    assert lane_of("/wp-login.php") == "wordpress"
    assert lane_of("/app") is None
    src = open(os.path.join(ROOT, "analyse_attacks.py"), encoding="utf-8").read()
    body = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    assert "CLASSES = [" not in body, "analyse_attacks.py re-declared the class table"
    assert "from app.shield import" in body, "it no longer imports the shared vocabulary"
    from app import siege
    assert set(siege.LANES) == {n for n, _ in CLASSES}, "the feed advertises a different lane set"


def test_the_endpoint_is_public_and_reads_only():
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    i = src.index('@app.get("/api/siege")')
    seg = src[i:i + 900]
    assert "Depends" not in seg and "require" not in seg, "the public feed grew an auth dependency"
    assert re.search(r"siege\.snapshot", seg), "the endpoint no longer serves the snapshot"
