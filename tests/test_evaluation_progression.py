"""Tests for ``reframe.evaluation.progression`` — pre-specified criteria and banding.

Strict TDD: written BEFORE ``reframe/evaluation/progression.py`` exists; the
first run must fail with ``ModuleNotFoundError`` (RED).

Four pre-specified progression criteria (recruitment, retention, data
completeness, safety-event status) in the research report's order, with the
exact green/amber/red texts and the verified citation strings locked here (E6).
Bands are OPERATIONAL REVIEW STATUSES — never safety or efficacy judgments.
Thresholds are provisional RE:FRAME design defaults pending pilot validation.
The safety band is CLASS-based (E5), first match wins, never rate-based.
"""

import datetime
from dataclasses import FrozenInstanceError

import pytest

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.evaluation.progression import (
    DEFAULT_PROGRESSION_CRITERIA,
    ProgressionCriterion,
    band_from_value,
    safety_band,
)

UTC = datetime.UTC
NOW = datetime.datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def _event(
    ae_type: AEType,
    *,
    detected_at: datetime.datetime = NOW,
    serious: bool | None = None,
    followup_completed: bool = False,
) -> AdverseEvent:
    event = AdverseEvent.create(
        ae_type,
        source=AESource.REVIEW,
        serious=serious,
        detected_at=detected_at,
    )
    return event.with_followup_completed(followup_completed) if followup_completed else event


def _expected_bands() -> dict[str, tuple[str, str, str]]:
    """The exact criterion texts from the stage-7b specification (locked)."""
    return {
        "recruitment": (
            ">= 100% of planned participants enrolled",
            ">= 75% of planned",
            "< 75% of planned",
        ),
        "retention": (
            ">= 70% of window weeks active (>= 1 check-in)",
            ">= 50%",
            "< 50%",
        ),
        "data_completeness": (
            ">= 80% of expected check-ins recorded",
            ">= 60%",
            "< 60%",
        ),
        "safety_event_rate": (
            "no escalation-pathway failures, no overdue serious follow-ups, "
            "only expected monitoring-signal events (or none)",
            "content-class events logged, or any serious event (all serious follow-ups on time)",
            "any crisis-response failure or inappropriate/delayed escalation, or "
            "any serious follow-up overdue past 48 hours",
        ),
    }


# ---------------------------------------------------------------------------
# DEFAULT_PROGRESSION_CRITERIA: order, non-empty fields, exact band texts
# ---------------------------------------------------------------------------


def test_default_criteria_follow_the_research_report_order() -> None:
    assert tuple(DEFAULT_PROGRESSION_CRITERIA) == (
        "recruitment",
        "retention",
        "data_completeness",
        "safety_event_rate",
    )


def test_every_criterion_field_is_non_empty() -> None:
    for criterion in DEFAULT_PROGRESSION_CRITERIA.values():
        assert criterion.key
        assert criterion.label
        assert criterion.green
        assert criterion.amber
        assert criterion.red
        assert criterion.justification
        assert criterion.citation


def test_every_criterion_carries_the_exact_specified_band_texts() -> None:
    for key, (green, amber, red) in _expected_bands().items():
        criterion = DEFAULT_PROGRESSION_CRITERIA[key]
        assert (criterion.green, criterion.amber, criterion.red) == (green, amber, red)


def test_basis_renders_all_three_bands() -> None:
    for criterion in DEFAULT_PROGRESSION_CRITERIA.values():
        assert (
            criterion.basis
            == f"green: {criterion.green}; amber: {criterion.amber}; red: {criterion.red}"
        )
        assert "green:" in criterion.basis
        assert "amber:" in criterion.basis
        assert "red:" in criterion.basis


def test_the_default_criteria_mapping_is_read_only() -> None:
    with pytest.raises(TypeError):
        DEFAULT_PROGRESSION_CRITERIA["banana"] = ProgressionCriterion(  # type: ignore[index]
            key="banana",
            label="banana",
            green="x",
            amber="x",
            red="x",
            justification="x",
            citation="x",
        )


def test_criterion_is_frozen() -> None:
    criterion = DEFAULT_PROGRESSION_CRITERIA["retention"]
    with pytest.raises(FrozenInstanceError):
        criterion.label = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Citation/justification honesty: provisional labeling, verified strings (E6)
# ---------------------------------------------------------------------------


def test_recruitment_citation_carries_the_verified_anchors() -> None:
    citation = DEFAULT_PROGRESSION_CRITERIA["recruitment"].citation
    assert "Determining sample size for pilot trials: a tutorial" in citation
    assert "DOI 10.1002/pst.185" in citation
    assert "DOI 10.1186/s40814-025-01675-9" in citation
    justification = DEFAULT_PROGRESSION_CRITERIA["recruitment"].justification
    assert "12-per-arm floor" in justification
    assert "Flat rules of thumb" in justification


def test_retention_citation_carries_the_verified_anchors_and_provisional_label() -> None:
    criterion = DEFAULT_PROGRESSION_CRITERIA["retention"]
    assert "Linardon et al. 2026 (derived ~84% retention, protocolized iCBT)" in criterion.citation
    assert "Youper week-4 retention 42.66%" in criterion.citation
    assert "DOI 10.1186/s40814-025-01675-9" in criterion.citation
    assert "Provisional RE:FRAME design thresholds" in criterion.justification
    assert "Provisional pending pilot validation." in criterion.justification
    assert "not directly comparable" in criterion.justification


