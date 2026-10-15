"""Constrained LLM generation over curated exercise content (stage 2b).

Public surface: the :class:`~reframe.generation.client.GenerationRequest` /
:class:`~reframe.generation.client.GenerationResponse` value types, the single
:class:`~reframe.generation.client.GenerationError` failure type, the
:class:`~reframe.generation.client.LLMClient` protocol, the red-line
:data:`~reframe.generation.prompts.SYSTEM_PROMPT` and prompt builders, the
:class:`~reframe.generation.openai_client.OpenAICompatibleClient` adapter, and
the :class:`~reframe.generation.generator.ConstrainedGenerator` orchestrator.

The input safety layer decides escalation BEFORE generation ever runs — this
layer only has to stay inside its red lines.
"""

from reframe.generation.client import (
    GenerationError,
    GenerationRequest,
    GenerationResponse,
    LLMClient,
)
from reframe.generation.generator import ConstrainedGenerator, GenerationResult
from reframe.generation.openai_client import OpenAICompatibleClient
from reframe.generation.prompts import SYSTEM_PROMPT, build_context, build_user_message

__all__ = [
    "SYSTEM_PROMPT",
    "ConstrainedGenerator",
    "GenerationError",
    "GenerationRequest",
    "GenerationResponse",
    "GenerationResult",
    "LLMClient",
    "OpenAICompatibleClient",
    "build_context",
    "build_user_message",
]
