#!/usr/bin/env python3
"""agent_forensics.py -- was the client that drained our inference a HUMAN, a SCRIPT, or an AGENT?

    python agent_forensics.py                        # the known actor, last 12 days
    python agent_forensics.py --ip 1.2.3.4 --days 20
    python agent_forensics.py --selftest             # prove the classifier separates the 3 shapes

WHAT THIS CAN ESTABLISH, AND WHAT IT CANNOT. That distinction is the whole point of the file.

  ESTABLISHED FROM EVIDENCE (behavioural, high confidence):
    * automated vs a person at a keyboard -- inter-arrival regularity, 24h coverage, plateau length,
      request concurrency. A human cannot issue evenly-spaced calls for eleven hours without a
      break, and a cron loop cannot produce human think-time.
    * a fixed-context application vs a growing conversation -- the variance of tokens_in. A chat
      accumulates history and grows monotonically; an app re-sends one system prompt every call.
    * multi-model ROUTING vs a single hardcoded model, and whether a model switch FOLLOWS an error
      (a fallback chain) or alternates steadily (a router).
    * how fast the estate was mapped -- the gap between /openapi.json, /api/models and /api/chat.

  INFERENCE, NOT PROOF (reported as such):
    * "agentic" specifically, as opposed to a competent script. The tell is a DEPENDENT loop: the
      next request begins a short, consistent interval after the previous RESPONSE completed, with
      variable request sizes and an error-driven model fallback. That is what an agent framework
      does; a determined engineer can write the same thing by hand, and no log can tell them apart.

  CANNOT BE ESTABLISHED, AT ALL:
    * the prompts. We do not log request bodies, deliberately -- they are third-party content and
      may carry other people's personal data. Content attribution is therefore impossible, and no
      amount of analysis here changes that. I am NOT proposing we start logging them.
    * identity, intent, or which framework. An IP is an address, not a person.

METHOD NOTE. Timing uses LOKI's nanosecond timestamp, not the app's `ts` field, which is
`int(time.time())` -- one-second granularity would destroy the inter-arrival signal that most of
this rests on. Read the field, do not assume it.

READ-ONLY. One ssh session, log queries only. Nothing is sent to the address under analysis: this
repository does not scan back (StGB s.202a/s.303b, EU Directive 2013/40, US CFAA s.1030).
"""
import argparse
import json
import math
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ACTOR = "24.199.91.170"          # the address measured on the jobhuntwow /api/chat abuse
JHW = '{container=~".*jhw-web.*"}'


# ── signal extraction (pure functions, so the classifier can be proven on known input) ────────

def _gaps(ts):
    return [b - a for a, b in zip(sorted(ts), sorted(ts)[1:])]


def regularity(ts):
    """Coefficient of variation of the inter-arrival gaps.

    CV is stdev/mean, so it is scale-free: it says how IRREGULAR the rhythm is, independent of how
    fast it is. A person typing has enormous variance (seconds, then minutes of reading). A fixed
    sleep loop has almost none. An agent sits in between, because each step waits on a model."""
    g = [x for x in _gaps(ts) if x >= 0]
    if len(g) < 8:
        return None
    m = statistics.mean(g)
    if m <= 0:
        return None
    return statistics.pstdev(g) / m


def circadian(ts):
    """Hours of the day the client was active, and its longest silence.

    A human sleeps. Across several days that shows up as a recurring multi-hour gap and as some
    hours of the day never being used at all. A machine has neither."""
    if not ts:
        return None
    hours = {time.gmtime(t).tm_hour for t in ts}
    return {"hours_active": len(hours), "longest_silence_h": round(max(_gaps(ts) or [0]) / 3600.0, 2)}


