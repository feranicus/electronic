// tools/partners_gate.mjs — the blocking gate for /partners, in all six languages.
//
//   node tools/partners_gate.mjs
//
// WHY A GATE AT ALL, and why these specific checks:
//
// 1. STRUCTURE. Partners.jsx renders a DATA OBJECT, so a translator editing a locale file can
//    delete a column, drop a bullet or reorder the page without touching a line of markup and
//    without breaking the build. `vite build` would be perfectly happy. The only thing that can
//    catch it is comparing every locale against the English reference, field by field.
//    partners-locales/index.js falls back WHOLE-ARRAY precisely because a per-index merge would
//    silently pair the German "For resellers" with the English "For law firms"; this gate is what
//    makes that whole-array choice safe, by proving the arrays are parallel.
//
// 2. LOOKUP KEYS. `id`, `group`, `accent` and `change.cells[].k` are matched in JS and in CSS.
//    Translating one makes a section vanish from the rail, or lose its colour, in exactly one
//    language. Same hard rule as the severity enums in the deck i18n engine and the COLT
//    remediation tag: translate the label, never the key.
//
// 3. NO PRICES. The operator's standing instruction. A price on a public page is a negotiating
//    position given away for free and it goes stale the day a tier changes. Checked in every
//    language, because a translator "helpfully" adding "ab 500 EUR" is exactly how it would get in.
//
// 4. THE LANGUAGE RULES the operator asked for by name: no long dashes, no jargon abbreviation
//    left unexpanded, no sentence over 30 words. Enforced rather than remembered.
//
// 5. NO HTML ENTITIES. React escapes a string that reaches the DOM through data, so "&rsquo;"
//    is printed verbatim. That defect has already shipped to the live site once, from five locale
//    files at the same time, because the English source string was the key.
//
// 6. ACTUALLY TRANSLATED. A locale that is a copy of English passes every structural check
//    perfectly. So each non-English locale must differ from English on most of its long strings.
//    A gate that a copy-paste would pass is not a gate.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DIR = path.join(HERE, "..", "src", "partners-locales");
const CODES = ["en", "de", "it", "fr", "es", "pl"];

let fail = 0;
const bad = (m) => { console.error("  [FAIL] " + m); fail++; };

// pathToFileURL, never a bare path: on Windows an absolute path starts "C:" and Node's ESM loader
// reads that as a URL SCHEME (ERR_UNSUPPORTED_ESM_URL_SCHEME). It works on Linux by accident.
const load = (c) => import(pathToFileURL(path.join(DIR, `${c}.js`)).href);

const L = {};
for (const c of CODES) {
  try { L[c] = await load(c); }
  catch (e) { bad(`${c}.js will not import: ${e.message}`); }
}
if (fail) { console.error(`\n[FAIL] partners gate: ${fail} problem(s)`); process.exit(1); }

const EN = L.en;

// ---- every string in a module, with a path, so a failure names the field ------------------------
function strings(v, at, out = []) {
  if (typeof v === "string") out.push([at, v]);
  else if (Array.isArray(v)) v.forEach((x, i) => strings(x, `${at}[${i}]`, out));
  else if (v && typeof v === "object") for (const [k, x] of Object.entries(v)) strings(x, `${at}.${k}`, out);
  return out;
}
const allOf = (m) => [
  ...strings(m.meta, "meta"), ...strings(m.arts, "arts"), ...strings(m.sections, "sections"),
];

// ---- 1. structure: every locale parallel to English --------------------------------------------
const enIds = EN.sections.map((s) => s.id);
const OPTIONAL = ["scr", "ladder", "change", "vs", "quote", "channel", "note", "steps", "win", "cta"];

for (const c of CODES) {
  if (c === "en") continue;
  const M = L[c];
  const ids = M.sections.map((s) => s.id);
  if (ids.join(",") !== enIds.join(",")) {
    bad(`${c}: section ids differ from English.\n         en: ${enIds.join(",")}\n         ${c}: ${ids.join(",")}`);
    continue; // everything below indexes in parallel; comparing further would be noise
  }
  if (M.arts.length !== EN.arts.length) bad(`${c}: arts has ${M.arts.length} entries, English has ${EN.arts.length}`);
  EN.arts.forEach((a, i) => {
    if (M.arts[i]?.n !== a.n) bad(`${c}: arts[${i}].n is "${M.arts[i]?.n}", must stay "${a.n}" (it is a lookup value)`);
  });

  EN.sections.forEach((s, i) => {
    const o = M.sections[i];
    // lookup keys, never translated
    if (o.group !== s.group) bad(`${c}/${s.id}: group is "${o.group}", must stay "${s.group}"`);
    if (o.accent !== s.accent) bad(`${c}/${s.id}: accent is "${o.accent}", must stay "${s.accent}"`);
    // optional blocks present in one and absent in the other = a page that differs by language
    for (const k of OPTIONAL) {
      if (!!s[k] !== !!o[k]) bad(`${c}/${s.id}: block "${k}" is ${s[k] ? "present" : "absent"} in English and ${o[k] ? "present" : "absent"} here`);
    }
    const sc = s.cols || [], oc = o.cols || [];
    if (sc.length !== oc.length) bad(`${c}/${s.id}: ${oc.length} columns, English has ${sc.length}`);
    else sc.forEach((col, j) => {
      if (col.li.length !== (oc[j].li || []).length) {
        bad(`${c}/${s.id}: column ${j + 1} has ${oc[j].li?.length} bullets, English has ${col.li.length}`);
      }
    });
    if (s.ladder && o.ladder && s.ladder.items.length !== o.ladder.items.length) bad(`${c}/${s.id}: ladder length differs`);
    if (s.steps && o.steps && s.steps.length !== o.steps.length) bad(`${c}/${s.id}: steps length differs`);
    if (s.change && o.change) {
      if (s.change.cells.length !== o.change.cells.length) bad(`${c}/${s.id}: change cells differ`);
      else s.change.cells.forEach((cell, j) => {
        if (o.change.cells[j].k !== cell.k) bad(`${c}/${s.id}: change.cells[${j}].k is "${o.change.cells[j].k}", must stay "${cell.k}"`);
      });
    }
  });
}

