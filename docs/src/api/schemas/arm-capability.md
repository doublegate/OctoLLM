# ArmCapability Schema Reference

## Overview

The **ArmCapability** schema defines how specialized arms register their capabilities with the Orchestrator. This registry enables dynamic task routing, cost-aware scheduling, and capability-based delegation across the OctoLLM system.

**Used By**: Orchestrator (for arm registry), all Arms (for self-registration)
**Primary Endpoint**: `GET /capabilities`
**Format**: JSON

---

## Structure

### ArmCapability

Complete arm registration structure returned by the capabilities endpoint.

```typescript
interface ArmCapability {
  arm_id: string;                  // Required: Unique arm identifier
  name: string;                    // Required: Human-readable name
  description: string;             // Required: Purpose and specialization
  capabilities: string[];          // Required: Capability tags
  cost_tier: number;               // Required: 1-5 (1=cheap, 5=expensive)
  endpoint: string;                // Required: Service URL
  status?: ArmStatus;              // Optional: Current health status
  input_schema?: JSONSchema;       // Optional: Request schema
  output_schema?: JSONSchema;      // Optional: Response schema
  metadata?: ArmMetadata;          // Optional: Additional info
}

type ArmStatus = 'healthy' | 'degraded' | 'unavailable';

interface ArmMetadata {
  version?: string;                // Arm version (e.g., "0.3.0")
  technology?: string;             // Tech stack (e.g., "Python/FastAPI")
  model?: string;                  // LLM model if applicable
  average_latency_ms?: number;     // Typical response time
  max_concurrent_tasks?: number;   // Concurrency limit
  uptime_percentage?: number;      // 30-day uptime (0-100)
}
```

---

## Field Definitions

### `arm_id` (required)

**Type**: string
**Constraints**: Lowercase, alphanumeric with hyphens
**Description**: Unique identifier used for arm routing and discovery

**Valid Arm IDs** (current system):
```typescript
type ArmId =
  | 'planner'
  | 'executor'
  | 'retriever'
  | 'coder'
  | 'judge'
  | 'safety-guardian';
```

**Validation**:
```typescript
function validateArmId(armId: string): boolean {
  const pattern = /^[a-z0-9]+(-[a-z0-9]+)*$/;
  if (!pattern.test(armId)) {
    throw new Error("arm_id must be lowercase alphanumeric with hyphens");
  }
  return true;
}
```

---

### `name` (required)

**Type**: string
**Constraints**: 3-50 characters
**Description**: Human-readable display name for the arm

**Examples**:
```json
"Planner Arm"
"Tool Executor Arm"
"Code Generation Arm"
"Safety Guardian Arm"
```

---

### `description` (required)

**Type**: string
**Constraints**: 10-200 characters
**Description**: Concise explanation of the arm's purpose and specialization

**Best Practices**:
- Start with the primary function
- Mention key specializations
- Keep under 200 characters

**Examples**:
```json
"Task decomposition and planning specialist"
"Sandboxed command execution specialist with capability-based security"
"Hybrid vector and keyword search over knowledge bases"
"Code generation, debugging, and refactoring using GPT-4"
```

---

### `capabilities` (required)

**Type**: array of strings
**Constraints**: At least 1 capability tag
**Description**: Tags describing what the arm can do, used for task routing

#### Capability Tag Taxonomy

**Planning Capabilities**:
- `task_planning` - Task decomposition into subtasks
- `goal_decomposition` - Breaking down high-level goals
- `dependency_resolution` - Managing task dependencies
- `acceptance_criteria` - Defining success conditions

**Execution Capabilities**:
- `shell_execution` - Running shell commands
- `http_requests` - Making HTTP/HTTPS requests
- `python_execution` - Running Python scripts
- `network_scanning` - Port scanning and network recon

**Knowledge Capabilities**:
- `vector_search` - Semantic similarity search
- `keyword_search` - Traditional keyword-based search
- `rag_retrieval` - Retrieval-Augmented Generation
- `citation_generation` - Creating source citations

**Code Capabilities**:
- `code_generation` - Creating new code
- `code_debugging` - Finding and fixing bugs
- `code_refactoring` - Improving code structure
- `code_analysis` - Understanding existing code
- `test_generation` - Creating unit tests
- `code_explanation` - Documenting code

**Validation Capabilities**:
- `schema_validation` - Validating data structures
- `fact_checking` - Verifying factual claims
- `criteria_validation` - Checking acceptance criteria
- `hallucination_detection` - Identifying LLM hallucinations
- `quality_assessment` - Evaluating output quality

