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


def do_agents(token):
    """Agents running on DO's OWN Agent Platform, plus the model access keys on the account.

    WHY THIS IS HERE AND NOT IN THE CODE SCAN: an agent created in the DO console runs on DO's
    infrastructure. It appears in no repository, on no droplet, and in no container -- so grepping
    source for a model name can never find it, however thorough the grep. The console sidebar in
    the operator's screenshot lists "Agent Platform", so this is a live possibility and not a
    hypothetical, and it is exactly the sort of caller that produces a step-change on one day
    against a flat baseline.

    Best-effort: these endpoints are newer than the billing API and may not be enabled on every
    account. A failure is REPORTED, never silently swallowed as "no agents" - the difference
    between "there are none" and "I could not look" is the whole point.
    """
    out = {}
    for label, path in (("agents", "/gen-ai/agents"),
                        ("model_keys", "/gen-ai/models/api_keys")):
        try:
            d = _do_get(path, token)
            out[label] = d
        except Exception as e:
            out[label + "_error"] = _http_reason(e)
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
    # OVERRIDE THE MODULE ATTRIBUTE, NOT THE ENVIRONMENT.
    # recover.py does `HOST = os.environ.get("DROPLET_HOST", "64.225...")` at IMPORT time, so
    # setting the env var after importing it changes nothing. The first version did exactly that
    # and both calls went to production: the "STAGING" block in the 2026-09-01 output was a
    # verbatim duplicate of production, right down to an OUTBOUND_NOW listing 64.225.108.200.
    # Two identical blocks under different headings is worse than one, because it reads as
    # corroboration when it is the same measurement twice.
    import recover as _rc
    prev = _rc.HOST
    _rc.HOST = host
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
        _rc.HOST = prev


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


def render_trace(prod, stage, local, agents=None):
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

        for sec, title in (("STARTED", "container start times (the spike began 08/31 - look here)"),
                           ("OUTBOUND_NOW", "live connections (a socket proves a caller, config does not)"),
                           ("RECENT_LLM_LOGS", "the last 48h of model traffic, with timestamps"),
                           ("MODEL_ENV", "the model id is in these containers' ENVIRONMENT"),
                           ("MODEL_FILES_IN_CONTAINERS", "...and in these files inside containers"),
                           ("MODEL_FILES_ON_HOST", "...and in these files on the host"),
                           ("MODEL_IN_LOGS_72H", "...and appears this many times in 72h of logs"),
                           ("INFERENCE_ENDPOINT_USERS", "containers that reference the endpoint")):
            body = [l for l in (d.get(sec) or "").splitlines() if l.strip()]
            if body:
                print("\n    %s" % title.upper())
                for l in body[:14]:
                    print("      %s" % l[:110])
            elif sec in ("OUTBOUND_NOW", "RECENT_LLM_LOGS"):
                # AN EMPTY DECISIVE SECTION IS A FINDING, NOT AN ABSENCE TO HIDE. Silently
                # omitting it makes "nothing is calling models here" indistinguishable from "the
                # check did not run", which is the logship defect in miniature.
                print("\n    %s" % title.upper())
                print("      NONE. That is evidence: no model traffic seen on this box.")

    print("\n  " + "-" * 70)
    print("  CONFIGURED TO USE THESE MODELS (source only - NOT proof anything ran)")
    print("  A file naming a model says the project COULD call it. It does not say a process did.")
    print("  On 2026-09-01 that distinction was got wrong here: jobhuntwow was named from its")
    print("  config, and the operator then showed that Docker Desktop was not even running.")
    if not local:
        print("    no reference to those models in the local working copies")
    else:
        for p, i, line in local[:20]:
            print("    %s:%d" % (p, i))
            print("        %s" % line)
    print()
    if agents is not None:
        print("  " + "-" * 70)
        print("  DIGITALOCEAN AGENT PLATFORM (runs on DO's side - invisible to any code scan)")
        for k in ("agents", "model_keys"):
            if agents.get(k + "_error"):
                print("    [!] %-11s could not be read: %s" % (k, agents[k + "_error"]))
                continue
            d = agents.get(k) or {}
            items = d.get(k) or d.get("agents") or d.get("api_key_infos") or []
            if not items:
                print("    %-11s none on this account" % k)
            else:
                print("    %-11s %d found" % (k, len(items)))
                for it in items[:10]:
                    print("      %s  created=%s" % (str(it.get("name") or it.get("uuid"))[:40],
                                                    str(it.get("created_at"))[:19]))
        print()

    print("  " + "=" * 68)
    print("  HOW TO ACTUALLY SETTLE THIS")
    print()
    print("  If the key table above shows ONE fingerprint across several containers, then DO's")
    print("  per-key usage page CANNOT separate them either - every project is the same key, so")
    print("  the vendor sees one caller. That is the real reason this is hard to attribute, and")
    print("  no amount of grepping will fix it.")
    print()
    print("    1. Issue a SEPARATE model access key per project (DO -> Serverless Inference ->")
    print("       Manage -> model access keys), put each in that project's env, and redeploy.")
    print("       Within hours the Insights page attributes spend by key, permanently.")
    print("    2. Until then, DO -> Agent Platform in the console: an agent there runs on DO's")
    print("       infrastructure and appears nowhere in this output except the section above.")
    print("    3. A key you cannot account for should be REVOKED, not investigated further.")
    print()
    print("  Everything this script gathers is weaker than the vendor's own per-key record.\n")


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


