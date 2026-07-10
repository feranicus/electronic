import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

export default function Landing() {
  const rootRef = useRef(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const cleanups = [];
    const raf = [];
    const timers = [];

    const hd = root.querySelector("#hd");
    const onScroll = () => hd && hd.classList.toggle("s", window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    cleanups.push(() => window.removeEventListener("scroll", onScroll));

    const io = new IntersectionObserver(
      (es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }),
      { threshold: 0.1 }
    );
    root.querySelectorAll(".reveal").forEach((el) => io.observe(el));
    cleanups.push(() => io.disconnect());

    const cv = root.querySelector("#dust");
    if (cv) {
      const ctx = cv.getContext("2d");
      let W, H, ps = [];
      const sz = () => { W = cv.width = cv.parentElement.offsetWidth; H = cv.height = cv.parentElement.offsetHeight; };
      sz();
      window.addEventListener("resize", sz);
      cleanups.push(() => window.removeEventListener("resize", sz));
      const sp = () => ({ x: Math.random() * W, y: Math.random() * H, r: Math.random() * 2.2 + 0.4,
        vx: Math.random() * 0.3 - 0.15, vy: -Math.random() * 0.4 - 0.05, a: Math.random() * 0.5 + 0.1,
        c: Math.random() > 0.7 ? "247,200,68" : "0,178,169" });
      for (let i = 0; i < 90; i++) ps.push(sp());
      let alive = true;
      const dr = () => {
        if (!alive) return;
        ctx.clearRect(0, 0, W, H);
        ps.forEach((p) => {
          p.x += p.vx; p.y += p.vy; p.a -= 0.0014;
          if (p.a <= 0 || p.y < -10) { Object.assign(p, sp()); p.y = H + 5; }
          ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7);
          ctx.fillStyle = "rgba(" + p.c + "," + p.a + ")"; ctx.fill();
        });
        raf.push(requestAnimationFrame(dr));
      };
      dr();
      cleanups.push(() => { alive = false; });
    }

    const CONV = [
      { s: "me", t: "/auth jevgenijs.vainsteins@colt.net ********", cmd: "/auth" },
      { s: "them", typ: 900, t: "Code emailed. Reply /verify <code> (valid 10 min)." },
      { s: "me", t: "/verify 483920", cmd: "/verify" },
      { s: "them", typ: 700, t: "Verified. You're in." },
      { s: "me", t: "/assess Volkswagen AG", cmd: "/assess" },
      { s: "them", typ: 1000, t: "Assessing Volkswagen AG ..." },
      { s: "them", typ: 1600, t: "[auto] 9 ASNs / 41 domains / internal-CA VW-CA-PROC-09 / sweeping Shodan..." },
      { s: "file", fn: "VW_Shodan_Findings.pptx", fs: "2 CRIT / 4 HIGH / evidence + Colt fixes", typ: 900 },
      { s: "file", fn: "VW_C-BIQ.pptx", fs: "portfolio ALE EUR 11M-29M" },
      { s: "file", fn: "VW_GEOPOL.pptx", fs: "APT41/Winnti +4 adversaries" },
      { s: "file", fn: "VW_DELTAS.pptx", fs: "value Colt buys back" },
      { s: "them", typ: 600, t: "Done in 2m 10s. 4 decks ready." },
    ];
    const tb = root.querySelector("#tgbody");
    const esc = (x) => (x || "").replace(/</g, "&lt;");
    let demoAlive = true;
    function tgRun() {
      if (!demoAlive || !tb) return;
      tb.innerHTML = ""; let d = 500;
      CONV.forEach((m) => {
        if (m.typ) {
          timers.push(setTimeout(() => {
            if (!demoAlive) return;
            const t = document.createElement("div");
            t.className = "typing"; t.dataset.typing = "1";
            t.innerHTML = "<i></i><i></i><i></i>";
            tb.appendChild(t); tb.scrollTop = tb.scrollHeight;
          }, d));
          d += m.typ;
        }
        timers.push(setTimeout(() => {
          if (!demoAlive) return;
          const tp = tb.querySelector('[data-typing="1"]'); if (tp) tp.remove();
          const b = document.createElement("div");
          if (m.s === "file") {
            b.className = "msg file";
            b.innerHTML = '<div class="doc">PPTX</div><div><div class="fn">' + m.fn + '</div><div class="fs">' + m.fs + "</div></div>";
          } else {
            b.className = "msg " + m.s;
            let txt = esc(m.t);
            if (m.cmd) txt = txt.replace(esc(m.cmd), '<span class="cmd">' + esc(m.cmd) + "</span>");
            b.innerHTML = txt;
          }
          tb.appendChild(b); tb.scrollTop = tb.scrollHeight;
        }, d));
        d += 800;
      });
      timers.push(setTimeout(tgRun, d + 3200));
    }
    if (tb) {
      const demoIo = new IntersectionObserver((e, o) => {
        if (e[0].isIntersecting) { tgRun(); o.disconnect(); }
      }, { threshold: 0.35 });
      demoIo.observe(tb);
      cleanups.push(() => demoIo.disconnect());
    }
    cleanups.push(() => { demoAlive = false; });

    const C = { green: "#10B981", teal: "#00B2A9", gold: "#F7C844", purple: "#8b6cff", cyan: "#38e1ff" };
    const NODES = [
      { id: "you", x: 150, y: 210, ico: "phone", t: "SALES", s: "Telegram / one name", c: C.green, n: "1", dd: "d1" },
      { id: "bot", x: 450, y: 130, ico: "shield", t: "colttechbot", s: "the assessor", c: C.teal, n: "1", dd: "d1", big: true },
      { id: "cass", x: 450, y: 300, ico: "compass", t: "cassandra", s: "AE assistant", c: C.teal, n: "1", dd: "d1" },
      { id: "auth", x: 450, y: 470, ico: "lock", t: "ZERO-TRUST", s: "email+pw+code", c: C.purple, n: "2", dd: "d2" },
      { id: "eng", x: 740, y: 300, ico: "gear", t: "ENGINE", s: "recon > decks", c: C.teal, n: "3", dd: "d3", big: true },
      { id: "gmail", x: 740, y: 110, ico: "mail", t: "GMAIL API", s: "2FA code / HTTPS", c: C.gold, n: "2", dd: "d2" },
      { id: "foot", x: 1050, y: 120, ico: "globe", t: "FOOTPRINT", s: "bgpview/RIPE/crt.sh", c: C.gold, n: "3", dd: "d3" },
      { id: "shodan", x: 1050, y: 280, ico: "scope", t: "SHODAN", s: "paid / 30+ filters", c: C.gold, n: "4", dd: "d4" },
      { id: "deep", x: 1050, y: 440, ico: "bot", t: "DEEPSEEK", s: "DO serverless AI", c: C.gold, n: "5", dd: "d5" },
      { id: "spaces", x: 740, y: 520, ico: "disk", t: "SPACES", s: "backups", c: C.gold, n: "7", dd: "d7" },
      { id: "graf", x: 1050, y: 590, ico: "chart", t: "GRAFANA", s: "godeyes.ai/observe", c: C.cyan, n: "6", dd: "d6" },
      { id: "gh", x: 150, y: 440, ico: "octo", t: "GITHUB CI/CD", s: "build/scan/ship", c: C.teal, n: "8", dd: "d8" },
      { id: "patch", x: 150, y: 600, ico: "patch", t: "PATCHWATCH", s: "self-patch /3d", c: C.purple, n: "7", dd: "d7" },
    ];
    const ICO = { phone: "📱", shield: "🛡️", compass: "🧭", lock: "🔐", gear: "⚙️", mail: "✉️", globe: "🌐", scope: "🔭", bot: "🤖", disk: "💾", chart: "📈", octo: "🐙", patch: "🩹" };
    const EDGES = [
      { a: "you", b: "bot", c: C.green }, { a: "you", b: "cass", c: C.green },
      { a: "bot", b: "auth", c: C.purple }, { a: "cass", b: "auth", c: C.purple }, { a: "auth", b: "gmail", c: C.gold, two: true },
      { a: "auth", b: "eng", c: C.teal }, { a: "eng", b: "foot", c: C.gold, two: true }, { a: "eng", b: "shodan", c: C.gold, two: true },
      { a: "eng", b: "deep", c: C.gold, two: true }, { a: "bot", b: "graf", c: C.cyan, bow: 90 }, { a: "eng", b: "graf", c: C.cyan },
      { a: "eng", b: "spaces", c: C.gold }, { a: "patch", b: "spaces", c: C.purple, bow: -60 }, { a: "patch", b: "eng", c: C.purple },
      { a: "gh", b: "eng", c: C.teal, bow: 60 },
    ];
    const NS = "http://www.w3.org/2000/svg";
    const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));
    const el = (t, a) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
    const pathD = (a, b, bow) => { const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - (bow || 0); return "M " + a.x + " " + a.y + " Q " + mx + " " + my + " " + b.x + " " + b.y; };
    const eg = root.querySelector("#edges"), ng = root.querySelector("#nodes");
    const E = [], Ngr = {};
    if (eg && ng) {
      EDGES.forEach((e, i) => {
        const a = byId[e.a], b = byId[e.b], d = pathD(a, b, e.bow);
        const p = el("path", { d, fill: "none", stroke: e.c, "stroke-width": 2, "stroke-opacity": 0.22, "stroke-dasharray": "2 9", "stroke-linecap": "round" });
        eg.appendChild(p);
        const dots = [];
        for (let k = 0; k < 3; k++) {
          const dot = el("circle", { r: 4.2, fill: e.c, filter: "url(#glow)" });
          const m = el("animateMotion", { dur: (3.4 + i * 0.11) + "s", repeatCount: "indefinite", begin: (-(k * 1.13)) + "s", path: d, calcMode: "linear" });
          if (e.two && k === 1) { m.setAttribute("keyPoints", "1;0"); m.setAttribute("keyTimes", "0;1"); }
          dot.appendChild(m); eg.appendChild(dot); dots.push(dot);
        }
        E.push({ path: p, dots, from: e.a, to: e.b });
      });
      NODES.forEach((n) => {
        const w = n.big ? 176 : 150, h = n.big ? 92 : 84, x = n.x - w / 2, y = n.y - h / 2;
        const g = el("g", { class: "node" });
        g.appendChild(el("rect", { x: x - 1, y: y - 1, width: w + 2, height: h + 2, rx: 18, fill: "none", stroke: n.c, "stroke-opacity": 0.5, "stroke-width": 1.5 }));
        g.appendChild(el("rect", { class: "box", x, y, width: w, height: h, rx: 17, fill: "#101f3b", stroke: n.c, "stroke-opacity": 0.4, "stroke-width": 1.2 }));
        const ic = el("text", { x: n.x, y: y + 34, "text-anchor": "middle", "font-size": n.big ? 32 : 26 }); ic.textContent = ICO[n.ico] || ""; g.appendChild(ic);
        const t = el("text", { x: n.x, y: y + (n.big ? 62 : 56), "text-anchor": "middle", "font-size": 13.5, "font-weight": 800, fill: "#eaf1fb" }); t.textContent = n.t; g.appendChild(t);
        const s = el("text", { x: n.x, y: y + (n.big ? 79 : 73), "text-anchor": "middle", "font-size": 10.5, fill: "#93a9ce" }); s.textContent = n.s; g.appendChild(s);
        const bx = x + 15; g.appendChild(el("circle", { cx: bx, cy: y, r: 13, fill: n.c, filter: "url(#glow)" }));
        const num = el("text", { x: bx, y: y + 5, "text-anchor": "middle", "font-size": 13, "font-weight": 900, fill: "#04211f" }); num.textContent = n.n; g.appendChild(num);
        g.addEventListener("click", () => flash(n.dd));
        g.addEventListener("mouseenter", () => { if (!touring) hl([n.id]); });
        g.addEventListener("mouseleave", () => { if (!touring) hl(null); });
        ng.appendChild(g); Ngr[n.id] = g;
      });
    }
    function hl(ids) {
      E.forEach((e) => {
        const on = !ids || ids.includes(e.from) || ids.includes(e.to);
        e.path.style.strokeOpacity = ids ? (on ? 0.7 : 0.05) : 0.22;
        e.dots.forEach((d) => (d.style.opacity = ids ? (on ? 1 : 0.08) : 1));
      });
      NODES.forEach((n) => { if (Ngr[n.id]) { Ngr[n.id].style.opacity = ids ? (ids.includes(n.id) ? 1 : 0.3) : 1; Ngr[n.id].style.transition = "opacity .3s"; } });
    }

    const STEPS = [
      { ids: ["you", "bot"], t: "1 - You text one company name to the bot - that's the whole input." },
      { ids: ["bot", "auth", "gmail"], t: "2 - Zero-trust: colt.net email + password + a one-time code emailed to you." },
      { ids: ["auth", "eng", "foot"], t: "3 - The engine auto-resolves the company's entire footprint. You type no IPs." },
      { ids: ["eng", "shodan"], t: "4 - It sweeps Shodan (paid) for every exposed door + the hidden internal-CA estate." },
      { ids: ["eng", "deep"], t: "5 - DeepSeek writes the prose; templates lock the numbers into 4 decks." },
      { ids: ["bot", "eng", "graf"], t: "6 - Every login, assessment and patch is logged live to Grafana." },
      { ids: ["patch", "spaces", "eng"], t: "7 - patchwatch backs up to Spaces, then patches the server itself every 3 days." },
      { ids: ["gh", "eng"], t: "8 - One command / git push builds, scans and ships it over a private Tailscale tunnel." },
    ];
    let touring = false, ti = 0, timer = null;
    const cap = root.querySelector("#cap"), tbtn = root.querySelector("#tour");
    function step() {
      const s = STEPS[ti]; hl(s.ids); if (cap) { cap.textContent = s.t; cap.classList.add("show"); }
      ti = (ti + 1) % STEPS.length; timer = setTimeout(step, 3000); timers.push(timer);
    }
    if (tbtn) {
      tbtn.onclick = () => {
        if (touring) {
          touring = false; clearTimeout(timer); hl(null);
          if (cap) cap.classList.remove("show"); tbtn.textContent = "▶ Guided tour"; tbtn.classList.remove("off");
        } else {
          touring = true; ti = 0; step(); tbtn.textContent = "⏸ Stop tour"; tbtn.classList.add("off");
          const map = root.querySelector("#map"); if (map) map.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      };
    }

    const DD = [
      { id: "d1", n: "1", ic: "📱", c: C.green, h: "Telegram + the two bots", plain: "You send one message - the prospect's name. Two bots live on the server 24/7: <b>colttechbot</b> does the assessment, <b>cassandra</b> is your research/outreach sidekick.", hood: ["<code>python-telegram-bot</code>, one per bot, in Docker", "colttechbot shells the deterministic engine per <code>/assess</code>", "cassandra: live OSINT (HTTP + headless-Chromium fallback) + DeepSeek"] },
      { id: "d2", n: "2", ic: "🔐", c: C.purple, h: "Zero-trust login (2FA)", plain: "To use a bot you need a real <b>@colt.net</b> email, the shared password, <b>and</b> a one-time code emailed to that inbox. Knowing the password isn't enough - you must own the mailbox.", hood: ["<code>colt_auth.py</code>: constant-time compare, lockout, 10-min codes", "OTP delivered via <b>Gmail API over HTTPS</b> (droplet blocks SMTP ports)", "Every attempt logged for the auth audit trail"] },
      { id: "d3", n: "3", ic: "🧩", c: C.teal, h: "The engine + auto-discovery", plain: "From just the name the engine finds the company's <b>networks, domains and certificates</b> - then hunts, scores and writes. You never hand it an IP.", hood: ["ASNs+prefixes: <code>bgpview.io</code> + RIPEstat", "Brand domains/subdomains: <code>crt.sh</code> CT logs", "cert-subject-O + favicon derived; internal-CA harvested live from the sweep", "<code>run_assessment.py</code> to <code>shodan_recon.autodiscover()</code>"] },
      { id: "d4", n: "4", ic: "🔭", c: C.gold, h: "Shodan - what's exposed", plain: "It queries Shodan (a search engine of internet-connected devices) for exposed remote-access, databases, VPNs, mail, industrial gear and known-vulnerable systems - and the killer pivot: the company's own private CA to reveal their whole hidden estate.", hood: ["30+ super-filters; edge-appliance mgmt = CRITICAL", "Paid facets: <code>has_vuln</code>, <code>vuln:CVE</code>, <code>tag:ics</code>, <code>ssl.jarm</code>", "CDN/honeypot false-positives dropped automatically"] },
      { id: "d5", n: "5", ic: "🤖", c: C.gold, h: "DeepSeek writes the decks", plain: "An AI writes the words; fixed templates guarantee the structure and the maths. You get board-ready slides, not a scan dump: <b>Findings / C-BIQ (EUR) / GEOPOL / DELTAS</b>.", hood: ["DeepSeek on DigitalOcean serverless inference (OpenAI-compatible)", "<code>pptxgenjs</code> templates lock layout; numbers stay deterministic", "EUR business impact, adversary attribution, value bought back"] },
      { id: "d6", n: "6", ic: "📈", c: C.cyan, h: "Always watching", plain: "Every login, assessment and patch prints a structured line that flows into <b>your existing Grafana</b> - no second monitoring stack.", hood: ["events.log to <code>promtail</code> to Loki to Grafana (<code>godeyes.ai/observe</code>)", "Per-bot activity, auth audit trail, patchwatch deep-dive dashboard", "Dashboards imported from the repo (<code>import-dashboards.yml</code>)"] },
      { id: "d7", n: "7", ic: "🩹", c: C.purple, h: "It patches itself", plain: "A server nobody patches gets hacked. Every 3 days it <b>backs itself up</b> to Spaces, upgrades the OS/Docker, and an AI writes a risk digest (flagging kernel holes like GhostLock). Reboots happen at 4am.", hood: ["<code>patchwatch/</code> systemd timer; backup-first (abort if backup fails)", "DO Spaces tarball + optional DO droplet snapshot", "DeepSeek digest to Telegram + Grafana"] },
      { id: "d8", n: "8", ic: "🚀", c: C.teal, h: "Shipping is one command", plain: "Change the code, run one thing, it's live - no clicking through consoles.", hood: ["<code>python ship.py</code>: repair to commit to push to rebuild to redeploy to verify", "GitHub Actions: build to Trivy scan to GHCR to deploy", "Reaches the firewalled droplet over a private <b>Tailscale</b> tunnel"] },
    ];
    const dw = root.querySelector("#ddwrap");
    if (dw) {
      DD.forEach((d) => {
        const s = document.createElement("div");
        s.className = "dd reveal"; s.id = d.id;
        s.innerHTML = '<div class="num" style="background:' + d.c + '">' + d.n + '</div><div><h3><span class="ic">' + d.ic + "</span>" + d.h + '</h3><p class="plain">' + d.plain + '</p><div class="flowstrip" style="--c:' + d.c + '"><i></i></div><div class="hood"><div class="h">Under the hood - for the engineer</div><ul>' + d.hood.map((x) => "<li>" + x + "</li>").join("") + "</ul></div></div>";
        dw.appendChild(s); io.observe(s);
      });
    }
    function flash(id) {
      const c = root.querySelector("#" + id); if (!c) return;
      c.scrollIntoView({ behavior: "smooth", block: "center" });
      c.classList.add("flash"); timers.push(setTimeout(() => c.classList.remove("flash"), 1400));
    }

    return () => {
      cleanups.forEach((fn) => fn());
      raf.forEach((id) => cancelAnimationFrame(id));
      timers.forEach((id) => clearTimeout(id));
    };
  }, []);

  return (
    <div ref={rootRef}>
      <header id="hd"><div className="wrap">
        <span className="brand"><span className="chev">❯</span> colt</span>
        <nav>
          <a href="#demo">See it live</a><a href="#map">The machine</a>
          <a href="#deep">Deep dive</a><a href="#secure">Security</a>
          <Link className="btn sm" to="/login">Open the app</Link>
        </nav>
      </div></header>

      <section className="hero">
        <canvas id="dust"></canvas>
        <div className="wrap">
          <div className="kick">Colt / S4Biz - cyber pre-sales automation</div>
          <h1>Type a company name.<br /><span className="g">Four boardroom decks.</span> Two minutes.</h1>
          <p className="sub">A robot that turns one word - a prospect's name - into a full external
            cyber-risk assessment, priced in euros. So 30+ sales people are ready for any meeting, hands-free.</p>
          <div className="cta-row">
            <Link className="btn" to="/login">Open the app / Log in</Link>
            <a className="btn ghost" href="#demo">Watch it work</a>
          </div>
        </div>
      </section>

      <section id="demo" className="lp"><div className="wrap reveal">
        <h2>See it <span className="g">live</span></h2>
        <p className="lede">This is the entire product - texting a bot. The chat below plays the real flow: log in, ask, get four decks.</p>
        <div className="demo">
          <div className="phone"><div className="notch"></div><div className="screen">
            <div className="tgh"><span className="bk">‹</span><div className="av">C</div>
              <div><div className="nm">colttechbot</div><div className="st">bot / online</div></div>
              <div className="dots">⋮</div></div>
            <div className="tgbody" id="tgbody"></div>
          </div></div>
          <div className="demoside">
            <h3>One input. Zero flags.</h3>
            <p>You never type an IP, a network or a certificate. The robot resolves the target's <b>entire</b> internet
              footprint itself, then hunts every exposure, prices it, and writes the decks.</p>
            <div className="chips">
              <span className="chip">zero-trust login</span><span className="chip">auto-discovery</span>
              <span className="chip">Shodan (paid)</span><span className="chip">DeepSeek prose</span>
              <span className="chip">4 decks</span>
            </div>
            <p style={{ marginTop: 14, color: "var(--gold)" }}>The chat loops - watch the four .pptx files land.</p>
            <Link className="btn gold" style={{ marginTop: 6 }} to="/login">Do this in the web app</Link>
          </div>
        </div>
      </div></section>

      <section id="map" className="lp"><div className="wrap reveal">
        <div className="maphead">
          <div><h2>The whole <span className="g">machine</span></h2>
            <p className="lede" style={{ margin: 0 }}>Hover a box to see its wires. Click it to jump to the details. Or hit play for a guided tour.</p></div>
          <button className="tour" id="tour">Guided tour</button>
        </div>
        <div className="legend" style={{ margin: "6px 0 12px" }}>
          <span><b style={{ background: "#10B981" }}></b>You and bots</span>
          <span><b style={{ background: "#00B2A9" }}></b>Brains</span>
          <span><b style={{ background: "#F7C844" }}></b>Outside services</span>
          <span><b style={{ background: "#8b6cff" }}></b>Safety nets</span>
          <span><b style={{ background: "#38e1ff" }}></b>Observability</span>
        </div>
        <div className="mapbox">
          <svg id="svg" viewBox="0 0 1200 700" xmlns="http://www.w3.org/2000/svg">
            <defs><filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="3.2" result="b" />
              <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
            <g id="edges"></g><g id="nodes"></g>
          </svg>
        </div>
        <div className="cap" id="cap"></div>
      </div></section>

      <section id="deep" className="lp"><div className="wrap reveal">
        <h2>Deep <span className="g">dive</span></h2>
        <p className="lede">Plain English for everyone; under the hood for the engineer. Click a box in the map above to jump here.</p>
        <div id="ddwrap"></div>
      </div></section>

      <section id="secure" className="lp"><div className="wrap reveal">
        <h2>Locked <span className="g">down</span></h2>
        <p className="lede">Secure-by-design, in plain terms.</p>
        <div className="grid2">
          <div className="hood"><div className="h">Nobody walks in</div><ul><li>Real <code>@colt.net</code> email + shared password <b style={{ color: "var(--teal)" }}>+ a one-time code emailed to that inbox</b>. Guessing the first two isn't enough.</li></ul></div>
          <div className="hood"><div className="h">Secrets never in git</div><ul><li>Keys live only on the server or as encrypted GitHub secrets; <code>gitleaks</code> blocks accidental commits.</li></ul></div>
          <div className="hood"><div className="h">Scanned before ship</div><ul><li>Trivy (deps+image), CodeQL SAST, ruff, pytest - every change checked before it reaches the server.</li></ul></div>
          <div className="hood"><div className="h">Never breaks the neighbours</div><ul><li>Isolated <code>colt-stack</code>; the existing VPN and services and the firewall are untouched.</li></ul></div>
        </div>
      </div></section>

      <div className="foot"><div className="wrap">
        <div style={{ fontSize: 20, fontWeight: 800 }}><span className="chev">❯</span> colt</div>
        <p>Colt / S4Biz - cyber pre-sales automation / one name in, four boardroom decks out / built to run itself.</p>
        <Link className="btn" to="/login">Open the app</Link>
        <div className="g" style={{ marginTop: 18 }}>» » » » »</div>
      </div></div>
    </div>
  );
}
