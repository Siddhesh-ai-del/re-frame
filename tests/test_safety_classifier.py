"""Tests for ``reframe.safety.classifier`` — deterministic, rule-based signal routing."""

import json
import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from reframe.safety import classifier
from reframe.safety.classifier import RULES, classify_input
from reframe.safety.types import (
    SIGNAL_PRECEDENCE,
    SafetyVerdict,
    SignalType,
    VerdictLevel,
)

_CORPUS_PATH = Path(__file__).parent / "data" / "audit_corpus.json"

EXPECTED_LEVEL = {
    "crisis": VerdictLevel.HIGH_RISK,
    "psychosis_mania": VerdictLevel.HIGH_RISK,
    "trauma": VerdictLevel.REVIEW,
    "diagnosis": VerdictLevel.REVIEW,
    "none": VerdictLevel.NORMAL,
}

MINIMUM_CORPUS_SIZES = {
    "crisis": 12,
    "psychosis_mania": 4,
    "trauma": 4,
    "diagnosis": 4,
    "none": 12,
}


def _corpus() -> list[dict[str, str]]:
    raw = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    return raw


def _corpus_rows() -> list[tuple[str, str]]:
    return [(row["text"], row["expected_class"]) for row in _corpus()]


# ---------------------------------------------------------------------------
# Corpus integrity
# ---------------------------------------------------------------------------


def test_corpus_rows_have_exactly_the_expected_shape() -> None:
    for row in _corpus():
        assert set(row) == {"text", "expected_class"}
        assert row["expected_class"] in EXPECTED_LEVEL
        assert row["text"].strip()


def test_corpus_meets_minimum_class_sizes() -> None:
    counts = {cls: 0 for cls in MINIMUM_CORPUS_SIZES}
    for _, expected in _corpus_rows():
        counts[expected] += 1
    for cls, minimum in MINIMUM_CORPUS_SIZES.items():
        assert counts[cls] >= minimum, f"{cls}: {counts[cls]} < {minimum}"


# ---------------------------------------------------------------------------
# Corpus-driven routing: every case lands on its expected level
# ---------------------------------------------------------------------------

_CORPUS_IDS = [row["text"] for row in _corpus()]


@pytest.mark.parametrize(
    ("text", "expected_class"),
    _corpus_rows(),
    ids=_CORPUS_IDS,
)
def test_corpus_case_routes_to_expected_level(text: str, expected_class: str) -> None:
    verdict = classify_input(text)
    assert verdict.level is EXPECTED_LEVEL[expected_class], (
        f"{text!r} -> {verdict.level.value}, expected {expected_class}"
    )


@pytest.mark.parametrize(
    ("signal", "rule_id", "pattern"),
    RULES,
    ids=[rule_id for _, rule_id, _ in RULES],
)
def test_every_rule_is_triggered_by_at_least_one_corpus_case(
    signal: SignalType,
    rule_id: str,
    pattern: re.Pattern[str],
) -> None:
    assert any(pattern.search(text) for text, _ in _corpus_rows()), (
        f"rule {rule_id} ({signal.value}) never matched the corpus"
    )


def test_rule_ids_are_unique() -> None:
    rule_ids = [rule_id for _, rule_id, _ in RULES]
    assert len(rule_ids) == len(set(rule_ids))


def test_rules_are_compiled_case_insensitive_patterns() -> None:
    assert RULES
    for signal, rule_id, pattern in RULES:
        assert isinstance(signal, SignalType)
        assert rule_id
        assert pattern.flags & re.IGNORECASE, rule_id


