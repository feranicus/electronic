#!/usr/bin/env python3
"""incident_report.py -- forensics for the jobhuntwow open-endpoint incident (2026-09-01 .. 09-06).

    python incident_report.py                 # last 30 days, writes incident-<stamp>.md
    python incident_report.py --days 14
    python incident_report.py --json          # machine-readable

WHAT HAPPENED (established 2026-09-06, see CLAUDE.md "FOUND: jobhuntwow's /api/chat WAS A PUBLIC,
UNAUTHENTICATED LLM ENDPOINT"): jobhuntwow exposed, with no login, `GET /api/models` (DigitalOcean's
whole catalogue), `POST /api/chat` (any model, streamed on our key), and the entire
`/api/electronic/*` tree (any user's tailored CV/cover letter by naming their email; the
four-model tailor on our key). This tool answers, from evidence that already exists:

  HOW MANY TIMES, WHEN, FROM WHERE  - every hit on those routes, per address, per day, per hour,
                                      from jhw-web's docker stdout (videodead-promtail -> Loki,
                                      30-day retention). Loki holds the ONLY copy of Sep 1-5:
                                      the container was recreated on Sep 6 and jhw never wrote
                                      to the shared events.log (UID 10001 vs a root 0644 file).
  WHAT IT WAS USED FOR              - the model, the token counts and the cost per call, for
                                      every call since the meter shipped (06 Sep 09:xx UTC).
                                      Before that: model + duration only. PROMPTS WERE NEVER
                                      LOGGED and cannot be recovered; the tool says so.
  WHO                               - `user` on every http line (empty = no session, which was
                                      the point), the users table (signups, verified, last
                                      login), and every auth event with its address.
  WHAT ELSE THEY COULD REACH        - the public surface as it stood, and whether any
                                      non-owner address touched /api/electronic (that is the
                                      personal-data question, GDPR Art. 33/34).
  WHOM TO TELL                      - RDAP abuse contact per address, and a ready-to-send
                                      abuse complaint with UTC timestamps.

READ-ONLY. One ssh session (recover.ssh_script), Loki via wget inside the loki container, the
users table read with sqlite3 inside jhw-web. Nothing on the droplet is modified. The output file
is gitignored: it contains addresses, emails and paths that must not be committed.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROUTES = [                      # (family, substring filter) -- the surface that was public
    ("chat",        "/api/chat"),
    ("models",      "/api/models"),
    ("electronic",  "/api/electronic"),
    ("proxy",       "/v1/chat/completions"),
    ("proxy_models", "/v1/models"),
    ("connections", "/api/connections"),
    ("scout_apply", "/api/scout"),
    ("auth",        "/api/auth/"),
]
LIMIT = 5000                    # Loki's default per-query cap; a family at the cap is flagged


def _enc(q):
    for a, b in (("%", "%25"), ("\\", "%5C"), ("{", "%7B"), ("}", "%7D"), ('"', "%22"),
                 (" ", "%20"), ("|", "%7C"), ("(", "%28"), (")", "%29"), ("[", "%5B"),
                 ("]", "%5D"), ("=", "%3D"), ("+", "%2B"), ("&", "%26")):
        q = q.replace(a, b)
    return q


def _script(start, end):
    b = ["L=$(docker ps --format '{{.Names}}' | grep -iE 'loki' | head -1)",
         'echo "#### LOKI"; echo "${L:-NONE}"',
         "s(){ [ -n \"$L\" ] && docker exec \"$L\" wget -qO- \"http://127.0.0.1:3100/loki/api/v1/"
         "query_range?query=$1&start=%s&end=%s&limit=%d&direction=backward\" 2>/dev/null; }"
         % (start, end, LIMIT)]
    for fam, sub in ROUTES:
        q = '{container=~".*jhw-web.*"} |= "%s" |= "\\"evt\\": \\"http\\""' % sub
        b.append('echo; echo "#### R_%s"; s "%s"' % (fam, _enc(q)))
    b.append('echo; echo "#### LLM"; s "%s"' % _enc('{container=~".*jhw-web.*"} |= "\\"evt\\": \\"llm_call\\""'))
    b.append('echo; echo "#### AUTH"; s "%s"' % _enc('{container=~".*jhw-web.*"} |= "\\"evt\\": \\"auth\\""'))
    b.append('echo; echo "#### PROXYLOG"; s "%s"' % _enc('{container=~".*jhw-web.*"} |= "[proxy]"'))
    b.append('echo; echo "#### USERS"; docker exec jhw-web python3 -c "'
             "import sqlite3,os,json;p=os.path.join(os.environ.get('DATA_DIR','/data'),'users.sqlite');"
             "c=sqlite3.connect(p);print(json.dumps([dict(zip(['email','created_at','verified_at',"
             "'last_login'],r)) for r in c.execute('select email,created_at,verified_at,last_login "
             "from users order by created_at')]))\" 2>&1")
    b.append('echo; echo "#### CONTAINER"; docker inspect jhw-web -f \'{{.State.StartedAt}} {{.Config.Image}}\' 2>&1')
    return "\n".join(b) + "\n"


def _lines(raw):
    out = []
    try:
        for st in json.loads(raw or "{}").get("data", {}).get("result", []):
            for ts, line in st.get("values") or []:
                out.append((int(ts) // 10**9, line))
    except Exception:
        return None
    out.sort()
    return out


def _j(line):
    try:
        return json.loads(line)
    except Exception:
        return None


def _utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def rdap_abuse(ip, timeout=8):
    """Abuse contact for an address from the RDAP bootstrap. Best-effort; a failure is reported."""
    try:
        with urllib.request.urlopen("https://rdap.org/ip/%s" % ip, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"error": repr(e)[:100]}
    holder = d.get("name") or ""
    emails, org = [], ""
    def walk(ents):
        nonlocal org
        for e in ents or []:
            roles = e.get("roles") or []
            v = e.get("vcardArray") or [None, []]
            for item in (v[1] if isinstance(v, list) and len(v) > 1 else []):
                if item[0] == "email" and "abuse" in roles:
                    emails.append(item[3])
                if item[0] == "fn" and not org and ("registrant" in roles or "administrative" in roles):
                    org = item[3]
            walk(e.get("entities"))
    walk(d.get("entities"))
    return {"holder": holder, "org": org, "abuse": sorted(set(emails)),
            "cidr": ",".join("%s-%s" % (c.get("startAddress", ""), c.get("endAddress", ""))
                             for c in [d]) if d.get("startAddress") else ""}


def collect(host, days):
    from recover import ssh_script, sections
    import recover as _rc
    prev = _rc.HOST; _rc.HOST = host
    try:
        end = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        start = end - days * 86400
        out, err, rc = ssh_script(_script(start, end), timeout=300)
    finally:
        _rc.HOST = prev
    if rc != 0 and not out:
        return {"error": "ssh failed rc=%s: %s" % (rc, (err or "")[:200])}
    sec = sections(out or "")
    res = {"loki": (sec.get("LOKI") or "").strip(), "days": days, "families": {}, "truncated": [],
           "llm": [], "auth": [], "proxylog": [], "users": None, "container": (sec.get("CONTAINER") or "").strip()}
    for fam, _ in ROUTES:
        ls = _lines(sec.get("R_%s" % fam))
        if ls is None:
            res["families"][fam] = {"error": (sec.get("R_%s" % fam) or "")[:120] or "no answer"}; continue
        if len(ls) >= LIMIT:
            res["truncated"].append(fam)
        res["families"][fam] = {"hits": [(ts, _j(l)) for ts, l in ls if _j(l)]}
    for key, name in (("LLM", "llm"), ("AUTH", "auth")):
        ls = _lines(sec.get(key)) or []
        res[name] = [(ts, _j(l)) for ts, l in ls if _j(l)]
    res["proxylog"] = [(ts, l) for ts, l in (_lines(sec.get("PROXYLOG")) or [])]
    try:
        res["users"] = json.loads((sec.get("USERS") or "").strip())
    except Exception:
        res["users"] = {"error": (sec.get("USERS") or "")[:200]}
    return res


def analyse(res):
    per_ip = {}
    def acc(ip, fam, ts, d):
        p = per_ip.setdefault(ip, {"first": ts, "last": ts, "fams": {}, "users": set(), "ua": set(),
                                   "days": {}, "status": {}})
        p["first"] = min(p["first"], ts); p["last"] = max(p["last"], ts)
        p["fams"][fam] = p["fams"].get(fam, 0) + 1
        if d.get("user"): p["users"].add(d["user"])
        if d.get("ua"): p["ua"].add(str(d["ua"])[:80])
        day = _utc(ts)[:10]; p["days"][day] = p["days"].get(day, 0) + 1
        st = str(d.get("status")); p["status"][st] = p["status"].get(st, 0) + 1
    for fam, v in res["families"].items():
        for ts, d in v.get("hits") or []:
            acc(str(d.get("ip") or "?"), fam, ts, d)
    # hourly for the two doors that spent money
    hourly = {}
    for fam in ("chat", "proxy", "electronic"):
        for ts, d in (res["families"].get(fam) or {}).get("hits") or []:
            h = _utc(ts)[:13]; hourly.setdefault(h, {}); hourly[h][fam] = hourly[h].get(fam, 0) + 1
    # llm calls: model -> tokens/cost, and per user
    models, by_user = {}, {}
    for ts, d in res["llm"]:
        m = str(d.get("model")); k = models.setdefault(m, {"calls": 0, "tin": 0, "tout": 0, "usd": 0.0,
                                                          "first": ts, "last": ts, "callers": set()})
        k["calls"] += 1; k["tin"] += int(d.get("tokens_in") or 0); k["tout"] += int(d.get("tokens_out") or 0)
        k["usd"] += float(d.get("cost_usd") or 0); k["first"] = min(k["first"], ts); k["last"] = max(k["last"], ts)
        k["callers"].add(str(d.get("caller")))
        u = str(d.get("user") or "(none)"); by_user[u] = by_user.get(u, 0) + 1
    owners = {u["email"] for u in res["users"] or [] if isinstance(u, dict) and u.get("email")}
    # personal-data question: /api/electronic reached by an address with NO session
    pd_hits = [(ts, d) for ts, d in (res["families"].get("electronic") or {}).get("hits") or []
               if not d.get("user")]
    return {"per_ip": per_ip, "hourly": hourly, "models": models, "by_user": by_user,
            "owners": owners, "electronic_anonymous": pd_hits}


def render(res, an, abuse):
    L = []
    P = L.append
    P("# jobhuntwow.com incident report - public LLM and profile endpoints")
    P("")
    P("Generated %s from Loki (%s), window %d days. Container: %s" % (
        _utc(int(datetime.datetime.now(datetime.timezone.utc).timestamp())), res["loki"], res["days"], res["container"]))
    P("")
    P("## 1. What was exposed")
    P("")
    P("Until 2026-09-06 the following jobhuntwow.com routes required NO login:")
    P("`GET /api/models` (DigitalOcean's full model catalogue), `POST /api/chat` (any model, streamed on")
    P("our DigitalOcean key), `GET/POST /api/connections`, `POST /api/scout`, `POST /api/apply`, and the")
    P("whole `/api/electronic/*` tree, which listed and served any user's generated CV and cover letter")
    P("by naming their email in a query parameter, and ran the four-model tailor on our key.")
    P("No registration was needed and none was bypassed: the doors had no lock. The proxy at")
    P("`/v1/chat/completions` required a bearer token throughout.")
    P("")
    P("Prompts and completions were never logged. What follows is who called what, when, how often,")
    P("with which model, and (since the meter shipped on 2026-09-06) how many tokens it cost.")
    if res["truncated"]:
        P("")
        P("WARNING: these families hit Loki's %d-line cap and are UNDER-COUNTED: %s" % (LIMIT, ", ".join(res["truncated"])))
    P("")
    P("## 2. Every address that touched the exposed routes")
    P("")
    P("| address | first seen | last seen | chat | models | electronic | proxy | auth | users seen | statuses |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for ip, p in sorted(an["per_ip"].items(), key=lambda kv: -sum(kv[1]["fams"].values())):
        f = p["fams"]
        P("| %s | %s | %s | %d | %d | %d | %d | %d | %s | %s |" % (
            ip, _utc(p["first"]), _utc(p["last"]), f.get("chat", 0), f.get("models", 0),
            f.get("electronic", 0), f.get("proxy", 0) + f.get("proxy_models", 0), f.get("auth", 0),
            ", ".join(sorted(p["users"])) or "(no session)",
            " ".join("%s:%d" % kv for kv in sorted(p["status"].items()))))
    P("")
    P("### 2a. Per day, per address (chat + electronic + proxy)")
    P("")
    for ip, p in sorted(an["per_ip"].items(), key=lambda kv: -sum(kv[1]["fams"].values())):
        if not any(k in p["fams"] for k in ("chat", "electronic", "proxy")):
            continue
        P("- %s: %s" % (ip, "  ".join("%s=%d" % kv for kv in sorted(p["days"].items()))))
        for ua in sorted(p["ua"])[:5]:
            P("    ua: %s" % ua)
    P("")
    P("### 2b. Per hour (UTC) - line up against DigitalOcean Insights")
    P("")
    for h, fams in sorted(an["hourly"].items()):
        P("- %s  %s" % (h, "  ".join("%s=%d" % kv for kv in sorted(fams.items()))))
    P("")
    P("## 3. What it was used for (metered calls, since 2026-09-06)")
    P("")
    P("| model | calls | tokens in | tokens out | USD (our pricing table) | first | last | callers |")
    P("|---|---|---|---|---|---|---|---|")
    for m, k in sorted(an["models"].items(), key=lambda kv: -kv[1]["usd"]):
        P("| %s | %d | %d | %d | %.4f | %s | %s | %s |" % (
            m, k["calls"], k["tin"], k["tout"], k["usd"], _utc(k["first"]), _utc(k["last"]), ", ".join(sorted(k["callers"]))))
    P("")
    P("Calls by session user: %s" % (", ".join("%s=%d" % kv for kv in sorted(an["by_user"].items())) or "none"))
    P("")
    P("Before 2026-09-06 no token counts exist anywhere we control. The Sep 1 and Sep 3 volumes are")
    P("in DigitalOcean's Insights page (operator screenshots: 318K/518K input tokens on Sep 1 11:57,")
    P("~1.1M input on Sep 3 07:00-18:00) and on the invoice; those are the authoritative numbers.")
    P("")
    P("## 3b. WHAT IT COST -- estimate, with its bounds stated")
    P("")
    mt_calls = sum(k["calls"] for k in an["models"].values())
    mt_in = sum(k["tin"] for k in an["models"].values())
    mt_out = sum(k["tout"] for k in an["models"].values())
    mt_usd = sum(k["usd"] for k in an["models"].values())
    chat_all = sum(p.get("fams", {}).get("chat", 0) for p in an["per_ip"].values())
    ok200 = sum(n for p in an["per_ip"].values() for st, n in p.get("status", {}).items()
                if st == "200") if chat_all else 0
    if mt_calls and chat_all:
        per = mt_usd / mt_calls
        est = chat_all * per
        P("MEASURED (the metered window only, %d call(s)): %d tokens in, %d tokens out, $%.4f."
          % (mt_calls, mt_in, mt_out, mt_usd))
        P("That is $%.5f and %.0f input tokens per call." % (per, mt_in / mt_calls))
        P("")
        P("EXTRAPOLATED over the %d chat request(s) in this window: **~$%.2f** (range $%.2f to $%.2f"
          % (chat_all, est, est * 0.5, est * 2))
        P("if the unobserved calls averaged half, or twice, the context of the measured ones).")
        P("Implied volume: ~%.1fM input tokens." % (chat_all * mt_in / mt_calls / 1e6))
        P("")
        P("THREE REASONS THIS IS NOT THE INVOICE, in the direction each pushes:")
        P("1. Both model ids are ABSENT from our price table, so `llm_events.rate_for()` charges")
        P("   them at the most expensive rate we know ($0.425 in / $1.36 out per 1M). If")
        P("   DigitalOcean prices a `-pro` model above that, the real figure is HIGHER. We cannot")
        P("   read DO's published rate from here; the invoice settles it.")
        P("2. Only calls inside the metered window carry token counts. Everything before")
        P("   2026-09-06 is extrapolated from request COUNTS, which assumes a similar context")
        P("   size per call. The operator's DO Insights screenshots (318K + 518K input tokens on")
        P("   1 Sep, ~1.1M on 3 Sep) are the check on that assumption.")
        P("3. Loki keeps 30 days. Anything older than this window is invisible and is NOT in the")
        P("   number above.")
        P("")
        P("THE AUTHORITATIVE NUMBER is DigitalOcean's own: Billing -> invoice line for Serverless")
        P("Inference, or the month-to-date balance delta. `python cost_report.py` prints the")
        P("reconciliation: what DO charged for AI, what our own meter accounts for, and the gap.")
        P("Our own legitimate usage in the same period is ~$0.005 per assessment (cost_ledger),")
        P("so essentially all of the AI line in this window is the unauthorised traffic.")
    else:
        P("Not estimable: no metered calls in the window, or no chat requests recorded.")
    P("")
    P("## 4. Accounts on the platform")
    P("")
    if isinstance(res["users"], list):
        P("| email | created | verified | last login |")
        P("|---|---|---|---|")
        for u in res["users"]:
            P("| %s | %s | %s | %s |" % (u.get("email"), _utc(u["created_at"]) if u.get("created_at") else "-",
                                       _utc(u["verified_at"]) if u.get("verified_at") else "NO",
                                       _utc(u["last_login"]) if u.get("last_login") else "-"))
    else:
        P("users table could not be read: %s" % res["users"])
    P("")
    P("Auth events in the window (signup/login/verify with the address that made them):")
    for ts, d in res["auth"][-60:]:
        P("- %s  %s %s %s  %s" % (_utc(ts), d.get("action"), d.get("result"), d.get("email"), d.get("ip") or ""))
    P("")
    P("## 5. Personal data: was anyone's profile reached without a session?")
    P("")
    hits = an["electronic_anonymous"]
    if hits:
        P("YES. %d request(s) to /api/electronic/* arrived with NO session. Each is listed; whether a" % len(hits))
        P("named user's files were served is decided by the path (jobs / artifacts) and the status:")
        for ts, d in hits[-200:]:
            P("- %s  %s  %s %s -> %s" % (_utc(ts), d.get("ip"), d.get("method"), d.get("path"), d.get("status")))
        P("")
        P("If any of those returned 200 on /jobs or /artifacts for an email that is not the caller's,")
        P("that is a personal data breach under GDPR Art. 4(12); Art. 33 requires notifying the")
        P("supervisory authority within 72 hours of becoming aware, and Art. 34 the affected person")
        P("if the risk is high. A CV with address and phone is high risk. Decide with counsel.")
    else:
        P("No request to /api/electronic/* without a session appears in the window. Note the window")
        P("is bounded by Loki's 30-day retention; nothing older can be established either way.")
    P("")
    P("## 6. Abuse contacts (RDAP) and complaint drafts")
    P("")
    for ip, info in abuse.items():
        p = an["per_ip"].get(ip) or {}
        P("### %s" % ip)
        if info.get("error"):
            P("RDAP lookup failed: %s" % info["error"]); P(""); continue
        P("holder: %s   org: %s   abuse: %s" % (info.get("holder"), info.get("org") or "-", ", ".join(info.get("abuse") or []) or "(none published)"))
        P("")
        P("```")
        P("To: %s" % (", ".join(info.get("abuse") or []) or "<abuse desk of the holder above>"))
        P("Subject: Abuse report - unauthorised use of an LLM API endpoint from %s" % ip)
        P("")
        P("The address %s, in your allocation %s, made %d requests to https://jobhuntwow.com" % (
            ip, info.get("holder") or "", sum(p.get("fams", {}).values())))
        P("between %s and %s, consuming paid inference on our DigitalOcean" % (_utc(p.get("first", 0)), _utc(p.get("last", 0))))
        P("account through an endpoint that was not intended for public use. Requests by day:")
        P("%s" % "  ".join("%s=%d" % kv for kv in sorted(p.get("days", {}).items())))
        P("Routes: %s" % ", ".join("%s=%d" % kv for kv in sorted(p.get("fams", {}).items())))
        P("Timestamps are UTC; full request lines with paths and status codes are available on request.")
        P("Please identify the customer responsible and act under your acceptable-use policy.")
        P("Operator: Cybergod LLC / S4Biz Group, feranicus@s4biz.io")
        P("```")
        P("")
    P("## 7. Legal framing, honestly")
    P("")
    P("- The routes had NO access control, so criminal provisions that require overcoming a security")
    P("  measure (StGB s.202a 'besonders gesichert', CFAA 'without authorisation' after Van Buren) are")
    P("  weak. The realistic channels are the hosting provider's abuse desk (AUP breach) and, if a")
    P("  user's CV was served to a stranger, the GDPR notification duty on US, not on them.")
    P("- Do not contact the address, scan it, or connect back. Hosting addresses are usually a rented")
    P("  droplet or a compromised third party.")
    P("- Keep this file and the Loki export: retention is 30 days and the Sep 1-5 evidence exists")
    P("  nowhere else. `python logship.py` archives cybergod's file; jhw's stdout is NOT archived.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--host", default=os.environ.get("DROPLET_HOST", "64.225.108.200"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-rdap", action="store_true")
    a = ap.parse_args()
    res = collect(a.host, a.days)
    if res.get("error"):
        print("[X] %s" % res["error"]); return 1
    an = analyse(res)
    abuse = {}
    if not a.no_rdap:
        for ip in sorted(an["per_ip"], key=lambda i: -sum(an["per_ip"][i]["fams"].values()))[:15]:
            if ip in ("?", "127.0.0.1") or ip.startswith(("10.", "172.", "192.168.")):
                continue
            abuse[ip] = rdap_abuse(ip)
    if a.json:
        def _d(o):
            if isinstance(o, set): return sorted(o)
            return str(o)
        print(json.dumps({"per_ip": an["per_ip"], "hourly": an["hourly"], "models": an["models"],
                          "users": res["users"], "abuse": abuse}, default=_d, indent=1)); return 0
    text = render(res, an, abuse)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(HERE, "incident-%s.md" % stamp)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    sys.stdout.reconfigure(errors="replace") if hasattr(sys.stdout, "reconfigure") else None
    print(text)
    print("written: %s   (gitignored - it holds addresses and emails)" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
