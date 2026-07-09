#!/usr/bin/env node
/* Colt-branded C-BIQ (Cyber Business-Impact Quantification) deck generator.
   Layout ported VERBATIM from the hand-authored VIP builders
   (build_rosneft_de_cbiq.js / build_ubs_cbiq.js): palette C{}, fonts
   FH/FB/FM/FD/FA, corner()/bigChevrons()/tracer()/footer()/pageHeader(),
   the TITLE slide, section dividers, the FAIR-maths slide, the loss-exceedance
   LINE chart (before/after), the Monte-Carlo distribution bar, the 7-bucket
   bar, the ROSI cost-benefit slide, the EVERY-FINDING-PRICED table with
   coloured tier badges, the worked-example CRIT slide and a closer.

   Usage: node build_cbiq_deck.js <cbiq.json> [out.pptx]

   Derived fields computed when absent:
     lef = tef*vuln ; PERT(min,likely,max) = (min+4*likely+max)/6 ;
     meanLM = Sigma PERT(bucket) ; aleMid = lef*meanLM ;
     aleRange defaults to [aleMid*0.4, aleMid*2.6] ; codRange = aleRange/12 ;
     rosiPct = (aleMid - aleAfter - controlCost)/controlCost*100 .

   NB: source is pure-ASCII; typographic glyphs are emitted via \u escapes so
   the file survives cross-platform writes intact. Hex colours WITHOUT '#'. */

const fs = require("fs");
const pptxgen = require("pptxgenjs");

// typographic glyphs (pure-ASCII source, emitted via \u escapes)
const EMDASH = "—";   // em dash
const MIDDOT = "·";   // middot
const RAQUO  = "»";   // >>
const TIMES  = "×";   // times
const SIGMA  = "Σ";   // Sigma
const APPROX = "≈";   // approx
const RARR   = "→";   // right arrow

// ---------- input ----------
const DATA = process.argv[2] || "cbiq.json";
let d = {};
try { d = JSON.parse(fs.readFileSync(DATA, "utf8")); }
catch (e) { console.error("Cannot read/parse " + DATA + ": " + e.message); process.exit(1); }

const cust = d.customer || "Target";
const cur = d.currency || { code: "EUR", symbol: "€", word: "euros" };
const SYM = cur.symbol || "€";
const WORD = (cur.word || "euros");
const OUT = process.argv[3] ||
  "./" + String(cust).replace(/[^A-Za-z0-9]+/g, "_") + "_CBIQ_Business_Impact.pptx";

// ---------- palette / fonts (copied VERBATIM from the VIP builder) ----------
const C = {
  teal: "00D7BD", tealMid: "00A49A", tealDark: "0C544E",
  black: "121212", dark: "474946", light: "ECECED",
  crit: "F20C36", high: "FF7900", med: "FFC33C", low: "474946",
  ink: "1A1A1A", inkMuted: "5B6470", divider: "D8D6CF",
  white: "FFFFFF", evBg: "0C544E", evInk: "ECECED",
  green: "1E9E6A", gold: "C9A227",
};
const FH = "Georgia", FB = "Calibri", FM = "Consolas", FD = "Arial Black", FA = "Arial";
const TIER = { CRIT: [C.crit, C.white], HIGH: [C.high, C.white], MED: [C.med, C.black], LOW: [C.low, C.white] };

const CLASS = String(d.classification || "INTERNAL " + EMDASH + " COLT CONFIDENTIAL " + MIDDOT + " NOT FOR EXTERNAL DISTRIBUTION").toUpperCase();
const CAVEAT = "ILLUSTRATIVE MODEL OUTPUT " + EMDASH + " not a guarantee of loss";
const FOOT = CLASS + " " + MIDDOT + " ILLUSTRATIVE MODEL OUTPUT (" + (cur.code || "EUR") + ")";

// ---------- presentation ----------
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625"
pres.author = "Colt Sales Engineering";
pres.title = cust + " " + EMDASH + " C-BIQ Business Impact Quantification";

let pageNum = 0;
const TOTAL = 13;
const R = () => pres.shapes.RECTANGLE;

// ---------- loose-JSON coercion / number helpers ----------
const num = v => (v == null || v === "" || Number.isNaN(Number(v))) ? 0 : Number(v);
const PERT = a => (Array.isArray(a) && a.length === 3) ? (num(a[0]) + 4 * num(a[1]) + num(a[2])) / 6 : 0;

function money(n) {
  if (n == null || isNaN(n)) return EMDASH;
  const abs = Math.abs(n);
  if (abs >= 1e9) return SYM + (n / 1e9).toFixed(abs >= 1e10 ? 0 : 1) + "bn";
  if (abs >= 1e6) return SYM + (n / 1e6).toFixed(abs >= 1e7 ? 0 : 1) + "M";
  if (abs >= 1e3) return SYM + (n / 1e3).toFixed(0) + "k";
  return SYM + Math.round(n);
}
function moneyRange(r) {
  return (Array.isArray(r) && r.length === 2) ? money(r[0]) + EMDASH + money(r[1]) : EMDASH;
}
function runsStr() {
  const r = d.montecarlo && d.montecarlo.runs;
  return r != null ? Number(r).toLocaleString("en-US") : "50,000";
}
function distStr() {
  const x = d.montecarlo && d.montecarlo.distribution;
  return (typeof x === "string" && x) ? x : "lognormal";
}

// ---------- derive per-finding fields (degrade gracefully) ----------
const findings = Array.isArray(d.findings) ? d.findings : [];
findings.forEach(f => {
  if (f.lef == null && f.tef != null && f.vuln != null) f.lef = num(f.tef) * num(f.vuln);
  if (f.lmBuckets && f.meanLM == null) {
    f.meanLM = Object.values(f.lmBuckets).reduce((s, b) => s + PERT(b), 0);
  }
  if (f.aleMid == null && f.lef != null && f.meanLM != null) f.aleMid = f.lef * f.meanLM;
  if (!f.aleRange && f.aleMid != null) f.aleRange = [f.aleMid * 0.4, f.aleMid * 2.6];
  if (!f.codRange && f.aleRange) f.codRange = [f.aleRange[0] / 12, f.aleRange[1] / 12];
  if (f.rosiPct == null && f.aleMid != null && f.controlCost) {
    f.rosiPct = Math.round(((f.aleMid - (f.aleAfter || 0) - f.controlCost) / f.controlCost) * 100);
  }
});

