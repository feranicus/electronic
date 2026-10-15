"""test_ci_key.py - a credential nobody can read back must be PROVEN before it is written.

THE INCIDENT, 2026-10-14. Every GitHub Actions deploy this repo had ever attempted died at the
first ssh:

    Load key "/home/runner/.ssh/deploy_key": error in libcrypto
    root@64.225.108.200: Permission denied (publickey,password).

The workflows write the secret correctly (`printf '%s\\n'`), so the SECRET'S CONTENT was never a
usable key. It was uploaded by setup_github_cicd.py, which read a file and handed it to
`gh secret set` without ever parsing it, let alone authenticating with it. A GitHub secret cannot
be read back by anybody, so the write was unverifiable in BOTH directions and the credential rotted
silently for weeks while the workflow kept reporting a droplet problem.

The property under test is one sentence: `push()` uploads ONLY a key that shape-checked, that
OpenSSH itself parsed, and that the droplet accepted - and an UNKNOWN at any step is not a pass
(defect class 1: a check that cannot see its subject must not answer about it).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ci_key                                                        # noqa: E402

# A real passphrase-less ed25519 key's SHAPE. The body is deliberately not a valid key: these tests
# are about the text checks, and the ones that need a real key use ssh-keygen to make one.
GOOD = ("-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtz\n"
        "c2gtZWQyNTUxOQAAACBQ0ZQ3Yw1b2mQ4h5Zr8KkqS7bJ5n0wX1yYc2dEf3gHiA\n"
        "AAAJiZvXHfmb1x3wAAAAtzc2gtZWQyNTUxOQAAACBQ0ZQ3Yw1b2mQ4h5Zr8Kkq\n"
        "-----END OPENSSH PRIVATE KEY-----\n")

# EVERY fixture that puts key material on disk writes THESE BYTES, in binary. Discovered the hard
# way on the operator's box, 2026-10-15: `Path.write_text(GOOD, encoding="utf-8")` goes through a
# TextIOWrapper with newline=None, so on Windows it wrote the file with CRLF, read_key_bytes
# faithfully returned CRLF, and the test failed while the CODE was correct. Defect class 21 is not
# only about the product; a fixture that will be hashed, diffed or parsed is written in BINARY.
GOOD_BYTES = GOOD.encode("utf-8")


# ---------------------------------------------------------------- shape: turn libcrypto into words
def test_a_good_key_passes_the_shape_check():
    """Prove the fixture first (defect class 12): if GOOD does not pass, every negative below is
    measuring the fixture rather than the guard."""
    ok, why = ci_key.key_shape(GOOD)
    assert ok, why


@pytest.mark.parametrize("text,needle", [
    (GOOD.rstrip("\n"), "TRAILING NEWLINE"),
    (GOOD.replace("\n", ""), "ONE line"),
    (GOOD.split("-----END")[0], "END line is MISSING"),
    ("PuTTY-User-Key-File-3: ssh-ed25519\nEncryption: none\n", "PuTTY"),
    ("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI gh-actions-deploy\n", "PUBLIC half"),
    ("-----BEGIN RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\nDEK-Info: AES-128-CBC,1\n"
     "abc\n-----END RSA PRIVATE KEY-----\n", "PASSPHRASE"),
    ("", "EMPTY"),
    ("   \n\n", "EMPTY"),
    (None, "could not be read"),
    ("hello world, this is not a key at all\nsecond line\nthird\nfourth\n", "no BEGIN line"),
])
def test_every_way_a_secret_goes_wrong_is_named_not_shrugged_at(text, needle):
    """Defect class 26: a diagnostic that does not NAME its subject sends the next investigation
    down the wrong road. 'error in libcrypto' sent this one at the droplet for weeks."""
    ok, why = ci_key.key_shape(text)
    assert not ok, "accepted a broken key: %r" % (text[:40] if text else text)
    assert needle in why, "the cause was not named. got: %s" % why


def test_the_shape_check_never_echoes_the_key_body():
    """A diagnostic that prints the thing it is diagnosing puts a private key in a CI log."""
    body = GOOD.splitlines()[1]
    for text in (GOOD.rstrip("\n"), GOOD.replace("\n", ""), GOOD.split("-----END")[0]):
        _, why = ci_key.key_shape(text)
        assert body not in why, "the failure message leaked key material"
        assert body[:20] not in why


# ---------------------------------------------------------------- the gate in front of the upload
class _Spy:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, stdin_text):
        self.calls.append((cmd, stdin_text))
        return 0, "ok"


@pytest.fixture
def keyfile(tmp_path):
    p = tmp_path / "colt_deploy"
    p.write_bytes(GOOD_BYTES)          # BINARY: write_text translates on Windows
    return str(p)


def test_push_sends_the_value_on_stdin_never_in_argv(keyfile):
    """The set_secret.py rule, applied here: argv is visible in the process table and in shell
    history; a secret belongs on stdin."""
    spy = _Spy()
    ok, detail = ci_key.push(keyfile, repo="feranicus/electronic", runner=spy)
    assert ok, detail
    (cmd, stdin_text), = spy.calls
    # REWRITTEN 2026-10-15 (defect class 17), old reasoning kept: this asserted `== GOOD`, a str,
    # which is exactly the shape that let subprocess text mode rewrite "\n" as "\r\n" on Windows
    # and upload an unreadable key. The payload is now BYTES, and the test says so.
    assert stdin_text == GOOD.encode("utf-8"), "the key did not travel on stdin, as bytes"
    joined = " ".join(cmd)
    assert "BEGIN OPENSSH" not in joined, "the key appeared in argv: %s" % joined
    assert cmd[:4] == ["gh", "secret", "set", "DROPLET_SSH_KEY"]


def test_an_unknown_auth_result_is_not_a_pass(monkeypatch, keyfile):
    """THE WHOLE POINT. The old script uploaded whatever it read. A timed-out probe tells us
    nothing about the key, and nothing is not permission to overwrite a credential."""
    monkeypatch.setattr(ci_key, "parses", lambda p: (True, "SHA256:fake"))
    monkeypatch.setattr(ci_key, "authenticates", lambda *a, **k: (None, "timed out"))
    assert ci_key.check(keyfile) is False, "an UNKNOWN was scored as a usable key"


def test_a_key_the_droplet_rejects_is_not_a_pass(monkeypatch, keyfile):
    monkeypatch.setattr(ci_key, "parses", lambda p: (True, "SHA256:fake"))
    monkeypatch.setattr(ci_key, "authenticates",
                        lambda *a, **k: (False, "not in authorized_keys"))
    assert ci_key.check(keyfile) is False


def test_a_key_openssh_cannot_parse_never_reaches_the_droplet_probe(monkeypatch, keyfile):
    """Order matters: ssh-ing with a garbage key just produces another libcrypto line."""
    probed = []
    monkeypatch.setattr(ci_key, "parses", lambda p: (False, "error in libcrypto"))
    monkeypatch.setattr(ci_key, "authenticates",
                        lambda *a, **k: (probed.append(1), (True, "x"))[1])
    assert ci_key.check(keyfile) is False
    assert not probed, "it tried to authenticate with a key OpenSSH had already rejected"


def test_a_fully_proven_key_passes(monkeypatch, keyfile):
    """A gate that cannot pass is not a gate (defect class 3 inverted)."""
    monkeypatch.setattr(ci_key, "parses", lambda p: (True, "SHA256:fake"))
    monkeypatch.setattr(ci_key, "authenticates", lambda *a, **k: (True, "authenticated"))
    assert ci_key.check(keyfile) is True


def test_parses_uses_openssh_itself_and_discards_its_output(tmp_path):
    """Same binary as the runner, same verdict. Uses a REAL generated key, so this is the one test
    that proves the shape checks and the parse check agree."""
    import shutil
    import subprocess
    if not shutil.which("ssh-keygen"):
        pytest.skip("ssh-keygen not on PATH")
    p = tmp_path / "real"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(p), "-N", "", "-q"], check=True)
    ok, fp = ci_key.parses(str(p))
    assert ok is True, fp
    assert "SHA256:" in fp, "the fingerprint was not reported: %s" % fp
    assert "PRIVATE KEY" not in fp, "parse() leaked key material into its own answer"
    ok_shape, why = ci_key.key_shape(p.read_text(encoding="utf-8"))
    assert ok_shape, "a key ssh-keygen accepts was rejected by the shape check: %s" % why
    # And the public half must FAIL the shape check, since that is a real paste mistake.
    ok_pub, why_pub = ci_key.key_shape((tmp_path / "real.pub").read_text(encoding="utf-8"))
    assert not ok_pub and "PUBLIC half" in why_pub


# ------------------------------------------- THE REAL ROOT CAUSE: a passphrase-protected CI key
# This is the defect the first version of this file shipped WITHOUT, and it is the one that broke
# every CI deploy. `~/.ssh/colt_deploy` on the operator's PC is a perfectly good OpenSSH key with a
# passphrase. A GitHub runner has no keyboard, so it can never unlock it: "error in libcrypto".
# The header check could not see it, because a modern OpenSSH key says NOTHING about encryption in
# its armour - no "ENCRYPTED", no "Proc-Type: 4,ENCRYPTED". Those are PEM-era tells. The cipher name
# lives in the clear inside the base64, and reading it is the only way to answer the question
# without asking a human for the passphrase.
_SSHKEYGEN = __import__("shutil").which("ssh-keygen")
_needs_keygen = pytest.mark.skipif(not _SSHKEYGEN, reason="ssh-keygen not on PATH")


@pytest.fixture(scope="module")
def real_keys(tmp_path_factory):
    """One key with a passphrase and one without, both made by ssh-keygen itself. Prove the fixture
    (defect class 12): if these two files do not actually differ in encryption, every assertion
    below is measuring nothing."""
    import subprocess
    if not _SSHKEYGEN:
        pytest.skip("ssh-keygen not on PATH")
    d = tmp_path_factory.mktemp("keys")
    plain, enc = d / "plain", d / "enc"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(plain), "-N", "", "-q"], check=True)
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(enc), "-N", "correct horse", "-q"],
                   check=True)
    pt = plain.read_text(encoding="utf-8")
    et = enc.read_text(encoding="utf-8")
    assert "ENCRYPTED" not in et and "Proc-Type" not in et, (
        "FIXTURE INVALID: this OpenSSH build announces encryption in the armour, so the incident "
        "this test encodes could not have happened the way it did")
    assert pt != et
    return {"plain": str(plain), "enc": str(enc), "plain_text": pt, "enc_text": et}


@_needs_keygen
def test_the_cipher_is_read_from_the_body_not_the_header(real_keys):
    assert ci_key.openssh_cipher(real_keys["plain_text"]) == "none"
    assert ci_key.openssh_cipher(real_keys["enc_text"]) not in (None, "none"), (
        "a passphrase-protected key reported no cipher - it would pass straight to GitHub")


@_needs_keygen
def test_a_passphrase_protected_key_is_refused_and_the_reason_is_the_passphrase(real_keys):
    """THE WHOLE POINT. The operator supplied the CORRECT passphrase and was still told the key was
    unusable; the message must say why that is right, not imply his key is corrupt."""
    ok, why = ci_key.key_shape(real_keys["enc_text"])
    assert not ok, "a passphrase-protected key passed the shape check"
    assert "PASSPHRASE" in why.upper()
    assert "libcrypto" in why, "the message must connect to the error he has actually been seeing"
    ok2, why2 = ci_key.key_shape(real_keys["plain_text"])
    assert ok2, "a passphrase-less key was refused: %s" % why2


@_needs_keygen
def test_no_check_ever_prompts_the_operator(real_keys, monkeypatch):
    """A check that stops and interrogates the human has stopped measuring. The first version ran
    `ssh-keygen -y -f <key>` with an inherited stdin, so it ASKED HIM to type the passphrase and
    then reported his correct passphrase as incorrect.

    Proved by making any read of this process's stdin fail: `parses` must answer anyway.
    """
    import subprocess as sp
    real = sp.run
    seen = {}

    def guard(cmd, *a, **k):
        if isinstance(cmd, (list, tuple)) and cmd and "ssh-keygen" in str(cmd[0]):
            seen["stdin"] = k.get("stdin")
            assert k.get("stdin") is sp.DEVNULL, (
                "ssh-keygen was run with an inheritable stdin (%r): it can prompt" % k.get("stdin"))
            # `-y` is the only verb that DECRYPTS, so it is the only one that can prompt.
            # `-l` reads the public blob and never asks for anything.
            if "-y" in cmd:
                assert "-P" in cmd, (
                    "ssh-keygen -y was run without -P, so it falls back to prompting")
        return real(cmd, *a, **k)

    monkeypatch.setattr(ci_key.subprocess, "run", guard)
    ok, detail = ci_key.parses(real_keys["enc"])
    assert seen.get("stdin") is sp.DEVNULL
    assert ok is False, "an unusable-by-CI key was reported as parseable"
    assert "passphrase" in detail.lower()
    assert "correct" in detail.lower(), (
        "the operator typed the right passphrase; the message must not imply otherwise")
    ok2, fp = ci_key.parses(real_keys["plain"])
    assert ok2 is True and "SHA256:" in fp


@_needs_keygen
def test_mint_makes_a_passphrase_less_key_and_never_overwrites_one(tmp_path):
    p = str(tmp_path / "colt_ci")
    ok, detail = ci_key.mint(p)
    assert ok, detail
    text = open(p, encoding="utf-8").read()
    assert ci_key.openssh_cipher(text) == "none", "minted a key a runner cannot use"
    ok_shape, why = ci_key.key_shape(text)
    assert ok_shape, why
    before = text
    ok2, detail2 = ci_key.mint(p)
    assert ok2 and "already exists" in detail2
    assert open(p, encoding="utf-8").read() == before, (
        "mint overwrote an existing key, orphaning whatever is in authorized_keys")


@_needs_keygen
def test_provisioning_never_reads_or_writes_the_operators_own_key(tmp_path, monkeypatch):
    """His personal key is not ours to strip, copy or move. A dedicated key can also be revoked on
    its own by deleting one line from authorized_keys."""
    his = tmp_path / "id_ed25519"
    import subprocess
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(his), "-N", "his pass", "-q"],
                   check=True)
    before = his.read_bytes()
    opened = []
    real_open = open

    def spy(f, *a, **k):
        opened.append(str(f))
        return real_open(f, *a, **k)

    monkeypatch.setattr(ci_key, "CANDIDATES", [str(his)])
    monkeypatch.setitem(__builtins__ if isinstance(__builtins__, dict)
                        else __builtins__.__dict__, "open", spy)
    ci_key.mint(str(tmp_path / "colt_ci"))
    monkeypatch.undo()
    assert his.read_bytes() == before, "the operator's own key was modified"
    assert not [o for o in opened if o == str(his)], "the operator's own key was read: %s" % opened


def test_authorize_sends_only_the_public_half(tmp_path, monkeypatch):
    priv = tmp_path / "colt_ci"
    priv.write_bytes(GOOD_BYTES)
    (tmp_path / "colt_ci.pub").write_bytes(b"ssh-ed25519 AAAAC3Nza-TEST ci@x\n")
    sent = {}

    class _R:
        stdout, stderr, returncode = "__authorized__\n", "", 0

    def fake_run(cmd, *a, **k):
        sent["cmd"] = " ".join(cmd)
        return _R()

    monkeypatch.setattr(ci_key.subprocess, "run", fake_run)
    ok, detail = ci_key.authorize(str(priv))
    assert ok, detail
    assert "AAAAC3Nza-TEST" in sent["cmd"]
    assert "BEGIN OPENSSH" not in sent["cmd"], "the PRIVATE key was sent to the droplet"
    # Assert the PROPERTY, not the presence of a string the VERIFICATION grep also contains
    # (defect class 4): the append itself must be the right-hand side of a `grep ... ||`. The first
    # version of this line passed against an unconditional append, because the trailing
    # "grep -qxF ... && echo __authorized__" kept the needle in the command.
    assert "~/.ssh/authorized_keys || printf" in sent["cmd"], (
        "the append is not guarded by the grep, so a re-run duplicates the line:\n  %s"
        % sent["cmd"])


def test_authorize_believes_the_droplet_not_itself(tmp_path, monkeypatch):
    """The success token is the DROPLET's answer. Without it nothing was proven, so authorize must
    refuse - otherwise a dead ssh becomes 'authorized' and the deploy proceeds on a key the box has
    never heard of (defect class 1, the same shape as the sshout incident)."""
    priv = tmp_path / "colt_ci"
    priv.write_bytes(GOOD_BYTES)
    (tmp_path / "colt_ci.pub").write_bytes(b"ssh-ed25519 AAAAC3Nza-TEST ci@x\n")

    class _Dead:
        stdout = ""
        stderr = "root@64.225.108.200: Permission denied (publickey,password).\n"
        returncode = 255

    monkeypatch.setattr(ci_key.subprocess, "run", lambda *a, **k: _Dead())
    ok, detail = ci_key.authorize(str(priv))
    assert ok is False, "a failed ssh was reported as a successful authorization"
    assert "Permission denied" in detail, "the cause was not quoted: %s" % detail


def test_authorizing_twice_really_leaves_one_line(tmp_path, monkeypatch):
    """The structural check above says the shape is right; this RUNS the remote script against a
    throwaway HOME and counts the lines, because PARSE is not RUN (defect class 48).

    WINDOWS SKIPS, and the gate is teamlock's existing `shell_harness_allowed()` rather than a
    second copy of the same decision (ONE HOME, defect class 32). The first version of this test
    used a bare `shutil.which("bash")` and failed on the operator's box: `bash` there is WSL's
    bash.exe, and the stripped env I handed it made WSL itself fail with an RPC error in UTF-16.
    That is defect class 19 twice over - green in a Linux sandbox said nothing about his machine,
    and the failure named my harness instead of the code. This script only ever executes on the
    Ubuntu droplet over ssh, so Git Bash/WSL would test the emulation either way; CI and the
    droplet keep the real coverage. TEAMLOCK_TEST_SHELL=1 forces it.
    """
    import subprocess
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_teamwork import shell_harness_allowed
    ok_shell, why = shell_harness_allowed()
    if not ok_shell:
        pytest.skip(why)
    priv = tmp_path / "colt_ci"
    priv.write_bytes(GOOD_BYTES)
    (tmp_path / "colt_ci.pub").write_bytes(b"ssh-ed25519 AAAAC3Nza-TEST ci@x\n")
    home = tmp_path / "home"
    home.mkdir()
    scripts = []

    class _R:
        stdout, stderr, returncode = "__authorized__\n", "", 0

    def capture(cmd, *a, **k):
        scripts.append(cmd[-1])
        return _R()

    monkeypatch.setattr(ci_key.subprocess, "run", capture)
    ci_key.authorize(str(priv))
    monkeypatch.undo()
    script, = scripts
    for _ in range(3):
        env = dict(os.environ, HOME=str(home))
        r = subprocess.run(["bash", "-c", script], env=env,
                           capture_output=True, text=True, timeout=60)
        assert "__authorized__" in r.stdout, r.stderr
    lines = (home / ".ssh" / "authorized_keys").read_text().splitlines()
    assert lines.count("ssh-ed25519 AAAAC3Nza-TEST ci@x") == 1, (
        "three runs left %d copies of the key: %r" % (len(lines), lines))

    # AND IT MUST BE ABLE TO FAIL (defect class 3). Make the append impossible and assert the
    # script does NOT say __authorized__: a success token printed without checking the file is a
    # fail-open, and the next thing to happen would be a deploy with an unusable secret.
    broken = tmp_path / "broken"
    (broken / ".ssh" / "authorized_keys").mkdir(parents=True)   # cannot be appended to
    r = subprocess.run(["bash", "-c", script], env=dict(os.environ, HOME=str(broken)),
                       capture_output=True, text=True, timeout=60)
    assert "__authorized__" not in r.stdout, (
        "the script reported success while the key was NOT in authorized_keys")


# --------------------- THE ROOT CAUSE: subprocess text mode rewrote the key on the way to GitHub
# 2026-10-15. A proven, passphrase-less key was uploaded and the runner still said
# "(no fingerprint: not a key)". The file on disk was correct every single time. The UPLOAD was not.
#
# `subprocess.run(..., input=<str>, text=True)` wraps stdin in io.TextIOWrapper with newline=None,
# and TextIOWrapper on WRITE translates "\n" into os.linesep. On the operator's Windows box
# os.linesep is "\r\n". So `gh secret set` received the key with CRLF line endings, and OpenSSH
# rejects a CR inside the base64 body with exactly "error in libcrypto".
#
# MEASURED, not reasoned: a real ed25519 key parses with LF; the same bytes with every "\n"
# replaced by "\r\n" give rc=255 and that message. test_crlf_really_is_what_breaks_a_key proves it
# here, so this test file does not rest on my description of OpenSSH's behaviour.
#
# setup_github_cicd.py had the identical shape (`inp=open(priv).read()`), which is why the secret
# has never worked since the day it was created - and why the passphrase, though a genuine second
# defect, was not the thing still breaking it.
#
# Defect class 21: "Line endings are the platform's business."
# Defect class 20: SIMULATE the platform, do not skip it. These run on Linux and on Windows.

@_needs_keygen
def test_crlf_really_is_what_breaks_a_key(real_keys, tmp_path):
    """PROVE THE FIXTURE (defect class 12). If CRLF did not actually break a key, every assertion
    below would be enforcing a rule with no incident behind it."""
    import subprocess

    def keygen_y(path):
        return subprocess.run(["ssh-keygen", "-y", "-f", str(path), "-P", ""],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)

    # LET SSH-KEYGEN CREATE THE FILE, then rewrite only its CONTENT.
    #
    # The first version of this test wrote the bytes itself and called os.chmod(0o600). On the
    # operator's Windows box that produces an ACL OpenSSH considers world-readable, so ssh-keygen
    # refused on "Bad permissions" and never looked at the key at all - the test was measuring
    # Windows ACL inheritance while claiming to measure CRLF (defect class 12: a fixture that does
    # not reproduce the condition under test is a test of the fixture; defect class 13: a negative
    # that passes because of ANOTHER guard measures that other guard).
    #
    # ssh-keygen sets a correct private ACL when it creates a key, on every platform. Overwriting
    # the bytes in place does not change the ACL, so the only variable left between the control
    # and the experiment is the line endings.
    subject = tmp_path / "subject"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(subject), "-N", "", "-q"], check=True)
    lf = subject.read_bytes()
    assert b"\r\n" not in lf, "the generated key already had CRLF; the premise is wrong"

    control = keygen_y(subject)
    assert control.returncode == 0, (
        "CONTROL FAILED: ssh-keygen rejected the key before any CRLF was introduced, so this "
        "machine cannot run the experiment. It said: %r" % ((control.stderr or "")[:200],))

    subject.write_bytes(lf.replace(b"\n", b"\r\n"))          # same file, same ACL, CRLF content
    r = keygen_y(subject)
    said = r.stderr + r.stdout

    # THE SUBJECT OF THIS EXPERIMENT IS THE RUNNER'S OpenSSH, AND THE RUNNER IS LINUX.
    #
    # Measured 2026-10-15, both ways, on the same bytes:
    #   Linux OpenSSH : CRLF key -> rc=255, "error in libcrypto"   <- what the runner does
    #   Win32 OpenSSH : CRLF key -> rc=0, prints the public key    <- what the operator's box does
    #
    # So this cannot be proven on Windows, and that tolerance is itself part of the story: it is
    # why a CRLF-mangled key looked perfectly healthy every time it was checked locally and died
    # only on the runner. Defect class 19 inverted - green on his box was never evidence about the
    # Linux machine that actually had to read the key.
    #
    # The gate DETECTS the behaviour rather than branching on sys.platform (defect class 20): if
    # the local OpenSSH tolerates CRLF it is not the implementation under test, so a result here
    # would mean nothing. CI (ubuntu-latest) and the droplet keep the real coverage.
    if r.returncode == 0:
        pytest.skip("this OpenSSH tolerates CRLF in a private key (Win32 does; the GitHub runner's "
                    "Linux OpenSSH does not), so the experiment cannot be run here - and that very "
                    "tolerance is why the mangled key looked fine on this machine")

    assert "permission" not in said.lower(), (
        "the refusal is about file permissions, not the key bytes: %r" % said[:200])
    assert "libcrypto" in said, (
        "CRLF broke the key but not with the message the operator saw: %r" % said[:200])


def test_the_shape_check_catches_crlf_even_where_the_local_openssh_does_not():
    """The local ssh-keygen is NOT a proxy for the runner's. Win32 OpenSSH parses a CRLF key
    happily (measured), so `parses()` on the operator's box cannot see this defect - which is
    exactly how a mangled key passed every local check for weeks. key_shape carries the RUNNER's
    rule instead, so it fails identically on Windows, Linux and CI."""
    crlf = GOOD.replace("\n", "\r\n")
    ok, why = ci_key.key_shape(crlf)
    assert not ok, "a CRLF key passed the shape check; the runner will reject it"
    assert "CARRIAGE RETURN" in why.upper()
    assert "libcrypto" in why, "the message must connect to what the runner will actually say"
    # a lone CR anywhere is enough - this is not a 'does it end with CRLF' check
    assert not ci_key.key_shape(GOOD.replace("KEY-----\n", "KEY-----\r\n", 1))[0]
    # and the clean key must still pass, or the check is just always-fail
    assert ci_key.key_shape(GOOD)[0]


def test_no_fixture_in_this_file_writes_key_material_as_text():
    """The guard on the guards. My own fixtures used Path.write_text and put CRLF on disk on
    Windows, which made a correct implementation look broken and cost a ship. A file this suite
    will hand to ssh-keygen or compare byte-for-byte is written in BINARY, always - so assert it,
    rather than trusting that I will remember (defect class 21, applied to the tests themselves)."""
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "write_text":
                bad.append("line %d: %s" % (node.lineno, ast.unparse(node)[:80]))
            # tempfile.NamedTemporaryFile("w", ...) / open(..., "w") for key bytes
            if node.func.attr == "NamedTemporaryFile" and node.args:
                mode = node.args[0]
                if isinstance(mode, ast.Constant) and "b" not in str(mode.value):
                    bad.append("line %d: NamedTemporaryFile(%r)" % (node.lineno, mode.value))
    assert not bad, "key material written through a newline-translating layer:\n  " + "\n  ".join(bad)


def test_the_upload_sends_raw_bytes_so_no_layer_can_rewrite_them(tmp_path):
    """The property, stated once: what reaches gh is byte-identical to the file."""
    p = tmp_path / "colt_ci"
    p.write_bytes(GOOD.encode("utf-8"))
    seen = {}

    def runner(cmd, stdin_payload):
        seen["payload"] = stdin_payload
        return 0, "ok"

    ok, detail = ci_key.push(str(p), "feranicus/electronic", runner)
    assert ok, detail
    assert isinstance(seen["payload"], bytes), (
        "the key was handed over as str; subprocess text mode will rewrite its newlines on Windows")
    assert seen["payload"] == p.read_bytes(), "the uploaded bytes differ from the file on disk"


def test_reading_the_key_never_normalises_what_is_on_disk(tmp_path):
    """Both directions, not just the write. Python's text-mode READ uses universal newlines, so
    `open(path).read()` turns a CRLF file into LF - the bytes stop being the file's bytes, and a
    reader that quietly repairs its input cannot report that the input was broken.

    This is the mutation that escaped the first run of this suite: swapping the binary read for a
    text read passed everything, because on Linux the two agree for an LF file. They do not agree
    for the file that actually caused the incident."""
    p = tmp_path / "crlf_on_disk"
    raw = GOOD.encode("utf-8").replace(b"\n", b"\r\n")
    p.write_bytes(raw)
    assert ci_key.read_key_bytes(str(p)) == raw, (
        "the reader normalised the file instead of reporting it verbatim")


def test_no_upload_path_uses_subprocess_text_mode(tmp_path):
    """SIMULATE WINDOWS (defect class 20), do not skip it: force os.linesep behaviour by giving
    the real `push` a subprocess.run that translates newlines exactly as Windows would, then
    assert the bytes gh would have received are unchanged.

    A `sys.platform` skip would have hidden this from the one machine that needed it - which is
    precisely what happened for weeks."""
    import io
    p = tmp_path / "colt_ci"
    p.write_bytes(GOOD.encode("utf-8"))
    captured = {}

    def windows_like_run(cmd, input=None, capture_output=False, timeout=None, **kw):
        # Reproduce what CPython does: if text/encoding is requested, stdin is a TextIOWrapper
        # with newline=None, which on Windows writes os.linesep for every "\n".
        if kw.get("text") or kw.get("encoding"):
            buf = io.BytesIO()
            w = io.TextIOWrapper(buf, encoding="utf-8", newline="\r\n", write_through=True)
            w.write(input or "")
            w.flush()
            captured["bytes"] = buf.getvalue()
        else:
            captured["bytes"] = input

        class _R:
            returncode = 0
            stdout = b"" if not (kw.get("text") or kw.get("encoding")) else ""
            stderr = stdout
        return _R()

    real_run = ci_key.subprocess.run
    ci_key.subprocess.run = windows_like_run
    try:
        ci_key.shutil.which = lambda n: "/usr/bin/gh"
        ok, detail = ci_key.push(str(p), "feranicus/electronic")
    finally:
        ci_key.subprocess.run = real_run
        import shutil as _sh
        ci_key.shutil.which = _sh.which
    assert ok, detail
    assert captured["bytes"] == p.read_bytes(), (
        "on a Windows box the upload would have mangled the key: %r"
        % captured["bytes"][:60])
    assert b"\r\n" not in captured["bytes"], "CRLF reached gh secret set"


def test_setup_github_cicd_uploads_through_the_one_home():
    """The script that created the broken secret must not have its own upload path any more
    (ONE HOME, defect class 32) - it had the identical `open(priv).read()` + text-mode shape."""
    import ast
    src = open(os.path.join(ROOT, "setup_github_cicd.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        txt = ast.unparse(node)
        if "gh" in txt and "secret" in txt and "DROPLET_SSH_KEY" in txt:
            raise AssertionError(
                "setup_github_cicd.py still calls gh secret set for the key itself: %s" % txt[:160])
    assert "ci_key.push_everywhere" in src, "it no longer uploads the key at all"


# ------------------------------------------- SCOPE: a secret set correctly, into the wrong level
# GitHub Actions reference, "Naming your secrets", quoted verbatim:
#   "If a secret with the same name exists at multiple levels, the secret at the lowest level takes
#    precedence. ... if an organization, repository, and environment all have a secret with the
#    same name, the environment-level secret takes precedence."
#   https://docs.github.com/en/actions/reference/security/secrets
# deploy.yml's deploy job declares `environment: production`, which setup_github_cicd.py created.
# So `gh secret set --repo <r>` writes a scope that job never reads, the workflow keeps installing
# the old key, and the log looks exactly like "the fix did not work". ONE HOME (defect class 32),
# violated by GitHub's own resolution order rather than by our code.
#
# The same page also documents a SECOND, independent mechanism, kept here because it is a different
# failure with the same symptom: "Organization and repository secrets are read when a workflow run
# is queued, and environment secrets are read when a job referencing the environment starts."

def _fake_api(repo_secrets=(), environments=(), env_secrets=None):
    env_secrets = env_secrets or {}

    def api(args):
        import json as _json
        path = args[1] if len(args) > 1 else ""
        if path.endswith("/actions/secrets") and path.startswith("repos/"):
            return 0, _json.dumps({"secrets": [{"name": n} for n in repo_secrets]})
        if path.endswith("/environments"):
            return 0, _json.dumps({"environments": [{"name": e} for e in environments]})
        for e, names in env_secrets.items():
            if path.endswith("/environments/%s/secrets" % e):
                return 0, _json.dumps({"secrets": [{"name": n} for n in names]})
        return 1, ""
    return api


def test_the_environment_scope_is_reported_last_because_it_wins():
    """Order is the whole point: the caller prints the LAST entry as the one that decides."""
    api = _fake_api(repo_secrets=["DROPLET_SSH_KEY"], environments=["production"],
                    env_secrets={"production": ["DROPLET_SSH_KEY"]})
    got = ci_key.scopes("feranicus/electronic", api)
    assert [s for s, _ in got] == ["repository", "environment:production"], got


def test_a_repo_only_secret_reports_only_the_repository():
    api = _fake_api(repo_secrets=["DROPLET_SSH_KEY"], environments=["production"],
                    env_secrets={"production": ["SOMETHING_ELSE"]})
    assert [s for s, _ in ci_key.scopes("feranicus/electronic", api)] == ["repository"]


def test_unreadable_scopes_are_not_reported_as_proof_of_absence():
    """Defect class 1. gh missing, not authenticated, or no admin rights all look like 'nothing
    found', and 'nothing found' must never be printed as 'the secret is only in one place'."""
    assert ci_key.scopes("feranicus/electronic", lambda args: (1, "")) == []


