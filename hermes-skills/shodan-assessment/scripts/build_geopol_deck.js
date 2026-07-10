#!/usr/bin/env node
/* Colt-branded GEOPOL (geo-political / threat-actor) deck generator (data-driven).
   Layout ported VERBATIM from the hand-authored VIP builder (build_rosneft_de_geopol.js)
   and sharing the exact helper style / palette / fonts with build_findings_deck.js so all
   three decks match: palette C{}, fonts FH/FB/FM/FD/FA, corner()/bigChevrons()/tracer()/
   footer()/pageHeader()/content(), tierBadge()/pill()/evBlock()/drawTable(), the TITLE slide,
   EXECUTIVE VERDICT (tier-count cards), METHODOLOGY STACK, GEOPOLITICAL EXPOSURE MAP,
   THREAT LANDSCAPE AT-A-GLANCE, band section dividers, the per-actor two-column card,
   PROBABILITY INDEX, KILL-CHAIN, BUSINESS-IMPACT LINKAGE (C-BIQ) and CAVEATS & CONFIDENCE.

   Usage: node build_geopol_deck.js <geopol.json> [out.pptx]

   geopol.json schema (kept consuming; degrades gracefully if fields missing):
   { customer, date, classification, frameworks:[], shelfLifeMonths, verdict?,
     exposureMap:[{driver,attracts,why}], sectorContext, likelihoodBands,
     actors:[{ band, sponsor, tier, eyebrow, title, pills:[], what:[], evidence:[], why,
               refs, admiraltyGrade, score:{intent,capability,exposureFit}, likelihood12mo,
               linkedFindingId, rem:[{tag,title,body}] }],
     killChain:{ scenarioTitle, steps:[] },
     cbiqBridge:[{ scenario, ale, pml, note, linkedFindingId }] }

   NB: typographic glyphs (em-dash, middot, bullet, chevron, x, arrow) are emitted via \u
   escapes so this source survives cross-platform writes intact. Hex colours WITHOUT '#'. */

const fs = require("fs");
const pptxgen = require("pptxgenjs");

// ---- typographic glyphs (avoid raw multibyte literals in source) ----
const EMDASH = "—"; // --
const MIDDOT = "·"; // middot
const BULLET = "•"; // bullet char
const RAQUO  = "»"; // >>
const TIMES  = "×"; // x
const ARROW  = "→"; // ->
const CHEV   = "❯"; // heavy right chevron (wordmark)
const APPROX = "≈"; // approx equals

// ---------- input ----------
const DATA = process.argv[2] || "geopol.json";
let d = {};
try { d = JSON.parse(fs.readFileSync(DATA, "utf8")); }
catch (e) { console.error("Cannot read/parse " + DATA + ": " + e.message); process.exit(1); }

const cust = d.customer || "Target";
const CUST_UP = String(cust).toUpperCase();
const OUT = process.argv[3] ||
  "./" + String(cust).replace(/[^A-Za-z0-9]+/g, "_") + "_GEOPOL_Assessment_Internal.pptx";

// loose-JSON coercion helpers
const asLines = v => Array.isArray(v) ? v.filter(x => x != null).map(String)
  : (v == null || v === "" ? [] : [String(v)]);
const asText = v => Array.isArray(v) ? v.filter(x => x != null).map(String).join(" ")
  : (v == null ? "" : String(v));

// ---------- presentation ----------
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625"
pres.author = "Colt / S4Biz Sales Engineering";
pres.title = cust + " " + EMDASH + " GEOPOL Cyber Threat Assessment";

// ---- Palette (COLT_DESIGN_SYSTEM.md 1.4) -- copied verbatim from VIP builder ----
const C = {
  teal: "00D7BD", tealMid: "00A49A", tealDark: "0C544E",
  black: "121212", dark: "474946", light: "ECECED",
  crit: "F20C36", high: "FF7900", med: "FFC33C", low: "474946",
  ink: "1A1A1A", inkMuted: "5B6470", divider: "D8D6CF", white: "FFFFFF",
  evBg: "0C544E", evInk: "ECECED", green: "1E9E6A", gold: "F7C844",
};
const FH = "Georgia", FB = "Calibri", FM = "Consolas", FD = "Arial Black", FA = "Arial";

const FOOT = "INTERNAL " + EMDASH + " COLT / S4BIZ CONFIDENTIAL " + MIDDOT +
  " NOT FOR EXTERNAL DISTRIBUTION " + MIDDOT + " STRATEGIC CTI";
const CLASS = (d.classification || "INTERNAL " + EMDASH + " CONFIDENTIAL").toUpperCase();
const R = () => pres.shapes.RECTANGLE;

const BANDS = ["NATION-STATE", "STATE-ALIGNED", "ORGANISED eCRIME", "HACKTIVIST"];
const TIER_RANK = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

// ---- group actors by band (fixed order) ----
const actors = Array.isArray(d.actors) ? d.actors : [];
// BUG 3 FIX: compare uppercased-to-uppercased. "ORGANISED eCRIME".toUpperCase() is
// "ORGANISED ECRIME", so matching against the raw literal ("...eCRIME") silently dropped
// every eCrime actor. Uppercase BOTH sides so the band grouping is exact.
const byBand = Object.fromEntries(BANDS.map(b =>
  [b, actors.filter(a => String(a.band || "").toUpperCase() === b.toUpperCase())]));

// ---- TOTAL page count, computed up-front so the tracer reads N / TOTAL correctly ----
// 1 title + 1 verdict + 1 methodology + 1 exposure map + 1 landscape
// + per band present: 1 divider + N actor cards
// + probability index + kill-chain + C-BIQ bridge + caveats
let TOTAL = 5;
if (d.anchorCase) TOTAL += 1; // anchor case slide
for (const b of BANDS) if (byBand[b].length) TOTAL += 1 + byBand[b].length;
TOTAL += 4;

