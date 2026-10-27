// Builds the customer-facing overview of every LLM implementation we run in production.
// Every item below was traced to the file that performs it before it was written down.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle,
  Table, TableRow, TableCell, WidthType, ShadingType,
} = require("docx");

const TEAL = "0C544E";
const ACCENT = "00B2A9";
const INK = "1D2B4E";
const MUT = "5A6478";

const P = (text, o = {}) => new Paragraph({
  spacing: { after: o.after === undefined ? 120 : o.after, line: 276 },
  alignment: o.align,
  children: [new TextRun({
    text, size: o.size || 21, color: o.color || INK, bold: !!o.bold,
    italics: !!o.italics, font: "Calibri",
  })],
});

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 320, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: ACCENT, space: 6 } },
  children: [new TextRun({ text, size: 26, bold: true, color: TEAL, font: "Calibri" })],
});

const H2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 220, after: 60 },
  children: [new TextRun({ text, size: 23, bold: true, color: INK, font: "Calibri" })],
});

const NOTE = (label, text) => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [9360],
  rows: [new TableRow({
    children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "F2F7F6" },
      margins: { top: 140, bottom: 140, left: 180, right: 180 },
      children: [
        P(label, { bold: true, color: TEAL, size: 19, after: 40 }),
        P(text, { size: 20, after: 0 }),
      ],
    })],
  })],
});

