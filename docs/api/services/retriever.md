# Retriever Arm API Reference

**Service**: Retriever Arm (Knowledge Search Specialist)
**Port**: 8004
**Base URL**: `http://localhost:8004` (development), `http://retriever:8004` (internal)
**Technology**: Python 3.11+ / FastAPI
**Cost Tier**: 1 (Low - no expensive LLM calls)
**Average Latency**: 100-500ms

## Overview

The Retriever Arm is the memory and research assistant of OctoLLM. It performs intelligent search across knowledge bases using hybrid vector and keyword methods, then synthesizes results with citations. Think of it as a librarian who not only finds relevant information but also summarizes and properly cites it.

### Capabilities

- **Vector Search**: Semantic similarity using embeddings (e.g., "find similar concepts")
- **Keyword Search**: Traditional full-text search with BM25 ranking
- **Hybrid Search**: Combines vector + keyword with reranking for best results
- **Result Synthesis**: LLM-powered summarization with numbered citations
- **Metadata Filtering**: Filter by date, severity, source, tags, etc.
- **Relevance Scoring**: Confidence scores (0.0-1.0) for each result

### Key Features

- **Sub-500ms Latency**: Fast retrieval with cached embeddings
- **Multi-Source**: Searches across CVE databases, security advisories, documentation
- **Citation Tracking**: Automatic URL citations in synthesized summaries
- **Reranking**: Cross-encoder model improves result ordering
- **Scalable**: Horizontal scaling with Qdrant/Weaviate backends
- **Cost-Effective**: No expensive LLM calls (embeddings only)

---

## Authentication

All Retriever endpoints require Bearer token authentication (inter-service communication):

```bash
curl http://retriever:8004/search \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are common nginx vulnerabilities?",
    "method": "hybrid",
    "limit": 10
  }'
```

**Note**: The Retriever is typically called by the Orchestrator or Planner, not directly by external clients. External clients should use the [Orchestrator API](./orchestrator.md).

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details on capability-based tokens.

---

## Endpoints

### POST /search

