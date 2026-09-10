"""The defence as DATA: a versioned, bounded, self-reverting ruleset shared by every project.

WHY THIS FILE EXISTS. Until now each project carried its own hard-coded detection list, its own
thresholds, and in four of six cases no cost control at all. A static defence that lives in six
places is really six defences, all drifting, and the one that matters is always the one nobody
updated. On 2026-09-06 that cost a week of investigation and a bill nobody could attribute.

So the defence becomes one artifact with a version number, and it CHANGES on a schedule.

THE AUTONOMY MODEL (operator's decision, 2026-09-07: "full auto within bounds").
A rule may be promoted to BLOCKING automatically when all of these hold, and they are checked by
deterministic code, never by a model:
  * `vet.py` passed it (valid regex, matches nothing we serve, not catastrophically broad);
  * 3 of 4 reviewers, one per vendor, agreed on the DIRECTION;
  * it spent MIN_DETECT_HOURS in detection first, seeing real traffic, without hitting anything
    that looked legitimate.
The models PROPOSE. This file DECIDES. That division is the whole reason a bad afternoon from one
vendor cannot change what the estate refuses.

AND THE PART THE OPERATOR DID NOT ASK FOR, WHICH IS WHY IT IS HERE.
Full autonomy without a way back is a one-way door. `review()` DEMOTES a blocking rule to detection
by itself when it starts refusing traffic that does not look hostile, and records why. The same
doctrine as the FP auditor that may flag but never gut a deck, and the co-tenant guard that refuses
rather than empty an estate: an automatic process may narrow, it may never quietly do harm.

BOUNDS ARE ENFORCED ON READ, not on write. A hand-edited file, a corrupt file, or a model that
somehow reached the store still cannot produce a value outside the committed range, because every
consumer goes through `thresholds()`. That is the lesson from ENRICH_MODELS having four homes: a
constraint that is applied at one entry point is a constraint somebody will eventually route around.
"""
import json
import os
import re
import time

VERSION = 1

# ── committed bounds. A number outside these cannot be reached, whatever the file says ────────
BOUNDS = {
    "ip_per_min":      (3, 60),      # requests one address may make in a minute
    "ip_per_day":      (50, 5000),
    "net_per_min":     (5, 200),     # ...and one /24
    "probe_score":     (2, 20),      # distinct probe paths before an address is hostile
    "slow_distinct":   (4, 60),      # distinct probe paths over the long window
    "block_minutes":   (5, 1440),
}
DEFAULTS = {"ip_per_min": 8, "ip_per_day": 120, "net_per_min": 20,
            "probe_score": 4, "slow_distinct": 12, "block_minutes": 15}

STEP_CAP = 0.25          # no threshold may move more than 25% in one cycle
MIN_DETECT_HOURS = 24    # a new pattern watches for a day before it may refuse anything
QUORUM = 3               # of 4 reviewers, and they must be different vendors

# A RULE THAT HAS NEVER MATCHED ANYTHING IN A MONTH IS COST WITHOUT COVER. It is compiled on every
# client reload and evaluated on every request of six properties, and it is evidence of nothing.
# THIRTY DAYS, AND THE NUMBER IS WHY THIS IS A WEEKLY JOB: a rule cannot be called dormant from a
# two-day window, so the daily cycle is structurally unable to make this judgement. Retiring is
# also the only tier transition that is safe to make from silence, because retiring REMOVES a
# refusal and can therefore never deny a real visitor.
DORMANT_DAYS = int(os.environ.get("PERSEUS_DORMANT_DAYS", "30"))

TIER_DETECT, TIER_BLOCK, TIER_RETIRED = "detect", "block", "retired"

# WHERE A RULE CAME FROM. `propose()` stamps every rule with one of these and the ledger keeps it
# for the life of the rule, because six weeks from now the only useful question about a pattern is
# "why is this here".
SOURCE_MINED = "daily-mining"
SOURCE_SEED = "seed"

STORE = os.environ.get("PERSEUS_RULESET", "/var/log/colt/perseus_ruleset.json")


