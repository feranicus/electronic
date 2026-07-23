#!/usr/bin/env node
/**
 * build_compliance_deck.js — ONE parametrized Colt-branded deck builder for the Compliance module.
 *
 *   node build_compliance_deck.js compliance.json out.pptx <nis2|cra|aiact|roadmap>
 *
 * Renders either a single-regime deck (NIS2 / CRA / EU AI Act — scope, obligations, gaps, deadlines,
 * penalty exposure, how Colt helps) or the combined ROADMAP deck (exec summary + assumptions, a
 * three-regime at-a-glance table, the merged deadline calendar, penalty exposure and a phased plan).
 *
 * Deterministic rendering: the JSON is produced by compliance_enrich.py; a weak model can weaken the
 * prose but never breaks the layout. Defensive by contract — every field is guarded and the deck
 * renders on the deterministic fallback (applicability "requires confirmation", no gaps) too.
 *
 * Language: DECK_LANG=de -> Hoch-Deutsch chrome via the local label map L(); the prose (rationale,
 * gaps, colt, exec_summary) is already written in the requested language by the model.
 */
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const [, , jsonPath, outPath, regimeArg] = process.argv;
if (!jsonPath || !outPath || !regimeArg) {
  console.error("usage: build_compliance_deck.js compliance.json out.pptx <nis2|cra|aiact|roadmap>");
  process.exit(2);
}
const D = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
const LANG = (process.env.DECK_LANG || D.lang || "en").toLowerCase().startsWith("de") ? "de" : "en";
const company = D.company || "Target";
const EMDASH = "—", MIDDOT = "·", RAQUO = "»";

// ---- Colt palette (matches the security decks) ----
const C = {
  teal: "00D7BD", tealMid: "00A49A", tealDark: "0C544E", black: "121212", dark: "474946",
  light: "ECECED", crit: "F20C36", high: "FF7900", med: "FFC33C", low: "474946",
  ink: "1A1A1A", inkMuted: "5B6470", divider: "D8D6CF", white: "FFFFFF", gold: "F7C844",
  navy: "1D2B4E", purple: "6B3FA0", green: "10B981",
};
const FH = "Georgia", FB = "Calibri", FD = "Arial Black", FA = "Arial";

// ---- tiny EN/DE label map for chrome (prose comes from the model already localised) ----
const LABELS = {
  eyebrow: { en: "EU DIGITAL & CYBER COMPLIANCE", de: "EU-DIGITAL- & CYBER-COMPLIANCE" },
  scope: { en: "Scope & applicability", de: "Anwendungsbereich & Betroffenheit" },
  obligations: { en: "Core obligations", de: "Kernpflichten" },
  gaps: { en: "Priority gaps", de: "Prioritäre Lücken" },
  deadlines: { en: "Key deadlines", de: "Wichtige Fristen" },
  penalty: { en: "Penalty exposure", de: "Bußgeld-Exposition" },
  colt: { en: "How Colt helps", de: "Wie Colt unterstützt" },
  applies: { en: "Applies", de: "Betroffen" },
  notApplies: { en: "Out of scope", de: "Nicht betroffen" },
  unclear: { en: "Requires confirmation", de: "Zu bestätigen" },
  classification: { en: "Classification", de: "Einstufung" },
  instrument: { en: "Instrument", de: "Rechtsakt" },
  regulates: { en: "Regulates", de: "Reguliert" },
  ref: { en: "REF", de: "REF" },
  obligation: { en: "OBLIGATION", de: "PFLICHT" },
  requires: { en: "WHAT IT REQUIRES", de: "WAS ERFORDERLICH IST" },
  date: { en: "DATE", de: "DATUM" },
  milestone: { en: "MILESTONE", de: "MEILENSTEIN" },
  essentialMax: { en: "Essential-tier maximum", de: "Obergrenze (essenziell)" },
  importantMax: { en: "Important-tier maximum", de: "Obergrenze (wichtig)" },
  overview: { en: "Three regimes at a glance", de: "Drei Regime im Überblick" },
  roadmap: { en: "Remediation roadmap", de: "Umsetzungs-Fahrplan" },
  priorities: { en: "Priorities", de: "Prioritäten" },
  execSummary: { en: "Executive summary", de: "Management-Zusammenfassung" },
  assumptions: { en: "Scoping assumptions (confirm via clarification)", de: "Annahmen zum Anwendungsbereich (bitte bestätigen)" },
  regime: { en: "REGIME", de: "REGIME" },
  maxFine: { en: "MAX FINE", de: "MAX. BUSSGELD" },
  nearest: { en: "NEAREST DEADLINE", de: "NÄCHSTE FRIST" },
  none: { en: "None recorded", de: "Keine erfasst" },
  gapNone: { en: "No priority gaps recorded for this regime at the assumed scope. Confirm scope to finalise.", de: "Keine prioritären Lücken bei angenommenem Anwendungsbereich. Anwendungsbereich bestätigen." },
  status: { en: "INTERNAL " + EMDASH + " COLT CONFIDENTIAL", de: "INTERN " + EMDASH + " VERTRAULICH (COLT)" },
  prepared: { en: "Colt Sales Engineering", de: "Colt Sales Engineering" },
};
const L = (k) => (LABELS[k] || {})[LANG] || (LABELS[k] || {}).en || k;

