"""Provider-agnostic value types and the single failure type for generation.

Everything the constrained-generation layer exchanges with an LLM client is a
frozen record, validated fail-closed at construction: a request is only built
with a non-blank system prompt and user message (context may be empty — it is
empty when no exercise module matched), and :class:`GenerationError` is the
only exception this layer ever raises outward.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


def _require_non_blank(value: object, field_name: str) -> None:
    """Fail closed unless ``value`` is a non-blank string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"GenerationRequest.{field_name}: {value!r} must be a non-empty string")


def _require_string(value: object, field_name: str) -> None:
    """Fail closed unless ``value`` is a string (empty is allowed)."""
    if not isinstance(value, str):
        raise ValueError(
            f"GenerationRequest.{field_name}: {value!r} must be a string (empty is allowed)"
        )


@dataclass(frozen=True)
class GenerationRequest:
    """One constrained completion request: red lines, curated context, user text.

    Validation is fail-closed: ``system_prompt`` and ``user_message`` must be
    non-blank strings, while ``context`` must be a string but may be empty
    (empty context == no exercise module matched this turn).
    """

    system_prompt: str
    context: str
    user_message: str

    def __post_init__(self) -> None:
        _require_non_blank(self.system_prompt, "system_prompt")
        _require_string(self.context, "context")
        _require_non_blank(self.user_message, "user_message")


@dataclass(frozen=True)
class GenerationResponse:
    """One successful completion: the reply text and the model that produced it."""

    text: str
    model: str


class GenerationError(RuntimeError):
    """The single failure type this layer ever raises; provider details stay inside."""


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic completion contract — any object with ``complete`` conforms."""

    def complete(self, request: GenerationRequest) -> GenerationResponse:
        """Return a completion for ``request``; raise ``GenerationError`` on failure."""
        ...
