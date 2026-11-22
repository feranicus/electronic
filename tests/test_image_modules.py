"""test_image_modules.py — a module the app imports must be IN the image that runs it.

THE INCIDENT (22 Nov 2026). `main.py` gained `import roles` for the RBAC routes. `roles.py` sits
beside `colt_auth.py` and `user_store.py` in the repo root, and inside the container the ONLY
sys.path entry that can supply a root module is `/opt` — which holds exactly what the Dockerfile
COPYs there. Nothing copied roles.py, so `/api/admin/users` answered 500 and the Administration
page said "Could not load the user list." Everything else on the page worked, which is why it read
as a frontend bug.

THE SHAPE IS DEFECT CLASS 35, and the class text names the exact wiring point that was missed:
one module needed FOUR edits — `.dockerignore` (an allow-list: a path not named there is not even
in the build context), `webapp/Dockerfile`, `assess-bot/Dockerfile`, and the deploy pack lists in
`deploy_web_direct.INCLUDE` / `deploy.BOTS_INCLUDE`. Counting by hand is how the fourth is missed.

SO THIS TEST COUNTS NOTHING BY HAND. It parses each app's own imports, intersects them with the
repo's root modules, and demands every wiring point for each one. Adding a root module to main.py
and forgetting any single edit fails here, on the laptop, before the image is built.

WHY NOT JUST GREP FOR "roles.py" — because that is a test of this incident, not of the class. The
next module will have a different name, and a check that only knows the last failure is a check
that catches nothing new.
"""
import ast
import io
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def _root_modules():
    """Every importable .py at the repo root. This is the candidate set; nothing is hardcoded."""
    return {f[:-3] for f in os.listdir(ROOT)
            if f.endswith(".py") and not f.startswith("_")}


def _direct_imports(rel):
    """Top-level module names this file imports, INCLUDING the ones inside functions.

    `import roles as _roles` in main.py lives inside `admin_users()` and inside `_require_perm`'s
    dependency, not at module scope - so a scan that only read the file header would have declared
    the bug impossible. ast.walk covers both, which is the whole point of parsing rather than
    grepping the first twenty lines.
    """
    out = set()
    for n in ast.walk(ast.parse(_read(rel))):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            out.add(n.module.split(".")[0])
    return out


def _imports(rel):
    """The TRANSITIVE set of root modules this app needs.

    Found by a mutation that the first version of this file did not catch: dropping roles.py from
    the bots' pack list changed nothing, because `bot.py` never names roles - it imports
    user_store, and user_store imports roles inside set_role() to refuse an undefined one. A
    missing module two hops away is the same 500 as a missing module one hop away, and it is worse
    to diagnose because the import that fails is in a file nobody edited.

    Walking the graph is also what makes this a check about the CLASS rather than about today's
    module list: it follows whatever the code actually does.
    """
    roots = _root_modules()
    seen, queue = set(), [rel]
    while queue:
        cur = queue.pop()
        for m in _direct_imports(cur) & roots:
            if m not in seen:
                seen.add(m)
                queue.append(m + ".py")
    return seen


def _copied_into(dockerfile):
    """The root modules a Dockerfile puts on the container's sys.path, read from its COPY lines."""
    out = set()
    for ln in _read(dockerfile).split("\n"):
        ln = ln.strip()
        if not ln.startswith("COPY ") or "/opt/" not in ln:
            continue
        parts = ln.split()
        if len(parts) >= 3 and parts[1].endswith(".py") and "/" not in parts[1]:
            out.add(parts[1][:-3])
    return out


def _allowlisted_in_build_context():
    """.dockerignore starts with `*`, so it is an ALLOW-LIST: `!name.py` lines are the whole set."""
    out = set()
    for ln in _read(".dockerignore").split("\n"):
        ln = ln.strip()
        if ln.startswith("!") and ln.endswith(".py"):
            out.add(ln[1:-3])
    return out


# app -> (its source, the image that runs it, the deploy pack constant that ships that image)
APPS = [
    ("colt-web", "webapp/backend/app/main.py", "webapp/Dockerfile",
     ("deploy_web_direct.py", "INCLUDE")),
    ("colt-assessbot", "assess-bot/bot.py", "assess-bot/Dockerfile",
     ("deploy.py", "BOTS_INCLUDE")),
]


def _pack_list(rel, name):
    """The literal list assigned to `name` at module scope, read without importing the module -
    importing deploy.py would pull in ssh helpers and a network stack this test does not want."""
    for n in ast.walk(ast.parse(_read(rel))):
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", None) == name for t in n.targets):
            return {e.value for e in n.value.elts if isinstance(e, ast.Constant)}
    raise AssertionError("%s has no module-scope %s - the constant moved, and a constant a test "
                         "cannot read is an untested one" % (rel, name))


@pytest.mark.parametrize("app,src,dockerfile,pack", APPS,
                         ids=[a[0] for a in APPS])