const REGIME_TITLE = {
  nis2: { en: "NIS2", de: "NIS2" },
  cra: { en: "Cyber Resilience Act", de: "Cyber Resilience Act" },
  aiact: { en: "EU AI Act", de: "EU AI Act" },
  roadmap: { en: "Compliance Roadmap", de: "Compliance-Fahrplan" },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Colt Sales Engineering";
pres.title = company + " " + EMDASH + " EU Compliance " + (REGIME_TITLE[regimeArg] || {}).en;

let pageNum = 0, TOTAL = 1;

// ---------- helpers ----------
function corner(s, color = C.black, size = 18) {
  s.addText("colt", { x: 9.05, y: 0.18, w: 0.85, h: 0.32, fontSize: size, fontFace: FA, color, bold: true, align: "right", margin: 0 });
}
function tracer(s, color = C.tealDark) {
  s.addText(RAQUO + RAQUO + " " + pageNum + "/" + TOTAL, { x: 8.62, y: 5.28, w: 1.23, h: 0.28, fontSize: 9, fontFace: FB, color, bold: true, align: "right", valign: "middle", margin: 0 });
}
function footer(s) {
  s.addText(L("status") + " " + MIDDOT + " NOT FOR EXTERNAL DISTRIBUTION", { x: 0.4, y: 5.32, w: 6.4, h: 0.22, fontSize: 7.5, fontFace: FB, color: C.inkMuted, charSpacing: 2, valign: "middle", margin: 0 });
}
function pageHeader(s, eyebrow, title) {
  s.addText(String(eyebrow || "").toUpperCase(), { x: 0.4, y: 0.22, w: 8.4, h: 0.22, fontSize: 9, fontFace: FB, color: C.teal, charSpacing: 3, bold: true, margin: 0 });
  s.addText(String(title || ""), { x: 0.4, y: 0.44, w: 8.6, h: 0.80, fontSize: 20, fontFace: FH, color: C.tealDark, bold: true, valign: "top", margin: 0 });
  corner(s, C.tealDark, 16);
}
function content(eyebrow, title) {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.white };
  pageHeader(s, eyebrow, title);
  return s;
}
function drawTable(s, rows, opts) {
  s.addTable(rows, Object.assign({ border: { type: "solid", color: C.divider, pt: 0.5 }, fontFace: FB, color: C.ink, valign: "middle", align: "left", autoPage: false }, opts));
}
function hdrCell(t) { return { text: t, options: { fill: C.tealDark, color: C.white, bold: true } }; }
function appliesBadge(s, applies, x, y) {
  const map = { true: [C.crit, C.white, L("applies")], false: [C.dark, C.white, L("notApplies")], unclear: [C.med, C.black, L("unclear")] };
  const key = applies === true ? "true" : applies === false ? "false" : "unclear";
  const [bg, fg, txt] = map[key];
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.6, h: 0.34, fill: { color: bg }, line: { type: "none" } });
  s.addText(txt.toUpperCase(), { x, y, w: 2.6, h: 0.34, fontSize: 11, fontFace: FB, color: fg, bold: true, align: "center", valign: "middle", charSpacing: 2, margin: 0 });
}
function sevColor(sev) { return { CRITICAL: C.crit, HIGH: C.high, MEDIUM: C.med, LOW: C.low }[(sev || "").toUpperCase()] || C.dark; }
function fmtDate(d) {
  try { const dt = new Date(d + "T00:00:00Z"); if (isNaN(dt)) return d;
    return dt.toLocaleDateString(LANG === "de" ? "de-DE" : "en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
  } catch { return d; }
}
function titleSlide(bigTitle, subline, classText, applies) {
  pageNum++;
  const s = pres.addSlide();
  s.background = { color: C.teal };
  corner(s, C.black, 22);
  s.addText(L("eyebrow"), { x: 0.5, y: 1.10, w: 8.5, h: 0.3, fontSize: 11, fontFace: FA, color: C.black, bold: true, charSpacing: 3, margin: 0 });
  s.addText(bigTitle, { x: 0.46, y: 1.52, w: 9.0, h: 1.4, fontSize: bigTitle.length > 16 ? 44 : 62, fontFace: FD, color: C.black, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.54, y: 3.05, w: 0.22, h: 0.22, fill: { color: C.navy }, line: { type: "none" } });
  s.addText(company + "  " + MIDDOT + "  " + subline, { x: 0.9, y: 3.0, w: 8.4, h: 0.32, fontSize: 14, fontFace: FA, color: C.black, bold: true, margin: 0 });
  if (classText) {
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.55, w: 9.0, h: 0.5, fill: { color: C.black }, line: { type: "none" } });
    s.addText((classText || ""), { x: 0.66, y: 3.55, w: 8.7, h: 0.5, fontSize: 13, fontFace: FB, color: C.teal, bold: true, valign: "middle", margin: 0 });
  }
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.75, w: 10, h: 0.875, fill: { color: C.black }, line: { type: "none" } });
  const meta = [["PREPARED", L("prepared")], ["FOR", company], ["SOURCE", "EU primary law (see appendix)"], ["STATUS", L("status")]];
  let mx = 0.5;
  meta.forEach(([k, v], i) => {
    const w = (i === 1 || i === 2) ? 3.1 : 1.6;
    s.addText([{ text: k + "\n", options: { fontSize: 8, color: C.teal, bold: true, charSpacing: 2 } }, { text: String(v), options: { fontSize: 8.5, color: C.white } }], { x: mx, y: 4.83, w, h: 0.72, fontFace: FB, valign: "middle", margin: 0 });
    mx += w + 0.05;
  });
  s.addText("1 / " + TOTAL, { x: 8.80, y: 4.40, w: 1.05, h: 0.28, fontSize: 9, fontFace: FB, color: C.black, bold: true, align: "right", margin: 0 });
}

