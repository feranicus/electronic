#!/usr/bin/env python3
"""add_language.py — add a COMPLETE language to cybergod.ai with ONE command, using our own AI.

    python add_language.py pt --name "Português"
    python add_language.py ja --name "日本語" --only decks
    python add_language.py it --name "Italiano" --dry-run

WHY THIS EXISTS
Adding German took a week of hand-editing. Adding Russian still meant touching five separate
surfaces by hand. That does not scale to "many languages", and hand-editing half the codebase per
language is how a locale ends up 80% translated with nobody able to say which 20% is missing.

This script does the whole job from the ENGLISH SOURCE OF TRUTH that already exists in the repo,
translates it with the same DigitalOcean model chain the product already pays for, writes every
file, and then RUNS THE EXISTING GATES so a half-finished language cannot ship.

THE FIVE SURFACES, and why each is separate:
  1. DECK CHROME      scripts/i18n/<code>.json      ~620 literals + 66 regex patterns + units/locale
  2. DECK PROSE       enrich.py::LANG_BLOCKS        the per-company text a MODEL writes — no
                                                    dictionary can ever reach it, which is why
                                                    deck_langs.py refuses to offer a language
                                                    without this block
  3. WEB UI           webapp/frontend/src/locales/<code>.js   201 keyed + 203 by-English strings
  4. ANIMATED HTML    scripts/geopol_html/i18n/<code>.json    skeleton + canvas + fallback strings
  5. COMPLIANCE       build_compliance_deck.js::LABELS        a per-builder label map

Anything a locale does not cover falls back to English at RUNTIME, so a partial run is safe — it is
simply incomplete, and `--verify` will say by how much.

RESUMABLE BY DESIGN: every batch is cached under .add_language_cache/<code>/. A rerun re-translates
only what is missing, so a timeout or a rate-limit costs minutes, not the whole language.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "hermes-skills", "shodan-assessment", "scripts")
I18N = os.path.join(ENGINE, "i18n")
GEO = os.path.join(ENGINE, "geopol_html", "i18n")
FE = os.path.join(HERE, "webapp", "frontend")
LOCALES = os.path.join(FE, "src", "locales")
CACHE = os.path.join(HERE, ".add_language_cache")

# ------------------------------------------------------------------ protected vocabulary
# Never translated, on ANY surface. A model asked to "translate everything" will happily render
# "NIS2" as a local acronym and silently break a legal citation, so the list is stated in the prompt
# AND re-checked on the way back: a batch that lost a protected token is rejected and retried.
PROTECTED = [
    "NIS2", "CRA", "Cyber Resilience Act", "EU AI Act", "DORA", "GDPR", "DSGVO", "RGPD", "RODO",
    "MITRE ATT&CK", "FAIR", "NIST", "BSI", "ISO", "IEC", "TISAX", "UNECE", "CISA KEV", "EPSS",
    "CVSS", "Shodan", "Monte-Carlo", "Admiralty", "Diamond Model", "Pyramid of Pain",
    "SASE", "ZTNA", "WAF", "NGFW", "SD-WAN", "DPI", "NDR", "SOC", "MFA", "SIEM",
    "Managed Firewall", "Managed WAF", "Managed Security Service", "Managed DDoS protection",
    "RDP", "Telnet", "TLS", "SSL", "VPN", "SSH", "SMB", "SNMP", "FTP", "IMAP", "SIP", "HTTP",
    "HTTPS", "DNS", "BGP", "ASN", "IP", "API", "PPTX", "HTML", "JSON",
    "C-BIQ", "GEOPOL", "DELTAS", "Findings", "cybergod.ai", "Cybergod LLC", "S4Biz Group",
]

STYLE = (
    "Business register for a CISO/CFO audience: formal, dense, no colloquialisms, no exclamation "
    "marks, no marketing tone, no calques of English word order. Address the reader with the "
    "language's standard FORMAL form of address."
)


# ------------------------------------------------------------------ model access
def _load_env():
    """Read the API key from assess-bot/.env — the documented local source of truth for secrets."""
    p = os.path.join(HERE, "assess-bot", ".env")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _enrich():
    """Import the engine's own model client, so the chain, failover and pricing are shared."""
    sys.path.insert(0, ENGINE)
    import enrich as E  # noqa: E402
    return E


