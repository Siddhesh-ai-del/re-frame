"""Tests for ``reframe.evaluation.log`` — in-memory and durable AE logs.

Strict TDD: written BEFORE ``reframe/evaluation/`` exists; the first run must
fail with ``ModuleNotFoundError`` (RED).

``AdverseEventLog`` is the fail-closed in-memory log (duplicate ids rejected,
insertion order preserved). ``PersistentAdverseEventLog`` mirrors
``PersistentCheckInTracker``'s all-or-nothing semantics (D7): a store failure
rolls the in-memory change back and re-raises bare — memory and store never
diverge, and the AE response never pretends success.
"""

import datetime
from collections.abc import Sequence
from pathlib import Path

import pytest

from reframe.evaluation import (
    AdverseEvent,
    AdverseEventLog,
    AESource,
    AEType,
    PersistentAdverseEventLog,
    SqliteAdverseEventStore,
)
from reframe.evaluation.store import AdverseEventStore

UTC = datetime.UTC
NOW = datetime.datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


class RecordingStore:
    """Stub AdverseEventStore: replays a fixed load(), records calls, scripted failures."""

    def __init__(
        self,
        loaded: Sequence[AdverseEvent] = (),
        *,
        append_error: BaseException | None = None,
        load_error: BaseException | None = None,
    ) -> None:
        self.loaded = tuple(loaded)
        self.appended: list[AdverseEvent] = []
        self.updates: list[tuple[str, bool]] = []
        self.append_error = append_error
        self.load_error = load_error
        self.update_error: BaseException | None = None
        self.close_calls = 0

    def append(self, event: AdverseEvent) -> None:
        self.appended.append(event)
        if self.append_error is not None:
            raise self.append_error

    def load(self) -> tuple[AdverseEvent, ...]:
        if self.load_error is not None:
            raise self.load_error
        return self.loaded

    def update_followup(self, event_id: str, completed: bool) -> None:
        self.updates.append((event_id, completed))
        if self.update_error is not None:
            raise self.update_error

    def close(self) -> None:
        self.close_calls += 1


def _event(
    *,
    id: str = "evt-0001",
    type: AEType = AEType.TRANSIENT_EARLY_WORSENSING,
    serious: bool = False,
    reference: str | None = None,
) -> AdverseEvent:
    return AdverseEvent(
        id=id,
        type=type,
        source=AESource.AUTOMATIC,
        detected_at=NOW,
        serious=serious,
        followup_completed=False,
        reference=reference,
    )


# ---------------------------------------------------------------------------
# AdverseEventLog — seed order, append order, get, duplicate rejection
# ---------------------------------------------------------------------------


def test_seeded_events_keep_their_order() -> None:
    first = _event(id="e1")
    second = _event(id="e2")

    log = AdverseEventLog([first, second])

    assert log.events() == (first, second)


def test_default_construction_is_an_empty_log() -> None:
    assert AdverseEventLog().events() == ()


def test_appended_events_keep_insertion_order() -> None:
    log = AdverseEventLog()
    first = _event(id="e1")
    second = _event(id="e2")

    log.append(first)
    log.append(second)

    assert log.events() == (first, second)


def test_get_returns_the_event_on_a_hit_and_none_on_a_miss() -> None:
    event = _event(id="e1")
    log = AdverseEventLog([event])

    assert log.get("e1") is event
    assert log.get("nope") is None
    assert AdverseEventLog().get("e1") is None


def test_duplicate_id_in_the_seed_is_rejected() -> None:
    with pytest.raises(ValueError):
        AdverseEventLog([_event(id="e1"), _event(id="e1")])


def test_duplicate_id_on_append_is_rejected() -> None:
    event = _event(id="e1")
    log = AdverseEventLog([event])

    with pytest.raises(ValueError):
        log.append(_event(id="e1"))

    assert log.events() == (event,)


def test_complete_followup_returns_the_replaced_instance_and_leaves_others_alone() -> None:
    first = _event(id="e1", serious=True)
    second = _event(id="e2", serious=True)
    log = AdverseEventLog([first, second])

    replaced = log.complete_followup("e2")

    assert replaced.followup_completed is True
    assert replaced.id == "e2"
    assert log.get("e2") is replaced
    assert log.events() == (first, replaced)
    assert log.get("e1") is first
    assert first.followup_completed is False


