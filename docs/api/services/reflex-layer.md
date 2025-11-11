# Reflex Layer API Reference

**Service**: Reflex Layer (Ingress Gateway)
**Port**: 8001
**Base URL**: `http://localhost:8001` (development), `https://reflex.octollm.example.com` (production)
**Technology**: Rust 1.75+ / Axum
**Cost Tier**: 1 (Cheap - no LLM calls)
**Average Latency**: <10ms (cache hit), <50ms (reflex decision)

## Overview

The Reflex Layer is the first line of defense and performance optimization in the OctoLLM system. It provides ultra-fast preprocessing for incoming requests with caching, pattern matching, and safety checks. Think of it as the security guard and receptionist that handles routine questions instantly, freeing the brain (Orchestrator) for complex tasks.

### Capabilities

- **Cache Lookup**: Sub-10ms responses for previously seen queries
- **Pattern Matching**: Instant responses for common patterns (greetings, help, status queries)
- **Safety Checks**: PII detection, SQL injection detection, prompt injection blocking
- **Rate Limiting**: Per-key request throttling
- **Request Routing**: Smart forwarding decisions to Orchestrator
- **Metrics Collection**: Prometheus-compatible observability

### Key Features

- **Ultra-Low Latency**: <10ms for cache hits, <50ms for reflex decisions
- **Zero LLM Cost**: All processing uses local pattern matching and caching
- **150+ Patterns**: Pre-configured responses for common queries
- **Redis Backend**: Distributed caching with automatic eviction
- **Safety First**: Multi-layer input validation before forwarding
- **Horizontal Scaling**: Stateless design enables easy scaling

---

## Authentication

Most Reflex Layer endpoints require authentication:

**API Key** (recommended for preprocessing):
```bash
curl https://reflex.octollm.example.com/preprocess \
  -H "X-API-Key: octollm_live_1234567890abcdef" \
  -d '{"query": "Hello", "user_id": "user_12345"}'
```

**Bearer Token** (for admin operations like cache management):
```bash
curl https://reflex.octollm.example.com/cache/clear \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -X POST
```

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details.

---

## Endpoints

### POST /preprocess

Preprocess incoming request with cache checking, pattern matching, and safety validation.

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `X-API-Key: <api-key>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "query": "What is the capital of France?",
  "user_id": "user_12345",
  "check_cache": true,
  "metadata": {
    "source": "web",
    "session_id": "sess_xyz789"
  }
}
```

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `query` | string | ✅ | 1-5000 chars | User query or request text |
| `user_id` | string | ✅ | Pattern: `^user_[a-zA-Z0-9_-]+$` | Unique user identifier for rate limiting |
| `check_cache` | boolean | ❌ | - | Whether to check cache (default: `true`) |
| `metadata` | object | ❌ | - | Additional metadata (source, session_id, etc.) |

#### Response

**Status**: 200 OK

**Possible Decisions**:

1. **cache_hit**: Found exact match in cache (instant response)
2. **reflex_handled**: Matched pattern, generated response without LLM
3. **forward_to_orchestrator**: Complex query requiring Orchestrator
4. **blocked**: Request blocked by safety checks

**Response Body**:

```json
{
  "decision": "cache_hit",
  "response": "The capital of France is Paris.",
  "confidence": 1.0,
  "latency_ms": 3.2,
  "metadata": {
    "cache_key": "sha256_abc123",
    "cached_at": "2025-11-11T09:00:00Z"
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `decision` | string | One of: `cache_hit`, `reflex_handled`, `forward_to_orchestrator`, `blocked` |
| `response` | string | Response text (only present for `cache_hit` or `reflex_handled`) |
| `confidence` | number | Confidence in decision (0.0-1.0). Always 1.0 for cache/blocked, <1.0 for patterns |
| `latency_ms` | number | Processing latency in milliseconds |
| `metadata` | object | Additional context (cache key, pattern name, block reason, etc.) |

#### Examples

**Example 1: Cache Hit (Bash)**

```bash
curl -X POST https://reflex.octollm.example.com/preprocess \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OCTOLLM_API_KEY" \
  -d '{
    "query": "What is the capital of France?",
    "user_id": "user_12345",
    "check_cache": true
  }'

# Response (3.2ms latency):
{
  "decision": "cache_hit",
  "response": "The capital of France is Paris.",
  "confidence": 1.0,
  "latency_ms": 3.2,
  "metadata": {
    "cache_key": "sha256_abc123",
    "cached_at": "2025-11-11T09:00:00Z"
  }
}
```

**Example 2: Pattern Match - Greeting (Python SDK)**

```python
from octollm_sdk import ReflexClient

