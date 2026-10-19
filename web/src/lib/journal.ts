/**
 * Device-local journal helpers (stage 6d).
 *
 * Extracted verbatim from JournalCard (behavior unchanged) so Settings can
 * offer the SAME export and clear flows over the SAME storage — one
 * implementation of the privacy contract, two surfaces.
 *
 * PRIVACY (design §5.6, CRITICAL): everything here touches only
 * `localStorage['reframe:journal']` (a JSON array of {id, text, createdAt}).
 * Nothing is ever sent anywhere — `exportJournal` builds a local Blob
 * download and the helpers contain no fetch, no beacon, nothing.
 *
 * Fail-closed storage: a corrupt or unexpected stored shape reads as an
 * empty list (never a crash, never half-parsed garbage), and write/remove
 * failures are swallowed after the in-memory caller has its own copy.
 */

export const JOURNAL_STORAGE_KEY = 'reframe:journal'
export const JOURNAL_FILENAME = 'reframe-journal.md'

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
    const raw = storage.getItem(JOURNAL_STORAGE_KEY)
    if (raw === null) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isEntry)
  } catch {
    // Corrupt JSON (or a storage that throws): fail closed to empty.
    return []
  }
}

/** Build one entry stamped with an ISO timestamp and a unique-enough id. */
export function makeEntry(text: string): JournalEntry {
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

/** Return a NEW list with `text` appended as an entry (never mutates). */
export function appendEntry(entries: JournalEntry[], text: string): JournalEntry[] {
  return [...entries, makeEntry(text)]
}

/** Write the list through to storage; a failing storage never throws here. */
export function persistEntries(
  storage: Pick<Storage, 'setItem'>,
  entries: JournalEntry[],
): void {
  try {
    storage.setItem(JOURNAL_STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // Storage unavailable (privacy mode): the caller's session copy stands.
  }
}

/** Remove the stored journal; a failing storage never throws here. */
export function clearEntries(storage: Pick<Storage, 'removeItem'>): void {
  try {
    storage.removeItem(JOURNAL_STORAGE_KEY)
  } catch {
    // Storage unavailable: the caller has already cleared its own list.
  }
}

/** Render the entries as the exported markdown document. */
export function toMarkdown(entries: JournalEntry[]): string {
  const lines = entries.map(
    (entry) => `## ${new Date(entry.createdAt).toLocaleString()}\n\n${entry.text}\n`,
  )
  return `# RE:FRAME journal\n\nYour entries, exported from this device.\n\n${lines.join('\n')}`
}

/**
 * Download the entries as a markdown file — a local Blob + anchor click,
 * no network involvement of any kind.
 */
export function exportJournal(entries: JournalEntry[]): void {
  const blob = new Blob([toMarkdown(entries)], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = JOURNAL_FILENAME
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
