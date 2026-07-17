#!/usr/bin/env python3
"""
cloudflare_setup.py — configure the cybergod.ai zone from code, not from clicks. Idempotent.

WHAT IT DOES (after you have created the account and moved the nameservers):
  1. finds the zone + reports whether the nameservers have actually moved
  2. A @ and www -> the droplet, PROXIED (orange cloud)
  3. SSL/TLS mode -> Full (strict)   [Caddy already serves a real Let's Encrypt cert]
  4. Always Use HTTPS + TLS 1.2 minimum
  5. one WAF custom rule that blocks the scanner paths from your daily digest
     (.php, /wp-, /.env, /.git, /phpmyadmin, /vendor/, xmlrpc, /.aws ...)
  6. verifies: prints the resulting records, settings and rule

WHAT IT CANNOT DO (and no script can):
  * create the Cloudflare account — that is your identity
  * move the nameservers at GoDaddy — only the domain owner can. That is the one human step.

TOKEN (scoped, least privilege) — https://dash.cloudflare.com/profile/api-tokens -> Create Token
-> Custom token, permissions:
       Zone : DNS            : Edit
       Zone : Zone Settings  : Edit
       Zone : Zone WAF       : Edit
       Zone : Zone           : Read
   Zone Resources: Include -> Specific zone -> cybergod.ai
Store it like every other secret (never in git):
       python set_secret.py CF_API_TOKEN      # or: set CF_API_TOKEN=... just for this shell

    python cloudflare_setup.py --dry-run     # show every change without making it
    python cloudflare_setup.py --apply
"""
import argparse, json, os, sys, urllib.error, urllib.request

API   = "https://api.cloudflare.com/client/v4"
ZONE  = os.environ.get("CF_ZONE", "cybergod.ai")
TOKEN = os.environ.get("CF_API_TOKEN", "")
ORIGIN = os.environ.get("DROPLET_HOST", "64.225.108.200")

# The exact paths your scanners hunt (from the attacker digest). Nothing legitimate on cybergod.ai
# ends in .php or lives under /wp- — blocking them costs you nothing and drops the whole digest.
BLOCK_EXPR = (
    '(http.request.uri.path contains "/wp-") or '
    '(http.request.uri.path contains "/wordpress") or '
    '(ends_with(http.request.uri.path, ".php")) or '
    '(http.request.uri.path contains "/.env") or '
    '(http.request.uri.path contains "/.git") or '
    '(http.request.uri.path contains "/.aws") or '
    '(http.request.uri.path contains "/phpmyadmin") or '
    '(http.request.uri.path contains "/vendor/") or '
    '(http.request.uri.path contains "/xmlrpc") or '
    '(http.request.uri.path contains "/cgi-bin") or '
    '(http.request.uri.path contains "/adminer") or '
    '(http.request.uri.path contains "/actuator")'
)
RULE_DESC = "colt: block commodity scanner paths (managed by cloudflare_setup.py)"


