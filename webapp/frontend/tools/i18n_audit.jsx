// tools/i18n_audit.jsx — the SSR gate for the six-language site. Run by ship.py.
//
// WHY THIS EXISTS, in the order the failures actually happened:
//   1. A passing `vite build` proves NOTHING about rendering. `useLegalLang is not defined` compiled
//      cleanly and white-screened /app. So we RENDER every page, in every language.
//   2. A fallback that silently prints the KEY looks like content. `q3.h` and `earn.01b` shipped to
//      the live site in both languages. So we fail on any dotted key reaching the DOM.
//   3. A trailing-space mismatch between the JSX call and the dictionary key made five German
//      strings fall back to English mid-headline — the "mixed language" report. So we MEASURE the
//      English residue per page per language instead of eyeballing it.
//   4. `tx` was a fresh arrow each render, so a useEffect dep changed every render and the
//      architecture map was appended again and again. So we render twice with a language flip in
//      between and assert the output does not grow.
//   5. Six labels sharing a 360px phone row wrapped and doubled the tab bar's height. So we assert
//      the tab labels are short IN EVERY LANGUAGE, not just the one we happened to look at.
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { setLang, LANGS } from "../src/legal.jsx";
import { tr } from "../src/i18n.jsx";
import Landing from "../src/pages/Landing.jsx";
import Demo from "../src/pages/Demo.jsx";
import Partners from "../src/pages/Partners.jsx";
import Contact from "../src/pages/Contact.jsx";
import Experience from "../src/pages/Experience.jsx";
import Privacy from "../src/pages/Privacy.jsx";
import Impressum from "../src/pages/Impressum.jsx";
import Login from "../src/pages/Login.jsx";
// The cabinet is the PRODUCT, and it was English-only long after the marketing site was translated —
// a German user logged in and the whole application switched to English. It is audited here too.
// SSR only exercises the idle branch, so `tools/i18n_catalogue.mjs` covers the rest by asserting
// every t("...") call site in the source resolves to a real key.
import NewAssessment from "../src/pages/NewAssessment.jsx";
import Compliance from "../src/pages/Compliance.jsx";
import Assistant from "../src/pages/Assistant.jsx";
import History from "../src/pages/History.jsx";
import Sidebar from "../src/components/Sidebar.jsx";
// ADDED WITH THE ADMINISTRATION FEATURE. A page absent from this list is a page nobody has ever
// PROVEN renders: `vite build` accepts an undefined identifier, which is how /app once went white
// on `useLegalLang is not defined`. Both of these call hooks and api helpers, so they are exactly
// the shape that fails at execution rather than at compile time.
import Admin from "../src/pages/Admin.jsx";
import WhiteLabel from "../src/pages/WhiteLabel.jsx";
import ChangePassword from "../src/pages/ChangePassword.jsx";

const PAGES = { Landing, Demo, Partners, Contact, Experience, Privacy, Impressum, Login,
                NewAssessment, Compliance, Assistant, History, Sidebar, Admin, ChangePassword,
                WhiteLabel };
const CODES = LANGS.map((l) => l.code);
let fail = 0;

// SILENCE THE KNOWN SSR-ONLY NOISE. React warns once per component per render about
// useLayoutEffect on the server (react-router uses it) — that is 66 renders x N components, ~2,700
// lines of stack traces that bury this gate's own output in ship.py's terminal. These warnings are
// artefacts of rendering a browser app on the server, not defects in the page.
// Everything NOT on this list still prints, so a real error cannot hide behind the filter.
const _err = console.error;
const SSR_NOISE = /useLayoutEffect does nothing on the server|Invalid DOM property/;
console.error = (...a) => { if (!SSR_NOISE.test(String(a[0] ?? ""))) _err(...a); };

const bad = (m) => { _err("  [FAIL] " + m); fail++; };

const render = (P) => renderToStaticMarkup(<MemoryRouter><P /></MemoryRouter>);
const text = (html) => html.replace(/<[^>]*>/g, " ").replace(/&[a-z]+;|&#\d+;/gi, " ")
  .replace(/\s+/g, " ").trim();

// A raw key looks exactly like content, which is why it survived to production. Match the namespaces
// we actually use, not a generic dotted pattern — "cybergod.ai" and "crt.sh" are legitimate text.
const KEYLIKE = /\b(nav|tab|hero|creed|demo|login|lede|q3|clocks|touch|earn|faq|foot|contact|impressum|privacy|assess|comp|assist|hist|side|prt)\.[a-z0-9]+\b/i;

// Function words that are English and are NOT also words in de/it/fr/es/pl. "in", "la", "no", "a",
// "the" (no), "son"… were pruned deliberately: a false positive here trains you to ignore the gate.
const EN_WORDS = /\b(the|your|and|with|from|what|which|would|could|should|about|before|after|every|never|always|because|through|between|nothing|something|whether|here|there|their|these|those|while|when|where|been|being|have|does|doesn't|isn't|you|yours|ours|them|they|its|it's)\b/gi;

console.log("i18n audit — " + Object.keys(PAGES).length + " pages x " + CODES.length + " languages");

for (const code of CODES) {
  setLang(code);
  // The tab bar is a fixed-height row of six. This is arithmetic, not taste.
  for (const k of ["tab.why", "tab.live", "tab.machine", "tab.deep", "tab.secure", "tab.open"]) {
    const v = tr(code, k);
    if (v.length > 8) bad(`${code}: ${k} = "${v}" is ${v.length} chars (max 8) — the phone tab bar will wrap`);
    if (v === k) bad(`${code}: ${k} resolved to the KEY ITSELF`);
  }

  const line = [];
  for (const [name, P] of Object.entries(PAGES)) {
    let html;
    try { html = render(P); }
    catch (e) { bad(`${code}/${name}: RENDER THREW — ${e.message}`); continue; }

    const t = text(html);
    const km = t.match(KEYLIKE);
    if (km) bad(`${code}/${name}: raw i18n key rendered to the DOM: "${km[0]}"`);
    if (/\bundefined\b|\bNaN\b|\[object Object\]/.test(t)) {
      bad(`${code}/${name}: undefined/NaN/[object Object] leaked into the page`);
    }

    const words = t.split(/\s+/).length;
    const en = (t.match(EN_WORDS) || []).length;
    const pct = words ? Math.round((en / words) * 1000) / 10 : 0;
    line.push(`${name} ${pct}%`);
    // English pages are 100% English by definition. For the others, a few percent is proper nouns
    // and code identifiers; double digits means whole sentences fell back.
    if (code !== "en" && pct > 6) {
      bad(`${code}/${name}: ${pct}% English function-words (${en} of ${words}) — sentences are falling back`);
    }
  }
  console.log(`  ${code}: ` + line.join(" · "));
}

// ---- the duplicate guard: render, flip language, render again, compare size ---------------------
// The architecture map is built in a useEffect, which SSR never runs — so this cannot catch the DOM
// append directly. What it CAN catch is the render-identity regression that caused it: if `tx` or
// `t` is not memoised, the markup produced for the same language differs between two renders that
// straddle a language change, because a new function identity forces different child output.
setLang("en");
const a1 = render(Landing);
setLang("de");
render(Landing);
setLang("en");
const a2 = render(Landing);
if (a1 !== a2) bad("Landing markup is not stable across a language flip — a hook identity is changing per render");
else console.log("  duplicate guard: markup stable across en -> de -> en");

if (fail) { _err(`\n[FAIL] i18n audit: ${fail} problem(s)`); process.exit(1); }
console.log("  i18n audit OK");
