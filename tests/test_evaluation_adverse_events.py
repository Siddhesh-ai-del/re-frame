"""Tests for ``reframe.evaluation.adverse_events`` — AE taxonomy and record.

Strict TDD: written BEFORE ``reframe/evaluation/`` exists; the first run must
fail with ``ModuleNotFoundError`` (RED).

The six types are RE:FRAME PRE-SPECIFIED design definitions (no validated
published GenAI adverse-event definitions exist — Olisaeloka et al. 2026).
:class:`AdverseEvent` is a fail-closed frozen record: no message content ever
(D1) — ``reference`` is a locator string only — and the 48-hour follow-up
marker (D3) is a property of ``serious`` + ``detected_at``.
"""

import datetime
import uuid
from dataclasses import FrozenInstanceError

import pytest

from reframe.evaluation.adverse_events import (
    AE_DEFINITIONS,
    SERIOUS_FOLLOWUP_HOURS,
    AdverseEvent,
    AEDefinition,
    AESource,
    AEType,
)

UTC = datetime.UTC
NOW = datetime.datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


class _OffsetlessTz(datetime.tzinfo):
    """A tzinfo whose ``utcoffset`` is None — an aware-looking, naive-in-fact value."""

    def utcoffset(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        return None

    def dst(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        return None


def _event(
    *,
    id: str = "evt-0001",
    type: AEType = AEType.TRANSIENT_EARLY_WORSENSING,
    source: AESource = AESource.AUTOMATIC,
    detected_at: datetime.datetime = NOW,
    serious: bool = False,
    followup_completed: bool = False,
    reference: str | None = None,
) -> AdverseEvent:
    """A schema-valid :class:`AdverseEvent` for direct construction."""
    return AdverseEvent(
        id=id,
        type=type,
        source=source,
        detected_at=detected_at,
        serious=serious,
        followup_completed=followup_completed,
        reference=reference,
    )


# ---------------------------------------------------------------------------
# Taxonomy: exactly six pre-specified definitions, read-only, in enum order
# ---------------------------------------------------------------------------


def test_taxonomy_has_exactly_the_six_pre_specified_types() -> None:
    assert len(AEType) == 6
    assert set(AE_DEFINITIONS) == {member.value for member in AEType}


def test_taxonomy_keys_match_enum_declaration_order() -> None:
    assert list(AE_DEFINITIONS) == [member.value for member in AEType]


def test_every_definition_carries_nonempty_text_citation_rationale_and_bool_default() -> None:
    for member in AEType:
        definition = AE_DEFINITIONS[member.value]
        assert isinstance(definition, AEDefinition)
        assert definition.type is member
        assert definition.definition.strip()
        assert definition.citation.strip()
        assert definition.seriousness_rationale.strip()
        assert isinstance(definition.default_serious, bool)


def test_pre_specified_seriousness_matches_the_design_decision() -> None:
    # D2: escalation-pathway failures are self-evidently serious; content
    # defects and the early-worsening monitoring signal are review-judged.
    assert AE_DEFINITIONS["crisis_response_failure"].default_serious is True
    assert AE_DEFINITIONS["inappropriate_or_delayed_escalation"].default_serious is True
    for name in (
        "hallucinated_clinical_claim",
        "boundary_violation_diagnosis",
        "sycophancy_episode",
        "transient_early_worsening",
    ):
        assert AE_DEFINITIONS[name].default_serious is False


def test_ae_definitions_mapping_is_read_only() -> None:
    with pytest.raises(TypeError):
        AE_DEFINITIONS["injected_type"] = object()  # type: ignore[index]


# ---------------------------------------------------------------------------
# AdverseEvent.create: uuid id, UTC now, taxonomy seriousness, D1 reference
# ---------------------------------------------------------------------------


def test_create_generates_a_uuid_id_and_a_utc_detection_time() -> None:
    before = datetime.datetime.now(UTC)
    event = AdverseEvent.create(AEType.SYCOPHANCY_EPISODE, source=AESource.REVIEW)
    after = datetime.datetime.now(UTC)

    uuid.UUID(event.id)  # a valid uuid hex string, not an arbitrary id
    assert len(event.id) == 32
    assert event.detected_at.utcoffset() == datetime.timedelta(0)
    assert before <= event.detected_at <= after


def test_create_defaults_seriousness_from_the_taxonomy_for_every_type() -> None:
    for member in AEType:
        event = AdverseEvent.create(member, source=AESource.AUTOMATIC)
        assert event.serious is AE_DEFINITIONS[member.value].default_serious


def test_explicit_serious_override_wins_over_the_taxonomy_default() -> None:
    escalated = AdverseEvent.create(AEType.SYCOPHANCY_EPISODE, source=AESource.REVIEW, serious=True)
    downgraded = AdverseEvent.create(
        AEType.CRISIS_RESPONSE_FAILURE, source=AESource.REVIEW, serious=False
    )
    assert escalated.serious is True
    assert downgraded.serious is False


def test_create_never_starts_with_followup_completed() -> None:
    event = AdverseEvent.create(AEType.CRISIS_RESPONSE_FAILURE, source=AESource.AUDIT)
    assert event.followup_completed is False


def test_reference_is_stripped_to_a_bare_locator() -> None:
    event = AdverseEvent.create(
        AEType.SYCOPHANCY_EPISODE,
        source=AESource.REVIEW,
        reference="  session 3 turn 14  ",
    )
    assert event.reference == "session 3 turn 14"


def test_reference_none_is_accepted() -> None:
    event = AdverseEvent.create(AEType.SYCOPHANCY_EPISODE, source=AESource.REVIEW, reference=None)
    assert event.reference is None


def test_whitespace_only_reference_is_rejected() -> None:
    with pytest.raises(ValueError):
        AdverseEvent.create(AEType.SYCOPHANCY_EPISODE, source=AESource.REVIEW, reference="   ")


def test_a_201_char_reference_is_rejected() -> None:
    with pytest.raises(ValueError):
        AdverseEvent.create(AEType.SYCOPHANCY_EPISODE, source=AESource.REVIEW, reference="x" * 201)


def test_a_200_char_reference_is_accepted() -> None:
    event = AdverseEvent.create(
        AEType.SYCOPHANCY_EPISODE, source=AESource.REVIEW, reference="x" * 200
    )
    assert event.reference == "x" * 200


def test_non_string_reference_is_rejected_with_a_value_error() -> None:
    with pytest.raises(ValueError):
        AdverseEvent(
            id="evt-0002",
            type=AEType.SYCOPHANCY_EPISODE,
            source=AESource.REVIEW,
            detected_at=NOW,
            serious=False,
            followup_completed=False,
            reference=42,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Fail-closed __post_init__
# ---------------------------------------------------------------------------


def test_naive_detected_at_is_rejected() -> None:
    with pytest.raises(ValueError):
        AdverseEvent.create(
            AEType.SYCOPHANCY_EPISODE,
            source=AESource.REVIEW,
            detected_at=datetime.datetime(2026, 10, 26, 12, 0),
        )


def test_offsetless_tzinfo_detected_at_is_rejected() -> None:
    with pytest.raises(ValueError):
        AdverseEvent.create(
            AEType.SYCOPHANCY_EPISODE,
            source=AESource.REVIEW,
            detected_at=datetime.datetime(2026, 10, 26, 12, 0, tzinfo=_OffsetlessTz()),
        )


def test_non_bool_serious_is_rejected_even_when_int_like() -> None:
    with pytest.raises(ValueError):
        AdverseEvent.create(AEType.SYCOPHANCY_EPISODE, source=AESource.REVIEW, serious=1)


def test_non_bool_followup_completed_is_rejected_even_when_int_like() -> None:
    with pytest.raises(ValueError):
        _event(followup_completed=1)  # type: ignore[arg-type]


def test_bare_string_type_is_rejected_not_coerced() -> None:
    with pytest.raises(ValueError):
        AdverseEvent.create("sycophancy_episode", source=AESource.REVIEW)  # type: ignore[arg-type]


def test_direct_construction_with_a_bare_string_type_is_rejected() -> None:
    with pytest.raises(ValueError):
        AdverseEvent(
            id="evt-0003",
            type="sycophancy_episode",  # type: ignore[arg-type]
            source=AESource.REVIEW,
            detected_at=NOW,
            serious=False,
            followup_completed=False,
            reference=None,
        )


def test_bare_string_source_is_rejected_not_coerced() -> None:
    with pytest.raises(ValueError):
        _event(source="automatic")  # type: ignore[arg-type]


def test_empty_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        _event(id="")


def test_direct_construction_accepts_a_valid_record() -> None:
    event = _event(reference="check-in phq9 2026-10-08 total=16")
    assert event.id == "evt-0001"
    assert event.type is AEType.TRANSIENT_EARLY_WORSENSING
    assert event.source is AESource.AUTOMATIC


# ---------------------------------------------------------------------------
# D3: the 48-hour follow-up marker is a property, not a stored column
# ---------------------------------------------------------------------------


def test_serious_followup_is_due_exactly_48_hours_after_detection() -> None:
    assert SERIOUS_FOLLOWUP_HOURS == 48
    event = _event(detected_at=NOW, serious=True)
    assert event.followup_due_at == NOW + datetime.timedelta(hours=48)


def test_non_serious_followup_is_never_due() -> None:
    event = _event(detected_at=NOW, serious=False)
    assert event.followup_due_at is None


# ---------------------------------------------------------------------------
# Immutability: replacements are new instances, the original never changes
# ---------------------------------------------------------------------------


def test_with_followup_completed_returns_a_new_instance_original_untouched() -> None:
    original = _event(id="evt-0007", serious=True)

    replaced = original.with_followup_completed()

    assert replaced is not original
    assert replaced.id == original.id
    assert replaced.followup_completed is True
    assert original.followup_completed is False


def test_with_followup_completed_can_be_set_back_to_false() -> None:
    replaced = _event(serious=True).with_followup_completed(False)
    assert replaced.followup_completed is False


def test_records_are_frozen_against_direct_mutation() -> None:
    event = _event()
    with pytest.raises(FrozenInstanceError):
        event.serious = True
