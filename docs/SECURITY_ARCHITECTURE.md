# Security architecture, tooling and guardrails — cybergod.ai

**Owner:** Evgeny "Jev" Vainshtein · Cybergod LLC / S4Biz Group
**Written:** 8 Aug 2026 · **Audience:** our own engineering, and the CISO / security architecture
function of an enterprise buyer evaluating us for API, white-label or OEM integration.

## How to read this

Three sections, in this order on purpose:

1. **What we actually run today** — inventory, honest, nothing aspirational.
2. **What we do NOT have** — the list a bank's security architect will produce in the first hour.
   It is better that we write it than that they do.
3. **What to add, prioritised** — open-source only, with the effort and the UX cost of each.

**Two rules this document obeys.**

- **No invented identifiers.** Frameworks are named; specific control IDs are quoted only where
  verified. Anything needing a clause number before it goes to a customer is marked `[verify]`.
- **No commercial products.** Every recommendation is an open-source project that a bank's
  architecture board already recognises. Where a category has no credible OSS answer, it says so.

**And the design constraint that outranks everything below:** *security that damages usability does
not get used, and a control nobody uses is a control you do not have.* Every recommendation states
its UX cost. Anything that would put friction in front of a user without materially reducing risk
is listed under "Deliberately not doing" at the end.

---

# 1. What we run today

## 1.1 Supply chain and build

| Tool | OSS | Purpose here | Where |
|---|---|---|---|
| **Gitleaks** | ✅ | Secret detection across the working tree and history. A committed key is the fastest total compromise available to an attacker; this is the single highest-value scanner we run. | `ci.yml`, and a working-tree scan |
| **Trivy** | ✅ | Vulnerability + misconfiguration scan of the container image and filesystem. Also the SCA layer for OS packages. | `security.yml`, `deploy.yml` |
| **CodeQL** | ✅ | Semantic SAST — taint tracking, injection classes, unsafe deserialisation. Catches what a regex never will. | `codeql.yml` |
| **Hadolint** | ✅ | Dockerfile linting: pinned bases, no `latest`, no root-by-accident, no `apt` cache left in the layer. | `security.yml` |
| **pip-audit** | ✅ | Python dependency CVEs against the PyPA advisory database. | `security.yml` |
| **Dependabot** | ✅ | Automated dependency PRs. Keeps the window between a published CVE and our patch short. | `dependabot.yml` |
| **Ruff** (`F821/F811/F822`) | ✅ | Undefined names, redefinitions, undefined exports — **blocking**. Added after a `NameError` reached production; pyflakes rules only, no style noise. | `ship.py` |
| **pytest** | ✅ | 46 unit tests, blocking. Nothing ships if one fails. | `ship.py` |
| **OpenTofu** | ✅ | Infrastructure as code for the droplet — infrastructure is reviewable and reproducible, not clicked. | `tofu/` |

## 1.2 Network, transport and edge

| Tool | OSS | Purpose here |
|---|---|---|
| **Caddy** | ✅ | Reverse proxy and **automatic TLS** via ACME. Certificates are issued, renewed and stapled without human involvement — the most common cause of a total outage (a lapsed cert) is removed by design. HTTP→HTTPS redirect is automatic. |
| **caddyguard** (ours) | — | The shared proxy is a single point of failure for six domains. Each project writes an **isolated fragment**; the guard assembles, validates in the container's own image *and environment*, checks the bind-mount is fresh, reloads, and runs a **10-minute systemd watchdog** that self-heals. It also **blocks a reboot** into an invalid config. Written after a truncated config took every domain down for ~6 hours. |
| **Bot / scanner gate** (`visitors.py`) | — | Non-human, non-allowlisted user agents get `404` on page routes. Path-based probe detection (`/.env`, `/.git`, `/.aws/credentials`) suppresses by **path, not user agent** — a UA is attacker-controlled, the requested path is evidence. |
| **Uptime probe** | ✅ (GitHub Actions) | External, off-box, every 10 minutes. Monitoring that lives behind the thing it monitors is mute exactly when it matters. |

