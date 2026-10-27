"""Feasibility-pilot configuration and operational metrics (pure; stage 7b).

Scope: the pilot's OBSERVATION window, ISO calendar-week arithmetic, and the
descriptive feasibility counts that feed the pre-specified progression
criteria (E2-E4). Everything here is operational feasibility instrumentation —
never a clinical score, never an efficacy computation.

- **E2 — window resolution:** explicit params > data span (min/max over
  check-in dates and adverse-event ``detected_at`` dates) > ``None``. An
  explicit ``start > end`` raises ``ValueError``.
- **E3 — ISO calendar weeks everywhere:** ``total_weeks`` counts distinct ISO
  ``(isoyear, isoweek)`` pairs spanned by stepping day-by-day (robust across
  year boundaries); ``active_weeks`` counts distinct ISO weeks holding at
  least one in-window check-in.
- **E4 — not-evaluable honesty:** retention/data completeness are ``None``
  exactly when no check-ins were recorded at all; the safety rate is ``None``
  exactly when neither check-ins nor events exist. A real window with zero
  in-window check-ins is a genuine ``0.0`` — observation happened.
"""

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from reframe.evaluation.adverse_events import AdverseEvent
from reframe.measurement.tracker import CheckIn


@dataclass(frozen=True)
class PilotConfig:
    """Provisional pilot cadence and protocol-level recruitment counts (E6).

    All defaults are RE:FRAME provisional design assumptions, operator
    overridable; validation is fail-closed (``ValueError``).
    """

    expected_per_week: int = 1
    planned_participants: int | None = None
    enrolled_participants: int | None = None

    def __post_init__(self) -> None:
        """Validate cadence and the planned/enrolled pairing, fail-closed."""
        if type(self.expected_per_week) is not int or self.expected_per_week < 1:
            raise ValueError("expected_per_week must be an int >= 1")
        if (self.planned_participants is None) != (self.enrolled_participants is None):
            raise ValueError("planned_participants and enrolled_participants must be paired")
        for count in (self.planned_participants, self.enrolled_participants):
            if count is not None and (type(count) is not int or count < 1):
                raise ValueError("participant counts must be ints >= 1")


@dataclass(frozen=True)
class PilotMetrics:
    """Descriptive feasibility metrics over one observation window (E2-E4)."""

    window_start: datetime.date | None
    window_end: datetime.date | None
    total_weeks: int | None
    checkins_in_window: int
    active_weeks: int | None
    retention: float | None
    data_completeness: float | None
    expected_checkins: int | None
    adverse_events_in_window: int
    adverse_events_per_week: float | None


def _iso_week(day: datetime.date) -> tuple[int, int]:
    """The ``(isoyear, isoweek)`` pair holding ``day``."""
    return (day.isocalendar()[0], day.isocalendar()[1])


def _iso_weeks_spanned(start: datetime.date, end: datetime.date) -> int:
    """Count distinct ISO weeks from ``start`` to ``end`` inclusive (E3).

    Steps day-by-day so a window crossing a year boundary (e.g. ISO week
    2026-w53 into 2027-w01) counts correctly.
    """
    weeks: set[tuple[int, int]] = set()
    day = start
    while day <= end:
        weeks.add(_iso_week(day))
        day += datetime.timedelta(days=1)
    return len(weeks)


def compute_metrics(
    checkins: Sequence[CheckIn],
    events: Sequence[AdverseEvent],
    *,
    config: PilotConfig,
    window_start: datetime.date | None = None,
    window_end: datetime.date | None = None,
) -> PilotMetrics:
    """Compute the descriptive feasibility metrics over the resolved window (E2-E4).

    Args:
        checkins: All recorded check-ins (any date); in-window filtering uses
            ``checkin.date`` inclusive of both bounds.
        events: All adverse events; in-window filtering uses
            ``event.detected_at.date()`` inclusive of both bounds.
        config: The pilot configuration (cadence, recruitment counts).
        window_start: Explicit window start; ``None`` resolves to the data span.
        window_end: Explicit window end; ``None`` resolves to the data span.

    Returns:
        The frozen :class:`PilotMetrics`; metrics that are not evaluable
        (E4) are ``None``.

    Raises:
        ValueError: If the resolved ``start`` is after the resolved ``end``.
    """
    span_dates = [checkin.date for checkin in checkins]
    span_dates += [event.detected_at.date() for event in events]
    start = window_start if window_start is not None else (min(span_dates) if span_dates else None)
    end = window_end if window_end is not None else (max(span_dates) if span_dates else None)
    if start is not None and end is not None and start > end:
        raise ValueError("window start is after window end")
    if start is None or end is None:
        return PilotMetrics(None, None, None, 0, None, None, None, None, 0, None)

    in_window_checkins = [c for c in checkins if start <= c.date <= end]
    in_window_events = [e for e in events if start <= e.detected_at.date() <= end]
    total_weeks = _iso_weeks_spanned(start, end)
    active_weeks = len({_iso_week(c.date) for c in in_window_checkins})
    expected_checkins = total_weeks * config.expected_per_week
    # E4: "no check-ins recorded at all" -> not evaluable; a real window with
    # zero in-window check-ins is a genuine 0.0 (observation happened).
    retention = active_weeks / total_weeks if checkins else None
    data_completeness = len(in_window_checkins) / expected_checkins if checkins else None
    adverse_events_per_week = len(in_window_events) / total_weeks if checkins or events else None
    return PilotMetrics(
        window_start=start,
        window_end=end,
        total_weeks=total_weeks,
        checkins_in_window=len(in_window_checkins),
        active_weeks=active_weeks,
        retention=retention,
        data_completeness=data_completeness,
        expected_checkins=expected_checkins,
        adverse_events_in_window=len(in_window_events),
        adverse_events_per_week=adverse_events_per_week,
    )
