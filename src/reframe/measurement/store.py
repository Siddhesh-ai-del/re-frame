"""Durable check-in storage: single-connection, lock-guarded, fail-closed SQLite.

:class:`SqliteCheckInStore` is the v1 persistence engine for the single-user
local product: ONE SQLite connection per store, closed when the app shuts
down (``create_service`` registers the shutdown handler when it creates the
store), with every access guarded by
an internal ``threading.Lock`` because FastAPI sync routes run in a
threadpool. Loading is fail-closed — a malformed stored row makes
:meth:`load` RAISE naming the row id (a loud startup failure); rows are never
silently skipped. :class:`CheckInStore` is the protocol that keeps the engine
swappable and lets tests stub persistence.
"""

import datetime
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Protocol

from reframe.measurement.flags import CheckInFlag
from reframe.measurement.tracker import CheckIn

_TABLE_DDL = (
    "CREATE TABLE IF NOT EXISTS checkins ("
    "id INTEGER PRIMARY KEY, instrument_id TEXT NOT NULL, "
    "checkin_date TEXT NOT NULL, responses TEXT NOT NULL, "
    "total INTEGER NOT NULL, severity_label TEXT, flags TEXT NOT NULL)"
)

_INSERT_SQL = (
    "INSERT INTO checkins "
    "(instrument_id, checkin_date, responses, total, severity_label, flags) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)


def _is_plain_int(value: object) -> bool:
    """True only for real ints — bools are rejected even though bool subclasses int."""
    if isinstance(value, bool):
        return False
    return isinstance(value, int)


class CheckInStore(Protocol):
    """Persistence contract for recorded check-ins: append-only, ordered load."""

    def append(self, checkin: CheckIn) -> None:
        """Durably persist one check-in; raise on failure (no suppression)."""
        ...

    def load(self) -> tuple[CheckIn, ...]:
        """All stored check-ins in insertion order; raise on any malformed row."""
        ...

    def close(self) -> None:
        """Release underlying resources (a no-op for in-memory stubs)."""
        ...


class SqliteCheckInStore:
    """Lock-guarded SQLite implementation of :class:`CheckInStore`.

    One connection per store (``check_same_thread=False``) for the process
    lifetime; a private ``threading.Lock`` serializes every compound access.
    Loading validates each row fail-closed via :meth:`_checkin_from_row` —
    this class does its own validation and never reaches into tracker
    internals.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(str(db_path), check_same_thread=False)
        with self._lock:
            self._connection.execute(_TABLE_DDL)
            self._connection.commit()

    def append(self, checkin: CheckIn) -> None:
        """Insert one check-in (commit inside the lock); propagate any failure."""
        with self._lock:
            self._connection.execute(
                _INSERT_SQL,
                (
                    checkin.instrument_id,
                    checkin.date.isoformat(),
                    json.dumps(list(checkin.responses)),
                    checkin.total,
                    checkin.severity_label,
                    json.dumps([flag.value for flag in checkin.flags]),
                ),
            )
            self._connection.commit()

    def load(self) -> tuple[CheckIn, ...]:
        """All stored check-ins in insertion (rowid) order; ``()`` for an empty table.

        Raises:
            ValueError: If any stored row is malformed — fail-closed, never
                silently skipped; the message names the row id.
        """
        with self._lock:
            rows = self._connection.execute("SELECT * FROM checkins ORDER BY id").fetchall()
            checkins: list[CheckIn] = []
            for row in rows:
                checkins.append(self._checkin_from_row(row))
            return tuple(checkins)

    def close(self) -> None:
        """Close the connection (inside the lock, like every access)."""
        with self._lock:
            self._connection.close()

    @staticmethod
    def _checkin_from_row(row: tuple[Any, ...]) -> CheckIn:
        """Validate one raw row fail-closed and rebuild its :class:`CheckIn`.

        Raises:
            ValueError: Naming the row id for any malformed field — a bad
                instrument id, unparsable date, bad/non-list responses JSON,
                non-int response items (bools rejected), non-int total (bool
                rejected), non-str/None severity label, or bad/non-list
                flags JSON with an unknown flag value.
        """
        (
            row_id,
            instrument_id,
            checkin_date,
            responses_json,
            total,
            severity_label,
            flags_json,
        ) = row
        label = f"malformed check-in row {row_id}"
        if not (isinstance(instrument_id, str) and instrument_id):
            raise ValueError(f"{label}: bad instrument_id {instrument_id!r}")
        try:
            checkin_parsed_date = datetime.date.fromisoformat(checkin_date)
        except ValueError:
            raise ValueError(f"{label}: bad checkin_date {checkin_date!r}") from None
        try:
            responses = json.loads(responses_json)
        except json.JSONDecodeError:
            raise ValueError(f"{label}: responses is not valid JSON") from None
        if not isinstance(responses, list):
            raise ValueError(f"{label}: responses is not a list: {responses!r}")
        if not all(_is_plain_int(value) for value in responses):
            raise ValueError(f"{label}: non-int in responses: {responses!r}")
        if not isinstance(total, int) or isinstance(total, bool):
            raise ValueError(f"{label}: bad total {total!r}")
        if severity_label is not None and not isinstance(severity_label, str):
            raise ValueError(f"{label}: bad severity_label {severity_label!r}")
        try:
            raw_flags = json.loads(flags_json)
        except json.JSONDecodeError:
            raise ValueError(f"{label}: flags is not valid JSON") from None
        if not isinstance(raw_flags, list):
            raise ValueError(f"{label}: flags is not a list: {raw_flags!r}")
        try:
            flags = tuple(CheckInFlag(value) for value in raw_flags)
        except ValueError:
            raise ValueError(f"{label}: unknown flag value {raw_flags!r}") from None
        return CheckIn(
            instrument_id=instrument_id,
            date=checkin_parsed_date,
            responses=tuple(responses),
            total=total,
            severity_label=severity_label,
            flags=flags,
        )
