"""Constrained generation: curated content in, boundary-observing reply out.

The generator is the only place a prompt meets an LLM client: it assembles
the red lines, the retrieved exercise context, and the wrapped user message,
then translates any unexpected client failure into
:class:`~reframe.generation.client.GenerationError` so this layer leaks
exactly one exception type. Escalation is NOT handled here — the input
safety layer decides before generation ever runs.
"""

from dataclasses import dataclass

from reframe.content.schema import ExerciseModule
from reframe.generation.client import GenerationError, GenerationRequest, LLMClient
from reframe.generation.prompts import SYSTEM_PROMPT, build_context, build_user_message


@dataclass(frozen=True)
class GenerationResult:
    """Immutable outcome of one turn: reply text, model, and the modules served."""

    text: str
    model: str
    module_ids: tuple[str, ...]


class ConstrainedGenerator:
    """Turns (user message, curated modules) into one constrained LLM completion."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def respond(
        self,
        user_message: str,
        modules: tuple[ExerciseModule, ...] = (),
    ) -> GenerationResult:
        """Generate one constrained reply for ``user_message``.

        Args:
            user_message: Raw user text for this turn (non-blank string).
            modules: Curated modules retrieved for this turn (may be empty).

        Returns:
            The reply text, the model that produced it, and the ids of the
            modules actually provided (in the order given).

        Raises:
            TypeError: If ``user_message`` is not a ``str``.
            ValueError: If ``user_message`` is empty or whitespace-only.
            GenerationError: If the client fails — a client ``GenerationError``
                propagates unchanged; any other client exception is wrapped so
                arbitrary exceptions never leak through this layer.
        """
        if not isinstance(user_message, str):
            raise TypeError(
                "ConstrainedGenerator.respond: user_message must be str, "
                f"got {type(user_message).__name__}"
            )
        if not user_message.strip():
            raise ValueError(f"ConstrainedGenerator.respond: {user_message!r} must not be blank")

        request = GenerationRequest(
            system_prompt=SYSTEM_PROMPT,
            context=build_context(modules),
            user_message=build_user_message(user_message, bool(modules)),
        )
        try:
            response = self._client.complete(request)
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError(
                f"ConstrainedGenerator: unexpected client failure ({type(exc).__name__})"
            ) from exc
        return GenerationResult(
            text=response.text,
            model=response.model,
            module_ids=tuple(module.id for module in modules),
        )
