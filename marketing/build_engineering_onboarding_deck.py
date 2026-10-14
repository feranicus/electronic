"""build_engineering_onboarding_deck.py - S4biz-format onboarding deck for a new developer.

WHY THIS EXISTS. A second developer has to hold four things in his head before he can touch
anything: the two droplets and what runs on each, what `python ship.py` actually does and what it
calls, the full test scope, and how the four-model chain works. Those facts live in code, in
CLAUDE.md and in incident history. This script renders them as one deck so they can be handed over
in an hour instead of a week.

DESIGN IS INHERITED, NOT RE-CREATED. S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx is opened as
the template: its gradient background image and its drawn S4biz mark are copied onto every slide,
and the palette and fonts are the ones measured out of that file
(22D3EE cyan / 8B5CF6 violet / 4F46E5 indigo / 14161F / 1B1F2C cards / C7CDDA body / 8E97A8 muted;
Arial Black headlines, Arial body, Consolas labels).

DIAGRAMS ARE SHAPES, NOT PICTURES. Every architecture and flow diagram is drawn from PowerPoint
autoshapes and block arrows, so the developer can open the deck and edit a box (Visio-style).

EVERY NUMBER IS TRACED. The facts below carry the file and symbol they were read from; nothing here
is estimated. Where the committed code default and the deployed environment value differ, BOTH are
shown and labelled, because a developer who reads only one of them will mis-diagnose a timeout.

    python marketing/build_engineering_onboarding_deck.py [out.pptx]
"""
import copy
import io
import os
import sys
import zipfile

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "S4biz_Cybergod_Engineering_Onboarding.pptx")

# ---- palette + type, measured from the Capability Brief -----------------------------------------
CYAN, VIOLET, INDIGO = "22D3EE", "8B5CF6", "4F46E5"
INK, CARD, CARD2 = "14161F", "1B1F2C", "2B3042"
BODY, MUTED, WHITE = "C7CDDA", "8E97A8", "FFFFFF"
RED, AMBER, GOLD = "FF4D6D", "FF9F1C", "FFD23F"
HB, BF, MONO = "Arial Black", "Arial", "Consolas"

W, H = 13.333, 7.5
MARK_IDS = {2, 3, 4, 5}          # 'S4BIZ' + three chevrons, top right of the brief


def rgb(h):
    return RGBColor.from_string(h)


# ---- template harvesting -------------------------------------------------------------------------
def _harvest(path):
    """(background PNG bytes, [deep-copied logo shape elements]) from slide 2 of the brief."""
    with zipfile.ZipFile(path) as z:
        bg = z.read("ppt/media/Slide-2-image-1.png")
    src = Presentation(path).slides[1]
    mark = [copy.deepcopy(sh._element) for sh in src.shapes if sh.shape_id in MARK_IDS]
    return bg, mark


class Deck:
    def __init__(self):
        self.bg, self.mark = _harvest(TEMPLATE)
        self.p = Presentation()
        self.p.slide_width, self.p.slide_height = Inches(W), Inches(H)
        self.n = 0

    # -- primitives --------------------------------------------------------------------------------
    def _text(self, s, x, y, w, h, txt, size, color, font=BF, bold=False, italic=False,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=0, wrap=True):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = wrap
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        lines = txt.split("\n") if isinstance(txt, str) else list(txt)
        for i, ln in enumerate(lines):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.alignment = align
            r = par.add_run()
            r.text = ln
            f = r.font
            f.size, f.name, f.bold, f.italic = Pt(size), font, bold, italic
            f.color.rgb = rgb(color)
            if space:
                from pptx.oxml.ns import qn
                r.font._rPr.set("spc", str(int(space * 100)))
        return tb

    def _rect(self, s, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE, lw=1.0):
        sp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill is None:
            sp.fill.background()
        else:
            sp.fill.solid()
            sp.fill.fore_color.rgb = rgb(fill)
        if line:
            sp.line.color.rgb = rgb(line)
            sp.line.width = Pt(lw)
        else:
            sp.line.fill.background()
        sp.shadow.inherit = False
        if sp.has_text_frame:
            sp.text_frame.word_wrap = True
        return sp

    # -- slide chrome ------------------------------------------------------------------------------
    def slide(self, eyebrow, headline, sub=None, footer="S4BIZ ENGINEERING  ·  CYBERGOD.AI STACK  ·  INTERNAL"):
        self.n += 1
        s = self.p.slides.add_slide(self.p.slide_layouts[6])
        s.shapes.add_picture(io.BytesIO(self.bg), 0, 0, Inches(W), Inches(H))
        for el in self.mark:
            s.shapes._spTree.append(copy.deepcopy(el))
        self._text(s, 0.55, 0.30, 9.5, 0.26, eyebrow.upper(), 9, CYAN, MONO, True, space=2.2)
        self._text(s, 0.55, 0.58, 11.0, 0.62, headline, 30, WHITE, HB)
        y = 1.26
        if sub:
            self._text(s, 0.55, 1.22, 11.6, 0.3, sub, 11.5, MUTED, BF, italic=True)
            y = 1.68
        self._text(s, 0.55, 7.04, 10.5, 0.3, footer, 7.5, MUTED, MONO, space=1.8)
        self._text(s, 11.93, 7.04, 0.85, 0.3, ">> %02d" % self.n, 7.5, MUTED, MONO,
                   align=PP_ALIGN.RIGHT)
        return s, y

    # -- diagram pieces ----------------------------------------------------------------------------
    def card(self, s, x, y, w, h, title, lines=(), accent=CYAN, fill=CARD, tsize=10.5, lsize=8.2):
        self._rect(s, x, y, w, h, fill, accent, lw=1.0)
        self._rect(s, x, y, 0.055, h, accent)
        self._text(s, x + 0.18, y + 0.12, w - 0.3, 0.24, title, tsize, WHITE, BF, True)
        if lines:
            self._text(s, x + 0.18, y + 0.44, w - 0.3, h - 0.56, list(lines), lsize, BODY, BF)

    def node(self, s, x, y, w, h, title, sub="", accent=CYAN, fill=CARD2, tsize=9.5):
        self._rect(s, x, y, w, h, fill, accent, lw=1.25)
        self._text(s, x, y + (0.12 if sub else (h - 0.2) / 2), w, 0.22, title, tsize, WHITE, BF,
                   True, align=PP_ALIGN.CENTER)
        if sub:
            self._text(s, x, y + 0.36, w, h - 0.44, sub, 7.4, MUTED, MONO, align=PP_ALIGN.CENTER)

    def arrow_r(self, s, x, y, w, color=VIOLET, h=0.14):
        self._rect(s, x, y, w, h, color, shape=MSO_SHAPE.RIGHT_ARROW)

    def arrow_d(self, s, x, y, h, color=VIOLET, w=0.14):
        self._rect(s, x, y, w, h, color, shape=MSO_SHAPE.DOWN_ARROW)

    def line(self, s, x, y, w, h, color=INDIGO):
        self._rect(s, x, y, max(w, 0.014), max(h, 0.014), color)

    def tag(self, s, x, y, w, txt, bg, fg=INK, h=0.24, size=7.6):
        self._rect(s, x, y, w, h, bg)
        self._text(s, x, y + 0.04, w, h, txt, size, fg, BF, True, align=PP_ALIGN.CENTER)

    def save(self, path):
        self.p.save(path)
        return path


