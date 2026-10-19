/**
 * Stage 6e a11y contract: WCAG 2.2 AA contrast for the token pairs that carry
 * TEXT (docs/webapp-design.md §5.5 "axe-clean in E2E" — enforced here at the
 * unit level so a palette regression fails in `npm test`, not only in E2E).
 *
 * Why `--accent-ink` exists (documented deviation): the design doc pins
 * `--accent: #4A7C59` and `--accent-soft: #E8F0EA`, and that pair measures
 * 4.19:1 — below the 4.5:1 required for normal-size text, which axe flagged
 * on all five routes (active nav links + selected instrument chips). The doc
 * is immutable this stage, so the FIX is a derived text token: accent text
 * over accent-soft backgrounds uses `--accent-ink`, a darker sage verified
 * here at ≥4.5:1 over both the tint and the page background.
 *
 * Ratios use the WCAG 2.x relative-luminance formula (same as axe-core).
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const tokensCss = readFileSync(
  resolve(process.cwd(), 'src/styles/tokens.css'),
  'utf8',
)

/** Extract a `--token: #RRGGBB;` declaration from tokens.css. */
function token(name: string): string {
  const match = tokensCss.match(new RegExp(`^\\s*${name}:\\s*(#[0-9A-Fa-f]{6});\\s*$`, 'm'))
  expect(match, `token ${name} must be declared in tokens.css`).not.toBeNull()
  return match?.[1] as string
}

/** WCAG 2.x relative luminance of a #RRGGBB color. */
function luminance(hex: string): number {
  const channel = (index: number): number => {
    const c = parseInt(hex.slice(index, index + 2), 16) / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  const r = channel(1)
  const g = channel(3)
  const b = channel(5)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** Contrast ratio of two colors (1..21). */
function contrast(a: string, b: string): number {
  const la = luminance(a)
  const lb = luminance(b)
  const hi = Math.max(la, lb)
  const lo = Math.min(la, lb)
  return (hi + 0.05) / (lo + 0.05)
}

/** Text pairs the UI actually renders, each required to clear AA (4.5:1). */
const TEXT_PAIRS: ReadonlyArray<readonly [foreground: string, background: string]> = [
  // The a11y fix (stage 6e): accent TEXT over accent-soft SELECTED states.
  ['--accent-ink', '--accent-soft'],
  ['--accent-ink', '--bg'],
  // Existing contracts, pinned so the palette cannot silently regress.
  ['--accent', '--bg'],
  ['--accent', '--surface'],
  ['--ink', '--bg'],
  ['--ink', '--surface'],
  ['--ink-muted', '--bg'],
  ['--ink-muted', '--surface'],
  ['--ink-muted', '--surface-sunk'],
  ['--ink-muted', '--accent-soft'],
  ['--warning', '--warning-soft'],
  ['--warning', '--bg'],
  ['--crisis', '--crisis-soft'],
  ['--crisis', '--bg'],
]

describe('token contrast (WCAG 2.2 AA)', () => {
  it.each(TEXT_PAIRS)(
    '%s on %s meets 4.5:1 for normal-size text',
    (fg, bg) => {
      const ratio = contrast(token(fg), token(bg))
      expect(ratio).toBeGreaterThanOrEqual(4.5)
    },
  )

  it('exposes the derived accent text token for selected states', () => {
    // Guard the anti-pattern this token exists to prevent: selected states
    // must not render `--accent` text on `--accent-soft` (4.19:1, axe-flagged).
    expect(contrast(token('--accent'), token('--accent-soft'))).toBeLessThan(4.5)
    expect(contrast(token('--accent-ink'), token('--accent-soft'))).toBeGreaterThanOrEqual(
      4.5,
    )
  })
})
