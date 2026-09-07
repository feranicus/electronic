"""perseus.hub -- ONE brain for six properties. Reads Loki, changes the defence, reports the delta.

    python -m perseus.hub --cycle          # run one full cycle now (what the timer calls)
    python -m perseus.hub --dry-run        # decide everything, change nothing, print the report
    python -m perseus.hub --report         # last delta report, no analysis

WHY A HUB AND NOT A SIDECAR PER PROJECT. Measured, not preferred: the droplet is 4 GB with ~20
containers and ~2 GB free, so six more containers is not viable. And copy-pasting a STATEFUL
component into six repos is the "one value, several homes" defect this codebase has paid for with
ENRICH_MODELS (four homes), the document language set (six) and the model allowlist (two).

WHY IT READS LOKI. The six projects write to THREE different event volumes (colt_events,
polara_events, s4biz_events) through FOUR promtails -- but every promtail pushes to the SAME Loki.
Loki is the only substrate they already share, so cross-project observation needs ZERO code in
jev, polara, s4biz or godeyes. That is the entire reason this is cheap to adopt.

WHAT ONE CYCLE DOES, in order, and the order matters:
  1. REVIEW first. Any blocking rule that has refused legitimate-looking traffic demotes itself
     before anything new is considered. Cleaning up after yesterday outranks acting today.
  2. MINE. Sources that missed on many DISTINCT paths, minus everything the corpus already names.
     What survives is, by construction, a technique we cannot yet detect.
  3. ASK the four vendors. They propose patterns. They never install one.
  4. VET deterministically (perseus.vet). A pattern that matches anything we serve is refused here,
     whatever the models said.
  5. PROMOTE what has earned it (24h in detection, quorum, hostile matches, zero clean matches).
  6. TUNE thresholds within committed BOUNDS, median of the agreeing side, step-capped.
  7. PUBLISH the blocklist and ruleset to the shared volume for the thin clients.
  8. REPORT the delta: what changed, what was refused and why, coverage before and after.
  9. ABUSE. AbuseIPDB automatically; hoster complaints only for repeat offenders, capped.

FAILS SAFE AT EVERY STEP. A cycle that cannot reach Loki, or the models, or the store, reports
that it could not and changes nothing. A defence that silently does nothing looks exactly like a
defence that had nothing to do, which is the failure this whole subsystem exists to end.
"""
import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from perseus import ruleset as RS
import abuse as AB, vet as VET          # noqa: E402

# Every property, and the Loki selector that finds it. Three event volumes, four promtails, one
# Loki: these selectors are the only place that knows the difference.
PROJECTS = {
    "cybergod":   '{job="coltbots"} | json | service!="jhw-web"',
    "jobhuntwow": '{container=~".*jhw-web.*"}',
    "polara":     '{job=~".*polara.*"}',
    "s4biz":      '{job=~".*s4biz.*"}',
    "jev":        '{container=~".*jev-.*"}',
    "godeyes":    '{container=~".*godeyes.*"}',
}

BLOCKLIST = os.environ.get("PERSEUS_BLOCKLIST", "/var/log/colt/perseus_blocklist.json")
STATE = os.environ.get("PERSEUS_STATE", "/var/log/colt/perseus_state.json")
LOKI_LIMIT = 5000


def _now():
    return time.time()


def _utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ── evidence ─────────────────────────────────────────────────────────────────────────────────
def _enc(q):
    for a, b in (("%", "%25"), ("\\", "%5C"), ("{", "%7B"), ("}", "%7D"), ('"', "%22"),
                 (" ", "%20"), ("|", "%7C"), ("(", "%28"), (")", "%29"), ("[", "%5B"),
                 ("]", "%5D"), ("=", "%3D"), ("+", "%2B"), ("&", "%26")):
        q = q.replace(a, b)
    return q


def _loki_script(start, end):
    b = ["L=$(docker ps --format '{{.Names}}' | grep -iE 'loki' | head -1)",
         'echo "#### LOKI"; echo "${L:-NONE}"',
         '[ -z "$L" ] && exit 0',
         "q(){ docker exec \"$L\" wget -qO- \"http://127.0.0.1:3100/loki/api/v1/query_range"
         "?query=$1&start=%s&end=%s&limit=%d&direction=backward\" 2>/dev/null; }" % (start, end, LOKI_LIMIT)]
    for name, sel in PROJECTS.items():
        q = '%s |= "\\"evt\\": \\"http\\""' % sel
        b.append('echo; echo "#### P_%s"; q "%s"' % (name, _enc(q)))
    return "\n".join(b) + "\n"


