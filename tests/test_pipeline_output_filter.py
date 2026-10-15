"""Tests for ``reframe.pipeline.output_filter`` — Layer 5, what the MODEL produced.

Deterministic output safety: regex rule families over generated text plus a
reuse of the input classifier (the model must never emit crisis-level
content). No model calls, no I/O — identical text must yield an identical
:class:`OutputVerdict`.
"""

import re
from dataclasses import FrozenInstanceError

import pytest

from reframe.pipeline.messages import FILTER_FALLBACK, SCRIPTED
from reframe.pipeline.output_filter import OUTPUT_RULES, filter_output

SAFETY_REUSE_MARKER = "SAFETY-REUSE-HIGH-RISK"
FALLBACK_ID = "filter_fallback_v1"

# One triggering example per required rule family: (family prefix, example).
FAMILY_EXAMPLES: tuple[tuple[str, str], ...] = (
    ("OUT-DX", "You might have depression."),
    ("OUT-DX", "You are clearly depressed."),
    ("OUT-TX", "You should take medication for this."),
    ("OUT-TX", "You should probably increase your dose."),
    ("OUT-CRED", "As a therapist, I know exactly what this is."),
    ("OUT-CRED", "Trust me, I'm a licensed professional."),
    ("OUT-RISK", "Your risk level is high right now."),
    ("OUT-RISK", "You are high risk for burnout."),
    ("OUT-SYC", "There is nothing wrong with you, honestly."),
    ("OUT-SYC", "Don't worry, you're fine."),
)

BENIGN_WELLNESS_TEXT = (
    "That sounds like a heavy day. Would you like to try a quiet breathing exercise, "
    "or would you prefer I just listen for a while?"
)

CRISIS_MODEL_OUTPUT = "many people want to die sometimes"


# ---------------------------------------------------------------------------
# Rule table shape
# ---------------------------------------------------------------------------


def test_output_rules_is_a_non_empty_tuple_of_id_and_case_insensitive_patterns() -> None:
    assert isinstance(OUTPUT_RULES, tuple)
    assert len(OUTPUT_RULES) >= 5  # at least one rule per required family
    seen_ids: set[str] = set()
    for rule_id, pattern in OUTPUT_RULES:
        assert isinstance(rule_id, str) and rule_id
        assert rule_id not in seen_ids
        seen_ids.add(rule_id)
        assert pattern.flags & re.IGNORECASE


def test_output_rules_cover_every_required_family() -> None:
    rule_families = {f"OUT-{rule_id.split('-')[1]}" for rule_id, _pattern in OUTPUT_RULES}
    for family_prefix, _example in FAMILY_EXAMPLES:
        assert family_prefix in rule_families


# ---------------------------------------------------------------------------
# Each rule family blocks: violations non-empty, fallback id set
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("family_prefix", "example"), FAMILY_EXAMPLES)
def test_each_rule_family_blocks_its_example(family_prefix: str, example: str) -> None:
    verdict = filter_output(example)
    assert verdict.passed is False
    assert verdict.violations
    assert any(v.startswith(family_prefix) for v in verdict.violations)
    assert verdict.fallback_message_id == FALLBACK_ID


def test_pattern_matching_is_case_insensitive() -> None:
    verdict = filter_output("AS A DOCTOR, I WOULD KNOW.")
    assert verdict.passed is False
    assert verdict.violations


def test_multiple_violations_are_reported_sorted() -> None:
    verdict = filter_output("You have depression. As a therapist I would know.")
    assert verdict.passed is False
    assert verdict.violations == ("OUT-CRED-AS-A", "OUT-DX-YOU-HAVE")
    assert list(verdict.violations) == sorted(verdict.violations)


# ---------------------------------------------------------------------------
# Reuse of the input classifier: model output must never be crisis-level
# ---------------------------------------------------------------------------


def test_crisis_level_model_output_is_blocked_via_safety_reuse_marker() -> None:
    verdict = filter_output(CRISIS_MODEL_OUTPUT)
    assert verdict.passed is False
    assert verdict.violations == (SAFETY_REUSE_MARKER,)
    assert verdict.fallback_message_id == FALLBACK_ID


def test_rule_violation_and_safety_marker_are_reported_together_sorted() -> None:
    verdict = filter_output("You have depression and many people want to die sometimes.")
    assert verdict.passed is False
    assert verdict.violations == ("OUT-DX-YOU-HAVE", SAFETY_REUSE_MARKER)


def test_review_level_reuse_alone_does_not_block_only_high_risk_does() -> None:
    # Spec: blocked on rule match OR HIGH_RISK only — REVIEW-level reuse passes.
    verdict = filter_output("Sometimes the flashbacks come back at night and I sit awake.")
    assert verdict.passed is True
    assert verdict.violations == ()
    assert verdict.fallback_message_id is None


# ---------------------------------------------------------------------------
# Benign supportive wellness text passes
# ---------------------------------------------------------------------------


def test_benign_supportive_wellness_text_passes() -> None:
    verdict = filter_output(BENIGN_WELLNESS_TEXT)
    assert verdict.passed is True
    assert verdict.violations == ()
    assert verdict.fallback_message_id is None


# ---------------------------------------------------------------------------
# Boundaries, immutability, determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, 42, ["text"]])
def test_non_str_input_raises_type_error(bad: object) -> None:
    with pytest.raises(TypeError):
        filter_output(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("blank", ["", "   ", "\n\t"])
def test_empty_or_whitespace_input_raises_value_error(blank: str) -> None:
    with pytest.raises(ValueError):
        filter_output(blank)


def test_output_verdict_is_frozen() -> None:
    verdict = filter_output(BENIGN_WELLNESS_TEXT)
    with pytest.raises(FrozenInstanceError):
        verdict.passed = False  # type: ignore[misc]


def test_filter_output_is_deterministic() -> None:
    first = filter_output("You should take medication.")
    second = filter_output("You should take medication.")
    assert first == second
    assert first is not second


def test_fallback_message_id_matches_the_scripted_fallback_catalog_entry() -> None:
    # Cross-layer contract: a blocked verdict points at the cataloged fallback.
    verdict = filter_output("You should take medication.")
    assert verdict.fallback_message_id is not None
    assert verdict.fallback_message_id == FILTER_FALLBACK.message_id
    assert SCRIPTED[verdict.fallback_message_id] is FILTER_FALLBACK
