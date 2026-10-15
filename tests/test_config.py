"""Tests for ``reframe.config`` settings loading and the secret boundary."""

from dataclasses import FrozenInstanceError

import pytest

from reframe.config import Settings, load_settings

SECRET = "sk-test-secret-value"


def test_defaults_from_fresh_mapping() -> None:
    settings = load_settings({})
    assert settings.environment == "development"
    assert settings.api_key is None


def test_settings_dataclass_defaults() -> None:
    settings = Settings()
    assert settings.environment == "development"
    assert settings.api_key is None


def test_env_mapping_honors_reframe_env() -> None:
    settings = load_settings({"REFRAME_ENV": "test"})
    assert settings.environment == "test"


def test_env_mapping_honors_api_key() -> None:
    settings = load_settings({"REFRAME_API_KEY": SECRET})
    assert settings.api_key == SECRET


def test_env_mapping_honors_both_variables() -> None:
    settings = load_settings({"REFRAME_ENV": "production", "REFRAME_API_KEY": SECRET})
    assert settings.environment == "production"
    assert settings.api_key == SECRET


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_blank_reframe_env_falls_back_to_default(raw: str) -> None:
    settings = load_settings({"REFRAME_ENV": raw})
    assert settings.environment == "development"


def test_reframe_env_is_stripped_before_validation() -> None:
    settings = load_settings({"REFRAME_ENV": "  production  ", "REFRAME_API_KEY": SECRET})
    assert settings.environment == "production"


def test_invalid_reframe_env_raises_with_guidance() -> None:
    with pytest.raises(ValueError) as excinfo:
        load_settings({"REFRAME_ENV": "staging"})

    message = str(excinfo.value)
    assert "REFRAME_ENV" in message
    assert "development" in message
    assert "test" in message
    assert "production" in message


def test_production_without_api_key_fails_closed() -> None:
    with pytest.raises(ValueError) as excinfo:
        load_settings({"REFRAME_ENV": "production"})

    assert "REFRAME_API_KEY" in str(excinfo.value)


def test_production_with_api_key_is_allowed() -> None:
    settings = load_settings({"REFRAME_ENV": "production", "REFRAME_API_KEY": SECRET})
    assert settings.environment == "production"
    assert settings.api_key == SECRET


def test_api_key_hidden_from_repr_and_str() -> None:
    settings = load_settings({"REFRAME_API_KEY": SECRET})
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)


def test_settings_repr_omits_api_key_field_entirely() -> None:
    assert "api_key" not in repr(Settings())


def test_blank_api_key_treated_as_missing() -> None:
    settings = load_settings({"REFRAME_ENV": "development", "REFRAME_API_KEY": "   "})
    assert settings.api_key is None


def test_settings_is_frozen() -> None:
    settings = Settings()
    with pytest.raises(FrozenInstanceError):
        settings.environment = "production"


def test_env_none_uses_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REFRAME_ENV", "production")
    monkeypatch.setenv("REFRAME_API_KEY", SECRET)

    settings = load_settings()

    assert settings.environment == "production"
    assert settings.api_key == SECRET


def test_env_none_defaults_when_os_environ_is_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REFRAME_ENV", raising=False)
    monkeypatch.delenv("REFRAME_API_KEY", raising=False)

    settings = load_settings()

    assert settings.environment == "development"
    assert settings.api_key is None


def test_explicit_mapping_ignores_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REFRAME_ENV", "production")
    monkeypatch.setenv("REFRAME_API_KEY", SECRET)

    settings = load_settings({"REFRAME_ENV": "test"})

    assert settings.environment == "test"
    assert settings.api_key is None