def collect(host=None, days=2):
    """Every evt=http line from every project, normalised. Returns (events, blind_projects)."""
    host = host or os.environ.get("DROPLET_HOST", "64.225.108.200")
    try:
        from recover import ssh_script, sections
        import recover as _rc
    except Exception as e:
        return [], list(PROJECTS), "recover.py not importable: %r" % e
    prev = _rc.HOST
    _rc.HOST = host
    try:
        end = int(_now())
        start = end - days * 86400
        out, err, rc = ssh_script(_loki_script(start, end), timeout=240)
    except Exception as e:
        return [], list(PROJECTS), repr(e)[:160]
    finally:
        _rc.HOST = prev
    if rc != 0 and not out:
        return [], list(PROJECTS), "ssh failed rc=%s: %s" % (rc, (err or "")[:160])
    sec = sections(out or "")
    if (sec.get("LOKI") or "").strip() in ("", "NONE"):
        return [], list(PROJECTS), "no Loki container on %s" % host

    events, blind = [], []
    for name in PROJECTS:
        raw = (sec.get("P_%s" % name) or "").strip()
        got = 0
        try:
            for st in json.loads(raw or "{}").get("data", {}).get("result", []):
                for _ts, line in st.get("values") or []:
                    # A docker-stdout stream may wrap the line; take the JSON we recognise.
                    try:
                        e = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(e, dict) or e.get("evt") != "http":
                        continue
                    e["project"] = name
                    # The line's own JSON carries no timestamp, so keep Loki's. Without it the
                    # cycle cannot tell "the last 2 days" from "the last 7", and the abuse gate
                    # counts DISTINCT DAYS -- a fact that does not exist without a clock.
                    try:
                        e["_ts"] = int(_ts) / 1e9
                    except Exception:
                        e["_ts"] = _now()
                    events.append(e)
                    got += 1
        except Exception:
            pass
        if not got:
            # BLIND IS NOT CLEAN. A project with no lines has not been observed, and every
            # conclusion about it below is invalid. Say so rather than counting it as quiet.
            blind.append(name)
    return events, blind, ""


def mine(events, days=2):
    """Sources that missed on many DISTINCT paths, minus everything the corpus already names.

    Reuses shield's classifier rather than a second copy of the corpus: two vocabularies would
    drift, and a path that is an attack to one and not the other is how a gap opens."""
    try:
        sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
        from app import shield as sh
    except Exception:
        return {"sources": [], "paths": [], "error": "shield unavailable"}
    missed, per_proj = {}, {}
    for e in events:
        if int(e.get("status") or 0) != 404:
            continue
        ip, pth = e.get("ip") or "", (e.get("path") or "")[:120]
        if not ip or not pth:
            continue
        missed.setdefault(ip, set()).add(pth)
        per_proj.setdefault(ip, set()).add(e.get("project"))
    th = RS.thresholds(RS.load())
    floor = th["slow_distinct"]
    sources, paths = [], {}
    for ip, pset in missed.items():
        if len(pset) < floor:
            continue
        unnamed = [p for p in pset if not sh.is_our_route(p) and not sh.probe_shape(p)]
        if not unnamed:
            continue
        sources.append({"ip": ip, "distinct": len(pset), "unnamed": len(unnamed),
                        "projects": sorted(per_proj.get(ip) or []), "sample": sorted(unnamed)[:8]})
        for p in unnamed:
            paths[p] = paths.get(p, 0) + 1
    sources.sort(key=lambda s: -s["unnamed"])
    return {"sources": sources[:25],
            "paths": [p for p, _ in sorted(paths.items(), key=lambda kv: -kv[1])][:40]}


def ask_panel(unk):
    """Four vendors, one per provider, so a quota or an outage cannot silence the review."""
    if not unk.get("paths"):
        return []
    try:
        sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
        from app import attack_digest as ad
        return ad.ask_panel(unk)
    except Exception as e:
        return [{"model": "-", "ok": False, "error": "panel unavailable: %r" % e}]


def consensus(reviews):
    try:
        sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
        from app import attack_digest as ad
        return ad.consensus(reviews)
    except Exception:
        return []


# ── who to report, and what the numbers should be ─────────────────────────────────────────────

ABUSE_DAYS = int(os.environ.get("PERSEUS_ABUSE_WINDOW_DAYS", "7"))


