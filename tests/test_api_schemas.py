"""Schema tests for ``reframe.api.schemas`` — the HTTP request/response contracts.

ChatRequest is the security-relevant boundary: ``extra="forbid"`` rejects unknown
body keys, and ``message`` is length-bounded (1..4000) so oversized or empty
payloads never reach the pipeline.
"""

import pytest
from pydantic import ValidationError

from reframe.api.schemas import ChatRequest, ChatResponse, ErrorDetail, HealthResponse, ResourceOut

# ---------------------------------------------------------------------------
# ChatRequest: bounds + extra="forbid"
# ---------------------------------------------------------------------------


def test_chat_request_accepts_a_one_char_message() -> None:
    assert ChatRequest(message="a").message == "a"


def test_chat_request_accepts_the_4000_char_upper_bound() -> None:
    assert ChatRequest(message="x" * 4000).message == "x" * 4000


def test_chat_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_rejects_a_4001_char_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 4001)


def test_chat_request_rejects_unknown_extra_field() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="hi", admin=True)  # type: ignore[call-arg]


def test_chat_request_is_configured_to_forbid_extra_fields() -> None:
    assert ChatRequest.model_config["extra"] == "forbid"


# ---------------------------------------------------------------------------
# Response models: field shapes
# ---------------------------------------------------------------------------


def test_resource_out_with_url() -> None:
    resource = ResourceOut(name="Find A Helpline", url="https://example.com")
    assert resource.name == "Find A Helpline"
    assert resource.url == "https://example.com"


def test_resource_out_without_url_is_none() -> None:
    resource = ResourceOut(name="Emergency services", url=None)
    assert resource.url is None


def test_chat_response_field_shapes() -> None:
    response = ChatResponse(
        reply="hello there",
        route="generated",
        module_ids=["m1", "m2"],
        violations=["medication"],
        resources=[ResourceOut(name="r", url=None)],
    )
    assert response.reply == "hello there"
    assert response.route == "generated"
    assert response.module_ids == ["m1", "m2"]
    assert response.violations == ["medication"]
    assert response.resources[0].name == "r"


def test_health_response_field_shapes() -> None:
    health = HealthResponse(status="ok", version="0.1.0.dev0")
    assert health.status == "ok"
    assert health.version == "0.1.0.dev0"


def test_error_detail_field_shape() -> None:
    error = ErrorDetail(detail="something went wrong")
    assert error.detail == "something went wrong"
