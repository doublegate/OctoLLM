# Configuration Reference

Configuration for all OctoLLM components using environment variables and config files.

## Environment Variables

### Orchestrator

```bash
# Server
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000
ORCHESTRATOR_WORKERS=4

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/octollm
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# LLM Provider
LLM_PROVIDER=openai  # or anthropic
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Reflex Layer
REFLEX_LAYER_URL=http://localhost:8001

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # json or text
```

### Reflex Layer

```bash
# Server
REFLEX_LAYER_HOST=0.0.0.0
REFLEX_LAYER_PORT=8001

# Redis Cache
REDIS_URL=redis://localhost:6379/1
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE_MB=100

# Patterns
PII_DETECTION_ENABLED=true
INJECTION_DETECTION_ENABLED=true

# Performance
MAX_CONCURRENT_REQUESTS=1000
TIMEOUT_MS=50
```

### Arms (General)

```bash
# Server
ARM_HOST=0.0.0.0
ARM_PORT=8080

# Orchestrator
ORCHESTRATOR_URL=http://localhost:8000

# LLM (arm-specific)
LLM_MODEL=gpt-3.5-turbo
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.7

# Timeouts
TASK_TIMEOUT_SECONDS=30
LLM_TIMEOUT_SECONDS=20
```

## Configuration Files

### docker-compose.yml

See [Docker Compose Setup](../operations/docker-compose-setup.md)

### Kubernetes

See [Kubernetes Deployment](../operations/kubernetes-deployment.md)

## Secrets Management

**Development**: `.env` files (not committed to git)
**Production**: Kubernetes Secrets or AWS Secrets Manager

See [Secrets Management Strategy](../security/secrets-management.md)

## See Also

- [Deployment Guide](../operations/deployment-guide.md)
- [Operations Documentation](../operations/kubernetes-deployment.md)
