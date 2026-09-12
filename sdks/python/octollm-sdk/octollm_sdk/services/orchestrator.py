"""
Orchestrator service client.

The Orchestrator is the central brain that coordinates task planning,
arm delegation, and result integration.
"""

from typing import Any

from ..client import BaseClient
from ..models import (
    ArmCapability,
    HealthResponse,
    RegisterArmRequest,
    RegisterArmResponse,
    TaskRequest,
    TaskResponse,
    TaskStatusResponse,
)


class OrchestratorClient(BaseClient):
    """
    Client for Orchestrator service (port 8000).

    The Orchestrator receives complex tasks, breaks them down into subtasks,
    delegates to specialized arms, and synthesizes results.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        bearer_token: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize Orchestrator client.

        Args:
            base_url: Orchestrator service URL (default: http://localhost:8000)
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
        """
        Check service health.

        Args:
            timeout: Request timeout in seconds

        Returns:
            HealthResponse with service status and version

        Example:
            >>> client = OrchestratorClient(api_key="sk-12345")
            >>> health = await client.health()
            >>> print(health.status)
            healthy
        """
        response = await self.get("/health", timeout=timeout)
        return HealthResponse(**response)

    async def get_metrics(self, timeout: float | None = None) -> str:
        """
        Get Prometheus metrics.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Metrics in Prometheus text format

        Example:
            >>> metrics = await client.get_metrics()
            >>> print(metrics)
            # HELP orchestrator_tasks_total Total tasks processed
            # TYPE orchestrator_tasks_total counter
            orchestrator_tasks_total 1234
        """
        # _make_plain_text_request is a coroutine returning the body, not an async context
        # manager; `async with` on it raised AttributeError on every call.
        return await self._make_plain_text_request("GET", "/metrics", timeout)

    async def list_arms(self, timeout: float | None = None) -> list[ArmCapability]:
        """
        List registered arms and their capabilities.

        Args:
            timeout: Request timeout in seconds

        Returns:
            List of ArmCapability objects

        Example:
            >>> arms = await client.list_arms()
            >>> for arm in arms:
            ...     print(f"{arm.name}: {arm.capabilities}")
            Planner Arm: ['task_planning', 'goal_decomposition']
            Coder Arm: ['code_generation', 'debugging']
        """
        # `/arms`, not `/capabilities`. The two SDKs disagreed about this path, and
        # neither endpoint existed. `/capabilities` means *this service's own
        # declaration* on every arm; reusing it here for "the arms I know about" is
        # the kind of near-collision that produces a wrong client six months later.
        response = await self.get("/arms", timeout=timeout)
        return [ArmCapability(**arm) for arm in response["arms"]]

    async def submit_task(
        self,
        task: TaskRequest,
        timeout: float | None = None,
    ) -> TaskResponse:
        """
        Submit a new task to the orchestrator.

        Args:
            task: TaskRequest with goal, constraints, and budget
            timeout: Request timeout in seconds

        Returns:
            TaskResponse with task_id and status

        Raises:
            ValidationError: If task validation fails
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded

        Example:
            >>> from octollm_sdk import TaskRequest, ResourceBudget
            >>> task = TaskRequest(
            ...     goal="Create a Python function to validate emails",
            ...     constraints=["Include type hints", "Add docstring"],
            ...     budget=ResourceBudget(max_tokens=5000, max_time_seconds=30)
            ... )
            >>> response = await client.submit_task(task)
            >>> print(f"Task ID: {response.task_id}")
            Task ID: task_abc123xyz789
        """
        # `/submit`, not `/tasks`. The orchestrator has only ever served `POST /submit`
        # -- `/tasks/{id}` is the read path. Both SDKs posted to `/tasks`, which is a
        # 405 against the real service.
        response = await self.post(
            "/submit",
            json=task.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return TaskResponse(**response)

    async def get_task(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> TaskStatusResponse:
        """
        Get task status and results.

        Args:
            task_id: Task identifier
            timeout: Request timeout in seconds

        Returns:
            TaskStatusResponse with current status, progress, and results

        Raises:
            NotFoundError: If task doesn't exist

        Example:
            >>> status = await client.get_task("task_abc123xyz789")
            >>> print(f"Status: {status.status}")
            Status: completed
            >>> if status.result:
            ...     print(f"Output: {status.result.output}")
        """
        response = await self.get(f"/tasks/{task_id}", timeout=timeout)
        return TaskStatusResponse(**response)

    async def cancel_task(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> TaskStatusResponse:
        """
        Cancel a running task.

        Args:
            task_id: Task identifier
            timeout: Request timeout in seconds

        Returns:
            TaskStatusResponse with updated status

        Raises:
            NotFoundError: If task doesn't exist

        Example:
            >>> result = await client.cancel_task("task_abc123xyz789")
            >>> print(result.status)
            cancelled
        """
        response = await self.delete(f"/tasks/{task_id}", timeout=timeout)
        return TaskStatusResponse(**response)

    async def register_arm(
        self,
        request: RegisterArmRequest,
        timeout: float | None = None,
    ) -> RegisterArmResponse:
        """
        Update what the orchestrator knows about an arm.

        This deliberately **cannot introduce an arm**: an unknown `arm_id` is refused
        with 403. An endpoint that let a caller add an arm to the routing table would
        be a privilege escalation with extra steps, because the orchestrator is the
        sole signing authority for capability tokens -- an arm it can be told about is
        an arm it can be told to trust. Dynamic registration arrives in Stage 5, gated
        on an orchestrator-issued token.

        An omitted field is left alone rather than cleared, and `base_url`, `port`,
        `endpoint` and `cost_tier` cannot be set at all: they are roster facts, and a
        caller able to restate where an arm listens could redirect that arm's traffic
        to a host it controls.

        Requires a bearer token, and the endpoint is **disabled** unless the
        orchestrator has one configured -- construct this client with
        `bearer_token=...`.

        Args:
            request: The arm id and the fields to update.
            timeout: Request timeout in seconds

        Returns:
            RegisterArmResponse with the arm as the registry now holds it

        Raises:
            ServiceUnavailableError: Registration is not enabled on this deployment.
            AuthenticationError: The bearer token is absent or wrong.
            AuthorizationError: The arm id is not in the roster.

        Example:
            >>> from octollm_sdk import RegisterArmRequest
            >>> response = await client.register_arm(
            ...     RegisterArmRequest(arm_id="planner", implemented=True)
            ... )
            >>> print(response.arm.status)
            healthy
        """
        response = await self.post(
            "/arms/register",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return RegisterArmResponse(**response)

    async def _make_plain_text_request(self, method: str, path: str, timeout: float | None) -> str:
        """Helper for plain text responses (metrics endpoint)."""
        import httpx

        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        request_timeout = timeout or self.timeout

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                timeout=request_timeout,
            )
            response.raise_for_status()
            return response.text
