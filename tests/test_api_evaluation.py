"""HTTP-layer tests for ``reframe.api.evaluation`` — the AE monitoring endpoints.

Strict TDD: written BEFORE ``reframe/api/evaluation.py`` exists; the first run
must fail with an ``ImportError`` (RED).

Operational safety monitoring over the ``/evaluation/*`` namespace: list the
logged adverse events, record a reviewer-entered event (always stamped
``source="review"`` — D4, never trusted from the client), and mark a 48-hour
follow-up completed. Every record-level failure maps to ONE generic 422
detail and unknown ids to one generic 404 detail — no internals leaked.
"""

import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from reframe.api.evaluation import (
    ADVERSE_EVENT_UNRECORDED_DETAIL,
    UNKNOWN_ADVERSE_EVENT_DETAIL,
    include_evaluation_routes,
)
from reframe.evaluation import AdverseEventLog


def make_client(ae_log: AdverseEventLog | None = None) -> TestClient:
    """Wire a fresh bare FastAPI app around ``ae_log`` (an in-memory log by default)."""
    app = FastAPI()
    app.state.ae_log = ae_log if ae_log is not None else AdverseEventLog()
    include_evaluation_routes(app, app.state.ae_log)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /evaluation/adverse-events
# ---------------------------------------------------------------------------


def test_get_an_empty_log_returns_an_empty_list() -> None:
    client = make_client()
    response = client.get("/evaluation/adverse-events")
    assert response.status_code == 200
    assert response.json() == {"adverse_events": []}


def test_posted_events_are_listed_in_insertion_order() -> None:
    client = make_client()
    first = client.post("/evaluation/adverse-events", json={"type": "sycophancy_episode"})
    second = client.post("/evaluation/adverse-events", json={"type": "crisis_response_failure"})
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.get("/evaluation/adverse-events")

    assert response.status_code == 200
    listed = response.json()["adverse_events"]
    assert [entry["id"] for entry in listed] == [
        first.json()["id"],
        second.json()["id"],
    ]


# ---------------------------------------------------------------------------
# POST /evaluation/adverse-events — reviewer records, source always "review"
# ---------------------------------------------------------------------------


def test_post_stamps_review_source_and_taxonomy_defaults() -> None:
    client = make_client()
    response = client.post(
        "/evaluation/adverse-events",
        json={"type": "sycophancy_episode", "reference": "session 3 turn 14"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "sycophancy_episode"
    assert body["source"] == "review"  # D4: server-set, never client-trusted
    assert body["serious"] is False
    assert body["followup_completed"] is False
    assert body["followup_due_at"] is None  # non-serious: no 48h marker (D3)
    assert body["reference"] == "session 3 turn 14"
    assert body["id"]
    assert body["detected_at"].endswith("+00:00")


def test_post_serious_default_carries_the_48_hour_followup_marker() -> None:
    client = make_client()
    response = client.post("/evaluation/adverse-events", json={"type": "crisis_response_failure"})
    assert response.status_code == 200
    body = response.json()
    assert body["serious"] is True

    detected_at = datetime.datetime.fromisoformat(body["detected_at"])
    due_at = datetime.datetime.fromisoformat(body["followup_due_at"])
    assert due_at - detected_at == datetime.timedelta(hours=48)


def test_post_explicit_serious_override_wins_in_both_directions() -> None:
    client = make_client()
    escalated = client.post(
        "/evaluation/adverse-events", json={"type": "sycophancy_episode", "serious": True}
    )
    downgraded = client.post(
        "/evaluation/adverse-events",
        json={"type": "crisis_response_failure", "serious": False},
    )
    assert escalated.json()["serious"] is True
    assert escalated.json()["followup_due_at"] is not None
    assert downgraded.json()["serious"] is False
    assert downgraded.json()["followup_due_at"] is None


def test_post_unknown_type_maps_to_the_generic_422() -> None:
    client = make_client()
    response = client.post("/evaluation/adverse-events", json={"type": "banana"})
    assert response.status_code == 422
    assert response.json() == {"detail": ADVERSE_EVENT_UNRECORDED_DETAIL}
    assert "banana" not in response.text
    assert "ValueError" not in response.text


def test_post_whitespace_reference_maps_to_the_generic_422() -> None:
    client = make_client()
    response = client.post(
        "/evaluation/adverse-events",
        json={"type": "sycophancy_episode", "reference": "   "},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": ADVERSE_EVENT_UNRECORDED_DETAIL}


def test_post_overlong_reference_maps_to_the_generic_422() -> None:
    client = make_client()
    response = client.post(
        "/evaluation/adverse-events",
        json={"type": "sycophancy_episode", "reference": "x" * 201},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": ADVERSE_EVENT_UNRECORDED_DETAIL}


def test_post_extra_field_is_rejected_by_pydantic() -> None:
    client = make_client()
    response = client.post(
        "/evaluation/adverse-events",
        json={"type": "sycophancy_episode", "source": "automatic"},
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_post_empty_type_is_rejected_by_pydantic() -> None:
    client = make_client()
    response = client.post("/evaluation/adverse-events", json={"type": ""})
    assert response.status_code == 422


def test_a_failed_post_records_nothing_in_the_log() -> None:
    ae_log = AdverseEventLog()
    client = make_client(ae_log)
    assert client.post("/evaluation/adverse-events", json={"type": "banana"}).status_code == 422
    assert ae_log.events() == ()


# ---------------------------------------------------------------------------
# POST /evaluation/adverse-events/{event_id}/followup — mark the 48h marker done
# ---------------------------------------------------------------------------


def test_followup_marks_completed_and_keeps_the_due_marker_visible() -> None:
    client = make_client()
    created = client.post("/evaluation/adverse-events", json={"type": "crisis_response_failure"})
    event_id = created.json()["id"]

    response = client.post(f"/evaluation/adverse-events/{event_id}/followup")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == event_id
    assert body["followup_completed"] is True
    assert body["followup_due_at"] is not None
    assert body["serious"] is True


def test_followup_on_a_non_serious_event_stays_due_at_none() -> None:
    client = make_client()
    created = client.post("/evaluation/adverse-events", json={"type": "sycophancy_episode"})
    event_id = created.json()["id"]

    response = client.post(f"/evaluation/adverse-events/{event_id}/followup")

    assert response.status_code == 200
    assert response.json()["followup_completed"] is True
    assert response.json()["followup_due_at"] is None


def test_followup_on_an_unknown_id_is_a_generic_404() -> None:
    client = make_client()
    response = client.post("/evaluation/adverse-events/nope/followup")
    assert response.status_code == 404
    assert response.json() == {"detail": UNKNOWN_ADVERSE_EVENT_DETAIL}
