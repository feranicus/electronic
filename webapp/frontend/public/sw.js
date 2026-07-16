/* Service worker — app shell only.
 *
 * HARD RULE: never cache /api. This app streams a live assessment and serves owner-scoped decks
 * behind a session cookie. A cached API response would show one user another user's job, or replay
 * a stale run — a correctness AND a privacy bug. Only static build assets are cached.
 *
 * Strategy: network-first for navigation (so a deploy is picked up immediately), cache-first for
 * hashed build assets (they are immutable — Vite fingerprints them).
 */
const CACHE = "cybergod-shell-v1";
const SHELL = ["/", "/app", "/icon-192.png", "/icon-512.png", "/apple-touch-icon.png", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;
  // never touch the API or the event stream — auth'd, live, per-user
  if (url.pathname.startsWith("/api/")) return;

  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        .then((r) => { const cp = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, cp)); return r; })
        .catch(() => caches.match(e.request).then((m) => m || caches.match("/app")))
    );
    return;
  }
  if (/\/assets\/.*\.(js|css|woff2?)$/.test(url.pathname) || /\.(png|svg|ico|webmanifest)$/.test(url.pathname)) {
    e.respondWith(
      caches.match(e.request).then((m) => m || fetch(e.request).then((r) => {
        const cp = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, cp)); return r;
      }))
    );
  }
});
