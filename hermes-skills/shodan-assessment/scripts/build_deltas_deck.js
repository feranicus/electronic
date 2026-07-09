#!/usr/bin/env node
/* Colt-branded DELTAS deck generator — "WHAT THE AI ADDED" (model-agnostic branding).
   Shows, in ONE deck, what the enrichment model improved across ALL three reports:
   Findings (before/after prose), C-BIQ (named precedent + loss scenario per finding),
   and GEOPOL (tailored sector threat context). Facts never change.

   Usage: node build_deltas_deck.js <raw.json> <enriched.json> [out.pptx] [cbiq.json] [geopol.json]

   raw/enriched share the findings.json schema. enriched carries target.exec_summary,
   target.strengths[], target.colt_mitigation[], target.geopol_context, and
   target.qwen{status,model,tokens_in,tokens_out,cost_usd}. cbiq/geopol are the derived decks. */

const fs = require("fs");
const pptxgen = require("pptxgenjs");

const EMDASH = "—", MIDDOT = "·", BULLET = "•", RAQUO = "»", APPROX = "≈";

// ---------- input ----------
function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, "utf8")); }
  catch (e) { return null; }
}
const raw = readJson(process.argv[2] || "findings_raw.json");
const enr = readJson(process.argv[3] || "findings.json");
if (!raw || !enr) { console.error("Cannot read raw/enriched findings"); process.exit(1); }
const cbiq = readJson(process.argv[5] || "cbiq.json") || {};
const geopol = readJson(process.argv[6] || "geopol.json") || {};

const rt = (raw.target || {}), et = (enr.target || {});
const company = et.company || rt.company || "Target";
const OUT = process.argv[4] || ("./" + company.replace(/[^A-Za-z0-9]+/g, "_") + "_DELTAS.pptx");

const asLines = v => Array.isArray(v) ? v.filter(x => x != null).map(String)
  : (v == null || v === "" ? [] : [String(v)]);
const nid = v => String(v == null ? "" : v).toUpperCase().replace(/[^A-Z0-9]/g, "");
const fmtInt = n => { const x = Number(n); return Number.isFinite(x) ? x.toLocaleString("en-US") : "0"; };

// ---------- model telemetry + dynamic brand ----------
const q = et.qwen || {};
const qModel  = q.model ? String(q.model) : "ai";
const BRAND   = (qModel.split(/[-.]/)[0] || "AI").toUpperCase();   // deepseek-3.2 -> "DEEPSEEK"
const qTokens = (Number(q.tokens_in) || 0) + (Number(q.tokens_out) || 0);
const qCost   = Number(q.cost_usd) || 0;
const qLine = qModel + "  " + MIDDOT + "  " + fmtInt(qTokens) + " tokens  " + MIDDOT + "  " + APPROX + "$" + qCost.toFixed(4);

// ---------- pair findings by normalised id ----------
const enrById = {};
(Array.isArray(enr.findings) ? enr.findings : []).forEach(f => { enrById[nid(f.id)] = f; });
function textFor(f, k) { return asLines(f && f[k]).join("\n"); }
function differs(rf, ef) { return ["what", "why", "rem"].some(k => textFor(rf, k) !== textFor(ef, k)); }
const rawFindings = Array.isArray(raw.findings) ? raw.findings : [];
const pairs = [];
rawFindings.forEach(rf => { const ef = enrById[nid(rf.id)]; if (ef && differs(rf, ef)) pairs.push({ raw: rf, enr: ef }); });

const strengths  = Array.isArray(et.strengths) ? et.strengths.filter(x => x != null).map(String).filter(x => x.trim()) : [];
const mitigation = Array.isArray(et.colt_mitigation) ? et.colt_mitigation.filter(x => x && typeof x === "object") : [];
const execSummary = (et.exec_summary != null && String(et.exec_summary).trim()) ? String(et.exec_summary).trim() : "";
const cbiqRows = (Array.isArray(cbiq.findings) ? cbiq.findings : []).filter(f => f && f.id && f.id !== "—" && f.id !== "-");
const geoAfter = (geopol && geopol.sectorContext) ? String(geopol.sectorContext).trim() : (et.geopol_context ? String(et.geopol_context).trim() : "");

