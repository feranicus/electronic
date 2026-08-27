"""The database backup must be a backup, not a folder of files nobody has opened.

WHAT THIS PINS, and every one of these was found by MEASURING rather than reasoning:

  * a backup taken while a writer is COMMITTING must still verify. The first version compared the
    copy against a single pre-backup row count, which on a live database is a race: it would have
    deleted good backups and alerted, nightly, on a perfectly healthy system. A check that
    false-alarms is worse than no check, because it teaches you to ignore it.
  * a BADLY corrupt file RAISES sqlite3.DatabaseError rather than returning a non-"ok"
    integrity_check. The first version let that propagate, so the one case verify() exists for
    crashed the agent with a traceback instead of being reported and the copy deleted.
  * a failed backup must ALERT and exit non-zero. Silence after a backup run is indistinguishable
    from success, and that is exactly how people discover at restore time that they have nothing.

Stdlib only (plus pytest). No httpx, no boto3: a test that cannot run on the operator's Windows
box is not a check, and this repo has already paid four wasted ships for that lesson.
"""
import gzip
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "deploy", "dbbackup", "agent.py")


def _agent(backup_dir):
    os.environ["DBBACKUP_DIR"] = backup_dir
    spec = importlib.util.spec_from_file_location("dbb_agent_t", AGENT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.spaces_client = lambda: (None, "not configured in tests", None)
    m.sent = []
    m.notify = lambda t: m.sent.append(t) or True
    return m


def _ledger(path, rows=193):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE assessments (id INTEGER PRIMARY KEY, company TEXT, cost_usd REAL)")
    c.executemany("INSERT INTO assessments (company, cost_usd) VALUES (?,?)",
                  [("co%d" % i, 0.0049) for i in range(rows)])
    c.commit()
    c.execute("PRAGMA journal_mode=WAL")          # the mode that makes cp/tar unsafe
    c.close()


def _fixture():
    work = tempfile.mkdtemp(prefix="dbbtest-")
    vol = os.path.join(work, "vol")
    os.makedirs(vol)
    _ledger(os.path.join(vol, "cost_ledger.sqlite"))
    jobs = os.path.join(vol, "colt.sqlite")
    c = sqlite3.connect(jobs)
    c.execute("CREATE TABLE jobs (job_id TEXT PRIMARY KEY, email TEXT, company TEXT, lang TEXT)")
    c.executemany("INSERT INTO jobs VALUES (?,?,?,?)",
                  [("j%d" % i, "a@s4biz.io", "c%d" % i, "en") for i in range(50)])
    c.commit()
    c.close()
    ag = _agent(os.path.join(work, "backups"))
    ag.volume_path = lambda cont, inside, v: (
        os.path.join(vol, os.path.basename(inside))
        if os.path.exists(os.path.join(vol, os.path.basename(inside))) else None)
    ag.container_running = lambda name: False        # no docker in the test environment
    return work, vol, ag


def test_a_backup_taken_while_a_writer_commits_still_verifies():
    """The false-alarm case. Exact row-count equality against a pre-backup read cannot hold on a
    live database, and deleting a good backup because of it is the worst outcome available."""
    work, vol, ag = _fixture()
    try:
        src = os.path.join(vol, "cost_ledger.sqlite")
        stop = threading.Event()
        wrote = [0]

        def writer():
            c = sqlite3.connect(src, timeout=30)
            while not stop.is_set():
                c.execute("INSERT INTO assessments (company, cost_usd) VALUES ('live', 0.01)")
                c.commit()
                wrote[0] += 1
            c.close()

        t = threading.Thread(target=writer)
        t.start()
        time.sleep(0.15)
        try:
            dst = os.path.join(work, "copy.sqlite")
            before = ag.table_counts(src)
            ag.online_backup(src, dst)
            after = ag.table_counts(src)
        finally:
            stop.set()
            t.join()
        assert wrote[0] > 0, "the fixture never wrote concurrently, so this proved nothing"
        ok, msg = ag.verify(dst, before, after)
        assert ok, "a healthy live backup was rejected (%s) - this would alert every night" % msg

        # AND THE SAME PROPERTY, DETERMINISTICALLY. The threaded case above only exercises the
        # race WHEN IT HAPPENS, so on a fast machine it can pass while exact-equality is back in
        # the code - which is exactly what a mutation test caught. Force the window: commit rows
        # between reading `before` and taking the copy, so copy_count > before is guaranteed.
        before = ag.table_counts(src)
        c = sqlite3.connect(src, timeout=30)
        for _ in range(25):
            c.execute("INSERT INTO assessments (company, cost_usd) VALUES ('gap', 0.01)")
        c.commit()
        c.close()
        forced = os.path.join(work, "forced.sqlite")
        ag.online_backup(src, forced)
        after = ag.table_counts(src)
        assert after["assessments"] > before["assessments"], "the fixture did not create a window"
        ok, msg = ag.verify(forced, before, after)
        assert ok, ("rows committed between the count and the copy were treated as corruption "
                    "(%s). Exact equality against a pre-backup read cannot hold on a live "
                    "database and would delete good backups nightly." % msg)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_a_corrupt_copy_is_reported_not_raised():
    work, vol, ag = _fixture()
    try:
        src = os.path.join(vol, "cost_ledger.sqlite")
        dst = os.path.join(work, "copy.sqlite")
        before = ag.table_counts(src)
        ag.online_backup(src, dst)
        after = ag.table_counts(src)
        with open(dst, "r+b") as fh:
            fh.seek(4096)
            fh.write(b"\xde\xad\xbe\xef" * 500)
        ok, msg = ag.verify(dst, before, after)          # must NOT raise
        assert not ok, "a corrupt backup passed verification"
        assert "will not open" in msg or "integrity" in msg, msg
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_a_copy_missing_rows_or_carrying_a_stray_table_is_caught():
    work, vol, ag = _fixture()
    try:
        src = os.path.join(vol, "cost_ledger.sqlite")
        before = ag.table_counts(src)
        short = os.path.join(work, "short.sqlite")
        ag.online_backup(src, short)
        after = ag.table_counts(src)
        c = sqlite3.connect(short)
        c.execute("DELETE FROM assessments WHERE id < 50")
        c.commit()
        c.close()
        ok, msg = ag.verify(short, before, after)
        assert not ok and "rows" in msg, "a truncated backup passed: %s" % msg

        wrong = os.path.join(work, "wrong.sqlite")
        ag.online_backup(src, wrong)
        c = sqlite3.connect(wrong)
        c.execute("CREATE TABLE surprise (x)")
        c.commit()
        c.close()
        ok, msg = ag.verify(wrong, before, after)
        assert not ok and "tables differ" in msg, "the wrong file passed: %s" % msg
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_backup_then_restore_after_the_source_is_destroyed():
    """The only thing that turns a file into a backup."""
    work, vol, ag = _fixture()
    try:
        assert ag.cmd_backup() == 0
        assert ag.cmd_verify_restore() == 0
        led = os.path.join(vol, "cost_ledger.sqlite")
        newest = sorted(f for f in os.listdir(ag.BACKUP_DIR)
                        if f.startswith("cost_ledger") and f.endswith(".gz"))[-1]
        with open(led, "wb") as fh:                       # lose the database
            fh.write(b"\x00" * 4096)
        rc = ag.cmd_restore(os.path.join(ag.BACKUP_DIR, newest),
                            "colt_events", "cost_ledger.sqlite")
        assert rc == 0, "restore failed"
        assert ag.table_counts(led)["assessments"] == 193, "restored data is wrong"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_a_copy_that_fails_verification_is_never_left_on_disk():
    """A file that failed its own check must not sit in the backup directory looking like a
    backup. It is worse than nothing: it is the one you would reach for in an incident."""
    work, vol, ag = _fixture()
    try:
        ag.verify = lambda p, b, a: (False, "forced failure for this test")
        rc = ag.cmd_backup()
        assert rc == 1, "a backup whose verification failed was reported as success"
        left = [f for f in os.listdir(ag.BACKUP_DIR)] if os.path.isdir(ag.BACKUP_DIR) else []
        assert not left, "unverified copies were kept: %s" % left
        assert ag.sent, "the failure was silent"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_a_failed_backup_alerts_and_exits_non_zero():
    work, vol, ag = _fixture()
    try:
        with open(os.path.join(vol, "colt.sqlite"), "wb") as fh:
            fh.write(b"not a database")
        rc = ag.cmd_backup()
        assert rc == 1, "a broken database was reported as a successful backup"
        assert ag.sent, "the failure was silent - silence is indistinguishable from success"
        assert "colt.sqlite" in ag.sent[0], "the alert does not name the database"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_a_missing_database_is_a_skip_not_a_failure():
    """A fresh deployment has no jobs table yet. Absence of evidence is not a finding, and it is
    not a success either: it says SKIP and backs up what does exist."""
    work, vol, ag = _fixture()
    try:
        os.unlink(os.path.join(vol, "colt.sqlite"))
        rc = ag.cmd_backup()
        assert rc == 0 and not ag.sent, "a not-yet-created database was treated as a failure"
        made = [f for f in os.listdir(ag.BACKUP_DIR) if f.startswith("cost_ledger")]
        assert made, "it skipped the missing one and also failed to back up the present one"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_it_never_uses_cp_or_tar_for_a_live_sqlite_file():
    """`cp`/`tar` on a live SQLite database can capture a torn write. patchwatch's volume tarball
    does exactly that, which is why this agent exists alongside it."""
    src = open(AGENT, encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    body = body.split('"""', 2)[-1]                      # drop the module docstring
    assert ".backup(" in body, "the online backup API is not used"
    for bad in ("shutil.copy2(src", "tar czf", "cp %s"):
        assert bad not in body, "a live database is being copied with %r" % bad


def test_credentials_have_exactly_one_home_and_it_is_not_git():
    src = open(AGENT, encoding="utf-8").read()
    assert "/etc/patchwatch/patchwatch.env" in src, "it invented a second credential home"
    for leak in ("SPACES_KEY=", "aws_secret_access_key='", 'aws_secret_access_key="'):
        assert leak not in src, "a credential value is hardcoded: %r" % leak


def test_ship_py_invokes_it_as_a_building_block():
    """Operating principle 7: the operator runs ONE command. A backup nobody triggers is not a
    backup, and a second command to remember is a defect."""
    src = open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()
    body = "\n".join(l.split("#", 1)[0] for l in src.splitlines())
    assert 'os.path.join(HERE, "dbbackup.py")' in body, (
        "ship.py never RUNS dbbackup.py, so the backup depends on the operator remembering a "
        "second command. (Checking for the bare filename is not enough: it also appears in a "
        "print() line, which is how a mutation of the real call site went unnoticed.)")


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))


