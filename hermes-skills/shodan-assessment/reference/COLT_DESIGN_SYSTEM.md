# Colt Design System — Reference for PPTX Decks

**Canonical visual-identity recipe for any Colt-branded slide deliverable.**
This document captures the exact palette, typography, motifs, and layout patterns extracted from the official Colt template (`Colt_Template_26.potx`, theme1.xml) and codified into reusable pptxgenjs primitives.

Pair this with `COLT_SHODAN_DECK_METHODOLOGY.md` when building findings decks; use this alone when building any Colt-branded slide deliverable (proposal, status report, customer briefing).

---

## 1. Brand Palette — Authoritative Hex Values

Extracted from `ppt/theme/theme1.xml` of the official `Colt_Template_26.potx`. These are the **only** colors that should appear in a Colt-branded deck. Do not invent shades; do not source from screenshots.

### 1.1 Primary brand colors

| Name | Hex | Usage |
|------|-----|-------|
| **Brand teal** | `00D7BD` | Primary brand color; chevrons, accent strips, eyebrow text, CTA elements |
| **Secondary teal** | `00A49A` | Secondary teal — supporting accents, hover/secondary states |
| **Deep teal** | `0C544E` | Headings, content-slide titles, dark teal sections (e.g. Next Steps slide bg) |
| **Brand near-black** | `121212` | Body ink on light backgrounds; logo; bold display type |
| **Brand dark gray** | `474946` | Low-severity bg, muted UI chrome, alternative dark neutral |
| **Light gray** | `ECECED` | Subtle backgrounds, alternating table rows, callout boxes on white |

### 1.2 Severity / state colors (also brand-aligned)

| Name | Hex | Usage |
|------|-----|-------|
| **Brand red** | `F20C36` | CRITICAL severity, alarms, decline/abort states |
| **Brand orange** | `FF7900` | HIGH severity, warning states |
| **Brand amber** | `FFC33C` | MEDIUM severity, the yellow square accent on title slides |
| **Brand gray** | `474946` | LOW severity, secondary informational |

### 1.3 Functional grays

| Name | Hex | Usage |
|------|-----|-------|
| **Body ink** | `1A1A1A` | Body text on white/light bg |
| **Muted ink** | `5B6470` | Captions, secondary text, supporting copy |
| **Divider** | `D8D6CF` | Hairlines, table borders |
| **White** | `FFFFFF` | Default canvas, chevrons |

### 1.4 pptxgenjs constant block (copy-paste)

```javascript
const C = {
  // Brand
  teal:        "00D7BD",   // primary brand teal
  tealMid:     "00A49A",   // secondary teal
  tealDark:    "0C544E",   // deep teal — content-slide titles
  black:       "121212",   // brand near-black
  dark:        "474946",   // brand dark gray
  light:       "ECECED",   // light gray bg

  // Severity (brand-aligned)
  crit:        "F20C36",   // brand red
  high:        "FF7900",   // brand orange
  med:         "FFC33C",   // brand amber
  low:         "474946",   // brand gray

  // Functional
  ink:         "1A1A1A",
  inkMuted:    "5B6470",
  divider:     "D8D6CF",
  white:       "FFFFFF",

  // Evidence block (dark mono panel)
  evidenceBg:  "121212",
  evidenceInk: "ECECED",
};
```

> ⚠️ **No `#` prefix on hex codes.** pptxgenjs requires raw 6-char hex. `"#FF0000"` corrupts the file.
> ⚠️ **No 8-char hex for transparency.** Use `opacity: 0.5` instead.

---

## 2. Typography

### 2.1 Font stack

| Role | Family | Weight | Notes |
|------|--------|--------|-------|
| **Display / titles** | Arial Black | Bold | Title slides + section dividers — the iconic Colt heavy display |
| **Content titles** | Georgia | Bold 18pt | Two-line max, content slides |
| **Body** | Calibri | Regular / Bold | Default body text, 8.5pt baseline |
| **Mono / evidence** | Consolas | Regular | Evidence blocks, IP/hostname data, 7.2pt |
| **Logo** | Arial | Bold | The lowercase "colt" wordmark — never italic, always solid weight |

