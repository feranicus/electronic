#!/usr/bin/env python3
"""
deploy.py — A-to-Z deploy of the Colt bots to the DigitalOcean droplet over SSH.

Two modes:
  --reuse   (RECOMMENDED for you) bots + a tiny promtail that ships into your EXISTING Loki
            (the jobhuntwow/godeyes.ai Grafana stack). Adds NO Grafana/Loki of our own.
  --deploy  standalone: also brings up our own Loki+Grafana (only if you have no existing one).

SAFE alongside Amnezia VPN / VideoDead / jobhuntwow:
  * isolated docker project (colt-stack), unique container names (colt-*), own network
  * NEVER touches the firewall (ufw); NEVER stops/removes/prunes other containers
  * bots are OUTBOUND ONLY; in --reuse we publish NOTHING
  * installs Docker only if missing; adds swap only if none exists

Run from  C:\\Python SW\\Linkedin Scraper  on Windows (uses built-in ssh/scp/tar):
    python deploy.py --inspect
    python deploy.py --reuse                     # discovers your Loki + network, ships into it
    python deploy.py --reuse --loki-url http://loki:3100/loki/api/v1/push --loki-network jobhuntwow_default
    python deploy.py --deploy --grafana-port 3001   # standalone (own Grafana), only if needed
Config via env: DROPLET_HOST, DROPLET_USER, SSH_KEY.
"""
import argparse, os, subprocess, sys, tempfile

