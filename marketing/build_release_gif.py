#!/usr/bin/env python3
"""
build_release_gif.py — the cybergod.ai release timeline as an animated GIF for LinkedIn.

WHY A SCRIPT AND NOT A ONE-OFF: the timeline changes every time we ship. Re-run this and the GIF is
rebuilt from the same committed source of truth, so the post never drifts from what actually exists.

Dates and features are taken from the repo's own git history (see MILESTONES below, each entry
traceable to real commits on that date) — not from memory. Nothing here is invented.

    python marketing/build_release_gif.py
    python marketing/build_release_gif.py --square     # 1080x1080 variant for mobile feeds
    python marketing/build_release_gif.py --seconds 4  # slower still
"""
import argparse, os, sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required:  pip install pillow")

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- Colt palette (identical to the site and the decks) -----------------------------------------
INK      = (10, 21, 38)        # near-black background
TEAL     = (0, 178, 169)
TEAL_DIM = (18, 114, 107)
GOLD     = (247, 200, 68)
WHITE    = (233, 240, 247)
MUTED    = (139, 160, 181)
LINE     = (28, 46, 68)

F_BOLD = "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
F_REG  = "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
F_MONO = "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf"


# Liberation Sans has no ❯ ▸ ◆ glyphs — they render as empty boxes (checked, not assumed). Draw the
# brand marks as SHAPES so the GIF never depends on a font having a symbol.
def chevron(d, x, y, size, col, w=None):
    w = w or max(2, int(size * 0.16))
    d.line([(x, y), (x + size * 0.55, y + size * 0.5)], fill=col, width=w)
    d.line([(x + size * 0.55, y + size * 0.5), (x, y + size)], fill=col, width=w)


def tri(d, x, y, size, col):
    d.polygon([(x, y), (x + size * 0.82, y + size * 0.5), (x, y + size)], fill=col)


def diamond(d, cx, cy, r, col):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=col)


def brand(d, W, H):
    """The ❯ colt wordmark, drawn."""
    pad = int(W * 0.055)
    s = int(H * 0.040)
    chevron(d, pad, int(H * 0.052), s, TEAL)
    d.text((pad + int(W * 0.026), int(H * 0.046)), "colt", font=font(F_BOLD, int(H * 0.048)), fill=WHITE)


def font(path, size):
    return ImageFont.truetype(path, size)


# ---- The timeline. Every date is a real commit date in this repo. --------------------------------
MILESTONES = [
    ("09 JUL", "The foundation", [
        "CI/CD from day one: GHCR build, Trivy scan, CodeQL SAST, gitleaks",
        "patchwatch — backup-first, self-patching droplet on a 3-day timer",
        "Grafana observability wired before the first feature shipped",
    ]),
    ("10 JUL", "The engine", [
        "Shodan super-filter playbook + name-only autodiscovery",
        "One input: a company name. Out come four boardroom decks",
        "React cabinet + FastAPI backend — cybergod.ai is born",
    ]),
    ("11 JUL", "Live on the internet", [
        "cybergod.ai deployed entirely through CI/CD",
        "Zero-trust login: allow-list + emailed one-time code",
        "No hand-editing anything on the server, ever",
    ]),
    ("15 JUL", "Money and language", [
        "Persistent cost ledger — true all-time cost per assessment",
        "Every deck in English or Hochdeutsch, one flag",
        "Partner access without a code change",
    ]),
    ("16 JUL", "Trust, safety, mobile", [
        "Hallucination guard: invented CVEs stripped before a slide",
        "Visitor telemetry + 11 security alert rules",
        "Bilingual DSGVO privacy notice · installable mobile PWA",
    ]),
    ("21 JUL", "Zero false positives", [
        "A pivot adopted public CAs and claimed 1,003 hosts. Fixed.",
        "Every anchor must now PROVE ownership, not merely match",
        "Deploys verified by hashing the engine inside the container",
    ]),
    ("22 JUL", "Depth and honesty", [
        "5th deliverable: a bespoke animated threat report per company",
        "An independent second model audits every deck for false positives",
        "Edge appliances and password vaults graded CRITICAL, not noise",
    ]),
    ("23 JUL", "The compliance module", [
        "NIS2 · Cyber Resilience Act · EU AI Act, from one company name",
        "Three regime decks + a combined roadmap, EN or DE",
        "Every technical finding tied to the article it touches",
    ]),
    ("30 JUL", "Attribution done properly", [
        "Group discovery: subsidiaries trading under other names",
        "Co-tenant guard — a shared netblock is not a customer",
        "Graded ownership confidence, with the reasons recorded",
    ]),
    ("31 JUL", "Open the doors", [
        "A public demo anyone can open — real decks, fabricated data",
        "Parallel AI enrichment with cross-vendor failover",
        "118 assessments run. Lifetime AI cost: $0.53.",
    ]),
]

