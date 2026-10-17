"""Tests for ``reframe.measurement.instruments`` — validated free instrument specs.

Every test here is written BEFORE the implementation exists (strict TDD):
the first run must fail with ``ModuleNotFoundError``.
"""

import re
from dataclasses import FrozenInstanceError

import pytest

from reframe.measurement.instruments import (
    INSTRUMENTS,
    PENDING_VERIFICATION,
    AnswerOption,
    InstrumentSpec,
    ItemSpec,
    SeverityBand,
    get_instrument,
)

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

PHQ9_OPTIONS = (
    AnswerOption(0, "Not at all"),
    AnswerOption(1, "Several days"),
    AnswerOption(2, "More than half the days"),
    AnswerOption(3, "Nearly every day"),
)


def _items(n: int) -> tuple[ItemSpec, ...]:
    return tuple(ItemSpec(i, f"Item prompt {i}") for i in range(1, n + 1))


def make_spec(**overrides: object) -> InstrumentSpec:
    """Build a minimal valid InstrumentSpec, then apply field overrides."""
    fields: dict[str, object] = {
        "id": "synthetic",
        "title": "Synthetic Scale",
        "recall_period": "the past 7 days",
        "items": _items(5),
        "scale_min": 0,
        "scale_max": 3,
        "total_min": 0,
        "total_max": 15,
        "answer_options": PHQ9_OPTIONS,
        "severity_bands": (),
        "citation": "Tester 2026, Journal of Synthetic Instruments",
    }
    fields.update(overrides)
    return InstrumentSpec(**fields)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Leaf dataclasses: validation & immutability
# ---------------------------------------------------------------------------


def test_answer_option_holds_value_and_label() -> None:
    option = AnswerOption(2, "More than half the days")
    assert option.value == 2
    assert option.label == "More than half the days"


def test_answer_option_is_frozen() -> None:
    option = AnswerOption(0, "Not at all")
    with pytest.raises(FrozenInstanceError):
        option.value = 3  # type: ignore[misc]


def test_item_spec_holds_index_and_prompt() -> None:
    item = ItemSpec(1, "Little interest or pleasure in doing things")
    assert item.index == 1
    assert "Little interest" in item.prompt


def test_item_spec_rejects_zero_index() -> None:
    with pytest.raises(ValueError, match="index"):
        ItemSpec(0, "Prompt")


def test_item_spec_rejects_negative_index() -> None:
    with pytest.raises(ValueError, match="index"):
        ItemSpec(-1, "Prompt")


def test_item_spec_rejects_empty_prompt() -> None:
    with pytest.raises(ValueError, match="prompt"):
        ItemSpec(1, "")


def test_severity_band_holds_label_and_bounds() -> None:
    band = SeverityBand("mild", 5, 9)
    assert (band.label, band.lower, band.upper) == ("mild", 5, 9)


def test_severity_band_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError, match="upper"):
        SeverityBand("bad", 10, 9)


# ---------------------------------------------------------------------------
# InstrumentSpec: each failure mode, one by one
# ---------------------------------------------------------------------------


def test_spec_accepts_minimal_valid_instance() -> None:
    spec = make_spec()
    assert spec.id == "synthetic"
    assert len(spec.items) == 5
    assert spec.reverse_scored == ()


def test_spec_rejects_bad_id() -> None:
    with pytest.raises(ValueError, match="id"):
        make_spec(id="PHQ-9!")


def test_spec_rejects_uppercase_id() -> None:
    with pytest.raises(ValueError, match="id"):
        make_spec(id="phq9X")


def test_spec_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="title"):
        make_spec(title="")


def test_spec_rejects_empty_recall_period() -> None:
    with pytest.raises(ValueError, match="recall_period"):
        make_spec(recall_period="")


def test_spec_rejects_too_few_items() -> None:
    with pytest.raises(ValueError, match="items"):
        make_spec(items=_items(4))


def test_spec_rejects_item_index_gap() -> None:
    bad = (ItemSpec(1, "a"), ItemSpec(2, "b"), ItemSpec(4, "c"), ItemSpec(5, "d"), ItemSpec(6, "e"))
    with pytest.raises(ValueError, match="items"):
        make_spec(items=bad)


