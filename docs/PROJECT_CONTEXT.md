# Project Context & Standing Direction

**Read this first in every session working on RE:FRAME.** It records user-confirmed
direction, non-negotiable rules, and current project state. Last updated: 2026-10-19.

## What this is

RE:FRAME — an evidence-based, non-diagnostic, chatbot-first wellness tool for adults
managing rumination, painful memories, self-harshness, and early depressive distress,
before or alongside professional care. Grounded in a verified 147-source research report
(see "Research foundation" below).

- Repository: https://github.com/Siddhesh-ai-del/re-frame
- Local checkout: `/home/siddhesh/RE:FRAME/`

## Standing decisions (user-confirmed, 2026-10-15)

1. **Full professional product — no MVP shortcuts.** The research report uses "MVP"
   language for *scoping only*. The build standard is a real, complete, tested product
   with sub-staged delivery and quality gates — never a throwaway prototype.
2. **Web first, Android later.** The website is built and tested end-to-end before any
   native app work begins. The backend (safety pipeline, retrieval, generation) is
   platform-agnostic; an Android client (or PWA install) is a later, thin layer over the
   same proven API.
3. **The wellness lane is inviolable.** The product never diagnoses, never treats, never
   implies treatment, never assesses clinical risk. This is both a research-backed safety
   requirement and a source of pride — "something worth being proud of" and "honest, safe,
   professional" are the same product. The safety layer (`reframe.safety`) and its 100%
   coverage / audit-recall gates are non-negotiable.
4. **Personal use is intended.** The user is the target profile: an adult, wellness
   positioning, non-diagnostic. The product should be something its maker uses daily.
5. **Stage granularity is flexible.** The lead may split any stage into sub-stages when a
   slice is too large to build and verify properly. Quality gates apply per stage:
   TDD (red → green → refactor), 100% coverage on security-critical code, all CI jobs
   green, and roadmap status flips to Complete only *after* CI evidence exists.

## Standing decisions (user-confirmed, 2026-10-18 — Stage 6 web design)

6. **Style: calm minimal, sage-green palette.** Warm off-white paper, green-gray ink,
   sage accent; system fonts; hairline borders over shadows; motion ≤160ms with a global
   `prefers-reduced-motion` kill switch plus an in-app "Reduce effects" toggle.
   Full tokens and rules: `docs/webapp-design.md` (the build reference for Stage 6).
7. **All four component sources, all nine showcase picks** — chat bubbles + toasts,
   focus-breath, journal card, progress ring + trend charts, dashboard shell + status
   bars, ambient backgrounds, Liquid Glass orb, Canvas frost/clouds ambience, Text
   Reel/Flip Text headings — adapted to our tokens, origin-commented, reduced-motion
   gated.
8. **Licenses verified:** opensourceui.in, ObsidianUI, `@samasante/liquid-glass`,
   lucide-react = MIT. **Canvas UI = MIT + Commons Clause** → handled by the user's
   choice: vendored under `web/vendored/canvas-ui/` with its LICENSE copy and an
   explicit NOTICE that those files are NOT Apache-2.0; product use only, never
   redistributed as components.
9. **UI safety rules are non-negotiable:** escalation is never toast-only (crisis =
   persistent banner + always-visible resources); frontend wellness-lane lint mirrors
   the backend banned-word families; score displays use published severity labels +
   citations with **no traffic-light/risk coloring** (NG225); journal text stays on
   device; honest error states (503 = assistant unavailable, resources still reachable).

## Standing decisions (Stage 6e completion, 2026-10-19 — per the approved stage spec)

10. **Config LLM overrides.** `REFRAME_LLM_BASE_URL` / `REFRAME_LLM_MODEL` optionally
    replace the CLI's OpenAI defaults; base URL is fail-closed (non-`http(s)` → the
    service refuses to start). Blank = unset. Generation still always requires
    `REFRAME_API_KEY` — overrides alone never enable a model.
11. **Static serving from FastAPI.** `python -m reframe.cli --static <dir>` mounts the
    built SPA LAST in `create_service`, so every API route wins by registration order —
    the prod `/chat` method collision resolves exactly like the dev proxy (GET → SPA,
    POST → API). No `static_dir`/missing dir = API-only app, byte-identical route table.
12. **PWA + offline.** Install manifest (sage `#4A7C59`, honest description); service
    worker precaches the app shell (mandatory) and `GET /resources` + `offline.html`
    (best-effort), serves navigations network-first with a cache/offline fallback, and
    cache-fills same-origin assets; `offline.html` carries the crisis resources HARDCODED
    so they render with no network at all. Registration runs only in production builds
    and never throws.
13. **Axe-clean is a bar, not a report.** Every route must show ZERO axe-core
    violations (WCAG 2.2 AA) in E2E; violations are fixed in the component, never
    allowlisted. (6e fix: derived `--accent-ink` token — accent text on the doc-pinned
    `--accent-soft` tint is 4.19:1, so selected states use the darker 5.37:1 sage.)
