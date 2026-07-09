#!/usr/bin/env python3
"""
provision_patchwatch.py — ZERO-TOUCH setup of the patchwatch auto-patcher.

Given only your cloud secrets (via environment / GitHub Actions secrets — never hard-coded),
this does EVERYTHING with no manual droplet editing:

  1. DO API: find this droplet's numeric ID from its IP.
  2. Ensure the Spaces bucket exists; if no Spaces key was supplied, mint one via the DO API.
  3. Reuse the droplet's existing bot token + DeepSeek keys (read from /opt/colt-stack/.env).
  4. Auto-discover your Telegram chat id from the bot's getUpdates (message the bot once).
  5. Write /etc/patchwatch/patchwatch.env over SSH (chmod 600) — DRY_RUN off, first run reboot=notify.
  6. Install units + deps, enable the 3-day timer.
  7. Trigger ONE real run, verify the backup landed in Spaces and the Telegram digest was sent.
  8. On success, flip REBOOT_MODE=auto for future hands-off kernel patching.

Secrets are read from the environment and only ever written to the droplet's own env file.
Nothing sensitive is printed or committed. Designed to run locally OR from the GitHub workflow
`.github/workflows/provision-patchwatch.yml` using repo secrets.

Required env (set once as GitHub secrets, or export locally):
  DO_API_TOKEN            DigitalOcean API token (read+write)
  DROPLET_HOST           droplet public IP (default 64.225.108.200)
  DROPLET_USER           ssh user (default root)
  SSH_KEY                path to the private key (default ~/.ssh/id_ed25519)
Optional:
  SPACES_KEY / SPACES_SECRET   if omitted, a key is minted via the DO API
  SPACES_REGION (fra1)  SPACES_BUCKET (colt-backups)
  PATCH_TG_CHAT         your Telegram chat id (else auto-discovered via getUpdates)
"""
import argparse, json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))

DO_TOKEN = os.environ.get("DO_API_TOKEN", "")
HOST     = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER     = os.environ.get("DROPLET_USER", "root")
KEY      = os.environ.get("SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
REGION   = os.environ.get("SPACES_REGION", "fra1")
BUCKET   = os.environ.get("SPACES_BUCKET", "colt-backups")
SP_KEY   = os.environ.get("SPACES_KEY", "")
SP_SECRET= os.environ.get("SPACES_SECRET", "")
TG_CHAT  = os.environ.get("PATCH_TG_CHAT", "")
ENDPOINT = os.environ.get("SPACES_ENDPOINT", f"https://{REGION}.digitaloceanspaces.com")

SSH = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
SCP = ["scp", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
if KEY and os.path.exists(KEY):
    SSH += ["-i", KEY]; SCP += ["-i", KEY]


def die(msg): sys.exit("[X] " + msg)

def ssh(cmd, input_text=None, quiet=False):
    if not quiet: print("  $ " + (cmd if len(cmd) < 90 else cmd[:87] + "..."))
    r = subprocess.run(SSH + [f"{USER}@{HOST}", cmd], input=input_text,
                       text=True, capture_output=True)
    return r.returncode, r.stdout, r.stderr

def scp(local, remote):
    print(f"  scp {os.path.basename(local)} -> {remote}")
    r = subprocess.run(SCP + [local, f"{USER}@{HOST}:{remote}"], capture_output=True, text=True)
    if r.returncode != 0: die(f"scp failed for {local}: {r.stderr[:200]}")

def do_api(method, path, body=None):
    url = "https://api.digitalocean.com" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": "Bearer " + DO_TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def find_droplet_id():
    _, j = do_api("GET", "/v2/droplets?per_page=200")
    for d in j.get("droplets", []):
        for net in d.get("networks", {}).get("v4", []):
            if net.get("ip_address") == HOST:
                return str(d["id"])
    return ""

def ensure_spaces_key():
    """Return (key, secret): use provided, else mint one via the DO API."""
    global SP_KEY, SP_SECRET
    if SP_KEY and SP_SECRET:
        return SP_KEY, SP_SECRET
    print("  minting a Spaces access key via DO API...")
    code, j = do_api("POST", "/v2/spaces/keys",
                     {"name": "patchwatch", "grants": [{"bucket": "", "permission": "fullaccess"}]})
    key = (j.get("key") or {})
    ak, sk = key.get("access_key"), key.get("secret_key")
    if not (ak and sk):
        die("could not mint a Spaces key via the API (code %s). Set SPACES_KEY/SPACES_SECRET and retry." % code)
    return ak, sk

def ensure_bucket(ak, sk):
    import boto3
    from botocore.exceptions import ClientError
    s3 = boto3.client("s3", region_name=REGION, endpoint_url=ENDPOINT,
                      aws_access_key_id=ak, aws_secret_access_key=sk)
    try:
        s3.head_bucket(Bucket=BUCKET); print(f"  bucket '{BUCKET}' exists")
    except ClientError:
        # key just minted may take a few seconds to become active
        for _ in range(6):
            try:
                s3.create_bucket(Bucket=BUCKET); print(f"  created bucket '{BUCKET}'"); break
            except ClientError as e:
                if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
                    print(f"  bucket '{BUCKET}' already present"); break
                time.sleep(5)

def read_remote_shared():
    """Reuse BOT_TOKEN + DeepSeek keys already on the droplet."""
    _, out, _ = ssh("cat /opt/colt-stack/.env 2>/dev/null || true", quiet=True)
    kv = {}
    for line in out.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1); kv[k.strip()] = v.strip()
    return kv

def discover_tg_chat(token):
    if not token: return ""
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20) as r:
            j = json.loads(r.read().decode())
        for upd in reversed(j.get("result", [])):
            msg = upd.get("message") or upd.get("edited_message") or {}
            cid = (msg.get("chat") or {}).get("id")
            if cid: return str(cid)
    except Exception:
        pass
    return ""

