# RetrievalResult Schema Reference

## Overview

The **RetrievalResult** (also called `SearchResponse`) schema represents the output from the Retriever arm after performing knowledge base searches. It includes ranked results, relevance scores, optional LLM-generated synthesis, and citations for Retrieval-Augmented Generation (RAG) workflows.

**Used By**: Retriever Arm (output), Orchestrator (for RAG), Coder Arm (for context)
**Primary Endpoint**: `POST /search`
**Format**: JSON

---

## Structure

### RetrievalResult (SearchResponse)

Complete search response with results, synthesis, and citations.

```typescript
interface RetrievalResult {
  results: SearchResult[];          // Required: Ordered list of results
  query: string;                    // Required: Original query (echo)
  method_used: SearchMethod;        // Required: Method used
  total_results: number;            // Required: Number of results
  synthesis?: string;               // Optional: LLM summary with citations
  citations?: string[];             // Optional: Source URLs in citation order
  metadata?: RetrievalMetadata;     // Optional: Additional info
}

interface SearchResult {
  content: string;                  // Required: Retrieved content
  source: string;                   // Required: Source URL or identifier
  relevance_score: number;          // Required: 0.0-1.0 relevance
  rank: number;                     // Required: 1-indexed rank
  metadata?: ResultMetadata;        // Optional: Additional metadata
}

type SearchMethod = 'vector' | 'keyword' | 'hybrid';

interface RetrievalMetadata {
  search_duration_ms: number;       // Search execution time
  synthesis_duration_ms?: number;   // Synthesis generation time
  vector_model?: string;            // Embedding model used
  database_used: string;            // Vector DB (Qdrant, Weaviate, etc.)
  reranked: boolean;                // Whether results were reranked
}

interface ResultMetadata {
  title?: string;                   // Document title
  date?: string;                    // Publication date (ISO 8601)
  author?: string;                  // Author name
  language?: string;                // Document language
  severity?: string;                // Severity (for CVEs, vulnerabilities)
  cvss_score?: number;              // CVSS score (0-10)
  tags?: string[];                  // Tags/categories
  snippet_start?: number;           // Character offset in original doc
  snippet_length?: number;          // Length of content snippet
  [key: string]: any;               // Additional custom metadata
}
```

---

## Field Definitions

### `results` (required)

**Type**: array of SearchResult objects
**Description**: Ordered list of search results, ranked by relevance (highest first)

**Ordering**:
- Results are sorted by `relevance_score` in descending order
- Rank 1 = most relevant result
- Empty array if no results match criteria

**Example**:
```json
{
  "results": [
    {
      "content": "Use parameterized queries to prevent SQL injection...",
      "source": "https://owasp.org/sql-injection-prevention",
      "relevance_score": 0.94,
      "rank": 1
    },
    {
      "content": "Input validation with allowlists is another defense...",
      "source": "https://portswigger.net/web-security/sql-injection",
      "relevance_score": 0.87,
      "rank": 2
    }
  ]
}
```

---

### `results[].content` (required)

**Type**: string
**Constraints**: 1-5000 characters
**Description**: Retrieved content snippet from the source document

**Format**:
- Plain text (no HTML markup)
- Trimmed to relevant context window
- May be truncated with "..." if exceeds max length
- Surrounding context included for clarity

**Examples**:
```json
// Well-formed content
"Use parameterized queries to prevent SQL injection. This technique separates SQL code from user input, making injection impossible. Example: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"

// Truncated content
"Nginx HTTP/2 buffer overflow vulnerability allows remote code execution... [see full advisory for details]"
```

---

### `results[].source` (required)

**Type**: string
**Constraints**: Valid URL or identifier
**Description**: Source URL or document identifier where content was retrieved

