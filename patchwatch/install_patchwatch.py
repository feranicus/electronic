#!/usr/bin/env python3
"""
install_patchwatch.py — deploy the patchwatch auto-patcher onto the droplet over SSH.

It uploads patchwatch.py + the systemd units, installs boto3/requests, drops an env template
at /etc/patchwatch/patchwatch.env (only if missing — it never overwrites your filled-in secrets),
and enables the timer. Non-destructive: touches nothing that belongs to Amnezia/VideoDead/joplin.

Usage (from this folder):
    python install_patchwatch.py                 # install + enable timer
    python install_patchwatch.py --dry-test      # install, then run ONE dry-run pass (no changes)
    python install_patchwatch.py --run-now        # install, then trigger a real run immediately

Host/user/key come from flags or the same env you use for deploy.py.
"""
import argparse, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))

SSH_BASE = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
if KEY and os.path.exists(KEY):
    SSH_BASE += ["-i", KEY]

def ssh(cmd):
    full = SSH_BASE + [f"{USER}@{HOST}", cmd]
    print("  $ " + cmd)
    r = subprocess.run(full)
    if r.returncode != 0:
        sys.exit(f"[X] remote command failed ({r.returncode})")

def scp(local, remote):
    base = ["scp", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
    if KEY and os.path.exists(KEY):
        base += ["-i", KEY]
    print(f"  scp {os.path.basename(local)} -> {remote}")
    r = subprocess.run(base + [local, f"{USER}@{HOST}:{remote}"])
    if r.returncode != 0:
        sys.exit(f"[X] scp failed for {local}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-test", action="store_true", help="after install, run one dry-run pass")
    ap.add_argument("--run-now", action="store_true", help="after install, trigger a real run now")
    a = ap.parse_args()

    print(f"Target: {USER}@{HOST}")
    print("=== 1) directories ===")
    ssh("mkdir -p /opt/patchwatch /etc/patchwatch /opt/colt-stack/observe")

    print("=== 2) upload script + units ===")
    scp(os.path.join(HERE, "patchwatch.py"),       "/opt/patchwatch/patchwatch.py")
    scp(os.path.join(HERE, "patchwatch.service"),  "/etc/systemd/system/patchwatch.service")
    scp(os.path.join(HERE, "patchwatch.timer"),    "/etc/systemd/system/patchwatch.timer")
    # env template only if the real one doesn't exist yet (don't clobber secrets)
    scp(os.path.join(HERE, "patchwatch.env.example"), "/etc/patchwatch/patchwatch.env.example")
    ssh("test -f /etc/patchwatch/patchwatch.env || cp /etc/patchwatch/patchwatch.env.example /etc/patchwatch/patchwatch.env")
    ssh("chmod 600 /etc/patchwatch/patchwatch.env")

    print("=== 3) dependencies (boto3 for Spaces) ===")
    ssh("python3 -m pip install --quiet --break-system-packages boto3 requests 2>/dev/null || "
        "pip3 install --quiet boto3 requests")

    print("=== 4) enable timer ===")
    ssh("systemctl daemon-reload && systemctl enable --now patchwatch.timer")
    ssh("systemctl list-timers patchwatch.timer --no-pager || true")

    if a.dry_test:
        print("=== 5) DRY-RUN pass (no changes) ===")
        ssh("PATCHWATCH_DRY_RUN=1 systemd-run --wait --collect --pipe "
            "-p EnvironmentFile=/etc/patchwatch/patchwatch.env "
            "-p EnvironmentFile=-/opt/colt-stack/.env "
            "/usr/bin/python3 /opt/patchwatch/patchwatch.py || true")
    elif a.run_now:
        print("=== 5) real run now ===")
        ssh("systemctl start patchwatch.service && journalctl -u patchwatch.service -n 40 --no-pager")

    print("\n" + "=" * 60)
    print("patchwatch installed. NEXT (once):")
    print("  1) SSH in and fill /etc/patchwatch/patchwatch.env  (Spaces keys, DO token, Telegram chat id)")
    print("  2) Test safely:   python install_patchwatch.py --dry-test")
    print("  3) Timer runs every 3 days at 04:17 UTC. Manual run: systemctl start patchwatch.service")
    print("  Logs: journalctl -u patchwatch.service   |   Grafana (bot=patchwatch)")
    print("=" * 60)

if __name__ == "__main__":
    main()
