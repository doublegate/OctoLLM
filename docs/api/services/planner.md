# Planner Arm API Reference

**Service**: Planner Arm (Task Decomposition Specialist)
**Port**: 8002
**Base URL**: `http://localhost:8002` (development), `http://planner:8002` (internal)
**Technology**: Python 3.11+ / FastAPI
**Cost Tier**: 2 (Medium - uses GPT-3.5-turbo)
**Average Latency**: 1-3 seconds

## Overview

The Planner Arm is the strategic thinking component of OctoLLM. It breaks down complex, ambiguous goals into concrete, ordered subtasks with clear acceptance criteria. Think of it as the project manager that transforms "build me a website" into a detailed step-by-step plan with assigned responsibilities.

### Capabilities

- **Goal Analysis**: Parse and understand complex natural language goals
- **Task Decomposition**: Break goals into 2-10 executable subtasks
- **Arm Assignment**: Route each subtask to the appropriate specialist arm
- **Dependency Management**: Identify which tasks must run sequentially vs. in parallel
- **Acceptance Criteria**: Generate measurable success conditions for each step
- **Time Estimation**: Predict execution time for each subtask

### Key Features

- **Hierarchical Planning**: Supports recursive decomposition for complex tasks
- **Context-Aware**: Uses constraints and context to inform planning decisions
- **Confidence Scoring**: Returns confidence level (0.0-1.0) for plan quality
- **Fast Iteration**: GPT-3.5-turbo enables 1-3 second planning
- **Parallel Detection**: Identifies independent tasks for concurrent execution
- **Budget-Conscious**: Estimates token/cost requirements per step

---

## Authentication

All Planner endpoints require Bearer token authentication (inter-service communication):

```bash
curl http://planner:8002/plan \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Research CVE-2024-12345",
    "constraints": ["Use only public sources"]
  }'
```

**Note**: The Planner is typically called by the Orchestrator, not directly by external clients. External clients should use the [Orchestrator API](./orchestrator.md) which handles authentication and coordinates arm communication.

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details on capability-based tokens.

---

## Endpoints

### POST /plan

