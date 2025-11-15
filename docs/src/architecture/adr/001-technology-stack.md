# ADR-001: Technology Stack Selection

**Status**: Accepted
**Date**: 2025-11-10
**Decision Makers**: Architecture Team, Engineering Leads
**Consulted**: Development Team, DevOps Team

## Context

OctoLLM requires a technology stack that supports:
- High-performance request processing (>10,000 req/s for Reflex Layer)
- Async I/O for LLM API calls and database operations
- Vector similarity search for episodic memory
- Reliable data storage with ACID guarantees
- Fast caching for frequently accessed data
- Multiple specialized components (orchestrator, arms, reflex layer)
- Cloud-native deployment (Kubernetes)
- Developer productivity and maintainability

The system has diverse performance requirements:
- **Reflex Layer**: <10ms P95 latency, >10,000 req/s throughput
- **Orchestrator**: Complex routing logic, multiple concurrent operations
- **Arms**: LLM integration, specialized processing
- **Memory**: Vector search, relational queries, caching

## Decision

We will use the following technology stack:

### Core Languages

**Python 3.11+ (Primary)**
- Used for: Orchestrator, all Arms, API services
- Framework: FastAPI for HTTP APIs
- Async: asyncio for concurrent operations
- Reasons:
  - Excellent LLM ecosystem (OpenAI, Anthropic SDKs)
  - Strong async support with asyncio/FastAPI
  - Rich data processing libraries
  - High developer productivity
  - Large talent pool
  - Extensive testing frameworks

**Rust 1.75+ (Performance-Critical)**
- Used for: Reflex Layer, Tool Executor
- Framework: Axum for HTTP
- Reasons:
  - Zero-cost abstractions for performance
  - Memory safety without garbage collection
  - Excellent async runtime (tokio)
  - Pattern matching for PII detection
  - No runtime overhead
  - Strong type system prevents bugs

### Databases

**PostgreSQL 15+ (Primary Data Store)**
- Used for: Global knowledge graph, task history, provenance
- Reasons:
  - ACID guarantees for critical data
  - JSONB for flexible schemas
  - Full-text search with GIN indexes
  - Excellent performance for relational queries
  - Mature replication and backup tools
  - Strong community support

**Qdrant 1.7+ (Vector Database)**
- Used for: Episodic memory (code examples, patterns)
- Reasons:
  - Optimized for similarity search
  - Built in Rust (high performance)
  - Filtering support for hybrid search
  - Supports multiple distance metrics
  - Good Python SDK
  - Active development

**Redis 7+ (Cache & Pub/Sub)**
- Used for: L2 cache, rate limiting, session state, events
- Reasons:
  - In-memory performance (<1ms latency)
  - Rich data structures (strings, hashes, sets, sorted sets)
  - Pub/sub for event messaging
  - TTL support for automatic expiration
  - Persistence options (AOF, RDB)
  - Cluster mode for scale

### Web Framework

**FastAPI (Python)**
- Reasons:
  - Built on Starlette (async ASGI)
  - Automatic OpenAPI documentation
  - Pydantic integration for validation
  - Excellent async support
  - Dependency injection
  - WebSocket support
  - Strong type hints

**Axum (Rust)**
- Reasons:
  - Built on tokio (async runtime)
  - Type-safe routing
  - Minimal overhead
  - Good ecosystem integration
  - Composable middleware

### Async Runtime

**Python: asyncio + uvicorn**
- ASGI server with excellent performance
- Integrates with FastAPI
- Multiple worker processes for CPU utilization

**Rust: tokio**
- Industry-standard async runtime
- Work-stealing scheduler
- Efficient I/O operations

### Deployment

**Docker + Docker Compose**
- Development: Easy local setup
- Production: Standardized containers
- CI/CD: Consistent builds

**Kubernetes**
- Production orchestration
- Auto-scaling with HPA
- Rolling updates
- Service discovery
- Health checks

### Supporting Tools

**Monitoring**:
- Prometheus: Metrics collection
- Grafana: Visualization
- Alertmanager: Alert routing
- Loki: Log aggregation (optional)
- Jaeger: Distributed tracing (optional)

**Development**:
- Poetry: Python dependency management
- Cargo: Rust build tool
- Black/isort/ruff: Python formatting/linting
- rustfmt/clippy: Rust formatting/linting
- pre-commit: Git hooks
- pytest: Python testing
- cargo test: Rust testing

## Consequences

### Positive

