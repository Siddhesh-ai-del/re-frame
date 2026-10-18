/**
 * Frontend wellness-lane lint: mirrors the backend content rule — no source
 * file (tests excluded) may contain diagnosis/treatment/prescription claim
 * language. Strings in the UI must stay in the wellness lane.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { extname, join, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// vitest runs with the project root (web/) as cwd; jsdom rewrites
// import.meta.url to an http URL, so resolve from cwd instead.
const SRC_DIR = resolve(process.cwd(), 'src')

const BANNED =
  /\b(diagnos\w*|therap\w*|treatment\w*|prescrib\w*|medication\w*|cure[sd]?\b)/i

function collectSourceFiles(dir: string): string[] {
  const files: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...collectSourceFiles(path))
      continue
    }
    if (!['.ts', '.tsx'].includes(extname(entry.name))) continue
    if (entry.name.includes('.test.')) continue
    if (entry.name === 'schema.d.ts') continue
    files.push(path)
  }
  return files
}

describe('frontend wellness-lane lint', () => {
  it('finds source files to scan (sanity)', () => {
    expect(collectSourceFiles(SRC_DIR).length).toBeGreaterThan(0)
  })

  it.each(collectSourceFiles(SRC_DIR).map((path) => [relative(SRC_DIR, path), path] as const))(
    '%s contains no banned wellness-lane claims',
    (_name, path) => {
      const source = readFileSync(path, 'utf8')
      const violation = source.match(BANNED)
      expect(violation?.[0]).toBeUndefined()
    },
  )
})
