import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

/* Public DEMO — "Trojan Empire".
 *
 * Open to anyone. Shows the real deliverables produced by the real deck builders, from FABRICATED
 * data, so a prospect can judge the format without us scanning anything or spending credits.
 *
 * HONESTY IS THE DESIGN CONSTRAINT, not a footnote:
 *  - the fabricated notice is the FIRST thing under the hero, not buried at the bottom;
 *  - every host uses an RFC 5737 documentation range (192.0.2.x / 198.51.100.x / 203.0.113.x),
 *    reserved by the IETF so it can never route to a real machine;
 *  - the company does not exist, and no real organisation is named anywhere on the page.
 */

const CONTACT = "jevgenijs.vainsteins@colt.net";

/* The third avatar: a Trojan horse on wheels, drawn inline so it needs no asset pipeline,
 * scales cleanly on any display and matches the teal-on-near-black palette exactly. */
function TrojanHorse() {
  return (
    <svg className="th-avatar" viewBox="0 0 240 200" role="img"
         aria-label="A wooden Trojan horse on wheels">
      <defs>
        <linearGradient id="thWood" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1a6f68" /><stop offset="100%" stopColor="#0c3f3b" />
        </linearGradient>
        <linearGradient id="thGlow" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#00B2A9" stopOpacity=".55" />
          <stop offset="100%" stopColor="#00B2A9" stopOpacity="0" />
        </linearGradient>
      </defs>

      <ellipse cx="120" cy="186" rx="86" ry="9" fill="url(#thGlow)" />

      {/* body */}
      <path d="M62 96 q6-26 30-30 l44-4 q22-2 32 12 l14 20 q6 9 2 18 l-6 14 q-4 9-14 9 H78
               q-12 0-16-10 l-6-16 q-3-9 6-13 Z" fill="url(#thWood)" stroke="#00B2A9" strokeWidth="2.5"/>
      {/* plank lines — it is a wooden horse, and the seams are the point */}
      <path d="M70 104 H188 M68 120 H192 M74 136 H186" stroke="#00B2A9" strokeWidth="1.1" opacity=".45"/>
      {/* neck + head */}
      <path d="M150 70 q16-16 30-10 q12 5 10 18 l-3 18 q-2 10-12 10 l-18 2"
            fill="url(#thWood)" stroke="#00B2A9" strokeWidth="2.5"/>
      <path d="M186 74 l10-16 l4 18 Z" fill="#00B2A9" opacity=".9"/>   {/* ear  */}
      <circle cx="178" cy="84" r="3.4" fill="#F7C844" />                {/* eye  */}
      {/* legs */}
      <path d="M84 152 v20 M112 152 v20 M148 152 v20 M176 152 v20"
            stroke="#0c3f3b" strokeWidth="9" strokeLinecap="round"/>
      <path d="M84 152 v20 M112 152 v20 M148 152 v20 M176 152 v20"
            stroke="#00B2A9" strokeWidth="2" strokeLinecap="round" opacity=".7"/>
      {/* WHEELS — the detail that makes it the Troy horse and not a statue */}
      {[[84, 176], [176, 176]].map(([cx, cy]) => (
        <g key={cx}>
          <circle cx={cx} cy={cy} r="17" fill="#0a1526" stroke="#00B2A9" strokeWidth="2.5"/>
          <circle cx={cx} cy={cy} r="4.5" fill="#00B2A9"/>
          <path d={`M${cx - 17} ${cy} H${cx + 17} M${cx} ${cy - 17} V${cy + 17}
                    M${cx - 12} ${cy - 12} L${cx + 12} ${cy + 12}
                    M${cx - 12} ${cy + 12} L${cx + 12} ${cy - 12}`}
                stroke="#00B2A9" strokeWidth="1.6" opacity=".75"/>
        </g>
      ))}
      {/* the hidden door — closed, hinged, and slightly ajar */}
      <rect x="104" y="112" width="30" height="30" rx="3" fill="#0a1526"
            stroke="#F7C844" strokeWidth="1.8" opacity=".95"/>
      <path d="M104 127 h30" stroke="#F7C844" strokeWidth="1" opacity=".6"/>
    </svg>
  );
}

export default function Demo() {
  const [meta, setMeta] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetch("/api/demo")
      .then((r) => r.json())
      .then(setMeta)
      .catch(() => setErr("The demo artifacts are being prepared. Please refresh in a moment."));
  }, []);

  const decks = (meta && meta.decks) || [];

  return (
    <div className="demo-page">
      {/* ---------- hero: the horse, then the creed ---------- */}
      <section className="demo-hero">
        <div className="wrap">
          <TrojanHorse />
          <div className="creed-kick">The name is not an accident</div>
          <blockquote className="creed-q">
            <span className="l1">Cassandra foretold the fall of Troy &mdash; and no one believed her.</span>
            <span className="l2">We predict the <b>critical cyber risks</b>, stop them
              <b> before they materialise</b>, and keep every <b>Trojan horse</b> out of your IT landscape.</span>
          </blockquote>
          <div className="creed-rule" aria-hidden="true"><i></i><span>&#9670;</span><i></i></div>
        </div>
      </section>

      {/* ---------- the honesty notice: first thing after the hero, impossible to miss ---------- */}
      <section className="wrap">
        <div className="demo-warn" role="note">
          <div className="demo-warn-h">THIS IS A DEMONSTRATION &mdash; EVERY RESULT IS FABRICATED</div>
          <p>
            <b>Trojan Empire is a fictional company.</b> Every host, certificate, CVE, threat actor and
            euro figure below is <b>invented</b> to show you the shape of the deliverable. Nothing was
            scanned. No real organisation is described. The IP addresses use IETF documentation ranges
            (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) that cannot route to a real machine.
          </p>
          <p className="demo-warn-sub">
            What is <i>not</i> fabricated is the machinery: these files come from the same engine and
            the same deck builders a paying engagement uses.
          </p>
        </div>
      </section>

      {/* ---------- what this is, in plain language ---------- */}
      <section className="wrap demo-sec">
        <h2>What this actually does</h2>
        <div className="demo-grid">
          <div className="demo-card">
            <div className="demo-num">1</div>
            <h3>You type one company name</h3>
            <p>
              That is the entire input. No IP ranges, no ASNs, no certificates to paste. The engine
              works out the rest &mdash; including the subsidiaries that trade under completely
              different names, which is where most of the real exposure hides.
            </p>
          </div>
          <div className="demo-card">
            <div className="demo-num">2</div>
            <h3>It finds what is already public</h3>
            <p>
              Entirely passive. It reads what internet-wide scanners, certificate transparency logs
              and public DNS already publish about the estate. No packet is ever sent to the target,
              so nothing needs permission and nothing sets off an alarm.
            </p>
          </div>
          <div className="demo-card">
            <div className="demo-num">3</div>
            <h3>It proves what belongs to whom</h3>
            <p>
              The hard part is not finding hosts &mdash; it is knowing which are <i>theirs</i>. Every
              asset is scored on independent evidence (published group structure, certificates,
              per-IP registry ownership) and the reasons are recorded, so a disputed host can be
              explained rather than argued about.
            </p>
          </div>
          <div className="demo-card">
            <div className="demo-num">4</div>
            <h3>It writes the boardroom papers</h3>
            <p>
              Four decks and an animated report, in English or Hoch&shy;deutsch: what is exposed, what
              it would cost in euros, who would plausibly come for it, and which Colt service closes
              each gap. Roughly three minutes, start to finish.
            </p>
          </div>
        </div>
      </section>

      {/* ---------- the artifacts ---------- */}
      <section className="wrap demo-sec">
        <h2>The deliverables &mdash; download them</h2>
        <p className="demo-lead">
          These are the real files, generated for the fictional Trojan Empire. Open them; this is
          exactly what lands in your inbox for a real target.
        </p>
        {err && <div className="demo-warn"><p>{err}</p></div>}
        {!meta && !err && <p className="demo-lead">Preparing the demonstration artifacts&hellip;</p>}
        <div className="demo-decks">
          {decks.map((d) => {
            const html = d.name.toLowerCase().endsWith(".html");
            const label =
              d.name.includes("Shodan") ? "Attack-surface findings"
              : d.name.includes("C-BIQ") ? "Business impact, priced in euros"
              : d.name.includes("GEOPOL_Animated") ? "Animated threat report"
              : d.name.includes("GEOPOL") ? "Who would target you, and why"
              : "Deliverable";
            return (
              <a key={d.name} className="demo-deck" href={d.url}
                 target={html ? "_blank" : undefined} rel="noreferrer"
                 download={html ? undefined : ""}>
                <span className="demo-deck-tag">{html ? "HTML" : "PPTX"}</span>
                <span className="demo-deck-name">{label}</span>
                <span className="demo-deck-file">{d.name}</span>
              </a>
            );
          })}
        </div>
      </section>

      {/* ---------- how it works, for the technical reader ---------- */}
      <section className="wrap demo-sec">
        <h2>How it works, technically</h2>
        <div className="demo-tech">
          <div><b>Attribution before analysis.</b> Ownership is graded on a 0&ndash;100 confidence
            score built from independent signals &mdash; the customer's own published group structure,
            certificate subject names, per-IP registry organisation, vendor-tenant labels, DNS the
            customer controls. Two weak signals that agree beat one strong signal that does not, and
            every score carries the rules that produced it.</div>
          <div><b>Co-tenant safety.</b> A shared netblock is not a customer. Where several companies
            share a provider range, per-IP registry ownership decides, so a neighbour's exposed
            management interface never appears in your report.</div>
          <div><b>The AI writes prose, never facts.</b> Severity, evidence and CVE identifiers come
            from the scan data only. The language model rewrites explanation and remediation, and a
            second model from a different vendor independently reviews the result. Any CVE the model
            cites that is not in the evidence is stripped before the deck is built.</div>
          <div><b>Deterministic rendering.</b> The decks are generated by code, not by a model, so the
            same input always produces the same document &mdash; and layout is machine-checked for
            overflow before anything ships.</div>
          <div><b>EU-resident.</b> Application, data and logs run in Frankfurt. Assessments are
            passive: no packet is sent to the target.</div>
        </div>
      </section>

      {/* ---------- access ---------- */}
      <section className="wrap demo-sec">
        <div className="demo-access">
          <h2>Running this against your own estate</h2>
          <p>
            The demonstration above is open to everyone. <b>Live assessments are available to Colt
            employees and Colt Partners only</b>, because each one consumes licensed scanning capacity
            and produces material about a real organisation.
          </p>
          <p>
            If you are a Colt Partner or a Colt employee and would like access, get in touch:
          </p>
          <a className="demo-mail" href={`mailto:${CONTACT}?subject=cybergod.ai%20access%20request`}>
            {CONTACT}
          </a>
          <p className="demo-warn-sub">
            Please include your company and your Colt relationship so access can be confirmed.
          </p>
          <div className="demo-actions">
            <Link className="btn ghost" to="/">Back to the main page</Link>
            <Link className="btn" to="/login">I already have access</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
