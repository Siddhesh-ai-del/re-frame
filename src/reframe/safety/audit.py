"""Pre-specified crisis-query audit harness for the deterministic classifier.

Seeded-corpus audits must meet :data:`MINIMUM_CRISIS_RECALL` — every crisis
case is expected to be flagged ``HIGH_RISK``. A miss, or a ``HIGH_RISK`` flag
on a ``"none"`` case, is surfaced in the report so fail-closed regressions are
visible before the classifier is trusted.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from reframe.safety.classifier import classify_input
from reframe.safety.types import VerdictLevel

#: Pre-specified target: every seeded crisis case must be flagged HIGH_RISK.
MINIMUM_CRISIS_RECALL: float = 1.0


@dataclass(frozen=True)
class AuditReport:
    """Immutable outcome of one audit run."""

    total: int
    crisis_total: int
    flagged_crisis: int
    misses: tuple[str, ...]
    recall: float
    neutral_high_risk: int
    review_count: int


def run_crisis_audit(texts: Sequence[tuple[str, str]]) -> AuditReport:
    """Audit :func:`~reframe.safety.classifier.classify_input` over ``texts``.

    Each pair is ``(text, expected_class)`` where ``expected_class`` is one of
    ``{"crisis", "psychosis_mania", "trauma", "diagnosis", "none"}``.

    Returns:
        An :class:`AuditReport` where ``recall`` is
        ``flagged_crisis / crisis_total`` (``1.0`` when there are no crisis
        cases), ``misses`` lists crisis-class texts that were not flagged
        ``HIGH_RISK``, ``neutral_high_risk`` counts ``"none"``-class texts
        that were flagged ``HIGH_RISK``, and ``review_count`` counts texts at
        ``REVIEW`` level.
    """
    total = 0
    crisis_total = 0
    flagged_crisis = 0
    misses: list[str] = []
    neutral_high_risk = 0
    review_count = 0

    for text, expected_class in texts:
        verdict = classify_input(text)
        total += 1
        if verdict.level is VerdictLevel.REVIEW:
            review_count += 1
        if expected_class == "crisis":
            crisis_total += 1
            if verdict.level is VerdictLevel.HIGH_RISK:
                flagged_crisis += 1
            else:
                misses.append(text)
        elif expected_class == "none" and verdict.level is VerdictLevel.HIGH_RISK:
            neutral_high_risk += 1

    recall = flagged_crisis / crisis_total if crisis_total else 1.0
    return AuditReport(
        total=total,
        crisis_total=crisis_total,
        flagged_crisis=flagged_crisis,
        misses=tuple(misses),
        recall=recall,
        neutral_high_risk=neutral_high_risk,
        review_count=review_count,
    )
