/**
 * Design-token contract (docs/webapp-design.md §2): the sage palette must
 * exist verbatim in `src/styles/tokens.css`, and motion must be tokenized
 * behind a duration that honors the 160ms policy.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// vitest runs with the project root (web/) as cwd; jsdom rewrites
// import.meta.url to an http URL, so resolve from cwd instead.
const tokensCss = readFileSync(
  resolve(process.cwd(), 'src/styles/tokens.css'),
  'utf8',
)

const PALETTE: Record<string, string> = {
  '--bg': '#FAFAF7',
  '--surface': '#FFFFFF',
  '--surface-sunk': '#F1F2ED',
  '--border': '#E3E5E0',
  '--ink': '#1F2421',
  '--ink-muted': '#59615B',
  '--accent': '#4A7C59',
  '--accent-soft': '#E8F0EA',
  '--warning': '#7A5B14',
  '--warning-soft': '#F6EFDC',
  '--crisis': '#A33A32',
  '--crisis-soft': '#F8EAE8',
}

describe('design tokens', () => {
  it.each(Object.entries(PALETTE))(
    'defines %s with the approved value %s',
    (token, value) => {
      expect(tokensCss).toMatch(
        new RegExp(`^\\s*${token}:\\s*${value};\\s*$`, 'm'),
      )
    },
  )

  it('tokenizes motion behind a duration of at most 160ms', () => {
    const match = tokensCss.match(/--motion-duration:\s*(\d+)ms/)
    expect(match).not.toBeNull()
    const duration = Number(match?.[1])
    expect(Number.isFinite(duration)).toBe(true)
    expect(duration).toBeLessThanOrEqual(160)
  })
})
