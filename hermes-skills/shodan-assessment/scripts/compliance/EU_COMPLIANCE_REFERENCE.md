# EU Digital & Cyber Compliance — Master Reference

**NIS2 · Cyber Resilience Act · EU AI Act — full requirements, obligations, deadlines, penalties**

Compiled 20 July 2026. Reference document for internal use. Every article reference is to the primary legal text; source links are listed at the end. This is an educational summary, not legal advice — confirm scope and classification with qualified counsel.

---

## 0. The three regimes at a glance

| | **NIS2** | **Cyber Resilience Act (CRA)** | **EU AI Act** |
|---|---|---|---|
| **Instrument** | Directive (EU) 2022/2555 | Regulation (EU) 2024/2847 | Regulation (EU) 2024/1689 |
| **Type** | Directive — via national law | Regulation — directly applicable | Regulation — directly applicable |
| **Regulates** | Cybersecurity of *organisations* (18 sectors) | Cybersecurity of *products with digital elements* | *AI systems* by risk level |
| **Who** | Medium+ entities in scope sectors | Manufacturers, importers, distributors | Providers, deployers, importers, distributors of AI |
| **Core duty** | Risk management + incident reporting + governance | Security by design + vulnerability handling + CE | Tiered duties by AI risk category |
| **Max fine** | €10m / 2% (essential); €7m / 1.4% (important) | €15m / 2.5% | €35m / 7% |
| **In force** | 16 Jan 2023; transposed by MS | 10 Dec 2024 | 1 Aug 2024 |
| **Key dates** | National deadlines (e.g. DE 6 Mar 2026) | Reporting 11 Sep 2026; full 11 Dec 2027 | Bans 2 Feb 2025; high-risk 2 Aug 2026 |
| **Enforcement** | National competent authorities | National market surveillance | National authorities + EU AI Office (GPAI) |

**How they interlock:** an organisation can be caught by all three at once. A connected medical-device maker, for example, is a NIS2 important entity (as an organisation), must classify its connected products under the CRA (unless MDR-exempt), and if it embeds AI in a device is caught by the AI Act as a high-risk provider — all on top of GDPR and sector law.

---

# PART 1 — NIS2 (Directive (EU) 2022/2555)

## 1.1 Purpose and structure

NIS2 replaces the original NIS Directive (2016/1148). It raises the baseline of cybersecurity across the EU by imposing risk-management, incident-reporting and governance duties on medium and large organisations in 18 designated sectors, backed by significant fines and personal management liability. Because it is a *directive*, it binds organisations only through each Member State's transposing national law — so an entity established in several Member States has parallel, independent duties in each.

## 1.2 Scope — who is caught

**Two annexes of sectors:**

- **Annex I — "sectors of high criticality"** (can be *essential* entities if large): energy; transport; banking; financial market infrastructure; health (incl. healthcare providers, EU reference labs, pharma R&D, manufacturers of *critical* medical devices for public-health emergencies); drinking water; waste water; digital infrastructure; ICT service management (B2B); public administration; space.
- **Annex II — "other critical sectors"** (generally *important* entities): postal & courier; waste management; manufacture/distribution of chemicals; production/processing/distribution of food; **manufacturing** (incl. medical devices & IVDs — point 5(a); computers/electronics; electrical equipment; machinery; motor vehicles; other transport equipment); digital providers (marketplaces, search engines, social networks); research organisations.

**Size threshold (Art. 2(1)):** the directive applies to entities that qualify as **medium-sized or above** under Commission Recommendation 2003/361/EC — i.e. **≥ 50 staff, OR annual turnover AND balance sheet each > €10m**. Micro and small entities are generally out, unless specifically designated. Some entity types are in scope *regardless of size* (e.g. certain public electronic-communications providers, trust service providers, TLD/DNS providers, sole providers of a critical service).