14. **Mock-LLM E2E pattern.** Generated-turn proofs run against a REAL composed service
    (built SPA + API in one FastAPI process) wired by config overrides to a stdlib mock
    OpenAI provider — no real credentials anywhere, and the 21 safety specs stay keyless
    on the separate dev lane (ports 8123/5373; composed lane 8124/8125; port 8000 is
    never touched).

## Standing decisions (Stage 6f completion, 2026-10-19 — Golden Glass restyle)

15. **Golden Glass is the styling direction (spec's "D10").** The web app's visual
    layer follows `.plans/stage-6f-golden-glass-spec.md` / `docs/webapp-design-golden-glass.md`
    and supersedes `docs/webapp-design.md` **for styling only** (safety/honesty sections
    there stay authoritative). Decisions:
    - **Light-only.** Cream sky (`--bg #FFF4E4`), terracotta accent (`#A8501C`), warm
      brown ink (`#34261A`); no dark block in `tokens.css` — a dark theme would be a
      new stage, not a token swap.
    - **3-lens budget.** Exactly three `@samasante/liquid-glass` sites (nav pill,
      GlassOrb, chat composer), all via the shared `GlassSurface` primitive in
      **material mode** — `filterResolution` is never passed (it disqualifies material
      mode and warps children). Optics pinned per variant (nav/orb/composer) and
      asserted by test.
    - **`mapSize: 256` and `frost: 0`** at all three sites; per-site strength/depth/
      curvature/dispersion/bend/sheen/glow/specular/brightness per the spec §4 table.
    - **CTA gradient** `#A8501C → #8A3F14` with `--cta-text #FFF9F0` (5.24/7.16) and
      `--cta-hover #7A3611`; used for primary actions only.
    - **Reduced effects = no lens.** The lib never mounts under reduced effects; each
      site renders an opaque warm static fallback keeping its testids
      (`glass-orb`/`data-fallback="frosted"`, `data-fallback="static"`,
      `composer-glass`). Landscape stays static; only the haze drift class is dropped.
    - **Added token `--ink-on #FFF6EA`** (text on ink pills) beyond the spec's list —
      contrast-paired with `--ink` in `contrast.test.ts`. `--accent-bright #E8853C` is
      decorative-only (never a text background).

## How we work (established conventions)

- **Stack:** Python ≥ 3.11 (FastAPI planned for the API), TypeScript/React planned for
  the frontend; tooling via `uv`, `.venv` in-repo.
- **TDD is mandatory** (ECC `/TDD` workflow via the tdd-guide agent): failing test first,
  minimal implementation, refactor; coverage gate enforced in pytest config.
- **CI:** ruff lint + format, mypy strict, pytest on Python 3.12 + 3.14, gitleaks secret
  scan. Every push to `main` or PR must be green.
- **Commits:** conventional format (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`). One stage
  of work per push where practical.
- **Honesty rules:** no invented claims, metrics, badges, or CI; no secrets ever
  (environment/keyring only); roadmap and README statements must match verifiable
  reality at the time they are written.

## Current state (update this section when it changes)

- **Stage 0 — Complete:** repository scaffold, test harness, CI pipeline, security baseline.
- **Stage 1 — Complete:** `reframe.safety` — deterministic input classifier (23 rules),
  fixed escalation policy table (hard bypass / human review / proceed), real crisis
  resources, crisis-query audit harness (recall target 1.0).
- **Stage 2 — Complete (sub-staged 2a/2b/2c):** `reframe.content` (12 evidence-tiered
  exercise modules + deterministic rule-matched retrieval + wellness-lane content lint),
  `reframe.generation` (nine system-prompt red lines, provider-agnostic OpenAI-compatible
  client, network-free tests), `reframe.pipeline` (Layer-5 output filter + orchestration:
  safety decides before generation; model never called on crisis/review routes).
- **Stage 3 — Complete:** intervention delivery through the pipeline (exercises served
  in-conversation; covered by 2a/2c work).
- **Stage 4 — Complete (sub-staged 4a/4b):** `reframe.measurement` — verbatim PHQ-9,
  GAD-7, K-10 instruments with fail-closed scoring and band-partition tests; SCS-SF held
  fail-closed in pending-verification until its item wording is checked against Neff 2011
  (RESOLVED 2026-10-25: wording verified verbatim against the official self-compassion.org
  SCS-SF information sheet + Neff permission letter and activated in `INSTRUMENTS`;
  `PENDING_VERIFICATION` now empty);
  longitudinal CheckInTracker with PHQ-9 item-9 escalation, early-worsening AE signals
  (provisional thresholds, NICE NG222 1.2.10), persistent >=16 referral prompts (1.4.3);
  routing bridges check-in flags onto the pipeline's escalation vocabulary.
- **Stage 5 — Complete (sub-staged 5a/5b/5c/5d):** FastAPI service — `reframe.api.app`
  (create_app: /health, /chat; fail-closed error mapping: GenerationError->503,
  ValueError->422, Exception->500, all generic — secret-token probes prove no leakage;
  crisis bypass verified through HTTP with the generator never called),
  `reframe.api.measure` (GET /instruments form-ready specs; POST /checkins returns
  score + flags + routing — item 9 -> hard_bypass + scripted crisis text, persistent
  >=16 / early-worsening -> human_review + concern copy; GET /checkins/{id} history),
  `reframe.measurement.store`/`persistent` (CheckInStore protocol + sqlite3 engine,
  fail-closed row loading, flags restored verbatim, lock-guarded
  PersistentCheckInTracker with rollback-on-persist-failure),
  `reframe.api.service`/`reframe.cli` (create_service composition root — one app with
  both route families + store closed on shutdown; runnable `python -m reframe.cli`,
  no-key dev mode serves scripted routes with generated turns 503-ing cleanly).
  README updated: status paragraph, roadmap (0–5 Complete), coverage gate text (100%),
  architecture status line, layout tree (measurement/api/cli added), local-run section.
- **Stage 6 — Complete (sub-staged 6a–6f), built strictly per `docs/webapp-design.md`
  (6f styling per `docs/webapp-design-golden-glass.md`):**
  web application in `web/` (Vite + React 19 + strict TS + Tailwind 4, Golden Glass
  tokens per 6f — originally sage) with
  five routes — onboarding, chat, exercise library, check-in dashboard, settings — plus
  typed API client, honest error/503 states, crisis banner + resources, device-local
  journal, reduced-effects engine, vendored Canvas UI (with NOTICE), and a frontend
  wellness-lane claims lint. Final sub-stage 6e added: config LLM overrides
  (`REFRAME_LLM_BASE_URL`/`REFRAME_LLM_MODEL`, fail-closed), `--static <dir>` FastAPI
  serving of the built SPA (route precedence: API routes registered before the mount win;
  `GET /chat` → SPA, `POST /chat` → API), PWA (manifest + service worker precaching the
  shell and `/resources` + network-free `offline.html` with hardcoded crisis resources,
  registration production-only), axe-core zero-violation pass over all five routes
  (component fix: derived `--accent-ink` token for accent text on the pinned
  `--accent-soft` tint), and a mock-LLM generated-turn E2E against a real composed
  service (`web/dist` + `--static` + stdlib mock provider) proving a generated reply
  reaches the UI without any real credential. Sub-stage 6f restyled the whole web app
  to **Golden Glass** (warm cream/terracotta tokens, static landscape background,
  floating glass nav pill + orb + composer lenses via one shared `GlassSurface`
  primitive, all with full reduced-effects static fallbacks; serif display headings;
  CTA gradients) with zero behavior change — safety surfaces, verbatim copy, testids,
  and roles untouched (D15); PWA manifest/icons/theme-color retinted to terracotta.
  README roadmap flipped to Complete with evidence; CHANGELOG updated.
- **Test suite:** backend 689 tests at 100% statement and branch coverage; web 373
  frontend tests at 99.09% statements / 94.96% branches; 31 Playwright E2E specs (21
  keyless safety specs unchanged + 5 axe + 3 generated-turn + 2 PWA offline), axe zero
  violations on all five routes; CI green
  (ruff, mypy strict, Python 3.12 + 3.14 matrix, gitleaks).
- **Next: Stage 7 — evaluation harness** (adverse-event logging, feasibility-pilot
  instrumentation and reporting, per the README roadmap table). Stage 8 — Android client
  follows after, reusing the proven API (D2/D3: web-first, then native; `--static`
  serving also means the same API process can serve a webview-backed client directly).
  Open items carried: none on SCS-SF — its item wording was verified against the
  primary source (self-compassion.org SCS-SF information sheet + Neff permission letter,
  2026-10-25) and it is now ACTIVE in `INSTRUMENTS`. Modeling decision recorded at
  activation: `total` is the Raes et al. 2011 integer item-sum (12–60, the original
  paper totaled rather than averaged); because every SCS-SF subscale has exactly 2
  items, the sheet's mean-of-subscales total is algebraically sum/12, so the modern
  mean score is derivable with no scoring-engine change. The low/moderate/high bands
  (12–29 / 30–42 / 43–60) are the sheet's explicitly AD HOC rubric mapped ×12, with
  no clinical norms — trait-level labels, not clinical severity.
  See README roadmap for the authoritative stage table.
- **Housekeeping (decided 2026-10-15):** research files (`distress-management-pipeline.md`,
  `.provenance.md`) are intentionally untracked in the repo root; `.drafts/` and `.plans/`
  are git-ignored working artifacts. The old docs-only clone at `/home/siddhesh/re-frame/`
  is redundant and kept only as a backup.

## Research foundation

- `distress-management-pipeline.md` (repo root, untracked) — the verified research report:
  evidence tiers (A/B/C), architecture, safety classification, evaluation plan.
- `distress-management-pipeline.provenance.md` — verification provenance
  (PASS WITH NOTES; blocked URL disclosures). Working drafts and the approved research
  plan live in `.drafts/` and `.plans/` (git-ignored).

When a decision here is overridden, update this file in the same change — it is the
single source of directional truth for fresh sessions.
