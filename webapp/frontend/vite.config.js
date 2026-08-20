import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server's /api target. `python preview.py` sets these; the defaults keep the historical
// behaviour (a backend running locally on :8000) so nothing changes for anyone already doing that.
const TARGET = process.env.CG_API_TARGET || "http://localhost:8000";
const READONLY = process.env.CG_API_READONLY === "1";

// -------------------------------------------------------------------------------------------
// STRIP HTML COMMENTS FROM THE SHIPPED SHELL (production builds only).
//
// index.html is delivered to EVERY visitor, including the scanners the bot gate exists to keep
// out - and view-source is a browser feature that cannot be turned off, so whatever is in that
// file is public by definition. Our comments there explained the BOT_404 mechanism by name and
// pointed at `visitors.py`. That is not a vulnerability, but telling an attacker which defence
// is running and what the file is called is free information we do not need to give away.
//
// The comments stay in the SOURCE, because explaining WHY is the whole point of them and the dev
// server still shows them. They are removed on the way into dist/ instead. `apply: "build"` is
// what keeps that split honest.
//
// Deliberately NOT touched: <script type="application/ld+json"> is an element, not a comment, so
// the structured data that earns the rich search result survives. Verified by a test.
// -------------------------------------------------------------------------------------------
const stripHtmlComments = {
  name: "strip-html-comments",
  apply: "build",
  transformIndexHtml(html) {
    return html.replace(/<!--[\s\S]*?-->/g, "").replace(/\n{3,}/g, "\n\n");
  },
};

export default defineConfig({
  base: "/",
  plugins: [react(), stripHtmlComments],
  server: {
    port: Number(process.env.CG_PORT || 5173),
    host: true,                       // also serve on the LAN, so the page can be opened on a phone
    proxy: {
      "/api": {
        target: TARGET,
        changeOrigin: true,
        secure: true,
        // ------------------------------------------------------------------------------------
        // READ-ONLY GUARD. When the preview points at the LIVE site so that the public pages
        // have real data, a local page must not be able to CHANGE anything up there. One stray
        // click on "Run assessment" would start a real job, burn Shodan credits and inference
        // tokens, and consume an evaluation account's quota, from what the operator believes is
        // a local colour preview.
        //
        // GET and HEAD pass. So does SIGNING IN, and that exception was earned the hard way:
        // blocking every write also blocked POST /api/auth/begin, so no logged-in page could be
        // opened in the preview AT ALL. The standing rule is to LOOK at a UI change before
        // shipping it, and for the cabinet — Assess, Compliance, History, Administration — that
        // rule was unfollowable. The operator hit exactly this ("I couldn't enter the preview with
        // shared password"); the vite log said `http proxy error: /api/auth/begin, socket hang up`,
        // which is this guard destroying the request.
        //
        // The line is COST AND CONSEQUENCE, not the HTTP verb. Signing in spends nothing, creates
        // nothing and is undone by logging out; the OTP still has to arrive in the real mailbox,
        // so this grants no access the operator did not already have. Everything that spends money,
        // consumes quota or changes another person's account stays refused.
        // ------------------------------------------------------------------------------------
        configure: (proxy) => {
          if (!READONLY) return;
          // Exact paths only. A prefix match on "/api/auth" would also admit
          // /api/auth/change-password, which is a real credential change and belongs on the live
          // site, not in a colour preview.
          const ALLOW_WRITE = new Set([
            "/api/auth/begin",     // email + password -> sends the OTP to the real mailbox
            "/api/auth/verify",    // OTP -> session cookie, so the cabinet can be looked at
            "/api/auth/logout",    // always allow the way out
            "/api/privacy/ack",    // records that the Art.13 notice was shown; no cost, no quota
          ]);
          proxy.on("proxyReq", (proxyReq, req, res) => {
            const m = (req.method || "GET").toUpperCase();
            if (m === "GET" || m === "HEAD") return;
            const path = (req.url || "").split("?")[0];
            if (ALLOW_WRITE.has(path)) return;
            proxyReq.destroy();
            res.writeHead(405, { "Content-Type": "application/json" });
            res.end(JSON.stringify({
              error: "blocked by the local preview",
              detail: `${m} ${req.url} was not sent. The preview proxies /api to ${TARGET} in `
                    + "READ-ONLY mode so a local page cannot start a real assessment, change a "
                    + "user's account or consume quota. Signing in works so that logged-in pages "
                    + "can be looked at; anything with a cost or a consequence does not.",
            }));
          });
        },
      },
    },
  },
  build: { outDir: "dist" },
});
