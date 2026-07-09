#!/usr/bin/env python3
"""
deploy_jobhuntwow_obs.py
========================
Lights up jobhuntwow.com in the EXISTING Grafana/Loki stack on this droplet.

  1) enables Caddy JSON access logs for the jobhuntwow.com block (stdout ->
     promtail (docker sd) -> Loki, labels: container="videodead-caddy-1")
  2) validates the Caddyfile, then `caddy reload` (zero-downtime)
  3) drops a provisioned Grafana dashboard "JobHuntWOW" into
     /opt/videodead/observability/grafana/dashboards/jobhuntwow.json

Idempotent + backups. godeyes.ai untouched. Run as root on the droplet:
    python3 deploy_jobhuntwow_obs.py
    python3 deploy_jobhuntwow_obs.py --dry-run
"""
import os, sys, json, shutil, subprocess, datetime

COMPOSE_DIR      = "/opt/videodead"
CADDYFILE        = os.path.join(COMPOSE_DIR, "Caddyfile")
CADDY_CONTAINER  = "videodead-caddy-1"
CADDY_IMAGE      = "caddy:2-alpine"
DASH_DIR         = "/opt/videodead/observability/grafana/dashboards"
DASH_PATH        = os.path.join(DASH_DIR, "jobhuntwow.json")

CONTAINER = "videodead-caddy-1"   # Loki 'container' label value for caddy
HOST      = "jobhuntwow.com"

MARKER  = "# >>> jobhuntwow.com one-pager (managed by deploy_jobhuntwow_caddy.py) >>>"
ENDMARK = "# <<< jobhuntwow.com one-pager <<<"

# The whole jobhuntwow block, now WITH access logging (spaces indent; Caddy accepts it)
NEW_BLOCK = '''# >>> jobhuntwow.com one-pager (managed by deploy_jobhuntwow_caddy.py) >>>
jobhuntwow.com, www.jobhuntwow.com {
    log {
        output stdout
        format json
    }
    encode gzip zstd
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        -Server
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    }
    root * /srv/jobhuntwow
    try_files {path} /index.html
    file_server
}
# <<< jobhuntwow.com one-pager <<<'''

DRY = "--dry-run" in sys.argv
TS  = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
def ok(m):   print("  \033[92m✓\033[0m " + m)
def say(m):  print("  " + m)
def warn(m): print("  \033[93m!\033[0m " + m)
def die(m):  print("  \033[91m✗ " + m + "\033[0m"); sys.exit(1)

def backup(p):
    b = p + ".bak." + TS; shutil.copy2(p, b); ok("backup: " + b); return b

