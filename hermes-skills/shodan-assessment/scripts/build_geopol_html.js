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
 *               "h1": "A VPN edge on {hl}the carrier backbone{/hl}.",
 *               "sub": "…rich prose with {ink}…{/ink} {red}…{/red} spans…",
 *               "stats": [ {"n":"8","l":"Verified exposed hosts"}, {"n":"1","l":"Exposed VPN edge","bad":true} ],
 *               "legend":[ {"c":"teal","t":"carrier backbone"} ],
 *               "caption":"Findings: …" },
 *   "scene2": { same shape, canvas id c2, no statbar by default }
 * }
 *
 * Inline markup tokens in h1/sub/caption:  {hl}..{/hl} teal highlight · {ink}..{/ink} bright ·
 *   {red}..{/red} · {amber}..{/amber} · {b}..{/b} bold.  Everything else is escaped.
 *
 * LANGUAGE:  DECK_LANG=en|ru|…  — the skeleton's own ~59 visible strings are localised from
 *   geopol_html/i18n/<code>.json. See localiseShell() for why the substitution is surgical.
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

/* ------------------------------------------------------------------ language
   LANGUAGE IS DATA, NOT A BRANCH — the same rule scripts/i18n/deck_i18n.js follows. The 2-letter
   code selects `geopol_html/i18n/<code>.json`; a language with no dictionary falls back to English
   rather than rendering half-translated. Adding German = dropping a `de.json` in beside ru.json,
   with no change to this file. (German is not shipped here on purpose — see ru.json's _comment.) */
const LANG = (function () {
  const want = String(process.env.DECK_LANG || "en").toLowerCase().slice(0, 2);
  if (!want || want === "en") return "en";
  return fs.existsSync(path.join(__dirname, "geopol_html", "i18n", want + ".json")) ? want : "en";
})();
const PACK = (function () {
  if (LANG === "en") return {};
  try { return JSON.parse(fs.readFileSync(path.join(__dirname, "geopol_html", "i18n", LANG + ".json"), "utf8")); }
  catch (e) { console.error("[geopol-html] i18n: could not load " + LANG + ".json: " + e.message); return {}; }
})();
const STRINGS = PACK.strings || {};
const CANVAS = PACK.canvas || {};
// Source strings that stay English ON PURPOSE (brand, service categories, framework names). Stated
// in the pack rather than hardcoded here so the list is reviewable next to the translations, and so
// the coverage report below can tell "deliberately English" from "somebody forgot".
const KEEP = new Set(PACK.untranslated || []);
const MISSING = [];

/** Translate one visible string, preserving the caller's own surrounding whitespace.
 *  Unknown strings pass through untouched: a missing translation degrades to English, never to a
 *  blank or a raw key. */
