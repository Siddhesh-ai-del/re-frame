/**
 * Service-worker registration (stage 6e) — production browsers only.
 *
 * Contract (the reasons this module is separate from `main.tsx`):
 *  - NO-OP outside a production build: under vitest/jsdom `import.meta.env.PROD`
 *    is false and there is no `navigator.serviceWorker`, so tests and the dev
 *    server never register a worker (the dev shell references unbundled
 *    `/src/*` modules a precache could never serve).
 *  - NEVER throws: registration failures (insecure context, storage blocked,
 *    unsupported browser) are swallowed — the PWA affordance must never break
 *    the app shell that the failure would otherwise take down.
 *  - Registers `sw.js` at the app root scope; `public/sw.js` does the
 *    precaching (app shell + crisis resources) and the offline fallback.
 */

/** Worker script path (served verbatim from `web/public/`). */
export const SW_PATH = '/sw.js'

/** Scope: the whole origin root — the SPA owns every route. */
export const SW_SCOPE = '/'

/** Minimal injection seam so tests never need a real `ServiceWorkerContainer`. */
export interface RegisterSWOptions {
  /** Production flag; defaults to `import.meta.env.PROD`. */
  isProd?: boolean
  /** Container to register with; defaults to `navigator.serviceWorker`. */
  serviceWorker?: Pick<ServiceWorkerContainer, 'register'>
}

/**
 * Register the service worker when running as a production build in a
 * browser that supports it. Safe to call unconditionally from app entry:
 * it returns void, never throws, and does nothing in dev/test.
 */
export function registerServiceWorker(options: RegisterSWOptions = {}): void {
  const isProd = options.isProd ?? import.meta.env.PROD
  if (!isProd) return
  try {
    const container = options.serviceWorker ?? navigator.serviceWorker
    if (!container) return
    // Registration rejections are a normal outcome (http:// origin, disabled
    // storage): swallow them so no unhandled rejection ever surfaces.
    void Promise.resolve(container.register(SW_PATH, { scope: SW_SCOPE })).catch(
      () => undefined,
    )
  } catch {
    // Synchronous failures (sandboxed contexts, throwing getters) are equally
    // non-fatal: the app runs fine without a worker.
  }
}
