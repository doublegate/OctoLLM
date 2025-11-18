"""
Configuration management for Planner Arm service.

Loads settings from environment variables with validation and defaults.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables are prefixed with PLANNER_ (e.g., PLANNER_OPENAI_API_KEY).
    """

    model_config = SettingsConfigDict(
        env_prefix="PLANNER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service Configuration
    service_name: str = Field(default="planner-arm", description="Service name")
    version: str = Field(default="0.1.0", description="Service version")
    environment: str = Field(default="development", description="Environment (dev/staging/prod)")
    debug: bool = Field(default=False, description="Debug mode")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server bind host")  # nosec B104
    port: int = Field(default=8001, ge=1, le=65535, description="Server port")

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key (required)")
    llm_model: str = Field(default="gpt-3.5-turbo", description="LLM model to use")
    planning_temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="LLM temperature (low for consistency)"
    )
    max_tokens: int = Field(default=2000, ge=100, le=8000, description="Max tokens for LLM")
    llm_timeout: float = Field(default=30.0, ge=1.0, le=120.0, description="LLM API timeout")

    # Planning Configuration
    max_plan_steps: int = Field(default=7, ge=3, le=15, description="Maximum steps in plan")
    min_plan_steps: int = Field(default=3, ge=1, le=10, description="Minimum steps in plan")
    timeout_seconds: int = Field(default=10, ge=1, le=60, description="Planning operation timeout")
    max_retries: int = Field(default=3, ge=1, le=5, description="Max retry attempts for LLM")

    # Observability Configuration
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Ensure environment is valid."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @field_validator("llm_model")
    @classmethod
    def validate_llm_model(cls, v: str) -> str:
        """Ensure LLM model is supported."""
        allowed_models = [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-turbo-preview",
        ]
        if v not in allowed_models:
            raise ValueError(f"LLM model must be one of {allowed_models}")
        return v

    @field_validator("max_plan_steps")
    @classmethod
    def validate_max_plan_steps(cls, v: int) -> int:
        """Validate max plan step count."""
        if v < 3:
            raise ValueError("max_plan_steps must be at least 3")
        return v

    @field_validator("min_plan_steps")
    @classmethod
    def validate_min_plan_steps(cls, v: int) -> int:
        """Validate min plan step count."""
        if v < 1:
            raise ValueError("min_plan_steps must be at least 1")
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
