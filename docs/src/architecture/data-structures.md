# Data Structures

Core data structures used throughout the OctoLLM system for task management, arm coordination, and memory persistence.

## TaskContract

Central data structure representing a task with all its requirements, constraints, and context.

```python
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class ResourceBudget:
    max_tokens: Optional[int] = None
    max_time_seconds: Optional[int] = None
    max_cost_dollars: Optional[float] = None
    max_llm_calls: Optional[int] = None

@dataclass
class TaskContract:
    task_id: str
    goal: str  # Natural language description
    constraints: Dict[str, Any]  # Hard constraints
    context: Dict[str, Any]  # Background information
    acceptance_criteria: List[str]  # Success conditions
    budget: ResourceBudget  # Resource limits
    assigned_arm: Optional[str] = None
    parent_task_id: Optional[str] = None
    priority: int = 5  # 1 (highest) to 10 (lowest)
    security_policy: Optional[str] = None
```

**Usage**: Created by Orchestrator during task decomposition, passed to Arms for execution.

[Schema Details](../api/schemas/task-contract.md)

## ArmCapability

Describes an arm's capabilities, interface, and resource requirements.

```python
@dataclass
class ArmCapability:
    arm_id: str
    name: str
    description: str
    input_schema: JSONSchema  # Pydantic model or JSON schema
    output_schema: JSONSchema
    capabilities: List[str]  # Tags for routing (e.g., "code", "security")
    cost_tier: int  # 1 (cheap) to 5 (expensive)
    endpoint: str  # Kubernetes service URL
    health_check_url: str
    timeout_seconds: int = 30
    retry_policy: Optional[Dict] = None
```

**Usage**: Registered in Arm Registry, used by Orchestrator for routing decisions.

[Schema Details](../api/schemas/arm-capability.md)

## Memory Models

### Global Semantic Memory

Stored in PostgreSQL, represents project-wide knowledge.

```python
@dataclass
class SemanticMemory:
    memory_id: str
    entity_type: str  # "task", "decision", "fact", "artifact"
    content: str
    embeddings: List[float]  # For semantic search
    metadata: Dict[str, Any]
    source: str  # Which arm created this
    timestamp: datetime
    confidence: float  # 0.0 to 1.0
    tags: List[str]
```

### Local Episodic Memory

Stored in Redis, arm-specific short-term memory.

```python
@dataclass
class EpisodicMemory:
    episode_id: str
    arm_id: str
    task_id: str
    observations: List[str]
    actions: List[str]
    outcomes: List[str]
    ttl_seconds: int = 3600  # 1 hour default
```

## Response Models

### Execution Result

```python
@dataclass
class ExecutionResult:
    task_id: str
    arm_id: str
    status: str  # "success", "failure", "partial"
    output: Any  # Arm-specific output
    confidence: float  # 0.0 to 1.0
    execution_time_ms: int
    tokens_used: int
    error: Optional[str] = None
    provenance: ProvenanceMetadata
```

### Provenance Metadata

```python
@dataclass
class ProvenanceMetadata:
    arm_id: str
    timestamp: datetime
    command_hash: str  # SHA256 of command executed
    data_sources: List[str]  # URLs, file paths, etc.
    model_version: Optional[str] = None
    tests_passed: List[str] = []
```

## See Also

- [Component Contracts](../api/component-contracts.md)
- [OpenAPI Specifications](../api/openapi-specs.md)
- [Memory Systems](../development/memory-systems.md)
