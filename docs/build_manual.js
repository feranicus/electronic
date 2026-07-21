/**
 * build_manual.js — generates "cybergod.ai — User Manual" as a branded .docx.
 *
 *   cd "C:\Python SW\Linkedin Scraper"
 *   node docs/build_manual.js
 *
 * Content is FACTUAL: every screen label, command, email rule, timing and filename below was read
 * out of the running code (webapp/frontend/src/pages/*, colt_auth.py, run_assessment.py, bot.py).
 * If you change the product, change this file in the same commit — a manual that drifts is worse
 * than no manual.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, TableOfContents,
  LevelFormat, convertInchesToTwip, PageNumber, Footer, Header, PositionalTab,
  PositionalTabAlignment, PositionalTabLeader, ExternalHyperlink,
} = require("docx");

// ---------------------------------------------------------------- Colt palette
const TEAL = "00B2A9", DTEAL = "0C544E", GOLD = "F7C844", NAVY = "1D2B4E",
      RED = "F20C36", GREY = "5B6B85", LIGHT = "F2F7F7", LINE = "D8E3E3",
      WHITE = "FFFFFF", INK = "1D2B4E";

const CW = 9638;                       // content width in DXA (A4, 2cm margins)
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: NONE, bottom: NONE, left: NONE, right: NONE };

// ---------------------------------------------------------------- helpers
const P = (text, o = {}) => new Paragraph({
  spacing: { after: o.after === undefined ? 120 : o.after, before: o.before || 0, line: 276 },
  alignment: o.align, indent: o.indent, border: o.border, shading: o.shading,
  children: [new TextRun({ text, size: o.size || 21, color: o.color || INK,
                           bold: o.bold, italics: o.italics, font: o.font || "Calibri" })],
});

// rich paragraph: pass an array of {t, b, c, i, mono}
const RP = (runs, o = {}) => new Paragraph({
  spacing: { after: o.after === undefined ? 120 : o.after, before: o.before || 0, line: 276 },
  alignment: o.align, indent: o.indent, shading: o.shading, border: o.border,
  children: runs.map(r => new TextRun({
    text: r.t, bold: r.b, italics: r.i, color: r.c || INK, size: r.size || 21,
    font: r.mono ? "Consolas" : "Calibri",
  })),
});

const H1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 0, after: 180 },
  pageBreakBefore: true,
  children: [new TextRun({ text: t, size: 32, bold: true, color: DTEAL, font: "Calibri" })],
});
const H2 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 140 },
  children: [new TextRun({ text: t, size: 25, bold: true, color: NAVY, font: "Calibri" })],
});
const H3 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 },
  children: [new TextRun({ text: t, size: 22, bold: true, color: TEAL, font: "Calibri" })],
});

const BULLET = (t, lvl = 0) => new Paragraph({
  numbering: { reference: "coltBullets", level: lvl },
  spacing: { after: 70, line: 276 },
  children: [new TextRun({ text: t, size: 21, color: INK, font: "Calibri" })],
});
const RBULLET = (runs, lvl = 0) => new Paragraph({
  numbering: { reference: "coltBullets", level: lvl },
  spacing: { after: 70, line: 276 },
  children: runs.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, color: r.c || INK,
                                        size: 21, font: r.mono ? "Consolas" : "Calibri" })),
});
// Numbered steps. EVERY list must restart at 1, so each call to steps() burns a fresh numbering
// `instance` — without it docx continues one global list and §3 opens at "5.".
let _inst = 0;
function steps(items) {
  const instance = _inst++;
  return items.map(it => new Paragraph({
    numbering: { reference: "coltSteps", level: 0, instance },
    spacing: { after: 80, line: 276 },
    children: (typeof it === "string"
      ? [new TextRun({ text: it, size: 21, color: INK, font: "Calibri" })]
      : it.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, color: r.c || INK,
                                  size: 21, font: r.mono ? "Consolas" : "Calibri" }))),
  }));
}

// A coloured callout box (tip / warning / rule)
function callout(kind, title, lines) {
  const col = { tip: TEAL, warn: RED, note: GOLD, rule: DTEAL }[kind] || TEAL;
  const kids = [new Paragraph({
    spacing: { after: 60 },
    children: [new TextRun({ text: title, bold: true, size: 21, color: col, font: "Calibri" })],
  })];
  lines.forEach((l, i) => kids.push(new Paragraph({
    spacing: { after: i === lines.length - 1 ? 0 : 60, line: 276 },
    children: (typeof l === "string"
      ? [new TextRun({ text: l, size: 20, color: INK, font: "Calibri" })]
      : l.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, color: r.c || INK,
                                size: 20, font: r.mono ? "Consolas" : "Calibri" }))),
  })));
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      right: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      left: { style: BorderStyle.SINGLE, size: 24, color: col },
      insideHorizontal: NONE, insideVertical: NONE,
    },
    rows: [new TableRow({ children: [new TableCell({
      width: { size: CW, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: LIGHT, color: "auto" },
      margins: { top: 140, bottom: 140, left: 200, right: 160 },
      children: kids,
    })] })],
  });
}

// Monospace command / screen-text block
function code(lines) {
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    borders: { top: NONE, bottom: NONE, left: { style: BorderStyle.SINGLE, size: 12, color: TEAL },
               right: NONE, insideHorizontal: NONE, insideVertical: NONE },
    rows: [new TableRow({ children: [new TableCell({
      width: { size: CW, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "F4F6F9", color: "auto" },
      margins: { top: 120, bottom: 120, left: 200, right: 140 },
      children: lines.map((l, i) => new Paragraph({
        spacing: { after: i === lines.length - 1 ? 0 : 40 },
        children: [new TextRun({ text: l, font: "Consolas", size: 19, color: NAVY })],
      })),
    })] })],
  });
}

// Borderless key/value table — no header row (the cover block, "numbers worth remembering").
// A table() with an empty header prints an ugly blank dark bar, so this exists separately.
function plainTable(widths, rows, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = CW / total;
  const w = widths.map(x => Math.round(x * scale));
  w[w.length - 1] += CW - w.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: w,
    borders: {
      top: NONE, bottom: NONE, left: NONE, right: NONE, insideVertical: NONE,
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: LINE },
    },
    rows: rows.map(r => new TableRow({
      children: r.map((c, i) => new TableCell({
        width: { size: w[i], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: WHITE, color: "auto" },
        margins: { top: 90, bottom: 90, left: i === 0 ? 0 : 130, right: 130 },
        children: [new Paragraph({
          spacing: { after: 0 },
          children: [new TextRun({
            text: String(c).replace(/^\*/, ""),
            bold: String(c).startsWith("*") || (opts.boldFirstCol && i === 0),
            size: 20, color: i === 0 ? DTEAL : INK, font: "Calibri" })],
        })],
      })),
    })),
  });
}

