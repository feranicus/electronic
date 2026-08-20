#!/usr/bin/env python3
"""pptx_preview.py — draw ONE slide of a .pptx as SVG, so a partner can see it before it ships.

WHY THIS EXISTS. White Label decides a partner's palette from their own deck, and no extractor is
right for every file: the S4biz brief carried a stock Office theme, so the first version themed the
reports in Microsoft's default blue, and the second synthesised a dark fill that came out within
(1,-2,15) of the palette we had just retired. Both were shipped to the operator before anyone
looked. The fix that generalises is not a better heuristic, it is letting a human look first.

WHY IT PARSES THE ARTIFACT RATHER THAN RE-DRAWING IT. The obvious cheap preview is a React mock of
the cover using the theme colours. That is a SECOND implementation of the cover, and this repo has
paid repeatedly for a value with two homes: it will drift from the builder and then reassure a
partner about a slide that does not exist. So the real builder emits a real .pptx and this reads the
shapes back out of slide1.xml. What you see is what pptxgenjs wrote.

WHY NOT LIBREOFFICE. `soffice --convert-to png` renders faithfully and costs ~400 MB in the image
plus several seconds per call, for a page whose whole job is to show colour placement. A cover is a
handful of rectangles, some text and at most one image; that subset is small enough to render
honestly here. Anything this cannot draw is REPORTED in the SVG rather than silently omitted, so an
empty-looking preview can never be mistaken for an empty slide.

Not a general OOXML renderer and not trying to be. Supported: rectangles, rounded rectangles,
ellipses, lines, plain text boxes with per-run size/bold/italic/colour, paragraph alignment, and
embedded raster images. Gradients, tables, charts, SmartArt and autoshapes fall back to an outline.
"""
import base64
import io
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
RELNS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

EMU = 914400.0                      # per inch
PX = 96.0                           # preview pixels per inch


def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _hex6(s):
    s = (s or "").strip().lstrip("#").upper()
    return s if re.fullmatch(r"[0-9A-F]{6}", s or "") else None


def _fill(node):
    """The solid fill of a shape or run, or None. Theme colours are not resolved on purpose.

    Every builder in this repo paints with an explicit <a:srgbClr>, which is exactly why White Label
    can read a brand out of a generated deck at all. A schemeClr here would mean the shape is NOT
    one of ours, and guessing at it would put a colour in the preview that the file does not state.
    """
    if node is None:
        return None
    sf = node.find(A + "solidFill")
    if sf is None:
        return None
    c = sf.find(A + "srgbClr")
    return _hex6(c.get("val")) if c is not None else None


def _xfrm(sp):
    # A graphicFrame (table, chart) positions itself with <p:xfrm>, not <a:xfrm>. Looking only for
    # the drawingml one made every table return None and be skipped BEFORE the unsupported counter,
    # so the findings index rendered as a blank page with nothing saying why — the precise failure
    # the counter exists to prevent.
    x = sp.find(".//" + A + "xfrm")
    if x is None:
        x = sp.find(P + "xfrm")
    if x is None:
        return None
    off, ext = x.find(A + "off"), x.find(A + "ext")
    if off is None or ext is None:
        return None
    try:
        return (int(off.get("x") or 0) / EMU, int(off.get("y") or 0) / EMU,
                int(ext.get("cx") or 0) / EMU, int(ext.get("cy") or 0) / EMU)
    except (TypeError, ValueError):
        return None


def _geom(sp):
    g = sp.find(".//" + A + "prstGeom")
    return (g.get("prst") or "rect") if g is not None else "rect"


def _runs(sp):
    """[(paragraph_align, [(text, size_pt, bold, italic, colour, face)])] in document order."""
    out = []
    # A SHAPE's text body is <p:txBody>; a TABLE CELL's is <a:txBody>. Same element name, different
    # namespace, and looking only for the presentationml one drew every table as coloured bars with
    # no text in them.
    body = sp.find(P + "txBody")
    if body is None:
        body = sp.find(A + "txBody")
    if body is None:
        return out
    for p in body.findall(A + "p"):
        pr = p.find(A + "pPr")
        algn = (pr.get("algn") if pr is not None else None) or "l"
        runs = []
        for r in p.findall(A + "r"):
            t = r.findtext(A + "t") or ""
            if not t:
                continue
            rpr = r.find(A + "rPr")
            sz = 18.0
            bold = ital = False
            face = None
            if rpr is not None:
                try:
                    sz = int(rpr.get("sz") or 1800) / 100.0
                except (TypeError, ValueError):
                    sz = 18.0
                bold = (rpr.get("b") or "0") in ("1", "true")
                ital = (rpr.get("i") or "0") in ("1", "true")
                lat = rpr.find(A + "latin")
                if lat is not None:
                    face = lat.get("typeface")
            runs.append((t, sz, bold, ital, _fill(rpr) or "1A1A1A", face))
        if runs:
            out.append((algn, runs))
    return out


