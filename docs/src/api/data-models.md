# Data Models

Complete reference for all data models and schemas used in OctoLLM APIs.

## Core Models

### TaskContract

Complete task specification with goals, constraints, and budgets.

[Schema Details](./schemas/task-contract.md)

### ArmCapability

Arm registration and capability description.

[Schema Details](./schemas/arm-capability.md)

## Domain-Specific Models

### CodeGeneration

Code generation requests and responses.

[Schema Details](./schemas/code-generation.md)

### ValidationResult

Output validation results from Judge Arm.

[Schema Details](./schemas/validation-result.md)

### RetrievalResult

Knowledge retrieval results from Retriever Arm.

[Schema Details](./schemas/retrieval-result.md)

### PIIDetection

PII detection results from Safety Guardian.

[Schema Details](./schemas/p-i-i-detection.md)

## Common Patterns

### Resource Budget

```python
{
  "max_tokens": 4096,
  "max_time_seconds": 300,
  "max_cost_dollars": 0.50,
  "max_llm_calls": 10
}
```

### Provenance Metadata

```python
{
  "arm_id": "coder-arm-1",
  "timestamp": "2025-11-15T10:30:00Z",
  "command_hash": "sha256:abcd1234...",
  "data_sources": ["github.com/repo/file.py"],
  "model_version": "gpt-4-1106-preview",
  "tests_passed": ["test_syntax", "test_security"]
}
```

## See Also

- [REST API Overview](./rest-api.md)
- [OpenAPI Specifications](./openapi-specs.md)
- [Data Structures](../architecture/data-structures.md)