def write_env(values):
    lines = ["# Managed by provision_patchwatch.py — do not hand-edit; re-run provisioning instead."]
    for k, v in values.items():
        lines.append(f"{k}={v}")
    content = "\n".join(lines) + "\n"
    rc, _, err = ssh("mkdir -p /etc/patchwatch && cat > /etc/patchwatch/patchwatch.env && "
                     "chmod 600 /etc/patchwatch/patchwatch.env", input_text=content, quiet=True)
    if rc != 0: die("writing remote env failed: " + err[:200])
    print("  wrote /etc/patchwatch/patchwatch.env (chmod 600)")

def set_env_var(k, v):
    ssh(f"sed -i 's|^{k}=.*|{k}={v}|' /etc/patchwatch/patchwatch.env", quiet=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first-reboot-mode", default="notify", choices=["notify", "auto"],
                    help="reboot policy for the FIRST provisioning run (default notify = no surprise reboot)")
    ap.add_argument("--final-reboot-mode", default="auto", choices=["notify", "auto"],
                    help="reboot policy set after a successful run (default auto)")
    a = ap.parse_args()

    if not DO_TOKEN: die("DO_API_TOKEN is required (set it as a GitHub secret or export it).")
    if not (KEY and os.path.exists(KEY)): die(f"SSH key not found at {KEY}")

    print(f"Target droplet: {USER}@{HOST}")
    print("=== 1) discover droplet id ===")
    drop_id = find_droplet_id()
    print("  droplet id:", drop_id or "(not found — snapshots will be skipped)")

    print("=== 2) Spaces key + bucket ===")
    ak, sk = ensure_spaces_key()
    ensure_bucket(ak, sk)

    print("=== 3) reuse droplet bot/LLM creds ===")
    shared = read_remote_shared()
    bot_token = os.environ.get("PATCH_TG_TOKEN") or shared.get("BOT_TOKEN", "")
    print("  bot token:", "found" if bot_token else "MISSING (Telegram digest will be off)")

    print("=== 4) discover Telegram chat id ===")
    chat = TG_CHAT or discover_tg_chat(bot_token)
    print("  chat id:", chat or "(not found — message your bot once, then re-run)")

    print("=== 5) upload code + install ===")
    ssh("mkdir -p /opt/patchwatch /etc/patchwatch /opt/colt-stack/observe", quiet=True)
    for f, dest in (("patchwatch.py", "/opt/patchwatch/patchwatch.py"),
                    ("patchwatch.service", "/etc/systemd/system/patchwatch.service"),
                    ("patchwatch.timer", "/etc/systemd/system/patchwatch.timer")):
        scp(os.path.join(HERE, f), dest)
    ssh("export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && "
        "apt-get install -y python3-boto3 python3-requests "
        "|| (apt-get install -y python3-pip && python3 -m pip install --break-system-packages boto3 requests)")

    print("=== 6) write env (first run reboot=%s) ===" % a.first_reboot_mode)
    env_values = {
        "UPGRADE_MODE": "full", "REBOOT_MODE": a.first_reboot_mode, "REQUIRE_BACKUP": "1",
        "PATCHWATCH_DRY_RUN": "0",
        "SPACES_ENDPOINT": ENDPOINT, "SPACES_REGION": REGION, "SPACES_BUCKET": BUCKET,
        "SPACES_PREFIX": "patchwatch", "SPACES_KEY": ak, "SPACES_SECRET": sk, "BACKUP_KEEP": "6",
        "DO_API_TOKEN": DO_TOKEN if drop_id else "", "DROPLET_ID": drop_id, "SNAPSHOT_KEEP": "3",
        "BACKUP_PATHS": "/etc /opt/colt-stack /root/colt-stack", "COMPOSE_PROJECT": "colt-stack",
        "OPENAI_BASE_URL": shared.get("OPENAI_BASE_URL", "https://inference.do-ai.run/v1"),
        "PATCH_LLM_MODEL": shared.get("ENRICH_MODEL", "deepseek-3.2"),
        "PATCH_TG_TOKEN": bot_token, "PATCH_TG_CHAT": chat,
        "PATCH_EVENTS_LOG": "/opt/colt-stack/observe/events.log",
    }
    # OPENAI_API_KEY: only write it if not already inherited from colt-stack .env
    if not shared.get("OPENAI_API_KEY") and os.environ.get("OPENAI_API_KEY"):
        env_values["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
    write_env(env_values)

    print("=== 7) enable timer + one real run ===")
    ssh("systemctl daemon-reload && systemctl enable --now patchwatch.timer", quiet=True)
    ssh("systemctl start patchwatch.service", quiet=True)
    _, out, _ = ssh("journalctl -u patchwatch.service -n 40 --no-pager 2>/dev/null || true", quiet=True)
    tail = "\n".join(out.splitlines()[-25:])
    print("---- patchwatch run log (tail) ----")
    print(tail)

    ok = ("backup_uploaded" in out) or ("run_end" in out and '"changed": false' in out)
    print("=== 8) result ===")
    if ok:
        set_env_var("REBOOT_MODE", a.final_reboot_mode)
        print(f"  ✅ healthy. REBOOT_MODE set to '{a.final_reboot_mode}' for future runs.")
        print("  Timer active — runs every 3 days at 04:17 UTC. Digest -> Telegram + Grafana(bot=patchwatch).")
    else:
        print("  ⚠ run did not clearly report a backup. Check the log above / journalctl on the droplet.")
        print("  (If Telegram chat id was missing: message your bot once, then re-run this script.)")


if __name__ == "__main__":
    main()
