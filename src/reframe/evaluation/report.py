"""Feasibility-report assembly and markdown rendering (stage 7b).

Composes :func:`reframe.evaluation.pilot.compute_metrics` with the
pre-specified progression criteria (:mod:`reframe.evaluation.progression`)
into one immutable :class:`FeasibilityReport`, and renders it as markdown.

Honesty rules bound every byte this module emits (E1):

- ``NON_EFFICACY_BANNER`` appears verbatim in every report (JSON and markdown).
- Bands are OPERATIONAL review statuses — never clinical findings, never
  efficacy claims; thresholds are provisional design defaults (E6).
- Not-evaluable criteria say so with the exact E4 reason text — a missing
  input is never rendered as a zero or a pass.
- Event rollups carry ids and counts only, never message content (D1).
- Check-ins are read through the public tracker API per active instrument (E9).
"""

import datetime
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.evaluation.pilot import PilotConfig, PilotMetrics, compute_metrics
from reframe.evaluation.progression import (
    DEFAULT_PROGRESSION_CRITERIA,
    band_from_value,
    safety_band,
)
from reframe.measurement.instruments import INSTRUMENTS
from reframe.measurement.tracker import CheckIn, CheckInTracker

#: Embedded verbatim in every report — feasibility only, never efficacy (E1).
NON_EFFICACY_BANNER: str = (
    "Feasibility report — operational feasibility parameters only. This "
    "evaluation was not designed or powered to support any efficacy claim; "
    "scores, rates, and counts here are descriptive operational data, not "
    "clinical findings. No diagnostic or treatment claims are made."
)


@dataclass(frozen=True)
class CriterionResult:
    """One evaluated progression criterion: band, observed value, and basis."""

    key: str
    label: str
    band: str | None
    value: float | None
    value_label: str
    basis: str
    justification: str
    citation: str


@dataclass(frozen=True)
class FeasibilityReport:
    """The assembled, immutable feasibility report."""

    generated_at: datetime.datetime
    banner: str
    window_start: datetime.date | None
    window_end: datetime.date | None
    total_weeks: int | None
    config: PilotConfig
    metrics: PilotMetrics
    events_by_type: tuple[tuple[str, int], ...]
    events_by_source: tuple[tuple[str, int], ...]
    serious_in_window: int
    overdue_serious_ids: tuple[str, ...]
    criteria: tuple[CriterionResult, ...]


def checkins_from_tracker(tracker: CheckInTracker) -> tuple[CheckIn, ...]:
    """Every recorded check-in across all active instruments, in registry order (E9).

    Reads through ``tracker.history`` only — no private attributes, no SQL.
    An instrument with no check-ins raises ``ValueError`` from the tracker and
    contributes nothing.
    """
    collected: list[CheckIn] = []
    for instrument_id in INSTRUMENTS:
        try:
            collected.extend(tracker.history(instrument_id))
        except ValueError:
            continue
    return tuple(collected)


def _in_window_events(
    events: Sequence[AdverseEvent],
    start: datetime.date | None,
    end: datetime.date | None,
) -> list[AdverseEvent]:
    """Events whose detection date falls inside the window (inclusive), else none."""
    if start is None or end is None:
        return []
    return [event for event in events if start <= event.detected_at.date() <= end]


def _overdue_serious_ids(
    events: Sequence[AdverseEvent], *, now: datetime.datetime
) -> tuple[str, ...]:
    """Ids of serious events whose 48-hour follow-up is past due and uncompleted."""
    ids: list[str] = []
    for event in events:
        due = event.followup_due_at
        if event.serious and not event.followup_completed and due is not None and now > due:
            ids.append(event.id)
    return tuple(ids)


def _evaluate_criteria(
    *,
    config: PilotConfig,
    metrics: PilotMetrics,
    window_events: Sequence[AdverseEvent],
    now: datetime.datetime,
) -> tuple[CriterionResult, ...]:
    """Evaluate the four criteria with the exact E4 not-evaluable rules."""
    results: list[CriterionResult] = []
    for key, definition in DEFAULT_PROGRESSION_CRITERIA.items():
        band: str | None
        value: float | None
        value_label: str
        if key == "recruitment":
            planned = config.planned_participants
            enrolled = config.enrolled_participants
            if planned is None or enrolled is None:
                band, value = None, None
                value_label = "not evaluable — planned/enrolled counts not provided"
            else:
                value = enrolled / planned
                band = band_from_value(key, value)
                value_label = f"{enrolled} of {planned} enrolled"
        elif key == "retention":
            if metrics.retention is None:
                band, value = None, None
                value_label = "not evaluable — no check-ins recorded"
            else:
                value = metrics.retention
                band = band_from_value(key, value)
                value_label = f"{metrics.active_weeks} of {metrics.total_weeks} weeks active"
        elif key == "data_completeness":
            if metrics.data_completeness is None:
                band, value = None, None
                value_label = "not evaluable — no check-ins recorded"
            else:
                value = metrics.data_completeness
                band = band_from_value(key, value)
                value_label = (
                    f"{metrics.checkins_in_window} of {metrics.expected_checkins} "
                    "expected check-ins"
                )
        else:  # safety_event_rate: banded by pre-specified class, never by rate (E5)
            rate = metrics.adverse_events_per_week
            if rate is None:
                band, value = None, None
                value_label = "not evaluable — no check-ins or events recorded"
            else:
                value = rate
                band = safety_band(window_events, now=now)
                value_label = (
                    f"{metrics.adverse_events_in_window} event(s) in window ({rate:.2f}/week)"
                )
        results.append(
            CriterionResult(
                key=key,
                label=definition.label,
                band=band,
                value=value,
                value_label=value_label,
                basis=definition.basis,
                justification=definition.justification,
                citation=definition.citation,
            )
        )
    return tuple(results)


