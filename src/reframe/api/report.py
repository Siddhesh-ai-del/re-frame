"""``GET /evaluation/report`` — the structured feasibility report over HTTP (7b).

Registers ONE route on an existing FastAPI app (the 7a
:mod:`reframe.api.evaluation` module is untouched). The route reads through
public APIs only (E9): check-ins via :func:`reframe.evaluation.report.
checkins_from_tracker` over the service's tracker, events via
``ae_log.events()`` — no private-attribute access, no direct SQL.

Contract:

- The response carries ``NON_EFFICACY_BANNER`` verbatim and operational
  criterion data only; no message content ever crosses this surface (D1) —
  ids and counts only.
- Record-level parameter failures (``start > end``, planned without enrolled)
  map to ONE generic 422 detail; query-constraint failures (e.g.
  ``expected_per_week=0``) are rejected by FastAPI's own validation.
- Sync ``def`` route; docstrings operational, never clinical.
"""

import datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from reframe.evaluation.log import AdverseEventLog
from reframe.evaluation.pilot import PilotConfig
from reframe.evaluation.report import FeasibilityReport, build_report, checkins_from_tracker
from reframe.measurement.tracker import CheckInTracker

#: Generic 422 detail for any invalid report parameter — leaks nothing about the cause.
REPORT_INVALID_PARAMETERS_DETAIL = "Report parameters are invalid."


class WindowOut(BaseModel):
    """The resolved observation window (both bounds and weeks are both-or-none)."""

    start: str | None
    end: str | None
    weeks: int | None


class ConfigOut(BaseModel):
    """The report configuration as submitted/defaulted."""

    expected_per_week: int
    planned_participants: int | None
    enrolled_participants: int | None


class MetricsOut(BaseModel):
    """Mirror of ``PilotMetrics`` on the wire (str/float/int or null)."""

    window_start: str | None
    window_end: str | None
    total_weeks: int | None
    checkins_in_window: int
    active_weeks: int | None
    retention: float | None
    data_completeness: float | None
    expected_checkins: int | None
    adverse_events_in_window: int
    adverse_events_per_week: float | None


class AeSummaryOut(BaseModel):
    """In-window adverse-event rollups: ids and counts only (D1)."""

    in_window: int
    per_week: float | None
    by_type: dict[str, int]
    by_source: dict[str, int]
    serious_in_window: int
    overdue_serious_ids: list[str]


class CriterionOut(BaseModel):
    """One evaluated progression criterion as the UI needs it."""

    key: str
    label: str
    band: str | None
    value: float | None
    value_label: str
    basis: str
    justification: str
    citation: str


class ReportOut(BaseModel):
    """The complete feasibility report on the wire."""

    generated_at: str
    banner: str
    window: WindowOut
    config: ConfigOut
    metrics: MetricsOut
    adverse_events: AeSummaryOut
    criteria: list[CriterionOut]


def _to_report_out(report: FeasibilityReport) -> ReportOut:
    """Map the frozen report onto the response DTOs (no content, ids/counts only)."""
    metrics = report.metrics
    window_events_in_window = report.metrics.adverse_events_in_window
    return ReportOut(
        generated_at=report.generated_at.isoformat(),
        banner=report.banner,
        window=WindowOut(
            start=report.window_start.isoformat() if report.window_start else None,
            end=report.window_end.isoformat() if report.window_end else None,
            weeks=report.total_weeks,
        ),
        config=ConfigOut(
            expected_per_week=report.config.expected_per_week,
            planned_participants=report.config.planned_participants,
            enrolled_participants=report.config.enrolled_participants,
        ),
        metrics=MetricsOut(
            window_start=metrics.window_start.isoformat() if metrics.window_start else None,
            window_end=metrics.window_end.isoformat() if metrics.window_end else None,
            total_weeks=metrics.total_weeks,
            checkins_in_window=metrics.checkins_in_window,
            active_weeks=metrics.active_weeks,
            retention=metrics.retention,
            data_completeness=metrics.data_completeness,
            expected_checkins=metrics.expected_checkins,
            adverse_events_in_window=metrics.adverse_events_in_window,
            adverse_events_per_week=metrics.adverse_events_per_week,
        ),
        adverse_events=AeSummaryOut(
            in_window=window_events_in_window,
            per_week=metrics.adverse_events_per_week,
            by_type=dict(report.events_by_type),
            by_source=dict(report.events_by_source),
            serious_in_window=report.serious_in_window,
            overdue_serious_ids=list(report.overdue_serious_ids),
        ),
        criteria=[
            CriterionOut(
                key=criterion.key,
                label=criterion.label,
                band=criterion.band,
                value=criterion.value,
                value_label=criterion.value_label,
                basis=criterion.basis,
                justification=criterion.justification,
                citation=criterion.citation,
            )
            for criterion in report.criteria
        ],
    )


def include_report_routes(
    app: FastAPI,
    tracker: CheckInTracker,
    ae_log: AdverseEventLog,
) -> None:
    """Register ``GET /evaluation/report`` over ``tracker`` and ``ae_log``.

    Parameter validation is fail-closed to the single generic 422 detail:
    planned without enrolled (or the reverse) and an explicit window whose
    start is after its end both map to ``REPORT_INVALID_PARAMETERS_DETAIL``;
    ``expected_per_week`` below 1 never reaches the handler — FastAPI's own
    query validation rejects it.
    """

    @app.get("/evaluation/report", response_model=ReportOut)
    def evaluation_report(
        start: Annotated[datetime.date | None, Query()] = None,
        end: Annotated[datetime.date | None, Query()] = None,
        expected_per_week: Annotated[int, Query(ge=1)] = 1,
        planned: Annotated[int | None, Query(ge=1)] = None,
        enrolled: Annotated[int | None, Query(ge=1)] = None,
    ) -> ReportOut:
        """Assemble the feasibility report (operational parameters only)."""
        if (planned is None) != (enrolled is None):
            raise HTTPException(status_code=422, detail=REPORT_INVALID_PARAMETERS_DETAIL)
        config = PilotConfig(
            expected_per_week=expected_per_week,
            planned_participants=planned,
            enrolled_participants=enrolled,
        )
        try:
            report = build_report(
                checkins_from_tracker(tracker),
                ae_log.events(),
                config=config,
                window_start=start,
                window_end=end,
            )
        except ValueError:
            raise HTTPException(status_code=422, detail=REPORT_INVALID_PARAMETERS_DETAIL) from None
        return _to_report_out(report)