**Group / linked-enterprise rule:** size is assessed on **consolidated group data** (Art. 6(2) of the Rec. 2003/361/EC Annex) — 100% of the data of linked enterprises is added. A small subsidiary of a large group is therefore usually in scope. A narrow Member-State option (NIS2 Recital 16) can relieve genuinely independent subsidiaries, but only where the entity is independent in the network-and-information-systems it uses.

**Essential vs important (Art. 3):**

| | Medium-sized | Large |
|---|---|---|
| **Annex I activity** | Important | **Essential** |
| **Annex II activity** | Important | **Important** |

- **Essential entities** face *ex-ante* supervision (proactive audits) and the higher fine tier.
- **Important entities** face *ex-post* supervision (on evidence of a problem) and the lower fine tier.
- Art. 3(1)(a) (size route to *essential*) refers to **Annex I only** — so an Annex II entity is always *important*, however large.

**Scope attaches by operation of law.** NIS2 "applies to" qualifying entities (Art. 2(1)); Recital 8 calls it a "size-cap rule"; Recital 18 describes the Member-State list as an *overview of entities already in scope*. **Registration is declaratory, not constitutive** — an unregistered entity meeting sector+size criteria is in scope and liable; non-registration is a *separate* breach, not a defence.

## 1.3 The four core duties

### (a) Registration / notification (Art. 3(3)–(4))
Member States keep a list of essential/important entities. Entities must submit at least: name; address & up-to-date contacts (incl. email, IP ranges, phone); relevant sector/subsector; Member States where they operate. Changes must be notified within **two weeks**. Mechanism, portal and deadline are set per Member State.

### (b) Cybersecurity risk-management measures (Art. 21)
**Art. 21(1):** entities must take "appropriate and proportionate technical, operational and organisational measures" to manage risks, taking into account the **state of the art**, relevant European/international standards, and cost of implementation, proportionate to exposure, size and likelihood/severity of incidents. "Appropriate and proportionate" is a *calibration* standard, not an opt-out — where a control is disapplied, the reasoning must be documented (reinforced by Commission Implementing Regulation (EU) 2024/2690, Art. 2(2), for the sectors it binds).

**Art. 21(2) — the minimum measures ("shall include at least"):**
1. (a) policies on risk analysis and information system security;
2. (b) incident handling;
3. (c) **business continuity** — backup management, disaster recovery, crisis management;
4. (d) **supply-chain security** — security in relationships with direct suppliers/providers;
5. (e) security in network & information systems acquisition, development and maintenance, incl. vulnerability handling and disclosure;
6. (f) policies/procedures to assess effectiveness of the measures;
7. (g) basic cyber hygiene and cybersecurity training;
8. (h) cryptography and, where appropriate, encryption;
9. (i) human-resources security, access-control policies, asset management;
10. (j) multi-factor / continuous authentication, secured voice/video/text and secured emergency communications, where appropriate.

**Art. 21(3) — supply chain:** entities must take into account vulnerabilities specific to each direct supplier, and the overall quality of products and cybersecurity practices of their suppliers, including secure development procedures, and the results of coordinated risk assessments under Art. 22.

### (c) Incident reporting (Art. 23) — the 24h / 72h / 1-month clock
For any incident with a **significant impact** on service provision:
- **Early warning — within 24 hours** of becoming aware (flag whether suspected malicious/cross-border);
- **Incident notification — within 72 hours** (update the assessment, indicators of compromise);
- **Final report — within one month** — detailed description, severity, root cause, mitigation, cross-border impact.
Intermediate reports on request; for ongoing incidents, a progress report at one month and a final report within one month of handling completion. Where appropriate, recipients of the service must be informed.

### (d) Governance & management liability (Art. 20)
Management bodies of essential and important entities **must approve** the cybersecurity risk-management measures, **oversee implementation**, and **can be held liable** for infringements. Members of management bodies are **required to follow training** (and should offer similar training to staff). This makes the risk decision a board-level, documented function.

## 1.4 Penalties (Art. 34)

