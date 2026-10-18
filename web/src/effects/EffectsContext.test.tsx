/**
 * Reduced-effects engine: an in-app motion preference (system/on/off) layered
 * over the OS `prefers-reduced-motion` signal, persisted to localStorage and
 * mirrored onto `<html data-reduced-effects>` for CSS gating.
 */
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { listenerCount, setMediaQuery } from '../test/setup'
import { EffectsProvider, useReducedEffects } from './EffectsContext'

const QUERY = '(prefers-reduced-motion: reduce)'
const STORAGE_KEY = 'reframe:effects'

function Probe() {
  const { reducedEffects, preference, setPreference } = useReducedEffects()
  return (
    <div>
      <output data-testid="reduced">{String(reducedEffects)}</output>
      <output data-testid="preference">{preference}</output>
      <button type="button" onClick={() => setPreference('on')}>
        Always on
      </button>
      <button type="button" onClick={() => setPreference('off')}>
        Always off
      </button>
      <button type="button" onClick={() => setPreference('system')}>
        Follow system
      </button>
    </div>
  )
}

function renderProvider() {
  return render(
    <EffectsProvider>
      <Probe />
    </EffectsProvider>,
  )
}

describe('EffectsProvider / useReducedEffects', () => {
  it('defaults to the system preference with the OS signal (no reduce)', () => {
    renderProvider()
    expect(screen.getByTestId('preference')).toHaveTextContent('system')
    expect(screen.getByTestId('reduced')).toHaveTextContent('false')
  })

  it('follows an OS reduce signal under the system preference', () => {
    setMediaQuery(QUERY, true)
    renderProvider()
    expect(screen.getByTestId('reduced')).toHaveTextContent('true')
  })

  it('lets preference "on" override an OS reduce signal', async () => {
    setMediaQuery(QUERY, true)
    const user = userEvent.setup()
    renderProvider()
    await user.click(screen.getByRole('button', { name: 'Always on' }))
    expect(screen.getByTestId('reduced')).toHaveTextContent('false')
    expect(screen.getByTestId('preference')).toHaveTextContent('on')
  })

  it('lets preference "off" override a non-reduce OS signal', async () => {
    const user = userEvent.setup()
    renderProvider()
    await user.click(screen.getByRole('button', { name: 'Always off' }))
    expect(screen.getByTestId('reduced')).toHaveTextContent('true')
    expect(screen.getByTestId('preference')).toHaveTextContent('off')
  })

  it('persists the preference to localStorage and restores it on remount', async () => {
    const user = userEvent.setup()
    const first = renderProvider()
    await user.click(screen.getByRole('button', { name: 'Always off' }))
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('off')
    first.unmount()

    renderProvider()
    expect(screen.getByTestId('preference')).toHaveTextContent('off')
    expect(screen.getByTestId('reduced')).toHaveTextContent('true')
  })

  it('reacts to OS preference changes while following the system', () => {
    renderProvider()
    expect(screen.getByTestId('reduced')).toHaveTextContent('false')
    act(() => setMediaQuery(QUERY, true))
    expect(screen.getByTestId('reduced')).toHaveTextContent('true')
    act(() => setMediaQuery(QUERY, false))
    expect(screen.getByTestId('reduced')).toHaveTextContent('false')
  })

  it('mirrors the resolved value onto documentElement.dataset.reducedEffects', () => {
    const { unmount } = renderProvider()
    expect(document.documentElement.dataset.reducedEffects).toBe('false')
    act(() => setMediaQuery(QUERY, true))
    expect(document.documentElement.dataset.reducedEffects).toBe('true')
    unmount()
  })

  it('registers a media-query listener only while following the system', async () => {
    const user = userEvent.setup()
    const { unmount } = renderProvider()
    expect(listenerCount(QUERY)).toBe(1)

    await user.click(screen.getByRole('button', { name: 'Always off' }))
    expect(listenerCount(QUERY)).toBe(0)

    await user.click(screen.getByRole('button', { name: 'Follow system' }))
    expect(listenerCount(QUERY)).toBe(1)

    unmount()
    expect(listenerCount(QUERY)).toBe(0)
  })

  it('ignores an invalid stored preference', () => {
    window.localStorage.setItem(STORAGE_KEY, 'banana')
    renderProvider()
    expect(screen.getByTestId('preference')).toHaveTextContent('system')
  })

  it('falls back to the system preference when storage is unavailable', () => {
    const original = window.localStorage
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: () => {
          throw new Error('storage blocked')
        },
        setItem: () => {
          throw new Error('storage blocked')
        },
      },
    })
    try {
      renderProvider()
      expect(screen.getByTestId('preference')).toHaveTextContent('system')
    } finally {
      Object.defineProperty(window, 'localStorage', {
        configurable: true,
        value: original,
      })
    }
  })

  it('keeps the in-session preference when persisting fails', async () => {
    const original = window.localStorage
    const backing = new Map<string, string>()
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => backing.get(key) ?? null,
        setItem: () => {
          throw new Error('storage blocked')
        },
      },
    })
    try {
      const user = userEvent.setup()
      renderProvider()
      await user.click(screen.getByRole('button', { name: 'Always off' }))
      expect(screen.getByTestId('preference')).toHaveTextContent('off')
      expect(screen.getByTestId('reduced')).toHaveTextContent('true')
    } finally {
      Object.defineProperty(window, 'localStorage', {
        configurable: true,
        value: original,
      })
    }
  })

  it('throws when the hook is used outside a provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Probe />)).toThrow(
      'useReducedEffects must be used within an EffectsProvider',
    )
    spy.mockRestore()
  })
})
