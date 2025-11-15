# TaskContract Schema Reference

## Overview

The **TaskContract** is the core data structure in OctoLLM representing a user's request for AI assistance. It flows through the entire system from the Orchestrator to specialized arms, carrying the goal, constraints, acceptance criteria, and resource budgets.

**Used By**: Orchestrator, Planner, all Arms
**Primary Endpoints**: `POST /tasks`, `GET /tasks/{id}`
**Format**: JSON

---

## Structure

### TaskRequest

Submitted by clients to create a new task.

```typescript
interface TaskRequest {
  goal: string;                    // Required: 10-2000 chars
  constraints?: string[];          // Optional: Hard constraints
  acceptance_criteria?: string[];  // Optional: Success conditions
  context?: Record<string, any>;   // Optional: Additional metadata
  budget?: ResourceBudget;         // Optional: Resource limits
}
```

### TaskResponse

Returned when a task is created or queried.

```typescript
interface TaskResponse {
  task_id: string;                 // Format: task_<alphanumeric>
  status: TaskStatus;              // Current status
  created_at: string;              // ISO 8601 timestamp
  updated_at?: string;             // ISO 8601 timestamp
  estimated_completion?: string;   // ISO 8601 timestamp
  progress?: TaskProgress;         // Progress info
  result?: TaskResult;             // Final result (if completed)
  error?: TaskError;               // Error info (if failed)
}
```

### ResourceBudget

Defines resource constraints for task execution.

```typescript
interface ResourceBudget {
  max_tokens?: number;             // 100-100,000, default: 10,000
  max_time_seconds?: number;       // 5-300, default: 120
  max_cost_dollars?: number;       // 0.01-10.0, default: 1.0
}
```

### TaskStatus

```typescript
type TaskStatus =
  | 'queued'           // Waiting for execution
  | 'processing'       // Currently executing
  | 'completed'        // Successfully finished
  | 'failed'           // Error occurred
  | 'cancelled';       // Cancelled by user
```

### TaskProgress

```typescript
interface TaskProgress {
  current_step: string;            // Current execution step
  completed_steps: number;
  total_steps: number;
  percentage: number;              // 0-100
  estimated_time_remaining?: number; // Seconds
}
```

### TaskResult

```typescript
interface TaskResult {
  output: string;                  // Primary result
  confidence: number;              // 0.0-1.0
  validation_passed: boolean;
  artifacts?: Record<string, any>; // Generated files, code, etc.
  metadata?: Record<string, any>;  // Execution metadata
}
```

### TaskError

```typescript
interface TaskError {
  code: string;                    // Error code
  message: string;                 // Human-readable error
  details?: Record<string, any>;   // Additional error context
  recovery_suggestions?: string[]; // How to fix
}
```

---

## Field Definitions

### `goal` (required)

**Type**: string
**Constraints**: 10-2000 characters
**Description**: Natural language description of what to accomplish

**Examples**:
```json
"Create a Python function to validate email addresses"
"Analyze security vulnerabilities in the provided Flask application"
"Scan network 192.168.1.0/24 for open ports"
```

**Best Practices**:
- Be specific and actionable
- Include relevant technical details
- Avoid ambiguous language
- Specify desired output format if applicable

**Bad**:
```json
"Help me with code"  // Too vague
"Make it better"      // Unclear what "it" is
```

**Good**:
```json
"Refactor the authentication module in auth.py to use JWT tokens instead of session cookies, maintaining backward compatibility"
```

---

### `constraints` (optional)

**Type**: array of strings
**Description**: Hard constraints that must be respected during execution

**Examples**:
```json
[
  "Complete within 60 seconds",
  "Use only public sources",
  "Do not modify files in /protected/",
  "Maximum 5,000 tokens"
]
```

**Common Constraint Types**:
- **Time**: `"Complete within N seconds"`
- **Resources**: `"Maximum N tokens"`, `"Budget limit $N"`
- **Scope**: `"Read-only access"`, `"No network calls"`
- **Style**: `"Follow PEP 8"`, `"Use TypeScript strict mode"`
- **Security**: `"No secrets in output"`, `"Sanitize user input"`

---

### `acceptance_criteria` (optional)

**Type**: array of strings
**Description**: Measurable conditions that define success

**Examples**:
```json
[
  "Code implements email validation with RFC 5322 regex",
  "Unit tests included with >80% coverage",
  "Docstring with examples present",
  "Type hints on all functions"
]
```

**Best Practices**:
- Make criteria objective and measurable
- Focus on outcomes, not implementation details
- Include testable conditions
- Prioritize high-value checks