// ---------- presentation ----------
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Colt Sales Engineering";
pres.title = company + " " + EMDASH + " What " + BRAND + " Added (raw vs pursuit-grade)";

const C = {
  teal: "00D7BD", tealMid: "00A49A", tealDark: "0C544E",
  black: "121212", dark: "474946", light: "ECECED",
  crit: "F20C36", high: "FF7900", med: "FFC33C", low: "474946",
  ink: "1A1A1A", inkMuted: "5B6470", divider: "D8D6CF",
  white: "FFFFFF", evidenceBg: "121212", evidenceInk: "ECECED",
  green: "10B981", raw: "9AA0A6", rawBg: "F1F1EF",
};
const FH = "Georgia", FB = "Calibri", FM = "Consolas", FD = "Arial Black", FA = "Arial";
let pageNum = 0;
let TOTAL = 1 + 1 + pairs.length + (cbiqRows.length ? 1 : 0) + (geoAfter ? 1 : 0) + 1;

function corner(slide, color = C.black, size = 18) {
  slide.addText("colt", { x: 9.05, y: 0.18, w: 0.85, h: 0.32, fontSize: size, fontFace: FA, color, bold: true, align: "right", margin: 0 });
}
function bigChevrons(slide, opts = {}) {
  const x = opts.x ?? 0.5, w = opts.w ?? 9.0, yStart = opts.yStart ?? 0.20;
  const triH = opts.triH ?? 1.55, gap = opts.gap ?? 0.30, color = opts.color || C.white;
  for (let i = 0; i < 3; i++) slide.addShape(pres.shapes.ISOSCELES_TRIANGLE,
    { x, y: yStart + i * (triH + gap), w, h: triH, fill: { color }, line: { type: "none" } });
}
function tracer(slide, color = C.tealDark) {
  for (let i = 0; i < 3; i++) slide.addShape(pres.shapes.RIGHT_TRIANGLE,
    { x: 8.30 + i * 0.14, y: 5.34, w: 0.11, h: 0.16, fill: { color }, line: { type: "none" }, rotate: 90 });
  slide.addText(RAQUO + RAQUO + " " + pageNum + "/" + TOTAL, { x: 8.62, y: 5.28, w: 1.23, h: 0.28,
    fontSize: 9, fontFace: FB, color, bold: true, align: "right", valign: "middle", margin: 0 });
}
function footer(slide) {
  slide.addText("INTERNAL " + EMDASH + " COLT CONFIDENTIAL " + MIDDOT + " NOT FOR EXTERNAL DISTRIBUTION", {
    x: 0.4, y: 5.32, w: 6.4, h: 0.22, fontSize: 7.5, fontFace: FB, color: C.inkMuted, charSpacing: 2, valign: "middle", margin: 0 });
}
function pageHeader(slide, eyebrow, title) {
  slide.addText(String(eyebrow || "").toUpperCase(), { x: 0.4, y: 0.22, w: 8.4, h: 0.22,
    fontSize: 9, fontFace: FB, color: C.teal, charSpacing: 3, bold: true, margin: 0 });
  slide.addText(String(title || ""), { x: 0.4, y: 0.44, w: 8.5, h: 0.80,
    fontSize: 18, fontFace: FH, color: C.tealDark, bold: true, valign: "top", margin: 0 });
  corner(slide, C.tealDark, 16);
}
function sevBadge(slide, sev, x, y, w = 1.05) {
  const map = { CRITICAL: [C.crit, C.white], HIGH: [C.high, C.white], MEDIUM: [C.med, C.black], LOW: [C.low, C.white] };
  const [bg, fg] = map[sev] || map.LOW;
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.28, fill: { color: bg }, line: { type: "none" } });
  slide.addText(sev, { x, y, w, h: 0.28, fontSize: 10, fontFace: FB, color: fg, bold: true, align: "center", valign: "middle", charSpacing: 2, margin: 0 });
}
function content(eyebrow, title) {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.white };
  pageHeader(s, eyebrow, title);
  return s;
}
const tierCol = t => ({ CRIT: C.crit, CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, MED: C.med, LOW: C.low })[String(t || "").toUpperCase()] || C.tealDark;

