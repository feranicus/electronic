"""A PACKAGE NAME ON A `RUN` LINE IS A VERSION NOBODY WROTE DOWN, AND A BUILD CACHE WILL FREEZE IT.

THE RUN, 2026-10-22, pipeline #12. The scan gate stopped the promotion:

    scan the artifacts (CRITICAL stops the promotion) (colttechbot)
    certifi (METADATA)  GHSA-6q48-6c7w-9gw2  CRITICAL  installed 2026.7.22  fixed 2026.10.19
    "certifi bundles emSign root CAs with compromised intermediate CA keys"

colt-web, built from the same commit in the same run, held certifi 2026.10.19 and passed. The
difference was not the code and not the base image. assess-bot/Dockerfile installed its
dependencies by NAME:

    RUN pip3 install --no-cache-dir --break-system-packages shodan python-telegram-bot mmh3

and pipeline.yml builds that image with `cache-from: type=gha,scope=bot`. A RUN line that never
changes is a cache key that never changes, so the layer had not re-resolved since the day it was
first built, and a cache hit does not consult PyPI. xlsxwriter in the same scan told the same
story from the other side: 3.2.9 in the bot, 3.3.0 in the web image, one commit, one run.

THE SURROUNDING MECHANISMS ALL POINTED SOMEWHERE ELSE, which is why six weeks passed:

  * `requirements.txt` at the repo root opened with "Dockerfiles install these". No Dockerfile
    installed it. It was the ONLY pip manifest Dependabot watched, so every bump it could have
    offered would have changed nothing that ships. It has been retired.
  * scripts/gen_sbom.py already named hermes-skills/shodan-assessment/requirements.txt as a
    manifest. That file did not exist, so the engine's dependencies were absent from our own SBOM.
  * webapp/backend/requirements.txt argues this exact case at length for starlette and
    python-multipart — "a floor defeats the immutability guarantee" — and the engine's packages
    were simply never held to it, in four Dockerfiles at once (defect class 32: one home).

So the repair is not "bump certifi". It is: every image installs `-r` a committed, pinned
manifest, and nothing installs a bare name. A pin cannot be frozen by a cache, because changing
the pin changes the COPY and the layer with it.

WHAT THIS FILE ASSERTS, and why each one can fail:

  1. No Dockerfile installs a python package by name. (The bug, stated directly.)
  2. Every `-r` a Dockerfile installs resolves to a file that Dockerfile COPIES in, and that file
     is tracked by git. A manifest the build context cannot see fails at build time; a manifest
     that is not committed is not a manifest.
  3. Every pip command's manifests, taken together, pin certifi EXACTLY. certifi is transitive —
     requests pulls it — and it is the one dependency whose entire job is to be current.
  4. .github/dependabot.yml watches exactly the directories of those manifests. DERIVED, not
     listed: a fifth manifest added without a fifth watcher re-creates the original fault
     (defect class 35).
  5. scripts/gen_sbom.py declares exactly those manifests, for the same reason.

Assertions 4 and 5 are what make this self-maintaining rather than a snapshot of today.

The full account, including the six mutations this file was proved against:
docs/decisions/2026-10-image-dependencies.md
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# "MEDDPICC STEP UP" is a different product living in this repo; gen_sbom.py already says a bill
# of materials listing another product's dependencies is wrong, not thorough. Same rule here.
FOREIGN = "meddpicc step up/"

# Dev tooling, allowed by name and ONLY in the gate image. ruff and pytest are not in any shipped
# artifact and no scanner reads them; pinning a linter would make a new rule release able to block
# a ship, which is a different risk from the one this file exists for. The allowlist is asserted
# small below, because an exemption nobody has to justify is just a disabled check.
DEV_TOOLS = {"ruff", "pytest"}
DEV_TOOL_FILE = "Dockerfile.ci"

PIP_FLAGS_WITH_VALUE = {"-r", "--requirement", "-c", "--constraint", "-t", "--target",
                        "--index-url", "-i", "--extra-index-url", "--find-links", "-f",
                        "--python-version", "--platform", "--abi", "--implementation"}


def _tracked(include_new=False):
    """Paths git will carry. With include_new, also the untracked-but-not-ignored ones.

    The gate runs BEFORE `git add -A`, so a manifest added in the same change is on disk and not
    yet in the index; failing it then would mean this guard could never be satisfied by the commit
    that introduces a new image. What it must still catch is a manifest that is GITIGNORED - a
    file the operator's machine can build from and a CI checkout cannot see, which is the shape of
    the jobhuntwow vhost outage (defect class 19)."""
    cmd = ["git", "ls-files", "-z"]
    if include_new:
        cmd += ["--cached", "--others", "--exclude-standard"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=120)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    # -z and split("\0"): tracked paths in this repo contain spaces and .split() shreds them.
    return [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]


def _dockerfiles():
    files = [p for p in _tracked()
             if os.path.basename(p).lower().startswith("dockerfile")
             and not p.lower().startswith(FOREIGN)]
    assert files, "no Dockerfiles found - this guard would pass by measuring nothing (class 1)"
    return files


def _logical_lines(path):
    """Join Dockerfile continuations, so a `RUN a \\\n && b` is read as one command."""
    raw = open(os.path.join(ROOT, path), encoding="utf-8").read()
    out, buf = [], ""
    for line in raw.splitlines():
        if line.lstrip().startswith("#") and not buf:
            continue
        if line.rstrip().endswith("\\"):
            buf += line.rstrip()[:-1] + " "
            continue
        out.append((buf + line).strip())
        buf = ""
    if buf:
        out.append(buf.strip())
    return [ln for ln in out if ln]


def _copies(path):
    """basename of the destination -> source path in the repo, for every COPY of a plain file."""
    got = {}
    for ln in _logical_lines(path):
        m = re.match(r"^COPY\s+(?:--\S+\s+)*(\S+)\s+(\S+)\s*$", ln, re.I)
        if not m:
            continue
        src, dst = m.group(1), m.group(2)
        got[os.path.basename(dst.rstrip("/"))] = src
    return got


def _pip_commands(path):
    """Every `pip install` segment in the file, as (requirement_args, bare_names)."""
    cmds = []
    for ln in _logical_lines(path):
        if not re.match(r"^RUN\b", ln, re.I):
            continue
        for seg in re.split(r"&&|;", ln[3:]):
            toks = seg.split()
            if len(toks) < 2:
                continue
            # the pip binary may be pip or pip3, and `install` must be the verb that follows it
            try:
                i = next(k for k, t in enumerate(toks)
                         if os.path.basename(t) in ("pip", "pip3") and k + 1 < len(toks)
                         and toks[k + 1] == "install")
            except StopIteration:
                continue
            reqs, bare, k = [], [], i + 2
            while k < len(toks):
                t = toks[k]
                if t in PIP_FLAGS_WITH_VALUE:
                    if t in ("-r", "--requirement") and k + 1 < len(toks):
                        reqs.append(toks[k + 1])
                    k += 2
                    continue
                if t.startswith("-"):
                    k += 1
                    continue
                bare.append(t.strip('"\''))
                k += 1
            cmds.append((reqs, bare))
    return cmds


def _manifests():
    """Repo-relative paths of every requirements file a Dockerfile installs. DERIVED."""
    found = set()
    for df in _dockerfiles():
        cp = _copies(df)
        for reqs, _ in _pip_commands(df):
            for r in reqs:
                src = cp.get(os.path.basename(r))
                if src:
                    found.add(src)
    return found


# --------------------------------------------------------------------------- 1. the bug itself

def test_no_dockerfile_installs_a_python_package_by_name():
    offenders = []
    for df in _dockerfiles():
        for _, bare in _pip_commands(df):
            for name in bare:
                if df == DEV_TOOL_FILE and name.lower() in DEV_TOOLS:
                    continue
                offenders.append("%s: %s" % (df, name))
    assert not offenders, (
        "a package installed by name re-resolves only when its RUN line changes, and the GHA "
        "layer cache keeps that from ever happening - this is the 2026-10-22 certifi finding:\n  "
        + "\n  ".join(offenders))


def test_the_dev_tool_exemption_stays_small_and_stays_in_the_gate_image():
    assert DEV_TOOLS == {"ruff", "pytest"}, (
        "the by-name exemption grew; every addition needs a written reason here, or the check "
        "above degrades into a rubber stamp")
    assert DEV_TOOL_FILE == "Dockerfile.ci", DEV_TOOL_FILE
    shipped = [df for df in _dockerfiles() if df != DEV_TOOL_FILE]
    assert shipped, "every Dockerfile is exempt, so nothing is checked"


# --------------------------------------------------------- 2. a manifest the build can't see

def test_every_requirement_file_is_copied_in_and_tracked_by_git():
    tracked = set(_tracked(include_new=True))
    problems = []
    for df in _dockerfiles():
        cp = _copies(df)
        for reqs, _ in _pip_commands(df):
            for r in reqs:
                src = cp.get(os.path.basename(r))
                if src is None:
                    problems.append("%s installs -r %s but COPIES no such file" % (df, r))
                elif src.replace("\\", "/") not in tracked:
                    problems.append("%s installs -r %s from %s, which git does not track"
                                    % (df, r, src))
    assert not problems, (
        "a manifest the build context cannot see fails at build time, and one git will not carry "
        "can only be built from the machine that happens to hold it:\n  " + "\n  ".join(problems))


# ------------------------------------------------------------------- 3. the trust store itself

def _pins_certifi(rel):
    body = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if re.match(r"^certifi\s*==\s*[0-9]", line):
            return True
    return False


def test_every_image_pins_certifi_exactly():
    """requests pulls certifi transitively, so no manifest NAMES it unless someone decides to.
    Nobody had, and the version that shipped was whatever the frozen layer happened to hold."""
    problems = []
    for df in _dockerfiles():
        cp = _copies(df)
        for reqs, _ in _pip_commands(df):
            if not reqs:
                continue
            srcs = [cp[os.path.basename(r)] for r in reqs if os.path.basename(r) in cp]
            if not any(_pins_certifi(s) for s in srcs):
                problems.append("%s: pip install -r %s pins no exact certifi"
                                % (df, " -r ".join(reqs)))
    assert not problems, (
        "certifi is a trust store whose whole purpose is to be current; left transitive it is "
        "resolved by accident and then frozen:\n  " + "\n  ".join(problems))


# ------------------------------------------------ 4+5. the watchers must follow the manifests

def test_dependabot_watches_exactly_the_manifests_the_images_install():
    yaml = pytest.importorskip("yaml")
    cfg = yaml.safe_load(open(os.path.join(ROOT, ".github", "dependabot.yml"), encoding="utf-8"))
    pip = [u for u in cfg["updates"] if u["package-ecosystem"] == "pip"]
    assert len(pip) == 1, "expected one pip entry, found %d" % len(pip)
    watched = set()
    for d in pip[0].get("directories", []) or [pip[0].get("directory")]:
        watched.add(d.strip("/"))
    wanted = {os.path.dirname(m).replace("\\", "/") for m in _manifests()}
    assert watched == wanted, (
        "Dependabot and the images disagree about where the dependencies live. Watching a file "
        "nothing installs is what let certifi sit six weeks past its fix.\n"
        "  watched: %s\n  installed by an image: %s" % (sorted(watched), sorted(wanted)))


def test_the_sbom_declares_exactly_those_manifests():
    import scripts.gen_sbom as sbom
    declared = {m.replace("\\", "/") for m in sbom.PY_MANIFESTS}
    wanted = {m.replace("\\", "/") for m in _manifests()}
    assert declared == wanted, (
        "the SBOM describes a different dependency set than the images install. It previously "
        "named a root manifest nothing read AND an engine manifest that did not exist, so the "
        "engine's packages were missing from our own bill of materials.\n"
        "  declared: %s\n  installed: %s" % (sorted(declared), sorted(wanted)))


def test_the_retired_root_manifest_has_not_come_back():
    """It claimed 'Dockerfiles install these' and no Dockerfile did. If it returns it must return
    as something an image actually installs, which the assertions above would then require."""
    assert "requirements.txt" not in set(_tracked()), (
        "a root requirements.txt is tracked again; either an image installs it (and the watchers "
        "above must name it) or it is a fourth home for names nobody ships")
