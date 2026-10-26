"""Pre-specified adverse-event taxonomy and the fail-closed AE record.

Honesty framing (binding on every string in this module): the six types in
:class:`AEType` are RE:FRAME *pre-specified design definitions* for safety
monitoring of the feasibility pilot. They are NOT validated published
adverse-event definitions — none exist for GenAI mental-health
interventions: none of the 21 reviewed GenAI interventions defines an
adverse event (Olisaeloka et al. 2026, *Healthcare*, DOI
10.3390/healthcare14101395). The AI-specific direction (AE definitions,
human escalation pathways) follows the US FDA Digital Health Advisory
Committee (6 Nov 2025); the early-worsening monitoring signal follows NICE
NG222 rec. 1.2.10.

Record rules (design decisions):

- **D1 — no message content, ever.** ``reference`` is a locator string
  only (at most 200 chars after stripping): an instrument id/date/total,
  an audit digest, or a reviewer locator like ``"session 3 turn 14"`` —
  never the text of a turn or a check-in response vector.
- **D2 — pre-specified seriousness, overridable at record time.** Each
  :class:`AEDefinition` carries its ``default_serious`` value and
  rationale; :meth:`AdverseEvent.create` applies that default when the
  caller passes ``serious=None``.
- **D3 — 48-hour follow-up marker.** Serious events are due for follow-up
  at ``detected_at + SERIOUS_FOLLOWUP_HOURS``; the marker is a PROPERTY of
  ``serious`` + ``detected_at`` (one constant, never a stored column).
- Records are FROZEN: replacements go through
  :meth:`AdverseEvent.with_followup_completed`, never mutation.
"""

import datetime
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType

#: Hours after detection at which a SERIOUS event's follow-up is due (NIA/NIH
#: DSMP serious-unexpected-event reporting timeline, design-applied).
SERIOUS_FOLLOWUP_HOURS: int = 48

#: Maximum length of the D1 ``reference`` locator after stripping.
_MAX_REFERENCE_CHARS: int = 200


# ``str, Enum`` is the repo-mandated base (StrEnum would change ``str()`` output).
class AEType(str, Enum):  # noqa: UP042
    """The six PRE-SPECIFIED adverse-event types (design definitions, not validated)."""

    CRISIS_RESPONSE_FAILURE = "crisis_response_failure"
    HALLUCINATED_CLINICAL_CLAIM = "hallucinated_clinical_claim"
    BOUNDARY_VIOLATION_DIAGNOSIS = "boundary_violation_diagnosis"
    SYCOPHANCY_EPISODE = "sycophancy_episode"
    INAPPROPRIATE_OR_DELAYED_ESCALATION = "inappropriate_or_delayed_escalation"
    TRANSIENT_EARLY_WORSENSING = "transient_early_worsening"


class AESource(str, Enum):  # noqa: UP042
    """How an adverse event entered the log.

    ``automatic`` — the in-product detector fired; ``audit`` — a
    seeded-corpus audit miss detected before any participant impact
    (near-miss); ``review`` — entered by a pilot reviewer over HTTP.
    """

    AUTOMATIC = "automatic"
    AUDIT = "audit"
    REVIEW = "review"


@dataclass(frozen=True)
class AEDefinition:
    """One pre-specified AE type: definition, citation, default seriousness."""

    type: AEType
    definition: str
    citation: str
    default_serious: bool
    seriousness_rationale: str


# Shared citation for the five content/escalation definitions: the honest
# "no validated published definitions exist" framing plus the FDA direction.
_DESIGN_CITATION = (
    "Pre-specified AI-specific AE definition (RE:FRAME design): no GenAI "
    "intervention defines an adverse event (Olisaeloka et al. 2026, Healthcare, "
    "DOI 10.3390/healthcare14101395); direction per US FDA Digital Health "
    "Advisory Committee, 6 Nov 2025 (AI-specific AE definitions, human "
    "escalation pathways)."
)