CREED_1 = "Cassandra foretold the fall of Troy — and no one believed her."
CREED_2 = "We predict the critical cyber risks, stop them before they materialise,"
CREED_3 = "and keep every Trojan horse out of your IT landscape."


def bg(W, H):
    """Near-black canvas with a soft teal glow, drawn cheaply so the GIF palette stays small."""
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    cx, cy = int(W * 0.5), int(H * 0.42)
    for i in range(26, 0, -1):
        r = int(min(W, H) * 0.055 * i)
        t = i / 26.0
        col = (int(INK[0] + (TEAL[0] - INK[0]) * 0.05 * (1 - t)),
               int(INK[1] + (TEAL[1] - INK[1]) * 0.05 * (1 - t)),
               int(INK[2] + (TEAL[2] - INK[2]) * 0.05 * (1 - t)))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return img


def chrome(img, W, H, step, total):
    """Brand mark, progress rail and footer — identical on every frame so the eye stays still."""
    d = ImageDraw.Draw(img)
    pad = int(W * 0.055)
    brand(d, W, H)
    d.text((W - pad, int(H * 0.062)), "cybergod.ai", font=font(F_MONO, int(H * 0.026)),
           fill=TEAL, anchor="ra")

    # progress rail: how far through the story this frame is
    y = int(H * 0.905)
    x0, x1 = pad, W - pad
    d.line([x0, y, x1, y], fill=LINE, width=3)
    if total > 1:
        d.line([x0, y, x0 + int((x1 - x0) * (step / float(total - 1))), y], fill=TEAL, width=3)
    for i in range(total):
        cx = x0 + int((x1 - x0) * (i / float(max(1, total - 1))))
        r = 6 if i == step else 4
        d.ellipse([cx - r, y - r, cx + r, y + r], fill=(TEAL if i <= step else LINE))
    d.text((x0, int(H * 0.945)), "09 – 31 July 2026   ·   109 releases   ·   one command to ship",
           font=font(F_REG, int(H * 0.024)), fill=MUTED)
    return img


def wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def title_frame(W, H):
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    pad = int(W * 0.055)
    brand(d, W, H)

    d.text((W // 2, int(H * 0.245)), "cybergod.ai", font=font(F_BOLD, int(H * 0.135)),
           fill=WHITE, anchor="ma")
    d.text((W // 2, int(H * 0.40)), "22 DAYS · 109 RELEASES · ONE IDEA",
           font=font(F_MONO, int(H * 0.036)), fill=GOLD, anchor="ma")

    f = font(F_REG, int(H * 0.036))
    for i, ln in enumerate((CREED_1, CREED_2, CREED_3)):
        d.text((W // 2, int(H * 0.52) + i * int(H * 0.062)), ln, font=f,
               fill=(MUTED if i == 0 else WHITE), anchor="ma")

    diamond(d, W // 2, int(H * 0.815), int(H * 0.016), TEAL)
    d.text((W // 2, int(H * 0.875)), "Here is everything we built.",
           font=font(F_BOLD, int(H * 0.038)), fill=TEAL, anchor="ma")
    return img


def milestone_frame(W, H, idx, total):
    date, headline, bullets = MILESTONES[idx]
    img = chrome(bg(W, H), W, H, idx, total)
    d = ImageDraw.Draw(img)
    pad = int(W * 0.055)

    d.text((pad, int(H * 0.215)), date, font=font(F_MONO, int(H * 0.048)), fill=GOLD)
    d.line([pad, int(H * 0.285), pad + int(W * 0.20), int(H * 0.285)], fill=TEAL, width=3)
    d.text((pad, int(H * 0.315)), headline, font=font(F_BOLD, int(H * 0.082)), fill=WHITE)

    fb = font(F_REG, int(H * 0.038))
    y = int(H * 0.475)
    for b in bullets:
        for j, ln in enumerate(wrap(d, b, fb, W - 2 * pad - int(W * 0.045))):
            if j == 0:
                tri(d, pad + int(W * 0.008), y + int(H * 0.012), int(H * 0.026), TEAL)
            d.text((pad + int(W * 0.045), y), ln, font=fb, fill=WHITE if j == 0 else MUTED)
            y += int(H * 0.052)
        y += int(H * 0.022)
    return img


def closing_frame(W, H):
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    pad = int(W * 0.055)
    brand(d, W, H)

    d.text((W // 2, int(H * 0.17)), "ONE INPUT: A COMPANY NAME",
           font=font(F_MONO, int(H * 0.034)), fill=GOLD, anchor="ma")
    for i, ln in enumerate(("Your whole internet-facing estate.",
                            "Priced in euros. Mapped to NIS2, CRA and the AI Act.",
                            "Minutes, not weeks. Nothing ever touches your systems.")):
        d.text((W // 2, int(H * 0.27) + i * int(H * 0.075)), ln,
               font=font(F_BOLD, int(H * 0.052)), fill=WHITE, anchor="ma")

    stats = [("109", "releases"), ("22", "days"), ("5", "deliverables"), ("$0.53", "AI cost, lifetime")]
    n = len(stats)
    for i, (big, small) in enumerate(stats):
        cx = int(W * (0.5 + (i - (n - 1) / 2.0) * 0.21))
        d.text((cx, int(H * 0.575)), big, font=font(F_BOLD, int(H * 0.085)), fill=TEAL, anchor="ma")
        d.text((cx, int(H * 0.685)), small, font=font(F_REG, int(H * 0.028)), fill=MUTED, anchor="ma")

    d.line([int(W * 0.30), int(H * 0.775), int(W * 0.70), int(H * 0.775)], fill=LINE, width=2)
    d.text((W // 2, int(H * 0.805)), "See it work — cybergod.ai/demo",
           font=font(F_BOLD, int(H * 0.046)), fill=TEAL, anchor="ma")
    d.text((W // 2, int(H * 0.888)),
           "Colt employees & Colt Partners · jevgenijs.vainsteins@colt.net",
           font=font(F_REG, int(H * 0.028)), fill=MUTED, anchor="ma")
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--square", action="store_true", help="1080x1080 instead of 1200x675")
    ap.add_argument("--seconds", type=float, default=3.6, help="seconds per frame (default 3.6)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    W, H = (1080, 1080) if a.square else (1200, 675)
    out = a.out or os.path.join(HERE, "cybergod_releases%s.gif" % ("_square" if a.square else ""))

    total = len(MILESTONES)
    frames = [title_frame(W, H)]
    frames += [milestone_frame(W, H, i, total) for i in range(total)]
    frames.append(closing_frame(W, H))

    # GIF is 256 colours. Quantising ONCE to a shared adaptive palette keeps the flat brand colours
    # clean and stops the file ballooning — per-frame palettes would also make the teal shimmer.
    pal = frames[0].quantize(colors=128, method=Image.MEDIANCUT)
    frames = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]

    ms = int(a.seconds * 1000)
    durations = [ms + 900] + [ms] * total + [ms + 1800]     # linger on the title and the close
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=2)
    kb = os.path.getsize(out) / 1024.0
    print("[gif] %s" % out)
    print("[gif] %dx%d · %d frames · %.1fs/frame · %.0fs total · %.0f KB"
          % (W, H, len(frames), a.seconds, sum(durations) / 1000.0, kb))
    if kb > 5120:
        print("[gif] WARNING: over LinkedIn's ~5 MB limit — lower --seconds or use --square")
    return 0


if __name__ == "__main__":
    sys.exit(main())
