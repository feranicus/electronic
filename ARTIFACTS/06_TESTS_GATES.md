# 06 — Tests and blocking gates

Doctrine, learned the hard way and repeated across `CLAUDE.md`: **a check that cannot run is not a
check; a check that cannot see its subject is not a check; assert the PROPERTY, not a string the
error text shares; prove a negative test against a GREEN baseline first.** Gates run both in
`ship.py` and — for the frontend ones — inside `webapp/Dockerfile` (toolchain correct by
construction).

## Engine self-tests (`hermes-skills/shodan-assessment/scripts/test_*.py`)

| Test | Guards |
|---|---|
| `test_recall.py` | Recall + scope on shared-hosting targets; crt.sh retry (§26); CT-name resolution (§24); enrich 400-repair (§25); the low-and-slow and CertSpotter sections. **The real gate is the LAST line** (was a mid-file exit that let §19–§26 pass vacuously). |
| `test_ca_pivot.py` | The internal-CA pivot ownership gate (bibeltv.de 1003-FP incident). |
| `test_run_path.py` | Executes `run()` against a mocked shodan; co-tenant guard; lotto24 per-pivot rollback. |
| `test_scope_abakus.py` | Abakus incidents §1–§14: generic-word anchors, SaaS-tenancy pinning, attribution gate, empty-estate-is-honest, cert-name refusal, inventory derived from final estate, AMINA no-space attribution. |
| `test_classify_adpolice.py` | TLS-version negation, redirect-chain service naming, per-jurisdiction regimes, dangling-DNS-is-a-question. |
| `test_asn_enterprise.py` | RBC all-RIR ASN discovery + bgp.he.net fallback + holder corroboration. |
| `test_parity.py` | Manual-Shodan-vs-platform parity (angermann exports). |
| `test_passive_checks.py` | email_auth / cert_intel / on-prem Exchange (§6). |
| `test_deck_quality.py` | Every slide read, length budgets derived from the builder, footer collisions, two-slides-agree. |
| `test_engine_i18n.py` | Every advertised deck language renders composed titles, declined counts, labels; EN byte-identical. |
| `test_compliance_ca.py` | Canada §6.4 "must never appear" list (no OSFI fine, no live CCSPA clock, etc.). |
| `test_drift.py` | Semantic served-config drift (hosts/handlers/path-matchers), roster, mount-sync. |
| `test_white_label.py` | Branded build maps all surfaces, unbranded build byte-identical, severity enums untouched. |
| `test_creed.js` | Deck creed chrome. |

## Backend / infra suites (`tests/`)

Auth & access: `test_auth.py`, `test_admin_users.py`, `test_quota.py`, `test_jurisdiction_path.py`,
`test_doc_lang.py`, `test_routes.py`, `test_chat_open_wallet.py`* (*in jobhuntwow).
Defence: `test_shield.py`, `test_perseus_hub.py`, `test_perseus_ruleset.py`, `test_perseus_abuse.py`,
`test_siege_feed.py`, `test_spend_watch.py`, `test_ip_reputation.py`, `test_attack_digest.py`,
`test_fleet.py`, `test_fleet_cli.py`, `test_agent_forensics.py`, `test_llm_guard.py`.
Deploy & proxy: `test_deploy_immutability.py`, `test_deploy_parity.py`, `test_caddy_wiring.py`,
`test_gate_integrity.py`, `test_decommission.py`, `test_outside_view.py`, `test_hostpath.py`,
`test_supplychain.py`.
Cost & data: `test_llm_meter.py`, `test_dbbackup.py`, `test_set_secret.py`, `test_run_log.py`,
`test_jhw_llm_events.py`.
Platform-safety: `test_console_encoding.py` (cp1252), `test_security_headers.py` (stdlib ASGI, no
httpx), `test_demo_atomic.py` (simulates Windows os.replace), `test_preview_proxy.py`,
`test_white_label_api.py`, `test_recon.py`, `test_release_notes.py`.
`conftest.py` — shared fixtures.

## Frontend build gates (`webapp/frontend/tools/*.mjs`)
`i18n_catalogue.mjs`, `run_i18n_audit.mjs`, `api_contract.mjs`, `header_layout.mjs`,
`contrast_gate.mjs`, `canvas_smoke.mjs`, `shipped_shell.mjs`, `partners_gate.mjs`.

## Recurring platform traps to check in BOTH repos before shipping
POSIX-only APIs (`os.uname`), test-only deps not on the operator's box (httpx, python-multipart,
docx), `bash -n <windows path>`, CRLF in payloads/`git archive`, cp1252 console — each has cost a
wasted ship. A fix in one project's CLAUDE.md is not applied to the sibling until someone applies it.
