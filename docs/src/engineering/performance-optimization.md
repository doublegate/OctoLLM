# Performance Optimization Best Practices

**Last Updated**: 2025-11-10
**Status**: Production Standard
**Applies To**: All OctoLLM components

## Overview

This document defines performance optimization best practices for developing OctoLLM components. These guidelines help ensure the system meets production performance targets while maintaining code quality and maintainability.

## Performance Targets

### Latency Targets

| Component | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Reflex Layer | <5ms | <10ms | <20ms |
| Orchestrator (simple) | <100ms | <500ms | <1s |
| Orchestrator (complex) | <500ms | <2s | <5s |
| Arms (average) | <1s | <3s | <10s |
| End-to-end (simple) | <1s | <3s | <10s |
| End-to-end (complex) | <5s | <15s | <30s |

### Throughput Targets

| Component | Target | Limit |
|-----------|--------|-------|
| Reflex Layer | >10,000 req/s | CPU-bound |
| Orchestrator | >100 tasks/min | Database-bound |
| Arms (combined) | >500 tasks/min | LLM API-bound |

### Resource Targets

| Resource | Development | Production |
|----------|-------------|------------|
| Memory (Orchestrator) | <2GB | <4GB |
| Memory (Arm) | <1GB | <2GB |
| Memory (Reflex) | <100MB | <200MB |
| CPU (Orchestrator) | <2 cores | <4 cores |
| CPU (Arm) | <1 core | <2 cores |
| CPU (Reflex) | <0.5 cores | <1 core |

---

## Table of Contents

