#!/usr/bin/env python3
"""proteus.py — White Label: turn a partner's own PowerPoint into a theme for our artifacts.

Named for the god who takes any form while remaining the same substance, which is exactly the
contract: the findings, the arithmetic and the methodology are ours and unchanged; only the surface
becomes the partner's. Perseus Shield sits over shield.py the same way.

WHAT IS DETERMINISTIC AND WHAT IS JUDGEMENT — read this before adding a model anywhere.
-------------------------------------------------------------------------------------
A .pptx is a ZIP of XML. The partner's exact brand colours are already IN the file:
    ppt/theme/theme1.xml   <a:clrScheme>  dk1 lt1 dk2 lt2 accent1..6 hlink folHlink
                           <a:fontScheme> majorFont/minorFont -> <a:latin typeface="...">
    ppt/media/*            every image the deck ships, logo included
    docProps/core.xml      the company that authored it
Extracting those is exact, free and instant. Asking a model to GUESS hex codes off a deck would be
slower, cost money, hallucinate a shade, and give a different answer on every upload — the same
mistake as the phantom `deepseek-v4-flash` model id, one layer up. So there is NO model in extract().

The panel earns its place on the questions parsing cannot answer, and only those:
    * which of six accents is the BRAND colour and which are decoration
    * which file in ppt/media is the LOGO rather than a stock photo or an icon
    * is the house style light or dark
    * what should the wordmark say
`judge()` asks four vendors, takes a quorum, and falls back to a deterministic heuristic when the
endpoint is unavailable — an upload must never fail because an inference account hit its quota.

AND THREE RAILS NO MODEL GETS A VOTE ON (build_theme):
  1. CONTRAST. Every foreground/background pair we actually render is measured against WCAG 2.x.
     If a partner's brand is pale gold, white text on it is unreadable and EVERY deck we ship for
     them is unreadable. The ink flips to whichever of black/white passes; if neither does, the
     colour is refused as a background and kept as an accent only. Measured, never assumed.
  2. THE LUMINANCE RAMP, which is the part that is easy to get wrong. Our layouts do not use one
     brand colour, they use a triple — `teal` is a LIGHT accent that carries dark text and sits on
     dark fills, `tealDark` is a dark fill that carries light text. Swapping a partner's navy
     straight into `teal` would invert every one of those relationships at once. So the partner's
     brand is placed at the stop matching ITS OWN luminance and the other two stops are derived by
     tinting toward white / shading toward black to hit our reference luminances. Every existing
     contrast relationship then holds by construction, and rail 1 verifies it rather than hoping.
  3. SEVERITY COLOURS ARE ENUMS, NOT BRAND. crit/high/med/low are read by the builders for grouping
     and by every reader as meaning. A partner whose brand is red does not get green criticals.
     Same doctrine as "never translate ENUM/LOOKUP keys" — the i18n rule that made findings vanish.

Usage:
    python3 proteus.py extract <deck.pptx> [--logo logo.png] [--out theme.json] [--no-panel]
    python3 proteus.py show <theme.json>
"""
import base64
import hashlib
import json
import os
import re
import struct
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"

MAX_UPLOAD = int(os.environ.get("BRAND_MAX_UPLOAD", 25 * 1024 * 1024))   # 25 MB
# THE LOGO IS EMBEDDED ONCE PER SLIDE, NOT ONCE PER DECK. Measured: pptxgenjs writes a separate
# ppt/media entry for every addImage call, so an 18-slide deck carries 18 copies. A 263 KB logo
# turned a 498 KB deck into 5.2 MB. The first cap here was 4 MB, which would have produced a 72 MB
# artifact that no partner could email and no reader could open — and nothing would have said why.
# 150 KB is generous for a mark rendered ~2 inches wide (600 px at 300 DPI is ample).
MAX_LOGO_BYTES = int(os.environ.get("BRAND_MAX_LOGO", 150 * 1024))
MAX_LOGO_PX = 8000            # a declared dimension beyond this is a decompression bomb, not a logo
MIN_LOGO_PX = 24              # smaller than this is a bullet glyph or a spacer, not a logo