// ======================================================================= REGIME DECK
function regimeDeck(key) {
  const r = (D.regimes || {})[key] || {};
  const nearest = (r.deadlines || []).slice().sort((a, b) => String(a.date).localeCompare(String(b.date)))[0];
  TOTAL = 1 /*title*/ + 1 /*scope*/ + 1 /*obligations*/ + 1 /*gaps*/ + 1 /*deadlines*/ + 1 /*penalty*/ + ((r.colt || []).length ? 1 : 0);

  const shortName = (REGIME_TITLE[key] || {})[LANG] || key.toUpperCase();
  titleSlide(shortName, r.name || "", (L("classification") + ": " + (r.classification || L("unclear"))), r.applies);

  // -- scope & applicability
  (function () {
    const s = content(L("eyebrow"), L("scope"));
    appliesBadge(s, r.applies, 0.4, 1.30);
    s.addText((L("classification") + ": ").toUpperCase() + (r.classification || L("unclear")), { x: 3.2, y: 1.30, w: 6.3, h: 0.34, fontSize: 12, fontFace: FB, color: C.tealDark, bold: true, valign: "middle", margin: 0 });
    s.addText(String(r.rationale || ""), { x: 0.4, y: 1.85, w: 9.2, h: 1.6, fontSize: 12, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
    // instrument / regulates strip
    const strip = [[L("instrument"), r.instrument || EMDASH], [L("regulates"), r.regulates || EMDASH]];
    let yy = 3.7;
    strip.forEach(([k, v]) => {
      s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: yy, w: 9.2, h: 0.52, fill: { color: C.light }, line: { type: "none" } });
      s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: yy, w: 0.07, h: 0.52, fill: { color: C.teal }, line: { type: "none" } });
      s.addText([{ text: k + ":  ", options: { bold: true, color: C.tealDark } }, { text: String(v), options: { color: C.ink } }], { x: 0.58, y: yy, w: 8.9, h: 0.52, fontSize: 10, fontFace: FB, valign: "middle", margin: 0 });
      yy += 0.6;
    });
    footer(s); tracer(s);
  })();

  // -- obligations
  (function () {
    const s = content(L("eyebrow"), L("obligations"));
    const rows = [[hdrCell(L("ref")), hdrCell(L("obligation")), hdrCell(L("requires"))]];
    (r.obligations || []).slice(0, 6).forEach((o) => rows.push([
      { text: o.ref || "", options: { bold: true, color: C.tealDark, valign: "top" } },
      { text: o.title || "", options: { bold: true, valign: "top" } },
      { text: o.detail || "", options: { fontSize: 8.5, valign: "top" } },
    ]));
    drawTable(s, rows, { x: 0.4, y: 1.35, w: 9.2, colW: [1.35, 2.5, 5.35], rowH: 0.5, fontSize: 9, valign: "top" });
    footer(s); tracer(s);
  })();

  // -- gaps
  (function () {
    const s = content(L("eyebrow"), L("gaps"));
    const gaps = (r.gaps || []).filter((g) => g && (g.title || g.detail));
    if (!gaps.length) {
      s.addText(L("gapNone"), { x: 0.4, y: 1.5, w: 9.2, h: 0.8, fontSize: 12, fontFace: FB, color: C.inkMuted, italic: true, margin: 0 });
    } else {
      let y = 1.35;
      gaps.slice(0, 5).forEach((g) => {
        const col = sevColor(g.sev);
        s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 1.05, h: 0.28, fill: { color: col }, line: { type: "none" } });
        s.addText(String(g.sev || "").toUpperCase(), { x: 0.4, y, w: 1.05, h: 0.28, fontSize: 9, fontFace: FB, color: (col === C.med ? C.black : C.white), bold: true, align: "center", valign: "middle", charSpacing: 1, margin: 0 });
        s.addText([{ text: (g.title || "") + "  ", options: { bold: true, color: C.ink } }, { text: g.article ? "(" + g.article + ")" : "", options: { color: C.tealMid, bold: true } }], { x: 1.6, y: y - 0.02, w: 8.0, h: 0.3, fontSize: 11, fontFace: FB, valign: "middle", margin: 0 });
        s.addText(String(g.detail || ""), { x: 1.6, y: y + 0.28, w: 8.0, h: 0.5, fontSize: 9, fontFace: FB, color: C.inkMuted, valign: "top", margin: 0 });
        y += 0.86;
      });
    }
    footer(s); tracer(s);
  })();

  // -- deadlines
  (function () {
    const s = content(L("eyebrow"), L("deadlines"));
    const rows = [[hdrCell(L("date")), hdrCell(L("milestone"))]];
    (r.deadlines || []).slice(0, 8).forEach((d) => rows.push([
      { text: fmtDate(d.date), options: { bold: true, color: C.tealDark } },
      { text: d.label || "", options: {} },
    ]));
    if (rows.length === 1) rows.push([{ text: EMDASH }, { text: L("none") }]);
    drawTable(s, rows, { x: 0.4, y: 1.35, w: 9.2, colW: [1.8, 7.4], rowH: 0.42, fontSize: 10 });
    footer(s); tracer(s);
  })();

  // -- penalty
  (function () {
    const s = content(L("eyebrow"), L("penalty"));
    const p = r.penalty || {};
    const cards = [[L("essentialMax"), p.essential || EMDASH, C.crit], [L("importantMax"), p.important || EMDASH, C.high]];
    let cx = 0.4;
    cards.forEach(([lab, val, col]) => {
      s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.5, w: 4.5, h: 1.4, fill: { color: C.tealDark }, line: { type: "none" } });
      s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.5, w: 4.5, h: 0.09, fill: { color: col }, line: { type: "none" } });
      s.addText(lab.toUpperCase(), { x: cx + 0.2, y: 1.66, w: 4.1, h: 0.3, fontSize: 9, fontFace: FB, color: C.teal, bold: true, charSpacing: 1, margin: 0 });
      s.addText(String(val), { x: cx + 0.2, y: 2.0, w: 4.1, h: 0.82, fontSize: 17, fontFace: FH, color: C.white, bold: true, valign: "top", margin: 0 });
      cx += 4.7;
    });
    if (p.note) {
      s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 3.2, w: 9.2, h: 1.0, fill: { color: C.light }, line: { type: "none" } });
      s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 3.2, w: 0.07, h: 1.0, fill: { color: C.gold }, line: { type: "none" } });
      s.addText(String(p.note), { x: 0.58, y: 3.28, w: 8.9, h: 0.84, fontSize: 10, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
    }
    footer(s); tracer(s);
  })();

  // -- how Colt helps
  if ((r.colt || []).length) {
    const s = content(L("eyebrow"), L("colt"));
    let y = 1.4;
    (r.colt || []).slice(0, 4).forEach((c) => {
      s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 9.2, h: 0.82, fill: { color: C.white }, line: { color: C.divider, pt: 1 } });
      s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 0.09, h: 0.82, fill: { color: C.teal }, line: { type: "none" } });
      s.addText(String(c.title || ""), { x: 0.62, y: y + 0.08, w: 8.8, h: 0.3, fontSize: 12, fontFace: FB, color: C.tealDark, bold: true, margin: 0 });
      s.addText(String(c.body || ""), { x: 0.62, y: y + 0.38, w: 8.8, h: 0.4, fontSize: 9.5, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
      y += 0.92;
    });
    footer(s); tracer(s);
  }
}

