/**
 * ProgressRing (stage 6d): a hand-rolled SVG circle arc for the MOST RECENT
 * total within [total_min, total_max], with the published severity label and
 * the instrument citation as text, in neutral (ink/accent) colors only —
 * never crisis/warning colors (design §5.4, NG225).
 *
 * Animation decision (spec §C): the ring NEVER animates its value — no
 * draw-in, no transition — so there is no reduced-motion divergence to
 * police. `reducedMotion` is accepted for API symmetry with the rest of the
 * effects-aware surface but intentionally unused by the drawing itself.
 */

export interface ProgressRingProps {
  value: number
  totalMin: number
  totalMax: number
  severityLabel: string | null
  citation: string
  reducedMotion?: boolean
}

const SIZE = 96
const STROKE = 8
const RADIUS = (SIZE - STROKE) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function ProgressRing({
  value,
  totalMin,
  totalMax,
  severityLabel,
  citation,
}: ProgressRingProps) {
  const span = totalMax - totalMin || 1
  const ratio = Math.min(Math.max((value - totalMin) / span, 0), 1)
  const dash = ratio * CIRCUMFERENCE

  return (
    <div className="flex flex-col items-center gap-2">
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={totalMin}
        aria-valuemax={totalMax}
        aria-label="Most recent check-in total"
        className="relative inline-flex items-center justify-center"
      >
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} aria-hidden="true">
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            className="stroke-border"
            strokeWidth={STROKE}
          />
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            className="stroke-accent"
            strokeWidth={STROKE}
            strokeDasharray={`${dash} ${CIRCUMFERENCE - dash}`}
            strokeLinecap="round"
            transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
          />
        </svg>
        <span className="absolute text-lg tabular-nums text-ink">{value}</span>
      </div>
      {severityLabel !== null && (
        <p className="text-sm text-ink">{severityLabel}</p>
      )}
      <p className="text-xs text-ink-muted">{citation}</p>
    </div>
  )
}
