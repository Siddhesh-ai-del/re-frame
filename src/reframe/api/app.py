"""FastAPI service core for RE:FRAME — a non-diagnostic wellness companion.

This v1 service is designed to run behind a reverse proxy or on localhost, so
it intentionally adds no auth, CORS, or rate limiting (those are Stage 6/7
scope). The API never presents itself as care and never leaks internals: every
error body is a generic, wellness-framed message with no stack traces, provider
details, or model names. Safety routing (crisis bypass, human review) is
delegated unchanged to the deterministic pipeline below, so its semantics
survive the HTTP layer intact.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import reframe
from reframe.api.schemas import (
    ChatRequest,
    ChatResponse,
    ExerciseListOut,
    ExerciseOut,
    HealthResponse,
    ResourceOut,
    ResourcesOut,
)
from reframe.content import default_library
from reframe.content.schema import ExerciseModule
from reframe.generation import GenerationError
from reframe.pipeline import ConversationPipeline, PipelineOutcome
from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES

DESCRIPTION = (
    "RE:FRAME is a wellness companion API for emotional distress self-management, offering "
    "grounded, evidence-informed exercise support behind a layered safety system."
)
CHAT_UNAVAILABLE_DETAIL = "The assistant is temporarily unavailable. Please try again shortly."
CHAT_UNPROCESSABLE_DETAIL = "The message could not be processed."
INTERNAL_ERROR_DETAIL = "Internal server error."


def _to_chat_response(outcome: PipelineOutcome) -> ChatResponse:
    """Map a frozen ``PipelineOutcome`` onto the wire ``ChatResponse``."""
    return ChatResponse(
        reply=outcome.reply,
        route=outcome.route.value,
        module_ids=list(outcome.module_ids),
        violations=list(outcome.violations),
        resources=[
            ResourceOut(name=resource.name, url=resource.url) for resource in outcome.resources
        ],
    )


def _to_exercise_out(module: ExerciseModule) -> ExerciseOut:
    """Map a library module onto the wire ``ExerciseOut``.

    ``safety_class`` is deliberately dropped — it is an internal routing
    detail (self-help vs referral-only), never part of the public contract.
    """
    return ExerciseOut(
        id=module.id,
        title=module.title,
        summary=module.summary,
        category=module.category.value,
        tier=module.tier.value,
        steps=list(module.steps),
        sources=list(module.sources),
        contraindications=list(module.contraindications),
        early_worsening_notice=module.early_worsening_notice,
    )


def create_app(pipeline: ConversationPipeline) -> FastAPI:
    """Build the FastAPI app around ``pipeline``.

    Error mapping is fail-closed and leaks nothing: a ``GenerationError`` from
    the pipeline becomes 503, a ``ValueError`` (e.g. a blank message that passed
    pydantic) becomes 422, and any other exception becomes a generic 500.
    """
    app = FastAPI(title="RE:FRAME API", description=DESCRIPTION)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=reframe.__version__)

    @app.get("/resources", response_model=ResourcesOut)
    def resources() -> ResourcesOut:
        """Serve the standing crisis resources.

        Deliberately independent of ``pipeline`` (and therefore of the LLM):
        these links must stay reachable even when generation is down — the UI
        shows them on the 503 path, so this endpoint can never fail the same
        way chat does.
        """
        return ResourcesOut(
            resources=[
                ResourceOut(name=resource.name, url=resource.url)
                for resource in DEFAULT_CRISIS_RESOURCES
            ]
        )

    @app.get("/content/exercises", response_model=ExerciseListOut)
    def content_exercises() -> ExerciseListOut:
        """Serve the full exercise library (stage 6c).

        The path is ``/content/exercises`` (not ``/exercises``) precisely
        because the SPA owns GET ``/exercises`` — a same-path API route could
        not be disambiguated by method the way ``POST /chat`` is. Served from
        the packaged, cached library; no LLM involved, so it stays reachable
        on the 503 path.
        """
        return ExerciseListOut(
            exercises=[_to_exercise_out(module) for module in default_library().modules]
        )

    @app.post("/chat", response_model=ChatResponse)
    def chat(chat_request: ChatRequest) -> ChatResponse:
        try:
            outcome = pipeline.handle(chat_request.message)
        except GenerationError:
            raise HTTPException(status_code=503, detail=CHAT_UNAVAILABLE_DETAIL) from None
        except ValueError:
            raise HTTPException(status_code=422, detail=CHAT_UNPROCESSABLE_DETAIL) from None
        return _to_chat_response(outcome)

    @app.exception_handler(Exception)
    def unhandled(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR_DETAIL})

    return app
