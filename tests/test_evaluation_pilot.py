"""Tests for ``reframe.evaluation.pilot`` — feasibility-pilot config and metrics.

Strict TDD: written BEFORE ``reframe/evaluation/pilot.py`` exists; the first run
must fail with ``ModuleNotFoundError`` (RED).

Pure instrumentation for the feasibility pilot (stage 7b, decisions E2-E4):
window resolution prefers explicit params over the data span over ``None``;
ISO calendar weeks everywhere (``_iso_weeks_spanned`` steps day-by-day, robust
across year boundaries); retention/data-completeness/safety-rate metrics are
``None`` exactly when their pre-specified criterion is not evaluable. These are
OPERATIONAL feasibility parameters — never clinical, never efficacy.
"""

import datetime
from dataclasses import FrozenInstanceError

import pytest

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.evaluation.pilot import (
    PilotConfig,
    PilotMetrics,
    _iso_week,
    _iso_weeks_spanned,
    compute_metrics,
)
from reframe.measurement.tracker import CheckInTracker

UTC = datetime.UTC
DAY_ONE = datetime.date(2026, 10, 1)


def _tracker(*dates: datetime.date) -> CheckInTracker:
    """Record one zeroed PHQ-9 check-in per date, in order."""
    tracker = CheckInTracker()
    for date in dates:
        tracker.record("phq9", [0] * 9, date)
    return tracker


def _event(
    ae_type: AEType,
    *,
    detected_at: datetime.datetime,
    serious: bool | None = None,
) -> AdverseEvent:
    return AdverseEvent.create(
        ae_type,
        source=AESource.REVIEW,
        serious=serious,
        detected_at=detected_at,
    )


def _at(date: datetime.date) -> datetime.datetime:
    return datetime.datetime(date.year, date.month, date.day, 9, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# PilotConfig: defaults and fail-closed validation
# ---------------------------------------------------------------------------


def test_pilot_config_defaults_are_the_provisional_design_assumptions() -> None:
    config = PilotConfig()
    assert config.expected_per_week == 1
    assert config.planned_participants is None
    assert config.enrolled_participants is None


@pytest.mark.parametrize("cadence", [0, -3])
def test_pilot_config_rejects_a_cadence_below_one(cadence: int) -> None:
    with pytest.raises(ValueError):
        PilotConfig(expected_per_week=cadence)


def test_pilot_config_rejects_a_non_int_cadence() -> None:
    with pytest.raises(ValueError):
        PilotConfig(expected_per_week=1.5)  # type: ignore[arg-type]


def test_pilot_config_rejects_unpaired_planned_and_enrolled() -> None:
    with pytest.raises(ValueError):
        PilotConfig(planned_participants=40)
    with pytest.raises(ValueError):
        PilotConfig(enrolled_participants=30)


def test_pilot_config_rejects_counts_below_one() -> None:
    with pytest.raises(ValueError):
        PilotConfig(planned_participants=0, enrolled_participants=30)
    with pytest.raises(ValueError):
        PilotConfig(planned_participants=40, enrolled_participants=0)


def test_pilot_config_accepts_paired_counts() -> None:
    config = PilotConfig(expected_per_week=2, planned_participants=40, enrolled_participants=30)
    assert config.expected_per_week == 2
    assert config.planned_participants == 40
    assert config.enrolled_participants == 30


def test_pilot_config_is_frozen() -> None:
    config = PilotConfig()
    with pytest.raises(FrozenInstanceError):
        config.expected_per_week = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Window resolution (E2): explicit params > data span > None; start > end raises
# ---------------------------------------------------------------------------


def test_explicit_window_wins_over_the_data_span() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 15))
    checkins = tracker.history("phq9")

    metrics = compute_metrics(
        checkins,
        (),
        config=PilotConfig(),
        window_start=datetime.date(2026, 10, 5),
        window_end=datetime.date(2026, 10, 10),
    )

    assert metrics.window_start == datetime.date(2026, 10, 5)
    assert metrics.window_end == datetime.date(2026, 10, 10)


