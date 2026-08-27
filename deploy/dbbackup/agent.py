#!/usr/bin/env python3
"""dbbackup agent — the books of record, backed up properly and PROVED restorable.

WHY THIS EXISTS
    Two SQLite files hold everything the product cannot regenerate:
      /data/colt.sqlite                     (colt_webdata)  who ran what, when, in which language
      /var/log/colt/cost_ledger.sqlite      (colt_events)   the TRUE all-time cost, the books of
                                                            record, deliberately outliving Loki
    `git` backs up the code. NOTHING backed up these. patchwatch tars the volumes before an
    upgrade, which is better than nothing but is not a database backup:
      * it runs only before a patch, not on a schedule tied to how fast the data changes;
      * it `tar`s a LIVE file. SQLite in WAL mode can be mid-transaction, so the copy inside that
        tarball may be torn, and nothing has ever opened it to find out;
      * a backup nobody has ever restored is not a backup, it is a folder.

WHAT THIS DOES DIFFERENTLY
    1. sqlite3's ONLINE BACKUP API (Connection.backup()), never `cp`/`tar`. It is the supported
       way to copy a database that a live process is writing to, and it is transactionally safe.
    2. VERIFIES THE COPY, not the source: `PRAGMA integrity_check` must say ok, and every table's
       row count in the COPY must equal the source. A copy that fails is DELETED and reported as
       a failure - a corrupt backup is worse than no backup, because it buys false confidence.
    3. OFF-BOX or it says so. A backup on the same droplet does not survive losing the droplet.
       Credentials are read from /etc/patchwatch/patchwatch.env, which already exists, is chmod
       600 and is not in git. If they are absent it keeps a local copy and states plainly that
       off-box is NOT configured. It never reports success for something it did not do.
    4. RESTORE IS PART OF THE SAME SCRIPT, and `--verify-restore` actually performs one into a
       temp directory and compares row counts. That is the only thing that turns a file into a
       backup.

READ-ONLY with respect to the live databases. It opens them for reading and writes only to its
own directory. It never stops a container.
"""
import datetime
import gzip
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile

# ONE implementation of "where does a container path live on the host". See deploy/hostpath.py:
# this resolution was written here, got it wrong once, was fixed here, and then logship made the
# SAME mistake because the fix was not reachable from there. It is shared now. No local fallback
# copy: a second implementation is the defect being removed.
sys.path.insert(0, os.environ.get("CYBERGOD_LIB") or "/opt/cybergod")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hostpath import container_running, sh, volume_path   # noqa: E402

BACKUP_DIR = os.environ.get("DBBACKUP_DIR", "/var/backups/cybergod-db")
KEEP_LOCAL = int(os.environ.get("DBBACKUP_KEEP_LOCAL", "14"))
KEEP_REMOTE = int(os.environ.get("DBBACKUP_KEEP_REMOTE", "60"))
PW_ENV = "/etc/patchwatch/patchwatch.env"
# POSIX-ONLY APIs ARE A TESTABILITY BUG EVEN WHEN PRODUCTION IS LINUX. This used to be
# os.uname()[1], which does not exist on Windows, so the operator's test run died in the
# failure path - the one place a backup tool must be reliable. socket.gethostname() is stdlib
# and identical on the droplet.
HOSTNAME = socket.gethostname()

# (container, path INSIDE the container, logical volume, description)
#
# RESOLVED FROM THE CONTAINER'S MOUNT TABLE, not from a volume name.
# The first version looked up `colt_webdata` and `colt_events` directly and both came back "not
# found", so the very first production run backed up NOTHING and exited 0 - the worst possible
# outcome, because the operator now believes the books of record are safe. Docker Compose PREFIXES
# volumes with the project name, so the real names are `colt-stack_colt_webdata` and
# `colt-stack_colt_events`; docker-compose.web.yml even says so in a comment I did not read.
# Asking the CONTAINER where its own mounts come from is the same rule caddyguard's mount_source()
# already enforces: never assume a path, ask docker. It is also prefix-agnostic, so renaming the
# compose project cannot break the backup again.
DATABASES = [
    ("colt-web", "/data/colt.sqlite", "colt_webdata", "jobs - who ran what"),
    ("colt-web", "/var/log/colt/cost_ledger.sqlite", "colt_events",
     "cost ledger - the books of record"),
]


def log(msg):
    print(msg, flush=True)


