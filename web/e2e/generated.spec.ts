/**
 * Stage 6e generated-turn E2E — the proof that a REAL generated reply reaches
 * the UI (the 21 keyless specs assert the honest 503 instead).
 *
 * This runs against the composed production-like service on :8124: FastAPI
 * serving the BUILT SPA from `web/dist` via `--static` AND the JSON API from
 * one process (no dev server, no proxy), wired through the config overrides
 * `REFRAME_LLM_BASE_URL=http://127.0.0.1:8125` / `REFRAME_LLM_MODEL` to the
 * tiny mock OpenAI-compatible provider in `web/scripts/mock-llm-server.py`.
 *
 * Flow under test: GET /chat serves the SPA by route precedence → the UI sends
 * POST /chat → retrieval → ConstrainedGenerator → OpenAICompatibleClient →
 * mock provider → fixed reply rendered as an assistant bubble, with NO
 * unavailable/503 notice anywhere.
 *
 * No real credentials exist anywhere in this flow.
 */
import { expect, test } from '@playwright/test'

/** Must match `MOCK_REPLY` in web/scripts/mock-llm-server.py. */
const MOCK_REPLY =
  "That argument keeps looping in your head. Would it help to write down what you'd say differently, or to set the thought aside for ten minutes and come back to it?"

/** Verified NORMAL/PROCEED input: routes to generation, never crisis/review. */
const GENERATED_TURN_MESSAGE = 'I keep replaying an argument in my head'

test.describe('composed service (static SPA + API in one process)', () => {
  test('GET /chat serves the SPA by route precedence, not 405/json', async ({
    page,
  }) => {
    const response = await page.goto('/chat')

    expect(response?.status()).toBe(200)
    await expect(page.getByRole('banner')).toContainText('RE:FRAME')
    await expect(page.getByRole('heading', { name: 'Chat', level: 1 })).toBeVisible()
  })

  test('the JSON API still answers on the same origin', async ({ request }) => {
    const health = await request.get('/health')
    expect(health.ok()).toBe(true)
    expect((await health.json()).status).toBe('ok')

    const chat = await request.post('/chat', {
      data: { message: GENERATED_TURN_MESSAGE },
    })
    expect(chat.status()).toBe(200)
    const body = await chat.json()
    expect(body.route).toBe('generated')
    expect(body.reply).toBe(MOCK_REPLY)
  })
})

test.describe('generated turn through the mock provider', () => {
  test('renders the model reply as an assistant bubble instead of the 503 state', async ({
    page,
  }) => {
    await page.goto('/chat')

    await page.getByLabel('Message').fill(GENERATED_TURN_MESSAGE)
    await page.getByRole('button', { name: 'Send' }).click()

    // The generated reply is rendered as a conversation bubble.
    const assistantBubble = page
      .getByRole('list', { name: 'Conversation' })
      .getByRole('listitem')
      .filter({ hasText: MOCK_REPLY })
    await expect(assistantBubble).toHaveCount(1)

    // The honest-503 state must NOT appear: generation truly happened.
    await expect(
      page.getByText('The assistant is unavailable right now'),
    ).toHaveCount(0)
    await expect(page.getByText("You appear to be offline")).toHaveCount(0)

    // And no escalation state was triggered by this non-crisis message.
    await expect(page.getByRole('alert')).toHaveCount(0)
  })
})
