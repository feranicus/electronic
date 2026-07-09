#!/usr/bin/env node
/* Colt-branded Shodan Findings deck generator (data-driven).
   Layout ported verbatim from the hand-authored VIP builder (build_ubs_findings.js):
   palette C{}, fonts FH/FB/FM/FD/FA, corner()/bigChevrons()/tracer()/footer()/pageHeader(),
   sevBadge()/pill()/evidenceBlock()/content()/drawTable(), the title slide,
   the findings-index table, and the per-finding WHAT / EVIDENCE / WHY / REMEDIATION card.

   Usage: node build_findings_deck.js <findings.json> [out.pptx]

   findings.json schema (kept consuming, degrades gracefully if fields missing):
   { target:{company,audience,date,scope,exec_summary?},
     summary:{unique_ips,asns,dropped_false_positives,critical,high,medium,low,...},
     findings:[ {sev:"CRITICAL"|"HIGH"|"MEDIUM"|"LOW", id, title, what:[], evidence:[], why:[], rem:[], refs:[]} ] }

   NB: source is kept pure-ASCII; typographic glyphs (em-dash, middot, bullet) are
   emitted via \u escapes so the file survives cross-platform writes intact. */

const fs = require("fs");
const pptxgen = require("pptxgenjs");

// typographic glyphs (avoid raw multibyte literals in source)
const EMDASH = "—";     // --
const MIDDOT = "·";     // middot
const BULLET = "•";     // bullet char
const RAQUO = "»";      // >>

// ---------- input ----------
const DATA = process.argv[2] || "findings.json";
let d = {};
try { d = JSON.parse(fs.readFileSync(DATA, "utf8")); }
catch (e) { console.error("Cannot read/parse " + DATA + ": " + e.message); process.exit(1); }
const t = d.target || {};
const sum = d.summary || {};
const findings = Array.isArray(d.findings) ? d.findings : [];
const strengths = Array.isArray(t.strengths) ? t.strengths.filter(x => x != null).map(String).filter(x => x.trim()) : [];
const mitigation = Array.isArray(t.colt_mitigation) ? t.colt_mitigation.filter(x => x && typeof x === "object") : [];
const OUT = process.argv[3] ||
  "./" + (t.company || "Target").replace(/[^A-Za-z0-9]+/g, "_") + "_Shodan_Findings.pptx";

// loose-JSON coercion helpers
const asLines = v => Array.isArray(v) ? v.filter(x => x != null).map(String)
  : (v == null || v === "" ? [] : [String(v)]);
const asText = v => Array.isArray(v) ? v.filter(x => x != null).map(String).join(" ")
  : (v == null ? "" : String(v));
const num = v => (v == null || v === "" || Number.isNaN(Number(v))) ? 0 : Number(v);

// ---------- presentation ----------
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625"
pres.author = "Colt Sales Engineering";
pres.title = (t.company || "Target") + " " + EMDASH + " External Attack Surface Assessment";

// ---- Palette (COLT_DESIGN_SYSTEM.md 1.4) -- copied verbatim from VIP builder ----
const C = {
  teal: "00D7BD", tealMid: "00A49A", tealDark: "0C544E",
  black: "121212", dark: "474946", light: "ECECED",
  crit: "F20C36", high: "FF7900", med: "FFC33C", low: "474946",
  ink: "1A1A1A", inkMuted: "5B6470", divider: "D8D6CF",
  white: "FFFFFF", evidenceBg: "121212", evidenceInk: "ECECED",
  green: "10B981",
};
const FH = "Georgia", FB = "Calibri", FM = "Consolas", FD = "Arial Black", FA = "Arial";

let pageNum = 0;

// TOTAL page count (computed up-front so the tracer reads N / TOTAL correctly):
// 1 title + 1 exec + 1 findings-index + (per severity present: 1 divider + N cards)
const order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const bySev = Object.fromEntries(order.map(sev =>
  [sev, findings.filter(f => (f.sev || "").toUpperCase() === sev)]));