// ===== SLIDE 1 — TITLE =====
(function title() {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.teal };
  bigChevrons(s, { x: 5.95, w: 5.0, yStart: 0.05, triH: 1.95, gap: 0.06, color: C.white });
  corner(s, C.black, 22);
  s.addText("LLM ENRICHMENT " + MIDDOT + " VALUE MADE TANGIBLE", { x: 0.5, y: 1.20, w: 7.5, h: 0.3,
    fontSize: 11, fontFace: FA, color: C.black, bold: true, charSpacing: 3, margin: 0 });
  s.addText("WHAT " + BRAND + " ADDED", { x: 0.46, y: 1.58, w: 8.6, h: 1.02,
    fontSize: 50, fontFace: FD, color: C.black, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.54, y: 2.74, w: 0.22, h: 0.22, fill: { color: C.med }, line: { type: "none" } });
  s.addText(company + "  " + EMDASH + "  raw scan vs pursuit-grade, across all 3 reports", { x: 0.9, y: 2.70, w: 8.4, h: 0.34,
    fontSize: 14, fontFace: FA, color: C.black, bold: true, margin: 0 });
  s.addText(qLine, { x: 0.5, y: 3.66, w: 8.6, h: 0.30, fontSize: 12, fontFace: FM, color: C.black, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.75, w: 10, h: 0.875, fill: { color: C.black }, line: { type: "none" } });
  const meta = [
    ["PREPARED", "Colt Sales Engineering"], ["MODEL", qModel],
    ["ENGINE", BRAND + " prose + audit (facts unchanged)"], ["STATUS", "INTERNAL " + EMDASH + " CONFIDENTIAL"],
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
  s.addText("1 / " + TOTAL, { x: 8.80, y: 4.34, w: 1.05, h: 0.28, fontSize: 9, fontFace: FB, color: C.black, bold: true, align: "right", margin: 0 });
})();

// ===== SLIDE 2 — SUMMARY =====
(function summary() {
  const s = content("WHAT CHANGED", "The delta at a glance " + EMDASH + " all 3 reports");
  const cards = [
    [String(pairs.length),      "FINDINGS REWRITTEN", C.teal],
    [String(cbiqRows.length),   "C-BIQ CASES BUILT",  C.crit],
    [geoAfter ? "1" : "0",      "GEOPOL CONTEXT",     C.high],
    [String(strengths.length),  "STRENGTHS ADDED",    C.green],
  ];
  let cx = 0.4;
  cards.forEach(([n, l, col]) => {
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.34, w: 2.18, h: 1.02, fill: { color: C.tealDark }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.34, w: 2.18, h: 0.08, fill: { color: col }, line: { type: "none" } });
    s.addText(n, { x: cx, y: 1.45, w: 2.18, h: 0.62, fontSize: 34, fontFace: FH, color: col, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(l, { x: cx, y: 2.03, w: 2.18, h: 0.28, fontSize: 8, fontFace: FB, color: C.white, bold: true, align: "center", charSpacing: 1, margin: 0 });
    cx += 2.38;
  });
  s.addText("EXEC SUMMARY " + EMDASH + " ADDED BY " + BRAND, { x: 0.4, y: 2.66, w: 9.0, h: 0.20,
    fontSize: 8.5, fontFace: FB, color: C.tealDark, bold: true, charSpacing: 2, margin: 0 });
  const para = execSummary || "(no exec_summary produced)";
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.90, w: 9.3, h: 1.70, fill: { color: C.rawBg }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.90, w: 0.07, h: 1.70, fill: { color: C.teal }, line: { type: "none" } });
  s.addText(para, { x: 0.62, y: 2.98, w: 8.95, h: 1.54, fontSize: 10.5, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.72, w: 9.3, h: 0.48, fill: { color: C.light }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.72, w: 0.07, h: 0.48, fill: { color: C.teal }, line: { type: "none" } });
  s.addText([{ text: "Facts unchanged.  ", options: { bold: true, color: C.tealDark } },
    { text: BRAND + " reframes prose and adds business/architecture context, named precedents, strengths and Colt mapping " + EMDASH + " it never alters the observed evidence.", options: { color: C.ink } }],
    { x: 0.58, y: 4.75, w: 9.0, h: 0.42, fontSize: 8.6, fontFace: FB, valign: "middle", margin: 0 });
  footer(s); tracer(s);
})();

