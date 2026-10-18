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
  model are the module constants below (the config module exposes only the
  key, so those are the only knobs v1 has).

``uvicorn`` is imported lazily inside :func:`_run_uvicorn` — the seam tests
monkeypatch instead of starting a server — so importing this module never
pulls in server machinery.
"""

import argparse
import sys
from collections.abc import Sequence

from fastapi import FastAPI

from reframe.api.service import create_service
from reframe.config import load_settings
from reframe.content import ExerciseModule
from reframe.generation import (
    ConstrainedGenerator,
    GenerationError,
    GenerationResult,
    OpenAICompatibleClient,
)

#: v1 endpoint defaults for the OpenAI-compatible API (config exposes only the key).
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
    return parser


def _run_uvicorn(app: FastAPI, *, host: str, port: int, log_level: str) -> None:
    """Serve ``app`` until interrupted — the documented "no server" test seam.

    The lazy ``uvicorn`` import lives HERE (never at module level) so
    importing ``reframe.cli`` never imports server machinery.
    """
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level=log_level)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` (default: ``sys.argv[1:]``), compose the service, serve.

    Exit codes: ``0`` after the server returns; ``2`` when the configuration
    is rejected (fail closed — nothing is served). Out-of-range ports abort
    through argparse's own ``SystemExit(2)`` before anything is built.

    Args:
        argv: Argument vector WITHOUT the program name; ``None`` reads sys.argv.

    Returns:
        ``0`` once serving finishes; ``2`` for a rejected configuration.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error(f"--port must be between 1 and 65535 (got {args.port})")

    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"reframe: cannot start: {exc}", file=sys.stderr)
        return 2

    if settings.api_key is not None:
        client = OpenAICompatibleClient(
            base_url=LLM_BASE_URL, api_key=settings.api_key, model=LLM_MODEL
        )
        generator: ConstrainedGenerator = ConstrainedGenerator(client)
    else:
        print(NOTICE_NO_API_KEY, file=sys.stderr)
        generator = _UnconfiguredGenerator()

    app = create_service(generator=generator, db_path=args.db)
    _run_uvicorn(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