1. **Performance**:
   - Rust delivers <10ms latency for Reflex Layer
   - Async Python handles thousands of concurrent operations
   - Redis provides sub-millisecond caching
   - Qdrant optimized for vector search

2. **Developer Experience**:
   - Python enables rapid development
   - FastAPI auto-generates API docs
   - Strong typing catches bugs early
   - Extensive libraries available

3. **Scalability**:
   - Kubernetes enables horizontal scaling
   - Stateless services easy to replicate
   - Database clustering supported
   - Redis can scale with cluster mode

4. **Maintainability**:
   - Type hints improve code clarity
   - Rust prevents memory bugs
   - PostgreSQL ensures data integrity
   - Docker standardizes deployments

5. **Ecosystem**:
   - Rich LLM integration libraries
   - Mature database drivers
   - Active communities
   - Abundant learning resources

### Negative

1. **Complexity**:
   - Two languages to maintain (Python + Rust)
   - Different build tools and workflows
   - Team needs skills in both languages
   - More complex CI/CD pipeline

2. **Learning Curve**:
   - Rust has steep learning curve
   - Async programming can be challenging
   - Kubernetes requires operations expertise
   - Multiple databases to manage

3. **Resource Usage**:
   - Three databases increase infrastructure cost
   - Kubernetes overhead for small deployments
   - Development environment is heavyweight
   - Local testing requires significant resources

4. **Operational Overhead**:
   - More components to monitor
   - More failure modes
   - Complex troubleshooting
   - Data consistency across databases

### Mitigation Strategies

1. **Language Complexity**:
   - Keep Rust components minimal (Reflex, Executor only)
   - Provide Python fallbacks where feasible
   - Comprehensive documentation
   - Code review focus on readability

2. **Learning Curve**:
   - Training programs for team
   - Pair programming for knowledge sharing
   - Start contributors with Python
   - Document common patterns

3. **Resource Usage**:
   - Provide lightweight dev mode (Docker Compose)
   - Use resource limits in Kubernetes
   - Optimize container images
   - Implement efficient caching

4. **Operational Complexity**:
   - Comprehensive monitoring and alerting
   - Automated deployment pipelines
   - Disaster recovery procedures
   - Regular operational training

## Alternatives Considered

### 1. Go for Performance-Critical Components

**Pros**:
- Good performance (better than Python)
- Simpler than Rust
- Excellent concurrency model
- Single binary deployment

**Cons**:
- Not as fast as Rust (<10ms requirement tight)
- Garbage collection introduces latency variance
- Weaker type system than Rust
- Less memory safe

**Why Rejected**: Rust provides better latency guarantees and memory safety for our <10ms P95 requirement.

### 2. Node.js/TypeScript for All Services

**Pros**:
- Single language across stack
- Good async support
- Large ecosystem
- Fast development

**Cons**:
- Not ideal for CPU-intensive tasks
- Weaker LLM library support
- Memory usage higher than Python
- Type system not as strong as Python + mypy

**Why Rejected**: Python has superior LLM ecosystem and better data processing libraries.

### 3. Java/Spring Boot

**Pros**:
- Mature enterprise ecosystem
- Strong typing
- Excellent tooling
- Large talent pool

**Cons**:
- Slower development than Python
- Higher memory usage
- More verbose code
- Weaker LLM integration

**Why Rejected**: Python provides better developer experience and LLM integration.

### 4. All Python (including performance-critical)

**Pros**:
- Single language
- Simpler deployment
- Easier team management
- Unified tooling

**Cons**:
- Cannot meet <10ms P95 latency consistently
- GIL limits true parallelism
- Higher memory usage
- No compile-time safety

**Why Rejected**: Cannot achieve required performance for Reflex Layer without Rust.

### 5. MongoDB instead of PostgreSQL

**Pros**:
- Flexible schema
- Horizontal scaling built-in
- Good for unstructured data

**Cons**:
- Weaker ACID guarantees
- No SQL JOIN support
- Transaction model more limited
- Less mature tooling

**Why Rejected**: Need ACID guarantees for critical data and complex relational queries.

### 6. Elasticsearch instead of Qdrant

**Pros**:
- Mature ecosystem
- Full-text search excellent
- Powerful aggregations

**Cons**:
- Not optimized for vector search
- Higher resource usage
- More complex to operate
- Slower vector operations

**Why Rejected**: Qdrant is purpose-built for vector similarity search with better performance.

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Rust Async Book](https://rust-lang.github.io/async-book/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Redis Documentation](https://redis.io/documentation)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-05-10 (6 months)
**Related ADRs**: ADR-002, ADR-003, ADR-005
