"""
Executor Arm service client.

The Executor specializes in sandboxed command execution.
"""

from typing import Optional
from ..client import BaseClient
from ..models import ExecutionRequest, ExecutionResult, HealthResponse


class ExecutorClient(BaseClient):
    """
    Client for Tool Executor Arm service (port 8003).

    Executes commands in isolated Docker containers with security controls.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8003",
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Executor client.

        Args:
            base_url: Executor service URL (default: http://localhost:8003)
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

    async def execute(
        self,
        request: ExecutionRequest,
        timeout: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute a command in a sandboxed environment.

        Args:
            request: ExecutionRequest with command and execution parameters
            timeout: Request timeout in seconds (should be > request.timeout_seconds)

        Returns:
            ExecutionResult with stdout, stderr, and exit code

        Example:
            >>> from octollm_sdk import ExecutionRequest
            >>> request = ExecutionRequest(
            ...     command="echo",
            ...     command_type="shell",
            ...     args=["Hello, World!"],
            ...     timeout_seconds=10
            ... )
            >>> result = await client.execute(request)
            >>> print(f"Exit code: {result.exit_code}")
            Exit code: 0
            >>> print(f"Output: {result.stdout}")
            Output: Hello, World!
        """
        response = await self.post(
            "/execute",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return ExecutionResult(**response)

    async def get_capabilities(self, timeout: Optional[float] = None) -> dict:
        """Get executor capabilities."""
        response = await self.get("/capabilities", timeout=timeout)
        return response
