# Performance Tuning Guide

**Estimated Time**: 2-4 hours
**Difficulty**: Advanced
**Prerequisites**: OctoLLM running, access to metrics, profiling tools

## Overview

This guide covers systematic performance optimization for OctoLLM across all layers:
- Database query optimization
- Application-level tuning
- Resource allocation and scaling
- Network and I/O optimization
- LLM API optimization

## Table of Contents

1. [Performance Baseline](#performance-baseline)
2. [Database Optimization](#database-optimization)
3. [Application Tuning](#application-tuning)
4. [Cache Optimization](#cache-optimization)
5. [LLM API Optimization](#llm-api-optimization)
6. [Resource Allocation](#resource-allocation)
7. [Network Optimization](#network-optimization)
8. [Load Testing](#load-testing)
9. [Profiling](#profiling)
10. [Best Practices](#best-practices)

---

## Performance Baseline

### Target Performance Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| **API Latency (P95)** | < 500ms | < 1s | > 2s |
| **API Latency (P99)** | < 1s | < 2s | > 5s |
| **Task Throughput** | > 100/min | > 50/min | < 25/min |
| **Database Query Time** | < 10ms | < 50ms | > 100ms |
| **Cache Hit Rate** | > 80% | > 60% | < 40% |
| **CPU Usage** | < 60% | < 80% | > 90% |
| **Memory Usage** | < 70% | < 85% | > 95% |
| **Error Rate** | < 0.1% | < 1% | > 5% |

### Establish Baseline

```bash
# Run baseline load test
docker run --rm -it \
  -v $(pwd)/load-tests:/tests \
  grafana/k6 run /tests/baseline.js

# Collect baseline metrics
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'
```

### K6 Load Test Script

```javascript
// load-tests/baseline.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 10 },   // Stay at 10 users
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],  // 95% of requests < 1s
    http_req_failed: ['rate<0.01'],     // Error rate < 1%
  },
};

const BASE_URL = 'http://localhost:8000';

export default function() {
  // Test task creation
  let payload = JSON.stringify({
    goal: 'Write a Python function to calculate fibonacci',
    constraints: ['Include docstring', 'Add type hints'],
    priority: 'medium'
  });

  let params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  let res = http.post(`${BASE_URL}/api/v1/tasks`, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 1s': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}
```

---

## Database Optimization

### Index Optimization

```sql
-- Analyze current index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;

-- Find missing indexes
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
ORDER BY abs(correlation) DESC;

-- Create recommended indexes
CREATE INDEX CONCURRENTLY idx_tasks_status_created
ON tasks(status, created_at DESC);

CREATE INDEX CONCURRENTLY idx_tasks_priority
ON tasks(priority)
WHERE status = 'pending';

CREATE INDEX CONCURRENTLY idx_entities_type_name
ON entities(entity_type, name);

CREATE INDEX CONCURRENTLY idx_relationships_from_type
ON relationships(from_entity_id, relationship_type);

-- GIN index for full-text search
CREATE INDEX CONCURRENTLY idx_entities_name_gin
ON entities USING GIN(to_tsvector('english', name));

-- BRIN index for timestamp columns (efficient for large tables)
CREATE INDEX CONCURRENTLY idx_action_log_timestamp_brin
ON action_log USING BRIN(timestamp);
```

### Query Optimization

```sql
-- Identify slow queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Analyze specific query
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tasks
WHERE status = 'pending'
ORDER BY priority DESC, created_at ASC
LIMIT 10;
```

**Common optimizations:**

```sql
-- Bad: SELECT *
SELECT * FROM entities WHERE entity_type = 'person';

-- Good: Select only needed columns
SELECT entity_id, name, properties
FROM entities
WHERE entity_type = 'person';

-- Bad: OR conditions
SELECT * FROM tasks
WHERE priority = 'high' OR priority = 'critical';

-- Good: IN clause
SELECT * FROM tasks
WHERE priority IN ('high', 'critical');

-- Bad: Function in WHERE clause
SELECT * FROM tasks
WHERE DATE(created_at) = '2024-01-01';

-- Good: Range comparison
SELECT * FROM tasks
WHERE created_at >= '2024-01-01'
  AND created_at < '2024-01-02';

-- Bad: LIKE with leading wildcard
SELECT * FROM entities
WHERE name LIKE '%Smith%';

-- Good: GIN index with full-text search
SELECT * FROM entities
WHERE to_tsvector('english', name) @@ to_tsquery('Smith');
```

### Connection Pooling

```python
# orchestrator/app/database/pool.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

# Development: Simple pool
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

# Production: Optimized pool
engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,              # Base connections
    max_overflow=40,            # Additional connections under load
    pool_timeout=30,            # Wait 30s for connection
    pool_recycle=3600,          # Recycle connections after 1 hour
    pool_pre_ping=True,         # Test connection before use
    echo=False,
    connect_args={
        "server_settings": {
            "application_name": "octollm-orchestrator",
            "jit": "on",        # Enable JIT compilation
        },
        "timeout": 10,
        "command_timeout": 60,
    }
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

### PostgreSQL Configuration

```ini
# postgresql.conf optimizations

# Memory
shared_buffers = 4GB                    # 25% of system RAM
effective_cache_size = 12GB             # 75% of system RAM
work_mem = 128MB                        # Per operation
maintenance_work_mem = 1GB              # For VACUUM, CREATE INDEX

# Checkpoints
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Query Planning
random_page_cost = 1.1                  # Lower for SSD
effective_io_concurrency = 200          # Higher for SSD

# Connections
max_connections = 200

# Logging
log_min_duration_statement = 100        # Log queries > 100ms
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d '
log_checkpoints = on
log_lock_waits = on

# Autovacuum
autovacuum_max_workers = 4
autovacuum_naptime = 15s
```

---

## Application Tuning

### Async Optimization

```python
# Bad: Sequential operations
async def process_task_sequential(task_id: str):
    task = await db.get_task(task_id)
    capabilities = await db.get_arm_capabilities()
    context = await memory.get_context(task_id)

    # Total time: sum of all operations

# Good: Concurrent operations
async def process_task_concurrent(task_id: str):
    task, capabilities, context = await asyncio.gather(
        db.get_task(task_id),
        db.get_arm_capabilities(),
        memory.get_context(task_id)
    )

    # Total time: max of all operations
```

### Batching Requests

```python
# Bad: Individual requests in loop
async def get_entities(entity_ids: List[str]):
    entities = []
    for entity_id in entity_ids:
        entity = await db.get_entity(entity_id)
        entities.append(entity)
    return entities

# Good: Batch request
async def get_entities(entity_ids: List[str]):
    query = select(Entity).where(Entity.entity_id.in_(entity_ids))
    result = await db.execute(query)
    return result.scalars().all()
```

### N+1 Query Prevention

```python
# Bad: N+1 queries
async def get_tasks_with_arms():
    tasks = await db.query(Task).all()
    for task in tasks:
        task.arm = await db.query(Arm).filter(
            Arm.arm_id == task.arm_id
        ).first()
    return tasks

# Good: Join or eager loading
async def get_tasks_with_arms():
    tasks = await db.query(Task).options(
        selectinload(Task.arm)
    ).all()
    return tasks

# Or with raw SQL join
async def get_tasks_with_arms():
    query = """
        SELECT t.*, a.name as arm_name, a.url as arm_url
        FROM tasks t
        LEFT JOIN arms a ON t.arm_id = a.arm_id
        WHERE t.status = 'completed'
    """
    result = await db.execute(query)
    return result.fetchall()
```

### Response Compression

```python
# orchestrator/app/main.py
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

# Enable gzip compression for responses > 1KB
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,
    compresslevel=6  # 1-9, higher = more compression, slower
)
```

### Request Deduplication

```python
# Prevent duplicate requests from racing
from asyncio import Lock
from typing import Dict, Any

class RequestDeduplicator:
    def __init__(self):
        self.locks: Dict[str, Lock] = {}
        self.cache: Dict[str, Any] = {}

    async def get_or_compute(self, key: str, compute_fn):
        """Get cached result or compute (only once for concurrent requests)"""

        # Fast path: check cache
        if key in self.cache:
            return self.cache[key]

        # Get or create lock for this key
        if key not in self.locks:
            self.locks[key] = Lock()

        lock = self.locks[key]

        async with lock:
            # Double-check cache (another request may have computed)
            if key in self.cache:
                return self.cache[key]

            # Compute value
            result = await compute_fn()

            # Cache result
            self.cache[key] = result

            return result
```

---

## Cache Optimization

### Multi-Level Caching

```python
# Implement L1 (in-memory) and L2 (Redis) cache
from cachetools import TTLCache
import json

class MultiLevelCache:
    def __init__(self, redis_client):
        self.l1_cache = TTLCache(maxsize=1000, ttl=60)  # 1 minute
        self.l2_cache = redis_client  # Redis
        self.l1_hits = 0
        self.l2_hits = 0
        self.misses = 0

    async def get(self, key: str):
        """Get from L1, then L2, then return None"""

        # Try L1 cache (in-memory)
        if key in self.l1_cache:
            self.l1_hits += 1
            return self.l1_cache[key]

        # Try L2 cache (Redis)
        cached = await self.l2_cache.get(key)
        if cached:
            self.l2_hits += 1
            value = json.loads(cached)
            # Promote to L1
            self.l1_cache[key] = value
            return value

        # Cache miss
        self.misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in both L1 and L2 cache"""
        self.l1_cache[key] = value
        await self.l2_cache.setex(key, ttl, json.dumps(value))

    def get_stats(self):
        """Get cache statistics"""
        total = self.l1_hits + self.l2_hits + self.misses
        return {
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "misses": self.misses,
            "hit_rate": (self.l1_hits + self.l2_hits) / total if total > 0 else 0
        }
```

### Cache Warming

```python
# Warm cache on startup with frequently accessed data
@app.on_event("startup")
async def warm_cache():
    """Pre-populate cache with hot data"""

    # Load arm capabilities (accessed on every request)
    arms = await db.query(Arm).filter(Arm.enabled == True).all()
    for arm in arms:
        await cache.set(
            f"arm:capability:{arm.name}",
            arm.capabilities,
            ttl=3600
        )

    # Load frequently accessed entities
    query = """
        SELECT entity_id, name, entity_type, properties
        FROM entities
        WHERE access_count > 100
        ORDER BY access_count DESC
        LIMIT 1000
    """
    entities = await db.execute(query)

    for entity in entities:
        await cache.set(
            f"entity:{entity.entity_id}",
            entity,
            ttl=1800
        )

    logger.info(f"Cache warmed with {len(arms)} arms and {len(entities)} entities")
```

### Cache Invalidation

```python
# Implement cache invalidation on updates
async def update_entity(entity_id: str, updates: dict):
    """Update entity and invalidate cache"""

    # Update database
    await db.query(Entity).filter(
        Entity.entity_id == entity_id
    ).update(updates)

    await db.commit()

    # Invalidate cache
    await cache.delete(f"entity:{entity_id}")

    # Invalidate related caches
    relationships = await db.query(Relationship).filter(
        (Relationship.from_entity_id == entity_id) |
        (Relationship.to_entity_id == entity_id)
    ).all()

    for rel in relationships:
        await cache.delete(f"relationship:{rel.relationship_id}")
```

---

## LLM API Optimization

### Request Batching

```python
# Batch multiple LLM requests
class LLMBatcher:
    def __init__(self, max_batch_size=5, max_wait_ms=100):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.queue = []
        self.batch_task = None

    async def add_request(self, prompt: str) -> str:
        """Add request to batch and wait for response"""

        future = asyncio.Future()
        self.queue.append((prompt, future))

        # Start batch processor if not running
        if self.batch_task is None:
            self.batch_task = asyncio.create_task(self._process_batch())

        return await future

    async def _process_batch(self):
        """Process batch after delay or when full"""

        # Wait for batch to fill or timeout
        await asyncio.sleep(self.max_wait_ms / 1000)

        if not self.queue:
            self.batch_task = None
            return

        # Take batch
        batch = self.queue[:self.max_batch_size]
        self.queue = self.queue[self.max_batch_size:]

        # Combine prompts
        combined = "\n---\n".join([p for p, _ in batch])

        # Single API call
        response = await llm_client.generate(combined)

        # Split and resolve futures
        responses = response.split("\n---\n")
        for (_, future), resp in zip(batch, responses):
            future.set_result(resp)

        # Process remaining
        if self.queue:
            self.batch_task = asyncio.create_task(self._process_batch())
        else:
            self.batch_task = None
```

### Response Streaming

```python
# Stream LLM responses for faster TTFB
async def stream_llm_response(prompt: str):
    """Stream LLM response chunks"""

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            },
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=60.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = json.loads(line[6:])
                    if chunk["choices"][0].get("delta", {}).get("content"):
                        yield chunk["choices"][0]["delta"]["content"]
```

### Model Selection

```python
# Use appropriate model for task complexity
def select_model(task: Task) -> str:
    """Select most cost-effective model for task"""

    # Simple tasks: Use cheaper, faster model
    if task.complexity == "simple":
        return "gpt-3.5-turbo"

    # Complex reasoning: Use advanced model
    elif task.complexity == "complex":
        return "gpt-4"

    # Code generation: Use specialized model
    elif task.domain == "coding":
        return "gpt-4"  # or code-specific model

    # Default
    return "gpt-3.5-turbo"
```

---

## Resource Allocation

### CPU Allocation

```yaml
# Kubernetes: Set CPU requests and limits
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
spec:
  template:
    spec:
      containers:
      - name: orchestrator
        resources:
          requests:
            cpu: 1000m      # 1 CPU guaranteed
            memory: 2Gi
          limits:
            cpu: 2000m      # Max 2 CPUs
            memory: 4Gi
```

```yaml
# Docker Compose: Set CPU limits
services:
  orchestrator:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Memory Allocation

```python
# Tune Python memory settings
import gc

# Disable automatic GC, run manually
gc.disable()

# Run GC periodically
async def periodic_gc():
    while True:
        await asyncio.sleep(60)  # Every minute
        gc.collect()

asyncio.create_task(periodic_gc())

# Or use generational GC tuning
gc.set_threshold(700, 10, 5)  # (gen0, gen1, gen2)
```

### Worker Configuration

```python
# orchestrator/app/config.py

# Development
WORKER_COUNT = 2
WORKER_THREADS = 2

# Production
import multiprocessing

CPU_COUNT = multiprocessing.cpu_count()
WORKER_COUNT = (CPU_COUNT * 2) + 1  # Rule of thumb
WORKER_THREADS = 4
```

```bash
# Start with optimal workers
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 9 \
  --loop uvloop \
  --access-log \
  --use-colors
```

---

## Network Optimization

### HTTP/2 and Keep-Alive

```python
# Use HTTP/2 and connection pooling
import httpx

client = httpx.AsyncClient(
    http2=True,  # Enable HTTP/2
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30.0
    ),
    timeout=httpx.Timeout(
        connect=5.0,
        read=30.0,
        write=5.0,
        pool=5.0
    )
)
```

### Request Compression

```python
# Enable request compression
async def post_with_compression(url: str, data: dict):
    """POST request with gzip compression"""

    json_data = json.dumps(data).encode('utf-8')
    compressed = gzip.compress(json_data)

    async with client.stream(
        "POST",
        url,
        content=compressed,
        headers={
            "Content-Encoding": "gzip",
            "Content-Type": "application/json"
        }
    ) as response:
        return await response.json()
```

### DNS Caching

```python
# Configure DNS caching
import aiodns

resolver = aiodns.DNSResolver(
    nameservers=["8.8.8.8", "8.8.4.4"],
    timeout=5.0,
    tries=2
)

# Cache DNS lookups
dns_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes
```

---

## Load Testing

### Progressive Load Testing

```javascript
// load-tests/progressive.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 10 },
    { duration: '1m', target: 25 },
    { duration: '1m', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '1m', target: 200 },
    { duration: '5m', target: 200 },  // Sustain
    { duration: '1m', target: 0 },
  ],
};

export default function() {
  let res = http.get('http://localhost:8000/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'latency < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

### Stress Testing

```javascript
// load-tests/stress.js
export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },
    { duration: '5m', target: 300 },
    { duration: '10m', target: 0 },
  ],
};
```

---

## Profiling

### Python Profiling

```python
# CPU profiling with cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
await process_task(task_id)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

```python
# Memory profiling
from memory_profiler import profile

@profile
async def memory_intensive_function():
    # Function code
    pass
```

### Request Tracing

```python
# Add timing middleware
from time import time

@app.middleware("http")
async def add_timing_header(request, call_next):
    start_time = time()

    response = await call_next(request)

    process_time = time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response
```

---

## Best Practices

### 1. Database

- ✅ Use indexes on frequently queried columns
- ✅ Avoid SELECT *, specify needed columns
- ✅ Use connection pooling
- ✅ Batch operations when possible
- ✅ Use EXPLAIN ANALYZE for slow queries
- ❌ Don't use LIKE with leading wildcard
- ❌ Don't query in loops (N+1 problem)

### 2. Application

- ✅ Use async/await for I/O operations
- ✅ Batch LLM API requests
- ✅ Implement multi-level caching
- ✅ Use connection pooling for HTTP clients
- ✅ Stream responses when possible
- ❌ Don't block event loop
- ❌ Don't create new clients per request

### 3. Caching

- ✅ Cache frequently accessed data
- ✅ Set appropriate TTLs
- ✅ Warm cache on startup
- ✅ Invalidate cache on updates
- ❌ Don't cache everything
- ❌ Don't use unbounded caches

### 4. Monitoring

- ✅ Track all key metrics
- ✅ Set up performance alerts
- ✅ Profile regularly
- ✅ Load test before deployment
- ✅ Monitor resource usage

---

## Performance Checklist

Before going to production:

### Database
- [ ] Indexes created for all frequently queried columns
- [ ] Query performance analyzed with EXPLAIN
- [ ] Connection pool configured
- [ ] PostgreSQL configuration tuned
- [ ] Autovacuum configured

### Application
- [ ] Async operations used throughout
- [ ] N+1 queries eliminated
- [ ] Response compression enabled
- [ ] Request batching implemented
- [ ] Error handling doesn't block

### Caching
- [ ] Multi-level caching implemented
- [ ] Cache hit rate > 70%
- [ ] TTLs set appropriately
- [ ] Cache invalidation working
- [ ] Cache warming on startup

### Resources
- [ ] CPU/memory limits set
- [ ] Worker count optimized
- [ ] Connection pools sized correctly
- [ ] Horizontal scaling configured

### Testing
- [ ] Load testing completed
- [ ] Stress testing completed
- [ ] Performance baselines established
- [ ] Profiling identifies no bottlenecks

---

## Next Steps

After optimization:

1. **Monitor results** - Track metrics to validate improvements
2. **Iterate** - Continuously profile and optimize
3. **Scale** - Add resources as needed
4. **Document** - Record optimization decisions

## See Also

- [Monitoring and Alerting](monitoring-alerting.md) - Track performance
- [Troubleshooting Playbooks](troubleshooting-playbooks.md) - Diagnose issues
- [Kubernetes Deployment](kubernetes-deployment.md) - Production deployment
- [Docker Compose Setup](docker-compose-setup.md) - Local development
