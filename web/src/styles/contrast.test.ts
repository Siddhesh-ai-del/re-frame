/**
 * Golden Glass a11y contract (stage 6f): WCAG 2.2 AA contrast for the token
 * pairs that carry TEXT, per .plans/stage-6f-golden-glass-spec.md §1/§2.
 * Enforced at the unit level so a palette regression fails in `npm test`,
 * not only in the axe E2E gate.
 *
 * Two documented guards, kept from the sage era because the same anti-pattern
 * exists in this palette too:
 *  1. `--accent` on `--accent-soft` MUST stay < 4.5 (it is 4.48) — so
 *     selected/tinted states use `--accent-ink` (6.12) for accent TEXT.
 *  2. `--accent-bright` is decorative only (dots, gradients, chart bars) and
 *     is never a text background.
 *
 * CTA gradient pairs are included as hex tokens (`--cta-start`, `--cta-end`,
 * `--cta-text`) so the extractor can read them even though they render as a
 * gradient background.
 *
 * Ratios use the WCAG 2.x relative-luminance formula (same as axe-core).
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// Strip /* … */ comments so token lines with inline rationale still match
// the declaration regexes below (values stay byte-identical to the spec).
const tokensCss = readFileSync(
  resolve(process.cwd(), 'src/styles/tokens.css'),
  'utf8',
).replace(/\/\*[\s\S]*?\*\//g, '')

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
  // Accent TEXT states (derived token — see guard below).
  ['--accent-ink', '--accent-soft'],
  ['--accent-ink', '--bg'],
  ['--accent', '--bg'],
  ['--accent', '--surface'],
  // Primary ink.
  ['--ink', '--bg'],
  ['--ink', '--surface'],
  ['--ink-on', '--ink'], // ink-pill text (active nav, selected chips)
  ['--ink-muted', '--bg'],
  ['--ink-muted', '--surface'],
  ['--ink-muted', '--surface-sunk'],
  ['--ink-muted', '--accent-soft'],
  // Semantic surfaces (crisis banner, warning strip).
  ['--warning', '--warning-soft'],
  ['--warning', '--bg'],
  ['--crisis', '--crisis-soft'],
  ['--crisis', '--bg'],
  // CTA gradient: light text over both stops (stage 6f).
  ['--cta-text', '--cta-start'],
  ['--cta-text', '--cta-end'],
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
    // must not render `--accent` text on `--accent-soft` (4.48:1 — below AA).
    expect(contrast(token('--accent'), token('--accent-soft'))).toBeLessThan(4.5)
    expect(contrast(token('--accent-ink'), token('--accent-soft'))).toBeGreaterThanOrEqual(
      4.5,
    )
  })

  it('keeps accent-bright decorative-only (never a text background)', () => {
    // #E8853C is too light to carry text at AA — it is allowed only for
    // dots, gradients and chart fills (spec §1 "decorative only").
    expect(contrast(token('--ink'), token('--accent-bright'))).toBeGreaterThanOrEqual(4.5)
    expect(
      contrast(token('--cta-text'), token('--accent-bright')),
    ).toBeLessThan(4.5)
  })
})