let pageNum = 0;

// ---------- chrome helpers (from VIP builder) ----------
function corner(s, color) {
  s.addText("colt", { x: 9.10, y: 0.18, w: 0.8, h: 0.32, fontSize: 18, fontFace: FA,
    color, bold: true, align: "right", margin: 0 });
}
function bigChevrons(s, o = {}) {
  const x = o.x ?? 0.5, w = o.w ?? 9.0, yStart = o.yStart ?? 0.20,
    triH = o.triH ?? 1.55, gap = o.gap ?? 0.30, color = o.color || C.white, op = o.opacity;
  for (let i = 0; i < 3; i++) {
    const cfg = { x, y: yStart + i * (triH + gap), w, h: triH, fill: { color }, line: { type: "none" } };
    if (op !== undefined) cfg.fill = { color, transparency: Math.round((1 - op) * 100) };
    s.addShape(pres.shapes.ISOSCELES_TRIANGLE, cfg);
  }
}
function tracer(s, color = C.tealDark) {
  for (let i = 0; i < 3; i++)
    s.addShape(pres.shapes.RIGHT_TRIANGLE, { x: 8.30 + i * 0.14, y: 5.34, w: 0.11, h: 0.16,
      fill: { color }, line: { type: "none" }, rotate: 90 });
  s.addText(RAQUO + RAQUO + " " + pageNum + "/" + TOTAL, { x: 8.62, y: 5.28, w: 1.23, h: 0.28,
    fontSize: 9, fontFace: FB, color, bold: true, align: "right", valign: "middle", margin: 0 });
}
function footer(s) {
  s.addText(FOOT, { x: 0.4, y: 5.34, w: 8.0, h: 0.2, fontSize: 7, fontFace: FB,
    color: C.inkMuted, charSpacing: 1, margin: 0, valign: "middle" });
}
function pageHeader(s, eyebrow, title) {
  s.addText(String(eyebrow || "").toUpperCase(), { x: 0.4, y: 0.22, w: 8.2, h: 0.22,
    fontSize: 9, fontFace: FB, color: C.teal, charSpacing: 3, bold: true, margin: 0 });
  s.addText(String(title || ""), { x: 0.4, y: 0.44, w: 8.6, h: 0.82, fontSize: 18, fontFace: FH,
    color: C.tealDark, bold: true, valign: "top", margin: 0 });
  corner(s, C.tealDark);
}
// content() factory: a blank branded content slide (+ footer/tracer)
function content(eyebrow, title) {
  pageNum++; const s = pres.addSlide(); s.background = { color: C.white };
  pageHeader(s, eyebrow, title); footer(s); tracer(s); return s;
}

// rect-based branded table (VIP drawTable)
function drawTable(s, x, y, colW, headers, rows, o = {}) {
  const rowH = o.rowH || 0.30, hH = o.hH || 0.28, fs = o.fs || 8, hfs = o.hfs || 7.6;
  let cx = x;
  headers.forEach((h, i) => {
    s.addShape(R(), { x: cx, y, w: colW[i], h: hH, fill: { color: C.tealDark }, line: { type: "none" } });
    s.addText(h, { x: cx + 0.06, y, w: colW[i] - 0.12, h: hH, fontSize: hfs, fontFace: FB, bold: true,
      color: C.white, charSpacing: 1, valign: "middle", margin: 0 }); cx += colW[i];
  });
  rows.forEach((r, ri) => {
    const ry = y + hH + ri * rowH; cx = x;
    r.forEach((cell, i) => {
      const cl = (cell && typeof cell === "object") ? cell : { text: cell };
      const fill = cl.fill || (ri % 2 ? C.light : C.white);
      s.addShape(R(), { x: cx, y: ry, w: colW[i], h: rowH, fill: { color: fill }, line: { type: "none" } });
      s.addText(String(cl.text == null ? "" : cl.text), { x: cx + 0.06, y: ry, w: colW[i] - 0.12, h: rowH,
        fontSize: cl.fs || fs, fontFace: cl.mono ? FM : FB, bold: cl.bold, color: cl.color || C.ink,
        align: cl.align, valign: "middle", margin: 0, lineSpacingMultiple: 0.9 }); cx += colW[i];
    });
  });
}
function tierBadge(s, tier, x, y, w = 1.05) {
  const map = { CRITICAL: [C.crit, C.white], HIGH: [C.high, C.white], MEDIUM: [C.med, "121212"], LOW: [C.low, C.white] };
  const [bg, fg] = map[tier] || map.LOW;
  s.addShape(R(), { x, y, w, h: 0.28, fill: { color: bg }, line: { type: "none" } });
  s.addText(tier, { x, y, w, h: 0.28, fontSize: 9.5, fontFace: FB, color: fg, bold: true,
    align: "center", valign: "middle", charSpacing: 1, margin: 0 });
}
function pill(s, t, x, y, w) {
  s.addShape(R(), { x, y, w, h: 0.25, fill: { color: C.light }, line: { type: "none" } });
  s.addText(t, { x, y, w, h: 0.25, fontSize: 8, fontFace: FB, color: C.tealDark, bold: true,
    align: "center", valign: "middle", charSpacing: 1, margin: 0 });
}
function evBlock(s, lines, x, y, w, h) {
  lines = (lines && lines.length) ? lines : ["(no evidence recorded)"];
  lines = lines.slice(0, 9);
  s.addShape(R(), { x, y, w, h, fill: { color: C.evBg }, line: { type: "none" } });
  s.addShape(R(), { x, y, w: 0.05, h, fill: { color: C.teal }, line: { type: "none" } });
  s.addText(lines.map((l, i) => ({ text: l, options: { breakLine: i < lines.length - 1,
    fontSize: 7.2, fontFace: FM, color: C.evInk } })),
    { x: x + 0.12, y: y + 0.05, w: w - 0.18, h: h - 0.10, valign: "top", margin: 0 });
}
// tagMap: VENDOR->orange, COLT->teal, PSF->tealDark, OSS->dark grey
const tagMap = { VENDOR: [C.high, C.white], COLT: [C.teal, "121212"], PSF: [C.tealDark, C.white], OSS: [C.dark, C.white] };

