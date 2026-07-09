#!/usr/bin/env python3
"""
import_dashboard.py — push the 'Colt Bots Observability' dashboard into your EXISTING Grafana
(videodead / godeyes.ai) over the Grafana HTTP API. No manual upload, no new Grafana.

It:
  1) finds your Loki datasource uid automatically,
  2) rewrites the dashboard's datasource refs to that uid,
  3) creates/updates the dashboard (idempotent, overwrite=true).

Auth (pick one):
  * Service account token (recommended): Grafana -> Administration -> Service accounts ->
    add a token with role Editor or Admin.  Pass it as --token or env GRAFANA_TOKEN.
  * Admin basic auth: --user admin --password <pw>  (or env GRAFANA_USER / GRAFANA_PASS)

Examples (run from C:\\Python SW\\Linkedin Scraper):
  python import_dashboard.py --url https://godeyes.ai/observe --token glsa_XXXX…
  python import_dashboard.py --url https://godeyes.ai/observe --user admin --password '***'
  # if datasource listing is blocked, name the Loki uid yourself:
  python import_dashboard.py --url https://godeyes.ai/observe --token … --loki-uid loki
"""
import argparse, base64, json, os, ssl, sys, urllib.request, urllib.error

def req(method, url, headers, body=None, insecure=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    ctx = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(r, timeout=30, context=ctx) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def auth_headers(token, user, password):
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    elif user:
        h["Authorization"] = "Basic " + base64.b64encode(("%s:%s" % (user, password)).encode()).decode()
    else:
        sys.exit("!! Provide --token (service account) or --user/--password.")
    return h

def find_loki_uid(base, headers, insecure):
    st, data = req("GET", base + "/api/datasources", headers, insecure=insecure)
    if st != 200 or not isinstance(data, list):
        return None
    loki = [d for d in data if d.get("type") == "loki"]
    if not loki:
        return None
    # prefer one literally named/uid'd 'loki', else the first
    for d in loki:
        if d.get("uid") == "loki" or (d.get("name", "").lower() == "loki"):
            return d["uid"]
    return loki[0]["uid"]

def retarget(obj, uid):
    """Recursively point every loki datasource ref at the real uid."""
    if isinstance(obj, dict):
        if obj.get("type") == "loki" and "uid" in obj:
            obj["uid"] = uid
        for v in obj.values():
            retarget(v, uid)
    elif isinstance(obj, list):
        for v in obj:
            retarget(v, uid)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("GRAFANA_URL", "https://godeyes.ai/observe"),
                    help="Grafana base URL incl. sub-path (e.g. https://godeyes.ai/observe)")
    ap.add_argument("--token", default=os.environ.get("GRAFANA_TOKEN", ""))
    ap.add_argument("--user", default=os.environ.get("GRAFANA_USER", ""))
    ap.add_argument("--password", default=os.environ.get("GRAFANA_PASS", ""))
    ap.add_argument("--dashboard", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "obs", "grafana", "dashboards", "assess.json"))
    ap.add_argument("--loki-uid", default="", help="override if datasource listing is blocked")
    ap.add_argument("--folder", default="", help="Grafana folder title (optional; default General)")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification")
    ap.add_argument("--all", action="store_true", help="import EVERY *.json in obs/grafana/dashboards/")
    a = ap.parse_args()
    base = a.url.rstrip("/")
    headers = auth_headers(a.token, a.user, a.password)

    # sanity: can we reach the API?
    st, who = req("GET", base + "/api/user", headers, insecure=a.insecure)
    if st == 401 or st == 403:
        sys.exit("!! Auth failed (%s). Check the token/credentials and role (need Editor/Admin)." % st)
    if st != 200:
        print("… /api/user returned %s (continuing; sub-path or proxy may differ): %s" % (st, str(who)[:160]))

    # 1) find the Loki datasource uid
    uid = a.loki_uid or find_loki_uid(base, headers, a.insecure)
    if not uid:
        sys.exit("!! Could not find a Loki datasource (need datasource read perm). "
                 "Re-run with --loki-uid <uid> — find it in Grafana: Connections -> Data sources -> your Loki.")
    print("Using Loki datasource uid: %s" % uid)

    # 2) which dashboard(s) to push
    if a.all:
        ddir = os.path.dirname(os.path.abspath(a.dashboard))
        paths = sorted(p for p in [os.path.join(ddir, f) for f in os.listdir(ddir)]
                       if p.endswith(".json"))
    else:
        paths = [a.dashboard]

    # 3) load + retarget + create/update each
    failures = 0
    for path in paths:
        dash = json.load(open(path, encoding="utf-8"))
        dash.pop("id", None); dash["id"] = None      # create-or-update by uid
        retarget(dash, uid)
        payload = {"dashboard": dash, "overwrite": True,
                   "message": "imported via import_dashboard.py"}
        if a.folder:
            payload["folderUid"] = a.folder
        st, res = req("POST", base + "/api/dashboards/db", headers, body=payload, insecure=a.insecure)
        name = os.path.basename(path)
        if st == 200 and isinstance(res, dict) and res.get("status") == "success":
            print("✅ %-22s -> %s%s" % (name, base, res.get("url", "")))
        else:
            print("!! %-22s import failed (%s): %s" % (name, st, str(res)[:300]))
            failures += 1
    if failures:
        sys.exit(1)

if __name__ == "__main__":
    main()
