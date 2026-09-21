"""asset_trace.py -- did a BROWSER ENGINE actually render the page this address asked for?

ONE-WAY POSITIVE, AND THAT IS THE WHOLE DESIGN. This ledger may CONFIRM that a browser engine
rendered a page. It may NEVER be used to conclude that something is a script. `assets >= MIN_ASSETS`
is evidence of a browser; `assets == 0` is evidence of NOTHING AT ALL, and any caller that treats a
zero as incriminating is wrong.

WHY ZERO PROVES NOTHING, stated once so nobody has to re-derive it:
  * The FIRST navigation from any address legitimately has no assets behind it yet. The ledger is
    written as the subresources arrive, which is after the navigation was already logged.
  * A cached repeat visit fetches nothing. A browser with a warm disk cache, or a registered
    service worker serving from its own cache, makes zero requests for the bundle it already has.
  * A page served fully inline fetches nothing. So does a 404, a redirect, a JSON route, and any
    request a person made by pasting a URL to a non-HTML resource.
That is three enormous legitimate populations at zero, which is exactly the "absence of evidence is
never a finding" rule this estate already writes down. `tests/test_asset_trace.py` asserts the
one-way property across every path rather than grepping for a word.

AND BECAUSE IT ONLY EVER POINTS ONE WAY, IT CANNOT PRODUCE A FALSE POSITIVE AGAINST A REAL PERSON.
The worst thing a wrong answer here can do is leave an address in the unjudged column, which is
where it already was. That asymmetry is the reason the signal is worth having at all.

WHAT IT IS WORTH, HONESTLY. It confirms a BROWSER ENGINE, not a human. A full headless browser
driven by Playwright or Puppeteer fetches the CSS, the bundle and the icons exactly as Chrome does,
because it IS Chrome, and this signal will confirm it. What it defeats is the large and cheap
population of scrapers built on a plain HTTP client that fetches the HTML and stops. Claiming more
than that would be the unsubstantiated comparative claim the estate refuses to make elsewhere.

NOTHING HERE ENFORCES. No block, no tarpit, no score, no rule, no firewall, no persistence. The
module holds two dicts and returns an integer. A caller that wanted to enforce on this would have
to invent the decision in its own file, where a reviewer can see it.

NO NEW LOG VOLUME. `note()` writes nothing anywhere. The reason static assets were dropped from the
event log in the first place was that they would drown it, and that reason has not changed: this
records the fact IN MEMORY and the navigation line carries the derived count as `av`. An asset
still produces zero log lines, asserted by test.

VENDORABLE. Standard library only, and only `threading` and `time` at that. No relative import, no
package assumption, no regex: the ledger deliberately does NOT decide what counts as an asset,
because the EMITTER already has that predicate (telemetry.SKIP_PATH_PAT) and a second copy of it
here would be a second home for one decision. The caller says "this was an asset"; the ledger
counts. `perseus/client.py` may not import this file -- its import floor is exactly seven stdlib
modules and that floor is a security control -- so the four constants are restated there and
`tests/test_asset_trace.py::test_the_sidecar_and_this_module_agree_on_the_constants` reads both
files off disk with `ast` and fails the build if they ever drift.
"""
import threading
import time

# ---------------------------------------------------------------------------------------------
# THE FOUR CONSTANTS. Each one says WHY it is the number it is, because the next person to read
# this will otherwise tune it by feel.
# ---------------------------------------------------------------------------------------------

# HOW LONG AFTER A NAVIGATION AN ASSET STILL COUNTS AS BELONGING TO IT.
# Deliberately generous, because every error in the generous direction costs nothing (the worst
# case is confirming a browser that was in fact a browser two minutes ago) and every error in the
# tight direction silently deletes the signal for exactly the visitors who most deserve the benefit
# of the doubt: a phone on a bad mobile connection, a lazy-loaded hero video, a font fetched only
# once a deferred stylesheet has parsed, a service worker registering after first paint. 120s is
# roughly ten times a bad cold load on this site and still far shorter than any plausible session,
# so a repeat visitor an hour later is measured afresh rather than inheriting an old answer.
WINDOW_S = 120

# THE FLOOR THAT CONFIRMS A BROWSER ENGINE.
# MEASURED, NOT GUESSED. webapp/frontend/dist/index.html references, on a cold production page
# view: /assets/index-*.css, /assets/index-*.js, /manifest.webmanifest, /favicon.ico and /icon.svg,
# and main.jsx then registers /sw.js. That is five to six distinct same-origin subresources that
# EVERY engine fetches; the Google-hosted fonts are third-party and never reach our box, so they
# are not counted on. Three is therefore comfortably below what the real page produces, which
# matters because this signal must not start missing real browsers the moment a build splits or
# merges a chunk. It is also above one and two, which is what an opportunistic scraper that
# follows the first <script> or <link> it sees would reach. A client that fetches the HTML and
# stops -- which is what the cheap scraper population actually does -- reaches zero.
MIN_ASSETS = 3

# HARD CEILING ON ADDRESSES HELD. A FLOOD MUST NOT TURN THIS INTO THE OUTAGE.
# 4096 addresses x MAX_PATHS_PER_IP entries is the entire worst case, a few megabytes, on a 4 GB
# droplet that also runs the VPN, the proxy and four other stacks. A scanner rotating source
# addresses is the expected attack on any in-memory map keyed by IP, so the bound is enforced on
# every write and not aspirationally: oldest-touched addresses are evicted first, in batches, so
# the eviction cost stays amortised instead of sorting the whole table on every request of a flood.
MAX_TRACKED = 4096

