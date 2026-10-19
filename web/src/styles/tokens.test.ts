/**
 * Design-token contract (stage 6f): the Golden Glass palette must exist
 * verbatim in `src/styles/tokens.css` (values pinned by
 * .plans/stage-6f-golden-glass-spec.md §1), and motion must be tokenized
 * behind a duration that honors the 160ms policy.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// vitest runs with the project root (web/) as cwd; jsdom rewrites
// import.meta.url to an http URL, so resolve from cwd instead. Comments are
// stripped so declarations with inline rationale still match byte-for-byte.
const tokensCss = readFileSync(
  resolve(process.cwd(), 'src/styles/tokens.css'),
  'utf8',
).replace(/\/\*[\s\S]*?\*\//g, '')

const PALETTE: Record<string, string> = {
  '--bg': '#FFF4E4',
  '--surface': '#FFFCF7',
  '--surface-sunk': '#F5E7D0',
  '--border': '#EAD9C2',
  '--ink': '#34261A',
  '--ink-muted': '#6E5847',
  '--accent': '#A8501C',
  '--accent-soft': '#FAE5CD',
  '--accent-ink': '#8A3F14',
  '--accent-bright': '#E8853C',
  '--cta-start': '#A8501C',
  '--cta-end': '#8A3F14',
  '--cta-text': '#FFF9F0',
  '--cta-hover': '#7A3611',
  '--warning': '#6E5210',
  '--warning-soft': '#F6EBD2',
  '--crisis': '#8F2F27',
  '--crisis-soft': '#F8E7E4',
  // Landscape (decorative).
  '--sky-top': '#FFF4E4',
  '--sky-mid': '#FFE8CC',
  '--sky-low': '#F9E0C6',
  '--hill-1': '#CBD9BA',
  '--hill-2': '#AFC7A4',
  '--hill-3': '#8FAD92',
  '--sun-core': '#FFFAF0',
  '--sun-edge': '#FFC988',
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

  it('defines the glass and radius shape tokens', () => {
    expect(tokensCss).toMatch(/--ink-on:\s*#FFF6EA/)
    expect(tokensCss).toMatch(/--panel:\s*rgba\(255, 251, 243, 0\.86\)/)
    expect(tokensCss).toMatch(/--glass-tint:\s*rgba\(255, 252, 246, 0\.42\)/)
    expect(tokensCss).toMatch(/--glass-edge:\s*rgba\(255, 255, 255, 0\.72\)/)
    expect(tokensCss).toMatch(/--radius-card:\s*26px/)
    expect(tokensCss).toMatch(/--radius-input:\s*18px/)
    expect(tokensCss).toMatch(/--font-display:\s*ui-serif/)
  })

  it('tokenizes motion behind a duration of at most 160ms', () => {
    const match = tokensCss.match(/--motion-duration:\s*(\d+)ms/)
    expect(match).not.toBeNull()
    const duration = Number(match?.[1])
    expect(Number.isFinite(duration)).toBe(true)
    expect(duration).toBeLessThanOrEqual(160)
  })
})
