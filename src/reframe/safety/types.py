"""Value types for the deterministic input safety layer.

Verdict levels follow a fixed precedence — ``HIGH_RISK`` > ``REVIEW`` >
``NORMAL`` — and signals are normalized (deduplicated and sorted) against
:data:`SIGNAL_PRECEDENCE` whenever a :class:`SafetyVerdict` is constructed.
"""

from dataclasses import dataclass
from enum import Enum


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class SignalType(str, Enum):  # noqa: UP042
    """Categories of disclosed content the rule set can detect."""

    CRISIS = "crisis"
    PSYCHOSIS_OR_MANIA = "psychosis_mania"
    TRAUMA_PROCESSING = "trauma"
    DIAGNOSIS_SEEKING = "diagnosis"


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class VerdictLevel(str, Enum):  # noqa: UP042
    """Verdict severity, declared in precedence order: HIGH_RISK > REVIEW > NORMAL."""

    HIGH_RISK = "high_risk"
    REVIEW = "review"
    NORMAL = "normal"


#: Fixed signal ordering: most severe signal class first.
SIGNAL_PRECEDENCE: tuple[SignalType, ...] = (
    SignalType.CRISIS,
    SignalType.PSYCHOSIS_OR_MANIA,
    SignalType.TRAUMA_PROCESSING,
    SignalType.DIAGNOSIS_SEEKING,
)


@dataclass(frozen=True)
class SafetyVerdict:
    """Immutable classification result for one user input.

    ``signals`` is normalized on construction: values outside
    :data:`SIGNAL_PRECEDENCE` are dropped, duplicates removed, and the rest
    sorted by the fixed precedence order. The verdict only reflects disclosed
    text — it is never a risk *score* of the person.
    """

    level: VerdictLevel
    signals: tuple[SignalType, ...]

    def __post_init__(self) -> None:
        ordered = tuple(signal for signal in SIGNAL_PRECEDENCE if signal in self.signals)
        object.__setattr__(self, "signals", ordered)

    @property
    def requires_hard_bypass(self) -> bool:
        """True only for :attr:`VerdictLevel.HIGH_RISK` (fail-closed bypass)."""
        return self.level is VerdictLevel.HIGH_RISK
