# Arms (Specialized Modules)

Arms are domain-specific execution modules with local autonomy and specialized expertise. Each arm handles a specific class of tasks and reports results back to the Orchestrator.

## Arm Architecture

All arms share a common interface:

```python
class ArmCapability:
    arm_id: str
    name: str
    description: str
    input_schema: JSONSchema
    output_schema: JSONSchema
    capabilities: List[str]  # Tags for routing
    cost_tier: int  # 1 (cheap) to 5 (expensive)
    endpoint: str  # Kubernetes service URL
```

## Implemented Arms

### 1. Planner Arm (Sprint 1.3 - PLANNED)

**Purpose**: Task decomposition and workflow generation
**Technology**: Python, GPT-3.5-turbo
**Status**: 🚧 In Planning

[Details: Planner Arm](./arms/planner-arm.md)

### 2. Tool Executor Arm

**Purpose**: Execute external commands in sandboxed environments
**Technology**: Rust for safety
**Status**: ⏳ Not Started

[Details: Tool Executor Arm](./arms/executor-arm.md)

### 3. Retriever Arm

**Purpose**: Knowledge base search and information synthesis
**Technology**: Python, Qdrant/Weaviate
**Status**: ⏳ Not Started

[Details: Retriever Arm](./arms/retriever-arm.md)

### 4. Coder Arm

**Purpose**: Code generation, debugging, and refactoring
**Technology**: Python, specialized models
**Status**: ⏳ Not Started

[Details: Coder Arm](./arms/coder-arm.md)

### 5. Judge Arm

**Purpose**: Output validation and quality assurance
**Technology**: Python, validation frameworks
**Status**: ⏳ Not Started

[Details: Judge Arm](./arms/judge-arm.md)

### 6. Safety Guardian Arm

**Purpose**: PII detection, content filtering, security checks
**Technology**: Python/Rust, classifiers
**Status**: ⏳ Not Started

[Details: Safety Guardian Arm](./arms/guardian-arm.md)

## Arm Capabilities

| Arm | Primary Function | Input | Output | Cost Tier |
|-----|-----------------|-------|--------|-----------|
| Planner | Task decomposition | TaskContract | List[Subtask] | 2 |
| Tool Executor | Command execution | Command + Args | ExecutionResult | 3 |
| Retriever | Knowledge search | Query + Filters | Documents | 1 |
| Coder | Code generation | Spec + Context | CodePatch | 4 |
| Judge | Validation | Output + Spec | ValidationResult | 2 |
| Safety Guardian | Security checks | Content | SecurityReport | 1 |

## Communication Pattern

```
Orchestrator
    ↓ (TaskContract)
[Arm]
    ↓ (Execute with local autonomy)
[Arm] → Result
    ↓ (Response with confidence, provenance)
Orchestrator (integrate into global state)
```

## See Also

- [API Specifications](../api/openapi-specs.md)
- [Custom Arms Development](../development/custom-arms.md)
- [Component Contracts](../api/component-contracts.md)
