/**
 * FrostClouds (stage 6d): the opt-in ambient canvas layer wrapping the
 * vendored Canvas UI clouds (see web/vendored/canvas-ui/NOTICE for the
 * license provenance). Contract under test here is the GATING, not the
 * drawing (jsdom cannot rasterize a canvas — the vendored module is mocked
 * to a marker element):
 *
 *  - default OFF (no storage → nothing rendered)
 *  - renders only when enabled AND reduced effects are false AND the tab is
 *    visible
 *  - same-tab sync: the 'reframe:frost-changed' event re-reads storage
 *  - pauses (unmounts) while the tab is hidden and resumes when visible
 *  - cleans up its listeners on unmount
 */
import { act, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FrostClouds, FROST_CHANGE_EVENT, FROST_STORAGE_KEY } from './FrostClouds'
import { EffectsProvider } from './EffectsContext'
import { setMediaQuery } from '../test/setup'

// The vendored component draws on a canvas; jsdom cannot rasterize, so the
// wrapper's gating is tested against a marker stand-in. The specifier must
// match FrostClouds.tsx's own import (`../../vendored/...`) so vitest
// resolves both to the same module id.
vi.mock('../../vendored/canvas-ui/Clouds', () => ({
  Clouds: () => <div data-testid="vendored-clouds" />,
}))

function renderFrost() {
  return render(
    <EffectsProvider>
      <FrostClouds />
    </EffectsProvider>,
  )
}

/** Force document.hidden and fire the visibilitychange listeners. */
function setHidden(hidden: boolean) {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    get: () => hidden,
  })
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'))
  })
}

beforeEach(() => {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    get: () => false,
  })
})

describe('FrostClouds gating', () => {
  it('renders nothing by default (opt-in, default OFF)', () => {
    const { container } = renderFrost()
    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByTestId('vendored-clouds')).not.toBeInTheDocument()
  })

  it('renders nothing when storage explicitly says off', () => {
    window.localStorage.setItem(FROST_STORAGE_KEY, 'off')
    const { container } = renderFrost()
    expect(container).toBeEmptyDOMElement()
  })

  it('renders the vendored clouds when enabled', () => {
    window.localStorage.setItem(FROST_STORAGE_KEY, 'on')
    renderFrost()
    expect(screen.getByTestId('vendored-clouds')).toBeInTheDocument()
  })

  it('reacts to the same-tab frost-changed event', () => {
    const { container } = renderFrost()
    expect(container).toBeEmptyDOMElement()

    window.localStorage.setItem(FROST_STORAGE_KEY, 'on')
    act(() => {
      window.dispatchEvent(new Event(FROST_CHANGE_EVENT))
    })
    expect(screen.getByTestId('vendored-clouds')).toBeInTheDocument()

    window.localStorage.setItem(FROST_STORAGE_KEY, 'off')
    act(() => {
      window.dispatchEvent(new Event(FROST_CHANGE_EVENT))
    })
    expect(screen.queryByTestId('vendored-clouds')).not.toBeInTheDocument()
  })

  it('renders nothing when reduced effects are resolved, even if enabled', () => {
    window.localStorage.setItem(FROST_STORAGE_KEY, 'on')
    window.localStorage.setItem('reframe:effects', 'off')
    const { container } = renderFrost()
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when the system signals reduced motion', () => {
    window.localStorage.setItem(FROST_STORAGE_KEY, 'on')
    setMediaQuery('(prefers-reduced-motion: reduce)', true)
    const { container } = renderFrost()
    expect(container).toBeEmptyDOMElement()
  })

  it('pauses while the tab is hidden and resumes when visible', () => {
    window.localStorage.setItem(FROST_STORAGE_KEY, 'on')
    renderFrost()
    expect(screen.getByTestId('vendored-clouds')).toBeInTheDocument()

    setHidden(true)
    expect(screen.queryByTestId('vendored-clouds')).not.toBeInTheDocument()

    setHidden(false)
    expect(screen.getByTestId('vendored-clouds')).toBeInTheDocument()
  })

  it('stops reacting to storage events after unmount (no leaked listeners)', () => {
    window.localStorage.setItem(FROST_STORAGE_KEY, 'on')
    const { unmount } = renderFrost()
    unmount()

    window.localStorage.setItem(FROST_STORAGE_KEY, 'on')
    expect(() => {
      window.dispatchEvent(new Event(FROST_CHANGE_EVENT))
    }).not.toThrow()
    expect(screen.queryByTestId('vendored-clouds')).not.toBeInTheDocument()
  })
})
