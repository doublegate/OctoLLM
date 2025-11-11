# Orchestrator API Reference

**Service**: Orchestrator (Central Brain)
**Port**: 8000
**Base URL**: `http://localhost:8000` (development), `https://api.octollm.example.com:8000` (production)
**Technology**: Python 3.11+ / FastAPI
**Cost Tier**: 5 (Expensive - uses GPT-4/Claude Opus)
**Average Latency**: 5-30 seconds

## Overview

The Orchestrator is the central brain of the OctoLLM system. It coordinates task planning, arm delegation, and result integration. Think of it as the conductor of an orchestra, managing when and how each specialized arm (instrument) contributes to the overall performance.

### Capabilities

- **Task Submission**: Accept complex natural language tasks from clients
- **Task Decomposition**: Break tasks into executable subtasks (via Planner arm)
- **Arm Coordination**: Delegate subtasks to specialized arms (Executor, Coder, etc.)
- **Result Synthesis**: Integrate outputs from multiple arms into coherent response
- **Progress Tracking**: Real-time task status and progress updates
- **Quality Assurance**: Validate outputs against acceptance criteria (via Judge arm)

### Key Features

- **Frontier LLM**: Uses GPT-4 or Claude Opus for strategic planning
- **Parallel Execution**: Runs independent subtasks concurrently
- **Budget Enforcement**: Respects token, time, and cost constraints
- **Fault Tolerance**: Graceful degradation when arms fail
- **Observability**: Comprehensive logging, metrics, and tracing

---

## Authentication

All Orchestrator endpoints require authentication:

**API Key** (recommended):
```bash
curl https://api.octollm.example.com:8000/tasks \
  -H "X-API-Key: octollm_live_1234567890abcdef"
```

**Bearer Token** (for inter-service communication):
```bash
curl https://api.octollm.example.com:8000/tasks \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details.

---

## Endpoints

### POST /tasks

Submit a new task to the orchestrator for execution.

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `X-API-Key: <api-key>` or `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "goal": "Natural language description of the task (10-2000 chars)",
  "constraints": [
    "Optional constraint 1",
    "Optional constraint 2"
  ],
  "acceptance_criteria": [
    "Success condition 1",
    "Success condition 2"
  ],
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

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `goal` | string | ✅ | 10-2000 chars | Natural language task description |
| `constraints` | array[string] | ❌ | max 10 items | Hard constraints that must be satisfied |
| `acceptance_criteria` | array[string] | ❌ | max 10 items | Success conditions for validation |
| `context` | object | ❌ | max 10KB | Additional context and metadata |
| `budget.max_tokens` | integer | ❌ | 100-100,000 | Maximum LLM tokens (default: 10,000) |
| `budget.max_time_seconds` | integer | ❌ | 5-300 | Maximum execution time (default: 60) |
| `budget.max_cost_dollars` | float | ❌ | 0.01-10.0 | Maximum cost in USD (default: 1.0) |

#### Response

**Status**: 201 Created

**Body**:

```json
{
  "task_id": "task_abc123xyz456",
  "status": "queued",
  "created_at": "2025-11-11T12:00:00Z",
  "estimated_completion": "2025-11-11T12:02:00Z"
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique task identifier (format: `task_[a-zA-Z0-9]{16}`) |
| `status` | enum | Task status: `queued`, `processing`, `completed`, `failed`, `cancelled` |
| `created_at` | datetime | Task creation timestamp (ISO 8601) |
| `estimated_completion` | datetime | Estimated completion time (null if cannot estimate) |

#### Examples

**Example 1: Security Analysis**

```bash
curl -X POST https://api.octollm.example.com:8000/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OCTOLLM_API_KEY" \
  -d '{
    "goal": "Analyze the security vulnerabilities in the provided Python Flask application",
    "constraints": [
      "Focus on OWASP Top 10 vulnerabilities",
      "Include SQL injection and XSS analysis"
    ],
    "acceptance_criteria": [
      "All high-severity vulnerabilities identified",
      "Remediation recommendations provided",
      "Code examples for fixes included"
    ],
    "context": {
      "framework": "Flask",
      "python_version": "3.11",
      "authentication": "JWT"
    },
    "budget": {
      "max_tokens": 10000,
      "max_time_seconds": 120,
      "max_cost_dollars": 1.0
    }
  }'
