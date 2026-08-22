#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_onepager.py — the one page you attach to every outreach message.

    python marketing/campaign/build_onepager.py            # writes Cybergod_OnePager_EN.pdf
    python marketing/campaign/build_onepager.py --png      # also renders a PNG to LOOK at

WHY THIS EXISTS SEPARATELY FROM THE PITCH DECK. A deck is what you present. This is what somebody
opens on a phone, inside LinkedIn, between two meetings, having never heard of us. It gets about
twenty seconds, so it makes ONE argument and it makes it visually:

    You cannot sell security to a company that believes it is already secure.

The whole page is the before and after of a single sales call. Everything that is not that was cut,
including the architecture, the model chain, the languages and the compliance regimes, all of which
are true and none of which change anybody's Tuesday.

THE PALETTE IS READ OUT OF THE S4BIZ DESIGN SYSTEM, NOT INVENTED.
The first version used #0F1117, a near-black I chose myself, with no logo and nothing tying it to
either company. Source of truth is `webapp/frontend/src/styles.css` in the S4biz site, whose own
comment says the near-black version "read as heavy and generic" and was deliberately replaced with
a deep INDIGO canvas so bright panels look like they belong to the page. Every value below is
copied from those CSS variables, so if the brand moves, this moves with it.

    --ink #0c1233 canvas · --ink-3 #182254 card · --txt #f2f3ff · --muted #aeb8e0
    --cyan #22d3ee · --violet #8b5cf6 · --indigo #4f46e5 · --magenta #c026d3

TWO RULES FROM THAT FILE ARE LOAD-BEARING AND ARE OBEYED HERE:
  * MAGENTA IS A SURFACE COLOUR, NOT A TEXT COLOUR. Measured at 3.88:1 on the canvas, which fails
    body text. It appears as a fill or a rule. Where magenta text is wanted the value is
    --magenta-lt #e879f9 at 7.4:1.
  * CYAN AS A SOLID FILL MEANS "ACT ON THIS" and is spent once, on the offer band at the bottom.
    Share that fill with headings or chips and the single most distinct element on the page stops
    being distinct.

THE MARK IS THE REAL ONE. assets/s4biz_mark.svg carries the exact path data from the site's
Logo.jsx and the exact gradient stops, rendered through cairosvg. Redrawing it by hand would be a
second copy of the logo that drifts the first time the real one changes.

