# RE:FRAME Web App — Stage 6 Design Document

**Status:** approved design inputs (style, palette, component picks, license policy decided
by the project owner on 2026-10-18). This document is the build reference for Stage 6.
Honesty rules apply to every string in this UI: no diagnosis, no treatment claims, no
risk framing.

---

## 1. Confirmed direction

| Decision | Choice |
|---|---|
| Style | **Calm minimal** — low stimulation, generous whitespace, one accent |
| Palette | **Sage green** — warm off-white paper, green-gray ink, sage accent |
| Component sources | opensourceui.in + ObsidianUI + Liquid Glass + Canvas UI (all four) |
| Showcase picks | all nine (below) |
| Canvas UI license | **Vendor with license notice** — MIT + Commons Clause files copied into a clearly marked `vendored/` directory, NOT relicensed Apache-2.0 |

### License ledger (verified 2026-10-18)

| Source | License | Handling |
|---|---|---|
| opensourceui.in | MIT | normal copy-paste into `src/`, adapted to our tokens |
| ObsidianUI | MIT (`Atharvsinh-codez/ObsidianUI`) | normal copy-paste, adapted |
| `@samasante/liquid-glass` | MIT (npm dependency) | installed dep, one usage site |
| Canvas UI | **MIT + Commons Clause v1.0 (David Haz)** | vendored files under `web/vendored/canvas-ui/` with `LICENSE.md` copy + `NOTICE`: *these files are not covered by the repo's Apache-2.0 license; used inside the product per the Commons Clause "as part of an application" permission; not sold or redistributed as a component library* |
| lucide-react (icons) | MIT | normal dependency |

Every adapted component keeps an origin comment (`// adapted from <source>`).

---

## 2. Design tokens (calm minimal / sage)

CSS custom properties in one tokens stylesheet; all values contrast-verified (WCAG 2.2 AA)
by an automated test at build time.

```
--bg:            #FAFAF7   warm off-white paper
--surface:       #FFFFFF   cards, bubbles
--surface-sunk:  #F1F2ED   inputs, wells
--border:        #E3E5E0   hairline
--ink:           #1F2421   primary text (deep green-gray)
--ink-muted:     #59615B   secondary text (AA-verified on bg/surface)
--accent:        #4A7C59   sage — primary actions, links (AA with its text color)
--accent-soft:   #E8F0EA   tinted backgrounds, selected states
--warning:       #7A5B14   referral/persistent-flag notices (on --warning-soft)
--warning-soft:  #F6EFDC
--crisis:        #A33A32   crisis banner (AA text on --crisis-soft)
--crisis-soft:   #F8EAE8
```

- **Type:** system font stack only (no webfonts — privacy, speed). Body 16–17px / 1.6;
  headings medium weight (no ultra-bold); `font-variant-numeric: tabular-nums` for scores.
- **Space:** 4px base scale; chat reading column `max-width: 720px`; pages `1080px`.
- **Shape:** radius 14px cards / 10px inputs / 999px pills; hairline borders; one soft
  shadow token — shadows are the exception, borders the rule.
- **Motion:** transitions ≤160ms ease; a global `prefers-reduced-motion` kill switch AND
  an in-app **Settings → Reduce effects** toggle (follows OS by default). Every animated
  component must render a static equivalent when motion is off.

---

## 3. Component map (nine picks → screens)

| # | Component | Source (license) | Screen | Adaptation notes |
|---|---|---|---|---|
| 1 | Chat bubbles + toasts | opensourceui (MIT) | `/chat` | user/assistant bubbles, route-aware styling; **toasts are for non-critical confirmations ONLY** (e.g. "Check-in saved") — escalation is never toast-only |
| 2 | Focus-breath widget | opensourceui (MIT) | `/exercises` | paced-breathing break; copy must make **no physiological claims** ("a minute of paced breathing", not "reduces anxiety"); static cue under reduced motion |
| 3 | Journal writing card | opensourceui (MIT) | `/exercises` | **journal text never leaves the device** (localStorage only, never sent to the API); UI says so plainly; export + clear in Settings |
| 4 | Progress ring + trend charts | opensourceui + ObsidianUI (MIT) | `/check-ins` | hand-rolled SVG (no chart lib); shows instrument scores over time with the instrument's **published severity labels + citation**; **no traffic-light/risk coloring** (NICE NG225) — worsening trends use neutral ink + the API's flag notices, not red |
| 5 | Dashboard shell + status bars | ObsidianUI (MIT) | `/check-ins` chrome | status bar shows last check-in date/instrument; **no streaks, no guilt language** |
| 6 | Ambient backgrounds | opensourceui aurora/linen (MIT) | app backdrop | CSS-only, subtle; static variant under reduced motion |
| 7 | Liquid Glass orb | `@samasante/liquid-glass` (MIT) | onboarding hero + empty-chat state | ONE signature usage, not scattered; static frosted fallback when motion is off or the lens is disabled; disabled on low-power devices |
| 8 | Canvas ambience (frost/clouds) | Canvas UI (**vendored, MIT+Commons**) | optional ambience layer | **default OFF** (opt-in in Settings); vendored with license notice; `prefers-reduced-motion` forces it off regardless |
| 9 | Text Reel / Flip Text | ObsidianUI (MIT) | onboarding headline, empty states | short and interruptive only; static text under reduced motion |

