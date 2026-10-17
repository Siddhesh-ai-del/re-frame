"""Tests for ``reframe.measurement.tracker`` — in-memory check-in tracking.

Strict TDD: written BEFORE ``reframe/measurement/tracker.py`` exists; the
first run must fail with ``ModuleNotFoundError`` (RED).

The tracker is deterministic and NOT thread-safe (documented design limit):
one process, one caller, in-memory history only. Out-of-order check-in
dates for the same instrument are rejected (fail-closed data quality).
"""

import datetime
from dataclasses import FrozenInstanceError

import pytest

from reframe.measurement.flags import CheckInFlag, EarlyWorseningPolicy
from reframe.measurement.tracker import CheckIn, CheckInTracker


def _phq9(total: int, item9: int = 0) -> tuple[int, ...]:
    """A valid PHQ-9 response vector summing to ``total`` with fixed item 9."""
    responses = [0] * 9
    responses[8] = item9
    remaining = total - item9
    for index in range(8):
        take = min(3, remaining)
        responses[index] = take
        remaining -= take
    assert remaining == 0, "test helper cannot build this total"
    return tuple(responses)


def _gad7(total: int) -> tuple[int, ...]:
    """A valid GAD-7 response vector summing to ``total``."""
    responses = [0] * 7
    remaining = total
    for index in range(7):
        take = min(3, remaining)
        responses[index] = take
        remaining -= take
    assert remaining == 0, "test helper cannot build this total"
    return tuple(responses)


DAY_ONE = datetime.date(2026, 1, 1)


# ------------------------------------------------------------- first check-in


def test_first_checkin_has_no_baseline_and_single_history_entry() -> None:
    tracker = CheckInTracker()
    checkin = tracker.record("phq9", _phq9(total=0), DAY_ONE)

    assert checkin.instrument_id == "phq9"
    assert checkin.date == DAY_ONE
    assert checkin.responses == _phq9(total=0)
    assert checkin.total == 0
    assert checkin.severity_label == "minimal"
    assert checkin.flags == ()  # first check-in: no baseline/previous, item 9 = 0

    # With one check-in recorded, that check-in IS the baseline for future
    # comparisons; it only returns None when nothing has been recorded yet
    # (covered by test_latest_and_baseline_are_none_before_any_record).
    assert tracker.baseline("phq9") == checkin
    assert tracker.history("phq9") == (checkin,)
    assert tracker.latest("phq9") == checkin


# ------------------------------------------------- early worsening vs baseline


def test_second_checkin_within_window_flags_early_worsening_vs_baseline() -> None:
    tracker = CheckInTracker()
    baseline = tracker.record("phq9", _phq9(total=0), DAY_ONE)
    second = tracker.record("phq9", _phq9(total=5), DAY_ONE + datetime.timedelta(days=10))

    assert second.total == 5
    assert second.severity_label == "mild"
    assert second.flags == (CheckInFlag.EARLY_WORSENSING,)
    assert tracker.baseline("phq9") == baseline
    assert tracker.history("phq9") == (baseline, second)
    assert tracker.latest("phq9") == second


def test_custom_policy_drives_early_worsening_threshold() -> None:
    strict = EarlyWorseningPolicy(thresholds={"phq9": 1})
    tracker = CheckInTracker(policy=strict)
    tracker.record("phq9", _phq9(total=0), DAY_ONE)
    second = tracker.record("phq9", _phq9(total=1), DAY_ONE + datetime.timedelta(days=2))

    assert second.flags == (CheckInFlag.EARLY_WORSENSING,)


# ------------------------------------------------------------- data quality


def test_out_of_order_checkin_date_is_rejected() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", _phq9(total=0), DAY_ONE + datetime.timedelta(days=10))

    with pytest.raises(ValueError, match="out-of-order"):
        tracker.record("phq9", _phq9(total=3), DAY_ONE)


def test_unknown_instrument_is_rejected() -> None:
    tracker = CheckInTracker()
    with pytest.raises(ValueError, match="instrument"):
        tracker.record("not_an_instrument", (0, 0, 0, 0, 0, 0, 0, 0, 0), DAY_ONE)


def test_same_day_checkin_is_allowed() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", _phq9(total=4), DAY_ONE)
    same_day = tracker.record("phq9", _phq9(total=4), DAY_ONE)

    assert same_day.flags == ()  # delta 0 over baseline, same day


# -------------------------------------------------------------- item-9 flag


def test_item9_response_records_escalate_flag_on_checkin() -> None:
    tracker = CheckInTracker()
    checkin = tracker.record("phq9", _phq9(total=2, item9=2), DAY_ONE)

    assert checkin.total == 2
    assert checkin.flags == (CheckInFlag.ESCALATE,)


# ----------------------------------------------------- multi-instrument scope