def actors(events, window_days=None, now=None):
    """Repeat offenders, assembled from observed requests. One entry per ADDRESS.

    DISTINCT DAYS, never request volume. A thousand requests in one hour is a burst and might be a
    broken client; the same address returning on Tuesday and Friday is somebody working through an
    estate. The abuse gate keys on the first and ignores the second on purpose.

    The RDAP lookup is the ONLY network call in this function, it targets the REGISTRY and never
    the address itself, and a failure leaves the actor without a contact rather than without an
    entry -- so a registry outage costs us a complaint, not the evidence.
    """
    now = now or _now()
    cutoff = now - (window_days or ABUSE_DAYS) * 86400
    try:
        sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
        from app import shield as sh
    except Exception as e:
        # NOT SILENTLY EMPTY. "no repeat offenders" and "I could not load the classifier" look
        # identical from the outside, and only one of them is good news. Raise a marker the cycle
        # turns into a reported error rather than returning a reassuring empty list.
        raise RuntimeError("shield unavailable, so no actor could be classified: %r" % e)
    by_ip = {}
    for e in events:
        if e.get("_ts", now) < cutoff:
            continue
        ip, pth = e.get("ip") or "", (e.get("path") or "")[:120]
        if not ip or not pth:
            continue
        hostile = sh.probe_shape(pth) or int(e.get("status") or 0) == 404
        if not hostile:
            continue
        a = by_ip.setdefault(ip, {"ip": ip, "total": 0, "days": {}, "routes": {},
                                  "classes": set(), "first": None, "last": None,
                                  "projects": set()})
        ts = e.get("_ts", now)
        a["total"] += 1
        a["days"][time.strftime("%Y-%m-%d", time.gmtime(ts))] = \
            a["days"].get(time.strftime("%Y-%m-%d", time.gmtime(ts)), 0) + 1
        a["routes"][pth] = a["routes"].get(pth, 0) + 1
        a["projects"].add(e.get("project"))
        # classify() returns EVERY class the path belongs to, most specific first -- a list, not
        # a name. Assuming a string here put a list into a set and raised; read the signature.
        for cls in (sh.classify(pth) or []):
            a["classes"].add(cls)
        a["first"] = ts if a["first"] is None else min(a["first"], ts)
        a["last"] = ts if a["last"] is None else max(a["last"], ts)
    out = []
    for a in by_ip.values():
        if len(a["days"]) < AB.MIN_DAYS:
            continue                       # not a repeat offender: nothing to report yet
        a["classes"] = ", ".join(sorted(a["classes"])) or "automated scanning"
        a["projects"] = sorted(x for x in a["projects"] if x)
        try:
            import incident_report as IR
            info = IR.rdap_abuse(a["ip"]) or {}
            a["holder"] = info.get("name") or info.get("handle") or ""
            a["abuse"] = info.get("abuse") or []
        except Exception:
            a["holder"], a["abuse"] = "", []
        out.append(a)
    out.sort(key=lambda x: (-len(x["days"]), -x["total"]))
    return out[:20]


THRESHOLD_PROMPT = """

You are tuning the rate limits of a small security platform from ITS OWN measured traffic. You are
not blocking anything and you cannot: your numbers are clamped to a committed range, capped to a
25%% move, and only applied when 3 of 4 independent reviewers agree on the DIRECTION.

A limit set too low denies real visitors, which is the more expensive mistake. A limit set too high
lets an automated client run for a day before anything notices. Argue from the numbers below.

MEASURED, last %(days)d day(s):
  requests seen                 %(total)d
  distinct source addresses     %(sources)d
  requests by the BUSIEST source that looked legitimate   %(top_clean)d
  requests by the busiest source that looked hostile      %(top_hostile)d
  distinct 404 paths by the busiest prober                %(top_probe)d

CURRENT VALUES:
%(current)s

ALLOWED RANGES (a number outside its range is discarded, not clamped, so stay inside):
%(bounds)s

Return STRICT JSON only, and include ONLY keys you would actually change:
{"reasoning": "<two sentences>", "thresholds": {"ip_per_min": 8, "ip_per_day": 120}}
"""


