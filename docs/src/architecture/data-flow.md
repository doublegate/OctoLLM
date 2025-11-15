# OctoLLM Data Flow Architecture

**Version**: 1.0
**Last Updated**: 2025-11-10

## Table of Contents

- [Overview](#overview)
- [Request Processing Pipeline](#request-processing-pipeline)
- [Memory Data Flow](#memory-data-flow)
- [Inter-Component Communication](#inter-component-communication)
- [Provenance Tracking](#provenance-tracking)
- [Error Handling Flow](#error-handling-flow)

## Overview

This document details how data flows through the OctoLLM system, from initial user request to final response, including memory operations, inter-component communication, and error handling.

## Request Processing Pipeline

### Complete Flow

```mermaid
flowchart TD
    START([User Request]) --> AUTH{Authenticated?}
    AUTH -->|No| REJECT([401 Unauthorized])
    AUTH -->|Yes| RATE{Within Rate Limit?}

    RATE -->|No| THROTTLE([429 Too Many Requests])
    RATE -->|Yes| REFLEX[Reflex Layer]

    REFLEX --> CACHE{Cache Hit?}
    CACHE -->|Yes| RETURN_CACHE([Return Cached Result])
    CACHE -->|No| PII[PII Detection]

    PII --> INJECT{Injection Detected?}
    INJECT -->|Yes| BLOCK([403 Blocked])
    INJECT -->|No| SANITIZE[Sanitize Input]

    SANITIZE --> ORCH[Orchestrator]
    ORCH --> PARSE[Parse Intent]
    PARSE --> COMPLEXITY{Complex Task?}

    COMPLEXITY -->|Yes| PLANNER[Planner Arm]
    COMPLEXITY -->|No| DIRECT[Direct Execution]

    PLANNER --> PLAN[Generate Plan]
    PLAN --> ROUTE[Route to Arms]

    ROUTE --> EXEC_LOOP{More Steps?}
    EXEC_LOOP -->|Yes| SELECT_ARM[Select Arm]

    SELECT_ARM --> ARM_TYPE{Arm Type}
    ARM_TYPE -->|Retriever| RETR[Retriever Arm]
    ARM_TYPE -->|Coder| CODE[Coder Arm]
    ARM_TYPE -->|Executor| EXEC[Executor Arm]

    RETR --> ARM_RESULT[Arm Result]
    CODE --> ARM_RESULT
    EXEC --> ARM_RESULT
    DIRECT --> ARM_RESULT

    ARM_RESULT --> STORE_LOCAL[Store in Local Memory]
    STORE_LOCAL --> UPDATE_CONTEXT[Update Task Context]
    UPDATE_CONTEXT --> EXEC_LOOP

    EXEC_LOOP -->|No| INTEGRATE[Integrate Results]
    INTEGRATE --> JUDGE[Judge Arm Validation]

    JUDGE --> VALID{Valid?}
    VALID -->|No| REPAIR[Repair Loop]
    REPAIR --> RETRY{Max Retries?}
    RETRY -->|No| INTEGRATE
    RETRY -->|Yes| ERROR([Error Response])

    VALID -->|Yes| STORE_GLOBAL[Store in Global Memory]
    STORE_GLOBAL --> CACHE_RESULT[Cache Result]
    CACHE_RESULT --> RESPONSE([Return to User])
```

### Layer-by-Layer Processing

#### Layer 1: API Gateway

```mermaid
sequenceDiagram
    participant User
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant RateLimit as Rate Limiter

    User->>Gateway: HTTP Request
    Gateway->>Auth: Validate Token
    Auth-->>Gateway: Valid/Invalid

    alt Invalid Token
        Gateway-->>User: 401 Unauthorized
    else Valid Token
        Gateway->>RateLimit: Check Limit
        RateLimit-->>Gateway: Allow/Deny

        alt Rate Limited
            Gateway-->>User: 429 Too Many Requests
        else Allowed
            Gateway->>Gateway: Add Request Metadata
            Note over Gateway: request_id, timestamp,<br/>user_id, trace_id
            Gateway-->>User: Forward to Reflex
        end
    end
```

#### Layer 2: Reflex Preprocessing

```mermaid
flowchart LR
    INPUT[Incoming Request] --> HASH[Compute Hash]
    HASH --> CACHE_LOOKUP{Redis Cache}

    CACHE_LOOKUP -->|Hit| METRICS1[Increment cache_hit]
    METRICS1 --> RETURN1[Return Cached]

    CACHE_LOOKUP -->|Miss| INJECT_CHECK[Injection Pattern Check]
    INJECT_CHECK -->|Match| BLOCK[Block Request]
    BLOCK --> METRICS2[Increment blocked]

    INJECT_CHECK -->|Clean| PII_CHECK[PII Pattern Scan]
    PII_CHECK --> REDACT[Redact/Sanitize]
    REDACT --> SCHEMA[Schema Validation]

    SCHEMA -->|Invalid| REJECT[Return 400]
    SCHEMA -->|Valid| FORWARD[Forward to Orchestrator]
    FORWARD --> METRICS3[Increment passthrough]
```

**Reflex Decision Matrix:**

| Condition | Action | Latency | Cache |
|-----------|--------|---------|-------|
| Exact query match | Return cached | < 5ms | Hit |
| Similar query (>0.95 similarity) | Return cached + log variance | < 10ms | Near-hit |
| PII detected | Sanitize + forward | < 15ms | Miss |
| Injection pattern | Block + alert | < 5ms | N/A |
| Novel query | Forward | < 10ms | Miss |

#### Layer 3: Orchestrator Planning

```mermaid
flowchart TD
    INPUT[Sanitized Request] --> PARSE[Parse Goal & Constraints]
    PARSE --> CONTEXT[Build Task Context]

    CONTEXT --> CACHED_PLAN{Similar Plan Exists?}
    CACHED_PLAN -->|Yes| ADAPT[Adapt Cached Plan]
    CACHED_PLAN -->|No| NEW_PLAN[Generate New Plan]

    ADAPT --> PLAN_READY[Plan Ready]
    NEW_PLAN --> LLM{Use LLM or Planner Arm?}

    LLM -->|Simple| DIRECT_LLM[Direct LLM Call]
    LLM -->|Complex| PLANNER_ARM[Planner Arm Call]

    DIRECT_LLM --> PARSE_PLAN[Parse Plan JSON]
    PLANNER_ARM --> PARSE_PLAN

    PARSE_PLAN --> VALIDATE_PLAN{Plan Valid?}
    VALIDATE_PLAN -->|No| REPLAN[Retry Planning]
    REPLAN --> LLM

    VALIDATE_PLAN -->|Yes| RESOLVE_DEPS[Resolve Dependencies]
    RESOLVE_DEPS --> PLAN_READY

    PLAN_READY --> EXECUTE[Execute Plan]
```

**Planning Decision Criteria:**

```python
def should_use_planner_arm(task):
    # Use dedicated Planner Arm if:
    return (
        len(task.constraints) > 3 or
        task.priority == Priority.HIGH or
        estimate_steps(task) > 5 or
        has_complex_dependencies(task) or
        requires_specialized_domain_knowledge(task)
    )
```

#### Layer 4: Arm Execution

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Router as Router
    participant ArmReg as Arm Registry
    participant Arm as Selected Arm
    participant LocalMem as Local Memory
    participant GlobalMem as Global Memory

    Orch->>Router: Route Step
    Router->>ArmReg: Get Capabilities
    ArmReg-->>Router: Arm Metadata

    Router->>Router: Score Arms
    Note over Router: Consider: cost, latency,<br/>success rate, load

    Router-->>Orch: Selected Arm(s)

    alt Single Arm
        Orch->>Arm: Execute Task
        Arm->>LocalMem: Query Context
        LocalMem-->>Arm: Local Context
        Arm->>Arm: Process
        Arm-->>Orch: Result + Confidence
    else Swarm (Multiple Arms)
        par Parallel Execution
            Orch->>Arm: Execute Task
            Arm->>LocalMem: Query Context
            Arm->>Arm: Process
            Arm-->>Orch: Result A
        and
            Orch->>Arm: Execute Task
            Arm->>LocalMem: Query Context
            Arm->>Arm: Process
            Arm-->>Orch: Result B
        and
            Orch->>Arm: Execute Task
            Arm->>LocalMem: Query Context
            Arm->>Arm: Process
            Arm-->>Orch: Result C
        end
        Orch->>Orch: Aggregate Results
        Note over Orch: Vote, average,<br/>or learned aggregation
        Orch-->>Orch: Consensus Result
    end

    Orch->>GlobalMem: Update Knowledge Graph
```

## Memory Data Flow

### Write Operations

```mermaid
flowchart TD
    ARM_RESULT[Arm Produces Result] --> PROV[Attach Provenance]
    PROV --> CLASS{Classify Data}

    CLASS -->|Ephemeral| TEMP[Discard After Task]
    CLASS -->|Local| LOCAL_WRITE[Write to Local Memory]
    CLASS -->|Global| GLOBAL_WRITE[Write to Global Memory]

    LOCAL_WRITE --> VECTOR[Vectorize if Text]
    VECTOR --> QDRANT[Store in Qdrant]
    QDRANT --> INDEX[Update Index]

    GLOBAL_WRITE --> SANITIZE[PII Sanitization]
    SANITIZE --> EXTRACT[Extract Entities/Relations]
    EXTRACT --> PSQL[PostgreSQL Write]
    PSQL --> UPDATE_GRAPH[Update Knowledge Graph]

    INDEX --> CACHE_INV[Invalidate Related Cache]
    UPDATE_GRAPH --> CACHE_INV
```

### Read Operations

```mermaid
flowchart LR
    QUERY[Memory Query] --> L1{L1: Redis Cache}
    L1 -->|Hit| RETURN1[Return Result]
    L1 -->|Miss| L2{L2: Local Arm Memory}

    L2 -->|Hit| PROMOTE1[Promote to L1]
    PROMOTE1 --> RETURN2[Return Result]

    L2 -->|Miss| L3{L3: Global Knowledge Graph}
    L3 -->|Hit| PROMOTE2[Promote to L2 & L1]
    PROMOTE2 --> RETURN3[Return Result]

    L3 -->|Miss| EXTERNAL[Query External Sources]
    EXTERNAL --> STORE[Store in L3, L2, L1]
    STORE --> RETURN4[Return Result]
```

### Memory Routing Strategy

```python
class MemoryRouter:
    def route_query(self, query, context):
        # Classify query type
        if is_recent(query, window="5m"):
            return "L1_cache"  # Redis

        domain = extract_domain(query)
        if domain in ["code", "docs", "data"]:
            # Domain-specific local memory
            return f"L2_{domain}_vector_db"

        if is_entity_query(query):
            return "L3_knowledge_graph"  # PostgreSQL

        if requires_external_data(query):
            return "external_sources"

        # Default to global search
        return "L3_knowledge_graph"
```

## Inter-Component Communication

### Message Format

All inter-component messages follow this schema:

```json
{
  "message_id": "uuid-v4",
  "timestamp": "2025-11-10T10:30:00Z",
  "from": "orchestrator",
  "to": "coder-arm",
  "message_type": "task_request",
  "payload": {
    "task_id": "task-12345",
    "action": "generate_function",
    "context": {},
    "constraints": [],
    "budget": {
      "max_tokens": 4000,
      "max_time_seconds": 30
    }
  },
  "trace_id": "trace-uuid",
  "parent_message_id": "parent-uuid"
}
```

### Communication Patterns

#### 1. Request-Response (Synchronous)

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Arm as Arm

    Orch->>+Arm: POST /execute
    Note over Arm: Process Task<br/>(max 30s timeout)
    Arm-->>-Orch: 200 OK + Result
```

#### 2. Fire-and-Forget (Asynchronous)

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Queue as Task Queue
    participant Arm as Arm Worker

    Orch->>Queue: Enqueue Task
    Orch-->>Orch: Continue

    Note over Queue: Task persisted

    Arm->>Queue: Poll for Tasks
    Queue-->>Arm: Task
    Arm->>Arm: Process
    Arm->>Queue: Mark Complete
```

#### 3. Publish-Subscribe (Events)

```mermaid
sequenceDiagram
    participant Arm as Arm (Publisher)
    participant Bus as Event Bus
    participant Sub1 as Subscriber 1
    participant Sub2 as Subscriber 2

    Arm->>Bus: Publish Event<br/>(e.g., "vulnerability_found")
    Bus->>Sub1: Notify
    Bus->>Sub2: Notify
    Sub1->>Sub1: Handle Event
    Sub2->>Sub2: Handle Event
```

### Direct Arm-to-Arm Communication

Certain workflows benefit from direct communication:

```mermaid
graph LR
    PLAN[Planner Arm] -->|Execution Plan| EXEC[Executor Arm]
    CODE[Coder Arm] -->|Code Artifact| JUDGE[Judge Arm]
    JUDGE -->|Validation Result| CODE
    RETR[Retriever Arm] -->|Retrieved Context| CODE
```

**When to use direct communication:**
- High-frequency interactions (e.g., code validation loop)
- Large data transfers (avoid orchestrator bottleneck)
- Tight coupling between specific arms (e.g., coder + judge)

**Constraints:**
- Must register intent with orchestrator
- Include provenance in all messages
- Respect capability boundaries (no privilege escalation)

## Provenance Tracking

Every data artifact includes complete lineage:

```json
{
  "artifact_id": "art-uuid",
  "artifact_type": "code_function",
  "content": "def hello(): ...",
  "provenance": {
    "created_by": "coder-arm",
    "created_at": "2025-11-10T10:30:00Z",
    "task_id": "task-12345",
    "parent_task_id": "task-12300",
    "input_sources": [
      {
        "source_id": "doc-456",
        "source_type": "documentation",
        "relevance_score": 0.92
      }
    ],
    "transformations": [
      {
        "step": 1,
        "operation": "template_fill",
        "tool": "code_generator_v1"
      },
      {
        "step": 2,
        "operation": "syntax_validation",
        "tool": "ast_parser"
      }
    ],
    "validation_status": {
      "validated": true,
      "validator": "judge-arm",
      "confidence": 0.95,
      "checks_passed": ["syntax", "type_hints", "docstring"]
    },
    "model_info": {
      "model_name": "gpt-3.5-turbo",
      "prompt_hash": "sha256:abc123...",
      "temperature": 0.3,
      "tokens_used": 350
    }
  }
}
```

### Provenance Flow

```mermaid
flowchart TD
    INPUT[Input Data] --> ARM[Arm Processes]
    ARM --> ATTACH[Attach Metadata]

    ATTACH --> PROV[Provenance Record]
    PROV --> CONTENT[Content Hash]
    PROV --> SOURCE[Source References]
    PROV --> TRANSFORM[Transformation Log]
    PROV --> VALID[Validation Results]

    CONTENT --> STORE[Storage]
    SOURCE --> STORE
    TRANSFORM --> STORE
    VALID --> STORE

    STORE --> QUERY[Queryable Provenance]
```

## Error Handling Flow

### Error Classification

```mermaid
flowchart TD
    ERROR[Error Occurred] --> CLASSIFY{Error Type}

    CLASSIFY -->|Transient| RETRY[Retry Logic]
    CLASSIFY -->|Invalid Input| USER_ERROR[Return 400]
    CLASSIFY -->|Auth/Authz| SECURITY[Return 403]
    CLASSIFY -->|Resource Limit| BACKPRESSURE[Apply Backpressure]
    CLASSIFY -->|Logic Error| ESCALATE[Escalate to Orchestrator]
    CLASSIFY -->|Critical| SHUTDOWN[Graceful Shutdown]

    RETRY --> BACKOFF{Retry Count}
    BACKOFF -->|< Max| WAIT[Exponential Backoff]
    WAIT --> RETRY_OP[Retry Operation]
    RETRY_OP --> SUCCESS{Success?}
    SUCCESS -->|Yes| RECOVER[Recovery Complete]
    SUCCESS -->|No| RETRY

    BACKOFF -->|>= Max| GIVE_UP[Return 503]

    USER_ERROR --> LOG1[Log Warning]
    SECURITY --> LOG2[Log Alert]
    BACKPRESSURE --> LOG3[Log Info]
    ESCALATE --> LOG4[Log Error]
    SHUTDOWN --> LOG5[Log Critical]

    LOG1 --> METRICS
    LOG2 --> METRICS
    LOG3 --> METRICS
    LOG4 --> METRICS
    LOG5 --> METRICS

    METRICS[Update Metrics]
```

### Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(TransientError)
)
async def call_arm(arm_endpoint, payload):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            arm_endpoint,
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
```

### Circuit Breaker Pattern

```mermaid
stateDiagram-v2
    [*] --> Closed

    Closed --> Open: Failure threshold exceeded
    Open --> HalfOpen: Timeout elapsed
    HalfOpen --> Closed: Success
    HalfOpen --> Open: Failure

    Closed : Allow all requests
    Open : Reject all requests<br/>Return cached/default
    HalfOpen : Allow limited requests<br/>Test recovery
```

**Implementation:**

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_external_api(url):
    # Will open circuit after 5 consecutive failures
    # Attempt recovery after 60 seconds
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

### Error Propagation

```mermaid
sequenceDiagram
    participant Arm as Arm
    participant Orch as Orchestrator
    participant Monitor as Monitoring

    Arm->>Arm: Error Occurs
    Arm->>Arm: Classify Error

    alt Recoverable
        Arm->>Arm: Retry with Backoff
        Arm->>Monitor: Log Retry
    else Unrecoverable
        Arm->>Orch: Report Failure
        Orch->>Orch: Attempt Alternative
        alt Alternative Available
            Orch->>Arm: Try Different Arm
        else No Alternative
            Orch->>Monitor: Log Critical
            Orch-->>User: Return Error Response
        end
    end

    Monitor->>Monitor: Update Metrics
    Monitor->>Monitor: Check Thresholds
    alt Threshold Exceeded
        Monitor->>Monitor: Trigger Alert
    end
```

## See Also

- [System Architecture Overview](./system-overview.md)
- [Component Specifications](../components/README.md)
- [Error Handling Guide](../engineering/error-handling.md)
- [Monitoring and Observability](../operations/monitoring.md)
