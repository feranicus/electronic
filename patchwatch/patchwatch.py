#!/usr/bin/env python3
"""
patchwatch — backup-first, LLM-assisted auto-patcher for the DigitalOcean droplet.

Every run (driven by a systemd timer, ~every 3 days in a low-traffic window):
  1. INVENTORY   — upgradable apt packages, kernel status, Docker version, colt-stack image updates.
  2. BACKUP FIRST— (a) tar /etc + colt-stack compose/.env + named docker volumes -> DO Spaces (S3);
                   (b) optional full DO droplet snapshot via the API. Upgrade ABORTS if backup fails.
  3. UPGRADE     — apt-get full-upgrade (non-interactive, keep existing configs); refresh colt-stack
                   images only (Amnezia VPN / VideoDead / joplin are NOT touched — only OS/engine,
                   which they share, gets patched).
  4. DIGEST      — DeepSeek (your DO serverless endpoint) writes a plain-English risk summary and
                   flags kernel/CVE-class items (e.g. GhostLock / CVE-2026-43499).
  5. NOTIFY      — Telegram + a JSON line to events.log (promtail -> Loki -> Grafana).
  6. REBOOT      — if a kernel update left /run/reboot-required and REBOOT_MODE=auto, reboot at the
                   end of the run (the run itself is scheduled in the low-traffic window).

The LLM only SUMMARISES and assesses risk. It never decides whether to run apt or reboot — those are
deterministic. Config comes from /etc/patchwatch/patchwatch.env (see patchwatch.env.example).
No secret is ever hard-coded; everything sensitive is read from the environment on the droplet.
"""
import os, sys, json, time, subprocess, socket, tarfile, tempfile, datetime, uuid, contextlib, urllib.request, urllib.error

RUN_ID = uuid.uuid4().hex[:12]   # correlates every event of a single run

# ----------------------------------------------------------------------------- config
def env(k, d=""): return os.environ.get(k, d)

HOST          = socket.gethostname()
DRY_RUN       = env("PATCHWATCH_DRY_RUN", "0").lower() in ("1", "true", "yes")
FULL_UPGRADE  = env("UPGRADE_MODE", "full").lower() == "full"      # 'full' | 'security'
REBOOT_MODE   = env("REBOOT_MODE", "auto").lower()                 # 'auto' | 'notify'
REQUIRE_BACKUP= env("REQUIRE_BACKUP", "1").lower() in ("1", "true", "yes")

# Spaces (S3-compatible) — REQUIRED for the backup step
SPACES_ENDPOINT = env("SPACES_ENDPOINT")            # e.g. https://fra1.digitaloceanspaces.com
SPACES_REGION   = env("SPACES_REGION", "fra1")
SPACES_BUCKET   = env("SPACES_BUCKET")              # e.g. colt-backups
SPACES_KEY      = env("SPACES_KEY")
SPACES_SECRET   = env("SPACES_SECRET")
SPACES_PREFIX   = env("SPACES_PREFIX", "patchwatch")
BACKUP_KEEP     = int(env("BACKUP_KEEP", "6"))      # keep last N backups in Spaces

# Optional full-droplet snapshot via the DO API
DO_API_TOKEN  = env("DO_API_TOKEN")
DROPLET_ID    = env("DROPLET_ID")
SNAPSHOT_KEEP = int(env("SNAPSHOT_KEEP", "3"))

# What to back up (space-separated paths that exist on the droplet)
BACKUP_PATHS  = env("BACKUP_PATHS", "/etc /opt/colt-stack /root/colt-stack").split()
COMPOSE_PROJECT = env("COMPOSE_PROJECT", "colt-stack")

# LLM digest (reuse the DO serverless inference you already run)
LLM_KEY   = env("OPENAI_API_KEY")
LLM_BASE  = env("OPENAI_BASE_URL", "https://inference.do-ai.run/v1")
LLM_MODEL = env("PATCH_LLM_MODEL", env("ENRICH_MODEL", "deepseek-3.2"))
LLM_TIMEOUT = int(env("PATCH_LLM_TIMEOUT", "120"))