**Format**:
- Full URLs (https://example.com/path)
- Internal document IDs (doc_abc123)
- File paths (documents/security/vuln-report.pdf)

**Examples**:
```json
"https://nvd.nist.gov/vuln/detail/CVE-2024-12345"
"https://owasp.org/sql-injection-prevention"
"doc_nginx_security_2024_001"
"documents/vulnerabilities/nginx-http2.pdf"
```

---

### `results[].relevance_score` (required)

**Type**: number
**Constraints**: 0.0-1.0
**Description**: Relevance score indicating how well the result matches the query

**Scoring Methodology**:

**Vector Search**:
- Cosine similarity between query embedding and document embedding
- Range: 0.0 (orthogonal) to 1.0 (identical)

**Keyword Search**:
- TF-IDF or BM25 scoring, normalized to 0-1 range
- Factors: term frequency, inverse document frequency, document length

**Hybrid Search**:
- Weighted combination of vector and keyword scores
- Default: 0.7 × vector_score + 0.3 × keyword_score

**Score Interpretation**:
| Range | Interpretation | Quality |
|-------|----------------|---------|
| 0.9-1.0 | Excellent match | Highly relevant, exact match likely |
| 0.7-0.89 | Good match | Relevant, on-topic |
| 0.5-0.69 | Fair match | Somewhat relevant, may need filtering |
| 0.3-0.49 | Weak match | Tangentially related |
| 0.0-0.29 | Poor match | Likely irrelevant |

**Example**:
```json
{
  "results": [
    {"relevance_score": 0.94, "rank": 1},  // Excellent
    {"relevance_score": 0.87, "rank": 2},  // Good
    {"relevance_score": 0.62, "rank": 3}   // Fair
  ]
}
```

---

### `results[].rank` (required)

**Type**: integer
**Constraints**: >= 1
**Description**: 1-indexed rank of the result in the ordered list

**Ranking**:
- Rank 1 = highest relevance_score
- Sequential ordering (1, 2, 3, ...)
- No gaps even if scores are identical

**Example**:
```json
[
  {"rank": 1, "relevance_score": 0.94},
  {"rank": 2, "relevance_score": 0.87},
  {"rank": 3, "relevance_score": 0.87}  // Same score, next rank
]
```

---

### `results[].metadata` (optional)

**Type**: object
**Description**: Additional structured information about the result

**Common Metadata Fields**:

**Document Metadata**:
- `title`: Document title
- `date`: Publication date (ISO 8601)
- `author`: Author name
- `language`: Document language (ISO 639-1 code)

**Security Metadata** (for CVEs, vulnerabilities):
- `severity`: none | low | medium | high | critical
- `cvss_score`: 0.0-10.0 CVSS score
- `cve_id`: CVE identifier (e.g., "CVE-2024-12345")
- `affected_versions`: Affected software versions

**Content Metadata**:
- `tags`: Array of tags/categories
- `snippet_start`: Character offset in original document
- `snippet_length`: Length of content snippet

**Example**:
```json
{
  "metadata": {
    "title": "Nginx HTTP/2 Buffer Overflow Vulnerability",
    "date": "2024-02-15T10:30:00Z",
    "author": "NIST NVD",
    "language": "en",
    "severity": "high",
    "cvss_score": 7.5,
    "cve_id": "CVE-2024-12345",
    "affected_versions": "< 1.24.0",
    "tags": ["nginx", "http2", "buffer-overflow", "rce"]
  }
}
```

---

### `query` (required)

**Type**: string
**Description**: Original search query echoed back in the response

**Purpose**:
- Confirms query was processed correctly
- Useful for logging and debugging
- Enables query correlation

**Example**:
```json
{
  "query": "What are common nginx vulnerabilities?",
  "results": [...]
}
```

---

### `method_used` (required)

**Type**: enum - `'vector'` | `'keyword'` | `'hybrid'`
**Description**: Search method that was actually used

**Method Characteristics**:

**vector** - Semantic similarity search
- Uses embedding models (e.g., text-embedding-ada-002)
- Finds semantically similar content
- Best for: conceptual queries, synonyms, paraphrasing

**keyword** - Traditional keyword matching
- Uses TF-IDF or BM25 algorithms
- Finds exact or fuzzy keyword matches
- Best for: specific terms, product names, IDs

**hybrid** - Combination of vector and keyword
- Weighted combination (default: 70% vector, 30% keyword)
- Reranking step to merge results
- Best for: most queries, balance of precision and recall

**Example**:
```json
{
  "query": "SQL injection prevention",
  "method": "vector",  // Requested method
  "method_used": "hybrid"  // Actually used (auto-upgraded)
}
```

**Note**: The system may auto-upgrade to `hybrid` if `vector` or `keyword` alone returns few results.

---

### `total_results` (required)

**Type**: integer
**Constraints**: >= 0
**Description**: Total number of results returned (may be less than requested `limit` if filtered)

**Examples**:
```json
{"total_results": 10}  // Returned 10 results
{"total_results": 0}   // No matching results
```

---

### `synthesis` (optional)

**Type**: string
**Constraints**: 100-2000 characters
**Description**: LLM-generated summary of the results with numbered citations

**Format**:
- Plain text summary
- Inline citations [1], [2], [3] corresponding to `citations` array
- Synthesizes information from multiple sources
- 2-5 sentences typical

**Generation**:
- Only generated if `include_citations: true` in request
- Uses GPT-3.5-turbo or similar model
- Costs ~500-1500 tokens per synthesis

**Example**:
```json
{
  "synthesis": "Nginx has several known vulnerabilities including buffer overflow in HTTP/2 [1] and remote code execution via malformed headers [2]. The HTTP/2 buffer overflow affects versions prior to 1.24.0, with a CVSS score of 7.5. The RCE vulnerability is more critical with CVSS 9.8 and affects versions below 1.24.1.",
  "citations": [
    "https://nvd.nist.gov/vuln/detail/CVE-2024-12345",
    "https://security.nginx.org/advisories/2024/001"
  ]
}
```

**When Not Present**:
- `include_citations: false` in request
- No results to synthesize
- Synthesis generation failed (fallback to empty)

---

### `citations` (optional)

**Type**: array of strings (URLs)
**Description**: Source URLs in citation order matching [1], [2], [3] in synthesis

**Format**:
- Array index 0 = citation [1]
- Array index 1 = citation [2]
- etc.

**Example**:
```json
{
  "synthesis": "SQL injection can be prevented using parameterized queries [1], input validation [2], and ORM frameworks [3].",
  "citations": [
    "https://owasp.org/sql-injection-prevention",
    "https://portswigger.net/web-security/sql-injection",
    "https://docs.sqlalchemy.org/en/14/core/tutorial.html"
  ]
}
```

---

### `metadata` (optional)

**Type**: object
**Description**: Additional information about the search process

**Common Metadata Fields**:
- `search_duration_ms`: Search execution time (vector/keyword search)
- `synthesis_duration_ms`: Synthesis generation time (LLM call)
- `vector_model`: Embedding model used (e.g., "text-embedding-ada-002")
- `database_used`: Vector database (e.g., "qdrant", "weaviate")
- `reranked`: Whether results were reranked after hybrid search

**Example**:
```json
{
  "metadata": {
    "search_duration_ms": 450,
    "synthesis_duration_ms": 1200,
    "vector_model": "text-embedding-ada-002",
    "database_used": "qdrant",
    "reranked": true
  }
}
```

---

## Complete Examples

### Example 1: Hybrid Search with Synthesis

```json
{
  "results": [
    {
      "content": "Nginx HTTP/2 buffer overflow vulnerability (CVE-2024-12345) allows remote attackers to execute arbitrary code. Affects versions prior to 1.24.0. CVSS score: 7.5 (High).",
      "source": "https://nvd.nist.gov/vuln/detail/CVE-2024-12345",
      "relevance_score": 0.92,
      "rank": 1,
      "metadata": {
        "title": "CVE-2024-12345",
        "date": "2024-02-15T10:30:00Z",
        "severity": "high",
        "cvss_score": 7.5,
        "cve_id": "CVE-2024-12345",
        "affected_versions": "< 1.24.0"
      }
    },
    {
      "content": "Remote code execution via malformed HTTP headers in Nginx. This vulnerability (CVE-2024-67890) is critical with CVSS 9.8, affecting versions below 1.24.1.",
      "source": "https://security.nginx.org/advisories/2024/001",
      "relevance_score": 0.88,
      "rank": 2,
      "metadata": {
        "title": "Nginx RCE Advisory",
        "date": "2024-03-01T14:15:00Z",
        "severity": "critical",
        "cvss_score": 9.8,
        "cve_id": "CVE-2024-67890",
        "affected_versions": "< 1.24.1"
      }
    }
  ],
  "query": "What are common nginx vulnerabilities?",
  "method_used": "hybrid",
  "total_results": 2,
  "synthesis": "Nginx has several known vulnerabilities including buffer overflow in HTTP/2 [1] and remote code execution via malformed headers [2]. The HTTP/2 buffer overflow affects versions prior to 1.24.0, with a CVSS score of 7.5. The RCE vulnerability is more critical with CVSS 9.8 and affects versions below 1.24.1.",
  "citations": [
    "https://nvd.nist.gov/vuln/detail/CVE-2024-12345",
    "https://security.nginx.org/advisories/2024/001"
  ],
  "metadata": {
    "search_duration_ms": 450,
    "synthesis_duration_ms": 1200,
    "vector_model": "text-embedding-ada-002",
    "database_used": "qdrant",
    "reranked": true
  }
}
```

---

### Example 2: Vector Search without Synthesis

```json
{
  "results": [
    {
      "content": "Use parameterized queries to prevent SQL injection. This technique separates SQL code from user input, making injection impossible. Example: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
      "source": "https://owasp.org/sql-injection-prevention",
      "relevance_score": 0.94,
      "rank": 1,
      "metadata": {
        "title": "SQL Injection Prevention Cheat Sheet",
        "date": "2024-01-10T09:00:00Z",
        "author": "OWASP",
        "language": "en",
        "tags": ["sql-injection", "prevention", "security"]
      }
    },
    {
      "content": "Input validation with allowlists is another defense against SQL injection. Only allow known-safe characters and reject all others.",
      "source": "https://portswigger.net/web-security/sql-injection",
      "relevance_score": 0.87,
      "rank": 2,
      "metadata": {
        "title": "SQL Injection",
        "author": "PortSwigger",
        "language": "en",
        "tags": ["sql-injection", "input-validation"]
      }
    },
    {
      "content": "ORM frameworks like SQLAlchemy automatically use parameterized queries, providing built-in SQL injection protection.",
      "source": "https://docs.sqlalchemy.org/en/14/core/tutorial.html",
      "relevance_score": 0.82,
      "rank": 3,
      "metadata": {
        "title": "SQLAlchemy Core Tutorial",
        "language": "en",
        "tags": ["orm", "sqlalchemy", "python"]
      }
    }
  ],
  "query": "SQL injection prevention techniques",
  "method_used": "vector",
  "total_results": 3,
  "metadata": {
    "search_duration_ms": 320,
    "vector_model": "text-embedding-ada-002",
    "database_used": "qdrant",
    "reranked": false
  }
}
```

---

### Example 3: Keyword Search with Filters

```json
{
  "results": [
    {
      "content": "XSS attack vectors include stored XSS, reflected XSS, and DOM-based XSS. All three types can execute malicious JavaScript in the victim's browser.",
      "source": "https://owasp.org/xss-attack-vectors",
      "relevance_score": 0.89,
      "rank": 1,
      "metadata": {
        "title": "Cross-Site Scripting (XSS) Attack Vectors",
        "date": "2024-06-01T12:00:00Z",
        "severity": "high",
        "tags": ["xss", "javascript", "web-security"]
      }
    },
    {
      "content": "DOM-based XSS occurs when JavaScript reads from the DOM and writes to a dangerous sink like innerHTML without proper sanitization.",
      "source": "https://portswigger.net/web-security/cross-site-scripting/dom-based",
      "relevance_score": 0.76,
      "rank": 2,
      "metadata": {
        "title": "DOM-based XSS",
        "date": "2024-05-15T10:30:00Z",
        "severity": "medium",
        "tags": ["xss", "dom", "javascript"]
      }
    }
  ],
  "query": "XSS attack vectors",
  "method_used": "keyword",
  "total_results": 2,
  "metadata": {
    "search_duration_ms": 180,
    "database_used": "qdrant",
    "reranked": false
  }
}
```

---

### Example 4: No Results

```json
{
  "results": [],
  "query": "blahblahblah nonexistent query xyz123",
  "method_used": "hybrid",
  "total_results": 0,
  "metadata": {
    "search_duration_ms": 250,
    "vector_model": "text-embedding-ada-002",
    "database_used": "qdrant",
    "reranked": false
  }
}
```

---

## Usage Patterns

### Pattern 1: RAG (Retrieval-Augmented Generation)

Use retrieval results as context for code generation or analysis.

```python
from octollm_sdk import RetrieverClient, CoderClient

retriever = RetrieverClient(bearer_token="service_token_abc123")
coder = CoderClient(bearer_token="service_token_abc123")

# 1. Retrieve relevant security knowledge
retrieval_result = await retriever.search({
    "query": "How to prevent SQL injection in Python?",
    "method": "hybrid",
    "limit": 5,
    "include_citations": True
})

# 2. Use synthesis as context for code generation
code_result = await coder.process_code({
    "request_type": "generate",
    "language": "python",
    "instruction": f"""
        Create a secure database query function.

        Security Context:
        {retrieval_result.synthesis}

        Sources: {', '.join(retrieval_result.citations)}
    """,
    "constraints": ["Follow OWASP guidelines", "Use parameterized queries"]
})

print("Generated code:")
print(code_result.code)
```

---

### Pattern 2: Filtering by Relevance Score

Only accept high-confidence results.

```typescript
function filterHighConfidenceResults(
  result: RetrievalResult,
  minScore: number = 0.7
): SearchResult[] {
  return result.results.filter(r => r.relevance_score >= minScore);
}

// Example usage
const retrieval = await retrieverClient.search({
  query: "nginx CVE 2024",
  method: "hybrid",
  limit: 20
});

const highConfidence = filterHighConfidenceResults(retrieval, 0.8);
console.log(`${highConfidence.length}/${retrieval.total_results} results are high-confidence`);
```

---

### Pattern 3: Citation Extraction for Reports

Extract citations for inclusion in security reports.

```python
def format_citations(result: RetrievalResult) -> str:
    """Format citations for inclusion in reports."""
    if not result.citations:
        return "No citations available"

    citations_text = []
    for i, url in enumerate(result.citations, start=1):
        # Try to get title from metadata
        matching_result = next(
            (r for r in result.results if r.source == url),
            None
        )
        title = matching_result.metadata.get("title", url) if matching_result else url
        citations_text.append(f"[{i}] {title}\n    {url}")

    return "\n".join(citations_text)

# Example usage
retrieval = await retriever.search({
    "query": "nginx vulnerabilities 2024",
    "method": "hybrid",
    "limit": 10,
    "include_citations": True
})

print("=== SUMMARY ===")
print(retrieval.synthesis)
print("\n=== SOURCES ===")
print(format_citations(retrieval))

# Output:
# === SUMMARY ===
# Nginx has several known vulnerabilities...
#
# === SOURCES ===
# [1] CVE-2024-12345
#     https://nvd.nist.gov/vuln/detail/CVE-2024-12345
# [2] Nginx RCE Advisory
#     https://security.nginx.org/advisories/2024/001
```

---

### Pattern 4: Grouping Results by Metadata

Group results by severity, date, or other metadata.

```typescript
function groupBySeverity(result: RetrievalResult): Record<string, SearchResult[]> {
  const groups: Record<string, SearchResult[]> = {
    critical: [],
    high: [],
    medium: [],
    low: [],
    none: []
  };

  for (const r of result.results) {
    const severity = r.metadata?.severity || 'none';
    if (groups[severity]) {
      groups[severity].push(r);
    }
  }

  return groups;
}

// Example usage
const retrieval = await retrieverClient.search({
  query: "web application vulnerabilities",
  method: "hybrid",
  limit: 50,
  filters: {
    published_after: "2024-01-01"
  }
});

const bySeverity = groupBySeverity(retrieval);
console.log("Results by severity:");
for (const [severity, results] of Object.entries(bySeverity)) {
  if (results.length > 0) {
    console.log(`  ${severity.toUpperCase()}: ${results.length}`);
  }
}
```

---

## Best Practices

### 1. Always Check `total_results` Before Processing

**Why**: Empty results need different handling
**How**: Check count first

```typescript
if (result.total_results === 0) {
  console.log("No results found, try broader query");
  return;
}

// Process results
result.results.forEach(r => console.log(r.content));
```

---

### 2. Filter by Relevance Score for Quality

**Why**: Low-relevance results are often noise
**How**: Set minimum threshold

```python
MIN_RELEVANCE = 0.7
high_quality = [r for r in result.results if r.relevance_score >= MIN_RELEVANCE]
```

---

### 3. Use Synthesis for Quick Summaries, Results for Details

**Why**: Synthesis is concise but loses detail
**How**: Show synthesis first, results on demand

```typescript
// Show synthesis for overview
console.log("Summary:", result.synthesis);

// Show detailed results on request
if (userWantsDetails) {
  result.results.forEach(r => {
    console.log(`\n[${r.rank}] ${r.metadata?.title || 'Untitled'}`);
    console.log(`Relevance: ${r.relevance_score.toFixed(2)}`);
    console.log(r.content);
    console.log(`Source: ${r.source}`);
  });
}
```

---

### 4. Leverage Metadata for Advanced Filtering

**Why**: Metadata enables precise filtering
**How**: Filter after retrieval based on metadata

```python
# Filter to only critical CVEs from 2024
critical_2024 = [
    r for r in result.results
    if r.metadata.get("severity") == "critical"
    and r.metadata.get("date", "").startswith("2024")
]
```

---

## Related Documentation

- [Retriever Arm API Reference](../services/retriever.md)
- [TaskContract Schema](./TaskContract.md)
- [RAG Integration Guide](../../guides/rag-integration.md) (coming soon)
- [Vector Search Best Practices](../../guides/vector-search.md) (coming soon)

---

## JSON Schema

Complete JSON Schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RetrievalResult",
  "type": "object",
  "required": ["results", "query", "method_used", "total_results"],
  "properties": {
    "results": {
      "type": "array",
      "items": {"$ref": "#/definitions/SearchResult"},
      "description": "Ordered list of search results"
    },
    "query": {
      "type": "string",
      "description": "Original query (echo)"
    },
    "method_used": {
      "type": "string",
      "enum": ["vector", "keyword", "hybrid"],
      "description": "Search method used"
    },
    "total_results": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of results returned"
    },
    "synthesis": {
      "type": "string",
      "minLength": 100,
      "maxLength": 2000,
      "description": "LLM-generated summary with citations"
    },
    "citations": {
      "type": "array",
      "items": {"type": "string", "format": "uri"},
      "description": "Source URLs in citation order"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "search_duration_ms": {"type": "number"},
        "synthesis_duration_ms": {"type": "number"},
        "vector_model": {"type": "string"},
        "database_used": {"type": "string"},
        "reranked": {"type": "boolean"}
      }
    }
  },
  "definitions": {
    "SearchResult": {
      "type": "object",
      "required": ["content", "source", "relevance_score", "rank"],
      "properties": {
        "content": {
          "type": "string",
          "minLength": 1,
          "maxLength": 5000,
          "description": "Retrieved content snippet"
        },
        "source": {
          "type": "string",
          "description": "Source URL or identifier"
        },
        "relevance_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Relevance score (0-1)"
        },
        "rank": {
          "type": "integer",
          "minimum": 1,
          "description": "1-indexed result rank"
        },
        "metadata": {
          "type": "object",
          "additionalProperties": true,
          "description": "Additional metadata"
        }
      }
    }
  }
}
```