**Safety Capabilities**:
- `pii_detection` - Finding personally identifiable information
- `secret_detection` - Identifying API keys, passwords, tokens
- `content_filtering` - Blocking inappropriate content
- `input_sanitization` - Cleaning user input
- `output_redaction` - Removing sensitive data

**Example Capability Sets**:

```json
// Planner Arm
{
  "capabilities": [
    "task_planning",
    "goal_decomposition",
    "dependency_resolution",
    "acceptance_criteria"
  ]
}

// Executor Arm
{
  "capabilities": [
    "shell_execution",
    "http_requests",
    "python_execution",
    "network_scanning"
  ]
}

// Coder Arm
{
  "capabilities": [
    "code_generation",
    "code_debugging",
    "code_refactoring",
    "code_analysis",
    "test_generation",
    "code_explanation"
  ]
}
```

---

### `cost_tier` (required)

**Type**: integer
**Constraints**: 1-5
**Description**: Relative cost indicator for resource-aware scheduling

#### Cost Tier Definitions

| Tier | Name | Characteristics | LLM Usage | Typical Cost/Task |
|------|------|-----------------|-----------|-------------------|
| **1** | Cheap | No LLM calls, pure computation | None | $0.00 |
| **2** | Low | Small model, simple tasks | GPT-3.5-turbo | $0.01-0.05 |
| **3** | Medium | Medium model or sandboxing overhead | GPT-3.5-turbo (complex) | $0.05-0.10 |
| **4** | High | Large model, complex tasks | GPT-4 | $0.10-0.50 |
| **5** | Expensive | Frontier model, multi-step reasoning | GPT-4/Claude Opus | $0.50-2.00 |

#### Cost Tier Examples

**Tier 1 - Cheap**:
```json
{
  "arm_id": "reflex-layer",
  "cost_tier": 1,
  "rationale": "Cache lookups and regex pattern matching only"
}

{
  "arm_id": "safety-guardian",
  "cost_tier": 1,
  "rationale": "Regex-based PII/secret detection without LLM"
}
```

**Tier 2 - Low**:
```json
{
  "arm_id": "planner",
  "cost_tier": 2,
  "rationale": "GPT-3.5-turbo for task decomposition (500-2000 tokens)"
}

{
  "arm_id": "judge",
  "cost_tier": 2,
  "rationale": "GPT-3.5-turbo for validation (1000-3000 tokens)"
}
```

**Tier 3 - Medium**:
```json
{
  "arm_id": "executor",
  "cost_tier": 3,
  "rationale": "Docker sandboxing overhead, no LLM but resource-intensive"
}

{
  "arm_id": "retriever",
  "cost_tier": 3,
  "rationale": "Vector database queries and embedding generation"
}
```

**Tier 4 - High**:
```json
{
  "arm_id": "coder",
  "cost_tier": 4,
  "rationale": "GPT-4 for complex code generation (5000-10000 tokens)"
}
```

**Tier 5 - Expensive**:
```json
{
  "arm_id": "orchestrator",
  "cost_tier": 5,
  "rationale": "GPT-4/Claude Opus with multi-step reasoning and synthesis"
}
```

---

### `endpoint` (required)

**Type**: string (URI format)
**Description**: HTTP(S) URL where the arm service is accessible

**Environment-Specific Endpoints**:

```typescript
// Local Development (Docker Compose)
const endpoints = {
  planner: "http://planner:8002",
  executor: "http://executor:8003",
  retriever: "http://retriever:8004",
  coder: "http://coder:8005",
  judge: "http://judge:8006",
  safetyGuardian: "http://safety-guardian:8007"
};

// Kubernetes (Internal)
const k8sEndpoints = {
  planner: "http://planner.octollm.svc.cluster.local:8002",
  executor: "http://executor.octollm.svc.cluster.local:8003"
};

// Production (External)
const prodEndpoints = {
  planner: "https://planner.api.octollm.example.com",
  executor: "https://executor.api.octollm.example.com"
};
```

**Validation**:
```typescript
function validateEndpoint(endpoint: string): boolean {
  try {
    const url = new URL(endpoint);
    if (!['http:', 'https:'].includes(url.protocol)) {
      throw new Error("Endpoint must use HTTP or HTTPS protocol");
    }
    return true;
  } catch (error) {
    throw new Error(`Invalid endpoint URL: ${endpoint}`);
  }
}
```

---