# =================================================================================================
d = Deck()

# -- 01 title --------------------------------------------------------------------------------------
s = d.p.slides.add_slide(d.p.slide_layouts[6])
d.n = 1
s.shapes.add_picture(io.BytesIO(d.bg), 0, 0, Inches(W), Inches(H))
for el in d.mark:
    s.shapes._spTree.append(copy.deepcopy(el))
d._text(s, 0.55, 0.30, 9.5, 0.26, "S4BIZ  ·  CYBERGOD.AI  ·  ENGINEERING ONBOARDING", 9, CYAN, MONO,
        True, space=2.2)
d._text(s, 0.55, 2.05, 8.6, 0.6, "> whoami  --role engineer", 11, VIOLET, MONO)
d._text(s, 0.55, 2.45, 11.8, 1.9, ["THE STACK,", "END TO END."], 54, WHITE, HB)
d._text(s, 0.55, 4.35, 10.4, 0.3,
        "Two droplets · one orchestrator · 1,000+ automated checks · four models that never decide.",
        13, BODY, BF)
for i, (t, sub, c) in enumerate([
        ("A", "Estate\nTest DO + Prod DO", CYAN),
        ("B", "Pipeline\npython ship.py", VIOLET),
        ("C", "Test scope\nwhat must pass", INDIGO),
        ("D", "4 LLMs\npropose, never decide", CYAN)]):
    x = 0.55 + i * 3.02
    d._rect(s, x, 5.05, 2.82, 1.0, CARD, c, lw=1.25)
    d._rect(s, x, 5.05, 2.82, 0.05, c)
    d._text(s, x + 0.2, 5.2, 0.5, 0.3, t, 15, c, HB)
    d._text(s, x + 0.2, 5.56, 2.5, 0.42, sub, 8.4, BODY, BF)
d._text(s, 0.55, 7.04, 10.5, 0.3,
        "STARS4BUSINESS OU  ·  CYBERGOD LLC  ·  INTERNAL  ·  NOT FOR EXTERNAL DISTRIBUTION",
        7.5, MUTED, MONO, space=1.8)
d._text(s, 11.93, 7.04, 0.85, 0.3, ">> 01", 7.5, MUTED, MONO, align=PP_ALIGN.RIGHT)

# -- 02 the estate ---------------------------------------------------------------------------------
s, y = d.slide("A · THE ESTATE", "Two droplets, built identical on purpose.",
               "Staging is a real second machine, same size, same region. That is what makes its reboot test mean something.")
d.node(s, 0.55, 1.75, 5.6, 0.72, "PRODUCTION  ·  64.225.108.200",
       "FRA1 · 4 GB · 2 AMD vCPU · 80 GB · Ubuntu 24.04", CYAN, INDIGO, 11)
d.node(s, 7.18, 1.75, 5.6, 0.72, "STAGING TWIN  ·  165.245.244.174",
       "FRA1 · 4 GB · 2 AMD vCPU · 80 GB · same image", VIOLET, CARD2, 11)
