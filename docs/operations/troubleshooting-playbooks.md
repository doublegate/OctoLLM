# Troubleshooting Playbooks

**Purpose**: Step-by-step procedures for diagnosing and resolving common OctoLLM issues
**Audience**: Operations engineers, SREs, on-call responders
**Prerequisites**: Access to logs, metrics, and deployment environment

## Overview

This document provides systematic troubleshooting procedures for common OctoLLM issues. Each playbook follows a structured format:
1. **Symptoms** - How to recognize the problem
2. **Diagnosis** - Steps to identify root cause
3. **Resolution** - How to fix the issue
4. **Prevention** - How to avoid recurrence

## Table of Contents

1. [Service Unavailable](#service-unavailable)
2. [High Latency](#high-latency)
3. [Database Connection Issues](#database-connection-issues)
4. [Memory Leaks](#memory-leaks)
5. [Task Routing Failures](#task-routing-failures)
6. [LLM API Failures](#llm-api-failures)
7. [Cache Performance Issues](#cache-performance-issues)
8. [Resource Exhaustion](#resource-exhaustion)
9. [Security Violations](#security-violations)
10. [Data Corruption](#data-corruption)

---

## Service Unavailable

### Symptoms

- HTTP 503 responses from API
- Health check failures
- No response from service endpoints
- Alert: `ServiceDown` or `ArmDown`

### Diagnosis

**Step 1: Check service status**

```bash
# Docker Compose
docker compose ps

# Kubernetes
kubectl get pods -n octollm
kubectl describe pod <pod-name> -n octollm
```

**Step 2: Check container logs**

```bash
# Docker Compose
docker compose logs --tail=100 orchestrator

# Kubernetes
kubectl logs <pod-name> -n octollm --tail=100
```

**Step 3: Check resource usage**

```bash
# Docker
docker stats

# Kubernetes
kubectl top pods -n octollm
kubectl describe node <node-name>
```

**Step 4: Check dependencies**

```bash
# Verify database connections
docker compose exec orchestrator nc -zv postgres 5432
docker compose exec orchestrator nc -zv redis 6379
docker compose exec orchestrator nc -zv qdrant 6333

# Check database health
docker compose exec postgres pg_isready -U octollm
docker compose exec redis redis-cli ping
```

### Resolution

**Scenario A: Container crashed**

```bash
# Check exit code and restart
docker compose ps
docker compose logs <service>
docker compose restart <service>

# Kubernetes
kubectl get pods -n octollm
kubectl logs <pod-name> -n octollm --previous
kubectl delete pod <pod-name> -n octollm  # Force restart
```

**Scenario B: Out of memory**

```bash
# Increase memory limits
# In .env for Docker Compose:
ORCHESTRATOR_MEMORY_LIMIT=8g

# In Kubernetes:
kubectl edit deployment orchestrator -n octollm
# Update resources.limits.memory to higher value

# Restart service
docker compose up -d orchestrator
# or
kubectl rollout restart deployment orchestrator -n octollm
```

**Scenario C: Database connection failure**

```bash
# Restart database
docker compose restart postgres

# Verify connectivity
docker compose exec orchestrator ping postgres

# Check network
docker network inspect octollm_octollm-network

# Kubernetes: Check network policies
kubectl get networkpolicies -n octollm
```

**Scenario D: Configuration error**

```bash
# Validate environment variables
docker compose config

# Check configuration in running container
docker compose exec orchestrator env | grep POSTGRES

# Fix configuration in .env and restart
docker compose up -d orchestrator
```

### Prevention

1. **Set up health checks**: Ensure all services have proper liveness/readiness probes
2. **Resource reservations**: Set CPU/memory requests and limits
3. **Monitoring**: Alert on service availability (ServiceDown alert)
4. **Auto-restart**: Use `restart: unless-stopped` in Docker Compose
5. **Pod Disruption Budgets**: Ensure minimum replicas in Kubernetes

---

## High Latency

### Symptoms

- Slow API responses (>5 seconds)
- Task processing delays
- Timeouts from clients
- Alert: `HighRequestLatency`

### Diagnosis

**Step 1: Identify slow endpoints**

```bash
# Query Prometheus for P95 latency by endpoint
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'

# Check Grafana dashboard for latency breakdown
```

**Step 2: Check resource utilization**

```bash
# CPU usage
docker stats
# or
kubectl top pods -n octollm

# Memory pressure
free -h
# or
kubectl describe node <node-name>
```

**Step 3: Identify bottlenecks**

```bash
# Check database query performance
docker compose exec postgres psql -U octollm -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"

# Check Redis performance
docker compose exec redis redis-cli --latency

# Check LLM API latency
# Review metrics: llm_api_duration_seconds
```

**Step 4: Profile application**

```bash
# Python profiling (add to orchestrator temporarily)
python -m cProfile -o profile.stats app/main.py

# View profile
python -m pstats profile.stats
> sort cumtime
> stats 20
```

### Resolution

**Scenario A: Database slow queries**

```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_tasks_created_at ON tasks(created_at);
CREATE INDEX CONCURRENTLY idx_entities_type ON entities(entity_type);

-- Optimize frequently accessed queries
EXPLAIN ANALYZE SELECT * FROM tasks WHERE status = 'pending';

-- Update statistics
ANALYZE tasks;
VACUUM ANALYZE;
```

**Scenario B: LLM API latency**

```python
# Implement request batching
# In orchestrator/app/services/llm_client.py

async def batch_requests(requests: List[Request]) -> List[Response]:
    """Batch multiple LLM requests into single API call"""
    combined_prompt = "\n---\n".join([r.prompt for r in requests])

    response = await self.client.chat.completions.create(
        model=self.model,
        messages=[{"role": "user", "content": combined_prompt}]
    )

    # Split and return individual responses
    return parse_batch_response(response)
```

```python
# Implement caching for repeated queries
from functools import lru_cache
import hashlib

async def get_llm_response(prompt: str) -> str:
    # Check Redis cache first
    cache_key = f"llm:{hashlib.md5(prompt.encode()).hexdigest()}"
    cached = await redis_client.get(cache_key)

    if cached:
        cache_hits_total.labels(cache_type="llm").inc()
        return cached

    # Make API call
    response = await llm_client.generate(prompt)

    # Cache for 1 hour
    await redis_client.setex(cache_key, 3600, response)

    return response
```

**Scenario C: Resource contention**

```bash
# Scale horizontally (Kubernetes)
kubectl scale deployment orchestrator --replicas=4 -n octollm

# Docker Compose: Update docker-compose.yml
services:
  orchestrator:
    deploy:
      replicas: 3

# Scale vertically: Increase CPU/memory
kubectl edit deployment orchestrator -n octollm
# Update resources.limits
```

**Scenario D: Network latency**

```bash
# Check network latency between services
docker compose exec orchestrator time curl -s http://planner-arm:8100/health

# Optimize service communication
# Use connection pooling
# Implement circuit breakers
# Add retry logic with exponential backoff
```

### Prevention

1. **Connection pooling**: Configure database connection pools
2. **Caching strategy**: Cache frequently accessed data
3. **Query optimization**: Add indexes, optimize N+1 queries
4. **Request batching**: Batch LLM API requests
5. **Rate limiting**: Prevent resource exhaustion
6. **Horizontal scaling**: Use auto-scaling based on metrics

---

## Database Connection Issues

### Symptoms

- Connection refused errors
- Connection timeout
- `psycopg2.OperationalError` or `ConnectionError`
- Alert: `PostgreSQLDown` or `HighDatabaseConnections`

### Diagnosis

**Step 1: Verify database is running**

```bash
# Check database status
docker compose ps postgres
docker compose exec postgres pg_isready -U octollm

# Kubernetes
kubectl get pods -l app=postgres -n octollm
kubectl logs -l app=postgres -n octollm
```

**Step 2: Check connection limits**

```sql
-- Check current connections
docker compose exec postgres psql -U octollm -c "
SELECT count(*) as current_connections,
       (SELECT setting::int FROM pg_settings WHERE name='max_connections') as max_connections
FROM pg_stat_activity;"

-- View active connections
docker compose exec postgres psql -U octollm -c "
SELECT pid, usename, application_name, client_addr, state, query
FROM pg_stat_activity
WHERE state != 'idle';"
```

**Step 3: Test connectivity**

```bash
# From orchestrator container
docker compose exec orchestrator nc -zv postgres 5432

# Manual connection test
docker compose exec orchestrator psql -h postgres -U octollm -d octollm -c "SELECT 1;"
```

**Step 4: Check network configuration**

```bash
# Docker network
docker network inspect octollm_octollm-network

# Kubernetes network policy
kubectl describe networkpolicy -n octollm
```

### Resolution

**Scenario A: Connection pool exhausted**

```python
# Increase pool size in orchestrator/app/database/connection.py

from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Increased from 5
    max_overflow=40,       # Increased from 10
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,    # Verify connections before use
)
```

**Scenario B: Too many open connections**

```sql
-- Increase max_connections in PostgreSQL
docker compose exec postgres psql -U octollm -c "
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();"

-- Or update postgresql.conf
echo "max_connections = 200" >> data/postgres/postgresql.conf
docker compose restart postgres
```

**Scenario C: Connection leak**

```python
# Fix connection leaks - always use context managers

# Bad (connection leak):
conn = await pool.acquire()
result = await conn.fetch("SELECT * FROM tasks")
# conn never released!

# Good (automatic cleanup):
async with pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM tasks")
    # conn automatically released
```

**Scenario D: Network partition**

```bash
# Docker: Recreate network
docker compose down
docker network prune
docker compose up -d

# Kubernetes: Check DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup postgres.octollm.svc.cluster.local

# Verify network policies allow traffic
kubectl get networkpolicies -n octollm
```

### Prevention

1. **Connection pooling**: Always use connection pools
2. **Context managers**: Use `async with` for automatic cleanup
3. **Health checks**: Monitor database connection count
4. **Graceful shutdown**: Close connections on service shutdown
5. **Connection timeout**: Set reasonable timeout values
6. **Monitoring**: Alert on high connection count

---

## Memory Leaks

### Symptoms

- Gradual memory increase over time
- OOMKilled pod restarts (Kubernetes)
- Swap usage increasing
- Alert: `HighMemoryUsage`

### Diagnosis

**Step 1: Identify leaking service**

```bash
# Monitor memory over time
docker stats

# Kubernetes
kubectl top pods -n octollm --watch

# Check for OOMKilled containers
kubectl get pods -n octollm -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'
```

**Step 2: Profile memory usage**

```python
# Add memory profiling to orchestrator
# Install: pip install memory-profiler

from memory_profiler import profile

@profile
async def process_task(task_id: str):
    # Function code
    pass

# Run with:
# python -m memory_profiler app/main.py
```

```python
# Track object counts
import gc
import sys

def get_memory_usage():
    """Get current memory usage details"""
    gc.collect()

    object_counts = {}
    for obj in gc.get_objects():
        obj_type = type(obj).__name__
        object_counts[obj_type] = object_counts.get(obj_type, 0) + 1

    # Sort by count
    sorted_counts = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)

    return sorted_counts[:20]  # Top 20 object types
```

**Step 3: Check for common leak patterns**

```python
# 1. Unclosed connections
# BAD:
client = httpx.AsyncClient()
await client.get("http://example.com")
# client never closed!

# GOOD:
async with httpx.AsyncClient() as client:
    await client.get("http://example.com")

# 2. Growing caches
# BAD:
cache = {}  # Unbounded cache
cache[key] = value  # Grows forever

# GOOD:
from cachetools import TTLCache
cache = TTLCache(maxsize=1000, ttl=3600)

# 3. Event listener leaks
# BAD:
emitter.on("event", handler)  # Handler never removed

# GOOD:
emitter.on("event", handler)
# ... later:
emitter.off("event", handler)
```

### Resolution

**Scenario A: Unbounded cache**

```python
# Replace unbounded cache with TTL cache

# Before:
result_cache = {}  # Grows indefinitely

# After:
from cachetools import TTLCache

result_cache = TTLCache(
    maxsize=10000,      # Max 10k items
    ttl=3600            # 1 hour TTL
)

# Or use Redis with expiration
await redis_client.setex(key, 3600, value)
```

**Scenario B: Connection leaks**

```python
# Audit all HTTP clients and database connections

# Create reusable client
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.on_event("startup")
async def startup():
    app.state.http_client = httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(max_keepalive_connections=20)
    )

@app.on_event("shutdown")
async def shutdown():
    await app.state.http_client.aclose()

# Use shared client
async def call_arm(request):
    client = app.state.http_client
    response = await client.post("http://arm/execute", json=request)
    return response
```

**Scenario C: Large object retention**

```python
# Clear large objects after use

async def process_large_dataset(data):
    # Process data
    result = expensive_operation(data)

    # Explicitly clear references
    del data
    gc.collect()

    return result

# Use generators for large sequences
def iterate_tasks():
    # BAD: Load all tasks into memory
    tasks = Task.query.all()  # Could be millions
    for task in tasks:
        yield process(task)

    # GOOD: Use pagination
    page = 0
    while True:
        tasks = Task.query.limit(100).offset(page * 100).all()
        if not tasks:
            break
        for task in tasks:
            yield process(task)
        page += 1
```

**Scenario D: Circular references**

```python
# Break circular references

# Problematic:
class Task:
    def __init__(self):
        self.subtasks = []

class SubTask:
    def __init__(self, parent):
        self.parent = parent  # Circular reference
        parent.subtasks.append(self)

# Fix with weak references:
import weakref

class SubTask:
    def __init__(self, parent):
        self.parent = weakref.ref(parent)  # Weak reference
        parent.subtasks.append(self)

    def get_parent(self):
        return self.parent()  # De-reference
```

### Prevention

1. **Use context managers**: For all resources (files, connections, clients)
2. **Bounded caches**: Use TTLCache or LRU with size limits
3. **Weak references**: For parent-child relationships
4. **Regular profiling**: Run memory profiler in staging
5. **Resource limits**: Set memory limits to catch leaks early
6. **Monitoring**: Track memory usage over time

---

## Task Routing Failures

### Symptoms

- Tasks stuck in "pending" state
- No appropriate arm found for task
- Routing scores all zero
- Tasks timing out

### Diagnosis

**Step 1: Check task details**

```bash
# View task in database
docker compose exec postgres psql -U octollm -c "
SELECT task_id, goal, status, created_at, updated_at
FROM tasks
WHERE task_id = 'task-123';"

# Check task routing history
docker compose exec postgres psql -U octollm -c "
SELECT * FROM action_log
WHERE task_id = 'task-123'
ORDER BY timestamp DESC;"
```

**Step 2: Verify arm availability**

```bash
# Check arm health
for port in 8100 8101 8102 8103 8104 8105; do
  echo -n "Port $port: "
  curl -sf http://localhost:$port/health && echo "✓" || echo "✗"
done

# Check arm capabilities
curl http://localhost:8100/capabilities | jq
```

**Step 3: Check orchestrator routing logic**

```bash
# Enable debug logging
# In .env:
LOG_LEVEL=debug

docker compose restart orchestrator

# View routing decisions
docker compose logs -f orchestrator | grep -i "routing"
```

**Step 4: Test routing manually**

```python
# In orchestrator container
docker compose exec orchestrator python

from app.services.router import ArmRouter
from app.models.task import TaskContract

router = ArmRouter()
task = TaskContract(
    goal="Write a Python function",
    constraints=[],
    priority="medium"
)

scores = await router.score_arms(task)
print(scores)
```

### Resolution

**Scenario A: All arms down**

```bash
# Restart arms
docker compose restart planner-arm executor-arm coder-arm judge-arm guardian-arm retriever-arm

# Kubernetes
kubectl rollout restart deployment -l app-type=arm -n octollm
```

**Scenario B: Routing scoring issues**

```python
# Fix routing algorithm in orchestrator/app/services/router.py

async def score_arms(self, task: TaskContract) -> Dict[str, float]:
    """Score arms based on task requirements"""
    scores = {}

    for arm_name, arm_capability in self.registered_arms.items():
        score = 0.0

        # Check keyword matching
        task_keywords = extract_keywords(task.goal.lower())
        arm_keywords = arm_capability.keywords

        keyword_matches = len(set(task_keywords) & set(arm_keywords))
        score += keyword_matches * 10

        # Check domain match
        if arm_capability.domain in task.goal.lower():
            score += 50

        # Penalize if arm is unhealthy
        if not await self.is_arm_healthy(arm_name):
            score = 0

        scores[arm_name] = score

    # If no scores, default to planner
    if all(s == 0 for s in scores.values()):
        scores["planner"] = 100

    return scores
```

**Scenario C: Capabilities not registered**

```python
# Ensure arms register capabilities on startup
# In each arm's app/main.py

@app.on_event("startup")
async def register_with_orchestrator():
    """Register arm capabilities with orchestrator"""
    capability = ArmCapability(
        name="planner-arm",
        domain="planning",
        keywords=["plan", "decompose", "break down", "steps"],
        url=f"http://{os.getenv('HOSTNAME')}:8100"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://orchestrator:8000/api/v1/arms/register",
            json=capability.dict()
        )

        if response.status_code != 200:
            logger.error("Failed to register with orchestrator", error=response.text)
        else:
            logger.info("Successfully registered with orchestrator")
```

**Scenario D: Task constraints too strict**

```python
# Relax constraints if no match found
async def route_task(self, task: TaskContract) -> str:
    """Route task to best arm"""
    scores = await self.score_arms(task)

    max_score_arm = max(scores, key=scores.get)
    max_score = scores[max_score_arm]

    # If no good match, try relaxing constraints
    if max_score < 10:
        logger.warning(
            "No good arm match, relaxing constraints",
            task_id=task.task_id,
            original_goal=task.goal
        )

        # Remove optional constraints
        task.constraints = [c for c in task.constraints if "must" in c.lower()]

        # Re-score
        scores = await self.score_arms(task)
        max_score_arm = max(scores, key=scores.get)

    return max_score_arm
```

### Prevention

1. **Health checks**: Ensure all arms have health endpoints
2. **Registration**: Auto-register arms on startup
3. **Fallback routing**: Always have a default arm (planner)
4. **Monitoring**: Track routing failures
5. **Testing**: Test routing logic with various task types

---

## LLM API Failures

### Symptoms

- 429 Too Many Requests errors
- 503 Service Unavailable from LLM provider
- Authentication errors
- Timeout errors
- Alert: `HighLLMAPIErrorRate`

### Diagnosis

**Step 1: Check LLM API metrics**

```bash
# Query Prometheus
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(llm_api_calls_total{status="error"}[5m])'

# Check error logs
docker compose logs orchestrator | grep -i "llm.*error"
```

**Step 2: Verify API key**

```bash
# Test API key manually
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check key in environment
docker compose exec orchestrator env | grep OPENAI_API_KEY
```

**Step 3: Check rate limiting**

```bash
# View rate limit headers from last request
docker compose logs orchestrator | grep -i "rate.*limit"

# Check current request rate
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(llm_api_calls_total[1m]) * 60'
```

### Resolution

**Scenario A: Rate limiting (429 errors)**

```python
# Implement exponential backoff with jitter
import asyncio
import random
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
async def call_llm_api(prompt: str) -> str:
    """Call LLM API with exponential backoff"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60.0
        )

        if response.status_code == 429:
            # Add jitter to prevent thundering herd
            await asyncio.sleep(random.uniform(0, 2))
            response.raise_for_status()

        return response.json()
```

```python
# Implement request queuing
from asyncio import Queue, Semaphore

class LLMClient:
    def __init__(self, max_concurrent=5, max_per_minute=50):
        self.semaphore = Semaphore(max_concurrent)
        self.rate_limiter = TokenBucket(max_per_minute, 60)

    async def generate(self, prompt: str) -> str:
        async with self.semaphore:  # Limit concurrent requests
            await self.rate_limiter.acquire()  # Rate limit
            return await self._call_api(prompt)
```

**Scenario B: Service unavailable (503 errors)**

```python
# Implement circuit breaker pattern
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_llm_with_circuit_breaker(prompt: str) -> str:
    """Call LLM API with circuit breaker"""
    try:
        return await call_llm_api(prompt)
    except Exception as e:
        logger.error("LLM API call failed", error=str(e))
        raise

# Circuit opens after 5 failures, waits 60s before retry
```

```python
# Implement fallback to alternative provider
async def generate_with_fallback(prompt: str) -> str:
    """Try primary provider, fallback to secondary"""
    try:
        return await openai_client.generate(prompt)
    except Exception as e:
        logger.warning(
            "OpenAI failed, falling back to Anthropic",
            error=str(e)
        )
        return await anthropic_client.generate(prompt)
```

**Scenario C: Timeout errors**

```python
# Increase timeout for long-running requests
client = httpx.AsyncClient(
    timeout=httpx.Timeout(
        connect=5.0,
        read=120.0,  # 2 minutes for completion
        write=5.0,
        pool=5.0
    )
)

# Stream responses for long generations
async def stream_llm_response(prompt: str):
    """Stream LLM response chunks"""
    async with client.stream(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }
    ) as response:
        async for chunk in response.aiter_bytes():
            yield chunk
```

**Scenario D: Authentication errors**

```bash
# Rotate API key
# Update .env file
OPENAI_API_KEY=sk-new-key-here

# Reload configuration
docker compose up -d orchestrator

# Kubernetes: Update secret
kubectl create secret generic octollm-secrets \
  --from-literal=OPENAI_API_KEY=sk-new-key \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment orchestrator -n octollm
```

### Prevention

1. **Rate limiting**: Implement token bucket or leaky bucket
2. **Circuit breakers**: Prevent cascading failures
3. **Retries**: Use exponential backoff with jitter
4. **Fallback providers**: Have secondary LLM provider
5. **Caching**: Cache LLM responses when possible
6. **Monitoring**: Track API error rates and costs

---

## Cache Performance Issues

### Symptoms

- Low cache hit rate (<50%)
- Redis memory full
- Slow cache lookups
- Alert: `CacheMissRate`

### Diagnosis

**Step 1: Check cache hit rate**

```bash
# Query Prometheus
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))'
```

**Step 2: Check Redis stats**

```bash
# Redis info
docker compose exec redis redis-cli INFO stats

# Check memory usage
docker compose exec redis redis-cli INFO memory

# Check key count
docker compose exec redis redis-cli DBSIZE

# Sample keys
docker compose exec redis redis-cli --scan --pattern "*" | head -20
```

**Step 3: Analyze cache usage patterns**

```bash
# Monitor cache commands
docker compose exec redis redis-cli MONITOR

# Check slow queries
docker compose exec redis redis-cli SLOWLOG GET 10
```

### Resolution

**Scenario A: Cache eviction policy issues**

```bash
# Check current policy
docker compose exec redis redis-cli CONFIG GET maxmemory-policy

# Set appropriate policy for use case
docker compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Options:
# - allkeys-lru: Evict any key, LRU
# - volatile-lru: Evict keys with TTL, LRU
# - allkeys-lfu: Evict any key, LFU (least frequently used)
# - volatile-ttl: Evict keys with shortest TTL
```

**Scenario B: Inefficient cache keys**

```python
# Bad: Too specific keys (low hit rate)
cache_key = f"task:{task_id}:{user_id}:{timestamp}"

# Good: Normalized keys
cache_key = f"task:{task_id}"

# Bad: Large values cached
await redis.set("large_dataset", json.dumps(huge_object))  # MB of data

# Good: Cache references or summaries
await redis.set(f"dataset:{id}:summary", summary)  # Small summary
# Store full data in database
```

**Scenario C: Missing cache warming**

```python
# Implement cache warming on startup
@app.on_event("startup")
async def warm_cache():
    """Pre-populate cache with frequently accessed data"""
    logger.info("Warming cache...")

    # Load arm capabilities
    arms = await db.query("SELECT * FROM arms WHERE enabled = true")
    for arm in arms:
        await redis.setex(
            f"arm:capability:{arm.name}",
            3600,
            json.dumps(arm.capabilities)
        )

    # Load common entity relationships
    entities = await db.query(
        "SELECT * FROM entities WHERE access_count > 100"
    )
    for entity in entities:
        await redis.setex(
            f"entity:{entity.id}",
            3600,
            json.dumps(entity.dict())
        )

    logger.info(f"Cache warmed with {len(arms) + len(entities)} entries")
```

**Scenario D: Cache stampede**

```python
# Prevent cache stampede with locking
import asyncio
from contextlib import asynccontextmanager

class CacheWithLock:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.locks = {}

    @asynccontextmanager
    async def lock(self, key: str):
        """Acquire lock for cache key"""
        lock_key = f"lock:{key}"
        lock_id = str(uuid.uuid4())

        # Try to acquire lock
        while not await self.redis.set(lock_key, lock_id, nx=True, ex=10):
            await asyncio.sleep(0.1)  # Wait for lock

        try:
            yield
        finally:
            # Release lock
            if await self.redis.get(lock_key) == lock_id:
                await self.redis.delete(lock_key)

    async def get_or_compute(self, key: str, compute_fn):
        """Get from cache or compute with lock"""
        # Try cache first
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)

        # Cache miss - acquire lock to prevent stampede
        async with self.lock(key):
            # Double-check cache (another thread may have computed)
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)

            # Compute value
            value = await compute_fn()

            # Cache result
            await self.redis.setex(key, 3600, json.dumps(value))

            return value
```

### Prevention

1. **Appropriate TTLs**: Set expiration based on data change frequency
2. **Cache warming**: Pre-populate cache on startup
3. **Consistent keys**: Use normalized cache keys
4. **Monitoring**: Track hit rate and memory usage
5. **Eviction policy**: Choose policy matching access patterns

---

## Resource Exhaustion

### Symptoms

- CPU at 100%
- Memory at limit
- Disk space full
- Alert: `HighCPUUsage`, `HighMemoryUsage`, `DiskSpaceLow`

### Diagnosis

```bash
# Check resource usage
docker stats

# Kubernetes
kubectl top pods -n octollm
kubectl top nodes

# Check disk usage
df -h
docker system df

# Identify resource-heavy processes
docker compose exec orchestrator top
```

### Resolution

**CPU exhaustion:**

```bash
# Identify CPU-heavy services
docker stats --no-stream | sort -k3 -hr

# Scale horizontally
kubectl scale deployment orchestrator --replicas=3 -n octollm

# Optimize code (add CPU profiling)
python -m cProfile app/main.py
```

**Memory exhaustion:**

```bash
# Clear caches
docker compose exec redis redis-cli FLUSHDB

# Restart services
docker compose restart

# Increase limits
kubectl edit deployment orchestrator -n octollm
```

**Disk exhaustion:**

```bash
# Clean up Docker
docker system prune -a --volumes

# Rotate logs
docker compose logs --no-log-prefix > /dev/null

# Clean old backups
find /backups -mtime +30 -delete
```

### Prevention

1. **Resource limits**: Set CPU/memory limits
2. **Auto-scaling**: Configure HPA in Kubernetes
3. **Monitoring**: Alert on resource usage
4. **Log rotation**: Limit log file sizes
5. **Regular cleanup**: Schedule cleanup jobs

---

## Security Violations

### Symptoms

- Alert: `SecurityViolationDetected`
- PII detected in logs
- Suspicious commands blocked
- Unauthorized access attempts

### Diagnosis

```bash
# Check security logs
docker compose logs guardian-arm | grep -i "violation"

# Query security metrics
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=security_violations_total'
```

### Resolution

```bash
# Review and update security rules
# In guardian-arm configuration

# Block command execution
docker compose exec guardian-arm cat /app/config/blocked_commands.txt

# Review PII detection patterns
docker compose logs guardian-arm | grep "PII detected"

# Update firewall rules if needed
```

### Prevention

1. **Input validation**: Validate all user inputs
2. **PII detection**: Scan all inputs/outputs
3. **Audit logging**: Log all security events
4. **Regular audits**: Review security logs
5. **Security training**: Educate team on security

---

## Data Corruption

### Symptoms

- Invalid data in database
- Foreign key violations
- Inconsistent entity relationships
- Application errors due to malformed data

### Diagnosis

```sql
-- Check for orphaned records
SELECT * FROM relationships r
LEFT JOIN entities e1 ON r.from_entity_id = e1.entity_id
WHERE e1.entity_id IS NULL;

-- Check for invalid JSON
SELECT * FROM entities
WHERE jsonb_typeof(properties) != 'object';

-- Check constraints
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'tasks'::regclass;
```

### Resolution

```sql
-- Fix orphaned relationships
DELETE FROM relationships
WHERE from_entity_id NOT IN (SELECT entity_id FROM entities)
   OR to_entity_id NOT IN (SELECT entity_id FROM entities);

-- Fix invalid JSON
UPDATE entities
SET properties = '{}'::jsonb
WHERE jsonb_typeof(properties) != 'object';

-- Restore from backup if needed
docker compose exec -T postgres psql -U octollm octollm < backup.sql
```

### Prevention

1. **Foreign keys**: Use database constraints
2. **Validation**: Validate data before insert
3. **Transactions**: Use atomic operations
4. **Backups**: Regular automated backups
5. **Testing**: Test data integrity

---

## Quick Reference

### Common Commands

```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker compose logs -f [service]

# Restart service
docker compose restart [service]

# Check resource usage
docker stats

# Access database
docker compose exec postgres psql -U octollm

# Access Redis
docker compose exec redis redis-cli

# Check metrics
curl http://localhost:9090/metrics
```

### Emergency Procedures

**Complete system restart:**

```bash
# Stop all services
docker compose down

# Clear caches (optional)
docker compose down -v

# Start services
docker compose up -d

# Verify health
./scripts/healthcheck.sh
```

**Rollback deployment (Kubernetes):**

```bash
# View rollout history
kubectl rollout history deployment orchestrator -n octollm

# Rollback to previous version
kubectl rollout undo deployment orchestrator -n octollm

# Rollback to specific revision
kubectl rollout undo deployment orchestrator --to-revision=3 -n octollm
```

---

## Escalation Procedures

### Level 1: On-call Engineer

- Service unavailable
- High latency
- Database connection issues

**Actions**:
1. Follow relevant playbook
2. Restart affected services
3. Escalate if unresolved in 15 minutes

### Level 2: Senior Engineer

- Memory leaks
- Resource exhaustion
- Data corruption

**Actions**:
1. Deep diagnosis with profiling
2. Code fixes if needed
3. Escalate to engineering lead if architectural issue

### Level 3: Engineering Lead

- Security violations
- Architectural issues
- Multi-service failures

**Actions**:
1. Coordinate team response
2. Make architectural decisions
3. Communicate with stakeholders

---

## See Also

- [Monitoring and Alerting](monitoring-alerting.md) - Set up observability
- [Performance Tuning](performance-tuning.md) - Optimize performance
- [Kubernetes Deployment](kubernetes-deployment.md) - Production deployment
- [Docker Compose Setup](docker-compose-setup.md) - Local setup
