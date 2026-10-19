#!/usr/bin/env python3
"""Tiny mock OpenAI-compatible provider for the stage 6e generated-turn E2E.

Serves exactly two routes:

- ``POST /chat/completions`` — returns a fixed, valid OpenAI-shaped body with
  a lane-safe reply and IGNORES the request payload entirely (no model, no
  key, no variability: the E2E proves the wiring, not model quality).
- ``GET /health`` — a readiness probe for Playwright's webServer check.

The composed RE:FRAME service reaches this server through the config
overrides ``REFRAME_LLM_BASE_URL`` / ``REFRAME_LLM_MODEL`` (stage 6e), so the
E2E runs without any real credentials anywhere in the repository or CI.

Usage::

    python web/scripts/mock-llm-server.py --port 8125

Standard library only — works with the repo venv, CI system python, anything.
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8125
CHAT_COMPLETIONS_PATH = "/chat/completions"

#: Fixed reply returned for EVERY completion request. Kept in the wellness
#: lane (no clinical claims) and stable so `web/e2e/generated.spec.ts` can
#: assert it verbatim — keep the two copies identical.
MOCK_REPLY = (
    "That argument keeps looping in your head. Would it help to write down what "
    "you'd say differently, or to set the thought aside for ten minutes and come "
    "back to it?"
)

COMPLETION_BODY = {
    "id": "mock-completion-1",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": MOCK_REPLY},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


class MockOpenAIHandler(BaseHTTPRequestHandler):
    """Method-shaped stub: parse nothing, always answer the fixed body."""

    server_version = "ReframeMockLLM/1.0"

    def _send_json(self, status: int, body: dict[str, object]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        """Readiness probe (and a friendly 404 for anything else)."""
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "provider": "reframe-mock"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        """Consume the payload (intentionally ignored) and answer fixed."""
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            _payload = self.rfile.read(length)  # read & drop: no parsing at all
        if self.path != CHAT_COMPLETIONS_PATH:
            self._send_json(404, {"error": "not found"})
            return
        self._send_json(200, COMPLETION_BODY)

    def log_message(self, fmt: str, *args: object) -> None:
        """Minimal stderr logging so Playwright's output stays readable."""
        sys.stderr.write(f"[mock-llm] {self.address_string()} {fmt % args}\n")


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv``, bind, and serve until interrupted."""
    parser = argparse.ArgumentParser(description="Mock OpenAI-compatible provider.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind interface")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="TCP port")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), MockOpenAIHandler)
    print(
        f"[mock-llm] listening on http://{args.host}:{args.port} (POST {CHAT_COMPLETIONS_PATH})",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
