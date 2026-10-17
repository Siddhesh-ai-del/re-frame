"""Bridge check-in flags onto the existing escalation vocabulary.

:func:`route_for_checkin` is a pure table lookup from pre-specified
check-in flags to the pipeline's :class:`~reframe.safety.EscalationAction`
vocabulary. ESCALATE reuses the pipeline's scripted crisis path
(``crisis_response_v1``) — the SCRIPTED catalog in
:mod:`reframe.pipeline.messages` remains the single source for that wording.
Human-review routings reference ``checkin_concern_v1``; the concern text
itself lives in :data:`CHECKIN_CONCERN_TEXT` here.

The routing decision, like the flags it consumes, never turns a summed
score into a risk category of the person (NICE NG225): the non-crisis paths
only open a human-review conversation.
"""

from dataclasses import dataclass

from reframe.measurement.flags import CheckInFlag
from reframe.safety import EscalationAction

#: Scripted crisis path shared with the conversation pipeline (the pipeline's
#: SCRIPTED catalog is the single source for that text).
CHECKIN_CRISIS_MESSAGE_ID = "crisis_response_v1"

#: Message id for the wellness-framed concern response (:data:`CHECKIN_CONCERN_TEXT`).
CHECKIN_CONCERN_MESSAGE_ID = "checkin_concern_v1"

#: Warm, plain, wellness-framed wording acknowledging a flagged check-in
#: without diagnosis or judging numbers, encouraging a conversation with a
#: qualified professional, and framing reaching out as a strength. Deliberately
#: avoids: treat, therapy/therapist, diagnos-, prescrib-, medication.
CHECKIN_CONCERN_TEXT = (
    "Thank you for taking the time to check in with us — what you shared matters, and it "
    "took real courage to notice how you have been feeling and to say it out loud. We are "
    "not able to judge or label what this means for you, and no score can capture the whole "
    "of your experience. Please consider talking with a qualified professional who can "
    "listen properly and walk alongside you with care. Reaching out for support is a "
    "genuine strength, not a weakness, and you deserve support that is thoughtful and "
    "unhurried."
)


@dataclass(frozen=True)
class CheckInRouting:
    """Immutable routing decision for one flagged check-in."""

    action: EscalationAction
    message_id: str | None


def route_for_checkin(flags: tuple[CheckInFlag, ...]) -> CheckInRouting:
    """Map one check-in's flags onto the fixed escalation policy table.

    +---------------------------+---------------+----------------------+
    | Flags                     | Action        | Message id           |
    +===========================+===============+======================+
    | ESCALATE present          | ``HARD_BYPASS``  | ``crisis_response_v1``  |
    | EARLY_WORSENSING or       | ``HUMAN_REVIEW`` | ``checkin_concern_v1``  |
    | REFERRAL_PROMPT           |               |                      |
    +---------------------------+---------------+----------------------+
    | none                      | ``PROCEED``      | ``None``                |
    +---------------------------+---------------+----------------------+

    ESCALATE takes precedence over every other flag (fail-closed: the
    scripted crisis path is never downgraded). Pure function of the flags
    only: no I/O, environment, or randomness.
    """
    if CheckInFlag.ESCALATE in flags:
        return CheckInRouting(
            action=EscalationAction.HARD_BYPASS, message_id=CHECKIN_CRISIS_MESSAGE_ID
        )
    if CheckInFlag.EARLY_WORSENSING in flags or CheckInFlag.REFERRAL_PROMPT in flags:
        return CheckInRouting(
            action=EscalationAction.HUMAN_REVIEW, message_id=CHECKIN_CONCERN_MESSAGE_ID
        )
    return CheckInRouting(action=EscalationAction.PROCEED, message_id=None)
