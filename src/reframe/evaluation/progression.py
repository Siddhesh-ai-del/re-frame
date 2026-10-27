"""Pre-specified progression criteria and banding for the feasibility pilot (7b).

Four criteria in the research report's order — recruitment, retention, data
completeness, safety-event status — each with the exact green/amber/red texts,
a justification, and a VERIFIED citation (locked in stage 7b; never re-derive
or shorten them). Thresholds are provisional RE:FRAME design defaults pending
pilot validation (E6).

Bands are OPERATIONAL REVIEW STATUSES — never safety or efficacy judgments.
Safety banding (E5) is CLASS-based over pre-specified adverse-event types and
the 48-hour serious follow-up timeline, first match wins — never a comparison
of the observed rate to published participant-level base rates, which are
indicative context only and not convertible to instance-level event rates.
"""

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from reframe.evaluation.adverse_events import AdverseEvent, AEType

#: Escalation-pathway failure classes (E5 rule 1): any occurrence is red.
_FAILURE_TYPES: frozenset[AEType] = frozenset(
    {AEType.CRISIS_RESPONSE_FAILURE, AEType.INAPPROPRIATE_OR_DELAYED_ESCALATION}
)

#: Content-defect classes (E5 rule 3): any occurrence (or any serious event) is amber.
_CONTENT_TYPES: frozenset[AEType] = frozenset(
    {
        AEType.HALLUCINATED_CLINICAL_CLAIM,
        AEType.BOUNDARY_VIOLATION_DIAGNOSIS,
        AEType.SYCOPHANCY_EPISODE,
    }
)

#: green_min, amber_min per key; boundaries are inclusive (E6). Keys without
#: numeric thresholds (``safety_event_rate``) are absent — they band by class.
_THRESHOLDS: Mapping[str, tuple[float, float]] = MappingProxyType(
    {
        "recruitment": (1.00, 0.75),
        "retention": (0.70, 0.50),
        "data_completeness": (0.80, 0.60),
    }
)


@dataclass(frozen=True)
class ProgressionCriterion:
    """One pre-specified progression criterion: bands, rationale, citation."""

    key: str
    label: str
    green: str
    amber: str
    red: str
    justification: str
    citation: str

    @property
    def basis(self) -> str:
        """All three bands rendered as one operational reference string."""
        return f"green: {self.green}; amber: {self.amber}; red: {self.red}"


