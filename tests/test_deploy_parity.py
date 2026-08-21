#!/usr/bin/env python3
"""Both deploy paths must ship the SAME bytes, and the verify must show what it compared.

THE DEFECT, from the 2026-08-20 ship log. One `python ship.py`, one commit, and the two containers
it deployed ended up with DIFFERENT engine files:

    scripts/proteus.py        colt-web fbed443dfcea   colt-assessbot 26ab2bf3a805
    scripts/creed.js          colt-web 472e6a8c7985   colt-assessbot 73c14617e33c
    scripts/pptx_preview.py   colt-web 0b111a71374d   colt-assessbot MISSING

and the run printed, directly underneath that list, `OK colt-assessbot engine matches the repo`.

TWO CAUSES, and they are independent:

1. THE TWO PATHS PACKED DIFFERENTLY. deploy_web_direct.py packs `git archive HEAD` with
   core.autocrlf=false (repository bytes, immutable). deploy.py tar'd the operator's WORKING COPY —
   so on Windows the same commit hashes differently through the two paths, and any uncommitted edit
   shipped to the bots only. "staging and prod get identical bytes" was true of the web app and
   false of the bots, which is precisely what the engine-hash verify exists to detect.

2. THE VERIFY PRINTED A RAW DUMP AND A SEPARATE VERDICT. The human read the probe's nineteen lines
   of output; the OK was computed elsewhere. When the two disagree the operator has no way to tell,
   which is how a MISSING came to sit above an OK. So the printout must BE the comparison.

The secrets split is deliberate and is asserted here too: code comes from the commit, `assess-bot
/.env` is gitignored by design and is added on top from the operator's machine. Packing only the
commit would have silently stopped shipping it — a behaviour change smuggled in as a side effect.
"""
import hashlib
import importlib.util
import os
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    try:
        spec.loader.exec_module(m)
    except SystemExit:                      # these modules parse argv at import
        pass
    return m


def _members(path):
    with tarfile.open(path) as t:
        return {n.lstrip("./"): n for n in t.getnames()}


def _sha_in(path, rel):
    with tarfile.open(path) as t:
        for cand in (rel, "./" + rel):
            try:
                return hashlib.sha256(t.extractfile(cand).read()).hexdigest()
            except KeyError:
                continue
    return None


ENGINE = "hermes-skills/shodan-assessment/scripts/"
# The three files that actually diverged in production, plus one that did not — a test that only
# contains the broken cases cannot show the fix is narrow.
WATCH = [ENGINE + f for f in ("proteus.py", "creed.js", "pptx_preview.py", "shodan_recon.py")]


def test_both_deploy_paths_ship_identical_engine_bytes():
    dwd = _load("dwd_parity", "deploy_web_direct.py")
    dep = _load("dep_parity", "deploy.py")
    web = dwd.pack()
    bots = dwd.pack(include=dep.BOTS_INCLUDE)
    diff = [f for f in WATCH if _sha_in(web, f) != _sha_in(bots, f)]
    assert not diff, (
        "the web and bots packs disagree on %s.\n"
        "Both must come from `git archive HEAD` with core.autocrlf=false. A tar of the working "
        "tree emits CRLF on Windows and includes uncommitted edits, so the two containers end up "
        "running different bytes of the same commit." % ", ".join(diff))


def test_the_bots_pack_contains_everything_the_bots_build_from():
    dwd = _load("dwd_need", "deploy_web_direct.py")
    dep = _load("dep_need", "deploy.py")
    got = _members(dwd.pack(include=dep.BOTS_INCLUDE))
    # docker-compose.reuse.yml builds with `context: .` and these Dockerfiles; promtail bind-mounts
    # obs/. The WEB include set contains none of them, which is why the file list cannot be shared.
    need = ["docker-compose.reuse.yml", "assess-bot/Dockerfile", "assess-bot/bot.py",
            "cassandra-bot/Dockerfile", "colt_auth.py", "user_store.py",
            ENGINE + "pptx_preview.py"]
    missing = [f for f in need if f not in got]
    assert not missing, "the bots pack is missing %s - the image would not build" % missing


def test_the_web_pack_is_not_silently_widened_to_the_bots_tree():
    """The two scopes must stay DIFFERENT. Sharing one list is the other way to get this wrong."""
    dwd = _load("dwd_scope", "deploy_web_direct.py")
    got = _members(dwd.pack())
    assert "assess-bot/Dockerfile" not in got, \
        "the web pack now carries the bots tree; the scopes were merged, not shared"


