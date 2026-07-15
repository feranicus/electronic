#!/usr/bin/env python3
"""
cost_ledger.py -- persistent, append-only cost ledger for Colt assessments.

WHY: Loki is the log pipeline, not a books-of-record — old lines age out with retention, so
"cost since the beginning of time" cannot come from logs. This ledger is the source of truth.

WHERE: a SQLite file on the SHARED, PERSISTENT docker volume `colt_events`
       (/var/log/colt/...), which BOTH Telegram bots and colt-web already mount. It therefore
       survives container rebuilds, redeploys and Loki retention.
       Override with env COST_LEDGER=/path/to/ledger.sqlite

USE (engine):  cost_ledger.record(company=..., cost_usd=..., ...)  -> returns totals()
USE (report):  python3 cost_report.py            (lifetime / per-day / per-company)

Every write is best-effort: a ledger failure must NEVER break an assessment.
"""
import os, sqlite3, time, datetime

LEDGER = os.environ.get("COST_LEDGER") or os.path.join(
    os.path.dirname(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log")) or "/var/log/colt",
    "cost_ledger.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assessments (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         REAL    NOT NULL,
  day        TEXT    NOT NULL,
  company    TEXT,
  user       TEXT,
  source     TEXT,
  model      TEXT,
  cost_usd   REAL    DEFAULT 0,
  tokens_in  INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  crit INTEGER DEFAULT 0, high INTEGER DEFAULT 0,
  med  INTEGER DEFAULT 0, low  INTEGER DEFAULT 0,
  total_ms   INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_day     ON assessments(day);
CREATE INDEX IF NOT EXISTS idx_company ON assessments(company);
"""

def _conn():
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    c = sqlite3.connect(LEDGER, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")      # safe concurrent appends (bots + web)
    c.execute("PRAGMA synchronous=NORMAL")
    c.executescript(_SCHEMA)
    return c

def record(company, cost_usd=0.0, tokens_in=0, tokens_out=0, model=None,
           crit=0, high=0, med=0, low=0, total_ms=0, user=None, source=None, ts=None):
    """Append one completed assessment. Returns totals() (or {} on failure). Never raises."""
    try:
        t = float(ts or time.time())
        day = datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
        c = _conn()
        with c:
            c.execute("""INSERT INTO assessments
                (ts,day,company,user,source,model,cost_usd,tokens_in,tokens_out,crit,high,med,low,total_ms)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (t, day, (company or "?"), user, source, model, float(cost_usd or 0),
                 int(tokens_in or 0), int(tokens_out or 0),
                 int(crit or 0), int(high or 0), int(med or 0), int(low or 0), int(total_ms or 0)))
        out = totals(c)
        c.close()
        return out
    except Exception as e:
        print("[warn] cost_ledger.record: %s" % e)
        return {}

def totals(c=None):
    """Lifetime rollup: spend, count, average, first/last timestamps."""
    own = c is None
    try:
        c = c or _conn()
        r = c.execute("""SELECT COALESCE(SUM(cost_usd),0), COUNT(*),
                                COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0),
                                MIN(ts), MAX(ts) FROM assessments""").fetchone()
        cost, n = float(r[0] or 0), int(r[1] or 0)
        return {"lifetime_usd": round(cost, 6), "assessments_total": n,
                "avg_usd": round(cost / n, 6) if n else 0.0,
                "tokens_in_total": int(r[2] or 0), "tokens_out_total": int(r[3] or 0),
                "first_ts": r[4], "last_ts": r[5]}
    except Exception as e:
        print("[warn] cost_ledger.totals: %s" % e); return {}
    finally:
        if own and c:
            try: c.close()
            except Exception: pass

def per_company(limit=50):
    try:
        c = _conn()
        rows = c.execute("""SELECT company, COUNT(*) n, ROUND(SUM(cost_usd),6) cost,
                                   ROUND(AVG(cost_usd),6) avg, MAX(ts) last
                            FROM assessments GROUP BY company
                            ORDER BY cost DESC LIMIT ?""", (limit,)).fetchall()
        c.close()
        return [{"company": r[0], "runs": r[1], "cost_usd": r[2], "avg_usd": r[3], "last_ts": r[4]}
                for r in rows]
    except Exception as e:
        print("[warn] cost_ledger.per_company: %s" % e); return []

def per_day(days=90):
    try:
        c = _conn()
        rows = c.execute("""SELECT day, COUNT(*) n, ROUND(SUM(cost_usd),6) cost
                            FROM assessments GROUP BY day ORDER BY day DESC LIMIT ?""",
                         (days,)).fetchall()
        c.close()
        return [{"day": r[0], "runs": r[1], "cost_usd": r[2]} for r in rows]
    except Exception as e:
        print("[warn] cost_ledger.per_day: %s" % e); return []

def backfill_from_events(path=None):
    """Seed the ledger from the existing events.log history (idempotent).

    Lets 'lifetime' include assessments that ran BEFORE the ledger existed (Honda, Rosatom, ...).
    Dedupes on (ts, company), so it is safe to run repeatedly."""
    import json
    path = path or os.environ.get("EVENTS_LOG", "/var/log/colt/events.log")
    added = skipped = 0
    try:
        c = _conn()
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if '"assess_done"' not in line:
                    continue
                try:
                    i = line.find("{")
                    e = json.loads(line[i:]) if i >= 0 else None
                except Exception:
                    continue
                if not e or e.get("evt") != "assess_done":
                    continue
                ts = e.get("ts")
                if isinstance(ts, str):
                    try:
                        ts = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        ts = None
                ts = float(ts or 0) or time.time()
                co = e.get("company") or "?"
                if c.execute("SELECT 1 FROM assessments WHERE ts=? AND company=?", (ts, co)).fetchone():
                    skipped += 1
                    continue
                day = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                with c:
                    c.execute("""INSERT INTO assessments
                        (ts,day,company,user,source,model,cost_usd,tokens_in,tokens_out,crit,high,med,low,total_ms)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (ts, day, co, e.get("user"), e.get("bot") or e.get("service") or "backfill",
                         e.get("qwen_model"), float(e.get("qwen_cost_usd") or 0), 0, 0,
                         int(e.get("crit") or 0), int(e.get("high") or 0),
                         int(e.get("med") or 0), int(e.get("low") or 0),
                         int(e.get("total_ms") or 0)))
                added += 1
        c.close()
    except FileNotFoundError:
        print("[warn] backfill: no events log at %s" % path)
    except Exception as e:
        print("[warn] backfill: %s" % e)
    return {"added": added, "already_present": skipped}


def emit_snapshot():
    """Append one cumulative `cost_snapshot` line to events.log so Grafana can display TRUE
    lifetime totals via last_over_time() -- no new datasource/plugin needed."""
    import json
    t = totals()
    if not t:
        return {}
    rec = dict(evt="cost_snapshot", ts=time.time(), ledger=LEDGER,
               bot=os.environ.get("SERVICE", "ledger"), service=os.environ.get("SERVICE", "ledger"), **t)
    try:
        with open(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log"), "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception as e:
        print("[warn] emit_snapshot: %s" % e)
    return rec


if __name__ == "__main__":
    import json, sys as _s
    if "--snapshot" in _s.argv:
        print(json.dumps(emit_snapshot(), indent=2))
    if "--backfill" in _s.argv:
        i = _s.argv.index("--backfill")
        src = _s.argv[i + 1] if len(_s.argv) > i + 1 and not _s.argv[i + 1].startswith("-") else None
        print(json.dumps(backfill_from_events(src), indent=2))
    print(json.dumps({"ledger": LEDGER, "totals": totals(),
                      "per_day": per_day(30), "per_company": per_company(50)}, indent=2))