def test_no_posix_only_api_in_code_the_tests_exercise():
    """FIFTH occurrence of the same root cause, so it is a check now rather than a note.

    `os.uname()` does not exist on Windows. The agent RUNS on the Linux droplet, so production was
    never affected - but the tests run on the operator's Windows box, and the call sat on the
    FAILURE path, which is the one place a backup tool has to be reliable. `python ship.py` died
    with `AttributeError: module 'os' has no attribute 'uname'` after a clean deploy.

    The rule this enforces is the one CLAUDE.md already carries: a check that cannot run on the
    invoking platform is not a check. Anything the test suite executes must be importable and
    runnable on Windows, even when it only ever ships to Linux.
    """
    import ast
    src = open(AGENT, encoding="utf-8").read()
    tree = ast.parse(src)
    POSIX_ONLY = {
        ("os", "uname"): "socket.gethostname()",
        ("os", "getuid"): "not needed, or guard it",
        ("os", "geteuid"): "not needed, or guard it",
        ("os", "fork"): "subprocess",
        ("os", "getpwuid"): "not needed",
    }
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            key = (node.value.id, node.attr)
            if key in POSIX_ONLY:
                bad.append("%s.%s (line %d) - use %s"
                           % (key[0], key[1], node.lineno, POSIX_ONLY[key]))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])] + [getattr(node, "module", "")]
            for n in names:
                if (n or "").split(".")[0] in {"pwd", "grp", "fcntl", "termios", "resource"}:
                    bad.append("imports %s, which does not exist on Windows (line %d)"
                               % (n, node.lineno))
    assert not bad, (
        "the agent uses a POSIX-only API, so the tests cannot run on the operator's machine:\n  "
        + "\n  ".join(bad))


