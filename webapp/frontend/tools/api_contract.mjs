// tools/api_contract.mjs — assert every api.js caller consumes the shape its helper actually returns.
//
// THE DEFECT THIS EXISTS FOR, twice in one codebase:
//   api.js has TWO helpers with DIFFERENT return contracts —
//     getJSON(path)  -> the PARSED BODY            (throws on 401 / network)
//     postJSON(path) -> { ok, status, data }
//   Destructuring `{ ok, data }` from a getJSON-backed call compiles, runs, and silently yields
//   `undefined` for both. Every guard written against them then fails closed:
//     * `getLangs`     -> the document-language selector showed English ONLY, while the engine could
//                        write German and Russian. The operator saw a feature disappear.
//     * `assessStatus` -> the re-attach path ALWAYS bailed and deleted `cg_job`, so a phone that
//                        evicted the tab could never rejoin a running assessment.
//   Neither is visible to `vite build`, to the SSR audit, or to a code review that does not happen
//   to open api.js. It is the same root cause as calling `.returncode` on ship.py's `run()`, which
//   returns an int: ASSUMING A HELPER'S CONTRACT INSTEAD OF READING IT.
//
// Run: node tools/api_contract.mjs   (exit 1 on any mismatch)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SRC = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src");
const read = (p) => fs.readFileSync(p, "utf8");
const api = read(path.join(SRC, "api.js"));

// Which exported names are backed by which helper.
const backed = (helper) =>
  new Set([...api.matchAll(new RegExp(String.raw`export const (\w+)\s*=[^;]*?${helper}\(`, "g"))]
    .map((m) => m[1]));
const GET = backed("getJSON");
// delJSON returns the SAME { ok, status, data } shape as postJSON on purpose, so its callers are
// checked by the same rule. Listed explicitly: a helper this gate does not know about is a helper
// whose call sites nobody checks, which is the silent gap the whole file exists to close.
const POST = new Set([...backed("postJSON"), ...backed("delJSON")]);
GET.add("getJSON");
POST.add("postJSON");
POST.add("delJSON");

const files = [];
for (const dir of ["pages", "components", "."]) {
  const d = path.join(SRC, dir);
  for (const f of fs.readdirSync(d)) {
    if (/\.(jsx?|mjs)$/.test(f) && fs.statSync(path.join(d, f)).isFile()) files.push(path.join(d, f));
  }
}

let fail = 0;
for (const f of files) {
  const s = read(f);
  // `const { ok, data } = await someCall(` — the exact shape that silently breaks.
  for (const m of s.matchAll(/const\s*\{([^}]*)\}\s*=\s*await\s+(\w+)\s*\(/g)) {
    const fields = m[1].replace(/\s+/g, " ").trim();
    const fn = m[2];
    if (GET.has(fn) && /\b(ok|status|data)\b/.test(fields)) {
      console.error(`  [FAIL] ${path.relative(SRC, f)}: {${fields}} = await ${fn}() — ` +
        `${fn} is getJSON-backed and returns the BODY, not {ok, data}`);
      fail++;
    }
  }
  // The mirror image: reading a postJSON result as if it were the body.
  for (const m of s.matchAll(/const\s+(\w+)\s*=\s*await\s+(\w+)\s*\(/g)) {
    const [, name, fn] = m;
    if (POST.has(fn) && fn !== "postJSON" && !/^\s*$/.test(name)) {
      const used = new RegExp(String.raw`\b${name}\.(ok|data|status)\b`).test(s);
      if (!used) {
        console.error(`  [FAIL] ${path.relative(SRC, f)}: const ${name} = await ${fn}() — ` +
          `${fn} is postJSON-backed and returns {ok, status, data}; ${name}.data is never read`);
        fail++;
      }
    }
  }
}

console.log(`api contract: ${GET.size - 1} getJSON-backed, ${POST.size - 1} postJSON-backed, ` +
            `${files.length} files checked`);
if (fail) { console.error(`\n[FAIL] api contract: ${fail} call site(s) use the wrong shape`); process.exit(1); }
console.log("  api contract OK");
