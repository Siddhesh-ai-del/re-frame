"""System-prompt red lines and deterministic prompt assembly.

Everything here is pure string logic: no I/O, no randomness — the exact bytes
sent to the provider are a deterministic function of the curated modules.
"""

from reframe.content.schema import ExerciseModule

#: The verbatim early-worsening notice appended to blocks that opt into it.
EARLY_WORSENING_NOTICE = (
    "It is normal for unsettled feelings to briefly increase when starting an exercise; "
    "if that happens, pause and consider reaching out to a professional."
)

#: The verbatim instruction appended to the user message when nothing matched.
NO_EXERCISE_MATCHED_INSTRUCTION = (
    "No specific exercise matched; offer warm general support within your boundaries, "
    "and suggest the user describe their situation further."
)

#: The non-negotiable red lines, stated as explicit sentences (one per line).
SYSTEM_PROMPT = "\n".join(
    (
        "You are a wellness companion for adults, not a healthcare professional.",
        "Never diagnose or suggest the user has any condition.",
        "Never recommend treatment, therapy, or medication.",
        "Never claim professional credentials or impersonate a therapist, doctor, or clinician.",
        "Never assess, score, or mention risk levels.",
        "Never promise outcomes or cures.",
        "Only suggest exercises from the provided exercise content; never invent exercises.",
        (
            "If asked for a diagnosis, treatment, or medication advice, decline warmly "
            "and suggest speaking with a qualified professional."
        ),
        "Style: warm, plain language, short messages, no lists of medical terms.",
    )
)


def build_context(modules: tuple[ExerciseModule, ...]) -> str:
    """Render curated modules as exercise blocks for system-side injection.

    Args:
        modules: The curated modules retrieved for this turn (may be empty).

    Returns:
        Blocks joined by a blank line — id, title, category, tier, summary,
        numbered steps, and the early-worsening notice when the module opts
        into it — or ``""`` when ``modules`` is empty (an empty context is
        valid; the request then carries no exercise).
    """
    if not modules:
        return ""
    blocks: list[str] = []
    for module in modules:
        lines = [
            f"Exercise id: {module.id}",
            f"Title: {module.title}",
            f"Category: {module.category.value}",
            f"Evidence tier: {module.tier.value}",
            f"Summary: {module.summary}",
            "Steps:",
        ]
        for number, step in enumerate(module.steps, start=1):
            lines.append(f"{number}. {step}")
        if module.early_worsening_notice:
            lines.append(f"Early-worsening notice: {EARLY_WORSENING_NOTICE}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_user_message(user_message: str, modules_present: bool) -> str:
    """Wrap ``user_message`` with the no-match instruction when nothing matched.

    Args:
        user_message: The raw user text for this turn.
        modules_present: Whether any curated module accompanies the turn.

    Returns:
        ``user_message`` unchanged when modules are present; otherwise the
        message with :data:`NO_EXERCISE_MATCHED_INSTRUCTION` appended.
    """
    if modules_present:
        return user_message
    return f"{user_message}\n\n{NO_EXERCISE_MATCHED_INSTRUCTION}"
