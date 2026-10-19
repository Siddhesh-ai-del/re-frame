import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

/**
 * Stage 6b safety E2E: keyless by design.
 *
 * Two webServers: the backend (reframe.cli in development mode — no LLM key,
 * so scripted routes like crisis bypass work while generated turns return an
 * honest 503) and the vite dev server (whose proxy forwards /chat POST,
 * /health, /instruments, /checkins to the API while GET /chat serves the SPA).
 *
 * Environment-safety notes (learned the hard way):
 *  - The readiness URL must be RE:FRAME-unique. An unrelated API server (the
 *    user's separate `saafscan` project) also answers 200 on /health, which
 *    fooled reuseExistingServer into testing the wrong backend. /resources
 *    exists only in RE:FRAME: a squatter on the port 404s it, Playwright
 *    starts our own server, and the bind failure surfaces loudly instead of
 *    silently corrupting results.
 *  - The dedicated default port (8123, not the CLI's 8000) exists because
 *    port 8000 is occupied on this machine; CI runners are fresh either way.
 *
 * Env overrides:
 *  - E2E_PYTHON: interpreter for the backend (CI uses system python after
 *    `pip install -e .`); locally the repo venv is used, with the package
 *    installed editable so `-m reframe.cli` resolves.
 *  - E2E_BACKEND_PORT: backend port. The vite dev server gets a matching
 *    REFRAME_API_TARGET so the proxy follows the port.
 *
 * Stage 6e additions — the COMPOSED production-like service:
 *  - A mock OpenAI-compatible provider (web/scripts/mock-llm-server.py) on
 *    8125 and a second RE:FRAME instance on 8124 started with `--static
 *    <web/dist>` that serves the BUILT SPA and the JSON API from ONE process
 *    (no dev server, no proxy) with the config overrides
 *    `REFRAME_LLM_BASE_URL` / `REFRAME_LLM_MODEL` pointed at the mock — so
 *    a genuinely generated reply reaches the UI without any real credential.
 *  - Projects: `chromium` (the 21 keyless specs + the axe a11y pass, dev
 *    frontend on 5373), `generated` (generated.spec.ts against :8124), and
 *    `pwa` (pwa-offline.spec.ts against :8124 — the service worker only
 *    registers in production builds, so the offline proof cannot run on the
 *    dev server where `import.meta.env.PROD` is false).
 */
const backendPort = process.env.E2E_BACKEND_PORT ?? '8123'
const backendOrigin = `http://127.0.0.1:${backendPort}`

/** Composed service (built SPA + API in one process) and its mock provider. */
const composedPort = '8124'
const composedOrigin = `http://127.0.0.1:${composedPort}`
const mockLlmPort = '8125'
const mockLlmOrigin = `http://127.0.0.1:${mockLlmPort}`

/** Absolute path to the built SPA (web/dist) for the `--static` mount. */
const builtSpaDir = fileURLToPath(new URL('./dist', import.meta.url))

export default defineConfig({
  testDir: './e2e',
  // Stage 6d: the check-in specs share ONE SQLite database (the backend
  // writes check-ins that later specs read and purge), so tests must not
  // interleave — serial execution across files and within each file.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5373',
  },
  projects: [
    {
      // Default lane: the 21 keyless specs (dev frontend, honest-503 flows)
      // plus the axe-core a11y pass. The two composed-service specs opt out
      // via testIgnore so this list stays "everything else" as specs grow.
      name: 'chromium',
      testIgnore: ['generated.spec.ts', 'pwa-offline.spec.ts'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      // Generated-turn proof against the composed :8124 service (static SPA
      // + API + mock provider) — no dev server, no proxy, no real key.
      name: 'generated',
      testMatch: 'generated.spec.ts',
      use: { ...devices['Desktop Chrome'], baseURL: composedOrigin },
    },
    {
      // PWA offline proof: also against :8124, because a production build is
      // where the service worker registers at all.
      name: 'pwa',
      testMatch: 'pwa-offline.spec.ts',
      use: { ...devices['Desktop Chrome'], baseURL: composedOrigin },
    },
  ],
  webServer: [
    {
      // cwd is the repo root; the default venv path is relative to it.
      command: `${process.env.E2E_PYTHON ?? '.venv/bin/python'} -m reframe.cli --port ${backendPort} --db /tmp/reframe-e2e.db`,
      cwd: '..',
      // RE:FRAME-unique route — see the safety note above.
      url: `${backendOrigin}/resources`,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5373',
      reuseExistingServer: !process.env.CI,
      env: { REFRAME_API_TARGET: backendOrigin },
    },
    {
      // Stage 6e: tiny mock OpenAI-compatible provider (stdlib only).
      // cwd is the repo root so the default venv path resolves, like the
      // backend entry above.
      command: `${process.env.E2E_PYTHON ?? '.venv/bin/python'} web/scripts/mock-llm-server.py --port ${mockLlmPort}`,
      cwd: '..',
      url: `${mockLlmOrigin}/health`,
      reuseExistingServer: !process.env.CI,
    },
    {
      // Stage 6e: the composed service — BUILT SPA (web/dist via --static)
      // and JSON API in ONE process, generation wired to the mock provider
      // through the config overrides. Readiness uses /resources (RE:FRAME-
      // unique) so a port squatter 404s instead of poisoning the lane.
      // Requires `npm run build` first (CI builds before e2e; locally the
      // full-suite gate builds too).
      command: `${process.env.E2E_PYTHON ?? '.venv/bin/python'} -m reframe.cli --static ${builtSpaDir} --port ${composedPort} --db /tmp/reframe-e2e-static.db`,
      cwd: '..',
      url: `${composedOrigin}/resources`,
      reuseExistingServer: !process.env.CI,
      env: {
        REFRAME_API_KEY: 'test-mock-key',
        REFRAME_LLM_BASE_URL: mockLlmOrigin,
        REFRAME_LLM_MODEL: 'mock-model',
      },
    },
  ],
})
