// sw.js  ──────────────────────────────────────────────
// A do-nothing service-worker so the browser registration
// succeeds and Flask no longer logs 404 for /sw.js.

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate',  () => self.clients.claim());
