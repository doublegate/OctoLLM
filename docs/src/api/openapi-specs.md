# OpenAPI Specifications

Complete OpenAPI 3.0 specifications for all OctoLLM services.

## Available Specifications

### Core Services

- [Orchestrator API](./openapi/orchestrator.md) - Central coordination service
- [Reflex Layer API](./openapi/reflex-layer.md) - Preprocessing and caching

### Arm Services

- [Planner Arm API](./openapi/planner.md) - Task decomposition
- [Tool Executor API](./openapi/executor.md) - Command execution
- [Retriever Arm API](./openapi/retriever.md) - Knowledge base search
- [Coder Arm API](./openapi/coder.md) - Code generation/debugging
- [Judge Arm API](./openapi/judge.md) - Output validation
- [Safety Guardian API](./openapi/safety-guardian.md) - PII detection/filtering

## Interactive Documentation

When running services locally, interactive API documentation is available:

**Orchestrator**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Reflex Layer**:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## YAML Specifications

Raw OpenAPI YAML files are available in the repository:

```bash
docs/api/openapi/
├── orchestrator.yaml
├── reflex-layer.yaml
├── planner.yaml
├── executor.yaml
├── retriever.yaml
├── coder.yaml
├── judge.yaml
└── safety-guardian.yaml
```

## Generating Client SDKs

Use [OpenAPI Generator](https://openapi-generator.tech/) to create client SDKs:

```bash
# Python SDK
openapi-generator-cli generate \
  -i docs/api/openapi/orchestrator.yaml \
  -g python \
  -o clients/python

# TypeScript SDK
openapi-generator-cli generate \
  -i docs/api/openapi/orchestrator.yaml \
  -g typescript-axios \
  -o clients/typescript
```

## See Also

- [REST API Overview](./rest-api.md)
- [Data Models](./data-models.md)
- [Component Contracts](./component-contracts.md)
