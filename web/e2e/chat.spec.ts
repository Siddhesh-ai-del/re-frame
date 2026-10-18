/**
 * Stage 6b safety E2E (keyless by design — no LLM key in CI).
 *
 * These tests prove three things the unit layer cannot:
 *  1. Route collision: GET /chat serves the SPA (not a 405/404) while the
 *     UI-sent POST /chat reaches the API through the same dev proxy.
 *  2. The crisis path NEVER touches the model: a scripted crisis reply comes
 *     back with the assertive banner and real resources, and no unavailable
 *     notice ever appears (the keyless 503 would expose any model call).
 *  3. The generated path fails HONESTLY without a key: the 503 surfaces as
 *     the fixed unavailable notice plus reachable crisis resources.
 *
 * Assertions never depend on model-generated text.
 */
import { expect, test } from '@playwright/test'

const CRISIS_BANNER_TEXT =
  'Immediate support matters right now. The resources below are free and available now.'

test.describe('chat route collision', () => {
  test('GET /chat renders the SPA app shell', async ({ page }) => {
    const response = await page.goto('/chat')

    // The SPA served index.html — not the API's 405/404 for GET /chat.
    expect(response?.status()).toBe(200)
    await expect(page.getByRole('banner')).toContainText('RE:FRAME')
    await expect(page.getByRole('navigation')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Chat', level: 1 })).toBeVisible()
  })
})

test.describe('crisis bypass (scripted, model never called)', () => {
  test('crisis message shows banner, resources, and scripted reply — and stays sticky', async ({
    page,
  }) => {
    await page.goto('/chat')

    await page.getByLabel('Message').fill('I want to kill myself')
    await page.getByRole('button', { name: 'Send' }).click()

    // Assertive banner + real resources from the scripted crisis route.
    const banner = page.getByRole('alert')
    await expect(banner).toContainText(CRISIS_BANNER_TEXT)
    const resources = page.getByRole('region', {
      name: 'Crisis support resources',
    })
    await expect(resources.getByRole('link')).toHaveCount(2)
    await expect(
      resources.getByRole('link', { name: /Find A Helpline/ }),
    ).toHaveAttribute('href', 'https://findahelpline.com')
    await expect(
      resources.getByRole('link', { name: /988 Suicide/ }),
    ).toHaveAttribute('href', 'https://988lifeline.org')
    // Non-linkable guidance is rendered as text.
    await expect(resources.getByText(/contact your local emergency services/)).toBeVisible()

    // Scripted crisis reply is visible (fixed backend copy, not model output).
    await expect(
      page.getByText(/I'm a wellness companion, not a crisis service/),
    ).toBeVisible()

    // The model path was never taken: a keyless generated turn would 503 and
    // surface the unavailable notice. It must NOT be here.
    await expect(
      page.getByText('The assistant is unavailable right now. You can still reach crisis support below.'),
    ).toHaveCount(0)

    // Sticky escalation: a later non-crisis send keeps the banner + resources.
    await page.getByLabel('Message').fill('thank you')
    await page.getByRole('button', { name: 'Send' }).click()
    // This send goes down the generated path → 503 → unavailable notice.
    await expect(
      page.getByText('The assistant is unavailable right now. You can still reach crisis support below.'),
    ).toBeVisible()
    // But the crisis escalation persists (fail-closed).
    await expect(page.getByRole('alert')).toContainText(CRISIS_BANNER_TEXT)
    await expect(
      resources.getByRole('link', { name: /988 Suicide/ }),
    ).toBeVisible()
  })
})

test.describe('generated path without a key (honest 503)', () => {
  test('a normal message surfaces the unavailable notice with reachable resources', async ({
    page,
  }) => {
    await page.goto('/chat')

    await page
      .getByLabel('Message')
      .fill('I keep replaying an argument in my head')
    await page.getByRole('button', { name: 'Send' }).click()

    // Honest degraded state: fixed notice + best-effort GET /resources.
    await expect(
      page.getByText('The assistant is unavailable right now. You can still reach crisis support below.'),
    ).toBeVisible()
    const resources = page.getByRole('region', {
      name: 'Crisis support resources',
    })
    await expect(resources.getByRole('link').first()).toBeVisible()
    // No crisis banner — the generated path never produced a crisis route.
    await expect(page.getByRole('alert')).toHaveCount(0)
  })
})
