// Customer-facing overview of our AI work, grouped BY PROJECT.
// Every model id below was read out of the file that sets it, not written from memory:
//   cybergod + Perseus panel  hermes-skills/shodan-assessment/scripts/enrich.py::_FALLBACKS,
//                             webapp/backend/app/shield_panel.py::MODELS, release_notes.py::MODELS
//   staging quorum            deploy/stagegate/quorum.py::SOLDIERS / AUDITORS
//   Cassandra                 webapp/backend/app/settings.py::ASSIST_MODEL / ASSIST_FALLBACK
//   JobHuntWow                jobhuntwow-app/backend/app/llm.py::DEFAULT_MODELS
//   endpoint                  OPENAI_BASE_URL default https://inference.do-ai.run/v1
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, BorderStyle,
  Table, TableRow, TableCell, WidthType, ShadingType, PageBreak,
} = require("docx");

const TEAL = "0C544E", ACCENT = "00B2A9", INK = "1D2B4E", MUT = "5A6478";
const W = 9360;

const P = (text, o = {}) => new Paragraph({
  spacing: { after: o.after === undefined ? 120 : o.after, line: 276 },
  children: [new TextRun({ text, size: o.size || 21, color: o.color || INK,
                           bold: !!o.bold, italics: !!o.italics, font: "Calibri" })],
});

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 150 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: ACCENT, space: 6 } },
  children: [new TextRun({ text, size: 27, bold: true, color: TEAL, font: "Calibri" })],
});

const H2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 60 },
  children: [new TextRun({ text, size: 22, bold: true, color: INK, font: "Calibri" })],
});

const KICKER = (text) => new Paragraph({
  spacing: { after: 140 },
  children: [new TextRun({ text, size: 20, color: MUT, italics: true, font: "Calibri" })],
});

// label / value table, used for the model roster and the technology line
const SPEC = (rows) => new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2200, 7160],
  rows: rows.map(([k, v], i) => new TableRow({
    children: [
      new TableCell({
        width: { size: 2200, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: i % 2 ? "FFFFFF" : "F2F7F6" },
        margins: { top: 90, bottom: 90, left: 140, right: 100 },
        children: [P(k, { bold: true, size: 19, color: TEAL, after: 0 })],
      }),
      new TableCell({
        width: { size: 7160, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: i % 2 ? "FFFFFF" : "F2F7F6" },
        margins: { top: 90, bottom: 90, left: 140, right: 140 },
        children: [P(v, { size: 19, after: 0 })],
      }),
    ],
  })),
});

const NOTE = (label, text) => new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [W],
  rows: [new TableRow({ children: [new TableCell({
    width: { size: W, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: "F2F7F6" },
    margins: { top: 140, bottom: 140, left: 180, right: 180 },
    children: [P(label, { bold: true, color: TEAL, size: 19, after: 40 }),
               P(text, { size: 20, after: 0 })],
  })] })],
});