- **Essential entities:** administrative fines up to **€10,000,000 or 2%** of total worldwide annual turnover, whichever is higher.
- **Important entities:** up to **€7,000,000 or 1.4%** of total worldwide annual turnover, whichever is higher.
- Fines attach to the turnover of *the undertaking to which the entity belongs* (group level).
- **Essential entities only** (Art. 32(5)): authorities may **suspend certification/authorisation** and impose a **temporary management ban** on CEO/legal-representative level, where lesser measures fail. Art. 33 (important entities) contains no such powers.

## 1.5 Transposition status (indicative, July 2026)

NIS2 binds via national law, so deadlines differ. Snapshot of countries relevant to a multinational:

| Country | Transposed? | Registration deadline | Authority |
|---|---|---|---|
| Germany | In force 6 Dec 2025 (NIS2UmsuCG / BSIG) | Statutory 6 Mar 2026; BSI grace period **31 Jul 2026** | BSI |
| Italy | In force 18 Oct 2024 (D.lgs 138/2024) | Annual window **1 Jan – 28 Feb** | ACN |
| Poland | In force 3 Apr 2026 (amended KSC) | Register by **3 Oct 2026** | national CSIRTs |
| Portugal | In force 3 Apr 2026 (DL 125/2025) | Per CNCS regulation | CNCS |
| Sweden | In force 15 Jan 2026 (Cybersäkerhetslag) | By **30 Sep 2026** | MSB/MCF |
| Netherlands | In force ~15 Aug 2026 (Cyberbeveiligingswet) | Mandatory from entry into force | NCSC |
| Austria | In force 1 Oct 2026 (NISG 2026) | Register by **31 Dec 2026** | Bundesamt für Cybersicherheit |
| France | Not yet in force | ANSSI voluntary pre-registration | ANSSI |
| Spain | Not yet in force | Pending | INCIBE / CCN-CERT |

**German national registers are not public** — external parties cannot verify whether a specific company has registered; only the entity and BSI know.

## 1.6 German transposition specifics (NIS2UmsuCG / BSIG)
- In force 6 December 2025, no transition period. Medical-device manufacturing sits in **Anlage 2, Nr. 5.1** → *wichtige Einrichtung* (important entity) where the size test is met.
- **§ 30 BSIG:** ten mandatory risk-management measures. **§ 32 BSIG:** the 24h / 72h / 1-month incident-reporting cascade. **§ 33 BSIG:** registration. **§ 38 BSIG:** management-body approval, oversight and personal liability + training.
- Late registration is a **separate offence** — up to €500,000. Substantive breaches: important entity up to €7m / 1.4%.

---

# PART 2 — Cyber Resilience Act (Regulation (EU) 2024/2847)

## 2.1 Purpose and structure
The CRA is the EU's horizontal cybersecurity law for **products** (not organisations). It applies to any "product with digital elements" made available on the EU market, requiring cybersecurity to be built in across the lifecycle, backed by CE marking and market surveillance. It is a *regulation* — directly applicable, no national transposition.

## 2.2 Scope

**"Product with digital elements" (PDE):** any software or hardware product and its remote data-processing solutions, whose intended or reasonably foreseeable use includes a direct or indirect logical or physical data connection to a device or network. This captures connected hardware, standalone software, apps, IoT devices, operating systems, and their supporting cloud/back-end components.

**Who is caught:** **manufacturers** (primary duty holder), **importers**, and **distributors** placing PDEs on the EU market.

**The critical carve-out — Art. 2 exclusions.** The CRA does **not** apply to products already covered by specified EU regimes, to avoid double regulation, including:
- **Art. 2(2)(a): Medical devices under Regulation (EU) 2017/745 (MDR)** and IVDs under (EU) 2017/746;
- Art. 2(2): motor vehicles under (EU) 2019/2144; civil aviation; marine equipment.
- The exclusion is **product-based, not company-based**: only the *specific product* that is MDR/etc.-regulated is exempt. A company's *non-medical* connected products, consumer devices, apps and cloud back-ends remain in CRA scope. (Rationale: Recital 25.)

