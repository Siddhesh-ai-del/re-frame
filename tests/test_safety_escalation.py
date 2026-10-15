"""Tests for ``reframe.safety.escalation`` — the deterministic escalation policy table."""

from dataclasses import FrozenInstanceError

import pytest

from reframe.safety.escalation import (
    EscalationAction,
    EscalationDecision,
    escalation_decision,
)
from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES, CrisisResource
from reframe.safety.types import SafetyVerdict, SignalType, VerdictLevel

HIGH_RISK_VERDICT = SafetyVerdict(level=VerdictLevel.HIGH_RISK, signals=(SignalType.CRISIS,))
REVIEW_VERDICT = SafetyVerdict(level=VerdictLevel.REVIEW, signals=(SignalType.TRAUMA_PROCESSING,))
NORMAL_VERDICT = SafetyVerdict(level=VerdictLevel.NORMAL, signals=())


# ---------------------------------------------------------------------------
# Crisis resources (exact, real, well-known set)
# ---------------------------------------------------------------------------


def test_default_crisis_resources_are_the_real_well_known_set() -> None:
    assert (
        CrisisResource(
            name="Find A Helpline (IASP global directory)",
            url="https://findahelpline.com",
        ),
        CrisisResource(
            name="988 Suicide & Crisis Lifeline (US)",
            url="https://988lifeline.org",
        ),
        CrisisResource(
            name="If you are in immediate danger, contact your local emergency services",
            url=None,
        ),
    ) == DEFAULT_CRISIS_RESOURCES


def test_default_resources_include_exactly_one_no_url_entry() -> None:
    without_url = [r for r in DEFAULT_CRISIS_RESOURCES if r.url is None]
    assert len(without_url) == 1
    assert "emergency services" in without_url[0].name


# ---------------------------------------------------------------------------
# Policy table: all three rows, exactly
# ---------------------------------------------------------------------------


def test_high_risk_maps_to_hard_bypass_with_crisis_message_and_resources() -> None:
    decision = escalation_decision(HIGH_RISK_VERDICT)
    assert decision == EscalationDecision(
        action=EscalationAction.HARD_BYPASS,
        message_id="crisis_response_v1",
        resources=DEFAULT_CRISIS_RESOURCES,
    )


def test_review_maps_to_human_review_with_boundary_message_and_no_resources() -> None:
    decision = escalation_decision(REVIEW_VERDICT)
    assert decision == EscalationDecision(
        action=EscalationAction.HUMAN_REVIEW,
        message_id="boundary_response_v1",
        resources=(),
    )


def test_normal_maps_to_proceed_with_no_message_and_no_resources() -> None:
    decision = escalation_decision(NORMAL_VERDICT)
    assert decision == EscalationDecision(
        action=EscalationAction.PROCEED,
        message_id=None,
        resources=(),
    )


def test_hard_bypass_resources_are_exactly_the_default_set() -> None:
    decision = escalation_decision(HIGH_RISK_VERDICT)
    assert decision.resources == DEFAULT_CRISIS_RESOURCES
    assert all(isinstance(r, CrisisResource) for r in decision.resources)
    assert len(decision.resources) == len(DEFAULT_CRISIS_RESOURCES)


# ---------------------------------------------------------------------------
# Purity / determinism
# ---------------------------------------------------------------------------


def test_two_calls_with_the_same_verdict_return_equal_decisions() -> None:
    for verdict in (HIGH_RISK_VERDICT, REVIEW_VERDICT, NORMAL_VERDICT):
        assert escalation_decision(verdict) == escalation_decision(verdict)


def test_decisions_are_independent_instances_not_shared_state() -> None:
    first = escalation_decision(HIGH_RISK_VERDICT)
    second = escalation_decision(HIGH_RISK_VERDICT)
    assert first is not second
    assert first == second


def test_decision_is_frozen() -> None:
    decision = escalation_decision(HIGH_RISK_VERDICT)
    with pytest.raises(FrozenInstanceError):
        decision.action = EscalationAction.PROCEED  # type: ignore[misc]
