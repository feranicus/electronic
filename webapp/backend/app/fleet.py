"""Is the security sidecar actually connected to every project, and is anything watching them?

WHY THIS EXISTS. The operator: "after implementing our security guardrails I do not get nothing on
to my telegram from jev.best from jobhuntwow from polara? who visited? why?" He was right, and the
answer was worse than a bug:

  * `perseus_client.py` was COPIED into jobhuntwow and jev.best and imported by NOTHING. Correct
    code, wired to no request path. This repository already records the rule -- a control that is
    correct and unreachable is not a control -- and I broke it while shipping the thing.
  * even wired, the client is ENFORCEMENT ONLY. It reads a blocklist and answers allow/deny. It has
    no telemetry and no alerting, so it was never going to say who visited jev.best.
  * every alert he does receive comes from `app/notify.py` + `alerts.py`, which live in colt-web and
    nowhere else. The other projects have no equivalent, so there was no path for a message to
    travel down. Nothing was broken; nothing was built.

So this module answers the question with EVIDENCE, per project, and distinguishes the three states
that look identical from a dashboard and mean completely different things:

    LIVE      the project is logging AND the sidecar is beating   -> protected and observed
    OBSERVED  the project is logging, no sidecar heartbeat        -> we can see it, it is unguarded
    SILENT    no logs at all in the window                        -> WE ARE BLIND, not "it is safe"

The third is the one that matters. A dashboard that renders "no attacks" for a project that is not
shipping a single line is the same defect as a backup that reports success while copying nothing.
"""
import json
import os
import time

BEAT_DIR = os.environ.get("PERSEUS_BEATS", "/var/log/colt/perseus_beats")
EVENTS = os.environ.get("EVENTS_LOG", "/var/log/colt/events.log")
# EVERY LOG THIS CONTAINER CAN SEE. klima and s4biz write to their OWN volumes, so reading only the
# shared one reported them as unseeable -- a statement about where we looked, not about them.
# docker-compose.web.yml mounts those volumes read-only at these paths; a path that is not mounted
# is skipped, so the list is safe on a box where a project does not exist.
# EMPTY BY DEFAULT, AND THAT IS THE POINT. The first version mounted klima's and s4biz's event
# volumes into colt-web with `external: true` -- which made cybergod UNDEPLOYABLE anywhere those
# volumes are absent, and staging proved it by refusing the deploy. A status page is never worth
# coupling a deploy to a sibling project. Set EXTRA_EVENT_LOGS on a host where they ARE mounted.
EXTRA_EVENTS = [p for p in os.environ.get("EXTRA_EVENT_LOGS", "").split(":") if p]
BLOCKLIST = os.environ.get("PERSEUS_BLOCKLIST", "/var/log/colt/perseus_blocklist.json")

# The fleet, and the log `service` each one stamps. Committed rather than discovered: a project
# that stops reporting must show up as SILENT, and a list built from whatever happens to be in the
# log can never notice an absence -- it would simply stop mentioning it.
PROJECTS = [
    {"key": "colt-web", "name": "cybergod.ai", "service": "colt-web"},
    {"key": "jhw-web", "name": "jobhuntwow.com", "service": "jhw-web"},
    # own_log: this project writes to ITS OWN event volume, which colt-web does not mount. Absence
    # of its lines here is a statement about where this container can look, NOT about the project.
    {"key": "polara-web", "name": "klimaanlage-preise.de", "service": "polara-web",
     "own_log": "polara_events"},
    {"key": "jev-web", "name": "jev.best", "service": "jev-web"},
    {"key": "s4biz-web", "name": "s4biz.io", "service": "s4biz-web", "own_log": "s4biz_events"},
]

STALE_BEAT_S = 15 * 60      # the client beats every 60s; 15 min of silence is a dead sidecar
WINDOW_S = 24 * 3600


def _beats():
    """One heartbeat file per service, written by perseus_client. ABSENCE IS THE SIGNAL: it means
    that project is not running the client, which is exactly the state we were blind to."""
    out = {}
    try:
        for fn in os.listdir(BEAT_DIR):
            if not fn.endswith(".json") or fn.startswith("."):
                continue
            try:
                with open(os.path.join(BEAT_DIR, fn), encoding="utf-8") as fh:
                    d = json.load(fh)
                if isinstance(d, dict) and d.get("service"):
                    out[d["service"]] = d
            except Exception:
                continue                 # one unreadable beat must not hide the others
    except Exception:
        pass                             # no directory yet == no sidecar has ever run
    return out


def _loki_query_url():
    """LOKI_URL in colt-web's .env is the PUSH endpoint the deploy writes
    (http://videodead-loki-1:3100/loki/api/v1/push). The query API is the same host, other path."""
    u = os.environ.get("LOKI_URL", "")
    return (u.split("/loki/api/v1/")[0] + "/loki/api/v1/query_range") if "/loki/api/v1/" in u else ""


def _num(name, default, cast):
    """A config value must never be able to stop this MODULE FROM IMPORTING.

    `int(os.environ.get(...))` at module level looks harmless and is not: the route does
    `from . import fleet` inside the handler, so an empty or non-numeric env var raises ValueError
    on EVERY request and the page shows nothing but "Could not read the fleet status." -- with no
    hint that the cause is a typo in a .env file. Fall back to the default and SAY SO on stdout,
    which promtail ships to Loki, so the next person reads a cause instead of guessing at one.
    """
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return cast(raw)
    except Exception:
        print('{"evt":"fleet_config_bad","name":"%s","value":"%s","using":"%s"}'
              % (name, str(raw)[:40], default), flush=True)
        return default


