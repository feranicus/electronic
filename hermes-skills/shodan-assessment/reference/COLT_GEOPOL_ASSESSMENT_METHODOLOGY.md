# GEOPOL Assessment Report — Methodology

**Canonical recipe for the Colt / S4Biz Geo-Political Cyber Threat Assessment ("GEOPOL")**

This document is the product definition and build recipe for the GEOPOL Assessment Report: a strategic, intelligence-led deep dive that maps the **named adversaries** — nation-state actors, state-aligned crews, organised eCrime, and hacktivists — that could realistically target and **halt the operations** of a specific large enterprise or bank, and ties each threat to evidence, business impact, and a remediation/portfolio fit.

GEOPOL is the **threat-actor and geopolitical attribution layer** of the Colt sales-engineering product suite. It sits on top of, and consumes, the two existing products:

- **Shodan External Attack Surface Assessment** (`COLT_SHODAN_DECK_METHODOLOGY.md`) — the *what is exposed* layer (CVEs, KEV, certs, edge devices).
- **C-BIQ Business Impact Quantification** (`06-business-impact-quantification.md`) — the *what it costs in euros* layer.

GEOPOL answers the third question the other two don't: **who would come for this customer, why, how, and what would it take to stop them.** Use the Colt design system (`COLT_DESIGN_SYSTEM.md`) for all visual output — palette, chevrons, evidence blocks, severity badges are unchanged.

> **Worked reference build:** J. Safra Sarasin × Saxo Bank (`Safra_GEOPOL_Assessment_Internal.pptx`, June 2026). Anchor case study: **Turla / "Secret Blizzard" / Kazuar** (Microsoft Threat Intelligence, 14 May 2026).

---

## 1. When to Use This Format

Use GEOPOL when:

- The customer is a **large, geopolitically-exposed organisation** — a bank, insurer, critical-infrastructure operator, defence-adjacent manufacturer, or a multinational with cross-border data and sanctions exposure (ECB, Commerzbank, BASF, SGL Carbon, Raiffeisen, J. Safra Sarasin, Saxo, Helvetia, Medela-class).
- The conversation needs to move **above** the attack-surface findings to *strategic* threat intelligence — board-level "who is the adversary and why us" — not just "here are 23 exposed hosts."
- There is a triggering event: an **M&A** (new combined attack surface and two threat models), a **sanctions/geopolitical** posture change, a **regulator-mandated** intelligence-led test (TIBER-EU / DORA TLPT / CBEST / FINMA Circ. 2023/1), or a peer breach in the same sector.

Do **not** use GEOPOL when:

- The engagement is a pure technical scan with no strategic audience (use the Shodan findings deck alone).
- The customer wants only a euro-denominated risk number (use C-BIQ alone).
- There is no real intelligence basis — GEOPOL must be grounded in **named, sourced** threat reporting. A GEOPOL report with invented actors or unsourced attribution is worse than no report. Evidence discipline is the entire value.

GEOPOL is **strategic CTI**. Pair it with the Shodan deck (operational/tactical) and C-BIQ (financial) for a full three-layer account narrative.

---

## 2. The Methodology Stack — What GEOPOL Is Built On

GEOPOL does not invent a framework. It composes a defensible stack of established, citable methodologies, one per analytical job. The methodology slide presents these as a layered diagram.

### 2.1 Analytical frameworks (the rigor layer)