Search knowledge base using vector, keyword, or hybrid methods with optional synthesis.

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "query": "What are common nginx vulnerabilities?",
  "method": "hybrid",
  "limit": 10,
  "filters": {
    "severity": ["high", "critical"],
    "published_after": "2024-01-01"
  },
  "min_relevance_score": 0.5,
  "include_citations": true
}
```

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `query` | string | ✅ | 1-500 chars | Search query (natural language) |
| `method` | string | ❌ | `vector`, `keyword`, `hybrid` | Search method (default: `hybrid`) |
| `limit` | integer | ❌ | 1-100, default: 10 | Maximum number of results to return |
| `filters` | object | ❌ | - | Metadata filters (severity, date, source, etc.) |
| `min_relevance_score` | number | ❌ | 0.0-1.0, default: 0.5 | Minimum relevance score threshold |
| `include_citations` | boolean | ❌ | default: `true` | Include citations in synthesized summary |

#### Response

**Status**: 200 OK

```json
{
  "results": [
    {
      "content": "Nginx is vulnerable to buffer overflow in HTTP/2 implementation (CVE-2024-12345)",
      "source": "https://nvd.nist.gov/vuln/detail/CVE-2024-12345",
      "relevance_score": 0.92,
      "rank": 1,
      "metadata": {
        "published_date": "2024-03-15",
        "severity": "high",
        "cvss_score": 7.5
      }
    },
    {
      "content": "Remote code execution possible via malformed headers in versions <1.24.1",
      "source": "https://security.nginx.org/advisories/2024/001",
      "relevance_score": 0.87,
      "rank": 2,
      "metadata": {
        "published_date": "2024-02-20",
        "severity": "critical",
        "cvss_score": 9.8
      }
    }
  ],
  "query": "What are common nginx vulnerabilities?",
  "method_used": "hybrid",
  "total_results": 10,
  "synthesis": "Nginx has several known vulnerabilities including buffer overflow in HTTP/2 [1] and remote code execution via malformed headers [2]. The HTTP/2 buffer overflow affects versions prior to 1.24.0, with a CVSS score of 7.5. The RCE vulnerability is more critical with CVSS 9.8 and affects versions below 1.24.1.",
  "citations": [
    "https://nvd.nist.gov/vuln/detail/CVE-2024-12345",
    "https://security.nginx.org/advisories/2024/001"
  ]
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Ordered list of search results (highest relevance first) |
| `results[].content` | string | Retrieved content snippet |
| `results[].source` | string | Source URL or identifier |
| `results[].relevance_score` | number | Relevance score (0.0-1.0) |
| `results[].rank` | integer | Result rank (1 = most relevant) |
| `results[].metadata` | object | Additional info (date, severity, tags, etc.) |
| `query` | string | Original search query (echo back) |
| `method_used` | string | Search method used (`vector`, `keyword`, `hybrid`) |
| `total_results` | integer | Total number of results returned |
| `synthesis` | string | LLM-generated summary with numbered citations [1], [2], etc. |
| `citations` | array | Source URLs in citation order |

#### Examples

**Example 1: Hybrid Search for CVEs (Bash)**

```bash
curl -X POST http://retriever:8004/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "query": "What are common nginx vulnerabilities?",
    "method": "hybrid",
    "limit": 10,
    "min_relevance_score": 0.5,
    "include_citations": true
  }'

# Response: (see above)
```

**Example 2: Vector Search with Filters (Python SDK)**

```python
from octollm_sdk import RetrieverClient

client = RetrieverClient(bearer_token="service_token_abc123")

response = await client.search({
    "query": "SQL injection prevention techniques",
    "method": "vector",  # Semantic search
    "limit": 5,
    "filters": {
        "source": ["owasp.org", "portswigger.net"],
        "language": "Python"
    },
    "min_relevance_score": 0.7
})

print(f"Found {response.total_results} results")
print(f"\n=== SYNTHESIS ===")
print(response.synthesis)

print(f"\n=== TOP RESULTS ===")
for result in response.results[:3]:
    print(f"\n[{result.rank}] Relevance: {result.relevance_score:.2f}")
    print(f"Content: {result.content}")
    print(f"Source: {result.source}")

# Output:
# Found 5 results
#
# === SYNTHESIS ===
# SQL injection can be prevented using parameterized queries [1],
# input validation with allowlists [2], and ORM frameworks like SQLAlchemy [3].
#
# === TOP RESULTS ===
# [1] Relevance: 0.94
# Content: Use parameterized queries to prevent SQL injection...
# Source: https://owasp.org/sql-injection-prevention
```

**Example 3: Keyword Search with Date Filter (TypeScript SDK)**

```typescript
import { RetrieverClient } from 'octollm-sdk';

const client = new RetrieverClient({
  bearerToken: process.env.SERVICE_TOKEN
});

const response = await client.search({
  query: 'CVE-2024 nginx',
  method: 'keyword',  // Exact keyword matching
  limit: 20,
  filters: {
    published_after: '2024-01-01',
    severity: ['high', 'critical']
  },
  min_relevance_score: 0.6
});

console.log(`Query: "${response.query}"`);
console.log(`Method: ${response.method_used}`);
console.log(`Total results: ${response.total_results}\n`);

// Group by severity
const bySeverity: Record<string, number> = {};
response.results.forEach(r => {
  const severity = r.metadata.severity || 'unknown';
  bySeverity[severity] = (bySeverity[severity] || 0) + 1;
});

console.log('Results by severity:');
Object.entries(bySeverity).forEach(([severity, count]) => {
  console.log(`  ${severity}: ${count}`);
});
```

**Example 4: No Synthesis Mode (Python SDK)**

```python
from octollm_sdk import RetrieverClient

client = RetrieverClient(bearer_token="service_token_abc123")

# Fast retrieval without synthesis (skips LLM call)
response = await client.search({
    "query": "XSS attack vectors",
    "method": "hybrid",
    "limit": 50,
    "include_citations": False  # Skip synthesis step
})

# Process raw results
for result in response.results:
    print(f"[{result.rank}] {result.content[:100]}...")
    print(f"  Score: {result.relevance_score}, Source: {result.source}\n")
```

**Example 5: Metadata-Only Filtering (Bash)**

```bash
# Search for recent critical CVEs
curl -X POST http://retriever:8004/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "query": "web application vulnerabilities",
    "method": "hybrid",
    "limit": 10,
    "filters": {
      "severity": "critical",
      "published_after": "2024-10-01",
      "cvss_score": ">= 9.0"
    },
    "min_relevance_score": 0.7
  }'
```

#### Error Responses

**400 Bad Request** (invalid query):

```json
{
  "error": "ValidationError",
  "message": "Query must be between 1 and 500 characters",
  "details": {
    "field": "query",
    "value_length": 0
  }
}
```

**401 Unauthorized** (missing or invalid token):

```json
{
  "error": "Unauthorized",
  "message": "Bearer token required for search operations"
}
```

**500 Internal Server Error** (vector database unavailable):

```json
{
  "error": "ServiceUnavailable",
  "message": "Vector database connection failed",
  "details": {
    "backend": "qdrant",
    "status": "unreachable"
  }
}
```

---

### GET /capabilities

Retrieve retriever capabilities and supported search methods.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "capabilities": [
    "vector_search",
    "keyword_search",
    "hybrid_search",
    "result_synthesis"
  ]
}
```

#### Examples

**Example 1: Check Capabilities (Bash)**

```bash
curl -X GET http://retriever:8004/capabilities