d.card(s, 0.55, 2.72, 5.6, 1.62, "Runs the live product", [
    "colt-web · FastAPI + React, 127.0.0.1:8090",
    "colt-assessbot · Telegram assessment bot",
    "colt-cassandra · Telegram assistant bot",
    "colt-promtail · ships logs to shared Loki",
    "Shares the box with Amnezia VPN, VideoDead,",
    "jobhuntwow, jev, klima, s4biz. Never disturb them."], CYAN)
d.card(s, 7.18, 2.72, 5.6, 1.62, "Runs the release gate", [
    "Same stack, deployed by the SAME script",
    "(deploy_web_direct.py with DROPLET_HOST set)",
    "Its own staging-caddy on :8080",
    "Gets rebooted on every ship. Production",
    "can never be rebooted to prove a config,",
    "so the twin does it instead."], VIOLET)
d.card(s, 0.55, 4.52, 5.6, 1.34, "Shared, and therefore fragile", [
    "videodead-caddy-1 owns :443 for EVERY domain",
    "videodead-loki-1 is the only thing holding the PAST",
    "Its death is a total outage, never an app fault"], RED)
d.card(s, 7.18, 4.52, 5.6, 1.34, "Secrets never travel through git", [
    "assess-bot/.env on the droplet, chmod 600",
    "The gate copies it prod -> staging over ssh",
    "python set_secret.py NAME · value on stdin"], AMBER)
d._text(s, 0.55, 6.08, 12.2, 0.6,
        "Read the spec, never the name: the production droplet is still called "
        "ubuntu-s-1vcpu-1gb-fra1-01 because that is the size it was created at.",
        9, MUTED, BF, italic=True)

# -- 03 production topology (Visio) ------------------------------------------------------------------
s, y = d.slide("A · PRODUCTION TOPOLOGY", "What actually runs on 64.225.108.200.",
               "Boxes are containers, lines are networks, the grey slab is the shared volume. Everything here is editable.")
d._text(s, 0.55, 1.72, 2.4, 0.22, "INTERNET", 8, CYAN, MONO, True, space=1.6)
d.node(s, 0.55, 1.98, 2.3, 0.62, "clients", ":443", CYAN, CARD)
d.arrow_r(s, 2.95, 2.22, 0.5)
d.node(s, 3.55, 1.90, 2.6, 0.78, "videodead-caddy-1", "shared reverse proxy\nowns :443 for 6 domains", RED)
d.arrow_r(s, 6.28, 2.22, 0.5)
d.node(s, 6.9, 1.90, 2.5, 0.78, "colt-web", "FastAPI + React\n127.0.0.1:8090 -> 8000", CYAN)
d._text(s, 9.55, 1.95, 3.3, 0.7, ["network: videodead_appnet", "image: ghcr.io/feranicus/colt-web"],
        8, MUTED, MONO)
d.line(s, 8.1, 2.72, 0, 0.55, INDIGO)
d.node(s, 3.55, 3.3, 2.5, 0.72, "colt-assessbot", "Telegram · /assess", VIOLET)
d.node(s, 6.9, 3.3, 2.5, 0.72, "colt-cassandra", "Telegram · assistant", VIOLET)
d.node(s, 0.55, 3.3, 2.3, 0.72, "colt-promtail", "log shipper", INDIGO)
d._text(s, 9.55, 3.4, 3.3, 0.5, ["network: colt (own)", "same engine image, 2nd delivery path"],
        8, MUTED, MONO)
d._rect(s, 0.55, 4.35, 8.85, 0.62, CARD2, GOLD, lw=1.25)
d._text(s, 0.75, 4.5, 8.4, 0.3, "VOLUME  colt_events   ·   /var/log/colt   ·   web + both bots + promtail all write here",
        9.5, GOLD, BF, True)
for x in (1.7, 4.8, 8.15):
    d.line(s, x, 4.02, 0, 0.33, GOLD)
d.line(s, 1.7, 4.97, 0, 0.42, INDIGO)
d.arrow_d(s, 1.64, 5.0, 0.38, INDIGO)
d.node(s, 0.55, 5.45, 2.3, 0.62, "videodead-loki-1", "the PAST", INDIGO)
d.card(s, 3.55, 5.12, 5.85, 0.95, "Also on the volume", [
    "colt.sqlite (jobs, users) · cost_ledger.sqlite (books of record)",
    "llm_meter.sqlite (daily cap) · events.log (telemetry, shield, fleet)"], GOLD, CARD, 9.5, 8)
d.card(s, 9.9, 4.35, 2.88, 1.72, "Not ours", [
    "Amnezia VPN",
    "VideoDead",
    "jobhuntwow · jev",
    "klima · s4biz",
    "",
    "Shared host.",
    "No firewall changes."], RED, CARD, 9.5, 8)

# -- 04 staging topology + gate flow (Visio) --------------------------------------------------------
s, y = d.slide("A · THE TEST DROPLET", "The twin, and the decision it produces.",
               "Same commit, same deploy script, its own proxy. Then it is rebooted, which is the one test production can never run.")
