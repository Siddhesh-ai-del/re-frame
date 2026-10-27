"""Tests for ``reframe.evaluation.report`` — feasibility-report assembly and markdown.

Strict TDD: written BEFORE ``reframe/evaluation/report.py`` exists; the first
run must fail with ``ModuleNotFoundError`` (RED).

The report is an OPERATIONAL feasibility surface (E1): it carries
``NON_EFFICACY_BANNER`` verbatim, reads through public APIs only (E9 —
``tracker.history`` per active instrument, ``ae_log.events()``), and its bands
are operational review statuses — never clinical findings, never efficacy
claims. Not-evaluable rules follow the E4 table exactly; by-type/by-source
counts follow enum declaration order over observed values only; only event IDs
and counts appear — never message content (D1).
"""

import datetime
from dataclasses import FrozenInstanceError

import pytest

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.evaluation.pilot import PilotConfig
from reframe.evaluation.progression import DEFAULT_PROGRESSION_CRITERIA
from reframe.evaluation.report import (
    NON_EFFICACY_BANNER,
    CriterionResult,
    FeasibilityReport,
    build_report,
    checkins_from_tracker,
    to_markdown,
)
from reframe.measurement.tracker import CheckInTracker

UTC = datetime.UTC
NOW = datetime.datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
DAY_ONE = datetime.date(2026, 10, 1)

#: The banner exactly as specified for stage 7b (E1) — pinned verbatim.
EXPECTED_BANNER = (
    "Feasibility report — operational feasibility parameters only. This "
    "evaluation was not designed or powered to support any efficacy claim; "
    "scores, rates, and counts here are descriptive operational data, not "
    "clinical findings. No diagnostic or treatment claims are made."
)


def _at(date: datetime.date) -> datetime.datetime:
    return datetime.datetime(date.year, date.month, date.day, 9, 0, tzinfo=UTC)


def _event(
    ae_type: AEType,
    *,
    detected_at: datetime.datetime,
    source: AESource = AESource.REVIEW,
    serious: bool | None = None,
) -> AdverseEvent:
    return AdverseEvent.create(
        ae_type,
        source=source,
        serious=serious,
        detected_at=detected_at,
    )


# ---------------------------------------------------------------------------
# checkins_from_tracker (E9): every active instrument, public API only
# ---------------------------------------------------------------------------


def test_checkins_from_tracker_pulls_every_active_instrument() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", [0] * 9, DAY_ONE)
    tracker.record("gad7", [0] * 7, DAY_ONE)
    tracker.record("k10", [3] * 10, DAY_ONE)
    tracker.record("scs_sf", [3] * 12, DAY_ONE)

    checkins = checkins_from_tracker(tracker)

    assert [checkin.instrument_id for checkin in checkins] == [
        "phq9",
        "gad7",
        "k10",
        "scs_sf",
    ]
    assert all(checkin.date == DAY_ONE for checkin in checkins)


def test_checkins_from_tracker_returns_all_entries_per_instrument() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", [0] * 9, DAY_ONE)
    tracker.record("phq9", [1] * 9, datetime.date(2026, 10, 8))
    tracker.record("phq9", [0] * 9, datetime.date(2026, 10, 15))

    checkins = checkins_from_tracker(tracker)

    assert len(checkins) == 3
    assert [checkin.date for checkin in checkins] == [
        DAY_ONE,
        datetime.date(2026, 10, 8),
        datetime.date(2026, 10, 15),
    ]


def test_checkins_from_tracker_on_an_empty_tracker_is_empty() -> None:
    assert checkins_from_tracker(CheckInTracker()) == ()


# ---------------------------------------------------------------------------
# build_report on empty inputs: E4 not-evaluable table, banner, injected now
# ---------------------------------------------------------------------------


def test_empty_report_follows_the_e4_not_evaluable_table() -> None:
    report = build_report((), (), now=NOW)

    assert isinstance(report, FeasibilityReport)
    assert report.generated_at == NOW
    assert report.banner == EXPECTED_BANNER
    assert report.banner == NON_EFFICACY_BANNER
    assert report.window_start is None
    assert report.window_end is None
    assert report.total_weeks is None
    assert report.metrics.retention is None
    assert report.metrics.data_completeness is None
    assert report.metrics.adverse_events_per_week is None
    assert report.events_by_type == ()
    assert report.events_by_source == ()
    assert report.serious_in_window == 0
    assert report.overdue_serious_ids == ()

    assert [criterion.key for criterion in report.criteria] == [
        "recruitment",
        "retention",
        "data_completeness",
        "safety_event_rate",
    ]
    for criterion in report.criteria:
        assert criterion.band is None
        assert criterion.value is None
        assert "not evaluable" in criterion.value_label

    by_key = {criterion.key: criterion for criterion in report.criteria}
    assert (
        by_key["recruitment"].value_label == "not evaluable — planned/enrolled counts not provided"
    )
    assert by_key["retention"].value_label == "not evaluable — no check-ins recorded"
    assert by_key["data_completeness"].value_label == "not evaluable — no check-ins recorded"
    assert (
        by_key["safety_event_rate"].value_label == "not evaluable — no check-ins or events recorded"
    )