// ==================================================================
// chrome / helpers (copied from the VIP builder + findings deck)
// ==================================================================
function corner(s, color = C.tealDark, size = 16) {
  s.addText("colt", { x: 9.05, y: 0.18, w: 0.85, h: 0.32, fontSize: size, fontFace: FA,
    color, bold: true, align: "right", margin: 0 });
}
function bigChevrons(s, o = {}) {
  const x = o.x ?? 0.5, w = o.w ?? 9.0, yStart = o.yStart ?? 0.20;
  const triH = o.triH ?? 1.55, gap = o.gap ?? 0.30, color = o.color || C.white, op = o.opacity;
  for (let i = 0; i < 3; i++) {
    const cfg = { x, y: yStart + i * (triH + gap), w, h: triH, fill: { color }, line: { type: "none" } };
    if (op !== undefined) cfg.fill = { color, transparency: Math.round((1 - op) * 100) };
    s.addShape(pres.shapes.ISOSCELES_TRIANGLE, cfg);
  }
}
function tracer(s, color = C.tealDark) {
  for (let i = 0; i < 3; i++) s.addShape(pres.shapes.RIGHT_TRIANGLE,
    { x: 8.30 + i * 0.14, y: 5.34, w: 0.11, h: 0.16, fill: { color }, line: { type: "none" }, rotate: 90 });
  s.addText(RAQUO + RAQUO + " " + pageNum + "/" + TOTAL, { x: 8.62, y: 5.28, w: 1.23, h: 0.28,
    fontSize: 9, fontFace: FB, color, bold: true, align: "right", valign: "middle", margin: 0 });
}
function footer(s, color = C.inkMuted) {
  s.addText(FOOT, { x: 0.4, y: 5.34, w: 7.7, h: 0.20, fontSize: 6.6, fontFace: FB,
    color, charSpacing: 1, margin: 0, valign: "middle" });
}
function pageHeader(s, eyebrow, title) {
  s.addText(String(eyebrow || "").toUpperCase(), { x: 0.4, y: 0.22, w: 8.4, h: 0.22,
    fontSize: 9, fontFace: FB, color: C.teal, charSpacing: 3, bold: true, margin: 0 });
  s.addText(String(title || ""), { x: 0.4, y: 0.44, w: 8.6, h: 0.82,
    fontSize: 18, fontFace: FH, color: C.tealDark, bold: true, valign: "top", margin: 0 });
  corner(s, C.tealDark, 16);
}
// content() factory: branded content slide with header + footer + tracer
function content(eyebrow, title) {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.white };
  pageHeader(s, eyebrow, title);
  footer(s);
  tracer(s);
  return s;
}

// rect-based branded table (teal-dark header + zebra rows + optional cell fills)
function drawTable(s, x, y, colW, headers, rows, o = {}) {
  const rowH = o.rowH || 0.30, hH = o.hH || 0.28, fs = o.fs || 8, hfs = o.hfs || 7.6;
  let cx = x;
  headers.forEach((h, i) => {
    s.addShape(R(), { x: cx, y, w: colW[i], h: hH, fill: { color: C.tealDark }, line: { type: "none" } });
    s.addText(String(h).toUpperCase(), { x: cx + 0.06, y, w: colW[i] - 0.12, h: hH, fontSize: hfs,
      fontFace: FB, bold: true, color: C.white, charSpacing: 1, valign: "middle", margin: 0 });
    cx += colW[i];
  });
  rows.forEach((r, ri) => {
    const ry = y + hH + ri * rowH; cx = x;
    r.forEach((cell, i) => {
      const cl = (cell && typeof cell === "object") ? cell : { text: cell };
      const fill = cl.fill || (ri % 2 ? C.light : C.white);
      s.addShape(R(), { x: cx, y: ry, w: colW[i], h: rowH, fill: { color: fill }, line: { type: "none" } });
      s.addText(String(cl.text == null ? "" : cl.text), { x: cx + 0.06, y: ry, w: colW[i] - 0.12, h: rowH,
        fontSize: cl.fs || fs, fontFace: cl.mono ? FM : FB, bold: cl.bold, color: cl.color || C.ink,
        align: cl.align, valign: "middle", margin: 0, lineSpacingMultiple: 0.94 });
      cx += colW[i];
    });
  });
  return y + hH + rows.length * rowH;
}

function badge(s, tier, x, y, w = 1.0) {
  const [c, fg] = TIER[tier] || TIER.LOW;
  s.addShape(R(), { x, y, w, h: 0.28, fill: { color: c }, line: { type: "none" } });
  s.addText(tier, { x, y, w, h: 0.28, fontSize: 9, fontFace: FB, bold: true, color: fg,
    align: "center", valign: "middle", charSpacing: 2, margin: 0 });
}

// simple horizontal bar chart (rect based)
function barChart(s, items, o = {}) {
  const x0 = o.x ?? 0.4, y0 = o.y ?? 1.5, w = o.w ?? 9.2;
  const barH = o.barH ?? 0.32, gap = o.gap ?? 0.14, labW = o.labW ?? 2.2, valW = o.valW ?? 1.6;
  const max = Math.max.apply(null, items.map(i => i.v).concat([1]));
  const track = w - labW - valW;
  items.forEach((it, i) => {
    const y = y0 + i * (barH + gap);
    s.addText(it.label, { x: x0, y, w: labW - 0.1, h: barH, fontSize: 8.6, fontFace: FB,
      color: C.ink, valign: "middle", bold: !!it.bold, margin: 0 });
    s.addShape(R(), { x: x0 + labW, y: y + 0.04, w: track, h: barH - 0.08, fill: { color: C.light }, line: { type: "none" } });
    const bw = Math.max(0.05, (it.v / max) * track);
    s.addShape(R(), { x: x0 + labW, y: y + 0.04, w: bw, h: barH - 0.08, fill: { color: it.color || C.teal }, line: { type: "none" } });
    s.addText(it.vlabel != null ? it.vlabel : String(it.v), { x: x0 + labW + track + 0.08, y, w: valW - 0.1, h: barH,
      fontSize: 8.6, fontFace: FM, color: C.ink, valign: "middle", margin: 0 });
  });
}

