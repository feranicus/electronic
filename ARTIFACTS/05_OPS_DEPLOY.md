# 05 — Ops, proxy, recovery, cost & forensics, secrets

All droplet changes live in committed artifacts — never a hand-edit over SSH. Read-only diagnostics
are fine. Single-connection ssh pattern preferred (Windows OpenSSH has no ControlMaster; OpenSSH
9.8 PerSourcePenalties + MaxStartups throttle rapid sessions).

## Shared proxy / Caddy (the 2026-08-07 outage subsystem)

| Script | Role |
|---|---|
| `caddyguard.py` | The shared Caddyfile is now GENERATED from per-project fragments, never edited. Write-time validation (container's own image + env), runtime watchdog (10-min timer + OnBootSec), reboot gate, tamper check (fragment vs committed block). Building block of ship.py. |
| `perseus/`-style `agent.py`* | (lives under stagegate/caddyguard) drift/roster/admin/mount_sync/selftest checks — semantic served-config comparison, not byte hash. |
| `recover.py` | One-command outage triage: probe from outside, then one ssh for uptime/disk/mem/ports/containers/crash-loop logs/caddy validate. Refuses to restart a crash loop. |
| `forensics.py` | Read-only "who wrote the file and when" timeline across /etc /opt /root /srv, timers, patchwatch, apt, ssh logins, OOM. |
| `decommission.py` | Retire a vhost from the shared proxy safely (collateral check, restart-policy first, nothing deleted, dry-run default, `--undo`). |
| `cloudflare_setup.py` | Planned CF WAF fronting (see `deploy/CLOUDFLARE.md`). |

## Cost, spend & LLM forensics

| Script | Role |
|---|---|
| `cost_report.py` | Lifetime/per-day/per-company cost; DO billing reconciliation; `--trace` (group containers by API-key fingerprint), `--correlate`, `--whodunit` (who spent the money — decisive 4-way verdict). |
| `secaudit.py` | Kernel currency / pending reboot / queued security packages, both hosts; twin-drift. |
| `incident_report.py` | Read-only forensics of exposed-route hits (the jobhuntwow abuse). Output gitignored. |
| `agent_forensics.py` | Was the LLM-jacker a human/script/agent? Behaviour-only (bodies never logged); BLIND-not-innocent guard. |
| `analyse_attacks.py` | Replays the mass-scan corpus vs the shield against the real event log; names classes not yet recognised. |
| `logship.py` | Off-box append-only archive of the events log (CRA Art.14 material). |
| `dbbackup.py` | Off-box backup of `colt.sqlite` + `cost_ledger.sqlite` via sqlite online-backup API; verifies + test-restores; finding-nothing-on-a-live-box is a FAILURE. |

## Secrets, IAM, GitHub

| Script | Role |
|---|---|
| `set_secret.py` | Upserts one runtime secret (value on stdin, never argv) into local + droplet `.env`. |
| `enable_gmail_api.py` / `fix_smtp.py` | Gmail API setup (SMTP is blocked outbound). |
| `setup_github_cicd.py` | One-time CI/CD provisioning. |
| `import_dashboard.py` | Re-imports Grafana dashboards after a bots deploy. |
| `publish_landing.py` | Legacy GitHub-Pages landing publisher — DO NOT use for cybergod (droplet serves it now). |
| `finalize_public.py` | Public-surface finalizer. |
| `diagnose_engine.py` | Engine diagnostics. |

## GitHub Actions (`.github/workflows/`)
`ci.yml` (gitleaks, ruff, pytest), `security.yml` + `codeql.yml` (Trivy pinned+sha-verified, CodeQL),
`deploy.yml`, `web-deploy.yml`, `import-dashboards.yml`, `provision-patchwatch.yml`,
`uptime.yml` (off-box every 10 min — the one monitor outside the proxy's failure domain).

## Patch automation
`patchwatch/` — backup-first, LLM-assisted droplet updater on a 3-day timer; reboot gate refuses to
reboot into an invalid proxy config.

*`agent.py` referenced above is the caddyguard/stagegate helper, not a repo-root file.*
