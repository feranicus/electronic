// What the world can read.
//
// VIEW-SOURCE CANNOT BE DISABLED. It is a browser feature that shows bytes the browser already
// has; curl, DevTools, a proxy or the disk cache give the same result, and blocking right-click
// is theatre anyone defeats with Ctrl+U. So the question is never "can they look", it is "what
// is there to find". This measures that, on the REAL build output.
//
// Three properties, each of which would be a genuine finding if it broke:
//   1. NO SOURCE MAPS. A shipped .map hands over the entire original source, comments included.
//   2. NO SECRETS OR INTERNAL INFRASTRUCTURE in the bundle or the shell.
//   3. NO HTML COMMENTS in the shipped shell. Ours named the bot-gate mechanism and the file it
//      lives in - not a vulnerability, but free information handed to every scanner.
// And one thing that must SURVIVE: the JSON-LD block, which is what earns the rich search result.
import fs from "node:fs";
import path from "node:path";

const DIST = path.resolve(process.cwd(), "dist");
if (!fs.existsSync(DIST)) {
  console.error("shipped-shell: no dist/ - run the build first");
  process.exit(2);                      // toolchain, not a defect: ship.py treats 2 as a note
}
const fail = [];
const walk = (d) => fs.readdirSync(d, { withFileTypes: true })
  .flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const files = walk(DIST);

// 1 -------------------------------------------------------------------------------------------
const maps = files.filter((f) => f.endsWith(".map"));
if (maps.length) fail.push(`source maps are shipped (${maps.length}): the full original source, `
  + `comments and all, is downloadable. Set build.sourcemap=false.`);

// 2 -------------------------------------------------------------------------------------------
const SECRET = [
  [/\b64\.225\.108\.\d+\b/, "the production droplet's IP"],
  [/\b165\.245\.\d+\.\d+\b/, "the staging droplet's IP"],
  [/\bsk-[A-Za-z0-9]{16,}/, "an OpenAI-style key"],
  [/\bgh[pous]_[A-Za-z0-9]{16,}/, "a GitHub token"],
  [/\bglsa_[A-Za-z0-9]{16,}/, "a Grafana token"],
  [/\b\d{9,10}:AA[A-Za-z0-9_-]{30,}/, "a Telegram bot token"],
  [/AKIA[0-9A-Z]{16}/, "an AWS/Spaces access key"],
];
for (const f of files.filter((x) => /\.(js|css|html|json|webmanifest)$/.test(x))) {
  const s = fs.readFileSync(f, "utf8");
  for (const [re, what] of SECRET) {
    const m = s.match(re);
    if (m) fail.push(`${path.relative(DIST, f)} contains ${what}: ${m[0].slice(0, 12)}...`);
  }
}

// 3 + the thing that must survive ---------------------------------------------------------------
const shell = fs.readFileSync(path.join(DIST, "index.html"), "utf8");
const comments = shell.match(/<!--[\s\S]*?-->/g) || [];
if (comments.length) {
  fail.push(`the shipped shell carries ${comments.length} HTML comment(s), delivered to every `
    + `visitor including scanners: ${JSON.stringify(comments[0].slice(0, 70))}`);
}
if (!shell.includes("application/ld+json")) {
  fail.push("the JSON-LD block is gone - the comment strip is too greedy and the rich search "
    + "result depends on it");
}
for (const must of ["<title>", 'name="description"', 'property="og:title"']) {
  if (!shell.includes(must)) fail.push(`the shell lost ${must} - the strip removed too much`);
}

const js = files.filter((f) => f.endsWith(".js"));
console.log(`shipped shell: ${(shell.length / 1024).toFixed(1)} KB, `
  + `${comments.length} comment(s), ${maps.length} source map(s), ${js.length} script(s)`);
if (fail.length) {
  console.error("\nWHAT THE WORLD CAN READ - problems:");
  for (const f of fail) console.error("  [X] " + f);
  process.exit(1);
}
console.log("  no source maps, no secrets, no comments; JSON-LD and the meta tags intact");
