/**
 * Stage 6e: service-worker registration is production-only, browser-only,
 * and must NEVER throw — a PWA affordance can never break the app shell.
 *
 * Under vitest/jsdom there is no real service worker support and
 * `import.meta.env.PROD` is false, so the default call path must be a
 * no-op; the registration path is exercised through the injected
 * `serviceWorker` option (and a stubbed navigator).
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SW_PATH, SW_SCOPE, registerServiceWorker } from './registerSW'

/** Loose mock impls (any arity/return) cast into the container's register slot. */
function makeContainer(registerImpl: unknown): Pick<ServiceWorkerContainer, 'register'> {
  return { register: registerImpl as ServiceWorkerContainer['register'] }
}

describe('registerServiceWorker', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('exposes the worker path and root scope as constants', () => {
    expect(SW_PATH).toBe('/sw.js')
    expect(SW_SCOPE).toBe('/')
  })

  it('is a no-op outside production even when a container is present', () => {
    const register = vi.fn()
    registerServiceWorker({ isProd: false, serviceWorker: makeContainer(register) })
    expect(register).not.toHaveBeenCalled()
  })

  it('is a no-op when no explicit flag is given (import.meta.env.PROD is false under vitest)', () => {
    const register = vi.fn()
    registerServiceWorker({ serviceWorker: makeContainer(register) })
    expect(register).not.toHaveBeenCalled()
  })

  it('registers the worker at /sw.js with the root scope in production', () => {
    const register = vi.fn().mockResolvedValue(undefined)
    registerServiceWorker({ isProd: true, serviceWorker: makeContainer(register) })

    expect(register).toHaveBeenCalledTimes(1)
    expect(register).toHaveBeenCalledWith(SW_PATH, { scope: SW_SCOPE })
  })

  it('is a no-op when the browser has no serviceWorker support', () => {
    // jsdom's navigator has no serviceWorker member: the default lookup
    // must resolve to "unsupported" and simply do nothing.
    expect(() =>
      registerServiceWorker({ isProd: true, serviceWorker: undefined }),
    ).not.toThrow()
  })

  it('falls back to navigator.serviceWorker when no container is injected', () => {
    const register = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { serviceWorker: { register } })

    registerServiceWorker({ isProd: true })

    expect(register).toHaveBeenCalledWith(SW_PATH, { scope: SW_SCOPE })
  })

  it('never throws when registration rejects', async () => {
    const register = vi.fn().mockRejectedValue(new Error('insecure context'))

    expect(() =>
      registerServiceWorker({ isProd: true, serviceWorker: makeContainer(register) }),
    ).not.toThrow()

    // The rejection must be swallowed, not surfaced as an unhandled rejection.
    await new Promise((resolve) => setTimeout(resolve, 0))
  })

  it('never throws when register throws synchronously', () => {
    const register = vi.fn(() => {
      throw new Error('blocked by policy')
    })

    expect(() =>
      registerServiceWorker({ isProd: true, serviceWorker: makeContainer(register) }),
    ).not.toThrow()
  })

  it('tolerates a container whose register returns a non-promise', () => {
    const register = vi.fn(() => undefined)

    expect(() =>
      registerServiceWorker({ isProd: true, serviceWorker: makeContainer(register) }),
    ).not.toThrow()
    expect(register).toHaveBeenCalledWith(SW_PATH, { scope: SW_SCOPE })
  })

  it('swallows a navigator lookup that throws (sandboxed contexts)', () => {
    vi.stubGlobal('navigator', {
      get serviceWorker(): never {
        throw new Error('blocked')
      },
    })

    expect(() => registerServiceWorker({ isProd: true })).not.toThrow()
  })
})
