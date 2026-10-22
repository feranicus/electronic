"""test_probe_fail_closed.py - a probe that cannot SEE the droplet must never answer about it.

THE INCIDENT, 2026-10-14. A GitHub Actions run had a malformed DROPLET_SSH_KEY. Every ssh failed:

    Load key "/home/runner/.ssh/deploy_key": error in libcrypto
    root@64.225.108.200: Permission denied (publickey,password).

`deploy.run()` folds stderr into stdout when capturing, so that text became `sshout`'s RETURN
VALUE. The old guard was `if rc == 0 or out: return out` - and the error text is non-empty, so it
was handed back as the probe's answer. `ensure_docker()` asked `if "OK" in <that>`, got no, and
concluded Docker was missing from a droplet it had never reached. It then ran

    apt-get install -y docker-ce docker-ce-cli containerd.io ...

against the production box that also hosts Amnezia VPN, VideoDead and six public domains. Only the
install's own ssh failing stopped it. Installing Docker there could restart the daemon and bounce
every container on the host, which is a total outage with no application fault.

Six callers had the same shape (docker, swap, the Grafana port, and two Loki lookups whose answers
become container and network NAMES). The fix is a sentinel inside `sshout`, so all six are fixed at
once (ONE HOME): only a shell that actually ran on the droplet can echo it. A probe is allowed to
answer "no"; it is not allowed to answer when it never ran.

CLAUDE.md defect class 1: "A check that cannot see its subject is not a check. It must not report
its own blindness as a finding about the system."
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# The exact bytes GitHub Actions printed, kept verbatim: the fixture must reproduce the condition
# under test, not an idealised version of it (defect class 12).
SSH_AUTH_FAILURE = ('Load key "/home/runner/.ssh/deploy_key": error in libcrypto\n'
                    'root@64.225.108.200: Permission denied (publickey,password).\n')


def _deploy():
    """deploy.py's module-level definitions, without running main()."""
    src = open(os.path.join(ROOT, "deploy.py"), encoding="utf-8").read()
    src = src.split("def main(")[0]
    ns = {"__name__": "deploymod", "__file__": os.path.join(ROOT, "deploy.py")}
    exec(compile(src, "deploy.py", "exec"), ns)
    return ns


@pytest.fixture(scope="module")
def dep():
    return _deploy()


class _Result:
    def __init__(self, stdout, rc):
        self.stdout, self.returncode = stdout, rc


def _ssh_that_fails(ns, payload=SSH_AUTH_FAILURE, rc=255):
    """Replace deploy.ssh with one that reproduces a dead transport: stderr folded into stdout."""
    calls = []

    def fake(cmd, check=True, capture=False, echo=True, timeout=90, retries=2):
        calls.append(cmd)
        return _Result(payload, rc)
    ns["ssh"] = fake
    ns["time"].sleep = lambda *_a, **_k: None          # no 3s back-off in a unit test
    return calls


def _ssh_that_works(ns, answer):
    """A droplet that really answers. The sentinel is appended by sshout, so echo it back."""
    calls = []

    def fake(cmd, check=True, capture=False, echo=True, timeout=90, retries=2):
        calls.append(cmd)
        return _Result(answer + "\n" + ns["_PROBE_MARK"] + "\n", 0)
    ns["ssh"] = fake
    return calls


# ---------------------------------------------------------------- the probe itself
def test_a_dead_transport_never_becomes_an_answer(dep):
    _ssh_that_fails(dep)
    with pytest.raises(SystemExit) as e:
        dep["sshout"]("command -v docker >/dev/null 2>&1 && echo OK || echo MISSING")
    msg = str(e.value)
    assert "could not RUN" in msg, "the exit must say the probe never ran, not that it answered no"
    assert "Nothing was" in msg and "nothing was concluded" in msg


def test_the_failure_names_an_auth_problem_as_an_auth_problem(dep):
    """A diagnostic that does not NAME its subject sends the next investigation down the wrong road
    (defect class 26). 'error in libcrypto' is a malformed KEY, not a sick droplet."""
    _ssh_that_fails(dep)
    with pytest.raises(SystemExit) as e:
        dep["sshout"]("echo hello")
    msg = str(e.value)
    assert "AUTHENTICATION failure" in msg
    assert "DROPLET_SSH_KEY" in msg and "trailing newline" in msg
    assert "libcrypto" in msg, "quote what the transport actually said"


def test_a_real_answer_still_comes_back_clean(dep):
    calls = _ssh_that_works(dep, "OK")
    assert dep["sshout"]("command -v docker ... && echo OK || echo MISSING") == "OK"
    assert dep["_PROBE_MARK"] in calls[0], "the sentinel must be appended to the remote command"
    assert "; echo" in calls[0], (
        "the sentinel must be joined with ';' not '&&' - a probe is allowed to answer 'no'")


