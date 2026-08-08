// partners-locales/en.js — the English (reference) content for /partners.
//
// ============================================================================================
// WHY THIS IS DATA AND NOT JSX, AND WHY IT IS NOT IN THE STRING CATALOGUE
// ============================================================================================
// Two separate decisions, both deliberate.
//
// 1. DATA, NOT MARKUP. Partners.jsx renders THIS OBJECT. The layout therefore lives in exactly one
//    place and only the text varies by language. That is the same doctrine as the GEOPOL HTML
//    builder: a fixed shell with text injected, so a translation can never move a box, drop a
//    column or reorder a page. `test_partners.py` asserts every locale has the identical section
//    ids, the same number of columns and the same number of bullets, so drift is a failed build
//    rather than a customer noticing.
//
// 2. ITS OWN LOCALE FOLDER, following legal-locales/ and NOT locales/.
//    The by-English key space in locales/*.js exists for the ~200 sentences scattered through
//    Landing.jsx. This page is ~450 strings of long-form prose that only ever appear here. Putting
//    them in the shared catalogue would triple gap.*.json and bury a real missing nav label under
//    four hundred marketing sentences. legal-locales/ already established the pattern for exactly
//    this shape of content. The ONE string that belongs in the shared space is the nav label
//    ("nav.partners"), because that is chrome, not content.
//
// FALLBACK: partners-locales/index.js resolves reader language -> English. A locale that is
// missing or incomplete degrades to readable English, never to a blank page. Same rule as
// everything else in this codebase.
//
// ============================================================================================
// CONTENT RULES THAT ARE ENFORCED BY A TEST, NOT BY MEMORY (tools/partners_gate.mjs)
// ============================================================================================
//   · NO PRICES, anywhere, in any language. No currency figures, no percentages off, no seat
//     counts, no setup fees. Commercial terms are agreed directly. A price on a public page is a
//     negotiating position given away for free, and it goes stale the day a tier changes.
//   · NO LONG DASHES. The operator reads them as noise. Commas, colons, full stops, brackets.
//   · NO UNEXPANDED ABBREVIATIONS in the English source: due diligence, systems integrator,
//     programming interface, security monitoring, and so on are written out.
//   · NO SENTENCE OVER 30 WORDS.
//   · NO NAMED CUSTOMER, ever. The engineer quote is anonymised down to what the argument needs.
//
// STRUCTURE is the Minto pyramid as the strategy houses actually teach it: Situation, then
// Complication, then a single governing-thought Answer, then three grouped supports, then
// evidence, then the next step. Sources are in the commit message; the short version is that a
// heading states a conclusion and every element must survive the question "so what".

export const meta = {
  docTitle: "Who it is for",
  kicker: "One name in. Four board-ready documents out. Eleven audiences.",
  h1a: "Type a company name.",
  h1b: "Get the ",
  h1c: "whole risk picture",
  h1d: " in minutes.",
  lede:
    "Not one packet is sent to the company being assessed. Everything is built from sources any " +
    "researcher may lawfully consult. So there is nothing to install, nobody to ask for " +
    "permission, and no questionnaire to wait for. Four documents come back every time.",
  artsNote:
    "There is also a fifth document: a single self-contained web report that combines all four and " +
    "opens in any browser. That is the one people forward internally. Every document is available " +
    "in English, German or Russian.",
  railTitle: "Who it is for",
  groupPartners: "Partners",
  groupBuyers: "Buyers",
  groupEngage: "How to engage",
  foot:
    "Content is drawn from the partner and regulator briefing material and the signed legal pack. " +
    "No prices, discounts, seat counts or commitments appear anywhere, by design. Partner meeting " +
    "volumes are as reported by those partners and depend on the individual sales person. " +
    "Assessment output is not legal advice. All references to identified customers are removed.",
};

export const arts = [
  { n: "1", name: "Findings", body:
    "Every exposure facing the internet, ranked Critical to Low. Each one states what it is, why " +
    "it matters, how to fix it, and the exact address and port it was seen on." },
  { n: "2", name: "Risk in money", body:
    "The same findings expressed in currency, using the recognised Factor Analysis of Information " +
    "Risk method. Cost of one incident, worst case per year, and a curve that falls as findings " +
    "close. Written for the finance director." },
  { n: "3", name: "Threat actors", body:
    "Which attackers are actually relevant to this industry and these countries, and how they " +
    "operate. The answer to the board asking who would come for us." },
  { n: "4", name: "Compliance", body:
    "Findings mapped to the clauses of the laws that apply where the company operates, with the " +
    "real deadlines. European Union and Canada today." },
];

