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

TIER_DETECT, TIER_BLOCK, TIER_RETIRED = "detect", "block", "retired"

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


def propose(rs, pattern, why, evidence, reviewers, source="daily-mining"):
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


def can_promote(rule, now=None):
    """Deterministic promotion test. Every clause is a fact about observed behaviour or about the
    reviewers, and none of them is a model's opinion about whether the rule is a good idea."""
    now = now or _now()
    if rule.get("tier") != TIER_DETECT:
        return False, "not in detection"
    age_h = (now - rule.get("created", now)) / 3600.0
    if age_h < MIN_DETECT_HOURS:
        return False, "only %.1fh in detection, needs %d" % (age_h, MIN_DETECT_HOURS)
    if len(rule.get("reviewers") or []) < QUORUM:
        return False, "%d reviewer(s), needs %d" % (len(rule.get("reviewers") or []), QUORUM)
    if not rule.get("hits"):
        return False, "never matched anything, so nothing justifies blocking on it"
    if rule.get("clean_hits"):
        # It matched traffic that did not otherwise look hostile. That is the whole reason for the
        # detection period, and it is a refusal, not a delay.
        return False, "matched %d request(s) that looked legitimate" % rule["clean_hits"]
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
            "thresholds": thresholds(rs)}
