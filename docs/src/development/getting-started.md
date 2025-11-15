# Getting Started

Quick start guide for setting up OctoLLM development environment and running your first task.

## Prerequisites

### Required

- **Docker**: 20.10+ (for local services)
- **Docker Compose**: 2.0+
- **Python**: 3.11+ (for Orchestrator and Arms)
- **Rust**: 1.75+ (for Reflex Layer)
- **Git**: 2.30+

### Optional

- **Kubernetes**: For production deployment (minikube for local testing)
- **PostgreSQL**: 14+ (or use Docker Compose)
- **Redis**: 7+ (or use Docker Compose)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/doublegate/OctoLLM.git
cd OctoLLM
```

### 2. Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=sk-...
# Or ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check service health
docker-compose ps
```

### 4. Verify Installation

```bash
# Test Reflex Layer
curl http://localhost:8001/health

# Test Orchestrator
curl http://localhost:8000/health

# View logs
docker-compose logs -f orchestrator
```

## Development Setup

For detailed setup instructions for each language:

- [Python Setup](./dev-environment.md#python-setup)
- [Rust Setup](./dev-environment.md#rust-setup)
- [Docker Setup](./dev-environment.md#docker-setup)

## Running Tests

```bash
# All tests
docker-compose run --rm orchestrator pytest

# Specific component
docker-compose run --rm orchestrator pytest tests/unit/

# With coverage
docker-compose run --rm orchestrator pytest --cov=octollm --cov-report=html
```

See [Testing Guide](./testing.md) for comprehensive testing documentation.

## Your First Task

```bash
# Create a task via API
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Analyze security vulnerabilities in Python code",
    "constraints": {"max_time_seconds": 300},
    "context": {"language": "python"},
    "acceptance_criteria": ["Find at least 3 vulnerability types"]
  }'

# Get task status
curl http://localhost:8000/api/v1/tasks/{task_id}
```

## Interactive API Documentation

Once services are running, access interactive documentation:

- **Orchestrator**: http://localhost:8000/docs
- **Reflex Layer**: http://localhost:8001/docs

## Troubleshooting

### Services won't start

```bash
# Check Docker daemon
docker ps

# View detailed logs
docker-compose logs orchestrator
docker-compose logs reflex-layer

# Restart services
docker-compose restart
```

### Database connection errors

```bash
# Ensure PostgreSQL is running
docker-compose ps postgres

# Run migrations
docker-compose run --rm orchestrator alembic upgrade head
```

### Redis connection errors

```bash
# Check Redis
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
```

See [Troubleshooting Playbooks](../operations/troubleshooting-playbooks.md) for more issues.

## Next Steps

- [Development Workflow](./workflow.md) - Git workflow, PR process
- [Development Environment](./dev-environment.md) - Detailed setup
- [Testing Guide](./testing.md) - Writing and running tests
- [Custom Arms](./custom-arms.md) - Build your own specialized arms
- [Contributing](./contributing.md) - How to contribute

## See Also

- [Architecture Overview](../architecture/overview.md)
- [API Documentation](../api/rest-api.md)
- [Operations Guide](../operations/deployment-guide.md)