# =================================================================================================
# LOKI CORRELATION -- "which project was calling the inference endpoint while the money moved?"
#
# WHY LOKI AND NOT ANOTHER PROBE. Everything else in this file is a SNAPSHOT: `--trace` lists the
# sockets open at the moment it runs and the containers started before it, which is why it produced
# "OUTBOUND_NOW: only tailscale and sshd" -- true, and worth nothing about a spike that happened
# last Sunday. Loki is the only thing on this estate that holds the PAST. The spike is over; a
# snapshot cannot be pointed at it, and a log can.
#
# WHAT IS ACTUALLY IN THERE, measured rather than assumed:
#   * {job="coltbots"}   -- /logs/events.log, shipped by colt-promtail. `evt=qwen` is emitted by
#                           enrich.py once per model call and carries model, tokens_in, tokens_out
#                           and cost_usd IN THE LINE (promtail promotes only evt/bot/company/status
#                           to labels, so the numbers have to be unwrapped with `| json`).
#   * {job="jobhuntwow"} -- /logs/jhw-web.log, on the SAME shared colt_events volume. It carries
#                           http, auth and security_alert events and NOT ONE model call:
#                           electronic.py:104 receives `_usage` from call_model and discards it.
#
# THAT SECOND POINT IS THE HONEST ANSWER TO "use the data we have". For cybergod the data is there
# and this query reads it. For jobhuntwow it is not there to read, so this prints the gap by name
# instead of rendering an empty series as if it were a quiet project -- the same distinction
# logship got wrong when it reported success for a week while shipping nothing.
#
# EVEN WITH THE GAP, THE CORRELATION IS DECISIVE BY EXCLUSION. If DigitalOcean bills 836k tokens in
# a window and coltbots' own log accounts for 30k against models that are all in our committed
# chain, then the remaining 806k did not come from this codebase -- and neither runaway id has ever
# appeared in a `evt=qwen` line, which is a positive statement about the past rather than a guess.
# =================================================================================================
# RAW LINES, SUBSTRING FILTERS, EVERY STREAM. Everything in LOKI_QUERIES assumes the line is JSON
# with fields called evt/path/ip at the top level. If a stream stores the line wrapped (docker's
# {"log": "...", "stream": "stdout"} shape, for instance) every metric row above it is zero and
# reads as innocence. These ask the question the operator actually asked -- "we know the model
# names and the dates" -- with `|=` substring filters that cannot be defeated by line shape, and
# they return the LINES so the shape is read, not assumed. (title, LogQL, limit)
LOKI_SAMPLES = [
    ("lines naming deepseek-v4-pro, ANY container", '{container=~".+"} |= "deepseek-v4-pro"', 40),
    ("lines naming glm-5.3, ANY container", '{container=~".+"} |= "glm-5.3"', 40),
    ("lines naming deepseek-v4-pro, the file stream", '{job="coltbots"} |= "deepseek-v4-pro"', 20),
    ("lines naming glm-5.3, the file stream", '{job="coltbots"} |= "glm-5.3"', 20),
    ("jhw-web stdout lines mentioning the proxy path",
     '{container=~".*jhw-web.*"} |= "/v1/chat/completions"', 40),
    ("jhw-web stdout: what a line LOOKS like (shape check)", '{container=~".*jhw-web.*"}', 5),
    # THE DOOR IT ACTUALLY CAME THROUGH (found 2026-09-06): /api/chat was PUBLIC, took any model
    # id, and streamed it on our key. Every hit is an evt=http line with ip + user + status.
    ("WHO called /api/chat (ip + user on every line)",
     '{container=~".*jhw-web.*"} |= "/api/chat" |= "\\"evt\\": \\"http\\""', 60),
]
# Per-hour substring counts, for lining up against DO's Insights graph by the clock.
LOKI_HOURLY = [
    ("/api/chat calls in jhw-web stdout, per hour (the public chat door)",
     'sum(count_over_time({container=~".*jhw-web.*"} |= "/api/chat" [1h]))'),
    ("proxy path in jhw-web stdout, per hour (substring, no JSON)",
     'sum(count_over_time({container=~".*jhw-web.*"} |= "/v1/chat/completions" [1h]))'),
    ("deepseek-v4-pro named anywhere, per hour",
     'sum by (container) (count_over_time({container=~".+"} |= "deepseek-v4-pro" [1h]))'),
    ("glm-5.3 named anywhere, per hour",
     'sum by (container) (count_over_time({container=~".+"} |= "glm-5.3" [1h]))'),
]