def test_report_defaults_to_a_real_utc_timestamp_when_now_is_not_injected() -> None:
    report = build_report((), ())
    assert report.generated_at.tzinfo is not None
    before = datetime.datetime.now(UTC)
    assert report.generated_at <= before + datetime.timedelta(seconds=5)


def test_report_is_frozen() -> None:
    report = build_report((), (), now=NOW)
    with pytest.raises(FrozenInstanceError):
        report.banner = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Full scenario: every metric, band, ordering, and overdue id pinned
# ---------------------------------------------------------------------------


def _full_scenario() -> FeasibilityReport:
    tracker = CheckInTracker()
    for date in (
        DAY_ONE,
        datetime.date(2026, 10, 2),
        datetime.date(2026, 10, 7),
        datetime.date(2026, 10, 13),
    ):
        tracker.record("phq9", [0] * 9, date)
    overdue_serious = _event(
        AEType.HALLUCINATED_CLINICAL_CLAIM,
        detected_at=datetime.datetime(2026, 10, 10, 8, 0, tzinfo=UTC),
        serious=True,
    )
    events = (
        _event(
            AEType.TRANSIENT_EARLY_WORSENSING,
            detected_at=_at(datetime.date(2026, 10, 7)),
            source=AESource.AUTOMATIC,
        ),
        _event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(datetime.date(2026, 10, 8))),
        overdue_serious,
    )
    return build_report(
        tracker.history("phq9"),
        events,
        config=PilotConfig(planned_participants=40, enrolled_participants=40),
        now=NOW,
    )


def test_full_scenario_pins_every_metric() -> None:
    report = _full_scenario()

    assert report.window_start == DAY_ONE
    assert report.window_end == datetime.date(2026, 10, 13)
    assert report.total_weeks == 3
    metrics = report.metrics
    assert metrics.checkins_in_window == 4
    assert metrics.active_weeks == 3
    assert metrics.retention == 1.0
    assert metrics.expected_checkins == 3
    assert metrics.data_completeness == pytest.approx(4 / 3)
    assert metrics.adverse_events_in_window == 3
    assert metrics.adverse_events_per_week == 1.0


def test_full_scenario_pins_the_event_rollups_in_enum_order() -> None:
    report = _full_scenario()

    assert report.events_by_type == (
        ("hallucinated_clinical_claim", 1),
        ("sycophancy_episode", 1),
        ("transient_early_worsening", 1),
    )
    assert report.events_by_source == (("automatic", 1), ("review", 2))
    assert report.serious_in_window == 1
    assert len(report.overdue_serious_ids) == 1
    assert report.overdue_serious_ids[0]


def test_full_scenario_pins_every_criterion_band_and_label() -> None:
    report = _full_scenario()
    by_key = {criterion.key: criterion for criterion in report.criteria}

    recruitment = by_key["recruitment"]
    assert recruitment.band == "green"
    assert recruitment.value == 1.0
    assert recruitment.value_label == "40 of 40 enrolled"

    retention = by_key["retention"]
    assert retention.band == "green"
    assert retention.value == 1.0
    assert retention.value_label == "3 of 3 weeks active"

    completeness = by_key["data_completeness"]
    assert completeness.band == "green"
    assert completeness.value == pytest.approx(4 / 3)
    assert completeness.value_label == "4 of 3 expected check-ins"

    safety = by_key["safety_event_rate"]
    assert safety.band == "red"  # overdue 48-hour serious follow-up (E5 rule 2)
    assert safety.value == 1.0
    assert safety.value_label == "3 event(s) in window (1.00/week)"

    for criterion in report.criteria:
        assert criterion.basis == DEFAULT_PROGRESSION_CRITERIA[criterion.key].basis
        assert criterion.justification == DEFAULT_PROGRESSION_CRITERIA[criterion.key].justification
        assert criterion.citation == DEFAULT_PROGRESSION_CRITERIA[criterion.key].citation


def test_a_content_event_without_overdue_serious_bands_amber() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", [0] * 9, DAY_ONE)
    report = build_report(
        tracker.history("phq9"),
        (_event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(DAY_ONE)),),
        now=NOW,
    )
    safety = {c.key: c for c in report.criteria}["safety_event_rate"]
    assert safety.band == "amber"


