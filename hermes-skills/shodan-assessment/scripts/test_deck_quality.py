#!/usr/bin/env python3
"""
test_deck_quality.py — mechanical deck QA. Renders real decks and inspects the OOXML geometry.

WHY: "the deck looks terrible, all the letters are on top of each other, first page beyond terrible."
That was a 4,000-character scope string rendered into a 3.1-inch footer box. It shipped because deck
quality was only ever judged by a human opening the file. Every other property of this system has a
test; the customer-facing artifact did not.

WHAT IT CHECKS (all derived from real incidents)
  1. TEXT FITS ITS BOX   - estimate rendered characters against the shape's area at its font size.
                           Catches the 144-domain DATA SOURCE footer.
  2. NO OVERLAP          - text boxes in the same column must not intersect.
                           Catches the creed lines that overlapped by 0.01in.
  3. NO LEAKED PLACEHOLDERS - undefined / NaN / [object Object] / {{ }} never reach a customer.
  4. NO EMPTY DECK       - the findings index must list at least one finding per built deck.
  5. ENRICHMENT COVERAGE - if findings.json carries `_enriched` flags, assert the deck is not
                           mostly canned template prose.

    python test_deck_quality.py
"""
import glob, json, os, re, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "..", "sample")
EMU = 914400.0
FAILS = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


def shapes(pptx, slide_no):
    """[(text, x, y, w, h, font_pt)] for every text shape on the slide."""
    xml = zipfile.ZipFile(pptx).read("ppt/slides/slide%d.xml" % slide_no).decode("utf8")
    out = []
    for sp in re.findall(r"<p:sp>.*?</p:sp>", xml, re.S):
        m = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>\s*<a:ext cx="(\d+)" cy="(\d+)"/>', sp)
        if not m:
            continue
        x, y, w, h = [int(g) / EMU for g in m.groups()]
        txt = "".join(re.findall(r"<a:t>(.*?)</a:t>", sp, re.S))
        if not txt.strip():
            continue
        # a:rPr sz is in 100ths of a point; other attributes (spc/charSpacing) also match a bare
        # sz=, so take the smallest PLAUSIBLE value rather than the first thing that matches.
        sz = [int(v) / 100.0 for v in re.findall(r'<a:rPr[^>]*\bsz="(\d+)"', sp)]
        sz = [v for v in sz if 4.0 <= v <= 96.0]
        pt = min(sz) if sz else 12.0
        out.append((txt, x, y, w, h, pt))
    return out


def capacity(w_in, h_in, pt):
    """Rough characters a box can hold. ~0.5*pt wide per char, ~1.25*pt line height, 72pt/inch."""
    if pt <= 0:
        return 10 ** 6
    chars_per_line = max(1, int((w_in * 72.0) / (pt * 0.5)))
    lines = max(1, int((h_in * 72.0) / (pt * 1.25)))
    return chars_per_line * lines


def build(builder, args, out):
    r = subprocess.run(["node", os.path.join(HERE, builder)] + args + [out],
                       capture_output=True, text=True, timeout=180,
                       env={**os.environ, "DECK_LANG": os.environ.get("DECK_LANG", "en")})
    return os.path.exists(out), (r.stderr or "")[-300:]