LOKI_QUERIES = [
    # (title, LogQL, what a number here MEANS)
    #
    # THE LABEL WAS WRONG FOR SIX DAYS. jhw-web writes to /var/log/colt/events.log -- the SAME file
    # as cybergod, on the same volume -- and its compose file says so ("already tailed by
    # colt-promtail"). So every jobhuntwow line has been in Loki the whole time under
    # job="coltbots", distinguished by the `service` field IN THE LINE (colt-promtail promotes only
    # evt/bot/company/status to labels). The first version of these queries asked for
    # job="jobhuntwow", a label that only a never-deployed promtail config would have set, got
    # zero, and concluded "NOT SHIPPING". The probe was honest; the conclusion was not. The
    # project was never blind. I was reading the wrong label.
    #
    # ONE STREAM, TWO SERVICES. Everything below selects by service, and the two visibility probes
    # now prove each SERVICE is present rather than each job.
    ("CAN WE SEE jobhuntwow AT ALL (any line, any type)",
     'sum(count_over_time({job="coltbots"} | json | service="jhw-web" [%(step)s]))',
     "IF THIS IS ZERO, every jobhuntwow row below is BLIND, not innocent"),
    ("CAN WE SEE cybergod AT ALL (any line, any type)",
     'sum(count_over_time({job="coltbots"} | json | service!="jhw-web" [%(step)s]))',
     "same, for the other project"),
    # THE THIRD STREAM, and the one that actually holds the evidence (2026-09-06, third run).
    # jhw-web runs as UID 10001 (Dockerfile.web: USER jhw) while events.log on the shared volume is
    # created by cybergod's containers as root, 0644. jhw's `open(EVENTS_LOG, "a")` therefore
    # raises PermissionError on EVERY write and telemetry.emit swallows it (`except: pass`), so the
    # file holds ZERO jhw lines and the two probes above are honestly blind. But emit() prints the
    # SAME line to stdout first, and videodead-promtail scrapes every container's docker stdout
    # into Loki with a `container` label -- the accident that once carried the assessment engine's
    # events under container=~".*assess-bot.*". Loki keeps 30 days, so the Sep 1 and Sep 3 proxy
    # hits survive there even though the container itself was recreated on Sep 6.
    ("CAN WE SEE jobhuntwow-stdout AT ALL (docker stdout via videodead-promtail)",
     'sum(count_over_time({container=~".*jhw-web.*"} [%(step)s]))',
     "the stream that survives the permission bug; zero here means the docker scrape is off"),
    ("WHO called the jobhuntwow LLM proxy (by source IP, from docker stdout)",
     'sum by (ip) (count_over_time({container=~".*jhw-web.*"} | json | evt="http"'
     ' | path=~"/v1/chat/completions.*" [%(step)s]))',
     "same question as the row below, answered from the stream jhw could actually write to"),
    # FIRST SUBSTANTIVE ROW, because it is the one that names a SOURCE. jhw-web's telemetry logs
    # every request with its client IP and skips only static assets, so the OpenAI-compatible proxy
    # at /v1/chat/completions -- the endpoint that forwarded ANY model slug to DigitalOcean on our
    # key -- has been queryable since day one. It needed the right label, not a deploy.
    ("WHO called the jobhuntwow LLM proxy (by source IP)",
     'sum by (ip) (count_over_time({job="coltbots"} | json | service="jhw-web" | evt="http"'
     ' | path=~"/v1/chat/completions.*" [%(step)s]))',
     "each row is an address that spent on the shared key through the proxy; match the hours"
     " against DigitalOcean's Insights and the spender has a source address"),
    ("jobhuntwow model calls, per model (NEW - emitted since 2026-09-06)",
     'sum by (model) (count_over_time({job="coltbots"} | json | service="jhw-web"'
     ' | evt="llm_call" [%(step)s]))',
     "jhw's own metered calls; before 6 Sep it emitted none, so this row is empty for the spike"),
    ("cybergod model calls, per model",
     'sum by (model) (count_over_time({job="coltbots"} | json | service!="jhw-web"'
     ' | evt="qwen" [%(step)s]))',
     "one entry per call enrich.py made; a model absent here was not called by this codebase"),
    ("cybergod output tokens, per model",
     'sum by (model) (sum_over_time({job="coltbots"} | json | service!="jhw-web" | evt="qwen"'
     ' | unwrap tokens_out [%(step)s]))',
     "compare against DO's Insights page: a large gap is spend that is not ours"),
    ("cybergod AI cost (USD)",
     'sum(sum_over_time({job="coltbots"} | json | service!="jhw-web" | evt="qwen"'
     ' | unwrap cost_usd [%(step)s]))',
     "our own metered cost over the window"),
    ("attack volume, cybergod (404s to non-bots)",
     'sum(count_over_time({job="coltbots"} | json | service!="jhw-web" | evt="http"'
     ' | status="404" [%(step)s]))',
     "OVERLAY. If AI spend tracks this, attack response is driving cost; if it does not, it is not"),
    ("attack volume, jobhuntwow (404s to non-bots)",
     'sum(count_over_time({job="coltbots"} | json | service="jhw-web" | evt="http"'
     ' | status="404" [%(step)s]))',
     "same overlay for the other project - it was under active scan on 1 and 3 Sep"),
]


