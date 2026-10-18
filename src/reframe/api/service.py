"""Composition root: one FastAPI app carrying the conversation and measurement routes.

``create_service`` assembles the v1 service from tested parts WITHOUT changing
their semantics: the conversation pipeline (safety -> retrieval -> generation
-> output filter) is created by :func:`reframe.api.app.create_app`, and the
check-in routes from :func:`reframe.api.measure.include_measurement_routes`
are added over a tracker — so chat and check-ins both route through the same
deterministic safety layers above the HTTP boundary.

Single-user local v1 by design (not accident): no auth, CORS, or rate
limiting — the service serves localhost and must sit behind a reverse proxy
before any wider exposure. The tracker defaults to in-memory (dev); pass
``db_path`` for a durable SQLite store — its connection is attached to
``app.state.store`` and closed by the shutdown handler registered here.
"""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI

from reframe.api.app import create_app
from reframe.api.measure import include_measurement_routes
from reframe.content import default_library
from reframe.generation import ConstrainedGenerator
from reframe.measurement.persistent import PersistentCheckInTracker
from reframe.measurement.store import SqliteCheckInStore
from reframe.measurement.tracker import CheckInTracker
from reframe.pipeline import ConversationPipeline


def create_service(
    *,
    generator: ConstrainedGenerator,
    tracker_factory: Callable[[], CheckInTracker] | None = None,
    db_path: str | Path | None = None,
) -> FastAPI:
    """Build the composed service app around ``generator``.

    Tracker wiring, in priority order: ``tracker_factory`` when given (tests
    inject fakes/in-memory trackers); else a durable
    ``PersistentCheckInTracker`` over ``SqliteCheckInStore(db_path)``; else a
    plain in-memory ``CheckInTracker`` (the dev default). The store — when one
    was created — is attached to ``app.state.store`` and closed by the
    shutdown handler, so a server shutdown (or a test's ``TestClient``
    context) releases the SQLite connection.

    Safety routing is unchanged by composition: the pipeline decides crisis
    bypass and human review before any generation, and check-in routing is
    recomputed from the recorded flags at the HTTP layer.
    """
    pipeline = ConversationPipeline(generator=generator, library=default_library())
    app = create_app(pipeline)

    store: SqliteCheckInStore | None = None
    if tracker_factory is not None:
        tracker: CheckInTracker = tracker_factory()
    elif db_path is not None:
        store = SqliteCheckInStore(db_path)
        tracker = PersistentCheckInTracker(store)
    else:
        tracker = CheckInTracker()
    include_measurement_routes(app, tracker)
    app.state.store = store

    async def _close_store_on_shutdown() -> None:
        """Close the SQLite store; a clean no-op when no store was created."""
        if app.state.store is not None:
            app.state.store.close()

    app.router.add_event_handler("shutdown", _close_store_on_shutdown)
    return app
