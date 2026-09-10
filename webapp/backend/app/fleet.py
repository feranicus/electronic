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


LOKI_TIMEOUT_S = float(os.environ.get("PERSEUS_LOKI_TIMEOUT", "3"))
# Raw lines pulled per own-log project per window. Bounded because a status page must not be a
# lever for making our own server work; if a project genuinely exceeds it the counts are reported
# as a FLOOR rather than silently understated (see _loki_events).
LOKI_EVENT_LIMIT = int(os.environ.get("PERSEUS_LOKI_LIMIT", "2000"))
# Traffic counts do not need per-minute freshness, and every refresh is a real query against a
# shared Loki. Five minutes, refreshed off the request path.
LOKI_EVENT_TTL_S = int(os.environ.get("PERSEUS_LOKI_TTL", "300"))
# A KILL SWITCH, because the first version of this lookup took the Admin page down and the only
# way back was a redeploy. `set_secret.py PERSEUS_LOKI_EVENTS` + restart now disables it instead.
LOKI_EVENTS_ON = os.environ.get("PERSEUS_LOKI_EVENTS", "1") != "0"
_LOKI_CACHE = {"ts": 0.0, "beats": {}}
_LOKI_EVENTS = {"ts": 0.0, "rows": [], "ok": False, "partial": False, "busy": False}
# Tried in order; the FIRST that returns anything wins. See _loki_beats for why this is a list.
LOKI_BEAT_SELECTORS = [s for s in os.environ.get(
    "PERSEUS_LOKI_SELECTORS", '{container=~".+"}:{job=~".+"}:{service_name=~".+"}').split(":") if s]


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
    try:
        with open(BLOCKLIST, encoding="utf-8") as fh:
            d = json.load(fh)
        return {"cycle": d.get("cycle"), "patterns": len(d.get("patterns") or []),
                "age_s": int(time.time() - os.path.getmtime(BLOCKLIST))}
    except Exception:
        return {"cycle": None, "patterns": 0, "age_s": None}


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


def status():
    # ONE read of the traffic cache, taken FIRST and then handed to _tail_events, so the counts and
    # the badge that explains them describe the same snapshot. This read never blocks: the request
    # path gets whatever the background refresh last put there, and a cold cache renders `elsewhere`
    # for one page load rather than hanging the page for eighteen seconds.
    _lrows, _lok, _lpartial = _loki_events()
    beats, rows, now = _all_beats(), _tail_events(loki_rows=_lrows), time.time()
    pub = _cycle()
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
        p = per.setdefault(s, {"lines": 0, "http": 0, "attacks": 0, "alerts": 0,
                               "visitors": set(), "last_ts": 0})
        p["lines"] += 1
        p["last_ts"] = max(p["last_ts"], r.get("ts") or 0)
        evt = r.get("evt")
        if evt == "http":
            p["http"] += 1
            if r.get("ip"):
                p["visitors"].add(r["ip"])
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

    out = []
    for proj in PROJECTS:
        svc = proj["service"]
        m = per.get(svc)
        b = beats.get(svc)
        beat_age = int(now - (b.get("ts") or 0)) if b else None
        sidecar = ("active" if b and beat_age is not None and beat_age < STALE_BEAT_S
                   else "stale" if b else "not installed")
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
                why = ("sidecar heartbeat confirmed via stdout (cycle %s), but its TRAFFIC could "
                       "not be read: its event volume (%s) is not mounted here and Loki %s. The "
                       "zeros below are our blind spot, NOT a quiet project -- run "
                       "`python fleet.py`, which reads its own log over ssh."
                       % ((b or {}).get("cycle"), proj["own_log"],
                          "returned no lines for it" if _lok else "did not answer"))
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
            why = ("logging and enforcing cycle %s. Its traffic is read from the shared Loki, not "
                   "from a volume mount -- mounting a sibling's volume is the `external:` coupling "
                   "that made this deploy fail on staging.%s"
                   % ((b or {}).get("cycle"), floor))
        elif sidecar == "active":
            state = "live"
            why = "logging, and the sidecar is enforcing cycle %s" % (b or {}).get("cycle")
        else:
            state = "observed"
            why = ("logging, but no sidecar heartbeat: this project is visible and UNGUARDED. "
                   "perseus_client is not wired into its request path.")
        out.append({
            "key": proj["key"], "name": proj["name"], "service": svc,
            "state": state, "why": why,
            "sidecar": sidecar, "sidecar_age_s": beat_age,
            "sidecar_cycle": (b or {}).get("cycle"),
            "checks": (b or {}).get("checks"),
            "lines_24h": (m or {}).get("lines", 0),
            "requests_24h": (m or {}).get("http", 0),
            "attacks_24h": (m or {}).get("attacks", 0),
            "alerts_24h": (m or {}).get("alerts", 0),
            "visitors_24h": len((m or {}).get("visitors") or ()),
            "last_seen": (m or {}).get("last_ts") or None,
        })

    return {
        "generated": int(now),
        "window_h": WINDOW_S // 3600,
        "published": pub,
        "events_log": EVENTS,
        "beats_dir": BEAT_DIR,
        "projects": out,
        "guarded": sum(1 for p in out if p["sidecar"] == "active"),
        "blind": sum(1 for p in out if p["state"] == "silent"),
        "elsewhere": sum(1 for p in out if p["state"] == "elsewhere"),
        # STATE THE LIMIT ON THE PAGE ITSELF. A number that came from a log nobody is writing is
        # not a measurement, and the reader cannot tell from the number alone.
        "loki_ok": _lok,
        "loki_partial": _lpartial,
        "caveat": ("Counts come from the shared events log, plus the shared Loki for the projects "
                   "whose event volume is not mounted here. A project we cannot read reads as "
                   "SILENT or ELSEWHERE, which means we cannot see it -- never that it is safe."),
    }