d._text(s, 0.55, 1.70, 4.0, 0.22, "STAGING  ·  165.245.244.174", 8.4, VIOLET, MONO, True, space=1.6)
d.node(s, 0.55, 1.98, 2.55, 0.66, "staging-caddy", ":8080 · admin localhost:2019", VIOLET)
d.arrow_r(s, 3.18, 2.24, 0.34, VIOLET)
d.node(s, 3.62, 1.98, 2.45, 0.66, "colt-web", "the shipped image", CYAN)
d._text(s, 0.55, 2.78, 5.5, 0.22, "DEPLOYED BY THE SAME SCRIPT AS PRODUCTION", 8, MUTED, MONO, space=1.4)
d.card(s, 0.55, 3.06, 5.52, 1.42, "What the twin gets", [
    "deploy_web_direct.py --no-proxy, DROPLET_HOST=staging",
    "assess-bot/.env copied prod -> staging over ssh",
    "deploy/caddy/cybergod.caddy, the committed block",
    "deploy/stagegate/quorum.py shipped into colt-web"], VIOLET, CARD, 10, 8.2)
d.card(s, 0.55, 4.62, 5.52, 2.26, "Why a twin at all", [
    "Caddy reads its config only at start. A file damaged at",
    "16:15 keeps serving happily from memory until a 04:22",
    "kernel reboot takes six domains down together.",
    "",
    "So the gate reboots the twin and waits for the boot_id",
    "to CHANGE, not merely for ssh to answer. Then it runs",
    "every check again as post_reboot_*.",
    "",
    "A check that reported before the reboot and goes silent",
    "after it FAILS the gate. 35 of 35 passing while six",
    "checks never reported is the defect that bought this."], CYAN, CARD, 10, 8.2)
flow = [("Deploy the commit to the twin", CYAN),
        ("42 deterministic checks", CYAN),
        ("REBOOT · wait for a new boot_id", RED),
        ("Re-run every check as post_reboot_*", VIOLET),
        ("expected - got  must be empty", VIOLET),
        ("2 soldiers + 2 auditors write a verdict", INDIGO)]
for i, (txt, c) in enumerate(flow):
    yy = 1.98 + i * 0.63
    d._rect(s, 6.55, yy, 5.1, 0.46, CARD, c, lw=1.1)
    d._rect(s, 6.55, yy, 0.05, 0.46, c)
    d._text(s, 6.78, yy + 0.13, 4.8, 0.24, txt, 9.5, WHITE, BF, True)
    if i < len(flow) - 1:
        d.arrow_d(s, 9.03, yy + 0.47, 0.15, c)
d.tag(s, 6.55, 5.84, 2.45, "GO  ->  production", CYAN, INK, 0.34, 9)
d.tag(s, 9.20, 5.84, 2.45, "NO-GO  ->  exit 2", RED, WHITE, 0.34, 9)
d._text(s, 6.55, 6.3, 5.1, 0.6,
        ["The gate is computed from the deterministic checks alone.",
         "The panel can turn a GO into a NO-GO (2+ dissenters, one hard NO-GO).",
         "It can never turn a NO-GO into a GO."], 8.4, MUTED, BF, italic=True)

# -- 04 the pipeline (Visio flow) --------------------------------------------------------------------
s, y = d.slide("B · THE PIPELINE", "One command. python ship.py.",
               "Five numbered phases, a staging gate between 2 and 3, and a tail of infrastructure verbs that never block.")
cols = [("1/5", "TESTS", "nothing ships\nif these fail", CYAN),
        ("2/5", "COMMIT + PUSH", "git is the single\nsource of truth", CYAN),
        ("3/5", "DEPLOY WEB", "cybergod.ai\ncolt-web", VIOLET),
        ("4/5", "DEPLOY BOTS", "colt-stack\nassessbot + cassandra", VIOLET),
        ("5/5", "VERIFY", "hashes, 401, headers,\nbot gate", INDIGO)]
for i, (num, name, sub, c) in enumerate(cols):
    x = 0.55 + i * 2.56
    d._rect(s, x, 1.80, 2.3, 1.22, CARD, c, lw=1.25)
    d._rect(s, x, 1.80, 2.3, 0.05, c)
    d._text(s, x + 0.16, 1.94, 1.0, 0.24, num, 10, c, MONO, True)
    d._text(s, x + 0.16, 2.2, 2.0, 0.26, name, 11, WHITE, BF, True)
    d._text(s, x + 0.16, 2.5, 2.0, 0.44, sub, 7.8, MUTED, BF)
    if i < 4:
        d.arrow_r(s, x + 2.33, 2.34, 0.2, c)
d._rect(s, 5.55, 3.12, 0.1, 0.5, VIOLET)
d._rect(s, 3.11, 3.62, 2.54, 0.1, VIOLET)
d.card(s, 0.55, 3.72, 5.1, 1.5, "STAGING GATE  ·  between 2/5 and 3/5", [
    "Deploys the same commit to the twin, then reboots it",
    "42 deterministic checks, repeated as post_reboot_*",
    "A missing post-reboot check FAILS the gate",
    "NO-GO stops the ship with exit 2. Production untouched."], VIOLET, CARD, 10, 8.2)