**Bad**:
```json
["Code is good", "Works well"]  // Too subjective
```

**Good**:
```json
[
  "Function returns True for valid emails, False for invalid",
  "Handles edge cases (empty string, null, Unicode)",
  "Performance: <1ms for typical email validation"
]
```

---

### `context` (optional)

**Type**: object (any key-value pairs)
**Description**: Additional information to inform task execution

**Common Context Fields**:
- `language`: Programming language (e.g., "python", "javascript")
- `framework`: Framework/library (e.g., "Flask", "React")
- `version`: Version info (e.g., "Python 3.11", "Node 18")
- `environment`: Execution environment (e.g., "production", "test")
- `target`: Target system/application (e.g., "nginx/1.24.0")
- `source`: Request source (e.g., "api", "cli", "web")
- `user_id`: User identifier for tracking

**Example**:
```json
{
  "language": "python",
  "framework": "Flask",
  "python_version": "3.11",
  "authentication": "JWT",
  "database": "PostgreSQL 15",
  "source": "api",
  "user_id": "user_12345"
}
```

---

### `budget.max_tokens` (optional)

**Type**: integer
**Constraints**: 100-100,000
**Default**: 10,000
**Description**: Maximum LLM tokens to consume

**Token Estimation**:
- Simple task (email validator): ~500 tokens
- Medium task (refactor module): ~5,000 tokens
- Complex task (full feature): ~20,000 tokens

**Example**:
```json
{
  "budget": {
    "max_tokens": 5000  // Moderate task
  }
}
```

---

### `budget.max_time_seconds` (optional)

**Type**: integer
**Constraints**: 5-300 seconds
**Default**: 120 seconds
**Description**: Maximum execution time

**Time Estimation**:
- Code generation: 2-10 seconds
- Security analysis: 10-60 seconds
- Network scan: 30-300 seconds

**Example**:
```json
{
  "budget": {
    "max_time_seconds": 60  // 1 minute limit
  }
}
```

---

### `budget.max_cost_dollars` (optional)

**Type**: number
**Constraints**: 0.01-10.0
**Default**: 1.0
**Description**: Maximum monetary cost in USD

**Cost Estimation** (approximate):
- GPT-3.5-turbo: $0.001/1K tokens
- GPT-4: $0.03/1K input, $0.06/1K output
- Claude Opus: $0.015/1K input, $0.075/1K output

**Example**:
```json
{
  "budget": {
    "max_cost_dollars": 0.50  // 50 cents max
  }
}
```

---

## Usage Examples

### Example 1: Simple Code Generation

```json
{
  "goal": "Create a Python function to validate email addresses",
  "constraints": [
    "Include type hints",
    "Add comprehensive docstring"
  ],
  "acceptance_criteria": [
    "Function returns bool",
    "Handles edge cases (empty, Unicode)"
  ],
  "context": {
    "language": "python",
    "python_version": "3.11"
  },
  "budget": {
    "max_tokens": 2000,
    "max_time_seconds": 30,
    "max_cost_dollars": 0.10
  }
}
```

### Example 2: Security Analysis

```json
{
  "goal": "Analyze the Flask application in app.py for OWASP Top 10 vulnerabilities",
  "constraints": [
    "Focus on SQL injection and XSS",
    "Complete within 60 seconds"
  ],
  "acceptance_criteria": [
    "All high-severity vulnerabilities identified",
    "Remediation recommendations provided",
    "Code examples for fixes included"
  ],
  "context": {
    "framework": "Flask",
    "python_version": "3.11",
    "database": "PostgreSQL",
    "authentication": "JWT"
  },
  "budget": {
    "max_tokens": 10000,
    "max_time_seconds": 60,
    "max_cost_dollars": 0.50
  }
}
```

### Example 3: Network Scanning

```json
{
  "goal": "Scan network 192.168.1.0/24 for open ports 22, 80, 443",
  "constraints": [
    "Stealth scan mode",
    "Complete within 120 seconds",
    "No service disruption"
  ],
  "acceptance_criteria": [
    "All hosts scanned",
    "Open ports identified per host",
    "Service versions detected"
  ],
  "context": {
    "scan_type": "stealth",
    "target_network": "192.168.1.0/24",
    "ports": [22, 80, 443]
  },
  "budget": {
    "max_time_seconds": 120
  }
}
```

---

## Validation Rules

### Goal Validation

