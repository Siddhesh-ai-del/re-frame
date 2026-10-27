"""HTTP-layer tests for ``reframe.api.report`` — ``GET /evaluation/report``.

Strict TDD: written BEFORE ``reframe/api/report.py`` exists; the first run
must fail with an ``ImportError`` (RED).

The route is wired like the service wires it: one bare FastAPI app carrying
the 7a measurement routes, the 7a evaluation routes, and the new report route
over the SAME tracker and adverse-event log — so the cross-surface test
(record an early-worsening check-in through the measure route, then see the
automatic event reflected in the report) exercises real composition, not a
stub. Every record-level failure maps to the ONE generic 422 detail; the
response carries the non-efficacy banner verbatim and never any message
content (D1) — ids and counts only.
"""

import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from reframe.api.evaluation import include_evaluation_routes
from reframe.api.measure import include_measurement_routes
from reframe.api.report import REPORT_INVALID_PARAMETERS_DETAIL, include_report_routes
from reframe.evaluation.log import AdverseEventLog
from reframe.measurement.tracker import CheckInTracker

#: The banner exactly as specified for stage 7b (E1) — pinned verbatim.
EXPECTED_BANNER = (
    "Feasibility report — operational feasibility parameters only. This "
    "evaluation was not designed or powered to support any efficacy claim; "
    "scores, rates, and counts here are descriptive operational data, not "
    "clinical findings. No diagnostic or treatment claims are made."
)

#: The four criterion keys, in research-report order (E4).
CRITERION_KEYS = ["recruitment", "retention", "data_completeness", "safety_event_rate"]


def make_client(
    tracker: CheckInTracker | None = None,
    ae_log: AdverseEventLog | None = None,
) -> TestClient:
    """Wire a bare FastAPI app exactly like the service: measure + evaluation + report."""
    app = FastAPI()
    tracker = tracker if tracker is not None else CheckInTracker()
    ae_log = ae_log if ae_log is not None else AdverseEventLog()
    include_measurement_routes(app, tracker, ae_log)
    include_evaluation_routes(app, ae_log)
    include_report_routes(app, tracker, ae_log)
    return TestClient(app)


def _checkin(date: str) -> dict[str, object]:
    return {"instrument_id": "phq9", "responses": [0] * 9, "date": date}


# ---------------------------------------------------------------------------
# Empty state: 200, null window, banner verbatim, four not-evaluable criteria
# ---------------------------------------------------------------------------


def test_empty_report_is_200_with_a_null_window_and_the_banner() -> None:
    client = make_client()
    response = client.get("/evaluation/report")

    assert response.status_code == 200
    body = response.json()
    assert body["banner"] == EXPECTED_BANNER
    assert body["window"] == {"start": None, "end": None, "weeks": None}
    assert body["config"] == {
        "expected_per_week": 1,
        "planned_participants": None,
        "enrolled_participants": None,
    }
    assert body["adverse_events"]["in_window"] == 0
    assert body["adverse_events"]["overdue_serious_ids"] == []
    assert body["metrics"]["checkins_in_window"] == 0
    assert body["metrics"]["retention"] is None
    assert body["metrics"]["data_completeness"] is None
    assert body["metrics"]["adverse_events_per_week"] is None


def test_empty_report_carries_all_four_criteria_as_not_evaluable() -> None:
    client = make_client()
    body = client.get("/evaluation/report").json()

    criteria = body["criteria"]
    assert [criterion["key"] for criterion in criteria] == CRITERION_KEYS
    for criterion in criteria:
        assert criterion["band"] is None
        assert criterion["value"] is None
        assert "not evaluable" in criterion["value_label"]
        assert criterion["basis"]
        assert criterion["justification"]
        assert criterion["citation"]


def test_report_never_carries_message_content() -> None:
    tracker = CheckInTracker()
    client = make_client(tracker=tracker)
    assert client.post("/checkins", json=_checkin("2026-10-01")).status_code == 200

    response = client.get("/evaluation/report")

    assert response.status_code == 200
    # The check-in's response vector must not leak into the report surface.
    assert "responses" not in response.text
    assert '"0", "0"' not in response.text


# ---------------------------------------------------------------------------
# Seeded data: window auto-span, retention evaluated
# ---------------------------------------------------------------------------


