# ADR-003: Memory Architecture

**Status**: Accepted
**Date**: 2025-11-10
**Decision Makers**: Architecture Team, ML Engineers
**Consulted**: Database Team, Security Team

## Context

OctoLLM needs a memory system that supports:
- **Global Knowledge**: Facts, entities, relationships shared across all tasks
- **Episodic Memory**: Task-specific examples, code patterns, solutions
- **Short-term Cache**: Frequently accessed data for performance
- **Provenance Tracking**: Audit trail of all operations
- **Security Isolation**: Prevent data leakage between security contexts
- **Vector Search**: Similarity-based retrieval for examples
- **Relational Queries**: Complex joins for knowledge graph
- **High Performance**: Low latency for memory operations

Memory requirements vary by use case:
- Knowledge graph queries: Need SQL joins, ACID guarantees
- Code example retrieval: Need vector similarity search
- Recent task lookup: Need fast key-value access
- Cross-task learning: Need shared knowledge repository

## Decision

We will implement a **three-tier memory architecture** with routing and security isolation:

### 1. Global Memory (PostgreSQL)

**Purpose**: Shared knowledge graph across all tasks
**Storage**: PostgreSQL with JSONB for flexible properties
**Access**: SQL queries via SQLAlchemy ORM

**Schema**:
```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    properties JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE relationships (
    id UUID PRIMARY KEY,
    from_entity_id UUID REFERENCES entities(id),
    to_entity_id UUID REFERENCES entities(id),
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE task_history (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    input TEXT,
    output TEXT,
    provenance JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Use Cases**:
- Storing discovered facts and entities
- Tracking relationships between concepts
- Maintaining task history and audit logs
- Querying for related knowledge

### 2. Episodic Memory (Qdrant)

**Purpose**: Task-specific examples and patterns
**Storage**: Qdrant vector database
**Access**: Vector similarity search

**Collections**:
- `coder_memory`: Code examples with embeddings
- `planner_memory`: Successful task decompositions
- `judge_memory`: Validation patterns

**Example**:
```python
# Store code example
await qdrant_client.upsert(
    collection_name="coder_memory",
    points=[
        {
            "id": example_id,
            "vector": embedding,  # 1536-dim vector
            "payload": {
                "code": code_snippet,
                "language": "python",
                "task_description": description,
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    ]
)

# Retrieve similar examples
results = await qdrant_client.search(
    collection_name="coder_memory",
    query_vector=query_embedding,
    limit=5,
    query_filter={
        "must": [
            {"key": "language", "match": {"value": "python"}},
            {"key": "success", "match": {"value": True}}
        ]
    }
)
```

**Use Cases**:
- Finding similar code examples
- Retrieving relevant task patterns
- Learning from past successes
- Context for LLM prompts

### 3. Cache Layer (Redis + In-Memory)

**L1 Cache (In-Memory)**:
- Library: cachetools TTLCache
- Size: 1,000 items per service
- TTL: 60 seconds
- Use: Hot data, arm capabilities

**L2 Cache (Redis)**:
- Size: Unlimited (eviction policy: LRU)
- TTL: 1-3600 seconds (configurable)
- Use: Shared cache across services

**Example**:
```python
class MultiLevelCache:
    def __init__(self):
        self.l1 = TTLCache(maxsize=1000, ttl=60)
        self.l2 = redis.Redis()

    async def get(self, key: str) -> Optional[str]:
        # Try L1
        if key in self.l1:
            return self.l1[key]

        # Try L2
        value = await self.l2.get(key)
        if value:
            self.l1[key] = value  # Promote to L1
            return value

        return None
```

### 4. Memory Router

**Purpose**: Route queries to appropriate memory system
**Logic**: Based on query type and requirements

```python
class MemoryRouter:
    async def query(self, query: MemoryQuery) -> List[Any]:
        if query.type == "vector_search":
            return await self.episodic_memory.search(query)
        elif query.type == "graph_query":
            return await self.global_memory.query(query)
        elif query.type == "recent_lookup":
            cached = await self.cache.get(query.key)
            if cached:
                return cached
            result = await self.global_memory.query(query)
            await self.cache.set(query.key, result)
            return result
```

### 5. Data Diodes (Security Isolation)

**Purpose**: Enforce security boundaries between memory contexts
**Implementation**: Filtering layer before memory access

```python
class DataDiode:
    async def filter_read(
        self,
        data: Any,
        capability: CapabilityToken
    ) -> Any:
        """Filter data based on capability scope."""
        if capability.scope == "task:read:own":
            # Only return data from user's tasks
            return [
                item for item in data
                if item.user_id == capability.user_id
            ]
        elif capability.scope == "task:read:all":
            # Admin can read all
            return data
        else:
            raise AuthorizationError("Insufficient permissions")

    async def filter_write(
        self,
        data: Any,
        capability: CapabilityToken
    ) -> None:
        """Validate write operations."""
        # Check for PII
        if contains_pii(data):
            raise SecurityViolation("PII detected in write")

        # Check authorization
        if not capability.can_write:
            raise AuthorizationError("No write permission")
```

## Consequences

### Positive

1. **Performance**:
   - L1 cache: sub-millisecond lookups
   - L2 cache: <5ms for common queries
   - Vector search: optimized for similarity
   - SQL: optimized for relations

2. **Flexibility**:
   - Right tool for each use case
   - Can optimize each layer independently
   - Easy to add new memory types
   - Supports diverse query patterns

3. **Security**:
   - Data diodes enforce boundaries
   - Capability-based access control
   - PII detection before storage
   - Audit trail in PostgreSQL

4. **Scalability**:
   - PostgreSQL: vertical + replication
   - Qdrant: horizontal scaling
   - Redis: cluster mode
   - Independent scaling per layer

5. **Rich Queries**:
   - SQL for complex joins
   - Vector search for similarity
   - Hybrid queries combining both
   - Full-text search in PostgreSQL

### Negative

1. **Complexity**:
   - Three databases to manage
   - Data consistency challenges
   - More failure modes
   - Complex debugging

2. **Data Synchronization**:
   - No automatic sync between layers
   - Manual cache invalidation
   - Potential staleness issues
   - Consistency is eventual

3. **Resource Usage**:
   - Higher memory footprint
   - More infrastructure cost
   - Development environment heavier
   - Backup complexity

4. **Operational Burden**:
   - Three systems to monitor
   - Three backup strategies
   - More moving parts
   - Complex recovery procedures

### Mitigation Strategies

1. **Complexity**:
   - Abstract behind unified API
   - Comprehensive documentation
   - Clear routing logic
   - Automated testing

2. **Synchronization**:
   - Well-defined TTLs
   - Event-driven invalidation
   - Version tracking
   - Monitoring for staleness

3. **Resource Usage**:
   - Resource limits in Kubernetes
   - Optimize cache sizes
   - Efficient data models
   - Regular cleanup jobs

4. **Operations**:
   - Unified monitoring dashboards
   - Automated backups
   - Runbooks for common issues
   - Health checks for all layers

## Alternatives Considered

### 1. Single Database (PostgreSQL) with pgvector

**Pros**:
- Simpler architecture
- Single source of truth
- ACID guarantees everywhere
- Easier operations

**Cons**:
- Vector search not as optimized
- Performance trade-offs
- Single point of failure
- Harder to scale independently

**Why Rejected**: Vector search performance insufficient for production scale.

### 2. Graph Database (Neo4j) for Global Memory

**Pros**:
- Optimized for relationships
- Native graph queries
- Good visualization tools

**Cons**:
- Less familiar to team
- Higher operational complexity
- More expensive
- Cypher learning curve

**Why Rejected**: PostgreSQL with JSONB provides sufficient graph capabilities with familiar SQL.

### 3. Elasticsearch for All Memory

**Pros**:
- Full-text search excellent
- Horizontal scaling
- Rich query DSL

**Cons**:
- Not optimized for vectors
- Resource intensive
- Complex to operate
- Overkill for our needs

**Why Rejected**: Qdrant better for vectors, PostgreSQL better for structured data.

### 4. Single-Tier Cache (Redis only)

**Pros**:
- Simpler caching
- No L1/L2 coordination
- Less memory usage

**Cons**:
- Network latency for every lookup
- Higher Redis load
- No in-process caching benefit

**Why Rejected**: L1 cache provides significant performance improvement for hot data.

## Implementation Guidelines

### Global Memory Operations

```python
# Store entity
entity = Entity(
    entity_type="file",
    name="config.yaml",
    properties={"path": "/etc/app/config.yaml", "size": 1024}
)
await global_memory.store_entity(entity)

# Store relationship
relationship = Relationship(
    from_entity_id=file_entity.id,
    to_entity_id=config_entity.id,
    relationship_type="contains",
    properties={"line": 42}
)
await global_memory.store_relationship(relationship)

# Query entities
files = await global_memory.query_entities(
    entity_type="file",
    filters={"properties.extension": "yaml"}
)
```

### Episodic Memory Operations

```python
# Store example
example = CodeExample(
    code="def hello(): print('world')",
    language="python",
    task_description="Print hello world"
)
embedding = await get_embedding(example.code)
await episodic_memory.store(example, embedding)

# Retrieve similar
query_embedding = await get_embedding("print greeting")
examples = await episodic_memory.search(
    query_embedding,
    filter={"language": "python"},
    limit=5
)
```

### Cache Operations

```python
# Store in cache
await cache.set(
    key="arm:capabilities:coder",
    value=json.dumps(capabilities),
    ttl=3600
)

# Retrieve from cache
cached = await cache.get("arm:capabilities:coder")
if cached:
    return json.loads(cached)

# Invalidate cache
await cache.delete("arm:capabilities:coder")
```

## References

- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Redis Caching Patterns](https://redis.io/topics/lru-cache)
- [Memory Architecture Patterns](https://martinfowler.com/articles/patterns-of-distributed-systems/)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-05-10 (6 months)
**Related ADRs**: ADR-001, ADR-004
