# Project Context & Standing Direction

**Read this first in every session working on RE:FRAME.** It records user-confirmed
direction, non-negotiable rules, and current project state. Last updated: 2026-10-17.

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
  fail-closed in pending-verification until its item wording is checked against Neff 2011;
  longitudinal CheckInTracker with PHQ-9 item-9 escalation, early-worsening AE signals
  (provisional thresholds, NICE NG222 1.2.10), persistent >=16 referral prompts (1.4.3);
  routing bridges check-in flags onto the pipeline's escalation vocabulary.
- **Test suite:** 542 tests, 100% statement and branch coverage; CI green (ruff, mypy
  strict, Python 3.12 + 3.14 matrix, gitleaks).
- **Next: Stage 5 — FastAPI service** exposing the conversation pipeline
  (`ConversationPipeline.handle`) and measurement endpoints (`record check-in` →
  `route_for_checkin`; tracker persistence decision needed — DB choice is a Stage 5
  sub-stage decision). Then Stage 6 web app (chat UI, onboarding, PWA — tested
  end-to-end before any Android work), Stage 7 evaluation harness, Stage 8 Android.
  Open item for Stage 5: verify SCS-SF item wording against Neff 2011 and activate it
  (moves from PENDING_VERIFICATION to INSTRUMENTS). See README roadmap for the
  authoritative stage table.
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
