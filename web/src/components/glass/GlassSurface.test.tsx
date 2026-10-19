/**
 * GlassSurface (stage 6f): THE shared liquid-glass primitive behind the
 * app's exactly-3 lens sites (nav pill, hero orb, chat composer) —
 * spec §4 (.plans/stage-6f-golden-glass-spec.md).
 *
 * Contract under test:
 *  - effects allowed → `@samasante/liquid-glass` <Glass> mounts in MATERIAL
 *    mode with the variant's pinned optics and NO `filterResolution` prop
 *    (passing it disqualifies material mode and refracts children).
 *  - reduced effects → a plain static div (`data-fallback="static"`) and the
 *    lib is never executed (mock asserted not called).
 *  - children always render (crisp, inside the lens row).
 *
 * The lib is mocked: jsdom has no canvas/WebGL, and these tests are about
 * the wrapper's mount/optics decision, not the lens math.
 */
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { EffectsProvider } from '../../effects/EffectsContext'
import { setMediaQuery } from '../../test/setup'
import { GlassSurface, GLASS_OPTICS, type GlassVariant } from './GlassSurface'

const { glassMock } = vi.hoisted(() => ({
  glassMock: vi.fn(),
}))

vi.mock('@samasante/liquid-glass', () => ({
  Glass: (props: { children?: ReactNode }) => {
    glassMock(props)
    return <div data-testid="mock-glass">{props.children}</div>
  },
}))

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)'

function renderSurface(variant: GlassVariant, props: Record<string, unknown> = {}) {
  return render(
    <GlassSurface variant={variant} {...props}>
      <span>child content</span>
    </GlassSurface>,
  )
}

describe('GlassSurface', () => {
  it('mounts the liquid-glass lib with the nav optics when effects are allowed', () => {
    renderSurface('nav')

    expect(screen.getByTestId('mock-glass')).toBeInTheDocument()
    expect(glassMock).toHaveBeenCalledTimes(1)
    const props = glassMock.mock.calls[0]?.[0] as { optics?: Record<string, number> }
    expect(props.optics).toEqual(GLASS_OPTICS.nav)
    expect(props.optics?.mapSize).toBe(256)
    expect(props.optics?.frost).toBe(0)
  })

  it('never passes filterResolution (it disqualifies material mode)', () => {
    renderSurface('nav')
    renderSurface('orb', { size: 120 })
    renderSurface('composer')

    for (const call of glassMock.mock.calls) {
      expect(call[0]).not.toHaveProperty('filterResolution')
    }
  })

  it.each<[GlassVariant, Record<string, number>]>([
    ['nav', { strength: 0.55, depth: 0.9, curvature: 0.62, dispersion: 0.55 }],
    ['orb', { strength: 0.85, depth: 1, curvature: 0.95, dispersion: 0.8 }],
    ['composer', { strength: 0.6, depth: 0.92, curvature: 0.68, dispersion: 0.6 }],
  ])('uses the %s variant optics from the approved mockups', (variant, expected) => {
    renderSurface(variant)
    const props = glassMock.mock.calls.at(-1)?.[0] as { optics?: Record<string, number> }
    for (const [key, value] of Object.entries(expected)) {
      expect(props.optics?.[key]).toBe(value)
    }
  })

  it('renders children inside the lens row', () => {
    renderSurface('nav')
    expect(screen.getByText('child content')).toBeInTheDocument()
  })

  it('renders a static fallback under reduced effects — lib never executed', () => {
    setMediaQuery(REDUCED_QUERY, true)
    glassMock.mockClear()
    renderSurface('composer', { testId: 'composer-glass' })

    expect(glassMock).not.toHaveBeenCalled()
    expect(screen.queryByTestId('mock-glass')).not.toBeInTheDocument()
    const fallback = screen.getByTestId('composer-glass')
    expect(fallback).toHaveAttribute('data-fallback', 'static')
    expect(fallback).toHaveTextContent('child content')
  })

  it('assumes effects are allowed when rendered outside an EffectsProvider', () => {
    // The ChatPage composer renders GlassSurface without a provider in
    // Composer.test.tsx — the optional hook must default to lens-mounted.
    glassMock.mockClear()
    render(
      <GlassSurface variant="composer">
        <span>no provider</span>
      </GlassSurface>,
    )
    expect(glassMock).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('mock-glass')).toBeInTheDocument()
  })

  it('renders the static fallback when the stored preference turns effects off', () => {
    window.localStorage.setItem('reframe:effects', 'off')
    glassMock.mockClear()
    render(
      <EffectsProvider>
        <GlassSurface variant="nav" testId="nav-glass" />
      </EffectsProvider>,
    )
    expect(glassMock).not.toHaveBeenCalled()
    expect(screen.getByTestId('nav-glass')).toHaveAttribute(
      'data-fallback',
      'static',
    )
  })
})