# Telegram digest
TG_TOKEN  = env("PATCH_TG_TOKEN", env("BOT_TOKEN"))
TG_CHAT   = env("PATCH_TG_CHAT")                    # your Telegram numeric chat id

# Write to the SAME file promtail tails (the colt_events docker volume), so events reach Loki/Grafana.
EVENTS_LOG = env("PATCH_EVENTS_LOG", "/var/lib/docker/volumes/colt-stack_colt_events/_data/events.log")

# ----------------------------------------------------------------------------- helpers
def log(evt, **kw):
    rec = {"ts": int(time.time()), "iso": datetime.datetime.utcnow().isoformat() + "Z",
           "bot": "patchwatch", "host": HOST, "run_id": RUN_ID, "evt": evt, **kw}
    line = json.dumps(rec, default=str)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(EVENTS_LOG), exist_ok=True)
        with open(EVENTS_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

@contextlib.contextmanager
def phase(name, **meta):
    """Emit start/done/error events with a duration so Grafana can render a progress timeline."""
    t0 = time.time()
    log(evt="phase", phase=name, state="start", **meta)
    try:
        yield
    except Exception as e:
        log(evt="phase", phase=name, state="error", dur_s=round(time.time() - t0, 1), err=str(e)[:200])
        raise
    else:
        log(evt="phase", phase=name, state="done", dur_s=round(time.time() - t0, 1))

def sh(cmd, timeout=1800, check=False):
    """Run a shell command, capture output."""
    p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}): {cmd}\n{p.stderr[:500]}")
    return p.returncode, (p.stdout or ""), (p.stderr or "")

def do_api(method, path, body=None):
    url = "https://api.digitalocean.com" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": "Bearer " + DO_API_TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode() or "{}")

# ----------------------------------------------------------------------------- 1) inventory
def inventory():
    inv = {}
    sh("apt-get update -qq")
    rc, out, _ = sh("apt-get -s -o Debug::NoLocking=true upgrade 2>/dev/null | grep -E '^Inst' || true")
    inv["upgradable"] = [l.split()[1] for l in out.splitlines() if l.startswith("Inst")]
    rc, out, _ = sh("apt-get -s dist-upgrade 2>/dev/null | grep -Ei 'linux-image|linux-headers' || true")
    inv["kernel_updates"] = [l.split()[1] for l in out.splitlines() if l.startswith("Inst")]
    _, out, _ = sh("uname -r"); inv["kernel_running"] = out.strip()
    _, out, _ = sh("docker --version 2>/dev/null || echo none"); inv["docker"] = out.strip()
    _, out, _ = sh("dpkg -l docker-ce 2>/dev/null | awk '/^ii/{print $3}' || true"); inv["docker_pkg"] = out.strip()
    inv["reboot_required_before"] = os.path.exists("/run/reboot-required")
    _, out, _ = sh("df -h / | tail -1 | awk '{print $5\" used, \"$4\" free\"}'"); inv["disk_root"] = out.strip()
    return inv

