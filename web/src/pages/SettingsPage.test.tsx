/**
 * SettingsPage (stage 6d): preferences, local data, and About.
 *
 * Covers the three-way reduce-effects radio bound to the preference engine
 * (localStorage + dataset update in both directions), the frost/clouds
 * opt-in (default OFF, disabled + explained when motion effects are off,
 * forced OFF under OS reduced-motion), the journal export + confirm-guarded
 * delete-all (inline confirmation, never toast-only), the check-in JSON
 * export (aggregated client-side, filename contains "check-ins"), the
 * confirm-guarded purge with the honest returned count and the honest
 * failure path, and the About version with its honest fallback.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiUnavailableError,
  NetworkError,
  fetchHealth,
  fetchInstruments,
  fetchCheckinHistory,
  purgeCheckins,
} from '../api/client'
import { EffectsProvider } from '../effects/EffectsContext'
import { setMediaQuery } from '../test/setup'
import { SettingsPage } from './SettingsPage'
import { JOURNAL_STORAGE_KEY } from '../lib/journal'
import type { components } from '../api/schema.d'

type InstrumentOut = components['schemas']['InstrumentOut']
type CheckInOut = components['schemas']['CheckInOut']

vi.mock('../api/client', () => ({
  fetchHealth: vi.fn(),
  fetchInstruments: vi.fn(),
  fetchCheckinHistory: vi.fn(),
  purgeCheckins: vi.fn(),
  ApiUnavailableError: class ApiUnavailableError extends Error {},
  NetworkError: class NetworkError extends Error {},
}))

const mockFetchHealth = vi.mocked(fetchHealth)
const mockFetchInstruments = vi.mocked(fetchInstruments)
const mockFetchCheckinHistory = vi.mocked(fetchCheckinHistory)
const mockPurgeCheckins = vi.mocked(purgeCheckins)

const FROST_KEY = 'reframe:frost-clouds'
const EFFECTS_KEY = 'reframe:effects'

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

const K10: InstrumentOut = {
  ...PHQ9,
  id: 'k10',
  title: 'Kessler Psychological Distress Scale (K-10)',
  items: [{ index: 1, prompt: 'About how often did you feel tired out for no good reason?' }],
}

function historyEntry(overrides: Partial<CheckInOut> = {}): CheckInOut {
  return {
    instrument_id: 'phq9',
    date: '2026-01-05',
    responses: [0, 1, 2, 3, 0],
    total: 6,
    severity_label: 'mild',
    flags: [],
    action: 'proceed',
    message_id: null,
    message: null,
    ...overrides,
  }
}

function renderPage() {
  return render(
    <EffectsProvider>
      <SettingsPage />
    </EffectsProvider>,
  )
}

/** Capture anchor downloads produced by Blob export helpers. */
function trackDownloads() {
  const downloads: string[] = []
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    downloads.push(this.download)
  })
  const createObjectURL = vi.fn((blob: Blob) => {
    void blob
    return 'blob:download'
  })
  const revokeObjectURL = vi.fn()
  vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })
  return { downloads, createObjectURL, revokeObjectURL }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  mockFetchHealth.mockResolvedValue({ status: 'ok', version: '1.4.0' })
  mockFetchInstruments.mockResolvedValue([PHQ9, K10])
  mockFetchCheckinHistory.mockResolvedValue([])
  mockPurgeCheckins.mockResolvedValue(0)
})