// Standard table: header row + body rows
function table(widths, header, rows, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = CW / total;
  const w = widths.map(x => Math.round(x * scale));
  // rounding drift -> push into the last column so the sum is exact
  w[w.length - 1] += CW - w.reduce((a, b) => a + b, 0);

  const hdr = new TableRow({
    tableHeader: true,
    children: header.map((h, i) => new TableCell({
      width: { size: w[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: DTEAL, color: "auto" },
      margins: { top: 90, bottom: 90, left: 130, right: 130 },
      children: [new Paragraph({ spacing: { after: 0 },
        children: [new TextRun({ text: h, bold: true, size: 19, color: WHITE, font: "Calibri" })] })],
    })),
  });

  const body = rows.map((r, ri) => new TableRow({
    children: r.map((c, i) => new TableCell({
      width: { size: w[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: ri % 2 ? "FFFFFF" : LIGHT, color: "auto" },
      margins: { top: 90, bottom: 90, left: 130, right: 130 },
      children: String(c).split("\n").map((line, li, arr) => new Paragraph({
        spacing: { after: li === arr.length - 1 ? 0 : 50, line: 264 },
        children: [new TextRun({
          text: line.replace(/^\*/, ""),
          bold: line.startsWith("*") || (opts.boldFirstCol && i === 0),
          size: 19, color: INK,
          font: opts.monoCols && opts.monoCols.includes(i) ? "Consolas" : "Calibri",
        })],
      })),
    })),
  }));

  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: w,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      left: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      right: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: LINE },
    },
    rows: [hdr, ...body],
  });
}

const SPACER = (h = 200) => new Paragraph({ spacing: { after: h }, children: [] });
const RULE = () => new Paragraph({
  spacing: { before: 120, after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: TEAL } }, children: [],
});
const BREAK = () => new Paragraph({ children: [new PageBreak()] });

// ---------------------------------------------------------------- cover page
const cover = [
  SPACER(1400),
  new Paragraph({
    spacing: { after: 100 },
    children: [
      new TextRun({ text: "❯ ", bold: true, size: 56, color: TEAL, font: "Calibri" }),
      new TextRun({ text: "colt", bold: true, size: 56, color: NAVY, font: "Calibri" }),
    ],
  }),
  new Paragraph({
    spacing: { after: 700 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: TEAL } },
    children: [new TextRun({ text: "CYBER PRE-SALES AUTOMATION", bold: true, size: 20,
                             color: GREY, font: "Calibri" })],
  }),
  new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text: "cybergod.ai", bold: true, size: 76, color: DTEAL, font: "Calibri" })],
  }),
  new Paragraph({
    spacing: { after: 500 },
    children: [new TextRun({ text: "The complete user manual", size: 40, color: NAVY, font: "Calibri" })],
  }),
  new Paragraph({
    spacing: { after: 160 },
    children: [new TextRun({
      text: "Type a company name. Get four boardroom-ready decks.",
      size: 26, italics: true, color: TEAL, font: "Calibri" })],
  }),
  new Paragraph({
    spacing: { after: 900 },
    children: [new TextRun({
      text: "Everything you need, start to finish — no technical background required.",
      size: 21, color: GREY, font: "Calibri" })],
  }),
  plainTable([26, 74], [
    ["*For", "Colt account executives and authorised partners"],
    ["*Covers", "The web app at www.cybergod.ai and the Telegram bots"],
    ["*Version", "1.0 — July 2026"],
    ["*Questions", "feranicus@s4biz.io"],
  ]),
  SPACER(400),
  P("Internal document. Contains no customer data.", { size: 18, color: GREY, italics: true }),
];

