import { useOptionalReducedEffects } from './EffectsContext'

/**
 * AmbientBackground (stage 6d): the CSS-only aurora/linen layer, mounted once
 * behind all content. adapted from opensourceui (MIT) ambient-gradient
 * techniques — reshaped to RE:FRAME tokens. Contract: aria-hidden,
 * pointer-events-none, painted BELOW content (DOM order before the shell +
 * non-positive z-index), and completely static when reduced effects are
 * resolved (no animation classes in the DOM at all — CSS cannot animate what
 * isn't declared).
 *
 * Uses the optional context hook so a decorative layer that mounts outside
 * the provider still renders (it just assumes effects are allowed).
 */

export function AmbientBackground() {
  const effects = useOptionalReducedEffects()
  const reducedEffects = effects?.reducedEffects ?? false

  return (
    <div
      data-testid="ambient-background"
      aria-hidden="true"
      className={[
        'pointer-events-none fixed inset-0 -z-10 overflow-hidden',
        reducedEffects ? '' : 'animate-aurora',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="absolute inset-0 bg-[radial-gradient(60%_50%_at_20%_20%,var(--accent-soft)_0%,transparent_60%)] opacity-60" />
      <div className="absolute inset-0 bg-[radial-gradient(50%_40%_at_80%_30%,var(--surface-sunk)_0%,transparent_55%)] opacity-50" />
      <div className="absolute inset-0 bg-[linear-gradient(160deg,transparent_0%,var(--accent-soft)_100%)] opacity-30" />
    </div>
  )
}
