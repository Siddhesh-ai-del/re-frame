"""Tests for ``reframe.content.library`` — library assembly and packaged loading."""

import json
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from reframe.content.library import ContentLibrary, default_library, load_library_json
from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)


def minimal_module_data(**overrides: object) -> dict[str, Any]:
    """Build one valid JSON-shaped module dict; ``overrides`` replace fields."""
    data: dict[str, Any] = {
        "id": "sample-module",
        "title": "A sample module",
        "summary": "A short summary of the sample module.",
        "category": "rumination",
        "tier": "A",
        "safety_class": "self_help_safe",
        "steps": ["Do the thing.", "Check the thing."],
        "sources": ["NICE NG222 depression in adults (2022)"],
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# default_library(): packaged data, fail-closed loading, single instance
# ---------------------------------------------------------------------------


def test_default_library_loads_at_least_eleven_modules() -> None:
    library = default_library()
    assert len(library.modules) >= 11


def test_default_library_has_at_least_two_modules_per_category() -> None:
    library = default_library()
    for category in ExerciseCategory:
        assert len(library.by_category(category)) >= 2, f"category {category.value} too sparse"


def test_default_library_is_fully_self_help_safe() -> None:
    for module in default_library().modules:
        assert module.safety_class is SafetyClass.SELF_HELP_SAFE, module.id


def test_default_library_sets_early_worsening_notice_everywhere() -> None:
    for module in default_library().modules:
        assert module.early_worsening_notice is True, module.id


def test_default_library_ids_are_unique() -> None:
    ids = default_library().ids
    assert len(ids) == len(set(ids))


def test_default_library_is_a_single_cached_instance() -> None:
    assert default_library() is default_library()


def test_default_library_ids_match_module_order() -> None:
    library = default_library()
    assert library.ids == tuple(module.id for module in library.modules)


def test_default_library_fails_closed_when_packaged_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from reframe.content import library as library_module

    def _boom(package: str) -> object:
        raise FileNotFoundError(package)

    default_library.cache_clear()
    monkeypatch.setattr(library_module.resources, "files", _boom)
    with pytest.raises(FileNotFoundError):
        default_library()
    monkeypatch.undo()
    default_library.cache_clear()


def test_default_library_fails_closed_when_packaged_file_is_corrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from reframe.content import library as library_module

    class _Corrupt:
        def joinpath(self, *parts: str) -> "_Corrupt":
            return self

        def read_text(self, encoding: str = "utf-8") -> str:
            return "{ this is not valid json"

    default_library.cache_clear()
    monkeypatch.setattr(library_module.resources, "files", lambda package: _Corrupt())
    with pytest.raises(json.JSONDecodeError):
        default_library()
    monkeypatch.undo()
    default_library.cache_clear()


# ---------------------------------------------------------------------------
# ContentLibrary surface
# ---------------------------------------------------------------------------


def test_library_is_frozen() -> None:
    library = ContentLibrary(modules=())
    with pytest.raises(FrozenInstanceError):
        library.modules = ()  # type: ignore[misc]


def test_by_id_returns_the_matching_module() -> None:
    library = default_library()
    module = library.by_id("rumination-postponement")
    assert module.id == "rumination-postponement"
    assert module.category is ExerciseCategory.RUMINATION


def test_by_id_miss_raises_value_error_naming_the_id() -> None:
    library = default_library()
    with pytest.raises(ValueError) as excinfo:
        library.by_id("no-such-module")
    assert "no-such-module" in str(excinfo.value)


def test_by_category_returns_non_empty_for_every_category() -> None:
    library = default_library()
    for category in ExerciseCategory:
        modules = library.by_category(category)
        assert modules, f"no modules for {category.value}"
        assert all(module.category is category for module in modules)


def test_by_category_returns_empty_tuple_for_absent_category() -> None:
    library = ContentLibrary(modules=())
    assert library.by_category(ExerciseCategory.RUMINATION) == ()


# ---------------------------------------------------------------------------
# load_library_json(): happy path
# ---------------------------------------------------------------------------


def test_load_library_json_builds_modules_from_dicts() -> None:
    library = load_library_json([minimal_module_data()])
    assert len(library.modules) == 1
    module = library.modules[0]
    assert module.id == "sample-module"
    assert module.category is ExerciseCategory.RUMINATION
    assert module.tier is EvidenceTier.A
    assert module.safety_class is SafetyClass.SELF_HELP_SAFE
    assert module.steps == ("Do the thing.", "Check the thing.")


def test_load_library_json_accepts_optional_fields_and_converts_lists_to_tuples() -> None:
    data = minimal_module_data(
        early_worsening_notice=False,
        contraindications=["not for trauma processing"],
    )
    module = load_library_json([data]).modules[0]
    assert module.early_worsening_notice is False
    assert module.contraindications == ("not for trauma processing",)


def test_load_library_json_empty_list_returns_empty_library() -> None:
    library = load_library_json([])
    assert library.modules == ()
    assert library.ids == ()


# ---------------------------------------------------------------------------
# load_library_json(): fail-closed rejection
# ---------------------------------------------------------------------------


def test_load_library_json_rejects_non_list_input() -> None:
    with pytest.raises(ValueError) as excinfo:
        load_library_json({"id": "not-a-list"})
    assert "list" in str(excinfo.value)


def test_load_library_json_rejects_non_object_item_naming_its_index() -> None:
    with pytest.raises(ValueError) as excinfo:
        load_library_json(["not-an-object"])
    assert "index 0" in str(excinfo.value)


def test_load_library_json_rejects_bad_item_naming_its_id() -> None:
    data = minimal_module_data(steps="not-a-list")
    with pytest.raises(ValueError) as excinfo:
        load_library_json([data])
    message = str(excinfo.value)
    assert "sample-module" in message
    assert "steps" in message


def test_load_library_json_rejects_invalid_enum_value_naming_its_id() -> None:
    data = minimal_module_data(category="anxiety")
    with pytest.raises(ValueError) as excinfo:
        load_library_json([data])
    message = str(excinfo.value)
    assert "sample-module" in message
    assert "anxiety" in message


def test_load_library_json_rejects_unhashable_enum_value_naming_its_id() -> None:
    data = minimal_module_data(tier=["A"])
    with pytest.raises(ValueError) as excinfo:
        load_library_json([data])
    assert "sample-module" in str(excinfo.value)


def test_load_library_json_rejects_module_missing_required_key_naming_its_id() -> None:
    data = minimal_module_data()
    del data["summary"]
    with pytest.raises(ValueError) as excinfo:
        load_library_json([data])
    message = str(excinfo.value)
    assert "sample-module" in message
    assert "summary" in message


def test_load_library_json_rejects_item_without_id_naming_its_index() -> None:
    data = minimal_module_data()
    del data["id"]
    with pytest.raises(ValueError) as excinfo:
        load_library_json([data])
    message = str(excinfo.value)
    assert "index 0" in message
    assert "id" in message


def test_load_library_json_rejects_non_string_id_value() -> None:
    data = minimal_module_data()
    data["id"] = 42
    with pytest.raises(ValueError) as excinfo:
        load_library_json([data])
    message = str(excinfo.value)
    assert "42" in message
    assert "id" in message


def test_load_library_json_rejects_duplicate_ids_naming_the_id() -> None:
    data = [minimal_module_data(), minimal_module_data()]
    with pytest.raises(ValueError) as excinfo:
        load_library_json(data)
    message = str(excinfo.value)
    assert "duplicate" in message
    assert "sample-module" in message


def test_load_library_json_rejects_one_bad_item_in_an_otherwise_valid_library() -> None:
    data = [minimal_module_data(), minimal_module_data(id="second-module")]
    data[1]["steps"] = "not-a-list"
    with pytest.raises(ValueError) as excinfo:
        load_library_json(data)
    message = str(excinfo.value)
    assert "second-module" in message
    assert "steps" in message


def test_valid_module_dict_round_trips_through_the_dataclass() -> None:
    data = minimal_module_data()
    module = load_library_json([data]).modules[0]
    assert isinstance(module, ExerciseModule)
    assert module.sources == ("NICE NG222 depression in adults (2022)",)
