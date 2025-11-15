# REST API Overview

OctoLLM exposes RESTful APIs for all major components. All APIs follow OpenAPI 3.0 specifications and use JSON for request/response bodies.

## Base URLs

**Local Development**:
- Orchestrator: `http://localhost:8000`
- Reflex Layer: `http://localhost:8001`
- Arms: `http://localhost:80XX` (varies by arm)

**Production**:
- API Gateway: `https://api.octollm.example.com`

## Authentication

**Current**: None (Phase 1 POC)
**Planned**: JWT tokens with role-based access control (Phase 5)

## Common Headers

```http
Content-Type: application/json
Accept: application/json
X-Request-ID: <uuid>  # Optional, for tracing
```

## Orchestrator API

Base URL: `/api/v1`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tasks` | Create new task |
| GET | `/tasks/{task_id}` | Get task status |
| GET | `/tasks` | List all tasks |
| DELETE | `/tasks/{task_id}` | Cancel task |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

[Full Specification](./openapi/orchestrator.md)

## Reflex Layer API

Base URL: `/api/v1`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/check` | Check request (cache + patterns) |
| POST | `/cache` | Store in cache |
| GET | `/cache/{key}` | Retrieve from cache |
| DELETE | `/cache/{key}` | Invalidate cache entry |
| GET | `/stats` | Cache statistics |
| GET | `/health` | Health check |

[Full Specification](./openapi/reflex-layer.md)

## Error Handling

All APIs return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error description",
    "details": {
      "field": "specific_field",
      "constraint": "must be non-empty"
    },
    "request_id": "uuid"
  }
}
```

### Error Codes

- `VALIDATION_ERROR` (400): Invalid request
- `NOT_FOUND` (404): Resource not found
- `TIMEOUT` (408): Request timeout
- `RATE_LIMIT` (429): Too many requests
- `INTERNAL_ERROR` (500): Server error
- `SERVICE_UNAVAILABLE` (503): Dependency down

## Rate Limiting

**Current**: Not implemented (Phase 1)
**Planned**:
- 100 requests/minute per IP (Phase 3)
- 1000 requests/minute for authenticated users

## Pagination

List endpoints support pagination:

```
GET /api/v1/tasks?page=1&page_size=50&sort_by=created_at&order=desc
```

Response includes pagination metadata:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_pages": 10,
    "total_items": 487
  }
}
```

## See Also

- [OpenAPI Specifications](./openapi-specs.md)
- [Component Contracts](./component-contracts.md)
- [Data Models](./data-models.md)