def longest_plateau(ts, max_gap=None):
    """Longest continuous run of activity with no break longer than max_gap seconds.

    THE THRESHOLD MUST SCALE WITH THE CLIENT'S OWN BEAT. A fixed 5 minutes reported 0.75h for an
    actor whose longest silence in twelve days was SEVENTEEN MINUTES -- because its median interval
    was 6.2 minutes, so nearly every normal gap "broke" the plateau. That understates a client that
    in truth never stopped. Scale to three times its own median gap, floor 5 minutes."""
    if not ts:
        return 0.0
    ts = sorted(ts)
    if max_gap is None:
        g = [x for x in _gaps(ts) if x >= 0]
        max_gap = max(300.0, 3.0 * statistics.median(g)) if g else 300.0
    best = start = ts[0]
    best_len = 0.0
    for a, b in zip(ts, ts[1:]):
        if b - a > max_gap:
            best_len = max(best_len, a - start)
            start = b
    return round(max(best_len, ts[-1] - start) / 3600.0, 2)


def concurrency(events):
    """Maximum number of requests in flight at once, from ts + duration.

    One person clicking is 1. A worker pool is N. This is the cheapest way to tell a loop from a
    fleet, and it needs no content."""
    edges = []
    for e in events:
        t, ms = e.get("_ts"), e.get("ms") or 0
        if t is None:
            continue
        edges.append((t, 1))
        edges.append((t + ms / 1000.0, -1))
    edges.sort()
    cur = peak = 0
    for _, d in edges:
        cur += d
        peak = max(peak, cur)
    return peak


def context_shape(calls):
    """Is the prompt a FIXED application context, or a conversation that grows?

    Returns the spread of tokens_in and whether it trends upward. A chat session accumulates its
    own history, so tokens_in climbs; an app or an agent step re-sends a constant scaffold."""
    ti = [c.get("tokens_in") or 0 for c in sorted(calls, key=lambda c: c.get("_ts", 0))
          if (c.get("tokens_in") or 0) > 0]
    if len(ti) < 6:
        return None
    m = statistics.mean(ti)
    cv = statistics.pstdev(ti) / m if m else 0
    # Spearman-ish: does it climb with time? +1 climbing, -1 falling, ~0 flat.
    n = len(ti)
    mid = n // 2
    trend = (statistics.mean(ti[mid:]) - statistics.mean(ti[:mid])) / m if m else 0
    return {"mean_in": int(m), "cv": round(cv, 3), "trend": round(trend, 3), "n": n}


def model_behaviour(calls):
    """Distinct models, and WHY they changed.

    A switch that follows a failed call is a FALLBACK CHAIN. Steady alternation between a cheap and
    an expensive model is a ROUTER. Both are framework behaviour; one hardcoded model is a script."""
    calls = sorted(calls, key=lambda c: c.get("_ts", 0))
    models = [c.get("model") for c in calls if c.get("model")]
    if not models:
        return None
    switches = after_error = 0
    for i in range(1, len(calls)):
        if calls[i].get("model") != calls[i - 1].get("model"):
            switches += 1
            if str(calls[i - 1].get("status", "ok")) != "ok":
                after_error += 1
    return {"distinct": len(set(models)), "switches": switches,
            "switch_after_error": after_error, "calls": len(calls),
            "models": sorted(set(models))}


def dependency(events):
    """Gap between one response FINISHING and the next request starting.

    This is the sharpest agent signal available without content. A loop that feeds the model's
    answer into the next step resumes almost immediately and consistently. A human reads the answer
    first, and reading time is wildly variable."""
    ev = sorted([e for e in events if e.get("_ts") is not None], key=lambda e: e["_ts"])
    think = []
    for a, b in zip(ev, ev[1:]):
        done = a["_ts"] + (a.get("ms") or 0) / 1000.0
        d = b["_ts"] - done
        if 0 <= d < 3600:
            think.append(d)
    if len(think) < 8:
        return None
    return {"median_s": round(statistics.median(think), 2),
            "cv": round(statistics.pstdev(think) / statistics.mean(think), 3)
            if statistics.mean(think) else None, "n": len(think)}


