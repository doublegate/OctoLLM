# OctoLLM API Overview

**Version**: 0.4.0
**Last Updated**: 2025-11-11
**Sprint**: 0.5 (Phase 0: Foundation)

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Getting Started](#getting-started)
4. [Authentication & Authorization](#authentication--authorization)
5. [Request/Response Handling](#requestresponse-handling)
6. [Error Handling](#error-handling)
7. [Rate Limiting & Quotas](#rate-limiting--quotas)
8. [API Versioning](#api-versioning)
9. [Common Patterns](#common-patterns)
10. [Performance & Optimization](#performance--optimization)
11. [Security Best Practices](#security-best-practices)
12. [SDK Usage](#sdk-usage)
13. [API Reference](#api-reference)

---

## Introduction

OctoLLM is a distributed AI architecture inspired by octopus neurobiology, designed for offensive security and developer tooling. The system features:

- **Central Orchestrator**: Strategic planning and coordination using frontier LLMs (GPT-4, Claude Opus)
- **Specialized Arms**: Domain-specific execution with local decision-making
- **Reflex Layer**: Fast preprocessing for common patterns without LLM involvement
- **Distributed Memory**: Global semantic memory + local episodic stores per arm

### Key Benefits

- **Cost Efficiency**: 50% reduction vs monolithic LLM by using specialized models
- **Performance**: <10ms reflex caching for common requests, <30s task completion
- **Security**: Defense-in-depth with PII sanitization, capability isolation, sandboxed execution
- **Scalability**: Horizontal scaling of individual arms based on workload

### Target Audience

This API is designed for:
- Security researchers and penetration testers
- DevOps engineers automating infrastructure tasks
- Developers building AI-powered applications
- Organizations requiring complex task automation with cost controls

---

## Architecture Overview

### System Components

```
┌──────────────────────────────────────────────────────────────┐
│                      API Gateway (NGINX)                     │
│                    Port: 80/443 (External)                   │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────┐
│                   Reflex Layer (8001)                        │
│     Fast Preprocessing │ Caching │ PII Detection            │
│     Latency: <10ms for cache hits, <50ms for decisions       │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────┐
│                   Orchestrator (8000)                        │
│     Central Brain │ Task Planning │ Arm Coordination         │
│     Model: GPT-4 / Claude Opus │ Cost Tier: 5 (Expensive)   │
└──────┬──────┬──────┬──────┬──────┬──────┬─────────────┬─────┘
       │      │      │      │      │      │             │
   ┌───┴──┐ ┌─┴───┐ ┌┴────┐ ┌┴────┐ ┌┴────┐ ┌┴─────┐  ┌┴─────┐
   │Planner│Executor│Retriever│Coder│Judge│Safety│
   │(8002) │(8003) │(8004) │(8005)│(8006)│(8007)│
   └──────┘ └──────┘ └──────┘ └─────┘ └─────┘ └──────┘
```

### Service Endpoints

| Service | Port | Purpose | Cost Tier | Avg Latency |
|---------|------|---------|-----------|-------------|
| **Orchestrator** | 8000 | Task coordination | 5 (Expensive) | 5-30s |
| **Reflex Layer** | 8001 | Preprocessing & caching | 1 (Cheap) | <50ms |
| **Planner** | 8002 | Task decomposition | 3 (Medium) | 1-5s |
| **Executor** | 8003 | Sandboxed execution | 2 (Low) | 5-60s |
| **Retriever** | 8004 | Semantic search | 2 (Low) | 100-500ms |
| **Coder** | 8005 | Code generation | 4 (High) | 2-10s |
| **Judge** | 8006 | Output validation | 3 (Medium) | 1-5s |
| **Safety Guardian** | 8007 | PII detection | 2 (Low) | 100-300ms |

### Data Flow

1. **Ingress**: API Gateway → Reflex Layer (cache check, PII detection)
2. **Planning**: Orchestrator → Planner (task decomposition)
3. **Execution**: Orchestrator → Specialized Arms (parallel execution)
4. **Validation**: Arms → Judge (acceptance criteria validation)
5. **Safety**: All inputs/outputs → Safety Guardian (PII filtering)
6. **Synthesis**: Orchestrator (result integration and response)

---

## Getting Started

### Prerequisites

- **API Key**: Obtain from [api.octollm.example.com/keys](https://api.octollm.example.com/keys)
- **Network Access**: Ports 8000-8007 accessible (or API Gateway on 443)
- **TLS**: All production traffic must use HTTPS

### Quick Start (curl)

```bash
# Set API key
export OCTOLLM_API_KEY="your-api-key-here"

# Submit a task
curl -X POST https://api.octollm.example.com:8000/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OCTOLLM_API_KEY" \
  -d '{
    "goal": "Analyze security vulnerabilities in Python Flask application",
    "budget": {
      "max_tokens": 10000,
      "max_time_seconds": 120,
      "max_cost_dollars": 1.0
    }
  }'

# Response
{
  "task_id": "task_abc123xyz456",
  "status": "queued",
  "created_at": "2025-11-11T12:00:00Z",
  "estimated_completion": "2025-11-11T12:02:00Z"
}

# Poll for results
curl https://api.octollm.example.com:8000/tasks/task_abc123xyz456 \
  -H "X-API-Key: $OCTOLLM_API_KEY"
```

### Quick Start (Python SDK)

```python
from octollm_sdk import OrchestratorClient

client = OrchestratorClient(
    baseUrl="https://api.octollm.example.com:8000",
    apiKey="your-api-key-here"
)

# Submit task
response = await client.submitTask({
    "goal": "Analyze security vulnerabilities",
    "budget": {"max_tokens": 10000}
})

# Get status
status = await client.getTask(response.task_id)
print(f"Status: {status.status}")
```

### Quick Start (TypeScript SDK)

```typescript
import { OrchestratorClient } from 'octollm-sdk';

const client = new OrchestratorClient({
  baseUrl: 'https://api.octollm.example.com:8000',
  apiKey: 'your-api-key-here'
});

// Submit task
const response = await client.submitTask({
  goal: 'Analyze security vulnerabilities',
  budget: { max_tokens: 10000 }
});

// Get status
const status = await client.getTask(response.task_id);
console.log(`Status: ${status.status}`);
```

---

## Authentication & Authorization

### Authentication Methods

OctoLLM supports two authentication methods:

#### 1. API Key Authentication (Recommended for External Clients)

**Header**: `X-API-Key`
**Format**: `X-API-Key: octollm_live_1234567890abcdef`
**Scope**: Full API access

```bash
curl https://api.octollm.example.com:8000/tasks \
  -H "X-API-Key: octollm_live_1234567890abcdef" \
  -d '{"goal": "..."}'
```

#### 2. Bearer Token Authentication (For Inter-Service Communication)

**Header**: `Authorization`
**Format**: `Authorization: Bearer <JWT_TOKEN>`
**Scope**: Capability-based (specific arm permissions)

```bash
curl https://api.octollm.example.com:8000/tasks \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{"goal": "..."}'
```

### API Key Management

#### Obtaining API Keys

1. Sign up at [api.octollm.example.com/signup](https://api.octollm.example.com/signup)
2. Verify email
3. Generate API key from dashboard: [api.octollm.example.com/keys](https://api.octollm.example.com/keys)
4. **Store securely** - keys cannot be retrieved after generation

#### API Key Types

| Type | Prefix | Scope | Rate Limit | Use Case |
|------|--------|-------|------------|----------|
| **Test** | `octollm_test_` | Development env | 10 req/min | Testing |
| **Live** | `octollm_live_` | Production | 100 req/min | Production |
| **Admin** | `octollm_admin_` | All services | Unlimited | Internal |

#### Key Rotation

```bash
# Generate new key
curl -X POST https://api.octollm.example.com/keys \
  -H "X-API-Key: <current-key>" \
  -d '{"name": "New Production Key", "type": "live"}'

# Revoke old key
curl -X DELETE https://api.octollm.example.com/keys/<key-id> \
  -H "X-API-Key: <current-key>"
```

### Bearer Tokens (Advanced)

Bearer tokens are JWT tokens with **capability-based access control**:

```json
{
  "sub": "arm_planner",
  "iss": "octollm-orchestrator",
  "exp": 1699999999,
  "capabilities": [
    "task:decompose",
    "memory:read"
  ],
  "budget": {
    "max_tokens": 5000,
    "max_cost_dollars": 0.50
  }
}
```

**Use Cases**:
- Inter-service communication (Orchestrator → Arms)
- Time-limited tokens for specific tasks
- Delegated access with restricted capabilities

### Authorization Scopes

| Scope | Description | Required For |
|-------|-------------|--------------|
| `task:submit` | Submit new tasks | All external clients |
| `task:read` | Get task status | Task monitoring |
| `task:cancel` | Cancel running tasks | Task management |
| `arm:list` | List registered arms | Discovery |
| `arm:register` | Register new arms | Arm deployment |
| `memory:read` | Read global memory | Retriever arm |
| `memory:write` | Write global memory | All arms |
| `sandbox:execute` | Execute commands | Executor arm |

### Security Best Practices

1. **Never commit API keys to version control**
2. **Use environment variables**: `OCTOLLM_API_KEY`
3. **Rotate keys every 90 days**
4. **Use test keys in development**
5. **Monitor key usage**: [api.octollm.example.com/usage](https://api.octollm.example.com/usage)
6. **Revoke compromised keys immediately**
7. **Use HTTPS only** - never send keys over HTTP

---

## Request/Response Handling

### Request Format

All requests must use:
- **Method**: GET, POST, PUT, DELETE (as documented per endpoint)
- **Content-Type**: `application/json` (for request bodies)
- **Accept**: `application/json` (for responses)

#### Required Headers

```http
POST /tasks HTTP/1.1
Host: api.octollm.example.com:8000
Content-Type: application/json
X-API-Key: octollm_live_1234567890abcdef
X-Request-ID: uuid-1234-5678-90ab-cdef (optional but recommended)
```

#### Request Body Structure

```json
{
  "goal": "Natural language task description",
  "constraints": ["Optional constraint 1", "Optional constraint 2"],
  "acceptance_criteria": ["Success condition 1", "Success condition 2"],
  "context": {
    "key": "value",
    "additional_metadata": "..."
  },
  "budget": {
    "max_tokens": 10000,
    "max_time_seconds": 120,
    "max_cost_dollars": 1.0
  }
}
```

### Response Format

#### Success Response

**Status Code**: 200 (OK), 201 (Created)
**Content-Type**: `application/json`

```json
{
  "task_id": "task_abc123xyz456",
  "status": "completed",
  "created_at": "2025-11-11T12:00:00Z",
  "updated_at": "2025-11-11T12:02:30Z",
  "progress": {
    "current_step": "synthesis",
    "completed_steps": 5,
    "total_steps": 5,
    "percentage": 100
  },
  "result": {
    "output": "Security analysis completed. Found 3 high-severity vulnerabilities...",
    "confidence": 0.92,
    "validation_passed": true
  }
}
```

#### Error Response

**Status Code**: 400-599
**Content-Type**: `application/json`

```json
{
  "error": {
    "code": "validation_error",
    "message": "Goal must be between 10 and 2000 characters",
    "details": {
      "field": "goal",
      "provided_length": 5,
      "min_length": 10,
      "max_length": 2000
    }
  },
  "request_id": "req_xyz789",
  "timestamp": "2025-11-11T12:00:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| **200** | OK | Request successful |
| **201** | Created | Resource created (e.g., task submitted) |
| **202** | Accepted | Request accepted for processing |
| **400** | Bad Request | Invalid request format or parameters |
| **401** | Unauthorized | Invalid or missing authentication |
| **403** | Forbidden | Valid auth but insufficient permissions |
| **404** | Not Found | Resource not found (e.g., task_id) |
| **422** | Unprocessable Entity | Valid format but semantic errors |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Server-side error |
| **503** | Service Unavailable | Service temporarily down |

### Request IDs

All requests should include an `X-Request-ID` header for distributed tracing:

```bash
curl https://api.octollm.example.com:8000/tasks \
  -H "X-Request-ID: $(uuidgen)" \
  -H "X-API-Key: $OCTOLLM_API_KEY"
```

**Benefits**:
- Track requests across services
- Debug issues with support team
- Monitor request flow in observability tools
- Correlate logs, metrics, and traces

---

## Error Handling

### Error Response Structure

All errors follow a consistent structure:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {
      "additional": "context-specific details"
    }
  },
  "request_id": "req_xyz789",
  "timestamp": "2025-11-11T12:00:00Z"
}
```

### Error Codes

#### Authentication Errors (401)

```json
{
  "error": {
    "code": "invalid_api_key",
    "message": "The provided API key is invalid or has been revoked"
  }
}
```

**Common Codes**:
- `invalid_api_key`: API key not recognized
- `expired_token`: Bearer token expired
- `missing_auth`: No authentication provided

**Solution**: Check API key, regenerate if needed

#### Authorization Errors (403)

```json
{
  "error": {
    "code": "insufficient_permissions",
    "message": "Your API key does not have permission to access this resource",
    "details": {
      "required_scope": "task:cancel",
      "provided_scopes": ["task:submit", "task:read"]
    }
  }
}
```

**Common Codes**:
- `insufficient_permissions`: Missing required scope
- `quota_exceeded`: Monthly quota exceeded
- `capability_denied`: Bearer token lacks capability

**Solution**: Upgrade plan or request additional permissions

#### Validation Errors (400, 422)

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": {
      "field": "budget.max_tokens",
      "constraint": "must be between 100 and 100000",
      "provided": 50
    }
  }
}
```

**Common Codes**:
- `validation_error`: Field constraint violation
- `missing_required_field`: Required field omitted
- `invalid_format`: Field format incorrect (e.g., invalid task_id pattern)

**Solution**: Review request body against API schema

#### Not Found Errors (404)

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Task with ID 'task_invalid123' not found"
  }
}
```

**Common Codes**:
- `resource_not_found`: Task, arm, or other resource doesn't exist
- `endpoint_not_found`: Invalid API endpoint

**Solution**: Verify resource ID, check for typos

#### Rate Limit Errors (429)

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit of 100 requests per minute exceeded",
    "details": {
      "limit": 100,
      "window": "60s",
      "retry_after": 45
    }
  }
}
```

**Response Headers**:
- `Retry-After: 45` (seconds until next retry allowed)
- `X-RateLimit-Limit: 100`
- `X-RateLimit-Remaining: 0`
- `X-RateLimit-Reset: 1699999999` (Unix timestamp)

**Solution**: Implement exponential backoff, respect `Retry-After` header

#### Server Errors (500, 503)

```json
{
  "error": {
    "code": "internal_server_error",
    "message": "An unexpected error occurred",
    "details": {
      "incident_id": "inc_xyz789"
    }
  }
}
```

**Common Codes**:
- `internal_server_error`: Unexpected server issue
- `service_unavailable`: Temporary outage (503)
- `timeout`: Request timed out internally

**Solution**: Retry with exponential backoff, contact support with `incident_id`

### Error Handling Best Practices

#### 1. Implement Retry Logic

```python
import time
from octollm_sdk import OrchestratorClient, RateLimitError, ServiceUnavailableError

client = OrchestratorClient(apiKey="...")

max_retries = 3
for attempt in range(max_retries):
    try:
        response = await client.submitTask({"goal": "..."})
        break
    except RateLimitError as e:
        if attempt < max_retries - 1:
            time.sleep(e.retryAfter or 60)
            continue
        raise
    except ServiceUnavailableError:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
        raise
```

#### 2. Log Request IDs

```python
import uuid

request_id = str(uuid.uuid4())
try:
    response = await client.submitTask(task, requestId=request_id)
except Exception as e:
    logger.error(f"Request {request_id} failed: {e}")
    # Include request_id when contacting support
```

#### 3. Handle Partial Failures

```python
# For batch operations, track successes and failures
results = {"success": [], "failed": []}

for task in tasks:
    try:
        response = await client.submitTask(task)
        results["success"].append(response.task_id)
    except ValidationError as e:
        results["failed"].append({"task": task, "error": str(e)})

print(f"Submitted {len(results['success'])} tasks, {len(results['failed'])} failed")
```

#### 4. Use Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise

# Usage
breaker = CircuitBreaker()
response = await breaker.call(client.submitTask, task)
```

---

## Rate Limiting & Quotas

### Rate Limits

Rate limits are enforced **per API key** and **per endpoint**:

| API Key Type | Requests/Minute | Requests/Hour | Requests/Day |
|--------------|-----------------|---------------|--------------|
| **Test** | 10 | 100 | 1,000 |
| **Live** | 100 | 5,000 | 100,000 |
| **Admin** | Unlimited | Unlimited | Unlimited |

### Rate Limit Headers

Every response includes rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699999999
Retry-After: 0
```

- **X-RateLimit-Limit**: Total requests allowed in current window
- **X-RateLimit-Remaining**: Requests remaining in current window
- **X-RateLimit-Reset**: Unix timestamp when window resets
- **Retry-After**: Seconds until next request allowed (only on 429)

### Resource Quotas

In addition to rate limits, resource quotas limit **total usage per month**:

| Plan | Monthly Tokens | Monthly Cost | Max Concurrent Tasks |
|------|----------------|--------------|----------------------|
| **Free** | 100,000 | $10 | 5 |
| **Pro** | 1,000,000 | $100 | 25 |
| **Enterprise** | Unlimited | Custom | Unlimited |

### Quota Exceeded Response

```json
{
  "error": {
    "code": "quota_exceeded",
    "message": "Monthly token quota of 100,000 exceeded",
    "details": {
      "quota_type": "tokens",
      "limit": 100000,
      "used": 100523,
      "resets_at": "2025-12-01T00:00:00Z"
    }
  }
}
```

### Best Practices for Rate Limiting

1. **Monitor Headers**: Check `X-RateLimit-Remaining` before requests
2. **Implement Backoff**: Use exponential backoff with jitter
3. **Batch Requests**: Combine multiple operations when possible
4. **Cache Responses**: Cache reflex layer outputs locally
5. **Upgrade Plan**: If consistently hitting limits

---

## API Versioning

OctoLLM uses **URL-based versioning** for major breaking changes:

```
https://api.octollm.example.com/v1/tasks
https://api.octollm.example.com/v2/tasks
```

### Current Version: v1 (Implicit)

During Phase 0, all endpoints are considered **v1** and do not require explicit version in URL:

```
https://api.octollm.example.com:8000/tasks  # Equivalent to /v1/tasks
```

### Version Migration

When v2 is released:
- **v1 endpoints remain available for 12 months**
- Deprecation warnings added to v1 responses
- Migration guide published at [docs.octollm.example.com/migrations](https://docs.octollm.example.com/migrations)

### Semantic Versioning for SDKs

SDKs follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes (e.g., v1 → v2 API migration)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Current SDK versions:
- Python SDK: `0.4.0`
- TypeScript SDK: `0.4.0`

---

## Common Patterns

### Pattern 1: Task Submission with Polling

```python
import asyncio
from octollm_sdk import OrchestratorClient

client = OrchestratorClient(apiKey="...")

# Submit task
response = await client.submitTask({
    "goal": "Analyze security vulnerabilities",
    "budget": {"max_tokens": 10000}
})

task_id = response.task_id
print(f"Task submitted: {task_id}")

# Poll for completion
while True:
    status = await client.getTask(task_id)
    print(f"Status: {status.status} ({status.progress.percentage if status.progress else 0}%)")

    if status.status in ("completed", "failed", "cancelled"):
        break

    await asyncio.sleep(2)

# Process result
if status.status == "completed":
    print(f"Result: {status.result.output}")
else:
    print(f"Task failed: {status.error.message if status.error else 'Unknown'}")
```

### Pattern 2: Multi-Arm Workflow

```python
from octollm_sdk import PlannerClient, CoderClient, JudgeClient

planner = PlannerClient(apiKey="...")
coder = CoderClient(apiKey="...")
judge = JudgeClient(apiKey="...")

# Step 1: Plan
plan = await planner.plan({
    "goal": "Create secure user authentication",
    "budget": {"max_tokens": 5000}
})

# Step 2: Generate code
code_result = await coder.code({
    "operation": "generate",
    "prompt": "Create Python Flask login function with bcrypt",
    "language": "python"
})

# Step 3: Validate
validation = await judge.validate({
    "output": code_result.code,
    "criteria": [
        "Uses bcrypt for password hashing",
        "Includes proper error handling",
        "No hardcoded secrets"
    ]
})

if validation.passed:
    print("Code passed validation!")
else:
    print("Validation failed:")
    for cr in validation.criteria_results:
        if not cr.passed:
            print(f"  - {cr.criterion}: {cr.explanation}")
```

### Pattern 3: Request Chaining

```python
# Submit task
task_response = await orchestrator.submitTask({
    "goal": "Scan network for vulnerabilities"
})

# Use task_id in subsequent requests
status = await orchestrator.getTask(task_response.task_id)

if status.status == "processing":
    # Cancel if needed
    await orchestrator.cancelTask(task_response.task_id)
```

### Pattern 4: Error Recovery

```python
from octollm_sdk import (
    OrchestratorClient,
    ValidationError,
    RateLimitError,
    TimeoutError
)

client = OrchestratorClient(apiKey="...")

async def submit_with_retry(task, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return await client.submitTask(task)
        except ValidationError as e:
            # Don't retry validation errors
            print(f"Validation failed: {e.message}")
            raise
        except RateLimitError as e:
            # Wait and retry
            if attempt < max_attempts - 1:
                await asyncio.sleep(e.retryAfter or 60)
                continue
            raise
        except TimeoutError:
            # Retry with longer timeout
            if attempt < max_attempts - 1:
                client.timeout *= 2
                continue
            raise
```

---

## Performance & Optimization

### Response Times by Service

| Service | P50 | P95 | P99 | Max |
|---------|-----|-----|-----|-----|
| Reflex (cache hit) | 5ms | 10ms | 15ms | 50ms |
| Reflex (cache miss) | 25ms | 50ms | 75ms | 100ms |
| Safety Guardian | 100ms | 200ms | 300ms | 500ms |
| Retriever | 150ms | 400ms | 600ms | 1000ms |
| Planner | 2s | 5s | 8s | 15s |
| Executor | 5s | 30s | 60s | 300s |
| Coder | 3s | 8s | 12s | 30s |
| Judge | 1s | 3s | 5s | 10s |
| Orchestrator (end-to-end) | 10s | 25s | 35s | 60s |

### Optimization Techniques

#### 1. Use Reflex Layer Caching

```python
# First request: Cache miss (300ms)
response1 = await reflex.preprocess({"input": "Analyze Flask app"})
# response1.cached = False

# Subsequent requests: Cache hit (5ms)
response2 = await reflex.preprocess({"input": "Analyze Flask app"})
# response2.cached = True
```

**Cache hit rate target**: >60%

#### 2. Batch Operations

Instead of:
```python
# Sequential: 3 requests × 200ms = 600ms
for query in queries:
    await retriever.search({"query": query})
```

Use:
```python
# Parallel: max(200ms) = 200ms
results = await asyncio.gather(*[
    retriever.search({"query": q}) for q in queries
])
```

#### 3. Set Budget Constraints

```python
# Prevent long-running tasks
task = await orchestrator.submitTask({
    "goal": "...",
    "budget": {
        "max_tokens": 5000,  # Lower = faster + cheaper
        "max_time_seconds": 30  # Hard timeout
    }
})
```

#### 4. Use Streaming (Future Feature)

```python
# Not yet implemented - planned for Sprint 1.2
async for chunk in orchestrator.submitTaskStream(task):
    print(chunk.partial_result)
```

#### 5. Monitor Performance

```python
import time

start = time.time()
response = await client.submitTask(task)
latency = time.time() - start

if latency > 30:
    logger.warn(f"Slow request: {latency}s for task {response.task_id}")
```

---

## Security Best Practices

### 1. Authentication Security

- **Never log API keys**: Redact in logs/monitoring
- **Use HTTPS only**: Enforce TLS 1.2+ in production
- **Rotate keys regularly**: Every 90 days minimum
- **Limit key scope**: Use capability tokens for arms
- **Monitor key usage**: Alert on unusual patterns

### 2. Input Validation

```python
# Always validate inputs before submission
def validate_task(task):
    if len(task["goal"]) < 10 or len(task["goal"]) > 2000:
        raise ValueError("Goal must be 10-2000 characters")

    if task.get("budget", {}).get("max_cost_dollars", 0) > 10:
        raise ValueError("Max cost must be ≤ $10")

    return task

# Use with API
clean_task = validate_task(user_input)
response = await client.submitTask(clean_task)
```

### 3. PII Protection

```python
# Always check for PII before submission
from octollm_sdk import SafetyClient

safety = SafetyClient(apiKey="...")

# Check content
safety_check = await safety.check({
    "content": user_provided_text,
    "check_pii": True
})

if safety_check.pii_detected:
    # Use redacted version
    clean_text = safety_check.redacted_content
    print(f"PII detected: {[e.type for e in safety_check.pii_entities]}")
else:
    clean_text = user_provided_text

# Submit clean task
await orchestrator.submitTask({"goal": clean_text})
```

### 4. Sandboxing (Executor)

```python
# Executor automatically sandboxes all commands
result = await executor.execute({
    "command": "nmap",
    "args": ["-sV", "target.com"],
    "timeout": 60  # Hard timeout
})

# Sandbox features:
# - Isolated containers (Docker/gVisor)
# - Network restrictions (no outbound by default)
# - Resource limits (CPU, memory, disk)
# - Command allowlisting
```

### 5. Rate Limit Handling

```python
# Monitor rate limits
response = await client.submitTask(task)
remaining = int(response.headers.get("X-RateLimit-Remaining", 0))

if remaining < 10:
    logger.warn(f"Rate limit low: {remaining} requests remaining")
    # Slow down requests
    await asyncio.sleep(1)
```

### 6. Error Message Sanitization

```python
# Don't expose internal details to end users
try:
    response = await client.submitTask(task)
except Exception as e:
    # Log full error internally
    logger.error(f"Task submission failed: {e}", exc_info=True)

    # Return sanitized message to user
    return {"error": "Task submission failed. Please try again later."}
```

### 7. Audit Logging

```python
# Log all API operations for security audits
import logging

audit_logger = logging.getLogger("audit")

def log_api_call(operation, user_id, task_id=None, status="success"):
    audit_logger.info({
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "user_id": user_id,
        "task_id": task_id,
        "status": status,
        "ip_address": request.remote_addr
    })

# Usage
response = await client.submitTask(task)
log_api_call("task:submit", user_id="user_123", task_id=response.task_id)
```

---

## SDK Usage

### Python SDK

#### Installation

```bash
pip install octollm-sdk
```

#### Basic Usage

```python
from octollm_sdk import OrchestratorClient

client = OrchestratorClient(
    baseUrl="https://api.octollm.example.com:8000",
    apiKey="your-api-key-here",
    timeout=30.0,
    maxRetries=3
)

# Submit task
response = await client.submitTask({
    "goal": "Analyze security",
    "budget": {"max_tokens": 10000}
})
```

#### All Service Clients

```python
from octollm_sdk import (
    OrchestratorClient,
    ReflexClient,
    PlannerClient,
    ExecutorClient,
    RetrieverClient,
    CoderClient,
    JudgeClient,
    SafetyClient
)

# Initialize all clients
orchestrator = OrchestratorClient(apiKey="...")
reflex = ReflexClient(apiKey="...")
planner = PlannerClient(apiKey="...")
executor = ExecutorClient(apiKey="...")
retriever = RetrieverClient(apiKey="...")
coder = CoderClient(apiKey="...")
judge = JudgeClient(apiKey="...")
safety = SafetyClient(apiKey="...")
```

#### Error Handling

```python
from octollm_sdk import (
    AuthenticationError,
    ValidationError,
    RateLimitError,
    NotFoundError
)

try:
    response = await client.submitTask(task)
except AuthenticationError:
    print("Invalid API key")
except ValidationError as e:
    print(f"Validation failed: {e.details}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retryAfter}s")
except NotFoundError:
    print("Task not found")
```

### TypeScript SDK

#### Installation

```bash
npm install octollm-sdk
```

#### Basic Usage

```typescript
import { OrchestratorClient } from 'octollm-sdk';

const client = new OrchestratorClient({
  baseUrl: 'https://api.octollm.example.com:8000',
  apiKey: 'your-api-key-here',
  timeout: 30000,
  maxRetries: 3
});

// Submit task
const response = await client.submitTask({
  goal: 'Analyze security',
  budget: { max_tokens: 10000 }
});
```

#### All Service Clients

```typescript
import {
  OrchestratorClient,
  ReflexClient,
  PlannerClient,
  ExecutorClient,
  RetrieverClient,
  CoderClient,
  JudgeClient,
  SafetyClient
} from 'octollm-sdk';

const orchestrator = new OrchestratorClient({ apiKey: '...' });
const reflex = new ReflexClient({ apiKey: '...' });
const planner = new PlannerClient({ apiKey: '...' });
const executor = new ExecutorClient({ apiKey: '...' });
const retriever = new RetrieverClient({ apiKey: '...' });
const coder = new CoderClient({ apiKey: '...' });
const judge = new JudgeClient({ apiKey: '...' });
const safety = new SafetyClient({ apiKey: '...' });
```

#### Error Handling

```typescript
import {
  AuthenticationError,
  ValidationError,
  RateLimitError,
  NotFoundError
} from 'octollm-sdk';

try {
  const response = await client.submitTask(task);
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof ValidationError) {
    console.error(`Validation failed: ${error.details}`);
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof NotFoundError) {
    console.error('Task not found');
  }
}
```

---

## API Reference

### Quick Reference Table

| Service | Endpoint | Method | Description |
|---------|----------|--------|-------------|
| **Orchestrator** | `/tasks` | POST | Submit new task |
| | `/tasks/{task_id}` | GET | Get task status |
| | `/tasks/{task_id}` | DELETE | Cancel task |
| | `/arms` | GET | List arms |
| **Reflex** | `/preprocess` | POST | Preprocess input |
| | `/cache/stats` | GET | Cache statistics |
| **Planner** | `/plan` | POST | Decompose task |
| **Executor** | `/execute` | POST | Execute command |
| | `/sandbox/{id}/status` | GET | Sandbox status |
| **Retriever** | `/search` | POST | Search knowledge base |
| **Coder** | `/code` | POST | Generate/debug code |
| **Judge** | `/validate` | POST | Validate output |
| **Safety** | `/check` | POST | Check content safety |

### Full Documentation

For complete API reference including:
- Request/response schemas
- Field descriptions and constraints
- Code examples in multiple languages
- Error codes and troubleshooting

See service-specific documentation:
- [Orchestrator API](./services/orchestrator.md)
- [Reflex Layer API](./services/reflex-layer.md)
- [Planner API](./services/planner.md)
- [Executor API](./services/executor.md)
- [Retriever API](./services/retriever.md)
- [Coder API](./services/coder.md)
- [Judge API](./services/judge.md)
- [Safety Guardian API](./services/safety-guardian.md)

---

## Support & Resources

### Documentation

- **API Reference**: [docs.octollm.example.com/api](https://docs.octollm.example.com/api)
- **Guides & Tutorials**: [docs.octollm.example.com/guides](https://docs.octollm.example.com/guides)
- **SDK Documentation**:
  - Python: [docs.octollm.example.com/sdk/python](https://docs.octollm.example.com/sdk/python)
  - TypeScript: [docs.octollm.example.com/sdk/typescript](https://docs.octollm.example.com/sdk/typescript)

### Community

- **GitHub**: [github.com/octollm/octollm](https://github.com/octollm/octollm)
- **Discord**: [discord.gg/octollm](https://discord.gg/octollm)
- **Stack Overflow**: Tag `octollm`

### Support

- **Email**: support@octollm.example.com
- **Status Page**: [status.octollm.example.com](https://status.octollm.example.com)
- **Issue Tracker**: [github.com/octollm/octollm/issues](https://github.com/octollm/octollm/issues)

### Service Level Agreement (SLA)

| Plan | Uptime | Support Response | Support Hours |
|------|--------|------------------|---------------|
| **Free** | 95% | 48 hours | Business hours |
| **Pro** | 99% | 12 hours | 24/5 |
| **Enterprise** | 99.9% | 1 hour | 24/7 |

---

**End of API Overview**

For service-specific details, see the documentation links above.

**Last Updated**: 2025-11-11
**Version**: 0.4.0
**Sprint**: 0.5 (Phase 0: Foundation)
