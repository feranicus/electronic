"""test_pipeline_architecture.py - the CI pipeline must not become a second home for anything.

THE SHAPE THIS REPLACES, measured from one real ship on 2026-10-15:

    colt-web                   shipped by the LAPTOP, BUILT ON PRODUCTION      11:52:00Z
    colt-assessbot, cassandra  shipped by CI from GHCR images                  11:58:28Z

Two owners, one droplet, six minutes apart; only the order they happened to run in kept them from
colliding. And the one INTERNET-FACING image was the one image CI had never seen, because it was
compiled on the production host at deploy time.

The architecture that replaced it rests on four properties. Each is a sentence, and each is
asserted here rather than described in a comment, because the whole point of this repo's defect
list is that a rule which is only written down goes stale:

  1. ONE GATE. The required check runs ship.py's OWN test phase, not a copy of its gate list.
  2. ONE AUTOMATIC PATH to production.
  3. ONE ARTIFACT. Production pulls the image CI built and scanned; it never compiles.
  4. ONE DEPLOY AT A TIME, across runners AND laptops.
"""
import glob
import json
import os
import re
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")
sys.path.insert(0, ROOT)


def load(name):
    with open(os.path.join(WF, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def dump(x):
    """yaml.dump WRAPS AT 80 COLUMNS by default, which silently breaks long shell lines in half and
    makes every substring assertion below fail against text that is actually present. Two checks in
    this file failed that way on their first run: they were asserting about a re-wrapped rendering
    of the step, not the step. Width is pinned so the dump is a faithful view of the value."""
    return yaml.dump(x, width=10 ** 9, default_flow_style=False)


def runs(steps):
    """ONLY the shell that actually executes.

    Three mutations escaped this file on its first run because the assertions matched a step NAME
    ("Gates (python ship.py --test)") or an explanatory COMMENT ("# --network none is deliberate")
    instead of the command. Asserting on a string the surrounding prose also contains is defect
    class 4, and it is how a check matches its own documentation and reports health.
    """
    return "\n".join(str(s.get("run", "")) for s in steps)


def triggers(doc):
    # PyYAML resolves the bare key `on:` to the boolean True (YAML 1.1). Reading doc["on"] returns
    # None and every assertion built on it passes vacuously - a check that cannot fail.
    t = doc.get(True)
    if t is None:
        t = doc.get("on")
    return t if isinstance(t, dict) else {}


def test_the_yaml_trap_that_would_make_every_check_here_vacuous():
    """PROVE THE FIXTURE (defect class 12). If triggers() silently returned {} for every workflow,
    every assertion below would pass while measuring nothing."""
    t = triggers(load("pipeline.yml"))
    assert t, "triggers() read nothing - `on:` was parsed as the boolean True and not handled"
    assert "push" in t


# ----------------------------------------------------------------- 1. ONE GATE
def test_the_required_check_runs_ship_pys_own_test_phase():
    """The ruleset requires `quality-and-secrets`, so that job decides what "main is protected"
    MEANS. Until 2026-10-15 it meant `ruff check . || true` (a check that cannot fail, defect
    class 3), `node --check` (PARSE is not RUN, class 48) and the unit suite only - none of the 37
    engine gates. A commit ship.py would refuse could turn it green."""
    steps = load("ci.yml")["jobs"]["quality-and-secrets"]["steps"]
    body = runs(steps)          # the COMMANDS, not the step names
    assert "ship.py --test" in body, (
        "the gate of record does not run the orchestrator's own test phase, so CI and the laptop "
        "can disagree about what must pass")
    assert "|| true" not in body, "a step that cannot fail is in the gate of record"
    # The toolchain is pinned by an action input, not a shell line, so look where it actually
    # lives rather than widening the command search until something matches.
    built = [st for st in steps if (st.get("with") or {}).get("file") == "Dockerfile.ci"]
    assert built, "the gate does not build its pinned toolchain image"


def test_the_gate_cannot_touch_anything():
    """A gate that can write is not a gate, it is a deploy. do_tests() has exactly one branch that
    could write to the droplet and SHIP_GATES_OFFLINE=1 refuses it out loud."""
    steps = runs(load("ci.yml")["jobs"]["quality-and-secrets"]["steps"]) + dump(
        [s.get("env") or {} for s in load("ci.yml")["jobs"]["quality-and-secrets"]["steps"]])
    assert "SHIP_GATES_OFFLINE=1" in steps
    assert "--network none" in steps, (
        "tests must not reach the internet (defect class 18); the gate does not enforce it")
    assert "DROPLET_SSH_KEY" not in steps, "the gate was handed a production credential"
    assert "secrets." not in steps.replace("secrets.GITHUB_TOKEN", ""), (
        "the gate was handed a secret; it must have nothing to change anything with")


def test_the_gate_phase_really_is_side_effect_free():
    """Not a claim about YAML - a claim about ship.py, asserted against ship.py. do_tests() must
    make no ssh call, because CI runs it on every pull request."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read())
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "do_tests"][0]
    ssh = [ast.unparse(c)[:70] for c in ast.walk(fn)
           if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
           and c.func.id in ("ssh", "ssh_script")]
    assert not ssh, "do_tests() now opens an ssh session; CI must not run it: %s" % ssh
    src = ast.unparse(fn)
    assert "GATES_OFFLINE" in src, (
        "the one droplet-writing branch is no longer guarded by SHIP_GATES_OFFLINE")


def test_the_checkout_is_mounted_read_only_and_the_gate_works_on_a_copy():
    """THE 124 "BROKEN" FILES, 2026-10-15. The first gate run that got past gitleaks reported every
    python file in the repo as broken. Not one of them was: `python -m py_compile` writes the .pyc
    into __pycache__ beside the source, the checkout belongs to the runner, the container is uid
    10001, and so all 124 failed with EACCES - a permissions fact rendered as a syntax verdict.

    do_tests() also refreshes the git index and can regenerate the SBOM, so this was never going to
    be fixed one writer at a time. The gate gets a workspace it owns, and `:ro` turns "the gate
    phase is side-effect free" - the claim that makes it safe to run on every pull request - into
    something the kernel enforces instead of something a comment asserts.
    """
    steps = runs(load("ci.yml")["jobs"]["quality-and-secrets"]["steps"])
    assert ":ro" in steps, (
        "the checkout is no longer mounted read-only. A gate that can modify the tree it is "
        "judging can also make itself pass.")
    assert "-v \"$PWD:/src\" -w /src" not in steps, (
        "the gate is running IN the mounted checkout again; that is the configuration that "
        "produced 124 false 'broken' files")
    assert "GATE_WORKDIR" in steps, (
        "the gate no longer runs in its own writable workspace")


def test_the_compile_gate_does_not_need_to_write_next_to_the_source():
    """The specific mechanism, pinned so it cannot come back. `py_compile` exists to WRITE
    bytecode; the image even sets PYTHONDONTWRITEBYTECODE=1, which py_compile ignores by design.
    Compiling in-process needs no write, no subprocess and no mount, and raises SyntaxError on
    exactly what this gate is for."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read())
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "do_tests"][0]
    src = ast.unparse(fn)
    assert "py_compile" not in src, (
        "do_tests() shells out to py_compile again. It writes __pycache__ beside the source, so "
        "it fails on a read-only or foreign-owned tree and reports that as broken code.")
    assert "compile(" in src, "the compile gate no longer compiles anything"


#: Node builtins a gate script may use with no package.json entry, bare or `node:`-prefixed.
_NODE_BUILTINS = {
    "assert", "buffer", "child_process", "console", "crypto", "dns", "events", "fs", "http",
    "https", "module", "net", "os", "path", "perf_hooks", "process", "querystring", "readline",
    "stream", "string_decoder", "timers", "tls", "url", "util", "v8", "vm", "worker_threads",
    "zlib",
}
_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
_IMPORT = re.compile(r"""^\s*import\s[^;\n]*?from\s*['"]([^'"]+)['"]""", re.M)


def _gate_js_dependencies():
    """Every third-party module the gate-run JavaScript actually imports, read FROM the source.

    Derived, never hand-listed (defect class 35): the whole reason CI broke is that somebody
    measured one directory and wrote a conclusion about all of them.
    """
    found = {}
    for sub in ("webapp/frontend/tools", "hermes-skills/shodan-assessment/scripts"):
        d = os.path.join(ROOT, sub)
        for dirpath, _dirs, files in os.walk(d):
            if "node_modules" in dirpath:
                continue
            for f in files:
                if not f.endswith((".js", ".mjs")):
                    continue
                p = os.path.join(dirpath, f)
                src = open(p, encoding="utf-8", errors="replace").read()
                for spec in _REQUIRE.findall(src) + _IMPORT.findall(src):
                    if spec.startswith((".", "/")):
                        continue
                    name = spec[5:] if spec.startswith("node:") else spec
                    base = name.split("/")[0]
                    if base in _NODE_BUILTINS:
                        continue
                    found.setdefault(base, os.path.relpath(p, ROOT).replace("\\", "/"))
    return found


def test_the_gate_image_installs_the_node_dependencies_the_gates_actually_import():
    """CI died with `Cannot find module 'pptxgenjs'` because Dockerfile.ci claimed no node_modules
    were needed. That claim was true of webapp/frontend/tools - which import only builtins - and
    false of the engine's five deck builders, which all require pptxgenjs. The node_modules on the
    operator's box is gitignored, so the checkout CI gets has none and his machine could never
    reveal this.

    This asserts the real property: every third-party module the gate JavaScript imports is
    declared in the committed package.json the image installs from. A new dependency added to the
    engine fails HERE, on his laptop, rather than after a push.
    """
    deps = _gate_js_dependencies()
    declared = set(json.load(open(
        os.path.join(ROOT, "hermes-skills", "shodan-assessment", "package.json"),
        encoding="utf-8")).get("dependencies", {}))
    missing = {k: v for k, v in deps.items() if k not in declared}
    assert not missing, (
        "gate JavaScript imports %d module(s) that hermes-skills/shodan-assessment/package.json "
        "does not declare, so the CI image will not install them and the gate dies with "
        "MODULE_NOT_FOUND: %s" % (len(missing), missing))
    assert deps, "the dependency scan found nothing at all - it is reading the wrong tree"


def test_the_web_stack_is_pinned_not_floored():
    """A FLOOR MEANS NOBODY CAN SAY WHAT WAS TESTED.

    requirements.txt already argues this at length for python-multipart - "a floor defeats the
    immutability guarantee", because pip resolves independently in every build. starlette was
    never held to it: `starlette>=1.3.1` let the CI image and the operator's machine land on
    different releases, and two white-label tests then failed in CI and passed locally because
    which responses poll for a client disconnect had changed between them.

    Only the packages that actually serve requests are required to be exact. A floor on a library
    that cannot change request handling is a different, smaller question, and a guard that
    demanded exactness everywhere would be noise.
    """
    req = os.path.join(ROOT, "webapp", "backend", "requirements.txt")
    serves_traffic = {"fastapi", "starlette", "uvicorn", "python-multipart"}
    floored = []
    for raw in open(req, encoding="utf-8"):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name = line
        for sep in ("[", "<", ">", "=", "!", "~", ";", " "):
            name = name.split(sep, 1)[0]
        if name.strip().lower() in serves_traffic and "==" not in line:
            floored.append(line)
    assert not floored, (
        "these serve HTTP and are declared with a floor, so every image build may resolve a "
        "different release than the one the suite ran against: %s" % floored)


def test_the_image_installs_from_the_lockfile_and_node_can_find_it():
    """`npm ci` not `npm install`, so the image gets exactly what the committed lockfile pins and
    cannot drift. NODE_PATH because the gate runs against a COPY of the checkout, and a checkout
    contains no node_modules - resolution has to work from wherever that copy lands."""
    # STRIP THE COMMENTS FIRST (defect class 4). Both of these assertions originally passed
    # against a Dockerfile whose `npm ci` and NODE_PATH had been removed, because the long comment
    # explaining WHY they exist still contained both strings. A check that matches its own
    # rationale measures nothing. CLAUDE.md records this happening five separate times; six now.
    raw = open(os.path.join(ROOT, "Dockerfile.ci"), encoding="utf-8").read()
    df = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
    assert "npm ci" in df, (
        "the gate image no longer installs node dependencies from the lockfile; the deck builders "
        "will fail with MODULE_NOT_FOUND")
    assert "NODE_PATH" in df, (
        "nothing tells node where those modules are, and they are not inside the copied workspace")
    assert "package-lock.json" in df, "npm ci without the lockfile copied in cannot run"


# ----------------------------------------------------------------- 2. ONE AUTOMATIC PATH
def test_exactly_one_workflow_deploys_on_push():
    """Two automatic paths to one droplet is the defect this pipeline was built to remove."""
    deployers = []
    for f in sorted(glob.glob(os.path.join(WF, "*.yml"))):
        doc = yaml.safe_load(open(f, encoding="utf-8"))
        if "push" not in triggers(doc):
            continue
        for job, spec in (doc.get("jobs") or {}).items():
            body = dump(spec)
            if any(k in body for k in ("deploy.py", "deploy_web_direct.py", "docker compose")):
                deployers.append("%s::%s" % (os.path.basename(f), job))
    assert deployers == ["pipeline.yml::production"], (
        "expected exactly one push-triggered deploy job, found: %s" % deployers)


def test_production_waits_for_a_human_and_for_staging():
    prod = load("pipeline.yml")["jobs"]["production"]
    assert prod.get("environment") == "production", "no required reviewer gate on production"
    assert "staging" in prod["needs"], "production does not wait for the staging gate"
    assert "scan" in prod["needs"], "production does not wait for the scanner"


def test_the_reboot_gate_is_the_staging_job():
    """The reboot is the one test production can never run, and it is what catches the outage
    class that took six domains down together. CI must RUN stagegate.py, not re-implement it."""
    body = dump(load("pipeline.yml")["jobs"]["staging"])
    assert "stagegate.py" in body
    assert "docker compose" not in body, "the staging job reimplements a deploy instead of calling one"


# ----------------------------------------------------------------- 3. ONE ARTIFACT
def test_production_pulls_the_scanned_image_and_never_compiles_one():
    """What was scanned is what runs. Building on the production host means the scanner inspected
    a different artifact than the one serving traffic."""
    steps = load("pipeline.yml")["jobs"]["production"]["steps"]
    web = [st for st in steps if "deploy_web_direct.py" in str(st.get("run", ""))]
    assert len(web) == 1, "expected exactly one colt-web deploy step, found %d" % len(web)
    assert "--ghcr" in web[0]["run"], (
        "the colt-web step does not name a pre-built image, so production compiles the only "
        "internet-facing artifact at deploy time - the shape this pipeline exists to remove")
    body = runs(steps)
    assert "--build" not in body, "production builds an image at deploy time"
    for forbidden in ("docker build", "docker compose build"):
        assert forbidden not in body, "production compiles: %r" % forbidden


def test_the_scanner_sees_every_image_that_is_deployed():
    """DERIVE N FROM SOMETHING AUTHORITATIVE (defect class 35): the scan matrix must cover every
    image the build job publishes, so a fourth image added later cannot ship unscanned."""
    doc = load("pipeline.yml")
    built = set()
    for step in doc["jobs"]["build"]["steps"]:
        tags = (step.get("with") or {}).get("tags", "")
        for t in str(tags).split(","):
            t = t.strip()
            if "/" in t and ":" in t:
                built.add(t.rsplit("/", 1)[1].split(":")[0])
    scanned = set(doc["jobs"]["scan"]["strategy"]["matrix"]["image"])
    assert built, "no images parsed from the build job - this check stopped measuring"
    assert built <= scanned, "built but never scanned: %s" % sorted(built - scanned)


def test_a_critical_finding_stops_the_promotion():
    body = dump(load("pipeline.yml")["jobs"]["scan"])
    assert "--severity CRITICAL" in body and "--exit-code 1" in body, (
        "the scanner reports CRITICAL without failing, which is a report, not a gate")
    assert "sha256sum -c" in body, "Trivy is not checksum-verified; the scanner is a dependency too"


# ----------------------------------------------------------------- 4. ONE DEPLOY AT A TIME
@pytest.mark.parametrize("job", ["staging", "production"])
def test_every_droplet_job_joins_the_same_queue(job):
    spec = load("pipeline.yml")["jobs"][job]
    assert (spec.get("concurrency") or {}).get("group") == "production-droplet", (
        "%s touches a droplet outside the shared queue" % job)
    assert (spec.get("concurrency") or {}).get("cancel-in-progress") is False, (
        "%s can be cancelled mid-deploy, which leaves the droplet half-applied" % job)


def test_production_takes_the_lock_a_concurrency_group_cannot_replace():
    """A concurrency group serialises CI against CI. It cannot see `python ship.py` on a laptop,
    and with two developers that is the collision that matters."""
    steps = dump(load("pipeline.yml")["jobs"]["production"]["steps"])
    assert "teamlock.py --acquire" in steps
    assert "teamlock.py --release" in steps
    rel = [s for s in load("pipeline.yml")["jobs"]["production"]["steps"]
           if "teamlock.py --release" in dump(s)]
    assert rel and rel[0].get("if") == "always()", (
        "the lock is released only on success, so a failed deploy wedges the droplet for 45 min")


# ----------------------------------------------------------------- the key install has one home
def test_no_workflow_hand_rolls_the_deploy_key_install():
    """Five workflows used to carry the same four lines. The composite action is the one home, and
    it is the only place that knows a key must be written as BYTES and then PROVEN."""
    offenders = []
    for f in sorted(glob.glob(os.path.join(WF, "*.yml"))):
        s = open(f, encoding="utf-8").read()
        if "pipeline.yml" not in f and "secrets.DROPLET_SSH_KEY" in s and "actions/ssh-key" not in s:
            if "printf '%s\\n'" in s:
                offenders.append(os.path.basename(f))
    # deploy.yml / web-deploy.yml are dispatch-only fallbacks; they are allowed to keep their own
    # copy until they are retired, but the AUTOMATIC path must use the shared action.
    assert "pipeline.yml" not in offenders
    body = open(os.path.join(WF, "pipeline.yml"), encoding="utf-8").read()
    assert "./.github/actions/ssh-key" in body
    # READ THE FILE, NOT A RE-RENDERING OF IT. A yaml round-trip re-quotes the shell block, so
    # `-P ""` comes back as `-P \"\"` and an assertion about the real command fails against text
    # that is genuinely there. That is the same defect as asserting on a string the error message
    # also contains (class 4): match the artifact, not your view of it.
    run = open(os.path.join(ROOT, ".github", "actions", "ssh-key", "action.yml"),
               encoding="utf-8").read()
    assert "ssh-keygen -l -f" in run, "the action does not NAME the key it installed"
    assert "ssh-keygen -y" in run and '-P ""' in run, "the action does not prove the key is usable"
    assert "$DEPLOY_KEY" in run, "the key is interpolated into the command line instead of env"