def test_spec_rejects_non_increasing_item_indices() -> None:
    bad = (ItemSpec(2, "a"), ItemSpec(1, "b"), ItemSpec(3, "c"), ItemSpec(4, "d"), ItemSpec(5, "e"))
    with pytest.raises(ValueError, match="items"):
        make_spec(items=bad)


def test_spec_rejects_scale_max_not_greater_than_scale_min() -> None:
    with pytest.raises(ValueError, match="scale"):
        make_spec(scale_min=3, scale_max=3)


def test_spec_rejects_inverted_total_range() -> None:
    with pytest.raises(ValueError, match="total"):
        make_spec(total_min=16, total_max=15)


def test_spec_rejects_answer_options_missing_a_scale_value() -> None:
    with pytest.raises(ValueError, match="answer_options"):
        make_spec(answer_options=PHQ9_OPTIONS[:-1])


def test_spec_rejects_answer_options_with_extra_value() -> None:
    with pytest.raises(ValueError, match="answer_options"):
        make_spec(answer_options=(*PHQ9_OPTIONS, AnswerOption(4, "Bonus")))


def test_spec_rejects_empty_answer_options() -> None:
    with pytest.raises(ValueError, match="answer_options"):
        make_spec(answer_options=())


def test_spec_rejects_overlapping_bands() -> None:
    bands = (
        SeverityBand("a", 0, 8),
        SeverityBand("b", 8, 15),  # overlap at 8
    )
    with pytest.raises(ValueError, match="severity_bands"):
        make_spec(severity_bands=bands)


def test_spec_rejects_band_gap() -> None:
    bands = (
        SeverityBand("a", 0, 7),  # gap at 8
        SeverityBand("b", 9, 15),
    )
    with pytest.raises(ValueError, match="severity_bands"):
        make_spec(severity_bands=bands)


def test_spec_rejects_bands_not_covering_total_min() -> None:
    bands = (SeverityBand("b", 1, 15),)
    with pytest.raises(ValueError, match="severity_bands"):
        make_spec(severity_bands=bands)


def test_spec_rejects_bands_not_covering_total_max() -> None:
    bands = (SeverityBand("a", 0, 14),)
    with pytest.raises(ValueError, match="severity_bands"):
        make_spec(severity_bands=bands)


def test_spec_accepts_partitioning_bands() -> None:
    bands = (
        SeverityBand("low", 0, 7),
        SeverityBand("high", 8, 15),
    )
    assert make_spec(severity_bands=bands).severity_bands == bands


def test_spec_rejects_empty_citation() -> None:
    with pytest.raises(ValueError, match="citation"):
        make_spec(citation="")


def test_spec_rejects_reverse_index_for_unknown_item() -> None:
    with pytest.raises(ValueError, match="reverse_scored"):
        make_spec(reverse_scored=(1, 6))


def test_spec_accepts_valid_reverse_index() -> None:
    assert make_spec(reverse_scored=(1,)).reverse_scored == (1,)


def test_spec_is_frozen() -> None:
    spec = make_spec()
    with pytest.raises(FrozenInstanceError):
        spec.id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Registry: exactly phq9 / gad7 / k10 active; scs_sf fail-closed pending
# ---------------------------------------------------------------------------


def test_registry_has_exactly_the_three_active_instruments() -> None:
    assert set(INSTRUMENTS) == {"phq9", "gad7", "k10"}


def test_phq9_metadata() -> None:
    phq9 = INSTRUMENTS["phq9"]
    assert phq9.title == "Patient Health Questionnaire-9 (PHQ-9)"
    assert phq9.recall_period == "the past 2 weeks"
    assert (phq9.scale_min, phq9.scale_max) == (0, 3)
    assert (phq9.total_min, phq9.total_max) == (0, 27)
    assert "Kroenke" in phq9.citation


def test_phq9_has_nine_items() -> None:
    assert len(INSTRUMENTS["phq9"].items) == 9


def test_phq9_item9_is_the_self_harm_item() -> None:
    item9 = INSTRUMENTS["phq9"].items[8]
    assert item9.index == 9
    assert "better off dead" in item9.prompt


def test_phq9_bands() -> None:
    bands = INSTRUMENTS["phq9"].severity_bands
    assert [(b.lower, b.upper) for b in bands] == [(0, 4), (5, 9), (10, 14), (15, 19), (20, 27)]
    assert [b.label for b in bands] == [
        "minimal",
        "mild",
        "moderate",
        "moderately severe",
        "severe",
    ]