// ==================================================================
// SLIDE 1 -- TITLE
// ==================================================================
function titleSlide() {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.teal };
  bigChevrons(s, { x: 5.95, w: 5.0, yStart: 0.05, triH: 1.95, gap: 0.06, color: C.white });
  corner(s, C.black, 22);
  s.addText("CYBER BUSINESS-IMPACT QUANTIFICATION " + MIDDOT + " C-BIQ",
    { x: 0.5, y: 1.10, w: 8.7, h: 0.30, fontSize: 11, fontFace: FA, color: C.black, bold: true, charSpacing: 2, margin: 0 });
  s.addText("CYBER RISK,", { x: 0.46, y: 1.48, w: 8.8, h: 0.95, fontSize: 46, fontFace: FD, color: C.black, bold: true, margin: 0 });
  s.addText("PRICED IN " + String(WORD).toUpperCase() + ".", { x: 0.46, y: 2.40, w: 8.8, h: 0.95, fontSize: 46, fontFace: FD, color: C.black, bold: true, margin: 0 });
  s.addShape(R(), { x: 0.54, y: 3.34, w: 0.22, h: 0.22, fill: { color: C.med }, line: { type: "none" } });
  s.addText(String(cust) + " " + EMDASH + " turning the external-surface findings into " + WORD + ", and pricing each Colt remediation.",
    { x: 0.9, y: 3.30, w: 8.4, h: 0.42, fontSize: 12.5, fontFace: FA, color: C.black, italic: true, margin: 0 });
  s.addShape(R(), { x: 0, y: 4.5, w: 10, h: 1.12, fill: { color: C.tealDark }, line: { type: "none" } });
  const meta = [
    ["FRAMEWORK", (d.frameworks && d.frameworks.join(" " + MIDDOT + " ")) || ("FAIR " + MIDDOT + " NIST IR 8286D")],
    ["METHOD", d.method || ("Monte-Carlo CRQ (" + runsStr() + " runs)")],
    ["OUTPUT", "ALE " + MIDDOT + " PML " + MIDDOT + " CoD " + MIDDOT + " ROSI"],
    ["REMEDIATION", d.remediationSuite || "Colt PSF + managed services"],
  ];
  meta.forEach((m, i) => {
    const x = 0.5 + i * 2.32;
    s.addText(m[0], { x, y: 4.66, w: 2.25, h: 0.22, fontSize: 8, fontFace: FB, color: C.teal, bold: true, charSpacing: 1, margin: 0 });
    s.addText(m[1], { x, y: 4.90, w: 2.30, h: 0.55, fontSize: 8.6, fontFace: FB, color: C.white, valign: "top", margin: 0 });
  });
  s.addText("All " + WORD + " figures are ILLUSTRATIVE model output, not measured loss " + EMDASH + " calibrated to public benchmarks plus stated assumptions. Internal Colt pursuit material.",
    { x: 0.5, y: 5.42, w: 9.0, h: 0.2, fontSize: 6.6, fontFace: FB, color: C.black, margin: 0 });
}

// ==================================================================
// SLIDE 2 -- DIVIDER  (big Arial-Black label + faint chevrons)
// ==================================================================
function dividerSlide() {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.tealDark };
  bigChevrons(s, { x: 0.5, w: 9.0, yStart: 0.10, triH: 1.55, gap: 0.30, color: C.white, opacity: 0.14 });
  s.addText("BUSINESS IMPACT.", { x: 0, y: 1.9, w: 10, h: 1.6, fontSize: 58, fontFace: FD,
    color: C.white, bold: true, align: "center", valign: "middle", margin: 0 });
  s.addText("What the exposure costs in " + WORD + " " + EMDASH + " and how much risk each Colt control buys back.",
    { x: 0.5, y: 3.5, w: 9, h: 0.4, fontSize: 13, fontFace: FB, color: C.teal, align: "center", italic: true, margin: 0 });
  corner(s, C.white, 16);
  tracer(s, C.white);
}

