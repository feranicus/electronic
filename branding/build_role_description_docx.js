/*
 * Build the Principal Director role description as a branded .docx.
 *
 * Palette is lifted from S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx
 * (slide1.xml / slide2.xml) and the HERKOS page :root block, so the document
 * matches both product surfaces.
 *
 *   cd /tmp/docxbuild && node build_role_description_docx.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertInchesToTwip, PageNumber, Footer, Header, TabStopType,
} = require("docx");

// ---------------------------------------------------------------- palette
const INK = "14161F";
const INK_DEEP = "08131A";
const INDIGO = "4F46E5";
const VIOLET = "8B5CF6";
const CYAN = "22D3EE";
const CYAN_DK = "0E7490";   // cyan is unreadable on white; darkened for text
const STEEL = "5C6880";
const MIST = "8E97A8";
const PAPER = "F4F5F9";
const WHITE = "FFFFFF";

const SANS = "Arial";
const DISPLAY = "Arial Black";
const MONO = "Consolas";

const NONE = { style: BorderStyle.NONE, size: 0, color: "auto" };
const NO_BORDERS = { top: NONE, bottom: NONE, left: NONE, right: NONE,
                     insideHorizontal: NONE, insideVertical: NONE };

// ---------------------------------------------------------------- helpers
const run = (text, o = {}) => new TextRun({
  text, font: o.font || SANS, size: o.size || 20,
  bold: !!o.bold, color: o.color || INK, allCaps: !!o.caps,
  characterSpacing: o.track || 0, italics: !!o.italic,
});

const p = (children, o = {}) => new Paragraph({
  children: Array.isArray(children) ? children : [children],
  spacing: { before: o.before ?? 0, after: o.after ?? 120, line: o.line ?? 276 },
  alignment: o.align, indent: o.indent, border: o.border, shading: o.shading,
  keepNext: !!o.keepNext, pageBreakBefore: !!o.pageBreakBefore,
});

const body = (text, o = {}) => p(run(text, { size: 20, color: "2B3042", ...o }),
  { after: 140, ...o });

/** Section heading: violet rule above, Arial Black caps. */
const h1 = (n, text) => p(
  [run(`${n}  `, { font: DISPLAY, size: 24, color: VIOLET }),
   run(text, { font: DISPLAY, size: 24, color: INK, caps: true, track: 8 })],
  { before: 420, after: 180, keepNext: true,
    border: { top: { style: BorderStyle.SINGLE, size: 12, color: VIOLET, space: 10 } } }
);

const h2 = (text) => p(
  run(text, { font: SANS, bold: true, size: 21, color: INDIGO }),
  { before: 260, after: 110, keepNext: true }
);

const h3 = (text) => p(
  run(text, { font: SANS, bold: true, size: 19, color: CYAN_DK, caps: true, track: 12 }),
  { before: 200, after: 90, keepNext: true }
);

const bullet = (children, level = 0) => new Paragraph({
  children: Array.isArray(children) ? children : [children],
  numbering: { reference: "s4b-bullets", level },
  spacing: { after: 90, line: 264 },
});

const numbered = (children) => new Paragraph({
  children: Array.isArray(children) ? children : [children],
  numbering: { reference: "s4b-numbers", level: 0 },
  spacing: { after: 110, line: 264 },
});

/** "**Lead.** rest" -> bold lead run + body run. */
const leadBullet = (lead, rest, level = 0) => bullet(
  [run(lead, { bold: true, color: INK, size: 20 }),
   run(rest, { size: 20, color: "2B3042" })], level);

/** Full-width shaded panel. */
const panel = (paras, fill) => new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  columnWidths: [9360],
  borders: NO_BORDERS,
  rows: [new TableRow({
    children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill, color: "auto" },
      margins: { top: 220, bottom: 220, left: 260, right: 260 },
      children: paras,
    })],
  })],
});