### `status` (optional)

**Type**: enum
**Values**: `'healthy'` | `'degraded'` | `'unavailable'`
**Description**: Current operational status of the arm

#### Status Definitions

**healthy** - Arm is fully operational
- All endpoints responding normally
- Latency within acceptable range
- Error rate <1%

**degraded** - Arm is partially operational
- Endpoints responding but slowly
- Latency 2-3x normal
- Error rate 1-5%
- Some features may be disabled

**unavailable** - Arm is not operational
- Endpoints not responding
- Network connectivity lost
- Service crashed or restarting

**Status Checks**:
```python
async def check_arm_status(arm_endpoint: str) -> ArmStatus:
    """Check arm health and return status."""
    try:
        response = await http_client.get(f"{arm_endpoint}/health", timeout=5)

        if response.status_code == 200:
            health_data = response.json()
            latency_ms = response.elapsed.total_seconds() * 1000

            # Check latency thresholds
            if latency_ms > 3000:
                return "degraded"
            return "healthy"
        else:
            return "degraded"

    except Exception as e:
        logger.error(f"Arm {arm_endpoint} health check failed: {e}")
        return "unavailable"
```

---

### `input_schema` (optional)

**Type**: JSON Schema object
**Description**: Formal schema defining the arm's expected request format

**Example - Planner Arm Input**:
```json
{
  "input_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["goal"],
    "properties": {
      "goal": {
        "type": "string",
        "minLength": 10,
        "maxLength": 2000
      },
      "constraints": {
        "type": "array",
        "items": {"type": "string"}
      },
      "context": {
        "type": "object",
        "additionalProperties": true
      }
    }
  }
}
```

**Example - Executor Arm Input**:
```json
{
  "input_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["action_type", "command", "capability_token"],
    "properties": {
      "action_type": {
        "type": "string",
        "enum": ["shell", "http", "python"]
      },
      "command": {
        "type": "string"
      },
      "args": {
        "type": "array",
        "items": {"type": "string"}
      },
      "timeout_seconds": {
        "type": "integer",
        "minimum": 1,
        "maximum": 300,
        "default": 30
      },
      "capability_token": {
        "type": "string",
        "pattern": "^tok_[a-zA-Z0-9]{16}$"
      }
    }
  }
}
```

---

### `output_schema` (optional)

**Type**: JSON Schema object
**Description**: Formal schema defining the arm's response format

**Example - Judge Arm Output**:
```json
{
  "output_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["valid", "confidence", "issues"],
    "properties": {
      "valid": {
        "type": "boolean"
      },
      "confidence": {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0
      },
      "issues": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["severity", "type", "message"],
          "properties": {
            "severity": {
              "type": "string",
              "enum": ["error", "warning", "info"]
            },
            "type": {
              "type": "string"
            },
            "message": {
              "type": "string"
            }
          }
        }
      }
    }
  }
}
```

---

### `metadata` (optional)

**Type**: object
**Description**: Additional metadata about the arm's capabilities and performance

**Common Metadata Fields**:
- `version`: Arm version (semantic versioning)
- `technology`: Tech stack (e.g., "Python 3.11/FastAPI", "Rust 1.75/Axum")
- `model`: LLM model if applicable (e.g., "gpt-4", "gpt-3.5-turbo")
- `average_latency_ms`: Typical response time
- `max_concurrent_tasks`: Maximum parallel task capacity
- `uptime_percentage`: 30-day uptime (0-100)

**Example**:
```json
{
  "metadata": {
    "version": "0.3.0",
    "technology": "Python 3.11 / FastAPI 0.104",
    "model": "gpt-4",
    "average_latency_ms": 8500,
    "max_concurrent_tasks": 10,
    "uptime_percentage": 99.7
  }
}
```

---

## Complete Examples

### Example 1: Planner Arm

```json
{
  "arm_id": "planner",
  "name": "Planner Arm",
  "description": "Task decomposition and planning specialist",
  "capabilities": [
    "task_planning",
    "goal_decomposition",
    "dependency_resolution",
    "acceptance_criteria"
  ],
  "cost_tier": 2,
  "endpoint": "http://planner:8002",
  "status": "healthy",
  "input_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["goal"],
    "properties": {
      "goal": {"type": "string", "minLength": 10, "maxLength": 2000},
      "constraints": {"type": "array", "items": {"type": "string"}},
      "context": {"type": "object"}
    }
  },
  "output_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["plan_id", "steps"],
    "properties": {
      "plan_id": {"type": "string"},
      "steps": {"type": "array", "items": {"type": "object"}}
    }
  },
  "metadata": {
    "version": "0.3.0",
    "technology": "Python 3.11 / FastAPI",
    "model": "gpt-3.5-turbo",
    "average_latency_ms": 2500,
    "max_concurrent_tasks": 20,
    "uptime_percentage": 99.8
  }
}
```

