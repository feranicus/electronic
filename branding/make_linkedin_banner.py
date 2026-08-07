#!/usr/bin/env python3
"""
Build the LinkedIn profile banner for Evgeny Vainsteins.

Brand source of truth = S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx
(exact hex values lifted from ppt/slides/slide1.xml + slide2.xml) plus the
cybergod.ai chevron mark from webapp/frontend/public/icon.svg.

LinkedIn personal banner is 1584 x 396. The profile photo overlaps the
bottom-left; measured against a live render it covers roughly
x 93..505, y 192..396, and the "edit" pencil sits over the top-right corner.
Everything load-bearing therefore lives right of x=540 or above y=180.

    python branding/make_linkedin_banner.py
"""
import os
import math

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------- palette
INK        = (0x14, 0x16, 0x1F)   # 14161F  deck base
INK_DEEP   = (0x08, 0x13, 0x1A)   # 08131A
INDIGO     = (0x4F, 0x46, 0xE5)   # 4F46E5
VIOLET     = (0x8B, 0x5C, 0xF6)   # 8B5CF6
CYAN       = (0x22, 0xD3, 0xEE)   # 22D3EE
MIST       = (0xC7, 0xCD, 0xDA)   # C7CDDA
STEEL      = (0x8E, 0x97, 0xA8)   # 8E97A8
WHITE      = (0xFF, 0xFF, 0xFF)
TEAL       = (0x00, 0xB2, 0xA9)   # cybergod.ai mark

W, H = 1584, 396
SAFE_X = 540                      # left of this is under the profile photo
CX     = 1048                     # optical centre of the usable area (right of the avatar)

# ---------------------------------------------------------------- fonts
# Arial Black / Consolas are not on the build host; Lato Black is the closest
# available heavy grotesque and DejaVu Sans Mono stands in for Consolas.
F_DIR = "/usr/share/fonts/truetype"
BLACK = f"{F_DIR}/lato/Lato-Black.ttf"
BOLD  = f"{F_DIR}/lato/Lato-Bold.ttf"
MONO  = f"{F_DIR}/dejavu/DejaVuSansMono.ttf"
MONOB = f"{F_DIR}/dejavu/DejaVuSansMono-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- helpers
def tracked(draw, xy, text, fnt, fill, track=0, anchor="ls", stroke=0):
    """Draw text with letter-spacing. Returns total advance width."""
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + track * (len(text) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for c, adv in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill, anchor="l" + anchor[1],
                  stroke_width=stroke, stroke_fill=fill)
        x += adv + track
    return total


def tracked_width(draw, text, fnt, track=0):
    return sum(draw.textlength(c, font=fnt) for c in text) + track * (len(text) - 1)


def linear_gradient(size, c0, c1, horizontal=True):
    w, h = size
    g = Image.new("RGB", (w, h))
    px = g.load()
    n = w if horizontal else h
    for i in range(n):
        t = i / max(1, n - 1)
        col = tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
        for j in range(h if horizontal else w):
            px[(i, j)] if False else None
        if horizontal:
            for j in range(h):
                px[i, j] = col
        else:
            for j in range(w):
                px[j, i] = col
    return g


def radial_glow(size, centre, radius, colour, strength):
    """Soft radial light, returned as an RGB layer + alpha mask."""
    w, h = size
    small = 6                                     # build small, upscale = fast + smooth
    m = Image.new("L", (w // small, h // small), 0)
    d = ImageDraw.Draw(m)
    cx, cy = centre[0] / small, centre[1] / small
    r = radius / small
    steps = 48
    for i in range(steps, 0, -1):
        t = i / steps
        a = int(strength * (1 - t) ** 2)
        rr = r * t
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=a)
    m = m.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(28))
    layer = Image.new("RGB", (w, h), colour)
    return layer, m


# ---------------------------------------------------------------- canvas
img = Image.new("RGB", (W, H), INK)

# deep vignette base: slightly darker on the left where the avatar sits
base = linear_gradient((W, H), INK_DEEP, INK, horizontal=True)
img = Image.blend(img, base, 0.55)

# indigo -> violet light across the right half (the deck's cover gradient)
for centre, rad, col, s in (
    ((1180, 150), 900, INDIGO, 150),
    ((1460, 330), 700, VIOLET, 120),
    ((760, 60), 620, INDIGO, 70),
    ((600, 370), 520, CYAN, 38),
):
    layer, mask = radial_glow((W, H), centre, rad, col, s)
    img = Image.composite(Image.blend(img, layer, 0.55), img, mask)

draw = ImageDraw.Draw(img, "RGBA")

