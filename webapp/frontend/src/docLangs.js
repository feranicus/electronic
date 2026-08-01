// docLangs.js — the DOCUMENT language of a run, which is NOT the language of the interface.
//
// THE BUG THIS EXISTS TO PREVENT: the Assess and Compliance screens defaulted the document language
// from the SITE language (`localStorage.cg_legal_lang`). That was right while the site shipped two
// languages and the engine shipped the same two. The site now ships six and the engine still ships
// two — a deck language needs a `scripts/i18n/<lang>.json`, an i18n.py post-pass AND a LANG_* prompt
// block in enrich.py, because per-company prose is written by a model and no dictionary can cover it.
// So an Italian reader would have sent `--lang it`, the engine would have quietly fallen back to
// English, and the interface would never have admitted it.
//
// The list comes from the SERVER (`/api/langs`), which derives it from the dictionaries actually on
// disk. A hardcoded array here would be a second source of truth and would drift the first time a
// dictionary is added or removed — the same defect as the enrichment chain having four homes.
import { useEffect, useState } from "react";
import { getLangs } from "./api.js";
import { useLegalLang } from "./legal";

// Until the probe answers, English is the only thing we can promise. Optimistically listing German
// would flash an option that might not exist; starting narrow and widening never shows a false one.
const FALLBACK = [{ code: "en", name: "English" }];

let _cache = null;                    // module scope: one fetch per page load, shared by both screens

export function useDocLangs() {
  const [siteLang] = useLegalLang();
  const [docs, setDocs] = useState(_cache || FALLBACK);
  const [lang, setLang] = useState("en");
  const [ready, setReady] = useState(!!_cache);

  useEffect(() => {
    let alive = true;
    (async () => {
      if (!_cache) {
        const { ok, data } = await getLangs();
        if (ok && data && Array.isArray(data.doc) && data.doc.length) _cache = data.doc;
      }
      if (!alive) return;
      setDocs(_cache || FALLBACK);
      setReady(true);
    })();
    return () => { alive = false; };
  }, []);

  // Default to the reader's own language when the engine can produce it, English otherwise. Run this
  // whenever either input changes: the probe may land after the first render, and the reader can
  // switch the site language while the form is open.
  useEffect(() => {
    if (!ready) return;
    const codes = (docs || FALLBACK).map((d) => d.code);
    setLang((cur) => (codes.includes(cur) ? cur : (codes.includes(siteLang) ? siteLang : "en")));
  }, [ready, docs, siteLang]);

  // `unavailable` drives the honest one-liner under the selector: it is true exactly when the reader
  // is browsing in a language the decks cannot be written in, which is a fact worth stating rather
  // than hiding behind a silently-English default.
  const unavailable = ready && !docs.some((d) => d.code === siteLang);
  return { docs, lang, setLang, unavailable };
}
