#!/usr/bin/env python3
"""ci_key.py - prove the CI deploy key WORKS before it becomes a GitHub secret.

THE INCIDENT, 2026-10-14. Every GitHub Actions deploy this repo has ever attempted died at the
first ssh with:

    Load key "/home/runner/.ssh/deploy_key": error in libcrypto
    root@64.225.108.200: Permission denied (publickey,password).

The workflow writes the secret correctly (`printf '%s\\n'`), so the SECRET'S OWN CONTENT is not a
usable OpenSSH private key. It was uploaded by setup_github_cicd.py, which read a file and handed
it to `gh secret set` WITHOUT EVER PROVING IT WAS A KEY, let alone that it could authenticate. An
unverifiable write to a place nobody can read back is how a credential rots silently for weeks.

WHAT THIS DOES, in order, and it refuses to continue the moment one step fails:
  1. SHAPE   - reads the file and says what is wrong with it IN WORDS (a PuTTY .ppk, the PUBLIC
               half, a passphrase-protected key, newlines collapsed into one line, no trailing
               newline). This is the step that turns "error in libcrypto" into a sentence.
  2. PARSES  - `ssh-keygen -y -f <key>`, whose output goes to /dev/null: if OpenSSH itself cannot
               derive the public half, GitHub's runner will not either. Same binary, same verdict.
  3. WORKS   - one BatchMode ssh to the droplet. A syntactically perfect key that is not in
               authorized_keys is still a broken deploy.
  4. UPLOADS - `gh secret set DROPLET_SSH_KEY`, value on STDIN, never argv (the set_secret.py rule:
               argv is visible in the process table and in shell history).

NOTHING is uploaded unless 1-3 all passed, because the only thing worse than a missing secret is a
secret that looks present and has never worked. Key material is never printed: step 2's output is
discarded and only the FINGERPRINT is shown, which is public information by construction.

    python ci_key.py                 # check only, change nothing
    python ci_key.py --push          # check, then upload if every check passed
    python ship.py --fix-ci-key      # the same, then the normal ship (ONE command, not two)
"""
import argparse
import base64
import os
import shutil
import struct
import subprocess
import sys

REPO = os.environ.get("REPO", "feranicus/electronic")
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")

# The key setup_github_cicd.py generates, then the general-purpose one ship.py deploys with.
CANDIDATES = [os.path.join(os.path.expanduser("~"), ".ssh", "colt_deploy"),
              os.path.join(os.path.expanduser("~"), ".ssh", "id_ed25519"),
              os.path.join(os.path.expanduser("~"), ".ssh", "id_rsa")]

SECRET = "DROPLET_SSH_KEY"

_OPENSSH_BEGIN = "-----BEGIN OPENSSH PRIVATE KEY-----"
_PEM_BEGINS = ("-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN EC PRIVATE KEY-----",
               "-----BEGIN PRIVATE KEY-----", "-----BEGIN DSA PRIVATE KEY-----")


def openssh_cipher(text):
    """The cipher an OPENSSH-format private key is encrypted with, or None if it cannot be read.

    "none" means no passphrase. ANYTHING ELSE means a passphrase, and a CI runner cannot type one.

    THIS IS WHY THE WHOLE CI PATH WAS BROKEN and why the first version of this file missed it: a
    modern OpenSSH key says nothing about encryption in its ARMOUR. There is no "ENCRYPTED" header
    and no `Proc-Type: 4,ENCRYPTED` line - those belong to the old PEM format. The cipher name sits
    inside the base64 body, in the clear, right after the "openssh-key-v1\\0" magic:

        magic "openssh-key-v1\\0" | uint32 len | ciphername | uint32 len | kdfname | ...

    So the only honest way to answer "does this key have a passphrase" without ASKING FOR THE
    PASSPHRASE is to decode the body and read that field. Measured against real keys:
    `ssh-keygen -N ""` gives "none", `ssh-keygen -N "x"` gives "aes256-ctr".
    """
    if not text or "-----BEGIN OPENSSH PRIVATE KEY-----" not in text:
        return None
    try:
        body = text.split("-----BEGIN OPENSSH PRIVATE KEY-----", 1)[1].split("-----END", 1)[0]
        raw = base64.b64decode("".join(body.split()), validate=False)
    except Exception:
        return None
    magic = b"openssh-key-v1\x00"
    if not raw.startswith(magic):
        return None
    off = len(magic)
    if len(raw) < off + 4:
        return None
    n, = struct.unpack(">I", raw[off:off + 4])
    off += 4
    if n <= 0 or n > 64 or len(raw) < off + n:
        return None
    try:
        return raw[off:off + n].decode("ascii")
    except UnicodeDecodeError:
        return None