# faint engineering grid (deck background texture)
GRID = 44
for x in range(0, W, GRID):
    draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 9), width=1)
for y in range(0, H, GRID):
    draw.line([(0, y), (W, y)], fill=(255, 255, 255, 9), width=1)

# scanning sweep: faint concentric arcs radiating from the right edge
for r in range(240, 1500, 78):
    draw.arc([W - 120 - r, H // 2 - r, W - 120 + r, H // 2 + r],
             start=100, end=260, fill=(0x22, 0xD3, 0xEE, 16), width=1)

# attack-surface node graph, left of the headline. Deterministic coordinates
# (no RNG) so a re-run produces a byte-identical banner.
NODES = [
    (96, 118), (168, 86), (150, 158), (232, 132), (214, 196), (296, 104),
    (300, 172), (372, 146), (356, 210), (438, 118), (446, 190), (508, 158),
    (120, 214), (262, 244), (392, 252), (474, 246),
]
EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (3, 6), (4, 6), (5, 7),
    (6, 7), (6, 8), (7, 9), (7, 10), (8, 10), (9, 11), (10, 11),
    (2, 12), (4, 13), (8, 14), (10, 15), (13, 14), (14, 15),
]
for a, b in EDGES:
    draw.line([NODES[a], NODES[b]], fill=(0x22, 0xD3, 0xEE, 34), width=1)
for i, (nx, ny) in enumerate(NODES):
    hot = i in (3, 7, 10)                       # a few "exposed" nodes
    col = (VIOLET if hot else CYAN) + (150 if hot else 80,)
    r = 3.5 if hot else 2.5
    draw.ellipse([nx - r, ny - r, nx + r, ny + r], fill=col)
    if hot:
        draw.ellipse([nx - 9, ny - 9, nx + 9, ny + 9], outline=VIOLET + (70,), width=1)

# ---------------------------------------------------------------- frame
M = 22
BR = 40                                    # corner bracket arm length
for (bx, by, sx, sy) in ((M, M, 1, 1), (W - M, M, -1, 1),
                         (M, H - M, 1, -1), (W - M, H - M, -1, -1)):
    draw.line([(bx, by), (bx + sx * BR, by)], fill=CYAN + (170,), width=2)
    draw.line([(bx, by), (bx, by + sy * BR)], fill=CYAN + (170,), width=2)

# top + bottom hairlines
draw.line([(M + BR + 14, M), (W - M - BR - 14, M)], fill=(255, 255, 255, 22), width=1)
draw.line([(M + BR + 14, H - M), (W - M - BR - 14, H - M)], fill=(255, 255, 255, 22), width=1)

# ---------------------------------------------------------------- eyebrow
f_eye = font(MONO, 15)
tracked(draw, (64, 46), "[ S4BIZ // SOVEREIGN CYBER & CLOUD // AI × ATTACK SURFACE ]",
        f_eye, CYAN, track=1.4, anchor="lm")

# ---------------------------------------------------------------- headline
HEAD_Y = 142
f_head = font(BLACK, 67)
TRACK = 1.5
parts = [("IN ", WHITE), ("CYBERGOD", None), (" WE TRUST", WHITE)]
widths = [tracked_width(draw, t, f_head, TRACK) + TRACK for t, _ in parts]
total = sum(widths)
x = CX - total / 2