def test_the_environments_are_derived_from_the_workflows_not_guessed():
    """DERIVE N FROM SOMETHING AUTHORITATIVE (defect class 35). The workflow files say which
    environment a deploy job runs in; counting by hand is how the one that matters gets missed."""
    envs = ci_key.environments_used_by_workflows(ROOT)
    assert "production" in envs, (
        "deploy.yml declares `environment: production` and uses DROPLET_SSH_KEY, but the deriver "
        "did not find it: %s" % envs)


def test_push_everywhere_writes_the_repository_and_every_declared_environment():
    sent = []

    def runner(cmd, stdin_text):
        sent.append(cmd)
        return 0, "ok"

    import tempfile
    with tempfile.NamedTemporaryFile("wb", suffix="key", delete=False) as fh:
        fh.write(GOOD_BYTES)
        p = fh.name
    try:
        ok, details = ci_key.push_everywhere(p, "feranicus/electronic", runner,
                                             api=lambda args: (1, ""))
    finally:
        os.unlink(p)
    assert ok, details
    envs = [c[c.index("--env") + 1] for c in sent if "--env" in c]
    assert "production" in envs, (
        "the environment the deploy job actually reads was never written: %s" % sent)
    assert any("--env" not in c for c in sent), "the repository scope was skipped"
    for c in sent:
        assert "BEGIN OPENSSH" not in " ".join(c), "the key reached argv"