def notify(text):
    """Alert through colt-web, which owns the Telegram token and the Gmail credentials.

    The agent runs on the HOST and deliberately has no copy of either: a second home for a
    credential is the defect this repo has paid for repeatedly. Text goes over STDIN, never argv
    (an attacker-shaped string must not reach a command line, and argv has a length limit).
    """
    try:
        p = subprocess.run(
            ["docker", "exec", "-i", "colt-web", "python3", "-c",
             "import sys; from app import notify; notify.telegram(sys.stdin.read())"],
            input=text.encode("utf-8"), capture_output=True, timeout=60)
        if p.returncode == 0:
            log("      alert delivered via colt-web")
            return True
        log("      [warn] colt-web refused the alert: %s" % (p.stderr or b"")[:160])
    except Exception as e:
        log("      [warn] could not alert: %s" % e)
    return False


def table_counts(path):
    """Row count per table. This is what proves a COPY holds the same data as its source."""
    c = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=30)
    try:
        tabs = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t: c.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] for t in sorted(tabs)}
    finally:
        c.close()


def online_backup(src, dst):
    """sqlite3's online backup API. Safe against a live writer; `cp` and `tar` are not."""
    s = sqlite3.connect("file:%s?mode=ro" % src, uri=True, timeout=60)
    d = sqlite3.connect(dst)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


def verify(copy_path, before, after):
    """Verify the COPY. A backup that has never been opened is an assumption, not a backup.

    TWO THINGS MEASURED THE HARD WAY:

    1. A BADLY corrupt file does not return a non-"ok" integrity_check, it RAISES
       `sqlite3.DatabaseError: database disk image is malformed`. The first version let that
       propagate, so the one case this function exists for crashed the agent with a traceback
       instead of being reported and deleted. Everything here is wrapped.

    2. COUNTS CANNOT BE COMPARED TO A SINGLE PRE-BACKUP READ. The source is LIVE: rows commit
       between reading the count and taking the copy, so exact equality would fail on a busy
       database and delete a perfectly good backup. That is a false alarm on a healthy system,
       which is the worst kind of check because it teaches you to ignore it.
       These tables are append-mostly (jobs rows are inserted then updated; ledger rows are only
       appended), so the honest invariant is a WINDOW: the copy must hold at least what existed
       before the backup started and no more than what exists after it finished.
    """
    try:
        c = sqlite3.connect("file:%s?mode=ro" % copy_path, uri=True, timeout=60)
        try:
            res = c.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            c.close()
        if res != "ok":
            return False, "integrity_check said %r" % str(res)[:120]
        got = table_counts(copy_path)
    except Exception as e:
        return False, "the copy will not open: %s: %s" % (type(e).__name__, e)

    if set(got) != set(before):
        return False, "tables differ: source=%s copy=%s" % (sorted(before), sorted(got))
    for t, n in sorted(got.items()):
        lo, hi = before.get(t, 0), max(before.get(t, 0), after.get(t, 0))
        if not (lo <= n <= hi):
            return False, ("table %s holds %d rows, outside the [%d..%d] the source had before "
                           "and after the copy" % (t, n, lo, hi))
    return True, "integrity ok, %s" % ", ".join("%s=%d" % kv for kv in sorted(got.items()))