def breakdown(events):
    """WHAT WAS IT ACTUALLY ASKING FOR, AND WAS IT STILL BEING SERVED?

    The first real run reported 1,539 requests and 34 llm_call events -- so 98% of the traffic
    produced no model call at all, and the tool showed neither what those requests were nor whether
    they were being refused. That is the decisive cut: a client that keeps beating every six minutes
    AFTER the locks went on is a retry loop with nobody watching it, which says more about
    automation than any timing statistic."""
    days, status, paths = {}, {}, {}
    for e in events:
        t = e.get("_ts")
        if t is None:
            continue
        days[time.strftime("%Y-%m-%d", time.gmtime(t))] = \
            days.get(time.strftime("%Y-%m-%d", time.gmtime(t)), 0) + 1
        st = str(e.get("status") or "?")
        status[st] = status.get(st, 0) + 1
        p = (e.get("path") or "?").split("?")[0]
        paths[p] = paths.get(p, 0) + 1
    return {"days": days, "status": status, "distinct_paths": len(paths),
            "top_paths": sorted(paths.items(), key=lambda kv: -kv[1])[:8]}


def instrumentation_overlap(http, llm):
    """DOES THE MODEL-CALL LOG COVER THE SAME PERIOD AS THE TRAFFIC?

    The first real run reported 34 llm_call events against 1,521 served requests and I nearly read
    that as '98% never reached inference'. But `evt=llm_call` was only added to jobhuntwow days
    before, and jhw-web's writes to the shared events.log were failing on a permission bug for most
    of that time -- so a thin ratio may be measuring WHEN WE STARTED LOOKING, not what the client
    did. Compare the two coverage windows before anyone draws that conclusion."""
    if not http or not llm:
        return None
    ht, lt = sorted(e["_ts"] for e in http), sorted(e["_ts"] for e in llm)
    span = ht[-1] - ht[0]
    if span <= 0:
        return None
    covered = max(0.0, min(ht[-1], lt[-1]) - max(ht[0], lt[0]))
    return {"http_span_h": round(span / 3600.0, 1),
            "llm_covers_h": round(covered / 3600.0, 1),
            "llm_starts_h_late": round((lt[0] - ht[0]) / 3600.0, 1),
            "partial": covered < 0.75 * span}


def recon(events):
    """How long between mapping the API and using it. Seconds means a program read the schema."""
    first = {}
    for e in sorted(events, key=lambda e: e.get("_ts", 0)):
        p = (e.get("path") or "").split("?")[0]
        for k in ("/openapi.json", "/api/models", "/api/chat", "/docs"):
            if p == k and k not in first:
                first[k] = e["_ts"]
    if "/api/chat" not in first:
        return None
    src = min((first[k] for k in ("/openapi.json", "/api/models", "/docs") if k in first),
              default=None)
    if src is None:
        return None
    gap = first["/api/chat"] - src
    # A NEGATIVE INTERVAL IS NOT FAST RECONNAISSANCE. It means the endpoint was called BEFORE the
    # schema was ever read, so this client did not learn it here -- it already knew, or it learned
    # elsewhere. Reporting "-1000s from reading the schema to calling it" as evidence that a program
    # read the schema is a claim the data does not support.
    if gap < 0:
        return {"map_to_use_s": None, "mapped": sorted(k for k in first if k != "/api/chat"),
                "note": "the endpoint was called BEFORE the schema was read: this client did not "
                        "learn the API here"}
    return {"map_to_use_s": round(gap, 1),
            "mapped": sorted(k for k in first if k != "/api/chat")}


# ── the verdict ──────────────────────────────────────────────────────────────────────────────