// ===== FINDINGS BEFORE / AFTER =====
function column(s, x, w, kind, f, accent, headBg, headFg, labelTop, labelBot) {
  s.addShape(pres.shapes.RECTANGLE, { x, y: 1.72, w, h: 0.34, fill: { color: headBg }, line: { type: "none" } });
  s.addText(labelTop, { x: x + 0.10, y: 1.72, w: w - 0.20, h: 0.34, fontSize: 9.5, fontFace: FB, color: headFg, bold: true, charSpacing: 2, valign: "middle", margin: 0 });
  s.addText(labelBot, { x: x + 0.10, y: 1.72, w: w - 0.20, h: 0.34, fontSize: 7.5, fontFace: FB, color: headFg, align: "right", valign: "middle", margin: 0 });
  const inkCol = kind === "raw" ? C.raw : C.ink;
  const secCol = kind === "raw" ? C.dark : C.tealDark;
  const sections = [["WHAT WE OBSERVED", asLines(f.what)], ["WHY IT MATTERS", asLines(f.why)], ["REMEDIATION & COLT FIT", asLines(f.rem)]];
  const heights = [1.32, 0.86, 1.02];
  let y = 2.18;
  sections.forEach(([lbl, lines], si) => {
    const h = heights[si];
    s.addText(lbl, { x, y, w, h: 0.18, fontSize: 8, fontFace: FB, color: secCol, bold: true, charSpacing: 2, margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x, y: y + 0.20, w: 0.05, h: h - 0.24, fill: { color: accent }, line: { type: "none" } });
    const body = (lines.length ? lines : [EMDASH]).map((ln, i) => ({ text: ln,
      options: { breakLine: i < lines.length - 1, fontSize: 8.2, fontFace: FB, color: inkCol, bullet: { code: "2022", indent: 10 } } }));
    s.addText(body, { x: x + 0.14, y: y + 0.20, w: w - 0.16, h: h - 0.24, valign: "top", margin: 0, paraSpaceAfter: 2 });
    y += h + 0.06;
  });
}
function beforeAfterSlide(pair) {
  const ef = pair.enr, rf = pair.raw;
  const sev = (ef.sev || rf.sev || "LOW").toUpperCase();
  const s = content("DELTA " + MIDDOT + " FINDING " + (ef.id || rf.id || ""), ef.title || rf.title || "Finding");
  sevBadge(s, sev, 0.4, 1.28);
  s.addText(String(ef.id || rf.id || "").toUpperCase(), { x: 1.55, y: 1.28, w: 4.4, h: 0.28, fontSize: 8.5, fontFace: FB, color: C.inkMuted, charSpacing: 2, bold: true, valign: "middle", margin: 0 });
  s.addText("RAW SCAN  " + RAQUO + RAQUO + "  " + BRAND + " PURSUIT", { x: 5.2, y: 1.28, w: 4.5, h: 0.28, fontSize: 8.5, fontFace: FB, color: C.teal, bold: true, charSpacing: 1, align: "right", valign: "middle", margin: 0 });
  column(s, 0.4, 4.55, "raw", rf, C.raw, C.dark, C.white, "BEFORE", "raw scan");
  column(s, 5.05, 4.55, "enr", ef, C.teal, C.tealDark, C.white, "AFTER", BRAND + " pursuit");
  footer(s); tracer(s);
}
pairs.forEach(p => beforeAfterSlide(p));