## 1.3 Identity and access (today)

| Control | Detail |
|---|---|
| **One authorisation gate** | `colt_auth.email_allowed()` is the single source of truth, shared by the web app and both Telegram bots. They cannot disagree. |
| **Allowlist** | Named partner addresses + trusted domains, **committed to git** — so access control is auditable in a PR, not hidden in an env var. Domain matching is exact. |
| **Two factors** | A shared password *and* a 6-digit OTP emailed to the address. A partner must control their own mailbox **and** know the password. |
| **Session** | `itsdangerous` timed serializer + HMAC-SHA256, cookie `HttpOnly` + `Secure` + `SameSite=Lax`, bounded `max_age`. |
| **Per-user quota** | `USER_QUOTAS` caps evaluation accounts; enforced on **both** front doors (web counts jobs, Telegram counts the shared cost ledger), because enforcing on one is just a signpost to the other. |
| **Auth telemetry** | Login success/failure, OTP failure, and new-IP logins are events, dashboarded and alertable. |

## 1.4 Detection and response

| Component | Purpose |
|---|---|
| **`alerts.py`** — 11 rules | password spray, OTP brute force, credential stuffing, assessment burst, DDoS shape, per-IP burst, path probing, directory brute force, authz probing (IDOR shape), download burst (exfiltration shape), session-multi-IP, new-IP login. Each rule has a 15-minute cooldown per rule+subject and a **12/hour global storm cap** — an alert flood is a second outage, and it is how real incidents get missed. |
| **`telemetry.py`** | One structured JSON event per request: IP, country, method, path, status, latency, UA, browser/OS/device, bot flag, referrer, user. Static assets skipped. `TELEMETRY_HASH_IPS=1` swaps raw IPs for salted hashes (GDPR minimisation) — currently off, deliberately, because forensics were requested. |
| **`threat_intel.py`** | Per-IP attacker digest with a **deterministic MITRE ATT&CK mapping** (`path_probe`→T1595.003, `login_failed`→T1110.001, …). A static table beats a model here: unambiguous, free, reliable. |
| **`abuse_report.py`** | AbuseIPDB reporting, **opt-in**, deduped per IP, research scanners skipped. |
| **Loki + Promtail + Grafana** | ✅ Log aggregation, retention and dashboards. Security row: alert volume, suppressed alerts, **delivery failures** (non-zero = flying blind), full forensic alert log, auth audit. |
| **Daily report** | Access, logins, visitors, countries, alerts and AI cost, emailed each morning. |
| **`security.txt`** (RFC 9116) | Machine-readable contact for a researcher who finds something. |

## 1.5 Data and privacy

| Control | Detail |
|---|---|
| **Data residency** | App, database, sessions, artifacts and logs all on a Frankfurt (FRA1) host. No replication outside the EU. |
| **Processor disclosure** | Exactly one genuine third-party recipient of personal data: Google (Gmail API) receives the user's email address to send the OTP and the daily report. Named on `/privacy`. |
| **Geo** | Country-level only, DB-IP Lite — no city, no coordinates. Proportionality by design. |
| **Owner scoping** | Artifacts are scoped to the requesting account and traversal-guarded. |
| **Synthetic-only staging** | The staging twin is built from committed RFC 5737 fixtures. **No production personal data ever crosses over.** |
| **Public demo safety** | Every demo IP is RFC 5737 reserved; a build gate greps the fixture and fails the deploy on any address outside those ranges. |

## 1.6 Release governance — the part that is genuinely unusual

This is the section that differentiates us in a CISO conversation, because most vendors have some
of §1.1–1.5 and almost none of this.

