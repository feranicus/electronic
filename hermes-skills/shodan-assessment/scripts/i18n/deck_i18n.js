/**
 * deck_i18n.js — one shared localisation layer for all four deck builders.
 *
 * DESIGN: we do NOT hoist ~600 string literals out of the builders. Instead we intercept the
 * pptxgenjs boundary (addText / addTable / addNotes) and translate every string on its way to the
 * slide. A builder opts in with ONE line:
 *
 *     require("./i18n/deck_i18n").install(pptx);
 *
 * Unknown strings pass through untouched (so a missing translation degrades to English, never to a
 * crash or an empty slide). Run with DECK_I18N_AUDIT=1 to dump every untranslated string — that is
 * also how the dictionary is harvested in the first place.
 *
 * LANGUAGE:  DECK_LANG=de|en   (default en; anything starting "de" -> German)
 *
 * GERMAN IS ~30% LONGER than English and every text box in the builders has a hardcoded w/h at a
 * fixed fontSize. So we also shrink text to fit: an explicit, deterministic fontSize is computed
 * here (works in every renderer) and fit:"shrink" is added as a belt-and-braces hint for PowerPoint.
 */
"use strict";
const fs = require("fs");
const path = require("path");

const LANG = /^de/i.test(process.env.DECK_LANG || "en") ? "de" : "en";
const AUDIT = !!process.env.DECK_I18N_AUDIT;

function _load(f) {
  try { return JSON.parse(fs.readFileSync(path.join(__dirname, f), "utf8")); }
  catch (e) { if (LANG !== "en") console.error("[i18n] could not load " + f + ": " + e.message); return {}; }
}
const PACK = LANG === "de" ? _load("de.json") : {};
const STRINGS = PACK.strings || {};
// UPPERCASE index: builders frequently render `foo.toUpperCase()`, so "unique IPs" must also
// resolve for the rendered key "UNIQUE IPS" without duplicating every entry in the dictionary.
const UPPER = {};
for (const k in STRINGS) UPPER[k.toUpperCase()] = STRINGS[k];
const PATTERNS = (PACK.patterns || []).map(p => [new RegExp(p[0]), p[1]]);
const SIZES = PACK.sizes || {};          // explicit fontSize overrides for display headlines
const MISSES = new Map();

/* ---------------------------------------------------------------- text lookup */
function T(s) {
  if (typeof s !== "string" || !s.trim()) return s;
  // preserve surrounding whitespace (builders concatenate e.g. "FINDING " + id)
  const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/);
  const lead = m[1], core = m[2], tail = m[3];
  if (LANG === "en") return s;

  const hit = STRINGS[core];
  if (hit !== undefined) return lead + hit + tail;

  if (core === core.toUpperCase()) {                  // rendered via .toUpperCase()
    const u = UPPER[core];
    if (u !== undefined) return lead + u.toUpperCase() + tail;
  }

  for (const [re, rep] of PATTERNS) {
    if (re.test(core)) return lead + core.replace(re, rep) + tail;
  }
  if (AUDIT && /[A-Za-z]{3}/.test(core)) MISSES.set(core, (MISSES.get(core) || 0) + 1);
  return s;                                   // graceful: English rather than nothing
}

/* ------------------------------------------------- deterministic shrink-to-fit
   Rough Arial/Arial-Black advance widths (fraction of em). Good enough to decide a
   font size; we never need pixel accuracy, only "does it overflow the box". */
const NARROW = new Set("iljI.,:;'`|!()[]{}/\\-".split(""));
const WIDE = new Set("MWmw@%".split(""));
function _emWidth(str, bold) {
  let w = 0;
  for (const ch of str) {
    if (NARROW.has(ch)) w += 0.30;
    else if (WIDE.has(ch)) w += 0.92;
    else if (ch === " ") w += 0.28;
    else if (ch >= "A" && ch <= "Z") w += 0.70;
    else if (ch >= "0" && ch <= "9") w += 0.56;
    else w += 0.53;
  }
  return w * (bold ? 1.06 : 1.0);
}

/** Largest fontSize (pt) at which `text` still fits a box of w x h inches. */
function fitSize(text, w, h, fontSize, bold, charSpacing) {
  if (!w || !fontSize || typeof text !== "string" || !text.trim()) return fontSize;
  const usableW = Math.max(0.2, (w - 0.16)) * 72;                 // inches -> pt, minus inset
  const usableH = h ? h * 72 : Infinity;
  const words = text.split(/\s+/);
  for (let fs_ = fontSize; fs_ >= 6; fs_ -= 0.5) {
    const sp = (charSpacing || 0);
    // greedy wrap at this size
    let lines = 1, cur = 0;
    let fits = true;
    for (const word of words) {
      const wWidth = _emWidth(word, bold) * fs_ + sp * word.length;
      if (wWidth > usableW) { fits = false; break; }              // single word too wide
      const spaceW = cur === 0 ? 0 : _emWidth(" ", bold) * fs_ + sp;
      if (cur + spaceW + wWidth <= usableW) cur += spaceW + wWidth;
      else { lines++; cur = wWidth; }
    }
    if (!fits) continue;
    if (lines * fs_ * 1.15 <= usableH) return fs_;
  }
  return 6;
}

/* ----------------------------------------------------------- option localising */
function _plain(text) {
  if (typeof text === "string") return text;
  if (Array.isArray(text)) return text.map(t => (t && typeof t === "object" ? (t.text || "") : String(t || ""))).join("");
  if (text && typeof text === "object") return String(text.text || "");
  return "";
}

