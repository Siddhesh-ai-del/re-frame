/**
 * Typed API client for the RE:FRAME service.
 *
 * All types are derived from FastAPI's generated OpenAPI schema
 * (`schema.d.ts`, regenerated from `schema.json`), so the wire contract
 * cannot drift from the backend silently.
 *
 * Error mapping is honest and leak-free: every failure becomes one of three
 * exported error classes whose messages are OUR fixed wellness-framed copy —
 * the server's `detail` text is never surfaced into UI state (a 503 body is
 * generic by construction, but the UI never depends on that wording).
 */
import type { components } from './schema.d'

export type ChatResponse = components['schemas']['ChatResponse']
export type ResourceOut = components['schemas']['ResourceOut']
export type ExerciseOut = components['schemas']['ExerciseOut']
export type InstrumentOut = components['schemas']['InstrumentOut']
export type CheckInOut = components['schemas']['CheckInOut']
export type CheckInRequest = components['schemas']['CheckInRequest']
export type CheckInPurgeOut = components['schemas']['CheckInPurgeOut']
export type HealthResponse = components['schemas']['HealthResponse']

/** The fixed, honest copy for a refused check-in (stage 6d). */
export const CHECKIN_BAD_REQUEST_MESSAGE =
  "Your check-in couldn't be sent. Please try again."

/** 422: the message was malformed or refused before the pipeline ran. */
export class BadRequestError extends Error {
  constructor(message = "Your message couldn't be sent. Please shorten it and try again.") {
    super(message)
    this.name = 'BadRequestError'
  }
}

/** 503/500: the assistant (LLM-backed generation) is unreachable. */
export class ApiUnavailableError extends Error {
  constructor(
    message = 'The assistant is unavailable right now. You can still reach crisis support below.',
  ) {
    super(message)
    this.name = 'ApiUnavailableError'
  }
}

/** The request never reached the server (offline, DNS, connection reset). */
export class NetworkError extends Error {
  constructor(message = 'You appear to be offline. Check your connection and try again.') {
    super(message)
    this.name = 'NetworkError'
  }
}

/**
 * Send one chat message. 200 → the typed response; 422 → BadRequestError;
 * 503/500 (or any other unexpected status) → ApiUnavailableError; a rejected
 * fetch → NetworkError.
 */
export async function sendChat(message: string): Promise<ChatResponse> {
  let response: Response
  try {
    response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
  } catch {
    throw new NetworkError()
  }
  if (response.ok) {
    return (await response.json()) as ChatResponse
  }
  if (response.status === 422) {
    throw new BadRequestError()
  }
  throw new ApiUnavailableError()
}

/**
 * Fetch the standing crisis resources (GET /resources). These are served
 * independently of the LLM, so this stays reachable on the 503 path.
 */
export async function fetchResources(): Promise<ResourceOut[]> {
  let response: Response
  try {
    response = await fetch('/resources')
  } catch {
    throw new NetworkError()
  }
  if (!response.ok) {
    throw new ApiUnavailableError()
  }
  const body = (await response.json()) as { resources: ResourceOut[] }
  return body.resources
}

/**
 * Fetch the full exercise library (GET /content/exercises). Served from the
 * packaged content, independent of the LLM. Error mapping matches
 * fetchResources: non-ok → ApiUnavailableError, rejected fetch → NetworkError.
 */
export async function fetchExercises(): Promise<ExerciseOut[]> {
  let response: Response
  try {
    response = await fetch('/content/exercises')
  } catch {
    throw new NetworkError()
  }
  if (!response.ok) {
    throw new ApiUnavailableError()
  }
  const body = (await response.json()) as { exercises: ExerciseOut[] }
  return body.exercises
}

/**
 * Fetch the full instrument catalog (GET /instruments) — the form-ready
 * specs (items, answer options, bands, citation) behind /check-ins.
 * Error mapping matches fetchResources.
 */
export async function fetchInstruments(): Promise<InstrumentOut[]> {
  let response: Response
  try {
    response = await fetch('/instruments')
  } catch {
    throw new NetworkError()
  }
  if (!response.ok) {
    throw new ApiUnavailableError()
  }
  const body = (await response.json()) as { instruments: InstrumentOut[] }
  return body.instruments
}

/**
 * Fetch one instrument's check-in history (GET /checkins/{instrument_id}),
 * oldest to newest as the service returns it. A 404 (unknown instrument)
 * maps to ApiUnavailableError like every other non-ok status — the UI only
 * asks for ids it got from GET /instruments, and the server's `detail`
 * never becomes client copy.
 */
export async function fetchCheckinHistory(instrumentId: string): Promise<CheckInOut[]> {
  let response: Response
  try {
    response = await fetch(`/checkins/${encodeURIComponent(instrumentId)}`)
  } catch {
    throw new NetworkError()
  }
  if (!response.ok) {
    throw new ApiUnavailableError()
  }
  const body = (await response.json()) as { checkins: CheckInOut[] }
  return body.checkins
}

/**
 * Record one check-in (POST /checkins). 200 → the typed CheckInOut (score,
 * flags, routing action, verbatim `message`); 422 → BadRequestError with our
 * own fixed copy; 503/500/other → ApiUnavailableError; rejected fetch →
 * NetworkError — the chat pattern exactly.
 */
export async function submitCheckin(request: CheckInRequest): Promise<CheckInOut> {
  let response: Response
  try {
    response = await fetch('/checkins', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  } catch {
    throw new NetworkError()
  }
  if (response.ok) {
    return (await response.json()) as CheckInOut
  }
  if (response.status === 422) {
    throw new BadRequestError(CHECKIN_BAD_REQUEST_MESSAGE)
  }
  throw new ApiUnavailableError()
}

/**
 * Fetch liveness + package version (GET /health) for the Settings about
 * section. Error mapping matches fetchResources.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  let response: Response
  try {
    response = await fetch('/health')
  } catch {
    throw new NetworkError()
  }
  if (!response.ok) {
    throw new ApiUnavailableError()
  }
  return (await response.json()) as HealthResponse
}

/**
 * Purge every recorded check-in (DELETE /checkins) and return how many rows
 * the service removed. No request body; error mapping matches fetchResources.
 */
export async function purgeCheckins(): Promise<number> {
  let response: Response
  try {
    response = await fetch('/checkins', { method: 'DELETE' })
  } catch {
    throw new NetworkError()
  }
  if (!response.ok) {
    throw new ApiUnavailableError()
  }
  const body = (await response.json()) as CheckInPurgeOut
  return body.deleted
}
