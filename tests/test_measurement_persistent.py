"""Tests for ``reframe.measurement.persistent`` — durable check-in tracking.

Strict TDD: written BEFORE ``reframe/measurement/persistent.py`` exists; the
first run must fail with ``ModuleNotFoundError`` (RED).

PersistentCheckInTracker = the in-memory :class:`CheckInTracker` plus one
``threading.Lock`` (FastAPI sync routes run in a threadpool) and a
:class:`CheckInStore` for durability: flags restore VERBATIM (load never
re-scores), rejected check-ins never touch the store, and a failed persist
rolls the in-memory append back so memory and store stay consistent — a
check-in exists either everywhere or nowhere.
"""

import datetime
from collections.abc import Sequence
from pathlib import Path

import pytest

from reframe.measurement.flags import CheckInFlag, EarlyWorseningPolicy
from reframe.measurement.persistent import PersistentCheckInTracker
from reframe.measurement.store import CheckInStore, SqliteCheckInStore
from reframe.measurement.tracker import CheckIn, CheckInTracker

DAY_ONE = datetime.date(2026, 1, 1)


class RecordingStore:
    """Stub CheckInStore: replays a fixed load(), records appends, scripted failures."""

    def __init__(
        self,
        loaded: Sequence[CheckIn] = (),
        *,
        append_error: BaseException | None = None,
        load_error: BaseException | None = None,
    ) -> None:
        self.loaded = tuple(loaded)
        self.calls: list[CheckIn] = []
        self.append_error = append_error
        self.load_error = load_error

    def append(self, checkin: CheckIn) -> None:
        self.calls.append(checkin)
        if self.append_error is not None:
            raise self.append_error

    def load(self) -> tuple[CheckIn, ...]:
        if self.load_error is not None:
            raise self.load_error
        return self.loaded

    def close(self) -> None:
        return None


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


def _checkin(
    date: datetime.date,
    *,
    total: int = 0,
    severity_label: str | None = None,
    flags: tuple[CheckInFlag, ...] = (),
) -> CheckIn:
    return CheckIn("phq9", date, _phq9(total), total, severity_label, flags)


# ---------------------------------------------------------------- restore


def test_restores_preexisting_checkins_from_the_store_on_init() -> None:
    first = _checkin(DAY_ONE, total=0, severity_label="minimal")
    second = _checkin(DAY_ONE + datetime.timedelta(days=3), total=4, severity_label="mild")
    store: CheckInStore = RecordingStore(loaded=[first, second])

    tracker = PersistentCheckInTracker(store)

    assert tracker.history("phq9") == (first, second)
    assert tracker.baseline("phq9") == first
    assert tracker.latest("phq9") == second


def test_flags_are_restored_verbatim_and_never_rescored_on_load() -> None:
    # All-zero responses would recompute to NO flags, but the stored flags say
    # REFERRAL_PROMPT — the recorded flags are the authority on load.
    stored = _checkin(DAY_ONE, total=0, flags=(CheckInFlag.REFERRAL_PROMPT,))
    tracker = PersistentCheckInTracker(RecordingStore(loaded=[stored]))

    restored = tracker.history("phq9")[0]
    assert restored == stored
    assert restored.flags == (CheckInFlag.REFERRAL_PROMPT,)

    # Contrast: the very same responses recorded fresh carry no flags — proof
    # that the restored flag survived without any re-scoring.
    fresh = PersistentCheckInTracker(RecordingStore()).record("phq9", (0,) * 9, DAY_ONE)
    assert fresh.flags == ()


def test_constructor_propagates_a_store_load_failure_unchanged() -> None:
    store = RecordingStore(load_error=ValueError("malformed check-in row 3"))

    with pytest.raises(ValueError) as excinfo:
        PersistentCheckInTracker(store)

    assert excinfo.value is store.load_error
    assert str(excinfo.value) == "malformed check-in row 3"


# ------------------------------------------------------- persistence chain


def test_recorded_checkin_survives_tracker_and_store_recreation(tmp_path: Path) -> None:
    path = tmp_path / "chain.db"
    store_a = SqliteCheckInStore(path)
    tracker_a = PersistentCheckInTracker(store_a)
    recorded = tracker_a.record("phq9", _phq9(total=6), DAY_ONE)
    store_a.close()

    store_b = SqliteCheckInStore(path)
    try:
        tracker_b = PersistentCheckInTracker(store_b)
        assert tracker_b.history("phq9") == (recorded,)
        assert tracker_b.baseline("phq9") == recorded
        assert tracker_b.latest("phq9") == recorded
    finally:
        store_b.close()