| Framework | Owner / origin | Job in GEOPOL |
|---|---|---|
| **MITRE ATT&CK** (Enterprise, Groups, Software) | MITRE | The common TTP taxonomy. Every actor's behaviours and every finding map to ATT&CK technique IDs. Groups pages anchor actor attribution. |
| **Diamond Model of Intrusion Analysis** | Caltagirone/Pendergast/Betz, 2013 | Each intrusion as Adversary · Capability · Infrastructure · Victim. Drives pivoting and campaign clustering. The actor-card is a Diamond in disguise. |
| **Lockheed Martin Cyber Kill Chain** | Lockheed Martin, 2011 | The seven-phase narrative spine for "how an attack on this customer would unfold." Recon → Weaponise → Deliver → Exploit → Install → C2 → Actions. |
| **Analysis of Competing Hypotheses (ACH) + Structured Analytic Techniques** | Richards J. Heuer Jr. / CIA tradecraft | Bias control on attribution. Enumerate hypotheses, disprove rather than confirm. Keeps "who did it / who would" honest. |
| **Admiralty (NATO AJP-2.1) source grading** | NATO / Five Eyes | Every intelligence claim gets a source-reliability (A–F) × credibility (1–6) grade. The confidence discipline of the report. |
| **CTI levels — strategic / operational / tactical** | Industry standard | GEOPOL is primarily **strategic** (board: who/why), with an operational TTP layer beneath. Tactical IOCs stay in the appendix. |
| **CVSS + EPSS + CISA KEV** | FIRST.org / CISA | Vulnerability triage: KEV = actively exploited (top of queue); EPSS = probability of exploitation; CVSS = severity magnitude. Combine, don't pick one. |
| **Pyramid of Pain** | David Bianco, 2013 | Justifies a TTP-led (not IOC-led) posture: detecting at the TTP apex forces adversary re-tooling. |
| **FAIR (Factor Analysis of Information Risk)** | Open Group / FAIR Institute | The bridge to C-BIQ: translate a GEOPOL scenario into a probable-loss distribution in euros. |

### 2.2 Intelligence-led red-team frameworks (the regulator bridge)

GEOPOL's intelligence output is designed to feed the **"targeted threat intelligence"** phase of a regulator-mandated red-team test. This is the natural downstream sale.

| Framework | Body | Jurisdiction | Note |
|---|---|---|---|
| **TIBER-EU** | ECB | Eurozone | The European umbrella; threat-intel → red-team → purple-team. |
| **DORA TLPT** (Threat-Led Penetration Testing) | EU (Reg. 2022/2554) | EU financial entities | Applicable since 17 Jan 2025; TLPT on live systems ≥ every 3 yrs for significant entities; RTS published 18 Jun 2025. |
| **CBEST** | Bank of England | UK | The original (2014) intelligence-led model TIBER is based on. |
| **iCAST** (Intelligence-led Cyber Attack Simulation Testing) | HKMA | Hong Kong | Phase of the Cyber Fortification Initiative / C-RAF. |
| **AASE** (Adversarial Attack Simulation Exercises) | ABS / MAS | Singapore | ABS Red Team guidelines; MAS TRM. |
| **CORIE** | Council of Financial Regulators | Australia | Cyber Operational Resilience Intelligence-led Exercises. |

### 2.3 National & supranational anchor bodies (cite the customer's regulator)

Cite the bodies whose frameworks the customer's regulator actually enforces, plus the national CERT whose threat assessments ground the geopolitics.

