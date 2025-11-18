"""
Tests for configuration management.
"""

import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings, reset_settings


def test_settings_defaults() -> None:
    """Test default settings values."""
    settings = Settings(openai_api_key="sk-test-key")

    assert settings.service_name == "planner-arm"
    assert settings.version == "0.1.0"
    assert settings.environment == "development"
    assert settings.port == 8001
    assert settings.llm_model == "gpt-3.5-turbo"
    assert settings.planning_temperature == 0.3
    assert settings.max_tokens == 2000
    assert settings.max_plan_steps == 7
    assert settings.min_plan_steps == 3


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading settings from environment variables."""
    monkeypatch.setenv("PLANNER_OPENAI_API_KEY", "sk-env-key")
    monkeypatch.setenv("PLANNER_LLM_MODEL", "gpt-4")
    monkeypatch.setenv("PLANNER_ENVIRONMENT", "production")
    monkeypatch.setenv("PLANNER_MAX_PLAN_STEPS", "10")

    reset_settings()
    settings = Settings(openai_api_key="sk-env-key")

    assert settings.llm_model == "gpt-4"
    assert settings.environment == "production"
    assert settings.max_plan_steps == 10


def test_settings_validation_invalid_environment() -> None:
    """Test validation for invalid environment."""
    with pytest.raises(ValidationError, match="Environment must be one of"):
        Settings(openai_api_key="sk-test", environment="invalid")


def test_settings_validation_invalid_model() -> None:
    """Test validation for invalid LLM model."""
    with pytest.raises(ValidationError, match="LLM model must be one of"):
        Settings(openai_api_key="sk-test", llm_model="invalid-model")


def test_settings_validation_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validation for missing API key."""
    # Clear the API key from environment (set by autouse fixture)
    monkeypatch.delenv("PLANNER_OPENAI_API_KEY", raising=False)
    reset_settings()

    with pytest.raises(ValidationError):
        Settings()  # Missing required openai_api_key


def test_settings_validation_temperature_bounds() -> None:
    """Test validation for temperature bounds."""
    # Valid bounds
    Settings(openai_api_key="sk-test", planning_temperature=0.0)
    Settings(openai_api_key="sk-test", planning_temperature=2.0)

    # Invalid bounds
    with pytest.raises(ValidationError):
        Settings(openai_api_key="sk-test", planning_temperature=-0.1)
    with pytest.raises(ValidationError):
        Settings(openai_api_key="sk-test", planning_temperature=2.1)


def test_settings_validation_plan_steps() -> None:
    """Test validation for plan step counts."""
    # Valid
    Settings(openai_api_key="sk-test", min_plan_steps=1, max_plan_steps=7)

    # Invalid: max < 3
    with pytest.raises(ValidationError):
        Settings(openai_api_key="sk-test", max_plan_steps=2)

    # Invalid: min < 1
    with pytest.raises(ValidationError):
        Settings(openai_api_key="sk-test", min_plan_steps=0)


def test_is_development() -> None:
    """Test is_development helper."""
    settings = Settings(openai_api_key="sk-test", environment="development")
    assert settings.is_development() is True
    assert settings.is_production() is False


def test_is_production() -> None:
    """Test is_production helper."""
    settings = Settings(openai_api_key="sk-test", environment="production")
    assert settings.is_production() is True
    assert settings.is_development() is False


def test_get_settings_singleton() -> None:
    """Test settings singleton pattern."""
    reset_settings()

    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_reset_settings() -> None:
    """Test resetting settings singleton."""
    reset_settings()
    settings1 = get_settings()

    reset_settings()
    settings2 = get_settings()

    # Should be different instances after reset
    assert settings1 is not settings2
