# Error Handling Patterns

**Last Updated**: 2025-11-10
**Status**: Production Standard
**Applies To**: All OctoLLM components

## Overview

This document defines error handling patterns and best practices for the OctoLLM project. Proper error handling ensures system reliability, debugging effectiveness, and graceful degradation under failure conditions.

## Table of Contents

- [Error Hierarchy](#error-hierarchy)
- [Python Error Patterns](#python-error-patterns)
- [Rust Error Patterns](#rust-error-patterns)
- [HTTP Error Responses](#http-error-responses)
- [Circuit Breaker Pattern](#circuit-breaker-pattern)
- [Retry Logic](#retry-logic)
- [Error Logging](#error-logging)
- [Error Recovery](#error-recovery)

---

## Error Hierarchy

### OctoLLM Error Classification

```
OctoLLMError (base)
├── ValidationError (4xx client errors)
│   ├── InvalidInputError
│   ├── TaskNotFoundError
│   ├── AuthenticationError
│   └── AuthorizationError
├── ResourceError (4xx resource issues)
│   ├── ArmUnavailableError
│   ├── CapacityExceededError
│   └── RateLimitError
├── SystemError (5xx server errors)
│   ├── DatabaseError
│   ├── CacheError
│   ├── NetworkError
│   └── TimeoutError
└── ExternalError (5xx external service errors)
    ├── LLMAPIError
    ├── VectorDBError
    └── ThirdPartyAPIError
```

### Error Severity Levels

1. **DEBUG**: Diagnostic information
2. **INFO**: Normal operation events
3. **WARNING**: Degraded operation, non-critical
4. **ERROR**: Operation failed, requires attention
5. **CRITICAL**: System failure, immediate action required

---

## Python Error Patterns

### Custom Exception Hierarchy

```python
# octollm/errors.py
class OctoLLMError(Exception):
    """Base exception for all OctoLLM errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.retry_after = retry_after

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        result = {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }
        if self.retry_after:
            result["retry_after"] = self.retry_after
        return result


# Validation errors (4xx)
class ValidationError(OctoLLMError):
    """Client provided invalid input."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {},
            **kwargs
        )


class InvalidInputError(ValidationError):
    """Input failed validation."""
    pass


class TaskNotFoundError(ValidationError):
    """Requested task does not exist."""

    def __init__(self, task_id: str):
        super().__init__(
            f"Task {task_id} not found",
            error_code="TASK_NOT_FOUND",
            details={"task_id": task_id}
        )


# Resource errors (4xx)
class ResourceError(OctoLLMError):
    """Resource unavailable or exhausted."""
    pass


class ArmUnavailableError(ResourceError):
    """No suitable arm available for task."""

    def __init__(self, required_capabilities: List[str]):
        super().__init__(
            f"No arm available with capabilities: {', '.join(required_capabilities)}",
            error_code="ARM_UNAVAILABLE",
            details={"required_capabilities": required_capabilities}
        )


class RateLimitError(ResourceError):
    """Rate limit exceeded."""

    def __init__(self, limit: int, window: int, retry_after: int):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}s",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window": window},
            retry_after=retry_after
        )


# System errors (5xx)
class SystemError(OctoLLMError):
    """Internal system error."""
    pass


class DatabaseError(SystemError):
    """Database operation failed."""

    def __init__(self, operation: str, original_error: Exception):
        super().__init__(
            f"Database {operation} failed: {str(original_error)}",
            error_code="DATABASE_ERROR",
            details={"operation": operation, "error": str(original_error)}
        )


class TimeoutError(SystemError):
    """Operation timed out."""

    def __init__(self, operation: str, timeout: int):
        super().__init__(
            f"{operation} timed out after {timeout}s",
            error_code="TIMEOUT_ERROR",
            details={"operation": operation, "timeout": timeout}
        )


# External service errors (5xx)
class ExternalError(OctoLLMError):
    """External service error."""
    pass


class LLMAPIError(ExternalError):
    """LLM API call failed."""

    def __init__(
        self,
        provider: str,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        super().__init__(
            f"{provider} API error: {error_message or 'Unknown error'}",
            error_code="LLM_API_ERROR",
            details={
                "provider": provider,
                "status_code": status_code,
                "error_message": error_message
            }
        )
```

### Error Handling Patterns

**Pattern 1: Try-Except with Specific Exceptions**

```python
async def get_task(task_id: str) -> TaskContract:
    """Retrieve task with proper error handling."""
    try:
        task = await db.query("SELECT * FROM tasks WHERE id = $1", task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        return TaskContract(**task)

    except asyncpg.PostgresConnectionError as e:
        logger.error("Database connection failed", error=str(e))
        raise DatabaseError("query", e) from e

    except asyncpg.PostgresError as e:
        logger.error("Database query failed", error=str(e))
        raise DatabaseError("query", e) from e

    except Exception as e:
        logger.error("Unexpected error retrieving task", error=str(e), exc_info=True)
        raise SystemError(f"Failed to retrieve task: {str(e)}") from e
```

**Pattern 2: Context Managers for Resource Cleanup**

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def database_transaction(
    db: Database
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide database transaction with automatic rollback on error."""
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            try:
                yield conn
            except Exception as e:
                logger.error("Transaction failed, rolling back", error=str(e))
                # Transaction automatically rolled back
                raise

# Usage
async def update_task_status(task_id: str, status: str):
    async with database_transaction(db) as conn:
        await conn.execute(
            "UPDATE tasks SET status = $1 WHERE id = $2",
            status, task_id
        )
        await conn.execute(
            "INSERT INTO task_history (task_id, status) VALUES ($1, $2)",
            task_id, status
        )
```

**Pattern 3: Validation with Early Returns**

```python
def validate_task_contract(task: TaskContract) -> None:
    """Validate task contract, raising specific errors."""
    if not task.description:
        raise InvalidInputError(
            "Task description is required",
            field="description"
        )

    if not task.description.strip():
        raise InvalidInputError(
            "Task description cannot be empty",
            field="description"
        )

    if len(task.description) > 10000:
        raise InvalidInputError(
            "Task description exceeds maximum length of 10000 characters",
            field="description"
        )

    if task.priority < 1 or task.priority > 10:
        raise InvalidInputError(
            "Task priority must be between 1 and 10",
            field="priority"
        )

    if task.timeout and task.timeout <= 0:
        raise InvalidInputError(
            "Task timeout must be positive",
            field="timeout"
        )
```

**Pattern 4: Error Aggregation**

```python
from typing import List, Dict

class ValidationErrors(ValidationError):
    """Multiple validation errors."""

    def __init__(self, errors: List[Dict[str, str]]):
        message = f"Validation failed with {len(errors)} errors"
        super().__init__(
            message,
            error_code="VALIDATION_ERRORS",
            details={"errors": errors}
        )


def validate_task_comprehensive(task: TaskContract) -> None:
    """Collect all validation errors before raising."""
    errors = []

    if not task.description:
        errors.append({
            "field": "description",
            "message": "Description is required"
        })
    elif len(task.description) > 10000:
        errors.append({
            "field": "description",
            "message": "Description exceeds maximum length"
        })

    if task.priority < 1 or task.priority > 10:
        errors.append({
            "field": "priority",
            "message": "Priority must be between 1 and 10"
        })

    if task.timeout and task.timeout <= 0:
        errors.append({
            "field": "timeout",
            "message": "Timeout must be positive"
        })

    if errors:
        raise ValidationErrors(errors)
```

---

## Rust Error Patterns

### Error Definition with thiserror

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ReflexError {
    #[error("PII detected: {pattern}")]
    PiiDetected { pattern: String },

    #[error("Rate limit exceeded: {limit} req/s")]
    RateLimitExceeded { limit: u32 },

    #[error("Invalid input: {message}")]
    InvalidInput { message: String },

    #[error("Cache error: {0}")]
    CacheError(#[from] redis::RedisError),

    #[error("Network error: {0}")]
    NetworkError(#[from] reqwest::Error),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("Internal error: {0}")]
    Internal(String),
}

// Implement conversion to HTTP status codes
impl ReflexError {
    pub fn status_code(&self) -> u16 {
        match self {
            ReflexError::PiiDetected { .. } => 400,
            ReflexError::RateLimitExceeded { .. } => 429,
            ReflexError::InvalidInput { .. } => 400,
            ReflexError::CacheError(_) => 500,
            ReflexError::NetworkError(_) => 502,
            ReflexError::SerializationError(_) => 500,
            ReflexError::Internal(_) => 500,
        }
    }

    pub fn error_code(&self) -> &str {
        match self {
            ReflexError::PiiDetected { .. } => "PII_DETECTED",
            ReflexError::RateLimitExceeded { .. } => "RATE_LIMIT_EXCEEDED",
            ReflexError::InvalidInput { .. } => "INVALID_INPUT",
            ReflexError::CacheError(_) => "CACHE_ERROR",
            ReflexError::NetworkError(_) => "NETWORK_ERROR",
            ReflexError::SerializationError(_) => "SERIALIZATION_ERROR",
            ReflexError::Internal(_) => "INTERNAL_ERROR",
        }
    }
}
```

### Error Handling Patterns

**Pattern 1: Result Propagation with ?**

```rust
async fn preprocess(input: &str) -> Result<String, ReflexError> {
    // Detect PII - propagates error if found
    let sanitized = detect_pii(input)?;

    // Check rate limit - propagates error if exceeded
    rate_limiter.check()?;

    // Get from cache - propagates redis error
    let cached = cache.get(&sanitized).await?;

    Ok(cached.unwrap_or_else(|| sanitized))
}
```

**Pattern 2: Error Conversion with map_err**

```rust
async fn fetch_from_api(url: &str) -> Result<String, ReflexError> {
    let response = reqwest::get(url)
        .await
        .map_err(|e| ReflexError::NetworkError(e))?;

    let text = response
        .text()
        .await
        .map_err(|e| ReflexError::NetworkError(e))?;

    Ok(text)
}
```

**Pattern 3: Error Recovery with or_else**

```rust
async fn get_with_fallback(key: &str) -> Result<String, ReflexError> {
    // Try primary cache
    match cache_primary.get(key).await {
        Ok(value) => Ok(value),
        Err(_) => {
            // Fallback to secondary cache
            cache_secondary.get(key).await
                .map_err(|e| ReflexError::CacheError(e))
        }
    }
}
```

**Pattern 4: Custom Error Context**

```rust
use anyhow::{Context, Result};

async fn process_task(task_id: &str) -> Result<String> {
    let task = db.get_task(task_id)
        .await
        .context(format!("Failed to fetch task {}", task_id))?;

    let result = execute_task(&task)
        .await
        .context(format!("Failed to execute task {}", task_id))?;

    Ok(result)
}
```

---

## HTTP Error Responses

### FastAPI Error Handling

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI()

# Custom exception handler
@app.exception_handler(OctoLLMError)
async def octollm_error_handler(
    request: Request,
    exc: OctoLLMError
) -> JSONResponse:
    """Handle all OctoLLM errors."""
    status_code = get_status_code(exc)

    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
        headers=get_retry_headers(exc)
    )


def get_status_code(exc: OctoLLMError) -> int:
    """Map exception to HTTP status code."""
    if isinstance(exc, ValidationError):
        return status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, TaskNotFoundError):
        return status.HTTP_404_NOT_FOUND
    elif isinstance(exc, AuthenticationError):
        return status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AuthorizationError):
        return status.HTTP_403_FORBIDDEN
    elif isinstance(exc, RateLimitError):
        return status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, (ResourceError, ArmUnavailableError)):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        return status.HTTP_500_INTERNAL_SERVER_ERROR


def get_retry_headers(exc: OctoLLMError) -> Dict[str, str]:
    """Get retry-related headers."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    return headers


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": errors}
        }
    )


# Generic exception handler (catch-all)
@app.exception_handler(Exception)
async def generic_error_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected errors."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )

    # Don't expose internal errors to clients
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "details": {}
        }
    )
```

### Standard Error Response Format

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "task_id",
    "additional_context": "value"
  },
  "retry_after": 60
}
```

---

## Circuit Breaker Pattern

### Python Implementation

```python
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering half-open state")
            else:
                raise SystemError(
                    f"Circuit breaker is open, retry after {self.timeout}s"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None
            and datetime.now() - self.last_failure_time
            > timedelta(seconds=self.timeout)
        )

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker closed after successful test")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )


# Usage
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60,
    expected_exception=LLMAPIError
)

async def call_llm_api(prompt: str) -> str:
    """Call LLM API with circuit breaker."""
    return await llm_circuit_breaker.call(
        _call_llm_api_internal,
        prompt
    )
```

---

## Retry Logic

### Python Retry with Exponential Backoff

```python
import asyncio
import random
from typing import TypeVar, Callable, Optional

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple = (Exception,),
) -> T:
    """Retry function with exponential backoff."""
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()

        except retry_on as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    "Max retries exceeded",
                    attempt=attempt,
                    error=str(e)
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(
                base_delay * (exponential_base ** attempt),
                max_delay
            )

            # Add jitter to prevent thundering herd
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                "Retrying after failure",
                attempt=attempt,
                delay=delay,
                error=str(e)
            )

            await asyncio.sleep(delay)

    raise last_exception


# Usage
async def call_external_api():
    return await retry_with_backoff(
        lambda: httpx.get("https://api.example.com"),
        max_retries=5,
        base_delay=1.0,
        retry_on=(httpx.HTTPError, httpx.TimeoutException)
    )
```

### Rust Retry Pattern

```rust
use tokio::time::{sleep, Duration};
use std::cmp::min;

pub async fn retry_with_backoff<F, Fut, T, E>(
    mut func: F,
    max_retries: u32,
    base_delay: Duration,
) -> Result<T, E>
where
    F: FnMut() -> Fut,
    Fut: Future<Output = Result<T, E>>,
{
    let mut attempts = 0;

    loop {
        match func().await {
            Ok(result) => return Ok(result),
            Err(e) => {
                attempts += 1;

                if attempts > max_retries {
                    return Err(e);
                }

                let delay = min(
                    base_delay * 2_u32.pow(attempts - 1),
                    Duration::from_secs(60),
                );

                tracing::warn!(
                    "Retry attempt {} after {:?}",
                    attempts,
                    delay
                );

                sleep(delay).await;
            }
        }
    }
}
```

---

## Error Logging

### Structured Error Logging

```python
import structlog

logger = structlog.get_logger(__name__)

async def process_task(task: TaskContract) -> str:
    """Process task with comprehensive error logging."""
    try:
        logger.info(
            "task.processing.started",
            task_id=task.task_id,
            priority=task.priority
        )

        result = await execute_task(task)

        logger.info(
            "task.processing.completed",
            task_id=task.task_id,
            duration_ms=result.duration
        )

        return result.output

    except TaskNotFoundError as e:
        logger.warning(
            "task.processing.not_found",
            task_id=task.task_id,
            error=str(e)
        )
        raise

    except ArmUnavailableError as e:
        logger.error(
            "task.processing.arm_unavailable",
            task_id=task.task_id,
            required_capabilities=e.details.get("required_capabilities"),
            error=str(e)
        )
        raise

    except Exception as e:
        logger.critical(
            "task.processing.unexpected_error",
            task_id=task.task_id,
            error=str(e),
            exc_info=True  # Include stack trace
        )
        raise
```

### Error Metrics

```python
from prometheus_client import Counter, Histogram

# Error counters
error_counter = Counter(
    'octollm_errors_total',
    'Total errors by type',
    ['error_type', 'component']
)

# Error duration
error_duration = Histogram(
    'octollm_error_duration_seconds',
    'Time to detect and handle error',
    ['error_type']
)

async def track_errors(func):
    """Decorator to track errors in metrics."""
    start_time = time.time()

    try:
        return await func()
    except OctoLLMError as e:
        error_counter.labels(
            error_type=e.error_code,
            component="orchestrator"
        ).inc()

        error_duration.labels(
            error_type=e.error_code
        ).observe(time.time() - start_time)
        raise
```

---

## Error Recovery

### Graceful Degradation

```python
async def get_task_with_fallback(task_id: str) -> TaskContract:
    """Get task with fallback to read replica."""
    try:
        # Try primary database
        return await db_primary.get_task(task_id)
    except DatabaseError:
        logger.warning(
            "Primary database failed, trying read replica",
            task_id=task_id
        )
        try:
            # Fallback to read replica
            return await db_replica.get_task(task_id)
        except DatabaseError:
            logger.error(
                "Both primary and replica failed",
                task_id=task_id
            )
            raise
```

### Partial Success Handling

```python
from typing import List, Tuple

async def execute_batch_tasks(
    tasks: List[TaskContract]
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Execute batch of tasks, collecting successes and failures."""
    successes = []
    failures = []

    for task in tasks:
        try:
            result = await execute_task(task)
            successes.append(result)
        except Exception as e:
            logger.error(
                "Task execution failed",
                task_id=task.task_id,
                error=str(e)
            )
            failures.append({
                "task_id": task.task_id,
                "error": str(e),
                "error_code": getattr(e, 'error_code', 'UNKNOWN_ERROR')
            })

    return successes, failures
```

---

## Best Practices Summary

1. **Use specific exceptions**: Don't catch generic `Exception` unless necessary
2. **Preserve error context**: Use `raise ... from e` to maintain error chain
3. **Log before raising**: Log errors with context before propagating
4. **Fail fast**: Validate inputs early and fail with clear messages
5. **Graceful degradation**: Provide fallbacks for non-critical failures
6. **Circuit breakers**: Protect against cascading failures
7. **Retry intelligently**: Use exponential backoff with jitter
8. **Monitor errors**: Track error rates and types in metrics
9. **Document errors**: Document what errors functions can raise
10. **Test error paths**: Write tests for error conditions

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Engineering Team
