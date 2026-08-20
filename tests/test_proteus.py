"""proteus.py — White Label theme extraction, the judgement panel, and the three rails.

This is code that decides what a customer-facing document LOOKS like, so the tests assert measured
properties (contrast ratios, luminance ordering, what a refused file does) rather than the presence
of strings. A test that greps for a variable name would pass against a version that ships white text
on a pale gold background in every deck we produce for that partner.

The .pptx fixture is BUILT IN MEMORY rather than committed as a binary: a checked-in sample drifts
away from what the parser expects and nobody notices, and a zip we construct here states exactly
which XML shapes are under test (sysClr with @lastClr, a logo on the slide master, a decoy image on
one slide only).
"""
import io
import os
import struct
import sys
import zipfile
import zlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import proteus as P                                                    # noqa: E402


# --------------------------------------------------------------------------------- fixtures
def png(w, h, rgb=(30, 78, 121)):
    """A real, decodable PNG of the requested size. Small enough to build inline."""
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


THEME_XML = """<?xml version="1.0"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Acme">
 <a:themeElements>
  <a:clrScheme name="Acme">
   <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
   <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
   <a:dk2><a:srgbClr val="1F3864"/></a:dk2>
   <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
   <a:accent1><a:srgbClr val="C8102E"/></a:accent1>
   <a:accent2><a:srgbClr val="7A8B99"/></a:accent2>
   <a:accent3><a:srgbClr val="00843D"/></a:accent3>
   <a:accent4><a:srgbClr val="FFB81C"/></a:accent4>
   <a:accent5><a:srgbClr val="41B6E6"/></a:accent5>
   <a:accent6><a:srgbClr val="6C1D45"/></a:accent6>
   <a:hlink><a:srgbClr val="0563C1"/></a:hlink>
   <a:folHlink><a:srgbClr val="954F72"/></a:folHlink>
  </a:clrScheme>
  <a:fontScheme name="Acme">
   <a:majorFont><a:latin typeface="Gill Sans MT"/></a:majorFont>
   <a:minorFont><a:latin typeface="Verdana"/></a:minorFont>
  </a:fontScheme>
 </a:themeElements>
</a:theme>"""

RELS = ('<?xml version="1.0"?><Relationships '
        'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>')
REL = '<Relationship Id="rId%d" Type="http://x/image" Target="%s"/>'


def make_pptx(company="Acme Security GmbH", title="Q3 review", author="PptxGenJS",
              theme=THEME_XML, with_logo=True):
    """A minimal but structurally real Office package.

    The logo is referenced from the slide MASTER (which is what makes it a logo: it appears on
    every slide) and a larger decoy photo only from slide1, so the ranking has something to get
    right rather than a single candidate it cannot get wrong.
    """
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        z.writestr("ppt/presentation.xml",
                   '<?xml version="1.0"?><p:presentation '
                   'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                   'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                   '<a:sldSz cx="12192000" cy="6858000"/></p:presentation>')
        z.writestr("ppt/theme/theme1.xml", theme)
        z.writestr("ppt/slides/slide1.xml", "<x/>")
        z.writestr("docProps/app.xml",
                   '<?xml version="1.0"?><Properties '
                   'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
                   '<Company>%s</Company></Properties>' % company)
        z.writestr("docProps/core.xml",
                   '<?xml version="1.0"?><cp:coreProperties '
                   'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                   'xmlns:dc="http://purl.org/dc/elements/1.1/">'
                   '<dc:title>%s</dc:title><dc:creator>%s</dc:creator>'
                   '</cp:coreProperties>' % (title, author))
        if with_logo:
            z.writestr("ppt/media/image1.png", png(240, 60))          # wide -> a logo
            z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels",
                       RELS % (REL % (1, "../media/image1.png")))
            z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels",
                       RELS % (REL % (1, "../media/image1.png")))
        z.writestr("ppt/media/image2.png", png(1200, 800, (10, 20, 30)))   # a photo on one slide
        z.writestr("ppt/slides/_rels/slide1.xml.rels", RELS % (REL % (2, "../media/image2.png")))
    return b.getvalue()


