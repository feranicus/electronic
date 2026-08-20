/**
 * brand.js — White Label at the render boundary.
 *
 * ONE require() and ONE call per builder. The builders keep their own palette object, their own
 * key names and their own layout arithmetic; this hands them either those exact defaults (no
 * theme: the output is byte-identical to before White Label existed) or the partner's equivalents.
 *
 * This is deliberately the same doctrine as scripts/i18n/deck_i18n.js, which was written after a
 * failed attempt to hoist ~530 literals out of the builders: DO NOT FORK THE BUILDERS, and do not
 * move their constants somewhere else. Translate — here, re-colour — at the boundary where the
 * value is consumed, and let anything unrecognised fall through unchanged.
 *
 * THE MAPPING IS BY VALUE, NOT BY KEY, and that is the trick that makes it small.
 * Our three brand stops are 00D7BD / 00A49A / 0C544E. Any default whose VALUE is one of those is a
 * brand surface wherever it appears, whatever the builder happens to call it — so `teal`,
 * `tealDark`, `evBg: "0C544E"` and any key a future builder adds are themed for free, while
 * crit/high/med/low, ink, divider, white and black are left alone because their values are not in
 * the ramp. Severity colours are semantic enums: a partner whose brand is red does not get green
 * criticals, and that property holds here by construction rather than by a list somebody maintains.
 *
 * FONTS: heading and body follow the partner's theme. The MONOSPACE face does not (evidence is
 * host:port and must stay aligned) and neither does the display face used for the poster headlines
 * — those boxes have hardcoded widths and hand-tuned sizes, and swapping the face changes the
 * metrics. That is the same class of defect as the German overflow work: a font change is a layout
 * change. Colour, logo and wordmark carry the recognition; the display face is not worth the risk.
 */
const fs = require("fs");
const path = require("path");

// The stops the builders ship with. Mirrors proteus.REF; asserted equal by the test suite so the
// two cannot drift into a state where a theme maps onto colours nothing uses.
const REF = { light: "00D7BD", mid: "00A49A", dark: "0C544E" };

const NORM = (s) => String(s || "").trim().replace(/^#/, "").toUpperCase();

let THEME = null;
let LOADED = false;
let PROBLEM = "";

function theme() {
  if (LOADED) return THEME;
  LOADED = true;
  const p = process.env.BRAND_THEME;
  if (!p) return null;
  try {
    const t = JSON.parse(fs.readFileSync(p, "utf8"));
    const pal = (t && t.palette) || {};
    // FAIL SAFE, NOT FAIL PRETTY. A theme we cannot read, or one whose ramp is inverted, would
    // produce a deck with dark text on dark fills on every slide. Falling back to our own palette
    // gives the partner an un-branded but READABLE artifact, and says so on stderr.
    for (const k of ["brandLight", "brandMid", "brandDark"]) {
      if (!/^[0-9A-F]{6}$/.test(NORM(pal[k]))) throw new Error("palette." + k + " is not a colour");
    }
    THEME = t;
    THEME.dir = path.dirname(p);
  } catch (e) {
    PROBLEM = String((e && e.message) || e);
    console.error("[brand] ignoring BRAND_THEME (" + PROBLEM + ") — rendering unbranded");
    THEME = null;
  }
  return THEME;
}

const active = () => !!theme();

/**
 * Re-colour ANY structure by VALUE: a flat palette, a map of arrays, a nested object.
 *
 * WHY IT RECURSES. `palette()` used to walk one flat object, so it only ever saw the colours that
 * went THROUGH it — and build_findings_deck.js has a SECOND colour table, `tagMap`, holding
 * `COLT: ["00D7BD", "121212"]` and `PSF: ["0C544E", "FFFFFF"]` as literals. Those bypassed the
 * mapping entirely, and a partner's deck shipped with 11 of our teal chips and 11 of our dark
 * ones still on it. Mapping by value is right; mapping by value in only one place is not.
 * The render gate missed it because its fixture produced no COLT or PSF tag — a gate is only as
 * good as the shapes its fixture contains.
 */
function recolor(x) {
  const t = theme();
  if (!t) return x;
  const p = t.palette;
  const map = {
    [REF.light]: NORM(p.brandLight),
    [REF.mid]: NORM(p.brandMid),
    [REF.dark]: NORM(p.brandDark),
  };
  const walk = (v) => {
    if (typeof v === "string") return map[NORM(v)] || v;
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === "object") {
      const o = {};
      for (const [k, val] of Object.entries(v)) o[k] = walk(val);
      return o;
    }
    return v;
  };
  return walk(x);
}

