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


# ---------------------------------------------------------------------------------------------
# THE STORE. A role is not a credential, and the whole feature turns on that distinction: almost
# everybody on the administration page signs in with the SHARED password and has no row in the
# credential table at all. The first version put a `role` column on that table, which cannot work
# for them - and the way it fails is the dangerous kind, because inventing a credential row makes
# user_store.has_account() true and TAKES THE SHARED PASSWORD AWAY. Naming somebody a Sales Rep
# would have locked them out.
# ---------------------------------------------------------------------------------------------
def _store(tmp_path, monkeypatch):
    monkeypatch.setenv("USER_DB", str(tmp_path / "u.sqlite"))
    import importlib
    import user_store
    importlib.reload(user_store)
    return user_store


def test_a_role_can_be_set_for_somebody_who_has_no_credential_row(tmp_path, monkeypatch):
    us = _store(tmp_path, monkeypatch)
    who = "armin.hall@colt.net"
    # PROVE THE FIXTURE REPRODUCES THE CONDITION (class 12): this is a shared-password user, which
    # is precisely the case the column could not serve.
    assert not us.has_account(who), "the fixture is not the case under test - this user has a row"

    assert us.set_role(who, "sales_rep", by="feranicus@s4biz.io") is True
    assert us.get_role(who) == "sales_rep"
    assert roles.role_of(who, us.get_role(who)) == "sales_rep"

    # AND THE SIDE EFFECT THAT MADE THE COLUMN WRONG MUST NOT HAPPEN.
    assert not us.has_account(who), (
        "assigning a role created a credential row - that removes this person's shared-password "
        "fallback, i.e. naming somebody a Sales Rep locks them out")
    assert us.get(who) is None, "a role wrote into the credential table"


def test_an_undefined_role_is_refused_rather_than_stored(tmp_path, monkeypatch):
    us = _store(tmp_path, monkeypatch)
    assert us.set_role("x@y.com", "wizard") is False
    assert us.get_role("x@y.com") == ""


def test_clearing_a_role_removes_the_row_rather_than_storing_the_default(tmp_path, monkeypatch):
    us = _store(tmp_path, monkeypatch)
    us.set_role("x@y.com", "presales")
    assert us.set_role("x@y.com", "") is True
    assert us.get_role("x@y.com") == ""
    assert "x@y.com" not in us.list_roles(), "a cleared role is still listed as a decision"


def test_the_listing_reads_every_role_in_one_query(tmp_path, monkeypatch):
    us = _store(tmp_path, monkeypatch)
    us.set_role("a@b.com", "presales")
    us.set_role("c@d.com", "company_admin")
    assert us.list_roles() == {"a@b.com": "presales", "c@d.com": "company_admin"}


def test_nothing_reads_the_dead_role_column():
    """The column still exists because the droplet has it and a schema that differs between boxes
    is its own class of bug. It must stay dead: two homes for one fact and the newer one loses."""
    src = io.open(os.path.join(ROOT, "user_store.py"), encoding="utf-8").read()
    # ASSERT THE PROPERTY, NOT A SUBSTRING (class 4). "SET role=" also matches the legitimate
    # user_roles upsert, so the first version of this check failed on the correct code. The real
    # property is per STATEMENT: a statement that mentions the role column must be talking about
    # user_roles, and the ALTER that keeps the schemas identical is the one exception.
    import re
    sql = [n.value for n in ast.walk(ast.parse(src))
           if isinstance(n, ast.Constant) and isinstance(n.value, str)
           and re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|ALTER TABLE)\b", n.value)]
    assert sql, "no SQL was found at all - this check cannot see its subject"
    for s in sql:
        if not re.search(r"\brole\b", s):
            continue
        if s.strip().startswith("ALTER TABLE users ADD COLUMN role"):
            continue                       # the dead column, kept so every box has one schema
        assert "user_roles" in s, "a statement touches users.role: %r" % " ".join(s.split())[:90]
    assert any("CREATE TABLE IF NOT EXISTS user_roles" in s for s in sql), "the role table is gone"


# ---------------------------------------------------------------------------------------------
# THE ROUTE. Two refusals belong to this endpoint rather than to the policy, and both are about
# recovery: a person who edits their own role can demote themselves out of the page that would
# undo it, and a committed ADMIN_EMAILS address would be given a row the server then ignores.
# ---------------------------------------------------------------------------------------------
def _role_route():
    i = BODY.index("def admin_set_role(")
    j = BODY.find("\n@app.", i)
    return BODY[i:j if j > 0 else len(BODY)]


def test_the_route_refuses_a_self_edit_and_the_committed_admin_floor():
    r = _role_route()
    assert "you cannot change your own role" in r, "an administrator can demote themselves"
    assert "colt_auth.is_admin(target)" in r, (
        "a committed ADMIN_EMAILS address can be given a role the server will ignore")


def test_the_route_asks_the_policy_and_does_not_restate_it():
    r = _role_route()
    assert "_roles.may_grant(" in r and "_roles.may_touch(" in r, (
        "the route decides for itself instead of asking roles.py")
    # ONE HOME: no rank arithmetic, no role names, no permission strings inline.
    for frag in ('"admin"', "rank", "users.invite", "ROLES["):
        assert frag not in r, "the route restates the policy: %r" % frag
    assert "role_denied" in r, "a refusal is not logged, so a complaint cannot be diagnosed"


def test_the_listing_reports_the_effective_role_not_the_stored_one():
    """colt_auth.ADMIN_EMAILS wins over any row. A page that showed the raw column would be
    answering a different question than the one the server enforces."""
    i = BODY.index("def admin_users(")
    j = BODY.index("class AdminRoleReq")
    listing = BODY[i:j]
    assert "_roles.role_of(" in listing, "the raw stored value is displayed"
    assert "list_roles()" in listing, "the listing looks the role up per user"
    assert '"grantable"' in listing and '"roles"' in listing, (
        "the picker would have to hardcode the catalogue, which drifts from roles.py")


# ---------------------------------------------------------------------------------------------
# THE PICKER. Class 35: derive N from something authoritative. A role added to roles.py with no
# label here renders as a raw key in the product.
# ---------------------------------------------------------------------------------------------
def test_every_role_has_a_label_in_every_interface_language():
    admin_jsx = io.open(os.path.join(ROOT, "webapp", "frontend", "src", "pages", "Admin.jsx"),
                        encoding="utf-8").read()
    block = admin_jsx[admin_jsx.index("const ROLE_LABEL"):]
    block = block[:block.index("};")]
    for key in roles.ROLES:
        assert key + ":" in block, "%s has no label in Admin.jsx" % key

    import re
    wanted = set(re.findall(r't\("(admin\.role[A-Za-z0-9]*)"\)', block))
    assert len(wanted) == len(roles.ROLES), (
        "expected one label key per role, found %d for %d roles" % (len(wanted), len(roles.ROLES)))
    loc = os.path.join(ROOT, "webapp", "frontend", "src", "locales")
    for code in ("en", "de", "it", "fr", "es", "pl"):
        src = io.open(os.path.join(loc, code + ".js"), encoding="utf-8").read()
        missing = sorted(k for k in wanted if ('"%s"' % k) not in src)
        assert not missing, "%s is missing role labels: %s" % (code, missing)