def test_record_persists_immediately_visible_to_a_fresh_store(tmp_path: Path) -> None:
    path = tmp_path / "record-persist.db"
    store = SqliteCheckInStore(path)
    tracker = PersistentCheckInTracker(store)
    checkin = tracker.record("phq9", _phq9(total=3), DAY_ONE)
    store.close()

    inspector = SqliteCheckInStore(path)
    try:
        assert inspector.load() == (checkin,)
    finally:
        inspector.close()


# ------------------------------------------------- rejected records


def test_unknown_instrument_record_never_reaches_the_store() -> None:
    store = RecordingStore()
    tracker = PersistentCheckInTracker(store)

    with pytest.raises(ValueError, match="instrument"):
        tracker.record("not_an_instrument", (0,) * 9, DAY_ONE)

    assert store.calls == []


def test_out_of_order_record_never_reaches_the_store() -> None:
    future = _checkin(DAY_ONE + datetime.timedelta(days=10))
    store = RecordingStore(loaded=[future])
    tracker = PersistentCheckInTracker(store)

    with pytest.raises(ValueError, match="out-of-order"):
        tracker.record("phq9", _phq9(total=2), DAY_ONE)

    assert store.calls == []


# ------------------------------------------------ rollback on persist failure


def test_persist_failure_on_first_record_rolls_back_memory_completely() -> None:
    error = RuntimeError("db exploded: secret-abc")
    store = RecordingStore(append_error=error)
    tracker = PersistentCheckInTracker(store)

    with pytest.raises(RuntimeError) as excinfo:
        tracker.record("phq9", _phq9(total=0), DAY_ONE)

    assert excinfo.value is error  # same instance, re-raised bare
    assert len(store.calls) == 1  # the persist WAS attempted, then rolled back
    assert tracker.baseline("phq9") is None
    assert tracker.latest("phq9") is None
    with pytest.raises(ValueError, match="no check-ins"):
        tracker.history("phq9")  # the emptied per-instrument list was deleted


def test_persist_failure_on_second_record_pops_only_the_failed_checkin() -> None:
    store = RecordingStore()
    tracker = PersistentCheckInTracker(store)
    first = tracker.record("phq9", _phq9(total=1), DAY_ONE)
    error = RuntimeError("db exploded: secret-abc")
    store.append_error = error

    with pytest.raises(RuntimeError) as excinfo:
        tracker.record("phq9", _phq9(total=4), DAY_ONE + datetime.timedelta(days=2))

    assert excinfo.value is error
    assert tracker.history("phq9") == (first,)  # only the failed append was popped
    assert tracker.baseline("phq9") == first
    assert tracker.latest("phq9") == first


# ------------------------------------------------------- read serialization


def test_overrides_keep_parent_read_and_serialization_semantics() -> None:
    store = RecordingStore()
    tracker = PersistentCheckInTracker(store)
    checkin = tracker.record("phq9", _phq9(total=0), DAY_ONE)

    assert tracker.history("phq9") == (checkin,)
    assert tracker.latest("phq9") == checkin
    assert tracker.baseline("phq9") == checkin
    assert tracker.to_dict() == CheckInTracker.to_dict(tracker)
    assert tracker.to_dict() == {
        "checkins": [
            {
                "instrument_id": "phq9",
                "date": "2026-01-01",
                "responses": [0, 0, 0, 0, 0, 0, 0, 0, 0],
                "total": 0,
                "severity_label": "minimal",
                "flags": [],
            }
        ]
    }
    with pytest.raises(ValueError, match="no check-ins"):
        tracker.history("gad7")


# --------------------------------------------------------- policy pass-through


def test_custom_policy_reaches_the_parent_and_drives_early_worsening() -> None:
    policy = EarlyWorseningPolicy(window_days=7)  # default window is 14
    tracker = PersistentCheckInTracker(RecordingStore(), policy=policy)

    tracker.record("phq9", _phq9(total=0), DAY_ONE)
    day_five = tracker.record("phq9", _phq9(total=5), DAY_ONE + datetime.timedelta(days=5))
    assert day_five.flags == (CheckInFlag.EARLY_WORSENSING,)

    # Day 10 is inside the DEFAULT 14-day window but beyond the custom 7-day
    # one: the absence of the flag proves the custom policy reached the parent.
    day_ten = tracker.record("phq9", _phq9(total=10), DAY_ONE + datetime.timedelta(days=10))
    assert day_ten.flags == ()
