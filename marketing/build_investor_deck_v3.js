// build_investor_deck_v3.js - S4biz Group seed deck, built with pptxgenjs.
//
//   node marketing/build_investor_deck_v3.js [out.pptx]
//
// WHY A THIRD BUILD. The first two used the S4biz technical-brief template: monospace chrome,
// 291 words a slide, zero visuals. That is a capability brief, not a pitch. This one follows the
// DocSend templates the founder supplied (10 x 5.625in, ~14 slides, ~30 words a slide) and the
// pptx skill's design rules: white content slides, one visual per slide, native charts, assertion
// headlines, no accent stripes.
//
// EVERY EXTERNAL NUMBER IS CITED ON THE SLIDE THAT USES IT. Sources, all read 2026-09-25:
//   EASM market  USD 1.74B (2025) -> 6.87B (2030), 31.6% CAGR  Grand View Research
//   MDR market   USD 4.19B (2025) -> 11.3B (2030), 22.0% CAGR  Mordor Intelligence
//   NIS2 scope   160,000+ entities EU (European Commission); ~29,500 Germany (BSI)
//   Breach cost  USD 4.44M global average, IBM Cost of a Data Breach 2025
//   Talent gap   4.8M unfilled roles, ISC2 Cybersecurity Workforce Study 2024
//   Exits        Recorded Future -> Mastercard USD 2.65B (2024); Expanse -> Palo Alto ~USD 0.8B (2020)
//   AI SOC       7AI USD 130M Series A (Dec 2025); Dropzone AI USD 37M Series B (2025); Prophet USD 41M total
// Internal numbers come from the two FACTS files in the partnership folder.
//
// NOTHING HERE IS INVENTED: no revenue, no ARR, no pipeline value, no valuation. The use-of-funds
// split and the hiring phases are the founder's plan and are labelled as a plan.

const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = process.argv[2] ||
  path.join("C:", "Users", "feran", "Downloads", "cybergod partnership", "Investor Pack", "S4biz_Investor_Deck_EN.pptx");

// S4biz palette. No '#', never 8 digits.
const INK = "14161F", VIOLET = "8B5CF6", INDIGO = "4F46E5", CYAN = "22D3EE";
const TXT = "1F2533", MUTED = "6B7280", PANEL = "F3F4F8", LINE = "E5E7EB", WHITE = "FFFFFF";
const GREEN = "16A34A", AMBER = "D97706";
const HFONT = "Arial", BFONT = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";          // 10 x 5.625 in, same canvas as the DocSend templates
pres.author = "S4biz Group";
pres.title = "S4biz Group - Investor Deck";

const W = 10, H = 5.625, M = 0.55;

