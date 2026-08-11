"""Our own external monitoring must be able to SEE the site it monitors.

THE DEFECT THIS PINS. colt-web serves an unrecognised user agent a 404 on every PAGE route, so
scanners get nothing. Both external monitors sent a non-browser agent:
  · recover.py's OUTSIDE VIEW sent "cybergod-recover/1.0"  -> 404 on every ship, printed in the
    deploy log next to "5/5 endpoints answering";
  · .github/workflows/uptime.yml used a bare curl ("curl/8.x") -> and 404 had been ADDED to the
    ACCEPTED status set for www.cybergod.ai to make it stop complaining.
The second is the serious one: it is the ONE monitor that lives off-box, precisely because
everything on the droplet sits behind the proxy it is watching, and it would have called a
completely dead front page healthy.
Nth instance of the recurring disease: a check that cannot see its subject is not a check.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel, strip_comments=False):
    with open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as fh:
        s = fh.read()
    if strip_comments:
        # STRIP COMMENTS BEFORE GREPPING SOURCE. My first version of the check below matched
        # the COMMENT that explains the removed user agent and failed a correct file. The brand
        # gate learned this months ago; I did not carry it across.
        s = "\n".join(re.sub(r"#.*$", "", ln) for ln in s.splitlines())
    return s


def test_the_deploy_probe_announces_a_browser():
    s = _src("recover.py", strip_comments=True)
    assert "cybergod-recover/1.0" not in s, "the probe is bot-gated again and sees only 404s"
    d = s[s.index("def probe("):s.index("def probe(") + 400]
    assert "ua=" in d and "Mozilla" in _src("recover.py"), "probe() no longer sends a browser user agent"


def test_the_offbox_monitor_announces_a_browser():
    s = _src(".github/workflows/uptime.yml")
    assert 'UA="Mozilla' in s, "the uptime workflow lost its browser user agent"
    assert re.search(r'curl[^\n]*-A "\$UA"', s) or '-A "$UA"' in s, "curl no longer sends it"


def test_404_is_never_an_acceptable_answer_for_a_public_page():
    """This is the assertion that matters. Widening the expectation to match a bot-gated probe
    is how a monitor comes to accept an outage."""
    s = _src(".github/workflows/uptime.yml")
    for line in s.splitlines():
        line = line.strip()
        if not line.startswith('"') or "|http" not in line:
            continue
        name, url, want = line.strip('"').split("|", 2)
        assert "404" not in want, (
            "%s accepts HTTP 404 as healthy — a dead page would go unreported" % name)


def test_the_front_page_itself_is_monitored():
    """/api/me proves the backend and auth. It is EXEMPT from the bot gate, so it can pass while
    every human-facing page is broken. The page a customer actually opens needs its own target."""
    s = _src(".github/workflows/uptime.yml")
    assert "https://cybergod.ai/|^(200)$" in s.replace('"', ""), \
        "nothing monitors the cybergod.ai front page itself"


def test_the_roster_covers_every_domain_the_proxy_serves():
    """A benign warning on every run trains you to ignore the one that is not benign."""
    import importlib.util as u
    sp = u.spec_from_file_location("ag", os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    m = u.module_from_spec(sp)
    sp.loader.exec_module(m)
    for d in ("jev.best", "www.jev.best", "klimaanlage-montieren.de",
              "www.klimaanlage-montieren.de"):
        assert d in m.EXPECT, "%s is served but still not on the committed roster" % d
