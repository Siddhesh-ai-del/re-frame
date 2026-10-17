"""Fail-closed scoring for RE:FRAME's free measurement instruments.

Malformed responses never produce a score: every value is validated before
any arithmetic happens, so a :class:`ScoreResult` can only exist for a fully
valid response vector on a known, active instrument.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from reframe.measurement.instruments import InstrumentSpec, get_instrument


@dataclass(frozen=True)
class ScoreResult:
    """A completed instrument score: raw responses, total, and severity band.

    ``severity_label`` is ``None`` when the instrument declares no bands.
    ``responses`` preserves the answers exactly as given (before any
    reverse scoring is applied to the total).
    """

    instrument_id: str
    total: int
    severity_label: str | None
    responses: tuple[int, ...]


def severity_for_total(instrument: InstrumentSpec, total: int) -> str | None:
    """Map ``total`` to its severity band label, or ``None`` when unbanded.

    Raises:
        ValueError: If ``total`` falls outside ``total_min..total_max``.
    """
    if not instrument.total_min <= total <= instrument.total_max:
        raise ValueError(
            f"total {total} is outside the {instrument.id} range "
            f"{instrument.total_min}..{instrument.total_max}"
        )
    for band in instrument.severity_bands:
        if band.lower <= total <= band.upper:
            return band.label
    return None


def score(instrument_id: str, responses: Sequence[int]) -> ScoreResult:
    """Score ``responses`` against the active instrument ``instrument_id``.

    Raises:
        ValueError: For unknown or pending instruments, a wrong number of
            responses, non-integer values (``bool`` included — ``True`` is
            not a valid answer), or values outside the instrument's scale.
            Offending response values are reported by 1-based index.
    """
    instrument = get_instrument(instrument_id)
    if len(responses) != len(instrument.items):
        raise ValueError(
            f"instrument {instrument_id!r} expects {len(instrument.items)} responses, "
            f"got {len(responses)}"
        )
    validated: list[int] = []
    for position, value in enumerate(responses, start=1):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"response at index {position} must be an int, got {value!r}")
        if not instrument.scale_min <= value <= instrument.scale_max:
            raise ValueError(
                f"response at index {position} must be within "
                f"{instrument.scale_min}..{instrument.scale_max}, got {value}"
            )
        validated.append(value)
    total = 0
    for item, value in zip(instrument.items, validated, strict=True):
        if item.index in instrument.reverse_scored:
            total += instrument.scale_min + instrument.scale_max - value
        else:
            total += value
    return ScoreResult(
        instrument_id=instrument_id,
        total=total,
        severity_label=severity_for_total(instrument, total),
        responses=tuple(validated),
    )