def test_history_baseline_and_latest_are_isolated_per_instrument() -> None:
    tracker = CheckInTracker()
    phq9_first = tracker.record("phq9", _phq9(total=0), DAY_ONE)
    gad7_first = tracker.record("gad7", _gad7(total=3), DAY_ONE + datetime.timedelta(days=1))
    phq9_second = tracker.record("phq9", _phq9(total=1), DAY_ONE + datetime.timedelta(days=4))

    phq9_history = tracker.history("phq9")
    assert phq9_history == (phq9_first, phq9_second)
    assert all(entry.instrument_id == "phq9" for entry in phq9_history)
    assert tracker.history("gad7") == (gad7_first,)
    assert tracker.baseline("phq9") == phq9_first
    assert tracker.baseline("gad7") == gad7_first
    assert tracker.latest("phq9") == phq9_second
    assert tracker.latest("gad7") == gad7_first


def test_latest_and_baseline_are_none_before_any_record() -> None:
    tracker = CheckInTracker()
    assert tracker.latest("phq9") is None
    assert tracker.baseline("phq9") is None


def test_latest_is_none_for_instrument_with_no_records() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", _phq9(total=0), DAY_ONE)
    assert tracker.latest("gad7") is None
    assert tracker.baseline("gad7") is None


def test_history_for_instrument_with_no_records_raises() -> None:
    tracker = CheckInTracker()
    with pytest.raises(ValueError, match="no check-ins"):
        tracker.history("phq9")


# -------------------------------------------------------------- serialization


def _sample_tracker() -> CheckInTracker:
    tracker = CheckInTracker()
    tracker.record("phq9", _phq9(total=0), DAY_ONE)
    tracker.record("phq9", _phq9(total=5), DAY_ONE + datetime.timedelta(days=10))
    tracker.record("phq9", _phq9(total=5, item9=1), DAY_ONE + datetime.timedelta(days=20))
    tracker.record("gad7", _gad7(total=3), DAY_ONE + datetime.timedelta(days=2))
    return tracker


def test_to_dict_shape() -> None:
    data = _sample_tracker().to_dict()

    assert set(data) == {"checkins"}
    entries = data["checkins"]
    assert len(entries) == 4
    first = entries[0]
    assert set(first) == {
        "instrument_id",
        "date",
        "responses",
        "total",
        "severity_label",
        "flags",
    }
    assert first["date"] == "2026-01-01"
    assert first["responses"] == list(_phq9(total=0))
    assert first["flags"] == []


def test_to_dict_from_dict_round_trip_preserves_everything_including_flags() -> None:
    original = _sample_tracker()
    rebuilt = CheckInTracker.from_dict(original.to_dict())

    assert rebuilt.to_dict() == original.to_dict()
    assert rebuilt.history("phq9") == original.history("phq9")
    assert rebuilt.history("gad7") == original.history("gad7")
    escalate = rebuilt.latest("phq9")
    assert escalate is not None
    assert escalate.flags == (CheckInFlag.ESCALATE,)
    worsened = rebuilt.history("phq9")[1]
    assert worsened.flags == (CheckInFlag.EARLY_WORSENSING,)


def test_from_dict_restores_explicit_policy() -> None:
    strict = EarlyWorseningPolicy(thresholds={"phq9": 1}, window_days=30)
    tracker = CheckInTracker.from_dict(_sample_tracker().to_dict(), policy=strict)
    tracker.record("phq9", _phq9(total=6), DAY_ONE + datetime.timedelta(days=21))

    latest = tracker.latest("phq9")
    assert latest is not None
    # delta 6 >= custom threshold 1, day 21 <= custom window 30 -> EARLY_WORSENSING
    assert CheckInFlag.EARLY_WORSENSING in latest.flags


def test_from_dict_rejects_bad_top_level_key() -> None:
    with pytest.raises(ValueError, match="checkins"):
        CheckInTracker.from_dict({"chekcins": []})


def test_from_dict_rejects_non_list_checkins() -> None:
    with pytest.raises(ValueError, match="checkins"):
        CheckInTracker.from_dict({"checkins": 42})


def test_from_dict_rejects_missing_field() -> None:
    entry = {
        "instrument_id": "phq9",
        "date": "2026-01-01",
        "responses": list(_phq9(total=0)),
        "severity_label": "minimal",
        "flags": [],
    }
    with pytest.raises(ValueError, match="malformed check-in"):
        CheckInTracker.from_dict({"checkins": [entry]})


def test_from_dict_rejects_bad_flag_value() -> None:
    entry = {
        "instrument_id": "phq9",
        "date": "2026-01-01",
        "responses": list(_phq9(total=0)),
        "total": 0,
        "severity_label": "minimal",
        "flags": ["not_a_flag"],
    }
    with pytest.raises(ValueError, match="flag"):
        CheckInTracker.from_dict({"checkins": [entry]})


# ------------------------------------------------------------------- immutability


def test_checkin_is_frozen() -> None:
    tracker = CheckInTracker()
    checkin = tracker.record("phq9", _phq9(total=0), DAY_ONE)
    with pytest.raises(FrozenInstanceError):
        checkin.total = 5  # type: ignore[misc]
    assert isinstance(checkin, CheckIn)
