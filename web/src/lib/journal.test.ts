/**
 * lib/journal (stage 6d): the device-local journal helpers extracted from
 * JournalCard so Settings can reuse the exact same read/write/export/clear
 * behavior. Covers the fail-closed read contract, the write-through helpers,
 * the markdown export mechanics (Blob download, no network), and the clear.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  JOURNAL_FILENAME,
  JOURNAL_STORAGE_KEY,
  appendEntry,
  clearEntries,
  exportJournal,
  loadEntries,
  makeEntry,
  persistEntries,
  toMarkdown,
} from './journal'
import type { JournalEntry } from './journal'

const ENTRY: JournalEntry = {
  id: 'a',
  text: 'a private thought',
  createdAt: '2026-10-01T10:00:00.000Z',
}

function memoryStorage(seed: Record<string, string> = {}): Storage {
  const store = new Map(Object.entries(seed))
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, String(value))
    },
    removeItem: (key: string) => {
      store.delete(key)
    },
    clear: () => store.clear(),
    key: (index: number) => [...store.keys()][index] ?? null,
    get length() {
      return store.size
    },
  }
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('loadEntries', () => {
  it('returns an empty list when nothing is stored', () => {
    expect(loadEntries(memoryStorage())).toEqual([])
  })

  it('parses a stored array of valid entries', () => {
    const storage = memoryStorage({ [JOURNAL_STORAGE_KEY]: JSON.stringify([ENTRY]) })
    expect(loadEntries(storage)).toEqual([ENTRY])
  })

  it('fails closed to an empty list on corrupt JSON', () => {
    const storage = memoryStorage({ [JOURNAL_STORAGE_KEY]: '{not valid json' })
    expect(loadEntries(storage)).toEqual([])
  })

  it('fails closed to an empty list when the stored value is not an array', () => {
    const storage = memoryStorage({ [JOURNAL_STORAGE_KEY]: JSON.stringify({ text: 'x' }) })
    expect(loadEntries(storage)).toEqual([])
  })

  it('drops malformed items instead of surfacing them', () => {
    const storage = memoryStorage({
      [JOURNAL_STORAGE_KEY]: JSON.stringify([ENTRY, { id: 1, text: 'bad' }, 'nope']),
    })
    expect(loadEntries(storage)).toEqual([ENTRY])
  })

  it('fails closed when the storage itself throws', () => {
    const throwing = {
      getItem: (): string | null => {
        throw new Error('storage blocked')
      },
    }
    expect(loadEntries(throwing)).toEqual([])
  })
})

describe('makeEntry / appendEntry / persistEntries', () => {
  it('makeEntry stamps the text with an ISO timestamp and a non-empty id', () => {
    const entry = makeEntry('hello')
    expect(entry.text).toBe('hello')
    expect(entry.id).not.toBe('')
    expect(Number.isNaN(Date.parse(entry.createdAt))).toBe(false)
  })

  it('appendEntry returns a NEW list with the entry appended (no mutation)', () => {
    const previous = [ENTRY]
    const next = appendEntry(previous, 'second thought')

    expect(next).toHaveLength(2)
    expect(next[1]?.text).toBe('second thought')
    expect(previous).toHaveLength(1)
  })

  it('persistEntries writes the list as JSON to the given storage', () => {
    const storage = memoryStorage()
    persistEntries(storage, [ENTRY])
    expect(storage.getItem(JOURNAL_STORAGE_KEY)).toBe(JSON.stringify([ENTRY]))
  })

  it('persistEntries never throws when the storage rejects writes', () => {
    const throwing = {
      setItem: (): void => {
        throw new Error('quota exceeded')
      },
    }
    expect(() => persistEntries(throwing, [ENTRY])).not.toThrow()
  })
})

describe('clearEntries', () => {
  it('removes the stored journal', () => {
    const storage = memoryStorage({ [JOURNAL_STORAGE_KEY]: JSON.stringify([ENTRY]) })
    clearEntries(storage)
    expect(storage.getItem(JOURNAL_STORAGE_KEY)).toBeNull()
  })

  it('never throws when the storage rejects removals', () => {
    const throwing = {
      removeItem: (): void => {
        throw new Error('storage blocked')
      },
    }
    expect(() => clearEntries(throwing)).not.toThrow()
  })
})

describe('toMarkdown / exportJournal', () => {
  it('toMarkdown renders the header plus a section per entry', () => {
    const markdown = toMarkdown([ENTRY])
    expect(markdown).toContain('# RE:FRAME journal')
    expect(markdown).toContain('a private thought')
    expect(markdown).toContain('## ')
  })

  it('exportJournal downloads the entries as a .md Blob (no network)', async () => {
    const createObjectURL = vi.fn((blob: Blob) => {
      void blob // typed so mock.calls[0][0] is a Blob; the URL is synthetic
      return 'blob:journal'
    })
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const appended: HTMLAnchorElement[] = []
    vi.spyOn(document.body, 'appendChild').mockImplementation((node: Node) => {
      appended.push(node as HTMLAnchorElement)
      return node
    })

    exportJournal([ENTRY])

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    const blob = createObjectURL.mock.calls[0]![0]
    expect(blob).toBeInstanceOf(Blob)
    expect(await blob.text()).toContain('a private thought')
    expect(appended[0]?.download).toBe(JOURNAL_FILENAME)
    expect(appended[0]?.href).toBe('blob:journal')
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:journal')
  })
})