// ------------------------------------------------------------------ helpers
function base(dark = false) {
  const s = pres.addSlide();
  s.background = { color: dark ? INK : WHITE };
  // wordmark, top right. Two runs so the "S4" carries the accent.
  s.addText([{ text: "S4", options: { color: dark ? CYAN : VIOLET } },
             { text: "BIZ", options: { color: dark ? WHITE : INK } }],
            { x: W - M - 1.2, y: 0.22, w: 1.2, h: 0.32, fontFace: HFONT, fontSize: 13, bold: true,
              align: "right", margin: 0, isTextBox: true });
  return s;
}
function eyebrow(s, t, dark = false) {
  s.addText(t.toUpperCase(), { x: M, y: 0.28, w: 6, h: 0.25, fontFace: HFONT, fontSize: 9, bold: true,
    color: dark ? CYAN : VIOLET, charSpacing: 2, margin: 0, isTextBox: true });
}
function headline(s, t, dark = false, size = 28, y = 0.62) {
  if (t.length > 42) throw new Error("headline wraps to two lines and hits the sub-line (" + t.length + " chars): " + t);
  s.addText(t, { x: M, y, w: W - 2 * M, h: 0.9, fontFace: HFONT, fontSize: size, bold: true,
    color: dark ? WHITE : INK, valign: "top", margin: 0, isTextBox: true });
}
function sub(s, t, dark = false, y = 1.42) {
  s.addText(t, { x: M, y, w: W - 2 * M, h: 0.45, fontFace: BFONT, fontSize: 13,
    color: dark ? "C7CDDA" : MUTED, valign: "top", margin: 0, isTextBox: true });
}
function source(s, t, dark = false) {
  s.addText(t, { x: M, y: H - 0.42, w: W - 2 * M - 0.6, h: 0.25, fontFace: BFONT, fontSize: 8,
    color: dark ? "8E97A8" : "9CA3AF", margin: 0, isTextBox: true });
}
function pageno(s, n, dark = false) {
  s.addText(String(n), { x: W - M - 0.5, y: H - 0.42, w: 0.5, h: 0.25, fontFace: BFONT, fontSize: 8,
    color: dark ? "8E97A8" : "9CA3AF", align: "right", margin: 0, isTextBox: true });
}
function stat(s, x, y, w, big, label, color = VIOLET, dark = false) {
  s.addText(big, { x, y, w, h: 0.75, fontFace: HFONT, fontSize: 40, bold: true, color, margin: 0, isTextBox: true });
  s.addText(label, { x, y: y + 0.78, w, h: 0.5, fontFace: BFONT, fontSize: 11,
    color: dark ? "C7CDDA" : MUTED, margin: 0, isTextBox: true, valign: "top" });
}
function card(s, x, y, w, h, title, body, accent = VIOLET, titleSize = 13) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: PANEL }, line: { color: PANEL }, rectRadius: 0.08 });
  s.addShape(pres.ShapeType.ellipse, { x: x + 0.2, y: y + 0.2, w: 0.22, h: 0.22, fill: { color: accent }, line: { color: accent } });
  s.addText(title, { x: x + 0.52, y: y + 0.14, w: w - 0.7, h: 0.36, fontFace: HFONT, fontSize: titleSize, bold: true,
    color: INK, margin: 0, isTextBox: true, valign: "middle" });
  s.addText(body, { x: x + 0.2, y: y + 0.58, w: w - 0.4, h: h - 0.72, fontFace: BFONT, fontSize: 11,
    color: TXT, margin: 0, isTextBox: true, valign: "top" });
}
function row(s, y, title, body, accent = VIOLET, x = M, w = W - 2 * M) {
  s.addShape(pres.ShapeType.ellipse, { x, y: y + 0.05, w: 0.3, h: 0.3, fill: { color: accent }, line: { color: accent } });
  s.addText(title, { x: x + 0.45, y, w: w - 0.45, h: 0.3, fontFace: HFONT, fontSize: 12.5, bold: true, color: INK,
    margin: 0, isTextBox: true, valign: "middle" });
  s.addText(body, { x: x + 0.45, y: y + 0.31, w: w - 0.45, h: 0.5, fontFace: BFONT, fontSize: 11, color: TXT,
    margin: 0, isTextBox: true, valign: "top" });
}
function table(s, x, y, w, rows, colW, opts = {}) {
  const head = rows[0].map(c => ({ text: c, options: { bold: true, color: MUTED, fontSize: 9, fontFace: HFONT,
    fill: { color: WHITE }, border: { type: "solid", pt: 0.75, color: LINE } } }));
  const body = rows.slice(1).map((r, i) => r.map((c, j) => ({ text: c, options: {
    fontSize: opts.fs || 10.5, fontFace: j === 0 ? HFONT : BFONT, bold: j === 0, color: j === 0 ? INK : TXT,
    fill: { color: i % 2 ? WHITE : PANEL }, border: { type: "solid", pt: 0.5, color: LINE } } })));
  s.addTable([head, ...body], { x, y, w, colW, rowH: opts.rowH || 0.36, margin: 0.06, valign: "middle" });
}

let n = 0;

// ================================================================== 1 COVER (dark)
{
  const s = base(true); n++;
  s.addText("S4biz Group", { x: M, y: 1.35, w: 8, h: 0.4, fontFace: HFONT, fontSize: 14, bold: true, color: CYAN,
    charSpacing: 2, margin: 0, isTextBox: true });
  s.addText("Every company is already visible to attackers.\nWe show them what is visible. Then we defend it.",
    { x: M, y: 1.85, w: 8.9, h: 1.6, fontFace: HFONT, fontSize: 30, bold: true, color: WHITE, margin: 0, isTextBox: true, valign: "top" });
  s.addText("cybergod.ai  ·  Perseus AI SOC", { x: M, y: 3.6, w: 8, h: 0.35, fontFace: BFONT, fontSize: 15, color: "C7CDDA", margin: 0, isTextBox: true });
  s.addText("Seed round  ·  Raising EUR 20M  ·  September 2026", { x: M, y: 4.05, w: 8, h: 0.35, fontFace: BFONT, fontSize: 13, color: VIOLET, margin: 0, isTextBox: true });
  source(s, "Confidential. Prepared for prospective investors.", true); pageno(s, n, true);
}

// ================================================================== 2 COMPANY PURPOSE
{
  const s = base(); n++;
  eyebrow(s, "Company purpose");
  s.addText("Make external cyber risk visible in minutes, priced in euros, and defended automatically.",
    { x: M, y: 1.0, w: 8.9, h: 1.7, fontFace: HFONT, fontSize: 28, bold: true, color: INK, margin: 0, isTextBox: true, valign: "top" });
  const items = [["SEE", "cybergod.ai finds what the internet already knows about a company, from one name, in about two minutes, touching nothing."],
                 ["PRICE", "It converts every exposure into an annual loss figure and a regulatory clock a board can act on."],
                 ["DEFEND", "Perseus AI SOC then defends what stays exposed, on the customer's own infrastructure, deciding for itself."]];
  items.forEach((it, i) => card(s, M + i * 3.0, 3.05, 2.85, 1.7, it[0], it[1], [VIOLET, INDIGO, CYAN][i]));
  pageno(s, n);
}

