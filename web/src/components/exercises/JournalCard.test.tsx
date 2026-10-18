/**
 * JournalCard (stage 6c): a device-local journal. Entries live ONLY in
 * localStorage['reframe:journal'] (JSON array of {id, text, createdAt}).
 *
 * The critical privacy proof: a fetch spy asserts NO network call ever
 * carries journal text (design §5.6). Also verifies save/load round-trip,
 * corrupt-JSON fail-closed behavior, .md export, and delete-all.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { JournalCard } from './JournalCard'

const STORAGE_KEY = 'reframe:journal'
const PRIVATE_TEXT = 'a private thought that must never reach the network'

const fetchSpy = vi.fn()

beforeEach(() => {
  fetchSpy.mockReset()
  vi.stubGlobal('fetch', fetchSpy)
  window.localStorage.removeItem(STORAGE_KEY)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  window.localStorage.removeItem(STORAGE_KEY)
})

describe('JournalCard — save and load round-trip', () => {
  it('saves an entry, lists it with a timestamp, and persists to localStorage', async () => {
    const user = userEvent.setup()
    render(<JournalCard />)

    await user.type(screen.getByLabelText(/what's on your mind/i), PRIVATE_TEXT)
    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(await screen.findByText(PRIVATE_TEXT)).toBeInTheDocument()
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '[]')
    expect(stored).toHaveLength(1)
    expect(stored[0]).toMatchObject({ text: PRIVATE_TEXT })
    expect(typeof stored[0].createdAt).toBe('string')
  })

  it('loads previously saved entries on mount', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { id: 'a', text: 'yesterday entry', createdAt: '2026-10-01T10:00:00.000Z' },
      ]),
    )

    render(<JournalCard />)

    expect(screen.getByText('yesterday entry')).toBeInTheDocument()
    expect(screen.getByText(/2026/)).toBeInTheDocument()
  })
})

describe('JournalCard — privacy (never leaves the device)', () => {
  it('states the device-local promise plainly in the UI', () => {
    render(<JournalCard />)

    expect(
      screen.getByText(/stored only on this device/i),
    ).toBeInTheDocument()
  })

  it('never sends journal text over the network — fetch spy proof', async () => {
    const user = userEvent.setup()
    render(<JournalCard />)

    await user.type(screen.getByLabelText(/what's on your mind/i), PRIVATE_TEXT)
    await user.click(screen.getByRole('button', { name: /save/i }))
    expect(await screen.findByText(PRIVATE_TEXT)).toBeInTheDocument()

    // No call at all may carry the private text (in URL, body, or options).
    const serialized = JSON.stringify(fetchSpy.mock.calls)
    expect(serialized).not.toContain(PRIVATE_TEXT)
    for (const call of fetchSpy.mock.calls) {
      expect(JSON.stringify(call)).not.toContain(PRIVATE_TEXT)
    }
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})

describe('JournalCard — fail-closed storage handling', () => {
  it('falls back to an empty list when stored JSON is corrupt', () => {
    window.localStorage.setItem(STORAGE_KEY, '{not valid json')

    render(<JournalCard />)

    expect(screen.queryByText(/\{/)).not.toBeInTheDocument()
    expect(screen.getByText(/no entries yet/i)).toBeInTheDocument()
  })

  it('falls back to an empty list when stored JSON is valid but not an entry array', () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ text: 'not an array' }))

    render(<JournalCard />)

    expect(screen.getByText(/no entries yet/i)).toBeInTheDocument()
  })
})

describe('JournalCard — export and delete', () => {
  it('exports the entries as a markdown file via a Blob download', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { id: 'a', text: 'exported entry', createdAt: '2026-10-01T10:00:00.000Z' },
      ]),
    )
    // The Blob parameter annotates the call-tuple so `mock.calls[0][0]` is a
    // Blob rather than an empty tuple; the value itself is unused here.
    const createObjectURL = vi.fn((blob: Blob) => {
      void blob
      return 'blob:journal'
    })
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {})

    render(<JournalCard />)
    await userEvent.setup().click(screen.getByRole('button', { name: /export/i }))

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    const blob = createObjectURL.mock.calls[0]![0]
    expect(blob).toBeInstanceOf(Blob)
    await waitFor(async () => {
      expect(await blob.text()).toContain('exported entry')
    })
    expect(clickSpy).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:journal')
  })

  it('delete-all clears the list and the stored data', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { id: 'a', text: 'entry one', createdAt: '2026-10-01T10:00:00.000Z' },
        { id: 'b', text: 'entry two', createdAt: '2026-10-02T10:00:00.000Z' },
      ]),
    )

    render(<JournalCard />)
    expect(screen.getByText('entry one')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /delete all/i }))

    expect(screen.queryByText('entry one')).not.toBeInTheDocument()
    expect(screen.getByText(/no entries yet/i)).toBeInTheDocument()
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('never sends journal text during export or delete either', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { id: 'a', text: PRIVATE_TEXT, createdAt: '2026-10-01T10:00:00.000Z' },
      ]),
    )
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: vi.fn(() => 'blob:journal'),
      revokeObjectURL: vi.fn(),
    })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    render(<JournalCard />)
    await user.click(screen.getByRole('button', { name: /export/i }))
    await user.click(screen.getByRole('button', { name: /delete all/i }))

    expect(JSON.stringify(fetchSpy.mock.calls)).not.toContain(PRIVATE_TEXT)
  })
})
