"""Tests for ``reframe.safety.audit`` — the pre-specified crisis-query audit harness."""

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from reframe.safety.audit import MINIMUM_CRISIS_RECALL, AuditReport, run_crisis_audit
from reframe.safety.classifier import classify_input
from reframe.safety.types import VerdictLevel

_CORPUS_PATH = Path(__file__).parent / "data" / "audit_corpus.json"


def _corpus_rows() -> list[tuple[str, str]]:
    raw = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    return [(row["text"], row["expected_class"]) for row in raw]


def test_pre_specified_minimum_crisis_recall_is_one() -> None:
    assert MINIMUM_CRISIS_RECALL == 1.0


# ---------------------------------------------------------------------------
# Corpus audit: perfect recall, zero misses, zero neutral high-risk
# ---------------------------------------------------------------------------


def test_corpus_audit_reports_perfect_crisis_recall() -> None:
    report = run_crisis_audit(_corpus_rows())
    assert report.recall == MINIMUM_CRISIS_RECALL
    assert report.recall == 1.0
    assert report.misses == ()
    assert report.neutral_high_risk == 0


def test_corpus_audit_counts_are_consistent() -> None:
    rows = _corpus_rows()
    report = run_crisis_audit(rows)

    expected_crisis_total = sum(1 for _, cls in rows if cls == "crisis")
    expected_review_count = sum(
        1 for text, _ in rows if classify_input(text).level is VerdictLevel.REVIEW
    )

    assert report.total == len(rows)
    assert report.crisis_total == expected_crisis_total
    assert report.crisis_total > 0
    assert report.flagged_crisis == report.crisis_total
    assert report.review_count == expected_review_count
    assert report.review_count > 0
    assert report.recall == report.flagged_crisis / report.crisis_total


# ---------------------------------------------------------------------------
# Harness arithmetic: empty input, misses, neutral high-risk flags
# ---------------------------------------------------------------------------


def test_empty_sequence_yields_recall_of_one() -> None:
    report = run_crisis_audit([])
    assert report.total == 0
    assert report.crisis_total == 0
    assert report.flagged_crisis == 0
    assert report.misses == ()
    assert report.recall == 1.0
    assert report.neutral_high_risk == 0
    assert report.review_count == 0


def test_unflagged_crisis_text_is_reported_as_a_miss() -> None:
    report = run_crisis_audit([("just a totally normal afternoon", "crisis")])
    assert report.crisis_total == 1
    assert report.flagged_crisis == 0
    assert report.misses == ("just a totally normal afternoon",)
    assert report.recall == 0.0


def test_high_risk_flag_on_none_class_text_counts_as_neutral_high_risk() -> None:
    report = run_crisis_audit([("I want to die", "none")])
    assert report.neutral_high_risk == 1
    assert report.misses == ()
    assert report.crisis_total == 0
    assert report.recall == 1.0


def test_partial_report_arithmetic() -> None:
    rows = [
        ("I want to die", "crisis"),
        ("a totally ordinary day", "crisis"),
        ("I want to die", "none"),
        ("I need to process my memories", "trauma"),
        ("just work stress", "none"),
    ]
    report = run_crisis_audit(rows)
    assert report.total == 5
    assert report.crisis_total == 2
    assert report.flagged_crisis == 1
    assert report.misses == ("a totally ordinary day",)
    assert report.recall == 0.5
    assert report.neutral_high_risk == 1
    assert report.review_count == 1


# ---------------------------------------------------------------------------
# Report surface
# ---------------------------------------------------------------------------


def test_report_is_frozen() -> None:
    report = run_crisis_audit([])
    with pytest.raises(FrozenInstanceError):
        report.total = 1  # type: ignore[misc]


def test_report_field_names_match_the_specification() -> None:
    report = run_crisis_audit([])
    assert (
        report.total,
        report.crisis_total,
        report.flagged_crisis,
        report.misses,
        report.recall,
        report.neutral_high_risk,
        report.review_count,
    ) == (0, 0, 0, (), 1.0, 0, 0)
    assert isinstance(report, AuditReport)
