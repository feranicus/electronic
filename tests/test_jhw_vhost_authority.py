"""www.jobhw.org went dark for six days because a fallback chose itself quietly.

THE OUTAGE, 2026-10-16 to 2026-10-22. www.jobhw.org answered ERR_SSL_PROTOCOL_ERROR. The last
visitor alert for it is timestamped 2026-10-16 12:03 UTC, which is the day production deploys
moved into GitHub Actions.

THE CHAIN, measured rather than reconstructed:

  * jobhuntwow's authoritative Caddy block lives in the SIBLING project,
    jobhuntwow-app/deploy/caddy/jobhuntwow.caddy, and declares three hosts:
        www.jobhuntwow.com, jobhw.org, www.jobhw.org { reverse_proxy jhw-web:8000 }
  * this repository keeps a FALLBACK copy at deploy/caddy/jobhuntwow.caddy which is stale and
    declares only the two jobhuntwow.com names.
  * `jobhuntwow-app/` is gitignored here. `git ls-files jobhuntwow-app` returns zero files, so a
    CI checkout does not contain the authority.
  * caddyguard's RESTORE step copies the chosen block OVER the droplet's live fragment whenever
    the two differ.

On the operator's laptop the authority exists and the right block ships. On a runner it does not,
the fallback was selected with no message, and the first green pipeline overwrote the fragment
without jobhw.org. No site block matched that SNI, so the TLS handshake failed outright, which is
why the browser reported a protocol error rather than a 404.

Three defect classes at once. Class 37, a feature behind `if <derived thing>` failing silently.
Class 19, a path that behaves differently depending on which machine runs it. Class 1, an actor
that cannot see its subject must not act on it.

THE RULE THIS PINS: when the authority is not visible, caddyguard must leave jobhuntwow's fragment
alone. Not touching a fragment is always safe. Overwriting one from a copy known to be stale is
how a domain disappears.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import caddyguard  # noqa: E402

AUTHORITY = os.path.join(ROOT, "jobhuntwow-app", "deploy", "caddy", "jobhuntwow.caddy")
FALLBACK = os.path.join(ROOT, "deploy", "caddy", "jobhuntwow.caddy")


def _hosts(path):
    """Hostnames a Caddy fragment declares, from its site-block opening lines."""
    out = set()
    for ln in open(path, encoding="utf-8"):
        ln = ln.split("#")[0].strip()
        if not ln.endswith("{") or ln.startswith(("log", "reverse_proxy", "header", "encode")):
            continue
        for h in ln[:-1].split(","):
            h = h.strip()
            if re.match(r"^[a-z0-9.*-]+\.[a-z]{2,}$", h):
                out.add(h)
    return out


def test_the_resolver_reports_whether_it_found_the_authority():
    """THE BUG, as a property. The old function returned a path either way, so the caller could
    not tell an authoritative block from a stale one."""
    got = caddyguard.jhw_snippet()
    assert isinstance(got, tuple) and len(got) == 2, (
        "jhw_snippet() must return (path, authoritative); it returned %r, which is the shape that "
        "let a fallback pass as the real thing" % (got,))
    path, ok = got
    assert isinstance(ok, bool), got
    if ok:
        assert path and os.path.exists(path), got


def test_without_the_authority_it_refuses_rather_than_falling_back():
    """FAIL CLOSED. Simulated, not skipped (class 20): point JHW_APP at a path that does not
    exist, which is exactly a CI runner's state, and require a refusal."""
    orig = caddyguard.JHW_APP
    try:
        caddyguard.JHW_APP = os.path.join(ROOT, "no-such-sibling", "jobhuntwow.caddy")
        path, ok = caddyguard.jhw_snippet()
        assert ok is False, "a runner would be told the block is authoritative when it is not"
        assert path is None, (
            "it still handed back %r, and the caller copies that over the live fragment. That is "
            "the 2026-10-16 outage exactly." % path)
    finally:
        caddyguard.JHW_APP = orig


def test_the_remote_script_skips_the_fragment_when_no_block_was_sent():
    """BEHAVIOUR AND WIRING (class 9). The resolver refusing is worth nothing if the shell script
    still overwrites the fragment with an empty file."""
    script = caddyguard.build(restore="yes", check_only=False)
    i = script.find("/tmp/jhw.caddy")
    assert i != -1, "the jhw restore step is gone from the generated script"
    seg = script[i:i + 700]
    assert "-s /tmp/jhw.caddy" in seg, (
        "the script does not test whether a block was actually sent, so an empty payload would "
        "be copied over the live fragment: %s" % seg[:220])
    assert "SKIPPED" in seg, "a skipped fragment says nothing, so nobody would know it was skipped"


def test_the_fallback_is_not_silently_used_for_a_host_it_does_not_know():
    """The fallback is missing hosts the authority serves. That is allowed, as long as nothing
    ships it as though it were complete."""
    if not os.path.exists(AUTHORITY):
        import pytest
        pytest.skip("sibling checkout absent here; CI covers the refusal path above")
    missing = _hosts(AUTHORITY) - _hosts(FALLBACK)
    assert "jobhw.org" in _hosts(AUTHORITY), (
        "the authority no longer declares jobhw.org, so this guard is reading the wrong file")
    if missing:
        path, ok = caddyguard.jhw_snippet()
        assert ok and path == AUTHORITY, (
            "the fallback is missing %s and would still be shipped" % sorted(missing))


def test_the_sibling_really_is_invisible_to_ci():
    """PROVE THE PREMISE (class 12). If jobhuntwow-app were tracked, the whole analysis above is
    wrong and this guard is solving an imaginary problem."""
    r = subprocess.run(["git", "ls-files", "-z", "jobhuntwow-app"], cwd=ROOT,
                       capture_output=True, timeout=60)
    if r.returncode != 0:
        import pytest
        pytest.skip("git unavailable here")
    tracked = [p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]
    assert not tracked, (
        "jobhuntwow-app is tracked now (%d files). If CI can see the authority, remove this "
        "guard and the fail-closed branch with it." % len(tracked))


def test_build_sends_NO_block_when_the_authority_is_absent():
    """SIMULATE THE RUNNER (class 20), do not test only the machine that happens to be healthy.

    The first version of this file checked the generated script on a box where the sibling
    checkout exists, so the payload was always populated and a mutation that shipped the fallback
    regardless passed every assertion. The whole outage lives in the other branch, which is the
    one that was never exercised.
    """
    orig = caddyguard.JHW_APP
    try:
        caddyguard.JHW_APP = os.path.join(ROOT, "no-such-sibling", "jobhuntwow.caddy")
        script = caddyguard.build(restore="yes", check_only=False)
    finally:
        caddyguard.JHW_APP = orig

    i = script.find("base64 -d > /tmp/jhw.caddy")
    assert i != -1, "the jhw payload line is gone"
    line = script[script.rfind("\n", 0, i) + 1:i]
    payload = line.split("'")[1] if "'" in line else line
    assert payload.strip() == "", (
        "with no authority visible the script still carries a %d-character block, which it then "
        "copies over the live fragment. That is the 2026-10-16 outage: the fallback does not "
        "declare jobhw.org." % len(payload.strip()))

    # And on a machine that CAN see the authority, a real block must still be sent, or the fix
    # would simply have disabled jobhuntwow's deploy everywhere.
    if os.path.exists(AUTHORITY):
        healthy = caddyguard.build(restore="yes", check_only=False)
        j = healthy.find("base64 -d > /tmp/jhw.caddy")
        ln = healthy[healthy.rfind("\n", 0, j) + 1:j]
        assert len(ln.split("'")[1]) > 100, "the authoritative block is no longer being sent"