// ------------------------------------------------------------------ projects
const PROJECTS = [
  {
    name: "Cybergod",
    kicker: "cybergod.ai  ·  external attack surface and compliance assessment",
    intro: "Cybergod tells a company what of theirs is visible from the internet and what that "
         + "exposure means, without touching their systems. An operator types a company name and "
         + "gets back a slide deck and an HTML report. The discovery and the severity are decided "
         + "by code; the models write the explanation a human reads.",
    items: [
      ["Writing the explanation for every finding",
       "Four models from four different vendors write the text that sits under each finding: what "
       + "was found, why it matters and what to do about it. The work is divided so every finding "
       + "gets written rather than whichever ones one model chose to answer, and a run that comes "
       + "back less than 80 per cent complete is reported as a quality failure instead of being "
       + "shipped. If the text a model returns does not name anything from the finding it was "
       + "written for, such as the port, the product or the CVE, it is thrown away and the "
       + "standard wording is used."],
      ["An independent second opinion on false positives",
       "A model from a different vendor than the one that wrote the report reviews every finding "
       + "against its evidence, looking for anything that belongs to a hosting provider, a content "
       + "delivery network or another company's tenancy. It may flag and it may not decide, "
       + "because ownership is settled by deterministic data. The different vendor is the point: "
       + "an outage or a blind spot is usually provider-wide."],
      ["Removing identifiers the model invented",
       "A CVE number reaches the report only if it appears in the raw scan data. Anything else is "
       + "stripped before the document is built and the removal is recorded. This is the one place "
       + "where a confident sentence is worse than no sentence, because the customer will look the "
       + "identifier up."],
      ["Compliance assessment, EU and Canada",
       "From a company name, a model produces a compliance assessment grounded only in a reference "
       + "document we maintain and version: NIS2, the Cyber Resilience Act and the EU AI Act for "
       + "Europe, and OSFI, PIPEDA, Law 25 and the CCSPA for Canada. It returns structured data "
       + "rather than prose that goes straight onto a slide, so a weaker model can only produce "
       + "weaker wording and never a broken document. The scoping assumptions it makes are printed "
       + "as assumptions and confirmed with the operator afterwards."],
      ["Reports in three languages",
       "Findings and compliance documents are produced in English, German and Russian, each with "
       + "its own dictionary and its own instructions to the model. A language is offered only once "
       + "both are complete, so nobody can send a customer a document that is half translated."],
    ],
    spec: [
      ["Models", "deepseek-3.2 (DeepSeek), llama-4-maverick (Meta), gemma-4-31B-it (Google), "
               + "kimi-k2.6 (Moonshot), tried in that order. The order is not a preference: it is "
               + "the measured speed and reliability on our own prompt."],
      ["Served by", "DigitalOcean Serverless Inference, OpenAI-compatible API. No model is "
                  + "self-hosted and no customer data is used for training."],
      ["Built with", "Python, Shodan, Certificate Transparency and DNS for discovery, pptxgenjs for "
                   + "the PowerPoint decks, Node for the HTML reports, FastAPI and React for the "
                   + "web application, SQLite, Docker."],
      ["Delivery", "Web application and a Telegram bot. The engine ships inside both."],
    ],
  },

  {
    name: "Perseus Shield",
    kicker: "automated defence  ·  six properties on one brain",
    intro: "Perseus watches the live traffic of six properties, decides what is hostile and acts "
         + "within limits written into the code. Detection is deterministic. The models are used "
         + "for the part code is bad at, which is reading a new pattern of behaviour and saying "
         + "what it looks like.",
    items: [
      ["Four vendors on one incident, while it is happening",
       "Every ten minutes the system checks whether something is going on that deserves attention, "
       + "and if so asks the four models about that single incident rather than about a daily "
       + "summary. They see the deterministic facts first and their answers are stored beside "
       + "those facts. They may propose a way to detect the behaviour and nothing else: no model "
       + "can block an address, change a limit or touch the emergency stop. The loop is capped at "
       + "twelve incidents and roughly thirty cents a day."],
      ["A nightly review that proposes new detection",
       "Once a day the panel reads what the estate saw and proposes patterns for behaviour the "
       + "current rules miss. Each proposal passes five independent checks that fail closed, "
       + "including compiling cleanly and matching nothing on any real page of any of the six "
       + "properties. Before a pattern may act it must spend a full day in detection only, be "
       + "agreed by three of the four vendors, match something hostile at least once and match "
       + "nothing legitimate. A rule that starts refusing traffic which looks legitimate is "
       + "demoted automatically."],
      ["A review of the defence's own decisions",
       "Every six hours the same four models review what the shield actually did and why. They may "
       + "adjust six numeric thresholds, and only inside limits written into the code rather than "
       + "into a file someone can edit. The blocking logic, the allow list and the cap on how much "
       + "traffic can ever be affected are beyond their reach."],
      ["A daily digest of what is new",
       "A threshold review can only look at traffic the detector already understands, so a "
       + "genuinely new technique scores nothing, is never blocked and is invisible precisely "
       + "because it is new. The digest looks at the opposite set, the requests that were not "
       + "classified, and reports what changed since yesterday. Anything it proposes goes through "
       + "the same vetting as everything else."],
    ],
    spec: [
      ["Models", "The same four as Cybergod: deepseek-3.2, llama-4-maverick, gemma-4-31B-it, "
               + "kimi-k2.6. Two act as soldiers and two as auditors."],
      ["Protects", "cybergod.ai, jobhuntwow.com, klimaanlage-preise.de, s4biz.io, jev.best and "
                 + "godeyes.ai, from one shared brain."],
      ["Built with", "Python, Grafana Loki as the log substrate, systemd timers, enforcement at "
                   + "the HTTP layer inside our own containers. It never touches the host "
                   + "firewall, because the host is shared."],
      ["Hard boundary", "No model call sits in the path of a visitor's request, so a slow or "
                      + "unavailable model can never slow down or break a protected site."],
    ],
  },

  {
    name: "Cassandra",
    kicker: "pre-sales assistant  ·  web application and Telegram",
    intro: "Cassandra answers questions about accounts, opportunities and outreach, and helps "
         + "write the follow-up. It is the one place in the platform where a person talks to a "
         + "model directly and expects a conversation back.",
    items: [
      ["Research on an allowlisted set of sources",
       "When a question needs current information, Cassandra fetches it from a fixed list of "
       + "allowed sources. It tries a cheap page request first and falls back to a full browser "
       + "only when a site refuses to render without one, which keeps the common case fast and "
       + "inexpensive."],
      ["Fetched pages are data, never instructions",
       "Anything retrieved from the web is handed to the model as material to read, not as "
       + "commands to follow. That is the defence against a page written to give an assistant "
       + "orders, which is the first item on the OWASP list of risks for this kind of system. "
       + "Access to the assistant uses the same identity rules as the rest of the platform."],
    ],
    spec: [
      ["Models", "deepseek-3.2 as the main model, openai-gpt-oss-120b as the fallback when it is "
               + "unavailable."],
      ["Built with", "FastAPI and React for the web version, python-telegram-bot for the chat "
                   + "version, Playwright with headless Chromium for the research fallback."],
    ],
  },

  {
    name: "JobHuntWow",
    kicker: "jobhuntwow.com  ·  a browser agent that completes job applications",
    intro: "A separate product. It drives a real browser to complete job applications on employer "
         + "systems, and it is the implementation where model choice mattered most, because every "
         + "action in the loop costs a round trip to a model and the candidate is waiting.",
    items: [
      ["Deterministic first, model only where it has to be",
       "Navigation, signing in and the steps that are the same on every employer system are done "
       + "by code with no model involved. A model is used only for the screening questions that "
       + "vary between employers. When it does not know an answer it stops and asks the person "
       + "rather than inventing one, and it always stops at the review screen so a human presses "
       + "submit."],
      ["A different model for each job, chosen by measurement",
       "Roles are split across models and vendors: one answers screening questions, one drives the "
       + "page, one reads screenshots, one writes the prose, and one does nothing but language, "
       + "turning machine state into a sentence a person can answer. Each was picked from a "
       + "bake-off against our own task rather than from a benchmark. Two well-known models were "
       + "rejected for the driver loop purely on latency, at roughly 28 and 92 seconds per action."],
      ["A spend allowlist on the model proxy",
       "The product exposes an OpenAI-compatible endpoint, which means a caller can name the model "
       + "they want. Only models we chose, measured and priced are accepted, with named exceptions "
       + "if we add one deliberately. This exists because an endpoint that forwards a "
       + "caller-chosen model id to a paid service is a payment endpoint."],
    ],
    spec: [
      ["Screening answers", "deepseek-3.2, then mistral-3-14B, then llama-4-maverick. Three "
                          + "vendors, so one provider outage does not stop the run."],
      ["Page driver", "mistral-3-14B for the fast single-action loop, measured at about 0.6 "
                    + "seconds per action, with nemotron-nano-12b-v2-vl as backup."],
      ["Reading screenshots", "nemotron-nano-12b-v2-vl (NVIDIA)."],
      ["Writing to the candidate", "kimi-k2.6 (Moonshot), whose only job is language. It never "
                                 + "votes on an action."],
      ["Built with", "Python, Playwright and browser-use for the browser work, FastAPI, React, "
                   + "Docker."],
    ],
  },

  {
    name: "The delivery platform",
    kicker: "how the above gets built, reviewed and released",
    intro: "We use the same panel on ourselves. This is included because it is a fair question "
         + "from a buyer who wants to know whether we run our own product the way we describe it.",
    items: [
      ["A review panel on every release",
       "Before anything reaches production it is deployed to an identical second server, that "
       + "server is rebooted, and every check runs again. Two models act as soldiers and two as "
       + "auditors, each reading the evidence from that run and writing a go or no-go verdict with "
       + "its reasons and its risks. The panel is advisory and a model verdict never overrides a "
       + "deterministic check in either direction. When the panel is right about something we turn "
       + "it into a check rather than a note."],
      ["Release notes written by the panel and actually sent",
       "The same four models write the notes for every release and they go out by email and "
       + "Telegram instead of sitting in a log. They are sent for a failed release too, because "
       + "that is the one somebody needs to read."],
      ["Watching for new models",
       "The platform we run on adds and removes models regularly, and a model id is an external "
       + "fact that changes without telling anyone. We detect anything new, check whether the "
       + "account is actually entitled to it, and test it against the contract our code depends on "
       + "before it goes anywhere near a customer deliverable."],
    ],
    spec: [
      ["Soldiers", "deepseek-3.2, llama-4-maverick."],
      ["Auditors", "gemma-4-31B-it, kimi-k2.6."],
      ["Built with", "GitHub Actions, Docker, an identical staging server that is rebooted on every "
                   + "release, container vulnerability scanning, secret scanning and a software "
                   + "bill of materials."],
    ],
  },
];