// band section divider (big Arial-Black word, coloured by highest tier in band)
function bandColor(acts) {
  const map = { CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, LOW: C.low };
  let rank = 0, color = C.low;
  acts.forEach(a => { const t = String(a.tier || "LOW").toUpperCase();
    const r = TIER_RANK[t] || 1; if (r > rank) { rank = r; color = map[t] || C.low; } });
  return color;
}
function divider(label, bgColor) {
  pageNum++; const s = pres.addSlide(); s.background = { color: bgColor };
  const light = bgColor === C.med; // gold/med is light -> use black ink
  const fg = light ? C.black : C.white;
  bigChevrons(s, { x: 0.5, w: 9.0, yStart: 0.10, triH: 1.55, gap: 0.30, color: C.white, opacity: 0.15 });
  s.addText(label + ".", { x: 0, y: 1.95, w: 10, h: 1.5, fontSize: 54, fontFace: FD,
    color: fg, bold: true, align: "center", valign: "middle", margin: 0 });
  corner(s, fg); tracer(s, fg);
  return s;
}

// relevance % helper (Intent x Capability x Exposure-fit, each 1-10 -> /1000)
function relevancePct(a) {
  const sc = a.score || {}; const i = sc.intent || 0, c = sc.capability || 0, e = sc.exposureFit || 0;
  if (!i && !c && !e) return EMDASH;
  return Math.round((i * c * e) / 1000 * 100) + "";
}

// ---------- ACTOR CARD (VIP two-column layout) ----------
function actorCard(a) {
  const tier = String(a.tier || "LOW").toUpperCase();
  const band = String(a.band || "").toUpperCase();
  const s = content(band + " " + MIDDOT + " " + (a.sponsor || "") + " " + MIDDOT + " " + tier, a.title || a.name || "Threat actor");
  tierBadge(s, tier, 0.4, 1.30);
  s.addText(String(a.eyebrow || band || "").toUpperCase(), { x: 1.55, y: 1.30, w: 4.0, h: 0.28,
    fontSize: 8.2, fontFace: FB, color: C.inkMuted, charSpacing: 2, bold: true, valign: "middle", margin: 0 });
  let px = 9.72; for (const p of (a.pills || []).slice(0, 3).slice().reverse()) { px -= 1.34; pill(s, p, px, 1.31, 1.28); }

  // left col: adversary & capability + evidence
  s.addShape(R(), { x: 0.4, y: 1.72, w: 0.07, h: 0.24, fill: { color: C.crit }, line: { type: "none" } });
  s.addText("ADVERSARY & CAPABILITY", { x: 0.54, y: 1.72, w: 4.5, h: 0.24, fontSize: 10, fontFace: FB,
    color: C.ink, bold: true, charSpacing: 1, valign: "middle", margin: 0 });
  s.addText("WHO THEY ARE " + MIDDOT + " TTPs (MITRE ATT&CK)", { x: 0.4, y: 2.02, w: 4.6, h: 0.2,
    fontSize: 8.2, fontFace: FB, color: C.teal, bold: true, charSpacing: 1, margin: 0 });
  const what = asLines(a.what);
  s.addText((what.length ? what : [EMDASH]).map((tt, i) => ({ text: tt,
    options: { breakLine: i < what.length - 1, fontSize: 8.4, fontFace: FB, color: C.ink } })),
    { x: 0.4, y: 2.22, w: 4.6, h: 1.02, valign: "top", margin: 0, paraSpaceAfter: 2 });
  s.addText("EVIDENCE " + MIDDOT + " NAMED CAMPAIGN " + MIDDOT + " ADMIRALTY GRADE", { x: 0.4, y: 3.28, w: 4.6, h: 0.2,
    fontSize: 8.0, fontFace: FB, color: C.teal, bold: true, charSpacing: 1, margin: 0 });
  evBlock(s, asLines(a.evidence), 0.4, 3.48, 4.6, 1.42);

  // right col: why + references + rem chips
  s.addShape(R(), { x: 5.15, y: 1.72, w: 0.07, h: 0.24, fill: { color: C.teal }, line: { type: "none" } });
  s.addText("WHY " + CUST_UP + " " + MIDDOT + " WHAT STOPS THEM", { x: 5.29, y: 1.72, w: 4.4, h: 0.24,
    fontSize: 10, fontFace: FB, color: C.ink, bold: true, charSpacing: 1, valign: "middle", margin: 0 });
  s.addText("RELEVANCE " + EMDASH + " THE EXPOSURE FIT", { x: 5.15, y: 2.02, w: 4.6, h: 0.2,
    fontSize: 8.2, fontFace: FB, color: C.teal, bold: true, charSpacing: 1, margin: 0 });
  s.addText(asText(a.why) || EMDASH, { x: 5.15, y: 2.22, w: 4.6, h: 0.92, fontSize: 8.4, fontFace: FB,
    color: C.ink, valign: "top", margin: 0, lineSpacingMultiple: 1.02 });
  s.addText("REFERENCES", { x: 5.15, y: 3.16, w: 4.6, h: 0.2, fontSize: 8.0, fontFace: FB,
    color: C.teal, bold: true, charSpacing: 1, margin: 0 });
  s.addText(asText(a.refs) || EMDASH, { x: 5.15, y: 3.34, w: 4.6, h: 0.22, fontSize: 7.4, fontFace: FB,
    color: C.inkMuted, italic: true, margin: 0 });
  const startY = 3.62, rowH = 0.43;
  (a.rem || []).slice(0, 3).forEach((r, i) => {
    const y = startY + i * rowH; const [bg, fg] = tagMap[String(r.tag || "").toUpperCase()] || tagMap.COLT;
    s.addShape(R(), { x: 5.15, y, w: 0.72, h: 0.24, fill: { color: bg }, line: { type: "none" } });
    s.addText(String(r.tag || "COLT").toUpperCase(), { x: 5.15, y, w: 0.72, h: 0.24, fontSize: 8,
      fontFace: FB, bold: true, color: fg, align: "center", valign: "middle", margin: 0 });
    s.addText(r.title || "", { x: 5.95, y: y - 0.01, w: 3.78, h: 0.22, fontSize: 8.3, fontFace: FB,
      color: C.ink, bold: true, valign: "middle", margin: 0 });
    s.addText(r.body || "", { x: 5.95, y: y + 0.20, w: 3.78, h: 0.22, fontSize: 7.4, fontFace: FB,
      color: C.inkMuted, valign: "top", margin: 0 });
  });

  // meta strip (admiralty / linked finding / P(12mo)) bottom-left
  const meta = [];
  if (a.admiraltyGrade) meta.push("Admiralty " + a.admiraltyGrade);
  if (a.linkedFindingId) meta.push(ARROW + " " + a.linkedFindingId);
  if (a.likelihood12mo) meta.push("P(12mo): " + a.likelihood12mo);
  if (meta.length) s.addText(meta.join("   " + MIDDOT + "   "), { x: 0.4, y: 5.06, w: 4.7, h: 0.2,
    fontSize: 6.8, fontFace: FM, color: C.inkMuted, margin: 0 });
  return s;
}