def _media_for(z, slide_name, embed_id):
    rels = "ppt/slides/_rels/" + os.path.basename(slide_name) + ".rels"
    if rels not in z.namelist():
        return None
    try:
        root = ET.fromstring(z.read(rels))
    except ET.ParseError:
        return None
    for rel in root.findall(RELNS + "Relationship"):
        if rel.get("Id") != embed_id:
            continue
        tgt = (rel.get("Target") or "").replace("\\", "/")
        if "media/" not in tgt:
            return None
        name = "ppt/media/" + tgt.rsplit("media/", 1)[1]
        if name not in z.namelist():
            return None
        blob = z.read(name)
        if len(blob) > 4 * 1024 * 1024:
            return None
        kind = ("image/png" if blob[:8] == b"\x89PNG\r\n\x1a\n" else
                "image/jpeg" if blob[:2] == b"\xff\xd8" else
                "image/gif" if blob[:3] == b"GIF" else None)
        if not kind:
            return None
        return "data:%s;base64,%s" % (kind, base64.b64encode(blob).decode("ascii"))
    return None


def render(path_or_bytes, index=1, scale=1.0):
    """One slide -> an SVG string. `index` is 1-based, matching slide1.xml."""
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else \
        open(path_or_bytes, "rb").read()
    z = zipfile.ZipFile(io.BytesIO(bytes(data)))

    w_in, h_in = 10.0, 5.625
    if "ppt/presentation.xml" in z.namelist():
        try:
            sz = ET.fromstring(z.read("ppt/presentation.xml")).find(A + "sldSz")
            if sz is not None:
                w_in = int(sz.get("cx") or 0) / EMU or w_in
                h_in = int(sz.get("cy") or 0) / EMU or h_in
        except (ET.ParseError, TypeError, ValueError):
            pass

    name = "ppt/slides/slide%d.xml" % int(index)
    if name not in z.namelist():
        raise ValueError("the deck has no slide %s" % index)
    root = ET.fromstring(z.read(name))
    tree = root.find(".//" + P + "cSld")
    spTree = tree.find(P + "spTree") if tree is not None else None
    if spTree is None:
        raise ValueError("slide %s has no shape tree" % index)

    W, H = w_in * PX * scale, h_in * PX * scale
    body = ['<rect width="%.1f" height="%.1f" fill="#FFFFFF"/>' % (W, H)]
    unsupported = 0

    for sp in list(spTree):
        tag = sp.tag
        # The shape tree's OWN metadata, not content. grpSpPr carries an <a:xfrm> (the group
        # transform), so it survives the geometry check and was being counted as an element the
        # preview could not draw — a footer reading "1 element on this slide is not drawn" on a
        # slide where everything was drawn. A diagnostic that miscounts is worse than none.
        if tag in (P + "nvGrpSpPr", P + "grpSpPr"):
            continue
        box = _xfrm(sp)
        if box is None:
            continue
        x, y, w, h = (v * PX * scale for v in box)

        if tag == P + "pic":
            blip = sp.find(".//" + A + "blip")
            src = _media_for(z, name, blip.get(R + "embed")) if blip is not None else None
            if src:
                body.append('<image x="%.1f" y="%.1f" width="%.1f" height="%.1f" href="%s" '
                            'preserveAspectRatio="xMidYMid meet"/>' % (x, y, w, h, src))
            else:
                unsupported += 1
            continue
        if tag == P + "graphicFrame":
            tbl = sp.find(".//" + A + "tbl")
            if tbl is None:
                unsupported += 1                       # a chart or SmartArt: say so, draw nothing
                continue
            # TABLES ARE DRAWN because they are where the brand colour actually appears: on a real
            # branded deck the cover carries 5 branded fills and the findings index 21, almost all
            # of them table header cells. A preview that silently omitted them would show a partner
            # a blank page and invite them to approve it.
            cols = [int(g.get("w") or 0) / EMU * PX * scale
                    for g in tbl.findall(A + "tblGrid/" + A + "gridCol")]
            ry = y
            for tr in tbl.findall(A + "tr"):
                try:
                    rh = int(tr.get("h") or 0) / EMU * PX * scale
                except (TypeError, ValueError):
                    rh = 0.0
                cx = x
                for ci, tc in enumerate(tr.findall(A + "tc")):
                    cw = cols[ci] if ci < len(cols) else (w / max(1, len(cols)))
                    cf = _fill(tc.find(A + "tcPr"))
                    if cf:
                        body.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                                    'fill="#%s"/>' % (cx, ry, cw, max(rh, 1.0), cf))
                    for algn, runs in _runs(tc):
                        txt = "".join(r[0] for r in runs)
                        if not txt.strip():
                            continue
                        sz, bold, col, face = runs[0][1], runs[0][2], runs[0][4], runs[0][5]
                        tx = cx + 3 if algn == "l" else (cx + cw - 3 if algn == "r" else cx + cw / 2)
                        anchor = ("start" if algn == "l" else
                                  "end" if algn == "r" else "middle")
                        body.append('<text x="%.1f" y="%.1f" font-size="%.1f" fill="#%s" '
                                    'text-anchor="%s" font-family="%s"%s>%s</text>'
                                    % (tx, ry + max(rh, sz * scale) / 2 + sz * scale * 0.35,
                                       sz * scale, col, anchor, _esc(face or "Georgia, serif"),
                                       ' font-weight="700"' if bold else "", _esc(txt[:90])))
                    cx += cw
                ry += max(rh, 1.0)
            continue
        if tag != P + "sp":
            unsupported += 1
            continue

        spPr = sp.find(P + "spPr")
        fill = _fill(spPr)
        geom = _geom(sp)
        ln = spPr.find(A + "ln") if spPr is not None else None
        stroke = _fill(ln)
        try:
            sw = (int(ln.get("w")) / EMU * PX * scale) if (ln is not None and ln.get("w")) else 1.0
        except (TypeError, ValueError):
            sw = 1.0

        attrs = 'fill="%s"' % (("#" + fill) if fill else "none")
        if stroke:
            attrs += ' stroke="#%s" stroke-width="%.2f"' % (stroke, max(sw, 0.5))
        if geom in ("ellipse", "circle"):
            body.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" %s/>'
                        % (x + w / 2, y + h / 2, w / 2, h / 2, attrs))
        elif geom == "line":
            body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                        'stroke-width="%.2f"/>'
                        % (x, y, x + w, y + h, ("#" + (stroke or fill or "1A1A1A")), max(sw, 0.75)))
        elif fill or stroke:
            rx = ' rx="%.1f"' % min(w, h, 8 * scale) if geom == "roundRect" else ""
            body.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s %s/>'
                        % (x, y, w, h, rx, attrs))

        # TEXT. pptxgenjs vertically centres in the box by default and wraps on width; both are
        # approximated here. This is a colour-placement preview, not a typesetter, and the wrapping
        # estimate is stated rather than hidden so nobody reads it as a layout proof.
        paras = _runs(sp)
        if not paras:
            continue
        lines = []
        for algn, runs in paras:
            txt = "".join(r[0] for r in runs)
            sz, bold, ital, col, face = runs[0][1], runs[0][2], runs[0][3], runs[0][4], runs[0][5]
            cap = max(4, int(w / (sz * scale * 0.52))) if sz else 40
            words, cur = txt.split(), ""
            for word in words:
                if cur and len(cur) + 1 + len(word) > cap:
                    lines.append((cur, algn, sz, bold, ital, col, face))
                    cur = word
                else:
                    cur = (cur + " " + word).strip()
            lines.append((cur, algn, sz, bold, ital, col, face))
        lh = max(l[2] for l in lines) * 1.22 * scale
        top = y + max(0.0, (h - lh * len(lines)) / 2.0) + lh * 0.78
        for i, (txt, algn, sz, bold, ital, col, face) in enumerate(lines):
            tx = x + 2 if algn == "l" else (x + w - 2 if algn == "r" else x + w / 2)
            anchor = "start" if algn == "l" else ("end" if algn == "r" else "middle")
            body.append('<text x="%.1f" y="%.1f" font-size="%.1f" fill="#%s" text-anchor="%s"'
                        ' font-family="%s"%s%s>%s</text>'
                        % (tx, top + i * lh, sz * scale, col, anchor,
                           _esc(face or "Georgia, serif"),
                           ' font-weight="700"' if bold else "",
                           ' font-style="italic"' if ital else "", _esc(txt)))

    if unsupported:
        body.append('<text x="6" y="%.1f" font-size="9" fill="#8A8F98" font-family="sans-serif">'
                    '%d element(s) on this slide are not drawn in the preview</text>'
                    % (H - 6, unsupported))

    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.1f %.1f" width="%.0f" '
            'height="%.0f" role="img" aria-label="cover slide preview">%s</svg>'
            % (W, H, W, H, "".join(body)))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: pptx_preview.py <deck.pptx> [slide] [out.svg]", file=sys.stderr)
        sys.exit(2)
    svg = render(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    if len(sys.argv) > 3:
        open(sys.argv[3], "w", encoding="utf-8").write(svg)
        print("wrote %s (%d bytes)" % (sys.argv[3], len(svg)))
    else:
        sys.stdout.write(svg)
