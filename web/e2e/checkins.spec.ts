/**
 * Stage 6d check-ins E2E (keyless by design — no LLM key in CI).
 *
 * Proves in a real browser, against the live dev-mode backend:
 *
 *  1. Keyboard completion of the full PHQ-9 (all nine items answered with
 *     option value 0 → total 0 → the published "minimal" band), submit via
 *     Enter, the honest result (score + published label + verbatim citation,
 *     NO risk coloring), the "Check-in saved." toast, and the dashboard
 *     status bar reflecting the new check-in.
 *  2. Item-9 escalation: the SAME form with item 9 = "Nearly every day"
 *     routes to the crisis tier — the API's scripted crisis message is
 *     rendered VERBATIM as role="alert", the crisis banner appears, and the
 *     always-visible support resources (≥3, incl. findahelpline.com) show.
 *     The escalation is NOT toast-only: the alert outlives the 4s toast.
 *  3. History: two recorded check-ins produce two trend-chart points (the
 *     accessible text alternative lists both) and the progress ring shows
 *     the most recent total + published label.
 *
 * Serial by design (test.describe.serial): the three tests share ONE SQLite
 * database and build on each other, exactly like a real session would.
 * Assertions never depend on model-generated text.
 */
import { expect, test, type Page } from '@playwright/test'

/** The scripted crisis wording (crisis_response_v1) — verbatim fragment. */
const CRISIS_FRAGMENT =
  "I'm a wellness companion, not a crisis service, so I can't help with a crisis moment."

/** Answer one PHQ-9 item by keyboard: focus its option radio, press Space. */
async function answerByKeyboard(page: Page, item: number, value: number): Promise<void> {
  const radio = page.locator(`#checkin-item-${item}-opt-${value}`)
  await radio.focus()
  await page.keyboard.press('Space')
}

test.describe.serial('check-ins dashboard (PHQ-9)', () => {
  test('completes the PHQ-9 by keyboard, submits, and shows the honest result', async ({
    page,
  }) => {
    // Keyboard-only navigation from the shell to the dashboard.
    await page.goto('/')
    await page.getByRole('link', { name: 'Check-ins' }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/check-ins$/)

    // Pick PHQ-9 explicitly (it is preselected as the first instrument, but
    // the picker must be operable, not decorative).
    const phq9 = page.getByRole('button', { name: /PHQ-9/ })
    await phq9.click()
    await expect(phq9).toHaveAttribute('aria-pressed', 'true')

    // The form is gated: nine unanswered items → submit disabled.
    const submit = page.getByRole('button', { name: 'Save check-in' })
    await expect(submit).toBeDisabled()

    // Read today's date FROM the form (the authority on what gets submitted)
    // so the status-bar assertion below cannot drift on timezone.
    const formDate = (await page.locator('form .tabular-nums').first().textContent()) ?? ''
    expect(formDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)

    // Answer all nine items with option 0 — keyboard only.
    for (let item = 1; item <= 9; item += 1) {
      await answerByKeyboard(page, item, 0)
    }

    // Every item answered → the gate opens; Enter on the form submits.
    await expect(submit).toBeEnabled()
    await page.keyboard.press('Enter')

    // Honest result: instrument score, PUBLISHED label, verbatim citation.
    const result = page.getByRole('region', { name: 'Check-in result' })
    await expect(result).toBeVisible()
    // The big tabular-numeral total is exactly 0 (all-zero responses).
    await expect(result.locator('.text-3xl')).toHaveText('0')
    await expect(result).toContainText('minimal')
    await expect(result.getByText(/Kroenke, Spitzer & Williams/)).toBeVisible()

    // The designed non-critical toast fires for every saved check-in.
    await expect(page.getByText('Check-in saved.')).toBeVisible()

    // The dashboard status bar reflects the new check-in immediately.
    const status = page.getByRole('region', { name: 'Dashboard status' })
    await expect(status).toContainText('Most recent check-in')
    await expect(status).toContainText(formDate)
    await expect(status).toContainText(/Patient Health Questionnaire-9 \(PHQ-9\)/)

    // Back to the form for the next check-in.
    await page.getByRole('button', { name: /done/i }).click()
    await expect(page.getByRole('form', { name: /Check-in form for/ })).toBeVisible()
  })

  test('item 9 escalation renders the scripted crisis message as an alert with resources', async ({
    page,
  }) => {
    await page.goto('/check-ins')

    // All items 0 EXCEPT item 9 = 3 ("Nearly every day").
    for (let item = 1; item <= 8; item += 1) {
      await answerByKeyboard(page, item, 0)
    }
    await answerByKeyboard(page, 9, 3)
    await page.keyboard.press('Enter')

    // The API's scripted crisis message, rendered VERBATIM as the alert.
    const alert = page.getByRole('alert')
    await expect(alert).toBeVisible()
    await expect(alert).toContainText(CRISIS_FRAGMENT)

    // Crisis-banner treatment + always-visible support resources.
    await expect(page.getByTestId('crisis-banner')).toBeVisible()
    const resources = page.getByRole('region', { name: 'Crisis support resources' })
    const findAHelpline = resources.getByRole('link', { name: /Find A Helpline/ })
    await expect(findAHelpline).toBeVisible()
    await expect(findAHelpline).toHaveAttribute('href', 'https://findahelpline.com')
    await expect(resources.getByRole('link', { name: /988 Suicide/ })).toBeVisible()
    // The third resource is non-linkable guidance (scoped to the panel — the
    // verbatim alert message also mentions emergency services).
    await expect(
      resources.getByText(/contact your local emergency services/i),
    ).toBeVisible()

    // NOT toast-only (D9): the success toast auto-dismisses after 4s while
    // the escalation alert must still be on screen.
    await expect(page.getByText('Check-in saved.')).toBeHidden({ timeout: 8000 })
    await expect(alert).toBeVisible()
    await expect(page.getByTestId('crisis-banner')).toBeVisible()
  })

  test('history shows both check-ins as chart points and the ring shows the latest', async ({
    page,
  }) => {
    await page.goto('/check-ins')

    // Back to the form if the previous test's result is still showing.
    const done = page.getByRole('button', { name: /done/i })
    if (await done.isVisible()) {
      await done.click()
    }

    // The accessible text alternative of the trend chart lists BOTH entries
    // (today, totals 0 and 3 — same date, two points).
    const points = page.getByRole('listitem')
    await expect(points).toHaveCount(2)
    const pointTexts = (await points.allTextContents()).join(' | ')
    expect(pointTexts).toMatch(/: 0 \(minimal\)/)
    expect(pointTexts).toMatch(/: 3 \(minimal\)/)

    // The progress ring shows the MOST RECENT total and its published label.
    const ring = page.getByRole('progressbar', { name: /Most recent check-in total/ })
    await expect(ring).toBeVisible()
    await expect(ring).toHaveAttribute('aria-valuenow', '3')
    await expect(ring.locator('xpath=ancestor::div[1]')).toContainText('minimal')
  })
})
