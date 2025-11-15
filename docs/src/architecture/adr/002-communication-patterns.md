# ADR-002: Communication Patterns

**Status**: Accepted
**Date**: 2025-11-10
**Decision Makers**: Architecture Team
**Consulted**: Engineering Team

## Context

OctoLLM has multiple components that need to communicate:
- **Reflex Layer** → **Orchestrator** (request preprocessing)
- **Orchestrator** → **Arms** (task execution)
- **Arms** → **Arms** (collaborative tasks)
- **Arms** → **Memory Systems** (knowledge retrieval/storage)
- **Components** → **External Services** (LLM APIs, webhooks)

Communication patterns must support:
- Synchronous request-response for task execution
- Asynchronous event notifications
- Low latency (<100ms for internal calls)
- Reliability and fault tolerance
- Observability and tracing
- Flexible routing and load balancing

## Decision

We will use the following communication patterns:

### 1. HTTP/REST for Synchronous Operations

**Use For**:
- Reflex Layer → Orchestrator
- Orchestrator → Arms
- Arms → Memory Systems
- External API integrations

**Protocol**: HTTP/1.1 or HTTP/2
**Format**: JSON
**Authentication**: JWT tokens with capability scopes

**Example**:
```python
# Orchestrator calling Coder Arm
async def execute_code_task(task: TaskContract) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://coder-arm:8102/execute",
            json=task.dict(),
            headers={
                "Authorization": f"Bearer {capability_token}",
                "X-Request-ID": request_id
            },
            timeout=30.0
        )
        return response.json()["output"]
```

**Reasons**:
- Universal protocol, widely understood
- Excellent debugging tools
- Native HTTP client libraries
- OpenAPI documentation support
- Load balancer integration
- Request/response tracing

### 2. Redis Pub/Sub for Event Notifications

**Use For**:
- Task completion events
- System health events
- Audit log events
- Cache invalidation signals

**Pattern**: Publish-subscribe
**Channels**: Topic-based routing

**Example**:
```python
# Publisher (Orchestrator)
await redis.publish(
    "events:task:completed",
    json.dumps({
        "task_id": task.task_id,
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat()
    })
)

# Subscriber (Monitoring Service)
pubsub = redis.pubsub()
pubsub.subscribe("events:task:*")

async for message in pubsub.listen():
    if message["type"] == "message":
        event = json.loads(message["data"])
        handle_task_event(event)
```

**Reasons**:
- Decoupled producers and consumers
- No blocking on publisher side
- Multiple subscribers supported
- Built into existing Redis infrastructure
- Low latency (<5ms)
- Simple implementation

### 3. Direct HTTP for Arm-to-Arm Communication

**Use For**:
- Coder Arm → Judge Arm (code validation)
- Planner Arm → Executor Arm (plan execution)
- Retriever Arm → other Arms (knowledge lookup)

**Pattern**: Direct service-to-service HTTP calls
**Discovery**: Kubernetes DNS or service registry

**Example**:
```python
# Coder Arm requesting validation from Judge Arm
async def validate_code(code: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://judge-arm:8103/validate",
            json={"code": code, "language": "python"},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()["is_valid"]
```

**Reasons**:
- Simple and direct
- Low latency
- Easy to trace with request IDs
- No message broker overhead
- Kubernetes service discovery

### 4. WebSocket for Real-Time Updates

**Use For**:
- Live task progress updates to clients
- Streaming LLM responses
- Real-time dashboard data

**Protocol**: WebSocket over HTTP
**Format**: JSON messages

**Example**:
```python
# Server
@app.websocket("/ws/tasks/{task_id}")
async def task_updates(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            update = await get_task_update(task_id)
            await websocket.send_json(update)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("Client disconnected", task_id=task_id)

# Client
async with websocket_connect(f"ws://localhost:8000/ws/tasks/{task_id}") as ws:
    async for message in ws:
        update = json.loads(message)
        print(f"Task progress: {update['progress']}%")
```

**Reasons**:
- Bi-directional communication
- Lower overhead than polling
- Native browser support
- Streaming responses
- Real-time updates

## Consequences

### Positive

1. **Simplicity**:
   - HTTP/REST is familiar to all developers
   - No complex message broker to manage
   - Standard debugging tools work
   - Easy to test and mock

2. **Performance**:
   - HTTP/2 multiplexing reduces overhead
   - Direct calls minimize latency
   - Redis pub/sub is very fast
   - Connection pooling improves efficiency

3. **Observability**:
   - HTTP requests easily traced
   - Standard headers for correlation
   - OpenTelemetry integration
   - Request/response logging

4. **Flexibility**:
   - Can add message broker later if needed
   - Easy to switch between sync and async
   - Support for multiple communication styles
   - Cloud-native patterns

5. **Reliability**:
   - HTTP retries well-understood
   - Circuit breakers easy to implement
   - Timeout handling straightforward
   - Failure modes are clear

