// legal-locales/ — the legal copy (privacy page, Impressum, contact page, Art.13 notice) in the
// languages beyond the German reference and its English translation.
//
// ONE FILE PER LANGUAGE, and each file holds the PAGE and the NOTICE together — that is the whole
// point of the original single-file rule: a retention period or a processor must change in exactly
// one place per language, so the page and the in-app notice can never disagree.
//
// Anything absent here falls back to English, then German (see legal.jsx::localised). German remains
// the NORMATIVE text; the translations are provided for readability and say so on the page.
import * as it from "./it.jsx";
import * as fr from "./fr.jsx";
import * as es from "./es.jsx";
import * as pl from "./pl.jsx";

export const LEGAL_EXTRA = { it, fr, es, pl };
