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
# CACHED PER LANGUAGE. The cache used to be two module globals that ignored `lang` entirely, so the
# FIRST language loaded in a process won for every later call — harmless while only German existed,
# a silent cross-language bug the moment a second pack shipped.
_PACKS, _PATS = {}, {}

def _pack(lang):
    lang = _code(lang)
    if lang not in _PACKS:
        try:
            _PACKS[lang] = json.load(open(os.path.join(HERE, "%s.json" % lang), encoding="utf-8"))
        except Exception:
            _PACKS[lang] = {"strings": {}, "patterns": []}
        _PATS[lang] = [(re.compile(p), r) for p, r in _PACKS[lang].get("patterns", [])]
    return _PACKS[lang]


def _code(lang):
    """2-letter code. Anything without a dictionary on disk resolves to English."""
    c = str(lang or "en").strip().lower()[:2]
    if c == "en" or not c:
        return "en"
    return c if os.path.exists(os.path.join(HERE, "%s.json" % c)) else "en"

def _labels(s, code):
    """Translate the inline structure labels wherever they appear.

    A remediation body is written "WHY THIS SERVICE: ... WHAT YOU GET: ... HOW: ...". Those labels
    are PROSE inside a German sentence, and they shipped in English eleven times in one deck. They
    cannot be ordinary patterns: `t()` returns on the first pattern that matches, so a body
    containing all three would have had one translated and two left in English.
    They cannot be fixed by asking the model either. A prompt is a request; this is a guarantee.
    """
    L = _pack(code).get("labels") or {}
    for en, tr in L.items():
        if en in s:
            s = s.replace(en, tr)
    return s


def t(s, lang="de"):
    """Translate one string; passthrough if unknown or if there is no pack for `lang`."""
    if not isinstance(s, str) or not s.strip():
        return s
    code = _code(lang)
    if code == "en":
        return s
    s = _labels(s, code)
    P = _pack(code); S = P.get("strings", {})
    core = s.strip()
    if core in S:
        return s.replace(core, S[core])
    up = core.upper()
    if core == up:
        for k, v in S.items():
            if k.upper() == up:
                return s.replace(core, v.upper())
    for rx, rep in _PATS.get(code, ()):
        if rx.search(core):
            # JS-style $1 backrefs in the shared dictionary -> python \1
            return s.replace(core, rx.sub(re.sub(r"\$(\d)", r"\\\1", rep), core))
    comp = _composed(core, code)
    if comp is not None:
        return s.replace(core, comp)
    return s


# A COMPOSED FINDING TITLE IS NOT A DICTIONARY KEY, and that is why a German deck shipped English.
#
# shodan_recon builds every finding title as
#     "<template title><extra> (<n> hosts)"
# where <extra> is " — <product>" or ": <CVE-id> +<k> more CVEs". The composed string can never be
# a key, so the exact lookup above always missed. The pack worked around it with ONE HAND-WRITTEN
# REGEX PER DETECTOR PER LANGUAGE — and the moment a detector was added without one, its title
# shipped in English. Measured on the bottomline.com deck: three of ten titles, and 15 of the 33
# templates had no pattern at all.
#
# So translate the PARTS instead. The head goes through the dictionary (where the plain template
# title lives), the product name is a proper noun and stays, and the host count is rendered from
# the pack. A new detector now needs its plain title translated and nothing else.
_COMPOSED = re.compile(r"^(?P<body>.+) \((?P<n>\d+) hosts?\)$")
_MORE = re.compile(r"\+(\d+) more CVEs")


def _plural(n, forms):
    """Pick a plural form. Slavic rules when the pack supplies `few`, otherwise one/other.

    THE PACK DECLARES ITS OWN GRAMMAR. Hardcoding "add an s" here would be an English rule applied
    to every language; hardcoding the Slavic rule would be a Russian rule applied to German. The
    code asks what forms exist and applies the rule that those forms imply.
    """
    if "few" in forms:                                    # ru: 1 хост, 2-4 хоста, 5+ хостов
        a, b = n % 10, n % 100
        if a == 1 and b != 11:
            return forms.get("one", forms["other"])
        if 2 <= a <= 4 and not (12 <= b <= 14):
            return forms["few"]
        return forms["other"]
    return forms.get("one", forms["other"]) if n == 1 else forms["other"]


def _count(n, kind, code):
    forms = (_pack(code).get("counts") or {}).get(kind)
    if not forms:
        return None
    try:
        return _plural(n, forms) % n
    except (TypeError, ValueError):
        return None


def _composed(core, code):
    """Split "<template><extra> (<n> hosts)" and translate the parts.

    THE SPLIT POINT CANNOT BE GUESSED BY A SINGLE REGEX, and my first version proved it: several
    template titles CONTAIN an em dash ("No CAA record — any certificate authority may issue for
    this domain"), so a non-greedy head split at the wrong one and three detectors still failed.
    A greedy head fails the opposite way when a product IS appended. So try the candidate splits,
    longest head first, and take the one the dictionary actually recognises. The dictionary is the
    arbiter; the regex only proposes.
    """
    m = _COMPOSED.match(core)
    if not m:
        return None
    hosts = _count(int(m.group("n")), "hosts", code)
    if hosts is None:
        return None
    body = m.group("body")
    cands = [(body, "")]
    for sep in (" — ", ": "):
        i = body.rfind(sep)
        if i > 0:
            cands.append((body[:i], body[i:]))
    for head, extra in cands:
        got = t(head, code)
        if got != head:
            extra = _MORE.sub(
                lambda x: _count(int(x.group(1)), "more_cves", code) or x.group(0), extra)
            return "%s%s (%s)" % (got, extra, hosts)
    return None                # the template itself is untranslated: leave the title alone

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
    if _code(lang) == "en":
        return obj
    if isinstance(obj, dict):
        return {k: (v if k in _SKIP_KEYS else translate_json(v, lang, k)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [translate_json(v, lang, _key) for v in obj]
    if isinstance(obj, str):
        return t(obj, lang)
    return obj

def translate_file(path, lang="de"):
    if _code(lang) == "en" or not os.path.exists(path):
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