# Response:
{
  "capabilities": [
    "vector_search",
    "keyword_search",
    "hybrid_search",
    "result_synthesis"
  ]
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
  "version": "0.3.0"
}
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
# HELP retriever_searches_total Total number of searches
# TYPE retriever_searches_total counter
retriever_searches_total{method="vector"} 5234
retriever_searches_total{method="keyword"} 3421
retriever_searches_total{method="hybrid"} 12893

# HELP retriever_search_latency_seconds Search latency
# TYPE retriever_search_latency_seconds histogram
retriever_search_latency_seconds_bucket{le="0.1"} 8234
retriever_search_latency_seconds_bucket{le="0.3"} 15523
retriever_search_latency_seconds_bucket{le="0.5"} 19836

# HELP retriever_avg_relevance_score Average relevance score
# TYPE retriever_avg_relevance_score gauge
retriever_avg_relevance_score 0.78

# HELP retriever_cache_hit_rate Embedding cache hit rate
# TYPE retriever_cache_hit_rate gauge
retriever_cache_hit_rate 0.82
```

---

## Data Models

### SearchRequest

```typescript
type SearchMethod = 'vector' | 'keyword' | 'hybrid';

interface SearchRequest {
  query: string;                // 1-500 chars
  method?: SearchMethod;        // Default: 'hybrid'
  limit?: number;               // 1-100, default: 10
  filters?: {                   // Metadata filters
    [key: string]: any;
  };
  min_relevance_score?: number; // 0.0-1.0, default: 0.5
  include_citations?: boolean;  // Default: true
}
```

### SearchResponse

```typescript
interface SearchResponse {
  results: SearchResult[];
  query: string;
  method_used: SearchMethod;
  total_results: number;
  synthesis?: string;           // Present if include_citations=true
  citations?: string[];         // Source URLs in citation order
}
```

### SearchResult

```typescript
interface SearchResult {
  content: string;              // Retrieved content snippet
  source: string;               // Source URL or identifier
  relevance_score: number;      // 0.0-1.0
  rank: number;                 // 1-indexed result rank
  metadata?: {
    published_date?: string;
    severity?: string;
    cvss_score?: number;
    tags?: string[];
    [key: string]: any;
  };
}
```

---

## Integration Patterns

### Pattern 1: Two-Stage Retrieval (Retrieval + Rerank)

First retrieve many candidates, then rerank for precision.

```python
from octollm_sdk import RetrieverClient

client = RetrieverClient(bearer_token="service_token_abc123")

async def two_stage_search(query: str):
    # Stage 1: Retrieve 50 candidates (high recall)
    stage1 = await client.search({
        "query": query,
        "method": "hybrid",
        "limit": 50,
        "min_relevance_score": 0.3,  # Low threshold
        "include_citations": False   # Skip synthesis
    })

    # Stage 2: Rerank with cross-encoder (high precision)
    # Rerank top 50 → top 10
    reranked = rerank_with_cross_encoder(query, stage1.results)

    # Stage 3: Synthesize final results
    synthesis = await synthesize_results(query, reranked[:10])

    return {
        "results": reranked[:10],
        "synthesis": synthesis
    }
