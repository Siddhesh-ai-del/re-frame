# RE:FRAME Web App — Stage 6f Design Document (Golden Glass)

**Status:** approved and implemented (Stage 6f, 2026-10-19, per
`.plans/stage-6f-golden-glass-spec.md`). This document supersedes
`docs/webapp-design.md` **for styling only** — tokens, palette, shape, motion,
ambient background, and component chrome. The safety and honesty sections of
`docs/webapp-design.md` (escalation never toast-only, no risk coloring on
published labels, journal on device, honest error states, wellness-lane copy
rules) remain authoritative and unchanged.

Honesty rules apply to every string in this UI: no diagnosis, no treatment
claims, no risk framing.

---

## 1. Direction rationale

Stage 6 shipped the calm-minimal / sage design. Stage 6f restyles to **Golden
Glass**: a warm, sunlit, light-only palette (cream sky, terracotta accent, warm
brown ink) over a static layered landscape, with three real liquid-glass lenses
carrying the app's focal chrome. Why this direction:

- **Warmth without softness of claim.** The cream/terracotta palette reads calm
  and human, not clinical and not "wellness-influencer" — it supports the
  honest, non-diagnostic tone.
- **Depth without motion cost.** The landscape is fully static (sun, haze,
  contours, hills are fixed layers); only two small elements drift, and both
  are removed under reduced effects. Visual richness doesn't require animated
  load.
- **Glass as accent, not substrate.** Exactly three lens sites means the glass
  stays a focal accent, keeps text fully readable, and keeps the reduced-effects
  fallback surface small and audited.
- **Light-only.** There is no dark block in `tokens.css`; the sky gradient is
  the identity. A dark theme would be a new stage, not a token swap.

## 2. Token table (all ratios WCAG 2.2 AA, verified by `src/styles/contrast.test.ts`)

### Core

| Token | Value | Notes |
|---|---|---|
| `--bg` | `#FFF4E4` | warm sky cream (page background) |
| `--surface` | `#FFFCF7` | warm panel white |
| `--surface-sunk` | `#F5E7D0` | sunken warm sand |
| `--border` | `#EAD9C2` | warm hairline — UI borders only, never a text pair |
| `--ink` | `#34261A` | warm brown ink — 13.43:1 on bg |
| `--ink-muted` | `#6E5847` | 6.13 bg / 5.47 sunk / 5.45 accent-soft |
| `--ink-on` | `#FFF6EA` | text on ink pills (nav active, selected chips) — added beyond the spec list; pairs with `--ink` in `contrast.test.ts` |
| `--accent` | `#A8501C` | terracotta — 5.04 bg / 5.36 surface |
| `--accent-soft` | `#FAE5CD` | peach tint |
| `--accent-ink` | `#8A3F14` | deep terracotta text — 6.12 accent-soft / 6.89 bg |
| `--accent-bright` | `#E8853C` | **decorative only** (dots, gradients, chart line) — never a text background |
| `--cta-start` / `--cta-end` | `#A8501C` → `#8A3F14` | CTA gradient; `--cta-text #FFF9F0` = 5.24 / 7.16 |
| `--cta-hover` | `#7A3611` | 8.49 |
| `--warning` / `--warning-soft` | `#6E5210` / `#F6EBD2` | 6.16 / 6.71 |
| `--crisis` / `--crisis-soft` | `#8F2F27` / `#F8E7E4` | 6.74 / 7.42 |

### Landscape (decorative — no text pairs)

```
--sky-top: #FFF4E4; --sky-mid: #FFE8CC; --sky-low: #F9E0C6;   (+ body tail #F6DEC5)
--hill-1: #CBD9BA;  --hill-2: #AFC7A4;  --hill-3: #8FAD92;
--sun-core: #FFFAF0; --sun-edge: #FFC988; --sun-glow: rgba(255,214,150,.85);
--contour: rgba(150,105,60,.40); --contour-2: rgba(196,103,43,.40);
--panel: rgba(255,251,243,.86); --glass-tint: rgba(255,252,246,.42);
--glass-edge: rgba(255,255,255,.72);
```

### Shape / type / motion

