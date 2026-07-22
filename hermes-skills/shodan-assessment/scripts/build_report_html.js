#!/usr/bin/env node
/**
 * build_report_html.js — the 5th deliverable: ONE self-contained animated HTML report per company,
 * combining the three engine artifacts (findings.json + cbiq.json + geopol.json) into a single
 * dark, scroll-driven "scrollytelling" page in the Colt visual language.
 *
 *   node build_report_html.js findings.json cbiq.json geopol.json  <Company>_Report.html
 *
 * Design goals (match skon.de_GEOPOL_Animated.html):
 *   - dark Colt palette, Inter / Unbounded / JetBrains Mono, teal on near-black
 *   - a three.js particle-network hero (CDN, with a canvas fallback so it never renders blank)
 *   - scene-by-scene scroll reveals, count-up numbers, an animated loss-exceedance curve,
 *     severity bars, per-actor threat cards, a kill-chain timeline
 *   - 100% self-contained: no data fetched at view time, all values baked in at build.
 *
 * Defensive by contract: every field access is guarded. A missing key degrades to a sensible
 * default; the builder must NEVER throw on a thin estate (the bibeltv.de 5-host case) or a
 * findings-only run where enrichment was skipped.
 */
"use strict";
const fs = require("fs");

const [, , FIND, CBIQ, GEO, OUT] = process.argv;
if (!FIND || !OUT) {
  console.error("usage: build_report_html.js findings.json cbiq.json geopol.json out.html");
  process.exit(2);
}
const readJSON = (p) => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return {}; } };
const F = readJSON(FIND), C = CBIQ ? readJSON(CBIQ) : {}, G = GEO ? readJSON(GEO) : {};

const DE = String(process.env.DECK_LANG || "en").toLowerCase().startsWith("de");
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const num = (v, d = 0) => (typeof v === "number" && isFinite(v)) ? v : d;

// ---- pull the fields we need, all guarded ----
const tgt = F.target || {};
const company = tgt.company || C.customer || G.customer || "Target";
const scope = tgt.scope || "";
const sum = F.summary || {};
const sev = { critical: num(sum.critical), high: num(sum.high), medium: num(sum.medium), low: num(sum.low) };
const nFind = (F.findings || []).length;
const findings = (F.findings || []).slice();
const hostCount = num(sum.hosts || (tgt.inventory || {}).hosts || 0);
const asnCount = num(sum.asns || (tgt.inventory || {}).asns || 0);

const cur = (C.currency && C.currency.symbol) || "€";
const port = C.portfolio || {};
const aleTxt = port.aleRange || port.ale || "—";
const pmlTxt = port.pmlRange || port.pml || "—";
const rosiTxt = port.rosi || (C.remediationSuite ? "" : "") || "—";
const cbiqFindings = (C.findings || []).slice();
const lec = C.lossExceedance || {};

const verdict = G.verdict || "";
const sector = G.sectorContext || "";
const actors = (G.actors || []).slice();
const killChain = G.killChain || {};
const exposure = (G.exposureMap || []).slice();

const T = DE ? {
  kicker: "Cyber-Lagebild · vertraulich", intro: "Ein Ziel. Drei Fragen.",
  s_exposed: "Was ist exponiert", s_cost: "Was es kostet", s_who: "Wer angreift",
  crit: "KRITISCH", high: "HOCH", med: "MITTEL", low: "NIEDRIG",
  hosts: "Hosts", asns: "ASNs", findings: "Feststellungen",
  ale: "Erwarteter Jahresverlust", pml: "Plausibler Grossschaden", rosi: "ROSI",
  who_lead: "Wer würde angreifen — und warum", killchain: "Angriffskette",
  colt: "Warum Colt", close: "Ein Eingang. Vier Dokumente. Diese Seite.",
  scrolldown: "scrollen", exposedLead: "Die internetseitige Angriffsfläche",
} : {
  kicker: "Cyber posture · confidential", intro: "One target. Three questions.",
  s_exposed: "What is exposed", s_cost: "What it costs", s_who: "Who would attack",
  crit: "CRITICAL", high: "HIGH", med: "MEDIUM", low: "LOW",
  hosts: "hosts", asns: "ASNs", findings: "findings",
  ale: "Expected annual loss", pml: "Plausible maximum loss", rosi: "ROSI",
  who_lead: "Who would attack — and why", killchain: "Kill chain",
  colt: "Why Colt", close: "One input. Four documents. This page.",
  scrolldown: "scroll", exposedLead: "The internet-facing attack surface",
};

