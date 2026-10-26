"""Tests for ``reframe.evaluation.store`` — durable SQLite adverse-event storage.

Strict TDD: written BEFORE ``reframe/evaluation/`` exists; the first run must
fail with ``ModuleNotFoundError`` (RED).

The store mirrors ``reframe.measurement.store``: one lock-guarded SQLite
connection, insertion (rowid) order on load, and fail-closed row validation —
a malformed stored row makes ``load()`` RAISE naming the event id, never
silently skipped. ``update_followup`` raises on an unknown id instead of
pretending a record was updated (safety-monitoring honesty).
"""

import datetime
import sqlite3
from pathlib import Path

import pytest

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.evaluation.store import AdverseEventStore, SqliteAdverseEventStore

UTC = datetime.UTC
NOW = datetime.datetime(2026, 10, 26, 12, 0, tzinfo=UTC)

#: Column defaults for a directly inserted row; each malformed case overrides one.
_DEFAULT_ROW: dict[str, object] = {
    "id": "evt-0001",
    "type": "crisis_response_failure",
    "detected_at": "2026-10-26T12:00:00+00:00",
    "source": "review",
    "serious": 1,
    "followup_completed": 0,
    "reference": None,
}

_INSERT_SQL = (
    "INSERT INTO adverse_events "
    "(id, type, detected_at, source, serious, followup_completed, reference) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)


def _event(
    *,
    id: str = "evt-0001",
    type: AEType = AEType.CRISIS_RESPONSE_FAILURE,
    source: AESource = AESource.AUTOMATIC,
    serious: bool = True,
    reference: str | None = None,
) -> AdverseEvent:
    """A schema-valid :class:`AdverseEvent` for store round trips."""
    return AdverseEvent(
        id=id,
        type=type,
        source=source,
        detected_at=NOW,
        serious=serious,
        followup_completed=False,
        reference=reference,
    )


def _prime_table(db_path: Path) -> None:
    """Create the table through the real store, then close it (close is idempotent)."""
    SqliteAdverseEventStore(db_path).close()


def _insert_raw_row(db_path: Path, **overrides: object) -> object:
    """Insert one row directly with ``sqlite3``, bypassing ``append``; return its id."""
    row = dict(_DEFAULT_ROW)
    row.update(overrides)
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            _INSERT_SQL,
            (
                row["id"],
                row["type"],
                row["detected_at"],
                row["source"],
                row["serious"],
                row["followup_completed"],
                row["reference"],
            ),
        )
        connection.commit()
        row_id = cursor.lastrowid
    finally:
        connection.close()
    assert row_id is not None
    return row_id


# ------------------------------------------------------------- round trip


def test_append_then_load_round_trips_every_field(tmp_path: Path) -> None:
    store: AdverseEventStore = SqliteAdverseEventStore(tmp_path / "roundtrip.db")
    serious = _event(reference="check-in phq9 2026-10-08 total=16")
    non_serious = _event(
        id="evt-0002",
        type=AEType.SYCOPHANCY_EPISODE,
        source=AESource.REVIEW,
        serious=False,
        reference="session 3 turn 14",
    )
    try:
        store.append(serious)
        store.append(non_serious)
        loaded = store.load()
    finally:
        store.close()

    assert loaded == (serious, non_serious)
    assert loaded[0].detected_at == NOW
    assert loaded[0].reference == "check-in phq9 2026-10-08 total=16"
    assert loaded[1].serious is False
    assert loaded[1].source is AESource.REVIEW


def test_rows_survive_close_and_reopen_on_the_same_path(tmp_path: Path) -> None:
    path = tmp_path / "durable.db"
    event = _event(reference="audit-miss sha256:0123456789ab")
    first = SqliteAdverseEventStore(path)
    first.append(event)
    first.close()

    second = SqliteAdverseEventStore(path)
    try:
        assert second.load() == (event,)
    finally:
        second.close()


def test_load_returns_empty_tuple_for_an_empty_database(tmp_path: Path) -> None:
    store = SqliteAdverseEventStore(tmp_path / "empty.db")
    try:
        assert store.load() == ()
    finally:
        store.close()


def test_load_preserves_insertion_order_not_id_order(tmp_path: Path) -> None:
    store = SqliteAdverseEventStore(tmp_path / "order.db")
    first = _event(id="zzz-first", serious=False)
    second = _event(id="aaa-second")
    third = _event(id="mmm-third", serious=False)
    try:
        for event in (first, second, third):
            store.append(event)
        assert [event.id for event in store.load()] == ["zzz-first", "aaa-second", "mmm-third"]
    finally:
        store.close()