- Radii: `--radius-card: 26px`, `--radius-input: 18px`, `--radius-pill: 999px`.
- Shadow: warm `0 14px 40px rgba(150,100,50,.15)` (`--shadow-soft`).
- Type: body stays the system sans; `--font-display: ui-serif, Georgia,
  'Iowan Old Style', serif` for `h1`/section display headings (700, tight
  leading, -0.01em).
- Motion tokens **unchanged** (160ms cap, `--motion-*` aliases preserved).
- Body background: fixed sky gradient `--sky-top → --sky-mid 26% → --sky-low
  58% → #F6DEC5`; text stays `--ink`.
- Legacy aliases used by existing tests/components (`--surface`,
  `--surface-sunk`, `--ink-muted`, `--radius-*`, `--motion-*`, `--space-*`,
  `--width-*`, the reduced-effects `0ms` rule) are preserved so styling
  changes never reach behavior.

## 3. The 3-lens budget + optics table

There are **exactly three** liquid-glass lens sites in the app, all built on one
shared primitive, `src/components/glass/GlassSurface.tsx`
(`variant: 'nav' | 'orb' | 'composer'`). Nothing else gets a lens.

| Site | Component | Optics (`@samasante/liquid-glass`, material mode) |
|---|---|---|
| Nav pill | `AppShell` header | `mapSize 256, strength .55, depth .9, curvature .62, dispersion .55, bend .75, bendWidth .14, frost 0, sheen .8, glow .28, specular 1, brightness .04` |
| Hero orb | `GlassOrb` (reimplemented on the primitive) | `mapSize 256, strength .85, depth 1, curvature .95, dispersion .8, bend .9, bendWidth .18, frost 0, sheen .95, glow .42, specular 1.15, brightness .06` |
| Chat composer | `Composer` input row (`testId="composer-glass"`) | `mapSize 256, strength .6, depth .92, curvature .68, dispersion .6, bend .78, bendWidth .15, frost 0, sheen .82, glow .3, specular 1.05, brightness .04` |

Tint/edge per variant via inline style: nav/composer get
`background: var(--glass-tint); border: 1px solid var(--glass-edge)`; the orb
gets the full radial-gradient treatment from the approved mockup.

## 4. The material-mode gotcha (`filterResolution`)

`@samasante/liquid-glass` has two modes. Passing **`filterResolution`**
disqualifies material mode: the library then refracts the lens's *children*
instead of sampling the page behind it, so the nav links / orb mark / composer
text render warped and unreadable (this was debugged in
`.plans/style-mocks/glass-mockups`).

**Rule: never pass `filterResolution` at any of the three sites.** Sizing
(`width`/`height`) lives on the outer wrapper / lens class because the library
forces `display: inline-block` on its root; flex layout lives on an inner row
(the mockup `.nav-row` / `.composer-row` pattern). A unit test in
`GlassSurface.test.tsx` asserts the prop is never forwarded.

## 5. Reduced-effects contract

Under `data-reduced-effects` (in-app "Reduce effects" = on, or reduced via the
system signal when set to "system") the lens **never mounts**:

- `GlassSurface` renders a plain static div — opaque warm `--surface`,
  border, warm shadow — with `data-fallback="static"` and **no**
  `@samasante/liquid-glass` import instantiated. It resolves reduced state from
  `EffectsProvider`, falling back to the OS `prefers-reduced-motion` media
  query when no provider is present (the composer renders without one in
  tests).
- `GlassOrb` keeps its own `data-testid="glass-orb"` and
  `data-fallback="frosted"` static branch, byte-compatible with the Stage 6c
  contract.
- The ambient landscape stays (it is static by construction); only the haze
  drift animation class is dropped, and the two haze blobs leave the animated
  state. Everything under reduced effects is a static, fully opaque surface —
  same information, same testids, zero lib code running.

## 6. What styling changes may touch in tests

Per spec §7, only **styling assertions** may change (colors, class names,
layout). Testids, roles, aria attributes, verbatim copy, and behavioral
assertions are untouched. Safety surfaces kept their semantics: the crisis
banner is still a persistent `role=alert` banner with always-visible
resources (restyled to warm amber warning tokens), flag notices remain verbatim,
published labels + citations still carry no risk coloring, and journal data
stays on device.