def test_window_defaults_to_the_data_span_of_checkins_and_events() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 15))
    checkins = tracker.history("phq9")
    events = (_event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(datetime.date(2026, 10, 20))),)

    metrics = compute_metrics(checkins, events, config=PilotConfig())

    # The span is min/max over check-in dates UNION adverse-event detection dates.
    assert metrics.window_start == DAY_ONE
    assert metrics.window_end == datetime.date(2026, 10, 20)


def test_no_data_and_no_params_yields_no_window_and_mostly_none_metrics() -> None:
    metrics = compute_metrics((), (), config=PilotConfig())

    assert metrics.window_start is None
    assert metrics.window_end is None
    assert metrics.total_weeks is None
    assert metrics.checkins_in_window == 0
    assert metrics.active_weeks is None
    assert metrics.retention is None
    assert metrics.data_completeness is None
    assert metrics.expected_checkins is None
    assert metrics.adverse_events_in_window == 0
    assert metrics.adverse_events_per_week is None


def test_explicit_only_future_window_resolves_from_params_alone() -> None:
    start = datetime.date(2026, 11, 9)  # a Monday
    end = datetime.date(2026, 11, 15)  # the same ISO week's Sunday

    metrics = compute_metrics((), (), config=PilotConfig(), window_start=start, window_end=end)

    assert metrics.window_start == start
    assert metrics.window_end == end
    assert metrics.total_weeks == 1
    # No observation at all: rate/retention/completeness are not evaluable (E4).
    assert metrics.checkins_in_window == 0
    assert metrics.active_weeks == 0
    assert metrics.retention is None
    assert metrics.data_completeness is None
    assert metrics.adverse_events_per_week is None


def test_explicit_start_after_end_raises() -> None:
    with pytest.raises(ValueError):
        compute_metrics(
            (),
            (),
            config=PilotConfig(),
            window_start=datetime.date(2026, 10, 12),
            window_end=datetime.date(2026, 10, 5),
        )


# ---------------------------------------------------------------------------
# ISO week math (E3): helpers pinned directly, year boundary included
# ---------------------------------------------------------------------------


def test_iso_week_returns_the_isoyear_isoweek_pair() -> None:
    assert _iso_week(DAY_ONE) == (2026, 40)


def test_iso_weeks_spanned_within_one_week_is_one() -> None:
    assert _iso_weeks_spanned(datetime.date(2026, 10, 1), datetime.date(2026, 10, 4)) == 1


def test_iso_weeks_spanned_of_a_single_day_is_one() -> None:
    assert _iso_weeks_spanned(datetime.date(2026, 10, 5), datetime.date(2026, 10, 5)) == 1


def test_iso_weeks_spanned_crosses_a_year_boundary() -> None:
    # 2026-12-28 (Mon) .. 2027-01-05 (Tue): ISO 2026-w53 then ISO 2027-w01.
    assert _iso_weeks_spanned(datetime.date(2026, 12, 28), datetime.date(2027, 1, 5)) == 2


def test_iso_weeks_spanned_counts_three_weeks_over_fifteen_october_days() -> None:
    assert _iso_weeks_spanned(datetime.date(2026, 10, 1), datetime.date(2026, 10, 15)) == 3


# ---------------------------------------------------------------------------
# Metrics over constructed histories: retention, completeness, event rate
# ---------------------------------------------------------------------------


def test_retention_is_active_iso_weeks_over_total_window_weeks() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 2), datetime.date(2026, 10, 12))
    checkins = tracker.history("phq9")

    metrics = compute_metrics(checkins, (), config=PilotConfig())

    # 2026-10-01..2026-10-12 spans ISO weeks 40, 41, 42; check-ins sit in 40 and 42.
    assert metrics.total_weeks == 3
    assert metrics.active_weeks == 2
    assert metrics.retention == pytest.approx(2 / 3)


def test_data_completeness_uses_weeks_times_expected_cadence() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 2), datetime.date(2026, 10, 3))
    checkins = tracker.history("phq9")

    metrics = compute_metrics(checkins, (), config=PilotConfig())

    assert metrics.total_weeks == 1
    assert metrics.expected_checkins == 1
    assert metrics.checkins_in_window == 3
    assert metrics.data_completeness == 3.0  # raw ratio, NOT capped at 1.0


