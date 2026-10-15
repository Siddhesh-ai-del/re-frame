"""Tests for ``reframe.content.matching`` — deterministic, rule-based category matching."""

import re

import pytest

from reframe.content.matching import MATCH_RULES, match_categories
from reframe.content.schema import ExerciseCategory

# One dedicated probe string per rule id; every rule must be exercised by at
# least one of these (asserted below against MATCH_RULES).
RULE_PROBES: dict[str, str] = {
    "RUM-RUMINATING": "I keep ruminating on what went wrong yesterday.",
    "RUM-CANT-STOP-THINKING": "I can't stop thinking about that conversation.",
    "RUM-OVERTHINK": "I overthink every little decision.",
    "RUM-GOING-ROUND": "It keeps going round in my head all day.",
    "RUM-SAME-THOUGHTS": "The same thoughts over and over, hour after hour.",
    "BA-NO-MOTIVATION": "I have no motivation to do anything today.",
    "BA-STOPPED-DOING": "I've stopped doing things I used to enjoy.",
    "BA-HAVENT-BEEN-DOING": "I haven't been doing anything I normally like.",
    "BA-JUST-LYING-AROUND": "I spend the whole day just lying around.",
    "BA-CANT-GET-MYSELF": "I can't get myself to eat a proper meal.",
    "BA-NOTHING-WORTH": "It feels like nothing feels worth doing anymore.",
    "SC-HATING-MYSELF": "I keep hating myself for what I said.",
    "SC-SELF-CRITICAL": "I am so self-critical after every mistake.",
    "SC-SO-HARD-ON-MYSELF": "I'm so hard on myself constantly.",
    "SC-NOT-GOOD-ENOUGH": "I am not good enough for anyone, never am.",
    "SC-BLAMING-MYSELF": "I keep blaming myself for the whole thing.",
    "ER-CANT-CALM": "I can't calm down no matter what I try.",
    "ER-OVERWHELM": "I feel completely overwhelmed by everything.",
    "ER-CANT-COPE": "I can't cope with this week.",
    "ER-CANT-HANDLE": "I can't handle it anymore.",
    "ER-SO-ANXIOUS": "I am so anxious right now.",
    "ER-SPIRALING": "My thoughts are spiraling again tonight.",
}


def _rules_by_id() -> dict[str, tuple[ExerciseCategory, re.Pattern[str]]]:
    return {rule_id: (category, pattern) for category, rule_id, pattern in MATCH_RULES}


# ---------------------------------------------------------------------------
# Rule table integrity
# ---------------------------------------------------------------------------


def test_rule_ids_are_unique() -> None:
    rule_ids = [rule_id for _, rule_id, _ in MATCH_RULES]
    assert len(rule_ids) == len(set(rule_ids))


def test_rules_are_compiled_case_insensitive_patterns_with_enum_categories() -> None:
    assert MATCH_RULES
    for category, rule_id, pattern in MATCH_RULES:
        assert isinstance(category, ExerciseCategory)
        assert rule_id
        assert isinstance(pattern, re.Pattern)
        assert pattern.flags & re.IGNORECASE, rule_id


def test_every_rule_has_a_dedicated_probe_string() -> None:
    rule_ids = {rule_id for _, rule_id, _ in MATCH_RULES}
    assert rule_ids == set(RULE_PROBES), f"probes missing for: {rule_ids - set(RULE_PROBES)}"


@pytest.mark.parametrize(
    ("rule_id", "probe"),
    sorted(RULE_PROBES.items()),
)
def test_every_rule_is_matched_by_its_probe(rule_id: str, probe: str) -> None:
    category, pattern = _rules_by_id()[rule_id]
    assert pattern.search(probe), f"rule {rule_id} ({category.value}) never matched {probe!r}"


def test_rule_table_covers_every_required_phrase_bullet() -> None:
    """Each spec bullet phrase must be detected by at least one probe case."""
    bullets = {
        ExerciseCategory.RUMINATION: [
            "ruminat",
            "can't stop thinking",
            "overthink",
            "going round in my head",
            "same thoughts over and over",
        ],
        ExerciseCategory.BEHAVIORAL_ACTIVATION: [
            "no motivation",
            "stopped doing",
            "haven't been doing",
            "just lying around",
            "can't get myself to",
            "nothing feels worth",
        ],
        ExerciseCategory.SELF_COMPASSION: [
            "hating myself",
            "self-critical",
            "so hard on myself",
            "not good enough",
            "blaming myself",
        ],
        ExerciseCategory.EMOTION_REGULATION: [
            "can't calm",
            "overwhelm",
            "can't cope",
            "can't handle",
            "so anxious",
            "spiraling",
        ],
    }
    probes = list(RULE_PROBES.values())
    for category, phrases in bullets.items():
        rules = [pattern for cat, _rule_id, pattern in MATCH_RULES if cat is category]
        assert rules, f"no rules declared for {category.value}"
        for phrase in phrases:
            probe_hit = any(phrase in probe for probe in probes)
            assert probe_hit, f"no probe string contains bullet phrase {phrase!r}"
            assert any(pattern.search(phrase) for pattern in rules), (
                f"{category.value}: no rule matches bullet phrase {phrase!r}"
            )


# ---------------------------------------------------------------------------
# match_categories(): behavior
# ---------------------------------------------------------------------------


def test_single_category_text_matches_once() -> None:
    assert match_categories("I keep ruminating on yesterday") == (ExerciseCategory.RUMINATION,)


def test_multi_category_text_returns_both_in_enum_declaration_order() -> None:
    # EMOTION_REGULATION phrase appears first in the text; enum order must win.
    result = match_categories("I feel so anxious and I can't stop thinking about it")
    assert result == (ExerciseCategory.RUMINATION, ExerciseCategory.EMOTION_REGULATION)


def test_all_four_categories_returned_in_enum_order() -> None:
    text = (
        "I am so hard on myself, nothing feels worth doing, I can't calm down and I keep ruminating"
    )
    assert match_categories(text) == (
        ExerciseCategory.RUMINATION,
        ExerciseCategory.BEHAVIORAL_ACTIVATION,
        ExerciseCategory.SELF_COMPASSION,
        ExerciseCategory.EMOTION_REGULATION,
    )


def test_multiple_rules_of_one_category_deduplicate() -> None:
    text = "I keep ruminating, I overthink everything, going round in my head"
    assert match_categories(text) == (ExerciseCategory.RUMINATION,)


def test_matching_is_case_insensitive() -> None:
    assert match_categories("I KEEP RUMINATING ABOUT IT") == (ExerciseCategory.RUMINATION,)


def test_surrounding_whitespace_is_ignored() -> None:
    assert match_categories("  \n\t overthink everything \t\n ") == (ExerciseCategory.RUMINATION,)


def test_curly_apostrophes_are_matched() -> None:
    assert match_categories("I can’t stop thinking about it") == (ExerciseCategory.RUMINATION,)


def test_text_matching_nothing_returns_empty_tuple() -> None:
    assert match_categories("What is the weather going to be like tomorrow?") == ()


def test_matching_is_deterministic_across_calls() -> None:
    text = "I can't calm down and I keep hating myself"
    assert match_categories(text) == match_categories(text)


@pytest.mark.parametrize(
    "bad",
    [None, 7, [], {}, object()],
    ids=["none", "int", "list", "dict", "object"],
)
def test_non_string_input_raises_type_error(bad: object) -> None:
    with pytest.raises(TypeError):
        match_categories(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n \r\t"])
def test_empty_or_whitespace_only_input_raises_value_error(blank: str) -> None:
    with pytest.raises(ValueError):
        match_categories(blank)