### Negative

1. **No Native Message Queue**:
   - No guaranteed delivery
   - No persistent queuing
   - Manual retry logic needed
   - No dead letter queue

2. **Pub/Sub Limitations**:
   - Messages not persisted
   - No acknowledgment mechanism
   - Subscribers must be online
   - No ordering guarantees

3. **Service Discovery**:
   - Requires DNS or service registry
   - Hard-coded URLs in development
   - More complex in multi-cluster setup
   - Need health checks

4. **Scalability Concerns**:
   - HTTP connection overhead at very high scale
   - May need connection pooling tuning
   - Pub/sub doesn't scale horizontally well
   - Load balancing configuration required

### Mitigation Strategies

1. **Reliability**:
   - Implement retry logic with exponential backoff
   - Use circuit breakers for external calls
   - Add request timeouts
   - Idempotent operations where possible

2. **Message Durability**:
   - Use database for critical events
   - Add audit log for important operations
   - Implement task queue for background jobs
   - Consider Kafka for high-volume events (future)

3. **Service Discovery**:
   - Use Kubernetes DNS for production
   - Environment variables for URLs
   - Service mesh for advanced routing (future)
   - Health checks and readiness probes

4. **Performance**:
   - HTTP/2 for multiplexing
   - Connection pooling
   - Response compression
   - Caching where appropriate

## Alternatives Considered

### 1. gRPC for All Communication

**Pros**:
- Better performance than REST
- Strong typing with protobuf
- Bi-directional streaming
- Code generation

**Cons**:
- More complex than HTTP/REST
- Requires protobuf definitions
- Harder to debug
- Less universal tooling
- Steeper learning curve

**Why Rejected**: HTTP/REST simplicity outweighs gRPC performance benefits for our use case.

### 2. Message Broker (RabbitMQ/Kafka)

**Pros**:
- Guaranteed delivery
- Persistent queuing
- Complex routing
- Horizontal scaling
- Decoupling

**Cons**:
- Another component to manage
- More operational complexity
- Higher latency
- Resource overhead
- Overkill for current scale

**Why Rejected**: HTTP/REST with Redis pub/sub sufficient for current needs. Can add later if needed.

### 3. Service Mesh (Istio/Linkerd)

**Pros**:
- Advanced routing
- Automatic retries
- Circuit breakers
- mTLS security
- Observability

**Cons**:
- Complex to setup
- Resource overhead
- Steep learning curve
- Operational burden
- Overkill for current scale

**Why Rejected**: Too complex for initial deployment. May consider for larger deployments.

### 4. GraphQL for All APIs

**Pros**:
- Flexible queries
- Single endpoint
- Strong typing
- Batch requests

**Cons**:
- More complex than REST
- Caching harder
- N+1 query problem
- Learning curve
- Less suitable for internal APIs

**Why Rejected**: REST is simpler and sufficient for our internal APIs.

## Implementation Guidelines

### HTTP Best Practices

1. **Use standard status codes**:
   - 200 OK: Success
   - 201 Created: Resource created
   - 400 Bad Request: Validation error
   - 401 Unauthorized: Authentication required
   - 403 Forbidden: Authorization failed
   - 404 Not Found: Resource doesn't exist
   - 429 Too Many Requests: Rate limit
   - 500 Internal Server Error: Server error
   - 503 Service Unavailable: Service down

2. **Include correlation headers**:
   ```python
   headers = {
       "X-Request-ID": request_id,
       "X-Correlation-ID": correlation_id,
       "Authorization": f"Bearer {token}"
   }
   ```

3. **Set appropriate timeouts**:
   ```python
   timeout = httpx.Timeout(
       connect=5.0,  # Connection timeout
       read=30.0,    # Read timeout
       write=10.0,   # Write timeout
       pool=5.0      # Pool timeout
   )
   ```

4. **Use connection pooling**:
   ```python
   client = httpx.AsyncClient(
       limits=httpx.Limits(
           max_keepalive_connections=20,
           max_connections=100
       )
   )
   ```

### Event Publishing

1. **Event schema**:
   ```python
   {
       "event_type": "task.completed",
       "timestamp": "2025-11-10T10:30:00Z",
       "source": "orchestrator",
       "data": {
           "task_id": "task-123",
           "status": "completed",
           "duration_ms": 1234
       }
   }
   ```

2. **Channel naming**:
   - Format: `<domain>:<entity>:<action>`
   - Examples: `events:task:completed`, `events:arm:registered`

## References

- [HTTP/2 Specification](https://http2.github.io/)
- [REST API Best Practices](https://restfulapi.net/)
- [Redis Pub/Sub Documentation](https://redis.io/topics/pubsub)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [OpenTelemetry](https://opentelemetry.io/)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-05-10 (6 months)
**Related ADRs**: ADR-001, ADR-004, ADR-005
