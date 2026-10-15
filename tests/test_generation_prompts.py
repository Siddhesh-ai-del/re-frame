"""Tests for ``reframe.generation.prompts`` — the nine red lines and deterministic assembly.

Strict TDD stage 2b: written BEFORE any ``reframe.generation`` module exists (RED).
"""

import pytest

from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)
from reframe.generation.prompts import SYSTEM_PROMPT, build_context, build_user_message

#: The early-worsening sentence the spec mandates verbatim.
EARLY_WORSENING_LINE = (
    "It is normal for unsettled feelings to briefly increase when starting an exercise; "
    "if that happens, pause and consider reaching out to a professional."
)

#: The no-match instruction the spec mandates verbatim.
NO_MATCH_LINE = (
    "No specific exercise matched; offer warm general support within your boundaries, "
    "and suggest the user describe their situation further."
)


def _module(
    module_id: str = "attention-shift-refocus",
    *,
    title: str = "Attention shift and refocus",
    summary: str = "Redirect attention away from looping thoughts.",
    steps: tuple[str, ...] = ("Notice the loop.", "Name it and refocus."),
    category: ExerciseCategory = ExerciseCategory.RUMINATION,
    tier: EvidenceTier = EvidenceTier.A,
    early_worsening_notice: bool = True,
) -> ExerciseModule:
    """Build a valid module; each test varies only the field under test."""
    return ExerciseModule(
        id=module_id,
        title=title,
        summary=summary,
        category=category,
        tier=tier,
        safety_class=SafetyClass.SELF_HELP_SAFE,
        steps=steps,
        sources=("NICE NG222 depression in adults (2022)",),
        early_worsening_notice=early_worsening_notice,
    )


# ---------------------------------------------------------------------------
# SYSTEM_PROMPT — the nine red lines, asserted individually
# ---------------------------------------------------------------------------


def test_system_prompt_is_a_non_empty_string() -> None:
    assert isinstance(SYSTEM_PROMPT, str)
    assert SYSTEM_PROMPT.strip()


@pytest.mark.parametrize(
    "phrase",
    [
        "You are a wellness companion for adults, not a healthcare professional",
        "Never diagnose or suggest the user has any condition",
        "Never recommend treatment, therapy, or medication",
        "Never claim professional credentials or impersonate a therapist, doctor, or clinician",
        "Never assess, score, or mention risk levels",
        "Never promise outcomes or cures",
        "Only suggest exercises from the provided exercise content; never invent exercises",
        "decline warmly and suggest speaking with a qualified professional",
        "warm, plain language, short messages, no lists of medical terms",
    ],
    ids=[
        "red-line-1-wellness-companion",
        "red-line-2-no-diagnosis",
        "red-line-3-no-treatment",
        "red-line-4-no-credentials",
        "red-line-5-no-risk-levels",
        "red-line-6-no-outcome-promises",
        "red-line-7-curated-exercises-only",
        "red-line-8-decline-warmly",
        "red-line-9-warm-plain-short-style",
    ],
)
def test_system_prompt_states_each_red_line(phrase: str) -> None:
    assert phrase in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# build_context — deterministic exercise blocks
# ---------------------------------------------------------------------------


def test_build_context_renders_every_modules_block() -> None:
    first = _module(
        "attention-shift-refocus",
        title="Attention shift",
        summary="Redirect attention away from looping thoughts.",
        steps=("Notice the loop.", "Name it and refocus."),
    )
    second = _module(
        "concreteness-training",
        title="Concreteness training",
        summary="Turn vague worries into concrete specifics.",
        tier=EvidenceTier.B,
        steps=("Catch the vague worry.", "Make it specific and factual."),
        early_worsening_notice=False,
    )

    context = build_context((first, second))

    assert "Exercise id: attention-shift-refocus" in context
    assert "Exercise id: concreteness-training" in context
    assert "Title: Attention shift" in context
    assert "Title: Concreteness training" in context
    assert "Category: rumination" in context
    assert "Evidence tier: A" in context
    assert "Evidence tier: B" in context
    assert "Summary: Redirect attention away from looping thoughts." in context
    assert "Summary: Turn vague worries into concrete specifics." in context
    assert "1. Notice the loop." in context
    assert "2. Name it and refocus." in context
    assert "1. Catch the vague worry." in context
    assert "2. Make it specific and factual." in context


def test_build_context_includes_early_worsening_notice_when_enabled() -> None:
    context = build_context((_module(early_worsening_notice=True),))
    assert EARLY_WORSENING_LINE in context


def test_build_context_omits_early_worsening_notice_when_disabled() -> None:
    context = build_context((_module(early_worsening_notice=False),))
    assert EARLY_WORSENING_LINE not in context


def test_build_context_with_no_modules_is_the_empty_string() -> None:
    assert build_context(()) == ""


# ---------------------------------------------------------------------------
# build_user_message — deterministic instruction wrapper
# ---------------------------------------------------------------------------


def test_build_user_message_returns_message_unchanged_when_modules_present() -> None:
    message = "I keep ruminating at night"
    result = build_user_message(message, True)
    assert result == message
    assert NO_MATCH_LINE not in result


def test_build_user_message_appends_support_instruction_when_no_modules() -> None:
    message = "I keep ruminating at night"
    result = build_user_message(message, False)
    assert result != message
    assert result.startswith(message)
    assert NO_MATCH_LINE in result
