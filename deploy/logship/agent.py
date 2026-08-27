#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""logship agent — the security log, shipped OFF the box it protects, append-only.

WHY THIS EXISTS
    Loki runs on the same droplet it monitors. An attacker who owns the box owns the evidence: the
    events.log, the security alerts, the visitor trail. The one record you most need after an
    incident is the one an intruder deletes first. The forensics of every incident in this repo's
    history came from that file; if the box is compromised, it is gone.

    It is also what makes a CRA Article 14 report POSSIBLE. From 11 September 2026 a severe incident
    must be reported with a 24-hour early warning and a 72-hour notification. You cannot write that
    report from logs the incident erased. An off-box, append-only copy is the source of truth the
    report is built from.

WHAT IT DOES
    Every run, it uploads any NEW bytes of the events log to DigitalOcean Spaces under a dated key.
      * APPEND-ONLY BY CONSTRUCTION. Each run writes a NEW object keyed by timestamp and byte
        offset; it never overwrites a previous one. Deleting the local log cannot delete what is
        already in Spaces, and an attacker with the droplet's Spaces key (read from the same env
        file) can still only ADD objects, because we never issue a delete and the bucket policy
        should deny it. The upload is the whole point: the copy lives where the attacker is not.
      * OFF-BOX OR IT SAYS SO. Same doctrine as dbbackup: credentials come from the existing
        /etc/patchwatch/patchwatch.env (chmod 600, not in git). Absent, it does nothing and states
        that off-box shipping is not configured. It never reports success for work it did not do.
      * RESUMABLE. A small state file records the last byte offset shipped, so each run sends only
        what is new. A rotated (shrunk) log is detected and re-shipped from zero.
      * READ-ONLY with respect to the log. It opens events.log for reading only.

    This is a companion to dbbackup, not a replacement: dbbackup preserves the BOOKS OF RECORD
    (who ran what, the cost ledger); logship preserves the SECURITY TRAIL (what happened to the
    box). Different data, different retention, different reason.

    NOT a log SHIPPER in the Loki sense (no parsing, no indexing). It is an evidence archive. Loki
    stays the query layer; this is the copy that survives Loki's host being owned.
