# Reflex Layer

The Reflex Layer is OctoLLM's fast preprocessing component, handling common patterns and caching without LLM involvement.

## Overview

- **Language**: Rust 1.75+
- **Framework**: Axum (async HTTP)
- **Cache**: Redis 7+
- **Target Latency**: <10ms P95 for cache hits, <50ms for reflex decisions
- **Throughput**: 10,000+ req/s per instance

## Architecture

The Reflex Layer acts as the first decision point:

1. **Request Validation** → Schema validation, rate limiting
2. **PII Detection** → Scan for sensitive data (regex + ML)
3. **Cache Lookup** → Check Redis for exact/similar queries
4. **Pattern Matching** → Apply reflex rules (allowlists, shortcuts)
5. **Routing Decision** → Cache hit (respond) OR forward to Orchestrator

## Key Components

### Handlers (`src/handlers/`)
- `ingress.rs` - Main HTTP request handler
- `validation.rs` - Input validation and sanitization
- `routing.rs` - Decision logic (cache vs. orchestrator)

### Cache (`src/cache/`)
- `redis_client.rs` - Redis connection pool
- `similarity.rs` - Fuzzy cache matching (embeddings)
- `eviction.rs` - LRU eviction policy

### PII Detection (`src/pii/`)
- `detector.rs` - Regex patterns for 18+ PII types
- `redactor.rs` - Automatic redaction (email → `[EMAIL]`)
- `allow_list.rs` - Whitelisted patterns

### Metrics (`src/metrics/`)
- `prometheus.rs` - Metrics collection
- `latency.rs` - P50/P95/P99 histograms

## Configuration

Environment variables (see `.env.example`):

```bash
# Redis
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# PII Detection
PII_DETECTION_ENABLED=true
PII_AUTO_REDACT=true

# Performance
WORKER_THREADS=8
MAX_CONNECTIONS=1000
```

## Development

```bash
# Build
cd services/reflex-layer
cargo build --release

# Test
cargo test

# Benchmark
cargo bench

# Run locally
cargo run --release
```

## API Endpoints

- `POST /reflex/process` - Main reflex processing endpoint
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Performance

```
Benchmarks (Apple M1 Max, 10-core):
- Cache hit: 2.3ms P95
- Cache miss + PII scan: 12.7ms P95
- Throughput: 14,200 req/s (single instance)
```

## PII Detection Patterns

Supported types:
- Email addresses
- Phone numbers (US, international)
- SSN (US)
- Credit card numbers
- IP addresses
- Dates of birth
- Addresses
- Names (ML model)
- And 10+ more...

## Security

- TLS 1.3 required for external traffic
- Rate limiting per API key and IP
- Request size limits (10MB max)
- Automatic PII redaction in logs

## References

- [Reflex Layer Specification](../../docs/components/reflex-layer.md)
- [PII Protection Guide](../../docs/security/pii-protection.md)
- [Performance Tuning](../../docs/operations/performance-tuning.md)
