#!/usr/bin/env python3
"""
check_bot_gate.py — prove the bot-404 gate on cybergod.ai actually behaves.

Pretends to be a browser, then a series of crawlers/scanners/tools, and reports what each one gets
on the WEBSITE and on the API.

    python check_bot_gate.py                 # test the live site
    python check_bot_gate.py --host localhost:8000 --insecure --http
    python check_bot_gate.py --json          # machine-readable

WHAT "CORRECT" LOOKS LIKE
    browser  ->  /          200   real people must always get in
    bot      ->  /          404   crawlers are turned away
    anything ->  /api/me    401   the API is EXEMPT from the gate on purpose

Why /api/me must stay 401: ship.py, deploy_web_direct.py and web-deploy.yml all prove a deploy
landed by fetching /api/me and asserting 401 — and they do it with curl/urllib, whose user agents
classify as bots. If the gate covered the API, every deploy would report itself broken.

Called by ship.py during VERIFY. A human being served 404 is a hard failure (the site is down for
real users). Bots NOT being blocked is a warning only, since BOT_404=0 is a legitimate choice.
"""
import argparse, json, ssl, sys, urllib.error, urllib.request

BROWSER = ("browser (Chrome)",
           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
           "Chrome/120.0.0.0 Safari/537.36")
PHONE   = ("browser (iPhone)",
           "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
           "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
BOTS = [
    ("Googlebot",        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("Bingbot",          "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),
    ("GPTBot",           "Mozilla/5.0 (compatible; GPTBot/1.0; +https://openai.com/gptbot)"),
    ("AhrefsBot",        "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)"),
    ("Censys scanner",   "Mozilla/5.0 (compatible; CensysInspect/1.1)"),
    ("nuclei",           "Nuclei - Open-source project (github.com/projectdiscovery/nuclei)"),
    ("sqlmap",           "sqlmap/1.8#stable (https://sqlmap.org)"),
    ("curl",             "curl/8.5.0"),
    ("python-requests",  "python-requests/2.32.3"),
    ("empty user-agent", ""),
]


def fetch(url, ua, insecure=False, timeout=15):
    """-> HTTP status code, or 0 on a transport error."""
    req = urllib.request.Request(url)
    if ua:
        req.add_header("User-Agent", ua)
    else:
        # urllib always sends one; strip it to simulate a UA-less client
        req.add_header("User-Agent", "")
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def run(host="cybergod.ai", scheme="https", insecure=False, quiet=False):
    base = "%s://%s" % (scheme, host)
    page, api = base + "/", base + "/api/me"
    rows, fails, warns = [], [], []

    def line(label, page_code, api_code, verdict):
        rows.append({"client": label, "page": page_code, "api": api_code, "verdict": verdict})
        if not quiet:
            print("  %-20s /  %-14s /api/me  %-10s %s"
                  % (label, page_code or "no answer", api_code or "no answer", verdict))

    if not quiet:
        print("\n  bot-404 gate  ->  %s" % base)
        print("  " + "-" * 68)

    for label, ua in (BROWSER, PHONE):
        p, a = fetch(page, ua, insecure), fetch(api, ua, insecure)
        ok = (p == 200)
        if not ok:
            fails.append("%s got %s on / (real users are being blocked)" % (label, p))
        line(label, p, a, "OK — served" if ok else "FAIL — humans blocked!")

    blocked = 0
    for label, ua in BOTS:
        p, a = fetch(page, ua, insecure), fetch(api, ua, insecure)
        if p == 404:
            blocked += 1
            verdict = "OK — 404"
        elif p == 0:
            verdict = "no answer"
        else:
            verdict = "not blocked (%s)" % p
        if a not in (401, 0):
            fails.append("/api/me returned %s for %s — expected 401; the deploy verifiers rely on it"
                         % (a, label))
        line(label, p, a, verdict)

    if blocked == 0:
        warns.append("no bot was served a 404 — is BOT_404=0, or is the new code not deployed yet?")
    elif blocked < len(BOTS):
        warns.append("%d/%d bots blocked — the rest may be in BOT_404_ALLOW" % (blocked, len(BOTS)))

    if not quiet:
        print("  " + "-" * 68)
        print("  bots blocked: %d/%d   humans served: yes" % (blocked, len(BOTS))
              if not fails else "  bots blocked: %d/%d" % (blocked, len(BOTS)))
        for w in warns:
            print("  [!] " + w)
        for f in fails:
            print("  [X] " + f)
        print("  %s\n" % ("RESULT: PASS" if not fails else "RESULT: FAIL"))
    return {"rows": rows, "blocked": blocked, "of": len(BOTS), "warnings": warns, "failures": fails}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="cybergod.ai")
    ap.add_argument("--http", action="store_true", help="use http:// instead of https://")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = run(a.host, "http" if a.http else "https", a.insecure, quiet=a.json)
    if a.json:
        print(json.dumps(res, indent=2))
    sys.exit(1 if res["failures"] else 0)


if __name__ == "__main__":
    main()