// ======================================================================= ROADMAP DECK
function roadmapDeck() {
  const rm = D.roadmap || {};
  const a = D.assumptions || {};
  const regs = D.regimes || {};
  TOTAL = 1 /*title*/ + 1 /*exec*/ + 1 /*overview*/ + 1 /*calendar*/ + 1 /*penalty*/ + 1 /*roadmap*/ + ((rm.priorities || []).length ? 1 : 0);

  titleSlide((REGIME_TITLE.roadmap || {})[LANG] || "Compliance Roadmap",
    "NIS2 " + MIDDOT + " CRA " + MIDDOT + " EU AI Act", "", "unclear");

  // -- exec summary + assumptions
  (function () {
    const s = content(L("eyebrow"), L("execSummary"));
    s.addText(String(rm.exec_summary || ""), { x: 0.4, y: 1.32, w: 9.2, h: 1.5, fontSize: 12, fontFace: FB, color: C.ink, valign: "top", margin: 0 });
    s.addText(L("assumptions").toUpperCase(), { x: 0.4, y: 3.0, w: 9.2, h: 0.26, fontSize: 9, fontFace: FB, color: C.teal, bold: true, charSpacing: 2, margin: 0 });
    const yn = (v) => v === true ? (LANG === "de" ? "Ja" : "Yes") : v === false ? (LANG === "de" ? "Nein" : "No") : (LANG === "de" ? "unklar" : "unknown");
    const rows = [[hdrCell(LANG === "de" ? "ANNAHME" : "ASSUMPTION"), hdrCell(LANG === "de" ? "WERT" : "VALUE")]];
    rows.push([{ text: LANG === "de" ? "Sektor" : "Sector" }, { text: a.sector || EMDASH }]);
    rows.push([{ text: LANG === "de" ? "Größe" : "Size band" }, { text: a.size_band || EMDASH }]);
    rows.push([{ text: LANG === "de" ? "Digitale Produkte?" : "Sells digital products?" }, { text: yn(a.sells_digital_products) }]);
    rows.push([{ text: LANG === "de" ? "Baut/nutzt KI?" : "Builds/deploys AI?" }, { text: yn(a.builds_or_deploys_ai) }]);
    rows.push([{ text: LANG === "de" ? "Länder" : "Countries" }, { text: (a.countries || []).join(", ") || EMDASH }]);
    drawTable(s, rows, { x: 0.4, y: 3.3, w: 9.2, colW: [3.0, 6.2], rowH: 0.32, fontSize: 10 });
    footer(s); tracer(s);
  })();

  // -- three regimes at a glance
  (function () {
    const s = content(L("eyebrow"), L("overview"));
    const rows = [[hdrCell(L("regime")), hdrCell(L("applies")), hdrCell(L("classification")), hdrCell(L("maxFine")), hdrCell(L("nearest"))]];
    ["nis2", "cra", "aiact"].forEach((k) => {
      const r = regs[k] || {};
      const near = (r.deadlines || []).slice().sort((x, y) => String(x.date).localeCompare(String(y.date)))[0];
      const p = r.penalty || {};
      const applies = r.applies === true ? L("applies") : r.applies === false ? L("notApplies") : L("unclear");
      rows.push([
        { text: (REGIME_TITLE[k] || {})[LANG] || k.toUpperCase(), options: { bold: true, color: C.tealDark } },
        { text: applies, options: { bold: true, color: r.applies === true ? C.crit : r.applies === false ? C.dark : C.high } },
        { text: r.classification || L("unclear"), options: { fontSize: 8.5 } },
        { text: (p.essential || EMDASH).split(" of ")[0], options: { fontSize: 8.5 } },
        { text: near ? (fmtDate(near.date)) : EMDASH, options: { fontSize: 8.5 } },
      ]);
    });
    drawTable(s, rows, { x: 0.4, y: 1.4, w: 9.2, colW: [1.9, 1.5, 2.5, 1.7, 1.6], rowH: 0.62, fontSize: 9, valign: "middle" });
    footer(s); tracer(s);
  })();

  // -- merged deadline calendar
  (function () {
    const s = content(L("eyebrow"), L("deadlines"));
    const all = [];
    ["nis2", "cra", "aiact"].forEach((k) => (regs[k] || {}).deadlines?.forEach((d) => all.push({ ...d, regime: (REGIME_TITLE[k] || {}).en || k })));
    all.sort((x, y) => String(x.date).localeCompare(String(y.date)));
    const rows = [[hdrCell(L("date")), hdrCell(L("regime")), hdrCell(L("milestone"))]];
    all.slice(0, 10).forEach((d) => rows.push([
      { text: fmtDate(d.date), options: { bold: true, color: C.tealDark } },
      { text: d.regime, options: { fontSize: 9 } },
      { text: d.label || "", options: { fontSize: 9 } },
    ]));
    if (rows.length === 1) rows.push([{ text: EMDASH }, { text: EMDASH }, { text: L("none") }]);
    drawTable(s, rows, { x: 0.4, y: 1.35, w: 9.2, colW: [1.6, 2.0, 5.6], rowH: 0.36, fontSize: 9.5 });
    footer(s); tracer(s);
  })();

  // -- combined penalty exposure
  (function () {
    const s = content(L("eyebrow"), L("penalty"));
    let cx = 0.4;
    ["nis2", "cra", "aiact"].forEach((k) => {
      const r = regs[k] || {}, p = r.penalty || {};
      s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.5, w: 3.0, h: 2.4, fill: { color: C.tealDark }, line: { type: "none" } });
      s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.5, w: 3.0, h: 0.09, fill: { color: C.crit }, line: { type: "none" } });
      s.addText((REGIME_TITLE[k] || {})[LANG] || k.toUpperCase(), { x: cx + 0.16, y: 1.64, w: 2.7, h: 0.4, fontSize: 12, fontFace: FB, color: C.teal, bold: true, margin: 0 });
      s.addText(String(p.essential || EMDASH), { x: cx + 0.16, y: 2.1, w: 2.7, h: 0.9, fontSize: 13, fontFace: FH, color: C.white, bold: true, valign: "top", margin: 0 });
      s.addText(String(p.important || ""), { x: cx + 0.16, y: 3.0, w: 2.7, h: 0.82, fontSize: 8.5, fontFace: FB, color: C.light, valign: "top", margin: 0 });
      cx += 3.15;
    });
    footer(s); tracer(s);
  })();

  // -- phased roadmap
  (function () {
    const s = content(L("eyebrow"), L("roadmap"));
    const phases = (rm.phases || []).slice(0, 3);
    let cx = 0.4;
    const w = (9.2 - 0.4) / Math.max(1, phases.length);
    phases.forEach((ph) => {
      s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.35, w: w - 0.2, h: 0.5, fill: { color: C.teal }, line: { type: "none" } });
      s.addText(String(ph.when || ""), { x: cx, y: 1.35, w: w - 0.2, h: 0.5, fontSize: 12, fontFace: FB, color: C.black, bold: true, align: "center", valign: "middle", margin: 0 });
      const items = (ph.items || []).slice(0, 6).map((it) => ({ text: it, options: { bullet: { code: "2022" }, fontSize: 9.5, color: C.ink, breakLine: true, paraSpaceAfter: 6 } }));
      s.addText(items.length ? items : [{ text: EMDASH }], { x: cx + 0.05, y: 2.0, w: w - 0.3, h: 3.0, fontFace: FB, valign: "top", margin: 0 });
      cx += w;
    });
    footer(s); tracer(s);
  })();

  // -- priorities
  if ((rm.priorities || []).length) {
    const s = content(L("eyebrow"), L("priorities"));
    const rows = [[hdrCell(L("regime")), hdrCell(LANG === "de" ? "MASSNAHME" : "ACTION"), hdrCell(LANG === "de" ? "WARUM" : "WHY"), hdrCell("COLT")]];
    (rm.priorities || []).slice(0, 6).forEach((p) => rows.push([
      { text: p.regime || "", options: { bold: true, color: C.tealDark, fontSize: 9 } },
      { text: p.action || "", options: { fontSize: 9 } },
      { text: p.why || "", options: { fontSize: 8.5 } },
      { text: p.colt || "", options: { fontSize: 8.5, color: C.tealMid } },
    ]));
    drawTable(s, rows, { x: 0.4, y: 1.4, w: 9.2, colW: [1.4, 3.1, 2.9, 1.8], rowH: 0.55, fontSize: 9, valign: "top" });
    footer(s); tracer(s);
  }
}

// ---- drive ----
if (regimeArg === "roadmap") roadmapDeck();
else regimeDeck(regimeArg);

pres.writeFile({ fileName: outPath }).then(() => {
  console.error("[compliance-deck] wrote " + outPath + " (" + regimeArg + ", " + LANG + ")");
}).catch((e) => { console.error("[compliance-deck] FAILED: " + e.message); process.exit(1); });
