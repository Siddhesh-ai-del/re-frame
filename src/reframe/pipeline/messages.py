"""The scripted, non-generative response catalog — safety-owned wording only.

These three messages are the ONLY text the pipeline speaks without the model:
crisis bypass, human-review boundary, and output-filter fallback. The wording
is warm, wellness-framed plain English with no diagnosis or treatment
vocabulary, and only the crisis response carries crisis resources.
"""

from dataclasses import dataclass

from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES, CrisisResource


@dataclass(frozen=True)
class ScriptedResponse:
    """Immutable, pre-approved message: id, wording, and any crisis resources."""

    message_id: str
    text: str
    resources: tuple[CrisisResource, ...]


CRISIS_RESPONSE = ScriptedResponse(
    message_id="crisis_response_v1",
    text=(
        "I'm really sorry you're carrying this right now — you deserve support, and I want to be "
        "honest: I'm a wellness companion, not a crisis service, so I can't help with a crisis "
        "moment. Please reach out to people who can: the 988 Suicide & Crisis Lifeline (US) at "
        "988lifeline.org, or Find A Helpline (IASP global directory) at findahelpline.com to find "
        "a helpline in your country. If you might be in immediate danger, please contact your "
        "local emergency services or go to the nearest emergency department right now, and try "
        "not to be alone while you wait."
    ),
    resources=DEFAULT_CRISIS_RESOURCES,
)

BOUNDARY_RESPONSE = ScriptedResponse(
    message_id="boundary_response_v1",
    text=(
        "I hear how heavy this feels, and I'm glad you reached out. There are some things I'm not "
        "able to do: I can't work through painful memories with you, offer a label for what "
        "you're experiencing, or support you when things feel far from steady — I'm a wellness "
        "companion, not a qualified professional. What I can do is encourage you to speak with a "
        "qualified professional who is trained for this, such as your doctor or a licensed "
        "counselor. If things feel urgent or unsafe right now, please reach out to crisis support "
        "or your local emergency services — you deserve real, timely help."
    ),
    resources=(),
)

FILTER_FALLBACK = ScriptedResponse(
    message_id="filter_fallback_v1",
    text=(
        "I want to be careful with my words here, so I'm going to slow down. I can share a short "
        "wellness exercise you could try right now, or I can simply listen while you tell me more "
        "about what's going on — whichever would feel more helpful to you."
    ),
    resources=(),
)

#: Every scripted response, keyed by the message id the escalation table emits.
SCRIPTED: dict[str, ScriptedResponse] = {
    CRISIS_RESPONSE.message_id: CRISIS_RESPONSE,
    BOUNDARY_RESPONSE.message_id: BOUNDARY_RESPONSE,
    FILTER_FALLBACK.message_id: FILTER_FALLBACK,
}
