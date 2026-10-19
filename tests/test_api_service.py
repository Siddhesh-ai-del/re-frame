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


# ---------------------------------------------------------------------------
# Stage 6e: static SPA serving (prod path — the built SPA served by FastAPI)
# ---------------------------------------------------------------------------

SPA_MARKER = "<!doctype html><html><head><title>RE:FRAME SPA</title></head>"
ASSET_BODY = "console.log('hashed asset');\n"


@pytest.fixture
def spa_dir(tmp_path: Path) -> Path:
    """Tiny stand-in for ``web/dist``: an index.html plus one hashed asset."""
    (tmp_path / "index.html").write_text(
        SPA_MARKER + '<body><div id="root"></div></body></html>', encoding="utf-8"
    )
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app-abc123.js").write_text(ASSET_BODY, encoding="utf-8")
    return tmp_path


def _api_only_assertions(client: TestClient) -> None:
    """The API surface must answer exactly the same in API-only mode."""
    assert client.get("/health").status_code == 200
    assert client.get("/resources").status_code == 200
    assert client.get("/instruments").status_code == 200
    assert client.get("/content/exercises").status_code == 200
    chat = client.post("/chat", json={"message": "I can't stop thinking about work"})
    assert chat.status_code == 200
    assert chat.json()["route"] == "generated"


def test_static_dir_serves_the_spa_for_every_unknown_get(spa_dir: Path) -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=spa_dir)

    with TestClient(app) as client:
        for path in ("/", "/chat", "/exercises", "/some/client/route"):
            response = client.get(path)
            assert response.status_code == 200, path
            assert "text/html" in response.headers["content-type"], path
            assert "RE:FRAME SPA" in response.text, path


def test_static_mount_does_not_swallow_the_json_api(spa_dir: Path) -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=spa_dir)

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.headers["content-type"].startswith("application/json")
        assert health.json()["status"] == "ok"

        resources = client.get("/resources")
        assert resources.status_code == 200
        assert len(resources.json()["resources"]) >= 2

        instruments = client.get("/instruments")
        assert instruments.status_code == 200
        assert "json" in instruments.headers["content-type"]

        exercises = client.get("/content/exercises")
        assert exercises.status_code == 200
        assert "json" in exercises.headers["content-type"]


def test_static_mount_keeps_checkin_routes_on_the_api(spa_dir: Path) -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=spa_dir)

    with TestClient(app) as client:
        recorded = client.post(
            "/checkins",
            json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-10-19"},
        )
        assert recorded.status_code == 200

        history = client.get("/checkins/phq9")
        assert history.status_code == 200
        assert "json" in history.headers["content-type"]
        assert len(history.json()["checkins"]) == 1

        purged = client.delete("/checkins")
        assert purged.status_code == 200
        assert purged.json()["deleted"] == 1


def test_static_mount_keeps_post_chat_on_the_api(spa_dir: Path) -> None:
    generator, fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=spa_dir)

    with TestClient(app) as client:
        chat = client.post("/chat", json={"message": "I can't stop thinking about work"})

    assert chat.status_code == 200
    assert chat.json()["route"] == "generated"
    assert chat.json()["reply"] == WELL_BEHAVED_REPLY
    assert fake.call_count == 1


def test_hashed_assets_are_served_verbatim(spa_dir: Path) -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=spa_dir)

    with TestClient(app) as client:
        asset = client.get("/assets/app-abc123.js")

    assert asset.status_code == 200
    assert "javascript" in asset.headers["content-type"]
    assert asset.text == ASSET_BODY


def test_without_static_dir_no_spa_route_leaks() -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator)

    with TestClient(app) as client:
        _api_only_assertions(client)
        # API-only mode: the SPA is nowhere on the app.
        assert client.get("/").status_code == 404
        assert client.get("/some/client/route").status_code == 404
        # GET /chat exists only as POST /chat -> method mismatch, no SPA.
        assert client.get("/chat").status_code == 405


def test_missing_static_dir_is_treated_as_api_only(tmp_path: Path) -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=tmp_path / "does-not-exist")

    with TestClient(app) as client:
        _api_only_assertions(client)
        assert client.get("/").status_code == 404
        assert client.get("/some/client/route").status_code == 404


def test_static_file_pointing_at_a_file_is_treated_as_api_only(tmp_path: Path) -> None:
    # ``static_dir`` must be a directory; a stray file is ignored (API-only).
    stray = tmp_path / "not-a-dir.txt"
    stray.write_text("x", encoding="utf-8")
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=stray)

    with TestClient(app) as client:
        _api_only_assertions(client)
        assert client.get("/").status_code == 404


def test_static_mount_adds_nothing_to_the_openapi_schema(spa_dir: Path) -> None:
    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    without_static = create_service(generator=generator)
    with_static = create_service(generator=generator, static_dir=spa_dir)

    assert with_static.openapi() == without_static.openapi()


def test_static_serving_never_escapes_the_served_directory(tmp_path: Path) -> None:
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(SPA_MARKER, encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOP-SECRET-DO-NOT-SERVE", encoding="utf-8")

    generator, _fake = make_generator([WELL_BEHAVED_REPLY])
    app = create_service(generator=generator, static_dir=static_dir)

    with TestClient(app) as client:
        escaped = client.get("/%2e%2e/secret.txt")

    assert "TOP-SECRET-DO-NOT-SERVE" not in escaped.text