for (text, colour), wdt in zip(parts, widths):
    if colour is not None:
        tracked(draw, (x, HEAD_Y), text, f_head, colour, track=TRACK, anchor="lm", stroke=1)
    else:
        # gradient fill cyan -> violet, drawn through a text mask
        pad = 12
        box = (int(wdt) + pad * 2, 120)
        mask = Image.new("L", box, 0)
        md = ImageDraw.Draw(mask)
        tracked(md, (pad, box[1] // 2), text, f_head, 255, track=TRACK, anchor="lm", stroke=1)
        grad = linear_gradient(box, CYAN, VIOLET, horizontal=True)
        glow = mask.filter(ImageFilter.GaussianBlur(11)).point(lambda v: int(v * 0.55))
        img.paste(Image.new("RGB", box, VIOLET), (int(x) - pad, HEAD_Y - box[1] // 2), glow)
        img.paste(grad, (int(x) - pad, HEAD_Y - box[1] // 2), mask)
        draw = ImageDraw.Draw(img, "RGBA")
    x += wdt

# ---------------------------------------------------------------- sub-line
f_sub = font(BOLD, 17)
tracked(draw, (CX, 200), "AI-DRIVEN ATTACK-SURFACE INTELLIGENCE  ·  SOVEREIGN BY DESIGN",
        f_sub, MIST, track=3.2, anchor="mm")

# rule either side of the sub-line
sub_w = tracked_width(draw, "AI-DRIVEN ATTACK-SURFACE INTELLIGENCE  ·  SOVEREIGN BY DESIGN",
                      f_sub, 3.2)
for sgn in (-1, 1):
    x0 = CX + sgn * (sub_w / 2 + 22)
    draw.line([(x0, 200), (x0 + sgn * 54, 200)], fill=CYAN + (110,), width=1)

# ---------------------------------------------------------------- prompt
f_mono = font(MONO, 16)
prompt = "cybergod.ai --scan --passive --no-carrier --sovereign"
pw = tracked_width(draw, "> " + prompt, f_mono, 0.6)
px0 = CX - pw / 2
tracked(draw, (px0, 242), "> ", f_mono, CYAN, track=0.6, anchor="lm")
tracked(draw, (px0 + tracked_width(draw, "> ", f_mono, 0.6), 242),
        prompt, f_mono, STEEL, track=0.6, anchor="lm")
draw.rectangle([px0 + pw + 5, 234, px0 + pw + 13, 251], fill=CYAN + (210,))

# ---------------------------------------------------------------- lockup
LOCK_Y = 312

# --- cybergod.ai mark: rounded square, chevron, dot (from icon.svg)
def chevron_mark(size):
    s = size * 4
    m = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.1875), fill=(0x0C, 0x54, 0x4E, 255))
    k = s / 512.0
    d.line([(188 * k, 140 * k), (286 * k, 256 * k), (188 * k, 372 * k)],
           fill=TEAL + (255,), width=int(46 * k), joint="curve")
    for pt in ((188 * k, 140 * k), (286 * k, 256 * k), (188 * k, 372 * k)):
        r = 23 * k
        d.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=TEAL + (255,))
    r = 26 * k
    d.ellipse([352 * k - r, 256 * k - r, 352 * k + r, 256 * k + r], fill=TEAL + (255,))
    return m.resize((size, size), Image.LANCZOS)


MARK = 46
mark = chevron_mark(MARK)

f_lock = font(BLACK, 30)
f_s4 = font(BLACK, 27)
gap = 14
cg_w = tracked_width(draw, "cybergod.ai", f_lock, 0.4)
sep_gap = 30
s4_w = tracked_width(draw, "S4", f_s4, 0.8) + tracked_width(draw, "BIZ", f_s4, 0.8) + 2

lock_total = MARK + gap + cg_w + sep_gap * 2 + 1 + s4_w
lx = CX - lock_total / 2

img.paste(mark, (int(lx), LOCK_Y - MARK // 2), mark)
draw = ImageDraw.Draw(img, "RGBA")
lx += MARK + gap
tracked(draw, (lx, LOCK_Y), "cybergod.ai", f_lock, WHITE, track=0.4, anchor="lm")
lx += cg_w + sep_gap
draw.line([(lx, LOCK_Y - 20), (lx, LOCK_Y + 20)], fill=(255, 255, 255, 60), width=1)
lx += sep_gap
w1 = tracked(draw, (lx, LOCK_Y), "S4", f_s4, VIOLET, track=0.8, anchor="lm")
tracked(draw, (lx + w1 + 2, LOCK_Y), "BIZ", f_s4, WHITE, track=0.8, anchor="lm")

# ---------------------------------------------------------------- footer
f_foot = font(MONO, 12)
tracked(draw, (W - 64, H - 46),
        "STARS4BUSINESS OÜ  ·  CYBERGOD LLC  ·  EU-SOVEREIGN  ·  100% PASSIVE RECON",
        f_foot, (0x6E, 0x77, 0x88), track=1.2, anchor="rm")

# ---------------------------------------------------------------- output
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(OUT_DIR, "linkedin_banner_cybergod.png")
img.save(out, "PNG", optimize=True)
print("wrote", out, img.size, os.path.getsize(out), "bytes")

# proof sheet: overlay the profile-photo circle + mobile crop so the safe
# zones can be checked by eye rather than by assumption.
proof = img.copy().convert("RGBA")
pd = ImageDraw.Draw(proof, "RGBA")
pd.ellipse([93, 192, 505, 604], outline=(255, 77, 109, 220), width=3)
pd.rectangle([0, 0, SAFE_X, H], outline=(255, 210, 63, 120), width=2)
pd.rectangle([W - 100, 0, W, 120], outline=(255, 210, 63, 120), width=2)
proof.convert("RGB").save(os.path.join(OUT_DIR, "_proof_safezones.png"))
print("wrote proof sheet")
