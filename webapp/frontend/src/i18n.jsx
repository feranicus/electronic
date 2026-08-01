// i18n.jsx — ONE dictionary layer for every UI string outside the legal pages.
//
// WHY IT SHARES legal.jsx's HOOK AND STORAGE KEY:
// `useLegalLang()` already exists, already defaults from the browser and already remembers the
// reader's choice in localStorage under `cg_legal_lang`. A second language store would let the site
// and the privacy page disagree — one toggle showing Italian while the other shows English is
// exactly the drift legal.jsx was created to prevent. ONE hook, ONE key, ONE toggle, whole site.
//
// ------------------------------------------------------------------------------------------------
// TWO KEY SPACES. Mixing them is what once printed `q3.h` on the live page, in BOTH languages.
//   * KEYED       — dotted keys ("nav.why"), read with `t("nav.why")`.   Source: locales/en.js
//   * BY-ENGLISH  — the English sentence IS the key, read with `tx("Fair questions")`.
//                   Source: each locale's `byEn`. English needs no entry: it IS the fallback.
// A gettext-style by-English space exists because Landing.jsx holds ~145 long sentences inside JS
// data arrays; inventing a dotted key per sentence would be 145 chances to mistype one and ship a
// blank. Using the English text as the key means a missing translation degrades to the original.
// Every NEW string must state which space it belongs to. A raw key reaching the DOM fails the build.
// ------------------------------------------------------------------------------------------------
//
// FALLBACK IS NEVER A CRASH: locale -> English -> the key itself. Same doctrine as the deck i18n
// engine — an incomplete translation degrades to readable English, never to a blank or an exception.
// That is what makes it safe to add a language before its dictionary is complete.
import { useCallback } from "react";
import { useLegalLang, LANGS } from "./legal";

import { keyed as EN } from "./locales/en.js";
import * as DE from "./locales/de.js";
import * as IT from "./locales/it.js";
import * as FR from "./locales/fr.js";
import * as ES from "./locales/es.js";
import * as PL from "./locales/pl.js";

export const useLang = useLegalLang;
export { LANGS };

const LOCALES = { de: DE, it: IT, fr: FR, es: ES, pl: PL };

// ------------------------------------------------------------------------------------------------
// WHITESPACE-TOLERANT LOOKUP — this is a bug fix, not a nicety.
//
// The page renders `tx("What you cannot see is ")` with a TRAILING SPACE (the next word sits in a
// coloured <span>), while the dictionary was written with the key trimmed. Exact-match lookup missed,
// the sentence fell back to English, and the result was a German page with English fragments in the
// middle of headlines — the "mixed language" report. It hit five separate strings.
// Trimming for the lookup and re-attaching the caller's own padding makes the whole class impossible.
// ------------------------------------------------------------------------------------------------
function padded(map, en) {
  if (!map) return undefined;
  if (map[en] !== undefined) return map[en];
  const core = en.trim();
  if (core === en) return undefined;
  const hit = map[core];
  if (hit === undefined) return undefined;
  const lead = en.slice(0, en.length - en.trimStart().length);
  const tail = en.slice(en.trimEnd().length);
  return lead + hit + tail;
}

// Optional recorder used by the build-time catalogue extractor (tools/i18n_catalogue.mjs). It exists
// so the catalogue is harvested from what the pages ACTUALLY render — including strings passed to
// tx() from a variable, which no regex over the source can see.
export function _record(fn) { _rec = fn; }
let _rec = null;

/** t("nav.demo") in the current language. Missing translation falls back to English, then the key. */
export function tr(lang, key) {
  const loc = LOCALES[lang];
  const hit = loc && loc.keyed ? loc.keyed[key] : undefined;
  if (hit !== undefined) return hit;
  return EN[key] !== undefined ? EN[key] : key;
}

/** tx("English source") -> the current language, or the original sentence untouched. */
export function trx(lang, en) {
  if (_rec) _rec(en);
  const loc = LOCALES[lang];
  const hit = loc ? padded(loc.byEn, en) : undefined;
  return hit !== undefined ? hit : en;
}

/** Hook form: `const [lang, setLang, t] = useT();` */
export function useT() {
  const [lang, setLang] = useLang();
  return [lang, setLang, useCallback((k) => tr(lang, k), [lang])];
}

/**
 * MEMOISED ON PURPOSE. A fresh arrow function every render changes the identity of `tx`, and
 * Landing.jsx lists it in a useEffect dependency array — so the effect re-ran on EVERY render and
 * appended the architecture map again each time. That was the duplicated content on the page.
 */
export function useTx() {
  const [lang] = useLang();
  return useCallback((en) => trx(lang, en), [lang]);
}

/** Coverage per locale. An untranslated string must be a visible number, not a surprise. */
export const I18N_STATS = () => {
  const enKeys = Object.keys(EN);
  const out = { keys: enKeys.length };
  for (const [code, loc] of Object.entries(LOCALES)) {
    out[code] = {
      keyed: enKeys.filter((k) => loc.keyed && loc.keyed[k] !== undefined).length,
      byEn: loc.byEn ? Object.keys(loc.byEn).length : 0,
    };
  }
  return out;
};