| Control | What it guarantees |
|---|---|
| **One orchestrator** (`ship.py`) | test → commit → push → staging → reboot → decide → deploy → verify → tag. There is no second path to production. |
| **Immutable artifact** | The deploy packs `git archive HEAD`, forced to repository line endings. The tested tree, the staging input, the production input and the safe-point tag are provably the same bytes. |
| **Staging twin + reboot** | Same size, region and image as production. It is **rebooted** as part of the gate — the one test production can never run, and the exact event that exposed a latent config fault. `boot_id` must change, or the test did not happen. |
| **35 deterministic checks** | Container health, auth enforcement, bot gate, proxy config, engine freshness, mount freshness, config drift, vhost roster, concurrency, memory, disk — before *and* after the reboot. |
| **Engine-hash verification** | SHA-256 of every engine file **inside the running container** compared to the repo. "The site answers" is a liveness probe, not a deploy proof. |
| **4-model consensus panel** | Two soldiers + two auditors, four different vendors (no shared outage, rate limit or training blind spot). **Advisory** — code decides. A unanimous NO-GO against a green gate halts and requires a human override, because twice that pattern meant a check was lying. |
| **Safe points + rollback** | Every verified deploy tags `last-known-good`; `ship.py --rollback` restores and redeploys that exact state. |
| **patchwatch** | Backup-first, LLM-assisted OS patching on a 3-day systemd timer, with a **reboot gate** that refuses to reboot into an invalid proxy config. |

## 1.7 Product-correctness guardrails (why the output can be trusted)

Not "security tooling" in the classic sense, but this is what a bank is actually buying, and every
one of these is a **blocking build gate**:

- **Ownership gate** — a discovered domain is a *candidate*, not proof. Brand tokens, certificate
  subject-O, published group structure and per-IP whois must corroborate before anything enters
  scope. Written after a deck claimed 1,003 hosts for a company with 5.
- **Public-suffix correctness** — `gov.ru`, `co.uk` are not owners. Seeding one is refused.
- **Co-tenant guard** — a shared netblock is not a customer.
- **Attribution gate** — pinning proves the *address* is theirs, not every *observation* on it.
- **Per-pivot and per-domain budgets** — one selector can widen scope at the margin, never own it.
- **Rarity gate** — a brand token is an anchor only if it is rare in the index.
- **Hallucination guard** — every CVE in generated prose is cross-checked against the scan
  evidence; unverifiable identifiers are stripped and the event is logged.
- **Independent FP audit** — a *different vendor's* model reviews findings; it may flag but never
  gut a deck, and its flags apply only where deterministic ownership data agrees.
- **Jurisdiction gate** — a Canadian deck cannot claim an OSFI fine, a live CCSPA obligation or a
  PIPEDA penalty on the breach itself.
- **Brand gate** — no former-employer name in any rendered artifact, page, bot or email.
- **i18n gate** — 6 locales × 11 pages rendered; no raw key, no `undefined`, no mixed language.

---

# 2. What we do NOT have

Written plainly, because a security architect will find all of it and it is far better coming
from us. Ordered by how quickly it will be asked.