describe('SettingsPage — reduce effects (three-way)', () => {
  it('defaults to following the system setting', async () => {
    renderPage()

    expect(await screen.findByRole('radio', { name: /follow my system setting/i })).toBeChecked()
  })

  it('stores the explicit preference and flips the dataset immediately (both directions)', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByRole('radio', { name: /follow my system setting/i })

    await user.click(screen.getByRole('radio', { name: /on — reduce motion and effects/i }))
    expect(window.localStorage.getItem(EFFECTS_KEY)).toBe('off')
    expect(document.documentElement.dataset.reducedEffects).toBe('true')

    await user.click(screen.getByRole('radio', { name: /off — use full effects/i }))
    expect(window.localStorage.getItem(EFFECTS_KEY)).toBe('on')
    expect(document.documentElement.dataset.reducedEffects).toBe('false')
  })

  it('follows the OS reduced-motion signal while set to system', async () => {
    renderPage()
    await screen.findByRole('radio', { name: /follow my system setting/i })

    setMediaQuery('(prefers-reduced-motion: reduce)', true)
    await waitFor(() =>
      expect(document.documentElement.dataset.reducedEffects).toBe('true'),
    )

    setMediaQuery('(prefers-reduced-motion: reduce)', false)
    await waitFor(() =>
      expect(document.documentElement.dataset.reducedEffects).toBe('false'),
    )
  })
})

describe('SettingsPage — ambient frost/clouds toggle', () => {
  it('defaults to OFF and is enabled when motion effects are on', async () => {
    renderPage()

    const toggle = await screen.findByRole('checkbox', { name: /frost/i })
    expect(toggle).not.toBeChecked()
    expect(toggle).toBeEnabled()
  })

  it('writes storage and announces the change on the same tab when toggled', async () => {
    const user = userEvent.setup()
    const seen: Event[] = []
    window.addEventListener('reframe:frost-changed', (event) => seen.push(event))
    renderPage()
    const toggle = await screen.findByRole('checkbox', { name: /frost/i })

    await user.click(toggle)
    expect(window.localStorage.getItem(FROST_KEY)).toBe('on')
    expect(seen).toHaveLength(1)

    await user.click(toggle)
    expect(window.localStorage.getItem(FROST_KEY)).toBe('off')
    expect(seen).toHaveLength(2)
  })

  it('disables and explains the toggle when reduce-effects is ON, forcing it OFF', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem(FROST_KEY, 'on')
    renderPage()
    await screen.findByRole('checkbox', { name: /frost/i })

    await user.click(screen.getByRole('radio', { name: /on — reduce motion and effects/i }))

    const toggle = screen.getByRole('checkbox', { name: /frost/i })
    expect(toggle).toBeDisabled()
    expect(toggle).not.toBeChecked()
    expect(screen.getByText('frost/clouds needs motion effects on')).toBeInTheDocument()
    expect(window.localStorage.getItem(FROST_KEY)).toBe('off')
  })

  it('forces the toggle OFF under OS reduced-motion even at system preference', async () => {
    window.localStorage.setItem(FROST_KEY, 'on')
    setMediaQuery('(prefers-reduced-motion: reduce)', true)
    renderPage()

    const toggle = await screen.findByRole('checkbox', { name: /frost/i })
    expect(toggle).toBeDisabled()
    expect(toggle).not.toBeChecked()
    expect(screen.getByText('frost/clouds needs motion effects on')).toBeInTheDocument()
    expect(window.localStorage.getItem(FROST_KEY)).toBe('off')
  })
})

describe('SettingsPage — journal', () => {
  function seedJournal() {
    window.localStorage.setItem(
      JOURNAL_STORAGE_KEY,
      JSON.stringify([
        { id: 'a', text: 'first private entry', createdAt: '2026-01-01T10:00:00.000Z' },
        { id: 'b', text: 'second private entry', createdAt: '2026-01-02T10:00:00.000Z' },
      ]),
    )
  }

  it('exports the journal as a markdown Blob download', async () => {
    const user = userEvent.setup()
    seedJournal()
    const { downloads, createObjectURL } = trackDownloads()
    renderPage()

    const button = await screen.findByRole('button', { name: /export.*journal/i })
    await user.click(button)

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    const blob = createObjectURL.mock.calls[0]![0]
    const text = await blob.text()
    expect(text).toContain('first private entry')
    expect(downloads[0]).toMatch(/journal/)
  })

  it('cancel on the delete-all confirm does nothing', async () => {
    const user = userEvent.setup()
    seedJournal()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /delete all entries/i }))
    expect(screen.getByText(/delete all entries\?/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(screen.queryByText(/delete all entries\?/i)).not.toBeInTheDocument()
    expect(window.localStorage.getItem(JOURNAL_STORAGE_KEY)).toContain('first private entry')
    expect(screen.getByText('first private entry')).toBeInTheDocument()
  })

  it('confirm clears the journal with an inline confirmation (not toast-only)', async () => {
    const user = userEvent.setup()
    seedJournal()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /delete all entries/i }))
    await user.click(screen.getByRole('button', { name: /^delete$/i }))

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/cleared/i))
    expect(window.localStorage.getItem(JOURNAL_STORAGE_KEY)).toBeNull()
    expect(screen.queryByText('first private entry')).not.toBeInTheDocument()
  })
})