// ---------------------------------------------------------------- the inventory
const SECTIONS = [
  {
    title: "Security assessment",
    lead: "These run when we assess a company's internet-facing estate and produce the report the "
        + "customer receives.",
    items: [
      ["Writing the explanation for every finding",
       "When the scan is finished, four language models from four different vendors write the "
       + "explanation that sits under each finding: what was found, why it matters and what to do "
       + "about it. The work is divided so that every finding gets written, rather than whichever "
       + "ones a single model chose to answer, and a run that comes back less than 80 per cent "
       + "complete is reported as a quality failure instead of being shipped. Each model only ever "
       + "sees the finding it is writing about. If the text it returns does not name anything from "
       + "that finding, such as the port, the product or the CVE, the text is discarded and the "
       + "standard wording is used instead."],

      ["An independent second opinion on false positives",
       "A separate model, from a different vendor than the one that wrote the report, reviews every "
       + "finding against the evidence behind it. Its job is to spot anything that actually belongs "
       + "to a hosting provider, a content delivery network or another company's tenancy rather "
       + "than to the customer. It is allowed to flag, and it is not allowed to decide: ownership "
       + "is settled by deterministic data, not by an opinion. Using a different vendor matters "
       + "because an outage or a blind spot tends to be provider-wide."],

      ["Removing identifiers the model invented",
       "A CVE number appears in the report only if it is present in the raw scan data. Anything "
       + "else a model produced is stripped out before the document is built, and the removal is "
       + "recorded in the run log. This is the one place where a confident sentence is more "
       + "dangerous than no sentence at all, because a customer will go and look the identifier "
       + "up."],

      ["Compliance assessment against NIS2, the CRA and the EU AI Act",
       "Given a company name, a model produces a compliance assessment grounded only in a "
       + "reference document we maintain and version. It returns structured data rather than prose "
       + "that goes straight onto a slide, so the layout and the wording of the deliverable are the "
       + "same every time and a weaker model can only produce weaker wording, never a broken "
       + "document. The scoping assumptions it makes, such as sector and company size, are printed "
       + "as assumptions and confirmed with the operator afterwards. A Canadian set covering OSFI, "
       + "PIPEDA and Law 25 works the same way."],

      ["Reports in three languages",
       "The findings and compliance documents are produced in English, German and Russian. Each "
       + "language has its own dictionary and its own instructions to the model, and a language is "
       + "only offered to the operator once both are complete. Half a translation is treated as no "
       + "translation, so nobody can accidentally send a customer a document in two languages at "
       + "once."],
    ],
  },
  {
    title: "Automated defence",
    lead: "These run continuously on live traffic across the properties we protect. None of them "
        + "sits in the path of a visitor's request, so a slow or unavailable model can never slow "
        + "down or break a website.",
    items: [
      ["Four vendors looking at one incident while it is happening",
       "Every ten minutes the system checks whether something is currently happening that deserves "
       + "attention, and if so it asks the four models about that single incident rather than about "
       + "a daily summary. They are shown the deterministic facts first and their answers are "
       + "recorded beside those facts. They may propose a way to detect the behaviour and nothing "
       + "else: no model can block an address, change a limit or touch the emergency stop. The "
       + "whole loop is capped at twelve incidents and roughly thirty cents a day."],

      ["A nightly review that proposes new detection",
       "Once a day the panel reads what the estate saw and proposes patterns for behaviour the "
       + "current rules do not recognise. Every proposal then has to pass five independent checks "
       + "that fail closed, including compiling cleanly and matching nothing on any real page of "
       + "any of our sites. Before a pattern is ever allowed to act it must spend a full day in "
       + "detection-only mode, be agreed by three of the four vendors, match something hostile at "
       + "least once and match nothing legitimate. A rule that starts refusing traffic that looks "
       + "legitimate is demoted automatically."],

      ["A review of the defence's own decisions",
       "Every six hours the same four models review what the defence actually did and why. They "
       + "may adjust six numeric thresholds, and only within limits that are written into the code "
       + "rather than into a configuration file someone can edit. Everything outside those six "
       + "numbers, including the blocking logic, the allow list and the cap on how much traffic can "
       + "ever be affected, is beyond their reach."],

      ["A daily digest of what is new",
       "A threshold review can only ever look at traffic the detector already understands, which "
       + "means a genuinely new technique scores nothing, is never blocked and is therefore "
       + "invisible exactly because it is new. The daily digest looks at the opposite set: the "
       + "requests that were not classified. The models summarise what changed since yesterday and "
       + "say what they would propose, and the proposals go through the same vetting as everything "
       + "else."],
    ],
  },
  {
    title: "Assistants people use directly",
    lead: "",
    items: [
      ["Cassandra, the pre-sales assistant",
       "Cassandra answers questions about accounts, opportunities and outreach, and is available "
       + "both in the web application and as a Telegram bot. It can do live research on an "
       + "allowlisted set of sources, trying a cheap page fetch first and falling back to a full "
       + "browser only when a site needs one. Anything it fetches from the web is treated as data "
       + "and never as instructions, which is the defence against a page that tries to give the "
       + "assistant orders. Access is controlled by the same identity rules as the rest of the "
       + "platform."],

      ["Job application agent (a separate product)",
       "Our job search product drives a real browser to complete applications. The deterministic "
       + "part does the navigation and the known steps; a model is used only for the screening "
       + "questions that vary between employers. When it does not know an answer it stops and asks "
       + "the person rather than inventing one, and it always stops at the review screen so a human "
       + "presses submit. The model is never the thing that navigates the job board or signs in; "
       + "those steps are deterministic and the model is not involved in them."],
    ],
  },
  {
    title: "How we build and release the platform",
    lead: "We use the same panel on ourselves. These are included because they are a fair question "
        + "from a buyer who wants to know whether we practise what we sell.",
    items: [
      ["A review panel on every release",
       "Before anything reaches production it is deployed to an identical second server, that "
       + "server is rebooted, and every check is run again. Two models act as soldiers and two as "
       + "auditors, each reading the evidence from that run and writing a go or no-go verdict with "
       + "its reasons and its risks. The panel is advisory. A model verdict never overrides a "
       + "deterministic check in either direction, and we act on what the panel gets right by "
       + "turning it into a check."],

      ["Release notes written by the panel and actually sent",
       "The same four models write the release notes for every release, and the notes are "
       + "delivered by email and Telegram rather than being left in a log. They are sent on a "
       + "failed release too, because the release that went wrong is the one somebody needs to read "
       + "about."],

      ["Watching for new models",
       "The platform we run on adds and removes models regularly. We detect anything new, check "
       + "whether the account is actually entitled to it, and test it against the contract our code "
       + "depends on before it is allowed anywhere near a customer deliverable. A model that fails "
       + "that test is reported with the reason and is not used."],
    ],
  },
  {
    title: "Keeping the cost predictable",
    lead: "",
    items: [
      ["One place where money can be spent",
       "Every call to a model in the assessment engine goes through a single function, which prices "
       + "it per direction and records who made it. The daily budget is checked before the request "
       + "is issued rather than after the bill arrives, and the default ceiling is three dollars a "
       + "day. If the accounting storage itself fails the call is allowed and the failure is "
       + "reported, because losing a report to a bookkeeping problem would be the wrong trade. If "
       + "the budget is reached the call is refused. Separately, an hourly job compares our own "
       + "metered total against the provider's balance and names any model that is new today."],
    ],
  },
];