```typescript
function validateGoal(goal: string): boolean {
  if (goal.length < 10 || goal.length > 2000) {
    throw new Error("Goal must be 10-2000 characters");
  }
  if (goal.trim().length === 0) {
    throw new Error("Goal cannot be empty or whitespace only");
  }
  return true;
}
```

### Budget Validation

```typescript
function validateBudget(budget: ResourceBudget): boolean {
  if (budget.max_tokens && (budget.max_tokens < 100 || budget.max_tokens > 100000)) {
    throw new Error("max_tokens must be 100-100,000");
  }
  if (budget.max_time_seconds && (budget.max_time_seconds < 5 || budget.max_time_seconds > 300)) {
    throw new Error("max_time_seconds must be 5-300");
  }
  if (budget.max_cost_dollars && (budget.max_cost_dollars < 0.01 || budget.max_cost_dollars > 10.0)) {
    throw new Error("max_cost_dollars must be 0.01-10.0");
  }
  return true;
}
```

---

## Best Practices

### 1. Always Specify Acceptance Criteria

**Why**: Enables Judge arm to validate outputs objectively
**How**: Include 2-5 measurable success conditions

```json
{
  "goal": "Refactor authentication module",
  "acceptance_criteria": [
    "All existing tests pass",
    "JWT tokens replace session cookies",
    "Backward compatibility maintained",
    "Security audit passes"
  ]
}
```

### 2. Use Constraints to Prevent Issues

**Why**: Prevents runaway costs, timeouts, and policy violations
**How**: Set realistic limits based on task complexity

```json
{
  "constraints": [
    "Maximum 5,000 tokens",      // Prevent cost overruns
    "Complete within 60 seconds", // Prevent timeouts
    "Read-only filesystem access" // Security constraint
  ]
}
```

### 3. Provide Rich Context

**Why**: Improves quality and reduces ambiguity
**How**: Include language, framework, version, environment

```json
{
  "context": {
    "language": "python",
    "framework": "Django",
    "django_version": "4.2",
    "python_version": "3.11",
    "database": "PostgreSQL 15",
    "authentication": "OAuth2"
  }
}
```

### 4. Set Appropriate Budgets

**Why**: Balance cost vs quality
**How**: Use table below as starting point

| Task Complexity | Tokens | Time (s) | Cost ($) |
|-----------------|--------|----------|----------|
| Simple | 1,000-2,000 | 10-30 | 0.05-0.10 |
| Medium | 3,000-7,000 | 30-90 | 0.20-0.50 |
| Complex | 10,000-20,000 | 90-180 | 0.50-2.00 |
| Very Complex | 20,000-50,000 | 180-300 | 2.00-5.00 |

---

## Common Patterns

### Pattern 1: Iterative Refinement

Submit task, check result, refine goal if needed.

```typescript
let attempt = 0;
while (attempt < 3) {
  const response = await orchestrator.submitTask({
    goal: attempt === 0 ? originalGoal : `${originalGoal}\n\nPrevious attempt failed: ${previousError}`,
    acceptance_criteria: criteria
  });

  if (response.result?.validation_passed) {
    return response.result;
  }

  attempt++;
}
```

### Pattern 2: Budget-Constrained Development

Start with small budget, increase if needed.

```typescript
const budgets = [
  { max_tokens: 2000, max_cost_dollars: 0.10 },
  { max_tokens: 5000, max_cost_dollars: 0.30 },
  { max_tokens: 10000, max_cost_dollars: 0.60 }
];

for (const budget of budgets) {
  const response = await orchestrator.submitTask({
    goal,
    budget
  });

  if (response.status === 'completed') {
    return response;
  }
}
```

---

## Related Documentation

- [Orchestrator API Reference](../services/orchestrator.md)
- [ResourceBudget Best Practices](../guides/resource-budgets.md) (coming soon)
- [Acceptance Criteria Guide](../guides/acceptance-criteria.md) (coming soon)

---

## JSON Schema

Complete JSON Schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TaskRequest",
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
    "acceptance_criteria": {
      "type": "array",
      "items": {"type": "string"}
    },
    "context": {
      "type": "object",
      "additionalProperties": true
    },
    "budget": {
      "type": "object",
      "properties": {
        "max_tokens": {
          "type": "integer",
          "minimum": 100,
          "maximum": 100000
        },
        "max_time_seconds": {
          "type": "integer",
          "minimum": 5,
          "maximum": 300
        },
        "max_cost_dollars": {
          "type": "number",
          "minimum": 0.01,
          "maximum": 10.0
        }
      }
    }
  }
}
```
