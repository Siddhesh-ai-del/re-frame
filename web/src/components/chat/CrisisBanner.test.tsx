/**
 * CrisisBanner: sticky, assertive, non-dismissible fail-closed escalation
 * banner with the exact approved copy.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CrisisBanner } from './CrisisBanner'

describe('CrisisBanner', () => {
  it('renders with role="alert" and assertive live region', () => {
    render(<CrisisBanner />)
    const banner = screen.getByRole('alert')
    expect(banner).toHaveAttribute('aria-live', 'assertive')
  })

  it('shows the exact approved support copy', () => {
    render(<CrisisBanner />)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Immediate support matters right now. The resources below are free and available now.',
    )
  })

  it('is sticky and carries the warm amber-warn background (stage 6f)', () => {
    const { container } = render(<CrisisBanner />)
    const banner = container.querySelector('[data-testid="crisis-banner"]')
    expect(banner!.className).toContain('sticky')
    // Spec §5: the escalation banner restyles to amber-warn (same copy,
    // same role) — `bg-warning-soft` / `text-warning`, not crisis-red.
    expect(banner!.className).toContain('bg-warning-soft')
    expect(banner!.className).toContain('text-warning')
  })

  it('offers no close control (fail-closed, not dismissible)', () => {
    const { container } = render(<CrisisBanner />)
    expect(container.querySelector('button')).toBeNull()
  })
})