def threshold_stats(events, days):
    """Our own arithmetic, not the attacker's text: nothing here is fenced because nothing here
    came from a request body or path."""
    try:
        sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
        from app import shield as sh
    except Exception:
        return None
    clean, hostile, probes = {}, {}, {}
    for e in events:
        ip, pth = e.get("ip") or "", e.get("path") or ""
        if not ip:
            continue
        if sh.probe_shape(pth):
            hostile[ip] = hostile.get(ip, 0) + 1
            probes.setdefault(ip, set()).add(pth[:120])
        else:
            clean[ip] = clean.get(ip, 0) + 1
    return {"days": days, "total": len(events),
            "sources": len(set(list(clean) + list(hostile))),
            "top_clean": max(clean.values()) if clean else 0,
            "top_hostile": max(hostile.values()) if hostile else 0,
            "top_probe": max((len(v) for v in probes.values()), default=0)}


def ask_thresholds(stats, rs, models=None):
    """Four vendors vote on the numbers. RS.tune() decides: quorum on direction, median of the
    agreeing side, step-capped, clamped on read. One bold model cannot move anything."""
    if not stats or not stats.get("total"):
        return {}
    try:
        sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
        from app import shield_panel as sp, llm_guard as _G
        import enrich as E
    except Exception:
        return {}
    cur = RS.thresholds(rs)
    prompt = (_G.GUARD_PREAMBLE + THRESHOLD_PROMPT) % dict(
        stats,
        current="\n".join("  %-14s %s" % (k, v) for k, v in sorted(cur.items())),
        bounds="\n".join("  %-14s %d..%d" % (k, lo, hi)
                          for k, (lo, hi) in sorted(RS.BOUNDS.items())))
    votes = {}
    for m in (models or sp.MODELS):
        try:
            raw, _u = E._call(prompt, model=m, max_tokens=700, timeout=60)
            j = E._json(raw)
            for k, v in (j.get("thresholds") or {}).items():
                c = RS.clamp(k, v)
                # DISCARD, do not clamp, a vote outside the range: clamping it would silently turn
                # a nonsense answer into a valid vote and let it count toward the quorum.
                if c is not None and int(v) == c:
                    votes.setdefault(k, []).append(c)
        except Exception:
            continue
    return votes


