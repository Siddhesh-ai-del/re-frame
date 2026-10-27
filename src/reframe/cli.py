"""Runnable entry point for the RE:FRAME local service (stage 5d).

Run it with ``python -m reframe.cli``; a ``reframe`` console script can simply
alias ``reframe.cli:main`` when pyproject gains its entry-point table (this
stage adds no packaging metadata). Defaults bind ``127.0.0.1:8000`` — the v1
service is single-user and local by design (no auth, CORS, or rate limiting),
so anything beyond localhost must run behind a reverse proxy on a trusted
interface.

LLM key policy, driven by the actual ``reframe.config`` behavior:

- ``development``/``test`` allow a missing ``REFRAME_API_KEY``: the server
  still starts. A non-alarming notice goes to stderr and the generator is a
  fail-closed ``_UnconfiguredGenerator`` whose calls raise ``GenerationError``
  — so ``POST /chat`` on a generated turn maps to 503 while the scripted
  crisis and human-review routes (which never call the generator) keep
  working without a model.
- ``production`` without a key — or an invalid ``REFRAME_ENV`` — is rejected
  by ``load_settings``: the message goes to stderr and ``main`` returns 2
  WITHOUT starting the server (fail closed — a chat service never serves
  half-configured in production).
- With a key, the generator wraps ``OpenAICompatibleClient``; its base URL and
  model default to the module constants below and are overridable per
  environment through ``REFRAME_LLM_BASE_URL`` / ``REFRAME_LLM_MODEL`` (both
  validated by ``reframe.config`` — a non-``http(s)`` base URL is rejected
  before anything is built).
- ``--static <dir>`` serves a built SPA (``web/dist``) from the same process:
  the composed service mounts it last, so every registered API route wins and
  unknown GETs fall through to ``index.html``.

Offline commands (stage 7b, E7): ``--report`` prints the feasibility report
(markdown) for ``--db`` and exits; ``--audit`` runs the crisis self-audit over
the packaged seeded corpus and exits (with ``--record-audit-misses``, audit
misses are durably recorded to ``--db``, deduplicated by reference). Both
branch BEFORE ``load_settings()`` — no LLM key, no settings load, no port
bind, no server — and ``--report`` never creates a missing database file
(read-only tool).

``uvicorn`` is imported lazily inside :func:`_run_uvicorn` — the seam tests
monkeypatch instead of starting a server — so importing this module never
pulls in server machinery.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from fastapi import FastAPI

from reframe.api.service import create_service
from reframe.config import load_settings
from reframe.content import ExerciseModule
from reframe.evaluation.adverse_events import AdverseEvent
from reframe.evaluation.detectors import audit_miss_events
from reframe.evaluation.log import AdverseEventLog, PersistentAdverseEventLog
from reframe.evaluation.report import build_report, checkins_from_tracker, to_markdown
from reframe.evaluation.store import SqliteAdverseEventStore
from reframe.generation import (
    ConstrainedGenerator,
    GenerationError,
    GenerationResult,
    OpenAICompatibleClient,
)
from reframe.measurement.persistent import PersistentCheckInTracker
from reframe.measurement.store import SqliteCheckInStore
from reframe.measurement.tracker import CheckInTracker
from reframe.safety.audit import run_crisis_audit
from reframe.safety.audit_corpus import AUDIT_CORPUS

#: v1 endpoint defaults for the OpenAI-compatible API (overridable via config).
LLM_BASE_URL = "https://api.openai.com/v1"
LLM_MODEL = "gpt-4o-mini"

#: Non-alarming stderr notice when no key is configured (the server still starts).
NOTICE_NO_API_KEY = (
    "reframe: no LLM API key configured — set REFRAME_API_KEY in your environment to "
    "enable generated replies; crisis and scripted routes still work without a model."
)

#: Failure surfaced by the fail-closed generator on generated turns.
NO_API_KEY_DETAIL = "no LLM API key configured"


class _UnconfiguredGenerator(ConstrainedGenerator):
    """Fail-closed generator stand-in used when no LLM API key is configured.

    Every call raises ``GenerationError`` so generated turns map to a generic
    503 at the HTTP layer; the scripted crisis and human-review routes never
    call the generator and therefore keep working without a model.
    """

    def __init__(self) -> None:
        """No client is constructed: this generator performs no I/O."""

    def respond(
        self,
        user_message: str,
        modules: tuple[ExerciseModule, ...] = (),
    ) -> GenerationResult:
        """Always fail closed with the layer's single failure type."""
        raise GenerationError(NO_API_KEY_DETAIL)