// ---------------------------------------------------------------- contents
// A STATIC list, not a TableOfContents field. A field renders blank until the reader right-clicks
// -> Update Field, which is exactly the kind of step this manual is supposed to avoid.
const SECTIONS = [
  ["1.", "The 60-second version", "What it does, what you get, what it is not"],
  ["2.", "Before you start", "Who can log in, and what you need"],
  ["3.", "Logging in (web)", "Three steps, about thirty seconds"],
  ["4.", "Running an assessment", "The two inputs, and what happens while you wait"],
  ["5.", "The four decks, explained", "Findings · C-BIQ · GEOPOL · DELTAS"],
  ["6.", "English or German", "Producing the deck set in Hochdeutsch"],
  ["7.", "The Assistant and your History", "Cassandra, and re-downloading past runs"],
  ["8.", "Using it from Telegram", "Every command, verbatim"],
  ["9.", "When something goes wrong", "Every error message and its fix"],
  ["10.", "Security and data protection", "What customers will ask you"],
  ["11.", "On your phone", "Installing it like an app"],
  ["12.", "Frequently asked questions", ""],
  ["13.", "One-page cheat sheet", "Print this one"],
];
const toc = [
  H1("Contents"),
  SPACER(120),
  ...SECTIONS.map(([n, t, sub]) => new Paragraph({
    spacing: { after: sub ? 40 : 160, line: 264 },
    children: [
      new TextRun({ text: n + "  ", bold: true, size: 22, color: TEAL, font: "Calibri" }),
      new TextRun({ text: t, bold: true, size: 22, color: NAVY, font: "Calibri" }),
    ],
  })).flatMap((p, i) => SECTIONS[i][2]
    ? [p, new Paragraph({
        spacing: { after: 160 }, indent: { left: 340 },
        children: [new TextRun({ text: SECTIONS[i][2], size: 19, color: GREY, font: "Calibri" })],
      })]
    : [p]),
  SPACER(200),
  callout("tip", "In a hurry?", [
    "Read §1 (one page), then keep §13 (the cheat sheet) open beside you. Everything in between is there for when you need it.",
  ]),
];

// ---------------------------------------------------------------- body
const body = [];
const add = (...x) => body.push(...x);

// ===== 1. THE 60-SECOND VERSION =====
add(
  H1("1. The 60-second version"),
  P("cybergod.ai turns a single company name into four presentation-ready decks about that company's cyber exposure — the kind of material that normally takes an analyst several days.", { size: 23 }),
  SPACER(80),
  H2("What you do"),
  ...steps([
    [{ t: "Log in " }, { t: "at www.cybergod.ai", b: true }, { t: " with your Colt email." }],
    [{ t: "Type a company name", b: true }, { t: " — for example " }, { t: "Volkswagen AG", mono: true }, { t: "." }],
    [{ t: "Choose English or German", b: true }, { t: "." }],
    [{ t: "Wait a few minutes", b: true }, { t: ", then download your decks." }],
  ]),
  SPACER(120),
  H2("What you get"),
  table([22, 48, 30], ["Deck", "What it answers", "Use it for"], [
    ["*Findings", "What of theirs is exposed on the internet right now, and how serious each item is.", "The opening conversation. Proof you did homework."],
    ["*C-BIQ", "What that exposure could cost them in euros — with the maths shown.", "Getting budget released. Speaking to a CFO."],
    ["*GEOPOL", "Who would realistically attack them, and why.", "Building urgency with a CISO or board."],
    ["*DELTAS", "What the AI added on top of the raw scan — the proof of value.", "Internal review, or showing your own work."],
  ], { boldFirstCol: true }),
  SPACER(160),
  callout("tip", "The one thing to remember", [
    "You never type IP addresses, ASNs, domains or certificates. One company name is the whole input — the engine works the rest out by itself.",
  ]),
  SPACER(160),
  H2("What it is not"),
  BULLET("It is not a penetration test. No port scanning, no vulnerability probing, no login attempts, nothing exploited. It reads public sources, and at most fetches a public page icon."),
  BULLET("It is not a replacement for you. It produces the evidence and the numbers; the conversation is still yours."),
  BULLET("It is not a customer-facing portal. Only authorised Colt staff and named partners can log in."),
);

// ===== 2. BEFORE YOU START =====
add(
  H1("2. Before you start"),
  H2("Who can log in"),
  P("Access is deliberately narrow. Your email address must match one of these:"),
  table([32, 40, 28], ["Who", "Email pattern", "Example"], [
    ["Colt account executives", "name.familyname@colt.net", "jevgenijs.vainsteins@colt.net"],
    ["S4BIZ (whole domain)", "anyone@s4biz.io", "feranicus@s4biz.io"],
    ["Named partners", "Individually approved addresses", "ud@objectale.ch"],
  ], { monoCols: [1, 2] }),
  SPACER(120),
  callout("note", "Your Colt address must have exactly one dot", [
    [{ t: "The pattern is " }, { t: "firstname.lastname@colt.net", mono: true }, { t: ". Double-barrelled names with a hyphen are fine (" }, { t: "anna-maria.schmidt@colt.net", mono: true }, { t: "). An address with no dot at all (" }, { t: "jvainsteins@colt.net", mono: true }, { t: ") or a shared mailbox will be rejected." }],
    "If you are a partner and your address is not recognised, it has to be added by the operator first. Email feranicus@s4biz.io.",
  ]),
  SPACER(160),
  H2("What you also need"),
  BULLET("The shared access password. This is given to you by the operator — it is not your Colt network password, and it is never emailed to you."),
  BULLET("Access to your own inbox. Every login sends a fresh 6-digit code to your email address. Knowing the password alone is not enough."),
  SPACER(120),
  H2("Where to use it"),
  table([28, 72], ["Route", "Best for"], [
    ["*Web app\nwww.cybergod.ai", "Everything. This is the main tool — assessments, the assistant, and your history of past runs. Works on a laptop, and on a phone (it can be installed like an app — see §11)."],
    ["*Telegram bots", "Speed and mobility. Fire off an assessment from your phone in a taxi and receive the decks as files in the chat. Also the only place with advanced options."],
  ], { boldFirstCol: true }),
);

