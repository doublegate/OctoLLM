"""
Executor Arm service client.

The Executor specializes in sandboxed command execution.
"""

from typing import Any

from ..client import BaseClient
from ..models import (
    ExecutionRequest,
    ExecutionResult,
    HealthResponse,
    SandboxStatusResponse,
)


class ExecutorClient(BaseClient):
    """
    Client for Tool Executor Arm service (port 8006).

    Executes commands in isolated Docker containers with security controls.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:18006",
        api_key: str | None = None,
        bearer_token: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize Executor client.

        Args:
            base_url: Executor service URL (default: http://localhost:18006)
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

    async def execute(
        self,
        request: ExecutionRequest,
        timeout: float | None = None,
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

    async def get_capabilities(self, timeout: float | None = None) -> dict:
        """Get executor capabilities."""
        response = await self.get("/capabilities", timeout=timeout)
        return response

    async def get_sandbox_status(
        self,
        sandbox_id: str,
        timeout: float | None = None,
    ) -> SandboxStatusResponse:
        """
        Get the state of one execution sandbox.

        Not served yet: the hardened sandbox arrives in Stage 9, and the executor is
        still a Rust hello-world serving only `/health`. It is here because the
        TypeScript SDK has carried `getSandboxStatus` since Phase 0 and this SDK had
        no equivalent -- an asymmetry `scripts/ci/check_sdk_parity.py` now fails on.

        Args:
            sandbox_id: The sandbox to query
            timeout: Request timeout in seconds

        Returns:
            SandboxStatusResponse with the sandbox state and, while running, its
            resource usage

        Raises:
            NotFoundError: No such sandbox, or the endpoint does not exist yet.
        """
        response = await self.get(f"/sandbox/{sandbox_id}/status", timeout=timeout)
        return SandboxStatusResponse(**response)