# Our own reference ramp. The three stops the builders use, and the luminances a partner's ramp is
# rebuilt to hit. Read from here rather than restated in brand.js: one home.
REF = {"light": "00D7BD", "mid": "00A49A", "dark": "0C544E"}

POWERED_BY = os.environ.get("BRAND_POWERED_BY", "Powered by cybergod.ai")

# WHO AUTHORED A FILE IS NOT WHO OWNS THE BRAND. Measured on real uploads: the first two templates
# tested reported `cp:lastModifiedBy` as "PptxGenJS" and "Steve Canny" — a rendering library and the
# author of python-pptx. Either would have gone onto a partner's title slide. Metadata is a
# SUGGESTION for the form, never a value we put in front of a customer unconfirmed.
_TOOL_AUTHORS = re.compile(
    r"^(pptxgenjs|python-pptx|steve canny|microsoft (office|powerpoint)( user)?|user|admin|"
    r"apache poi|libreoffice|openoffice|google|canva|slidesgo|windows user|autor|author)$", re.I)

# The stock Office palettes. A template still on one of these has no brand colour to find, which is
# a legitimate and common outcome for a deck somebody started from File > New. Saying so is far more
# useful than confidently theming a partner's reports in Microsoft's blue.
_OFFICE_DEFAULT_ACCENTS = {
    ("4472C4", "ED7D31", "A5A5A5", "FFC000", "5B9BD5", "70AD47"),   # Office 2013+
    ("4F81BD", "C0504D", "9BBB59", "8064A2", "4BACC6", "F79646"),   # Office 2007-2010
    ("5B9BD5", "ED7D31", "A5A5A5", "FFC000", "4472C4", "70AD47"),   # Office 2013 variant
}