let TOTAL = 3;
for (const sev of order) if (bySev[sev].length) TOTAL += 1 + bySev[sev].length;
if (strengths.length) TOTAL += 1;
if (mitigation.length) TOTAL += 1;

// ---------- helpers (copied from VIP builder) ----------
function corner(slide, color = C.black, size = 18) {
  slide.addText("colt", { x: 9.05, y: 0.18, w: 0.85, h: 0.32,
    fontSize: size, fontFace: FA, color, bold: true, align: "right", margin: 0 });
}
function bigChevrons(slide, opts = {}) {
  const x = opts.x ?? 0.5, w = opts.w ?? 9.0, yStart = opts.yStart ?? 0.20;
  const triH = opts.triH ?? 1.55, gap = opts.gap ?? 0.30, color = opts.color || C.white;
  for (let i = 0; i < 3; i++) {
    slide.addShape(pres.shapes.ISOSCELES_TRIANGLE, {
      x, y: yStart + i * (triH + gap), w, h: triH, fill: { color }, line: { type: "none" } });
  }
}
function tracer(slide, color = C.tealDark) {
  for (let i = 0; i < 3; i++) {
    slide.addShape(pres.shapes.RIGHT_TRIANGLE, { x: 8.30 + i * 0.14, y: 5.34, w: 0.11, h: 0.16,
      fill: { color }, line: { type: "none" }, rotate: 90 });
  }
  slide.addText(RAQUO + RAQUO + " " + pageNum + "/" + TOTAL, { x: 8.62, y: 5.28, w: 1.23, h: 0.28,
    fontSize: 9, fontFace: FB, color, bold: true, align: "right", valign: "middle", margin: 0 });
}
function footer(slide) {
  slide.addText("INTERNAL " + EMDASH + " COLT CONFIDENTIAL " + MIDDOT + " NOT FOR EXTERNAL DISTRIBUTION", {
    x: 0.4, y: 5.32, w: 6.4, h: 0.22, fontSize: 7.5, fontFace: FB, color: C.inkMuted,
    charSpacing: 2, valign: "middle", margin: 0 });
}
function pageHeader(slide, eyebrow, title) {
  slide.addText(String(eyebrow || "").toUpperCase(), { x: 0.4, y: 0.22, w: 8.4, h: 0.22,
    fontSize: 9, fontFace: FB, color: C.teal, charSpacing: 3, bold: true, margin: 0 });
  slide.addText(String(title || ""), { x: 0.4, y: 0.44, w: 8.5, h: 0.80,
    fontSize: 18, fontFace: FH, color: C.tealDark, bold: true, valign: "top", margin: 0 });
  corner(slide, C.tealDark, 16);
}
function sevBadge(slide, sev, x, y, w = 1.05) {
  const map = { CRITICAL: [C.crit, C.white], HIGH: [C.high, C.white],
    MEDIUM: [C.med, C.black], LOW: [C.low, C.white] };
  const [bg, fg] = map[sev] || map.LOW;
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.28, fill: { color: bg }, line: { type: "none" } });
  slide.addText(sev, { x, y, w, h: 0.28, fontSize: 10, fontFace: FB, color: fg, bold: true,
    align: "center", valign: "middle", charSpacing: 2, margin: 0 });
}
function pill(slide, text, x, y, w, bg, fg) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.25, fill: { color: bg }, line: { type: "none" } });
  slide.addText(text, { x, y, w, h: 0.25, fontSize: 8, fontFace: FB, color: fg, bold: true,
    align: "center", valign: "middle", charSpacing: 1, margin: 0 });
}
function evidenceBlock(slide, lines, x, y, w, h) {
  lines = (lines && lines.length) ? lines : ["(no evidence recorded)"];
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.evidenceBg }, line: { type: "none" } });
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.04, h, fill: { color: C.teal }, line: { type: "none" } });
  slide.addText(lines.map((l, i) => ({ text: l, options: {
    breakLine: i < lines.length - 1, fontSize: 7.2, fontFace: FM, color: C.evidenceInk } })),
    { x: x + 0.12, y: y + 0.05, w: w - 0.18, h: h - 0.10, valign: "top", margin: 0 });
}
function contentBg(slide) { slide.background = { color: C.white }; }

