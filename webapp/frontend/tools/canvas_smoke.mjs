/* Execute a canvas page's render loop against a stub 2D context and FAIL on any runtime error
   or any invalid colour string.

   WHY THIS EXISTS. defense.html shipped with a half-written line that produced the colour
   "rgba(FF3B57" and threw inside addColorStop on EVERY frame, so the canvas stayed black. It
   passed `node --check`, because that only PARSES. It passed the offline composition render,
   because that redraws the maths in Python and never executes the page's own JavaScript. An
   invalid value is legal JS right up to the moment it executes.
   CLAUDE.md already carried the rule ("a passing vite build does NOT mean the page works") and I
   checked syntax instead of running the thing. So: run the thing.                                */
import fs from "node:fs";
import path from "node:path";

const file = process.argv[2] || "public/defense.html";
const FRAMES = Number(process.argv[3] || 900);
const html = fs.readFileSync(file, "utf8");

/* The script moved OUT of the page so the site can run script-src 'self' with no 'unsafe-inline'.
   This gate has to follow it. Reading an inline block that no longer exists would have made the
   check silently unable to see its subject, which is the single most repeated defect in this
   repository. So: take whichever form the page uses, and FAIL if neither is there. */
let js = null, src = null;
const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
const ext = html.match(/<script[^>]*\ssrc="\/([^"]+\.js)"/);
if (inline.length) { js = inline[inline.length - 1][1]; src = "inline block"; }
else if (ext) {
  const p = path.join(path.dirname(file), ext[1]);
  if (!fs.existsSync(p)) {
    console.error("%s references /%s and that file does not exist", file, ext[1]);
    process.exit(1);
  }
  js = fs.readFileSync(p, "utf8"); src = ext[1];
}
if (!js || js.trim().length < 500) {
  console.error("no runnable script found in " + file + " (looked for an inline block and a "
                + "same-origin src). A gate that reads nothing passes for the wrong reason.");
  process.exit(1);
}
console.log("  smoke: %s -> %s (%d bytes)", path.basename(file), src, js.length);

const errors = [];
const COLOUR = /^(#[0-9a-fA-F]{3,8}|rgba?\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*(,\s*[\d.]+\s*)?\)|transparent|[a-z]+)$/;
function checkColour(v, where) {
  if (v == null) return;
  if (typeof v === "object") return;                 /* a gradient object is fine */
  const s = String(v);
  if (!COLOUR.test(s)) errors.push(where + ": invalid colour " + JSON.stringify(s));
}
function gradient() {
  return { addColorStop(off, col) { checkColour(col, "addColorStop"); } };
}
const noop = () => {};
function ctx() {
  const o = {
    canvas: { width: 1600, height: 900 },
    createRadialGradient: gradient, createLinearGradient: gradient,
    createPattern: () => null,
    measureText: (t) => ({ width: String(t).length * 6 }),
    save: noop, restore: noop, beginPath: noop, closePath: noop, moveTo: noop, lineTo: noop,
    arc: noop, arcTo: noop, ellipse: noop, rect: noop, fill: noop, stroke: noop,
    fillRect: noop, strokeRect: noop, clearRect: noop, fillText: noop, strokeText: noop,
    translate: noop, rotate: noop, scale: noop, setTransform: noop, transform: noop,
    clip: noop, drawImage: noop, setLineDash: noop, quadraticCurveTo: noop, bezierCurveTo: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }), putImageData: noop,
  };
  return new Proxy(o, {
    set(t, k, v) {
      if (k === "fillStyle" || k === "strokeStyle" || k === "shadowColor") checkColour(v, String(k));
      t[k] = v; return true;
    },
    get(t, k) { return k in t ? t[k] : undefined; },
  });
}
const el = () => ({ getContext: ctx, style: {}, width: 0, height: 0, appendChild: noop,
                    removeChild: noop, firstChild: null, children: [], textContent: "",
                    addEventListener: noop, set onclick(f) { this._c = f; }, get onclick() { return this._c; } });

let queue = [];
const sandbox = {
  document: { getElementById: el, createElement: el, addEventListener: noop,
              body: { appendChild: noop } },
  window: { matchMedia: () => ({ matches: false }), addEventListener: noop },
  performance: { now: () => nowMs },
  requestAnimationFrame: (f) => { queue.push(f); return queue.length; },
  addEventListener: noop, devicePixelRatio: 2, innerWidth: 1600, innerHeight: 900,
  setInterval: () => 0, setTimeout: () => 0, console,
  Math, Date, JSON, Number, String, Array, Object, isNaN, parseInt, parseFloat,
};
let nowMs = 0;
const fn = new Function(...Object.keys(sandbox), js);
try { fn(...Object.values(sandbox)); }
catch (e) { console.error("THREW on load: " + e.message); process.exit(1); }

/* Drive the real loop. 900 frames at 16.7ms covers the whole 41s timeline, every act. */
for (let i = 0; i < FRAMES; i++) {
  const q = queue; queue = [];
  if (!q.length) break;
  nowMs += 46;                                        /* step fast enough to cross all six acts */
  for (const f of q) {
    try { f(nowMs); }
    catch (e) { console.error("THREW on frame " + i + ": " + e.message); process.exit(1); }
  }
  if (errors.length > 12) break;
}
if (errors.length) {
  const seen = new Set();
  for (const e of errors) if (!seen.has(e)) { seen.add(e); console.error("  " + e); }
  console.error("canvas smoke: " + seen.size + " distinct invalid colour(s) in " + path.basename(file));
  process.exit(1);
}
console.log("canvas smoke: " + path.basename(file) + " ran " + FRAMES +
            " frames, no exception, every colour valid");
