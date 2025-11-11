# Orchestrator Service

The Orchestrator is the central brain of OctoLLM, responsible for strategic planning, task delegation, and coordination across all specialized arms.

## Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM Integration**: OpenAI GPT-4, Anthropic Claude 3 Opus
- **Database**: PostgreSQL 15+ (global memory), Redis 7+ (caching)
- **Observability**: Prometheus metrics, structured logging

## Architecture

The Orchestrator implements the main decision-making loop:

1. **Request Ingress** → Receive TaskContract from Reflex Layer
2. **Cache Check** → Query Redis for similar past solutions
3. **Planning** → Generate multi-step plan using frontier LLM
4. **Delegation** → Route subtasks to appropriate Arms
5. **Execution** → Coordinate parallel/sequential execution
6. **Validation** → Verify results via Judge Arm
7. **Memory Storage** → Store decision traces in PostgreSQL

## Key Components

### API Layer (`src/api/`)
- FastAPI routes for task submission and status queries
- WebSocket endpoint for real-time progress updates
- Health check and metrics endpoints

### Core Orchestration (`src/core/`)
- `orchestrator.py` - Main orchestration loop
- `planner.py` - Task decomposition logic
- `router.py` - Arm selection based on capabilities
- `executor.py` - Execution coordination (parallel/sequential)

### Data Models (`src/models/`)
- `task_contract.py` - TaskContract schema
- `arm_capability.py` - Arm capability registry
- `execution_state.py` - Execution tracking

### Utilities (`src/utils/`)
- `cache.py` - Redis caching logic
- `memory.py` - PostgreSQL persistence
- `observability.py` - Logging and metrics

## Configuration

Environment variables (see `.env.example`):

```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Databases
DATABASE_URL=postgresql://user:pass@localhost:5432/octollm
REDIS_URL=redis://localhost:6379

# Orchestrator Settings
MAX_PARALLEL_ARMS=5
TASK_TIMEOUT=300
CACHE_TTL=3600
```

## Development

```bash
# Install dependencies
cd services/orchestrator
poetry install

# Run tests
poetry run pytest tests/ -v --cov=src

# Run locally
poetry run uvicorn src.api.main:app --reload --port 8000
```

## API Endpoints

- `POST /v1/tasks` - Submit new task
- `GET /v1/tasks/{task_id}` - Get task status
- `WS /v1/tasks/{task_id}/stream` - Real-time progress
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Performance Targets

- Task routing latency: <100ms P95
- LLM call timeout: 30s default
- Cache hit rate: >60% after warmup
- Concurrent tasks: 50+ per instance

## Security

- JWT authentication for all API requests
- Rate limiting: 100 req/min per API key
- Input validation via Pydantic schemas
- Secrets loaded from environment (never hardcoded)

## References

- [Orchestrator Implementation Guide](../../docs/implementation/orchestrator-impl.md)
- [API Contract Specifications](../../docs/api/component-contracts.md)
- [Architecture Overview](../../docs/architecture/system-overview.md)
