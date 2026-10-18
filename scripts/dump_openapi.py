"""Dump the composed service's OpenAPI schema to web/src/api/schema.json.

The schema must be derivable WITHOUT any model access: the generator is built
around a stub client that raises if a completion is ever requested, so any
future change that would make schema generation call the model fails loudly
here. Output is deterministic (sorted, stable key order from FastAPI's own
serializer) — running this twice must produce byte-identical files; CI gates
on ``git diff --exit-code -- web/src/api/schema.json`` to catch schema drift.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from reframe.api.service import create_service  # noqa: E402
from reframe.generation import ConstrainedGenerator  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "web" / "src" / "api" / "schema.json"


class _StubClient:
    """Placeholder LLM client: never called during a schema dump."""

    def complete(self, request):  # noqa: ANN001, ARG002
        raise AssertionError("never called during schema dump")


def main() -> None:
    """Build the service and write its OpenAPI schema as pretty JSON."""
    app = create_service(generator=ConstrainedGenerator(_StubClient()))
    schema_text = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(schema_text, encoding="utf-8")
    print(f"wrote {SCHEMA_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
