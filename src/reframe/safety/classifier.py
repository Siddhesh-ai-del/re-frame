"""Deterministic, rule-based classification of disclosed user input.

Every input is matched against :data:`RULES` — compiled regexes over the
user's own words. There is no model call, randomness, environment or I/O
dependence: identical input always yields an identical verdict, and the
(future) generative model never influences whether an input escalates.

Version 1 does not attempt negation or idiom understanding: text such as
"I don't want to die anymore" will over-flag as CRISIS. Over-flagging is the
accepted direction of error — under-flagging is not acceptable (fail-closed).
"""

import re

from reframe.safety.types import SafetyVerdict, SignalType, VerdictLevel

RULES: tuple[tuple[SignalType, str, re.Pattern[str]], ...] = (
    # Crisis / suicide risk
    (SignalType.CRISIS, "CRISIS-KILL-MYSELF", re.compile(r"kill(?:ing|ed)? myself", re.IGNORECASE)),
    (SignalType.CRISIS, "CRISIS-END-MY-LIFE", re.compile(r"end my life", re.IGNORECASE)),
    (SignalType.CRISIS, "CRISIS-SUICIDE", re.compile(r"suicid(?:e|al)", re.IGNORECASE)),
    (SignalType.CRISIS, "CRISIS-TAKE-MY-LIFE", re.compile(r"take my life", re.IGNORECASE)),
    (SignalType.CRISIS, "CRISIS-WANT-TO-DIE", re.compile(r"want to die", re.IGNORECASE)),
    (SignalType.CRISIS, "CRISIS-BETTER-OFF-DEAD", re.compile(r"better off dead", re.IGNORECASE)),
    (
        SignalType.CRISIS,
        "CRISIS-SELF-INJURY",
        re.compile(r"(?:hurt|harming|cut(?:ting)?) myself", re.IGNORECASE),
    ),
    (
        SignalType.CRISIS,
        "CRISIS-SELF-HARM",
        re.compile(r"self[-\s]harm", re.IGNORECASE),
    ),
    (
        SignalType.CRISIS,
        "CRISIS-NO-REASON-TO-LIVE",
        re.compile(r"no reason to live", re.IGNORECASE),
    ),
    (
        SignalType.CRISIS,
        "CRISIS-OVERDOSE",
        re.compile(r"take an overdose", re.IGNORECASE),
    ),
    # Psychosis or mania
    (
        SignalType.PSYCHOSIS_OR_MANIA,
        "PSY-HEAR-VOICES",
        re.compile(r"hear voices", re.IGNORECASE),
    ),
    (
        SignalType.PSYCHOSIS_OR_MANIA,
        "PSY-VOICES-IN-MY-HEAD",
        re.compile(r"voices in my head", re.IGNORECASE),
    ),
    (
        SignalType.PSYCHOSIS_OR_MANIA,
        "PSY-SEEING-THINGS",
        re.compile(r"seeing things that (?:aren['’]t|are not) there", re.IGNORECASE),
    ),
    (
        SignalType.PSYCHOSIS_OR_MANIA,
        "PSY-HAVEN-T-SLEPT-FOR-DAYS",
        re.compile(r"haven['’]t slept for days", re.IGNORECASE),
    ),
    (
        SignalType.PSYCHOSIS_OR_MANIA,
        "PSY-MANIC-ENERGY",
        re.compile(r"manic energy|feel(?:ing)? manic", re.IGNORECASE),
    ),
    # Trauma processing — never processed in-product, always referred out
    (
        SignalType.TRAUMA_PROCESSING,
        "TRAUMA-MY-TRAUMA",
        re.compile(r"my trauma", re.IGNORECASE),
    ),
    (
        SignalType.TRAUMA_PROCESSING,
        "TRAUMA-FLASHBACKS",
        re.compile(r"flashbacks?", re.IGNORECASE),
    ),
    (SignalType.TRAUMA_PROCESSING, "TRAUMA-PTS-D", re.compile(r"ptsd", re.IGNORECASE)),
    (
        SignalType.TRAUMA_PROCESSING,
        "TRAUMA-WHAT-HAPPENED",
        re.compile(r"what happened to me", re.IGNORECASE),
    ),
    (
        SignalType.TRAUMA_PROCESSING,
        "TRAUMA-PROCESS-MEMORIES",
        re.compile(r"process my memories", re.IGNORECASE),
    ),
    # Diagnosis-seeking — a boundary violation, never answered in-product
    (
        SignalType.DIAGNOSIS_SEEKING,
        "DX-DO-I-HAVE",
        re.compile(r"do i have (?:depression|anxiety|bipolar|ptsd)", re.IGNORECASE),
    ),
    (
        SignalType.DIAGNOSIS_SEEKING,
        "DX-AM-I",
        re.compile(r"am i (?:depressed|bipolar)", re.IGNORECASE),
    ),
    (
        SignalType.DIAGNOSIS_SEEKING,
        "DX-DIAGNOSE-ME",
        re.compile(r"diagnose me", re.IGNORECASE),
    ),
)


def classify_input(text: str) -> SafetyVerdict:
    """Classify one user input into a deterministic :class:`SafetyVerdict`.

    Level policy (fail-closed): any crisis signal or any psychosis/mania
    signal yields ``HIGH_RISK``; any trauma-processing or diagnosis-seeking
    signal (without those) yields ``REVIEW``; otherwise ``NORMAL``. The
    returned ``signals`` tuple contains every matched signal type,
    deduplicated and sorted by :data:`~reframe.safety.types.SIGNAL_PRECEDENCE`.

    Args:
        text: Raw user-disclosed text.

    Returns:
        The deterministic verdict for ``text``.

    Raises:
        TypeError: If ``text`` is not a ``str``.
        ValueError: If ``text`` is empty or whitespace-only after stripping.
    """
    if not isinstance(text, str):
        raise TypeError(f"classify_input() requires str, got {type(text).__name__}")

    stripped = text.strip()
    if not stripped:
        raise ValueError("classify_input() requires non-empty text")

    matched: set[SignalType] = set()
    for signal, _rule_id, pattern in RULES:
        if pattern.search(stripped):
            matched.add(signal)

    if SignalType.CRISIS in matched or SignalType.PSYCHOSIS_OR_MANIA in matched:
        level = VerdictLevel.HIGH_RISK
    elif SignalType.TRAUMA_PROCESSING in matched or SignalType.DIAGNOSIS_SEEKING in matched:
        level = VerdictLevel.REVIEW
    else:
        level = VerdictLevel.NORMAL

    return SafetyVerdict(level=level, signals=tuple(matched))
