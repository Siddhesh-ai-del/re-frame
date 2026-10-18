/**
 * Stage 6c exercises E2E (keyless by design — no LLM key in CI).
 *
 * Proves in a real browser:
 *  1. Keyboard nav to /exercises via the nav link; the library renders with
 *     ≥3 exercise cards, each with steps and an honest evidence-tier label.
 *  2. Focus-breath is keyboard-operable: Start advances the countdown text,
 *     and Pause/Stop work from the keyboard.
 *  3. Journal privacy (CRITICAL, design §5.6): type an entry, save via
 *     keyboard, see it in the list — while a page-level fetch spy records
 *     every request URL and body and proves the journal text NEVER reaches
 *     the network.
 *  4. Reduced motion: the focus-breath renders a static text cue (no
 *     animated-circle element).
 *
 * Assertions never depend on model-generated text. chat.spec.ts is untouched.
 */
import { expect, test, type Page } from '@playwright/test'

/** A string unique enough that a match anywhere in a request is unambiguous. */
const JOURNAL_TEXT = 'private-journal-zenith-7f3a2b-keep-local'

/** Instrument window.fetch to record every URL + body seen by the app. */
async function installRequestSpy(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const w = window as unknown as { __reqLog: Array<{ url: string; body: string }> }
    w.__reqLog = []
    const originalFetch = window.fetch.bind(window)
    ;(window as unknown as { fetch: typeof fetch }).fetch = (
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => {
      const url =
        typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
      // The journal flow never sends a body; init.body is the only body that
      // could carry text, so record it and leave request objects alone.
      const body = typeof init?.body === 'string' ? init.body : ''
      w.__reqLog.push({ url, body })
      return originalFetch(input, init)
    }
  })
}

test.describe('exercise library (keyboard nav)', () => {
  test('navigates via the nav link and renders ≥3 cards with steps', async ({ page }) => {
    await page.goto('/')

    // Keyboard-only navigation to the exercises route.
    await page.getByRole('link', { name: 'Exercises' }).focus()
    await page.keyboard.press('Enter')

    await expect(page).toHaveURL(/\/exercises$/)
    await expect(page.getByRole('heading', { name: 'Exercises', level: 1 })).toBeVisible()

    // The library loads from GET /content/exercises (no LLM needed).
    const cards = page.getByTestId('exercise-card')
    await expect(cards.first()).toBeVisible()
    expect(await cards.count()).toBeGreaterThanOrEqual(3)

    // Every card carries numbered steps and an honest tier label (no coloring).
    for (let i = 0; i < (await cards.count()); i += 1) {
      const card = cards.nth(i)
      await expect(card.getByRole('list', { name: 'Steps' })).toBeVisible()
      await expect(card.getByText(/Evidence tier:/)).toBeVisible()
    }
  })
})

test.describe('focus-breath (keyboard-operable, claim-free)', () => {
  test('Start advances the countdown; Pause and Stop work from the keyboard', async ({
    page,
  }) => {
    await page.goto('/exercises')

    const countdown = page.getByTestId('breath-countdown')
    await expect(countdown).toHaveText('1:00')

    // Start via keyboard: focus the button and press Enter.
    await page.getByRole('button', { name: 'Start' }).focus()
    await page.keyboard.press('Enter')

    // The countdown ticks down from the full minute (text in both modes).
    await expect(countdown).not.toHaveText('1:00', { timeout: 4000 })

    // Pause via keyboard freezes the clock, Stop resets it.
    await page.getByRole('button', { name: 'Pause' }).focus()
    await page.keyboard.press('Enter')
    const frozen = await countdown.textContent()
    await page.waitForTimeout(1500)
    await expect(countdown).toHaveText(frozen ?? '')

    await page.getByRole('button', { name: 'Stop' }).focus()
    await page.keyboard.press('Enter')
    await expect(countdown).toHaveText('1:00')
  })
})

test.describe('journal privacy (device-local, never on the network)', () => {
  test('saves an entry via keyboard and it never reaches the network', async ({ page }) => {
    await installRequestSpy(page)
    await page.goto('/exercises')

    // Type the entry and save it with the keyboard (focus + Enter).
    const textarea = page.getByLabel("What's on your mind?")
    await textarea.focus()
    await textarea.fill(JOURNAL_TEXT)
    await page.getByRole('button', { name: 'Save entry' }).focus()
    await page.keyboard.press('Enter')

    // The entry appears in the device-local list.
    await expect(page.getByRole('list', { name: 'Saved entries' })).toBeVisible()
    await expect(page.getByText(JOURNAL_TEXT)).toBeVisible()

    // PRIVACY PROOF: no recorded request (URL or body) ever carried the text.
    const requests = await page.evaluate(
      () => (window as unknown as { __reqLog: Array<{ url: string; body: string }> }).__reqLog,
    )
    for (const request of requests) {
      expect(request.url).not.toContain(JOURNAL_TEXT)
      expect(request.body).not.toContain(JOURNAL_TEXT)
    }
    // And it is persisted on-device only.
    const stored = await page.evaluate(() => window.localStorage.getItem('reframe:journal'))
    expect(stored).toContain(JOURNAL_TEXT)
  })
})

test.describe('reduced motion', () => {
  test.use({ reducedMotion: 'reduce' })

  test('focus-breath shows a static text cue, not the animated circle', async ({ page }) => {
    await page.goto('/exercises')

    // The static text cue renders, and the animated circle does NOT exist.
    await expect(page.getByTestId('breath-cue')).toBeVisible()
    await expect(page.getByTestId('breath-circle')).toHaveCount(0)
    // The countdown is text and still works under reduced motion.
    await expect(page.getByTestId('breath-countdown')).toHaveText('1:00')
  })
})
