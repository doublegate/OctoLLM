"""
HTTP client for calling the Planner Arm service.

Provides async interface for requesting execution plans from the Planner Arm,
with retry logic, circuit breaker pattern, and structured logging.
"""

from typing import Any

import httpx
import structlog
from prometheus_client import Counter, Histogram
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger(__name__)

# ==============================================================================
# Prometheus Metrics
# ==============================================================================

PLANNER_REQUEST_COUNTER = Counter(
    "orchestrator_planner_requests_total",
    "Total number of Planner Arm requests",
    ["status"],
)

PLANNER_LATENCY_HISTOGRAM = Histogram(
    "orchestrator_planner_latency_seconds",
    "Planner Arm request latency in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)


# ==============================================================================
# Exceptions
# ==============================================================================


class PlannerServiceError(Exception):
    """Base exception for Planner Arm service errors."""

    pass


class PlannerServiceUnavailable(PlannerServiceError):
    """Raised when Planner Arm service is unavailable."""

    pass


class PlannerCircuitBreakerOpen(PlannerServiceError):
    """Raised when circuit breaker is open."""

    pass


# ==============================================================================
# Circuit Breaker
# ==============================================================================


class CircuitBreaker:
    """
    Simple circuit breaker for Planner Arm calls.

    Opens after threshold failures, prevents requests for reset timeout.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def record_success(self) -> None:
        """Record successful request."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        """Record failed request."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "planner_circuit_breaker.opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        import time

        if self.state == "closed":
            return False

        # Check if reset timeout has passed
        if time.time() - self.last_failure_time > self.reset_timeout:
            self.state = "half-open"
            self.failure_count = 0
            logger.info("planner_circuit_breaker.half_open")
            return False

        return True


# ==============================================================================
# Planner Client
# ==============================================================================


class PlannerClient:
    """
    HTTP client for Planner Arm service.

    Provides async methods for requesting execution plans with retry logic,
    circuit breaker, and observability.
    """

    def __init__(self) -> None:
        """Initialize Planner client with settings."""
        settings = get_settings()
        self.base_url = settings.planner_arm_url
        self.timeout = settings.planner_arm_timeout
        self.max_retries = settings.planner_arm_max_retries

        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.planner_arm_circuit_breaker_threshold,
            reset_timeout=settings.planner_arm_circuit_breaker_reset_timeout,
        )

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

        logger.info(
            "planner_client.initialized",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    async def create_plan(
        self,
        goal: str,
        constraints: list[str],
        context: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Request execution plan from Planner Arm.

        Args:
            goal: Natural language description of what to accomplish
            constraints: List of hard constraints
            context: Additional background information
            request_id: Optional request ID for tracing

        Returns:
            Plan response dictionary with subtasks and metadata

        Raises:
            PlannerCircuitBreakerOpen: If circuit breaker is open
            PlannerServiceUnavailable: If service is unavailable
            PlannerServiceError: For other service errors
        """
        # Check circuit breaker
        if self.circuit_breaker.is_open():
            PLANNER_REQUEST_COUNTER.labels(status="circuit_open").inc()
            raise PlannerCircuitBreakerOpen("Planner Arm circuit breaker is open")

        logger.info(
            "planner_client.request",
            goal=goal[:100],
            constraints_count=len(constraints),
            request_id=request_id,
        )

        try:
            with PLANNER_LATENCY_HISTOGRAM.time():
                response = await self._make_request(
                    goal=goal,
                    constraints=constraints,
                    context=context,
                    request_id=request_id,
                )

            self.circuit_breaker.record_success()
            PLANNER_REQUEST_COUNTER.labels(status="success").inc()

            logger.info(
                "planner_client.success",
                steps=len(response.get("plan", [])),
                request_id=request_id,
            )

            return response

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            self.circuit_breaker.record_failure()
            PLANNER_REQUEST_COUNTER.labels(status="unavailable").inc()
            logger.error(
                "planner_client.unavailable",
                error=str(e),
                request_id=request_id,
            )
            raise PlannerServiceUnavailable(f"Planner Arm service unavailable: {e}") from e

        except httpx.HTTPStatusError as e:
            self.circuit_breaker.record_failure()
            PLANNER_REQUEST_COUNTER.labels(status=f"http_{e.response.status_code}").inc()
            logger.error(
                "planner_client.http_error",
                status_code=e.response.status_code,
                error=str(e),
                request_id=request_id,
            )
            raise PlannerServiceError(f"Planner Arm HTTP error: {e}") from e

        except Exception as e:
            self.circuit_breaker.record_failure()
            PLANNER_REQUEST_COUNTER.labels(status="error").inc()
            logger.error(
                "planner_client.error",
                error=str(e),
                request_id=request_id,
            )
            raise PlannerServiceError(f"Planner Arm error: {e}") from e

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _make_request(
        self,
        goal: str,
        constraints: list[str],
        context: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Make HTTP request to Planner Arm with retry logic.

        Args:
            goal: Task goal
            constraints: Task constraints
            context: Task context
            request_id: Optional request ID

        Returns:
            Plan response dictionary

        Raises:
            httpx.HTTPStatusError: For non-2xx status codes
            httpx.TimeoutException: For timeout errors
            httpx.ConnectError: For connection errors
        """
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        response = await self.client.post(
            "/plan",
            json={
                "goal": goal,
                "constraints": constraints,
                "context": context,
                "request_id": request_id,
            },
            headers=headers,
        )

        response.raise_for_status()
        return response.json()

    async def health_check(self) -> dict[str, Any]:
        """
        Check Planner Arm service health.

        Returns:
            Health check response

        Raises:
            PlannerServiceError: If health check fails
        """
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error("planner_client.health_check.error", error=str(e))
            raise PlannerServiceError(f"Health check failed: {e}") from e

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.info("planner_client.closed")


# ==============================================================================
# Global Client Instance
# ==============================================================================

_planner_client: PlannerClient | None = None


def get_planner_client() -> PlannerClient:
    """
    Get global PlannerClient instance.

    Returns:
        PlannerClient instance
    """
    global _planner_client
    if _planner_client is None:
        _planner_client = PlannerClient()
    return _planner_client