- [Python Performance](#python-performance)
- [Rust Performance](#rust-performance)
- [Database Optimization](#database-optimization)
- [Caching Strategies](#caching-strategies)
- [Async Programming](#async-programming)
- [Network Optimization](#network-optimization)
- [Memory Management](#memory-management)
- [Profiling Tools](#profiling-tools)

---

## Python Performance

### Async Operations

**Good - Concurrent Execution**:
```python
import asyncio

# Execute multiple operations concurrently
async def fetch_task_context(task_id: str):
    # Run all queries in parallel
    task, capabilities, memory = await asyncio.gather(
        db.get_task(task_id),
        db.get_arm_capabilities(),
        memory_client.get_context(task_id)
    )
    return task, capabilities, memory

# Process multiple tasks concurrently
async def process_batch(tasks: List[TaskContract]):
    results = await asyncio.gather(
        *[process_task(task) for task in tasks],
        return_exceptions=True
    )
    return results
```

**Bad - Sequential Execution**:
```python
# Sequential - wastes time waiting
async def fetch_task_context(task_id: str):
    task = await db.get_task(task_id)
    capabilities = await db.get_arm_capabilities()
    memory = await memory_client.get_context(task_id)
    return task, capabilities, memory
```

### List Comprehensions vs Loops

**Good - List Comprehensions**:
```python
# Fast - single pass, optimized
high_priority = [t for t in tasks if t.priority >= 8]

# Even better - generator for large datasets
high_priority = (t for t in tasks if t.priority >= 8)
```

**Bad - Loops with Append**:
```python
# Slower - multiple reallocations
high_priority = []
for t in tasks:
    if t.priority >= 8:
        high_priority.append(t)
```

### String Operations

**Good - Join for Concatenation**:
```python
# Fast - single allocation
result = " ".join(words)

# For large datasets, use io.StringIO
from io import StringIO
buffer = StringIO()
for item in large_list:
    buffer.write(str(item))
result = buffer.getvalue()
```

**Bad - String Concatenation in Loop**:
```python
# Slow - creates new string each iteration
result = ""
for word in words:
    result += " " + word
```

### Set Operations

**Good - Set Lookups**:
```python
# O(1) lookup
allowed_arms = {"planner", "coder", "judge"}
if arm_name in allowed_arms:
    process(arm_name)

# Set operations for filtering
active_arms = set(active) & set(available)
```

**Bad - List Lookups**:
```python
# O(n) lookup
allowed_arms = ["planner", "coder", "judge"]
if arm_name in allowed_arms:  # Slow for large lists
    process(arm_name)
```

### Dictionary Operations

**Good - Get with Default**:
```python
# Efficient - single lookup
value = cache.get(key, default_value)

# For complex defaults, use setdefault
value = cache.setdefault(key, expensive_compute())

# Or defaultdict for many defaults
from collections import defaultdict
counts = defaultdict(int)
counts[key] += 1
```

**Bad - Check Then Access**:
```python
# Inefficient - double lookup
if key in cache:
    value = cache[key]
else:
    value = default_value
```

### Function Call Overhead

**Good - Inline Simple Operations**:
```python
# For performance-critical paths, inline simple operations
scores = [task.priority * 0.1 + len(task.description) * 0.001
          for task in tasks]
```

**Bad - Excessive Function Calls**:
```python
# Function call overhead for simple operations
def calculate_score(task):
    return task.priority * 0.1 + len(task.description) * 0.001

scores = [calculate_score(task) for task in tasks]
```

---

## Rust Performance

### Zero-Cost Abstractions

**Good - Iterator Chains**:
```rust
// Optimized to single pass by compiler
let result: Vec<_> = tasks
    .iter()
    .filter(|t| t.priority >= 8)
    .map(|t| t.id.clone())
    .collect();

// Avoid unnecessary allocations
let count = tasks
    .iter()
    .filter(|t| t.priority >= 8)
    .count();  // Don't collect if you just need count
```

**Avoid - Unnecessary Clones**:
```rust
// Bad - unnecessary clone
fn process_task(task: Task) -> String {
    // task is moved, requires clone at call site
}

// Good - borrow instead
fn process_task(task: &Task) -> String {
    // task is borrowed, no clone needed
}
```

### String Handling

**Good - String Building**:
```rust
// Efficient - pre-allocated capacity
let mut result = String::with_capacity(1000);
for item in items {
    result.push_str(&item);
}

// For known size
let result = format!("{}-{}-{}", part1, part2, part3);
```

**Avoid - Repeated Allocations**:
```rust
// Inefficient
let mut result = String::new();
for item in items {
    result = result + &item;  // Allocates new string each time
}
```

### Memory Allocation

**Good - Reuse Allocations**:
```rust
// Reuse vector allocation
let mut buffer = Vec::with_capacity(1000);
for batch in batches {
    buffer.clear();  // Keeps capacity
    process_batch(&mut buffer);
}

// Use Box for large stack objects
let large_data = Box::new(LargeStruct::default());
```

### Async Performance

**Good - Concurrent Futures**:
```rust
use tokio::join;

// Run concurrently
let (task, caps, mem) = join!(
    db.get_task(task_id),
    db.get_capabilities(),
    memory.get_context(task_id)
);

// Process multiple items
use futures::future::join_all;
let results = join_all(
    tasks.iter().map(|t| process_task(t))
).await;
```

---

## Database Optimization

### Query Optimization

**Good - Single Query with Join**:
```python
# One query with join
tasks = await db.fetch("""
    SELECT t.*, u.name as user_name, a.name as arm_name
    FROM tasks t
    JOIN users u ON t.user_id = u.id
    LEFT JOIN arms a ON t.assigned_arm_id = a.id
    WHERE t.status = $1
""", "pending")
```

**Bad - N+1 Queries**:
```python
# N+1 problem - slow
tasks = await db.fetch("SELECT * FROM tasks WHERE status = $1", "pending")
for task in tasks:
    user = await db.fetch("SELECT name FROM users WHERE id = $1", task.user_id)
    arm = await db.fetch("SELECT name FROM arms WHERE id = $1", task.assigned_arm_id)
```

### Indexing Strategy

```sql
-- Strategic indexes
CREATE INDEX CONCURRENTLY idx_tasks_status_priority
ON tasks(status, priority DESC);

CREATE INDEX CONCURRENTLY idx_tasks_user_created
ON tasks(user_id, created_at DESC);

-- Partial index for active tasks
CREATE INDEX CONCURRENTLY idx_tasks_active
ON tasks(created_at DESC)
WHERE status IN ('pending', 'running');

-- GIN index for full-text search
CREATE INDEX CONCURRENTLY idx_entities_name_gin
ON entities USING GIN(to_tsvector('english', name));

-- BRIN index for time-series data
CREATE INDEX CONCURRENTLY idx_task_history_created_brin
ON task_history USING BRIN(created_at);
```

### Connection Pooling

```python
from sqlalchemy.ext.asyncio import create_async_engine

# Properly sized connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Base pool size
    max_overflow=10,       # Additional connections under load
    pool_timeout=30,       # Wait time for connection
    pool_recycle=3600,     # Recycle connections hourly
    pool_pre_ping=True,    # Verify connection before use
    echo_pool=True         # Debug pool usage
)
```

### Batch Operations

```python
# Good - batch insert
async def create_tasks_batch(tasks: List[TaskContract]):
    values = [
        (t.task_id, t.description, t.priority, t.user_id)
        for t in tasks
    ]
    await db.executemany(
        "INSERT INTO tasks (id, description, priority, user_id) VALUES ($1, $2, $3, $4)",
        values
    )

# Good - batch update with temporary table
async def update_tasks_batch(updates: List[Tuple[str, str]]):
    # Create temp table
    await db.execute("""
        CREATE TEMP TABLE task_updates (
            task_id TEXT,
            status TEXT
        ) ON COMMIT DROP
    """)

    # Bulk insert updates
    await db.executemany(
        "INSERT INTO task_updates VALUES ($1, $2)",
        updates
    )

    # Single update from temp table
    await db.execute("""
        UPDATE tasks t
        SET status = u.status
        FROM task_updates u
        WHERE t.id = u.task_id
    """)
```

---

## Caching Strategies

### Multi-Level Cache

```python
from cachetools import TTLCache
import redis.asyncio as redis

class MultiLevelCache:
    """L1 (in-memory) + L2 (Redis) cache."""

    def __init__(self, redis_client: redis.Redis):
        self.l1 = TTLCache(maxsize=1000, ttl=60)  # 1 minute
        self.l2 = redis_client

    async def get(self, key: str) -> Optional[str]:
        # Try L1 (fast)
        if key in self.l1:
            return self.l1[key]

        # Try L2 (slower but shared)
        value = await self.l2.get(key)
        if value:
            # Promote to L1
            self.l1[key] = value
            return value

        return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        # Write to both levels
        self.l1[key] = value
        await self.l2.setex(key, ttl, value)
```

### Cache Warming

```python
async def warm_cache_on_startup():
    """Pre-load frequently accessed data."""
    # Load arm capabilities
    capabilities = await db.fetch_all_arm_capabilities()
    for cap in capabilities:
        await cache.set(
            f"arm:capabilities:{cap.arm_id}",
            json.dumps(cap.to_dict()),
            ttl=3600
        )

    # Load active users
    users = await db.fetch_active_users()
    for user in users:
        await cache.set(
            f"user:{user.id}",
            json.dumps(user.to_dict()),
            ttl=1800
        )
```

### Cache Invalidation

```python
async def update_task_status(task_id: str, status: str):
    """Update with cache invalidation."""
    # Update database
    await db.execute(
        "UPDATE tasks SET status = $1 WHERE id = $2",
        status, task_id
    )

    # Invalidate related caches
    await cache.delete(f"task:{task_id}")
    await cache.delete(f"task:status:{task_id}")

    # Update cache with new value
    task = await db.get_task(task_id)
    await cache.set(
        f"task:{task_id}",
        json.dumps(task.dict()),
        ttl=300
    )
```

---

## Async Programming

### Semaphore for Concurrency Control

```python
import asyncio

# Limit concurrent database connections
db_semaphore = asyncio.Semaphore(10)

async def query_with_limit(query: str):
    async with db_semaphore:
        return await db.fetch(query)

# Limit concurrent LLM API calls
llm_semaphore = asyncio.Semaphore(5)

async def call_llm_with_limit(prompt: str):
    async with llm_semaphore:
        return await llm_client.generate(prompt)
```

### Task Groups for Better Error Handling

```python
import asyncio

async def process_tasks_with_groups(tasks: List[TaskContract]):
    """Process tasks with proper error handling."""
    async with asyncio.TaskGroup() as group:
        results = [
            group.create_task(process_task(task))
            for task in tasks
        ]

    # If any task fails, all are cancelled
    return [r.result() for r in results]
```

### Avoid Blocking Operations

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Bad - blocks event loop
def sync_heavy_computation():
    return sum(range(10_000_000))

# Good - run in thread pool
executor = ThreadPoolExecutor(max_workers=4)

async def async_heavy_computation():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        sync_heavy_computation
    )
    return result
```

---

## Network Optimization

### Connection Pooling

```python
import httpx

# Reuse HTTP connections
http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30
    ),
    timeout=httpx.Timeout(30.0),
    http2=True  # Enable HTTP/2
)

async def call_arm(arm_url: str, data: dict):
    """Call arm with connection reuse."""
    response = await http_client.post(
        f"{arm_url}/execute",
        json=data
    )
    return response.json()
```

### Request Batching

```python
from typing import List, Dict
import asyncio

class RequestBatcher:
    """Batch multiple requests into one."""

    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.queue: List[Tuple[str, asyncio.Future]] = []
        self.lock = asyncio.Lock()

    async def add_request(self, prompt: str) -> str:
        """Add request to batch."""
        future = asyncio.Future()

        async with self.lock:
            self.queue.append((prompt, future))

            if len(self.queue) >= self.batch_size:
                await self._process_batch()

        # Wait for batch to process
        try:
            return await asyncio.wait_for(
                future,
                timeout=self.batch_timeout * 2
            )
        except asyncio.TimeoutError:
            # Process partial batch
            await self._process_batch()
            return await future

    async def _process_batch(self):
        """Process current batch."""
        async with self.lock:
            if not self.queue:
                return

            batch = self.queue[:]
            self.queue.clear()

        # Combine prompts
        prompts = [p for p, _ in batch]
        combined = "\n---\n".join(prompts)

        # Single API call
        response = await llm_client.generate(combined)

        # Split response
        responses = response.split("\n---\n")

        # Resolve futures
        for (_, future), resp in zip(batch, responses):
            future.set_result(resp)
```

### Response Compression

```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

# Enable gzip compression
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # Only compress responses > 1KB
)
```

---

## Memory Management

### Object Pooling

```python
from queue import Queue
from typing import Generic, TypeVar, Callable

T = TypeVar('T')

class ObjectPool(Generic[T]):
    """Reuse expensive objects."""

    def __init__(
        self,
        factory: Callable[[], T],
        size: int = 10
    ):
        self.factory = factory
        self.pool: Queue[T] = Queue(maxsize=size)

        # Pre-populate pool
        for _ in range(size):
            self.pool.put(factory())

    def acquire(self) -> T:
        """Get object from pool."""
        try:
            return self.pool.get_nowait()
        except:
            return self.factory()

    def release(self, obj: T):
        """Return object to pool."""
        try:
            self.pool.put_nowait(obj)
        except:
            pass  # Pool full, let object be garbage collected

# Usage
import httpx

client_pool = ObjectPool(
    factory=lambda: httpx.AsyncClient(),
    size=10
)

async def make_request(url: str):
    client = client_pool.acquire()
    try:
        response = await client.get(url)
        return response.json()
    finally:
        client_pool.release(client)
```

### Generators for Large Datasets

```python
# Good - generator for memory efficiency
def process_large_dataset(file_path: str):
    """Process file line by line."""
    with open(file_path) as f:
        for line in f:
            yield process_line(line)

# Use generator
for result in process_large_dataset("large_file.txt"):
    handle_result(result)

# Bad - loads everything into memory
def process_large_dataset_bad(file_path: str):
    with open(file_path) as f:
        lines = f.readlines()  # Loads entire file
        return [process_line(line) for line in lines]
```

---

## Profiling Tools

### CPU Profiling

```python
import cProfile
import pstats

# Profile function
profiler = cProfile.Profile()
profiler.enable()

result = expensive_function()

profiler.disable()

# Print stats
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    """Profile memory usage."""
    large_list = [i for i in range(10_000_000)]
    return sum(large_list)

# Run with: python -m memory_profiler script.py
```

### Request Profiling Middleware

```python
import time
from fastapi import Request

@app.middleware("http")
async def profile_requests(request: Request, call_next):
    """Profile request handling."""
    start = time.time()

    response = await call_next(request)

    duration = time.time() - start

    if duration > 1.0:  # Log slow requests
        logger.warning(
            "slow_request",
            path=request.url.path,
            method=request.method,
            duration=duration
        )

    response.headers["X-Process-Time"] = str(duration)
    return response
```

---

## Best Practices Summary

1. **Measure first**: Profile before optimizing
2. **Async by default**: Use async/await for I/O operations
3. **Batch operations**: Combine multiple database/API calls
4. **Cache aggressively**: Use multi-level caching
5. **Pool connections**: Reuse database and HTTP connections
6. **Optimize queries**: Use indexes and avoid N+1 queries
7. **Stream large data**: Use generators for large datasets
8. **Limit concurrency**: Use semaphores to control resource usage
9. **Monitor performance**: Track metrics in production
10. **Set budgets**: Define and enforce performance budgets

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Engineering Team
