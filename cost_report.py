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
import os, sys, json, subprocess, datetime, urllib.request, urllib.error

# ---------------------------------------------------------------------------------------------
# THE DIGITALOCEAN SIDE (added 2026-09-01)
#
# WHY: DO auto-recharged the prepaid balance by $5 three times inside two days while this very
# script reported a lifetime spend under a dollar. Both numbers were honestly produced and the
# report was simply blind, because cost_ledger.record() is called from ONE caller
# (run_assessment.py) and nine others were spending money invisibly.
#
# But even a perfect ledger of OUR calls cannot answer the first question, which is whether the
# money went on inference at all. A droplet, a second staging droplet, Spaces and bandwidth are on
# the same invoice. So the authoritative number has to come from DO's own billing API, broken down
# BY PRODUCT, and then be reconciled against what we can account for. The gap between the two is
# the finding; printing either number on its own is what caused two days of guessing.
#
# READ-ONLY. Every endpoint here is a GET. This script cannot change anything in the account.
DO_API = "https://api.digitalocean.com/v2"


def _do_token():
    """DO_API_TOKEN from the environment, or from a local gitignored env file.

    The token is the ONE irreducible human input here: only the account owner can mint it, exactly
    as CLAUDE.md records for the GoDaddy key. Without it this half is skipped with an explanation
    rather than a traceback, because the ledger half is still worth reading on its own.
    """
    t = os.environ.get("DO_API_TOKEN", "").strip()
    if t:
        return t
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("golive.secrets.env", ".do.env", "assess-bot/.env"):
        p = os.path.join(here, name)
        if not os.path.exists(p):
            continue
        try:
            for line in open(p, encoding="utf-8", errors="replace"):
                if line.strip().startswith("DO_API_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def _do_get(path, token):
    req = urllib.request.Request(DO_API + path,
                                 headers={"Authorization": "Bearer " + token,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def do_billing(token):
    """Balance, month-to-date usage, and the CURRENT invoice broken down by product.

    `product_charges.items` is the decisive field and the reason this exists: it is what separates
    "Serverless Inference" from "Droplets" and "Spaces". Everything else in this investigation is
    inference from our own logs; this is the vendor's own statement of what we are being charged
    for, which is the only number that can settle it.
    """
    out = {"ok": False}
    try:
        bal = _do_get("/customers/my/balance", token)
        out["balance"] = {"account_balance": bal.get("account_balance"),
                          "month_to_date_balance": bal.get("month_to_date_balance"),
                          "month_to_date_usage": bal.get("month_to_date_usage"),
                          "generated_at": bal.get("generated_at")}
    except Exception as e:
        out["balance_error"] = _http_reason(e)
    try:
        inv = _do_get("/customers/my/invoices?per_page=6", token)
        prev = inv.get("invoice_preview") or {}
        out["current_period"] = {"amount": prev.get("amount"),
                                 "period": prev.get("invoice_period"),
                                 "uuid": prev.get("invoice_uuid")}
        out["by_product"] = _invoice_products(prev.get("invoice_uuid"), token)
        # The PREVIOUS closed invoice is the baseline that makes "a spike" measurable. A single
        # month's number tells you nothing about whether it is unusual.
        past = [i for i in (inv.get("invoices") or [])][:3]
        out["previous_invoices"] = [
            {"period": i.get("invoice_period"), "amount": i.get("amount"),
             "by_product": _invoice_products(i.get("invoice_uuid"), token)} for i in past]
    except Exception as e:
        out["invoice_error"] = _http_reason(e)
    try:
        h = _do_get("/customers/my/billing_history?per_page=25", token)
        out["history"] = [{"date": x.get("date"), "type": x.get("type"),
                           "amount": x.get("amount"), "description": x.get("description")}
                          for x in (h.get("billing_history") or [])][:25]
    except Exception as e:
        out["history_error"] = _http_reason(e)
    out["ok"] = "balance" in out or "current_period" in out
    return out


def _http_reason(e):
    if isinstance(e, urllib.error.HTTPError):
        if e.code == 401:
            return "401 unauthorised - the DO_API_TOKEN is wrong, expired, or lacks read scope"
        if e.code == 403:
            return "403 forbidden - the token has no billing read permission"
        return "HTTP %d" % e.code
    return str(e)[:120]


def _invoice_products(uuid, token):
    """[(product, amount)] for one invoice. [] when it cannot be read, never a guess."""
    if not uuid:
        return []
    try:
        s = _do_get("/customers/my/invoices/%s/summary" % uuid, token)
        items = ((s.get("product_charges") or {}).get("items") or [])
        rows = [(str(i.get("name") or "?"), float(i.get("amount") or 0)) for i in items]
        return sorted(rows, key=lambda r: -r[1])
    except Exception:
        return []


HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", "")
SSH  = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"] + (["-i", KEY] if KEY and os.path.exists(KEY) else [])
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


# ---------------------------------------------------------------------------------------------
# WHO IS CALLING THE MODELS WE NEVER CALL  (`python cost_report.py --trace`)
#
# On 2026-09-01 DO's Serverless Inference insights showed `deepseek-v4-pro-0813` and
# `glm-5.3-flash` consuming >96% of input and >98% of output tokens on the account. Neither model
# appears anywhere in this repository. The droplet hosts five containers from four projects and
# they share one DO account, so "not ours" was as far as reading our own code could get.
#
# THE MODEL NAME IS THE FINGERPRINT. A process that calls a model has that model's id somewhere:
# in its environment, in its code or config on disk, or in its logs. So this greps for the two ids
# across every container on both droplets, every mounted host path, and the local working copies.
#
# IT ALSO GROUPS CONTAINERS BY API-KEY FINGERPRINT, which is the question underneath the question:
# not "who called it" but "who CAN spend on this bill". The key value is never printed, only
# sha256[:8] and its length, so the grouping is visible and the secret is not.
#
# READ-ONLY. Every command below is an inspect, a grep or a log read.
TRACE_MODELS = [m.strip() for m in os.environ.get(
    "TRACE_MODELS", "deepseek-v4-pro,glm-5.3,glm-5,deepseek-v4").split(",") if m.strip()]

# Where a container keeps code. Grepping from / would walk /proc and every layer and take minutes.
TRACE_DIRS = "/app /opt /srv /code /usr/src /home /etc"


def _trace_script(pattern):
    return r"""
set +e
PAT='%s'
echo "#### CONTAINERS"
docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}' 2>/dev/null
echo "#### KEYS"
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$c" 2>/dev/null \
    | grep -E '^[A-Z_]*(API_KEY|INFERENCE_KEY|TOKEN)=' | while IFS= read -r kv; do
      n="${kv%%%%=*}"; v="${kv#*=}"
      [ -z "$v" ] && continue
      fp=$(printf '%%s' "$v" | sha256sum | cut -c1-8)
      echo "$c|$n|sha256:$fp|len=${#v}"
    done
done
echo "#### MODEL_ENV"
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$c" 2>/dev/null \
    | grep -iE "$PAT|_MODEL=|MODELS=" | sed "s|^|$c\||"
done
echo "#### MODEL_FILES_IN_CONTAINERS"
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
  docker exec "$c" sh -c "grep -rlI -E '$PAT' %s 2>/dev/null | head -6" 2>/dev/null \
    | sed "s|^|$c\||"
done
echo "#### MODEL_FILES_ON_HOST"
grep -rlI -E "$PAT" /opt /srv /root /etc 2>/dev/null | head -25
echo "#### MODEL_IN_LOGS_72H"
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
  n=$(docker logs --since 72h "$c" 2>&1 | grep -icE "$PAT")
  [ "$n" != "0" ] && echo "$c|$n"
done
echo "#### INFERENCE_ENDPOINT_USERS"
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
  h=$(docker exec "$c" sh -c "grep -rlI 'inference.do-ai' %s 2>/dev/null | head -3" 2>/dev/null)
  [ -n "$h" ] && echo "$c|$(echo $h | tr '\n' ' ')"
done
echo "#### STARTED"
# WHEN, not just what. The spike began on 08/31 against a flat baseline, so anything that started
# or restarted around then is a suspect and anything running untouched since 08/19 is much less
# likely to be it. A list of names cannot answer that; a list of start times can.
for c in $(docker ps -a --format '{{.Names}}' 2>/dev/null); do
  t=$(docker inspect -f '{{.State.StartedAt}}' "$c" 2>/dev/null)
  r=$(docker inspect -f '{{.RestartCount}}' "$c" 2>/dev/null)
  echo "$t|$c|restarts=$r"
done | sort -r
echo "#### OUTBOUND_NOW"
# Anything holding a connection to the inference endpoint RIGHT NOW. A live socket is proof of a
# caller in a way that a config file never is - which is the mistake that named the wrong project.
(ss -tnp 2>/dev/null || netstat -tnp 2>/dev/null) | grep -iE 'ESTAB' | head -20
echo "#### RECENT_LLM_LOGS"
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
  docker logs --since 48h --timestamps "$c" 2>&1 \
    | grep -iE "$PAT|inference\.do-ai|chat/completions" | tail -4 | sed "s|^|$c\||"
done
""" % (pattern, TRACE_DIRS, TRACE_DIRS)


def trace_remote(host, label):
    try:
        from recover import ssh_script, sections
    except Exception as e:
        return {"error": "cannot import recover.py: %s" % e}
    prev = os.environ.get("DROPLET_HOST")
    os.environ["DROPLET_HOST"] = host
    try:
        # ssh_script returns (stdout, stderr, returncode) -- READ, not guessed. The first version
        # of this line assumed a bare string and "defended" with `isinstance(out, str)`, which is
        # not a defence: a tuple is truthy, so it sailed through to sections() and died on
        # 'tuple' object has no attribute 'splitlines'. Guessing a helper's contract and then
        # writing a guard around the guess is worse than reading six lines of the helper.
        out, err, rc = ssh_script(_trace_script("|".join(TRACE_MODELS)), timeout=300)
        if rc != 0 and not (out or "").strip():
            return {"error": "%s: ssh rc=%s %s" % (label, rc, (err or "").strip()[:140])}
        return sections(out or "")
    except Exception as e:
        return {"error": "%s: %s" % (label, str(e)[:160])}
    finally:
        if prev is None:
            os.environ.pop("DROPLET_HOST", None)
        else:
            os.environ["DROPLET_HOST"] = prev


def trace_local(roots=None):
    """The operator suspected a LOCAL docker project. A machine he runs is as able to spend on
    that key as the droplet is, and it would leave no trace on either droplet at all."""
    import re
    hits = []
    pat = re.compile("|".join(re.escape(m) for m in TRACE_MODELS), re.I)
    skip = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "site-packages"}
    for root in (roots or [os.path.dirname(os.path.abspath(__file__))]):
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for f in files:
                if not f.endswith((".py", ".js", ".ts", ".json", ".yml", ".yaml", ".env",
                                   ".toml", ".sh", ".md", ".txt")) and "env" not in f.lower():
                    continue
                p = os.path.join(dirpath, f)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        for i, line in enumerate(fh, 1):
                            if pat.search(line):
                                hits.append((p, i, line.strip()[:110]))
                                break
                except Exception:
                    pass
            if len(hits) > 200:
                return hits
    return hits


def render_trace(prod, stage, local):
    print("\n" + "=" * 74)
    print("  WHO IS CALLING %s" % ", ".join(TRACE_MODELS))
    print("=" * 74)
    print("  The model id is the fingerprint: a process that calls a model carries its name in")
    print("  the environment, in code on disk, or in its logs. Read-only throughout.\n")

    for label, host, d in (("PRODUCTION", "64.225.108.200", prod),
                           ("STAGING", "165.245.244.174", stage)):
        print("  " + "-" * 70)
        print("  %s  %s" % (label, host))
        if not d or d.get("error"):
            print("    [!] %s" % ((d or {}).get("error") or "no data"))
            continue
        cs = [l for l in (d.get("CONTAINERS") or "").splitlines() if "|" in l]
        print("    containers: %s" % ", ".join(l.split("|")[0] for l in cs) or "none")

        # THE KEY GROUPING IS THE REAL ANSWER: not who called it, but who CAN spend on this bill.
        keys = {}
        for line in (d.get("KEYS") or "").splitlines():
            p = line.split("|")
            if len(p) >= 4:
                keys.setdefault(p[2], []).append("%s (%s)" % (p[0], p[1]))
        if keys:
            print("\n    API KEYS IN USE (value never printed, only its fingerprint)")
            for fp, who in sorted(keys.items(), key=lambda kv: -len(kv[1])):
                shared = "  <-- SHARED by %d containers" % len(who) if len(who) > 1 else ""
                print("      %s%s" % (fp, shared))
                for w in who:
                    print("          %s" % w)

        for sec, title in (("MODEL_ENV", "the model id is in these containers' ENVIRONMENT"),
                           ("MODEL_FILES_IN_CONTAINERS", "...and in these files inside containers"),
                           ("MODEL_FILES_ON_HOST", "...and in these files on the host"),
                           ("MODEL_IN_LOGS_72H", "...and appears this many times in 72h of logs"),
                           ("INFERENCE_ENDPOINT_USERS", "containers that reference the endpoint")):
            body = [l for l in (d.get(sec) or "").splitlines() if l.strip()]
            if body:
                print("\n    %s" % title.upper())
                for l in body[:14]:
                    print("      %s" % l[:110])

    print("\n  " + "-" * 70)
    print("  THIS MACHINE (the local docker project you suspected)")
    if not local:
        print("    no reference to those models in the local working copies")
    else:
        for p, i, line in local[:20]:
            print("    %s:%d" % (p, i))
            print("        %s" % line)
    print()
    print("  IF NOTHING ABOVE NAMES A CALLER, the spender is not on these droplets and not in")
    print("  these checkouts. Then the answer is in DO's own per-key usage:")
    print("    Serverless Inference -> Manage -> model access keys, and read usage per key.")
    print("  A key you cannot account for should be REVOKED, not investigated further.\n")


def meter_report():
    """Per-caller AI spend from the droplet's llm_meter. READ-ONLY, one ssh session.

    This is the half that names WHO. Until 2026-09-01 the answer to "which part of the system is
    spending the money" did not exist anywhere, because only assessments were counted.
    """
    cmd = SSH + ["%s@%s" % (USER, HOST),
                 "docker exec %s python3 /opt/shodan-skill/scripts/llm_meter.py 30" % CT]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=60)
    if r.returncode:
        return {"error": (r.stderr or r.stdout).strip()[:200] or "remote read failed"}
    try:
        return json.loads(r.stdout[r.stdout.index("{"):])
    except Exception:
        return {"error": "could not parse the meter output"}


def render_spend(do, meter, ledger):
    """DO's own numbers, ours, and THE GAP BETWEEN THEM.

    Printing either side alone is what turned this into two days of guessing: the ledger said
    under a dollar, the bank said fifteen euros, and nothing put the two on the same page.
    """
    print("\n" + "=" * 72)
    print("  DIGITALOCEAN SPEND  (the vendor's own numbers, read-only)")
    print("=" * 72)
    if not do:
        print("  SKIPPED - no DO_API_TOKEN.")
        print("  Mint a READ-scoped token at https://cloud.digitalocean.com/account/api/tokens")
        print("  and put DO_API_TOKEN=... in golive.secrets.env (gitignored), then re-run.")
        print("  This is the one thing no script can do for you: only the account owner can mint it.")
    else:
        b = do.get("balance") or {}
        if b:
            print("  account balance      : %s" % b.get("account_balance"))
            print("  month to date usage  : %s   (as at %s)"
                  % (b.get("month_to_date_usage"), b.get("generated_at")))
        for k in ("balance_error", "invoice_error", "history_error"):
            if do.get(k):
                print("  [!] %-18s %s" % (k.replace("_error", ""), do[k]))
        cur = do.get("current_period") or {}
        if cur.get("amount") is not None:
            print("\n  CURRENT PERIOD %s : %s" % (cur.get("period") or "", cur.get("amount")))
        rows = do.get("by_product") or []
        if rows:
            print("  %-46s %12s" % ("product", "USD"))
            for name, amt in rows:
                mark = "  <-- AI" if _is_ai(name) else ""
                print("  %-46s %12.2f%s" % (name[:46], amt, mark))
        for inv in (do.get("previous_invoices") or []):
            print("\n  PREVIOUS %s : %s" % (inv.get("period") or "", inv.get("amount")))
            for name, amt in (inv.get("by_product") or [])[:8]:
                print("    %-44s %12.2f%s" % (name[:44], amt, "  <-- AI" if _is_ai(name) else ""))
        hist = do.get("history") or []
        if hist:
            print("\n  RECENT BILLING EVENTS (the $5 auto-recharges show up here)")
            for x in hist[:10]:
                print("    %-12s %-10s %10s  %s" % (str(x.get("date"))[:10], str(x.get("type"))[:10],
                                                    x.get("amount"), str(x.get("description"))[:44]))

    print("\n" + "=" * 72)
    print("  WHAT WE CAN ACCOUNT FOR  (our own meter, per caller)")
    print("=" * 72)
    if meter.get("error"):
        print("  [!] %s" % meter["error"])
    elif not meter.get("per_caller"):
        print("  no calls recorded yet. The meter starts counting from the deploy that added it,")
        print("  so it CANNOT explain spend that happened before then - only the DO invoice can.")
    else:
        print("  cap $%.2f/day   today $%.4f   meter healthy: %s"
              % (meter.get("cap_usd", 0), meter.get("today_usd") or 0, meter.get("healthy")))
        print("\n  BY CALLER (30d)")
        print("  %-24s %8s %12s" % ("caller", "calls", "USD"))
        for c in meter["per_caller"]:
            print("  %-24s %8d %12.4f" % (c["caller"][:24], c["calls"], c["usd"]))
        print("\n  BY MODEL (30d)")
        for m in meter.get("per_model", []):
            print("  %-24s %8d %12.4f" % (m["model"][:24], m["calls"], m["usd"]))
        pd = meter.get("per_day") or []
        if pd:
            print("\n  PER DAY")
            for r in pd[-14:]:
                print("  %-12s %6d calls  $%8.4f  (%s out)" % (r["day"], r["calls"], r["usd"],
                                                               f"{r['tout']:,}"))
        worst = meter.get("most_expensive_calls") or []
        if worst:
            print("\n  MOST EXPENSIVE SINGLE CALLS - a runaway prompt shows up here first")
            for w in worst[:5]:
                print("    $%.4f  %-20s %-20s %s out"
                      % (w["usd"], w["caller"][:20], w["model"][:20], f"{w['tout']:,}"))

    # THE RECONCILIATION. The gap is the finding.
    ai = sum(a for n, a in (do.get("by_product") or []) if _is_ai(n)) if do else None
    ours = sum(c["usd"] for c in (meter.get("per_caller") or []))
    print("\n  " + "-" * 68)
    if ai is None:
        print("  RECONCILIATION: not possible without DO_API_TOKEN.")
    else:
        print("  DO charges for AI this period : $%.2f" % ai)
        print("  our meter accounts for        : $%.4f" % ours)
        gap = ai - ours
        print("  UNEXPLAINED                   : $%.2f" % gap)
        if gap > max(1.0, ai * 0.25):
            print("\n  A LARGE GAP HERE IS ITSELF THE ANSWER and it has three possible causes,")
            print("  in the order worth checking:")
            print("    1. the meter was deployed AFTER the spend happened (compare the dates above)")
            print("    2. something outside this repository is using the same API key")
            print("       -> rotate it: https://cloud.digitalocean.com/account/api/tokens")
            print("    3. the charge is not inference at all. Read the per-product table above")
            print("       before assuming it is: droplets, Spaces and bandwidth share one invoice.")
    print()


def _is_ai(name):
    n = str(name or "").lower()
    return any(k in n for k in ("inference", "gen ai", "genai", "serverless ai", "model", "agent"))


def main():
    if "--trace" in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        roots = [here] + [p for p in (os.environ.get("TRACE_ROOTS", "").split(os.pathsep)) if p]
        # The sibling projects live beside this one on the operator's machine and are the most
        # likely local suspects, so they are scanned without being asked for.
        for sib in ("jobhuntwow-app", os.path.join(os.path.dirname(here), "Vendor SDWAN OSINT")):
            p = sib if os.path.isabs(sib) else os.path.join(here, sib)
            if os.path.isdir(p) and p not in roots:
                roots.append(p)
        render_trace(trace_remote(os.environ.get("DROPLET_HOST", "64.225.108.200"), "production"),
                     trace_remote(os.environ.get("STAGING_HOST", "165.245.244.174"), "staging"),
                     trace_local(roots))
        return

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
    # The spend investigation runs by DEFAULT, because the question it answers ("where did the
    # money go") is the one somebody actually has when they open this script. --ledger-only skips
    # it for the narrow per-assessment view this file originally had.
    spend = None
    if "--ledger-only" not in sys.argv and not local:
        tok = _do_token()
        spend = {"do": do_billing(tok) if tok else None, "meter": meter_report()}
    if "--json" in sys.argv:
        print(json.dumps({"ledger": d, "spend": spend}, indent=2, default=str))
    else:
        render(d)
        if spend is not None:
            render_spend(spend["do"], spend["meter"], d)


if __name__ == "__main__":
    main()