## 2.3 Product classes (risk-based conformity route)
- **Default (majority of products):** self-assessment (internal control).
- **Important products — Class I & Class II (Annex III):** e.g. password managers, network management, VPNs, firewalls, microcontrollers, operating systems — heightened conformity requirements; Class II generally needs third-party assessment or harmonised-standard/scheme conformity.
- **Critical products (Annex IV):** e.g. hardware security modules, smart-meter gateways, smartcards — may require European cybersecurity certification.

## 2.4 Core obligations (essential requirements, Annex I)

**Part I — product security properties.** Products must be designed, developed and produced to ensure an appropriate level of cybersecurity based on the risks, and:
- be made available **without known exploitable vulnerabilities**;
- have a **secure-by-default configuration**, with the ability to reset;
- protect against unauthorised access (authentication, identity/access management);
- protect **confidentiality** (e.g. encryption of stored/transmitted data);
- protect **integrity** of data, commands, configuration;
- process only data that is adequate, relevant and limited (data minimisation);
- protect **availability** and resilience to denial-of-service;
- minimise attack surfaces; mitigate incidents' impact;
- provide security-related information via logging/monitoring;
- ensure vulnerabilities can be fixed through **security updates**, including automatic updates where appropriate.

**Part II — vulnerability handling requirements.** Manufacturers must:
- identify and document vulnerabilities and components (incl. a **software bill of materials — SBOM**);
- **remediate vulnerabilities without delay**, including via free security updates;
- apply effective and regular testing;
- **publicly disclose** fixed vulnerabilities (description, impact, remediation);
- have a **coordinated vulnerability disclosure** policy;
- share information about potential vulnerabilities (contact point);
- provide secure distribution of updates;
- ensure fixes are disseminated without delay and (where appropriate) free of charge, with advisory messages.

**Support period:** security updates must be provided for the product's expected use, **at least 5 years** (or shorter if the product's lifetime is shorter).

**Documentation & CE:** technical documentation, EU declaration of conformity, and **CE marking** are required before placing on the market.

## 2.5 Reporting obligations (Art. 14)
Manufacturers must report to the relevant CSIRT and ENISA, via the **single reporting platform**:
- **Actively exploited vulnerabilities** and **severe incidents** affecting product security;
- **Early warning within 24 hours** of becoming aware → **notification within 72 hours** → **final report within 14 days** (for exploited vulnerabilities; within one month for severe incidents).

## 2.6 Timeline
- **10 December 2024** — entered into force.
- **11 September 2026** — reporting obligations (Art. 14) apply.
- **11 December 2027** — full application: essential requirements, conformity assessment, CE marking, all remaining obligations.

## 2.7 Penalties (Art. 64)
- Breach of the **essential requirements (Annex I)** or the core manufacturer obligations (Art. 13/14): up to **€15,000,000 or 2.5%** of total worldwide annual turnover, whichever is higher.
- Breach of other obligations: up to **€10,000,000 or 2%**.
- Incorrect/incomplete/misleading information to authorities: up to **€5,000,000 or 1%**.
- Market surveillance can also order products **withdrawn or recalled**.

---

# PART 3 — EU AI Act (Regulation (EU) 2024/1689)

## 3.1 Purpose and structure
The AI Act is the EU's horizontal, risk-based law for artificial intelligence. It classifies AI systems into four risk tiers and applies obligations proportionate to risk, plus a separate regime for general-purpose AI (GPAI) models. It is a *regulation* — directly applicable.