/** Two-column key/value strip used for the meta block. */
const metaRow = (k, v) => new TableRow({
  children: [
    new TableCell({
      width: { size: 2200, type: WidthType.DXA }, borders: NO_BORDERS,
      margins: { top: 40, bottom: 40, left: 0, right: 120 },
      children: [p(run(k, { font: MONO, size: 16, color: CYAN, caps: true, track: 10 }), { after: 0 })],
    }),
    new TableCell({
      width: { size: 7160, type: WidthType.DXA }, borders: NO_BORDERS,
      margins: { top: 40, bottom: 40, left: 0, right: 0 },
      children: [p(run(v, { size: 19, color: "E8EEF9" }), { after: 0 })],
    }),
  ],
});

// ---------------------------------------------------------------- title block
const titleBlock = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  columnWidths: [9360],
  borders: NO_BORDERS,
  rows: [new TableRow({
    children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: INK, color: "auto" },
      margins: { top: 400, bottom: 400, left: 340, right: 340 },
      children: [
        p([run("S4", { font: DISPLAY, size: 22, color: VIOLET }),
           run("BIZ", { font: DISPLAY, size: 22, color: WHITE }),
           run("   ·   ", { size: 20, color: STEEL }),
           run("CYBERGOD LLC", { font: MONO, size: 16, color: CYAN, track: 12 })],
          { after: 220 }),
        p([run("PRINCIPAL DIRECTOR", { font: DISPLAY, size: 40, color: WHITE, track: 4 })],
          { after: 60 }),
        p([run("AI  ·  CYBER SECURITY  ·  CLOUD  ·  DEVELOPMENT",
               { font: DISPLAY, size: 22, color: VIOLET, track: 20 })],
          { after: 260 }),
        p(run("Role description", { font: MONO, size: 17, color: MIST, caps: true, track: 14 }),
          { after: 0 }),
      ],
    })],
  })],
});

const metaBlock = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  columnWidths: [9360],
  borders: NO_BORDERS,
  rows: [new TableRow({
    children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: INK_DEEP, color: "auto" },
      margins: { top: 260, bottom: 280, left: 340, right: 340 },
      children: [new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        columnWidths: [2200, 7160], borders: NO_BORDERS,
        rows: [
          metaRow("Organisation", "S4Biz Group (Stars4Business OÜ) · Cybergod LLC"),
          metaRow("Reports to", "Group Board"),
          metaRow("Product lines", "cybergod.ai — AI cyber assessment & EU compliance platform"),
          metaRow("", "HERKOS — sovereign secure mobile platform: contact centre, mobile OS, secure communications, AI oversight"),
          metaRow("Location", "EU · remote-first, EU-resident infrastructure"),
        ],
      })],
    })],
  })],
});

