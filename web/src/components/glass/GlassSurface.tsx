/**
 * GlassSurface (stage 6f): the ONE shared liquid-glass primitive — the app's
 * exactly-3 lens budget (nav pill, hero orb, chat composer) routes through
 * this component (spec §4). Content cards elsewhere are plain warm panels:
 * scattering lenses across every card is what caused the hardware load.
 *
 * Material mode gotcha (debugged in the mockups): `filterResolution` must
 * NEVER be passed — that prop disqualifies material mode, which switches the
 * lib to refracting the CHILDREN instead of the live page (warped, unreadable
 * text). Material mode = backdrop-filter displacement over the page with the
 * children rendered crisp on top.
 *
 * Layout gotcha: the lib forces `display: inline-block` on its root, so
 * centering/sizing of the OUTER wrapper lives on our own div, the lens width
 * and padding on the Glass className, and flex layout on the inner row
 * (mockup `.nav-row` / `.composer-row` pattern).
 *
 * Reduced effects (spec §0.3): the lens NEVER mounts — a plain static div
 * with an opaque warm surface renders instead (`data-fallback="static"`).
 */
import { Glass, type GlassOptics } from '@samasante/liquid-glass'
import type { CSSProperties, ReactNode } from 'react'
import { useOptionalReducedEffects } from '../../effects/EffectsContext'

export type GlassVariant = 'nav' | 'orb' | 'composer'

/**
 * Pinned optics per variant — copied verbatim from the approved mockups
 * (`.plans/style-mocks/glass-mockups/src/chrome.jsx` OPTICS). Gentle bend:
 * reads as a material, not a funhouse mirror. mapSize capped at 256² (the
 * default 512² is wasted resolution at these element sizes), frost 0 — blur
 * must not be doing the work.
 */
export const GLASS_OPTICS: Record<GlassVariant, Partial<GlassOptics>> = {
  nav: {
    mapSize: 256,
    strength: 0.55,
    depth: 0.9,
    curvature: 0.62,
    dispersion: 0.55,
    bend: 0.75,
    bendWidth: 0.14,
    frost: 0,
    sheen: 0.8,
    glow: 0.28,
    specular: 1,
    brightness: 0.04,
  },
  orb: {
    mapSize: 256,
    strength: 0.85,
    depth: 1,
    curvature: 0.95,
    dispersion: 0.8,
    bend: 0.9,
    bendWidth: 0.18,
    frost: 0,
    sheen: 0.95,
    glow: 0.42,
    specular: 1.15,
    brightness: 0.06,
  },
  composer: {
    mapSize: 256,
    strength: 0.6,
    depth: 0.92,
    curvature: 0.68,
    dispersion: 0.6,
    bend: 0.78,
    bendWidth: 0.15,
    frost: 0,
    sheen: 0.82,
    glow: 0.3,
    specular: 1.05,
    brightness: 0.04,
  },
}

/** Lens tint + hairline edge for the flat variants (mockup `Lens`). */
const TINT_STYLE: CSSProperties = {
  background: 'var(--glass-tint)',
  border: '1px solid var(--glass-edge)',
}

/** The hero orb's full radial styling (mockup `Orb` — spec §4). */
const ORB_STYLE: CSSProperties = {
  position: 'relative',
  borderRadius: '50%',
  background:
    'radial-gradient(circle at 30% 24%, rgba(255,255,255,0.92), rgba(255,255,255,0.3) 38%, rgba(255,250,240,0.16) 64%, rgba(255,246,228,0.5) 100%)',
  border: '1.5px solid rgba(255,255,255,0.95)',
  boxShadow:
    '0 20px 50px rgba(180, 120, 60, 0.28), inset 0 -12px 26px rgba(240, 180, 120, 0.35)',
}

/** Static fallback surface: opaque warm panel + hairline + warm shadow. */
const STATIC_STYLE: CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  boxShadow: 'var(--shadow-soft)',
}

/** Lens-root sizing/padding per variant (width honors the outer wrapper). */
const GLASS_CLASS: Record<GlassVariant, string> = {
  nav: 'w-full rounded-full px-3 py-2',
  composer: 'w-full rounded-full px-4 py-2',
  orb: 'block rounded-full',
}

/** Flex layout lives on the inner row (never on the inline-block lens root). */
const ROW_CLASS: Record<GlassVariant, string> = {
  nav: 'flex w-full items-center justify-between gap-3',
  composer: 'flex w-full items-center gap-3',
  orb: 'relative h-full w-full',
}

export interface GlassSurfaceProps {
  /** Which of the three signature sites this lens serves. */
  variant: GlassVariant
  /** Orb diameter in CSS pixels (orb variant only). */
  size?: number
  /** Outer-wrapper classes: centering and width live here, not on the lens. */
  className?: string
  /** Outer-wrapper inline styles. */
  style?: CSSProperties
  /** Crisp content rendered inside the lens row. */
  children?: ReactNode
  /** data-testid for the wrapper (same node in both lens/fallback branches). */
  testId?: string
}

export function GlassSurface({
  variant,
  size,
  className,
  style,
  children,
  testId,
}: GlassSurfaceProps) {
  const effects = useOptionalReducedEffects()
  // Outside a provider (unit tests, decorative mounts) honor the OS signal
  // directly — reduced motion must still keep the lens off.
  const reducedEffects =
    effects?.reducedEffects ??
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (reducedEffects) {
    // Static equivalent — no lib import executed at all (the lens is a pure
    // motion affordance). Same node, same content, no refraction.
    return (
      <div
        data-testid={testId}
        data-fallback="static"
        className={className}
        style={{ ...STATIC_STYLE, ...style }}
      >
        <div className={[ROW_CLASS[variant], 'p-1'].join(' ')}>{children}</div>
      </div>
    )
  }

  return (
    <div data-testid={testId} className={className} style={style}>
      <Glass
        className={GLASS_CLASS[variant]}
        optics={GLASS_OPTICS[variant]}
        {...(variant === 'orb' ? { size, radius: size != null ? size / 2 : undefined } : {})}
        style={variant === 'orb' ? ORB_STYLE : TINT_STYLE}
      >
        <div className={ROW_CLASS[variant]}>
          {children}
          {variant === 'orb' ? (
            // Specular highlight crisp on top of the refracted page (mockup Orb).
            <span
              aria-hidden="true"
              className="pointer-events-none absolute left-[17%] top-[13%] h-[22%] w-[40%] rounded-full bg-white/85"
              style={{ filter: 'blur(8px)' }}
            />
          ) : null}
        </div>
      </Glass>
    </div>
  )
}