| # | Gap | Why it matters to an enterprise buyer |
|---|---|---|
| 1 | **No backup or restore. At all.** | Log retention is not backup. The jobs database, the cost ledger and delivered artifacts have no snapshot, no offsite copy and **no tested restore**. This is the first question in every due-diligence pack and the answer today is bad. |
| 2 | **No SBOM, no artifact signing, no provenance** | CISA and the EU CRA both push SBOM; an OEM partner shipping our binary inside their product will require it. |
| 3 | **Scanners are report-only, and the branch protection is being bypassed** | Every push logs `Bypassed rule violations … Required status check "quality-and-secrets" is expected`. A control that is routinely overridden is not a control. |
| 4 | **No SSO / OIDC / SAML, no RBAC, no SCIM** | A bank will not create a shared password for its staff. This blocks enterprise onboarding outright. |
| 5 | **No API keys, no per-tenant rate limits, no documented API** | The OEM/white-label ask cannot be satisfied with a session cookie. |
| 6 | **No secrets management** | Secrets live in a `chmod 600` env file on the droplet. No rotation, no versioning, no break-glass audit. |
| 7 | **No container/host hardening** | Containers run as root, writable root filesystem, full capability set, no seccomp profile, no memory/CPU limits. |
| 8 | **No host IDS / file-integrity monitoring** | Nothing would notice a modified binary or a new SUID file on the host. |
| 9 | **Single droplet, no HA, no documented RTO/RPO** | Business-continuity questionnaires ask for numbers we cannot currently give. |
| 10 | **No WAF** | Caddy proxies; it does not inspect. |
| 11 | **No formal threat model, DFD or Statement of Applicability** | TOGAF/ISO-shaped review expects architecture artifacts, not only running code. |
| 12 | **No tenant isolation model** | White-label means several partners' data on one platform. There is no documented (or enforced) boundary. |
| 13 | **No log integrity / WORM** | An attacker with host access can edit the audit trail. |
| 14 | **No independent penetration test** | Expect this as a contract condition. |
| 15 | **No AI-specific controls** | Prompt-injection defence, model I/O logging as evidence, an AI BOM. The EU AI Act and every bank's new AI policy will ask. |
| 16 | **No DPIA / Art. 30 record of processing** | We have a good privacy notice; we do not have the underlying documents. |

---

# 3. Recommendations — prioritised, open source only

Effort is calendar time for one engineer. **UX cost** is the important column: anything marked
"none" is invisible to the user, and most of this is.

## P0 — do before the next enterprise conversation (2–3 weeks)

### 3.1 Backups that are actually restorable — **Litestream + restic**

| | |
|---|---|
| **What** | `Litestream` streams SQLite WAL continuously to object storage — the correct answer for our jobs DB and cost ledger, with near-zero RPO and no application change. `restic` (or `BorgBackup`) takes encrypted, deduplicated, incremental snapshots of `/data` and the artifact tree to a second region. |
| **Non-negotiable** | A **monthly automated restore test** into a scratch container, asserting row counts and one known artifact. An untested backup is a belief, not a control. |
| **Frameworks** | OSFI E-21 (resilience, tolerances), BSI IT-Grundschutz (`CON.3` backup concept `[verify]`), CSA CCM (BCR domain), CCCS ITSG-33 contingency planning family. |
| **Effort** | 3–4 days including the restore drill. |
| **UX cost** | **None.** |

### 3.2 Stop bypassing the gate, and make the scanners blocking

| | |
|---|---|
| **What** | Make `quality-and-secrets` a genuinely required status check, and stop force-pushing past it. Set **Trivy to fail** on `HIGH`/`CRITICAL` with an explicit, dated, reviewed allowlist for accepted findings. Add **OSV-Scanner** (broader ecosystem coverage than pip-audit alone) and **Semgrep** OSS rules for the FastAPI/React patterns CodeQL under-covers. |
| **Why first** | Free. It costs nothing to turn on, and "we run scanners" collapses under one question — *"and what happens when one fails?"* — if the honest answer is "we push anyway". |
| **Frameworks** | CISA Secure by Design; NIST SSDF (SP 800-218) practice PW; CSA CCM (AIS, CCC). |
| **Effort** | 1 day. |
| **UX cost** | None to users; a real cost to *us* — the pipeline will start failing. That is the point. |

### 3.3 SBOM + signing + provenance — **Syft, Grype, Cosign, SLSA**

| | |
|---|---|
| **What** | `Syft` generates a CycloneDX/SPDX SBOM per build; `Grype` scans it; `Cosign` (Sigstore) signs the image and attaches the SBOM as an attestation; publish **SLSA build provenance** from GitHub Actions. Optionally `Dependency-Track` to hold SBOMs over time and alert when a *previously shipped* build becomes vulnerable. |
| **Why** | This is the single artifact an OEM partner's security team will ask for by name, and it converts "trust us" into a verifiable claim. |
| **Frameworks** | CISA SBOM guidance; EU CRA Annex I (SBOM + vulnerability handling); NIST SSDF. |
| **Effort** | 2–3 days. |
| **UX cost** | None. |

