"""
Reflex Layer HTTP Client

This module provides an async HTTP client for communicating with the Reflex Layer service.
It includes retry logic, circuit breaker pattern, and comprehensive error handling.

Example usage:
    from app.reflex_client import ReflexClient

    client = ReflexClient(base_url="http://reflex-layer:8080")
    response = await client.process("Find bugs in auth.py")

    if response.pii_detected:
        print("PII detected:", response.pii_matches)
    if response.injection_detected:
        print("Injection attempt blocked")
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, cast

import httpx
import structlog
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class ProcessStatus(str, Enum):
    """Status of text processing by Reflex Layer."""

    SUCCESS = "Success"
    BLOCKED = "Blocked"
    ERROR = "Error"


class PIIMatch(BaseModel):
    """Details of a detected PII match."""

    pii_type: str = Field(..., description="Type of PII (Email, SSN, CreditCard, etc.)")
    value: str = Field(..., description="Matched PII value")
    position: int = Field(..., description="Character position in text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    context: str = Field(..., description="Surrounding context")


class ContextAnalysis(BaseModel):
    """Context analysis for injection detection."""

    is_quoted: bool = Field(False, description="Pattern appears in quotes")
    is_academic: bool = Field(False, description="Pattern in academic/discussion context")
    is_testing: bool = Field(False, description="Pattern in testing context")
    is_negation: bool = Field(False, description="Pattern used in negation")


class InjectionMatch(BaseModel):
    """Details of a detected injection attempt."""

    injection_type: str = Field(..., description="Type of injection detected")
    severity: str = Field(..., description="Severity level (Critical, High, Medium, Low)")
    matched_text: str = Field(..., description="Text that matched the pattern")
    position: int = Field(..., description="Character position in text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    context_analysis: ContextAnalysis = Field(
        default_factory=lambda: ContextAnalysis(), description="Contextual analysis"
    )


class ReflexRequest(BaseModel):
    """Request payload for Reflex Layer processing."""

    text: str = Field(..., min_length=1, max_length=100000, description="Text to process")
    user_id: str | None = Field(None, description="Optional user identifier for rate limiting")
    context: dict[str, Any] | None = Field(default_factory=dict, description="Additional context")

    @field_validator("text")
    @classmethod
    def validate_text_not_empty(cls, v: str) -> str:
        """Ensure text is not just whitespace."""
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v


class ReflexResponse(BaseModel):
    """Response from Reflex Layer processing."""

    request_id: str = Field(..., description="Unique request identifier")
    status: ProcessStatus = Field(..., description="Processing status")
    pii_detected: bool = Field(..., description="Whether PII was detected")
    pii_matches: list[PIIMatch] = Field(default_factory=list, description="List of PII matches")
    injection_detected: bool = Field(..., description="Whether injection was detected")
    injection_matches: list[InjectionMatch] = Field(
        default_factory=list, description="List of injection matches"
    )
    cache_hit: bool = Field(..., description="Whether result was from cache")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")

    @property
    def is_safe(self) -> bool:
        """Check if the text is safe to process (no PII, no injection)."""
        return not self.pii_detected and not self.injection_detected

    @property
    def is_blocked(self) -> bool:
        """Check if the request was blocked."""
        return self.status == ProcessStatus.BLOCKED


class ReflexClientError(Exception):
    """Base exception for Reflex client errors."""

    pass


class ReflexServiceUnavailable(ReflexClientError):
    """Raised when Reflex service is unavailable."""

    pass


class ReflexCircuitBreakerOpen(ReflexClientError):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """Circuit breaker implementation to prevent cascading failures."""

    def __init__(
        self, failure_threshold: int = 5, reset_timeout: int = 60, half_open_attempts: int = 3
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            reset_timeout: Seconds to wait before attempting to close circuit
            half_open_attempts: Number of successful requests needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_attempts = half_open_attempts

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """Decorator to wrap function calls with circuit breaker."""

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                    logger.info("circuit_breaker.half_open", threshold=self.failure_threshold)
                else:
                    raise ReflexCircuitBreakerOpen(
                        f"Circuit breaker is open. Try again after {self.reset_timeout}s"
                    )

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e

        return wrapper

    def _on_success(self) -> None:
        """Handle successful request."""
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.half_open_attempts:
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
                logger.info("circuit_breaker.closed", reason="successful_recovery")
        elif self.state == "closed":
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        self.success_count = 0

        if self.state == "half-open":
            self.state = "open"
            logger.warning("circuit_breaker.open", reason="half_open_failure")
        elif self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "circuit_breaker.open",
                reason="failure_threshold_exceeded",
                count=self.failure_count,
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        elapsed = datetime.now(UTC) - self.last_failure_time
        return elapsed > timedelta(seconds=self.reset_timeout)

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("circuit_breaker.reset", reason="manual")


class ReflexClient:
    """
    Async HTTP client for Reflex Layer service.

    Features:
    - Retry logic with exponential backoff
    - Circuit breaker pattern to prevent cascading failures
    - Request/response validation with Pydantic
    - Comprehensive error handling
    - Metrics collection (request count, latency, errors)
    """

    def __init__(
        self,
        base_url: str = "http://reflex-layer:8080",
        timeout: float = 10.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_reset_timeout: int = 60,
    ):
        """
        Initialize Reflex client.

        Args:
            base_url: Base URL of Reflex Layer service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            circuit_breaker_threshold: Failures before circuit breaker opens
            circuit_breaker_reset_timeout: Seconds before attempting to reset circuit
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            reset_timeout=circuit_breaker_reset_timeout,
        )

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "blocked_requests": 0,
            "pii_detections": 0,
            "injection_detections": 0,
            "cache_hits": 0,
            "total_latency_ms": 0.0,
        }

        logger.info(
            "reflex_client.initialized",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _make_request(self, request: ReflexRequest) -> ReflexResponse:
        """
        Make HTTP request to Reflex Layer with retry logic.

        Args:
            request: Reflex request payload

        Returns:
            Reflex response

        Raises:
            httpx.RequestError: Network-related errors
            httpx.HTTPStatusError: HTTP error status codes
        """
        start_time = datetime.now(UTC)

        try:
            response = await self.client.post(
                f"{self.base_url}/process",
                json=request.model_dump(exclude_none=True),
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()

            # Parse response
            data = response.json()
            reflex_response = ReflexResponse(**data)

            # Update metrics
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self._update_metrics(reflex_response, latency_ms)

            logger.info(
                "reflex_client.request_success",
                request_id=reflex_response.request_id,
                status=reflex_response.status,
                pii_detected=reflex_response.pii_detected,
                injection_detected=reflex_response.injection_detected,
                latency_ms=latency_ms,
            )

            return reflex_response

        except httpx.HTTPStatusError as e:
            logger.error(
                "reflex_client.http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            self.metrics["failed_requests"] += 1
            raise

        except httpx.RequestError as e:
            logger.error("reflex_client.request_error", error=str(e))
            self.metrics["failed_requests"] += 1
            raise

    async def process(
        self, text: str, user_id: str | None = None, context: dict[str, Any] | None = None
    ) -> ReflexResponse:
        """
        Process text through Reflex Layer.

        Args:
            text: Text to process
            user_id: Optional user identifier for rate limiting
            context: Additional context

        Returns:
            Reflex response with PII and injection detection results

        Raises:
            ReflexCircuitBreakerOpen: Circuit breaker is open
            ReflexServiceUnavailable: Service is unavailable after retries
            ValueError: Invalid input
        """
        # Validate input
        request = ReflexRequest(text=text, user_id=user_id, context=context or {})

        self.metrics["total_requests"] += 1

        # Apply circuit breaker
        @self.circuit_breaker.call
        async def _execute() -> ReflexResponse:
            return cast(ReflexResponse, await self._make_request(request))

        try:
            response = await cast(Callable[[], Awaitable[ReflexResponse]], _execute)()
            self.metrics["successful_requests"] += 1
            return response

        except ReflexCircuitBreakerOpen:
            logger.error("reflex_client.circuit_breaker_open")
            raise

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error("reflex_client.service_unavailable", error=str(e))
            raise ReflexServiceUnavailable(f"Reflex Layer unavailable: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if Reflex Layer service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=httpx.Timeout(5.0))
            is_healthy: bool = response.status_code == 200

            logger.info(
                "reflex_client.health_check",
                healthy=is_healthy,
                status_code=response.status_code,
            )

            return is_healthy

        except Exception as e:
            logger.error("reflex_client.health_check_failed", error=str(e))
            return False

    async def ready_check(self) -> bool:
        """
        Check if Reflex Layer service is ready to accept requests.

        Returns:
            True if service is ready, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/ready", timeout=httpx.Timeout(5.0))
            is_ready: bool = response.status_code == 200

            logger.info(
                "reflex_client.ready_check", ready=is_ready, status_code=response.status_code
            )

            return is_ready

        except Exception as e:
            logger.error("reflex_client.ready_check_failed", error=str(e))
            return False

    def get_metrics(self) -> dict[str, Any]:
        """
        Get client metrics.

        Returns:
            Dictionary of metrics
        """
        avg_latency_ms = (
            self.metrics["total_latency_ms"] / self.metrics["total_requests"]
            if self.metrics["total_requests"] > 0
            else 0.0
        )

        return {
            **self.metrics,
            "average_latency_ms": avg_latency_ms,
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0
                else 0.0
            ),
            "circuit_breaker_state": self.circuit_breaker.state,
            "circuit_breaker_failure_count": self.circuit_breaker.failure_count,
        }

    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker."""
        self.circuit_breaker.reset()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("reflex_client.closed")

    async def __aenter__(self) -> "ReflexClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    def _update_metrics(self, response: ReflexResponse, latency_ms: float) -> None:
        """Update internal metrics."""
        self.metrics["total_latency_ms"] += latency_ms

        if response.is_blocked:
            self.metrics["blocked_requests"] += 1

        if response.pii_detected:
            self.metrics["pii_detections"] += 1

        if response.injection_detected:
            self.metrics["injection_detections"] += 1

        if response.cache_hit:
            self.metrics["cache_hits"] += 1
