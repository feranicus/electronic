"""Render the LinkedIn WAF/DDoS/SASE story as slow-crossfade frames (Colt design system)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import argparse, os, math, sys

W = H = 1080                        # square: LinkedIn's biggest in-feed real estate
NAVY   = (13, 20, 38)
NAVY2  = (18, 27, 50)
TEAL   = (0, 178, 169)
DTEAL  = (12, 84, 78)
GOLD   = (247, 200, 68)
RED    = (242, 12, 54)
INK    = (234, 241, 251)
MUT    = (147, 169, 206)
GREEN  = (16, 185, 129)

_DIRS = ["/usr/share/fonts/truetype/dejavu/",              # linux
         os.path.join(os.environ.get("WINDIR", r"C:\\Windows"), "Fonts")]  # windows


def _font(name, sz):
    """DejaVu if present, else a metric-ish Windows fallback. Never crash on a missing font."""
    alt = {"DejaVuSans-Bold.ttf": "arialbd.ttf", "DejaVuSans.ttf": "arial.ttf",
           "DejaVuSansMono-Bold.ttf": "consolab.ttf", "DejaVuSansMono.ttf": "consola.ttf"}
    for base in _DIRS:
        for n in (name, alt[name]):
            p = os.path.join(base, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def f(sz, bold=True):  return _font("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", sz)
def m(sz, bold=False): return _font("DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf", sz)

def bg():
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    for y in range(H):                      # subtle vertical gradient
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(13 + 9*t), int(20 + 11*t), int(38 + 16*t)))
    g = Image.new("RGB", (W, H), NAVY); gd = ImageDraw.Draw(g)
    gd.ellipse([W-460, -260, W+240, 440], fill=DTEAL)          # teal glow, top-right
    gd.ellipse([-300, H-320, 300, H+280], fill=(20, 40, 70))
    g = g.filter(ImageFilter.GaussianBlur(150))
    return Image.blend(im, g, 0.55)

def chrome(d, page, total):
    d.text((64, 52), "❯", font=f(34), fill=TEAL)
    d.text((96, 52), "colt", font=f(34), fill=INK)
    d.text((W-150, 60), "%d/%d" % (page, total), font=m(22), fill=MUT)
    d.line([(64, H-72), (W-64, H-72)], fill=(40, 55, 85), width=2)
    d.text((64, H-56), "» » » » »", font=f(18), fill=(46, 64, 96))
    d.text((W-260, H-56), "cybergod.ai · Colt / S4Biz", font=f(16, False), fill=(70, 92, 132))

def wrap(d, txt, font, maxw):
    out, line = [], ""
    for w in txt.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: line = t
        else: out.append(line); line = w
    if line: out.append(line)
    return out

def slide(page, total, kicker, kcol, title, lines, code=None, big=None, bigsub=None, accent=TEAL):
    im = bg()
    chrome(ImageDraw.Draw(im), page, total)
    # draw the content on its own layer so we can MEASURE it and centre it — top-aligned slides
    # left ~350px of dead space at the bottom and read unbalanced.
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    y = 168
    d.rectangle([64, y, 64+8, y+30], fill=kcol)
    d.text((84, y-2), kicker, font=f(24), fill=kcol)
    y += 62
    for ln in wrap(d, title, f(60), W-140):
        d.text((64, y), ln, font=f(60), fill=INK); y += 70
    y += 14
    if big:
        d.text((64, y), big, font=f(150), fill=accent); y += 196   # descender room
        if bigsub:
            for ln in wrap(d, bigsub, f(30, False), W-140):
                d.text((64, y), ln, font=f(30, False), fill=MUT); y += 40
        y += 8
    if code:
        bh = 34 * len(code) + 44
        d.rounded_rectangle([64, y, W-64, y+bh], 14, fill=(9, 14, 28), outline=(38, 52, 80), width=2)
        cy = y + 22
        for ln, col in code:
            d.text((90, cy), ln, font=m(22), fill=col); cy += 34
        y += bh + 30
    for ln in lines:
        col, txt, fnt = ln
        for w in wrap(d, txt, fnt, W-150):
            d.text((64, y), w, font=fnt, fill=col); y += fnt.size + 14
        y += 10
    bb = layer.getbbox()
    if bb:
        top_safe, bot_safe = 150, H - 110
        content_h = bb[3] - bb[1]
        off = int(top_safe + ((bot_safe - top_safe) - content_h) / 2) - bb[1]
        off = max(0, off)                       # never push content up under the brand
        shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shifted.paste(layer.crop((0, bb[1], W, bb[3])), (0, bb[1] + off))
        layer = shifted
    im.paste(layer, (0, 0), layer)
    return im

B  = lambda s: (INK,  s, f(34))
Bm = lambda s: (MUT,  s, f(30, False))
Bt = lambda s: (TEAL, s, f(34))
Bg = lambda s: (GOLD, s, f(32))

TOTAL = 7
S = []
S.append(slide(1, TOTAL, "24 HOURS · REAL LOG", GOLD,
    "A brand-new domain. Nobody knew it existed.",
    [Bm("No links to it. No announcement. Not indexed."), B("It was scanned within hours."),
     Bm("Not targeted — found. By machines.")]))

S.append(slide(2, TOTAL, "WHAT HIT IT", RED, "Three sources. Zero humans.",
    [Bt("MITRE ATT&CK  T1595.003 — Wordlist Scanning"),
     Bm("Hunting webshells, admin panels, cloud keys.")],
    code=[("20.63.63.128     Azure   → /wp-content/…/wp_filemanager.php", MUT),
          ("20.151.7.119     Azure   → /admin.php, /wp-includes/", MUT),
          ("216.144.249.201  Censys  → /.env, /.git/config", MUT)]))

S.append(slide(3, TOTAL, "LAYER 1 · WAF", TEAL, "One rule. Ten minutes.",
    big="100%", bigsub="of that day's hostile traffic — blocked", accent=TEAL,
    lines=[Bm("block  /wp-   *.php   /.env   /.git"),
           B("Nothing legitimate on my host ends in .php."),
           Bm("The cheapest control you will ever deploy.")]))

S.append(slide(4, TOTAL, "LAYER 2 · DDoS", RED, "Recon is the cheap half.",
    big="31.4 Tbps", bigsub="largest DDoS ever recorded · Aisuru · Dec 2025 · lasted 35 seconds",
    accent=RED,
    lines=[Bm("Oct 2024 record: 3.8 Tbps  →  +700% in 14 months"),
           Bm("Cloudflare mitigated 47.1M attacks in 2025 (~227k/day)")]))

S.append(slide(5, TOTAL, "PHYSICS, NOT SKILL", GOLD, "31 Tbps into a 10 Gbps circuit.",
    [B("The circuit is the casualty."),
     Bm("The packets never reach anything you own. Your firewall, your load balancer, your tuned nginx — all irrelevant."),
     Bg("You cannot patch your way out of a bandwidth problem."),
     Bt("It has to be absorbed upstream, in the carrier's network.")]))

S.append(slide(6, TOTAL, "LAYER 0 · SECURE BY DESIGN", TEAL, "Why did I need that WAF rule at all?",
    [Bm("Because the service was exposed in the first place."),
     B("SASE / ZTNA = there is no public edge to scan."),
     Bm("No open panel. No internet-facing VPN appliance waiting to become next quarter's KEV entry."),
     Bt("You cannot wordlist a door that does not exist.")]))

S.append(slide(7, TOTAL, "THE ORDER I'D DEPLOY IT", GOLD, "Bolt-on is a tax you pay forever.",
    [Bt("1 · SASE / ZTNA      — remove the exposed edge"),
     Bt("2 · Managed WAF      — kill the wordlists"),
     Bt("3 · IP Guardian      — absorb the flood upstream"),
     Bm("NIS2 applies in DE since 6 Dec 2025 · BSI audits from H2 2026 · Art. 21 = availability."),
     Bg("Day-zero architecture is paid once.")]))

_ap = argparse.ArgumentParser()
_ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames"))
_a = _ap.parse_args()
os.makedirs(_a.out, exist_ok=True)
for i, im in enumerate(S, 1):
    im.save(os.path.join(_a.out, "s%02d.png" % i))
print("rendered", len(S), "slides ->", W, "x", H, "->", _a.out)
