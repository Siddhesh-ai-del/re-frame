"""Durable adverse-event storage: single-connection, lock-guarded, fail-closed SQLite.

Mirrors :mod:`reframe.measurement.store`: ONE SQLite connection per store
opened with ``check_same_thread=False`` for the process lifetime, every
access guarded by an internal ``threading.Lock`` (FastAPI sync routes run
in a threadpool). Loading is fail-closed — a malformed stored row makes
:meth:`load` RAISE naming the event id (a loud startup failure); rows are
never silently skipped. ``update_followup`` raises on an unknown id
instead of pretending a safety record was updated. :class:`AdverseEventStore`
is the protocol that keeps the engine swappable and lets tests stub
persistence.
"""

import datetime
import sqlite3
import threading
from pathlib import Path
from typing import Any, Protocol

from reframe.evaluation.adverse_events import (
    _MAX_REFERENCE_CHARS,
    AdverseEvent,
    AESource,
    AEType,
)

_TABLE_DDL = (
    "CREATE TABLE IF NOT EXISTS adverse_events ("
    "id TEXT PRIMARY KEY, type TEXT NOT NULL, detected_at TEXT NOT NULL, "
    "source TEXT NOT NULL, serious INTEGER NOT NULL, "
    "followup_completed INTEGER NOT NULL, reference TEXT)"
)

_INSERT_SQL = (
    "INSERT INTO adverse_events "
    "(id, type, detected_at, source, serious, followup_completed, reference) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)


class AdverseEventStore(Protocol):
    """Persistence contract for adverse events: append, ordered load, follow-up."""

    def append(self, event: AdverseEvent) -> None:
        """Durably persist one event; raise on failure (no suppression)."""
        ...

    def load(self) -> tuple[AdverseEvent, ...]:
        """All stored events in insertion order; raise on any malformed row."""
        ...

    def update_followup(self, event_id: str, completed: bool) -> None:
        """Persist the follow-up marker for one event; raise on an unknown id."""
        ...

    def close(self) -> None:
        """Release underlying resources (a no-op for in-memory stubs)."""
        ...


class SqliteAdverseEventStore:
    """Lock-guarded SQLite implementation of :class:`AdverseEventStore`.

    One connection per store; a private ``threading.Lock`` serializes every
    compound access. Loading validates each row fail-closed via
    :meth:`_event_from_row` — this class does its own validation and never
    reaches into record internals.
    """

    def __init__(self, db_path: str | Path) -> None:
        """Open (or create) the database file and ensure the table exists."""
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(str(db_path), check_same_thread=False)
        with self._lock:
            self._connection.execute(_TABLE_DDL)
            self._connection.commit()

    def append(self, event: AdverseEvent) -> None:
        """Insert one event (commit inside the lock); propagate any failure."""
        with self._lock:
            self._connection.execute(
                _INSERT_SQL,
                (
                    event.id,
                    event.type.value,
                    event.detected_at.isoformat(),
                    event.source.value,
                    int(event.serious),
                    int(event.followup_completed),
                    event.reference,
                ),
            )
            self._connection.commit()

    def load(self) -> tuple[AdverseEvent, ...]:
        """All stored events in insertion (rowid) order; ``()`` for an empty table.

        Ordered by ``rowid`` deliberately — the TEXT primary key is a uuid hex
        string, so ``ORDER BY id`` would NOT be insertion order.

        Raises:
            ValueError: If any stored row is malformed — fail-closed, never
                silently skipped; the message names the event id.
        """
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM adverse_events ORDER BY rowid"
            ).fetchall()
            events: list[AdverseEvent] = []
            for row in rows:
                events.append(self._event_from_row(row))
            return tuple(events)

    def update_followup(self, event_id: str, completed: bool) -> None:
        """Persist the follow-up marker for ``event_id`` (commit inside the lock).

        Raises:
            ValueError: If no row matches ``event_id`` — an unknown id is a
                loud failure, never a silent no-op that pretends a safety
                record was updated.
        """
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE adverse_events SET followup_completed = ? WHERE id = ?",
                (int(completed), event_id),
            )
            self._connection.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"unknown adverse event id {event_id!r}")

    def close(self) -> None:
        """Close the connection (inside the lock, like every access)."""
        with self._lock:
            self._connection.close()

    @staticmethod
    def _event_from_row(row: tuple[Any, ...]) -> AdverseEvent:
        """Validate one raw row fail-closed and rebuild its :class:`AdverseEvent`.

        Raises:
            ValueError: Naming the event id for any malformed field — an empty
                id, an unknown type/source value, an unparsable or naive
                ``detected_at``, a ``serious``/``followup_completed`` that is
                not a literal 0/1, or a reference that is not ``None``/str or
                violates the D1 locator rule (blank after stripping, over 200
                chars).
        """
        (
            row_id,
            type_value,
            detected_at_text,
            source_value,
            serious,
            followup_completed,
            reference,
        ) = row
        label = f"malformed adverse-event row {row_id!r}"
        if not (isinstance(row_id, str) and row_id):
            raise ValueError(f"{label}: bad id {row_id!r}")
        try:
            ae_type = AEType(type_value)
        except ValueError:
            raise ValueError(f"{label}: unknown type {type_value!r}") from None
        try:
            ae_source = AESource(source_value)
        except ValueError:
            raise ValueError(f"{label}: unknown source {source_value!r}") from None
        try:
            detected_at = datetime.datetime.fromisoformat(detected_at_text)
        except (ValueError, TypeError):
            raise ValueError(f"{label}: unparsable detected_at") from None
        if detected_at.utcoffset() is None:
            raise ValueError(f"{label}: naive detected_at {detected_at_text!r}")
        if not isinstance(serious, int) or serious not in (0, 1):
            raise ValueError(f"{label}: bad serious {serious!r}")
        if not isinstance(followup_completed, int) or followup_completed not in (0, 1):
            raise ValueError(f"{label}: bad followup_completed {followup_completed!r}")
        if reference is None:
            locator: str | None = None
        elif not isinstance(reference, str):
            raise ValueError(f"{label}: bad reference {reference!r}")
        else:
            locator = reference.strip()
            if not locator or len(locator) > _MAX_REFERENCE_CHARS:
                raise ValueError(f"{label}: reference violates the locator rule")
        return AdverseEvent(
            id=row_id,
            type=ae_type,
            source=ae_source,
            detected_at=detected_at,
            serious=bool(serious),
            followup_completed=bool(followup_completed),
            reference=locator,
        )
