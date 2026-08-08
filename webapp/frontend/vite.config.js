import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server's /api target. `python preview.py` sets these; the defaults keep the historical
// behaviour (a backend running locally on :8000) so nothing changes for anyone already doing that.
const TARGET = process.env.CG_API_TARGET || "http://localhost:8000";
const READONLY = process.env.CG_API_READONLY === "1";

export default defineConfig({
  base: "/",
  plugins: [react()],
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