def _loki_script(queries, start, end, step):
    """One ssh session that asks Loki every question. Built as a bash script rather than a series of
    `ssh` calls because the Windows OpenSSH client has no ControlMaster multiplexing and sshd
    penalises rapid repeat connections -- the rule this repository already paid for twice."""
    # GROUND TRUTH FIRST, AND IT DOES NOT NEED LOKI. The raw events.log sits on the persistent
    # colt_events volume; every jhw-web request line (evt=http, with ip + path + ts) is appended
    # there by the app itself. Loki is an INDEX over that file. When the index answers "0 lines"
    # the file says which hop is broken: jhw-web not mounting the volume, not carrying EVENTS_LOG,
    # not writing, or writing while Loki fails to parse/promote. And it answers the attribution
    # question directly: grep the proxy path, read the source addresses. The 2026-09-06 run
    # printed BLIND twice from the index alone while the file was one grep away.
    body = ['echo "#### FILE"',
            "E=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination \"/var/log/colt\"}}"
            "{{.Source}}{{end}}{{end}}' jhw-web 2>/dev/null)",
            'echo "jhw_mount=${E:-NONE}"',
            "docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' jhw-web 2>/dev/null "
            "| grep -E '^(EVENTS_LOG|SERVICE)=' | sed 's/^/jhw_env=/'",
            'F="${E:-/var/lib/docker/volumes/colt-stack_colt_events/_data}/events.log"',
            'if [ -f "$F" ]; then',
            '  echo "file=$F size=$(stat -c %s "$F")"',
            '  echo "jhw_lines=$(grep -c -F \'"service": "jhw-web"\' "$F")"',
            '  echo "jhw_first=$(grep -F \'"service": "jhw-web"\' "$F" | head -1 | cut -c1-240)"',
            '  echo "jhw_last=$(grep -F \'"service": "jhw-web"\' "$F" | tail -1 | cut -c1-240)"',
            '  grep -F "/v1/chat/completions" "$F" | grep -F \'"evt": "http"\' | tail -200 '
            '| cut -c1-600 | sed "s/^/proxy=/"',
            'else',
            '  echo "file=MISSING $F"',
            'fi',
            "L=$(docker ps --format '{{.Names}}' | grep -iE 'loki' | head -1)",
            'echo "#### LOKI"; echo "${L:-NONE}"',
            '[ -z "$L" ] && exit 0',
            "q(){ docker exec \"$L\" wget -qO- --header='Content-Type: application/json' "
            "\"http://127.0.0.1:3100/loki/api/v1/query_range?query=$1&start=%s&end=%s&step=%s\" "
            "2>/dev/null; }" % (start, end, step)]
    for i, (title, q, _why) in enumerate(queries):
        # urlencode just enough: LogQL is full of characters wget would mangle in a query string.
        enc = (q % {"step": step + "s" if step.isdigit() else step})
        for a, b in (("%", "%25"), ("{", "%7B"), ("}", "%7D"), ('"', "%22"), (" ", "%20"),
                     ("|", "%7C"), ("(", "%28"), (")", "%29"), ("[", "%5B"), ("]", "%5D"),
                     ("=", "%3D"), ("+", "%2B"), ("&", "%26")):
            enc = enc.replace(a, b)
        body.append('echo; echo "#### Q%d"; q "%s"' % (i, enc))
    # log-line samples: query_range with a LOG selector returns streams; limit + newest-first
    body.append("s(){ docker exec \"$L\" wget -qO- \"http://127.0.0.1:3100/loki/api/v1/query_range"
                "?query=$1&start=%s&end=%s&limit=$2&direction=backward\" 2>/dev/null; }" % (start, end))
    for i, (_t, q, lim) in enumerate(LOKI_SAMPLES):
        body.append('echo; echo "#### S%d"; s "%s" %d' % (i, _enc(q), lim))
    body.append("h(){ docker exec \"$L\" wget -qO- \"http://127.0.0.1:3100/loki/api/v1/query_range"
                "?query=$1&start=%s&end=%s&step=3600\" 2>/dev/null; }" % (start, end))
    for i, (_t, q) in enumerate(LOKI_HOURLY):
        body.append('echo; echo "#### H%d"; h "%s"' % (i, _enc(q)))
    return "\n".join(body) + "\n"


def _enc(q):
    for a, b in (("%", "%25"), ("\\", "%5C"), ("{", "%7B"), ("}", "%7D"), ('"', "%22"), (" ", "%20"),
                 ("|", "%7C"), ("(", "%28"), (")", "%29"), ("[", "%5B"), ("]", "%5D"),
                 ("=", "%3D"), ("+", "%2B"), ("&", "%26")):
        q = q.replace(a, b)
    return q


def file_evidence(text, start_ts=0):
    """Parse the '#### FILE' section: what the raw events.log on the droplet says about jhw-web.

    Returns mount/env facts, how many jhw-web lines the FILE holds (independent of Loki), the
    first and last of them (so 'no evidence for Sep 1' can be told apart from 'jhw joined the
    shared file on Sep 5'), and every proxy hit with ip + status + day, aggregated per source.
    """
    fe = {"mount": "", "env": [], "file": "", "jhw_lines": 0, "jhw_first_ts": None,
          "jhw_last_ts": None, "proxy": [], "per_ip": {}, "per_day": {}}
    for ln in (text or "").splitlines():
        ln = ln.rstrip()
        if ln.startswith("jhw_mount="):
            fe["mount"] = ln[len("jhw_mount="):].strip()
        elif ln.startswith("jhw_env="):
            fe["env"].append(ln[len("jhw_env="):].strip())
        elif ln.startswith("file="):
            fe["file"] = ln[len("file="):].strip()
        elif ln.startswith("jhw_lines="):
            try: fe["jhw_lines"] = int(ln.split("=", 1)[1])
            except Exception: pass
        elif ln.startswith("jhw_first=") or ln.startswith("jhw_last="):
            key = "jhw_first_ts" if ln.startswith("jhw_first=") else "jhw_last_ts"
            try:
                fe[key] = float(json.loads(ln.split("=", 1)[1]).get("ts"))
            except Exception:
                pass
        elif ln.startswith("proxy="):
            try:
                d = json.loads(ln[len("proxy="):])
            except Exception:
                continue
            ts = float(d.get("ts") or 0)
            if start_ts and ts and ts < start_ts:
                continue
            ip = str(d.get("ip") or "?")
            day = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d") if ts else "?"
            fe["proxy"].append({"ts": ts, "day": day, "ip": ip,
                                "status": str(d.get("status") or "?"),
                                "path": str(d.get("path") or "")[:60]})
            fe["per_ip"][ip] = fe["per_ip"].get(ip, 0) + 1
            fe["per_day"][day] = fe["per_day"].get(day, 0) + 1
    return fe


