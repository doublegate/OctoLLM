# Component API Contracts

**Document**: API Specifications
**Version**: 1.0
**Last Updated**: 2025-11-10
**Status**: Production Ready

[← Back to Documentation](../README.md) | [API Reference](./README.md) | [REST API](./rest-api.md)

---

## Table of Contents

1. [Overview](#overview)
   - [Contract Philosophy](#contract-philosophy)
   - [Design Principles](#design-principles)
   - [Versioning Strategy](#versioning-strategy)
2. [Core Data Models](#core-data-models)
   - [TaskContract](#taskcontract)
   - [ArmCapability](#armcapability)
   - [ProvenanceMetadata](#provenancemetadata)
   - [BaseMessage](#basemessage)
   - [ErrorResponse](#errorresponse)
3. [Orchestrator API](#orchestrator-api)
   - [POST /task](#post-task)
   - [GET /task/{task_id}](#get-tasktask_id)
   - [POST /task/{task_id}/cancel](#post-tasktask_idcancel)
   - [GET /health](#get-health)
   - [GET /metrics](#get-metrics)
4. [Arm Interface Contract](#arm-interface-contract)
   - [Standard Arm Endpoints](#standard-arm-endpoints)
   - [Request Format](#request-format)
   - [Response Format](#response-format)
   - [Error Handling](#error-handling)
5. [Reflex Layer API](#reflex-layer-api)
   - [POST /preprocess](#post-preprocess)
   - [GET /cache/{key}](#get-cachekey)
   - [POST /filter/pii](#post-filterpii)
6. [Authentication](#authentication)
   - [Capability Tokens](#capability-tokens)
   - [Token Generation](#token-generation)
   - [Token Verification](#token-verification)
7. [Error Handling](#error-handling-1)
   - [Error Categories](#error-categories)
   - [Error Codes](#error-codes)
   - [Retry Policies](#retry-policies)
8. [Versioning](#versioning)
   - [API Versioning](#api-versioning)
   - [Backward Compatibility](#backward-compatibility)
   - [Deprecation Process](#deprecation-process)
9. [Rate Limiting](#rate-limiting)
   - [Global Rate Limits](#global-rate-limits)
   - [Per-Arm Rate Limits](#per-arm-rate-limits)
   - [Rate Limit Headers](#rate-limit-headers)
10. [OpenAPI Specification](#openapi-specification)
    - [Complete OpenAPI Schema](#complete-openapi-schema)
    - [Generated Client Libraries](#generated-client-libraries)

---

## Overview

OctoLLM's component API contracts define the formal interfaces between all system components. These contracts ensure interoperability, enable independent development and testing, and provide clear boundaries for security isolation.

### Contract Philosophy

The OctoLLM API contracts are designed around these core philosophies:

1. **Explicit over Implicit**: All expectations, constraints, and capabilities are explicitly declared in machine-readable schemas
2. **Fail Fast**: Invalid inputs are rejected immediately with detailed error messages
3. **Defensive Programming**: All components validate inputs and sanitize outputs
4. **Observable by Default**: All operations emit structured logs and metrics
5. **Capability-Based Security**: Access is governed by cryptographic capability tokens, not ambient authority

### Design Principles

#### 1. Strong Typing with Pydantic

All data structures use Pydantic models for:
- Automatic validation
- JSON schema generation
- FastAPI integration
- Clear documentation

Example:

```python
from pydantic import BaseModel, Field, validator

class TaskContract(BaseModel):
    task_id: str = Field(..., description="Unique identifier")
    goal: str = Field(..., min_length=1, max_length=2000)

    @validator('task_id')
    def validate_task_id(cls, v):
        if not v.startswith('task-'):
            raise ValueError('task_id must start with "task-"')
        return v
```

#### 2. Versioned Schemas

All schemas include version information:

```python
class VersionedContract(BaseModel):
    api_version: str = Field(default="v1", const=True)
    schema_version: str = Field(default="1.0.0")
```

#### 3. Graceful Degradation

Contracts support optional fields for backward compatibility:

```python
class TaskContract(BaseModel):
    # Required fields (breaking changes require version bump)
    task_id: str
    goal: str

    # Optional fields (can be added without breaking changes)
    priority: Optional[Priority] = Priority.MEDIUM
    metadata: Optional[Dict[str, Any]] = {}
```

#### 4. Rich Error Information

Errors include actionable information:

```python
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after_seconds: Optional[int] = None
    documentation_url: Optional[str] = None
```

```mermaid
graph TD
    subgraph "Contract Layer"
        TC[TaskContract]
        AC[ArmCapability]
        PM[ProvenanceMetadata]
        BM[BaseMessage]
        ER[ErrorResponse]
    end

    subgraph "Orchestrator"
        O[Orchestrator API]
    end

    subgraph "Arms"
        A1[Planner Arm]
        A2[Coder Arm]
        A3[Executor Arm]
    end

    subgraph "Reflex Layer"
        RL[Reflex API]
    end

    O -->|uses| TC
    O -->|queries| AC
    O -->|sends| BM

    A1 -->|implements| AC
    A2 -->|implements| AC
    A3 -->|implements| AC

    A1 -->|returns| PM
    A2 -->|returns| PM
    A3 -->|returns| PM

    O -->|returns| ER
    A1 -->|returns| ER
    RL -->|returns| ER
```

---

## Core Data Models

This section defines the fundamental data structures used throughout OctoLLM.

### TaskContract

The `TaskContract` defines a formal specification for a task or subtask:

#### Complete Pydantic Model

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskContract(BaseModel):
    """Formal specification for a subtask.

    This contract defines everything needed for an arm to understand
    and execute a task independently.
    """

    # Core identification
    task_id: str = Field(
        ...,
        description="Unique task identifier (format: task-{uuid})",
        regex=r'^task-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )

    # Task definition
    goal: str = Field(
        ...,
        description="Natural language goal description",
        min_length=10,
        max_length=2000
    )

    constraints: List[str] = Field(
        default_factory=list,
        description="Hard constraints (time, cost, safety)",
        max_items=20
    )

    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Relevant background information"
    )

    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions for successful completion",
        max_items=10
    )

    # Resource management
    budget: Dict[str, int] = Field(
        default_factory=lambda: {
            "max_tokens": 4000,
            "max_time_seconds": 30,
            "max_retries": 3
        },
        description="Resource limits"
    )

    # Task metadata
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Task priority level"
    )

    parent_task_id: Optional[str] = Field(
        None,
        description="Parent task if this is a subtask",
        regex=r'^task-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )

    assigned_arm: Optional[str] = Field(
        None,
        description="Target arm identifier (e.g., 'coder-001')"
    )

    # Temporal information
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation timestamp"
    )

    deadline: Optional[datetime] = Field(
        None,
        description="Task deadline (UTC)"
    )

    # Capability requirements
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="Required capability tokens",
        max_items=10
    )

    # API versioning
    api_version: str = Field(
        default="v1",
        const=True,
        description="API version"
    )

    schema_version: str = Field(
        default="1.0.0",
        description="Schema version"
    )

    @validator('deadline')
    def validate_deadline(cls, v, values):
        """Ensure deadline is in the future."""
        if v and v < values.get('created_at', datetime.utcnow()):
            raise ValueError('deadline must be in the future')
        return v

    @validator('budget')
    def validate_budget(cls, v):
        """Validate budget parameters."""
        if v.get('max_tokens', 0) <= 0:
            raise ValueError('max_tokens must be positive')
        if v.get('max_time_seconds', 0) <= 0:
            raise ValueError('max_time_seconds must be positive')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
                "goal": "Generate a Python function to parse JSON with error handling",
                "constraints": [
                    "Must handle malformed JSON gracefully",
                    "Must include type hints",
                    "Must include docstrings"
                ],
                "context": {
                    "language": "python",
                    "python_version": "3.10+",
                    "use_case": "API response parsing"
                },
                "acceptance_criteria": [
                    "Function includes try-except blocks",
                    "Function has type hints",
                    "Function has comprehensive docstring",
                    "Includes usage example"
                ],
                "budget": {
                    "max_tokens": 2000,
                    "max_time_seconds": 15,
                    "max_retries": 2
                },
                "priority": "medium",
                "assigned_arm": "coder-001",
                "required_capabilities": ["code_generation"]
            }
        }
```

#### JSON Schema

```json
{
  "title": "TaskContract",
  "type": "object",
  "required": ["task_id", "goal"],
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^task-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
      "description": "Unique task identifier"
    },
    "goal": {
      "type": "string",
      "minLength": 10,
      "maxLength": 2000,
      "description": "Natural language goal description"
    },
    "constraints": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": 20,
      "description": "Hard constraints"
    },
    "context": {
      "type": "object",
      "description": "Background information"
    },
    "acceptance_criteria": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": 10,
      "description": "Success conditions"
    },
    "budget": {
      "type": "object",
      "properties": {
        "max_tokens": {"type": "integer", "minimum": 1},
        "max_time_seconds": {"type": "integer", "minimum": 1},
        "max_retries": {"type": "integer", "minimum": 0}
      }
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"]
    },
    "parent_task_id": {
      "type": "string",
      "pattern": "^task-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    },
    "assigned_arm": {
      "type": "string"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "deadline": {
      "type": "string",
      "format": "date-time"
    },
    "required_capabilities": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": 10
    },
    "api_version": {
      "type": "string",
      "const": "v1"
    },
    "schema_version": {
      "type": "string"
    }
  }
}
```

### ArmCapability

The `ArmCapability` model describes what an arm can do:

#### Complete Pydantic Model

```python
from typing import Set, Dict, Any, List
from pydantic import BaseModel, Field, HttpUrl

class ArmCapability(BaseModel):
    """Description of what an arm can do.

    This is registered in the ARM_REGISTRY and used by the orchestrator
    for intelligent task routing.
    """

    # Core identification
    arm_id: str = Field(
        ...,
        description="Unique arm identifier (e.g., 'planner-001')",
        regex=r'^[a-z]+-[0-9]{3}$'
    )

    name: str = Field(
        ...,
        description="Human-readable name",
        min_length=1,
        max_length=100
    )

    description: str = Field(
        ...,
        description="Detailed description of arm's purpose",
        min_length=10,
        max_length=500
    )

    # Schema definitions
    input_schema: Dict[str, Any] = Field(
        ...,
        description="JSON schema for input validation"
    )

    output_schema: Dict[str, Any] = Field(
        ...,
        description="JSON schema for output validation"
    )

    # Capability tags
    capabilities: Set[str] = Field(
        ...,
        description="Capability tags (e.g., 'code', 'security', 'web')",
        min_items=1
    )

    # Performance characteristics
    cost_tier: int = Field(
        ...,
        description="Cost tier (1=cheap, 5=expensive)",
        ge=1,
        le=5
    )

    average_latency_ms: float = Field(
        ...,
        description="Average response latency in milliseconds",
        gt=0
    )

    success_rate: float = Field(
        ...,
        description="Historical success rate (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

    # Network configuration
    endpoint: HttpUrl = Field(
        ...,
        description="Kubernetes service URL or function reference"
    )

    health_check_endpoint: HttpUrl = Field(
        ...,
        description="Health check URL"
    )

    # Capacity management
    max_concurrent_tasks: int = Field(
        default=10,
        description="Maximum concurrent tasks this arm can handle",
        ge=1
    )

    # Versioning
    api_version: str = Field(
        default="v1",
        description="API version supported by this arm"
    )

    arm_version: str = Field(
        ...,
        description="Arm implementation version (semver)",
        regex=r'^\d+\.\d+\.\d+$'
    )

    class Config:
        json_schema_extra = {
            "example": {
                "arm_id": "coder-001",
                "name": "Coder Arm",
                "description": "Generates and analyzes code in multiple programming languages with emphasis on security and quality",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "language": {"type": "string"},
                        "context": {"type": "object"}
                    },
                    "required": ["goal", "language"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"},
                        "explanation": {"type": "string"},
                        "confidence": {"type": "number"}
                    },
                    "required": ["code", "language"]
                },
                "capabilities": ["code_generation", "code_analysis", "refactoring"],
                "cost_tier": 3,
                "average_latency_ms": 1500.0,
                "success_rate": 0.94,
                "endpoint": "http://coder-arm:8080",
                "health_check_endpoint": "http://coder-arm:8080/health",
                "max_concurrent_tasks": 20,
                "api_version": "v1",
                "arm_version": "1.2.3"
            }
        }
```

#### Arm Registry Example

```python
from typing import Dict

# Global ARM_REGISTRY
ARM_REGISTRY: Dict[str, ArmCapability] = {
    "planner": ArmCapability(
        arm_id="planner-001",
        name="Task Planner",
        description="Decomposes complex tasks into subtasks with dependencies",
        input_schema={
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "constraints": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["goal"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_id": {"type": "string"},
                            "action": {"type": "string"},
                            "arm": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "required": ["plan"]
        },
        capabilities={"planning", "decomposition", "dependency_resolution"},
        cost_tier=2,
        average_latency_ms=1200.0,
        success_rate=0.92,
        endpoint="http://planner-arm:8080",
        health_check_endpoint="http://planner-arm:8080/health",
        max_concurrent_tasks=15,
        api_version="v1",
        arm_version="1.0.0"
    ),

    "coder": ArmCapability(
        arm_id="coder-001",
        name="Coder Arm",
        description="Generates and analyzes code in multiple languages",
        input_schema={
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "language": {"type": "string"},
                "context": {"type": "object"}
            },
            "required": ["goal", "language"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
                "explanation": {"type": "string"}
            },
            "required": ["code", "language"]
        },
        capabilities={"code_generation", "code_analysis", "refactoring"},
        cost_tier=3,
        average_latency_ms=1500.0,
        success_rate=0.94,
        endpoint="http://coder-arm:8080",
        health_check_endpoint="http://coder-arm:8080/health",
        max_concurrent_tasks=20,
        api_version="v1",
        arm_version="1.2.3"
    ),

    "executor": ArmCapability(
        arm_id="executor-001",
        name="Executor Arm",
        description="Executes tools in isolated sandboxes",
        input_schema={
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "args": {"type": "object"},
                "sandbox": {"type": "string"}
            },
            "required": ["tool", "args"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": "integer"},
                "duration_ms": {"type": "integer"}
            },
            "required": ["exit_code"]
        },
        capabilities={"tool_execution", "sandbox_management", "security_scanning"},
        cost_tier=4,
        average_latency_ms=2500.0,
        success_rate=0.88,
        endpoint="http://executor-arm:8080",
        health_check_endpoint="http://executor-arm:8080/health",
        max_concurrent_tasks=10,
        api_version="v1",
        arm_version="1.1.0"
    ),

    "retriever": ArmCapability(
        arm_id="retriever-001",
        name="Retriever Arm",
        description="Retrieves and summarizes documentation",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["query"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "source": {"type": "string"},
                            "relevance": {"type": "number"}
                        }
                    }
                }
            },
            "required": ["results"]
        },
        capabilities={"documentation_search", "summarization", "context_extraction"},
        cost_tier=2,
        average_latency_ms=800.0,
        success_rate=0.96,
        endpoint="http://retriever-arm:8080",
        health_check_endpoint="http://retriever-arm:8080/health",
        max_concurrent_tasks=25,
        api_version="v1",
        arm_version="1.0.5"
    ),

    "judge": ArmCapability(
        arm_id="judge-001",
        name="Judge Arm",
        description="Validates results and enforces quality standards",
        input_schema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "result": {"type": "object"},
                "criteria": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["task_id", "result"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "score": {"type": "number"},
                "feedback": {"type": "string"},
                "issues": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["passed", "score"]
        },
        capabilities={"result_validation", "quality_assurance", "testing"},
        cost_tier=2,
        average_latency_ms=900.0,
        success_rate=0.98,
        endpoint="http://judge-arm:8080",
        health_check_endpoint="http://judge-arm:8080/health",
        max_concurrent_tasks=30,
        api_version="v1",
        arm_version="1.0.2"
    )
}
```

### ProvenanceMetadata

The `ProvenanceMetadata` model tracks the origin and processing history of data:

#### Complete Pydantic Model

```python
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ProvenanceMetadata(BaseModel):
    """Provenance information for audit and debugging.

    Tracks the complete lineage of a task result including:
    - Which components touched the data
    - When and why transformations occurred
    - Resource consumption
    - Security validations
    """

    # Source identification
    task_id: str = Field(
        ...,
        description="Task identifier",
        regex=r'^task-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )

    arm_id: str = Field(
        ...,
        description="Arm that produced this result"
    )

    # Temporal information
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Result generation timestamp (UTC)"
    )

    processing_time_ms: int = Field(
        ...,
        description="Processing duration in milliseconds",
        ge=0
    )

    # Processing chain
    processing_chain: List[str] = Field(
        default_factory=list,
        description="Ordered list of components that processed this data"
    )

    # Resource consumption
    tokens_consumed: Optional[int] = Field(
        None,
        description="LLM tokens consumed",
        ge=0
    )

    estimated_cost_usd: Optional[float] = Field(
        None,
        description="Estimated processing cost in USD",
        ge=0.0
    )

    # Quality metrics
    confidence: float = Field(
        ...,
        description="Confidence score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

    quality_score: Optional[float] = Field(
        None,
        description="Quality assessment score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

    # Security
    pii_detected: bool = Field(
        default=False,
        description="Whether PII was detected and redacted"
    )

    security_scan_passed: bool = Field(
        default=True,
        description="Whether security scan passed"
    )

    # Model information
    model_used: Optional[str] = Field(
        None,
        description="Model identifier (e.g., 'claude-sonnet-4')"
    )

    model_version: Optional[str] = Field(
        None,
        description="Model version"
    )

    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provenance metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
                "arm_id": "coder-001",
                "timestamp": "2025-11-10T10:30:00Z",
                "processing_time_ms": 1450,
                "processing_chain": ["reflex-layer", "coder-001", "judge-001"],
                "tokens_consumed": 1250,
                "estimated_cost_usd": 0.015,
                "confidence": 0.92,
                "quality_score": 0.88,
                "pii_detected": False,
                "security_scan_passed": True,
                "model_used": "claude-sonnet-4",
                "model_version": "20250929",
                "metadata": {
                    "language": "python",
                    "complexity": "medium",
                    "cached": False
                }
            }
        }
```

### BaseMessage

The `BaseMessage` model defines the structure for inter-component communication:

#### Complete Pydantic Model

```python
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class MessageType(str, Enum):
    """Message types for component communication."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CANCEL_REQUEST = "cancel_request"

class BaseMessage(BaseModel):
    """Base message format for all inter-component communication.

    All messages exchanged between orchestrator, arms, and other
    components use this structure.
    """

    # Message identification
    message_id: str = Field(
        ...,
        description="Unique message identifier",
        regex=r'^msg-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )

    message_type: MessageType = Field(
        ...,
        description="Message type"
    )

    # Routing information
    sender_id: str = Field(
        ...,
        description="Sender component identifier"
    )

    recipient_id: str = Field(
        ...,
        description="Recipient component identifier"
    )

    # Correlation
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for request/response pairs"
    )

    # Message content
    payload: Dict[str, Any] = Field(
        ...,
        description="Message payload"
    )

    # Temporal information
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message creation timestamp (UTC)"
    )

    # Priority and delivery
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Message priority"
    )

    ttl_seconds: int = Field(
        default=300,
        description="Time-to-live in seconds",
        ge=1,
        le=3600
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg-650e8400-e29b-41d4-a716-446655440000",
                "message_type": "task_request",
                "sender_id": "orchestrator-001",
                "recipient_id": "coder-001",
                "correlation_id": "task-550e8400-e29b-41d4-a716-446655440000",
                "payload": {
                    "goal": "Generate Python function",
                    "context": {"language": "python"}
                },
                "timestamp": "2025-11-10T10:30:00Z",
                "priority": "medium",
                "ttl_seconds": 300,
                "metadata": {}
            }
        }
```

### ErrorResponse

The `ErrorResponse` model provides structured error information:

#### Complete Pydantic Model

```python
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, HttpUrl

class ErrorCategory(str, Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
    EXTERNAL = "external"

class ErrorResponse(BaseModel):
    """Structured error response.

    Provides rich error information including error codes,
    human-readable messages, retry guidance, and links to documentation.
    """

    # Error identification
    error_code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'INVALID_TASK_ID')",
        regex=r'^[A-Z_]+$'
    )

    category: ErrorCategory = Field(
        ...,
        description="Error category for classification"
    )

    # Error information
    message: str = Field(
        ...,
        description="Human-readable error message",
        min_length=1,
        max_length=500
    )

    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details (field validation errors, stack traces, etc.)"
    )

    # Retry guidance
    retryable: bool = Field(
        default=False,
        description="Whether the operation can be retried"
    )

    retry_after_seconds: Optional[int] = Field(
        None,
        description="Recommended retry delay in seconds",
        ge=1
    )

    # Documentation
    documentation_url: Optional[HttpUrl] = Field(
        None,
        description="URL to relevant documentation"
    )

    # Context
    request_id: Optional[str] = Field(
        None,
        description="Request ID for debugging"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp (UTC)"
    )

    # Suggestions
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested actions to resolve the error",
        max_items=5
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "INVALID_TASK_ID",
                "category": "validation",
                "message": "Task ID must match format 'task-{uuid}'",
                "details": {
                    "field": "task_id",
                    "value": "invalid-id",
                    "expected_pattern": "^task-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
                },
                "retryable": False,
                "retry_after_seconds": None,
                "documentation_url": "https://docs.octollm.io/api/errors#INVALID_TASK_ID",
                "request_id": "req-750e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-11-10T10:30:00Z",
                "suggestions": [
                    "Ensure task_id starts with 'task-' followed by a valid UUID",
                    "Use the task creation endpoint to generate a valid task_id"
                ]
            }
        }
```

---

## Orchestrator API

The Orchestrator exposes a REST API for task management and system monitoring.

### POST /task

Create and submit a new task for execution.

#### Request

```http
POST /v1/task HTTP/1.1
Host: orchestrator.octollm.svc.cluster.local
Content-Type: application/json
Authorization: Bearer <capability_token>

{
  "goal": "Scan example.com for open ports and identify services",
  "constraints": [
    "Use only non-invasive scanning techniques",
    "Complete within 60 seconds",
    "Minimize network bandwidth"
  ],
  "context": {
    "target": "example.com",
    "scan_type": "service_detection"
  },
  "acceptance_criteria": [
    "All open ports identified",
    "Services correctly detected",
    "No false positives"
  ],
  "priority": "high",
  "budget": {
    "max_tokens": 5000,
    "max_time_seconds": 60,
    "max_retries": 2
  }
}
```

#### Response (202 Accepted)

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
Location: /v1/task/task-550e8400-e29b-41d4-a716-446655440000

{
  "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Task queued for processing",
  "estimated_completion_seconds": 45,
  "created_at": "2025-11-10T10:30:00Z"
}
```

#### Error Response (400 Bad Request)

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error_code": "INVALID_BUDGET",
  "category": "validation",
  "message": "max_time_seconds must be positive",
  "details": {
    "field": "budget.max_time_seconds",
    "value": -10,
    "constraint": "minimum: 1"
  },
  "retryable": false,
  "documentation_url": "https://docs.octollm.io/api/errors#INVALID_BUDGET",
  "suggestions": [
    "Set max_time_seconds to a positive integer",
    "Typical values range from 10 to 300 seconds"
  ]
}
```

#### cURL Example

```bash
curl -X POST https://orchestrator.octollm.io/v1/task \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -d '{
    "goal": "Scan example.com for open ports",
    "constraints": ["Non-invasive only"],
    "priority": "high"
  }'
```

#### Python Client Example

```python
import requests

def create_task(goal: str, priority: str = "medium") -> dict:
    """Create a new task."""
    response = requests.post(
        "https://orchestrator.octollm.io/v1/task",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CAPABILITY_TOKEN}"
        },
        json={
            "goal": goal,
            "priority": priority,
            "budget": {
                "max_tokens": 5000,
                "max_time_seconds": 60
            }
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
result = create_task("Scan example.com for vulnerabilities", priority="high")
print(f"Task ID: {result['task_id']}")
```

### GET /task/{task_id}

Retrieve the status and results of a task.

#### Request

```http
GET /v1/task/task-550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: orchestrator.octollm.svc.cluster.local
Authorization: Bearer <capability_token>
```

#### Response (200 OK) - Running Task

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 0.65,
  "current_step": "executor-001: Running nmap scan",
  "created_at": "2025-11-10T10:30:00Z",
  "started_at": "2025-11-10T10:30:02Z",
  "estimated_completion": "2025-11-10T10:31:15Z",
  "steps_completed": 2,
  "steps_total": 4
}
```

#### Response (200 OK) - Completed Task

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "success": true,
  "created_at": "2025-11-10T10:30:00Z",
  "started_at": "2025-11-10T10:30:02Z",
  "completed_at": "2025-11-10T10:31:12Z",
  "duration_ms": 70000,
  "result": {
    "open_ports": [22, 80, 443],
    "services": {
      "22": "OpenSSH 8.2p1",
      "80": "nginx/1.18.0",
      "443": "nginx/1.18.0 (TLS 1.3)"
    },
    "confidence": 0.95
  },
  "provenance": {
    "arm_id": "executor-001",
    "processing_time_ms": 65000,
    "tokens_consumed": 850,
    "confidence": 0.95
  }
}
```

#### Response (404 Not Found)

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error_code": "TASK_NOT_FOUND",
  "category": "not_found",
  "message": "Task with ID 'task-550e8400-e29b-41d4-a716-446655440000' not found",
  "retryable": false,
  "suggestions": [
    "Verify the task_id is correct",
    "Check if the task has expired (default TTL: 24 hours)"
  ]
}
```

### POST /task/{task_id}/cancel

Cancel a running task.

#### Request

```http
POST /v1/task/task-550e8400-e29b-41d4-a716-446655440000/cancel HTTP/1.1
Host: orchestrator.octollm.svc.cluster.local
Authorization: Bearer <capability_token>
Content-Type: application/json

{
  "reason": "User requested cancellation"
}
```

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Task cancellation initiated",
  "cancelled_at": "2025-11-10T10:30:45Z"
}
```

### GET /health

Health check endpoint for monitoring.

#### Request

```http
GET /v1/health HTTP/1.1
Host: orchestrator.octollm.svc.cluster.local
```

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-10T10:30:00Z",
  "checks": {
    "database": {"status": "up", "latency_ms": 5},
    "redis": {"status": "up", "latency_ms": 1},
    "qdrant": {"status": "up", "latency_ms": 3},
    "arms": {
      "planner-001": {"status": "up"},
      "coder-001": {"status": "up"},
      "executor-001": {"status": "up"},
      "retriever-001": {"status": "up"},
      "judge-001": {"status": "up"}
    }
  }
}
```

### GET /metrics

Prometheus metrics endpoint.

#### Request

```http
GET /v1/metrics HTTP/1.1
Host: orchestrator.octollm.svc.cluster.local
```

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: text/plain; version=0.0.4

# HELP octollm_tasks_total Total tasks processed
# TYPE octollm_tasks_total counter
octollm_tasks_total{status="completed"} 1250
octollm_tasks_total{status="failed"} 45
octollm_tasks_total{status="cancelled"} 12

# HELP octollm_task_duration_seconds Task duration
# TYPE octollm_task_duration_seconds histogram
octollm_task_duration_seconds_bucket{le="1.0"} 120
octollm_task_duration_seconds_bucket{le="5.0"} 890
octollm_task_duration_seconds_bucket{le="10.0"} 1150
octollm_task_duration_seconds_bucket{le="+Inf"} 1307
octollm_task_duration_seconds_sum 8432.5
octollm_task_duration_seconds_count 1307

# HELP octollm_arms_active Currently active arms
# TYPE octollm_arms_active gauge
octollm_arms_active{arm_id="planner-001"} 1
octollm_arms_active{arm_id="coder-001"} 1
octollm_arms_active{arm_id="executor-001"} 1
```

---

## Arm Interface Contract

All arms must implement a standard interface for interoperability with the orchestrator.

### Standard Arm Endpoints

Every arm MUST expose these endpoints:

#### POST /{arm_id}/execute

Execute a task.

**Request**:
```json
{
  "task_contract": {
    "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
    "goal": "Generate Python function for JSON parsing",
    "context": {"language": "python"},
    "budget": {"max_tokens": 2000}
  },
  "capability_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response**:
```json
{
  "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "result": {
    "code": "def parse_json(data: str) -> dict: ...",
    "language": "python",
    "explanation": "Function includes error handling..."
  },
  "provenance": {
    "arm_id": "coder-001",
    "processing_time_ms": 1450,
    "confidence": 0.92
  }
}
```

#### GET /{arm_id}/health

Health check.

**Response**:
```json
{
  "status": "healthy",
  "arm_id": "coder-001",
  "version": "1.2.3",
  "capabilities": ["code_generation", "code_analysis"],
  "active_tasks": 3,
  "max_concurrent_tasks": 20
}
```

#### GET /{arm_id}/capabilities

Get arm capabilities.

**Response**:
```json
{
  "arm_id": "coder-001",
  "name": "Coder Arm",
  "capabilities": ["code_generation", "code_analysis", "refactoring"],
  "input_schema": {...},
  "output_schema": {...},
  "cost_tier": 3,
  "average_latency_ms": 1500.0
}
```

### Request Format

Standard request to arm:

```python
class ArmRequest(BaseModel):
    """Standard request format for arm execution."""
    task_contract: TaskContract
    capability_token: str
    request_id: str = Field(default_factory=lambda: f"req-{uuid.uuid4()}")
    timeout_seconds: int = Field(default=30, ge=1, le=300)

# Example
request = ArmRequest(
    task_contract=TaskContract(
        task_id="task-550e8400-e29b-41d4-a716-446655440000",
        goal="Generate code",
        budget={"max_tokens": 2000}
    ),
    capability_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
    timeout_seconds=30
)
```

### Response Format

Standard response from arm:

```python
class ArmResponse(BaseModel):
    """Standard response format from arm execution."""
    task_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorResponse] = None
    provenance: ProvenanceMetadata

# Example - Success
response = ArmResponse(
    task_id="task-550e8400-e29b-41d4-a716-446655440000",
    success=True,
    result={
        "code": "def parse_json(data): ...",
        "language": "python"
    },
    provenance=ProvenanceMetadata(
        arm_id="coder-001",
        processing_time_ms=1450,
        confidence=0.92
    )
)

# Example - Error
response = ArmResponse(
    task_id="task-550e8400-e29b-41d4-a716-446655440000",
    success=False,
    error=ErrorResponse(
        error_code="EXECUTION_TIMEOUT",
        category="timeout",
        message="Task execution exceeded timeout",
        retryable=True,
        retry_after_seconds=60
    ),
    provenance=ProvenanceMetadata(
        arm_id="coder-001",
        processing_time_ms=30000,
        confidence=0.0
    )
)
```

### Error Handling

Arms must handle errors gracefully and return structured error responses:

```python
async def execute_task(request: ArmRequest) -> ArmResponse:
    """Execute task with comprehensive error handling."""
    try:
        # Validate capability token
        if not verify_capability_token(request.capability_token):
            return ArmResponse(
                task_id=request.task_contract.task_id,
                success=False,
                error=ErrorResponse(
                    error_code="INVALID_CAPABILITY_TOKEN",
                    category="authentication",
                    message="Capability token is invalid or expired",
                    retryable=False
                ),
                provenance=ProvenanceMetadata(
                    arm_id=ARM_ID,
                    processing_time_ms=0,
                    confidence=0.0
                )
            )

        # Execute task with timeout
        result = await asyncio.wait_for(
            _execute_task_internal(request.task_contract),
            timeout=request.timeout_seconds
        )

        return ArmResponse(
            task_id=request.task_contract.task_id,
            success=True,
            result=result,
            provenance=ProvenanceMetadata(...)
        )

    except asyncio.TimeoutError:
        return ArmResponse(
            task_id=request.task_contract.task_id,
            success=False,
            error=ErrorResponse(
                error_code="EXECUTION_TIMEOUT",
                category="timeout",
                message=f"Task execution exceeded {request.timeout_seconds}s",
                retryable=True,
                retry_after_seconds=60
            ),
            provenance=ProvenanceMetadata(...)
        )

    except Exception as e:
        logger.exception("Unexpected error during task execution")
        return ArmResponse(
            task_id=request.task_contract.task_id,
            success=False,
            error=ErrorResponse(
                error_code="INTERNAL_ERROR",
                category="internal",
                message="An unexpected error occurred",
                details={"error_type": type(e).__name__},
                retryable=True,
                retry_after_seconds=30
            ),
            provenance=ProvenanceMetadata(...)
        )
```

---

## Reflex Layer API

The Reflex Layer provides preprocessing, caching, and PII filtering.

### POST /preprocess

Preprocess a request before routing to orchestrator.

#### Request

```http
POST /v1/preprocess HTTP/1.1
Host: reflex.octollm.svc.cluster.local
Content-Type: application/json

{
  "goal": "Find user John Smith's email address john.smith@example.com",
  "context": {"user_id": "12345"}
}
```

#### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "preprocessed_goal": "Find user [REDACTED_NAME]'s email address [REDACTED_EMAIL]",
  "preprocessed_context": {"user_id": "[REDACTED]"},
  "pii_detected": true,
  "pii_types": ["name", "email", "user_id"],
  "cached": false,
  "processing_time_ms": 15
}
```

### GET /cache/{key}

Retrieve cached result.

#### Request

```http
GET /v1/cache/scan_example.com_ports HTTP/1.1
Host: reflex.octollm.svc.cluster.local
```

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "cache_key": "scan_example.com_ports",
  "cached_result": {
    "open_ports": [22, 80, 443],
    "services": {...}
  },
  "cached_at": "2025-11-10T10:25:00Z",
  "expires_at": "2025-11-10T10:30:00Z",
  "hit": true
}
```

#### Response (404 Not Found)

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "cache_key": "scan_example.com_ports",
  "hit": false
}
```

### POST /filter/pii

Filter PII from text.

#### Request

```http
POST /v1/filter/pii HTTP/1.1
Host: reflex.octollm.svc.cluster.local
Content-Type: application/json

{
  "text": "Contact John Smith at john.smith@example.com or call 555-123-4567"
}
```

#### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "filtered_text": "Contact [REDACTED_NAME] at [REDACTED_EMAIL] or call [REDACTED_PHONE]",
  "pii_detected": true,
  "pii_types": ["name", "email", "phone"],
  "redactions": [
    {"type": "name", "original": "John Smith", "position": [8, 18]},
    {"type": "email", "original": "john.smith@example.com", "position": [22, 44]},
    {"type": "phone", "original": "555-123-4567", "position": [53, 65]}
  ]
}
```

---

## Authentication

OctoLLM uses capability-based authentication with JWT tokens.

### Capability Tokens

Capability tokens are JWT tokens that encode:
- Granted capabilities
- Expiration time
- Issuer information
- Scope restrictions

#### Token Structure

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "iss": "octollm-orchestrator",
    "sub": "coder-001",
    "exp": 1731240000,
    "iat": 1731236400,
    "capabilities": [
      "code_generation",
      "memory_read:coder_memory",
      "memory_write:action_log"
    ],
    "scope": {
      "entity_types": ["tool", "library"],
      "max_tokens": 10000
    }
  },
  "signature": "..."
}
```

### Token Generation

```python
import jwt
from datetime import datetime, timedelta
from typing import List, Dict, Any

def generate_capability_token(
    arm_id: str,
    capabilities: List[str],
    scope: Dict[str, Any],
    expires_in_hours: int = 24,
    private_key: str = None
) -> str:
    """Generate a capability token for an arm."""

    now = datetime.utcnow()
    expires = now + timedelta(hours=expires_in_hours)

    payload = {
        "iss": "octollm-orchestrator",
        "sub": arm_id,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "capabilities": capabilities,
        "scope": scope
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )

    return token

# Example
token = generate_capability_token(
    arm_id="coder-001",
    capabilities=[
        "code_generation",
        "memory_read:coder_memory",
        "memory_write:action_log"
    ],
    scope={
        "entity_types": ["tool", "library"],
        "max_tokens": 10000
    },
    expires_in_hours=24,
    private_key=PRIVATE_KEY
)
```

### Token Verification

```python
def verify_capability_token(
    token: str,
    required_capability: str,
    public_key: str
) -> bool:
    """Verify capability token and check for required capability."""

    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer="octollm-orchestrator"
        )

        # Check expiration
        if payload["exp"] < datetime.utcnow().timestamp():
            return False

        # Check capability
        capabilities = payload.get("capabilities", [])
        if required_capability not in capabilities:
            return False

        return True

    except jwt.InvalidTokenError:
        return False
```

---

## Error Handling

### Error Categories

| Category | Description | HTTP Status | Retryable |
|----------|-------------|-------------|-----------|
| `validation` | Invalid input | 400 | No |
| `authentication` | Auth failure | 401 | No |
| `authorization` | Permission denied | 403 | No |
| `not_found` | Resource not found | 404 | No |
| `rate_limit` | Rate limit exceeded | 429 | Yes |
| `timeout` | Operation timeout | 504 | Yes |
| `internal` | Internal server error | 500 | Yes |
| `external` | External service error | 502 | Yes |

### Error Codes

Common error codes:

- `INVALID_TASK_ID`: Task ID format invalid
- `INVALID_BUDGET`: Budget parameters invalid
- `INVALID_CAPABILITY_TOKEN`: Authentication failure
- `INSUFFICIENT_CAPABILITIES`: Missing required capabilities
- `TASK_NOT_FOUND`: Task does not exist
- `RATE_LIMIT_EXCEEDED`: Rate limit hit
- `EXECUTION_TIMEOUT`: Task exceeded time budget
- `MEMORY_LIMIT_EXCEEDED`: Memory allocation failed
- `INTERNAL_ERROR`: Unexpected internal error
- `EXTERNAL_SERVICE_ERROR`: External dependency failed

### Retry Policies

```python
import asyncio
from typing import Callable, TypeVar, Any

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> T:
    """Retry function with exponential backoff."""

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            # Check if retryable
            if hasattr(e, 'retryable') and not e.retryable:
                raise

            if attempt == max_retries:
                raise

            # Calculate delay
            delay = min(base_delay * (exponential_base ** attempt), max_delay)

            # Add jitter
            if jitter:
                import random
                delay *= (0.5 + random.random())

            await asyncio.sleep(delay)

    raise last_exception
```

---

## Versioning

### API Versioning

OctoLLM uses URL-based API versioning:

```
/v1/task          # Version 1
/v2/task          # Version 2 (future)
```

### Backward Compatibility

Changes that are backward compatible:
- Adding new optional fields
- Adding new endpoints
- Adding new error codes
- Expanding enum values

Changes that break compatibility (require version bump):
- Removing or renaming fields
- Changing field types
- Removing endpoints
- Changing required fields

### Deprecation Process

1. **Announce**: Deprecation announced 6 months in advance
2. **Warning**: Deprecated endpoints return `Deprecation` header
3. **Support**: Old version supported for 12 months
4. **Removal**: Old version removed after support period

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Wed, 10 May 2026 10:00:00 GMT
Link: </v2/task>; rel="successor-version"
```

---

## Rate Limiting

### Global Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /task | 100 requests | 1 minute |
| GET /task/{id} | 1000 requests | 1 minute |
| GET /health | Unlimited | - |
| GET /metrics | 60 requests | 1 minute |

### Per-Arm Rate Limits

Each arm has individual rate limits based on `max_concurrent_tasks`:

- Planner: 15 concurrent
- Coder: 20 concurrent
- Executor: 10 concurrent
- Retriever: 25 concurrent
- Judge: 30 concurrent

### Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1731236460
```

Rate limit exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1731236460

{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "category": "rate_limit",
  "message": "Rate limit of 100 requests per minute exceeded",
  "retryable": true,
  "retry_after_seconds": 60
}
```

---

## OpenAPI Specification

### Complete OpenAPI Schema

```yaml
openapi: 3.0.3
info:
  title: OctoLLM API
  description: Distributed AI architecture for offensive security
  version: 1.0.0
  contact:
    name: OctoLLM Team
    url: https://octollm.io
  license:
    name: Apache 2.0
    url: https://www.apache.org/licenses/LICENSE-2.0

servers:
  - url: https://api.octollm.io/v1
    description: Production
  - url: https://staging.octollm.io/v1
    description: Staging
  - url: http://localhost:8000/v1
    description: Development

paths:
  /task:
    post:
      summary: Create task
      operationId: createTask
      tags: [Tasks]
      security:
        - CapabilityToken: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskContract'
      responses:
        '202':
          description: Task accepted
          content:
            application/json:
              schema:
                type: object
                properties:
                  task_id: {type: string}
                  status: {type: string}
                  created_at: {type: string, format: date-time}
        '400':
          description: Invalid input
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /task/{task_id}:
    get:
      summary: Get task status
      operationId: getTask
      tags: [Tasks]
      security:
        - CapabilityToken: []
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Task details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskStatus'
        '404':
          description: Task not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /health:
    get:
      summary: Health check
      operationId: healthCheck
      tags: [System]
      responses:
        '200':
          description: System healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: {type: string}
                  version: {type: string}
                  checks: {type: object}

components:
  schemas:
    TaskContract:
      type: object
      required: [task_id, goal]
      properties:
        task_id: {type: string}
        goal: {type: string}
        constraints: {type: array, items: {type: string}}
        priority: {type: string, enum: [low, medium, high, critical]}

    ErrorResponse:
      type: object
      required: [error_code, category, message]
      properties:
        error_code: {type: string}
        category: {type: string}
        message: {type: string}
        details: {type: object}
        retryable: {type: boolean}

  securitySchemes:
    CapabilityToken:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

### Generated Client Libraries

Generate client libraries using OpenAPI Generator:

```bash
# Python client
openapi-generator-cli generate \
  -i openapi.yaml \
  -g python \
  -o clients/python \
  --additional-properties=packageName=octollm_client

# TypeScript client
openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-fetch \
  -o clients/typescript

# Go client
openapi-generator-cli generate \
  -i openapi.yaml \
  -g go \
  -o clients/go
```

---

**Document Maintainer**: OctoLLM Core Team
**Last Review**: 2025-11-10
**Next Review**: 2025-12-10

---

[← Back to Documentation](../README.md) | [API Reference](./README.md) | [REST API](./rest-api.md)