// ==================================================================
// SLIDE 3 -- THE THREE NUMBERS (ALE / PML / ROSI cards + CoD strip)
// ==================================================================
function threeNumbersSlide() {
  const s = content("Bottom line up front", "The three numbers your board needs");
  const p = d.portfolio || {};
  const cards = [
    ["ALE", "ANNUALISED LOSS EXPECTANCY", p.aleRange ? moneyRange(p.aleRange) : money(p.aleLikely),
      "per year, across all findings " + EMDASH + " the budget number", C.crit],
    ["PML", "PROBABLE MAXIMUM LOSS", (p.largestPmls && p.largestPmls[0]) ? money(p.largestPmls[0].pml) : EMDASH,
      "single worst-case event " + EMDASH + " capital / insurance", C.high],
    ["ROSI", "RETURN ON SECURITY INVESTMENT", (p.rosiPct != null ? p.rosiPct + "%" : EMDASH),
      "payback " + (p.payback || "< 12 mo") + " " + EMDASH + " the funding case", C.green],
  ];
  cards.forEach((cd, i) => {
    const k = cd[0], l = cd[1], v = cd[2], sub = cd[3], c = cd[4];
    const x = 0.4 + i * 3.07;
    s.addShape(R(), { x, y: 1.55, w: 2.87, h: 2.2, fill: { color: C.tealDark }, line: { type: "none" } });
    s.addShape(R(), { x, y: 1.55, w: 2.87, h: 0.11, fill: { color: c }, line: { type: "none" } });
    s.addText(k, { x, y: 1.72, w: 2.87, h: 0.44, fontSize: 26, fontFace: FH, bold: true, color: c, align: "center", margin: 0 });
    s.addText(l, { x: x + 0.12, y: 2.20, w: 2.63, h: 0.34, fontSize: 7.6, fontFace: FB, color: C.white, bold: true, align: "center", charSpacing: 1, margin: 0 });
    s.addText(v, { x: x + 0.1, y: 2.56, w: 2.67, h: 0.62, fontSize: 22, fontFace: FD, bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(sub, { x: x + 0.15, y: 3.24, w: 2.57, h: 0.44, fontSize: 8.4, fontFace: FB, color: C.teal, align: "center", valign: "top", margin: 0 });
  });
  s.addShape(R(), { x: 0.4, y: 4.02, w: 9.3, h: 0.82, fill: { color: C.light }, line: { type: "none" } });
  s.addShape(R(), { x: 0.4, y: 4.02, w: 0.07, h: 0.82, fill: { color: C.gold }, line: { type: "none" } });
  const codAv = p.codAvoided ? money(p.codAvoided) : (p.aleLikely ? money(p.aleLikely / 12) : EMDASH);
  s.addText([
    { text: "COST OF DELAY  ", options: { bold: true, color: C.tealDark } },
    { text: "every month un-remediated burns " + APPROX + " " + codAv + " in expected loss.  ", options: { color: C.ink } },
    { text: "CoD = ALE / 12.", options: { color: C.inkMuted, italic: true } },
  ], { x: 0.6, y: 4.08, w: 8.9, h: 0.7, fontSize: 10.5, fontFace: FB, valign: "middle", margin: 0 });
}

// ==================================================================
// SLIDE 4 -- STANDARDS (grounded in published models)
// ==================================================================
function standardsSlide() {
  const s = content("Grounded in standards", "We didn't invent the maths");
  drawTable(s, 0.4, 1.4, [2.9, 3.3, 3.1],
    ["Standard / source", "What it gives us", "Role in C-BIQ"],
    [
      ["FAIR (Open FAIR)", "Factor Analysis of Information Risk", { text: "Decomposes risk into LEF " + TIMES + " Loss Magnitude", color: C.ink }],
      ["NIST IR 8286D", "Cyber risk " + RARR + " ERM integration", "Board-level roll-up & tolerance bands"],
      ["Gartner ROSI", "Return on Security Investment", "Cost-benefit & payback of controls"],
      ["IBM / Ponemon", "Cost of a Data Breach report", "Empirical loss-magnitude anchors"],
      ["Deloitte", "Beneath the Surface", "The seven cash buckets (L1" + EMDASH + "L7)"],
    ],
    { rowH: 0.52, hH: 0.30, fs: 8.8, hfs: 8 });
  s.addText("Every " + WORD.replace(/s$/, "") + " figure in this deck traces to a published model " + EMDASH + " no black boxes.",
    { x: 0.4, y: 4.72, w: 9.3, h: 0.3, fontSize: 9.5, fontFace: FB, color: C.tealDark, italic: true, bold: true, margin: 0 });
}

// ==================================================================
// SLIDE 5 -- THE SEVEN-STEP ENGINE
// ==================================================================
function engineSlide() {
  const s = content("How we measure", "The C-BIQ engine " + EMDASH + " a seven-step pipeline, run per finding");
  const steps = [
    ["1", "Asset criticality", "How hard the operation leans on the asset (NIST 8286D BIA " + MIDDOT + " C/I/A 1" + EMDASH + "5)"],
    ["2", "Loss scenario", "The specific bad thing that happens, in one plain sentence (FAIR)"],
    ["3", "Frequency (LEF)", "How often it lands per year: LEF = TEF " + TIMES + " Vulnerability"],
    ["4", "Magnitude (LM)", "What one event costs, summed across seven cash buckets (Deloitte)"],
    ["5", "Simulate", runsStr() + " Monte-Carlo runs " + RARR + " ALE, PML and the loss-exceedance curve"],
    ["6", "Register & compare", "Write to the risk register; test against risk appetite (NIST 8286D)"],
    ["7", "Treat & re-measure", "Apply the Colt fix, recompute, report ROSI (Gartner)"],
  ];
  let y = 1.34;
  steps.forEach((st, i) => {
    const h = 0.5;
    s.addShape(R(), { x: 0.4, y, w: 0.5, h: h - 0.06, fill: { color: i < 6 ? C.tealDark : C.green }, line: { type: "none" } });
    s.addText(st[0], { x: 0.4, y, w: 0.5, h: h - 0.06, fontSize: 16, fontFace: FH, color: C.white, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(st[1], { x: 1.05, y, w: 3.0, h: h - 0.06, fontSize: 11, fontFace: FB, bold: true, color: C.tealDark, valign: "middle", margin: 0 });
    s.addText(st[2], { x: 4.1, y, w: 5.6, h: h - 0.06, fontSize: 9, fontFace: FB, color: C.ink, valign: "middle", margin: 0 });
    y += h;
  });
  s.addText("Steps 1" + EMDASH + "6 any CRQ vendor can do. Step 7 " + EMDASH + " apply the fix and prove the ROSI " + EMDASH + " is the part only a delivery partner closes. That is Colt.",
    { x: 0.4, y: 4.92, w: 9.3, h: 0.3, fontSize: 8.6, fontFace: FB, color: C.green, bold: true, italic: true, margin: 0 });
}

// ==================================================================
// SLIDE 6 -- FAIR MATHS (LEF = TEF x Vuln, LM = Sigma L1..L7, Monte-Carlo box)
// ==================================================================
function fairMathSlide() {
  const s = content("The maths, made visible", "Risk = LEF " + TIMES + " LM " + EMDASH + " decomposed so every number can be challenged");
  const box = (x, top, big, sub, small, col) => {
    s.addShape(R(), { x, y: top, w: 2.7, h: 1.35, fill: { color: C.light }, line: { type: "none" } });
    s.addShape(R(), { x, y: top, w: 2.7, h: 0.38, fill: { color: col }, line: { type: "none" } });
    s.addText(big, { x: x + 0.1, y: top, w: 2.5, h: 0.38, fontSize: 11, fontFace: FB, bold: true, color: C.white, valign: "middle", margin: 0 });
    s.addText(sub, { x: x + 0.1, y: top + 0.44, w: 2.5, h: 0.42, fontSize: 14, fontFace: FH, bold: true, color: C.tealDark, valign: "middle", margin: 0 });
    s.addText(small, { x: x + 0.1, y: top + 0.88, w: 2.5, h: 0.45, fontSize: 8.2, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
  };
  box(0.4, 1.34, "RISK " + MIDDOT + " ALE", "Expected loss / yr", "Mean of " + runsStr() + " simulated years", C.tealDark);
  s.addText("=", { x: 3.15, y: 1.7, w: 0.5, h: 0.6, fontSize: 26, fontFace: FH, bold: true, color: C.inkMuted, align: "center", valign: "middle", margin: 0 });
  box(3.6, 1.34, "LOSS EVENT FREQ", "LEF = TEF " + TIMES + " Vuln", "Attempts/yr " + TIMES + " chance one succeeds", C.high);
  s.addText(TIMES, { x: 6.35, y: 1.7, w: 0.5, h: 0.6, fontSize: 26, fontFace: FH, bold: true, color: C.inkMuted, align: "center", valign: "middle", margin: 0 });
  box(6.9, 1.34, "LOSS MAGNITUDE", "LM = " + SIGMA + " (L1" + EMDASH + "L7)", "One event's cost " + MIDDOT + " 7 cash buckets", C.crit);

  s.addText("THE TERMS", { x: 0.4, y: 2.95, w: 6.3, h: 0.22, fontSize: 9, fontFace: FB, bold: true, color: C.tealDark, charSpacing: 1, margin: 0 });
  const defs = [
    ["LEF", "Loss Event Frequency " + EMDASH + " loss events / year"],
    ["TEF", "Threat Event Frequency " + EMDASH + " credible attempts / year"],
    ["Vuln", "Probability any single attempt succeeds (0" + EMDASH + "1)"],
    ["LM", "Loss Magnitude " + EMDASH + " " + SIGMA + " of seven cost buckets (PERT)"],
  ];
  defs.forEach((r, i) => {
    const y = 3.22 + i * 0.40;
    s.addShape(R(), { x: 0.4, y, w: 0.66, h: 0.34, fill: { color: C.tealDark }, line: { type: "none" } });
    s.addText(r[0], { x: 0.4, y, w: 0.66, h: 0.34, fontSize: 9, fontFace: FM, bold: true, color: C.teal, align: "center", valign: "middle", margin: 0 });
    s.addText(r[1], { x: 1.16, y, w: 5.4, h: 0.34, fontSize: 9, fontFace: FB, color: C.ink, valign: "middle", margin: 0 });
  });
  s.addShape(R(), { x: 6.9, y: 3.22, w: 2.8, h: 1.54, fill: { color: C.light }, line: { type: "none" } });
  s.addShape(R(), { x: 6.9, y: 3.22, w: 2.8, h: 0.09, fill: { color: C.teal }, line: { type: "none" } });
  s.addText("MONTE-CARLO", { x: 6.9, y: 3.38, w: 2.8, h: 0.28, fontSize: 10, fontFace: FB, bold: true, color: C.tealDark, align: "center", charSpacing: 1, margin: 0 });
  s.addText(runsStr(), { x: 6.9, y: 3.70, w: 2.8, h: 0.55, fontSize: 24, fontFace: FD, bold: true, color: C.tealDark, align: "center", margin: 0 });
  s.addText("iterations per finding\ndistribution: " + distStr(), { x: 7.0, y: 4.28, w: 2.6, h: 0.44, fontSize: 8.4, fontFace: FB, color: C.ink, align: "center", margin: 0 });
  s.addText("We never report one number: each input is a Min/Likely/Max estimate anchored to public benchmarks and sampled " + runsStr() + " times " + EMDASH + " the output is a range and a curve.",
    { x: 0.4, y: 4.86, w: 9.3, h: 0.3, fontSize: 8.2, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
}

// ==================================================================
// SLIDE 7 -- LOSS-EXCEEDANCE LINE CHART (before / after)
// ==================================================================
function lecSlide() {
  const s = content("The board picture", "Loss-exceedance curve " + EMDASH + " the whole curve shifts down after remediation");
  s.addText("Read it as: a P% chance " + cust + " loses at least " + SYM + "X to an external-surface cyber event in a year. The Colt remediation shifts the entire curve toward the origin " + EMDASH + " the drawn version of the ROSI.",
    { x: 0.4, y: 1.28, w: 9.3, h: 0.44, fontSize: 9, fontFace: FB, color: C.ink, valign: "top", margin: 0, lineSpacingMultiple: 1.03 });
  const lec = d.lossExceedance || {};
  const th = Array.isArray(lec.thresholds) ? lec.thresholds : [];
  const pct = arr => arr.map(v => (v <= 1 ? v * 100 : v));
  if (th.length && (lec.before || lec.after)) {
    const data = [];
    if (lec.before) data.push({ name: "Before remediation", labels: th.map(money), values: pct(lec.before) });
    if (lec.after) data.push({ name: "After Colt controls", labels: th.map(money), values: pct(lec.after) });
    s.addChart(pres.charts.LINE, data, {
      x: 0.5, y: 1.80, w: 9.0, h: 3.05, chartColors: [C.crit, C.green], lineSize: 3, lineSmooth: true,
      showLegend: true, legendPos: "t", legendColor: C.ink, legendFontFace: FB, legendFontSize: 9, showTitle: false,
      valAxisTitle: "Probability of exceeding (%)", showValAxisTitle: true, valAxisTitleColor: C.inkMuted, valAxisTitleFontSize: 9,
      valAxisMinVal: 0, valAxisLabelColor: C.inkMuted, valAxisLabelFontFace: FM, valAxisLabelFontSize: 8,
      catAxisTitle: "Annual external-surface loss threshold", showCatAxisTitle: true, catAxisTitleColor: C.inkMuted, catAxisTitleFontSize: 9,
      catAxisLabelColor: C.ink, catAxisLabelFontFace: FM, catAxisLabelFontSize: 8.5,
    });
  } else {
    s.addText("No loss-exceedance data supplied.", { x: 0.4, y: 2.6, w: 9, h: 0.4, fontSize: 12, fontFace: FB, color: C.inkMuted, margin: 0 });
  }
  const p = d.portfolio || {};
  const aleTxt = p.aleRange ? moneyRange(p.aleRange) : money(p.aleLikely);
  const pmlTxt = (p.largestPmls && p.largestPmls[0]) ? money(p.largestPmls[0].pml) : EMDASH;
  s.addText("Before: ALE " + APPROX + " " + aleTxt + ", PML " + APPROX + " " + pmlTxt + ".  After Colt remediation the curve collapses toward the origin " + EMDASH + " illustrative.",
    { x: 0.5, y: 4.94, w: 9, h: 0.24, fontSize: 8, fontFace: FB, color: C.inkMuted, italic: true, align: "center", margin: 0 });
}

// ==================================================================
// SLIDE 8 -- MONTE-CARLO DISTRIBUTION BAR
// ==================================================================
function distSlide() {
  const s = content("Under the hood", "Monte-Carlo loss distribution");
  const dist = d.montecarlo && d.montecarlo.distribution;
  let items;
  if (Array.isArray(dist)) {
    items = dist.map(b => ({ label: b.band || b[0], v: num(b.count != null ? b.count : b[1]), vlabel: String(b.count != null ? b.count : b[1]), color: C.tealMid }));
  } else {
    const shape = [3, 9, 17, 22, 19, 13, 8, 5, 3, 1];
    const p = d.portfolio || {};
    const lo = (p.aleRange && p.aleRange[0]) || 1e6;
    const hi = (p.aleRange && p.aleRange[1]) || 1e7;
    const step = (hi - lo) / shape.length;
    items = shape.map((v, i) => ({ label: money(lo + i * step), v, vlabel: v + "%", color: i >= 6 ? C.high : C.tealMid }));
  }
  barChart(s, items, { x: 0.4, y: 1.5, w: 9.2, barH: 0.26, gap: 0.08, labW: 1.9, valW: 0.8 });
  s.addText(runsStr() + " simulated annual-loss outcomes. The long right tail is the tail-risk your PML captures.",
    { x: 0.4, y: 5.0, w: 9.2, h: 0.28, fontSize: 8.5, fontFace: FB, color: C.tealDark, italic: true, margin: 0 });
}

// ==================================================================
// SLIDE 9 -- SEVEN CASH BUCKETS (bar)
// ==================================================================
function bucketsSlide() {
  const s = content("Loss magnitude", "The seven cash buckets (L1" + EMDASH + "L7) " + EMDASH + " what a cyber event actually costs");
  const buckets = (d.buckets && d.buckets.length) ? d.buckets : [
    { id: "L1", name: "Response & investigation" }, { id: "L2", name: "Notification & legal" },
    { id: "L3", name: "Business interruption" }, { id: "L4", name: "Regulatory fines" },
    { id: "L5", name: "Reputation & churn" }, { id: "L6", name: "Recovery & rebuild" },
    { id: "L7", name: "Secondary / liability" },
  ];
  const sums = {};
  buckets.forEach(b => sums[b.id] = 0);
  findings.forEach(f => { if (f.lmBuckets) Object.entries(f.lmBuckets).forEach(([k, v]) => { sums[k] = (sums[k] || 0) + PERT(v); }); });
  const anyData = Object.values(sums).some(v => v > 0);
  const items = buckets.map((b, i) => ({
    label: b.id + "  " + (b.name || ""),
    v: anyData ? sums[b.id] : (7 - i),
    vlabel: anyData ? money(sums[b.id]) : "",
    color: (b.id === "L3") ? C.crit : (i < 2 ? C.high : C.tealDark),
  }));
  barChart(s, items, { x: 0.4, y: 1.5, w: 9.2, barH: 0.34, gap: 0.15, labW: 3.2, valW: 1.4 });
  s.addText("Bars are the summed most-likely (PERT) loss per bucket, across all priced findings. For most operators the below-surface buckets (L3" + EMDASH + "L7) dwarf the incident-response invoice (L1).",
    { x: 0.4, y: 5.0, w: 9.2, h: 0.3, fontSize: 8.4, fontFace: FB, color: C.tealDark, italic: true, margin: 0 });
}

// ==================================================================
// SLIDE 10 -- ROSI / COST-BENEFIT
// ==================================================================
function rosiSlide() {
  const s = content("The funding case", "ROSI " + EMDASH + " risk bought back, set against the cost of the managed service");
  const p = d.portfolio || {};
  s.addText("The controls remove most of the external-surface annual loss; together they cost a fraction of what they buy back. ROSI = (ALE before " + EMDASH + " ALE after " + EMDASH + " control cost) / control cost.",
    { x: 0.4, y: 1.28, w: 9.3, h: 0.44, fontSize: 9, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
  const items = findings.map(f => ({
    label: (f.id || "") + " " + String(f.label || "").slice(0, 20),
    v: Math.max(0, f.rosiPct || 0),
    vlabel: (f.rosiPct != null ? f.rosiPct + "%" : EMDASH),
    color: C.green,
  }));
  if (items.length) barChart(s, items, { x: 0.4, y: 1.9, w: 5.6, barH: 0.34, gap: 0.16, labW: 2.6, valW: 0.9 });
  const cards = [
    ["PORTFOLIO ROSI", (p.rosiPct != null ? p.rosiPct + "%" : EMDASH), "risk bought back per " + SYM + " of control", C.green],
    ["PAYBACK", (p.payback || "< 12 mo"), "before the service pays for itself", C.teal],
    ["CoD AVOIDED", (p.codAvoided ? money(p.codAvoided) + " / mo" : EMDASH), "carried for every month deferred", C.gold],
  ];
  let y = 1.92;
  cards.forEach(c => {
    s.addShape(R(), { x: 6.3, y, w: 3.3, h: 0.95, fill: { color: C.light }, line: { type: "none" } });
    s.addShape(R(), { x: 6.3, y, w: 0.08, h: 0.95, fill: { color: c[3] }, line: { type: "none" } });
    s.addText(c[0], { x: 6.5, y: y + 0.1, w: 3.0, h: 0.25, fontSize: 9, fontFace: FB, bold: true, color: C.tealDark, charSpacing: 1, margin: 0 });
    s.addText(c[1], { x: 6.5, y: y + 0.32, w: 3.0, h: 0.4, fontSize: 19, fontFace: FH, bold: true, color: c[3], valign: "middle", margin: 0 });
    s.addText(c[2], { x: 6.5, y: y + 0.72, w: 3.0, h: 0.22, fontSize: 7.6, fontFace: FB, color: C.ink, margin: 0 });
    y += 1.07;
  });
  s.addText("One managed plane retires several findings at once, so portfolio ROSI far exceeds any single-finding fix " + EMDASH + " the managed-service argument, drawn.",
    { x: 0.4, y: 5.0, w: 9.2, h: 0.28, fontSize: 8.2, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
}

// ==================================================================
// SLIDE 11 -- EVERY FINDING PRICED (table with coloured tier badges)
// ==================================================================
function pricedTableSlide() {
  const s = content("Every finding " + EMDASH + " priced & assigned", "Findings " + RARR + " " + WORD + " " + RARR + " the Colt control that retires each");
  const cols = [0.62, 0.7, 3.16, 0.72, 1.4, 1.4, 1.3];
  const X = 0.4;
  const hd = ["SEV", "ID", "FINDING / LOSS DRIVER", "LEF", "ALE " + SYM + "/yr", "PML " + SYM, "COLT CONTROL"];
  const y = 1.34, hH = 0.28;
  const rows = findings.slice(0, 11).map(f => [
    { text: f.tier || "LOW", fill: (TIER[f.tier] || TIER.LOW)[0], color: (TIER[f.tier] || TIER.LOW)[1], bold: true, align: "center" },
    { text: f.id || "", bold: true },
    { text: String(f.label || "").slice(0, 42) },
    { text: (f.lef != null ? Number(f.lef).toFixed(2) : EMDASH), mono: true },
    { text: moneyRange(f.aleRange), mono: true, color: C.crit, bold: true },
    { text: moneyRange(f.pmlRange), mono: true, color: C.high },
    { text: f.coltControl || EMDASH, color: C.tealDark, bold: true },
  ]);
  const rowH = Math.max(0.26, Math.min(0.34, 3.3 / Math.max(rows.length, 1)));
  if (rows.length) {
    drawTable(s, X, y, cols, hd, rows, { rowH, hH, fs: 7.7, hfs: 7.4 });
  } else {
    s.addText("No findings to price.", { x: 0.4, y: 2.5, w: 9, h: 0.4, fontSize: 12, fontFace: FB, color: C.inkMuted, margin: 0 });
  }
  const p = d.portfolio || {};
  const aleTxt = p.aleRange ? moneyRange(p.aleRange) : money(p.aleLikely);
  const likely = p.aleLikely ? money(p.aleLikely) : EMDASH;
  const pmls = (p.largestPmls || []).slice(0, 2).map(x => (x.id || "") + " " + APPROX + " " + money(x.pml)).join(" " + MIDDOT + " ");
  s.addText("LEF = events/yr " + MIDDOT + " ALE = mean annual loss " + MIDDOT + " PML = ~95th-pct single event. Ranges reflect modelling uncertainty; figures illustrative.",
    { x: 0.4, y: 4.74, w: 9.3, h: 0.22, fontSize: 7.6, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
  s.addText([
    { text: "Portfolio ALE " + APPROX + " " + aleTxt + "/yr (likely " + APPROX + " " + likely + ").  ", options: { bold: true, color: C.tealDark } },
    { text: pmls ? ("Largest single PMLs: " + pmls + " " + EMDASH + " reported as capital/insurance, never averaged into ALE.") : "", options: { color: C.ink } },
  ], { x: 0.4, y: 4.98, w: 9.3, h: 0.28, fontSize: 8.2, fontFace: FB, margin: 0 });
}

// ==================================================================
// SLIDE 12 -- WORKED EXAMPLE (top CRIT finding, end-to-end)
// ==================================================================
function workedExampleSlide() {
  const crit = findings.find(f => f.tier === "CRIT") || findings[0];
  const s = content("Worked end-to-end", crit ? (String(crit.id || "") + " " + EMDASH + " " + String(crit.label || "Finding")) : "Worked example");
  if (!crit) {
    s.addText("No findings to work through.", { x: 0.4, y: 2.5, w: 9, h: 0.4, fontSize: 12, fontFace: FB, color: C.inkMuted, margin: 0 });
    return;
  }
  badge(s, crit.tier || "CRIT", 8.55, 0.58, 1.0);

  s.addText("THE FAIR CHAIN", { x: 0.4, y: 1.4, w: 4.4, h: 0.22, fontSize: 9, fontFace: FB, bold: true, color: C.tealMid, charSpacing: 1, margin: 0 });
  const chain = [
    ["TEF (attempts / yr)", crit.tef != null ? String(crit.tef) : EMDASH],
    [TIMES + " Vuln (success prob.)", crit.vuln != null ? Number(crit.vuln).toFixed(2) : EMDASH],
    ["= LEF (loss events / yr)", crit.lef != null ? Number(crit.lef).toFixed(2) : EMDASH],
    [TIMES + " Mean LM (" + SIGMA + " L1" + EMDASH + "L7)", crit.meanLM != null ? money(crit.meanLM) : EMDASH],
    ["= ALE (mid)", crit.aleMid != null ? money(crit.aleMid) : EMDASH],
  ];
  chain.forEach((r, i) => {
    const y = 1.68 + i * 0.5; const last = i === chain.length - 1;
    s.addShape(R(), { x: 0.4, y, w: 4.5, h: 0.42, fill: { color: last ? C.tealDark : C.light }, line: { type: "none" } });
    s.addText(r[0], { x: 0.55, y, w: 3.05, h: 0.42, fontSize: 9.5, fontFace: FB, color: last ? C.white : C.ink, bold: last, valign: "middle", margin: 0 });
    s.addText(r[1], { x: 3.5, y, w: 1.3, h: 0.42, fontSize: 11, fontFace: FM, bold: true, color: last ? C.teal : C.tealDark, align: "right", valign: "middle", margin: 0 });
  });

  s.addText("STEPS 5" + EMDASH + "7 " + MIDDOT + " SIMULATE, REGISTER, TREAT", { x: 5.1, y: 1.4, w: 4.5, h: 0.22, fontSize: 9, fontFace: FB, bold: true, color: C.tealMid, charSpacing: 1, margin: 0 });
  const outs = [
    ["ALE range / yr", moneyRange(crit.aleRange), C.crit],
    ["PML (worst case)", moneyRange(crit.pmlRange), C.high],
    ["Cost of Delay / mo", moneyRange(crit.codRange), C.gold],
    ["Colt control", crit.coltControl || EMDASH, C.teal],
    ["Residual ALE / ROSI", (crit.aleAfter != null ? money(crit.aleAfter) : EMDASH) + "  /  " + (crit.rosiPct != null ? crit.rosiPct + "%" : EMDASH), C.green],
  ];
  outs.forEach((r, i) => {
    const y = 1.68 + i * 0.5;
    s.addShape(R(), { x: 5.1, y, w: 4.5, h: 0.42, fill: { color: C.light }, line: { type: "none" } });
    s.addShape(R(), { x: 5.1, y, w: 0.07, h: 0.42, fill: { color: r[2] }, line: { type: "none" } });
    s.addText(r[0], { x: 5.28, y, w: 2.3, h: 0.42, fontSize: 9.5, fontFace: FB, color: C.ink, valign: "middle", margin: 0 });
    s.addText(r[1], { x: 7.0, y, w: 2.5, h: 0.42, fontSize: 9.5, fontFace: FM, bold: true, color: r[2], align: "right", valign: "middle", margin: 0 });
  });

  if (crit.realComparable) {
    s.addShape(R(), { x: 0.4, y: 4.28, w: 9.2, h: 0.5, fill: { color: C.light }, line: { type: "none" } });
    s.addShape(R(), { x: 0.4, y: 4.28, w: 0.07, h: 0.5, fill: { color: C.crit }, line: { type: "none" } });
    s.addText([
      { text: "Real comparable:  ", options: { bold: true, color: C.tealDark } },
      { text: String(crit.realComparable), options: { color: C.ink, italic: true } },
    ], { x: 0.6, y: 4.28, w: 9.0, h: 0.5, fontSize: 8.8, fontFace: FB, valign: "middle", margin: 0 });
  } else if (crit.lossScenario) {
    s.addText([
      { text: "Loss scenario:  ", options: { bold: true, color: C.tealDark } },
      { text: String(crit.lossScenario), options: { color: C.ink, italic: true } },
    ], { x: 0.4, y: 4.35, w: 9.2, h: 0.5, fontSize: 8.8, fontFace: FB, valign: "middle", margin: 0 });
  }
}

// ==================================================================
// SLIDE 13 -- CLOSER
// ==================================================================
function closerSlide() {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.tealDark };
  corner(s, C.white, 16);
  s.addText("PRICED " + MIDDOT + " PROVEN " + MIDDOT + " FUNDED", { x: 0.4, y: 0.40, w: 8, h: 0.3, fontSize: 11, fontFace: FB, color: C.teal, bold: true, charSpacing: 3, margin: 0 });
  s.addText("From model to mandate " + EMDASH + " your complimentary C-BIQ", { x: 0.4, y: 0.72, w: 9, h: 0.5, fontSize: 24, fontFace: FH, color: C.white, bold: true, margin: 0 });
  const acts = [
    ["FRAME", "Agree the board questions and a " + WORD + " risk-appetite line with " + cust + "'s CISO/CFO (one workshop)."],
    ["CALIBRATE", "Replace the illustrative inputs with revenue-per-hour, incident history and the insurance tower " + EMDASH + " recompute ALE/PML."],
    ["SEQUENCE", "Fund the controls in staged order, leading with the largest buy-back (" + (d.remediationSuite || "Colt PSF + managed services") + ")."],
    ["WATCH", "Stand up continuous external re-scan so the number stays live, not a point-in-time snapshot."],
  ];
  let ay = 1.55; const ah = 0.84;
  acts.forEach(a => {
    const owner = a[0], body = a[1];
    s.addShape(R(), { x: 0.4, y: ay, w: 9.3, h: ah - 0.12, fill: { color: "0A4640" }, line: { type: "none" } });
    s.addShape(R(), { x: 0.4, y: ay, w: 0.08, h: ah - 0.12, fill: { color: C.teal }, line: { type: "none" } });
    s.addShape(R(), { x: 0.6, y: ay + 0.16, w: 1.7, h: 0.40, fill: { color: C.teal }, line: { type: "none" } });
    s.addText(owner, { x: 0.6, y: ay + 0.16, w: 1.7, h: 0.40, fontSize: 8.5, fontFace: FB, color: C.black, bold: true, align: "center", valign: "middle", charSpacing: 1, margin: 0 });
    s.addText(body, { x: 2.5, y: ay, w: 7.05, h: ah - 0.12, fontSize: 9.5, fontFace: FB, color: C.white, valign: "middle", margin: 0 });
    ay += ah;
  });
  s.addText(CAVEAT, { x: 0.4, y: 5.30, w: 7.4, h: 0.22, fontSize: 8, fontFace: FB, color: C.teal, italic: true, charSpacing: 1, valign: "middle", margin: 0 });
  s.addText("colt", { x: 8.9, y: 5.28, w: 1.0, h: 0.28, fontSize: 12, fontFace: FA, color: C.white, bold: true, align: "right", margin: 0 });
}

// ---------- build ----------
// SLIDE -- LOSS SCENARIOS + REAL PRECEDENTS (every priced finding, matched to a recorded breach)
function lossScenariosSlide() {
  const s = content("Loss scenarios " + EMDASH + " real precedents",
                    "Every priced finding, matched to a recorded public breach");
  const priced = findings.filter(f => f.id && f.id !== "—").slice(0, 5);
  if (!priced.length) {
    s.addText("No CRIT/HIGH findings to price.", { x: 0.4, y: 2.5, w: 9, h: 0.4,
      fontSize: 12, fontFace: FB, color: C.inkMuted, margin: 0 });
    return;
  }
  const cols = [0.62, 5.06, 4.12], X = 0.4, y = 1.36, hH = 0.28;
  const clip = (t, n) => { t = String(t || ""); return t.length > n ? t.slice(0, n - 1) + "…" : t; };
  const rows = priced.map(f => [
    { text: f.id || "", bold: true, color: (TIER[f.tier] || TIER.LOW)[1] || C.tealDark, align: "center" },
    { text: clip(f.lossScenario || f.label, 200), fs: 7.6 },
    { text: clip(f.realComparable, 150), color: C.crit, bold: true, fs: 7.6 },
  ]);
  const rowH = Math.max(0.62, Math.min(0.86, 3.5 / rows.length));
  drawTable(s, X, y, cols, ["ID", "LOSS SCENARIO " + EMDASH + " what actually happens", "REAL PRECEDENT " + EMDASH + " recorded public loss"],
            rows, { rowH, hH, fs: 7.6, hfs: 7.2 });
  s.addText("Precedents are real, dated, public incidents in adjacent sectors " + EMDASH + " not model output. They calibrate the loss magnitudes above.",
    { x: 0.4, y: 4.98, w: 9.4, h: 0.3, fontSize: 7.8, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
}

titleSlide();          // 1
dividerSlide();        // 2
threeNumbersSlide();   // 3
standardsSlide();      // 4
engineSlide();         // 5
fairMathSlide();       // 6
lecSlide();            // 7
distSlide();           // 8
bucketsSlide();        // 9
rosiSlide();           // 10
pricedTableSlide();    // 11
lossScenariosSlide();  // 12  (NEW: loss scenario + real precedent per finding)
workedExampleSlide();  // 13
closerSlide();         // 14

pres.writeFile({ fileName: OUT })
  .then(fn => console.log("WROTE " + fn + "  slides: " + pageNum))
  .catch(e => { console.error(e); process.exit(1); });
