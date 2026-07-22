#!/usr/bin/env node
/**
 * build_geopol_html.js — render the per-company GEOPOL animated HTML, 1:1 with the reference
 * examples (BibelTV / Stratos / Rosneft). The FIXED shell (CSS, the five inline canvas animations,
 * and the defense scenes s3/s4/s5) lives in geopol_html/skeleton.html and is emitted byte-for-byte.
 * Only Scene 01 (exposed estate) and Scene 02 (who is coming) are per-company — this builder
 * assembles their exact DOM from a small content object so the structure can never drift.
 *
 *   node build_geopol_html.js content.json out.html
 *
 * content.json shape (all fields optional; missing -> sensible default):
 * {
 *   "company": "Bibel TV",
 *   "title":   "Bibel TV GEOPOL — Threat, Defence & Secure by Design",
 *   "scene1": { "eyebrow": "Scene 01 · The exposed estate",
 *               "h1": "A VPN edge on {hl}Colt's own backbone{/hl}.",
 *               "sub": "…rich prose with {ink}…{/ink} {red}…{/red} spans…",
 *               "stats": [ {"n":"8","l":"Verified exposed hosts"}, {"n":"1","l":"Exposed VPN edge","bad":true} ],
 *               "legend":[ {"c":"teal","t":"Colt backbone · AS8220"} ],
 *               "caption":"Findings: …" },
 *   "scene2": { same shape, canvas id c2, no statbar by default }
 * }
 *
 * Inline markup tokens in h1/sub/caption:  {hl}..{/hl} teal highlight · {ink}..{/ink} bright ·
 *   {red}..{/red} · {amber}..{/amber} · {b}..{/b} bold.  Everything else is escaped.
 */
"use strict";
const fs = require("fs");
const path = require("path");

const [, , CONTENT, OUT] = process.argv;
if (!CONTENT || !OUT) { console.error("usage: build_geopol_html.js content.json out.html"); process.exit(2); }

const SKELETON = path.join(__dirname, "geopol_html", "skeleton.html");
let shell = fs.readFileSync(SKELETON, "utf8");
let C = {};
try { C = JSON.parse(fs.readFileSync(CONTENT, "utf8")); } catch (e) { console.error("bad content.json:", e.message); }

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// inline rich-text tokens -> the reference's exact span markup
function rich(s) {
  let out = esc(s);
  out = out
    .replace(/\{hl\}/g, '<span class="hl">').replace(/\{\/hl\}/g, "</span>")
    .replace(/\{ink\}/g, '<b style="color:var(--ink)">').replace(/\{\/ink\}/g, "</b>")
    .replace(/\{red\}/g, '<b style="color:var(--red)">').replace(/\{\/red\}/g, "</b>")
    .replace(/\{amber\}/g, '<b style="color:var(--amber)">').replace(/\{\/amber\}/g, "</b>")
    .replace(/\{green\}/g, '<b style="color:var(--green)">').replace(/\{\/green\}/g, "</b>")
    .replace(/\{b\}/g, "<b>").replace(/\{\/b\}/g, "</b>");
  return out;
}
const VARC = { teal: "var(--teal)", violet: "var(--violet)", orange: "var(--orange)",
  mint: "var(--mint)", amber: "var(--amber)", red: "var(--red)", green: "var(--green)", faint: "#3b4a63" };

function statbar(stats) {
  if (!stats || !stats.length) return "";
  const cells = stats.slice(0, 4).map((s) =>
    `<div class="stat${s.bad ? " bad" : ""}"><div class="n" data-to="${esc(s.n)}">0</div><div class="l">${esc(s.l)}</div></div>`
  ).join("\n        ");
  return `<div class="statbar">\n        ${cells}\n      </div>`;
}
function legend(items) {
  if (!items || !items.length) return "";
  const rows = items.map((it) =>
    `<span><i style="background:${VARC[it.c] || it.c || "var(--teal)"}"></i>${esc(it.t)}</span>`
  ).join("\n        ");
  return `<div class="legend">\n        ${rows}\n      </div>`;
}

function scene(sc, canvasId, fallbackEyebrow) {
  sc = sc || {};
  const eye = esc(sc.eyebrow || fallbackEyebrow);
  const h1 = rich(sc.h1 || "");
  const sub = rich(sc.sub || "");
  const cap = sc.caption ? `<p class="caption">${rich(sc.caption)}</p>` : "";
  const bar = statbar(sc.stats);
  const leg = legend(sc.legend);
  return `
    <div class="eyebrow">${eye}</div>
    <h1>${h1}</h1>
    <p class="sub">${sub}</p>
    <div class="stage">
      <canvas id="${canvasId}"></canvas>
      ${bar}
      ${leg}
    </div>
    ${cap}
  `;
}

const company = C.company || "Target";
const title = C.title || (company + " GEOPOL — Threat, Defence & Secure by Design · Colt / S4Biz");

shell = shell.replace("__SCENE1__", scene(C.scene1, "c1", "Scene 01 · The exposed estate"));
shell = shell.replace("__SCENE2__", scene(C.scene2, "c2", "Scene 02 · Who is coming"));
// {{COMPANY}} tokens in the fixed defense scenes + header; and the <title>
shell = shell.replace(/\{\{COMPANY_UPPER\}\}/g, esc(company.toUpperCase()));
shell = shell.replace(/\{\{COMPANY\}\}/g, esc(company));
shell = shell.replace(/<title>[^<]*<\/title>/, "<title>" + esc(title) + "</title>");

fs.writeFileSync(OUT, shell);
console.log("[ok] " + OUT + "  (" + (Buffer.byteLength(shell) / 1024).toFixed(0) + " KB)");
