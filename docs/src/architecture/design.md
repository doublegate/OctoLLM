# System Design

Technical implementation details and design decisions.

## Technology Stack

- **Orchestrator:** Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Reflex Layer:** Rust (performance-critical)
- **Arms:** Mixed (Python for AI-heavy, Rust for security-critical)
- **Persistence:** PostgreSQL, Redis, Qdrant/Weaviate
- **Observability:** Prometheus, Loki, Jaeger

## Deployment

- **Development:** Docker Compose
- **Production:** Kubernetes with namespace `octollm`

For complete architecture documentation, see [ref-docs/OctoLLM-Architecture-Implementation.md](https://github.com/doublegate/OctoLLM/blob/main/ref-docs/OctoLLM-Architecture-Implementation.md).