```

**Response**:

```json
{
  "task_id": "task_sec789analysis",
  "status": "queued",
  "created_at": "2025-11-11T12:00:00Z",
  "estimated_completion": "2025-11-11T12:02:00Z"
}
```

**Example 2: Network Scan (Python SDK)**

```python
from octollm_sdk import OrchestratorClient

client = OrchestratorClient(
    apiKey="octollm_live_1234567890abcdef"
)

response = await client.submitTask({
    "goal": "Scan network 192.168.1.0/24 for open ports and services",
    "constraints": [
        "Use only passive scanning techniques",
        "Do not exceed 100 requests per second"
    ],
    "budget": {
        "max_tokens": 5000,
        "max_time_seconds": 300,
        "max_cost_dollars": 0.50
    }
})

print(f"Task ID: {response.task_id}")
```

**Example 3: Code Generation (TypeScript SDK)**

```typescript
import { OrchestratorClient } from 'octollm-sdk';

const client = new OrchestratorClient({
  apiKey: 'octollm_live_1234567890abcdef'
});

const response = await client.submitTask({
  goal: 'Generate a Python FastAPI endpoint for user registration with email validation',
  acceptance_criteria: [
    'Uses Pydantic for request validation',
    'Includes proper error handling',
    'Follows REST best practices'
  ],
  budget: {
    max_tokens: 8000
  }
});

console.log(`Task ID: ${response.task_id}`);
```

#### Error Responses

**400 Bad Request - Validation Error**:

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
  "request_id": "req_xyz789"
}
```

**401 Unauthorized - Invalid API Key**:

```json
{
  "error": {
    "code": "invalid_api_key",
    "message": "The provided API key is invalid or has been revoked"
  }
}
```

**429 Too Many Requests - Rate Limit Exceeded**:

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

---

### GET /tasks/{task_id}

Retrieve the status and results of a submitted task.

#### Request

**Path Parameters**:
- `task_id` (string, required): Task identifier returned from POST /tasks

**Headers**:
- `X-API-Key: <api-key>` or `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional)

#### Response

**Status**: 200 OK

**Body**:

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

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Task identifier |
| `status` | enum | Current status: `queued`, `processing`, `completed`, `failed`, `cancelled` |
| `created_at` | datetime | Task creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `progress` | object | Progress information (null if not started) |
| `progress.current_step` | enum | Current step: `preprocessing`, `planning`, `execution`, `validation`, `synthesis` |
| `progress.completed_steps` | integer | Number of completed steps |
| `progress.total_steps` | integer | Total number of steps |
| `progress.percentage` | integer | Progress percentage (0-100) |
| `result` | object | Task result (null if not completed) |
| `result.output` | string | Primary output |
| `result.confidence` | float | Confidence score (0.0-1.0) |
| `result.validation_passed` | boolean | Whether output passed acceptance criteria |
| `error` | object | Error information (only if status is `failed`) |

#### Examples

**Example 1: Task In Progress**

```bash
curl https://api.octollm.example.com:8000/tasks/task_abc123xyz456 \
  -H "X-API-Key: $OCTOLLM_API_KEY"
```

**Response**:

```json
{
  "task_id": "task_abc123xyz456",
  "status": "processing",
  "created_at": "2025-11-11T12:00:00Z",
  "updated_at": "2025-11-11T12:01:15Z",
  "progress": {
    "current_step": "execution",
    "completed_steps": 3,
    "total_steps": 5,
    "percentage": 60
  }
}
```

**Example 2: Task Completed (Python SDK)**

```python
status = await client.getTask("task_abc123xyz456")

if status.status == "completed":
    print(f"Output: {status.result.output}")
    print(f"Confidence: {status.result.confidence}")
    print(f"Validation: {'✓' if status.result.validation_passed else '✗'}")
elif status.status == "processing":
    print(f"Progress: {status.progress.percentage}%")
elif status.status == "failed":
    print(f"Error: {status.error.message}")
```

**Example 3: Polling Pattern (TypeScript SDK)**

```typescript
async function waitForCompletion(taskId: string, maxAttempts: number = 60): Promise<TaskStatusResponse> {
  for (let i = 0; i < maxAttempts; i++) {
    const status = await client.getTask(taskId);
    console.log(`Status: ${status.status} (${status.progress?.percentage || 0}%)`);

    if (['completed', 'failed', 'cancelled'].includes(status.status)) {
      return status;
    }

    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2s
  }

  throw new Error('Task timeout');
}

