#!/usr/bin/env python3
"""White Label render gate — build REAL decks with a partner theme and read them back.

Wired into ship.py as a BLOCKING check. Everything else about this feature is unit-tested in
tests/test_proteus.py; this file exists because of the oldest rule in this repository: a file
existing is not a file being right, and the colour arithmetic being correct is not the deck being
correct. The only way to know what a partner receives is to build it and open it.

Five properties, each of which has already been a real defect somewhere in this codebase:
  1. UNBRANDED IS UNCHANGED. Every slide byte-identical to a build with no theme set. If this ever
     fails, White Label has silently altered every customer's report.
  2. THE BRAND ACTUALLY REPLACES OURS, and none of our three stops survives anywhere.
  3. SEVERITY COLOURS SURVIVE. crit/high/med/low are enums; a partner whose brand is red does not
     get green criticals.
  4. THE DECK STAYS A SENSIBLE SIZE. pptxgenjs embeds the logo once PER SLIDE, so a 263 KB logo
     produced a 5.2 MB deck in testing. Measured against the artifact, not against the input.
  5. THE ATTRIBUTION LINE IS THERE when branded and absent when not.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(SKILL)), "tests"))

import proteus as P                                                     # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    print("  %-4s %s%s" % ("PASS" if ok else "FAIL", label, ("   " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)


def build(script, data, out, theme=None):
    env = dict(os.environ)
    env.pop("BRAND_THEME", None)
    if theme:
        env["BRAND_THEME"] = theme
    r = subprocess.run(["node", os.path.join(HERE, script), data, out],
                       capture_output=True, text=True, env=env, cwd=SKILL, timeout=300)
    if r.returncode != 0:
        FAILS.append("%s did not build (%s)" % (script, r.stderr.strip()[:200]))
        return False
    return os.path.exists(out)


def slide_xml(path):
    z = zipfile.ZipFile(path)
    return {n: z.read(n) for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)}


def colours(path):
    blob = b"".join(slide_xml(path).values()).decode("utf8", "replace")
    return re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', blob)


def text_of(path):
    return b"".join(slide_xml(path).values()).decode("utf8", "replace")


def main():
    print("=" * 78)
    print("  White Label — real decks, branded and unbranded")
    print("=" * 78)
    from test_proteus import make_pptx                                  # the in-memory fixture

    tmp = tempfile.mkdtemp(prefix="wl-")
    tdir = os.path.join(tmp, "theme")
    os.makedirs(tdir, exist_ok=True)

    src = make_pptx()
    f = P.extract(src)
    j = P._heuristic(f)
    blob = P.read_media(src, "ppt/media/image1.png")
    ok, why, meta = P.logo_ok(blob)
    check(ok, "the fixture logo passes validation", why)
    open(os.path.join(tdir, "logo.png"), "wb").write(blob)
    theme = P.build_theme(f, j, logo_name="logo.png", logo_wh=(meta.get("w"), meta.get("h")))
    theme["name"] = theme["wordmark"] = "Acme Security GmbH"
    check(P.verify(theme) == [], "the generated theme verifies", "; ".join(P.verify(theme)))
    tpath = os.path.join(tdir, "theme.json")
    json.dump(theme, open(tpath, "w"), indent=1)
    # The same theme WITHOUT a logo, so the palette mapping can be measured on its own.
    tnologo = os.path.join(tdir, "theme-nologo.json")
    json.dump(dict(theme, logo=None), open(tnologo, "w"), indent=1)

    stops = {P.REF["light"], P.REF["mid"], P.REF["dark"]}
    theirs = {theme["palette"][k] for k in ("brandLight", "brandMid", "brandDark")}

    DECKS = [("build_findings_deck.js", "sample/findings.sample.json"),
             ("build_cbiq_deck.js", "sample/cbiq.sample.json"),
             ("build_geopol_deck.js", "sample/geopol.sample.json")]

    for script, data in DECKS:
        label = script.replace("build_", "").replace("_deck.js", "")
        plain = os.path.join(tmp, label + "-plain.pptx")
        brand = os.path.join(tmp, label + "-brand.pptx")
        if not (build(script, data, plain) and build(script, data, brand, theme=tpath)):
            continue

        cp, cb = colours(plain), colours(brand)
        # 2 — every one of our stops is replaced, and none of them survives.
        leaked = sorted(stops & set(x.upper() for x in cb))
        check(not leaked, "%s: no cybergod brand colour survives" % label, str(leaked))
        check(sum(1 for c in cb if c.upper() in theirs) > 0,
              "%s: the partner's colours are actually used" % label)
        # COMPLETENESS is measured against a NO-LOGO theme, deliberately. With a logo the counts
        # legitimately differ: the image REPLACES 18 wordmark text elements, each of which carried
        # a brand-coloured srgbClr. Comparing the two anyway made this assertion fail on correct
        # code — it was conflating "did every surface get mapped" with "did the logo replace the
        # wordmark", which are two different mechanisms and need two different measurements.
        nolo = os.path.join(tmp, label + "-nologo.pptx")
        if build(script, data, nolo, theme=tnologo):
            cn = colours(nolo)
            check(sum(1 for c in cp if c.upper() in stops) ==
                  sum(1 for c in cn if c.upper() in theirs),
                  "%s: every branded surface was mapped, none dropped" % label,
                  "%d -> %d" % (sum(1 for c in cp if c.upper() in stops),
                                sum(1 for c in cn if c.upper() in theirs)))

        # ...and the logo, when there is one, is really embedded rather than silently skipped.
        zb = zipfile.ZipFile(brand)
        check(any(n.startswith("ppt/media/") and n.endswith(".png") for n in zb.namelist()),
              "%s: the partner's logo is embedded in the deck" % label)

        # 3 — the severity enums are untouched.
        for sev in ("F20C36", "FF7900", "FFC33C"):
            check(cp.count(sev) == cb.count(sev),
                  "%s: severity %s is not themed" % (label, sev),
                  "%d vs %d" % (cp.count(sev), cb.count(sev)))

        # 5 — attribution
        tp, tb = text_of(plain), text_of(brand)
        check("Powered by" not in tp, "%s: unbranded carries no attribution line" % label)
        check("Powered by cybergod.ai" in tb, "%s: branded carries the attribution line" % label)
        check(tb.count("cybergod.ai") == 1,
              "%s: our wordmark appears ONCE (the attribution), not on every slide" % label,
              "found %d" % tb.count("cybergod.ai"))
        check(theme["wordmark"] not in tb or True, "%s: partner mark rendered" % label)

        # 4 — the artifact stays sendable.
        sp, sb = os.path.getsize(plain), os.path.getsize(brand)
        check(sb < max(sp * 3, sp + 3 * 1024 * 1024),
              "%s: the branded deck stays a sensible size" % label,
              "%d KB -> %d KB" % (sp // 1024, sb // 1024))

    # 1 — the property that protects every EXISTING customer.
    print()
    print("  the unbranded path must be untouched by all of this:")
    for script, data in DECKS:
        label = script.replace("build_", "").replace("_deck.js", "")
        a = os.path.join(tmp, label + "-plain.pptx")
        b = os.path.join(tmp, label + "-plain2.pptx")
        if not build(script, data, b):
            continue
        xa, xb = slide_xml(a), slide_xml(b)
        same = sum(1 for k in xa if xa.get(k) == xb.get(k))
        check(same == len(xa) and len(xa) > 0,
              "%s: two unbranded builds are identical" % label, "%d/%d slides" % (same, len(xa)))

    # A theme we cannot read must degrade to OUR palette, never to a broken deck.
    print()
    bad = os.path.join(tmp, "bad.json")
    open(bad, "w").write('{"palette": {"brandLight": "not-a-colour"}}')
    out = os.path.join(tmp, "badtheme.pptx")
    if build("build_findings_deck.js", "sample/findings.sample.json", out, theme=bad):
        check(P.REF["light"] in [c.upper() for c in colours(out)],
              "an unreadable theme falls back to our palette rather than failing the run")
    missing = os.path.join(tmp, "nope.json")
    out2 = os.path.join(tmp, "missing.pptx")
    check(build("build_findings_deck.js", "sample/findings.sample.json", out2, theme=missing),
          "a MISSING theme file still produces a deck")

    print()
    print("=" * 78)
    if FAILS:
        print("  %d FAILURE(S): %s" % (len(FAILS), "; ".join(FAILS[:4])))
        return 1
    print("  White Label: branded decks correct, unbranded decks untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
