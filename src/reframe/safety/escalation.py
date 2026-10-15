"""Deterministic escalation policy: a verdict in, a routing decision out.

The policy is a fixed table — :func:`escalation_decision` is a pure function
of the verdict. The generative model never participates in this decision, and
``HIGH_RISK`` always hard-bypasses to canned crisis handling (fail-closed).
"""

from dataclasses import dataclass
from enum import Enum

from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES, CrisisResource
from reframe.safety.types import SafetyVerdict, VerdictLevel


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class EscalationAction(str, Enum):  # noqa: UP042
    """What the pipeline does with an input, decided by table lookup only."""

    HARD_BYPASS = "hard_bypass"
    HUMAN_REVIEW = "human_review"
    PROCEED = "proceed"


@dataclass(frozen=True)
class EscalationDecision:
    """Immutable routing decision for one classified input."""

    action: EscalationAction
    message_id: str | None
    resources: tuple[CrisisResource, ...]


def escalation_decision(verdict: SafetyVerdict) -> EscalationDecision:
    """Map ``verdict`` onto the fixed policy table.

    +--------------+------------------+----------------------+-----------+
    | Level        | Action           | Message id           | Resources |
    +==============+==================+======================+===========+
    | ``HIGH_RISK``   | ``HARD_BYPASS``   | ``crisis_response_v1``  | default   |
    | ``REVIEW``      | ``HUMAN_REVIEW``  | ``boundary_response_v1``| none      |
    | ``NORMAL``      | ``PROCEED``       | ``None``                | none      |
    +--------------+------------------+----------------------+-----------+

    Pure function of the verdict only: no I/O, environment, or randomness.
    """
    if verdict.level is VerdictLevel.HIGH_RISK:
        return EscalationDecision(
            action=EscalationAction.HARD_BYPASS,
            message_id="crisis_response_v1",
            resources=DEFAULT_CRISIS_RESOURCES,
        )
    if verdict.level is VerdictLevel.REVIEW:
        return EscalationDecision(
            action=EscalationAction.HUMAN_REVIEW,
            message_id="boundary_response_v1",
            resources=(),
        )
    return EscalationDecision(
        action=EscalationAction.PROCEED,
        message_id=None,
        resources=(),
    )
