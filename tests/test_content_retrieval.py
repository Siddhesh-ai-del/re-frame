"""Tests for ``reframe.content.retrieval`` — deterministic, tiered module retrieval."""

from dataclasses import FrozenInstanceError

import pytest

from reframe.content.library import ContentLibrary, default_library
from reframe.content.retrieval import RetrievalResult, retrieve
from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)


def _referral_module() -> ExerciseModule:
    """A REFERRAL_ONLY module that would outrank every safe module if selected."""
    return ExerciseModule(
        id="aaa-referral-only",
        title="Referral-only module",
        summary="Must never be selected by retrieval.",
        category=ExerciseCategory.RUMINATION,
        tier=EvidenceTier.A,
        safety_class=SafetyClass.REFERRAL_ONLY,
        steps=("Pause.", "Seek professional support."),
        sources=("NICE NG222 depression in adults (2022)",),
    )


def _safe_module(module_id: str, tier: EvidenceTier) -> ExerciseModule:
    return ExerciseModule(
        id=module_id,
        title=f"Safe module {module_id}",
        summary="A self-help-safe module.",
        category=ExerciseCategory.RUMINATION,
        tier=tier,
        safety_class=SafetyClass.SELF_HELP_SAFE,
        steps=("Do the thing.", "Check the thing."),
        sources=("NICE NG222 depression in adults (2022)",),
    )


# ---------------------------------------------------------------------------
# Result surface
# ---------------------------------------------------------------------------


def test_retrieval_result_is_frozen() -> None:
    result = retrieve("I keep ruminating", default_library())
    with pytest.raises(FrozenInstanceError):
        result.modules = ()  # type: ignore[misc]


def test_public_content_api_is_exported() -> None:
    from reframe import content

    for name in (
        "EvidenceTier",
        "ExerciseCategory",
        "ExerciseModule",
        "SafetyClass",
        "ContentLibrary",
        "load_library_json",
        "default_library",
        "MATCH_RULES",
        "match_categories",
        "RetrievalResult",
        "retrieve",
    ):
        assert hasattr(content, name), f"missing public export: {name}"


# ---------------------------------------------------------------------------
# Happy path on the packaged library
# ---------------------------------------------------------------------------


def test_rumination_text_returns_only_rumination_modules_tier_a_first() -> None:
    result = retrieve("I can't stop thinking about it", default_library())
    assert result.categories == (ExerciseCategory.RUMINATION,)
    assert result.modules, "expected rumination modules"
    assert all(module.category is ExerciseCategory.RUMINATION for module in result.modules)
    assert all(module.safety_class is SafetyClass.SELF_HELP_SAFE for module in result.modules)
    tiers = [module.tier for module in result.modules]
    assert tiers == sorted(tiers, key=lambda tier: (tier is not EvidenceTier.A, tier.value))
    assert result.modules[0].tier is EvidenceTier.A


def test_rumination_selection_is_capped_at_two_and_ordered_by_id_within_tier() -> None:
    result = retrieve("I keep ruminating and I overthink everything", default_library())
    assert len(result.modules) == 2
    # All packaged rumination modules are tier A → id order decides.
    assert [module.id for module in result.modules] == [
        "attention-shift-refocus",
        "concreteness-training",
    ]


def test_max_per_category_of_one_is_respected() -> None:
    result = retrieve("I keep ruminating", default_library(), max_per_category=1)
    assert len(result.modules) == 1
    assert result.modules[0].id == "attention-shift-refocus"


def test_matched_rule_ids_list_the_rules_that_fired_in_rule_order() -> None:
    result = retrieve("I can't stop thinking about it", default_library())
    assert result.matched_rule_ids == ("RUM-CANT-STOP-THINKING",)


def test_multi_category_retrieval_groups_modules_by_enum_order() -> None:
    text = "I can't stop thinking and I keep blaming myself"
    result = retrieve(text, default_library())
    assert result.categories == (ExerciseCategory.RUMINATION, ExerciseCategory.SELF_COMPASSION)
    assert result.matched_rule_ids, "expected matched rule ids"
    rumination_ids = [
        module.id for module in result.modules if module.category is ExerciseCategory.RUMINATION
    ]
    assert len(rumination_ids) == 2
    first_compassion_index = next(
        index
        for index, module in enumerate(result.modules)
        if module.category is ExerciseCategory.SELF_COMPASSION
    )
    assert first_compassion_index == 2, "self-compassion modules must follow rumination ones"


def test_retrieval_is_deterministic_across_calls() -> None:
    text = "I can't calm down and I keep ruminating"
    assert retrieve(text, default_library()) == retrieve(text, default_library())


def test_no_match_returns_an_entirely_empty_result() -> None:
    result = retrieve("What will the weather be like tomorrow?", default_library())
    assert result.categories == ()
    assert result.modules == ()
    assert result.matched_rule_ids == ()


# ---------------------------------------------------------------------------
# Boundaries
# ---------------------------------------------------------------------------


def test_max_per_category_below_one_raises_value_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        retrieve("I keep ruminating", default_library(), max_per_category=0)
    assert "max_per_category" in str(excinfo.value)


@pytest.mark.parametrize(
    "bad",
    [None, 7, [], {}, object()],
    ids=["none", "int", "list", "dict", "object"],
)
def test_non_string_input_raises_type_error(bad: object) -> None:
    with pytest.raises(TypeError):
        retrieve(bad, default_library())  # type: ignore[arg-type]


@pytest.mark.parametrize("blank", ["", "   ", "\t\n "])
def test_empty_input_raises_value_error(blank: str) -> None:
    with pytest.raises(ValueError):
        retrieve(blank, default_library())


# ---------------------------------------------------------------------------
# REFERRAL_ONLY exclusion policy
# ---------------------------------------------------------------------------


def test_referral_only_module_is_never_selected() -> None:
    library = ContentLibrary(
        modules=(
            _referral_module(),
            _safe_module("zzz-safe-low", EvidenceTier.C),
            _safe_module("bbb-safe-high", EvidenceTier.A),
        )
    )
    result = retrieve("I keep ruminating", library)
    selected_ids = [module.id for module in result.modules]
    assert "aaa-referral-only" not in selected_ids
    # Safe modules win, tier A first regardless of the referral module's rank.
    assert selected_ids == ["bbb-safe-high", "zzz-safe-low"]


def test_category_with_only_referral_yields_no_modules_for_that_category() -> None:
    library = ContentLibrary(modules=(_referral_module(),))
    result = retrieve("I keep ruminating", library)
    assert result.categories == (ExerciseCategory.RUMINATION,)
    assert result.matched_rule_ids
    assert result.modules == ()


def test_result_is_a_retrieval_result_instance() -> None:
    result = retrieve("I keep ruminating", default_library())
    assert isinstance(result, RetrievalResult)