def test_every_root_module_the_app_imports_is_in_its_image(app, src, dockerfile, pack):
    needed = _imports(src) & _root_modules()
    # A CHECK THAT CANNOT SEE ITS SUBJECT IS NOT A CHECK (class 1). If the intersection is empty
    # the parse found nothing and every assertion below would pass vacuously.
    assert needed, ("%s appears to import NO root module, which cannot be right - the parse or the "
                    "root listing is broken, not the wiring" % src)

    missing = sorted(needed - _copied_into(dockerfile))
    assert not missing, (
        "%s imports %s, and %s does not COPY it into /opt. Inside the container /opt is the only "
        "sys.path entry that can supply a root module, so this is a 500 on the first request that "
        "reaches the import - which is exactly what shipped on 22 Nov 2026."
        % (src, missing, dockerfile))

    out = sorted(needed - _allowlisted_in_build_context())
    assert not out, (
        "%s needs %s, and .dockerignore does not allow it into the build context. That file starts "
        "with `*`, so a path nobody names is excluded and the COPY fails the BUILD." % (src, out))

    packed = _pack_list(*pack)
    unpacked = sorted(m for m in needed if (m + ".py") not in packed)
    assert not unpacked, (
        "%s needs %s, and %s.%s does not ship it. The file would never reach the droplet, so the "
        "build has nothing to COPY." % (src, unpacked, pack[0], pack[1]))


def test_the_check_would_fail_if_a_needed_module_were_dropped():
    """PROVE THE GATE BY BREAKING WHAT IT GUARDS (class 3). A wiring test that passes against a
    broken wiring is the thing this file exists to prevent, so it is demonstrated here rather than
    asserted in prose."""
    needed = _imports("webapp/backend/app/main.py") & _root_modules()
    copied = _copied_into("webapp/Dockerfile")
    assert needed <= copied, "baseline is already broken; the demonstration below proves nothing"
    for victim in sorted(needed):
        assert needed - (copied - {victim}), (
            "dropping %s from the image leaves the check with nothing to report" % victim)


def test_roles_specifically_reached_both_images():
    """THE REGRESSION, named. The derived checks above are the real guard and would catch this
    without this test; it is here because class 17 says an incident keeps its own marker, so the
    next person reading a 500 on the Administration page finds the story."""
    for dockerfile in ("webapp/Dockerfile", "assess-bot/Dockerfile"):
        assert "roles" in _copied_into(dockerfile), (
            "roles.py is not in %s - the 22 Nov Administration-page 500 is back" % dockerfile)


# ---------------------------------------------------------------------------------------------
# A STATIC GUARD REASONS ABOUT THE DOCKERFILE; THE DEPLOY REASONS ABOUT THE RUNNING CONTAINER.
# Only one of those is the artifact (class 49), and the whole point of this incident is that the
# repo was right and the image was not. So the deploy must exercise it, on BOTH boxes.
# ---------------------------------------------------------------------------------------------
def _dwd():
    import importlib.util
    import sys
    sys.path.insert(0, ROOT)
    spec = importlib.util.spec_from_file_location("_dwd_for_test",
                                                  os.path.join(ROOT, "deploy_web_direct.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("proxy,where", [(True, "production"), (False, "staging")])
def test_every_deploy_path_checks_the_modules_inside_the_container(proxy, where):
    """STAGING ESPECIALLY. The twin rehearses the same bytes, so a missing module should be found
    there - letting staging skip this would leave production as the first box to discover it,
    which is exactly what happened on 22 Nov."""
    d = _dwd()
    for name, script in (("build", d.remote(proxy)), ("ghcr pull", d.remote_ghcr("t", proxy))):
        steps = [ln for ln in script.split("\n") if "importlib" in ln]
        assert len(steps) == 1, (
            "the %s %s path has %d module checks, expected exactly 1 - zero means the deploy "
            "cannot see a missing module, two means it has grown a second home"
            % (where, name, len(steps)))
        step = steps[0]
        for mod in _imports("webapp/backend/app/main.py") & _root_modules():
            assert '"%s"' % mod in step, (
                "%s is not in the %s %s check, so the deploy would not notice it missing"
                % (mod, where, name))


def test_the_derivation_refuses_to_answer_with_an_empty_list():
    """A CHECK THAT CANNOT SEE ITS SUBJECT MUST NOT ANSWER (class 1). An empty derivation would
    render a step that passes while measuring nothing - and that nearly shipped: the first version
    swallowed a NameError per file and returned an empty set for every one of them."""
    d = _dwd()
    assert d.root_modules_main_imports(), "the derivation is empty on a healthy tree"
    import builtins
    real = builtins.open

    def blind(path, *a, **k):
        if str(path).endswith("main.py"):
            raise OSError("simulated unreadable source")
        return real(path, *a, **k)

    builtins.open = blind
    try:
        with pytest.raises(SystemExit):
            d.root_modules_main_imports()
    finally:
        builtins.open = real


def test_the_module_list_is_rendered_with_double_quotes():
    """The payload sits inside a SINGLE-quoted shell argument, so repr() of a list would close the
    quoting mid-step and the failure would look like a droplet problem."""
    lit = _dwd()._module_literal()
    assert "'" not in lit, "the module literal uses single quotes: %s" % lit
    assert lit.startswith("[") and lit.endswith("]")
