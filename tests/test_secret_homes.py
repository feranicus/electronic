"""test_secret_homes.py — A CREDENTIAL HAS AS MANY HOMES AS SOMEBODY GAVE IT, AND THE WRITER KNEW
ONE.

THE INCIDENT (22 Nov 2026). DigitalOcean deprecated `deepseek-3.2`; the operator minted a new model
access key, granted it the successor, and installed it with `python set_secret.py OPENAI_API_KEY`.
The command succeeded — it printed `verify: OPENAI_API_KEY = set, 71 chars` — and
`deepseek-v4.1-flash` still answered **HTTP 403**. The 403 was read as a model-id problem for an
afternoon, because an entitlement error and a stale credential produce the identical line.

MEASURED on the checkout, which is where the answer was the whole time:

    assess-bot/.env      OPENAI_API_KEY / DO_INFERENCE_KEY   sha256 b4bb02748df6   (new)
    cassandra-bot/.env   OPENAI_API_KEY                      sha256 9327f18662ac   (July)

`cassandra-bot` loads `env_file: cassandra-bot/.env` in all three compose files and reads the same
`OPENAI_API_KEY`. `set_secret.py` wrote one file and recreated one container, so:

  * cassandra-bot had been calling the inference API on a credential three rotations old, and
  * `deploy.py::BOTS_SECRETS` packs BOTH files, so every `--reuse` deploy re-shipped the stale one.

Two defects, two repairs, both asserted here:

  1. THE FILES. The write set is DERIVED by reading the files (class 35) and the file list comes
     from `deploy.BOTS_SECRETS` (class 32 — one home for "what gets shipped"). Files that do not
     hold the credential are NAMED, never silently written: an env file with no inference key
     points at a service nobody configured, a different fault with a different repair.
  2. THE CONTAINERS. A container's environment is baked at CREATION. `docker restart` re-executes
     the process with the OLD environment, so a merely-restarted consumer keeps the stale
     credential and then returns a perfectly accurate 403. Every consumer is RECREATED, derived
     from compose's own labels and filtered to project `colt-stack` so the other stacks sharing
     this host are untouched (operating principle 4).

The shell half is SIMULATED, not skipped (class 20): a fake `/opt/colt-stack` tree and a fake
`docker` on PATH. There is no droplet in CI and none on the operator's Windows box, and "skip it
everywhere" is how the single-file write survived four key rotations.
"""
import importlib.util
import io
import os
import re
import stat
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_teamwork import shell_harness_allowed            # ONE HOME for "may this box run sh"


