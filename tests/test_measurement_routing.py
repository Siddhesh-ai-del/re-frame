"""Tests for ``reframe.measurement.routing`` — check-in flags onto the
existing escalation vocabulary.

Strict TDD: written BEFORE ``reframe/measurement/routing.py`` exists; the
first run must fail with ``ModuleNotFoundError`` (RED).

ESCALATE reuses the pipeline's scripted crisis path (``crisis_response_v1``
— the pipeline's SCRIPTED catalog remains the single source for that text).
"""

import re
from dataclasses import FrozenInstanceError

import pytest

from reframe.measurement.flags import CheckInFlag
from reframe.measurement.routing import (
    CHECKIN_CONCERN_TEXT,
    CheckInRouting,
    route_for_checkin,
)
from reframe.pipeline.messages import SCRIPTED
from reframe.safety import EscalationAction


def test_escalate_routes_to_hard_bypass_with_scripted_crisis_path() -> None:
    routing = route_for_checkin((CheckInFlag.ESCALATE,))
    assert routing.action is EscalationAction.HARD_BYPASS
    assert routing.message_id == "crisis_response_v1"
    # The pipeline's SCRIPTED catalog is the single source for crisis wording:
    # the routed id must resolve there.
    assert routing.message_id in SCRIPTED


def test_escalate_takes_precedence_over_other_flags() -> None:
    routing = route_for_checkin(
        (CheckInFlag.EARLY_WORSENSING, CheckInFlag.ESCALATE, CheckInFlag.REFERRAL_PROMPT)
    )
    assert routing.action is EscalationAction.HARD_BYPASS
    assert routing.message_id == "crisis_response_v1"


def test_early_worsening_alone_routes_to_human_review() -> None:
    routing = route_for_checkin((CheckInFlag.EARLY_WORSENSING,))
    assert routing.action is EscalationAction.HUMAN_REVIEW
    assert routing.message_id == "checkin_concern_v1"


def test_referral_prompt_alone_routes_to_human_review() -> None:
    routing = route_for_checkin((CheckInFlag.REFERRAL_PROMPT,))
    assert routing.action is EscalationAction.HUMAN_REVIEW
    assert routing.message_id == "checkin_concern_v1"


def test_no_flags_proceeds_without_message() -> None:
    routing = route_for_checkin(())
    assert routing.action is EscalationAction.PROCEED
    assert routing.message_id is None


def test_concern_text_is_at_least_fifteen_words() -> None:
    assert len(CHECKIN_CONCERN_TEXT.split()) >= 15


def test_concern_text_avoids_banned_vocabulary() -> None:
    lowered = CHECKIN_CONCERN_TEXT.lower()
    banned = ("treat", "therapy", "therapist", "diagnos", "prescrib", "medication")
    for word in banned:
        assert word not in lowered, f"banned vocabulary {word!r} found in concern text"


def test_concern_text_encourages_professional_support_and_frames_reaching_out_as_strength() -> None:
    lowered = CHECKIN_CONCERN_TEXT.lower()
    assert "professional" in lowered
    assert re.search(r"\bstrength\b", lowered) is not None


def test_routing_is_frozen() -> None:
    routing = route_for_checkin(())
    assert isinstance(routing, CheckInRouting)
    with pytest.raises(FrozenInstanceError):
        routing.message_id = "something_else"  # type: ignore[misc]
