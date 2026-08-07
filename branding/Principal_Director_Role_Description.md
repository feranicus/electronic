# Principal Director — AI, Cyber Security, Cloud & Development

**Organisation:** S4Biz Group (Stars4Business OÜ) · Cybergod LLC
**Reports to:** Group Board
**Scope:** Two product lines — **cybergod.ai** (AI cyber assessment and EU compliance platform) and **HERKOS** (sovereign secure mobile platform: contact centre, mobile OS, secure communications, AI oversight)
**Location:** EU · remote-first, EU-resident infrastructure

---

## 1. Purpose of the role

The Principal Director owns the technical and commercial arc of both product lines end to end: architecture, engineering, security assurance, cloud operations, AI model strategy, and the pre-sales motion that turns them into revenue. This is a build-and-sell role, not a supervisory one — the holder writes the architecture, ships the code, defends the design in front of a CISO, and is accountable when a customer-facing artefact is wrong.

Both products address the same market shift: European and Gulf organisations are being required to prove where their data lives, who can read it, and what their externally observable attack surface actually is. The role exists to make those proofs producible by machine, repeatably, in the customer's own jurisdiction.

---

## 2. Scope of ownership

### 2.1 cybergod.ai — AI-driven attack-surface and compliance platform

An assessment engine that takes a single input — a company name or domain — and returns a boardroom-grade risk package without sending a single packet to the target.

- **Passive reconnaissance:** Shodan and Censys, Certificate Transparency, BGP/RPKI and RIR data, passive DNS, WHOIS/RDAP, KEV and EPSS enrichment. Autonomous system, prefix, brand-domain and certificate discovery are resolved by the engine, not hand-fed by the operator.
- **Attribution and scope control:** a layered ownership model — public-suffix-aware domain resolution, per-IP whois co-tenant separation, per-pivot and per-domain contribution budgets, and a record-level attribution gate for shared hosting — designed so that a stranger's infrastructure can never appear in a customer's report.
- **Quantification:** FAIR-based loss modelling (loss-event and threat-event frequency, probable maximum loss, annualised expected loss, return on security investment), MITRE ATT&CK mapping and kill-chain narrative.
- **Deliverables:** four generated presentation decks plus an animated scrollytelling HTML report, produced in multiple document languages, with a post-delivery clarification loop that lets the operator correct scope and trigger a refined re-run.
- **Compliance module:** graded assessment against NIS2, the Cyber Resilience Act and the EU AI Act, with a regime roadmap deck.
- **Delivery surfaces:** a FastAPI backend and React PWA cabinet, plus Telegram bots, behind a shared authentication gate with hardware-independent OTP; six-language interface.

### 2.2 HERKOS — sovereign secure mobile platform

A secure communications estate delivered on open components, hosted on two independent sites inside the customer's jurisdiction.

- **Mobile OS:** Ubuntu Touch 24.04 with the Lomiri shell and Halium hardware layer — read-only root, writable state confined to `/userdata`, `fscrypt v2` data-at-rest encryption, a per-application AppArmor profile, and a private signed application catalogue. Everyday Android applications run isolated in a Waydroid LXC container on a LineageOS image with no Google services.
- **Secure communications:** Matrix/Synapse with end-to-end encryption and MLS for chat and files; Element Call on a LiveKit SFU for encrypted group voice and video; Delta Chat as a PGP-over-email fallback that requires none of the platform's own infrastructure, with metadata minimised per RFC 9788.
- **Contact centre and telephony:** Asterisk with PSTN breakout and SIP endpoints, media relayed through an in-jurisdiction SFU, so interconnect-level interception yields ciphertext only.
- **Censorship- and DPI-resistant transport:** VLESS-Reality on port 443 as primary, AmneziaWG as fallback, wstunnel over WebSocket as third line; mutual TLS between services. Plain WireGuard and OpenVPN are excluded by policy.
- **Identity and PKI:** Keycloak as identity provider, step-ca as internal certificate authority, SPIFFE for workload identity, FIDO2 hardware keys for human authentication, short-lived certificates.
- **Fleet and supply chain:** a self-built, GPG-signed system image with an owned OTA channel and phased rollout; SBOM per build; signature verified in recovery before boot; Fleet and osquery for inventory and live query; Git with `ansible-pull` and commit-signature verification, so nothing is exposed inbound.
- **Detection and AI oversight:** Wazuh, Suricata and osquery feeding Loki and OpenSearch; a four-model inference chain on local vLLM in which two models author an incident analysis and two independently audit it, with only whitelisted containment actions executing automatically.
- **Standards posture:** NIST SP 800-207 zero trust, CISA Secure by Design, BSI TR-02102 and IT-Grundschutz, CSA CCM v4.

