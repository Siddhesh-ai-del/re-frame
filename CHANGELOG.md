# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Stage 2b constrained generation (`reframe.generation`): nine explicit system-prompt red lines (no diagnosis, treatment, impersonation, risk scoring, outcome promises; curated-exercises-only; decline-and-refer behavior), RAG-style context injection from the content library, a provider-agnostic LLM client protocol, and an OpenAI-compatible adapter (httpx, injectable transport, timeouts, sanitized errors that never contain the API key). 342 tests, 100% statement and branch coverage.
- Stage 2a content library (`reframe.content`): 12 curated exercise modules across rumination, behavioral activation, self-compassion, and emotion regulation — evidence-tiered A/B/C with real citations, contraindications, and the NICE NG222 rec. 1.2.10 early-worsening notice on every module. Deterministic rule-matched retrieval (no embeddings, no model calls) with tier-A-first selection. A wellness-lane lint test scans every content string against banned treatment/diagnosis claim patterns (fail-closed). 280 tests, 100% statement and branch coverage.
- Stage 1 safety layer (`reframe.safety`): deterministic, rule-based input classifier (23 compiled-regex rules across crisis, psychosis/mania, trauma-processing, and diagnosis-seeking signals), a fixed escalation policy table (HIGH_RISK → hard bypass with scripted crisis resources; REVIEW → human review queue; NORMAL → proceed), real crisis-resource references, and a pre-specified crisis-query audit harness (target recall 1.0, enforced by tests over a 46-case corpus). Fail-closed by design: over-flagging is the accepted direction of error; the generative model never participates in escalation decisions. 136 tests, 100% statement and branch coverage.
- Stage 0 scaffold: `src/reframe` Python package with an immutable, environment-driven settings loader (fail-closed secret boundary — production refuses to start without its API key, and secrets are excluded from all string renderings).
- TDD test suite: 21 tests written before implementation (RED → GREEN → refactor), 100% statement and branch coverage.
- CI pipeline: lint (ruff), format check, strict type check (mypy), tests on Python 3.12 and 3.14, and a gitleaks secret scan.
- Initial product repository: README, contributing guide, code of conduct, security policy, support policy, Apache-2.0 license, documentation index, and GitHub community-health templates.
- Repository standards: conventional commits, test-driven development with an 80%+ coverage gate, and a pull-request checklist requiring a pre-commit secret scan.

No implementation code has been committed. There are no releases.
