"""test_secret_scan.py - the gitleaks allowlist must never be able to hide a real credential.

THE INCIDENT, 2026-10-15. `quality-and-secrets` is the check the branch ruleset requires. The
first time it ever actually blocked a merge (PR #19), it reported five findings - and the oldest,
`tests/test_llm_guard.py`, has been in the tree since **2026-08-22**. So the secret scanner had
been RED for nearly two months and nobody saw it, because the rule it belongs to was bypassed on
every single push. CLAUDE.md already says it: an alert nobody gets is not an alert.

All five findings are code ABOUT secrets - the delimiters a key detector matches on, synthetic key
fixtures, and a list of tokens an LLM guard must redact. Allowlisting those three files is correct
and it is also a new hole: gitleaks will now ignore anything in them, including a real key pasted
there by accident.

THIS FILE IS THAT HOLE'S GUARD. It is the reason the allowlist is defensible rather than a rubber
stamp, and it fails the build if:

  * an allowlisted file contains a private key that ACTUALLY PARSES (ssh-keygen -y is the judge,
    not a regex and not an opinion);
  * an allowlisted file contains a token that matches a real credential format outside the
    documented synthetic set;
  * an allowlist entry points at a file that no longer exists, because a stale entry silently
    widens over time as paths are reused;
  * the allowlist grows without this test being updated.
"""
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, ".gitleaks.toml")

# The gitleaks default rules that actually fired on PR #19, transcribed from its own output.
PRIVATE_KEY = re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY[A-Z ]*-----")
GITHUB_PAT = re.compile(r"gh[pousr]_[0-9a-zA-Z]{36}")

# The ONLY token-shaped strings allowed to exist in the allowlisted files, each because a test
# needs the guard to redact it. Anything else is a finding, even inside an allowlisted path.
SYNTHETIC = {
    "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
}


_B64_LINE = re.compile(r'^[\s"\'(),]*[A-Za-z0-9+/=]*(\\n)?[\s"\'(),]*$')


def key_blocks(src):
    """Every PEM block in `src`, as file content, found LINE BY LINE.

    REWRITTEN 2026-10-15 after the first version let the mutation through, and the old reasoning is
    kept because it is the whole lesson. It used one regex:

        -----BEGIN[ A-Z]*PRIVATE KEY[A-Z ]*-----.*?-----END[ A-Z]*PRIVATE KEY[A-Z ]*-----

    with re.S. In ci_key.py the first BEGIN is a DELIMITER CONSTANT on line 53, so even the
    non-greedy match ran from there to the END of a real key appended 25 KB later and returned ONE
    block of 25,228 characters - python source with a key buried in it. ssh-keygen refused that
    soup, the assertion `returncode != 0` passed, and the guard reported health while the exact
    thing it exists to catch sat in the file. Defect class 13: the negative passed because of
    something other than the property under test.

    A key is a BEGIN line, then base64 (possibly wrapped in python quoting), then an END line. So
    the body is required to be base64-ish all the way through, and a block that is not stops being
    a block instead of swallowing the rest of the file.
    """
    out, cur = [], None
    for line in src.splitlines():
        # ONE-LINE FORM FIRST. A key copied out of JSON arrives as a single escaped string -
        # "-----BEGIN PRIVATE KEY-----\nMII...\n-----END PRIVATE KEY-----\n" - which is exactly how
        # a Google service-account file stores one, and therefore the likeliest accident of all.
        # A line-by-line scanner that only pairs a BEGIN line with a later END line never sees it;
        # that gap let the second mutation through on the first attempt.
        if (re.search(r"-----BEGIN[ A-Z]*PRIVATE KEY[A-Z ]*-----", line)
                and re.search(r"-----END[ A-Z]*PRIVATE KEY[A-Z ]*-----", line)):
            label = re.search(r"-----BEGIN ([A-Z ]*PRIVATE KEY)-----", line).group(1)
            inner = re.split(r"-----BEGIN[ A-Z]*PRIVATE KEY[A-Z ]*-----", line, 1)[1]
            inner = re.split(r"-----END[ A-Z]*PRIVATE KEY[A-Z ]*-----", inner, 1)[0]
            body = re.sub(r'[\s"\'(),]|\\n', "", inner)
            if body:
                out.append((label, body))
            continue
        if cur is None:
            m = re.search(r"-----BEGIN ([A-Z ]*PRIVATE KEY)-----", line)
            if m:
                cur, label = [], m.group(1)
            continue
        if re.search(r"-----END[ A-Z]*PRIVATE KEY[A-Z ]*-----", line):
            out.append((label, "".join(cur)))
            cur = None
            continue
        if not _B64_LINE.match(line):        # prose, code, anything: this was never a key block
            cur = None
            continue
        cur.append(re.sub(r'[\s"\'(),]|\\n', "", line))
    # KEEP THE ARMOUR THE KEY ARRIVED IN. Re-wrapping every body as OPENSSH looked tidy and was
    # wrong: an RSA PEM body inside OPENSSH armour is refused by ssh-keygen for the WRONG reason,
    # so a real RSA key pasted into an allowlisted file read as "safely unparseable". The label is
    # part of the evidence, not decoration.
    return ["-----BEGIN %s-----\n%s\n-----END %s-----\n"
            % (label, "\n".join(body[i:i + 64] for i in range(0, len(body), 64)), label)
            for label, body in out if body]


