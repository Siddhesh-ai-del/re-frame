"""Value types for the evidence-tiered exercise content library.

Modules are immutable, self-validating records: every field is checked in
:data:`ExerciseModule.__post_init__`, and any invalid value raises a
``ValueError`` that names the offending field and value (fail-closed —
corrupt content never reaches the user).
"""

import re
from dataclasses import dataclass
from enum import Enum

#: Module ids are lowercase slug fragments: ``^[a-z0-9-]+$``.
ID_PATTERN = re.compile(r"^[a-z0-9-]+$")


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class EvidenceTier(str, Enum):  # noqa: UP042
    """Evidence grade, declared strongest first: A, then B, then C."""

    A = "A"
    B = "B"
    C = "C"


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class ExerciseCategory(str, Enum):  # noqa: UP042
    """Wellness lanes, declared in fixed presentation order."""

    RUMINATION = "rumination"
    BEHAVIORAL_ACTIVATION = "behavioral_activation"
    SELF_COMPASSION = "self_compassion"
    EMOTION_REGULATION = "emotion_regulation"


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class SafetyClass(str, Enum):  # noqa: UP042
    """Whether a module may be served as self-help or only referred outward."""

    SELF_HELP_SAFE = "self_help_safe"
    REFERRAL_ONLY = "referral_only"


def _require_non_empty_str(value: object, field_name: str) -> str:
    """Return ``value`` if it is a non-blank string; else raise naming ``field_name``."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"ExerciseModule.{field_name}: {value!r} must be a non-empty string")
    return value


def _require_str_tuple(value: object, field_name: str) -> tuple[str, ...]:
    """Return ``value`` if it is a tuple of non-blank strings; else raise naming ``field_name``."""
    if not isinstance(value, tuple):
        raise ValueError(
            f"ExerciseModule.{field_name}: expected tuple[str, ...], got {type(value).__name__}"
        )
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"ExerciseModule.{field_name}[{index}]: {item!r} must be a non-empty string"
            )
    return value


@dataclass(frozen=True)
class ExerciseModule:
    """One curated, evidence-tiered self-help exercise module.

    Validation is fail-closed: a module with an invalid id, blank text,
    too few steps, no sources, or a non-enum classification raises
    ``ValueError`` naming the offending field and value.
    """

    id: str
    title: str
    summary: str
    category: ExerciseCategory
    tier: EvidenceTier
    safety_class: SafetyClass
    steps: tuple[str, ...]
    sources: tuple[str, ...]
    early_worsening_notice: bool = True
    contraindications: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not ID_PATTERN.match(self.id):
            raise ValueError(f"ExerciseModule.id: {self.id!r} does not match ^[a-z0-9-]+$")
        _require_non_empty_str(self.title, "title")
        _require_non_empty_str(self.summary, "summary")
        if not isinstance(self.category, ExerciseCategory):
            raise ValueError(
                f"ExerciseModule.category: {self.category!r} is not an ExerciseCategory"
            )
        if not isinstance(self.tier, EvidenceTier):
            raise ValueError(f"ExerciseModule.tier: {self.tier!r} is not an EvidenceTier")
        if not isinstance(self.safety_class, SafetyClass):
            raise ValueError(
                f"ExerciseModule.safety_class: {self.safety_class!r} is not a SafetyClass"
            )
        steps = _require_str_tuple(self.steps, "steps")
        if len(steps) < 2:
            raise ValueError(f"ExerciseModule.steps: need at least 2 steps, got {len(steps)}")
        sources = _require_str_tuple(self.sources, "sources")
        if not sources:
            raise ValueError("ExerciseModule.sources: at least 1 source is required")
        _require_str_tuple(self.contraindications, "contraindications")