// ===== 3. LOGGING IN =====
add(
  H1("3. Logging in (web)"),
  P("Three steps, roughly thirty seconds. Go to www.cybergod.ai and click ", { after: 60 }),
  RP([{ t: "Open the app", b: true, c: DTEAL }, { t: " (top right) or " }, { t: "Open the app / Log in", b: true, c: DTEAL }, { t: " in the middle of the page." }]),
  SPACER(80),
  H3("Step 1 — Your identity"),
  ...steps([
    [{ t: "In " }, { t: "Colt email", b: true }, { t: ", type your full address, e.g. " }, { t: "name.surname@colt.net", mono: true }, { t: "." }],
    [{ t: "In " }, { t: "Access password", b: true }, { t: ", type the shared access password." }],
    [{ t: "Click " }, { t: "Continue →", b: true, c: DTEAL }, { t: "." }],
  ]),
  SPACER(80),
  H3("Step 2 — Your one-time code"),
  P("A 6-digit code is emailed to the address you just typed. It is valid for 10 minutes."),
  ...steps([
    [{ t: "Open your inbox and copy the six digits." }],
    [{ t: "Type them into " }, { t: "6-digit code", b: true }, { t: " and click " }, { t: "Verify & enter", b: true, c: DTEAL }, { t: "." }],
  ]),
  SPACER(80),
  H3("Step 3 — You're in"),
  P("You land on the New assessment screen. You will stay signed in for 12 hours, then you'll be asked to log in again."),
  SPACER(140),
  callout("warn", "If login fails", [
    [{ t: "\"Access denied\"", b: true }, { t: " — either your email is not on the allow-list, or the password is wrong. Check for a typo in the address first; that is the usual cause." }],
    [{ t: "\"Account locked — too many attempts\"", b: true }, { t: " — five wrong password attempts locks you out for 15 minutes. Wait it out; there is no unlock button." }],
    [{ t: "\"Invalid or expired code\"", b: true }, { t: " — codes die after 10 minutes and after 5 wrong tries. Click " }, { t: "← Use a different account", b: true }, { t: " and start again to get a fresh one." }],
    [{ t: "No email arrived", b: true }, { t: " — check spam. The code is sent from a Google-hosted mailbox. If nothing arrives at all, the address may be allow-listed but mistyped." }],
  ]),
  SPACER(140),
  H2("Signing out"),
  P("Click Log out at the bottom of the left-hand menu (on a phone, top right). Always do this on a shared machine."),
);

// ===== 4. RUNNING AN ASSESSMENT =====
add(
  H1("4. Running an assessment"),
  P("This is the core of the product, and it is one screen."),
  SPACER(60),
  H2("The first time only: the privacy notice"),
  RP([{ t: "On your first visit a short data-protection notice appears, with a " }, { t: "Deutsch / English", b: true }, { t: " toggle. Read it, then click " }, { t: "Understood — don't show again", b: true, c: DTEAL }, { t: ". It will not come back. Full details are in §10." }]),
  SPACER(120),
  H2("The two inputs"),
  table([26, 74], ["Field", "What to put in it"], [
    ["*Company name", "The company's name or its domain. Both work: Volkswagen AG, volkswagen.de, or SGL Carbon. Use the full legal name where you can — it resolves the footprint more accurately than an abbreviation."],
    ["*Document language", "English, or Deutsch (Hochdeutsch). This changes the entire deck set — headings, prose and terminology — not just the cover. Pick what your customer reads."],
  ], { boldFirstCol: true }),
  SPACER(120),
  RP([{ t: "Then click " }, { t: "Assess", b: true, c: DTEAL }, { t: ". That is it." }]),
  SPACER(160),
  callout("tip", "Choosing a good input", [
    "Use the legal entity you are actually selling to. \"Siemens AG\" and \"Siemens Energy\" are different companies with different infrastructure.",
    "A domain is the most precise input if you know it — it anchors the discovery immediately.",
    "Very large groups produce very large estates, and take longer. That is normal, not a fault.",
  ]),
  SPACER(160),
  H2("What happens while you wait"),
  P("A progress bar, a percentage, an elapsed clock and a live log appear. The phases are:"),
  table([12, 40, 48], ["Progress", "Phase", "What it is doing"], [
    ["8%", "Shodan recon + super-filters", "Finding everything of theirs that faces the internet. This is the long part."],
    ["56%", "BGP/ASN resilience", "Checking how their networks are connected and whether that is a NIS2 weakness."],
    ["62%", "AI enrichment", "Writing the business prose and checking it against the methodology."],
    ["91%", "Building 3 decks", "Rendering Findings, C-BIQ and GEOPOL."],
    ["97%", "Building DELTAS deck", "Rendering the before/after comparison."],
    ["100%", "Complete", "Download links appear."],
  ], { monoCols: [0] }),
  SPACER(140),
  callout("note", "How long does it really take?", [
    "Plan for 2 to 7 minutes. A small company can finish in about two minutes; a large multinational with dozens of networks takes longer, and that is the engine doing more work, not hanging.",
    "The bar deliberately creeps between milestones so you can see it is alive. If it sits at one phase for a while during recon, that is expected.",
    "After five minutes the screen tells you why it is still going — usually a large estate, or an AI model being slow and the system switching to a backup.",
  ]),
  SPACER(140),
  H2("Can I close the tab?"),
  P("The assessment runs on the server, not in your browser. If your connection drops, or you switch apps on your phone, the run continues and the page reconnects to it automatically — you will see \"Reconnected to an assessment already running on the server\"."),
  RP([{ t: "That said, the safest habit is to " }, { t: "leave the tab open", b: true }, { t: " until the decks appear. You will also notice an on-screen warning that says refreshing cancels the run; that message is out of date, but there is no advantage to testing it." }]),
  SPACER(140),
  H2("When it finishes"),
  RP([{ t: "You will see " }, { t: "\"Done. Your four decks are ready.\"", b: true, c: DTEAL }, { t: " and one card per deck. Click " }, { t: "Download", b: true, c: DTEAL }, { t: " on each. They are ordinary PowerPoint files — open, edit and re-brand them freely." }]),
  SPACER(100),
  callout("note", "Sometimes you get three decks, not four", [
    "The fourth deck (DELTAS) only exists if the AI enrichment step succeeded. If an AI model was unavailable, the run still completes and the first three decks are still valid and usable — they simply use standard wording instead of AI-written prose. The log will say so.",
  ]),
);