### 2.2 Size scale

| Element | Size | Face | Weight |
|---------|------|------|--------|
| Title-slide hero text (e.g. "WEMPE GROUP.") | 64–72pt | Arial Black | Bold |
| Section divider severity word | 90pt | Arial Black | Bold |
| Content slide title | 18pt | Georgia | Bold |
| Eyebrow / category label | 9–11pt | Calibri | Bold, charSpacing 3 |
| Section header within slide | 10–11pt | Calibri | Bold, charSpacing 2-3 |
| Body | 8.5pt | Calibri | Regular |
| Evidence (mono) | 7.2pt | Consolas | Regular |
| Footer / classification | 7.5–8pt | Calibri | Regular, muted |

### 2.3 Character-spacing convention

All-caps eyebrows and labels use `charSpacing: 2–4` to mimic the wide, deliberate letterspacing in the official template. Lowercase body text never gets letter-spacing.

---

## 3. The Chevron Motif — Colt's Signature

The single most recognizable Colt visual element. Three upward-pointing white isoceles triangles, stacked vertically, with thin teal gaps between them. Used on:

- Title slides (right side, bleeding off-canvas)
- Section dividers (centered, full-width)
- Selected feature slides (decorative or as a tracer)

### 3.1 Construction parameters

| Variant | Dimensions | Stack count | Gap | Notes |
|---------|------------|-------------|-----|-------|
| **Title-slide right-bleed** | w: 5.0", h: 2.0" each | 3 | 0.05" | Sits at x: 5.8", extends beyond right edge |
| **Section divider centered** | w: 9.0", h: 1.55" each | 3 | 0.30" | Spans nearly full slide width |
| **Tracer (bottom-right indicator)** | w: 0.10–0.14", h: 0.16" each | 2-3 | 0.02" | Small `»»` ornament near page number |

### 3.2 pptxgenjs helper

```javascript
// Three big white upward chevrons spanning the slide width
function bigChevrons(slide, opts = {}) {
  const x      = opts.x      !== undefined ? opts.x      : 0.5;
  const w      = opts.w      !== undefined ? opts.w      : 9.0;
  const yStart = opts.yStart !== undefined ? opts.yStart : 0.20;
  const triH   = opts.triH   !== undefined ? opts.triH   : 1.55;
  const gap    = opts.gap    !== undefined ? opts.gap    : 0.30;
  const color  = opts.color  || "FFFFFF";
  for (let i = 0; i < 3; i++) {
    const y = yStart + i * (triH + gap);
    slide.addShape(pres.shapes.ISOSCELES_TRIANGLE, {
      x, y, w, h: triH,
      fill: { color }, line: { type: "none" },
    });
  }
}
```

### 3.3 Tracer chevron (bottom-right page indicator)

The `»» N` ornament used on every content slide:

```javascript
function chevronTracer(slide, pageNum, color = "0C544E") {
  for (let i = 0; i < 3; i++) {
    slide.addShape(pres.shapes.RIGHT_TRIANGLE, {
      x: 8.30 + i * 0.14, y: 5.32, w: 0.11, h: 0.16,
      fill: { color }, line: { type: "none" }, rotate: 90,
    });
  }
  slide.addText(`${pageNum}`, {
    x: 8.85, y: 5.27, w: 1.0, h: 0.28,
    fontSize: 10, fontFace: "Calibri", color, bold: true,
    align: "right", valign: "middle", margin: 0,
  });
}
```

---

## 4. The "colt" Logo Treatment

The lowercase "colt" wordmark appears top-right on **every** slide except the section dividers (which carry their own version).

- **Font**: Arial, bold
- **Color**: Brand near-black `121212` on light backgrounds; white `FFFFFF` on dark/severity backgrounds
- **Size**: 14–22pt depending on slide scale (title: 22pt; content slides: 14–18pt; section dividers: 18pt)
- **Position**: `x: 9.05–9.20", y: 0.18"` — flush right, 0.18" from top
- **Casing**: Always lowercase; never italicized