// ---- 2. content rules, every locale -------------------------------------------------------------
// A currency amount, a discount, a seat count or a setup fee. Deliberately narrow: "one analyst"
// and "six to ten meetings" are legitimate prose, and a gate that cries wolf gets switched off.
const PRICE = /(?:[€$£]\s?\d|\b\d[\d.,]*\s?(?:EUR|USD|CHF|GBP|PLN)\b|\b\d+\s?%\s?(?:off|discount|rabatt|descuento|sconto|remise|rabat)|\bper (?:seat|user|licence|license)\b|\bpro (?:Platz|Nutzer|Lizenz)\b|\bsetup fee\b)/i;
const ENTITY = /&(?:[a-zA-Z][a-zA-Z0-9]{1,7}|#\d{2,5}|#[xX][0-9a-fA-F]{2,4});/;
const DASH = /[—–]/;

for (const c of CODES) {
  for (const [at, s] of allOf(L[c])) {
    if (PRICE.test(s)) bad(`${c} ${at}: a PRICE reached the page: ${JSON.stringify(s.slice(0, 100))}`);
    if (DASH.test(s)) bad(`${c} ${at}: long dash (use a comma, colon or full stop): ${JSON.stringify(s.slice(0, 90))}`);
    if (ENTITY.test(s)) bad(`${c} ${at}: HTML entity in a data string. React escapes it, so it reaches the screen verbatim: ${JSON.stringify(s.slice(0, 90))}`);
    // ** is inline emphasis parsed by rich(). An odd count leaves a literal ** on the page.
    const stars = (s.match(/\*\*/g) || []).length;
    if (stars % 2) bad(`${c} ${at}: unbalanced ** emphasis markers`);
  }
}

// ---- 3. the English source is the reference, so it carries the writing rules --------------------
// Abbreviations the operator called out by name, plus the ones in the same family. Word-boundary
// matched so "DDoS" and "SPAM" do not trigger — a false positive here trains you to ignore the gate.
const JARGON = /\b(DD|SPA|QBR|SKU|MGA|SIEM|SI|TCO|ASM|CTEM)\b/;
for (const [at, s] of allOf(EN)) {
  const m = s.match(JARGON);
  if (m) bad(`en ${at}: unexpanded abbreviation "${m[1]}". Write it out: ${JSON.stringify(s.slice(0, 90))}`);
  // STRIP THE EMPHASIS MARKERS BEFORE SPLITTING. "…finding.**  An address…" ends its first
  // sentence with `.**`, so a split on "full stop then whitespace" never fires and two ordinary
  // sentences are measured as one 36-word monster. The reader sees two sentences; the gate has to
  // measure what the reader sees, not what the source file happens to look like. Found by the
  // gate's own first run, which is the argument for running it before believing it.
  for (const sent of s.replace(/\*\*/g, "").split(/(?<=[.!?])\s+/)) {
    const w = sent.trim().split(/\s+/).filter(Boolean).length;
    if (w > 30) bad(`en ${at}: a ${w}-word sentence (max 30): ${JSON.stringify(sent.slice(0, 100))}`);
  }
}

// ---- 4. a copy of English is not a translation --------------------------------------------------
// Long strings only: "OEM", "1", a proper noun and a brand name are IDENTICAL in every language
// and always will be, so counting them would make a copied file look partly translated.
const LONG = allOf(EN).filter(([, s]) => s.length >= 60);
for (const c of CODES) {
  if (c === "en") continue;
  const mine = new Map(allOf(L[c]));
  const same = LONG.filter(([at, s]) => mine.get(at) === s);
  const pct = Math.round((same.length / LONG.length) * 100);
  if (pct > 10) {
    bad(`${c}: ${pct}% of the long strings (${same.length}/${LONG.length}) are byte-identical to English. This locale looks copied, not translated.`);
    for (const [at] of same.slice(0, 3)) console.error("           " + at);
  } else {
    console.log(`  ${c}: translated (${same.length}/${LONG.length} long strings match English, ${pct}%)`);
  }
}

// ---- 5. the rail must reach every section, and every section must be reachable -------------------
const GROUPS = new Set(["partners", "buyers", "engage"]);
for (const s of EN.sections) {
  if (!GROUPS.has(s.group)) bad(`en/${s.id}: group "${s.group}" is not one of ${[...GROUPS].join(", ")}, so the section renders in no rail group and is unreachable`);
  if (!s.scr && s.id !== "contact") bad(`en/${s.id}: no Situation/Complication/Answer block. A page without a governing thought is a list of features.`);
}
const dupes = enIds.filter((x, i) => enIds.indexOf(x) !== i);
if (dupes.length) bad(`duplicate section ids: ${dupes.join(", ")} (the anchor links would collide)`);

console.log(`partners gate: ${CODES.length} locales x ${enIds.length} sections, ${allOf(EN).length} English strings`);
if (fail) { console.error(`\n[FAIL] partners gate: ${fail} problem(s)`); process.exit(1); }
console.log("  partners gate OK");