// ===== 5. THE FOUR DECKS =====
add(
  H1("5. The four decks, explained"),
  P("Filenames follow the company name, for example VolkswagenAG_C-BIQ.pptx. German versions get a _DE suffix, so the two never overwrite each other."),
  SPACER(120),

  H2("5.1 Findings — \"what is exposed\""),
  RP([{ t: "File: " }, { t: "<Company>_Shodan_Findings.pptx", mono: true }]),
  P("The factual inventory. Every internet-facing system found, each rated Critical / High / Medium / Low, each with the evidence behind it."),
  BULLET("An executive summary with counts at each severity."),
  BULLET("A findings index, then one card per finding: what it is, the evidence, why it matters, and how to fix it."),
  BULLET("The asset inventory — their estate by operator, ASN, country and role."),
  BULLET("A mitigation mapping that lines each finding up against the Colt portfolio."),
  BULLET("An honest caveats slide, and a \"next seven days\" list of highest-leverage moves."),
  RP([{ t: "Use it: ", b: true }, { t: "as your opening. It proves you looked before you called." }]),
  SPACER(140),

  H2("5.2 C-BIQ — \"what it would cost them\""),
  RP([{ t: "File: " }, { t: "<Company>_C-BIQ.pptx", mono: true }, { t: "   (Cyber Business-Impact Quantification)" }]),
  P("The money deck. It converts the findings into euros using recognised methods (FAIR-style loss modelling and Monte-Carlo simulation), and shows the maths rather than asserting a number."),
  BULLET("The three headline numbers a board asks for: expected annual loss, worst realistic case, and return on security investment."),
  BULLET("A loss-exceedance curve showing how the whole risk profile drops after remediation."),
  BULLET("Every finding priced individually, plus one worked end-to-end example."),
  BULLET("A staged plan showing how each Colt control removes a slice of the total."),
  RP([{ t: "Use it: ", b: true }, { t: "when the technical case is accepted but the budget is not. This is the CFO deck." }]),
  SPACER(140),

  H2("5.3 GEOPOL — \"who would attack them\""),
  RP([{ t: "File: " }, { t: "<Company>_GEOPOL.pptx", mono: true }]),
  P("The threat-actor picture, built from established public frameworks rather than invented."),
  BULLET("An executive verdict, then why this specific company is a target — sector, geography, supply chain."),
  BULLET("Named adversary groups, grouped by how likely they are to act."),
  BULLET("A likelihood index (intent × capability × exposure fit) over the next 12 months."),
  BULLET("A kill-chain scenario: how an attack would actually unfold against them."),
  BULLET("A link back to the C-BIQ numbers, so threat and cost line up."),
  RP([{ t: "Use it: ", b: true }, { t: "to create urgency with a CISO. \"Exposed\" is abstract; \"this named group targets your sector this way\" is not." }]),
  SPACER(140),

  H2("5.4 DELTAS — \"what the AI added\""),
  RP([{ t: "File: " }, { t: "<Company>_DELTAS.pptx", mono: true }]),
  P("A transparency deck: the raw scan output on one side, the finished analysis on the other, finding by finding."),
  RP([{ t: "Use it: ", b: true }, { t: "internally. It is rarely a customer deck — it is how you show a manager, or yourself, what the machine actually contributed." }]),
  SPACER(160),
  callout("warn", "Read the caveats slide before you present", [
    "Every deck contains a caveats section stating what the assessment is and is not. Read it. If a lookup failed, the engine says \"unknown\" rather than inventing a weakness — but you should know which slides that affects before a customer asks.",
    "The AI writes business prose, not facts. Sanity-check any named breach, date or figure you intend to say out loud.",
  ]),
);

// ===== 6. EN / DE =====
add(
  H1("6. English or German"),
  P("The customer chooses the language; you get the same four decks either way."),
  BULLET("Pick it once, in the Document language dropdown, before you click Assess."),
  BULLET("German is proper Hochdeutsch business German written for a German reader — not a machine translation of the English deck. Headings, prose, terminology and the specialist vocabulary are all German."),
  BULLET("German files are saved with a _DE suffix, so you can produce both versions for the same company and keep them side by side."),
  BULLET("To get both languages, simply run the assessment twice — once in each language."),
  SPACER(120),
  callout("tip", "German terminology", [
    "The German decks translate the technical vocabulary fully — for example the loss-model acronyms become their German equivalents — so a German CISO reads native terminology, not English jargon in a German sentence. Proper nouns (FAIR, MITRE ATT&CK, NIST, BSI, Colt product names, CVE numbers) deliberately stay as they are, because those are how they are known in German too.",
  ]),
);

