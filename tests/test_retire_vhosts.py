"""test_retire_vhosts.py — the proxy converges onto estate.py, on every ship, with no extra command.

ORIGINALLY tests/test_observemove.py, and the ORIGINAL REASONING IS KEPT (class 17). That file
tested a standalone `observemove.py --apply`, which was the wrong shape twice over. Operating
principle 7: a migration is wired INTO the orchestrator in the same change, and a script the
operator has to remember to run separately is a bug. And "the proxy serves exactly what estate.py
says" is not a one-off migration at all, it is a CONVERGENCE step, which belongs on every run.

So the logic moved into deploy/caddyguard/agent.py, which ship.py already invokes through
caddyguard.py, and the retired set travels in CADDY_RETIRE from the one home. The assertions
below are the same ones, pointed at the code that now does the work.

THE TRAP THESE EXIST FOR. The block being removed ended with a Content-Security-Policy string and
a `try_files {path} /index.html` line, and the godeyes.ai header was the PLACEHOLDER `{$DOMAIN} {`.
A matcher ending in \\b never matched it (no word boundary between `}` and a space), and a brace
counter that does not ignore comments and strings runs past the closing brace and takes the next
vhost with it. Both of those were real, and both were caught here before they reached the proxy.
"""
import importlib.util as ilu
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

AGENT = os.path.join(ROOT, "deploy", "caddyguard", "agent.py")

# The fragment set as the droplet reported it on 19 Nov 2026, including the placeholder header,
# the CSP and the {path} placeholder. A fixture that does not reproduce the condition under test
# is a test of the fixture (class 12).
BASE = """# videodead base — managed by caddyguard
{$DOMAIN} {
\tencode gzip zstd
\t# an unbalanced { in a comment: this is the line that breaks a naive counter
\thandle /api/* {
\t\treverse_proxy api:8000
\t}
\thandle {
\t\theader {
\t\t\tContent-Security-Policy "default-src 'self'; frame-ancestors 'none'"
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
\treverse_proxy colt-web:8000
}
"""
FRAGS = {
    "polara__klima.caddy": "klimaanlage-preise.de, www.klimaanlage-preise.de {\n\treverse_proxy polara-web:8000\n}\n",
    "colt__cybergod.caddy": "cybergod.ai, www.cybergod.ai {\n\thandle /observe* {\n\t\treverse_proxy grafana:3000\n\t}\n\thandle {\n\t\treverse_proxy colt-web:8000\n\t}\n}\n",
    "s4biz__site.caddy": "s4biz.io {\n\treverse_proxy s4biz-web:8000\n}\n",
    "mixed__example.caddy": 'jev.best {\n\trespond "x"\n}\n\ns4biz.io {\n\trespond "y"\n}\n',
}


def _agent(tmp_path, retire=None):
    """Load the SHIPPED agent against a scratch blocks dir. Not a copy of its logic (class 32)."""
    import estate
    frag = tmp_path / "blocks"
    frag.mkdir()
    (frag / "_base.caddy").write_bytes(BASE.encode("utf-8"))      # BYTES: no newline translation
    for n, t in FRAGS.items():
        (frag / n).write_bytes(t.encode("utf-8"))
    os.environ["CADDY_RETIRE"] = ",".join(retire if retire is not None else estate.retire_headers())
    os.environ["CADDYGUARD_FRAG"] = str(frag)
    spec = ilu.spec_from_file_location("agent_under_test", AGENT)
    m = ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.FRAG = str(frag)          # the agent resolves FRAG at import; point it at the scratch dir
    return m, frag


def test_the_fixture_really_contains_the_traps():
    assert "{$DOMAIN} {" in BASE, "no placeholder header, so the \\b bug cannot be caught"
    assert "unbalanced { in a comment" in BASE
    assert "try_files {path} /index.html" in BASE
    assert BASE.count("{") == BASE.count("}") + 1, (
        "the fixture must NOT balance by raw count: Caddy balances it, a naive counter does not")