# ------------------------------------------------------------------ the translation call
BATCH_PROMPT = """You are a professional localiser. Translate the VALUES of the JSON object below \
from English into %(language)s (%(code)s).

CONTEXT — these strings appear in %(surface)s of a cybersecurity assessment product. It maps a \
company's internet-facing estate from public sources, prices the risk in euros, names likely threat \
actors, and grades EU regulatory exposure. The reader is a CISO, a CFO or a board.

STYLE: %(style)s

HARD RULES
1. Return ONLY a JSON object mapping each ENGLISH KEY to its %(language)s translation. No prose, no
   markdown, no code fences. Every key present in the input MUST be present in the output.
2. Keys are byte-identical to the input, INCLUDING leading/trailing spaces, punctuation, curly
   quotes and HTML entities. Copy them; do not retype or "tidy" them.
3. NEVER translate these — copy them through verbatim:
   %(protected)s
   ...nor CVE identifiers, article citations (Art. 32, Art. 21(2)(d)(i)), hostnames, IP addresses,
   ports, product names, company names, file names or anything inside <code>...</code>.
4. Preserve inline HTML tags (<b>, <code>, <br/>) exactly, including their contents when those are
   code. Translate only the prose around them.
5. Preserve every %%s / {token} / $1 placeholder, in the same order and with the same meaning.
6. A key in ALL CAPS is a rendered heading — its translation must also be ALL CAPS.
7. LENGTH IS LOAD-BEARING: these render into fixed-width boxes. Stay as close to the English
   character count as the language allows; prefer a shorter true synonym over a literal expansion.
%(extra)s
INPUT:
%(payload)s"""


def _translate_batch(E, items, language, code, surface, extra="", model=None):
    """One batch -> {english: translated}. Raises on an unusable answer so the caller can retry."""
    prompt = BATCH_PROMPT % {
        "language": language, "code": code, "surface": surface, "style": STYLE,
        "protected": ", ".join(PROTECTED), "extra": extra,
        "payload": json.dumps({k: "" for k in items}, ensure_ascii=False, indent=1),
    }
    raw, _usage = E._call(prompt, model=model, timeout=180)
    out = E._json(raw)
    if not isinstance(out, dict):
        raise ValueError("model returned %s, not an object" % type(out).__name__)
    missing = [k for k in items if not str(out.get(k, "")).strip()]
    if missing:
        raise ValueError("%d/%d keys missing or empty (e.g. %r)" % (len(missing), len(items), missing[0][:60]))
    # A protected token that vanished means the model paraphrased a citation. Reject the batch.
    for k in items:
        v = str(out[k])
        for tok in PROTECTED:
            if tok in k and tok not in v:
                raise ValueError("protected term %r lost in the translation of %r" % (tok, k[:60]))
    return {k: str(out[k]) for k in items}


