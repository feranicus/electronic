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

/* The third avatar: a flat 2D wooden Trojan horse on a wheeled cart.
 *
 * Drawn as SOLID SHAPES, not outlines: an earlier attempt traced a naturalistic horse with hand-
 * tuned beziers and produced a blob. Flat geometry (a barrel, a tapered neck slab, a rotated
 * capsule head, triangular ears, post legs, a plank cart) reads unmistakably at any size and suits
 * the subject — the thing in the story was a carpentered object, not an animal.
 *
 * DRAW ORDER IS LOAD-BEARING: the neck is painted BEFORE the body so the body's smooth back edge
 * cuts the join. Trying to hand-fit that corner left a sharp fin every time; letting the body
 * overlap it is exact by construction.
 *
 * Inline SVG, no asset pipeline, no gradients — it inherits the page palette and stays crisp on a
 * phone, a 5K display and a print stylesheet alike.
 */
function TrojanHorse() {
  const T = "#12726b";          // wood body
  const E = "#00B2A9";          // teal edge
  const D = "#0d564f";          // cart / shadowed wood
  const INK = "#0a1526";        // page background, used for the wheel voids
  const GOLD = "#F7C844";
  return (
    <svg className="th-avatar" viewBox="0 0 440 380" role="img"
         aria-label="A wooden Trojan horse standing on a wheeled cart">
      <g stroke={E} strokeWidth="3" strokeLinejoin="round">
        {/* tail */}
        <path d="M118 138 C84 146,54 182,50 226 C47 254,58 278,76 292
                 C74 268,72 240,78 214 C86 178,104 156,130 150 Z" fill="#0f6259"/>
        {/* legs — same tone as the barrel, or they sink into the cart and read as slats */}
        <g fill={T}>
          <rect x="112" y="188" width="31" height="80" rx="4"/>
          <rect x="153" y="188" width="31" height="80" rx="4"/>
          <rect x="231" y="188" width="31" height="80" rx="4"/>
          <rect x="271" y="188" width="31" height="80" rx="4"/>
        </g>
        {/* neck (before the body — see the note above) */}
        <path d="M240 182 L306 42 L330 96 L322 182 Z" fill={T}/>
        {/* barrel: withers higher than the croup, rounded rump, soft belly */}
        <path d="M92 180 C92 148,104 132,130 128
                 C170 138,214 140,252 130
                 C278 123,302 132,311 156
                 L313 196 C313 214,300 224,284 224
                 C230 230,170 230,118 224 C100 222,92 212,92 196 Z" fill={T}/>
        {/* ears */}
        <path d="M304 40 L296 4 L322 30 Z" fill={T}/>
        <path d="M326 28 L342 2 L344 38 Z" fill={T}/>
        {/* head */}
        <g transform="rotate(20 352 80)">
          <rect x="306" y="55" width="92" height="50" rx="21" fill={T}/>
        </g>
      </g>

      {/* mane, as strokes rather than a slab — a slab turns the neck into a plank */}
      <g stroke="#0b4a45" strokeWidth="7" strokeLinecap="round" opacity=".8">
        <path d="M272 120 l20 7"/><path d="M285 95 l20 7"/><path d="M297 70 l20 7"/>
      </g>
      {/* plank seams: it is a wooden horse and the carpentry is the whole point */}
      <g stroke={E} strokeWidth="1.7" opacity=".32" fill="none">
        <path d="M104 158 H300"/><path d="M96 186 H306"/>
      </g>

      {/* the cart */}
      <g stroke={E} strokeWidth="3" strokeLinejoin="round">
        <rect x="90" y="266" width="230" height="21" rx="4" fill={D}/>
        <rect x="106" y="287" width="18" height="12" fill={D}/>
        <rect x="288" y="287" width="18" height="12" fill={D}/>
        <circle cx="148" cy="315" r="33" fill={INK}/>
        <circle cx="266" cy="315" r="33" fill={INK}/>
      </g>
      <g stroke={E} strokeWidth="2" opacity=".85">
        <path d="M115 315h66M148 282v66M125 292l46 46M125 338l46-46"/>
        <path d="M233 315h66M266 282v66M243 292l46 46M243 338l46-46"/>
      </g>
      <circle cx="148" cy="315" r="7" fill={E}/><circle cx="266" cy="315" r="7" fill={E}/>

      {/* eye, nostril, mouth */}
      <circle cx="352" cy="76" r="5" fill={GOLD}/>
      <circle cx="392" cy="108" r="3.4" fill={INK} opacity=".8"/>
      <path d="M378 122 l16 6" stroke={INK} strokeWidth="2.6" opacity=".5" fill="none"/>

      {/* the hidden door — the reason anyone remembers the horse */}
      <rect x="150" y="152" width="54" height="54" rx="4" fill={INK} stroke={GOLD} strokeWidth="3"/>
      <path d="M150 179 h54" stroke={GOLD} strokeWidth="1.8" opacity=".6"/>
      <circle cx="195" cy="179" r="2.8" fill={GOLD}/>
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