const PRINCIPLES = [
  ["Models propose, code decides.",
   "Nothing a model says can block an address, change a limit, deploy a release or alter a "
   + "finding's severity. Those are deterministic code paths and they stay that way."],
  ["Four vendors, not four models.",
   "A rate limit or an outage is provider-wide, so four models at one vendor would be four hats on "
   + "one head. A model that is simply wrong is contradicted by three others rather than believed."],
  ["No model sits in the request path.",
   "Every model call happens out of band, so a slow response or a provider outage can never make a "
   + "protected site slow or unavailable."],
  ["One place where money can be spent.",
   "Every model call in the assessment engine goes through a single function that prices it and "
   + "records who made it. The daily budget is checked before the request is issued, with a default "
   + "ceiling of three dollars a day. If the budget is reached the call is refused."],
  ["Absence of evidence is never a finding.",
   "When a lookup fails, the report says the answer is unknown and claims no gap."],
  ["Nothing is sent to the company being assessed.",
   "A Cybergod assessment is built from data that is already public. Not one packet reaches the "
   + "company's own systems, which is why no authorisation from them is needed."],
];

// ------------------------------------------------------------------ build
const body = [];

body.push(new Paragraph({ spacing: { after: 60 },
  children: [new TextRun({ text: "S4BIZ GROUP", size: 18, bold: true, color: ACCENT,
                           font: "Calibri", characterSpacing: 60 })] }));