// ===== C-BIQ DELTA =====
function cbiqDeltaSlide() {
  const s = content("DELTA " + MIDDOT + " C-BIQ BUSINESS IMPACT", BRAND + " turned each priced finding into a euro business case");
  s.addText("BEFORE " + EMDASH + " templated", { x: 1.0, y: 1.24, w: 3.5, h: 0.2, fontSize: 8, fontFace: FB, color: C.dark, bold: true, charSpacing: 1, margin: 0 });
  s.addText("AFTER " + EMDASH + " " + BRAND + ": named precedent + loss scenario", { x: 5.1, y: 1.24, w: 4.6, h: 0.2, fontSize: 8, fontFace: FB, color: C.tealDark, bold: true, charSpacing: 1, margin: 0 });
  const rows = cbiqRows.slice(0, 5);
  const y0 = 1.52, rh = Math.max(0.6, Math.min(0.74, 3.4 / Math.max(rows.length, 1)));
  rows.forEach((f, i) => {
    const y = y0 + i * rh;
    if (i % 2) s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: y - 0.02, w: 9.3, h: rh, fill: { color: C.rawBg }, line: { type: "none" } });
    s.addText(String(f.id || ""), { x: 0.44, y, w: 0.55, h: 0.3, fontSize: 10, fontFace: FB, bold: true, color: tierCol(f.tier), valign: "top", margin: 0 });
    s.addText("Generic exposure class; no named precedent, no euro anchor", { x: 1.0, y, w: 3.5, h: rh - 0.06, fontSize: 7.7, fontFace: FB, color: C.raw, italic: true, valign: "top", margin: 0 });
    s.addText(RAQUO + RAQUO, { x: 4.6, y, w: 0.42, h: 0.3, fontSize: 11, fontFace: FB, color: C.teal, bold: true, valign: "top", margin: 0 });
    s.addText([{ text: String(f.realComparable || "").trim() + "\n", options: { bold: true, color: C.crit, breakLine: true } },
               { text: String(f.lossScenario || "").trim(), options: { color: C.ink } }],
      { x: 5.1, y, w: 4.6, h: rh - 0.06, fontSize: 7.7, fontFace: FB, valign: "top", margin: 0, lineSpacingMultiple: 0.95 });
  });
  s.addText("Every priced finding now carries a real, dated, costed precedent and a plain-language loss scenario " + EMDASH + " the C-BIQ argument, drawn.",
    { x: 0.4, y: 5.0, w: 9.4, h: 0.28, fontSize: 8, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
  footer(s); tracer(s);
}
if (cbiqRows.length) cbiqDeltaSlide();

// ===== GEOPOL DELTA =====
function geopolDeltaSlide() {
  const s = content("DELTA " + MIDDOT + " GEOPOL THREAT CONTEXT", BRAND + " tailored the sector threat narrative to this customer");
  const before = "BSI 2025: Germany is among the most-targeted nations; many KRITIS operators lack full detection coverage.";
  s.addText("BEFORE " + EMDASH + " GENERIC SECTOR LINE", { x: 0.4, y: 1.30, w: 9.0, h: 0.2, fontSize: 8.5, fontFace: FB, color: C.dark, bold: true, charSpacing: 2, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.54, w: 9.3, h: 0.9, fill: { color: C.rawBg }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.54, w: 0.07, h: 0.9, fill: { color: C.raw }, line: { type: "none" } });
  s.addText(before, { x: 0.62, y: 1.62, w: 8.95, h: 0.76, fontSize: 10, fontFace: FB, color: C.raw, italic: true, valign: "top", margin: 0 });
  s.addText("AFTER " + EMDASH + " " + BRAND + " TAILORED CONTEXT", { x: 0.4, y: 2.62, w: 9.0, h: 0.2, fontSize: 8.5, fontFace: FB, color: C.tealDark, bold: true, charSpacing: 2, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.86, w: 9.3, h: 1.30, fill: { color: C.rawBg }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.86, w: 0.07, h: 1.30, fill: { color: C.teal }, line: { type: "none" } });
  s.addText(geoAfter || "(no geopol_context produced)", { x: 0.62, y: 2.94, w: 8.95, h: 1.14, fontSize: 10.5, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
  const actorCount = Array.isArray(geopol.actors) ? geopol.actors.length : 0;
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.34, w: 9.3, h: 0.52, fill: { color: C.light }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.34, w: 0.07, h: 0.52, fill: { color: C.teal }, line: { type: "none" } });
  s.addText([{ text: "Plus: ", options: { bold: true, color: C.tealDark } },
    { text: actorCount + " named threat actor" + (actorCount === 1 ? "" : "s") + " mapped to the enriched findings (dated campaigns, MITRE TTPs, Admiralty grades) " + EMDASH + " the same exposures " + BRAND + " reframed now drive actor selection.", options: { color: C.ink } }],
    { x: 0.58, y: 4.38, w: 9.0, h: 0.46, fontSize: 8.6, fontFace: FB, valign: "middle", margin: 0 });
  footer(s); tracer(s);
}
if (geoAfter) geopolDeltaSlide();

// ===== CLOSING =====
(function closing() {
  const s = content("PROOF OF VALUE", "Net-new artifacts " + BRAND + " produced " + EMDASH + " the raw scan had none");
  const items = [
    ["EXECUTIVE SUMMARY", execSummary ? "A pursuit-ready narrative " + EMDASH + " posture vs peers, headline risks and the Colt hook." : "(not produced)", C.med],
    ["C-BIQ NAMED PRECEDENTS", cbiqRows.length ? cbiqRows.length + " priced finding" + (cbiqRows.length === 1 ? "" : "s") + " matched to a real, dated, costed breach." : "(none)", C.crit],
    ["GEOPOL TAILORED CONTEXT", geoAfter ? "Sector threat narrative rewritten for this customer's exposure + geography." : "(none)", C.high],
    ["STRENGTHS + MITIGATION MAP", (strengths.length + mitigation.length) ? strengths.length + " strength" + (strengths.length === 1 ? "" : "s") + " and " + mitigation.length + " Colt mapping row" + (mitigation.length === 1 ? "" : "s") + "." : "(none)", C.green],
  ];
  const cardH = 0.78, gap = 0.12, startY = 1.34;
  items.forEach(([lbl, body, col], i) => {
    const y = startY + i * (cardH + gap);
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 9.3, h: cardH, fill: { color: C.rawBg }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 0.08, h: cardH, fill: { color: col }, line: { type: "none" } });
    s.addShape(pres.shapes.OVAL, { x: 0.62, y: y + 0.16, w: 0.30, h: 0.30, fill: { color: col }, line: { type: "none" } });
    s.addText("+", { x: 0.62, y: y + 0.14, w: 0.30, h: 0.30, fontSize: 16, fontFace: FA, color: C.white, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(String(lbl), { x: 1.08, y: y + 0.08, w: 8.5, h: 0.26, fontSize: 10.5, fontFace: FB, color: C.tealDark, bold: true, charSpacing: 1, valign: "middle", margin: 0 });
    s.addText(String(body), { x: 1.08, y: y + 0.36, w: 8.5, h: cardH - 0.40, fontSize: 8.8, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
  });
  footer(s); tracer(s);
})();

pres.writeFile({ fileName: OUT })
  .then(fn => console.log("WROTE " + fn + "  pages: " + pageNum))
  .catch(e => { console.error(e); process.exit(1); });