### 3.4 Container and host hardening — configuration only

| | |
|---|---|
| **What** | In compose: `read_only: true` with explicit `tmpfs`, `cap_drop: [ALL]` plus only what is needed, `security_opt: [no-new-privileges:true]`, a non-root `user:`, `mem_limit`/`cpus`, and a seccomp profile. On the host: `auditd` rules, `AIDE` for file integrity, `fail2ban` on SSH, and **CIS Benchmark** verification via `OpenSCAP` or `Lynis`. |
| **Frameworks** | CIS Docker/Linux Benchmarks; BSI IT-Grundschutz `SYS.1.6` containers `[verify]`; CSA CCM (IVS, UEM). |
| **Effort** | 2 days, mostly testing that nothing breaks. |
| **UX cost** | None. |

## P1 — required before an enterprise pilot signs (4–8 weeks)

### 3.5 Real IAM — **Keycloak** (or **Zitadel** / **Ory**) + **OpenFGA** (or **Cerbos**)

| | |
|---|---|
| **What** | Put an OIDC provider in front. `Keycloak` is the safest choice for a bank conversation — it is the identity server enterprise architects already know, supports OIDC/SAML, external IdP federation, WebAuthn/passkeys, TOTP, and SCIM provisioning via extensions. `Zitadel` is a lighter modern alternative; `Ory Kratos/Hydra/Keto` if we want composable pieces. Authorisation moves to a policy engine — `OpenFGA` (relationship-based, Zanzibar model, right for multi-tenant) or `Cerbos` (simpler, policy-per-resource). |
| **Model** | Tenant → entity → user, with roles `owner / analyst / auditor / api`. Modules (EXPOSURE / COMPLIANCE / RISK) become **entitlements checked in one place server-side** — never an `if` scattered through the UI, exactly as `email_allowed()` is today. |
| **Keep** | Our allowlist and OTP stay as the fallback for direct customers who do not federate. **Do not remove a working path when adding a new one.** |
| **Frameworks** | CISA ZTMM pillar 1 (Identity); CSA CCM (IAM domain); OSFI B-13 §3.2.7 (MFA on external-facing and privileged); CCCS ITSG-33 AC/IA families. |
| **Effort** | 2–3 weeks including migration. |
| **UX cost** | **Positive.** SSO removes a password and an OTP round-trip for enterprise users. Passkeys remove them entirely. This is a rare case where the secure path is the faster path — which is exactly the kind we should prefer. |

### 3.6 The public API, done properly — the OEM blocker

| | |
|---|---|
| **What** | Scoped **API keys per account/entity** (never the session cookie), hashed at rest, prefix-identifiable, rotatable, with last-used telemetry. Per-key rate limits and quotas. A versioned, documented **OpenAPI 3.1** specification — machine-readable, so a partner's gateway can import it. Webhook **push** for critical findings (HMAC-signed payloads, replay-protected with a timestamp + nonce) so a partner's Grafana/Splunk/Elastic ingests without polling. |
| **OSS** | `OpenAPI` + `Redoc`/`Scalar` for docs; `Schemathesis` to fuzz the API against its own schema in CI; `slowapi` or a Caddy rate-limit module for throttling. |
| **Frameworks** | OWASP **API Security Top 10** — map each item explicitly, it is the checklist their AppSec team will use; CSA CCM (AIS). |
| **Effort** | 2 weeks. |
| **UX cost** | None — it is additive. |

### 3.7 Secrets — **OpenBao** (Vault fork) or **SOPS + age**