def allowlisted_paths():
    """The paths the gitleaks config exempts, read FROM the config (defect class 35: derive N from
    something authoritative; a hand-copied list here would drift from the file that matters)."""
    src = open(CONFIG, encoding="utf-8").read()
    block = src.split("paths = [", 1)[1].split("]", 1)[0]
    out = []
    for m in re.finditer(r"'''(.+?)'''", block):
        pat = m.group(1)
        if pat.startswith("^") and pat.endswith("$"):          # a concrete file, not a wildcard
            out.append(pat[1:-1].replace("\\.", "."))
    return out


def test_the_config_really_exempts_the_three_files():
    """PROVE THE FIXTURE (defect class 12). If the parser returned nothing, every check below
    would pass while measuring an empty list."""
    got = allowlisted_paths()
    assert set(got) == {"ci_key.py", "tests/test_ci_key.py", "tests/test_llm_guard.py"}, (
        "the allowlist changed and this guard was not updated with it: %s" % got)


@pytest.mark.parametrize("rel", ["ci_key.py", "tests/test_ci_key.py", "tests/test_llm_guard.py"])
def test_every_allowlisted_file_still_exists(rel):
    """A stale entry is worse than no entry: the path gets reused one day and arrives pre-exempted."""
    assert os.path.exists(os.path.join(ROOT, rel)), (
        "%s is allowlisted in .gitleaks.toml but does not exist" % rel)


@pytest.mark.skipif(not shutil.which("ssh-keygen"), reason="ssh-keygen not on PATH")
@pytest.mark.parametrize("rel", ["ci_key.py", "tests/test_ci_key.py", "tests/test_llm_guard.py"])
def test_no_allowlisted_file_contains_a_key_that_parses(rel, tmp_path):
    """THE WHOLE POINT. A regex cannot tell a synthetic fixture from a real key; OpenSSH can.

    Every PEM block in an exempted file is extracted and handed to `ssh-keygen -y`. If one of them
    is a usable private key, this fails - which is the protection gitleaks can no longer give once
    the path is allowlisted.
    """
    for i, body in enumerate(key_blocks(open(os.path.join(ROOT, rel), encoding="utf-8").read())):
        p = tmp_path / ("block%d" % i)
        p.write_bytes(body.encode("utf-8"))      # BINARY: write_text translates on Windows
        os.chmod(str(p), 0o600)
        r = subprocess.run(["ssh-keygen", "-y", "-f", str(p), "-P", ""],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        assert r.returncode != 0, (
            "%s contains a PEM block that OpenSSH ACCEPTS as a private key. gitleaks is "
            "allowlisted on this path, so nothing else would have caught it." % rel)


@pytest.mark.parametrize("rel", ["ci_key.py", "tests/test_ci_key.py", "tests/test_llm_guard.py"])
def test_no_allowlisted_file_carries_an_undocumented_token(rel):
    """A token inside an exempted file must be one this suite deliberately put there."""
    src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    found = set(GITHUB_PAT.findall(src))
    unknown = found - SYNTHETIC
    assert not unknown, (
        "%s contains token(s) not in the documented synthetic set, and gitleaks is allowlisted "
        "here: %s" % (rel, sorted(unknown)))


def test_the_allowlist_is_small_enough_to_read():
    """Scope creep is how an allowlist becomes a disabled scanner. Three files is reviewable; a
    growing list is not, and the next entry should have to argue for itself."""
    paths = allowlisted_paths()
    assert len(paths) <= 4, (
        "the gitleaks allowlist has grown to %d concrete files. Each one is a place a real "
        "credential could hide: %s" % (len(paths), paths))


def test_the_service_account_keys_are_not_in_the_repository():
    """These exist in the operator's working directory and hold REAL Google private keys. They are
    gitignored and have never been committed - verified 2026-10-15 - and on a PUBLIC repository
    that distinction is the whole ballgame. Asserted here so a future `git add -f` is caught by
    the suite rather than by somebody reading the repo."""
    r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        pytest.skip("git not available here")
    tracked = set((r.stdout or "").split())
    leaked = [f for f in tracked
              if f.endswith("_sa.json") or re.match(r"colt-bots-[0-9a-f]+\.json$", f)]
    assert not leaked, "a service-account key is TRACKED in a public repository: %s" % leaked