#: All six types, in :class:`AEType` declaration order, keyed by ``type.value``.
AE_DEFINITIONS: Mapping[str, AEDefinition] = MappingProxyType(
    {
        AEType.CRISIS_RESPONSE_FAILURE.value: AEDefinition(
            type=AEType.CRISIS_RESPONSE_FAILURE,
            definition=(
                "A turn classified as crisis-level did not receive the scripted "
                "crisis response — the deterministic escalation layer failed to "
                "bypass the model for a person in crisis."
            ),
            citation=_DESIGN_CITATION,
            default_serious=True,
            seriousness_rationale=(
                "The response a person in crisis depended on did not arrive; highest-harm class."
            ),
        ),
        AEType.HALLUCINATED_CLINICAL_CLAIM.value: AEDefinition(
            type=AEType.HALLUCINATED_CLINICAL_CLAIM,
            definition=(
                "Delivered output stated a clinical fact, diagnosis, or treatment "
                "claim not grounded in the curated exercise library — an invented "
                "or unverifiable claim."
            ),
            citation=_DESIGN_CITATION,
            default_serious=False,
            seriousness_rationale="Content defect; seriousness judged by review.",
        ),
        AEType.BOUNDARY_VIOLATION_DIAGNOSIS.value: AEDefinition(
            type=AEType.BOUNDARY_VIOLATION_DIAGNOSIS,
            definition=(
                "Delivered output diagnosed, assigned a risk category, or presented "
                "itself as care — a breach of the non-diagnostic wellness boundary."
            ),
            citation=_DESIGN_CITATION,
            default_serious=False,
            seriousness_rationale="Content defect; seriousness judged by review.",
        ),
        AEType.SYCOPHANCY_EPISODE.value: AEDefinition(
            type=AEType.SYCOPHANCY_EPISODE,
            definition=(
                "Delivered output agreed with or reinforced harmful reasoning "
                "instead of holding the safety line."
            ),
            citation=_DESIGN_CITATION,
            default_serious=False,
            seriousness_rationale="Content defect; seriousness judged by review.",
        ),
        AEType.INAPPROPRIATE_OR_DELAYED_ESCALATION.value: AEDefinition(
            type=AEType.INAPPROPRIATE_OR_DELAYED_ESCALATION,
            definition=(
                "Escalation was shown when it should not have been, withheld when it "
                "should have been shown, or arrived outside the pre-specified "
                "response path."
            ),
            citation=_DESIGN_CITATION,
            default_serious=True,
            seriousness_rationale=(
                "Escalation-pathway failure, the highest-harm class after crisis-response failure."
            ),
        ),
        AEType.TRANSIENT_EARLY_WORSENSING.value: AEDefinition(
            type=AEType.TRANSIENT_EARLY_WORSENSING,
            definition=(
                "A completed check-in showed a pre-specified increase over that "
                "instrument's baseline within the early window — a participant-level "
                "untoward-outcome signal detected by the check-in flags."
            ),
            citation=(
                "NICE NG222 rec. 1.2.10 (early worsening after starting an "
                "intervention is an adverse-event signal to monitor); detection "
                "thresholds are provisional design defaults pending pilot validation."
            ),
            default_serious=False,
            seriousness_rationale=(
                "A monitoring signal, not itself a serious event; review may escalate."
            ),
        ),
    }
)


@dataclass(frozen=True)
class AdverseEvent:
    """One fail-closed adverse-event record: type, source, seriousness, locator.

    Never carries message or response content (D1) — ``reference`` is a
    locator only. ``followup_due_at`` is computed, never stored (D3).
    """

    id: str
    type: AEType
    source: AESource
    detected_at: datetime.datetime
    serious: bool
    followup_completed: bool
    reference: str | None

    def __post_init__(self) -> None:
        """Validate fail-closed and normalize the reference locator (D1).

        Raises:
            ValueError: For an empty id; a ``type``/``source`` that is not its
                enum member (bare strings are rejected, never coerced); a naive
                ``detected_at`` (an offsetless ``tzinfo`` counts as naive);
                non-bool ``serious``/``followup_completed`` (``1``/``0``
                rejected); or a ``reference`` that is not ``None``/str, is
                blank after stripping, or exceeds 200 chars.
        """
        if not self.id:
            raise ValueError("adverse-event id must not be empty")
        if not isinstance(self.type, AEType):
            raise ValueError("adverse-event type must be an AEType member")
        if not isinstance(self.source, AESource):
            raise ValueError("adverse-event source must be an AESource member")
        if self.detected_at.utcoffset() is None:
            raise ValueError("adverse-event detected_at must be timezone-aware")
        if not isinstance(self.serious, bool):
            raise ValueError("adverse-event serious must be a bool")
        if not isinstance(self.followup_completed, bool):
            raise ValueError("adverse-event followup_completed must be a bool")
        if self.reference is not None:
            if not isinstance(self.reference, str):
                raise ValueError("adverse-event reference must be a string or None")
            locator = self.reference.strip()
            if not locator:
                raise ValueError("adverse-event reference must not be blank")
            if len(locator) > _MAX_REFERENCE_CHARS:
                raise ValueError(
                    f"adverse-event reference must be at most {_MAX_REFERENCE_CHARS} characters"
                )
            object.__setattr__(self, "reference", locator)

    @classmethod
    def create(
        cls,
        type: AEType,
        *,
        source: AESource,
        reference: str | None = None,
        serious: bool | None = None,
        detected_at: datetime.datetime | None = None,
    ) -> "AdverseEvent":
        """Assemble one validated record: uuid id, UTC detection time, D2 default.

        Args:
            type: The pre-specified AE type; a bare string is rejected, not coerced.
            source: How the event was detected (automatic, audit, or review).
            reference: Optional D1 locator (at most 200 chars after stripping),
                never message content.
            serious: Override for the taxonomy default; ``None`` applies the
                pre-specified default (D2).
            detected_at: Optional tz-aware detection time; ``None`` means now (UTC).

        Returns:
            A new frozen :class:`AdverseEvent` with ``followup_completed=False``.

        Raises:
            ValueError: If ``type`` is not an :class:`AEType` member, or the
                assembled record fails validation (see :meth:`__post_init__`).
        """
        if not isinstance(type, AEType):
            raise ValueError("adverse-event type must be an AEType member")
        default_serious = AE_DEFINITIONS[type.value].default_serious
        return cls(
            id=uuid.uuid4().hex,
            type=type,
            source=source,
            detected_at=(
                datetime.datetime.now(datetime.UTC) if detected_at is None else detected_at
            ),
            serious=default_serious if serious is None else serious,
            followup_completed=False,
            reference=reference,
        )

    @property
    def followup_due_at(self) -> datetime.datetime | None:
        """``detected_at + SERIOUS_FOLLOWUP_HOURS`` iff serious, else ``None`` (D3)."""
        if not self.serious:
            return None
        return self.detected_at + datetime.timedelta(hours=SERIOUS_FOLLOWUP_HOURS)

    def with_followup_completed(self, completed: bool = True) -> "AdverseEvent":
        """Return a REPLACED copy with the follow-up marker set — never mutate."""
        return replace(self, followup_completed=completed)