def test_the_agent_does_not_use_a_deprecated_utc_clock():
    """datetime.utcnow() is deprecated and emits a warning per call. Six of them per run buried
    the real output in the operator's terminal."""
    src = open(AGENT, encoding="utf-8").read()
    assert "utcnow(" not in src, (
        "datetime.utcnow() is deprecated - use datetime.now(datetime.timezone.utc)")


def test_finding_no_database_while_the_app_is_RUNNING_is_a_failure():
    """THE FIRST PRODUCTION RUN'S DEFECT, and the worst outcome a backup tool can have.

    Docker Compose prefixes volumes with the project name, so `colt_webdata` matched nothing and
    the real volume is `colt-stack_colt_webdata`. The run printed "volume not found" twice, backed
    up NOTHING, and exited 0 - after which the operator believes the books of record are safe.

    A fresh deployment legitimately has no databases yet, so the discriminator is whether the APP
    IS RUNNING: if colt-web is up those files exist by definition, and not finding them means the
    lookup is broken, not that the system is empty.
    """
    work, vol, ag = _fixture()
    try:
        ag.volume_path = lambda c, i, v: None            # reproduce the name mismatch
        ag.container_running = lambda name: True         # ...on a box where colt-web is UP
        rc = ag.cmd_backup()
        assert rc == 1, "backing up NOTHING on a live box was reported as success"
        assert ag.sent, "and it was silent - the operator would never learn"
        assert "colt-web is running" in ag.sent[0], (
            "the alert does not explain WHY this is a failure: %s" % ag.sent[0][:160])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_a_fresh_deployment_with_nothing_running_is_still_a_clean_skip():
    """The other direction: do not fail a box that genuinely has no databases yet."""
    work, vol, ag = _fixture()
    try:
        ag.volume_path = lambda c, i, v: None
        ag.container_running = lambda name: False
        rc = ag.cmd_backup()
        assert rc == 0 and not ag.sent, "a genuinely empty system was treated as broken"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _patch_sh(ag, fake):
    """Stub docker WHERE THE RESOLVER IS DEFINED, not where it happens to be imported.

    volume_path used to live in this agent; it now lives in deploy/hostpath.py because logship
    needed the same answer and made the same mistake for want of it (2026-08-27). Setting
    `ag.sh = fake` therefore stopped having any effect - the real function kept calling the real
    docker, found nothing, and the test failed while the code was correct. Resolving the owning
    module from the function itself keeps this honest if it ever moves again.
    """
    mod = sys.modules[ag.volume_path.__module__]
    real = mod.sh
    mod.sh = fake
    return lambda: setattr(mod, "sh", real)