## 3.2 Scope and definitions
- **AI system (Art. 3(1)):** a machine-based system designed to operate with varying autonomy, that may exhibit adaptiveness, and that infers from inputs how to generate outputs (predictions, content, recommendations, decisions) influencing physical or virtual environments.
- **Who is caught (Art. 2):** **providers** (develop/place on market), **deployers** (use in a professional capacity), **importers**, **distributors** — including those established outside the EU where the AI output is used in the EU.
- **Exclusions (Art. 2):** AI used **exclusively for military, defence or national security** (Art. 2(3)) — fully out; scientific R&D (Art. 2(6)); pure personal non-professional use; free and open-source components (except where high-risk / GPAI / prohibited). **Dual-use** systems also used for civilian/law-enforcement purposes fall back into scope.

## 3.3 The four risk tiers

### Tier 1 — Prohibited practices (Art. 5) — BANNED (since 2 Feb 2025)
AI systems that:
- deploy subliminal, manipulative or deceptive techniques distorting behaviour causing harm;
- exploit vulnerabilities of age, disability or socio-economic situation;
- perform **social scoring** leading to detrimental/disproportionate treatment;
- assess/predict the risk of a person committing a crime based solely on profiling/personality;
- create/expand facial-recognition databases through **untargeted scraping** of images;
- infer **emotions** in the workplace or education (except medical/safety);
- **biometric categorisation** to deduce race, political opinions, union membership, religion, sex life, sexual orientation;
- **real-time remote biometric identification** in public spaces for law enforcement (narrow exceptions).

### Tier 2 — High-risk (Art. 6 + Annexes I & III) — heavy obligations
**Route A — Annex I (products):** AI that is a **safety component of a product**, or is itself a product, covered by EU harmonisation legislation requiring third-party conformity assessment — e.g. **medical devices (MDR/IVDR)**, machinery, lifts, motor vehicles (type-approval), aviation, toys, PPE.

**Route B — Annex III (standalone use cases):** AI used in:
1. **Biometrics** (remote identification, categorisation, emotion recognition — where not prohibited);
2. **Critical infrastructure** (safety components in the management/operation of digital infrastructure, road traffic, water, gas, heating, electricity);
3. **Education / vocational training** (admission, evaluation of learning outcomes, exam-cheating monitoring);
4. **Employment / worker management** (CV-screening, recruitment, promotion/termination, task allocation, performance monitoring);
5. **Access to essential services** — (a) public benefits/services eligibility; (b) **creditworthiness / credit scoring**; (c) **risk assessment & pricing in life and health insurance**; (d) emergency dispatch/triage;
6. **Law enforcement**;
7. **Migration, asylum and border control**;
8. **Administration of justice and democratic processes**.

### Tier 3 — Limited risk / transparency (Art. 50)
Applies to AI that interacts with people or generates content. Obligations are **transparency only**:
- **inform users** they are interacting with an AI system (chatbots, voice assistants);
- **label AI-generated or manipulated content** (synthetic audio/image/video/text; deepfakes must be disclosed);
- deployers of emotion-recognition or biometric-categorisation systems must inform exposed persons.

### Tier 4 — Minimal risk
Everything else (spam filters, recommendation engines, most enterprise AI, games). **No mandatory obligations** — voluntary codes of conduct encouraged.

## 3.4 High-risk requirements — what providers must do (Art. 8–17)
For a high-risk AI system, the **provider** must:
1. **Risk-management system (Art. 9)** — continuous, iterative across the lifecycle.
2. **Data & data governance (Art. 10)** — training/validation/test data must be relevant, representative, error-minimised, appropriate; bias examination.
3. **Technical documentation (Art. 11 + Annex IV)** — drawn up before market and kept up to date.
4. **Record-keeping / automatic logging (Art. 12)** — traceability of events over the system's lifetime.
5. **Transparency & information to deployers (Art. 13)** — clear instructions for use.
6. **Human oversight (Art. 14)** — design enabling effective human oversight (incl. stop/override).
7. **Accuracy, robustness & cybersecurity (Art. 15)** — appropriate levels declared and maintained; resilience to errors and adversarial attacks.
8. **Quality management system (Art. 17)**.
Plus: registration in the **EU database** (Art. 49/71), a **conformity assessment** and **CE marking** before placing on the market, corrective action and duty to inform (Art. 20), and cooperation with authorities (Art. 21).