# ── the cycle ────────────────────────────────────────────────────────────────────────────────
def cycle(days=2, dry_run=False, host=None):
    rs = RS.load()
    since = (rs.get("history") or [{}])[-1].get("ts", 0) if rs.get("history") else 0
    started = _now()
    rep = {"started": started, "days": days, "dry_run": dry_run,
           "before": RS.summary(rs), "blind": [], "errors": []}

    # Collect the WIDER of the two windows in ONE query. Mining wants what is recent; the
    # abuse gate counts DISTINCT DAYS and cannot see two of them inside a two-day window.
    events, blind, err = collect(host, max(days, ABUSE_DAYS))
    rep["blind"] = blind
    rep["events"] = len(events)
    if err:
        rep["errors"].append(err)
    if not events:
        rep["after"] = RS.summary(rs)
        rep["verdict"] = "NO EVIDENCE - nothing changed"
        return rep, rs

    # 1. REVIEW BEFORE ACTING. Yesterday's mistakes are undone before today's are made.
    demoted = RS.review(rs)
    rep["demoted"] = [{"id": r["id"], "pattern": r["pattern"], "clean_hits": r.get("clean_hits")}
                      for r in demoted]

    # 2-3. MINE, then ASK.
    recent = [e for e in events if e.get("_ts", _now()) >= _now() - days * 86400]
    unk = mine(recent, days)
    rep["unknown_sources"] = len(unk.get("sources") or [])
    rep["unknown_paths"] = len(unk.get("paths") or [])
    reviews = ask_panel(unk)
    rep["panel"] = [{"model": r.get("model"), "ok": bool(r.get("ok")),
                     "error": r.get("error", "")} for r in reviews]
    props = consensus(reviews)

    # 4. VET. The models proposed; this is where code decides.
    known_good = sorted({(e.get("path") or "")[:120] for e in events
                         if int(e.get("status") or 0) < 400 and e.get("path")})
    accepted, refused = VET.vet_batch(
        [{"pattern": p["pattern"], "why": p.get("why", ""), "models": p.get("models", []),
          "agreement": p.get("agreement", 0)} for p in props], known_good)
    rep["refused"] = [{"pattern": r["pattern"], "why": r["vet"]} for r in refused]

    # 5. PROPOSE the survivors into DETECTION, and PROMOTE anything that earned it yesterday.
    added = []
    if not dry_run:
        for a in accepted:
            r = RS.propose(rs, a["pattern"], a.get("why", ""), unk.get("paths", []),
                           a.get("models", []))
            if r:
                added.append(r["id"])
    rep["added"] = added

    promoted = []
    for r in list(rs.get("rules") or []):
        ok, why = RS.can_promote(r)
        if ok and not dry_run:
            done, w = RS.promote(rs, r)
            if done:
                promoted.append({"id": r["id"], "pattern": r["pattern"], "why": w})
        elif ok:
            promoted.append({"id": r["id"], "pattern": r["pattern"], "why": "would promote: " + why})
    rep["promoted"] = promoted

    # 6. TUNE THE NUMBERS. This is the half of "not static" that has nothing to do with patterns:
    #    a limit that never moves is a limit tuned for last month's traffic. The panel votes;
    #    RS.tune() decides (quorum on the DIRECTION, median of the agreeing side, 25% step cap,
    #    clamped on read), so one confident model can move nothing.
    rep["tuned"] = []
    rep["threshold_stats"] = stats = threshold_stats(recent, days)
    votes = ask_thresholds(stats, rs) if any(p.get("ok") for p in rep.get("panel") or []) else {}
    rep["threshold_votes"] = dict(votes)
    for key in sorted(votes):
        before = RS.thresholds(rs)[key]
        if dry_run:
            # Decide out loud, change nothing. A dry run that skipped the decision entirely would
            # tell the operator nothing about what tonight's real cycle is going to do.
            ups = sum(1 for v in votes[key] if v > before)
            downs = sum(1 for v in votes[key] if v < before)
            if max(ups, downs) >= RS.QUORUM:
                rep["tuned"].append({"key": key, "from": before, "to": "(dry run)",
                                     "why": "%d of %d agree on the direction"
                                            % (max(ups, downs), len(votes[key]))})
            continue
        after, why = RS.tune(rs, key, None, votes[key])
        if after != before:
            rep["tuned"].append({"key": key, "from": before, "to": after, "why": why})

    # 7. CONSEQUENCE. Blocking an address protects us and costs the attacker nothing; the hosting
    #    provider is the only party who can take the machine away, and nobody tells them. AbuseIPDB
    #    is automatic (an API, so it cannot touch our sending reputation); hoster email is gated on
    #    repeat offending, a daily cap and a per-/24 dedupe window, because VOLUME is what gets a
    #    domain blocklisted and that domain sends our one-time passwords.
    rep["abuse"] = {"abuseipdb": [], "sent": [], "skipped": [], "errors": []}
    try:
        rep["actors"] = acts = actors(events)
    except Exception as e:
        rep["actors"] = acts = []
        rep["errors"].append(str(e))
    if acts:
        rep["abuse"] = AB.run(acts, dry_run=dry_run)

    rs["cycle"] = rs.get("cycle", 0) + 1
    rep["after"] = RS.summary(rs)
    rep["deltas"] = RS.deltas(rs, since)
    rep["verdict"] = "changed" if (added or promoted or demoted or rep["tuned"]) else "no change"

    if not dry_run:
        if not RS.save(rs):
            rep["errors"].append("ruleset could not be written: the cycle decided but nothing persisted")
        publish(rs, events)
    return rep, rs


def publish(rs, events):
    """Write the blocklist the thin clients read. A shared volume, not an API: every project
    already mounts one, and a file cannot be down."""
    try:
        blocking = [{"id": r["id"], "pattern": r["pattern"]}
                    for r, _rx in RS.active_patterns(rs, RS.TIER_BLOCK)]
        doc = {"generated": _now(), "cycle": rs.get("cycle", 0),
               "thresholds": RS.thresholds(rs), "patterns": blocking}
        os.makedirs(os.path.dirname(BLOCKLIST), exist_ok=True)
        tmp = BLOCKLIST + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        os.replace(tmp, BLOCKLIST)
        return True
    except Exception:
        return False


