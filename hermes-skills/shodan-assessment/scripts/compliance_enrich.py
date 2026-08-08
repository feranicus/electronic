#!/usr/bin/env python3
"""
compliance_enrich.py — produce compliance.json for a company across NIS2, CRA and the EU AI Act.

Mirrors the security engine: the LLM returns a STRUCTURED JSON blob (never prose the builders paste
blind), grounded ONLY in the committed reference (compliance/EU_COMPLIANCE_REFERENCE.md). Rendering is
deterministic (pptxgenjs + a Node HTML builder), so a weak model can produce weaker wording but never
a broken or unsafe deliverable.

Input is a COMPANY NAME only (the operator's choice). The model INFERS the scoping assumptions
(sector, size band, whether the company sells products with digital elements, whether it builds/uses
AI, countries) from its own knowledge and STATES them as assumptions — the post-run clarification loop
(compliance_clarify.py) is how the operator confirms/corrects them, exactly like the security Assess.

    python compliance_enrich.py "Acme AG" out/compliance.json [--lang en|de] [--overrides overrides.json]

The model chain, key and pricing are reused from enrich.py (same DigitalOcean inference). A
deterministic fallback ALWAYS yields a usable compliance.json: the obligations, deadlines and penalty
maxima are FIXED facts from the reference (company-independent), so even with no model the decks carry
the real regulatory content — applicability is simply marked "requires confirmation".
"""
import argparse, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# =============================================================================================
# JURISDICTION REGISTRY — ONE map, the way build_findings_deck.js already selects its framework
# set from d.target.country. Adding a country must never mean a second code path: it means a new
# entry here plus its reference document. `_ORDER` used to be a flat ["nis2","cra","aiact"], which
# is why Canada fell through to the generic ISO 27001 default.
#
#   regimes : every regime GRADED for this jurisdiction, in presentation order
#   decks   : the subset that gets its own deck. The rest appear in the roadmap at-a-glance table.
#             A bank does not want eight single-guideline decks; it wants the four that carry a
#             distinct deadline or audience, and one page that shows the whole picture.
# =============================================================================================
JURISDICTIONS = {
    "EU": {
        "label": "EU",
        "title": "EU Compliance",
        "eyebrow": "EU DIGITAL & CYBER COMPLIANCE",
        "reference": "EU_COMPLIANCE_REFERENCE.md",
        "compiled": "20 Jul 2026",
        "regimes": ["nis2", "cra", "aiact"],
        "decks": ["nis2", "cra", "aiact"],
        "framing": "three EU regimes: NIS2, the Cyber Resilience Act (CRA) and the EU AI Act",
    },
    "CA": {
        "label": "Canada",
        "title": "Canadian Compliance",
        "eyebrow": "CANADIAN DIGITAL & CYBER COMPLIANCE",
        "reference": "CA_COMPLIANCE_REFERENCE.md",
        "compiled": "1 Aug 2026",
        "regimes": ["osfi_b13", "osfi_e21", "osfi_b10", "osfi_integrity", "osfi_incident",
                    "pipeda", "law25", "ccspa"],
        "decks": ["osfi_b13", "osfi_e21", "osfi_b10", "pipeda"],
        "framing": ("the Canadian regime set: OSFI Guidelines B-13, E-21, B-10 and Integrity & "
                    "Security, the OSFI Technology and Cyber Security Incident Reporting Advisory, "
                    "PIPEDA, Quebec Law 25 and the CCSPA"),
    },
}
DEFAULT_JURISDICTION = "EU"


def jurisdiction(code):
    """Resolve a country/jurisdiction code to a registry entry. Fails CLOSED to the EU set.

    Accepts a jurisdiction key ("CA") or any country code we map onto one. An unknown code must
    never produce an empty regime list — a deck with no regimes is worse than the wrong regimes,
    because it looks finished.
    """
    c = str(code or "").strip().upper()
    if c in JURISDICTIONS:
        return c, JURISDICTIONS[c]
    return DEFAULT_JURISDICTION, JURISDICTIONS[DEFAULT_JURISDICTION]


def regimes_for(juris):
    return list(JURISDICTIONS[jurisdiction(juris)[0]]["regimes"])


def decks_for(juris):
    return list(JURISDICTIONS[jurisdiction(juris)[0]]["decks"])


