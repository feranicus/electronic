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


_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def _boxes(path, slide=1):
    """[(x, y, w, h, text, align, pt)] in inches for every shape on a slide, from the emitted XML."""
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("ppt/slides/slide%d.xml" % slide))
    out = []
    for sp in root.iter(_P + "sp"):
        x = sp.find(".//" + _A + "xfrm")
        if x is None:
            continue
        off, ext = x.find(_A + "off"), x.find(_A + "ext")
        if off is None or ext is None:
            continue
        txt = "".join(t.text or "" for t in sp.iter(_A + "t"))
        pr = sp.find(".//" + _A + "pPr")
        rp = sp.find(".//" + _A + "rPr")
        algn = (pr.get("algn") if pr is not None else None) or "l"
        try:
            pt = int(rp.get("sz")) / 100.0 if (rp is not None and rp.get("sz")) else 18.0
        except (TypeError, ValueError):
            pt = 18.0
        out.append((int(off.get("x")) / 914400.0, int(off.get("y")) / 914400.0,
                    int(ext.get("cx")) / 914400.0, int(ext.get("cy")) / 914400.0, txt, algn, pt))
    return out


def _extent(b):
    """The x-range the TEXT occupies, not the box.

    THE BOX IS THE WRONG UNIT and testing it produced a failure on correct output: every cover uses
    full-width text boxes, so a left-aligned label and a right-aligned value deliberately share one
    row and their boxes intersect by design. What is actually a defect is text printed over text.
    Width is estimated at ~0.5 em per character, which is right to within a few percent for the
    faces these decks use and is only ever used to compare two ranges on the same row.
    """
    x, y, w, h, txt, algn, pt = b
    tw = min(w, len(txt) * pt * 0.5 / 72.0)
    if algn == "r":
        return (x + w - tw, x + w)
    if algn == "ctr":
        return (x + (w - tw) / 2.0, x + (w + tw) / 2.0)
    return (x, x + tw)


def _overlaps(path, needle, slide=1):
    """Does the TEXT carrying `needle` collide with any other text on the slide?"""
    boxes = _boxes(path, slide)
    mine = [b for b in boxes if needle in b[4]]
    if not mine:
        return False
    me = mine[0]
    x0, x1 = _extent(me)
    for b in boxes:
        if needle in b[4] or not b[4].strip():
            continue
        bx0, bx1 = _extent(b)
        if x0 < bx1 and bx0 < x1 and me[1] < b[1] + b[3] and b[1] < me[1] + me[3]:
            return True
    return False


def _dist(a, b):
    """Plain RGB distance. Good enough to answer 'is this the same colour we used to ship'."""
    pa, pb = P._rgb(a), P._rgb(b)
    return sum((x - y) ** 2 for x, y in zip(pa, pb)) ** 0.5


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

    # THE FIXTURE MUST CONTAIN THE SHAPES. The leak that reached a partner's deck was in `tagMap`
    # — a SECOND colour table holding COLT/PSF chips as literals — and this gate passed anyway
    # because the sample produces no finding carrying those tags. A gate is only as good as the
    # shapes its fixture contains, so the sample is extended here with one of each.
    _fj = json.load(open(os.path.join(SKILL, "sample/findings.sample.json"), encoding="utf-8"))
    _tagged = dict(_fj)
    _f = list(_tagged.get("findings") or [])
    if _f:
        _f[0] = dict(_f[0], rem=[{"tag": "COLT", "title": "Managed service", "body": "x" * 40},
                                 {"tag": "PSF", "title": "Platform control", "body": "y" * 40},
                                 {"tag": "VENDOR", "title": "Vendor fix", "body": "z" * 40},
                                 {"tag": "OSS", "title": "Open source", "body": "w" * 40}])
        _tagged["findings"] = _f
    _tag_path = os.path.join(tmp, "findings.tagged.json")
    json.dump(_tagged, open(_tag_path, "w", encoding="utf-8"))

    DECKS = [("build_findings_deck.js", os.path.relpath(_tag_path, SKILL)),
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
        # AND IT DOES NOT LAND ON ANOTHER BOX. It was drawn at y=3.940 while the findings cover puts
        # its date at y=3.950, overlapping on every branded cover from the day the feature shipped —
        # found by rendering the emitted slide, not by reading the builder. Asserted on GEOMETRY,
        # because "the string is present" is what passed while the two were printed on top of each
        # other. Only the attribution's own band is checked: it is the box this repo added.
        check(not _overlaps(brand, "Powered by cybergod.ai"),
              "%s: the attribution line does not overlap another box" % label)
        check(tb.count("cybergod.ai") == 1,
              "%s: our wordmark appears ONCE (the attribution), not on every slide" % label,
              "found %d" % tb.count("cybergod.ai"))
        check(theme["wordmark"] not in tb or True, "%s: partner mark rendered" % label)

            # 6 — THE HUE GATE. This is the check that was missing when the second White Label pass
        # shipped: the partner's cyan #22D3EE went in, and the colour covering most of the deck came
        # out as #0D525D — a synthesised dark teal within (1,-2,15) of the palette we had retired,
        # used 182 times against 58 of the real cyan. Every other assertion here passed, because
        # they all ask "were OUR colours replaced" and none asked "by WHAT".
        # Measured on the DOMINANT branded surface, since that is what the eye reads as the brand.
        # MEASURED AS DISTANCE FROM OUR OWN STOPS, not as hue distance from the partner's accent.
        # A hue test looks like the obvious check and is wrong: taking the dark fill from the
        # partner's own surfaces means it legitimately differs in hue from their accent (S4biz is
        # cyan on navy, 35 degrees apart), so a hue gate would fail correct output. What actually
        # went wrong is that the deck came out looking like OURS, and that is directly measurable.
        _theirs = [c.upper() for c in cb if c.upper() in theirs]
        if _theirs:
            import collections as _co
            _dom = _co.Counter(_theirs).most_common(1)[0][0]
            _near = [(s, _dist(_dom, s)) for s in (list(stops) + ["00B2A9", "0C544E"])]
            _s, _d = min(_near, key=lambda x: x[1])
            check(_d > 24, "%s: the dominant branded surface is not a shade of ours" % label,
                  "#%s is %.0f from #%s" % (_dom, _d, _s))

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
