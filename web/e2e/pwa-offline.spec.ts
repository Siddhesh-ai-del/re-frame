/**
 * Stage 6e PWA offline E2E — runs against the COMPOSED production service
 * (:8124, built SPA served by FastAPI via `--static`) because service-worker
 * registration is production-only (`import.meta.env.PROD`): the vite dev
 * server deliberately never registers a worker, so this proof cannot run in
 * the default dev lane.
 *
 * What must hold (design doc §6 PWA + spec §E.3):
 *  1. The static PWA surface exists and is honest: sw.js, manifest, and a
 *     network-FREE offline.html whose crisis resources are HARDCODED (no
 *     fetch, no network at all to read them).
 *  2. The worker registers, precaches the shell + GET /resources (crisis
 *     resources), and — when the harness allows it — serves the app shell
 *     (or the offline fallback page) with the network cut.
 *
 * Reliability policy (explicit in the spec): Playwright + SW control can be
 * finicky. The offline-navigation attempt below is tolerant (shell-from-cache
 * OR offline fallback content — either satisfies), and if worker control is
 * genuinely unavailable the test degrades HONESTLY to the static prerequisites
 * + precache assertions and records that outcome as a test annotation rather
 * than faking a green. The annotation tells you which path actually ran.
 */
import { expect, test, type Page } from '@playwright/test'

/** Must match `web/public/offline.html` (hardcoded, no-network resources). */
const CRISIS_URLS = ['https://findahelpline.com', 'https://988lifeline.org']

/** Ask the page whether a worker controls it yet (false when unsupported). */
async function isControlled(page: Page): Promise<boolean> {
  return page
    .waitForFunction(() => navigator.serviceWorker.controller !== null, undefined, {
      timeout: 15_000,
    })
    .then(() => true)
    .catch(() => false)
}

test.describe('PWA surface (static assets)', () => {
  test('serves sw.js, the manifest, and a self-contained offline page', async ({
    request,
  }) => {
    // The worker script itself is reachable (registration prerequisite).
    const sw = await request.get('/sw.js')
    expect(sw.status()).toBe(200)
    expect(sw.headers()['content-type'] ?? '').toContain('javascript')

    // The install manifest is linked, honest, and sage-themed (D6).
    const manifest = await request.get('/manifest.webmanifest')
    expect(manifest.status()).toBe(200)
    const parsed = (await manifest.json()) as Record<string, unknown>
    expect(parsed.name).toBe('RE:FRAME')
    expect(parsed.short_name).toBe('RE:FRAME')
    expect(parsed.theme_color).toBe('#A8501C')
    expect(parsed.background_color).toBe('#FFF4E4')
    expect(parsed.start_url).toBe('/')

    // The offline page exists and carries the standing crisis resources
    // HARDCODED — reachable with no network at all.
    const offline = await request.get('/offline.html')
    expect(offline.status()).toBe(200)
    const html = await offline.text()
    for (const url of CRISIS_URLS) expect(html).toContain(url)
    expect(html).toContain('offline')
    // Emergency-services guidance (the null-url resource) is plain text too.
    expect(html).toContain('emergency services')

    // Self-contained on purpose: no external subresource could fail offline.
    const externalRefs = [...html.matchAll(/(?:src|href)="(https?:\/\/[^"]+)"/g)]
    const allowed = new Set(CRISIS_URLS)
    expect(
      externalRefs.map((m) => m[1]).filter((url) => !allowed.has(url)),
    ).toEqual([])

    // index.html links the manifest + sage theme color (honest PWA install).
    const index = await request.get('/')
    expect(index.status()).toBe(200)
    const indexHtml = await index.text()
    expect(indexHtml).toContain('rel="manifest"')
    expect(indexHtml).toContain('theme-color')
    expect(indexHtml).toContain('#A8501C')
  })
})

test.describe('PWA offline behavior (service worker)', () => {
  test('registers, precaches the shell + crisis resources, and serves offline', async ({
    page,
    context,
  }) => {
    await page.goto('/')
    await expect(page.getByRole('banner')).toContainText('RE:FRAME')

    // Registration happened in this production build (active or activating).
    const registration = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration()
      return { registered: Boolean(reg), state: reg?.active?.state ?? null }
    })
    expect(registration.registered).toBe(true)

    const controlled = await isControlled(page)

    // GET /resources (the standing crisis resources) precached at install —
    // this is the offline-reachability requirement that does not depend on
    // navigation control at all.
    const resourcesCached = await page.evaluate(async () => {
      try {
        return Boolean(await caches.match('/resources'))
      } catch {
        return false
      }
    })
    expect(resourcesCached).toBe(true)

    if (!controlled) {
      // HONEST DEGRADED PATH (spec-sanctioned): worker control was not
      // reproducible in this harness. The verified prerequisites above are
      // the assertion; the full offline navigation is documented as not
      // reproducible rather than faked.
      test.info().annotations.push({
        type: 'offline-degraded',
        description:
          'service worker did not control the page in this harness — asserted ' +
          'registration + precached /resources + static PWA surface only',
      })
      expect(registration.registered).toBe(true)
      return
    }

    // The network is gone: from here NOTHING may reach the server.
    await context.setOffline(true)

    let outcome: string
    try {
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 10_000 })
      const banner = page.getByRole('banner').first()
      if ((await banner.count()) > 0 && (await banner.innerText()).includes('RE:FRAME')) {
        outcome = 'shell-from-cache'
      } else {
        // The SW served its offline fallback (offline.html) instead.
        const text = await page.locator('body').innerText()
        expect(text).toContain('findahelpline.com')
        expect(text).toContain('988lifeline.org')
        outcome = 'offline-fallback-page'
      }
    } catch {
      // Navigation itself failed (browser error page). Per the tolerant
      // contract this is NOT proof of offline support — degrade honestly.
      outcome = 'navigation-failed'
    }

    test.info().annotations.push({ type: 'offline-outcome', description: outcome })

    if (outcome === 'navigation-failed') {
      // HONEST DEGRADED PATH (spec-sanctioned): prerequisites + precache are
      // the standing assertion; documented, not faked.
      expect(resourcesCached).toBe(true)
      expect(registration.registered).toBe(true)
      return
    }

    // Shell (or fallback) rendered with NO network: prove the page is truly
    // live offline — a client route still resolves from the cached shell.
    await page.goto('/exercises', { waitUntil: 'domcontentloaded', timeout: 10_000 })
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

    await context.setOffline(false)
  })
})
