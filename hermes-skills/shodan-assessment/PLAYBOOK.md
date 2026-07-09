# COLT PRE-SALES REPORT PLAYBOOK — the one source of truth

This is the master reference for producing Colt's three pre-sales reports from a single
company input (name / URL / domain / ASN). Follow it exactly. Everything is data-driven:
you run scripts, you do NOT hand-write Shodan queries, and you NEVER fabricate data.

The three reports (always in this order — each feeds the next):
1. **Stratos Cyber Security Assessment** — Shodan external attack surface (Critical/High/Medium/Low).
2. **C-BIQ** — Business-Impact Quantification: each finding priced in € via FAIR/Monte-Carlo.
3. **GEOPOL** — named, sourced threat actors for the sector, tied back to the findings.
Plus the customer-facing synthesis: **One-Finding-Three-Lenses**.

## ⚡ THE ONE COMMAND (use this — fully autonomous, no manual steps, no rate-limits)
```
python3 /root/.hermes/skills/shodan-assessment/scripts/run_assessment.py --seed "<input>" --outdir /root/work
```
This runs the WHOLE chain deterministically (no LLM writing JSON): recon → findings.json →
derive cbiq.json + geopol.json → build all 3 decks. Attach the 3 `.pptx` from `/root/work`.
Only drop to the per-report steps below if you need to customise or a single deck FAILs.
CDN/thin result → re-run with `--asn AS<N> --net <CIDR>` (find on bgp.he.net by company name).

Scripts dir: `/root/.hermes/skills/shodan-assessment/scripts/`
Work dir (outputs): `/root/work/`
Keys already in env: `SHODAN_API_KEY`. Model = your DigitalOcean Qwen.

---

## 0. GOLDEN RULES (never break)
1. **Run the scripts. Never eyeball shodan.io in a browser** — that returns the CDN
   (Cloudflare) and false positives, not the company's real estate.
2. **Never invent** hosts, CVEs, actors, or numbers. Every fact traces to Shodan, RIPE,
   or a cited source. If empty, say so.
3. **Remove false positives**: every host must tie to the target by ASN, netblock, cert CN,
   or hostname. The CDN itself is never a "finding".
4. All € figures are **"ILLUSTRATIVE MODEL OUTPUT"** (the generators stamp this) — keep it.
5. Passive only. Active follow-up (scanning, logins) needs written authorization — state it.
6. One report chain per request. If the model is rate-limited, wait and retry the SAME step
   (see §8) — do not restart the whole chain.

---

## 1. END-TO-END WORKFLOW (company → 3 reports)
Mirrors the analyst process in `reference/` (Upgaming practice 01→06):
1. **Identity/audit** — resolve entities, ASNs, netblocks, domains (the recon script does this).
2. **Recon + filters** — build the canonical Top-10 Super Filters, run Shodan → `findings.json`.
3. **Report 1 (Shodan)** — build the findings deck.
4. **Report 2 (C-BIQ)** — derive `cbiq.json` from the findings, price them, build the deck.
5. **Report 3 (GEOPOL)** — derive `geopol.json` (sector actors tied to findings), build the deck.
6. **Synthesis** — pick one HIGH/CRIT finding, run it through all three lenses (§6).

---

## 2. REPORT 1 — STRATOS CYBER ASSESSMENT (Shodan)

### 2a. Run recon
```
python3 /root/.hermes/skills/shodan-assessment/scripts/shodan_recon.py \
    --seed "<exactly what the user typed>" --outdir /root/work
```
Read the last line: `RESULT ips=<N> cdn=<true|false> asns=<n>`.

### 2b. Branch (CDN / thin result)
- `ips>=3 and cdn=false` → good, go to 2c.
- `cdn=true OR ips<=2 OR asns=0` → the domain is behind a CDN/shared host. Find the company's
  REAL network: on **bgp.he.net** search the **company name** → note its **ASN** and **prefixes**
  (if it has no own ASN, note the RIPE **netblock assigned to it**, e.g. a Telekom /27).
  Cross-check **northdata.com** (legal entity/HQ). Then re-run feeding the real network:
  ```
  python3 .../shodan_recon.py --seed "<company>" --asn AS<NNNN> --net <CIDR> --outdir /root/work
  ```
- Still empty → the company has almost no internet-facing footprint. Say so; do not invent.

### 2c. The Top-10 Super Filters (auto-built — do not write by hand)
`asn:` · `net:` (master) · `org:` · `ssl.cert.subject.cn:` · `ssl:"Org"` · `hostname:` ·
remote/DB ports · VPN/firewall mgmt · RDP/WinRM/VNC · OT/ICS · mail · vuln+TLS hygiene · panels.
Full port lists + the org-vs-carrier rule are in `reference/FILTERS_PLAYBOOK_KEB.md`. Under a
**carrier** (ISP) the assigned `net:` is authoritative; under a **CDN** use cert/hostname + the
real ASN.

