// Boys Center — Service Worker
// Cache-first for static assets; network-first with offline fallback for HTML.

const VERSION = 'bc-v5';
const STATIC_CACHE = `bc-static-${VERSION}`;
const RUNTIME_CACHE = `bc-runtime-${VERSION}`;

// App shell — cached on install
const PRECACHE_URLS = [
  '/static/img/bc-icon-192.png',
  '/static/img/bc-icon-512.png',
  '/static/img/bc-icon.svg',
  '/static/pwa/manifest.webmanifest',
  '/static/pwa/offline.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== STATIC_CACHE && k !== RUNTIME_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Helpers — decide strategy based on request
function isHTML(req) {
  return req.headers.get('accept')?.includes('text/html');
}
function isStatic(url) {
  return url.pathname.startsWith('/static/')
      || url.pathname.startsWith('/media/');
}
function isAPI(url) {
  return url.pathname.startsWith('/quiz/answer')
      || url.pathname.startsWith('/attendance/api/');
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;  // never cache POSTs

  const url = new URL(req.url);

  // Same-origin only
  if (url.origin !== self.location.origin) return;

  // POST/api endpoints — always go to network, no caching
  if (isAPI(url)) return;

  // Static/media — cache-first
  if (isStatic(url)) {
    event.respondWith(cacheFirst(req));
    return;
  }

  // HTML — network-first with offline fallback
  if (isHTML(req)) {
    event.respondWith(networkFirst(req));
    return;
  }

  // Everything else — try network, fall back to cache
  event.respondWith(staleWhileRevalidate(req));
});

async function cacheFirst(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(req, res.clone());
    }
    return res;
  } catch (e) {
    return cached || Response.error();
  }
}

async function networkFirst(req) {
  try {
    const res = await fetch(req);
    if (res.ok) {
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(req, res.clone());
    }
    return res;
  } catch (e) {
    const cached = await caches.match(req);
    if (cached) return cached;
    // Offline fallback page
    return caches.match('/static/pwa/offline.html');
  }
}

async function staleWhileRevalidate(req) {
  const cached = await caches.match(req);
  const network = fetch(req).then((res) => {
    if (res.ok) {
      caches.open(RUNTIME_CACHE).then((cache) => cache.put(req, res.clone()));
    }
    return res;
  }).catch(() => cached);
  return cached || network;
}

// Listen for SKIP_WAITING from the page (used when prompting users to reload)
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