# CEILING ON DISTINCT PATHS HELD PER ADDRESS.
# The only question ever asked of this ledger is "is the count at or above MIN_ASSETS", so holding
# more than a handful buys nothing and an unbounded per-address set is the same flood defect one
# level down. 16 is five times the floor, which leaves room for the window to be full of a genuine
# multi-page visit without the count ever being capped below a decision it could have changed.
MAX_PATHS_PER_IP = 16

# How often the whole table is swept for expired addresses when it is NOT under pressure. Pruning
# happens ON WRITE, never on a timer: a background thread would be a thread to leak, and a leaked
# thread in the request path of every site on the box is a worse failure than the memory it saves.
# Under pressure (over MAX_TRACKED) the sweep runs regardless of this interval.
_SWEEP_S = 30

# Bounds on what is stored, so a hostile path or a malformed address cannot inflate a row.
_MAX_IP_LEN = 64
_MAX_PATH_LEN = 160

_LOCK = threading.Lock()
_SEEN = {}          # ip -> {path: last_seen_ts}
_LAST = {}          # ip -> last_seen_ts, so eviction never has to scan the inner dicts
_SWEPT = [0.0]      # last full sweep, in a list so it is mutable under the lock


def _prune_locked(now):
    """Drop what is out of the window, then enforce the ceiling. Caller holds _LOCK.

    Two separate jobs and they are deliberately not merged: expiry is correctness of the MEMORY
    BOUND only (evidence() filters by the window itself, so a stale entry can never be counted),
    and eviction is the flood defence. Eviction takes a batch rather than the single oldest entry
    so that a sustained flood pays for a sort once every few hundred writes instead of once per
    write, which is the difference between a bound and a self-inflicted slowdown.
    """
    pressure = len(_SEEN) > MAX_TRACKED
    if not pressure and (now - _SWEPT[0]) < _SWEEP_S:
        return
    _SWEPT[0] = now
    for ip in [k for k, t in _LAST.items() if (now - t) >= WINDOW_S]:
        _SEEN.pop(ip, None)
        _LAST.pop(ip, None)
    if len(_SEEN) > MAX_TRACKED:
        keep = MAX_TRACKED - (MAX_TRACKED // 8)
        drop = len(_SEEN) - keep
        for ip, _t in sorted(_LAST.items(), key=lambda kv: kv[1])[:drop]:
            _SEEN.pop(ip, None)
            _LAST.pop(ip, None)


def note(ip, path, now=None):
    """Record that `ip` fetched the static asset `path`. Writes NOTHING anywhere. Never raises.

    Called from the emitter at the exact point where a static asset is currently dropped from the
    log, so the fact survives while the log line still does not. Distinct paths only: a browser
    re-requesting one stylesheet is one asset, not ten, or a single image on a retry loop would
    confirm a browser on its own.

    `now` is injectable so the window and the eviction can be tested without sleeping. A test that
    depends on a real clock is the coin flip that teaches the operator to re-run rather than read.
    """
    try:
        if not ip or not path:
            return
        now = time.time() if now is None else float(now)
        key = str(path)[:_MAX_PATH_LEN]
        who = str(ip)[:_MAX_IP_LEN]
        with _LOCK:
            paths = _SEEN.get(who)
            if paths is None:
                paths = {}
                _SEEN[who] = paths
            paths[key] = now
            _LAST[who] = now
            # Per-address window expiry, every write. Bounded by MAX_PATHS_PER_IP + 1, so this is
            # a fixed small cost and not a scan.
            for p in [p for p, t in paths.items() if (now - t) >= WINDOW_S]:
                paths.pop(p, None)
            if len(paths) > MAX_PATHS_PER_IP:
                excess = len(paths) - MAX_PATHS_PER_IP
                for p, _t in sorted(paths.items(), key=lambda kv: kv[1])[:excess]:
                    paths.pop(p, None)
            _prune_locked(now)
    except Exception:
        # FAIL OPEN. An error here is a fact about us, not about the client, and it must not reach
        # the request this is observing.
        return


def evidence(ip, now=None):
    """-> how many DISTINCT assets this address fetched inside WINDOW_S. Never raises, 0 on error.

    ZERO IS NOT A FINDING. It means this address has fetched no asset we recorded in the last two
    minutes, which is the normal state of a first navigation, a cached repeat visit, an inline
    page, an API caller and an address we simply have no memory of. The caller's ONLY permitted
    reading of the return value is `>= MIN_ASSETS -> confirmed browser`.

    Capped at MAX_PATHS_PER_IP by construction, which is five times the floor: the number is a
    decision input, not a traffic statistic, and must never be reported as one.
    """
    try:
        now = time.time() if now is None else float(now)
        with _LOCK:
            paths = _SEEN.get(str(ip)[:_MAX_IP_LEN])
            if not paths:
                return 0
            return sum(1 for t in paths.values() if (now - t) < WINDOW_S)
    except Exception:
        return 0


def confirmed(ip, now=None):
    """-> True when this address has CONFIRMED a browser engine. Never raises, False on error.

    The one reading of `evidence()` that is allowed, in one place, so no caller has to restate the
    comparison and none of them can drift into inverting it. False means NOT CONFIRMED, which is
    not the same as "this is a script" and must never be rendered as one.
    """
    try:
        return evidence(ip, now=now) >= MIN_ASSETS
    except Exception:
        return False


def tracked():
    """-> how many addresses the ledger currently holds. For tests and diagnostics only."""
    try:
        with _LOCK:
            return len(_SEEN)
    except Exception:
        return 0


def reset():
    """Empty the ledger. For tests. Never raises."""
    try:
        with _LOCK:
            _SEEN.clear()
            _LAST.clear()
            _SWEPT[0] = 0.0
    except Exception:
        return