def test_push_everywhere_fails_if_any_scope_fails():
    """A partial write leaves the scopes DISAGREEING, which is the bug, not a lesser version of
    the fix. Anything short of all of them is a failure."""
    def runner(cmd, stdin_text):
        return (1, "denied") if "--env" in cmd else (0, "ok")

    import tempfile
    with tempfile.NamedTemporaryFile("wb", suffix="key", delete=False) as fh:
        fh.write(GOOD_BYTES)
        p = fh.name
    try:
        ok, details = ci_key.push_everywhere(p, "feranicus/electronic", runner,
                                             api=lambda args: (1, ""))
    finally:
        os.unlink(p)
    assert ok is False, "a refused environment write was reported as success: %s" % (details,)


def test_every_workflow_prints_the_fingerprint_of_the_key_it_installed():
    """A fingerprint is PUBLIC (it is in authorized_keys) and it is the difference between 'the
    secret is wrong' and 'the secret is THIS key'. Without it, which scope won is unknowable from
    the log, which is how this cost a day (defect class 26)."""
    for name in ("deploy.yml", "web-deploy.yml", "provision-patchwatch.yml"):
        s = _wf(name)
        assert "ssh-keygen -l -f ~/.ssh/deploy_key" in s, (
            "%s never names the key it installed" % name)
        assert s.index("ssh-keygen -l -f") < s.index("ssh-keygen -y -f"), (
            "%s only names the key AFTER the refusal, so a failed run says nothing" % name)


