import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import TabBar from "../components/TabBar.jsx";
import WhatsAppFab from "../components/WhatsAppFab.jsx";
import SiteHeader from "../components/SiteHeader.jsx";
import { useT, useTx } from "../i18n";

export default function Landing() {
  const [lang, , t] = useT();
  const tx = useTx();
  const rootRef = useRef(null);
  // Mobile navigation. The section anchors were previously display:none under 720px, which removed
  // the whole site map from every phone. They now drive a native-app style bottom tab bar
  // (the jev.best pattern) with a scroll-spy that keeps the active tab in sync with the page.
  const nav = useNavigate();
  const TABS = [
    { id: "edge", label: t("tab.why"), href: "#edge" },
    { id: "demo", label: t("tab.live"), href: "#demo" },
    { id: "map", label: t("tab.machine"), href: "#map" },
    { id: "deep", label: t("tab.deep"), href: "#deep" },
    { id: "secure", label: t("tab.secure"), href: "#secure" },
    { id: "app", label: t("tab.open"), to: "/login" },
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
      { s: "me", t: "/auth anna.schmidt@yourcompany.com ********", cmd: "/auth" },
      { s: "them", typ: 900, t: tx("Code emailed. Reply /verify <code> (valid 10 min).") },
      { s: "me", t: "/verify 483920", cmd: "/verify" },
      { s: "them", typ: 700, t: tx("Verified. You're in.") },
      { s: "me", t: "/assess Volkswagen AG", cmd: "/assess" },
      { s: "them", typ: 1000, t: tx("Assessing Volkswagen AG ...") },
      { s: "them", typ: 1600, t: tx("[auto] 9 ASNs / 41 domains / internal-CA VW-CA-PROC-09 / sweeping Shodan...") },
      { s: "file", fn: "VW_Shodan_Findings.pptx", fs: tx("2 CRIT / 4 HIGH / evidence + fixes"), typ: 900 },
      { s: "file", fn: "VW_C-BIQ.pptx", fs: tx("portfolio ALE EUR 11M-29M") },
      { s: "file", fn: "VW_GEOPOL.pptx", fs: tx("APT41/Winnti +4 adversaries") },
      { s: "file", fn: "VW_DELTAS.pptx", fs: tx("value the fix buys back") },
      { s: "them", typ: 600, t: tx("Done in 2m 10s. 4 decks ready.") },
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
        if (ms <= 0) { n.textContent = tx("LIVE NOW"); n.classList.add("past"); return; }
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
      { id: "you",    x: 105,  y: 110, ico: "phone",  t: tx("SALES"),        s: tx("Telegram / one name"),   c: C.green,  n: "1",  dd: "d1" },
      { id: "web",    x: 105,  y: 262, ico: "screen", t: tx("WEB APP"),      s: tx("cybergod.ai cabinet"),   c: C.green,  n: "1",  dd: "d1" },
      { id: "gh",     x: 105,  y: 462, ico: "octo",   t: tx("GITHUB CI/CD"), s: tx("build/scan/ship"),       c: C.teal,   n: "11", dd: "d11" },
      { id: "patch",  x: 105,  y: 602, ico: "patch",  t: tx("PATCHWATCH"),   s: tx("self-patch /3d"),        c: C.purple, n: "10", dd: "d10" },
      { id: "bot",    x: 355,  y: 110, ico: "shield", t: tx("assessment bot"), s: tx("the assessor"),        c: C.teal,   n: "1",  dd: "d1", big: true },
      { id: "cass",   x: 355,  y: 262, ico: "compass",t: tx("cassandra"),    s: tx("research assistant"),    c: C.teal,   n: "1",  dd: "d1" },
      { id: "auth",   x: 355,  y: 412, ico: "lock",   t: tx("ZERO-TRUST"),   s: tx("email+pw+code"),         c: C.purple, n: "2",  dd: "d2" },
      { id: "eng",    x: 600,  y: 252, ico: "gear",   t: tx("ENGINE"),       s: tx("recon to decks"),        c: C.teal,   n: "3",  dd: "d3", big: true },
      { id: "comp",   x: 600,  y: 422, ico: "scroll", t: tx("COMPLIANCE"),   s: tx("EU + Canada regimes"),   c: C.teal,   n: "8",  dd: "d8", big: true },
      { id: "clar",   x: 600,  y: 582, ico: "chat",   t: tx("CLARIFY"),      s: tx("deliver, then refine"),  c: C.teal,   n: "7",  dd: "d7" },
      { id: "foot",   x: 850,  y: 95,  ico: "globe",  t: tx("FOOTPRINT"),    s: tx("bgpview/RIPE/crt.sh"),   c: C.gold,   n: "3",  dd: "d3" },
      { id: "shodan", x: 850,  y: 235, ico: "scope",  t: tx("SHODAN"),       s: tx("paid / 30+ filters"),    c: C.gold,   n: "4",  dd: "d4" },
      { id: "deep",   x: 850,  y: 375, ico: "bot",    t: tx("AI MODELS"),    s: tx("multi-vendor chain"),    c: C.gold,   n: "5",  dd: "d5" },
      { id: "audit",  x: 850,  y: 515, ico: "scale",  t: tx("AI AUDIT"),     s: tx("2nd model checks it"),   c: C.gold,   n: "6",  dd: "d6" },
      { id: "gmail",  x: 1095, y: 95,  ico: "mail",   t: tx("GMAIL API"),    s: tx("2FA code / HTTPS"),      c: C.gold,   n: "2",  dd: "d2" },
      { id: "decks",  x: 1095, y: 252, ico: "decks",  t: tx("DELIVERABLES"), s: tx("4 decks + live report"), c: C.green,  n: "5",  dd: "d5", big: true },
      { id: "graf",   x: 1095, y: 420, ico: "chart",  t: tx("GRAFANA"),      s: tx("godeyes.ai/observe"),    c: C.cyan,   n: "9",  dd: "d9" },
      { id: "spaces", x: 1095, y: 580, ico: "disk",   t: tx("SPACES"),       s: tx("backups"),               c: C.gold,   n: "10", dd: "d10" },
      // ---- added 7 Aug 2026: the parts of the system the first map predates ------------------
      // SCOPE GUARDS is the accuracy story and the hardest-won code in the product: ownership
      // gate, public-suffix rule, co-tenant guard, per-domain and per-pivot budgets.
      { id: "scope",  x: 600,  y: 95,  ico: "filter", t: tx("SCOPE GUARDS"), s: tx("ownership, not guesswork"), c: C.cyan, n: "3", dd: "d3", big: true },
      // The consensus panel: 2 soldiers + 2 auditors, one per vendor, deterministic gate.
      { id: "quorum", x: 850,  y: 655, ico: "panel",  t: tx("AI CONSENSUS"), s: tx("4 models, 4 vendors"),   c: C.purple, n: "6", dd: "dq", big: true },
      { id: "stage",  x: 355,  y: 562, ico: "twin",   t: tx("STAGING TWIN"), s: tx("built, rebooted, checked"), c: C.purple, n: "11", dd: "d11" },
      { id: "guard",  x: 355,  y: 702, ico: "wall",   t: tx("PROXY GUARD"),  s: tx("config cannot break"),   c: C.purple, n: "11", dd: "d11" },
      { id: "cost",   x: 1095, y: 700, ico: "coin",   t: tx("COST LEDGER"),  s: tx("every run, priced"),     c: C.cyan,   n: "9",  dd: "d9" },
    ];
    const ICO = { phone: "\ud83d\udcf1", screen: "\ud83d\udda5\ufe0f", shield: "\ud83d\udee1\ufe0f", compass: "\ud83e\udded", lock: "\ud83d\udd10", gear: "\u2699\ufe0f", scroll: "\ud83d\udcdc", chat: "\ud83d\udcac", mail: "\u2709\ufe0f", globe: "\ud83c\udf10", scope: "\ud83d\udd2d", bot: "\ud83e\udd16", scale: "\u2696\ufe0f", decks: "\ud83d\udcd1", disk: "\ud83d\udcbe", chart: "\ud83d\udcc8", octo: "\ud83d\udc19", patch: "\ud83e\ude79", filter: "\ud83e\udded", panel: "\u2696\ufe0f", twin: "\ud83e\uddea", wall: "\ud83e\uddf1", coin: "\ud83d\udcb0" };
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
      // ---- added 7 Aug 2026 -------------------------------------------------------------------
      { a: "eng", b: "scope", c: C.cyan, two: true },
      { a: "scope", b: "shodan", c: C.cyan },
      { a: "gh", b: "stage", c: C.purple }, { a: "stage", b: "quorum", c: C.purple, two: true },
      { a: "quorum", b: "eng", c: C.purple, bow: -140 },
      { a: "stage", b: "guard", c: C.purple }, { a: "guard", b: "web", c: C.purple, bow: -70 },
      { a: "deep", b: "cost", c: C.cyan, bow: 60 }, { a: "cost", b: "graf", c: C.cyan },
      { a: "audit", b: "quorum", c: C.purple },
    ];
    const NS = "http://www.w3.org/2000/svg";
    const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));
    const el = (t, a) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
    const pathD = (a, b, bow) => { const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - (bow || 0); return "M " + a.x + " " + a.y + " Q " + mx + " " + my + " " + b.x + " " + b.y; };
    const eg = root.querySelector("#edges"), ng = root.querySelector("#nodes");
    // The effect re-runs when the language changes; without clearing, every node and
    // edge is appended a second time and the map renders on top of itself.
    if (eg) eg.innerHTML = "";
    if (ng) ng.innerHTML = "";
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
      { ids: ["you", "web", "bot"], t: tx("1 - One input: a company name. From Telegram, or from the cybergod.ai web app.") },
      { ids: ["bot", "auth", "gmail"], t: tx("2 - Zero-trust: approved email + password + a one-time code emailed to that inbox.") },
      { ids: ["auth", "eng", "foot"], t: tx("3 - The engine auto-resolves the company's entire footprint. You type no IPs.") },
      { ids: ["eng", "shodan"], t: tx("4 - It sweeps Shodan for every exposed door - and pivots on their own private CA.") },
      { ids: ["eng", "deep", "decks"], t: tx("5 - A multi-vendor AI chain writes the prose; templates lock the numbers into the decks.") },
      { ids: ["eng", "audit"], t: tx("6 - A SECOND AI, from a different vendor, audits the findings for false positives before you ever see them.") },
      { ids: ["decks", "clar", "eng"], t: tx("7 - Decks land first - then it asks what it could not resolve. You answer, it re-scopes and rebuilds.") },
      { ids: ["web", "comp", "decks"], t: tx("8 - Compliance: NIS2, the Cyber Resilience Act and the EU AI Act - from the same one input.") },
      { ids: ["bot", "eng", "graf"], t: tx("9 - Every login, assessment, audit and patch is logged live to Grafana.") },
      { ids: ["patch", "spaces", "eng"], t: tx("10 - patchwatch backs up to Spaces, then patches the server itself every 3 days.") },
      { ids: ["gh", "eng"], t: tx("11 - One command builds, scans and ships it - and proves the container really holds the new code.") },
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
          if (cap) cap.classList.remove("show"); tbtn.textContent = "▶ " + tx("Guided tour"); tbtn.classList.remove("off");
        } else {
          touring = true; ti = 0; step(); tbtn.textContent = "⏸ " + tx("Stop tour"); tbtn.classList.add("off");
          const map = root.querySelector("#map"); if (map) map.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      };
    }

    const DD = [
      { id: "d1", n: "1", ic: "\ud83d\udcf1", c: C.green, h: "Two front doors, one input", plain: "Type a company name - in <b>Telegram</b>, or in the <b>cybergod.ai web app</b>. Same engine, same decks. Two bots live on the server: the <b>assessment bot</b> runs the scan, <b>cassandra</b> answers questions about the findings.", hood: ["<code>python-telegram-bot</code>, one per bot, in Docker", "React cabinet: Assess / Compliance / Assistant / History", "The run is owned by the SERVER - lock your phone, it keeps going"] },
      { id: "d2", n: "2", ic: "\ud83d\udd10", c: C.purple, h: "Zero-trust login (2FA)", plain: "You need an approved <b>company or partner email</b>, the shared password, <b>and</b> a one-time code emailed to that inbox. Knowing the password isn't enough - you must own the mailbox.", hood: ["Shared auth module: constant-time compare, lockout, 10-min codes", "OTP delivered via <b>Gmail API over HTTPS</b> (droplet blocks SMTP ports)", "One gate shared by the bots AND the web app - they can never disagree"] },
      { id: "d3", n: "3", ic: "\ud83e\udde9", c: C.teal, h: "The engine + auto-discovery", plain: "From just the name the engine finds the company's <b>networks, domains and certificates</b> - then hunts, scores and writes. You never hand it an IP.", hood: ["ASNs+prefixes from RIPE + CAIDA + PeeringDB + bgpview", "Brand domains/subdomains: <code>crt.sh</code> + CertSpotter CT logs + DNS probe", "Ownership gate: a discovered domain is a CANDIDATE, never proof", "Scope blow-out guard - it refuses to build decks from an unverified estate"] },
      { id: "d4", n: "4", ic: "\ud83d\udd2d", c: C.gold, h: "Shodan - what's exposed", plain: "It queries Shodan for exposed remote-access, databases, VPNs, mail, industrial gear and known-vulnerable systems - plus the killer pivot: the company's own private CA and whois-org, which reveal the hidden estate.", hood: ["30+ super-filters; edge appliances (firewalls, VPN concentrators) = CRITICAL", "Paid facets: <code>has_vuln</code>, <code>vuln:CVE</code>, <code>tag:ics</code>, <code>ssl.jarm</code>", "CDN/honeypot false-positives dropped automatically"] },
      { id: "d5", n: "5", ic: "\ud83e\udd16", c: C.gold, h: "The AI writes it - you get five artifacts", plain: "A chain of AI models writes the words; fixed templates guarantee the structure and the maths. You get <b>Findings / C-BIQ (EUR) / GEOPOL / DELTAS</b> plus a <b>live animated report</b> you present on screen.", hood: ["Multi-VENDOR chain with failover - a 429 is provider-wide, so the backup must be another vendor", "<code>pptxgenjs</code> templates lock layout; numbers stay deterministic", "Hallucination guard: any CVE not in the scan evidence is stripped, and logged"] },
      { id: "d6", n: "6", ic: "\u2696\ufe0f", c: C.gold, h: "A second AI audits the first", plain: "Before you ever see the decks, a <b>different model from a different vendor</b> re-reads every finding and challenges anything that looks like it isn't really theirs. A model is never allowed to mark its own homework.", hood: ["<code>audit_fp.py</code> picks an auditor that differs from the deck author - it refuses to self-audit", "The LLM can FLAG, but a finding is only dropped when deterministic ownership data agrees", "Hard guardrail: it can never empty a deck, or drop more than 40% of findings", "Every audit is logged: auditor vs author, verdict, dropped, refused"] },
      { id: "d7", n: "7", ic: "\ud83d\udcac", c: C.teal, h: "It asks you what it couldn't work out", plain: "The decks land <b>first</b>. Then the engine tells you what it could not resolve - which related domains are yours, your netblocks if you sit behind a CDN, anything in the report that isn't yours - you answer, and it re-scopes and rebuilds.", hood: ["Questions are DETERMINISTIC, not LLM-written - auditable, free, never invents a domain", "Your answers are the ONE sanctioned way scope changes after a run", "Because you asserted the fact, the zero-false-positive rules stay intact"] },
      { id: "d8", n: "8", ic: "\ud83d\udcdc", c: C.teal, h: "Compliance: NIS2, CRA, EU AI Act", plain: "The same one input, pointed at regulation. It grades the company against the three horizontal EU digital laws and writes <b>three regime decks, a roadmap deck and an animated report</b> - applicability, duties, gaps, deadlines and the maximum fine.", hood: ["Grounded ONLY in a committed reference of the primary legal texts", "The model infers sector/size/product/AI profile and STATES it - you confirm and it rebuilds", "Deterministic fallback holds the fixed facts, so obligations and fines are right even if the model is down", "Not legal advice - and every deck says so"] },
      { id: "d9", n: "9", ic: "\ud83d\udcc8", c: C.cyan, h: "Always watching", plain: "Every login, assessment, audit, cost and patch prints a structured line that flows into <b>your existing Grafana</b> - no second monitoring stack.", hood: ["events.log to <code>promtail</code> to Loki to Grafana (<code>godeyes.ai/observe</code>)", "Per-run cost ledger in SQLite - true lifetime spend, survives log retention", "11 live security rules: brute force, spraying, scanners, IDOR probes, exfil bursts"] },
      { id: "d10", n: "10", ic: "\ud83e\ude79", c: C.purple, h: "It patches itself", plain: "A server nobody patches gets hacked. Every 3 days it <b>backs itself up</b> to Spaces, upgrades the OS/Docker, and an AI writes a risk digest. Reboots happen at 4am.", hood: ["<code>patchwatch/</code> systemd timer; backup-first (abort if the backup fails)", "DO Spaces tarball + optional droplet snapshot", "AI digest to Telegram + Grafana"] },
      { id: "d11", n: "11", ic: "\ud83d\ude80", c: C.teal, h: "Shipping is one command", plain: "Change the code, run one thing, it's live - and it <b>proves</b> the running container actually holds the new code before it reports success.", hood: ["<code>python ship.py</code>: test to commit to push to deploy to VERIFY", "Engine-hash check: sha256 inside the container vs the repo - a stale container fails the ship", "Tagged safe-points and <code>--rollback</code> to any known-good state"] },
    ];
    const dw = root.querySelector("#ddwrap");
    if (dw) {
      dw.innerHTML = "";      // rebuilt whenever the language changes; never append twice
      DD.forEach((d) => {
        const s = document.createElement("div");
        s.className = "dd reveal"; s.id = d.id;
        s.innerHTML = '<div class="num" style="background:' + d.c + '">' + d.n + '</div><div><h3><span class="ic">' + d.ic + "</span>" + tx(d.h) + '</h3><p class="plain">' + tx(d.plain) + '</p><div class="flowstrip" style="--c:' + d.c + '"><i></i></div><div class="hood"><div class="h">' + tx("Under the hood - for the engineer") + '</div><ul>' + d.hood.map((x) => "<li>" + tx(x) + "</li>").join("") + "</ul></div></div>";
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
  }, [lang]);

  return (
    <div ref={rootRef}>
      <WhatsAppFab />
      <SiteHeader onLanding />

      <section className="hero">
        <canvas id="dust"></canvas>
        <div className="wrap">
          <div className="kick">{t("hero.kick")}</div>
          <h1>{t("hero.h1a")}<br /><span className="g">{t("hero.h1b")}</span> {t("hero.h1c")}</h1>
          <p className="sub">{t("hero.sub")}</p>
          <div className="cta-row">
            <Link className="btn" to="/login">{t("hero.cta1")}</Link>
            <Link className="btn ghost" to="/demo">{t("hero.cta2")}</Link>
          </div>
        </div>
      </section>

      <section className="creed"><div className="wrap reveal">
        <div className="creed-kick">{t("creed.kick")}</div>
        <blockquote className="creed-q">
          <span className="l1">{t("creed.l1")}</span>
          <span className="l2">{t("creed.l2a")}<b>{t("creed.l2b")}</b>{t("creed.l2c")}<b>{t("creed.l2d")}</b>{t("creed.l2e")}<b>{t("creed.l2f")}</b>{t("creed.l2g")}</span>
        </blockquote>
        <div className="creed-rule" aria-hidden="true"><i></i><span>&#9670;</span><i></i></div>
      </div></section>

      <section id="edge" className="lp edge"><div className="wrap reveal">
        <div className="kick2">{tx("For boards, CISOs and risk owners")}</div>
        <h2>{tx("What you cannot see is ")}<span className="g">{tx("already public")}</span></h2>
        <p className="lede">{t("lede.edge")}</p>

        <div className="vs">
          <div className="vsc bad"><h4>{tx("How it usually goes")}</h4><ul>
            <li>{tx("An annual test, scoped to what you remembered to list")}</li>
            <li>{tx("A findings spreadsheet with no price attached to anything")}</li>
            <li>{tx("Weeks between the question and the answer")}</li>
            <li>{tx("The board asks what it would actually cost. Nobody knows.")}</li>
            <li className="last">{tx("Compliance deadlines live in somebody&rsquo;s inbox.")}</li></ul></div>
          <div className="vsc good"><h4>{tx("What you get here")}</h4><ul>
            <li>{tx("Your whole internet-facing estate, discovered from public data")}</li>
            <li>{tx("Every exposure modelled in euros, with the method shown")}</li>
            <li>{tx("Minutes, not weeks - and repeatable whenever you want")}</li>
            <li>{tx("A number the board can actually make a decision on")}</li>
            <li className="last">{tx("The regulatory clock, on one slide.")}</li></ul></div>
        </div>

        <h3 className="eh">{t("q3.h")}</h3>
        <div className="tri">
          {[["faq.1q","faq.1a"],["faq.2q","faq.2a"],["faq.3q","faq.3a"]].map(([q, a]) => (
            <div className="tric" key={q}>
              <div className="tt" style={{ fontSize: 19, color: "var(--teal)" }}>{t(q)}</div>
              <p>{t(a)}</p>
            </div>
          ))}
        </div>

        <h3 className="eh">{tx("The clocks are ")}<span className="r">{tx("already running")}</span></h3>
        <p className="lede small">{t("clocks.lede")}</p>
        <div className="clocks">
          <div className="clock"><div className="reg">{tx("NIS2 — Germany")}</div><div className="fine">{tx("€10m / 2% of turnover")}</div>
            <div className="num" id="cd1">&mdash;</div>
            <div className="cap2">{tx("until the BSI registration grace period ends · 31 Jul 2026")}</div></div>
          <div className="clock"><div className="reg">{tx("EU AI Act")}</div><div className="fine">{tx("€35m / 7% of turnover")}</div>
            <div className="num" id="cd2">&mdash;</div>
            <div className="cap2">{tx("until high-risk obligations apply · 2 Aug 2026")}</div></div>
          <div className="clock"><div className="reg">{tx("Cyber Resilience Act")}</div><div className="fine">{tx("€15m / 2.5% of turnover")}</div>
            <div className="num" id="cd3">&mdash;</div>
            <div className="cap2">{tx("until incident & vulnerability reporting · 11 Sep 2026")}</div></div>
        </div>

        <div className="unlock">
          <h3>{tx("Nothing of yours is touched")}</h3>
          <p>{t("touch.body")} <b>{t("touch.bold")}</b></p>
        </div>

        <h3 className="eh">{tx("Where it earns its place")}</h3>
        <div className="plays">
          {[["01",t("earn.01h"),t("earn.01b")],["02",t("earn.02h"),t("earn.02b")],["03",t("earn.03h"),t("earn.03b")],["04",t("earn.04h"),t("earn.04b")],["05",t("earn.05h"),t("earn.05b")],["+",t("earn.06h"),t("earn.06b")]].map(([n, t, b]) => (
            <div className="play" key={n}><span className="pn">{n}</span><b>{t}</b><p>{b}</p></div>
          ))}
        </div>

        <h3 className="eh">{tx("Fair questions")}</h3>
        <div className="tri">
          <div className="tric"><div className="tt" style={{ fontSize: 19, color: "var(--teal)" }}>{tx("“Is this legal?”")}</div>
            <p>{tx("Yes. It uses public sources any researcher could look up, and never interacts with your systems. Nothing is exploited, nothing is logged into.")}</p></div>
          <div className="tric"><div className="tt" style={{ fontSize: 19, color: "var(--teal)" }}>{tx("“How accurate is it?”")}</div>
            <p>{tx("Every finding carries the evidence behind it. Where a source cannot be reached it says “unknown” rather than inventing a weakness - and it asks you to confirm anything it could not resolve.")}</p></div>
          <div className="tric"><div className="tt" style={{ fontSize: 19, color: "var(--teal)" }}>{tx("“What do we have to provide?”")}</div>
            <p>{tx("Your company name. No access, no questionnaire, no NDA to start, and nothing to install. The euro figures are modelled ranges with the assumptions shown.")}</p></div>
        </div>

        <div className="pullq">{tx("The question is not whether something of yours is exposed.")}{" "}
          <span className="g">{tx("It is whether you know what.")}</span></div>
        <div className="cta-row" style={{ justifyContent: "center" }}>
          <Link className="btn" to="/contact">{tx("Request an assessment")}</Link>
        </div>
      </div></section>

      <section id="demo" className="lp"><div className="wrap reveal">
        <h2>{tx("See it ")}<span className="g">{tx("live")}</span></h2>
        <p className="lede">{tx("This is the entire product - texting a bot. The chat below plays the real flow: log in, ask, get four decks.")}</p>
        <div className="demo">
          <div className="phone"><div className="notch"></div><div className="screen">
            <div className="tgh"><span className="bk">‹</span><div className="av">C</div>
              <div><div className="nm">{tx("assessment bot")}</div><div className="st">{tx("bot / online")}</div></div>
              <div className="dots">⋮</div></div>
            <div className="tgbody" id="tgbody"></div>
          </div></div>
          <div className="demoside">
            <h3>{tx("One input. Zero flags.")}</h3>
            <p>{tx("You never type an IP, a network or a certificate. The robot resolves the target's ")}<b>{tx("entire")}</b>{tx(" internet footprint itself, then hunts every exposure, prices it, and writes the decks.")}</p>
            <div className="chips">
              <span className="chip">{tx("zero-trust login")}</span><span className="chip">{tx("auto-discovery")}</span>
              <span className="chip">{tx("Shodan (paid)")}</span><span className="chip">{tx("DeepSeek prose")}</span>
              <span className="chip">{tx("4 decks")}</span>
            </div>
            <p style={{ marginTop: 14, color: "var(--gold)" }}>{tx("The chat loops - watch the four .pptx files land.")}</p>
            <Link className="btn gold" style={{ marginTop: 6 }} to="/login">{tx("Do this in the web app")}</Link>
          </div>
        </div>
      </div></section>

      <section id="map" className="lp"><div className="wrap reveal">
        <div className="maphead">
          <div><h2>{tx("The whole ")}<span className="g">{tx("machine")}</span></h2>
            <p className="lede" style={{ margin: 0 }}>{tx("Hover a box to see its wires. Click it to jump to the details. Or hit play for a guided tour.")}</p></div>
          <button className="tour" id="tour">{tx("Guided tour")}</button>
        </div>
        <div className="legend" style={{ margin: "6px 0 12px" }}>
          <span><b style={{ background: "#10B981" }}></b>{tx("You and bots")}</span>
          <span><b style={{ background: "#00B2A9" }}></b>{tx("Brains")}</span>
          <span><b style={{ background: "#F7C844" }}></b>{tx("Outside services")}</span>
          <span><b style={{ background: "#8b6cff" }}></b>{tx("Safety nets")}</span>
          <span><b style={{ background: "#38e1ff" }}></b>{tx("Observability")}</span>
        </div>
        <div className="mapbox">
          <svg id="svg" viewBox="0 0 1200 790" xmlns="http://www.w3.org/2000/svg">
            <defs><filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="3.2" result="b" />
              <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
            <g id="edges"></g><g id="nodes"></g>
          </svg>
        </div>
        <p className="maphint">{tx("Swipe the map sideways to explore &rarr;")}</p>
        <div className="cap" id="cap"></div>
      </div></section>

      {/* ---- AI CONSENSUS -------------------------------------------------------------------
          EVERY CLAIM IN THIS SECTION IS MEASURED AND LIVES IN THE REPO. Deliberately NOT here:
          any comparison against a named competitor. The product's whole credibility rests on
          "absence of evidence is never a finding" and "no invented identifiers" — putting an
          unmeasured superiority claim on the marketing page would break the exact discipline that
          makes the findings trustworthy, and comparative advertising needs substantiation under
          UWG s.6 / the UCP Directive. The architecture is differentiated enough on facts. */}
      <section id="consensus" className="lp"><div className="wrap reveal">
        <h2>{tx("Four models. Four vendors. ")}<span className="g">{tx("One verdict.")}</span></h2>
        <p className="lede">{tx("Most AI products call one model and print whatever comes back. This one runs a panel \u2014 two models produce, two independent models attack the result, each from a different vendor \u2014 and then lets deterministic code, not the models, make the call.")}</p>

        <div className="cons-grid">
          <div className="cons">
            <span className="cons-k">{tx("No shared failure domain")}</span>
            <p>{tx("A rate limit, an outage or a blind spot is provider-wide. A chain of four models from one vendor is one model wearing four hats. Ours are deepseek, Meta, Google and Moonshot \u2014 when one refuses, the next answers.")}</p>
          </div>
          <div className="cons">
            <span className="cons-k">{tx("The auditor is never the author")}</span>
            <p>{tx("The model that writes a finding is never the model that checks it, and the checker must be from a different vendor. A model reviewing its own work agrees with itself.")}</p>
          </div>
          <div className="cons">
            <span className="cons-k">{tx("Code decides, models advise")}</span>
            <p>{tx("The release gate is deterministic. A model cannot block a good change because it hit a rate limit, and an agreeable model cannot wave a broken one through. When all four dissent against a green gate, the run halts for a human \u2014 because that has twice meant a check was lying.")}</p>
          </div>
          <div className="cons">
            <span className="cons-k">{tx("Nothing is asserted that cannot be evidenced")}</span>
            <p>{tx("Every identifier the model writes is cross-checked against the scan evidence before it reaches a slide. A CVE that is not in the raw findings is stripped, the prose is kept, and the removal is logged.")}</p>
          </div>
          <div className="cons">
            <span className="cons-k">{tx("Cost, measured per run")}</span>
            <p>{tx("Roughly half a cent of inference per assessment, recorded in a ledger that survives redeploys \u2014 not estimated, counted. The panel costs a fraction of the analyst hour it replaces.")}</p>
          </div>
          <div className="cons">
            <span className="cons-k">{tx("Speed comes from the order, not the hardware")}</span>
            <p>{tx("The chain order is set by measurement on the real workload, not by benchmarks \u2014 model rankings invert between a toy prompt and a 13,000-character one. Every call is sized so it can finish inside the time it was given.")}</p>
          </div>
        </div>

        <p className="maphint" style={{ marginTop: 14 }}>{tx("Two produce. Two attack. Code decides. A human is asked when they all disagree.")}</p>
      </div></section>

      <section id="deep" className="lp"><div className="wrap reveal">
        <h2>{tx("Deep ")}<span className="g">{tx("dive")}</span></h2>
        <p className="lede">{tx("Plain English for everyone; under the hood for the engineer. Click a box in the map above to jump here.")}</p>
        <div id="ddwrap"></div>
      </div></section>

      <section id="secure" className="lp"><div className="wrap reveal">
        <h2>{tx("Locked ")}<span className="g">{tx("down")}</span></h2>
        <p className="lede">{tx("Secure-by-design, in plain terms.")}</p>
        <div className="grid2">
          <div className="hood"><div className="h">{tx("Nobody walks in")}</div><ul><li>{tx("A real approved email address + the shared password ")}<b style={{ color: "var(--teal)" }}>{tx("+ a one-time code emailed to that inbox")}</b>{tx(". Guessing the first two isn't enough.")}</li></ul></div>
          <div className="hood"><div className="h">{tx("Secrets never in git")}</div><ul><li>{tx("Keys live only on the server or as encrypted GitHub secrets; ")}<code>gitleaks</code>{tx(" blocks accidental commits.")}</li></ul></div>
          <div className="hood"><div className="h">{tx("Scanned before ship")}</div><ul><li>{tx("Trivy (deps+image), CodeQL SAST, ruff, pytest - every change checked before it reaches the server.")}</li></ul></div>
          <div className="hood"><div className="h">{tx("Never breaks the neighbours")}</div><ul><li>{tx("An isolated container stack; existing services and the firewall are untouched.")}</li></ul></div>
        </div>
      </div></section>

      <div className="foot"><div className="wrap">
        <div style={{ fontSize: 20, fontWeight: 800 }}><span className="chev">❯</span> cybergod<span className="g">.ai</span></div>
        <p>{tx("Cybergod LLC / S4Biz Group - external cyber-risk and EU compliance assessment / one company name in, four boardroom documents out.")}</p>
        <Link className="btn" to="/login">{tx("Open the app")}</Link>
        <div className="footlinks">
          <Link to="/contact">{tx("Kontakt / Contact")}</Link><span>&middot;</span>
          <Link to="/impressum">{tx("Impressum")}</Link><span>&middot;</span>
          <Link to="/privacy">{tx("Datenschutz / Privacy")}</Link>
        </div>
        <p className="foothost">{tx("Betrieben in Deutschland &middot; Server in Frankfurt am Main (FRA1) &middot; Ihre Daten bleiben in der EU.")}</p>
        <div className="g" style={{ marginTop: 18 }}>» » » » »</div>
      </div></div>

      <TabBar tabs={TABS} active={tab} onGo={go} />
    </div>
  );
}
