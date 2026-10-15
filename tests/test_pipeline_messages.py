"""Tests for ``reframe.pipeline.messages`` — the scripted, non-generative catalog.

Every scripted response must be warm, wellness-framed plain English that is
non-empty, substantive (>= 12 words), and free of diagnosis / treatment
vocabulary. Only the crisis response carries crisis resources.
"""

import re
from dataclasses import FrozenInstanceError

import pytest

from reframe.pipeline.messages import (
    BOUNDARY_RESPONSE,
    CRISIS_RESPONSE,
    FILTER_FALLBACK,
    SCRIPTED,
    ScriptedResponse,
)
from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES, CrisisResource

EXPECTED_IDS = ("crisis_response_v1", "boundary_response_v1", "filter_fallback_v1")

# Substrings that must never appear in any scripted text (case-insensitive).
BANNED_PATTERN = re.compile(r"treat|therapy|diagnos|prescrib|medication", re.IGNORECASE)

ALL_RESPONSES = (CRISIS_RESPONSE, BOUNDARY_RESPONSE, FILTER_FALLBACK)


def test_scripted_maps_exactly_the_three_message_ids() -> None:
    assert set(SCRIPTED) == set(EXPECTED_IDS)
    assert len(SCRIPTED) == 3


def test_each_message_id_maps_to_its_response() -> None:
    assert SCRIPTED["crisis_response_v1"] is CRISIS_RESPONSE
    assert SCRIPTED["boundary_response_v1"] is BOUNDARY_RESPONSE
    assert SCRIPTED["filter_fallback_v1"] is FILTER_FALLBACK


def test_message_ids_match_their_constants() -> None:
    assert CRISIS_RESPONSE.message_id == "crisis_response_v1"
    assert BOUNDARY_RESPONSE.message_id == "boundary_response_v1"
    assert FILTER_FALLBACK.message_id == "filter_fallback_v1"


@pytest.mark.parametrize("response", ALL_RESPONSES, ids=EXPECTED_IDS)
def test_every_scripted_text_is_non_empty_and_at_least_twelve_words(
    response: ScriptedResponse,
) -> None:
    assert response.text.strip()
    assert len(response.text.split()) >= 12


@pytest.mark.parametrize("response", ALL_RESPONSES, ids=EXPECTED_IDS)
def test_no_scripted_text_contains_banned_claim_words(response: ScriptedResponse) -> None:
    assert BANNED_PATTERN.search(response.text) is None


# ---------------------------------------------------------------------------
# Crisis response: honesty about limits + real resources + emergency guidance
# ---------------------------------------------------------------------------


def test_crisis_text_mentions_emergency() -> None:
    assert "emergency" in CRISIS_RESPONSE.text.lower()


def test_crisis_resources_are_the_default_crisis_resources() -> None:
    assert CRISIS_RESPONSE.resources == DEFAULT_CRISIS_RESOURCES


def test_at_least_one_resource_name_appears_in_the_crisis_text() -> None:
    assert any(resource.name in CRISIS_RESPONSE.text for resource in CRISIS_RESPONSE.resources)


def test_crisis_text_says_this_companion_cannot_help_with_crisis() -> None:
    lowered = CRISIS_RESPONSE.text.lower()
    assert "can't help" in lowered or "cannot help" in lowered


# ---------------------------------------------------------------------------
# Boundary / fallback framing and resources
# ---------------------------------------------------------------------------


def test_boundary_response_states_the_boundary_and_points_to_professionals() -> None:
    lowered = BOUNDARY_RESPONSE.text.lower()
    assert "qualified professional" in lowered
    assert BOUNDARY_RESPONSE.resources == ()


def test_boundary_response_keeps_dignity_with_warm_acknowledgement() -> None:
    assert any(
        opener in BOUNDARY_RESPONSE.text.lower() for opener in ("i hear", "i'm glad", "i hear how")
    )


def test_filter_fallback_offers_an_exercise_or_to_listen() -> None:
    lowered = FILTER_FALLBACK.text.lower()
    assert "i want to be careful with my words here" in lowered
    assert "exercise" in lowered
    assert "listen" in lowered
    assert FILTER_FALLBACK.resources == ()


def test_only_the_crisis_response_carries_resources() -> None:
    with_resources = [r for r in ALL_RESPONSES if r.resources]
    assert with_resources == [CRISIS_RESPONSE]


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_scripted_response_is_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        CRISIS_RESPONSE.message_id = "mutated"  # type: ignore[misc]


def test_crisis_resources_are_frozen_crisis_resource_values() -> None:
    assert all(isinstance(resource, CrisisResource) for resource in CRISIS_RESPONSE.resources)
