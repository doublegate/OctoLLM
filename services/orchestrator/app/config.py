"""
Configuration management for Orchestrator service.

Loads settings from environment variables with validation and defaults.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables are prefixed with ORCHESTRATOR_ (e.g., ORCHESTRATOR_DATABASE_URL).
    """

    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRATOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service Configuration
    service_name: str = Field(default="orchestrator", description="Service name")
    version: str = Field(default="0.1.0", description="Service version")
    environment: str = Field(default="development", description="Environment (dev/staging/prod)")
    debug: bool = Field(default=False, description="Debug mode")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server bind host")  # nosec B104
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, le=32, description="Number of worker processes")

    # Database Configuration
    database_url: str = Field(
        default="postgresql://octollm:octollm@localhost:5432/octollm",
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    database_max_overflow: int = Field(
        default=20, ge=0, le=100, description="Max overflow connections"
    )
    database_pool_timeout: int = Field(
        default=30, ge=1, le=300, description="Pool timeout in seconds"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(
        default=50, ge=1, le=1000, description="Redis connection pool size"
    )

    # Reflex Layer Configuration
    reflex_layer_url: str = Field(
        default="http://reflex-layer:8080",
        description="Reflex Layer service URL",
    )
    reflex_layer_timeout: float = Field(
        default=10.0, ge=1.0, le=60.0, description="Request timeout"
    )
    reflex_layer_max_retries: int = Field(default=3, ge=1, le=10, description="Max retry attempts")
    reflex_layer_circuit_breaker_threshold: int = Field(
        default=5, ge=1, le=20, description="Circuit breaker failure threshold"
    )
    reflex_layer_circuit_breaker_reset_timeout: int = Field(
        default=60, ge=10, le=600, description="Circuit breaker reset timeout"
    )

    # Task Configuration
    task_default_timeout: int = Field(
        default=300, ge=1, le=3600, description="Default task timeout"
    )
    task_max_timeout: int = Field(default=3600, ge=1, le=86400, description="Maximum task timeout")
    task_queue_size: int = Field(default=1000, ge=1, le=10000, description="Task queue size")

    # LLM Configuration (for future phases)
    openai_api_key: str | None = Field(None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(None, description="Anthropic API key")
    llm_default_model: str = Field(default="gpt-4", description="Default LLM model")
    llm_max_tokens: int = Field(default=4000, ge=1, le=128000, description="Max LLM tokens")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")

    # Observability Configuration
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    jaeger_endpoint: str = Field(
        default="http://jaeger-collector:4317",
        description="Jaeger OTLP endpoint",
    )
    otel_sampling_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Trace sampling rate"
    )

    # Feature Flags
    enable_reflex_integration: bool = Field(
        default=True, description="Enable Reflex Layer integration"
    )
    enable_background_processing: bool = Field(
        default=True, description="Enable background task processing"
    )
    enable_task_cancellation: bool = Field(default=True, description="Enable task cancellation")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is PostgreSQL."""
        if not v.startswith("postgresql://") and not v.startswith("postgresql+psycopg://"):
            raise ValueError("Database URL must be a PostgreSQL connection string")
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Ensure Redis URL format is correct."""
        if not v.startswith("redis://") and not v.startswith("rediss://"):
            raise ValueError("Redis URL must start with redis:// or rediss://")
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Ensure environment is valid."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get application settings singleton.

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (useful for testing)."""
    global _settings
    _settings = None
