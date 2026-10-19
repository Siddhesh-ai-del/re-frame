/**
 * SettingsPage (stage 6d): preferences, local data, and About.
 *
 * Four honest surfaces:
 *
 * - Reduce effects: the three-way preference radio bound to the existing
 *   engine (localStorage + <html data-reduced-effects> flip in both
 *   directions, OS signal honored while set to system).
 * - Ambient frost/clouds: opt-in, default OFF, disabled + explained when
 *   motion effects are off ("frost/clouds needs motion effects on"), and
 *   FORCED off (storage + UI) whenever reduced effects resolve true — the
 *   toggle can never leave the ambience running against a reduced-motion
 *   decision. Same-tab changes announce via the 'reframe:frost-changed'
 *   custom event so FrostClouds re-gates without a reload.
 * - Local data: journal export/clear (device-local, reusing lib/journal —
 *   the SAME helpers JournalCard uses) and check-in export/purge. Both
 *   destructive actions are confirm-guarded inline (never toast-only) and
 *   every outcome — cleared, "N check-ins deleted.", or an honest failure —
 *   is rendered in place. The check-in export aggregates
 *   GET /checkins/{id} for every instrument id from GET /instruments into
 *   a local JSON Blob: the person's own data, no server round-trip beyond
 *   the history reads.
 * - About: the service version from GET /health with an honest fallback
 *   when the local service is unreachable, plus the standing line.
 */
import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'
import {
  fetchCheckinHistory,
  fetchHealth,
  fetchInstruments,
  purgeCheckins,
} from '../api/client'
import {
  clearEntries,
  exportJournal,
  loadEntries,
  type JournalEntry,
} from '../lib/journal'
import { useReducedEffects } from '../effects/EffectsContext'
import {
  FROST_CHANGE_EVENT,
  FROST_STORAGE_KEY,
} from '../effects/FrostClouds'

const FROST_EXPLANATION = 'frost/clouds needs motion effects on'
const HONESTY_LINE = 'RE:FRAME is wellness support, not medical care.'

const EFFECT_OPTIONS: ReadonlyArray<{
  value: 'system' | 'on' | 'off'
  label: string
}> = [
  { value: 'system', label: 'Follow my system setting' },
  { value: 'off', label: 'On — reduce motion and effects' },
  { value: 'on', label: 'Off — use full effects' },
]

function readFrostEnabled(): boolean {
  try {
    return window.localStorage.getItem(FROST_STORAGE_KEY) === 'on'
  } catch {
    // Storage unavailable: frost stays off (opt-in can't be confirmed).
    return false
  }
}

/** Persist the frost opt-in and announce it (same-tab FrostClouds sync). */
function writeFrost(enabled: boolean): void {
  try {
    window.localStorage.setItem(FROST_STORAGE_KEY, enabled ? 'on' : 'off')
  } catch {
    // Storage unavailable: the in-session toggle still applies.
  }
  window.dispatchEvent(new Event(FROST_CHANGE_EVENT))
}

/** Subscribe to same-tab frost changes (the write above dispatches them). */
function subscribeFrost(onStoreChange: () => void): () => void {
  window.addEventListener(FROST_CHANGE_EVENT, onStoreChange)
  return () => window.removeEventListener(FROST_CHANGE_EVENT, onStoreChange)
}

