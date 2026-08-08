// tools/contrast_gate.mjs — the blocking accessibility and palette gate for the shipped stylesheet.
//
//   node tools/contrast_gate.mjs
//
// ============================================================================================
// WHY THIS EXISTS
// ============================================================================================
// The site moved from dark to light on 8 Aug 2026. A colour change is the easiest kind of change
// to get subtly wrong, and every failure mode is silent:
//
//   · A text colour that measures 4.1:1 looks fine to the person who chose it on a good monitor
//     indoors, and is unreadable on a phone in daylight. `vite build` has no opinion.
//     THIS ALREADY HAPPENED: the first draft of the palette used #6B7A94 for muted text and
//     #0891B2 for the cyan accent. Measured, they were 4.08:1 and 3.68:1. Both were rejected by
//     this check before they reached the stylesheet.
//   · rgba(255,255,255,x) LIGHTENS a dark surface. On a light surface the element simply
//     disappears: no error, no warning, an invisible border or an invisible progress track.
//   · The conversion rule ("one colour reserved for actions") erodes the moment somebody uses the
//     action colour for a heading, and then the button is no longer the most distinct thing on
//     the screen, which is the entire mechanism the research describes.
//     I BROKE THIS MYSELF within an hour of writing it, on a chat bubble and a progress bar.
//
// So: measure the shipped file, not a design document. Every number here is computed from
// styles.css with the WCAG 2.x relative-luminance formula. Pure Node, no dependencies, so it runs
// identically on the operator's Windows box and inside the frontend image build.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CSS = fs.readFileSync(path.join(HERE, "..", "src", "styles.css"), "utf8");

let fail = 0;
const bad = (m) => { console.error("  [FAIL] " + m); fail++; };

// ---- resolve the palette out of :root -----------------------------------------------------------
const rootBlock = CSS.slice(CSS.indexOf(":root{"), CSS.indexOf("\n}", CSS.indexOf(":root{")));
const V = {};
for (const m of rootBlock.matchAll(/--([\w-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})\s*[;\n]/g)) V[m[1]] = m[2];
const need = ["navy", "navy2", "card", "line", "line2", "ink", "body", "mut", "cta", "cta-d",
              "cta-l", "teal", "purple", "gold", "green", "red", "d-canvas", "d-ink", "d-mut"];
for (const k of need) if (!V[k]) bad(`--${k} is missing from :root`);
if (fail) { console.error("\n[FAIL] contrast gate: palette incomplete"); process.exit(1); }