```javascript
function corner(slide, color = "121212") {
  slide.addText("colt", {
    x: 9.10, y: 0.18, w: 0.8, h: 0.32,
    fontSize: 18, fontFace: "Arial", color, bold: true,
    align: "right", margin: 0,
  });
}
```

---

## 5. Layout Patterns

### 5.1 Title slide

**The Colt title-slide DNA** — used as slide 1 of every deck. Variations seen in the template (slides 1-5 of `Colt_Template_26.potx`) keep this skeleton:

| Element | Position | Style |
|---------|----------|-------|
| Background | Full slide | Brand teal `00D7BD` |
| Three white chevrons | x: 5.8", right-bleeding | bigChevrons() — sized to extend off edge |
| "colt" logo | Top-right (9.05", 0.18") | 22pt Arial Bold black |
| Eyebrow line | x: 0.5", y: 1.25" | 11pt Arial Bold caps, charSpacing 3, black |
| Hero title line 1 | x: 0.5", y: 1.70" | 72pt Arial Black bold |
| Hero title line 2 | x: 0.5", y: 2.75" | 72pt Arial Black bold |
| Yellow accent square | Below the period of title | 0.22" × 0.22" brand amber square |
| Subtitle / date | y: 3.95" | 14pt Arial Bold |
| Metadata strip | y: 5.0", full width | Brand near-black bg, teal labels, white values |
| Tracer + page num | Bottom-right | Standard tracer |

> The **square accent** is a deliberate Colt motif — distinct from a circular dot. Always `C.med` amber. Always squared corners.

### 5.2 Section divider

Used to introduce major sections (e.g. CRITICAL / HIGH / MEDIUM / LOW). The most visually intense slide in the deck.

| Element | Position | Style |
|---------|----------|-------|
| Background | Full slide | Severity color (`crit`, `high`, `med`, or `low`) |
| Three big chevrons | Centered, full-width | bigChevrons() with default params |
| Section word | Centered, y: 1.85" | 90pt Arial Black, bold, black `121212` |
| Period after word | Inline with section word | Same style — the iconic Colt trailing period |
| "colt" logo | Top-right | Bold black (always; never recolor on dividers) |
| Tracer + page num | Bottom-right | Standard tracer in black |

```javascript
function sectionDivider(label, bgColor) {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: bgColor };
  bigChevrons(s, { x: 0.5, w: 9.0, yStart: 0.10, triH: 1.55, gap: 0.30, color: "FFFFFF" });
  s.addText(label + ".", {
    x: 0, y: 1.85, w: 10, h: 1.80,
    fontSize: 90, fontFace: "Arial Black", color: "121212", bold: true,
    align: "center", valign: "middle", margin: 0,
  });
  // colt logo + tracer (always black on dividers)
  corner(s, "121212");
  // (tracer code)
}
```

> ⚠️ **Always use BLACK section text** even on dark backgrounds. The white chevrons overlay the text — black text reads against both the severity bg AND the white chevrons. White text disappears into the chevrons.

### 5.3 Content slide chrome

Every content slide (not title, not section divider) carries this consistent chrome:

| Element | Position | Style |
|---------|----------|-------|
| Background | Full slide | White `FFFFFF` (or `ECECED` for dim slides) |
| Eyebrow text | x: 0.4", y: 0.22" | 9pt Calibri Bold, **brand teal** `00D7BD`, charSpacing 3 |
| Slide title | x: 0.4", y: 0.44" | 18pt Georgia Bold, **deep teal** `0C544E` |
| "colt" logo | Top-right | 18pt Arial Bold, deep teal (NOT black on content slides) |
| Classification footer | Bottom-left | 7.5pt Calibri, muted gray, all-caps |
| Tracer + page num | Bottom-right | Standard tracer in brand teal |

The split-personality of the teal logo (deep teal on content slides) vs. black logo (title + dividers) is intentional — content slides feel calmer, the brand assertion lives on the cover and section breaks.