HOST    = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER    = os.environ.get("DROPLET_USER", "root")
SSH_KEY = os.environ.get("SSH_KEY", "")
REMOTE  = "/opt/colt-stack"
PROJECT = "colt-stack"
LOCAL   = os.path.dirname(os.path.abspath(__file__))
SSH_OPTS = (["-i", SSH_KEY] if SSH_KEY else []) + ["-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]

def run(cmd, check=True, capture=False, echo=True):
    if echo: print("  $ " + " ".join(cmd))
    r = subprocess.run(cmd, text=True,
                       stdout=(subprocess.PIPE if capture else None),
                       stderr=(subprocess.STDOUT if capture else None))
    if check and r.returncode != 0:
        if capture and r.stdout: print(r.stdout)
        print("!! command failed (%d)" % r.returncode); sys.exit(r.returncode)
    return r

def ssh(cmd, check=True, capture=False, echo=True):
    return run(["ssh", *SSH_OPTS, "%s@%s" % (USER, HOST), cmd], check=check, capture=capture, echo=echo)
def sshout(cmd):
    return (ssh(cmd, check=False, capture=True, echo=False).stdout or "").strip()
def scp(local_path, remote_path):
    return run(["scp", *SSH_OPTS, local_path, "%s@%s:%s" % (USER, HOST, remote_path)])

def inspect():
    print("\n=== READ-ONLY inventory of %s (nothing changed) ===\n" % HOST)
    ssh("docker --version 2>/dev/null || echo 'docker: NOT INSTALLED'", check=False)
    print("\n-- running containers (Amnezia VPN / VideoDead / jobhuntwow — we must NOT disturb them) --")
    ssh("docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null || true", check=False)
    print("\n-- existing Loki (we will ship into it) --")
    ssh("docker ps --format '{{.Names}}  {{.Image}}  net={{.Networks}}' 2>/dev/null | grep -i loki || echo '(no loki container found)'", check=False)
    print("\n-- listening ports / memory / swap --")
    ssh("(ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | awk 'NR==1||/LISTEN/'; echo; free -h; echo; swapon --show 2>/dev/null || echo '(no swap)'", check=False)
    print("\n-- our stack already present? --")
    ssh("docker ps -a --filter name=colt- --format '  {{.Names}} ({{.Status}})' 2>/dev/null || true", check=False)

def discover_loki():
    name = sshout("docker ps --format '{{.Names}}|{{.Image}}' 2>/dev/null | grep -i loki | head -1 | cut -d'|' -f1")
    if not name:
        return None, None
    net = sshout("docker inspect %s -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null | awk '{print $1}'" % name)
    return name, net

def ensure_docker():
    if "OK" in sshout("command -v docker >/dev/null 2>&1 && echo OK || echo MISSING"):
        print("  docker present — untouched."); return
    print("  installing docker (does not disturb existing services)...")
    ssh("apt-get update && apt-get install -y ca-certificates curl gnupg && install -m 0755 -d /etc/apt/keyrings && "
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && "
        "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] "
        "https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable\" > /etc/apt/sources.list.d/docker.list && "
        "apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin")

def ensure_swap():
    if "HAVE" in sshout("swapon --show 2>/dev/null | grep -q . && echo HAVE || echo NONE"):
        print("  swap present — untouched."); return
    print("  adding 2G swap (non-interfering)...")
    ssh("fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && "
        "grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab", check=False)

def package():
    tgz = os.path.join(tempfile.gettempdir(), "colt-stack.tgz")
    excludes = [".git", "shodan-out", "node_modules", "__pycache__", "*.bak", "*.bak2", "*.bak3", "hermes-local", "*.tgz", "uploads"]
    run(["tar"] + sum([["--exclude", e] for e in excludes], []) + ["-czf", tgz, "-C", LOCAL, "."])
    print("  packaged -> %s" % tgz); return tgz

def upload():
    tgz = package()
    scp(tgz, "/tmp/colt-stack.tgz")
    ssh("mkdir -p %s && tar -xzf /tmp/colt-stack.tgz -C %s && rm -f /tmp/colt-stack.tgz && chmod 600 %s/*/.env 2>/dev/null || true" % (REMOTE, REMOTE, REMOTE))

def deploy_reuse(loki_url, loki_net, assume_yes):
    print("\n=== PRE-FLIGHT (read-only) ==="); inspect()
    if not loki_url or not loki_net:
        name, net = discover_loki()
        if name and net:
            loki_url = loki_url or "http://%s:3100/loki/api/v1/push" % name
            loki_net = loki_net or net
            print("\nDiscovered existing Loki: container=%s  network=%s" % (name, net))
        else:
            print("\n!! Could not auto-discover the existing Loki container/network.")
            print("   Re-run with:  --loki-url http://<loki-container>:3100/loki/api/v1/push --loki-network <network>")
            sys.exit(2)
    print("\nWill ship logs to: %s   (join network: %s)" % (loki_url, loki_net))
    if not assume_yes and input("Proceed (reuse existing Grafana/Loki, add NO extra stack)? [y/N] ").strip().lower() != "y":
        print("Aborted."); return
    print("\n=== prerequisites (guarded) ==="); ensure_docker(); ensure_swap()
    print("\n=== upload ==="); upload()
    print("\n=== configure + launch (reuse mode, project '%s') ===" % PROJECT)
    ssh("cd %s && printf 'LOKI_URL=%s\\nLOKI_NETWORK=%s\\n' > .env && cat .env" % (REMOTE, loki_url, loki_net))
    ssh("cd %s && docker compose -f docker-compose.reuse.yml -p %s up -d --build" % (REMOTE, PROJECT))
    ssh("cd %s && docker compose -f docker-compose.reuse.yml -p %s ps" % (REMOTE, PROJECT), check=False)
    print("\nDONE. The bots now ship into your EXISTING Loki. Next:")
    print("  1) In your Grafana (godeyes.ai/observe): Dashboards -> New -> Import ->")
    print("     upload  obs/grafana/dashboards/assess.json  -> pick your existing Loki datasource -> Import.")
    print("  2) Send /auth on Telegram, then check the 'Colt Bots Observability' dashboard.")
    print("\nUntouched: firewall, Amnezia VPN, VideoDead, and your existing Grafana/Loki.")

def deploy_full(grafana_port, assume_yes):
    print("\n=== PRE-FLIGHT (read-only) ==="); inspect()
    if "USED" in sshout("(ss -tln 2>/dev/null||netstat -tln 2>/dev/null) | grep -E '[:.]%d[[:space:]]' >/dev/null && echo USED || echo FREE" % grafana_port):
        print("!! Grafana port %d already in use. Re-run with --grafana-port %d" % (grafana_port, grafana_port+1)); sys.exit(2)
    if not assume_yes and input("\nDeploy standalone stack incl. our OWN Grafana on localhost:%d? [y/N] " % grafana_port).strip().lower() != "y":
        print("Aborted."); return
    ensure_docker(); ensure_swap(); upload()
    ssh("cd %s && ([ -f .env ] || echo GRAFANA_PASSWORD=$(openssl rand -base64 24) > .env) && (grep -q '^GRAFANA_PORT=' .env || echo GRAFANA_PORT=%d >> .env) && grep -E '^GRAFANA_' .env" % (REMOTE, grafana_port))
    ssh("cd %s && docker compose -p %s up -d --build" % (REMOTE, PROJECT))
    ssh("cd %s && docker compose -p %s ps" % (REMOTE, PROJECT), check=False)
    print("\nGrafana on 127.0.0.1:%d — tunnel:  ssh %s@%s -L %d:localhost:%d" % (grafana_port, USER, HOST, grafana_port, grafana_port))

def deploy_ghcr(tag, owner, assume_yes):
    """Deploy pre-built, scanned GHCR images (no build on the droplet). Rollback = pass an older tag."""
    if not owner:
        sys.exit("!! --image-owner required, e.g. ghcr.io/feranicus/electronic")
    print("\n=== PRE-FLIGHT (read-only) ==="); inspect()
    name, net = discover_loki()
    loki_url = ("http://%s:3100/loki/api/v1/push" % name) if name else os.environ.get("LOKI_URL", "")
    loki_net = net or os.environ.get("LOKI_NETWORK", "")
    if not (loki_url and loki_net):
        sys.exit("!! could not resolve the existing Loki; set LOKI_URL / LOKI_NETWORK")
    print("\nDeploy: %s/{colttechbot,cassandra}:%s  ->  Loki %s (net %s)" % (owner, tag, loki_url, loki_net))
    if not assume_yes and input("Proceed (pull scanned images, no build)? [y/N] ").strip().lower() != "y":
        print("Aborted."); return
    ensure_docker(); ensure_swap(); upload()
    # optional private-registry login (public packages need no auth)
    tok, usr = os.environ.get("GHCR_TOKEN", ""), os.environ.get("GHCR_USER", "")
    if tok and usr:
        ssh("echo '%s' | docker login ghcr.io -u '%s' --password-stdin" % (tok, usr))
    ssh("cd %s && printf 'LOKI_URL=%s\\nLOKI_NETWORK=%s\\nIMAGE_OWNER=%s\\nIMAGE_TAG=%s\\n' > .env && cat .env"
        % (REMOTE, loki_url, loki_net, owner, tag))
    ssh("cd %s && docker compose -f docker-compose.ghcr.yml -p %s pull && docker compose -f docker-compose.ghcr.yml -p %s up -d"
        % (REMOTE, PROJECT, PROJECT))
    ssh("cd %s && docker compose -f docker-compose.ghcr.yml -p %s ps" % (REMOTE, PROJECT), check=False)
    print("\nDeployed tag %s. Rollback: python deploy.py --ghcr <older-sha> --image-owner %s" % (tag, owner))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="ship into your EXISTING Loki/Grafana (recommended)")
    ap.add_argument("--deploy", action="store_true", help="standalone: bring up our own Loki+Grafana too")
    ap.add_argument("--loki-url", default=os.environ.get("LOKI_URL", ""))
    ap.add_argument("--loki-network", default=os.environ.get("LOKI_NETWORK", ""))
    ap.add_argument("--grafana-port", type=int, default=int(os.environ.get("GRAFANA_PORT", "3000")))
    ap.add_argument("--ghcr", metavar="TAG", help="deploy pre-built GHCR images with this tag (no build)")
    ap.add_argument("--image-owner", default=os.environ.get("IMAGE_OWNER", ""))
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    print("Target: %s@%s  project=%s  remote=%s" % (USER, HOST, PROJECT, REMOTE))
    if a.ghcr: deploy_ghcr(a.ghcr, a.image_owner, a.yes)
    elif a.reuse: deploy_reuse(a.loki_url, a.loki_network, a.yes)
    elif a.deploy: deploy_full(a.grafana_port, a.yes)
    elif a.inspect: inspect()
    else: ap.print_help()

if __name__ == "__main__":
    main()