def _ref_text(juris=DEFAULT_JURISDICTION):
    _, j = jurisdiction(juris)
    try:
        return open(os.path.join(HERE, "compliance", j["reference"]),
                    encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


# ---------------------------------------------------------------- FIXED regulatory facts ---
# These come verbatim from the reference and DO NOT depend on the company. They anchor the
# deterministic fallback and are also handed to the model as the ground truth it must not contradict.
FIXED = {
    "nis2": {
        "name": "NIS2 — Directive (EU) 2022/2555",
        "instrument": "Directive (via national law)",
        "regulates": "Cybersecurity of organisations (18 sectors)",
        "obligations": [
            {"ref": "Art. 20", "title": "Governance & management liability",
             "detail": "Management bodies must approve the risk-management measures, oversee implementation, follow training, and can be held personally liable."},
            {"ref": "Art. 21(2)", "title": "Risk-management measures (10 minimum)",
             "detail": "Risk-analysis & IS-security policies; incident handling; business continuity/backup/DR/crisis; supply-chain security; secure acquisition/development incl. vulnerability handling; effectiveness assessment; cyber hygiene & training; cryptography/encryption; HR security, access control, asset management; MFA & secured comms."},
            {"ref": "Art. 21(3)", "title": "Supply-chain security",
             "detail": "Take account of vulnerabilities and cybersecurity practices of each direct supplier, including secure development."},
            {"ref": "Art. 23", "title": "Incident reporting — 24h / 72h / 1 month",
             "detail": "Early warning within 24h, incident notification within 72h, final report within one month, for any incident with a significant impact."},
            {"ref": "Art. 3(3)-(4)", "title": "Registration / notification",
             "detail": "Register with the national authority (name, contacts, IP ranges, sector, Member States); notify changes within two weeks."},
        ],
        "deadlines": [
            {"date": "2026-03-06", "label": "German NIS2 registration statutory deadline (BSI grace to 31 Jul 2026)"},
            {"date": "2026-08-15", "label": "Netherlands NIS2 law in force"},
            {"date": "2026-09-30", "label": "Sweden NIS2 registration deadline"},
            {"date": "2026-10-01", "label": "Austria NIS2 law in force"},
            {"date": "2026-10-03", "label": "Poland NIS2 registration deadline"},
            {"date": "2026-12-31", "label": "Austria NIS2 registration deadline"},
        ],
        "penalty": {"essential": "€10m or 2% of worldwide turnover",
                    "important": "€7m or 1.4% of worldwide turnover",
                    "note": "Essential entities also face temporary management bans and suspension of authorisation (Art. 32(5)); late registration is a separate offence (DE up to €500k)."},
    },
    "cra": {
        "name": "Cyber Resilience Act — Regulation (EU) 2024/2847",
        "instrument": "Regulation (directly applicable)",
        "regulates": "Cybersecurity of products with digital elements (PDE)",
        "obligations": [
            {"ref": "Annex I Part I", "title": "Security by design",
             "detail": "No known exploitable vulnerabilities; secure-by-default; access protection; confidentiality/integrity/availability; data minimisation; attack-surface reduction; security logging; fixable via security updates."},
            {"ref": "Annex I Part II", "title": "Vulnerability handling + SBOM",
             "detail": "Identify & document components (SBOM); remediate without delay via free updates; regular testing; coordinated vulnerability disclosure; public disclosure of fixed vulnerabilities; secure update distribution."},
            {"ref": "Art. 13", "title": "Support period & CE marking",
             "detail": "Security updates for the expected product life, at least 5 years; technical documentation, EU declaration of conformity and CE marking before market placement."},
            {"ref": "Art. 14", "title": "Reporting — 24h / 72h / 14 days",
             "detail": "Report actively exploited vulnerabilities & severe incidents to CSIRT + ENISA via the single platform: early warning 24h, notification 72h, final report 14 days."},
        ],
        "deadlines": [
            {"date": "2026-09-11", "label": "CRA incident & vulnerability reporting begins (Art. 14)"},
            {"date": "2027-12-11", "label": "CRA full product requirements apply (Annex I, conformity, CE)"},
        ],
        "penalty": {"essential": "€15m or 2.5% of worldwide turnover",
                    "important": "€10m or 2% (other obligations); €5m or 1% (misleading info)",
                    "note": "Market surveillance can order products withdrawn or recalled. MDR-regulated medical devices are carved out (Art. 2(2)(a))."},
    },
    "aiact": {
        "name": "EU AI Act — Regulation (EU) 2024/1689",
        "instrument": "Regulation (directly applicable)",
        "regulates": "AI systems by risk tier",
        "obligations": [
            {"ref": "Art. 5", "title": "Prohibited practices (live since 2 Feb 2025)",
             "detail": "No manipulative/deceptive AI, social scoring, untargeted face-scraping, workplace/education emotion inference, sensitive biometric categorisation, or (narrow exceptions) real-time remote biometric ID."},
            {"ref": "Art. 8-17", "title": "High-risk provider duties",
             "detail": "Risk-management system; data governance & bias examination; technical documentation; automatic logging; transparency to deployers; human oversight; accuracy/robustness/cybersecurity; quality-management system; EU-database registration; conformity assessment + CE marking."},
            {"ref": "Art. 26-27", "title": "Deployer duties",
             "detail": "Use per instructions; ensure human oversight; monitor and suspend/report risks; keep logs; inform affected persons; fundamental-rights impact assessment where required."},
            {"ref": "Art. 50", "title": "Transparency (limited-risk)",
             "detail": "Tell people they are interacting with AI; label AI-generated/manipulated content and deepfakes; disclose emotion-recognition/biometric-categorisation use."},
            {"ref": "Art. 53-55", "title": "General-purpose AI (GPAI)",
             "detail": "Technical documentation; downstream information; copyright policy; public training-data summary; systemic-risk models add evaluation/red-teaming, risk mitigation, incident reporting and cybersecurity."},
        ],
        "deadlines": [
            {"date": "2025-02-02", "label": "Prohibited practices + AI-literacy duties apply"},
            {"date": "2025-08-02", "label": "GPAI obligations, governance & penalties apply"},
            {"date": "2026-08-02", "label": "General application: high-risk (Annex III) + transparency"},
            {"date": "2027-08-02", "label": "Embedded high-risk (Annex I) + pre-2025 GPAI"},
        ],
        "penalty": {"essential": "€35m or 7% of worldwide turnover (Art. 5 breaches)",
                    "important": "€15m or 3% (operator/high-risk/transparency duties); €7.5m or 1% (misleading info)",
                    "note": "GPAI model fines up to €15m or 3% (Art. 101); SMEs pay the LOWER of the fixed amount or the percentage."},
    },
    # =========================================================================================
    # CANADA — every article, date and figure below is quoted from
    # compliance/CA_COMPLIANCE_REFERENCE.md (compiled 1 Aug 2026), which cites the primary text.
    #
    # `penalty.essential` / `.important` are LOOKUP KEYS the deck builder reads — they are NOT
    # renamed (the standing rule about enums). `label1`/`label2` override what is RENDERED, because
    # "Essential-tier maximum" is NIS2 vocabulary and would be nonsense over an OSFI guideline.
    #
    # The reference's §6.4 "must never appear" list is binding here and is enforced by
    # scripts/test_compliance_ca.py: no OSFI fine, no live CCSPA obligation or 72h clock, no $1M
    # individual CCSPA AMP, no PIPEDA fine for the breach itself, no assertion that Law 25 binds a
    # federally chartered bank.
    # =========================================================================================
    "osfi_b13": {
        "name": "OSFI Guideline B-13 — Technology and Cyber Risk Management",
        "instrument": "OSFI guideline (supervisory expectation)",
        "regulates": "Technology and cyber risk at federally regulated financial institutions",
        "obligations": [
            {"ref": "P14 §3.1.3", "title": "Vulnerabilities identified, assessed and ranked",
             "detail": "Regular vulnerability assessments of network devices, systems and applications; rank by severity and exposure; consider the cumulative impact of vulnerabilities, irrespective of individual risk level, that could present a high-risk exposure when combined."},
            {"ref": "P15 §3.2.4", "title": "Minimise the attack surface",
             "detail": "Protect networks, including external-facing services, from threats by minimizing its attack surface, and define authorized logical network zones."},
            {"ref": "P15 §3.2.3", "title": "Enhanced controls for external-facing assets",
             "detail": "Critical and EXTERNAL-FACING technology assets carry enhanced control requirements — the clause an external attack-surface assessment maps onto most directly."},
            {"ref": "P15 §3.2.6", "title": "Security vulnerabilities are remediated",
             "detail": "Timely, risk-based patching in accordance with established timelines; compensating controls where remediation is unavailable; regularly monitor and report patching status and remediation against those timelines, including backlog and exceptions."},
            {"ref": "P15 §3.2.7", "title": "Identity and access management",
             "detail": "Multi-factor authentication across external-facing channels and privileged accounts; privileged credentials held in a secure vault."},
            {"ref": "P15 §3.2.2", "title": "Cryptography kept effective",
             "detail": "Strong cryptographic technologies, with the cryptography standard reassessed regularly to remain effective against current and emerging threats."},
        ],
        "deadlines": [
            {"date": "2024-01-01", "label": "B-13 effective for all FRFIs, including foreign bank branches"},
        ],
        "penalty": {"essential": "No monetary penalty",
                    "important": "Supervisory intervention",
                    "label1": "Fine", "label2": "Enforcement tool",
                    "note": "OSFI's tools are supervisory, not monetary: increased oversight, watch-list placement, or a stage in OSFI's supervisory intervention approach. There is no fine attached to B-13."},
    },
    "osfi_e21": {
        "name": "OSFI Guideline E-21 — Operational Risk Management and Resilience",
        "instrument": "OSFI guideline (supervisory expectation)",
        "regulates": "Operational risk and resilience at federally regulated financial institutions",
        "obligations": [
            {"ref": "§3.1 P6", "title": "Map critical operations end to end",
             "detail": "Mapping must consider people, technology, processes, information, facilities, THIRD PARTIES, and the connections or dependencies among them."},
            {"ref": "§3.2 P7", "title": "Set tolerances for disruption",
             "detail": "The maximum disruption withstandable under severe but plausible scenarios, explicitly considering the systems, facilities and third-party suppliers on which critical operations depend."},
            {"ref": "§3.3 P8", "title": "Scenario testing",
             "detail": "Named examples include large-scale technology failures, critical third-party service disruptions and cyber incidents."},
            {"ref": "§4.5", "title": "Technology and cyber",
             "detail": "E-21 states no technology controls of its own and refers to Guideline B-13 — a control mapping must chain E-21 §4.5 to B-13."},
            {"ref": "§4.7", "title": "Data risk",
             "detail": "A dedicated data-risk framework covering integrity, confidentiality and availability across the data lifecycle."},
        ],
        "deadlines": [
            {"date": "2025-09-01", "label": "Milestone 2 — §4: BCM, DR, crisis, change, technology/cyber, third-party, data risk"},
            {"date": "2026-09-01", "label": "FULL ADHERENCE — critical operations identified, mapped, tolerances set, scenario-testing methodology developed and testing begun"},
            {"date": "2027-09-01", "label": "Scenario testing completed for all critical operations"},
        ],
        "penalty": {"essential": "No monetary penalty",
                    "important": "Supervisory intervention",
                    "label1": "Fine", "label2": "Enforcement tool",
                    "note": "Effective dates are NOT in the guideline itself — they appear only in the accompanying OSFI Letter of 22 Aug 2024. 1 September 2026 is the live full-adherence milestone and is the single most actionable date for a Canadian FRFI."},
    },
    "osfi_b10": {
        "name": "OSFI Guideline B-10 — Third-Party Risk Management",
        "instrument": "OSFI guideline (supervisory expectation)",
        "regulates": "Third-party and subcontractor risk at federally regulated financial institutions",
        "obligations": [
            {"ref": "§4 Outcome 6", "title": "Third-party technology and cyber operations are secure",
             "detail": "§4.2 requires third parties carrying elevated technology or cyber risk to comply with FRFI or recognized industry standards, notably in access management and data security and protection."},
            {"ref": "Principle 5", "title": "Subcontractors / fourth parties",
             "detail": "The FRFI is responsible for identifying, monitoring and managing risk arising from subcontracting arrangements undertaken by its third parties; contractual levers include the right to refuse a subcontractor and to audit it."},
            {"ref": "§4.3-4.4", "title": "Cloud and concentration risk",
             "detail": "Data protection, key management, container management and portability, plus strategies such as multi-cloud design to mitigate cloud service provider concentration risk."},
            {"ref": "§2.4.2.2", "title": "Contracts must carry the incident clock",
             "detail": "Contracts must enable the FRFI to meet the Incident Reporting Advisory, including prompt notification of incidents at the third party OR the subcontractor."},
            {"ref": "§2.4 P10", "title": "Monitoring at aggregate level",
             "detail": "Monitor at arrangement level and at aggregate business-unit, platform and enterprise level."},
        ],
        "deadlines": [
            {"date": "2024-05-01", "label": "B-10 effective for FRFIs"},
            {"date": "2025-03-31", "label": "B-10 effective for foreign bank and foreign insurance branches"},
        ],
        "penalty": {"essential": "No monetary penalty",
                    "important": "Supervisory intervention",
                    "label1": "Fine", "label2": "Enforcement tool",
                    "note": "Two effective dates must be modelled separately — getting the branch date wrong for a foreign-branch client is a visible error. Hosts on a third party's infrastructure that carry the customer's brand are B-10 evidence; attributing a co-tenant's host to the customer is a FALSE B-10 finding."},
    },
    "osfi_integrity": {
        "name": "OSFI Integrity and Security Guideline",
        "instrument": "OSFI guideline (statutory basis in the OSFI Act)",
        "regulates": "Integrity and security, including protection against foreign interference",
        "obligations": [
            {"ref": "§2", "title": "Policies and procedures MUST be established",
             "detail": "Adequate policies and procedures to protect against threats to integrity or security, including foreign interference, must be established, implemented, maintained and adhered to — OSFI uses 'must', unusually for guidance."},
            {"ref": "P7 §4.3", "title": "Technology assets — weaknesses identified and addressed",
             "detail": "Technology assets should be secure, with weaknesses identified and addressed, effective defences in place, and issues identified accurately and promptly. Defers to B-13 for the controls."},
            {"ref": "P9 §4.5", "title": "Third-party risks",
             "detail": "Accountability for security cannot be contracted out. For foreign-interference purposes the institution must consider the third party's and its subcontractors' location of operations, location of headquarters, connections to foreign governments and ownership structure."},
            {"ref": "§4.3", "title": "Annual threat-environment reporting",
             "detail": "The threat environment should be assessed and internally reported at least annually — the cleanest recurring-assessment hook in the Canadian set."},
        ],
        "deadlines": [
            {"date": "2024-01-31", "label": "Published; four phased dates, all now past — fully in force"},
        ],
        "penalty": {"essential": "No monetary penalty",
                    "important": "Supervisory intervention",
                    "label1": "Fine", "label2": "Enforcement tool",
                    "note": "Statutory basis in the OSFI Act. Enforcement is supervisory; there is no fine."},
    },
    "osfi_incident": {
        "name": "OSFI Technology and Cyber Security Incident Reporting Advisory",
        "instrument": "OSFI advisory (supervisory expectation)",
        "regulates": "Incident reporting by federally regulated financial institutions",
        "obligations": [
            {"ref": "Advisory", "title": "Report within 24 hours, or sooner if possible",
             "detail": "Report in writing to OSFI's Technology Risk Division and to the Lead Supervisor on the Incident Reporting and Resolution Form."},
            {"ref": "Advisory", "title": "Report even when details are incomplete",
             "detail": "Where details are unavailable, state 'information not yet available', give best estimates, and provide regular (e.g. daily) updates until the report is complete."},
        ],
        # NO dated entry: this is a STANDING obligation with a 24-hour clock that starts at the
        # incident, not a date in a calendar. Publishing today's date in a "nearest deadline"
        # column would invent a deadline — absence of a date is the honest render (an em-dash).
        "deadlines": [],
        "penalty": {"essential": "No monetary penalty",
                    "important": "Supervisory intervention",
                    "label1": "Fine", "label2": "Consequence of not reporting",
                    "note": "24 hours is tighter than PIPEDA's 'as soon as feasible' and tighter than the CCSPA's future 72-hour ceiling. Not reporting leads to increased supervisory oversight, watch-list placement or a stage in OSFI's supervisory intervention approach."},
    },
    "pipeda": {
        "name": "PIPEDA — Personal Information Protection and Electronic Documents Act",
        "instrument": "Federal statute (R.S.C. 1985, c. P-8.6)",
        "regulates": "Personal information handled in the course of commercial activity",
        "obligations": [
            {"ref": "Sch. 1, cl. 4.7", "title": "Security safeguards",
             "detail": "Personal information shall be protected by security safeguards appropriate to the sensitivity of the information. Clause 4.7.1 protects against loss or theft and unauthorized access, disclosure, copying, use or modification, regardless of format. Only the 'shall' clauses (4.7, 4.7.1) are enforceable obligations."},
            {"ref": "s. 10.1(1)", "title": "Report a breach of security safeguards",
             "detail": "Report to the Privacy Commissioner where it is reasonable in the circumstances to believe the breach creates a REAL RISK OF SIGNIFICANT HARM to an individual."},
            {"ref": "ss. 10.1(2), 10.1(6)", "title": "Timing — as soon as feasible",
             "detail": "As soon as feasible after the organization determines that the breach has occurred. There is no fixed hour count in PIPEDA."},
            {"ref": "s. 10.3 + SOR/2018-64 s. 6(1)", "title": "Keep a record of EVERY breach",
             "detail": "Including breaches below the real-risk threshold, retained for 24 months after the organization determines the breach occurred."},
            {"ref": "cl. 4.1.3", "title": "Third-party processing",
             "detail": "Accountability follows information transferred to a third party for processing — contractual or other means must provide a comparable level of protection."},
        ],
        "deadlines": [
            {"date": "2018-11-01", "label": "Mandatory breach reporting and record-keeping in force"},
        ],
        "penalty": {"essential": "$100,000 (indictable)",
                    "important": "$10,000 (summary conviction)",
                    "label1": "Maximum fine — indictable", "label2": "Maximum fine — summary",
                    "note": "s. 28 applies only where an organization KNOWINGLY contravenes s. 10.1, s. 10.3(1), s. 8(8) or s. 27.1(1), or obstructs the Commissioner. There is NO penalty for the breach itself, nor for failing clause 4.7 — those are enforced through Commissioner findings, compliance agreements and Federal Court applications. s. 16(c) allows the Federal Court to award damages, an unbounded exposure that dwarfs the $100,000 cap. PIPEDA has no administrative monetary penalty regime."},
    },
    "law25": {
        "name": "Quebec Law 25 — Act respecting the protection of personal information in the private sector",
        "instrument": "Quebec statute (CQLR c. P-39.1)",
        "regulates": "Personal information held by enterprises carrying on an enterprise in Quebec",
        "obligations": [
            {"ref": "s. 3.5", "title": "Notify the CAI and affected persons",
             "detail": "Where a confidentiality incident presents a risk of serious injury, notify the Commission d'acces a l'information and each affected person PROMPTLY. The CAI may order notification if the enterprise fails to."},
            {"ref": "s. 3.8", "title": "Register of confidentiality incidents",
             "detail": "Keep a register capturing ALL incidents, including those with no risk of serious injury, retained at least 5 years — contrast PIPEDA's 24 months."},
            {"ref": "s. 10", "title": "Necessary security measures",
             "detail": "The obligation to take necessary security measures is NOT new to Law 25 — it has been in force since 14 June 2006. Law 25 made it ENFORCEABLE, via s. 90.1(4) and s. 91(4)."},
            {"ref": "s. 3.2 / 3.3", "title": "Governance policies and privacy impact assessments",
             "detail": "Published governance policies and PIAs for information-system projects, in force since 22 September 2023."},
        ],
        "deadlines": [
            {"date": "2022-09-22", "label": "Person in charge, incident notification (s. 3.5), incident register (s. 3.8)"},
            {"date": "2023-09-22", "label": "Governance, PIAs, privacy by default, service providers — and the entire penalty regime"},
            {"date": "2024-09-22", "label": "Data portability (s. 27 para. 3)"},
        ],
        "penalty": {"essential": "Greater of $25,000,000 or 4% of worldwide turnover (penal, s. 91)",
                    "important": "Greater of $10,000,000 or 2% of worldwide turnover (administrative, s. 90.12)",
                    "label1": "Maximum penal fine", "label2": "Maximum administrative penalty",
                    "note": "APPLICABILITY TO A FEDERALLY CHARTERED BANK IS AN OPEN CONSTITUTIONAL QUESTION and must be answered by counsel — do not assume P-39.1 binds an FRFI. Under the CAI's Cadre general a notice of non-compliance must precede any administrative penalty. s. 93.1 punitive damages are mandatory with a $1,000 floor per person where the infringement is intentional or results from gross fault."},
    },
    "ccspa": {
        "name": "CCSPA — Critical Cyber Systems Protection Act",
        "instrument": "Federal statute, S.C. 2026 c. 9 (consolidated as C-47.4) — PART 2 NOT IN FORCE",
        "regulates": "Designated operators of vital services and systems — none designated to date",
        "obligations": [
            {"ref": "STATUS", "title": "Part 2 is not in force — nothing is owed today",
             "detail": "Royal Assent 15 June 2026. Part 2 comes into force on a day to be fixed by order of the Governor in Council; no order and no regulations had appeared in the Canada Gazette as at 1 August 2026. Schedule 2, which defines 'designated operator', contains its column headers and ZERO rows — so there are no designated operators in enacted Canadian law today."},
            {"ref": "Sch. 1 item 5", "title": "Banking systems ARE a listed vital service",
             "detail": "Schedule 1 lists banking systems and clearing and settlement systems, so a bank is in the intended perimeter once a class is added to Schedule 2. That OSFI will be named the regulator for banking is a structural inference, NOT enacted law."},
            {"ref": "s. 9(1) / s. 10", "title": "Planning only — 90-day cyber security programme",
             "detail": "Once a class is added to Schedule 2, a designated operator has 90 days to establish a cyber security programme with five elements including supply-chain and third-party risk, and to provide it to the regulator."},
            {"ref": "s. 17 / s. 15", "title": "Planning only — reporting and supply-chain",
             "detail": "Incident reports to the Communications Security Establishment within a period to be prescribed by regulations, not to exceed 72 hours; supply-chain risk mitigation 'as soon as' a risk is identified, with no grace period."},
            {"ref": "s. 135(2)-(3)", "title": "The deemed-compliance hook",
             "detail": "Regulations must, to the extent possible, ensure consistency with existing regulatory and standards regimes, and the Governor in Council MAY DEEM compliance with such a regime to be compliance with the Act. A bank already meeting OSFI B-13 and E-21 has a direct argument."},
        ],
        "deadlines": [
            {"date": "2026-06-15", "label": "Royal Assent — Parts 1 and 3 in force; PART 2 NOT IN FORCE"},
        ],
        "penalty": {"essential": "$15,000,000 (ceiling on future regulations)",
                    "important": "$500,000 for an individual (ceiling on future regulations)",
                    "label1": "Corporate AMP ceiling", "label2": "Individual AMP ceiling",
                    "note": "THESE ARE CEILINGS ON FUTURE REGULATIONS, NOT A LIVE TARIFF — Part 2 is not in force and no penalty can be imposed today. The individual ceiling was reduced at committee on 26 February 2026; figures quoted from earlier drafts of the Bill are wrong. s. 94 makes a continuing violation a separate violation each day, and s. 93 makes directors and officers parties whether or not the operator has been proceeded against."},
    },
}

_ORDER = ["nis2", "cra", "aiact"]   # legacy alias; use regimes_for(jurisdiction)


def _skeleton(company, lang, assumptions=None, juris=DEFAULT_JURISDICTION):
    """Deterministic compliance.json from the FIXED facts. Always correct; the safety net."""
    a = assumptions or {}
    jcode, J = jurisdiction(juris)
    regimes = {}
    for k in J["regimes"]:
        f = FIXED[k]
        regimes[k] = {
            "key": k, "name": f["name"], "instrument": f["instrument"], "regulates": f["regulates"],
            "applies": "unclear",
            "classification": "Requires confirmation",
            "rationale": ("Scope depends on the company's sector, size and product/AI profile — "
                          "confirm via the clarification questions to finalise the classification."),
            "obligations": list(f["obligations"]),
            "gaps": [],
            "deadlines": list(f["deadlines"]),
            "penalty": f["penalty"],
            "colt": _remediation_defaults(k),
        }
    return {
        "company": company, "generated": datetime.date.today().isoformat(), "lang": lang,
        # The deck builders read these instead of hard-coding ["nis2","cra","aiact"], so a new
        # jurisdiction needs no JS change at all.
        "jurisdiction": jcode,
        "jurisdiction_label": J["label"],
        "jurisdiction_title": J["title"],
        "eyebrow": J.get("eyebrow", ""),
        "order": list(J["regimes"]),
        "decks": list(J["decks"]),
        "assumptions": {
            "sector": a.get("sector") or "Not yet confirmed",
            "size_band": a.get("size_band") or "unknown",
            "sells_digital_products": a.get("sells_digital_products"),
            "builds_or_deploys_ai": a.get("builds_or_deploys_ai"),
            "countries": a.get("countries") or [],
            "note": "Company-independent obligations, deadlines and penalties are shown verbatim from "
                    "the primary legal texts. Applicability requires confirmation of sector/size/profile.",
        },
        "regimes": regimes,
        "roadmap": {
            "exec_summary": ("This assessment maps %s against %s. Confirm the scoping assumptions to "
                             "finalise which duties bite and by when." % (company, J["framing"])),
            "phases": list(ROADMAP_PHASES[jcode]),
            "priorities": [],
        },
        "source": "compliance/%s (compiled %s)" % (J["reference"], J["compiled"]),
        "disclaimer": "Not legal advice. Obligations, dates and penalty maxima are quoted from the "
                      "primary texts as at the reference compilation date; national and provincial "
                      "rules move, so re-check before relying on this.",
    }


# Per-jurisdiction fallback plan. A single EU-shaped plan told a Canadian bank to "register with
# the national NIS2 authority", which is the kind of line that ends a meeting.
ROADMAP_PHASES = {
    "EU": [
        {"when": "0-3 months", "items": ["Confirm scope & entity classification per regime",
                                         "Register with the relevant national NIS2 authority",
                                         "Stand up 24h/72h incident-reporting runbooks"]},
        {"when": "3-9 months", "items": ["Close Art. 21 risk-management gaps (MFA, backup/DR, supply-chain)",
                                         "Build the product SBOM & vulnerability-handling process (CRA)",
                                         "Inventory AI systems and classify by AI-Act risk tier"]},
        {"when": "9-18 months", "items": ["Complete CRA conformity + CE for products with digital elements",
                                          "Meet AI-Act high-risk duties for any Annex III system",
                                          "Independent effectiveness review & board sign-off"]},
    ],
    "CA": [
        {"when": "Before 1 Sep 2026", "items": [
            "E-21 full adherence: critical operations identified and mapped, tolerances set",
            "Scenario-testing methodology developed and testing begun",
            "Confirm the 24-hour OSFI incident-reporting runbook and the Lead Supervisor contact"]},
        {"when": "0-6 months", "items": [
            "B-13 §3.2.4: reduce the external attack surface and evidence the reduction",
            "B-13 §3.2.6: patch against defined timelines and report backlog and exceptions",
            "B-13 §3.2.7: MFA across every external-facing channel and privileged account",
            "B-10: map third parties and subcontractors carrying elevated technology risk"]},
        {"when": "6-18 months", "items": [
            "Integrity & Security: annual threat-environment assessment reported internally",
            "E-21 scenario testing completed for all critical operations by 1 Sep 2027",
            "Track the CCSPA coming-into-force order and Schedule 2 — a banking class starts a 90-day clock",
            "Confirm with counsel whether Quebec Law 25 applies to the federally chartered entity"]},
    ],
}


def _remediation_defaults(k):
    """Vendor-NEUTRAL managed-service suggestions.

    The audience is resellers delivering with their own stack, so naming a specific carrier's
    products is an own-goal. The JSON key stays `colt` because build_compliance_deck.js reads it —
    renaming a lookup key makes rows silently vanish; the rendered label is what got rebranded.
    This path is the DETERMINISTIC fallback, which is exactly the path the brand gate never
    rendered, which is how "Colt SASE / ZTNA" survived the rebrand.
    """
    CA_MAP = {
        "osfi_b13": [
            {"title": "External attack-surface monitoring", "body": "Continuous discovery and ranking of internet-facing assets — the evidence B-13 §3.1.3 and §3.2.4 ask for, including the cumulative-impact view."},
            {"title": "Managed vulnerability remediation", "body": "Risk-based patching against defined timelines with backlog and exception reporting, per §3.2.6."},
            {"title": "MFA and privileged access management", "body": "Multi-factor authentication across external-facing channels and privileged accounts, with credentials vaulted, per §3.2.7."}],
        "osfi_e21": [
            {"title": "Critical-operations mapping", "body": "End-to-end mapping including third parties and dependencies, the §3.1 P6 deliverable due for 1 Sep 2026."},
            {"title": "Scenario testing programme", "body": "Severe-but-plausible cyber and third-party disruption scenarios, with tolerances evidenced, per §3.2 and §3.3."}],
        "osfi_b10": [
            {"title": "Third-party exposure assessment", "body": "Assess a supplier's external estate the same way, with no access and no questionnaire — direct evidence for Outcome 6 and Principle 5."},
            {"title": "Concentration-risk view", "body": "Supplier, geography and subcontractor concentration across the estate, per §2.4 P10."}],
        "osfi_integrity": [
            {"title": "Annual threat-environment report", "body": "A recurring, dated assessment of the external threat environment for internal reporting, per §4.3."}],
        "osfi_incident": [
            {"title": "24-hour incident runbook", "body": "Pre-agreed reporting path to the Technology Risk Division and Lead Supervisor, with partial-information templates."}],
        "pipeda": [
            {"title": "Breach-record keeping", "body": "A register of every breach including sub-threshold ones, retained 24 months per s. 10.3 and SOR/2018-64."},
            {"title": "Safeguards evidence", "body": "Demonstrable technical safeguards proportionate to sensitivity, for clause 4.7."}],
        "law25": [
            {"title": "Incident register (5 years)", "body": "A register capturing all confidentiality incidents, retained at least five years per s. 3.8."}],
        "ccspa": [
            {"title": "Horizon tracking", "body": "Monitor the coming-into-force order and Schedule 2; a banking class starts a 90-day programme clock. Nothing is owed today."}],
    }
    if k in CA_MAP:
        return list(CA_MAP[k])
    if k == "nis2":
        return [{"title": "Managed Detection & Response + SOC", "body": "Delivers Art. 21(2) incident handling and the 24h/72h reporting evidence trail."},
                {"title": "SASE / ZTNA + Managed Firewall", "body": "Access control, MFA and secure connectivity for Art. 21(2)(i)/(j)."},
                {"title": "Backup, DR & network resilience", "body": "Business-continuity controls (Art. 21(2)(c)) with dual-homing and tested recovery."}]
    if k == "cra":
        return [{"title": "Secure-by-design advisory + SBOM tooling", "body": "Vulnerability-handling process and SBOM to meet Annex I Part II."},
                {"title": "Managed vulnerability disclosure & update delivery", "body": "Coordinated disclosure and secure update distribution across the 5-year support window."}]
    return [{"title": "AI governance & risk-management framework", "body": "Art. 9 risk-management system, logging and human-oversight design for high-risk AI."},
            {"title": "Model security & red-teaming", "body": "Art. 15 accuracy/robustness/cybersecurity and adversarial testing for AI systems."}]


PROMPT = """You are a senior cyber & compliance pre-sales analyst. Using ONLY the reference below,
assess %(company)s against %(framing)s.

Return ONLY strict JSON, no prose, no markdown. British English%(lang)s.

STEP 1 — INFER the company profile from your own knowledge of %(company)s and STATE it as assumptions
(you have no company questionnaire; the operator will confirm/correct these afterwards):
sector, size_band (micro|small|medium|large), whether it SELLS products with digital elements
(hardware/software/apps/IoT), whether it BUILDS or DEPLOYS AI, and its main countries of operation.
If confirmed facts are provided under CONFIRMED, they OVERRIDE your inference and you must not contradict them.

STEP 2 — For EACH regime decide applicability from those assumptions and the reference's scope rules,
then produce the analysis. NEVER invent an article number, deadline, penalty figure or fine that is not
in the reference. The obligations/deadlines/penalty maxima are FIXED — reproduce them faithfully; your
job is the company-specific applicability, rationale, GAPS and remediation.

VOICE: the reader is a reseller delivering with their OWN stack. Describe remediation as a capability
("managed detection and response"), never as a named vendor product, and never in the first person.

Return this EXACT shape — one entry per regime key listed, and NO OTHER KEYS:
{
 "assumptions": {"sector":"", "size_band":"", "sells_digital_products":true, "builds_or_deploys_ai":false,
                 "countries":["%(country)s"], "note":"Inferred from public information; confirm to finalise scope."},
 "regimes": {
%(shape)s
 },
 "roadmap": {"exec_summary":"3-4 sentences for a board: combined exposure, the nearest hard deadline, the biggest gap",
             "priorities":[{"regime":"","action":"","why":"deadline/penalty","colt":"the managed capability"}]}
}
Give 3-5 gaps and 2-3 remediation items per APPLICABLE regime; [] for an out-of-scope regime. Every gap
sentence must carry an attacker action or a business/deadline consequence AND the clause reference — no filler.

%(rules)s

CONFIRMED (operator-asserted facts; override your inference):
%(confirmed)s

=== REFERENCE (the ONLY permitted source of articles, deadlines and penalties) ===
%(reference)s
"""

# Per-regime classification vocabularies. The model must choose FROM these, so a Canadian deck can
# never come back classified "Essential|Important" (NIS2 vocabulary over an OSFI guideline).
CLASSIFICATIONS = {
    "nis2": "Essential|Important|Out of scope|Unclear",
    "cra": "Default self-assessment|Important (Class I/II)|Critical|Out of scope|Unclear",
    "aiact": "Prohibited|High-risk|Limited-risk (transparency)|Minimal|GPAI|Out of scope|Unclear",
    "osfi_b13": "Applies (FRFI)|Applies (foreign branch)|Out of scope|Unclear",
    "osfi_e21": "Applies (FRFI)|Applies (foreign branch)|Out of scope|Unclear",
    "osfi_b10": "Applies (FRFI)|Applies (foreign branch from 31 Mar 2025)|Out of scope|Unclear",
    "osfi_integrity": "Applies (FRFI)|Out of scope|Unclear",
    "osfi_incident": "Applies (FRFI)|Out of scope|Unclear",
    "pipeda": "Applies|Applies (substantially similar provincial law may displace)|Out of scope|Unclear",
    "law25": "Open constitutional question for an FRFI|Applies (Quebec enterprise)|Out of scope|Unclear",
    "ccspa": "Not in force — horizon only",
}

# Jurisdiction-specific hard rules handed to the model. For Canada these are the reference's own
# "what must never appear in a Canadian deck" list (§6.4), restated as instructions.
PROMPT_RULES = {
    "EU": "",
    "CA": """HARD RULES FOR CANADA — breaking any of these makes the deck wrong:
- The CCSPA imposes NOTHING today. Part 2 is not in force and Schedule 2 is empty. Never state a live
  CCSPA obligation or a live 72-hour clock, and never quote a $1,000,000 individual AMP.
- OSFI does NOT fine. Its tools are supervisory. Never state an OSFI penalty amount.
- PIPEDA's $100,000 attaches only to KNOWINGLY contravening s. 10.1 / s. 10.3(1) / s. 8(8) / s. 27.1(1)
  or obstructing the Commissioner — never to the breach itself and never to clause 4.7.
- Do NOT assert that Quebec Law 25 binds a federally chartered bank; it is an open constitutional
  question for counsel.
- ITSG-33 is not mandatory and has no citable control count. CCCS Baseline Controls are for small and
  medium organisations, not a large bank.
- The nearest hard deadline for a Canadian FRFI is E-21 full adherence on 1 September 2026.""",
}


def _shape_for(order):
    """Build the JSON shape block from the regime registry, so adding a regime needs no prompt edit."""
    out = []
    for k in order:
        out.append('   "%s": {"applies": true, "classification":"%s",\n'
                   '            "rationale":"2-3 sentences tying the company profile to the scope test",\n'
                   '            "gaps":[{"sev":"HIGH|MEDIUM|LOW","title":"","detail":"attacker/impact + the clause","article":""}],\n'
                   '            "colt":[{"title":"managed capability","body":"what it delivers, mapped to the clause"}]}'
                   % (k, CLASSIFICATIONS.get(k, "Applies|Out of scope|Unclear")))
    return ",\n".join(out)


LANG_DE = (" — schreibe ALLE Fliesstexte (rationale, gaps, colt, exec_summary, assumptions.note, "
           "priorities) auf formellem Hochdeutsch (Sie-Form). JSON-Schluessel und Artikel-/"
           "Verordnungsnummern bleiben englisch/original. Uebersetze NICHT: NIS2, CRA, AI Act, OSFI, "
           "PIPEDA, CCSPA, Gesetzes-/Richtliniennamen, CVE-/Artikel-IDs, Eigennamen.")

LANG_RU = (" — пиши ВЕСЬ связный текст (rationale, gaps, colt, exec_summary, assumptions.note, "
           "penalty.note) ИСКЛЮЧИТЕЛЬНО на русском языке, деловым регистром для CISO/CFO. "
           "Названия правовых актов НЕ переводятся: NIS2, Cyber Resilience Act (CRA), EU AI Act, "
           "DORA. Ключи JSON остаются английскими — на русском только значения. "
           "Даты, суммы штрафов и ссылки на статьи не изменяются.")

# ONE registry, same doctrine as enrich.py: a per-file `if de` is how a language gets missed.
LANG_BLOCKS = {"de": LANG_DE, "ru": LANG_RU}


def lang_block(lang):
    return LANG_BLOCKS.get(str(lang or "en").strip().lower()[:2], "")


def _merge(base, model):
    """Overlay the model's per-regime analysis onto the deterministic skeleton, keeping FIXED facts."""
    a = model.get("assumptions")
    if isinstance(a, dict):
        for k, v in a.items():
            if v not in (None, "", []):
                base["assumptions"][k] = v
    mr = model.get("regimes") or {}
    for k in base.get("order") or list(base["regimes"].keys()):
        m = mr.get(k)
        if not isinstance(m, dict):
            continue
        r = base["regimes"][k]
        if m.get("applies") is not None:
            r["applies"] = m["applies"]
        for fld in ("classification", "rationale"):
            if str(m.get(fld) or "").strip():
                r[fld] = m[fld]
        if isinstance(m.get("gaps"), list) and m["gaps"]:
            r["gaps"] = [g for g in m["gaps"] if isinstance(g, dict)][:6]
        if isinstance(m.get("colt"), list) and m["colt"]:
            r["colt"] = [c for c in m["colt"] if isinstance(c, dict)][:4]
    rm = model.get("roadmap") or {}
    if str(rm.get("exec_summary") or "").strip():
        base["roadmap"]["exec_summary"] = rm["exec_summary"]
    if isinstance(rm.get("priorities"), list) and rm["priorities"]:
        base["roadmap"]["priorities"] = [p for p in rm["priorities"] if isinstance(p, dict)][:8]
    return base


def build(company, lang="en", overrides=None, juris=DEFAULT_JURISDICTION):
    """Return compliance.json. Tries the DO model chain; falls back to the deterministic skeleton."""
    overrides = overrides or {}
    jcode, J = jurisdiction(juris)
    base = _skeleton(company, lang, overrides.get("assumptions"), jcode)
    if not os.environ.get("OPENAI_API_KEY"):
        base["assumptions"]["note"] += "  (LLM not configured — deterministic scope shown.)"
        return base, "no OPENAI_API_KEY — deterministic"
    try:
        sys.path.insert(0, HERE)
        import enrich as E
        prompt = PROMPT % {
            "company": company,
            "lang": lang_block(lang),
            "framing": J["framing"],
            "country": "CA" if jcode == "CA" else "DE",
            "shape": _shape_for(J["regimes"]),
            "rules": PROMPT_RULES.get(jcode, ""),
            "confirmed": json.dumps(overrides, ensure_ascii=False) if overrides else "(none supplied)",
            "reference": _ref_text(jcode)[:16000],
        }
        chain = E._chain() or ["gemma-4-31B-it"]
        last = ""
        for model in chain[:3]:
            try:
                txt, usage = E._call(prompt, model=model,
                                     timeout=int(os.environ.get("COMPLIANCE_TIMEOUT", "150")))
                j = E._json(txt)
                if isinstance(j, dict) and (j.get("regimes") or j.get("assumptions")):
                    out = _merge(base, j)
                    out["model"] = model
                    print("[compliance] enriched via %s (%s tok)"
                          % (model, (usage or {}).get("completion_tokens", "?")), file=sys.stderr)
                    return out, "ok:%s" % model
                last = "empty/'%s'" % (str(j)[:80])
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, str(e)[:120])
                print("[compliance] model %s failed (%s) — trying next" % (model, last), file=sys.stderr)
        base["assumptions"]["note"] += "  (LLM chain failed: %s — deterministic scope shown.)" % last
        return base, "fallback:%s" % last
    except Exception as e:
        print("[compliance] enrich unavailable (%s) — deterministic" % type(e).__name__, file=sys.stderr)
        return base, "deterministic"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("company")
    ap.add_argument("out")
    ap.add_argument("--lang", default=os.environ.get("DECK_LANG", "en"))
    ap.add_argument("--overrides", help="JSON file of operator-confirmed facts")
    a = ap.parse_args()
    ov = {}
    if a.overrides and os.path.exists(a.overrides):
        try: ov = json.load(open(a.overrides, encoding="utf-8"))
        except Exception: pass
    out, status = build(a.company, a.lang, ov)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("compliance_enrich: %s -> %s" % (status, a.out), file=sys.stderr)


if __name__ == "__main__":
    main()