// content() factory: a blank branded content slide
function content(eyebrow, title) {
  pageNum++;
  const s = pres.addSlide();
  contentBg(s);
  pageHeader(s, eyebrow, title);
  return s;
}

// drawTable(): branded table with teal-dark header + divider borders
function drawTable(slide, rows, opts) {
  slide.addTable(rows, Object.assign({
    border: { type: "solid", color: C.divider, pt: 0.5 },
    fontFace: FB, color: C.ink, valign: "middle", align: "left",
  }, opts));
}

// ===================================================================
// SLIDE 1 -- TITLE  (HUGE company name in Arial Black, eyebrow, 3 white
//   chevrons bleeding off the right edge, `colt` wordmark, gold accent
//   square, 4-field footer strip PREPARED / FOR / DATA SOURCE / STATUS)
// ===================================================================
(function title() {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.teal };
  bigChevrons(s, { x: 5.95, w: 5.0, yStart: 0.05, triH: 1.95, gap: 0.06, color: C.white });
  corner(s, C.black, 22);
  s.addText("EXTERNAL ATTACK SURFACE ASSESSMENT", { x: 0.5, y: 1.20, w: 7.5, h: 0.3,
    fontSize: 11, fontFace: FA, color: C.black, bold: true, charSpacing: 3, margin: 0 });
  s.addText(t.company || "Target", { x: 0.46, y: 1.62, w: 8, h: 1.05,
    fontSize: 70, fontFace: FD, color: C.black, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.54, y: 2.78, w: 0.22, h: 0.22,
    fill: { color: C.med }, line: { type: "none" } });
  s.addText("Shodan external reconnaissance " + MIDDOT + " Critical " + MIDDOT + " High " + MIDDOT + " Medium " + MIDDOT + " Low",
    { x: 0.9, y: 2.74, w: 8.2, h: 0.3, fontSize: 13, fontFace: FA, color: C.black, bold: true, margin: 0 });
  s.addText(t.date || new Date().toISOString().slice(0, 10), { x: 0.5, y: 3.95, w: 4, h: 0.3,
    fontSize: 14, fontFace: FA, color: C.black, bold: true, margin: 0 });
  // 4-field footer metadata strip
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.75, w: 10, h: 0.875,
    fill: { color: C.black }, line: { type: "none" } });
  const meta = [
    ["PREPARED", "Colt Sales Engineering"],
    ["FOR", t.audience || "Internal " + EMDASH + " Colt Sales Engineering"],
    ["DATA SOURCE", t.scope || "Shodan host-record export"],
    ["STATUS", "INTERNAL " + EMDASH + " CONFIDENTIAL"],
  ];
  let mx = 0.5;
  meta.forEach(([k, v], i) => {
    const w = (i === 1 || i === 2) ? 3.1 : 1.6;
    s.addText([{ text: k + "\n", options: { fontSize: 8, color: C.teal, bold: true, charSpacing: 2 } },
      { text: String(v), options: { fontSize: 8.5, color: C.white } }],
      { x: mx, y: 4.83, w, h: 0.72, fontFace: FB, valign: "middle", margin: 0 });
    mx += w + 0.05;
  });
  for (let i = 0; i < 3; i++) s.addShape(pres.shapes.RIGHT_TRIANGLE,
    { x: 8.30 + i * 0.14, y: 4.40, w: 0.11, h: 0.16, fill: { color: C.black }, line: { type: "none" }, rotate: 90 });
  s.addText("1 / " + TOTAL, { x: 8.80, y: 4.34, w: 1.05, h: 0.28,
    fontSize: 9, fontFace: FB, color: C.black, bold: true, align: "right", margin: 0 });
})();

