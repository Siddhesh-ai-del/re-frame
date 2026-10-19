import { useMemo, useState } from 'react'
import { submitCheckin, BadRequestError, ApiUnavailableError, NetworkError } from '../../api/client'
import type { components } from '../../api/schema.d'

/**
 * CheckInForm (stage 6d): one radio group per item (fieldset/legend),
 * keyboard-complete selection (Space selects, arrows move within a group),
 * today's date pre-filled and shown as an ISO string, submit gated on a full
 * set of answers, an honest in-flight state, and the chat pattern's honest
 * error states (422/503/network/unknown — never fake success). The submitted
 * responses are ordered by the instrument's item order.
 */

type InstrumentOut = components['schemas']['InstrumentOut']
type CheckInOut = components['schemas']['CheckInOut']

function todayIso(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

export interface CheckInFormProps {
  instrument: InstrumentOut
  onDone: (result: CheckInOut) => void
}

export function CheckInForm({ instrument, onDone }: CheckInFormProps) {
  const date = useMemo(() => todayIso(), [])
  const [picks, setPicks] = useState<Record<number, number>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const answered = instrument.items.filter((item) => picks[item.index] !== undefined).length
  const complete = answered === instrument.items.length

  function pick(index: number, value: number) {
    setPicks((current) => ({ ...current, [index]: value }))
  }

  /**
   * Move the selection within one item's group by OPTION POSITION (answer
   * values are instrument-defined — K-10 is 1-based — so position, not value,
   * is what arrow keys step through).
   */
  function moveWithinGroup(index: number, currentValue: number, delta: number) {
    const options = instrument.answer_options
    const position = Math.max(
      options.findIndex((option) => option.value === currentValue),
      0,
    )
    const next = options[(position + delta + options.length) % options.length]!
    pick(index, next.value)
    document.getElementById(`checkin-item-${index}-opt-${next.value}`)?.focus()
  }

  function onItemKeyDown(event: React.KeyboardEvent<HTMLInputElement>, index: number) {
    if (event.key === 'Enter') {
      // Enter on any focused option submits the finished form (keyboard-only
      // completion — the button is not the only way through).
      event.preventDefault()
      void submitAnswers()
      return
    }
    const value = Number((event.target as HTMLInputElement).value)
    if (event.key === ' ') {
      event.preventDefault()
      pick(index, value)
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      moveWithinGroup(index, value, 1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      moveWithinGroup(index, value, -1)
    }
  }

  async function submitAnswers(): Promise<void> {
    if (!complete || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const responses = instrument.items.map((item) => picks[item.index]!)
      const result = await submitCheckin({
        instrument_id: instrument.id,
        date,
        responses,
      })
      onDone(result)
    } catch (caught) {
      if (caught instanceof BadRequestError) {
        setError(caught.message)
      } else if (caught instanceof ApiUnavailableError) {
        setError(
          "The check-in service isn't responding right now. Please try again in a moment.",
        )
      } else if (caught instanceof NetworkError) {
        setError(
          "You appear to be offline or the service can't be reached. Check your connection and try again.",
        )
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    void submitAnswers()
  }

  return (
    <form
      aria-label={`Check-in form for ${instrument.title}`}
      onSubmit={onSubmit}
      className="flex flex-col gap-4"
    >
      <p className="text-sm text-ink-muted">
        Answers for <span className="tabular-nums">{date}</span> — {instrument.recall_period}.
      </p>

      {instrument.items.map((item) => (
        <fieldset
          key={item.index}
          className="rounded-[var(--radius-card)] border border-border bg-surface p-3"
        >
          <legend className="px-1 text-sm font-medium text-ink">
            {item.prompt}
          </legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {instrument.answer_options.map((option) => (
              <label
                key={option.value}
                className="flex items-center gap-1.5 text-sm text-ink"
              >
                <input
                  id={`checkin-item-${item.index}-opt-${option.value}`}
                  type="radio"
                  name={`item-${item.index}`}
                  value={option.value}
                  aria-label={option.label}
                  checked={picks[item.index] === option.value}
                  onChange={() => pick(item.index, option.value)}
                  onKeyDown={(event) => onItemKeyDown(event, item.index)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
      ))}

      {error !== null && (
        <p role="alert" className="rounded-[var(--radius-card)] bg-warning-soft px-3 py-2 text-sm text-warning">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!complete || submitting}
        className="self-start rounded-[var(--radius-input)] border border-accent bg-accent px-4 py-2 text-sm text-white transition-colors duration-150 hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? 'Sending your check-in…' : 'Save check-in'}
      </button>
    </form>
  )
}
