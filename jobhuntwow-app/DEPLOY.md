# JobHuntWOW app — deployment

Both halves live on the **same droplet** behind the shared videodead Caddy:
- **`jobhuntwow.com`** (static one-pager + Apps-Script tracker) → deployed by **`deploy_jobhuntwow_caddy.py`**
  (stages the build to `/opt/jobhuntwow/site`, mounts it into Caddy at `/srv/jobhuntwow`, adds the site
  block, validates, recreates the caddy container). Observability via **`deploy_jobhuntwow_obs.py`**.
  The repo's GitHub-Pages workflow is legacy — DNS A-records `jobhuntwow.com` → the droplet.
- **`app.jobhuntwow.com`** (this cabinet) → Docker (below).

## The cabinet (`jobhuntwow-app`)

Runs as Docker on the droplet, behind the shared Caddy, at **`app.jobhuntwow.com`**.

## One-time setup

1. **DNS (GoDaddy).** Point the app subdomain at the droplet:
   - `A  app  -> 64.225.108.200`  (or `CNAME app -> jobhuntwow.com` if the apex already A-records there).

2. **Secrets.** On the droplet, in the app folder:
   ```bash
   cp .env.example .env
   #  DO_INFERENCE_KEY=doo_v1_...      (your DigitalOcean Serverless Inference key)
   #  QWEN_MODEL=                       (blank = auto-pick first model)
   chmod 600 .env
   ```

3. **Caddy vhost.** Add the block from `Caddy-snippet.txt` to the droplet's Caddy config
   (`/opt/videodead/Caddyfile`) so it serves the app:
   ```
   app.jobhuntwow.com {
       encode gzip zstd
       reverse_proxy jhw_frontend:80      # or 127.0.0.1:8090 (the published port)
   }
   ```
   Then reload Caddy. If a reload reports "config unchanged" but you know it changed, use
   `caddy reload --config /etc/caddy/Caddyfile --force` (Caddy skips reloads whose config hash matches).
   If Caddy runs in a container, mount the Caddyfile's **directory**, not the single file (a single-file
   bind-mount pins the inode and editors save-and-swap, so the container never sees the change).

## Deploy / update

```bash
docker compose up -d --build           # build + (re)start backend + frontend
docker compose ps                      # backend (internal :8000) + frontend (8090:80)
```

- The frontend nginx proxies `/api` to the backend, so only the frontend port is exposed.
- Verify: `curl -s http://127.0.0.1:8090/api/health` should return OK, and
  `https://app.jobhuntwow.com` should load the cabinet.

## Networking notes (learned the hard way)
- Reverse-proxy to the **service name** on a shared Docker network (`reverse_proxy jhw_frontend:80`),
  not `127.0.0.1` — inside a container `127.0.0.1` is the container's own loopback, not the host.
- Keep the upstream container on **one** network. A container on two networks makes Docker DNS return
  two IPs and the proxy may dial the unreachable one → intermittent `502 Bad Gateway`.

## Backups
All app state is JSON on the `jhw_data` Docker volume:
```bash
docker run --rm -v jhw_data:/d -v "$PWD":/b alpine tar czf /b/jhw_data_backup.tgz -C /d .
```

## Rollback
Rebuild from a previous git tag/commit and `docker compose up -d --build`. The volume persists across
rebuilds; delete it only for a clean reset.
