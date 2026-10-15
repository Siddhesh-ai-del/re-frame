"""Tests for ``reframe.pipeline.pipeline`` — full conversation orchestration.

Safety decides (input classifier + escalation table), content grounds
(deterministic retrieval), generation speaks (real ``ConstrainedGenerator``
wrapping a recording fake client), and the output filter approves. The
generator must never be called on the bypass or review routes.
"""

from dataclasses import FrozenInstanceError

import pytest

from reframe.content import ContentLibrary, default_library, retrieve
from reframe.generation import ConstrainedGenerator, GenerationRequest, GenerationResponse
from reframe.pipeline.messages import BOUNDARY_RESPONSE, CRISIS_RESPONSE, FILTER_FALLBACK
from reframe.pipeline.pipeline import ConversationPipeline, PipelineOutcome, Route
from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES

WELL_BEHAVED_REPLY = (
    "That loop sounds exhausting. Would you like to try one short grounding exercise "
    "from today's set, or would you rather tell me more about what keeps looping?"
)
MISBEHAVING_REPLY = "You have depression and you should take medication."


class FakeClient:
    """Recording LLM client: returns scripted replies, captures every request."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self.requests: list[GenerationRequest] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def complete(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        index = self.call_count - 1
        return GenerationResponse(text=self._replies[index], model="fake-model")


def make_pipeline(replies: list[str]) -> tuple[ConversationPipeline, FakeClient]:
    client = FakeClient(replies)
    generator = ConstrainedGenerator(client)
    return ConversationPipeline(generator=generator, library=default_library()), client


# ---------------------------------------------------------------------------
# Route 1: crisis hard bypass — scripted only, generation never runs
# ---------------------------------------------------------------------------


def test_crisis_input_hard_bypasses_with_default_resources_and_no_generation() -> None:
    pipeline, client = make_pipeline([WELL_BEHAVED_REPLY])
    outcome = pipeline.handle("I want to die")

    assert outcome.route is Route.CRISIS_BYPASS
    assert outcome.reply == CRISIS_RESPONSE.text
    assert outcome.resources == DEFAULT_CRISIS_RESOURCES
    assert outcome.module_ids == ()
    assert outcome.violations == ()
    assert client.call_count == 0


# ---------------------------------------------------------------------------
# Route 2: human review (trauma / diagnosis-seeking) — scripted, no generation
# ---------------------------------------------------------------------------


def test_trauma_input_routes_to_human_review_without_generation() -> None:
    pipeline, client = make_pipeline([WELL_BEHAVED_REPLY])
    outcome = pipeline.handle("help me process my trauma")

    assert outcome.route is Route.HUMAN_REVIEW
    assert outcome.reply == BOUNDARY_RESPONSE.text
    assert outcome.resources == ()
    assert outcome.module_ids == ()
    assert client.call_count == 0


def test_diagnosis_seeking_input_routes_to_human_review_without_generation() -> None:
    pipeline, client = make_pipeline([WELL_BEHAVED_REPLY])
    outcome = pipeline.handle("do I have depression")

    assert outcome.route is Route.HUMAN_REVIEW
    assert outcome.reply == BOUNDARY_RESPONSE.text
    assert outcome.resources == ()
    assert client.call_count == 0


# ---------------------------------------------------------------------------
# Route 3: generated reply passes the output filter
# ---------------------------------------------------------------------------


def test_rumination_input_generates_with_retrieved_modules_and_context() -> None:
    pipeline, client = make_pipeline([WELL_BEHAVED_REPLY])
    outcome = pipeline.handle("I can't stop thinking about work")

    assert outcome.route is Route.GENERATED
    assert outcome.reply == WELL_BEHAVED_REPLY
    assert outcome.module_ids
    assert outcome.violations == ()
    assert outcome.resources == ()
    assert client.call_count == 1

    # The request context carried the steps of every served module.
    library: ContentLibrary = default_library()
    context = client.requests[0].context
    assert context
    for module_id in outcome.module_ids:
        module = library.by_id(module_id)
        for step in module.steps:
            assert step in context


def test_generated_route_passes_the_same_modules_retrieval_selects() -> None:
    pipeline, client = make_pipeline([WELL_BEHAVED_REPLY])
    outcome = pipeline.handle("I can't stop thinking about work")
    retrieval = retrieve("I can't stop thinking about work", default_library())
    assert outcome.module_ids == tuple(module.id for module in retrieval.modules)


def test_benign_input_with_no_category_match_generates_without_modules() -> None:
    pipeline, client = make_pipeline([WELL_BEHAVED_REPLY])
    outcome = pipeline.handle("good morning")

    assert outcome.route is Route.GENERATED
    assert outcome.module_ids == ()
    assert outcome.reply == WELL_BEHAVED_REPLY
    assert client.call_count == 1
    assert client.requests[0].context == ""


# ---------------------------------------------------------------------------
# Route 4: model output violates the filter — scripted fallback, violations kept
# ---------------------------------------------------------------------------


def test_violating_model_output_falls_back_with_violations() -> None:
    pipeline, client = make_pipeline([MISBEHAVING_REPLY])
    outcome = pipeline.handle("I can't stop thinking about work")

    assert outcome.route is Route.FILTERED_FALLBACK
    assert outcome.reply == FILTER_FALLBACK.text
    assert outcome.violations
    assert outcome.resources == ()
    assert outcome.module_ids  # modules still reported for observability
    assert client.call_count == 1


# ---------------------------------------------------------------------------
# Boundary propagation, immutability, public surface
# ---------------------------------------------------------------------------


def test_empty_message_raises_value_error() -> None:
    pipeline, _client = make_pipeline([WELL_BEHAVED_REPLY])
    with pytest.raises(ValueError):
        pipeline.handle("   ")


def test_non_str_message_raises_type_error() -> None:
    pipeline, _client = make_pipeline([WELL_BEHAVED_REPLY])
    with pytest.raises(TypeError):
        pipeline.handle(None)  # type: ignore[arg-type]


def test_pipeline_outcome_is_frozen() -> None:
    outcome = ConversationPipeline(
        generator=ConstrainedGenerator(FakeClient([WELL_BEHAVED_REPLY])),
        library=default_library(),
    ).handle("good morning")
    with pytest.raises(FrozenInstanceError):
        outcome.reply = "mutated"  # type: ignore[misc]


def test_route_is_a_string_enum_with_the_four_routes() -> None:
    assert set(Route) == {
        Route.CRISIS_BYPASS,
        Route.HUMAN_REVIEW,
        Route.GENERATED,
        Route.FILTERED_FALLBACK,
    }
    assert Route.CRISIS_BYPASS.value == "crisis_bypass"


def test_pipeline_package_exports_public_surface() -> None:
    import reframe.pipeline as package

    assert package.ConversationPipeline is ConversationPipeline
    assert package.PipelineOutcome is PipelineOutcome
    assert package.Route is Route
