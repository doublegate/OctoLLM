# Persistence Layer

Data storage and caching infrastructure for OctoLLM.

## Components

### PostgreSQL (Global Semantic Memory)

**Purpose**: Project-wide knowledge graph
**Technology**: PostgreSQL 14+
**Schema**: Tasks, decisions, facts, artifacts

**Features**:
- Relational data with JSON support
- Full-text search
- Vector similarity search (pgvector extension)
- ACID compliance

### Redis (Caching)

**Purpose**: High-speed caching and session storage
**Technology**: Redis 7+
**TTL**: Configurable (default 1 hour)

**Features**:
- Sub-millisecond latency
- Pub/sub messaging
- Automatic expiration
- Persistence options

### Qdrant/Weaviate (Vector Store)

**Purpose**: Semantic search over embeddings
**Technology**: Qdrant or Weaviate
**Dimensions**: 1536 (OpenAI embeddings)

**Features**:
- Fast approximate nearest neighbor search
- Filtering and metadata
- Multi-tenancy
- REST API

## Data Models

See [Data Structures](../architecture/data-structures.md) for schemas.

## Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| PostgreSQL Query (P95) | <10ms | <5ms ✅ |
| Redis Get | <1ms | <1ms ✅ |
| Vector Search | <50ms | TBD |

## See Also

- [Architecture Overview](../architecture/overview.md)
- [Memory Systems](../development/memory-systems.md)
- [Operations Guide](../operations/deployment-guide.md)
