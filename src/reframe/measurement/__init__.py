"""Measurement layer: free public instruments and fail-closed scoring.

Public surface: :data:`INSTRUMENTS` (the active registry of confirmed
free-to-use instruments), :data:`PENDING_VERIFICATION` (fail-closed
placeholders unreachable via :func:`get_instrument`), the spec
dataclasses, :func:`score`, and :func:`severity_for_total`.
"""

from reframe.measurement.instruments import (
    GAD7,
    INSTRUMENTS,
    K10,
    PENDING_VERIFICATION,
    PHQ9,
    SCS_SF,
    AnswerOption,
    InstrumentSpec,
    ItemSpec,
    SeverityBand,
    get_instrument,
)
from reframe.measurement.scoring import ScoreResult, score, severity_for_total

__all__ = [
    "GAD7",
    "INSTRUMENTS",
    "K10",
    "PHQ9",
    "PENDING_VERIFICATION",
    "SCS_SF",
    "AnswerOption",
    "InstrumentSpec",
    "ItemSpec",
    "ScoreResult",
    "SeverityBand",
    "get_instrument",
    "score",
    "severity_for_total",
]