---

### Example 2: Tool Executor Arm

```json
{
  "arm_id": "executor",
  "name": "Tool Executor Arm",
  "description": "Sandboxed command execution specialist",
  "capabilities": [
    "shell_execution",
    "http_requests",
    "python_execution",
    "network_scanning"
  ],
  "cost_tier": 3,
  "endpoint": "http://executor:8003",
  "status": "healthy",
  "input_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["action_type", "command", "capability_token"],
    "properties": {
      "action_type": {"type": "string", "enum": ["shell", "http", "python"]},
      "command": {"type": "string"},
      "args": {"type": "array", "items": {"type": "string"}},
      "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300},
      "capability_token": {"type": "string"}
    }
  },
  "output_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["success", "provenance"],
    "properties": {
      "success": {"type": "boolean"},
      "stdout": {"type": "string"},
      "stderr": {"type": "string"},
      "exit_code": {"type": "integer"},
      "duration_ms": {"type": "number"},
      "provenance": {"type": "object"}
    }
  },
  "metadata": {
    "version": "0.3.0",
    "technology": "Rust 1.75 / Axum",
    "average_latency_ms": 850,
    "max_concurrent_tasks": 15,
    "uptime_percentage": 99.5
  }
}
```

---

### Example 3: Retriever Arm

```json
{
  "arm_id": "retriever",
  "name": "Retriever Arm",
  "description": "Hybrid vector and keyword search over knowledge bases",
  "capabilities": [
    "vector_search",
    "keyword_search",
    "rag_retrieval",
    "citation_generation"
  ],
  "cost_tier": 3,
  "endpoint": "http://retriever:8004",
  "status": "healthy",
  "metadata": {
    "version": "0.3.0",
    "technology": "Python 3.11 / FastAPI + Qdrant",
    "average_latency_ms": 1200,
    "max_concurrent_tasks": 25,
    "uptime_percentage": 99.9
  }
}
```

---

### Example 4: Coder Arm

```json
{
  "arm_id": "coder",
  "name": "Code Generation Arm",
  "description": "Code generation, debugging, and refactoring using GPT-4",
  "capabilities": [
    "code_generation",
    "code_debugging",
    "code_refactoring",
    "code_analysis",
    "test_generation",
    "code_explanation"
  ],
  "cost_tier": 4,
  "endpoint": "http://coder:8005",
  "status": "healthy",
  "metadata": {
    "version": "0.3.0",
    "technology": "Python 3.11 / FastAPI",
    "model": "gpt-4",
    "average_latency_ms": 8500,
    "max_concurrent_tasks": 10,
    "uptime_percentage": 99.6
  }
}
```

---

### Example 5: Judge Arm

```json
{
  "arm_id": "judge",
  "name": "Judge Arm",
  "description": "Multi-layer validation of outputs against criteria and facts",
  "capabilities": [
    "schema_validation",
    "fact_checking",
    "criteria_validation",
    "hallucination_detection",
    "quality_assessment"
  ],
  "cost_tier": 2,
  "endpoint": "http://judge:8006",
  "status": "healthy",
  "metadata": {
    "version": "0.3.0",
    "technology": "Python 3.11 / FastAPI",
    "model": "gpt-3.5-turbo",
    "average_latency_ms": 3200,
    "max_concurrent_tasks": 20,
    "uptime_percentage": 99.7
  }
}
```

---

### Example 6: Safety Guardian Arm

```json
{
  "arm_id": "safety-guardian",
  "name": "Safety Guardian Arm",
  "description": "PII detection, secret detection, and content filtering",
  "capabilities": [
    "pii_detection",
    "secret_detection",
    "content_filtering",
    "input_sanitization",
    "output_redaction"
  ],
  "cost_tier": 1,
  "endpoint": "http://safety-guardian:8007",
  "status": "healthy",
  "metadata": {
    "version": "0.3.0",
    "technology": "Python 3.11 / FastAPI (regex-based, no LLM)",
    "average_latency_ms": 75,
    "max_concurrent_tasks": 50,
    "uptime_percentage": 99.9
  }
}
```

---

