/**
 * JournalCard (stage 6c): a device-local journal. adapted from opensourceui
 * (MIT) writing-card — reshaped to the RE:FRAME privacy contract.
 *
 * PRIVACY (design §5.6, CRITICAL): journal text lives ONLY in
 * `localStorage['reframe:journal']` (a JSON array of {id, text, createdAt}).
 * It is never sent anywhere — no fetch, no beacon, nothing. The UI says so
 * plainly, and a fetch-spy test proves it.
 *
 * Fail-closed storage: corrupt or unexpected stored JSON renders as an empty
 * list (never a crash, never half-parsed garbage). Export (a .md Blob
 * download) and delete-all live on the card for now (Settings wiring is 6d).
 * The timestamp display is locale-formatted from the stored ISO string.
 */
import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'reframe:journal'

export interface JournalEntry {
  id: string
  text: string
  createdAt: string
}

function isEntry(value: unknown): value is JournalEntry {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return (
    typeof record.id === 'string' &&
    typeof record.text === 'string' &&
    typeof record.createdAt === 'string'
  )
}

/** Read the stored entries; ANY malformed shape fails closed to an empty list. */
export function loadEntries(storage: Pick<Storage, 'getItem'>): JournalEntry[] {
  try {
    const raw = storage.getItem(STORAGE_KEY)
    if (raw === null) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isEntry)
  } catch {
    // Corrupt JSON (or a storage that throws): fail closed to empty.
    return []
  }
}

function makeEntry(text: string): JournalEntry {
  const randomSuffix =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2)
  return {
    id: `${Date.now()}-${randomSuffix}`,
    text,
    createdAt: new Date().toISOString(),
  }
}

function toMarkdown(entries: JournalEntry[]): string {
  const lines = entries.map(
    (entry) => `## ${new Date(entry.createdAt).toLocaleString()}\n\n${entry.text}\n`,
  )
  return `# RE:FRAME journal\n\nYour entries, exported from this device.\n\n${lines.join('\n')}`
}

export function JournalCard() {
  const [entries, setEntries] = useState<JournalEntry[]>(() =>
    loadEntries(window.localStorage),
  )
  const [draft, setDraft] = useState('')
  const trimmed = draft.trim()

  const save = useCallback(() => {
    if (trimmed.length === 0) return
    const entry = makeEntry(trimmed)
    setEntries((previous) => {
      const next = [...previous, entry]
      // Write-through: the device-local store is the only destination.
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      } catch {
        // Storage unavailable (privacy mode): the session copy still shows.
      }
      return next
    })
    setDraft('')
  }, [trimmed])

  const deleteAll = useCallback(() => {
    setEntries([])
    try {
      window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      // Storage unavailable: the in-session list is already cleared.
    }
  }, [])

  const exportMarkdown = useCallback(() => {
    const blob = new Blob([toMarkdown(entries)], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'reframe-journal.md'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }, [entries])

  // Keep storage and state in step if another tab writes (best-effort).
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setEntries(loadEntries(window.localStorage))
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  return (
    <section aria-label="Journal" className="flex flex-col gap-3">
      <h2 className="text-xl font-medium text-ink">Journal</h2>
      <p className="text-sm text-ink-muted">
        Your journal is stored only on this device. It is never sent anywhere.
      </p>
      <label htmlFor="journal-input" className="sr-only">
        What's on your mind?
      </label>
      <textarea
        id="journal-input"
        aria-label="What's on your mind?"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        rows={3}
        placeholder="Write a private entry…"
        className="rounded-[var(--radius-input)] border border-border bg-surface-sunk px-3 py-2 text-ink placeholder:text-ink-muted focus-visible:border-accent focus-visible:outline-none"
      />
      <div className="flex gap-2">
        <button
          type="button"
          onClick={save}
          disabled={trimmed.length === 0}
          className="rounded-pill bg-accent px-4 py-2 text-sm text-bg transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Save entry
        </button>
        <button
          type="button"
          onClick={exportMarkdown}
          disabled={entries.length === 0}
          className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Export as Markdown
        </button>
        <button
          type="button"
          onClick={deleteAll}
          disabled={entries.length === 0}
          className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Delete all entries
        </button>
      </div>
      {entries.length === 0 ? (
        <p className="text-ink-muted">No entries yet.</p>
      ) : (
        <ul aria-label="Saved entries" className="flex flex-col gap-2">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="rounded-[var(--radius-card)] border border-border bg-surface px-3 py-2"
            >
              <time
                dateTime={entry.createdAt}
                className="block text-xs text-ink-muted"
              >
                {new Date(entry.createdAt).toLocaleString()}
              </time>
              <p className="whitespace-pre-wrap text-ink">{entry.text}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
