"""Evaluation HTTP endpoints: adverse-event monitoring over the ``/evaluation/*`` namespace.

Operational SAFETY MONITORING for the feasibility pilot — not a clinical
surface. Three routes over the injected :class:`~reframe.evaluation.log.AdverseEventLog`:

- ``GET /evaluation/adverse-events`` — every logged event in insertion order.
- ``POST /evaluation/adverse-events`` — a pilot reviewer records an event; the
  server ALWAYS stamps ``source="review"`` (D4, never trusted from the
  client), applies the pre-specified taxonomy seriousness when the body
  omits it (D2), and computes the 48-hour follow-up marker as a property of
  ``serious`` + ``detected_at`` (D3).
- ``POST /evaluation/adverse-events/{event_id}/followup`` — mark a reviewer
  follow-up completed; unknown ids are a generic 404.

The no-content rule (D1) holds above the HTTP boundary: records carry
locator ``reference`` strings only — this API never receives or returns
message content. Every record-level failure (unknown type, invalid
reference, duplicate id) maps to ONE generic 422 detail and a durable-log
failure propagates as a generic 500 through the app's unhandled-exception
handler — no internals leak either way.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from reframe.evaluation.adverse_events import AdverseEvent, AESource, AEType
from reframe.evaluation.log import AdverseEventLog

#: Generic 422 detail for any failed adverse-event record — leaks nothing.
ADVERSE_EVENT_UNRECORDED_DETAIL = "Adverse event could not be recorded."

#: Generic 404 detail for an unknown adverse-event id.
UNKNOWN_ADVERSE_EVENT_DETAIL = "unknown adverse event"


class AdverseEventOut(BaseModel):
    """One logged adverse event on the wire: metadata and locators only (D1)."""

    id: str
    type: str
    source: str
    detected_at: str
    serious: bool
    followup_due_at: str | None
    followup_completed: bool
    reference: str | None


class AdverseEventListOut(BaseModel):
    """Every logged adverse event, in insertion order."""

    adverse_events: list[AdverseEventOut]


class AdverseEventCreateIn(BaseModel):
    """Inbound reviewer record: known-shape fields only; source is NOT accepted (D4)."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    reference: str | None = None
    serious: bool | None = None


def _to_event_out(event: AdverseEvent) -> AdverseEventOut:
    """Map a frozen ``AdverseEvent`` onto the wire, computing the follow-up marker."""
    due_at = event.followup_due_at
    return AdverseEventOut(
        id=event.id,
        type=event.type.value,
        source=event.source.value,
        detected_at=event.detected_at.isoformat(),
        serious=event.serious,
        followup_due_at=due_at.isoformat() if due_at is not None else None,
        followup_completed=event.followup_completed,
        reference=event.reference,
    )


def include_evaluation_routes(app: FastAPI, ae_log: AdverseEventLog) -> None:
    """Register the adverse-event monitoring endpoints on ``app`` over ``ae_log``.

    All routes return 200 (the log is a flat safety record, not a REST
    resource tree). ``ValueError`` from type coercion, record validation,
    or a duplicate id becomes ONE generic 422 detail; an unknown follow-up
    id is a generic 404; any durable-log failure propagates untouched to
    the app's generic 500 handler (D7 — an AE-integrity failure is never
    dressed up as a validation error and never silently swallowed).
    """

    @app.get("/evaluation/adverse-events", response_model=AdverseEventListOut)
    def list_adverse_events() -> AdverseEventListOut:
        """List every logged adverse event in insertion order (metadata only)."""
        return AdverseEventListOut(
            adverse_events=[_to_event_out(event) for event in ae_log.events()]
        )

    @app.post("/evaluation/adverse-events", response_model=AdverseEventOut)
    def record_adverse_event(event_in: AdverseEventCreateIn) -> AdverseEventOut:
        """Record one reviewer-entered adverse event (source stamped ``review``).

        The body's ``serious`` (when present) overrides the pre-specified
        taxonomy default (D2); ``reference`` must be a locator, never
        message content (D1). Failures map to a generic 422; nothing about
        the record's internals reaches the wire.
        """
        try:
            event = AdverseEvent.create(
                AEType(event_in.type),
                source=AESource.REVIEW,
                reference=event_in.reference,
                serious=event_in.serious,
            )
            ae_log.append(event)
        except ValueError:
            raise HTTPException(status_code=422, detail=ADVERSE_EVENT_UNRECORDED_DETAIL) from None
        return _to_event_out(event)

    @app.post("/evaluation/adverse-events/{event_id}/followup", response_model=AdverseEventOut)
    def complete_adverse_event_followup(event_id: str) -> AdverseEventOut:
        """Mark an adverse event's follow-up completed (the 48-hour marker, D3).

        Body-free by design: the call itself records that a reviewer
        addressed the event. Unknown ids are a generic 404 — a follow-up
        against an unlogged id is a loud failure, never a silent no-op.
        """
        if ae_log.get(event_id) is None:
            raise HTTPException(status_code=404, detail=UNKNOWN_ADVERSE_EVENT_DETAIL)
        return _to_event_out(ae_log.complete_followup(event_id))