## Usage Patterns

### Pattern 1: Querying Available Capabilities

Retrieve all registered arms to understand system capabilities.

```bash
curl http://orchestrator:8000/capabilities \
  -H "Authorization: Bearer $SERVICE_TOKEN"
```

**Response**:
```json
{
  "arms": [
    {
      "arm_id": "planner",
      "name": "Planner Arm",
      "description": "Task decomposition and planning specialist",
      "capabilities": ["task_planning", "goal_decomposition"],
      "cost_tier": 2,
      "endpoint": "http://planner:8002",
      "status": "healthy"
    },
    {
      "arm_id": "executor",
      "name": "Tool Executor Arm",
      "description": "Sandboxed command execution specialist",
      "capabilities": ["shell_execution", "http_requests", "python_execution"],
      "cost_tier": 3,
      "endpoint": "http://executor:8003",
      "status": "healthy"
    }
  ]
}
```

---

### Pattern 2: Capability-Based Task Routing

Select the appropriate arm based on required capabilities.

```typescript
interface TaskRoutingRequest {
  requiredCapabilities: string[];
  preferLowCost?: boolean;
}

async function routeTask(request: TaskRoutingRequest): Promise<ArmCapability> {
  // Fetch all arms
  const response = await fetch('http://orchestrator:8000/capabilities', {
    headers: { 'Authorization': `Bearer ${serviceToken}` }
  });
  const { arms } = await response.json();

  // Filter arms with all required capabilities
  const compatibleArms = arms.filter(arm =>
    request.requiredCapabilities.every(cap =>
      arm.capabilities.includes(cap)
    )
  );

  if (compatibleArms.length === 0) {
    throw new Error(`No arm found with capabilities: ${request.requiredCapabilities}`);
  }

  // Sort by cost tier if preferLowCost is true
  if (request.preferLowCost) {
    compatibleArms.sort((a, b) => a.cost_tier - b.cost_tier);
  }

  // Return first healthy arm
  const healthyArm = compatibleArms.find(arm => arm.status === 'healthy');
  if (!healthyArm) {
    throw new Error('No healthy arms available');
  }

  return healthyArm;
}

// Example usage
const arm = await routeTask({
  requiredCapabilities: ['code_generation', 'test_generation'],
  preferLowCost: false
});

console.log(`Routing to: ${arm.name} (cost tier ${arm.cost_tier})`);
// Output: "Routing to: Code Generation Arm (cost tier 4)"
```

---

### Pattern 3: Cost-Aware Scheduling

Choose the cheapest arm that meets requirements.

```python
from typing import List, Optional

async def schedule_task_cost_aware(
    required_capabilities: List[str],
    max_cost_tier: int = 5
) -> Optional[ArmCapability]:
    """Schedule task to cheapest compatible arm."""

    response = await http_client.get(
        "http://orchestrator:8000/capabilities",
        headers={"Authorization": f"Bearer {service_token}"}
    )
    arms = response.json()["arms"]

    # Filter by capabilities and cost tier
    compatible = [
        arm for arm in arms
        if all(cap in arm["capabilities"] for cap in required_capabilities)
        and arm["cost_tier"] <= max_cost_tier
        and arm["status"] == "healthy"
    ]

    if not compatible:
        return None

    # Sort by cost tier (ascending)
    compatible.sort(key=lambda a: a["cost_tier"])

    cheapest_arm = compatible[0]
    print(f"Scheduled to {cheapest_arm['name']} (tier {cheapest_arm['cost_tier']})")
    return cheapest_arm

# Example usage
arm = await schedule_task_cost_aware(
    required_capabilities=["pii_detection", "secret_detection"],
    max_cost_tier=3
)
# Output: "Scheduled to Safety Guardian Arm (tier 1)"
```

---

### Pattern 4: Health Monitoring

Continuously monitor arm health and adjust routing.