NO PRICES. A number on a page that gets forwarded is a negotiating position given away before the
first call. The only figure here is the PROSPECT's loss, which is the argument itself.
"""
import argparse
import os
import subprocess
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H = A4

# ONE list, imported rather than copied. A second copy of the banned-vendor list is how the page
# and the outreach copy end up disagreeing about the rule.
sys.path.insert(0, HERE)
from messages import DEMO, VENDOR_NAMES                                        # noqa: E402

# --------------------------------------------------------------------------- palette (styles.css)
INK      = HexColor("#0C1233")   # --ink        page canvas, a deep indigo
INK3     = HexColor("#182254")   # --ink-3      raised card
TXT      = HexColor("#F2F3FF")   # --txt        16.6:1 on the canvas
MUTED    = HexColor("#AEB8E0")   # --muted       9.3:1  body secondary
FAINT    = HexColor("#98A3CE")   # --faint       7.4:1  labels
CYAN     = HexColor("#22D3EE")
CYAN_BR  = HexColor("#67E8F9")
VIOLET   = HexColor("#8B5CF6")
INDIGO   = HexColor("#4F46E5")
MAGENTA  = HexColor("#C026D3")   # SURFACE ONLY, 3.88:1
MAG_LT   = HexColor("#E879F9")   # the text-safe magenta, 7.4:1
LINE     = HexColor("#39406B")   # rgba(255,255,255,.14) resolved over the canvas
WHITE    = HexColor("#FFFFFF")   # --field-ink, measured against the worst field stop

# Inter, Unbounded and JetBrains Mono are not installed here. Helvetica is metric-compatible with
# the grotesque body face; the MONO is registered from a real TTF because the spaced monospace
# eyebrow is a signature of the S4biz decks and Courier would read as a typewriter, not a terminal.
B, R = "Helvetica-Bold", "Helvetica"
MONO, MONO_B = R, B
for _p, _n in ((("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
                 "C:/Windows/Fonts/consola.ttf"), "S4Mono"),
               (("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf",
                 "C:/Windows/Fonts/consolab.ttf"), "S4MonoB")):
    for _f in _p:
        if os.path.exists(_f):
            try:
                pdfmetrics.registerFont(TTFont(_n, _f))
                if _n == "S4Mono":
                    MONO = _n
                else:
                    MONO_B = _n
                break
            except Exception:
                pass


def mark_png():
    """The S4Biz shield, rendered from the site's own SVG. None if it cannot be produced, and the
    page then simply omits it rather than failing: a missing logo is a blemish, not an outage."""
    png = os.path.join(ASSETS, "s4biz_mark.png")
    svg = os.path.join(ASSETS, "s4biz_mark.svg")
    if os.path.exists(png):
        return png
    if not os.path.exists(svg):
        return None
    try:
        import cairosvg
        cairosvg.svg2png(url=svg, write_to=png, output_width=512, output_height=512)
        return png
    except Exception as e:
        print("[warn] logo not rendered (%s: %s)" % (type(e).__name__, e))
        return None


# --------------------------------------------------------------------------- drawing helpers
def wrap(c, text, font, size, width):
    """Greedy wrap against the REAL measured string width, never a character estimate. The findings
    deck already paid for the guess-the-width version with 46 truncated boxes."""
    out, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if stringWidth(trial, font, size) <= width:
            line = trial
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out


def para(c, text, x, y, width, font=R, size=9.5, lead=13, colour=MUTED):
    c.setFillColor(colour)
    for ln in wrap(c, text, font, size, width):
        c.setFont(font, size)
        c.drawString(x, y, ln)
        y -= lead
    return y


def card(c, x, y, w, h, fill=INK3, stroke=LINE, r=10):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.9)
    c.roundRect(x, y, w, h, r, stroke=1, fill=1)


def tracked(c, text, x, y, font, size, colour, track=1.6):
    """Letter-spaced text. The mono eyebrow with wide tracking is the single most recognisable
    element of the S4biz layout and reportlab has no tracking, so it is drawn glyph by glyph."""
    c.setFont(font, size)
    c.setFillColor(colour)
    for ch in text:
        c.drawString(x, y, ch)
        x += stringWidth(ch, font, size) + track
    return x


def tracked_w(text, font, size, track=1.6):
    return sum(stringWidth(ch, font, size) + track for ch in text) - track


def grad_text(c, text, x, y, font, size, stops):
    """Text filled with the brand gradient, via a text clip path. This is how the wordmark keeps
    cyan-to-violet-to-indigo instead of collapsing to one flat colour."""
    c.saveState()
    t = c.beginText(x, y)
    t.setTextRenderMode(7)                       # add to clip, paint nothing
    t.setFont(font, size)
    t.textOut(text)
    c.drawText(t)
    wdt = stringWidth(text, font, size)
    c.linearGradient(x, y, x + wdt, y + size, stops, extend=True)
    c.restoreState()
    return x + wdt


def field(c, x, y, w, h, r=12):
    """--field: the bright brand panel. Linear indigo base, cyan glow from the top left, magenta
    glow from the bottom right. Text on it is PURE WHITE, which styles.css measured rather than
    chose: an off-white drops to 4.27:1 against the magenta stop and fails."""
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(x, y + h, x + w, y,
                     [HexColor("#4F46E5"), HexColor("#5B3BD4"), HexColor("#3B2E9E")],
                     positions=[0, 0.52, 1], extend=True)
    c.setFillAlpha(0.34)
    c.radialGradient(x + w * 0.10, y + h * 1.12, max(w, h) * 0.62,
                     [HexColor("#22D3EE"), HexColor("#22D3EE")], positions=[0, 1])
    c.setFillAlpha(0.40)
    c.radialGradient(x + w * 1.02, y - h * 0.10, max(w, h) * 0.58,
                     [HexColor("#C026D3"), HexColor("#C026D3")], positions=[0, 1])
    c.setFillAlpha(1)
    c.restoreState()
    c.setStrokeColor(HexColor("#6D5BF0"))
    c.setLineWidth(0.9)
    c.roundRect(x, y, w, h, r, stroke=1, fill=0)


# --------------------------------------------------------------------------- the page
def build(path):
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle("cybergod.ai - stop selling discovery")
    c.setAuthor("Cybergod LLC / S4Biz Group")
    c.setFillColor(INK)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    M = 38.0
    CW = W - 2 * M

    # top rule: the brand gradient, edge to edge
    c.linearGradient(0, H - 4, W, H, [CYAN, VIOLET, INDIGO], positions=[0, 0.55, 1], extend=True)
    c.setFillColor(INK)
    c.rect(0, 0, W, H - 4, stroke=0, fill=1)

    # ---------------------------------------------------------------- masthead
    y = H - 46
    mk = mark_png()
    wx = M
    if mk:
        c.drawImage(ImageReader(mk), M - 3, y - 8, 30, 30, mask="auto")
        wx = M + 32
    # "S4" is solid light and "Biz" carries the gradient, which is how the real lockup reads.
    c.setFillColor(TXT)
    c.setFont(B, 17)
    c.drawString(wx, y, "S4")
    grad_text(c, "Biz", wx + stringWidth("S4", B, 17), y, B, 17, [CYAN, VIOLET, INDIGO])
    c.setFillColor(FAINT)
    c.setFont(R, 9)
    c.drawString(wx + stringWidth("S4Biz", B, 17) + 9, y + 1, "|")
    c.setFillColor(TXT)
    c.setFont(B, 12.4)
    c.drawString(wx + stringWidth("S4Biz", B, 17) + 18, y + 1, "cybergod.ai")
    tracked(c, "SALES ENABLEMENT", W - M - tracked_w("SALES ENABLEMENT", MONO_B, 7.6, 1.5),
            y + 3, MONO_B, 7.6, CYAN, 1.5)

    # ---------------------------------------------------------------- headline
    y -= 30
    tracked(c, "> cybergod --company \"acme gmbh\"", M, y, MONO, 8.2, FAINT, 0.5)
    y -= 30
    c.setFillColor(TXT)
    c.setFont(B, 21.5)
    c.drawString(M, y, "YOU CANNOT SELL SECURITY TO A COMPANY")
    y -= 26
    grad_text(c, "THAT BELIEVES IT IS ALREADY SECURE.", M, y, B, 21.5,
              [CYAN, VIOLET, MAG_LT])
    y -= 21
    y = para(c, "So stop asking. Start showing. This page is one sales call, before and after.",
             M, y, CW, R, 10.2, 14, MUTED) - 12

    # ---------------------------------------------------------------- the two panels
    PH = 190.0
    PW = (CW - 16) / 2.0
    ptop, pbot = y, y - PH

    def panel(px, accent, eyebrow, steps, footer):
        card(c, px, pbot, PW, PH)
        c.setFillColor(accent)
        c.rect(px, pbot + PH - 3, PW, 3, stroke=0, fill=1)
        ix, iy, iw = px + 15, ptop - 23, PW - 30
        tracked(c, eyebrow, ix, iy, MONO_B, 7.4, accent if accent is not MAGENTA else MAG_LT, 1.3)
        iy -= 21
        for n, (h, s) in enumerate(steps, 1):
            c.setFillColor(FAINT)
            c.setFont(MONO_B, 8.4)
            c.drawString(ix, iy, "%02d" % n)
            c.setFillColor(TXT)
            c.setFont(B, 9.3)
            c.drawString(ix + 17, iy, h)
            iy -= 12
            iy = para(c, s, ix + 17, iy, iw - 17, R, 8.4, 11.4, MUTED) - 11
        c.setFillColor(accent if accent is not MAGENTA else MAG_LT)
        c.setFont(B, 8.8)
        c.drawString(ix, pbot + 14, footer)

    panel(M, MAGENTA, "HOW THE CALL GOES TODAY", [
        ("Book the discovery call.", "Two weeks out, if they take it."),
        ("Ask the three questions.", "What keeps you up at night. What are your pain points. "
                                     "What are your security projects this year."),
        ("Get the answer everyone gets.", "“Thanks, we are covered. Vendor X handles it. "
                                          "Call us back in six months.”"),
    ], "Six months later, the same call.")

    panel(M + PW + 16, CYAN, "HOW IT GOES WITH CYBERGOD.AI", [
        ("Type their company name.", "That is the whole input. Three minutes."),
        ("Open with a fact, not a question.", "Their exposed systems, named, with the host and "
                                              "port behind each one, and what a breach costs them."),
        ("Get a different answer.", "“Who else can see this? Can you show my board?”"),
    ], "Meeting. Demo. Remediation. Upsell.")

    # ---------------------------------------------------------------- the opening line
    y = pbot - 16
    # VENDOR-NEUTRAL. This named Palo Alto until 2026-08-22. A reader who runs Fortinet stops
    # reading a line about somebody else's kit, and to a security vendor it reads as a dig at a
    # competitor. "Firewall VPN" is what all of them are, so one sentence covers the whole room.
    # messages.py::VENDOR_NAMES holds the list and its --check enforces the same rule on the
    # outreach copy, so the page and the message cannot drift apart.
    QUOTE = ("“Mr Weber, your firewall VPN is reachable from the internet. If it goes, six "
             "hundred people cannot log in. A day of that is about 120,000 euro, before anyone "
             "talks about a ransom.”")
    for _v in VENDOR_NAMES:
        if _v in QUOTE.lower():
            raise SystemExit("[X] the one-pager names a firewall vendor (%r). Keep it neutral."
                             % _v)
    QLEAD = 15.2
    # SIZE THE BOX FROM THE TEXT, never the other way round. A hardcoded height leaves dead space
    # when the quote is short and clips it when somebody lengthens it.
    qlines = len(wrap(c, QUOTE, B, 10.8, CW - 44))
    QH = 22 + 16 + qlines * QLEAD + 12
    field(c, M, y - QH, CW, QH)
    qy = y - 22
    tracked(c, "THE FIRST SENTENCE OUT OF YOUR MOUTH", M + 20, qy, MONO_B, 7.6,
            HexColor("#A5F3FC"), 1.3)
    para(c, QUOTE, M + 20, qy - 19, CW - 44, B, 10.8, QLEAD, WHITE)
    y = y - QH - 20

    # ---------------------------------------------------------------- what changes
    c.setFillColor(TXT)
    c.setFont(B, 10.6)
    c.drawString(M, y, "What actually changes")
    y -= 19
    c1, c2 = M + 150, M + 150 + (CW - 150) / 2.0
    tracked(c, "DISCOVERY-LED", c1, y, MONO_B, 7.4, FAINT, 1.2)
    tracked(c, "EVIDENCE-LED", c2, y, MONO_B, 7.4, CYAN, 1.2)
    y -= 4
    for label, a, bb in [
        ("The first call", "You ask them to confess a weakness", "You show them one"),
        ("Their reply", "Call back in six months", "Who else can see this"),
        ("Time to a real meeting", "Weeks, and usually never", "That call"),
        ("What you are selling", "A product they did not ask for", "A fix for a named problem"),
    ]:
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(M, y, W - M, y)
        y -= 15
        c.setFillColor(MUTED)
        c.setFont(R, 8.7)
        c.drawString(M, y, label)
        c.setFillColor(FAINT)
        c.drawString(c1, y, a)
        c.setFillColor(TXT)
        c.setFont(B, 8.7)
        c.drawString(c2, y, bb)
        y -= 6
    c.setStrokeColor(LINE)
    c.line(M, y, W - M, y)
    y -= 20

    # ---------------------------------------------------------------- the four facts
    facts = [("ONE INPUT", "A company name. Nothing else to gather.", CYAN),
             ("THREE MINUTES", "Four decks and an animated report.", VIOLET),
             ("YOUR BRAND", "Your logo, colours and fonts. Not ours.", MAG_LT),
             ("ZERO PACKETS", "Nothing is sent to them. No permission needed.", CYAN_BR)]
    FW = (CW - 3 * 9) / 4.0
    FH = 66.0
    for i, (h, s, col) in enumerate(facts):
        fx = M + i * (FW + 9)
        card(c, fx, y - FH, FW, FH)
        c.setFillColor(col)
        c.rect(fx, y - FH, 2.5, FH, stroke=0, fill=1)
        tracked(c, h, fx + 12, y - 18, MONO_B, 7.6, col, 1.2)
        para(c, s, fx + 12, y - 32, FW - 22, R, 8.0, 10.6, MUTED)
    y -= FH + 18

    # ---------------------------------------------------------------- the offer
    # THE ONE SOLID CYAN OBJECT ON THE PAGE. styles.css reserves that fill for the call to action,
    # because what converts is being the single most distinct element rather than any given hue.
    OH = 70.0
    c.setFillColor(CYAN)
    c.roundRect(M, y - OH, CW, OH, 12, stroke=0, fill=1)
    c.setFillColor(HexColor("#04102A"))          # --cta-ink
    c.setFont(B, 13.2)
    c.drawString(M + 20, y - 27, "Name one company you are chasing.")
    # THE DURATION IS IMPORTED, NOT RETYPED. This page said "fifteen minutes" while messages.py
    # said twenty, which is the two-homes drift the shared close was created to prevent, one file
    # over. The partner deck states twenty, so messages.py is the authority and this reads it.
    offer = ("Their report lands in 48 hours. Free, no contract, no access to anything. Judge the "
             "artifact, not the description. Then %s with the architect, not a salesperson."
             % ("twenty minutes" if "twenty minutes" in DEMO else "a short call"))
    para(c, offer, M + 20, y - 43, CW - 40, R, 9.0, 12.2, HexColor("#0B2740"))
    y -= OH + 14

    # ---------------------------------------------------------------- footer
    # A FIXED ROW IS AN ARITHMETIC PROBLEM. The first version put a 41-character line and a
    # 40-character line in a 519pt row at 7.2pt mono with 0.9 tracking, and they overlapped in the
    # middle. This repo has already paid for that twice on the site header. Measure, then draw.
    head = "CYBERGOD LLC  ·  S4BIZ GROUP  ·  EN / DE / RU"
    tail = "CYBERGOD.AI  ·  FERANICUS@S4BIZ.IO"
    hw = tracked_w(head, MONO, 7.2, 0.9)
    tw = tracked_w(tail, MONO, 7.2, 0.9)
    if hw + tw + 24 > CW:
        raise SystemExit("[X] footer row is %.0fpt of %.0fpt available. Shorten one side."
                         % (hw + tw + 24, CW))
    # And keep it off the paper edge: a line at y<26 gets clipped by most printers and looks
    # broken in a PDF viewer's page shadow.
    # NEVER CLAMP AN OVERFLOW. The first fix pinned the footer to y=30 and it printed straight
    # through the offer band, which is a worse defect than the one it replaced because it looks
    # deliberate. Fail the build instead and shorten the content.
    if y < 56:
        raise SystemExit('[X] content overruns the footer by %.0fpt. Tighten a section; do NOT\n'
                         '    clamp the footer, it will print over the offer band.' % (56 - y))
    fy = y - 7
    c.setStrokeColor(LINE)
    c.line(M, fy + 13, W - M, fy + 13)
    tracked(c, head, M, fy, MONO, 7.2, FAINT, 0.9)
    tracked(c, tail, W - M - tw, fy, MONO, 7.2, FAINT, 0.9)

    c.showPage()
    c.save()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="store_true", help="also render a PNG so it can be LOOKED at")
    ap.add_argument("--out", default=os.path.join(HERE, "Cybergod_OnePager_EN.pdf"))
    a = ap.parse_args()
    p = build(a.out)
    print("wrote %s  (%.0f KB)" % (p, os.path.getsize(p) / 1024.0))
    print("      mono=%s  logo=%s" % (MONO, "yes" if mark_png() else "MISSING"))
    if a.png:
        # RENDER IT AND LOOK. A layout that is correct in code can still be unreadable on the page.
        png = p[:-4] + ".png"
        r = subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", p, p[:-4]],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("png: %s" % (png if os.path.exists(png) else "FAILED " + (r.stderr or r.stdout)[:200]))


if __name__ == "__main__":
    main()