// ================================================================== 3 PROBLEM
{
  const s = base(); n++;
  eyebrow(s, "The problem");
  headline(s, "A company cannot see what attackers see.");
  sub(s, "The exposure picture is assembled by hand, once a year, and it is stale within a week. Meanwhile the attacks arrive every day, automatically.");
  stat(s, M, 2.15, 2.9, "42,369", "attack-shaped requests in 14 days\nagainst one small estate of six domains", VIOLET);
  stat(s, M + 3.0, 2.15, 2.9, "551", "distinct paths tried by a single address,\nusing 143 different announced browsers", INDIGO);
  stat(s, M + 6.0, 2.15, 2.9, "$4.44M", "global average cost of one breach,\nIBM 2025", CYAN);
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 3.85, w: W - 2 * M, h: 0.95, fill: { color: PANEL }, line: { color: PANEL }, rectRadius: 0.08 });
  s.addText("The stack a company already owns judges one request at a time. A firewall sees ports. A WAF sees payloads. None of them models one client over time, which is exactly what a scanner is.",
    { x: M + 0.25, y: 3.95, w: W - 2 * M - 0.5, h: 0.75, fontFace: BFONT, fontSize: 12, color: TXT, margin: 0, isTextBox: true, valign: "middle" });
  source(s, "Attack figures: our own estate, measured 2026-09-13 (attack_digest). Breach cost: IBM Cost of a Data Breach Report 2025."); pageno(s, n);
}

