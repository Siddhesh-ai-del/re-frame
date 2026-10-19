/**
 * GlassOrb (stage 6c/6f): signature liquid-glass usage site 2 of 3
 * (spec §4) — now a thin wrapper over the shared GlassSurface primitive in
 * its `orb` variant (full liquid-lens optics from the approved mockups).
 *
 * With motion allowed it mounts `@samasante/liquid-glass`'s <Glass> lens as a
 * soft frosted orb; under reduced effects it renders a plain frosted-circle
 * div — the static equivalent, with NO lib mount (the lens is pure motion
 * affordance). Low-power-device heuristics (hardwareConcurrency guessing)
 * are deliberately deferred — the reduced-effects signal is the single
 * source of truth for the static decision.
 *
 * Testid contract: `glass-orb` in BOTH branches; the static branch keeps
 * `data-fallback="frosted"` (asserted by onboarding E2E).
 */
import { useReducedEffects } from '../../effects/EffectsContext'
import { GlassSurface } from '../glass/GlassSurface'

export interface GlassOrbProps {
  /** Orb diameter in CSS pixels. */
  size?: number
}

export function GlassOrb({ size = 160 }: GlassOrbProps) {
  const { reducedEffects } = useReducedEffects()

  if (reducedEffects) {
    // Static equivalent: a calm frosted circle. No lens, no animation.
    return (
      <div
        data-testid="glass-orb"
        data-fallback="frosted"
        aria-hidden="true"
        style={{ width: size, height: size }}
        className="rounded-full border border-border bg-accent-soft shadow-[var(--shadow-soft)]"
      />
    )
  }

  return (
    <div
      data-testid="glass-orb"
      aria-hidden="true"
      style={{ width: size, height: size }}
    >
      <GlassSurface variant="orb" size={size} className="h-full w-full" />
    </div>
  )
}
