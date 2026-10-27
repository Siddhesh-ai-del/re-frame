# RE:FRAME

[![License](https://img.shields.io/badge/License-Apache_2.0-0F172A?style=for-the-badge&labelColor=0F172A&logo=apache&logoColor=white)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Pre--release-0F172A?style=for-the-badge&labelColor=0F172A&logo=rocket&logoColor=white)](#project-status)
[![CI](https://img.shields.io/github/actions/workflow/status/Siddhesh-ai-del/re-frame/ci.yml?style=for-the-badge&label=CI&labelColor=0F172A&color=0F172A&logo=githubactions&logoColor=white&event=push)](../../actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/Platform-Web-0F172A?style=for-the-badge&labelColor=0F172A&logo=googlechrome&logoColor=white)](#planned-capabilities)

**An evidence-based, non-diagnostic chatbot-first wellness tool for adults managing rumination, painful memories, self-harshness, and early depressive distress — before or alongside professional care.**

## Overview

RE:FRAME delivers structured, evidence-based self-help techniques (rumination postponement and concreteness training, behavioral activation, self-compassion) through a conversational interface. It does not diagnose, does not treat, and does not replace professional care. Every technique and safety rule in the design traces back to a 147-source research review spanning clinical guidelines, meta-analyses, digital-intervention trials, and safety engineering literature.

| Principle | What it means |
|-----------|---------------|
| **Non-diagnostic by design** | Wellness positioning only; disease, treatment, or risk-assessment language is excluded from copy and model outputs by design. |
| **Safety is architecture, not policy** | Escalation policy is deterministic; the generative model never decides whether to escalate. Crisis signals trigger a hard bypass to scripted resources. |
| **Evidence-tiered content** | Every technique carries an explicit evidence tier — (A) guideline/meta-analysis, (B) trial-level, (C) experimental — so nothing experimental is presented as validated. |
| **Evaluate before claiming** | Pre-specified adverse-event definitions and a feasibility pilot come before any efficacy claim. |

## Why RE:FRAME

The problem space is documented, not assumed:

- **Rumination is the best-supported software-addressable target.** Repetitive negative thinking predicts persistence and relapse of depression, and NICE NG222 names rumination as a relapse risk factor; rumination-focused CBT packages show the largest effects on rumination outcomes (|g| ≈ 0.76–0.99).
- **Guided self-help is the guideline-backed first line for less-severe depression.** NICE NG222 positions guided self-help (CBT/BA principles, printed or digital) as the least intrusive, least resource-intensive first option — the exact population this product targets.
- **Digital delivery works, but modestly.** Self-guided digital interventions show g ≈ 0.27–0.53 for depressive symptoms; human guidance and initial screening are the highest-leverage design choices, which is why RE:FRAME pairs a chatbot interface with escalation-to-human pathways.
- **Safety failures in LLM mental-health products are published and specific.** Slow escalation of suicidality, informational rather than therapeutic responses, and sycophancy under pressure are documented failure modes — addressed here by layered, deterministic safety rather than prompt-level hopes.
- **Adverse events are common enough to require monitoring.** Deterioration occurs in roughly 6.7% of digital-intervention participants; none of the 21 reviewed GenAI mental-health interventions even defines an adverse event. RE:FRAME pre-specifies them.

The full research base, caveats (including what remains uncertain), and the safe evaluation plan are documented in the project's research report.

## Planned capabilities

- Non-diagnostic supportive conversation with a chatbot-first interface
- Rule-grounded delivery of structured self-help exercises (rumination, behavioral activation, self-compassion) with an LLM language wrapper — the model never authors clinical advice
- Input risk classification with a deterministic escalation policy and a hard bypass to scripted crisis resources
- Output filtering that blocks diagnosis, treatment advice, impersonation of professionals, and sycophantic reinforcement
- Self-tracking with free validated instruments (K-10, PHQ-9, GAD-7, SCS-SF) and longitudinal progress views
- Safety audit logging and pre-specified adverse-event monitoring

> **Pre-release.** The pipeline and a local web application exist and are tested end-to-end (see the Roadmap below); there is no hosted service, no release, and nothing runs without your own local setup.

## Project status

**Pre-release.** Stages 0–6 are complete with green CI: the backend (safety layer, conversation core, intervention delivery, measurement, and the FastAPI service) at 689 tests and 100% coverage, and the web application (chat, onboarding, exercise library, check-ins, settings) at 343 frontend tests / 98.99% statement coverage plus 31 Playwright end-to-end specs — including an axe-core accessibility pass with zero violations on all five routes, a service-worker offline proof, and a generated-reply proof against a mock LLM provider. The evaluation harness (Stage 7) and the Android client (Stage 8) are still to come; there are no releases yet.

### Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| Stage 0 | Repository scaffold, test harness, CI, security baseline | **Complete** |
| Stage 1 | Safety layer: input risk classifier, deterministic escalation policy, crisis-query audit harness | **Complete** |
| Stage 2 | Conversation core: content library + retrieval, constrained generation, output filter, pipeline orchestration | **Complete** |
| Stage 3 | Intervention delivery: evidence-tiered exercise library served through the pipeline (rumination, behavioral activation, self-compassion, emotion regulation) | **Complete** |
| Stage 4 | Measurement: validated self-report instruments (K-10, PHQ-9, GAD-7, SCS-SF), scoring, and longitudinal tracking | **Complete** |
| Stage 5 | API service (FastAPI) exposing the conversation pipeline and measurement endpoints | **Complete** |
| Stage 6 | Web application: chat interface, onboarding, tracking views, PWA — built and tested end-to-end before any native client | **Complete** (5-route web app, PWA with offline shell, `--static` serving from FastAPI, mock-LLM generated-turn E2E, zero-violation axe pass) |
| Stage 7 | Evaluation harness: adverse-event logging, feasibility-pilot instrumentation and reporting | **Complete** (7a+7b: pre-specified AE taxonomy + fail-closed adverse-event log (SQLite), automatic/audit/review detection, pilot metrics, pre-specified green/amber/red progression criteria, feasibility report with a non-efficacy banner via `GET /evaluation/report` + CLI `--report`/`--audit`; report UI planned as 7c) |
| Stage 8 | Android client, reusing the proven API (after the web app is tested end-to-end) | Planned |

Each stage follows test-driven development (tests first, 100% statement and branch coverage gate) and is pushed only after its stage tests pass with green CI.

## Installation

**Not yet available as a release.** To run the project locally from a checkout (development):

### API only (backend service)

```bash
uv sync                      # or: pip install -e .
python -m reframe.cli        # serves http://127.0.0.1:8000
```

Development runs without an LLM API key: scripted crisis and boundary routes and all measurement endpoints work as-is; generated replies return a clean 503 until `REFRAME_API_KEY` is set. Check-ins persist to `reframe.db` (override with `--db`).

### Web app (dev server)

```bash
cd web
npm ci
npm run dev                  # serves http://127.0.0.1:5373, API proxy targets :8000
```

The dev server proxies the API paths to the backend (`REFRAME_API_TARGET` overrides the target, which is how E2E points it at its own backend port).

### Built SPA served by FastAPI (closest to production)

```bash
cd web && npm run build      # produces web/dist
cd .. && python -m reframe.cli --static web/dist
```

One process then serves both the built web app and the JSON API: registered API routes win, `GET /chat` and any other unknown GET fall through to the SPA shell. `npm run e2e` in `web/` exercises this composed service end-to-end against a mock LLM provider (no real credentials anywhere).

### Configuration (environment variables)

| Variable | Purpose |
|----------|---------|
| `REFRAME_ENV` | `development` (default) / `test` / `production` — production refuses to start without an API key |
| `REFRAME_API_KEY` | LLM API key; unset = server still runs, generated turns return an honest 503 |
| `REFRAME_LLM_BASE_URL` | Optional OpenAI-compatible endpoint override (must be `http(s)://`, fail-closed) |
| `REFRAME_LLM_MODEL` | Optional model-name override (defaults to `gpt-4o-mini`) |

Full installation instructions will appear here once a first release exists.

## Architecture

RE:FRAME is intended to be built as a layered pipeline in which safety layers bracket generation:

1. **Input safety layer** — validated risk classifier; risk/intent routing (crisis language, self-harm mentions, psychosis/mania cues, trauma-processing requests, diagnosis-seeking requests). High risk triggers a hard bypass; uncertain results route to a human review queue.
2. **Retrieval layer** — retrieval-augmented access to a curated, evidence-tiered content library; the generative model draws on vetted material rather than authoring advice.
3. **Constrained generation** — system-level red lines: no diagnosis, no treatment advice, no risk scoring, no professional impersonation.
4. **Output safety layer** — independent filter that catches escalation-worthy content, boundary violations, and sycophancy before a reply is delivered.
5. **Escalation path** — deterministic, non-negotiable: scripted crisis resources and referral prompts; no risk-score stratification (in line with NICE NG225 guidance against risk scales for prediction or categorization).

**Status:** the safety, retrieval, generation, filtering, and measurement layers exist today as tested backend components, exposed through a tested FastAPI service; a tested React web application (installed as a PWA, with an offline fallback page carrying the standing crisis resources) consumes that service, either through a dev-server proxy or served directly by FastAPI from a production build. See Repository layout for both halves.

## Repository layout

```
re-frame/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── SUPPORT.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── src/
│   └── reframe/
│       ├── __init__.py
│       ├── config.py
│       ├── cli.py
│       ├── safety/
│       │   ├── __init__.py
│       │   ├── types.py
│       │   ├── classifier.py
│       │   ├── escalation.py
│       │   ├── resources.py
│       │   └── audit.py
│       ├── content/
│       │   ├── __init__.py
│       │   ├── schema.py
│       │   ├── library.py
│       │   ├── matching.py
│       │   ├── retrieval.py
│       │   └── data/
│       │       └── exercises.json
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── prompts.py
│       │   ├── openai_client.py
│       │   └── generator.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── output_filter.py
│       │   ├── messages.py
│       │   └── pipeline.py
│       ├── measurement/
│       │   ├── __init__.py
│       │   ├── instruments.py
│       │   ├── scoring.py
│       │   ├── flags.py
│       │   ├── tracker.py
│       │   ├── routing.py
│       │   ├── store.py
│       │   └── persistent.py
│       └── api/
│           ├── __init__.py
│           ├── schemas.py
│           ├── app.py
│           ├── measure.py
│           └── service.py
├── tests/
│   ├── test_package.py
│   ├── test_config.py
│   ├── test_safety_*.py
│   ├── test_content_*.py
│   ├── test_generation_*.py
│   ├── test_pipeline_*.py
│   ├── test_measurement_*.py
│   ├── test_api_*.py
│   ├── test_cli.py
│   └── data/
│       └── audit_corpus.json
├── scripts/
│   └── dump_openapi.py          # deterministic OpenAPI dump (CI schema-drift gate)
├── web/
│   ├── package.json             # npm scripts invoke ./node_modules/.bin/* (colon-safe repo path)
│   ├── playwright.config.ts     # dev lane (port 5373 + backend 8123) and composed-service lane (8124 + mock LLM 8125)
│   ├── index.html               # links the manifest + sage theme-color
│   ├── public/
│   │   ├── manifest.webmanifest # PWA install manifest (sage theming)
│   │   ├── sw.js                # service worker: precaches shell + /resources, offline navigation, cache-first assets
│   │   ├── offline.html         # network-free fallback page with hardcoded crisis resources
│   │   └── icon.svg / icon-maskable.svg / favicon.svg
│   ├── scripts/
│   │   └── mock-llm-server.py   # stdlib OpenAI-compatible mock provider for the generated-turn E2E
│   ├── src/
│   │   ├── App.tsx / main.tsx   # routes + production-only SW registration
│   │   ├── api/                 # typed client + generated OpenAPI schema types
│   │   ├── pages/               # Welcome, Chat, Exercises, Check-ins, Settings
│   │   ├── components/          # AppShell, chat, onboarding, exercises, checkins, settings, toast
│   │   ├── effects/             # reduced-motion engine, ambient aurora, FrostClouds wrapper
│   │   ├── pwa/                 # service-worker registration module (no-op outside prod)
│   │   ├── styles/              # sage design tokens + WCAG contrast tests
│   │   ├── lib/ lint/ test/     # device-local journal, wellness-lane claims lint, setup
│   │   └── api/schema.json      # OpenAPI schema (dumped by scripts/dump_openapi.py)
│   ├── e2e/                     # Playwright specs: 21 keyless safety specs + axe a11y + generated-turn + PWA offline
│   └── vendored/                # Canvas UI (MIT + Commons Clause) — see its NOTICE, not Apache-2.0
├── docs/
│   └── README.md
└── .github/
    ├── CODEOWNERS
    ├── PULL_REQUEST_TEMPLATE.md
    ├── ISSUE_TEMPLATE/
    │   ├── config.yml
    │   ├── bug_report.yml
    │   └── feature_request.yml
    └── workflows/
        └── ci.yml
```

## Contributing

Bug reports, feature proposals, and code contributions are welcome once implementation begins. See [CONTRIBUTING.md](CONTRIBUTING.md) for standards — test-driven development, 80%+ coverage, and conventional commits are required from the first line of code. All participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Security issues and vulnerabilities must be reported privately — see [SECURITY.md](SECURITY.md). Do not open public issues for security reports.

## Support

See [SUPPORT.md](SUPPORT.md) for where to get help. No SLA is offered at this stage.

## License

Released under the [Apache License 2.0](LICENSE).