# --------------------------------------------------------------------------------- colour maths
def test_luminance_and_contrast_against_the_wcag_reference_values():
    assert P.contrast("FFFFFF", "000000") == pytest.approx(21.0, abs=0.01)
    assert P.contrast("FFFFFF", "FFFFFF") == pytest.approx(1.0, abs=0.001)
    assert P.luminance("000000") == pytest.approx(0.0, abs=1e-9)
    assert P.luminance("FFFFFF") == pytest.approx(1.0, abs=1e-9)
    assert P.contrast("777777", "FFFFFF") == pytest.approx(4.48, abs=0.05)


@pytest.mark.parametrize("brand", [
    "00D7BD",   # our own accent
    "1F4E79",   # a corporate navy: DARK, the case that inverts naive theming
    "DA291C",   # a vendor red
    "F2C75C",   # pale gold: white text on it is unreadable
    "111827",   # near black
    "FFFFFF",   # pathological
    "000000",   # pathological
    "A4D65E",   # lime
])
def test_the_ramp_is_ordered_and_every_stop_carries_readable_text(brand):
    """THE RAIL THAT KEEPS THE LAYOUTS WORKING. `brandLight` carries DARK text and `brandDark`
    carries LIGHT text in the existing builders. If a partner's navy landed on the light stop, every
    slide would put dark text on a dark fill at once."""
    r = P.ramp(brand)
    ll, lm, ld = (P.luminance(r[k]) for k in ("light", "mid", "dark"))
    assert ll >= lm >= ld, "ramp not ordered light->mid->dark for %s: %s" % (brand, r)
    for stop in ("light", "dark"):
        ink = P.ink_for(r[stop])
        assert P.contrast(r[stop], ink) >= 4.5, (
            "%s stop %s carries no readable ink (best %.2f:1)"
            % (brand, r[stop], P.contrast(r[stop], ink)))


def test_the_ink_is_measured_not_assumed():
    """White on a pale gold is 1.8:1. Anything that hardcodes white on the brand colour ships an
    unreadable deck for every partner whose brand is light."""
    assert P.ink_for("F2C75C") == "1A1A1A"
    assert P.ink_for("1F3864") == "FFFFFF"


# --------------------------------------------------------------------------------- extraction
def test_extract_reads_the_colours_fonts_and_ranks_the_logo():
    f = P.extract(make_pptx())
    assert f["colors"]["accent1"] == "C8102E"
    assert f["colors"]["dk1"] == "000000", "sysClr @lastClr is where the real value lives"
    assert f["colors"]["lt1"] == "FFFFFF"
    assert f["fonts"] == {"major": "Gill Sans MT", "minor": "Verdana"}
    assert f["company"] == "Acme Security GmbH"
    top = f["media"][0]
    assert top["name"] == "ppt/media/image1.png", "the image on the MASTER is the logo"
    assert top["on_master"] and top["w"] == 240 and top["h"] == 60


def test_a_rendering_library_is_not_a_company_name():
    """MEASURED ON REAL FILES: two templates reported their author as 'PptxGenJS' and 'Steve Canny'
    (the author of python-pptx). Either would have gone on a partner's title slide."""
    f = P.extract(make_pptx(company="", author="Steve Canny", title="Q3 review"))
    t = P.build_theme(f, P._heuristic(f))
    assert t["name"] == "", "a tool name reached the wordmark"
    assert any("does not say which company" in w for w in t["warnings"])
    assert P._clean_name("PptxGenJS") == "" and P._clean_name("Microsoft Office User") == ""
    assert P._clean_name("Acme Security GmbH") == "Acme Security GmbH"