export const sections = [
  // ------------------------------------------------------------------ MANAGED SERVICE PROVIDERS
  {
    id: "msp", group: "partners", nav: "Managed service providers",
    eyebrow: "Partner", h2: "For managed service providers",
    scr: {
      s: "You run security for many customers at once, with a team that cannot grow as fast as your customer list.",
      c: "Reviewing one customer's exposure by hand costs about a day of analyst time. At scale that does not happen, so the quarterly business review becomes a status update nobody sets a budget against.",
      a: "Assess every customer in your book on the same schedule, at a cost that does not rise with the number of customers. Then sell the fix at four separate price points.",
    },
    cols: [
      { h: "1. What you sell", li: [
        "The assessment itself, priced, under your own name.",
        "A monthly or quarterly repeat with a report of what changed. That report is the managed service.",
        "Licences, sold in packs or on an unlimited basis, which you earn on in their own right.",
      ] },
      { h: "2. Why the cost works", li: [
        "One analyst covers your whole book instead of one account.",
        "Starting a customer needs nothing from them: no software to install, no access, no form.",
        "The compliance document answers the auditor in the same run, so there is no second engagement to staff.",
      ] },
      { h: "3. Where the margin is", li: [
        "Not in the report. In the four ways to close a finding, set out below.",
        "Your account managers gain a reason to call every customer, every month, with news.",
        "A closed finding proves the retainer works, which is the hardest thing in security to demonstrate.",
      ] },
    ],
    ladder: { h: "The four ways to close a finding, cheapest first", items: [
      { b: "Advice.", t: "A workshop that walks every finding against what the customer already owns." },
      { b: "No new spend, using their own equipment.", t: "Most findings close through configuration, placement and process changes on products they already pay for. You deliver a list of actions, each mapped to the tool that closes it." },
      { b: "Open source.", t: "Where existing equipment cannot close the gap, a design built on open source instead of a purchase. There is no licence to buy. The cost moves to skills and operation, which the customer either hires or buys from you." },
      { b: "A commercial product.", t: "Only where neither of the above works. Selection stays inside the customer's approved supplier list. You advise on fit, sequence and integration." },
    ] },
    win: { h: "The claim, stated plainly", p:
      "A single report is a project. A monthly report of what changed is a subscription. You are " +
      "selling the finding and the route to fixing it, at four price points, to a customer who " +
      "already trusts you." },
    steps: [
      { k: "Week 1", v: "Run your ten largest accounts and read what comes back." },
      { k: "Week 2", v: "Send one finding to each. See the method below." },
      { k: "Week 3", v: "Put your brand on it and price it into your managed tier." },
    ],
    cta: { btn: "Talk to us", txt: "Licence packs, unlimited plans, tiers and terms are commercial. Please ask." },
  },

  // ------------------------------------------------------------------------------- RESELLERS
  {
    id: "var", group: "partners", nav: "Resellers",
    eyebrow: "Partner", h2: "For resellers",
    scr: {
      s: "You sell technology, and you win on relationship, timing and the quality of the conversation you can start.",
      c: "The first technical meeting is the hardest thing to get. The usual substitute is a discount, which costs you margin and teaches the customer to wait for the next one.",
      a: "Walk in already knowing what is exposed on their perimeter. Charge properly for the assessment, then credit its value against the work it uncovers.",
    },
    cols: [
      { h: "1. How it is priced", li: [
        "The assessment is a paid, fixed-scope engagement. It is not a giveaway.",
        "Its value is then credited against the advice or remediation work that follows.",
        "The customer therefore risks nothing, and you are paid either way.",
      ] },
      { h: "2. What else you earn on", li: [
        "Licences, in packs or on an unlimited basis, as a second and recurring line.",
        "All four ways to close a finding: advice, their own equipment, open source, or an approved product.",
        "Repeat runs, which show what changed and reopen the conversation on a schedule.",
      ] },
      { h: "3. What your sales team gains", li: [
        "A reason to call anyone, with something specific to say.",
        "New logos: you need no permission and no access, so you can do the work before you are invited.",
        "Renewal defence: run it before a competitor's renewal date and show what changed.",
      ] },
    ],
    win: { h: "The claim, stated plainly", p:
      "A discount buys one deal. Knowing more about their perimeter than they do buys the " +
      "relationship, and this time you are paid for the work that got you in." },
    steps: [
      { k: "Day 1", v: "Pick five prospects you cannot get a meeting with." },
      { k: "Day 2", v: "Send one finding to each. Never the report." },
      { k: "Day 5", v: "Take the meeting. Price the assessment. Credit it forward." },
    ],
    cta: { btn: "Talk to us", txt: "Referral, resale, licence and white-label routes all exist. Terms on request." },
  },

  // ------------------------------------------------------------------------------ THE METHOD
  {
    id: "play", group: "partners", nav: "The opening method", accent: "gold",
    eyebrow: "Every partner uses this", h2: "Send one finding. Hold the report back.",
    scr: {
      s: "You have run the assessment and you are holding a document with everything in it.",
      c: "A prospect who did not ask for a report reads it as a sales document and puts it aside. A full report also asks for a meeting slot nobody has this quarter.",
      a: "Send exactly one finding, with its evidence and how to fix it. The single finding is what wins you the meeting. The report is what you sell inside it.",
    },
    quote: {
      q: "I do not see this address in our asset system at all.",
      by: "A network security engineer at a large regulated enterprise, watching a live run. The " +
          "platform had surfaced an address attributed to his own organisation. He could not find " +
          "it in the internal asset register. Company, sector and details withheld.",
    },
    cols: [
      { h: "How to run it", li: [
        "Run the assessment, read the findings, and pick exactly one.",
        "Send that finding, with the evidence and the advice on fixing it.",
        "Do not attach the report. Remove identifying detail if the approach is cold.",
        "Ask for thirty minutes to walk through the rest.",
      ] },
      { h: "Why one finding beats a report", li: [
        "**An unknown asset is the strongest kind of finding.** An address outside the asset register is outside patching, scanning and reporting, and asset inventory sits at the base of every security standard they are audited against.",
        "**It survives scepticism.** A known finding gets \"another team handles that\". An address nobody can account for cannot be answered that way.",
        "**It fits the room.** It lands with the team you are already talking to, not a department nobody in the meeting controls.",
        "**It prices itself.** One unmanaged host facing the internet is cheap to argue about and expensive to ignore.",
      ] },
    ],
    win: { h: "What partners report", p:
      "Partners in Germany and Switzerland using this method report six to ten new first meetings " +
      "per sales person per week. It clearly depends on the individual seller's ability to turn a " +
      "fact into a conversation, so we would rather you heard it from them. We will arrange the call." },
    cta: { btn: "Ask for a reference call", ghost: true, txt: "Reference partners available in the German-speaking market." },
  },

  // --------------------------------------------------------------------- SYSTEMS INTEGRATORS
  {
    id: "gsi", group: "partners", nav: "Systems integrators",
    eyebrow: "Partner", h2: "For systems integrators",
    scr: {
      s: "Discovery is the first phase of every security and transformation programme you run.",
      c: "It is billed at consultant rates, done by hand, different on every engagement, and it is the invoice clients argue about. Yet nothing after it is valid without it.",
      a: "Make discovery a fixed, fast, identical step on every engagement, so your margin moves to architecture and remediation, where it belongs.",
    },
    cols: [
      { h: "1. Where it goes in the method", li: [
        "Discovery becomes an input to your methodology, not a replacement for it.",
        "A baseline at the start of the programme, then a repeat at each stage gate.",
        "Progress is evidenced by what closed, rather than asserted in a status report.",
      ] },
      { h: "2. Where else it applies", li: [
        "Assessing a supplier without waiting for the supplier to cooperate.",
        "Scoping a newly acquired business before its network is joined to the parent.",
        "Any country or subsidiary where you have no local team.",
      ] },
      { h: "3. What it changes commercially", li: [
        "You stop selling weeks of fact-finding and start selling the outcome it was blocking.",
        "The money document prices the programme in the finance director's language on day one.",
        "Every finding carries its evidence, so it survives the client's own technical review.",
      ] },
    ],
    win: { h: "The claim, stated plainly", p:
      "The first invoice stops being the one your client disputes, because it now buys an answer " +
      "instead of an activity." },
    steps: [
      { k: "Step 1", v: "Run it on a live engagement and compare with what your team found by hand." },
      { k: "Step 2", v: "Fold it into your standard discovery deliverable." },
      { k: "Step 3", v: "Put your brand on it, or embed it. See the two models at the end." },
    ],
    cta: { btn: "Talk to us", txt: "Volume, regional and embedded terms are commercial. Please ask." },
  },

  // ------------------------------------------------------------------------------- VENDORS
  {
    id: "vendors", group: "partners", nav: "Cybersecurity vendors",
    eyebrow: "Partner", h2: "For cybersecurity vendors",
    scr: {
      s: "You have a product that solves a real problem, and a demonstration that shows it working.",
      c: "Your demonstration proves the product works in general. It does not prove this customer has the problem today, so the evaluation collapses into a comparison of features against a competitor.",
      a: "Show the prospect what is open on their own perimeter before you show them your product. Then run it again after deployment and show, in money, what your product closed.",
    },
    cols: [
      { h: "1. In your own sales team", li: [
        "Every account manager carries an exposure picture specific to that customer.",
        "It opens doors at companies that have never heard of you, with no access required.",
        "The money document turns a technical exposure into a budget line.",
      ] },
      { h: "2. Inside your product", li: [
        "External exposure becomes a feature of your platform, delivered over our programming interface.",
        "Your interface, your brand, no second product for the customer to evaluate.",
        "It adds an outside-in view to a product that mostly looks inward, which is a genuine gap in most security stacks.",
      ] },
      { h: "3. Alongside your product", li: [
        "Run it before and after deployment. The difference is your case study.",
        "It gives renewals a number rather than a feeling.",
        "You can also resell licences next to your own products.",
      ] },
    ],
    win: { h: "The claim, stated plainly", p:
      "Nobody argues with their own attack surface. It is the shortest route from a demonstration " +
      "to a budget." },
    steps: [
      { k: "Evaluate", v: "Run it against three of your own open opportunities." },
      { k: "Decide", v: "Sales tool, resale line, or a feature of your platform." },
      { k: "Integrate", v: "Findings arrive in your product through the programming interface." },
    ],
    cta: { btn: "Talk to us", txt: "Embedded and licence terms depend on volume and depth of integration. Please ask." },
  },

  // ---------------------------------------------------------------------------- CONSULTING
  {
    id: "consulting", group: "partners", nav: "Consulting firms",
    eyebrow: "Partner", h2: "For consulting firms",
    scr: {
      s: "You sell judgement and independence. Clients pay for the advice and the name on the cover.",
      c: "Fact-finding consumes most of the engagement and is the part clients least want to pay for. You bill juniors to gather facts and partners to interpret them, and only the second is valued.",
      a: "Compress fact-finding from weeks to days, put your own brand on the output, and sell the interpretation.",
    },
    cols: [
      { h: "1. What you can sell", li: [
        "A paid first engagement, delivered in days, that opens the larger one.",
        "An independent second opinion on a security programme already under way.",
        "Licences for the client to keep using it, on which you earn.",
      ] },
      { h: "2. What you leave behind", li: [
        "Findings for the security director.",
        "Risk in money for the finance director.",
        "Threat actors for the board, and compliance for the audit committee.",
      ] },
      { h: "3. Why it is safe to sign", li: [
        "Where a source could not be reached, findings say \"unknown\" instead of inventing a weakness.",
        "Every finding carries the evidence it rests on, and the date it was seen.",
        "It is repeatable, so the follow-on engagement has a measured starting point.",
      ] },
    ],
    win: { h: "The claim, stated plainly", p:
      "Your name goes on the document. That is exactly why a method that refuses to guess is worth " +
      "more to you than one that always produces a number." },
    steps: [
      { k: "Pilot", v: "One client, one run, your own analysis on top." },
      { k: "Package", v: "A named offering with a fixed scope and a fixed price." },
      { k: "Brand", v: "Your identity on the platform and every document." },
    ],
    cta: { btn: "Talk to us", txt: "White-label, licence and volume terms on request." },
  },

  // --------------------------------------------------------------------------------- TELCO
  {
    id: "telco", group: "partners", nav: "Telecoms operators",
    eyebrow: "Partner", h2: "For telecoms operators",
    scr: {
      s: "You sell connectivity to thousands of business customers and you want to attach security before connectivity becomes a pure commodity.",
      c: "A managed security practice needs analysts you cannot recruit, at a margin the market will not pay, for a customer base far too large to serve one at a time.",
      a: "Sell a security service whose cost does not rise with the number of customers, delivered by the account managers you already employ.",
    },
    cols: [
      { h: "1. What you sell", li: [
        "A branded assessment service: your portal, your invoice, your price.",
        "Licences as a recurring line, in packs or on an unlimited basis.",
        "A recurring review that makes the connectivity contract harder to switch than price alone.",
      ] },
      { h: "2. How it reaches the base", li: [
        "Attach it at the point of sale, while the connectivity order is being signed.",
        "No new sales motion: your existing account managers are the channel.",
        "It reaches the long tail of small customers you can never serve with people.",
      ] },
      { h: "3. Where it runs", li: [
        "In your own environment, or in a national cloud where regulation requires it.",
        "In the country your regulator names, including the licensing server.",
        "In the languages your market actually reads.",
      ] },
    ],
    win: { h: "The claim, stated plainly", p:
      "This is the rare security offer a customer base your size can actually consume, because " +
      "nothing about it needs one analyst per customer." },
    steps: [
      { k: "Prove", v: "Run it across a sample of your own base." },
      { k: "Brand", v: "Style the platform and every document as yours." },
      { k: "Attach", v: "Put it on the connectivity order form." },
    ],
    cta: { btn: "Talk to us", txt: "White-label, embedded, licence and volume terms on request." },
  },

  // ----------------------------------------------------------------------------------- SME
  {
    id: "sme", group: "buyers", nav: "Small and mid-sized companies",
    eyebrow: "Buyer", h2: "For small and mid-sized companies",
    note:
      "A small or mid-sized company here means a business of roughly ten to two hundred and fifty " +
      "employees, where one person looks after information technology alongside another job. This " +
      "page is written for that company itself: the owner, the managing director, or that one person.",
    scr: {
      s: "You are told your company needs to take cyber security seriously, and you agree.",
      c: "The advice is to buy a penetration test, a consultant and a set of policies. All three cost more than the risk anyone has quantified for you, and none of them answers the only question you actually have.",
      a: "Find out what a stranger can see of your company from the outside, this week, without installing anything or letting anyone into your network.",
    },
    cols: [
      { h: "1. What you receive", li: [
        "Everything of yours that faces the internet, including the things nobody remembered.",
        "What it would cost you if it went wrong, in money, with the method shown.",
        "Which laws apply to you and by when, in plain language.",
      ] },
      { h: "2. Why it fits a company your size", li: [
        "Nothing to install. No software, no access, nobody visiting your office.",
        "You give a company name. That is the whole of the setup.",
        "Run it again whenever something changes, instead of once a year when you can afford it.",
      ] },
      { h: "3. What you can do with it", li: [
        "Forward it to a customer who is auditing you, as it is.",
        "Give it to your bank or your insurer without translation.",
        "Hand it to your information technology supplier as a list of work.",
      ] },
    ],
    channel: {
      b: "How you buy it.",
      t: "Through a partner, not from us directly. Either choose one of our certified partners in " +
         "your region, or introduce us to the information technology company you already trust and " +
         "we will bring them on board. You keep the relationship you have. They gain the " +
         "capability. The choice is yours.",
    },
    win: { h: "The claim, stated plainly", p:
      "Most companies your size find at least one thing they did not know was visible from the " +
      "internet. Finding it costs you an afternoon instead of a project." },
    steps: [
      { k: "Now", v: "Look at the public demonstration. Real documents, invented company." },
      { k: "Then", v: "Ask us, or your own supplier, for a run on your own name." },
      { k: "After", v: "Fix what matters, then run it again to prove it is closed." },
    ],
    cta: { btn: "Find a partner", txt: "Prices and terms come from your partner. Tell us your region and we will introduce you, or bring your own." },
  },

  // ---------------------------------------------------------------------------- ENTERPRISE
  {
    id: "enterprise", group: "buyers", nav: "Large enterprises",
    eyebrow: "Buyer", h2: "For large enterprises",
    scr: {
      s: "You have security teams, mature tooling and a real budget. Every one of those teams owns part of the picture.",
      c: "Nobody can state what the whole group looks like from the outside and prove it. Subsidiaries and acquisitions leave assets no team claims. Supplier risk is assessed with a form the supplier fills in about itself.",
      a: "One external view of the entire group, priced in money, repeated on a schedule, with a report of exactly what changed since the last run.",
    },
    cols: [
      { h: "1. Coverage your tools do not have", li: [
        "The whole group, including subsidiaries and brands that do not carry the parent name.",
        "Suppliers assessed the same way, with no access and no questionnaire.",
        "Newly acquired businesses, before their network is joined to yours.",
      ] },
      { h: "2. Output shaped like your organisation", li: [
        "Findings for network security. Risk in money for the finance director and the risk committee.",
        "Threat actors for the board. Compliance for internal audit.",
        "No team has to agree with another team before it can use its own document.",
      ] },
      { h: "3. Built to survive challenge", li: [
        "Every finding carries the address, the port, the evidence and the date.",
        "Scoping is deliberately conservative: another company's server on shared infrastructure is never reported as yours.",
        "Where a source could not be reached it reports \"unknown\" rather than inferring a weakness.",
      ] },
    ],
    change: {
      h: "The change report, which is the part that matters",
      lead:
        "A single assessment tells you where you stand. It cannot tell you whether anything is " +
        "getting better. Run it again and the platform compares the two runs and reports only what moved.",
      cells: [
        { k: "new", t: "New", b: "did not exist last time",
          before: "Exposures that ", after: ": a service somebody published, a certificate that expired, a server an acquisition brought with it." },
        { k: "closed", t: "Closed", b: "gone",
          before: "Findings that are ", after: ". This is the evidence that a remediation budget produced a result, which is the hardest thing in security to demonstrate." },
        { k: "open", t: "Still open", b: "have not moved",
          before: "Findings raised previously that ", after: ", with how long they have been open. This is the escalation list, and it writes itself." },
      ],
      tailBefore: "Your compliance process does not want a report. It wants a dated, evidenced answer to one question: ",
      tailBold: "what changed, and did anyone fix what we raised?",
      tailAfter: " That is what turns this from a project into a control, and it is the reason to run it on a schedule rather than once.",
    },
    channel: {
      b: "How you buy it.",
      t: "Through the channel. Either choose one of our certified partners, or nominate the systems " +
         "integrator you already work with and we will bring them on board. Your procurement " +
         "process, your contracts and your existing supplier relationships stay as they are.",
    },
    win: { h: "The claim, stated plainly", p:
      "Your teams keep every tool they have. This answers the one question none of those tools is " +
      "pointed at: what the outside world can see across everything you own. It then proves, month " +
      "after month, whether that is shrinking." },
    steps: [
      { k: "Prove", v: "One business unit. Compare it with what you believed you had." },
      { k: "Extend", v: "Add subsidiaries and your most critical suppliers." },
      { k: "Operate", v: "Put it on a schedule and manage the change report." },
    ],
    cta: { btn: "Talk to us", txt: "Enterprise agreements, programming interface access and security documentation come through your partner or ours." },
  },

  // ----------------------------------------------------------------------------------- LAW
  {
    id: "law", group: "buyers", nav: "Law firms",
    eyebrow: "Buyer", h2: "For law firms",
    scr: {
      s: "You advise on data protection, cyber incidents, mergers and acquisitions, and regulatory exposure.",
      c: "You routinely need technical facts about a company you have no authority to touch. Testing another party's systems without authorisation creates exactly the liability you exist to prevent.",
      a: "Technical evidence obtained without doing anything to anybody, which is precisely what makes it usable in your work.",
    },
    cols: [
      { h: "1. Where it applies", li: [
        "**Due diligence in a transaction:** the target's real external estate, and its priced risk, before the purchase agreement is signed.",
        "**After an incident:** an independent, dated picture of what was publicly visible.",
        "**Disputes:** a technical exhibit that another expert can reproduce.",
      ] },
      { h: "2. Why it is lawful to use", li: [
        "Entirely passive. Not one packet reaches the company being assessed.",
        "Nothing is exploited and nothing is logged into.",
        "Built only from sources any researcher may lawfully consult, so no authorisation is required from anyone.",
      ] },
      { h: "3. What you can put in front of a client", li: [
        "Each finding with its evidence and the date it was retrieved.",
        "Which regulations apply, with obligations and deadlines quoted from the primary texts.",
        "The exposure converted into an amount your client's board understands.",
      ] },
    ],
    win: { h: "The claim, stated plainly", p:
      "It produces technical facts with the one property your work demands: they were obtained " +
      "without doing anything to anybody. That is what makes them usable." },
    steps: [
      { k: "Assess", v: "Run it on a matter you already advise on." },
      { k: "Verify", v: "Test the evidence trail against your own standard." },
      { k: "Adopt", v: "Make it a standard step in transaction due diligence and incident work." },
    ],
    cta: { btn: "Talk to us", txt: "Terms per matter or firm-wide, through the channel. The output is not legal advice and does not replace counsel." },
  },

  // ----------------------------------------------------------------------------- INSURANCE
  {
    id: "insurance", group: "buyers", nav: "Insurers",
    eyebrow: "Buyer", h2: "For insurers, agents and brokers",
    scr: {
      s: "You write cyber insurance, and you price it from what the applicant tells you about themselves.",
      c: "The proposal form is self-reported, optimistic and out of date the day it is signed. At renewal you cannot tell whether anything the insured promised to fix was fixed. After a loss you cannot show what was visible.",
      a: "Underwrite what is observable instead of what is declared, on every risk, at a cost that does not rise with the number of risks.",
    },
    cols: [
      { h: "1. What premium should this risk carry?", li: [
        "An expected loss and a worst case per year, produced by the recognised Factor Analysis of Information Risk method.",
        "The workings are shown, so it is a technical input to your rating decision and not a score from a black box.",
        "Available before the applicant has chosen you, because it needs no cooperation.",
      ] },
      { h: "2. What is actually on their estate?", li: [
        "Every exposure facing the internet, ranked, with the address and the port.",
        "Independent of the proposal form, so the two can be compared.",
        "Delivered in minutes, so it fits inside a quotation process.",
      ] },
      { h: "3. Are they compliant?", li: [
        "Their standing against the cyber laws that apply to them, with deadlines.",
        "Non-compliance is both a driver of loss and a question of coverage.",
        "European Union and Canadian regimes are live today.",
      ] },
    ],
    ladder: { h: "Across the life of the policy", items: [
      { b: "At quotation.", t: "Minutes, no cooperation needed." },
      { b: "At renewal.", t: "The change report shows remediation, or its absence. Price the difference." },
      { b: "Across the portfolio.", t: "Re-run the whole book when a new widely exploited vulnerability appears, and know your accumulated exposure the same day." },
      { b: "At claim.", t: "A dated record of what was externally visible." },
    ] },
    win: { h: "The claim, stated plainly", p:
      "You move from underwriting what the applicant says to underwriting what can be observed, " +
      "consistently, on every risk. That is an argument about loss ratio, not about technology." },
    steps: [
      { k: "Calibrate", v: "Run it against risks you have already written, including ones that produced losses." },
      { k: "Compare", v: "Set the results beside the proposal forms and look at the gaps." },
      { k: "Embed", v: "Into the quotation process, or your broker portal." },
    ],
    cta: { btn: "Talk to us", txt: "Portfolio, programming interface and embedded terms on request." },
  },

  // ----------------------------------------------------------------------------- REGULATOR
  {
    id: "regulator", group: "buyers", nav: "Regulators",
    eyebrow: "Buyer", h2: "For regulators and supervisory authorities",
    scr: {
      s: "You supervise a population of entities under a cyber security or operational resilience mandate.",
      c: "The law is written and the deadlines are real. Your technical capacity is not. In practice you inspect a handful of entities a year, chosen without a technical basis. You cannot know whether the ones you did not inspect are the ones that matter.",
      a: "Supervise the entire population from public evidence, without visiting anyone, and turn each breach into a prepared case file your officer reviews and signs.",
    },
    cols: [
      { h: "1. Coverage instead of sampling", li: [
        "Every supervised entity, assessed by the same method on the same day.",
        "Results are comparable across the sector, because nothing is measured differently.",
        "Repeatable on a schedule, so you can measure the sector's direction of travel.",
      ] },
      { h: "2. Evidence that survives challenge", li: [
        "Per entity: the address, the port, the evidence and the date it was observed.",
        "Mapped to the specific clause it engages.",
        "Where a source cannot be reached it reports \"unknown\" and asserts no breach.",
      ] },
      { h: "3. Lawful by construction", li: [
        "Entirely passive. No entity is touched, so no notice or authorisation arises.",
        "Reproducible, so it withstands review by the entity's own experts.",
        "Deployable inside your own or a national environment where the mandate requires it.",
      ] },
    ],
    ladder: { h: "The enforcement pipeline, run across the whole population", items: [
      { b: "Detect.", t: "A non-compliant condition on a supervised entity, with the address, the port and the date it was observed." },
      { b: "Map.", t: "The specific clause it engages, whether in European law or your own national instrument." },
      { b: "Corroborate.", t: "Four independent artificial intelligence models, from four different suppliers, review the case. Two build it and two try to break it. Fixed rules in code make the decision, not the models, and a case none of them can corroborate never leaves the queue." },
      { b: "Draft.", t: "The evidenced case file and the enforcement notice are prepared automatically." },
      { b: "Decide.", t: "Your officer reviews and signs. The machine builds the case and the authority issues it, which is what keeps every notice reviewable and open to appeal." },
    ] },
    win: { h: "The claim, stated plainly", p:
      "You stop choosing who to inspect by reputation. You start supervising the whole sector by " +
      "evidence, without sending an inspector to a single building, and without a single packet " +
      "reaching a supervised entity." },
    steps: [
      { k: "Pilot", v: "One sector, one group of entities. Rank them." },
      { k: "Compare", v: "Set the ranking against your own supervisory knowledge." },
      { k: "Scale", v: "The full population, on a schedule, with the enforcement queue." },
    ],
    cta: { btn: "Talk to us", txt: "Public sector procurement, hosting location and terms on request." },
  },

  // --------------------------------------------------------------------------- WHITE-LABEL
  {
    id: "whitelabel", group: "engage", nav: "White-label", accent: "purple",
    eyebrow: "How to engage, model 1 of 2", h2: "White-label",
    scr: {
      s: "You want a security service to sell under your own name.",
      c: "Building the engine takes years. Reselling somebody else's brand means the customer's relationship is with them and not with you.",
      a: "Your brand on the front, our engine underneath. Your customer, your contract, your price, and they never see us.",
    },
    cols: [
      { h: "What becomes yours", li: [
        "The brand on every screen and on all four documents.",
        "The customer relationship, the contract and the invoice.",
        "Your own pricing, set by you, for your market.",
        "Where it runs: your cloud, your region, or a national environment. The licensing server can sit in whichever country or region you require.",
      ] },
      { h: "What does not become yours", li: [
        "The source code, and ownership of the platform. You receive a licence to use it and present it, not to own it.",
        "The right to license the software itself onward to a third party.",
        "The engine's development and its correctness guarantees. Those stay with us, and they are what you are relying on.",
      ] },
    ],
    win: { h: "Choose this if", p:
      "You want a product to sell: something your customer logs into with your name on it. It is " +
      "the right model for managed service providers, telecoms operators, consulting firms and " +
      "resellers building a security practice." },
    steps: [
      { k: "Scope", v: "Brand, hosting region, languages, which modules." },
      { k: "Build", v: "We style and deploy it. You accept it against agreed criteria." },
      { k: "Sell", v: "Under your name, at your price." },
    ],
    cta: { btn: "Talk to us", txt: "Commitments, setup scope and pricing are commercial and confidential. Please ask." },
  },

  // ----------------------------------------------------------------------------------- OEM
  {
    id: "oem", group: "engage", nav: "Embedded (OEM)", accent: "purple",
    eyebrow: "How to engage, model 2 of 2", h2: "Embedded, also called OEM",
    scr: {
      s: "You already have a product your customers log into every day.",
      c: "Selling a separate product alongside it creates friction: another login, another contract, another thing to explain. It also dilutes the product you spent years building.",
      a: "Our engine inside your product, so your customer sees a new feature rather than a new product to evaluate.",
    },
    cols: [
      { h: "How it works", li: [
        "You call our programming interface. Findings, priced risk, threat actor context, compliance gradings and finished documents come back as data.",
        "You display them in your own interface, in your own structure.",
        "Critical findings are pushed to your platform or your security monitoring system as they occur, so there is nothing to poll.",
        "Deployable in your environment, in the region your architecture or your regulator requires.",
      ] },
      { h: "What it gives you", li: [
        "A new capability in an existing product, with no new item for the customer to approve.",
        "No second login, no second contract, no second support route.",
        "Full control of the experience, its place on your roadmap and how you price it.",
        "You can still resell licences as a separate line where an account calls for it.",
      ] },
    ],
    vs: {
      a: { h: "White-label is", bold: "product", before: "A ", after: " that looks like yours. Your customer logs into something carrying your brand. Best when you are building a service practice and need something to sell." },
      b: { h: "Embedded is", bold: "capability", before: "A ", after: " inside your product. Your customer sees a new feature, not a new product. Best when you already own the screen your customer looks at and do not want to add a second one." },
    },
    win: { h: "Choose this if", p:
      "You are a software or security vendor, an insurer with a portal, or a platform business. The " +
      "test is simple. If your customer already logs into something of yours, choose embedded. If " +
      "they do not, choose white-label." },
    steps: [
      { k: "Design", v: "Which calls, which data, where it appears." },
      { k: "Integrate", v: "Scoped keys, signed callbacks, a versioned specification." },
      { k: "Ship", v: "It becomes a feature of your platform." },
    ],
    cta: { btn: "Talk to us", txt: "Depth of integration, volume and terms are commercial. Please ask." },
  },

  // ------------------------------------------------------------------------------- CONTACT
  {
    id: "contact", group: "engage", nav: "Talk to us",
    eyebrow: "Next step", h2: "Talk to us",
    note:
      "Prices, tiers, licence models, commitments and contract terms are commercial and are agreed " +
      "directly. They are deliberately not published here.",
    cols: [
      { h: "What we can do this week", li: [
        "A live run on a company name you choose, so you judge the output rather than the pitch.",
        "A reference call with a partner already selling this in the German-speaking market.",
        "The legal pack: partner agreement, white-label and embedded supplement, non-disclosure agreement, service level agreement, terms of use, data processing agreement and a hosting factsheet.",
        "The security architecture documentation your security officer or procurement team will ask for.",
      ] },
      { h: "What we will ask you", li: [
        "Which of the audiences above you are. It changes the answer materially.",
        "Whether you want to resell it, brand it, or embed it in your own product.",
        "Whether you sell licences, services, or both.",
        "Where the data, and the licensing server, has to be located.",
      ] },
    ],
    cta: { btn: "Email us", ghost2: "See the public demonstration first", txt: "Cybergod LLC, part of the S4Biz Group" },
  },
];