```javascript
function pageHeader(slide, eyebrow, title) {
  slide.addText(eyebrow.toUpperCase(), {
    x: 0.4, y: 0.22, w: 8.2, h: 0.22,
    fontSize: 9, fontFace: "Calibri", color: C.teal,
    charSpacing: 3, bold: true, margin: 0,
  });
  slide.addText(title, {
    x: 0.4, y: 0.44, w: 9.2, h: 0.78,
    fontSize: 18, fontFace: "Georgia", color: C.tealDark, bold: true,
    valign: "top", margin: 0,
  });
}
```

---

## 6. Reusable Components

### 6.1 Big-stat card (4-card row)

Used on Asset Inventory / Executive Summary slides. Deep-teal background card with brand-teal number, white label.

| Spec | Value |
|------|-------|
| Card size | 2.10" × 1.10" |
| Gap between cards | 0.20" |
| Background | `0C544E` deep teal |
| Number | 32pt Georgia Bold, brand teal `00D7BD` |
| Label | 9pt Calibri Bold white, charSpacing 2 |
| Sub-caption | 8pt Calibri, brand teal |

### 6.2 Severity badge (inline pill)

Used in finding cards and tables to color-code severity.

| Sev | Background | Foreground |
|-----|------------|------------|
| CRITICAL | `F20C36` red | White |
| HIGH | `FF7900` orange | White |
| MEDIUM | `FFC33C` amber | **Black** `121212` (never white) |
| LOW | `474946` gray | White |

Dimensions: 1.05" × 0.28", 10pt Calibri Bold, charSpacing 2, center-aligned.

### 6.3 Tag pill (remediation track)

Used on finding-card remediation rows. Same dimensions as severity badge.

| Tag | Background | Foreground | Meaning |
|-----|------------|------------|---------|
| **VENDOR** | `FF7900` orange | White | Vendor-direct remediation (patch, reissue) |
| **COLT** | `00D7BD` brand teal | Black | Direct Colt portfolio fit |
| **PSF** | `0C544E` deep teal | White | PSF / Versa solutions architecture |
| **OSS** | `474946` gray | White | Open-source alternative |

### 6.4 Evidence block

Dark mono panel for technical evidence (IP, hostnames, cert details, JARM fingerprints). The single most distinctive content element on a finding card.

| Spec | Value |
|------|-------|
| Background | `121212` brand near-black |
| Left accent strip | 0.04" wide × full height, brand teal `00D7BD` |
| Text | Consolas 7.2pt, `ECECED` light gray |
| Padding | 0.10" left, 0.04" top |
| Max | 9 lines × 50 chars per line |

```javascript
function evidenceBlock(slide, lines, x, y, w, h) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: "121212" }, line: { type: "none" },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.04, h, fill: { color: "00D7BD" }, line: { type: "none" },
  });
  const txt = lines.map((l, i) => ({
    text: l,
    options: {
      breakLine: i < lines.length - 1,
      fontSize: 7.2, fontFace: "Consolas", color: "ECECED",
    },
  }));
  slide.addText(txt, {
    x: x + 0.10, y: y + 0.04, w: w - 0.16, h: h - 0.08,
    valign: "top", margin: 0,
  });
}
```

> ⚠️ **Max 9 lines × 50 chars at 7.2pt.** Anything longer wraps and corrupts the card layout. Test programmatically: `Math.max(...lines.map(l => l.length))` should be ≤ 50.

### 6.5 Tables

Standard table treatment for Colt decks:

| Element | Style |
|---------|-------|
| Header row bg | `0C544E` deep teal |
| Header text | 8.5–9pt Calibri Bold white, charSpacing 2–3 |
| Body row bg | White `FFFFFF` (no zebra striping) |
| Body text | 8.0–8.5pt Calibri, ink `1A1A1A` |
| Border | 0.5pt `D8D6CF` divider gray |
| Row height | 0.24–0.32" depending on density |

For severity cells in finding-index tables, color the cell with the severity background and override text color per the severity-badge spec (6.2).

