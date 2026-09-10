# 03 — cybergod.ai web app (`webapp/`)

FastAPI backend + React SPA, one container `colt-web` in the isolated `colt-stack`, fronted by the
shared videodead-caddy. Deploys direct from PC via `deploy_web_direct.py`. `app` is a **package** —
always `from . import x`; a bare `import x` fails at runtime and the except-swallow hides it.

## Backend (`webapp/backend/app/`)

### Core
| Module | Role |
|---|---|
| `main.py` | Routes, SSE stream, `_run_job` (owns the engine as a background task), `_APP_ROUTES`, quota, jurisdiction/language resolution, static SPA serving. |
| `settings.py` | Config. |
| `store.py` | Jobs SQLite (who ran what, language, status). |
| `auth.py` / `colt_auth.py`* | IAM. `email_allowed()` is the single gate (Colt AEs, partner emails/domains, enabled `user_store` accounts). *`colt_auth.py` is at repo root. |
| `user_store.py`* | Per-user password store (scrypt) on shared volume; assigned password wins over the shared one. *repo root. |
| `assistant.py` | Cassandra assistant (system prompt is customer-facing — rebranded). |

### Observability & telemetry
| Module | Role |
|---|---|
| `telemetry.py` | One `evt=http` per request → EVENTS_LOG (client IP from first XFF). Shield/siege observe at this point. |
| `geoip.py` | Country-level geo (DB-IP Country-Lite). |
| `daily_report.py` | Emailed daily access + threat digest. |
| `threat_intel.py` | Per-IP MITRE ATT&CK digest. |
| `notify.py` | Telegram + Gmail API (SMTP is blocked outbound — never "fix" to SMTP). |

### Compliance / privacy / branding
| Module | Role |
|---|---|
| `security_headers.py` | HSTS/CSP/etc, in the app not the shared Caddyfile. |
| `brand.py` | White-label upload job (`/api/brand`), delegates to `proteus`. |
| `release_notes.py` | In-container half of the 4-model release notes. |

## Defence modules (see `04_SECURITY_FLEET.md` for the full story)
`shield.py`, `shield_console.py`, `shield_panel.py`, `shield_tuning.py`, `siege.py`,
`slow_store.py`, `spend_watch.py`, `alerts.py`, `visitors.py`, `ip_reputation.py`,
`abuse_report.py`, `attack_digest.py`, `llm_guard.py`, `fleet.py`, `perseus_client.py`.

## Frontend (`webapp/frontend/src/pages/`)

Public: `Landing.jsx`, `Demo.jsx`, `Partners.jsx`, `Contact.jsx`, `Impressum.jsx`, `Privacy.jsx`,
`Experience.jsx`, `Login.jsx`.
Cabinet (owner-scoped): `Cabinet.jsx`, `NewAssessment.jsx`, `Compliance.jsx`, `Assistant.jsx`,
`History.jsx`, `WhiteLabel.jsx`, `Admin.jsx`, `Fleet.jsx`, `ChangePassword.jsx`.

### Frontend infrastructure (not pages)
- i18n: `locales/{en,de,it,fr,es,pl}.js` + `legal-locales/` + `partners-locales/` — 404 strings ×
  6 locales, plus deck languages via `deck_langs`. `useSyncExternalStore` shared language store.
- Build gates (run in the Docker fe stage AND ship.py): `tools/i18n_catalogue.mjs`,
  `tools/run_i18n_audit.mjs`, `tools/api_contract.mjs`, `tools/header_layout.mjs`,
  `tools/contrast_gate.mjs`, `tools/canvas_smoke.mjs`, `tools/shipped_shell.mjs`,
  `tools/partners_gate.mjs`.
- PWA: `public/manifest.webmanifest`, `public/sw.js` (never caches `/api/`), `make_icons.py`.

## Local preview (never touches the droplet)
`preview.py` — dev server / `--build` / `--offline`; read-only `/api` proxy; prints the LAN phone
address. `ui_preview_stamp.py` — the hash the "look before you ship a UI change" gate compares.
