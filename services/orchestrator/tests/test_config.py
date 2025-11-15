"""
Tests for Orchestrator configuration.

Validates settings loading, environment variable handling, and configuration validation.
"""

import os

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings, reset_settings

# ==============================================================================
# Settings Loading Tests
# ==============================================================================


def test_settings_defaults():
    """Test Settings loads with default values."""
    # Reset any existing settings
    reset_settings()

    # Clear environment variables
    for key in list(os.environ.keys()):
        if key.startswith("ORCHESTRATOR_"):
            del os.environ[key]

    settings = Settings()

    assert settings.service_name == "orchestrator"
    assert settings.version == "0.1.0"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.host == "0.0.0.0"  # nosec B104  # Test assertion for default config value
    assert settings.port == 8000
    assert settings.workers == 1
    assert settings.database_url == "postgresql://octollm:octollm@localhost:5432/octollm"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.reflex_layer_url == "http://reflex-layer:8080"
    assert settings.enable_reflex_integration is True
    assert settings.enable_background_processing is True


def test_settings_from_environment_variables():
    """Test Settings loads from environment variables."""
    reset_settings()

    # Set environment variables
    os.environ["ORCHESTRATOR_SERVICE_NAME"] = "test-orchestrator"
    os.environ["ORCHESTRATOR_VERSION"] = "2.0.0"
    os.environ["ORCHESTRATOR_ENVIRONMENT"] = "staging"
    os.environ["ORCHESTRATOR_DEBUG"] = "true"
    os.environ["ORCHESTRATOR_PORT"] = "9000"
    os.environ["ORCHESTRATOR_DATABASE_URL"] = "postgresql://test:test@testhost:5432/testdb"
    os.environ["ORCHESTRATOR_REDIS_URL"] = "redis://testhost:6379/1"

    settings = Settings()

    assert settings.service_name == "test-orchestrator"
    assert settings.version == "2.0.0"
    assert settings.environment == "staging"
    assert settings.debug is True
    assert settings.port == 9000
    assert settings.database_url == "postgresql://test:test@testhost:5432/testdb"
    assert settings.redis_url == "redis://testhost:6379/1"

    # Cleanup
    for key in [
        "ORCHESTRATOR_SERVICE_NAME",
        "ORCHESTRATOR_VERSION",
        "ORCHESTRATOR_ENVIRONMENT",
        "ORCHESTRATOR_DEBUG",
        "ORCHESTRATOR_PORT",
        "ORCHESTRATOR_DATABASE_URL",
        "ORCHESTRATOR_REDIS_URL",
    ]:
        if key in os.environ:
            del os.environ[key]
    reset_settings()


def test_settings_case_insensitive():
    """Test Settings environment variable prefix is case-insensitive."""
    reset_settings()

    os.environ["orchestrator_service_name"] = "lowercase-test"

    settings = Settings()
    assert settings.service_name == "lowercase-test"

    del os.environ["orchestrator_service_name"]
    reset_settings()


def test_get_settings_singleton():
    """Test get_settings returns singleton instance."""
    reset_settings()

    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2

    reset_settings()


def test_reset_settings():
    """Test reset_settings clears singleton."""
    settings1 = get_settings()
    reset_settings()
    settings2 = get_settings()

    # After reset, should be different instance
    assert settings1 is not settings2


# ==============================================================================
# Validation Tests
# ==============================================================================


def test_database_url_validation_rejects_non_postgresql():
    """Test database_url validation rejects non-PostgreSQL URLs."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url="sqlite:///test.db")

    assert "postgresql" in str(exc_info.value).lower()


def test_database_url_validation_rejects_mysql():
    """Test database_url validation rejects MySQL URLs."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url="mysql://user:pass@localhost/db")

    assert "postgresql" in str(exc_info.value).lower()


def test_database_url_validation_accepts_postgresql():
    """Test database_url validation accepts postgresql:// URLs."""
    settings = Settings(database_url="postgresql://user:pass@host:5432/db")
    assert settings.database_url == "postgresql://user:pass@host:5432/db"


def test_database_url_validation_accepts_postgresql_psycopg():
    """Test database_url validation accepts postgresql+psycopg:// URLs."""
    settings = Settings(database_url="postgresql+psycopg://user:pass@host:5432/db")
    assert settings.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_redis_url_validation_rejects_invalid_scheme():
    """Test redis_url validation rejects invalid schemes."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql://test:test@localhost:5432/test",
            redis_url="http://localhost:6379",
        )

    assert "redis" in str(exc_info.value).lower()


def test_redis_url_validation_accepts_redis_scheme():
    """Test redis_url validation accepts redis:// URLs."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
    )
    assert settings.redis_url == "redis://localhost:6379/0"