// ================================================================== 4 TWO SOLUTIONS
{
  const s = base(); n++;
  eyebrow(s, "The solution");
  headline(s, "See it. Then defend it.");
  // left: SEE
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.55, w: 4.3, h: 3.4, fill: { color: PANEL }, line: { color: PANEL }, rectRadius: 0.1 });
  s.addText("1", { x: M + 0.25, y: 1.7, w: 0.6, h: 0.6, fontFace: HFONT, fontSize: 34, bold: true, color: VIOLET, margin: 0, isTextBox: true });
  s.addText("cybergod.ai", { x: M + 0.9, y: 1.72, w: 3, h: 0.35, fontFace: HFONT, fontSize: 16, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("See it.", { x: M + 0.9, y: 2.05, w: 3, h: 0.3, fontFace: BFONT, fontSize: 12, color: VIOLET, margin: 0, isTextBox: true });
  s.addText([
    { text: "One company name in. Four board decks out.", options: { bold: true, breakLine: true } },
    { text: "Finds networks, domains and certificates itself from public sources. Prices the risk in euros. Names the attacker groups whose methods match. Checks NIS2, CRA and the EU AI Act.", options: { breakLine: true } },
    { text: "About two minutes. Nothing installed. No authorisation needed.", options: { color: MUTED } },
  ], { x: M + 0.25, y: 2.5, w: 3.8, h: 2.3, fontFace: BFONT, fontSize: 11.5, color: TXT, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 6 });
  // right: DEFEND
  s.addShape(pres.ShapeType.roundRect, { x: M + 4.6, y: 1.55, w: 4.3, h: 3.4, fill: { color: INK }, line: { color: INK }, rectRadius: 0.1 });
  s.addText("2", { x: M + 4.85, y: 1.7, w: 0.6, h: 0.6, fontFace: HFONT, fontSize: 34, bold: true, color: CYAN, margin: 0, isTextBox: true });
  s.addText("Perseus AI SOC", { x: M + 5.5, y: 1.72, w: 3.2, h: 0.35, fontFace: HFONT, fontSize: 16, bold: true, color: WHITE, margin: 0, isTextBox: true });
  s.addText("Defend it.", { x: M + 5.5, y: 2.05, w: 3, h: 0.3, fontFace: BFONT, fontSize: 12, color: CYAN, margin: 0, isTextBox: true });
  s.addText([
    { text: "An automated SOC that decides for itself.", options: { bold: true, breakLine: true } },
    { text: "Watches every request, blocks scanners, revises its own rules nightly and weekly. Four AI models from four vendors propose; deterministic code decides.", options: { breakLine: true } },
    { text: "Runs on the customer's own infrastructure. Replaces nothing they own.", options: { color: "C7CDDA" } },
  ], { x: M + 4.85, y: 2.5, w: 3.8, h: 2.3, fontFace: BFONT, fontSize: 11.5, color: "E5E7EB", margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 6 });
  pageno(s, n);
}

// ================================================================== 5 MARKET SIZE
{
  const s = base(); n++;
  eyebrow(s, "Market");
  headline(s, "Two growing markets, one stack.");
  sub(s, "Attack surface management and managed detection are both compounding above 20% a year. We sell into both with one engine.");
  s.addChart(pres.ChartType.bar, [
    { name: "2025", labels: ["Attack surface mgmt", "Managed detection (MDR)"], values: [1.74, 4.19] },
    { name: "2030", labels: ["Attack surface mgmt", "Managed detection (MDR)"], values: [6.87, 11.3] },
  ], { x: M, y: 1.95, w: 5.4, h: 2.95, barDir: "col", barGrouping: "clustered",
       chartColors: [VIOLET, CYAN], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: TXT,
       dataLabelFormatCode: '"$"0.0"B"', catAxisLabelColor: TXT, catAxisLabelFontSize: 10, valAxisHidden: true,
       valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: true, legendPos: "t", legendFontSize: 10,
       legendColor: MUTED, showTitle: false });
  // right column: the regulatory demand driver
  s.addText("160,000+", { x: 6.3, y: 2.0, w: 3.2, h: 0.7, fontFace: HFONT, fontSize: 34, bold: true, color: INDIGO, margin: 0, isTextBox: true });
  s.addText("entities across the EU now in scope of NIS2, each one required to evidence its cyber risk management. About 29,500 in Germany alone.",
    { x: 6.3, y: 2.72, w: 3.2, h: 1.0, fontFace: BFONT, fontSize: 11, color: TXT, margin: 0, isTextBox: true, valign: "top" });
  s.addText("31.6%", { x: 6.3, y: 3.8, w: 1.5, h: 0.5, fontFace: HFONT, fontSize: 22, bold: true, color: VIOLET, margin: 0, isTextBox: true });
  s.addText("ASM CAGR", { x: 6.3, y: 4.28, w: 1.5, h: 0.3, fontFace: BFONT, fontSize: 9, color: MUTED, margin: 0, isTextBox: true });
  s.addText("22.0%", { x: 7.9, y: 3.8, w: 1.5, h: 0.5, fontFace: HFONT, fontSize: 22, bold: true, color: CYAN, margin: 0, isTextBox: true });
  s.addText("MDR CAGR", { x: 7.9, y: 4.28, w: 1.5, h: 0.3, fontFace: BFONT, fontSize: 9, color: MUTED, margin: 0, isTextBox: true });
  source(s, "USD billions. ASM: Grand View Research, 2025 to 2030. MDR: Mordor Intelligence, 2025 to 2030. NIS2 scope: European Commission; Germany: BSI."); pageno(s, n);
}

// ================================================================== 6 COMPETITION
{
  const s = base(); n++;
  eyebrow(s, "Competition and why we win");
  headline(s, "Validated category, underserved buyer.");
  sub(s, "Large exits and large rounds prove the budget exists. Every one of them sells a platform to a CISO. We arm the partner who is already in the room.");
  table(s, M, 1.95, 5.3, [
    ["Who", "What they did", "Sells to"],
    ["Recorded Future", "Acquired by Mastercard, USD 2.65B, 2024", "CISO, threat intel"],
    ["Expanse", "Acquired by Palo Alto, ~USD 0.8B, 2020", "CISO, attack surface"],
    ["Bitsight", "Last valuation USD 2.4B", "Risk teams, ratings"],
    ["7AI", "USD 130M Series A, Dec 2025", "SOC teams, AI triage"],
    ["Dropzone AI", "USD 37M Series B, 2025", "SOC teams, AI triage"],
  ], [1.35, 2.55, 1.4], { fs: 9.5, rowH: 0.34 });
  // right: how we differ, as architecture
  const diff = [["Different buyer", "MSPs, VARs and consultancies resell it white-labelled. A first meeting costs them EUR 100, not a procurement cycle."],
                ["Different unit", "Priced per run and per protected application, so it is buyable at 40 seats. The category's rate cards thin out below 300."],
                ["Different footprint", "Nothing installed, nothing scanned, no authorisation. Then an SOC that runs on the customer's own infrastructure, EU-resident."]];
  diff.forEach((d, i) => row(s, 2.0 + i * 0.95, d[0], d[1], [VIOLET, INDIGO, CYAN][i], 6.15, 3.35));
  source(s, "Deal values: Mastercard and Palo Alto Networks press releases; Bitsight, 7AI and Dropzone AI company announcements. Compared on what each is built for, not on a benchmark."); pageno(s, n);
}

// ================================================================== 7 WHY NOW
{
  const s = base(); n++;
  eyebrow(s, "Why now");
  headline(s, "Three clocks started at once.");
  const cols = [
    ["Regulation has dates", "NIS2 is in force across the EU. DORA applies to financial entities. The Cyber Resilience Act and the EU AI Act follow. 160,000 entities need evidence, not adjectives.", VIOLET],
    ["Attacks are automated", "About 3,000 attack-shaped requests a day against an estate nobody has heard of. One address, 143 browser identities. That is software, and it does not sleep.", INDIGO],
    ["Defenders are scarce", "4.8 million unfilled security roles worldwide. The market answered with USD 130M and USD 37M rounds into AI SOC startups in 2025. The category is now real.", CYAN],
  ];
  cols.forEach((c, i) => {
    const x = M + i * 3.0;
    s.addShape(pres.ShapeType.ellipse, { x, y: 1.7, w: 0.5, h: 0.5, fill: { color: c[2] }, line: { color: c[2] } });
    s.addText(String(i + 1), { x, y: 1.7, w: 0.5, h: 0.5, fontFace: HFONT, fontSize: 16, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(c[0], { x, y: 2.35, w: 2.8, h: 0.4, fontFace: HFONT, fontSize: 14, bold: true, color: INK, margin: 0, isTextBox: true });
    s.addText(c[1], { x, y: 2.8, w: 2.8, h: 1.9, fontFace: BFONT, fontSize: 11.5, color: TXT, margin: 0, isTextBox: true, valign: "top" });
  });
  source(s, "NIS2: European Commission. Attack rate: our own measurement, 2026-09-13. Talent gap: ISC2 Workforce Study 2024. Rounds: 7AI, Dropzone AI announcements."); pageno(s, n);
}

// ================================================================== 8 PRODUCT ONE
{
  const s = base(); n++;
  eyebrow(s, "Product one  ·  cybergod.ai");
  headline(s, "One name in. Four decks out.");
  // pipeline diagram: 4 boxes with arrows
  const steps = [["INPUT", "One company\nname or domain", VIOLET], ["DISCOVER", "Networks, domains,\ncertificates, from\n10 public sources", INDIGO],
                 ["PROVE", "15 ownership gates:\nonly what is theirs\nreaches the deck", INDIGO], ["WRITE", "4 models, 4 vendors.\nA different vendor\naudits the author", CYAN]];
  steps.forEach((st, i) => {
    const x = M + i * 2.3;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.75, w: 2.0, h: 1.35, fill: { color: PANEL }, line: { color: PANEL }, rectRadius: 0.08 });
    s.addText(st[0], { x: x + 0.15, y: 1.85, w: 1.7, h: 0.3, fontFace: HFONT, fontSize: 10, bold: true, color: st[2], charSpacing: 1, margin: 0, isTextBox: true });
    s.addText(st[1], { x: x + 0.15, y: 2.15, w: 1.75, h: 0.9, fontFace: BFONT, fontSize: 10.5, color: TXT, margin: 0, isTextBox: true, valign: "top" });
    if (i < 3) s.addShape(pres.ShapeType.rightArrow, { x: x + 2.02, y: 2.3, w: 0.26, h: 0.25, fill: { color: LINE }, line: { color: LINE } });
  });
  // outputs
  const outs = [["Findings", "What is exposed, with evidence"], ["C-BIQ", "What it costs, in euros a year"], ["GEOPOL", "Which groups' methods match"], ["Compliance", "NIS2, CRA, AI Act, DORA clocks"]];
  s.addText("WHAT COMES BACK, IN ABOUT TWO MINUTES", { x: M, y: 3.3, w: 6, h: 0.25, fontFace: HFONT, fontSize: 9, bold: true, color: MUTED, charSpacing: 1, margin: 0, isTextBox: true });
  outs.forEach((o, i) => {
    const x = M + i * 2.3;
    s.addText(o[0], { x, y: 3.6, w: 2.1, h: 0.3, fontFace: HFONT, fontSize: 13, bold: true, color: INK, margin: 0, isTextBox: true });
    s.addText(o[1], { x, y: 3.9, w: 2.1, h: 0.5, fontFace: BFONT, fontSize: 10.5, color: TXT, margin: 0, isTextBox: true, valign: "top" });
  });
  s.addText("No scanning, no probing, no authentication attempt against the company. So a partner can assess a prospect before the first conversation.",
    { x: M, y: 4.5, w: W - 2 * M, h: 0.5, fontFace: BFONT, fontSize: 11, italic: true, color: VIOLET, margin: 0, isTextBox: true });
  pageno(s, n);
}

// ================================================================== 9 PRODUCT TWO
{
  const s = base(); n++;
  eyebrow(s, "Product two  ·  Perseus AI SOC");
  headline(s, "Models propose. Code decides.");
  sub(s, "An SOC that runs itself on the customer's own infrastructure. Three loops, one gate, and nothing a model says ever becomes a side effect on its own.");
  const loops = [["Every 10 min", "Four models from four vendors review one live incident and propose a detection rule.", VIOLET],
                 ["Every night", "Scores the day's traffic, promotes rules that earned it, demotes any that touched a real visitor.", INDIGO],
                 ["Every week", "Re-checks every live rule against the routes the app serves this week. Retires what went stale.", CYAN]];
  loops.forEach((l, i) => card(s, M + i * 3.0, 2.0, 2.85, 1.55, l[0], l[1], l[2]));
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 3.75, w: W - 2 * M, h: 1.1, fill: { color: INK }, line: { color: INK }, rectRadius: 0.08 });
  s.addText("THE GATE A RULE MUST PASS TO BLOCK ANYTHING", { x: M + 0.25, y: 3.85, w: 8, h: 0.25, fontFace: HFONT, fontSize: 9, bold: true, color: CYAN, charSpacing: 1, margin: 0, isTextBox: true });
  s.addText("24 hours in detection   ·   3 of 4 vendors agree   ·   at least 1 real hostile match   ·   exactly 0 matches against real visitors",
    { x: M + 0.25, y: 4.12, w: 8.5, h: 0.35, fontFace: BFONT, fontSize: 12, bold: true, color: WHITE, margin: 0, isTextBox: true });
  s.addText("One legitimate hit kills a rule permanently. It never touches a firewall. Every block expires by itself.",
    { x: M + 0.25, y: 4.47, w: 8.5, h: 0.3, fontFace: BFONT, fontSize: 10.5, color: "C7CDDA", margin: 0, isTextBox: true });
  pageno(s, n);
}