/** Download data as a local Blob file — no network involvement. */
function downloadBlob(contents: string, filename: string, type: string): void {
  const blob = new Blob([contents], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

const SECTION_CLASS =
  'panel flex flex-col gap-3 rounded-[var(--radius-card)] p-5'

export function SettingsPage() {
  const { preference, reducedEffects, setPreference } = useReducedEffects()

  // Frost is a pure projection of the external opt-in store (localStorage +
  // the 'reframe:frost-changed' event) — no local shadow state to drift.
  const frostOn = useSyncExternalStore(
    subscribeFrost,
    readFrostEnabled,
    () => false,
  )
  const [entries, setEntries] = useState<JournalEntry[]>(() =>
    loadEntries(window.localStorage),
  )
  const [confirmingJournalDelete, setConfirmingJournalDelete] = useState(false)
  const [journalCleared, setJournalCleared] = useState(false)
  const [confirmingPurge, setConfirmingPurge] = useState(false)
  const [purgeMessage, setPurgeMessage] = useState<string | null>(null)
  const [purgeFailed, setPurgeFailed] = useState(false)
  const [exportFailed, setExportFailed] = useState(false)
  const [version, setVersion] = useState<string | null>(null)
  const [healthFailed, setHealthFailed] = useState(false)

  // Frost can never stay on against a reduced-effects decision: whenever
  // reduced effects resolve true (explicit preference OR OS signal), the
  // opt-in is forced OFF in the external store. This effect updates the
  // external system only; the change flows back through the subscription
  // above (storage read + same-tab event), so there is no setState here.
  useEffect(() => {
    if (reducedEffects && readFrostEnabled()) {
      writeFrost(false)
    }
  }, [reducedEffects])

  useEffect(() => {
    let cancelled = false
    fetchHealth()
      .then((health) => {
        if (!cancelled) setVersion(health.version)
      })
      .catch(() => {
        // Honest fallback: never invent a version number.
        if (!cancelled) setHealthFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const toggleFrost = useCallback((checked: boolean) => {
    // Writing the store dispatches the change event, which re-renders this
    // page AND re-gates FrostClouds — one source of truth, no local mirror.
    writeFrost(checked)
  }, [])

  const deleteAllJournal = useCallback(() => {
    clearEntries(window.localStorage)
    setEntries([])
    setConfirmingJournalDelete(false)
    setJournalCleared(true)
  }, [])

  const exportCheckins = useCallback(async () => {
    setExportFailed(false)
    try {
      const instruments = await fetchInstruments()
      const histories = await Promise.all(
        instruments.map((instrument) => fetchCheckinHistory(instrument.id)),
      )
      downloadBlob(
        JSON.stringify(histories.flat(), null, 2),
        'reframe-check-ins.json',
        'application/json',
      )
    } catch {
      setExportFailed(true)
    }
  }, [])

  const deleteAllCheckins = useCallback(async () => {
    setConfirmingPurge(false)
    setPurgeMessage(null)
    setPurgeFailed(false)
    try {
      const deleted = await purgeCheckins()
      setPurgeMessage(`${deleted} check-ins deleted.`)
    } catch {
      // Honest failure — never claim a purge that didn't happen.
      setPurgeFailed(true)
    }
  }, [])

  return (
    <section
      aria-label="Settings"
      className="mx-auto flex w-full max-w-page flex-col gap-8 px-6 py-8"
    >
      <h1 className="font-display text-3xl font-bold tracking-[-0.01em] text-ink">
        Settings
      </h1>

      <fieldset className={SECTION_CLASS}>
        <legend className="px-1 font-display text-xl font-bold text-ink">
          Reduce effects
        </legend>
        {/* Segmented pill track: the REAL radios stay in the DOM (keyboard +
            Playwright) — only the paint changes (spec §5). */}
        <div className="flex flex-wrap gap-1 self-start rounded-pill border border-border bg-white/60 p-1">
          {EFFECT_OPTIONS.map((option) => (
            <label
              key={option.value}
              className="flex cursor-pointer items-center gap-2 rounded-pill px-3 py-1.5 text-sm text-ink transition-colors duration-150 has-[:checked]:bg-ink has-[:checked]:font-semibold has-[:checked]:text-ink-on"
            >
              <input
                type="radio"
                name="reduce-effects"
                value={option.value}
                checked={preference === option.value}
                onChange={() => setPreference(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>

      <section aria-label="Ambient frost/clouds" className={SECTION_CLASS}>
        <h2 className="font-display text-xl font-bold tracking-[-0.01em] text-ink">Ambient frost/clouds</h2>
        <label className="flex items-center gap-2 text-ink">
          <input
            type="checkbox"
            checked={frostOn}
            disabled={reducedEffects}
            onChange={(event) => toggleFrost(event.target.checked)}
          />
          Show frost/clouds ambience
        </label>
        {reducedEffects && (
          <p className="text-sm text-ink-muted">{FROST_EXPLANATION}</p>
        )}
      </section>

      <section aria-label="Journal" className={SECTION_CLASS}>
        <h2 className="font-display text-xl font-bold tracking-[-0.01em] text-ink">Journal</h2>
        <p className="text-sm text-ink-muted">
          Your journal is stored only on this device. Nothing is sent anywhere.
        </p>
        <ul className="flex flex-col gap-2">
          {entries.map((entry) => (
            <li key={entry.id} className="text-ink">
              {entry.text}
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => exportJournal(entries)}
            className="btn-cta rounded-pill px-4 py-2 text-sm font-semibold transition-colors duration-150"
          >
            Export journal
          </button>
          {confirmingJournalDelete ? (
            <>
              <span className="text-ink">Delete all entries?</span>
              <button
                type="button"
                onClick={() => setConfirmingJournalDelete(false)}
                className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={deleteAllJournal}
                className="rounded-pill bg-crisis px-4 py-2 text-sm text-bg transition-colors duration-150"
              >
                Delete
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => {
                setJournalCleared(false)
                setConfirmingJournalDelete(true)
              }}
              className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150"
            >
              Delete all entries
            </button>
          )}
        </div>
        {journalCleared && (
          <p role="status" className="text-ink">
            Journal cleared on this device.
          </p>
        )}
      </section>

      <section aria-label="Check-in data" className={SECTION_CLASS}>
        <h2 className="font-display text-xl font-bold tracking-[-0.01em] text-ink">Check-in data</h2>
        <p className="text-sm text-ink-muted">
          Exports build a file on this device from your own check-in history.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void exportCheckins()}
            className="btn-cta rounded-pill px-4 py-2 text-sm font-semibold transition-colors duration-150"
          >
            Export my check-ins
          </button>
          {confirmingPurge ? (
            <>
              <span className="text-ink">Delete all check-ins?</span>
              <button
                type="button"
                onClick={() => setConfirmingPurge(false)}
                className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void deleteAllCheckins()}
                className="rounded-pill bg-crisis px-4 py-2 text-sm text-bg transition-colors duration-150"
              >
                Delete
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => {
                setPurgeMessage(null)
                setPurgeFailed(false)
                setConfirmingPurge(true)
              }}
              className="rounded-pill border border-border bg-surface px-4 py-2 text-sm text-ink transition-colors duration-150"
            >
              Delete all check-ins
            </button>
          )}
        </div>
        {exportFailed && (
          <p role="alert" className="text-ink">
            Your check-ins couldn't be exported right now. Try again.
          </p>
        )}
        {purgeMessage !== null && (
          <p role="status" className="text-ink">
            {purgeMessage}
          </p>
        )}
        {purgeFailed && (
          <p role="alert" className="text-ink">
            Your check-ins couldn't be deleted right now. Try again.
          </p>
        )}
      </section>

      <section aria-label="About" className={SECTION_CLASS}>
        <h2 className="font-display text-xl font-bold tracking-[-0.01em] text-ink">About</h2>
        {version !== null ? (
          <p className="text-ink">Version {version} — from the local service</p>
        ) : healthFailed ? (
          <p className="text-ink">
            Version unavailable — the local service isn't responding.
          </p>
        ) : (
          <p className="text-ink-muted">Checking the local service…</p>
        )}
        <p className="text-ink-muted">{HONESTY_LINE}</p>
      </section>
    </section>
  )
}
