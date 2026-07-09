# Colt External Attack Surface Assessment — Deck Build Methodology

**Standard format for Colt Sales Engineering Shodan-Findings decks**

This document is the canonical recipe for producing a 30-slide deep-dive PowerPoint deck from a Shodan JSON export. It captures the structure, layout maths, content rules, and pptxgenjs implementation that work without rework. Use this as the baseline for every customer / prospect (Commerzbank, SGS, Innopolis, and onwards).

---

## 1. When to Use This Format

Use this deck format when:

- Source data is one or more Shodan JSON host-record exports for a named target (customer or prospect).
- Audience is **internal Colt** (account team, sales engineering, PSF, DDoS PM). Mark every page `INTERNAL — COLT CONFIDENTIAL · NOT FOR EXTERNAL DISTRIBUTION`.
- The deliverable needs to flow Critical → High → Medium → Low with per-finding evidence + Colt portfolio mapping.

Do **not** use this format when:

- The customer is the audience (use the SGS docx whitepaper format instead — narrative, methodology-heavy, with disclaimer chapters).
- The dataset has < 5 records or > 100 records (5-record decks should be a one-page briefing; 100+ records need a different scaling strategy — group findings by host-class, not per-host).
- The engagement is post-sale or remediation-tracking (different format — status report, not findings deck).

---

## 2. Pre-Build Checklist

Before writing a single line of code, work through this list. Every item below has caused rework on at least one prior deck.

### 2.1 Data inventory

Open the JSON, count records, and compute these numbers exactly:

| Metric | Source | Used on slide |
|--------|--------|----------------|
| Total records | sum of records across all files | Title, exec, methodology |
| Unique IPs | dedupe `ip_str` | Exec, asset inventory |
| Unique ASNs | dedupe `asn` | Asset inventory, brand-frag finding |
| Countries | dedupe `location.country_name` | Exec, methodology |
| Top hosting ASNs | count records per ASN, top 8 | Asset inventory |
| Top products | count records per `product` or `http.components` key | Asset inventory, CPE inventory |
| Hosts with `vulns` field | filter where `vulns` is non-null | Drives the Critical/High count |
| Hosts with expired SSL | parse `ssl.cert.expires`, compare to today | Often a Critical finding |
| Hosts with TLS 1.0/1.1 in `ssl.versions` (no leading `-`) | Often a High/Medium finding |

Dump this to a text file before drafting findings. The numbers must match across the title slide, exec summary, methodology, asset inventory, and caveats slides — five places. Recompute, don't transcribe from memory.

### 2.2 Severity calibration

The classification framework is fixed (do not deviate):

| Severity | Trigger |
|----------|---------|
| **CRITICAL** | CISA KEV-listed CVE on host, OR brand impersonation, OR expired cert on critical service, OR exposed admin console for production identity/network plane |
| **HIGH** | CVSS ≥ 7.5 with EPSS > 0.5 — OR unpatched edge-device family (VPN/load-balancer/mail) — OR non-prod environment exposed |
| **MEDIUM** | Information disclosure, weak crypto, foreign / third-party hosting of brand asset, supply-chain blast radius (shared hosting) |
| **LOW** | Banner/version disclosure, fingerprint sprawl, parked redirect infra, related but distinct entities sharing the brand name |

Target distribution for a 30-slide deck: **5 Critical · 7 High · 7 Medium · 4 Low = 23 findings**. This isn't arbitrary — it's what fits the slide budget (5 + 7 + 7 + 1 combined Low + 7 framing/wrap slides + cover = 30). If the actual data has more or fewer findings, adjust *within* the bands, not the bands themselves: combine related findings (e.g. multiple TLS 1.0 hosts → one finding) or split overloaded ones (e.g. one host with admin-console + expired cert → two findings).

### 2.3 Reference deck

Always start from the most recent Commerzbank or Innopolis pptx as a layout reference. The teal/navy/bordeaux palette, the page-header pattern, and the finding-card two-column layout are all defined there. Differentiate the new deck only on:

- **Palette accent**: pick one accent colour from the bank to distinguish. Commerzbank uses teal `0D9488`; Innopolis uses a navy `16213E` title with `E94560` rose accent. SGS-style would use a corporate blue. Don't change the structure.
- **Per-finding content**: every finding is unique. Don't reuse phrasing across decks — Shodan / customer staff read them all.
- **Frameworks cited**: BSI + BAIT for German banks; ENISA + NIS2 for EU education / industrial; FCA / PRA for UK financials; HKMA for Hong Kong. Use what the customer's regulator actually enforces.

---

## 3. Deck Structure — 30 Slides

The structure is fixed. Do not skip slides; do not add slides. If a section doesn't apply (e.g. no Medium findings worth detailing), repurpose the slot for a sub-finding break-out, not a new section.

| Slide | Purpose | Key elements |
|-------|---------|--------------|
| 1 | Title | Customer name, ASN list, date, classification, prepared-by, frameworks |
| 2 | Executive Summary | One-paragraph verdict + 4 severity cards (counts) + 3 priority headlines |
| 3 | Methodology & Data Scope | Data sources, classification framework, reference frameworks |
| 4 | Asset Inventory | 4 big-number stats + Top Products + Top Hosting ASNs |
| 5 | Findings At A Glance | 23-row table: severity, ID, finding, CVE/reference |
| 6 | Software Inventory (CPE) | CPE table: cpe-string, instance count, associated CVE/risk |
| 7-11 | 5 Critical findings | One finding per slide (see §4 for card layout) |
| 12-18 | 7 High findings | One per slide |
| 19-25 | 7 Medium findings | One per slide |
| 26 | Low findings (combined) | 2×2 grid of 4 Low findings on one slide |
| 27 | CVE Catalogue | Table of all distinct CVEs with CVSS, EPSS, KEV, found-on |
| 28 | Mitigation Mapping | Findings × Colt portfolio coverage matrix |
| 29 | Caveats & Confidence | What this report is/isn't, evidence base |
| 30 | Next Steps / 7-Day Horizon | Action owners (Account team, SE, DDoS PM, PSF) |

---

## 4. Finding-Card Layout (Slides 7-25)

This is the workhorse layout. Every Critical/High/Medium finding renders into it. The layout is **two columns**:

- **Left column** (x: 0.4–4.95) — Finding section: WHAT WE OBSERVED + EVIDENCE block + WHY IT MATTERS
- **Right column** (x: 5.05–9.7) — Remediation section: REFERENCES + 3 remediation rows tagged VENDOR/COLT/PSF/OSS

### 4.1 Vertical budget (16:9 slide = 5.625" tall)

| y-coord | Element | Height |
|---------|---------|--------|
| 0.18 | Eyebrow strip (severity · finding ID) | 0.22 |
| 0.40 | Title (reserved for 2-line wrap) | 0.85 |
| 1.30 | Severity badge + eyebrow + pills | 0.28 |
| 1.70 | Column headers (FINDING / REMEDIATION) | 0.26 |
| 2.00 | Sub-section labels (WHAT WE OBSERVED / REFERENCES) | 0.20 |
| 2.20 | WHAT WE OBSERVED body | 1.05 |
| 3.28 | EVIDENCE label | 0.20 |
| 3.48 | EVIDENCE block (dark) | 1.10 |
| 4.65 | WHY IT MATTERS label | 0.20 |
| 4.83 | WHY IT MATTERS body | 0.45 |
| 5.30 | Footer (page number, classification, colt logo right) | 0.22 |

Right column timing for remediation rows: start y 2.55, row height 0.90, 3 rows → ends 5.25. Tight but fits.

### 4.2 Content rules per element

**Title (`pageHeader`)** — Georgia 18pt bold, max ~95 chars to avoid 3-line wrap. Patterns that work:
- `<asset> — <product version> with <N> CVEs flagged`
- `<asset> — <protocol/cert finding> (<sub-detail>)`
- `<adjective> — <descriptive phrase>` for governance findings

**Eyebrow** — 9pt all-caps spaced text, `<TOPIC> · <SUB-TOPIC>`. Examples: `PKI · MAIL GATEWAY · EXPIRED-CERT`, `REMOTE ACCESS · FOREIGN HOSTING · FORTINET`.

**Pills** — Right-aligned at top, max 3 pills, 1.5" wide each. Use them for: CVE IDs (KEV-suffix if listed), CVSS scores, regulatory tags (`BSI TR-02102-2`), or status tags (`EOL-PRODUCT`, `EXPIRED 2019-09-08`).