def _build_parser() -> argparse.ArgumentParser:
    """Build the v1 argument parser (localhost defaults; see module docstring)."""
    parser = argparse.ArgumentParser(
        prog="reframe", description="Run the RE:FRAME local API service."
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="interface to bind (default: localhost)"
    )
    parser.add_argument("--port", type=int, default=8000, help="TCP port, 1..65535")
    parser.add_argument("--db", default="reframe.db", help="SQLite check-in database path")
    parser.add_argument("--log-level", default="info", help="uvicorn log level")
    parser.add_argument(
        "--static",
        default=None,
        metavar="DIR",
        help="directory with the built SPA (web/dist) to serve from the API app",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="print the feasibility report (markdown) for --db and exit",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="run the crisis self-audit over the packaged seeded corpus and exit",
    )
    parser.add_argument(
        "--record-audit-misses",
        action="store_true",
        help="with --audit: record audit misses to the --db adverse-event log (deduplicated)",
    )
    return parser


def _run_uvicorn(app: FastAPI, *, host: str, port: int, log_level: str) -> None:
    """Serve ``app`` until interrupted — the documented "no server" test seam.

    The lazy ``uvicorn`` import lives HERE (never at module level) so
    importing ``reframe.cli`` never imports server machinery.
    """
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level=log_level)


def _run_offline(args: argparse.Namespace) -> int:
    """Run the requested offline command(s) and return 0 (E7).

    Never calls ``load_settings``, never builds the generator, never binds a
    port. The audit (if requested) runs FIRST, then the report (if
    requested). ``--report`` on a missing ``--db`` file reports on a bare
    in-memory tracker/log and does NOT create the file (read-only tool);
    ``--record-audit-misses`` legitimately creates it — it records NEW safety
    records (E7). Failures from a malformed database propagate loudly.
    """
    if args.audit:
        audit_report = run_crisis_audit(AUDIT_CORPUS)
        print(f"probes: {audit_report.total}")
        print(f"recall: {audit_report.recall:.0%}")
        print(f"misses: {len(audit_report.misses)}")
        miss_events = audit_miss_events(audit_report)
        for event in miss_events:
            print(event.reference)
        if args.record_audit_misses:
            recorded, skipped = _record_audit_misses(args.db, miss_events)
            print(f"recorded: {recorded}")
            print(f"skipped: {skipped}")

    if args.report:
        db_path = Path(args.db)
        if db_path.exists():
            checkin_store = SqliteCheckInStore(db_path)
            tracker: CheckInTracker = PersistentCheckInTracker(checkin_store)
            ae_store = SqliteAdverseEventStore(db_path)
            ae_log: AdverseEventLog = PersistentAdverseEventLog(ae_store)
            report = build_report(checkins_from_tracker(tracker), ae_log.events())
            checkin_store.close()
            ae_store.close()
        else:
            report = build_report(
                checkins_from_tracker(CheckInTracker()), AdverseEventLog().events()
            )
        print(to_markdown(report))
    return 0


def _record_audit_misses(db_path: str, events: tuple[AdverseEvent, ...]) -> tuple[int, int]:
    """Durably record audit-miss events to ``db_path``, deduplicated by reference.

    Args:
        db_path: SQLite path for the adverse-event store (created if absent —
            recording NEW safety records is the explicit purpose here).
        events: The miss events to record (``audit_miss_events`` output).

    Returns:
        ``(recorded, skipped)`` — appended this run vs. already present.
    """
    store = SqliteAdverseEventStore(db_path)
    log = PersistentAdverseEventLog(store)
    existing = {event.reference for event in log.events()}
    recorded = 0
    skipped = 0
    for event in events:
        if event.reference in existing:
            skipped += 1
        else:
            log.append(event)
            recorded += 1
    store.close()
    return recorded, skipped


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` (default: ``sys.argv[1:]``), compose the service, serve.

    Exit codes: ``0`` after the server returns (or an offline command runs);
    ``2`` when the configuration is rejected (fail closed — nothing is
    served). Out-of-range ports abort through argparse's own ``SystemExit(2)``
    before anything is built.

    Args:
        argv: Argument vector WITHOUT the program name; ``None`` reads sys.argv.

    Returns:
        ``0`` once serving finishes or an offline command completes; ``2`` for
        a rejected configuration.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error(f"--port must be between 1 and 65535 (got {args.port})")
    if args.record_audit_misses and not args.audit:
        parser.error("--record-audit-misses requires --audit")
    if args.audit or args.report:
        # E7: offline — no settings, no generator, no port, no server.
        return _run_offline(args)

    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"reframe: cannot start: {exc}", file=sys.stderr)
        return 2

    if settings.api_key is not None:
        client = OpenAICompatibleClient(
            base_url=settings.llm_base_url or LLM_BASE_URL,
            api_key=settings.api_key,
            model=settings.llm_model or LLM_MODEL,
        )
        generator: ConstrainedGenerator = ConstrainedGenerator(client)
    else:
        print(NOTICE_NO_API_KEY, file=sys.stderr)
        generator = _UnconfiguredGenerator()

    app = create_service(
        generator=generator,
        db_path=args.db,
        static_dir=Path(args.static) if args.static is not None else None,
    )
    _run_uvicorn(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
