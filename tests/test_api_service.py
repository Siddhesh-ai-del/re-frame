"""HTTP-layer tests for ``reframe.api.service`` — one app carries both route families.

``create_service`` is the composition root: it wires a real conversation
pipeline (scripted fake LLM client + the real content library) and a check-in
tracker into a single FastAPI app, proving chat and measurement share one
process while the deterministic safety routing (crisis bypass) survives above
the HTTP boundary.

Tracker wiring is exercised in all three configurations: the in-memory dev
default, a durable ``db_path`` store that closes on shutdown (simulated
restart included), and an injected ``tracker_factory``. The v1 service is
single-user and local by design — no auth, CORS, or rate limiting here.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import reframe
from reframe.api.service import create_service
from reframe.generation import ConstrainedGenerator, GenerationRequest, GenerationResponse
from reframe.measurement.tracker import CheckInTracker
from reframe.pipeline.messages import CRISIS_RESPONSE

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


def make_generator(replies: list[str]) -> tuple[ConstrainedGenerator, FakeClient]:
    client = FakeClient(replies)
    return ConstrainedGenerator(client), client


def _checkin_body(date: str) -> dict[str, object]:
    return {"instrument_id": "phq9", "responses": [0] * 9, "date": date}


# ---------------------------------------------------------------------------
# Composition: one app serves health, chat, AND measurement routes
# ---------------------------------------------------------------------------


def test_default_service_carries_both_route_families_on_one_app() -> None:
    generator, fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator)

    with TestClient(app) as client:
        # In-memory default: no store is created; the shutdown handler is a no-op.
        assert app.state.store is None

        health = client.get("/health")
        assert health.status_code == 200
        health_body = health.json()
        assert health_body["status"] == "ok"
        assert health_body["version"] == reframe.__version__

        instruments = client.get("/instruments")
        assert instruments.status_code == 200
        ids = [instrument["id"] for instrument in instruments.json()["instruments"]]
        assert ids == ["phq9", "gad7", "k10"]

        checkin = client.post("/checkins", json=_checkin_body("2026-10-18"))
        assert checkin.status_code == 200

        chat = client.post("/chat", json={"message": "I can't stop thinking about work"})
        assert chat.status_code == 200
        assert chat.json()["route"] == "generated"
        assert fake.call_count == 1


def test_service_reuses_create_app_metadata() -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator)
    assert "RE:FRAME" in app.title
    assert "wellness" in app.description.lower()


# ---------------------------------------------------------------------------
# Durability: db_path survives an app restart through the HTTP layer
# ---------------------------------------------------------------------------


def test_checkins_survive_a_restart_through_the_http_layer(tmp_path: Path) -> None:
    db_path = tmp_path / "s.db"
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])

    first_app = create_service(generator=generator, db_path=db_path)
    with TestClient(first_app) as client:
        assert first_app.state.store is not None
        recorded = client.post("/checkins", json=_checkin_body("2026-10-01"))
        assert recorded.status_code == 200

    # Fresh composition over the same file: history must replay from disk.
    restarted_app = create_service(generator=generator, db_path=db_path)
    with TestClient(restarted_app) as client:
        history = client.get("/checkins/phq9")
        assert history.status_code == 200
        checkins = history.json()["checkins"]
        assert len(checkins) == 1
        assert checkins[0]["responses"] == [0] * 9
        assert checkins[0]["date"] == "2026-10-01"
        assert checkins[0]["action"] == "proceed"


# ---------------------------------------------------------------------------
# Tracker injection: the factory is called and its tracker serves the routes
# ---------------------------------------------------------------------------


def test_tracker_factory_is_called_once_and_its_tracker_serves_checkins() -> None:
    factory_calls: list[int] = []

    def factory() -> CheckInTracker:
        factory_calls.append(1)
        return CheckInTracker()

    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, tracker_factory=factory)
    assert factory_calls == [1]
    assert app.state.store is None

    with TestClient(app) as client:
        recorded = client.post("/checkins", json=_checkin_body("2026-10-18"))
        assert recorded.status_code == 200
        history = client.get("/checkins/phq9")
        assert len(history.json()["checkins"]) == 1


# ---------------------------------------------------------------------------
# Shutdown: the registered handler closes a created store, no-ops without one
# ---------------------------------------------------------------------------


def test_shutdown_handler_closes_a_created_sqlite_store(tmp_path: Path) -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, db_path=tmp_path / "s.db")

    with TestClient(app):
        pass

    store = app.state.store
    assert store is not None
    # Public behavior after shutdown: the connection is closed fail-closed.
    with pytest.raises(sqlite3.ProgrammingError):
        store.load()


def test_shutdown_handler_without_a_store_is_a_clean_noop() -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator)

    # Exiting the context runs the shutdown handler; store is None, no error.
    with TestClient(app):
        assert app.state.store is None


# ---------------------------------------------------------------------------
# Safety routing through the composed app
# ---------------------------------------------------------------------------


def test_chat_crisis_bypasses_with_resources_and_never_calls_the_generator() -> None:
    generator, fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator)

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "I want to kill myself"})

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "crisis_bypass"
    assert body["reply"] == CRISIS_RESPONSE.text
    assert len(body["resources"]) >= 1
    assert all("name" in resource for resource in body["resources"])
    assert fake.call_count == 0
