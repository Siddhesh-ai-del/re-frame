import { useCallback, useEffect, useMemo, useState } from 'react'
import { useToast } from '../components/toast/ToastProvider'
import {
  fetchCheckinHistory,
  fetchInstruments,
  type CheckInOut,
  type InstrumentOut,
} from '../api/client'
import { DashboardStatusBar } from '../components/checkins/DashboardStatusBar'
import { InstrumentPicker } from '../components/checkins/InstrumentPicker'
import { CheckInForm } from '../components/checkins/CheckInForm'
import { CheckInResult } from '../components/checkins/CheckInResult'
import { FlagNotice } from '../components/checkins/FlagNotice'
import { TrendChart } from '../components/checkins/TrendChart'
import { ProgressRing } from '../components/checkins/ProgressRing'

/**
 * CheckInsPage (stage 6d): the measurement dashboard.
 *
 * Layout (design §3 rows 4–6): the honest DashboardStatusBar across ALL
 * instruments on top, the instrument picker, then the active instrument's
 * area — the form when no result is showing, the result + verbatim flag
 * notice after a submit — and below it the selected instrument's history as
 * a trend chart + progress ring.
 *
 * Honest state machine: instruments and history load independently with
 * their own loading/failure/retry (a failure never fakes an empty state).
 * The status bar's "latest check-in" is a client-side aggregate over every
 * instrument's history (there is no cross-instrument endpoint). A successful
 * submit appends to that aggregate locally so the dashboard reflects the new
 * check-in without a round-trip; "Done" returns to the form. The success
 * toast fires for EVERY saved check-in — escalation adds the persistent
 * verbatim notice, it never replaces it (D9: never toast-only).
 */

interface HistoryState {
  readonly entries: CheckInOut[]
  readonly failed: boolean
}

function byDateOldestFirst(entries: CheckInOut[]): CheckInOut[] {
  return [...entries].sort((a, b) => a.date.localeCompare(b.date))
}

export function CheckInsPage() {
  const showToast = useToast()

  const [instruments, setInstruments] = useState<InstrumentOut[] | null>(null)
  const [instrumentsFailed, setInstrumentsFailed] = useState(false)
  const [instrumentAttempt, setInstrumentAttempt] = useState(0)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const [history, setHistory] = useState<Record<string, HistoryState>>({})
  const [historyAttempt, setHistoryAttempt] = useState(0)

  const [result, setResult] = useState<CheckInOut | null>(null)

  // Instrument catalog: honest load / failure / retry (pattern: ExercisesPage).
  useEffect(() => {
    let cancelled = false
    fetchInstruments()
      .then((list) => {
        if (cancelled) return
        setInstruments(list)
        setInstrumentsFailed(false)
        setSelectedId((previous) => previous ?? list[0]?.id ?? null)
      })
      .catch(() => {
        if (!cancelled) setInstrumentsFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [instrumentAttempt])

  // One history fetch per instrument (feeds both the status aggregate and
  // the selected instrument's chart). Retried as a unit via historyAttempt.
  useEffect(() => {
    if (instruments === null) return
    let cancelled = false
    for (const instrument of instruments) {
      fetchCheckinHistory(instrument.id)
        .then((entries) => {
          if (cancelled) return
          setHistory((previous) => ({
            ...previous,
            [instrument.id]: { entries: byDateOldestFirst(entries), failed: false },
          }))
        })
        .catch(() => {
          if (cancelled) return
          setHistory((previous) => ({
            ...previous,
            [instrument.id]: {
              entries: previous[instrument.id]?.entries ?? [],
              failed: true,
            },
          }))
        })
    }
    return () => {
      cancelled = true
    }
  }, [instruments, historyAttempt])

  const retryInstruments = useCallback(() => {
    setInstruments(null)
    setInstrumentsFailed(false)
    setInstrumentAttempt((previous) => previous + 1)
  }, [])

  const retryHistory = useCallback(() => {
    setHistory({})
    setHistoryAttempt((previous) => previous + 1)
  }, [])

  /** Client-side aggregate: the most recent entry across every instrument. */
  const latest = useMemo(() => {
    let newest: { date: string; title: string } | null = null
    for (const instrument of instruments ?? []) {
      const entries = history[instrument.id]?.entries ?? []
      const last = entries[entries.length - 1]
      if (last !== undefined && (newest === null || last.date.localeCompare(newest.date) > 0)) {
        newest = { date: last.date, title: instrument.title }
      }
    }
    return newest
  }, [instruments, history])

  const historyLoading =
    !instrumentsFailed &&
    (instruments === null ||
      instruments.some((instrument) => history[instrument.id] === undefined))
  const historyFailed =
    instrumentsFailed || Object.values(history).some((state) => state.failed)

  const selected = useMemo(
    () => instruments?.find((instrument) => instrument.id === selectedId) ?? null,
    [instruments, selectedId],
  )
  const selectedHistory = selectedId !== null ? history[selectedId] : undefined
  const entries = selectedHistory?.entries ?? []

  const onSubmitted = useCallback(
    (recorded: CheckInOut) => {
      setResult(recorded)
      showToast('Check-in saved.')
      // Fold the new check-in into the local aggregate so the status bar and
      // the chart show it immediately (the service's own store persists it).
      setHistory((previous) => {
        const existing = previous[recorded.instrument_id]?.entries ?? []
        const failed = previous[recorded.instrument_id]?.failed ?? false
        return {
          ...previous,
          [recorded.instrument_id]: {
            entries: byDateOldestFirst([...existing, recorded]),
            failed,
          },
        }
      })
    },
    [showToast],
  )

  return (
    <section
      aria-label="Check-ins"
      className="mx-auto flex w-full max-w-page flex-col gap-6 px-6 py-8"
    >
      <h1 className="text-3xl font-medium text-ink">Check-ins</h1>

      <DashboardStatusBar latest={latest} loading={historyLoading} failed={historyFailed} />

      <InstrumentPicker
        instruments={instruments}
        loading={!instrumentsFailed && instruments === null}
        failed={instrumentsFailed}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onRetry={retryInstruments}
      />

      {selected !== null && result !== null && (
        <div className="flex flex-col gap-4">
          <FlagNotice result={result} />
          <CheckInResult
            result={result}
            instrument={selected}
            onDone={() => setResult(null)}
          />
        </div>
      )}

      {selected !== null && result === null && (
        <CheckInForm key={selected.id} instrument={selected} onDone={onSubmitted} />
      )}

      {selected !== null && (
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <div className="min-w-0 flex-1">
            <h2 className="mb-2 text-xl font-medium text-ink">History</h2>
            <TrendChart
              entries={entries}
              totalMin={selected.total_min}
              totalMax={selected.total_max}
              loading={selectedHistory === undefined && !historyFailed}
              failed={selectedHistory?.failed ?? false}
              onRetry={retryHistory}
            />
          </div>
          {entries.length > 0 && (() => {
            const newest = entries[entries.length - 1]!
            return (
              <ProgressRing
                value={newest.total}
                totalMin={selected.total_min}
                totalMax={selected.total_max}
                severityLabel={newest.severity_label}
                citation={selected.citation}
              />
            )
          })()}
        </div>
      )}
    </section>
  )
}
