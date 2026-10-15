"""Deterministic, tiered retrieval of exercise modules for matched text.

Selection policy (fixed, no I/O, no randomness): for each matched category —
in :class:`~reframe.content.schema.ExerciseCategory` declaration order — take
up to ``max_per_category`` modules that are ``SELF_HELP_SAFE``, ordered by
evidence tier (A, then B, then C) and then by id. ``REFERRAL_ONLY`` modules
are never selected.
"""

from dataclasses import dataclass

from reframe.content.library import ContentLibrary
from reframe.content.matching import MATCH_RULES, match_categories
from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)

#: Fixed tier ranking used as the primary sort key: strongest evidence first.
TIER_RANK: dict[EvidenceTier, int] = {
    EvidenceTier.A: 0,
    EvidenceTier.B: 1,
    EvidenceTier.C: 2,
}


@dataclass(frozen=True)
class RetrievalResult:
    """Immutable outcome of one retrieval: what matched and what was served."""

    categories: tuple[ExerciseCategory, ...]
    modules: tuple[ExerciseModule, ...]
    matched_rule_ids: tuple[str, ...]


def retrieve(
    text: str,
    library: ContentLibrary,
    max_per_category: int = 2,
) -> RetrievalResult:
    """Deterministically retrieve self-help modules for ``text``.

    Args:
        text: Raw user-disclosed text.
        library: The validated content library to select from.
        max_per_category: Cap on served modules per matched category (>= 1).

    Returns:
        The matched categories (enum order), the selected ``SELF_HELP_SAFE``
        modules (tier A first, then B, then C, then id), and the ids of every
        rule that fired — all empty when nothing matched.

    Raises:
        TypeError: If ``text`` is not a ``str``.
        ValueError: If ``text`` is empty/whitespace-only, or
            ``max_per_category`` is less than 1.
    """
    categories = match_categories(text)
    if max_per_category < 1:
        raise ValueError(f"retrieve() requires max_per_category >= 1, got {max_per_category!r}")

    stripped = text.strip()
    matched_rule_ids = tuple(
        rule_id for _category, rule_id, pattern in MATCH_RULES if pattern.search(stripped)
    )

    modules: list[ExerciseModule] = []
    for category in categories:
        candidates = [
            module
            for module in library.modules
            if module.category is category and module.safety_class is SafetyClass.SELF_HELP_SAFE
        ]
        candidates.sort(key=lambda module: (TIER_RANK[module.tier], module.id))
        modules.extend(candidates[:max_per_category])

    return RetrievalResult(
        categories=categories,
        modules=tuple(modules),
        matched_rule_ids=matched_rule_ids,
    )