def _read_env(path):
    env = {}
    if os.path.exists(path):
        for raw in open(path, encoding="utf-8"):
            s = raw.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def validate():
    say("validating Caddyfile ...")
    env = _read_env(os.path.join(COMPOSE_DIR, ".env"))
    dom = env.get("DOMAIN", "example.com"); mail = env.get("ADMIN_EMAIL", "admin@example.com")
    r = subprocess.run(["docker","run","--rm","-e","DOMAIN="+dom,"-e","ADMIN_EMAIL="+mail,
        "-v", CADDYFILE+":/etc/caddy/Caddyfile:ro", CADDY_IMAGE,
        "caddy","validate","--adapter","caddyfile","--config","/etc/caddy/Caddyfile"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout); print(r.stderr); return False
    ok("Caddyfile valid"); return True

# ---------- Grafana dashboard (Loki-based) ----------
DS = {"type": "loki", "uid": "${ds}"}
SEL = '{container="%s"} | json | request_host="%s"' % (CONTAINER, HOST)

def tgt(expr, refId="A", qt="range", legend=None):
    d = {"refId": refId, "expr": expr, "queryType": qt, "datasource": DS}
    if legend is not None: d["legendFormat"] = legend
    return d

def stat(pid, title, x, y, w, expr, unit="short", dec=0):
    return {"id": pid, "type": "stat", "title": title, "datasource": DS,
            "gridPos": {"h": 4, "w": w, "x": x, "y": y},
            "targets": [tgt(expr, qt="instant")],
            "fieldConfig": {"defaults": {"unit": unit, "decimals": dec}, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": "value", "graphMode": "area", "textMode": "auto"}}

def ts(pid, title, x, y, w, targets, unit="short"):
    return {"id": pid, "type": "timeseries", "title": title, "datasource": DS,
            "gridPos": {"h": 8, "w": w, "x": x, "y": y}, "targets": targets,
            "fieldConfig": {"defaults": {"unit": unit,
                "custom": {"drawStyle": "line", "fillOpacity": 12, "showPoints": "never", "lineWidth": 2}},
                "overrides": []},
            "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}}

def table(pid, title, x, y, w, expr):
    return {"id": pid, "type": "table", "title": title, "datasource": DS,
            "gridPos": {"h": 8, "w": w, "x": x, "y": y},
            "targets": [tgt(expr, qt="instant")],
            "options": {"showHeader": True},
            "transformations": [{"id": "labelsToFields", "options": {}},
                                {"id": "organize", "options": {"excludeByName": {"Time": True}}}],
            "fieldConfig": {"defaults": {}, "overrides": []}}

def logs(pid, title, x, y, w, h, expr):
    return {"id": pid, "type": "logs", "title": title, "datasource": DS,
            "gridPos": {"h": h, "w": w, "x": x, "y": y}, "targets": [tgt(expr, qt="range")],
            "options": {"showTime": True, "wrapLogMessage": True, "enableLogDetails": True,
                        "sortOrder": "Descending", "dedupStrategy": "none"}}

def dashboard():
    panels = [
        stat(1, "Requests (range)", 0, 0, 6, "sum(count_over_time(%s [$__range]))" % SEL),
        stat(2, "Unique visitors (IPs)", 6, 0, 6,
             "count(sum by (request_remote_ip) (count_over_time(%s [$__range])))" % SEL),
        stat(3, "Errors 4xx/5xx", 12, 0, 6,
             'sum(count_over_time(%s | status=~"4..|5.." [$__range]))' % SEL),
        stat(4, "Avg latency", 18, 0, 6,
             "avg_over_time(%s | unwrap duration [$__range])" % SEL, unit="s", dec=3),
        ts(5, "Requests/min by status", 0, 4, 12,
           [tgt("sum by (status) (count_over_time(%s [1m]))" % SEL, legend="{{status}}")]),
        ts(6, "Latency p50 / p95 (s)", 12, 4, 12,
           [tgt("quantile_over_time(0.50, %s | unwrap duration [5m])" % SEL, "A", legend="p50"),
            tgt("quantile_over_time(0.95, %s | unwrap duration [5m])" % SEL, "B", legend="p95")],
           unit="s"),
        table(7, "Top paths", 0, 12, 12,
              "topk(15, sum by (request_uri) (count_over_time(%s [$__range])))" % SEL),
        table(8, "Top client IPs", 12, 12, 12,
              "topk(15, sum by (request_remote_ip) (count_over_time(%s [$__range])))" % SEL),
        logs(9, "Live access log (jobhuntwow.com)", 0, 20, 24, 11,
             '{container="%s"} | json | request_host="%s" | line_format "{{.request_method}} {{.request_uri}} → {{.status}}  {{.duration}}s  {{.request_remote_ip}}"' % (CONTAINER, HOST)),
    ]
    return {"uid": "jobhuntwow", "title": "JobHuntWOW — traffic (jobhuntwow.com)",
            "tags": ["jobhuntwow", "caddy", "loki"], "schemaVersion": 39, "version": 1,
            "editable": True, "refresh": "30s", "time": {"from": "now-6h", "to": "now"},
            "templating": {"list": [{"type": "datasource", "name": "ds", "label": "Loki",
                                     "query": "loki", "hide": 0, "refresh": 1, "current": {}}]},
            "panels": panels}

# ------------------------------- main ---------------------------------
def main():
    print("\n=== jobhuntwow.com observability ===\n")
    if os.geteuid() != 0:
        warn("not root — editing /opt and docker may fail (use sudo)")
    if not os.path.exists(CADDYFILE):
        die("Caddyfile not found: " + CADDYFILE)

    print("[1] Caddy access logs for jobhuntwow.com")
    text = open(CADDYFILE, encoding="utf-8").read()
    s, e = text.find(MARKER), text.find(ENDMARK)
    if s == -1 or e == -1:
        die("jobhuntwow marker block not found — run deploy_jobhuntwow_caddy.py first")
    block = text[s:e + len(ENDMARK)]
    if "log {" in block:
        ok("access logging already enabled — no change")
    elif DRY:
        say("[dry-run] would replace the jobhuntwow block with a logging-enabled version")
    else:
        cbak = backup(CADDYFILE)
        new = text[:s] + NEW_BLOCK + text[e + len(ENDMARK):]
        open(CADDYFILE, "w", encoding="utf-8").write(new)
        ok("enabled log { format json } in jobhuntwow block")
        if not validate():
            warn("validation FAILED — restoring backup"); shutil.copy2(cbak, CADDYFILE)
            die("nothing changed; fix and re-run")

    print("\n[2] reload caddy (zero-downtime)")
    if DRY:
        say("[dry-run] would run: docker exec %s caddy reload --config /etc/caddy/Caddyfile" % CADDY_CONTAINER)
    else:
        r = subprocess.run(["docker", "exec", CADDY_CONTAINER, "caddy", "reload",
                            "--config", "/etc/caddy/Caddyfile"])
        if r.returncode != 0:
            die("caddy reload failed — check 'docker logs %s'" % CADDY_CONTAINER)
        ok("caddy reloaded")

    print("\n[3] Grafana dashboard")
    if DRY:
        say("[dry-run] would write dashboard -> " + DASH_PATH)
    else:
        os.makedirs(DASH_DIR, exist_ok=True)
        if os.path.exists(DASH_PATH): backup(DASH_PATH)
        json.dump(dashboard(), open(DASH_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        ok("wrote " + DASH_PATH)

    print("\n=== done ===")
    print("  Open Grafana:  https://godeyes.ai/observe  -> Dashboards -> 'JobHuntWOW'")
    print("  (provisioning auto-loads it in ~10-30s; or:  docker restart videodead-grafana-1)")
    print("  Generate some traffic to see data:")
    print("     for i in $(seq 30); do curl -s -o /dev/null https://jobhuntwow.com/; done")
    print("  Raw logs in Grafana Explore (Loki):")
    print('     {container="%s"} | json | request_host="%s"\n' % (CONTAINER, HOST))

if __name__ == "__main__":
    main()
