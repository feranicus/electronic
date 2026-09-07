"""The ONLY file copied into each project. Stateless, stdlib-only, ~40 lines of logic.

COPY THIS, NOT THE BRAIN. Everything that decides -- scoring, the panel, promotion, abuse
reporting -- lives in the hub, in one place, and changes there. This file only READS what the hub
published. It has no state of its own to drift, no thresholds of its own to go stale, and no
network call, so it cannot introduce a failure mode into a request path.

HOW IT REACHES THE APP: the hub writes `perseus_blocklist.json` to a volume every project already
mounts. A file cannot be down, cannot rate-limit us, and needs no token. That is deliberate: an
HTTP call to a central service would put the hub in the blast radius of every site it protects.

FAILS OPEN, ALWAYS. A missing file, a corrupt file, a permission error, a clock problem: every one
of them returns "allow". The sibling incident cost money; a defence that takes six sites down
because one JSON file was half-written would cost more. There is exactly one safe direction here.

USAGE (three lines in any FastAPI app):

    from perseus_client import check
    ok, retry, why = check(client_ip, request.url.path)
    if not ok: return JSONResponse({"error": "rate limited"}, 429, {"Retry-After": str(retry)})
"""
import json
import os
import re
import threading
import time

BLOCKLIST = os.environ.get("PERSEUS_BLOCKLIST", "/var/log/colt/perseus_blocklist.json")
RELOAD_S = int(os.environ.get("PERSEUS_RELOAD_S", "30"))
ENABLED = os.environ.get("PERSEUS_ENABLED", "1") != "0"

_LOCK = threading.Lock()
_CACHE = {"mtime": 0.0, "loaded": 0.0, "patterns": [], "thresholds": {}, "cycle": 0}


def _load():
    """Re-read only when the file changed, and at most every RELOAD_S. A blocklist consulted on
    every request must never become a disk read on every request."""
    now = time.time()
    if now - _CACHE["loaded"] < RELOAD_S:
        return _CACHE
    with _LOCK:
        _CACHE["loaded"] = now
        try:
            st = os.stat(BLOCKLIST)
            if st.st_mtime == _CACHE["mtime"]:
                return _CACHE
            with open(BLOCKLIST, encoding="utf-8") as fh:
                doc = json.load(fh)
            pats = []
            for p in doc.get("patterns") or []:
                try:
                    pats.append((p.get("id"), re.compile(p["pattern"], re.I)))
                except Exception:
                    continue        # one bad pattern must not discard the rest
            _CACHE.update(mtime=st.st_mtime, patterns=pats, cycle=doc.get("cycle", 0),
                          thresholds=doc.get("thresholds") or {})
        except Exception:
            pass                    # keep whatever we had; never clear on a read failure
    return _CACHE


def check(ip, path):
    """(allowed, retry_after, reason). Never raises, never blocks on IO, fails OPEN."""
    if not ENABLED:
        return True, 0, ""
    try:
        c = _load()
        for rid, rx in c["patterns"]:
            if rx.search(path or ""):
                return False, 60, "perseus rule %s (cycle %s)" % (rid, c.get("cycle"))
    except Exception:
        return True, 0, ""
    return True, 0, ""


def thresholds():
    """The hub's current numbers, for a project that wants to use them for its own rate limiting
    instead of hard-coding its own. Empty dict means 'the hub has not published yet': the caller
    keeps its committed defaults rather than treating absence as zero."""
    try:
        return dict(_load().get("thresholds") or {})
    except Exception:
        return {}


def status():
    c = _load()
    return {"enabled": ENABLED, "file": BLOCKLIST, "cycle": c.get("cycle"),
            "patterns": len(c.get("patterns") or []),
            "age_s": int(time.time() - c["mtime"]) if c["mtime"] else None}