def atomic_write(path, render):
    """Write a file so no reader ever sees it half-written. THE one implementation in this package.

    `render` is called with an open handle, so the caller decides the format (json.dump, write...).

    THE RETRY IS A PLATFORM FIX. On POSIX a rename over an open file always succeeds and a reader
    keeps its handle to the old inode. On WINDOWS os.replace raises PermissionError while any
    handle is open, because Python's open() does not pass FILE_SHARE_DELETE. The hub only ever runs
    on the Linux droplet -- but perseus/client.py is COPIED INTO SIX PROJECTS and reads these files,
    and the test suite runs on the operator's Windows box. A control that behaves differently there
    is one he has to take on trust, and this repository has paid six times for exactly that gap.
    """
    tmp = "%s.tmp-%d" % (path, os.getpid())
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            render(fh)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False
    for _ in range(30):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:          # Windows: a reader is holding the destination open
            time.sleep(0.02)
        except Exception:
            break
    try:
        os.remove(tmp)
    except Exception:
        pass
    return False


def _now():
    return time.time()


def clamp(key, value):
    """Force a value into the committed range. Returns None for an unknown key or junk, never a
    number: an unbounded key must not silently become a threshold."""
    lo_hi = BOUNDS.get(key)
    if not lo_hi:
        return None
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    lo, hi = lo_hi
    return max(lo, min(hi, v))


def blank():
    return {"version": VERSION, "created": _now(), "cycle": 0,
            "thresholds": dict(DEFAULTS), "rules": [], "history": []}


def load(path=None):
    p = path or STORE
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict) or "rules" not in d:
            return blank()
        return d
    except Exception:
        # A missing or unreadable store must not disarm the defence: the committed defaults are
        # a working ruleset on their own.
        return blank()


def save(rs, path=None):
    return atomic_write(path or STORE, lambda fh: json.dump(rs, fh, indent=1, sort_keys=True))


def thresholds(rs):
    """THE ONLY WAY TO READ A THRESHOLD. Clamped here, so no caller can be handed a value outside
    the committed range no matter how the store was written."""
    out = {}
    for k, dflt in DEFAULTS.items():
        v = clamp(k, (rs.get("thresholds") or {}).get(k, dflt))
        out[k] = dflt if v is None else v
    return out


def active_patterns(rs, tier=None):
    """Compiled patterns at a tier. A pattern that no longer compiles is skipped, not fatal: the
    store is data and data can rot, but the defence must keep running."""
    out = []
    for r in rs.get("rules") or []:
        if r.get("tier") == TIER_RETIRED:
            continue
        if tier and r.get("tier") != tier:
            continue
        try:
            out.append((r, re.compile(r["pattern"], re.I)))
        except Exception:
            continue
    return out


def _class_table():
    """perseus.client's committed class table, or None. NEVER a second copy of it.

    TWO import spellings because this package is run two ways: as `perseus.hub`, with the repository
    root on sys.path, and as a SCRIPT from inside perseus/ -- which is how the systemd unit starts it,
    and there only the flat name resolves. hub.py already puts both directories on the path for
    exactly this reason, and getting it wrong is how `import abuse` once took the timer down under
    `set -e` while production was fine. Returning None
    rather than a hard-coded fallback list is the whole point: if the shared table cannot be read,
    the seed is EMPTY and the caller says so. A retyped copy would be a second home for the one
    vocabulary five sidecars already score with, and it would drift the day somebody edits one.
    """
    for mod in ("perseus.client", "client"):
        try:
            m = __import__(mod, fromlist=["CLASSES"])
        except Exception:
            continue
        table = getattr(m, "CLASSES", None)
        if table:
            return list(table), "%s.CLASSES" % mod
    return None, ""