# ---------------------------------------------------------------------------
# Boundary validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [None, 7, [], {}, object()],
    ids=["none", "int", "list", "dict", "object"],
)
def test_non_string_input_raises_type_error(bad: object) -> None:
    with pytest.raises(TypeError):
        classify_input(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n \r\t"])
def test_empty_or_whitespace_only_input_raises_value_error(blank: str) -> None:
    with pytest.raises(ValueError):
        classify_input(blank)


# ---------------------------------------------------------------------------
# Signal collection: precedence order, deduplication, multi-signal inputs
# ---------------------------------------------------------------------------


def test_crisis_plus_trauma_reports_both_signals_in_precedence_order() -> None:
    verdict = classify_input("I want to die and my trauma keeps coming back")
    assert verdict.level is VerdictLevel.HIGH_RISK
    assert verdict.signals == (SignalType.CRISIS, SignalType.TRAUMA_PROCESSING)


def test_crisis_plus_psychosis_reports_both_signals() -> None:
    verdict = classify_input("I hear voices and I want to die")
    assert verdict.level is VerdictLevel.HIGH_RISK
    assert verdict.signals == (SignalType.CRISIS, SignalType.PSYCHOSIS_OR_MANIA)


def test_multiple_rules_of_one_signal_deduplicate_to_a_single_signal() -> None:
    verdict = classify_input("I want to die and I want to end my life")
    assert verdict.level is VerdictLevel.HIGH_RISK
    assert verdict.signals == (SignalType.CRISIS,)


def test_signal_precedence_order_is_fixed() -> None:
    assert SIGNAL_PRECEDENCE == (
        SignalType.CRISIS,
        SignalType.PSYCHOSIS_OR_MANIA,
        SignalType.TRAUMA_PROCESSING,
        SignalType.DIAGNOSIS_SEEKING,
    )


def test_verdict_normalizes_unsorted_and_duplicate_signals_on_construction() -> None:
    verdict = SafetyVerdict(
        level=VerdictLevel.REVIEW,
        signals=(
            SignalType.DIAGNOSIS_SEEKING,
            SignalType.TRAUMA_PROCESSING,
            SignalType.DIAGNOSIS_SEEKING,
        ),
    )
    assert verdict.signals == (
        SignalType.TRAUMA_PROCESSING,
        SignalType.DIAGNOSIS_SEEKING,
    )


def test_verdict_with_no_signals_keeps_empty_tuple() -> None:
    assert SafetyVerdict(level=VerdictLevel.NORMAL, signals=()).signals == ()


# ---------------------------------------------------------------------------
# Determinism and verdict surface
# ---------------------------------------------------------------------------


def test_identical_input_yields_identical_verdicts() -> None:
    assert classify_input("I keep having suicidal thoughts") == classify_input(
        "I keep having suicidal thoughts"
    )
    assert classify_input("I feel hopeless") == classify_input("I feel hopeless")


def test_classification_is_case_insensitive() -> None:
    assert classify_input("I WANT TO KILL MYSELF").level is VerdictLevel.HIGH_RISK


def test_surrounding_whitespace_is_ignored() -> None:
    verdict = classify_input("   \n I want to die \t")
    assert verdict.level is VerdictLevel.HIGH_RISK


def test_verdict_is_frozen() -> None:
    verdict = classify_input("hello there")
    with pytest.raises(FrozenInstanceError):
        verdict.level = VerdictLevel.HIGH_RISK  # type: ignore[misc]


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (VerdictLevel.HIGH_RISK, True),
        (VerdictLevel.REVIEW, False),
        (VerdictLevel.NORMAL, False),
    ],
)
def test_requires_hard_bypass(level: VerdictLevel, expected: bool) -> None:
    assert SafetyVerdict(level=level, signals=()).requires_hard_bypass is expected


def test_classifier_docstring_documents_over_flag_stance() -> None:
    doc = classifier.__doc__ or ""
    assert "negation" in doc
    assert "over-flag" in doc


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------


def test_package_exports_public_safety_api() -> None:
    from reframe import safety

    for name in (
        "SignalType",
        "VerdictLevel",
        "SafetyVerdict",
        "classify_input",
        "EscalationAction",
        "EscalationDecision",
        "escalation_decision",
        "CrisisResource",
        "DEFAULT_CRISIS_RESOURCES",
        "AuditReport",
        "run_crisis_audit",
        "MINIMUM_CRISIS_RECALL",
    ):
        assert hasattr(safety, name), f"missing public export: {name}"