d.card(s, 6.05, 3.72, 6.73, 1.5, "After 5/5  ·  never blocking, always run", [
    "caddyguard.py  assemble + validate + reload the shared proxy  (CAN fail the run)",
    "perseus.py --install-only · dbbackup.py · logship.py · secaudit.py · model_watch.py",
    "tag last-known-good + good-YYYYMMDD-HHMMSS, pushed to GitHub",
    "release_notes.py  four models write them, Telegram + Gmail API send them"], INDIGO, CARD, 10, 8.2)
d.card(s, 0.55, 5.42, 12.23, 1.4, "Flags narrow it. They never split it.", [
    "--test  run the gate battery only          --web / --bots  one target only          --no-stage  skip the twin",
    "--fast-stage  gate without the reboot      --dry-run  print, change nothing          --no-preview  skip the UI stamp",
    "--rollback [REF]  reset to last-known-good (or a dated tag) and redeploy. Bypasses tests, preview and the gate by design.",
    "-m \"msg\"  commit message, also quoted in the release notes"], CYAN, CARD, 10, 8.4)

# -- 05 what ship.py touches -------------------------------------------------------------------------
s, y = d.slide("B · THE ORCHESTRATOR'S REACH", "Everything ship.py calls.",
               "No step is a second command for the operator. If a capability is not wired in here, it does not run.")
d.node(s, 5.2, 1.78, 2.9, 0.6, "python ship.py", "the only verb", CYAN, INDIGO, 12)
groups = [
    (0.55, "GATES (phase 1)", CYAN, [
        "py_compile · every .py", "ruff F821/F811/F822", "16 engine test_*.py",
        "8 node tools/*.mjs", "pytest tests/", "authz_audit.py --local",
        "demo_build.py · deck builds", "gen_sbom.py --check"]),
    (3.70, "DEPLOY", VIOLET, [
        "stagegate.py (twin + gate)", "deploy_web_direct.py", "ship_web.py (--ci only)",
        "deploy.py --reuse --yes", "import_dashboard.py", "govern.py (on NO-GO)"]),
    (6.85, "INFRASTRUCTURE", INDIGO, [
        "caddyguard.py", "dbbackup.py", "logship.py", "secaudit.py",
        "perseus.py --install-only", "model_watch.py"]),
    (10.0, "RECORD", GOLD, [
        "git add / commit / push", "git tag last-known-good", "git tag good-<stamp>",
        "release_notes.py", "ui_preview_stamp.py"]),
]
for x, title, c, items in groups:
    d.arrow_d(s, x + 1.37, 2.44, 0.3, c)
    d.card(s, x, 2.82, 2.78, 2.62, title, items, c, CARD, 10, 8.4)
d.card(s, 0.55, 5.66, 12.23, 0.82, "The rule that keeps it one command", [
    "New capability (a test, a check, a migration, a provisioning step)? Wire it into ship.py in the SAME change.",
    "A script the operator has to remember to run separately is a bug, not a feature."], CYAN, CARD, 10, 8.6)

# -- 06 test scope: the gate battery ------------------------------------------------------------------
s, y = d.slide("C · TEST SCOPE  ·  1 of 2", "The gate battery. Phase 1/5.",
               "Every one of these was bought by a customer-facing incident. The bracketed name is the incident it prevents.")
d.card(s, 0.55, 1.75, 6.05, 2.72, "ENGINE  ·  16 scripts, all wired into ship.py", [
    "test_ca_pivot.py          false positives  [bibeltv.de, 1003 false IPs]",
    "test_recall.py            false negatives  [bibeltv.de, the opposite bug]",
    "test_parity.py            must not find less than manual Shodan work",
    "test_run_path.py          executes recon end to end on a mocked API",
    "test_recon_budget.py      recon bounded  [caixabank.es, 22 minutes]",
    "test_enrich_deadline.py   enrichment bounded  [AS37468, 19 minutes]",
    "test_enrich_grounding.py  prose names its own finding  [AS37468]",
    "test_scope_abakus.py      one footer link became 236 Meta hosts",
    "test_classify_adpolice.py TLS sign, redirects, jurisdiction",
    "test_asn_enterprise.py    RBC 7-ASN recall + precision",
    "test_deck_quality.py      renders decks, reads back the OOXML geometry",
    "test_white_label.py · test_engine_i18n.py · test_passive_checks.py",
    "test_drift.py · test_compliance_ca.py · test_creed.js"], CYAN, CARD, 10, 8.1)
d.card(s, 6.92, 1.75, 5.86, 2.72, "FRONTEND  ·  8 node gates", [
    "api_contract.mjs    getJSON vs postJSON shape",
    "canvas_smoke.mjs    900 frames, no exception",
    "header_layout.mjs   row arithmetic in the longest language",
    "contrast_gate.mjs   WCAG on the shipped stylesheet",
    "partners_gate.mjs   6 locales, no prices, no entities",
    "i18n_catalogue.mjs  per-locale gaps, two key spaces",
    "run_i18n_audit.mjs  SSR audit, 16 pages x 6 languages",
    "shipped_shell.mjs   no source maps, no secrets in dist/",
    "",
    "Exit 2 means the toolchain is unusable and the gate",
    "skips. Exit 1 means a real defect and the ship stops.",
    "A gate that cannot run is not a gate."], VIOLET, CARD, 10, 8.1)
