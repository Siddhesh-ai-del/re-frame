"""Tests for ``reframe.generation.openai_client`` — MockTransport-only adapter, zero network.

Strict TDD stage 2b: written BEFORE any ``reframe.generation`` module exists (RED).
"""

import json
from collections.abc import Callable

import httpx
import pytest

from reframe.generation.client import GenerationError, GenerationRequest, GenerationResponse
from reframe.generation.openai_client import OpenAICompatibleClient

BASE_URL = "https://llm.example.test/v1"
API_KEY = "unit-test-key-fake-0000-not-a-real-secret"
MODEL = "test-model"
SYSTEM_PROMPT_LINE = "You are a wellness companion for adults, not a healthcare professional."
CONTEXT_BLOCK = "Exercise id: attention-shift-refocus\nSteps:\n1. Notice the loop."
USER_MESSAGE = "I keep ruminating at night"


def _request(context: str = CONTEXT_BLOCK) -> GenerationRequest:
    """A valid request; ``context`` selects the empty/non-empty system-content branch."""
    return GenerationRequest(
        system_prompt=SYSTEM_PROMPT_LINE,
        context=context,
        user_message=USER_MESSAGE,
    )


def _payload(content: str = "A gentle exercise.") -> dict[str, object]:
    return {"choices": [{"message": {"content": content}}]}


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAICompatibleClient:
    """Client wired to a MockTransport so no real network call can ever happen."""
    return OpenAICompatibleClient(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        transport=httpx.MockTransport(handler),
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_complete_posts_to_chat_completions_and_parses_the_response() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        payload: dict[str, object] = {**_payload(), "model": "provider-reported-model"}
        return httpx.Response(200, json=payload)

    response = _client(handler).complete(_request())

    assert isinstance(response, GenerationResponse)
    assert response.text == "A gentle exercise."
    assert response.model == MODEL  # configured model, not the provider-reported one

    assert len(seen) == 1
    sent = seen[0]
    assert sent.method == "POST"
    assert str(sent.url) == f"{BASE_URL}/chat/completions"
    assert sent.headers["Authorization"] == f"Bearer {API_KEY}"
    assert sent.headers["Content-Type"] == "application/json"

    body = json.loads(sent.content)
    assert body["model"] == MODEL
    assert body["messages"] == [
        {"role": "system", "content": f"{SYSTEM_PROMPT_LINE}\n\n{CONTEXT_BLOCK}"},
        {"role": "user", "content": USER_MESSAGE},
    ]


def test_empty_context_sends_the_bare_system_prompt() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_payload())

    _client(handler).complete(_request(context=""))

    body = json.loads(seen[0].content)
    assert body["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT_LINE}
    assert body["messages"][1] == {"role": "user", "content": USER_MESSAGE}


# ---------------------------------------------------------------------------
# Failure translation — everything becomes GenerationError
# ---------------------------------------------------------------------------


def test_server_error_raises_generation_error_with_status_but_without_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    with pytest.raises(GenerationError) as excinfo:
        _client(handler).complete(_request())

    message = str(excinfo.value)
    assert "500" in message
    assert API_KEY not in message


def test_timeout_raises_generation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout")

    with pytest.raises(GenerationError) as excinfo:
        _client(handler).complete(_request())

    assert "timed out" in str(excinfo.value)


def test_transport_request_error_raises_generation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.RequestError("simulated connection failure", request=request)

    with pytest.raises(GenerationError) as excinfo:
        _client(handler).complete(_request())

    assert "failed" in str(excinfo.value)


def test_invalid_json_body_raises_generation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"definitely-not-json{")

    with pytest.raises(GenerationError) as excinfo:
        _client(handler).complete(_request())

    assert "malformed" in str(excinfo.value)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "   "}}]},
    ],
    ids=[
        "missing-choices-key",
        "empty-choices",
        "missing-content-key",
        "null-content",
        "blank-content",
    ],
)
def test_incomplete_payload_raises_generation_error(payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(GenerationError):
        _client(handler).complete(_request())


# ---------------------------------------------------------------------------
# Constructor validation — every failure is a ValueError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_base_url",
    ["ftp://llm.example.test", "llm.example.test", "", "http:/broken"],
    ids=["ftp-scheme", "missing-scheme", "empty", "malformed"],
)
def test_invalid_base_url_raises_value_error(bad_base_url: str) -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleClient(base_url=bad_base_url, api_key=API_KEY, model=MODEL)


def test_non_string_base_url_raises_value_error() -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleClient(base_url=None, api_key=API_KEY, model=MODEL)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_api_key", ["", "   "], ids=["empty", "whitespace"])
def test_blank_api_key_raises_value_error(bad_api_key: str) -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleClient(base_url=BASE_URL, api_key=bad_api_key, model=MODEL)


def test_blank_model_raises_value_error() -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleClient(base_url=BASE_URL, api_key=API_KEY, model="")


@pytest.mark.parametrize("bad_timeout", [0, 0.0, -1.5], ids=["zero-int", "zero-float", "negative"])
def test_non_positive_timeout_raises_value_error(bad_timeout: float) -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleClient(
            base_url=BASE_URL,
            api_key=API_KEY,
            model=MODEL,
            timeout_seconds=bad_timeout,
        )


def test_non_numeric_timeout_raises_value_error() -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleClient(
            base_url=BASE_URL,
            api_key=API_KEY,
            model=MODEL,
            timeout_seconds="30",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Field defaults and repr
# ---------------------------------------------------------------------------


def test_timeout_defaults_to_thirty_seconds_and_transport_to_none() -> None:
    client = OpenAICompatibleClient(base_url=BASE_URL, api_key=API_KEY, model=MODEL)
    assert client.timeout_seconds == 30.0
    assert client.transport is None


def test_transport_is_excluded_from_the_repr() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=_payload()))
    client = OpenAICompatibleClient(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        transport=transport,
    )
    assert "transport" not in repr(client)