| | |
|---|---|
| **What** | Minimum viable: `SOPS` + `age` so secrets are encrypted *in git*, reviewable, versioned and rotatable, decrypted only at deploy. Full: `OpenBao` for dynamic secrets, leases and an audit trail of every read. |
| **Also** | Document a rotation schedule and a break-glass procedure. Rotate the current `SESSION_SECRET`, the shared password and every API token as part of the change. |
| **Frameworks** | CSA CCM (CEK); BSI TR-02102 for algorithm choice; OSFI B-13 §3.2.7 (privileged credentials vaulted). |
| **Effort** | 3 days (SOPS) / 1 week (OpenBao). |
| **UX cost** | None. |

### 3.8 Tenant isolation for white-label / OEM

| | |
|---|---|
| **What** | A `tenant_id` on every row, every artifact path and every log line, enforced in **one** data-access layer rather than per query. A test that authenticates as tenant A and attempts every endpoint against tenant B's identifiers, asserting `404`/`403` — the IDOR class, proven rather than assumed. Per-tenant encryption keys if a partner requires cryptographic separation. |
| **Frameworks** | CSA CCM (DSP, IVS); CISA ZTMM (Data pillar). |
| **Effort** | 1–2 weeks. |
| **UX cost** | None. |

### 3.9 Audit log integrity and retention

| | |
|---|---|
| **What** | Ship auth and admin events to append-only storage with a hash chain (each entry includes the previous entry's digest). Separate **audit** retention (typically 12 months `[verify per jurisdiction]`) from operational log retention (30 days today, and our privacy page states it — so Loki's config must actually enforce it, or the page is lying). |
| **OSS** | Loki with per-stream retention; `Vector` for routing; `auditd` on the host. |
| **Frameworks** | CSA CCM (LOG); ITSG-33 AU family; OSFI B-13 P16 (centralised logging and detection). |
| **Effort** | 4 days. |
| **UX cost** | None. |

### 3.10 Business continuity — write the numbers down and prove them

| | |
|---|---|
| **What** | A one-page **BC/DR plan** stating RTO and RPO per service, the restore runbook, and the dependency map (droplet, DNS, ACME, inference endpoint, Telegram, Gmail). Then a **documented restore drill** twice a year: rebuild from the safe-point tag plus a restic snapshot onto a clean host, timed. Our `ship.py --rollback` already gives a fast code-level restore; what is missing is the data half and the evidence. |
| **Frameworks** | **OSFI E-21 is the one with a live date — full adherence 1 Sep 2026** (critical operations identified and mapped, tolerances set, scenario testing begun). CSA CCM (BCR); BSI 200-4 (business continuity). |
| **Effort** | 3 days to write, 1 day per drill. |
| **UX cost** | None. |

## P2 — maturity, do when a specific customer asks (or when revenue justifies it)

| Item | OSS | Note |
|---|---|---|
| **WAF** | `Coraza` (Go, ModSecurity-compatible) + **OWASP Core Rule Set** | Deploy in **detection-only** first. A WAF in blocking mode with default rules will break a legitimate customer request and cost more trust than it saves. |
| **Runtime threat detection** | `Falco` | Syscall-level: unexpected shell in a container, sensitive file reads, outbound connections. High signal on a small estate. |
| **Host security monitoring / FIM** | `Wazuh` (or `OSSEC` + `AIDE`) | Also gives CIS-benchmark scoring and a SIEM-shaped view, which is what auditors expect to see. |
| **Endpoint/host query** | `osquery` | Answers "what is installed, what is listening, what changed" without shelling in. |
| **IaC scanning** | `Checkov` / `Trivy config` / `KICS` | Applies to `tofu/` and the compose files. |
| **DAST** | `OWASP ZAP` baseline scan in CI | Catches the classes SAST cannot see. Keep it to the baseline profile so it stays fast. |
| **Vulnerability disclosure** | `security.txt` (have it) + a written **VDP** and a `SECURITY.md` | Publishing how to report, and the SLA for a response. Cheap; disproportionately reassuring. |
| **Threat modelling** | `OWASP Threat Dragon` or `pytm` | One STRIDE pass per trust boundary, in the repo as a diagram + markdown so it lives with the code. |
| **Chaos / failure drills** | `Pumba` or plain `docker kill` in a runbook | Proves the recovery path rather than assuming it. |
| **AI-specific** | **OWASP Top 10 for LLM Applications** as the checklist; `Rebuff`/`LLM Guard` for prompt-injection heuristics; an **AI BOM** (model ids, versions, vendors, data flows) | We already have the strongest available control here — deterministic post-checks on model output (CVE audit, contract validation, FP audit by a different vendor). Document that, because it is better than what most vendors do. |
| **Isolated egress** | Per-container egress allowlist | The engine talks to a known set of APIs. Everything else denied makes exfiltration visibly hard. |