d.card(s, 0.55, 4.6, 12.23, 1.1, "Also in phase 1, before any of the above", [
    "py_compile over every .py in the engine, the repo root and webapp/backend/app  ·  catches a truncated file",
    "ruff F821/F811/F822  ·  the undefined-name gate, added after a NameError reached a customer run"], INDIGO, CARD, 10, 8.4)
d.card(s, 0.55, 5.85, 12.23, 1.02, "What a failure means", [
    "Any gate failure exits before phase 2. Nothing is committed, nothing is pushed, nothing is deployed.",
    "A gate that CRASHES is reported differently from a gate that FINDS something. Read the verdict line, not the stack."], RED, CARD, 10, 8.4)

# -- 07 test scope: pytest ----------------------------------------------------------------------------
s, y = d.slide("C · TEST SCOPE  ·  2 of 2", "The suite: 50 modules, 958 test functions.",
               "Counted from tests/*.py. Grouped by what they defend, not by file name.")
blocks = [
    (0.55, 1.75, "ACCESS + IDENTITY", CYAN, [
        "test_auth · test_admin_users · test_quota",
        "test_routes · test_set_secret",
        "Every /api/admin/* route refuses a non-admin.",
        "Hiding a nav item is presentation, not control."]),
    (4.62, 1.75, "ACTIVE DEFENCE", VIOLET, [
        "test_shield · test_perseus_* (7 modules)",
        "test_client_truth · test_asset_trace",
        "test_ip_reputation · test_attack_digest",
        "Never iptables. Never block a logged-in user."]),
    (8.69, 1.75, "DEPLOY INTEGRITY", INDIGO, [
        "test_deploy_immutability · test_deploy_parity",
        "test_caddy_wiring · test_decommission",
        "test_gate_integrity · test_hostpath",
        "What deploys is the COMMIT, never the tree."]),
    (0.55, 3.92, "MONEY", GOLD, [
        "test_llm_meter · test_spend_watch",
        "test_jhw_llm_events",
        "The daily cap, the spike detector, and",
        "proof of what each project spent."]),
    (4.62, 3.92, "OUTPUT + LANGUAGE", CYAN, [
        "test_doc_lang · test_jurisdiction_path",
        "test_white_label_api · test_proteus",
        "test_run_log · test_release_notes",
        "A capability the API discards is invisible."]),
    (8.69, 3.92, "THE WATCHERS", RED, [
        "test_fleet · test_fleet_cli · test_fleet_soc",
        "test_outside_view · test_supplychain",
        "test_console_encoding · test_claude_md_size",
        "The observer must itself be observed."]),
]
for x, yy, title, c, items in blocks:
    d.card(s, x, yy, 3.9, 1.95, title, items, c, CARD, 10, 8.1)
d.card(s, 0.55, 6.06, 12.23, 0.62, "Platform honesty", [
    "Five modules need bash/sed and skip cleanly on Windows; CI and the droplet run them. No module requires a docker binary."],
    MUTED, CARD, 10, 8.4)

# -- 08 the four models -------------------------------------------------------------------------------
s, y = d.slide("D · THE FOUR MODELS", "Four vendors, so no shared failure domain.",
               "enrich._FALLBACKS is the ONE home. Compose must not restate it; ship.py deletes any override from the droplet .env.")
chain = [("deepseek-3.2", "DeepSeek", "20 tok/s", CYAN),
         ("llama-4-maverick", "Meta", "5 tok/s", VIOLET),
         ("gemma-4-31B-it", "Google", "9 tok/s", INDIGO),
         ("kimi-k2.6", "Moonshot", "9 tok/s", CYAN)]
for i, (mid, vendor, rate, c) in enumerate(chain):
    x = 0.55 + i * 3.17
    d._rect(s, x, 1.78, 2.82, 0.98, CARD, c, lw=1.25)
    d._rect(s, x, 1.78, 2.82, 0.05, c)
    d._text(s, x + 0.16, 1.93, 2.6, 0.26, mid, 10.5, WHITE, MONO, True)
    d._text(s, x + 0.16, 2.22, 2.6, 0.22, vendor, 8.4, MUTED, BF)
    d._text(s, x + 0.16, 2.45, 2.6, 0.22, "measured " + rate, 8.4, GOLD, MONO)
    if i < 3:
        d.arrow_r(s, x + 2.85, 2.2, 0.26, c)
d.card(s, 0.55, 2.95, 6.05, 2.42, "How one assessment is written", [
    "1. Feasibility check. findings x 600 tokens vs what the fastest",
    "    model writes in its slice. Too big? The whole-estate call is",
    "    never issued, and the shards take over.",
    "2. Serial chain. Head gets 55% of the remaining budget. Two",
    "    consecutive timeouts end the chain: same prompt, so it is",
    "    the prompt that is wrong, not the vendor.",
    "3. Map-reduce top-up. 3 findings per shard, 4 workers, shards",
    "    spread ACROSS vendors, severity-interleaved.",
    "4. Coverage contract. Missing ids get one retry on a DIFFERENT",
    "    model. Under 420 chars counts as THIN, not as covered.",
    "    Floor 80%."], CYAN, CARD, 10, 8.2)