// ================================================================== 10 TRACTION
{
  const s = base(); n++;
  eyebrow(s, "Traction");
  headline(s, "Built, running, and in front of buyers.");
  stat(s, M, 1.55, 2.2, "2", "products in production", VIOLET);
  stat(s, M + 2.3, 1.55, 2.2, "22", "companies assessed, Jun to Aug 2026", INDIGO);
  stat(s, M + 4.6, 1.55, 2.2, "5", "live properties defended by Perseus", CYAN);
  stat(s, M + 6.9, 1.55, 2.2, "6", "markets in active conversation", GREEN);
  table(s, M, 2.95, W - 2 * M, [
    ["Account", "Market", "What they are", "Stage"],
    ["byon GmbH (360 ITC group)", "Germany", "MSP, 130 staff, 2,300 B2B customers", "Proposal delivered, 20-domain pilot proposed"],
    ["Objectale GmbH", "Switzerland", "Reseller; sells a run at CHF 900", "Distribution agreement in final draft"],
    ["Cybernet, TechMaster", "Angola", "Security integrators", "Channel partnership in progress, Africa pilot"],
    ["RBC", "Canada", "Tier-1 bank", "Technical evaluation with security engineering"],
    ["MTS, Balticom", "Baltics, CIS", "Telecom operators", "OEM and business-case material delivered"],
  ], [2.25, 1.15, 2.7, 2.8], { fs: 9.5, rowH: 0.3 });
  source(s, "Stages as of September 2026. Objectale's CHF 900 resale price is the strongest evidence the list price has headroom."); pageno(s, n);
}