def seed_candidates():
    """(candidates, provenance). The committed probe corpus, offered to the promotion gate.

    WHY THIS EXISTS. `hub.mine()` proposes only what the corpus CANNOT already name -- by
    construction, a technique we detect perfectly is never a candidate. So on an estate whose
    detection is good, the mining loop proposes nothing, `can_promote()` is handed nothing, and the
    published blocklist stays at zero patterns while every schedule reports success. Measured on
    2026-09-10: cycle 1, 0 patterns, five sidecars enforcing an empty list.

    DERIVED, NOT RETYPED. Every candidate is `perseus.client.CLASSES[i]` read at CALL TIME -- the
    same compiled table `shield.py` imports, `classify()` answers from and the public siege feed
    draws its lanes with. `rx.pattern` is taken off the compiled object, so there is no second
    string anywhere that an edit could leave stale.

    THIS FUNCTION PROPOSES. It vets nothing and installs nothing: the caller puts every candidate
    through `vet.vet()` against the routes we are OBSERVED serving, exactly as it does a model's
    proposal, and several of these are refused there every time (`admin_panel` matches
    /api/admin/users, which we serve). That refusal is the barrier working, not a defect in the
    seed, and the caller reports it.
    """
    table, where = _class_table()
    if not table:
        return [], ("the shared class table could not be imported, so there is no seed: a retyped "
                    "copy would be a second home for the one vocabulary every sidecar scores with")
    out = []
    for name, rx in table:
        pattern = getattr(rx, "pattern", None)
        if not pattern:
            continue
        out.append({"name": name, "pattern": pattern, "source": SOURCE_SEED,
                    "why": "detection class %s, derived from %s - the committed probe corpus every "
                           "sidecar already scores with" % (name, where)})
    return out, "%d class(es) read from %s" % (len(out), where)


def propose(rs, pattern, why, evidence, reviewers, source=SOURCE_MINED):
    """Add a pattern in DETECTION. It cannot refuse anything yet, whatever the reviewers said.

    Every rule carries its provenance: who proposed it, on what evidence, and when. Six weeks from
    now the only useful question about a rule is "why is this here", and a rule that cannot answer
    it is a rule nobody dares delete."""
    if any(r.get("pattern") == pattern for r in rs.get("rules") or []):
        return None
    rule = {"id": "r%d-%d" % (rs.get("cycle", 0), len(rs.get("rules") or []) + 1),
            "pattern": pattern, "why": why[:300], "evidence": (evidence or [])[:8],
            "reviewers": sorted(reviewers or []), "source": source,
            "tier": TIER_DETECT, "created": _now(), "promoted": None, "demoted": None,
            "hits": 0, "clean_hits": 0, "last_hit": None}
    rs.setdefault("rules", []).append(rule)
    rs.setdefault("history", []).append(
        {"ts": _now(), "action": "proposed", "id": rule["id"], "pattern": pattern, "why": why[:160]})
    return rule


def shortfall(rule, now=None):
    """EVERY promotion clause this rule has not met, and BY HOW MUCH. `[]` means it may promote.

    THE ONE HOME FOR THE GATE. can_promote() is this function plus a verdict, and the daily report
    renders the same list, so there is no second statement of the rule to drift from the first --
    the ENRICH_MODELS defect, applied to the one decision that can refuse a paying customer.

    IT ANSWERS "BY HOW MUCH", not just "no". On 2026-09-10 the estate had one published cycle, zero
    published patterns and a promotion gate that had never been handed a candidate, and the report
    said only that nothing had been promoted. "Nothing happened" with no arithmetic behind it is
    indistinguishable from "nothing works", and this repository has paid for that distinction more
    than once.
    """
    now = now or _now()
    out = []
    tier = rule.get("tier")
    if tier != TIER_DETECT:
        # Not a shortfall that time can fix: a blocking rule has already been promoted and a retired
        # one has failed a barrier. Stated as a clause anyway so the caller never has to special-case.
        return [{"clause": "tier", "have": tier, "need": TIER_DETECT, "short": "not in detection",
                 "why": "not in detection"}]

    age_h = (now - float(rule.get("created") or now)) / 3600.0
    if age_h < MIN_DETECT_HOURS:
        out.append({"clause": "soak", "have": round(age_h, 1), "need": MIN_DETECT_HOURS,
                    "short": "%.1fh more in detection" % (MIN_DETECT_HOURS - age_h),
                    "why": "only %.1fh in detection, needs %d" % (age_h, MIN_DETECT_HOURS)})

    n = len(rule.get("reviewers") or [])
    if n < QUORUM:
        out.append({"clause": "quorum", "have": n, "need": QUORUM,
                    "short": "%d more vendor(s) must agree" % (QUORUM - n),
                    "why": "%d reviewer(s), needs %d" % (n, QUORUM)})

    if not rule.get("hits"):
        out.append({"clause": "evidence", "have": 0, "need": 1,
                    "short": "1 hostile match in real traffic",
                    "why": "never matched anything, so nothing justifies blocking on it"})

    if rule.get("clean_hits"):
        # It matched traffic that did not otherwise look hostile. That is the whole reason for the
        # detection period, and it is a refusal, not a delay. NO SHORTFALL IS QUOTED because there
        # is no number of good days that earns this one back.
        out.append({"clause": "clean", "have": int(rule["clean_hits"]), "need": 0,
                    "short": "REFUSED OUTRIGHT - it matched traffic we served",
                    "why": "matched %d request(s) that looked legitimate" % rule["clean_hits"]})
    return out