Create an execution plan by decomposing a goal into ordered subtasks.

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "goal": "Research and exploit CVE-2024-12345 in nginx",
  "constraints": [
    "Use only public sources",
    "Complete within 60 seconds"
  ],
  "context": {
    "target": "nginx/1.24.0",
    "environment": "test"
  }
}
```

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `goal` | string | ✅ | 10-1000 chars | Natural language description of what to accomplish |
| `constraints` | array | ❌ | - | Hard constraints (time, resources, scope limitations) |
| `context` | object | ❌ | - | Additional information to inform planning (target versions, environment, etc.) |

#### Response

**Status**: 200 OK

```json
{
  "plan_id": "plan_abc123",
  "steps": [
    {
      "step_number": 1,
      "action": "Search for CVE-2024-12345 details",
      "arm_id": "retriever",
      "acceptance_criteria": [
        "CVE description retrieved",
        "Affected versions identified"
      ],
      "estimated_duration_seconds": 10,
      "dependencies": []
    },
    {
      "step_number": 2,
      "action": "Generate exploitation proof-of-concept",
      "arm_id": "coder",
      "acceptance_criteria": [
        "Working PoC code generated",
        "Includes safety warnings"
      ],
      "estimated_duration_seconds": 20,
      "dependencies": [1]
    },
    {
      "step_number": 3,
      "action": "Validate exploitation code",
      "arm_id": "judge",
      "acceptance_criteria": [
        "Code syntax valid",
        "Ethical considerations included"
      ],
      "estimated_duration_seconds": 5,
      "dependencies": [2]
    }
  ],
  "total_estimated_duration": 35,
  "confidence": 0.88
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `plan_id` | string | Unique plan identifier (format: `plan_<alphanumeric>`) |
| `steps` | array | Ordered list of subtasks (1-indexed) |
| `steps[].step_number` | integer | Step position in execution order |
| `steps[].action` | string | Natural language description of what to do |
| `steps[].arm_id` | string | Target arm: `planner`, `executor`, `retriever`, `coder`, `judge`, `safety-guardian` |
| `steps[].acceptance_criteria` | array | Success conditions (checked by Judge arm) |
| `steps[].estimated_duration_seconds` | integer | Predicted execution time |
| `steps[].dependencies` | array | Step numbers that must complete first (empty = can run immediately) |
| `total_estimated_duration` | integer | Sum of all step durations (assumes sequential execution) |
| `confidence` | number | Plan quality confidence (0.0-1.0, typically >0.75 for production use) |

#### Examples

**Example 1: Security Research Plan (Bash)**

```bash
curl -X POST http://planner:8002/plan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "goal": "Research and exploit CVE-2024-12345 in nginx",
    "constraints": [
      "Use only public sources",
      "Complete within 60 seconds"
    ],
    "context": {
      "target": "nginx/1.24.0"
    }
  }'

# Response:
{
  "plan_id": "plan_abc123",
  "steps": [
    {
      "step_number": 1,
      "action": "Search for CVE-2024-12345 details",
      "arm_id": "retriever",
      "acceptance_criteria": [
        "CVE description retrieved",
        "Affected versions identified"
      ],
      "estimated_duration_seconds": 10,
      "dependencies": []
    },
    {
      "step_number": 2,
      "action": "Generate exploitation proof-of-concept",
      "arm_id": "coder",
      "acceptance_criteria": [
        "Working PoC code generated",
        "Includes safety warnings"
      ],
      "estimated_duration_seconds": 20,
      "dependencies": [1]
    },
    {
      "step_number": 3,
      "action": "Validate exploitation code",
      "arm_id": "judge",
      "acceptance_criteria": [
        "Code syntax valid",
        "Ethical considerations included"
      ],
      "estimated_duration_seconds": 5,
      "dependencies": [2]
    }
  ],
  "total_estimated_duration": 35,
  "confidence": 0.88
}
```

**Example 2: Code Refactoring Plan (Python SDK)**

```python
from octollm_sdk import PlannerClient

client = PlannerClient(bearer_token="service_token_abc123")

plan = await client.create_plan({
    "goal": "Refactor authentication module to use JWT tokens",
    "constraints": [
        "Maintain backward compatibility",
        "Add comprehensive tests"
    ],
    "context": {
        "language": "Python",
        "framework": "Flask",
        "current_auth": "session-based"
    }
})

print(f"Plan ID: {plan.plan_id}")
print(f"Total steps: {len(plan.steps)}")
print(f"Estimated time: {plan.total_estimated_duration}s")
print(f"Confidence: {plan.confidence * 100:.1f}%")

# Print execution order
for step in plan.steps:
    deps = f" (depends on: {step.dependencies})" if step.dependencies else ""
    print(f"{step.step_number}. {step.action} → {step.arm_id}{deps}")

# Output:
# Plan ID: plan_def456
# Total steps: 5
# Estimated time: 45s
# Confidence: 92.3%
# 1. Analyze current authentication code → coder
# 2. Design JWT token schema → coder (depends on: [1])
# 3. Implement JWT authentication → coder (depends on: [2])
# 4. Write unit and integration tests → coder (depends on: [3])
# 5. Validate implementation meets criteria → judge (depends on: [4])
```

**Example 3: Parallel Task Detection (TypeScript SDK)**

```typescript
import { PlannerClient } from 'octollm-sdk';

const client = new PlannerClient({
  bearerToken: process.env.SERVICE_TOKEN
});

const plan = await client.createPlan({
  goal: 'Scan network 192.168.1.0/24 for vulnerabilities',
  constraints: [
    'Scan ports 22, 80, 443, 3306, 5432',
    'Complete within 120 seconds'
  ],
  context: {
    scan_type: 'stealth'
  }
});

// Identify parallel tasks (no dependencies)
const parallelSteps = plan.steps.filter(step => step.dependencies.length === 0);
const sequentialSteps = plan.steps.filter(step => step.dependencies.length > 0);

console.log(`Parallel tasks (${parallelSteps.length}):`);
parallelSteps.forEach(step => {
  console.log(`  - Step ${step.step_number}: ${step.action} (${step.arm_id})`);
});

console.log(`\nSequential tasks (${sequentialSteps.length}):`);
sequentialSteps.forEach(step => {
  console.log(`  - Step ${step.step_number}: ${step.action} (depends on: ${step.dependencies})`);
});

// Execute parallel steps concurrently
const parallelPromises = parallelSteps.map(step =>
  executeStep(step)  // Execute via Orchestrator
);

await Promise.all(parallelPromises);
```

**Example 4: Low Confidence Plan Handling (Python SDK)**

```python
from octollm_sdk import PlannerClient

client = PlannerClient(bearer_token="service_token_abc123")

plan = await client.create_plan({
    "goal": "Hack into government database",  # Vague, unethical goal
    "constraints": []
})

# Check confidence before executing
if plan.confidence < 0.75:
    print(f"⚠️ Low confidence plan ({plan.confidence * 100:.1f}%)")
    print("Possible reasons:")
    print("  - Goal is too vague")
    print("  - Goal may be unethical")
    print("  - Insufficient context provided")

    # Ask user for clarification
    print("\nOriginal goal:", plan.steps[0].action if plan.steps else "N/A")
    print("Please refine the goal and try again.")
else:
    # Proceed with execution
    print(f"✓ High confidence plan ({plan.confidence * 100:.1f}%)")
    # Execute steps...
```

#### Error Responses

**400 Bad Request** (invalid goal):

```json
{
  "error": "ValidationError",
  "message": "Goal must be between 10 and 1000 characters",
  "details": {
    "field": "goal",
    "value_length": 5
  }
}
```

**401 Unauthorized** (missing or invalid token):

```json
{
  "error": "Unauthorized",
  "message": "Bearer token required for planning operations"
}
```

---

### GET /capabilities

Retrieve planner capabilities and supported features.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "capabilities": [
    "task_decomposition",
    "goal_analysis",
    "acceptance_criteria_generation"
  ]
}
```

#### Examples

**Example 1: Check Capabilities (Bash)**

```bash
curl -X GET http://planner:8002/capabilities