def build_report(
    checkins: Sequence[CheckIn],
    events: Sequence[AdverseEvent],
    *,
    config: PilotConfig | None = None,
    window_start: datetime.date | None = None,
    window_end: datetime.date | None = None,
    now: datetime.datetime | None = None,
) -> FeasibilityReport:
    """Assemble the feasibility report from check-ins and adverse events.

    Args:
        checkins: All recorded check-ins (public-API reads; see
            :func:`checkins_from_tracker`).
        events: All adverse events (e.g. ``ae_log.events()``).
        config: Pilot configuration; ``None`` uses the provisional defaults.
        window_start: Explicit window start; ``None`` resolves per E2.
        window_end: Explicit window end; ``None`` resolves per E2.
        now: Evaluation time; ``None`` means the current UTC time.

    Returns:
        The frozen :class:`FeasibilityReport` with the banner embedded verbatim.

    Raises:
        ValueError: If the resolved window start is after its end.
    """
    effective_config = config if config is not None else PilotConfig()
    generated_at = datetime.datetime.now(datetime.UTC) if now is None else now
    metrics = compute_metrics(
        checkins,
        events,
        config=effective_config,
        window_start=window_start,
        window_end=window_end,
    )
    window_events = _in_window_events(events, metrics.window_start, metrics.window_end)
    by_type = Counter(event.type for event in window_events)
    by_source = Counter(event.source for event in window_events)
    return FeasibilityReport(
        generated_at=generated_at,
        banner=NON_EFFICACY_BANNER,
        window_start=metrics.window_start,
        window_end=metrics.window_end,
        total_weeks=metrics.total_weeks,
        config=effective_config,
        metrics=metrics,
        events_by_type=tuple((t.value, by_type[t]) for t in AEType if t in by_type),
        events_by_source=tuple((s.value, by_source[s]) for s in AESource if s in by_source),
        serious_in_window=sum(1 for event in window_events if event.serious),
        overdue_serious_ids=_overdue_serious_ids(window_events, now=generated_at),
        criteria=_evaluate_criteria(
            config=effective_config,
            metrics=metrics,
            window_events=window_events,
            now=generated_at,
        ),
    )


def _cell(value: float | int | None, spec: str) -> str:
    """Render one metric cell: formatted per ``spec`` when present, ``—`` when None."""
    return f"{value:{spec}}" if value is not None else "—"


def to_markdown(report: FeasibilityReport) -> str:
    """Render ``report`` as markdown: banner, metrics, criteria, events, references.

    Band cells are the plain words ``green``/``amber``/``red`` or
    ``not evaluable`` — never emoji, never clinical framing.
    """
    metrics = report.metrics
    lines = [
        "# RE:FRAME feasibility report",
        "",
        f"> {report.banner}",
        "",
        f"- Generated: {report.generated_at.isoformat()}",
    ]
    if report.window_start is None or report.window_end is None:
        lines.append("- Window: no data recorded")
    else:
        lines.append(
            f"- Window: {report.window_start} → {report.window_end} "
            f"({report.total_weeks} ISO weeks)"
        )

    lines += [
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Check-ins in window | {metrics.checkins_in_window} |",
        f"| ISO weeks in window | {_cell(metrics.total_weeks, 'd')} |",
        f"| Retention | {_cell(metrics.retention, '.1%')} |",
        f"| Data completeness | {_cell(metrics.data_completeness, '.1%')} |",
        f"| Adverse events in window | {metrics.adverse_events_in_window} |",
        f"| Adverse events per week | {_cell(metrics.adverse_events_per_week, '.2f')} |",
        "",
        "## Progression criteria (pre-specified, provisional)",
        "",
        "| Criterion | Band | Observed | Basis |",
        "| --- | --- | --- | --- |",
    ]
    for result in report.criteria:
        band_cell = result.band if result.band is not None else "not evaluable"
        lines.append(f"| {result.label} | {band_cell} | {result.value_label} | {result.basis} |")

    lines += [
        "",
        "## Adverse events in window",
        "",
        "| Type | Count |",
        "| --- | --- |",
    ]
    for ae_type, count in report.events_by_type:
        lines.append(f"| {ae_type} | {count} |")
    breakdown = ", ".join(f"{source} {count}" for source, count in report.events_by_source)
    overdue = ", ".join(report.overdue_serious_ids) if report.overdue_serious_ids else "none"
    lines += [
        "",
        f"- Source breakdown: {breakdown or 'none'}",
        f"- Serious events: {report.serious_in_window}",
        f"- Overdue serious follow-ups: {overdue}",
        "",
        "## References",
        "",
    ]
    for citation in dict.fromkeys(result.citation for result in report.criteria):
        lines.append(f"- {citation}")
    return "\n".join(lines) + "\n"