// ===================================================================
// SLIDE 2 -- EXECUTIVE SUMMARY  (severity count cards + exec_summary paragraph)
// ===================================================================
(function exec() {
  const nCrit = num(sum.critical), nHigh = num(sum.high),
    nMed = num(sum.medium), nLow = num(sum.low);
  const totalFindings = (nCrit + nHigh + nMed + nLow) || findings.length;
  const s = content("EXECUTIVE SUMMARY", "Exposure at a glance");

  const para = t.exec_summary && String(t.exec_summary).trim()
    ? String(t.exec_summary).trim()
    : "Passive external reconnaissance of " + (t.company || "the target") + " surfaced "
      + totalFindings + " finding" + (totalFindings === 1 ? "" : "s")
      + " across the internet-facing estate. All items are observed via Shodan (no active scanning); each is mapped to remediation and the relevant Colt service.";
  s.addText(para, { x: 0.4, y: 1.32, w: 9.3, h: 1.05, fontSize: 10, fontFace: FB,
    color: C.ink, valign: "top", margin: 0 });

  const cards = [[String(nCrit), "CRITICAL", C.crit], [String(nHigh), "HIGH", C.high],
    [String(nMed), "MEDIUM", C.med], [String(nLow), "LOW", C.low]];
  let cx = 0.4;
  cards.forEach(([n, l, col]) => {
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 2.55, w: 2.18, h: 1.02, fill: { color: C.tealDark }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 2.55, w: 2.18, h: 0.08, fill: { color: col }, line: { type: "none" } });
    s.addText(n, { x: cx, y: 2.66, w: 2.18, h: 0.62, fontSize: 34, fontFace: FH,
      color: col, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(l, { x: cx, y: 3.24, w: 2.18, h: 0.28, fontSize: 9, fontFace: FB, color: C.white,
      bold: true, align: "center", charSpacing: 2, margin: 0 });
    cx += 2.38;
  });

  const stats = [
    ["unique IPs", sum.unique_ips], ["ASNs", sum.asns],
    ["countries", sum.countries], ["dropped FPs", sum.dropped_false_positives],
  ];
  let sx = 0.4;
  stats.forEach(([l, n]) => {
    s.addText(n == null ? EMDASH : String(n), { x: sx, y: 3.80, w: 2.18, h: 0.46,
      fontSize: 22, fontFace: FH, bold: true, color: C.ink, align: "center", margin: 0 });
    s.addText(l.toUpperCase(), { x: sx, y: 4.24, w: 2.18, h: 0.24, fontSize: 8, fontFace: FB,
      color: C.inkMuted, align: "center", charSpacing: 1, margin: 0 });
    sx += 2.38;
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.66, w: 9.3, h: 0.52, fill: { color: C.light }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.66, w: 0.07, h: 0.52, fill: { color: C.teal }, line: { type: "none" } });
  s.addText([{ text: "Passive only.  ", options: { bold: true, color: C.tealDark } },
    { text: "Every finding is observed from public data via Shodan " + EMDASH + " visible is not vulnerable. Each maps to a remediation and the relevant Colt service.", options: { color: C.ink } }],
    { x: 0.58, y: 4.70, w: 9.0, h: 0.44, fontSize: 8.6, fontFace: FB, valign: "middle", margin: 0 });
  footer(s); tracer(s);
})();