---

## 4. Screens & routes

| Route | Purpose | Key elements |
|---|---|---|
| `/welcome` | first-run onboarding | honest framing (what this is / is not: wellness support, not care), privacy summary, Liquid Glass hero orb, Text Reel headline |
| `/chat` | main conversation | chat bubbles, **persistent crisis banner**, resources panel, inline exercise cards, honest 503 state |
| `/exercises` | exercise library | 3 categories from `GET /instruments`-era content (rule-matched in-chat too), focus-breath, journal card |
| `/check-ins` | measurement | instrument forms (driven by `GET /instruments`), results, history trends, progress ring, flag notices (referral/early-worsening presented as the API's `message`, never re-worded) |
| `/settings` | control | effects toggles, journal export/clear, data export/delete, version (`/health`) |

Crisis presentation is a shared component rendered on `/chat` whenever `route ==
crisis_bypass`: inline persistent banner (aria-live assertive) + always-visible real
resources — **never** a dismissible toast, never hidden behind a menu.

---

## 5. Non-negotiable UI rules (carried from the backend research)

1. **Wellness lane lint on the frontend:** a Vitest test scans all UI string constants for
   the banned families (diagnos, therap, treatment, prescrib, medication…) — same
   standard as the backend content lint.
2. **Escalation survives the UI layer:** crisis → banner + resources + scripted text;
   human_review / check-in concern → boundary copy exactly as the API returns it.
3. **Honest states:** 503 → "The assistant is unavailable right now" + crisis resources
   still reachable; loading states name what is happening; no fake streaming dots when
   nothing streams.
4. **No risk framing:** totals are instrument scores with published labels and citations,
   never colored as danger, never summed into anything.
5. **Accessibility:** WCAG 2.2 AA (skill `frontend-a11y` at build): keyboard-complete,
   visible focus, aria-live for chat, axe-clean in E2E, reduced-motion respected.
6. **Privacy copy is literal:** journal stays local; check-ins go to the local SQLite DB;
   message text goes to the configured LLM only when a key exists.

---

## 6. Tech stack

- **React 19 + TypeScript (strict) + Vite + Tailwind CSS** (opensourceui/ObsidianUI are
  Tailwind-native), `react-router-dom` for routes, `lucide-react` icons.
- **API client:** typed from FastAPI's `/openapi.json` via `openapi-typescript` generated
  in CI (drift test: fail if committed types differ from the served schema).
- **Dev:** Vite proxy → uvicorn (127.0.0.1:8000). **Prod:** FastAPI mounts the built SPA
  (small TDD extension to `create_app`/`create_service` + catch-all to `index.html`).
- **Tests:** Vitest + React Testing Library (component; **80% statements** gate for
  `web/src`, backend stays 100%); Playwright E2E (+ `@axe-core/playwright` a11y job).
- **E2E without an LLM key:** scripted routes (crisis, review, check-ins) run keyless;
  the generated-turn flow runs against a tiny mock OpenAI-compatible server
  (needs `REFRAME_LLM_BASE_URL`/`REFRAME_LLM_MODEL` config overrides — TDD addition).
- **PWA:** manifest (sage theming), service worker precaches the shell **and the crisis
  resources**, offline fallback page shows resources without a network.
- **CI:** new `web` job — install, typecheck, lint, unit+coverage, build, Playwright.

## 7. Sub-stage plan (each: TDD → gates → push → green CI → next)

| Sub | Scope | E2E added |
|---|---|---|
| **6a** | Vite/React/TS/Tailwind scaffold, design tokens, app shell + nav + reduced-motion engine, CI `web` job, OpenAPI type generation | — |
| **6b** | API client + `/chat` (bubbles, crisis banner, resources, honest 503, toasts) + first safety E2E (crisis message → banner + resources, model never used) | ✅ |
| **6c** | `/welcome` onboarding + `/exercises` (library, focus-breath, local-only journal, glass orb) | ✅ keyboard + reduced-motion flow |
| **6d** | `/check-ins` (forms, results, trend charts, progress ring, flag notices) + dashboard shell + effects layer (aurora, vendored frost/clouds with license notice) + Settings | ✅ full check-in flow |
| **6e** | PWA + static serving from FastAPI + mock-LLM generated-turn E2E + axe a11y pass + docs/roadmap wrap | ✅ complete matrix |

**Open items:** none blocking; SCS-SF wording verification (Neff 2011) remains a
backend-side carried item unrelated to UI build.
