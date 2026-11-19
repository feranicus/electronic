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
import sys
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


def test_the_roster_matches_the_estate_exactly():
    """DOCTRINE CORRECTED 19 NOV 2026, ORIGINAL REASONING KEPT (class 17).

    This used to assert that jev.best, www.jev.best and the two klimaanlage domains were ON the
    roster, because they were being served and a vhost served but not expected can never be
    reported as MISSING when it disappears. That reasoning is still right and still enforced
    below for every LIVE site.

    What changed is the facts: those projects ended. klimaanlage-preise.de had been answering 502
    for weeks and jev.best was 502 on 19 Nov, which is what made `observemove.py --apply` refuse
    to start. A retired name left on the roster produces a MISSING warning on every single run,
    and a warning that fires every time is the thing that teaches you to read past the one that
    matters. So the rule is now two-sided and both sides derive from estate.py, which exists
    because this list had nine homes.
    """
    import importlib.util as u
    sys.path.insert(0, ROOT)
    import estate
    sp = u.spec_from_file_location("ag", os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    m = u.module_from_spec(sp)
    sp.loader.exec_module(m)
    for d in estate.expected_vhosts():
        assert d in m.EXPECT, "%s is live and not on the roster, so its death would be silent" % d
    for d in estate.RETIRED:
        assert d not in m.EXPECT, (
            "%s was retired on %s and is still expected, so every drift check reports it missing"
            % (d, estate.RETIRED[d][0]))
    assert sorted(m.EXPECT) == estate.expected_vhosts(), (
        "the roster and the estate disagree: %s" % sorted(set(m.EXPECT) ^ set(estate.LIVE)))
