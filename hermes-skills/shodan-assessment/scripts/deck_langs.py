"""deck_langs.py — the ONE source of truth for which languages the DECK ENGINE can actually produce.

WHY THIS EXISTS
The web UI now ships in six languages (en/de/it/fr/es/pl). The DECK engine does not: a deck language
needs three things, and only two of them are a dictionary —

  1. `scripts/i18n/<lang>.json`  — the ~530 deck-chrome literals (deck_i18n.js translates at the
     addText/addTable boundary),
  2. `scripts/i18n/i18n.py`      — the engine-deterministic prose post-pass (finding titles, controls),
  3. a LANG_* prompt block in `enrich.py` — the per-company PROSE, which no dictionary can ever cover.

So "the site speaks Polish" does NOT imply "the decks speak Polish". Before this module, the web
selector and the bot were free to send `--lang it`; the engine would silently fall back to English
and the customer would receive an English deck from an Italian-language interface with no warning.
That is the same defect class as a scope pivot that matches without proving ownership: a claim the
system cannot actually back.

The list is DERIVED FROM THE ARTIFACT — the dictionaries present on disk — not from a hardcoded
constant that drifts away from reality. Drop a new `it.json` in and add its enrich prompt block, and
the selector offers Italian on the next deploy with no UI change. Delete one and the option vanishes.
That is the same doctrine as engine_config.py: resolve and report, never guess.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
I18N_DIR = os.path.join(HERE, "i18n")

# Display names, so the UI never has to carry its own copy of this mapping.
NAMES = {
    "en": "English",
    "de": "Deutsch (Hochdeutsch)",
    "it": "Italiano",
    "fr": "Français",
    "es": "Español",
    "pl": "Polski",
    "ru": "Русский",
    "pt": "Português (Portugal e Angola)",
}

# English is the source language of every builder — it needs no dictionary and is always available.
BASE = "en"

# A PACK MUST BE COMPLETE, NOT MERELY PRESENT.
#
# The rule written at the top of this file is "half a language is not a language", and until now it
# was enforced at the granularity of a FILE: `pt.json` exists -> Portuguese is offered. A pack
# translated to 40% would have passed, and the customer would have received a deck in two languages
# at once, because an unknown string falls through to English by design and that fall-through is
# invisible. The file-level check could not see its own subject (defect class 1): presence is not
# completeness.
#
# The reference key set is DERIVED from the other packs on disk, never hardcoded, and never from the
# pack being measured — a denominator produced by the thing under test is not a measurement
# (class 3). de.json and ru.json currently carry an identical 780 keys, so the reference is
# unambiguous today and will track the builders as they grow.
PACK_COVERAGE_MIN = 0.98
# ... and it must actually be TRANSLATED. A stub pack that copies the English value for every key
# would score 100% coverage. Measured baselines: de.json leaves 4.0% of values identical to the
# English (proper nouns: ASN, STATUS, FAIR, Deloitte), ru.json 2.7%. Portuguese shares far more
# vocabulary with English than German does, so the ceiling is set well above both rather than
# tuned to them: the job here is to catch a stub at ~100% identical, not to grade style.
PACK_IDENTICAL_MAX = 0.25

_CACHE = {}                                   # path -> (mtime, size, strings dict)


def _strings(path):
    """The `strings` block of a pack, cached on (mtime, size).

    doc_langs() is called from an HTTP handler to answer GET /api/langs. Re-reading two 140 KB JSON
    documents on every request would make a capability question into a latency problem, which is
    the rule that an optional lookup must never be slower than the page's own budget.
    """
    try:
        st = os.stat(path)
        sig = (st.st_mtime, st.st_size)
    except OSError:
        return {}
    hit = _CACHE.get(path)
    if hit and hit[0] == sig:
        return hit[1]
    try:
        import json
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        s = d.get("strings") or {}
        if not isinstance(s, dict):
            s = {}
    except (OSError, ValueError):
        return {}
    _CACHE[path] = (sig, s)
    return s


def _pack_codes():
    try:
        return sorted(f[:-5] for f in os.listdir(I18N_DIR)
                      if f.endswith(".json") and f[:-5] != BASE)
    except OSError:
        return []


def reference_keys(exclude=None):
    """The key universe a pack is measured against: the largest OTHER pack on disk.

    Excluding the pack under test is what stops a stub from being graded against itself.
    """
    best = set()
    for code in _pack_codes():
        if code == exclude:
            continue
        ks = set(_strings(os.path.join(I18N_DIR, code + ".json")))
        if len(ks) > len(best):
            best = ks
    return best


def pack_report(code):
    """Measure one pack. Returns the numbers AND the verdict, never a bare verdict.

    `ok` False with `ref` 0 means there was nothing to measure against, which is reported as
    unknown rather than scored as a pass.
    """
    s = _strings(os.path.join(I18N_DIR, code + ".json"))
    ref = reference_keys(exclude=code)
    out = {"code": code, "keys": len(s), "ref": len(ref), "coverage": 0.0,
           "identical": 0.0, "prose_block": _has_prose_block(code), "ok": False, "why": ""}
    if not ref:
        out["why"] = "no reference pack on disk to measure against"
        return out
    if not s:
        out["why"] = "no pack, or no 'strings' block in it"
        return out
    out["coverage"] = len(set(s) & ref) / float(len(ref))
    ident = sum(1 for k, v in s.items() if isinstance(v, str) and v.strip() == k.strip())
    out["identical"] = ident / float(len(s))
    if out["coverage"] < PACK_COVERAGE_MIN:
        out["why"] = ("pack covers %.1f%% of the %d reference strings, below the %.0f%% floor; %d "
                      "missing keys would render in English inside a translated deck"
                      % (100 * out["coverage"], len(ref), 100 * PACK_COVERAGE_MIN,
                         len(ref - set(s))))
    elif out["identical"] > PACK_IDENTICAL_MAX:
        out["why"] = ("%.1f%% of values are identical to the English key, above the %.0f%% ceiling "
                      "— this looks like a stub rather than a translation"
                      % (100 * out["identical"], 100 * PACK_IDENTICAL_MAX))
    elif not out["prose_block"]:
        out["why"] = "no LANG_* prompt block in enrich.py: deck chrome would be translated around English prose"
    else:
        out["ok"] = True
    return out


def _has_prose_block(code: str) -> bool:
    """Does enrich.py carry a LANG_* instruction for this code?

    A dictionary translates deck CHROME. The per-company PROSE — exec_summary, why, remediation
    bodies, the loss scenario — is written fresh by a model for every customer, so no dictionary can
    ever reach it. Shipping `<code>.json` alone would produce a deck with translated labels wrapped
    around English paragraphs, which is worse than an honest English deck. Read enrich.py's registry
    as TEXT rather than importing it: this module is imported by the web app to answer a capability
    question, and importing enrich pulls in the API key handling for no reason.
    """
    try:
        with open(os.path.join(HERE, "enrich.py"), encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return False
    return ('"%s":' % code) in src.split("LANG_BLOCKS", 1)[-1][:400]


def doc_langs() -> list[str]:
    """Languages the deck builders can genuinely render, English first.

    A language counts only when BOTH halves exist — the chrome dictionary AND the prose prompt.
    Fail-closed: half a language is not a language.
    """
    out = [BASE]
    for code in _pack_codes():                # already OSError-safe: [] when the dir is unreadable
        if code not in out and pack_report(code)["ok"]:
            out.append(code)
    return out


def supported(lang: str | None) -> str:
    """Coerce a requested language to one the engine can actually produce.

    Callers pass the USER'S interface language, which may be any of the six the site ships. Returning
    English for the other four is the honest answer; silently accepting `it` and emitting English
    would be a lie told by omission.
    """
    code = (lang or BASE).strip().lower()[:2]
    return code if code in doc_langs() else BASE


def catalogue() -> list[dict]:
    """[{code, name}] for the UI, in a stable order."""
    return [{"code": c, "name": NAMES.get(c, c.upper())} for c in doc_langs()]


if __name__ == "__main__":                    # python deck_langs.py -> what can we really produce?
    import json
    # PRINT THE COMPARISON, NOT A VERDICT. A language that is NOT offered has to say how far short
    # it falls, or "Portuguese is missing" reads as a bug in the selector rather than as 380
    # untranslated strings.
    print("reference key universe: %d strings" % len(reference_keys()))
    for _c in _pack_codes():
        _r = pack_report(_c)
        print("  %-4s %-6s keys %4d/%-4d  coverage %5.1f%%  identical %4.1f%%  prose %-5s %s"
              % (_c, "OFFERED" if _r["ok"] else "NO", _r["keys"], _r["ref"],
                 100 * _r["coverage"], 100 * _r["identical"], _r["prose_block"], _r["why"]))
    print(json.dumps({"doc_langs": doc_langs(), "catalogue": catalogue()},
                     ensure_ascii=False, indent=2))