function T(s) {
  if (LANG === "en" || typeof s !== "string" || !s.trim()) return s;
  const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/);
  const core = m[2];
  const hit = STRINGS[core];
  if (hit === undefined) {
    // A string with no entry renders in ENGLISH — readable, never a blank or a raw key. But record
    // it: silent English inside a translated page is the failure mode that has to be visible.
    const bare = core.replace(/\{\{[A-Z_]+\}\}/g, "").replace(/&[a-zA-Z#0-9]+;/g, "").replace(/__SCENE\d__/g, "");
    if (/[A-Za-z]{2}/.test(bare) && !KEEP.has(core)) MISSING.push(core);
    return s;
  }
  return m[1] + hit + m[3];
}

/* ------------------------------------------------------- surgical localisation
   The skeleton is CSS + HTML + ~230 lines of canvas JavaScript in ONE file. A blanket
   string-replace over it WILL corrupt code — that exact mistake once broke a JS data array in this
   repo and produced a parse error. So two narrow passes, and nothing else is ever touched:
     1) HTML TEXT NODES only — the text between `>` and `<`, with <script>/<style> bodies excised
        first so a CSS selector or a JS identifier can never be matched as prose.
     2) Complete quoted STRING LITERALS inside <script> — matched WITH their quotes and re-emitted
        via JSON.stringify, so a substring of an identifier can never match and the replacement is
        always a syntactically valid literal. Only the ids listed in the pack's `canvas` map are
        eligible, which is what keeps the animation's LOOKUP KEYS ('SASE · ZTNA', 'SSE · SECURE
        EGRESS' — compared with === and indexOf) out of reach.
   A key in the pack that no longer exists in the skeleton is REPORTED, not silently ignored: that
   is how a renamed literal shows up as a translation gap instead of as English on a Russian page. */
function localiseScript(js) {
  for (const en of Object.keys(CANVAS)) {
    let hits = 0;
    for (const q of ['"', "'"]) {
      const needle = q + en + q;
      if (js.indexOf(needle) < 0) continue;
      hits += js.split(needle).length - 1;
      js = js.split(needle).join(JSON.stringify(CANVAS[en]));
    }
    if (!hits) console.error("[geopol-html] i18n: canvas literal not found in skeleton: " + JSON.stringify(en));
  }
  return js;
}

function localiseShell(html) {
  if (LANG === "en") return html;            // EN is a strict no-op -> byte-identical to before
  const parts = html.split(/(<script\b[\s\S]*?<\/script>|<style\b[\s\S]*?<\/style>)/i);
  for (let i = 0; i < parts.length; i++) {
    if (/^<script\b/i.test(parts[i])) { parts[i] = localiseScript(parts[i]); continue; }
    if (/^<style\b/i.test(parts[i])) continue;                       // never touch CSS
    parts[i] = parts[i].replace(/>([^<]+)</g, (m, txt) => ">" + T(txt) + "<");
  }
  // document language: assistive tech and browser spellcheck read this, and it is a text ATTRIBUTE,
  // so it has to be set explicitly rather than falling out of the text-node pass.
  return parts.join("").replace(/<html lang="[^"]*"/i, '<html lang="' + LANG + '"');
}

/** Report every skeleton string that fell through to English. ship.py fails the deploy on this:
 *  a paragraph added to the skeleton and never translated is invisible otherwise. */
function reportCoverage() {
  if (LANG === "en" || !MISSING.length) return;
  const uniq = [...new Set(MISSING)];
  console.error("[geopol-html] i18n: " + uniq.length + " UNTRANSLATED string(s) for " + LANG + ":");
  for (const s of uniq) console.error("[geopol-html] i18n:   " + JSON.stringify(s.slice(0, 110)));
}

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

shell = localiseShell(shell);        // must run BEFORE the scene/company substitutions below:
                                     // the authored scenes already arrive in the target language,
                                     // and {{COMPANY}} tokens survive inside translated strings.

const company = C.company || "Target";
const title = C.title || (company + " " + T("GEOPOL — Threat, Defence & Secure by Design · Cybergod / S4Biz"));

// ---- scene-3 vectors/exposures/impacts + scene-2 actors are DATA, not frozen text ----
// The canvas wires index into these by fixed position, so lengths are pinned: 6 vectors, 6 exposures,
// 5 impacts, 6 actors. We pad with generic defaults and truncate — never leak another company's data.
const COLORS = ["TEAL", "RED", "ORANGE", "MINT", "VIOLET", "AMBER"];
const jsColor = (c) => COLORS.includes(String(c || "").toUpperCase()) ? String(c).toUpperCase() : "TEAL";
// The padding defaults are OUR copy (not the customer's data), so they are localised too — a
// half-Russian chip row is the same defect class as a half-translated page.
function fixArr(items, n, deflt) {
  const out = (Array.isArray(items) ? items : []).slice(0, n);
  while (out.length < n) {
    const d = deflt[out.length] || deflt[deflt.length - 1];
    out.push(Array.isArray(d) ? d.map((x, i) => (i === 1 ? x : T(x))) : T(d));
  }
  return out;
}
const s3 = (C.scene3 || {});
// LEFT = [[label, COLOR], ...] (6 attack vectors)
const DEF_VEC = [["Volumetric DDoS", "TEAL"], ["Remote-access exploit", "RED"], ["Credential stuffing", "AMBER"],
  ["Web-app exploit", "ORANGE"], ["Ransomware deploy", "VIOLET"], ["Data exfiltration", "MINT"]];
const vecs = fixArr((s3.vectors || []).map((v) => [String(v.t || v), jsColor(v.c)]), 6, DEF_VEC);
// MID = [str, ...] (6 of the target's own exposures — filled from real findings by the author)
const DEF_EXP = ["Internet-facing edge", "Web / app fleet", "Mail edge", "Management interface",
  "TLS / PKI weakness", "Look-alike / brand"];
const exps = fixArr((s3.exposures || []).map(String), 6, DEF_EXP);
// RIGHT = [str, ...] (5 impacts / crown jewels)
const DEF_IMP = ["Customer / user PII", "Core service delivery", "Operational continuity",
  "Credentials & secrets", "Brand & trust"];
const imps = fixArr((s3.impacts || []).map(String), 5, DEF_IMP);
// scene-2 actors = [[NAME, COLOR, method], ...] (6)
const DEF_ACT = [["OPPORTUNISTIC RaaS", "VIOLET", "ransomware via exposed edge"],
  ["INITIAL-ACCESS BROKERS", "AMBER", "sell exposed remote-access"], ["HACKTIVIST DDoS", "TEAL", "volumetric flood"],
  ["CREDENTIAL THIEVES", "RED", "phishing / stuffing"], ["KEV fleet", "ORANGE", "known-exploited CVE"],
  ["BRAND ABUSE", "MINT", "look-alike / fraud"]];
const acts = fixArr((C.scene2 && C.scene2.actors || []).map((a) =>
  [String(a.name || a.t || ""), jsColor(a.c), String(a.method || a.m || "")]), 6, DEF_ACT);

const jsLeft = "[" + vecs.map(([t, c]) => `[${JSON.stringify(t)},${c}]`).join(",") + "]";
const jsMid = JSON.stringify(exps);
const jsRight = JSON.stringify(imps);
const jsActs = "[" + acts.map(([n, c, m]) => `[${JSON.stringify(n)},${c},${JSON.stringify(m)}]`).join(",") + "]";

shell = shell.replace("__SCENE1__", scene(C.scene1, "c1", T("Scene 01 · The exposed estate")));
shell = shell.replace("__SCENE2__", scene(C.scene2, "c2", T("Scene 02 · Who is coming")));
shell = shell.replace("__S3_LEFT__", jsLeft).replace("__S3_MID__", jsMid)
             .replace("__S3_RIGHT__", jsRight).replace("__S2_ACTORS__", jsActs);
// {{COMPANY}} tokens in the fixed defense scenes + header; and the <title>
shell = shell.replace(/\{\{COMPANY_UPPER\}\}/g, esc(company.toUpperCase()));
shell = shell.replace(/\{\{COMPANY\}\}/g, esc(company));
shell = shell.replace(/<title>[^<]*<\/title>/, "<title>" + esc(title) + "</title>");

reportCoverage();
fs.writeFileSync(OUT, shell);
console.log("[ok] " + OUT + "  (" + (Buffer.byteLength(shell) / 1024).toFixed(0) + " KB)");
