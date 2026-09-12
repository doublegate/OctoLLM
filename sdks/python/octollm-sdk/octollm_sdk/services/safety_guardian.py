"""
Safety Guardian Arm service client.

The Safety Guardian specializes in PII detection and content filtering.
"""

from typing import Any

from ..client import BaseClient
from ..models import HealthResponse, SafetyRequest, SafetyResult


class SafetyGuardianClient(BaseClient):
    """
    Client for Safety Guardian Arm service (port 8005).

    Detects PII, prompt injection, and harmful content to ensure safe operation.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8005",
        api_key: str | None = None,
        bearer_token: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize Safety Guardian client.

        Args:
            base_url: Safety Guardian service URL (default: http://localhost:8005)
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

    async def check_safety(
        self,
        request: SafetyRequest,
        timeout: float | None = None,
    ) -> SafetyResult:
        """
        Perform safety checks on content.

        Args:
            request: SafetyRequest with content and check types
            timeout: Request timeout in seconds

        Returns:
            SafetyResult with detected issues and sanitized content

        Example:
            >>> from octollm_sdk import SafetyRequest
            >>> request = SafetyRequest(
            ...     content="My SSN is 123-45-6789 and email is john@example.com",
            ...     check_types=["pii"],
            ...     sanitize=True
            ... )
            >>> result = await client.check_safety(request)
            >>> print(f"Safe: {result.safe}")
            Safe: False
            >>> print(f"Risk score: {result.risk_score}")
            Risk score: 0.85
            >>> for issue in result.issues:
            ...     print(f"- {issue.issue_type}: {issue.description}")
            - pii: Social Security Number detected
            - pii: Email address detected
            >>> print(result.sanitized_content)
            My SSN is [SSN] and email is [EMAIL]
        """
        response = await self.post(
            "/check",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return SafetyResult(**response)

    async def get_capabilities(self, timeout: float | None = None) -> dict:
        """Get safety guardian capabilities."""
        response = await self.get("/capabilities", timeout=timeout)
        return response