**Deployer obligations (Art. 26):** use per instructions; ensure human oversight; monitor operation and suspend/report if risks arise; keep logs; inform affected workers/persons; and, for public bodies and certain essential-service providers, complete a **fundamental-rights impact assessment (Art. 27)**.

## 3.5 General-purpose AI models (Chapter V, Art. 51–56)
**All GPAI providers (Art. 53):** technical documentation; information/documentation to downstream providers; a **copyright policy**; a **public summary of training data**.
**GPAI with systemic risk (Art. 55)** (models above a compute threshold, e.g. ≥10²⁵ FLOPs): additional model evaluation/red-teaming, systemic-risk assessment & mitigation, incident reporting, and cybersecurity protection.
Enforced by the **EU AI Office**; fines up to **€15m or 3%** (Art. 101).

## 3.6 Timeline (Art. 113)
- **1 August 2024** — entered into force.
- **2 February 2025** — prohibited practices (Art. 5) + AI-literacy duties (Art. 4) apply.
- **2 August 2025** — GPAI obligations, governance structures, penalties/enforcement powers, notifying authorities apply.
- **2 August 2026** — **general application**: high-risk systems under Annex III + transparency obligations (Art. 50) become enforceable. ← current major deadline.
- **2 August 2027** — high-risk AI that is a safety component of products under Annex I (e.g. medical devices) + GPAI models placed before Aug 2025 must comply.

## 3.7 Penalties (Art. 99 & 101)
- **Art. 99(3):** non-compliance with the **Art. 5 prohibitions** → up to **€35,000,000 or 7%** of total worldwide annual turnover, whichever is higher.
- **Art. 99(4):** breach of operator/high-risk/transparency duties (Art. 16, 22, 23, 24, 26, 50) → up to **€15,000,000 or 3%**.
- **Art. 99(5):** incorrect/incomplete/misleading info to authorities → up to **€7,500,000 or 1%**.
- **Art. 99(6):** for **SMEs/start-ups**, the fine is the **lower** of the fixed amount or the percentage.
- **Art. 101:** GPAI model providers — fines by the Commission up to **€15,000,000 or 3%**.
- Enforcement status: no publicly reported AI Act fines as of mid-2026; the prohibitions and penalty powers are already live.

---

# PART 4 — Cross-cutting and adjacent regimes

## 4.1 How the three overlap
- **Organisation vs product vs AI.** NIS2 regulates the *organisation's* cybersecurity; the CRA regulates the *product's* cybersecurity; the AI Act regulates the *AI system's* risk. A single company can hold all three duty sets simultaneously.
- **CRA ↔ MDR:** MDR-regulated medical devices are carved out of the CRA (Art. 2(2)(a)); their cybersecurity is governed by MDR Annex I 17.2/17.4 + MDCG 2019-16 instead.
- **AI Act ↔ MDR:** an AI-based medical device is high-risk under AI Act Annex I *and* an MDR device — it must satisfy both, ideally via a combined conformity assessment.
- **AI Act ↔ CRA:** high-risk AI systems must meet cybersecurity requirements (Art. 15); compliance with CRA essential requirements can help demonstrate this for products in CRA scope.
- **NIS2 ↔ everything:** NIS2 Art. 21(2)(d)/(3) pushes supplier-security requirements down the chain, so even out-of-scope suppliers get vetted by their in-scope customers.