def _mod():
    spec = importlib.util.spec_from_file_location("set_secret",
                                                  os.path.join(ROOT, "set_secret.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --------------------------------------------------------------------------------------------
# The Python half: which files does it consider, and does it refuse to answer blindly?
# --------------------------------------------------------------------------------------------

def test_the_file_list_comes_from_deploy_not_from_a_copy():
    """ONE HOME (class 32). `deploy.BOTS_SECRETS` decides what is shipped to the droplet; a second
    copy of that list inside set_secret.py is precisely how cassandra-bot/.env fell outside this
    script's world."""
    m = _mod()
    got = {os.path.basename(os.path.dirname(p)) for p in m.local_env_files()}
    deploy = io.open(os.path.join(ROOT, "deploy.py"), encoding="utf-8").read()
    line = [l for l in deploy.split("\n") if l.startswith("BOTS_SECRETS")][0]
    want = {p.strip().strip("\"'").split("/")[0]
            for p in line.split("[", 1)[1].rsplit("]", 1)[0].split(",") if p.strip()}
    assert got == want, (
        "set_secret.py considers %s but deploy.py ships %s - the difference is a file that gets "
        "a stale credential re-shipped on the next --reuse deploy" % (sorted(got), sorted(want)))
    assert len(want) > 1, (
        "deploy.py now ships one env file, so this whole class is gone - delete the derivation "
        "rather than leaving a guard that cannot fail (class 3)")


def test_set_secret_does_not_hardcode_the_stack_root_twice():
    """A value with two homes drifts, and the second literal also made the shell half untestable
    off the droplet."""
    src = io.open(os.path.join(ROOT, "set_secret.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.split("\n")
                     if not l.lstrip().startswith("#") and not l.lstrip().startswith("//"))
    hits = re.findall(r"/opt/colt-stack", code)
    assert len(hits) == 1, (
        "/opt/colt-stack appears %d times in code; it has one home (ENVF) and the shell derives "
        "the root from it" % len(hits))


def test_a_split_credential_is_reported_as_split(tmp_path, monkeypatch):
    """THE WHOLE POINT. Two homes holding two values is the fault that shipped, and `--audit` must
    name it rather than printing a cheerful per-file 'set, 71 chars'."""
    m = _mod()
    a, c = tmp_path / "assess-bot" / ".env", tmp_path / "cassandra-bot" / ".env"
    for p, v in ((a, "NEWKEY"), (c, "OLDKEY")):
        p.parent.mkdir(parents=True)
        p.write_text("OPENAI_API_KEY=%s\nOTHER=x\n" % v, encoding="utf-8")
    monkeypatch.setattr(m, "local_env_files", lambda: [str(a), str(c)])
    rows = m.key_homes()
    assert len({r[2] for r in rows}) == 2, rows
    assert m.audit() == 1, "a split credential exited 0 - the operator is told nothing is wrong"


def test_agreeing_homes_are_not_reported_as_a_fault(tmp_path, monkeypatch):
    """A warning that fires on every run trains the operator to read past the one that matters."""
    m = _mod()
    a, c = tmp_path / "assess-bot" / ".env", tmp_path / "cassandra-bot" / ".env"
    for p in (a, c):
        p.parent.mkdir(parents=True)
        p.write_text("OPENAI_API_KEY=SAME\n", encoding="utf-8")
    monkeypatch.setattr(m, "local_env_files", lambda: [str(a), str(c)])
    assert m.audit() == 0


def test_no_key_anywhere_is_a_finding_not_a_pass(tmp_path, monkeypatch):
    """A check that cannot see its subject must not report health (class 1)."""
    m = _mod()
    p = tmp_path / "assess-bot" / ".env"
    p.parent.mkdir(parents=True)
    p.write_text("SOMETHING_ELSE=1\n", encoding="utf-8")
    monkeypatch.setattr(m, "local_env_files", lambda: [str(p)])
    assert m.audit() == 1


def test_the_audit_never_prints_key_material(tmp_path, monkeypatch, capsys):
    """This repository is PUBLIC, and an audit output is the thing people paste into a chat."""
    m = _mod()
    p = tmp_path / "assess-bot" / ".env"
    p.parent.mkdir(parents=True)
    p.write_text("OPENAI_API_KEY=doo_v1_SUPERSECRETVALUE\n", encoding="utf-8")
    monkeypatch.setattr(m, "local_env_files", lambda: [str(p)])
    m.audit()
    out = capsys.readouterr().out
    assert "SUPERSECRETVALUE" not in out and "doo_v1" not in out, out


def test_a_write_reaches_every_local_home_that_holds_the_credential(tmp_path, monkeypatch):
    """`deploy.py --reuse` packs these files, so one left behind re-ships the old key."""
    m = _mod()
    a, c, o = (tmp_path / "assess-bot" / ".env", tmp_path / "cassandra-bot" / ".env",
               tmp_path / "obs" / ".env")
    for p, body in ((a, "OPENAI_API_KEY=OLD\n"), (c, "OPENAI_API_KEY=ANCIENT\nX=1\n"),
                    (o, "GRAFANA_PASSWORD=p\n")):
        p.parent.mkdir(parents=True)
        p.write_text(body, encoding="utf-8")
    monkeypatch.setattr(m, "local_env_files", lambda: [str(a), str(c), str(o)])
    monkeypatch.setattr(m, "LOCAL", str(a))
    assert m.upsert_local("OPENAI_API_KEY", "NEW", m.TWINS) is True
    assert "OPENAI_API_KEY=NEW" in a.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=NEW" in c.read_text(encoding="utf-8"), (
        "cassandra-bot/.env was skipped, which is the defect verbatim")
    assert "ANCIENT" not in c.read_text(encoding="utf-8")
    assert "X=1" in c.read_text(encoding="utf-8"), "the rest of the file was destroyed"
    assert "OPENAI_API_KEY" not in o.read_text(encoding="utf-8"), (
        "a file that never held the inference key was written to - that hides an unconfigured "
        "service instead of naming it")


# --------------------------------------------------------------------------------------------
# The shell half, against a simulated droplet.
# --------------------------------------------------------------------------------------------

FAKE_DOCKER = r'''#!/bin/sh
# A fake `docker` that answers only what the script asks, and RECORDS every call so the test can
# assert the script consulted it (class 12: prove the fixture reproduces the condition).
#
# IT REPRODUCES THE REAL ESTATE'S SHAPE: colt-web comes from docker-compose.web.yml, while
# colt-assessbot comes from docker-compose.ghcr.yml (which PULLS the scanned image) - and the host
# also carries docker-compose.reuse.yml, which defines the SAME bot service but BUILDS it locally.
# That overlap is the whole point: a recreate loop that walks compose FILES applies both and the
# last one wins, swapping the scanned artifact for an unscanned one.
echo "$@" >> "$DOCKER_LOG"
case "$1 $2" in
  "ps -q")
      echo c1; echo c2 ;;
  "ps --format")
      echo colt-web; echo colt-assessbot ;;
  "inspect -f")
      case "$3" in
        *Config.Image*) echo "ghcr.io/feranicus/electronic/colt-web:t1" ;;
        *)
          # service|config_files, per container, exactly as compose labels them
          case "$4" in
            c1) if [ -n "$SIM_GONE" ]; then
                  # the retired web-deploy path: a container naming a file no longer on disk
                  echo "colt-web|$STACK/docker-compose.web.yml,$STACK/docker-compose.gone.yml"
                else
                  echo "colt-web|$STACK/docker-compose.web.yml"
                fi ;;
            *)  echo "colt-assessbot|$STACK/docker-compose.ghcr.yml" ;;
          esac ;;
      esac ;;
  "compose -p")
      exit 0 ;;
  "exec -i")
      echo "   OPENAI_API_KEY   set, 3 chars, sha256 deadbeefcafe" ; exit 0 ;;
  "exec "*)
      exit 0 ;;
esac
exit 0
'''


@pytest.fixture
def droplet(tmp_path):
    ok, why = shell_harness_allowed()
    if not ok:
        pytest.skip(why)
    stack = tmp_path / "opt" / "colt-stack"
    for d, body in (("assess-bot", "OPENAI_API_KEY=OLD\nDO_INFERENCE_KEY=OLD\nCOLT_BOT_PASSWORD=p\n"),
                    ("cassandra-bot", "OPENAI_API_KEY=ANCIENT\nTELEGRAM_TOKEN=t\n"),
                    ("obs", "GRAFANA_PASSWORD=g\n")):
        (stack / d).mkdir(parents=True)
        (stack / d / ".env").write_text(body, encoding="utf-8")
    for cf in ("docker-compose.web.yml", "docker-compose.ghcr.yml", "docker-compose.reuse.yml"):
        (stack / cf).write_text("services: {}\n", encoding="utf-8")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    dk = bin_ / "docker"
    dk.write_text(FAKE_DOCKER, encoding="utf-8")
    dk.chmod(dk.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return stack, bin_, tmp_path / "docker.log"


def _run_remote(droplet, name="OPENAI_API_KEY", family="DO_INFERENCE_KEY|OPENAI_API_KEY",
                value="NEWVALUE", sim_gone=""):
    stack, bin_, log = droplet
    m = _mod()
    script = droplet[2].parent / "remote.sh"
    script.write_text(m.REMOTE, encoding="utf-8", newline="")
    import base64
    fp = base64.b64encode(m.FINGERPRINT.encode()).decode()
    env = dict(os.environ)
    env["PATH"] = str(bin_) + os.pathsep + env["PATH"]
    env["DOCKER_LOG"] = str(log)
    env["STACK"] = str(stack)
    env["SIM_GONE"] = sim_gone
    r = subprocess.run(["bash", str(script), name, family,
                        str(stack / "assess-bot" / ".env"), fp],
                       input=value.encode(), capture_output=True, env=env, timeout=90)
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    return r.returncode, out, (log.read_text() if log.exists() else "")


def test_the_remote_writes_both_homes_and_names_the_third(droplet):
    stack = droplet[0]
    rc, out, _log = _run_remote(droplet)
    assert rc == 0, out
    assert "OPENAI_API_KEY=NEWVALUE" in (stack / "assess-bot" / ".env").read_text()
    assert "OPENAI_API_KEY=NEWVALUE" in (stack / "cassandra-bot" / ".env").read_text(), (
        "the second home was skipped on the droplet too - the defect verbatim:\n" + out)
    assert "TELEGRAM_TOKEN=t" in (stack / "cassandra-bot" / ".env").read_text(), (
        "the rest of cassandra-bot/.env was destroyed")
    obs = (stack / "obs" / ".env").read_text()
    assert "OPENAI_API_KEY" not in obs
    assert "skipped" in out and "obs" in out, (
        "the file it did NOT write was not named, so an unconfigured service stays invisible "
        "(class 37):\n" + out)


def test_the_remote_recreates_rather_than_restarts(droplet):
    """ENV IS BAKED AT CREATION. `docker restart` would leave every consumer on the old
    credential while reporting success - which is the fault being repaired."""
    rc, out, log = _run_remote(droplet)
    assert rc == 0, out
    assert "--force-recreate" in log, (
        "no container was recreated, so they all still hold the old value:\n" + log)
    assert not re.search(r"(?m)^restart\b", log), (
        "`docker restart` re-executes with the OLD environment:\n" + log)


def test_the_recreate_set_is_label_derived_and_confined_to_colt_stack(droplet):
    """Amnezia VPN, VideoDead and joplin share this host. The project filter is what keeps them
    out, and the label is what makes the set derived rather than typed (classes 35 and 4)."""
    rc, out, log = _run_remote(droplet)
    assert rc == 0, out
    # ANCHOR ON THE SELECTION CALL (class 4). Asserting the filter appears ANYWHERE in the log is
    # what a removed filter survived first time round: the later verification pass lists containers
    # with the same filter, so its line kept the assertion green while the recreate set had gone
    # host-wide. The call that CHOOSES what to recreate is `ps -q`; that is the one to read.
    picks = [l for l in log.split("\n") if l.startswith("ps -q")]
    assert picks, "nothing selected containers for recreation at all:\n" + log
    for line in picks:
        assert "label=com.docker.compose.project=colt-stack" in line, (
            "the recreate set was chosen without the project filter, so Amnezia VPN, VideoDead and "
            "joplin are in it: %r" % line)
    assert "com.docker.compose.project.config_files" in log, (
        "the compose file was not read from the container's own labels")


def test_a_compose_file_absent_from_disk_is_named_not_fatal(droplet):
    """The retired web-deploy path left containers naming a file that no longer exists. A `set -e`
    abort there would leave half the stack on the old credential with no report."""
    rc, out, _log = _run_remote(droplet, sim_gone="1")
    assert rc == 0, out
    assert "docker-compose.gone.yml" in out and "absent from disk" in out, out
    assert "still hold the OLD value" in out, (
        "it skipped them silently - an unrecreated consumer that nobody is told about is the "
        "stale credential all over again (class 37):\n" + out)


def test_each_service_is_recreated_from_its_own_definition_only(droplet):
    """ONE ARTIFACT. docker-compose.ghcr.yml PULLS the image CI built and scanned;
    docker-compose.reuse.yml BUILDS the same services locally. The first version of this script
    looped over compose FILES and ran a bare `up -d` on each, so the bots were recreated from
    ghcr.yml and then again from reuse.yml - last one wins, and the only internet-facing artifact
    stopped being the scanned one. MEASURED on production: the next run showed ghcr.yml no longer
    claimed by any container.

    The repair is to rebuild each container's OWN compose invocation from its labels and name only
    that service."""
    rc, out, log = _run_remote(droplet)
    assert rc == 0, out
    ups = [l for l in log.split("\n") if l.startswith("compose -p") and " up " in l]
    assert ups, "nothing was recreated at all:\n" + log
    for line in ups:
        assert line.rstrip().split()[-1] in ("colt-web", "colt-assessbot"), (
            "a recreate named no service, so compose applied the whole file and whichever "
            "definition came last won: %r" % line)
    # reuse.yml is on disk and defines the same bot service. No container reports it, so it must
    # never be applied - that is the difference between provenance kept and provenance guessed.
    assert not any("reuse.yml" in l for l in ups), (
        "a compose file no running container was created from was applied anyway:\n"
        + "\n".join(ups))
    assert any("ghcr.yml" in l and l.rstrip().endswith("colt-assessbot") for l in ups), (
        "the bot was not recreated from the ghcr definition it actually came from:\n"
        + "\n".join(ups))


def test_the_image_each_container_runs_is_printed(droplet):
    """Recreating a container is the moment its image can change, and an unprinted change is one
    nobody can catch. A ghcr.io ref is the artifact CI scanned; a bare local tag is not."""
    rc, out, _log = _run_remote(droplet)
    assert rc == 0, out
    assert "image ghcr.io/" in out, (
        "no provenance was reported, so a swapped artifact would look identical to a correct "
        "run:\n" + out)


def test_it_verifies_per_container_and_prints_no_key_material(droplet):
    rc, out, log = _run_remote(droplet, value="doo_v1_SUPERSECRET")
    assert rc == 0, out
    assert "exec" in log, "no container was asked what it holds"
    assert "sha256" in out, out
    assert "SUPERSECRET" not in out, "the key reached stdout; this repository is public"


def test_the_fingerprint_probe_reports_a_missing_name_as_missing():
    """The probe runs inside a container whose env may not hold the name at all. 'MISSING' and a
    fingerprint are different answers with different repairs; a probe that printed a fingerprint of
    the empty string would read as healthy."""
    m = _mod()
    r = subprocess.run([sys.executable, "-c", m.FINGERPRINT, "NO_SUCH_NAME_HERE", "ct"],
                       capture_output=True, text=True, timeout=60)
    assert "MISSING" in r.stdout, r.stdout + r.stderr
    r2 = subprocess.run([sys.executable, "-c", m.FINGERPRINT, "PATH", "ct"],
                        capture_output=True, text=True, timeout=60)
    assert "sha256" in r2.stdout and "MISSING" not in r2.stdout, r2.stdout + r2.stderr


def test_the_remote_script_has_no_percent_formatting_hazard():
    """It used to be built with `% ENVF`, so every literal `%` had to be `%%` - a precondition
    invisible at the point of editing (class 44). Everything variable is an argument now."""
    src = io.open(os.path.join(ROOT, "set_secret.py"), encoding="utf-8").read()
    m = re.search(r"REMOTE = r'''(.*?)'''(\s*)", src, re.S)
    assert m, "the remote payload moved"
    assert not m.group(2).strip().startswith("%"), (
        "REMOTE is %-formatted again; every literal %% in shell must then be doubled")
    assert "%%" not in m.group(1), (
        "a doubled %% survives in a block that is no longer %-formatted, so the shell now sees it")
