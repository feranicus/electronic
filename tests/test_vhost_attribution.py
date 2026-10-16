"""An unexpected vhost on the shared proxy must NAME where it came from.

THE INCIDENT, 2026-10-15/16. caddyguard's roster check reported, on four consecutive ships:

    [!] 2 host(s) served that are NOT on the committed roster: jobhw.org, www.jobhw.org
        On a shared proxy an unexpected vhost claims traffic and certificates for a name nobody
        committed. Add it to the roster, or find out who wrote it.

Nobody ever did find out who wrote it, and the reason is that the check told the operator to go
looking for a fact it was already holding: the guard ASSEMBLES the live file from the fragments in
FRAG, so whichever fragment declares that hostname was one directory read away. Four runs of a
warning that nobody can act on is the benign-every-time alert CLAUDE.md names as the enemy - it
trains the operator to read past the one that matters.

The two possible answers have completely different remedies, which is exactly why the message had
to distinguish them:
  * declared in a fragment  -> that fragment exists on the droplet; if it has no committed source,
                               part of the shared config is unversioned (principle 2).
  * declared by NO fragment -> something wrote outside the guard, and the next assemble drops it.
"""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "deploy", "caddyguard", "agent.py")


def _agent():
    spec = importlib.util.spec_from_file_location("_cg_agent_for_test", AGENT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fragments(tmp_path):
    """The REAL shape: a _base fragment carrying vhosts nobody committed, beside a project one."""
    d = tmp_path / "blocks"
    d.mkdir()
    (d / "_base.caddy").write_text(
        "{\n\temail ops@example.com\n}\n\n"
        "jobhw.org, www.jobhw.org {\n\treverse_proxy jhw-web:8000\n}\n", encoding="utf-8")
    (d / "colt__cybergod.caddy").write_text(
        "cybergod.ai, www.cybergod.ai {\n\treverse_proxy colt-web:8000\n}\n", encoding="utf-8")
    ag = _agent()
    ag.FRAG = str(d)
    return ag


def test_it_names_the_fragment_that_declares_the_host(fragments):
    """The whole point. `jobhw.org` is in _base.caddy, and saying so is the difference between a
    warning and an action."""
    for host in ("jobhw.org", "www.jobhw.org"):
        said = fragments._declared_in(host)
        assert "_base.caddy" in said, (host, said)
    # and it must not blame the wrong file
    assert "colt__cybergod" not in fragments._declared_in("jobhw.org")
    assert "colt__cybergod.caddy" in fragments._declared_in("cybergod.ai")


def test_a_host_no_fragment_declares_is_reported_as_exactly_that(fragments):
    """The OTHER answer, and the more serious one: a vhost in the running config that the guard
    does not assemble is a write that went around the guard, and the next assemble deletes it.
    Reporting it as "declared in <something>" would be a lie with an outage attached."""
    said = fragments._declared_in("stranger.example")
    assert "NO fragment" in said, said
    assert "a reload would drop it" in said, said


def test_it_refuses_to_answer_when_it_cannot_read_the_fragments(fragments):
    """A probe that cannot see its subject must not answer (defect class 1). An unreadable
    fragment directory is not evidence that nothing declares the host."""
    fragments.FRAG = "/definitely/not/here"
    said = fragments._declared_in("jobhw.org")
    assert "not determined" in said, said
    assert "NO fragment" not in said, (
        "an unreadable directory was reported as proof that no fragment declares it: %s" % said)


def test_a_substring_match_is_not_a_declaration(fragments, tmp_path):
    """`example.com` must not be attributed to a fragment that merely serves `notexample.com`,
    and a hostname appearing in a COMMENT or an upstream is not a site header either."""
    d = tmp_path / "blocks"
    (d / "decoy.caddy").write_text(
        "# jobhw.org is mentioned here in prose\n"
        "notjobhw.org {\n\treverse_proxy jobhw.org:8000\n}\n", encoding="utf-8")
    said = fragments._declared_in("jobhw.org")
    assert "decoy.caddy" not in said, (
        "a comment or an upstream was read as a site header: %s" % said)
    assert "_base.caddy" in said


def test_the_roster_check_actually_calls_it(fragments):
    """BEHAVIOUR AND WIRING (defect class 9). The helper being correct is worth nothing if the
    warning still prints the old go-and-find-it sentence. Anchored on the call site."""
    import ast
    tree = ast.parse(open(AGENT, encoding="utf-8").read())
    fn = [n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "cmd_roster"]
    assert fn, "cmd_roster is gone; this guard is reading the wrong function"
    src = ast.unparse(fn[0])
    assert "_declared_in" in src, (
        "the unexpected-vhost warning does not name the source - it is back to telling the "
        "operator to find out who wrote it, which is what nobody could do for four ships")
    assert "find out who wrote it" not in src, (
        "the old unactionable sentence is still what the operator reads")
