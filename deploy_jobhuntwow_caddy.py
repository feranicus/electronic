#!/usr/bin/env python3
"""
deploy_jobhuntwow_caddy.py
==========================
Adds jobhuntwow.com (static one-pager) to the EXISTING Caddy that already
fronts godeyes.ai (the `videodead` compose stack) on this DigitalOcean droplet.

Steps 3, 4, 5:
  3) adds a read-only volume for /opt/jobhuntwow/site to the `caddy` service
  4) appends a jobhuntwow.com site block to the Caddyfile
  5) validates the Caddyfile, then recreates ONLY the caddy container

Idempotent + backups. If validation fails, the Caddyfile backup is restored
and nothing is deployed. godeyes.ai is NOT touched.

Usage (run as root on the droplet):
    python3 deploy_jobhuntwow_caddy.py            # do it
    python3 deploy_jobhuntwow_caddy.py --dry-run  # preview only
    python3 deploy_jobhuntwow_caddy.py --no-stage # don't download index.html
"""
from __future__ import annotations
import os, re, sys, shutil, subprocess, datetime, urllib.request

# ----------------------------- CONFIG ---------------------------------
COMPOSE_DIR   = "/opt/videodead"
COMPOSE_FILE  = os.path.join(COMPOSE_DIR, "docker-compose.yml")
CADDYFILE     = os.path.join(COMPOSE_DIR, "Caddyfile")
CADDY_SERVICE = "caddy"
CADDY_IMAGE   = "caddy:2-alpine"

SITE_HOST_DIR = "/opt/jobhuntwow/site"
MOUNT_TARGET  = "/srv/jobhuntwow"
MOUNT_LINE    = SITE_HOST_DIR + ":" + MOUNT_TARGET + ":ro"

RAW_URL       = "https://raw.githubusercontent.com/feranicus/jobhuntwow.com/main/index.html"
DOMAINS       = "jobhuntwow.com, www.jobhuntwow.com"   # set to "jobhuntwow.com" if www DNS is not moved

MARKER  = "# >>> jobhuntwow.com one-pager (managed by deploy_jobhuntwow_caddy.py) >>>"
ENDMARK = "# <<< jobhuntwow.com one-pager <<<"

CADDY_BLOCK = f"""{MARKER}
{DOMAINS} {{
\tencode gzip zstd
\theader {{
\t\tStrict-Transport-Security "max-age=31536000; includeSubDomains"
\t\t-Server
\t\tX-Content-Type-Options "nosniff"
\t\tReferrer-Policy "strict-origin-when-cross-origin"
\t\tContent-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
\t}}
\troot * {MOUNT_TARGET}
\ttry_files {{path}} /index.html
\tfile_server
}}
{ENDMARK}"""
# ----------------------------------------------------------------------

DRY = "--dry-run" in sys.argv
NO_STAGE = "--no-stage" in sys.argv
TS = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def say(m):  print("  " + m)
def ok(m):   print("  \033[92m✓\033[0m " + m)
def warn(m): print("  \033[93m!\033[0m " + m)
def die(m):  print("  \033[91m✗ " + m + "\033[0m"); sys.exit(1)

def backup(path):
    b = path + ".bak." + TS
    shutil.copy2(path, b)
    ok("backup: " + b)
    return b

def stage_site():
    idx = os.path.join(SITE_HOST_DIR, "index.html")
    if os.path.exists(idx) and os.path.getsize(idx) > 1000:
        ok("static file already present: %s (%d bytes)" % (idx, os.path.getsize(idx)))
        return
    if NO_STAGE:
        die(idx + " missing and --no-stage set. Put index.html there first.")
    if DRY:
        say("[dry-run] would create %s and download index.html" % SITE_HOST_DIR); return
    os.makedirs(SITE_HOST_DIR, exist_ok=True)
    say("downloading index.html -> " + idx)
    try:
        urllib.request.urlretrieve(RAW_URL, idx)
    except Exception as e:
        die("download failed (%s). Put index.html into %s manually." % (e, SITE_HOST_DIR))
    ok("staged %s (%d bytes)" % (idx, os.path.getsize(idx)))

