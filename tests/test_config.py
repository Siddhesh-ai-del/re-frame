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


# ---------------------------------------------------------------------------
# Stage 6e: optional LLM endpoint overrides (mock-LLM / local provider seam)
# ---------------------------------------------------------------------------


def test_llm_overrides_default_to_none() -> None:
    settings = load_settings({})
    assert settings.llm_base_url is None
    assert settings.llm_model is None


def test_settings_dataclass_llm_defaults() -> None:
    settings = Settings()
    assert settings.llm_base_url is None
    assert settings.llm_model is None


def test_llm_overrides_read_from_env_mapping() -> None:
    settings = load_settings(
        {
            "REFRAME_LLM_BASE_URL": "http://127.0.0.1:8125",
            "REFRAME_LLM_MODEL": "mock-model",
        }
    )
    assert settings.llm_base_url == "http://127.0.0.1:8125"
    assert settings.llm_model == "mock-model"


def test_llm_overrides_are_stripped() -> None:
    settings = load_settings(
        {
            "REFRAME_LLM_BASE_URL": "  https://llm.example/v1  ",
            "REFRAME_LLM_MODEL": "  my-model  ",
        }
    )
    assert settings.llm_base_url == "https://llm.example/v1"
    assert settings.llm_model == "my-model"


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_blank_llm_base_url_is_treated_as_unset(raw: str) -> None:
    settings = load_settings({"REFRAME_LLM_BASE_URL": raw})
    assert settings.llm_base_url is None


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_blank_llm_model_is_treated_as_unset(raw: str) -> None:
    settings = load_settings({"REFRAME_LLM_MODEL": raw})
    assert settings.llm_model is None


@pytest.mark.parametrize(
    "raw",
    ["ftp://llm.example/v1", "llm.example", "file:///tmp/llm", "ws://localhost:9999"],
)
def test_invalid_llm_base_url_fails_closed(raw: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        load_settings({"REFRAME_LLM_BASE_URL": raw})

    message = str(excinfo.value)
    assert "REFRAME_LLM_BASE_URL" in message
    assert "http" in message


def test_llm_base_url_accepts_both_http_schemes() -> None:
    for url in ("http://127.0.0.1:8125", "https://api.openai.com/v1"):
        settings = load_settings({"REFRAME_LLM_BASE_URL": url})
        assert settings.llm_base_url == url


def test_llm_model_accepts_any_non_blank_value() -> None:
    # Not validated beyond non-blank: the client validates at construction.
    settings = load_settings({"REFRAME_LLM_MODEL": "gpt-x-large-2026"})
    assert settings.llm_model == "gpt-x-large-2026"


def test_llm_overrides_read_from_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REFRAME_LLM_BASE_URL", "http://127.0.0.1:8125")
    monkeypatch.setenv("REFRAME_LLM_MODEL", "mock-model")

    settings = load_settings()

    assert settings.llm_base_url == "http://127.0.0.1:8125"
    assert settings.llm_model == "mock-model"


def test_llm_overrides_are_repr_visible_not_secret() -> None:
    # Unlike the API key, the endpoint overrides are not secrets: they render.
    settings = Settings(llm_base_url="http://127.0.0.1:8125", llm_model="mock-model")
    assert "llm_base_url" in repr(settings)
    assert "mock-model" in repr(settings)


def test_production_rule_is_unchanged_by_llm_overrides() -> None:
    # Regression: production without a key still fails closed, even with
    # endpoint overrides configured.
    with pytest.raises(ValueError) as excinfo:
        load_settings(
            {"REFRAME_ENV": "production", "REFRAME_LLM_BASE_URL": "http://127.0.0.1:8125"}
        )

    assert "REFRAME_API_KEY" in str(excinfo.value)
