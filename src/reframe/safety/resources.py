"""Crisis resources surfaced on hard bypass — real, well-known services only."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrisisResource:
    """A named crisis resource; ``url`` is ``None`` for non-linkable guidance."""

    name: str
    url: str | None


DEFAULT_CRISIS_RESOURCES: tuple[CrisisResource, ...] = (
    CrisisResource(
        name="Find A Helpline (IASP global directory)",
        url="https://findahelpline.com",
    ),
    CrisisResource(
        name="988 Suicide & Crisis Lifeline (US)",
        url="https://988lifeline.org",
    ),
    CrisisResource(
        name="If you are in immediate danger, contact your local emergency services",
        url=None,
    ),
)
