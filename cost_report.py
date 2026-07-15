#!/usr/bin/env python3
"""
cost_report.py -- TRUE lifetime cost report from the persistent ledger (not Loki).

The ledger (SQLite) lives on the droplet's persistent `colt_events` volume at
/var/log/colt/cost_ledger.sqlite, shared by the Telegram bots and colt-web. This script reads it
READ-ONLY over SSH (`docker exec`) -- it changes nothing on the droplet.

  python cost_report.py              # backfill history + snapshot + print the report
  python cost_report.py --no-backfill
  python cost_report.py --json       # machine-readable
  python cost_report.py --local /path/ledger.sqlite   # read a local copy instead

Backfill seeds the ledger from the existing events.log so pre-ledger runs (Honda, Rosatom, ...)
count towards lifetime. It is idempotent -- re-running never double-counts.
"""
import os, sys, json, subprocess, datetime

HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", "")
SSH  = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"] + (["-i", KEY] if KEY and os.path.exists(KEY) else [])
CT   = os.environ.get("COLT_CONTAINER", "colt-web")
SCRIPT = "/opt/shodan-skill/scripts/cost_ledger.py"


def _remote(args):
    cmd = SSH + ["%s@%s" % (USER, HOST), "docker exec %s python3 %s %s" % (CT, SCRIPT, args)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("[X] remote read failed:\n%s" % (r.stderr.strip()[:500] or r.stdout.strip()[:500]))
    out = r.stdout
    i = out.rfind('{\n  "ledger"')          # the report object is printed last
    if i < 0:
        i = out.find("{")
    try:
        return json.loads(out[i:])
    except Exception:
        sys.exit("[X] could not parse ledger output:\n%s" % out[:500])


def _local(path):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "hermes-skills", "shodan-assessment", "scripts"))
    os.environ["COST_LEDGER"] = path
    import cost_ledger as L
    return {"ledger": L.LEDGER, "totals": L.totals(), "per_day": L.per_day(30),
            "per_company": L.per_company(50)}


def _ts(v):
    return datetime.datetime.utcfromtimestamp(float(v)).strftime("%Y-%m-%d %H:%M") if v else "-"


def render(d):
    t = d.get("totals") or {}
    n = t.get("assessments_total", 0)
    print("\n" + "=" * 64)
    print("  COLT ASSESSMENT COST LEDGER  (persistent — independent of Loki retention)")
    print("=" * 64)
    print("  ledger        : %s" % d.get("ledger"))
    print("  since         : %s  (first recorded assessment)" % _ts(t.get("first_ts")))
    print("  last run      : %s" % _ts(t.get("last_ts")))
    print("  " + "─" * 60)
    print("  LIFETIME COST : $%.4f   over %d assessment(s)" % (t.get("lifetime_usd", 0), n))
    print("  AVG / ASSESS  : $%.4f" % t.get("avg_usd", 0))
    print("  TOKENS        : %s in / %s out" % (f"{t.get('tokens_in_total',0):,}", f"{t.get('tokens_out_total',0):,}"))

    pd = d.get("per_day") or []
    if pd:
        print("\n  PER DAY")
        print("  %-12s %6s  %10s" % ("day", "runs", "cost USD"))
        for r in pd:
            print("  %-12s %6d  %10.4f" % (r["day"], r["runs"], r["cost_usd"] or 0))

    pc = d.get("per_company") or []
    if pc:
        print("\n  PER ASSESSMENT (by company)")
        print("  %-28s %6s %10s %10s   %s" % ("company", "runs", "cost USD", "avg USD", "last run"))
        for r in pc:
            print("  %-28s %6d %10.4f %10.4f   %s" % (
                (r["company"] or "?")[:28], r["runs"], r["cost_usd"] or 0, r["avg_usd"] or 0, _ts(r.get("last_ts"))))
    print("\n  Note: cost = AI inference (DeepSeek/QWEN) per assessment. Shodan plan and the droplet")
    print("        are flat subscriptions, not per-assessment, so they are not in this ledger.\n")


def main():
    local = None
    if "--local" in sys.argv:
        i = sys.argv.index("--local")
        local = sys.argv[i + 1] if len(sys.argv) > i + 1 else "/var/log/colt/cost_ledger.sqlite"
    if local:
        d = _local(local)
    else:
        args = "" if "--no-backfill" in sys.argv else "--backfill"
        args = (args + " --snapshot").strip()   # refresh the Grafana lifetime snapshot too
        d = _remote(args)
    if "--json" in sys.argv:
        print(json.dumps(d, indent=2))
    else:
        render(d)


if __name__ == "__main__":
    main()
