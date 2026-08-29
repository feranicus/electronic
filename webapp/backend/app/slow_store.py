"""slow_store.py — the long-horizon scan evidence, on disk instead of in a dying process.

WHY THIS FILE EXISTS
    shield.py grew a 24-hour distinct-path window on 2026-08-27 to catch scanners that pace
    themselves under the five-minute rule. The logic was right and it never fired once. The
    evidence lived in a module-level dict, and `deploy_web_direct.py` recreates colt-web with
    `--force-recreate` on every `python ship.py`, so a window measured in DAYS was being kept in
    state that dies in HOURS. On a release day it was reset several times before lunch.

    The 2026-08-29 digest is what made it undeniable: 52,879 attack-shaped requests over fourteen
    days, ZERO blocked, and a returning actor on 212.58.119.0/24 that had been probing for fifteen
    days at about 1.3 requests a day. Nothing that patient can ever accumulate twelve distinct
    paths inside one process lifetime.

    So the evidence goes where the cost ledger and the user store already are: SQLite on the
    persistent `colt_events` volume, which BOTH colt-web and the bots mount, and which survives
    redeploys, image rebuilds and Loki retention.

THE /24, AND WHY IT IS SCORING ONLY
    The digest folds returning actors to a /24 and the shield did not, which is why a pattern that
    was obvious in an email was invisible to the blocker. Accumulating distinct probe paths per
    /24 turns fifteen days of patience into evidence.

    It does NOT authorise blocking a /24. That is up to 256 addresses and may be an office or a
    mobile carrier, and it stays an operator decision behind a Telegram button, exactly as it is
    today. What the network evidence does is convict an INDIVIDUAL ADDRESS that has itself already
    contributed probe paths. Corroboration, the same doctrine every ownership anchor in the engine
    follows: a strong signal still has to be corroborated before it is allowed to convict.

WRITE-BEHIND, NOT WRITE-THROUGH
    A SQLite write per request would put disk I/O on the hot path of a web server whose whole job
    during an attack is to stay up. The in-memory dict stays the hot path; this module flushes and
    re-reads once a minute. At most a minute of evidence is lost to a crash, which is nothing
    against a fourteen-day window.

MERGE, NEVER REPLACE
    Rows are upserted with `ts = max(existing, new)`. If colt-web is ever run with more than one
    worker, each process holds a partial view, and a replace would have them clobbering each other
    into permanent amnesia. A merge lets them converge instead, and the periodic re-read is what
    carries one worker's sighting to the others.

EVERYTHING HERE FAILS OPEN. A defensive store that raises takes the site down to protect it, which
is a worse outcome than the scan it was watching. Every public function is wrapped and returns a
safe empty value.
"""
import os
import sqlite3
import time

# Same home and the same reasoning as cost_ledger.sqlite and users.sqlite: the shared, persistent
# colt_events volume. NOT colt_webdata, which only colt-web mounts.
DB_PATH = os.environ.get("SHIELD_SLOW_DB", "/var/log/colt/shield_slow.sqlite")

FLUSH_S = int(os.environ.get("SHIELD_SLOW_FLUSH_S", "60") or 60)

# Retention is the longest window any caller asks about. Fourteen days, because that is the span
# over which the returning actors in the digest actually operate.
KEEP_S = int(os.environ.get("SHIELD_SLOW_KEEP_S", str(14 * 86400)) or 14 * 86400)

