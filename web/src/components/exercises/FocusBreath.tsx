/**
 * FocusBreath (stage 6c): a claim-free, one-minute paced-breathing break.
 * adapted from opensourceui (MIT) — reshaped to the RE:FRAME honesty rules.
 *
 * Copy is STRICTLY descriptive (design §3 row 2): "a minute of paced
 * breathing", "Follow the cue: in for 4, hold for 2, out for 6" — zero
 * physiological or outcome claims (enforced separately by the claims lint).
 *
 * Motion contract: with motion allowed, a soft circle scales with the phase
 * (≤160ms transitions); under reduced effects there is NO circle animation —
 * a static text cue + the countdown instead. The countdown is text in BOTH
 * modes. All controls are native buttons (keyboard-operable by default). The
 * interval is cleared on unmount — no timer leaks.
 */
import { useEffect, useState } from 'react'
import { useReducedEffects } from '../../effects/EffectsContext'

/** Phase lengths in seconds: the 4-2-6 pattern, one 12s cycle. */
const PHASES = [
  { name: 'in', seconds: 4, scale: 'scale-100' },
  { name: 'hold', seconds: 2, scale: 'scale-110' },
  { name: 'out', seconds: 6, scale: 'scale-90' },
] as const

const CYCLE_SECONDS = PHASES.reduce((sum, phase) => sum + phase.seconds, 0)
const SESSION_SECONDS = 60

type Status = 'idle' | 'running' | 'paused' | 'done'

function phaseAt(elapsed: number): (typeof PHASES)[number] {
  const position = elapsed % CYCLE_SECONDS
  let cursor = 0
  for (const phase of PHASES) {
    cursor += phase.seconds
    if (position < cursor) return phase
  }
  return PHASES[0]!
}

function formatClock(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

const CUE_TEXT = 'Follow the cue: in for 4, hold for 2, out for 6.'

export function FocusBreath() {
  const { reducedEffects } = useReducedEffects()
  const [status, setStatus] = useState<Status>('idle')
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    // Guard on elapsed too: once the minute is over the interval is torn down
    // on the next render instead of ticking against a clamped clock.
    if (status !== 'running' || elapsed >= SESSION_SECONDS) return
    const interval = setInterval(() => {
      setElapsed((previous) => Math.min(previous + 1, SESSION_SECONDS))
    }, 1000)
    return () => clearInterval(interval)
  }, [status, elapsed])

  // Completion is DERIVED, never set: when the running clock reaches the end
  // the component simply presents the done state — no cascading effect, and
  // the state updaters stay pure.
  const effectiveStatus: Status =
    status === 'running' && elapsed >= SESSION_SECONDS ? 'done' : status

  const remaining = SESSION_SECONDS - elapsed
  const phase = phaseAt(elapsed)
  const scaleClass = PHASES.find((p) => p.name === phase.name)?.scale ?? 'scale-100'

  function start() {
    // "Start" both begins a fresh minute (idle/done) and resumes (paused).
    if (status === 'paused') {
      setStatus('running')
      return
    }
    setElapsed(0)
    setStatus('running')
  }

  function stop() {
    setStatus('idle')
    setElapsed(0)
  }

  return (
    <section aria-label="Focus breath" className="flex flex-col gap-3">
      <h2 className="text-xl font-medium text-ink">Focus breath</h2>
      <p className="text-ink-muted">A minute of paced breathing. {CUE_TEXT}</p>
      <div className="flex items-center gap-4">
        {reducedEffects ? (
          <p data-testid="breath-cue" className="text-lg text-ink">
            {CUE_TEXT}
          </p>
        ) : (
          <div
            data-testid="breath-circle"
            data-phase={status === 'idle' ? 'idle' : phase.name}
            aria-hidden="true"
            className={`h-24 w-24 rounded-full border border-border bg-accent-soft transition-transform duration-150 ease-out ${scaleClass}`}
          />
        )}
        <p
          data-testid="breath-countdown"
          aria-live="polite"
          className="tabular-nums text-2xl text-ink"
        >
          {formatClock(remaining)}
        </p>
      </div>
      {effectiveStatus === 'done' && <p className="text-ink">That was a minute.</p>}
      <div className="flex gap-2">
        {(effectiveStatus === 'idle' || effectiveStatus === 'done') && (
          <button
            type="button"
            onClick={start}
            className="rounded-pill bg-accent px-4 py-2 text-sm text-bg transition-colors duration-150"
          >
            Start
          </button>
        )}
        {effectiveStatus === 'running' && (
          <>
            <button
              type="button"
              onClick={() => setStatus('paused')}
              className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150"
            >
              Pause
            </button>
            <button
              type="button"
              onClick={stop}
              className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150"
            >
              Stop
            </button>
          </>
        )}
        {status === 'paused' && (
          <>
            <button
              type="button"
              onClick={start}
              className="rounded-pill bg-accent px-4 py-2 text-sm text-bg transition-colors duration-150"
            >
              Resume
            </button>
            <button
              type="button"
              onClick={stop}
              className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150"
            >
              Stop
            </button>
          </>
        )}
      </div>
    </section>
  )
}