# ---------------------------------------------------------------- wiring (defect class 9)
def _wf(name):
    return open(os.path.join(ROOT, ".github", "workflows", name),
               encoding="utf-8").read()


@pytest.mark.parametrize("name", ["deploy.yml", "web-deploy.yml", "provision-patchwatch.yml"])
def test_every_workflow_that_writes_the_key_also_validates_it(name):
    """Behaviour AND wiring. A workflow that installs the secret without checking it is the exact
    hole this incident came through, and a fourth workflow added later must not reopen it."""
    s = _wf(name)
    assert "deploy_key" in s
    assert "ssh-keygen -y -f ~/.ssh/deploy_key" in s, (
        "%s writes the deploy key but never asks OpenSSH whether it IS one" % name)
    assert ">/dev/null" in s.split("ssh-keygen -y -f ~/.ssh/deploy_key")[1][:30], (
        "%s lets ssh-keygen print the public key into the build log" % name)
    assert "ship.py --fix-ci-key" in s, "%s does not say how to fix it" % name


def test_the_validation_runs_before_the_first_use_of_the_key():
    """A check after the failure it was meant to explain is decoration. The validate step must come
    before the first ssh/scp that uses the key in each workflow."""
    for name in ("deploy.yml", "web-deploy.yml", "provision-patchwatch.yml"):
        s = _wf(name)
        guard = s.index("ssh-keygen -y -f ~/.ssh/deploy_key")
        uses = [s.index(t) for t in ("-i ~/.ssh/deploy_key", "SSH_KEY: /home/runner/.ssh/deploy_key")
                if t in s]
        assert uses, "%s never uses the key it installs" % name
        assert guard < min(uses), "%s uses the key before validating it" % name