LOKI_TIMEOUT_S = _num("PERSEUS_LOKI_TIMEOUT", 3.0, float)
# Raw lines pulled per own-log project per window. Bounded because a status page must not be a
# lever for making our own server work; if a project genuinely exceeds it the counts are reported
# as a FLOOR rather than silently understated (see _loki_events).
LOKI_EVENT_LIMIT = _num("PERSEUS_LOKI_LIMIT", 2000, int)
# Traffic counts do not need per-minute freshness, and every refresh is a real query against a
# shared Loki. Five minutes, refreshed off the request path.
LOKI_EVENT_TTL_S = _num("PERSEUS_LOKI_TTL", 300, int)
# DEFAULT OFF. THIS IS A RETREAT TO THE LAST STATE THAT DEMONSTRABLY WORKED.
#
# The traffic-from-Loki lookup is the ONLY thing the last two ships put on the request path, and
# the Admin page has been dead for both of them. It has never once been observed working. Three
# rules in CLAUDE.md say what to do here and I ignored all of them: measure before naming a cause,
# an optional lookup may never make a page worse, and a feature nobody can see is not a feature.
#
# With this OFF, status() takes exactly the path of the version the operator last saw working:
# klima and s4biz render `elsewhere` with `active` sidecars proven by their stdout heartbeat, which
# was already working in production. The counts go back to being honestly unavailable rather than
# dishonestly absent.
#
# It is turned back on -- per box, no redeploy -- once the fleet telemetry below shows what the
# endpoint is actually doing:  python set_secret.py PERSEUS_LOKI_EVENTS   (value: 1)
LOKI_EVENTS_ON = os.environ.get("PERSEUS_LOKI_EVENTS", "0") == "1"
_LOKI_CACHE = {"ts": 0.0, "beats": {}}
_LOKI_EVENTS = {"ts": 0.0, "rows": [], "ok": False, "partial": False, "busy": False}
# Tried in order; the FIRST that returns anything wins. See _loki_beats for why this is a list.
LOKI_BEAT_SELECTORS = [s for s in os.environ.get(
    "PERSEUS_LOKI_SELECTORS", '{container=~".+"}:{job=~".+"}:{service_name=~".+"}').split(":") if s]

# --------------------------------------------------------------------------------- THE SOC HALF
# EVERYTHING ABOVE ANSWERS "CAN WE SEE THIS PROJECT". NONE OF IT ANSWERS "IS ANYTHING STOPPED".
# The operator was told, correctly, that this page is observation and almost nothing on it is
# enforcement. The evidence was on the page the whole time and nobody read it as a finding: every
# row said `enforcing cycle 0`. hub.cycle() sets rs["cycle"] to 1 on its FIRST success, so cycle 0
# on all five rows means no cycle has ever completed -> publish() never wrote a blocklist ->
# perseus_client.check() iterates an EMPTY pattern list on all five sites. `live` was true and
# irrelevant. So the same three facts get asked of the security posture:
#
#   IS ANYTHING ENFORCED   the sidecar's own beat carries the ruleset cycle it LOADED; the
#                          published file carries how many rules that cycle contains.
#   HAS THE BRAIN RUN      `evt=perseus_publish`, printed by perseus/hub.py.
#   WOULD AN ATTACK REACH  can colt-web read this project's lines at all -- watch() and this page
#   THE OPERATOR           read the SAME rows, so the question is already answered, in the wrong
#                          vocabulary. Said in words here.
#
# `evt=perseus_publish` is printed to STDOUT and nowhere else -- the hub does not write the shared
# events log -- so Loki is the only place it can be read from, and THE LINE CARRIES NO TIMESTAMP OF
# ITS OWN. This lookup therefore reports a COUNT over a window and never "the latest line":
# _loki_fetch merges several streams and only the first is guaranteed newest-first, so reading
# rows[0] as "the most recent publish" would be an ordering assumption dressed up as a measurement.
# WHEN the last successful publish happened is answered by the blocklist file's own mtime, which
# _cycle() already reads -- one reader of that file, not two.
#
# DEFAULT OFF, inheriting the traffic lookup's setting, for the reason written on LOKI_EVENTS_ON
# above: a Loki query on this request path has taken the page down twice, and a feature nobody has
# watched working is off. It gets its OWN name so it can be turned on alone, per box, no redeploy:
#     python set_secret.py PERSEUS_LOKI_PUBLISH   (value: 1)
LOKI_PUBLISH_ON = os.environ.get(
    "PERSEUS_LOKI_PUBLISH", os.environ.get("PERSEUS_LOKI_EVENTS", "0")) == "1"
PUBLISH_LOOKBACK_S = _num("PERSEUS_PUBLISH_LOOKBACK", 7 * 24 * 3600, int)
PUBLISH_TTL_S = _num("PERSEUS_PUBLISH_TTL", 600, int)
# `lookup` is an ENUM KEY and is never translated -- the label is chosen at render time, because
# translating a key makes rows silently vanish. The counts are None until a query has actually
# COMPLETED: "we have not asked yet", "we asked and Loki did not answer" and "Loki answered, there
# were none" are three different facts and this module exists to keep them apart.
_PUBLISH = {"ts": 0.0, "busy": False,
            "val": {"lookup": "pending", "runs": None, "ok": None, "failed": None,
                    "cycle": None, "err": None}}


def _loki_beats():
    """The heartbeat of a project whose beat FILE this container cannot reach.

    klima and s4biz write their heartbeat beside their OWN event log, on a volume colt-web does not
    mount and must not -- that `external:` coupling is exactly what the staging gate refused, and a
    status page is never worth making cybergod's deploy depend on a sibling project. But
    `perseus_client._beat()` also PRINTS the beat to stdout, and this box's promtail ships every
    container's stdout to the SAME Loki. So the beat is OBSERVABLE even where the file is not, which
    is the same accident that made the jobhuntwow abuse reconstructable, used deliberately.

    THE UNPROVEN PART, STATED RATHER THAN HIDDEN: the label scheme of that promtail is not verified
    from here, and this repository has already paid a week for querying a label that was never
    deployed. So several candidate selectors are tried and the first that returns anything wins; the
    line filter does the real work because "perseus_beat" is a rare string. If NONE answers, this
    returns {} and the caller degrades to exactly the previous behaviour -- it can make the page
    more accurate, never less.
    """
    now = time.time()
    if now - _LOKI_CACHE["ts"] < 60:
        return _LOKI_CACHE["beats"]
    _LOKI_CACHE["ts"] = now                       # stamp first: a dead Loki must not be retried per request
    rows, _answered = _loki_fetch('|= "perseus_beat"', now - STALE_BEAT_S, 200)
    found = {}
    for d in rows:
        if d.get("evt") == "perseus_beat" and d.get("service"):
            prev = found.get(d["service"]) or {}
            if int(d.get("ts") or 0) >= int(prev.get("ts") or 0):
                found[d["service"]] = d
    _LOKI_CACHE["beats"] = found
    return found


