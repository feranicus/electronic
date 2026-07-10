#!/usr/bin/env python3
"""
provision_web.py — publish cybergod.ai from the droplet, fully automatically. No manual steps.

Runs in CI (over Tailscale) or locally. It:
  1. DNS  — via the DigitalOcean API, points cybergod.ai (+ www) A-records at the droplet.
  2. Proxy— SSHes in, DETECTS what serves 80/443, and wires cybergod.ai -> the colt-web
            container (127.0.0.1:8090) with TLS, WITHOUT disturbing the existing sites:
              * host Caddy  -> append an idempotent site block to /etc/caddy/Caddyfile + reload
              * Caddy in a container -> append to its mounted Caddyfile + `caddy reload`
              * nothing on 80/443 -> bring up our own colt-caddy (compose profile) for auto-TLS
              * nginx/traefik detected -> print the exact one-liner (rare; still no guesswork)
Env: DO_API_TOKEN, DROPLET_HOST, DROPLET_USER, SSH_KEY, DOMAIN(=cybergod.ai), WEB_PORT(=8090).
"""
import os, sys, json, subprocess, urllib.request, urllib.error

DOMAIN = os.environ.get("DOMAIN", "cybergod.ai")
HOST   = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER   = os.environ.get("DROPLET_USER", "root")
KEY    = os.environ.get("SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
PORT   = os.environ.get("WEB_PORT", "8090")
TOKEN  = os.environ.get("DO_API_TOKEN", "")
PUBIP  = os.environ.get("DROPLET_PUBLIC_IP", "64.225.108.200")   # A-record target (public IP, not tailnet)

SSH = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
if os.path.exists(KEY): SSH += ["-i", KEY]

def ssh(cmd):
    r = subprocess.run(SSH + [f"{USER}@{HOST}", cmd], text=True, capture_output=True)
    return r.returncode, (r.stdout or ""), (r.stderr or "")

def do_api(method, path, body=None):
    req = urllib.request.Request("https://api.digitalocean.com" + path,
        data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r: return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or "{}")

# ---------- 1) DNS via DO API ----------
def ensure_dns():
    if not TOKEN:
        print("  [dns] no DO_API_TOKEN — skipping (point cybergod.ai A -> %s yourself once)" % PUBIP); return
    st, j = do_api("GET", "/v2/domains/" + DOMAIN)
    if st == 404:
        do_api("POST", "/v2/domains", {"name": DOMAIN, "ip_address": PUBIP})
        print(f"  [dns] created zone {DOMAIN} -> {PUBIP}")
    st, j = do_api("GET", f"/v2/domains/{DOMAIN}/records?per_page=200")
    recs = {(r["type"], r["name"]): r for r in j.get("domain_records", [])}
    for name in ("@", "www"):
        cur = recs.get(("A", name))
        if cur and cur.get("data") == PUBIP:
            print(f"  [dns] {name}.{DOMAIN} already -> {PUBIP}")
        elif cur:
            do_api("PUT", f"/v2/domains/{DOMAIN}/records/{cur['id']}", {"data": PUBIP}); print(f"  [dns] updated {name} -> {PUBIP}")
        else:
            do_api("POST", f"/v2/domains/{DOMAIN}/records", {"type": "A", "name": name, "data": PUBIP, "ttl": 300}); print(f"  [dns] added {name} -> {PUBIP}")

# ---------- 2) detect proxy + wire cybergod.ai ----------
CADDY_BLOCK = (f"\n# --- cybergod.ai (colt-web) — managed by provision_web.py ---\n"
               f"{DOMAIN}, www.{DOMAIN} {{\n\treverse_proxy 127.0.0.1:{PORT}\n}}\n")

def wire_proxy():
    _, who, _ = ssh("ss -tlnp '( sport = :443 )' 2>/dev/null | tail -n +2")
    _, cad, _ = ssh("docker ps --format '{{.Names}} {{.Image}}' | grep -i caddy | head -1")
    host_caddy = "caddy" in who.lower() or bool(ssh("test -f /etc/caddy/Caddyfile && echo y")[1].strip())
    if cad.strip():                                   # Caddy in a container
        name = cad.split()[0]
        _, cf, _ = ssh(f"docker inspect {name} --format '{{{{range .Mounts}}}}{{{{if eq .Destination \"/etc/caddy/Caddyfile\"}}}}{{{{.Source}}}}{{{{end}}}}{{{{end}}}}'")
        cf = cf.strip()
        if cf:
            ssh(f"grep -q '{DOMAIN} ' {cf} || printf '%s' \"{CADDY_BLOCK}\" >> {cf}")
            ssh(f"docker exec {name} caddy reload --config /etc/caddy/Caddyfile 2>/dev/null || docker restart {name}")
            print(f"  [proxy] merged into container Caddy '{name}' ({cf}) — auto-TLS for {DOMAIN}"); return True
    if host_caddy:                                    # host Caddy
        ssh(f"grep -q '{DOMAIN} ' /etc/caddy/Caddyfile || printf '%s' \"{CADDY_BLOCK}\" >> /etc/caddy/Caddyfile")
        ssh("caddy reload --config /etc/caddy/Caddyfile 2>/dev/null || systemctl reload caddy")
        print(f"  [proxy] merged into host Caddy — auto-TLS for {DOMAIN}"); return True
    if not who.strip():                               # nothing on 443 -> run our own Caddy
        ssh("cd /opt/colt-stack 2>/dev/null || cd /root/colt-stack; docker compose -f docker-compose.reuse.yml -p colt-stack --profile edge up -d caddy")
        print(f"  [proxy] nothing owned 443 — started bundled colt-caddy (auto-TLS for {DOMAIN})"); return True
    print(f"  [proxy] 443 is held by a non-Caddy proxy: {who.strip()[:120]}")
    print(f"          add one vhost: {DOMAIN} -> 127.0.0.1:{PORT}  (nginx: proxy_pass; traefik: labels)")
    return False

def main():
    print(f"=== provision cybergod.ai on {USER}@{HOST} ===")
    print("--- 1) DNS ---");  ensure_dns()
    print("--- 2) proxy ---"); ok = wire_proxy()
    print("--- 3) verify ---")
    rc, out, _ = ssh(f"curl -sko /dev/null -w '%{{http_code}}' https://127.0.0.1:{PORT}/api/me || true")
    print(f"  colt-web local health: HTTP {out.strip() or '?'} (401 = up, auth working)")
    print("\nDONE." + (f" https://{DOMAIN} will serve once DNS + Let's Encrypt settle (~1–2 min)." if ok else " Manual vhost needed (see above)."))

if __name__ == "__main__":
    main()
