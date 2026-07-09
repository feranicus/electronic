# 06 — Business-Impact Quantification (C-BIQ)

**[← Back to README](README.md)**

**Internal — Colt Confidential — NOT for external distribution · RFP 343557**

> Chapter [`03-findings`](03-findings.md) says *how bad each finding is technically*
> (Critical/High/Medium/Low). This chapter says *what it costs in Swiss francs if we don't
> fix it, and how much risk each Colt remediation buys back.* It is the layer that turns a
> findings deck into a board conversation — the same move Jungheinrich's CISO made when he
> stopped selling "better protection" and started selling "Return on Security Investment in
> CHF." **The board reads francs. C-BIQ writes francs.**

---

## How to read this chapter (KISS)

Four things, in order:

1. **Why Colt is the right firm to do this** — §1. (We find it, price it, fix it, and watch it. Most can do one.)
2. **Exactly how we measure** — §2–§3, with one finding (C2, the NetScaler) **worked end-to-end with real numbers** so you can follow the maths and reproduce it.
3. **The standards we stand on** — §4. We use the same frameworks the Big Four bill for (NIST, FAIR, PwC, Deloitte, EY). The difference is we attach a Colt product to every answer.
4. **Every finding priced + fixed** — §6, then the board one-pager §7.

> ⚠️ **Every CHF number here is model output, not a measured fact.** It is produced by the
> method in §2 from public benchmarks plus stated assumptions. We always give a **range**,
> never a single number, and we **show our working**. Final calibration needs customer data
> Shodan cannot see (revenue-per-hour per service, incident history, insurance tower). Same
> status as the "illustrative" Squalify/Deloitte graphics in the source article. Consistent
> with [`05-caveats`](05-caveats-and-next-steps.md): **visible ≠ vulnerable; modelled ≠ actual.**

---

## 1. Why Colt — and why we beat the alternatives

The customer has three ways to get cyber-risk numbers. Only one of them also fixes the risk.

| | Scanner / ASM vendor | Big-Four advisory (Deloitte/KPMG/EY/PwC) | **Colt (C-BIQ)** |
|---|---|---|---|
| **Finds the exposure** | ✅ automated scan | ⚠️ questionnaire / interview-led | ✅ **active Shodan recon — real external evidence, not a survey** ([`01`](01-methodology.md)) |
| **Prices it in CHF** | ❌ severity only | ✅ (their core product, billed at day-rates) | ✅ **same standards (FAIR/NIST/PwC/Deloitte), built into the assessment** |
| **Fixes it** | ❌ hands you a PDF | ❌ hands you a slide deck + a follow-on SOW | ✅ **we own the network & SASE plane — Versa/Fortinet PSF + Colt managed services** |
| **Watches it after** | ⚠️ re-scan licence | ❌ | ✅ **continuous re-scan + managed SOC + monitored single plane** |
| **One accountable throat** | ❌ | ❌ | ✅ **assess → price → remediate → monitor, one contract** |

**The one-line pitch:** *a scanner tells you the door is open; a consultant tells you what an
open door costs; **Colt closes the door, prices the risk while doing it, and keeps watching
it** — on infrastructure we already run for you.* For RFP 343557 that is decisive, because the
single biggest exposure in this report (the **10 fragmented off-ASN suppliers**, finding H5) is
not a patch — it is an **architecture** problem, and architecture is what the SD-WAN/SASE
tender is buying.

### 1.1 Why our numbers are credible, stated plainly

We did not invent a scoring system. We assembled the published standards and bolted them to
real external evidence:

- **The maths** is FAIR — the only open international CRQ standard.
- **The plumbing** (how a finding becomes an enterprise risk number) is **NIST IR 8286D**, the
  US government standard for using Business-Impact Analysis to prioritise risk.
- **The delivery method** is PwC's four-step CRQ model (top-down questions first, data second).
- **The cost taxonomy** is Deloitte's "above/below the surface."
- **The evidence** is our own Shodan assessment — the part the Big Four don't have.

PwC's own data shows why this matters: **only ~15 % of organisations measure cyber risk to any
significant extent, and 44 % blame data quality.** We solve the data problem by starting from
hard external evidence, not a questionnaire.

---

## 2. How we measure — the engine, worked end-to-end

This is a seven-step pipeline. We run it per finding. Below, **every step is shown on finding
C2** (the public Citrix NetScaler AAA portal) so the maths is visible, not asserted.

```
 Step 1  Asset criticality   →  how much the bank's mission leans on this asset  (NIST 8286D BIA)
 Step 2  Loss scenario       →  the specific bad thing that happens             (FAIR)
 Step 3  Frequency  (LEF)     →  how often it lands per year                     (FAIR: TEF × Vuln)
 Step 4  Magnitude  (LM)      →  what one event costs, in 7 cash buckets         (FAIR + Deloitte)
 Step 5  Simulate             →  10,000 runs → ALE, PML, loss curve              (Monte Carlo)
 Step 6  Register & compare   →  write to risk register, test vs risk appetite   (NIST 8286D)
 Step 7  Treat & re-measure   →  apply Colt fix, recompute, report ROSI          (Gartner ROSI)
```

