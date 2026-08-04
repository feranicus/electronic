"""The document language must survive the WHOLE request path, not just the engine.

WHY THIS TEST EXISTS — ecolines.ru, 2026-08. The engine had just been generalised to N deck
languages and rendered Russian correctly in isolation. The operator picked "Русский" in the UI and
received ENGLISH decks. The run log said `"lang": "en"` and the filenames carried no `_RU` suffix.

The engine was innocent. `webapp/backend/app/main.py` still coerced with

    lang = "de" if str(req.lang or "en").lower().startswith("de") else "en"

in FIVE places (assess, assess-refine, compliance, compliance-refine) plus once more inside
`store.create_job`. `ru` was flattened to `en` at the API boundary, before the engine ever saw it.

Generalising one layer and leaving the layer in front of it on a two-language ternary is the same
defect class as a value having four homes: the stale one silently wins. So this asserts the RULE,
not one line — no module on the request path may hard-code a language set.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "webapp", "backend", "app")
ENGINE_DIR = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts")

# `de`-only coercion, in any of the shapes it has taken. Comments are stripped first: the engine
# legitimately DESCRIBES the old pattern in a docstring explaining why it was removed.
BAD = re.compile(r"""startswith\(\s*["']de["']\s*\)""")


def _code_only(path):
    out = []
    for line in open(path, encoding="utf-8"):
        s = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
        out.append(s)
    return "\n".join(out)


def test_no_de_only_coercion_on_the_request_path():
    offenders = []
    for d in (BACKEND, ENGINE_DIR):
        for f in sorted(os.listdir(d)):
            if not f.endswith(".py"):
                continue
            p = os.path.join(d, f)
            for i, line in enumerate(_code_only(p).splitlines(), 1):
                if BAD.search(line):
                    offenders.append("%s:%d: %s" % (f, i, line.strip()))
    assert not offenders, (
        "a two-language coercion survives on the request path — a third deck language will be "
        "silently flattened to English exactly as Russian was:\n  " + "\n  ".join(offenders))


def test_doc_lang_accepts_every_language_the_engine_claims():
    """Whatever deck_langs offers, the API must let through unchanged."""
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("deck_langs", os.path.join(ENGINE_DIR, "deck_langs.py"))
    dl = ilu.module_from_spec(spec); spec.loader.exec_module(dl)
    offered = dl.doc_langs()
    assert "ru" in offered, "ru.json + LANG_RU are committed, so Russian must be offered"
    for code in offered:
        assert dl.supported(code) == code, "%s is offered but coerced away" % code
    # ...and anything it cannot render must fail closed to English, never pass through.
    for code in ("it", "fr", "es", "pl", "zz", "", None):
        assert dl.supported(code) == "en"


def test_store_persists_the_language_it_was_given():
    """create_job used to re-coerce, so a valid `ru` died on the way into the DB."""
    src = _code_only(os.path.join(BACKEND, "store.py"))
    assert "startswith" not in src.split("def create_job", 1)[1].split("def ", 1)[0], (
        "store.create_job must persist the decision, not re-make it")
