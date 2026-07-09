# patchwatch — backup-first auto-patcher for the droplet

Keeps the DigitalOcean droplet current (kernel/OS/Docker + colt-stack images) on a ~3-day cycle,
**after taking a backup**, and sends a DeepSeek-written plain-English digest. Built to close the
local-root / container-escape kernel bugs that keep landing in 2026 (e.g. GhostLock, CVE-2026-43499,
which needs a kernel update **and a reboot** to take effect).

## What each run does

1. **Inventory** — upgradable apt packages, pending kernel updates, Docker version, disk headroom.
2. **Backup first** — tars `/etc` + the colt-stack compose/`.env` + the colt-stack Docker volumes and
   uploads to **DO Spaces**; optionally takes a **full droplet snapshot** via the DO API. If the backup
   fails and `REQUIRE_BACKUP=1`, the run **aborts before touching any package**.
3. **Upgrade** — `apt-get full-upgrade` (non-interactive, keeps your existing config files), then
   refreshes **only the colt-stack** container images. Amnezia VPN / VideoDead / joplin images are never
   pulled or recreated — they only get the shared OS/engine patch.
4. **Digest** — DeepSeek summarises what changed, flags kernel/CVE-class fixes, and says whether a reboot
   is needed.
5. **Notify** — Telegram message + a JSON line to `events.log` (promtail → Loki → Grafana, `bot=patchwatch`).
6. **Reboot** — if a kernel update set `/run/reboot-required` and `REBOOT_MODE=auto`, it reboots at the end
   of the run. The run is scheduled at 04:17 UTC so this lands in a low-traffic window; Docker services
   auto-restart and the VPN reconnects.

The LLM **only writes the digest and assesses risk** — it never decides whether to run `apt` or reboot.
Those are deterministic. That keeps an LLM from ever YOLO-ing a production upgrade.

## Install

```bash
# from this folder, with SSH access to the droplet (ssh-agent recommended)
python install_patchwatch.py            # upload + enable the 3-day timer
```

Then, **once**, SSH in and fill `/etc/patchwatch/patchwatch.env` (see `patchwatch.env.example`):

- **Spaces** (required): `SPACES_ENDPOINT`, `SPACES_BUCKET`, `SPACES_KEY`, `SPACES_SECRET`
- **DO snapshot** (optional): `DO_API_TOKEN`, `DROPLET_ID`
- **Telegram**: `PATCH_TG_CHAT` (your numeric chat id; `PATCH_TG_TOKEN` can reuse colttechbot's)
- DeepSeek keys are inherited from `/opt/colt-stack/.env` if already present

Secrets live **only** on the droplet in that file (`chmod 600`); nothing sensitive is in git.

## Test safely before trusting it

```bash
python install_patchwatch.py --dry-test    # inventories + shows would-be actions, changes NOTHING
```

Flip `PATCHWATCH_DRY_RUN=0` in the env file when you're happy.

## Knobs (`/etc/patchwatch/patchwatch.env`)

| Var | Default | Meaning |
|-----|---------|---------|
| `UPGRADE_MODE` | `full` | `full` upgrades everything; `security` = security pocket only |
| `REBOOT_MODE` | `auto` | `auto` reboots in-window when the kernel needs it; `notify` just tells you |
| `REQUIRE_BACKUP` | `1` | abort the upgrade if the backup fails |
| `BACKUP_KEEP` / `SNAPSHOT_KEEP` | `6` / `3` | how many backups/snapshots to retain |

## Rollback

- **Config/data**: download the newest `patchwatch/<host>/pre-upgrade-*.tar.gz` from your Space and
  extract (`fs/` = filesystem paths, `volumes/` = per-volume tarballs).
- **Whole droplet**: in the DO console, restore the `patchwatch-pre-*` snapshot (or rebuild the droplet
  from it). This reverts a bad kernel/OS upgrade completely.

## Verify it's scheduled

```bash
systemctl list-timers patchwatch.timer
journalctl -u patchwatch.service -n 50
```
