# Phase 4: Additional Documentation - Complete Specifications

**Phase Status**: Complete
**Date Completed**: 2025-11-10
**Total Documents**: 13 (5 engineering practices + 3 guides + 5 ADRs)

This document consolidates all Phase 4 documentation including engineering practices, development guides, and architectural decision records.

---

## Table of Contents

1. [Engineering Practices](#engineering-practices)
   - [Coding Standards](#coding-standards)
   - [Error Handling](#error-handling)
   - [Logging and Observability](#logging-and-observability)
   - [Performance Optimization](#performance-optimization)
   - [Code Review](#code-review)

2. [Development Guides](#development-guides)
   - [Development Workflow](#development-workflow)
   - [Migration Guide](#migration-guide)
   - [Contributing Guidelines](#contributing-guidelines)

3. [Architecture Decision Records](#architecture-decision-records)
   - [ADR-001: Technology Stack](#adr-001-technology-stack)
   - [ADR-002: Communication Patterns](#adr-002-communication-patterns)
   - [ADR-003: Memory Architecture](#adr-003-memory-architecture)
   - [ADR-004: Security Model](#adr-004-security-model)
   - [ADR-005: Deployment Platform](#adr-005-deployment-platform)

---

## Engineering Practices

### Coding Standards

**Location**: `/docs/engineering/coding-standards.md`

**Purpose**: Define consistent coding standards for Python and Rust codebases.

#### Python Standards

**Style Guide**: PEP 8 compliance with modifications
- **Line Length**: 100 characters (Black default)
- **Indentation**: 4 spaces
- **Imports**: Organized by stdlib, third-party, local (isort)
- **Quotes**: Double quotes for strings
- **Type Hints**: Required for all function signatures

**Tools Configuration**:
```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
select = ["E", "F", "I", "B", "C4", "UP", "ARG", "SIM"]
ignore = ["E501"]  # Line too long (handled by Black)

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

**Code Example - Type Hints**:
```python
from typing import List, Dict, Optional, Any
from datetime import datetime

async def execute_task(
    task_id: str,
    parameters: Dict[str, Any],
    timeout: int = 300
) -> TaskResult:
    """Execute a task with given parameters.

    Args:
        task_id: Unique identifier for the task
        parameters: Task-specific parameters
        timeout: Maximum execution time in seconds

    Returns:
        TaskResult containing output and metadata

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        TaskTimeoutError: If execution exceeds timeout
        TaskExecutionError: If task fails to execute
    """
    try:
        task = await db.get_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        result = await orchestrator.execute(task, parameters, timeout)
        return result
    except asyncio.TimeoutError:
        raise TaskTimeoutError(f"Task {task_id} timed out after {timeout}s")
    except Exception as e:
        logger.error("Task execution failed", task_id=task_id, error=str(e))
        raise TaskExecutionError(f"Failed to execute task: {e}") from e
```

**Function Documentation**:
```python
def create_capability_token(
    user_id: str,
    task_id: str,
    capabilities: Dict[str, List[str]],
    expiry_minutes: int = 30
) -> str:
    """Create a capability token for task execution.

    This function generates a JWT token with specific capability scopes
    that authorize the bearer to perform certain operations. The token
    expires after the specified duration.

    Args:
        user_id: Identifier of the user requesting the token
        task_id: Identifier of the task being authorized
        capabilities: Dictionary mapping capability types to allowed resources
            Example: {"task:read": ["task-123"], "arm:invoke": ["coder"]}
        expiry_minutes: Token validity period in minutes (default: 30)

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_capability_token(
        ...     "user-123",
        ...     "task-456",
        ...     {"task:read": ["task-456"], "arm:invoke": ["coder"]},
        ...     expiry_minutes=60
        ... )
        >>> print(token[:20])
        eyJhbGciOiJIUzI1NiI...
    """
    payload = {
        "sub": user_id,
        "iss": "octollm-orchestrator",
        "exp": datetime.utcnow() + timedelta(minutes=expiry_minutes),
        "capabilities": capabilities,
        "context": {
            "task_id": task_id,
            "user_id": user_id
        }
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

#### Rust Standards

**Style Guide**: Rust standard style (rustfmt)
- **Formatting**: `cargo fmt` with default settings
- **Linting**: `cargo clippy` with all warnings as errors
- **Naming**: snake_case for functions/variables, CamelCase for types
- **Documentation**: Required for public APIs
- **Error Handling**: Use `Result<T, E>` consistently

**Cargo Configuration**:
```toml
[profile.dev]
opt-level = 0
debug = true

[profile.release]
opt-level = 3
lto = true
codegen-units = 1

[profile.test]
opt-level = 1
```

**Code Example - Error Handling**:
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ReflexError {
    #[error("Rate limit exceeded: {limit} requests per {window}s")]
    RateLimitExceeded { limit: u32, window: u32 },

    #[error("PII detected: {pattern}")]
    PiiDetected { pattern: String },

    #[error("Invalid request: {0}")]
    InvalidRequest(String),

    #[error("Internal error: {0}")]
    Internal(#[from] anyhow::Error),
}

pub type ReflexResult<T> = Result<T, ReflexError>;

pub async fn process_request(req: Request) -> ReflexResult<Response> {
    // Validate request
    validate_request(&req)?;

    // Check rate limit
    rate_limiter.check(&req.client_id)
        .map_err(|e| ReflexError::RateLimitExceeded {
            limit: e.limit,
            window: e.window,
        })?;

    // Detect PII
    if let Some(pii) = pii_detector.detect(&req.body) {
        return Err(ReflexError::PiiDetected {
            pattern: pii.pattern_name,
        });
    }

    // Process request
    let response = handle_request(req).await?;
    Ok(response)
}
```

**Documentation Example**:
```rust
/// PII detector for identifying personally identifiable information.
///
/// This detector uses regex patterns to identify common PII types including:
/// - Email addresses
/// - Social Security Numbers (SSN)
/// - Credit card numbers
/// - Phone numbers
///
/// # Examples
///
/// ```
/// use reflex::pii::PiiDetector;
///
/// let detector = PiiDetector::new();
/// let text = "Contact me at john@example.com";
/// let matches = detector.detect(text);
/// assert_eq!(matches.len(), 1);
/// assert_eq!(matches[0].pattern_name, "email");
/// ```
pub struct PiiDetector {
    patterns: Vec<(String, Regex)>,
}

impl PiiDetector {
    /// Creates a new PII detector with default patterns.
    pub fn new() -> Self {
        Self {
            patterns: vec![
                ("email".to_string(), EMAIL.clone()),
                ("ssn".to_string(), SSN.clone()),
                ("credit_card".to_string(), CREDIT_CARD.clone()),
                ("phone".to_string(), PHONE.clone()),
            ]
        }
    }

    /// Detects PII in the given text.
    ///
    /// # Arguments
    ///
    /// * `text` - The text to scan for PII
    ///
    /// # Returns
    ///
    /// A vector of PII matches found in the text
    pub fn detect(&self, text: &str) -> Vec<PiiMatch> {
        let mut matches = Vec::new();
        for (name, pattern) in &self.patterns {
            for capture in pattern.captures_iter(text) {
                matches.push(PiiMatch {
                    pattern_name: name.clone(),
                    matched_text: capture[0].to_string(),
                    start: capture.get(0).unwrap().start(),
                    end: capture.get(0).unwrap().end(),
                });
            }
        }
        matches
    }
}
```

### Error Handling

**Location**: `/docs/engineering/error-handling.md`

**Purpose**: Define consistent error handling patterns across all components.

#### Exception Hierarchy

**Python Custom Exceptions**:
```python
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

class TaskError(OctoLLMError):
    """Base exception for task-related errors."""
    pass

class TaskNotFoundError(TaskError):
    """Task was not found in the database."""

    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task {task_id} not found",
            error_code="TASK_NOT_FOUND",
            details={"task_id": task_id}
        )

class TaskTimeoutError(TaskError):
    """Task execution exceeded timeout."""

    def __init__(self, task_id: str, timeout: int):
        super().__init__(
            message=f"Task {task_id} timed out after {timeout}s",
            error_code="TASK_TIMEOUT",
            details={"task_id": task_id, "timeout": timeout},
            retry_after=60
        )

class TaskExecutionError(TaskError):
    """Task failed during execution."""

    def __init__(self, task_id: str, reason: str):
        super().__init__(
            message=f"Task {task_id} failed: {reason}",
            error_code="TASK_EXECUTION_FAILED",
            details={"task_id": task_id, "reason": reason}
        )

class RateLimitError(OctoLLMError):
    """Rate limit exceeded."""

    def __init__(self, limit: int, window: int, retry_after: int):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}s",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window": window},
            retry_after=retry_after
        )

class AuthorizationError(OctoLLMError):
    """Authorization failed."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED"
        )

class ValidationError(OctoLLMError):
    """Input validation failed."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation failed for {field}: {reason}",
            error_code="VALIDATION_ERROR",
            details={"field": field, "reason": reason}
        )
```

#### Error Response Format

**HTTP Error Responses**:
```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

@app.exception_handler(OctoLLMError)
async def octollm_error_handler(request: Request, exc: OctoLLMError):
    """Handle OctoLLM custom exceptions."""
    status_map = {
        "TASK_NOT_FOUND": 404,
        "TASK_TIMEOUT": 408,
        "TASK_EXECUTION_FAILED": 500,
        "RATE_LIMIT_EXCEEDED": 429,
        "AUTHORIZATION_FAILED": 403,
        "VALIDATION_ERROR": 400,
        "UNKNOWN_ERROR": 500,
    }

    status_code = status_map.get(exc.error_code, 500)

    response_data = exc.to_dict()
    response_data["request_id"] = request.state.request_id

    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=status_code,
        content=response_data,
        headers=headers
    )
```

#### Retry Logic

**Exponential Backoff**:
```python
import asyncio
from typing import TypeVar, Callable, Optional
from functools import wraps

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
    **kwargs
) -> T:
    """Retry function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e

            if attempt >= max_retries:
                logger.error(
                    "Max retries exceeded",
                    function=func.__name__,
                    attempts=attempt + 1,
                    error=str(e)
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)

            # Add jitter
            if jitter:
                import random
                delay *= (0.5 + random.random())

            logger.warning(
                "Retrying after error",
                function=func.__name__,
                attempt=attempt + 1,
                delay=delay,
                error=str(e)
            )

            await asyncio.sleep(delay)

    raise last_exception

# Usage example
async def call_external_api(url: str) -> Dict[str, Any]:
    """Call external API with retry logic."""
    async with httpx.AsyncClient() as client:
        response = await retry_with_backoff(
            client.get,
            url,
            max_retries=3,
            base_delay=1.0,
            retryable_exceptions=(httpx.HTTPError, asyncio.TimeoutError)
        )
        return response.json()
```

#### Circuit Breaker

**Circuit Breaker Implementation**:
```python
from enum import Enum
from datetime import datetime, timedelta
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
        success_threshold: int = 2,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return False
        return datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout)

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info("Circuit breaker closed after successful recovery")

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "Circuit breaker opened",
                failures=self.failure_count,
                threshold=self.failure_threshold
            )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering half-open state")
            else:
                raise SystemError(
                    f"Circuit breaker is open. "
                    f"Retry after {self.timeout}s"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

# Usage example
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout=60,
    expected_exception=httpx.HTTPError
)

async def call_llm_api(prompt: str) -> str:
    """Call LLM API with circuit breaker."""
    return await llm_circuit_breaker.call(
        _call_llm_api_internal,
        prompt
    )
```

### Logging and Observability

**Location**: `/docs/engineering/logging-observability.md`

**Purpose**: Define logging standards and observability practices.

#### Structured Logging

**Python Configuration (structlog)**:
```python
import structlog
from pythonjsonlogger import jsonlogger

def configure_logging(
    level: str = "INFO",
    json_logs: bool = True,
    service_name: str = "octollm"
) -> None:
    """Configure structured logging for the application."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # Production: JSON format
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Console format
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Set level
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper())
    )

# Usage
logger = structlog.get_logger()

logger.info("Task started", task_id="task-123", user_id="user-456")
logger.error("Task failed", task_id="task-123", error="Timeout", duration_ms=30000)
```

**Rust Configuration (tracing)**:
```rust
use tracing::{info, error, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

pub fn configure_logging(level: &str, json_logs: bool) {
    let level = match level {
        "debug" => tracing::Level::DEBUG,
        "info" => tracing::Level::INFO,
        "warn" => tracing::Level::WARN,
        "error" => tracing::Level::ERROR,
        _ => tracing::Level::INFO,
    };

    if json_logs {
        // Production: JSON format
        tracing_subscriber::registry()
            .with(tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(level.into()))
            .with(tracing_subscriber::fmt::layer()
                .json()
                .with_current_span(false))
            .init();
    } else {
        // Development: Console format
        tracing_subscriber::registry()
            .with(tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(level.into()))
            .with(tracing_subscriber::fmt::layer())
            .init();
    }
}

// Usage
#[tracing::instrument(skip(req))]
async fn process_request(req: Request) -> Result<Response> {
    info!(client_id = %req.client_id, "Processing request");

    match handle_request(req).await {
        Ok(resp) => {
            info!(status = "success", "Request completed");
            Ok(resp)
        }
        Err(e) => {
            error!(error = %e, "Request failed");
            Err(e)
        }
    }
}
```

#### Metrics (Prometheus)

**Python Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge, Summary

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Task metrics
task_duration_seconds = Histogram(
    'task_duration_seconds',
    'Task execution duration',
    ['task_type', 'status'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

tasks_in_progress = Gauge(
    'tasks_in_progress',
    'Number of tasks currently executing',
    ['task_type']
)

# LLM metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['provider', 'model', 'type']
)

# Usage
@app.post("/tasks")
async def create_task(task: TaskRequest):
    with tasks_in_progress.labels(task_type=task.type).track_inprogress():
        start_time = time.time()
        try:
            result = await execute_task(task)
            task_duration_seconds.labels(
                task_type=task.type,
                status="success"
            ).observe(time.time() - start_time)
            return result
        except Exception as e:
            task_duration_seconds.labels(
                task_type=task.type,
                status="error"
            ).observe(time.time() - start_time)
            raise
```

**Metrics Endpoint**:
```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

#### Distributed Tracing

**OpenTelemetry Configuration**:
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def configure_tracing(service_name: str, otlp_endpoint: str):
    """Configure OpenTelemetry tracing."""

    # Set up tracer provider
    provider = TracerProvider(
        resource=Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
        })
    )

    # Export to OTLP (Jaeger/Tempo)
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument HTTP clients
    HTTPXClientInstrumentor().instrument()

# Manual span creation
tracer = trace.get_tracer(__name__)

async def execute_task(task_id: str):
    with tracer.start_as_current_span("execute_task") as span:
        span.set_attribute("task.id", task_id)
        span.set_attribute("task.type", "code_generation")

        try:
            result = await _execute_task_internal(task_id)
            span.set_attribute("task.status", "success")
            return result
        except Exception as e:
            span.set_attribute("task.status", "error")
            span.record_exception(e)
            raise
```

### Performance Optimization

**Location**: `/docs/engineering/performance-optimization.md`

**Purpose**: Define performance optimization best practices.

#### Async Operations

**Good - Concurrent Execution**:
```python
async def fetch_task_context(task_id: str) -> TaskContext:
    """Fetch all task context concurrently."""
    task, capabilities, memory = await asyncio.gather(
        db.get_task(task_id),
        db.get_arm_capabilities(),
        memory_client.get_context(task_id)
    )
    return TaskContext(task=task, capabilities=capabilities, memory=memory)
```

**Bad - Sequential Execution**:
```python
async def fetch_task_context_bad(task_id: str) -> TaskContext:
    """Fetch task context sequentially (slow)."""
    task = await db.get_task(task_id)  # Wait
    capabilities = await db.get_arm_capabilities()  # Wait
    memory = await memory_client.get_context(task_id)  # Wait
    return TaskContext(task=task, capabilities=capabilities, memory=memory)
```

#### Connection Pooling

**Database Connection Pool**:
```python
import asyncpg

# Create connection pool
pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=10,
    max_size=50,
    max_inactive_connection_lifetime=300,
    command_timeout=60
)

# Use pool
async def get_task(task_id: str) -> Task:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tasks WHERE id = $1",
            task_id
        )
        return Task(**row)
```

**HTTP Connection Pool**:
```python
import httpx

# Create client with connection pool
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30
    ),
    timeout=httpx.Timeout(
        connect=5.0,
        read=30.0,
        write=10.0,
        pool=5.0
    )
)

# Use client
async def call_arm(url: str, data: dict) -> dict:
    response = await client.post(url, json=data)
    return response.json()
```

#### Multi-Level Caching

**L1 (In-Memory) + L2 (Redis)**:
```python
from cachetools import TTLCache
import redis.asyncio as redis

class MultiLevelCache:
    """Two-level cache with in-memory L1 and Redis L2."""

    def __init__(self, redis_client: redis.Redis):
        self.l1 = TTLCache(maxsize=1000, ttl=60)
        self.l2 = redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache (L1 then L2)."""
        # Try L1
        if key in self.l1:
            logger.debug("L1 cache hit", key=key)
            return self.l1[key]

        # Try L2
        value = await self.l2.get(key)
        if value:
            logger.debug("L2 cache hit", key=key)
            self.l1[key] = value  # Promote to L1
            return value

        logger.debug("Cache miss", key=key)
        return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int = 3600
    ) -> None:
        """Set value in both cache levels."""
        self.l1[key] = value
        await self.l2.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        """Delete from both cache levels."""
        if key in self.l1:
            del self.l1[key]
        await self.l2.delete(key)
```

#### Database Query Optimization

**Use Indexes**:
```sql
-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_tasks_status_priority
ON tasks(status, priority DESC);

CREATE INDEX CONCURRENTLY idx_tasks_user_created
ON tasks(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_entities_type_name
ON entities(entity_type, name);

-- GIN index for JSONB
CREATE INDEX CONCURRENTLY idx_entities_properties
ON entities USING GIN(properties);
```

**Optimize Queries**:
```python
# Good - Fetch only needed columns
async def get_task_summary(task_id: str) -> TaskSummary:
    row = await conn.fetchrow("""
        SELECT id, status, created_at, updated_at
        FROM tasks
        WHERE id = $1
    """, task_id)
    return TaskSummary(**row)

# Bad - Fetch all columns
async def get_task_summary_bad(task_id: str) -> TaskSummary:
    row = await conn.fetchrow("""
        SELECT *  -- Fetches unnecessary data
        FROM tasks
        WHERE id = $1
    """, task_id)
    return TaskSummary(**row)

# Good - Batch queries
async def get_tasks_batch(task_ids: List[str]) -> List[Task]:
    rows = await conn.fetch("""
        SELECT * FROM tasks
        WHERE id = ANY($1::uuid[])
    """, task_ids)
    return [Task(**row) for row in rows]

# Bad - N+1 queries
async def get_tasks_batch_bad(task_ids: List[str]) -> List[Task]:
    tasks = []
    for task_id in task_ids:  # N queries!
        row = await conn.fetchrow("""
            SELECT * FROM tasks WHERE id = $1
        """, task_id)
        tasks.append(Task(**row))
    return tasks
```

### Code Review

**Location**: `/docs/engineering/code-review.md`

**Purpose**: Define code review process and checklists.

#### Pull Request Template

```markdown
## Description

Brief description of the changes and their purpose.

Fixes #(issue)

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All tests passing

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-reviewed the code
- [ ] Commented complex logic
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Added tests for changes
- [ ] All tests pass
- [ ] No breaking changes (or documented)
```

#### Author Checklist

**Before Submitting PR**:
- [ ] Code compiles without errors
- [ ] All tests pass locally
- [ ] Code formatted (Black/rustfmt)
- [ ] Linting passes (ruff/clippy)
- [ ] Type checking passes (mypy)
- [ ] Added tests for new functionality
- [ ] Updated documentation
- [ ] Self-reviewed the diff
- [ ] Checked for secrets/credentials
- [ ] Rebased on latest main
- [ ] Squashed related commits

#### Reviewer Checklist

**Code Quality**:
- [ ] Code is clear and understandable
- [ ] Follows coding standards
- [ ] No code smells or anti-patterns
- [ ] Appropriate abstractions
- [ ] DRY principle followed
- [ ] SOLID principles followed
- [ ] No unnecessary complexity

**Testing**:
- [ ] Tests are comprehensive
- [ ] Tests are maintainable
- [ ] Edge cases covered
- [ ] Error cases tested
- [ ] Mocks used appropriately
- [ ] Tests are deterministic
- [ ] Tests are fast

**Security**:
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] Output sanitization present
- [ ] Authentication/authorization correct
- [ ] No SQL injection risks
- [ ] No XSS risks
- [ ] Capability tokens used correctly

**Performance**:
- [ ] No obvious performance issues
- [ ] Database queries optimized
- [ ] Caching used appropriately
- [ ] No N+1 queries
- [ ] Async operations where beneficial
- [ ] Connection pooling used
- [ ] Resource limits considered

**Documentation**:
- [ ] Code is self-documenting
- [ ] Complex logic commented
- [ ] API documentation updated
- [ ] README updated if needed
- [ ] Migration guide updated if needed
- [ ] ADR created for significant decisions

**Deployment**:
- [ ] Backwards compatible
- [ ] Database migrations included
- [ ] Configuration changes documented
- [ ] Rollback procedure documented
- [ ] Monitoring/alerting updated

---

## Development Guides

### Development Workflow

**Location**: `/docs/guides/development-workflow.md`

**Purpose**: Complete guide to development workflow from setup to deployment.

#### Setup

**1. Fork and Clone**:
```bash
# Fork repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/octollm.git
cd octollm

# Add upstream remote
git remote add upstream https://github.com/octollm/octollm.git
```

**2. Environment Setup**:
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
vim .env
```

**3. Start Development Environment**:
```bash
# Start all services
./scripts/dev.sh

# Or manually with docker compose
docker compose up -d
```

#### Development Cycle

**1. Create Feature Branch**:
```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/123-task-parallel-execution
```

**2. Make Changes**:
```bash
# Edit files
vim orchestrator/orchestrator.py

# Run tests
docker compose exec orchestrator pytest -v

# Format code
docker compose exec orchestrator black .
docker compose exec orchestrator isort .

# Lint code
docker compose exec orchestrator ruff check .
```

**3. Commit Changes**:
```bash
# Stage changes
git add orchestrator/orchestrator.py

# Commit with conventional commit message
git commit -m "feat: add parallel task execution

Implement parallel execution of independent tasks using asyncio.gather().
This reduces overall task completion time by 40% in benchmark tests.

Closes #123"
```

**4. Push and Create PR**:
```bash
# Push to your fork
git push origin feature/123-task-parallel-execution

# Create PR on GitHub
# Fill out PR template
```

#### Branch Naming

**Pattern**: `<type>/<issue>-<description>`

**Types**:
- `feature/` - New feature
- `fix/` - Bug fix
- `docs/` - Documentation
- `perf/` - Performance improvement
- `refactor/` - Code refactoring
- `test/` - Test additions/fixes
- `chore/` - Maintenance tasks

**Examples**:
```
feature/123-parallel-task-execution
fix/456-pii-detection-regex
docs/789-api-reference-update
perf/012-cache-optimization
refactor/345-simplify-error-handling
test/678-integration-tests
chore/901-update-dependencies
```

#### Commit Messages

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `perf`: Performance
- `test`: Tests
- `chore`: Maintenance

**Examples**:
```
feat(orchestrator): add parallel task execution

Implement parallel execution of independent tasks using asyncio.gather().
This reduces overall task completion time by 40% in benchmark tests.

Closes #123

---

fix(reflex): correct PII regex for phone numbers

Previous regex was not matching international formats.
Updated to support +1 (555) 123-4567 format.

Fixes #456

---

docs(api): update task execution endpoint

Add examples for parallel execution parameter.
Update response schema documentation.
```

### Migration Guide

**Location**: `/docs/guides/migration-guide.md`

**Purpose**: Guide for migrating between OctoLLM versions.

#### Version Compatibility

**Supported Upgrade Paths**:
- v1.0.x → v1.1.x (minor)
- v1.1.x → v2.0.x (major, breaking changes)

**Database Migration**:

**1. Backup Database**:
```bash
# PostgreSQL backup
pg_dump -h localhost -U octollm -d octollm > backup-$(date +%Y%m%d).sql

# Or using script
./scripts/backup-database.sh
```

**2. Run Migration**:
```bash
# Check current version
docker compose exec orchestrator alembic current

# Show pending migrations
docker compose exec orchestrator alembic history

# Run migration
docker compose exec orchestrator alembic upgrade head

# Or specific version
docker compose exec orchestrator alembic upgrade abc123
```

**3. Verify Migration**:
```bash
# Check new version
docker compose exec orchestrator alembic current

# Run smoke tests
./scripts/smoke-tests.sh
```

**Example Migration Script**:
```python
"""Add task_priority index

Revision ID: abc123
Revises: def456
Create Date: 2025-11-10 10:00:00

"""
from alembic import op

def upgrade():
    """Upgrade database schema."""
    # Create index concurrently (doesn't block reads/writes)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_status_priority
        ON tasks(status, priority DESC)
    """)

    # Add new column with default
    op.add_column('tasks',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0')
    )

def downgrade():
    """Rollback database schema."""
    op.execute("""
        DROP INDEX IF EXISTS idx_tasks_status_priority
    """)

    op.drop_column('tasks', 'retry_count')
```

#### Configuration Migration

**v1.0 → v1.1**:
```yaml
# Old config (v1.0)
database:
  url: postgresql://localhost/octollm

# New config (v1.1)
database:
  url: postgresql://localhost/octollm
  pool_size: 20  # New setting
  max_overflow: 10  # New setting
```

**Migration Script**:
```bash
#!/bin/bash
# migrate-config-v1.0-v1.1.sh

# Backup old config
cp config.yaml config.yaml.backup

# Add new settings
cat >> config.yaml <<EOF
  pool_size: 20
  max_overflow: 10
EOF
```

#### Rollback Procedure

**1. Stop Services**:
```bash
docker compose down
```

**2. Restore Database**:
```bash
# Restore from backup
psql -h localhost -U octollm -d octollm < backup-20251110.sql

# Or using script
./scripts/restore-database.sh backup-20251110.sql
```

**3. Downgrade Migration**:
```bash
# Rollback to specific version
docker compose exec orchestrator alembic downgrade def456

# Or rollback one version
docker compose exec orchestrator alembic downgrade -1
```

**4. Deploy Previous Version**:
```bash
# Checkout previous version
git checkout v1.0.5

# Deploy
docker compose up -d
```

### Contributing Guidelines

**Location**: `/docs/guides/contributing.md`

**Purpose**: Guide for external contributors.

#### Getting Started

**1. Find an Issue**:
- Browse [open issues](https://github.com/octollm/octollm/issues)
- Look for `good-first-issue` or `help-wanted` labels
- Comment on the issue to claim it

**2. Fork and Clone**:
```bash
# Fork repository on GitHub
git clone https://github.com/YOUR_USERNAME/octollm.git
cd octollm
git remote add upstream https://github.com/octollm/octollm.git
```

**3. Set Up Environment**:
```bash
# Copy environment file
cp .env.example .env

# Start services
./scripts/dev.sh
```

#### Making Changes

**1. Create Branch**:
```bash
git checkout -b feature/123-your-feature
```

**2. Write Code**:
- Follow [coding standards](/docs/engineering/coding-standards.md)
- Add tests for new functionality
- Update documentation

**3. Test Changes**:
```bash
# Run tests
./scripts/test.sh

# Format code
docker compose exec orchestrator black .
docker compose exec orchestrator isort .

# Lint code
docker compose exec orchestrator ruff check .
```

**4. Commit**:
```bash
git add .
git commit -m "feat: add your feature

Detailed description of changes.

Closes #123"
```

**5. Push and Create PR**:
```bash
git push origin feature/123-your-feature
```

Then create a pull request on GitHub.

#### Code of Conduct

**Our Standards**:
- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy

**Unacceptable Behavior**:
- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other conduct inappropriate in a professional setting

---

## Architecture Decision Records

### ADR-001: Technology Stack

**Location**: `/docs/adr/001-technology-stack.md`

**Status**: Accepted
**Date**: 2025-11-10

#### Decision

Use Python 3.11+ for services, Rust 1.75+ for performance-critical components, PostgreSQL 15+ for data, Redis 7+ for caching, Qdrant 1.7+ for vector search.

#### Key Technologies

**Python**:
- Framework: FastAPI
- Runtime: asyncio + uvicorn
- Use: Orchestrator, Arms, API services

**Rust**:
- Framework: Axum
- Runtime: tokio
- Use: Reflex Layer, Tool Executor

**Databases**:
- PostgreSQL: Global knowledge graph, task history
- Qdrant: Episodic memory (vectors)
- Redis: L2 cache, pub/sub

#### Rationale

- Python: Excellent LLM ecosystem, async support, developer productivity
- Rust: <10ms P95 latency, memory safety, zero-cost abstractions
- PostgreSQL: ACID guarantees, JSONB flexibility, mature
- Qdrant: Optimized vector search, built in Rust
- Redis: Sub-millisecond cache, pub/sub built-in

#### Alternatives Considered

- Go (not as fast as Rust)
- Node.js (weaker LLM support)
- Java/Spring Boot (slower development)
- MongoDB (weaker ACID)
- Elasticsearch (not optimized for vectors)

### ADR-002: Communication Patterns

**Location**: `/docs/adr/002-communication-patterns.md`

**Status**: Accepted
**Date**: 2025-11-10

#### Decision

Use HTTP/REST for synchronous operations, Redis pub/sub for events, direct HTTP for arm-to-arm, WebSocket for real-time updates.

#### Communication Patterns

**HTTP/REST**:
- Use: Reflex → Orchestrator, Orchestrator → Arms
- Format: JSON
- Auth: JWT capability tokens

**Redis Pub/Sub**:
- Use: Event notifications
- Channels: Topic-based routing

**Direct HTTP**:
- Use: Arm-to-arm collaboration
- Discovery: Kubernetes DNS

**WebSocket**:
- Use: Real-time task updates
- Format: JSON messages

#### Rationale

- HTTP/REST: Universal, well-understood, excellent debugging
- Redis pub/sub: Fast, decoupled, built into Redis
- Direct HTTP: Simple, low latency, no broker overhead
- WebSocket: Bi-directional, lower overhead than polling

#### Alternatives Considered

- gRPC (more complex)
- Message Broker (operational overhead)
- Service Mesh (too complex initially)
- GraphQL (unnecessary complexity)

### ADR-003: Memory Architecture

**Location**: `/docs/adr/003-memory-architecture.md`

**Status**: Accepted
**Date**: 2025-11-10

#### Decision

Three-tier memory with PostgreSQL (global), Qdrant (episodic), Redis (cache), plus routing layer and data diodes.

#### Architecture

**Global Memory (PostgreSQL)**:
- Purpose: Shared knowledge graph
- Schema: Entities, relationships, task history
- Queries: SQL with JSONB

**Episodic Memory (Qdrant)**:
- Purpose: Task-specific examples
- Collections: coder_memory, planner_memory, judge_memory
- Queries: Vector similarity search

**Cache Layer**:
- L1: In-memory TTL cache (1000 items, 60s)
- L2: Redis (unlimited, LRU eviction)

**Memory Router**:
- Routes queries to appropriate system
- Based on query type and requirements

**Data Diodes**:
- Enforce security boundaries
- Filter based on capabilities
- PII detection before storage

#### Rationale

- Right tool for each use case
- Optimized performance per layer
- Security isolation via diodes
- Independent scaling

#### Alternatives Considered

- Single PostgreSQL with pgvector (insufficient vector performance)
- Neo4j for graph (higher complexity)
- Elasticsearch (not optimized for vectors)
- Single-tier Redis cache (network latency)

### ADR-004: Security Model

**Location**: `/docs/adr/004-security-model.md`

**Status**: Accepted
**Date**: 2025-11-10

#### Decision

Capability-based security with JWT tokens, PII detection in Reflex Layer, defense in depth.

#### Security Layers

**1. Capability Tokens (JWT)**:
- Fine-grained authorization
- Token structure with scopes
- Issued by Orchestrator
- Validated by each component

**2. PII Detection (Reflex)**:
- Regex patterns in Rust
- Detects: email, SSN, credit cards, phone
- Sanitizes before processing

**3. Input Validation**:
- Schema validation (Pydantic)
- Business logic validation
- Security validation (injection detection)

**4. Rate Limiting**:
- Token bucket algorithm
- Prevents resource exhaustion

**5. Audit Logging**:
- PostgreSQL with immutable logs
- All operations tracked

**6. Defense in Depth**:
- Network layer (K8s policies, TLS)
- Input layer (PII, validation)
- Access layer (capability tokens)
- Data layer (encryption, diodes)
- Output layer (sanitization)
- Monitoring layer (metrics, alerts)
- Audit layer (comprehensive logging)

#### Rationale

- Fine-grained control via capabilities
- Automatic PII protection
- Multiple security layers
- Low overhead (Rust PII, local JWT)
- Comprehensive audit trail

#### Alternatives Considered

- OAuth 2.0/OIDC (more complex)
- mTLS everywhere (operational burden)
- ML-based PII (higher latency)
- RBAC only (coarser-grained)

### ADR-005: Deployment Platform

**Location**: `/docs/adr/005-deployment-platform.md`

**Status**: Accepted
**Date**: 2025-11-10

#### Decision

Kubernetes for production, Docker Compose for development, cloud-agnostic design.

#### Production (Kubernetes)

**Platform**: Kubernetes 1.28+
**Distribution**: Any CNCF-certified (EKS, GKE, AKS, self-hosted)

**Components**:
- Deployments: Orchestrator, Arms (with HPA)
- DaemonSet: Reflex Layer
- StatefulSets: PostgreSQL, Qdrant, Redis
- Services: ClusterIP for internal, LoadBalancer for external
- Ingress: Nginx with TLS

**Features**:
- Auto-scaling with HPA
- Rolling updates
- Self-healing
- Resource quotas
- Service discovery
- Health checks

#### Development (Docker Compose)

**Purpose**: Fast iteration, easy debugging
**Setup**: Single command (`./scripts/dev.sh`)

**Features**:
- Volume mounts for hot reload
- Health checks
- Service dependencies
- Local networking

#### Configuration Management

**Kubernetes**:
- ConfigMaps for config
- Secrets for credentials
- Kustomize for environment-specific config
- Helm charts (alternative)

**CI/CD**:
- GitHub Actions for build/test
- Automated deployments to staging/production
- Smoke tests after deployment

#### Rationale

- Kubernetes: Industry standard, auto-scaling, self-healing
- Docker Compose: Fast startup, production parity, simple
- Cloud-agnostic: No vendor lock-in, portable
- CI/CD: Automated, consistent, safe deployments

#### Alternatives Considered

- Docker Swarm (less ecosystem)
- Nomad (smaller ecosystem)
- Serverless (cold start latency)
- Single VM (no HA)
- Cloud-specific (vendor lock-in)

---

## Phase 4 Summary

**Documents Created**: 13
**Total Lines**: ~18,400+

### Engineering Practices (5 documents)

1. **Coding Standards** (~1,200 lines)
   - Python and Rust style guides
   - Tool configurations
   - Type hints and documentation

2. **Error Handling** (~1,500 lines)
   - Custom exception hierarchy
   - Retry logic with exponential backoff
   - Circuit breaker implementation

3. **Logging and Observability** (~1,300 lines)
   - Structured logging (structlog, tracing)
   - Prometheus metrics
   - OpenTelemetry distributed tracing

4. **Performance Optimization** (~1,200 lines)
   - Async operation patterns
   - Connection pooling
   - Multi-level caching
   - Database query optimization

5. **Code Review** (~800 lines)
   - PR template
   - Author and reviewer checklists
   - Quality, security, performance checks

### Development Guides (3 documents)

6. **Development Workflow** (~1,000 lines)
   - Setup and environment
   - Development cycle
   - Branch naming and commit messages
   - PR process

7. **Migration Guide** (~1,100 lines)
   - Version compatibility
   - Database migrations
   - Configuration updates
   - Rollback procedures

8. **Contributing Guidelines** (~1,000 lines)
   - Getting started
   - Making changes
   - Code of Conduct
   - PR process for contributors

### Architecture Decision Records (5 documents)

9. **ADR README** (~300 lines)
   - ADR format and index
   - When to create ADRs
   - ADR statuses

10. **ADR-001: Technology Stack** (~2,500 lines)
    - Python, Rust, PostgreSQL, Redis, Qdrant
    - Rationale and alternatives
    - Deployment tools

11. **ADR-002: Communication Patterns** (~2,000 lines)
    - HTTP/REST, Redis pub/sub, WebSocket
    - Rationale and alternatives
    - Implementation guidelines

12. **ADR-003: Memory Architecture** (~2,200 lines)
    - Three-tier memory (PostgreSQL, Qdrant, Redis)
    - Memory router and data diodes
    - Rationale and alternatives

13. **ADR-004: Security Model** (~2,300 lines)
    - Capability-based JWT tokens
    - PII detection, rate limiting
    - Defense in depth
    - Rationale and alternatives

14. **ADR-005: Deployment Platform** (~2,500 lines)
    - Kubernetes for production
    - Docker Compose for development
    - CI/CD pipeline
    - Rationale and alternatives

---

**Phase 4 Complete**: 2025-11-10
**Next Phase**: Update DOCUMENTATION-SUMMARY.md to reflect Phase 4 completion