d.card(s, 6.92, 2.95, 5.86, 2.42, "What stops a confident wrong answer", [
    "grounded()  prose must name something of its own finding:",
    "a port, a CVE, a product, an IP. If it names nothing, it is",
    "REJECTED and the template text is kept.",
    "   [AS37468: BGP prose landed on a database finding]",
    "",
    "_audit_cves()  a CVE is cited only if it is in the raw",
    "findings. The rest are stripped and logged as",
    "hallucination_guard.",
    "",
    "slim_payload()  the model sees findings + evidence only.",
    "Never the whole file, never a character-sliced JSON blob."], RED, CARD, 10, 8.2)
d.card(s, 0.55, 5.52, 12.23, 1.35, "Budgets  ·  committed default vs what is deployed", [
    "ENRICH_TIMEOUT   per call      code 120 s   ·  droplet 175 s           ENRICH_WALL_S   whole phase   540 s  (enrich_parallel.WALL_S_DEFAULT)",
    "ENRICH_BUDGET_S  serial chain  code 245 s   ·  droplet 380 s           RECON_BUDGET_S  recon         300 s  (shodan_recon.ReconBudget)",
    "Shard cap 150 s · shard floor 45 s (below that the call is not issued) · subprocess kill 430 s. Read BOTH numbers before diagnosing a timeout."],
    AMBER, CARD, 10, 8.3)

# -- 09 models propose, code decides ------------------------------------------------------------------
s, y = d.slide("D · THE RULE THAT SURVIVES EVERYTHING", "Models propose. Code decides.",
               "The same four models appear in six places. In none of them do they decide a side effect.")
rows = [
    ("Enrichment", "writes the finding prose", "severity, evidence and CVE ids are engine facts", CYAN),
    ("Staging gate", "2 soldiers + 2 auditors write a verdict", "GO/NO-GO comes from 42 deterministic checks", VIOLET),
    ("Release notes", "readable prose and a risk read", "commits, files and hashes are computed by git", INDIGO),
    ("Shield panel", "proposes threshold changes", "3-of-4 consensus, MEDIAN value, clamped to committed bounds", RED),
    ("FP auditor", "flags a finding as a third party's", "only dropped if deterministic ownership data agrees", AMBER),
    ("White Label", "picks brand colour vs decoration", "colours and fonts are extracted from theme1.xml", GOLD),
]
d._rect(s, 0.55, 1.75, 12.23, 0.4, CARD2)
for lbl, x, w in (("WHERE", 0.75, 2.3), ("THE MODELS WRITE", 3.15, 4.4), ("THE CODE DECIDES", 7.75, 4.9)):
    d._text(s, x, 1.86, w, 0.24, lbl, 8.4, CYAN, MONO, True, space=1.6)
for i, (where, prop, dec, c) in enumerate(rows):
    yy = 2.2 + i * 0.68
    d._rect(s, 0.55, yy, 12.23, 0.62, CARD if i % 2 == 0 else INK)
    d._rect(s, 0.55, yy, 0.05, 0.62, c)
    d._text(s, 0.75, yy + 0.19, 2.3, 0.26, where, 10, WHITE, BF, True)
    d._text(s, 3.15, yy + 0.19, 4.4, 0.26, prop, 9, BODY, BF)
    d._text(s, 7.75, yy + 0.19, 4.9, 0.26, dec, 9, BODY, BF)
d._rect(s, 0.55, 6.36, 12.23, 0.56, CARD, CYAN, lw=1.0)
d._rect(s, 0.55, 6.36, 0.05, 0.56, CYAN)
d._text(s, 0.8, 6.46, 11.8, 0.4,
        ["A 429, an outage or a truncated answer cannot block a correct release. A hallucinated objection cannot stall a good",
         "deploy. A model that is feeling agreeable cannot wave through a container that is not running."],
        8.8, BODY, BF, italic=True)

# -- 10 cost control ----------------------------------------------------------------------------------
s, y = d.slide("D · SPEND", "Three controls, three different questions.",
               "They were built in this order, each after the previous one proved insufficient.")
d.node(s, 0.55, 1.85, 3.72, 0.6, "llm_meter.py", "make it stop", RED, CARD2, 11)
d.node(s, 4.80, 1.85, 3.72, 0.6, "cost_ledger.py", "what did it cost", GOLD, CARD2, 11)
d.node(s, 9.06, 1.85, 3.72, 0.6, "spend_watch.py", "something changed", CYAN, CARD2, 11)
d.card(s, 0.55, 2.62, 3.72, 2.5, "The hard ceiling", [
    "Daily cap  $3.00",
    "Warn at    60%",
    "Single-call alert  $0.15",
    "",
    "Hooked at enrich._call,",
    "the ONE chokepoint.",
    "allow() runs BEFORE the",
    "request, record() after.",
    "",
    "Fails OPEN on a storage",
    "fault, CLOSED on budget.",
    "A refusal just falls back",
    "to template text."], RED, CARD, 10, 8.2)