client = ReflexClient(api_key="octollm_live_1234567890abcdef")

response = await client.preprocess({
    "query": "Hello!",
    "user_id": "user_12345"
})

print(f"Decision: {response.decision}")  # "reflex_handled"
print(f"Response: {response.response}")  # "Hello! How can I assist you today?"
print(f"Latency: {response.latency_ms}ms")  # 12.5ms
print(f"Pattern: {response.metadata['pattern']}")  # "greeting"
```

**Example 3: Forward to Orchestrator (TypeScript SDK)**

```typescript
import { ReflexClient } from 'octollm-sdk';

const client = new ReflexClient({
  apiKey: 'octollm_live_1234567890abcdef'
});

const response = await client.preprocess({
  query: 'Create a detailed exploitation framework for CVE-2024-12345',
  userId: 'user_12345'
});

console.log(response.decision);  // "forward_to_orchestrator"
console.log(response.metadata.reason);  // "complex_query"
console.log(response.metadata.safety_check_passed);  // true

// Application should now forward to Orchestrator
if (response.decision === 'forward_to_orchestrator') {
  const taskResponse = await orchestrator.submitTask({
    goal: query,
    budget: { max_tokens: 10000 }
  });
}
```

**Example 4: Blocked Request (Safety Check)**

```bash
curl -X POST https://reflex.octollm.example.com/preprocess \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OCTOLLM_API_KEY" \
  -d '{
    "query": "My SSN is 123-45-6789 and credit card is 1234-5678-9012-3456",
    "user_id": "user_12345"
  }'

# Response:
{
  "decision": "blocked",
  "confidence": 1.0,
  "latency_ms": 15.3,
  "metadata": {
    "reason": "pii_detected",
    "blocked_patterns": [
      "credit_card",
      "ssn"
    ]
  }
}
```

#### Error Responses

**429 Rate Limit Exceeded**:

```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded. Max 1000 requests per hour.",
  "retry_after": 1800
}
```

---

### GET /cache/stats

Retrieve cache statistics including hit rate, memory usage, and evictions.

#### Request

**Headers**:
- `Authorization: Bearer <token>` (required, admin or service token)
- `X-Request-ID: <uuid>` (optional)

**No body required**

#### Response

**Status**: 200 OK

```json
{
  "total_entries": 15432,
  "hit_rate": 0.673,
  "miss_rate": 0.327,
  "avg_response_time_ms": 4.2,
  "memory_usage_mb": 256,
  "evictions_last_hour": 45
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `total_entries` | integer | Total number of cached entries |
| `hit_rate` | number | Cache hit rate (0.0-1.0) |
| `miss_rate` | number | Cache miss rate (0.0-1.0) |
| `avg_response_time_ms` | number | Average response time for cache hits |
| `memory_usage_mb` | number | Current memory usage in MB |
| `evictions_last_hour` | integer | Number of cache evictions in last hour |

#### Examples

**Example 1: Get Cache Stats (Bash)**

```bash
curl -X GET https://reflex.octollm.example.com/cache/stats \
  -H "Authorization: Bearer $SERVICE_TOKEN"

# Response:
{
  "total_entries": 15432,
  "hit_rate": 0.673,
  "miss_rate": 0.327,
  "avg_response_time_ms": 4.2,
  "memory_usage_mb": 256,
  "evictions_last_hour": 45
}
```

**Example 2: Monitor Cache Performance (Python SDK)**

```python
from octollm_sdk import ReflexClient

client = ReflexClient(bearer_token="service_token_abc123")

stats = await client.get_cache_stats()

print(f"Cache Hit Rate: {stats.hit_rate * 100:.1f}%")
print(f"Memory Usage: {stats.memory_usage_mb} MB")
print(f"Avg Latency: {stats.avg_response_time_ms} ms")

# Alert if hit rate drops below 60%
if stats.hit_rate < 0.60:
    print("WARNING: Cache hit rate below threshold!")
```

**Example 3: Cache Health Dashboard (TypeScript SDK)**

```typescript
import { ReflexClient } from 'octollm-sdk';

const client = new ReflexClient({
  bearerToken: process.env.SERVICE_TOKEN
});

async function monitorCache() {
  const stats = await client.getCacheStats();

  console.log('=== CACHE HEALTH ===');
  console.log(`Total Entries: ${stats.total_entries.toLocaleString()}`);
  console.log(`Hit Rate: ${(stats.hit_rate * 100).toFixed(1)}%`);
  console.log(`Miss Rate: ${(stats.miss_rate * 100).toFixed(1)}%`);
  console.log(`Avg Latency: ${stats.avg_response_time_ms.toFixed(1)} ms`);
  console.log(`Memory: ${stats.memory_usage_mb} MB`);
  console.log(`Evictions (1h): ${stats.evictions_last_hour}`);

  return stats;
}

// Poll every 60 seconds
setInterval(monitorCache, 60000);
```

---

### POST /cache/clear

Clear all cached responses (requires admin privileges).

#### Request

**Headers**:
- `Authorization: Bearer <admin-token>` (required, admin token only)
- `X-Request-ID: <uuid>` (optional)

**No body required**

#### Response

**Status**: 200 OK

```json
{
  "message": "Cache cleared successfully",
  "entries_cleared": 15432
}
```

#### Examples

**Example 1: Clear Cache (Bash)**

```bash
curl -X POST https://reflex.octollm.example.com/cache/clear \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Response:
{
  "message": "Cache cleared successfully",
  "entries_cleared": 15432
}
```

**Example 2: Clear Cache After Deployment (Python SDK)**

```python
from octollm_sdk import ReflexClient

# Admin token required
client = ReflexClient(bearer_token="admin_token_xyz789")

result = await client.clear_cache()
print(f"Cleared {result.entries_cleared} cache entries")
```

**Example 3: Scheduled Cache Refresh (TypeScript SDK)**

```typescript
import { ReflexClient } from 'octollm-sdk';

const client = new ReflexClient({
  bearerToken: process.env.ADMIN_TOKEN
});

// Clear cache daily at 3 AM
async function scheduledCacheClear() {
  const result = await client.clearCache();
  console.log(`Cache cleared: ${result.entries_cleared} entries`);

  // Log to monitoring system
  await logToMonitoring({
    event: 'cache_cleared',
    entries: result.entries_cleared,
    timestamp: new Date().toISOString()
  });
}
```

#### Error Responses

**401 Unauthorized** (missing or invalid token):

```json
{
  "error": "Unauthorized",
  "message": "Admin token required for cache operations"
}
```

---

### GET /health

Health check endpoint for load balancers and monitoring systems.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "status": "healthy",
  "version": "0.3.0",
  "uptime_seconds": 7200,
  "cache_hit_rate": 0.67,
  "avg_latency_ms": 8.5
}
```

#### Examples

**Example 1: Kubernetes Liveness Probe**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 30
  periodSeconds: 10
```

