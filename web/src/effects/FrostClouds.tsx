import { useEffect, useState } from 'react'
import { Clouds } from '../../vendored/canvas-ui/Clouds'
import { useReducedEffects } from './EffectsContext'

/**
 * FrostClouds (stage 6d): the opt-in ambient canvas layer wrapping the
 * vendored Canvas UI clouds component. License provenance is documented in
 * web/vendored/canvas-ui/NOTICE (MIT + Commons Clause v1.0, David Haz) — the
 * vendored source is used inside the RE:FRAME application per the Commons
 * Clause permission, never sold or redistributed as a component library.
 *
 * Gating (the part unit tests can actually exercise — jsdom cannot rasterize
 * a canvas): renders only when the frost preference is ON AND reduced effects
 * are resolved false AND the tab is visible. Same-tab changes sync through
 * the 'reframe:frost-changed' custom event (Settings dispatches it after
 * writing storage). The tab-visibility pause unmounts the canvas entirely so
 * no rAF/WebGL work runs while hidden, and the vendored component tears its
 * own GL resources down on unmount.
 */

export const FROST_STORAGE_KEY = 'reframe:frost-clouds'
export const FROST_CHANGE_EVENT = 'reframe:frost-changed'

function readFrostEnabled(): boolean {
  try {
    return window.localStorage.getItem(FROST_STORAGE_KEY) === 'on'
  } catch {
    // Storage unavailable: frost stays off (opt-in can't be confirmed).
    return false
  }
}

export function FrostClouds() {
  const { reducedEffects } = useReducedEffects()
  const [enabled, setEnabled] = useState(readFrostEnabled)
  const [tabVisible, setTabVisible] = useState(() => !document.hidden)

  useEffect(() => {
    const sync = () => setEnabled(readFrostEnabled())
    window.addEventListener(FROST_CHANGE_EVENT, sync)
    const onVisibility = () => setTabVisible(!document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      window.removeEventListener(FROST_CHANGE_EVENT, sync)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  if (!enabled || reducedEffects || !tabVisible) return null

  return (
    <div
      data-testid="frost-clouds"
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10"
    >
      <Clouds className="h-full w-full" style={{ opacity: 0.5 }}>
        <div />
      </Clouds>
    </div>
  )
}