# Bounds. The input is chosen by the attacker, so both dimensions are capped.
MAX_KEYS = int(os.environ.get("SHIELD_SLOW_MAX_KEYS", "8000") or 8000)
MAX_PATHS_PER_KEY = int(os.environ.get("SHIELD_SLOW_MAX_PATHS", "64") or 64)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS slow (
    k    TEXT NOT NULL,
    path TEXT NOT NULL,
    ts   REAL NOT NULL,
    PRIMARY KEY (k, path)
);
CREATE INDEX IF NOT EXISTS slow_ts ON slow (ts);
"""

_last_flush = [0.0]
_broken = [False]          # one failure disables the store for the process; it never retries hot


def net_key(ip):
    """The /24 for IPv4, the /48 for IPv6. Returns "" for anything unparseable.

    Purely textual on purpose: this runs on the request path and must not import ipaddress or
    allocate objects per request. An address that does not look like either family yields "",
    and every caller treats "" as "no network evidence" rather than as a group.
    """
    s = str(ip or "")
    if ":" in s:
        parts = s.split(":")
        return ":".join(parts[:3]) + "::/48" if len(parts) >= 3 else ""
    parts = s.split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        return ""
    return ".".join(parts[:3]) + ".0/24"


def _connect():
    d = os.path.dirname(DB_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    # A short timeout rather than the default five seconds: if another writer is holding the lock
    # we would rather lose one flush than stall a request thread.
    c = sqlite3.connect(DB_PATH, timeout=2.0)
    c.executescript(_SCHEMA)
    return c


def load(since_ts=None):
    """Every live (key, path, ts) as {key: {path: ts}}. {} on any failure."""
    if _broken[0]:
        return {}
    try:
        cutoff = since_ts if since_ts is not None else time.time() - KEEP_S
        out = {}
        with _connect() as c:
            for k, p, ts in c.execute("SELECT k, path, ts FROM slow WHERE ts >= ?", (cutoff,)):
                d = out.setdefault(k, {})
                if len(d) < MAX_PATHS_PER_KEY or p in d:
                    d[p] = ts
        return out
    except Exception:
        _broken[0] = True
        return {}


def flush(mem, now=None):
    """Merge the in-memory view into the database and return the merged view.

    Returns `mem` unchanged on any failure, so a broken or read-only database degrades the shield
    to exactly the behaviour it had before this module existed rather than breaking it.
    """
    if _broken[0]:
        return mem
    now = now or time.time()
    try:
        rows = []
        for k, paths in list(mem.items())[:MAX_KEYS]:
            for p, ts in list(paths.items())[:MAX_PATHS_PER_KEY]:
                rows.append((str(k)[:64], str(p)[:200], float(ts)))
        with _connect() as c:
            # MAX() is what makes concurrent writers converge instead of overwrite. Without it the
            # last worker to flush would erase the others' sightings and the window would never
            # fill on a multi-worker deployment.
            c.executemany(
                "INSERT INTO slow (k, path, ts) VALUES (?, ?, ?) "
                "ON CONFLICT(k, path) DO UPDATE SET ts = MAX(ts, excluded.ts)", rows)
            c.execute("DELETE FROM slow WHERE ts < ?", (now - KEEP_S,))
        _last_flush[0] = now
        merged = load(now - KEEP_S)
        for k, paths in mem.items():                 # anything written since the read still counts
            merged.setdefault(k, {}).update(paths)
        return merged
    except Exception:
        _broken[0] = True
        return mem


def forget(key):
    """Delete every path recorded under `key`. Returns rows removed, 0 on any failure.

    NEEDED FOR RELEASE TO MEAN ANYTHING. `shield.unblock()` clears the in-memory evidence, and
    without a matching delete here the next flush would merge it straight back off disk and the
    address would be re-convicted on its next request. That is precisely the defect the unblock
    docstring already describes -- a hand brake that did nothing -- and persistence would have
    reintroduced it through the back door.
    """
    if _broken[0] or not key:
        return 0
    try:
        with _connect() as c:
            return c.execute("DELETE FROM slow WHERE k = ?", (str(key)[:64],)).rowcount
    except Exception:
        return 0


def due(now=None):
    """True when it is time to flush. Cheap enough to call on every observed probe."""
    if _broken[0]:
        return False
    now = now or time.time()
    if _last_flush[0] == 0.0:
        _last_flush[0] = now                          # do not flush on the very first request
        return False
    return (now - _last_flush[0]) >= FLUSH_S


def healthy():
    """Whether the store is usable, for the diagnostic endpoint. Never raises."""
    return not _broken[0]


def stats():
    """Row and key counts, for /api/diag and the digest. Zeroes on failure."""
    try:
        with _connect() as c:
            r = c.execute("SELECT COUNT(*), COUNT(DISTINCT k) FROM slow").fetchone()
        return {"rows": r[0], "keys": r[1], "path": DB_PATH, "healthy": healthy()}
    except Exception:
        return {"rows": 0, "keys": 0, "path": DB_PATH, "healthy": False}