def test_complete_followup_with_an_unknown_id_raises_key_error() -> None:
    log = AdverseEventLog([_event(id="e1")])

    with pytest.raises(KeyError):
        log.complete_followup("nope")


# ---------------------------------------------------------------------------
# PersistentAdverseEventLog — load on init, all-or-nothing writes (D7)
# ---------------------------------------------------------------------------


def test_init_restores_every_event_from_the_store() -> None:
    first = _event(id="e1")
    second = _event(id="e2")

    log = PersistentAdverseEventLog(RecordingStore(loaded=[first, second]))

    assert log.events() == (first, second)


def test_init_propagates_a_store_load_failure_unchanged() -> None:
    store = RecordingStore(load_error=ValueError("malformed adverse-event row 'evt-x'"))

    with pytest.raises(ValueError) as excinfo:
        PersistentAdverseEventLog(store)

    assert excinfo.value is store.load_error


def test_append_reaches_the_store() -> None:
    store = RecordingStore()
    log = PersistentAdverseEventLog(store)
    event = _event(id="e1")

    log.append(event)

    assert store.appended == [event]
    assert log.events() == (event,)


def test_append_store_failure_rolls_back_memory_and_reraises_bare() -> None:
    error = RuntimeError("db exploded: secret-abc")
    store = RecordingStore(append_error=error)
    log = PersistentAdverseEventLog(store)

    with pytest.raises(RuntimeError) as excinfo:
        log.append(_event(id="e1"))

    assert excinfo.value is error
    assert len(store.appended) == 1  # the persist WAS attempted, then rolled back
    assert log.events() == ()


def test_append_store_failure_rolls_back_only_the_new_event() -> None:
    seed = _event(id="seed")
    error = RuntimeError("db exploded: secret-abc")
    store = RecordingStore(loaded=[seed], append_error=error)
    log = PersistentAdverseEventLog(store)

    with pytest.raises(RuntimeError) as excinfo:
        log.append(_event(id="new"))

    assert excinfo.value is error
    assert log.events() == (seed,)
    assert log.get("seed") is seed


def test_duplicate_append_never_reaches_the_store() -> None:
    store = RecordingStore()
    log = PersistentAdverseEventLog(store)
    event = _event(id="e1")
    log.append(event)

    with pytest.raises(ValueError):
        log.append(_event(id="e1"))

    assert store.appended == [event]


def test_complete_followup_persists_through_store_update_followup() -> None:
    event = _event(id="e1", serious=True)
    store = RecordingStore(loaded=[event])
    log = PersistentAdverseEventLog(store)

    replaced = log.complete_followup("e1")

    assert store.updates == [("e1", True)]
    assert replaced.followup_completed is True
    assert log.get("e1") is replaced


def test_complete_followup_unknown_id_raises_without_touching_the_store() -> None:
    store = RecordingStore(loaded=[_event(id="e1")])
    log = PersistentAdverseEventLog(store)

    with pytest.raises(KeyError):
        log.complete_followup("nope")

    assert store.updates == []


def test_store_update_failure_restores_the_previous_instance_and_reraises() -> None:
    first = _event(id="e1", serious=True)
    second = _event(id="e2", serious=True)
    store = RecordingStore(loaded=[first, second])
    log = PersistentAdverseEventLog(store)
    error = RuntimeError("db exploded: secret-abc")
    store.update_error = error

    with pytest.raises(RuntimeError) as excinfo:
        log.complete_followup("e1")

    assert excinfo.value is error
    assert store.updates == [("e1", True)]
    assert log.events() == (first, second)
    assert log.get("e1") is first


# ---------------------------------------------------------- real SQLite chain


def test_persistent_log_survives_recreation_over_the_same_sqlite_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ae.db"
    first_store: AdverseEventStore = SqliteAdverseEventStore(path)
    first_log = PersistentAdverseEventLog(first_store)
    event = _event(id="evt-real", serious=True)
    first_log.append(event)
    first_store.close()

    second_store = SqliteAdverseEventStore(path)
    try:
        second_log = PersistentAdverseEventLog(second_store)
        assert second_log.events() == (event,)
        replaced = second_log.complete_followup("evt-real")
        assert replaced.followup_completed is True
        assert second_store.load() == (replaced,)
    finally:
        second_store.close()
