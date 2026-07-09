# APPLY·AGENT — Project Memory (LinkedIn Automation POC)

> Persistent context for the LinkedIn Automation / "real Apply button" project.
> Keep this updated. Read it at the start of any new session.

## What we're building
A **multi-agent** system where a user talks to **Hermes** (chat: web/Telegram) and it:
sources roles → writes **truth-checked** resumes & cover letters → drives the **real "Apply" flow**
(NOT LinkedIn Easy-Apply) on **Workday, Taleo, SAP SuccessFactors, Personio, HiBob** →
handles recruiter **email** + screening questions → up to the **interview invite** + calendar.
To be **open-sourced** once the POC works.

## Hard rules (non-negotiable)
- **No lies.** Truth Gate = independent entailment check vs the user's real LinkedIn/resume evidence.
  Verdicts: supported / overstated / unsupported. Evidence receipt per document.
- **Human-in-the-loop.** Every irreversible action (submit, send, book) is behind an explicit Confirm.
- **Quality over volume** (avoid the AIHawk spam backlash). Fit-scored, one job at a time.
- **ToS honesty.** LinkedIn/ATS ToS restrict automation (our linkedin_verifier.py cites User Agreement §8.2).
  Run inside the user's own authenticated session; document constraints; get counsel before scale.

## Tech stack (decided)
- **Apply Driver:** Alibaba **Page-Agent** (in-page JS GUI agent, DOM-dehydration, model-agnostic).
- **Model:** open-weights **Qwen 3.x** on **DigitalOcean Serverless Inference** (pay-per-token, one API key).
  Embeddings: qwen3-embedding. Model routing: small for DOM steps, large for writing/verification.
- **Orchestration:** **LangGraph** supervisor graph (AgentCore-style), durable/resumable, 7 agents.
- **Agents:** Supervisor, Sourcing, Resume+CoverLetter, Truth Gate, Apply Driver, Comms, Scheduler.
- **Data:** DO Managed **Postgres + pgvector**; **Spaces** (S3) for artifacts; **Valkey** cache/queue; **Kafka** event bus.
- **Guardrails:** self-hosted **LlamaFirewall + AlignmentCheck + Qwen judge**; OWASP LLM Top-10 (2025) mapped.
- **Observability:** OpenTelemetry → Prometheus/Grafana + Loki + Tempo + **ELK (Kibana)** + Sentry; append-only audit; cost metering.
- **Security:** Cloudflare **WAF**+CDN, DO IAM/RBAC + scoped tokens, **Vault/KMS** secrets, VPC + Cloud Firewall.

## Architecture principles (MUST — added 2026-07-05)
- **Everything containerized (Docker)** — every service/agent is a container; identical image local → droplet → registry.
- **Docker Compose** brings up the whole stack (app + agents + Postgres + Valkey + Kafka + observability via compose profiles).
- **Serverless + Docker hybrid** — DO **Functions** for bursty agent jobs; long-running services in Compose on droplet(s).
- **Maximum automation** — **Terraform from Day 0**. `terraform apply` provisions the droplet(s) AND everything on it:
  VPC, Cloud Firewall, Managed Postgres, Spaces, DO Container Registry, DNS, Cloudflare, secrets; **cloud-init/user-data
  renders ALL configs + .env, logs into registry, and runs `docker compose up`** → full running stack, incl. all configs.
- **GitHub is the source of truth + CI/CD + testing backbone** (explicit requirement). Mono-repo (app, agents, IaC, compose);
  branch protection; PRs with required checks + terraform plan comment; GitHub Environments (dev→staging→prod, prod needs approval);
  Secrets/OIDC to DO (no long-lived keys); Dependabot + CodeQL.
- **CI/CD** (GitHub Actions): lint (ruff) → unit (pytest) → integration (testcontainers) → LLM evals (hallucination-block/groundedness/injection-catch)
  → Playwright E2E (sandbox ATS) → build image → push **DOCR** → `terraform plan/apply` → smoke test. Testing gates block merge/deploy.
- **Throttle-as-code** — rate limits, agent step-budgets, spend caps declared in config and deployed via IaC.
- Terraform **remote state** in Spaces backend. Immutable image tags. Secrets never in git (SOPS/Vault, rendered at boot).

