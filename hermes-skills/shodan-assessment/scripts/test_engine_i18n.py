#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_engine_i18n.py — every customer-visible engine string exists in every document language.

BLOCKING, wired into ship.py. This is the check that did not exist, and its absence shipped a
German deck to a German bank with English finding titles on three of ten slides.

WHAT WENT WRONG, measured on bottomline.com_Shodan_Findings_DE.pptx:
  * 15 of the 33 TEMPLATES titles had no German translation at all, and the same 15 had no Russian.
  * 143 of 237 customer-visible TEMPLATES strings (60%) were untranslated in BOTH packs.
  * Every one of them belonged to a detector added AFTER the packs were written.

WHY IT KEPT HAPPENING. A finding title is COMPOSED at render time as
    "<template title><extra> (<n> hosts)"
so the composed string is never a dictionary key. The packs worked around that with one
hand-written regex per detector per language. Adding a detector therefore required a second edit,
in two other files, that nothing asserted — so it was forgotten every time. i18n.py now translates
the parts generically and this gate asserts the parts are present.

THE RULE THIS ENCODES: /api/langs is a CAPABILITY CLAIM. Advertising a document language means the
DETERMINISTIC path renders in it, not just the model's prose. The model writes over most of these
strings on a good run, which is exactly why the gap stayed invisible: it only shows on the findings
the enrichment did not reach, and those are the runs where the customer is already getting less.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "i18n"))

# THE CONSOLE ENCODING IS NOT THE TEST'S BUSINESS, AND IT KILLED THIS GATE ON THE FIRST REAL RUN.
# A Windows console defaults to cp1252. This check prints what it compared — and for Russian that
# detail is Cyrillic — so `print()` raised UnicodeEncodeError, the gate exited non-zero, and ship.py
# reported "ENGINE i18n REGRESSION - a document language would ship English finding text". Every
# translation was correct; the printer was not. A gate that cannot report its own PASS is worse than
# no gate: it blocks a good deploy and names the wrong culprit.
# Sixth instance of the same root cause in this repo (httpx, esbuild/win32, os.uname, ...): I
# validated in a UTF-8 sandbox and handed the operator a command for a cp1252 box.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")     # py3.7+; never raises on a pipe
    except Exception:
        pass


def out(s=""):
    """print() that CANNOT raise on the console it is given.

    reconfigure() above is the nice path — it prints real Cyrillic. But it sits in a try/except, so
    if it ever fails (an older Python, a redirected stream, a platform that refuses) the gate falls
    straight back to cp1252 and dies again, SILENTLY, in the same place. A guard whose failure is
    invisible is the shape of defect this repo keeps paying for, so the printing itself is made
    total: on UnicodeEncodeError, re-encode with backslashreplace. Cyrillic then renders as escapes
    rather than crashing — the evidence is degraded, never lost, and the gate still reports.
    MEASURED, not assumed: with reconfigure() forced to fail under PYTHONIOENCODING=cp1252 the old
    version exited 1 with UnicodeEncodeError; this one exits 0.
    """
    try:
        print(s)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(s).encode(enc, "backslashreplace").decode(enc, "replace"))

import deck_langs                                                        # noqa: E402
import shodan_recon as R                                                 # noqa: E402
import i18n as I                                                         # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    out("  %-4s %s%s" % ("PASS" if ok else "FAIL", label, ("   " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)


def customer_visible():
    """Every deterministic string from TEMPLATES that can reach a slide, with where it came from."""
    out = {}
    for key, tpl in R.TEMPLATES.items():
        title, why, rem = tpl[0], tpl[1], tpl[2]
        out.setdefault(title, "%s.title" % key)
        for w in why:
            out.setdefault(w, "%s.why" % key)
        for r in rem:
            if isinstance(r, dict):
                for f in ("title", "body"):
                    if r.get(f):
                        out.setdefault(r[f], "%s.rem.%s" % (key, f))
            elif r:
                out.setdefault(r, "%s.rem" % key)
    return {k: v for k, v in out.items() if len(k.strip()) > 3}


