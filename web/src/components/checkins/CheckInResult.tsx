import type { components } from '../../api/schema.d'

/**
 * CheckInResult (stage 6d): the honest score screen. The total is the
 * instrument's own score rendered with tabular numerals, the severity label
 * is the instrument's PUBLISHED wording (verbatim, no re-wording), and the
 * citation is shown verbatim. NO risk coloring ever touches the score
 * (docs/webapp-design.md §5.4, NG225 — colors here are ink/accent only); a
 * high or flagged score is never painted red/warning/crisis. A null severity
 * label renders without a fabricated placeholder. "Done" returns to history.
 */

type InstrumentOut = components['schemas']['InstrumentOut']
type CheckInOut = components['schemas']['CheckInOut']

export interface CheckInResultProps {
  result: CheckInOut
  instrument: InstrumentOut
  onDone: () => void
}

export function CheckInResult({ result, instrument, onDone }: CheckInResultProps) {
  return (
    <section
      aria-label="Check-in result"
      className="panel flex flex-col gap-3 rounded-[var(--radius-card)] p-5"
    >
      <h2 className="text-xs font-extrabold uppercase tracking-[0.14em] text-accent-ink">Your check-in</h2>

      <div className="flex items-baseline gap-3">
        <span className="font-display text-3xl font-bold tabular-nums text-ink md:text-[44px]">{result.total}</span>
        <span className="text-sm text-ink-muted">
          out of {instrument.total_max}
        </span>
      </div>

      {result.severity_label !== null && (
        <p className="text-sm text-ink">{result.severity_label}</p>
      )}

      <p className="text-xs text-ink-muted">{instrument.citation}</p>

      <button
        type="button"
        onClick={onDone}
        className="mt-2 self-start rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150 hover:bg-white/70"
      >
        Done
      </button>
    </section>
  )
}