def test_every_retired_block_leaves_and_the_live_ones_stay(tmp_path):
    m, frag = _agent(tmp_path)
    did = m.retire_blocks()
    out = io.open(frag / "_base.caddy", encoding="utf-8").read()
    assert "{$DOMAIN}" not in out, "the placeholder block survived"
    assert "jev.best" not in out, "a retired project is still served"
    assert "cybergod.ai, www.cybergod.ai {" in out, "the edit took the production host with it"
    assert "reverse_proxy colt-web:8000" in out
    assert out.count("{") == out.count("}"), "the result does not balance"
    assert any("_base.caddy" in d for d in did), "it did the work without reporting it"


def test_a_fragment_that_is_all_retired_is_removed(tmp_path):
    m, frag = _agent(tmp_path)
    m.retire_blocks()
    left = sorted(p.name for p in frag.iterdir() if p.name.endswith(".caddy"))
    assert "polara__klima.caddy" not in left, "a retired project keeps its own fragment"
    assert {"colt__cybergod.caddy", "s4biz__site.caddy"} <= set(left)


def test_a_fragment_with_one_live_header_is_never_deleted(tmp_path):
    """Deleting it would retire a site nobody asked to retire."""
    m, frag = _agent(tmp_path)
    m.retire_blocks()
    left = {p.name for p in frag.iterdir() if p.name.endswith(".caddy")}
    assert "mixed__example.caddy" in left, "a live site was retired as collateral"


def test_running_twice_changes_nothing(tmp_path):
    """Idempotence is what makes this safe on EVERY ship rather than once, by hand."""
    m, frag = _agent(tmp_path)
    m.retire_blocks()
    after_one = io.open(frag / "_base.caddy", encoding="utf-8").read()
    assert m.retire_blocks() == [], "a second run claims to have retired something again"
    assert io.open(frag / "_base.caddy", encoding="utf-8").read() == after_one


def test_nothing_retired_means_nothing_touched(tmp_path):
    m, frag = _agent(tmp_path, retire=[])
    assert m.retire_blocks() == []
    assert io.open(frag / "_base.caddy", encoding="utf-8").read() == BASE


def test_the_header_matcher_handles_the_real_header_forms(tmp_path):
    m, _ = _agent(tmp_path)
    assert m._is_retired_header("{$DOMAIN} {"), (
        "the placeholder is not matched, which is the one site this was written for")
    assert m._is_retired_header("jev.best, www.jev.best {")
    assert m._is_retired_header("klimaanlage-preise.de, www.klimaanlage-preise.de {")
    assert not m._is_retired_header("cybergod.ai, www.cybergod.ai {"), "production would be removed"
    assert not m._is_retired_header("s4biz.io {")
    assert not m._is_retired_header("jev.best.example.com {"), "a prefix match takes a stranger"


def test_an_unterminated_block_is_refused_rather_than_truncating_the_file(tmp_path):
    m, frag = _agent(tmp_path)
    (frag / "_base.caddy").write_bytes(b"{$DOMAIN} {\n\thandle /observe* {\n")
    m.retire_blocks()
    assert "handle /observe*" in io.open(frag / "_base.caddy", encoding="utf-8").read(), (
        "a truncated file was rewritten; a brace counter that runs off the end deletes the rest "
        "of the proxy")


def test_it_runs_inside_the_orchestrator_and_needs_no_second_command():
    """Operating principle 7, asserted rather than intended. This is the whole reason the logic
    moved out of a standalone script."""
    agent = io.open(AGENT, encoding="utf-8").read()
    i_ret = agent.index("retire_blocks()", agent.index("def cmd_assemble("))
    i_asm = agent.index("assemble()", agent.index("def cmd_assemble("))
    assert i_ret < i_asm, "retire must run BEFORE the assemble it feeds"
    cg = io.open(os.path.join(ROOT, "caddyguard.py"), encoding="utf-8").read()
    assert "CADDY_RETIRE" in cg, "the retired set never reaches the droplet"
    assert "_estate.retire_headers()" in cg, "the list is retyped instead of derived (class 32)"
    ship = io.open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()
    assert "caddyguard" in ship, "ship.py does not invoke the guard, so nothing converges"
    assert not os.path.exists(os.path.join(ROOT, "observemove.py")), (
        "the standalone migration script is back; it is a second command and principle 7 forbids it")