### 2d. Severity (from `reference/SEVERITY_FRAMEWORK.md`)
- CRITICAL: CISA KEV CVE · exposed DB/ICS · internet-facing RDP · unmanaged off-ASN brand asset.
- HIGH: CVSS≥7.5 & EPSS>0.5 · exposed VPN/edge appliance · Telnet/VNC/WinRM · exposed panel/OWA.
- MEDIUM: weak/expired/self-signed TLS · verbose banners · info-disclosure.
- LOW: standard services · recon metadata · hygiene.

### 2e. Build the deck
```
node /root/.hermes/skills/shodan-assessment/scripts/build_findings_deck.js \
    /root/work/findings.json "/root/work/<Company>_Shodan_Findings.pptx"
```

### findings.json schema
```json
{ "target":{"company","audience","date","scope"},
  "summary":{"records","unique_ips","asns","countries","critical","high","medium","low"},
  "findings":[{"sev":"CRITICAL","id":"C1","title","what":[],"evidence":[],"why":[],"rem":[],"refs":[]}] }
```

---

## 3. REPORT 2 — C-BIQ (business impact in €)

### The FAIR math (exact)
```
LEF = TEF × Vuln                          (Loss Event Frequency)
PERT(min,likely,max) = (min + 4·likely + max) / 6
meanLM = Σ PERT(L1…L7)                     (7 loss buckets)
ALE = LEF × meanLM                         (Annual Loss Expectancy — the budget number)
PML ≈ 95th percentile of the loss distribution (capital/insurance — never averaged into ALE)
CoD = ALE ÷ 12                             (Cost of Delay per month)
ROSI = (ALE_before − ALE_after − control_cost) ÷ control_cost
```
Monte-Carlo: 10,000 runs, PERT/triangular sampling. Seven buckets L1–L7:
L1 Response/forensics · L2 Regulatory/legal (FINMA/BSI/NIS2/DORA/GDPR) · L3 Operational downtime ·
L4 Customer/revenue · L5 Reputational · L6 Third-party/contractual · L7 Capital/funding.
Frequency bands (ARO/yr): Routine 1–4 · Likely 0.3–1 · Plausible 0.1–0.3 · Tail 0.02–0.1.
Benchmark anchors: IBM/Ponemon 2025 avg breach ≈ USD 5.56M (FS); PwC ~15% of orgs quantify;
DORA up to 2% turnover / €5M for critical ICT third parties. Method detail: `reference/06-business-impact-quantification.md`.

### Build
```
node /root/.hermes/skills/shodan-assessment/scripts/build_cbiq_deck.js \
    /root/work/cbiq.json "/root/work/<Company>_C-BIQ.pptx"
```
The generator computes lef/meanLM/ale/cod/rosi if you omit them — supply the raw inputs.

### cbiq.json schema (derive from findings.json)
```json
{ "customer","currency":{"code":"EUR","symbol":"€","word":"euros"},
  "classification":"INTERNAL — COLT CONFIDENTIAL · ILLUSTRATIVE MODEL OUTPUT",
  "frameworks":"FAIR · NIST IR 8286D","method":"Monte-Carlo CRQ (10k runs)","remediationSuite":"DDoS · WAF · Mgd FW · SASE",
  "montecarlo":{"runs":10000,"distribution":"PERT"},
  "frequencyBands":{"Routine":[1,4],"Likely":[0.3,1],"Plausible":[0.1,0.3],"Tail":[0.02,0.1]},
  "buckets":[{"id":"L1","name":"Response & forensics","surface":"above"}, "...L2..L7"],
  "benchmarks":[{"label","value","source"}],
  "findings":[{"id":"C-01","tier":"CRIT","label","asset":{"C":4,"I":4,"A":5},"lossScenario","realComparable",
    "tef":12,"vuln":0.08,"lmBuckets":{"L1":[0.1,0.3,1.0],"...":"..."},
    "aleRange":[2,5],"pmlRange":[25,80],"coltControl":"SASE","controlCost":0.5,"aleAfter":0.2}],
  "portfolio":{"aleRange":[6.5,17],"aleLikely":10.4,"largestPmls":[{"id":"C-01","pml":80}],
    "waterfall":[{"label":"− SASE","cut":5.15,"svc":"SASE / ZTNA"}],"rosiPct":590,"payback":"< 3 months","codAvoided":"€0.6–0.9M/mo"},
  "lossExceedance":{"thresholds":["€1M","€5M","€10M","€20M","€40M"],"before":[97,66,44,25,11],"after":[6,1.5,0.6,0.2,0.05]} }
```
Map severity → tier (CRITICAL→CRIT). Pick TEF/Vuln from the frequency bands + KEV/EPSS of the CVE.

---

## 4. REPORT 3 — GEOPOL (who is coming)

### The actor model
- **Relevance tier = Intent × Capability × Exposure-fit** → CRITICAL/HIGH/MEDIUM/LOW (this drives
  inclusion — relevance, not fame). Colors: crit/high/med/low.