## Sequencing recommendation (answer to "Compose-first vs Day-0 IaC?")
**Hybrid — recommended:**
1. **Compose-first for the APP** (week 1): Dockerfiles + docker-compose, run locally + on ONE droplet. Fast feedback, prove the stack end-to-end.
2. **Thin Terraform from Day 0 for INFRA** (parallel): a small TF that creates droplet + VPC + firewall + Managed Postgres + Spaces + DNS. Avoids snowflake servers from the start. Manual `terraform apply` at first.
3. **Converge** (phase 1): fold the working Compose + rendered configs into Terraform cloud-init/user-data so `terraform apply` builds the whole environment.
4. **CI/CD + throttle** (phase 1–2): add GitHub Actions pipeline and throttle-as-code AFTER the app runs.
Rationale: full CI/CD before the app even works = premature; pure manual Compose = snowflake drift. Compose-first for app + IaC-from-Day-0 for infra gets fast feedback AND no drift.

## Deployment target (added 2026-07-05)
- **Domain:** `jobhuntwow.com` (registered at GoDaddy, renews Dec 1 2026). Host everything on DigitalOcean.
- **Droplet:** FRA1, Ubuntu 24, **2 vCPU / 4 GB RAM / 80 GB SSD** (display name says 1vcpu-1gb but actual specs are 4 GB / 2 vCPU). User also has DO **Serverless Inference / Model Catalog / Agent Platform** available.
- **Capacity verdict:** enough for a **lean Phase-0 POC** (heaviest pieces are off-box: Qwen on Serverless Inference, Page-Agent in browser). For Phase 0 substitute **Valkey streams for Kafka** and **Loki for ELK**, agents ×1, add a **4 GB swap file**. NOT enough for the full stack (Kafka + ELK) or production → resize to 8 GB/4 vCPU or offload to managed / DOKS in Phase 1+.
- **DNS/WAF:** put jobhuntwow.com behind **Cloudflare** (switch GoDaddy nameservers → Cloudflare; A @ → droplet IP proxied; Full-strict TLS + Origin cert on Caddy/Traefik). Cloudflare = the design's WAF layer and hides the origin IP. Lock DO Cloud Firewall to 443 (Cloudflare ranges) + 22 (own IP). Keep origin IP private (do not hardcode in the open-source repo).

## Reusable code (in user's folders)
- `Linkedin Scraper/linkedin_verifier.py` — Playwright stealth, cookie-session reuse, human pacing, exponential backoff,
  CAPTCHA/challenge STOP, fuzzy match confidence scoring, checkpoint/resume. → evidence ingestion + graceful-stop base.
- `Python SW/oxford-dictionary-scraper` — scrape → DB → export → HTML-generate + rewrite pipeline. → reuse DB/export/doc-gen plumbing.
  (NOTE: no literal Qwen code found in oxford-dictionary-scraper/src; check "Claude all files"/"rewrite_output" dirs if Qwen code is needed.)
- santifer/career-ops (MIT) — A–F fit rubric (10 dims) + ATS-optimized PDF generation.
- **`feranicus/jobhuntwow.com` (yours, MIT)** — the CRM/kanban front-of-house. Current stack: Gmail → Google Apps Script → Google Sheets → React dashboard
  (kanban pipeline, interview timeline, analytics: conversion/interviews-per-week/ghosting, company cards, search/filter; Telegram/Slack/email + interview countdown).
  Sheet columns: ID|Company|Role|Stage|Next Interview|Last Email|HR Contact|Status|Next Follow-up|Notes. Stages: HR→Tech→Director→Final→Offer.
  **Incorporated as the tracking UI of APPLY·AGENT:** reuse the React kanban + analytics + notifications directly; repoint data source Google Sheets → Postgres API;
  upgrade Gmail keyword/RegExp parsing → the Comms agent (Qwen); Apps Script 15-min CRON → event-driven updates from the agent pipeline.
  Agents move cards: Sourcing→Sourced, Apply Driver→Applied, Comms→stage/sentiment, Scheduler→interview date+countdown, You→Offer.
  New DB entities added: pipeline_card, contact, stage_event.
  NOTE: hosting moved OFF GitHub Pages (removed custom domain + Unpublish); GitHub stays source+CI/CD; site now hosted on the droplet.

## Open questions
- "Hermes" = agent runtime/brand (assumed) vs React Native Hermes JS engine? (assumed runtime)
- Exact Qwen model variant to pin (currently "3.x"; DO catalog shifts).
- Where the Qwen code the user mentioned actually lives.

## Deliverables so far
- `Linkedin Scraper/apply_agent_hld_v2.html` — HLD + LLD interactive one-pager (KVADROCYCLE style).

## Working style (user preference — ALWAYS follow)
- Give **precise, numbered, step-by-step** instructions. Every command exact and copy-pasteable
  (full path, exact flags). No vague "do X then Y" — spell out each command + expected output.
- Prefer **deterministic** solutions over LLM-in-the-loop for fixed tasks (LLM adds flakiness,
  rate-limits, hallucination). AE interaction for assessments = the dedicated no-LLM `assess-bot`
  (`/assess <company>`), NOT the Hermes agent.
