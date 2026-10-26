"""Measurement HTTP endpoints: the instrument catalog and longitudinal check-ins.

This module registers three routes on an existing FastAPI app via
:func:`include_measurement_routes` — the chat service in
:mod:`reframe.api.app` is untouched, and the same tracker instance the
conversation owns is injected as the single source of check-in state.

The contract keeps the measurement safety semantics intact above the HTTP
boundary:

- ``GET /instruments`` exposes the full, active-only catalog (item wording,
  scale, bands, citation) so a UI can render forms; pending or unknown
  instruments are unreachable.
- ``POST /checkins`` records one check-in and returns its flags PLUS the
  routing decision (action, message id, message text) so the client can
  escalate. Escalation is driven by item 9 / pre-specified flags, never by
  a summed total presented as a risk level (NICE NG225). The ESCALATE route
  reuses the pipeline's scripted crisis copy verbatim; the human-review
  route returns the wellness-framed concern text.
- ``GET /checkins/{instrument_id}`` replays history with routing recomputed
  per entry; unknown instrument ids are 404, a valid instrument with no
  check-ins is an empty 200 list.
- ``DELETE /checkins`` purges every recorded check-in (all instruments) and
  returns the number removed; it takes no path parameter, so no
  instrument-id validation applies — the GET history contract above is
  untouched. The purge touches check-in rows only: adverse-event records
  are safety monitoring records and survive independently (D6, see
  ``docs/evaluation-harness.md`` and :mod:`reframe.evaluation`).
- Optional stage-7a wiring (D5): when an ``ae_log`` is provided, a
  recorded check-in carrying the EARLY_WORSENSING flag appends one
  ``transient_early_worsening`` event to it — outside the ``ValueError``
  handler, because an AE-integrity failure is a 500, never a 422 (D7).

Every record-level failure (unknown instrument, bad responses, out-of-order
date) maps to one generic 422 detail — no internals, no repr of input.
"""

import datetime
import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from reframe.evaluation.detectors import early_worsening_event
from reframe.evaluation.log import AdverseEventLog
from reframe.measurement.instruments import INSTRUMENTS, InstrumentSpec, get_instrument
from reframe.measurement.routing import (
    CHECKIN_CONCERN_MESSAGE_ID,
    CHECKIN_CONCERN_TEXT,
    CHECKIN_CRISIS_MESSAGE_ID,
    route_for_checkin,
)
from reframe.measurement.tracker import CheckIn, CheckInTracker
from reframe.pipeline.messages import CRISIS_RESPONSE

#: Generic 422 detail for any failed check-in — leaks nothing about the cause.
CHECKIN_UNRECORDED_DETAIL = "Check-in could not be recorded."

#: 404 detail for an unknown (or pending) instrument id.
UNKNOWN_INSTRUMENT_DETAIL = "unknown instrument"

#: Routing message id -> the exact human-readable text to return on the wire.
_ROUTING_MESSAGE_TEXT: dict[str, str] = {
    CHECKIN_CRISIS_MESSAGE_ID: CRISIS_RESPONSE.text,
    CHECKIN_CONCERN_MESSAGE_ID: CHECKIN_CONCERN_TEXT,
}

_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


class InstrumentItemOut(BaseModel):
    """One instrument item as a UI needs it: 1-based index and prompt."""

    index: int
    prompt: str


class AnswerOptionOut(BaseModel):
    """One labelled answer option on the instrument's scale."""

    value: int
    label: str


class SeverityBandOut(BaseModel):
    """One inclusive total range mapped to a severity-band label."""

    label: str
    lower: int
    upper: int


class InstrumentOut(BaseModel):
    """Full instrument specification on the wire, enough to render a form."""

    id: str
    title: str
    recall_period: str
    scale_min: int
    scale_max: int
    total_min: int
    total_max: int
    items: list[InstrumentItemOut]
    answer_options: list[AnswerOptionOut]
    severity_bands: list[SeverityBandOut]
    citation: str


class InstrumentListOut(BaseModel):
    """Every active instrument, in registry order."""

    instruments: list[InstrumentOut]