// ---- WCAG 2.x -----------------------------------------------------------------------------------
const lum = (h) => {
  h = h.replace("#", "");
  if (h.length === 3) h = [...h].map((c) => c + c).join("");
  const v = [0, 2, 4].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// ---- 1. every foreground that is rendered on every surface it can land on ------------------------
// 4.5:1 is the WCAG AA minimum for body text. Large text and component EDGES need only 3:1, and
// those pairs are marked so a heading colour is not rejected for a rule that does not apply to it.
const SURFACES = [["page", V.navy], ["raised", V.navy2], ["panel", V.card]];
const TEXT = [
  ["ink (headings, and all body text on a phone)", V.ink, 4.5],
  ["body (paragraphs)", V.body, 4.5],
  ["mut (captions, labels)", V.mut, 4.5],
  ["teal (accent text, links)", V.teal, 4.5],
  ["purple (second brand)", V.purple, 4.5],
  ["gold (attention text)", V.gold, 4.5],
  ["green (closed, compliant)", V.green, 4.5],
  ["red (critical)", V.red, 4.5],
  ["cta (as an edge or an icon)", V.cta, 3.0],
];
console.log("light surfaces");
for (const [sn, sc] of SURFACES) {
  const line = [];
  for (const [tn, tc, min] of TEXT) {
    const r = ratio(tc, sc);
    if (r < min) bad(`${tn} ${tc} on the ${sn} ${sc} is ${r.toFixed(2)}:1, below ${min}:1`);
    line.push(`${tn.split(" ")[0]} ${r.toFixed(1)}`);
  }
  console.log(`  ${sn.padEnd(7)} ${sc}  ` + line.join(" · "));
}

// ---- 2. text sitting ON a coloured fill ---------------------------------------------------------
for (const [fg, bg, what] of [
  ["#FFFFFF", V.cta, "the primary button label"],
  ["#FFFFFF", V["cta-d"], "the button label on hover"],
  [V.cta, V["cta-l"], "action text on its own wash (menu hover, active nav)"],
  [V.gold, V["gold-l"] || "#FEF6E7", "attention text on its tint"],
  [V.red, V["red-l"] || "#FEECF0", "error text on its tint"],
  [V.green, V["green-l"] || "#E7F7F1", "success text on its tint"],
]) {
  const r = ratio(fg, bg);
  if (r < 4.5) bad(`${what}: ${fg} on ${bg} is ${r.toFixed(2)}:1, below 4.5:1`);
}
console.log(`  button  white on ${V.cta} = ${ratio("#FFFFFF", V.cta).toFixed(2)}:1`);

// ---- 3. the dark blocks that survive on purpose --------------------------------------------------
// The log stream, the architecture map and the login brand panel stay dark. They are machine output,
// a schematic and a first impression: none is long-form reading, which is what the light theme is for.
for (const [fg, name] of [[V["d-ink"], "d-ink"], [V["d-mut"], "d-mut"]]) {
  const r = ratio(fg, V["d-canvas"]);
  if (r < 4.5) bad(`${name} ${fg} on the dark canvas ${V["d-canvas"]} is ${r.toFixed(2)}:1`);
}
console.log(`  dark    ${V["d-canvas"]}  ink ${ratio(V["d-ink"], V["d-canvas"]).toFixed(1)} · mut ${ratio(V["d-mut"], V["d-canvas"]).toFixed(1)}`);

// ---- 4. THE RESERVED COLOUR ----------------------------------------------------------------------
// A solid indigo rectangle must mean "click this". As TEXT or inside a gradient it is fine, because
// it never reads as a clickable block. As a large FILL on something inert it competes with the
// button and the whole mechanism goes away.
const CONTROLS = /(^|[\s,>])(\.btn|\.tour|\.lang-toggle button\.on|button|\.wa-fab)/;
const fills = [];
for (const m of CSS.matchAll(/([^{}]+)\{([^{}]*background\s*:\s*var\(--cta\)[^{}]*)\}/g)) {
  const sel = m[1].split("\n").pop().trim();
  fills.push(sel);
  if (!CONTROLS.test(sel)) {
    bad(`\`background:var(--cta)\` on "${sel}", which is not a control. A solid block of the action `
      + `colour on something inert stops the button being the most distinct thing on screen, which `
      + `is the entire reason the colour is reserved. Use --purple or --cta-l instead.`);
  }
}
// NOT "does anything use it", but "does THE BUTTON use it". The first version asked the weaker
// question and a negative test caught it: blanking `.btn`'s background left `.tour` and the
// language toggle still using --cta, so the count was non-zero and the gate passed a site whose
// primary call to action had turned white on white. A check has to name its subject.
if (!fills.some((sel) => /(^|[\s,])\.btn\b/.test(sel))) {
  bad("`.btn` does not have `background:var(--cta)`. The primary call to action has lost the "
    + "reserved colour, which is the one thing this whole palette is arranged around.");
}
if (!fills.length) bad("nothing uses `background:var(--cta)` at all");
console.log(`  reserved: solid --cta appears on ${fills.length} selector(s), all controls: ${fills.join(", ")}`);

// ---- 5. white overlays on a light theme are invisible ---------------------------------------------
// Allowed only inside the blocks that are still dark. Anything else is an element nobody can see.
// ALPHA IS THE DISCRIMINATOR, and getting that wrong was this check's own first failure: it
// flagged `#hd.s{background:rgba(255,255,255,.92)}`, which is the sticky header's white surface
// and entirely correct on a light theme. A near-opaque white IS a surface. It is the FAINT white
// (a tint meant to lighten something dark beneath it) that becomes invisible when the thing
// beneath it is already white. So: only alpha below 0.5 is suspect.
const DARK_OK = /iam-brand|iam-steps|iam-tag|loglist|mapbox|shine|prog-fill|cass|tgh|d-canvas|wa-fab/;
for (const m of CSS.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
  const sel = m[1].split("\n").pop().trim();
  for (const w of m[2].matchAll(/rgba\(255,\s*255,\s*255,\s*(\.\d+|0?\.\d+|[01])\s*\)/g)) {
    const alpha = parseFloat(w[1]);
    if (alpha >= 0.5) continue;                       // an opaque-ish white surface, deliberate
    if (DARK_OK.test(sel) || DARK_OK.test(m[2])) continue;  // still a dark block
    bad(`faint white overlay rgba(255,255,255,${alpha}) on "${sel}". It was there to lighten a dark `
      + `surface; on a light one the element is invisible. Use var(--line) or an ink-tinted rgba.`);
  }
}

// ---- 6. the old brand must not creep back ---------------------------------------------------------
// The rebrand changed the wordmark and left the colours, which is why the site still read as Colt.
const COLT = /#00[Bb]2[Aa]9|#0[Aa]1526|#0[Cc]544[Ee]|#132546|#22385[Ff]/g;
const strip = CSS.replace(/\/\*[\s\S]*?\*\//g, "");   // the header comment quotes them deliberately
const hits = [...new Set(strip.match(COLT) || [])];
if (hits.length) bad(`the previous (Colt) palette is still in styles.css: ${hits.join(", ")}`);

console.log(`contrast gate: ${Object.keys(V).length} palette entries, ${SURFACES.length * TEXT.length + 6} pairs measured`);
if (fail) { console.error(`\n[FAIL] contrast gate: ${fail} problem(s)`); process.exit(1); }
console.log("  contrast gate OK");