def test_a_legitimate_negative_answer_is_still_a_negative_answer(dep):
    """Fail-closed must not become fail-always: a droplet that really says MISSING must say so."""
    _ssh_that_works(dep, "MISSING")
    assert dep["sshout"]("command -v docker ...") == "MISSING"


def test_a_probe_that_exits_non_zero_but_RAN_is_trusted(dep):
    """grep finding nothing exits 1. That is an answer, not a transport failure."""
    def fake(cmd, check=True, capture=False, echo=True, timeout=90, retries=2):
        return _Result("\n" + dep["_PROBE_MARK"] + "\n", 1)
    dep["ssh"] = fake
    assert dep["sshout"]("docker ps | grep -i loki") == ""


# ---------------------------------------------------------------- the callers that act on it
def test_an_unreachable_droplet_can_never_trigger_an_apt_install(dep):
    """THE WHOLE POINT. ensure_docker() ran `apt-get install docker-ce` against production because
    a transport failure read as 'docker is missing'. Installing Docker on that box restarts the
    daemon and bounces Amnezia VPN, VideoDead and six domains."""
    calls = _ssh_that_fails(dep)
    with pytest.raises(SystemExit):
        dep["ensure_docker"]()
    joined = " ".join(calls)
    assert "apt-get install" not in joined, (
        "an unreachable droplet triggered a package install: %s" % joined[:300])
    assert "docker-ce" not in joined


def test_an_unreachable_droplet_can_never_trigger_a_swapfile(dep):
    calls = _ssh_that_fails(dep)
    with pytest.raises(SystemExit):
        dep["ensure_swap"]()
    joined = " ".join(calls)
    assert "fallocate" not in joined and "mkswap" not in joined and "swapon /" not in joined, (
        "an unreachable droplet started writing a swapfile: %s" % joined[:300])


def test_a_real_droplet_with_docker_is_left_alone(dep):
    calls = _ssh_that_works(dep, "OK")
    dep["_INV"] = ""
    dep["ensure_docker"]()
    assert "apt-get install" not in " ".join(calls), "docker was present and got installed anyway"


def test_every_sshout_caller_is_covered_by_the_sentinel(dep):
    """Behaviour AND wiring (defect class 9). A seventh caller added later must inherit the fix,
    so assert there is exactly ONE sshout and that it is the thing that appends the sentinel."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "deploy.py"), encoding="utf-8").read())
    defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sshout"]
    assert len(defs) == 1, "sshout has %d definitions; the guard has more than one home" % len(defs)
    assert "_PROBE_MARK" in ast.unparse(defs[0]), "sshout no longer proves the probe ran"
    callers = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Name) and n.func.id == "sshout"]
    assert len(callers) >= 5, "expected the known read-only probes, found %d" % len(callers)


# ---------------------------------------------------------------------------------------------
# THE SAME DOCTRINE, ONE LAYER UP: recover.ssh_script returns (stdout, stderr, rc), and a caller
# that uses the result without unpacking it is either crashing or - worse - reading a tuple's
# truthiness as "the droplet answered".
#
# 2026-10-22: decommission.py did `sections(ssh_script(...))` at all three call sites and died
# with `'tuple' object has no attribute 'splitlines'` the first time it was ever run end to end.
# The crash is the harmless half. The half that matters is that nothing read the RETURN CODE, so
# a refused ssh would have produced empty output, an empty section map, and a plan announcing
# "none of the target sites is served by a caddyguard fragment" - a statement about the proxy,
# made by a probe that never reached it.
#
# Defect class 36 lists `ssh_script() -> 3-tuple` by name. This asserts it instead of repeating it.
# ship.py defines its OWN ssh_script that returns a string, which is why reading the name is not
# enough: the module decides the shape, so the check is scoped per module to the recover import.

def _modules_importing_recover_ssh_script():
    import ast
    import subprocess
    out = subprocess.run(["git", "ls-files", "-z", "*.py"], cwd=ROOT,
                         capture_output=True, timeout=120)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    found = []
    for rel in [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]:
        try:
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        if any(isinstance(n, ast.ImportFrom) and (n.module or "").endswith("recover")
               and any(a.name == "ssh_script" for a in n.names) for n in ast.walk(tree)):
            found.append((rel, tree))
    assert found, "no module imports recover.ssh_script - this guard would measure nothing"
    return found


def test_nobody_uses_recover_ssh_scripts_tuple_without_unpacking_it():
    import ast
    offenders = []
    for rel, tree in _modules_importing_recover_ssh_script():
        unpacked = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
                    and getattr(node.value.func, "id", None) == "ssh_script" \
                    and any(isinstance(t, ast.Tuple) and len(t.elts) == 3 for t in node.targets):
                unpacked.add(node.value.lineno)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "ssh_script" \
                    and node.lineno not in unpacked:
                offenders.append("%s:%d" % (rel, node.lineno))
    assert not offenders, (
        "recover.ssh_script returns (stdout, stderr, rc); these call sites use it whole, so "
        "either they crash or they never read the return code:\n  " + "\n  ".join(offenders))