### Step 1 — Asset criticality (NIST 8286D BIA register)

We score how badly the bank's mission depends on the asset, on Confidentiality / Integrity /
Availability, 1–5. This is the BIA register that NIST 8286D makes the *nexus* of risk.

> **C2 worked:** `app-portal.raiffeisen.ch` is the **authentication front door to the
> application stack.** If it falls, attackers are *inside* the app plane.
> **C = 5, I = 4, A = 5 → baseline criticality "Critical".** test-portal shares the product
> family, so one CVE class hits prod *and* non-prod at once.

### Step 2 — Loss scenario (FAIR)

One sentence, no jargon. The better the scenario, the better the number.

> **C2 worked:** *"An unauthenticated attacker exploits a Citrix-Bleed-class flaw on the public
> AAA portal, steals a valid session token, pivots into the app stack, and deploys
> ransomware / exfiltrates data."* This is **not hypothetical** — it is exactly what happened
> to ICBC (see §5.2), discovered the same way we found C2: on Shodan.

### Step 3 — Frequency: LEF = TEF × Vulnerability

```
TEF  (Threat Event Frequency)  = how many credible attempts per year
Vuln (Vulnerability)           = chance any one attempt succeeds
LEF  (Loss Event Frequency)    = TEF × Vuln   → events per year (the ARO)
```

We don't guess these — we anchor them:

| Input | C2 value | Where it comes from |
|-------|----------|---------------------|
| **TEF** | **12 / yr** | Public AAA portal in a KEV-active family is scanned in waves; ~monthly credible attempts. CISA KEV + high EPSS. |
| **Vuln** | **0.05** (5 %) | Patch level unknown from Shodan, **no ZTNA in front**. Mostly-patched but residual session/MFA-bypass risk. FINMA: successful attacks on CH banks **+~50 % in 2024** → we do not round down. |
| **LEF** | **12 × 0.05 = 0.6 / yr** | ≈ **once every ~1.7 years.** Band: **Likely.** |

Frequency bands (house calibration, stated openly so a reviewer can challenge them — the
opposite of a black-box "3 out of 5"):

| Band | ARO (events/yr) | Plain English |
|------|-----------------|---------------|
| Routine | 1.0–4.0 | Several times a year |
| **Likely** | 0.3–1.0 | About once a year ± |
| Plausible | 0.1–0.3 | Once every 3–10 yrs |
| Tail | 0.02–0.1 | Once every 10–50 yrs |

### Step 4 — Magnitude: LM = Primary + Secondary loss, in 7 cash buckets

Primary loss = what *we* pay directly. Secondary loss = what we pay *because of others*
(regulator, customers, market). The seven buckets are Deloitte's above/below-surface model,
specialised for a Swiss retail-cooperative bank. **For a bank, the below-surface buckets
(L3–L7) dwarf the IR invoice (L1).**

| | Bucket | Surface | C2 three-point estimate (Min / Likely / Max) |
|--|--------|---------|----------------------------------------------|
| **L1** | Incident response & forensics | Above | 0.4 / 0.8 / 2.0 M — DFIR, rebuild, **full session+credential rotation post-patch** (Bleed tokens survive patching) |
| **L2** | Regulatory & legal | Above | 0.1 / 0.5 / 3.0 M — FINMA reportable + supervisory action; outside counsel |
| **L3** | Operational downtime | Below | 0.3 / 1.5 / 8.0 M — e-banking + RAInet (1,200 sites / 212 banks) degraded during containment |
| **L4** | Customer & revenue | Below | 0.2 / 1.0 / 12 M — deposit flight, churn, lost net-new-money on a public outage |
| **L5** | Reputational / brand | Below | 0.1 / 0.5 / 9 M — **acute for a cooperative whose whole brand is member trust** |
| **L6** | Third-party / contractual | Below | 0.0 / 0.1 / 2.0 M — fronting BigIP (H2) shares the blast radius |
| **L7** | Capital & funding | Below | 0.0 / 0.1 / 24 M — Moody's **A2** pressure / cost-to-raise-funding on a systemic event |
| | **Total LM** | | **Min ≈ 1.2 M · Likely ≈ 4.5 M · Max ≈ 60 M** |

### Step 5 — Simulate (Monte Carlo)

We sample LEF and the LM buckets 10,000 times (PERT/triangular distributions) and read three
numbers off the result. **We never report one number.**

```
ALE  (Annualised Loss Expectancy) = mean annual loss          → the BUDGET number
PML  (Probable Maximum Loss)      = ~95th-percentile single event → the CAPITAL / INSURANCE number
Loss-exceedance curve             = P(loss ≥ X)               → the BOARD picture
```