"""
import datetime
import hashlib
import json
import os
import sys

# ONE implementation of "where does a container path live on the host" - see deploy/hostpath.py.
# THE BUG THIS REPLACES (2026-08-27): EVENTS_LOG defaulted to /var/log/colt/events.log, which is
# the path INSIDE colt-web. This agent runs on the HOST under systemd, where the same file lives
# under the colt_events volume mountpoint. os.path.exists() was therefore always False, and every
# run since installation printed "no events log yet - nothing to ship" and exited 0. The off-box
# security archive contained nothing, and said it was fine. dbbackup had already solved this
# exact question, on this exact volume, thirteen days earlier.
sys.path.insert(0, os.environ.get("CYBERGOD_LIB") or "/opt/cybergod")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hostpath import container_running, volume_path   # noqa: E402

CONTAINER = os.environ.get("LOGSHIP_CONTAINER", "colt-web")
EVENTS_INSIDE = os.environ.get("EVENTS_LOG", "/var/log/colt/events.log")
EVENTS_VOLUME = os.environ.get("LOGSHIP_VOLUME", "colt_events")
PW_ENV = os.environ.get("PATCHWATCH_ENV", "/etc/patchwatch/patchwatch.env")
CHUNK_CAP = int(os.environ.get("LOGSHIP_MAX_BYTES", str(64 * 1024 * 1024)))   # 64 MB per run


def resolve_log():
    """(host path to events.log or None, how it was found).

    Tries the literal path first so that running inside the container, or with a bind mount, still
    works; then asks docker where colt-web's own mount actually is.
    """
    if os.path.exists(EVENTS_INSIDE):
        return EVENTS_INSIDE, "direct path"
    p = volume_path(CONTAINER, EVENTS_INSIDE, EVENTS_VOLUME)
    if p:
        return p, "%s mount table" % CONTAINER
    return None, "not found"


def state_path(host_log):
    """The offset file sits BESIDE the log, on the same persistent volume, so a redeploy cannot
    reset it and cause the whole archive to be re-uploaded from byte zero."""
    if os.environ.get("LOGSHIP_STATE"):
        return os.environ["LOGSHIP_STATE"]
    return os.path.join(os.path.dirname(host_log), ".logship_state.json")


def log(m):
    print(m, flush=True)


def _spaces():
    """The same credential source and client as dbbackup, so there is one place secrets live."""
    if not os.path.exists(PW_ENV):
        return None, "%s not found - off-box shipping NOT configured" % PW_ENV, None
    env = {}
    for ln in open(PW_ENV, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    missing = [k for k in ("SPACES_KEY", "SPACES_SECRET", "SPACES_BUCKET") if not env.get(k)]
    if missing:
        return None, "missing %s in %s - off-box shipping NOT configured" % (",".join(missing), PW_ENV), None
    region = env.get("SPACES_REGION", "fra1")
    endpoint = env.get("SPACES_ENDPOINT") or "https://%s.digitaloceanspaces.com" % region
    try:
        import boto3
    except ImportError:
        return None, "boto3 not installed on the host - off-box shipping NOT possible", None
    cl = boto3.client("s3", region_name=region, endpoint_url=endpoint,
                      aws_access_key_id=env["SPACES_KEY"],
                      aws_secret_access_key=env["SPACES_SECRET"])
    return cl, env["SPACES_BUCKET"], env.get("LOGSHIP_PREFIX", "cybergod-logs")


def _load_state(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {"offset": 0, "inode": None}


def _save_state(path, st):
    try:
        tmp = path + ".tmp"
        json.dump(st, open(tmp, "w", encoding="utf-8"))
        os.replace(tmp, path)
    except Exception as e:
        log("   [!] could not persist state: %s" % e)


def _notify(msg):
    """Alerts go through colt-web, which holds the Telegram token; the host does not. Best effort:
    a shipping problem must never take anything down."""
    try:
        import subprocess
        subprocess.run(["docker", "exec", "-i", "colt-web", "python3", "-c",
                        "import sys; from app import notify; notify.telegram(sys.stdin.read())"],
                       input=("logship: " + msg).encode("utf-8"), timeout=20)
    except Exception:
        pass


def cmd_ship():
    EVENTS_LOG, how = resolve_log()

    # ---- NOT FINDING THE LOG ON A LIVE BOX IS A FAILURE, NOT A SUCCESS -------------------------
    # Same rule, same wording and the same reason as dbbackup: if colt-web is running then the
    # events log exists by definition (the app writes to it on every request), so failing to find
    # it means the RESOLUTION is broken, not that there is nothing to archive. Printing an "[i]"
    # and exiting 0 is how this shipped nothing for a week while reporting success.
    if not EVENTS_LOG:
        if container_running(CONTAINER):
            log("[X] %s is RUNNING but %s could not be located on the host - the security trail "
                "is NOT being archived." % (CONTAINER, EVENTS_INSIDE))
            log("    This is a broken lookup, not an empty system. Check the mount table:")
            log("    docker inspect -f '{{range .Mounts}}{{.Destination}} {{.Source}}"
                "{{\"\\n\"}}{{end}}' %s" % CONTAINER)
            _notify("cannot locate %s on the host while %s is running. Nothing is being archived "
                    "off-box." % (EVENTS_INSIDE, CONTAINER))
            return 1
        log("[i] no events log yet and %s is not running - nothing to ship" % CONTAINER)
        return 0
    log("   log: %s  (via %s)" % (EVENTS_LOG, how))

    STATE = state_path(EVENTS_LOG)
    cl, bucket_or_err, prefix = _spaces()
    if cl is None:
        log("[!] %s" % bucket_or_err)
        log("    the security trail is NOT leaving the box. Add SPACES_* to %s to enable it." % PW_ENV)
        return 0                                   # not configured is not a failure

    size = os.path.getsize(EVENTS_LOG)
    st = _load_state(STATE)
    ino = os.stat(EVENTS_LOG).st_ino
    start = st.get("offset", 0)
    # ROTATION DETECTION: a smaller file, or a new inode, means the log was rotated. Re-ship from 0
    # so a rotation cannot create a gap in the archive.
    if ino != st.get("inode") or size < start:
        log("   log rotated (inode changed or shrank) - shipping from the beginning")
        start = 0
    if size <= start:
        log("[i] no new log bytes since the last run (offset %d)" % start)
        return 0

    end = min(size, start + CHUNK_CAP)
    with open(EVENTS_LOG, "rb") as fh:
        fh.seek(start)
        data = fh.read(end - start)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y/%m/%d/%H%M%S")
    digest = hashlib.sha256(data).hexdigest()[:16]
    key = "%s/events/%s-%d-%d-%s.log" % (prefix, stamp, start, end, digest)
    try:
        cl.put_object(Bucket=bucket_or_err, Key=key, Body=data,
                      ContentType="text/plain",
                      Metadata={"sha256": hashlib.sha256(data).hexdigest(),
                                "offset": str(start), "end": str(end)})
    except Exception as e:
        log("[X] upload FAILED: %s" % e)
        _notify("upload to Spaces FAILED (%s). The security trail is not being archived." % e)
        return 1
    st.update({"offset": end, "inode": ino})
    _save_state(STATE, st)
    log("   shipped %d bytes (offset %d..%d) -> s3://%s/%s" % (end - start, start, end,
                                                              bucket_or_err, key))
    return 0


def cmd_verify():
    """Prove an archived object can be read back and matches its own recorded hash. A backup nobody
    reads back is a folder; the same rule applies to the log archive."""
    cl, bucket_or_err, prefix = _spaces()
    if cl is None:
        log("[!] %s" % bucket_or_err)
        return 0
    try:
        r = cl.list_objects_v2(Bucket=bucket_or_err, Prefix="%s/events/" % prefix, MaxKeys=1)
        objs = r.get("Contents") or []
        if not objs:
            log("[i] no archived objects yet")
            return 0
        key = objs[0]["Key"]
        obj = cl.get_object(Bucket=bucket_or_err, Key=key)
        body = obj["Body"].read()
        want = (obj.get("Metadata") or {}).get("sha256")
        got = hashlib.sha256(body).hexdigest()
        ok = (want == got)
        log("   %s  %s  (%d bytes, hash %s)" % ("OK" if ok else "MISMATCH", key, len(body),
                                               "verified" if ok else "%s != %s" % (want, got)))
        return 0 if ok else 1
    except Exception as e:
        log("[X] verify failed: %s" % e)
        return 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ship"
    if cmd == "ship":
        sys.exit(cmd_ship())
    if cmd == "verify":
        sys.exit(cmd_verify())
    log("usage: agent.py [ship|verify]")
    sys.exit(2)


if __name__ == "__main__":
    main()
