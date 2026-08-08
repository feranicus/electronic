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
// `topbar` joined this list when the phone header became the brand gradient: a white overlay on
// a saturated surface is correct, it is only on a LIGHT surface that it vanishes. The list is
// the set of surfaces that are still dark or saturated, and it has to be kept honest by hand.
// The allowlist is "selectors that render on a DARK OR SATURATED surface". `topbar` and the
// `#hd`-scoped controls joined it when the phone chrome became the brand gradient: a translucent
// white pill on a gradient is correct, it is only on a LIGHT surface that it vanishes.
// LIMIT WORTH KNOWING: this gate reads selectors, not media context, so it cannot tell that these
// `#hd` rules exist only inside @media(max-width:720px) where #hd IS a gradient. The exemptions are
// therefore narrow and named rather than a blanket "#hd" — a broad exemption here would let a real
// invisible overlay through on the desktop header.
const DARK_OK = /iam-brand|iam-steps|iam-tag|loglist|mapbox|shine|prog-fill|cass|tgh|d-canvas|wa-fab|topbar|#hd \.btn\.ghost|#hd \.lang-trigger|#hd \.more-t|\.phone|\.more-bd/;
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

// ---- 5b. A SURFACE THAT IS STILL DARK -------------------------------------------------------
// THE CHECK THAT SHOULD HAVE EXISTED FIRST. Converting the site to light was not one edit, it was
// dozens, and twice I converted the page and left a bar that FRAMES it:
//   · `.topbar` and the two bottom navigation bars, photographed on a phone;
//   · then `#hd`, which has a desktop rule AND a phone override, and I changed only the first.
// Both times everything else was green, because nothing was asking the obvious question: is any
// surface still dark? So ask it. Any literal dark background outside the deliberately-dark set is
// a failure, and the message names the selector so the fix is one line.
//
// Colours reached through var(--d-canvas) are NOT matched here: using the dark token is the
// documented way to say "this block is meant to be dark", and those selectors are in DARK_OK.
{
  const lumOf = (c) => {
    let m = c.match(/#([0-9A-Fa-f]{3,6})\b/);
    if (m) return lum("#" + m[1]);
    m = c.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?/);
    if (!m) return null;
    // ALPHA IS THE DISCRIMINATOR, for the second time today. A dark colour at low alpha is a TINT
    // over whatever sits beneath it, not a dark surface: .creed's indigo wash is rgba(79,70,229,.07)
    // on a light page. The white-overlay check learned this an hour earlier and I did not carry it
    // across to this one. Anything under half opacity is a wash and is not judged as a surface.
    if (m[4] !== undefined && parseFloat(m[4]) < 0.5) return null;
    const [r, g, b] = m.slice(1, 4).map(Number);
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  for (const m of CSS.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const sel = m[1].split("\n").pop().trim();
    if (DARK_OK.test(sel) || sel.startsWith(":root") || sel.startsWith("@")) continue;
    for (const d of m[2].matchAll(/background(?:-color)?\s*:\s*([^;}]+)/g)) {
      const val = d[1];
      if (val.includes("var(--d-")) continue;              // the dark token, deliberate
      for (const part of val.split(/,(?![^()]*\))/)) {
        const L = lumOf(part);
        if (L !== null && L < 0.16) {
          bad(`"${sel}" still has a DARK background (${part.trim().slice(0, 34)}). The site is `
            + `light; a dark surface here frames the page in the old palette. If it is meant to `
            + `be dark, use var(--d-canvas)/var(--d-surface) and add the selector to DARK_OK.`);
        }
      }
    }
  }
}

// ---- 6. the old brand must not creep back ---------------------------------------------------------
// The rebrand changed the wordmark and left the colours, which is why the site still read as Colt.
const COLT = /#00[Bb]2[Aa]9|#0[Aa]1526|#0[Cc]544[Ee]|#132546|#22385[Ff]/g;
const strip = CSS.replace(/\/\*[\s\S]*?\*\//g, "");   // the header comment quotes them deliberately
const hits = [...new Set(strip.match(COLT) || [])];
if (hits.length) bad(`the previous (Colt) palette is still in styles.css: ${hits.join(", ")}`);

// ---- 7. THE APP'S OWN CHROME -----------------------------------------------------------------
// The defect this exists for, photographed on a phone: the SITE went light and the INSTALLED APP
// did not. `manifest.webmanifest`'s theme_color still held the previous brand's dark teal, which is
// the colour Android paints the status bar, and `background_color` was the dark splash screen. The
// icons were the same story. None of that is in styles.css, so nothing I had written could see it.
//
// theme-color ALSO lives in index.html, which is a value with two homes: the classic way for the
// two to drift apart. Assert they agree, and that both match the palette.
{
  const mf = JSON.parse(fs.readFileSync(path.join(HERE, "..", "public", "manifest.webmanifest"), "utf8"));
  const html = fs.readFileSync(path.join(HERE, "..", "index.html"), "utf8");
  const meta = (html.match(/<meta\s+name="theme-color"\s+content="(#[0-9A-Fa-f]{3,8})"/) || [])[1];

  if (!meta) bad("index.html has no theme-color meta: the browser paints its chrome grey");
  else if (meta.toUpperCase() !== String(mf.theme_color).toUpperCase()) {
    bad(`theme-color disagrees between its two homes: index.html says ${meta}, `
      + `manifest.webmanifest says ${mf.theme_color}. One value, two files, guaranteed to drift.`);
  }
  if (String(mf.theme_color).toUpperCase() !== V.cta.toUpperCase()) {
    bad(`manifest theme_color is ${mf.theme_color}, not the brand ${V.cta}. That is the colour `
      + `Android paints the status bar of the installed app.`);
  }
  if (String(mf.background_color).toUpperCase() !== V.navy.toUpperCase()) {
    bad(`manifest background_color is ${mf.background_color}, not the page canvas ${V.navy}. `
      + `That is the PWA splash screen, so it flashes the wrong colour on every cold start.`);
  }
  // iOS forces WHITE status text under black-translucent, which is invisible on a light bar.
  if (/apple-mobile-web-app-status-bar-style"\s+content="black-translucent"/.test(html)) {
    bad("apple-mobile-web-app-status-bar-style is black-translucent, which forces white status "
      + "text over what is now a light surface. Use \"default\".");
  }
  for (const f of ["icon.svg", "icon-maskable.svg"]) {
    const svg = fs.readFileSync(path.join(HERE, "..", "public", f), "utf8");
    const h = [...new Set(svg.match(COLT) || [])];
    if (h.length) bad(`${f} still uses the previous brand (${h.join(", ")}). That is the tile on `
                    + `the home screen. Regenerate: python tools/make_icons.py`);
  }
  console.log(`  app chrome: status bar ${mf.theme_color}, splash ${mf.background_color}, icons on brand`);
}

console.log(`contrast gate: ${Object.keys(V).length} palette entries, ${SURFACES.length * TEXT.length + 6} pairs measured`);
if (fail) { console.error(`\n[FAIL] contrast gate: ${fail} problem(s)`); process.exit(1); }
console.log("  contrast gate OK");
