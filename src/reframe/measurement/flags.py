"""Longitudinal check-in flags: single-item escalation and adverse-event signals.

Flags are pre-specified, rule-based signals attached to a completed check-in.
They follow two evidence constraints:

- NICE NG225: a summed score never drives a risk category. Nothing here
  re-labels a person from a total; the only score-derived signals are the
  pre-specified persistence and early-worsening rules below, which prompt a
  *conversation* (referral prompt, human review), never a category.
- PHQ-9 item 9 ("better off dead or of hurting yourself") is a single-item
  escalation flag: any positive answer escalates regardless of the total.

Research grounding and provisional defaults:

- NICE NG222 rec. 1.2.10 (design-applied): early worsening after starting
  treatment — an increase vs baseline within the first 14 days — is a
  pre-specified adverse-event signal (:data:`CheckInFlag.EARLY_WORSENSING`).
- NICE NG222 rec. 1.4.3 (design-applied): score >= 16 persisting across two
  consecutive check-ins prompts a professional-referral conversation
  (:data:`CheckInFlag.REFERRAL_PROMPT`).

All threshold values (:data:`DEFAULT_EARLY_WORSENSING_THRESHOLDS`, the
14-day window, and the >= 16 persistence cutoff) are PROVISIONAL design
defaults pending pilot validation.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

#: Provisional early-worsening increase thresholds (total points above the
#: first check-in's baseline) per instrument, pending pilot validation.
DEFAULT_EARLY_WORSENSING_THRESHOLDS: dict[str, int] = {"phq9": 5, "gad7": 4, "k10": 5}

#: Provisional persistence cutoff for the professional-referral prompt:
#: two consecutive PHQ-9 totals at or above this value (NICE NG222 rec.
#: 1.4.3, design-applied), pending pilot validation.
REFERRAL_PERSISTENT_TOTAL = 16

#: Zero-based index of PHQ-9 item 9 ("...better off dead or of hurting
#: yourself...") — the single-item escalation flag.
PHQ9_ITEM9_INDEX = 8


# ``str, Enum`` is the spec-mandated base (StrEnum would change ``str()`` output).
class CheckInFlag(str, Enum):  # noqa: UP042
    """Pre-specified flags a completed check-in can carry.

    Members are declared in escalation-precedence order; flag tuples are
    always returned deduplicated in this order.
    """

    ESCALATE = "escalate"
    EARLY_WORSENSING = "early_worsening"
    REFERRAL_PROMPT = "referral_prompt"


@dataclass(frozen=True)
class EarlyWorseningPolicy:
    """Provisional early-worsening detection parameters (see module docstring).

    ``thresholds`` maps an instrument id to the minimum total increase over
    that instrument's baseline that counts as early worsening. It is stored
    read-only; :attr:`window_days` is the inclusive window (baseline day is
    day 0) within which the increase counts, per NICE NG222 rec. 1.2.10.

    Raises:
        ValueError: If any threshold or ``window_days`` is not positive.
    """

    thresholds: Mapping[str, int] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_EARLY_WORSENSING_THRESHOLDS))
    )
    window_days: int = 14

    def __post_init__(self) -> None:
        for instrument_id, threshold in self.thresholds.items():
            if threshold <= 0:
                raise ValueError(
                    f"EarlyWorseningPolicy threshold for {instrument_id!r} must be > 0, "
                    f"got {threshold}"
                )
        if self.window_days <= 0:
            raise ValueError(
                f"EarlyWorseningPolicy.window_days must be > 0, got {self.window_days}"
            )


def checkin_flags(
    instrument_id: str,
    responses: Sequence[int],
    total: int,
    baseline_total: int | None,
    days_since_baseline: int | None,
    previous_total: int | None,
    policy: EarlyWorseningPolicy,
) -> tuple[CheckInFlag, ...]:
    """Compute the pre-specified flags for one completed check-in.

    Pure and deterministic. ``responses`` is preconditioned on having been
    validated by :func:`reframe.measurement.score` (correct length, scale
    values) — in particular a ``phq9`` response vector always has at least
    9 entries, so ``responses[8]`` (item 9) is safe to read.

    Args:
        instrument_id: The active instrument that was just completed.
        responses: Validated response vector for this check-in.
        total: The scored total for this check-in.
        baseline_total: The first (baseline) check-in's total for the same
            instrument, or ``None`` if this IS the first check-in.
        days_since_baseline: Whole days since the baseline check-in, or
            ``None`` if no baseline exists.
        previous_total: The immediately preceding check-in's total for the
            same instrument, or ``None`` if there is none.
        policy: Provisional early-worsening thresholds and window.

    Returns:
        Flags in :class:`CheckInFlag` declaration order, deduplicated;
        ``()`` when nothing pre-specified fires. A first check-in can never
        carry EARLY_WORSENSING or REFERRAL_PROMPT (no baseline/previous) but
        CAN carry ESCALATE (item 9 on day one still escalates).
    """
    flags: list[CheckInFlag] = []

    # Single-item escalation: PHQ-9 item 9, regardless of the total.
    if instrument_id == "phq9" and responses[PHQ9_ITEM9_INDEX] > 0:
        flags.append(CheckInFlag.ESCALATE)

    # Early worsening: pre-specified adverse-event signal (NICE NG222 rec. 1.2.10).
    threshold = policy.thresholds.get(instrument_id)
    if (
        threshold is not None
        and baseline_total is not None
        and days_since_baseline is not None
        and 0 <= days_since_baseline <= policy.window_days
        and total - baseline_total >= threshold
    ):
        flags.append(CheckInFlag.EARLY_WORSENSING)

    # Persistent elevation: two consecutive scores >= 16 prompt referral talk
    # (NICE NG222 rec. 1.4.3, design-applied; provisional cutoff).
    if (
        instrument_id == "phq9"
        and previous_total is not None
        and previous_total >= REFERRAL_PERSISTENT_TOTAL
        and total >= REFERRAL_PERSISTENT_TOTAL
    ):
        flags.append(CheckInFlag.REFERRAL_PROMPT)

    return tuple(flags)