def test_ship_py_repairs_the_key_instead_of_stopping():
    """ONE COMMAND (operating principle 7) and FULL AUTOMATION (principle 1). --fix-ci-key must
    mint and authorize a usable key when the only one present cannot work, then carry on into the
    ship - not print advice and exit. Asserted on the AST so a later edit cannot quietly turn it
    back into an operator step."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read())
    main = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    blk = [n for n in ast.walk(main) if isinstance(n, ast.If)
           and "fix_ci_key" in ast.unparse(n.test)]
    assert len(blk) == 1, "--fix-ci-key has %d homes in main()" % len(blk)
    body = ast.unparse(blk[0])
    assert "ci_key.check" in body, "it does not prove the key"
    # REWRITTEN 2026-10-15 (defect class 17); the old reasoning stands and is kept. It read
    # `assert "ci_key.provision" in body`, because at the time the only repair was to MINT. Once
    # check() began proving the staging twin as well, the ordinary failure became "the existing
    # good key is not in staging's authorized_keys", and minting a replacement for that would
    # rotate a working credential over one missing line. ensure_usable() is the repair now: it
    # authorizes first and still mints when OpenSSH refuses the key. The property the test is
    # really about is unchanged - ship.py REPAIRS rather than telling the operator to go and do it.
    assert "ci_key.ensure_usable" in body, (
        "it does not repair an unusable key - it tells the operator to go and do it")
    # `"ci_key.push" in body` was the first version of this line and it is a SUBSTRING of
    # push_everywhere, so reverting ship.py to the repo-only write passed (defect class 4 again).
    assert "ci_key.push_everywhere" in body, (
        "ship.py writes only one scope; an environment secret of the same name would keep winning")
    assert "ci_key.scopes" in body, "it does not report which scope actually decides"
    assert body.count("sys.exit(2)") >= 2, "a refusal path does not stop the run"
    # and it must FALL THROUGH on success, or the operator needs a second command
    assert "return" not in body.split("ci_key.push")[-1], (
        "it returns after fixing the key, which makes this two commands")


def test_the_shape_check_has_one_home():
    """ONE HOME (defect class 32). The reason the old path failed is that nothing owned the question
    'is this a key'. If a second copy appears, the newer one always loses."""
    import ast
    import glob
    offenders = []
    for f in glob.glob(os.path.join(ROOT, "*.py")):
        if os.path.basename(f) in ("ci_key.py",):
            continue
        src = open(f, encoding="utf-8", errors="replace").read()
        if "BEGIN OPENSSH PRIVATE KEY" in src and "PuTTY-User-Key-File" in src:
            offenders.append(os.path.basename(f))
    assert not offenders, "a second key-shape checker appeared in: %s" % offenders
    tree = ast.parse(open(os.path.join(ROOT, "ci_key.py"), encoding="utf-8").read())
    names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert names.count("key_shape") == 1


def test_setup_github_cicd_no_longer_uploads_an_unproven_key():
    """The script that created this incident must not be able to create it again.

    Assert the PROPERTY by AST, not a string the explanatory comment also contains (defect class
    4): the first version of this test passed against `pass  # import ci_key`, because the comment
    saying what was removed contained the name of the thing that was removed. This now requires a
    real CALL to ci_key.check whose line number precedes the upload."""
    import ast
    src = open(os.path.join(ROOT, "setup_github_cicd.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    # REWRITTEN 2026-10-15 (defect class 17), old reasoning kept: this anchored on the literal
    # "DROPLET_SSH_KEY", which that file used to pass to `gh secret set` itself. It no longer has
    # its own upload path at all - ci_key owns it - so the anchor is now the call that uploads.
    uploads = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute) and n.func.attr == "push_everywhere"]
    assert uploads, "setup_github_cicd.py no longer uploads the key through ci_key"
    upload = min(uploads)
    proofs = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "check"
              and isinstance(n.func.value, ast.Name) and n.func.value.id == "ci_key"]
    assert proofs, "setup_github_cicd.py never calls ci_key.check - it uploads a key on faith"
    assert min(proofs) < upload, (
        "ci_key.check runs at line %d, AFTER the upload at line %d" % (min(proofs), upload))
    guarded = [n for n in ast.walk(tree) if isinstance(n, ast.If)
               and any(getattr(c, "lineno", None) in proofs for c in ast.walk(n.test))]
    assert guarded, "ci_key.check is called but its answer is not acted on"
    for node in guarded:
        assert not [c for c in ast.walk(node.test) if isinstance(c, ast.Constant)], (
            "the verdict is short-circuited by a constant: if %s" % ast.unparse(node.test))
        assert any(isinstance(c, ast.Call) and ast.unparse(c).startswith("sys.exit")
                   for c in ast.walk(node)), (
            "a failed proof does not stop the upload: if %s" % ast.unparse(node.test))


# =============================================================================================
# THE KEY MUST REACH EVERY DROPLET THE PIPELINE DEPLOYS TO, not just production.
#
# 2026-10-15. The dedicated CI key was minted and authorized on the default host - production.
# Nothing put it on the staging twin, so the first real pipeline run passed the gate, built and
# signed three images, scanned all three, and then died on the staging hop with
# "Permission denied (publickey)". Production was untouched, which is the gate behaving; it just
# cost a full pipeline to find one missing line in one authorized_keys file.
# =============================================================================================

def test_the_host_list_is_derived_from_each_hosts_own_home():
    """ONE HOME (defect class 32). Production lives in ci_key.HOST, staging in stagegate.STAGING.
    If either address were copied into ci_key.py there would be two homes, and the copy is the one
    that goes stale when a droplet is replaced."""
    import stagegate
    hosts = ci_key.deploy_hosts()
    addrs = [h for _u, h, _l in hosts]
    labels = [l for _u, _h, l in hosts]
    assert ci_key.HOST in addrs, "production is missing from the deploy host list"
    assert stagegate.STAGING in addrs, (
        "the staging twin is not in the list, so provisioning will skip it exactly as it did "
        "before: %s" % hosts)
    assert labels == ["production", "staging"], (
        "every host must be LABELLED - an unlabelled address in a failure line is what made this "
        "take a whole pipeline run to read: %s" % hosts)

    src = open(os.path.join(ROOT, "ci_key.py"), encoding="utf-8").read()
    assert stagegate.STAGING not in src, (
        "the staging address is written into ci_key.py; it has a home in stagegate.py and a "
        "second copy always drifts")


def test_stagegate_is_safe_to_import_for_its_constant():
    """deploy_hosts() imports stagegate to read one constant. That is only acceptable while
    stagegate's top level does nothing - no ssh, no deploy, no side effect."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8").read())
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef,
                                 ast.Assign, ast.AnnAssign, ast.Expr, ast.If)), (
            "stagegate.py now executes %s at import time, so reading its STAGING constant would "
            "run it" % type(node).__name__)