---

## 3. Key responsibilities

### Architecture and engineering

- Own the reference architecture for both platforms and the trade-off decisions inside them — protocol selection, isolation boundaries, failure domains, and what is deliberately *not* built.
- Write and maintain production code across the engine, backend, frontend and infrastructure layers. This role is hands-on at the keyboard.
- Maintain a single-command delivery orchestrator: test, commit, push, deploy, and verify in one invocation, with tagged known-good safe points and one-command rollback.
- Prove deployments by artefact, not by liveness: compare content hashes of the running engine inside each container against the repository before reporting success.

### AI engineering and model governance

- Select, benchmark and chain inference models on measured evidence — contract validity, latency under the real production prompt, output depth, cost per assessment, and per-vendor entitlement — never on marketing claims or synthetic probes.
- Maintain multi-vendor failover so no single provider outage or quota ceiling can stop delivery, and enforce vendor separation between an authoring model and its auditor.
- Guard against fabricated identifiers: cross-check every CVE and named incident emitted by a model against the evidence actually collected, strip what cannot be verified, and surface the strip rather than silently rewriting prose.
- Keep a persistent cost ledger with per-user and per-assessment attribution, independent of log retention.

### Cyber security practice and assurance

- Own the finding taxonomy, severity model and remediation templates, including detection of edge security appliances, exposed management planes, secrets managers, NAS and backup consoles, PBX exposure and non-production systems on the perimeter.
- Run and defend the zero-false-positive doctrine: every scope-widening mechanism must produce independent evidence of ownership, and every automatic filter must be bounded so it can neither empty nor gut a report.
- Design guardrails that fail in the safe direction and record their own refusals, so that a declined action is auditable rather than invisible.
- Present findings and quantified risk to CISO and board audiences, and run the technical defence in competitive evaluations.

### Cloud, infrastructure and sovereign hosting

- Own EU-resident hosting, container orchestration, reverse proxy and TLS automation, DNS, and the shared-tenancy isolation that keeps unrelated stacks on the same host from interfering with one another.
- Operate a staging twin matched to production in size, image and region, and gate every production release behind a deploy-and-reboot rehearsal on that twin.
- Own observability end to end — structured event emission, log shipping, dashboards and alerting — including monitoring placed outside the failure domain it watches.
- Own configuration integrity for shared infrastructure: generated rather than hand-edited configuration, write-time validation against the running version and environment, and a runtime watchdog.

### Software engineering and delivery

- Maintain the automated quality gates that block a release: static undefined-name analysis, execution-path tests, deck and artefact rendering tests, internationalisation coverage and key-leak audits, API contract analysis, brand and privacy-copy gates, and a scope-regression suite that replays real historical failures.
- Own internationalisation across interface and generated documents, including the distinction between interface language and document language, and the capability list that advertises which is which.
- Own accessibility and mobile behaviour of the delivered web surfaces, including installable PWA behaviour and offline-safe caching that never caches owner-scoped data.

### Commercial and pre-sales

- Own solution design, scoping, effort estimation, commercial modelling and support-tier definition for both product lines.
- Run pre-sales engagements directly with enterprise and public-sector buyers, and produce the technical content — capability briefs, assessment reports and reference architectures — that carries them.
- Manage partner and reseller enablement, including vendor-neutral remediation guidance so that partners can deliver on their own security stack.

### Governance, compliance and data protection

- Own the GDPR position of the platforms: lawful basis, Article 13 notice, processor and transfer disclosures, data minimisation in telemetry, retention claims that match enforced retention, and accountability logging.
- Own the EU regulatory content of the compliance product — NIS2, CRA, EU AI Act — and keep it current against primary legal texts and national transposition.
- Maintain per-user access control and usage quotas as committed, reviewable configuration rather than out-of-band settings.

---

## 4. Engineering doctrine the role is accountable for

These are the standing principles of the practice. The Principal Director sets them, applies them, and is judged on whether the codebase still obeys them.

