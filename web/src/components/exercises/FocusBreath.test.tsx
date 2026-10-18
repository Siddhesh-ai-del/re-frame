/**
 * FocusBreath (stage 6c): a claim-free, one-minute paced-breathing break.
 * Verifies the full lifecycle (start → countdown advances → phase advances →
 * pause → stop → completion), interval cleanup on unmount (no leaks), and
 * the reduced-motion static mode (text cue + countdown, NO animated circle).
 *
 * The copy must stay strictly descriptive — the claims lint enforces that
 * separately; these tests pin the behavior.
 */
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EffectsProvider } from '../../effects/EffectsContext'
import { setMediaQuery } from '../../test/setup'
import { FocusBreath } from './FocusBreath'

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)'

function renderBreath() {
  return render(
    <EffectsProvider>
      <FocusBreath />
    </EffectsProvider>,
  )
}

function setupUser() {
  // user-event awaits its own promise chain, which never resolves under
  // `vi.useFakeTimers()` unless the fake clock also advances real time.
  // `shouldAdvanceTime` ticks the fake clock alongside real time so those
  // awaits settle, while tests still drive the session via
  // `vi.advanceTimersByTime` for precise second-by-second assertions.
  vi.useFakeTimers({ shouldAdvanceTime: true })
  return userEvent.setup({
    advanceTimers: (ms) => vi.advanceTimersByTime(ms),
  })
}

afterEach(() => {
  vi.useRealTimers()
})

describe('FocusBreath — lifecycle', () => {
  it('starts idle with the full countdown and a Start button', () => {
    vi.useFakeTimers()
    renderBreath()

    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('1:00')
    expect(screen.getByRole('button', { name: 'Start' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
  })

  it('Start begins the session: the countdown advances every second', async () => {
    const user = setupUser()
    renderBreath()

    await user.click(screen.getByRole('button', { name: 'Start' }))
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('1:00')

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('0:59')
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()
  })

  it('advances through the in/hold/out phases as the session runs', async () => {
    const user = setupUser()
    renderBreath()

    await user.click(screen.getByRole('button', { name: 'Start' }))
    // 4s in-phase, then hold, then out — the circle carries the phase marker.
    act(() => {
      vi.advanceTimersByTime(4000)
    })
    expect(screen.getByTestId('breath-circle')).toHaveAttribute('data-phase', 'hold')
    act(() => {
      vi.advanceTimersByTime(2000)
    })
    expect(screen.getByTestId('breath-circle')).toHaveAttribute('data-phase', 'out')
  })

  it('Pause freezes the countdown and Stop resets to idle', async () => {
    const user = setupUser()
    renderBreath()

    await user.click(screen.getByRole('button', { name: 'Start' }))
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    await user.click(screen.getByRole('button', { name: 'Pause' }))
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('0:57')
    expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Stop' }))
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('1:00')
    expect(screen.getByRole('button', { name: 'Start' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
  })

  it('completes the one-minute session with an honest done state', async () => {
    const user = setupUser()
    renderBreath()

    await user.click(screen.getByRole('button', { name: 'Start' }))
    act(() => {
      vi.advanceTimersByTime(60000)
    })
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('0:00')
    expect(screen.getByText('That was a minute.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument()

    // Start again restarts a fresh minute.
    await user.click(screen.getByRole('button', { name: 'Start' }))
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('1:00')
  })

  it('is operable from the keyboard alone', async () => {
    const user = setupUser()
    renderBreath()

    await user.tab()
    expect(screen.getByRole('button', { name: 'Start' })).toHaveFocus()
    await user.keyboard('{Enter}')
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('0:59')
  })

  it('clears its interval on unmount (no timer leak)', async () => {
    const user = setupUser()
    const { unmount } = renderBreath()

    await user.click(screen.getByRole('button', { name: 'Start' }))
    expect(vi.getTimerCount()).toBeGreaterThan(0)

    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
})

describe('FocusBreath — reduced motion', () => {
  it('renders a static text cue and countdown instead of the animated circle', async () => {
    setMediaQuery(REDUCED_QUERY, true)
    const user = setupUser()
    renderBreath()

    expect(screen.queryByTestId('breath-circle')).not.toBeInTheDocument()
    expect(screen.getByTestId('breath-cue')).toHaveTextContent('in for 4, hold for 2, out for 6')

    // The countdown still works — it is text, not motion.
    await user.click(screen.getByRole('button', { name: 'Start' }))
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByTestId('breath-countdown')).toHaveTextContent('0:59')
    expect(screen.queryByTestId('breath-circle')).not.toBeInTheDocument()
  })
})