const finalStatus = await waitForCompletion('task_abc123xyz456');
```

#### Error Responses

**404 Not Found - Task Not Found**:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Task with ID 'task_invalid123' not found"
  }
}
```

---

### DELETE /tasks/{task_id}

Cancel a running task.

#### Request

**Path Parameters**:
- `task_id` (string, required): Task identifier

**Headers**:
- `X-API-Key: <api-key>` or `Authorization: Bearer <token>` (required)

#### Response

**Status**: 200 OK

**Body**:

```json
{
  "task_id": "task_abc123xyz456",
  "status": "cancelled",
  "created_at": "2025-11-11T12:00:00Z",
  "updated_at": "2025-11-11T12:01:30Z"
}
```

#### Examples

**Example 1: Cancel Task (curl)**

```bash
curl -X DELETE https://api.octollm.example.com:8000/tasks/task_abc123xyz456 \
  -H "X-API-Key: $OCTOLLM_API_KEY"
```

**Example 2: Cancel with Timeout (Python SDK)**

```python
# Cancel if task takes too long
import asyncio

async def submit_with_timeout(task, timeout_seconds=60):
    response = await client.submitTask(task)
    task_id = response.task_id

    try:
        await asyncio.wait_for(
            wait_for_completion(task_id),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        await client.cancelTask(task_id)
        raise Exception(f"Task {task_id} cancelled due to timeout")
```

#### Error Responses

**400 Bad Request - Cannot Cancel Completed Task**:

```json
{
  "error": {
    "code": "invalid_operation",
    "message": "Cannot cancel task in 'completed' status"
  }
}
```

---

### GET /arms

List all registered arms and their capabilities.

#### Request

**Headers**:
- `X-API-Key: <api-key>` or `Authorization: Bearer <token>` (required)

#### Response

**Status**: 200 OK

**Body**:

```json
{
  "arms": [
    {
      "arm_id": "planner",
      "name": "Planner Arm",
      "description": "Decomposes complex tasks into executable subtasks",
      "input_schema": {...},
      "output_schema": {...},
      "capabilities": ["task:decompose", "planning"],
      "cost_tier": 3,
      "endpoint": "http://planner:8002"
    },
    ...
  ]
}
```

#### Examples

**Example 1: List Arms (curl)**

```bash
curl https://api.octollm.example.com:8000/arms \
  -H "X-API-Key: $OCTOLLM_API_KEY"
```

**Example 2: Discover Capabilities (Python SDK)**

```python
response = await client.listArms()

print(f"Registered arms: {len(response.arms)}")
for arm in response.arms:
    print(f"  - {arm.name} ({arm.arm_id}): {', '.join(arm.capabilities)}")
    print(f"    Cost tier: {arm.cost_tier}, Endpoint: {arm.endpoint}")
```

---

## Data Models

### TaskRequest

```typescript
interface TaskRequest {
  goal: string;                    // 10-2000 chars
  constraints?: string[];          // max 10 items
  acceptance_criteria?: string[];  // max 10 items
  context?: Record<string, any>;   // max 10KB
  budget?: ResourceBudget;
}
```

### ResourceBudget

```typescript
interface ResourceBudget {
  max_tokens?: number;        // 100-100,000 (default: 10,000)
  max_time_seconds?: number;  // 5-300 (default: 60)
  max_cost_dollars?: number;  // 0.01-10.0 (default: 1.0)
}
```

### TaskResponse

```typescript
interface TaskResponse {
  task_id: string;                   // format: task_[a-zA-Z0-9]{16}
  status: TaskStatus;
  created_at: string;                // ISO 8601 datetime
  estimated_completion?: string;     // ISO 8601 datetime
}
```

### TaskStatusResponse

```typescript
interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  created_at: string;
  updated_at?: string;
  progress?: TaskProgress;
  result?: TaskResult;
  error?: TaskError;
}
```

### TaskStatus

```typescript
type TaskStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';
```

### TaskProgress

```typescript
interface TaskProgress {
  current_step: ProcessingStep;
  completed_steps: number;
  total_steps: number;
  percentage: number;  // 0-100
}
```

### ProcessingStep

```typescript
type ProcessingStep =
  | 'preprocessing'
  | 'planning'
  | 'execution'
  | 'validation'
  | 'synthesis';
```

