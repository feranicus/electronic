# 01 — Orchestration: `python ship.py` and its building blocks

**Operating principle 7: ONE orchestrator, ONE command.** The operator only ever runs `python
ship.py`. Every other script here is a building block it calls as a subprocess; they stay
individually runnable for debugging only. A reply that ends with two `python` lines is a defect.

## The orchestrator

| Script | Role |
|---|---|
| `ship.py` | test → commit → push → deploy web + bots → verify → tag safe-point → release notes. Flags narrow it (`--test`, `--web`, `--bots`, `--direct`, `--dry-run`, `--rollback`, `-m`); they never split it. Runs the static ruff F-gate, the i18n/brand/contrast/header gates, engine-hash verify, model-existence probe, caddyguard, and the Perseus hub install. |
| `ship_web.py` | Web-only deploy via GitHub Actions (`--ci` path). Legacy; direct-from-PC is default. |

## Deploy building blocks

| Script | Role |
|---|---|
| `deploy_web_direct.py` | Builds colt-web on the droplet and wires the committed Caddy block. Single ssh session. Packs `git archive HEAD` (immutable commit, LF bytes) — staging and prod get identical bytes. `--no-proxy` for the staging twin. |
| `deploy.py` | Bots deploy (colt-assessbot, colt-cassandra, promtail). Multi-session; hard `timeout=` on every ssh; batches probes to dodge sshd throttling. |
| `deploy_web_direct.pack()` | The one pack implementation; `deploy.py` reuses it with a bots include-list + the gitignored `.env` as `extra`. |
| `stagegate.py` | Deploy to the staging twin (165.245.244.174) → health → **reboot** → health → AI quorum panel → GO/NO-GO before prod. `quorum.py`/`agent.py` live here. |
| `golive.py` | Legacy one-shot go-live (DNS + TLS + deploy). Superseded by ship.py's web path. |

## Verification & config

| Script | Role |
|---|---|
| `engine_config.py` | Resolves the *effective* enrichment config with provenance (chain, head, every source, conflicts). Served at `GET /api/diag`; printed by every ship. |
| `probe_models.py` | Picks the enrichment chain from evidence (real contract call per model). |
| `model_probe.py` / `model_watch.py` | Assert every chain id exists in the live catalog; diff catalog vs `models_seen.json`. Run inside colt-web where the key lives. |
| `compare_models.py` | Deck-quality bake-off on the REAL prompt. |
| `check_enrich.py` | Reads `enrich_last.json` off the droplet to see the raw model answer. |
| `release_notes.py` | Gathers deterministic release facts (commits/files since `last-known-good`, staging verdict); the in-colt-web half asks the 4 models and sends via Gmail API + Telegram. |
| `govern.py` | Governance helper. |

**Standing rule:** every reply that requires the operator to act ends with exactly one `python …`
line (with `cd "C:\Python SW\Linkedin Scraper"`) or "Nothing to run." A new capability is wired
INTO ship.py in the same change, never handed over as a second command.
