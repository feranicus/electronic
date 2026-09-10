# 02 — The assessment engine (`hermes-skills/shodan-assessment/scripts/`)

Shared by BOTH images (colt-web and colt-assessbot each `COPY` this tree to `/opt/shodan-skill`),
so a change ships to the web app and the Telegram bots at once. `run_assessment.py` is the
orchestrator; `run_assessment.autodiscover()` resolves the entire recon anchor block from **one
input: a company name or domain**. Never require the operator to hand-feed ASN/net/issuer/cert-org.

## Recon & scope (the zero-false-positive core)

| Script | Purpose |
|---|---|
| `shodan_recon.py` | The heart. Identity resolution, the ownership gate (`_owns_apex`), the attribution gate, co-tenant guard, per-pivot & per-domain budgets, cert-name harvest, scope-blowout guard, `ScopeRefused`. Largest and most defect-hardened file in the repo. |
| `asn_sources.py` | Multi-source ASN discovery: RIPEstat searchcomplete (all RIRs, first), bgp.he.net (HTML fallback when JSON APIs die), RIPE DB, CAIDA, PeeringDB, bgpview. Holder-corroboration gated. |
| `psl.py` | Public-suffix / registrable-domain (eTLD+1). Stops `budget.gov.ru` → `gov.ru`. |
| `scope_deny.py` | Authoritative shortener/social/SaaS/platform denylist, enforced at harvest AND at the ownership gate. |
| `group_discovery.py` | Crawls the customer's own site for group-structure pages → owned subsidiary domains. |
| `naming.py` | Learns the target's hostname grammar from CT, generates candidates in the target's own language. |
| `attribution.py` | Attribution helpers for the record/name gates. |
| `bgp_resilience.py` | NIS2 routing-resilience grading. UNKNOWN on a failed lookup, never CRITICAL. |
| `clarify.py` / `compliance_clarify.py` | Deterministic post-run clarification questions (deliver-then-refine loop). |

## Passive intelligence (zero packets)

| Script | Purpose |
|---|---|
| `email_auth.py` | SPF / DMARC / DKIM / MTA-STS. DKIM presence-only. |
| `cert_intel.py` | Revoked/near-expiry/shared-key certificate findings, joined to resolved hosts. |
| `active_probe.py` | End-of-life from a stored banner (passive); active tier gated behind `ACTIVE_PROBE=1` + `ACTIVE_PROBE_AUTH`. |

## Enrichment (the LLM layer)

| Script | Purpose |
|---|---|
| `enrich.py` | The LLM contract, model chain (`_FALLBACKS`), `_call`, `MODEL_PARAMS` per-model overrides, CVE hallucination guard, `normalise_prose`, budget/timeout arithmetic. All model calls route through `_call`. |
| `enrich_parallel.py` | Map-reduce sharding for large estates; round-robin across the chain so shards don't share one failure domain. |
| `llm_meter.py` | Per-call cost meter + daily budget (`allow()` before the request, fails open on storage fault / closed on budget). |
| `cost_ledger.py` | SQLite lifetime cost ledger on the persistent volume. |

## Deck & report builders (JS, deterministic)

| Builder | Output |
|---|---|
| `build_findings_deck.js` | Findings deck (jurisdiction-aware framework set from `target.country`). |
| `build_cbiq_deck.js` | C-BIQ (FAIR loss) deck. |
| `build_geopol_deck.js` + `build_geopol_html.js` + `author_geopol.py` | Animated GEOPOL scrollytelling HTML (fixed skeleton, text injected). |
| `build_deltas_deck.js` | Deltas deck. |
| `build_compliance_deck.js` + `build_compliance_html.js` | NIS2/CRA/EU-AI-Act + Canada (OSFI/PIPEDA) regime decks, jurisdiction-keyed. |
| `brand.js` | White-label recolour (maps by VALUE; severity enums never remapped). |
| `creed.js` | Shared deck chrome/creed. |
| `deck_langs.py` | Single source of truth for document languages (derived from dictionaries on disk); served at `GET /api/langs`. |

## Compliance, demo, white-label, output

| Script | Purpose |
|---|---|
| `compliance_assess.py` / `compliance_enrich.py` | Compliance engine + `JURISDICTIONS` registry (EU + Canada). |
| `demo_build.py` | Pre-bakes the public "Trojan Empire" demo from RFC-5737 fixtures; atomic `os.replace` publish. |
| `proteus.py` | White-label: extract palette/fonts/logo from an uploaded .pptx (parsing, not LLM). |
| `pptx_preview.py` | Renders a deck to images for visual verification. |
| `run_log.py` | Customer-safe run-log deliverable (allow-list redaction). |
| `audit_fp.py` | Independent FP auditor (different vendor than deck author; may flag, never guts a deck). |
| `run_assessment.py` | The engine orchestrator: recon → decks → GEOPOL HTML → clarify. Emits structured events to `EVENTS_LOG`. |

## Engine self-tests (also gates in ship.py)

`test_recall.py`, `test_ca_pivot.py`, `test_run_path.py`, `test_scope_abakus.py`,
`test_classify_adpolice.py`, `test_asn_enterprise.py`, `test_parity.py`, `test_passive_checks.py`,
`test_deck_quality.py`, `test_engine_i18n.py`, `test_compliance_ca.py`, `test_drift.py`,
`test_white_label.py` — each guards a specific past incident. See `06_TESTS_GATES.md`.
