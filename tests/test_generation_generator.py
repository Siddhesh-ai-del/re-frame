"""Tests for ``reframe.generation.client`` and ``reframe.generation.generator``.

Strict TDD stage 2b: written BEFORE any ``reframe.generation`` module exists (RED).
The FakeClient double implements the ``LLMClient`` protocol and never touches a network.
"""

from dataclasses import FrozenInstanceError

import pytest

from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)
from reframe.generation.client import (
    GenerationError,
    GenerationRequest,
    GenerationResponse,
    LLMClient,
)
from reframe.generation.generator import ConstrainedGenerator, GenerationResult
from reframe.generation.prompts import SYSTEM_PROMPT

#: The no-match instruction the spec mandates verbatim.
NO_MATCH_LINE = (
    "No specific exercise matched; offer warm general support within your boundaries, "
    "and suggest the user describe their situation further."
)

DEFAULT_RESPONSE = GenerationResponse(text="A warm, short reply.", model="fake-model")


class FakeClient:
    """Recording test double for the ``LLMClient`` protocol (zero network)."""

    def __init__(
        self,
        response: GenerationResponse | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.response = response if response is not None else DEFAULT_RESPONSE
        self.error = error
        self.requests: list[GenerationRequest] = []

    def complete(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response


def _module(module_id: str) -> ExerciseModule:
    """A valid curated module with steps distinctive enough to assert on."""
    return ExerciseModule(
        id=module_id,
        title=f"Exercise {module_id}",
        summary="A curated self-help exercise.",
        category=ExerciseCategory.RUMINATION,
        tier=EvidenceTier.A,
        safety_class=SafetyClass.SELF_HELP_SAFE,
        steps=(f"First step for {module_id}.", "Check in with how you feel."),
        sources=("NICE NG222 depression in adults (2022)",),
    )


# ---------------------------------------------------------------------------
# ConstrainedGenerator.respond — request assembly
# ---------------------------------------------------------------------------


def test_respond_with_modules_sends_red_lines_context_steps_and_user_message() -> None:
    client = FakeClient()
    generator = ConstrainedGenerator(client)

    result = generator.respond(
        "I can't stop thinking about it", (_module("attention-shift-refocus"),)
    )

    assert result.module_ids == ("attention-shift-refocus",)
    assert len(client.requests) == 1
    request = client.requests[0]
    # System side: the red lines...
    assert request.system_prompt == SYSTEM_PROMPT
    assert "Never diagnose or suggest the user has any condition" in request.system_prompt
    assert "Never recommend treatment, therapy, or medication" in request.system_prompt
    # ...and the curated exercise content.
    assert "Exercise id: attention-shift-refocus" in request.context
    assert "1. First step for attention-shift-refocus." in request.context
    # User side carries the user message untouched when modules are present.
    assert "I can't stop thinking about it" in request.user_message
    assert NO_MATCH_LINE not in request.user_message


def test_respond_without_modules_sends_empty_context_and_support_instruction() -> None:
    client = FakeClient()
    generator = ConstrainedGenerator(client)

    result = generator.respond("Feeling flat today")

    assert result.module_ids == ()
    request = client.requests[0]
    assert request.context == ""
    assert "Feeling flat today" in request.user_message
    assert NO_MATCH_LINE in request.user_message


def test_result_carries_response_text_model_and_module_ids() -> None:
    client = FakeClient(GenerationResponse(text="Here is a gentle exercise.", model="chosen-model"))
    generator = ConstrainedGenerator(client)

    result = generator.respond("Help me refocus", (_module("aaa-one"), _module("bbb-two")))

    assert isinstance(result, GenerationResult)
    assert result.text == "Here is a gentle exercise."
    assert result.model == "chosen-model"
    assert result.module_ids == ("aaa-one", "bbb-two")


def test_generation_result_is_frozen() -> None:
    result = ConstrainedGenerator(FakeClient()).respond("hello")
    with pytest.raises(FrozenInstanceError):
        result.text = "mutated"


def test_fake_client_satisfies_the_llm_client_protocol() -> None:
    assert isinstance(FakeClient(), LLMClient)


# ---------------------------------------------------------------------------
# ConstrainedGenerator.respond — validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "blank",
    ["", "   ", "\t\n "],
    ids=["empty", "spaces", "whitespace-chars"],
)
def test_respond_rejects_blank_user_message_with_value_error(blank: str) -> None:
    generator = ConstrainedGenerator(FakeClient())
    with pytest.raises(ValueError):
        generator.respond(blank)


@pytest.mark.parametrize("bad", [None, 7, [], {}], ids=["none", "int", "list", "dict"])
def test_respond_rejects_non_string_user_message_with_type_error(bad: object) -> None:
    generator = ConstrainedGenerator(FakeClient())
    with pytest.raises(TypeError):
        generator.respond(bad)


# ---------------------------------------------------------------------------
# ConstrainedGenerator.respond — client failure handling
# ---------------------------------------------------------------------------


def test_generation_error_from_client_propagates_unchanged() -> None:
    original = GenerationError("provider refused the request")
    generator = ConstrainedGenerator(FakeClient(error=original))

    with pytest.raises(GenerationError) as excinfo:
        generator.respond("hello")

    assert excinfo.value is original


def test_unexpected_client_exception_is_wrapped_in_generation_error() -> None:
    original = ValueError("unexpected failure leaking out of the client")
    generator = ConstrainedGenerator(FakeClient(error=original))

    with pytest.raises(GenerationError) as excinfo:
        generator.respond("hello")

    assert excinfo.value is not original
    assert type(excinfo.value) is GenerationError
    assert excinfo.value.__cause__ is original


# ---------------------------------------------------------------------------
# client.py value types
# ---------------------------------------------------------------------------


def test_generation_error_is_a_runtime_error() -> None:
    assert issubclass(GenerationError, RuntimeError)


def test_request_is_frozen() -> None:
    request = GenerationRequest(system_prompt="sys", context="", user_message="hi")
    with pytest.raises(FrozenInstanceError):
        request.system_prompt = "other"


def test_response_is_frozen() -> None:
    response = GenerationResponse(text="t", model="m")
    with pytest.raises(FrozenInstanceError):
        response.text = "other"


def test_request_requires_non_empty_system_prompt_and_user_message() -> None:
    with pytest.raises(ValueError):
        GenerationRequest(system_prompt="", context="", user_message="hi")
    with pytest.raises(ValueError):
        GenerationRequest(system_prompt="sys", context="", user_message="   ")


def test_request_rejects_non_string_system_prompt_and_user_message() -> None:
    with pytest.raises(ValueError):
        GenerationRequest(system_prompt=None, context="", user_message="hi")
    with pytest.raises(ValueError):
        GenerationRequest(system_prompt="sys", context="", user_message=7)


def test_request_allows_empty_context_but_rejects_non_string_context() -> None:
    request = GenerationRequest(system_prompt="sys", context="", user_message="hi")
    assert request.context == ""
    with pytest.raises(ValueError):
        GenerationRequest(system_prompt="sys", context=None, user_message="hi")


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_generation_public_api_is_exported() -> None:
    from reframe import generation

    for name in (
        "GenerationError",
        "GenerationRequest",
        "GenerationResponse",
        "LLMClient",
        "ConstrainedGenerator",
        "GenerationResult",
        "OpenAICompatibleClient",
        "SYSTEM_PROMPT",
        "build_context",
        "build_user_message",
    ):
        assert hasattr(generation, name), f"missing public export: {name}"