def key_shape(text):
    """(ok, why) from the TEXT alone - no subprocess, no network, so it is testable and fast.

    Every branch names a cause the operator can act on. A wildcard that shrugs is worse than no
    check at all (defect class 6: an unrecognised answer must FAIL, never score as a pass), so the
    fall-through here is a PASS only after the positive OpenSSH/PEM evidence has been found.
    """
    if text is None:
        return False, "the key file could not be read"
    if not text.strip():
        return False, "the key is EMPTY (0 bytes of content)"
    if "PuTTY-User-Key-File" in text:
        return False, ("this is a PuTTY .ppk file, which OpenSSH cannot read. In PuTTYgen: "
                       "Conversions -> Export OpenSSH key, and use THAT file")
    if text.lstrip().startswith(("ssh-rsa ", "ssh-ed25519 ", "ecdsa-sha2-", "ssh-dss ")):
        return False, ("this is the PUBLIC half (a .pub file). The secret needs the PRIVATE key - "
                       "the same path WITHOUT the .pub extension")
    has_openssh = _OPENSSH_BEGIN in text
    has_pem = any(b in text for b in _PEM_BEGINS)
    if not (has_openssh or has_pem):
        return False, ("no BEGIN line found, so this is not a private key in any format OpenSSH "
                       "reads. First 24 characters: %r" % text[:24])
    if "-----END " not in text:
        return False, ("the BEGIN line is present but the END line is MISSING - the key was "
                       "truncated when it was pasted")
    # PASSPHRASE. Two formats, two completely different tells: the old PEM armour announces it in
    # a header, the modern OpenSSH armour says nothing and keeps the cipher name in the base64.
    # Reading only the header is how a passphrase-protected key reached GitHub in the first place.
    cipher = openssh_cipher(text)
    if "Proc-Type: 4,ENCRYPTED" in text or "DEK-Info:" in text or (
            cipher is not None and cipher != "none"):
        return False, ("this key is PROTECTED BY A PASSPHRASE (cipher: %s). A GitHub runner has no "
                       "keyboard, so it can never unlock it - that is the 'error in libcrypto' this "
                       "repo has been seeing. A CI deploy key must have no passphrase; mint a "
                       "dedicated one with --mint, which leaves this key untouched"
                       % (cipher or "PEM-encrypted"))
    if text.count("\n") < 3:
        return False, ("the key is on ONE line (%d newlines). Its line breaks were collapsed on "
                       "the way into the secret; paste the file verbatim" % text.count("\n"))
    if not text.endswith("\n"):
        return False, ("the key has NO TRAILING NEWLINE. OpenSSH rejects the final base64 line "
                       "without it, and that is exactly the 'error in libcrypto' signature")
    return True, ("looks like a %s private key, %d lines, trailing newline present"
                  % ("OpenSSH" if has_openssh else "PEM", text.count("\n")))


