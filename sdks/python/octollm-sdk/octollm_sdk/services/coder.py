"""
Coder Arm service client.

The Coder specializes in code generation, debugging, and refactoring.
"""

from typing import Optional
from ..client import BaseClient
from ..models import CodeRequest, CodeResponse, HealthResponse


class CoderClient(BaseClient):
    """
    Client for Coder Arm service (port 8005).

    Generates, debugs, and refactors code in multiple programming languages.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8005",
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize Coder client.

        Args:
            base_url: Coder service URL (default: http://localhost:8005)
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

    async def health(self, timeout: Optional[float] = None) -> HealthResponse:
        """Check service health."""
        response = await self.get("/health", timeout=timeout)
        return HealthResponse(**response)

    async def generate_code(
        self,
        request: CodeRequest,
        timeout: Optional[float] = None,
    ) -> CodeResponse:
        """
        Generate, debug, or refactor code.

        Args:
            request: CodeRequest with operation type and parameters
            timeout: Request timeout in seconds

        Returns:
            CodeResponse with generated code and explanation

        Example:
            >>> from octollm_sdk import CodeRequest
            >>> request = CodeRequest(
            ...     operation="generate",
            ...     prompt="Create a Python function to validate email addresses",
            ...     language="python",
            ...     include_tests=True,
            ...     include_docstrings=True
            ... )
            >>> result = await client.generate_code(request)
            >>> print(result.code)
            def validate_email(email: str) -> bool:
                \"\"\"Validate email address format.\"\"\"
                ...
            >>> print(result.tests)
            def test_validate_email():
                ...
        """
        response = await self.post(
            "/code",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return CodeResponse(**response)

    async def get_capabilities(self, timeout: Optional[float] = None) -> dict:
        """Get coder capabilities."""
        response = await self.get("/capabilities", timeout=timeout)
        return response
