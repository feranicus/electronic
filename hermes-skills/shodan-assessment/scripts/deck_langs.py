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
}

# English is the source language of every builder — it needs no dictionary and is always available.
BASE = "en"


def doc_langs() -> list[str]:
    """Languages the deck builders can genuinely render, English first."""
    out = [BASE]
    try:
        for f in sorted(os.listdir(I18N_DIR)):
            if not f.endswith(".json"):
                continue
            code = f[:-5]
            if code != BASE and code not in out:
                out.append(code)
    except OSError:
        pass                                  # no dictionaries readable -> English only, never a crash
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
    print(json.dumps({"doc_langs": doc_langs(), "catalogue": catalogue()}, ensure_ascii=False, indent=2))