// ===== 7. ASSISTANT + HISTORY =====
add(
  H1("7. The Assistant and your History"),
  H2("7.1 Assistant (Cassandra)"),
  RP([{ t: "Click " }, { t: "Assistant", b: true, c: DTEAL }, { t: " in the left-hand menu. It is a chat window with a pre-sales specialist that can research live, not just recall." }]),
  P("Good things to ask:"),
  BULLET("\"What does Volkswagen's IT estate look like, and who runs security there?\""),
  BULLET("\"Give me a MEDDPICC breakdown for this account.\""),
  BULLET("\"Draft a LinkedIn message to a CISO based on the findings I just ran.\""),
  BULLET("\"What's happened in this customer's sector in the last six months?\""),
  RP([{ t: "Type your question, press " }, { t: "Send", b: true, c: DTEAL }, { t: " (or Enter). It is a conversation — follow-up questions keep the context." }]),
  SPACER(160),
  H2("7.2 History"),
  RP([{ t: "Click " }, { t: "History", b: true, c: DTEAL }, { t: ". Every assessment you have run, newest first, with the decks ready to download again." }]),
  BULLET("You see only your own assessments. Decks are locked to the person who generated them — nobody else can download your files, and you cannot download theirs."),
  BULLET("There is no delete button in the app. If you need something removed, email feranicus@s4biz.io."),
  BULLET("Assessment records are retained per the privacy notice (90 days). If you need something removed sooner, ask — there is no self-service delete."),
);

// ===== 8. TELEGRAM =====
add(
  H1("8. Using it from Telegram"),
  P("Two bots. Same login rules as the web, same engine, same decks — delivered as files in a chat. Useful when you are away from a laptop."),
  SPACER(100),
  H2("8.1 The assessment bot"),
  P("Find the bot in Telegram, then:"),
  code([
    "/auth name.familyname@colt.net <access-password>",
    "/verify 483920",
    "/assess Volkswagen AG",
  ]),
  SPACER(120),
  callout("warn", "Delete your /auth message immediately", [
    "That message contains the shared access password in plain text, sitting in a chat history. The bot reminds you; do it every time.",
  ]),
  SPACER(140),
  P("After /assess, the bot asks which language, with two buttons:"),
  code([
    "In which language should I write the 4 documents for Volkswagen AG?",
    "     [  English  ]        [  Deutsch  ]",
  ]),
  P("Pick one and it starts. Progress is edited into a single message so the chat stays clean, then each .pptx arrives as a file."),
  SPACER(120),
  H3("Skipping the language question"),
  code(["/assess Volkswagen AG --lang de"]),
  P("Add --lang de or --lang en and it starts immediately."),
  SPACER(140),
  H3("Advanced: helping the engine along"),
  P("If a company hides behind a CDN, auto-discovery can under-resolve. Only in Telegram, you can supply hints:"),
  code([
    "/assess keb.de --asn AS1234 --net 1.2.3.0/24",
    "/assess Acme --org \"Acme Group SE\" --domain acme.com",
  ]),
  P("These are optional overrides, not requirements. Ignore them unless a result looks thin."),
  SPACER(160),
  H2("8.2 The assistant bot (Cassandra)"),
  P("Same two-step login, then either a command or plain conversation:"),
  code([
    "/auth name.familyname@colt.net <access-password>",
    "/verify 483920",
    "/research sglcarbon.com",
    "…or just type your question.",
  ]),
  SPACER(120),
  H2("8.3 Command reference"),
  table([34, 66], ["Command", "What it does"], [
    ["/start", "Shows the welcome and help text."],
    ["/auth <email> <password>", "Step 1 of login. Sends a code to your email."],
    ["/verify <code>", "Step 2 of login. The 6 digits from that email."],
    ["/assess <company>", "Runs an assessment. Asks for the language."],
    ["/assess <company> --lang de", "Runs it straight away in German (or --lang en)."],
    ["/research <company>", "Cassandra only. Live research on a company."],
  ], { monoCols: [0] }),
);

// ===== 9. TROUBLESHOOTING =====
add(
  H1("9. When something goes wrong"),
  table([34, 66], ["What you see", "What to do"], [
    ["*\"Access denied\" at login", "Check your email address character by character — it must be firstname.lastname@colt.net. If that is right, the shared password is wrong or has been changed."],
    ["*\"Account locked\"", "Five wrong passwords. Wait 15 minutes. There is no override."],
    ["*The code never arrives", "Check spam. If still nothing, your address may be mistyped — restart with \"← Use a different account\"."],
    ["*\"Invalid or expired code\"", "Codes last 10 minutes and allow 5 tries. Start the login again for a fresh one."],
    ["*Bounced back to the login screen", "Your 12-hour session expired. Log in again; nothing is lost."],
    ["*The run seems stuck", "Watch the log, not the bar. Large estates genuinely take several minutes. After 5 minutes the screen explains what is happening."],
    ["*\"Connection dropped — reconnecting\"", "Nothing to do. The run continues on the server and the page re-attaches by itself."],
    ["*A warning about switching models", "Normal and harmless. One AI provider was slow, so it moved to a backup. The deck is still valid."],
    ["*Only three decks appeared", "AI enrichment did not complete. The three decks are valid; re-run later if you want the AI prose and the DELTAS deck."],
    ["*The findings look thin", "Often a CDN hiding the estate. Re-run from Telegram with --org or --domain hints (§8.3), or try the exact legal entity name."],
    ["*A slide says \"unknown\"", "A data source was unreachable. The engine deliberately reports unknown rather than inventing a weakness — do not present that slide as a finding."],
    ["*You cannot download someone else's deck", "Working as intended. Decks are locked to whoever ran them."],
  ], { boldFirstCol: true }),
  SPACER(160),
  callout("tip", "Still stuck?", [
    "Email feranicus@s4biz.io with the company name you tried, the time, and roughly what the log said. Every run is logged server-side, so it can be traced.",
  ]),
);

