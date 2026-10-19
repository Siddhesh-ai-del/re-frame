/**
 * ProgressRing (stage 6d): a hand-rolled SVG arc for the MOST RECENT total
 * within [total_min, total_max], with the published severity label and the
 * instrument citation as text, in neutral (ink/accent) colors only.
 *
 * Animation decision (spec §C): the ring NEVER animates its value — no
 * draw-in, no transition — so there is no reduced-motion divergence to
 * police; these tests pin that down in both motion modes.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProgressRing } from './ProgressRing'

const CITATION = 'Kroenke, Spitzer & Williams 2001'

function renderRing(
  props: Partial<React.ComponentProps<typeof ProgressRing>> = {},
) {
  return render(
    <ProgressRing
      value={6}
      totalMin={0}
      totalMax={27}
      severityLabel="mild"
      citation={CITATION}
      {...props}
    />,
  )
}

describe('ProgressRing', () => {
  it('renders an accessible progress indicator with the latest value', () => {
    renderRing()
    const meter = screen.getByRole('progressbar')
    expect(meter).toHaveAttribute('aria-valuenow', '6')
    expect(meter).toHaveAttribute('aria-valuemin', '0')
    expect(meter).toHaveAttribute('aria-valuemax', '27')
    expect(screen.getByText('6')).toBeInTheDocument()
  })

  it('renders the published severity label and citation verbatim', () => {
    renderRing()
    expect(screen.getByText('mild')).toBeInTheDocument()
    expect(screen.getByText(CITATION)).toBeInTheDocument()
  })

  it('renders an SVG arc', () => {
    const { container } = renderRing()
    expect(container.querySelector('svg')).not.toBeNull()
  })

  it('never animates, in either motion mode', () => {
    const { container, rerender } = renderRing()
    expect(container.querySelectorAll('[class*="animate"]')).toHaveLength(0)
    expect(container.querySelectorAll('[style*="transition"]')).toHaveLength(0)

    rerender(
      <ProgressRing
        value={6}
        totalMin={0}
        totalMax={27}
        severityLabel="mild"
        citation={CITATION}
        reducedMotion
      />,
    )
    expect(container.querySelectorAll('[class*="animate"]')).toHaveLength(0)
  })

  it('clamps the arc ratio into the 0..1 range', () => {
    const { container } = renderRing({ value: 40 })
    const meter = screen.getByRole('progressbar')
    // The reported value stays honest even when out of range…
    expect(meter).toHaveAttribute('aria-valuenow', '40')
    // …and the drawn arc still fits the ring (stroke-dasharray capped).
    const circle = container.querySelector('circle')
    expect(circle).not.toBeNull()
  })

  it('handles a null severity label without a placeholder', () => {
    renderRing({ severityLabel: null })
    expect(screen.queryByText(/unknown|n\/a/i)).not.toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
  })
})
