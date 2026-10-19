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
  fetchCheckinHistory,
  fetchExercises,
  fetchHealth,
  fetchInstruments,
  fetchResources,
  purgeCheckins,
  sendChat,
  submitCheckin,
} from './client'
import type { components } from './schema.d'

type ChatResponse = components['schemas']['ChatResponse']
type ResourceOut = components['schemas']['ResourceOut']
type ExerciseOut = components['schemas']['ExerciseOut']
type InstrumentOut = components['schemas']['InstrumentOut']
type CheckInOut = components['schemas']['CheckInOut']
type CheckInRequest = components['schemas']['CheckInRequest']

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

const EXERCISE_LIST: ExerciseOut[] = [
  {
    id: 'rumination-postponement',
    title: 'Thought postponement',
    summary: 'Set aside a short, fixed window for the looping thoughts.',
    category: 'rumination',
    tier: 'A',
    steps: ['Notice the loop.', 'Park it for later.'],
    sources: ['Stenzel et al. 2025'],
    contraindications: [],
    early_worsening_notice: true,
  },
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

describe('fetchExercises', () => {
  it('GETs /content/exercises and returns the exercises array', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { exercises: EXERCISE_LIST }))

    const result = await fetchExercises()

    expect(result).toEqual(EXERCISE_LIST)
    expect(fetchMock).toHaveBeenCalledWith('/content/exercises')
  })

  it('maps a non-ok response to ApiUnavailableError without the server detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'library-internals' }))

    const error = await fetchExercises().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('library-internals')
  })

  it('maps a fetch rejection to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await fetchExercises().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
  })
})

// ---------------------------------------------------------------------------
// Stage 6d: instruments, check-in history, submit, health, purge
// ---------------------------------------------------------------------------

const PHQ9: InstrumentOut = {
  id: 'phq9',
  title: 'Patient Health Questionnaire-9 (PHQ-9)',
  recall_period: 'the past 2 weeks',
  scale_min: 0,
  scale_max: 3,
  total_min: 0,
  total_max: 27,
  items: [{ index: 1, prompt: 'Little interest or pleasure in doing things' }],
  answer_options: [{ value: 0, label: 'Not at all' }],
  severity_bands: [{ label: 'minimal', lower: 0, upper: 4 }],
  citation: 'Kroenke, Spitzer & Williams 2001',
}

const RECORD: CheckInOut = {
  instrument_id: 'phq9',
  date: '2026-10-18',
  responses: [0, 0, 0, 0, 0, 0, 0, 0, 0],
  total: 0,
  severity_label: 'minimal',
  flags: [],
  action: 'proceed',
  message_id: null,
  message: null,
}

describe('fetchInstruments', () => {
  it('GETs /instruments and returns the instruments array', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { instruments: [PHQ9] }))

    const result = await fetchInstruments()

    expect(result).toEqual([PHQ9])
    expect(fetchMock).toHaveBeenCalledWith('/instruments')
  })

  it('maps a non-ok response to ApiUnavailableError without the server detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'catalog-internals' }))

    const error = await fetchInstruments().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('catalog-internals')
  })

  it('maps a fetch rejection to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await fetchInstruments().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
  })
})

describe('fetchCheckinHistory', () => {
  it('GETs /checkins/{id} and returns the checkins array', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { checkins: [RECORD] }))

    const result = await fetchCheckinHistory('phq9')

    expect(result).toEqual([RECORD])
    expect(fetchMock).toHaveBeenCalledWith('/checkins/phq9')
  })

  it('maps a non-ok response (e.g. 404 unknown instrument) to ApiUnavailableError', async () => {
    fetchMock.mockResolvedValue(jsonResponse(404, { detail: 'unknown instrument' }))

    const error = await fetchCheckinHistory('nope').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('unknown instrument')
  })

  it('maps a fetch rejection to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await fetchCheckinHistory('phq9').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
  })
})

describe('submitCheckin', () => {
  const REQUEST: CheckInRequest = {
    instrument_id: 'phq9',
    responses: [0, 0, 0, 0, 0, 0, 0, 0, 0],
    date: '2026-10-18',
  }

  it('POSTs the check-in to /checkins and returns the typed CheckInOut', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, RECORD))

    const result = await submitCheckin(REQUEST)

    expect(result).toEqual(RECORD)
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/checkins')
    expect(init).toMatchObject({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(REQUEST),
    })
  })

  it('maps 422 to BadRequestError with our own fixed message', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(422, { detail: 'Check-in could not be recorded.' }),
    )

    const error = await submitCheckin(REQUEST).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(BadRequestError)
    expect((error as Error).message).toBe(
      "Your check-in couldn't be sent. Please try again.",
    )
    expect((error as Error).message).not.toContain('could not be recorded')
  })

  it('maps 503 to ApiUnavailableError without the server detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse(503, { detail: 'down-internals' }))

    const error = await submitCheckin(REQUEST).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('down-internals')
  })

  it('maps a fetch rejection to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await submitCheckin(REQUEST).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
  })
})

describe('fetchHealth', () => {
  it('GETs /health and returns the version payload', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { status: 'ok', version: '0.1.0.dev0' }))

    const result = await fetchHealth()

    expect(result).toEqual({ status: 'ok', version: '0.1.0.dev0' })
    expect(fetchMock).toHaveBeenCalledWith('/health')
  })

  it('maps a non-ok response to ApiUnavailableError without the server detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'health-internals' }))

    const error = await fetchHealth().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('health-internals')
  })

  it('maps a fetch rejection to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await fetchHealth().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
  })
})

describe('purgeCheckins', () => {
  it('DELETEs /checkins and returns the deleted count', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { deleted: 3 }))

    const result = await purgeCheckins()

    expect(result).toBe(3)
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/checkins')
    expect(init).toMatchObject({ method: 'DELETE' })
  })

  it('maps a non-ok response to ApiUnavailableError', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'purge-internals' }))

    const error = await purgeCheckins().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiUnavailableError)
    expect((error as Error).message).not.toContain('purge-internals')
  })

  it('maps a fetch rejection to NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await purgeCheckins().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(NetworkError)
  })
})