def test_redis_url_validation_accepts_rediss_scheme():
    """Test redis_url validation accepts rediss:// URLs (SSL)."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        redis_url="rediss://secure-host:6380/0",
    )
    assert settings.redis_url == "rediss://secure-host:6380/0"


def test_environment_validation_rejects_invalid():
    """Test environment validation rejects invalid values."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url="postgresql://test:test@localhost:5432/test", environment="invalid")

    assert "environment" in str(exc_info.value).lower()


def test_environment_validation_accepts_development():
    """Test environment validation accepts 'development'."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test", environment="development"
    )
    assert settings.environment == "development"


def test_environment_validation_accepts_staging():
    """Test environment validation accepts 'staging'."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test", environment="staging"
    )
    assert settings.environment == "staging"


def test_environment_validation_accepts_production():
    """Test environment validation accepts 'production'."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test", environment="production"
    )
    assert settings.environment == "production"


def test_port_validation_rejects_zero():
    """Test port validation rejects 0."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url="postgresql://test:test@localhost:5432/test", port=0)

    assert "port" in str(exc_info.value).lower()


def test_port_validation_rejects_negative():
    """Test port validation rejects negative values."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url="postgresql://test:test@localhost:5432/test", port=-1)

    assert "port" in str(exc_info.value).lower()


def test_port_validation_rejects_above_65535():
    """Test port validation rejects ports above 65535."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url="postgresql://test:test@localhost:5432/test", port=70000)

    assert "port" in str(exc_info.value).lower()


def test_port_validation_accepts_valid_port():
    """Test port validation accepts valid port numbers."""
    settings = Settings(database_url="postgresql://test:test@localhost:5432/test", port=8080)
    assert settings.port == 8080


# ==============================================================================
# Helper Method Tests
# ==============================================================================


def test_is_development_true():
    """Test is_development returns True for development environment."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test", environment="development"
    )
    assert settings.is_development() is True
    assert settings.is_production() is False


def test_is_production_true():
    """Test is_production returns True for production environment."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test", environment="production"
    )
    assert settings.is_production() is True
    assert settings.is_development() is False


def test_is_development_false_for_staging():
    """Test is_development returns False for staging."""
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test", environment="staging"
    )
    assert settings.is_development() is False
    assert settings.is_production() is False


# ==============================================================================
# Feature Flag Tests
# ==============================================================================


def test_feature_flags_defaults():
    """Test feature flags have correct default values."""
    settings = Settings(database_url="postgresql://test:test@localhost:5432/test")

    assert settings.enable_reflex_integration is True
    assert settings.enable_background_processing is True
    assert settings.enable_task_cancellation is True
    assert settings.enable_metrics is True
    assert settings.enable_tracing is True


def test_feature_flags_can_be_disabled():
    """Test feature flags can be disabled via environment variables."""
    reset_settings()

    os.environ["ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION"] = "false"
    os.environ["ORCHESTRATOR_ENABLE_BACKGROUND_PROCESSING"] = "false"
    os.environ["ORCHESTRATOR_ENABLE_METRICS"] = "false"
    os.environ["ORCHESTRATOR_DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"

    settings = Settings()

    assert settings.enable_reflex_integration is False
    assert settings.enable_background_processing is False
    assert settings.enable_metrics is False

    # Cleanup
    for key in [
        "ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION",
        "ORCHESTRATOR_ENABLE_BACKGROUND_PROCESSING",
        "ORCHESTRATOR_ENABLE_METRICS",
        "ORCHESTRATOR_DATABASE_URL",
    ]:
        if key in os.environ:
            del os.environ[key]
    reset_settings()


# ==============================================================================
# Observability Configuration Tests
# ==============================================================================


def test_observability_defaults():
    """Test observability configuration defaults."""
    settings = Settings(database_url="postgresql://test:test@localhost:5432/test")

    assert settings.enable_metrics is True
    assert settings.enable_tracing is True
    assert settings.otel_sampling_rate == 0.1
    assert settings.jaeger_endpoint == "http://jaeger-collector:4317"


def test_sampling_rate_validation():
    """Test OTEL sampling rate must be between 0.0 and 1.0."""
    # Valid sampling rates
    settings1 = Settings(
        database_url="postgresql://test:test@localhost:5432/test", otel_sampling_rate=0.0
    )
    assert settings1.otel_sampling_rate == 0.0

    settings2 = Settings(
        database_url="postgresql://test:test@localhost:5432/test", otel_sampling_rate=1.0
    )
    assert settings2.otel_sampling_rate == 1.0

    # Invalid sampling rate
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://test:test@localhost:5432/test", otel_sampling_rate=1.5)
