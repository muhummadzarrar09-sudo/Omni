/* OMNI Mobile PWA — Service Worker
 * Caches the shell so the app loads fast and works offline.
 * Never caches WebSocket or API responses.
 */
const CACHE_NAME = 'omni-mobile-v1';
const SHELL = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Never intercept WebSocket or cross-origin API calls
  if (req.method !== 'GET') return;
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;

  // Network-first for API, cache-first for shell
  if (url.origin === self.location.origin) {
    // Same-origin: cache-first with network fallback
    event.respondWith(
      caches.match(req).then((cached) => {
        const fetched = fetch(req).then((resp) => {
          if (resp && resp.status === 200 && resp.type === 'basic') {
            const copy = resp.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copy));
          }
          return resp;
        }).catch(() => cached);
        return cached || fetched;
      })
    );
  }
  // Cross-origin: pass through (don't cache)
});