// ===== 10. SECURITY + PRIVACY =====
add(
  H1("10. Security and data protection"),
  P("Worth knowing, because customers ask."),
  SPACER(50),
  H2("How access is protected"),
  BULLET("Nobody can register — your address must already be on the allow-list."),
  BULLET("Two factors every time: the shared password plus a fresh code to your inbox. A leaked password alone is useless."),
  BULLET("Five wrong attempts locks the account for 15 minutes; sessions expire after 12 hours."),
  BULLET("Your decks are yours — downloads are locked to the account that generated them."),
  BULLET("The site is monitored continuously for attacks, and patched automatically."),
  SPACER(70),
  H2("Where the data lives"),
  BULLET("Everything — app, database, session, documents and logs — runs on one server in Frankfurt am Main, Germany. Nothing is replicated outside the EU."),
  BULLET("One exception: your email address goes to the Google Gmail API, which sends your code and the operator's daily report. Covered by the EU-US Data Privacy Framework."),
  SPACER(70),
  H2("What is collected about you"),
  table([30, 40, 30], ["Data", "Why", "Kept for"], [
    ["Your email address", "Access control and 2FA", "As long as you have access"],
    ["IP, time, browser, device, country", "Attack detection and abuse prevention", "Up to 30 days"],
    ["Companies you assessed, documents", "Delivery and traceability", "90 days"],
    ["Security alerts", "Incident response", "Up to 30 days"],
  ]),
  SPACER(70),
  BULLET("No ad cookies, no cross-site tracking, no profiling, no automated decisions about you. The only cookie keeps you logged in."),
  BULLET("Location is recorded at country level only, from a local offline database."),
  SPACER(70),
  H2("What happens to the assessed company's data"),
  P("This matters when a customer asks whether you \"scanned\" them.", { after: 60 }),
  BULLET("No port scanning, no vulnerability probing, no login attempts. It reads public sources any researcher could look up, and at most fetches the site's public icon."),
  BULLET("Those sources receive only the company name or domain — never your identity, your email or your IP address."),
  BULLET("The companies assessed are organisations, not individuals — no personal data of theirs is involved."),
  RBULLET([{ t: "Full notice (DE/EN): " }, { t: "www.cybergod.ai/privacy", b: true }, { t: " · data-protection requests to feranicus@s4biz.io." }]),
);

// ===== 11. PHONE =====
add(
  H1("11. On your phone"),
  P("The web app is built for phones as well as laptops, and can be installed so it behaves like a normal app."),
  SPACER(80),
  H2("Installing it"),
  H3("Android (Chrome)"),
  ...steps([
    "Open www.cybergod.ai in Chrome.",
    "Tap the three-dot menu -> Install app (or \"Add to Home screen\").",
    "It gets its own icon and opens without browser bars.",
  ]),
  SPACER(80),
  H3("iPhone (Safari)"),
  ...steps([
    "Open www.cybergod.ai in Safari.",
    "Tap Share → Add to Home Screen.",
    "Tap Add.",
  ]),
  SPACER(140),
  H2("Using it on a phone"),
  BULLET("The menu becomes a bar along the bottom: Assess, Assistant, History."),
  BULLET("An assessment keeps running even if you lock the screen or switch apps — reopen the app and it re-attaches to the run in progress."),
  BULLET("Decks download as normal PowerPoint files; open them in the Office app or share them straight to email."),
  SPACER(120),
  callout("tip", "Phone or Telegram?", [
    "For starting a run and reading the result, either works. For firing off several assessments while moving between meetings, Telegram is faster — the decks arrive as chat attachments you can forward directly.",
  ]),
);

// ===== 12. FAQ =====
add(
  H1("12. Frequently asked questions"),
  H3("Is this legal? Are we hacking anyone?"),
  P("No. The engine reads publicly available information — the internet equivalent of walking past a building and noting which doors are visible from the street. There is no port scanning, no vulnerability testing and no attempt to log in to anything. Say this plainly if a customer asks; it is a strength, not a hedge."),
  H3("Can I run an assessment on a customer without telling them?"),
  P("Technically yes, and the data is public. Commercially, use judgement: these decks land far better as \"we did our homework before this meeting\" than as a surprise. That is a sales decision, not a technical restriction."),
  H3("Can I edit the decks?"),
  P("Yes. They are ordinary PowerPoint files. Re-brand, cut slides, merge them into your own deck — whatever the opportunity needs."),
  H3("How accurate is it?"),
  P("The findings are factual observations from public sources. The euro figures are modelled estimates using recognised methods, and are stated as ranges with assumptions shown — they are a basis for discussion, not an invoice. The threat-actor content is assessed likelihood, not intelligence reporting. Every deck says so on its caveats slide."),
  H3("Can I run the same company twice?"),
  P("Yes, as often as you like. Exposure changes, so a re-run before a follow-up meeting is a genuinely good idea — and the delta between two runs is itself a conversation."),
  H3("Someone else already assessed this company. Can I see it?"),
  P("No. History and downloads are private to each user. Run your own; it takes minutes."),
  H3("What does a run cost?"),
  P("A few tenths of a cent in AI inference per assessment. Cost is not a reason to hesitate."),
  H3("It produced nothing / almost nothing. Did it fail?"),
  P("Usually the company is behind a CDN, or the name did not resolve to the right entity. Try the exact legal name or the primary domain, or use the Telegram hints in §8.3. A genuinely small, well-run company can also simply have very little exposed — which is itself a finding worth saying."),
  H3("Can I get both English and German?"),
  P("Run it twice, once in each language. The German files carry a _DE suffix so nothing overwrites."),
  H3("Who do I ask for help?"),
  P("feranicus@s4biz.io."),
);

