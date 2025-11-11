# Getting Started with OctoLLM

**Estimated Time**: 15 minutes
**Difficulty**: Beginner
**Prerequisites**: Docker, Docker Compose, and a terminal

## Quick Start Overview

This guide will help you:
1. Clone and set up OctoLLM locally
2. Run the system with Docker Compose
3. Submit your first task
4. View results and explore the system
5. Understand next steps for development

By the end of this guide, you'll have a fully functional OctoLLM system running on your local machine.

---

## Step 1: Clone the Repository (2 minutes)

```bash
# Clone the repository
git clone https://github.com/your-org/octollm.git
cd octollm

# Check you're in the right place
ls -la
# You should see: docker-compose.yml, orchestrator/, arms/, reflex-layer/, etc.
```

---

## Step 2: Environment Configuration (3 minutes)

### Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Open .env in your editor
nano .env  # or vim, code, etc.
```

### Configure Required Variables

Add your API keys to `.env`:

```bash
# .env file

# LLM API Keys (choose at least one)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Optional: Use local models instead
# LOCAL_LLM_ENDPOINT=http://localhost:11434  # Ollama

# Database Configuration (defaults work for local dev)
POSTGRES_USER=octollm
POSTGRES_PASSWORD=dev-password-change-in-production
POSTGRES_DB=octollm

# Redis Configuration
REDIS_PASSWORD=dev-redis-password

# Qdrant Configuration (vector DB)
QDRANT_API_KEY=  # Leave empty for local dev

# System Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Verify Configuration

```bash
# Check your environment file is valid
cat .env | grep -v "^#" | grep -v "^$"
```

**Important**: Never commit `.env` to version control. It's already in `.gitignore`.

---

## Step 3: Start OctoLLM Services (5 minutes)

### Launch with Docker Compose

```bash
# Pull and build all containers (first time takes 5-10 minutes)
docker-compose up -d

# Watch the startup logs
docker-compose logs -f
```

**What's happening:**
- PostgreSQL database initializing with schema
- Redis cache starting
- Qdrant vector database initializing
- Reflex Layer (Rust) compiling and starting
- Orchestrator (Python) starting
- All 6 Arms starting (Planner, Executor, Coder, Judge, Guardian, Retriever)

### Verify All Services Are Running

```bash
# Check service status
docker-compose ps

# All services should show "Up" status:
# NAME                STATUS              PORTS
# octollm-postgres    Up (healthy)        5432/tcp
# octollm-redis       Up (healthy)        6379/tcp
# octollm-qdrant      Up (healthy)        6333/tcp
# octollm-reflex      Up (healthy)        0.0.0.0:8000->8000/tcp
# octollm-orchestrator Up (healthy)       0.0.0.0:8001->8000/tcp
# octollm-planner-arm Up (healthy)        8080/tcp
# octollm-executor-arm Up (healthy)       8080/tcp
# octollm-coder-arm   Up (healthy)        8080/tcp
# octollm-judge-arm   Up (healthy)        8080/tcp
# octollm-guardian-arm Up (healthy)       8080/tcp
# octollm-retriever-arm Up (healthy)      8080/tcp
```

### Health Check All Components

```bash
# Check reflex layer
curl http://localhost:8000/health

# Check orchestrator
curl http://localhost:8001/health

# Expected response for both:
# {"status":"healthy","component":"...","version":"1.0.0"}
```

