/* Sentinel PWA Service Worker v1.0
 * - Precache app shell on install
 * - Network-first for API (fallback to cache when offline)
 * - Stale-while-revalidate for static assets
 * - Cache busting on new versions
 */
const VERSION = 'sentinel-pwa-v1.0'
const SHELL_CACHE = `${VERSION}-shell`
const API_CACHE = `${VERSION}-api`

const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable-512.png',
  '/apple-touch-icon.png',
]

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(SHELL_CACHE)
      .then((c) => c.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((k) => !k.startsWith(VERSION))
          .map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  const req = e.request
  const url = new URL(req.url)

  // Same-origin only for SW handling
  if (url.origin !== self.location.origin) return

  // Navigation requests: network-first, fall back to cached shell
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone()
          caches.open(SHELL_CACHE).then((c) => c.put('/index.html', copy))
          return res
        })
        .catch(() => caches.match('/index.html'))
    )
    return
  }

  // API requests: network-first, fall back to cached response
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone()
            caches.open(API_CACHE).then((c) => c.put(req, copy))
          }
          return res
        })
        .catch(async () => {
          const cached = await caches.match(req)
          if (cached) return cached
          return new Response(JSON.stringify({ offline: true, error: 'You are offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          })
        })
    )
    return
  }

  // Static assets: stale-while-revalidate
  e.respondWith(
    caches.match(req).then((cached) => {
      const refresh = fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone()
            caches.open(SHELL_CACHE).then((c) => c.put(req, copy))
          }
          return res
        })
        .catch(() => cached)
      return cached || refresh
    })
  )
})

self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting()
})