**WHAT WE OBSERVED** — 4 lines of 8.5pt Calibri, ~95 chars per line. Lead with the asset (IP + hostname), state the product/version, give the date or context. Plain-English, no marketing fluff.

**EVIDENCE block** — Dark navy `1E2230` rectangle with Consolas 7.2pt mono text. Max 9 lines, each ≤ 50 characters. This is non-negotiable — anything longer wraps and corrupts the layout. Pattern:

```
<ip>:<port>    <hostname>           <asn> (<isp>)
Server:        <product>/<version>  Tag: <tag>
SSL CN:        <cn>                 Issuer: <issuer>
TLS versions:  <list>
CPE:           <cpe-string>
Vulns flagged:
  CVE-YYYY-NNNN   <description>   CVSS  KEV
  CVE-YYYY-NNNN   <description>   CVSS  --
```

If you can't fit it in 9 × 50, the finding is over-stuffed. Split it.

**WHY IT MATTERS** — 2-3 sentences of 8.2pt Calibri. State the business consequence, not the technical one. "Applicant PII exposure" not "nginx 1.18 has CVE-2023-44487."

**Remediation rows** — Each row has:
- Tag pill (0.7" wide) — VENDOR (orange), COLT (teal), PSF (navy), OSS (slate). Order: most-critical-first.
- Title (9.3pt bold) — concrete action, e.g. "Patch nginx to mainline 1.27.4+", "Colt Managed WAF — virtual-patching for legacy stack"
- Body (8.2pt) — 2-3 sentences. Always tie to a specific Colt product where possible.

Every finding card has exactly 3 remediation rows. Not 2, not 4. Three.

---

## 5. Palette & Typography

### Fixed across all decks

```javascript
const C = {
  pageBg:       "FFFFFF",       // body slides
  ink:          "1A1A1A",       // body text
  inkMuted:     "5B6470",       // secondary text
  divider:      "D8D6CF",       // hairlines
  evidenceBg:   "1E2230",       // dark evidence rectangle
  evidenceInk:  "E8E6E0",       // evidence mono text

  // Severity — fixed across all decks
  crit:         "8B0000",       // deep red
  high:         "C84B31",       // burnt orange
  med:          "D4A574",       // muted gold
  low:          "5C7C8A",       // slate blue
};
```

### Customer-specific (pick one accent)

```javascript
// Commerzbank pattern — teal
titleBg: "0F2027", titleAccent: "203A43", brand: "0F2027", accent: "0D9488"

// Innopolis pattern — navy + rose
titleBg: "16213E", titleAccent: "0F3460", titleBlue: "E94560", brand: "16213E", accent: "0D9488"

// Generic corporate — deep blue
titleBg: "1B2A4E", titleAccent: "2C3E50", brand: "1B2A4E", accent: "3498DB"
```

### Fonts

- **Headers** — Georgia (serif, professional, present on all Office installs)
- **Body** — Calibri (clean sans, default)
- **Mono / evidence** — Consolas (fixed-width, present on Office)

Sizes — fixed:
- Title: 18pt bold Georgia
- Section header: 10-11pt bold Calibri, charSpacing 2-3
- Body: 8.5pt Calibri
- Evidence: 7.2pt Consolas
- Footer: 8pt Calibri muted

---

## 6. Implementation — pptxgenjs

### 6.1 Setup

```bash
mkdir -p /home/claude/<customer> && cd /home/claude/<customer>
cp /mnt/user-data/uploads/*.json .
# pptxgenjs is installed globally — no per-project npm install
export NODE_PATH=/home/claude/.npm-global/lib/node_modules
```

### 6.2 Skeleton

```javascript
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";  // 10 x 5.625"
pres.author = "Colt Sales Engineering";
pres.title = "<Customer> — External Attack Surface Assessment";

const FONT_H = "Georgia";
const FONT_B = "Calibri";
const FONT_M = "Consolas";

const C = { /* palette from §5 */ };

let pageNum = 0;
const TOTAL = 30;

function footer(slide) {
  slide.addText(`${pageNum} / ${TOTAL}`, {
    x: 0.4, y: 5.3, w: 1.0, h: 0.22,
    fontSize: 8, fontFace: FONT_B, color: C.inkMuted, margin: 0,
  });
  slide.addText("INTERNAL — COLT CONFIDENTIAL · NOT FOR EXTERNAL DISTRIBUTION", {
    x: 2.0, y: 5.3, w: 6.0, h: 0.22,
    fontSize: 8, fontFace: FONT_B, color: C.inkMuted,
    align: "center", charSpacing: 2, margin: 0,
  });
  slide.addText("colt", {
    x: 8.6, y: 5.28, w: 1.0, h: 0.28,
    fontSize: 12, fontFace: FONT_H, italic: true, color: C.brand,
    align: "right", margin: 0,
  });
}

function pageHeader(slide, eyebrow, title) {
  slide.addText(eyebrow, {
    x: 0.4, y: 0.18, w: 9.2, h: 0.22,
    fontSize: 9, fontFace: FONT_B, color: C.accentDark,
    charSpacing: 3, bold: true, margin: 0,
  });
  slide.addText(title, {
    x: 0.4, y: 0.4, w: 9.2, h: 0.85,
    fontSize: 18, fontFace: FONT_H, color: C.brand, bold: true,
    valign: "top", margin: 0,
  });
}
```

### 6.3 The finding-card function

This is the single most reused function. Build it once, parameterise everything:

```javascript
function findingCard(slide, opts) {
  // opts: { sev, id, eyebrow, title, pills: [{text, bg, fg}],
  //         whatLines: [], evidenceLines: [], whyShort: "",
  //         refs: "", remediation: [{tag, title, body}] }
  pageHeader(slide, `${opts.sev}  ·  FINDING ${opts.id}`, opts.title);

  // Severity badge + eyebrow at y=1.30
  sevBadge(slide, opts.sev, 0.4, 1.30);
  slide.addText(opts.eyebrow, {
    x: 1.55, y: 1.30, w: 4.5, h: 0.28,
    fontSize: 9, fontFace: FONT_B, color: C.inkMuted,
    charSpacing: 3, bold: true, valign: "middle", margin: 0,
  });

  // Pills upper-right
  let px = 9.7;
  for (const p of (opts.pills || []).slice().reverse()) {
    px -= 1.55;
    pill(slide, p.text, px, 1.32, 1.5, p.bg, p.fg);
  }

  // LEFT COLUMN — FINDING section header
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.7, w: 0.08, h: 0.26,
    fill: { color: C.crit }, line: { type: "none" },
  });
  slide.addText("●  FINDING", {
    x: 0.55, y: 1.7, w: 2, h: 0.26,
    fontSize: 10, fontFace: FONT_B, color: C.ink, bold: true,
    charSpacing: 2, valign: "middle", margin: 0,
  });

  // WHAT WE OBSERVED
  slide.addText("WHAT WE OBSERVED", {
    x: 0.4, y: 2.0, w: 4.5, h: 0.2,
    fontSize: 8.5, fontFace: FONT_B, color: C.accentDark,
    bold: true, charSpacing: 2, margin: 0,
  });
  slide.addText(opts.whatLines.map((t, i) => ({
    text: t,
    options: {
      breakLine: i < opts.whatLines.length - 1,
      fontSize: 8.5, fontFace: FONT_B, color: C.ink,
    },
  })), {
    x: 0.4, y: 2.2, w: 4.55, h: 1.05,
    valign: "top", margin: 0, paraSpaceAfter: 2,
  });

  // EVIDENCE
  slide.addText("EVIDENCE", {
    x: 0.4, y: 3.28, w: 4.5, h: 0.2,
    fontSize: 8.5, fontFace: FONT_B, color: C.accentDark,
    bold: true, charSpacing: 2, margin: 0,
  });
  evidenceBlock(slide, opts.evidenceLines, 0.4, 3.48, 4.55, 1.1);

  // WHY IT MATTERS
  slide.addText("WHY IT MATTERS", {
    x: 0.4, y: 4.65, w: 4.5, h: 0.2,
    fontSize: 8.5, fontFace: FONT_B, color: C.accentDark,
    bold: true, charSpacing: 2, margin: 0,
  });
  slide.addText(opts.whyShort, {
    x: 0.4, y: 4.83, w: 4.55, h: 0.45,
    fontSize: 8.2, fontFace: FONT_B, color: C.ink,
    valign: "top", margin: 0,
  });

  // RIGHT COLUMN — REMEDIATION section header
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.05, y: 1.7, w: 0.08, h: 0.26,
    fill: { color: C.accent }, line: { type: "none" },
  });
  slide.addText("→  REMEDIATION  &  COLT FIT", {
    x: 5.2, y: 1.7, w: 4.5, h: 0.26,
    fontSize: 10, fontFace: FONT_B, color: C.ink, bold: true,
    charSpacing: 2, valign: "middle", margin: 0,
  });

  // REFERENCES
  if (opts.refs) {
    slide.addText("REFERENCES (BSI / CISA / VENDOR)", {
      x: 5.05, y: 2.0, w: 4.65, h: 0.2,
      fontSize: 8.5, fontFace: FONT_B, color: C.accentDark,
      bold: true, charSpacing: 2, margin: 0,
    });
    slide.addText(opts.refs, {
      x: 5.05, y: 2.2, w: 4.65, h: 0.3,
      fontSize: 8, fontFace: FONT_B, color: C.inkMuted,
      italic: true, valign: "top", margin: 0,
    });
  }

  // 3 REMEDIATION ROWS
  const startY = 2.55;
  const rowH = 0.9;
  const tagMap = {
    VENDOR: { bg: C.warn,   fg: "FFFFFF" },
    COLT:   { bg: C.accent, fg: "FFFFFF" },
    PSF:    { bg: C.brand,  fg: "FFFFFF" },
    OSS:    { bg: C.low,    fg: "FFFFFF" },
  };
  (opts.remediation || []).slice(0, 3).forEach((r, i) => {
    const y = startY + i * rowH;
    const tm = tagMap[r.tag] || tagMap.COLT;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 5.05, y, w: 0.7, h: 0.28,
      fill: { color: tm.bg }, line: { type: "none" },
    });
    slide.addText(r.tag, {
      x: 5.05, y, w: 0.7, h: 0.28,
      fontSize: 9, fontFace: FONT_B, bold: true, color: tm.fg,
      align: "center", valign: "middle", charSpacing: 1, margin: 0,
    });
    slide.addText(r.title, {
      x: 5.82, y, w: 3.85, h: 0.28,
      fontSize: 9.3, fontFace: FONT_B, color: C.ink, bold: true,
      valign: "middle", margin: 0,
    });
    slide.addText(r.body, {
      x: 5.82, y: y + 0.3, w: 3.85, h: rowH - 0.32,
      fontSize: 8.2, fontFace: FONT_B, color: C.inkMuted,
      valign: "top", margin: 0,
    });
  });

  footer(slide);
}
```

### 6.4 Supporting helpers

```javascript
function sevBadge(slide, sev, x, y) {
  const map = {
    CRITICAL: { bg: C.crit, fg: "FFFFFF" },
    HIGH:     { bg: C.high, fg: "FFFFFF" },
    MEDIUM:   { bg: C.med,  fg: "1A1A1A" },
    LOW:      { bg: C.low,  fg: "FFFFFF" },
  };
  const m = map[sev];
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 1.05, h: 0.28,
    fill: { color: m.bg }, line: { type: "none" },
  });
  slide.addText(sev, {
    x, y, w: 1.05, h: 0.28,
    fontSize: 10, fontFace: FONT_B, color: m.fg, bold: true,
    align: "center", valign: "middle", charSpacing: 2, margin: 0,
  });
}

function pill(slide, text, x, y, w, bg, fg) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h: 0.25, fill: { color: bg }, line: { type: "none" },
  });
  slide.addText(text, {
    x, y, w, h: 0.25,
    fontSize: 8.5, fontFace: FONT_B, color: fg, bold: true,
    align: "center", valign: "middle", charSpacing: 1, margin: 0,
  });
}

function evidenceBlock(slide, lines, x, y, w, h) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: C.evidenceBg }, line: { type: "none" },
  });
  const txt = lines.map((l, i) => ({
    text: l,
    options: {
      breakLine: i < lines.length - 1,
      fontSize: 7.2, fontFace: FONT_M, color: C.evidenceInk,
    },
  }));
  slide.addText(txt, {
    x: x + 0.08, y: y + 0.04, w: w - 0.16, h: h - 0.08,
    valign: "top", margin: 0,
  });
}
```

---

## 7. Build & QA Loop

Once the script is written, run this exact sequence:

```bash
cd /home/claude/<customer>
export NODE_PATH=/home/claude/.npm-global/lib/node_modules
node build_deck.js

# Render to PDF + JPGs
python3 /mnt/skills/public/pptx/scripts/office/soffice.py \
  --headless --convert-to pdf <Customer>_Shodan_Findings_Internal.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 100 <Customer>_Shodan_Findings_Internal.pdf slide

# Visual check via thumbnail grid (3 grids of 12 slides each)
python3 /mnt/skills/public/pptx/scripts/thumbnail.py \
  <Customer>_Shodan_Findings_Internal.pptx
```

View the three `thumbnails-*.jpg` files. Look for:

1. **Title-wrap collisions** — any slide where the title runs into the row below
2. **Evidence overflow** — any evidence block where text bleeds below the dark rectangle into WHY IT MATTERS
3. **Remediation overflow** — any row body that runs past the slide bottom
4. **Pill collisions** — any pill that overlaps another pill or the title

If you find any of these, the fix is usually one of:

- Shorten the evidence lines (max 9 lines × 50 chars at 7.2pt). Test in code: `Math.max(...lines.map(l => l.length))` should be ≤ 50.
- Shorten the title to fit in 2 lines (≤ 95 chars at 18pt).
- Drop a pill (use 2 instead of 3 if titles run long).
- Shorten remediation body to 2 sentences.

Do not iterate more than once on cosmetic fixes. The first pass + one targeted fix-pass is the budget.

---

## 8. Output & Hand-off

```bash
cp /home/claude/<customer>/<Customer>_Shodan_Findings_Internal.pptx \
   /mnt/user-data/outputs/
```

Then call `present_files` with the absolute outputs path. File naming convention:

```
<Customer>_Shodan_Findings_Internal.pptx
```

Examples: `Commerzbank_Shodan_Findings_Internal.pptx`, `SGS_Shodan_Findings_Internal.pptx`, `Innopolis_Shodan_Findings_Internal.pptx`.

---

## 9. Content Patterns That Always Work

### 9.1 Critical-finding archetypes

These five Critical-finding types recur across every deck. If the data supports any of them, lead with them.

1. **KEV-active edge device with version exposed** — VPN, load-balancer, mail gateway running a version flagged by CISA KEV. Always Critical, always patch-currency question.
2. **Expired or distrusted certificate on production service** — anything > 2 years expired, or any StartCom / WoSign / Symantec-distrust-era cert. Always Critical.
3. **Brand impersonation / phishing infrastructure** — typosquat domain serving the customer's brand. Highest priority because every hour live = customer at risk.
4. **Admin console of identity / MDM / SDN plane on internet** — Citrix Endpoint Mgmt, Versa Director, NetScaler Gateway. Always Critical — these grant lateral compromise to everything else.
5. **Brand fragmentation across unattributed ASNs** — the customer's name appears on hosting infrastructure outside their primary ASN, on third-party / foreign / cloud hosting. Critical when ≥ 5 distinct ASNs.

### 9.2 High-finding archetypes

- HTTP/2 Rapid Reset (CVE-2023-44487) on any nginx version
- Outdated Python / Flask / Werkzeug or Apache with 10+ CPE-matched CVEs
- Microsoft Exchange smtpd on the public internet
- Non-prod / dev / staging environment with public DNS
- Unattributed hosts (empty PTR) on customer-aligned datacenter ASN
- TLS 1.0 / 1.1 still negotiable

### 9.3 Medium-finding archetypes

- Foreign-country hosting of a brand asset (data-residency / jurisdiction question)
- Wildcard cert deployed on a third-party not aligned with the primary estate
- JARM TLS fingerprint sprawl (fleet trivially mappable from one query)
- Shared-hosting tenancy with many unrelated domains
- Separate brand entity sharing the customer's name (brand-monitoring deduplication)

### 9.4 Colt portfolio mapping shortcuts

Every finding maps to at least one of these portfolio anchors. Use them consistently across decks:

| Finding type | Primary Colt fit | Secondary |
|--------------|------------------|-----------|
| KEV-active edge device | SASE / SSE with ZTNA (replace VPN) | Managed WAF |
| Rapid Reset / DDoS-class CVE | IP Guardian Premium Plus | Managed WAF |
| Admin console on internet | SASE / ZTNA admin-only access | Managed WAF |
| Exchange / mail gateway exposure | Web & Email Security (managed) | — |
| Foreign / third-party hosting | SSE / CASB uniform policy | Cloud Security Posture |
| TLS legacy / weak crypto | Managed WAF (perimeter termination) | — |
| Wildcard cert / PKI sprawl | PSF — PKI lifecycle audit | OSS — crt.sh / Cert Spotter |
| Brand fragmentation | PSF — brand-asset attribution sprint | OSS — dnstwist / URLScan.io |
| Non-prod exposure | SASE / SSE with ZTNA | OSS — Cloudflare Tunnel / Tailscale |
| Banner disclosure | Managed WAF (response rewrite) | — |

---

## 10. Common Pitfalls (Learned The Hard Way)

1. **Don't bulk-replace evidence blocks via regex** — at least one always breaks because the trailing-comma matching fails on multi-line arrays. Edit each one with `str_replace` and a clear unique anchor.
2. **Title height must reserve 2 lines** — at 18pt, set `h: 0.85`. Single-line titles look fine in extra space; two-line titles in single-line space collide with everything below.
3. **Evidence is the most-overflowed element** — budget 9 lines max × 50 chars max at 7.2pt Consolas. Anything more wraps and corrupts the layout.
4. **Slide masters are not worth the complexity** — define helpers (`pageHeader`, `footer`, `findingCard`) as plain functions. Re-add them per slide.
5. **Don't reuse option objects** — pptxgenjs mutates options in-place (especially `shadow`). Use factory functions if needed: `const makeShadow = () => ({ ... })`.
6. **No "#" prefix on hex colors** — `"FF0000"` is correct, `"#FF0000"` corrupts the file.
7. **No 8-char hex for transparency** — use the `opacity` property on shapes / shadows instead. `"00000020"` corrupts; `color: "000000", opacity: 0.12` works.
8. **First render usually has 3-5 real overflow issues** — fix them in one pass, then stop. Don't chase sub-pixel adjustments.

---

## 11. Customer-Specific Variations Already Built

| Customer | Palette accent | Distinctive notes |
|----------|----------------|---------------------|
| Commerzbank AG | teal `0D9488` on cream | BSI / BAIT / DORA frameworks; bank-style typography |
| SGS | corporate blue (docx whitepaper format, not deck) | NIS2 / Strategy 27 alignment; Versa SD-WAN context |
| Innopolis | navy `16213E` + rose `E94560` | ENISA / NIS2 / education-sector focus; brand-fragmentation as headline |

To start a new customer:

1. Copy the most-recent `build_deck.js` from the prior customer's `/home/claude/` directory
2. Adjust the palette constants in `C` (§5)
3. Replace the title-slide customer name, ASN, date
4. Re-run the data inventory checklist (§2.1) — recompute every number
5. Rewrite finding content (do **not** reuse text verbatim across customers)
6. Update the mitigation mapping (§9.4) only if the customer has different portfolio preferences (e.g. no IP Guardian if Anycast-DDoS is out of scope)
7. Build → render → QA per §7
8. Hand off per §8

---

## 12. Time Budget

For an experienced operator working from this MD, the budget is:

- **Data inventory + finding classification**: 30 min
- **Script adaptation from prior customer**: 20 min
- **Content writing (23 findings × ~5 min)**: 2 hours
- **Build + first render**: 5 min
- **QA + targeted fixes**: 30 min
- **Hand-off**: 5 min

**Total: ~3.5 hours from JSON to delivered deck.**

If a build run takes longer than this, the cause is almost always content rewriting — either the data inventory wasn't done up-front, or the finding-classification was reshuffled mid-build. Both are addressable by following §2 strictly before opening the editor.

---

*Colt Sales Engineering · Internal methodology · v1.0 · 25 May 2026*
*Reference decks: Commerzbank (07 May 2026), Innopolis (25 May 2026), SGS whitepaper (01 May 2026)*
