import type { components } from '../../api/schema.d'

/**
 * InstrumentPicker (stage 6d): choose which instrument to fill in, from
 * GET /instruments. Radio-style toggle buttons showing title + recall period,
 * with honest loading and failure states (a retry that actually refetches).
 * Failure always wins over loading — never a fake list, never both.
 */

type InstrumentOut = components['schemas']['InstrumentOut']

export interface InstrumentPickerProps {
  /** The loaded instruments, or null while loading / after a failure. */
  instruments: InstrumentOut[] | null
  loading: boolean
  failed: boolean
  selectedId: string | null
  onSelect: (instrumentId: string) => void
  onRetry: () => void
}

export function InstrumentPicker({
  instruments,
  loading,
  failed,
  selectedId,
  onSelect,
  onRetry,
}: InstrumentPickerProps) {
  if (failed) {
    return (
      <div role="status" className="flex flex-col items-start gap-2">
        <p className="text-sm text-ink-muted">
          The instrument list couldn&apos;t be loaded right now.
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

  if (loading || instruments === null) {
    return (
      <p role="status" className="text-sm text-ink-muted">
        Loading instruments…
      </p>
    )
  }

  return (
    <div
      role="group"
      aria-label="Choose an instrument"
      className="flex flex-wrap gap-2"
    >
      {instruments.map((instrument) => {
        const selected = instrument.id === selectedId
        return (
          <button
            key={instrument.id}
            type="button"
            aria-pressed={selected}
            onClick={() => onSelect(instrument.id)}
            className={[
              'flex flex-col items-start gap-0.5 rounded-[var(--radius-card)] border px-3 py-2 text-left transition-colors duration-150',
              selected
                ? 'border-accent bg-accent-soft text-accent-ink'
                : 'border-border bg-surface text-ink hover:bg-surface-sunk',
            ].join(' ')}
          >
            <span className="text-sm font-medium">{instrument.title}</span>
            <span className="text-xs text-ink-muted">{instrument.recall_period}</span>
          </button>
        )
      })}
    </div>
  )
}
