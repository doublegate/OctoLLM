"""
Memory arm configuration.

Prefixed `MEMORY_`, which is what `pydantic-settings` needs and what
`scripts/ci/check_compose_env.py` asserts every compose variable matches. All 23
compose variables in this repository were silently ignored before that check existed,
because the orchestrator's were unprefixed and the reflex layer's used a separator that
made most of its configuration unreachable. A setting nothing reads is a setting that
lies.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment for the Memory / Curator arm."""

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    service_name: str = Field(default="memory", description="Service name")
    version: str = Field(default="0.5.0", description="Service version")
    log_level: str = Field(default="INFO", description="Root log level")

    database_url: str = Field(
        default="postgresql+psycopg://octollm:octollm@localhost:5432/octollm",
        description="PostgreSQL URL for the `memory` schema. Async driver.",
    )
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant REST endpoint holding the episodic collections",
    )
    # Seconds, as an int: qdrant-client's own signature takes `int | None`, and a float
    # here would be a type error at the only place this value is used.
    qdrant_timeout: int = Field(default=10, ge=1, le=120)

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Where the Neural Ring's artifact streams live",
    )
    ring_enabled: bool = Field(
        default=True,
        description=(
            "Consume `artifact` from the ring. Off in tests that exercise only the "
            "HTTP surface, so a missing Redis is never mistaken for a broken arm."
        ),
    )
    ring_block_ms: int = Field(default=2000, ge=10, le=60_000)
    ring_batch: int = Field(default=32, ge=1, le=500)

    capability_secret: str | None = Field(
        None,
        description=(
            "Verification key for capability tokens the orchestrator signs. Unset by "
            "default, and `/recall` and `/remember` then answer 503 -- a deployment "
            "that has not configured authorization should refuse, not allow. Memory "
            "holds every arm's output, so an open recall endpoint is a read of the "
            "whole system's work."
        ),
    )
    capability_kid: str = Field("k1", description="Key id the orchestrator signs with")

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        """
        Refuse a sync driver URL.

        `postgresql://` selects psycopg's sync driver under SQLAlchemy's async engine
        and fails at connect time with an error that names neither the setting nor the
        fix. The compose file supplies the async form; this makes a hand-edited one
        fail at startup instead.
        """
        if not v.startswith("postgresql+psycopg://"):
            raise ValueError(
                "MEMORY_DATABASE_URL must use the async driver, "
                f"'postgresql+psycopg://...' (got {v.split('://', 1)[0]!r}://)"
            )
        if any(ch.isspace() for ch in v):
            raise ValueError(
                "MEMORY_DATABASE_URL contains whitespace. A YAML folded scalar (`>-`) "
                "joins its lines with a space and will silently corrupt a URL; quote "
                "it on one line instead."
            )
        return v


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Drop the cached settings. Used by tests that change the environment."""
    global _settings
    _settings = None