def can_promote(rule, now=None):
    """Deterministic promotion test. Every clause is a fact about observed behaviour or about the
    reviewers, and none of them is a model's opinion about whether the rule is a good idea.

    The clauses live in shortfall(); this is the verdict on them. A seed pattern is not exempt from
    a single one of them -- being committed code buys a rule a place in the detection queue and
    nothing else."""
    now = now or _now()
    miss = shortfall(rule, now)
    if miss:
        return False, "; ".join(m["why"] for m in miss)
    age_h = (now - float(rule.get("created") or now)) / 3600.0
    return True, "%.0fh in detection, %d hostile match(es), 0 legitimate" % (age_h, rule["hits"])


def promote(rs, rule, now=None):
    ok, why = can_promote(rule, now)
    if not ok:
        return False, why
    rule["tier"] = TIER_BLOCK
    rule["promoted"] = now or _now()
    rs.setdefault("history", []).append(
        {"ts": _now(), "action": "promoted", "id": rule["id"], "pattern": rule["pattern"],
         "why": why})
    return True, why


def demote(rs, rule, why):
    """AUTO-REVERT. A blocking rule that hurts goes back to watching, by itself, and says so.

    Not deleted: a demoted rule keeps its evidence so the next cycle can see it was tried and why
    it failed, instead of proposing the same thing again next week."""
    if rule.get("tier") != TIER_BLOCK:
        return False
    rule["tier"] = TIER_DETECT
    rule["demoted"] = _now()
    rule["clean_hits"] = rule.get("clean_hits", 0)
    rs.setdefault("history", []).append(
        {"ts": _now(), "action": "demoted", "id": rule["id"], "pattern": rule["pattern"],
         "why": why[:200]})
    return True


def record_hit(rs, rule_id, looked_legitimate=False):
    for r in rs.get("rules") or []:
        if r.get("id") == rule_id:
            r["last_hit"] = _now()
            if looked_legitimate:
                r["clean_hits"] = r.get("clean_hits", 0) + 1
            else:
                r["hits"] = r.get("hits", 0) + 1
            return r
    return None