d.card(s, 4.80, 2.62, 3.72, 2.5, "The books of record", [
    "SQLite on the shared",
    "colt_events volume, so it",
    "survives every rebuild.",
    "",
    "One row per completed",
    "assessment: company,",
    "cost, tokens, model,",
    "severity counts, user.",
    "",
    "Loki ages out with",
    "retention. This does not.",
    "",
    "Every write best-effort."], GOLD, CARD, 10, 8.2)
d.card(s, 9.06, 2.62, 3.72, 2.5, "The spike detector", [
    "Hourly. Median baseline",
    "over 14 days.",
    "",
    "Spike = 4x baseline,",
    "min $0.10 · account $2.00",
    "unattributed $1.00",
    "Cooldown 6 h.",
    "",
    "Two sources: our meter",
    "AND the DO balance.",
    "The second is the point:",
    "it sees callers we do",
    "not control."], CYAN, CARD, 10, 8.2)
d.card(s, 0.55, 5.28, 12.23, 1.55, "The incident that built the third one", [
    "Two models, deepseek-v4-pro-0813 and glm-5.3-flash, appeared in NO configuration in this repository or in jobhuntwow,",
    "and took more than 96% of the account's tokens. A meter that only counts OUR OWN calls would never have seen them.",
    "That is why the watcher reads the DigitalOcean balance as well, and why the five projects sharing one model key is a",
    "known open item: DO's own per-key usage cannot attribute the invoice until scoped keys are minted in the console."],
    RED, CARD, 10, 8.4)

# -- 11 day one ---------------------------------------------------------------------------------------
s, y = d.slide("ONBOARDING", "Day one.", "In this order. Nothing here needs permission from anyone.")
steps = [
    ("01", "Read CLAUDE.md top to bottom", "The operating principles and the 56 defect classes. Every line was bought by an incident.", CYAN),
    ("02", "python ship.py --test", "Runs the whole gate battery and changes nothing. Expect it to take minutes, not seconds.", CYAN),
    ("03", "python ship.py --dry-run", "Prints every command the pipeline would run, in order, without touching a droplet.", VIOLET),
    ("04", "python fleet.py", "Read-only: which project is alive, wired in, beating, taking traffic, under attack.", VIOLET),
    ("05", "python recover.py", "Read-only outage triage. Learn it before you need it, not during.", INDIGO),
    ("06", "Read docs/decisions/HISTORY-*.md", "The evidence behind the rules. Grep it with the phrase from the rule you are questioning.", INDIGO),
]
for i, (num, cmd, why, c) in enumerate(steps):
    yy = 1.78 + i * 0.84
    d._rect(s, 0.55, yy, 12.23, 0.72, CARD, c, lw=1.0)
    d._rect(s, 0.55, yy, 0.05, 0.72, c)
    d._text(s, 0.78, yy + 0.24, 0.5, 0.26, num, 12, c, HB)
    d._text(s, 1.42, yy + 0.13, 5.2, 0.26, cmd, 11, WHITE, MONO, True)
    d._text(s, 1.42, yy + 0.42, 10.9, 0.24, why, 8.6, BODY, BF)
d.card(s, 0.55, 6.86, 12.23, 0.0, "", [], CYAN)

# -- 12 the rules -------------------------------------------------------------------------------------
s, y = d.slide("ONBOARDING", "Six rules you will be held to.",
               "These are not style preferences. Each one is the shape of a defect that already happened here.")
rules = [
    ("ONE HOME", "A value with several homes drifts, and the newer one always loses. ENRICH_MODELS once had four homes.", CYAN),
    ("ONE COMMAND", "If a reply ends with two python lines, fold the second into ship.py. A step the operator must remember is a bug.", VIOLET),
    ("A CHECK THAT CANNOT FAIL IS NOT A CHECK", "Prove a gate by breaking the thing it guards. If the denominator comes from the thing being measured, it is not a measurement.", INDIGO),
    ("ABSENCE OF EVIDENCE IS NEVER A FINDING", "A failed lookup reports UNKNOWN and claims no gap. A dead DNS resolver once produced a CRITICAL.", RED),
    ("READ THE DELIVERED ARTIFACT", "Rich finding text is not a good deck. Open the file. Every one of these defects was invisible in the logs.", AMBER),
    ("SECRETS NEVER TOUCH GIT", "set_secret.py, value on stdin, never in argv. gitleaks runs in CI.", GOLD),
]
for i, (title, body, c) in enumerate(rules):
    yy = 1.78 + i * 0.84
    d._rect(s, 0.55, yy, 12.23, 0.72, CARD, c, lw=1.0)
    d._rect(s, 0.55, yy, 0.05, 0.72, c)
    d._text(s, 0.8, yy + 0.13, 11.9, 0.26, title, 10.5, c, BF, True, space=1.2)
    d._text(s, 0.8, yy + 0.42, 11.9, 0.24, body, 8.8, BODY, BF)

p = d.save(OUT)
print("wrote %s (%d slides)" % (p, len(Presentation(p).slides._sldIdLst)))