| Body | Country / bloc | Why cite it |
|---|---|---|
| **CISA** + US Treasury **OFAC** / **FinCEN** + **FS-ISAC** | USA | KEV catalogue, joint advisories, ransomware-payment **sanctions** advisories. FS-ISAC = the financial-sector sharing forum. |
| **NCSC-UK** | UK | Technical authority; CBEST support. |
| **ECB** (TIBER-EU) · **ENISA** (Threat Landscape, NIS2) | EU | DORA / TLPT backbone; ENISA ETL for sector framing. |
| **BSI** (+ BaFin **BAIT**) | Germany | German bank IT/cyber requirements (for Commerzbank-class accounts). |
| **FINMA** (Circ. **2023/1** Operational risks & resilience) · **BACS** (formerly NCSC-CH / MELANI / GovCERT.ch) | Switzerland | **Binding for Swiss banks.** BACS publishes the Swiss DDoS/threat reporting (e.g. NoName057(16) analyses). |
| **CFCS — Center for Cybersikkerhed** (Danish Defence Intelligence) | Denmark | National threat authority; publishes "The Cyber Threat Against Denmark" (5-level scale). Distinct from the financial supervisor **Finanstilsynet**. |
| **CSA Singapore** + **MAS** TRM / **AASE** | Singapore | APAC anchor for regional accounts. |
| **INCD**, **Shin Bet (Shabak)**, **Unit 8200**, **ICT at Reichman/Herzliya** | Israel | Ecosystem and talent reference; ICT = academic counter-terror/cyber institute. (Intelligence services inform the ecosystem; they are not public-framework publishers.) |
| **BACEN / CMN Resolution 4.893** | Brazil | Brazilian bank cyber-policy mandate (for Banco Safra-class entities). |
| Consultancy methods: **Mandiant/GTIG** (APT/UNC tracking, ICD maturity), **Control Risks** (RiskMap), **Booz Allen** (Global4Sight) | — | Mandiant is the most citable for attribution methodology. McKinsey/BCG/Bain publish thought-leadership, **not** a standardised, citable cyber-geopolitical methodology — frame, don't cite. |

> **Disambiguation flags carried from research (state on the caveats slide):** "DFSA" for the customer means **Finanstilsynet (Danish FSA)**, not Dubai FSA. The Herzliya body is the **ICT at Reichman University (Merkaz Beintchumi)**; "IICC" may denote a separate organisation — confirm before citing. "FEER" could not be confirmed as an established framework — do not cite it as one.

---

## 3. Threat-Actor Taxonomy & Tiering

Every GEOPOL report profiles named actors across four bands. The bands are fixed; the actors are selected for the specific customer. **Relevance, not fame, drives inclusion** — an actor goes in only if there is a sourced reason it would target *this* customer.

### 3.1 The four actor bands

| Band | Definition | Typical motivation |
|---|---|---|
| **NATION-STATE** | State intelligence/military services and their named clusters | Espionage, pre-positioning, disruption |
| **STATE-ALIGNED / PROXY** | State-funded theft crews and contractors | Revenue for the regime, sanctions evasion |
| **ORGANISED eCRIME** | Financially-motivated intrusion specialists, RaaS, IABs | Theft, extortion |
| **HACKTIVIST / DISRUPTIVE** | Ideologically-motivated DDoS/defacement collectives | Disruption, political signalling |

### 3.2 The standing actor library (reuse and select)