def test_the_deck_title_is_not_the_company_name():
    """dc:title produced the wordmark 'Why Redevco Needs Breach & Attack Simula[tion]'."""
    f = P.extract(make_pptx(company="", author="", title="Why Redevco Needs BAS"))
    assert P.build_theme(f, P._heuristic(f))["name"] == ""


def test_a_stock_office_palette_is_reported_rather_than_themed_confidently():
    stock = THEME_XML.replace("C8102E", "4472C4").replace("7A8B99", "ED7D31") \
                     .replace("00843D", "A5A5A5").replace("FFB81C", "FFC000") \
                     .replace("41B6E6", "5B9BD5").replace("6C1D45", "70AD47")
    f = P.extract(make_pptx(theme=stock))
    assert P.is_stock_palette(f["colors"]) is True
    assert any("default Office colour scheme" in w for w in P.build_theme(f, P._heuristic(f))["warnings"])
    assert P.is_stock_palette(P.extract(make_pptx())["colors"]) is False


def test_a_file_that_is_not_a_presentation_is_refused():
    for blob in (b"not a zip at all", png(64, 64)):
        with pytest.raises(ValueError):
            P.extract(blob)
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("word/document.xml", "<x/>")
    with pytest.raises(ValueError):
        P.extract(z.getvalue())


def test_media_extraction_refuses_a_traversal_name():
    data = make_pptx()
    assert P.read_media(data, "ppt/media/image1.png")[:4] == b"\x89PNG"
    for bad in ("../../etc/passwd", "ppt/media/../../../etc/passwd", "ppt/slides/slide1.xml", ""):
        with pytest.raises(ValueError):
            P.read_media(data, bad)


# --------------------------------------------------------------------------------- logo safety
def test_logo_validation_fails_closed():
    ok, why, meta = P.logo_ok(png(240, 60))
    assert ok and meta["kind"] == "png" and meta["w"] == 240

    bad, why, _ = P.logo_ok(b'<?xml version="1.0"?><svg onload="alert(1)"><script/></svg>')
    assert not bad and "SVG" in why, "an SVG logo is inlined into the HTML report"
    assert not P.logo_ok(b'  <svg xmlns="http://www.w3.org/2000/svg"/>')[0]

    assert not P.logo_ok(b"MZ\x90\x00this is a windows executable")[0]
    assert not P.logo_ok(b"")[0]
    assert not P.logo_ok(png(8, 8))[0], "8x8 is a bullet glyph, not a logo"
    assert not P.logo_ok(b"\x89PNG\r\n\x1a\n" + b"\x00" * 4 + b"IHDR"
                         + struct.pack(">II", 30000, 30000))[0], "declared 30000px is a bomb"