def _loki_fetch(line_filter, start_ts, limit):
    """Parsed JSON lines from the shared Loki, newest first.

    Returns (rows, ANSWERED). **`answered` is not `len(rows)`.** "Loki says this project sent
    nothing" and "Loki never answered" are different facts, and rendering the second as a zero is
    the exact defect this module exists to prevent -- it is the logship failure, on a dashboard.

    ONE query implementation, used by the heartbeat lookup AND the traffic lookup, so the badge and
    the numbers beside it can never disagree about which Loki they asked or how.
    """
    base = _loki_query_url()
    if not base:
        return [], False
    import urllib.parse
    import urllib.request
    now = time.time()
    answered = False
    for sel in LOKI_BEAT_SELECTORS:
        # Bound BEFORE the try, because `if rows:` below is read outside it. It happens to be
        # unreachable on the failing path today (every except continues), but a name whose binding
        # depends on which branch of a try ran is one edit away from a NameError -- and a NameError
        # here is another 500 on the page this function is not allowed to break.
        rows = []
        try:
            url = "%s?%s" % (base, urllib.parse.urlencode({
                "query": "%s %s" % (sel, line_filter),
                "start": "%d000000000" % int(start_ts),
                "end": "%d000000000" % int(now),
                "limit": limit, "direction": "backward"}))
            with urllib.request.urlopen(url, timeout=LOKI_TIMEOUT_S) as r:
                doc = json.loads(r.read().decode("utf-8", "replace"))
            answered = True
            # THE PARSING STAYS INSIDE THE try. It used to sit after it, so an unexpected envelope
            # (`doc` not a dict) raised AttributeError straight out of this function, past every
            # caller, into a 500 -- and the whole Fleet page rendered "Could not read the fleet
            # status". An optional lookup must not be able to take the page down.
            for stream in (doc.get("data") or {}).get("result") or []:
                for _ts, line in stream.get("values") or []:
                    # The container's stdout line may carry a prefix; the JSON starts at the brace.
                    try:
                        d = json.loads(line[line.index("{"):])
                    except Exception:
                        continue
                    if isinstance(d, dict):
                        rows.append(d)
        except Exception:
            continue                      # this selector (or this Loki) did not answer; try the next
        if rows:
            return rows, True             # this selector works; stop probing the others
    return [], answered


def _loki_events(block=False):
    """The TRAFFIC of a project whose event volume this container does not mount.

    THE ZERO THAT PROMPTED THIS. klima and s4biz showed `0 requests · 0 attack-shaped · 0 visitors
    · 0 alerts` while both were plainly serving traffic, because every count on this page came from
    a FILE on the shared volume and their lines are on their own. Worse than the cosmetics: the
    SAME read feeds `watch()`, so those two projects could not page the operator about a scanner.
    That is not a smaller version of cybergod's security; it is none of it.

    Both promtails already push to the SAME Loki as everything else on this box, so their `evt=http`
    lines have been there the whole time. Reading them costs no volume mount, and therefore none of
    the `external:` deploy coupling that staging refused.

    Returns (rows, ok, partial). PARTIAL matters: the fetch is bounded, so a project that really
    exceeds the limit would otherwise be reported with a confident, wrong, too-small number -- the
    caller says "at least N" instead.

    THE PAGE MUST NEVER WAIT FOR THIS, and the first version made it wait. Two projects x three
    candidate selectors x a 3s timeout is up to 18 SECONDS of blocking on a cold cache, on a query
    far heavier than the heartbeat's (24 hours instead of 15 minutes, 5000 lines instead of 200).
    The admin page stopped loading at all. The comment on the beat cache four functions up already
    said it -- "a status page that hangs is its own outage" -- and this ignored it.

    So the request path only ever READS the cache; a daemon thread refreshes it. A cold cache
    renders `elsewhere` for one page load and the numbers appear on the next. The alerting loop
    passes block=True, because it runs in the background and has the time the page does not.
    """
    own = [p["service"] for p in PROJECTS if p.get("own_log")]
    now = time.time()
    if not own or not LOKI_EVENTS_ON:
        return [], False, False
    if now - _LOKI_EVENTS["ts"] < LOKI_EVENT_TTL_S:
        return _LOKI_EVENTS["rows"], _LOKI_EVENTS["ok"], _LOKI_EVENTS["partial"]
    if not block:
        _loki_events_async(own)
        return _LOKI_EVENTS["rows"], _LOKI_EVENTS["ok"], _LOKI_EVENTS["partial"]
    _loki_events_now(own)
    return _LOKI_EVENTS["rows"], _LOKI_EVENTS["ok"], _LOKI_EVENTS["partial"]


def _loki_events_async(own):
    """Refresh in the background, at most one refresh in flight."""
    if _LOKI_EVENTS.get("busy"):
        return
    _LOKI_EVENTS["busy"] = True
    try:
        import threading
        threading.Thread(target=_loki_events_now, args=(own,), daemon=True).start()
    except Exception:
        _LOKI_EVENTS["busy"] = False      # could not spawn: the page still renders, just without it


def _loki_events_now(own):
    """The actual fetch. Wrapped whole: nothing in here may reach a caller as an exception."""
    now = time.time()
    _LOKI_EVENTS["ts"] = now              # stamp first, as above
    rows, ok, partial, seen_keys = [], False, False, set()
    try:
        for svc in own:
            # Filter on the bare service NAME, never on `"service": "x"`: json.dumps separator
            # spacing is not something to guess at inside a substring filter, and guessing wrong
            # fails silently and looks exactly like innocence. The line is parsed and the field
            # checked properly below.
            got, answered = _loki_fetch('|= "%s"' % svc, now - WINDOW_S, LOKI_EVENT_LIMIT)
            ok = ok or answered
            if len(got) >= LOKI_EVENT_LIMIT:
                partial = True
            # The heartbeat is on stdout too and carries the same service name, so it comes back
            # with this query. Drop it: _loki_beats already owns that question, it is not traffic,
            # and ~1440 beats a day would eat the line budget real requests need.
            # DEDUPE, because one request can produce TWO stdout lines: the project's own telemetry
            # AND the perseus sidecar's observe(). Counting both would double every number on the
            # page -- a confident wrong figure, worse than the zero it replaces. The key is the
            # request itself; `ts` is whole seconds, so two identical requests from one address in
            # the same second collapse into one. A known, bounded UNDERCOUNT in the noisiest
            # direction only, stated here rather than discovered later.
            for d in got:
                if d.get("service") != svc or d.get("evt") == "perseus_beat":
                    continue
                k = (d.get("evt"), d.get("ts"), d.get("ip"), d.get("method"), d.get("path"))
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                rows.append(d)
        _LOKI_EVENTS["rows"], _LOKI_EVENTS["ok"], _LOKI_EVENTS["partial"] = rows, ok, partial
    except Exception:
        pass                              # a refresh that fails leaves the previous answer standing
    finally:
        _LOKI_EVENTS["busy"] = False
    return _LOKI_EVENTS["rows"], _LOKI_EVENTS["ok"], _LOKI_EVENTS["partial"]


def _all_beats():
    """File beats, plus Loki-observed beats ONLY for projects whose beat file we cannot reach.

    The file is authoritative where it exists: colt-web writes it and reads it, so it cannot lie
    about itself. Loki is consulted only to answer the question the file physically cannot."""
    out = _beats()
    if any(p.get("own_log") and p["service"] not in out for p in PROJECTS):
        for svc, d in _loki_beats().items():
            out.setdefault(svc, d)
    return out


