/**
 * Typed API client: status-to-error mapping for every branch, and the honesty
 * rule that server-provided `detail` text never reaches a client error
 * message (the UI speaks its own fixed, wellness-framed strings).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiUnavailableError,
  BadRequestError,
  NetworkError,
  fetchResources,
  sendChat,
} from './client'
import type { components } from './schema.d'

type ChatResponse = components['schemas']['ChatResponse']
type ResourceOut = components['schemas']['ResourceOut']

const fetchMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response
}

const CHAT_DATA: ChatResponse = {
  reply: 'That loop sounds exhausting.',
  route: 'generated',
  module_ids: ['rumination_pause'],
  violations: [],
  resources: [],
}

const RESOURCE_LIST: ResourceOut[] = [
  { name: 'Find A Helpline (IASP global directory)', url: 'https://findahelpline.com' },
  { name: '988 Suicide & Crisis Lifeline (US)', url: 'https://988lifeline.org' },
  { name: 'If you are in immediate danger, contact your local emergency services', url: null },
]

describe('sendChat', () => {
  it('POSTs the message to /chat and returns the parsed ChatResponse', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, CHAT_DATA))

    const result = await sendChat('I keep replaying an argument in my head')

    expect(result).toEqual(CHAT_DATA)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/chat')
    expect(init).toMatchObject({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'I keep replaying an argument in my head' }),
    })
  })

  it('maps 422 to BadRequestError with our own fixed message', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(422, { detail: 'The message could not be processed.' }),
    )

    await expect(sendChat('x')).rejects.toBeInstanceOf(BadRequestError)
    const error = await sendChat('x').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(Error)
    expect((error as Error).name).toBe('BadRequestError')
    expect((error as Error).message).toBe(
      "Your message couldn't be sent. Please shorten it and try again.",
    )
  })

  it('maps 503 to ApiUnavailableError without leaking the server detail', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(503, { detail: 'The assistant is temporarily unavailable. sk-SECRET' }),
    )

    const error = await sendChat('hello').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).name).toBe('ApiUnavailableError')
    expect((error as Error).message).toBe(
      'The assistant is unavailable right now. You can still reach crisis support below.',
    )
    expect((error as Error).message).not.toContain('sk-SECRET')
    expect((error as Error).message).not.toContain('temporarily unavailable')
  })

  it('maps 500 to ApiUnavailableError', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'Internal server error.' }))

    const error = await sendChat('hello').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('Internal server error')
  })

  it('maps a fetch rejection (offline) to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await sendChat('hello').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
    expect((error as Error).name).toBe('NetworkError')
    expect((error as Error).message).toBe(
      'You appear to be offline. Check your connection and try again.',
    )
  })

  it('maps any other unexpected status to ApiUnavailableError (fail honest)', async () => {
    fetchMock.mockResolvedValue(jsonResponse(404, { detail: 'Not Found' }))

    const error = await sendChat('hello').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
  })
})

describe('fetchResources', () => {
  it('GETs /resources and returns the resources array', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { resources: RESOURCE_LIST }))

    const result = await fetchResources()

    expect(result).toEqual(RESOURCE_LIST)
    expect(fetchMock).toHaveBeenCalledWith('/resources')
  })

  it('maps a non-ok response to ApiUnavailableError without the server detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'boom-internals' }))

    const error = await fetchResources().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('boom-internals')
  })

  it('maps a fetch rejection to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await fetchResources().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
  })
})