def api(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=(json.dumps(body).encode() if body is not None else None),
                                 headers={"Authorization": "Bearer " + TOKEN,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"success": False, "errors": [{"message": "HTTP %d" % e.code}]}


def need(res, what):
    if not res.get("success"):
        msgs = "; ".join(x.get("message", "?") for x in (res.get("errors") or []))
        sys.exit("[X] %s failed: %s" % (what, msgs or res))
    return res["result"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="make the changes (default is dry-run)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    apply = a.apply and not a.dry_run
    if not TOKEN:
        sys.exit("[X] CF_API_TOKEN not set.\n"
                 "    Create a scoped token (see the docstring), then:\n"
                 "      PowerShell:  $env:CF_API_TOKEN=\"...\"; python cloudflare_setup.py --dry-run")

    print("=" * 74)
    print("  Cloudflare setup for %s  ->  origin %s   [%s]"
          % (ZONE, ORIGIN, "APPLY" if apply else "DRY-RUN"))
    print("=" * 74)

    zones = need(api("GET", "/zones?name=" + ZONE), "zone lookup")
    if not zones:
        sys.exit("[X] zone %s not found on this account. Add the site in the Cloudflare dashboard "
                 "first (that part needs a human)." % ZONE)
    z = zones[0]; zid = z["id"]
    print("  zone id     : %s" % zid)
    print("  status      : %s   %s" % (z["status"],
          "<- nameservers NOT moved yet at GoDaddy" if z["status"] != "active" else "(nameservers moved)"))
    print("  cloudflare NS: %s" % ", ".join(z.get("name_servers") or []))
    if z["status"] != "active":
        print("\n  Until GoDaddy points at those nameservers, nothing below takes effect.")

    # ---- 1. DNS: A @ / www -> droplet, proxied
    print("\n-- DNS --")
    recs = need(api("GET", "/zones/%s/dns_records?type=A" % zid), "dns list")
    have = {r["name"]: r for r in recs}
    for name in (ZONE, "www." + ZONE):
        want = {"type": "A", "name": name, "content": ORIGIN, "proxied": True, "ttl": 1}
        cur = have.get(name)
        if cur and cur["content"] == ORIGIN and cur.get("proxied"):
            print("   = %-18s %s proxied — already correct" % (name, ORIGIN)); continue
        if cur:
            print("   ~ %-18s %s(proxied=%s) -> %s(proxied=True)"
                  % (name, cur["content"], cur.get("proxied"), ORIGIN))
            if apply: need(api("PUT", "/zones/%s/dns_records/%s" % (zid, cur["id"]), want), "dns update")
        else:
            print("   + %-18s %s proxied" % (name, ORIGIN))
            if apply: need(api("POST", "/zones/%s/dns_records" % zid, want), "dns create")

    # ---- 2. TLS + HTTPS settings
    print("\n-- TLS --")
    for key, val, why in (("ssl", "strict", "Full (strict) — Caddy has a real LE cert"),
                          ("always_use_https", "on", "redirect http->https at the edge"),
                          ("min_tls_version", "1.2", "drop TLS 1.0/1.1")):
        cur = api("GET", "/zones/%s/settings/%s" % (zid, key)).get("result", {}).get("value")
        if str(cur) == val:
            print("   = %-18s %s — already set" % (key, val)); continue
        print("   ~ %-18s %s -> %s   (%s)" % (key, cur, val, why))
        if apply: need(api("PATCH", "/zones/%s/settings/%s" % (zid, key), {"value": val}), key)

    # ---- 3. WAF custom rule: block the scanner paths
    print("\n-- WAF custom rule --")
    ep = api("GET", "/zones/%s/rulesets/phases/http_request_firewall_custom/entrypoint" % zid)
    rules = (ep.get("result") or {}).get("rules") or [] if ep.get("success") else []
    mine = [r for r in rules if r.get("description") == RULE_DESC]
    others = [r for r in rules if r.get("description") != RULE_DESC]
    new_rule = {"action": "block", "expression": BLOCK_EXPR, "description": RULE_DESC, "enabled": True}
    if mine and mine[0].get("expression") == BLOCK_EXPR:
        print("   = rule already present and identical")
    else:
        print("   %s block rule: /wp-  .php  /.env  /.git  /phpmyadmin  /vendor/  xmlrpc ..."
              % ("~ updating" if mine else "+ adding"))
        print("     (this one rule drops every IP in today's attacker digest)")
        if apply:
            body = {"rules": others + [new_rule]}
            need(api("PUT", "/zones/%s/rulesets/phases/http_request_firewall_custom/entrypoint" % zid,
                     body), "waf rule")

    print("\n" + "=" * 74)
    if not apply:
        print("  DRY-RUN — nothing changed. Re-run with --apply to make it so.")
    else:
        print("  Applied. Verify:  curl -I https://%s/wp-login.php   -> expect 403 from Cloudflare" % ZONE)
        print("  Real client IPs keep working: telemetry reads CF-Connecting-IP; country <- CF-IPCountry.")
    print("  NOT touched: Amnezia VPN (UDP) and SSH bypass Cloudflare entirely — by design.")


if __name__ == "__main__":
    main()