// ================================================================== 11 GO TO MARKET
{
  const s = base(); n++;
  eyebrow(s, "Go to market");
  headline(s, "We arm the partner, not the CISO.");
  sub(s, "Channel-led and white-labelled. The partner's brand is on every deck; the engine works underneath. Our sales team sells partners, and each partner sells hundreds of customers.");
  const who = [["MSPs", "A recurring external-risk module for their whole base, every quarter."],
               ["VARs", "A EUR 200 a month subscription that shows a client their holes, then sells what closes them."],
               ["Integrators", "Entry due diligence before a major contract, an M&A deal or an audit."],
               ["Consultancies", "NIS2, CRA and AI Act readiness in minutes, a finished client deck instead of weeks."]];
  who.forEach((w, i) => card(s, M + (i % 2) * 4.55, 2.05 + Math.floor(i / 2) * 1.2, 4.4, 1.1, w[0], w[1], [VIOLET, INDIGO, CYAN, GREEN][i], 12));
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 4.5, w: W - 2 * M, h: 0.55, fill: { color: PANEL }, line: { color: PANEL }, rectRadius: 0.08 });
  s.addText([{ text: "The door opener: ", options: { bold: true, color: VIOLET } },
             { text: "a EUR 100 run against a prospect's own name, before the first meeting. Then a review, a workshop, a subscription, and remediation that is the partner's own business." }],
    { x: M + 0.2, y: 4.55, w: W - 2 * M - 0.4, h: 0.45, fontFace: BFONT, fontSize: 11, color: TXT, margin: 0, isTextBox: true, valign: "middle" });
  pageno(s, n);
}