def _translate_all(E, keys, language, code, surface, extra="", batch=40, model=None):
    """Batched + cached + retried. Returns {english: translated} for everything it managed."""
    cdir = os.path.join(CACHE, code)
    os.makedirs(cdir, exist_ok=True)
    cpath = os.path.join(cdir, re.sub(r"\W+", "_", surface) + ".json")
    done = {}
    if os.path.exists(cpath):
        try:
            done = json.load(open(cpath, encoding="utf-8"))
        except Exception:
            done = {}
    todo = [k for k in keys if k not in done]
    if not todo:
        print("    %s: %d/%d already cached" % (surface, len(done), len(keys)))
        return done
    print("    %s: %d string(s) to translate (%d cached)" % (surface, len(todo), len(done)))
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        for attempt in (1, 2, 3):
            try:
                t0 = time.time()
                done.update(_translate_batch(E, chunk, language, code, surface, extra, model))
                print("      batch %d-%d ok (%.0fs)" % (i + 1, i + len(chunk), time.time() - t0))
                break
            except Exception as e:
                print("      batch %d-%d attempt %d failed: %s" % (i + 1, i + len(chunk), attempt, e))
                if attempt == 3:
                    print("      giving up on this batch — rerun to retry (progress is cached)")
                time.sleep(2 * attempt)
        json.dump(done, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return done


# ------------------------------------------------------------------ surface 1: deck chrome
def do_decks(E, code, language, model, dry):
    de = json.load(open(os.path.join(I18N, "de.json"), encoding="utf-8"))
    strings = list(de["strings"].keys())
    tr = _translate_all(E, strings, language, code, "PowerPoint slide labels and headings",
                        model=model)

    # Patterns carry $1/$2 captures around live numbers. Translated separately with an explicit
    # warning about numeral agreement, which is the one thing a naive translation always gets wrong.
    pat_extra = (
        "8. These are SENTENCE TEMPLATES. Each $1/$2 is replaced at render time by a NUMBER or a "
        "NAME you cannot see. Write the sentence so it is grammatical for ANY value — if the "
        "language inflects nouns after numerals, restructure (e.g. 'count: $1') rather than "
        "guessing. Every $n in the English MUST appear in your translation.\n"
    )
    pkeys = [rep for _rx, rep in de["patterns"]]
    ptr = _translate_all(E, pkeys, language, code, "sentence templates with numeric placeholders",
                         extra=pat_extra, batch=20, model=model)
    patterns = []
    for rx, rep in de["patterns"]:
        new = ptr.get(rep, rep)
        if set(re.findall(r"\$\d", rep)) != set(re.findall(r"\$\d", new)):
            print("      !! capture mismatch, keeping English for: %r" % rep[:60])
            new = rep
        patterns.append([rx, new])           # the REGEX matches English and must never change

    units = _translate_all(E, ["bn", "M", "k"], language, code,
                           "compact number suffixes (billion / million / thousand), e.g. ' Mrd.'",
                           batch=3, model=model)
    pack = {
        "_comment": ("%s pack, generated by add_language.py. Keys = the English string as RENDERED "
                     "by the deck builders. Never translate ENUM/lookup keys in the engine JSON "
                     "(sev, band, tier) — they are matched for grouping and colour maps." % language),
        "locale": "%s-%s" % (code, code.upper()),
        "dateFormat": "dmy",
        "strings": tr, "patterns": patterns, "sizes": {}, "units": units,
    }
    out = os.path.join(I18N, "%s.json" % code)
    if dry:
        print("    [dry-run] would write %s (%d strings)" % (out, len(tr)))
        return
    json.dump(pack, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("    wrote %s (%d strings, %d patterns)" % (out, len(tr), len(patterns)))


# ------------------------------------------------------------------ surface 2: the prose prompt
def do_prose(E, code, language, model, dry):
    """The LANG_<CODE> block in enrich.py — without it deck_langs refuses to offer the language."""
    src = open(os.path.join(ENGINE, "enrich.py"), encoding="utf-8").read()
    upper = code.upper()
    if "LANG_%s" % upper in src:
        print("    enrich.py already has LANG_%s — left untouched" % upper)
        return
    ask = ("Write a LANGUAGE INSTRUCTION for an LLM prompt, IN %s. It must tell the model to write "
           "every prose field (exec_summary, what, why, rem, strengths, colt_mitigation, "
           "realComparable, lossScenario, geopol_context, qa_note) exclusively in %s, in a formal "
           "business register for a CISO/CFO; to translate risk-methodology terms (ALE, PML, LEF, "
           "TEF, Loss Magnitude, Cost of Delay, ROSI, Kill Chain, finding, exposure, remediation, "
           "attack surface) into that language and give the equivalents; to leave proper nouns and "
           "identifiers untranslated (%s, CVE ids, hostnames, IPs, ports, protocol names, company "
           "names); and that JSON KEYS stay English while only VALUES are translated, with facts, "
           "numbers, ids and evidence unchanged. Return ONLY the instruction text."
           % (language, language, ", ".join(PROTECTED[:18])))
    raw, _ = E._call(ask, model=model, timeout=180)
    body = raw.strip().strip("`")
    block = '\n\nLANG_%s = """\n=== %s / LANGUAGE ===\n%s\n"""\n' % (upper, language.upper(), body)
    if dry:
        print("    [dry-run] would add LANG_%s (%d chars) to enrich.py" % (upper, len(body)))
        return
    anchor = "\n# THE LANGUAGE REGISTRY."
    assert anchor in src, "enrich.py: LANG_BLOCKS registry anchor missing"
    src = src.replace(anchor, block + anchor, 1)
    src = re.sub(r"LANG_BLOCKS = \{([^}]*)\}",
                 lambda m: 'LANG_BLOCKS = {%s, "%s": LANG_%s}' % (m.group(1).rstrip(), code, upper),
                 src, count=1)
    open(os.path.join(ENGINE, "enrich.py"), "w", encoding="utf-8").write(src)
    print("    added LANG_%s to enrich.py and registered it in LANG_BLOCKS" % upper)


# ------------------------------------------------------------------ surface 3: the web UI
def do_web(E, code, language, model, dry):
    cat = os.path.join(FE, "tools", "catalogue.json")
    if not os.path.exists(cat):
        subprocess.run(["node", "tools/i18n_catalogue.mjs"], cwd=FE, capture_output=True)
    c = json.load(open(cat, encoding="utf-8"))
    keyed_en, by_en = c["keyed"], c["byEn"]

    tab_extra = ("8b. Keys beginning `tab.` are phone tab-bar labels with a HARD MAXIMUM OF 8 "
                 "CHARACTERS. Count them. Use a real short word, never a truncation.\n")
    kt = _translate_all(E, list(keyed_en.values()), language, code,
                        "web application UI labels, buttons and status messages",
                        extra=tab_extra, model=model)
    keyed = {k: kt.get(v, v) for k, v in keyed_en.items()}
    for k, v in list(keyed.items()):
        if k.startswith("tab.") and len(v) > 8:
            print("      !! %s = %r is %d chars (>8) — trimming to the English" % (k, v, len(v)))
            keyed[k] = keyed_en[k]

    seam = ("8c. Some strings are FRAGMENTS that are concatenated with a coloured word between "
            "them (e.g. 'What you cannot see is ' + 'already public'). Translate each fragment so "
            "the JOIN is grammatical, moving words across the boundary if the language needs it, "
            "and PRESERVE leading/trailing spaces exactly.\n")
    bt = _translate_all(E, by_en, language, code, "marketing website copy", extra=seam, model=model)

    body = ('// locales/%s.js — %s. Generated by `python add_language.py %s`.\n'
            '// `keyed` maps dotted keys (see locales/en.js); `byEn` maps the English sentence to its\n'
            '// translation. Anything missing falls back to English, so this file is safe to extend.\n'
            'export const keyed = %s;\n\nexport const byEn = %s;\n'
            % (code, language, code,
               json.dumps(keyed, ensure_ascii=False, indent=2),
               json.dumps({k: bt.get(k, k) for k in by_en}, ensure_ascii=False, indent=2)))
    out = os.path.join(LOCALES, "%s.js" % code)
    if dry:
        print("    [dry-run] would write %s (%d keyed + %d by-English)"
              % (out, len(keyed), len(by_en)))
        return
    open(out, "w", encoding="utf-8").write(body)
    print("    wrote %s (%d keyed + %d by-English)" % (out, len(keyed), len(by_en)))
    _register_web_locale(code, language, dry)


def _register_web_locale(code, language, dry):
    """Wire the new locale into i18n.jsx and legal.jsx so the toggle actually offers it."""
    p = os.path.join(FE, "src", "i18n.jsx")
    s = open(p, encoding="utf-8").read()
    up = code.upper()
    if 'locales/%s.js' % code not in s:
        s = s.replace('import * as PL from "./locales/pl.js";',
                      'import * as PL from "./locales/pl.js";\nimport * as %s from "./locales/%s.js";' % (up, code))
        s = re.sub(r"const LOCALES = \{([^}]*)\}",
                   lambda m: "const LOCALES = {%s, %s: %s }" % (m.group(1).rstrip().rstrip(","), code, up),
                   s, count=1)
        if not dry:
            open(p, "w", encoding="utf-8").write(s)
        print("    registered %s in i18n.jsx" % code)
    p2 = os.path.join(FE, "src", "legal.jsx")
    s2 = open(p2, encoding="utf-8").read()
    if '"%s"' % code not in s2.split("const CODES", 1)[0]:
        s2 = s2.replace('  { code: "pl", label: "Polski",   short: "PL" },',
                        '  { code: "pl", label: "Polski",   short: "PL" },\n'
                        '  { code: "%s", label: "%s", short: "%s" },' % (code, language, up))
        if not dry:
            open(p2, "w", encoding="utf-8").write(s2)
        print("    added %s to the LANGS toggle in legal.jsx" % code)


# ------------------------------------------------------------------ surface 4 + 5
def do_geopol(E, code, language, model, dry):
    ref = os.path.join(GEO, "ru.json")
    if not os.path.exists(ref):
        print("    no reference pack at %s — skipping the animated report" % ref)
        return
    r = json.load(open(ref, encoding="utf-8"))
    pack = {"_comment": "%s pack for the animated GEOPOL report. Generated by add_language.py." % language,
            "locale": "%s-%s" % (code, code.upper()),
            "untranslated": r.get("untranslated", [])}
    for sect in ("strings", "canvas", "fallback"):
        keys = list(r.get(sect, {}).keys())
        if not keys:
            continue
        extra = ("8d. These are canvas labels drawn into a fixed-size diagram — keep them SHORT and "
                 "in the same case.\n" if sect == "canvas" else "")
        pack[sect] = _translate_all(E, keys, language, code,
                                    "an animated scrollytelling HTML report (%s)" % sect,
                                    extra=extra, model=model)
    out = os.path.join(GEO, "%s.json" % code)
    if dry:
        print("    [dry-run] would write %s" % out)
        return
    os.makedirs(GEO, exist_ok=True)
    json.dump(pack, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("    wrote %s" % out)


def do_compliance(E, code, language, model, dry):
    p = os.path.join(ENGINE, "build_compliance_deck.js")
    s = open(p, encoding="utf-8").read()
    if re.search(r"\b%s:\s*\"" % code, s.split("const LABELS", 1)[-1][:6000]):
        print("    build_compliance_deck.js already carries %s labels" % code)
        return
    en = dict(re.findall(r"(\w+):\s*\{\s*en:\s*\"((?:[^\"\\]|\\.)*)\"", s))
    tr = _translate_all(E, sorted(set(en.values())), language, code,
                        "compliance slide labels and table headers", batch=30, model=model)
    if dry:
        print("    [dry-run] would add %d %s labels" % (len(en), code))
        return
    def add(m):
        key, val = m.group(1), m.group(2)
        t = tr.get(val)
        return m.group(0) if not t else m.group(0) + ', %s: %s' % (code, json.dumps(t, ensure_ascii=False))
    # Append the new code to each entry, immediately after its LAST existing translation.
    s2 = re.sub(r"(\w+):\s*\{\s*en:\s*\"((?:[^\"\\]|\\.)*)\"((?:,\s*\w+:\s*\"(?:[^\"\\]|\\.)*\")*)",
                lambda m: m.group(0) + (', %s: %s' % (code, json.dumps(tr[m.group(2)], ensure_ascii=False))
                                        if m.group(2) in tr else ""), s, count=0)
    open(p, "w", encoding="utf-8").write(s2)
    print("    added %s labels to build_compliance_deck.js" % code)


# ------------------------------------------------------------------ verification
def verify(code):
    """Run the gates that already exist. A language nobody verified is a language nobody has."""
    ok = True
    print("\n  VERIFY")
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "deck_langs.py")],
                       capture_output=True, text=True)
    offered = json.loads(r.stdout or "{}").get("doc_langs", []) if r.returncode == 0 else []
    print("    engine offers: %s" % offered)
    if code not in offered:
        print("    !! %s is NOT offered — the chrome dictionary or the enrich prose block is missing" % code)
        ok = False
    for cmd, label in (
        (["node", "tools/api_contract.mjs"], "api contract"),
        (["node", "tools/i18n_catalogue.mjs", "--check"], "web catalogue 100%"),
    ):
        rc = subprocess.run(cmd, cwd=FE, capture_output=True, text=True)
        print("    %-22s %s" % (label, "OK" if rc.returncode == 0 else "FAILED"))
        if rc.returncode != 0:
            ok = False
            print((rc.stdout or "")[-600:])
    print("\n  %s" % ("ALL GATES PASSED" if ok else "INCOMPLETE — see above; rerun to fill the gaps"))
    return ok


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Add a complete language using the product's own AI.")
    ap.add_argument("code", help="2-letter language code, e.g. pt")
    ap.add_argument("--name", help='endonym, e.g. "Português" (defaults to the code)')
    ap.add_argument("--only", choices=["decks", "prose", "web", "geopol", "compliance"], nargs="*",
                    help="limit to these surfaces (default: all five)")
    ap.add_argument("--model", help="override the model (default: the enrich.py chain head)")
    ap.add_argument("--dry-run", action="store_true", help="translate and report, write nothing")
    ap.add_argument("--verify-only", action="store_true", help="just run the gates")
    a = ap.parse_args()

    code = a.code.strip().lower()[:2]
    language = a.name or code.upper()
    if a.verify_only:
        sys.exit(0 if verify(code) else 1)

    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("[X] no OPENAI_API_KEY. It lives in assess-bot/.env (gitignored). Either put it "
                 "there, or run this on the droplet:\n"
                 "    docker exec colt-web python3 /opt/shodan-skill/scripts/... ")
    E = _enrich()
    model = a.model or E._chain()[0]
    print("=" * 74)
    print("  add_language.py — %s (%s) via %s%s" % (language, code, model, "  [DRY RUN]" if a.dry_run else ""))
    print("=" * 74)

    want = set(a.only or ["decks", "prose", "web", "geopol", "compliance"])
    steps = [("decks", do_decks), ("prose", do_prose), ("web", do_web),
             ("geopol", do_geopol), ("compliance", do_compliance)]
    for name, fn in steps:
        if name not in want:
            continue
        print("\n  %s" % name.upper())
        try:
            fn(E, code, language, model, a.dry_run)
        except Exception as e:
            print("    [X] %s failed: %r" % (name, e))
            print("        progress is cached — rerun to continue")

    if a.dry_run:
        print("\n  dry run: nothing written. Cache kept in %s" % os.path.join(CACHE, code))
        return
    verify(code)
    print("\n  Now run:  python ship.py")


if __name__ == "__main__":
    main()
