"""test_observemove.py — the godeyes.ai retirement edits the shared proxy. Prove the edit first.

The fragment being rewritten is `_base.caddy`, which is assembled into the Caddyfile that owns
:443 for cybergod.ai, jobhuntwow.com, jev.best, two klimaanlage domains and s4biz.io. A bad edit
there is not a bug in a report, it is six sites down until somebody notices.

THE TRAP THIS EXISTS FOR. The block being removed ends with a Content-Security-Policy string and
a `try_files {path} /index.html` line. `{path}` is a Caddy placeholder, so a replacement that
finds the end of a site block by grepping for `}` at column zero, or by counting braces without
knowing about placeholders, cuts in the wrong place and takes the NEXT vhost with it. decommission.py
already carries that rule; this test holds the new code to it.

THE CODE UNDER TEST IS THE SHIPPED CODE. The replacement runs on the droplet inside a heredoc in
observemove.APPLY. Copying it here would make this a test of the copy (class 32), so the heredoc
is extracted from the module and executed. If somebody edits the shell and not the logic, this
test runs the edit.
"""
import io
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _om():
    import observemove
    return observemove


def _rewriter():
    """The python the droplet runs, lifted out of the shell payload verbatim."""
    src = _om().APPLY
    m = re.search(r"python3 - \"\$BASE\" <<'PYEOF'\n(.*?)\nPYEOF", src, re.S)
    assert m, "the rewriter heredoc is no longer where this test looks for it"
    return m.group(1)


# The block as the droplet reported it on 19 Nov 2026, verbatim, including the CSP and the
# {path} placeholder. A fixture that does not reproduce the condition is a test of the fixture.
MEASURED = """# videodead base — managed by caddyguard
{$DOMAIN} {
\tencode gzip zstd

\theader {
\t\tStrict-Transport-Security "max-age=31536000; includeSubDomains; preload"
\t\t-Server
\t}

\t# an unbalanced { in a comment: this is the line that breaks a naive counter
\thandle /api/* {
\t\treverse_proxy api:8000
\t}

\thandle /observe* {
\t\treverse_proxy grafana:3000
\t}

\thandle {
\t\theader {
\t\t\tX-Content-Type-Options "nosniff"
\t\t\tContent-Security-Policy "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
\t\t}
\t\troot * /srv/www
\t\ttry_files {path} /index.html
\t\tfile_server
\t}
}

jev.best, www.jev.best {
\treverse_proxy jev-api:8000
}

cybergod.ai, www.cybergod.ai {
\tencode zstd gzip
\treverse_proxy colt-web:8000
}

klimaanlage-preise.de, www.klimaanlage-preise.de {
\treverse_proxy polara-web:8000
}

s4biz.io {
\treverse_proxy s4biz-web:8000
}
"""


def _run(base_text):
    """Run the shipped rewriter over a scratch copy and hand back the result."""
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "_base.caddy")
    io.open(p, "w", encoding="utf-8", newline="\n").write(base_text)
    env = dict(os.environ)
    env["GRAFANA_ROOT_URL"] = _om().GRAFANA_ROOT_URL
    env["RETIRE_HEADERS"] = _om().retire_headers()
    # The shipped shell loops this until rc 11 ("nothing retired left"), because one pass removes
    # one block and three projects are being retired. The test loops it the same way or it would
    # be testing a single pass of a loop.
    log, rc = "", 0
    for _ in range(8):
        r = subprocess.run([sys.executable, "-c", _rewriter(), p],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=60)
        log += (r.stdout or "") + (r.stderr or "")
        rc = r.returncode
        if rc != 0:
            break
    out = io.open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    return (0 if rc == 11 else rc), log, out


def test_the_fixture_really_contains_the_trap():
    """Prove the fixture before trusting any verdict it produces (class 12)."""
    assert "{$DOMAIN} {" in MEASURED
    assert "try_files {path} /index.html" in MEASURED, "no placeholder, so no trap to catch"
    assert "Content-Security-Policy" in MEASURED
    assert "# an unbalanced { in a comment" in MEASURED, (
        "without a stray brace in a comment this fixture cannot tell a depth counter from a "
        "line-matching one, and every mutation scores as caught")
    # The fixture does NOT balance by raw character count, and that is the point: Caddy balances
    # it, a naive counter does not.
    assert MEASURED.count("{") == MEASURED.count("}") + 1