> **C2 worked (transparent arithmetic):**
> - "Typical breach" loss (excluding the rare catastrophe) PERT-mean ≈ (1.2 + 4×4.5 + 18) / 6 ≈ **CHF 6.2 M**.
> - **ALE = LEF × mean LM = 0.6 × 6.2 ≈ CHF 3.7 M / year.** (Range across assumptions: **CHF 2.0–4.5 M/yr**.)
> - **PML** (the catastrophic tail — core-banking ransomware halting services for days) ≈ **CHF 25–90 M** single event.
> - **Cost of Delay = ALE ÷ 12 ≈ CHF 165–375 k per month** the finding stays open — and it
>   **rises** the longer the box is visible on Shodan (KEV exploitation ramps). That per-month
>   figure is the single most persuasive line in a board pack: "next quarter" = "we choose to
>   carry ~CHF 0.5 M of risk for that delay."

### Step 6 — Register & compare to risk appetite (NIST 8286D)

The result goes into a **risk register** row and is tested against the bank's stated **risk
appetite**. NIST 8286D's whole point: a Level-3 *system* risk (one NetScaler) rolls up to a
Level-2 *organisation* risk and then to the **Level-1 enterprise** view the board owns. C2's
PML lands in the "tens of millions" band — Deloitte's CIONET research shows boards already
intuitively place a major cyber event at **CHF 10–100 M+**, so this is the language they expect.

### Step 7 — Treat & re-measure → ROSI (the part only Colt closes)

We apply the Colt remediation (§6), recompute ALE, and report what the spend bought:

```
ROSI = (ALE_before − ALE_after − annual cost of control) ÷ annual cost of control
```

> **C2 worked:** Replacing the public AAA portal with **Versa SASE + ZTNA** removes the asset
> from Shodan entirely (TEF → near-0) and puts **Fortinet FortiGate L7 IPS** in front during
> patch windows. LEF collapses from 0.6 to ~0.05. **ALE_after ≈ CHF 0.3 M.** Risk bought back
> ≈ **CHF 3.4 M/yr** against a managed-service cost a fraction of that → **ROSI strongly
> positive.** This is the number a scanner and a consultant *cannot* produce, because neither
> of them operates the replacement.

---

## 3. The seven cash buckets (reference)

Used in every worksheet in §6. Primary = we pay it; Secondary = others make us pay it.