body.push(new Paragraph({ spacing: { after: 100 },
  children: [new TextRun({ text: "Our AI work, project by project", size: 40, bold: true,
                           color: TEAL, font: "Calibri" })] }));
body.push(P("What each product uses language models for, which models, and what they are not "
          + "allowed to do. Prepared 26 October 2026.", { color: MUT, size: 20, after: 240 }));

body.push(P("Five projects, each with its own job and its own model roster. Every model named here "
          + "was chosen by measuring it against our own task, and every one of them is reachable "
          + "through a single provider interface, so swapping one is a configuration change rather "
          + "than a rewrite.", { after: 160 }));

body.push(NOTE("Why four models and four vendors keeps coming up",
  "Three of the five projects ask several models the same question and compare the answers. The "
  + "vendors are deliberately different, because a rate limit or an outage affects a whole vendor "
  + "at once, so four models from one company would fail together. It also means a model that has "
  + "misread something is contradicted by three others instead of believed. The four are "
  + "deepseek-3.2 from DeepSeek, llama-4-maverick from Meta, gemma-4-31B-it from Google and "
  + "kimi-k2.6 from Moonshot."));

for (const pr of PROJECTS) {
  body.push(new Paragraph({ children: [new PageBreak()] }));
  body.push(H1(pr.name));
  body.push(KICKER(pr.kicker));
  body.push(P(pr.intro, { after: 160 }));
  for (const [h, t] of pr.items) { body.push(H2(h)); body.push(P(t)); }
  body.push(P("", { after: 60 }));
  body.push(SPEC(pr.spec));
}

body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(H1("The rules that apply to all of them"));
for (const [h, t] of PRINCIPLES) {
  body.push(new Paragraph({ spacing: { before: 130, after: 100, line: 276 }, children: [
    new TextRun({ text: h + "  ", bold: true, size: 21, color: INK, font: "Calibri" }),
    new TextRun({ text: t, size: 21, color: INK, font: "Calibri" }),
  ] }));
}

body.push(H1("Honest limits"));
body.push(NOTE("What we say before a customer has to ask",
  "A passive assessment cannot see a website hidden behind a shared front end, and in that case we "
  + "say so rather than reporting an empty result as a clean one. No public source is authoritative "
  + "for address ownership everywhere in the world, so on a company that owns its own address space "
  + "we ask rather than assume. A mail signature cannot be enumerated, so a missing one is reported "
  + "as not determinable rather than as a failure. And a panel of four models is evidence, not "
  + "proof: on at least one recorded occasion all four agreed on something that was wrong, which is "
  + "why none of them is allowed to act alone."));

const doc = new Document({
  creator: "S4Biz Group",
  title: "Our AI work, project by project",
  description: "Customer-facing overview of every LLM implementation, grouped by product",
  sections: [{
    properties: { page: { margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    children: body,
  }],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync(process.argv[2], b);
  console.log("wrote " + process.argv[2] + "  (" + b.length + " bytes)");
});
