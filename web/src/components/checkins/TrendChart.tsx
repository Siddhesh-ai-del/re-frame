import { useState } from 'react'
import type { components } from '../../api/schema.d'

/**
 * TrendChart (stage 6d): a hand-rolled SVG polyline of `total` over `date`
 * for the selected instrument (no chart library — design decision D7). The
 * entries are rendered in the order the service returns them (oldest to
 * newest — verified against the SQLite store's ordering). Accessibility
 * contract: an aria-label on the SVG plus a visually-hidden equivalent list
 * of "date: total (label)" entries; every point focusable via a focusable
 * role="button" with its value announced. Tone contract: ink / ink-muted /
 * accent only — worsening must NEVER turn red (docs/webapp-design.md §3
 * row 4). Honest loading/failure/empty states, no fake data.
 */

type CheckInOut = components['schemas']['CheckInOut']

const WIDTH = 640
const HEIGHT = 200
const PAD = { top: 16, right: 16, bottom: 28, left: 36 }

export interface TrendChartProps {
  entries: CheckInOut[]
  totalMin: number
  totalMax: number
  loading: boolean
  failed: boolean
  onRetry: () => void
}

export function TrendChart({
  entries,
  totalMin,
  totalMax,
  loading,
  failed,
  onRetry,
}: TrendChartProps) {
  const [focusedPoint, setFocusedPoint] = useState<number | null>(null)

  if (loading) {
    return <p className="text-sm text-ink-muted">Loading your history…</p>
  }
  if (failed) {
    return (
      <div className="flex flex-col items-start gap-2">
        <p className="text-sm text-ink-muted">
          Your history couldn&apos;t be loaded right now.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-[var(--radius-input)] border border-border bg-surface px-3 py-1.5 text-sm text-ink transition-colors duration-150 hover:bg-surface-sunk"
        >
          Try again
        </button>
      </div>
    )
  }
  if (entries.length === 0) {
    return (
      <p className="text-sm text-ink-muted">
        Your first check-in will start your history here.
      </p>
    )
  }

  const span = totalMax - totalMin || 1
  const plotWidth = WIDTH - PAD.left - PAD.right
  const plotHeight = HEIGHT - PAD.top - PAD.bottom

  const points = entries.map((entry, index) => {
    const x =
      entries.length === 1
        ? PAD.left + plotWidth / 2
        : PAD.left + (index / (entries.length - 1)) * plotWidth
    const ratio = Math.min(Math.max((entry.total - totalMin) / span, 0), 1)
    const y = PAD.top + plotHeight - ratio * plotHeight
    return { x, y, entry }
  })

  const polyline = points.map((point) => `${point.x},${point.y}`).join(' ')

  return (
    <div className="flex flex-col gap-2">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Check-in totals over time, from ${entries[0]!.date} to ${entries[entries.length - 1]!.date}`}
        className="w-full"
      >
        <polyline
          points={polyline}
          fill="none"
          className="stroke-accent"
          strokeWidth={2}
        />
        {points.map((point, index) => (
          // Index-based key: two check-ins can share one date (a person may
          // record more than one in a day), and date alone would collide.
          <circle
            key={`${point.entry.date}-${index}`}
            cx={point.x}
            cy={point.y}
            r={focusedPoint === index ? 6 : 4}
            tabIndex={0}
            role="button"
            aria-label={`${point.entry.date}: ${point.entry.total}${point.entry.severity_label !== null ? ` (${point.entry.severity_label})` : ''}`}
            onFocus={() => setFocusedPoint(index)}
            onBlur={() => setFocusedPoint(null)}
            className="fill-accent"
          />
        ))}
      </svg>
      <ul className="sr-only">
        {entries.map((entry, index) => (
          // Index-based key for the same-date reason as the chart points.
          <li key={`${entry.date}-${index}`}>
            {entry.date}: {entry.total}
            {entry.severity_label !== null ? ` (${entry.severity_label})` : ''}
          </li>
        ))}
      </ul>
    </div>
  )
}
