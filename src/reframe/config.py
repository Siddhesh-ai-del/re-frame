"""Typed runtime settings for RE:FRAME, loaded from environment variables."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_ENVIRONMENT = "development"
VALID_ENVIRONMENTS = ("development", "test", "production")
ENV_VAR_ENVIRONMENT = "REFRAME_ENV"
ENV_VAR_API_KEY = "REFRAME_API_KEY"
ENV_VAR_LLM_BASE_URL = "REFRAME_LLM_BASE_URL"
ENV_VAR_LLM_MODEL = "REFRAME_LLM_MODEL"


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings.

    ``api_key`` is declared with ``repr=False`` so the secret can never surface in
    logs, tracebacks, or any other string rendering of a ``Settings`` instance.
    The LLM endpoint overrides are NOT secrets: they render normally.
    """

    environment: str = DEFAULT_ENVIRONMENT
    api_key: str | None = field(default=None, repr=False)
    llm_base_url: str | None = None
    llm_model: str | None = None


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from ``env``, or from ``os.environ`` when ``env is None``.

    Raises:
        ValueError: If ``REFRAME_ENV`` is not one of :data:`VALID_ENVIRONMENTS`,
            if the environment is ``production`` and ``REFRAME_API_KEY`` is
            missing (fail-closed secret boundary), or if
            ``REFRAME_LLM_BASE_URL`` is set to a non-``http(s)://`` value
            (fail-closed, mirroring ``OpenAICompatibleClient``'s own check).
    """
    source: Mapping[str, str] = os.environ if env is None else env

    environment = source.get(ENV_VAR_ENVIRONMENT, "").strip() or DEFAULT_ENVIRONMENT
    if environment not in VALID_ENVIRONMENTS:
        valid = ", ".join(VALID_ENVIRONMENTS)
        raise ValueError(
            f"{ENV_VAR_ENVIRONMENT}={environment!r} is not a valid environment; "
            f"valid options are: {valid}"
        )

    api_key = source.get(ENV_VAR_API_KEY, "").strip() or None
    if environment == "production" and api_key is None:
        raise ValueError(
            f"{ENV_VAR_API_KEY} must be set when {ENV_VAR_ENVIRONMENT} is 'production'"
        )

    llm_base_url = source.get(ENV_VAR_LLM_BASE_URL, "").strip() or None
    if llm_base_url is not None and not llm_base_url.startswith(("http://", "https://")):
        raise ValueError(
            f"{ENV_VAR_LLM_BASE_URL}={llm_base_url!r} must start with http:// or https://"
        )

    llm_model = source.get(ENV_VAR_LLM_MODEL, "").strip() or None

    return Settings(
        environment=environment,
        api_key=api_key,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
    )
