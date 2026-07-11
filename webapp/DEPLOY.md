# cybergod.ai — how it is built and deployed (single source of truth)

This is the documented, version-controlled way cybergod.ai goes live. No ad-hoc SSH edits.
Everything below is code in this repo; GitHub builds and ships it to the droplet.

## Architecture (one host, one domain)

```
Browser ──HTTPS──> cybergod.ai (A-record → droplet 64.225.108.200)
                      │
             videodead-caddy  (already owns :80/:443, auto-TLS via Let's Encrypt)
                      │  reverse_proxy colt-web:8000   (deploy/caddy/cybergod.caddy)
                      ▼
                  colt-web  (FastAPI + built React app)  — landing, /login, cabinet
```

- **DNS:** GoDaddy → A `@` and `www` → `64.225.108.200`. That is the ONLY human DNS step, done once.
- **TLS:** the existing `videodead-caddy` container terminates TLS and fetches the cert on demand.
- **Isolation:** `colt-web` joins the existing `videodead_appnet` network so Caddy can reach it by
  name. VideoDead / Amnezia / joplin are never modified. The vhost is a separate managed block.

## Build + deploy pipeline (GitHub → droplet)

`/.github/workflows/web-deploy.yml` runs on any push to `webapp/**`, `deploy/caddy/**`,
`docker-compose.web.yml`, or `colt_auth.py` (or via "Run workflow"):

1. **build** — GitHub builds `webapp/Dockerfile` and pushes `ghcr.io/feranicus/colt-web:latest`
   and `:<sha>` to GHCR. The droplet never builds (saves its 3.8 GB RAM).
2. **deploy** — GitHub joins Tailscale, SSHes the droplet, and:
   - `docker compose -p colt-stack -f docker-compose.web.yml pull && up -d` (pulls the new image),
   - appends the committed `deploy/caddy/cybergod.caddy` block into `videodead`'s Caddyfile
     between `# colt:cybergod BEGIN/END` markers (idempotent — old block removed first),
   - `caddy reload` (graceful; other sites keep serving),
   - verifies `https://cybergod.ai/api/me` returns `401` (up + auth working).

Rollback = re-run the workflow pinned to an older image `:<sha>`.

## One-time setup (do each once, then never again)

1. **DNS** (GoDaddy → cybergod.ai → DNS): `A @ → 64.225.108.200`, `A www → 64.225.108.200`.
   Remove any GitHub-Pages `A` records (185.199.108–111.153) and the `www` CNAME to GitHub.
2. **Release the domain from GitHub Pages** so it stops competing with the droplet:
   run `python webapp/unpublish_pages.py`, AND in `github.com/feranicus/feranicus` →
   Settings → Pages, clear the **Custom domain** field (or disable Pages).
3. **GHCR package visibility:** after the first CI build, open the `colt-web` package on GitHub →
   Package settings → make it **Public** (so the droplet pulls with no auth). Or leave it private —
   the deploy step logs in with the workflow token.
4. **GitHub secrets/vars** (already used by the workflow): secret `TS_AUTHKEY` (Tailscale auth key),
   `DROPLET_SSH_KEY`, `DROPLET_USER`; var `TAILNET_HOST` (default `100.78.224.75`).

## Files (what to edit for what)

| Want to change…                    | Edit this (then push)                         |
|------------------------------------|-----------------------------------------------|
| The web app (login, cabinet, API)  | `webapp/frontend/**`, `webapp/backend/**`     |
| The reverse-proxy / vhost          | `deploy/caddy/cybergod.caddy`                 |
| The container / image / ports      | `docker-compose.web.yml`, `webapp/Dockerfile` |
| The build/deploy pipeline          | `.github/workflows/web-deploy.yml`            |

## Do NOT

- Do **not** run `publish_landing.py` for cybergod.ai anymore — it re-adds the GitHub-Pages CNAME
  and re-claims the domain (that was the 404/502 flip-flop). The landing is served by the droplet.
- Do **not** hand-edit the Caddyfile on the droplet — change `deploy/caddy/cybergod.caddy` and push.


## Observability (Grafana)

`colt-web` emits one JSON event per meaningful action — logins (via `colt_auth`), `assess_request`,
`assist_query` — to `/var/log/colt/events.log` on the shared `colt_events` volume (env `EVENTS_LOG`,
`SERVICE=colt-web`). The existing `colt-promtail` already tails that file, so events flow to
**Loki -> Grafana** with no extra agent. Labels: `service=colt-web`, `bot=webapp`, `evt=...`.

- Dashboard: `obs/grafana/dashboards/webapp.json` ("Colt Web (cybergod.ai)") — logins/denials,
  assessments, assistant queries, and a live event stream. It auto-imports on push via
  `.github/workflows/import-dashboards.yml`. Manual: `python import_dashboard.py --all`.
- Queries use `{container=~".*assess-bot.*"} | json | service=` + "`colt-web`" so they parse the JSON at
  query time (works regardless of which promtail labels are live).
