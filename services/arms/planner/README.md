# Planner Arm

The Planner Arm specializes in task decomposition, breaking complex goals into executable subtasks with acceptance criteria.

## Architecture

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM**: GPT-3.5-turbo (cost-optimized)
- **Port**: 8010

## Features

- Hierarchical task decomposition
- Dependency analysis
- Acceptance criteria generation
- Self-assessment and confidence scoring
- Recursive planning for complex tasks

## Project Structure

```
planner/
├── src/
│   ├── api/          # FastAPI routes
│   ├── core/         # Planning algorithms
│   └── models/       # Pydantic models
├── tests/            # Unit and integration tests
├── pyproject.toml    # Python dependencies
├── Dockerfile        # Multi-stage Docker build
└── README.md         # This file
```

## Development

See [Implementation Guide](../../../docs/implementation/planner-arm-impl.md) for details.

## References

- [Component Specification](../../../docs/components/planner-arm.md)
- [Planning Algorithms](../../../docs/architecture/planning-strategies.md)
