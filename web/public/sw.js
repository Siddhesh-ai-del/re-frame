/* RE:FRAME service worker (stage 6e).
 *
 * Strategy (deliberately small and pure — it is NOT unit-testable in jsdom,
 * so it is covered by the pwa-offline E2E spec instead):
 *  - install:    precache the app shell ('/', '/index.html') as MANDATORY,
 *                best-effort the offline fallback page, manifest, icon, and
 *                GET /resources (the standing crisis resources) so they are
 *                reachable with no network at all.
 *  - fetch:      navigations are network-first (fresh shell when online)
 *                with a cache fallback: exact URL -> cached shell ->
 *                offline.html. Same-origin GET assets are cache-first
 *                (hashed files are immutable) and fill the runtime cache
 *                during normal browsing.
 *  - activate:   delete caches this version doesn't own, then claim clients.
 *
 * SW_VERSION must be bumped whenever the precache list or strategy changes.
 */
'use strict'

const SW_VERSION = 'reframe-v1'
const SHELL_CACHE = SW_VERSION + '-shell'
const RUNTIME_CACHE = SW_VERSION + '-runtime'
const CACHE_PREFIX = SW_VERSION + '-'

/** Mandatory shell entries: install FAILS (and the PWA simply never
 *  registers) if these cannot be fetched — a broken shell must not be
 *  precached as "working". */
const SHELL_URLS = ['/', '/index.html']

/** Best-effort entries: fetched during install but never failing it. */
const PRECACHE_URLS = [
  '/offline.html',
  '/manifest.webmanifest',
  '/icon.svg',
  '/resources',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL_CACHE)
      await cache.addAll(SHELL_URLS)
      await Promise.all(
        PRECACHE_URLS.map(async (url) => {
          try {
            const response = await fetch(url, { cache: 'reload' })
            if (response.ok) await cache.put(url, response)
          } catch {
            // Best-effort: the offline fallback chain still works without it.
          }
        }),
      )
      await self.skipWaiting()
    })(),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys()
      await Promise.all(
        keys
          .filter((key) => !key.startsWith(CACHE_PREFIX))
          .map((key) => caches.delete(key)),
      )
      await self.clients.claim()
    })(),
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return
  if (new URL(request.url).origin !== self.location.origin) return

  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(request))
    return
  }
  event.respondWith(handleAsset(request))
})

/** Network-first navigation with the offline chain: exact -> shell -> page. */
async function handleNavigation(request) {
  let response
  try {
    response = await fetch(request)
  } catch {
    return offlineNavigation(request)
  }
  if (response.ok) {
    // Keep the precached shell fresh for the next offline visit; a cache
    // failure must never replace the FRESH response we already hold.
    try {
      const isHtml = (response.headers.get('content-type') || '').includes('text/html')
      if (isHtml) {
        const shell = await caches.open(SHELL_CACHE)
        await shell.put('/index.html', response.clone())
        await shell.put('/', response.clone())
      }
    } catch {
      // Quota/security failures only cost freshness, not the response.
    }
  }
  return response
}

/** Serve offline: exact URL, then the precached shell, then offline.html. */
async function offlineNavigation(request) {
  const exact = await caches.match(request)
  if (exact) return exact
  const shell = (await caches.match('/')) || (await caches.match('/index.html'))
  if (shell) return shell
  const offline = await caches.match('/offline.html')
  if (offline) return offline
  // Last resort (nothing cached at all): a minimal honest message.
  return new Response("You're offline and no cached page is available.", {
    status: 503,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}

/** Cache-first for same-origin GETs (hashed assets, /resources, icons). */
async function handleAsset(request) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(RUNTIME_CACHE)
      await cache.put(request, response.clone())
    }
    return response
  } catch {
    // Honest failure: the page sees a network error, never a wrong file.
    return Response.error()
  }
}