def test_completeness_citation_and_cadence_are_labeled_provisional() -> None:
    criterion = DEFAULT_PROGRESSION_CRITERIA["data_completeness"]
    assert criterion.citation == (
        "Determining sample size for pilot trials: a tutorial "
        "(progression criteria: data completeness)."
    )
    assert "provisional RE:FRAME design assumption" in criterion.justification
    assert "operator-overridable" in criterion.justification


def test_safety_citation_carries_the_verified_anchors_and_non_convertibility_note() -> None:
    criterion = DEFAULT_PROGRESSION_CRITERIA["safety_event_rate"]
    assert (
        "NIA/NIH DSMP template (48-hour serious unexpected-event reporting)" in criterion.citation
    )
    assert "DOI 10.1038/s41746-024-01388-y" in criterion.citation
    assert "PMID 39695173" in criterion.citation
    assert "DOI 10.1111/acps.13225" in criterion.citation
    assert "PMID 32820538" in criterion.citation
    assert "indicative context only" in criterion.justification
    assert "not convertible to instance-level event rates" in criterion.justification
    assert "NOT by comparing the observed rate" in criterion.justification
    assert "not a safety or efficacy judgment" in criterion.justification


# ---------------------------------------------------------------------------
# band_from_value: exact boundaries, inclusive, unknown key fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("recruitment", 1.00, "green"),
        ("recruitment", 0.99, "amber"),
        ("recruitment", 0.75, "amber"),
        ("recruitment", 0.74, "red"),
        ("retention", 0.70, "green"),
        ("retention", 0.69, "amber"),
        ("retention", 0.50, "amber"),
        ("retention", 0.49, "red"),
        ("data_completeness", 0.80, "green"),
        ("data_completeness", 0.79, "amber"),
        ("data_completeness", 0.60, "amber"),
        ("data_completeness", 0.59, "red"),
    ],
)
def test_band_boundaries_are_inclusive(key: str, value: float, expected: str) -> None:
    assert band_from_value(key, value) == expected


@pytest.mark.parametrize("key", ["banana", "safety_event_rate", ""])
def test_band_from_value_rejects_keys_without_numeric_thresholds(key: str) -> None:
    with pytest.raises(ValueError):
        band_from_value(key, 1.0)


# ---------------------------------------------------------------------------
# safety_band (E5): class-based, first match wins, operational review status
# ---------------------------------------------------------------------------


def test_no_events_bands_green() -> None:
    assert safety_band((), now=NOW) == "green"


@pytest.mark.parametrize(
    ("ae_type", "expected"),
    [
        (AEType.CRISIS_RESPONSE_FAILURE, "red"),
        (AEType.INAPPROPRIATE_OR_DELAYED_ESCALATION, "red"),
        (AEType.HALLUCINATED_CLINICAL_CLAIM, "amber"),
        (AEType.BOUNDARY_VIOLATION_DIAGNOSIS, "amber"),
        (AEType.SYCOPHANCY_EPISODE, "amber"),
        (AEType.TRANSIENT_EARLY_WORSENSING, "green"),
    ],
)
def test_each_ae_type_alone_bands_by_the_pre_specified_class(
    ae_type: AEType, expected: str
) -> None:
    event = _event(ae_type)
    assert safety_band((event,), now=NOW) == expected


def test_an_overdue_serious_followup_bands_red() -> None:
    event = _event(
        AEType.HALLUCINATED_CLINICAL_CLAIM,
        serious=True,
        detected_at=NOW - datetime.timedelta(hours=49),
    )
    assert safety_band((event,), now=NOW) == "red"


def test_a_serious_followup_still_on_time_bands_amber() -> None:
    event = _event(
        AEType.HALLUCINATED_CLINICAL_CLAIM,
        serious=True,
        detected_at=NOW - datetime.timedelta(hours=1),
    )
    assert safety_band((event,), now=NOW) == "amber"


def test_a_completed_late_followup_is_no_longer_overdue() -> None:
    event = _event(
        AEType.HALLUCINATED_CLINICAL_CLAIM,
        serious=True,
        detected_at=NOW - datetime.timedelta(hours=49),
        followup_completed=True,
    )
    assert safety_band((event,), now=NOW) == "amber"


def test_a_non_serious_event_has_no_followup_marker_at_any_age() -> None:
    event = _event(
        AEType.TRANSIENT_EARLY_WORSENSING,
        detected_at=NOW - datetime.timedelta(days=400),
    )
    assert safety_band((event,), now=NOW) == "green"


def test_escalation_failure_takes_precedence_over_every_other_class() -> None:
    overdue_content = _event(
        AEType.HALLUCINATED_CLINICAL_CLAIM,
        serious=True,
        detected_at=NOW - datetime.timedelta(hours=49),
    )
    crisis = _event(AEType.CRISIS_RESPONSE_FAILURE)

    assert safety_band((overdue_content, crisis), now=NOW) == "red"


def test_events_are_examined_in_order_and_the_first_matching_class_wins() -> None:
    # A content-class event comes first, but a later escalation failure still wins
    # because the escalation-failure pass runs over ALL events before any amber.
    sycophancy = _event(AEType.SYCOPHANCY_EPISODE)
    escalation = _event(AEType.INAPPROPRIATE_OR_DELAYED_ESCALATION)

    assert safety_band((sycophancy, escalation), now=NOW) == "red"
    assert safety_band((escalation, sycophancy), now=NOW) == "red"
