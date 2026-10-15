"""Conversation pipeline orchestration: safety, content, generation, filter.

Safety decides the route, content grounds the reply, generation speaks, and
the Layer 5 output filter approves what the model produced before delivery.
The route is decided entirely by the deterministic input safety layer before
any model call. Exactly one layer can speak: scripted responses on the bypass/review routes,
the model's (filter-approved) reply on the generated route, and the scripted
fallback when the filter blocks it.
"""

from dataclasses import dataclass
from enum import Enum

from reframe.content.library import ContentLibrary
from reframe.content.retrieval import retrieve
from reframe.generation.generator import ConstrainedGenerator
from reframe.pipeline.messages import BOUNDARY_RESPONSE, CRISIS_RESPONSE, FILTER_FALLBACK
from reframe.pipeline.output_filter import filter_output
from reframe.safety.classifier import classify_input
from reframe.safety.escalation import EscalationAction, escalation_decision
from reframe.safety.resources import CrisisResource


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class Route(str, Enum):  # noqa: UP042
    """Which layer produced the reply the user receives for one turn."""

    CRISIS_BYPASS = "crisis_bypass"
    HUMAN_REVIEW = "human_review"
    GENERATED = "generated"
    FILTERED_FALLBACK = "filtered_fallback"


@dataclass(frozen=True)
class PipelineOutcome:
    """Immutable result of one turn: reply, route, grounding, and filter record."""

    reply: str
    route: Route
    module_ids: tuple[str, ...]
    violations: tuple[str, ...]
    resources: tuple[CrisisResource, ...]


class ConversationPipeline:
    """Routes one user turn through safety, retrieval, generation, and filtering."""

    def __init__(self, generator: ConstrainedGenerator, library: ContentLibrary) -> None:
        self._generator = generator
        self._library = library

    def handle(self, user_message: str) -> PipelineOutcome:
        """Produce the safe reply for ``user_message`` on exactly one route.

        1. Classify the input and escalate (fail-closed table lookup).
        2. ``HARD_BYPASS`` → scripted crisis reply + default resources;
           the generator is never called.
        3. ``HUMAN_REVIEW`` → scripted boundary reply, no resources;
           the generator is never called.
        4. ``PROCEED`` → retrieve grounded modules, generate once, then run the
           output filter: a passing reply is served as-is; a blocked reply is
           replaced by the scripted fallback with its violations recorded.

        Args:
            user_message: Raw user text for this turn.

        Returns:
            The immutable outcome for the detected route.

        Raises:
            TypeError: If ``user_message`` is not a ``str``.
            ValueError: If ``user_message`` is empty or whitespace-only.
        """
        verdict = classify_input(user_message)
        decision = escalation_decision(verdict)

        if decision.action is EscalationAction.HARD_BYPASS:
            return PipelineOutcome(
                reply=CRISIS_RESPONSE.text,
                route=Route.CRISIS_BYPASS,
                module_ids=(),
                violations=(),
                resources=CRISIS_RESPONSE.resources,
            )

        if decision.action is EscalationAction.HUMAN_REVIEW:
            return PipelineOutcome(
                reply=BOUNDARY_RESPONSE.text,
                route=Route.HUMAN_REVIEW,
                module_ids=(),
                violations=(),
                resources=(),
            )

        retrieval = retrieve(user_message, self._library)
        result = self._generator.respond(user_message, retrieval.modules)
        filtered = filter_output(result.text)

        if filtered.passed:
            return PipelineOutcome(
                reply=result.text,
                route=Route.GENERATED,
                module_ids=result.module_ids,
                violations=(),
                resources=(),
            )
        return PipelineOutcome(
            reply=FILTER_FALLBACK.text,
            route=Route.FILTERED_FALLBACK,
            module_ids=result.module_ids,
            violations=filtered.violations,
            resources=(),
        )
