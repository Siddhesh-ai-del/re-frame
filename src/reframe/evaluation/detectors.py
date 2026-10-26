"""Pure adverse-event detectors: the automatic check-in signal and the audit converter (D5).

Scope is deliberately small and honest. Exactly ONE in-product field signal
is auto-detected today: a recorded check-in carrying
:class:`~reframe.measurement.flags.CheckInFlag.EARLY_WORSENSING` becomes a
``transient_early_worsening`` event (:func:`early_worsening_event`, source
``automatic``). :func:`audit_miss_events` converts seeded-corpus
:class:`~reframe.safety.audit.AuditReport` misses into
``crisis_response_failure`` events (source ``audit``) — a near-miss
detected before any participant impact; it is pure here and is invoked by
the stage-7b CLI.

Honesty framing: the event types are RE:FRAME pre-specified DESIGN
definitions (see :mod:`reframe.evaluation.adverse_events`), not validated
published ones. The deterministic safety layer is NOT instrumented here
and must never be modified for AE logging — a crisis turn that escalates
correctly is the product WORKING, never an adverse event. Both reference
locators are content-free by construction (D1): a score locator and a
truncated sha256 digest, never the text of a turn or a response vector.
"""

import datetime
import hashlib

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.measurement.flags import CheckInFlag
from reframe.measurement.tracker import CheckIn
from reframe.safety.audit import AuditReport

#: Number of hex characters kept from the sha256 miss digest (collision-safe
#: for a small seeded corpus while staying a bare locator).
_AUDIT_DIGEST_CHARS: int = 12


def early_worsening_event(
    checkin: CheckIn,
    *,
    detected_at: datetime.datetime | None = None,
) -> AdverseEvent | None:
    """Convert a recorded check-in into an AE iff it carries EARLY_WORSENSING.

    Args:
        checkin: The just-recorded check-in, flags as stored (verbatim).
        detected_at: Optional tz-aware detection time; ``None`` means now (UTC).

    Returns:
        A ``transient_early_worsening`` event (source ``automatic``) whose
        reference is the D1 score locator (instrument id, date, total) — never
        the response vector — or ``None`` when the flag is absent.
    """
    if CheckInFlag.EARLY_WORSENSING not in checkin.flags:
        return None
    reference = f"check-in {checkin.instrument_id} {checkin.date.isoformat()} total={checkin.total}"
    return AdverseEvent.create(
        AEType.TRANSIENT_EARLY_WORSENSING,
        source=AESource.AUTOMATIC,
        reference=reference,
        detected_at=detected_at,
    )


def audit_miss_events(
    report: AuditReport,
    *,
    detected_at: datetime.datetime | None = None,
) -> tuple[AdverseEvent, ...]:
    """Convert every seeded-corpus audit miss into a crisis-failure event.

    Args:
        report: The audit run's outcome; each entry in ``report.misses`` is one
            crisis-class text the classifier failed to flag.
        detected_at: Optional tz-aware detection time; ``None`` means now (UTC),
            applied to every produced event.

    Returns:
        One ``crisis_response_failure`` event (source ``audit``) per miss, in
        report order. Each reference is a content-free deterministic locator:
        the sha256 digest of the missed text, truncated (D1).
    """
    events: list[AdverseEvent] = []
    for text in report.misses:
        digest = hashlib.sha256(text.encode()).hexdigest()[:_AUDIT_DIGEST_CHARS]
        events.append(
            AdverseEvent.create(
                AEType.CRISIS_RESPONSE_FAILURE,
                source=AESource.AUDIT,
                reference=f"audit-miss sha256:{digest}",
                detected_at=detected_at,
            )
        )
    return tuple(events)
