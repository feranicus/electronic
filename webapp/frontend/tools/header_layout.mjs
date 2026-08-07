#!/usr/bin/env node
/* header_layout.mjs — the header row is ARITHMETIC, not a matter of taste.
 *
 * WHY: adding "Who we are" to the nav pushed the GERMAN row past the viewport and "Zur Anwendung"
 * landed on top of the page heading. CLAUDE.md had already recorded, twice, that a fixed-height
 * horizontal bar must be measured before shipping — brand + every control + gaps, in the LONGEST
 * language. I added a control and did not re-measure. This makes that impossible to skip.
 *
 * Also guards the duplicate language bar: SiteHeader owns the toggle, and no page may render a
 * second one. Two controls for one value is what the operator saw on /contact and /experience.
 */
import { pathToFileURL } from "url";
import { readdirSync, readFileSync } from "fs";

const L = {};
for (const c of ["en", "de", "it", "fr", "es", "pl"])
  L[c] = (await import(pathToFileURL("src/locales/" + c + ".js").href)).keyed;
const t = (c, k) => L[c][k] || L.en[k] || k;

const link = (s) => s.length * 6.6;            // 13.5px nav link
const btn = (s) => s.length * 6.9 + 32;        // 13px button + padding
const BRAND = 158, GAP = 15, LANG = 92;
const DESKTOP_BUDGET = 1136;   // .wrap is max-width:1180px with 22px padding each side
const NARROW_BUDGET = 956;     // 1000px viewport, the point where plain nav links hide
const PHONE_BUDGET = 360;

let bad = 0;
const fail = (m) => { console.log("  [FAIL] " + m); bad++; };

console.log("header row width — desktop (budget " + DESKTOP_BUDGET + "px)");
for (const c of Object.keys(L)) {
  const nav = ["nav.why", "nav.machine", "nav.secure"].map((k) => link(t(c, k)));
  const ctl = [btn(t(c, "nav.demo")), btn(t(c, "nav.more")), LANG, btn(t(c, "nav.open"))];
  const w = Math.round(BRAND + [...nav, ...ctl].reduce((a, b) => a + b, 0) + GAP * (nav.length + ctl.length));
  console.log("  " + c + "  " + String(w).padStart(4) + "px  " + (w <= DESKTOP_BUDGET ? "ok" : "OVERFLOW"));
  if (w > DESKTOP_BUDGET) fail(c + " header row is " + w + "px, over the " + DESKTOP_BUDGET + "px budget");
}

console.log("header row width — 720-1000px (plain links hidden, budget " + NARROW_BUDGET + "px)");
for (const c of Object.keys(L)) {
  const ctl = [btn(t(c, "nav.demo")), btn(t(c, "nav.more")), LANG, btn(t(c, "nav.open"))];
  const w = Math.round(BRAND + ctl.reduce((a, b) => a + b, 0) + GAP * ctl.length);
  if (w > NARROW_BUDGET) fail(c + " narrow header row is " + w + "px");
}
console.log("  all six fit");

console.log("header row width — phone (budget " + PHONE_BUDGET + "px, plain links hidden)");
for (const c of Object.keys(L)) {
  const w = Math.round(130 + (btn(t(c, "nav.demo")) - 8) + 40 + 46 + 8 * 3);
  if (w > PHONE_BUDGET) fail(c + " phone header row is " + w + "px");
}
console.log("  all six fit");

// The menu must reach every page a visitor needs; on a phone it is the ONLY route to them.
const mm = readFileSync("src/components/MoreMenu.jsx", "utf8");
for (const r of ["/experience", "/contact", "/impressum", "/privacy"])
  if (!mm.includes('to: "' + r + '"')) fail("MoreMenu does not link to " + r);
console.log("  menu reaches: /experience /contact /impressum /privacy");

// EXACTLY ONE language control on the site: the header's.
const pages = readdirSync("src/pages").filter((f) => f.endsWith(".jsx"));
for (const f of pages) {
  const s = readFileSync("src/pages/" + f, "utf8");
  // Scoped deliberately: NewAssessment renders a LangToggle INSIDE the Art. 13 privacy notice,
  // which is a different control in a different context and is not a duplicate of anything.
  // The defect is a page showing the SiteHeader's toggle AND its own.
  if (/<SiteHeader\b/.test(s) && /<LangToggle\b/.test(s))
    fail("src/pages/" + f + " renders SiteHeader AND its own LangToggle - two controls, one value");
}
if (!/<LangToggle\b/.test(readFileSync("src/components/SiteHeader.jsx", "utf8")))
  fail("SiteHeader lost the language toggle - the site would have none");
console.log("  language toggle: exactly one, in SiteHeader");

console.log(bad ? "\n[FAIL] header layout: " + bad + " problem(s)" : "\n  header layout OK");
process.exit(bad ? 1 : 0);
