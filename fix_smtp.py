#!/usr/bin/env python3
"""
fix_smtp.py — one-shot fix + verify for the cassandra "Network is unreachable" SMTP error.

Root cause: the container resolves smtp.gmail.com to IPv6 (AAAA) but the Docker bridge has no
IPv6 -> OSError(101). The shared auth module now FORCES IPv4 for SMTP. This script:
  1) diagnoses inside colt-cassandra (IPv4 vs IPv6 reachability + an IPv4-forced SMTP login),
  2) ships the patched colt_auth.py and rebuilds BOTH bots (Chromium layer stays cached -> fast),
  3) re-verifies SMTP login from the fresh container.
Touches ONLY the colt-* containers. No firewall / other-service changes.

Run from  C:\\Python SW\\Linkedin Scraper :   python fix_smtp.py
Env: DROPLET_HOST, DROPLET_USER, SSH_KEY.
"""
import os, subprocess, sys, tempfile

HOST    = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER    = os.environ.get("DROPLET_USER", "root")
SSH_KEY = os.environ.get("SSH_KEY", "")
REMOTE  = "/opt/colt-stack"
PROJECT = "colt-stack"
LOCAL   = os.path.dirname(os.path.abspath(__file__))
SSH_OPTS = (["-i", SSH_KEY] if SSH_KEY else []) + ["-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4", "-o", "LogLevel=ERROR"]

DIAG = r'''
import os, socket, ssl, smtplib
print("== connectivity to smtp.gmail.com:587 ==")
for fam, name in ((socket.AF_INET, "IPv4"), (socket.AF_INET6, "IPv6")):
    try:
        a = socket.getaddrinfo("smtp.gmail.com", 587, fam, socket.SOCK_STREAM)[0][4]
        s = socket.create_connection(a[:2], timeout=8); s.close()
        print("  ", name, "OK ->", a[0])
    except Exception as e:
        print("  ", name, "FAIL ->", repr(e))
print("== IPv4-forced SMTP login (uses this container's SMTP_* env) ==")
_g = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, f=0, t=0, pr=0, fl=0: _g(h, p, socket.AF_INET, t, pr, fl)
try:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com"); port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as s:
        s.starttls(context=ssl.create_default_context()); s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        print("   SMTP LOGIN OK  (IPv4 + STARTTLS + app-password all good)")
except KeyError as e:
    print("   SMTP env missing:", e, "-> the container has no SMTP creds")
except Exception as e:
    print("   SMTP LOGIN FAIL ->", repr(e))
'''

def run(cmd, check=True):
    print("  $ " + " ".join(cmd)); r = subprocess.run(cmd)
    if check and r.returncode != 0: sys.exit("!! failed (%d)" % r.returncode)
    return r
def ssh(cmd, check=True): return run(["ssh", *SSH_OPTS, "%s@%s" % (USER, HOST), cmd], check=check)
def scp(local, remote): return run(["scp", *SSH_OPTS, local, "%s@%s:%s" % (USER, HOST, remote)])

def run_diag(tag):
    print("\n=== %s: diagnostics inside colt-cassandra ===" % tag)
    ssh("docker cp /tmp/colt_smtp_diag.py colt-cassandra:/tmp/colt_smtp_diag.py && "
        "docker exec colt-cassandra python3 /tmp/colt_smtp_diag.py", check=False)

def main():
    print("Target: %s@%s  (fixing SMTP IPv4 for colt-cassandra + colt-assessbot)" % (USER, HOST))
    # upload the diagnostic once
    tf = os.path.join(tempfile.gettempdir(), "colt_smtp_diag.py")
    open(tf, "w").write(DIAG); scp(tf, "/tmp/colt_smtp_diag.py")

    run_diag("BEFORE (current container)")

    print("\n=== shipping the IPv4 fix (colt_auth.py) + rebuilding both bots ===")
    scp(os.path.join(LOCAL, "colt_auth.py"), REMOTE + "/colt_auth.py")
    # rebuild only rewrites the small COPY layer; Chromium/pip layers stay cached -> quick
    ssh("cd %s && docker compose -f docker-compose.reuse.yml -p %s up -d --build colttechbot cassandra" % (REMOTE, PROJECT))

    run_diag("AFTER (fresh container)")

    print("\nDONE. If AFTER shows 'SMTP LOGIN OK', the bots can now email codes.")
    print("Next: on Telegram send  /auth <your colt email> <password>  to cassandra -> you should get the code.")
    print("Untouched: firewall, Amnezia VPN, VideoDead, joplin, your Grafana/Loki.")

if __name__ == "__main__":
    main()
