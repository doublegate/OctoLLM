# OctoLLM Quick Start Guide

**Time Required**: 15 minutes
**Prerequisites**: Docker, Docker Compose, OpenAI API key

## Overview

This guide will walk you through setting up a minimal OctoLLM system on your local machine using Docker Compose. You'll deploy the orchestrator, reflex layer, two arms (Planner and Executor), and supporting infrastructure.

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/octollm.git
cd octollm
```

## Step 2: Set Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
OPENAI_API_KEY=sk-your-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here  # Optional

# Infrastructure
REDIS_URL=redis://redis:6379
POSTGRES_URL=postgresql://octollm:dev-password@postgres:5432/octollm
QDRANT_URL=http://qdrant:6333

# Orchestrator Configuration
DEFAULT_LLM_MODEL=gpt-4-turbo
MAX_CONCURRENT_TASKS=5
DEFAULT_TASK_TIMEOUT=300
LOG_LEVEL=INFO

# Planner Arm Configuration
PLANNER_MODEL=gpt-3.5-turbo
```

**Important**: Never commit `.env` files to version control. Add to `.gitignore`:

```bash
echo ".env" >> .gitignore
```

## Step 3: Start Infrastructure Services

Start Redis, PostgreSQL, and Qdrant:

```bash
docker-compose up -d redis postgres qdrant
```

Wait for services to be ready (about 10 seconds):

```bash
docker-compose ps
```

All three services should show status "Up".

## Step 4: Initialize Database

Run the schema migration:

```bash
docker-compose run --rm orchestrator python scripts/init_db.py
```

Expected output:
```
Creating tables...
✓ entities table created
✓ relationships table created
✓ task_history table created
✓ action_log table created
Database initialized successfully
```

## Step 5: Start OctoLLM Components

Start all OctoLLM services:

```bash
docker-compose up -d reflex-layer orchestrator planner-arm executor-arm
```

Check that all services are healthy:

```bash
docker-compose ps
```

Expected output:
```
NAME                STATUS
redis               Up
postgres            Up
qdrant              Up
reflex-layer        Up (healthy)
orchestrator        Up (healthy)
planner-arm         Up (healthy)
executor-arm        Up (healthy)
```

## Step 6: Verify Installation

Test the health endpoint:

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "llm_api": "available",
    "redis": "connected",
    "postgresql": "connected",
    "arms": {
      "planner": "healthy",
      "executor": "healthy"
    }
  }
}
```

## Step 7: Submit Your First Task

Create a simple task:

```bash
curl -X POST http://localhost:8001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "List all files in the /tmp directory",
    "constraints": ["Read-only operation"],
    "priority": "low"
  }'
```

Response:
```json
{
  "task_id": "task-abc123",
  "status": "accepted",
  "estimated_duration_seconds": 5
}
```

## Step 8: Check Task Status

Poll for results:

```bash
curl http://localhost:8001/api/v1/tasks/task-abc123
```

Once completed:
```json
{
  "task_id": "task-abc123",
  "status": "completed",
  "result": {
    "success": true,
    "output": {
      "files": ["file1.txt", "file2.log"],
      "count": 2
    }
  },
  "execution_details": {
    "plan": [
      {
        "step": 1,
        "description": "Execute ls command",
        "arm": "executor",
        "duration_ms": 150
      }
    ],
    "total_duration_ms": 150
  }
}
```

## Step 9: Try a Complex Task

Submit a multi-step task:

```bash
curl -X POST http://localhost:8001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Create a Python function that calculates fibonacci numbers and save it to /tmp/fib.py",
    "constraints": [
      "Include docstring",
      "Add type hints",
      "Function should be recursive"
    ],
    "acceptance_criteria": [
      "Function is syntactically valid",
      "File exists at /tmp/fib.py"
    ],
    "priority": "medium"
  }'