// ===== 13. CHEAT SHEET =====
add(
  H1("13. One-page cheat sheet"),
  P("Print this page.", { italics: true, color: GREY, after: 60 }),
  H2("Web, from nothing to decks"),
  plainTable([8, 92], [
    ["*1", "Go to www.cybergod.ai → Open the app"],
    ["*2", "Colt email + access password → Continue →"],
    ["*3", "6-digit code from your inbox → Verify & enter"],
    ["*4", "Type the company name"],
    ["*5", "Choose English or Deutsch"],
    ["*6", "Click Assess, wait 2–7 minutes"],
    ["*7", "Download the decks. Done."],
  ], { boldFirstCol: true }),
  SPACER(90),
  H2("Telegram, same thing"),
  code([
    "/auth name.familyname@colt.net <access-password>      ← then DELETE this message",
    "/verify 483920",
    "/assess Volkswagen AG --lang de",
  ]),
  SPACER(90),
  H2("The decks at a glance"),
  table([20, 46, 34], ["Deck", "Answers", "Audience"], [
    ["*Findings", "What is exposed", "Technical / IT security"],
    ["*C-BIQ", "What it costs in euros", "CFO, budget holder"],
    ["*GEOPOL", "Who would attack, and why", "CISO, board"],
    ["*DELTAS", "What the AI added", "Internal"],
  ], { boldFirstCol: true }),
  SPACER(90),
  H2("Numbers worth remembering"),
  plainTable([50, 50], [
    ["Code valid for", "10 minutes"],
    ["Wrong passwords before lockout", "5 (then 15 minutes)"],
    ["Session length", "12 hours"],
    ["Typical run", "2–7 minutes"],
    ["Security logs kept", "Up to 30 days"],
    ["Assessment history kept", "90 days (per the privacy notice)"],
    ["Where the data lives", "Frankfurt, Germany"],
    ["Help", "feranicus@s4biz.io"],
  ], { boldFirstCol: true }),
  SPACER(90),
  // NOTE: nothing after this. A trailing rule + tagline pushed a near-empty page 20; the document
  // deliberately ends ON the cheat sheet so the last page is the one people keep.
);

// ---------------------------------------------------------------- document
const doc = new Document({
  creator: "Colt / S4BIZ",
  title: "cybergod.ai — User Manual",
  description: "A-to-Z user manual for the cybergod.ai cyber pre-sales platform",
  styles: {
    default: { document: { run: { font: "Calibri", size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: DTEAL, font: "Calibri" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: NAVY, font: "Calibri" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: TEAL, font: "Calibri" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "coltBullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "▪", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 360, hanging: 220 } },
                     run: { color: TEAL, size: 21 } } },
          { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 220 } },
                     run: { color: GREY, size: 21 } } },
        ] },
      { reference: "coltSteps",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 400, hanging: 260 } },
                     run: { color: DTEAL, bold: true, size: 21 } } },
        ] },
    ],
  },
  sections: [{
    properties: {
      titlePage: true,          // page 1 is the cover: no running header/footer on it
      page: {
        margin: { top: 1134, right: 1134, bottom: 1134, left: 1134, header: 600, footer: 500 },
      },
    },
    headers: {
      first: new Header({ children: [new Paragraph({ children: [] })] }),
      default: new Header({ children: [new Paragraph({
        spacing: { after: 0 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE } },
        children: [
          new TextRun({ text: "❯ ", bold: true, size: 18, color: TEAL, font: "Calibri" }),
          new TextRun({ text: "colt", bold: true, size: 18, color: NAVY, font: "Calibri" }),
          new TextRun({ children: [new PositionalTab({
            alignment: PositionalTabAlignment.RIGHT, relativeTo: "margin",
            leader: PositionalTabLeader.NONE })] }),
          new TextRun({ text: "cybergod.ai — User Manual", size: 17, color: GREY, font: "Calibri" }),
        ],
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        spacing: { before: 0 },
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: LINE } },
        children: [
          new TextRun({ text: "» » » » »", size: 16, color: LINE, font: "Calibri" }),
          new TextRun({ children: [new PositionalTab({
            alignment: PositionalTabAlignment.RIGHT, relativeTo: "margin",
            leader: PositionalTabLeader.NONE })] }),
          new TextRun({ text: "Colt / S4BIZ · internal · ", size: 16, color: GREY, font: "Calibri" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: NAVY, bold: true, font: "Calibri" }),
        ],
      })] }),
    },
    children: [...cover, ...toc, ...body],
  }],
});

const outDir = path.join(__dirname);
fs.mkdirSync(outDir, { recursive: true });
const out = path.join(outDir, "cybergod.ai_User_Manual.docx");
Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(out, b);
  console.log("[ok] " + out + "  (" + (b.length / 1024).toFixed(0) + " KB)");
});
