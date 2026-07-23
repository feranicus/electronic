#!/usr/bin/env node
/**
 * build_compliance_html.js — self-contained animated HTML report for the Compliance module.
 *
 *   node build_compliance_html.js compliance.json out.html
 *
 * One dark, scroll-driven, Colt-styled page combining NIS2 + CRA + EU AI Act + the roadmap: a hero
 * with the three regime status chips, the scoping assumptions, a section per regime (applicability,
 * obligations, priority gaps, penalty exposure, how Colt helps), a merged deadline timeline and the
 * phased roadmap. No external dependencies — inline CSS + a little vanilla JS (scroll-reveal + count
 * up). Defensive by contract: renders on the deterministic fallback (no gaps, "requires confirmation")
 * with no undefined/NaN leaking. DECK_LANG=de switches the chrome to Hoch-Deutsch.
 */
const fs = require("fs");
const [, , jsonPath, outPath] = process.argv;
if (!jsonPath || !outPath) { console.error("usage: build_compliance_html.js compliance.json out.html"); process.exit(2); }
const D = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
const LANG = (process.env.DECK_LANG || D.lang || "en").toLowerCase().startsWith("de") ? "de" : "en";
const company = D.company || "Target";
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const T = {
  eyebrow: { en: "EU DIGITAL & CYBER COMPLIANCE", de: "EU-DIGITAL- & CYBER-COMPLIANCE" },
  applies: { en: "Applies", de: "Betroffen" }, notApplies: { en: "Out of scope", de: "Nicht betroffen" },
  unclear: { en: "To confirm", de: "Zu bestätigen" },
  assumptions: { en: "Scoping assumptions", de: "Annahmen zum Anwendungsbereich" },
  confirmNote: { en: "Inferred from the company name — confirm via the clarification questions to finalise scope.", de: "Aus dem Firmennamen abgeleitet — bitte über die Rückfragen bestätigen." },
  obligations: { en: "Core obligations", de: "Kernpflichten" }, gaps: { en: "Priority gaps", de: "Prioritäre Lücken" },
  noGaps: { en: "No priority gaps recorded at the assumed scope.", de: "Keine prioritären Lücken bei angenommenem Anwendungsbereich." },
  penalty: { en: "Penalty exposure", de: "Bußgeld-Exposition" }, colt: { en: "How Colt helps", de: "Wie Colt unterstützt" },
  timeline: { en: "Deadline calendar", de: "Fristenkalender" }, roadmap: { en: "Remediation roadmap", de: "Umsetzungs-Fahrplan" },
  sector: { en: "Sector", de: "Sektor" }, size: { en: "Size", de: "Größe" },
  digital: { en: "Sells digital products", de: "Digitale Produkte" }, ai: { en: "Builds / deploys AI", de: "Baut / nutzt KI" },
  countries: { en: "Countries", de: "Länder" }, yes: { en: "Yes", de: "Ja" }, no: { en: "No", de: "Nein" }, unknown: { en: "unknown", de: "unklar" },
  sources: { en: "Source: EU primary legal texts (NIS2 Dir. 2022/2555, CRA Reg. 2024/2847, AI Act Reg. 2024/1689). Educational summary, not legal advice.", de: "Quelle: EU-Primärrecht (NIS2 RL 2022/2555, CRA VO 2024/2847, KI-VO 2024/1689). Bildungszusammenfassung, keine Rechtsberatung." },
};
const L = (k) => (T[k] || {})[LANG] || (T[k] || {}).en || k;
const REG = { nis2: "NIS2", cra: "Cyber Resilience Act", aiact: "EU AI Act" };
const yn = (v) => v === true ? L("yes") : v === false ? L("no") : L("unknown");

