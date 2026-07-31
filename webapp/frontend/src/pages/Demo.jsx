import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import WhatsAppFab from "../components/WhatsAppFab.jsx";

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

const WHATSAPP     = "https://wa.me/351939994642";
const WHATSAPP_TEXT = "Hi — I sell cyber security and I would like access to cybergod.ai.";
const CONTACT      = "WhatsApp +351 939 994 642";

/* The hero: a short Cassandra film, not an illustration.
 *
 * It replaces a hand-drawn Trojan horse that never read as a horse at any size. A ten-second shot
 * of Cassandra on the walls of Troy carries the idea the page is actually about — a warning nobody
 * acted on — and does it without asking the viewer to decode a logo.
 *
 * Playback rules, all of them forced by how browsers and people actually behave:
 *  - MUTED is mandatory for autoplay. Every current browser blocks audible autoplay, and a hero
 *    that silently fails to start is worse than no hero. The film carries real audio, so there is
 *    an explicit sound toggle for anyone who wants it — chosen by the visitor, never sprung on them.
 *  - playsInline stops iOS hijacking the page into the native fullscreen player.
 *  - A POSTER covers the first paint, so a slow connection shows the opening frame instead of a
 *    black box; if the file fails outright the poster simply stays, and the page still reads.
 *  - prefers-reduced-motion is respected: those visitors get the still frame and no autoplay.
 *    Motion sensitivity is an accessibility requirement, not a preference to override.
 */
function CassandraFilm() {
  const reduced = typeof window !== "undefined" && window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches : false;
  const ref = useRef(null);
  const [muted, setMuted] = useState(true);
  const [failed, setFailed] = useState(false);

  function toggleSound() {
    const v = ref.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
    if (!v.muted && v.paused) v.play().catch(() => {});
  }

  if (failed) {
    return (
      <div className="cass-film">
        <img src="/media/cassandra-poster.jpg" alt="Cassandra on the walls of Troy" />
      </div>
    );
  }
  return (
    <div className="cass-film">
      <video
        ref={ref}
        src="/media/cassandra.mp4"
        poster="/media/cassandra-poster.jpg"
        autoPlay={!reduced}
        loop
        muted
        playsInline
        preload="metadata"
        controls={reduced}
        onError={() => setFailed(true)}
        aria-label="Cassandra on the walls of Troy"
      />
      {!reduced && (
        <button type="button" className="cass-sound" onClick={toggleSound}
                aria-label={muted ? "Turn sound on" : "Turn sound off"}>
          {muted ? "\u266A  Sound off" : "\u266A  Sound on"}
        </button>
      )}
    </div>
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
      <WhatsAppFab />
      {/* ---------- hero: the horse, then the creed ---------- */}
      <section className="demo-hero">
        <div className="wrap">
          <CassandraFilm />
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
              it would cost in euros, who would plausibly come for it, and which service closes
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
            The demonstration above is open to everyone. <b>Live assessments are available to approved
            partners only</b>, because each one consumes licensed scanning capacity
            and produces material about a real organisation.
          </p>
          <p>
            If you sell cyber security and would like access, get in touch:
          </p>
          <a className="demo-mail" href={`${WHATSAPP}?text=${encodeURIComponent(WHATSAPP_TEXT)}`}
             target="_blank" rel="noreferrer">
            {CONTACT}
          </a>
          <p className="demo-warn-sub">
            Please include your company and your role so access can be confirmed.
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