_DEFAULTS: tuple[ProgressionCriterion, ...] = (
    ProgressionCriterion(
        key="recruitment",
        label="Recruitment (protocol-level input)",
        green=">= 100% of planned participants enrolled",
        amber=">= 75% of planned",
        red="< 75% of planned",
        justification=(
            "Pre-specified progression criterion for feasibility recruitment; "
            "planning anchors on a >= 12-per-arm floor. Flat rules of thumb are "
            "known not to satisfy every pilot objective, so the target must be "
            "justified against this pilot's population. Evaluable only when the "
            "operator supplies planned and enrolled counts — protocol-level data "
            "not derivable from a single local instance."
        ),
        citation=(
            "Determining sample size for pilot trials: a tutorial (progression "
            "criteria: recruitment); Julious 2005, DOI 10.1002/pst.185 (12/arm "
            "floor); Sample size justification in feasibility studies, Pilot and "
            "Feasibility Studies 2025, DOI 10.1186/s40814-025-01675-9."
        ),
    ),
    ProgressionCriterion(
        key="retention",
        label="Retention (engagement across the window)",
        green=">= 70% of window weeks active (>= 1 check-in)",
        amber=">= 50%",
        red="< 50%",
        justification=(
            "Provisional RE:FRAME design thresholds set inside the published "
            "range: protocolized iCBT retains ~84% (derived from 16.3% dropout), "
            "while a polished commercial chatbot retains 42.66% at week 4 among "
            "paying subscribers — different product and pricing models, not "
            "directly comparable. Provisional pending pilot validation."
        ),
        citation=(
            "Linardon et al. 2026 (derived ~84% retention, protocolized iCBT); "
            "Youper week-4 retention 42.66% (commercial chatbot, paying "
            "subscribers); flat rule-of-thumb caveat: DOI 10.1186/s40814-025-01675-9."
        ),
    ),
    ProgressionCriterion(
        key="data_completeness",
        label="Check-in data completeness",
        green=">= 80% of expected check-ins recorded",
        amber=">= 60%",
        red="< 60%",
        justification=(
            "Data completeness is a pre-specified feasibility progression "
            "dimension. Expected cadence defaults to 1 check-in per week — a "
            "provisional RE:FRAME design assumption, operator-overridable."
        ),
        citation=(
            "Determining sample size for pilot trials: a tutorial "
            "(progression criteria: data completeness)."
        ),
    ),
    ProgressionCriterion(
        key="safety_event_rate",
        label="Safety events (pre-specified class review)",
        green=(
            "no escalation-pathway failures, no overdue serious follow-ups, "
            "only expected monitoring-signal events (or none)"
        ),
        amber="content-class events logged, or any serious event (all serious follow-ups on time)",
        red=(
            "any crisis-response failure or inappropriate/delayed escalation, or "
            "any serious follow-up overdue past 48 hours"
        ),
        justification=(
            "The band is determined by the pre-specified AE classes and the "
            "48-hour serious follow-up timeline (E5) — NOT by comparing the "
            "observed rate to published base rates: participant-level base rates "
            "(6.7% deterioration; 8.3% mindfulness adverse events) are indicative "
            "context only and not convertible to instance-level event rates. "
            "'Green' is an operational review status, not a safety or efficacy judgment."
        ),
        citation=(
            "NIA/NIH DSMP template (48-hour serious unexpected-event reporting); "
            "Linardon et al. 2024, npj Digital Medicine, DOI "
            "10.1038/s41746-024-01388-y, PMID 39695173 (6.7%, 95% CI 4.3-10.1); "
            "Farias et al. 2020, Acta Psychiatr Scand, DOI 10.1111/acps.13225, "
            "PMID 32820538 (8.3%, 95% CI 0.05-0.12)."
        ),
    ),
)

#: The four criteria in research-report order; read-only mapping keyed by ``.key``.
DEFAULT_PROGRESSION_CRITERIA: Mapping[str, ProgressionCriterion] = MappingProxyType(
    {criterion.key: criterion for criterion in _DEFAULTS}
)


def band_from_value(key: str, value: float) -> str:
    """Band a threshold-backed observed value: >= green_min green, >= amber_min amber.

    Args:
        key: Criterion key; keys without numeric thresholds raise.
        value: The observed ratio (0..1+).

    Returns:
        ``"green"``, ``"amber"``, or ``"red"`` (boundaries inclusive, E6).

    Raises:
        ValueError: If ``key`` has no pre-specified numeric thresholds — the
        safety criterion bands by class (see :func:`safety_band`), never by rate.
    """
    try:
        green_min, amber_min = _THRESHOLDS[key]
    except KeyError:
        raise ValueError(f"no numeric thresholds for criterion {key!r}") from None
    if value >= green_min:
        return "green"
    if value >= amber_min:
        return "amber"
    return "red"


def _is_overdue_serious(event: AdverseEvent, now: datetime.datetime) -> bool:
    """True iff ``event`` is serious, its 48-hour follow-up is uncompleted and past due."""
    due = event.followup_due_at
    return event.serious and not event.followup_completed and due is not None and now > due


def safety_band(events: Sequence[AdverseEvent], *, now: datetime.datetime) -> str:
    """Band in-window events by pre-specified class, first match wins (E5).

    Args:
        events: The in-window adverse events (order irrelevant across passes —
            each pass runs over ALL events before the next rule).
        now: The evaluation time for the 48-hour serious follow-up check.

    Returns:
        ``"red"`` / ``"amber"`` / ``"green"`` — an OPERATIONAL review status,
        never a safety or efficacy judgment.
    """
    if any(event.type in _FAILURE_TYPES for event in events):
        return "red"
    if any(_is_overdue_serious(event, now) for event in events):
        return "red"
    if any(event.type in _CONTENT_TYPES or event.serious for event in events):
        return "amber"
    return "green"