**Example 2: Health Check Script (Bash)**

```bash
#!/bin/bash
HEALTH=$(curl -s http://localhost:8001/health)
STATUS=$(echo $HEALTH | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
  echo "Service unhealthy: $HEALTH"
  exit 1
fi

echo "Service healthy"
exit 0
```

---

### GET /metrics

Prometheus metrics endpoint for observability.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK
**Content-Type**: text/plain

```
# HELP reflex_requests_total Total number of preprocessing requests
# TYPE reflex_requests_total counter
reflex_requests_total{decision="cache_hit"} 10523
reflex_requests_total{decision="reflex_handled"} 3421
reflex_requests_total{decision="forward_to_orchestrator"} 5892
reflex_requests_total{decision="blocked"} 164

# HELP reflex_latency_seconds Request processing latency
# TYPE reflex_latency_seconds histogram
reflex_latency_seconds_bucket{le="0.005"} 8234
reflex_latency_seconds_bucket{le="0.010"} 10523
reflex_latency_seconds_bucket{le="0.050"} 19836

# HELP reflex_cache_hit_rate Cache hit rate
# TYPE reflex_cache_hit_rate gauge
reflex_cache_hit_rate 0.673
```

#### Examples

**Example 1: Prometheus Scrape Config**

```yaml
scrape_configs:
  - job_name: 'reflex-layer'
    static_configs:
      - targets: ['reflex:8001']
    metrics_path: /metrics
    scrape_interval: 15s
```

---

### GET /capabilities

Retrieve reflex layer capabilities and configuration.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "capabilities": [
    "cache_lookup",
    "pattern_matching",
    "rate_limiting",
    "pii_detection",
    "injection_detection"
  ],
  "patterns_loaded": 150,
  "cache_enabled": true
}
```

#### Examples

**Example 1: Check Capabilities (Bash)**

```bash
curl -X GET https://reflex.octollm.example.com/capabilities