def test_only_the_domain_block_is_removed():
    """DESIGN CHANGED 19 NOV 2026, ORIGINAL REASONING KEPT. This used to assert that the block
    was REPLACED by an observe.cybergod.ai vhost. That plan needed a DNS record, and the GoDaddy
    credential it assumed does not exist in this project: no env file holds one, golive.secrets.env
    is an example file carrying a deprecation note, and cloudflare_setup.py is a plan that was
    never run (cybergod.ai resolves straight to the droplet). Grafana already serves from
    /observe, so it moved to a path of cybergod.ai instead and this block simply goes."""
    rc, log, out = _run(MEASURED)
    assert rc == 0, log
    assert "{$DOMAIN}" not in out, "the old block survived"
    for dead in ("jev.best", "klimaanlage"):
        assert dead not in out, "%s was retired weeks ago and still has a vhost" % dead
    assert "grafana:3000" not in out, (
        "the retired block still proxies Grafana; the route now lives in the committed "
        "cybergod fragment and having it twice is two homes for one value")
    # EVERY OTHER VHOST SURVIVES. This is the assertion that would have caught a greedy cut.
    for survivor in ("cybergod.ai, www.cybergod.ai {", "s4biz.io {",
                     "reverse_proxy colt-web:8000", "reverse_proxy s4biz-web:8000"):
        assert survivor in out, "the edit took %r with it" % survivor
    assert out.count("{") == out.count("}"), "the result does not balance"


def test_the_whole_videodead_vhost_is_gone():
    rc, log, out = _run(MEASURED)
    assert rc == 0, log
    for retired in ("reverse_proxy api:8000", "/srv/www"):
        assert retired not in out, "%s survived the decommission" % retired


def test_grafana_keeps_its_route_in_the_committed_cybergod_fragment():
    """The route moved, it did not vanish. It lives in the fragment CI reinstalls, so a hand edit
    on the droplet cannot survive a ship, and it is matched BEFORE the catch-all or every request
    would reach the React app instead."""
    frag = io.open(os.path.join(ROOT, "deploy", "caddy", "cybergod.caddy"), encoding="utf-8").read()
    assert "handle /observe*" in frag, "Grafana has no route anywhere"
    assert "reverse_proxy grafana:3000" in frag
    assert frag.index("handle /observe*") < frag.index("reverse_proxy colt-web:8000"), (
        "the catch-all comes first, so /observe would be served by the React app")
    assert "cybergod.ai, www.cybergod.ai {" in frag, "the production hosts lost their own block"


def test_the_csp_that_breaks_grafana_is_not_carried_over():
    """It lived on the SPA handle deliberately. Copying it onto Grafana is the tidy-looking
    mistake that presents to the operator as 'Grafana is broken'."""
    frag = io.open(os.path.join(ROOT, "deploy", "caddy", "cybergod.caddy"), encoding="utf-8").read()
    assert "Content-Security-Policy" not in frag


def test_no_dns_step_survives_in_the_apply_path():
    """The move must not wait on a credential this project does not have."""
    om = _om()
    assert not hasattr(om, "dns_ready"), "the DNS gate is still there"
    src = io.open(os.path.join(ROOT, "observemove.py"), encoding="utf-8").read()
    body = src[src.index("def apply("):src.index("def _shq(")]
    assert "GoDaddy" not in body and "A record" not in body
    assert om.GRAFANA_ROOT_URL == "https://cybergod.ai/observe/"


def test_the_proxy_container_is_never_restarted():
    """videodead-caddy-1 owns :443 for every domain on the droplet; its death is a total outage."""
    body = _om().APPLY
    assert "--no-deps grafana" in body, "the grafana recreate must not drag the stack with it"
    for forbidden in ("restart videodead-caddy", "up -d caddy", "--force-recreate caddy"):
        assert forbidden not in body, "this would restart the shared proxy: %r" % forbidden


def test_a_fragment_with_nothing_retired_is_left_alone():
    """Idempotence matters here: the loop runs until nothing matches, and a second --apply must
    not touch a file that is already clean."""
    rc, log, out = _run("cybergod.ai {\n\treverse_proxy colt-web:8000\n}\n")
    assert rc == 0, log
    assert "no retired site header left" in log
    assert "colt-web" in out, "the file was modified despite the failure"


def test_an_unterminated_block_is_refused():
    """Truncation is the one input where a brace counter can run off the end of the file and
    silently delete the rest of the proxy."""
    rc, log, out = _run("{$DOMAIN} {\n\thandle /observe* {\n\t\treverse_proxy grafana:3000\n")
    assert rc != 0, "an unterminated block was accepted"
    assert "never closes" in log or "FATAL" in log


def test_the_write_is_atomic():
    """A half-written fragment is a dead proxy, and `open(path,'w')` truncates before it
    validates anything. os.replace or nothing."""
    body = _rewriter()
    assert "os.replace(" in body, "the fragment is written in place"
    assert re.search(r'io\.open\(tmp, "w"', body), "it must write a temp file first"
    assert 'newline="\\n"' in body, "LF endings: this file is read by a Linux proxy (class 21)"


