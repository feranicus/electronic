# Canadian Cyber & Privacy Compliance — Master Reference

**OSFI B-13 · E-21 · B-10 · Integrity and Security · Incident Reporting Advisory · PIPEDA · CCSPA · Quebec Law 25 · CCCS**

Compiled **7 August 2026** from primary sources only (osfi-bsif.gc.ca, laws-lois.justice.gc.ca,
parl.ca, legisquebec.gouv.qc.ca, cai.gouv.qc.ca, cyber.gc.ca, tbs-sct.canada.ca). Every date,
section number and penalty figure below was read on the primary text; the source URL is given.
This is an educational summary, **not legal advice** — confirm scope and classification with
qualified counsel. Canadian federal and provincial rules are moving; re-check before every
engagement and update this file's compilation date when you do.

---

## 0. The five things most vendors get wrong

A Canadian compliance deck that repeats the market's received wisdom will contain at least three
false statements. These are the corrections, each verified:

1. **The CCSPA is NOT in force.** Bill C-26 died on prorogation 6 Jan 2025. Bill C-8 replaced it
   and received Royal Assent **15 June 2026** (S.C. 2026, c. 9), but Part 2 is flagged *"not in
   force"* and **Schedule 2 — the list of designated operator classes — is empty**. As at 7 Aug
   2026 **no Canadian bank has any live, enforceable CCSPA obligation.** Two further
   Governor-in-Council steps are needed first.
2. **The CCSPA "72-hour deadline" does not exist yet.** s. 17 caps what *regulations may prescribe*
   at 72 hours. No regulations exist. Quoting "72 hours" as a current deadline is wrong.
3. **The individual CCSPA AMP maximum is $500,000, not $1,000,000.** It was halved at SECU
   committee on 26 Feb 2026. Every figure still circulating at $1M is stale.
4. **The PIPEDA offence is not limited to record-keeping.** s. 28 also covers knowingly
   contravening **s. 10.1** — the duty to report to the OPC and notify individuals.
5. **Whether Quebec Law 25 binds a federally chartered bank is an open constitutional question.**
   Do not assert that it applies to an FRFI without a legal determination.

**What this means commercially:** the honest Canadian story for a bank is that the *binding* regime
today is **OSFI**, not the headline-grabbing critical-infrastructure act. Say so. It is more useful
than the alternative and it is defensible in front of the bank's own counsel.

---

## 1. The regimes at a glance

| | **OSFI B-13** | **OSFI E-21** | **OSFI B-10** | **OSFI Integrity & Security** | **PIPEDA** | **CCSPA** | **Quebec Law 25** |
|---|---|---|---|---|---|---|---|
| Instrument | Guideline | Guideline | Guideline | Guideline | Statute R.S.C. 1985 c. P-8.6 | S.C. 2026 c. 9 → C-47.4 | CQLR c. P-39.1 |
| Binding? | Supervisory expectation | Supervisory expectation | Supervisory expectation | Supervisory expectation (uses **"must"**) | Law | Law — **NOT IN FORCE** | Law (applicability to FRFI open) |
| Who | All FRFIs incl. foreign branches | All FRFIs incl. foreign branches | All FRFIs; branches from 31 Mar 2025 | All FRFIs | Private-sector orgs, commercial activity | Designated operators (**none yet**) | Enterprises in Quebec |
| Effective | **1 Jan 2024** | Phased: now / **1 Sep 2025** / **1 Sep 2026** / **1 Sep 2027** | **1 May 2024**; branches **31 Mar 2025** | Phased, all four dates now past | 2001; breach rules **1 Nov 2018** | Royal Assent 15 Jun 2026, **not in force** | 22 Sep **2022 / 2023 / 2024** |
| Max penalty | No fine — supervisory intervention | same | same | same | **$100,000** indictable | AMP **$15M** corporate (ceiling on future regs) | AMP **greater of $10M or 2%**; penal **greater of $25M or 4%** |
| Enforcement | OSFI supervision | OSFI | OSFI | OSFI | OPC + Federal Court | Regulator AMPs + courts (once in force) | CAI |

---

# PART 1 — OSFI (the binding regime for a federally regulated financial institution)

## 1.1 Guideline B-13 — Technology and Cyber Risk Management

**Published 31 July 2022. Effective 1 January 2024.** Applies to all FRFIs including foreign bank
branches and foreign insurance company branches.
Source: https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/technology-cyber-risk-management

Three domains, 17 numbered Principles. **This is the guideline an external attack-surface
assessment maps onto**, and the mapping is unusually direct — §3.2.4 uses the words "minimizing its
attack surface".

