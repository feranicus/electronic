"""llm_meter.py — every model call is counted, and the day has a hard ceiling.

WHY THIS EXISTS (2026-09-01)
    DigitalOcean auto-recharged the prepaid balance by $5 three times in under two days while our
    own cost report said the lifetime spend was under a dollar. Both numbers were honestly
    produced. The report was simply blind:

        cost_ledger.record() is called from exactly ONE place, run_assessment.py.

    Everything else that talks to the inference endpoint was invisible — the Cassandra assistant,
    the daily attack digest panel, the six-hourly shield panel, release notes, the White Label
    brand panel, the FP auditor, the GEOPOL author, compliance enrichment and every map-reduce
    shard. Nine callers, four of them on timers that run with nobody watching, none of them
    counted. A ledger that can only see one caller cannot answer "where did the money go", and it
    reports a reassuring total while doing it. That is the same defect class as the coverage
    metric that could only ever print 100%.

    So the meter moves to the ONE function every one of those callers goes through, `enrich._call`.
    A new caller is metered because it cannot avoid being metered, rather than because somebody
    remembered to add a line.

THE CEILING IS THE POINT, NOT THE REPORTING
    Counting after the fact would have produced a better post-mortem and the same bill. `allow()`
    is checked BEFORE the request is sent, so the spend physically cannot continue past the cap.

    IT FAILS OPEN ON ITS OWN ERRORS AND CLOSED ON THE BUDGET. Those are different things and the
    distinction matters: if the meter's database is unreadable we must not take the product down
    to protect it, so we allow the call. But if the meter can read the day's spend and that spend
    is over the cap, we refuse. A budget that fails open when it works is not a budget.

WHAT A REFUSAL COSTS, DELIBERATELY
    An assessment degrades to its deterministic template text, which is a documented and tested
    path — the same one taken when every model in the chain times out. It does not crash, and the
    decks still build. The operator gets an alert naming the cap. That is a far better failure
    than an invoice.

STORAGE is SQLite on the shared, persistent `colt_events` volume, beside cost_ledger.sqlite and
users.sqlite, for the same reason: it must survive a redeploy, and both the bots and colt-web must
see the same number or the cap is per-container and therefore not a cap.
"""
import os
import sqlite3
import time

DB_PATH = os.environ.get("LLM_METER_DB", "/var/log/colt/llm_meter.sqlite")

# THE DEFAULT IS DELIBERATELY LOW AND IS A CEILING, NOT A FORECAST. Measured normal operation is
# well under a dollar a day; $3 leaves room for a genuinely busy day and still bounds a runaway to
# roughly one $5 top-up rather than three. Raise it consciously, in the .env, with a reason.
DAILY_USD = float(os.environ.get("LLM_DAILY_USD", "3.00"))
# Warn well before the wall, so the first anyone hears of it is not a refusal.
WARN_AT = float(os.environ.get("LLM_WARN_FRACTION", "0.60"))