// ---------- fragment builders ----------
const sevColor = { CRITICAL: "var(--red)", HIGH: "var(--orange)", MEDIUM: "var(--amber)", LOW: "var(--dim)" };

function findingCard(f, i) {
  const s = String(f.sev || "").toUpperCase();
  const col = sevColor[s] || "var(--dim)";
  const ev = (f.evidence || []).slice(0, 3).map((e) => `<code>${esc(e)}</code>`).join("");
  const why = Array.isArray(f.why) ? f.why.join(" ") : (f.why || "");
  const rem = (f.rem || []).slice(0, 1).map((r) =>
    typeof r === "object" ? `${esc(r.title || r.tag || "")}` : esc(r)).join("");
  return `<article class="fcard reveal" style="--c:${col}">
    <div class="fhead"><span class="badge" style="background:${col}">${esc(s)}</span>
      <span class="fid">${esc(f.id || ("F" + (i + 1)))}</span></div>
    <h3>${esc(f.title || "Finding")}</h3>
    <p class="what">${esc(f.what || "")}</p>
    ${ev ? `<div class="ev">${ev}</div>` : ""}
    ${why ? `<p class="why">${esc(why)}</p>` : ""}
    ${rem ? `<div class="rem"><span>COLT</span>${rem}</div>` : ""}
  </article>`;
}

function actorCard(a) {
  const band = esc(a.band || a.tier || "");
  const pills = (a.pills || []).slice(0, 4).map((p) => `<span class="pill">${esc(p)}</span>`).join("");
  const lk = num(a.likelihood12mo);
  return `<article class="acard reveal">
    <div class="aeye">${esc(a.eyebrow || band)}</div>
    <h3>${esc(a.title || a.sponsor || "Threat actor")}</h3>
    <div class="pills">${pills}</div>
    <p>${esc(a.what || "")}</p>
    ${lk ? `<div class="lk"><div class="lkbar"><i style="width:${Math.min(100, lk)}%"></i></div>
      <span>${lk}% · 12mo</span></div>` : ""}
  </article>`;
}

const findingsHTML = findings.length
  ? findings.map(findingCard).join("")
  : `<p class="empty">No internet-exposed findings were raised — a small, well-run estate is itself a result.</p>`;

const actorsHTML = actors.length ? actors.map(actorCard).join("") : "";

const kcSteps = (killChain.steps || killChain.stages || []);
const killHTML = kcSteps.length ? `<ol class="kc">` + kcSteps.map((s, i) =>
  `<li class="reveal"><span class="kcn">${i + 1}</span><div><b>${esc(s.title || s.phase || s.name || ("Step " + (i + 1)))}</b>
   <p>${esc(s.what || s.detail || s.desc || (typeof s === "string" ? s : ""))}</p></div></li>`).join("") + `</ol>` : "";

const exposureHTML = exposure.length ? `<div class="expo">` + exposure.map((e) =>
  `<div class="exrow reveal"><b>${esc(e.driver || "")}</b><span>${esc(e.attracts || "")}</span>
   <p>${esc(e.why || "")}</p></div>`).join("") + `</div>` : "";

const cbiqRows = cbiqFindings.slice(0, 8).map((f) =>
  `<tr class="reveal"><td>${esc(f.label || f.asset || f.id || "")}</td>
   <td class="mono">${esc(f.pmlRange || f.aleAfter || "")}</td>
   <td>${esc((f.coltControl || "") + "")}</td></tr>`).join("");