| Bucket | What it contains for a Swiss retail-cooperative bank |
|--------|------------------------------------------------------|
| **L1 — Response** | DFIR retainer, threat-hunt, rebuild, overtime, session/credential rotation, crisis vendors |
| **L2 — Regulatory & legal** | FINMA notification + supervisory action; FDPIC/**nFADP** exposure; **DORA** exposure *via EU-based ICT providers*; outside counsel; litigation |
| **L3 — Operational downtime** | Lost throughput across RAInet (1,200 sites / 212 banks), e-banking, payment rails; settlement-fail penalties; branch downtime |
| **L4 — Customer & revenue** | Deposit flight, account churn, lost net-new-money, fee/interest income forgone, client remediation credits |
| **L5 — Reputational / brand** | Trade-name devaluation — *the cooperative's core asset is member trust*; long-tail acquisition cost |
| **L6 — Third-party / contractual** | Liability flowing in from the 10 off-ASN suppliers; SLA penalties; supplier-substitution cost; indemnity disputes |
| **L7 — Capital & funding** | Moody's **A2** rating pressure, higher cost to raise funding, FINMA operational-risk capital add-on |

### 3.1 Benchmark inputs — public, dated, auditable

Every three-point estimate is anchored on these. **All public; the customer can check them.**

| Benchmark | Value | Source / date |
|-----------|-------|---------------|
| Avg. breach cost, **financial services** | **≈ USD 5.56 M** (≈ CHF 4.9 M) | IBM/Ponemon *Cost of a Data Breach 2025* |
| Cost **per compromised record** | **USD 128–234** | IBM/Ponemon 2025 |
| **Supply-chain** compromise cost / time-to-resolve | **USD 4.91 M / 267 days** (longest) | IBM/Ponemon 2025 |
| Successful attacks on **Swiss FIs**, 2024 | **+ ~50 % YoY** | FINMA |
| FINMA on third parties | Over-reliance = "key operational risk" | FINMA |
| **nFADP / nDSG** sanction | up to **CHF 250,000** on *responsible individuals* — **not** %-of-turnover | Revised Swiss FADP (Sep 2023) |
| **DORA** ceiling | up to **2 % of worldwide turnover**; ICT critical-third-party up to **EUR 5 M** | EU 2022/2554 (enforced 17 Jan 2025) — applies **via EU ICT providers**, not the Swiss entity directly |
| **Raiffeisen Group** total assets | **CHF ≈ 305.6 bn** (FY2024) | Raiffeisen Group Annual Report 2024 |
| Raiffeisen Group customer deposits | **CHF ≈ 215 bn** | Annual Report 2024 |
| Raiffeisen Group profit | **CHF ≈ 1.2 bn** (FY2024) | Annual Report 2024 |
| Raiffeisen Group rating | **Moody's A2** | Moody's |
| Board's own worst-case framing | major cyber event = **CHF 10–100 M+** | Deloitte CIONET *Unlocking Business Value of Cyber Security* |
| Orgs measuring cyber risk "significantly" | only **~15 %** (44 % blame data quality) | PwC *Global Digital Trust Insights 2025* |

---

## 4. The standards we stand on (and exactly what we take from each)

Not name-dropping — each row is a concrete part of the engine in §2.

| Standard / firm | What it is | What C-BIQ uses, concretely |
|-----------------|-----------|------------------------------|
| **FAIR** (Open Group / FAIR Institute) | Open CRQ standard: Risk = LEF × LM, Monte-Carlo'd | **Steps 3–5.** The actual maths and the ALE/PML outputs. |
| **NIST IR 8286D** | US standard: use BIA to prioritise risk; BIA register → risk register → enterprise rollup; risk appetite/tolerance | **Steps 1 & 6.** Asset criticality and how one box's risk becomes the board's number. |
| **PwC — 4-step CRQ** | (1) define board questions, (2) fix the data + taxonomy, (3) blend qualitative+quantitative, (4) translate to action | **The delivery method (§5).** Top-down questions first; data discipline; plain-language output. |
| **Deloitte — Beneath the Surface** | 14 cost factors, 7 visible + 7 hidden; "business impact scenarios" | **Step 4.** The seven cash buckets, especially the hidden L3–L7. |
| **EY — Cyber-resilience wheel** | GRC core, ringed by Asset Valuation/BIA (RTO/RPO/MBCO), CIA classification, technical assessment (VA/PT/CR), threat feeds | **The shape of the engagement.** Anchors recovery objectives and ties C-BIQ to resilience, not just loss. |
| **Gartner — ODM / PLA / ROSI** | Outcome-driven metrics; spend-vs-protection at board level | **Step 7 & §7.** The loss-exceedance curve and ROSI framing. |
| **KPMG / EY / PwC actuarial** | Translate to P&L / capital / insurance; PML, VaR | **PML** as the capital/insurance number, reported separately from ALE. |
| **IBM/Ponemon · IDC · Omdia** | Sector breach-cost and downtime benchmarks | **§3.1** frequency and magnitude anchors. |

---

## 5. How we run the engagement (the delivery approach)

Same phased shape as a serious reference build — define, gather, model, present — done in
**under 8 weeks for a bank this size** (the Jungheinrich/Deloitte engagement hit that timeline;
we match it because the Shodan evidence base is already in hand).

| Phase | What happens | Output | Who |
|-------|--------------|--------|-----|
| **1 — Frame** (PwC step 1) | Agree the board questions (what loss, what appetite, what ROI) and the scenarios that matter | Scenario list + risk-appetite statement | Pursuit team + customer CRO/CISO |
| **2 — Gather** (PwC step 2 · NIST BIA) | Asset criticality + 3-point loss inputs via short interviews; anchor to §3.1 benchmarks | BIA register | SE Lead + customer SMEs |
| **3 — Model** (FAIR steps 3–5) | Build + Monte-Carlo each scenario; validate ranges | ALE/PML + loss curves | SE + Cyber Product Lead |
| **4 — Present** (PwC step 4 · Gartner) | Board one-pager (§7); ROSI per remediation; integrate into ERM | Board pack + risk-register rows | Pursuit Lead |
| **(ongoing) — Watch** | Weekly Shodan/Censys re-scan; recompute as the estate changes | Trend line | Colt managed service |

The "Watch" row is the differentiator: PwC's research warns CRQ decays into a stale
point-in-time number ("algorithmic inertia"). Because Colt runs the monitoring plane, our
number stays live.

---

## 6. Every finding — priced and fixed

Each card: the loss in CHF (method §2), the **comparable real incident**, and the
**remediation mapped to Colt products** in the house VENDOR/COLT/PSF/OSS structure (per
[`04-mitigation-mapping`](04-mitigation-mapping.md)). PSF preference: **Versa → Fortinet →
OSS**. ALE = mean annual loss; PML = worst single event; CoD/mo = cost of one month's delay;
ROSI = risk bought back vs. control cost. All CHF figures illustrative (see §0 warning).

---

### CRITICAL

#### C2 — Citrix NetScaler AAA on app-portal + test-portal (KEV-active) — *worked example, §2*
🔴 **CRITICAL** · BIA C5/I4/A5

| | |
|--|--|
| **Loss** | Citrix-Bleed-class RCE / session-token theft → pivot → ransomware/exfil. Prod + non-prod share the family. |
| **Frequency** | TEF 12 × Vuln 0.05 = **LEF 0.6/yr (Likely)** |
| **ALE** | **CHF 2.0 – 4.5 M/yr** · **PML CHF 25 – 90 M** · **CoD ≈ CHF 165–375 k/mo, rising** |
| **Comparable** | **ICBC FS / Citrix Bleed (Nov 2023)** — unpatched NetScaler *found on Shodan*; US Treasury settlement disruption; ~USD 9 bn injection. **Same CVE family, same discovery method as this report.** |
| **Fix — VENDOR** | Patch to fixed NetScaler build **and rotate ALL sessions/admin creds/federation tokens after patching** (Bleed artefacts survive the patch); responder policy to drop oversized GETs. |
| **Fix — COLT** | **Colt SASE/SSE with ZTNA** — replace the public AAA portal with identity-aware access. NetScaler stays as an internal load-balancer; **nothing internet-reachable for Shodan to find.** Directly serves the Zero-Trust direction in RFP §1. |
| **Fix — PSF** | **Versa SASE** (ZTNA + SWG, PSF-Existing) for user-to-app; **Fortinet FortiGate** managed L7 IPS in front during patch windows. Both already in PSF — no roadmap risk. |
| **Fix — OSS** | ProjectDiscovery **nuclei** templates `citrix-bleed-CVE-2023-4966`, run weekly vs the AS15532 perimeter; **Sigma** rules for post-exploit memory-leak patterns. |
| **After / ROSI** | LEF 0.6 → ~0.05; **ALE ≈ CHF 0.3 M.** Risk bought back **≈ CHF 3.4 M/yr. ROSI very high — top priority.** |

#### C1 — `raiffeisen.obsidio.com` — off-ASN brand asset, broken 256-bit DSA crypto
🔴 **CRITICAL** · BIA C5/I3/A2

| | |
|--|--|
| **Loss** | A Raiffeisen-branded login over broken crypto harvests member/staff credentials → credential-replay, or it is live brand-impersonation phishing. |
| **Frequency** | Brand-phishing is commodity. **LEF 0.3–0.7 (Likely)** |
| **ALE** | **CHF 0.4 – 1.3 M/yr** · **PML CHF 6 – 22 M** · **CoD ≈ CHF 35–110 k/mo** |
| **Comparable** | Banking-brand credential-phishing waves; Chain IQ-style off-ASN brand exposure |
| **Fix — VENDOR** | Validate provenance via Raiffeisen procurement (24 h). If a real vendor: force re-issue with 2048-bit RSA / ECDSA + migrate to a managed `raiffeisen.ch` subdomain. If not: abuse report to hosttech + registrar; engage NCSC.ch takedown. |
| **Fix — COLT** | **Colt SSE / Secure Web Gateway** — DNS-layer block of `*.obsidio.com` for Raiffeisen workforce traffic until disposition. Zero-touch protection during investigation. |
| **Fix — PSF** | **Versa SSE** (PSF-Existing) — DNS + URL-category enforcement at the user edge; route discovered shadow assets through the Versa cloud gateway under FINMA-2018/3-aligned policy. |
| **Fix — OSS** | **dnstwist** (lookalike permutations of raiffeisen.ch/.com) + **CertStream** (fires on every new CT-log entry containing "raiffeisen") → **TheHive** for triage. One VM. |
| **After / ROSI** | Block + takedown removes most of the ALE within days at trivial cost. **ROSI very high.** |

#### C3 — Five non-prod environments publicly reachable
🔴 **CRITICAL** · BIA C4/I3/A3

| | |
|--|--|
| **Loss** | Test/UAT/demo (weak patch SLA, weak auth, realistic data) breached → data leak, or low-friction pivot to prod (two front NetScaler/BigIP → inherit C2). |
| **Frequency** | Known soft target; several instances. **LEF 0.25–0.6 (Plausible→Likely)** |
| **ALE** | **CHF 0.5 – 1.6 M/yr** · **PML CHF 8 – 30 M** · **CoD ≈ CHF 40–135 k/mo** |
| **Comparable** | ICBC (shared NetScaler family via test-portal); supplier-hosted non-prod = Chain IQ pattern |
| **Fix — VENDOR** | Remove public DNS / put behind auth; enforce that non-prod never carries production-derived data. |
| **Fix — COLT** | **Colt SSE allow-list + ZTNA broker** — non-prod reachable only by named identities, never the open internet. |
| **Fix — PSF** | **Versa SD-WAN + SD-LAN** (PSF-Existing) — segment non-prod; pull the three supplier-hosted instances (Azure/EY, CONVOTIS, Flow Swiss) behind the security plane. |
| **Fix — OSS** | **subfinder + httpx** weekly to catch new non-prod hostnames the moment they appear. |
| **After / ROSI** | Removes a whole class of soft entry points. **ROSI high.** |

#### C4 — Unmanaged "VPN Portal" at senseLAN (off-ASN, unattributed)
🔴 **CRITICAL** · BIA C5/I4/A4

| | |
|--|--|
| **Loss** | An unattributed remote-access portal with no central control = an unmonitored standing door into the estate; if breached, **no Raiffeisen telemetry sees it** (long dwell). |
| **Frequency** | **LEF 0.15–0.4 (Plausible)** — but unmonitored access is structurally high-loss-if-realised. |
| **ALE** | **CHF 0.5 – 2.0 M/yr** · **PML CHF 10 – 40 M** · **CoD ≈ CHF 40–165 k/mo** |
| **Comparable** | Chain IQ (off-ASN supplier-borne); supplier-VPN compromise |
| **Fix — VENDOR** | Confirm attribution with central IT (48 h). If Raiffeisen-owned: bring under management. If not: block + investigate. |
| **Fix — COLT** | **Colt Managed SD-WAN + ZTNA** — the access path comes under central policy *and telemetry*. |
| **Fix — PSF** | **Versa SD-WAN + Fortinet FortiClient ZTNA** (PSF-Existing). |
| **Fix — OSS** | **RIPEstat / PeeringDB** to confirm ASN ownership; **Wazuh + Suricata** for monitoring once onboarded. |
| **After / ROSI** | Converts a blind spot into a monitored, policy-governed path. **ROSI high once provenance confirmed.** |

---

### HIGH

#### H5 — 10 external orgs hold raiffeisen-branded assets, no central control — *the strategic one*
🟠 **HIGH** · BIA C4/I3/A3 · **highest aggregate exposure in the report**

| | |
|--|--|
| **Loss** | A breach at any **one of 10** off-ASN suppliers exposes Raiffeisen data/brand with **no central WAF/SSE/policy and no Raiffeisen telemetry.** P(≥1 of 10 has an incident in a year) is high. |
| **Frequency** | **LEF 0.6–1.5 (Routine at the aggregate)** — FINMA names third-party reliance *the* key operational risk; CH FI attacks +~50 % (2024). |
| **ALE** | **CHF 1.2 – 3.8 M/yr (aggregate)** · **PML CHF 15 – 55 M** · **CoD ≈ CHF 100–315 k/mo** |
| **Comparable** | **Chain IQ → UBS / Pictet (Jun 2025)** — ~20 orgs, 130k+ records leaked; loss entered via a *shared supplier*, not the bank's own perimeter. **The exact H5 pattern.** |
| **Fix — VENDOR** | Cross-check all 10 against the FINMA-2018/3 outsourcing register; close the visibility gaps. |
| **Fix — COLT** | **Colt SASE — single security plane.** Consolidate 10 fragmented supplier edges into one governed, monitored policy plane. **This is the SD-WAN/SASE tender's core value, not a side fix.** |
| **Fix — PSF** | **Versa SASE + SSE** (PSF-Existing) — one identity/policy/telemetry plane across the supplier estate. |
| **Fix — OSS** | **OpenCTI + MISP** (supplier threat-intel) + **Wazuh** (telemetry) for any plane not yet on SASE. |
| **After / ROSI** | One accountable plane replaces 10 blind ones — directly the FINMA-2018/3 story RFP 343557 turns on. **ROSI very high; lead the pursuit with this.** |

#### H1 — OpenVPN Access Server reachable on 443 + 1194
🟠 **HIGH** · BIA C4/I4/A4

| | |
|--|--|
| **Loss** | Public VPN-AS = standing brute-force / credential-stuffing / CVE target → remote foothold without identity-awareness. **LEF 0.3–0.7 (Likely).** |
| **ALE** | **CHF 0.4 – 1.4 M/yr** · **PML CHF 6 – 22 M** · **CoD ≈ CHF 35–115 k/mo** · Comparable: edge-VPN ransomware-entry |
| **Fix** | **COLT/PSF: Colt SASE ZTNA replaces the VPN-AS** (Versa SASE / Fortinet FortiClient). **OSS:** Wazuh + Suricata. **After:** VPN attack surface removed. **ROSI high.** |

#### H2 — F5 BigIP fleet (4) fronting NetScaler — KEV-active family
🟠 **HIGH** · BIA C4/I4/A5

| | |
|--|--|
| **Loss** | BigIP CVE-family exploitation on internet-facing ADC → interception / pivot; **compounds C2.** **LEF 0.3–0.7 (Likely).** |
| **ALE** | **CHF 0.6 – 2.0 M/yr** · **PML CHF 10 – 35 M** · **CoD ≈ CHF 50–165 k/mo** · Comparable: ICBC architecture (BigIP fronted the NetScaler) |
| **Fix** | **COLT: Managed WAF + ADC modernisation. PSF: Fortinet FortiADC / FortiWeb. OSS:** nuclei + OWASP ZAP. **After:** couples with C2 — fix together. **ROSI high.** |

#### H3 — Self-signed Airlock "test.certificate" in production
🟠 **HIGH** · BIA C3/I4/A4

| | |
|--|--|
| **Loss** | Prod service trusting a test cert → MITM / trust-chain outage on a customer-facing path. **LEF 0.1–0.3 (Plausible).** |
| **ALE** | **CHF 0.2 – 0.8 M/yr** · **PML CHF 3 – 12 M** · **CoD ≈ CHF 15–65 k/mo** |
| **Fix** | **COLT: Managed WAF cert-lifecycle audit. PSF: Fortinet FortiWeb. OSS:** cert-manager + Smallstep. **ROSI medium-high.** |

#### H4 — Public SNMP on Cisco edge devices (2)
🟠 **HIGH** · BIA C3/I3/A3

| | |
|--|--|
| **Loss** | Internet-reachable SNMP → device/topology disclosure (recon uplift); config exposure if mis-set. SNMPv3 limits it. **LEF 0.1–0.3 (Plausible).** |
| **ALE** | **CHF 0.15 – 0.6 M/yr** · **PML CHF 2 – 9 M** · **CoD ≈ CHF 12–50 k/mo** |
| **Fix** | **COLT/PSF: Managed Firewall drops UDP/161 at the edge** (Versa SD-WAN + Fortinet FortiGate). **OSS:** LibreNMS / Prometheus for internal-only monitoring. **Cheap, fast, ROSI high.** |

#### H6 — SMTP banner exposure on 13 mail gateways
🟠 **HIGH** · BIA C3/I3/A3

| | |
|--|--|
| **Loss** | Banner/version disclosure across 13 gateways → targeted mail-path exploitation / BEC recon. **LEF 0.1–0.3 (Plausible).** |
| **ALE** | **CHF 0.15 – 0.7 M/yr** · **PML CHF 2 – 10 M** · **CoD ≈ CHF 12–60 k/mo** |
| **Fix** | **COLT: Web & Email Security (managed gateway). PSF: Fortinet FortiMail — _PSF gap, ESC route._ OSS:** Postfix + rspamd hardening. **ROSI medium.** |

---

### MEDIUM & LOW — condensed

These are hygiene / recon-uplift. Small standalone ALE, but they **raise the frequency of the
Criticals** — so their real value is modelled as frequency reduction on the big findings.

| ID | Sev | Loss driver | LEF | ALE | PML | Colt fix (product) |
|----|-----|-------------|-----|-----|-----|---------------------|
| **M1** | MED | Apache banner (116 hosts) — recon uplift | Routine recon | 60–250 k | 1–4 M | Managed WAF Server-header rewrite (Versa SSE / FortiWeb) |
| **M2** | MED | F5 BigIP banner disclosure | Routine recon | 50–200 k | 1–3 M | WAF edge rewrite (Fortinet FortiADC) |
| **M3** | MED | Pension-fund infra entirely off-ASN (CONVOTIS) | 0.1–0.3 | 0.3–1.1 M | 5–18 M | Cloud Connect + SSE policy extension (Versa SSE) |
| **M4** | MED | 80+ FQDNs on one iway IP — sub-brand sprawl | 0.1–0.3 | 0.2–0.9 M | 4–14 M | Managed DNS + SSE brand-policy (Versa SSE) |
| **M5** | MED | Sophos default appliance cert (2 hosts) | 0.1–0.3 | 0.1–0.5 M | 2–8 M | Managed Firewall replacement (Fortinet FortiGate) |
| **L1** | LOW | HTTP-only port-80 page | Low | 20–90 k | 0.3–1.5 M | Managed WAF default-redirect (Versa SSE) |
| **L2** | LOW | DigiCert SAN sprawl (30+ subdomains/cert) | Low | 30–120 k | 0.5–2 M | **PSF — Managed PKI / cert-lifecycle (_PSF gap, ESC route_)** |
| **L3** | LOW | `Server: xxxx` incomplete anonymisation | Low | 15–70 k | 0.2–1 M | SSE / WAF header policy (Versa SSE) |
| **L4** | LOW | Generic 400/403 baselines (62 hosts) | Low | 15–70 k | 0.2–1 M | WAF jitter + custom error page (Versa SSE) |

---

## 7. The board one-pager

The franc-denominated twin of the severity-counter table in the [README](README.md). **This
is the slide the CISO puts in front of the supervisory board.**

| Tier | Findings | Aggregate ALE (illustrative) | Largest single PML | Lead Colt fix |
|------|----------|------------------------------|--------------------|---------------|
| **CRITICAL** (4) | C1–C4 | **≈ CHF 3.4 – 9.4 M/yr** | C2 → ~CHF 90 M | SASE + ZTNA (Versa) |
| **HIGH** (6) | H1–H6 | **≈ CHF 2.1 – 7.5 M/yr** | H5 → ~CHF 55 M | SASE single plane (Versa) |
| **MEDIUM** (5) | M1–M5 | **≈ CHF 0.7 – 3.0 M/yr** | M3 → ~CHF 18 M | SSE / Cloud Connect |
| **LOW** (4) | L1–L4 | **≈ CHF 0.1 – 0.35 M/yr** | — | Managed WAF |
| **PORTFOLIO** | **19** | **≈ CHF 6.3 – 20.2 M/yr** | — | — |

**Read it like this:**

- The **CHF 6–20 M/yr** band is *expected* loss — the budgeting number.
- The big **PMLs (C2, H5)** are the *capital / insurance* numbers — report them separately, never averaged in.
- The two findings carrying both the **highest frequency and a real-world twin** — **C2 (ICBC)** and **H5 (Chain IQ)** — are the two that map straight onto the **SD-WAN/SASE pursuit.** The quantification and the sale point at the same place.

### 7.1 Show the curve, not a number (Gartner ODM)

Plot **P(annual loss ≥ X)** against CHF. The board reads it in one glance: "80 % chance we lose
at least CHF A; 10 % chance at least CHF B (the PML); **the Colt remediation shifts the whole
curve left by ΔCHF.**" That leftward shift *is* the ROSI — drawn, not asserted.

### 7.2 Why one Colt control beats a list of point-fixes

The §6 fixes are overwhelmingly **Versa SASE/SSE + Fortinet** — controls that **collapse
several findings at once**: ZTNA alone retires the public exposure in **C2, C3, C4, H1**; the
single security plane retires **H5, M3, M4**. Because one managed service buys back several
findings' ALE, **portfolio ROSI is far higher than any single-finding ROSI** — which is exactly
the managed-service argument RFP 343557 is asking Colt to make. A box-by-box patch list cannot
produce that compounding.

---

## 8. Slotting it into the deck

Per [`COLT_DESIGN_SYSTEM.md`](COLT_DESIGN_SYSTEM.md) §7:

- New section divider **`BUSINESS IMPACT.`** (black text, chevrons, trailing period) after Findings Index.
- On each finding card, a right-rail strip under EVIDENCE: three pills — **ALE** · **PML** · **CoD/mo** — coloured to severity (§1.2 palette).
- One **board one-pager** slide (§7 table + §7.1 curve).
- Reframe the Next-Steps closer as **"risk bought back per action."**
- Franc figures on **internal slides only**, watermarked *illustrative model output.*

---

## 9. Caveats specific to the numbers

In addition to all of [`05-caveats-and-next-steps.md`](05-caveats-and-next-steps.md):

| Topic | Position |
|-------|----------|
| **Illustrative, not measured** | Every CHF figure is model output from public benchmarks + stated assumptions (§2). Defensible *as a model*; not a measured loss or a prediction. Same status as the "fictional" Squalify/Deloitte graphics in the source article. |
| **Needs customer data to calibrate** | True calibration needs revenue-per-hour by service, incident history, the insurance tower, deposit-flight elasticity — none visible from Shodan. Until then, ranges are planning aids. |
| **Frequency is the soft spot** | LEF bands are house priors anchored on sector base-rates + the FINMA +~50 % trend. Stated openly (§2 step 3) so the customer can re-anchor them. |
| **Swiss ≠ EU on penalties** | nFADP fines hit **individuals up to CHF 250 k**, *not* %-of-turnover. **DORA's 2 % applies via EU-domiciled ICT providers, not the Swiss entity directly.** Never quote a turnover-% fine as a Raiffeisen prediction. |
| **PML ≠ ALE** | Never blend them. ALE = budget; PML = capital/insurance. Conflating them is the most common CRQ error. |
| **No double-counting** | Findings that share a loss path (C2⊃H2; C3⊃C2 via test-portal; H5⊃M3/M4) are **not** summed without a correlation haircut. The §7 bands already reflect this. |
| **Internal-only** | Colt pursuit material for RFP 343557. The franc figures especially must not reach Raiffeisen or any third party as if they were an audit finding. |

---

## 10. Sources

**Standards / frameworks:** FAIR (Open Group / FAIR Institute). NIST IR 8286D-upd1, *Using
Business Impact Analysis to Inform Risk Prioritization and Response* (Feb 2025) + the 8286A/B/C
series. PwC, *Unlocking Cyber Risk — 4 Key Steps* (Mar 2025) & *Global Digital Trust Insights
2025*. Deloitte, *Beneath the Surface of a Cyberattack* & Deloitte/CIONET *Unlocking Business
Value of Cyber Security*. EY, *Cyber Resilience through a Risk-Based Approach* (World Government
Summit 2023). Gartner — Outcome-Driven Metrics / Protection-Level Agreements. KPMG/EY/PwC
actuarial CRQ practice. Forrester Wave: Cyber Risk Quantification (CRQ tooling landscape).
**Benchmarks:** IBM Security/Ponemon *Cost of a Data Breach 2025* (FS ≈ USD 5.56 M; per-record
USD 128–234; supply-chain USD 4.91 M / 267 days). FINMA risk monitor (CH FI successful attacks
~+50 %, 2024) & third-party-risk position. Revised Swiss FADP (nFADP/nDSG, Sep 2023). EU Reg.
2022/2554 (DORA, enforced 17 Jan 2025). Raiffeisen Group Annual Report 2024 (assets ≈ CHF
305.6 bn; deposits ≈ CHF 215 bn; profit ≈ CHF 1.2 bn; Moody's A2). **Incidents:** Chain IQ →
UBS/Pictet (Jun 2025); ICBC FS → Citrix Bleed CVE-2023-4966 (Nov 2023); Swiss-sector ransomware
reporting (2025).

---

**[← Mitigation Mapping](04-mitigation-mapping.md)** · **[Caveats & Next Steps →](05-caveats-and-next-steps.md)** · **[Back to README](README.md)**

---

*Internal — Colt Confidential · NOT for external distribution · C-BIQ v2.0 · RFP 343557*
*Companion to the Raiffeisen Schweiz Active External Attack Surface Assessment*