### 6.6 Callout box (with left accent strip)

Used for "Concentration risk", "Primary anchor", or other inline emphasis blocks.

| Spec | Value |
|------|-------|
| Background | `ECECED` light gray |
| Left accent | 0.06–0.08" wide × full height in brand teal `00D7BD` (or severity color for warnings) |
| Padding | 0.15" left of content |
| Title | Calibri Bold, deep teal `0C544E` |
| Body | Calibri regular, ink `1A1A1A` |

---

## 7. Standard Slide Sequence (Findings Deck)

For Shodan-findings decks, this is the canonical sequence. Section dividers are non-negotiable — without them, the C/H/M/L structure isn't visually unmistakable.

| Position | Slide | Type |
|----------|-------|------|
| 1 | Title | Teal title slide |
| 2 | Executive Summary | Content (verdict + severity counts + headlines) |
| 3 | Methodology | Content (sources + exclusions + classification framework) |
| 4 | Asset Inventory | Content (4-card stats + tables) |
| 5 | Findings Index | Content (table of all findings) |
| **6** | **CRITICAL.** divider | Section divider |
| 7–(N) | Critical finding cards | Content (one per finding) |
| **N+1** | **HIGH.** divider | Section divider |
| ... | High finding cards | Content |
| ... | **MEDIUM.** divider | Section divider |
| ... | Medium finding cards | Content |
| ... | **LOW.** divider | Section divider |
| ... | Low findings (2×2 combined) | Content |
| ... | Mitigation Mapping | Content (findings × portfolio matrix) |
| ... | Caveats & Confidence | Content |
| Last | Next Steps / 7-Day Horizon | Closer slide (deep teal bg, white chevrons or just closing chrome) |

---

## 8. The Closer Slide

Mirrors the title slide's energy but in deep teal. Used as the final action-oriented slide.

| Element | Position | Style |
|---------|----------|-------|
| Background | Full slide | Deep teal `0C544E` |
| Eyebrow | x: 0.4", y: 0.40" | 11pt Calibri Bold, brand teal `00D7BD`, charSpacing 3 |
| Title | x: 0.4", y: 0.70" | 24pt Georgia Bold white |
| "colt" logo | Top-right | White, 14pt Arial Bold |
| Action rows | y: 1.65" + 0.85" each | Dark cards with teal accent strips |
| Owner pill | x: 0.55" within each card | Brand teal bg, black text |

---

## 9. Build & QA Loop

```bash
# Setup
mkdir -p /home/claude/<customer>
cd /home/claude/<customer>
export NODE_PATH=/home/claude/.npm-global/lib/node_modules

# Build
node build_deck.js

# Render to PDF then to JPGs for visual QA
python3 /mnt/skills/public/pptx/scripts/office/soffice.py \
  --headless --convert-to pdf <Customer>_Shodan_Findings_Internal.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 100 <Customer>_Shodan_Findings_Internal.pdf slide

# Or get a thumbnail grid (3 cols x 4 rows per grid)
python3 /mnt/skills/public/pptx/scripts/thumbnail.py \
  <Customer>_Shodan_Findings_Internal.pptx
```

### QA checklist — look for these in the rendered slides

1. **Title-wrap collisions** — content title should fit in 2 lines max
2. **Evidence block overflow** — text bleeding past the dark rectangle
3. **WHAT WE OBSERVED overflow** — body text bleeding into the EVIDENCE region
4. **WHY IT MATTERS bleed** — text running into the footer
5. **Pill collisions** — overlapping pills or pills colliding with title
6. **Mitigation matrix overflow** — bottom row pushed below the footer line
7. **Section divider text invisibility** — always BLACK text on dividers (white disappears into chevrons)
8. **Logo placement** — always top-right at x: 9.05–9.20", never moves

### Iteration budget

First render + **one** targeted fix pass = total budget. Do not iterate on sub-pixel adjustments. Cosmetic perfection is the enemy of shipping the deck.

---

## 10. Common Pitfalls

