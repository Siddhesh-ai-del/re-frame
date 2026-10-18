import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import type { ProxyOptions } from 'vite'
import { defineConfig } from 'vitest/config'

/** Overridable so E2E can point the proxy at a non-default backend port. */
const API_TARGET = process.env.REFRAME_API_TARGET ?? 'http://127.0.0.1:8000'

/**
 * The SPA route `/chat` and the API endpoint `POST /chat` collide on the same
 * path. The dev proxy resolves it by METHOD: POST (and other non-GET verbs)
 * proxy to the API, while GET/HEAD fall through to the SPA shell via the
 * bypass hook (which rewrites the request URL to /index.html and lets vite's
 * own middleware serve it — verified live by the E2E collision test).
 */
const chatProxy: ProxyOptions = {
  target: API_TARGET,
  bypass: (req) => {
    if (req.method === 'GET' || req.method === 'HEAD') {
      return '/index.html'
    }
    return undefined
  },
}

/** API prefixes proxied unconditionally (prefix match covers /checkins/{id}). */
const API_PREFIXES = ['/health', '/instruments', '/checkins', '/resources'] as const

const proxy: Record<string, ProxyOptions> = {
  '/chat': chatProxy,
  ...Object.fromEntries(
    API_PREFIXES.map((prefix) => [prefix, { target: API_TARGET }]),
  ),
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The repository directory name ("RE:FRAME") contains a colon, which
    // breaks vite's fs allow-list path parsing; relax the check (localhost
    // dev server only) so vitest/vite can load files under this root.
    fs: { strict: false },
    // Bind explicitly to IPv4 localhost: vite's default "::1"-only binding
    // makes http://127.0.0.1:5373 unreachable (Playwright's readiness check
    // and API base URL both use 127.0.0.1). A dedicated, strict port keeps a
    // stray dev server from being silently reused by E2E on another app's
    // default port.
    host: '127.0.0.1',
    port: 5373,
    strictPort: true,
    proxy,
  },
  // Same map for `vite preview` of the production build (harmless, useful
  // when previewing against a locally running API).
  preview: { proxy },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Playwright specs live in e2e/ — vitest must not collect them.
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        '**/*.test.*',
        'src/main.tsx',
        'src/test/**',
        'src/api/schema.d.ts',
      ],
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
    },
  },
})