def score_detection(rs, events, served=None, now=None):
    """Run every live rule against REAL OBSERVED TRAFFIC and record what it matched. No model.

    THIS IS THE MISSING HALF OF THE GATE. `can_promote()` has always demanded "at least one hostile
    match and zero legitimate ones", and `review()` has always demoted a blocking rule that refused
    somebody real -- but `record_hit()` was called by NOTHING outside the test suite. Both clauses
    were therefore unsatisfiable and unfireable: no rule could ever promote, and no wrong rule could
    ever revert itself. A gate that cannot pass is not a gate, and an auto-revert that cannot fire
    is not a safety net. (Defect class 9: behaviour AND wiring.)

    WHAT COUNTS AS WHAT, and the asymmetry is deliberate:
      * the request was SERVED (2xx/3xx), or its path is one this estate was observed serving
        successfully inside this window -> CLEAN. We would have refused a real page.
      * anything else -> HOSTILE.
    A 404 on a stale route OF OURS is a clean hit and not evidence, which is the 2026-08-10 lesson
    (two genuine visitors, 439 and 362 stale-link 404s each) applied to patterns instead of
    addresses. `served` is the corpus publish() writes; without it every 404 counts as hostile, so
    the caller passes it and this function does not guess.

    THE WATERMARK IS PER RULE AND IT MOVES ONLY FORWARD. The daily cycle collects the WIDER of the
    mining and abuse windows -- seven days -- every single night, so without it one hostile request
    would be counted seven times and a rule would "earn" its evidence clause from a single packet.
    A rule is also never scored on traffic older than itself: it was not in detection then, and
    "it spent a day watching real traffic" would otherwise be satisfied retroactively.
    """
    now = now or _now()
    out = []
    pats = active_patterns(rs)
    if not pats or not events:
        return out
    served = {str(p) for p in (served or [])}
    horizon = 0.0
    rows = []
    for e in events or []:
        try:
            ts = float(e.get("_ts") or 0)
        except Exception:
            ts = 0.0
        path = e.get("path") or ""
        if not path:
            continue
        try:
            status = int(e.get("status") or 0)
        except Exception:
            status = 0
        horizon = max(horizon, ts)
        rows.append((ts, path, status))
    if not rows:
        return out

    for rule, rx in pats:
        since = float(rule.get("scored_until") or rule.get("created") or 0)
        hostile = clean = 0
        for ts, path, status in rows:
            if ts <= since:
                continue
            if not rx.search(path):
                continue
            # THE CORPUS IS STORED TRUNCATED (publish() caps a path at 120 chars), so compare both
            # forms. Comparing only the raw path would score a long served route as hostile,
            # which is the failure this clause exists to prevent, wearing a length limit.
            if (200 <= status < 400) or path in served or path[:120] in served:
                clean += 1
            else:
                hostile += 1
        rule["scored_until"] = max(since, horizon)
        if not (hostile or clean):
            continue
        if hostile:
            rule["hits"] = int(rule.get("hits") or 0) + hostile
        if clean:
            rule["clean_hits"] = int(rule.get("clean_hits") or 0) + clean
        rule["last_hit"] = now
        out.append({"id": rule.get("id"), "pattern": rule.get("pattern"),
                    "tier": rule.get("tier"), "hostile": hostile, "clean": clean})
    return out


def review(rs, now=None):
    """Run every cycle BEFORE anything is promoted. Returns the list of demotions.

    A blocking rule that has matched legitimate-looking traffic since it was promoted is demoted
    immediately. This is what makes full autonomy survivable: the loop can be wrong, and being
    wrong costs noise for a day rather than a blocked customer for a month."""
    out = []
    for r in rs.get("rules") or []:
        if r.get("tier") != TIER_BLOCK:
            continue
        if r.get("clean_hits"):
            if demote(rs, r, "refused %d request(s) that looked legitimate after promotion"
                      % r["clean_hits"]):
                out.append(r)
    return out


def retire(rs, rule, why):
    """Take a rule out of service permanently. NARROWING ONLY, and that is what makes it safe.

    Retiring can only ever REMOVE a refusal, so unlike promotion it cannot deny a real visitor, and
    unlike demotion it does not need evidence of harm -- absence of any match at all is enough.
    The rule is kept, not deleted, with its evidence and its reason: six weeks from now the only
    useful question about a pattern is "why is this here", and next month's mining would otherwise
    propose the same dead pattern again and nobody would remember it had been tried.
    """
    if rule.get("tier") == TIER_RETIRED:
        return False
    rule["tier"] = TIER_RETIRED
    rule["retired"] = _now()
    rs.setdefault("history", []).append(
        {"ts": _now(), "action": "retired", "id": rule.get("id"), "pattern": rule.get("pattern"),
         "why": str(why)[:200]})
    return True


def dormant(rule, now=None, days=None):
    """(bool, why). A rule old enough to have been tested by traffic that has matched NOTHING.

    THE AGE FLOOR IS LOAD-BEARING. Without it every pattern proposed yesterday is 'dormant' and the
    weekly pass would retire the entire detection queue before it ever reached its promotion test --
    a check whose subject has not existed long enough to be measured is not a check.
    """
    now = now or _now()
    days = DORMANT_DAYS if days is None else days
    if rule.get("tier") == TIER_RETIRED:
        return False, "already retired"
    age_d = (now - float(rule.get("created") or now)) / 86400.0
    if age_d < days:
        return False, "only %.1f day(s) old, needs %d" % (age_d, days)
    if rule.get("hits") or rule.get("clean_hits"):
        return False, "has matched %d hostile / %d legitimate request(s)" % (
            int(rule.get("hits") or 0), int(rule.get("clean_hits") or 0))
    return True, "%.0f days in the ruleset without matching a single request" % age_d


