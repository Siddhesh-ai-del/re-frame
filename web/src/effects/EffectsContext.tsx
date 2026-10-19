import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from 'react'

/**
 * Reduced-effects engine.
 *
 * Resolves the app-wide "reduce motion and effects" decision from two inputs:
 * the user's explicit preference (`system` / `on` / `off`, persisted to
 * localStorage) and the OS `prefers-reduced-motion` signal. While following
 * the system, the media query's 'change' events are observed; an explicit
 * `on`/`off` preference overrides the OS signal entirely (and detaches the
 * listener — no leaks, no wasted work).
 *
 * The resolved boolean is mirrored onto `<html data-reduced-effects>` so CSS
 * can gate animations statically (and components can read it without React).
 */

export type EffectsPreference = 'system' | 'on' | 'off'

export interface ReducedEffectsValue {
  readonly reducedEffects: boolean
  readonly preference: EffectsPreference
  setPreference: (preference: EffectsPreference) => void
}

const STORAGE_KEY = 'reframe:effects'
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'

const EffectsContext = createContext<ReducedEffectsValue | null>(null)

function isPreference(value: unknown): value is EffectsPreference {
  return value === 'system' || value === 'on' || value === 'off'
}

function readStoredPreference(): EffectsPreference {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return isPreference(stored) ? stored : 'system'
  } catch {
    // Storage unavailable (privacy mode, blocked cookies): fall back to system.
    return 'system'
  }
}

function resolveReduced(
  preference: EffectsPreference,
  systemReduced: boolean,
): boolean {
  if (preference === 'off') return true
  if (preference === 'on') return false
  return systemReduced
}

export function EffectsProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] =
    useState<EffectsPreference>(readStoredPreference)

  // Subscribe to the OS signal only while following the system. React
  // re-runs subscribe (and re-reads the snapshot) when preference changes,
  // so returning to 'system' picks up any signal change that happened while
  // detached — no setState-in-effect needed.
  const subscribe = useCallback(
    (onStoreChange: () => void): (() => void) => {
      if (preference !== 'system') return () => {}
      const query = window.matchMedia(REDUCED_MOTION_QUERY)
      query.addEventListener('change', onStoreChange)
      return () => query.removeEventListener('change', onStoreChange)
    },
    [preference],
  )
  const systemReduced = useSyncExternalStore(
    subscribe,
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches,
    () => false,
  )

  const reducedEffects = resolveReduced(preference, systemReduced)

  useEffect(() => {
    document.documentElement.dataset.reducedEffects = String(reducedEffects)
  }, [reducedEffects])

  const setPreference = useCallback((next: EffectsPreference) => {
    setPreferenceState(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Storage unavailable: the preference still applies for this session.
    }
  }, [])

  const value = useMemo<ReducedEffectsValue>(
    () => ({ reducedEffects, preference, setPreference }),
    [reducedEffects, preference, setPreference],
  )

  return (
    <EffectsContext.Provider value={value}>{children}</EffectsContext.Provider>
  )
}

export function useReducedEffects(): ReducedEffectsValue {
  const context = useContext(EffectsContext)
  if (context === null) {
    throw new Error('useReducedEffects must be used within an EffectsProvider')
  }
  return context
}

/**
 * Non-throwing variant for purely decorative layers (stage 6d). A background
 * effect that mounts outside the provider must still render — it just falls
 * back to "effects allowed" rather than crashing the tree.
 */
export function useOptionalReducedEffects(): ReducedEffectsValue | null {
  return useContext(EffectsContext)
}