def test_jpeg_and_gif_headers_are_read_not_guessed_from_the_extension():
    # The APP0 length (0x0010) COUNTS ITSELF, so the segment spans bytes 4..19 and the SOF marker
    # begins at 20. My first fixture put it at 18 and failed a parser that was correct — a fixture
    # that does not model the format is a test of the fixture.
    jpg = (b"\xff\xd8\xff\xe0" + b"\x00\x10" + b"JFIF\x00" + b"\x00" * 9
           + b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", 100, 300) + b"\x03" + b"\x00" * 9)
    assert P.image_info(jpg) == ("jpeg", 300, 100)
    gif = b"GIF89a" + struct.pack("<HH", 200, 50) + b"\x00" * 10
    assert P.image_info(gif) == ("gif", 200, 50)


# --------------------------------------------------------------------------------- the panel
def _vote(brand, logo="ppt/media/image1.png", mode="light", name="Acme Security GmbH"):
    return {"brand": brand, "secondary": "7A8B99", "mode": mode, "logo": logo,
            "name": name, "why": "the red is the company's colour"}


def test_the_panel_decides_by_quorum_not_by_the_first_answer():
    f = P.extract(make_pptx())
    answers = {"deepseek-3.2": _vote("C8102E"), "llama-4-maverick": _vote("C8102E"),
               "gemma-4-31B-it": _vote("00843D"), "kimi-k2.6": _vote("C8102E")}
    j = P.judge(f, ask=lambda m, p: answers[m])
    assert j["brand"] == "C8102E"
    assert "3/4" in j["decided_by"]


def test_a_model_that_invents_a_colour_has_its_vote_discarded():
    """The colours are IN the file. A value that is not one of them is an answer to a different
    question, and adopting it would put a hallucinated shade on a partner's reports."""
    f = P.extract(make_pptx())
    answers = {"deepseek-3.2": _vote("FF00FF"), "llama-4-maverick": _vote("C8102E"),
               "gemma-4-31B-it": _vote("C8102E"), "kimi-k2.6": _vote("123456")}
    j = P.judge(f, ask=lambda m, p: answers[m])
    assert j["brand"] == "C8102E"
    assert sum(1 for v in j["votes"] if not v.get("ok")) == 2


def test_the_panel_being_unreachable_never_fails_an_upload():
    """A 429 on an inference account must not stop a partner uploading their template."""
    def boom(model, prompt):
        raise RuntimeError("429 rate limited")

    f = P.extract(make_pptx())
    j = P.judge(f, ask=boom)
    assert j["brand"] == "C8102E", "the heuristic picks accent1 by Office convention"
    assert "heuristic" in j["decided_by"]
    assert P.build_theme(f, j)["palette"]["brandDark"]


def test_one_model_alone_cannot_decide_the_brand():
    """Below a quorum we fall back to the heuristic rather than letting a single opinion become a
    partner's brand. The panel is a signal, not an authority."""
    def one(model, prompt):
        if model != "kimi-k2.6":
            raise RuntimeError("no answer")
        return _vote("6C1D45")

    j = P.judge(P.extract(make_pptx()), ask=one)
    assert "heuristic" in j["decided_by"] and j["brand"] != "6C1D45"


def test_a_tie_is_broken_deterministically():
    """Two runs over one file must not produce two different brands."""
    f = P.extract(make_pptx())
    answers = {"deepseek-3.2": _vote("C8102E"), "llama-4-maverick": _vote("C8102E"),
               "gemma-4-31B-it": _vote("00843D"), "kimi-k2.6": _vote("00843D")}
    first = P.judge(f, ask=lambda m, p: answers[m])["brand"]
    for _ in range(5):
        assert P.judge(f, ask=lambda m, p: answers[m])["brand"] == first


# --------------------------------------------------------------------------------- the rails
def test_severity_colours_are_never_part_of_a_theme():
    """crit/high/med/low are ENUMS read by the builders for grouping and by every reader as
    meaning. A partner whose brand is red does not get green criticals. Same doctrine as the i18n
    rule about severity keys, which made findings silently vanish when it was broken."""
    t = P.build_theme(P.extract(make_pptx()), P._heuristic(P.extract(make_pptx())))
    assert not (set(t["palette"]) & {"crit", "high", "med", "low"})
    t["palette"]["crit"] = "00FF00"
    assert any("semantic enum" in b for b in P.verify(t))


def test_verify_catches_a_hand_edited_theme():
    good = P.build_theme(P.extract(make_pptx()), P._heuristic(P.extract(make_pptx())))
    assert P.verify(good) == []

    inverted = dict(good, palette=dict(good["palette"], brandLight="0C544E", brandDark="00D7BD"))
    assert any("not ordered" in b for b in P.verify(inverted))

    unreadable = dict(good, palette=dict(good["palette"], brandDark="F2C75C", onBrandDark="FFFFFF"))
    assert any("unreadable" in b for b in P.verify(unreadable))

    assert any("not a colour" in b for b in P.verify(dict(good, palette={"brandLight": "zzz"})))
    assert P.verify({}) and P.verify(None)


def test_the_powered_by_line_is_present_by_default():
    t = P.build_theme(P.extract(make_pptx()), P._heuristic(P.extract(make_pptx())))
    assert "cybergod" in t["powered_by"].lower()
