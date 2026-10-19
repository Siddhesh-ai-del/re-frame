/**
 * Stage 6d settings E2E (keyless by design — no LLM key in CI).
 *
 * Proves in a real browser, against the live dev-mode backend:
 *
 *  1. Reduce effects: the three-way radio flips
 *     <html data-reduced-effects> in BOTH directions (localStorage
 *     'reframe:effects' follows).
 *  2. Frost/clouds: opt-in defaults OFF; turning reduce-effects ON
 *     disables the toggle, forces it OFF, and explains why.
 *  3. Journal (device-local): delete-all is confirm-guarded — cancel keeps
 *     the entries, confirm clears them with an inline (not toast-only)
 *     confirmation; the markdown export produces a download.
 *  4. Data: "Export my check-ins" produces a JSON download whose file name
 *     contains "check-ins" (the file is built client-side from the person's
 *     own history).
 *  5. Purge: with a check-in in history, "Delete all check-ins" → confirm →
 *     the DELETE /checkins request actually goes through the dev proxy
 *     (intercepted and asserted), the returned count is shown honestly,
 *     and the /check-ins history shows its empty state afterwards.
 *
 * Tests within this file run in declaration order (single worker): the
 * purge test runs LAST because it empties the shared database.
 */
import { expect, test, type Page } from '@playwright/test'

/**
 * Seed one PHQ-9 check-in through the same proxy the app uses.
 *
 * The date must be TODAY IN LOCAL TIME — the same authority the check-in
 * form uses. `toISOString()` is UTC, which is yesterday before ~05:30 IST
 * and would be rejected as out-of-order once a local-dated check-in exists.
 */
async function seedCheckin(page: Page): Promise<void> {
  const today = new Date().toLocaleDateString('en-CA') // YYYY-MM-DD in local time
  const response = await page.request.post('/checkins', {
    data: {
      instrument_id: 'phq9',
      date: today,
      responses: [0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
  })
  if (!response.ok()) {
    console.log('SEED FAILED', response.status(), await response.text())
  }
  expect(response.ok()).toBeTruthy()
}

test.describe('settings — reduce effects (three-way)', () => {
  test('flips <html data-reduced-effects> in both directions', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible()

    // Default: following the system setting → effects allowed.
    const html = page.locator('html')
    await expect(html).toHaveAttribute('data-reduced-effects', 'false')
    await expect(
      page.getByRole('radio', { name: /follow my system setting/i }),
    ).toBeChecked()

    // Explicit ON → reduced.
    await page
      .getByRole('radio', { name: /reduce motion and effects/i })
      .click()
    await expect(html).toHaveAttribute('data-reduced-effects', 'true')
    await expect
      .poll(() => page.evaluate(() => window.localStorage.getItem('reframe:effects')))
      .toBe('off')

    // Explicit OFF → full effects again.
    await page.getByRole('radio', { name: /use full effects/i }).click()
    await expect(html).toHaveAttribute('data-reduced-effects', 'false')
    await expect
      .poll(() => page.evaluate(() => window.localStorage.getItem('reframe:effects')))
      .toBe('on')
  })
})

test.describe('settings — frost/clouds opt-in', () => {
  test('defaults OFF and is enabled when motion effects are on', async ({ page }) => {
    await page.goto('/settings')

    const frost = page.getByRole('checkbox', { name: /frost/i })
    await expect(frost).toBeVisible()
    await expect(frost).not.toBeChecked()
    await expect(frost).toBeEnabled()
    await expect(page.getByText('frost/clouds needs motion effects on')).toHaveCount(0)
  })

  test('a stored opt-in is forced OFF (storage + UI) when reduce-effects turns on', async ({
    page,
  }) => {
    // The person opted in earlier — storage says 'on' before the page loads.
    await page.addInitScript(() => {
      window.localStorage.setItem('reframe:frost-clouds', 'on')
    })
    await page.goto('/settings')

    // With motion effects allowed, the stored opt-in is honored.
    const frost = page.getByRole('checkbox', { name: /frost/i })
    await expect(frost).toBeChecked()

    // Turning reduce-effects ON forces the opt-in OFF with an explanation.
    await page.getByRole('radio', { name: /reduce motion and effects/i }).click()
    await expect(frost).toBeDisabled()
    await expect(frost).not.toBeChecked()
    await expect(
      page.getByText('frost/clouds needs motion effects on'),
    ).toBeVisible()
    await expect
      .poll(() => page.evaluate(() => window.localStorage.getItem('reframe:frost-clouds')))
      .toBe('off')
  })
})

test.describe('settings — journal (device-local)', () => {
  test('delete-all is confirm-guarded; cancel keeps, confirm clears', async ({ page }) => {
    // Seed a journal entry BEFORE the app's scripts run.
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'reframe:journal',
        JSON.stringify([
          {
            id: 'e2e-1',
            text: 'e2e-private-journal-entry-9c4d1a',
            createdAt: '2026-01-01T10:00:00.000Z',
          },
        ]),
      )
    })
    await page.goto('/settings')

    // The seeded entry is listed on the page.
    await expect(page.getByText('e2e-private-journal-entry-9c4d1a')).toBeVisible()

    // Cancel: the confirm step appears and dismissing it changes nothing.
    await page.getByRole('button', { name: /delete all entries/i }).click()
    await expect(page.getByText(/delete all entries\?/i)).toBeVisible()
    await page.getByRole('button', { name: /cancel/i }).click()
    await expect(page.getByText(/delete all entries\?/i)).toHaveCount(0)
    await expect(page.getByText('e2e-private-journal-entry-9c4d1a')).toBeVisible()

    // Confirm: entries gone, inline confirmation shown (not toast-only).
    await page.getByRole('button', { name: /delete all entries/i }).click()
    await page.getByRole('button', { name: /^delete$/i }).click()
    await expect(page.getByRole('status')).toContainText(/cleared/i)
    await expect(page.getByText('e2e-private-journal-entry-9c4d1a')).toHaveCount(0)
    await expect
      .poll(() => page.evaluate(() => window.localStorage.getItem('reframe:journal')))
      .toBeNull()
  })

  test('journal export produces a markdown download', async ({ page }) => {
    await page.goto('/settings')

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /export.*journal/i }).click(),
    ])
    expect(download.suggestedFilename()).toMatch(/journal/)
  })
})