def test_provisioning_and_proving_both_walk_every_host():
    """ANCHOR ON THE CALL SITE (defect class 4). The bug was not in authorize() - that function
    always took a host argument. It was that provision() called it once, with the default. So the
    property is that both the writer and the prover ITERATE."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "ci_key.py"), encoding="utf-8").read())
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for name in ("authorize_everywhere", "check"):
        assert name in fns, "%s is gone; this guard is no longer reading what provisions" % name
        src = ast.unparse(fns[name])
        assert "deploy_hosts()" in src, (
            "%s does not walk deploy_hosts(), so it can authorize or prove production only - "
            "which is the 2026-10-15 staging failure" % name)
    prov = ast.unparse(fns["provision"])
    assert "authorize_everywhere" in prov, (
        "provision() authorizes a single host again; staging will be left without the key")


def test_an_unknown_on_any_host_is_not_a_pass(monkeypatch):
    """A credential nobody can read back must be PROVEN before it is written, and this file's own
    rule is that an UNKNOWN is not a pass. Staging being unreachable must block --push rather than
    quietly uploading a key that only half the estate accepts."""
    monkeypatch.setattr(ci_key, "key_shape", lambda _t: (True, "ok"))
    monkeypatch.setattr(ci_key, "read_key", lambda _p: "x")
    monkeypatch.setattr(ci_key, "parses", lambda _p: (True, "ok"))
    monkeypatch.setattr(ci_key, "deploy_hosts",
                        lambda: [("root", "1.2.3.4", "production"),
                                 ("root", "5.6.7.8", "staging")])

    answers = {"1.2.3.4": (True, "authenticated"), "5.6.7.8": (None, "timed out")}
    monkeypatch.setattr(ci_key, "authenticates",
                        lambda path, user=None, host=None, **kw: answers[host])
    assert ci_key.check("irrelevant") is False, (
        "an UNKNOWN on staging counted as a pass; --push would upload a key the staging job "
        "cannot use, which is precisely how this reached a live pipeline")

    answers["5.6.7.8"] = (False, "permission denied")
    assert ci_key.check("irrelevant") is False, "a REJECTION on staging counted as a pass"
    answers["5.6.7.8"] = (True, "authenticated")
    assert ci_key.check("irrelevant") is True, (
        "both hosts authenticate and the check still refuses - it can no longer pass at all")


def test_a_missing_authorized_keys_line_does_not_rotate_a_working_key(monkeypatch):
    """THE REPAIR MUST FIT THE FAULT. Once check() started proving staging too, the existing good
    CI key failed it for one reason: its public half was not in staging's authorized_keys. If that
    path mints a new key, a working credential is rotated - and re-pushed to every secret scope -
    to fix a missing line. ensure_usable() authorizes first and mints only when OpenSSH refuses."""
    calls = {"authorized": 0, "minted": 0}
    state = {"ok": False}

    monkeypatch.setattr(ci_key, "find_key", lambda: "/tmp/existing")
    monkeypatch.setattr(ci_key, "parses", lambda _p: (True, "ok"))

    def fake_authorize_everywhere(path=None):
        calls["authorized"] += 1
        state["ok"] = True                       # the line is appended; now it works
        return True, [("production", "1.2.3.4", True, "ok"), ("staging", "5.6.7.8", True, "ok")]

    monkeypatch.setattr(ci_key, "authorize_everywhere", fake_authorize_everywhere)
    monkeypatch.setattr(ci_key, "check", lambda _p: state["ok"])
    monkeypatch.setattr(ci_key, "provision",
                        lambda path=None: (calls.__setitem__("minted", calls["minted"] + 1),
                                           (True, "/tmp/minted"))[1])

    ok, path = ci_key.ensure_usable()
    assert ok and path == "/tmp/existing", (ok, path)
    assert calls["authorized"] == 1, "it never tried the small repair"
    assert calls["minted"] == 0, (
        "a working key was ROTATED because one host was missing an authorized_keys line")


def test_a_key_openssh_refuses_still_gets_a_freshly_minted_one(monkeypatch):
    """The other direction (defect class 13 - defeat the guard, not just confirm it). A key with a
    passphrase cannot be repaired by authorizing it anywhere, and that is the case minting exists
    for; it must still happen."""
    monkeypatch.setattr(ci_key, "find_key", lambda: "/tmp/passphrased")
    monkeypatch.setattr(ci_key, "parses", lambda _p: (False, "incorrect passphrase"))
    monkeypatch.setattr(ci_key, "authorize_everywhere",
                        lambda path=None: pytest.fail("authorized a key OpenSSH cannot read"))
    monkeypatch.setattr(ci_key, "provision", lambda path=None: (True, "/tmp/minted"))
    assert ci_key.ensure_usable() == (True, "/tmp/minted")