def classify(sig):
    """Score the signals. Every line names the evidence AND its direction, so a reader can
    disagree with the conclusion while still using the measurements."""
    votes, unknown = [], []

    r = sig.get("regularity")
    if r is None:
        unknown.append("inter-arrival regularity (fewer than 8 requests)")
    elif r < 0.35:
        votes.append(("AUTOMATED", "inter-arrival CV %.2f - a metronome, not a person" % r))
    elif r < 1.2:
        votes.append(("AGENT-LIKE", "inter-arrival CV %.2f - variable but bounded, the shape of a "
                                    "loop that waits on a model" % r))
    else:
        votes.append(("HUMAN-LIKE", "inter-arrival CV %.2f - long irregular pauses" % r))

    c = sig.get("circadian")
    if c:
        if c["hours_active"] >= 20:
            votes.append(("AUTOMATED", "active in %d of 24 hours - no sleep" % c["hours_active"]))
        elif c["longest_silence_h"] >= 5:
            votes.append(("HUMAN-LIKE", "a %.1fh silence - consistent with sleep"
                          % c["longest_silence_h"]))

    p = sig.get("plateau_h") or 0
    if p >= 4:
        votes.append(("AUTOMATED", "%.1fh of continuous activity with no break over 5 min" % p))

    k = sig.get("concurrency") or 0
    if k >= 3:
        votes.append(("AUTOMATED", "%d requests in flight at once - a worker pool" % k))
    elif k == 1:
        votes.append(("SERIAL", "strictly one request at a time - a single loop or one person"))

    cs = sig.get("context")
    if cs:
        if cs["cv"] < 0.15 and abs(cs["trend"]) < 0.1:
            votes.append(("AGENT-LIKE", "tokens_in flat (mean %d, CV %.2f) - a FIXED scaffold "
                                        "re-sent each call, not a conversation accumulating history"
                          % (cs["mean_in"], cs["cv"])))
        elif cs["trend"] > 0.4:
            votes.append(("HUMAN-LIKE", "tokens_in grows %.0f%% across the window - a conversation "
                                        "carrying its own history" % (cs["trend"] * 100)))

    m = sig.get("models")
    if m:
        if m["switch_after_error"] >= 2:
            votes.append(("AGENT-LIKE", "%d model switches immediately after a failed call - a "
                                        "FALLBACK CHAIN, i.e. framework behaviour"
                          % m["switch_after_error"]))
        elif m["distinct"] >= 2 and m["switches"] >= 4:
            votes.append(("AGENT-LIKE", "%d models alternating %d times - a ROUTER picking a model "
                                        "per step" % (m["distinct"], m["switches"])))
        elif m["distinct"] == 1:
            votes.append(("SCRIPT-LIKE", "one hardcoded model for every call"))

    d = sig.get("dependency")
    # A SCHEDULE'S "THINK TIME" IS THE CLOCK, NOT A PERSON READING. If the gap between a response
    # finishing and the next request is essentially the same distribution as the gap between
    # requests, the responses are short next to the interval -- so the interval is set by something
    # other than anyone reading, and the signal carries no information about a human.
    #
    # The first version only suppressed a metronome (CV < 0.35). The real actor beat every ~6
    # minutes with CV 0.77, its think-time CV was 0.771 -- IDENTICAL to its inter-arrival CV, which
    # is the tell -- and it scored a spurious HUMAN-LIKE vote on a client that ran for 12 days
    # without a 20-minute break. A signal that is an artifact of another signal must be suppressed,
    # not averaged in.
    same_shape = (d and r is not None and d.get("cv") is not None and abs(d["cv"] - r) < 0.05)
    if d and ((r is not None and r < 0.35) or same_shape):
        unknown.append("response-to-request think time (its spread matches the inter-arrival "
                       "spread, so the gap measures the schedule, not anyone reading)")
    elif d:
        if d["median_s"] < 5 and (d["cv"] or 9) < 1.0:
            votes.append(("AGENT-LIKE", "next request starts %.1fs after the previous response "
                                        "completes, consistently (CV %.2f) - a dependent loop, "
                                        "nobody is reading the answer" % (d["median_s"], d["cv"])))
        elif d["median_s"] > 20:
            votes.append(("HUMAN-LIKE", "%.0fs of think-time between answer and next question"
                          % d["median_s"]))

    rc = sig.get("recon")
    if rc and rc.get("map_to_use_s") is None:
        unknown.append("reconnaissance speed (%s)" % rc.get("note", "not measurable"))
    elif rc:
        if rc["map_to_use_s"] < 120:
            votes.append(("AUTOMATED", "%.0fs from reading %s to calling /api/chat - a program read "
                          "the schema" % (rc["map_to_use_s"], ", ".join(rc["mapped"]))))
        else:
            votes.append(("HUMAN-LIKE", "%.0f min between mapping the API and using it"
                          % (rc["map_to_use_s"] / 60.0)))

    auto = sum(1 for v, _ in votes if v in ("AUTOMATED", "AGENT-LIKE", "SCRIPT-LIKE"))
    human = sum(1 for v, _ in votes if v == "HUMAN-LIKE")
    agent = sum(1 for v, _ in votes if v == "AGENT-LIKE")

    if not votes:
        verdict = "INSUFFICIENT EVIDENCE - decide nothing"
    elif human > auto:
        verdict = "A PERSON, interactively"
    elif agent >= 2 and auto > human:
        verdict = "AUTOMATED, and AGENT-SHAPED (inference, not proof)"
    elif auto > human:
        verdict = "AUTOMATED - a program, but the evidence does not separate agent from script"
    else:
        verdict = "MIXED - the signals disagree; treat as undetermined"
    return verdict, votes, unknown