// ============================================================ 1 TITLE
pageNum++;
(function () {
  const s = pres.addSlide(); s.background = { color: C.teal };
  bigChevrons(s, { x: 5.8, w: 5.0, yStart: 0.05, triH: 2.0, gap: 0.05, color: C.white });
  corner(s, "121212");
  s.addText("GEO-POLITICAL CYBER THREAT ASSESSMENT " + MIDDOT + " GEOPOL",
    { x: 0.5, y: 1.05, w: 8.7, h: 0.3, fontSize: 11, fontFace: FA, color: "121212", bold: true, charSpacing: 2, margin: 0 });
  s.addText("WHO IS COMING,", { x: 0.5, y: 1.42, w: 8.8, h: 1.0, fontSize: 44, fontFace: FD, color: "121212", bold: true, margin: 0 });
  s.addText("AND WHY US.", { x: 0.5, y: 2.32, w: 8.8, h: 1.0, fontSize: 44, fontFace: FD, color: "121212", bold: true, margin: 0 });
  s.addShape(R(), { x: 0.57, y: 3.22, w: 0.22, h: 0.22, fill: { color: C.gold }, line: { type: "none" } });
  s.addText(cust + " " + EMDASH + " named adversaries, motives, methods and a probability index.",
    { x: 0.9, y: 3.18, w: 8.4, h: 0.4, fontSize: 12.5, fontFace: FA, color: "121212", italic: true, margin: 0 });
  s.addShape(R(), { x: 0, y: 4.5, w: 10, h: 1.12, fill: { color: C.tealDark }, line: { type: "none" } });
  const fw = (d.frameworks && d.frameworks.length) ? d.frameworks.join(" " + MIDDOT + " ")
    : "MITRE ATT&CK " + MIDDOT + " Diamond " + MIDDOT + " Kill-Chain " + MIDDOT + " Admiralty";
  const md = [
    ["SCOPE", cust],
    ["FRAMEWORKS", fw],
    ["DATE", d.date || new Date().toISOString().slice(0, 10)],
    ["CLASSIFICATION", CLASS],
  ];
  const ws = [2.4, 3.0, 1.4, 2.4]; let mx = 0.5;
  md.forEach((m, i) => {
    s.addText(m[0], { x: mx, y: 4.64, w: ws[i], h: 0.22, fontSize: 8, fontFace: FB, color: C.teal, bold: true, charSpacing: 1, margin: 0 });
    s.addText(m[1], { x: mx, y: 4.86, w: ws[i], h: 0.62, fontSize: 8.5, fontFace: FB, color: C.white, valign: "top", margin: 0 }); mx += ws[i] + 0.05;
  });
  const shelf = d.shelfLifeMonths ? ("~" + d.shelfLifeMonths + "-month shelf life.") : "~6-month shelf life.";
  s.addText("Strategic intelligence " + EMDASH + " states who could and would, with sourced rationale and graded confidence. Not a prediction. " + shelf,
    { x: 0.5, y: 5.42, w: 9.0, h: 0.2, fontSize: 6.6, fontFace: FB, color: "121212", margin: 0 });
})();

