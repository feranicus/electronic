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
import sys
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
    cmd = ss.remote_command("ABUSEIPDB_KEY", {"ABUSEIPDB_KEY"})
    for probe in ("02ffdeadbeef", "s3cr3t-value", "hunter2"):
        assert probe not in cmd, "a value could reach argv"
    assert "ABUSEIPDB_KEY" in cmd, "the (non-secret) name must be passed"
    assert "bash -s" not in cmd, ("bash -s reads the script from stdin, which is where the value "
                                  "goes - the exact bug. The script must travel in argv.")


def test_the_embedded_script_reads_the_value_from_stdin():
    ss = _mod()
    cmd = ss.remote_command("ABUSEIPDB_KEY", {"ABUSEIPDB_KEY"})
    b64 = re.search(r"'([A-Za-z0-9+/=]{40,})'", cmd).group(1)
    script = base64.b64decode(b64).decode()
    assert 'VALUE="$(cat)"' in script, "the script does not read the value from stdin"
    assert "grep -v" in script and "docker compose" in script, "not the real upsert script"


def test_the_value_is_read_before_set_e_can_abort():
    """ORDER MATTERS AND IT CHANGED. `VALUE="$(cat)"` must run before `set -e`, because stdin is
    the ONE thing the caller cannot resend: an abort after the pipe is drained loses the secret and
    the operator is asked to paste it again for a run that already consumed it."""
    ss = _mod()
    body = ss.REMOTE
    assert body.index('VALUE="$(cat)"') < body.index("\nset -e"), (
        "set -e precedes the stdin read; a failure before it discards the value")


@pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None,
                    reason="the remote upsert is a POSIX shell script that runs ONLY on the Linux "
                           "droplet - never on Windows. Executing it under Git Bash tests the "
                           "harness, not the code. The Windows-critical behaviour (value on stdin, "
                           "script in argv) is covered by the pure-Python tests above, which run "
                           "everywhere. This end-to-end runs in Linux CI, where the script is real.")
def test_end_to_end_the_value_lands_in_the_env_file_from_stdin_only():
    """On a REAL POSIX bash: run the embedded upsert script and confirm the value arrives from
    stdin and upserts idempotently. Skipped on Windows on purpose - see the skip reason."""
    ss = _mod()
    work = tempfile.mkdtemp(prefix="setsecret-")
    try:
        cmd = ss.remote_command("ABUSEIPDB_KEY", {"ABUSEIPDB_KEY"})
        b64 = re.search(r"'([A-Za-z0-9+/=]{40,})'", cmd).group(1)
        script = base64.b64decode(b64).decode()
        sf = os.path.join(work, "s.sh")
        with open(sf, "w", newline="\n") as fh:
            fh.write(script)
        # The script no longer hardcodes /opt/colt-stack - it derives the stack root from the
        # primary env path it is given, which is what makes this runnable off the droplet at all
        # (class 20: simulate the platform rather than skipping it). `docker` is stubbed to a
        # no-op: this test is about the UPSERT, and test_secret_homes.py exercises the container
        # half against a docker that records what it was asked.
        envf = os.path.join(work, "assess-bot", ".env")
        os.makedirs(os.path.dirname(envf))
        binq = os.path.join(work, "bin")
        os.makedirs(binq)
        with open(os.path.join(binq, "docker"), "w", newline="\n") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(binq, "docker"), 0o755)
        env = dict(os.environ, PATH=binq + os.pathsep + os.environ["PATH"])
        fp = base64.b64encode(ss.FINGERPRINT.encode()).decode()
        args = ["bash", sf, "ABUSEIPDB_KEY", "ABUSEIPDB_KEY", envf, fp]
        value = "02ffdeadbeefcafe0011223344556677"
        r = subprocess.run(args, input=value.encode(), capture_output=True, timeout=60, env=env)
        assert r.returncode == 0, r.stderr.decode()[:300] + r.stdout.decode()[:300]
        got = open(envf, encoding="utf-8").read().strip()
        assert got == "ABUSEIPDB_KEY=%s" % value, "the value did not upsert from stdin: %r" % got
        subprocess.run(args, input=b"newvalue123456789", timeout=60, env=env,
                       capture_output=True)
        lines = open(envf, encoding="utf-8").read().strip().splitlines()
        assert sum(l.startswith("ABUSEIPDB_KEY=") for l in lines) == 1, "the upsert duplicated"
        assert "newvalue123456789" in open(envf, encoding="utf-8").read()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_run_sends_the_value_on_stdin_and_the_script_in_argv(monkeypatch):
    """The WIRING, not just remote_command in isolation. Reverting run() to `bash -s` with the
    value on stdin is the exact bug, and it must be caught here."""
    ss = _mod()
    monkeypatch.setattr(ss, "upsert_local", lambda n, v, fam: True)  # do not touch the real .env
    monkeypatch.setattr(ss, "key_homes", lambda family=None: [])     # nor read it
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