// loss-exceedance points -> normalized polyline for the animated chart
const lecPts = (lec.points || lec.curve || []).map((p) => Array.isArray(p) ? p : [p.x, p.y]).filter(Boolean);

// ---------- the page ----------
const html = `<!doctype html><html lang="${DE ? "de" : "en"}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(company)} — Colt cyber report</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=Unbounded:wght@600;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
:root{--bg:#05080E;--bg2:#0A111C;--panel:#0E1827;--line:#16243B;--ink:#E9F1FA;--dim:#8DA0BC;--faint:#54657F;
--teal:#00D7BD;--teal2:#0C544E;--tealg:#19F0D6;--green:#26D98A;--amber:#FFC33C;--red:#FF3B57;--violet:#9E86FF;--orange:#FF7A33;--mint:#5FFFC2}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Inter",system-ui,sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden;
background-image:radial-gradient(1200px 700px at 82% -8%,rgba(0,215,189,.10),transparent 60%),radial-gradient(900px 600px at -8% 30%,rgba(158,134,255,.05),transparent 60%)}
#bg{position:fixed;inset:0;z-index:0;opacity:.55}
main{position:relative;z-index:1}
section{max-width:1120px;margin:0 auto;padding:14vh 24px;min-height:70vh}
.eyebrow{font-family:"JetBrains Mono",monospace;font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--teal)}
h1{font-family:"Unbounded",sans-serif;font-weight:800;font-size:clamp(34px,6vw,68px);line-height:1.02;margin:.25em 0 .3em}
h2{font-family:"Unbounded",sans-serif;font-weight:600;font-size:clamp(24px,3.4vw,40px);margin:.2em 0 .5em}
.hl{color:var(--teal)}.amberhl{color:var(--amber)}.redhl{color:var(--red)}
.sub{color:var(--dim);font-size:clamp(15px,1.5vw,19px);max-width:60ch;line-height:1.6}
.wm{font-family:"Unbounded";font-weight:800;color:var(--teal)}
.brandbar{display:flex;align-items:center;gap:10px;font-weight:800}
.chev{color:var(--teal)}
.hero{min-height:96vh;display:flex;flex-direction:column;justify-content:center}
.scroll{position:absolute;bottom:34px;left:50%;transform:translateX(-50%);color:var(--faint);font-family:"JetBrains Mono";font-size:11px;letter-spacing:.2em}
.scroll i{display:block;width:1px;height:34px;margin:8px auto 0;background:linear-gradient(var(--teal),transparent);animation:drop 1.8s infinite}
@keyframes drop{0%{opacity:0;transform:scaleY(.2)}40%{opacity:1}100%{opacity:0;transform:translateY(14px) scaleY(.6)}}
.reveal{opacity:0;transform:translateY(22px);transition:opacity .7s cubic-bezier(.2,.7,.2,1),transform .7s cubic-bezier(.2,.7,.2,1)}
.reveal.in{opacity:1;transform:none}
.stats{display:flex;flex-wrap:wrap;gap:16px;margin-top:26px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 22px;min-width:150px}
.stat .n{font-family:"Unbounded";font-weight:800;font-size:40px;line-height:1}
.stat .l{color:var(--dim);font-size:12px;letter-spacing:.12em;text-transform:uppercase;margin-top:6px}
.sevgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:26px}
.sevcard{border:1px solid var(--line);border-radius:14px;padding:18px;background:var(--panel)}
.sevcard .n{font-family:"Unbounded";font-weight:800;font-size:34px}
.sevcard .bar{height:6px;border-radius:6px;margin-top:12px;background:#0c1626;overflow:hidden}
.sevcard .bar i{display:block;height:100%;width:0;transition:width 1.1s cubic-bezier(.2,.7,.2,1)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-top:26px}
.fcard{border:1px solid var(--line);border-left:3px solid var(--c);border-radius:14px;padding:18px;background:linear-gradient(180deg,var(--panel),#0b1320)}
.fhead{display:flex;justify-content:space-between;align-items:center}
.badge{color:#04121a;font-weight:800;font-size:11px;letter-spacing:.08em;padding:3px 9px;border-radius:999px}
.fid{font-family:"JetBrains Mono";color:var(--faint);font-size:12px}
.fcard h3{font-size:17px;margin:12px 0 8px}.fcard .what{color:var(--dim);font-size:14px;margin:0 0 10px}
.ev{display:flex;flex-direction:column;gap:5px;margin:8px 0}
code{font-family:"JetBrains Mono";font-size:11.5px;color:var(--tealg);background:#08131b;border:1px solid var(--line);border-radius:7px;padding:5px 8px;word-break:break-all}
.why{color:var(--faint);font-size:13px;margin:8px 0 0}
.rem{margin-top:12px;font-size:13px;color:var(--ink)}.rem span{color:var(--teal);font-weight:800;font-family:"JetBrains Mono";font-size:11px;margin-right:8px}
.money{display:flex;flex-wrap:wrap;gap:16px;margin-top:26px}
.mcard{flex:1;min-width:210px;border:1px solid var(--line);border-radius:16px;padding:24px;background:radial-gradient(120% 120% at 0 0,rgba(0,215,189,.08),transparent 60%),var(--panel)}
.mcard .n{font-family:"Unbounded";font-weight:800;font-size:clamp(26px,3vw,40px);color:var(--teal)}
.mcard .l{color:var(--dim);font-size:12px;letter-spacing:.12em;text-transform:uppercase;margin-top:8px}
.chartwrap{margin-top:26px;border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:18px}
table{width:100%;border-collapse:collapse;margin-top:22px;font-size:14px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line)}th{color:var(--faint);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
.mono{font-family:"JetBrains Mono";color:var(--tealg)}
.pills{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.pill{font-size:11px;color:var(--dim);border:1px solid var(--line);border-radius:999px;padding:3px 9px}
.acard{border:1px solid var(--line);border-radius:14px;padding:18px;background:var(--panel)}
.aeye{font-family:"JetBrains Mono";font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--violet)}
.acard h3{margin:6px 0 2px;font-size:18px}.acard p{color:var(--dim);font-size:14px}
.lk{display:flex;align-items:center;gap:10px;margin-top:10px}.lk span{font-family:"JetBrains Mono";font-size:11px;color:var(--faint)}
.lkbar{flex:1;height:6px;background:#0c1626;border-radius:6px;overflow:hidden}.lkbar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--violet),var(--red));transition:width 1.1s}
.kc{list-style:none;padding:0;margin:26px 0 0;border-left:1px solid var(--line)}
.kc li{display:flex;gap:16px;padding:0 0 22px 22px;position:relative}
.kcn{position:absolute;left:-14px;width:28px;height:28px;border-radius:50%;background:var(--bg);border:1px solid var(--teal);color:var(--teal);display:grid;place-items:center;font-family:"JetBrains Mono";font-size:12px}
.kc b{display:block;margin-bottom:3px}.kc p{color:var(--dim);font-size:14px;margin:0}
.expo{margin-top:24px;display:flex;flex-direction:column;gap:10px}
.exrow{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:var(--panel)}
.exrow b{color:var(--teal)}.exrow span{color:var(--dim);margin-left:10px;font-size:13px}.exrow p{margin:6px 0 0;color:var(--faint);font-size:13px}
.empty{color:var(--dim);border:1px dashed var(--line);border-radius:14px;padding:24px;margin-top:20px}
.close{text-align:center}.close .big{font-family:"Unbounded";font-weight:800;font-size:clamp(26px,4vw,52px)}
.foot{border-top:1px solid var(--line);color:var(--faint);font-size:12px;text-align:center;padding:26px;font-family:"JetBrains Mono"}
.tag{display:inline-block;font-family:"JetBrains Mono";font-size:11px;color:var(--faint);border:1px solid var(--line);border-radius:999px;padding:4px 12px;margin-bottom:10px;letter-spacing:.12em}
@media(max-width:640px){.sevgrid{grid-template-columns:repeat(2,1fr)}section{padding:10vh 18px}}
</style></head>
<body>
<canvas id="bg"></canvas>
<main>
  <section class="hero">
    <div class="brandbar"><span class="chev wm">❯</span><span class="wm">colt</span>
      <span style="color:var(--faint);font-weight:500;margin-left:8px">/ S4Biz</span></div>
    <div class="eyebrow" style="margin-top:28px">${esc(T.kicker)}</div>
    <h1>${esc(company)}<br><span class="hl">${esc(T.intro)}</span></h1>
    <p class="sub">${esc(scope ? scope : (DE ? "Passives OSINT-Lagebild der internetseitigen Angriffsfläche." : "A passive OSINT picture of the internet-facing attack surface."))}</p>
    <div class="stats">
      <div class="stat"><div class="n" data-n="${hostCount}">0</div><div class="l">${esc(T.hosts)}</div></div>
      <div class="stat"><div class="n" data-n="${asnCount}">0</div><div class="l">${esc(T.asns)}</div></div>
      <div class="stat"><div class="n" data-n="${nFind}">0</div><div class="l">${esc(T.findings)}</div></div>
    </div>
    <div class="scroll">${esc(T.scrolldown)}<i></i></div>
  </section>

  <section>
    <div class="eyebrow">01</div><h2>${esc(T.s_exposed)}</h2>
    <p class="sub">${esc(T.exposedLead)}.</p>
    <div class="sevgrid">
      <div class="sevcard reveal"><div class="n" data-n="${sev.critical}" style="color:var(--red)">0</div>
        <div class="l">${esc(T.crit)}</div><div class="bar"><i style="background:var(--red)" data-w="${sev.critical ? 100 : 4}"></i></div></div>
      <div class="sevcard reveal"><div class="n" data-n="${sev.high}" style="color:var(--orange)">0</div>
        <div class="l">${esc(T.high)}</div><div class="bar"><i style="background:var(--orange)" data-w="${Math.min(100, sev.high * 18) || 4}"></i></div></div>
      <div class="sevcard reveal"><div class="n" data-n="${sev.medium}" style="color:var(--amber)">0</div>
        <div class="l">${esc(T.med)}</div><div class="bar"><i style="background:var(--amber)" data-w="${Math.min(100, sev.medium * 14) || 4}"></i></div></div>
      <div class="sevcard reveal"><div class="n" data-n="${sev.low}" style="color:var(--dim)">0</div>
        <div class="l">${esc(T.low)}</div><div class="bar"><i style="background:var(--dim)" data-w="${Math.min(100, sev.low * 10) || 4}"></i></div></div>
    </div>
    <div class="grid">${findingsHTML}</div>
  </section>

  ${(aleTxt !== "—" || cbiqFindings.length) ? `<section>
    <div class="eyebrow">02</div><h2>${esc(T.s_cost)}</h2>
    <p class="sub">${DE ? "In Euro, mit gezeigter Rechnung — nicht behauptet." : "In euros, with the maths shown — not asserted."}</p>
    <div class="money">
      <div class="mcard reveal"><div class="n">${esc(aleTxt)}</div><div class="l">${esc(T.ale)}</div></div>
      <div class="mcard reveal"><div class="n">${esc(pmlTxt)}</div><div class="l">${esc(T.pml)}</div></div>
      <div class="mcard reveal"><div class="n">${esc(rosiTxt)}</div><div class="l">${esc(T.rosi)}</div></div>
    </div>
    ${lecPts.length ? `<div class="chartwrap"><canvas id="lec" height="220"></canvas></div>` : ""}
    ${cbiqRows ? `<table><thead><tr><th>${DE ? "Feststellung" : "Finding"}</th><th>PML</th><th>Colt</th></tr></thead><tbody>${cbiqRows}</tbody></table>` : ""}
  </section>` : ""}

  ${(verdict || actors.length) ? `<section>
    <div class="eyebrow">03</div><h2>${esc(T.s_who)}</h2>
    ${verdict ? `<p class="sub">${esc(verdict)}</p>` : ""}
    ${sector ? `<p class="sub" style="color:var(--faint);margin-top:10px">${esc(sector)}</p>` : ""}
    ${exposureHTML}
    ${actorsHTML ? `<div class="grid">${actorsHTML}</div>` : ""}
    ${killHTML ? `<h2 style="margin-top:8vh">${esc(T.killchain)}</h2>${killHTML}` : ""}
  </section>` : ""}

  <section class="close">
    <span class="tag">${esc(T.colt)}</span>
    <p class="big">${DE ? "Bolt-on ist eine Steuer, die man ewig zahlt." : "Bolt-on is a tax you pay forever."}</p>
    <p class="sub" style="margin:18px auto 0">${DE
      ? "SASE/ZTNA entfernt die exponierte Kante · Managed WAF killt die Wordlists · IP Guardian absorbiert die Flut."
      : "SASE/ZTNA removes the exposed edge · Managed WAF kills the wordlists · IP Guardian absorbs the flood."}</p>
  </section>
  <div class="foot">❯ colt · S4Biz · ${esc(company)} · ${esc((F.target||{}).date || new Date().toISOString().slice(0,10))} · internal — not for external distribution</div>
</main>
<script>
// ---- scroll reveals ----
const io=new IntersectionObserver((es)=>{es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{threshold:.15});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
// ---- count-ups + bars on first view ----
function countUp(el){const t=+el.dataset.n||0;const d=900;const s=performance.now();
  (function tick(now){const p=Math.min(1,(now-s)/d);el.textContent=Math.round(t*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(tick)})(s)}
const io2=new IntersectionObserver((es)=>{es.forEach(e=>{if(e.isIntersecting){
  e.target.querySelectorAll('[data-n]').forEach(countUp);
  e.target.querySelectorAll('[data-w]').forEach(i=>i.style.width=i.dataset.w+'%');
  e.target.querySelectorAll('.lkbar i').forEach(i=>{});io2.unobserve(e.target)}})},{threshold:.3});
document.querySelectorAll('section').forEach(s=>io2.observe(s));
document.querySelectorAll('.lk').forEach(l=>{const b=l.querySelector('i');const w=(l.querySelector('span')||{}).textContent||'';});
document.querySelectorAll('.acard').forEach(a=>{const bar=a.querySelector('.lkbar i');if(bar){const m=(a.textContent.match(/(\\d+)% · 12mo/)||[])[1];if(m)new IntersectionObserver((e,o)=>{if(e[0].isIntersecting){bar.style.width=Math.min(100,+m)+'%';o.disconnect()}},{threshold:.4}).observe(a)}});
// ---- loss-exceedance curve ----
const LEC=${JSON.stringify(lecPts)};
(function(){const c=document.getElementById('lec');if(!c||!LEC.length)return;const ctx=c.getContext('2d');
  function draw(prog){const w=c.width=c.clientWidth,h=c.height;ctx.clearRect(0,0,w,h);
    const xs=LEC.map(p=>p[0]),ys=LEC.map(p=>p[1]);const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
    const X=x=>20+(w-40)*((x-xmin)/((xmax-xmin)||1)),Y=y=>h-24-(h-44)*((y-ymin)/((ymax-ymin)||1));
    ctx.strokeStyle='#16243B';ctx.lineWidth=1;for(let g=0;g<=4;g++){const yy=24+g*(h-48)/4;ctx.beginPath();ctx.moveTo(20,yy);ctx.lineTo(w-20,yy);ctx.stroke();}
    const n=Math.max(2,Math.floor(LEC.length*prog));ctx.beginPath();ctx.moveTo(X(LEC[0][0]),Y(LEC[0][1]));
    for(let i=1;i<n;i++)ctx.lineTo(X(LEC[i][0]),Y(LEC[i][1]));
    ctx.strokeStyle='#00D7BD';ctx.lineWidth=2.5;ctx.shadowColor='#00D7BD';ctx.shadowBlur=12;ctx.stroke();ctx.shadowBlur=0;
    ctx.lineTo(X(LEC[n-1][0]),h-24);ctx.lineTo(X(LEC[0][0]),h-24);ctx.closePath();
    const g=ctx.createLinearGradient(0,0,0,h);g.addColorStop(0,'rgba(0,215,189,.18)');g.addColorStop(1,'rgba(0,215,189,0)');ctx.fillStyle=g;ctx.fill();}
  let p=0;new IntersectionObserver((e,o)=>{if(e[0].isIntersecting){(function a(){p=Math.min(1,p+.03);draw(p);if(p<1)requestAnimationFrame(a)})();o.disconnect()}},{threshold:.3}).observe(c);
  addEventListener('resize',()=>draw(1));})();
// ---- three.js particle-network hero, with a canvas fallback ----
(function(){const canvas=document.getElementById('bg');
  function fallback(){const ctx=canvas.getContext('2d');let W,H,pts;
    function rs(){W=canvas.width=innerWidth;H=canvas.height=innerHeight;pts=Array.from({length:Math.min(90,(W*H)/22000|0)},()=>({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3}))}
    rs();addEventListener('resize',rs);(function loop(){ctx.clearRect(0,0,W,H);
      for(const p of pts){p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1}
      for(let i=0;i<pts.length;i++){for(let j=i+1;j<pts.length;j++){const dx=pts[i].x-pts[j].x,dy=pts[i].y-pts[j].y,d=Math.hypot(dx,dy);
        if(d<130){ctx.globalAlpha=(1-d/130)*.5;ctx.strokeStyle='#00D7BD';ctx.beginPath();ctx.moveTo(pts[i].x,pts[i].y);ctx.lineTo(pts[j].x,pts[j].y);ctx.stroke()}}}
      ctx.globalAlpha=.9;ctx.fillStyle='#19F0D6';for(const p of pts){ctx.beginPath();ctx.arc(p.x,p.y,1.4,0,7);ctx.fill()}
      requestAnimationFrame(loop)})()}
  const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  s.onload=function(){try{three()}catch(e){fallback()}};s.onerror=fallback;document.head.appendChild(s);
  function three(){const THREE=window.THREE;const sc=new THREE.Scene();const cam=new THREE.PerspectiveCamera(60,innerWidth/innerHeight,.1,1000);cam.position.z=60;
    const rnd=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true});rnd.setSize(innerWidth,innerHeight);rnd.setPixelRatio(Math.min(2,devicePixelRatio));
    const N=180,geo=new THREE.BufferGeometry(),pos=new Float32Array(N*3);for(let i=0;i<N*3;i++)pos[i]=(Math.random()-.5)*120;
    geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
    const mat=new THREE.PointsMaterial({color:0x19F0D6,size:.7,transparent:true,opacity:.9});const pts=new THREE.Points(geo,mat);sc.add(pts);
    const lg=new THREE.BufferGeometry();const lp=[];for(let i=0;i<N;i++)for(let j=i+1;j<N;j++){const a=i*3,b=j*3;const dx=pos[a]-pos[b],dy=pos[a+1]-pos[b+1],dz=pos[a+2]-pos[b+2];if(dx*dx+dy*dy+dz*dz<220){lp.push(pos[a],pos[a+1],pos[a+2],pos[b],pos[b+1],pos[b+2])}}
    lg.setAttribute('position',new THREE.BufferAttribute(new Float32Array(lp),3));
    const lines=new THREE.LineSegments(lg,new THREE.LineBasicMaterial({color:0x00D7BD,transparent:true,opacity:.22}));sc.add(lines);
    addEventListener('resize',()=>{cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();rnd.setSize(innerWidth,innerHeight)});
    (function a(t){pts.rotation.y=lines.rotation.y=t*.00004;pts.rotation.x=lines.rotation.x=Math.sin(t*.0002)*.1;rnd.render(sc,cam);requestAnimationFrame(a)})(0)}
})();
</script>
</body></html>`;

fs.writeFileSync(OUT, html);
console.log("[ok] " + OUT + "  (" + (Buffer.byteLength(html) / 1024).toFixed(0) + " KB)");
