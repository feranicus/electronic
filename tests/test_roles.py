"""test_roles.py — authorisation. The one place where a passing test that cannot fail is a breach.

The model is the one every channel platform converges on: a tenant, a membership with a role, and
a role that is a named bundle of PERMISSIONS rather than a list of screens. The tests below are
about the two properties that actually keep customers apart:

  * a verb nobody granted is refused, including a verb that does not exist;
  * an administrator is confined to their own tenant unless they were given the wider permission.

Both are asserted against roles.py directly AND against the gate in main.py, because a policy that
is correct and unreachable is not a control (class 9).
"""
import ast
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import roles  # noqa: E402


def test_every_role_holds_only_verbs_that_exist():
    """A permission string with a typo in it is a permission nobody can ever be granted, and it
    reads like a capability the role has."""
    for name, r in roles.ROLES.items():
        unknown = r["perms"] - set(roles.PERMISSIONS)
        assert not unknown, "%s holds verbs that are not defined: %s" % (name, sorted(unknown))


def test_an_unknown_verb_is_refused_for_everybody():
    """Deny by default. A typo in a route decorator must CLOSE the route, not open it."""
    for name in roles.ROLES:
        assert not roles.can("pipeline.viwe", name), "%s passed a misspelled verb" % name
        assert not roles.can("", name)


def test_a_verb_outside_the_catalogue_is_refused_even_if_a_role_holds_it():
    """DEFEAT EVERY GUARD ON THE PATH (class 13). The previous version of this check removed the
    `perm not in PERMISSIONS` line and nothing failed, because set membership refuses a misspelled
    verb anyway - the mutation did not violate the property, so it proved nothing.

    The guard earns its place in the one case set membership cannot cover: a role that HOLDS a
    verb the catalogue does not define. That is a real shape - it is what a half-finished rename
    leaves behind - and without the catalogue check the undefined verb would be granted."""
    import copy
    saved = copy.deepcopy(roles.ROLES["user"]["perms"])
    try:
        roles.ROLES["user"]["perms"].add("pipeline.admin.TYPO")
        assert not roles.can("pipeline.admin.TYPO", "user"), (
            "a verb that is not in the catalogue was granted because a role happened to list it")
    finally:
        roles.ROLES["user"]["perms"] = saved


def test_the_least_privileged_role_is_the_fallback():
    assert roles.role_of("nobody@example.com", None) == roles.DEFAULT_ROLE
    assert roles.role_of("nobody@example.com", "wizard") == roles.DEFAULT_ROLE, (
        "a stale or misspelled role column silently granted something")
    assert roles.role_of("nobody@example.com", "s4biz_power") == "s4biz_power"


def test_the_admin_floor_cannot_be_removed_by_a_row():
    """If a bad row could demote the platform admin, one UPDATE locks everybody out of the
    administration of the platform. colt_auth.ADMIN_EMAILS is the floor."""
    import colt_auth
    for a in colt_auth.ADMIN_EMAILS:
        assert roles.role_of(a, "user") == "admin", "%s was demoted by a row" % a
        assert roles.role_of(a.upper(), "") == "admin", "the floor is case-sensitive"


def test_nobody_can_create_a_peer_or_a_superior():
    """Privilege escalation with a friendly name. A company admin minting a second company admin
    is how one compromised account becomes two."""
    for a, av in roles.ROLES.items():
        for t, tv in roles.ROLES.items():
            if a == "admin":
                continue
            if roles.may_grant(a, t):
                assert tv["rank"] > av["rank"], "%s may create %s, which is not junior" % (a, t)


def test_only_a_role_with_an_invite_permission_may_grant_at_all():
    for a in ("presales", "sales_rep", "user"):
        for t in roles.ROLES:
            assert not roles.may_grant(a, t), "%s can create accounts and should not" % a


def test_a_company_admin_is_confined_to_their_own_tenant():
    """THE RULE THAT KEEPS CUSTOMERS APART. It lives in roles.py rather than in a route, because
    a rule written once per route is a rule that is missing from one of them."""
    assert roles.may_touch("company_admin", "boss@colt.net", "new@colt.net")
    assert not roles.may_touch("company_admin", "boss@colt.net", "victim@s4biz.io"), (
        "a customer administrator reached into another customer")
    # a reseller and S4biz staff are deliberately wider
    assert roles.may_touch("reseller_admin", "boss@objectale.ch", "new@somewhere.else")
    assert roles.may_touch("s4biz_power", "jev@s4biz.io", "anyone@anywhere.com")
    # and someone with no invite permission touches nobody, including themselves
    assert not roles.may_touch("sales_rep", "rep@s4biz.io", "rep@s4biz.io")


def test_an_empty_tenant_never_matches_another_empty_one():
    """`org_of` returns "" for a malformed address. Two malformed addresses must not become
    colleagues, which is what `"" == ""` would otherwise mean."""
    assert roles.org_of("not-an-email") == ""
    assert not roles.may_touch("company_admin", "not-an-email", "also-not-an-email")


def test_the_pipeline_is_confined_to_the_roles_that_should_see_it():
    """The operator's requirement, as a property: the channel pipeline is for S4biz people and
    the sellers, and for nobody at a customer."""
    for r in ("admin", "s4biz_power", "sales_rep", "reseller_admin"):
        assert roles.can("pipeline.view", r), "%s cannot see the pipeline" % r
    for r in ("company_admin", "presales", "user"):
        assert not roles.can("pipeline.view", r), "%s can see the channel pipeline" % r


def test_only_the_platform_admin_holds_the_dangerous_verbs():
    for verb in ("platform.admin", "users.manage.all"):
        holders = [r for r in roles.ROLES if roles.can(verb, r)]
        assert holders == ["admin"], "%s is held by %s" % (verb, holders)


# ---------------------------------------------------------------------------------------------
# WIRING. The policy above is worthless if no route asks it (class 9).
# ---------------------------------------------------------------------------------------------
MAIN = io.open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()


def _no_comments(src):
    out = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            d = ast.get_docstring(node, clean=False)
            if d:
                out = out.replace(d, "")
    return out


BODY = _no_comments(MAIN)


def test_the_gate_exists_and_asks_roles_py():
    assert "def _require_perm(" in BODY, "no permission dependency exists"
    gate = BODY[BODY.index("def _require_perm("):BODY.index("def _require_admin(")]
    assert "_roles.can(" in gate, "the gate does not consult the policy"
    assert "_require_ready(request)" in gate, (
        "the gate skips the authentication and password-change checks")
    assert "perm_denied" in gate, "a refusal is not logged, so a lockout cannot be diagnosed"


def test_the_role_lookup_degrades_rather_than_crashes():
    look = BODY[BODY.index("def role_for("):BODY.index("def _require_perm(")]
    assert "except Exception" in look, (
        "a broken user store would 500 every authenticated request instead of degrading")
    assert "role_of(" in look, "the raw column is trusted instead of being interpreted"
