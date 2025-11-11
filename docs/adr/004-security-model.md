# ADR-004: Security Model

**Status**: Accepted
**Date**: 2025-11-10
**Decision Makers**: Security Team, Architecture Team
**Consulted**: Compliance Team, Engineering Team

## Context

OctoLLM processes user tasks that may contain:
- Sensitive data (PII, credentials, proprietary information)
- Potentially malicious input (injections, exploits)
- Cross-user data that must be isolated
- LLM API requests that could be costly or unsafe

Security requirements:
- **Prevent PII leakage**: Detect and sanitize PII before storage
- **Isolation**: Prevent data leakage between users/tasks
- **Input validation**: Protect against injections and exploits
- **Least privilege**: Limit component access to minimum needed
- **Auditability**: Track all operations for compliance
- **Defense in depth**: Multiple security layers

Threat model:
- Malicious users attempting to access others' data
- Accidental PII exposure through LLM APIs
- Prompt injection attacks
- Resource exhaustion attacks
- Insider threats from compromised components

## Decision

We will implement a **capability-based security model** with multiple defensive layers:

### 1. Capability Tokens (JWT)

**Purpose**: Fine-grained authorization based on capabilities
**Format**: JWT with capability scopes
**Issuance**: Orchestrator issues tokens with specific scopes
**Validation**: Each component validates tokens before processing

**Token Structure**:
```json
{
  "sub": "user-123",
  "iss": "octollm-orchestrator",
  "exp": 1699999999,
  "capabilities": {
    "task:read": ["task-456"],
    "task:execute": ["task-456"],
    "arm:invoke": ["coder", "executor"],
    "memory:read": ["global"],
    "memory:write": []
  },
  "context": {
    "task_id": "task-456",
    "user_id": "user-123",
    "session_id": "session-789"
  }
}
```

**Example**:
```python
from jose import jwt

def create_capability_token(
    user_id: str,
    task_id: str,
    capabilities: Dict[str, List[str]],
    expiry_minutes: int = 30
) -> str:
    """Create capability token for task execution."""
    payload = {
        "sub": user_id,
        "iss": "octollm-orchestrator",
        "exp": datetime.utcnow() + timedelta(minutes=expiry_minutes),
        "capabilities": capabilities,
        "context": {
            "task_id": task_id,
            "user_id": user_id
        }
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

async def verify_capability(
    token: str,
    required_capability: str,
    resource_id: Optional[str] = None
) -> bool:
    """Verify token has required capability."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        capabilities = payload.get("capabilities", {})
        allowed = capabilities.get(required_capability, [])

        if resource_id:
            return resource_id in allowed
        return len(allowed) > 0

    except jwt.JWTError:
        return False
```

### 2. PII Detection (Reflex Layer)

**Purpose**: Detect and sanitize PII before processing
**Location**: Reflex Layer (first line of defense)
**Method**: Regex patterns + optional ML model

**Patterns**:
```rust
lazy_static! {
    static ref EMAIL: Regex = Regex::new(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ).unwrap();

    static ref SSN: Regex = Regex::new(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ).unwrap();

    static ref CREDIT_CARD: Regex = Regex::new(
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
    ).unwrap();

    static ref PHONE: Regex = Regex::new(
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
    ).unwrap();
}

pub struct PiiDetector {
    patterns: Vec<(String, Regex)>,
}

impl PiiDetector {
    pub fn detect(&self, text: &str) -> Vec<PiiMatch> {
        let mut matches = Vec::new();

        for (name, pattern) in &self.patterns {
            for capture in pattern.captures_iter(text) {
                matches.push(PiiMatch {
                    pattern_name: name.clone(),
                    matched_text: capture[0].to_string(),
                    start: capture.get(0).unwrap().start(),
                    end: capture.get(0).unwrap().end(),
                });
            }
        }

        matches
    }

    pub fn sanitize(&self, text: &str) -> String {
        let mut result = text.to_string();

        for (_, pattern) in &self.patterns {
            result = pattern.replace_all(&result, "[REDACTED]").to_string();
        }

        result
    }
}
```

### 3. Input Validation

**Layers**:
1. Schema validation (Pydantic)
2. Business logic validation
3. Security validation (injection detection)