def _tail_events(limit_bytes=4_000_000, block=False, loki_rows=None):
    """Every event this container can reach: the mounted logs FIRST, then Loki for the projects
    whose log is not among them.

    The Loki rows are merged HERE, in the one function both `status()` (the counts) and `since()`
    -> `watch()` (the alerting) already call, so the page and the pager cannot end up looking at
    different traffic. A file that IS mounted always wins: it needs no network and it is still
    readable when Loki is the thing that is down, which is exactly when this page gets opened.

    `block` is passed straight through: the HTTP request path must never wait on Loki, the
    background alerting loop must, because an alert computed from an empty cache is not a quiet
    project -- it is a scanner nobody was told about.

    `loki_rows` lets a caller that has ALREADY read the cache hand its snapshot in, so one response
    is built from ONE snapshot. status() needs that: it reads the cache for the counts and again for
    the badges, and a background refresh landing between the two reads would let a service be listed
    as readable while its numbers came from the older, emptier snapshot -- `live` with zeros, the
    exact confident-wrong-number this page exists to prevent."""
    rows = []
    for path in [EVENTS] + EXTRA_EVENTS:
        rows.extend(_tail_one(path, limit_bytes))
    seen = {r.get("service") for r in rows}
    if any(p.get("own_log") and p["service"] not in seen for p in PROJECTS):
        rows.extend(loki_rows if loki_rows is not None else _loki_events(block=block)[0])
    return rows


def _tail_one(EVENTS, limit_bytes=4_000_000):
    """Read the tail of the shared events log. Every project on this box writes there, so one read
    answers 'who is alive' for all of them without a Loki round trip -- and it still works when
    Loki is down, which is precisely when a status page is being looked at."""
    rows = []
    try:
        size = os.path.getsize(EVENTS)
        with open(EVENTS, "rb") as fh:
            if size > limit_bytes:
                fh.seek(size - limit_bytes)
                fh.readline()            # drop the partial first line
            cutoff = time.time() - WINDOW_S
            for raw in fh:
                try:
                    d = json.loads(raw.decode("utf-8", "replace"))
                except Exception:
                    continue
                if isinstance(d, dict) and (d.get("ts") or 0) >= cutoff:
                    rows.append(d)
    except Exception:
        pass
    return rows


def _cycle():
    """THE ONE READER OF THE PUBLISHED BLOCKLIST. Every enforcement claim on this page comes from
    here; a second reader would be a second answer to "how many rules are armed".

    `patterns: 0` ON THE FAILURE PATH WAS THE DEFECT. An unreadable file returned a confident zero,
    which renders as "no rules published" -- indistinguishable from "the file is not mounted in this
    container" and from "the JSON is corrupt". Those are three different states and only one of them
    is about perseus. Unreadable now returns None everywhere and NAMES the error, which is the same
    rule the project rows already obey.

    `enforcing` is the question the operator actually asked, answered here rather than re-derived by
    each caller: a blocklist is only enforcing if a cycle has completed AND that cycle armed at
    least one pattern. cycle 0, or cycle 4 with an empty pattern list, both block nothing.
    """
    out = {"cycle": None, "patterns": None, "age_s": None, "generated": None,
           "readable": False, "enforcing": False, "path": BLOCKLIST, "err": None}
    try:
        with open(BLOCKLIST, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict):
            raise ValueError("the blocklist is not a JSON object")
        pats = d.get("patterns")
        out["cycle"] = d.get("cycle")
        # A `patterns` key that is not a LIST is not a count. len() on a dict would return a
        # plausible number for a document we did not understand, which is worse than saying so.
        out["patterns"] = len(pats) if isinstance(pats, list) else None
        out["generated"] = d.get("generated")
        out["readable"] = True
        try:
            out["age_s"] = int(time.time() - os.path.getmtime(BLOCKLIST))
        except Exception:
            out["age_s"] = None       # we read the content but not the mtime; do not invent one
        out["enforcing"] = bool((out["cycle"] or 0) >= 1 and (out["patterns"] or 0) > 0)
    except Exception as exc:
        out["err"] = repr(exc)[:160]
    return out