```

### Pattern 2: Iterative Query Expansion

If initial results are poor, expand query and retry.

```typescript
import { RetrieverClient } from 'octollm-sdk';

const client = new RetrieverClient({ bearerToken: '...' });

async function expandingSearch(
  query: string,
  minResults: number = 5
): Promise<SearchResponse> {
  let response = await client.search({ query, method: 'hybrid', limit: 10 });

  // If too few high-quality results, expand query
  if (response.results.filter(r => r.relevance_score > 0.7).length < minResults) {
    console.log('Expanding query for better results...');

    // Add synonyms or related terms (not shown: LLM-generated)
    const expandedQuery = `${query} OR related_terms`;

    response = await client.search({
      query: expandedQuery,
      method: 'hybrid',
      limit: 20,
      min_relevance_score: 0.6
    });
  }

  return response;
}
```

### Pattern 3: Aggregated Multi-Query Search

Search multiple related queries and aggregate results.

```python
from octollm_sdk import RetrieverClient
from collections import defaultdict

client = RetrieverClient(bearer_token="service_token_abc123")

async def multi_query_search(queries: list[str]):
    # Execute searches in parallel
    results = await asyncio.gather(*[
        client.search({
            "query": q,
            "method": "hybrid",
            "limit": 10,
            "include_citations": False
        })
        for q in queries
    ])

    # Aggregate and deduplicate by source
    seen_sources = set()
    aggregated = []

    for response in results:
        for result in response.results:
            if result.source not in seen_sources:
                aggregated.append(result)
                seen_sources.add(result.source)

    # Sort by relevance
    aggregated.sort(key=lambda r: r.relevance_score, reverse=True)

    return aggregated[:10]  # Top 10 unique results

# Example: Comprehensive CVE research
queries = [
    "nginx CVE-2024 vulnerabilities",
    "nginx security advisories 2024",
    "nginx HTTP/2 exploits"
]
results = await multi_query_search(queries)
```

### Pattern 4: Metadata-Driven Filtering

Use metadata filters to narrow down large result sets.

```typescript
import { RetrieverClient } from 'octollm-sdk';

const client = new RetrieverClient({ bearerToken: '...' });

async function searchWithDynamicFilters(
  query: string,
  userPreferences: any
): Promise<SearchResponse> {
  const filters: Record<string, any> = {};

  // Build filters from user preferences
  if (userPreferences.onlyRecent) {
    filters.published_after = new Date(Date.now() - 30 * 86400000)
      .toISOString()
      .split('T')[0];
  }

  if (userPreferences.severityThreshold) {
    filters.severity = ['high', 'critical'];
  }

  if (userPreferences.preferredSources) {
    filters.source = userPreferences.preferredSources;
  }

  return await client.search({
    query,
    method: 'hybrid',
    limit: 10,
    filters,
    min_relevance_score: 0.6
  });
}
```

---

## Performance Characteristics

| Scenario | P50 | P95 | P99 | Max | Notes |
|----------|-----|-----|-----|-----|-------|
| Vector Search (no synthesis) | 120ms | 250ms | 400ms | 800ms | Embedding + Qdrant |
| Keyword Search (no synthesis) | 80ms | 180ms | 300ms | 600ms | BM25 full-text |
| Hybrid Search (no synthesis) | 200ms | 400ms | 600ms | 1.2s | Vector + keyword + rerank |
| With Synthesis | +150ms | +300ms | +500ms | +1s | LLM summary generation |

### Latency Optimization Tips

1. **Cache Embeddings**: Reuse embeddings for identical queries (82% hit rate typical)
2. **Skip Synthesis**: Set `include_citations=false` for 2-3x faster results
3. **Reduce Limit**: Fewer results = faster reranking (limit=5 is 2x faster than limit=50)
4. **Use Keyword Search**: For exact matches, keyword search is 40% faster than hybrid
5. **Parallel Queries**: Use asyncio/Promise.all for multiple independent searches

### Index Size vs Latency

| Documents | Vector Search | Keyword Search | Hybrid Search |
|-----------|---------------|----------------|---------------|
| 10K | 80ms | 40ms | 150ms |
| 100K | 120ms | 70ms | 200ms |
| 1M | 180ms | 110ms | 300ms |
| 10M | 300ms | 180ms | 500ms |

---

## Troubleshooting

### Issue 1: Low Relevance Scores (<0.50)

**Symptoms**: All results have relevance_score < 0.50, synthesis is poor quality

**Possible Causes**:
- Query too vague or ambiguous
- Knowledge base missing relevant documents
- Embedding model mismatch

**Solutions**:
```python
# Make query more specific
# Bad: "vulnerabilities"
# Good: "SQL injection vulnerabilities in Python Flask applications"

