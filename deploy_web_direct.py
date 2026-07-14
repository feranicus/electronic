#!/usr/bin/env python3
"""
deploy_web_direct.py -- deploy cybergod.ai (colt-web) DIRECTLY from your machine to the droplet.
No GitHub, no CI. Uses your working SSH. Minimal footprint. Idempotent, self-verifying.

Steps: pack web sources -> scp -> build+restart colt-web (single network, --force-recreate) ->
rewrite the cybergod block in videodead's Caddyfile from deploy/caddy/cybergod.caddy -> FORCE Caddy
to load it via the admin API (POST /load; a plain reload can keep a stale config) -> if still not
live, restart the caddy container as a last resort -> verify colt-web single-network + public 401.

Usage:  python deploy_web_direct.py
Env (optional): DROPLET_HOST (default 64.225.108.200), DROPLET_USER (root), SSH_KEY (path)
"""
import os, sys, subprocess, tarfile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", "")
SSH_BASE = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
SCP_BASE = ["scp", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
if KEY and os.path.exists(KEY):
    SSH_BASE += ["-i", KEY]; SCP_BASE += ["-i", KEY]

INCLUDE = ["webapp", "hermes-skills/shodan-assessment", "colt_auth.py",
           "docker-compose.web.yml", "deploy", ".dockerignore"]
EXCLUDE = {"node_modules", "__pycache__", "dist", ".git", ".pytest_cache", "shodan-out"}

def _filter(ti):
    if set(ti.name.split("/")) & EXCLUDE:
        return None
    return ti

def pack():
    tf = tempfile.NamedTemporaryFile(suffix=".tgz", delete=False); tf.close()
    with tarfile.open(tf.name, "w:gz") as tar:
        for item in INCLUDE:
            p = os.path.join(HERE, item)
            if os.path.exists(p):
                tar.add(p, arcname=item, filter=_filter)
    return tf.name

REMOTE = "\n".join([
    "set -e",
    "cd /opt/colt-stack",
    "[ -f .env ] || printf 'LOKI_URL=http://videodead-loki-1:3100/loki/api/v1/push\\nLOKI_NETWORK=videodead_appnet\\n' > .env",
    "echo '== build + (re)start colt-web (single network, force-recreate) =='",
    "docker compose -p colt-stack -f docker-compose.web.yml up -d --build --force-recreate",
    "echo '== wire cybergod.ai into the shared caddy from the committed snippet =='",
    "CADDY_CT=\"$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)\"",
    "CF=\"$(docker inspect \"$CADDY_CT\" --format '{{range .Mounts}}{{if eq .Destination \"/etc/caddy/Caddyfile\"}}{{.Source}}{{end}}{{end}}')\"",
    "cp \"$CF\" \"$CF.bak.$(date +%s)\"",
    "sed -i '/# colt:cybergod BEGIN/,/# colt:cybergod END/d' \"$CF\"",
    "sed -i '/cybergod/,/^}/d' \"$CF\"",
    "cat deploy/caddy/cybergod.caddy >> \"$CF\"",
    "sed -i 's#^cybergod.ai,.*{$#cybergod.ai, www.cybergod.ai {#' \"$CF\"",
    "docker exec \"$CADDY_CT\" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile",
    "echo '== FORCE a full config load via the admin API (a plain reload can keep a stale config) =='",
    "docker exec \"$CADDY_CT\" sh -c 'caddy adapt --config /etc/caddy/Caddyfile > /tmp/cfg.json && curl -sS -X POST -H \"Content-Type: application/json\" -H \"Cache-Control: must-revalidate\" --data @/tmp/cfg.json http://localhost:2019/load && echo ADMIN_LOAD_OK' || echo 'admin load failed (no admin API?)'",
    "sleep 3",
    "code=\"$(curl -sk --resolve cybergod.ai:443:127.0.0.1 https://cybergod.ai/api/me -o /dev/null -w '%{http_code}' || true)\"",
    "if [ \"$code\" != \"401\" ]; then echo \"== admin load did not take (got $code) -> restarting $CADDY_CT (brief) ==\"; docker restart \"$CADDY_CT\" >/dev/null; sleep 6; fi",
    "echo '== verify =='",
    "echo -n 'colt-web image : '; docker inspect colt-web -f '{{.Config.Image}}'",
    "echo -n 'colt-web nets  : '; docker inspect colt-web -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'; echo",
    "echo -n 'caddy->colt-web: '; docker exec \"$CADDY_CT\" wget -qO- -T5 http://colt-web:8000/api/me 2>&1 | head -c 60; echo",
    "curl -sk --resolve cybergod.ai:443:127.0.0.1 https://cybergod.ai/api/me -o /dev/null -w 'public via caddy = %{http_code}  (401 = LIVE)\\n'",
    "",
])

def main():
    tgt = "%s@%s" % (USER, HOST)
    print("== pack sources =="); tgz = pack()
    print("  packed (%d KB)" % (os.path.getsize(tgz)//1024))
    print("== upload ==")
    if subprocess.run(SSH_BASE + [tgt, "mkdir -p /opt/colt-stack"]).returncode: sys.exit("[X] ssh failed")
    if subprocess.run(SCP_BASE + [tgz, "%s:/tmp/colt-web-src.tgz" % tgt]).returncode:
        sys.exit("[X] scp failed")
    subprocess.run(SSH_BASE + [tgt, "tar xzf /tmp/colt-web-src.tgz -C /opt/colt-stack && rm -f /tmp/colt-web-src.tgz"], check=True)
    print("== build + deploy + wire + verify (on droplet) ==")
    # raw LF bytes: text=True would translate \n -> \r\n on Windows and break bash
    r = subprocess.run(SSH_BASE + [tgt, "bash -s"], input=REMOTE.encode("utf-8"))
    try: os.unlink(tgz)
    except Exception: pass
    if r.returncode: sys.exit("[X] remote deploy failed (see output above)")
    print("\nDONE. If 'public via caddy = 401', open https://cybergod.ai/login")

if __name__ == "__main__":
    main()