# ----------------------------------------------------------------------------- 2) backup
def backup_to_spaces():
    """tar the critical paths and upload to DO Spaces via boto3. Returns key or raises."""
    if not (SPACES_ENDPOINT and SPACES_BUCKET and SPACES_KEY and SPACES_SECRET):
        raise RuntimeError("Spaces not configured (SPACES_ENDPOINT/BUCKET/KEY/SECRET)")
    import boto3  # installed by the installer
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    key = f"{SPACES_PREFIX}/{HOST}/pre-upgrade-{stamp}.tar.gz"
    paths = [p for p in BACKUP_PATHS if os.path.exists(p)]
    # discover docker named volumes for the colt-stack project
    _, out, _ = sh(f"docker volume ls --format '{{{{.Name}}}}' | grep '^{COMPOSE_PROJECT}' || true")
    vols = [v for v in out.split() if v]
    stage = tempfile.mkdtemp(prefix="patchwatch-vols-")
    vol_files = []
    for v in vols:                          # dump each volume to a tarball via a throwaway container
        rc, _, err = sh(f"docker run --rm -v {v}:/vol:ro -v {stage}:/bk alpine "
                        f"tar czf /bk/{v}.tar.gz -C /vol . ")
        if rc == 0 and os.path.exists(os.path.join(stage, f"{v}.tar.gz")):
            vol_files.append(os.path.join(stage, f"{v}.tar.gz"))
        else:
            log("backup_volume_skip", volume=v, err=err[:120])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz"); tmp.close()
    with tarfile.open(tmp.name, "w:gz") as tar:     # single archive: paths + volume tarballs
        for p in paths:
            try: tar.add(p, arcname="fs/" + p.lstrip("/"))
            except Exception as e: log("backup_path_skip", path=p, err=str(e)[:120])
        for vf in vol_files:
            tar.add(vf, arcname="volumes/" + os.path.basename(vf))
    for vf in vol_files:
        try: os.unlink(vf)
        except Exception: pass
    try: os.rmdir(stage)
    except Exception: pass
    size = os.path.getsize(tmp.name)
    s3 = boto3.client("s3", region_name=SPACES_REGION, endpoint_url=SPACES_ENDPOINT,
                      aws_access_key_id=SPACES_KEY, aws_secret_access_key=SPACES_SECRET)
    if DRY_RUN:
        log("backup_dry_run", key=key, bytes=size); os.unlink(tmp.name); return key, size
    s3.upload_file(tmp.name, SPACES_BUCKET, key)
    os.unlink(tmp.name)
    log("backup_uploaded", key=key, bytes=size, volumes=vols)
    # prune old backups
    try:
        objs = s3.list_objects_v2(Bucket=SPACES_BUCKET, Prefix=f"{SPACES_PREFIX}/{HOST}/").get("Contents", [])
        old = sorted(objs, key=lambda o: o["LastModified"])[:-BACKUP_KEEP]
        for o in old:
            s3.delete_object(Bucket=SPACES_BUCKET, Key=o["Key"]); log("backup_pruned", key=o["Key"])
    except Exception as e:
        log("backup_prune_err", err=str(e)[:160])
    return key, size

def snapshot_droplet():
    """Optional full-image snapshot via DO API. Waits for completion. Returns action id or None."""
    if not (DO_API_TOKEN and DROPLET_ID):
        return None
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    if DRY_RUN:
        log("snapshot_dry_run", name=f"patchwatch-pre-{stamp}"); return "dry"
    _, resp = do_api("POST", f"/v2/droplets/{DROPLET_ID}/actions",
                     {"type": "snapshot", "name": f"patchwatch-pre-{stamp}"})
    action = resp.get("action", {}); aid = action.get("id")
    log("snapshot_started", action_id=aid, name=f"patchwatch-pre-{stamp}")
    # poll up to ~20 min
    for _ in range(80):
        time.sleep(15)
        try:
            _, st = do_api("GET", f"/v2/droplets/{DROPLET_ID}/actions/{aid}")
            if st.get("action", {}).get("status") == "completed":
                log("snapshot_completed", action_id=aid); break
            if st.get("action", {}).get("status") == "errored":
                raise RuntimeError("snapshot errored")
        except Exception as e:
            log("snapshot_poll_err", err=str(e)[:160])
    # prune old patchwatch snapshots
    try:
        _, snaps = do_api("GET", f"/v2/droplets/{DROPLET_ID}/snapshots?per_page=200")
        mine = [s for s in snaps.get("snapshots", []) if str(s.get("name", "")).startswith("patchwatch-pre-")]
        mine.sort(key=lambda s: s.get("created_at", ""))
        for s in mine[:-SNAPSHOT_KEEP]:
            do_api("DELETE", f"/v2/snapshots/{s['id']}"); log("snapshot_pruned", id=s["id"])
    except Exception as e:
        log("snapshot_prune_err", err=str(e)[:160])
    return aid

