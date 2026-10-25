"""HTTP-layer tests for ``reframe.api.measure`` — the measurement endpoints.

A bare ``FastAPI`` app with ``include_measurement_routes`` wired to a real
``CheckInTracker`` exercises the instrument catalog and the longitudinal
check-in contract end to end. The safety-critical assertions are behavioral:
escalation must be driven by item 9 / flags (never by totals), the ESCALATE
route must return the same scripted crisis copy the chat uses, and every
record-level failure must map to a generic 422 that leaks no internals.

No network calls: ``TestClient`` runs the ASGI app in-process.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from reframe.api.measure import include_measurement_routes
from reframe.measurement.routing import CHECKIN_CONCERN_TEXT
from reframe.measurement.tracker import CheckInTracker
from reframe.pipeline.messages import CRISIS_RESPONSE

#: The ONLY detail the API ever attaches to a failed check-in (no internals).
GENERIC_422_DETAIL = "Check-in could not be recorded."

#: A phq9 response vector totalling 16 WITHOUT touching item 9 (the spec's
#: "[2]*9" referral example would trip item-9 escalation; totals >= 16 must
#: be reachable without the crisis flag to isolate the referral rule).
REFERRAL_RESPONSES = [2, 2, 2, 2, 2, 2, 2, 2, 0]


def make_client(tracker: CheckInTracker) -> TestClient:
    """Wire a fresh bare FastAPI app around ``tracker``."""
    app = FastAPI()
    include_measurement_routes(app, tracker)
    return TestClient(app)


@pytest.fixture
def tracker() -> CheckInTracker:
    return CheckInTracker()


@pytest.fixture
def client(tracker: CheckInTracker) -> TestClient:
    return make_client(tracker)


# ---------------------------------------------------------------------------
# GET /instruments — full catalog detail so a UI can render forms
# ---------------------------------------------------------------------------


def test_instruments_lists_every_active_instrument_in_order(client: TestClient) -> None:
    response = client.get("/instruments")
    assert response.status_code == 200
    body = response.json()
    assert len(body["instruments"]) == 4
    assert [instrument["id"] for instrument in body["instruments"]] == [
        "phq9",
        "gad7",
        "k10",
        "scs_sf",
    ]


def test_instruments_phq9_has_nine_items_and_item9_mentions_being_better_off_dead(
    client: TestClient,
) -> None:
    phq9 = client.get("/instruments").json()["instruments"][0]
    assert len(phq9["items"]) == 9
    item9 = phq9["items"][8]
    assert item9["index"] == 9
    assert "better off dead" in item9["prompt"]


def test_instruments_k10_uses_the_1_to_5_scale_with_total_max_50(client: TestClient) -> None:
    k10 = client.get("/instruments").json()["instruments"][2]
    assert k10["scale_min"] == 1
    assert k10["total_max"] == 50


def test_instruments_every_instrument_has_options_and_a_citation(client: TestClient) -> None:
    for instrument in client.get("/instruments").json()["instruments"]:
        assert instrument["answer_options"], instrument["id"]
        assert instrument["citation"].strip(), instrument["id"]


def test_instruments_phq9_bands_partition_every_possible_total(client: TestClient) -> None:
    """Property-style: each total 0..27 falls in exactly one severity band."""
    phq9 = client.get("/instruments").json()["instruments"][0]
    bands = phq9["severity_bands"]
    for total in range(phq9["total_min"], phq9["total_max"] + 1):
        hits = [band for band in bands if band["lower"] <= total <= band["upper"]]
        assert len(hits) == 1, f"total {total} matched {len(hits)} bands"


# ---------------------------------------------------------------------------
# POST /checkins — happy path and flag-driven routing
# ---------------------------------------------------------------------------


def test_checkin_happy_path_scores_minimal_and_proceeds(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-10-18"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["instrument_id"] == "phq9"
    assert body["date"] == "2026-10-18"
    assert body["responses"] == [0] * 9
    assert body["total"] == 0
    assert body["severity_label"] == "minimal"
    assert body["flags"] == []
    assert body["action"] == "proceed"
    assert body["message_id"] is None
    assert body["message"] is None


def test_checkin_item9_flag_escalates_to_the_scripted_crisis_copy(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 8 + [1], "date": "2026-10-18"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "escalate" in body["flags"]
    assert body["action"] == "hard_bypass"
    assert body["message_id"] == "crisis_response_v1"
    assert body["message"] == CRISIS_RESPONSE.text


def test_checkin_persistent_totals_prompt_referral_conversation(client: TestClient) -> None:
    first = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": REFERRAL_RESPONSES, "date": "2026-10-01"},
    )
    second = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": REFERRAL_RESPONSES, "date": "2026-10-08"},
    )
    assert first.status_code == 200
    assert first.json()["flags"] == []
    body = second.json()
    assert "referral_prompt" in body["flags"]
    assert body["action"] == "human_review"
    assert body["message"] == CHECKIN_CONCERN_TEXT


def test_checkin_early_worsening_vs_baseline_opens_human_review(client: TestClient) -> None:
    baseline = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-10-01"},
    )
    assert baseline.json()["flags"] == []
    second = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": REFERRAL_RESPONSES, "date": "2026-10-08"},
    )
    body = second.json()
    assert "early_worsening" in body["flags"]
    assert body["action"] == "human_review"
    assert body["message"] == CHECKIN_CONCERN_TEXT


# ---------------------------------------------------------------------------
# POST /checkins — fail-closed error mapping, no internals leaked
# ---------------------------------------------------------------------------


def test_checkin_unknown_instrument_maps_to_generic_422(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={"instrument_id": "nope", "responses": [0] * 9, "date": "2026-10-18"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": GENERIC_422_DETAIL}
    assert "ValueError" not in response.text


def test_checkin_wrong_response_count_maps_to_generic_422(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 8, "date": "2026-10-18"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": GENERIC_422_DETAIL}


def test_checkin_out_of_range_response_maps_to_generic_422(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 8 + [9], "date": "2026-10-18"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": GENERIC_422_DETAIL}


def test_checkin_invalid_date_format_rejected_by_pydantic(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "18-10-2026"},
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_checkin_impossible_calendar_date_rejected_by_pydantic(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-02-30"},
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_checkin_out_of_order_date_maps_to_generic_422(client: TestClient) -> None:
    first = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-10-10"},
    )
    assert first.status_code == 200
    response = client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-10-05"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": GENERIC_422_DETAIL}


def test_checkin_unknown_extra_key_rejected_by_pydantic(client: TestClient) -> None:
    response = client.post(
        "/checkins",
        json={
            "instrument_id": "phq9",
            "responses": [0] * 9,
            "date": "2026-10-18",
            "admin": True,
        },
    )
    assert response.status_code == 422
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# GET /checkins/{instrument_id} — history with routing recomputed per entry
# ---------------------------------------------------------------------------


def test_history_returns_recorded_checkins_with_recomputed_routing(client: TestClient) -> None:
    client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 8 + [1], "date": "2026-10-18"},
    )
    client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-10-19"},
    )
    response = client.get("/checkins/phq9")
    assert response.status_code == 200
    checkins = response.json()["checkins"]
    assert len(checkins) == 2
    escalated = checkins[0]
    assert escalated["action"] == "hard_bypass"
    assert escalated["message_id"] == "crisis_response_v1"
    assert escalated["message"] == CRISIS_RESPONSE.text
    proceed = checkins[1]
    assert proceed["flags"] == []
    assert proceed["action"] == "proceed"
    assert proceed["message"] is None


def test_history_for_valid_instrument_without_checkins_is_empty(client: TestClient) -> None:
    response = client.get("/checkins/gad7")
    assert response.status_code == 200
    assert response.json() == {"checkins": []}


def test_history_for_unknown_instrument_is_404(client: TestClient) -> None:
    response = client.get("/checkins/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "unknown instrument"}


def test_histories_are_isolated_per_instrument(client: TestClient) -> None:
    client.post(
        "/checkins",
        json={"instrument_id": "phq9", "responses": [0] * 9, "date": "2026-10-18"},
    )
    assert client.get("/checkins/phq9").json()["checkins"] != []
    assert client.get("/checkins/gad7").json() == {"checkins": []}