// ================================================================== 12 TEAM
{
  const s = base(); n++;
  eyebrow(s, "Team");
  headline(s, "Twenty years on the attacker side.");
  // founder block
  s.addShape(pres.ShapeType.ellipse, { x: M, y: 1.7, w: 1.1, h: 1.1, fill: { color: INK }, line: { color: INK } });
  s.addText("EV", { x: M, y: 1.7, w: 1.1, h: 1.1, fontFace: HFONT, fontSize: 24, bold: true, color: CYAN, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText("Evgeny \"Jev\" Vainshtein", { x: M + 1.35, y: 1.7, w: 4, h: 0.35, fontFace: HFONT, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("Founder and principal architect. Built both products. Eight production languages, five companies founded.",
    { x: M + 1.35, y: 2.05, w: 4.2, h: 0.75, fontFace: BFONT, fontSize: 11, color: TXT, margin: 0, isTextBox: true, valign: "top" });
  const dom = [["OFFENSIVE CYBER", "Cognyte · Cyberbit · Intellexa", VIOLET],
               ["HYPERSCALE CLOUD", "AWS · Red Hat · NetApp · Huawei · Canonical", INDIGO],
               ["TIER-1 NETWORKS", "Colt · Cogent · Telefonica · Deutsche Telekom", CYAN]];
  dom.forEach((d, i) => {
    const y = 3.0 + i * 0.5;
    s.addShape(pres.ShapeType.ellipse, { x: M, y: y + 0.07, w: 0.2, h: 0.2, fill: { color: d[2] }, line: { color: d[2] } });
    s.addText(d[0], { x: M + 0.35, y, w: 1.9, h: 0.35, fontFace: HFONT, fontSize: 9.5, bold: true, color: MUTED, charSpacing: 1, margin: 0, isTextBox: true, valign: "middle" });
    s.addText(d[1], { x: M + 2.3, y, w: 3.4, h: 0.35, fontFace: BFONT, fontSize: 11.5, color: INK, margin: 0, isTextBox: true, valign: "middle" });
  });
  s.addText("The product needs all three. Almost nobody has all three.", { x: M, y: 4.55, w: 5.5, h: 0.35, fontFace: BFONT, fontSize: 11.5, italic: true, color: VIOLET, margin: 0, isTextBox: true });
  // right: channel partners + first hires
  s.addShape(pres.ShapeType.roundRect, { x: 6.3, y: 1.7, w: 3.2, h: 3.2, fill: { color: PANEL }, line: { color: PANEL }, rectRadius: 0.1 });
  s.addText("CHANNEL PARTNERS", { x: 6.5, y: 1.85, w: 2.9, h: 0.25, fontFace: HFONT, fontSize: 9, bold: true, color: MUTED, charSpacing: 1, margin: 0, isTextBox: true });
  s.addText([{ text: "Assad Kondakji", options: { bold: true, breakLine: true } }, { text: "Commercial lead, Africa and Middle East", options: { breakLine: true, color: MUTED } },
             { text: "Dima Diall", options: { bold: true, breakLine: true } }, { text: "Partnerships and legal, Africa", options: { color: MUTED } }],
    { x: 6.5, y: 2.12, w: 2.9, h: 1.2, fontFace: BFONT, fontSize: 10.5, color: INK, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 2 });
  s.addText("FIRST HIRES WITH THIS ROUND", { x: 6.5, y: 3.35, w: 2.9, h: 0.25, fontFace: HFONT, fontSize: 9, bold: true, color: MUTED, charSpacing: 1, margin: 0, isTextBox: true });
  s.addText([{ text: "VP Sales, DACH and Nordics", options: { bullet: true, breakLine: true } },
             { text: "Head of Cloud Engineering", options: { bullet: true, breakLine: true } },
             { text: "Partner manager, EU channel", options: { bullet: true, breakLine: true } },
             { text: "Head of Marketing", options: { bullet: true } }],
    { x: 6.5, y: 3.62, w: 2.9, h: 1.2, fontFace: BFONT, fontSize: 10.5, color: INK, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 2 });
  pageno(s, n);
}

// ================================================================== 13 BUSINESS MODEL
{
  const s = base(); n++;
  eyebrow(s, "Business model");
  headline(s, "Recurring revenue, partner-led.");
  table(s, M, 1.55, 4.4, [
    ["cybergod.ai", "List"],
    ["Single run, one company", "EUR 100"],
    ["Report subscription, per seat / month", "EUR 200"],
    ["Findings review, per hour", "EUR 200"],
    ["Workshop, per day", "EUR 2,500"],
  ], [3.1, 1.3], { fs: 10, rowH: 0.34 });
  table(s, 5.15, 1.55, 4.3, [
    ["Perseus AI SOC", "List / month"],
    ["SENTRY, detection, up to 3 apps", "EUR 450"],
    ["SHIELD, enforcement, up to 10 apps", "EUR 1,200"],
    ["CITADEL, plus integration, 25 apps", "EUR 2,900"],
    ["30-day pilot, detection only", "Free"],
  ], [3.0, 1.3], { fs: 10, rowH: 0.34 });
  s.addText("PARTNER LADDER", { x: M, y: 3.5, w: 3, h: 0.25, fontFace: HFONT, fontSize: 9, bold: true, color: MUTED, charSpacing: 1, margin: 0, isTextBox: true });
  const tiers = [["Partner", "10%"], ["VAR", "20%"], ["Gold", "30%"], ["Platinum", "40%"], ["OEM", "50%"]];
  tiers.forEach((t, i) => {
    const x = M + i * 1.78;
    s.addShape(pres.ShapeType.roundRect, { x, y: 3.8, w: 1.65, h: 0.62, fill: { color: PANEL }, line: { color: PANEL }, rectRadius: 0.06 });
    s.addText(t[1], { x: x + 0.12, y: 3.83, w: 0.75, h: 0.55, fontFace: HFONT, fontSize: 18, bold: true, color: [VIOLET, VIOLET, INDIGO, INDIGO, CYAN][i], margin: 0, isTextBox: true, valign: "middle" });
    s.addText(t[0], { x: x + 0.85, y: 3.83, w: 0.75, h: 0.55, fontFace: BFONT, fontSize: 10.5, color: TXT, margin: 0, isTextBox: true, valign: "middle" });
  });
  s.addText("Delivery cost is close to zero: the engine does the work, and Perseus's model spend is under USD 9 a month at its absolute ceiling. Nothing is perpetual, because the defences change daily.",
    { x: M, y: 4.55, w: W - 2 * M, h: 0.5, fontFace: BFONT, fontSize: 11, color: TXT, margin: 0, isTextBox: true, valign: "top" });
  pageno(s, n);
}

// ================================================================== 14 BOOTSTRAPPED
{
  const s = base(); n++;
  eyebrow(s, "Where we are");
  headline(s, "Two products, zero outside capital.");
  sub(s, "Bootstrapped to this point by the founder. What exists today was built without a single external euro.");
  const built = [["Two products in production", "cybergod.ai assessing, Perseus defending five live properties, 264 tests behind the SOC."],
                 ["A complete commercial pack", "Price lists, partner tiers, white papers, service descriptions, and a seven-agreement legal pack under Estonian law."],
                 ["Four entities, four countries", "Estonia, Germany, Portugal and Delaware. EU data residency by design, servers in Frankfurt."],
                 ["A channel forming on three continents", "Germany, Switzerland, Canada, Angola, the Baltics. Partners at proposal and agreement stage."]];
  built.forEach((b, i) => row(s, 2.0 + i * 0.7, b[0], b[1], [VIOLET, INDIGO, CYAN, GREEN][i]));
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 4.55, w: W - 2 * M, h: 0.5, fill: { color: INK }, line: { color: INK }, rectRadius: 0.08 });
  s.addText("Pre-revenue by design: the products were finished before the first contract was signed. The round turns a finished product into a sales organisation.",
    { x: M + 0.2, y: 4.58, w: W - 2 * M - 0.4, h: 0.44, fontFace: BFONT, fontSize: 11, color: WHITE, margin: 0, isTextBox: true, valign: "middle" });
  pageno(s, n);
}

// ================================================================== 15 USE OF FUNDS
{
  const s = base(); n++;
  eyebrow(s, "Use of funds");
  headline(s, "EUR 20M builds the sales machine.");
  s.addChart(pres.ChartType.doughnut, [
    { name: "Use of funds", labels: ["Sales and channel", "Engineering and cloud", "Marketing", "Assurance and certification", "Working capital"], values: [40, 30, 15, 5, 10] },
  ], { x: M - 0.1, y: 1.55, w: 3.9, h: 3.5, holeSize: 55, chartColors: [VIOLET, INDIGO, CYAN, GREEN, "9CA3AF"],
       showValue: true, dataLabelFormatCode: '0"%"', dataLabelColor: WHITE, dataLabelFontSize: 11, dataLabelFontBold: true,
       showLegend: false, showTitle: false, showPercent: false });
  const uses = [["40%  Sales and channel", "Direct enterprise sales plus partner enablement across DACH, Nordics, Iberia, and the Africa channel.", VIOLET],
                ["30%  Engineering and cloud", "Continuous monitoring, cloud posture, customer-held keys, enforcement and takedown, and the third product.", INDIGO],
                ["15%  Marketing", "Category presence, content and events behind the channel.", CYAN],
                ["5%  Assurance", "ISO 27001, SOC 2, a second EU hosting region.", GREEN],
                ["10%  Working capital", "Finance, legal and operations across four entities.", "9CA3AF"]];
  uses.forEach((u, i) => {
    const y = 1.6 + i * 0.68;
    s.addShape(pres.ShapeType.ellipse, { x: 4.5, y: y + 0.06, w: 0.22, h: 0.22, fill: { color: u[2] }, line: { color: u[2] } });
    s.addText(u[0], { x: 4.85, y, w: 4.6, h: 0.3, fontFace: HFONT, fontSize: 11.5, bold: true, color: INK, margin: 0, isTextBox: true, valign: "middle" });
    s.addText(u[1], { x: 4.85, y: y + 0.29, w: 4.6, h: 0.4, fontFace: BFONT, fontSize: 10, color: TXT, margin: 0, isTextBox: true, valign: "top" });
  });
  source(s, "Allocation is the plan for this round. 36-month horizon: year one the commercial core and first engineering, year two regional coverage and assurance, year three scale across all four locations."); pageno(s, n);
}

// ================================================================== 16 THE ASK (dark)
{
  const s = base(true); n++;
  eyebrow(s, "The ask", true);
  s.addText("EUR 20,000,000", { x: M, y: 0.95, w: 8, h: 0.9, fontFace: HFONT, fontSize: 44, bold: true, color: WHITE, margin: 0, isTextBox: true });
  s.addText("Seed round. To scale sales and marketing, take the product to cloud, and staff four offices that are already incorporated.",
    { x: M, y: 1.9, w: 8.5, h: 0.6, fontFace: BFONT, fontSize: 14, color: "C7CDDA", margin: 0, isTextBox: true, valign: "top" });
  const ms = [["12 months", "Commercial core hired. First customers under contract on both products.", VIOLET],
              ["24 months", "Cloud product shipped. Regional sales coverage. ISO 27001 and SOC 2 under way.", INDIGO],
              ["36 months", "Third product built. Scale across Tallinn, Frankfurt, Lisbon and Delaware.", CYAN]];
  ms.forEach((m, i) => {
    const x = M + i * 3.0;
    s.addText(m[0], { x, y: 2.75, w: 2.8, h: 0.35, fontFace: HFONT, fontSize: 13, bold: true, color: m[2], margin: 0, isTextBox: true });
    s.addText(m[1], { x, y: 3.1, w: 2.8, h: 0.8, fontFace: BFONT, fontSize: 11, color: "E5E7EB", margin: 0, isTextBox: true, valign: "top" });
  });
  s.addText("Next step: pick any company name. We run it in front of you, live, in two minutes.",
    { x: M, y: 4.1, w: 8.5, h: 0.4, fontFace: BFONT, fontSize: 13, bold: true, color: CYAN, margin: 0, isTextBox: true });
  s.addText("Evgeny \"Jev\" Vainshtein  ·  feranicus@s4biz.io  ·  cybergod.ai", { x: M, y: 4.55, w: 8.5, h: 0.35, fontFace: BFONT, fontSize: 12, color: "C7CDDA", margin: 0, isTextBox: true });
  source(s, "Stars4business OU (Estonia) is the contracting entity. S4biz UG (Germany), S4BIZ Lda (Portugal), CyberGod LLC (Delaware).", true); pageno(s, n, true);
}

pres.writeFile({ fileName: OUT }).then(() => console.log("built " + OUT + " (" + n + " slides)"));