# ── evidence collection ──────────────────────────────────────────────────────────────────────

def _script(ip, start, end):
    """One ssh session. Log-line queries only: we need per-request timestamps, and an aggregate
    would destroy exactly the signal this analysis rests on.

    THE QUERY MUST BE URL-ENCODED. The first version interpolated raw LogQL -- braces, quotes,
    pipes, spaces -- straight into a query string. Loki rejected it, `_parse` saw no streams, and
    the report said "0 requests" about a client that had made 1,538. A failed query rendered as
    absence of evidence is the defect this repository keeps paying for, so `cost_report._enc` (the
    ONE encoder) is used here and the raw body is kept for the blind check below."""
    from cost_report import _enc
    sel = '{container=~".*jhw-web.*"}'
    # Filter on the ADDRESS only, and decide what an event IS in Python. json.dumps' separator
    # spacing is not something to guess at inside a substring filter.
    body = [
        "L=$(docker ps --format '{{.Names}}' | grep -iE 'loki' | head -1)",
        'echo "#### LOKI"; echo "${L:-NONE}"',
        '[ -z "$L" ] && exit 0',
        # limit + newest-first: Loki caps one response, so a wide window returns a truncated slice.
        # The count is reported, so a slice that hit the cap is visible rather than silent.
        "s(){ docker exec \"$L\" wget -qO- \"http://127.0.0.1:3100/loki/api/v1/query_range"
        "?query=$1&start=%s&end=%s&limit=5000&direction=backward\" 2>/dev/null; }" % (start, end),
        # VISIBILITY FIRST. If the unfiltered stream is empty the container never shipped a line,
        # and every conclusion below it would be about our own blindness, not about the client.
        'echo "#### PROBE"', 's "%s"' % _enc(sel),
        'echo "#### HTTP"', 's "%s"' % _enc('%s |= "%s"' % (sel, ip)),
        'echo "#### LLM"', 's "%s"' % _enc('%s |= "llm_call"' % sel),
        'echo "#### END"',
    ]
    return "\n".join(body) + "\n"


def _sections(text):
    """recover.sections is the ONE implementation of the '#### NAME' split. A second copy here
    would drift from it the first time the delimiter changed."""
    import recover as RC
    return RC.sections(text)


def _answered(raw):
    """Did Loki ANSWER this query? An error body, an empty body or anything that is not a success
    envelope means the question was never asked -- which is a different fact from 'the client made
    no requests', and must never be rendered as the second."""
    try:
        doc = json.loads(raw or "")
    except Exception:
        return False
    return isinstance(doc, dict) and doc.get("status") == "success"


