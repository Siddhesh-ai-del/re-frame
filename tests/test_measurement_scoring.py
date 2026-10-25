"""Tests for ``reframe.measurement.scoring`` — fail-closed instrument scoring.

Every test here is written BEFORE the implementation exists (strict TDD):
the first run must fail with ``ModuleNotFoundError``.
"""

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from reframe.measurement import instruments
from reframe.measurement.instruments import (
    INSTRUMENTS,
    AnswerOption,
    InstrumentSpec,
    ItemSpec,
)
from reframe.measurement.scoring import ScoreResult, score, severity_for_total


def _items(n: int) -> tuple[ItemSpec, ...]:
    return tuple(ItemSpec(i, f"Item prompt {i}") for i in range(1, n + 1))


def _options_0_3() -> tuple[AnswerOption, ...]:
    return (
        AnswerOption(0, "Not at all"),
        AnswerOption(1, "Several days"),
        AnswerOption(2, "More than half the days"),
        AnswerOption(3, "Nearly every day"),
    )


@pytest.fixture
def synthetic_reverse_spec() -> InstrumentSpec:
    """Tiny synthetic spec with item 1 reverse-scored, scale 0..3, total 0..15."""
    return InstrumentSpec(
        id="synthetic_reverse",
        title="Synthetic Reverse-Scored Scale",
        recall_period="the past 7 days",
        items=_items(5),
        scale_min=0,
        scale_max=3,
        total_min=0,
        total_max=15,
        answer_options=_options_0_3(),
        severity_bands=(),
        citation="Tester 2026, Journal of Synthetic Instruments",
        reverse_scored=(1,),
    )


# ---------------------------------------------------------------------------
# ScoreResult shape
# ---------------------------------------------------------------------------


def test_score_result_fields() -> None:
    result = ScoreResult(
        instrument_id="phq9",
        total=12,
        severity_label="moderate",
        responses=(0, 1, 2, 3, 0, 1, 2, 3, 0),
    )
    assert result.instrument_id == "phq9"
    assert result.total == 12
    assert result.severity_label == "moderate"
    assert result.responses == (0, 1, 2, 3, 0, 1, 2, 3, 0)


def test_score_result_is_frozen() -> None:
    result = ScoreResult("phq9", 0, "minimal", (0,) * 9)
    with pytest.raises(FrozenInstanceError):
        result.total = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PHQ-9 scoring: known totals and band boundaries
# ---------------------------------------------------------------------------


def test_phq9_all_zeros_is_minimal() -> None:
    result = score("phq9", [0] * 9)
    assert result.total == 0
    assert result.severity_label == "minimal"


def test_phq9_all_threes_is_severe() -> None:
    result = score("phq9", [3] * 9)
    assert result.total == 27
    assert result.severity_label == "severe"


def test_phq9_mixed_responses_total_12_moderate() -> None:
    result = score("phq9", [0, 1, 2, 3, 0, 1, 2, 3, 0])
    assert result.total == 12
    assert result.severity_label == "moderate"
    assert result.responses == (0, 1, 2, 3, 0, 1, 2, 3, 0)


def test_phq9_total_4_is_minimal_boundary() -> None:
    assert score("phq9", [0, 0, 0, 0, 0, 0, 0, 1, 3]).severity_label == "minimal"


def test_phq9_total_5_is_mild_boundary() -> None:
    assert score("phq9", [0, 0, 0, 0, 0, 0, 0, 2, 3]).severity_label == "mild"


def test_phq9_total_14_is_moderate_boundary() -> None:
    assert score("phq9", [2, 2, 2, 2, 2, 2, 0, 0, 2]).severity_label == "moderate"


def test_phq9_total_15_is_moderately_severe_boundary() -> None:
    assert score("phq9", [2, 2, 2, 2, 2, 2, 0, 1, 2]).severity_label == "moderately severe"


def test_phq9_total_19_is_moderately_severe_upper_boundary() -> None:
    assert score("phq9", [3, 2, 2, 2, 2, 2, 2, 2, 2]).severity_label == "moderately severe"


def test_phq9_total_20_is_severe_boundary() -> None:
    assert score("phq9", [3, 3, 2, 2, 2, 2, 2, 2, 2]).severity_label == "severe"


# ---------------------------------------------------------------------------
# GAD-7 and K-10 scoring
# ---------------------------------------------------------------------------


def test_gad7_seven_ones_is_mild() -> None:
    result = score("gad7", [1] * 7)
    assert result.total == 7
    assert result.severity_label == "mild"


def test_k10_all_ones_is_likely_well() -> None:
    result = score("k10", [1] * 10)
    assert result.total == 10
    assert result.severity_label == "likely well"


def test_k10_all_fives_is_severe() -> None:
    result = score("k10", [5] * 10)
    assert result.total == 50
    assert result.severity_label == "severe"


# ---------------------------------------------------------------------------
# SCS-SF scoring: reverse arithmetic verified by hand in the comments
# ---------------------------------------------------------------------------
# Reverse-scored items are 1, 4, 8, 9, 11, 12 (six of twelve); the reverse
# of value v on the 1..5 scale is 1 + 5 - v (1<->5, 2<->4, 3<->3).


def test_scs_sf_all_ones_reverses_to_total_36_moderate() -> None:
    # All "Almost never" (1). The six reverse items become 5 each; the six
    # forward items stay 1: total = 6*5 + 6*1 = 36 -> mean 3.0 -> moderate.
    result = score("scs_sf", [1] * 12)
    assert result.total == 36
    assert result.severity_label == "moderate"
    assert result.responses == (1,) * 12


