"""Typed runtime settings for RE:FRAME, loaded from environment variables."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_ENVIRONMENT = "development"
VALID_ENVIRONMENTS = ("development", "test", "production")
ENV_VAR_ENVIRONMENT = "REFRAME_ENV"
ENV_VAR_API_KEY = "REFRAME_API_KEY"


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings.

    ``api_key`` is declared with ``repr=False`` so the secret can never surface in
    logs, tracebacks, or any other string rendering of a ``Settings`` instance.
    """

    environment: str = DEFAULT_ENVIRONMENT
    api_key: str | None = field(default=None, repr=False)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from ``env``, or from ``os.environ`` when ``env is None``.

    Raises:
        ValueError: If ``REFRAME_ENV`` is not one of :data:`VALID_ENVIRONMENTS`,
            or if the environment is ``production`` and ``REFRAME_API_KEY`` is
            missing (fail-closed secret boundary).
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

    return Settings(environment=environment, api_key=api_key)
