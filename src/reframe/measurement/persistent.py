"""Durable check-in tracking: thread-safe tracker over a persistent store.

:class:`PersistentCheckInTracker` extends the deliberately NOT-thread-safe
:class:`~reframe.measurement.tracker.CheckInTracker` with one
``threading.Lock`` (FastAPI sync routes run in a threadpool): ``record``
serializes the memory+store compound operation, and the public reads
(`history`/`latest`/`baseline`/`to_dict`) acquire the same lock. Recorded
flags are restored from the store VERBATIM — loading never re-scores or
re-flags; the recorded flags are the authority. If persisting a newly
recorded check-in fails, the in-memory append is rolled back and the
original exception re-raised, so a check-in exists either everywhere or
nowhere. Persist failures surface to clients as a generic HTTP 500 through
the app's unhandled-exception handler — store internals are never leaked.
"""

import datetime
import threading
from collections.abc import Sequence
from typing import Any

from reframe.measurement.flags import EarlyWorseningPolicy
from reframe.measurement.store import CheckInStore
from reframe.measurement.tracker import CheckIn, CheckInTracker


class PersistentCheckInTracker(CheckInTracker):
    """Thread-safe, durable :class:`CheckInTracker` backed by a :class:`CheckInStore`.

    Differences from the parent (which documents itself NOT thread-safe):

    - **Lock added**: one ``threading.Lock`` guards every compound
      memory+store operation (``record``) and every public read.
    - **Verbatim restore**: ``__init__`` replays ``store.load()`` through
      ``_append_restored`` without re-scoring; a failing ``load()``
      propagates unchanged (loud startup failure).
    - **Rollback**: if ``store.append`` raises after a successful in-memory
      record, the in-memory append is rolled back (the emptied
      per-instrument list is deleted) and the original exception re-raised
      bare — memory and store stay consistent. Callers see such failures as
      a generic HTTP 500 via the app's unhandled-exception handler.
    """

    def __init__(self, store: CheckInStore, policy: EarlyWorseningPolicy | None = None) -> None:
        """Restore the stored history verbatim, then record into memory + store."""
        super().__init__(policy)
        self._store = store
        self._lock = threading.Lock()
        for checkin in store.load():
            self._append_restored(checkin)

    def record(self, instrument_id: str, responses: Sequence[int], date: datetime.date) -> CheckIn:
        """Score, flag, persist, and append one check-in under the lock.

        The parent's ``ValueError`` (unknown instrument, invalid responses,
        out-of-order date) propagates BEFORE the store is touched — rejected
        check-ins never reach the store. If the store append raises, the
        in-memory append is rolled back and the original exception re-raised.

        Raises:
            ValueError: Exactly as the parent (nothing recorded anywhere).
            Exception: Any store failure, after rollback, unchanged.
        """
        with self._lock:
            checkin = super().record(instrument_id, responses, date)
            try:
                self._store.append(checkin)
            except BaseException:
                records = self._records[instrument_id]
                records.pop()
                if not records:
                    del self._records[instrument_id]
                raise
            return checkin

    def history(self, instrument_id: str) -> tuple[CheckIn, ...]:
        """Parent behavior under the shared lock (reads serialize with ``record``)."""
        with self._lock:
            return super().history(instrument_id)

    def latest(self, instrument_id: str) -> CheckIn | None:
        """Parent behavior under the shared lock."""
        with self._lock:
            return super().latest(instrument_id)

    def baseline(self, instrument_id: str) -> CheckIn | None:
        """Parent behavior under the shared lock."""
        with self._lock:
            return super().baseline(instrument_id)

    def to_dict(self) -> dict[str, Any]:
        """Parent serialization semantics under the shared lock."""
        with self._lock:
            return super().to_dict()