const PRINCIPLES = [
  ["Models propose, code decides.",
   "Nothing a model says can block an address, change a limit, deploy a release or alter a "
   + "finding's severity. Those are deterministic code paths and they stay that way."],
  ["No model sits in the request path.",
   "Every model call happens out of band. A rate limit, a slow response or a provider outage can "
   + "never make a protected website slow or unavailable."],
  ["Four vendors, not four models.",
   "A rate limit or an outage is provider-wide, so four models at one vendor would be four hats on "
   + "one head. A model that is simply wrong is contradicted by three others rather than believed."],
  ["Absence of evidence is never a finding.",
   "When a lookup fails, the report says the answer is unknown and claims no gap. We would rather "
   + "say less than say something a customer cannot verify."],
  ["Nothing is sent to the company being assessed.",
   "The assessment is built from data that is already public. Not one packet reaches the company's "
   + "own systems, which is why no authorisation from them is needed."],
];

// ---------------------------------------------------------------- build
const body = [];

body.push(new Paragraph({
  spacing: { after: 60 },
  children: [new TextRun({ text: "S4BIZ GROUP", size: 18, bold: true, color: ACCENT,
                           font: "Calibri", characterSpacing: 60 })],
}));
body.push(new Paragraph({
  spacing: { after: 100 },
  children: [new TextRun({ text: "AI in our products, explained", size: 40, bold: true,
                           color: TEAL, font: "Calibri" })],
}));
body.push(P("A plain description of every place we use a large language model in production, what "
          + "it does and what it is not allowed to do. Prepared " + "26 October 2026" + ".",
          { color: MUT, size: 20, after: 240 }));

body.push(P("This is written for a reader who does not need to know how any of it is built. Each "
          + "entry is a capability that runs today, not a plan. The last page sets out the five "
          + "rules that govern all of them, and the honest limits.", { after: 200 }));

for (const sec of SECTIONS) {
  body.push(H1(sec.title));
  if (sec.lead) body.push(P(sec.lead, { color: MUT, size: 20, after: 140 }));
  for (const [h, t] of sec.items) {
    body.push(H2(h));
    body.push(P(t));
  }
}

body.push(H1("What all of them have in common"));
for (const [h, t] of PRINCIPLES) {
  body.push(new Paragraph({
    spacing: { before: 140, after: 100, line: 276 },
    children: [
      new TextRun({ text: h + "  ", bold: true, size: 21, color: INK, font: "Calibri" }),
      new TextRun({ text: t, size: 21, color: INK, font: "Calibri" }),
    ],
  }));
}

body.push(H1("Honest limits"));
body.push(NOTE("What we tell customers before they ask",
  "A passive assessment cannot see a website hidden behind a shared front end, and in that case we "
  + "say so rather than reporting an empty result as a clean one. No public source is authoritative "
  + "for address ownership everywhere in the world, so on a company that owns its own address space "
  + "we ask rather than assume. A mail signature cannot be enumerated, so a missing one is reported "
  + "as not determinable rather than as a failure. And a panel of four models is evidence, not "
  + "proof: on at least one recorded occasion all four agreed on something that was wrong, which is "
  + "why none of them is allowed to act alone."));

body.push(P("", { after: 120 }));
body.push(P("Delivery is through the web application and a Telegram bot. The assessment engine "
          + "itself ships in both, so a customer can start a run by typing a company name in "
          + "either place.", { color: MUT, size: 20 }));

const doc = new Document({
  creator: "S4Biz Group",
  title: "AI in our products, explained",
  description: "Customer-facing overview of every LLM implementation in production",
  sections: [{
    properties: { page: { margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    children: body,
  }],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync(process.argv[2], b);
  console.log("wrote " + process.argv[2] + "  (" + b.length + " bytes)");
});
