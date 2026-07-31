import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import TabBar from "../components/TabBar.jsx";

export default function Landing() {
  const rootRef = useRef(null);
  // Mobile navigation. The section anchors were previously display:none under 720px, which removed
  // the whole site map from every phone. They now drive a native-app style bottom tab bar
  // (the jev.best pattern) with a scroll-spy that keeps the active tab in sync with the page.
  const nav = useNavigate();
  const TABS = [
    { id: "edge", label: "Why", href: "#edge" },
    { id: "demo", label: "Live", href: "#demo" },
    { id: "map", label: "Machine", href: "#map" },
    { id: "deep", label: "Deep", href: "#deep" },
    { id: "secure", label: "Secure", href: "#secure" },
    { id: "app", label: "Open", to: "/login" },
  ];
  const [tab, setTab] = useState("edge");

  const go = (t) => {
    if (t.to) { nav(t.to); return; }
    const el = document.querySelector(t.href);
    if (el) { setTab(t.id); el.scrollIntoView({ behavior: "smooth", block: "start" }); }
  };

  useEffect(() => {
    // scroll-spy: whichever section owns the middle of the viewport lights its tab
    const ids = ["edge", "demo", "map", "deep", "secure"];
    const els = ids.map((id) => document.getElementById(id)).filter(Boolean);
    if (!els.length) return;
    const io = new IntersectionObserver((entries) => {
      const vis = entries.filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (vis) setTab(vis.target.id);
    }, { rootMargin: "-45% 0px -45% 0px", threshold: [0, 0.15, 0.5, 1] });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

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
      { s: "me", t: "/auth WhatsApp +351 939 994 642 ********", cmd: "/auth" },
      { s: "them", typ: 900, t: "Code emailed. Reply /verify <code> (valid 10 min)." },
      { s: "me", t: "/verify 483920", cmd: "/verify" },
      { s: "them", typ: 700, t: "Verified. You're in." },
      { s: "me", t: "/assess Volkswagen AG", cmd: "/assess" },
      { s: "them", typ: 1000, t: "Assessing Volkswagen AG ..." },
      { s: "them", typ: 1600, t: "[auto] 9 ASNs / 41 domains / internal-CA VW-CA-PROC-09 / sweeping Shodan..." },
      { s: "file", fn: "VW_Shodan_Findings.pptx", fs: "2 CRIT / 4 HIGH / evidence + fixes", typ: 900 },
      { s: "file", fn: "VW_C-BIQ.pptx", fs: "portfolio ALE EUR 11M-29M" },
      { s: "file", fn: "VW_GEOPOL.pptx", fs: "APT41/Winnti +4 adversaries" },
      { s: "file", fn: "VW_DELTAS.pptx", fs: "value the fix buys back" },
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

    // ---- live regulatory countdowns. Real statutory dates; each retires itself to "LIVE NOW". ----
    const DEADLINES = [{ el: "cd1", date: "2026-07-31" }, { el: "cd2", date: "2026-08-02" }, { el: "cd3", date: "2026-09-11" }];
    function tickCd() {
      const now = new Date();
      DEADLINES.forEach((d) => {
        const n = root.querySelector("#" + d.el); if (!n) return;
        const ms = new Date(d.date + "T00:00:00Z") - now;
        if (ms <= 0) { n.textContent = "LIVE NOW"; n.classList.add("past"); return; }
        const dd = Math.floor(ms / 86400000), h = Math.floor(ms / 3600000) % 24,
              m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60;
        n.innerHTML = dd + "<i>d</i>" + String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0");
      });
    }
    tickCd();
    const cdTimer = setInterval(tickCd, 1000);
    cleanups.push(() => clearInterval(cdTimer));

    const C = { green: "#10B981", teal: "#00B2A9", gold: "#F7C844", purple: "#8b6cff", cyan: "#38e1ff" };
    const NODES = [
      { id: "you",    x: 105,  y: 110, ico: "phone",  t: "SALES",        s: "Telegram / one name",   c: C.green,  n: "1",  dd: "d1" },
      { id: "web",    x: 105,  y: 262, ico: "screen", t: "WEB APP",      s: "cybergod.ai cabinet",   c: C.green,  n: "1",  dd: "d1" },
      { id: "gh",     x: 105,  y: 462, ico: "octo",   t: "GITHUB CI/CD", s: "build/scan/ship",       c: C.teal,   n: "11", dd: "d11" },
      { id: "patch",  x: 105,  y: 602, ico: "patch",  t: "PATCHWATCH",   s: "self-patch /3d",        c: C.purple, n: "10", dd: "d10" },
      { id: "bot",    x: 355,  y: 110, ico: "shield", t: "assessment bot", s: "the assessor",          c: C.teal,   n: "1",  dd: "d1", big: true },
      { id: "cass",   x: 355,  y: 262, ico: "compass",t: "cassandra",    s: "research assistant",          c: C.teal,   n: "1",  dd: "d1" },
      { id: "auth",   x: 355,  y: 412, ico: "lock",   t: "ZERO-TRUST",   s: "email+pw+code",         c: C.purple, n: "2",  dd: "d2" },
      { id: "eng",    x: 600,  y: 252, ico: "gear",   t: "ENGINE",       s: "recon to decks",        c: C.teal,   n: "3",  dd: "d3", big: true },
      { id: "comp",   x: 600,  y: 422, ico: "scroll", t: "COMPLIANCE",   s: "NIS2 / CRA / AI Act",   c: C.teal,   n: "8",  dd: "d8", big: true },
      { id: "clar",   x: 600,  y: 582, ico: "chat",   t: "CLARIFY",      s: "deliver, then refine",  c: C.teal,   n: "7",  dd: "d7" },
      { id: "foot",   x: 850,  y: 95,  ico: "globe",  t: "FOOTPRINT",    s: "bgpview/RIPE/crt.sh",   c: C.gold,   n: "3",  dd: "d3" },
      { id: "shodan", x: 850,  y: 235, ico: "scope",  t: "SHODAN",       s: "paid / 30+ filters",    c: C.gold,   n: "4",  dd: "d4" },
      { id: "deep",   x: 850,  y: 375, ico: "bot",    t: "AI MODELS",    s: "multi-vendor chain",    c: C.gold,   n: "5",  dd: "d5" },
      { id: "audit",  x: 850,  y: 515, ico: "scale",  t: "AI AUDIT",     s: "2nd model checks it",   c: C.gold,   n: "6",  dd: "d6" },
      { id: "gmail",  x: 1095, y: 95,  ico: "mail",   t: "GMAIL API",    s: "2FA code / HTTPS",      c: C.gold,   n: "2",  dd: "d2" },
      { id: "decks",  x: 1095, y: 252, ico: "decks",  t: "DELIVERABLES", s: "4 decks + live report", c: C.green,  n: "5",  dd: "d5", big: true },
      { id: "graf",   x: 1095, y: 420, ico: "chart",  t: "GRAFANA",      s: "godeyes.ai/observe",    c: C.cyan,   n: "9",  dd: "d9" },
      { id: "spaces", x: 1095, y: 580, ico: "disk",   t: "SPACES",       s: "backups",               c: C.gold,   n: "10", dd: "d10" },
    ];
    const ICO = { phone: "\ud83d\udcf1", screen: "\ud83d\udda5\ufe0f", shield: "\ud83d\udee1\ufe0f", compass: "\ud83e\udded", lock: "\ud83d\udd10", gear: "\u2699\ufe0f", scroll: "\ud83d\udcdc", chat: "\ud83d\udcac", mail: "\u2709\ufe0f", globe: "\ud83c\udf10", scope: "\ud83d\udd2d", bot: "\ud83e\udd16", scale: "\u2696\ufe0f", decks: "\ud83d\udcd1", disk: "\ud83d\udcbe", chart: "\ud83d\udcc8", octo: "\ud83d\udc19", patch: "\ud83e\ude79" };
    const EDGES = [
      { a: "you", b: "bot", c: C.green }, { a: "you", b: "cass", c: C.green },
      { a: "web", b: "auth", c: C.green }, { a: "web", b: "comp", c: C.green, bow: -40 },
      { a: "bot", b: "auth", c: C.purple }, { a: "cass", b: "auth", c: C.purple },
      { a: "auth", b: "gmail", c: C.gold, two: true, bow: 80 },
      { a: "auth", b: "eng", c: C.teal },
      { a: "eng", b: "foot", c: C.gold, two: true }, { a: "eng", b: "shodan", c: C.gold, two: true },
      { a: "eng", b: "deep", c: C.gold, two: true }, { a: "eng", b: "audit", c: C.gold, two: true },
      { a: "comp", b: "deep", c: C.gold, two: true },
      { a: "eng", b: "decks", c: C.green }, { a: "comp", b: "decks", c: C.green },
      { a: "decks", b: "clar", c: C.teal, bow: -90 }, { a: "clar", b: "eng", c: C.teal, two: true },
      { a: "eng", b: "graf", c: C.cyan }, { a: "bot", b: "graf", c: C.cyan, bow: 120 },
      { a: "patch", b: "spaces", c: C.purple, bow: -60 }, { a: "patch", b: "eng", c: C.purple },
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
      { ids: ["you", "web", "bot"], t: "1 - One input: a company name. From Telegram, or from the cybergod.ai web app." },
      { ids: ["bot", "auth", "gmail"], t: "2 - Zero-trust: approved email + password + a one-time code emailed to that inbox." },
      { ids: ["auth", "eng", "foot"], t: "3 - The engine auto-resolves the company's entire footprint. You type no IPs." },
      { ids: ["eng", "shodan"], t: "4 - It sweeps Shodan for every exposed door - and pivots on their own private CA." },
      { ids: ["eng", "deep", "decks"], t: "5 - A multi-vendor AI chain writes the prose; templates lock the numbers into the decks." },
      { ids: ["eng", "audit"], t: "6 - A SECOND AI, from a different vendor, audits the findings for false positives before you ever see them." },
      { ids: ["decks", "clar", "eng"], t: "7 - Decks land first - then it asks what it could not resolve. You answer, it re-scopes and rebuilds." },
      { ids: ["web", "comp", "decks"], t: "8 - Compliance: NIS2, the Cyber Resilience Act and the EU AI Act - from the same one input." },
      { ids: ["bot", "eng", "graf"], t: "9 - Every login, assessment, audit and patch is logged live to Grafana." },
      { ids: ["patch", "spaces", "eng"], t: "10 - patchwatch backs up to Spaces, then patches the server itself every 3 days." },
      { ids: ["gh", "eng"], t: "11 - One command builds, scans and ships it - and proves the container really holds the new code." },
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
      { id: "d1", n: "1", ic: "\ud83d\udcf1", c: C.green, h: "Two front doors, one input", plain: "Type a company name - in <b>Telegram</b>, or in the <b>cybergod.ai web app</b>. Same engine, same decks. Two bots live on the server: the <b>assessment bot</b> runs the scan, <b>cassandra</b> answers questions about the findings.", hood: ["<code>python-telegram-bot</code>, one per bot, in Docker", "React cabinet: Assess / Compliance / Assistant / History", "The run is owned by the SERVER - lock your phone, it keeps going"] },
      { id: "d2", n: "2", ic: "\ud83d\udd10", c: C.purple, h: "Zero-trust login (2FA)", plain: "You need an approved <b>company or partner email</b>, the shared password, <b>and</b> a one-time code emailed to that inbox. Knowing the password isn't enough - you must own the mailbox.", hood: ["Shared auth module: constant-time compare, lockout, 10-min codes", "OTP delivered via <b>Gmail API over HTTPS</b> (droplet blocks SMTP ports)", "One gate shared by the bots AND the web app - they can never disagree"] },
      { id: "d3", n: "3", ic: "\ud83e\udde9", c: C.teal, h: "The engine + auto-discovery", plain: "From just the name the engine finds the company's <b>networks, domains and certificates</b> - then hunts, scores and writes. You never hand it an IP.", hood: ["ASNs+prefixes from RIPE + CAIDA + PeeringDB + bgpview", "Brand domains/subdomains: <code>crt.sh</code> + CertSpotter CT logs + DNS probe", "Ownership gate: a discovered domain is a CANDIDATE, never proof", "Scope blow-out guard - it refuses to build decks from an unverified estate"] },
      { id: "d4", n: "4", ic: "\ud83d\udd2d", c: C.gold, h: "Shodan - what's exposed", plain: "It queries Shodan for exposed remote-access, databases, VPNs, mail, industrial gear and known-vulnerable systems - plus the killer pivot: the company's own private CA and whois-org, which reveal the hidden estate.", hood: ["30+ super-filters; edge appliances (firewalls, VPN concentrators) = CRITICAL", "Paid facets: <code>has_vuln</code>, <code>vuln:CVE</code>, <code>tag:ics</code>, <code>ssl.jarm</code>", "CDN/honeypot false-positives dropped automatically"] },
      { id: "d5", n: "5", ic: "\ud83e\udd16", c: C.gold, h: "The AI writes it - you get five artifacts", plain: "A chain of AI models writes the words; fixed templates guarantee the structure and the maths. You get <b>Findings / C-BIQ (EUR) / GEOPOL / DELTAS</b> plus a <b>live animated report</b> you present on screen - in English or Hochdeutsch.", hood: ["Multi-VENDOR chain with failover - a 429 is provider-wide, so the backup must be another vendor", "<code>pptxgenjs</code> templates lock layout; numbers stay deterministic", "Hallucination guard: any CVE not in the scan evidence is stripped, and logged"] },
      { id: "d6", n: "6", ic: "\u2696\ufe0f", c: C.gold, h: "A second AI audits the first", plain: "Before you ever see the decks, a <b>different model from a different vendor</b> re-reads every finding and challenges anything that looks like it isn't really theirs. A model is never allowed to mark its own homework.", hood: ["<code>audit_fp.py</code> picks an auditor that differs from the deck author - it refuses to self-audit", "The LLM can FLAG, but a finding is only dropped when deterministic ownership data agrees", "Hard guardrail: it can never empty a deck, or drop more than 40% of findings", "Every audit is logged: auditor vs author, verdict, dropped, refused"] },
      { id: "d7", n: "7", ic: "\ud83d\udcac", c: C.teal, h: "It asks you what it couldn't work out", plain: "The decks land <b>first</b>. Then the engine tells you what it could not resolve - which related domains are yours, your netblocks if you sit behind a CDN, anything in the report that isn't yours - you answer, and it re-scopes and rebuilds.", hood: ["Questions are DETERMINISTIC, not LLM-written - auditable, free, never invents a domain", "Your answers are the ONE sanctioned way scope changes after a run", "Because you asserted the fact, the zero-false-positive rules stay intact"] },
      { id: "d8", n: "8", ic: "\ud83d\udcdc", c: C.teal, h: "Compliance: NIS2, CRA, EU AI Act", plain: "The same one input, pointed at regulation. It grades the company against the three horizontal EU digital laws and writes <b>three regime decks, a roadmap deck and an animated report</b> - applicability, duties, gaps, deadlines and the maximum fine.", hood: ["Grounded ONLY in a committed reference of the primary legal texts", "The model infers sector/size/product/AI profile and STATES it - you confirm and it rebuilds", "Deterministic fallback holds the fixed facts, so obligations and fines are right even if the model is down", "Not legal advice - and every deck says so"] },
      { id: "d9", n: "9", ic: "\ud83d\udcc8", c: C.cyan, h: "Always watching", plain: "Every login, assessment, audit, cost and patch prints a structured line that flows into <b>your existing Grafana</b> - no second monitoring stack.", hood: ["events.log to <code>promtail</code> to Loki to Grafana (<code>godeyes.ai/observe</code>)", "Per-run cost ledger in SQLite - true lifetime spend, survives log retention", "11 live security rules: brute force, spraying, scanners, IDOR probes, exfil bursts"] },
      { id: "d10", n: "10", ic: "\ud83e\ude79", c: C.purple, h: "It patches itself", plain: "A server nobody patches gets hacked. Every 3 days it <b>backs itself up</b> to Spaces, upgrades the OS/Docker, and an AI writes a risk digest. Reboots happen at 4am.", hood: ["<code>patchwatch/</code> systemd timer; backup-first (abort if the backup fails)", "DO Spaces tarball + optional droplet snapshot", "AI digest to Telegram + Grafana"] },
      { id: "d11", n: "11", ic: "\ud83d\ude80", c: C.teal, h: "Shipping is one command", plain: "Change the code, run one thing, it's live - and it <b>proves</b> the running container actually holds the new code before it reports success.", hood: ["<code>python ship.py</code>: test to commit to push to deploy to VERIFY", "Engine-hash check: sha256 inside the container vs the repo - a stale container fails the ship", "Tagged safe-points and <code>--rollback</code> to any known-good state"] },
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
        <span className="brand"><span className="chev">❯</span> cybergod<span class="g">.ai</span></span>
        <nav>
          <a href="#edge">Why it matters</a><a href="#demo">See it live</a><a href="#map">The machine</a>
          <a href="#deep">Deep dive</a><a href="#secure">Security</a><Link to="/contact">Contact</Link>
          {/* Demo is a .btn so the phone rule (#hd nav a:not(.btn){display:none}) keeps it visible —
              it is the one entry point an anonymous visitor can actually use. */}
          <Link className="btn sm ghost" to="/demo">Demo</Link>
          <Link className="btn sm" to="/login">Open the app</Link>
        </nav>
      </div></header>

      <section className="hero">
        <canvas id="dust"></canvas>
        <div className="wrap">
          <div className="kick">Cybergod LLC / S4Biz Group - external cyber-risk assessment</div>
          <h1>Type a company name.<br /><span className="g">Four boardroom decks.</span> Two minutes.</h1>
          <p className="sub">Every organisation has an internet-facing footprint it cannot fully see. From one
            company name, this maps yours using public sources alone, prices the risk in euros, names the
            groups most likely to target you, and shows which EU deadlines already apply - without touching
            a single one of your systems.</p>
          <div className="cta-row">
            <Link className="btn" to="/login">Open the app / Log in</Link>
            <Link className="btn ghost" to="/demo">See a full demo report</Link>
          </div>
        </div>
      </section>

      <section className="creed"><div className="wrap reveal">
        <div className="creed-kick">The name is not an accident</div>
        <blockquote className="creed-q">
          <span className="l1">Cassandra foretold the fall of Troy &mdash; and no one believed her.</span>
          <span className="l2">We predict the <b>critical cyber risks</b>, stop them
            <b> before they materialise</b>, and keep every <b>Trojan horse</b> out of your IT landscape.</span>
        </blockquote>
        <div className="creed-rule" aria-hidden="true"><i></i><span>&#9670;</span><i></i></div>
      </div></section>

      <section id="edge" className="lp edge"><div className="wrap reveal">
        <div className="kick2">For boards, CISOs and risk owners</div>
        <h2>What you cannot see is <span className="g">already public</span></h2>
        <p className="lede">Your internet-facing footprint grows every quarter - a forgotten host, a
          supplier portal, a VPN nobody decommissioned, a certificate that quietly names an internal
          system. An attacker enumerates all of it in minutes, from public sources, without ever
          touching you. Most organisations have never looked at themselves the same way.</p>

        <div className="vs">
          <div className="vsc bad"><h4>How it usually goes</h4><ul>
            <li>An annual test, scoped to what you remembered to list</li>
            <li>A findings spreadsheet with no price attached to anything</li>
            <li>Weeks between the question and the answer</li>
            <li>The board asks what it would actually cost. Nobody knows.</li>
            <li className="last">Compliance deadlines live in somebody&rsquo;s inbox.</li></ul></div>
          <div className="vsc good"><h4>What you get here</h4><ul>
            <li>Your whole internet-facing estate, discovered from public data</li>
            <li>Every exposure modelled in euros, with the method shown</li>
            <li>Minutes, not weeks - and repeatable whenever you want</li>
            <li>A number the board can actually make a decision on</li>
            <li className="last">The regulatory clock, on one slide.</li></ul></div>
        </div>

        <h3 className="eh">Three questions decide a security budget. You should be able to answer all
          three <span className="g">today</span>.</h3>
        <div className="tri">
          <div className="tric"><div className="tt" style={{ color: "var(--teal)" }}>WHO</div>
            <p>The threat groups realistically interested in your sector and geography - and the route
              they would most likely take into you.</p>
            <span className="src">GEOPOL deck</span></div>
          <div className="tric"><div className="tt" style={{ color: "var(--gold)" }}>HOW MUCH</div>
            <p>Your exposure modelled in euros - expected annual loss, worst realistic case, and the
              return on fixing it first.</p>
            <span className="src">C-BIQ deck</span></div>
          <div className="tric"><div className="tt" style={{ color: "#ff5c74" }}>WHEN</div>
            <p>The regulatory dates that already apply to you - and the maximum fine attached to each
              of them.</p>
            <span className="src">Compliance decks</span></div>
        </div>

        <h3 className="eh">The clocks are <span className="r">already running</span></h3>
        <p className="lede small">Three EU laws now reach most mid-size organisations: NIS2, the Cyber
          Resilience Act and the EU AI Act. These dates are written in law, not on a vendor&rsquo;s slide -
          and the penalties are set against global turnover.</p>
        <div className="clocks">
          <div className="clock"><div className="reg">NIS2 &mdash; Germany</div><div className="fine">&euro;10m / 2% of turnover</div>
            <div className="num" id="cd1">&mdash;</div>
            <div className="cap2">until the BSI registration grace period ends &middot; 31 Jul 2026</div></div>
          <div className="clock"><div className="reg">EU AI Act</div><div className="fine">&euro;35m / 7% of turnover</div>
            <div className="num" id="cd2">&mdash;</div>
            <div className="cap2">until high-risk obligations apply &middot; 2 Aug 2026</div></div>
          <div className="clock"><div className="reg">Cyber Resilience Act</div><div className="fine">&euro;15m / 2.5% of turnover</div>
            <div className="num" id="cd3">&mdash;</div>
            <div className="cap2">until incident &amp; vulnerability reporting &middot; 11 Sep 2026</div></div>
        </div>

        <div className="unlock">
          <h3>Nothing of yours is touched</h3>
          <p>This is not a penetration test and it is not a scan of your systems. No ports are probed,
            no logins attempted, no agent installed, no credentials required. It reads only what is
            already public - the internet equivalent of noting which doors are visible from the street.
            <b> That is precisely why it can show you what an attacker already sees, with no change
            request, no maintenance window, and not one packet sent to your infrastructure.</b></p>
        </div>

        <h3 className="eh">Where it earns its place</h3>
        <div className="plays">
          {[["01","Before the board","Walk in with the exposure and the euro number instead of adjectives."],["02","Before an audit","NIS2, CRA and AI-Act applicability, duties and deadlines on a single page."],["03","After an acquisition","See the estate you have just inherited, mapped from the outside in."],["04","Third-party risk","Assess a supplier the same way - no access, no questionnaire, no waiting."],["05","Quarter on quarter","Re-run it and see exactly what changed on your perimeter."],["+","Your own first look","Most organisations find something public they did not know was there."]].map(([n, t, b]) => (
            <div className="play" key={n}><span className="pn">{n}</span><b>{t}</b><p>{b}</p></div>
          ))}
        </div>

        <h3 className="eh">Fair questions</h3>
        <div className="tri">
          <div className="tric"><div className="tt" style={{ fontSize: 19, color: "var(--teal)" }}>&ldquo;Is this legal?&rdquo;</div>
            <p>Yes. It uses public sources any researcher could look up, and never interacts with your
              systems. Nothing is exploited, nothing is logged into.</p></div>
          <div className="tric"><div className="tt" style={{ fontSize: 19, color: "var(--teal)" }}>&ldquo;How accurate is it?&rdquo;</div>
            <p>Every finding carries the evidence behind it. Where a source cannot be reached it says
              &ldquo;unknown&rdquo; rather than inventing a weakness - and it asks you to confirm anything
              it could not resolve.</p></div>
          <div className="tric"><div className="tt" style={{ fontSize: 19, color: "var(--teal)" }}>&ldquo;What do we have to provide?&rdquo;</div>
            <p>Your company name. No access, no questionnaire, no NDA to start, and nothing to install.
              The euro figures are modelled ranges with the assumptions shown.</p></div>
        </div>

        <div className="pullq">The question is not whether something of yours is exposed.{" "}
          <span className="g">It is whether you know what.</span></div>
        <div className="cta-row" style={{ justifyContent: "center" }}>
          <Link className="btn" to="/contact">Request an assessment</Link>
        </div>
      </div></section>

      <section id="demo" className="lp"><div className="wrap reveal">
        <h2>See it <span className="g">live</span></h2>
        <p className="lede">This is the entire product - texting a bot. The chat below plays the real flow: log in, ask, get four decks.</p>
        <div className="demo">
          <div className="phone"><div className="notch"></div><div className="screen">
            <div className="tgh"><span className="bk">‹</span><div className="av">C</div>
              <div><div className="nm">assessment bot</div><div className="st">bot / online</div></div>
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
        <p className="maphint">Swipe the map sideways to explore &rarr;</p>
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
          <div className="hood"><div className="h">Nobody walks in</div><ul><li>Real <code>your approved address</code> email + shared password <b style={{ color: "var(--teal)" }}>+ a one-time code emailed to that inbox</b>. Guessing the first two isn't enough.</li></ul></div>
          <div className="hood"><div className="h">Secrets never in git</div><ul><li>Keys live only on the server or as encrypted GitHub secrets; <code>gitleaks</code> blocks accidental commits.</li></ul></div>
          <div className="hood"><div className="h">Scanned before ship</div><ul><li>Trivy (deps+image), CodeQL SAST, ruff, pytest - every change checked before it reaches the server.</li></ul></div>
          <div className="hood"><div className="h">Never breaks the neighbours</div><ul><li>An isolated container stack; existing services and the firewall are untouched.</li></ul></div>
        </div>
      </div></section>

      <div className="foot"><div className="wrap">
        <div style={{ fontSize: 20, fontWeight: 800 }}><span className="chev">❯</span> cybergod<span class="g">.ai</span></div>
        <p>Cybergod LLC / S4Biz Group - external cyber-risk and EU compliance assessment / one company name in, four boardroom documents out.</p>
        <Link className="btn" to="/login">Open the app</Link>
        <div className="footlinks">
          <Link to="/contact">Kontakt / Contact</Link><span>&middot;</span>
          <Link to="/impressum">Impressum</Link><span>&middot;</span>
          <Link to="/privacy">Datenschutz / Privacy</Link>
        </div>
        <p className="foothost">Betrieben in Deutschland &middot; Server in Frankfurt am Main (FRA1) &middot; Ihre Daten bleiben in der EU.</p>
        <div className="g" style={{ marginTop: 18 }}>» » » » »</div>
      </div></div>

      <TabBar tabs={TABS} active={tab} onGo={go} />
    </div>
  );
}