**Troubleshooting**: If services fail to start, see [Troubleshooting](#troubleshooting-common-issues) section below.

---

## Step 4: Submit Your First Task (3 minutes)

### Simple Task: List Files

```bash
# Submit a simple task via curl
curl -X POST http://localhost:8001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "List all files in the current directory",
    "constraints": ["Use only safe read commands", "No modifications"],
    "priority": "medium",
    "budget": {
      "max_tokens": 2000,
      "max_time_seconds": 30
    }
  }'
```

**Response:**

```json
{
  "task_id": "task-abc123def456",
  "status": "queued",
  "created_at": "2025-11-10T12:00:00Z",
  "message": "Task queued successfully"
}
```

### Check Task Status

```bash
# Poll for task completion
TASK_ID="task-abc123def456"  # Use your actual task_id from above

curl http://localhost:8001/api/v1/tasks/$TASK_ID
```

**Response when complete:**

```json
{
  "task_id": "task-abc123def456",
  "status": "completed",
  "goal": "List all files in the current directory",
  "result": {
    "success": true,
    "output": "total 24\ndrwxr-xr-x  5 user user 4096 Nov 10 12:00 .\ndrwxr-xr-x  3 user user 4096 Nov 10 11:00 ..\n...",
    "steps_executed": [
      {
        "step": 1,
        "arm": "executor",
        "action": "ls -la",
        "success": true,
        "duration_ms": 120
      },
      {
        "step": 2,
        "arm": "judge",
        "action": "Validate output format",
        "success": true,
        "duration_ms": 85
      }
    ]
  },
  "duration_ms": 1543,
  "created_at": "2025-11-10T12:00:00Z",
  "completed_at": "2025-11-10T12:00:01Z"
}
```

### More Complex Task: Generate Code

```bash
curl -X POST http://localhost:8001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Write a Python function to calculate Fibonacci numbers recursively with memoization",
    "constraints": [
      "Include docstring with examples",
      "Add type hints",
      "Include basic error handling"
    ],
    "acceptance_criteria": [
      "Function should work for n >= 0",
      "Must have O(n) time complexity",
      "Code should be well-documented"
    ],
    "priority": "medium"
  }'
```

---

## Step 5: Explore the System (2 minutes)

### View System Metrics

```bash
# Prometheus metrics
curl http://localhost:8001/metrics

# You'll see metrics like:
# octollm_tasks_total{component="orchestrator",status="success"} 1
# octollm_task_duration_seconds_bucket{component="orchestrator",le="5.0"} 1
# octollm_arm_invocations_total{arm_id="executor",success="true"} 1
# octollm_cache_hits_total{layer="reflex"} 0
```

### Access Grafana Dashboard

```bash
# Open Grafana in browser
open http://localhost:3000

# Default credentials:
# Username: admin
# Password: admin
```

Navigate to "OctoLLM System Overview" dashboard to see:
- Task success rates
- Latency percentiles (P50, P95, P99)
- Cache hit rates
- Token usage by model
- Active tasks

### Check Logs

```bash
# View orchestrator logs
docker-compose logs -f orchestrator

# View specific arm logs
docker-compose logs -f planner-arm

# View reflex layer logs
docker-compose logs -f reflex-layer

# View all logs
docker-compose logs -f
```

### Access PostgreSQL Database

```bash
# Connect to database
docker-compose exec postgres psql -U octollm -d octollm

# Run queries
SELECT * FROM task_history ORDER BY created_at DESC LIMIT 5;
SELECT * FROM entities LIMIT 10;

# Exit
\q
```

### Access Qdrant Vector DB

```bash
# Qdrant has a web UI
open http://localhost:6333/dashboard

# Or use API
curl http://localhost:6333/collections
```

---

## Example Tasks to Try

### 1. Simple File Operation

```json
{
  "goal": "Count the number of Python files in the current directory",
  "constraints": ["Read-only operation"],
  "priority": "low"
}
```

### 2. Code Analysis

```json
{
  "goal": "Analyze the orchestrator/main.py file and list all defined classes and their methods",
  "constraints": ["Static analysis only", "No execution"],
  "priority": "medium"
}
```

### 3. Web Research

```json
{
  "goal": "Find the latest stable version of FastAPI and summarize its key features",
  "constraints": ["Use official documentation only"],
  "priority": "medium"
}
```

### 4. Code Generation with Tests

```json
{
  "goal": "Create a Python class for a binary search tree with insert, search, and delete methods. Include unit tests.",
  "acceptance_criteria": [
    "All methods must have docstrings",
    "Tests must achieve >90% coverage",
    "Code must pass pylint checks"
  ],
  "priority": "high"
}
```

### 5. Multi-Step Workflow

```json
{
  "goal": "Search for Python best practices for error handling, summarize them, and generate example code demonstrating each pattern",
  "constraints": ["Use authoritative sources", "Examples must be executable"],
  "priority": "medium",
  "budget": {
    "max_tokens": 8000,
    "max_time_seconds": 120
  }
}
```

---

## Understanding the Workflow

### Request Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Reflex
    participant Orchestrator
    participant Planner
    participant Executor
    participant Judge

    User->>Reflex: POST /api/v1/tasks
    Reflex->>Reflex: Check cache
    Reflex->>Reflex: PII filter
    Reflex->>Orchestrator: Forward request
    Orchestrator->>Planner: Generate plan
    Planner->>Orchestrator: Return subtasks
    Orchestrator->>Executor: Execute subtask 1
    Executor->>Orchestrator: Return result
    Orchestrator->>Judge: Validate result
    Judge->>Orchestrator: Validation passed
    Orchestrator->>User: Return completed task
```

### What Happens Behind the Scenes

1. **Reflex Layer**: Fast preprocessing
   - Checks cache (if task seen before, return immediately)
   - Scans for PII and prompt injections
   - Validates input schema

2. **Orchestrator**: Planning and coordination
   - Parses task goal and constraints
   - Routes to Planner Arm for decomposition
   - Receives execution plan (3-7 steps)

3. **Execution Loop**: Sequential execution
   - For each step in plan:
     - Routes to appropriate Arm
     - Waits for completion
     - Updates context for next step
     - Handles errors with retry logic

4. **Validation**: Quality assurance
   - Judge Arm validates outputs
   - Checks acceptance criteria
   - Verifies no hallucinations

5. **Result Aggregation**: Integration
   - Orchestrator combines all step results
   - Adds provenance metadata
   - Caches for future similar queries
   - Returns to user

---

## Stopping and Cleanup

### Stop Services (Preserve Data)

```bash
# Stop all containers but keep data volumes
docker-compose stop

# Start again later
docker-compose start
```

### Full Cleanup (Delete All Data)

```bash
# Stop and remove containers, networks, and volumes
docker-compose down -v

# Remove all images (optional)
docker-compose down -v --rmi all
```

### Selective Cleanup

```bash
# Remove only specific volumes
docker volume rm octollm_postgres-data
docker volume rm octollm_redis-data
docker volume rm octollm_qdrant-data

# Rebuild specific service
docker-compose up -d --build orchestrator
```

---

## Troubleshooting Common Issues

### Issue: Services Won't Start

**Symptom**: `docker-compose ps` shows services as "Restarting" or "Exited"

**Solution**:

```bash
# Check logs for errors
docker-compose logs orchestrator | tail -50

# Common causes:
# 1. Missing API key
grep OPENAI_API_KEY .env  # Should show a key

# 2. Port already in use
lsof -i :8001  # Check if port 8001 is in use
# Kill the process or change port in docker-compose.yml

# 3. Database connection failed
docker-compose logs postgres | grep ERROR
```

### Issue: Database Connection Errors

**Symptom**: `could not connect to server: Connection refused`

**Solution**:

```bash
# Check Postgres is running and healthy
docker-compose ps postgres

# Verify database initialized
docker-compose exec postgres psql -U octollm -d octollm -c "\dt"

# If no tables, reinitialize:
docker-compose down -v
docker-compose up -d
```

### Issue: Orchestrator Can't Reach Arms

**Symptom**: `Connection refused` or `HTTP 503` when calling arms

**Solution**:

```bash
# Check all arms are running
docker-compose ps | grep arm

# Verify internal network connectivity
docker-compose exec orchestrator ping planner-arm

# Check DNS resolution
docker-compose exec orchestrator nslookup planner-arm

# Restart with fresh network
docker-compose down
docker-compose up -d
```

### Issue: Out of Memory Errors

**Symptom**: `Killed` or OOM errors in logs

**Solution**:

```bash
# Check Docker memory limits
docker stats

# Increase Docker memory (Docker Desktop):
# Settings > Resources > Memory > 8GB+

# Reduce replica counts in docker-compose.yml:
# services:
#   orchestrator:
#     deploy:
#       replicas: 1  # Reduce from 2
```

### Issue: Slow Performance

**Symptom**: Tasks take >30 seconds for simple operations

**Solution**:

```bash
# Check system resource usage
docker stats

# Check Redis cache is working
docker-compose exec redis redis-cli
> KEYS *
> INFO stats

# Enable debug logging
# In .env:
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

### Issue: API Key Invalid

**Symptom**: `Authentication failed` or `Invalid API key`

**Solution**:

```bash
# Verify API key format
grep OPENAI_API_KEY .env
# Should start with: sk-proj-... or sk-...

# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# If invalid, get new key from:
# https://platform.openai.com/api-keys
```

### Issue: PII Detected Errors

**Symptom**: `Blocked by safety guardian: PII detected`

**Solution**:

```bash
# This is intentional! The system detected sensitive data.
# Options:

# 1. Remove PII from your request
# Don't include: emails, SSNs, credit cards, phone numbers

# 2. Disable PII detection (DEV ONLY, not for production)
# In .env:
DISABLE_PII_FILTERING=true

# Restart
docker-compose restart guardian-arm
```

---

## Next Steps

### For Developers

1. **[Development Environment](./dev-environment.md)** - Set up IDE, linting, testing
2. **[Creating Custom Arms](./custom-arms.md)** - Build your own specialized arms
3. **[Local Development Workflow](./local-development.md)** - Day-to-day development practices
4. **[Debugging Guide](./debugging.md)** - Advanced debugging techniques

### For Operators

1. **[Docker Guide](./docker-guide.md)** - Advanced Docker configurations
2. **[Database Setup](./database-setup.md)** - PostgreSQL, Qdrant, Redis deep dive
3. **[Monitoring](../operations/monitoring.md)** - Set up Prometheus and Grafana
4. **[Deployment](../operations/deployment-guide.md)** - Production Kubernetes deployment

### For Architecture Understanding

1. **[System Overview](../architecture/system-overview.md)** - Detailed architecture
2. **[Data Flow](../architecture/data-flow.md)** - How requests flow through the system
3. **[Component Specifications](../components/)** - Deep dive into each component
4. **[Memory Systems](./memory-systems.md)** - Distributed memory architecture

### Try These Challenges

1. **Challenge 1**: Modify `docker-compose.yml` to add a new arm
2. **Challenge 2**: Create a custom task that uses all 6 arms
3. **Challenge 3**: Implement a Python client library for the API
4. **Challenge 4**: Add a new PII detection pattern to the Reflex Layer
5. **Challenge 5**: Create a Grafana dashboard showing custom metrics

---

## Quick Reference Commands

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Stop everything
docker-compose stop

# Restart a service
docker-compose restart [service-name]

# Rebuild a service
docker-compose up -d --build [service-name]

# Execute command in container
docker-compose exec [service-name] [command]

# View service status
docker-compose ps

# View resource usage
docker stats

# Clean up everything
docker-compose down -v

# Submit task
curl -X POST http://localhost:8001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "..."}'

# Check task status
curl http://localhost:8001/api/v1/tasks/[task-id]

# View metrics
curl http://localhost:8001/metrics

# Health check
curl http://localhost:8001/health
```

---

## Getting Help

### Community Resources

- **Documentation**: https://docs.octollm.io
- **GitHub Issues**: https://github.com/your-org/octollm/issues
- **Discord**: https://discord.gg/octollm
- **Stack Overflow**: Tag questions with `octollm`

### Reporting Issues

When reporting issues, include:

```bash
# System information
docker-compose version
docker version
uname -a

# Service status
docker-compose ps

# Recent logs
docker-compose logs --tail=100 > logs.txt

# Environment (sanitized, no API keys!)
cat .env | grep -v "API_KEY"
```

### Contributing

See [Contributing Guide](../guides/contributing.md) for:
- Code of conduct
- Development workflow
- Pull request process
- Coding standards

---

## Success! 🎉

You now have OctoLLM running locally and have submitted your first tasks. You understand:

- ✅ How to start and stop services
- ✅ How to submit tasks via API
- ✅ How to view results and metrics
- ✅ Basic troubleshooting techniques
- ✅ Where to go next for deeper learning

**Next recommended action**: Read [Development Environment Setup](./dev-environment.md) to configure your IDE and start contributing code.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Documentation Team