```

This will demonstrate:
1. Planner arm decomposing the task
2. Coder arm (if deployed) or orchestrator generating code
3. Executor arm writing the file
4. Judge arm (if deployed) validating the result

## Step 10: View Logs

Monitor orchestrator logs:

```bash
docker-compose logs -f orchestrator
```

You'll see structured JSON logs:
```json
{
  "event": "orchestrator.process_task.start",
  "task_id": "task-abc123",
  "timestamp": "2025-11-10T10:30:00Z",
  "level": "info"
}
```

## Common Commands

### Restart Services

```bash
docker-compose restart orchestrator
```

### View All Logs

```bash
docker-compose logs -f
```

### Stop All Services

```bash
docker-compose down
```

### Stop and Remove Data

```bash
docker-compose down -v  # Warning: Deletes all data
```

### Access Redis CLI

```bash
docker-compose exec redis redis-cli
```

### Access PostgreSQL

```bash
docker-compose exec postgres psql -U octollm -d octollm
```

### Rebuild After Code Changes

```bash
docker-compose build orchestrator
docker-compose up -d orchestrator
```

## Monitoring (Optional)

Start Prometheus and Grafana:

```bash
docker-compose up -d prometheus grafana
```

Access dashboards:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Troubleshooting

### "Connection refused" errors

Services may still be starting. Wait 30 seconds and retry.

### "LLM API error"

Check your `OPENAI_API_KEY` in `.env`:

```bash
grep OPENAI_API_KEY .env
```

Verify the key works:

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Orchestrator shows "unhealthy"

Check logs:

```bash
docker-compose logs orchestrator
```

Common issues:
- Database not initialized: Run `init_db.py`
- Redis not accessible: Check `redis` service status
- Wrong environment variables: Verify `.env`

### PostgreSQL connection errors

Ensure database is initialized:

```bash
docker-compose run --rm orchestrator python scripts/init_db.py
```

### High memory usage

Limit container resources in `docker-compose.yml`:

```yaml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          memory: 1G
```

## Next Steps

Now that you have a working OctoLLM system:

1. **Explore the API**: Read the [REST API Reference](../api/rest-api.md)
2. **Add More Arms**: Deploy Coder, Judge, and Safety Guardian arms
3. **Understand Architecture**: Review [System Overview](../architecture/system-overview.md)
4. **Customize**: Create [Custom Arms](../implementation/custom-arms.md)
5. **Deploy to Production**: Follow [Kubernetes Deployment Guide](../operations/deployment-guide.md)

## Example Use Cases

### Code Generation

```json
{
  "goal": "Create a REST API endpoint for user registration",
  "constraints": [
    "Use FastAPI framework",
    "Include input validation",
    "Hash passwords with bcrypt"
  ],
  "acceptance_criteria": [
    "Valid Python syntax",
    "Includes unit tests",
    "Follows PEP 8 style"
  ]
}
```

### Security Reconnaissance

```json
{
  "goal": "Scan the target web application for common vulnerabilities",
  "context": {
    "target_url": "https://example.com",
    "scope": "in-scope.txt"
  },
  "constraints": [
    "Non-destructive tests only",
    "Rate limit to 10 req/sec",
    "Respect robots.txt"
  ]
}
```

### Documentation Generation

```json
{
  "goal": "Generate API documentation from the OpenAPI spec",
  "context": {
    "spec_url": "https://api.example.com/openapi.json"
  },
  "acceptance_criteria": [
    "Markdown format",
    "Includes examples for each endpoint",
    "Generated code samples in Python and cURL"
  ]
}
```

## Getting Help

- **Documentation**: Browse the [full documentation](../README.md)
- **Issues**: Report bugs on [GitHub](https://github.com/your-org/octollm/issues)
- **Community**: Join [Discord](https://discord.gg/octollm)
- **Email**: support@octollm.io

## Clean Up

When you're done experimenting:

```bash
# Stop services
docker-compose down

# Remove all data (optional)
docker-compose down -v

# Remove images (optional)
docker-compose down --rmi all
```

---

**Congratulations!** You've successfully deployed OctoLLM locally and submitted your first tasks. Continue to the [Development Workflow Guide](./development-workflow.md) to learn about building and testing components.
