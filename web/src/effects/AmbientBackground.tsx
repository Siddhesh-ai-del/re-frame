import { useOptionalReducedEffects } from './EffectsContext'

/**
 * AmbientBackground (stage 6f — Golden Glass): the static layered landscape
 * behind all content — sky gradient is on <body>, and this fixed layer adds
 * sun, two blurred haze blobs, the two topographic contour sets (the crisp
 * vectors the liquid-glass lenses visibly bend), and three hills
 * (spec §3; generators copied from the approved mockup chrome).
 *
 * Contract (unchanged from stage 6d): aria-hidden, pointer-events-none,
 * painted BELOW content (fixed, non-positive z-index), testid unchanged.
 * The drift animation lives ONLY on the haze wrapper, which is removed from
 * the DOM under reduced effects — CSS cannot animate what isn't declared, so
 * the landscape renders completely static (spec §0.3).
 *
 * Uses the optional context hook so a decorative layer that mounts outside
 * the provider still renders (it resolves the OS signal itself).
 */

/** Sparse contour set — 10 lines (mockup `Contours`). */
function Contours() {
  const lines = []
  for (let i = 0; i < 10; i++) {
    const y = 90 + i * 170
    const a = 40 + (i % 4) * 22
    lines.push(
      <path
        key={i}
        d={`M -40 ${y} C 260 ${y - a}, 540 ${y + a}, 840 ${y - a * 0.6} S 1420 ${y + a * 0.7}, 1680 ${y - a * 0.3}`}
      />,
    )
  }
  return (
    <svg
      className="contours"
      viewBox="0 0 1600 1800"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {lines}
    </svg>
  )
}

/** Tighter terracotta set — 22 lines crossing nav + composer bands. */
function Contours2() {
  const lines = []
  for (let i = 0; i < 22; i++) {
    const y = 30 + i * 82
    const a = 26 + (i % 3) * 18
    lines.push(
      <path
        key={i}
        d={`M -40 ${y} C 320 ${y + a}, 620 ${y - a}, 900 ${y + a * 0.55} S 1380 ${y - a * 0.65}, 1680 ${y + a * 0.3}`}
      />,
    )
  }
  return (
    <svg
      className="contours2"
      viewBox="0 0 1600 1800"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {lines}
    </svg>
  )
}

export function AmbientBackground() {
  const effects = useOptionalReducedEffects()
  const reducedEffects = effects?.reducedEffects ?? false

  return (
    <div
      data-testid="ambient-background"
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div
        className={[
          'haze-layer',
          reducedEffects ? '' : 'animate-haze',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <i className="haze-a" />
        <i className="haze-b" />
      </div>
      <div className="ambient-sun" />
      <Contours />
      <Contours2 />
      <div className="hills">
        <div className="ambient-hill hill-1" />
        <div className="ambient-hill hill-2" />
        <div className="ambient-hill hill-3" />
      </div>
    </div>
  )
}