// ===================================================================
// SLIDE 3 -- FINDINGS INDEX  (serif count header + severity-badged table,
//   columns [SEV | ID | FINDING | EVIDENCE ANCHOR], zebra rows)
// ===================================================================
(function index() {
  const nCrit = num(sum.critical), nHigh = num(sum.high),
    nMed = num(sum.medium), nLow = num(sum.low);
  const totalFindings = (nCrit + nHigh + nMed + nLow) || findings.length;
  const hdr = totalFindings + " findings " + MIDDOT + " " + nCrit + " critical " + MIDDOT + " "
    + nHigh + " high " + MIDDOT + " " + nMed + " medium " + MIDDOT + " " + nLow + " low";
  const s = content("FINDINGS INDEX", hdr);

  const sevFill = { CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, LOW: C.low };
  const sevFg = { CRITICAL: C.white, HIGH: C.white, MEDIUM: C.black, LOW: C.white };

  const rows = [[
    { text: "SEV", options: { fill: C.tealDark, color: C.white, bold: true } },
    { text: "ID", options: { fill: C.tealDark, color: C.white, bold: true } },
    { text: "FINDING", options: { fill: C.tealDark, color: C.white, bold: true } },
    { text: "EVIDENCE ANCHOR", options: { fill: C.tealDark, color: C.white, bold: true } },
  ]];

  const ordered = order.flatMap(sev => bySev[sev]);
  ordered.forEach((f, i) => {
    const sev = (f.sev || "LOW").toUpperCase();
    const ev = asLines(f.evidence);
    const anchor = ev.length ? ev[0] : EMDASH;
    const zebra = i % 2 === 1 ? C.light : C.white;
    rows.push([
      { text: sev, options: { fill: sevFill[sev] || C.low, color: sevFg[sev] || C.white, bold: true, fontSize: 7.2, align: "center" } },
      { text: String(f.id || ""), options: { fill: zebra, bold: true, fontSize: 7.6 } },
      { text: String(f.title || "Finding"), options: { fill: zebra, fontSize: 7.6 } },
      { text: anchor, options: { fill: zebra, fontSize: 7.2, fontFace: FM, color: C.inkMuted } },
    ]);
  });
  if (!ordered.length) {
    rows.push([{ text: EMDASH, options: { align: "center" } },
      { text: "", options: {} },
      { text: "No findings recorded", options: {} },
      { text: EMDASH, options: {} }]);
  }

  const rowH = Math.max(0.16, Math.min(0.30, 3.9 / Math.max(rows.length, 1)));
  drawTable(s, rows, { x: 0.4, y: 1.30, w: 9.3, colW: [0.95, 0.55, 5.55, 2.25], rowH });
  footer(s); tracer(s);
})();

// ===================================================================
// SECTION DIVIDER  (big Arial-Black label + white chevrons)
// ===================================================================
function sectionDivider(label, bgColor) {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: bgColor };
  bigChevrons(s, { x: 0.5, w: 9.0, yStart: 0.10, triH: 1.55, gap: 0.30, color: C.white });
  s.addText(label + ".", { x: 0, y: 1.85, w: 10, h: 1.80, fontSize: 88, fontFace: FD,
    color: C.black, bold: true, align: "center", valign: "middle", margin: 0 });
  corner(s, C.black, 18);
  for (let i = 0; i < 3; i++) s.addShape(pres.shapes.RIGHT_TRIANGLE,
    { x: 8.30 + i * 0.14, y: 5.34, w: 0.11, h: 0.16, fill: { color: C.black }, line: { type: "none" }, rotate: 90 });
  s.addText(RAQUO + RAQUO + " " + pageNum + "/" + TOTAL, { x: 8.62, y: 5.28, w: 1.23, h: 0.28,
    fontSize: 9, fontFace: FB, color: C.black, bold: true, align: "right", valign: "middle", margin: 0 });
}