# Response:
{
  "capabilities": [
    "cache_lookup",
    "pattern_matching",
    "rate_limiting",
    "pii_detection",
    "injection_detection"
  ],
  "patterns_loaded": 150,
  "cache_enabled": true
}
```

---

## Data Models

### PreprocessRequest

```typescript
interface PreprocessRequest {
  query: string;              // 1-5000 chars
  user_id: string;            // Pattern: ^user_[a-zA-Z0-9_-]+$
  check_cache?: boolean;      // Default: true
  metadata?: {
    [key: string]: any;
  };
}
```

### PreprocessResponse

```typescript
type Decision =
  | 'cache_hit'
  | 'reflex_handled'
  | 'forward_to_orchestrator'
  | 'blocked';

interface PreprocessResponse {
  decision: Decision;
  response?: string;          // Present for cache_hit or reflex_handled
  confidence: number;         // 0.0-1.0
  latency_ms: number;
  metadata: {
    cache_key?: string;       // For cache_hit
    cached_at?: string;       // For cache_hit
    pattern?: string;         // For reflex_handled
    template?: string;        // For reflex_handled
    reason?: string;          // For forward_to_orchestrator or blocked
    blocked_patterns?: string[];  // For blocked
    safety_check_passed?: boolean;
  };
}
```

### CacheStats

```typescript
interface CacheStats {
  total_entries: number;
  hit_rate: number;           // 0.0-1.0
  miss_rate: number;          // 0.0-1.0
  avg_response_time_ms: number;
  memory_usage_mb: number;
  evictions_last_hour: number;
}
```

### HealthResponse

```typescript
interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;            // Semantic version (e.g., "0.3.0")
  uptime_seconds: number;
  cache_hit_rate?: number;    // 0.0-1.0
  avg_latency_ms?: number;
}
```

---

## Integration Patterns

### Pattern 1: Reflex-First Architecture

Always hit Reflex Layer before Orchestrator to maximize cache hits and minimize cost.

```python
from octollm_sdk import ReflexClient, OrchestratorClient

reflex = ReflexClient(api_key="...")
orchestrator = OrchestratorClient(api_key="...")

async def process_query(query: str, user_id: str):
    # Try reflex first
    reflex_response = await reflex.preprocess({
        "query": query,
        "user_id": user_id
    })

    if reflex_response.decision == "cache_hit":
        return reflex_response.response, reflex_response.latency_ms

    if reflex_response.decision == "reflex_handled":
        return reflex_response.response, reflex_response.latency_ms

    if reflex_response.decision == "blocked":
        raise ValueError(f"Request blocked: {reflex_response.metadata['reason']}")

    # Forward to orchestrator
    task = await orchestrator.submit_task({
        "goal": query,
        "budget": {"max_tokens": 10000}
    })

    # Poll for result
    result = await orchestrator.wait_for_completion(task.task_id)
    return result.output, result.total_latency_ms
```

### Pattern 2: Cache Warming

Pre-populate cache with common queries to improve hit rate.

```typescript
import { ReflexClient } from 'octollm-sdk';

const client = new ReflexClient({ apiKey: '...' });

async function warmCache(commonQueries: string[]) {
  console.log(`Warming cache with ${commonQueries.length} queries...`);

  for (const query of commonQueries) {
    await client.preprocess({
      query,
      userId: 'cache_warmer',
      checkCache: false  // Force processing even if cached
    });
  }

  const stats = await client.getCacheStats();
  console.log(`Cache warmed. Total entries: ${stats.total_entries}`);
}

// Common security queries
const commonQueries = [
  "What is the OWASP Top 10?",
  "How do I prevent SQL injection?",
  "What is XSS?",
  "How do I secure API keys?"
];

await warmCache(commonQueries);
```

### Pattern 3: Adaptive Rate Limiting

Monitor cache hit rate and adjust rate limits dynamically.

```python
from octollm_sdk import ReflexClient
import asyncio

client = ReflexClient(bearer_token="service_token_abc123")

async def monitor_and_adjust_limits():
    while True:
        stats = await client.get_cache_stats()

        # If cache hit rate is low, increase rate limits
        # to allow more queries to build cache
        if stats.hit_rate < 0.50:
            print("Low cache hit rate, increasing limits...")
            # Adjust rate limiter config (implementation-specific)

        # If memory usage is high, clear old entries
        if stats.memory_usage_mb > 500:
            print("High memory usage, clearing cache...")
            await client.clear_cache()

        await asyncio.sleep(300)  # Check every 5 minutes