def test_scs_sf_all_fives_reverses_to_total_36_moderate() -> None:
    # All "Almost always" (5). The six reverse items become 1 each; the six
    # forward items stay 5: total = 6*1 + 6*5 = 36 -> mean 3.0 -> moderate.
    result = score("scs_sf", [5] * 12)
    assert result.total == 36
    assert result.severity_label == "moderate"


def test_scs_sf_min_compassion_vector_is_total_12_low() -> None:
    # Forward items (2,3,5,6,7,10) = 1; reverse items (1,4,8,9,11,12) = 5.
    # After reverse scoring the reverse items become 1 too:
    # total = 6*1 + 6*1 = 12 (the floor) -> low.
    responses = [1] * 12
    for index in (0, 3, 7, 8, 10, 11):  # items 1,4,8,9,11,12 (0-based)
        responses[index] = 5
    result = score("scs_sf", responses)
    assert result.total == 12
    assert result.severity_label == "low"
    assert result.responses == tuple(responses)


def test_scs_sf_max_compassion_vector_is_total_60_high() -> None:
    # Forward items = 5; reverse items = 1, which reverse-score to 5:
    # total = 12*5 = 60 (the ceiling) -> high.
    responses = [5] * 12
    for index in (0, 3, 7, 8, 10, 11):
        responses[index] = 1
    result = score("scs_sf", responses)
    assert result.total == 60
    assert result.severity_label == "high"


# ---------------------------------------------------------------------------
# Fail-closed validation: wrong count, bad types, out-of-range values
# ---------------------------------------------------------------------------


def test_unknown_instrument_raises() -> None:
    with pytest.raises(ValueError, match="nope"):
        score("nope", [0] * 9)


def test_wrong_response_count_for_scs_sf_raises_naming_expectation() -> None:
    with pytest.raises(ValueError, match="12"):
        score("scs_sf", [1] * 10)


def test_wrong_response_count_raises_naming_expectation() -> None:
    with pytest.raises(ValueError, match="9"):
        score("phq9", [0] * 8)


def test_too_many_responses_raises() -> None:
    with pytest.raises(ValueError, match="9"):
        score("phq9", [0] * 10)


@pytest.mark.parametrize("bad_value", [-1, 4])
def test_phq9_out_of_range_value_raises_naming_index(bad_value: int) -> None:
    responses: list[int] = [0] * 9
    responses[4] = bad_value  # 5th response, 1-based index 5
    with pytest.raises(ValueError, match="index 5"):
        score("phq9", responses)


@pytest.mark.parametrize("bad_value", [0, 6])
def test_k10_out_of_range_value_raises_naming_index(bad_value: int) -> None:
    responses: list[int] = [3] * 10
    responses[2] = bad_value  # 3rd response, 1-based index 3
    with pytest.raises(ValueError, match="index 3"):
        score("k10", responses)


def test_bool_response_is_rejected_naming_index() -> None:
    responses: list[Any] = [0] * 9
    responses[0] = True
    with pytest.raises(ValueError, match="index 1"):
        score("phq9", responses)


def test_float_response_is_rejected_naming_index() -> None:
    responses: list[Any] = [0] * 9
    responses[8] = 2.5  # type: ignore[assignment]
    with pytest.raises(ValueError, match="index 9"):
        score("phq9", responses)


def test_none_response_is_rejected_naming_index() -> None:
    responses: list[Any] = [1] * 10
    responses[9] = None
    with pytest.raises(ValueError, match="index 10"):
        score("k10", responses)


# ---------------------------------------------------------------------------
# Reverse scoring
# ---------------------------------------------------------------------------


def test_reverse_scoring_flips_the_first_item(
    synthetic_reverse_spec: InstrumentSpec,
) -> None:
    original = instruments.INSTRUMENTS.get("synthetic_reverse")
    instruments.INSTRUMENTS["synthetic_reverse"] = synthetic_reverse_spec
    try:
        # Item 1 answered 3 reverses to 0 + 3 - 3 = 0; others are 0 -> total 0.
        assert score("synthetic_reverse", [3, 0, 0, 0, 0]).total == 0
        # Item 1 answered 0 reverses to 3; others are 1 -> total 3 + 4 = 7.
        result = score("synthetic_reverse", [0, 1, 1, 1, 1])
        assert result.total == 7
        # Severity label is None when the instrument declares no bands.
        assert result.severity_label is None
        # Responses are preserved as answered, not as scored.
        assert result.responses == (0, 1, 1, 1, 1)
    finally:
        if original is None:
            del instruments.INSTRUMENTS["synthetic_reverse"]
        else:
            instruments.INSTRUMENTS["synthetic_reverse"] = original


# ---------------------------------------------------------------------------
# severity_for_total helper
# ---------------------------------------------------------------------------


def test_severity_for_total_returns_band_label() -> None:
    phq9 = INSTRUMENTS["phq9"]
    assert severity_for_total(phq9, 0) == "minimal"
    assert severity_for_total(phq9, 10) == "moderate"
    assert severity_for_total(phq9, 27) == "severe"


def test_severity_for_total_returns_none_without_bands(
    synthetic_reverse_spec: InstrumentSpec,
) -> None:
    assert severity_for_total(synthetic_reverse_spec, 7) is None


@pytest.mark.parametrize("total", [-1, 28])
def test_severity_for_total_rejects_out_of_range(total: int) -> None:
    phq9 = INSTRUMENTS["phq9"]
    with pytest.raises(ValueError, match=str(total)):
        severity_for_total(phq9, total)


def test_severity_for_total_rejects_out_of_range_k10() -> None:
    k10 = INSTRUMENTS["k10"]
    with pytest.raises(ValueError, match="9"):
        severity_for_total(k10, 9)
