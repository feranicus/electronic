// tools/i18n_catalogue.mjs — build the COMPLETE translation catalogue and report per-locale gaps.
//
// WHY THIS EXISTS: the site has two key spaces (see src/i18n.jsx) and the by-English one is fed
// partly from JSX literals and partly from data arrays (DD / NODES / STEPS / CONV) whose strings
// reach tx() through a VARIABLE. A regex over the source misses the second kind; an SSR render
// misses the first kind's effect-only callers. The catalogue is the UNION of both, so a string
// cannot hide from the translators the way `gitlab.bibel.tv` once hid from recon.
//
//   node tools/i18n_catalogue.mjs            -> writes tools/catalogue.json, prints coverage
//   node tools/i18n_catalogue.mjs --check    -> ALSO exits non-zero if any locale is incomplete
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(HERE, "..", "src");

const read = (p) => fs.readFileSync(p, "utf8");
const jsx = (dir) => fs.readdirSync(path.join(SRC, dir)).filter((f) => f.endsWith(".jsx"))
  .map((f) => path.join(SRC, dir, f));

// ---- 1. every tx("literal") in the source ------------------------------------------------------
const files = [...jsx("pages"), ...jsx("components"), path.join(SRC, "App.jsx")].filter(fs.existsSync);
const byEn = new Set();
const LIT = /\btx\(\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')\s*\)/g;
for (const f of files) {
  const s = read(f);
  for (const m of s.matchAll(LIT)) byEn.add(JSON.parse(m[1][0] === '"' ? m[1] : `"${m[1].slice(1, -1).replace(/"/g, '\\"')}"`));
}

// ---- 2. the data arrays whose strings reach tx() through a variable -----------------------------
// These are object literals inside Landing.jsx's effect. Pulling the string VALUES out by field name
// is deliberate and narrow: a blanket sweep over the file would also match code identifiers, which
// is exactly the mistake that once corrupted the DD array into a parse error.
const landing = read(path.join(SRC, "pages", "Landing.jsx"));
const FIELD = /\b(?:h|plain):\s*("(?:[^"\\]|\\.)*")/g;
for (const m of landing.matchAll(FIELD)) byEn.add(JSON.parse(m[1]));
const HOOD = /\bhood:\s*\[([\s\S]*?)\]\s*\}/g;
for (const m of landing.matchAll(HOOD)) {
  for (const s of m[1].matchAll(/"(?:[^"\\]|\\.)*"/g)) byEn.add(JSON.parse(s[0]));
}

// ---- 3. the keyed space ------------------------------------------------------------------------
const LOCALES = ["de", "it", "fr", "es", "pl"];
// pathToFileURL, NOT a slash-normalised string. On Windows a bare absolute path starts with `C:`,
// which Node's ESM loader reads as a URL SCHEME and rejects with ERR_UNSUPPORTED_ESM_URL_SCHEME:
// "Received protocol 'c:'". It works on Linux by accident, which is exactly why it shipped broken.
const load = async (code) => import(pathToFileURL(path.join(SRC, "locales", `${code}.js`)).href);
const en = await load("en");
const keys = Object.keys(en.keyed);

const out = {
  keyed: Object.fromEntries(keys.map((k) => [k, en.keyed[k]])),
  byEn: [...byEn].sort(),
};
fs.writeFileSync(path.join(HERE, "catalogue.json"), JSON.stringify(out, null, 1));

// ---- 4. per-locale coverage, and the gap files the translators actually need --------------------
let bad = 0;
console.log(`catalogue: ${keys.length} keyed + ${out.byEn.length} by-English = ${keys.length + out.byEn.length} strings`);
for (const code of LOCALES) {
  const L = await load(code);
  const mk = keys.filter((k) => L.keyed?.[k] === undefined);
  const mb = out.byEn.filter((s) => L.byEn?.[s] === undefined && L.byEn?.[s.trim()] === undefined);
  const pct = Math.round(((keys.length + out.byEn.length - mk.length - mb.length) / (keys.length + out.byEn.length)) * 100);
  console.log(`  ${code}: ${pct}% complete   missing ${mk.length} keyed / ${mb.length} by-English`);
  fs.writeFileSync(path.join(HERE, `gap.${code}.json`), JSON.stringify({
    keyed: Object.fromEntries(mk.map((k) => [k, en.keyed[k]])), byEn: mb,
  }, null, 1));
  if (mk.length || mb.length) bad++;
  // An orphan is a translation nobody renders — dead weight that hides a real gap behind a good %.
  const orphan = Object.keys(L.byEn || {}).filter((s) => !byEn.has(s) && !byEn.has(s + " ") && !byEn.has(" " + s));
  if (orphan.length) console.log(`      (${orphan.length} orphan by-English entries no longer rendered)`);
}
if (process.argv.includes("--check") && bad) {
  console.error(`\n[FAIL] ${bad} locale(s) incomplete — see tools/gap.*.json`);
  process.exit(1);
}
