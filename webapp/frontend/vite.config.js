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
        // GET and HEAD pass. Everything else is refused HERE, before it leaves the machine, and
        // says why. Refusing locally rather than relying on the server's auth is deliberate: the
        // browser may still hold a valid session cookie for the live site.
        // ------------------------------------------------------------------------------------
        configure: (proxy) => {
          if (!READONLY) return;
          proxy.on("proxyReq", (proxyReq, req, res) => {
            const m = (req.method || "GET").toUpperCase();
            if (m === "GET" || m === "HEAD") return;
            proxyReq.destroy();
            res.writeHead(405, { "Content-Type": "application/json" });
            res.end(JSON.stringify({
              error: "blocked by the local preview",
              detail: `${m} ${req.url} was not sent. The preview proxies /api to ${TARGET} in `
                    + "READ-ONLY mode so a local page cannot start a real assessment, change "
                    + "settings or consume quota. Read-only pages work; anything that writes does not.",
            }));
          });
        },
      },
    },
  },
  build: { outDir: "dist" },
});
