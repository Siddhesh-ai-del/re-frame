import '@testing-library/jest-dom/vitest'

/**
 * Controllable `window.matchMedia` polyfill for jsdom.
 *
 * jsdom does not implement matchMedia; tests drive reduced-motion behavior by
 * calling `setMediaQuery()` (which also fires 'change' events on registered
 * listeners) and can assert listener hygiene with `listenerCount()`.
 */

type ChangeListener = (event: MediaQueryListEvent) => void

interface FakeMediaQueryList {
  media: string
  matches: boolean
  listeners: Set<ChangeListener>
}

const queries = new Map<string, FakeMediaQueryList>()

function queryFor(media: string): FakeMediaQueryList {
  let entry = queries.get(media)
  if (!entry) {
    entry = { media, matches: false, listeners: new Set() }
    queries.set(media, entry)
  }
  return entry
}

/**
 * Set the `matches` value for a media query and notify its 'change' listeners.
 */
export function setMediaQuery(media: string, matches: boolean): void {
  const entry = queryFor(media)
  entry.matches = matches
  const event = { matches, media } as MediaQueryListEvent
  for (const listener of [...entry.listeners]) {
    listener(event)
  }
}

/** Number of 'change' listeners currently registered for a media query. */
export function listenerCount(media: string): number {
  return queries.get(media)?.listeners.size ?? 0
}

/**
 * In-memory localStorage polyfill: this vitest+jsdom combination does not
 * expose window.localStorage. Deterministic per test via beforeEach clear.
 */
if (typeof window.localStorage === 'undefined') {
  const store = new Map<string, string>()
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string): string | null => store.get(key) ?? null,
      setItem: (key: string, value: string): void => {
        store.set(key, String(value))
      },
      removeItem: (key: string): void => {
        store.delete(key)
      },
      clear: (): void => {
        store.clear()
      },
      key: (index: number): string | null =>
        [...store.keys()][index] ?? null,
      get length(): number {
        return store.size
      },
    },
  })
}

window.matchMedia = (media: string): MediaQueryList => {
  const entry = queryFor(media)
  return {
    get media() {
      return entry.media
    },
    get matches() {
      return entry.matches
    },
    onchange: null,
    addEventListener: (
      type: string,
      listener: ChangeListener,
    ): void => {
      if (type === 'change') entry.listeners.add(listener)
    },
    removeEventListener: (
      type: string,
      listener: ChangeListener,
    ): void => {
      if (type === 'change') entry.listeners.delete(listener)
    },
    addListener: (listener: ChangeListener): void => {
      entry.listeners.add(listener)
    },
    removeListener: (listener: ChangeListener): void => {
      entry.listeners.delete(listener)
    },
    dispatchEvent: (): boolean => true,
  } as unknown as MediaQueryList
}

/**
 * jsdom's Blob is missing the async readers (text/arrayBuffer/slice) that the
 * platform provides; the JournalCard markdown-export test reads the Blob's
 * contents via .text(). This polyfill fills in just that reader — product code
 * sees a normal Blob.
 */
if (typeof Blob !== 'undefined' && typeof Blob.prototype.text !== 'function') {
  Object.defineProperty(Blob.prototype, 'text', {
    configurable: true,
    writable: true,
    value(this: Blob): Promise<string> {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(String(reader.result ?? ''))
        reader.onerror = () => reject(reader.error)
        reader.readAsText(this)
      })
    },
  })
}

/**
 * jsdom has no ResizeObserver; the liquid-glass lens (stage 6c) observes its
 * host box. This no-op stub keeps the real lib mountable in unit tests —
 * product code never sees a difference, and the reduced-effects fallback
 * path (no lib at all) is covered separately in GlassOrb.test.tsx.
 */
if (typeof globalThis.ResizeObserver === 'undefined') {
  class NoopResizeObserver {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  Object.defineProperty(globalThis, 'ResizeObserver', {
    configurable: true,
    value: NoopResizeObserver,
  })
}

beforeEach(() => {
  queries.clear()
  // Guarded: some jsdom versions don't populate localStorage on the global.
  window.localStorage?.clear()
  delete document.documentElement.dataset.reducedEffects
})