def _clean_name(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if not s or _TOOL_AUTHORS.match(s) or len(s) < 2:
        return ""
    return s[:80]


def is_stock_palette(colors):
    accents = tuple((colors or {}).get("accent%d" % i, "") for i in range(1, 7))
    return accents in _OFFICE_DEFAULT_ACCENTS


def _ms(t0):
    return int((time.time() - t0) * 1000)


# --------------------------------------------------------------------------- colour arithmetic
def _hex(s):
    s = (s or "").strip().lstrip("#").upper()
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return s if re.fullmatch(r"[0-9A-F]{6}", s or "") else None


def _rgb(h):
    h = _hex(h) or "000000"
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def luminance(h):
    """WCAG 2.x relative luminance. The one number every rail here is built on."""
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def ink_for(bg, dark="1A1A1A", light="FFFFFF"):
    """The readable ink for this background, MEASURED. Never 'white on the brand colour'."""
    return dark if contrast(bg, dark) >= contrast(bg, light) else light


def _mix(h, target, t):
    r, g, b = _rgb(h)
    tr, tg, tb = _rgb(target)
    return "%02X%02X%02X" % (round(r + (tr - r) * t), round(g + (tg - g) * t), round(b + (tb - b) * t))


def _to_luminance(h, want, toward):
    """Tint/shade `h` toward `toward` until its luminance reaches `want`.

    Mixing moves every channel linearly toward the target, so luminance is MONOTONIC in the mix
    fraction — which is what makes a binary search correct here. A fixed step (`lighten by 20%`)
    is not: luminance is a 2.4-power curve, so the same step lands somewhere different depending
    on where you start, and that is how a "lighter" shade comes out darker than the one below it.
    Best-effort if the target is unreachable (already lighter than `want` while tinting to white),
    because clamping to the endpoint is still ordered correctly.
    """
    up = luminance(toward) > luminance(h)
    lo, hi = 0.0, 1.0
    best, bestd = _hex(h), abs(luminance(h) - want)
    for _ in range(20):
        mid = (lo + hi) / 2.0
        c = _mix(h, toward, mid)
        lc = luminance(c)
        d = abs(lc - want)
        if d < bestd:
            best, bestd = c, d
        if (lc < want) == up:      # still short of the target in the direction we are moving
            lo = mid
        else:
            hi = mid
    return best


def ramp(brand):
    """Place the partner's brand at the stop matching its own luminance and derive the other two.

    THIS IS THE FUNCTION THAT KEEPS THE LAYOUTS READABLE. `teal` in our builders is a light accent
    that carries DARK text; `tealDark` is a dark fill that carries LIGHT text. A partner's navy
    dropped into `teal` would put dark text on a dark fill on every slide at once.
    """
    want = {k: luminance(v) for k, v in REF.items()}
    lb = luminance(brand)
    # Which of our three stops is this colour closest to? That is where it belongs.
    slot = min(want, key=lambda k: abs(want[k] - lb))
    out = {slot: _hex(brand)}
    for k in ("light", "mid", "dark"):
        if k == slot:
            continue
        toward = "FFFFFF" if want[k] > lb else "000000"
        out[k] = _to_luminance(brand, want[k], toward)
    return out


# --------------------------------------------------------------------------- image sniffing
def image_info(blob):
    """(kind, width, height) from the HEADER only, or (None, 0, 0).

    NO Pillow, deliberately: adding an image-decoding library to accept an image is a large new
    attack surface for a small job, and every dependency here is one Trivy will report on forever.
    Reading the header answers the two questions that matter — is this really the image type it
    claims, and are its declared dimensions sane — WITHOUT decoding attacker-supplied pixels.
    SVG is refused outright by the caller: it is a script and XXE vector, and it would be inlined
    into the animated HTML artifacts.
    """
    try:
        if blob[:8] == b"\x89PNG\r\n\x1a\n" and blob[12:16] == b"IHDR":
            w, h = struct.unpack(">II", blob[16:24])
            return ("png", w, h)
        if blob[:3] == b"\xff\xd8\xff":
            i = 2
            while i + 9 < len(blob):
                if blob[i] != 0xFF:
                    i += 1
                    continue
                m = blob[i + 1]
                if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                    i += 2
                    continue
                seg = struct.unpack(">H", blob[i + 2:i + 4])[0]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB,
                         0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", blob[i + 5:i + 9])
                    return ("jpeg", w, h)
                i += 2 + seg
            return (None, 0, 0)
        if blob[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", blob[6:10])
            return ("gif", w, h)
        if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
            if blob[12:16] == b"VP8X":
                w = int.from_bytes(blob[24:27], "little") + 1
                h = int.from_bytes(blob[27:30], "little") + 1
                return ("webp", w, h)
            return ("webp", 0, 0)     # plain VP8/VP8L: accepted, dimensions unknown
    except Exception:
        pass
    return (None, 0, 0)


def logo_ok(blob):
    """(ok, reason, meta). Fails CLOSED: anything we cannot positively identify is refused."""
    if not blob:
        return (False, "empty file", {})
    if len(blob) > MAX_LOGO_BYTES:
        return (False, "larger than %d KB" % (MAX_LOGO_BYTES // 1024), {})
    head = blob[:400].lstrip()
    if head[:5].lower() == b"<?xml" or b"<svg" in head.lower():
        return (False, "SVG is not accepted: it can carry script and external entities, and the "
                       "logo is inlined into the HTML report. Export it as PNG.", {})
    kind, w, h = image_info(blob)
    if not kind:
        return (False, "not a PNG, JPEG, GIF or WebP image", {})
    if w > MAX_LOGO_PX or h > MAX_LOGO_PX:
        return (False, "declared size %dx%d is implausible for a logo" % (w, h), {})
    if kind != "webp" and (w < MIN_LOGO_PX or h < MIN_LOGO_PX):
        return (False, "only %dx%d — too small to be a logo" % (w, h), {})
    return (True, "", {"kind": kind, "w": w, "h": h, "bytes": len(blob)})


# --------------------------------------------------------------------------- extraction
def _clr(node):
    """A DrawingML colour slot. dk1/lt1 are usually sysClr, whose real value is @lastClr."""
    if node is None:
        return None
    s = node.find(A + "srgbClr")
    if s is not None:
        return _hex(s.get("val"))
    y = node.find(A + "sysClr")
    if y is not None:
        return _hex(y.get("lastClr")) or ("FFFFFF" if "window" == (y.get("val") or "") else None)
    return None


def extract(path_or_bytes):
    """Every fact the file states about itself. No judgement, no model, no network."""
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else \
        open(path_or_bytes, "rb").read()
    if len(data) > MAX_UPLOAD:
        raise ValueError("file is larger than %d MB" % (MAX_UPLOAD // (1024 * 1024)))
    import io
    try:
        z = zipfile.ZipFile(io.BytesIO(bytes(data)))
    except Exception:
        raise ValueError("not a .pptx/.potx file (it is not a valid Office package)")
    names = set(z.namelist())
    if not any(n.startswith("ppt/") for n in names):
        raise ValueError("this is not a PowerPoint file (no ppt/ part inside)")

    # ZIP BOMB GUARD. The upload cap is on the COMPRESSED file; a 25 MB zip can declare a 10 GB
    # member, and z.read() would happily try to allocate it. Office parts are small — a theme is a
    # few KB and the largest legitimate media is a photograph — so a declared total this far above
    # any real deck is an attack, not a template. Checked BEFORE any member is read.
    total = sum(i.file_size for i in z.infolist())
    if total > 500 * 1024 * 1024:
        raise ValueError("the file declares %d MB of content when uncompressed, which is not a "
                         "presentation" % (total // (1024 * 1024)))
    for i in z.infolist():
        if i.file_size > 80 * 1024 * 1024:
            raise ValueError("a part inside the file (%s) declares %d MB — refused"
                             % (i.filename[:60], i.file_size // (1024 * 1024)))

    out = {"colors": {}, "fonts": {}, "media": [], "company": "", "title": "",
           "sizes": {}, "sha256": hashlib.sha256(bytes(data)).hexdigest()[:16]}

    # ---- theme: colours + fonts
    themes = sorted(n for n in names if re.fullmatch(r"ppt/theme/theme\d+\.xml", n))
    if themes:
        try:
            root = ET.fromstring(z.read(themes[0]))
            cs = root.find(".//" + A + "clrScheme")
            if cs is not None:
                for slot in ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3",
                             "accent4", "accent5", "accent6", "hlink", "folHlink"):
                    v = _clr(cs.find(A + slot))
                    if v:
                        out["colors"][slot] = v
            fs = root.find(".//" + A + "fontScheme")
            if fs is not None:
                for which, key in (("majorFont", "major"), ("minorFont", "minor")):
                    n = fs.find(A + which)
                    lat = n.find(A + "latin") if n is not None else None
                    if lat is not None and lat.get("typeface"):
                        out["fonts"][key] = lat.get("typeface")
        except Exception as e:
            out.setdefault("warnings", []).append("theme unreadable: %r" % (e,))

    # ---- who authored it
    # `<Company>` in app.xml is the only field that MEANS the organisation. cp:lastModifiedBy and
    # dc:creator mean "whoever or whatever last saved it", which on the two real templates tested
    # here was "PptxGenJS" and "Steve Canny" (a rendering library, and the author of python-pptx).
    # Both are offered only as a SUGGESTION for the form; _clean_name drops the known tool names.
    if "docProps/app.xml" in names:
        try:
            app = ET.fromstring(z.read("docProps/app.xml"))
            for el in app.iter():
                if el.tag.endswith("}Company") and (el.text or "").strip():
                    out["company"] = _clean_name(el.text)
        except Exception:
            pass
    if "docProps/core.xml" in names:
        try:
            core = ET.fromstring(z.read("docProps/core.xml"))
            out["title"] = _clean_name(core.findtext(DC + "title"))
            out["author_hint"] = _clean_name(core.findtext(DC + "creator")) or \
                _clean_name(core.findtext(CP + "lastModifiedBy"))
        except Exception:
            pass
    out.setdefault("company", "")

    # ---- media, ranked by WHERE it is referenced.
    # An image on the slide MASTER appears on every slide, which is what a logo does. One on a
    # single slide is a screenshot. This ranking is the whole reason we do not need a model to
    # find the logo in the common case.
    refs = {}
    for n in names:
        if not n.endswith(".rels"):
            continue
        try:
            rr = ET.fromstring(z.read(n))
        except Exception:
            continue
        where = ("master" if "slideMaster" in n else
                 "layout" if "slideLayout" in n else
                 "slide1" if re.search(r"slides/_rels/slide1\.xml", n) else
                 "slide" if "slides" in n else "other")
        for rel in rr.findall(R + "Relationship"):
            t = (rel.get("Target") or "").replace("\\", "/")
            if "media/" not in t:
                continue
            key = "ppt/media/" + t.rsplit("media/", 1)[1]
            e = refs.setdefault(key, {"master": 0, "layout": 0, "slide1": 0, "slide": 0, "other": 0})
            e[where] = e.get(where, 0) + 1

    for name in sorted(n for n in names if n.startswith("ppt/media/")):
        try:
            blob = z.read(name)
        except Exception:
            continue
        kind, w, h = image_info(blob)
        if not kind:
            continue                                   # emf/wmf/video/audio: not a usable logo
        r = refs.get(name, {})
        score = (r.get("master", 0) * 100) + (r.get("layout", 0) * 20) + (r.get("slide1", 0) * 30)
        out["media"].append({
            "name": name, "kind": kind, "w": w, "h": h, "bytes": len(blob), "score": score,
            "on_master": bool(r.get("master")), "on_layouts": r.get("layout", 0),
            "on_title_slide": bool(r.get("slide1")),
            "aspect": round((w / h), 2) if (w and h) else None,
            "sha": hashlib.sha256(blob).hexdigest()[:12],
        })
    out["media"].sort(key=lambda m: (-m["score"], m["name"]))

    if "ppt/presentation.xml" in names:
        try:
            p = ET.fromstring(z.read("ppt/presentation.xml"))
            sz = p.find(A + "sldSz")
            if sz is not None:
                out["sizes"] = {"cx": int(sz.get("cx") or 0), "cy": int(sz.get("cy") or 0)}
        except Exception:
            pass
    out["slides"] = sum(1 for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
    return out


def read_media(path_or_bytes, member):
    """Pull one ppt/media/* entry back out. Traversal-guarded: only names extract() emitted."""
    if not re.fullmatch(r"ppt/media/[A-Za-z0-9._-]+", member or ""):
        raise ValueError("refused media name")
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else \
        open(path_or_bytes, "rb").read()
    import io
    with zipfile.ZipFile(io.BytesIO(bytes(data))) as z:
        return z.read(member)


# --------------------------------------------------------------------------- judgement
PANEL = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]

PROMPT = """You are choosing how to apply a company's existing PowerPoint design to a
security report that another system generates. You are NOT inventing colours: every value below was
read out of the file. Decide only what the file cannot state.

FACTS READ FROM THE TEMPLATE
%s

Answer with STRICT JSON, no prose, no markdown fence:
{
  "brand": "RRGGBB",        // the ONE colour a reader would call this company's colour. Must be
                            // one of the values listed above, copied exactly. Prefer a saturated
                            // accent over near-black, near-white or a grey.
  "secondary": "RRGGBB",    // a supporting colour from the list, or the same as brand
  "mode": "light"|"dark",   // is the deck's page background light or dark
  "logo": "ppt/media/...",  // the entry that is the company LOGO, or "" if none of them is.
                            // A logo is usually on the slide master, small, and wide.
                            // A photograph, a screenshot or a square icon is NOT a logo.
  "name": "...",            // the company name a reader would put on a title slide, or ""
  "why": "..."              // one short sentence, under 25 words
}"""


def _facts_for_panel(f):
    lines = ["theme colours:"]
    for k, v in (f.get("colors") or {}).items():
        lines.append("  %-9s #%s   (luminance %.2f)" % (k, v, luminance(v)))
    lines.append("fonts: major=%s minor=%s" % (f.get("fonts", {}).get("major", "?"),
                                               f.get("fonts", {}).get("minor", "?")))
    lines.append("company from file metadata: %r   title: %r" % (f.get("company"), f.get("title")))
    lines.append("images (highest placement score first):")
    for m in (f.get("media") or [])[:12]:
        lines.append("  %-24s %dx%d aspect=%s on_master=%s on_layouts=%d on_title=%s"
                     % (m["name"], m["w"], m["h"], m["aspect"], m["on_master"],
                        m["on_layouts"], m["on_title_slide"]))
    return "\n".join(lines)


def _heuristic(f):
    """What we do when the panel cannot be reached. Never a failed upload.

    accent1 is the brand colour by Office convention, and the highest placement score is the logo.
    That is right most of the time, which is exactly why the panel is an improvement and not a
    dependency.
    """
    cols = f.get("colors") or {}
    cand = [cols.get(k) for k in ("accent1", "accent2", "accent3", "dk2", "hlink")]
    brand = next((c for c in cand if c and 0.03 < luminance(c) < 0.85), None) \
        or cols.get("accent1") or REF["light"]
    sec = cols.get("accent2") or brand
    lt1 = cols.get("lt1") or "FFFFFF"
    # A LOGO IS SHAPED LIKE A LOGO. The first version accepted anything referenced anywhere with an
    # aspect above 0.5, which adopted a 1200x800 PHOTOGRAPH off the title slide as a partner's mark
    # — caught by a test, and it would have gone on every slide of every report they produce.
    # On the MASTER is decisive (an image that repeats on every slide is doing a logo's job).
    # Otherwise it must be wide and small: photographs are large and roughly 3:2 or 4:3.
    logo = ""
    for m in (f.get("media") or []):
        if not m["score"]:
            continue
        area = (m["w"] or 0) * (m["h"] or 0)
        if m["on_master"] or ((m["aspect"] or 0) >= 1.2 and area < 500000):
            logo = m["name"]
            break
    return {"brand": brand, "secondary": sec, "mode": "light" if luminance(lt1) > 0.5 else "dark",
            # <Company> only. NOT dc:title — see build_theme: the deck's title is not the company's
            # name, and using it put a slide headline on a partner's wordmark.
            "logo": logo, "name": _clean_name(f.get("company")),
            "why": "no panel: Office convention (accent1) and the image on the slide master",
            "decided_by": "heuristic", "votes": []}


def judge(f, models=None, ask=None, on=None):
    """Ask the four vendors IN PARALLEL, then decide by QUORUM — never by the first answer.

    Ties and non-answers are expected: the panel is a signal, not an authority (the same rule the
    staging gate follows). Anything below a quorum of 2 falls back to the heuristic rather than
    letting one model's opinion become the partner's brand.

    PARALLEL, not serial, and the reason is a person waiting at an upload form. Four models at a
    45s timeout is up to THREE MINUTES end to end when one of them is slow, and the operator sees a
    spinner the whole time; in parallel the wall clock is the SLOWEST model, not their sum. The
    models are independent by construction here — each is answering the same question about the
    same file and none of them sees another's answer — so there is nothing to serialise.

    `on(pct, msg)` reports each answer AS IT LANDS, so a stuck vendor is visible as the one line
    that never arrives instead of as a spinner that never stops.
    """
    facts = _facts_for_panel(f)
    allowed = {v for v in (f.get("colors") or {}).values()}
    media = {m["name"] for m in (f.get("media") or [])}
    panel = list(models or PANEL)
    say = on or (lambda pct, msg: None)
    if ask is None:
        def ask(model, prompt):
            import enrich as E
            raw, _usage = E._call(prompt, model=model, timeout=45, max_tokens=400)
            return E._json(raw)

    def one(m):
        t0 = time.time()
        try:
            j = ask(m, PROMPT % facts)
            if not isinstance(j, dict):
                return {"model": m, "ok": False, "err": "not a JSON object", "ms": _ms(t0)}
            b = _hex(j.get("brand"))
            # A model that invents a colour that is not in the file is answering a different
            # question. Discard the vote rather than adopting a hallucinated shade.
            if not b or b not in allowed:
                return {"model": m, "ok": False, "ms": _ms(t0),
                        "err": "chose #%s, which is not a colour in the file" % (b or "?")}
            return {"model": m, "ok": True, "brand": b, "ms": _ms(t0),
                    "secondary": _hex(j.get("secondary")) or b,
                    "mode": "dark" if str(j.get("mode", "")).lower() == "dark" else "light",
                    "logo": j.get("logo") if j.get("logo") in media else "",
                    "name": str(j.get("name") or "").strip()[:80],
                    "why": str(j.get("why") or "").strip()[:160]}
        except Exception as e:
            return {"model": m, "ok": False, "err": repr(e)[:120], "ms": _ms(t0)}

    votes = []
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=max(1, len(panel))) as ex:
            futs = {ex.submit(one, m): m for m in panel}
            for fut in as_completed(futs):
                v = fut.result()
                votes.append(v)
                say(20 + int(50 * len(votes) / max(1, len(panel))),
                    "%s: %s (%.1fs)" % (v["model"],
                                        ("chose #" + v["brand"]) if v.get("ok") else v.get("err", "?"),
                                        v.get("ms", 0) / 1000.0))
    except Exception:
        # A thread pool we cannot create must not cost the partner their upload.
        for m in panel:
            votes.append(one(m))
    votes.sort(key=lambda v: panel.index(v["model"]) if v["model"] in panel else 99)

    good = [v for v in votes if v.get("ok")]
    if len(good) < 2:
        h = _heuristic(f)
        h["votes"] = votes
        h["decided_by"] = "heuristic (%d of %d models answered)" % (len(good), len(models or PANEL))
        return h

    def winner(key, fallback=""):
        tally = {}
        for v in good:
            val = v.get(key) or ""
            if val:
                tally[val] = tally.get(val, 0) + 1
        if not tally:
            return fallback
        top = max(tally.values())
        # Deterministic tie-break, so two runs on one file cannot disagree.
        return sorted([k for k, n in tally.items() if n == top])[0]

    brand = winner("brand", _heuristic(f)["brand"])
    agree = sum(1 for v in good if v.get("brand") == brand)
    return {"brand": brand, "secondary": winner("secondary", brand), "mode": winner("mode", "light"),
            "logo": winner("logo", ""), "name": winner("name", f.get("company") or ""),
            "why": next((v["why"] for v in good if v.get("brand") == brand and v.get("why")), ""),
            "decided_by": "panel %d/%d agreed on the brand colour" % (agree, len(good)),
            "votes": votes}


# --------------------------------------------------------------------------- the rails
def build_theme(f, j, logo_name=None, powered_by=None, logo_wh=None):
    """Facts + judgement -> the theme the builders consume. Every rail is applied HERE."""
    warn = []
    brand = _hex(j.get("brand")) or REF["light"]
    stops = ramp(brand)

    # RAIL 1 — the ink on each stop is MEASURED, not chosen.
    on_light = ink_for(stops["light"])
    on_dark = ink_for(stops["dark"])
    for k, ink in (("light", on_light), ("dark", on_dark)):
        c = contrast(stops[k], ink)
        if c < 4.5:
            warn.append("neither black nor white reaches 4.5:1 on %s (%s, best %.1f:1) — text on it "
                        "is reduced to large sizes only" % (k, stops[k], c))

    ink = "1A1A1A"
    paper = "FFFFFF"
    if contrast(paper, ink) < 4.5:                       # cannot happen today; asserted anyway
        ink = "000000"

    # A template still on the stock Office palette states nothing about the partner's brand. Theming
    # their reports in Microsoft's default blue while implying we read THEIR design would be a
    # confident wrong answer, which this repo treats as worse than an honest "we could not tell".
    if is_stock_palette(f.get("colors")):
        warn.append("this template still uses the default Office colour scheme, so it carries no "
                    "brand colour of its own — set the colour by hand, or upload a deck that uses "
                    "your real template")

    # The name is a SUGGESTION until a human confirms it — it goes on a customer's title slide.
    # NOT dc:title. That is the DECK's title, and using it produced the wordmark
    # "Why Redevco Needs Breach & Attack Simula[tion]" on a real file. Only <Company> means the
    # organisation; anything else is a guess dressed as a fact, on a customer's title slide.
    suggested = _clean_name(j.get("name")) or _clean_name(f.get("company"))
    if not suggested:
        warn.append("the file does not say which company it belongs to — type the name that should "
                    "appear on the artifacts")
    theme = {
        "v": 1,
        "name": suggested,
        "wordmark": suggested[:40],
        "logo": logo_name or None,
        # The PIXEL dimensions, recorded at upload. brand.js fits the image inside the box the
        # wordmark used to occupy and needs the real aspect ratio to do it: a logo stretched to the
        # box's proportions is the most obvious possible sign that a machine applied the template.
        "logo_w": (logo_wh or (0, 0))[0] or None,
        "logo_h": (logo_wh or (0, 0))[1] or None,
        "mode": j.get("mode", "light"),
        "palette": {
            # Named for the ROLE, mapped onto the builders' keys by brand.js. Their key names
            # (`teal`) are lookup keys and are deliberately not renamed — the same reason the COLT
            # remediation tag survived the rebrand.
            "brandLight": stops["light"],
            "brandMid": stops["mid"],
            "brandDark": stops["dark"],
            "onBrandLight": on_light,
            "onBrandDark": on_dark,
            "ink": ink,
            "paper": paper,
        },
        "fonts": {
            "heading": (f.get("fonts", {}) or {}).get("major") or "Georgia",
            "body": (f.get("fonts", {}) or {}).get("minor") or "Calibri",
        },
        "powered_by": powered_by if powered_by is not None else POWERED_BY,
        "source": {"sha256": f.get("sha256"), "slides": f.get("slides"),
                   "colors": f.get("colors"), "company": f.get("company")},
        "decided_by": j.get("decided_by", ""),
        "why": j.get("why", ""),
        "votes": [{k: v.get(k) for k in ("model", "ok", "brand", "logo", "err") if k in v}
                  for v in (j.get("votes") or [])],
        "warnings": warn,
    }
    # RAIL 3 is an absence, and absences rot: assert it. Severity colours must NEVER be themed.
    assert not (set(theme["palette"]) & {"crit", "high", "med", "low"}), \
        "severity colours are semantic enums and must not be part of a partner theme"
    return theme


def verify(theme):
    """Re-check a theme.json we are about to render with. Cheap, and it catches a hand-edited file.

    Returns a list of problems; empty means usable.
    """
    p = (theme or {}).get("palette") or {}
    bad = []
    for k in ("brandLight", "brandMid", "brandDark", "ink", "paper"):
        if not _hex(p.get(k)):
            bad.append("palette.%s is not a colour" % k)
    if bad:
        return bad
    if set(p) & {"crit", "high", "med", "low"}:
        bad.append("the theme tries to override a severity colour, which is a semantic enum")
    order = [luminance(p["brandLight"]), luminance(p["brandMid"]), luminance(p["brandDark"])]
    if not (order[0] >= order[1] >= order[2]):
        bad.append("the brand ramp is not ordered light -> dark (%.2f/%.2f/%.2f); layouts that put "
                   "dark text on the light stop would be unreadable" % tuple(order))
    for stop, inkkey in (("brandLight", "onBrandLight"), ("brandDark", "onBrandDark")):
        if _hex(p.get(inkkey)) and contrast(p[stop], p[inkkey]) < 3.0:
            bad.append("%s on %s is %.1f:1 — below 3:1, unreadable at any size"
                       % (inkkey, stop, contrast(p[stop], p[inkkey])))
    if contrast(p["paper"], p["ink"]) < 4.5:
        bad.append("body text does not reach 4.5:1 on the page background")
    return bad


# --------------------------------------------------------------------------- cli
def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "extract":
        src = argv[2]
        out = None
        use_panel = "--no-panel" not in argv
        if "--out" in argv:
            out = argv[argv.index("--out") + 1]
        f = extract(src)
        j = _heuristic(f) if not use_panel else judge(f)
        logo = j.get("logo") or ""
        theme = build_theme(f, j, logo_name=(os.path.basename(logo) if logo else None))
        problems = verify(theme)
        theme["warnings"] = list(theme.get("warnings") or []) + problems
        text = json.dumps(theme, indent=2, ensure_ascii=False)
        if out:
            open(out, "w", encoding="utf-8").write(text)
            print("wrote %s" % out)
        else:
            print(text)
        return 1 if problems else 0
    if cmd == "show":
        theme = json.load(open(argv[2], encoding="utf-8"))
        p = theme["palette"]
        print("name      : %s" % theme.get("name"))
        print("decided by: %s" % theme.get("decided_by"))
        for k in ("brandLight", "brandMid", "brandDark"):
            print("  %-11s #%s  luminance %.2f  ink #%s"
                  % (k, p[k], luminance(p[k]),
                     p.get("onBrandLight" if k == "brandLight" else "onBrandDark", "")))
        bad = verify(theme)
        print("verify    : %s" % ("OK" if not bad else "; ".join(bad)))
        return 1 if bad else 0
    print("unknown command %r" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
