/**
 * GlassOrb (stage 6c): the ONE signature liquid-glass usage site
 * (design §3 row 7 — "ONE usage, not scattered").
 *
 * With motion allowed it mounts `@samasante/liquid-glass`'s <Glass> lens as a
 * soft frosted orb; under reduced effects it renders a plain frosted-circle
 * div — the static equivalent, with NO lib mount (the lens is pure motion
 * affordance). Low-power-device heuristics (hardwareConcurrency guessing)
 * are deliberately deferred — the reduced-effects signal is the single
 * source of truth for the static decision.
 */
import { Glass } from '@samasante/liquid-glass'
import { useReducedEffects } from '../../effects/EffectsContext'

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
        className="rounded-full border border-border bg-accent-soft"
      />
    )
  }

  return (
    <div data-testid="glass-orb" aria-hidden="true" style={{ width: size, height: size }}>
      <Glass
        size={size}
        radius={size / 2}
        className="h-full w-full rounded-full bg-surface"
        optics={{ frost: 6, brightness: 0.08, specular: 0.4, saturate: 0.9 }}
      />
    </div>
  )
}
