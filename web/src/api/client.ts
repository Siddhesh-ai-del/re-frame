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