def test_gad7_metadata() -> None:
    gad7 = INSTRUMENTS["gad7"]
    assert gad7.title == "Generalized Anxiety Disorder-7 (GAD-7)"
    assert gad7.recall_period == "the past 2 weeks"
    assert (gad7.scale_min, gad7.scale_max) == (0, 3)
    assert (gad7.total_min, gad7.total_max) == (0, 21)
    assert "Spitzer" in gad7.citation


def test_gad7_has_seven_items() -> None:
    assert len(INSTRUMENTS["gad7"].items) == 7


def test_gad7_first_item_prompt() -> None:
    assert INSTRUMENTS["gad7"].items[0].prompt == "Feeling nervous, anxious, or on edge"


def test_gad7_bands() -> None:
    bands = INSTRUMENTS["gad7"].severity_bands
    assert [(b.lower, b.upper) for b in bands] == [(0, 4), (5, 9), (10, 14), (15, 21)]
    assert [b.label for b in bands] == ["minimal", "mild", "moderate", "severe"]


def test_k10_metadata() -> None:
    k10 = INSTRUMENTS["k10"]
    assert k10.title == "Kessler Psychological Distress Scale (K-10)"
    assert k10.recall_period == "the past 30 days"
    assert (k10.scale_min, k10.scale_max) == (1, 5)
    assert (k10.total_min, k10.total_max) == (10, 50)
    assert "Kessler" in k10.citation


def test_k10_has_ten_items() -> None:
    assert len(INSTRUMENTS["k10"].items) == 10


def test_k10_items_all_use_the_how_often_stem() -> None:
    for item in INSTRUMENTS["k10"].items:
        assert item.prompt.startswith("About how often did you")


def test_k10_bands() -> None:
    bands = INSTRUMENTS["k10"].severity_bands
    assert [(b.lower, b.upper) for b in bands] == [(10, 19), (20, 24), (25, 29), (30, 50)]
    assert [b.label for b in bands] == ["likely well", "mild", "moderate", "severe"]


@pytest.mark.parametrize("instrument_id", sorted(INSTRUMENTS))
def test_bands_partition_every_total(instrument_id: str) -> None:
    """Property test: every achievable total maps to exactly one band."""
    spec = INSTRUMENTS[instrument_id]
    for total in range(spec.total_min, spec.total_max + 1):
        matches = [b for b in spec.severity_bands if b.lower <= total <= b.upper]
        assert len(matches) == 1, f"{instrument_id} total {total} matched {len(matches)} bands"


@pytest.mark.parametrize("instrument_id", sorted(INSTRUMENTS))
def test_answer_options_exactly_cover_scale(instrument_id: str) -> None:
    spec = INSTRUMENTS[instrument_id]
    values = sorted(option.value for option in spec.answer_options)
    assert values == list(range(spec.scale_min, spec.scale_max + 1))


def test_scs_sf_is_pending_not_active() -> None:
    assert "scs_sf" in PENDING_VERIFICATION
    assert "scs_sf" not in INSTRUMENTS


def test_scs_sf_pending_spec_has_ten_placeholder_items() -> None:
    scs_sf = PENDING_VERIFICATION["scs_sf"]
    assert len(scs_sf.items) == 10
    for position, item in enumerate(scs_sf.items, start=1):
        assert item.prompt == f"PENDING-VERIFICATION item {position}"
    assert (scs_sf.scale_min, scs_sf.scale_max) == (1, 5)
    assert (scs_sf.total_min, scs_sf.total_max) == (10, 50)
    assert "pending verification" in scs_sf.citation


def test_get_instrument_returns_active_spec() -> None:
    assert get_instrument("phq9") is INSTRUMENTS["phq9"]


def test_get_instrument_rejects_pending_instrument() -> None:
    """A pending instrument must be indistinguishable from an unknown one."""
    with pytest.raises(ValueError, match="scs_sf"):
        get_instrument("scs_sf")


def test_get_instrument_rejects_unknown_id() -> None:
    with pytest.raises(ValueError, match="nope"):
        get_instrument("nope")


def test_instrument_ids_match_the_declared_pattern() -> None:
    pattern = re.compile(r"^[a-z0-9_]+$")
    for registry in (INSTRUMENTS, PENDING_VERIFICATION):
        for instrument_id in registry:
            assert pattern.match(instrument_id)
