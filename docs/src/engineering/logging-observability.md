# Logging and Observability

**Last Updated**: 2025-11-10
**Status**: Production Standard
**Applies To**: All OctoLLM components

## Overview

This document defines logging and observability standards for the OctoLLM project. Proper observability enables effective debugging, performance monitoring, and incident response in production environments.

## Table of Contents

- [Logging Standards](#logging-standards)
- [Structured Logging](#structured-logging)
- [Log Levels](#log-levels)
- [Metrics](#metrics)
- [Distributed Tracing](#distributed-tracing)
- [Request IDs](#request-ids)
- [Log Aggregation](#log-aggregation)
- [Observability Tools](#observability-tools)

---

## Logging Standards

### Python Logging with structlog

**Configuration**:

```python
# octollm/logging_config.py
import logging
import structlog
from typing import Any, Dict

def configure_logging(
    level: str = "INFO",
    json_logs: bool = True,
    service_name: str = "octollm"
) -> None:
    """Configure structured logging for the application."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=[logging.StreamHandler()]
    )

    # Shared processors for all loggers
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add service metadata
    def add_service_context(
        logger: Any,
        method_name: str,
        event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add service-level context to all logs."""
        event_dict["service"] = service_name
        event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
        event_dict["version"] = os.getenv("APP_VERSION", "unknown")
        return event_dict

    shared_processors.insert(0, add_service_context)

    if json_logs:
        # JSON output for production
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
        # Human-readable output for development
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


# Initialize logging
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("JSON_LOGS", "true").lower() == "true",
    service_name=os.getenv("SERVICE_NAME", "octollm")
)
```

### Rust Logging with tracing

**Configuration**:

```rust
// src/logging.rs
use tracing_subscriber::{
    fmt,
    prelude::*,
    EnvFilter,
};
use tracing_appender::rolling::{RollingFileAppender, Rotation};

pub fn configure_logging(service_name: &str) {
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    // JSON formatting for production
    let json_layer = fmt::layer()
        .json()
        .with_current_span(true)
        .with_span_list(true);

    // File appender
    let file_appender = RollingFileAppender::new(
        Rotation::DAILY,
        "/var/log/octollm",
        format!("{}.log", service_name)
    );

    let file_layer = fmt::layer()
        .json()
        .with_writer(file_appender);

    tracing_subscriber::registry()
        .with(env_filter)
        .with(json_layer)
        .with(file_layer)
        .init();

    tracing::info!(
        service = service_name,
        "Logging initialized"
    );
}
```

---

## Structured Logging

### Python Structured Logs

```python
import structlog

logger = structlog.get_logger(__name__)

# Basic structured log
logger.info(
    "task.created",
    task_id="task-123",
    user_id="user-456",
    priority=5
)

# Output (JSON):
# {
#   "event": "task.created",
#   "task_id": "task-123",
#   "user_id": "user-456",
#   "priority": 5,
#   "timestamp": "2025-11-10T10:30:45.123456Z",
#   "level": "info",
#   "logger": "octollm.orchestrator",
#   "service": "octollm-orchestrator",
#   "environment": "production"
# }

# Contextual logging with bind
logger = logger.bind(
    task_id="task-123",
    user_id="user-456"
)

logger.info("task.processing.started")
logger.info("task.arm.selected", arm="coder")
logger.info("task.processing.completed", duration_ms=1234)

# All logs include task_id and user_id automatically
```

### Request-Scoped Context

```python
from contextvars import ContextVar
from typing import Optional
import uuid

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar(
    "request_id",
    default=None
)

def set_request_context(request_id: Optional[str] = None):
    """Set request context for logging."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    structlog.contextvars.bind_contextvars(
        request_id=request_id
    )
    return request_id


# FastAPI middleware
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """Add request ID to all logs."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")
        set_request_context(request_id)

        logger.info(
            "request.started",
            method=request.method,
            path=request.url.path,
            client=request.client.host
        )

        response = await call_next(request)

        logger.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code
        )

        response.headers["X-Request-ID"] = request_id_var.get()
        return response

app = FastAPI()
app.add_middleware(LoggingMiddleware)
```

### Rust Structured Logs

```rust
use tracing::{info, warn, error, instrument};

// Basic structured log
info!(
    task_id = "task-123",
    user_id = "user-456",
    priority = 5,
    "Task created"
);

// Instrument function for automatic tracing
#[instrument(skip(config))]
async fn process_task(
    task_id: &str,
    config: &Config
) -> Result<String, Error> {
    info!("Processing task");

    let result = execute(task_id).await?;

    info!(
        duration_ms = result.duration,
        "Task completed"
    );

    Ok(result.output)
}

// All logs within this function automatically include task_id
```

---

## Log Levels

### Level Guidelines

**DEBUG**:
- Detailed diagnostic information
- Variable values and state
- Only enabled in development or troubleshooting

```python
logger.debug(
    "task.routing.evaluation",
    task_id=task.task_id,
    arm="coder",
    score=0.85,
    capabilities=["python", "code-generation"]
)
```

**INFO**:
- Normal operational events
- Task lifecycle events
- State transitions

```python
logger.info(
    "task.processing.started",
    task_id=task.task_id,
    priority=task.priority
)

logger.info(
    "task.processing.completed",
    task_id=task.task_id,
    duration_ms=result.duration
)
```

**WARNING**:
- Degraded operation
- Recoverable errors
- Unexpected but handled conditions

```python
logger.warning(
    "cache.miss",
    key=cache_key,
    fallback="database"
)

logger.warning(
    "arm.slow_response",
    arm="coder",
    duration_ms=5000,
    threshold_ms=1000
)
```

**ERROR**:
- Operation failed
- Requires attention
- User impact

```python
logger.error(
    "task.processing.failed",
    task_id=task.task_id,
    error=str(e),
    error_code=e.error_code,
    exc_info=True
)
```

**CRITICAL**:
- System failure
- Immediate action required
- Data loss risk

```python
logger.critical(
    "database.connection.lost",
    database="primary",
    error=str(e),
    exc_info=True
)
```

---

## Metrics

### Prometheus Metrics

**Counter**: Monotonically increasing values

```python
from prometheus_client import Counter

# Request counter
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Task counter
tasks_created_total = Counter(
    'tasks_created_total',
    'Total tasks created',
    ['priority', 'source']
)

# Error counter
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'component']
)

# Usage
http_requests_total.labels(
    method="POST",
    endpoint="/api/v1/tasks",
    status="200"
).inc()

tasks_created_total.labels(
    priority="high",
    source="api"
).inc()
```

**Histogram**: Distribution of values

```python
from prometheus_client import Histogram

# Request duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Task processing duration
task_duration_seconds = Histogram(
    'task_duration_seconds',
    'Task processing duration',
    ['arm', 'priority'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# LLM API latency
llm_api_latency_seconds = Histogram(
    'llm_api_latency_seconds',
    'LLM API call latency',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Usage
with http_request_duration_seconds.labels(
    method="POST",
    endpoint="/api/v1/tasks"
).time():
    result = await process_request()
```

**Gauge**: Current value

```python
from prometheus_client import Gauge

# Tasks in progress
tasks_in_progress = Gauge(
    'tasks_in_progress',
    'Number of tasks currently being processed',
    ['arm']
)

# Database connections
db_connections = Gauge(
    'db_connections',
    'Number of active database connections',
    ['pool']
)

# Cache size
cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes',
    ['cache_name']
)

# Usage
tasks_in_progress.labels(arm="coder").inc()
# ... process task ...
tasks_in_progress.labels(arm="coder").dec()

# Set absolute value
db_connections.labels(pool="primary").set(10)
```

### Custom Metrics Middleware

```python
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record metrics for all HTTP requests."""
    start_time = time.time()

    # Increment request counter
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status="in_progress"
    ).inc()

    try:
        response = await call_next(request)

        # Record duration
        duration = time.time() - start_time
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        # Update counter with final status
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code)
        ).inc()

        return response

    except Exception as e:
        # Record error
        errors_total.labels(
            error_type=type(e).__name__,
            component="http"
        ).inc()
        raise
```

---

## Distributed Tracing

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Configure tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure exporter (Jaeger)
otlp_exporter = OTLPSpanExporter(
    endpoint="http://jaeger:4317",
    insecure=True
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Instrument HTTP client
HTTPXClientInstrumentor().instrument()

# Manual span creation
async def process_task(task: TaskContract) -> str:
    """Process task with distributed tracing."""
    with tracer.start_as_current_span("process_task") as span:
        span.set_attribute("task.id", task.task_id)
        span.set_attribute("task.priority", task.priority)

        # Planning phase
        with tracer.start_as_current_span("plan_task"):
            plan = await planner.plan(task)
            span.set_attribute("plan.steps", len(plan.steps))

        # Execution phase
        with tracer.start_as_current_span("execute_task"):
            result = await executor.execute(plan)
            span.set_attribute("result.status", result.status)

        return result.output
```

### Span Propagation

```python
from opentelemetry.propagate import inject, extract

async def call_arm(arm_url: str, task: TaskContract) -> str:
    """Call arm with trace context propagation."""
    headers = {}

    # Inject trace context into headers
    inject(headers)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{arm_url}/execute",
            json=task.dict(),
            headers=headers
        )
        return response.json()


# Arm receiving request
@app.post("/execute")
async def execute(request: Request, task: TaskContract):
    """Execute task with trace context."""
    # Extract trace context from headers
    ctx = extract(request.headers)

    with tracer.start_as_current_span(
        "arm.execute",
        context=ctx
    ) as span:
        span.set_attribute("arm.name", "coder")
        result = await process(task)
        return result
```

---

## Request IDs

### Request ID Propagation

```python
import uuid
from typing import Optional

def generate_request_id() -> str:
    """Generate unique request ID."""
    return f"req_{uuid.uuid4().hex[:16]}"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate request IDs through the system."""

    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = (
            request.headers.get("X-Request-ID")
            or generate_request_id()
        )

        # Store in context
        set_request_context(request_id)

        # Add to all outgoing requests
        async def http_client_with_request_id():
            async with httpx.AsyncClient() as client:
                client.headers["X-Request-ID"] = request_id
                return client

        # Process request
        response = await call_next(request)

        # Add to response
        response.headers["X-Request-ID"] = request_id

        return response
```

### Correlation in Logs

```python
async def process_distributed_task(task: TaskContract):
    """Process task across multiple services."""
    request_id = request_id_var.get()

    logger.info(
        "orchestrator.processing.started",
        request_id=request_id,
        task_id=task.task_id
    )

    # Call planner arm
    plan = await call_arm("planner", task)
    logger.info(
        "orchestrator.planner.completed",
        request_id=request_id,
        task_id=task.task_id,
        steps=len(plan.steps)
    )

    # Call executor arm
    result = await call_arm("executor", plan)
    logger.info(
        "orchestrator.executor.completed",
        request_id=request_id,
        task_id=task.task_id
    )

    # All logs from all services will have the same request_id
    # enabling correlation across service boundaries
```

---

## Log Aggregation

### Loki Integration

**Promtail Configuration** (`promtail-config.yml`):

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Docker containers
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: 'stream'

  # Application logs
  - job_name: octollm
    static_configs:
      - targets:
          - localhost
        labels:
          job: octollm
          __path__: /var/log/octollm/*.log
```

### Query Examples

```bash
# All logs for a specific request
{service="octollm-orchestrator"} |= "req_abc123"

# Error logs from any service
{service=~"octollm-.*"} | json | level="error"

# Task processing logs
{service="octollm-orchestrator"} | json | event=~"task\\..*"

# Slow requests (>1s)
{service=~"octollm-.*"} | json | duration_ms > 1000

# LLM API errors
{service=~"octollm-.*"} | json | error_code="LLM_API_ERROR"
```

---

## Observability Tools

### Grafana Dashboards

**Orchestrator Dashboard**:

```json
{
  "dashboard": {
    "title": "OctoLLM Orchestrator",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{service=\"octollm-orchestrator\"}[5m])"
          }
        ]
      },
      {
        "title": "Request Duration (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(errors_total{service=\"octollm-orchestrator\"}[5m])"
          }
        ]
      },
      {
        "title": "Tasks In Progress",
        "targets": [
          {
            "expr": "tasks_in_progress"
          }
        ]
      }
    ]
  }
}
```

### Alert Configuration

**Prometheus Alert Rules**:

```yaml
groups:
  - name: octollm_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          rate(errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: SlowRequests
        expr: |
          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow request processing"
          description: "P95 latency is {{ $value }}s"

      - alert: ServiceDown
        expr: |
          up{job=~"octollm-.*"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
```

---

## Best Practices

1. **Use structured logging**: Always use structured logs (JSON) in production
2. **Include context**: Add relevant context (task_id, user_id, request_id)
3. **Consistent naming**: Use consistent event names (dot-notation)
4. **Log at boundaries**: Log at service boundaries and state transitions
5. **Don't log secrets**: Never log passwords, API keys, or PII
6. **Use appropriate levels**: Follow log level guidelines strictly
7. **Add metrics**: Complement logs with metrics for aggregation
8. **Correlation IDs**: Use request IDs for distributed tracing
9. **Sample when needed**: Use sampling for high-volume debug logs
10. **Monitor your monitoring**: Alert on logging/metrics failures

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Engineering Team
