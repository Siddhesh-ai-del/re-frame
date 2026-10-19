/**
 * GlassOrb (stage 6c/6f): signature liquid-glass usage site 2 of 3. With
 * motion on it mounts `@samasante/liquid-glass` through the shared
 * GlassSurface primitive; with reduced effects it renders a plain static
 * frosted circle instead (no lib mount at all).
 *
 * The lib is mocked here: jsdom has no ResizeObserver/canvas, and the point
 * of these tests is the wrapper's mount/fallback decision, not the lens math.
 */
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { EffectsProvider } from '../../effects/EffectsContext'
import { setMediaQuery } from '../../test/setup'
import { GlassOrb } from './GlassOrb'

const { glassMock } = vi.hoisted(() => ({ glassMock: vi.fn() }))

vi.mock('@samasante/liquid-glass', () => ({
  Glass: (props: { children?: ReactNode }) => {
    glassMock(props)
    return <div data-testid="mock-glass">{props.children}</div>
  },
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
  it('mounts the liquid-glass lib with the orb optics when motion is allowed', () => {
    renderOrb()

    expect(screen.getByTestId('glass-orb')).toBeInTheDocument()
    expect(screen.getByTestId('mock-glass')).toBeInTheDocument()
    const props = glassMock.mock.calls.at(-1)?.[0] as {
      optics?: Record<string, number>
    }
    expect(props.optics?.mapSize).toBe(256)
    expect(props.optics?.strength).toBe(0.85)
    expect(props.optics?.frost).toBe(0)
    expect(props.optics).not.toHaveProperty('filterResolution')
  })

  it('renders a static frosted fallback under reduced effects — no lib mount', () => {
    glassMock.mockClear()
    setMediaQuery(REDUCED_QUERY, true)
    renderOrb()

    const orb = screen.getByTestId('glass-orb')
    expect(orb).toBeInTheDocument()
    expect(orb).toHaveAttribute('data-fallback', 'frosted')
    expect(screen.queryByTestId('mock-glass')).not.toBeInTheDocument()
    expect(glassMock).not.toHaveBeenCalled()
  })
})