def test_seeded_checkins_auto_span_the_window_and_evaluate_retention() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", [0] * 9, datetime.date(2026, 10, 1))
    tracker.record("phq9", [1] * 9, datetime.date(2026, 10, 8))
    client = make_client(tracker=tracker)

    body = client.get("/evaluation/report").json()

    assert body["window"] == {"start": "2026-10-01", "end": "2026-10-08", "weeks": 2}
    assert body["metrics"]["checkins_in_window"] == 2
    assert body["metrics"]["active_weeks"] == 2
    assert body["metrics"]["retention"] == 1.0
    assert body["metrics"]["expected_checkins"] == 2
    assert body["metrics"]["data_completeness"] == 1.0

    by_key = {criterion["key"]: criterion for criterion in body["criteria"]}
    assert by_key["retention"]["band"] == "green"
    assert by_key["retention"]["value"] == 1.0
    assert by_key["retention"]["value_label"] == "2 of 2 weeks active"
    assert by_key["data_completeness"]["band"] == "green"
    assert by_key["safety_event_rate"]["band"] == "green"  # observation, no events


def test_seeded_data_with_paired_recruitment_counts_evaluates_recruitment() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", [0] * 9, datetime.date(2026, 10, 1))
    client = make_client(tracker=tracker)

    response = client.get("/evaluation/report", params={"planned": 10, "enrolled": 8})
    by_key = {c["key"]: c for c in response.json()["criteria"]}

    assert by_key["recruitment"]["band"] == "amber"  # 0.80: >= 0.75, < 1.00
    assert by_key["recruitment"]["value"] == 0.8
    assert by_key["recruitment"]["value_label"] == "8 of 10 enrolled"


# ---------------------------------------------------------------------------
# Explicit window + parameter validation (generic 422 only)
# ---------------------------------------------------------------------------


def test_explicit_window_query_params_are_respected() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", [0] * 9, datetime.date(2026, 10, 1))
    tracker.record("phq9", [0] * 9, datetime.date(2026, 10, 20))
    client = make_client(tracker=tracker)

    body = client.get(
        "/evaluation/report",
        params={"start": "2026-10-01", "end": "2026-10-10"},
    ).json()

    assert body["window"] == {"start": "2026-10-01", "end": "2026-10-10", "weeks": 2}
    assert body["metrics"]["checkins_in_window"] == 1


def test_start_after_end_maps_to_the_generic_422_detail() -> None:
    client = make_client()
    response = client.get(
        "/evaluation/report",
        params={"start": "2026-10-20", "end": "2026-10-01"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": REPORT_INVALID_PARAMETERS_DETAIL}
    assert "ValueError" not in response.text


def test_planned_without_enrolled_maps_to_the_generic_422_detail() -> None:
    client = make_client()
    response = client.get("/evaluation/report", params={"planned": 10})

    assert response.status_code == 422
    assert response.json() == {"detail": REPORT_INVALID_PARAMETERS_DETAIL}


def test_enrolled_without_planned_maps_to_the_generic_422_detail() -> None:
    client = make_client()
    response = client.get("/evaluation/report", params={"enrolled": 10})

    assert response.status_code == 422
    assert response.json() == {"detail": REPORT_INVALID_PARAMETERS_DETAIL}


def test_expected_per_week_below_one_is_a_fastapi_422() -> None:
    client = make_client()
    response = client.get("/evaluation/report", params={"expected_per_week": 0})

    assert response.status_code == 422
    # Query-constraint rejection: FastAPI's own validation body, not ours.
    assert REPORT_INVALID_PARAMETERS_DETAIL not in response.text


# ---------------------------------------------------------------------------
# Cross-surface integration: 7a measure route -> 7b report route
# ---------------------------------------------------------------------------


def test_early_worsening_recorded_by_the_measure_route_shows_in_the_report() -> None:
    client = make_client()
    worsening = {"instrument_id": "phq9", "responses": [2] * 8 + [0], "date": "2026-10-08"}
    assert client.post("/checkins", json=_checkin("2026-10-01")).status_code == 200
    assert client.post("/checkins", json=worsening).status_code == 200

    body = client.get("/evaluation/report").json()

    adverse = body["adverse_events"]
    assert adverse["in_window"] == 1
    assert adverse["by_type"] == {"transient_early_worsening": 1}
    assert adverse["by_source"] == {"automatic": 1}
    assert adverse["serious_in_window"] == 0
    by_key = {criterion["key"]: criterion for criterion in body["criteria"]}
    assert by_key["safety_event_rate"]["band"] == "green"  # expected monitoring signal


def test_report_route_is_registered_after_the_seven_a_routes() -> None:
    client = make_client()
    paths = {route.path for route in client.app.routes if hasattr(route, "path")}

    assert "/evaluation/report" in paths
    assert "/evaluation/adverse-events" in paths  # 7a route untouched
    assert "/checkins" in paths  # 7a route untouched