---

# 4. Framework crosswalk

Read this as *"where each framework will press hardest, and what satisfies it"*. Control IDs are
deliberately sparse — those get verified against the current published version before any
customer-facing use.

| Framework | Where it presses | Our answer after P0+P1 |
|---|---|---|
| **TOGAF** (ADM) | Architecture artifacts, not running code: baseline vs target architecture, requirements traceability, an Architecture Repository, security as a cross-cutting concern in Phases B–D. | This document + a threat model + DFDs + the BC/DR plan constitute the security architecture view. Gap today: we have excellent *implementation* and thin *artifacts*. |
| **CISA** | **Zero Trust Maturity Model v2.0** — five pillars (Identity, Devices, Networks, Applications & Workloads, Data) and three cross-cutting capabilities (Visibility & Analytics, Automation & Orchestration, Governance). Plus **Secure by Design** and SSDF. | Identity → Keycloak+OpenFGA (P1). Applications → SAST/DAST/SBOM/signing (P0). Data → tenant isolation + encryption (P1). Visibility → already strong (Loki/Grafana/alerts). Automation → already very strong (one orchestrator, 35 gates). |
| **BSI** | **IT-Grundschutz** modules and the **C5** criteria catalogue for cloud services; **TR-02102** for cryptographic choices. C5 is the realistic target for a German enterprise buyer. | Backup concept (P0), container hardening (P0), crypto conformance check against TR-02102, and the C5-shaped evidence set. `[verify module IDs]` |
| **CSA** | **Cloud Controls Matrix v4** + CAIQ; STAR Level 1 self-assessment is achievable and free. | **Recommend completing a CAIQ and publishing STAR Level 1.** It is the single highest-leverage credibility artifact available to a small vendor, costs only time, and pre-answers most of a buyer's questionnaire. |
| **Canada — CCCS** | **ITSG-33** control families for a Protected-B-shaped workload; **Cyber Security Readiness Goals**; ITSM.10.089 Top 10. For a bank, OSFI B-13/E-21/B-10 dominate in practice. | Our Canadian compliance module already maps findings to B-13 clauses. For *us as a supplier*: B-10 third-party expectations apply to how RBC assesses **us** — so §2's gaps are literally their B-10 checklist. |
| **Israel — INCD** | **Cyber Defence Methodology for an Organisation** — risk-based, with strong emphasis on continuity, supply chain and incident readiness. | BC/DR plan + drills (P1), supply-chain attestation (P0), documented incident response. |
| **UAE** | **UAE Information Assurance Standard** (NESA/TDRA), and for Abu Dhabi entities the **ADDA/ADSIC** policy. Data-residency and sovereignty questions are prominent. | FRA1 residency is documented; a UAE customer may require regional hosting — our deployment is already one script, so a second region is a configuration change, not a rebuild. |

---

# 5. Zero trust across the layers we actually use

We do not run L1/L2 — we are a container on a managed host. Honest scope:

| Layer | What we run | Zero-trust posture today | After P0+P1 |
|---|---|---|---|
| **L3/L4 — network** | Docker networks, one shared proxy owning :443 | Containers on a **single** network (a second network caused intermittent 502s); no inbound except via the proxy; SSH open to the internet with key-only auth | Per-container egress allowlist; fail2ban; consider WireGuard-only admin access |
| **L5/L6 — session & presentation** | TLS 1.2+ via Caddy/ACME, HSTS | Automatic renewal; strong ciphers by default | Verify against BSI TR-02102; add certificate transparency monitoring for our own domains (we already do it for customers) |
| **L7 — application** | FastAPI + React SPA | Authn on every route, owner-scoped artifacts, traversal guards, bot gate, no API caching in the service worker | OIDC + RBAC, API keys, WAF in detect mode, ZAP baseline in CI |
| **Data** | SQLite + files on a persistent volume | EU residency, owner scoping, synthetic-only staging | Encryption at rest, tenant keys, backups + tested restore, audit-log integrity |
| **Identity** | Allowlist + password + email OTP | Two factors; one shared gate for all front doors | Federated SSO, passkeys, per-tenant roles, SCIM deprovisioning |
| **Workload/supply chain** | Docker, GHCR, GitHub Actions | Immutable commit-based artifact; engine-hash verification container-vs-repo | SBOM + signature + SLSA provenance; verify signature at deploy |
| **"L8" — human/process** | One orchestrator, staging twin, 4-model panel, safe points | Strong. Better than the technical layers. | Add threat model, VDP, incident runbook, restore drill |

---

# 6. Deliberately NOT doing — where security would cost more than it buys

Stating these is part of the architecture. A CISO respects a vendor that has thought about the
trade-off more than one that has bolted on every control it could find.

| Not doing | Why |
|---|---|
| **Forcing MFA on every action** | Step-up authentication belongs on *destructive* or *privileged* actions, not on reading a report. Blanket MFA trains users to click through prompts, which makes them worse at noticing a real one. |
| **A WAF in blocking mode on day one** | Default rule sets false-positive on legitimate traffic. Detection-only first, tune on real traffic, then enforce. |
| **Aggressive session timeouts** | A 15-minute timeout during a 5-minute assessment run is how users learn to keep a second tab open. Bounded session + re-auth on sensitive actions instead. |
| **CAPTCHAs** | They punish humans and barely inconvenience automation. Our path-based bot gate is more effective and completely invisible. |
| **IP blocking / firewall automation** | The host is shared with an unrelated VPN service. Detection-only is a deliberate, documented decision; the response is a 404, an alert, and optionally an AbuseIPDB report. |
| **Password complexity theatre** | Length + a breach-corpus check beats character-class rules, and the enterprise path is SSO anyway. |
| **Client-side security controls** | Anything enforced only in React is decoration. Every control is server-side; the UI merely reflects it. |

---

# 7. Ninety-day plan

| Weeks | Deliverable | Outcome |
|---|---|---|
| **1** | Backups (Litestream + restic) with a restore drill · scanners made blocking · branch protection actually enforced | The two questions we currently fail are answered |
| **2** | SBOM + Cosign signing + SLSA provenance · container/host hardening | An OEM partner can verify what they are shipping |
| **3–4** | Threat model + DFD · BC/DR plan with RTO/RPO · VDP + `SECURITY.md` | The architecture artifacts a TOGAF-shaped review expects |
| **5–8** | Keycloak SSO + OpenFGA roles + module entitlements | Enterprise onboarding stops being blocked |
| **9–10** | API keys, per-tenant rate limits, OpenAPI spec, signed webhooks | The OEM/white-label ask is technically satisfiable |
| **11** | Tenant isolation + the cross-tenant IDOR test suite | White-label is safe to sell |
| **12** | CSA **CAIQ** completed and **STAR Level 1** published · audit-log integrity | A buyer's questionnaire is pre-answered |

**One measure of success:** a prospect's security questionnaire should be answerable from this
document plus the STAR entry, without a call. That is what shortens an enterprise sales cycle from
months to weeks — and it is worth more than any single control on the list.

---

*Not legal advice. Framework mappings marked `[verify]` must be checked against the current
published version of the standard before use in a customer-facing document.*
