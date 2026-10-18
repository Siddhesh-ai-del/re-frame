/**
 * Frontend physiological-claims lint (stage 6c, design §5 row 1 companion).
 *
 * The lane-lint bans diagnosis/treatment LANGUAGE; this lint bans OUTCOME
 * CLAIMS about physiology and efficacy that the UI must never make ("reduces
 * anxiety", "calms the nervous system", "heals", "clinically proven").
 * Scans every non-test source file; the fix is always the copy, never the
 * test.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { extname, join, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC_DIR = resolve(process.cwd(), 'src')

const EXCLUDED_FILES = new Set(['schema.d.ts'])

const CLAIM_PATTERNS: ReadonlyArray<{ name: string; pattern: RegExp }> = [
  { name: 'anxiety/stress/depression reduction', pattern: /reduc(e|es|ing)\s+(anxiety|stress|depression)/i },
  { name: 'nervous-system calming', pattern: /calms?\s+the\s+nervous\s+system/i },
  { name: 'healing', pattern: /heals?\b/i },
  { name: 'treatment', pattern: /treatment\b/i },
  { name: 'clinical proof', pattern: /clinically\s+proven/i },
]

function collectSourceFiles(dir: string): string[] {
  const files: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) {
      // The test/setup directory holds the lint's own fixtures and harness.
      if (entry.name === 'test') continue
      files.push(...collectSourceFiles(path))
      continue
    }
    if (!['.ts', '.tsx'].includes(extname(entry.name))) continue
    if (entry.name.includes('.test.')) continue
    if (EXCLUDED_FILES.has(entry.name)) continue
    files.push(path)
  }
  return files
}

describe('frontend physiological-claims lint', () => {
  it('finds source files to scan (sanity)', () => {
    expect(collectSourceFiles(SRC_DIR).length).toBeGreaterThan(0)
  })

  it.each(CLAIM_PATTERNS.map((claim) => [claim.name, claim.pattern] as const))(
    'no source file makes the "%s" claim',
    (_name, pattern) => {
      for (const path of collectSourceFiles(SRC_DIR)) {
        const source = readFileSync(path, 'utf8')
        const violation = source.match(pattern)
        expect(
          violation?.[0],
          `${relative(SRC_DIR, path)} contains banned claim text "${violation?.[0]}"`,
        ).toBeUndefined()
      }
    },
  )
})
