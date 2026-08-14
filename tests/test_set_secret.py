"""set_secret.py must send the SCRIPT in argv and the VALUE only on stdin.

THE BUG (2026-08-14): `run()` did `subprocess.run(SSH + [host, "bash -s", "--", name],
input=value)`. `bash -s` reads its script from STDIN, so piping the value there made the droplet
execute the API key as a command ("bash: line 1: <key>: command not found") and the real upsert
script was never sent. The secret also reached the droplet's shell. These tests pin the fix:
the value never appears in the remote command string, and the embedded script reads it from stdin.

Stdlib only. Needs `sed`/`bash` for the end-to-end case; skipped cleanly where absent.
"""
import base64
import importlib.util
import os
import re
import shutil
import subprocess
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod():
    spec = importlib.util.spec_from_file_location("set_secret_t", os.path.join(ROOT, "set_secret.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_value_never_appears_in_the_remote_command():
    ss = _mod()
    cmd = ss.remote_command("ABUSEIPDB_KEY")
    for probe in ("02ffdeadbeef", "s3cr3t-value", "hunter2"):
        assert probe not in cmd, "a value could reach argv"
    assert "ABUSEIPDB_KEY" in cmd, "the (non-secret) name must be passed"
    assert "bash -s" not in cmd, ("bash -s reads the script from stdin, which is where the value "
                                  "goes - the exact bug. The script must travel in argv.")


def test_the_embedded_script_reads_the_value_from_stdin():
    ss = _mod()
    cmd = ss.remote_command("ABUSEIPDB_KEY")
    b64 = re.search(r"'([A-Za-z0-9+/=]{40,})'", cmd).group(1)
    script = base64.b64decode(b64).decode()
    assert 'VALUE="$(cat)"' in script, "the script does not read the value from stdin"
    assert "grep -v" in script and "docker compose" in script, "not the real upsert script"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_end_to_end_the_value_lands_in_the_env_file_from_stdin_only():
    """Run the REAL embedded upsert script and confirm the value arrives from stdin and upserts
    idempotently.

    NO WINDOWS PATH IS EVER HANDED TO BASH. The first version wrote a temp .sh file and ran
    `bash C:\\Users\\...\\s.sh`; Git Bash mangled the backslashes ("C:UsersferanAppData...") and
    the test failed on the operator's box while passing in a Linux sandbox - the exact
    'a check that cannot run on the invoking platform is not a check' trap. Fix: the script goes
    to bash INLINE via `bash -c`, the env file is a RELATIVE name written in a cwd set through
    subprocess (which handles the platform path), and the value goes on stdin. Nothing bash sees
    is an absolute native path.
    """
    ss = _mod()
    work = tempfile.mkdtemp(prefix="setsecret-")
    try:
        cmd = ss.remote_command("ABUSEIPDB_KEY")
        b64 = re.search(r"'([A-Za-z0-9+/=]{40,})'", cmd).group(1)
        script = base64.b64decode(b64).decode()
        # emulate the droplet up to the docker restart, and write to a RELATIVE .env in cwd
        script = script.replace(ss.ENVF, "envtest.env").split("cd /opt/colt-stack")[0]
        envf = os.path.join(work, "envtest.env")

        value = "02ffdeadbeefcafe0011223344556677"
        r = subprocess.run(["bash", "-c", script, "bash", "ABUSEIPDB_KEY"],
                           input=value.encode(), cwd=work, capture_output=True, timeout=30)
        assert r.returncode == 0, r.stderr.decode()[:200]
        got = open(envf, encoding="utf-8").read().strip()
        assert got == "ABUSEIPDB_KEY=%s" % value, "the value did not upsert from stdin: %r" % got
        # and idempotent: a second run replaces, never duplicates
        subprocess.run(["bash", "-c", script, "bash", "ABUSEIPDB_KEY"],
                       input=b"newvalue123456789", cwd=work, timeout=30)
        lines = open(envf, encoding="utf-8").read().strip().splitlines()
        assert sum(l.startswith("ABUSEIPDB_KEY=") for l in lines) == 1, "the upsert duplicated"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_run_sends_the_value_on_stdin_and_the_script_in_argv(monkeypatch):
    """The WIRING, not just remote_command in isolation. Reverting run() to `bash -s` with the
    value on stdin is the exact bug, and it must be caught here."""
    ss = _mod()
    monkeypatch.setattr(ss, "upsert_local", lambda n, v: True)   # do not touch the real .env
    seen = {}

    def fake_run(argv, input=None, **kw):
        seen["argv"] = argv
        seen["input"] = input

        class R:
            returncode = 0
        return R()

    monkeypatch.setattr(ss.subprocess, "run", fake_run)
    ss.run("ABUSEIPDB_KEY", "02ffdeadbeefSECRETvalue")

    joined = " ".join(seen["argv"])
    assert "02ffdeadbeefSECRETvalue" not in joined, "the secret reached argv (ps/history visible)"
    assert seen["input"] == b"02ffdeadbeefSECRETvalue", "the value was not sent on stdin"
    assert "bash -s" not in joined, ("bash -s reads its script from stdin - the value's slot - "
                                     "which is the whole bug")
    assert "base64 -d" in joined, "the script is not embedded in argv the safe way"
