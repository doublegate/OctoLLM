# OctoLLM Local Development Setup

This guide walks you through setting up the complete OctoLLM development environment on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

- **Docker Desktop** 24.0+ ([Download](https://www.docker.com/products/docker-desktop))
  - Docker Engine 24.0+
  - Docker Compose 2.20+
- **Git** 2.30+ ([Download](https://git-scm.com/downloads))
- **VS Code** (optional, recommended) ([Download](https://code.visualstudio.com/))

### Required API Keys

- **OpenAI API Key** (required)
  - Sign up at https://platform.openai.com/
  - Generate API key at https://platform.openai.com/api-keys
  - Requires GPT-4 access for Orchestrator
  - Minimum credit balance: $10

- **Anthropic API Key** (optional)
  - Sign up at https://console.anthropic.com/
  - Generate API key in settings
  - For Claude 3 Opus/Sonnet models

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk Space | 10 GB free | 20 GB free |
| OS | macOS 12+, Ubuntu 20.04+, Windows 10+ (with WSL2) | macOS 13+, Ubuntu 22.04+ |

---

## Quick Start (5 Minutes)

Get OctoLLM running locally in 5 simple steps:

```bash
# 1. Clone the repository
git clone https://github.com/doublegate/OctoLLM.git
cd OctoLLM

# 2. Configure environment
cd infrastructure/docker-compose
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start all services
docker-compose -f docker-compose.dev.yml up -d

# 4. Wait for services to be healthy (30-60 seconds)
docker-compose -f docker-compose.dev.yml ps

# 5. Verify orchestrator is running
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "qdrant": "connected"
  }
}
```

---

## Detailed Setup Instructions

### Step 1: Clone Repository

```bash
# HTTPS (recommended for most users)
git clone https://github.com/doublegate/OctoLLM.git

# OR SSH (if you have SSH keys configured)
git clone git@github.com:doublegate/OctoLLM.git

cd OctoLLM
```

### Step 2: Configure Environment Variables

```bash
cd infrastructure/docker-compose

# Copy example environment file
cp .env.example .env

# Edit with your preferred editor
nano .env  # or vim, code, etc.
```

**Required configuration** (minimum to start):

```bash
# In .env file, update these lines:
OPENAI_API_KEY=sk-your-actual-openai-key-here
POSTGRES_PASSWORD=your-secure-password-here
```

**Optional but recommended**:

```bash
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
GRAFANA_ADMIN_PASSWORD=your-secure-password-here
LOG_LEVEL=DEBUG  # For development debugging
```

### Step 3: Start Services

```bash
# From infrastructure/docker-compose directory
docker-compose -f docker-compose.dev.yml up -d
```

This will:
1. Pull required Docker images (PostgreSQL, Redis, Qdrant)
2. Build custom images for OctoLLM services
3. Create Docker network and volumes
4. Start all 13 services

**First-time build** may take 5-10 minutes depending on your internet connection.

### Step 4: Monitor Service Startup

```bash
# Check service status
docker-compose -f docker-compose.dev.yml ps

# Follow logs for all services
docker-compose -f docker-compose.dev.yml logs -f

# Follow logs for specific service
docker-compose -f docker-compose.dev.yml logs -f orchestrator
```

**Wait for all health checks to pass** (look for "healthy" status):

```
NAME                    STATUS
octollm-postgres        Up (healthy)
octollm-redis           Up (healthy)
octollm-qdrant          Up (healthy)
octollm-reflex          Up (healthy)
octollm-orchestrator    Up (healthy)
octollm-planner         Up (healthy)
...
```

### Step 5: Verify Installation

```bash
# Test orchestrator health
curl http://localhost:8000/health

# Test reflex layer
curl http://localhost:8080/health

# Test planner arm
curl http://localhost:8001/health

# View Prometheus metrics (if monitoring profile enabled)
curl http://localhost:9090
```

---

## Service URLs

Once running, you can access services at:

### Core Services

| Service | URL | Description |
|---------|-----|-------------|
| Orchestrator | http://localhost:8000 | Main API endpoint |
| Reflex Layer | http://localhost:8080 | Preprocessing layer |
| Planner Arm | http://localhost:8001 | Task decomposition |
| Retriever Arm | http://localhost:8002 | Knowledge base search |
| Coder Arm | http://localhost:8003 | Code generation |
| Judge Arm | http://localhost:8004 | Output validation |
| Safety Guardian | http://localhost:8005 | PII detection |
| Executor Arm | http://localhost:8006 | Command execution |

### Infrastructure

| Service | URL | Credentials |
|---------|-----|-------------|
| PostgreSQL | localhost:5432 | user: `octollm`, password: from `.env` |
| Redis | localhost:6379 | No password (dev) |
| Qdrant | http://localhost:6333 | No auth (dev) |
| Prometheus | http://localhost:9090 | N/A (monitoring profile) |
| Grafana | http://localhost:3000 | user: `admin`, password: from `.env` |

### API Documentation

- **Orchestrator API Docs**: http://localhost:8000/docs (FastAPI Swagger UI)
- **Planner API Docs**: http://localhost:8001/docs
- **All Arm APIs**: http://localhost:800{1-6}/docs

---

## Common Commands

### Starting and Stopping

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Start specific service
docker-compose -f docker-compose.dev.yml up -d orchestrator

# Stop all services (keeps data)
docker-compose -f docker-compose.dev.yml down

# Stop and remove all data (WARNING: deletes databases)
docker-compose -f docker-compose.dev.yml down -v

# Restart specific service
docker-compose -f docker-compose.dev.yml restart orchestrator
```

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Specific service
docker-compose -f docker-compose.dev.yml logs -f orchestrator

# Last 100 lines
docker-compose -f docker-compose.dev.yml logs --tail=100

# Since specific time
docker-compose -f docker-compose.dev.yml logs --since=10m
```

### Rebuilding Services

```bash
# Rebuild all services (after code changes)
docker-compose -f docker-compose.dev.yml build

# Rebuild specific service
docker-compose -f docker-compose.dev.yml build orchestrator

# Rebuild and restart
docker-compose -f docker-compose.dev.yml up -d --build orchestrator

# Force rebuild (no cache)
docker-compose -f docker-compose.dev.yml build --no-cache
```

### Database Management

```bash
# Connect to PostgreSQL
docker exec -it octollm-postgres psql -U octollm -d octollm

# Connect to Redis CLI
docker exec -it octollm-redis redis-cli

# Backup PostgreSQL database
docker exec octollm-postgres pg_dump -U octollm octollm > backup.sql

# Restore PostgreSQL database
cat backup.sql | docker exec -i octollm-postgres psql -U octollm octollm
```

---

## Development Workflow

### Hot Reload (Python Services)

Python services (Orchestrator, all Arms) support hot reload in development:

1. Edit code in `services/orchestrator/src/`
2. Save file
3. Service automatically reloads (watch logs)

**No rebuild required** for Python code changes!

### Rebuilding Rust Services

Rust services (Reflex Layer, Executor Arm) require rebuild:

```bash
# After changing Rust code
docker-compose -f docker-compose.dev.yml build reflex-layer
docker-compose -f docker-compose.dev.yml up -d reflex-layer
```

### Running Tests

```bash
# Unit tests (outside Docker)
cd services/orchestrator
poetry install
poetry run pytest tests/unit/ -v

# Integration tests (requires Docker services running)
poetry run pytest tests/integration/ -v

# Run tests inside container
docker-compose -f docker-compose.dev.yml exec orchestrator pytest tests/ -v
```

### Debugging

#### VS Code Debugging

1. Install [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
2. Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Orchestrator",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}/services/orchestrator",
          "remoteRoot": "/app/services/orchestrator"
        }
      ]
    }
  ]
}
```

3. Add `debugpy` to orchestrator:
```bash
# In orchestrator container
pip install debugpy
```

4. Modify `services/orchestrator/src/api/main.py`:
```python
import debugpy
debugpy.listen(("0.0.0.0", 5678))
```

#### Using `pdb` (Python Debugger)

```python
# Add to your code
import pdb; pdb.set_trace()
```

Then attach to container:
```bash
docker attach octollm-orchestrator
```

---

## Troubleshooting

### Services Not Starting

**Issue**: Services fail to start or show "unhealthy" status

**Solutions**:

1. Check logs:
```bash
docker-compose -f docker-compose.dev.yml logs <service-name>
```

2. Verify ports are not in use:
```bash
# Check if ports 8000-8006, 5432, 6379, 6333 are free
lsof -i :8000  # macOS/Linux
netstat -an | grep 8000  # Windows
```

3. Restart Docker Desktop

4. Remove and recreate:
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

### Database Connection Errors

**Issue**: `connection refused` to PostgreSQL

**Solutions**:

1. Wait for PostgreSQL to be healthy:
```bash
docker-compose -f docker-compose.dev.yml ps postgres
# Should show "healthy" status
```

2. Check credentials in `.env`:
```bash
grep POSTGRES .env
```

3. Reset database:
```bash
docker-compose -f docker-compose.dev.yml down postgres
docker volume rm octollm_postgres_data
docker-compose -f docker-compose.dev.yml up -d postgres
```

### Out of Memory

**Issue**: Docker containers crashing with OOM errors

**Solutions**:

1. Increase Docker memory limit:
   - Docker Desktop → Settings → Resources → Memory
   - Increase to 8GB minimum, 16GB recommended

2. Reduce service count (disable arms you're not using):
```bash
# Edit docker-compose.dev.yml
# Comment out services you don't need
docker-compose -f docker-compose.dev.yml up -d
```

### Slow Build Times

**Issue**: `docker-compose build` takes too long

**Solutions**:

1. Use BuildKit:
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
docker-compose -f docker-compose.dev.yml build
```

2. Pre-pull base images:
```bash
docker pull python:3.11-slim
docker pull rust:1.75-slim
docker pull postgres:15-alpine
docker pull redis:7-alpine
```

3. Increase Docker CPU cores:
   - Docker Desktop → Settings → Resources → CPUs

### API Key Errors

**Issue**: `401 Unauthorized` from OpenAI/Anthropic

**Solutions**:

1. Verify API key in `.env`:
```bash
grep OPENAI_API_KEY .env
# Should NOT be empty or contain "your-key-here"
```

2. Check API key validity:
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-your-key-here"
```

3. Restart orchestrator after updating `.env`:
```bash
docker-compose -f docker-compose.dev.yml restart orchestrator
```

### Port Conflicts

**Issue**: `Address already in use` errors

**Solutions**:

1. Find process using port:
```bash
# macOS/Linux
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

2. Change ports in `docker-compose.dev.yml`:
```yaml
services:
  orchestrator:
    ports:
      - "8100:8000"  # Changed from 8000:8000
```

---

## Platform-Specific Notes

### macOS

- **Apple Silicon (M1/M2)**: All images support ARM64
- **Rosetta**: Not required
- **File Sharing**: Ensure `/Users` is shared in Docker Desktop → Settings → Resources → File Sharing

### Linux

- **Docker Group**: Add user to `docker` group to avoid `sudo`:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

- **systemd**: Start Docker on boot:
```bash
sudo systemctl enable docker
```

### Windows (WSL2)

- **WSL2 Required**: Docker Desktop requires WSL2 backend
- **File Location**: Clone repository in WSL2 filesystem (not `/mnt/c/`)
- **Line Endings**: Configure Git:
```bash
git config --global core.autocrlf input
```

---

## VS Code Devcontainer

For a fully integrated development experience:

1. Install [Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. Open OctoLLM folder in VS Code

3. Click "Reopen in Container" when prompted (or `Cmd/Ctrl + Shift + P` → "Remote-Containers: Reopen in Container")

4. VS Code will:
   - Build devcontainer
   - Install Python/Rust tooling
   - Install extensions
   - Forward ports

5. Develop directly inside container with:
   - IntelliSense for Python/Rust
   - Integrated terminal
   - Debugger
   - Git integration

---

## Next Steps

After successful setup:

1. **Read Architecture**: [docs/architecture/system-overview.md](../architecture/system-overview.md)
2. **API Documentation**: [docs/api/component-contracts.md](../api/component-contracts.md)
3. **Contribution Guide**: [docs/guides/contributing.md](../guides/contributing.md)
4. **Submit First Task**: Try the [Getting Started](../implementation/getting-started.md) tutorial

---

## Support

- **Documentation**: [docs/](../)
- **Issues**: https://github.com/doublegate/OctoLLM/issues
- **Discussions**: https://github.com/doublegate/OctoLLM/discussions
- **Discord**: https://discord.gg/octollm (coming soon)

---

**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Core Team