def test_the_path_lookup_resolves_through_the_containers_mount_table():
    """RUN it, do not grep for it. Greping the source for ".Mounts" passed against a mutation that
    kept the string and disabled the branch - the wrong-subject defect this repo keeps paying for.

    This gives the agent a REAL container mount table and NO usable volume list, so the only way
    to find the file is by asking the container. That is what makes it immune to Compose's
    project prefix, which is what broke the first production run.
    """
    work = tempfile.mkdtemp(prefix="dbbmount-")
    try:
        data = os.path.join(work, "some", "docker", "path", "_data")
        os.makedirs(data)
        _ledger(os.path.join(data, "cost_ledger.sqlite"))
        ag = _agent(os.path.join(work, "backups"))

        def fake_sh(cmd, timeout=120):
            if ".Mounts" in cmd:
                return 0, "/var/log/colt|%s" % data, ""
            if "volume ls" in cmd:
                return 0, "totally_unrelated_volume", ""      # the fallback CANNOT help here
            return 1, "", ""
        restore = _patch_sh(ag, fake_sh)
        try:
            got = ag.volume_path("colt-web", "/var/log/colt/cost_ledger.sqlite", "colt_events")
        finally:
            restore()
        assert got == os.path.join(data, "cost_ledger.sqlite"), (
            "the file was not resolved through the container's mount table: %r" % got)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_the_volume_fallback_tolerates_the_compose_project_prefix():
    """When the container is stopped, the volume list is the only source - and Compose names it
    `colt-stack_colt_events`, not `colt_events`. That mismatch is the original bug."""
    work = tempfile.mkdtemp(prefix="dbbvol-")
    try:
        mp = os.path.join(work, "vols", "colt-stack_colt_events", "_data")
        os.makedirs(mp)
        _ledger(os.path.join(mp, "cost_ledger.sqlite"))
        ag = _agent(os.path.join(work, "backups"))

        def fake_sh(cmd, timeout=120):
            if ".Mounts" in cmd:
                return 1, "", "container is not running"
            if "volume ls" in cmd:
                return 0, "colt-stack_colt_events\nvideodead_data", ""
            if "volume inspect" in cmd and "colt-stack_colt_events" in cmd:
                return 0, mp, ""
            return 1, "", ""
        restore = _patch_sh(ag, fake_sh)
        try:
            got = ag.volume_path("colt-web", "/var/log/colt/cost_ledger.sqlite", "colt_events")
        finally:
            restore()
        assert got == os.path.join(mp, "cost_ledger.sqlite"), (
            "the Compose-prefixed volume was not found - this is the exact first-run defect: %r"
            % got)
    finally:
        shutil.rmtree(work, ignore_errors=True)