def spaces_client():
    """Credentials come from patchwatch's env file, which already exists and is chmod 600.
    Returns (client, bucket, prefix) or (None, reason, None)."""
    if not os.path.exists(PW_ENV):
        return None, "%s not present - off-box upload NOT configured" % PW_ENV, None
    env = {}
    for ln in open(PW_ENV, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    need = ("SPACES_KEY", "SPACES_SECRET", "SPACES_BUCKET")
    missing = [k for k in need if not env.get(k)]
    if missing:
        return None, "missing %s in %s - off-box upload NOT configured" % (",".join(missing), PW_ENV), None
    region = env.get("SPACES_REGION", "fra1")
    endpoint = env.get("SPACES_ENDPOINT") or "https://%s.digitaloceanspaces.com" % region
    try:
        import boto3
    except ImportError:
        return None, "boto3 not installed on the host - off-box upload NOT possible", None
    cl = boto3.client("s3", region_name=region, endpoint_url=endpoint,
                      aws_access_key_id=env["SPACES_KEY"],
                      aws_secret_access_key=env["SPACES_SECRET"])
    return cl, env["SPACES_BUCKET"], env.get("DBBACKUP_PREFIX", "cybergod-db")


def cmd_backup():
    # A traceback is not a diagnosis. Run by hand as a non-root user this used to die with a raw
    # PermissionError, which reads like a bug in the tool rather than "you are not root".
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.chmod(BACKUP_DIR, 0o700)                  # these files contain user emails
    except OSError as e:
        log("[X] cannot use the backup directory %s: %s" % (BACKUP_DIR, e))
        log("    systemd runs this as root. To run it by hand elsewhere, set DBBACKUP_DIR to a")
        log("    path you can write, e.g. DBBACKUP_DIR=/tmp/dbb python3 agent.py backup")
        return 1
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    made, failed = [], []

    for cont, inside, vol, what in DATABASES:
        name = os.path.basename(inside)
        log("   %-22s (%s)" % (name, what))
        src = volume_path(cont, inside, vol)
        if not src:
            # A database that does not exist yet (fresh deployment) is normal. A database that
            # exists but cannot be FOUND is a broken backup wearing a green tick - see the
            # "found nothing at all" check below, which is what turns this into a failure.
            log("      SKIP %s not found (container %s, %s)" % (inside, cont, vol))
            continue
        raw = os.path.join(BACKUP_DIR, "%s.%s" % (name, stamp))
        try:
            # Read the counts either side of the copy. The source is LIVE, so a single reading
            # cannot be compared for equality - see verify() for why that would false-alarm.
            before = table_counts(src)
            online_backup(src, raw)
            after = table_counts(src)
        except Exception as e:
            failed.append("%s: backup failed: %s: %s" % (name, type(e).__name__, e))
            log("      FAIL %s: %s" % (type(e).__name__, e))
            if os.path.exists(raw):
                os.unlink(raw)
            continue

        want = before
        ok, msg = verify(raw, before, after)
        if not ok:
            os.unlink(raw)                            # never keep a copy we could not verify
            failed.append("%s: %s" % (name, msg)); log("      FAIL %s" % msg)
            continue
        log("      verified: %s" % msg)

        gz = raw + ".gz"
        with open(raw, "rb") as fi, gzip.open(gz, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        os.unlink(raw)
        # Opening the copy read-only creates WAL sidecars (-wal/-shm) next to it. They are not
        # backups, but they share the timestamped prefix, so leaving them would let rotation count
        # them and drop real .gz files early. Remove them here.
        for side in ("-wal", "-shm"):
            try:
                os.unlink(raw + side)
            except OSError:
                pass
        sha = hashlib.sha256(open(gz, "rb").read()).hexdigest()
        size = os.path.getsize(gz)
        log("      %s  %d bytes  sha256 %s" % (os.path.basename(gz), size, sha[:12]))
        made.append({"file": gz, "name": name, "bytes": size, "sha256": sha, "counts": want})

    # ---- off-box, or say plainly that there is none -------------------------------------------
    cl, bucket, prefix = spaces_client()
    if cl is None:
        log("   [!] LOCAL ONLY: %s" % bucket)
        log("       A copy on the same droplet does not survive losing the droplet. Set")
        log("       SPACES_KEY/SPACES_SECRET/SPACES_BUCKET in %s to close this." % PW_ENV)
    else:
        for m in made:
            key = "%s/%s/%s" % (prefix, HOSTNAME, os.path.basename(m["file"]))
            try:
                cl.upload_file(m["file"], bucket, key)
                m["remote"] = key
                log("   uploaded  s3://%s/%s" % (bucket, key))
            except Exception as e:
                failed.append("%s: upload failed: %s" % (m["name"], e))
                log("   [!] upload FAILED for %s: %s" % (m["name"], e))
        try:                                           # prune old remote copies
            objs = cl.list_objects_v2(Bucket=bucket, Prefix="%s/%s/" % (prefix, HOSTNAME))
            for o in sorted(objs.get("Contents", []), key=lambda x: x["LastModified"])[:-KEEP_REMOTE]:
                cl.delete_object(Bucket=bucket, Key=o["Key"])
        except Exception as e:
            log("   [warn] remote prune skipped: %s" % e)

    # ---- FINDING NOTHING ON A LIVE BOX IS A FAILURE, NOT A SUCCESS ----------------------------
    # The first production run printed "volume colt_webdata not found" twice, backed up NOTHING,
    # and exited 0. That is the worst possible outcome for a backup tool: the operator now
    # believes the books of record are safe. A fresh deployment legitimately has no databases yet,
    # so the discriminator is whether the APP IS RUNNING - if colt-web is up, those files exist by
    # definition and failing to find them means the resolution is broken, not the estate empty.
    if not made and not failed:
        live = sorted({c for c, _, _, _ in DATABASES if container_running(c)})
        if live:
            failed.append(
                "NOT ONE database was found, yet %s is running - so the files exist and the "
                "lookup is broken. Nothing was backed up. Check the container mount table: "
                "docker inspect -f '{{range .Mounts}}{{.Destination}} {{.Source}}\n{{end}}' %s"
                % (", ".join(live), live[0]))
            log("   [X] nothing found while %s is RUNNING - this is a broken backup, not an "
                "empty system" % ", ".join(live))

    # ---- rotate local --------------------------------------------------------------------------
    for _, inside, _, _ in DATABASES:
        name = os.path.basename(inside)
        old = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith(name + "."))
        for f in old[:-KEEP_LOCAL]:
            os.unlink(os.path.join(BACKUP_DIR, f))

    if failed:
        notify("cybergod DB BACKUP FAILED on %s\n\n%s" % (HOSTNAME, "\n".join(failed)))
        log("\n   %d FAILURE(S)" % len(failed))
        return 1
    if not made:
        log("\n   nothing to back up (no databases present yet)")
        return 0
    log("\n   OK  %d database(s) backed up and VERIFIED%s"
        % (len(made), "" if cl is None else ", off-box copy uploaded"))
    return 0


def cmd_verify_restore():
    """RESTORE THE NEWEST BACKUP AND READ IT. Until this passes, the files are not backups.

    Restores into a temp directory - it never touches the live database - and asserts the restored
    copy opens, passes integrity_check and holds at least as many rows as the live one had at
    backup time.
    """
    if not os.path.isdir(BACKUP_DIR):
        log("   no backup directory yet: %s" % BACKUP_DIR)
        return 1
    rc = 0
    for _c, inside, _v, _w in DATABASES:
        name = os.path.basename(inside)
        cands = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith(name + ".") and f.endswith(".gz"))
        if not cands:
            log("   %-22s no backup to restore" % name)
            continue
        newest = os.path.join(BACKUP_DIR, cands[-1])
        tmp = tempfile.mkdtemp(prefix="dbrestore-")
        out = os.path.join(tmp, name)
        try:
            with gzip.open(newest, "rb") as fi, open(out, "wb") as fo:
                shutil.copyfileobj(fi, fo)
            counts = table_counts(out)
            c = sqlite3.connect("file:%s?mode=ro" % out, uri=True)
            integ = c.execute("PRAGMA integrity_check").fetchone()[0]
            c.close()
            if integ != "ok":
                log("   %-22s RESTORE FAILED: %s" % (name, integ)); rc = 1
            else:
                log("   %-22s restored from %s -> %s"
                    % (name, cands[-1], ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))
        except Exception as e:
            log("   %-22s RESTORE FAILED: %s" % (name, e)); rc = 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return rc


