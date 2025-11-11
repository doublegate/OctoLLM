# OctoLLM Architecture

This document provides a technical overview of the OctoLLM distributed AI architecture.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                             │
│                      (NGINX/Traefik)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Reflex Layer (Rust)                         │
│  - PII Detection   - Cache Check   - Pattern Matching           │
│  - Target: <10ms P95                                            │
└──────────────┬───────────────────────────────┬──────────────────┘
               │                               │
               │ Cache Miss                    │ Cache Hit
               │                               │
┌──────────────▼────────────────────────────┐  │
│      Orchestrator (Python + FastAPI)      │  │
│  - Task Planning                          │  │
│  - Arm Selection & Routing                │  │
│  - Execution Coordination                 │  │
│  - Result Validation & Storage            │  │
└──────────────┬────────────────────────────┘  │
               │                               │
    ┌──────────┼──────────┐                    │
    │          │          │                    │
┌───▼───┐  ┌──▼──┐  ┌───▼───┐              ┌──▼─────┐
│Planner│  │Coder│  │Retriev│              │Response│
│  Arm  │  │ Arm │  │er Arm │              │  Cache │
└───┬───┘  └──┬──┘  └───┬───┘              └────────┘
    │         │          │
┌───▼───┐  ┌──▼──┐  ┌───▼────┐
│Executo│  │Judge│  │Safety  │
│r  Arm │  │ Arm │  │Guardian│
└───────┘  └─────┘  └────────┘
    │         │          │
    └─────────┼──────────┘
              │