- **Four bands** (fixed order): NATION-STATE → STATE-ALIGNED → ORGANISED eCRIME → HACKTIVIST.
- **Admiralty grade** on every attribution: source reliability A–F × credibility 1–6
  (CISA joint advisory ≈ A1; single vendor blog ≈ B2; forum chatter ≈ D4).
- **12-month likelihood** from the same bands as C-BIQ (Likely 0.3–1/yr, Plausible 0.1–0.3).
- Frameworks: MITRE ATT&CK, Diamond, Kill-Chain, ACH/Heuer, Pyramid of Pain; regulator bridge
  TIBER-EU/DORA/BSI/BaFin/ENISA-NIS2/CISA-KEV. Sector anchors from BSI. Detail: `reference/COLT_GEOPOL_ASSESSMENT_METHODOLOGY.md`.
- Choose actors by the target's jurisdiction × sector × the actual findings (e.g. exposed
  Check Point VPN CVE → Qilin RaaS; Russian-owned energy → pro-Ukraine hacktivists + Sandworm).
- **Tie each actor to a finding** via `linkedFindingId` (this powers §6).

### Build
```
node /root/.hermes/skills/shodan-assessment/scripts/build_geopol_deck.js \
    /root/work/geopol.json "/root/work/<Company>_GEOPOL.pptx"
```

### geopol.json schema
```json
{ "customer","date","classification","frameworks":"MITRE ATT&CK · Diamond · Admiralty · CVSS/EPSS/KEV","shelfLifeMonths":6,
  "exposureMap":[{"driver","attracts","why"}], "sectorContext":"BSI 2025: …",
  "likelihoodBands":{"Likely":[0.3,1],"Plausible":[0.1,0.3],"Routine":[1,4]},
  "actors":[{"band":"ORGANISED eCRIME","sponsor","tier":"CRITICAL","eyebrow","title","pills":["≤3"],
    "what":["lines"],"evidence":["≤9 mono lines incl 'Grade A2'"],"why","refs","admiraltyGrade":"A2",
    "score":{"intent":"High","capability":"High","exposureFit":"High"},"likelihood12mo","linkedFindingId":"C-01",
    "rem":[{"tag":"VENDOR","title","body"},{"tag":"COLT","title","body"},{"tag":"PSF","title","body"}]}],
  "killChain":{"scenarioTitle","steps":["Recon — …","Weaponise — …","Deliver — …","Exploit — …","Impact — …","Monetise — …"]},
  "cbiqBridge":[{"scenario","ale":"2.0–5.0 M","pml":"25–80 M","note","linkedFindingId":"C-01"}] }
```
tag colors: VENDOR→orange, COLT→teal, PSF→tealDark, OSS→gray.

---

## 5. ONE-FINDING-THREE-LENSES (the customer-facing close)
Take ONE real HIGH/CRIT finding and run it through all three lenses so they reinforce:
- **Lens 1 — Shodan:** *what is open* (the real evidence: host, CVE/KEV, cert).
- **Lens 2 — C-BIQ:** *what it costs* (that same finding's ALE/PML/CoD/ROSI).
- **Lens 3 — GEOPOL:** *who is coming* (the named actor with `linkedFindingId` = that finding).
Close with the synthesis row: `[What's open | What it costs | Who's coming | What stops it]` →
Colt portfolio. Narrative: "Shodan says what's open · C-BIQ says what it costs · GEOPOL says
who's coming — Colt + S4Biz find it, price it, name the adversary, fix it, keep watching it."

---

## 6. DESIGN SYSTEM (also for any HTML) — `reference/COLT_DESIGN_SYSTEM.md`
Hex WITHOUT `#`: teal `00D7BD` · tealDark `0C544E` · black `121212` · crit `F20C36` · high `FF7900`
· med `FFC33C` · low `474946` · ink `1A1A1A` · divider `D8D6CF`. Fonts: Georgia (headings),
Calibri (body), Consolas (mono/evidence), Arial Black (display), Arial (`colt` wordmark).
Chrome: top-right `colt` wordmark, stacked teal chevrons, `»» N/TOTAL` tracer, footer
classification line. The generators already bake all of this — match it in HTML variants.

---

## 7. DELIVERY
Attach the `.pptx` in the chat. 3-line summary: C/H/M/L counts, the single most urgent finding,
and (if behind a CDN) which real ASN/netblock you assessed. Offer C-BIQ and GEOPOL next.

## 8. RATE-LIMITING (model provider)
"The model provider is rate-limiting requests" = your DO Qwen endpoint hit its per-minute
request/token cap (browsing burns many calls; big context burns tokens). Mitigate: prefer the
scripts over browsing (one shell call vs dozens of LLM calls); `/new` between reports to shrink
context; wait ~30–60s and retry the SAME step; keep answers tight. Not a bug — a throughput cap.

## Reference index (`reference/`)
FILTERS_PLAYBOOK_KEB.md · SEVERITY_FRAMEWORK.md · COLT_SHODAN_DECK_METHODOLOGY.md ·
06-business-impact-quantification.md · COLT_GEOPOL_ASSESSMENT_METHODOLOGY.md · COLT_DESIGN_SYSTEM.md
