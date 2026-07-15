#!/usr/bin/env python3
"""
i18n.py — translate the ENGINE-generated English strings inside findings/cbiq/geopol.json.

Three streams of text end up on a slide:
  1. deck chrome, hardcoded in the four .js builders  -> scripts/i18n/deck_i18n.js (same de.json)
  2. LLM prose (exec_summary, why, rem, ...)          -> enrich.py asks the model for German
  3. deterministic prose the PYTHON engine writes      -> THIS module

Stream 3 (finding titles, Colt control names, framework lines, bucket names) is templated English,
so it translates exactly — no model call, no cost, no drift. Uses the SAME committed de.json as the
JS layer, so a term is never translated two different ways.

Unknown strings are returned untouched (English), never dropped.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
_PACK, _PATTERNS = None, None

def _pack(lang):
    global _PACK, _PATTERNS
    if _PACK is None:
        try:
            _PACK = json.load(open(os.path.join(HERE, "%s.json" % lang), encoding="utf-8"))
        except Exception:
            _PACK = {"strings": {}, "patterns": []}
        _PATTERNS = [(re.compile(p), r) for p, r in _PACK.get("patterns", [])]
    return _PACK

def t(s, lang="de"):
    """Translate one string; passthrough if unknown."""
    if not isinstance(s, str) or not s.strip() or not str(lang).lower().startswith("de"):
        return s
    P = _pack("de"); S = P.get("strings", {})
    core = s.strip()
    if core in S:
        return s.replace(core, S[core])
    up = core.upper()
    if core == up:
        for k, v in S.items():
            if k.upper() == up:
                return s.replace(core, v.upper())
    for rx, rep in _PATTERNS:
        if rx.search(core):
            # JS-style $1 backrefs in the shared dictionary -> python \1
            return s.replace(core, rx.sub(re.sub(r"\$(\d)", r"\\\1", rep), core))
    return s

# Keys we must NEVER translate.
#  (a) ENUM/LOOKUP KEYS — the builders group and colour-map on these exact English values
#      (findings[].sev == "CRITICAL", geopol actors[].band == "NATION-STATE", tier, ...).
#      Translating them makes findings silently VANISH from the deck (grouping stops matching).
#      They are translated at RENDER time by deck_i18n.js instead, which is display-only.
#  (b) LLM prose — already German from enrich.py.
#  (c) identifiers / proper nouns / machine values.
_SKIP_KEYS = {
    # (a) enum + lookup keys — load-bearing
    "sev", "severity", "band", "tier", "status", "phase", "key", "type", "tag",
    # (b) LLM prose
    "exec_summary", "qa_note", "geopol_context",
    # (c) identifiers / machine values
    "id", "cve", "cves", "refs", "model", "distribution", "code", "symbol", "company",
    "customer", "date", "ip", "port", "hostname", "asn", "favicon", "jarm", "cpe",
}

def translate_json(obj, lang="de", _key=None):
    """Deep-translate a findings/cbiq/geopol structure in place-safe fashion."""
    if not str(lang).lower().startswith("de"):
        return obj
    if isinstance(obj, dict):
        return {k: (v if k in _SKIP_KEYS else translate_json(v, lang, k)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [translate_json(v, lang, _key) for v in obj]
    if isinstance(obj, str):
        return t(obj, lang)
    return obj

def translate_file(path, lang="de"):
    if not str(lang).lower().startswith("de") or not os.path.exists(path):
        return False
    try:
        j = json.load(open(path, encoding="utf-8"))
        json.dump(translate_json(j, lang), open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print("[warn] i18n.translate_file(%s): %s" % (path, e))
        return False

if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        print(("translated " if translate_file(p, "de") else "skipped "), p)