### Domain 1 — Governance and risk management (Principles 1–3)
- **P1 §1.1** Senior Management assigns responsibility to senior officers (CTO/CIO/CISO).
- **P2 §1.2** Documented, approved, measurable technology and cyber strategy.
- **P3 §1.3** Technology and cyber risk management framework, with risk appetite, taxonomy,
  control domains, and reporting of exposures and trends to Senior Management.

### Domain 2 — Technology operations and resilience (Principles 4–13)
- **P4 §2.1** Architecture framework; §2.1.2 requires **Secure-by-Design and Resilience-by-Design**.
- **P5 §2.2** Asset inventory. **§2.2.3** requires recording and managing asset *configurations*,
  with processes "to identify, assess, and remediate discrepancies from the approved baseline".
  **§2.2.5 technology currency** — continuously monitor currency of software and hardware and
  "proactively implement plans to mitigate and manage risks stemming from unpatched, outdated or
  unsupported assets and replace or upgrade assets before maintenance ceases."
- **P7 §2.4** SDLC. **§2.5.2 segregation of duties** — "the same person cannot develop, authorize,
  execute and move code or releases **between production and non-production technology
  environments**."
- **P9 §2.6** Patch management — timely, controlled, tested before production.
- **P10 §2.7** Incident and problem management.
- **P12/P13 §2.9** Enterprise Disaster Recovery Program and scenario testing.

### Domain 3 — Cyber security (Principles 14–17) — *the core mapping surface*
- **P14 §3.1.3 Vulnerabilities are identified, assessed and ranked** — regular vulnerability
  assessments of "network devices, systems and applications"; rank by severity and exposure;
  "consider the potential **cumulative impact** of vulnerabilities, irrespective of risk level, that
  could present a high-risk exposure when combined."
- **§3.1.5** Continuous situational awareness of the external threat landscape.
- **P15 §3.2.2** Strong cryptographic technologies; regularly assess the cryptography standard
  "to remain effective against current and emerging threats."
- **§3.2.3 Enhanced controls for critical and EXTERNAL-FACING technology assets.**
- **§3.2.4** "Protect networks, **including external-facing services**, from threats by
  **minimizing its attack surface**"; define authorized logical network zones.
- **§3.2.6 Security vulnerabilities are remediated** — timely risk-based patching "in accordance
  with established timelines"; compensating controls where remediation is unavailable (zero-day);
  "regularly monitor and report on patching status and vulnerability remediation against defined
  timelines, including any backlog and exceptions."
- **§3.2.7 Identity and access management** — MFA "across external-facing channels and privileged
  accounts"; privileged credentials in a secure vault.
- **§3.2.8** Security configuration baselines enforced, deviations managed.
- **P16 §3.3** Continuous, centralized security logging and detection.
- **P17 §3.4** Respond, contain, recover, forensics and root-cause analysis.

### Finding-type → B-13 mapping (use this; do not invent principle numbers)

| Finding kind | B-13 clause |
|---|---|
| `edge_appliance`, exposed VPN/firewall admin | §3.2.3, §3.2.4, §3.2.7 |
| `expired_cert`, `self_signed`, weak TLS | §3.2.2 |
| `cve_kev`, unpatched software | §2.6, §3.2.6, §2.2.5 |
| `nonprod_exposed` (dev/test/staging public) | **§2.5.2**, §3.2.3 |
| `snmp_exposed`, management plane public | §3.2.4, §3.2.7 |
| `secrets_manager`, `backup_console`, `nas_exposed` | §3.2.3, §3.2.7 |
| `ecm_exposed`, admin console public | §3.2.3, §3.2.7 |
| `standard_service`, banner/version leakage | §2.2.3, §3.2.8 |
| Estate not fully known to the customer | §2.2.2 (inventory), §3.1.3 |

## 1.2 Guideline E-21 — Operational Risk Management and Resilience

**Published 22 August 2024.** Official title is "Operational Risk Management **and** Resilience".
Source: https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/operational-risk-management-resilience-guideline

⚠️ **The effective dates are NOT in the guideline** — they are only in the accompanying Letter.
Cite the Letter: https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/operational-risk-management-resilience-letter

| Stage | Date | Covers |
|---|---|---|
| Immediate | 22 Aug 2024 | §1 Governance + §2 Operational risk management |
| Milestone 2 | **1 Sep 2025** | §4 — BCM, disaster recovery, crisis mgmt, change mgmt, technology/cyber, third-party, data risk |
| Milestone 3 | **1 Sep 2026** | Full adherence incl. §3 Operational resilience: critical operations identified, mapped, tolerances set; scenario-testing methodology developed and testing begun |
| Milestone 4 | **1 Sep 2027** | Scenario testing **completed for all critical operations** |

