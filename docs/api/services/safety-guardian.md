# Safety Guardian Arm API Reference

**Service**: Safety Guardian Arm (Content Filtering & Policy Enforcement)
**Port**: 8007
**Base URL**: `http://localhost:8007` (development), `http://safety-guardian:8007` (internal)
**Technology**: Python 3.11+ / FastAPI
**Cost Tier**: 1 (Low - no LLM calls, pure regex)
**Average Latency**: <100ms

## Overview

The Safety Guardian is the security gatekeeper of OctoLLM. It performs ultra-fast content filtering and policy enforcement using regex-based detection. Think of it as the bouncer at a nightclub, checking IDs and enforcing rules before anyone enters.

### Capabilities

- **PII Detection**: Identify and redact SSN, credit cards, emails, phone numbers, IP addresses
- **Secrets Detection**: Find and redact API keys, tokens, passwords, connection strings
- **Content Filtering**: Block malicious content (SQL injection, XSS, command injection)
- **Policy Enforcement**: Verify organizational policy compliance (allowlists, denylists)

### Key Features

- **Sub-100ms Latency**: Pure regex matching, no LLM calls
- **Automatic Redaction**: Replace sensitive data with `[TYPE-REDACTED]` placeholders
- **Risk Scoring**: none → low → medium → high → critical
- **Block on High Risk**: Optional blocking for high/critical risk content
- **200+ Detection Patterns**: Comprehensive coverage of common PII and secrets
- **Zero Cost**: No LLM or external API calls

---

## Authentication

All Safety Guardian endpoints require Bearer token authentication (inter-service communication):

```bash
curl http://safety-guardian:8007/check \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My email is john@example.com",
    "check_types": ["pii", "secrets"],
    "redact_pii": true
  }'
```

**Note**: The Safety Guardian is typically called by the Orchestrator or Reflex Layer, not directly by external clients. External clients should use the [Orchestrator API](./orchestrator.md).

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details on capability-based tokens.

---

## Endpoints

### POST /check