class CheckInRequest(BaseModel):
    """Inbound check-in body: known-shape fields only, strict ISO date."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: str = Field(min_length=1)
    responses: list[int] = Field(min_length=1)
    date: str

    @field_validator("date")
    @classmethod
    def _date_must_be_a_strict_iso_calendar_date(cls, value: str) -> str:
        """Reject non-``YYYY-MM-DD`` formats and impossible calendar dates."""
        if not _ISO_DATE_PATTERN.fullmatch(value):
            raise ValueError("date must be an ISO calendar date (YYYY-MM-DD)")
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise ValueError("date must be an existing calendar date (YYYY-MM-DD)") from None
        return value


class CheckInOut(BaseModel):
    """One recorded check-in: raw data, score, flags, and its routing decision.

    ``action``/``message_id``/``message`` come from the pre-specified routing
    table applied to this check-in's flags — the client escalates on these,
    never on ``total`` alone. ``message`` is ``None`` exactly when the route
    is ``proceed``.
    """

    instrument_id: str
    date: str
    responses: list[int]
    total: int
    severity_label: str | None
    flags: list[str]
    action: str
    message_id: str | None
    message: str | None


class CheckInListOut(BaseModel):
    """Chronological check-in history for one instrument."""

    checkins: list[CheckInOut]


class CheckInPurgeOut(BaseModel):
    """Result of purging every recorded check-in: how many rows were removed."""

    deleted: int


def _to_instrument_out(spec: InstrumentSpec) -> InstrumentOut:
    """Map a frozen ``InstrumentSpec`` onto the wire ``InstrumentOut``."""
    return InstrumentOut(
        id=spec.id,
        title=spec.title,
        recall_period=spec.recall_period,
        scale_min=spec.scale_min,
        scale_max=spec.scale_max,
        total_min=spec.total_min,
        total_max=spec.total_max,
        items=[InstrumentItemOut(index=item.index, prompt=item.prompt) for item in spec.items],
        answer_options=[
            AnswerOptionOut(value=option.value, label=option.label)
            for option in spec.answer_options
        ],
        severity_bands=[
            SeverityBandOut(label=band.label, lower=band.lower, upper=band.upper)
            for band in spec.severity_bands
        ],
        citation=spec.citation,
    )


def _to_checkin_out(checkin: CheckIn) -> CheckInOut:
    """Map a recorded ``CheckIn`` onto the wire, recomputing its routing."""
    routing = route_for_checkin(checkin.flags)
    message_id = routing.message_id
    return CheckInOut(
        instrument_id=checkin.instrument_id,
        date=checkin.date.isoformat(),
        responses=list(checkin.responses),
        total=checkin.total,
        severity_label=checkin.severity_label,
        flags=[flag.value for flag in checkin.flags],
        action=routing.action.value,
        message_id=message_id,
        message=_ROUTING_MESSAGE_TEXT.get(message_id) if message_id is not None else None,
    )


def include_measurement_routes(
    app: FastAPI,
    tracker: CheckInTracker,
    ae_log: AdverseEventLog | None = None,
) -> None:
    """Register the measurement endpoints on ``app`` over ``tracker``.

    ``POST /checkins`` returns 200 on success (not 201 — the recorded
    check-in is a plain value in a conversation, not a creatable resource).
    ``tracker.record`` ``ValueError`` (unknown instrument, invalid
    responses, out-of-order date) becomes a generic 422;
    ``GET /checkins/{instrument_id}`` validates the instrument id first so a
    valid instrument with no check-ins is an empty list, not an error;
    ``DELETE /checkins`` purges through the tracker itself, so a durable
    tracker empties its store and its memory together while an in-memory
    tracker empties its records — one honest count either way.

    ``ae_log`` (stage 7a, optional): when provided, a recorded check-in
    carrying EARLY_WORSENSING appends one automatic
    ``transient_early_worsening`` event (D5). The library default stays
    ``None``; ``create_service`` always passes a real log so the product
    path can never silently skip safety recording (D8).
    """

    @app.get("/instruments", response_model=InstrumentListOut)
    def list_instruments() -> InstrumentListOut:
        return InstrumentListOut(
            instruments=[_to_instrument_out(spec) for spec in INSTRUMENTS.values()]
        )

    @app.post("/checkins", response_model=CheckInOut)
    def record_checkin(checkin_request: CheckInRequest) -> CheckInOut:
        try:
            checkin = tracker.record(
                checkin_request.instrument_id,
                checkin_request.responses,
                datetime.date.fromisoformat(checkin_request.date),
            )
        except ValueError:
            raise HTTPException(status_code=422, detail=CHECKIN_UNRECORDED_DETAIL) from None
        # Stage 7a (D5/D7): OUTSIDE the ValueError handler above — an
        # AE-integrity failure is a 500 through the app's generic handler,
        # never a 422, and never silently swallowed.
        if ae_log is not None:
            event = early_worsening_event(checkin)
            if event is not None:
                ae_log.append(event)
        return _to_checkin_out(checkin)

    @app.get("/checkins/{instrument_id}", response_model=CheckInListOut)
    def checkin_history(instrument_id: str) -> CheckInListOut:
        try:
            get_instrument(instrument_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=UNKNOWN_INSTRUMENT_DETAIL) from None
        baseline = tracker.baseline(instrument_id)
        history = tracker.history(instrument_id) if baseline is not None else ()
        return CheckInListOut(checkins=[_to_checkin_out(entry) for entry in history])

    @app.delete("/checkins", response_model=CheckInPurgeOut)
    def purge_checkins() -> CheckInPurgeOut:
        """Purge every recorded check-in and return how many were removed.

        Routed through ``tracker.delete_all`` so the durable tracker empties
        its SQLite store and its in-memory mirror together (no rows can
        resurrect on restart) while the in-memory dev tracker empties its
        records. The route takes no path parameter, so there is no
        instrument-id to validate: the per-instrument 404 contract of
        ``GET /checkins/{instrument_id}`` is unchanged.
        """
        return CheckInPurgeOut(deleted=tracker.delete_all())
