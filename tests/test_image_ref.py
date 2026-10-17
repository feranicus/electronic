"""The image name had THREE homes and they disagreed (defect class 32).

THE INCIDENT, 2026-10-16. A full pipeline run - gate green, three images built, signed, scanned -
died at the staging gate on:

    Image ghcr.io/feranicus/colt-web:c6d051e729cc Pulling
    failed to resolve reference "ghcr.io/feranicus/colt-web:c6d051e729cc": not found
    [!] staging build failed (exit 1)

Nothing in that log is wrong, and nothing in it is the cause. CI pushes to
`ghcr.io/${{ github.repository }}/colt-web` = **ghcr.io/feranicus/electronic/colt-web**. The pull
came from docker-compose.web.yml, which hardcoded **ghcr.io/feranicus/colt-web**. Two different
packages, one character class apart, and only WEB_TAG was ever passed from CI to the droplet - the
repository half was spelled out independently in compose, web-deploy.yml and deploy_web_direct.py.

GHCR returns 404 for a package you are not allowed to see, so "not found" never distinguished
"this tag was never pushed" from "this package is private". That is why a name mismatch could
survive an entire run looking like an infrastructure fault.

The fix is ONE HOME (`ghcr.py`) plus this guard, which DERIVES the set of spellings from the files
themselves rather than hand-listing them (class 35: counting by hand is how the fourth one is
missed).
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys  # noqa: E402

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import ghcr  # noqa: E402

COMPOSE = os.path.join(ROOT, "docker-compose.web.yml")
PIPELINE = os.path.join(ROOT, ".github", "workflows", "pipeline.yml")


def _read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def test_the_compose_image_is_not_hardcoded_to_one_registry_path():
    """THE BUG, as the property. The repository half must be substitutable, because CI and the
    laptop push to different paths and only one of them can be the hardcoded default."""
    text = _read(COMPOSE)
    line = next(ln for ln in text.splitlines()
                if ln.strip().startswith("image:") and "colt-web" in ln)
    assert "${WEB_IMAGE" in line, (
        "docker-compose.web.yml pins the repository, so whatever CI pushes to is ignored and the "
        "pull 404s: %s" % line.strip())
    assert "${WEB_TAG" in line, line.strip()


def test_ci_passes_BOTH_halves_of_the_name_to_the_gate():
    """BEHAVIOUR AND WIRING (class 9). A substitutable compose file is worth nothing if the
    pipeline still only exports the tag - the default would silently win again."""
    text = _read(PIPELINE)
    assert re.search(r"^\s*WEB_IMAGE:", text, re.M), (
        "pipeline.yml exports WEB_TAG but not WEB_IMAGE, so the droplet falls back to compose's "
        "default repository - which is the package CI does NOT push to")
    assert re.search(r"^\s*WEB_TAG:", text, re.M), text[:200]


def test_the_pushed_name_and_the_pulled_name_are_the_same_expression():
    """DERIVE THE COMPARISON (class 35). Both sides are read out of the workflow and compared;
    neither is restated here, so a future rename cannot pass by editing only one of them."""
    text = _read(PIPELINE)
    pushed = set(re.findall(r"tags:\s*\$\{\{\s*env\.(\w+)\s*\}\}/colt-web:", text))
    pulled = set(re.findall(r"WEB_IMAGE:\s*\$\{\{\s*env\.(\w+)\s*\}\}/colt-web", text))
    assert pushed, "no colt-web push found in pipeline.yml; this guard is reading the wrong file"
    assert pulled, "no WEB_IMAGE derived from the same variable the build pushes to"
    assert pushed == pulled, (
        "the build pushes colt-web under env.%s and the staging gate pulls it under env.%s - "
        "that is the 2026-10-16 'not found' exactly"
        % (sorted(pushed), sorted(pulled)))


def test_the_deploy_script_exports_the_repository_not_only_the_tag():
    src = _read(os.path.join(ROOT, "deploy_web_direct.py"))
    body = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    assert "WEB_IMAGE" in body, (
        "deploy_web_direct.py exports WEB_TAG only, so compose's default repository decides which "
        "package is pulled")


# ---------------------------------------------------------------------------------------------
# THE DIAGNOSIS. "not found" means two unrelated things and docker cannot tell you which.
# ---------------------------------------------------------------------------------------------

def _fetch(table):
    """A fake registry. Keys are (url-substring, authenticated) -> (status, body)."""
    def go(url, headers):
        authed = "Authorization" in headers
        for (frag, want_auth), resp in table.items():
            if frag in url and want_auth == authed:
                return resp
        return 404, ""
    return go


def test_split_handles_a_deep_repository_path():
    """`feranicus/colt-web` and `feranicus/electronic/colt-web` are different packages. A parser
    that assumes two segments is how the two names looked interchangeable in the first place."""
    assert ghcr.split("ghcr.io/feranicus/electronic/colt-web:abc123") == (
        "feranicus/electronic/colt-web", "abc123")
    assert ghcr.split("ghcr.io/feranicus/colt-web:abc123") == ("feranicus/colt-web", "abc123")
    assert ghcr.split("ghcr.io/feranicus/colt-web") == ("feranicus/colt-web", "latest")


def test_a_PRIVATE_package_is_not_reported_as_a_missing_tag():
    """THE DISTINCTION THAT COSTS RUNS. Anonymous 404 + authenticated 200 = private, and the
    repair is a login, not a rebuild."""
    table = {("/token", False): (200, '{"token":"t"}'),
             ("/token", True): (200, '{"token":"t"}'),
             ("/manifests/", False): (404, ""),
             ("/manifests/", True): (200, "{}"),
             ("/tags/list", True): (200, '{"tags":["abc123"]}')}
    out = ghcr.report("ghcr.io/feranicus/electronic/colt-web:abc123", token="x",
                      fetch=_fetch(table))
    assert "logged in" in out or "PRIVATE" in out, out
    assert "never pushed" not in out, (
        "a private package was reported as a missing tag - opposite repair: %s" % out)


def test_a_TAG_THAT_WAS_NEVER_PUSHED_names_the_tags_that_DO_exist():
    """This is the line that would have ended the 2026-10-16 run in one step."""
    table = {("/token", False): (200, '{"token":"t"}'),
             ("/token", True): (200, '{"token":"t"}'),
             ("/manifests/", False): (404, ""),
             ("/manifests/", True): (404, ""),
             ("/tags/list", True): (200, '{"tags":["aaaa1111","bbbb2222"]}')}
    out = ghcr.report("ghcr.io/feranicus/colt-web:c6d051e729cc", token="x", fetch=_fetch(table))
    assert "aaaa1111" in out, "the tags that DO exist were not printed: %s" % out
    assert "is NOT in it" in out or "never pushed" in out, out


def test_without_a_token_it_REFUSES_to_choose_between_the_two():
    """A check that cannot see its subject must not answer (class 1). With no credential the two
    causes are genuinely indistinguishable, and saying so is the correct output."""
    table = {("/token", False): (200, '{"token":"t"}'),
             ("/manifests/", False): (404, ""),
             ("/tags/list", False): (404, "")}
    out = ghcr.report("ghcr.io/feranicus/colt-web:abc", token=None, fetch=_fetch(table))
    assert "NOT TESTED" in out, out
    assert "never pushed" not in out and "PRIVATE" not in out, (
        "it picked a cause with no evidence to separate them: %s" % out)


def test_a_dead_registry_is_not_read_as_a_missing_image():
    """Status 0 is a transport failure. Scoring it as a 404 would blame the build for a network
    fault (class 1, the one this whole module exists to stop)."""
    out = ghcr.report("ghcr.io/feranicus/colt-web:abc", token=None,
                      fetch=lambda u, h: (0, ""))
    assert "could not be reached" in out, out
    assert "never pushed" not in out, out


def test_the_report_never_prints_the_credential():
    """This repository is PUBLIC and so are its CI logs."""
    secret = "ghp_THISMUSTNEVERAPPEAR0000000000000000"
    out = ghcr.report("ghcr.io/feranicus/colt-web:abc", token=secret,
                      fetch=lambda u, h: (404, ""))
    assert secret not in out, "the GHCR diagnosis leaked its token into the log"
    import base64
    assert base64.b64encode(("x:" + secret).encode()).decode() not in out, out


def test_the_failure_path_actually_CALLS_the_diagnosis():
    """BEHAVIOUR AND WIRING (class 9). The best report in the world is worth nothing if the
    deploy still exits with 'rc=1' and prints nothing."""
    import ast
    src = _read(os.path.join(ROOT, "deploy_web_direct.py"))
    tree = ast.parse(src)
    calls = [ast.unparse(n) for n in ast.walk(tree)
             if isinstance(n, ast.Call) and "report" in ast.unparse(n.func)
             and "ghcr" in ast.unparse(n.func)]
    assert calls, (
        "nothing in deploy_web_direct.py calls ghcr.report(), so a pull failure still prints "
        "only docker's ambiguous 'not found'")


def test_an_anonymous_pull_says_so_out_loud():
    """A SKIP MUST BE LOGGED (class 37). Pulling without a token is legitimate for a public
    package and fatal-looking for a private one; silence makes the log unreadable either way."""
    import deploy_web_direct
    for env in ({}, {"GHCR_TOKEN": "t"}):
        old = {k: os.environ.get(k) for k in ("GHCR_TOKEN", "GITHUB_TOKEN")}
        try:
            os.environ.pop("GHCR_TOKEN", None)
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.update(env)
            script = deploy_web_direct.remote_ghcr("abc", proxy=False, image="ghcr.io/o/r/i")
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        assert "ghcr:" in script, "the login step reports nothing at all: %s" % script[:400]
        if env:
            assert "docker login ghcr.io" in script, script[:400]
        else:
            assert "NO token" in script, (
                "an anonymous pull is silent, so a 404 from a private package is unreadable")


def test_the_token_never_travels_in_argv():
    """The operator's standing rule, and the reason set_secret.py takes stdin: a value in argv is
    visible in `ps` to every user on the box."""
    import deploy_web_direct
    os.environ["GHCR_TOKEN"] = "tok_example_value"
    try:
        script = deploy_web_direct.remote_ghcr("abc", proxy=False, image="ghcr.io/o/r/i")
    finally:
        os.environ.pop("GHCR_TOKEN", None)
    assert "--password-stdin" in script, script[:400]
    assert "--password tok_example_value" not in script, "the token was put on the command line"
    assert "-p tok_example_value" not in script, "the token was put on the command line"


def test_the_staging_job_may_actually_read_the_package():
    """A token without `packages: read` is valid and still gets a 404 - which reads exactly like
    a missing tag, i.e. the same dead end by another route.

    PARSE THE JOB, DO NOT SLICE THE TEXT (class 4). The first version of this cut the file at
    "staging:" and at "\\n  production", and when the second anchor did not match it kept the rest
    of the FILE - which contains the production job's own `packages: read`. The mutation that
    stripped the permission from the staging job passed. A guard that reads the wrong region is
    measuring something, just not its subject (class 1).
    """
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(_read(PIPELINE))
    jobs = doc.get("jobs") or {}
    assert "staging" in jobs, "no staging job in pipeline.yml; this guard reads the wrong file"
    perms = jobs["staging"].get("permissions") or {}
    assert perms.get("packages") == "read", (
        "the staging job's permissions are %r - without `packages: read` its token cannot see "
        "the package, so the pull 404s indistinguishably from a missing tag" % (perms,))


def test_the_login_line_really_pipes_the_TOKEN_and_not_a_literal_percent_s():
    """DEFECT CLASS 44, caught by READING THE GENERATED SCRIPT (class 49).

    The first version of the login step was written as `printf '%%s' ...` out of habit - but that
    string is CONCATENATED, not %-formatted, so the doubling never collapses and the shell sees
    `printf '%%s'`, which prints the two characters `%s`. docker login would have been handed the
    literal text "%s" as the password on every CI pull, failed, and - because a failed login makes
    a private package answer 404 - reported itself as a missing tag. The exact dead end this whole
    change exists to remove, reintroduced by the fix for it.

    Nothing in the Python source looks wrong. Only the artifact does.
    """
    import deploy_web_direct
    os.environ["GHCR_TOKEN"] = "tok_example_value"
    try:
        script = deploy_web_direct.remote_ghcr("abc", proxy=False, image="ghcr.io/o/r/i")
    finally:
        os.environ.pop("GHCR_TOKEN", None)
    login = next(ln for ln in script.splitlines() if "docker login" in ln)
    assert "%%s" not in login, (
        "the login line carries a literal %%s - printf will pipe the characters '%%s' instead of "
        "the token, docker login fails, and a private package then 404s as a 'missing tag': %s"
        % login)
    assert "tok_example_value" in login, login
    assert login.index("printf") < login.index("docker login"), login


def test_the_generated_script_is_valid_shell():
    """PARSE IS NOT RUN (class 48) - and a script assembled by concatenation is exactly where an
    unbalanced quote hides. `bash -n` is the cheapest proof that the droplet can read it.

    TWO OF MY OWN DEFECTS, both caught by his gate on the first real run [2026-10-16]:

    * I gated on `shutil.which("bash")`. CLAUDE.md forbids precisely that: `shell_harness_allowed()`
      is the ONE HOME for "may this machine host a POSIX-shell harness", because on this operator's
      box `bash` IS on PATH - it is WSL's bash.exe - so `which` answers yes and the harness then
      tests the emulation layer instead of the droplet.
    * I handed bash a path. `tempfile.mkstemp()` returns `C:\\Users\\...`, which WSL cannot open;
      it stripped the backslashes and reported `No such file or directory`, i.e. rc 127 presented
      as "the droplet would get invalid shell". Defect class 22 names this exact case, and a
      diagnostic that blames the subject for its own blindness is class 1.

    The script now travels on STDIN as BYTES (classes 21 and 43), so there is no path to translate
    and no newline for the platform to rewrite. CI runs it for real; Windows skips with a reason.
    """
    import subprocess
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_teamwork import shell_harness_allowed
    ok, why = shell_harness_allowed()
    if not ok:
        pytest.skip(why)
    import deploy_web_direct
    os.environ["GHCR_TOKEN"] = "tok_example_value"
    try:
        script = deploy_web_direct.remote_ghcr("abc", proxy=False, image="ghcr.io/o/r/i")
    finally:
        os.environ.pop("GHCR_TOKEN", None)
    payload = script.replace("\r\n", "\n").encode("utf-8")
    r = subprocess.run(["bash", "-n"], input=payload, capture_output=True, timeout=60)
    assert r.returncode == 0, (
        "the droplet would get invalid shell:\n%s" % r.stderr.decode("utf-8", "replace"))


def test_every_step_that_pulls_from_GHCR_is_given_a_token():
    """RUN #10, 2026-10-17. The production job's `Deploy colt-web` step was the only GHCR-pulling
    step in the pipeline without `GHCR_TOKEN`, so the droplet pulled anonymously, met its own
    STALE ghcr.io credential from the retired web-deploy.yml, and docker answered `denied` for an
    image the diagnosis then proved was pullable (`anonymous HTTP 200`).

    The staging job had the token and passed. That is the shape worth guarding: one missing line
    in one job out of five, presenting as a registry fault.

    DERIVE the set of steps that pull (class 35). Hand-listing them is how the fourth one is
    missed, which is exactly what happened.
    """
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(_read(PIPELINE))
    offenders = []
    for job_name, job in (doc.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            run = step.get("run") or ""
            pulls = "--ghcr" in run or "deploy.py" in run
            if not pulls:
                continue
            env = step.get("env") or {}
            if "GHCR_TOKEN" not in env:
                offenders.append("%s :: %s" % (job_name, (step.get("name") or run)[:60]))
    assert not offenders, (
        "these steps pull an image from GHCR but are given no GHCR_TOKEN, so the droplet pulls "
        "anonymously and any stale credential on it turns the pull into `denied`: %s" % offenders)


def test_the_anonymous_path_clears_a_stale_login_first():
    """A STALE CREDENTIAL IS WORSE THAN NO CREDENTIAL. docker sends whatever ~/.docker/config.json
    holds for ghcr.io, so an expired login makes even a PUBLIC image answer `denied` rather than
    falling back to anonymous. The message names the registry; the fault is on the host."""
    import deploy_web_direct
    for k in ("GHCR_TOKEN", "GITHUB_TOKEN"):
        os.environ.pop(k, None)
    script = deploy_web_direct.remote_ghcr("abc", proxy=False, image="ghcr.io/o/r/i")
    assert "docker logout ghcr.io" in script, (
        "the no-token path inherits whatever login the host already has: %s" % script[:500])
    assert script.index("docker logout ghcr.io") < script.index("compose"), (
        "the logout happens after the pull, which is too late to help it")


def test_the_no_token_branch_is_one_shell_script_not_a_python_tuple():
    """Caught in review, not in CI: adding the logout as a second list element made the else-branch
    a TUPLE, and these steps are joined with "\\n", so the droplet would have received the literal
    text `('docker logout ghcr.io...` and `set -e` would have killed the deploy on line one."""
    import deploy_web_direct
    for k in ("GHCR_TOKEN", "GITHUB_TOKEN"):
        os.environ.pop(k, None)
    script = deploy_web_direct.remote_ghcr("abc", proxy=False, image="ghcr.io/o/r/i")
    assert "('" not in script and '", "' not in script, (
        "a Python tuple or list repr reached the generated shell script: %s"
        % [ln for ln in script.splitlines() if "('" in ln or '", "' in ln][:2])