# Response:
{
  "capabilities": [
    "task_decomposition",
    "goal_analysis",
    "acceptance_criteria_generation"
  ]
}
```

---

### GET /health

Health check endpoint for load balancers and monitoring systems.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "status": "healthy",
  "version": "0.3.0"
}
```

#### Examples

**Example 1: Kubernetes Liveness Probe**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8002
  initialDelaySeconds: 30
  periodSeconds: 10
```

---

### GET /metrics

Prometheus metrics endpoint for observability.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK
**Content-Type**: text/plain

```
# HELP planner_plans_total Total number of plans created
# TYPE planner_plans_total counter
planner_plans_total 1523

# HELP planner_avg_steps Average number of steps per plan
# TYPE planner_avg_steps gauge
planner_avg_steps 4.2

# HELP planner_avg_confidence Average plan confidence
# TYPE planner_avg_confidence gauge
planner_avg_confidence 0.87

# HELP planner_latency_seconds Plan generation latency
# TYPE planner_latency_seconds histogram
planner_latency_seconds_bucket{le="1.0"} 892
planner_latency_seconds_bucket{le="2.0"} 1401
planner_latency_seconds_bucket{le="3.0"} 1523
```

---

## Data Models

### PlanRequest

```typescript
interface PlanRequest {
  goal: string;                // 10-1000 chars
  constraints?: string[];      // Optional hard constraints
  context?: {                  // Optional additional info
    [key: string]: any;
  };
}
```

### PlanResponse

```typescript
interface PlanResponse {
  plan_id: string;             // Format: plan_<alphanumeric>
  steps: PlanStep[];           // 1-10 ordered steps
  total_estimated_duration: number;  // Seconds (sum of step durations)
  confidence: number;          // 0.0-1.0 (plan quality score)
}
```

### PlanStep

```typescript
type ArmId =
  | 'planner'
  | 'executor'
  | 'retriever'
  | 'coder'
  | 'judge'
  | 'safety-guardian';

