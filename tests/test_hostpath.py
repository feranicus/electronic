"""The container-to-host path resolution has ONE implementation, and finding nothing is not success.

THE INCIDENT (2026-08-27). The ship log printed, one line apart:

    --- DATABASES ---
    /var/lib/docker/volumes/colt-stack_colt_events/_data/cost_ledger.sqlite   53248 bytes
    ...
    #### FIRST SHIP
    [i] no events log at /var/log/colt/events.log yet - nothing to ship

dbbackup found a file on the colt_events volume by asking the container for its mount table.
logship, looking for a file on THE SAME VOLUME, used the path inside the container, found nothing,
and exited 0. The off-box security archive - the copy that exists because an attacker who owns the
droplet owns Loki - had been empty since installation and reported success every hour.

dbbackup made the identical mistake on 2026-08-14 and was fixed. The fix lived inside dbbackup's
agent, where logship could not reach it, so it was made again thirteen days later. That is the
"two homes for one decision" defect this repository has paid for more than any other.

These tests pin the three properties that stop it recurring:
  * exactly one implementation exists, and the agents import it rather than carrying copies;
  * both installers actually SHIP it (an import with no fallback fails hard if they do not);
  * "I cannot find it" and "there is nothing to find" are distinguishable, and the first one fails.
"""
import importlib.util
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(ROOT, "deploy")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def logship():
    return _load(os.path.join(DEPLOY, "logship", "agent.py"), "logship_agent")


@pytest.fixture(scope="module")
def dbbackup():
    return _load(os.path.join(DEPLOY, "dbbackup", "agent.py"), "dbbackup_agent")


def _strip_comments(src):
    """Comments legitimately DISCUSS the removed implementation. Grepping raw source would
    false-positive on the paragraph explaining why it was removed - which this repo has done
    four separate times."""
    out = []
    for ln in src.splitlines():
        s = ln.split("#", 1)[0]
        out.append(s)
    return "\n".join(out)


def _py_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in ("node_modules", ".git", "__pycache__", "dist", "venv", ".venv")]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(base, f)


# --------------------------------------------------------------------------------------------
# ONE IMPLEMENTATION
# --------------------------------------------------------------------------------------------

def test_volume_path_is_defined_exactly_once_in_the_repo():
    hits = []
    for p in _py_files():
        src = _strip_comments(open(p, encoding="utf-8", errors="replace").read())
        if re.search(r"^def volume_path\(", src, re.M):
            hits.append(os.path.relpath(p, ROOT))
    assert hits == [os.path.join("deploy", "hostpath.py")], (
        "volume_path must exist once, in deploy/hostpath.py. Found: %s. A second copy is the "
        "defect that made logship repeat dbbackup's bug." % hits)


def test_container_running_is_defined_exactly_once_in_the_repo():
    hits = []
    for p in _py_files():
        src = _strip_comments(open(p, encoding="utf-8", errors="replace").read())
        if re.search(r"^def container_running\(", src, re.M):
            hits.append(os.path.relpath(p, ROOT))
    assert hits == [os.path.join("deploy", "hostpath.py")], hits


def test_both_agents_import_the_shared_module_and_keep_no_local_fallback(logship, dbbackup):
    for mod in (logship, dbbackup):
        assert mod.volume_path.__module__ == "hostpath", (
            "%s is not using the shared implementation" % mod.__name__)
        assert mod.container_running.__module__ == "hostpath"


def test_neither_agent_still_treats_the_container_path_as_a_host_path(logship):
    """The literal bug: os.path.exists('/var/log/colt/events.log') on the HOST is always False."""
    src = _strip_comments(open(os.path.join(DEPLOY, "logship", "agent.py"),
                               encoding="utf-8").read())
    assert "volume_path(" in src, "logship must resolve the host path via the mount table"
    # It may still TRY the direct path first (that is how it works inside a container), but it must
    # not stop there.
    assert src.count("resolve_log") >= 2


# --------------------------------------------------------------------------------------------
# THE INSTALLERS MUST SHIP IT (the import has no fallback, so a missing file is a hard failure)
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("installer", ["logship.py", "dbbackup.py"])
def test_installer_ships_hostpath(installer):
    src = open(os.path.join(ROOT, installer), encoding="utf-8").read()
    assert "hostpath.py" in src, "%s does not ship deploy/hostpath.py" % installer
    assert "/opt/cybergod/hostpath.py" in src, (
        "%s must write the shared module where the agents add it to sys.path" % installer)


# --------------------------------------------------------------------------------------------
# FINDING NOTHING ON A LIVE BOX IS A FAILURE
# --------------------------------------------------------------------------------------------

def test_missing_log_while_the_app_runs_is_a_FAILURE(logship, monkeypatch, capsys):
    monkeypatch.setattr(logship, "resolve_log", lambda: (None, "not found"))
    monkeypatch.setattr(logship, "container_running", lambda name: True)
    sent = []
    monkeypatch.setattr(logship, "_notify", lambda m: sent.append(m))

    rc = logship.cmd_ship()

    assert rc == 1, "a log that cannot be found while colt-web runs must FAIL, not report success"
    out = capsys.readouterr().out
    assert "RUNNING" in out and "NOT being archived" in out
    assert sent, "the operator must be told the security trail is not leaving the box"


