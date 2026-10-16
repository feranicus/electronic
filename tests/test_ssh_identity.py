"""Which private key does ssh actually get TOLD to offer?

THE STAGING FAILURE, 2026-10-14 to 2026-10-16. Four pipeline runs died on
`***@165.245.244.174: Permission denied (publickey)` while every piece of evidence said the key
was fine - because every check examined the FILE and none examined the INVOCATION.

`recover.py` built its ssh command like this:

    KEY = os.environ.get("DROPLET_KEY", os.path.expanduser("~/.ssh/id_rsa"))
    if os.path.exists(KEY):
        SSH += ["-i", KEY]

Every workflow exports **SSH_KEY**. NOTHING exports DROPLET_KEY. On a runner the default path
does not exist, so `-i` was silently dropped and ssh offered no identity at all. `deploy.py` reads
SSH_KEY, which is why CI could deploy PRODUCTION and never staging - stagegate imports its ssh
command from recover.

Two defect classes, both already in CLAUDE.md:
  * 32 — ONE HOME. "Which key" had two homes and the newer one lost.
  * 37 — a feature behind `if <derived thing>` fails silently by construction.

And the reason it survived so long is class 1: the composite action validated the key with
`ssh-keygen -y`, and the diagnosis printed its fingerprint. Both were true. Both were about a key
ssh was never asked to use.
"""
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys  # noqa: E402

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import recover  # noqa: E402


def _no_default(_p):
    """A runner has no ~/.ssh/id_rsa."""
    return False


def test_the_variable_the_workflows_actually_export_is_honoured():
    """THE BUG, stated as the property. Every workflow sets SSH_KEY; the resolver must use it."""
    key, why = recover.ssh_identity(env={"SSH_KEY": "/home/runner/.ssh/deploy_key"},
                                    exists=_no_default)
    assert key == "/home/runner/.ssh/deploy_key", (key, why)
    assert "SSH_KEY" in why, why


def test_the_legacy_name_still_works_so_nothing_that_set_it_breaks():
    key, why = recover.ssh_identity(env={"DROPLET_KEY": "/legacy/key"}, exists=_no_default)
    assert key == "/legacy/key" and "DROPLET_KEY" in why, (key, why)


def test_ssh_key_wins_when_both_are_set():
    """Precedence has to be decided somewhere; SSH_KEY is what the estate uses today."""
    key, _ = recover.ssh_identity(env={"SSH_KEY": "/new", "DROPLET_KEY": "/old"},
                                  exists=_no_default)
    assert key == "/new", key


def test_no_identity_is_REPORTED_not_silently_assumed():
    """The silent case is the incident. An empty path is fine - ssh may use an agent - but the
    provenance must SAY that nothing was named, so a reader can tell it apart from a key."""
    key, why = recover.ssh_identity(env={}, exists=_no_default)
    assert key == "", key
    assert "none" in why.lower(), why


def test_the_command_really_carries_minus_i(monkeypatch):
    """BEHAVIOUR AND WIRING (class 9). The resolver being right is worth nothing if SSH is still
    assembled from the old variable. Rebuild the module under a runner's environment and read the
    command it produces."""
    import importlib
    monkeypatch.setenv("SSH_KEY", "/home/runner/.ssh/deploy_key")
    monkeypatch.delenv("DROPLET_KEY", raising=False)
    mod = importlib.reload(recover)
    try:
        assert "-i" in mod.SSH, (
            "recover.SSH carries no -i under a runner's environment, so ssh offers no identity - "
            "this is the 2026-10-16 staging failure exactly: %s" % mod.SSH)
        assert mod.SSH[mod.SSH.index("-i") + 1] == "/home/runner/.ssh/deploy_key", mod.SSH
    finally:
        monkeypatch.undo()
        importlib.reload(recover)


def test_every_workflow_that_runs_a_repo_script_names_a_key_the_resolver_READS():
    """DERIVE THE SET, do not hand-list it (class 35). The failure was a name mismatch between
    YAML and Python; the guard has to compare the two sides rather than restate either."""
    import glob
    import re
    wf = glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml"))
    assert wf, "no workflows found; this guard is reading the wrong tree"
    known = set(recover.IDENTITY_ENV)
    offenders = {}
    for path in wf:
        text = open(path, encoding="utf-8", errors="replace").read()
        # SCOPE BY KEY INSTALLATION, not by a python invocation anywhere in the file. The first
        # version grepped for `python <script>.py` and flagged uptime.yml - whose only match is
        # the ADVISORY TEXT of its own alert ("Run: python recover.py --fix-caddy"). That
        # workflow probes from OUTSIDE the droplet deliberately and rightly has no key. Class 4,
        # matching prose. Installing the deploy key is the unambiguous signal, and the pairing
        # it enforces is the real property: if you install a key, NAME it, or nothing offers it.
        installs = ("actions/ssh-key" in text or "deploy_key" in text)
        if not installs:
            continue
        named = set(re.findall(r"^\s*(SSH_KEY|DROPLET_KEY)\s*:", text, re.M))
        if not named & known:
            offenders[os.path.basename(path)] = sorted(named) or ["(none)"]
    assert not offenders, (
        "these workflows run a repo script over ssh but name no identity variable the resolver "
        "reads %s, so `-i` is dropped and ssh offers nothing: %s" % (sorted(known), offenders))


def test_the_old_silent_drop_cannot_come_back():
    """ANCHOR ON THE SOURCE (class 4), because the property is an ABSENCE: there must be no
    branch that decides not to pass -i because a path is missing."""
    import ast
    src = open(os.path.join(ROOT, "recover.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    # the module-level `if` that guards the SSH += ["-i", ...]
    # ast.unparse normalises string quotes to single, so look for -i as a VALUE, not for the
    # double-quoted spelling the source happens to use.
    for node in tree.body:
        if isinstance(node, ast.If) and "'-i'" in ast.unparse(node):
            test = ast.unparse(node.test)
            assert "exists" not in test, (
                "passing -i is gated on the key file existing again. A missing key must be "
                "REPORTED and still offered, so ssh names the file instead of this module "
                "silently offering nothing: if %s" % test)
            break
    else:
        pytest.fail("could not find the branch that adds -i to recover.SSH")
