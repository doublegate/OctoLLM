"""
Configuration management for OctoLLM SDK.

Supports configuration from environment variables and direct parameters.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class OctoLLMConfig:
    """
    Configuration for OctoLLM client.

    Attributes:
        base_url: Base URL for OctoLLM Orchestrator service
        api_key: API key for authentication (can be set via OCTOLLM_API_KEY env var)
        bearer_token: JWT bearer token for inter-service auth (OCTOLLM_BEARER_TOKEN env var)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for failed requests
        verify_ssl: Whether to verify SSL certificates
    """

    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        """Load configuration from environment variables if not explicitly set."""
        # Load API key from environment if not provided
        if not self.api_key and not self.bearer_token:
            self.api_key = os.getenv("OCTOLLM_API_KEY")
            self.bearer_token = os.getenv("OCTOLLM_BEARER_TOKEN")

        # Load base URL from environment if using default
        if self.base_url == "http://localhost:8000":
            env_url = os.getenv("OCTOLLM_BASE_URL")
            if env_url:
                self.base_url = env_url

        # Ensure base_url doesn't end with slash
        if self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_env(cls) -> "OctoLLMConfig":
        """
        Create configuration from environment variables.

        Environment variables:
            OCTOLLM_BASE_URL: Base URL for OctoLLM API
            OCTOLLM_API_KEY: API key for authentication
            OCTOLLM_BEARER_TOKEN: JWT bearer token (alternative to API key)
            OCTOLLM_TIMEOUT: Request timeout in seconds (default: 30.0)
            OCTOLLM_MAX_RETRIES: Max retry attempts (default: 3)
            OCTOLLM_VERIFY_SSL: Verify SSL certificates (default: true)

        Returns:
            OctoLLMConfig instance

        Example:
            >>> # Export OCTOLLM_API_KEY=sk-12345
            >>> config = OctoLLMConfig.from_env()
            >>> print(config.api_key)
            sk-12345
        """
        return cls(
            base_url=os.getenv("OCTOLLM_BASE_URL", "http://localhost:8000"),
            api_key=os.getenv("OCTOLLM_API_KEY"),
            bearer_token=os.getenv("OCTOLLM_BEARER_TOKEN"),
            timeout=float(os.getenv("OCTOLLM_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("OCTOLLM_MAX_RETRIES", "3")),
            verify_ssl=os.getenv("OCTOLLM_VERIFY_SSL", "true").lower() == "true",
        )


# Service URLs relative to base URL
SERVICE_PORTS = {
    "orchestrator": 8000,
    "reflex": 8001,
    "planner": 8002,
    "executor": 8003,
    "retriever": 8004,
    "coder": 8005,
    "judge": 8006,
    "safety_guardian": 8007,
}


def get_service_url(base_url: str, service: str) -> str:
    """
    Get full URL for a specific service.

    Args:
        base_url: Base URL (e.g., http://localhost:8000)
        service: Service name (orchestrator, planner, coder, etc.)

    Returns:
        Full URL for the service

    Example:
        >>> get_service_url("http://localhost:8000", "coder")
        'http://localhost:8005'
    """
    if service not in SERVICE_PORTS:
        raise ValueError(
            f"Unknown service '{service}'. Must be one of: {list(SERVICE_PORTS.keys())}"
        )

    # Extract hostname and replace port
    if "://" in base_url:
        protocol, rest = base_url.split("://", 1)
        host = rest.split(":")[0].split("/")[0]
        port = SERVICE_PORTS[service]
        return f"{protocol}://{host}:{port}"
    else:
        raise ValueError(f"Invalid base URL format: {base_url}")