**Example**:
```python
from pydantic import BaseModel, Field, validator

class TaskRequest(BaseModel):
    """Validated task request."""

    description: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Task description"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Task priority (1-10)"
    )
    timeout: int = Field(
        default=300,
        gt=0,
        le=3600,
        description="Task timeout in seconds"
    )

    @validator('description')
    def validate_description(cls, v: str) -> str:
        """Validate description for security."""
        # Check for SQL injection patterns
        sql_patterns = ["'; DROP TABLE", "-- ", "/*", "*/"]
        for pattern in sql_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Potential SQL injection detected")

        # Check for command injection
        cmd_patterns = [";", "&&", "||", "|", "`", "$("]
        for pattern in cmd_patterns:
            if pattern in v:
                raise ValueError("Potential command injection detected")

        return v.strip()
```

### 4. Rate Limiting

**Purpose**: Prevent resource exhaustion
**Implementation**: Token bucket algorithm in Reflex Layer

**Example**:
```rust
pub struct RateLimiter {
    buckets: HashMap<String, TokenBucket>,
    rate: u32,
    capacity: u32,
}

impl RateLimiter {
    pub fn check(&mut self, key: &str) -> Result<(), RateLimitError> {
        let bucket = self.buckets
            .entry(key.to_string())
            .or_insert_with(|| TokenBucket::new(self.capacity));

        bucket.refill(self.rate);

        if bucket.consume(1) {
            Ok(())
        } else {
            Err(RateLimitError {
                limit: self.rate,
                retry_after: bucket.retry_after(),
            })
        }
    }
}
```

### 5. Audit Logging

**Purpose**: Compliance and forensics
**Storage**: PostgreSQL with immutable logs

**Example**:
```python
async def log_security_event(
    event_type: str,
    user_id: str,
    action: str,
    resource: str,
    outcome: str,
    details: Dict[str, Any]
):
    """Log security event for audit trail."""
    await db.execute("""
        INSERT INTO security_audit_log (
            event_type, user_id, action, resource, outcome, details
        ) VALUES ($1, $2, $3, $4, $5, $6)
    """, event_type, user_id, action, resource, outcome, json.dumps(details))

# Usage
await log_security_event(
    event_type="authentication",
    user_id="user-123",
    action="login",
    resource="api",
    outcome="success",
    details={"ip": "192.168.1.1", "user_agent": "..."}
)
```

### 6. Defense in Depth

**Layers**:
1. **Network**: Kubernetes Network Policies, TLS
2. **Input**: Reflex Layer PII detection, validation
3. **Access**: Capability tokens, RBAC
4. **Data**: Encryption at rest, data diodes
5. **Output**: Output validation, sanitization
6. **Monitoring**: Security metrics, alerts
7. **Audit**: Comprehensive logging

## Consequences

### Positive

1. **Fine-Grained Control**:
   - Capabilities limit access precisely
   - Tokens expire automatically
   - Scopes prevent over-privileging
   - Easy to revoke access

2. **PII Protection**:
   - Automatic detection in Reflex Layer
   - Prevents accidental exposure
   - Sanitization before LLM APIs
   - Compliance-friendly

3. **Defense in Depth**:
   - Multiple security layers
   - Failure in one layer doesn't compromise system
   - Comprehensive protection
   - Audit trail for forensics

4. **Performance**:
   - PII detection in fast Rust code
   - JWT validation is local (no DB lookup)
   - Rate limiting prevents overload
   - Minimal overhead

5. **Auditability**:
   - All operations logged
   - Immutable audit trail
   - Compliance requirements met
   - Forensics support

### Negative

1. **Complexity**:
   - Capability tokens add overhead
   - PII patterns need maintenance
   - More code to test
   - Learning curve for developers

2. **False Positives**:
   - PII regex may over-detect
   - Legitimate data may be redacted
   - User experience impact
   - Manual review needed

3. **Performance Overhead**:
   - PII detection adds latency (<5ms)
   - JWT validation on every request
   - Rate limiting checks
   - Audit logging I/O

4. **Operational Burden**:
   - Key management for JWT
   - PII pattern updates
   - Audit log retention
   - Security monitoring

### Mitigation Strategies

1. **Complexity**:
   - Comprehensive documentation
   - Helper libraries for common cases
   - Automated testing
   - Training for developers

2. **False Positives**:
   - Tunable PII patterns
   - Whitelist for known-safe data
   - User feedback mechanism
   - Regular pattern review

3. **Performance**:
   - Optimize PII regex
   - Cache JWT validations
   - Batch audit logs
   - Monitor overhead

4. **Operations**:
   - Automated key rotation
   - Monitoring dashboards
   - Alerting for anomalies
   - Runbooks for incidents

## Alternatives Considered

### 1. OAuth 2.0 / OIDC

**Pros**:
- Industry standard
- Rich ecosystem
- Identity federation
- Well-understood

**Cons**:
- More complex than needed
- External dependencies
- Token introspection overhead
- Capability model not native

**Why Rejected**: Capability tokens provide simpler, fine-grained control for internal services.

### 2. mTLS for All Communication

**Pros**:
- Strong authentication
- End-to-end encryption
- Certificate-based

**Cons**:
- Complex certificate management
- Higher operational burden
- Not necessary for internal services
- Overkill for current scale

**Why Rejected**: TLS with capability tokens sufficient for our threat model.

### 3. ML-Based PII Detection

**Pros**:
- Better accuracy
- Contextual understanding
- Fewer false positives

**Cons**:
- Higher latency
- Model management complexity
- Resource intensive
- Harder to explain decisions

**Why Rejected**: Regex patterns sufficient for current needs, can add ML later if needed.

### 4. Role-Based Access Control (RBAC) Only

**Pros**:
- Simpler than capabilities
- Familiar model
- Standard implementation

**Cons**:
- Coarser-grained access
- Can't limit to specific tasks
- Role explosion problem
- Less flexible

**Why Rejected**: Capabilities provide finer control needed for task-level isolation.

## Implementation Guidelines

See [Security Overview](../security/overview.md) for detailed implementation guidance.

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [GDPR Compliance](https://gdpr.eu/)
- [Capability-Based Security](https://en.wikipedia.org/wiki/Capability-based_security)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly - higher frequency for security)
**Related ADRs**: ADR-001, ADR-002, ADR-003