```typescript
class ArmHealthMonitor {
  private arms: Map<string, ArmCapability> = new Map();
  private healthCheckInterval = 30000; // 30 seconds

  async start() {
    setInterval(() => this.refreshCapabilities(), this.healthCheckInterval);
    await this.refreshCapabilities();
  }

  async refreshCapabilities() {
    const response = await fetch('http://orchestrator:8000/capabilities', {
      headers: { 'Authorization': `Bearer ${this.serviceToken}` }
    });
    const { arms } = await response.json();

    for (const arm of arms) {
      this.arms.set(arm.arm_id, arm);

      // Log status changes
      const previous = this.arms.get(arm.arm_id);
      if (previous && previous.status !== arm.status) {
        console.warn(`Arm ${arm.name} status changed: ${previous.status} → ${arm.status}`);
      }
    }
  }

  getHealthyArms(capability: string): ArmCapability[] {
    return Array.from(this.arms.values()).filter(
      arm => arm.capabilities.includes(capability) && arm.status === 'healthy'
    );
  }

  getCheapestHealthyArm(capability: string): ArmCapability | null {
    const healthyArms = this.getHealthyArms(capability);
    if (healthyArms.length === 0) return null;

    return healthyArms.reduce((cheapest, arm) =>
      arm.cost_tier < cheapest.cost_tier ? arm : cheapest
    );
  }
}

// Example usage
const monitor = new ArmHealthMonitor();
await monitor.start();

const arm = monitor.getCheapestHealthyArm('code_generation');
if (arm) {
  console.log(`Using ${arm.name} (${arm.status})`);
} else {
  console.error('No healthy arms available for code generation');
}
```

---

## Best Practices

### 1. Always Check Arm Status Before Routing

**Why**: Prevents routing to unhealthy arms
**How**: Filter by `status: 'healthy'` before delegation

```typescript
const healthyArms = arms.filter(arm => arm.status === 'healthy');
```

---

### 2. Use Cost Tiers for Budget Control

**Why**: Prevents runaway costs on simple tasks
**How**: Set `max_cost_tier` constraints

```python
# Use cheap arms (tier 1-2) for simple validation
arm = schedule_task(capabilities=["pii_detection"], max_cost_tier=2)

# Allow expensive arms (tier 4-5) for complex reasoning
arm = schedule_task(capabilities=["code_generation"], max_cost_tier=5)
```

---

### 3. Capability Tags Should Be Granular

**Why**: Enables precise routing and prevents over-delegation
**How**: Use specific capability tags

**Bad** (too broad):
```json
{"capabilities": ["coding"]}
```

**Good** (granular):
```json
{
  "capabilities": [
    "code_generation",
    "code_debugging",
    "code_refactoring",
    "test_generation"
  ]
}
```

---

### 4. Monitor Arm Health Continuously

**Why**: Enables graceful degradation and failover
**How**: Poll `/capabilities` endpoint every 30-60 seconds

```python
async def monitor_arms():
    while True:
        response = await get_capabilities()
        for arm in response["arms"]:
            if arm["status"] != "healthy":
                logger.warning(f"Arm {arm['name']} is {arm['status']}")
        await asyncio.sleep(30)
```

---

## Related Documentation

- [Orchestrator API Reference](../services/orchestrator.md)
- [TaskContract Schema](./TaskContract.md)
- [Arm Registration Guide](../../guides/arm-registration.md) (coming soon)
- [Cost Optimization Guide](../../guides/cost-optimization.md) (coming soon)

---

## JSON Schema

Complete JSON Schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ArmCapability",
  "type": "object",
  "required": ["arm_id", "name", "description", "capabilities", "cost_tier", "endpoint"],
  "properties": {
    "arm_id": {
      "type": "string",
      "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
      "description": "Unique arm identifier (lowercase alphanumeric with hyphens)"
    },
    "name": {
      "type": "string",
      "minLength": 3,
      "maxLength": 50,
      "description": "Human-readable arm name"
    },
    "description": {
      "type": "string",
      "minLength": 10,
      "maxLength": 200,
      "description": "Arm purpose and specialization"
    },
    "capabilities": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "description": "List of capability tags"
    },
    "cost_tier": {
      "type": "integer",
      "minimum": 1,
      "maximum": 5,
      "description": "Cost tier (1=cheap, 5=expensive)"
    },
    "endpoint": {
      "type": "string",
      "format": "uri",
      "description": "Arm service endpoint URL"
    },
    "status": {
      "type": "string",
      "enum": ["healthy", "degraded", "unavailable"],
      "description": "Current operational status"
    },
    "input_schema": {
      "type": "object",
      "description": "JSON Schema for arm input validation"
    },
    "output_schema": {
      "type": "object",
      "description": "JSON Schema for arm output validation"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "version": {"type": "string"},
        "technology": {"type": "string"},
        "model": {"type": "string"},
        "average_latency_ms": {"type": "number"},
        "max_concurrent_tasks": {"type": "integer"},
        "uptime_percentage": {"type": "number", "minimum": 0, "maximum": 100}
      }
    }
  }
}
```