function _localizeOpts(text, opts) {
  if (LANG === "en" || !opts || typeof opts !== "object") return opts;
  const o = Object.assign({}, opts);
  const plain = _plain(text);

  // 1) explicit per-string size override from the dictionary (display headlines)
  if (SIZES[plain] !== undefined) o.fontSize = SIZES[plain];
  // 2) otherwise shrink deterministically if it would overflow its box
  else if (o.fontSize && o.w) {
    const bold = !!o.bold || /Black|Heavy/i.test(o.fontFace || "");
    const want = fitSize(plain, o.w, o.h, o.fontSize, bold, o.charSpacing);
    if (want < o.fontSize) o.fontSize = want;
  }
  // 3) belt & braces for PowerPoint itself
  if (o.w && o.h && o.fit === undefined) o.fit = "shrink";
  return o;
}

function _localizeText(text) {
  if (typeof text === "string") return T(text);
  if (Array.isArray(text)) {
    return text.map(t => {
      if (typeof t === "string") return T(t);
      if (t && typeof t === "object") {
        const c = Object.assign({}, t);
        if (typeof c.text === "string") c.text = T(c.text);
        if (c.options) c.options = _localizeOpts(c.text, c.options);
        return c;
      }
      return t;
    });
  }
  if (text && typeof text === "object" && typeof text.text === "string") {
    const c = Object.assign({}, text); c.text = T(c.text); return c;
  }
  return text;
}

function _localizeRows(rows) {
  if (!Array.isArray(rows)) return rows;
  return rows.map(row => Array.isArray(row) ? row.map(cell => {
    if (typeof cell === "string") return T(cell);
    if (cell && typeof cell === "object") {
      const c = Object.assign({}, cell);
      if (typeof c.text === "string") c.text = T(c.text);
      else if (Array.isArray(c.text)) c.text = _localizeText(c.text);
      return c;
    }
    return cell;
  }) : row);
}

/* --------------------------------------------------------------------- install */
function install(pptx) {
  if (!pptx || typeof pptx.addSlide !== "function") return pptx;
  const origAddSlide = pptx.addSlide.bind(pptx);
  pptx.addSlide = function (...a) {
    const slide = origAddSlide(...a);
    if (slide && !slide.__i18n) {
      slide.__i18n = true;
      const at = slide.addText && slide.addText.bind(slide);
      if (at) slide.addText = (text, opts) => at(_localizeText(text), _localizeOpts(text, opts));
      const tb = slide.addTable && slide.addTable.bind(slide);
      if (tb) slide.addTable = (rows, opts) => tb(_localizeRows(rows), opts);
      const nt = slide.addNotes && slide.addNotes.bind(slide);
      if (nt) slide.addNotes = (n) => nt(T(n));
    }
    return slide;
  };
  return pptx;
}

/* ------------------------------------------------------- locale-aware helpers
   (builders call these directly — a wrapper cannot fix numbers already baked
   into a string by the time it reaches addText) */
const LOCALE = LANG === "de" ? "de-DE" : "en-US";
function nfmt(n, dec) {
  const v = Number(n || 0);
  return v.toLocaleString(LOCALE, dec !== undefined ? { minimumFractionDigits: dec, maximumFractionDigits: dec } : undefined);
}
/** Compact money: 1.2M -> "1,2 Mio." (de) / "1.2M" (en). `sym` is prefixed if given. */
function money(v, sym) {
  const n = Number(v || 0), a = Math.abs(n), s = sym || "";
  const U = PACK.units || {};
  const bn = U.bn !== undefined ? U.bn : (LANG === "de" ? " Mrd." : "bn");
  const mm = U.M !== undefined ? U.M : (LANG === "de" ? " Mio." : "M");
  const k = U.k !== undefined ? U.k : (LANG === "de" ? " Tsd." : "k");
  const f = (x, d) => nfmt(x, d);
  if (a >= 1e9) return s + f(n / 1e9, 1) + bn;
  if (a >= 1e6) return s + f(n / 1e6, 1) + mm;
  if (a >= 1e3) return s + f(n / 1e3, 0) + k;
  return s + f(Math.round(n), 0);
}
function dfmt(d) {
  const dt = d ? new Date(d) : new Date();
  if (LANG === "de") {
    const p = n => String(n).padStart(2, "0");
    return p(dt.getDate()) + "." + p(dt.getMonth() + 1) + "." + dt.getFullYear();
  }
  return dt.toISOString().slice(0, 10);
}

/* ---------------------------------------------------------------------- audit */
if (AUDIT) {
  process.on("exit", () => {
    if (!MISSES.size) { console.error("[i18n] audit: no untranslated strings"); return; }
    const out = process.env.DECK_I18N_AUDIT_OUT;
    const list = [...MISSES.entries()].sort((a, b) => b[1] - a[1]).map(([s, n]) => ({ n, s }));
    if (out) {
      let prev = [];
      try { prev = JSON.parse(fs.readFileSync(out, "utf8")); } catch (e) { }
      const seen = new Set(prev.map(x => x.s));
      fs.writeFileSync(out, JSON.stringify(prev.concat(list.filter(x => !seen.has(x.s))), null, 2));
    }
    console.error("[i18n] audit: " + MISSES.size + " untranslated string(s)" + (out ? " -> " + out : ""));
  });
}

module.exports = { install, T, LANG, LOCALE, nfmt, money, dfmt, fitSize, _emWidth };
