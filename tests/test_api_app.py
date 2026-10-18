"""HTTP-layer tests for ``reframe.api.app`` — safety semantics survive the API.

A REAL pipeline (recorded fake LLM client + the real content library) exercises
the generated, crisis-bypass, and human-review routes through FastAPI, proving
the deterministic safety routing is intact above the HTTP boundary. Stub
pipelines drive the error mapping: GenerationError -> 503, ValueError -> 422,
and any other exception -> a generic 500 that never leaks internals.

The v1 service runs behind a reverse proxy / on localhost, so there is no auth,
CORS, or rate limiting here (Stage 6/7 scope).
"""

import pytest
from fastapi.testclient import TestClient

import reframe
from reframe.api.app import create_app
from reframe.content import default_library
from reframe.generation import (
    ConstrainedGenerator,
    GenerationError,
    GenerationRequest,
    GenerationResponse,
)
from reframe.pipeline import ConversationPipeline, PipelineOutcome
from reframe.pipeline.messages import CRISIS_RESPONSE
from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES

WELL_BEHAVED_REPLY = (
    "That loop sounds exhausting. Would you like to try one short grounding exercise "
    "from today's set, or would you rather tell me more about what keeps looping?"
)


class FakeClient:
    """Recording LLM client: returns scripted replies, captures every request."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self.requests: list[GenerationRequest] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def complete(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        index = self.call_count - 1
        return GenerationResponse(text=self._replies[index], model="fake-model")


class StubPipeline:
    """Pipeline stand-in whose ``handle`` always raises the configured error."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def handle(self, user_message: str) -> PipelineOutcome:
        raise self._exc


def make_real_pipeline(replies: list[str]) -> tuple[ConversationPipeline, FakeClient]:
    client = FakeClient(replies)
    generator = ConstrainedGenerator(client)
    return ConversationPipeline(generator=generator, library=default_library()), client


def make_client(pipeline) -> TestClient:
    # raise_server_exceptions=False lets the 500 Exception handler surface as JSON.
    return TestClient(create_app(pipeline), raise_server_exceptions=False)


@pytest.fixture
def real() -> tuple[TestClient, FakeClient]:
    pipeline, fake = make_real_pipeline([WELL_BEHAVED_REPLY])
    return make_client(pipeline), fake


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok_and_the_package_version(real: tuple[TestClient, FakeClient]) -> None:
    client, _fake = real
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == reframe.__version__


# ---------------------------------------------------------------------------
# Chat: the three safety routes survive the HTTP layer
# ---------------------------------------------------------------------------


def test_chat_happy_path_generates_a_reply(real: tuple[TestClient, FakeClient]) -> None:
    client, fake = real
    response = client.post("/chat", json={"message": "I keep replaying an argument in my head..."})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "generated"
    assert body["reply"]
    assert isinstance(body["module_ids"], list)
    assert fake.call_count == 1


def test_chat_crisis_bypasses_with_resources_and_no_generation(
    real: tuple[TestClient, FakeClient],
) -> None:
    client, fake = real
    response = client.post("/chat", json={"message": "I want to kill myself"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "crisis_bypass"
    assert body["reply"] == CRISIS_RESPONSE.text
    assert len(body["resources"]) >= 1
    assert all("name" in resource for resource in body["resources"])
    assert fake.call_count == 0


def test_chat_review_route_has_no_resources(real: tuple[TestClient, FakeClient]) -> None:
    client, fake = real
    response = client.post("/chat", json={"message": "help me process my trauma"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "human_review"
    assert body["resources"] == []
    assert fake.call_count == 0


# ---------------------------------------------------------------------------
# Validation: pydantic (422) and the pipeline ValueError (422)
# ---------------------------------------------------------------------------


def test_chat_whitespace_only_maps_value_error_to_422(real: tuple[TestClient, FakeClient]) -> None:
    client, _fake = real
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_chat_empty_message_rejected_by_pydantic_422(real: tuple[TestClient, FakeClient]) -> None:
    client, _fake = real
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_extra_field_rejected_422(real: tuple[TestClient, FakeClient]) -> None:
    client, _fake = real
    response = client.post("/chat", json={"message": "hi", "admin": True})
    assert response.status_code == 422


def test_chat_over_length_message_rejected_422(real: tuple[TestClient, FakeClient]) -> None:
    client, _fake = real
    response = client.post("/chat", json={"message": "x" * 4001})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Error mapping: fail-closed, no internal leakage
# ---------------------------------------------------------------------------


def test_generation_error_maps_to_503_without_leaking_details() -> None:
    stub = StubPipeline(GenerationError("provider exploded: api-key=sk-SECRET"))
    client = make_client(stub)
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 503
    body = response.json()
    assert isinstance(body["detail"], str)
    assert "sk-SECRET" not in body["detail"]
    assert "provider exploded" not in body["detail"]


def test_unexpected_exception_maps_to_500_without_leaking_details() -> None:
    stub = StubPipeline(RuntimeError("secret-token-xyz"))
    client = make_client(stub)
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."
    assert "secret-token-xyz" not in response.text


# ---------------------------------------------------------------------------
# Resources: standing crisis resources, served without touching the pipeline
# ---------------------------------------------------------------------------


def test_resources_returns_default_crisis_resources_shape_and_content() -> None:
    client = TestClient(create_app(StubPipeline(GenerationError("must never run"))))
    response = client.get("/resources")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"resources"}
    assert body["resources"] == [
        {"name": resource.name, "url": resource.url} for resource in DEFAULT_CRISIS_RESOURCES
    ]


def test_resources_body_carries_no_internals() -> None:
    client = TestClient(create_app(StubPipeline(GenerationError("sk-SECRET"))))
    response = client.get("/resources")
    assert "sk-SECRET" not in response.text
    for entry in response.json()["resources"]:
        assert set(entry) == {"name", "url"}


def test_resources_never_calls_the_pipeline_even_when_generation_fails() -> None:
    # An exploding stub: if /resources touched the pipeline it would 503.
    stub = StubPipeline(GenerationError("generator is down"))
    client = TestClient(create_app(stub), raise_server_exceptions=False)
    response = client.get("/resources")
    assert response.status_code == 200
    assert len(response.json()["resources"]) == len(DEFAULT_CRISIS_RESOURCES)


# ---------------------------------------------------------------------------
# Unknown path + metadata lane lint
# ---------------------------------------------------------------------------


def test_unknown_path_returns_404(real: tuple[TestClient, FakeClient]) -> None:
    client, _fake = real
    response = client.get("/nope")
    assert response.status_code == 404


def test_app_metadata_stays_in_the_wellness_lane() -> None:
    pipeline, _fake = make_real_pipeline([WELL_BEHAVED_REPLY])
    app = create_app(pipeline)
    assert "RE:FRAME" in app.title
    description = app.description.lower()
    assert "wellness" in description
    for forbidden in ("diagnose", "therapy", "treatment", "prescrib"):
        assert forbidden not in description