def render(rep):
    L = []
    P = L.append
    P("PERSEUS DAILY CYCLE  %s" % _utc(rep.get("started", _now())))
    P("=" * 66)
    b, a = rep.get("before", {}), rep.get("after", {})
    P("cycle %s -> %s   |   %d event(s) over %d day(s)"
      % (b.get("cycle"), a.get("cycle"), rep.get("events", 0), rep.get("days", 0)))
    P("rules: blocking %s -> %s, detecting %s -> %s"
      % (b.get("blocking"), a.get("blocking"), b.get("detecting"), a.get("detecting")))
    if rep.get("blind"):
        P("")
        P("!! BLIND, NOT CLEAN: %s produced no lines. Any conclusion about them is invalid."
          % ", ".join(rep["blind"]))
    for e in rep.get("errors") or []:
        P("!! %s" % e)
    P("")
    P("WHAT CHANGED")
    if rep.get("demoted"):
        for d in rep["demoted"]:
            P("  REVERTED  %s  (refused %s request(s) that looked legitimate)"
              % (d["pattern"][:50], d.get("clean_hits")))
    for p in rep.get("promoted") or []:
        P("  BLOCKING  %s  (%s)" % (p["pattern"][:50], p["why"][:60]))
    if rep.get("added"):
        P("  WATCHING  %d new pattern(s) in detection for %dh before they may refuse anything"
          % (len(rep["added"]), RS.MIN_DETECT_HOURS))
    for t in rep.get("tuned") or []:
        P("  THRESHOLD %s  %s -> %s  (%s)" % (t["key"], t["from"], t["to"], t["why"][:50]))
    if not (rep.get("demoted") or rep.get("promoted") or rep.get("added") or rep.get("tuned")):
        P("  nothing. %s" % rep.get("verdict", ""))
    P("")
    P("WHAT WAS REFUSED (the loop wanted to, the vetting said no)")
    for r in (rep.get("refused") or [])[:8]:
        P("  %-40s %s" % (r["pattern"][:40], r["why"][:70]))
    if not rep.get("refused"):
        P("  nothing proposed that failed vetting")
    P("")
    P("COVERAGE: %d source(s) doing something we cannot name, %d unnamed path(s)"
      % (rep.get("unknown_sources", 0), rep.get("unknown_paths", 0)))
    ok = [p["model"] for p in rep.get("panel") or [] if p.get("ok")]
    P("PANEL: %d of %d answered (%s)" % (len(ok), len(rep.get("panel") or []), ", ".join(ok) or "-"))
    P("THRESHOLDS: %s" % json.dumps(a.get("thresholds", {})))

    ab = rep.get("abuse") or {}
    P("")
    P("CONSEQUENCE FOR THE ATTACKER (blocking costs them nothing; their provider can act)")
    P("  repeat offenders seen on %d+ days: %d" % (AB.MIN_DAYS, len(rep.get("actors") or [])))
    P("  AbuseIPDB submissions: %d" % len(ab.get("abuseipdb") or []))
    for x in (ab.get("sent") or [])[:6]:
        P("  REPORTED  %-16s -> %s%s" % (x.get("ip"), ", ".join(x.get("to") or [])[:44],
                                         "  (dry run)" if x.get("dry_run") else ""))
    # THE SKIP REASONS ARE THE MOST USEFUL LINES HERE. A silent skip teaches nothing, and every
    # one of these is a gate doing its job: a burst is not a campaign, a research scanner is not
    # abuse, and reporting one /24 twice a month is spam with our name on it.
    for x in (ab.get("skipped") or [])[:6]:
        P("  held      %-16s %s" % (x.get("ip"), x.get("why", "")[:60]))
    for e in (ab.get("errors") or [])[:4]:
        P("  !! %s" % e[:80])
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--host", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.report:
        rs = RS.load()
        print(json.dumps(RS.summary(rs), indent=1))
        return 0
    rep, _rs = cycle(days=a.days, dry_run=a.dry_run or not a.cycle, host=a.host)
    if a.json:
        print(json.dumps(rep, indent=1, default=str))
        return 0
    text = render(rep)
    print(text)
    if a.cycle and not a.dry_run:
        # DELIVERED IS NOT THE SAME AS SENT. Both helpers return truthy only on real delivery, so
        # ask them rather than reporting success because the import worked -- the defect this
        # repository has already paid for in logship and in the spend watcher.
        tg = em = False
        try:
            sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
            from app import notify
            # NO MARKDOWN. A path in this report is attacker-chosen text; one stray underscore
            # makes Telegram reject the whole message, and the report that matters most is the
            # one about the day something happened.
            tg = bool(notify.telegram("PERSEUS daily cycle\n\n" + text[:3500]))
            em = bool(notify.email("Perseus daily cycle - %s" % rep.get("verdict", ""), text))
        except Exception as e:
            print("[!] report not delivered: %r" % e)
        if not (tg or em):
            # A report nobody receives is not a report. Say so on stdout, which promtail scrapes,
            # so a muted channel is at least queryable instead of silent.
            print(json.dumps({"evt": "perseus_report", "result": "undelivered",
                              "telegram": tg, "email": em}))
        else:
            print("[i] report delivered: telegram=%s email=%s" % (tg, em))
    return 0


if __name__ == "__main__":
    sys.exit(main())
