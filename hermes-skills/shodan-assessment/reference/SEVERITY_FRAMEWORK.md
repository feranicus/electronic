# 01 — Methodology & Data Scope

**[← Back to README](README.md)**

---

## Data sources

| Field | Value |
|-------|-------|
| Dataset 1 | `f0548u_be.json` — 34 records |
| Dataset 2 | `fgafsje1p.json` — 37 records |
| Dataset 3 | `f95duo60o.json` — 28 records |
| Dataset 4 | `f9wnr7qcr.json` — 99 records |
| Total records | 198 (combined, with duplicates) |
| Unique IPs | 85 |
| Unique hostnames | 145 across 35+ domains |
| Primary ASN | AS15532 (179 records) |
| 3rd-party ASNs | Microsoft · CONVOTIS · Flow Swiss · Exoscale · hosttech · 5 more |
| Geography | 100% Switzerland (CH) |
| Service mix | HTTPS 135 · HTTP 45 · SMTP 13 · SNMP 2 · OpenVPN 1 |
| Crawl timestamps | 06–07 May 2026 |

All findings derived from a Shodan host export. **No active probing of Raiffeisen's
perimeter was performed.** No traffic originated from Colt.

---

## Classification framework

| Severity | Criteria |
|----------|----------|
| **CRITICAL** | CISA KEV-listed CVE  OR  exploitable cryptographic break  OR  unmanaged off-ASN brand asset |
| **HIGH**     | CVSS ≥ 7.5 with EPSS > 0.5  —  or  unpatched edge-device family  —  or  non-prod publicly reachable |
| **MEDIUM**   | Information-disclosure, weak-crypto, banner exposure, or supplier-sprawl visibility gap |
| **LOW**      | Reconnaissance-friendly metadata, generic banners, hygiene findings |

---

## Reference frameworks used

| Framework | Relevance |
|-----------|-----------|
| **FINMA Circ. 2018/3** | Outsourcing — central to RFP 343557 (cited in cover letter) |
| **FINMA Circ. 2023/1** | Operational risks and resilience — banks (since 01/2024) |
| **nFADP / nDSG** | Swiss Federal Data Protection Act (revised, in force Sep 2023) |
| **NCSC.ch** | Swiss National Cyber Security Centre — Minimum-Standard ICT |
| **EU DORA** | Digital Operational Resilience Act — referenced for sub-contractor stack |
| **ISO/IEC 27001:2022** | Information security management — operator baseline |
| **NIST CSF 2.0 / SP 800-207** | Cyber Security Framework + Zero Trust Architecture |
| **CISA KEV** | Known Exploited Vulnerabilities catalog |

**NOT used**: BSI IT-Grundschutz / BAIT — German framework, not applicable to a Swiss bank.

---

## PSF preference order (pursuit-team direction)

1. **Versa** — first preference. SD-WAN Router, SASE, SSE, SD LAN all Existing in PSF.
2. **Fortinet** — second preference. Switch, SD-WAN, Firewall Existing. FortiADC,
   FortiWeb, FortiMail noted as ESC-route gaps.
3. **Open-source frameworks** — for tooling, detection, attribution, monitoring.

Cisco, Aruba, Juniper, Palo Alto are all PSF-existing but not preferred for this RFP.

---

**[← Back to README](README.md)** · **[Next → Asset Inventory](02-asset-inventory.md)**