# ----------------------------------------------------------------------------- 3) upgrade
def upgrade(inv):
    results = {}
    envp = "DEBIAN_FRONTEND=noninteractive "
    opts = '-y -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef"'
    if DRY_RUN:
        results["apt"] = "dry-run (no changes)"
    elif FULL_UPGRADE:
        rc, out, err = sh(f"{envp} apt-get {opts} full-upgrade", timeout=3600)
        results["apt"] = "ok" if rc == 0 else f"rc={rc}: {err[-300:]}"
        results["upgraded_count"] = out.count("Setting up ")
        sh(f"{envp} apt-get {opts} autoremove --purge")
    else:  # security-only
        rc, out, err = sh(f"{envp} unattended-upgrade -v 2>&1 || {envp} apt-get {opts} upgrade", timeout=3600)
        results["apt"] = "ok" if rc == 0 else f"rc={rc}: {err[-300:]}"
        results["upgraded_count"] = out.count("Setting up ")
    # refresh ONLY the colt-stack images (do not touch amnezia/videodead/joplin)
    for cf in ("/opt/colt-stack/docker-compose.ghcr.yml", "/opt/colt-stack/docker-compose.reuse.yml",
               "/root/colt-stack/docker-compose.ghcr.yml"):
        if os.path.exists(cf) and not DRY_RUN:
            sh(f"docker compose -f {cf} -p {COMPOSE_PROJECT} pull", timeout=1200)
            sh(f"docker compose -f {cf} -p {COMPOSE_PROJECT} up -d", timeout=600)
            results["colt_images"] = f"refreshed via {cf}"
            break
    sh("docker image prune -f")
    results["reboot_required"] = os.path.exists("/run/reboot-required")
    return results

