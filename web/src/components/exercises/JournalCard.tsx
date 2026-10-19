/**
 * JournalCard (stage 6c): a device-local journal. adapted from opensourceui
 * (MIT) writing-card — reshaped to the RE:FRAME privacy contract.
 *
 * PRIVACY (design §5.6, CRITICAL): journal text lives ONLY in
 * `localStorage['reframe:journal']` (see `lib/journal.ts` — the shared
 * read/write/export/clear helpers this card and Settings both use). It is
 * never sent anywhere — no fetch, no beacon, nothing. The UI says so
 * plainly, and a fetch-spy test proves it.
 *
 * Fail-closed storage: corrupt or unexpected stored JSON renders as an empty
 * list (never a crash, never half-parsed garbage). The timestamp display is
 * locale-formatted from the stored ISO string.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  appendEntry,
  clearEntries,
  exportJournal,
  loadEntries,
  persistEntries,
} from '../../lib/journal'
import type { JournalEntry } from '../../lib/journal'

export function JournalCard() {
  const [entries, setEntries] = useState<JournalEntry[]>(() =>
    loadEntries(window.localStorage),
  )
  const [draft, setDraft] = useState('')
  const trimmed = draft.trim()

  const save = useCallback(() => {
    if (trimmed.length === 0) return
    setEntries((previous) => {
      // Write-through: the device-local store is the only destination.
      const next = appendEntry(previous, trimmed)
      persistEntries(window.localStorage, next)
      return next
    })
    setDraft('')
  }, [trimmed])

  const deleteAll = useCallback(() => {
    setEntries([])
    clearEntries(window.localStorage)
  }, [])

  const exportMarkdown = useCallback(() => {
    exportJournal(entries)
  }, [entries])

  // Keep storage and state in step if another tab writes (best-effort).
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === 'reframe:journal') setEntries(loadEntries(window.localStorage))
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
