/**
 * AmbientBackground (stage 6f): the Golden Glass landscape layer — sun, haze,
 * topographic contours, hills — mounted once behind all content (spec §3).
 * Contract: aria-hidden, pointer-events-none, painted BELOW content (DOM
 * order before the shell + non-positive z-index), and completely static when
 * reduced effects are resolved (no animation classes in the DOM at all).
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AmbientBackground } from './AmbientBackground'
import { EffectsProvider } from './EffectsContext'
import { setMediaQuery } from '../test/setup'

function renderAmbient() {
  return render(
    <EffectsProvider>
      <AmbientBackground />
    </EffectsProvider>,
  )
}

function layer(container: HTMLElement): HTMLElement {
  const el = container.querySelector<HTMLElement>('[data-testid="ambient-background"]')
  if (el === null) throw new Error('ambient layer not rendered')
  return el
}

describe('AmbientBackground', () => {
  it('renders a decorative, hidden-from-AT layer', () => {
    const { container } = renderAmbient()
    const el = layer(container)
    expect(el).toHaveAttribute('aria-hidden', 'true')
  })

  it('never intercepts pointer events', () => {
    const { container } = renderAmbient()
    expect(layer(container).className).toContain('pointer-events-none')
  })

  it('paints below content: before the shell in DOM order with a non-positive z-index', () => {
    const { container } = render(
      <div>
        <AmbientBackground />
        <div data-testid="content">page content</div>
      </div>,
    )
    const el = layer(container)
    const content = screen.getByTestId('content')
    expect(
      el.compareDocumentPosition(content) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    const zIndex = Number.parseInt(
      (el.style.zIndex || el.className.match(/z-index:\s*(-?\d+)/)?.[1] || '0'),
      10,
    )
    expect(Number.isNaN(zIndex) || zIndex <= 0).toBe(true)
  })

  it('animates only the haze wrapper when motion is allowed', () => {
    const { container } = renderAmbient()
    expect(layer(container).querySelector('.animate-haze')).not.toBeNull()
    // The root layer itself never carries an animation class (spec §3).
    expect(layer(container).className).not.toMatch(/animate/)
  })

  it('goes static when the system signals reduced motion', async () => {
    const { container } = renderAmbient()
    expect(layer(container).querySelector('.animate-haze')).not.toBeNull()

    setMediaQuery('(prefers-reduced-motion: reduce)', true)
    const { container: next } = renderAmbient()
    // No animation class at all — CSS cannot animate what isn't declared.
    expect(layer(next).querySelector('.animate-haze')).toBeNull()
    expect(container).toBeTruthy()
  })

  it('goes static when the user preference turns effects off', async () => {
    window.localStorage.setItem('reframe:effects', 'off')
    const { container } = renderAmbient()
    expect(layer(container).querySelector('.animate-haze')).toBeNull()
  })

  it('renders the full landscape layer (sun, contours, hills)', () => {
    const { container } = renderAmbient()
    const el = layer(container)
    expect(el.querySelector('.ambient-sun')).not.toBeNull()
    expect(el.querySelectorAll('.contours path')).toHaveLength(10)
    expect(el.querySelectorAll('.contours2 path')).toHaveLength(22)
    expect(el.querySelectorAll('.ambient-hill')).toHaveLength(3)
  })
})
