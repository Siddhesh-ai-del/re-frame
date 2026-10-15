"""OpenAI-compatible ``/chat/completions`` adapter (local servers work via ``base_url``).

Fail-closed translation to the layer's single failure type: transport failures
(timeouts included), non-2xx statuses, and malformed payloads all become
:class:`~reframe.generation.client.GenerationError`, whose message never
contains the API key. Tests inject an ``httpx.MockTransport`` through the
``transport`` field — the adapter performs no real network call in tests.
"""

from dataclasses import dataclass, field

import httpx

from reframe.generation.client import (
    GenerationError,
    GenerationRequest,
    GenerationResponse,
)

#: Path appended to ``base_url`` for every completion request.
CHAT_COMPLETIONS_PATH = "/chat/completions"


def _require_http_url(value: object, field_name: str) -> None:
    """Fail closed unless ``value`` is an ``http://`` or ``https://`` URL string."""
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        raise ValueError(
            f"OpenAICompatibleClient.{field_name}: {value!r} must start with http:// or https://"
        )


def _require_non_blank(value: object, field_name: str) -> None:
    """Fail closed unless ``value`` is a non-blank string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"OpenAICompatibleClient.{field_name}: {value!r} must be a non-empty string"
        )


def _require_positive_timeout(value: object) -> None:
    """Fail closed unless ``value`` is a number greater than zero."""
    if not isinstance(value, int | float) or value <= 0:
        raise ValueError(f"OpenAICompatibleClient.timeout_seconds: {value!r} must be > 0")


@dataclass(frozen=True)
class OpenAICompatibleClient:
    """Minimal chat-completions client; ``transport`` is the MockTransport injection point.

    Fail-closed construction: a non-``http(s)`` ``base_url``, a blank
    ``api_key`` or ``model``, or a non-positive ``timeout_seconds`` raises
    ``ValueError`` before any request could be attempted.
    """

    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 30.0
    transport: httpx.BaseTransport | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _require_http_url(self.base_url, "base_url")
        _require_non_blank(self.api_key, "api_key")
        _require_non_blank(self.model, "model")
        _require_positive_timeout(self.timeout_seconds)

    def complete(self, request: GenerationRequest) -> GenerationResponse:
        """POST one ``/chat/completions`` request and parse the reply text.

        The system message is the red lines plus the curated context
        (context omitted entirely when empty); the user message is passed
        through untouched.

        Args:
            request: The constrained request to send.

        Returns:
            The reply text paired with this client's configured model name.

        Raises:
            GenerationError: On timeout, transport failure, non-2xx status, or
                a malformed/incomplete response body.
        """
        if request.context:
            system_content = f"{request.system_prompt}\n\n{request.context}"
        else:
            system_content = request.system_prompt
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": request.user_message},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(
                transport=self.transport,
                timeout=self.timeout_seconds,
                headers=headers,
            ) as client:
                response = client.post(f"{self.base_url}{CHAT_COMPLETIONS_PATH}", json=payload)
        except httpx.TimeoutException as exc:
            raise GenerationError(
                f"LLM request timed out after {self.timeout_seconds}s: "
                f"{self.base_url}{CHAT_COMPLETIONS_PATH}"
            ) from exc
        except httpx.RequestError as exc:
            raise GenerationError(
                f"LLM request failed ({type(exc).__name__}): {self.base_url}{CHAT_COMPLETIONS_PATH}"
            ) from exc

        return self._parse_completion(response)

    def _parse_completion(self, response: httpx.Response) -> GenerationResponse:
        """Translate status/payload failures; pair the reply text with the configured model.

        Raises:
            GenerationError: On non-2xx status, malformed JSON, or a missing /
                unusable ``choices[0].message.content``.
        """
        if not (200 <= response.status_code < 300):
            raise GenerationError(f"LLM provider returned HTTP {response.status_code}")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise GenerationError(
                "LLM provider response was malformed or missing message content "
                f"({type(exc).__name__})"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise GenerationError("LLM provider response has no usable message content")
        return GenerationResponse(text=content, model=self.model)
