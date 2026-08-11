# -*- coding: utf-8 -*-
"""Live attack feed for the public siege page - redacted at the source.

WHAT THIS IS. An in-memory ring buffer that the telemetry middleware feeds on every request. The
public page polls `GET /api/siege?since=<seq>` and animates what arrives. Near-real-time with no
log parsing and no disk I/O: the delay is the poll interval, not a batch job.

THE REDACTION IS NOT A FEATURE, IT IS THE PRECONDITION. This endpoint is world-readable, so:

  1. AN IP ADDRESS IS PERSONAL DATA (GDPR; CJEU C-582/14 Breyer). "They attacked us" is not a
     lawful basis for publishing it. Every address is truncated to a /24 (IPv4) or /48 (IPv6)
     before it can ever leave this module, and the full value is NEVER stored in the buffer -
     truncation happens on the way IN, so a later bug in the endpoint cannot leak what was never
     kept.

  2. ORDINARY VISITORS ARE IN THE SAME REQUEST STREAM. Only attack-shaped requests are recorded
     at all. A human reading the site never appears, not even anonymised.

  3. A RAW PATH IS AN EXFILTRATION VECTOR. An attacker controls it, and it can carry a query
     string with an email, a token or a session id - which we would then publish. So a path is
     echoed ONLY when it matches the shield's own probe corpus, carries no query string and is
     short. Anything else is shown as its CLASS NAME and the path is discarded.

  4. NO USER, NO SESSION, NO REFERRER, NO USER AGENT. A user agent is attacker-controlled free
     text; publishing it is the same class of mistake as publishing the path.

COST. The buffer is bounded and the snapshot is cached, so a public endpoint cannot be turned
into a way to make our own server work hard - which would be an unusually embarrassing way to be
taken down, given what the page is about.
"""
import os
import re
import threading
import time

MAX_EVENTS = int(os.environ.get("SIEGE_BUFFER", 400))
CACHE_MS = 900                                     # snapshot reuse window
_LOCK = threading.Lock()
_buf = []                                          # newest last
_seq = 0
_counts = {}                                       # class -> count, since start
_sources = set()                                   # redacted /24s seen, for a distinct count
_blocked = 0
_started = time.time()
_cache = {"at": 0.0, "since": None, "payload": None}

# The classes the page draws as lanes. Keys match shield's classifier so one vocabulary is used
# by the detector, the dashboard and this feed.
def _lanes():
    """Derived from the shield's own table so the feed can never advertise a lane the detector
    does not produce, or miss one it does."""
    try:
        from .shield import CLASSES
        return tuple(n for n, _ in CLASSES)
    except Exception:
        return ("wordpress", "php_probe", "admin_panel", "shell_rce", "template",
                "env_secrets", "backup_file", "other")


LANES = _lanes()

# A path may be echoed only if it looks like this: no query, no spaces, short, printable ASCII.
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9._~%/\-\[\]]{0,62}$")


def redact_ip(ip):
    """/24 for IPv4, /48 for IPv6. Applied on the way IN - the full address is never stored."""
    s = str(ip or "").strip()
    if not s:
        return "unknown"
    if ":" in s:                                    # IPv6 -> first three hextets
        parts = [p for p in s.split(":") if p != ""]
        return ":".join(parts[:3]) + "::/48" if parts else "unknown"
    parts = s.split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        return "unknown"
    return "%s.%s.%s.0/24" % (parts[0], parts[1], parts[2])


def safe_path(path, cls):
    """Echo the path only when it cannot carry anything of somebody's. Otherwise the class name."""
    p = str(path or "")
    if "?" in p or "#" in p:
        return None
    if not _SAFE_PATH.match(p):
        return None
    return p


def record(ip, path, cls, blocked, status=0, country=None):
    """Called from the telemetry middleware for ATTACK-SHAPED requests only.

    `cls` is the shield's class name. Anything unrecognised is dropped rather than guessed: a feed
    that invents a category is the same failure the assessment engine refuses to make.
    """
    global _seq, _blocked
    try:
        lane = cls if cls in LANES else ("other" if cls else None)
        if lane is None:
            return
        net = redact_ip(ip)
        ev = {
            "id": 0,
            "lane": lane,
            "net": net,                              # already truncated
            "cc": (country or "")[:2].upper(),
            "path": safe_path(path, lane),           # may be None -> the page shows the class
            "blocked": bool(blocked),
            "t": int(time.time() * 1000),
        }
        with _LOCK:
            _seq += 1
            ev["id"] = _seq
            _buf.append(ev)
            if len(_buf) > MAX_EVENTS:
                del _buf[0:len(_buf) - MAX_EVENTS]
            _counts[lane] = _counts.get(lane, 0) + 1
            _sources.add(net)
            if blocked:
                _blocked += 1
            _cache["payload"] = None                 # invalidate
    except Exception:
        pass                                         # a visualisation must never break a request


def snapshot(since=None):
    """Events after `since`, plus counters. Cached briefly so polling stays cheap."""
    now = time.time()
    with _LOCK:
        if (_cache["payload"] is not None and _cache["since"] == since
                and (now - _cache["at"]) * 1000 < CACHE_MS):
            return _cache["payload"]
        try:
            s = int(since)
        except (TypeError, ValueError):
            s = None
        events = [e for e in _buf if s is None or e["id"] > s]
        if s is None:
            events = events[-60:]                    # a first-time viewer gets recent history
        payload = {
            "seq": _seq,
            "events": events,
            "counts": dict(_counts),
            "sources": len(_sources),
            "blocked": _blocked,
            "uptime_s": int(now - _started),
            "live": True,
        }
        _cache.update({"at": now, "since": since, "payload": payload})
        return payload


def stats():
    with _LOCK:
        return {"buffered": len(_buf), "seq": _seq, "sources": len(_sources), "blocked": _blocked}