def test_a_window_without_in_window_checkins_is_a_genuine_zero() -> None:
    tracker = _tracker(datetime.date(2026, 10, 20))
    checkins = tracker.history("phq9")

    metrics = compute_metrics(
        checkins,
        (),
        config=PilotConfig(),
        window_start=DAY_ONE,
        window_end=datetime.date(2026, 10, 7),
    )

    # Observation happened (check-ins exist), just none inside the window (E4).
    assert metrics.retention == 0.0
    assert metrics.data_completeness == 0.0


def test_rate_is_in_window_events_over_total_window_weeks() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 3))
    checkins = tracker.history("phq9")
    events = (_event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(datetime.date(2026, 10, 3))),)

    metrics = compute_metrics(checkins, events, config=PilotConfig())

    assert metrics.total_weeks == 1
    assert metrics.adverse_events_in_window == 1
    assert metrics.adverse_events_per_week == 1.0


def test_events_outside_the_explicit_window_are_excluded_by_detected_at_date() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 7))
    checkins = tracker.history("phq9")
    inside = _event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(datetime.date(2026, 10, 3)))
    outside = _event(
        AEType.TRANSIENT_EARLY_WORSENSING, detected_at=_at(datetime.date(2026, 10, 20))
    )

    metrics = compute_metrics(
        checkins,
        (inside, outside),
        config=PilotConfig(),
        window_start=DAY_ONE,
        window_end=datetime.date(2026, 10, 7),
    )

    assert metrics.adverse_events_in_window == 1
    # 2026-10-01..2026-10-07 spans ISO weeks 40 and 41 -> 1 event / 2 weeks.
    assert metrics.total_weeks == 2
    assert metrics.adverse_events_per_week == 0.5


def test_event_filtering_uses_the_local_date_of_detection() -> None:
    late_night = datetime.datetime(2026, 10, 8, 23, 30, tzinfo=UTC)  # still Oct 8
    after_midnight = datetime.datetime(2026, 10, 9, 0, 30, tzinfo=UTC)  # Oct 9
    events = (
        _event(AEType.SYCOPHANCY_EPISODE, detected_at=late_night),
        _event(AEType.SYCOPHANCY_EPISODE, detected_at=after_midnight),
    )

    metrics = compute_metrics(
        (),
        events,
        config=PilotConfig(),
        window_start=DAY_ONE,
        window_end=datetime.date(2026, 10, 8),
    )

    assert metrics.adverse_events_in_window == 1


def test_events_alone_give_a_window_and_a_rate_but_no_retention() -> None:
    events = (_event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(DAY_ONE)),)

    metrics = compute_metrics((), events, config=PilotConfig())

    assert metrics.window_start == DAY_ONE
    assert metrics.window_end == DAY_ONE
    assert metrics.total_weeks == 1
    assert metrics.retention is None
    assert metrics.data_completeness is None
    assert metrics.adverse_events_per_week == 1.0


def test_checkins_without_events_report_a_zero_event_rate() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 7))
    metrics = compute_metrics(tracker.history("phq9"), (), config=PilotConfig())
    assert metrics.adverse_events_in_window == 0
    assert metrics.adverse_events_per_week == 0.0


def test_explicit_cadence_scales_the_expected_checkins() -> None:
    tracker = _tracker(DAY_ONE, datetime.date(2026, 10, 7), datetime.date(2026, 10, 14))

    metrics = compute_metrics(
        tracker.history("phq9"),
        (),
        config=PilotConfig(expected_per_week=2),
    )

    # 2026-10-01..2026-10-14 spans ISO weeks 40, 41, and 42.
    assert metrics.total_weeks == 3
    assert metrics.expected_checkins == 6
    assert metrics.data_completeness == 0.5


def test_pilot_metrics_is_a_frozen_value() -> None:
    metrics = compute_metrics((), (), config=PilotConfig())
    assert isinstance(metrics, PilotMetrics)
    with pytest.raises(AttributeError):
        metrics.total_weeks = 1  # type: ignore[misc]
