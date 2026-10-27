"""Packaged audit-corpus tests for ``reframe.safety.audit_corpus`` (stage 7b).

Strict TDD: written BEFORE ``reframe/safety/audit_corpus.py`` exists; the
first run must fail with an ``ImportError`` (RED).

The corpus is the operator-facing smoke probe behind ``--audit``. These tests
pin three properties at once:

- **Well-formedness** — every row is a ``(text, expected_class)`` pair with
  non-empty text and an expected class drawn from the classifier's five-name
  set, and the class coverage floors from the spec are met (>=3 crisis,
  >=2 psychosis_mania, >=1 trauma, >=1 diagnosis, >=3 none).
- **As-built agreement** — every row classifies exactly as expected under the
  CURRENT deterministic classifier (level + matching signal). If a row ever
  reveals a genuine miss, the fix is the corpus or a loud report to the lead
  — never weakening ``src/reframe/safety/*`` or
  ``MINIMUM_CRISIS_RECALL`` (E8).
- **The recall gate itself** — ``run_crisis_audit(AUDIT_CORPUS)`` has
  ``recall == 1.0`` (>= ``MINIMUM_CRISIS_RECALL``), zero misses, and zero
  ``none``-class rows flagged HIGH_RISK.
"""

from collections import Counter

from reframe.safety.audit import MINIMUM_CRISIS_RECALL, run_crisis_audit
from reframe.safety.audit_corpus import AUDIT_CORPUS
from reframe.safety.classifier import classify_input
from reframe.safety.types import SignalType, VerdictLevel

#: The five expected class names (mirrors ``run_crisis_audit``'s contract).
EXPECTED_CLASSES = {"crisis", "psychosis_mania", "trauma", "diagnosis", "none"}

#: Spec class-coverage floors for the ~12-row corpus.
CLASS_COVERAGE_FLOORS = {
    "crisis": 3,
    "psychosis_mania": 2,
    "trauma": 1,
    "diagnosis": 1,
    "none": 3,
}

#: expected class -> (required verdict level, required signal) per row.
CLASS_EXPECTATIONS: dict[str, tuple[VerdictLevel, SignalType | None]] = {
    "crisis": (VerdictLevel.HIGH_RISK, SignalType.CRISIS),
    "psychosis_mania": (VerdictLevel.HIGH_RISK, SignalType.PSYCHOSIS_OR_MANIA),
    "trauma": (VerdictLevel.REVIEW, SignalType.TRAUMA_PROCESSING),
    "diagnosis": (VerdictLevel.REVIEW, SignalType.DIAGNOSIS_SEEKING),
    "none": (VerdictLevel.NORMAL, None),
}


def test_corpus_is_a_non_empty_tuple_of_pairs() -> None:
    assert isinstance(AUDIT_CORPUS, tuple)
    assert len(AUDIT_CORPUS) >= 12
    for row in AUDIT_CORPUS:
        assert isinstance(row, tuple)
        assert len(row) == 2


def test_every_row_has_non_empty_text_and_a_known_class() -> None:
    for text, expected_class in AUDIT_CORPUS:
        assert isinstance(text, str)
        assert text.strip(), "probe text must be non-empty"
        assert expected_class in EXPECTED_CLASSES


def test_corpus_covers_every_class_at_the_specified_floors() -> None:
    counts = Counter(expected_class for _text, expected_class in AUDIT_CORPUS)
    for expected_class, floor in CLASS_COVERAGE_FLOORS.items():
        assert counts[expected_class] >= floor, f"{expected_class}: {counts[expected_class]}"


def test_every_row_classifies_exactly_as_expected() -> None:
    for text, expected_class in AUDIT_CORPUS:
        verdict = classify_input(text)
        level, signal = CLASS_EXPECTATIONS[expected_class]
        assert verdict.level is level, f"{expected_class!r} row {text!r} -> {verdict.level}"
        if signal is not None:
            assert signal in verdict.signals, (
                f"{expected_class!r} row {text!r} -> {verdict.signals}"
            )


def test_audit_over_the_packaged_corpus_meets_the_recall_gate() -> None:
    report = run_crisis_audit(AUDIT_CORPUS)
    assert report.recall == 1.0
    assert report.recall >= MINIMUM_CRISIS_RECALL
    assert report.misses == ()
    assert report.neutral_high_risk == 0
    assert report.total == len(AUDIT_CORPUS)