def read_key(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def parses(path):
    """(ok, fingerprint_or_error). OpenSSH's own verdict, from OpenSSH's own binary.

    `-y` writes the PUBLIC key to stdout; it is captured and immediately thrown away so no key
    material can reach a log. Only the fingerprint, which is published in authorized_keys, is kept.
    """
    if not shutil.which("ssh-keygen"):
        return None, "ssh-keygen is not on PATH, so the key could not be parsed here"
    # NEVER PROMPT. The first version of this ran `ssh-keygen -y -f <key>` with an inherited stdin,
    # so on a passphrase-protected key it stopped and asked the OPERATOR to type the passphrase -
    # then reported "incorrect passphrase" as if the key were corrupt. A check that interrogates
    # the human has stopped measuring and started negotiating, and its answer was wrong twice over:
    # the key is fine, it is simply unusable BY CI. `-P ""` plus a closed stdin fails immediately.
    try:
        r = subprocess.run(["ssh-keygen", "-y", "-f", path, "-P", ""],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "ssh-keygen could not be run (%s)" % type(e).__name__
    if r.returncode != 0 and "passphrase" in ((r.stderr or "") + (r.stdout or "")).lower():
        return False, ("this key needs a passphrase, so GitHub Actions can never use it "
                       "(the passphrase is correct; a runner has nobody to type it)")
    if r.returncode != 0:
        said = ((r.stderr or "") + (r.stdout or "")).strip().splitlines()
        return False, (said[-1] if said else "ssh-keygen exited %d" % r.returncode)
    f = subprocess.run(["ssh-keygen", "-l", "-f", path], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=30)
    return True, (f.stdout or "").strip() or "parsed"


def authenticates(path, user=USER, host=HOST, timeout=40):
    """(ok, detail). None means we could not tell - a probe that cannot see its subject must not
    answer about it (defect class 1), so an unknown NEVER counts as a pass on the way to --push."""
    cmd = ["ssh", "-i", path, "-o", "StrictHostKeyChecking=accept-new", "-o", "BatchMode=yes",
           "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15", "-o", "IdentitiesOnly=yes",
           "%s@%s" % (user, host), "echo __ci_key_ok__"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "ssh to %s@%s timed out after %ds - nothing concluded" % (user, host, timeout)
    except OSError as e:
        return None, "ssh could not be run (%s)" % type(e).__name__
    out = (r.stdout or "") + (r.stderr or "")
    if "__ci_key_ok__" in out:
        return True, "authenticated to %s@%s" % (user, host)
    low = out.lower()
    if "permission denied" in low:
        return False, ("the key PARSES but %s@%s rejected it: its public half is not in "
                       "/root/.ssh/authorized_keys" % (user, host))
    if "connection timed out" in low or "connection refused" in low or "no route" in low:
        return None, "the droplet did not answer on port 22 - nothing concluded about the key"
    return False, (out.strip().splitlines() or ["ssh exited %d" % r.returncode])[-1]


CI_KEY = os.path.join(os.path.expanduser("~"), ".ssh", "colt_ci")


def mint(path=CI_KEY):
    """Create a DEDICATED passphrase-less key for CI. (ok, detail).

    A separate key, never a copy of the operator's own with the passphrase stripped, because the
    two have different blast radii: this one lives unencrypted in a GitHub secret and can be
    revoked on its own by deleting one line from authorized_keys. His personal key is never read,
    never copied and never modified. An existing file is NEVER overwritten - that would silently
    orphan a key already in authorized_keys.
    """
    if os.path.exists(path):
        return True, "already exists: %s" % path
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError as e:
        return False, "could not create %s (%s)" % (os.path.dirname(path), type(e).__name__)
    r = subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", path, "-N", "", "-q",
                        "-C", "github-actions-deploy-cybergod"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0 or not os.path.exists(path):
        return False, ((r.stderr or r.stdout or "").strip()[:200]
                       or "ssh-keygen exited %d" % r.returncode)
    return True, "minted a passphrase-less CI key at %s" % path


def authorize(path=CI_KEY, user=USER, host=HOST, timeout=60):
    """Append the PUBLIC half to the droplet's authorized_keys, idempotently. (ok, detail).

    Uses whatever identity already works from this PC (ssh-agent or the default key), which is the
    same thing `python ship.py` deploys with, so if a direct deploy works this does too. Only the
    PUBLIC half ever travels, and `grep -qxF` makes a re-run a no-op.
    """
    pub = path + ".pub"
    if not os.path.exists(pub):
        return False, "no public half at %s" % pub
    with open(pub, encoding="utf-8") as fh:
        pk = fh.read().strip()
    if not pk.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
        return False, "%s does not look like a public key" % pub
    remote = ("mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && "
              "chmod 600 ~/.ssh/authorized_keys && "
              "grep -qxF %(k)s ~/.ssh/authorized_keys || printf '%%s\\n' %(k)s "
              ">> ~/.ssh/authorized_keys; "
              "grep -qxF %(k)s ~/.ssh/authorized_keys && echo __authorized__"
              % {"k": "'" + pk.replace("'", "") + "'"})
    try:
        r = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "BatchMode=yes",
                            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15",
                            "%s@%s" % (user, host), remote],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "ssh to %s@%s timed out; the key was NOT authorized" % (user, host)
    out = (r.stdout or "") + (r.stderr or "")
    if "__authorized__" in out:
        return True, "public half present in %s@%s:~/.ssh/authorized_keys" % (user, host)
    return False, ("could not authorize it from this PC: %s"
                   % ((out.strip().splitlines() or ["ssh exited %d" % r.returncode])[-1]))


def _gh_json(args, runner=None):
    """`gh api ...` -> parsed JSON, or None if it could not be read. Never raises."""
    if runner is not None:
        rc, out = runner(args)
    else:
        if not shutil.which("gh"):
            return None
        try:
            r = subprocess.run(["gh"] + args, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        rc, out = r.returncode, (r.stdout or "")
    if rc != 0:
        return None
    try:
        import json as _json
        return _json.loads(out or "null")
    except ValueError:
        return None


def scopes(repo=REPO, runner=None):
    """Every place DROPLET_SSH_KEY is defined, in the order GitHub resolves them.

    WHY THIS EXISTS. `gh secret set --repo <r>` writes the REPOSITORY secret. But deploy.yml's
    deploy job declares `environment: production`, and an ENVIRONMENT secret of the same name
    OVERRIDES the repository one. setup_github_cicd.py created that environment months ago. So the
    secret was set, correctly, into a scope the job never reads - the workflow kept installing the
    old passphrase-protected key and kept failing with the same message, which looks exactly like
    "the fix did not work" and is in fact ONE HOME violated by GitHub's own resolution order
    (defect class 32: a value with several homes drifts, and the newer one always loses).

    Returns a list of (scope_label, where) ordered LEAST to MOST specific, so the last entry is the
    one that actually wins. An empty list means nothing could be read, which is not the same as
    "the secret is only in one place" - the caller must not treat it as proof.
    """
    owner, _, name = repo.partition("/")
    found = []
    org = _gh_json(["api", "orgs/%s/actions/secrets" % owner, "--jq", ".secrets[].name"],
                   runner) if runner else None
    if org and SECRET in org:
        found.append(("organisation", "orgs/%s" % owner))
    rs = _gh_json(["api", "repos/%s/actions/secrets" % repo], runner)
    if rs and any(s.get("name") == SECRET for s in (rs.get("secrets") or [])):
        found.append(("repository", repo))
    envs = _gh_json(["api", "repos/%s/environments" % repo], runner)
    for e in ((envs or {}).get("environments") or []):
        en = e.get("name")
        if not en:
            continue
        es = _gh_json(["api", "repos/%s/environments/%s/secrets" % (repo, en)], runner)
        if es and any(s.get("name") == SECRET for s in (es.get("secrets") or [])):
            found.append(("environment:%s" % en, en))
    return found


def environments_used_by_workflows(root=None):
    """Which environments the DEPLOY jobs actually declare, read from the workflows themselves.

    DERIVE N FROM SOMETHING AUTHORITATIVE (defect class 35). Counting the scopes by hand is how the
    one that matters gets missed; the workflow files are the authority on which environment a
    deploy job runs in, so they are what gets read.
    """
    import glob
    import re as _re
    root = root or os.path.dirname(os.path.abspath(__file__))
    out = []
    for f in sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.yml"))):
        src = open(f, encoding="utf-8", errors="replace").read()
        if "DROPLET_SSH_KEY" not in src:
            continue
        for m in _re.finditer(r"^\s{4}environment:\s*([A-Za-z0-9._-]+)\s*$", src, _re.M):
            if m.group(1) not in out:
                out.append(m.group(1))
    return out


def push(path, repo=REPO, runner=None, env=None):
    """gh secret set, VALUE ON STDIN. Returns (ok, detail). `env` targets one environment."""
    if runner is None:
        if not shutil.which("gh"):
            return False, ("the GitHub CLI 'gh' is not installed, so the secret cannot be set from "
                           "here. Install: winget install GitHub.cli   then: gh auth login")
        st = subprocess.run(["gh", "auth", "status"], capture_output=True)
        if st.returncode != 0:
            return False, "gh is installed but not authenticated. Run: gh auth login"

        def runner(cmd, stdin_text):
            r = subprocess.run(cmd, input=stdin_text, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
            return r.returncode, (r.stdout or "") + (r.stderr or "")

    text = read_key(path)
    if text is None:
        return False, "the key file disappeared between the check and the upload"
    cmd = ["gh", "secret", "set", SECRET, "--repo", repo]
    if env:
        cmd += ["--env", env]
    rc, out = runner(cmd, text)
    if rc != 0:
        return False, (out or "gh exited %d" % rc).strip()[:300]
    return True, "%s set on %s%s" % (SECRET, repo, " (environment: %s)" % env if env else "")


def push_everywhere(path, repo=REPO, runner=None, api=None):
    """Set the secret in EVERY scope the deploy jobs can read. (ok, [detail, ...]).

    The repository scope is always written. Every environment a DROPLET_SSH_KEY-using workflow
    declares is ALSO written, because an environment secret silently overrides the repository one
    and that is exactly how a correct fix kept failing. Writing the same proven key into each scope
    makes them agree, which is the only way to have one effective value when GitHub insists on
    several homes.
    """
    details = []
    ok_all, detail = push(path, repo, runner)
    details.append(("repository", ok_all, detail))
    targets = list(environments_used_by_workflows())
    for label, where in scopes(repo, api):
        if label.startswith("environment:") and where not in targets:
            targets.append(where)
    for e in targets:
        ok, d = push(path, repo, runner, env=e)
        details.append(("environment:%s" % e, ok, d))
        ok_all = ok_all and ok
    return ok_all, details


def find_key(explicit=None):
    if explicit:
        return explicit if os.path.exists(explicit) else None
    for c in CANDIDATES:
        if os.path.exists(c):
            return c
    return None


def check(path):
    """Run every read-only check and print the comparison made, not a bare verdict.

    Returns True only when the key is PROVEN usable: shape ok, OpenSSH parses it, and the droplet
    accepted it. An UNKNOWN at any step returns False, because --push must never upload a secret
    on the strength of a check that did not run.
    """
    print("  key file : %s" % path)
    ok_shape, why = key_shape(read_key(path))
    print("  %s shape: %s" % ("[ok]" if ok_shape else "[X] ", why))
    if not ok_shape:
        return False
    ok_parse, detail = parses(path)
    print("  %s parse: %s" % ("[ok]" if ok_parse else "[X] " if ok_parse is False else "[?] ",
                              detail))
    if ok_parse is not True:
        return False
    ok_auth, detail = authenticates(path)
    print("  %s auth : %s" % ("[ok]" if ok_auth else "[X] " if ok_auth is False else "[?] ",
                              detail))
    return ok_auth is True


def provision(path=CI_KEY):
    """Mint a dedicated passphrase-less CI key, authorize it, prove it. (ok, path).

    This is the automated answer to "the only key on this PC has a passphrase". It is full
    automation with no console step, and it touches nothing that already works: a new file, one
    appended line in authorized_keys, and the operator's own key left exactly as it was.
    """
    print("\n  minting a DEDICATED CI key (your own key is not read, copied or changed)")
    ok, detail = mint(path)
    print("  %s mint : %s" % ("[ok]" if ok else "[X] ", detail))
    if not ok:
        return False, path
    ok, detail = authorize(path)
    print("  %s authz: %s" % ("[ok]" if ok else "[X] ", detail))
    if not ok:
        return False, path
    print("")
    return check(path), path


def main():
    ap = argparse.ArgumentParser(description="prove the CI deploy key works, then set the secret")
    ap.add_argument("--key", default=None, help="path to the PRIVATE key (default: autodetect)")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--push", action="store_true",
                    help="upload it as the %s secret, but only if every check passed" % SECRET)
    ap.add_argument("--mint", action="store_true",
                    help="create a DEDICATED passphrase-less CI key at %s and authorize it on the "
                         "droplet (your own key is never read, copied or changed)" % CI_KEY)
    a = ap.parse_args()

    print("=" * 74)
    print("  ci_key.py - the GitHub Actions deploy key")
    print("=" * 74)

    if a.mint:
        ok, path = provision(a.key or CI_KEY)
        if not ok:
            return 1
        if a.push:
            ok_push, detail = push(path, a.repo)
            print("  %s %s" % ("[ok]" if ok_push else "[X] ", detail))
            return 0 if ok_push else 1
        return 0

    path = find_key(a.key)
    if not path:
        print("  [X] no private key found. Looked at:")
        for c in CANDIDATES:
            print("        %s" % c)
        print("\n  Generate a passphrase-less deploy key and authorize it on the droplet:")
        print("      python setup_github_cicd.py --no-guardrails")
        return 1

    ok = check(path)
    print("")
    if not ok:
        print("  VERDICT: this key is NOT usable by GitHub Actions. Nothing was uploaded.")
        print("  Fix what is named above, then re-run. The secret is unchanged, so CI keeps")
        print("  failing the same legible way rather than half-working.")
        return 1

    print("  VERDICT: usable. OpenSSH parses it and %s@%s accepts it." % (USER, HOST))
    if not a.push:
        print("")
        print("  The secret itself cannot be read back from GitHub by anyone, so a passing check")
        print("  here does NOT prove the secret matches this file. Upload it to be certain:")
        print("      python ship.py --fix-ci-key")
        return 0

    print("")
    print("  uploading (value on stdin, never argv)...")
    ok_push, detail = push(path, a.repo)
    print("  %s %s" % ("[ok]" if ok_push else "[X] ", detail))
    if not ok_push:
        return 1
    print("")
    print("  Re-run the workflow. The first ssh either says 'reachable' or names its own cause.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