describe('SettingsPage — check-in data', () => {
  it('exports every instrument history as a JSON download containing the person\'s own data', async () => {
    const user = userEvent.setup()
    mockFetchCheckinHistory.mockImplementation(async (id: string) =>
      id === 'phq9' ? [historyEntry()] : [historyEntry({ instrument_id: 'k10', date: '2026-02-01' })],
    )
    const { downloads, createObjectURL } = trackDownloads()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /export my check-ins/i }))

    await waitFor(() => expect(createObjectURL).toHaveBeenCalledTimes(1))
    expect(mockFetchInstruments).toHaveBeenCalled()
    expect(mockFetchCheckinHistory).toHaveBeenCalledWith('phq9')
    expect(mockFetchCheckinHistory).toHaveBeenCalledWith('k10')

    const blob = createObjectURL.mock.calls[0]![0]
    const payload = JSON.parse(await blob.text()) as Array<{
      instrument_id: string
      date: string
      total: number
      severity_label: string | null
      responses: number[]
    }>
    expect(payload).toHaveLength(2)
    expect(payload[0]).toMatchObject({
      instrument_id: 'phq9',
      date: '2026-01-05',
      total: 6,
      severity_label: 'mild',
      responses: [0, 1, 2, 3, 0],
    })
    expect(downloads[0]).toContain('check-ins')
  })

  it('cancel on the purge confirm deletes nothing', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /delete all check-ins/i }))
    expect(screen.getByText(/delete all check-ins\?/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(screen.queryByText(/delete all check-ins\?/i)).not.toBeInTheDocument()
    expect(mockPurgeCheckins).not.toHaveBeenCalled()
  })

  it('confirm purges and shows the returned count honestly', async () => {
    const user = userEvent.setup()
    mockPurgeCheckins.mockResolvedValue(3)
    renderPage()

    await user.click(await screen.findByRole('button', { name: /delete all check-ins/i }))
    await user.click(screen.getByRole('button', { name: /^delete$/i }))

    await waitFor(() => expect(mockPurgeCheckins).toHaveBeenCalledTimes(1))
    expect(await screen.findByRole('status')).toHaveTextContent('3 check-ins deleted.')
  })

  it('shows an honest inline error when the purge fails (no fake success)', async () => {
    const user = userEvent.setup()
    mockPurgeCheckins.mockRejectedValue(new NetworkError('offline'))
    renderPage()

    await user.click(await screen.findByRole('button', { name: /delete all check-ins/i }))
    await user.click(screen.getByRole('button', { name: /^delete$/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/couldn't be deleted|try again/i)
    expect(screen.queryByText(/check-ins deleted\./i)).not.toBeInTheDocument()
  })
})

describe('SettingsPage — About', () => {
  it('shows the service version when health responds', async () => {
    renderPage()
    expect(
      await screen.findByText('Version 1.4.0 — from the local service'),
    ).toBeInTheDocument()
  })

  it('falls back honestly when the service is unreachable', async () => {
    mockFetchHealth.mockRejectedValue(new ApiUnavailableError('down'))
    renderPage()
    expect(
      await screen.findByText("Version unavailable — the local service isn't responding."),
    ).toBeInTheDocument()
  })

  it('keeps the standing honesty line visible', async () => {
    renderPage()
    expect(
      await screen.findByText('RE:FRAME is wellness support, not medical care.'),
    ).toBeInTheDocument()
  })
})