1. **Full automation.** Every operational task is a script or a pipeline that runs end to end. If a task is done twice, it becomes code.
2. **One orchestrator, one command.** An operator is never asked to run two scripts. New capability is wired into the orchestrator in the same change.
3. **The repository is the single source of truth.** Infrastructure is provisioned from it and never configured out of band; secrets never enter it.
4. **The model assists, it does not decide side effects.** Inference writes prose and analysis. Deployments, patches, reboots and containment remain deterministic code paths with whitelisted actions.
5. **Absence of evidence is never a finding.** A failed lookup is reported as unavailable, never graded as a customer weakness.
6. **A widening mechanism must prove ownership.** A match is not evidence; corroboration is.
7. **An audit is a signal, not an authority.** An automated reviewer may flag and must never be able to empty the deliverable.
8. **Verify the artefact, not the intention.** A green build, a 200 response or a passing unit test is not proof that the shipped thing is correct.
9. **A check that cannot run is not a check.** Gates execute in an environment where their toolchain is correct by construction, and a silent skip is treated as a defect.

---

## 5. Decision rights

The role holds final technical authority over: platform architecture and protocol selection; the model chain and its ordering; the finding taxonomy and severity model; release gating and rollback; hosting jurisdiction and topology; and the privacy and disclosure copy attached to both products. Commercial pricing, legal entity structure and hiring sit with the Board.

---

## 6. Success measures

- **Attribution accuracy** — proportion of delivered findings attributable to the customer's own estate; false positives in a shipped report treated as a Sev-1 class defect.
- **Delivery integrity** — releases verified by artefact hash; production incidents traced to a gate that was absent, skipped or unenforceable.
- **Assessment economics** — inference cost and wall-clock time per assessment, and enrichment depth coverage, tracked per model and per user.
- **Sovereignty assurance** — demonstrable data residency, key custody and exit path at customer acceptance.
- **Commercial** — qualified pipeline, evaluation-to-contract conversion, and partner-delivered engagements.

---

## 7. Required experience and capability

**Essential**

- Senior hands-on engineering across at least three of: offensive/defensive security, applied AI and LLM systems, cloud and Linux infrastructure, telecommunications and real-time media, or full-stack product development — with credible depth in the rest.
- Demonstrated design and operation of production systems under an adversarial threat model, including state-grade network interference, supply-chain integrity and device seizure.
- Working command of Python, JavaScript/TypeScript, Linux systems engineering, containerisation and CI/CD, and infrastructure automation.
- Practical knowledge of EU cyber and data regulation — NIS2, GDPR, CRA, EU AI Act — sufficient to write defensible customer-facing positions, not merely to cite them.
- Enterprise pre-sales credibility: able to hold a technical evaluation with a CISO and a commercial conversation with a CFO in the same meeting.
- Business-level English and German; Russian an operational advantage for the current customer base.

**Desirable**

- Prior carrier, managed-security-provider or defence-adjacent delivery experience.
- Experience with Matrix, SIP/Asterisk, WebRTC SFU media, or mobile OS integration and OTA distribution.
- Published security research, open-source maintenance, or standards participation.

---

## 8. Technical environment

**AI/ML** — multi-vendor hosted inference with automatic failover, local vLLM, strict-JSON contract enforcement, prompt engineering under token and deadline budgets, cost telemetry.

**Security** — Shodan, Censys, Certificate Transparency, BGP/RPKI, passive DNS, RDAP, KEV/EPSS, MITRE ATT&CK, FAIR, Wazuh, Suricata, osquery, OpenSearch.

**Platform** — Python, FastAPI, React, Vite, PWA, Node, Docker and Compose, Caddy, GitHub Actions, GHCR, Grafana, Loki, Promtail, SQLite and PostgreSQL HA.

**Mobile and comms** — Ubuntu Touch, Lomiri, Halium, AppArmor, fscrypt, Waydroid, LXC, Matrix/Synapse, Element Call, LiveKit, Asterisk, SIP, Delta Chat, VLESS-Reality, AmneziaWG, wstunnel.

**Identity** — Keycloak, step-ca, SPIFFE, FIDO2, mutual TLS.

---

*S4Biz Group · Stars4Business OÜ · Cybergod LLC — [www.cybergod.ai](https://www.cybergod.ai)*
