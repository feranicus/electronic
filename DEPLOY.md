# Deploy the Colt bots to the DigitalOcean droplet — reuse your existing Grafana/Loki

Droplet `64.225.108.200` already runs **Amnezia VPN**, **VideoDead**, and a **Grafana + Loki**
stack (jobhuntwow / `godeyes.ai/observe`). We add **NO second observability stack** — the bots
ship their logs into your **existing Loki**, and you import one dashboard into your **existing
Grafana**. Everything else on the droplet is left untouched.

## Why it's safe next to Amnezia VPN / VideoDead / jobhuntwow
- **No firewall changes** (never runs `ufw`) — the VPN keeps working. Bots are outbound-only.
- **Reuse mode publishes nothing** — no new ports. Only a tiny promtail + the 2 bots.
- Isolated project `colt-stack`, unique `colt-*` container names, own network. Promtail joins
  your Loki's network **only to push logs**.
- **Never** stops/removes/prunes other containers. Installs Docker only if missing; swap only if none.

---

## A-to-Z (run on your Windows PC, from `C:\Python SW\Linkedin Scraper`)

Prereqs: SSH access to the droplet. Windows 10+ has `ssh`/`scp`/`tar`.
(If you use a key: `setx SSH_KEY "C:\Users\feran\.ssh\id_ed25519"`, reopen PowerShell.)

```powershell
# 1) LOOK — read-only. Lists Amnezia/VideoDead/jobhuntwow containers and finds your Loki. Changes nothing.
python deploy.py --inspect

# 2) DEPLOY in REUSE mode — auto-discovers your Loki container + network, ships into it.
python deploy.py --reuse

#    If auto-discovery can't find it, pass them explicitly (get the names from --inspect):
python deploy.py --reuse --loki-url http://loki:3100/loki/api/v1/push --loki-network jobhuntwow_default
```

The script: guarded Docker/swap → `tar` the project → `scp` to `/opt/colt-stack` →
writes `LOKI_URL`/`LOKI_NETWORK` → `docker compose -f docker-compose.reuse.yml -p colt-stack up -d --build`.

> Secrets (`assess-bot/.env`, `cassandra-bot/.env` — bot tokens, keys, `COLT_BOT_PASSWORD`,
> Google App Password) are uploaded over SSH and `chmod 600`. Never commit them.

---

## Import the dashboard into your EXISTING Grafana (one time)

In your Grafana (`godeyes.ai/observe`): **Dashboards → New → Import → Upload JSON file** →
choose `obs/grafana/dashboards/assess.json` → when prompted, pick your **existing Loki datasource**
→ **Import**. It appears as **"Colt Bots Observability"** and filters to the bots' streams
(`container="assess-bot"`, `bot="colttechbot|cassandra"`) so it won't mix with jobhuntwow panels.

---

## Verify

**Telegram** (test account, either bot):
1. `/auth name.familyname@colt.net <access-password>` → emails a 6-digit code
2. `/verify <code>` → authorized
3. colttechbot: `/assess sglcarbon.com --asn AS34386 --net 193.58.200.0/23`  ·  cassandra: `/research sglcarbon.com`

**Grafana:** open your existing Grafana → "Colt Bots Observability" → set range Last 6h. Auth/chat/
research/assessment events appear. (Confirm shipping: `docker logs colt-promtail` shows no push errors.)

---

## Operate / update
```bash
ssh root@64.225.108.200
cd /opt/colt-stack
docker compose -f docker-compose.reuse.yml -p colt-stack ps
docker compose -f docker-compose.reuse.yml -p colt-stack logs -f cassandra
docker compose -f docker-compose.reuse.yml -p colt-stack restart colttechbot cassandra
docker compose -f docker-compose.reuse.yml -p colt-stack down          # stops ONLY our 3 containers
```
Push new code later: just re-run `python deploy.py --reuse` from your PC.

## Notes
- **Memory:** 4 GB shared with Amnezia + VideoDead + jobhuntwow. Script adds 2 GB swap if none.
  If Chromium (`/research`) causes pressure, set `ENABLE_BROWSER=0` in `cassandra-bot/.env` and re-run.
- **Standalone fallback** (only if you had NO existing Grafana): `python deploy.py --deploy` brings up
  our own Loki+Grafana on `127.0.0.1:3000` (SSH-tunnel to reach). You don't need this — you have one.