// ===================================================================
// FINDING CARD  (WHAT / EVIDENCE dark panel / WHY / REMEDIATION)
// ===================================================================
function findingCard(f) {
  const sev = (f.sev || "LOW").toUpperCase();
  const accent = { CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, LOW: C.low }[sev] || C.low;
  const eyebrow = (sev + "  " + MIDDOT + "  FINDING " + (f.id || "")).trim();
  const s = content(eyebrow, f.title || "Finding");

  sevBadge(s, sev, 0.4, 1.28);
  s.addText(String(f.id || "").toUpperCase(), { x: 1.55, y: 1.28, w: 4.4, h: 0.28,
    fontSize: 8.5, fontFace: FB, color: C.inkMuted, charSpacing: 2, bold: true, valign: "middle", margin: 0 });

  const refs = asLines(f.refs).slice(0, 2);
  let px = 9.7;
  refs.slice().reverse().forEach(r => { px -= 1.62; pill(s, r, px, 1.30, 1.55, C.dark, C.white); });

  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.70, w: 0.08, h: 0.24, fill: { color: accent }, line: { type: "none" } });
  s.addText("FINDING", { x: 0.56, y: 1.70, w: 2, h: 0.24, fontSize: 10, fontFace: FB,
    color: C.ink, bold: true, charSpacing: 2, valign: "middle", margin: 0 });

  s.addText("WHAT WE OBSERVED", { x: 0.4, y: 2.00, w: 4.5, h: 0.18, fontSize: 8.5, fontFace: FB,
    color: C.tealDark, bold: true, charSpacing: 2, margin: 0 });
  const what = asLines(f.what);
  s.addText((what.length ? what : [EMDASH]).map((x, i) => ({ text: x,
    options: { breakLine: i < what.length - 1, fontSize: 8.3, fontFace: FB, color: C.ink,
      bullet: { code: "2022", indent: 10 } } })),
    { x: 0.4, y: 2.18, w: 4.55, h: 1.05, valign: "top", margin: 0, paraSpaceAfter: 2 });

  s.addText("EVIDENCE", { x: 0.4, y: 3.26, w: 4.5, h: 0.18, fontSize: 8.5, fontFace: FB,
    color: C.tealDark, bold: true, charSpacing: 2, margin: 0 });
  evidenceBlock(s, asLines(f.evidence), 0.4, 3.46, 4.55, 1.14);

  s.addText("WHY IT MATTERS", { x: 0.4, y: 4.64, w: 4.5, h: 0.18, fontSize: 8.5, fontFace: FB,
    color: C.tealDark, bold: true, charSpacing: 2, margin: 0 });
  s.addText(asText(f.why) || EMDASH, { x: 0.4, y: 4.82, w: 4.55, h: 0.46,
    fontSize: 8.0, fontFace: FB, color: C.ink, valign: "top", margin: 0 });

  s.addShape(pres.shapes.RECTANGLE, { x: 5.05, y: 1.70, w: 0.08, h: 0.24, fill: { color: C.teal }, line: { type: "none" } });
  s.addText("REMEDIATION  &  COLT FIT", { x: 5.21, y: 1.70, w: 4.5, h: 0.24, fontSize: 10, fontFace: FB,
    color: C.ink, bold: true, charSpacing: 2, valign: "middle", margin: 0 });

  const rem = asLines(f.rem);
  const startY = 2.06, rowH = 0.62;
  (rem.length ? rem : [EMDASH]).slice(0, 5).forEach((r, i) => {
    const y = startY + i * rowH;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.05, y: y + 0.03, w: 0.30, h: 0.22, fill: { color: C.teal }, line: { type: "none" } });
    s.addText(String(i + 1), { x: 5.05, y: y + 0.03, w: 0.30, h: 0.22, fontSize: 9, fontFace: FB,
      bold: true, color: C.black, align: "center", valign: "middle", margin: 0 });
    s.addText(r, { x: 5.45, y, w: 4.25, h: rowH - 0.06, fontSize: 9.0, fontFace: FB,
      color: C.ink, valign: "middle", margin: 0 });
  });

  footer(s); tracer(s);
}

// ---------- emit section dividers + finding cards ----------
for (const sev of order) {
  const items = bySev[sev];
  if (!items.length) continue;
  const bg = { CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, LOW: C.low }[sev];
  sectionDivider(sev, bg);
  items.forEach(f => findingCard(f));
}

