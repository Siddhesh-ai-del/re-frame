/**
 * Stage 6e axe-core accessibility pass: every route must be WCAG 2.2 AA-clean
 * with ZERO violations (design doc §5.5 — "axe-clean in E2E").
 *
 * Runs in the DEFAULT project against the dev frontend (keyless, proxied
 * backend on 8123). No allowlists: any violation found here is fixed in the
 * component itself — suppressing rules would defeat the purpose of the gate.
 */
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const ROUTES = [
  { path: '/welcome', name: 'onboarding' },
  { path: '/chat', name: 'chat' },
  { path: '/exercises', name: 'exercise library' },
  { path: '/check-ins', name: 'check-in dashboard' },
  { path: '/settings', name: 'settings' },
] as const

/** Render violations as readable strings so a failure names the exact node. */
function summarize(
  violations: Awaited<ReturnType<AxeBuilder['analyze']>>['violations'],
): string[] {
  return violations.map(
    (violation) =>
      `${violation.id} [${violation.impact ?? 'unknown'}] ${violation.help} — ` +
      violation.nodes.map((node) => node.target.join(' ')).join(' | '),
  )
}

for (const route of ROUTES) {
  test(`axe: zero violations on ${route.path} (${route.name})`, async ({ page }) => {
    await page.goto(route.path)
    // Wait for the shell (and route data) to settle before scanning.
    await expect(page.getByRole('navigation')).toBeVisible()
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()

    expect(summarize(results.violations)).toEqual([])
  })
}
