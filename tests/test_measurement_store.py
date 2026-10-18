"""Tests for ``reframe.measurement.store`` — durable SQLite check-in storage.

Strict TDD: written BEFORE ``reframe/measurement/store.py`` exists; the first
run must fail with ``ModuleNotFoundError`` (RED).

The store is a single-connection, lock-guarded SQLite engine for the v1
single-user local product. Loading is fail-closed: a malformed stored row
must make ``load()`` RAISE naming the row id — rows are never silently
skipped (loud startup failure, no internals leaked to callers later).
"""

import datetime
import sqlite3
from pathlib import Path

import pytest

from reframe.measurement.flags import CheckInFlag
from reframe.measurement.store import CheckInStore, SqliteCheckInStore
from reframe.measurement.tracker import CheckIn

DAY_ONE = datetime.date(2026, 1, 1)

#: Column defaults for a directly inserted row; each malformed case overrides one.
_DEFAULT_ROW: dict[str, object] = {
    "instrument_id": "phq9",
    "checkin_date": "2026-01-01",
    "responses": "[0, 0, 0, 0, 0, 0, 0, 0, 0]",
    "total": 0,
    "severity_label": None,
    "flags": "[]",
}

_INSERT_SQL = (
    "INSERT INTO checkins "
    "(instrument_id, checkin_date, responses, total, severity_label, flags) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)


def _checkin(
    *,
    instrument_id: str = "phq9",
    date: datetime.date = DAY_ONE,
    responses: tuple[int, ...] = (0,) * 9,
    total: int = 0,
    severity_label: str | None = None,
    flags: tuple[CheckInFlag, ...] = (),
) -> CheckIn:
    """A schema-valid :class:`CheckIn` for store round trips (store is self-contained)."""
    return CheckIn(instrument_id, date, responses, total, severity_label, flags)


def _prime_table(db_path: Path) -> None:
    """Create the table through the real store, then close it (close is idempotent)."""
    SqliteCheckInStore(db_path).close()


def _insert_raw_row(db_path: Path, **overrides: object) -> int:
    """Insert one row directly with ``sqlite3``, bypassing ``append``; return its id."""
    row = dict(_DEFAULT_ROW)
    row.update(overrides)
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            _INSERT_SQL,
            (
                row["instrument_id"],
                row["checkin_date"],
                row["responses"],
                row["total"],
                row["severity_label"],
                row["flags"],
            ),
        )
        connection.commit()
        row_id = cursor.lastrowid
    finally:
        connection.close()
    assert row_id is not None
    return int(row_id)


# ------------------------------------------------------------- round trip


def test_append_then_load_round_trips_every_field(tmp_path: Path) -> None:
    store: CheckInStore = SqliteCheckInStore(tmp_path / "roundtrip.db")
    unlabelled = _checkin(flags=(CheckInFlag.ESCALATE,))
    labelled = _checkin(
        date=DAY_ONE + datetime.timedelta(days=1),
        total=12,
        severity_label="moderate",
    )
    try:
        store.append(unlabelled)
        store.append(labelled)
        loaded = store.load()
    finally:
        store.close()

    assert loaded == (unlabelled, labelled)
    assert loaded[0].date == DAY_ONE
    assert loaded[0].responses == (0,) * 9
    assert loaded[0].severity_label is None
    assert loaded[0].flags == (CheckInFlag.ESCALATE,)
    assert loaded[1].severity_label == "moderate"
    assert loaded[1].date == DAY_ONE + datetime.timedelta(days=1)


def test_rows_survive_close_and_reopen_on_the_same_path(tmp_path: Path) -> None:
    path = tmp_path / "durable.db"
    checkin = _checkin(total=9, severity_label="mild")
    first = SqliteCheckInStore(path)
    first.append(checkin)
    first.close()

    second = SqliteCheckInStore(path)
    try:
        assert second.load() == (checkin,)
    finally:
        second.close()


def test_load_returns_empty_tuple_for_an_empty_database(tmp_path: Path) -> None:
    store = SqliteCheckInStore(tmp_path / "empty.db")
    try:
        assert store.load() == ()
    finally:
        store.close()


def test_load_preserves_global_insertion_order_across_instruments(tmp_path: Path) -> None:
    store = SqliteCheckInStore(tmp_path / "order.db")
    phq9_first = _checkin()
    gad7 = _checkin(instrument_id="gad7", responses=(0,) * 7)
    phq9_second = _checkin(date=DAY_ONE + datetime.timedelta(days=1), total=3)
    try:
        for checkin in (phq9_first, gad7, phq9_second):
            store.append(checkin)
        assert store.load() == (phq9_first, gad7, phq9_second)
    finally:
        store.close()


def test_store_accepts_a_str_db_path(tmp_path: Path) -> None:
    store = SqliteCheckInStore(str(tmp_path / "strpath.db"))
    try:
        assert store.load() == ()
    finally:
        store.close()


# ------------------------------------------------------- fail-closed loading


@pytest.mark.parametrize(
    ("column", "value"),
    [
        pytest.param("responses", "{not json", id="responses-bad-json"),
        pytest.param("responses", "5", id="responses-not-a-list"),
        pytest.param("responses", "[true]", id="responses-bool-item"),
        pytest.param("responses", '["x"]', id="responses-str-item"),
        pytest.param("flags", "{oops", id="flags-bad-json"),
        pytest.param("flags", "5", id="flags-not-a-list"),
        pytest.param("flags", '["banana"]', id="flags-unknown-value"),
        pytest.param("checkin_date", "not-a-date", id="bad-checkin-date"),
        pytest.param("total", "not-an-int", id="total-non-int"),
        pytest.param("instrument_id", "", id="empty-instrument-id"),
        pytest.param("severity_label", b"blob", id="severity-non-str"),
    ],
)
def test_malformed_row_makes_load_raise_naming_the_row_id(
    tmp_path: Path, column: str, value: object
) -> None:
    path = tmp_path / "malformed.db"
    _prime_table(path)
    row_id = _insert_raw_row(path, **{column: value})
    store = SqliteCheckInStore(path)
    try:
        with pytest.raises(ValueError) as excinfo:
            store.load()
        message = str(excinfo.value)
        assert "row" in message
        assert str(row_id) in message
    finally:
        store.close()


def test_unknown_flag_value_error_names_the_bad_value(tmp_path: Path) -> None:
    path = tmp_path / "badflag.db"
    _prime_table(path)
    _insert_raw_row(path, flags='["banana"]')
    store = SqliteCheckInStore(path)
    try:
        with pytest.raises(ValueError) as excinfo:
            store.load()
        assert "banana" in str(excinfo.value)
    finally:
        store.close()


# ------------------------------------------------------------- lifecycle


def test_append_after_close_raises_programming_error(tmp_path: Path) -> None:
    store = SqliteCheckInStore(tmp_path / "closed.db")
    store.close()

    with pytest.raises(sqlite3.ProgrammingError):
        store.append(_checkin())


def test_two_stores_on_the_same_path_see_all_rows(tmp_path: Path) -> None:
    path = tmp_path / "shared.db"
    first = SqliteCheckInStore(path)
    second = SqliteCheckInStore(path)
    checkin = _checkin()
    try:
        first.append(checkin)
        assert first.load() == (checkin,)
        assert second.load() == (checkin,)
    finally:
        first.close()
        second.close()
