# assess-bot Observability Stack (Loki + Promtail + Grafana)

Local, self-contained log observability for the `assess-bot` Telegram container.
Mirrors the DigitalOcean droplet stack: **Loki** stores logs, **Promtail**
auto-discovers Docker containers and ships their logs, **Grafana** renders a
provisioned dashboard.

## Run it

```bash
cd obs
docker compose up -d
```

Then open Grafana:

- URL: **http://localhost:3000**
- Login: **admin / admin** (anonymous Admin viewing is also enabled for local use)
- Dashboard: **Colt Assessment Bot** (auto-provisioned)

Loki API is on http://localhost:3100 if you want to query it directly.

Stop / clean up:

```bash
docker compose down          # stop
docker compose down -v       # stop and wipe Loki/Grafana data volumes
```

## How log collection works

Promtail uses **`docker_sd_configs`** (Docker service discovery over
`/var/run/docker.sock`). It automatically discovers *every* local container,
derives a `container` label from the Docker container name, and pushes the
logs to Loki at `http://loki:3100/loki/api/v1/push`. No per-container config
is needed — start `assess-bot` on the same Docker Desktop and it appears
automatically.

### Why docker_sd_configs (not raw file scraping)

On **Docker Desktop for Windows (WSL2)** the raw container log files live
inside the WSL2 VM under `/var/lib/docker/containers/*/*-json.log`. Mounting
that path is possible but flaky across Docker Desktop versions, and the file
names are container IDs (not names), so you have to reconstruct the container
name yourself. `docker_sd_configs` talks to the Docker API instead, which is
reliably available on Docker Desktop and gives us the container name directly.

The socket and the containers directory are both mounted **read-only**
(`:ro`), so Promtail can never modify anything.

**Fallback (if docker_sd is ever unreliable on your host):** swap the
`scrape_configs` in `promtail-config.yml` for a static file scrape:

```yaml
scrape_configs:
  - job_name: docker-files
    static_configs:
      - targets: [localhost]
        labels:
          job: docker
          __path__: /var/lib/docker/containers/*/*-json.log
    pipeline_stages:
      - json:
          expressions:
            output: log
            stream: stream
            attrs: attrs
            tag: attrs.tag
      - regex:
          source: tag
          expression: '(?P<container>[^/]+)$'
      - labels:
          container:
      - output:
          source: output
```

Both mounts required for the fallback are already present in
`docker-compose.yml`.

## Log format the dashboard expects

`assess-bot` prints one **structured JSON object per line** to stdout, e.g.:

```json
{"evt":"assess_start","company":"keb.de","user":"322226841","ts":1751800000}
{"evt":"phase","name":"recon","status":"start","company":"keb.de"}
{"evt":"phase","name":"shodan","status":"ok","company":"keb.de","ms":4200}
{"evt":"qwen","company":"keb.de","model":"alibaba-qwen3-coder-flash","status":"ok","tokens_in":1800,"tokens_out":900,"cost_usd":0.00176,"ms":5200}
{"evt":"assess_done","company":"keb.de","crit":1,"high":1,"med":2,"low":1,"decks":3,"qwen_used":true,"qwen_cost_usd":0.00176,"total_ms":62000}
{"evt":"error","company":"keb.de","msg":"..."}
```

Non-JSON human-readable lines also appear in the stream — that is fine.
Every panel uses Loki's `| json` parser, which **silently drops lines that
don't parse as JSON**, so the metrics only count real structured events.

## Dashboard panels

All panels are scoped to `{container=~".*assess-bot.*"} | json`.

| Panel | LogQL (essence) |
|-------|-----------------|
| Assessments Today (stat) | `sum(count_over_time(... \| evt=\`assess_done\` [1d]))` |
| QWEN Calls OK vs Fallback (stat) | `sum by (status) (count_over_time(... \| evt=\`qwen\` [1d]))` |
| QWEN Cost Today (stat) | `sum(sum_over_time(... \| evt=\`assess_done\` \| unwrap qwen_cost_usd [1d]))` |
| Errors Today (stat) | `sum(count_over_time(... \| evt=\`error\` [1d]))` |
| QWEN Tokens Over Time (timeseries) | `sum(sum_over_time(... \| evt=\`qwen\` \| unwrap tokens_in [$__interval]))` (+ tokens_out) |
| QWEN Cost Over Time (timeseries) | `sum(sum_over_time(... \| evt=\`assess_done\` \| unwrap qwen_cost_usd [$__interval]))` |
| Phase Latency by Phase (timeseries) | `avg by (name) (avg_over_time(... \| evt=\`phase\` \| unwrap ms [$__interval]))` |
| Findings Severity (bargauge) | `sum(sum_over_time(... \| evt=\`assess_done\` \| unwrap crit \| high \| med \| low [1d]))` |
| assess-bot log stream (logs) | `{container=~".*assess-bot.*"}` |

## Files

```
obs/
├── docker-compose.yml
├── loki-config.yml
├── promtail-config.yml
├── README.md
└── grafana/
    ├── provisioning/
    │   ├── datasources/loki.yml
    │   └── dashboards/dashboards.yml
    └── dashboards/assess.json
```
