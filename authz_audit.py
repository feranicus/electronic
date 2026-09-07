#!/usr/bin/env python3
"""authz_audit.py -- does every route actually refuse an anonymous caller?

    python authz_audit.py                 # audit the LIVE sites over HTTPS
    python authz_audit.py --local         # audit cybergod's app in-process (every route, no network)
    python authz_audit.py --json

WHY THIS EXISTS. On 2026-09-06 jobhuntwow was found serving `POST /api/chat` (any model, on our
paid key), `GET /api/models` (the vendor's whole catalogue) and the entire `/api/electronic/*`
tree (any user's tailored CV by naming their email in a query parameter) to anyone on the
internet, with no session. Nobody bypassed a control; the routes never had one. The defect class
is OPT-IN AUTHORISATION: a framework where a route is public unless the author remembers to add a
guard will, eventually, ship a route where the author forgot. NIST SP 800-53 AC-3, CISA/NSA
Secure-by-Design ("secure by default"), OWASP API Security Top 10 API1 (Broken Object Level
Authorization) and API5 (Broken Function Level Authorization) all say the same thing: deny by
default, and prove it.

WHAT IT MEASURES. Not the source. The RESPONSE. A route is compliant when an anonymous request
gets 401/403 (or a redirect to a login). Anything else is listed as a finding with the status and
the first bytes of the body, because a 200 with an empty React shell and a 200 with somebody's CV
look identical in a status column.

It sends only GET and HEAD to live sites (a POST could create or spend), and full method coverage
only in --local mode, where the app runs in this process against a temporary data directory.

READ-ONLY against production. No credentials are used or needed: that is the point.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# A browser UA: cybergod's bot gate answers an unrecognised agent with 404 on page routes, which
# would make a broken app look like a locked one. (That blind spot let www.cybergod.ai report
# healthy while returning 404 for weeks -- CLAUDE.md, 2026-08-11.)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")

OK_STATUS = (401, 403)          # a refusal
REDIRECT = (301, 302, 303, 307, 308)

# The public surface of each site, declared. Everything else must refuse.
SITES = {
    "cybergod.ai": {
        # Public BY DESIGN, each for a stated reason: /api/me answers 401 to the anonymous (the
        # SPA calls it on every load); logout only clears a cookie; privacy/ack records the Art.13
        # notice acknowledgement, which happens BEFORE anyone logs in; demo/langs/jurisdictions
        # are capability lists with no customer data; siege is the anonymised attack feed.
        "public": ["/", "/api/me", "/api/demo", "/api/langs", "/api/jurisdictions", "/robots.txt",
                   "/sitemap.xml", "/.well-known/security.txt", "/api/siege",
                   "/api/auth/logout", "/api/privacy/ack", "/api/auth/begin", "/api/auth/verify"],
        "must_refuse": ["/api/history", "/api/diag", "/api/brand", "/api/brand/logo",
                        "/api/brand/preview", "/api/admin/users",
                        "/api/assess/1/status", "/api/assess/1/clarify",
                        "/api/assess/1/deck/x.pptx"],
    },
    "jobhuntwow.com": {
        "public": ["/", "/api/health", "/robots.txt"],
        "must_refuse": ["/api/models", "/api/me", "/api/connections", "/api/electronic/jobs",
                        "/api/electronic/jobs?email=victim@example.com",
                        "/api/electronic/artifacts/x", "/v1/models"],
    },
    "s4biz.io": {"public": ["/", "/api/health"], "must_refuse": ["/api/models", "/api/chat",
                                                                 "/api/admin", "/api/users"]},
    "klimaanlage-preise.de": {"public": ["/"], "must_refuse": ["/api/models", "/api/chat",
                                                               "/api/admin", "/api/users",
                                                               "/api/config", "/api/leads"]},
    "godeyes.ai": {"public": ["/"], "must_refuse": ["/api/models", "/api/chat", "/api/admin"]},
    "jev.best": {"public": ["/"], "must_refuse": ["/api/models", "/api/chat", "/api/admin",
                                                  "/api/users", "/api/config"]},
}

# Paths worth trying everywhere: an LLM passthrough, a config dump, a user list. These are the
# shapes that cost money or leak people, and they are cheap to ask for.
SWEEP = ["/api/models", "/api/chat", "/v1/models", "/v1/chat/completions", "/api/users",
         "/api/admin", "/api/config", "/api/connections", "/api/debug", "/api/status",
         "/openapi.json", "/docs", "/redoc"]


def fetch(url, method="GET", timeout=12):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            body = e.read(400)
        except Exception:
            body = b""
        return e.code, body, dict(e.headers or {})
    except Exception as e:
        return 0, repr(e)[:120].encode(), {}


def classify(path, status, body, declared_public):
    # REACHABILITY FIRST. A declared-public path that never reached the host is UNREACHABLE, not
    # "public-by-design": counting it as a successful probe is what turned a fully blind run into
    # "partially reachable" and then into a pass.
    if status == 0:
        return "unreachable", body.decode("utf-8", "replace")
    if path in declared_public:
        return "public-by-design", ""
    if status in OK_STATUS:
        return "refused", ""
    if status == 404:
        # 404 on an API path means the route does not exist -- or the bot gate hid it. Either way
        # nothing was served, so it is not a finding; it is also not proof the route is absent.
        return "not-present", ""
    if status in REDIRECT:
        return "redirect", ""
    if status == 0:
        return "unreachable", body.decode("utf-8", "replace")
    if status == 200:
        txt = body.decode("utf-8", "replace")
        low = txt.lower()
        # API DOCUMENTATION IS HTML, and the first version of this check filed FastAPI's live
        # Swagger UI as "spa-shell" because any HTML 200 was treated as the SPA fallback. /docs
        # and /redoc are exactly where an attacker reads the route list, so they are decided on
        # CONTENT: a swagger/redoc bundle is SERVED, a genuine SPA shell is not.
        if path in ("/docs", "/redoc"):
            if "swagger" in low or "redoc" in low or "openapi" in low:
                return "SERVED", "interactive API docs are live: " + txt[:120]
            return "spa-shell", ""
        # An SPA serves index.html for unknown paths: that is the shell, not data.
        if "<!doctype html" in low or "<html" in low:
            return "spa-shell", ""
        return "SERVED", txt[:200]
    if status == 422:
        # FastAPI validates the BODY before the handler runs, so an anonymous POST with a body
        # that does not match the schema gets 422 and never reaches the auth check. That is NOT
        # evidence either way. Send a schema-valid body to decide; the local suite does.
        return "inconclusive-422", "schema rejected the probe body; auth was never reached"
    return "other-%d" % status, body.decode("utf-8", "replace")[:120]


def audit_live(only=None):
    findings, rows = [], []
    for host, spec in SITES.items():
        if only and host not in only:
            continue
        paths = list(dict.fromkeys(spec["public"] + spec["must_refuse"] + SWEEP))
        for p in paths:
            url = "https://%s%s" % (host, p)
            st, body, _ = fetch(url)
            verdict, extra = classify(p, st, body, spec["public"])
            rows.append((host, p, st, verdict, extra))
            if verdict == "SERVED":
                findings.append((host, p, st, extra))
    return rows, findings


def audit_local():
    """Every route of cybergod's own app, all methods, in-process. No network, no data touched."""
    import tempfile
    os.environ.setdefault("COLT_DATA", tempfile.mkdtemp())
    os.environ.setdefault("SESSION_SECRET", "audit-only")
    sys.path.insert(0, os.path.join(HERE, "webapp", "backend"))
    import asyncio
    from app.main import app
    from fastapi.routing import APIRoute

    def call(method, path):
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": method, "scheme": "https", "path": path, "raw_path": path.encode(),
                 "query_string": b"", "headers": [(b"host", b"cybergod.ai"),
                                                  (b"user-agent", UA.encode()),
                                                  (b"content-type", b"application/json")],
                 "client": ("203.0.113.9", 1234), "server": ("cybergod.ai", 443)}
        out = {"status": None, "body": b""}
        sent = [False]

        async def receive():
            if sent[0]:
                await asyncio.sleep(3600)
            sent[0] = True
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(m):
            if m["type"] == "http.response.start":
                out["status"] = m["status"]
            elif m["type"] == "http.response.body":
                out["body"] += m.get("body", b"")
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(app(scope, receive, send))
        return out["status"], out["body"][:300]

    public = set(SITES["cybergod.ai"]["public"])
    rows, findings = [], []
    for r in app.routes:
        if not isinstance(r, APIRoute) or not r.path.startswith(("/api/", "/v1/")):
            continue
        path = (r.path.replace("{job_id}", "1").replace("{name}", "x.pptx")
                .replace("{email}", "a@b.c").replace("{job}", "1").replace("{full_path:path}", "x"))
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            st, body = call(m, path)
            verdict, extra = classify(r.path, st, body, public)
            rows.append(("cybergod-local", "%s %s" % (m, r.path), st, verdict, extra))
            if verdict in ("SERVED", "spa-shell") and r.path not in public:
                findings.append(("cybergod-local", "%s %s" % (m, r.path), st, extra))
    return rows, findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="in-process audit of cybergod's app")
    ap.add_argument("--site", action="append", help="limit to these hosts")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows, findings = audit_local() if a.local else audit_live(a.site)
    # BLIND IS NOT CLEAN. Every probe from a sandboxed/proxied network returns 0/unreachable, and
    # the first version of this tool then printed "[OK] no route served content" -- a false pass
    # built on a run that never reached its subject. Same defect class as the whodunit that read
    # BLIND as innocence. Count what was actually reached, per host, and refuse to conclude.
    blind = {}
    for host, p_, st, verdict, _e in rows:
        d = blind.setdefault(host, [0, 0])
        d[0] += 1
        if verdict != "unreachable":
            d[1] += 1
    if a.json:
        print(json.dumps({"rows": rows, "findings": findings}, indent=1)); return 1 if findings else 0
    print("=" * 78)
    print("AUTHZ AUDIT -- an anonymous caller must be REFUSED by everything not declared public")
    print("=" * 78)
    last = None
    for host, p, st, verdict, extra in rows:
        if host != last:
            print("\n%s" % host); last = host
        flag = "  <-- FINDING" if verdict == "SERVED" else ""
        print("  %-46s %-4s %-16s%s" % (p[:46], st, verdict, flag))
        if extra and verdict in ("SERVED", "other", "unreachable"):
            print("        %s" % extra[:150])
    print()
    dead = [h for h, (tot, ok) in blind.items() if ok == 0]
    partial = [h for h, (tot, ok) in blind.items() if 0 < ok < tot]
    if findings:
        print("[X] %d ROUTE(S) SERVED DATA TO AN ANONYMOUS CALLER:" % len(findings))
        for host, p, st, extra in findings:
            print("    %s %s -> %s  %s" % (host, p, st, extra[:120]))
        return 1
    if dead:
        print("[!] BLIND, NOT CLEAN: nothing was reachable for %s." % ", ".join(dead))
        print("    Every probe failed at the network, so this run says NOTHING about those hosts.")
        print("    Run it from a machine with direct internet access (your PC), not from a")
        print("    sandbox or behind a filtering proxy.")
        return 2
    if partial:
        print("[!] partially reachable: %s -- read the rows before concluding." % ", ".join(partial))
    print("[OK] no route served content to an anonymous caller (%d host(s) fully probed)."
          % len([h for h, (t, o) in blind.items() if o == t]))
    print("     NOTE: 'not-present' means a 404, which is not proof a route is absent -- the bot")
    print("     gate returns 404 too. It is proof that nothing was SERVED, which is the question.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
