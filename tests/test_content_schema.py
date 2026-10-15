"""Tests for ``reframe.content.schema`` — evidence-tiered exercise module types."""

from dataclasses import FrozenInstanceError

import pytest

from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)


def make_module(**overrides: object) -> ExerciseModule:
    """Build a valid module; ``overrides`` replace individual field values."""
    fields: dict[str, object] = {
        "id": "sample-module",
        "title": "A sample module",
        "summary": "A short summary of the sample module.",
        "category": ExerciseCategory.RUMINATION,
        "tier": EvidenceTier.A,
        "safety_class": SafetyClass.SELF_HELP_SAFE,
        "steps": ("Do the thing.", "Check the thing."),
        "sources": ("NICE NG222 depression in adults (2022)",),
    }
    fields.update(overrides)
    return ExerciseModule(**fields)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


def test_evidence_tiers_are_a_b_c() -> None:
    assert [tier.value for tier in EvidenceTier] == ["A", "B", "C"]


def test_categories_declared_in_fixed_order() -> None:
    assert [category.value for category in ExerciseCategory] == [
        "rumination",
        "behavioral_activation",
        "self_compassion",
        "emotion_regulation",
    ]


def test_safety_classes() -> None:
    assert [safety.value for safety in SafetyClass] == ["self_help_safe", "referral_only"]


# ---------------------------------------------------------------------------
# Valid construction
# ---------------------------------------------------------------------------


def test_valid_module_is_constructed_with_all_fields() -> None:
    module = make_module()
    assert module.id == "sample-module"
    assert module.category is ExerciseCategory.RUMINATION
    assert module.tier is EvidenceTier.A
    assert module.safety_class is SafetyClass.SELF_HELP_SAFE
    assert module.steps == ("Do the thing.", "Check the thing.")


def test_early_worsening_notice_defaults_true_and_contraindications_default_empty() -> None:
    module = make_module()
    assert module.early_worsening_notice is True
    assert module.contraindications == ()


def test_module_is_frozen() -> None:
    module = make_module()
    with pytest.raises(FrozenInstanceError):
        module.title = "Changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validation failures — each names the offending field
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    ["Bad_ID", "has space", "", "UPPER", "dot.item", "under_score"],
    ids=["uppercase", "space", "empty", "caps", "dot", "underscore"],
)
def test_bad_id_raises_value_error_naming_id(bad_id: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(id=bad_id)
    assert "id" in str(excinfo.value)
    assert repr(bad_id) in str(excinfo.value)


def test_non_string_id_raises_value_error_naming_id() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(id=42)
    assert "id" in str(excinfo.value)


@pytest.mark.parametrize("bad_title", ["", "   "], ids=["empty", "whitespace"])
def test_empty_title_raises_value_error_naming_title(bad_title: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(title=bad_title)
    assert "title" in str(excinfo.value)


def test_non_string_title_raises_value_error_naming_title() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(title=7)
    assert "title" in str(excinfo.value)


@pytest.mark.parametrize("bad_summary", ["", "   "], ids=["empty", "whitespace"])
def test_empty_summary_raises_value_error_naming_summary(bad_summary: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(summary=bad_summary)
    assert "summary" in str(excinfo.value)


def test_empty_step_raises_value_error_naming_steps() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(steps=("Do the thing.", "   "))
    assert "steps" in str(excinfo.value)


def test_non_string_step_raises_value_error_naming_steps() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(steps=("Do the thing.", 2))  # type: ignore[arg-type]
    assert "steps" in str(excinfo.value)


def test_too_few_steps_raises_value_error_naming_steps() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(steps=("Only one.",))
    assert "steps" in str(excinfo.value)


def test_no_steps_raises_value_error_naming_steps() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(steps=())
    assert "steps" in str(excinfo.value)


def test_steps_not_a_tuple_raises_value_error_naming_steps() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(steps=["Do the thing.", "Check it."])  # type: ignore[arg-type]
    assert "steps" in str(excinfo.value)


def test_empty_sources_raises_value_error_naming_sources() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(sources=())
    assert "sources" in str(excinfo.value)


def test_empty_source_entry_raises_value_error_naming_sources() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(sources=("   ",))
    assert "sources" in str(excinfo.value)


def test_sources_not_a_tuple_raises_value_error_naming_sources() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(sources=["NICE NG222 depression in adults (2022)"])  # type: ignore[arg-type]
    assert "sources" in str(excinfo.value)


def test_bad_category_raises_value_error_naming_category() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(category="rumination")
    assert "category" in str(excinfo.value)
    assert "rumination" in str(excinfo.value)


def test_bad_tier_raises_value_error_naming_tier() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(tier="D")
    assert "tier" in str(excinfo.value)
    assert "D" in str(excinfo.value)


def test_bad_safety_class_raises_value_error_naming_safety_class() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(safety_class="maybe")
    assert "safety_class" in str(excinfo.value)
    assert "maybe" in str(excinfo.value)


def test_contraindications_not_a_tuple_raises_value_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(contraindications=["not for trauma"])  # type: ignore[arg-type]
    assert "contraindications" in str(excinfo.value)


def test_empty_contraindication_entry_raises_value_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        make_module(contraindications=("",))
    assert "contraindications" in str(excinfo.value)


def test_enum_values_round_trip() -> None:
    assert ExerciseCategory("rumination") is ExerciseCategory.RUMINATION
    assert EvidenceTier("C") is EvidenceTier.C
    assert SafetyClass("referral_only") is SafetyClass.REFERRAL_ONLY
