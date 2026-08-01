// tools/run_i18n_audit.mjs — bundle the SSR audit and run it. ONE command, cross-platform.
//
//     node tools/run_i18n_audit.mjs      -> exits non-zero if the audit fails
//
// WHY IT DOES NOT SHELL OUT TO node_modules/.bin/esbuild:
// that path is a PLATFORM SHIM. On Linux it is a symlink named `esbuild`; on Windows npm normally
// writes `esbuild.cmd`, and in this repo's install it is absent altogether — so ship.py probed for
// a file that does not exist and reported "esbuild missing - run npm install" on a machine where
// esbuild was installed and working. Importing the package's JS API instead resolves through
// node_modules the same way `import "react"` does, on every platform, with no path guessing.
//
// Same class of bug as the ESM `C:\...` path in i18n_catalogue.mjs: code that works on the dev's
// OS by accident and fails on the operator's. The rule is the one already in CLAUDE.md — never
// anchor on a path you did not just read.
// EXIT CODES ARE PART OF THE CONTRACT:
//   0 = audit passed
//   1 = the audit found a REAL defect (a raw key, a fallback to English, an over-length tab label)
//   2 = the TOOLCHAIN is unusable on this machine — esbuild ships a per-platform binary as an
//       optional dependency, and this repo's node_modules is Linux-native (it is a shared folder),
//       so on Windows it reports "@esbuild/win32-x64 could not be found".
// ship.py fails on 1 and only NOTES 2, because the audit is enforced for real in webapp/Dockerfile,
// which does a fresh npm install on linux/amd64. Conflating the two exit codes would either block
// the operator over a toolchain they never installed, or swallow a genuine translation defect.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FE = path.join(HERE, "..");
const OUT = path.join(FE, "ssrtmp", "i18n_audit.cjs");

let esbuild;
try {
  esbuild = await import("esbuild");
} catch (e) {
  console.error("[SKIP] esbuild is not usable here (" + (e && e.message ? e.message.split("\n")[0] : e) + ")");
  process.exit(2);
}

mkdirSync(path.join(FE, "ssrtmp"), { recursive: true });

// ALWAYS rebuild. The bundle inlines the locale files, so a stale one audits yesterday's
// dictionaries and reports green on a broken translation — a check that cannot see the thing it
// checks is not a check.
try {
  await esbuild.build({
    entryPoints: [path.join(HERE, "i18n_audit.jsx")],
    bundle: true, outfile: OUT,
    platform: "node", format: "cjs", jsx: "automatic",
    loader: { ".css": "empty" }, logLevel: "error",
  });
} catch (e) {
  const msg = String((e && e.message) || e);
  // A missing per-platform binary is a toolchain problem, not a translation problem.
  if (/@esbuild\/|could not be found|Cannot find module/.test(msg)) {
    console.error("[SKIP] esbuild has no binary for this platform:\n" + msg.split("\n")[0]);
    process.exit(2);
  }
  console.error("[FAIL] could not bundle the i18n audit: " + msg);
  process.exit(1);
}

const r = spawnSync(process.execPath, [OUT], { cwd: FE, stdio: "inherit" });
process.exit(r.status === null ? 1 : r.status);