# ---------------------------------------------------------------------------
# Explicit window trimming
# ---------------------------------------------------------------------------


def test_explicit_window_trims_both_checkins_and_events() -> None:
    tracker = CheckInTracker()
    tracker.record("phq9", [0] * 9, DAY_ONE)
    tracker.record("phq9", [0] * 9, datetime.date(2026, 10, 20))
    events = (
        _event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(datetime.date(2026, 10, 3))),
        _event(AEType.SYCOPHANCY_EPISODE, detected_at=_at(datetime.date(2026, 10, 19))),
    )

    report = build_report(
        tracker.history("phq9"),
        events,
        window_start=DAY_ONE,
        window_end=datetime.date(2026, 10, 10),
        now=NOW,
    )

    assert report.window_start == DAY_ONE
    assert report.window_end == datetime.date(2026, 10, 10)
    assert report.total_weeks == 2
    assert report.metrics.checkins_in_window == 1
    assert report.metrics.adverse_events_in_window == 1
    assert report.serious_in_window == 0
    assert report.events_by_type == (("sycophancy_episode", 1),)


def test_build_report_rejects_start_after_end() -> None:
    with pytest.raises(ValueError):
        build_report(
            (),
            (),
            window_start=datetime.date(2026, 10, 12),
            window_end=datetime.date(2026, 10, 5),
            now=NOW,
        )


# ---------------------------------------------------------------------------
# to_markdown: banner verbatim, pinned headers, empty state, references, bands
# ---------------------------------------------------------------------------


def test_markdown_embeds_the_banner_verbatim() -> None:
    markdown = to_markdown(build_report((), (), now=NOW))
    assert f"> {EXPECTED_BANNER}" in markdown


def test_markdown_carries_every_pinned_section_header() -> None:
    markdown = to_markdown(build_report((), (), now=NOW))
    assert markdown.startswith("# RE:FRAME feasibility report\n")
    assert "## Metrics" in markdown
    assert "## Progression criteria (pre-specified, provisional)" in markdown
    assert "## Adverse events in window" in markdown
    assert "## References" in markdown
    assert "- Generated: 2026-10-26T12:00:00+00:00" in markdown


def test_markdown_empty_state_shows_no_data_and_not_evaluable() -> None:
    markdown = to_markdown(build_report((), (), now=NOW))
    assert "- Window: no data recorded" in markdown
    assert "not evaluable" in markdown
    assert "planned/enrolled counts not provided" in markdown
    assert "- Overdue serious follow-ups: none" in markdown
    assert "- Serious events: 0" in markdown


def test_markdown_references_list_every_verified_citation_once() -> None:
    markdown = to_markdown(_full_scenario())
    references = markdown.split("## References", 1)[1]
    assert "DOI 10.1038/s41746-024-01388-y" in references  # Linardon et al. 2024
    assert "DOI 10.1186/s40814-025-01675-9" in references
    assert "DOI 10.1111/acps.13225" in references
    assert "PMID 39695173" in references
    for criterion in DEFAULT_PROGRESSION_CRITERIA.values():
        assert references.count(f"- {criterion.citation}") == 1


def test_markdown_renders_bands_as_plain_words_and_pins_the_scenario_tables() -> None:
    markdown = to_markdown(_full_scenario())

    assert "🟢" not in markdown
    assert "🟡" not in markdown
    assert "🔴" not in markdown
    assert "| red |" in markdown
    assert "3 of 3 weeks active" in markdown
    "| Check-ins in window | 4 |".startswith("| ")  # row shape sanity
    assert "| Check-ins in window | 4 |" in markdown
    assert "| Retention | 100.0% |" in markdown
    assert "| Data completeness | 133.3% |" in markdown
    assert "| Adverse events per week | 1.00 |" in markdown
    assert "| ISO weeks in window | 3 |" in markdown
    assert "| halluclawed" not in markdown
    assert "| hallucinated_clinical_claim | 1 |" in markdown
    assert "Source breakdown: automatic 1, review 2" in markdown
    assert markdown.count("audit-miss sha256") == 0  # no audit locators invented here


def test_markdown_window_line_reports_the_iso_week_span() -> None:
    markdown = to_markdown(_full_scenario())
    assert "- Window: 2026-10-01 → 2026-10-13 (3 ISO weeks)" in markdown


def test_criterion_result_is_a_frozen_record() -> None:
    criterion = build_report((), (), now=NOW).criteria[0]
    assert isinstance(criterion, CriterionResult)
    with pytest.raises(FrozenInstanceError):
        criterion.band = "green"  # type: ignore[misc]