# A single call that costs more than this is a bug, not a workload: the biggest legitimate call we
# make is a ~13k-character prompt answering with ~11k tokens, about two cents. Anything an order of
# magnitude past that means a prompt was built from a log or a model ran away, and it is worth
# knowing on the call that did it rather than at the end of the month.
ALERT_SINGLE_USD = float(os.environ.get("LLM_ALERT_SINGLE_USD", "0.15"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    ts      REAL NOT NULL,
    day     TEXT NOT NULL,
    caller  TEXT NOT NULL,
    model   TEXT NOT NULL,
    tin     INTEGER NOT NULL,
    tout    INTEGER NOT NULL,
    usd     REAL NOT NULL,
    ms      INTEGER NOT NULL,
    status  TEXT NOT NULL,
    user    TEXT
);
CREATE INDEX IF NOT EXISTS calls_day ON calls (day);
"""

_broken = [False]
_warned = [""]          # the day we last warned, so the warning fires once and not per call


def _today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def _connect():
    d = os.path.dirname(DB_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=3.0)
    c.executescript(_SCHEMA)
    return c


def spent_today():
    """USD recorded so far today. Returns None when the meter cannot read itself.

    None and 0.0 MUST stay distinguishable: 0.0 means a quiet day and the cap applies, None means
    we do not know and the caller has to decide what to do about that. Collapsing them is how a
    broken meter silently becomes an unlimited budget.
    """
    if _broken[0]:
        return None
    try:
        with _connect() as c:
            r = c.execute("SELECT COALESCE(SUM(usd), 0) FROM calls WHERE day = ?",
                          (_today(),)).fetchone()
        return float(r[0] or 0.0)
    except Exception:
        _broken[0] = True
        return None


def allow(estimate_usd=0.0):
    """(ok, reason). Called BEFORE the request, because counting afterwards buys nothing."""
    s = spent_today()
    if s is None:
        return True, "meter unavailable - failing OPEN so a storage fault cannot take the product down"
    if s + max(0.0, estimate_usd) >= DAILY_USD:
        return False, ("daily AI budget reached: $%.4f of $%.2f spent today (LLM_DAILY_USD)"
                       % (s, DAILY_USD))
    return True, ""


def record(caller, model, tokens_in, tokens_out, usd, ms=0, status="ok", user=""):
    """Write one call and return the day's running total (or None if unknown). Never raises."""
    if _broken[0]:
        return None
    try:
        with _connect() as c:
            c.execute("INSERT INTO calls (ts, day, caller, model, tin, tout, usd, ms, status, user)"
                      " VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (time.time(), _today(), str(caller)[:40], str(model)[:60],
                       int(tokens_in or 0), int(tokens_out or 0), float(usd or 0.0),
                       int(ms or 0), str(status)[:24], str(user or "")[:120]))
        return spent_today()
    except Exception:
        _broken[0] = True
        return None


def should_warn(total):
    """True once per day, the first time the running total crosses the warning fraction."""
    if total is None or _today() == _warned[0]:
        return False
    if total >= DAILY_USD * WARN_AT:
        _warned[0] = _today()
        return True
    return False


def report(days=14):
    """Per-day and per-caller totals. THE PER-CALLER SPLIT IS THE WHOLE POINT of this file: the
    question that could not be answered on 2026-09-01 was not 'how much' but 'who'."""
    try:
        with _connect() as c:
            since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
            per_day = [dict(day=r[0], calls=r[1], usd=round(r[2], 4), tin=r[3], tout=r[4])
                       for r in c.execute(
                           "SELECT day, COUNT(*), SUM(usd), SUM(tin), SUM(tout) FROM calls"
                           " WHERE day >= ? GROUP BY day ORDER BY day", (since,))]
            per_caller = [dict(caller=r[0], calls=r[1], usd=round(r[2], 4), tout=r[3])
                          for r in c.execute(
                              "SELECT caller, COUNT(*), SUM(usd), SUM(tout) FROM calls"
                              " WHERE day >= ? GROUP BY caller ORDER BY SUM(usd) DESC", (since,))]
            per_model = [dict(model=r[0], calls=r[1], usd=round(r[2], 4))
                         for r in c.execute(
                             "SELECT model, COUNT(*), SUM(usd) FROM calls"
                             " WHERE day >= ? GROUP BY model ORDER BY SUM(usd) DESC", (since,))]
            worst = [dict(ts=r[0], caller=r[1], model=r[2], usd=round(r[3], 4), tout=r[4])
                     for r in c.execute(
                         "SELECT ts, caller, model, usd, tout FROM calls WHERE day >= ?"
                         " ORDER BY usd DESC LIMIT 10", (since,))]
        return {"db": DB_PATH, "healthy": not _broken[0], "cap_usd": DAILY_USD,
                "today_usd": spent_today(), "per_day": per_day, "per_caller": per_caller,
                "per_model": per_model, "most_expensive_calls": worst}
    except Exception as e:
        return {"db": DB_PATH, "healthy": False, "error": str(e)[:200],
                "cap_usd": DAILY_USD, "per_day": [], "per_caller": [], "per_model": [],
                "most_expensive_calls": []}


if __name__ == "__main__":                                   # pragma: no cover
    import json as _j
    import sys
    print(_j.dumps(report(int(sys.argv[1]) if len(sys.argv) > 1 else 14), indent=2))
