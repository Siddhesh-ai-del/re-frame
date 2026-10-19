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
 */
const backendPort = process.env.E2E_BACKEND_PORT ?? '8123'
const backendOrigin = `http://127.0.0.1:${backendPort}`

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
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
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
  ],
})
