/**
 * TextReel (stage 6c): the onboarding flip-headline. Cycles a few short words
 * and settles on the final headline; under reduced effects it renders the
 * final text STATIC immediately — no timer, no churn (design §3 row 9).
 */
import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EffectsProvider } from '../../effects/EffectsContext'
import { setMediaQuery } from '../../test/setup'
import { TextReel } from './TextReel'

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)'

function renderReel(words: string[], finalText: string, intervalMs = 100) {
  return render(
    <EffectsProvider>
      <TextReel words={words} finalText={finalText} intervalMs={intervalMs} />
    </EffectsProvider>,
  )
}

afterEach(() => {
  vi.useRealTimers()
})

describe('TextReel — animated mode', () => {
  it('cycles through the words and settles on the final headline', () => {
    vi.useFakeTimers()
    renderReel(['Pause', 'Notice'], 'Welcome to RE:FRAME.')

    expect(screen.getByTestId('text-reel')).toHaveTextContent('Pause')
    act(() => {
      vi.advanceTimersByTime(100)
    })
    expect(screen.getByTestId('text-reel')).toHaveTextContent('Notice')
    act(() => {
      vi.advanceTimersByTime(100)
    })
    expect(screen.getByTestId('text-reel')).toHaveTextContent('Welcome to RE:FRAME.')
  })

  it('settles permanently and clears its timer once the final text shows', () => {
    vi.useFakeTimers()
    renderReel(['Pause'], 'Welcome to RE:FRAME.')

    act(() => {
      vi.advanceTimersByTime(100)
    })
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.getByTestId('text-reel')).toHaveTextContent('Welcome to RE:FRAME.')
    expect(vi.getTimerCount()).toBe(0)
  })
})

describe('TextReel — reduced motion', () => {
  it('renders the final text static immediately, with no timers at all', () => {
    setMediaQuery(REDUCED_QUERY, true)
    vi.useFakeTimers()
    renderReel(['Pause', 'Notice'], 'Welcome to RE:FRAME.')

    // Static from the very first paint — the intermediate words never show.
    expect(screen.getByTestId('text-reel')).toHaveTextContent('Welcome to RE:FRAME.')
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.getByTestId('text-reel')).toHaveTextContent('Welcome to RE:FRAME.')
    expect(vi.getTimerCount()).toBe(0)
  })
})