// ===================================================================
// STRENGTHS -- "WHAT NOT TO TOUCH"  (green-checked cards; mirrors finding cards)
// ===================================================================
function strengthsSlide() {
  const s = content("STRENGTHS " + MIDDOT + " WHAT NOT TO TOUCH",
    "Things the customer already does right " + EMDASH + " respect them in the pursuit");

  const items = strengths.slice(0, 5);
  const cardH = 0.64, gap = 0.14, startY = 1.42;
  items.forEach((txt, i) => {
    const y = startY + i * (cardH + gap);
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 9.3, h: cardH, fill: { color: C.light }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 0.07, h: cardH, fill: { color: C.green }, line: { type: "none" } });
    // green check disc
    s.addShape(pres.shapes.OVAL, { x: 0.62, y: y + (cardH - 0.34) / 2, w: 0.34, h: 0.34, fill: { color: C.green }, line: { type: "none" } });
    s.addText("✓", { x: 0.62, y: y + (cardH - 0.34) / 2, w: 0.34, h: 0.34, fontSize: 15, fontFace: FB,
      color: C.white, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(String(txt), { x: 1.12, y, w: 8.4, h: cardH, fontSize: 10.5, fontFace: FB,
      color: C.ink, valign: "middle", margin: 0 });
  });

  footer(s); tracer(s);
}

// ===================================================================
// MITIGATION MAPPING  (findings x Colt portfolio coverage table)
// ===================================================================
function mitigationSlide() {
  const s = content("MITIGATION MAPPING", "Findings " + MIDDOT + " Colt portfolio coverage");

  const rows = [[
    { text: "ID", options: { fill: C.tealDark, color: C.white, bold: true } },
    { text: "FINDING", options: { fill: C.tealDark, color: C.white, bold: true } },
    { text: "COLT PRODUCT / SERVICE", options: { fill: C.tealDark, color: C.white, bold: true } },
    { text: "PSF", options: { fill: C.tealDark, color: C.white, bold: true } },
    { text: "OPEN SOURCE", options: { fill: C.tealDark, color: C.white, bold: true } },
  ]];

  const items = mitigation.slice(0, 12);
  items.forEach((m, i) => {
    const zebra = i % 2 === 1 ? C.light : C.white;
    const cell = v => (v == null || String(v).trim() === "") ? EMDASH : String(v);
    rows.push([
      { text: cell(m.id), options: { fill: zebra, bold: true, fontSize: 7.6 } },
      { text: cell(m.finding), options: { fill: zebra, fontSize: 7.6 } },
      { text: cell(m.colt), options: { fill: zebra, fontSize: 7.6, color: C.tealDark, bold: true } },
      { text: cell(m.psf), options: { fill: zebra, fontSize: 7.2, color: C.inkMuted } },
      { text: cell(m.oss), options: { fill: zebra, fontSize: 7.2, fontFace: FM, color: C.inkMuted } },
    ]);
  });
  if (!items.length) {
    rows.push([{ text: EMDASH, options: { align: "center" } },
      { text: "No mitigation mapping recorded", options: {} },
      { text: EMDASH, options: {} }, { text: EMDASH, options: {} }, { text: EMDASH, options: {} }]);
  }

  const rowH = Math.max(0.20, Math.min(0.34, 3.9 / Math.max(rows.length, 1)));
  drawTable(s, rows, { x: 0.4, y: 1.30, w: 9.3, colW: [0.55, 2.85, 3.05, 1.60, 1.25], rowH });
  footer(s); tracer(s);
}

// ---------- emit optional strengths + mitigation slides ----------
if (strengths.length) strengthsSlide();
if (mitigation.length) mitigationSlide();

// ---------- write ----------
pres.writeFile({ fileName: OUT })
  .then(fn => console.log("WROTE " + fn + "  pages: " + pageNum))
  .catch(e => { console.error(e); process.exit(1); });