def _parse(raw):
    """Loki streams -> event dicts carrying LOKI's nanosecond timestamp as `_ts`."""
    ev = []
    try:
        doc = json.loads(raw or "{}")
    except Exception:
        return ev
    for st in (doc.get("data") or {}).get("result", []):
        for pair in st.get("values") or []:
            try:
                ts_ns, line = pair[0], pair[1]
                # the app line may be wrapped by the docker json driver
                i = line.find("{")
                e = json.loads(line[i:]) if i >= 0 else {}
                if isinstance(e, dict):
                    e["_ts"] = int(ts_ns) / 1e9
                    ev.append(e)
            except Exception:
                continue
    return ev


def collect(ip, days, host=None):
    try:
        import recover as RC
    except Exception as e:
        return None, "recover.py not importable: %r" % e
    prev = RC.HOST
    if host:
        RC.HOST = host                      # override the ATTRIBUTE; RC reads the env at import
    try:
        end = int(time.time())
        start = end - days * 86400
        out, err, rc = RC.ssh_script(_script(ip, start * 10**9, end * 10**9), timeout=240)
    except Exception as e:
        return None, repr(e)[:200]
    finally:
        RC.HOST = prev
    sec = _sections(out or "")
    if (sec.get("LOKI") or "").strip() in ("", "NONE"):
        return None, "no Loki container reachable (rc=%s) %s" % (rc, (err or "")[:120])
    # THE QUERY HAS TO HAVE BEEN ANSWERED before its emptiness means anything.
    for name in ("PROBE", "HTTP", "LLM"):
        if not _answered(sec.get(name, "")):
            return None, ("Loki did not answer the %s query (malformed query, or the endpoint "
                          "refused it). Body: %r" % (name, (sec.get(name) or "")[:160]))
    probe = _parse(sec.get("PROBE", ""))
    if not probe:
        return None, ("the jhw-web log stream is EMPTY for this window. The container shipped "
                      "nothing, so this is OUR blindness, not the client's innocence. Check that "
                      "jhw-web is running and that videodead-promtail is scraping docker stdout.")
    http = [e for e in _parse(sec.get("HTTP", "")) if e.get("evt") == "http"]
    llm = [e for e in _parse(sec.get("LLM", "")) if e.get("evt") == "llm_call"]
    return {"http": http, "llm": llm, "stream_lines": len(probe)}, ""


def analyse(data):
    http = [e for e in data["http"] if e.get("_ts")]
    llm = [e for e in data["llm"] if e.get("_ts")]
    ts = [e["_ts"] for e in http]
    # AN llm_call LINE CARRIES NO IP -- it records model, caller and tokens, never the address.
    # So the model and context signals can only be tied to this actor BY TIME. Narrow them to the
    # actor's own request window (with a small margin for the call that outlives its request), and
    # report the overlap, so a reader can see how strong that link is instead of assuming it.
    overlap = None
    if ts and llm:
        lo, hi = min(ts) - 30, max(ts) + 120
        inside = [c for c in llm if lo <= c["_ts"] <= hi]
        overlap = {"in_actor_window": len(inside), "in_window_total": len(llm)}
        llm = inside
    return {
        "stream_lines": data.get("stream_lines"),
        "llm_link": overlap,
        "requests": len(http), "llm_calls": len(llm),
        "regularity": regularity(ts),
        "circadian": circadian(ts),
        "plateau_h": longest_plateau(ts),
        "concurrency": concurrency(http),
        "context": context_shape(llm),
        "models": model_behaviour(llm),
        "dependency": dependency(http),
        "recon": recon(http),
        "breakdown": breakdown(http),
        "coverage": instrumentation_overlap(http, llm),
        "last_seen": max(ts) if ts else None,
    }


