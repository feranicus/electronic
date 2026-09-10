# Artifact inventory — feranicus/electronic (Cybergod / S4Biz cyber pre-sales)

Generated 2026-09-09. This folder documents every artifact in the repo so the project can be
carried into a fresh conversation without dragging the whole history along.

## Why this exists — the conversation is oversized because of ONE file

Measured, not guessed:

| File | Size | Lines | `##` sections |
|---|---|---|---|
| `CLAUDE.md` | **646 KB** | **7,950** | **307** |

`CLAUDE.md` is project instructions checked into the repo, so it is **re-injected into the model
context on every single turn**. At ~646 KB that is roughly **160,000+ tokens spent before you type
anything** — every message. That, not the message history, is what makes the conversation feel full
and slow. Nothing else in the repo comes close.

So the fix is not "move to a new project and start clean" on its own — if the new project still
carries a 646 KB `CLAUDE.md`, it will fill up exactly as fast. The lever is `CLAUDE.md` itself.
See **`07_OPTIMIZATION.md`** for the concrete plan.

## The index docs

| Doc | Covers |
|---|---|
| `01_ORCHESTRATION.md` | `ship.py` and its building blocks — the one-command deploy pipeline |
| `02_ENGINE.md` | The Shodan assessment engine — `hermes-skills/shodan-assessment/scripts/*` |
| `03_WEBAPP.md` | cybergod.ai — FastAPI backend + React cabinet (`webapp/`) |
| `04_SECURITY_FLEET.md` | Perseus shield, hub, sidecar, fleet observability, defensive tooling |
| `05_OPS_DEPLOY.md` | Proxy/Caddy, recovery, cost & spend forensics, backups, secrets |
| `06_TESTS_GATES.md` | Every regression suite and blocking gate, and what each one guards |
| `07_OPTIMIZATION.md` | Root cause + step-by-step plan to shrink CLAUDE.md and migrate |

## What "the project" actually contains (top level)

- **47 top-level Python scripts** — orchestration, deploy, ops, forensics (see `01`/`05`).
- **~42 engine scripts + 10 JS deck builders** in `hermes-skills/shodan-assessment/scripts` (`02`).
- **~30 backend modules + 17 React pages** in `webapp/` (`03`).
- **~40 pytest suites** in `tests/` plus engine self-tests (`06`).
- **8 GitHub Actions workflows** in `.github/workflows/`.
- **`perseus/`** package (hub, client, ruleset, vet, abuse) — fleet-wide defence (`04`).
- Sibling projects with their own `CLAUDE.md`: `jobhuntwow-app/`, and (outside this repo)
  jev.best, klima/polara, s4biz.

## How to read these docs

Each area doc lists the artifact, its one-line purpose, and — where it matters — the standing rule
or hard-won lesson attached to it. The lessons are compressed from `CLAUDE.md`'s 307 sections; the
full narrative for any of them still lives in `CLAUDE.md` until it is archived (see `07`).