def test_the_verifier_uses_a_browser_agent():
    """MEASURED on 19 Nov 2026: https://cybergod.ai/ answers 404 to curl's own agent and 200 to a
    browser, because of the bot gate. A verifier that does not know this reports the React site
    as broken before the change and fixed after it."""
    om = _om()
    assert "Mozilla/5.0" in om.UA
    names = {n for n, _u, _ok in om.WATCH}
    assert {"cybergod.ai", "cybergod.ai/api/me"} <= names, (
        "the production pair is what 'no interference' means; it must be watched")
    for _n, _u, ok in om.WATCH:
        assert ok, "an empty acceptable-code set can never fail"
    codes = dict((n, ok) for n, _u, ok in om.WATCH)
    assert codes["cybergod.ai/api/me"] == ("401",), "401 is the proof the app is up AND locked"


def test_the_new_path_is_proved_before_the_old_one_is_cut():
    """ORDER IS THE SAFETY HERE. ship.py installs the /observe route first, so Grafana answers on
    both names for a few minutes; only once the new path has been measured answering does the old
    vhost go. Reverse the two and a failed ship leaves no dashboard at all."""
    src = io.open(os.path.join(ROOT, "observemove.py"), encoding="utf-8").read()
    body = src[src.index("def apply("):src.index("def _shq(")]
    i_before = body.index('watch("BEFORE')
    i_ship = body.index('"ship.py"')
    i_proof = body.index('_probe("https://cybergod.ai/observe/")')
    i_ssh = body.index("ssh_script")
    assert i_before < i_ship < i_proof < i_ssh, (
        "baseline, then ship, then prove the new path, then retire the old one")
    assert body.index("return 5") < i_ssh, "a dead new path must stop the run before the cutover"


@pytest.mark.parametrize("path", ["observemove.py"])
def test_no_posix_only_calls_on_the_operators_machine(path):
    """This runs on Windows. os.uname, /proc and fcntl are not available there."""
    src = io.open(os.path.join(ROOT, path), encoding="utf-8").read()
    local = src.split("APPLY = r\"\"\"")[0] + src.split("\"\"\"", 2)[-1]
    for banned in ("os.uname", "fcntl", "/proc/"):
        assert banned not in local, "%s is POSIX-only and this runs on Windows" % banned


def test_the_roster_has_one_home_and_a_retired_site_cannot_block_a_deploy():
    """19 Nov 2026: --apply refused to start because its own copy of the roster said jev.best
    should answer 200. It answers 502 and has for weeks, because the project ended. The list of
    live sites had NINE homes; now it has one and everything derives from it."""
    import estate
    om = _om()
    names = {n for n, _u, _c in om.WATCH}
    for dead in ("jev.best", "klimaanlage-preise.de", "godeyes.ai"):
        assert dead not in names, "%s is retired and still gates the deploy" % dead
        assert estate.is_retired(dead)
    assert {"cybergod.ai", "cybergod.ai/api/me"} <= names
    # the route being CREATED cannot be in the baseline taken before it exists
    assert "cybergod.ai/observe" not in names, (
        "the new path is in the BEFORE baseline, so the guard refuses to build the thing it is for")
    assert "cybergod.ai/observe" in estate.LIVE_PATHS, "but it must still be a live route"
    src = io.open(os.path.join(ROOT, "observemove.py"), encoding="utf-8").read()
    assert "estate.watch_list()" in src, "the baseline must come from the one home"


def test_the_header_matcher_handles_the_real_header_forms():
    """REPLACED A CIRCULAR CHECK (class 3). The previous version asserted that every name in
    estate.RETIRED appeared in retire_headers() - a list retire_headers() DERIVES from exactly
    that set. The denominator was produced by the thing being measured, so it could not fail, and
    a mutation adding a bogus retired domain scored as caught when nothing had caught it.

    The property that can actually be wrong is the MATCHER, and it was: the first version ended
    the pattern in \\b, and there is no word boundary between `}` and a space, so `{$DOMAIN} {`
    never matched. The one site this whole script exists for would have been left on the proxy
    while every other block was removed.
    """
    import re
    om = _om()
    wanted = om.retire_headers().split("|")

    def matches(line):
        return any(re.match(r"^%s(\s|,|\{|$)" % re.escape(w), line) for w in wanted)

    # the real header lines, as the droplet printed them on 19 Nov 2026
    assert matches("{$DOMAIN} {"), "the placeholder header is not matched, which is the whole job"
    assert matches("jev.best, www.jev.best {")
    assert matches("klimaanlage-preise.de, www.klimaanlage-preise.de {")
    # and the survivors must not be touched
    assert not matches("cybergod.ai, www.cybergod.ai {"), "the production host would be removed"
    assert not matches("s4biz.io {")
    assert not matches("www.jobhuntwow.com, jobhw.org, www.jobhw.org {")
    # a name that merely starts the same is not the same site
    assert not matches("jev.best.example.com {"), "a prefix match would take a stranger's vhost"