def tune(rs, key, proposed, votes):
    """Move ONE threshold. Quorum on the direction, MEDIAN of the agreeing side, step-capped, then
    clamped. Lifted wholesale from the staging gate's consensus rule, which has the same shape and
    the same reason: one bold model must not be able to drag a number on its own."""
    cur = thresholds(rs)[key]
    ups = sorted(v for v in votes if v > cur)
    downs = sorted(v for v in votes if v < cur)
    side = ups if len(ups) >= QUORUM else (downs if len(downs) >= QUORUM else None)
    if not side:
        return cur, "no quorum on the direction (%d up, %d down of %d)" % (len(ups), len(downs), len(votes))
    med = side[len(side) // 2]
    cap = max(1, int(abs(cur) * STEP_CAP))
    stepped = cur + max(-cap, min(cap, med - cur))
    new = clamp(key, stepped)
    if new is None or new == cur:
        return cur, "no change after clamp"
    rs.setdefault("thresholds", {})[key] = new
    rs.setdefault("history", []).append(
        {"ts": _now(), "action": "tuned", "key": key, "from": cur, "to": new,
         "why": "median %s of %d agreeing, capped to %+d" % (med, len(side), new - cur)})
    return new, "%s %d -> %d" % (key, cur, new)


def deltas(rs, since):
    """Everything that changed since a timestamp, for the report. The report is the product: a
    defence that changes silently is indistinguishable from one that does not change at all."""
    return [h for h in (rs.get("history") or []) if h.get("ts", 0) >= since]


def summary(rs):
    rules = rs.get("rules") or []
    return {"version": rs.get("version"), "cycle": rs.get("cycle", 0),
            "blocking": sum(1 for r in rules if r.get("tier") == TIER_BLOCK),
            "detecting": sum(1 for r in rules if r.get("tier") == TIER_DETECT),
            "retired": sum(1 for r in rules if r.get("tier") == TIER_RETIRED),
            "seeded": sum(1 for r in rules if r.get("source") == SOURCE_SEED),
            "thresholds": thresholds(rs)}


def gate_status(rs, now=None):
    """What the promotion gate can see right now: how many rules block, how many watch, and for
    every rule still watching, WHICH clause it is short of and by how much.

    COMPUTED BY THE CALLER AFTER THE LAST THING THAT CAN CHANGE IT. A count taken before promotion
    describes a state the report never had, which is the same rule as a headline number taken
    mid-pipeline.
    """
    now = now or _now()
    rules = rs.get("rules") or []
    pending = []
    for r in rules:
        if r.get("tier") != TIER_DETECT:
            continue
        miss = shortfall(r, now)
        pending.append({
            "id": r.get("id"), "pattern": r.get("pattern"), "source": r.get("source") or "?",
            "age_h": round((now - float(r.get("created") or now)) / 3600.0, 1),
            "reviewers": len(r.get("reviewers") or []),
            "hits": int(r.get("hits") or 0), "clean_hits": int(r.get("clean_hits") or 0),
            # SCORED IS NOT THE SAME CLAIM AS SEEN. A rule whose watermark never moved has not been
            # measured against anything, and reporting it as "0 matches" would be our own blindness
            # dressed up as a fact about the traffic.
            "scored": bool(r.get("scored_until")),
            "short": miss, "ready": not miss})
    # Closest to promotion first: fewest clauses outstanding, then longest in detection.
    pending.sort(key=lambda p: (len(p["short"]), -p["age_h"]))
    return {"blocking": sum(1 for r in rules if r.get("tier") == TIER_BLOCK),
            "detecting": len(pending),
            "retired": sum(1 for r in rules if r.get("tier") == TIER_RETIRED),
            "seeded": sum(1 for r in rules if r.get("source") == SOURCE_SEED),
            "ready": sum(1 for p in pending if p["ready"]),
            "unscored": sum(1 for p in pending if not p["scored"]),
            "pending": pending}
