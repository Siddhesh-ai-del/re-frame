/**
 * GlassOrb (stage 6c): the ONE signature liquid-glass usage site. With motion
 * on it mounts `@samasante/liquid-glass`; with reduced effects it renders a
 * plain static frosted circle instead (no lib mount — design §3 row 7).
 *
 * The lib is mocked here: jsdom has no ResizeObserver/canvas, and the point
 * of these tests is the wrapper's mount/fallback decision, not the lens math.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EffectsProvider } from '../../effects/EffectsContext'
import { setMediaQuery } from '../../test/setup'
import { GlassOrb } from './GlassOrb'

vi.mock('@samasante/liquid-glass', () => ({
  Glass: () => <div data-testid="mock-glass" />,
}))

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)'

function renderOrb() {
  return render(
    <EffectsProvider>
      <GlassOrb />
    </EffectsProvider>,
  )
}

describe('GlassOrb', () => {
  it('mounts the liquid-glass lib when motion is allowed', () => {
    renderOrb()

    expect(screen.getByTestId('glass-orb')).toBeInTheDocument()
    expect(screen.getByTestId('mock-glass')).toBeInTheDocument()
  })

  it('renders a static frosted fallback under reduced effects — no lib mount', () => {
    setMediaQuery(REDUCED_QUERY, true)
    renderOrb()

    const orb = screen.getByTestId('glass-orb')
    expect(orb).toBeInTheDocument()
    expect(orb).toHaveAttribute('data-fallback', 'frosted')
    expect(screen.queryByTestId('mock-glass')).not.toBeInTheDocument()
  })
})