def _publish(block=False):
    """Has the BRAIN run? Counted from `evt=perseus_publish` over PUBLISH_LOOKBACK_S.

    THE PAGE MUST NEVER WAIT FOR THIS. Same discipline as _loki_events, for the same reason: the
    only two things this repository has ever put on this request path were Loki queries, and the
    Admin page was dead for both ships. The request path READS the cache; a daemon thread fills it.
    `block=True` exists for a caller that is not a page.

    A zero here is only ever reported once a query has ANSWERED. `lookup` says which of the four
    states we are in, so nothing downstream has to guess whether `runs: 0` means "the brain has not
    published" or "we never asked".
    """
    now = time.time()
    if not LOKI_PUBLISH_ON:
        return {"lookup": "off", "runs": None, "ok": None, "failed": None, "cycle": None,
                "err": None, "lookback_h": PUBLISH_LOOKBACK_S // 3600}
    if now - _PUBLISH["ts"] >= PUBLISH_TTL_S:
        if block:
            _publish_now()
        else:
            _publish_async()
    out = dict(_PUBLISH["val"])
    out["lookback_h"] = PUBLISH_LOOKBACK_S // 3600
    return out


def _publish_async():
    """Refresh in the background, at most one refresh in flight."""
    if _PUBLISH.get("busy"):
        return
    _PUBLISH["busy"] = True
    try:
        import threading
        threading.Thread(target=_publish_now, daemon=True).start()
    except Exception:
        _PUBLISH["busy"] = False      # could not spawn: the page still renders, just without it


def _publish_now():
    """The actual fetch. Wrapped whole: nothing in here may reach a caller as an exception."""
    now = time.time()
    _PUBLISH["ts"] = now              # stamp first: a dead Loki must not be retried per request
    try:
        rows, answered = _loki_fetch('|= "perseus_publish"', now - PUBLISH_LOOKBACK_S, 500)
        if not answered:
            # ASKED AND UNANSWERED IS NOT ZERO. Leave the counts unmeasured and say which happened.
            _PUBLISH["val"] = {"lookup": "no_answer", "runs": None, "ok": None, "failed": None,
                               "cycle": None, "err": None}
            return _PUBLISH["val"]
        runs = ok = failed = 0
        cycle, err = None, None
        for d in rows:
            if d.get("evt") != "perseus_publish":
                continue
            runs += 1
            if d.get("ok"):
                ok += 1
                c = d.get("cycle")
                if isinstance(c, int) and (cycle is None or c > cycle):
                    cycle = c
            else:
                failed += 1
                err = err or (str(d.get("err") or "")[:160] or None)
        _PUBLISH["val"] = {"lookup": "ok", "runs": runs, "ok": ok, "failed": failed,
                           "cycle": cycle, "err": err}
    except Exception:
        pass                          # a refresh that fails leaves the previous answer standing
    finally:
        _PUBLISH["busy"] = False
    return _PUBLISH["val"]


def _enforce_phrase(enforce, cycle, patterns):
    """The one sentence that says what a project is ACTUALLY enforcing. ONE HOME: every row's `why`
    composes this, so `live` can never again be printed beside `cycle 0` as if they agreed."""
    if enforce == "unknown":
        return "what it enforces is UNKNOWN: no heartbeat from it reaches this page"
    if enforce == "none":
        return ("the sidecar is running but has loaded NO ruleset (cycle 0), so it blocks NOTHING "
                "-- perseus has never published a blocklist it could read")
    if enforce == "armed":
        return ("the sidecar reports ruleset cycle %s, but how many rules that cycle contains is "
                "not readable from here" % cycle)
    if enforce == "empty":
        return ("the sidecar has ruleset cycle %s loaded and that cycle armed NO blocking rules, "
                "so it blocks nothing" % cycle)
    return "the sidecar is enforcing ruleset cycle %s (%s blocking rules)" % (cycle, patterns)


def since(ts, service=None, block=False):
    """Every event newer than `ts`, optionally for one service. The alerting loop calls this so the
    SAME rules colt-web applies to itself run over the other projects' lines."""
    out = []
    for r in _tail_events(block=block):
        if (r.get("ts") or 0) <= ts:
            continue
        if service and r.get("service") != service:
            continue
        out.append(r)
    return out


def watch(seen_ts, alert):
    """Apply cybergod's OWN detection to every OTHER project's traffic.

    THE POINT OF THE WHOLE DESIGN: the rules, the thresholds and the Telegram credentials stay in
    ONE place. jobhuntwow, jev.best and polara do not each get a copy of alerts.py and a bot token
    -- five copies of a rule set is five things that drift, and a token in five repositories is the
    'one value, several homes' defect this estate keeps paying for. They emit `evt=http`; this
    reads it and pages.

    Returns the newest timestamp it consumed, so the caller cannot re-alert on the same lines.

    block=True: this is a background loop, not a page. It waits for Loki. If it read the same cache
    the page reads, a cold or expired cache would make klima and s4biz look silent, and "no rows"
    would be indistinguishable from "no attack" -- the one inference this codebase forbids."""
    rows = [r for r in since(seen_ts, block=True) if r.get("evt") == "http"]
    if not rows:
        return seen_ts
    newest = max(r.get("ts") or 0 for r in rows)
    try:
        from . import shield
    except Exception:
        return newest                     # no classifier -> no claims. Absence of evidence.

    per = {}
    for r in rows:
        svc = r.get("service") or ""
        if svc == "colt-web":
            continue                      # cybergod already alerts on itself; two paths would double every message
        p = per.setdefault(svc, {"probes": {}, "visitors": set(), "n": 0})
        p["n"] += 1
        ip, path = r.get("ip") or "", (r.get("path") or "")
        try:
            hostile = shield.probe_shape(path)
        except Exception:
            hostile = False
        if hostile and ip:
            p["probes"].setdefault(ip, set()).add(path.split("?")[0])
        elif ip and not hostile:
            p["visitors"].add(ip)

    for svc, p in sorted(per.items()):
        name = next((x["name"] for x in PROJECTS if x["service"] == svc), svc)
        # VARIETY, NOT VOLUME. One address asking for many DIFFERENT things it cannot have is a
        # scan; the same address missing one stale link a hundred times is a person. That
        # distinction is what stopped two real visitors being blocked on 10 Aug.
        for ip, paths in p["probes"].items():
            if len(paths) >= 4:
                alert("SCANNER on %s\n%s asked for %d distinct probe paths\n  %s"
                      % (name, ip, len(paths), "\n  ".join(sorted(paths)[:6])))
    return newest


def _emit(**k):
    """Fleet telemetry, through the SAME writer as access logging (telemetry.emit): stdout, which
    promtail ships to Loki, plus the shared events log.

    WHY THIS EXISTS. The operator: "we don't have visibility that that is what causing the issue".
    Correct, and it is the reason this took three ships. Every other request on this box is
    observed; the one page whose whole job is observing was itself unobserved, so when it broke
    there was nothing to read and I guessed instead of measuring. That is defect class 1 pointed
    straight at the observer.

    A second writer here would drift from the first, so this is a thin wrapper, not a copy. It can
    never raise: telemetry that breaks the request it observes is worse than no telemetry.
    """
    try:
        from . import telemetry
        telemetry.emit(**k)
    except Exception:
        try:
            print(json.dumps(dict(k, ts=time.time())), flush=True)
        except Exception:
            pass


def status():
    t0 = time.time()
    try:
        out = _status()
    except Exception as exc:
        # NAMED, then re-raised. The route catches it and renders the cause; this line is what makes
        # the failure searchable in Loki afterwards, with the same key the success path uses.
        _emit(evt="fleet_status", outcome="error", err=repr(exc)[:300],
              ms=int((time.time() - t0) * 1000))
        raise
    _emit(evt="fleet_status", outcome="ok",
          ms=int((time.time() - t0) * 1000),
          projects=len(out.get("projects") or []),
          # The four questions this page can be wrong about, recorded on EVERY call so a change in
          # them is visible as a change, not discovered by someone opening the page.
          states={s: sum(1 for p in out["projects"] if p["state"] == s)
                  for s in ("live", "observed", "silent", "elsewhere")},
          # THE OBSERVER MUST BE OBSERVED, and that now includes the SOC half. `enforcing` going
          # from 0 to 5 is the single most important state change on this estate; discovering it by
          # opening a page is how it stayed at 0 for weeks. Edge-triggered alerting can only watch
          # a number that is written down on every call.
          enforce={e: sum(1 for p in out["projects"] if p.get("enforce") == e)
                   for e in ("unknown", "none", "armed", "empty", "active")},
          alerting={a: sum(1 for p in out["projects"] if p.get("alerting") == a)
                    for a in ("self", "covered", "unknown", "blind")},
          # The two words the operator reads off the page, and the loops behind the first one, so a
          # move from 0 to 5 is observable in Loki instead of discovered by opening the tab.
          soc={s: sum(1 for p in out["projects"] if p.get("soc") == s)
               for s in ("unknown", "off", "partial", "active")},
          telegram_on=out.get("telegram_on"),
          brain_loops=(out.get("brain") or {}).get("loops_ok"),
          brain_known=(out.get("brain") or {}).get("loops_known"),
          published_cycle=(out.get("published") or {}).get("cycle"),
          published_patterns=(out.get("published") or {}).get("patterns"),
          published_readable=(out.get("published") or {}).get("readable"),
          publish_lookup=(out.get("publish_evt") or {}).get("lookup"),
          publish_runs=(out.get("publish_evt") or {}).get("runs"),
          loki_events_on=LOKI_EVENTS_ON, loki_ok=out.get("loki_ok"),
          loki_partial=out.get("loki_partial"),
          loki_rows=len(_LOKI_EVENTS.get("rows") or []),
          # None, not a number, when the cache has NEVER been filled. `now - 0.0` printed
          # 1,789,033,753 -- seconds since 1970 dressed up as a cache age. Nobody would act on
          # that, which is the charitable reading; the uncharitable one is that a plausible-looking
          # figure in the next investigation is worse than an honest blank. Same rule the page
          # itself enforces on the projects: never render a number for something not measured.
          loki_cache_age_s=(int(time.time() - _LOKI_EVENTS["ts"]) if _LOKI_EVENTS.get("ts") else None),
          beats_dir=BEAT_DIR, events_log=EVENTS)
    return out


WEEKLY_STATE = os.environ.get("PERSEUS_WEEKLY_STATE", "/var/log/colt/perseus_weekly.json")
WATCH_STATE = os.environ.get("PERSEUS_WATCH_STATE", "/var/log/colt/perseus_watch.json")


def _fresh(path, max_age_s):
    """(ran_at_least_once, age_s) for one of the brain's state files, or (None, None) when it
    cannot be read. None is NOT False: a file we cannot open says nothing about whether the job
    ran, and this page does not turn our own blindness into a verdict about the system."""
    try:
        d = json.load(open(path, encoding="utf-8"))
        age = int(time.time() - os.path.getmtime(path))
        ran = int((d or {}).get("runs") or 0) >= 1 or bool((d or {}).get("generated"))
        return (bool(ran) and age <= max_age_s), age
    except Exception:
        return None, None


def _brain():
    """ARE THE THREE AUTONOMOUS LOOPS ALIVE? One reader, three files, all on the shared volume.

    "AI SOC active" is a claim about DECISION MAKING, not about a process being up, so it is only
    ever true when all three of the loops that make decisions have actually produced their artifact
    recently:

        per incident   perseus-watch   every 10 min   four vendors on ONE live burst
        daily          perseus         04:40 UTC      mine, vet, promote, publish
        weekly         perseus-weekly  Sun 05:20 UTC  re-vet live rules, retire the dormant

    Any of them missing and the honest word is `partial`, never `active`. This is the same rule the
    installer now enforces at deploy time; the page must not be more generous than the gate.
    """
    pub = _cycle()
    daily = None
    if pub.get("readable") is True:
        daily = bool((pub.get("cycle") or 0) >= 1 and (pub.get("age_s") or 0) <= 48 * 3600)
    elif pub.get("readable") is False:
        daily = False
    weekly, w_age = _fresh(WEEKLY_STATE, 8 * 86400)
    watch, i_age = _fresh(WATCH_STATE, 3600)
    known = [x for x in (daily, weekly, watch) if x is not None]
    return {"daily": daily, "weekly": weekly, "watch": watch,
            "weekly_age_s": w_age, "watch_age_s": i_age,
            "loops_ok": sum(1 for x in known if x), "loops_known": len(known)}


def _status():
    # ONE read of the traffic cache, taken FIRST and then handed to _tail_events, so the counts and
    # the badge that explains them describe the same snapshot. This read never blocks: the request
    # path gets whatever the background refresh last put there, and a cold cache renders `elsewhere`
    # for one page load rather than hanging the page for eighteen seconds.
    _lrows, _lok, _lpartial = _loki_events()
    beats, rows, now = _all_beats(), _tail_events(loki_rows=_lrows), time.time()
    pub = _cycle()
    # Read ONCE for the whole response, like the traffic cache above: the three loop files are the
    # same answer for every row, and re-reading them per project would let a mid-render write make
    # two rows disagree about the same fleet.
    try:
        brain = _brain()
    except Exception as exc:
        brain = {"daily": None, "weekly": None, "watch": None, "weekly_age_s": None,
                 "watch_age_s": None, "loops_ok": 0, "loops_known": 0, "err": repr(exc)[:160]}
    # AN OPTIONAL LOOKUP MAY NEVER 500 THE PAGE. This one is three dict operations and a daemon
    # thread, so it "cannot" raise -- which is exactly what was said about the last two things that
    # took this page down. It degrades to "no query has completed", which is precisely true when the
    # lookup itself is broken, and the cause travels in `err` instead of into a traceback.
    try:
        pubevt = _publish()
    except Exception as exc:
        pubevt = {"lookup": "pending", "runs": None, "ok": None, "failed": None, "cycle": None,
                  "err": repr(exc)[:160], "lookback_h": PUBLISH_LOOKBACK_S // 3600}
    loki_svcs = {r.get("service") for r in _lrows}
    floor = ""
    if _lpartial:
        floor = (" These counts are a FLOOR, not a total: the Loki fetch is capped at %d lines per "
                 "project and that cap was reached." % LOKI_EVENT_LIMIT)

    per = {}
    for r in rows:
        s = r.get("service") or ""
        if not s:
            continue
        # THIS PAGE'S OWN TELEMETRY IS NOT THIS PAGE'S TRAFFIC. _emit writes through the shared
        # writer, so its lines land in the same events log status() reads -- and the browser polls
        # every 30s, so colt-web would accrue ~2,880 self-inflicted "lines" a day and the observer
        # would be measuring itself. Exactly the heartbeat rule, one evt name over.
        if r.get("evt") in ("fleet_status", "perseus_beat"):
            continue
        p = per.setdefault(s, {"lines": 0, "http": 0, "attacks": 0, "alerts": 0,
                               "visitors": set(), "last_ts": 0, "r429": 0, "rblock": 0})
        p["lines"] += 1
        p["last_ts"] = max(p["last_ts"], r.get("ts") or 0)
        evt = r.get("evt")
        if evt == "http":
            p["http"] += 1
            if r.get("ip"):
                p["visitors"].add(r["ip"])
            # ENFORCEMENT THAT ACTUALLY HAPPENED, as opposed to enforcement that is configured.
            # 429 is the ONLY response perseus_client.Middleware produces when it denies, so a 429
            # in a project's own lines is the sidecar's work made visible. Counted separately from
            # shield_block below rather than summed here, because they are two different mechanisms
            # and only cybergod runs the second one.
            if r.get("status") == 429:
                p["r429"] += 1
            # A probe path is the honest per-project attack count and needs no classifier here:
            # shield.probe_shape is the one implementation, imported lazily so a fleet page can
            # never be taken down by an import error in the detector.
            try:
                from . import shield
                if shield.probe_shape(r.get("path") or ""):
                    p["attacks"] += 1
            except Exception:
                pass
        elif evt in ("security_alert", "shield_block"):
            p["alerts"] += 1
            if evt == "shield_block":
                p["rblock"] += 1

    out = []
    for proj in PROJECTS:
        svc = proj["service"]
        m = per.get(svc)
        b = beats.get(svc)
        beat_age = int(now - (b.get("ts") or 0)) if b else None
        sidecar = ("active" if b and beat_age is not None and beat_age < STALE_BEAT_S
                   else "stale" if b else "not installed")

        # ---- IS ANYTHING ACTUALLY ENFORCED HERE? -------------------------------------------------
        # `enforce` is an ENUM KEY. It is never translated; the label is chosen at render time.
        # The BEAT is authoritative about what this project LOADED (the client stamps the cycle it
        # is running); the published FILE is authoritative about how many rules that cycle armed.
        # They are only combined when they are talking about the SAME cycle -- a pattern count from
        # a different document is a number about something else, and a number about something else
        # is the defect this page exists to prevent.
        bcycle = (b or {}).get("cycle")
        if not b:
            enforce, epat = "unknown", None
        elif not bcycle:
            # cycle 0 or absent. The client's cache initialises to 0 and only moves when it has read
            # a published blocklist, so this is the sidecar telling us it has never loaded a ruleset.
            # It is running, it is beating, and it blocks nothing. THIS IS THE CURRENT FLEET STATE.
            enforce, epat = "none", None
        elif not pub.get("readable") or pub.get("cycle") != bcycle or pub.get("patterns") is None:
            enforce, epat = "armed", None
        elif pub["patterns"] > 0:
            enforce, epat = "active", pub["patterns"]
        else:
            enforce, epat = "empty", 0          # a MEASURED zero: same cycle, no patterns in it
        phrase = _enforce_phrase(enforce, bcycle, epat)

        # ---- WOULD AN ATTACK ON THIS PROJECT REACH THE OPERATOR? ---------------------------------
        # watch() pages from exactly the rows this page counts, so alerting coverage is not a new
        # measurement -- it is the live/silent/elsewhere distinction said in the vocabulary the
        # operator asked the question in. The one place it is NOT simply readable is an own-log
        # project when the traffic lookup is ON: this page reads a non-blocking cache and watch()
        # waits for the same query, so an empty cache here proves nothing about the alerting loop.
        # Reporting that as "blind" would be this page describing where WE looked. "unknown" is the
        # only honest answer, and the enum keeps it distinguishable from a real gap.
        if svc == "colt-web":
            alerting = "self"
        elif m:
            alerting = "covered"
        elif proj.get("own_log") and LOKI_EVENTS_ON:
            alerting = "unknown"
        else:
            alerting = "blind"

        if not m and proj.get("own_log"):
            # A FOURTH STATE, because collapsing it into SILENT would be the very error this module
            # exists to prevent: reporting where WE looked as a fact about THEM.
            state = "elsewhere"
            # ...AND THE SIDECAR BADGE HAD TO SAY THE SAME THING. It kept reading "not installed",
            # which is that identical error one column over: the beat for an own-log project is
            # written BESIDE ITS OWN EVENT LOG, on a volume this container does not mount, so the
            # directory read above can never see it no matter how healthy the sidecar is. Measured
            # 2026-09-09: klima and s4biz both carry perseus_client AND call add_middleware, and both
            # rendered as unguarded purely because of this line.
            if sidecar == "not installed":
                sidecar = "unverifiable"
            if sidecar == "active":
                # The beat came from the project's stdout via Loki, so the sidecar is proven. The
                # traffic is normally read from Loki too (see _loki_events) -- reaching this line
                # means that lookup returned nothing, which is a statement about LOKI, never about
                # the project. Say which, because "quiet" and "unreadable" are different facts.
                # THREE DIFFERENT FACTS, AND THE PAGE MUST NOT CONFLATE THEM. "We did not ask",
                # "we asked and Loki did not answer" and "Loki answered with nothing" are not the
                # same statement, and the first is now the normal case: the traffic lookup defaults
                # off until it has been seen working. Saying "did not answer" when we never asked
                # would be this page inventing evidence about a system it did not query.
                if not LOKI_EVENTS_ON:
                    lk = ("the traffic lookup is TURNED OFF on this box (PERSEUS_LOKI_EVENTS), so "
                          "we did not ask")
                elif _lok:
                    lk = "Loki was asked and returned no lines for it"
                else:
                    lk = "Loki was asked and did not answer"
                why = ("sidecar heartbeat confirmed via stdout, and %s. But its TRAFFIC could "
                       "not be read: its event volume (%s) is not mounted here and %s. The "
                       "zeros below are our blind spot, NOT a quiet project -- run "
                       "`python fleet.py`, which reads its own log over ssh."
                       % (phrase, proj["own_log"], lk))
            else:
                why = ("writes to its own event volume (%s), which this container does not mount -- "
                       "so neither its traffic NOR its sidecar heartbeat can reach this page. This "
                       "is our blind spot, not a missing control. Run `python fleet.py` from the "
                       "operator's machine, which reads every project's own log over ssh."
                       % proj["own_log"])
        elif not m:
            state = "silent"
            why = ("no log line in %dh. We are BLIND to this project, which is NOT the same as it "
                   "being quiet." % (WINDOW_S // 3600))
        elif proj.get("own_log") and svc in loki_svcs and sidecar == "active":
            # FULL PARITY, WITHOUT THE COUPLING. Its event volume is not mounted here and must not
            # be; its lines are read from the shared Loki that its own promtail already pushes to.
            # The same rows feed watch(), so this project can page the operator like any other.
            state = "live"
            # "logging AND enforcing cycle %s" is what this said, and it printed "enforcing cycle 0"
            # for weeks while the sidecars blocked nothing. The word `enforcing` was doing work the
            # measurement did not support. It now composes _enforce_phrase, which is allowed to say
            # the sidecar enforces NOTHING.
            why = ("logging, and %s. Its traffic is read from the shared Loki, not "
                   "from a volume mount -- mounting a sibling's volume is the `external:` coupling "
                   "that made this deploy fail on staging.%s" % (phrase, floor))
        elif sidecar == "active":
            state = "live"
            why = "logging, and %s" % phrase
        else:
            state = "observed"
            why = ("logging, but no sidecar heartbeat: this project is visible and UNGUARDED. "
                   "perseus_client is not wired into its request path.")
        # ---- AI SOC: ONE WORD, and it means DECISIONS ARE BEING MADE FOR THIS PROJECT ----------
        # The operator asked for one word per project with the same vocabulary as the sidecar badge,
        # and for `active` to mean the thing acts on its own behalf: per attack, per day, per week.
        # So it is a conjunction, and it is measured, never asserted:
        #   local   this project's own heartbeat says the shield is loaded AND armed here
        #   read    the brain can see this project's traffic, or it would have no incident to judge
        #   loops   all three autonomous loops have produced an artifact recently (see _brain)
        # Anything short of all three is `partial`. Anything we cannot see is `unknown`, never `off`.
        loc = (b or {}).get("local")
        enf = (b or {}).get("enforcing")
        if sidecar in ("not installed", "unverifiable") or b is None:
            soc, soc_why = "unknown", ("no heartbeat reaches this page, so whether anything decides "
                                       "for this project cannot be measured from here")
        elif loc is None:
            soc, soc_why = "unknown", ("this sidecar predates the local shield and does not report "
                                       "whether it can act - redeploy the project to find out")
        elif not loc or not enf:
            soc, soc_why = "off", "the sidecar reports it is present but not armed to act locally"
        elif alerting == "blind":
            soc, soc_why = "partial", ("armed locally, but the brain cannot read this project's "
                                       "traffic, so no incident here is ever judged by the panel")
        elif brain["loops_known"] < 3:
            soc, soc_why = "partial", ("armed locally; %d of 3 brain loops could not be read"
                                       % (3 - brain["loops_known"]))
        elif brain["loops_ok"] < 3:
            soc, soc_why = "partial", (
                "armed locally, but only %d of 3 autonomous loops are current (per-incident %s, "
                "daily %s, weekly %s)" % (brain["loops_ok"],
                                          "ok" if brain["watch"] else "stale",
                                          "ok" if brain["daily"] else "stale",
                                          "ok" if brain["weekly"] else "stale"))
        else:
            soc, soc_why = "active", ("deciding on its own: per incident every 10 min, daily at "
                                      "04:40, weekly on Sunday")

        # ---- TELEGRAM: ONE WORD. Does an attack HERE reach the operator? ----------------------
        # colt-web owns notify.py and the bot token; nothing else may. So a project reaches Telegram
        # exactly when the brain can read its lines. `self` and `covered` are both yes.
        tg = {"self": "active", "covered": "active",
              "blind": "off", "unknown": "unknown"}.get(alerting, "unknown")

        out.append({
            "key": proj["key"], "name": proj["name"], "service": svc,
            "state": state, "why": why,
            "soc": soc, "soc_why": soc_why,
            "telegram": tg,
            "sidecar": sidecar, "sidecar_age_s": beat_age,
            "sidecar_cycle": (b or {}).get("cycle"),
            "checks": (b or {}).get("checks"),
            "lines_24h": (m or {}).get("lines", 0),
            "requests_24h": (m or {}).get("http", 0),
            "attacks_24h": (m or {}).get("attacks", 0),
            "alerts_24h": (m or {}).get("alerts", 0),
            "visitors_24h": len((m or {}).get("visitors") or ()),
            "last_seen": (m or {}).get("last_ts") or None,
            # ---- the SOC half -------------------------------------------------------------------
            "enforce": enforce,                 # enum: unknown | none | armed | empty | active
            "enforce_cycle": bcycle,            # what THIS project reports having loaded
            "enforce_patterns": epat,           # None unless the beat and the file name one cycle
            "enforce_why": phrase,
            "alerting": alerting,               # enum: self | covered | unknown | blind
            # REFUSALS THAT ACTUALLY HAPPENED. None -- never 0 -- for a project whose lines we could
            # not read, because "we counted its requests and none were refused" and "we could not
            # read a single line" are the two facts this whole module exists to keep apart, and a 0
            # in an enforcement column reads as "the defence is working and nothing tried".
            "refused_24h": (None if not m else m["r429"] + m["rblock"]),
            "refused_429_24h": (None if not m else m["r429"]),
            "refused_shield_24h": (None if not m else m["rblock"]),
        })

    return {
        "generated": int(now),
        "window_h": WINDOW_S // 3600,
        "published": pub,
        # The three autonomous loops, as the page's own summary. `soc_active` is the number the
        # operator actually asked for: how many of five decide for themselves.
        "brain": brain,
        "soc_active": sum(1 for p in out if p["soc"] == "active"),
        "telegram_on": sum(1 for p in out if p["telegram"] == "active"),
        "events_log": EVENTS,
        "beats_dir": BEAT_DIR,
        "projects": out,
        "guarded": sum(1 for p in out if p["sidecar"] == "active"),
        "blind": sum(1 for p in out if p["state"] == "silent"),
        "elsewhere": sum(1 for p in out if p["state"] == "elsewhere"),
        # ---- the SOC half, for the fleet ----------------------------------------------------------
        # GUARDED AND ENFORCING ARE DIFFERENT NUMBERS, and printing only the first is what let
        # "5 guarded" sit above five rows that blocked nothing. `enforcing` counts the projects whose
        # own heartbeat names a cycle that the published blocklist says armed at least one rule.
        "enforcing": sum(1 for p in out if p["enforce"] == "active"),
        "enforce_unknown": sum(1 for p in out if p["enforce"] == "unknown"),
        "alerting_blind": sum(1 for p in out if p["alerting"] == "blind"),
        "publish_evt": pubevt,
        # A FACT ABOUT THE DATA SOURCE, NOT A COUNT. shield.decide() returns "TARPIT" and
        # telemetry.py sleeps on it, and NEITHER writes a line -- there is no `evt` for a tarpit
        # anywhere in this codebase. So how often a request was slowed down is NOT DETERMINABLE from
        # any log this page can read. The page says that in words rather than showing a 0; the flag
        # lives here so that when a tarpit event is added, one edit removes the disclaimer.
        "tarpit_recorded": False,
        # STATE THE LIMIT ON THE PAGE ITSELF. A number that came from a log nobody is writing is
        # not a measurement, and the reader cannot tell from the number alone.
        "loki_ok": _lok,
        "loki_partial": _lpartial,
        "caveat": ("Counts come from the shared events log, plus the shared Loki for the projects "
                   "whose event volume is not mounted here. A project we cannot read reads as "
                   "SILENT or ELSEWHERE, which means we cannot see it -- never that it is safe."),
    }