// ============================================================ 2 EXECUTIVE VERDICT
(function () {
  const s = content("Executive Verdict", "The threat picture in one glance");
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  actors.forEach(a => { const t = String(a.tier || "LOW").toUpperCase(); if (counts[t] != null) counts[t]++; });
  const verdict = asText(d.verdict) || (cust + " sits at the intersection of state-strategic interest and financially-motivated eCrime. "
    + (counts.CRITICAL + counts.HIGH) + " actor(s) rate HIGH or above on relevance. The dominant near-term risk is disruptive/extortion operations against exposed edge infrastructure.");
  s.addText(verdict, { x: 0.4, y: 1.30, w: 9.3, h: 1.20, fontSize: 10, fontFace: FB, color: C.ink, valign: "top", margin: 0, lineSpacingMultiple: 1.03 });
  const cards = [["CRITICAL", counts.CRITICAL, C.crit, C.white], ["HIGH", counts.HIGH, C.high, C.white],
    ["MEDIUM", counts.MEDIUM, C.med, "121212"], ["ACTORS", actors.length, C.tealDark, C.white]];
  let cx = 0.4; const cw = 2.18, cg = 0.20;
  cards.forEach(([lab, n, bg, fg]) => {
    s.addShape(R(), { x: cx, y: 2.62, w: cw, h: 0.98, fill: { color: bg }, line: { type: "none" } });
    s.addText(String(n), { x: cx, y: 2.70, w: cw, h: 0.58, fontSize: 34, fontFace: FH, color: fg, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(lab === "ACTORS" ? "PROFILED" : lab, { x: cx, y: 3.26, w: cw, h: 0.26, fontSize: 9, fontFace: FB, color: fg, bold: true, align: "center", charSpacing: 1, margin: 0 }); cx += cw + cg;
  });
  s.addText("PRIORITY ADVERSARIES", { x: 0.4, y: 3.78, w: 9, h: 0.22, fontSize: 9, fontFace: FB, color: C.teal, bold: true, charSpacing: 3, margin: 0 });
  // top 3 actors by tier rank then title
  const ranked = actors.slice().sort((a, b) =>
    (TIER_RANK[String(b.tier || "LOW").toUpperCase()] || 1) - (TIER_RANK[String(a.tier || "LOW").toUpperCase()] || 1));
  const heads = ranked.slice(0, 3).map(a => {
    const tier = String(a.tier || "LOW").toUpperCase();
    const title = (a.title || a.name || "Actor") + " " + EMDASH + " " + tier;
    const body = asText(a.why) || (asLines(a.what)[0] || "");
    return [title, String(body).slice(0, 150)];
  });
  let hy = 4.04;
  heads.forEach(([tt, b]) => {
    s.addShape(R(), { x: 0.4, y: hy, w: 0.07, h: 0.44, fill: { color: C.teal }, line: { type: "none" } });
    s.addText(tt, { x: 0.55, y: hy, w: 9.1, h: 0.22, fontSize: 9.5, fontFace: FB, color: C.tealDark, bold: true, margin: 0 });
    s.addText(b, { x: 0.55, y: hy + 0.21, w: 9.1, h: 0.22, fontSize: 8.5, fontFace: FB, color: C.inkMuted, margin: 0 }); hy += 0.50;
  });
})();

// ============================================================ 3 METHODOLOGY STACK
(function () {
  const s = content("Methodology Stack", "Composed from established, citable frameworks " + EMDASH + " not invented");
  const col = (x, w, title, items, col2) => {
    s.addShape(R(), { x, y: 1.36, w, h: 0.34, fill: { color: col2 || C.tealDark }, line: { type: "none" } });
    s.addText(title, { x: x + 0.1, y: 1.36, w: w - 0.2, h: 0.34, fontSize: 9, fontFace: FB, bold: true, color: C.white, charSpacing: 1, valign: "middle", margin: 0 });
    s.addText(items.map((tt, i) => ({ text: tt, options: { breakLine: i < items.length - 1, fontSize: 8.2, fontFace: FB, color: C.ink } })),
      { x: x + 0.02, y: 1.80, w: w - 0.05, h: 2.6, valign: "top", margin: 0, paraSpaceAfter: 3, bullet: { code: "2022", indent: 11 } });
  };
  col(0.4, 3.0, "ANALYTICAL (RIGOR)",
    ["MITRE ATT&CK " + EMDASH + " TTP taxonomy", "Diamond Model " + EMDASH + " intrusion analysis",
     "Lockheed Kill Chain " + EMDASH + " attack spine", "ACH + Heuer " + EMDASH + " bias control",
     "Pyramid of Pain " + EMDASH + " TTP-led defence"]);
  col(3.55, 3.0, "TRIAGE & CONFIDENCE",
    ["CVSS + EPSS + CISA KEV " + EMDASH + " exploit triage", "Admiralty (NATO AJP-2.1) " + EMDASH + " A" + EMDASH + "F " + TIMES + " 1" + EMDASH + "6",
     "FAIR " + EMDASH + " bridge to euro loss (C-BIQ)", "Relevance tier = Intent " + TIMES + " Capability " + TIMES,
     "  Exposure-fit " + ARROW + " C/H/M/L"]);
  col(6.70, 3.0, "RED-TEAM BRIDGE",
    ["TIBER-EU (ECB) " + MIDDOT + " DORA TLPT", "TISAX " + MIDDOT + " UNECE R155 (automotive)",
     "BSI / BaFin " + MIDDOT + " ENISA " + MIDDOT + " NIS2", "CBEST " + MIDDOT + " CISA KEV + advisories",
     "GEOPOL " + ARROW + " intel-led test (the sale)"], C.tealMid);
  s.addShape(R(), { x: 0.4, y: 4.62, w: 9.3, h: 0.6, fill: { color: C.light }, line: { type: "none" } });
  s.addShape(R(), { x: 0.4, y: 4.62, w: 0.07, h: 0.6, fill: { color: C.teal }, line: { type: "none" } });
  s.addText([{ text: "Three layers:  ", options: { bold: true, color: C.tealDark } },
    { text: "Shodan says what's open " + MIDDOT + " C-BIQ says what it costs " + MIDDOT + " ", options: { color: C.ink } },
    { text: "GEOPOL says who's coming and why.", options: { bold: true, color: C.tealDark } }],
    { x: 0.6, y: 4.62, w: 9.0, h: 0.6, fontSize: 9.5, fontFace: FB, valign: "middle", margin: 0 });
})();

// ============================================================ 4 GEOPOLITICAL EXPOSURE MAP
(function () {
  const s = content("Geopolitical Exposure Map", "Why " + cust + " is targeted " + EMDASH + " drivers + named entities");
  const em = (d.exposureMap || []);
  const rows = (em.length ? em : [{ driver: EMDASH, attracts: EMDASH, why: EMDASH }]).map(r => [
    { text: r.driver || EMDASH, bold: true, color: C.tealDark, fs: 7.6 }, { text: r.attracts || EMDASH, fs: 7.6 }, { text: r.why || EMDASH, fs: 7.4 },
  ]);
  drawTable(s, 0.4, 1.30, [2.3, 3.3, 3.7], ["DRIVER", "WHO IT ATTRACTS", "WHY"], rows,
    { rowH: 0.52, hH: 0.26, fs: 7.6, hfs: 7.4 });
  // per-jurisdiction / named-entity table (§F): Jurisdiction | Entity | Distinct exposure
  const ent = (d.exposureEntities || []);
  const eb = 1.30 + 0.26 + rows.length * 0.52 + 0.18;
  s.addText("PER-JURISDICTION EXPOSURE " + EMDASH + " NAMED ENTITIES", { x: 0.4, y: eb, w: 9.3, h: 0.2,
    fontSize: 8.5, fontFace: FB, bold: true, color: C.teal, charSpacing: 2, margin: 0 });
  const erows = (ent.length ? ent : [{ jurisdiction: EMDASH, entity: EMDASH, exposure: EMDASH }]).map(r => [
    { text: r.jurisdiction || EMDASH, bold: true, color: C.tealDark, align: "center", fs: 8 },
    { text: r.entity || EMDASH, bold: true, color: C.ink, fs: 7.6 },
    { text: r.exposure || EMDASH, color: C.inkMuted, fs: 7.4 },
  ]);
  drawTable(s, 0.4, eb + 0.24, [1.1, 3.0, 5.2], ["JURISDICTION", "ENTITY", "DISTINCT EXPOSURE"], erows,
    { rowH: 0.42, hH: 0.26, fs: 7.6, hfs: 7.2 });
})();

// ============================================================ 4b ANCHOR CASE
(function () {
  const ac = d.anchorCase;
  if (!ac) return;
  const s = content("Anchor Case", ac.title || "The sourced intrusion this report is built around");
  // headline strip: actor / sponsor / admiralty grade
  s.addShape(R(), { x: 0.4, y: 1.30, w: 9.3, h: 0.5, fill: { color: C.evBg }, line: { type: "none" } });
  s.addShape(R(), { x: 0.4, y: 1.30, w: 0.06, h: 0.5, fill: { color: C.crit }, line: { type: "none" } });
  s.addText([
    { text: (ac.actor || EMDASH) + "   ", options: { bold: true, color: C.teal } },
    { text: (ac.sponsor ? (MIDDOT + " " + ac.sponsor + "   ") : ""), options: { color: C.evInk } },
    { text: (ac.admiraltyGrade ? (MIDDOT + " Admiralty " + ac.admiraltyGrade) : ""), options: { color: C.evInk, italic: true } },
  ], { x: 0.58, y: 1.30, w: 9.0, h: 0.5, fontSize: 9, fontFace: FB, valign: "middle", margin: 0 });
  s.addText(asText(ac.summary), { x: 0.4, y: 1.92, w: 9.3, h: 0.82, fontSize: 9, fontFace: FB,
    color: C.ink, valign: "top", margin: 0, lineSpacingMultiple: 1.03 });
  // phased ACCESS -> PERSIST -> COLLECT -> EXFIL, tied to finding IDs
  const phases = Array.isArray(ac.phases) ? ac.phases : [];
  let y = 2.86; const h = 0.5;
  phases.slice(0, 4).forEach((p, i) => {
    const last = i === phases.length - 1;
    s.addShape(R(), { x: 0.4, y, w: 1.7, h: h - 0.08, fill: { color: last ? C.crit : C.tealDark }, line: { type: "none" } });
    s.addText(String(p.phase || ("STEP " + (i + 1))).toUpperCase(), { x: 0.4, y, w: 1.7, h: h - 0.08,
      fontSize: 9.5, fontFace: FB, bold: true, color: C.white, align: "center", valign: "middle", charSpacing: 1, margin: 0 });
    s.addText(asText(p.body), { x: 2.25, y, w: 6.2, h: h - 0.08, fontSize: 8.4, fontFace: FB, color: C.ink, valign: "middle", margin: 0 });
    if (p.linkedFindingId) s.addText(ARROW + " " + p.linkedFindingId, { x: 8.55, y, w: 1.15, h: h - 0.08,
      fontSize: 8, fontFace: FM, bold: true, color: C.tealDark, align: "right", valign: "middle", margin: 0 });
    y += h;
  });
  if (ac.refs) s.addText([{ text: "Sources:  ", options: { bold: true, color: C.tealDark } },
    { text: asText(ac.refs), options: { color: C.inkMuted, italic: true } }],
    { x: 0.4, y: 5.0, w: 9.3, h: 0.24, fontSize: 8, fontFace: FB, margin: 0 });
})();

// ============================================================ 5 THREAT LANDSCAPE AT A GLANCE
(function () {
  const s = content("Threat Landscape At A Glance", "The named adversaries selected for this target");
  const sevC = { CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, LOW: C.low };
  const hd = ["TIER", "ACTOR / CRYPTONYM", "SPONSOR", "HEADLINE", "RELEVANCE"];
  const rows = actors.map(a => {
    const tier = String(a.tier || "LOW").toUpperCase();
    const headline = (asLines(a.what)[0] || a.eyebrow || "");
    return [tier, a.title || a.name || "", a.sponsor || a.band || "", String(headline).slice(0, 58), relevancePct(a)];
  });
  let y = 1.34; const hH = 0.30, rowH = 0.375;
  const cols = [0.62, 2.35, 1.85, 2.95, 1.83]; const X = 0.4;
  let cx = X; hd.forEach((h, i) => { s.addShape(R(), { x: cx, y, w: cols[i], h: hH, fill: { color: C.tealDark }, line: { type: "none" } }); s.addText(h, { x: cx + 0.05, y, w: cols[i] - 0.08, h: hH, fontSize: 7.4, fontFace: FB, bold: true, color: C.white, valign: "middle", margin: 0 }); cx += cols[i]; });
  (rows.length ? rows : [[EMDASH, EMDASH, EMDASH, EMDASH, EMDASH]]).forEach((r, ri) => {
    const ry = y + hH + ri * rowH; cx = X;
    r.forEach((cell, i) => {
      let fill = ri % 2 ? C.light : C.white, color = C.ink, bold = false, align;
      if (i === 0) { fill = sevC[cell] || C.low; color = cell === "MEDIUM" ? "121212" : C.white; bold = true; align = "center"; }
      if (i === 4) { align = "center"; bold = true; color = C.tealDark; }
      if (i === 1) { bold = true; color = C.tealDark; }
      s.addShape(R(), { x: cx, y: ry, w: cols[i], h: rowH, fill: { color: fill }, line: { type: "none" } });
      s.addText(String(cell == null ? "" : cell), { x: cx + 0.05, y: ry, w: cols[i] - 0.08, h: rowH,
        fontSize: 7.6, fontFace: (i === 4) ? FM : FB, bold, color, align, valign: "middle", margin: 0, lineSpacingMultiple: 0.9 }); cx += cols[i];
    });
  });
  s.addText("Relevance, not fame, drives inclusion " + EMDASH + " each actor is here because of a sourced reason it would target this specific entity.",
    { x: 0.4, y: 4.95, w: 9.3, h: 0.22, fontSize: 7.8, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
})();

// ============================================================ BANDS: divider + actor cards
BANDS.forEach(band => {
  const acts = byBand[band];
  if (!acts.length) return;
  divider(band, bandColor(acts));
  acts.forEach(a => actorCard(a));
});

// ============================================================ PROBABILITY INDEX
(function () {
  const s = content("Probability Index", "Intent " + TIMES + " Capability " + TIMES + " Exposure-fit " + ARROW + " 12-month likelihood");
  const sevC = { CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, LOW: C.low };
  const hd = ["ACTOR", "INTENT", "CAPAB.", "FIT", "TIER", "12-MONTH LIKELIHOOD"];
  const rows = actors.map(a => {
    const sc = a.score || {}; const tier = String(a.tier || "LOW").toUpperCase();
    return [a.title || a.name || "", sc.intent != null ? String(sc.intent) : EMDASH,
      sc.capability != null ? String(sc.capability) : EMDASH, sc.exposureFit != null ? String(sc.exposureFit) : EMDASH,
      tier, a.likelihood12mo || EMDASH];
  });
  let y = 1.34; const hH = 0.30, rowH = 0.375;
  const cols = [2.45, 0.85, 0.85, 0.6, 0.7, 3.85]; const X = 0.4;
  let cx = X; hd.forEach((h, i) => { s.addShape(R(), { x: cx, y, w: cols[i], h: hH, fill: { color: C.tealDark }, line: { type: "none" } }); s.addText(h, { x: cx + 0.05, y, w: cols[i] - 0.08, h: hH, fontSize: 7.3, fontFace: FB, bold: true, color: C.white, valign: "middle", margin: 0 }); cx += cols[i]; });
  (rows.length ? rows : [[EMDASH, EMDASH, EMDASH, EMDASH, EMDASH, EMDASH]]).forEach((r, ri) => {
    const ry = y + hH + ri * rowH; cx = X;
    r.forEach((cell, i) => {
      let fill = ri % 2 ? C.light : C.white, color = C.ink, bold = false, align;
      if (i === 4) { fill = sevC[cell] || C.low; color = cell === "MEDIUM" ? "121212" : C.white; bold = true; align = "center"; }
      if (i === 0) { bold = true; color = C.tealDark; }
      if (i >= 1 && i <= 3) align = "center";
      s.addShape(R(), { x: cx, y: ry, w: cols[i], h: rowH, fill: { color: fill }, line: { type: "none" } });
      s.addText(String(cell == null ? "" : cell), { x: cx + 0.05, y: ry, w: cols[i] - 0.08, h: rowH,
        fontSize: 7.6, fontFace: (i >= 1 && i <= 3) ? FM : FB, bold, color, align, valign: "middle", margin: 0, lineSpacingMultiple: 0.9 }); cx += cols[i];
    });
  });
  s.addText("Intent " + MIDDOT + " Capability " + MIDDOT + " Exposure-fit each scored 1" + EMDASH + "10; tier is the composite relevance grade. House priors " + EMDASH + " stated openly so they can be re-anchored with customer data.",
    { x: 0.4, y: 4.95, w: 9.3, h: 0.24, fontSize: 7.6, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
})();

// ============================================================ KILL-CHAIN SCENARIO
(function () {
  const kc = d.killChain || {};
  const s = content("Kill-Chain Scenario", kc.scenarioTitle || "Representative kill chain");
  const steps = asLines(kc.steps).slice(0, 7);
  if (!steps.length) { s.addText("No kill-chain supplied.", { x: 0.4, y: 2.5, w: 9, h: 0.4, fontSize: 12, fontFace: FB, color: C.inkMuted, margin: 0 }); footer(s); return; }
  let y = 1.34; const h = 0.49;
  steps.forEach((st, i) => {
    let label = "STEP " + (i + 1), body = st;
    const m = /^\s*([A-Za-z0-9 &\/]+?)\s*[—\-]\s*(.+)$/.exec(st);
    if (m && m[1].length <= 28) { label = m[1].toUpperCase(); body = m[2]; }
    const isLast = i >= steps.length - 1;
    s.addShape(R(), { x: 0.4, y, w: 1.7, h: h - 0.06, fill: { color: isLast ? C.crit : C.tealDark }, line: { type: "none" } });
    s.addText(label, { x: 0.4, y, w: 1.7, h: h - 0.06, fontSize: 9, fontFace: FB, bold: true, color: C.white, align: "center", valign: "middle", charSpacing: 1, margin: 0, lineSpacingMultiple: 0.85 });
    s.addText(body, { x: 2.25, y, w: 7.45, h: h - 0.06, fontSize: 8.6, fontFace: FB, color: C.ink, valign: "middle", margin: 0, lineSpacingMultiple: 0.9 }); y += h;
  });
  s.addText("Break the chain early: ZTNA removes the exposed entry, patching removes the exploit, and segmentation + immutable backup neutralise impact.",
    { x: 0.4, y: 4.9, w: 9.3, h: 0.3, fontSize: 8.4, fontFace: FB, color: C.green, bold: true, italic: true, margin: 0 });
})();

// ============================================================ BUSINESS-IMPACT LINKAGE (C-BIQ)
(function () {
  const s = content("Business-Impact Linkage (C-BIQ)", "Top scenarios " + ARROW + " probable euro loss (FAIR bridge)");
  s.addText("GEOPOL scenarios feed the C-BIQ model: the named adversary supplies Intent, the exposure finding supplies the surface, and FAIR converts both into a euro range and a halt-of-operations cost.",
    { x: 0.4, y: 1.28, w: 9.3, h: 0.5, fontSize: 9, fontFace: FB, color: C.ink, valign: "top", margin: 0, lineSpacingMultiple: 1.03 });
  const cb = (d.cbiqBridge || []);
  const rows = (cb.length ? cb : [{ scenario: EMDASH, ale: EMDASH, pml: EMDASH, note: EMDASH }]).map(r => [
    { text: r.scenario || EMDASH, color: C.tealDark, bold: true }, r.ale || EMDASH, r.pml || EMDASH,
    asText(r.note) + (r.linkedFindingId ? "  (" + r.linkedFindingId + ")" : ""),
  ]);
  drawTable(s, 0.4, 1.82, [3.0, 1.6, 1.6, 3.1], ["SCENARIO", "ALE €/yr", "PML (event)", "HALT-OF-OPERATIONS NOTE"], rows,
    { rowH: 0.5, hH: 0.30, fs: 8.2, hfs: 7.4 });
  s.addShape(R(), { x: 0.4, y: 4.5, w: 9.3, h: 0.5, fill: { color: C.evBg }, line: { type: "none" } });
  s.addShape(R(), { x: 0.4, y: 4.5, w: 0.06, h: 0.5, fill: { color: C.teal }, line: { type: "none" } });
  s.addText([{ text: "Portfolio (C-BIQ):  ", options: { bold: true, color: C.teal } },
    { text: "each threat scenario is priced in the companion Colt C-BIQ model; figures are illustrative model output. Staged Colt remediation drives external-surface risk toward " + APPROX + " 0.", options: { color: C.evInk } }],
    { x: 0.6, y: 4.5, w: 9.0, h: 0.5, fontSize: 8.4, fontFace: FB, valign: "middle", margin: 0 });
})();

// ============================================================ CAVEATS & CONFIDENCE
(function () {
  const s = content("Caveats, Confidence & Disambiguation", "What this is, what it isn't");
  const shelf = (d.shelfLifeMonths || 6);
  const rows = [
    [{ text: "Strategic, not a prediction", bold: true, color: C.tealDark }, "GEOPOL states who could and would, with sourced rationale and graded confidence " + EMDASH + " never who will."],
    [{ text: "Admiralty grades shown", bold: true, color: C.tealDark }, "Source reliability A" + EMDASH + "F " + TIMES + " information credibility 1" + EMDASH + "6 (NATO AJP-2.1). Grades are on every actor card."],
    [{ text: "Relevance, not fame", bold: true, color: C.tealDark }, "Relevance = Intent " + TIMES + " Capability " + TIMES + " Exposure-fit. Each actor is included for a sourced reason it would hit this entity."],
    [{ text: "Sourced, not assumed", bold: true, color: C.tealDark }, "Named campaigns, CVEs and joint advisories back each actor; single-vendor claims are graded down."],
    [{ text: "FAIR-aligned loss bridge", bold: true, color: C.tealDark }, "C-BIQ figures are illustrative model output; they support " + EMDASH + " never replace " + EMDASH + " Colt remediation and monitoring."],
    [{ text: "~" + shelf + "-month shelf life", bold: true, color: C.tealDark }, "The threat landscape shifts fast. Date and re-grade this product before re-use."],
  ];
  drawTable(s, 0.4, 1.4, [3.1, 6.2], ["TOPIC", "POSITION"], rows,
    { rowH: 0.56, hH: 0.30, fs: 8.0, hfs: 7.8 });
})();

// ---------- write ----------
pres.writeFile({ fileName: OUT })
  .then(fn => console.log("WROTE " + fn + "  slides: " + pageNum + "/" + TOTAL))
  .catch(e => { console.error(e); process.exit(1); });