1. **`#`-prefixed hex codes corrupt the file.** Use raw 6-char hex: `"FF0000"` not `"#FF0000"`.
2. **8-char hex for transparency corrupts the file.** Use `opacity: 0.12` on the shape/text instead.
3. **Reusing options objects mutates them.** Especially `shadow` — pptxgenjs mutates in place. Use factory functions: `const makeShadow = () => ({ ... })`.
4. **Slide masters are not worth the complexity.** Define helpers (`pageHeader`, `footer`, `findingCard`, `sectionDivider`) as plain functions and call them per slide.
5. **LibreOffice renders table rows ~10% taller than `rowH` suggests.** Budget for this; if a table has 13 rows × 0.27" you'll get overflow. Drop a row or reduce `rowH` further.
6. **White text on section dividers disappears into white chevrons.** Always black.
7. **Section divider word needs a trailing period** — `"CRITICAL."` not `"CRITICAL"`. Matches the template's "THE EXTRAORDINARY EVERYDAY." treatment.
8. **The yellow accent on the title is a SQUARE, not a circle.** The template uses sharp-cornered amber rectangles, never ovals/dots.
9. **The "colt" logo is bold Arial, never italic, never serif.** Earlier drafts used Georgia italic — that's wrong. Always Arial Bold.
10. **Don't put the colt logo on section dividers in the wrong color.** Always black `121212` on section dividers, regardless of the severity bg.

---

## 11. Quick-Reference Code Block

The minimum viable Colt-branded deck skeleton:

```javascript
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";  // 10 x 5.625"
pres.author = "Colt Sales Engineering";

// Palette (§1.4 — verbatim)
const C = { teal: "00D7BD", tealMid: "00A49A", tealDark: "0C544E",
            black: "121212", dark: "474946", light: "ECECED",
            crit: "F20C36", high: "FF7900", med: "FFC33C", low: "474946",
            ink: "1A1A1A", inkMuted: "5B6470", divider: "D8D6CF",
            white: "FFFFFF", evidenceBg: "121212", evidenceInk: "ECECED" };

const FH = "Georgia", FB = "Calibri", FM = "Consolas";

let pageNum = 0;
const TOTAL = /* fill in based on §7 */;

// Helpers — corner(), bigChevrons(), chevronTracer(), pageHeader(),
// sectionDivider(), evidenceBlock(), findingCard(), footer()
// (Copy from §3–§6 above.)

// Slide 1 — title (§5.1)
// Slide 2 — exec summary
// Slide 3 — methodology
// Slide 4 — asset inventory
// Slide 5 — findings index
// SECTION DIVIDER — CRITICAL
// ... critical findings
// SECTION DIVIDER — HIGH
// ... high findings
// SECTION DIVIDER — MEDIUM
// ... medium findings
// SECTION DIVIDER — LOW
// ... low findings (combined 2x2)
// Mitigation mapping · Caveats · Next Steps

pres.writeFile({ fileName: `/home/claude/${customer}/${customer}_Shodan_Findings_Internal.pptx` });
```

---

## 12. Customer-Specific Variations

The palette and chrome do not change across customers. What can be tailored:

- **Title-slide hero text** — always the customer name in Arial Black + period + yellow square accent
- **Metadata strip content** — ASN list adjusts to the engagement; "Prepared by" stays consistent
- **Frameworks cited in methodology** — match the customer's regulator (BSI/BAIT for German banks, FINMA for Swiss, ENISA/NIS2 for EU industrial, FCA/PRA for UK financial, HKMA for HK)
- **Reference decks**: Commerzbank (07 May 2026), Innopolis (25 May 2026), Wempe Group (26 May 2026), SGS whitepaper (01 May 2026)

> **Never** modify the brand palette, chevron motif, section-divider pattern, or logo treatment per customer. These are the constants.

---

*Colt Sales Engineering · Internal design reference · v1.0 · 26 May 2026*
*Companion to `COLT_SHODAN_DECK_METHODOLOGY.md`*
*Palette sourced verbatim from `Colt_Template_26.potx` theme1.xml*