def test_untracked_secrets_still_ship_with_the_bots():
    """`assess-bot/.env` is gitignored, so `git archive` can never contain it.

    Packing only the commit would stop shipping the runtime secrets the bots compose declares in
    `env_file:` — a behaviour change arriving as a side effect of a determinism fix.
    """
    dwd = _load("dwd_secret", "deploy_web_direct.py")
    dep = _load("dep_secret", "deploy.py")
    assert "assess-bot/.env" in dep.BOTS_SECRETS, \
        "the bots deploy no longer carries the runtime env file"
    marker = os.path.join(HERE, "assess-bot", ".env")
    made = False
    if not os.path.exists(marker):
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        open(marker, "w").write("PARITY_TEST=1\n")
        made = True
    try:
        got = _members(dwd.pack(include=dep.BOTS_INCLUDE, extra=dep.BOTS_SECRETS))
        assert "assess-bot/.env" in got, \
            "an untracked secret named in BOTS_SECRETS did not reach the pack"
    finally:
        if made:
            os.unlink(marker)               # never leave a fake secret behind


def test_git_archive_is_used_and_line_endings_are_forced():
    # STRIP COMMENTS FIRST. The first version of this assertion grepped the raw file, and the
    # paragraph above the flags EXPLAINS core.autocrlf=false — so deleting the actual arguments left
    # the comment behind and the check passed against a file carrying the exact defect. That is the
    # fourth time this repo has been bitten by a check matching its own explanation.
    src = open(os.path.join(HERE, "deploy_web_direct.py"), encoding="utf-8").read()
    code = "\n".join(ln.split("#")[0] for ln in src.splitlines())
    assert "core.autocrlf=false" in code and "core.eol=lf" in code, (
        "git archive applies the same end-of-line conversion as a checkout; without both flags the "
        "artifact is platform-dependent and the two paths cannot agree")
    dep = open(os.path.join(HERE, "deploy.py"), encoding="utf-8").read()
    body = dep[dep.index("def package("):].split("\ndef ")[0]
    assert "_dwd.pack(" in body, \
        "deploy.py no longer packs through the shared commit-pack; it will drift again"


def test_the_verify_prints_the_comparison_it_made():
    """A raw remote dump plus a separately computed verdict is how MISSING sat above OK."""
    ship = _load("ship_cmp", "ship.py")
    assert hasattr(ship, "print_engine_comparison"), \
        "nothing renders the per-file comparison; the operator reads output the verdict did not use"
    src = open(os.path.join(HERE, "ship.py"), encoding="utf-8").read()
    # the probe must be QUIET: whatever is printed has to be the compared numbers
    probe = src[src.index("def _sha_all_in_container("):].split("\ndef ")[0]
    assert "echo=False" in probe, \
        "the raw probe output is still echoed; a MISSING can appear above an OK again"
    for name in ("colt-web", "colt-assessbot"):
        assert 'print_engine_comparison("%s")' % name in src, \
            "%s reports a verdict without showing the comparison" % name


def test_a_missing_file_can_never_be_reported_as_matching():
    """Run the real gate over the EXACT probe output from the 2026-08-20 log."""
    ship = _load("ship_gate", "ship.py")
    real = "\n".join([
        ship.ENGINE_FILES[0] + " " + "0" * 64,                 # a plausible hash, wrong
        "scripts/pptx_preview.py MISSING",
    ])
    ship.ssh = lambda *a, **k: real
    ship._SHA_CACHE.clear()
    ok, stale = ship.engine_is_current("colt-assessbot", fresh=True)
    assert not ok, "a container missing an engine file was reported as matching the repo"
    assert any("pptx_preview" in s for s in stale), \
        "the missing file is not named in the failure, so nobody can act on it"


def test_a_file_absent_from_the_repo_is_not_silently_skipped():
    """The gate used to `continue` when the local file was gone, shrinking itself in silence."""
    ship = _load("ship_skip", "ship.py")
    ship.ssh = lambda *a, **k: ""
    ship._SHA_CACHE.clear()
    original = list(ship.ENGINE_FILES)
    ship.ENGINE_FILES.append("scripts/this_file_does_not_exist.py")
    try:
        ok, stale = ship.engine_is_current("colt-web", fresh=True)
        assert not ok
        assert any("NOT IN THE REPO" in s for s in stale), \
            "a gate entry with no local file passed unnoticed - the check shrank and said nothing"
    finally:
        ship.ENGINE_FILES[:] = original


def test_an_empty_probe_is_not_a_pass():
    """ssh throttling returns nothing; that is 'I could not look', never 'it matches'."""
    ship = _load("ship_empty", "ship.py")
    ship.ssh = lambda *a, **k: ""
    ship._SHA_CACHE.clear()
    ok, stale = ship.engine_is_current("colt-web", fresh=True)
    assert not ok and any("returned NOTHING" in s for s in stale), \
        "an unanswered probe was treated as evidence about the container"


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
