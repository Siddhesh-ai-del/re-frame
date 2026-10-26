"""Composition root: one FastAPI app carrying the conversation and measurement routes.

``create_service`` assembles the v1 service from tested parts WITHOUT changing
their semantics: the conversation pipeline (safety -> retrieval -> generation
-> output filter) is created by :func:`reframe.api.app.create_app`, the
check-in routes from :func:`reframe.api.measure.include_measurement_routes`
are added over a tracker — so chat and check-ins both route through the same
deterministic safety layers above the HTTP boundary. Stage 7a adds the
adverse-event log: a log is ALWAYS built (durable when ``db_path`` is given,
in-memory otherwise), attached to ``app.state.ae_log``, and wired into BOTH
the check-in route (early-worsening detection) and the
``/evaluation/adverse-events`` endpoints — the product path can never
silently skip safety recording (D8).

Static serving (stage 6e): when ``static_dir`` points at a directory (the
built SPA in ``web/dist``), a ``StaticFiles`` mount with an ``index.html``
fallback is added LAST, so every API route registered above it wins — the
``GET /chat`` (SPA) vs ``POST /chat`` (API) collision resolves by registration
order exactly as the dev proxy resolves it by method. Without ``static_dir``
(or when the directory is missing) the app is API-only, byte-for-byte the
same route table as before this option existed.

Single-user local v1 by design (not accident): no auth, CORS, or rate
limiting — the service serves localhost and must sit behind a reverse proxy
before any wider exposure. The tracker defaults to in-memory (dev); pass
``db_path`` for a durable SQLite store — its connection is attached to
``app.state.store`` and closed by the shutdown handler registered here.
"""

import os
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from reframe.api.app import create_app
from reframe.api.evaluation import include_evaluation_routes
from reframe.api.measure import include_measurement_routes
from reframe.content import default_library
from reframe.evaluation.log import AdverseEventLog, PersistentAdverseEventLog
from reframe.evaluation.store import SqliteAdverseEventStore
from reframe.generation import ConstrainedGenerator
from reframe.measurement.persistent import PersistentCheckInTracker
from reframe.measurement.store import SqliteCheckInStore
from reframe.measurement.tracker import CheckInTracker
from reframe.pipeline import ConversationPipeline


class _SpaStaticFiles(StaticFiles):
    """``StaticFiles`` with an SPA deep-link fallback to ``index.html``.

    Plain ``StaticFiles`` 404s on client routes like ``/chat`` because they
    are not files on disk. Falling back at *lookup* time serves the shell for
    any path that is not a real file, while real files (hashed assets,
    ``favicon.svg``) resolve normally. API routes never reach this class when
    they are registered before the mount; requests that do reach it and find
    no file are, by definition, SPA routes.

    Trade-off (accepted, standard for generic SPA fallbacks): a genuinely
    missing asset under ``/assets/`` gets ``index.html`` (``text/html``) back
    and its script tag fails to parse loudly instead of 404-ing — a stale
    hashed URL after a redeploy, never a silent wrong-file serve.
    """

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        """Resolve ``path`` inside the served directory, else the SPA shell."""
        full_path, stat_result = super().lookup_path(path)
        if stat_result is None:
            return super().lookup_path("index.html")
        return full_path, stat_result


def create_service(
    *,
    generator: ConstrainedGenerator,
    tracker_factory: Callable[[], CheckInTracker] | None = None,
    db_path: str | Path | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Build the composed service app around ``generator``.

    Tracker wiring, in priority order: ``tracker_factory`` when given (tests
    inject fakes/in-memory trackers); else a durable
    ``PersistentCheckInTracker`` over ``SqliteCheckInStore(db_path)``; else a
    plain in-memory ``CheckInTracker`` (the dev default). The store — when one
    was created — is attached to ``app.state.store`` and closed by the
    shutdown handler, so a server shutdown (or a test's ``TestClient``
    context) releases the SQLite connection.

    AE log wiring (stage 7a, D8): a log is ALWAYS built — a durable
    ``PersistentAdverseEventLog`` over ``SqliteAdverseEventStore(db_path)``
    whenever ``db_path`` is given (even alongside an injected
    ``tracker_factory``), a plain in-memory ``AdverseEventLog`` otherwise.
    It is attached to ``app.state.ae_log`` (``app.state.ae_store`` only when
    one was created, closed by the same shutdown handler) and injected into
    both the check-in route (early-worsening detection) and the
    ``/evaluation/adverse-events`` endpoints — the product path can never
    silently skip safety recording.

    Static serving: when ``static_dir`` is an existing directory it is mounted
    at ``/`` LAST (after every API route), serving the built SPA with a
    ``index.html`` fallback for client routes. A ``None``/missing/non-directory
    value leaves the app API-only — the mount never silently half-configures.

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

    # Stage 7a (D8): the AE log is ALWAYS built — durable when db_path is
    # given (regardless of tracker_factory), in-memory otherwise.
    ae_store: SqliteAdverseEventStore | None = None
    ae_log: AdverseEventLog
    if db_path is not None:
        ae_store = SqliteAdverseEventStore(db_path)
        ae_log = PersistentAdverseEventLog(ae_store)
    else:
        ae_log = AdverseEventLog()

    include_measurement_routes(app, tracker, ae_log)
    include_evaluation_routes(app, ae_log)
    app.state.store = store
    app.state.ae_log = ae_log
    app.state.ae_store = ae_store

    async def _close_stores_on_shutdown() -> None:
        """Close the SQLite stores; a clean no-op when none were created."""
        if app.state.store is not None:
            app.state.store.close()
        if app.state.ae_store is not None:
            app.state.ae_store.close()

    app.router.add_event_handler("shutdown", _close_stores_on_shutdown)

    # LAST: the SPA mount must never shadow a registered API route (see the
    # module docstring — GET /chat falls through here, POST /chat never does).
    if static_dir is not None and static_dir.is_dir():
        app.mount("/", _SpaStaticFiles(directory=static_dir, html=True))
    return app