function statusClass(applies) { return applies === true ? "on" : applies === false ? "off" : "maybe"; }
function statusText(applies) { return applies === true ? L("applies") : applies === false ? L("notApplies") : L("unclear"); }
function fmtDate(d) { try { const dt = new Date(d + "T00:00:00Z"); if (isNaN(dt)) return d; return dt.toLocaleDateString(LANG === "de" ? "de-DE" : "en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }); } catch { return d; } }

const a = D.assumptions || {}, regs = D.regimes || {}, rm = D.roadmap || {};

function regimeSection(k) {
  const r = regs[k] || {};
  const gaps = (r.gaps || []).filter((g) => g && (g.title || g.detail));
  const obl = (r.obligations || []).slice(0, 6);
  const colt = (r.colt || []).slice(0, 4);
  const p = r.penalty || {};
  return `
  <section class="reg reveal" id="${k}">
    <div class="reg-head">
      <span class="chip ${statusClass(r.applies)}">${esc(statusText(r.applies))}</span>
      <h2>${esc(REG[k])}</h2>
      <div class="cls">${esc(r.classification || L("unclear"))}</div>
    </div>
    <p class="rationale">${esc(r.rationale || "")}</p>
    <div class="grid2">
      <div class="card">
        <h3>${esc(L("obligations"))}</h3>
        <ul class="obl">${obl.map((o) => `<li><b>${esc(o.ref || "")}</b> — ${esc(o.title || "")}<span>${esc(o.detail || "")}</span></li>`).join("")}</ul>
      </div>
      <div class="card">
        <h3>${esc(L("gaps"))}</h3>
        ${gaps.length ? `<ul class="gaps">${gaps.slice(0, 5).map((g) => `<li class="sev-${esc((g.sev || "low").toLowerCase())}"><span class="gsev">${esc((g.sev || "").toUpperCase())}</span><div><b>${esc(g.title || "")}</b>${g.article ? ` <em>(${esc(g.article)})</em>` : ""}<span>${esc(g.detail || "")}</span></div></li>`).join("")}</ul>` : `<p class="muted">${esc(L("noGaps"))}</p>`}
        <div class="pen">
          <h4>${esc(L("penalty"))}</h4>
          <div class="penrow"><b>${esc(p.essential || "—")}</b></div>
          <div class="penrow sub">${esc(p.important || "")}</div>
          ${p.note ? `<div class="pennote">${esc(p.note)}</div>` : ""}
        </div>
      </div>
    </div>
    ${colt.length ? `<div class="colt"><h3>${esc(L("colt"))}</h3><div class="coltgrid">${colt.map((c) => `<div class="coltcard"><b>${esc(c.title || "")}</b><span>${esc(c.body || "")}</span></div>`).join("")}</div></div>` : ""}
  </section>`;
}

// merged deadline calendar
const allDl = [];
["nis2", "cra", "aiact"].forEach((k) => (regs[k] || {}).deadlines?.forEach((d) => allDl.push({ ...d, regime: REG[k] })));
allDl.sort((x, y) => String(x.date).localeCompare(String(y.date)));

const chips = ["nis2", "cra", "aiact"].map((k) => {
  const r = regs[k] || {};
  return `<a href="#${k}" class="hchip ${statusClass(r.applies)}"><span>${esc(REG[k])}</span><b>${esc(statusText(r.applies))}</b></a>`;
}).join("");

const html = `<!DOCTYPE html>
<html lang="${LANG}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(company)} — EU Compliance</title>
<style>
:root{--teal:#00D7BD;--tealD:#0C544E;--ink:#eaf1fb;--mut:#9fb2cc;--bg:#070d15;--card:#0e1a2c;--line:#1c3050;--crit:#F20C36;--high:#FF7900;--med:#FFC33C;--gold:#F7C844}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.55}
.wrap{max-width:1040px;margin:0 auto;padding:0 22px}
a{color:var(--teal);text-decoration:none}
.hero{padding:70px 0 40px;border-bottom:1px solid var(--line);background:radial-gradient(1200px 400px at 20% -10%,rgba(0,215,189,.14),transparent)}
.eyebrow{color:var(--teal);font-weight:800;letter-spacing:3px;font-size:12px}
.hero h1{font-size:clamp(30px,6vw,58px);margin:.2em 0 .1em;font-weight:900;font-family:"Arial Black",Arial}
.hero .sub{color:var(--mut);font-size:18px}
.hchips{display:flex;flex-wrap:wrap;gap:12px;margin-top:26px}
.hchip{display:flex;flex-direction:column;gap:2px;padding:12px 16px;border:1px solid var(--line);border-radius:12px;background:var(--card);min-width:180px}
.hchip span{color:var(--mut);font-size:12px;letter-spacing:1px}.hchip b{font-size:15px}
.hchip.on{border-color:var(--crit)}.hchip.on b{color:#ff6b83}
.hchip.off b{color:var(--mut)}.hchip.maybe{border-color:var(--med)}.hchip.maybe b{color:var(--med)}
.assume{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0 6px}
.assume .a{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-size:13px}
.assume .a b{color:var(--teal)}
.note{color:var(--mut);font-size:13px;font-style:italic;margin:8px 0 0}
section{padding:44px 0;border-bottom:1px solid var(--line)}
.reg-head{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.reg-head h2{margin:0;font-size:28px;font-weight:900}
.cls{margin-left:auto;color:var(--teal);font-weight:700}
.chip{padding:5px 12px;border-radius:999px;font-size:12px;font-weight:800;letter-spacing:1px}
.chip.on{background:rgba(242,12,54,.16);color:#ff6b83;border:1px solid var(--crit)}
.chip.off{background:rgba(120,140,160,.14);color:var(--mut);border:1px solid var(--line)}
.chip.maybe{background:rgba(255,195,60,.14);color:var(--med);border:1px solid var(--med)}
.rationale{color:var(--ink);font-size:16px;margin:16px 0 22px;max-width:900px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}
.card h3{margin:0 0 12px;font-size:14px;letter-spacing:2px;color:var(--teal);text-transform:uppercase}
ul.obl,ul.gaps{list-style:none;margin:0;padding:0}
ul.obl li{padding:8px 0;border-top:1px solid var(--line);font-size:14px}ul.obl li:first-child{border-top:0}
ul.obl li b{color:var(--teal)}ul.obl li span{display:block;color:var(--mut);font-size:12.5px;margin-top:2px}
ul.gaps li{display:flex;gap:10px;padding:10px 0;border-top:1px solid var(--line)}ul.gaps li:first-child{border-top:0}
.gsev{font-size:10px;font-weight:800;padding:3px 7px;border-radius:6px;height:fit-content;letter-spacing:1px}
.sev-critical .gsev{background:var(--crit);color:#fff}.sev-high .gsev{background:var(--high);color:#fff}
.sev-medium .gsev{background:var(--med);color:#121212}.sev-low .gsev{background:#3a4d68;color:#fff}
ul.gaps li em{color:var(--teal);font-style:normal;font-weight:700}
ul.gaps li span{display:block;color:var(--mut);font-size:12.5px;margin-top:3px}
.muted{color:var(--mut)}
.pen{margin-top:18px;border-top:1px solid var(--line);padding-top:14px}
.pen h4{margin:0 0 6px;font-size:12px;letter-spacing:1px;color:var(--gold);text-transform:uppercase}
.penrow b{font-size:20px;font-family:"Arial Black"}.penrow.sub{color:var(--mut);font-size:13px}.pennote{color:var(--mut);font-size:12px;margin-top:6px}
.colt{margin-top:20px}.colt h3{color:var(--teal);font-size:14px;letter-spacing:2px;text-transform:uppercase}
.coltgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:760px){.coltgrid{grid-template-columns:1fr}}
.coltcard{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--teal);border-radius:10px;padding:14px}
.coltcard b{color:var(--ink)}.coltcard span{display:block;color:var(--mut);font-size:13px;margin-top:4px}
h2.sec{font-size:24px;font-weight:900;margin:0 0 20px}
.tl{position:relative;margin-left:8px;padding-left:22px;border-left:2px solid var(--line)}
.tl .ev{position:relative;padding:10px 0}
.tl .ev::before{content:"";position:absolute;left:-29px;top:16px;width:11px;height:11px;border-radius:50%;background:var(--teal);box-shadow:0 0 0 4px rgba(0,215,189,.15)}
.tl .ev .d{color:var(--teal);font-weight:800;font-size:14px}.tl .ev .r{color:var(--gold);font-size:12px;font-weight:700;letter-spacing:1px}
.tl .ev .l{color:var(--ink);font-size:14px}
.phases{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}@media(max-width:760px){.phases{grid-template-columns:1fr}}
.phase{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}
.phase .when{display:inline-block;background:var(--teal);color:#04211f;font-weight:800;padding:5px 12px;border-radius:8px;font-size:13px;margin-bottom:10px}
.phase ul{margin:0;padding-left:18px}.phase li{font-size:13.5px;margin:6px 0;color:var(--ink)}
.reveal{opacity:0;transform:translateY(26px);transition:opacity .7s cubic-bezier(.2,.7,.2,1),transform .7s cubic-bezier(.2,.7,.2,1)}
.reveal.in{opacity:1;transform:none}
footer{padding:34px 0;color:var(--mut);font-size:12.5px}
.wm{color:var(--teal);font-weight:900}
</style></head>
<body>
<div class="hero"><div class="wrap">
  <div class="eyebrow">${esc(L("eyebrow"))}</div>
  <h1>${esc(company)}</h1>
  <div class="sub">NIS2 &nbsp;·&nbsp; Cyber Resilience Act &nbsp;·&nbsp; EU AI Act</div>
  <div class="hchips">${chips}</div>
  <div class="assume">
    <div class="a"><b>${esc(L("sector"))}:</b> ${esc(a.sector || "—")}</div>
    <div class="a"><b>${esc(L("size"))}:</b> ${esc(a.size_band || L("unknown"))}</div>
    <div class="a"><b>${esc(L("digital"))}:</b> ${esc(yn(a.sells_digital_products))}</div>
    <div class="a"><b>${esc(L("ai"))}:</b> ${esc(yn(a.builds_or_deploys_ai))}</div>
    <div class="a"><b>${esc(L("countries"))}:</b> ${esc((a.countries || []).join(", ") || "—")}</div>
  </div>
  <p class="note">${esc(L("confirmNote"))}</p>
</div></div>

<div class="wrap">
  ${["nis2", "cra", "aiact"].map(regimeSection).join("")}

  <section class="reveal"><h2 class="sec">${esc(L("timeline"))}</h2>
    <div class="tl">${allDl.slice(0, 14).map((d) => `<div class="ev"><div class="d">${esc(fmtDate(d.date))} <span class="r">${esc(d.regime)}</span></div><div class="l">${esc(d.label || "")}</div></div>`).join("") || `<div class="ev"><div class="l muted">—</div></div>`}</div>
  </section>

  <section class="reveal"><h2 class="sec">${esc(L("roadmap"))}</h2>
    ${rm.exec_summary ? `<p class="rationale">${esc(rm.exec_summary)}</p>` : ""}
    <div class="phases">${(rm.phases || []).slice(0, 3).map((ph) => `<div class="phase"><span class="when">${esc(ph.when || "")}</span><ul>${(ph.items || []).slice(0, 6).map((it) => `<li>${esc(it)}</li>`).join("")}</ul></div>`).join("")}</div>
  </section>
</div>

<footer><div class="wrap"><span class="wm">» colt</span> &nbsp; ${esc(L("sources"))}</div></footer>
<script>
(function(){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target);}});},{threshold:.12});
document.querySelectorAll(".reveal").forEach(function(el){io.observe(el);});})();
</script>
</body></html>`;

fs.writeFileSync(outPath, html, "utf8");
console.error("[compliance-html] wrote " + outPath + " (" + LANG + ")");
