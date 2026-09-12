"""
Reflex Layer service client.

The Reflex Layer provides fast preprocessing including cache checks,
PII detection, and prompt injection detection.
"""

from typing import Any

from ..client import BaseClient
from ..models import CacheStats, HealthResponse, PreprocessRequest, PreprocessResponse


class ReflexClient(BaseClient):
    """
    Client for Reflex Layer service (port 8080).

    Fast preprocessing layer that handles cache lookups, PII detection,
    and prompt injection detection without LLM involvement.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: str | None = None,
        bearer_token: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize Reflex Layer client.

        Args:
            base_url: Reflex service URL (default: http://localhost:8080)
            api_key: API key for authentication
            bearer_token: JWT bearer token for authentication
            **kwargs: Additional arguments for BaseClient
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            bearer_token=bearer_token,
            **kwargs,
        )

    async def health(self, timeout: float | None = None) -> HealthResponse:
        """Check service health."""
        response = await self.get("/health", timeout=timeout)
        return HealthResponse(**response)

    async def preprocess(
        self,
        request: PreprocessRequest,
        timeout: float | None = None,
    ) -> PreprocessResponse:
        """
        Preprocess input text.

        Args:
            request: PreprocessRequest with input text and check options
            timeout: Request timeout in seconds

        Returns:
            PreprocessResponse with cache status, PII detection, and sanitized input

        Example:
            >>> from octollm_sdk import PreprocessRequest
            >>> request = PreprocessRequest(
            ...     input_text="My email is john@example.com",
            ...     detect_pii=True
            ... )
            >>> result = await client.preprocess(request)
            >>> print(f"PII detected: {result.pii_detected}")
            PII detected: True
            >>> print(f"Sanitized: {result.sanitized_input}")
            Sanitized: My email is [EMAIL]
        """
        # `/process`, not `/preprocess`. The reflex layer has only ever served
        # `/process`; this SDK asked for a path that has never existed, and no test
        # noticed because every one of them mocked the transport.
        response = await self.post(
            "/process",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return PreprocessResponse(**response)

    async def get_cache_stats(self, timeout: float | None = None) -> CacheStats:
        """
        Get cache statistics.

        Args:
            timeout: Request timeout in seconds

        Returns:
            CacheStats with hit rate, memory usage, etc.

        Example:
            >>> stats = await client.get_cache_stats()
            >>> print(f"Hit rate: {stats.hit_rate:.1%}")
            Hit rate: 65.3%
        """
        response = await self.get("/cache/stats", timeout=timeout)
        return CacheStats(**response)

    async def clear_cache(self, timeout: float | None = None) -> dict:
        """
        Clear the cache.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Confirmation message

        Example:
            >>> result = await client.clear_cache()
            >>> print(result)
            {'message': 'Cache cleared successfully'}
        """
        response = await self.post("/cache/clear", timeout=timeout)
        return response