def render(sig, ip, days):
    verdict, votes, unknown = classify(sig)
    L = ["", "=" * 78,
         "  CLIENT BEHAVIOUR FORENSICS  ·  %s  ·  last %d days" % (ip, days),
         "=" * 78, ""]
    L.append("  EVIDENCE COLLECTED")
    L.append("    http requests attributed : %d" % sig["requests"])
    L.append("    llm_call events in window: %d" % sig["llm_calls"])
    lk = sig.get("llm_link")
    if lk:
        L.append("    llm_call TIED TO THIS ACTOR BY TIME ONLY: %d of %d in the window."
                 % (lk["in_actor_window"], lk["in_window_total"]))
        L.append("      An llm_call line records model, caller and tokens - never an address. If")
        L.append("      another client was calling in the same minutes, the model and token signals")
        L.append("      below are shared with it. Treat them as weaker than the timing signals.")
    if not sig["requests"]:
        L.append("")
        n = sig.get("stream_lines")
        L.append("  NO REQUESTS FOUND. That is not 'the client was innocent' -- it is 'this window")
        L.append("  holds no evidence'. Widen --days, or the retention has aged the incident out.")
        if n:
            L.append("")
            L.append("  The stream itself IS visible (%d lines from jhw-web in this window), so we")
            L[-1] = L[-1] % n
            L.append("  are not blind -- this address simply does not appear in it. Check the")
            L.append("  address, or widen the window past Loki's retention boundary.")
        return "\n".join(L)
    bd = sig.get("breakdown") or {}
    if bd.get("days"):
        L.append("")
        L.append("  WHAT IT ASKED FOR, AND WHETHER IT WAS SERVED")
        L.append("    per day:")
        for d in sorted(bd["days"]):
            n = bd["days"][d]
            L.append("      %s  %5d  %s" % (d, n, "#" * min(50, max(1, n // 8))))
        L.append("    response codes: " + ", ".join(
            "%s x%d" % (k, v) for k, v in sorted(bd["status"].items(), key=lambda kv: -kv[1])))
        L.append("    top paths:")
        for p, n in bd["top_paths"]:
            L.append("      %6d  %s" % (n, p[:70]))
        served = sum(v for k, v in bd["status"].items() if k.startswith("2"))
        refused = sum(v for k, v in bd["status"].items() if k[:1] in "45")
        if refused and sig["requests"]:
            L.append("    -> %d of %d refused (%.0f%%). A client that keeps its rhythm while being"
                     % (refused, sig["requests"], 100.0 * refused / sig["requests"]))
            L.append("       refused is a retry loop with nobody watching it. That is a stronger")
            L.append("       statement about automation than any timing statistic here.")
        cov = sig.get("coverage")
        if served and sig["llm_calls"] is not None and sig["llm_calls"] < served / 4:
            L.append("    -> %d model call(s) against %d served requests."
                     % (sig["llm_calls"], served))
            if cov and cov["partial"]:
                # DO NOT READ A THIN RATIO AS CLIENT BEHAVIOUR WHEN IT MAY BE OUR OWN COVERAGE.
                L.append("       BUT the model-call log covers only %.1fh of this client's %.1fh"
                         % (cov["llm_covers_h"], cov["http_span_h"]))
                L.append("       and starts %.1fh after its first request. That gap is WHEN WE"
                         % cov["llm_starts_h_late"])
                L.append("       STARTED MEASURING, not proof the traffic skipped inference.")
                L.append("       The billed tokens at the provider are authoritative here.")
            else:
                L.append("       The model-call log spans this client's activity, so most of these")
                L.append("       requests genuinely did not reach inference.")
    if (bd.get("distinct_paths") or 0) == 1 and sig["requests"] > 50:
        L.append("")
        L.append("  ZERO RECONNAISSANCE: %d requests, ONE endpoint, nothing else ever probed."
                 % sig["requests"])
        L.append("    It did not search for the endpoint - it arrived knowing it. That points to")
        L.append("    prior knowledge (a schema read earlier or from another address, or a shared")
        L.append("    target list), i.e. something targeted rather than opportunistic scanning.")
    ls = sig.get("last_seen")
    if ls:
        quiet = (time.time() - ls) / 3600.0
        L.append("")
        L.append("  LAST SEEN: %s UTC (%.1fh ago)."
                 % (time.strftime("%Y-%m-%d %H:%M", time.gmtime(ls)), quiet))
        if quiet > 12:
            L.append("    It has stopped. Whether it gave up, was locked out, or simply finished is")
            L.append("    not decidable from these logs - check what changed at that hour.")
    L.append("")
    L.append("  SIGNALS")
    for k in ("regularity", "circadian", "plateau_h", "concurrency", "context", "models",
              "dependency", "recon"):
        v = sig.get(k)
        L.append("    %-12s %s" % (k, "not determinable" if v is None else
                                   (json.dumps(v) if isinstance(v, dict) else round(v, 3)
                                    if isinstance(v, float) else v)))
    L.append("")
    L.append("  WHAT EACH SIGNAL SAYS")
    for tag, why in votes:
        L.append("    [%-11s] %s" % (tag, why))
    for u in unknown:
        L.append("    [unknown    ] %s" % u)
    L.append("")
    L.append("  VERDICT: %s" % verdict)
    L.append("")
    L.append("  WHAT THIS CANNOT TELL YOU, AND NO ANALYSIS OF THESE LOGS EVER WILL:")
    L.append("    - the prompts. Request bodies are not logged, deliberately: they are third-party")
    L.append("      content and may carry other people's personal data. Content attribution is")
    L.append("      therefore impossible, and starting to log them is not the answer.")
    L.append("    - who, or why. An address is not a person.")
    L.append("    - agent framework vs a hand-written loop. The shapes are identical on the wire.")
    return "\n".join(L)


# ── self-test: prove the classifier SEPARATES the three shapes ───────────────────────────────

def _synth(kind, n=120, t0=1_756_000_000):
    """Three traces whose ground truth we know. A classifier that has never been shown a case it
    should REJECT is a classifier nobody should trust."""
    import random
    random.seed(7)
    ev, t = [], t0
    for i in range(n):
        if kind == "human":
            t += random.choice([4, 9, 15, 40, 120, 300, 900])      # reading, pausing, leaving
            if i and i % 30 == 0:
                t += 8 * 3600                                       # sleep
            ms, ti = random.randint(800, 4000), 400 + i * 120       # conversation grows
            model = "deepseek-3.2"
        elif kind == "cron":
            t += 60                                                 # a metronome
            ms, ti, model = 1500, 900, "deepseek-3.2"
        else:                                                       # agent
            ms = random.randint(1500, 9000)
            t += ms / 1000.0 + random.uniform(0.2, 1.4)             # resumes on completion
            ti = 17800 + random.randint(-150, 150)                  # fixed scaffold
            model = "glm-5.3-flash" if i % 3 else "deepseek-v4-pro-0813"
        ev.append({"_ts": t, "ms": ms, "path": "/api/chat", "evt": "http",
                   "tokens_in": ti, "tokens_out": 300, "model": model, "status": "ok"})
    return ev


def selftest():
    ok = True
    for kind, expect in (("human", "PERSON"), ("cron", "AUTOMATED"), ("agent", "AGENT-SHAPED")):
        ev = _synth(kind)
        sig = analyse({"http": ev, "llm": ev})
        verdict, votes, _ = classify(sig)
        good = expect in verdict
        ok = ok and good
        print("  %-6s -> %-55s %s" % (kind, verdict, "OK" if good else "WRONG"))
        for tag, why in votes:
            print("           [%-11s] %s" % (tag, why[:96]))
    print("\n  %s" % ("classifier separates all three shapes"
                      if ok else "CLASSIFIER DOES NOT DISCRIMINATE - do not trust its verdicts"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default=ACTOR)
    ap.add_argument("--days", type=int, default=12)
    ap.add_argument("--host", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    data, err = collect(a.ip, a.days, a.host)
    if data is None:
        print("[X] could not collect evidence: %s" % err)
        print("    Deciding nothing. BLIND is not INNOCENT.")
        return 2
    print(render(analyse(data), a.ip, a.days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
