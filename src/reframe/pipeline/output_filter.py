"""Layer 5 output safety: what the MODEL produced is re-checked before delivery.

Deterministic only — case-insensitive regex rules (:data:`OUTPUT_RULES`) plus a
reuse of the input classifier (the model must never emit crisis-level content;
scripted crisis resources only ever come from the bypass path). No model
calls, no I/O, no randomness: identical text always yields an identical
:class:`OutputVerdict`.
"""

import re
from dataclasses import dataclass

from reframe.safety.classifier import classify_input
from reframe.safety.types import VerdictLevel

#: Marker violation added when the input classifier flags model output HIGH_RISK.
SAFETY_REUSE_MARKER = "SAFETY-REUSE-HIGH-RISK"

#: Fallback message id carried by every blocked verdict.
FALLBACK_MESSAGE_ID = "filter_fallback_v1"

#: (rule_id, case-insensitive pattern) — one entry per required rule family.
OUTPUT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Diagnosis claims
    ("OUT-DX-YOU-HAVE", re.compile(r"you (?:have|might have|seem to have)", re.IGNORECASE)),
    (
        "OUT-DX-YOU-ARE",
        re.compile(r"you are (?:clearly )?(?:depressed|bipolar|anxious|borderline)", re.IGNORECASE),
    ),
    ("OUT-DX-SOUNDS-LIKE", re.compile(r"sounds like (?:you have|depression)", re.IGNORECASE)),
    # Treatment advice
    (
        "OUT-TX-YOU-SHOULD",
        re.compile(
            r"you should (?:take|start|try|consider) (?:medication|antidepressants|therapy|ssri)",
            re.IGNORECASE,
        ),
    ),
    ("OUT-TX-DOSE", re.compile(r"increase your dose", re.IGNORECASE)),
    ("OUT-TX-START-STOP", re.compile(r"(?:start|stop) taking", re.IGNORECASE)),
    ("OUT-TX-PRESCRIB", re.compile(r"prescrib", re.IGNORECASE)),
    # Professional impersonation / credentials
    (
        "OUT-CRED-AS-A",
        re.compile(r"as a (?:doctor|therapist|psychiatrist|clinician|licensed)", re.IGNORECASE),
    ),
    (
        "OUT-CRED-I-AM-A",
        re.compile(r"i am a (?:doctor|therapist|psychiatrist|licensed)", re.IGNORECASE),
    ),
    ("OUT-CRED-TRUST-ME", re.compile(r"trust me,? i(?:'m| am) a", re.IGNORECASE)),
    # Risk scoring
    ("OUT-RISK-YOUR-RISK", re.compile(r"your risk (?:level|score) is", re.IGNORECASE)),
    ("OUT-RISK-YOU-ARE", re.compile(r"you are (?:low|medium|high) risk", re.IGNORECASE)),
    ("OUT-RISK-X-RISK-OF", re.compile(r"(?:low|medium|high) risk of", re.IGNORECASE)),
    # Sycophancy / false reassurance
    (
        "OUT-SYC-NOTHING",
        re.compile(r"there (?:is|'s) nothing (?:wrong|to worry about) with you", re.IGNORECASE),
    ),
    (
        "OUT-SYC-NORMAL",
        re.compile(r"you are (?:completely|totally) (?:normal|fine|okay|right)", re.IGNORECASE),
    ),
    (
        "OUT-SYC-DONT-WORRY",
        re.compile(r"don'?t worry,? you(?:'re| are) (?:fine|normal|okay)", re.IGNORECASE),
    ),
)


@dataclass(frozen=True)
class OutputVerdict:
    """Immutable verdict for one piece of model output.

    ``violations`` holds the sorted rule ids of every rule that fired, plus
    :data:`SAFETY_REUSE_MARKER` when the input classifier flags the output as
    ``HIGH_RISK``; it is empty exactly when ``passed`` is true.
    """

    passed: bool
    violations: tuple[str, ...]
    fallback_message_id: str | None


def filter_output(text: str) -> OutputVerdict:
    """Deterministically approve or block one piece of model output.

    Blocked (``passed=False``) if ANY :data:`OUTPUT_RULES` pattern matches, or
    if reusing :func:`reframe.safety.classify_input` on the output yields
    ``VerdictLevel.HIGH_RISK`` (fail-closed: the model must never emit
    crisis-level content — scripted crisis resources only ever come from the
    bypass path).

    Args:
        text: The model-produced reply text.

    Returns:
        The immutable verdict: sorted violations plus the fallback message id
        when blocked, else an empty, passing verdict.

    Raises:
        TypeError: If ``text`` is not a ``str``.
        ValueError: If ``text`` is empty or whitespace-only after stripping.
    """
    if not isinstance(text, str):
        raise TypeError(f"filter_output() requires str, got {type(text).__name__}")

    if not text.strip():
        raise ValueError("filter_output() requires non-empty text")

    violations = [rule_id for rule_id, pattern in OUTPUT_RULES if pattern.search(text)]
    if classify_input(text).level is VerdictLevel.HIGH_RISK:
        violations.append(SAFETY_REUSE_MARKER)

    if violations:
        return OutputVerdict(
            passed=False,
            violations=tuple(sorted(violations)),
            fallback_message_id=FALLBACK_MESSAGE_ID,
        )
    return OutputVerdict(passed=True, violations=(), fallback_message_id=None)
