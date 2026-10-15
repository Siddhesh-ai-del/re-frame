"""Content library assembly: validated JSON in, immutable library out.

``load_library_json`` is fail-closed — one bad item aborts the whole load
with a ``ValueError`` naming the offending module — and ``default_library``
caches a single shared instance of the packaged corpus. A missing or corrupt
package file propagates its error; it never silently yields an empty library.
"""

import importlib.resources as resources
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)

#: Keys every JSON module object must carry (optional: ``early_worsening_notice``,
#: ``contraindications`` — both have dataclass defaults).
REQUIRED_KEYS: tuple[str, ...] = (
    "id",
    "title",
    "summary",
    "category",
    "tier",
    "safety_class",
    "steps",
    "sources",
)


@dataclass(frozen=True)
class ContentLibrary:
    """An immutable, queryable set of validated exercise modules."""

    modules: tuple[ExerciseModule, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        """Module ids in declaration order."""
        return tuple(module.id for module in self.modules)

    def by_id(self, module_id: str) -> ExerciseModule:
        """Return the module with ``module_id``.

        Raises:
            ValueError: If no module carries ``module_id`` (the id is named
                in the message).
        """
        for module in self.modules:
            if module.id == module_id:
                return module
        raise ValueError(f"no module with id {module_id!r}")

    def by_category(self, category: ExerciseCategory) -> tuple[ExerciseModule, ...]:
        """Return every module in ``category``, in declaration order."""
        return tuple(module for module in self.modules if module.category is category)


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    """Coerce a JSON list into a string tuple, or raise naming ``field_name``."""
    if not isinstance(value, list | tuple):
        raise ValueError(
            f"{field_name}: expected a JSON list of strings, got {type(value).__name__}"
        )
    return tuple(value)


def _module_from_json(item: dict[Any, Any]) -> ExerciseModule:
    """Build one :class:`ExerciseModule` from a JSON object; raise ``ValueError`` on bad values."""
    return ExerciseModule(
        id=item["id"],
        title=item["title"],
        summary=item["summary"],
        category=ExerciseCategory(item["category"]),
        tier=EvidenceTier(item["tier"]),
        safety_class=SafetyClass(item["safety_class"]),
        steps=_string_tuple(item["steps"], "steps"),
        sources=_string_tuple(item["sources"], "sources"),
        early_worsening_notice=item.get("early_worsening_notice", True),
        contraindications=_string_tuple(item.get("contraindications", ()), "contraindications"),
    )


def load_library_json(data: Any) -> ContentLibrary:
    """Validate parsed JSON (a list of module objects) into a :class:`ContentLibrary`.

    Every item is constructed and validated; one bad item aborts the load
    (fail-closed) with a ``ValueError`` naming the module's id (or its index
    when no id is present). Duplicate ids are rejected.

    Raises:
        ValueError: If ``data`` is not a list, or any item is invalid.
    """
    if not isinstance(data, list):
        raise ValueError(
            f"load_library_json() requires a JSON list of modules, got {type(data).__name__}"
        )
    modules: list[ExerciseModule] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"module at index {index} is not a JSON object: {item!r}")
        module_id = item.get("id")
        label = module_id if isinstance(module_id, str) else f"index {index}"
        missing = [key for key in REQUIRED_KEYS if key not in item]
        if missing:
            raise ValueError(f"module {label!r} missing required key(s): {', '.join(missing)}")
        try:
            module = _module_from_json(item)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"invalid module {label!r}: {exc}") from exc
        if module.id in seen_ids:
            raise ValueError(f"duplicate module id {module.id!r}")
        seen_ids.add(module.id)
        modules.append(module)
    return ContentLibrary(modules=tuple(modules))


@lru_cache(maxsize=1)
def default_library() -> ContentLibrary:
    """Return the packaged library as one shared, cached instance.

    Raises whatever the packaged data raises — a missing or corrupt
    ``exercises.json`` fails closed and never returns an empty library.
    """
    data_path = resources.files("reframe.content").joinpath("data").joinpath("exercises.json")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    return load_library_json(data)