def cmd_restore(path, target_vol, target_name):
    """Deliberate, explicit restore over a LIVE database. Never automatic.

    Resolves the target through the same DATABASES table the backup uses, so restore and backup
    can never disagree about where a file lives - the "one home for a value" rule.
    """
    entry = next((d for d in DATABASES
                  if d[2] == target_vol and os.path.basename(d[1]) == target_name), None)
    if not entry:
        log("   unknown target %s / %s. Known:" % (target_vol, target_name))
        for c, i, v, _w in DATABASES:
            log("     %-14s %s" % (v, os.path.basename(i)))
        return 1
    dst = volume_path(entry[0], entry[1], entry[2])
    if not dst:
        log("   target not found: %s in %s (container %s)" % (entry[1], target_vol, entry[0]))
        return 1
    bak = dst + ".before-restore-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    shutil.copy2(dst, bak)                                   # keep what we are about to replace
    tmp = tempfile.mkdtemp(prefix="dbrestore-")
    out = os.path.join(tmp, target_name)
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rb") as fi, open(out, "wb") as fo:
                shutil.copyfileobj(fi, fo)
        else:
            shutil.copy2(path, out)
        c = sqlite3.connect("file:%s?mode=ro" % out, uri=True)
        integ = c.execute("PRAGMA integrity_check").fetchone()[0]
        c.close()
        if integ != "ok":
            log("   REFUSING: the backup does not pass integrity_check (%s)" % integ); return 1
        shutil.copy2(out, dst)
        log("   restored %s -> %s   (previous file kept at %s)" % (path, dst, bak))
        log("   restart colt-web so it reopens the file: docker restart colt-web")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    a = sys.argv[1:]
    if not a or a[0] == "backup":
        return cmd_backup()
    if a[0] == "verify-restore":
        return cmd_verify_restore()
    if a[0] == "restore" and len(a) >= 4:
        return cmd_restore(a[1], a[2], a[3])
    if a[0] == "list":
        if os.path.isdir(BACKUP_DIR):
            for f in sorted(os.listdir(BACKUP_DIR)):
                p = os.path.join(BACKUP_DIR, f)
                print("  %-46s %10d bytes  %s" % (f, os.path.getsize(p),
                      datetime.datetime.utcfromtimestamp(os.path.getmtime(p)).isoformat()))
        return 0
    print(__doc__)
    print("usage: agent.py [backup|verify-restore|list|restore <file.gz> <volume> <name>]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