def test_store_accepts_a_str_db_path(tmp_path: Path) -> None:
    store = SqliteAdverseEventStore(str(tmp_path / "strpath.db"))
    try:
        assert store.load() == ()
    finally:
        store.close()


# ------------------------------------------------------- fail-closed loading


@pytest.mark.parametrize(
    ("column", "value"),
    [
        pytest.param("id", "", id="empty-id"),
        pytest.param("id", None, id="null-id"),
        pytest.param("type", "banana", id="unknown-type"),
        pytest.param("source", "banana", id="unknown-source"),
        pytest.param("detected_at", "not-a-date", id="unparsable-detected-at"),
        pytest.param("detected_at", b"blob", id="non-str-detected-at"),
        pytest.param("detected_at", "2026-10-26T12:00:00", id="naive-detected-at"),
        pytest.param("serious", 5, id="serious-out-of-range"),
        pytest.param("serious", "banana", id="serious-non-int"),
        pytest.param("followup_completed", 7, id="followup-out-of-range"),
        pytest.param("followup_completed", "banana", id="followup-non-int"),
        pytest.param("reference", "", id="empty-reference"),
        pytest.param("reference", "   ", id="blank-reference"),
        pytest.param("reference", "x" * 201, id="overlong-reference"),
        pytest.param("reference", b"blob", id="non-str-reference"),
    ],
)
def test_malformed_row_makes_load_raise_naming_the_event_id(
    tmp_path: Path, column: str, value: object
) -> None:
    path = tmp_path / "malformed.db"
    _prime_table(path)
    overrides = {column: value}
    if column != "id":
        overrides["id"] = "evt-bad"
    _insert_raw_row(path, **overrides)
    event_id: object = overrides["id"]
    store = SqliteAdverseEventStore(path)
    try:
        with pytest.raises(ValueError) as excinfo:
            store.load()
        message = str(excinfo.value)
        assert "malformed adverse-event row" in message
        if event_id:
            assert str(event_id) in message
    finally:
        store.close()


def test_unknown_type_error_names_the_bad_value(tmp_path: Path) -> None:
    path = tmp_path / "badtype.db"
    _prime_table(path)
    _insert_raw_row(path, type="banana")
    store = SqliteAdverseEventStore(path)
    try:
        with pytest.raises(ValueError) as excinfo:
            store.load()
        assert "banana" in str(excinfo.value)
    finally:
        store.close()


# ------------------------------------------------------- update_followup (D3)


def test_update_followup_persists_across_a_reopen(tmp_path: Path) -> None:
    path = tmp_path / "followup.db"
    event = _event(id="evt-fu", serious=True)
    first = SqliteAdverseEventStore(path)
    first.append(event)
    first.update_followup("evt-fu", True)
    first.close()

    second = SqliteAdverseEventStore(path)
    try:
        reloaded = second.load()
    finally:
        second.close()

    assert reloaded == (event.with_followup_completed(),)


def test_update_followup_on_an_unknown_id_raises_value_error(tmp_path: Path) -> None:
    store: AdverseEventStore = SqliteAdverseEventStore(tmp_path / "followup-unknown.db")
    try:
        with pytest.raises(ValueError):
            store.update_followup("nope", True)
    finally:
        store.close()


# ------------------------------------------------------------- lifecycle


def test_append_after_close_raises_programming_error(tmp_path: Path) -> None:
    store = SqliteAdverseEventStore(tmp_path / "closed.db")
    store.close()

    with pytest.raises(sqlite3.ProgrammingError):
        store.append(_event())


def test_update_followup_after_close_raises_programming_error(tmp_path: Path) -> None:
    store = SqliteAdverseEventStore(tmp_path / "closed-update.db")
    store.close()

    with pytest.raises(sqlite3.ProgrammingError):
        store.update_followup("evt-0001", True)


def test_two_stores_on_the_same_path_see_all_rows(tmp_path: Path) -> None:
    path = tmp_path / "shared.db"
    first = SqliteAdverseEventStore(path)
    second = SqliteAdverseEventStore(path)
    event = _event(serious=False)
    try:
        first.append(event)
        assert first.load() == (event,)
        assert second.load() == (event,)
    finally:
        first.close()
        second.close()