// ---------------------------------------------------------------- content
const doc = new Document({
  creator: "S4Biz Group",
  title: "Principal Director — AI, Cyber Security, Cloud & Development",
  description: "Role description",
  styles: {
    default: { document: { run: { font: SANS, size: 20, color: INK } } },
  },
  numbering: {
    config: [
      {
        reference: "s4b-bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "▪", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: convertInchesToTwip(0.3), hanging: convertInchesToTwip(0.2) } },
                     run: { color: VIOLET, font: SANS } } },
          { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: convertInchesToTwip(0.62), hanging: convertInchesToTwip(0.2) } },
                     run: { color: CYAN_DK, font: SANS } } },
        ],
      },
      {
        reference: "s4b-numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: convertInchesToTwip(0.34), hanging: convertInchesToTwip(0.24) } },
                     run: { color: INDIGO, bold: true, font: SANS } } },
        ],
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        margin: { top: 1000, bottom: 1000, left: 1080, right: 1080 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
          border: { top: { style: BorderStyle.SINGLE, size: 6, color: "D8DBE6", space: 8 } },
          children: [
            run("S4Biz Group · Cybergod LLC · www.cybergod.ai", { font: MONO, size: 15, color: MIST }),
            new TextRun({ children: ["\t"] }),
            run("", { font: MONO, size: 15, color: MIST }),
            new TextRun({ children: [PageNumber.CURRENT], font: MONO, size: 15, color: STEEL }),
            run(" / ", { font: MONO, size: 15, color: MIST }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: MONO, size: 15, color: STEEL }),
          ],
        })],
      }),
    },
    children: [
      titleBlock,
      p(run(""), { after: 0 }),
      metaBlock,

      // ---------------------------------------------------------- 1
      h1("01", "Purpose of the role"),
      body("The Principal Director owns the technical and commercial arc of both product lines end to end: architecture, engineering, security assurance, cloud operations, AI model strategy, and the pre-sales motion that turns them into revenue. This is a build-and-sell role, not a supervisory one — the holder writes the architecture, ships the code, defends the design in front of a CISO, and is accountable when a customer-facing artefact is wrong."),
      body("Both products address the same market shift: European and Gulf organisations are increasingly required to prove where their data lives, who can read it, and what their externally observable attack surface actually is. The role exists to make those proofs producible by machine, repeatably, inside the customer's own jurisdiction."),

      // ---------------------------------------------------------- 2
      h1("02", "Scope of ownership"),

      h2("2.1  cybergod.ai — AI-driven attack-surface and compliance platform"),
      body("An assessment engine that takes a single input — a company name or domain — and returns a board-grade risk package without sending a single packet to the target."),
      leadBullet("Passive reconnaissance. ", "Shodan and Censys, Certificate Transparency, BGP/RPKI and RIR data, passive DNS, WHOIS/RDAP, KEV and EPSS enrichment. Autonomous systems, prefixes, brand domains and certificate identities are resolved by the engine, never hand-fed by the operator."),
      leadBullet("Attribution and scope control. ", "A layered ownership model: public-suffix-aware domain resolution, per-IP whois co-tenant separation, per-pivot and per-domain contribution budgets, and a record-level attribution gate for shared hosting — so a stranger's infrastructure can never appear in a customer's report."),
      leadBullet("Quantification. ", "FAIR-based loss modelling (threat- and loss-event frequency, probable maximum loss, annualised expected loss, return on security investment), MITRE ATT&CK mapping and kill-chain narrative."),
      leadBullet("Deliverables. ", "Four generated presentation decks plus an animated scrollytelling HTML report, produced in multiple document languages, with a post-delivery clarification loop that lets the operator correct scope and trigger a refined re-run."),
      leadBullet("Compliance module. ", "Graded assessment against NIS2, the Cyber Resilience Act and the EU AI Act, with a combined regime roadmap."),
      leadBullet("Delivery surfaces. ", "A FastAPI backend and React PWA cabinet plus Telegram bots behind a shared authentication gate with e-mailed one-time codes; six-language interface."),

      h2("2.2  HERKOS — sovereign secure mobile platform"),
      body("A secure communications estate delivered on open components and hosted on two independent sites inside the customer's own jurisdiction."),
      leadBullet("Mobile OS. ", "Ubuntu Touch 24.04 with the Lomiri shell and Halium hardware layer — read-only root, writable state confined to /userdata, fscrypt v2 data-at-rest encryption, a per-application AppArmor profile, and a private signed application catalogue. Everyday Android applications run isolated in a Waydroid LXC container on a LineageOS image with no Google services."),
      leadBullet("Secure communications. ", "Matrix/Synapse with end-to-end encryption and MLS for chat and files; Element Call on a LiveKit SFU for encrypted group voice and video; Delta Chat as a PGP-over-e-mail fallback that requires none of the platform's own infrastructure, with metadata minimised per RFC 9788."),
      leadBullet("Contact centre and telephony. ", "Asterisk with PSTN breakout and SIP endpoints, media relayed through an in-jurisdiction SFU, so interconnect-level interception yields ciphertext only."),
      leadBullet("DPI-resistant transport. ", "VLESS-Reality on port 443 as primary, AmneziaWG as fallback, wstunnel over WebSocket as third line, mutual TLS between services. Plain WireGuard and OpenVPN are excluded by policy because their signature is cut by deep packet inspection."),
      leadBullet("Identity and PKI. ", "Keycloak as identity provider, step-ca as internal certificate authority, SPIFFE for workload identity, FIDO2 hardware keys for human authentication, certificate lifetimes measured in hours."),
      leadBullet("Fleet and supply chain. ", "A self-built, GPG-signed system image on an owned OTA channel with phased rollout; an SBOM per build; signature verified in recovery before boot; Fleet and osquery for inventory and live query; Git with ansible-pull and commit-signature verification, so nothing is exposed inbound."),
      leadBullet("Detection and AI oversight. ", "Wazuh, Suricata and osquery feeding Loki and OpenSearch; a four-model inference chain on local vLLM in which two models author an incident analysis and two audit it independently, with only whitelisted containment actions executing automatically."),
      leadBullet("Standards posture. ", "NIST SP 800-207 zero trust, CISA Secure by Design, BSI TR-02102 and IT-Grundschutz, CSA CCM v4."),

      // ---------------------------------------------------------- 3
      h1("03", "Key responsibilities"),

      h3("Architecture and engineering"),
      bullet(run("Own the reference architecture for both platforms and the trade-offs inside them — protocol selection, isolation boundaries, failure domains, and what is deliberately not built.")),
      bullet(run("Write and maintain production code across engine, backend, frontend and infrastructure layers. This role is hands-on at the keyboard.")),
      bullet(run("Maintain a single-command delivery orchestrator: test, commit, push, deploy and verify in one invocation, with tagged known-good safe points and one-command rollback.")),
      bullet(run("Prove deployments by artefact rather than by liveness — comparing content hashes of the running engine inside each container against the repository before reporting success.")),

      h3("AI engineering and model governance"),
      bullet(run("Select, benchmark and chain inference models on measured evidence — contract validity, latency under the real production prompt, output depth, cost per assessment and per-vendor entitlement — never on marketing claims or synthetic probes.")),
      bullet(run("Maintain multi-vendor failover so that no single provider outage or quota ceiling can stop delivery, and enforce vendor separation between an authoring model and its auditor.")),
      bullet(run("Guard against fabricated identifiers: cross-check every CVE and named incident emitted by a model against the evidence actually collected, strip what cannot be verified, and surface the strip rather than silently rewriting prose.")),
      bullet(run("Keep a persistent cost ledger with per-user and per-assessment attribution, independent of log retention.")),

      h3("Cyber security practice and assurance"),
      bullet(run("Own the finding taxonomy, severity model and remediation templates, including detection of edge security appliances, exposed management planes, secrets managers, network storage and backup consoles, PBX exposure and non-production systems on the perimeter.")),
      bullet(run("Run and defend the zero-false-positive doctrine: every scope-widening mechanism must produce independent evidence of ownership, and every automatic filter must be bounded so that it can neither empty nor gut a report.")),
      bullet(run("Design guardrails that fail in the safe direction and record their own refusals, so a declined action is auditable rather than invisible, and can be overridden by an informed operator.")),
      bullet(run("Present findings and quantified risk to CISO and board audiences, and run the technical defence in competitive evaluations.")),

      h3("Cloud, infrastructure and sovereign hosting"),
      bullet(run("Own EU-resident hosting, container orchestration, reverse proxy and TLS automation, DNS, and the shared-tenancy isolation that keeps unrelated stacks on one host from interfering with each other.")),
      bullet(run("Operate a staging twin matched to production in size, image and region, and gate every production release behind a deploy-and-reboot rehearsal on that twin.")),
      bullet(run("Own observability end to end — structured event emission, log shipping, dashboards and alerting — including monitoring placed outside the failure domain it watches.")),
      bullet(run("Own configuration integrity for shared infrastructure: generated rather than hand-edited configuration, write-time validation against the running version and environment, and a runtime watchdog.")),

      h3("Software engineering and delivery"),
      bullet(run("Maintain the automated gates that block a release: static undefined-name analysis, execution-path tests, artefact-rendering tests, internationalisation coverage and key-leak audits, API contract analysis, brand and privacy-copy gates, and a scope-regression suite that replays real historical failures.")),
      bullet(run("Own internationalisation across interface and generated documents, including the distinction between interface language and document language, and the capability list that advertises which is which.")),
      bullet(run("Own the behaviour of delivered web surfaces on mobile, including installable PWA behaviour and offline-safe caching that never caches owner-scoped data.")),

      h3("Commercial and pre-sales"),
      bullet(run("Own solution design, scoping, effort estimation, commercial modelling and support-tier definition for both product lines.")),
      bullet(run("Run pre-sales engagements directly with enterprise and public-sector buyers, and produce the technical content — capability briefs, assessment reports, reference architectures — that carries them.")),
      bullet(run("Manage partner and reseller enablement, including vendor-neutral remediation guidance so partners can deliver on their own security stack.")),

      h3("Governance, compliance and data protection"),
      bullet(run("Own the GDPR position of both platforms: lawful basis, Article 13 notice, processor and transfer disclosures, telemetry data minimisation, retention claims that match enforced retention, and accountability logging.")),
      bullet(run("Own the EU regulatory content of the compliance product — NIS2, CRA, EU AI Act — and keep it current against primary legal texts and national transposition.")),
      bullet(run("Maintain access control and per-user usage quotas as committed, reviewable configuration rather than out-of-band settings.")),

      // ---------------------------------------------------------- 4
      h1("04", "Engineering doctrine the role is accountable for"),
      body("These are the standing principles of the practice. The Principal Director sets them, applies them, and is judged on whether the codebase still obeys them."),
      numbered([run("Full automation. ", { bold: true }), run("Every operational task is a script or a pipeline that runs end to end. If a task is done twice, it becomes code.")]),
      numbered([run("One orchestrator, one command. ", { bold: true }), run("An operator is never asked to run two scripts. New capability is wired into the orchestrator in the same change.")]),
      numbered([run("The repository is the single source of truth. ", { bold: true }), run("Infrastructure is provisioned from it and never configured out of band; secrets never enter it.")]),
      numbered([run("The model assists, it does not decide side effects. ", { bold: true }), run("Inference writes prose and analysis. Deployment, patching, reboot and containment remain deterministic code paths with whitelisted actions.")]),
      numbered([run("Absence of evidence is never a finding. ", { bold: true }), run("A failed lookup is reported as unavailable, never graded as a customer weakness.")]),
      numbered([run("A widening mechanism must prove ownership. ", { bold: true }), run("A match is not evidence; corroboration is.")]),
      numbered([run("An audit is a signal, not an authority. ", { bold: true }), run("An automated reviewer may flag, and must never be able to empty the deliverable.")]),
      numbered([run("Verify the artefact, not the intention. ", { bold: true }), run("A green build, a 200 response or a passing unit test is not proof that the shipped thing is correct.")]),
      numbered([run("A check that cannot run is not a check. ", { bold: true }), run("Gates execute where their toolchain is correct by construction, and a silent skip is treated as a defect.")]),

      // ---------------------------------------------------------- 5
      h1("05", "Decision rights"),
      body("The role holds final technical authority over platform architecture and protocol selection; the inference model chain and its ordering; the finding taxonomy and severity model; release gating and rollback; hosting jurisdiction and topology; and the privacy and disclosure copy attached to both products. Commercial pricing, legal entity structure and hiring sit with the Board."),

      // ---------------------------------------------------------- 6
      h1("06", "Success measures"),
      leadBullet("Attribution accuracy — ", "proportion of delivered findings attributable to the customer's own estate; a false positive in a shipped report is treated as a severity-one class defect."),
      leadBullet("Delivery integrity — ", "releases verified by artefact hash; every production incident traced to a gate that was absent, skipped or unenforceable."),
      leadBullet("Assessment economics — ", "inference cost and wall-clock time per assessment, and enrichment depth coverage, tracked per model and per user."),
      leadBullet("Sovereignty assurance — ", "demonstrable data residency, key custody and exit path at customer acceptance."),
      leadBullet("Commercial — ", "qualified pipeline, evaluation-to-contract conversion, and partner-delivered engagements."),

      // ---------------------------------------------------------- 7
      h1("07", "Required experience and capability"),
      h3("Essential"),
      bullet(run("Senior hands-on engineering across at least three of: offensive and defensive security; applied AI and LLM systems; cloud and Linux infrastructure; telecommunications and real-time media; full-stack product development — with credible depth in the remainder.")),
      bullet(run("Demonstrated design and operation of production systems under an adversarial threat model, including state-grade network interference, supply-chain integrity and device seizure.")),
      bullet(run("Working command of Python, JavaScript/TypeScript, Linux systems engineering, containerisation, CI/CD and infrastructure automation.")),
      bullet(run("Practical knowledge of EU cyber and data regulation — NIS2, GDPR, CRA, EU AI Act — sufficient to write defensible customer-facing positions, not merely to cite them.")),
      bullet(run("Enterprise pre-sales credibility: able to hold a technical evaluation with a CISO and a commercial conversation with a CFO in the same meeting.")),
      bullet(run("Business-level English and German; Russian an operational advantage for the current customer base.")),
      h3("Desirable"),
      bullet(run("Prior carrier, managed-security-provider or defence-adjacent delivery experience.")),
      bullet(run("Experience with Matrix, SIP/Asterisk, WebRTC SFU media, or mobile OS integration and OTA distribution.")),
      bullet(run("Published security research, open-source maintenance, or standards participation.")),

      // ---------------------------------------------------------- 8
      h1("08", "Technical environment"),
      panel([
        p([run("AI / ML   ", { font: MONO, size: 16, color: CYAN, caps: true, track: 10 })], { after: 60 }),
        p(run("Multi-vendor hosted inference with automatic failover · local vLLM · strict-JSON contract enforcement · prompt engineering under token and deadline budgets · cost telemetry", { size: 19, color: "E8EEF9" }), { after: 200 }),
        p([run("Security   ", { font: MONO, size: 16, color: CYAN, caps: true, track: 10 })], { after: 60 }),
        p(run("Shodan · Censys · Certificate Transparency · BGP/RPKI · passive DNS · RDAP · KEV/EPSS · MITRE ATT&CK · FAIR · Wazuh · Suricata · osquery · OpenSearch", { size: 19, color: "E8EEF9" }), { after: 200 }),
        p([run("Platform   ", { font: MONO, size: 16, color: CYAN, caps: true, track: 10 })], { after: 60 }),
        p(run("Python · FastAPI · React · Vite · PWA · Node · Docker & Compose · Caddy · GitHub Actions · GHCR · Grafana · Loki · Promtail · SQLite · PostgreSQL HA", { size: 19, color: "E8EEF9" }), { after: 200 }),
        p([run("Mobile & comms   ", { font: MONO, size: 16, color: CYAN, caps: true, track: 10 })], { after: 60 }),
        p(run("Ubuntu Touch · Lomiri · Halium · AppArmor · fscrypt · Waydroid · LXC · Matrix/Synapse · Element Call · LiveKit · Asterisk · SIP · Delta Chat · VLESS-Reality · AmneziaWG · wstunnel", { size: 19, color: "E8EEF9" }), { after: 200 }),
        p([run("Identity   ", { font: MONO, size: 16, color: CYAN, caps: true, track: 10 })], { after: 60 }),
        p(run("Keycloak · step-ca · SPIFFE · FIDO2 · mutual TLS", { size: 19, color: "E8EEF9" }), { after: 0 }),
      ], INK),

      p([run("S4Biz Group  ·  Stars4Business OÜ  ·  Cybergod LLC  ·  www.cybergod.ai",
             { font: MONO, size: 15, color: MIST })],
        { before: 320, align: AlignmentType.CENTER, after: 0 }),
    ],
  }],
});

const out = process.argv[2] || "Principal_Director_Role_Description.docx";
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log("wrote", out, buf.length, "bytes");
});
