"""Tests for ``reframe.evaluation.detectors`` — the pure AE detectors (D5).

Strict TDD: written BEFORE ``reframe/evaluation/`` exists; the first run must
fail with ``ModuleNotFoundError`` (RED).

Exactly one field signal is auto-detected today: a recorded check-in carrying
``CheckInFlag.EARLY_WORSENSING`` becomes a ``transient_early_worsening`` event
(source ``automatic``). The audit converter turns seeded-corpus
``AuditReport.misses`` into ``crisis_response_failure`` events (source
``audit``) — pure and invoked later by the stage-7b CLI. Both reference
locators are content-free (D1): score locators and sha256 digests, never the
text of a turn or a response vector.
"""

import datetime
import hashlib

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.evaluation.detectors import audit_miss_events, early_worsening_event
from reframe.measurement.flags import CheckInFlag
from reframe.measurement.tracker import CheckIn
from reframe.safety.audit import AuditReport

UTC = datetime.UTC
NOW = datetime.datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
DAY_ONE = datetime.date(2026, 10, 1)


def _checkin(*, flags: tuple[CheckInFlag, ...] = (), total: int = 0) -> CheckIn:
    return CheckIn("phq9", DAY_ONE, (0,) * 9, total, None, flags)


def _report(*misses: str) -> AuditReport:
    return AuditReport(
        total=4,
        crisis_total=len(misses),
        flagged_crisis=0,
        misses=tuple(misses),
        recall=0.0,
        neutral_high_risk=0,
        review_count=0,
    )


# ---------------------------------------------------------------------------
# early_worsening_event — the one automatic in-product signal
# ---------------------------------------------------------------------------


def test_checkin_without_the_flag_yields_no_event() -> None:
    assert early_worsening_event(_checkin()) is None


def test_escalate_only_checkin_still_yields_no_event() -> None:
    # D5: exactly ONE field signal today — item-9 escalation is not itself an AE.
    flagged = _checkin(flags=(CheckInFlag.ESCALATE,), total=27)
    assert early_worsening_event(flagged) is None


def test_flagged_checkin_becomes_an_automatic_transient_early_worsening_event() -> None:
    flagged = _checkin(flags=(CheckInFlag.EARLY_WORSENSING,), total=16)

    event = early_worsening_event(flagged)

    assert event is not None
    assert event.type is AEType.TRANSIENT_EARLY_WORSENSING
    assert event.source is AESource.AUTOMATIC
    # D1: a score locator (instrument + date + total), never response content.
    assert event.reference == "check-in phq9 2026-10-01 total=16"


def test_explicit_detected_at_is_honored() -> None:
    flagged = _checkin(flags=(CheckInFlag.EARLY_WORSENSING,), total=16)

    event = early_worsening_event(flagged, detected_at=NOW)

    assert event is not None
    assert event.detected_at == NOW


# ---------------------------------------------------------------------------
# audit_miss_events — seeded-corpus near-misses, before any participant impact
# ---------------------------------------------------------------------------


def test_an_audit_with_no_misses_yields_no_events() -> None:
    assert audit_miss_events(_report()) == ()


def test_each_miss_becomes_one_ordered_crisis_response_failure_event() -> None:
    misses = ("a crisis sentence nobody flagged", "another missed crisis sentence")

    events = audit_miss_events(_report(*misses))

    assert len(events) == 2
    assert [event.type for event in events] == [
        AEType.CRISIS_RESPONSE_FAILURE,
        AEType.CRISIS_RESPONSE_FAILURE,
    ]
    assert all(event.source is AESource.AUDIT for event in events)


def test_audit_references_are_deterministic_content_free_sha256_locators() -> None:
    miss = "I want to end my life tonight"

    events = audit_miss_events(_report(miss))

    digest = hashlib.sha256(miss.encode()).hexdigest()[:12]
    assert events[0].reference == f"audit-miss sha256:{digest}"
    assert miss not in (events[0].reference or "")


def test_audit_explicit_detected_at_is_honored_on_every_event() -> None:
    events = audit_miss_events(_report("miss one", "miss two"), detected_at=NOW)

    assert [event.detected_at for event in events] == [NOW, NOW]


def test_audit_references_carry_the_full_order_of_misses() -> None:
    events = audit_miss_events(_report("first", "second", "third"))

    expected = tuple(
        f"audit-miss sha256:{hashlib.sha256(text.encode()).hexdigest()[:12]}"
        for text in ("first", "second", "third")
    )
    assert tuple(event.reference for event in events) == expected


def test_detected_events_are_immutably_constructed_records() -> None:
    # Sanity: the detectors produce full AdverseEvent records, not partial dicts.
    event = early_worsening_event(_checkin(flags=(CheckInFlag.EARLY_WORSENSING,), total=16))
    assert isinstance(event, AdverseEvent)
    assert event.serious is False
    assert event.followup_due_at is None