# Lower threshold for exploratory search
response = await client.search({
    "query": "vulnerabilities",
    "min_relevance_score": 0.3,  # Lower threshold
    "limit": 20
})

# Check if knowledge base has relevant content
# (Verify index contains expected sources)
```

### Issue 2: Slow Search (>1s latency)

**Symptoms**: Search latency consistently >1 second

**Possible Causes**:
- Large result limit (e.g., limit=100)
- Synthesis enabled (adds 150-500ms)
- Vector database overloaded

**Solutions**:
```bash
# Reduce limit
# limit=10 instead of limit=100

# Skip synthesis
"include_citations": false

# Check vector database performance
kubectl logs -l app=qdrant | grep latency

# Scale retriever horizontally
kubectl scale deployment retriever --replicas=5

# Monitor metrics
curl http://retriever:8004/metrics | grep retriever_search_latency
```

### Issue 3: Missing Recent Documents

**Symptoms**: Recent CVEs/advisories not appearing in results

**Possible Causes**:
- Index not updated recently
- Embedding cache stale
- Ingestion pipeline delayed

**Solutions**:
```bash
# Check index freshness
# (Query vector database for most recent document)

# Trigger reindexing (implementation-specific)
# POST /admin/reindex (admin endpoint, not documented here)

# Use keyword search for very recent content
# (Keyword index updates faster than vector index)
response = await client.search({
    "query": "CVE-2024-12345",
    "method": "keyword",  # Faster index updates
    "filters": {
        "published_after": "2024-11-01"
    }
})
```

### Issue 4: Synthesis Contains Hallucinations

**Symptoms**: Synthesized summary includes information not in results

**Possible Causes**:
- LLM generating content beyond retrieved context
- Low-quality results (relevance < 0.60)
- Synthesis prompt needs tuning

**Solutions**:
```python
# Increase relevance threshold
response = await client.search({
    "query": "nginx vulnerabilities",
    "min_relevance_score": 0.7,  # Higher threshold
    "limit": 5  # Fewer, higher-quality results
})

# Verify citations match content
for i, citation in enumerate(response.citations, 1):
    print(f"[{i}] {citation}")
    # Check if citation appears in synthesis

# Disable synthesis and generate your own
response = await client.search({
    "query": "...",
    "include_citations": False
})
# Generate custom summary from response.results
```

### Issue 5: Vector Database Connection Errors

**Symptoms**: 500 errors with "Vector database connection failed"

**Possible Causes**:
- Qdrant/Weaviate service down
- Network connectivity issues
- Authentication misconfigured

**Solutions**:
```bash
# Check vector database health
kubectl get pods -l app=qdrant
kubectl logs -l app=qdrant

# Test connection manually
curl http://qdrant:6333/collections

# Verify environment variables in Retriever
kubectl get deployment retriever -o yaml | grep VECTOR_DB

# Restart Retriever if config changed
kubectl rollout restart deployment retriever
```

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Orchestrator API](./orchestrator.md)
- [Planner Arm API](./planner.md)
- [OpenAPI Specification](../openapi/retriever.yaml)

---

## Support

For issues with the Retriever Arm:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `kubectl logs -l app=retriever`
3. Check metrics: `curl http://retriever:8004/metrics`
4. File issue: https://github.com/octollm/octollm/issues