**1 September 2026 is the live deadline** — under a month away at the time of writing. That is the
single most actionable date for a Canadian FRFI today.

- **Critical operations** — "services or products that, if disrupted, would put at risk the
  financial institution's continued operations or safety and soundness, or harm other institutions
  due to its interconnectedness to the financial system."
- **§3.1 P6 Mapping** — end to end, considering "people, technology, processes, information,
  facilities, **third parties**, and connections or dependencies among them."
- **§3.2 P7 Tolerances for disruption** — the maximum disruption withstandable under severe but
  plausible scenarios; must consider "Systems, facilities, and third-party suppliers on which
  critical operations depend."
- **§3.3 P8 Scenario testing** — examples named include "Large-scale technology failures",
  "Critical third-party service disruptions", "Cyber incidents".
- **§4.5 Technology and cyber** — E-21 states no controls of its own: "Refer to Guideline B-13."
- **§4.7 Data risk** — dedicated framework; integrity, confidentiality and availability across the
  lifecycle.

**E-21 is the umbrella; B-13 supplies the technical detail.** A control mapping must chain
E-21 §4.5 → B-13.

## 1.3 Guideline B-10 — Third-Party Risk Management

**Published April 2023** (OSFI's own pages carry 24 Apr / 30 Apr / 7 Jul — say "April 2023").
**Effective 1 May 2024**; **foreign bank and foreign insurance branches from 31 March 2025** per the
consequential amendment letter of 22 Feb 2024. Replaced the former B-10 *Outsourcing of Business
Activities, Functions and Processes*.
Sources: https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/third-party-risk-management-guideline
· https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/consequential-amendments-guidelines-b-10-b-13-related-foreign-branches

**Two effective dates must be modelled separately.** Getting this wrong for a foreign branch client
is a visible error.

- **§4 Outcome 6** — "Technology and cyber operations carried out by third parties are transparent,
  reliable and secure." §4.2 requires third parties with elevated technology/cyber risk to comply
  with FRFI or recognized industry standards, "notably in the areas of access management, and data
  security and protection."
- **§4.3/4.4** Cloud — data protection, key management, container management, portability, and
  "strategies (e.g., multi-cloud design) to build resilience and mitigate cloud service provider
  concentration risk."
- **Principle 5 — subcontractors / fourth parties**: "The FRFI is responsible for identifying,
  monitoring and managing risk arising from subcontracting arrangements undertaken by its third
  parties." Contractual levers include the right to refuse a subcontractor and to audit it.
- **§2.4 P10 Monitoring** — at arrangement level *and* aggregate business-unit, platform and
  enterprise level.
- **§2.4.2.2** — contracts must let the FRFI meet the Incident Reporting Advisory, including prompt
  notification of incidents "at the third party **or the subcontractor**".
- **Concentration risk** — institution-specific and systemic, across geography, supplier and
  subcontractor dimensions.

**Relevance to an external attack-surface assessment:** hosts on a third party's infrastructure that
carry the customer's brand, and estate discovered on shared/hoster address space, are B-10 evidence.
This is also why the engine's ownership gate matters commercially — attributing a co-tenant's host
to the customer is a *false* B-10 finding.

## 1.4 Integrity and Security Guideline

**Published 31 January 2024**; four phased dates, **all now past** — fully in force.
Source: https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/integrity-security-guideline

Statutory basis in the OSFI Act. Note §2 uses **"must"**, unusually for OSFI guidance: "Adequate
policies and procedures to protect against threats to integrity or security, including foreign
interference, **must** be established, implemented, maintained, and adhered to."

- **P7 §4.3 Technology assets** — "Technology assets should be secure, **with weaknesses identified
  and addressed**, effective defences in place, and issues identified accurately and promptly."
  Defers to B-13.
- **P8 §4.4** Data and information — controls for data at rest, in transit and in use.
- **P9 §4.5 Third-party risks** — "**Accountability for security cannot be contracted out.**" For
  foreign-interference purposes the FI must consider the third party's and its subcontractors'
  location of operations, location of HQ, connections to foreign governments, and ownership
  structure.
- The threat environment "should be assessed, and internally reported **at least annually**."

**"Weaknesses identified and addressed" plus annual threat-environment reporting is the cleanest
recurring-assessment hook in the whole Canadian set.**

## 1.5 Technology and Cyber Security Incident Reporting Advisory

**Report within 24 hours, or sooner if possible**, to OSFI's Technology Risk Division
(TRD-DRT@osfi-bsif.gc.ca) **and** the Lead Supervisor, in writing on the Incident Reporting and
Resolution Form. Where details are unavailable, state "information not yet available", give best
estimates, and provide regular (e.g. daily) updates until complete.
Source: https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/technology-cyber-security-incident-reporting

**Consequence of not reporting:** increased supervisory oversight, watch-list placement, or a stage
in OSFI's supervisory intervention approach. There is no monetary fine.

> **24 hours (OSFI) is the tightest clock in the Canadian set** — tighter than PIPEDA's "as soon as
> feasible" and tighter than the CCSPA's future 72-hour ceiling.

---

# PART 2 — PIPEDA

*Consolidation read: Act current to 2026-06-17, last amended 2025-03-04.*
Source: https://laws-lois.justice.gc.ca/eng/acts/P-8.6/

## 2.1 The security obligation — Schedule 1, clause 4.7
Schedule 1 has legal force via **s. 5**. **Clause 4.7 — Principle 7, Safeguards**: "Personal
information shall be protected by security safeguards appropriate to the sensitivity of the
information."
- **4.7.1** protects against "loss or theft, as well as unauthorized access, disclosure, copying,
  use, or modification… regardless of the format in which it is held." (**"shall"** — binding)
- **4.7.2** more sensitive information gets higher protection. (**"should"**)
- **4.7.3** physical, organizational and technological measures. (**"should"**)
- **4.1.3** accountability for information transferred to a third party for processing —
  "contractual or other means to provide a comparable level of protection."

**Only the "shall" clauses are enforceable obligations.** 4.7 and 4.7.1 are; 4.7.2 and 4.7.3 are not.

## 2.2 Breach reporting — ss. 10.1–10.3, in force 1 November 2018
- **s. 10.1(1)** report to the Commissioner where "it is reasonable in the circumstances to believe
  that the breach creates a **real risk of significant harm** to an individual" (RROSH).
- **s. 10.1(3)** notify the individual on the same threshold.
- **s. 10.1(7)** *significant harm* "includes bodily harm, humiliation, damage to reputation or
  relationships, loss of employment, business or professional opportunities, financial loss,
  identity theft, negative effects on the credit record and damage to or loss of property."
- **s. 10.1(8)** *real risk* factors: sensitivity; probability of misuse; any prescribed factor.
- **Timing (ss. 10.1(2), 10.1(6))**: "**as soon as feasible** after the organization determines that
  the breach has occurred." **There is no fixed hour count in PIPEDA.**
- **s. 10.3 + SOR/2018-64 s. 6(1)**: keep a record of **every** breach — including those below the
  RROSH threshold — for **24 months** after determining it occurred.
Sources: https://laws-lois.justice.gc.ca/eng/acts/P-8.6/page-3.html ·
https://laws-lois.justice.gc.ca/eng/regulations/SOR-2018-64/FullText.html

## 2.3 Penalties — s. 28
"Every organization that **knowingly** contravenes subsection 8(8), **section 10.1** or subsection
10.3(1) or 27.1(1) or that **obstructs** the Commissioner… is guilty of (a) an offence punishable on
summary conviction and liable to a fine **not exceeding $10,000**; or (b) an indictable offence and
liable to a fine **not exceeding $100,000**."
Source: https://laws-lois.justice.gc.ca/eng/acts/P-8.6/page-5.html

Three points counsel will want stated:
- The mens rea is **"knowingly"** — inadvertent non-reporting is not an offence.
- **There is no penalty for the breach itself**, nor for failing clause 4.7. Clause 4.7 is enforced
  through Commissioner findings, compliance agreements (s. 17.1) and Federal Court applications
  (ss. 14–16), not s. 28.
- **s. 16(c)** lets the Federal Court award damages "including damages for any humiliation" — an
  unbounded exposure that dwarfs the $100,000 cap.
- **PIPEDA has no AMP regime and the OPC has no order-making power.** The contrast with Quebec's
  $25M / 4% is the most striking asymmetry in Canadian privacy law.

## 2.4 Reform — moving, do not quote figures
- **Bill C-27 (CPPA/AIDA) DIED** on the 6 Jan 2025 prorogation.
- **Bill C-36**, *Protecting Privacy and Consumer Data Act* + PIPEDA amendments, first reading
  **15 June 2026**, at second reading. **Its contents are UNVERIFIED — no C-36 figure may enter a
  deck.**
- **PIPEDA has already been amended** by S.C. 2026, c. 3 (Royal Assent 26 Mar 2026) adding
  **Division 1.2 — Mobility of Personal Information** (ss. 10.4–10.5). **Not in force**; no
  regulations. This is the statutory hook for open banking / consumer-directed finance.
Sources: https://www.parl.ca/legisinfo/en/bill/45-1/c-36 · https://laws-lois.justice.gc.ca/eng/acts/P-8.6/nifnev.html

---

# PART 3 — CCSPA (Critical Cyber Systems Protection Act)

## 3.1 Status — the headline
Bill C-8, S.C. 2026 c. 9, **Royal Assent 15 June 2026**. Consolidated as **C-47.4**.
**Part 2 is NOT IN FORCE** — Bill C-8 s. 16: "The provisions of this Part come into force on a day
or days to be fixed by order of the Governor in Council. **[Note: Part 2 not in force.]**"
No coming-into-force order and no regulations appeared in *Canada Gazette* Part II through 29 July
2026, nor proposed regulations in Part I through 1 Aug 2026.
Sources: https://laws-lois.justice.gc.ca/eng/AnnualStatutes/2026_9/page-4.html ·
https://laws-lois.justice.gc.ca/eng/acts/C-47.4/index.html

Part 1 (*Telecommunications Act* amendments) and Part 3 (five-year review) came into force on
Royal Assent.

## 3.2 Schedule 1 — banking IS listed
Six vital services and systems: telecommunications; interprovincial/international pipeline and
power line systems; nuclear energy systems; federally regulated transportation systems;
**item 5 — Banking systems**; **item 6 — Clearing and settlement systems**.
Source: https://laws-lois.justice.gc.ca/eng/acts/C-47.4/page-12.html

## 3.3 Schedule 2 — EMPTY
"Designated operator" is defined *by reference to* Schedule 2, which currently contains its two
column headers and **zero rows**. Therefore **there are no designated operators in enacted Canadian
law today**, and no regulator is paired with banking.
Source: https://laws-lois.justice.gc.ca/eng/acts/C-47.4/page-13.html

s. 2 fixes a closed list of six bodies eligible to be named regulator, including **the
Superintendent** (OSFI) and **the Bank** (of Canada). The Act contains dedicated enforcement blocks
for both. **That OSFI will regulate banking is a structural inference, not enacted law — do not
state it as law.**

## 3.4 Obligations once in force (for planning only)
| Obligation | s. | Detail |
|---|---|---|
| Cyber security programme | **9(1)** | Within **90 days** of joining a Schedule 2 class. Five elements incl. supply-chain and third-party risk. |
| Provide programme to regulator | 10 | Same 90 days |
| Annual review | 13 | Within 60 days; notify regulator within 30 days of completion |
| Supply-chain mitigation | **15** | "**As soon as**" a risk is identified — no grace period |
| Incident report to CSE | **17** | "within a period prescribed by the regulations, **not to exceed 72 hours**" |
| Notify regulator + copy report | 18 | "Immediately after" reporting |

- **s. 18.1** — nothing in ss. 17–18 affects PIPEDA. **Breach reporting runs in parallel.**
- **"Cyber security incident"** means one that "**interferes or may interfere**" with continuity or
  security — **no materiality threshold in the Act**; thresholds are left to regulations
  (s. 135(1)(c)) that do not exist. Until they do, the statutory trigger is unbounded. **This is the
  largest open exposure for a bank and should be flagged as such.**
- **s. 135(2)–(3)** — regulations "must, to the extent possible, ensure consistency with existing
  regulatory and standards regimes", and the Governor in Council **may deem** compliance with such a
  regime to be compliance with the Act. **This is a deemed-compliance hook: a bank already meeting
  OSFI B-13 and E-21 has a direct argument.** Both provisions were added at committee.

## 3.5 Penalties (ceilings on future regulations, not a live tariff)
**s. 91**: AMP maximum **$500,000 for an individual**; **$15,000,000 in any other case**.
The individual figure was **halved from $1,000,000 at SECU on 26 Feb 2026** — any product carrying
$1M is wrong. **s. 94**: a continuing violation is a separate violation **each day**.
**s. 93**: directors and officers who directed, authorized, assented to, acquiesced in or
participated are parties "whether or not the designated operator has been proceeded against".
Source: https://laws-lois.justice.gc.ca/eng/acts/C-47.4/section-91.html

**Criminal offences (ss. 136–138) contain no dollar figures** — fines are at the court's discretion;
imprisonment up to 2 years less a day (summary) or 5 years (indictment); directors and officers
personally liable "even if the designated operator is not prosecuted".

---

# PART 4 — Quebec Law 25

⚠️ **THRESHOLD QUESTION, UNRESOLVED:** whether a **federally chartered bank** is subject to P-39.1,
or instead to PIPEDA by reason of the federal banking power, is a constitutional applicability
question. No primary source read addresses it. **Do not assume P-39.1 applies to an FRFI.** State
the question; let counsel answer it.

*An Act to modernize legislative provisions as regards the protection of personal information*,
(2021, c. 25), assented 22 Sep 2021. Private sector: **CQLR c. P-39.1**.
Source: https://www.legisquebec.gouv.qc.ca/en/document/cs/P-39.1

## 4.1 Phase-in
- **22 Sep 2022** — s. 3.1 person in charge (published on the website); **s. 3.5 incident
  notification to the CAI and affected persons**; s. 3.6 definition; s. 3.7 risk factors;
  **s. 3.8 register of confidentiality incidents**.
- **22 Sep 2023** — the bulk: governance policies (3.2), privacy impact assessments (3.3), collection
  notice (8), profiling transparency (8.1–8.3), **privacy by default (9.1)**, automated
  decision-making (12.1), consent per specific purpose (14), **service providers (18.3)**,
  destruction or anonymization (23), de-indexing (28.1), **and the entire AMP and penal regime**.
- **22 Sep 2024** — s. 27 ¶3 data portability.

**Trap:** **s. 10 (obligation to take necessary security measures) is NOT a Law 25 obligation** — it
has been in force since 14 June 2006. Law 25 made it *enforceable*, via s. 90.1(4) and s. 91(4).

## 4.2 Incident reporting — s. 3.5
Threshold is **"risk of serious injury"** (« risque qu'un préjudice sérieux soit causé »); timing is
**"promptly"** (« avec diligence »). Notify the **CAI** and each affected person; the CAI may order
notification if the enterprise fails. Notification may be withheld only where it could hamper a law
enforcement investigation.

**Règlement sur les incidents de confidentialité** (indexed A-2.1, r. 3.1 — but it **does** apply to
private enterprises via P-39.1 s. 90; the A-2.1 numbering is a codification artefact). In force
**29 Dec 2022**. Notice to the CAI: 11 items. Notices to individuals: 6 items. **Register: retain at
least 5 years**, capturing **all** incidents including those with no risk of serious injury —
contrast PIPEDA's 24 months.
Source: https://www.legisquebec.gouv.qc.ca/fr/document/rc/A-2.1,%20r.%203.1?langCont=en

## 4.3 Penalties
| | Natural person | Enterprise |
|---|---|---|
| **AMP** (s. 90.12) | $50,000 max, no turnover alternative | **greater of $10,000,000 or 2% of worldwide turnover** |
| **Penal** (s. 91) | $5,000 – $100,000 | **$15,000 – greater of $25,000,000 or 4% of worldwide turnover** |
| **Repeat** (s. 92.1) | penal fines **doubled** | penal fines **doubled** |
| **Punitive damages** (s. 93.1) | **≥ $1,000, mandatory, per person** | same |

s. 90.1 grounds include **(3)** failure to report an incident and **(4)** failure to take s. 10
security measures. Under the CAI's *Cadre général* (11 May 2023) a **notice of non-compliance must
precede any AMP**. s. 93.1 punitive damages are mandatory ("shall") with a $1,000 floor per person
where the infringement is intentional or results from gross fault — the class-action driver.

**Operational note:** since **27 May 2025** the CAI no longer publishes the list of organisations
that declared incidents. Any feature relying on that public list is dead.

---

# PART 5 — Canadian Centre for Cyber Security (CCCS)

**All CCCS material is ADVISORY. None of it is legally binding on a private organisation, and CSE
has no regulatory, inspection, audit or enforcement power over private organisations.** Public
Safety Canada, verbatim: "It is important to note that **CSE would not receive any new authorities
under the CCSPA.**" Under CCSPA s. 17, CSE is the incident-report *recipient* and technical adviser
— not the enforcer.

## 5.1 Cyber Security Readiness Goals (CRGs) — the right one for a bank
Effective **29 October 2024**. **36 foundational goals** grouped into the **six pillars of NIST CSF
2.0**. Aimed explicitly at **critical infrastructure**, which under CCSPA Schedule 1 includes
banking systems. For a Canadian bank in 2026 this is materially more current and more on-point than
either of the two below.
Source: https://www.cyber.gc.ca/en/cyber-security-readiness/cyber-security-readiness-goals-securing-our-most-critical-systems

## 5.2 Baseline Cyber Security Controls for Small and Medium Organizations
**V1.2, February 2020. 13 baseline controls** (§3.1–3.13) plus 5 organizational controls. It carries
**no ITSM/ITSAP publication number** — do not assign one. (ITSM.10.189 is the *former* number of the
Top 10, now superseded.)

The 13: 1 Incident Response Plan · 2 Automatically Patch OS and Applications · 3 Enable Security
Software · 4 Securely Configure Devices · 5 Strong User Authentication · 6 Employee Awareness
Training · 7 Backup and Encrypt Data · 8 Secure Mobility · **9 Establish Basic Perimeter Defences**
· 10 Secure Cloud and Outsourced IT Services · **11 Secure Websites** · 12 Access Control and
Authorization · 13 Secure Portable Media.

⚠️ **Scope gate: the document targets organisations with fewer than ~500 employees** (prose §2.1
says "less than 500", normative control OC.1 says "less than 499" — an internal contradiction in
V1.2; quote OC.1 and note it). Injury levels at or below "Medium"; assumed threat level is
cybercrime. **A major bank is outside this document's intended scope on every gate** — cite it for
SMEs, not for an FRFI.
Source: https://www.cyber.gc.ca/en/guidance/baseline-cyber-security-controls-small-and-medium-organizations

## 5.3 Top 10 IT Security Actions — ITSM.10.089
September 2021, effective 24 Sep 2021. Supersedes ITSM.10.189 and ITSB-89 v3.
1 Consolidate, monitor, and defend Internet gateways · 2 Patch operating systems and applications ·
3 Enforce the management of administrative privileges · 4 Harden operating systems and applications
· 5 Segment and separate information · 6 Provide tailored training · 7 Protect information at the
enterprise level · 8 Apply protection at the host level · **9 Isolate web-facing applications** ·
10 Implement application allow lists.
Source: https://www.cyber.gc.ca/en/guidance/top-10-it-security-actions-protect-internet-connected-networks-and-information-itsm10089

## 5.4 ITSG-33
Takes effect 1 Nov 2012; Annex 3A Security Control Catalogue effective 30 Dec 2014. Three control
classes — Management, Technical, Operational. **Target audience is Government of Canada
departments**; nothing extends it to the private sector.

⚠️ **Do NOT write "ITSG-33 is mandatory for GC departments under the Policy on Government
Security."** The full text of the Policy on Government Security, the Directive on Security
Management, its Appendix B and the Directive on Service and Digital were all read: **none mentions
ITSG-33 by name.** What is mandatory is *Appendix B: Mandatory Procedures for Information Technology
Security Control*, which mandates outcomes without prescribing a catalogue. ITSG-33 is the guidance
CSE — the "lead technical authority" — publishes to satisfy those procedures.

**Do not publish an ITSG-33 control count** — the total in Annex 3A is unverified.
Source: https://www.cyber.gc.ca/en/guidance/it-security-risk-management-lifecycle-approach-itsg-33

---

# PART 6 — How to use this in an assessment

## 6.1 Which regimes apply
| Customer shape | Regimes to grade |
|---|---|
| Federally regulated financial institution (bank, insurer, trust) | **B-13, E-21, B-10, Integrity & Security, Incident Reporting Advisory, PIPEDA**; CCSPA as *horizon*; Quebec Law 25 **only if counsel confirms** |
| Foreign bank branch in Canada | Same, noting B-10 applied from **31 Mar 2025** |
| Federally regulated non-financial (telecom, transport, energy) | PIPEDA; CCSPA as horizon (Schedule 1 sectors) |
| Private enterprise, Quebec presence | PIPEDA + **Quebec Law 25**; CCCS advisory |
| Private enterprise, no Quebec presence, not an FRFI | PIPEDA; CCCS advisory |
| SME (<500 employees) | PIPEDA; **CCCS Baseline Controls** are genuinely on-point here |

## 6.2 The deadline that matters right now
**E-21 full adherence — 1 September 2026.** Critical operations identified, mapped, tolerances set,
scenario-testing methodology developed and testing begun. Testing completed for all critical
operations by **1 September 2027**.

## 6.3 Reporting clocks, ranked
1. **OSFI — 24 hours** (or sooner), FRFIs, technology and cyber security incidents.
2. **Quebec CAI — "promptly"**, where there is a risk of serious injury.
3. **PIPEDA OPC — "as soon as feasible"** after determining a RROSH breach occurred.
4. **CCSPA — not yet; ≤72h once regulations exist.**

## 6.4 What must never appear in a Canadian deck
- Any statement that the CCSPA imposes obligations today, or a 72-hour deadline today.
- A $1,000,000 individual CCSPA AMP.
- A PIPEDA fine attached to the breach itself, or to a clause 4.7 failure.
- An assertion that Quebec Law 25 binds a federally chartered bank.
- "ITSG-33 is mandatory", or an ITSG-33 control count.
- CCCS Baseline Controls presented as the applicable framework for a large bank.
- Any Bill C-36 figure.
- Any OSFI *fine* — OSFI's tools are supervisory, not monetary.

## 6.5 Re-check before every engagement
| Watch | Why |
|---|---|
| CCSPA coming-into-force order + Schedule 2 | Nothing in the Gazette as at 1 Aug 2026; the moment a banking class is added, the 90-day programme clock starts |
| CCSPA regulations | Will fix the reporting period (≤72h), the incident threshold, and AMP amounts |
| Bill C-36 | At second reading 15 Jun 2026; would change the PIPEDA picture materially |
| PIPEDA Division 1.2 (data mobility) | Enacted, not in force; the open-banking hook |
| Quebec Bill 82 | Parallel breach notification to the Minister of Cybersecurity; not in force |
| CAI *Rapport quinquennal 2026* (11 Jun 2026) | The likeliest source of the next Law 25 amendments |
| OSFI guidance library | B-13 has not been revised since 2022; confirm before each engagement |

---

## Sources
**OSFI** — [B-13](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/technology-cyber-risk-management) ·
[E-21](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/operational-risk-management-resilience-guideline) ·
[E-21 Letter (effective dates)](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/operational-risk-management-resilience-letter) ·
[B-10](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/third-party-risk-management-guideline) ·
[B-10 effective date](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/osfi-response-draft-guideline-b-10-consultation-feedback-third-party-risk-management) ·
[Foreign-branch amendments](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/consequential-amendments-guidelines-b-10-b-13-related-foreign-branches) ·
[Integrity and Security](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/integrity-security-guideline) ·
[Incident Reporting](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/technology-cyber-security-incident-reporting)

**Federal statutes** — [PIPEDA](https://laws-lois.justice.gc.ca/eng/acts/P-8.6/) ·
[PIPEDA breach Div 1.1](https://laws-lois.justice.gc.ca/eng/acts/P-8.6/page-3.html) ·
[PIPEDA s.28](https://laws-lois.justice.gc.ca/eng/acts/P-8.6/page-5.html) ·
[SOR/2018-64](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2018-64/FullText.html) ·
[CCSPA C-47.4](https://laws-lois.justice.gc.ca/eng/acts/C-47.4/index.html) ·
[CCSPA Sch 1](https://laws-lois.justice.gc.ca/eng/acts/C-47.4/page-12.html) ·
[CCSPA Sch 2](https://laws-lois.justice.gc.ca/eng/acts/C-47.4/page-13.html) ·
[CCSPA s.91](https://laws-lois.justice.gc.ca/eng/acts/C-47.4/section-91.html) ·
[S.C. 2026 c.9 CIF](https://laws-lois.justice.gc.ca/eng/AnnualStatutes/2026_9/page-4.html) ·
[Bill C-8](https://www.parl.ca/legisinfo/en/bill/45-1/c-8) ·
[Bill C-36](https://www.parl.ca/legisinfo/en/bill/45-1/c-36)

**Quebec** — [P-39.1](https://www.legisquebec.gouv.qc.ca/en/document/cs/P-39.1) ·
[Incident Regulation](https://www.legisquebec.gouv.qc.ca/fr/document/rc/A-2.1,%20r.%203.1?langCont=en) ·
[CAI AMP framework](https://www.cai.gouv.qc.ca/uploads/pdfs/CAI_Cadre_Sanct_Pecun.pdf)

**CCCS** — [CRGs](https://www.cyber.gc.ca/en/cyber-security-readiness/cyber-security-readiness-goals-securing-our-most-critical-systems) ·
[Baseline Controls](https://www.cyber.gc.ca/en/guidance/baseline-cyber-security-controls-small-and-medium-organizations) ·
[ITSM.10.089](https://www.cyber.gc.ca/en/guidance/top-10-it-security-actions-protect-internet-connected-networks-and-information-itsm10089) ·
[ITSG-33](https://www.cyber.gc.ca/en/guidance/it-security-risk-management-lifecycle-approach-itsg-33)
