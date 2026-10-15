"""Deterministic, rule-based matching of user text to exercise categories.

Every input is matched against :data:`MATCH_RULES` — compiled case-insensitive
regexes over the user's own words. There is no model call, randomness, or I/O:
identical input always yields the identical category tuple, in fixed
:data:`~reframe.content.schema.ExerciseCategory` declaration order.
"""

import re

from reframe.content.schema import ExerciseCategory

#: ``(category, rule_id, pattern)`` — every rule is case-insensitively compiled.
MATCH_RULES: tuple[tuple[ExerciseCategory, str, re.Pattern[str]], ...] = (
    # Rumination — the loop of repetitive, abstract self-focus
    (
        ExerciseCategory.RUMINATION,
        "RUM-RUMINATING",
        re.compile(r"ruminat\w*", re.IGNORECASE),
    ),
    (
        ExerciseCategory.RUMINATION,
        "RUM-CANT-STOP-THINKING",
        re.compile(r"can(?:['’]t|not) stop thinking", re.IGNORECASE),
    ),
    (
        ExerciseCategory.RUMINATION,
        "RUM-OVERTHINK",
        re.compile(r"overthink\w*", re.IGNORECASE),
    ),
    (
        ExerciseCategory.RUMINATION,
        "RUM-GOING-ROUND",
        re.compile(r"going (?:a)?round in my head", re.IGNORECASE),
    ),
    (
        ExerciseCategory.RUMINATION,
        "RUM-SAME-THOUGHTS",
        re.compile(r"same thoughts over and over", re.IGNORECASE),
    ),
    # Behavioral activation — withdrawal from doing
    (
        ExerciseCategory.BEHAVIORAL_ACTIVATION,
        "BA-NO-MOTIVATION",
        re.compile(r"(?:no|zero) motivation", re.IGNORECASE),
    ),
    (
        ExerciseCategory.BEHAVIORAL_ACTIVATION,
        "BA-STOPPED-DOING",
        re.compile(r"stop(?:ped)? doing", re.IGNORECASE),
    ),
    (
        ExerciseCategory.BEHAVIORAL_ACTIVATION,
        "BA-HAVENT-BEEN-DOING",
        re.compile(r"(?:haven['’]t|have not) been doing", re.IGNORECASE),
    ),
    (
        ExerciseCategory.BEHAVIORAL_ACTIVATION,
        "BA-JUST-LYING-AROUND",
        re.compile(r"just lying around", re.IGNORECASE),
    ),
    (
        ExerciseCategory.BEHAVIORAL_ACTIVATION,
        "BA-CANT-GET-MYSELF",
        re.compile(r"can(?:['’]t|not) get myself to", re.IGNORECASE),
    ),
    (
        ExerciseCategory.BEHAVIORAL_ACTIVATION,
        "BA-NOTHING-WORTH",
        re.compile(r"nothing feels worth", re.IGNORECASE),
    ),
    # Self-compassion — the harsh, isolating inner voice
    (
        ExerciseCategory.SELF_COMPASSION,
        "SC-HATING-MYSELF",
        re.compile(r"hat(?:e|es|ed|ing) myself", re.IGNORECASE),
    ),
    (
        ExerciseCategory.SELF_COMPASSION,
        "SC-SELF-CRITICAL",
        re.compile(r"self[-\s]critic\w*", re.IGNORECASE),
    ),
    (
        ExerciseCategory.SELF_COMPASSION,
        "SC-SO-HARD-ON-MYSELF",
        re.compile(r"so hard on myself", re.IGNORECASE),
    ),
    (
        ExerciseCategory.SELF_COMPASSION,
        "SC-NOT-GOOD-ENOUGH",
        re.compile(r"n(?:ot|ever) good enough", re.IGNORECASE),
    ),
    (
        ExerciseCategory.SELF_COMPASSION,
        "SC-BLAMING-MYSELF",
        re.compile(r"blam(?:e|es|ed|ing) myself", re.IGNORECASE),
    ),
    # Emotion regulation — acute arousal that feels unmanageable
    (
        ExerciseCategory.EMOTION_REGULATION,
        "ER-CANT-CALM",
        re.compile(r"can(?:['’]t|not) calm", re.IGNORECASE),
    ),
    (
        ExerciseCategory.EMOTION_REGULATION,
        "ER-OVERWHELM",
        re.compile(r"overwhelm\w*", re.IGNORECASE),
    ),
    (
        ExerciseCategory.EMOTION_REGULATION,
        "ER-CANT-COPE",
        re.compile(r"can(?:['’]t|not) cope", re.IGNORECASE),
    ),
    (
        ExerciseCategory.EMOTION_REGULATION,
        "ER-CANT-HANDLE",
        re.compile(r"can(?:['’]t|not) handle", re.IGNORECASE),
    ),
    (
        ExerciseCategory.EMOTION_REGULATION,
        "ER-SO-ANXIOUS",
        re.compile(r"so anxious", re.IGNORECASE),
    ),
    (
        ExerciseCategory.EMOTION_REGULATION,
        "ER-SPIRALING",
        re.compile(r"spiral(?:l)?ing", re.IGNORECASE),
    ),
)


def match_categories(text: str) -> tuple[ExerciseCategory, ...]:
    """Return every exercise category ``text`` matches, in enum declaration order.

    The result is deduplicated and ordered by :class:`ExerciseCategory`
    declaration order, so the same input always yields the same tuple.

    Args:
        text: Raw user-disclosed text.

    Returns:
        The matched categories in fixed order; empty when nothing matched.

    Raises:
        TypeError: If ``text`` is not a ``str``.
        ValueError: If ``text`` is empty or whitespace-only after stripping.
    """
    if not isinstance(text, str):
        raise TypeError(f"match_categories() requires str, got {type(text).__name__}")

    stripped = text.strip()
    if not stripped:
        raise ValueError("match_categories() requires non-empty text")

    matched: set[ExerciseCategory] = set()
    for category, _rule_id, pattern in MATCH_RULES:
        if pattern.search(stripped):
            matched.add(category)

    return tuple(category for category in ExerciseCategory if category in matched)