## 4.2 Adjacent mandatory regimes (quick reference)
- **GDPR (Reg. (EU) 2016/679):** Art. 32 security incl. availability/resilience; Art. 33 breach notification within 72 hours. Fines up to €20m / 4% (core), €10m / 2% for Art. 32/33-tier breaches.
- **DORA (Reg. (EU) 2022/2554):** ICT operational-resilience regime for financial entities and their critical ICT providers; national fines, and up to 1% of average daily worldwide turnover per day for critical ICT third-party providers.
- **EU MDR (Reg. (EU) 2017/745):** device cybersecurity under Annex I 17.2/17.4; guidance MDCG 2019-16; penalties set by Member States.
- **Switzerland:** revFADP Art. 8 + Data Protection Ordinance (availability); Information Security Act reporting (critical-infrastructure operators only); Medical Devices Ordinance mirrors MDR.
- **Not in scope (common confusion):** German **KRITIS** = critical-infrastructure operators only (a manufacturer is not KRITIS); **UK NIS Regulations 2018** = essential-service operators / digital providers only.

## 4.3 Consolidated deadline calendar (2026–2027)
| Date | Milestone |
|---|---|
| 6 Mar 2026 | German NIS2 registration statutory deadline (grace to 31 Jul 2026) |
| 15 Aug 2026 | Netherlands NIS2 law in force |
| **2 Aug 2026** | **AI Act: high-risk + transparency obligations apply** |
| 11 Sep 2026 | **CRA: incident & vulnerability reporting begins** |
| 30 Sep 2026 | Sweden NIS2 registration deadline |
| 1 Oct 2026 | Austria NIS2 law in force |
| 3 Oct 2026 | Poland NIS2 registration deadline |
| 31 Dec 2026 | Austria NIS2 registration deadline |
| Jan–Feb 2027 | Italy NIS2 annual registration window |
| **11 Dec 2027** | **CRA: full product requirements apply** |
| 2 Aug 2027 | AI Act: embedded high-risk (Annex I) + pre-2025 GPAI |

---

# PART 5 — Sources (primary + official)

**NIS2**
- Directive (EU) 2022/2555 — https://eur-lex.europa.eu/eli/dir/2022/2555/oj
- Commission Implementing Regulation (EU) 2024/2690 — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402690
- Commission Recommendation 2003/361/EC (SME definition) — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32003H0361
- ENISA NIS2 Technical Implementation Guidance — https://www.enisa.europa.eu/publications/nis2-technical-implementation-guidance
- German BSI — NIS-2 obligations — https://www.bsi.bund.de/DE/Themen/Regulierte-Wirtschaft/NIS-2-regulierte-Unternehmen/NIS-2-Pflichten/nis-2-pflichten_node.html
- German BSI Act § 33 (registration) — https://www.gesetze-im-internet.de/bsig_2025/__33.html

**Cyber Resilience Act**
- Regulation (EU) 2024/2847 — https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847
- Commission — CRA overview — https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act
- Commission — CRA reporting obligations — https://digital-strategy.ec.europa.eu/en/policies/cra-reporting

**EU AI Act**
- Regulation (EU) 2024/1689 — https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Article 99 (penalties) — https://artificialintelligenceact.eu/article/99/
- Article 113 (application dates) — https://artificialintelligenceact.eu/article/113/
- Annex III (high-risk use cases) — https://artificialintelligenceact.eu/annex/3/
- Article 2 (scope & defence exclusion) — https://artificialintelligenceact.eu/article/2/
- Implementation timeline — https://artificialintelligenceact.eu/implementation-timeline/
- Commission — AI Act governance & enforcement — https://digital-strategy.ec.europa.eu/en/policies/ai-act-governance-and-enforcement

**Adjacent**
- GDPR (Reg. (EU) 2016/679) Art. 32 — https://gdpr-info.eu/art-32-gdpr/
- DORA (Reg. (EU) 2022/2554) — https://eur-lex.europa.eu/eli/reg/2022/2554/oj
- EU MDR (Reg. (EU) 2017/745) — https://eur-lex.europa.eu/eli/reg/2017/745/oj
- MDCG 2019-16 (device cybersecurity) — https://health.ec.europa.eu/system/files/2022-01/md_cybersecurity_en.pdf

---

*Prepared as an internal reference, 20 July 2026. Statutory maxima and application dates are stated as at this date; national NIS2 transpositions were moving quickly and should be re-checked. Not legal advice.*