Perform safety checks on text content including PII detection, secrets detection, content filtering, and policy enforcement.

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "text": "My email is john.doe@example.com and my phone is 555-123-4567. My API key is sk-1234567890abcdef.",
  "check_types": [
    "pii",
    "secrets"
  ],
  "redact_pii": true,
  "block_on_high_risk": true,
  "context": {
    "source": "user_input",
    "user_id": "user_123"
  }
}
```

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `text` | string | ✅ | 1-50,000 chars | Text to check for safety issues |
| `check_types` | array | ✅ | One or more: `pii`, `secrets`, `content`, `policy`, `all` | Types of safety checks to perform |
| `redact_pii` | boolean | ❌ | default: `true` | Whether to redact detected PII/secrets |
| `block_on_high_risk` | boolean | ❌ | default: `true` | Whether to block on high/critical risk |
| `context` | object | ❌ | - | Additional context (source, user_id, etc.) |

#### Response

**Status**: 200 OK

```json
{
  "safe": true,
  "risk_level": "medium",
  "issues": [
    {
      "type": "pii",
      "risk_level": "medium",
      "message": "PII detected: email",
      "matched_pattern": "email",
      "position": 12,
      "redaction": "[EMAIL-REDACTED]"
    },
    {
      "type": "pii",
      "risk_level": "medium",
      "message": "PII detected: phone",
      "matched_pattern": "phone",
      "position": 46,
      "redaction": "[PHONE-REDACTED]"
    },
    {
      "type": "secret",
      "risk_level": "high",
      "message": "Secret detected: openai_api_key",
      "matched_pattern": "openai_api_key",
      "position": 75,
      "redaction": "[OPENAI-KEY-REDACTED]"
    }
  ],
  "sanitized_text": "My email is [EMAIL-REDACTED] and my phone is [PHONE-REDACTED]. My API key is [OPENAI-KEY-REDACTED].",
  "blocked": false,
  "metadata": {
    "checks_performed": ["pii", "secrets"],
    "pii_types_found": ["email", "phone"],
    "secret_types_found": ["openai_api_key"],
    "processing_time_ms": 18.5
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `safe` | boolean | Whether content is safe (no high/critical risks, or risks were redacted) |
| `risk_level` | string | Highest risk level detected: `none`, `low`, `medium`, `high`, `critical` |
| `issues` | array | List of detected issues (PII, secrets, malicious content, policy violations) |
| `issues[].type` | string | Issue type: `pii`, `secret`, `malicious_content`, `inappropriate_content`, `policy_violation` |
| `issues[].risk_level` | string | Risk level for this issue: `low`, `medium`, `high`, `critical` |
| `issues[].message` | string | Human-readable issue description |
| `issues[].matched_pattern` | string | Pattern that matched (e.g., `email`, `api_key`, `sql_injection`) |
| `issues[].position` | integer | Character position in text where issue was found |
| `issues[].redaction` | string | Replacement text used for redaction (e.g., `[EMAIL-REDACTED]`) |
| `sanitized_text` | string | Text with all PII/secrets redacted |
| `blocked` | boolean | Whether request was blocked due to high/critical risk |
| `metadata` | object | Additional info (checks performed, types found, processing time) |

#### Examples

**Example 1: PII Detection and Redaction (Bash)**

```bash
curl -X POST http://safety-guardian:8007/check \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "text": "Contact me at john.doe@example.com or call 555-123-4567",
    "check_types": ["pii"],
    "redact_pii": true,
    "block_on_high_risk": false
  }'

# Response:
{
  "safe": true,
  "risk_level": "medium",
  "issues": [
    {
      "type": "pii",
      "risk_level": "medium",
      "message": "PII detected: email",
      "matched_pattern": "email",
      "position": 14,
      "redaction": "[EMAIL-REDACTED]"
    },
    {
      "type": "pii",
      "risk_level": "medium",
      "message": "PII detected: phone",
      "matched_pattern": "phone",
      "position": 48,
      "redaction": "[PHONE-REDACTED]"
    }
  ],
  "sanitized_text": "Contact me at [EMAIL-REDACTED] or call [PHONE-REDACTED]",
  "blocked": false,
  "metadata": {
    "checks_performed": ["pii"],
    "pii_types_found": ["email", "phone"],
    "processing_time_ms": 12.3
  }
}
```

**Example 2: Secrets Detection (Python SDK)**

```python
from octollm_sdk import SafetyGuardianClient

client = SafetyGuardianClient(bearer_token="service_token_abc123")

text = """
Here's the database connection:
postgresql://user:password123@db.example.com:5432/mydb

And here's my OpenAI key: sk-1234567890abcdef1234567890abcdef1234567890abcdef
"""

result = await client.check({
    "text": text,
    "check_types": ["secrets"],
    "redact_pii": True,
    "block_on_high_risk": True
})

print(f"Safe: {result.safe}")
print(f"Risk Level: {result.risk_level}")
print(f"Blocked: {result.blocked}")

print("\n=== ISSUES ===")
for issue in result.issues:
    print(f"[{issue.risk_level.upper()}] {issue.message}")
    print(f"  Pattern: {issue.matched_pattern}")
    print(f"  Position: {issue.position}\n")

print("=== SANITIZED TEXT ===")
print(result.sanitized_text)

# Output:
# Safe: False
# Risk Level: critical
# Blocked: True
#
# === ISSUES ===
# [HIGH] Secret detected: database_connection_string
#   Pattern: database_connection_string
#   Position: 30
#
# [CRITICAL] Secret detected: openai_api_key
#   Pattern: openai_api_key
#   Position: 100
#
# === SANITIZED TEXT ===
# Here's the database connection:
# [DB-CONNECTION-REDACTED]
#
# And here's my OpenAI key: [OPENAI-KEY-REDACTED]
```

**Example 3: SQL Injection Detection (TypeScript SDK)**

```typescript
import { SafetyGuardianClient } from 'octollm-sdk';

const client = new SafetyGuardianClient({
  bearerToken: process.env.SERVICE_TOKEN
});

const userInput = "admin' OR '1'='1' --";

const result = await client.check({
  text: userInput,
  checkTypes: ['content'],
  blockOnHighRisk: true
});

console.log(`Safe: ${result.safe}`);
console.log(`Risk Level: ${result.risk_level}`);
console.log(`Blocked: ${result.blocked}`);

if (result.blocked) {
  console.log('\n🚫 REQUEST BLOCKED');
  console.log('Reason:', result.metadata.block_reason);

  const sqlInjections = result.issues.filter(i => i.matched_pattern === 'sql_injection');
  console.log(`\nDetected ${sqlInjections.length} SQL injection attempts`);
}

// Output:
// Safe: false
// Risk Level: critical
// Blocked: true
//
// 🚫 REQUEST BLOCKED
// Reason: critical_risk_level
//
// Detected 1 SQL injection attempts
```

**Example 4: Multiple Check Types (Python SDK)**

```python
from octollm_sdk import SafetyGuardianClient

client = SafetyGuardianClient(bearer_token="service_token_abc123")

text = """
Here's my analysis:
Email: admin@company.com
SSN: 123-45-6789
Password: SuperSecret123!

Database query: SELECT * FROM users WHERE id = 1 UNION SELECT password FROM admin
"""

result = await client.check({
    "text": text,
    "check_types": ["all"],  # Run all checks
    "redact_pii": True,
    "block_on_high_risk": True
})

# Group issues by type
from collections import defaultdict
by_type = defaultdict(list)
for issue in result.issues:
    by_type[issue.type].append(issue)

print("=== ISSUES BY TYPE ===")
for issue_type, issues in by_type.items():
    print(f"\n{issue_type.upper()}: {len(issues)} found")
    for issue in issues:
        print(f"  - {issue.message} (risk: {issue.risk_level})")

print(f"\n=== SANITIZED TEXT ===")
print(result.sanitized_text)

# Output:
# === ISSUES BY TYPE ===
#
# PII: 2 found
#   - PII detected: email (risk: medium)
#   - PII detected: ssn (risk: high)
#
# SECRET: 1 found
#   - Secret detected: password (risk: high)
#
# MALICIOUS_CONTENT: 1 found
#   - Malicious content detected: sql_injection (risk: critical)
#
# === SANITIZED TEXT ===
# Here's my analysis:
# Email: [EMAIL-REDACTED]
# SSN: [SSN-REDACTED]
# Password: [PASSWORD-REDACTED]
#
# Database query: [SQL-INJECTION-BLOCKED]
```

**Example 5: Credit Card Detection (Bash)**

```bash
curl -X POST http://safety-guardian:8007/check \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "text": "My credit card is 4532-1234-5678-9010 with CVV 123",
    "check_types": ["pii"],
    "redact_pii": true
  }'

# Response:
{
  "safe": true,
  "risk_level": "high",
  "issues": [
    {
      "type": "pii",
      "risk_level": "high",
      "message": "PII detected: credit_card",
      "matched_pattern": "credit_card",
      "position": 18,
      "redaction": "[CREDIT-CARD-REDACTED]"
    },
    {
      "type": "pii",
      "risk_level": "medium",
      "message": "PII detected: cvv",
      "matched_pattern": "cvv",
      "position": 50,
      "redaction": "[CVV-REDACTED]"
    }
  ],
  "sanitized_text": "My credit card is [CREDIT-CARD-REDACTED] with CVV [CVV-REDACTED]",
  "blocked": false,
  "metadata": {
    "checks_performed": ["pii"],
    "pii_types_found": ["credit_card", "cvv"],
    "processing_time_ms": 15.2
  }
}
```

**Example 6: No Redaction Mode (Python SDK)**

```python
from octollm_sdk import SafetyGuardianClient

client = SafetyGuardianClient(bearer_token="service_token_abc123")

# Check for PII but don't redact (for logging/alerting only)
result = await client.check({
    "text": "Contact: john@example.com",
    "check_types": ["pii"],
    "redact_pii": False,  # Don't redact
    "block_on_high_risk": False
})

if result.issues:
    print(f"⚠️ PII detected in input!")
    for issue in result.issues:
        print(f"  - {issue.matched_pattern} at position {issue.position}")

    # Log to security monitoring (without redaction)
    await security_log(result.text, result.issues)

# sanitized_text will equal original text when redact_pii=False
assert result.sanitized_text == result.text
```

#### Error Responses

**400 Bad Request** (invalid request):

```json
{
  "error": "ValidationError",
  "message": "Text exceeds maximum length of 50,000 characters",
  "details": {
    "field": "text",
    "length": 75000,
    "max_length": 50000
  }
}
```

**401 Unauthorized** (missing or invalid token):

```json
{
  "error": "Unauthorized",
  "message": "Bearer token required for safety checks"
}
```

---

### GET /capabilities

Retrieve safety guardian capabilities and supported detection types.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "capabilities": [
    "pii_detection",
    "secrets_detection",
    "content_filtering",
    "policy_enforcement"
  ],
  "detection_types": [
    "ssn",
    "credit_card",
    "email",
    "phone",
    "ip_address",
    "api_key",
    "password",
    "database_connection",
    "sql_injection",
    "xss",
    "command_injection"
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
  "version": "0.3.0",
  "patterns_loaded": 237
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
# HELP safety_checks_total Total number of safety checks
# TYPE safety_checks_total counter
safety_checks_total{check_type="pii",result="safe"} 15234
safety_checks_total{check_type="secrets",result="blocked"} 892
safety_checks_total{check_type="content",result="safe"} 8901

# HELP safety_issues_by_type Issues by type
# TYPE safety_issues_by_type counter
safety_issues_by_type{type="pii",pattern="email"} 3421
safety_issues_by_type{type="pii",pattern="phone"} 1892
safety_issues_by_type{type="secret",pattern="api_key"} 523

# HELP safety_blocked_requests_total Requests blocked by Safety Guardian
# TYPE safety_blocked_requests_total counter
safety_blocked_requests_total 164

# HELP safety_check_duration_seconds Safety check duration
# TYPE safety_check_duration_seconds histogram
safety_check_duration_seconds_bucket{le="0.05"} 12523
safety_check_duration_seconds_bucket{le="0.1"} 19836
```

---

## Data Models

### SafetyRequest

```typescript
type CheckType = 'pii' | 'secrets' | 'content' | 'policy' | 'all';

interface SafetyRequest {
  text: string;                 // 1-50,000 chars
  check_types: CheckType[];
  redact_pii?: boolean;         // Default: true
  block_on_high_risk?: boolean; // Default: true
  context?: {
    [key: string]: any;
  };
}
```

### SafetyResult

```typescript
type RiskLevel = 'none' | 'low' | 'medium' | 'high' | 'critical';

interface SafetyResult {
  safe: boolean;                // No high/critical risks (or redacted)
  risk_level: RiskLevel;        // Highest risk level detected
  issues: SafetyIssue[];
  sanitized_text: string;       // Text with PII/secrets redacted
  blocked: boolean;             // Whether request was blocked
  metadata: {
    checks_performed: string[];
    pii_types_found?: string[];
    secret_types_found?: string[];
    processing_time_ms: number;
    block_reason?: string;
    [key: string]: any;
  };
}
```

### SafetyIssue

```typescript
type IssueType =
  | 'pii'
  | 'secret'
  | 'malicious_content'
  | 'inappropriate_content'
  | 'policy_violation';

interface SafetyIssue {
  type: IssueType;
  risk_level: RiskLevel;
  message: string;              // Human-readable description
  matched_pattern: string;      // e.g., "email", "api_key", "sql_injection"
  position: number;             // Character position in text
  redaction: string;            // Replacement text (e.g., "[EMAIL-REDACTED]")
}
```

---

## Integration Patterns

### Pattern 1: Input Sanitization Pipeline

Always sanitize user input before processing.

```python
from octollm_sdk import SafetyGuardianClient, OrchestratorClient

safety = SafetyGuardianClient(bearer_token="service_token_abc123")
orchestrator = OrchestratorClient(bearer_token="service_token_abc123")

async def process_user_request(user_input: str):
    # Stage 1: Safety check
    safety_result = await safety.check({
        "text": user_input,
        "check_types": ["all"],
        "redact_pii": True,
        "block_on_high_risk": True
    })

    if safety_result.blocked:
        raise ValueError(f"Request blocked: {safety_result.metadata.block_reason}")

    # Stage 2: Use sanitized input
    task = await orchestrator.submit_task({
        "goal": safety_result.sanitized_text,  # Use sanitized version
        "budget": {"max_tokens": 5000}
    })

    return task
```

### Pattern 2: Output Validation Before Delivery

Check outputs before sending to users.

```typescript
import { SafetyGuardianClient } from 'octollm-sdk';

const safety = new SafetyGuardianClient({ bearerToken: '...' });

async function validateOutput(output: string): Promise<string> {
  const result = await safety.check({
    text: output,
    checkTypes: ['pii', 'secrets'],
    redactPii: true,
    blockOnHighRisk: false  // Don't block, just redact
  });

  if (result.issues.length > 0) {
    console.log(`Redacted ${result.issues.length} PII/secret instances`);
    result.issues.forEach(issue => {
      console.log(`  - ${issue.matched_pattern} at position ${issue.position}`);
    });
  }

  return result.sanitized_text;  // Return sanitized version
}

// Example usage
const rawOutput = "User email is john@example.com";
const safeOutput = await validateOutput(rawOutput);
// Returns: "User email is [EMAIL-REDACTED]"
```

### Pattern 3: Tiered Risk Handling

Handle different risk levels differently.

```python
from octollm_sdk import SafetyGuardianClient

client = SafetyGuardianClient(bearer_token="service_token_abc123")

async def tiered_risk_handling(text: str):
    result = await client.check({
        "text": text,
        "check_types": ["all"],
        "redact_pii": True,
        "block_on_high_risk": False  # Handle manually
    })

    if result.risk_level == "critical":
        # Block immediately, alert security team
        await alert_security_team(result)
        raise SecurityError("Critical security issue detected")

    elif result.risk_level == "high":
        # Require manual review
        await queue_for_review(text, result)
        return "Queued for manual review"

    elif result.risk_level == "medium":
        # Redact and log
        await log_medium_risk(result)
        return result.sanitized_text

    else:
        # Allow through
        return text
```

### Pattern 4: Audit Logging with PII Detection

Log all safety checks for compliance.

```typescript
import { SafetyGuardianClient } from 'octollm-sdk';

const client = new SafetyGuardianClient({ bearerToken: '...' });

async function auditedSafetyCheck(
  text: string,
  userId: string
): Promise<SafetyResult> {
  const result = await client.check({
    text,
    checkTypes: ['all'],
    redactPii: true,
    context: {
      user_id: userId,
      timestamp: new Date().toISOString()
    }
  });

  // Log to audit system
  await auditLog({
    event: 'safety_check',
    user_id: userId,
    risk_level: result.risk_level,
    issues_found: result.issues.length,
    issue_types: result.issues.map(i => i.matched_pattern),
    blocked: result.blocked,
    timestamp: new Date().toISOString()
  });

  return result;
}
```

---

## Performance Characteristics

| Check Type | P50 | P95 | P99 | Max | Notes |
|------------|-----|-----|-----|-----|-------|
| PII only | 15ms | 40ms | 70ms | 150ms | ~50 regex patterns |
| Secrets only | 20ms | 50ms | 80ms | 180ms | ~30 regex patterns |
| Content only | 10ms | 30ms | 50ms | 100ms | ~20 injection patterns |
| All checks | 35ms | 80ms | 120ms | 250ms | All patterns |

### Throughput

| Text Size | Checks/Second (Single Instance) |
|-----------|---------------------------------|
| 100 chars | ~2,000 |
| 1K chars | ~1,500 |
| 10K chars | ~800 |
| 50K chars | ~200 |

**Note**: Performance scales linearly with text length.

---

## Troubleshooting

### Issue 1: False Positives (Valid Content Blocked)

**Symptoms**: Legitimate content being flagged as PII or malicious

**Possible Causes**:
- Pattern too broad
- Context not considered
- Test data in production

**Solutions**:
```python
# Use context to whitelist known safe patterns
result = await client.check({
    "text": "Our API endpoint is https://api.example.com/v1/users",
    "check_types": ["all"],
    "context": {
        "whitelist_patterns": ["api.example.com"],  # Don't flag our own domain
        "environment": "production"
    }
})

# Adjust risk thresholds
# Don't block on medium risk, only high/critical
```

### Issue 2: False Negatives (PII Not Detected)

**Symptoms**: Known PII not being detected

**Possible Causes**:
- Non-standard format
- Pattern not in database
- Obfuscation

**Solutions**:
```bash
# Check which patterns are loaded
curl http://safety-guardian:8007/capabilities | jq '.detection_types'

# Add custom patterns (config update required)
# CUSTOM_PATTERNS='{"employee_id": "EMP-\\d{6}"}'

# Restart Safety Guardian after config change
kubectl rollout restart deployment safety-guardian
```

### Issue 3: High Latency (>200ms)

**Symptoms**: Safety checks taking >200ms

**Possible Causes**:
- Very long text (>10K chars)
- Running all checks on every request
- High concurrent load

**Solutions**:
```bash
# Split large texts into chunks
# Check each chunk separately

# Use targeted check types
# Don't use check_types=["all"] if you only need PII detection

# Scale horizontally
kubectl scale deployment safety-guardian --replicas=10

# Monitor latency
curl http://safety-guardian:8007/metrics | grep safety_check_duration
```

### Issue 4: Blocked Requests (When Shouldn't Be)

**Symptoms**: Legitimate requests being blocked

**Possible Causes**:
- block_on_high_risk set too aggressively
- Risk level thresholds too strict
- Test data in production

**Solutions**:
```python
# Adjust blocking threshold
result = await client.check({
    "text": text,
    "check_types": ["all"],
    "block_on_high_risk": False,  # Manual handling
    "redact_pii": True
})

# Handle risk levels manually (see Integration Patterns)

# Review blocked requests
curl http://safety-guardian:8007/metrics | grep safety_blocked_requests_total
```

### Issue 5: Redaction Too Aggressive

**Symptoms**: Too much content being redacted

**Possible Causes**:
- Patterns matching non-sensitive data
- Overly broad regex
- Missing context

**Solutions**:
```python
# Disable redaction, use for detection only
result = await client.check({
    "text": text,
    "check_types": ["pii"],
    "redact_pii": False,  # Detect but don't redact
    "block_on_high_risk": False
})

# Then manually redact only specific patterns
if "ssn" in [i.matched_pattern for i in result.issues]:
    # Only redact SSN, not emails
    text = redact_ssn_only(text)
```

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Reflex Layer API](./reflex-layer.md)
- [Orchestrator API](./orchestrator.md)
- [Judge Arm API](./judge.md)
- [OpenAPI Specification](../openapi/safety-guardian.yaml)

---

## Support

For issues with the Safety Guardian Arm:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `kubectl logs -l app=safety-guardian`
3. Check metrics: `curl http://safety-guardian:8007/metrics`
4. File issue: https://github.com/octollm/octollm/issues