test.describe('settings — check-in data', () => {
  test('"Export my check-ins" downloads a JSON file named for check-ins', async ({
    page,
  }) => {
    await seedCheckin(page)
    await page.goto('/settings')

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /export my check-ins/i }).click(),
    ])
    expect(download.suggestedFilename()).toContain('check-ins')

    // The payload is the person's own data, built client-side.
    const stream = await download.createReadStream()
    const chunks: Buffer[] = []
    for await (const chunk of stream) {
      chunks.push(Buffer.from(chunk))
    }
    const payload = JSON.parse(Buffer.concat(chunks).toString('utf8')) as Array<{
      instrument_id: string
      total: number
    }>
    expect(payload.length).toBeGreaterThanOrEqual(1)
    expect(payload[0]).toMatchObject({ instrument_id: 'phq9' })
  })

  test('purge: confirm deletes via the proxy, shows the count, empties history', async ({
    page,
  }) => {
    // (seedCheckin from the previous test may have left rows; seed one more
    // so this test is self-contained if run alone.)
    await seedCheckin(page)

    // Sanity: the dashboard has history to purge.
    await page.goto('/check-ins')
    await expect(page.getByRole('listitem').first()).toBeVisible()

    await page.goto('/settings')

    // Watch the wire: the DELETE must travel through the dev proxy.
    const deleteRequest = page.waitForRequest(
      (request) => request.method() === 'DELETE' && request.url().includes('/checkins'),
    )

    await page.getByRole('button', { name: /delete all check-ins/i }).click()
    await expect(page.getByText(/delete all check-ins\?/i)).toBeVisible()
    await page.getByRole('button', { name: /^delete$/i }).click()

    // The proxied DELETE really happened…
    const request = await deleteRequest
    expect(new URL(request.url()).port).toBe('5373')

    // …and the returned count is shown honestly.
    await expect(page.getByRole('status')).toHaveText(/^\d+ check-ins deleted\.$/)

    // History is now empty — the honest empty states, not fake data.
    await page.goto('/check-ins')
    await expect(
      page.getByText(/your first check-in will start your history/i),
    ).toBeVisible()
    await expect(page.getByRole('region', { name: 'Dashboard status' })).toContainText(
      'No check-ins yet.',
    )
  })
})
