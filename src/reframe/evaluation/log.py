"""In-memory and durable adverse-event logs.

:class:`AdverseEventLog` is the fail-closed in-memory log: insertion order
preserved, duplicate ids rejected on seed and append, unknown follow-up
ids raise. :class:`PersistentAdverseEventLog` mirrors
:class:`reframe.measurement.persistent.PersistentCheckInTracker`'s
all-or-nothing semantics (D7): every write lands in memory first, then the
store; if the store write fails the in-memory change is rolled back and
the original exception re-raised bare, so the log exists either everywhere
or nowhere and the AE response never pretends success. Persist failures
surface to clients as a generic HTTP 500 through the app's
unhandled-exception handler — store internals are never leaked.
"""

import threading
from collections.abc import Sequence

from reframe.evaluation.adverse_events import AdverseEvent
from reframe.evaluation.store import AdverseEventStore


class AdverseEventLog:
    """In-memory adverse-event log: insertion-ordered, duplicate ids rejected."""

    def __init__(self, events: Sequence[AdverseEvent] = ()) -> None:
        """Seed the log from ``events`` in order; duplicate ids are rejected."""
        self._events: list[AdverseEvent] = []
        for event in events:
            self._append_unique(event)

    def append(self, event: AdverseEvent) -> None:
        """Append one event at the tail.

        Raises:
            ValueError: If the id is already logged — ids are unique, fail-closed.
        """
        self._append_unique(event)

    def events(self) -> tuple[AdverseEvent, ...]:
        """Every logged event in insertion order."""
        return tuple(self._events)

    def get(self, event_id: str) -> AdverseEvent | None:
        """The event with ``event_id``, or ``None`` when it is not logged."""
        for event in self._events:
            if event.id == event_id:
                return event
        return None

    def complete_followup(self, event_id: str) -> AdverseEvent:
        """Replace the event with ``event_id``, follow-up completed.

        Args:
            event_id: The logged event to mark as followed-up.

        Returns:
            The REPLACED frozen instance now shown in the log.

        Raises:
            KeyError: If ``event_id`` is not logged.
        """
        for index, event in enumerate(self._events):
            if event.id == event_id:
                replaced = event.with_followup_completed(True)
                self._events[index] = replaced
                return replaced
        raise KeyError(event_id)

    def _append_unique(self, event: AdverseEvent) -> None:
        """Append after the duplicate-id check; used by seed and append alike."""
        if any(existing.id == event.id for existing in self._events):
            raise ValueError(f"duplicate adverse event id {event.id!r}")
        self._events.append(event)


class PersistentAdverseEventLog(AdverseEventLog):
    """Thread-safe durable log over an :class:`AdverseEventStore` (D7).

    Differences from the parent:

    - **Load**: ``__init__`` replays ``store.load()`` through the parent's
      fail-closed seed (verbatim, via the parent's non-overridable seeding
      path — never re-appended to the store); a failing ``load()``
      propagates unchanged (loud startup failure).
    - **Rollback**: if ``store.append`` raises after a successful
      in-memory append, the in-memory append is popped and the original
      exception re-raised bare — memory and store stay consistent.
    - **Follow-up**: the store update runs after the in-memory replacement;
      on store failure the previous instance is restored and the exception
      re-raised bare.
    """

    def __init__(self, store: AdverseEventStore) -> None:
        """Restore the stored events verbatim, then write into memory + store."""
        super().__init__(store.load())
        self._store = store
        self._lock = threading.Lock()

    def append(self, event: AdverseEvent) -> None:
        """Append into memory and the store, rolling memory back on store failure.

        Raises:
            ValueError: Exactly as the parent (duplicate id; store untouched).
            Exception: Any store failure, after the in-memory rollback, unchanged.
        """
        with self._lock:
            super().append(event)
            try:
                self._store.append(event)
            except BaseException:
                self._events.pop()
                raise

    def complete_followup(self, event_id: str) -> AdverseEvent:
        """Mark the follow-up completed in memory AND the store, or nowhere.

        Raises:
            KeyError: Exactly as the parent (unknown id; store untouched).
            Exception: Any store failure, after the in-memory restore, unchanged.
        """
        with self._lock:
            previous = self.get(event_id)
            if previous is None:
                raise KeyError(event_id)
            replaced = super().complete_followup(event_id)
            try:
                self._store.update_followup(event_id, True)
            except BaseException:
                self._events = [
                    previous if existing.id == event_id else existing for existing in self._events
                ]
                raise
            return replaced