interface PlanStep {
  step_number: number;         // 1-indexed position
  action: string;              // Natural language description
  arm_id: ArmId;               // Target arm for execution
  acceptance_criteria: string[];  // Success conditions
  estimated_duration_seconds: number;
  dependencies: number[];      // Step numbers that must complete first
}
```

---

## Integration Patterns

### Pattern 1: Orchestrator-Driven Planning

The Orchestrator calls the Planner to decompose tasks, then executes the plan.

```python
from octollm_sdk import PlannerClient, ExecutorClient, CoderClient

planner = PlannerClient(bearer_token="service_token_abc123")

async def execute_task(goal: str, constraints: list):
    # Step 1: Create plan
    plan = await planner.create_plan({
        "goal": goal,
        "constraints": constraints
    })

    if plan.confidence < 0.75:
        raise ValueError(f"Low confidence plan: {plan.confidence}")

    # Step 2: Execute each step in order
    results = {}
    for step in plan.steps:
        # Check dependencies
        for dep in step.dependencies:
            if dep not in results:
                raise RuntimeError(f"Dependency {dep} not satisfied")

        # Route to appropriate arm
        if step.arm_id == "executor":
            result = await executor.execute(step.action)
        elif step.arm_id == "coder":
            result = await coder.generate(step.action)
        # ... other arms

        results[step.step_number] = result

    return results
```

### Pattern 2: Recursive Planning for Complex Tasks

For very complex tasks, the Planner can be called recursively.

```typescript
import { PlannerClient } from 'octollm-sdk';

const planner = new PlannerClient({ bearerToken: '...' });

async function recursivePlan(goal: string, depth: number = 0): Promise<any[]> {
  if (depth > 3) {
    throw new Error('Maximum planning depth exceeded');
  }

  const plan = await planner.createPlan({ goal });

  // If plan has >7 steps, decompose complex steps further
  const expandedSteps = [];
  for (const step of plan.steps) {
    if (step.estimated_duration_seconds > 30) {
      // Recursively plan this complex step
      console.log(`Decomposing complex step: ${step.action}`);
      const subPlan = await recursivePlan(step.action, depth + 1);
      expandedSteps.push(...subPlan);
    } else {
      expandedSteps.push(step);
    }
  }

  return expandedSteps;
}

// Example: Complex multi-stage attack
const fullPlan = await recursivePlan(
  'Perform complete penetration test on target.example.com'
);

console.log(`Total steps after decomposition: ${fullPlan.length}`);
```

### Pattern 3: Confidence-Based Replanning

If plan confidence is low, replan with additional context.

```python
from octollm_sdk import PlannerClient

planner = PlannerClient(bearer_token="service_token_abc123")

async def create_high_confidence_plan(goal: str, max_attempts: int = 3):
    attempt = 0
    context = {}

    while attempt < max_attempts:
        plan = await planner.create_plan({
            "goal": goal,
            "context": context
        })

        if plan.confidence >= 0.80:
            return plan

        # Add more context based on plan shortcomings
        print(f"Attempt {attempt + 1}: Low confidence ({plan.confidence})")
        context["previous_plan_id"] = plan.plan_id
        context["attempt"] = attempt + 1

        # Ask LLM to analyze why confidence is low (not shown)
        # Add clarifying context...

        attempt += 1

    raise ValueError("Could not create high-confidence plan")