### TaskResult

```typescript
interface TaskResult {
  output: string;
  confidence: number;           // 0.0-1.0
  validation_passed: boolean;
}
```

### TaskError

```typescript
interface TaskError {
  type: string;
  message: string;
  details?: string;
}
```

---

## Integration Patterns

### Pattern 1: Submit and Poll

```python
# Submit task
response = await orchestrator.submitTask({
    "goal": "Analyze security vulnerabilities",
    "budget": {"max_tokens": 10000}
})

# Poll until complete
while True:
    status = await orchestrator.getTask(response.task_id)
    if status.status in ("completed", "failed", "cancelled"):
        break
    await asyncio.sleep(2)

# Process result
if status.status == "completed":
    print(status.result.output)
```

### Pattern 2: Timeout and Cancel

```python
import asyncio

async def execute_with_timeout(task, timeout=60):
    response = await orchestrator.submitTask(task)

    try:
        return await asyncio.wait_for(
            poll_until_complete(response.task_id),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        await orchestrator.cancelTask(response.task_id)
        raise
```

### Pattern 3: Batch Processing

```python
# Submit multiple tasks in parallel
tasks = [{"goal": f"Task {i}"} for i in range(10)]
responses = await asyncio.gather(*[
    orchestrator.submitTask(task) for task in tasks
])

# Track all task IDs
task_ids = [r.task_id for r in responses]

# Poll all tasks
while task_ids:
    statuses = await asyncio.gather(*[
        orchestrator.getTask(tid) for tid in task_ids
    ])

    # Remove completed
    task_ids = [
        s.task_id for s in statuses
        if s.status not in ("completed", "failed", "cancelled")
    ]

    await asyncio.sleep(2)
```

---

## Performance Characteristics

### Latency

| Operation | P50 | P95 | P99 | Max |
|-----------|-----|-----|-----|-----|
| POST /tasks | 200ms | 500ms | 1s | 2s |
| GET /tasks/{id} | 50ms | 100ms | 200ms | 500ms |
| DELETE /tasks/{id} | 100ms | 200ms | 300ms | 500ms |
| GET /arms | 20ms | 50ms | 100ms | 200ms |

**End-to-end task completion**: 5-30 seconds (P50-P99)

### Throughput

- **Max concurrent tasks per API key**: 25 (Pro), 5 (Free)
- **Task submission rate limit**: 100 req/min (Live key)
- **Task status polling rate limit**: 1000 req/min

### Cost

**Cost per task** (average):
- Simple tasks (1-2 arms): $0.05-$0.10
- Medium tasks (3-5 arms): $0.20-$0.50
- Complex tasks (5+ arms): $0.50-$2.00

---

## Troubleshooting

### Common Issues

**1. "Goal must be between 10 and 2000 characters"**
- **Cause**: Goal too short or too long
- **Solution**: Ensure goal is descriptive but concise (10-2000 chars)

**2. "Rate limit exceeded"**
- **Cause**: Too many requests in short time
- **Solution**: Implement exponential backoff, respect `Retry-After` header

**3. "Task not found"**
- **Cause**: Invalid task_id or task expired
- **Solution**: Verify task_id, tasks are retained for 30 days

**4. "Budget exceeded"**
- **Cause**: Task exceeded budget constraints
- **Solution**: Increase budget or simplify task goal

**5. "Task timeout"**
- **Cause**: Task exceeded max_time_seconds
- **Solution**: Increase timeout or break task into smaller subtasks

### Debug Tips

1. **Use Request IDs**: Include `X-Request-ID` header for tracing
2. **Check Progress**: Monitor `progress.percentage` for execution status
3. **Review Logs**: Access logs at [api.octollm.example.com/logs](https://api.octollm.example.com/logs)
4. **Monitor Metrics**: View task metrics at [api.octollm.example.com/metrics](https://api.octollm.example.com/metrics)

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Planner API](./planner.md)
- [Executor API](./executor.md)
- [Judge API](./judge.md)
- [Python SDK Documentation](https://docs.octollm.example.com/sdk/python)
- [TypeScript SDK Documentation](https://docs.octollm.example.com/sdk/typescript)

---

**Last Updated**: 2025-11-11
**Version**: 0.4.0
**Sprint**: 0.5 (Phase 0: Foundation)
