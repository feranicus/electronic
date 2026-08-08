// partners-locales/ — the /partners content, one module per language.
//
// SAME PATTERN AS legal-locales/: long-form prose that only ever appears on one page lives beside
// that page, not in the shared string catalogue. See the header of en.js for the full reasoning.
//
// RESOLUTION, and why it is a Proxy rather than a merge:
//   reader's language -> English.
// A locale that is missing entirely, or that omits a section, degrades to readable English instead
// of white-screening on `sections[7].scr.a`. That is the same fallback doctrine as legal.jsx's
// `localised()`, i18n.jsx's `tr()` and the deck i18n engine: an incomplete translation must never
// be an exception. It is what makes it safe to add a language before its text is finished.
//
// A MERGE WOULD BE WRONG HERE. `sections` is an ARRAY whose order is the page order; merging two
// arrays index by index silently pairs the German "For resellers" with the English "For law firms"
// the moment one locale gains a section. So the fallback is whole-array: a locale either supplies
// the sections or it does not, and `test_partners.py` asserts every locale has the identical set of
// section ids in the identical order, which is what makes the whole-array choice safe.
import * as en from "./en.js";
import * as de from "./de.js";
import * as it from "./it.js";
import * as fr from "./fr.js";
import * as es from "./es.js";
import * as pl from "./pl.js";

export const PARTNER_LOCALES = { en, de, it, fr, es, pl };

/** The content for a reader language, falling back field by field to English. */
export function partnersFor(lang) {
  const L = PARTNER_LOCALES[lang] || en;
  return {
    meta: { ...en.meta, ...(L.meta || {}) },
    arts: Array.isArray(L.arts) && L.arts.length === en.arts.length ? L.arts : en.arts,
    sections: Array.isArray(L.sections) && L.sections.length === en.sections.length
      ? L.sections : en.sections,
  };
}
