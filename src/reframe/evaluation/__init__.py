"""Evaluation harness layer: pre-specified adverse-event taxonomy and logging.

Safety-monitoring instrumentation for the feasibility pilot (stage 7a). The
six AE types are RE:FRAME *pre-specified design definitions* — the GenAI
intervention literature contains NO validated published adverse-event
definitions (Olisaeloka et al. 2026, *Healthcare*, DOI
10.3390/healthcare14101395); the AI-specific direction (AE definitions,
human escalation pathways) follows the US FDA Digital Health Advisory
Committee (6 Nov 2025), and the early-worsening monitoring signal follows
NICE NG222 rec. 1.2.10.

Public surface: the taxonomy (:data:`AE_DEFINITIONS`, :class:`AEDefinition`,
:class:`AEType`, :class:`AESource`), the record (:class:`AdverseEvent`,
:data:`SERIOUS_FOLLOWUP_HOURS`), the logs (:class:`AdverseEventLog`,
:class:`PersistentAdverseEventLog` over :class:`AdverseEventStore` /
:class:`SqliteAdverseEventStore`), and the pure detectors
(:func:`early_worsening_event`, :func:`audit_miss_events`).

AE records are SAFETY MONITORING RECORDS, independent of the journal purge
(design decision D6): ``DELETE /checkins`` removes check-in rows only and
never touches adverse-event records — purging journal data cannot silently
destroy safety records. Records carry locator references only, never
message or response content (D1). See ``docs/evaluation-harness.md``.
"""

from reframe.evaluation.adverse_events import (
    AE_DEFINITIONS,
    SERIOUS_FOLLOWUP_HOURS,
    AdverseEvent,
    AEDefinition,
    AESource,
    AEType,
)
from reframe.evaluation.detectors import audit_miss_events, early_worsening_event
from reframe.evaluation.log import AdverseEventLog, PersistentAdverseEventLog
from reframe.evaluation.store import AdverseEventStore, SqliteAdverseEventStore

__all__ = [
    "AE_DEFINITIONS",
    "SERIOUS_FOLLOWUP_HOURS",
    "AEDefinition",
    "AEType",
    "AESource",
    "AdverseEvent",
    "AdverseEventLog",
    "AdverseEventStore",
    "PersistentAdverseEventLog",
    "SqliteAdverseEventStore",
    "audit_miss_events",
    "early_worsening_event",
]
