# Orchestrator Service

The Orchestrator is the central "brain" of OctoLLM, responsible for strategic planning, task decomposition, arm coordination, and result integration.

## Architecture

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM Integration**: OpenAI (GPT-4, GPT-3.5-turbo), Anthropic (Claude 3)
- **Database**: PostgreSQL (global memory)
- **Cache**: Redis
- **Port**: 8000

## Features

- Task planning and decomposition
- Intelligent arm routing
- Swarm decision-making coordination
- Result aggregation and validation
- Distributed memory management

## Project Structure

```
orchestrator/
├── src/
│   ├── api/          # FastAPI routes and endpoints
│   ├── core/         # Core orchestration logic
│   ├── models/       # Pydantic models and schemas
│   └── utils/        # Utilities and helpers
├── tests/            # Unit and integration tests
├── migrations/       # Alembic database migrations
├── pyproject.toml    # Python dependencies
├── Dockerfile        # Multi-stage Docker build
└── README.md         # This file
```

## Development

See [Development Guide](../../docs/implementation/orchestrator-impl.md) for detailed implementation instructions.

## API Documentation

Once running, API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## References

- [Component Specification](../../docs/components/orchestrator.md)
- [API Contracts](../../docs/api/component-contracts.md)
- [Implementation Guide](../../docs/implementation/orchestrator-impl.md)