def test_missing_log_while_the_app_is_down_is_not_a_failure(logship, monkeypatch, capsys):
    """A genuinely fresh box has no log yet. That is the ONLY case where silence is honest."""
    monkeypatch.setattr(logship, "resolve_log", lambda: (None, "not found"))
    monkeypatch.setattr(logship, "container_running", lambda name: False)
    monkeypatch.setattr(logship, "_notify", lambda m: None)

    assert logship.cmd_ship() == 0
    assert "not running" in capsys.readouterr().out


def test_resolve_log_uses_the_mount_table_when_the_direct_path_is_absent(logship, monkeypatch):
    monkeypatch.setattr(logship.os.path, "exists", lambda p: False)
    monkeypatch.setattr(logship, "volume_path",
                        lambda c, inside, vol: "/var/lib/docker/volumes/"
                                               "colt-stack_colt_events/_data/events.log")
    path, how = logship.resolve_log()
    assert path.startswith("/var/lib/docker/volumes/")
    assert "mount table" in how


def test_the_offset_file_lives_beside_the_log_on_the_persistent_volume(logship, monkeypatch):
    """If the state file went somewhere ephemeral, every run would re-upload the whole archive
    from byte zero - which is a cost and a duplication bug, not a safety one, but still wrong."""
    monkeypatch.delenv("LOGSHIP_STATE", raising=False)
    host = "/var/lib/docker/volumes/colt-stack_colt_events/_data/events.log"
    assert logship.state_path(host) == os.path.join(os.path.dirname(host), ".logship_state.json")


# --------------------------------------------------------------------------------------------
# model_watch: a baseline that cannot survive a deploy makes the diff unreachable
# --------------------------------------------------------------------------------------------

MW = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts", "model_watch.py")


@pytest.fixture(scope="module")
def model_watch():
    return _load(MW, "model_watch_mod")


def test_model_watch_baseline_is_not_written_into_the_container_image(model_watch, monkeypatch):
    """Two consecutive production ships both printed 'first run - recording the baseline'. The
    snapshot was inside /opt/shodan-skill/scripts, and every deploy recreates that container.

    RUN the resolver rather than grepping for the path. The first version of this test asserted
    `"/var/log/colt" in source` and passed against a mutation that pointed the code somewhere
    else entirely - because the string it matched was in the DOCSTRING explaining the fix. That
    is the same wrong-subject defect the brand gate, recover.py and the caddyguard TAMPER check
    have each already paid for.
    """
    monkeypatch.delenv("MODEL_WATCH_SNAPSHOT", raising=False)
    monkeypatch.setattr(model_watch.os.path, "isdir", lambda p: p == "/var/log/colt")
    monkeypatch.setattr(model_watch.os, "access", lambda p, m: True)

    path, persists = model_watch._snapshot_path()
    assert persists is True
    assert path == os.path.join("/var/log/colt", "models_seen.json"), (
        "the baseline must land on the persistent colt_events volume - the same home as "
        "cost_ledger.sqlite - or the NEW/DISAPPEARED diff can never fire across a deploy")


def test_model_watch_reports_a_baseline_that_will_not_survive(model_watch, monkeypatch):
    """With no persistent volume it still works, but it must SAY the baseline is disposable."""
    monkeypatch.delenv("MODEL_WATCH_SNAPSHOT", raising=False)
    monkeypatch.setattr(model_watch.os.path, "isdir", lambda p: False)

    path, persists = model_watch._snapshot_path()
    assert persists is False
    assert path.endswith("models_seen.json")


def test_model_watch_env_override_wins(model_watch, monkeypatch):
    monkeypatch.setenv("MODEL_WATCH_SNAPSHOT", "/tmp/baseline.json")
    assert model_watch._snapshot_path() == ("/tmp/baseline.json", True)


def test_model_watch_says_so_when_the_baseline_cannot_persist():
    src = open(MW, encoding="utf-8").read()
    assert "SNAPSHOT_PERSISTS" in src
    assert "could NOT persist the baseline" in src, (
        "an unwritable snapshot must be loud; silence is how this ran for its whole life "
        "reporting 'first run'")


# --------------------------------------------------------------------------------------------
# reproducibility: a floor lets two builds of one commit install different bytes
# --------------------------------------------------------------------------------------------

def test_python_multipart_is_pinned_exactly():
    req = os.path.join(ROOT, "webapp", "backend", "requirements.txt")
    lines = [ln.strip() for ln in open(req, encoding="utf-8")
             if ln.strip() and not ln.strip().startswith("#")]
    hit = [ln for ln in lines if ln.lower().startswith("python-multipart")]
    assert hit, "python-multipart is required for White Label uploads"
    assert hit[0].startswith("python-multipart=="), (
        "a >= floor makes the installed version depend on the day the image was built, which "
        "defeats packing the immutable commit - and Trivy reads the floor as the version, which "
        "is why it reported 0.0.18 against an image that had 0.0.32 installed. Got: %s" % hit[0])