```

---

## Performance Characteristics

| Scenario | P50 | P95 | P99 | Max | Notes |
|----------|-----|-----|-----|-----|-------|
| Simple Goal (2-3 steps) | 1.2s | 2.1s | 2.8s | 4.0s | GPT-3.5-turbo latency |
| Medium Goal (4-6 steps) | 1.8s | 2.9s | 3.5s | 5.2s | More reasoning required |
| Complex Goal (7-10 steps) | 2.5s | 4.1s | 5.0s | 7.8s | Multiple LLM passes |

### Token Usage

| Scenario | Input Tokens | Output Tokens | Total | Cost (GPT-3.5) |
|----------|--------------|---------------|-------|----------------|
| Simple Goal | ~200 | ~150 | ~350 | $0.00035 |
| Medium Goal | ~300 | ~300 | ~600 | $0.00060 |
| Complex Goal | ~400 | ~500 | ~900 | $0.00090 |

**Note**: GPT-3.5-turbo pricing: $0.0005 / 1K input tokens, $0.0015 / 1K output tokens

---

## Troubleshooting

### Issue 1: Low Confidence Plans (<0.70)

**Symptoms**: Plan confidence consistently below 0.70, steps are vague or illogical

**Possible Causes**:
- Goal is too ambiguous
- Insufficient context provided
- Goal is unethical or impossible

**Solutions**:
```python
# Add more context
plan = await planner.create_plan({
    "goal": "Analyze web app security",
    "context": {
        "framework": "Flask",
        "python_version": "3.11",
        "authentication": "JWT",
        "known_issues": ["CSRF vulnerabilities"]
    }
})

# Refine vague goals
# Bad: "Hack the system"
# Good: "Identify and document SQL injection vulnerabilities in login form"
```

### Issue 2: Too Many Steps (>10)

**Symptoms**: Plans with 15+ steps, total_estimated_duration >300s

**Possible Causes**:
- Goal is too complex for single plan
- Planner over-decomposing simple tasks

**Solutions**:
```python
# Add constraint to limit steps
plan = await planner.create_plan({
    "goal": "Complete penetration test",
    "constraints": [
        "Maximum 8 steps",
        "Complete within 120 seconds"
    ]
})

# Or use recursive planning (see Integration Patterns)
```

### Issue 3: Incorrect Arm Assignment

**Symptoms**: Steps assigned to wrong arms (e.g., code generation to executor)

**Possible Causes**:
- Planner LLM needs fine-tuning
- Arm capabilities not well-documented

**Solutions**:
```bash
# Check Planner metrics for misrouting
curl http://planner:8002/metrics | grep planner_arm_assignments

# If issue persists, manually override in Orchestrator:
# step.arm_id = "coder"  # Override incorrect assignment
```

### Issue 4: Missing Dependencies

**Symptoms**: Steps with missing dependencies, parallel execution fails

**Possible Causes**:
- Planner didn't detect dependencies
- Complex dependency graph

**Solutions**:
```python
# Validate dependencies before execution
def validate_dependencies(plan):
    for step in plan.steps:
        for dep in step.dependencies:
            if dep >= step.step_number:
                raise ValueError(f"Step {step.step_number} depends on future step {dep}")
            if not any(s.step_number == dep for s in plan.steps):
                raise ValueError(f"Step {step.step_number} depends on nonexistent step {dep}")

validate_dependencies(plan)
```

### Issue 5: High Latency (>5s)

**Symptoms**: Plan generation taking >5 seconds consistently

**Possible Causes**:
- GPT-3.5-turbo API throttling
- Complex goals requiring multiple LLM passes
- Network latency

**Solutions**:
```bash
# Check OpenAI API status
curl https://status.openai.com/api/v2/status.json

# Enable request caching for identical goals
# (Implementation in Planner service, not client-side)

# Scale horizontally
kubectl scale deployment planner --replicas=5

# Monitor latency
kubectl logs -l app=planner | grep "plan_generation_time"
```

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Orchestrator API](./orchestrator.md)
- [Executor Arm API](./executor.md)
- [OpenAPI Specification](../openapi/planner.yaml)

---

## Support

For issues with the Planner Arm:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `kubectl logs -l app=planner`
3. Check metrics: `curl http://planner:8002/metrics`
4. File issue: https://github.com/octollm/octollm/issues