def colt_regressions():
    """The COLT AS8220 run: numbers that disagreed between two slides of the SAME deck."""
    import json as _j
    print("\n== 6. the COLT run: cross-slide consistency + readable cells ==")
    tmp = tempfile.mkdtemp()
    fj = json.load(open(os.path.join(SAMPLE, "findings.sample.json"), encoding="utf-8"))
    # exactly the shape that broke: ONE inventory row holding 21 comma-joined country codes
    fj["summary"]["countries"] = 21
    fj["summary"]["inventory"] = [{"asn": "AS8220", "holder": "COLT Technology Services Group Limited",
                                   "country": "AT,AU,BE,CH,DE,DK,ES,FI,FR,GB,HK,IE,IT,JP,NL,PT,"
                                              "RO,SE,SG,SK,US", "hosts": 738}]
    p = os.path.join(tmp, "colt.json")
    _j.dump(fj, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    out = os.path.join(tmp, "colt.pptx")
    good, err = build("build_findings_deck.js", [p], out)
    check(good, "deck builds from an ASN-seeded, no-domain estate%s" % ("" if good else " " + err))
    if not good:
        return
    z = zipfile.ZipFile(out)
    s5 = z.read("ppt/slides/slide5.xml").decode("utf8")
    tiles = []
    for sp in re.findall(r"<p:sp>.*?</p:sp>", s5, re.S):
        m = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', sp)
        t = "".join(re.findall(r"<a:t>(.*?)</a:t>", sp, re.S)).strip()
        if m and t and 1.2 * EMU < int(m.group(2)) < 2.3 * EMU:
            tiles.append((int(m.group(1)), int(m.group(2)), t))
    col = {}
    for x, y, t in tiles:
        col.setdefault(round(x / EMU, 1), []).append((y, t))
    got = {}
    for k, v in col.items():
        vals = [t for _, t in sorted(v)]
        if len(vals) >= 2:
            got[vals[1]] = vals[0]
    check(got.get("COUNTRIES") == "21",
          "ASSET INVENTORY says %s countries, matching the exec summary's 21 (was 1: it counted "
          "distinct comma-joined STRINGS)" % got.get("COUNTRIES"))
    # the country CELL must stay readable in a ~1.1in column
    frame = re.findall(r"<p:graphicFrame>.*?</p:graphicFrame>", s5, re.S)
    if frame:
        row = re.findall(r"<a:tr .*?</a:tr>", frame[0], re.S)[1]
        cells = ["".join(re.findall(r"<a:t>(.*?)</a:t>", c, re.S))
                 for c in re.findall(r"<a:tc.*?</a:tc>", row, re.S)]
        cc = cells[2] if len(cells) > 2 else ""
        check(len(cc) <= 18 and "+" in cc,
              "country cell is summarised (%r), not 21 codes truncated mid-word" % cc)


def length_budgets():
    """The prose contract must fit the BOX, and every enrichment path must enforce it.

    bottomline.com was delivered with 46 text boxes ending in an ellipsis. Nothing was broken: the
    bible asked for three full sentences of `why` (~450 chars) into a 243-char box and 3-5
    remediation objects into rows that hold 148 chars at five rows. The contract and the box had
    simply never been compared.

    THE CAPACITY IS DERIVED FROM build_findings_deck.js, not retyped here, so moving a box fails
    this check instead of silently re-opening the defect.
    """
    print("\n  --- length budgets: the contract must fit the box -------------------------------")
    sys.path.insert(0, HERE)
    import enrich as E

    js = open(os.path.join(HERE, "build_findings_deck.js"), encoding="utf-8").read()

    def cap(w, h, pt):                       # fitText's own model: ~0.5*pt/char, ~1.25*pt/line
        return int(w * 72 / (0.5 * pt)) * int(h * 72 / (1.25 * pt))

    m = re.search(r"fitText\(asText\(f\.why\)[^,]*,\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\)", js)
    check(bool(m), "the why box is still readable from build_findings_deck.js")
    if m:
        box = cap(*(float(x) for x in m.groups()))
        check(E.BUDGET["why"] <= box,
              "why budget %d fits its %d-char box" % (E.BUDGET["why"], box))

    # REM_ROWS is the load-bearing number: rowH is adaptive, so asking for five rows is asking for
    # a third of the space per row. Assert the rows we request can hold the body we ask for.
    rh = min(1.05, (5.24 - 2.06) / max(1, E.REM_ROWS))
    body_box = cap(3.85, rh - 0.30, 7.4)
    check(E.BUDGET["rem_body"] <= body_box,
          "rem body budget %d fits its %d-char box at %d rows"
          % (E.BUDGET["rem_body"], body_box, E.REM_ROWS))
    check(E.BUDGET["rem_title"] <= cap(3.85, 0.24, 8.6),
          "rem title budget %d fits its box" % E.BUDGET["rem_title"])

    # THE BIBLE MUST STATE THE SAME NUMBERS. A budget the model is never told about is a budget it
    # cannot meet: it writes 450 characters, we delete 110, and the customer reads a fragment.
    bible = open(os.path.join(HERE, "..", "reference", "LLM_DELTAS_BIBLE.md"),
                 encoding="utf-8").read()
    for name, n in (("rem_title", E.BUDGET["rem_title"]), ("rem_body", E.BUDGET["rem_body"]),
                    ("why", E.BUDGET["why"])):
        check(str(n) in bible, "the bible states the %s budget (%d characters)" % (name, n))
    check(re.search(r"`rem` must be EXACTLY %d" % E.REM_ROWS, bible, re.I) is not None,
          "the bible asks for exactly %d remediation objects" % E.REM_ROWS)

    # BOTH PATHS ENFORCE IT. enrich_parallel.apply() used to copy the model's fields on verbatim,
    # and it is the path that runs whenever the monolithic call fails — i.e. the one that built the
    # deck this check exists for.
    over = {"why": ["S%d. " % i + "w" * 300 for i in range(3)],
            "rem": [{"tag": "MADEUP", "title": "N" * 200, "body": "b" * 900}] * 6}
    got = E.normalise_prose(over)
    check(len(got["rem"]) == E.REM_ROWS, "normalise_prose caps the rows the box can render")
    check(got["rem"][0]["tag"] == "COLT", "an invented remediation tag is coerced to a real one")
    check(all(len(r["title"]) <= E.BUDGET["rem_title"] and len(r["body"]) <= E.BUDGET["rem_body"]
              for r in got["rem"]), "every remediation field is inside its budget")
    check(len(" ".join(got["why"])) <= E.BUDGET["why"], "why is clamped on the JOINED budget")

    src = open(os.path.join(HERE, "enrich_parallel.py"), encoding="utf-8").read()
    body = src[src.index("def apply("):].split("\ndef ")[0]
    check("normalise_prose(" in body,
          "the shard path applies the same normalisation as the serial chain")

    # A SENTENCE THAT DOES NOT FIT IS DROPPED, NOT TRIMMED. Two complete thoughts read better than
    # two and a half, which is the entire reason for clamping here rather than letting fitText cut.
    two = E._clamp_list(["A" * 100 + ".", "B" * 100 + ".", "C" * 100 + "."], 230)
    check(all(s.endswith(".") and "…" not in s for s in two),
          "whole sentences only: an over-long one is dropped, never trimmed mid-thought")


def main():
    tmp = tempfile.mkdtemp()
    fj = json.load(open(os.path.join(SAMPLE, "findings.sample.json"), encoding="utf-8"))

    # Reproduce the EXACT regression: a whole corporate group's domain list in target.scope.
    fj.setdefault("target", {})
    fj["target"]["scope"] = ("ASN — · 0 prefixes · domains " +
                             ",".join("host%d.angermann-consult.de" % i for i in range(144)))
    big = os.path.join(tmp, "big.json")
    json.dump(fj, open(big, "w", encoding="utf-8"), ensure_ascii=False)

    print("== 1. text must FIT its shape (the 4,000-char footer regression) ==")
    out = os.path.join(tmp, "findings_big.pptx")
    ok, err = build("build_findings_deck.js", [big], out)
    check(ok, "findings deck renders with a pathological scope string%s" % ("" if ok else " " + err))
    if ok:
        worst, worst_ratio = None, 0.0
        for txt, x, y, w, h, pt in shapes(out, 1):
            cap = capacity(w, h, pt)
            ratio = len(txt) / float(cap)
            if ratio > worst_ratio:
                worst, worst_ratio = (txt[:44], len(txt), cap, w, h, pt), ratio
        if worst is None:
            worst = ("", 0, 0, 0.0, 0.0, 0.0)
        check(worst_ratio <= 1.6,
              "no title-slide text exceeds ~1.6x its box capacity "
              "(worst %.1fx: %r = %d chars, capacity ~%d, box %.1fx%.1fin @ %.0fpt)"
              % (worst_ratio, worst[0], worst[1], worst[2], worst[3], worst[4], worst[5]))

    print("\n== 2. text boxes in the same column must not OVERLAP ==")
    if ok:
        col = [(y, y + h, x, x + w, txt) for txt, x, y, w, h, pt in shapes(out, 1) if x < 5.0]
        bad = []
        for i, a in enumerate(sorted(col)):
            for b in sorted(col)[i + 1:]:
                if a[0] < b[1] - 0.005 and b[0] < a[1] - 0.005 and a[2] < b[3] and b[2] < a[3]:
                    bad.append((round(a[0], 2), round(b[0], 2)))
        check(not bad, "no overlapping text boxes in the left column%s"
              % ("" if not bad else " (%d pairs, e.g. y=%s vs y=%s)" % (len(bad), bad[0][0], bad[0][1])))

    print("\n== 2b. EVERY slide: text must fit, and nothing may run into the footer ==")
    # The title slide was the only slide checked, so the real overflow — `why` running through the
    # footer and remediation bodies running into the next row on the FINDING slides — sailed past.
    if ok:
        import zipfile as _zf
        n_sl = len([n for n in _zf.ZipFile(out).namelist()
                    if re.match(r"ppt/slides/slide\d+\.xml$", n)])
        worst_all, worst_sl, over_footer = 0.0, 0, []
        for sn in range(1, n_sl + 1):
            for txt, x, y, w, h, pt in shapes(out, sn):
                r = len(txt) / float(capacity(w, h, pt))
                if r > worst_all:
                    worst_all, worst_sl = r, sn
                # the confidentiality footer sits at y5.32; body text must stop above it
                if x < 5.0 and y < 5.30 and (y + h) > 5.36 and len(txt) > 60:
                    over_footer.append((sn, round(y + h, 2)))
        check(worst_all <= 1.6, "no text on ANY of the %d slides exceeds 1.6x its box "
                                "(worst %.1fx on slide %d)" % (n_sl, worst_all, worst_sl))
        check(not over_footer, "no body text runs into the confidentiality footer%s"
              % ("" if not over_footer else " (%d, e.g. slide %s ends at y%s)"
                 % (len(over_footer), over_footer[0][0], over_footer[0][1])))

    print("\n== 3. no leaked placeholders anywhere in any deck ==")
    decks = []
    for builder, args, name in (
            ("build_findings_deck.js", [os.path.join(SAMPLE, "findings.sample.json")], "findings"),
            ("build_cbiq_deck.js", [os.path.join(SAMPLE, "cbiq.sample.json")], "cbiq"),
            ("build_geopol_deck.js", [os.path.join(SAMPLE, "geopol.sample.json")], "geopol")):
        o = os.path.join(tmp, name + ".pptx")
        good, err = build(builder, args, o)
        check(good, "%s deck builds%s" % (name, "" if good else " " + err))
        if good:
            decks.append((name, o))
    BAD = ("undefined", "NaN", "[object Object]", "{{", "}}", "null null", "Infinity")
    for name, path in decks:
        z = zipfile.ZipFile(path)
        txt = " ".join("".join(re.findall(r"<a:t>(.*?)</a:t>", z.read(n).decode("utf8"), re.S))
                       for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))
        hit = [b for b in BAD if b in txt]
        check(not hit, "%s deck contains no placeholder leakage%s"
              % (name, "" if not hit else " (found %s)" % hit))

    print("\n== 4. the findings deck must not be empty ==")
    if decks:
        z = zipfile.ZipFile(decks[0][1])
        allt = " ".join("".join(re.findall(r"<a:t>(.*?)</a:t>", z.read(n).decode("utf8"), re.S))
                        for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))
        check(re.search(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b", allt) is not None,
              "at least one severity band is rendered")

    print("\n== 5. enrichment coverage must not be silently template-only ==")
    f2 = json.load(open(os.path.join(SAMPLE, "findings.sample.json"), encoding="utf-8"))
    fl = [x for x in (f2.get("findings") or []) if isinstance(x, dict)]
    if any("_enriched" in x for x in fl):
        cov = len([x for x in fl if x.get("_enriched")]) / float(len(fl))
        check(cov >= 0.8, "sample findings are >=80%% LLM-written (got %.0f%%)" % (cov * 100))
    else:
        print("  skip  sample has no _enriched flags (fixture predates the coverage contract)")

    colt_regressions()
    length_budgets()

    print("\n" + "=" * 78)
    print("  test_deck_quality: %s" % ("ALL PASSED" if not FAILS else "%d FAILURE(S)" % len(FAILS)))
    print("=" * 78)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