def loki_correlate(host, days=10, step_hours=6):
    """Ask Loki what each project was doing, hour by hour, across the window."""
    try:
        from recover import ssh_script, sections
    except Exception as e:
        return {"error": "recover.py not importable: %s" % repr(e)[:100]}
    import recover as _rc
    prev = _rc.HOST
    _rc.HOST = host          # MODULE ATTRIBUTE. recover reads DROPLET_HOST at IMPORT time, so
    try:                     # setting the env var here does nothing -- already found once, when
        end = int(datetime.datetime.now(datetime.timezone.utc).timestamp())   # "staging" came back
        start = end - days * 86400                                            # a copy of production.
        step = str(step_hours * 3600)
        # ssh_script returns (stdout, stderr, returncode). READ, not guessed.
        out, err, rc = ssh_script(_loki_script(LOKI_QUERIES, start, end, step), timeout=180)
    except Exception as e:
        return {"error": repr(e)[:160]}
    finally:
        _rc.HOST = prev
    if rc != 0 and not out:
        return {"error": "ssh failed (rc=%s): %s" % (rc, (err or "")[:200])}
    sec = sections(out or "")
    fe = file_evidence(sec.get("FILE") or "", start)
    if (sec.get("LOKI") or "").strip() in ("", "NONE"):
        return {"error": "no Loki container is running on %s" % host, "file": fe}
    res = {"loki": (sec.get("LOKI") or "").strip(), "series": [], "file": fe,
           "samples": [], "hourly": []}
    for i, (title, _q, _lim) in enumerate(LOKI_SAMPLES):
        raw = (sec.get("S%d" % i) or "").strip()
        lines = []
        try:
            for st in json.loads(raw).get("data", {}).get("result", []):
                lab = st.get("stream") or {}
                who = lab.get("container") or lab.get("job") or "?"
                for ts, line in st.get("values") or []:
                    lines.append((int(ts) // 10**9, who, line))
        except Exception:
            res["samples"].append({"title": title, "error": raw[:160] or "no answer"}); continue
        lines.sort()
        res["samples"].append({"title": title, "lines": lines})
    for i, (title, _q) in enumerate(LOKI_HOURLY):
        raw = (sec.get("H%d" % i) or "").strip()
        rows = []
        try:
            for r in json.loads(raw).get("data", {}).get("result", []):
                who = (r.get("metric") or {}).get("container") or "(all)"
                pts = [(int(float(t)), float(v)) for t, v in (r.get("values") or []) if float(v) > 0]
                if pts:
                    rows.append({"who": who, "points": pts})
        except Exception:
            res["hourly"].append({"title": title, "error": raw[:160] or "no answer"}); continue
        res["hourly"].append({"title": title, "rows": rows})
    for i, (title, _q, why) in enumerate(LOKI_QUERIES):
        raw = (sec.get("Q%d" % i) or "").strip()
        try:
            d = json.loads(raw)
            rows = d.get("data", {}).get("result", [])
        except Exception:
            res["series"].append({"title": title, "why": why, "error": raw[:160] or "no answer"})
            continue
        got = []
        for r in rows:
            m = r.get("metric") or {}
            name = m.get("model") or m.get("ip") or "(total)"
            vals = [(int(float(t)), float(v)) for t, v in (r.get("values") or [])
                    if str(v) not in ("NaN",)]
            got.append({"name": name, "total": round(sum(v for _, v in vals), 4), "points": vals})
        res["series"].append({"title": title, "why": why,
                              "rows": sorted(got, key=lambda x: -x["total"])})
    return res


def render_correlate(c, days):
    print()
    print("=" * 78)
    print("LOKI CORRELATION - what each project was doing while the money moved")
    print("=" * 78)
    if c.get("error"):
        print("  [!] %s" % c["error"])
        print("      NOT 'nothing was happening'. The query did not run, so it says nothing about")
        print("      the window at all. Those are different answers and must not render the same.")
        return
    print("  loki: %s     window: last %d days" % (c.get("loki"), days))

    # VISIBILITY FIRST. Read the two "can we see this project at all" rows before anything else,
    # because they decide whether an empty row below means INNOCENT or BLIND. Getting that backwards
    # would mean either rotating a key for nothing or clearing a project that was never observed.
    blind = []
    for s in c.get("series", []):
        if s["title"].startswith("CAN WE SEE "):
            proj = s["title"].split("CAN WE SEE ", 1)[1].split(" AT ALL")[0]
            total = sum(r["total"] for r in (s.get("rows") or []))
            if not s.get("rows") or total <= 0:
                blind.append(proj)
    if blind:
        print()
        print("  " + "!" * 72)
        print("  NOT SHIPPING TO LOKI: %s" % ", ".join(blind))
        print("  Every row for those below is BLIND, not innocent. An empty result is the query")
        print("  failing to see its subject, NOT evidence that nothing happened. Fix the log")
        print("  shipper for that project first; do not conclude anything from its rows.")
        print("  " + "!" * 72)

    for s in c.get("series", []):
        print()
        print("  %s" % s["title"])
        print("    (%s)" % s["why"])
        if s.get("error"):
            print("      [!] query error: %s" % s["error"])
            continue
        rows = s.get("rows") or []
        if not rows:
            print("      NONE. That is evidence: Loki holds no matching line in this window.")
            continue
        for r in rows[:8]:
            spark = "".join(" .:-=+*#@"[min(8, int(8 * v / (max(1e-9, max(x for _, x in r["points"])))))]
                            for _, v in r["points"][-40:]) if r["points"] else ""
            print("      %-26s total %12.4f   %s" % (r["name"][:26], r["total"], spark))
    print()
    print("  HOW TO READ THIS")
    print("    * A model in DigitalOcean's Insights that appears in NO row above was not called by")
    print("      this codebase. That is a statement about the recorded past, not a guess.")
    print("    * If AI cost does NOT track the attack-volume row, attack response is not the")
    print("      spender. Measured from code: cybergod's attack-driven AI is SCHEDULE-bounded")
    print("      (shield panel 4 models/6h + digest 4 models/day, roughly 20 calls a day), and")
    print("      abuse_report.draft_complaint calls no model at all - it is string formatting.")
    print("    * jobhuntwow emits evt=llm_call only since 2026-09-06, so for the 1 and 3 Sep spike")
    print("      its MODEL rows are empty by construction. Its PROXY HITS row is not: the HTTP")
    print("      telemetry has logged /v1/chat/completions with the source IP since day one.")


def whodunit(host, days=10):
    """ONE COMMAND, ONE VERDICT: is the spender reachable through our proxy, or not?

    The operator has asked three times how to TEST this, and every answer so far has been "read
    these logs and cross-reference the console". That is not a test. This is: it gathers the three
    evidence sources, applies the decision rule, and prints the action.

    The rule is a genuine fork and both branches are decisive:
      * PROXY HITS in the window  -> the spender came through jobhuntwow's OpenAI-compatible proxy
        on our key. The IP names them. The allowlist has already closed that path, so the next
        attempt is a 403 that pages immediately.
      * NO PROXY HITS, and jhw is demonstrably visible in Loki -> nothing came through the proxy,
        so the raw DO_INFERENCE_KEY is being used from somewhere we do not run. No code change can
        fix that. ROTATE THE KEY.
      * NO PROXY HITS and jhw NOT visible -> the query is BLIND. Decide nothing; fix the shipper.
    """
    c = loki_correlate(host, days=days)
    fe = c.get("file") or {}
    out = {"loki": c.get("error") or c.get("loki"), "days": days, "file": fe,
           "visible": {}, "proxy_hits": 0, "proxy_sources": [], "verdict": "", "action": "",
           "note": ""}
    if c.get("error") and not fe:
        out["verdict"] = "CANNOT DECIDE"
        out["action"] = ("the Loki query did not run (%s). That is not evidence about the window; "
                         "fix the query path and re-run." % c["error"])
        return out
    for s in c.get("series", []):
        t = s.get("title", "")
        rows = s.get("rows") or []
        total = sum(r["total"] for r in rows)
        if t.startswith("CAN WE SEE "):
            out["visible"][t.split("CAN WE SEE ", 1)[1].split(" AT ALL")[0]] = total
        elif t.startswith("WHO called"):
            # TWO streams can answer this (the shared file via service=, and docker stdout via
            # container=); the same hit is never in both, because jhw cannot write the file.
            out["proxy_hits"] += total
            merged = {x["ip"]: x["hits"] for x in out["proxy_sources"]}
            for r in rows:
                merged[r["name"]] = merged.get(r["name"], 0) + r["total"]
            out["proxy_sources"] = [{"ip": ip, "hits": n} for ip, n in
                                    sorted(merged.items(), key=lambda kv: -kv[1])[:10]]

    # THE FILE OUTRANKS THE INDEX. Loki is a view over events.log; if the two disagree the file is
    # the primary source and the disagreement is itself a finding (an indexing gap), not a reason
    # to declare the project unobserved. The 2026-09-06 runs said BLIND from the index alone.
    file_jhw = int(fe.get("jhw_lines") or 0)
    file_hits = len(fe.get("proxy") or [])
    if file_hits and file_hits > out["proxy_hits"]:
        out["proxy_hits"] = file_hits
        out["proxy_sources"] = [{"ip": ip, "hits": n} for ip, n in
                                sorted(fe["per_ip"].items(), key=lambda kv: -kv[1])[:10]]
        out["note"] = "proxy hits read from events.log directly (Loki indexed %d of them)" % \
                      int(sum(r["total"] for s in c.get("series", []) if s.get("title", "")
                              .startswith("WHO called") for r in (s.get("rows") or [])))
    out["samples"] = c.get("samples") or []
    out["hourly"] = c.get("hourly") or []
    # SUBSTRING EVIDENCE OUTRANKS PARSED EVIDENCE. If jhw stdout holds lines mentioning the proxy
    # path but the JSON-parsed WHO row found none, the lines are wrapped and the parsed row is
    # blind by shape, not by absence.
    raw_proxy = sum(len(x.get("lines") or []) for x in out["samples"]
                    if "proxy path" in x.get("title", ""))
    if raw_proxy and out["proxy_hits"] == 0:
        out["proxy_hits"] = raw_proxy
        out["note"] = (out["note"] + "; " if out["note"] else "") + \
            "%d proxy-path lines found by SUBSTRING in jhw stdout that the JSON-parsed row missed " \
            "(the line shape differs from the assumption); read the raw lines below" % raw_proxy
    jhw_seen = (out["visible"].get("jobhuntwow", 0) > 0 or file_jhw > 0
                or out["visible"].get("jobhuntwow-stdout", 0) > 0)
    if file_jhw > 0 and out["visible"].get("jobhuntwow", 0) == 0:
        out["note"] = (out["note"] + "; " if out["note"] else "") + \
            "events.log holds %d jhw-web lines that Loki does not return - an INDEXING gap, " \
            "not a silent project" % file_jhw
    if not jhw_seen:
        out["verdict"] = "BLIND - NOT INNOCENT"
        why = []
        if not fe:
            why.append("the FILE section did not come back from the droplet")
        elif fe.get("mount", "NONE") in ("", "NONE"):
            why.append("jhw-web does not mount the shared /var/log/colt volume")
        elif not any(e.startswith("EVENTS_LOG=") for e in fe.get("env", [])):
            why.append("jhw-web has no EVENTS_LOG in its environment")
        elif fe.get("file", "").startswith("MISSING"):
            why.append("events.log is absent on the volume (%s)" % fe["file"])
        else:
            why.append("jhw-web mounts the volume and carries EVENTS_LOG, yet has written 0 lines "
                       "with service=jhw-web to %s (it runs as UID 10001 and the file is root "
                       "0644, so every append is a swallowed PermissionError) AND the docker "
                       "stdout stream is empty too" % fe.get("file"))
        out["action"] = ("jobhuntwow has left NO evidence, in Loki OR in the raw events.log, so "
                         "'no proxy hits' means nothing. Decide NOTHING from it. Cause: %s. Fix "
                         "that (python ship.py in "
                         "jobhuntwow-app redeploys it from docker-compose.web.yml, which sets both) "
                         "and re-run this command." % "; ".join(why))
    elif out["proxy_hits"] > 0:
        out["verdict"] = "THE PROXY IS THE PATH"
        out["action"] = ("the addresses above spent on the shared key through jobhuntwow's proxy. "
                         "The model allowlist now refuses anything outside DEFAULT_MODELS and "
                         "pages on every refusal, so that path is closed and the next attempt "
                         "names them again. Decide whether each address should hold "
                         "AGENT_PROXY_TOKEN at all; rotate it to cut off the ones that should not.")
    else:
        out["verdict"] = "NOT THE PROXY - ROTATE THE KEY"
        out["action"] = ("jobhuntwow IS visible in Loki and shows ZERO calls to its proxy in this "
                         "window, so the spend did not come through anything we run. That leaves "
                         "the raw DO_INFERENCE_KEY being used from elsewhere - another holder of "
                         "the key, or a GenAI agent created in the DigitalOcean console (which "
                         "runs on their infrastructure and appears in no repository and on no "
                         "droplet). No code change can fix that: ROTATE the model key in the DO "
                         "console, and issue one key PER PROJECT so the next invoice is "
                         "attributable.")
    return out


def key_audit(token):
    """The model access keys on the account, and whether each is SCOPED.

    THE GUARDRAIL THAT COVERS CALLERS WE DO NOT CONTROL, from DigitalOcean's own documentation
    (docs.digitalocean.com/products/inference/how-to/manage-model-access-keys, verified 2026-09-06):
      * a key can be scoped to SPECIFIC MODELS at creation -- an unscoped model is then refused by
        DO's gateway itself, for ANYONE holding the key;
      * a key can be restricted to a VPC -- "only requests originating from that VPC network can
        authenticate", so a stolen key is useless from outside the droplet's network;
      * "Legacy keys: keys created before model and VPC scoping were available. Legacy keys grant
        access to ALL foundation models and have NO VPC restriction. You cannot edit their scope."
    Our shared key (sha256:9327f186, seven containers) predates scoping. It is almost certainly a
    legacy key, i.e. an open wallet at DO's level and not just at our proxy. Our proxy allowlist
    protects one path; a scoped key protects every path, including ones we have never seen.

    DEFENSIVE ON SHAPE: the endpoint is newer than the billing API and its response fields are not
    documented here, so this prints what it finds and reads any field whose name suggests scope,
    rather than asserting a structure it has not observed. A lookup that fails is REPORTED.
    """
    if not token:
        return {"error": "DO_API_TOKEN not set - cannot read the account's model access keys"}
    try:
        d = _do_get("/gen-ai/models/api_keys", token)
    except Exception as e:
        return {"error": "model keys lookup failed: %s" % _http_reason(e)}
    keys = d.get("api_keys") or d.get("keys") or d.get("data") or []
    if isinstance(keys, dict):
        keys = list(keys.values())
    out = {"count": len(keys), "keys": []}
    for k in keys if isinstance(keys, list) else []:
        if not isinstance(k, dict):
            continue
        scope_fields = {kk: vv for kk, vv in k.items()
                        if any(t in kk.lower() for t in ("model", "scope", "vpc", "router", "batch"))}
        out["keys"].append({"name": k.get("name") or k.get("api_key_name") or "?",
                            "created": k.get("created_at") or k.get("created") or "?",
                            "scope": scope_fields or "(no scope-shaped field returned)"})
    return out


def render_key_audit(k):
    print()
    print("  MODEL ACCESS KEYS ON THE ACCOUNT (the guardrail at DigitalOcean's level)")
    if k.get("error"):
        print("    [!] %s" % k["error"])
    else:
        print("    %d key(s)" % k.get("count", 0))
        for x in k.get("keys", []):
            print("    - %-28s created %s" % (str(x["name"])[:28], str(x["created"])[:19]))
            print("        scope: %s" % json.dumps(x["scope"], default=str)[:160])
    print()
    print("    DO's docs: a LEGACY key (created before scoping) reaches ALL models with NO VPC")
    print("    restriction and its scope cannot be edited - only replaced. Recommended end state:")
    print("      * ONE key PER PROJECT, scoped to exactly the models that project uses;")
    print("      * VPC-restricted to the droplet's network, so a leaked key is useless elsewhere;")
    print("      * the old shared key REGENERATED once every project holds its own.")
    print("    That makes deepseek-v4-pro impossible for anyone holding a project key, and makes")
    print("    the next invoice attributable per project. Neither is possible from code.")


def render_whodunit(w):
    print()
    print("=" * 78)
    print("WHO IS SPENDING ON THE SHARED DIGITALOCEAN KEY")
    print("=" * 78)
    print("  window: last %s days" % w.get("days"))
    for proj, n in sorted((w.get("visible") or {}).items()):
        print("  %-14s %s" % (proj, ("%d log lines in Loki" % n) if n else
                              "0 log lines in Loki"))
    fe = w.get("file") or {}
    if fe:
        def _d(ts):
            return (datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
                    .strftime("%Y-%m-%d %H:%M UTC")) if ts else "-"
        print()
        print("  RAW events.log ON THE DROPLET (the primary source; Loki is an index over it)")
        print("    file          : %s" % (fe.get("file") or "?"))
        print("    jhw-web mount : %s" % (fe.get("mount") or "NONE"))
        print("    jhw-web env   : %s" % (", ".join(fe.get("env") or []) or "(no EVENTS_LOG / SERVICE)"))
        print("    jhw-web lines : %d   first %s   last %s" % (
            int(fe.get("jhw_lines") or 0), _d(fe.get("jhw_first_ts")), _d(fe.get("jhw_last_ts"))))
        if fe.get("per_day"):
            print("    proxy hits per day (evt=http on /v1/chat/completions):")
            for day, n in sorted(fe["per_day"].items()):
                print("      %s  %d" % (day, n))
    if w.get("note"):
        print("  note: %s" % w["note"])
    def _dt(ts):
        return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%m-%d %H:%M")
    print()
    print("  THE MODEL NAMES, SEARCHED AS SUBSTRINGS IN EVERY STREAM LOKI HOLDS")
    for x in w.get("samples") or []:
        if x.get("error"):
            print("    %-52s query failed: %s" % (x["title"][:52], x["error"][:80])); continue
        ls = x.get("lines") or []
        print("    %-52s %d line(s)" % (x["title"][:52], len(ls)))
        for ts, who, line in ls[-8:]:
            print("      %s  %-22s %s" % (_dt(ts), who[:22], line.replace("\n", " ")[:150]))
    print()
    print("  PER HOUR (UTC) - line these up against DO Insights by the clock")
    for x in w.get("hourly") or []:
        if x.get("error"):
            print("    %-52s query failed" % x["title"][:52]); continue
        rows = x.get("rows") or []
        print("    %s" % x["title"])
        if not rows:
            print("      (no hour with a hit)")
        for r in rows:
            pts = ["%s=%d" % (_dt(t), v) for t, v in r["points"]]
            print("      %-22s %s" % (r["who"][:22], " ".join(pts)[:200]))
    print()
    print("  calls to the jobhuntwow LLM proxy: %d" % w.get("proxy_hits", 0))
    for s in w.get("proxy_sources") or []:
        print("      %-40s %d" % (s["ip"], s["hits"]))
    if fe.get("proxy"):
        print("    last proxy hits (UTC, ip, status, path):")
        for p in fe["proxy"][-12:]:
            print("      %s  %-18s %-4s %s" % (_d(p["ts"]), p["ip"], p["status"], p["path"]))
    print()
    print("  VERDICT: %s" % w.get("verdict"))
    print()
    for line in _wrap(w.get("action") or "", 74):
        print("    " + line)
    print()


def _wrap(text, width):
    words, line, out = str(text).split(), "", []
    for wd in words:
        if len(line) + len(wd) + 1 > width:
            out.append(line); line = wd
        else:
            line = (line + " " + wd).strip()
    if line:
        out.append(line)
    return out


def main():
    if "--whodunit" in sys.argv:
        days = 10
        if "--days" in sys.argv:
            i = sys.argv.index("--days")
            if len(sys.argv) > i + 1:
                try:
                    days = max(1, min(60, int(sys.argv[i + 1])))
                except ValueError:
                    pass
        w = whodunit(os.environ.get("DROPLET_HOST", "64.225.108.200"), days=days)
        w["keys"] = key_audit(_do_token())
        if "--json" in sys.argv:
            print(json.dumps(w, indent=2, default=str))
        else:
            render_whodunit(w)
            render_key_audit(w["keys"])
        return

    if "--correlate" in sys.argv:
        days = 10
        if "--days" in sys.argv:
            i = sys.argv.index("--days")
            if len(sys.argv) > i + 1:
                try:
                    days = max(1, min(60, int(sys.argv[i + 1])))
                except ValueError:
                    pass
        host = os.environ.get("DROPLET_HOST", "64.225.108.200")
        c = loki_correlate(host, days=days)
        if "--json" in sys.argv:
            print(json.dumps(c, indent=2, default=str))
        else:
            render_correlate(c, days)
        return

    if "--trace" in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        roots = [here] + [p for p in (os.environ.get("TRACE_ROOTS", "").split(os.pathsep)) if p]
        # The sibling projects live beside this one on the operator's machine and are the most
        # likely local suspects, so they are scanned without being asked for.
        for sib in ("jobhuntwow-app", os.path.join(os.path.dirname(here), "Vendor SDWAN OSINT")):
            p = sib if os.path.isabs(sib) else os.path.join(here, sib)
            if os.path.isdir(p) and p not in roots:
                roots.append(p)
        tok = _do_token()
        render_trace(trace_remote(os.environ.get("DROPLET_HOST", "64.225.108.200"), "production"),
                     trace_remote(os.environ.get("STAGING_HOST", "165.245.244.174"), "staging"),
                     trace_local(roots),
                     do_agents(tok) if tok else None)
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
