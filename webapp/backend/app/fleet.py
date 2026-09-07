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


def _tail_events(limit_bytes=4_000_000):
    rows = []
    for path in [EVENTS] + EXTRA_EVENTS:
        rows.extend(_tail_one(path, limit_bytes))
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


def since(ts, service=None):
    """Every event newer than `ts`, optionally for one service. The alerting loop calls this so the
    SAME rules colt-web applies to itself run over the other projects' lines."""
    out = []
    for r in _tail_events():
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

    Returns the newest timestamp it consumed, so the caller cannot re-alert on the same lines."""
    rows = [r for r in since(seen_ts) if r.get("evt") == "http"]
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
    beats, rows, now = _beats(), _tail_events(), time.time()
    pub = _cycle()

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
            why = ("writes to its own event volume (%s), which this container does not mount. Not "
                   "silent, not unseen -- run `python fleet.py` from the operator's machine, which "
                   "reads every project's own log over ssh." % proj["own_log"])
        elif not m:
            state = "silent"
            why = ("no log line in %dh. We are BLIND to this project, which is NOT the same as it "
                   "being quiet." % (WINDOW_S // 3600))
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
        "caveat": ("Counts come from the shared events log. A project that does not write to it "
                   "reads as SILENT, which means we cannot see it -- never that it is safe."),
    }