def translated(s, lang):
    """Does the pack render this string in `lang`? Exact key, pattern, or the composed path."""
    return I.t(s, lang) != s


def main():
    out("=" * 78)
    out("  Engine i18n — the deterministic strings, in every document language we advertise")
    out("=" * 78)

    langs = [l for l in deck_langs.doc_langs() if l != "en"]
    need = customer_visible()
    out("  %d customer-visible TEMPLATES string(s); document languages advertised: %s"
          % (len(need), ", ".join(langs) or "(none besides en)"))
    out()

    for lang in langs:
        missing = sorted((v, k) for k, v in need.items() if not translated(k, lang))
        check(not missing, "%s: every finding title, why and remediation is translated" % lang,
              "%d of %d missing" % (len(missing), len(need)))
        for src, txt in missing[:8]:
            out("        %-28s %s" % (src, txt[:74]))

        # THE COMPOSED TITLE IS THE ONE THAT SHIPPED IN ENGLISH. Assert the real rendered shape,
        # not just the plain template, because the plain template being present is what everybody
        # assumed and it was not what reached the slide.
        bad = []
        for key, tpl in R.TEMPLATES.items():
            for probe in ("%s — SomeProduct (14 hosts)" % tpl[0], "%s (1 host)" % tpl[0]):
                if I.t(probe, lang) == probe:
                    bad.append((key, probe))
                    break
        check(not bad, "%s: composed titles translate (template + product + host count)" % lang,
              "%d of %d fail" % (len(bad), len(R.TEMPLATES)))
        for k, p in bad[:5]:
            out("        %-22s %s" % (k, p[:70]))

        # PLURALS. "(1 Hosts)" is the kind of error a German reader notices immediately, and the
        # legacy per-detector regexes produced exactly that because each hardcoded the plural.
        #
        # ASSERT THE NOUN, NOT THE STRING. My first version compared the two rendered titles and
        # required "(1 " to appear — which "(1 Hosts)" satisfies perfectly. It passed against a pack
        # deliberately mutated to `{"other": "%d Hosts"}`, i.e. against the exact defect it is named
        # for. A check aimed next to its subject cannot fail for the right reason.
        def _noun(s):
            m = re.search(r"\((\d+)\s*([^)]*)\)\s*$", s) or re.search(r"\(([^)]*?)(\d+)\)\s*$", s)
            return (m.group(2) if m and m.group(2).strip(" 0123456789") else "").strip()
        one, many = (I.t("Exposed database — MongoDB (%s)" % n, lang)
                     for n in ("1 host", "14 hosts"))
        n1, nn = _noun(one), _noun(many)
        check(bool(n1) and bool(nn) and n1 != nn,
              "%s: the host count is declined, not hardcoded" % lang,
              "singular %r vs plural %r" % (n1, nn))

        # THE INLINE LABELS. A remediation body is structured "WHY THIS SERVICE: ... WHAT YOU GET:
        # ... HOW: ...". They are prose, they appear inside German sentences, and they shipped in
        # English 11 times in one deck.
        for lab in ("WHY THIS SERVICE:", "WHAT YOU GET:", "HOW:"):
            probe = "%s the exposure is removed structurally." % lab
            check(I.t(probe, lang) != probe, "%s: the inline label %r is translated" % (lang, lab))

    # ENGLISH MUST BE UNTOUCHED. Every one of these paths is a no-op for en, and if that ever stops
    # being true the English decks change silently.
    sample = list(need)[:40]
    check(all(I.t(s, "en") == s for s in sample), "en is a passthrough, byte for byte")

    out()
    out("=" * 78)
    if FAILS:
        out("  %d FAILURE(S): %s" % (len(FAILS), "; ".join(FAILS[:3])))
        out()
        out("  A document language we ADVERTISE must render the deterministic path, not only the")
        out("  model's prose. Add the string to scripts/i18n/<lang>.json and re-run.")
        return 1
    out("  engine i18n: every finding string renders in every advertised document language")
    return 0


if __name__ == "__main__":
    sys.exit(main())