/** The builder's own palette, re-coloured by VALUE. Unrecognised entries pass through untouched. */
const palette = (defaults) => recolor(defaults);

/** heading/body follow the partner; mono and display deliberately do not (see the header). */
function fonts(defaults) {
  const t = theme();
  if (!t) return defaults;
  const f = t.fonts || {};
  return Object.assign({}, defaults, {
    FH: f.heading || defaults.FH,
    FB: f.body || defaults.FB,
  });
}

const wordmark = () => {
  const t = theme();
  return (t && String(t.wordmark || "").trim()) || "cybergod.ai";
};

/** Absolute path to a validated logo file, or null. Never a path from the theme JSON directly. */
function logo() {
  const t = theme();
  if (!t || !t.logo) return null;
  // The theme names a BASENAME and the file must sit beside the theme. A theme that tries to point
  // at /etc/anything is a traversal attempt, not a logo.
  const base = path.basename(String(t.logo));
  if (base !== String(t.logo)) return null;
  const full = path.join(t.dir, base);
  try {
    return fs.statSync(full).isFile() ? full : null;
  } catch (e) {
    return null;
  }
}

/**
 * Draw the mark in the box the builder reserved for the wordmark.
 *
 * ONE call replaces five near-identical addText() blocks, so the logo can never appear on four
 * decks and be forgotten on the fifth. The image is fitted INSIDE the box and right-aligned, using
 * the pixel dimensions recorded at upload — a logo stretched to the box's aspect ratio is the most
 * obvious possible sign that a template was applied by a machine.
 */
function mark(slide, opts) {
  const o = opts || {};
  const box = { x: o.x, y: o.y, w: o.w, h: o.h };
  const t = theme();
  const file = logo();
  if (file && t) {
    const lw = Number(t.logo_w) || 0;
    const lh = Number(t.logo_h) || 0;
    let w = box.w;
    let h = box.h;
    if (lw > 0 && lh > 0) {
      const scale = Math.min(box.w / lw, box.h / lh);
      w = lw * scale;
      h = lh * scale;
    }
    slide.addImage({
      path: file,
      x: box.x + (box.w - w),                 // right-aligned, like the wordmark it replaces
      y: box.y + (box.h - h) / 2,             // vertically centred in the reserved box
      w: w,
      h: h,
    });
    return;
  }
  slide.addText(wordmark(), {
    x: box.x, y: box.y, w: box.w, h: box.h,
    fontSize: o.fontSize || 13, fontFace: o.fontFace || "Arial",
    color: o.color || "FFFFFF", bold: true, align: "right", margin: 0,
  });
}

/**
 * The attribution line. Present by default and deliberately small: the partner's customer sees
 * their brand, and the engine is still named. Removing it entirely is a commercial decision that
 * belongs in the OEM agreement, not a default in a builder.
 */
const poweredBy = () => {
  const t = theme();
  if (!t) return "";
  const s = String(t.powered_by === undefined ? "Powered by cybergod.ai" : t.powered_by).trim();
  return s;
};

const name = () => {
  const t = theme();
  return (t && String(t.name || "").trim()) || "";
};

module.exports = { REF, active, palette, recolor, fonts, wordmark, logo, mark, poweredBy, name, theme };