```

---

## Performance Characteristics

| Scenario | P50 | P95 | P99 | Max | Notes |
|----------|-----|-----|-----|-----|-------|
| Cache Hit | 3ms | 8ms | 12ms | 20ms | Redis latency + parsing |
| Cache Miss (Pattern) | 15ms | 35ms | 50ms | 80ms | Pattern matching + safety checks |
| Cache Miss (Forward) | 10ms | 20ms | 30ms | 50ms | Safety checks only |
| Blocked Request | 15ms | 25ms | 35ms | 60ms | PII/injection detection |

### Latency Optimization Tips

1. **Enable Connection Pooling**: Reuse connections to Reflex Layer
2. **Batch Requests**: Use HTTP/2 multiplexing for concurrent requests
3. **Monitor Cache Hit Rate**: Aim for >60% hit rate for optimal performance
4. **Use Request IDs**: Enable distributed tracing for debugging slow requests
5. **Deploy Close to Clients**: Minimize network latency

### Cost Savings

With 60% cache hit rate:
- **Before Reflex**: 100,000 requests × $0.002/request = **$200**
- **After Reflex**: 40,000 requests × $0.002/request = **$80** (60% savings)

---

## Troubleshooting

### Issue 1: Low Cache Hit Rate (<40%)

**Symptoms**: Cache hit rate consistently below 40%, high orchestrator load

**Possible Causes**:
- Queries have high variability (different wording for same question)
- Cache TTL too short
- Cache eviction too aggressive

**Solutions**:
```bash
# Check cache stats
curl https://reflex.octollm.example.com/cache/stats

# Increase cache TTL (config change)
# CACHE_TTL_SECONDS=7200  # 2 hours

# Increase max cache size
# MAX_CACHE_ENTRIES=50000

# Implement query normalization (strip punctuation, lowercase)
```

### Issue 2: High Latency (>100ms for reflex decisions)

**Symptoms**: Reflex decisions taking >100ms, health check shows high avg_latency_ms

**Possible Causes**:
- Redis connection issues
- High pattern count (>500)
- CPU saturation

**Solutions**:
```bash
# Check Redis latency
redis-cli --latency-history

# Reduce pattern count (remove low-confidence patterns)
# Keep only patterns with >0.80 confidence

# Scale horizontally (add more reflex instances)
kubectl scale deployment reflex-layer --replicas=5

# Check CPU usage
kubectl top pods -l app=reflex-layer
```

### Issue 3: Too Many Blocked Requests

**Symptoms**: Many legitimate requests getting blocked (decision="blocked")

**Possible Causes**:
- PII detection too aggressive
- False positive injection detection

**Solutions**:
```bash
# Check block reasons
curl https://reflex.octollm.example.com/metrics | grep blocked

# Adjust PII detection thresholds (config change)
# PII_CONFIDENCE_THRESHOLD=0.90  # Increase from 0.70

# Whitelist known safe patterns
# Add to config: WHITELIST_PATTERNS=["user_id", "session_id"]
```

### Issue 4: Cache Not Populating

**Symptoms**: total_entries stays at 0 or very low, hit_rate is 0%

**Possible Causes**:
- Redis connection failure
- Cache disabled in config
- All queries going to orchestrator (check_cache=false)

**Solutions**:
```bash
# Check Redis connection
redis-cli ping

# Check reflex logs
kubectl logs -l app=reflex-layer | grep cache

# Verify cache enabled
curl https://reflex.octollm.example.com/capabilities | jq '.cache_enabled'

# Check environment variables
kubectl get deployment reflex-layer -o yaml | grep CACHE_ENABLED
```

### Issue 5: Rate Limit Errors (429)

**Symptoms**: Clients receiving 429 errors, retry_after headers

**Possible Causes**:
- Rate limit too strict
- Single user making too many requests
- Bot/scraper traffic

**Solutions**:
```bash
# Check rate limit config
# RATE_LIMIT_PER_MINUTE=1000  # Increase if needed

# Implement retry logic with exponential backoff
# Example in SDK:
from octollm_sdk import ReflexClient, RateLimitError
import asyncio

client = ReflexClient(api_key="...", max_retries=5)

try:
    response = await client.preprocess({...})
except RateLimitError as e:
    await asyncio.sleep(e.retry_after)
    response = await client.preprocess({...})
```

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Orchestrator API](./orchestrator.md)
- [OpenAPI Specification](../openapi/reflex-layer.yaml)
- [Architecture Guide](../../ref-docs/OctoLLM-Architecture-Implementation.md)

---

## Support

For issues with the Reflex Layer:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `kubectl logs -l app=reflex-layer`
3. Check metrics: `curl http://reflex:8001/metrics`
4. File issue: https://github.com/octollm/octollm/issues