# ----------------------------------------------------------------------------- 4) LLM digest
def llm_digest(inv, upg, backup_key, snap):
    facts = {"host": HOST, "inventory": inv, "upgrade": upg,
             "backup_key": backup_key, "snapshot": bool(snap)}
    if not LLM_KEY:
        return ("(no LLM key configured) Upgraded packages: %d, kernel updates: %s, reboot required: %s."
                % (len(inv.get("upgradable", [])), inv.get("kernel_updates"), upg.get("reboot_required")))
    prompt = (
        "You are a Linux patch auditor for a DigitalOcean droplet that also runs a WireGuard-based VPN "
        "(Amnezia) and other services. Given this machine-generated data, write a SHORT plain-English "
        "digest (max ~150 words) for the admin: what was updated, whether any change is a KERNEL or "
        "CVE-class security fix (e.g. futex/use-after-free local-root bugs like GhostLock CVE-2026-43499), "
        "whether a reboot is needed and why, and any risk to the VPN or running services. Be factual, no "
        "fluff. End with one line: REBOOT: yes/no.\n\nDATA:\n" + json.dumps(facts, default=str)[:6000])
    body = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2, "max_tokens": 500}
    try:
        req = urllib.request.Request(LLM_BASE.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + LLM_KEY, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
            j = json.loads(r.read().decode())
        return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log("llm_err", err=str(e)[:200])
        return ("(LLM digest unavailable) upgradable=%d kernel=%s reboot=%s"
                % (len(inv.get("upgradable", [])), inv.get("kernel_updates"), upg.get("reboot_required")))

# ----------------------------------------------------------------------------- 5) notify
def notify_telegram(text):
    if not (TG_TOKEN and TG_CHAT):
        return
    try:
        body = json.dumps({"chat_id": TG_CHAT, "text": text[:3900],
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30)
        log("notify_telegram", result="ok")
    except Exception as e:
        log("notify_telegram", result="err", err=str(e)[:160])

# ----------------------------------------------------------------------------- main
def main():
    if os.geteuid() != 0 and not DRY_RUN:
        sys.exit("patchwatch must run as root (needs apt + reboot).")
    t_run = time.time()
    log("run_start", dry_run=DRY_RUN, upgrade_mode="full" if FULL_UPGRADE else "security",
        reboot_mode=REBOOT_MODE)

    with phase("inventory"):
        inv = inventory()
    log("inventory", upgradable_count=len(inv["upgradable"]), kernel_update_count=len(inv["kernel_updates"]),
        **{k: inv[k] for k in ("upgradable", "kernel_updates", "kernel_running",
                               "docker", "reboot_required_before", "disk_root")})

    nothing = not inv["upgradable"] and not inv["kernel_updates"]
    if nothing:
        log("metrics", upgradable_count=0, kernel_update_count=0, upgraded_count=0,
            backup_bytes=0, reboot_required=0, changed=0, duration_s=round(time.time() - t_run, 1))
        log("run_end", changed=False, note="already up to date")
        notify_telegram(f"🟢 patchwatch @{HOST}: nothing to update. Kernel {inv['kernel_running']}.")
        return

    # 2) BACKUP FIRST — abort the whole run if it fails and REQUIRE_BACKUP is on
    backup_key, snap, backup_bytes = None, None, 0
    try:
        with phase("backup_spaces", volumes_project=COMPOSE_PROJECT):
            backup_key, backup_bytes = backup_to_spaces()
        with phase("snapshot_droplet"):
            snap = snapshot_droplet()
    except Exception as e:
        log("backup_failed", err=str(e)[:300])
        if REQUIRE_BACKUP:
            notify_telegram(f"🛑 patchwatch @{HOST}: BACKUP FAILED ({str(e)[:150]}). "
                            f"No packages were touched. Fix Spaces/DO creds and it will retry next cycle.")
            log("metrics", upgradable_count=len(inv["upgradable"]), kernel_update_count=len(inv["kernel_updates"]),
                upgraded_count=0, backup_bytes=0, reboot_required=0, changed=0, aborted=1,
                duration_s=round(time.time() - t_run, 1))
            log("run_end", changed=False, aborted="backup_failed")
            return

    # 3) UPGRADE
    with phase("upgrade", upgrade_mode="full" if FULL_UPGRADE else "security"):
        upg = upgrade(inv)
    log("upgrade_done", **upg)

    # 4) DIGEST + 5) NOTIFY
    with phase("digest"):
        digest = llm_digest(inv, upg, backup_key, snap)
    reboot_needed = upg.get("reboot_required")
    header = f"🩹 patchwatch @{HOST} — {len(inv['upgradable'])} pkg(s) updated"
    if inv["kernel_updates"]:
        header += f", KERNEL patched ({', '.join(inv['kernel_updates'])})"
    tail = "\n\n⚠️ Reboot required." if reboot_needed else ""
    if reboot_needed and REBOOT_MODE == "auto":
        tail += " Rebooting now (low-traffic window; Docker services auto-restart, VPN reconnects)."
    with phase("notify"):
        notify_telegram(f"{header}\n\n{digest}\n\nBackup: {backup_key or 'n/a'}"
                        f"{' + DO snapshot' if snap else ''}{tail}")

    # numeric summary for the dashboard gauges/trends
    log("metrics",
        upgradable_count=len(inv["upgradable"]), kernel_update_count=len(inv["kernel_updates"]),
        upgraded_count=int(upg.get("upgraded_count", 0)), backup_bytes=int(backup_bytes),
        snapshot=1 if snap else 0, reboot_required=1 if reboot_needed else 0, changed=1,
        duration_s=round(time.time() - t_run, 1))

    # 6) REBOOT
    if reboot_needed and REBOOT_MODE == "auto" and not DRY_RUN:
        log("rebooting", reason="kernel/lib update requires reboot")
        sh("shutdown -r +1 'patchwatch: applying kernel/security update'")
    log("run_end", changed=True, reboot_required=reboot_needed,
        reboot_action="auto" if (reboot_needed and REBOOT_MODE == "auto") else "notify-only")

if __name__ == "__main__":
    main()