┌─────────────▼─────────────────────────────────────────┐
│              Distributed Memory                       │
│  - PostgreSQL (global memory)                         │
│  - Redis (caching layer)                              │
│  - Qdrant (vector store for embeddings)               │
└───────────────────────────────────────────────────────┘
```

## Core Components

### 1. Reflex Layer
- **Technology**: Rust + Axum
- **Purpose**: Fast preprocessing, caching, PII detection
- **Latency**: <10ms P95 for cache hits
- **Throughput**: 10,000+ req/s per instance

### 2. Orchestrator
- **Technology**: Python 3.11+ + FastAPI
- **Purpose**: Strategic planning, coordination
- **LLM**: GPT-4, Claude 3 Opus (frontier models)
- **Responsibilities**:
  - Task decomposition
  - Arm selection and routing
  - Parallel/sequential execution coordination
  - Result validation and memory storage

### 3. Specialized Arms
Each arm is a microservice with domain-specific expertise:

| Arm | Language | LLM | Purpose |
|-----|----------|-----|---------|
| **Planner** | Python | GPT-3.5 | Task decomposition |
| **Executor** | Rust | - | Sandboxed command execution |
| **Retriever** | Python | - | Knowledge base search (Qdrant) |
| **Coder** | Python | GPT-4 | Code generation/debugging |
| **Judge** | Python | GPT-3.5 | Output validation |
| **Safety Guardian** | Python | - | PII detection, content filtering |

### 4. Distributed Memory
- **PostgreSQL 15+**: Global task history, decision traces
- **Redis 7+**: L1 cache (TTL: 1 hour), session state
- **Qdrant 1.7+**: Vector embeddings for semantic search

## Data Flow

### Typical Request Flow

1. **User Request** → API Gateway → Reflex Layer
2. **Reflex Layer** checks:
   - Cache (Redis) - if hit, return immediately
   - PII patterns - if found, redact or reject
   - Simple patterns - if matched, apply reflex rule
3. **Cache Miss** → Forward to Orchestrator
4. **Orchestrator** generates plan:
   - Use GPT-4 to decompose task
   - Identify required arms (e.g., Planner → Coder → Judge)
   - Check resource budgets (tokens, time, cost)
5. **Task Execution**:
   - Call Planner Arm → Receive subtasks
   - Call Coder Arm (parallel) → Generate code
   - Call Judge Arm → Validate output
   - Call Safety Guardian → Scan for PII/vulnerabilities
6. **Result Integration**:
   - Aggregate arm responses
   - Store in PostgreSQL (decision trace)
   - Cache in Redis (for future similar queries)
   - Return to user

## Communication Patterns

### Synchronous (HTTP/REST)
- User → API Gateway → Reflex → Orchestrator
- Orchestrator → Arms (request/response)
- Used for: Fast queries, validation checks

### Asynchronous (Message Queue - Future)
- Long-running tasks (>30s)
- Batch processing
- Background indexing

### gRPC (Internal - Future)
- High-throughput inter-service communication
- Protocol Buffer schemas in `shared/proto/`

## Security Architecture

### Defense in Depth

1. **Ingress Layer**: TLS 1.3, rate limiting, DDoS protection
2. **Reflex Layer**: PII detection, prompt injection blocking
3. **Orchestrator**: JWT capability tokens, resource quotas
4. **Arms**: Sandboxing (Docker/gVisor), command allowlisting
5. **Data Layer**: Encryption at rest (AES-256), in transit (TLS)

### Capability-Based Access Control

Each arm receives time-limited JWT tokens with specific permissions:

```json
{
  "sub": "executor-arm-01",
  "exp": 1730000000,
  "capabilities": [
    {"action": "execute", "resource": "bash", "constraints": {"commands": ["ls", "cat", "python3"]}},
    {"action": "read", "resource": "filesystem", "constraints": {"paths": ["/workspace"]}}
  ],
  "rate_limits": {
    "requests_per_minute": 10,
    "tokens_per_day": 100000,
    "cost_per_day": 10.0
  }
}
```

## Deployment Architecture

### Development (Docker Compose)
- All services on single host
- SQLite for PostgreSQL (testing only)
- No TLS (localhost only)

### Staging/Production (Kubernetes)
- Namespace: `octollm-{env}`
- Ingress: NGINX + cert-manager (Let's Encrypt)
- Database: AWS RDS Multi-AZ
- Cache: AWS ElastiCache (Redis cluster mode)
- Vector DB: Qdrant on EKS (StatefulSet)
- Monitoring: Prometheus + Grafana + Loki + Jaeger

### Scaling Strategy

- **Horizontal**: Orchestrator (3+ replicas), Reflex (5+ replicas), Arms (2+ per type)
- **Vertical**: Database (r6g.xlarge), Cache (r7g.large)
- **Autoscaling**: HPA based on CPU (70%) and RPS (target: 80% capacity)

## Observability

### Metrics (Prometheus)
- Request rate, latency (P50/P95/P99), error rate
- LLM token usage, cost tracking
- Cache hit rate, arm utilization

### Logging (Loki + structlog)
- Structured JSON logs with trace IDs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Retention: 30 days (hot), 90 days (cold)

### Tracing (Jaeger - Future)
- Distributed traces across services
- Span tags: task_id, arm_id, llm_model, tokens

### Dashboards (Grafana)
- System health (uptime, error rates)
- Business metrics (tasks completed, cost per task)
- SLO tracking (P95 latency < 30s, success rate > 95%)

## Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| Reflex Layer Latency | <10ms P95 | TBD |
| Orchestrator Latency | <100ms P95 | TBD |
| End-to-End Task Latency | <30s P95 | TBD |
| Task Success Rate | >95% | TBD |
| Cache Hit Rate | >60% (after warmup) | TBD |
| Cost per Task | <50% vs monolithic GPT-4 | TBD |

## Technology Stack

### Languages
- **Python 3.11+**: Orchestrator, most Arms (Planner, Retriever, Coder, Judge, Safety Guardian)
- **Rust 1.75+**: Reflex Layer, Executor Arm (performance/security-critical)

### Frameworks
- **FastAPI**: Python HTTP services
- **Axum**: Rust async HTTP framework
- **Pydantic**: Data validation and serialization

### Databases
- **PostgreSQL 15+**: Relational data (task history, metadata)
- **Redis 7+**: Caching and session state
- **Qdrant 1.7+**: Vector embeddings for semantic search

### Infrastructure
- **Kubernetes 1.28+**: Container orchestration
- **Docker 24+**: Containerization
- **Terraform 1.6+**: Infrastructure as Code
- **Helm 3+**: Kubernetes package manager

### Observability
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and alerting
- **Loki**: Log aggregation
- **Jaeger**: Distributed tracing (future)

### CI/CD
- **GitHub Actions**: CI/CD pipelines
- **Docker Hub / GHCR**: Container registry
- **ArgoCD** (future): GitOps deployments

## Design Patterns

### 1. Mixture of Experts (MoE)
- Multiple specialist arms
- Gating function (Orchestrator) routes to best expert
- Reduces cost vs. single large model

### 2. Hierarchical Planning
- Recursive task decomposition
- Top-down (goal → subtasks → actions)
- Bottom-up validation (acceptance criteria)

### 3. Active Inference
- Proactive uncertainty reduction
- Predict → Act → Observe → Update belief state

### 4. Swarm Decision-Making (Future)
- Multiple arms generate parallel proposals
- Aggregation via voting/consensus
- Conflict resolution via Judge Arm

### 5. Skill Distillation (Future)
- Fine-tune smaller models from decision traces
- Reduce cost for common patterns
- Maintain quality via Judge validation

## Future Enhancements

### Phase 2+ Features
- **Async Task Queue**: RabbitMQ/Redis Streams for long-running tasks
- **gRPC**: High-performance inter-service communication
- **WebSockets**: Real-time progress updates
- **Multi-Tenancy**: Namespace isolation per customer
- **Custom Arms**: Plugin system for domain-specific arms
- **Model Fine-Tuning**: LoRA adapters for specialized tasks
- **Reinforcement Learning**: RLHF for orchestration decisions

## References

- [System Overview](docs/architecture/system-overview.md)
- [Component Specifications](docs/components/)
- [API Contracts](docs/api/component-contracts.md)
- [Deployment Guide](docs/operations/deployment-guide.md)
- [Security Model](docs/security/overview.md)

---

**Last Updated**: 2025-11-10
**Version**: 1.0
**Maintained By**: OctoLLM Architecture Team