These profiles are validated and reusable. Select the subset relevant to each customer; never paste all of them. Each carries vendor cryptonyms (Microsoft "weather" names, CrowdStrike, Mandiant APT#), sponsor, motivation, ATT&CK-mapped TTPs, and a named bank/finance campaign.

**Nation-state (espionage / disruption)**
- **Turla — "Secret Blizzard"** (Russia, FSB Center 16). MITRE G0010. Snake/Uroburos/Venomous Bear. **Anchor case: Kazuar** — a modular P2P botnet (Kernel/Bridge/Worker modules, single elected leader for low-observable C2, EWS/HTTP/WSS fallback channels, working-hours exfil blackout). Espionage, long-dwell. *Relevance to a private bank: indirect collection risk via politically-exposed clients, not theft.*
- **APT29 — "Midnight Blizzard" / Cozy Bear** (Russia, SVR). G0016. Cloud-native: OAuth abuse, federated-trust manipulation, password spray (T1078.004), supply-chain (SolarWinds). *Relevance: identity/SSO + supply-chain pivot.*
- **Sandworm — "Seashell Blizzard" / APT44** (Russia, GRU Unit 74455). G0034. Destructive wipers (NotPetya, Olympic Destroyer), ICS/OT. *Relevance: NotPetya-style spillover tail-risk.*
- **APT28 — "Forest Blizzard" / Fancy Bear** (Russia, GRU Unit 26165). G0007. Credential harvest, CVE exploitation (GooseEgg/CVE-2022-38028). *Swiss precedent: targeted the Spiez lab & OPCW (2018).*

**State-aligned theft (highest-relevance state cluster for banks)**
- **Lazarus / APT38 / Hidden Cobra** (DPRK, RGB). G0032 / G0082. **SWIFT abuse** (Bangladesh Bank / NY Fed, 2016 — USD 81m), **FASTCash** ATM cash-out (CISA AA20-239A). *Relevance: HIGH — directly targets correspondent-banking rails.*
- **BlueNoroff / "Sapphire Sleet" / TraderTraitor** (DPRK). G0082 sub-cluster. Deepfake-recruiter social engineering, supply-chain. **Bybit, Feb 2025 — ~USD 1.5bn** (Safe{Wallet} supply chain; FBI-attributed). *Relevance: HIGH for crypto/trading surface.*

**Organised eCrime (the most probable *direct* tier)**
- **Scattered Spider — "Octo Tempest" / UNC3944** (eCrime, EN-speaking). G1015. **Help-desk social engineering**: vishing (T1566.004), MFA push-bombing (T1621), SIM-swap, **adds rogue federated IdP to victim SSO (T1484.002)** for persistence; BlackCat/ALPHV. CISA AA23-320A. *Relevance: VERY HIGH — most probable direct intrusion vector for a cloud-SSO, help-desk-reliant bank.*
- **Evil Corp — "Indrik Spider" / UNC2165** (Russia). Dridex (>USD 100m, 40+ countries). **OFAC-sanctioned Dec 2019**; rotates ransomware brands (WastedLocker→Hades→LockBit) to evade attribution. *Relevance: HIGH + sanctions-payment landmine for the US entity.*
- **FIN7 — "Sangria Tempest" / Carbon Spider** (eCrime). G0046. Carbanak, Cobalt Strike. Carbanak/FIN7 cluster >USD 1bn. *Relevance: HIGH, mature financial-sector specialist.*
- **Carbanak / Cobalt Group** (eCrime). G0008. Bank-internal manipulation, ATM jackpotting. *Relevance: HIGH (banking specialist), legacy TTP template.*
- **TA505 — "Spandex Tempest"** (eCrime). G0092. Dridex, Locky, now **Cl0p**. *Relevance: HIGH — banking-trojan + mass-extortion nexus.*
- **RaaS families**: **LockBit** (AA23-165A), **ALPHV/BlackCat** (AA23-353A; help-desk overlap with Scattered Spider), **Cl0p** (MOVEit / CVE-2023-34362 mass-exploitation — 2,000+ orgs), **Black Basta** (fed by Qakbot). *Relevance: HIGH — dominant realised extortion risk; Cl0p edge-appliance zero-day = third-party risk.*
- **Banking-trojan / IAB ecosystem**: Dridex (S0384), Qakbot, IcedID, Gozi/ISFB/Ursnif, Emotet — shared loader infrastructure; feed the crews above. *Relevance: HIGH for retail-facing entities (account-takeover fraud).*

**Hacktivist / disruptive**
- **NoName057(16)** (pro-Russia DDoS, DDoSia). Hit **Danish banks (Jun 2022)**; **Switzerland repeatedly** — Zelensky address (Jun 2023, analysed by NCSC-CH), Bürgenstock summit (Jun 2024), **WEF/Davos (Jan 2025)**. *Relevance: HIGH availability risk / LOW data risk; "nuisance-level," event-timed.*
- **Killnet** (pro-Russia DDoS syndicate). European banking/critical-sector campaigns. *Relevance: moderate availability risk; current cohesion to be verified per-engagement.*

### 3.3 Geopolitical exposure mapping

For each customer, write a jurisdiction-by-jurisdiction exposure table — the bridge between "the company" and "the adversary." Worked example (Safra × Saxo):

| Jurisdiction | Entity | Distinct exposure |
|---|---|---|
| **Switzerland** | Bank J. Safra Sarasin | FINMA-regulated; Switzerland adopted EU Russia sanctions (Feb 2022) → sanctions-enforcement node & pro-Russian retaliation target; UHNWI client base = high-value spear-phishing/BEC. |
| **Denmark** | Saxo Bank | DFSA (Finanstilsynet); NATO member; large retail-trading internet surface (APIs, login, market data) → DDoS / credential-stuffing; early NoName057(16) target. |
| **Brazil** | Banco Safra | Retail/commercial footprint → banking-trojan ecosystem, PIX fraud. |
| **USA** | Safra National Bank of NY | US charter → **OFAC nexus** + Fed/SWIFT correspondent rails (the exact Lazarus/Bangladesh-Bank chokepoint). |

---

## 4. Scoring & Confidence

GEOPOL uses three scoring instruments. State the rubric explicitly on the methodology slide so judgments are reproducible.

### 4.1 Actor relevance tiering (the headline score)

Each profiled actor gets a **relevance tier** mapped to the deck's severity palette, derived from *Intent × Capability × Exposure-fit*:

| Tier | Colour | Meaning |
|---|---|---|
| **CRITICAL** | red `F20C36` | Demonstrated intent + capability against this customer's exact profile/sector/rails. (e.g. Scattered Spider, Lazarus/APT38 for a bank.) |
| **HIGH** | orange `FF7900` | Strong sector/jurisdiction relevance; realistic direct threat. (FIN7, TA505, RaaS, Evil Corp.) |
| **MEDIUM** | amber `FFC33C` | Contextual: capable but indirect, or availability-only. (APT29 identity-pivot, NoName057(16) DDoS.) |
| **LOW** | gray `474946` | Tail-risk / collection-only / spillover. (Turla, APT28, Sandworm.) |

### 4.2 Admiralty source grading (the confidence score)

Every intelligence claim and attribution carries an Admiralty grade: **source reliability A–F × information credibility 1–6** (e.g. a CISA joint advisory ≈ **A1**; a single-vendor blog corroborated by a second ≈ **B2**; uncorroborated forum chatter ≈ **D4**). Put the grade in the evidence block. This is what separates GEOPOL from threat-actor fan-fiction.

### 4.3 Vulnerability triage (the exploit score, shared with the Shodan layer)

Where GEOPOL references a specific CVE an actor is known to exploit against the customer's exposed estate (pulled from the Shodan layer), score it **KEV-listed? + EPSS probability + CVSS magnitude** — never CVSS alone. KEV jumps the queue; high EPSS flags imminence even at modest CVSS.

---

## 5. Deck Structure — 30 Slides

Fixed structure. Uses the Colt design system chrome (title teal slide, section dividers with 90pt Arial Black + trailing period, content-slide eyebrow/title, chevron tracer, evidence blocks). Mark every page `INTERNAL — COLT / S4Biz CONFIDENTIAL · NOT FOR EXTERNAL DISTRIBUTION`.

| Slide | Purpose | Key elements |
|---|---|---|
| 1 | Title | Customer name, entities/ASNs, date, classification, prepared-by, frameworks cited |
| 2 | Executive Verdict | One-paragraph verdict + 4 relevance-tier cards (counts) + 3 priority adversary headlines |
| 3 | Methodology Stack | The §2 layered diagram — frameworks, red-team bridge, anchor bodies, scoring rubric |
| 4 | Geopolitical Exposure Map | Jurisdiction × entity × exposure table (§3.3) + sanctions/posture context |
| 5 | Threat Landscape At A Glance | The actor index: band, actor, cryptonyms, sponsor, relevance tier, headline campaign |
| 6 | Anchor Case — Kazuar / Secret Blizzard | The nation-state exemplar: how a modular P2P espionage botnet operates, why it matters |
| **7** | **NATION-STATE.** divider | Section divider (red) |
| 8–11 | Nation-state actor cards | One actor per slide (§6 card layout) |
| **12** | **STATE-ALIGNED.** divider | Section divider (orange) |
| 13–15 | State-aligned theft actor cards | Lazarus/APT38, BlueNoroff/TraderTraitor, … |
| **16** | **eCRIME.** divider | Section divider (amber) |
| 17–22 | eCrime actor cards | Scattered Spider, Evil Corp, FIN7, TA505, RaaS, banking-trojan ecosystem |
| **23** | **HACKTIVIST.** divider | Section divider (gray) |
| 24 | Hacktivist actors (combined) | NoName057(16) + Killnet on one slide |
| 25 | Kill-Chain Scenario | A single end-to-end "attack on this customer" walk-through (Recon→Actions) for the top actor |
| 26 | Attack-Surface Linkage | How GEOPOL ties to the Shodan findings: which exposed hosts each top actor would use |
| 27 | Business-Impact Linkage (C-BIQ) | FAIR bridge: top scenarios → probable euro loss, halt-of-operations cost |
| 28 | Mitigation & Colt Fit Matrix | Actor/TTP × control × Colt portfolio coverage |
| 29 | Caveats, Confidence & Disambiguation | Admiralty grades, what this is/isn't, the §2 disambiguation flags |
| 30 | Next Steps / Intelligence-Led Roadmap | Feed TIBER-EU/DORA TLPT; owners; 30/60/90 |

If a band has only one or two relevant actors, repurpose the freed slots for deeper cards or a second kill-chain scenario — do not add a band.

---

## 6. Actor-Card Layout (the workhorse slide)

Each profiled actor renders into a two-column card — a Diamond Model in disguise.

- **Left column** — ADVERSARY & CAPABILITY: WHO THEY ARE (sponsor, cryptonyms, motivation) + TTP block (ATT&CK IDs) + EVIDENCE block (named campaign + Admiralty grade).
- **Right column** — WHY THIS CUSTOMER & WHAT STOPS THEM: relevance rationale (the exposure-fit) + REFERENCES (CISA/MITRE/vendor) + 3 remediation rows tagged VENDOR / COLT / PSF / OSS.

Reuse the Shodan-deck `findingCard` geometry verbatim (vertical budget, 9×50 evidence block, exactly 3 remediation rows, severity badge → here a **relevance-tier** badge). Card content rules:

- **Title pattern**: `<Actor> — "<Cryptonym>" · <one-line capability>` (≤ 95 chars, 2-line max).
- **Eyebrow**: `<BAND> · <SPONSOR> · <RELEVANCE TIER>`, all-caps, charSpacing 3.
- **Pills (≤3, upper-right)**: MITRE G-ID, primary cryptonym, ATT&CK technique of note (e.g. `T1484.002`).
- **TTP block**: ≤ 4 lines, ATT&CK IDs inline. Lead with the access vector.
- **EVIDENCE block** (dark mono, ≤ 9 lines × 50 chars): the named real campaign + figures + **Admiralty grade** + source tag. Example:
  ```
  CAMPAIGN:   Bybit crypto heist           2025-02
  ACTOR:      BlueNoroff / TraderTraitor   DPRK RGB
  IMPACT:     ~USD 1.5bn  (Safe{Wallet} supply chain)
  ATT&CK:     T1566 spearphish · T1195 supply chain
  ATTRIB:     FBI alert + Mandiant          Grade A1
  ```
- **WHY THIS CUSTOMER**: 2–3 sentences of *exposure-fit*, not generic threat. "Safra NB of NY sits on the same NY-Fed correspondent rail Lazarus exploited at Bangladesh Bank" — not "DPRK targets banks."
- **3 remediation rows**: each tied to a concrete Colt/PSF/vendor/OSS control. Map TTPs to controls (§7).

---

## 7. Mitigation Mapping — Actor TTP → Control → Colt Fit

Every actor card's remediation, and the slide-28 matrix, draws from this mapping. Consistent across customers.

| Adversary TTP / theme | Control objective | Primary Colt fit | Secondary |
|---|---|---|---|
| Help-desk social engineering / MFA fatigue (Scattered Spider) | Phishing-resistant MFA, help-desk identity verification, IdP-federation monitoring | SASE / SSE with ZTNA; managed identity monitoring | PSF — IdP hardening; OSS — FIDO2 |
| Rogue federated IdP persistence (T1484.002) | Detect new federation trusts / token issuers | Managed detection on identity plane | OSS — Entra/Okta config audit |
| SWIFT / correspondent-rail abuse (Lazarus/APT38) | Transaction-integrity monitoring, segregation of payment plane | PSF — payment-network segmentation; SASE ZTNA admin-only | OSS — SWIFT CSP self-attestation |
| Supply-chain / edge-appliance zero-day (Cl0p, APT29) | Third-party/edge exposure reduction, virtual patching | Managed WAF (virtual patching); SSE | OSS — SBOM / dependency scanning |
| Destructive wiper spillover (Sandworm) | Segmentation, immutable backup, blast-radius control | PSF — network segmentation; DDoS/IP Guardian | OSS — immutable/offline backups |
| DDoS availability (NoName057(16)/Killnet) | Volumetric + application DDoS mitigation | IP Guardian Premium Plus; Managed WAF | — |
| Banking-trojan / account-takeover (Dridex, Qakbot) | Web/email security, customer-fraud controls | Managed Web & Email Security | OSS — DMARC/BIMI |
| Cloud-identity abuse / OAuth (APT29) | Conditional access, OAuth app governance | SSE / CASB uniform policy | Cloud security posture |
| Espionage long-dwell (Turla/Kazuar) | EDR in block mode, ASR rules, egress (EWS/WSS) anomaly detection | Managed Detection & Response | OSS — Sigma rules for IPC/named-pipe |

> **OFAC overlay:** for any ransomware actor with a sanctions nexus (Evil Corp/LockBit-cover), the remediation must flag the **payment-as-sanctions-violation** risk for the US entity. This is a compliance control, not just a technical one.

---

## 8. Integrating the Three Layers

GEOPOL is most powerful as the connective tissue. The build pulls from the sibling products:

- **From the Shodan layer**: the exposed hosts/CVEs/KEV entries become the *Capability×Infrastructure* an actor would use. Slide 26 names them. (e.g. an exposed Fortinet edge → the access vector for a Cl0p-style or Scattered-Spider intrusion.)
- **From C-BIQ**: the euro impact of a successful operation. Slide 27 uses FAIR to turn the top GEOPOL scenario into a probable-loss range and a *halt-of-operations* day-cost. This is the "could halt its operation" payoff the customer asked for.
- **GEOPOL adds**: the *Adversary×Intent* the other two lack — the named who and why, sourced and graded.

The one-line pitch: **Shodan says what's open. C-BIQ says what it costs. GEOPOL says who's coming and why.**

---

## 9. Build, QA & Hand-off

Identical toolchain to the Shodan deck. Reuse `build_deck.js` geometry; swap finding-cards for actor-cards.

```bash
mkdir -p /home/claude/<customer>_geopol && cd /home/claude/<customer>_geopol
export NODE_PATH=/home/claude/.npm-global/lib/node_modules
node build_geopol_deck.js
python3 /mnt/skills/public/pptx/scripts/office/soffice.py \
  --headless --convert-to pdf <Customer>_GEOPOL_Assessment_Internal.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 100 <Customer>_GEOPOL_Assessment_Internal.pdf slide
python3 /mnt/skills/public/pptx/scripts/thumbnail.py <Customer>_GEOPOL_Assessment_Internal.pptx
```

QA checklist additions specific to GEOPOL:

1. **Every actor card has a real, sourced campaign** in the evidence block — no placeholder.
2. **Every attribution carries an Admiralty grade.**
3. **Every "WHY THIS CUSTOMER" is exposure-specific**, not generic ("targets banks" is a fail).
4. **Cryptonym mapping is consistent** (don't mix Microsoft and CrowdStrike names mid-deck without the cross-walk).
5. The four standard divider, evidence-overflow, title-wrap, and pill-collision checks from the Shodan QA loop.

First render + one targeted fix pass = budget.

File naming: `<Customer>_GEOPOL_Assessment_Internal.pptx`. Hand off via `present_files`.

---

## 10. Caveats & Evidence Discipline (read before any external use)

1. **GEOPOL is strategic intelligence, not a prediction.** It states *who could and would*, with sourced rationale and graded confidence — never *who will*.
2. **Attribution is contested.** DPRK and Russian cluster boundaries differ across vendors (MITRE vs Microsoft vs CrowdStrike). State which taxonomy the deck follows and cross-walk cryptonyms.
3. **Every figure is sourced or labelled indicative.** Theft totals, victim counts, and loss figures cite a named advisory or are flagged as ranges.
4. **Disambiguation flags** (carry to the caveats slide): DFSA = Finanstilsynet (not Dubai); Herzliya = ICT at Reichman (verify "IICC" separately); "FEER" unconfirmed as a framework — do not cite.
5. **The OFAC/sanctions overlay is legal, not just technical** — flag, but it is not legal advice; the customer's counsel owns the payment decision.
6. **Naming consultancy firms** (McKinsey/Bain/BCG/Mandiant) is framing, not a citable methodology claim — phrase aspirationally.
7. **Refresh cadence**: threat landscape shifts fast. A GEOPOL report has a ~6-month shelf life; date it and re-grade before re-use.

---

## 11. Sources (anchor set)

**Anchor case:** Microsoft Threat Intelligence, "Kazuar: Anatomy of a nation-state botnet," 14 May 2026; CISA AA23-129A "Hunting Russian Intelligence Snake Malware"; UK FSB factsheet.
**Frameworks:** MITRE ATT&CK (attack.mitre.org); Diamond Model (Caltagirone et al., 2013); Lockheed Martin Cyber Kill Chain; Heuer, *Psychology of Intelligence Analysis* (ACH); NATO AJP-2.1 Admiralty grading; FIRST.org (CVSS, EPSS); CISA KEV; Bianco, Pyramid of Pain; Open Group / FAIR Institute (FAIR).
**Red-team / regulation:** ECB TIBER-EU; EU DORA (Reg. 2022/2554) + TLPT RTS; Bank of England CBEST; HKMA iCAST; ABS/MAS AASE; Australia CORIE.
**Bodies:** CISA; US Treasury OFAC/FinCEN; FS-ISAC; NCSC-UK; ENISA; BSI/BaFin BAIT; FINMA Circ. 2023/1; Swiss BACS (ex-NCSC-CH/MELANI/GovCERT.ch); Danish CFCS; CSA Singapore/MAS; Israel INCD / ICT Reichman; BACEN Res. 4.893.
**Actor reporting:** MITRE Groups G0007/G0008/G0010/G0016/G0032/G0034/G0046/G0082/G0092/G1015; CISA AA20-239A, AA23-108, AA23-158A, AA23-165A, AA23-320A, AA23-353A, AA24-057A; FBI Bybit alert (2025); US Treasury sm845 (Evil Corp); Mandiant/Google, Microsoft, CrowdStrike, Unit 42, Proofpoint, NCSC-CH reporting.
**Colt internal:** `COLT_DESIGN_SYSTEM.md`, `COLT_SHODAN_DECK_METHODOLOGY.md`, `06-business-impact-quantification.md`, `Safra_Saxo_PostMA_Methodology_DeepDive.md`.

---

*Colt / S4Biz Sales Engineering · GEOPOL Assessment methodology · v1.0 · 15 June 2026*
*Companion to `COLT_SHODAN_DECK_METHODOLOGY.md`, `COLT_DESIGN_SYSTEM.md`, `06-business-impact-quantification.md`*
*Worked reference build: `Safra_GEOPOL_Assessment_Internal.pptx`*
