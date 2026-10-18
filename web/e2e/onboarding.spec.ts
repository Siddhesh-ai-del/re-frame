/**
 * Stage 6c onboarding E2E (keyless by design — no LLM key in CI).
 *
 * Proves what the unit layer cannot, in a real browser:
 *  1. First-run redirect: a fresh context (Playwright per-test contexts start
 *     with empty localStorage) landing on `/` is sent to /welcome, and
 *     /welcome renders the onboarding heading.
 *  2. Keyboard-only onboarding: Tab from the top of the document to the
 *     "Get started" CTA and activate it with Enter — landing on /chat with
 *     `reframe:onboarded` set. No mouse involved.
 *  3. Reduced-motion contract: with `prefers-reduced-motion` emulated, <html>
 *     carries data-reduced-effects="true", the TextReel renders its final
 *     headline STATIC on first paint (no per-word churn), and the GlassOrb
 *     renders the static frosted fallback instead of the liquid-glass lens.
 *
 * Assertions never depend on model-generated text. chat.spec.ts is untouched.
 */
import { expect, test } from '@playwright/test'

const ONBOARDED_KEY = 'reframe:onboarded'
const FINAL_HEADLINE = 'A calmer way to begin.'

test.describe('first-run redirect (never a gate)', () => {
  test('a fresh visitor on / is redirected to /welcome and sees the heading', async ({
    page,
  }) => {
    // Per-test contexts start with empty localStorage — a true first run.
    await page.goto('/')

    await expect(page).toHaveURL(/\/welcome$/)
    await expect(page.getByRole('heading', { name: 'Welcome', level: 1 })).toBeVisible()
    // The honest framing is present on the onboarding screen.
    await expect(page.getByRole('heading', { name: 'What this is', exact: true })).toBeVisible()
  })

  test('a deep link bypasses onboarding entirely (never a gate)', async ({ page }) => {
    // Landing straight on /chat must work regardless of the onboarding flag.
    await page.goto('/chat')

    await expect(page).toHaveURL(/\/chat$/)
    await expect(page.getByRole('heading', { name: 'Chat', level: 1 })).toBeVisible()
  })
})

test.describe('keyboard-only onboarding', () => {
  test('Tab to "Get started" and press Enter -> /chat with the flag set', async ({
    page,
  }) => {
    await page.goto('/')

    // Tab forward until focus lands on the CTA. The nav links precede it in
    // the tab order; a bounded loop keeps this robust to small markup shifts.
    const cta = page.getByRole('button', { name: 'Get started' })
    for (let i = 0; i < 12; i += 1) {
      await page.keyboard.press('Tab')
      if (await cta.evaluate((el) => el === document.activeElement)) break
    }
    await expect(cta).toBeFocused()

    await page.keyboard.press('Enter')

    await expect(page).toHaveURL(/\/chat$/)
    // The onboarding flag is recorded so the next visit is not redirected.
    expect(await page.evaluate((key) => window.localStorage.getItem(key), ONBOARDED_KEY)).toBe(
      '1',
    )
  })
})

test.describe('reduced-motion contract', () => {
  test.use({ reducedMotion: 'reduce' })

  test('renders static TextReel + frosted GlassOrb fallback under reduced motion', async ({
    page,
  }) => {
    await page.goto('/')

    // The engine mirrors the resolved decision onto <html> for CSS gating.
    await expect(page.locator('html')).toHaveAttribute('data-reduced-effects', 'true')

    // TextReel: the final headline is static on first paint (no word churn) —
    // data-static is set and the settled text is visible immediately.
    const reel = page.getByTestId('text-reel')
    await expect(reel).toHaveAttribute('data-static', 'true')
    await expect(reel).toContainText(FINAL_HEADLINE)

    // GlassOrb: the static frosted fallback renders (no liquid-glass lens).
    const orb = page.getByTestId('glass-orb')
    await expect(orb).toBeVisible()
    await expect(orb).toHaveAttribute('data-fallback', 'frosted')
  })
})