def edit_compose(text):
    if MOUNT_TARGET in text:
        return text, False
    lines = text.splitlines()
    svc_re = re.compile(r'^(\s*)' + re.escape(CADDY_SERVICE) + r':\s*$')
    start = indent = None
    for i, l in enumerate(lines):
        m = svc_re.match(l)
        if m:
            start, indent = i, len(m.group(1)); break
    if start is None:
        die("could not find service '%s:' in %s" % (CADDY_SERVICE, COMPOSE_FILE))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "":
            continue
        if (len(lines[i]) - len(lines[i].lstrip())) <= indent:
            end = i; break
    vol_idx = item_indent = None
    for i in range(start, end):
        if re.match(r'^\s*volumes:\s*$', lines[i]):
            vol_idx = i
            for j in range(i + 1, end):
                if lines[j].lstrip().startswith("- "):
                    item_indent = len(lines[j]) - len(lines[j].lstrip()); break
            if item_indent is None:
                item_indent = (len(lines[i]) - len(lines[i].lstrip())) + 2
            break
    if vol_idx is None:
        die("no 'volumes:' block found inside the caddy service")
    lines.insert(vol_idx + 1, " " * item_indent + "- " + MOUNT_LINE)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True

def edit_caddyfile(text):
    if MARKER in text or ("root * " + MOUNT_TARGET) in text:
        return text, False
    return text.rstrip("\n") + "\n\n" + CADDY_BLOCK + "\n", True

def _read_env(path):
    env = {}
    if os.path.exists(path):
        for raw in open(path, encoding="utf-8"):
            s = raw.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def validate_caddyfile():
    say("validating Caddyfile with a throwaway caddy container ...")
    env = _read_env(os.path.join(COMPOSE_DIR, ".env"))
    dom  = env.get("DOMAIN", "example.com")
    mail = env.get("ADMIN_EMAIL", "admin@example.com")
    r = subprocess.run(
        ["docker", "run", "--rm",
         "-e", "DOMAIN=" + dom, "-e", "ADMIN_EMAIL=" + mail,
         "-v", CADDYFILE + ":/etc/caddy/Caddyfile:ro",
         CADDY_IMAGE, "caddy", "validate", "--adapter", "caddyfile",
         "--config", "/etc/caddy/Caddyfile"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout); print(r.stderr); return False
    ok("Caddyfile is valid")
    return True

def compose_cmd():
    if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0:
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    die("neither 'docker compose' nor 'docker-compose' found")

def main():
    print("\n=== deploy jobhuntwow.com onto existing Caddy ===\n")
    if os.geteuid() != 0:
        warn("not running as root - editing /opt and docker may fail. Try: sudo python3 ...")
    for f in (COMPOSE_FILE, CADDYFILE):
        if not os.path.exists(f):
            die("not found: %s  (adjust COMPOSE_DIR at top of script)" % f)

    print("[0] stage static file")
    stage_site()

    print("\n[3] docker-compose.yml - add caddy volume")
    c0 = open(COMPOSE_FILE, encoding="utf-8").read()
    c1, changed_c = edit_compose(c0)
    if not changed_c:
        ok("volume already present - no change")
    elif DRY:
        say("[dry-run] would add volume line: - " + MOUNT_LINE)
    else:
        backup(COMPOSE_FILE); open(COMPOSE_FILE, "w", encoding="utf-8").write(c1)
        ok("added volume: - " + MOUNT_LINE)

    print("\n[4] Caddyfile - add jobhuntwow.com site block")
    f0 = open(CADDYFILE, encoding="utf-8").read()
    f1, changed_f = edit_caddyfile(f0)
    if not changed_f:
        ok("site block already present - no change")
    elif DRY:
        say("[dry-run] would append this block:"); print("\n" + CADDY_BLOCK + "\n")
    else:
        cbak = backup(CADDYFILE); open(CADDYFILE, "w", encoding="utf-8").write(f1)
        ok("appended jobhuntwow.com block")
        if not validate_caddyfile():
            warn("validation FAILED - restoring Caddyfile backup, nothing deployed")
            shutil.copy2(cbak, CADDYFILE)
            die("fix the error above and re-run")

    if DRY:
        print("\n[5] (dry-run) would run: docker compose up -d caddy\n")
        print("Dry run complete. Re-run without --dry-run to apply.\n"); return

    print("\n[5] recreate the caddy container (godeyes.ai blips ~2-3s)")
    cc = compose_cmd()
    r = subprocess.run(cc + ["up", "-d", CADDY_SERVICE], cwd=COMPOSE_DIR)
    if r.returncode != 0:
        die("docker compose up failed - check output above")
    ok("caddy recreated")

    print("\n=== done ===")
    print("  Next:")
    print("   1) DNS: point jobhuntwow.com (A @) -> this droplet IP, and www -> jobhuntwow.com")
    print("      (remove the GitHub Pages 185.199.x A-records; remove custom domain in GitHub Pages)")
    print("   2) Watch the cert:   docker logs -f videodead-caddy-1")
    print("      look for: certificate obtained successfully (jobhuntwow.com)")
    print("   3) Open https://jobhuntwow.com in incognito.")
    print("  Caddy keeps retrying the cert until DNS points here - that's normal.\n")

if __name__ == "__main__":
    main()
