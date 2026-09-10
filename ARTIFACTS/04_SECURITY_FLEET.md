# 04 — Perseus: shield, hub, fleet, defensive tooling

Active defence for cybergod and the wider fleet. Inline decisions are pure arithmetic (fast, no
model on the request path); the 4-model panel reviews out of band and tunes within committed
bounds. **Never touches the firewall** (Amnezia VPN shares the host) — HTTP-layer only. **Never
scans or hacks back** (StGB §202a/b, §303a/b, §202c; EU 2013/40; CFAA; Canada CC s.342.1).

## Inline shield (`webapp/backend/app/`)

| Module | Role |
|---|---|
| `shield.py` | `decide(ip, path, authed=)` enforcement + `_decide_raw()` scoring. Exemptions: an authenticated session is never blocked/tarpitted; a route we serve is tarpitted, never blocked. `probe_shape()` scores, `is_our_route()`/`is_probe_path()` decide action. UA-rotation, low-and-slow (per /24 over 14d, needs own-probe corroboration), referrer-spam detection. Owns the `CLASSES`/`classify()`/`lane_of()` vocabulary. |
| `slow_store.py` | The 14-day low-and-slow evidence, SQLite on the persistent volume (module state dies on `--force-recreate`). Write-behind, merge-not-replace, fails open. |
| `shield_console.py` | Applies Telegram-approved actions (`apply_decisions`, 20s loop). colt-web ENFORCES; the bot RECORDS. Confirmation is read back out of shield state. |
| `shield_panel.py` / `shield_tuning.py` | 6-hourly 4-model review; proposes bounded threshold changes (quorum on direction, median value, 25% step cap, clamp-on-read via `shield.BOUNDS`/`cfg()`). |
| `siege.py` | In-memory ring buffer feeding the public `/defense.html` siege feed. IP truncated to /24 on the way in; only attack-shaped requests recorded; paths shape-gated. |
| `visitors.py` | Bot gate (`BOT_404`), probe-path suppression, "a person just opened cybergod.ai" alert (suppressed for infra / spoofed-UA / referrer spam). |
| `alerts.py` | Sliding-window security rules; records hostile /24s to the reputation store. |
| `ip_reputation.py` | Passive hoster/VPN/bulletproof classifier; fails open (unknown = person). |
| `abuse_report.py` | AbuseIPDB (opt-in) + human-reviewed complaint drafts (drafter reaches no network). |
| `attack_digest.py` | Daily digest of NEW attack shapes the classifier does not yet name; models propose, `vet()` refuses, human taps to promote to DETECTION. |
| `llm_guard.py` | LLM-endpoint guardrails. |
| `spend_watch.py` | Hourly deviation-from-own-baseline spend alarm (median, ratio + absolute floor, names NEW models). Two sources: our meter + DO balance delta. |

## Fleet-wide (`perseus/` package + `perseus.py`)

| Artifact | Role |
|---|---|
| `perseus.py` | Installs the hub + daily timer; `--clients` copies the sidecar; `wire_middleware()` edits each project's ASGI app (package-aware relative import); `--rollout` deploys the fleet via each project's OWN orchestrator; `--install-only` (called by ship.py). |
| `perseus/hub.py` | The nightly cycle inside colt-web: review (auto-demote) → mine patterns → tune thresholds → report. Reads Loki (the shared substrate). |
| `perseus/client.py` | Thin stateless sidecar: `Middleware`, `observe()` (writes `evt=http` like colt-web), `check()` (blocklist read), `_beat()` (heartbeat proof). Holds no credentials, sends nothing. |
| `perseus/ruleset.py` | `can_promote()` (24h detection, 3-of-4 quorum, ≥1 hostile match, 0 clean hits), `thresholds()` (clamp on read), `review()` (auto-revert), `atomic_write()` (the one os.replace impl with Windows retry). |
| `perseus/vet.py` | 5 fail-closed barriers on a model-proposed regex (compiles, matches nothing known-good, not catastrophically broad, ≥3 literal chars, cheap on hostile input — nested-quantifier shape detected statically, never executed). |
| `perseus/abuse.py` | Fleet abuse-complaint drafting. |
| `webapp/backend/app/fleet.py` | `GET /api/admin/fleet` + `fleet.watch()`. Three states kept apart: LIVE / OBSERVED (unguarded) / SILENT (blind) / `elsewhere` (own event volume). Edge-triggered Telegram watch. |
| `fleet.py`* | Read-only fleet status CLI (one ssh): code present? / wired in? / beating? — never conflated. *repo root. |
