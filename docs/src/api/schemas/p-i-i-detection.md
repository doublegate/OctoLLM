# PIIDetection Schema Reference

## Overview

The **PIIDetection** (also called `SafetyResult`) schema represents the output from the Safety Guardian arm after checking text for personally identifiable information (PII), secrets, malicious content, and policy violations. This ultra-fast (<100ms) regex-based detection enables real-time content filtering without expensive LLM calls.

**Used By**: Safety Guardian Arm (output), Orchestrator (for input/output filtering), all Arms (for sanitization)
**Primary Endpoint**: `POST /check`
**Format**: JSON

---

## Structure

### PIIDetection (SafetyResult)

Complete safety check result with detected issues, risk level, and sanitized text.

```typescript
interface PIIDetection {
  safe: boolean;                    // Required: No high/critical risks
  risk_level: RiskLevel;            // Required: Highest risk level detected
  issues: SafetyIssue[];            // Required: List of detected issues
  sanitized_text: string;           // Required: Text with PII/secrets redacted
  blocked: boolean;                 // Required: Whether request was blocked
  metadata?: SafetyMetadata;        // Optional: Additional info
}

interface SafetyIssue {
  type: IssueType;                  // Required: Issue type
  risk_level: RiskLevel;            // Required: Risk level for this issue
  message: string;                  // Required: Human-readable description
  matched_pattern: string;          // Required: Pattern that matched
  position: number;                 // Required: Character position in text
  redaction?: string;               // Optional: Replacement text
}

type RiskLevel = 'none' | 'low' | 'medium' | 'high' | 'critical';

type IssueType =
  | 'pii'                           // Personally identifiable information
  | 'secret'                        // API keys, passwords, tokens
  | 'malicious_content'             // XSS, SQL injection, shell injection
  | 'inappropriate_content'         // Offensive language, hate speech
  | 'policy_violation';             // Violates usage policies

interface SafetyMetadata {
  checks_performed: string[];       // Check types run (pii, secrets, etc.)
  pii_types_found?: string[];       // PII types detected (email, phone, etc.)
  secret_types_found?: string[];    // Secret types detected (api_key, etc.)
  processing_time_ms: number;       // Execution time
  block_reason?: string;            // Why request was blocked
}
```

---

## Field Definitions

### `safe` (required)

**Type**: boolean
**Description**: Whether the content is safe (no high or critical risks, or successfully redacted)

**Safety Logic**:
```typescript
safe = (risk_level === 'none' || risk_level === 'low' || risk_level === 'medium')
      || (blocked === false && all_issues_redacted === true)
```

**Examples**:
```json
// Safe - no issues
{"safe": true, "risk_level": "none", "issues": []}

// Safe - low risk accepted
{"safe": true, "risk_level": "low", "issues": [{...}]}

// Safe - PII redacted
{"safe": true, "risk_level": "medium", "issues": [{type: "pii", ...}], "sanitized_text": "[EMAIL-REDACTED]"}

// Unsafe - high risk
{"safe": false, "risk_level": "high", "issues": [{...}]}

// Unsafe - blocked
{"safe": false, "risk_level": "critical", "blocked": true}
```

---

### `risk_level` (required)

**Type**: enum - `'none'` | `'low'` | `'medium'` | `'high'` | `'critical'`
**Description**: Highest risk level detected across all issues

**Risk Level Definitions**:

**none** - No issues detected
- Clean content
- No PII, secrets, or policy violations
- Safe to process without redaction

**low** - Minimal risk, acceptable
- Non-sensitive PII (first name only, common usernames)
- Informational warnings
- Generally safe to process

**medium** - Moderate risk, recommend redaction
- PII (email addresses, phone numbers)
- Low-sensitivity data
- Should be redacted for compliance

**high** - Significant risk, block or redact
- High-sensitivity PII (SSN, credit cards, addresses)
- API keys, secrets
- Policy violations
- Requires action (block or redact)

**critical** - Severe risk, always block
- Complete credentials (username + password)
- Private keys, access tokens
- Malicious code (XSS, SQL injection)
- Hate speech, threats
- Must be blocked immediately

**Example**:
```json
{
  "risk_level": "medium",
  "issues": [
    {"type": "pii", "risk_level": "low", "matched_pattern": "first_name"},
    {"type": "pii", "risk_level": "medium", "matched_pattern": "email"}
  ]
}
// Highest risk is "medium", so risk_level = "medium"
```

---

### `issues` (required)

**Type**: array of SafetyIssue objects
**Description**: List of all detected issues (PII, secrets, policy violations)

**Empty Array**: No issues detected
**Multiple Issues**: Sorted by risk_level (critical → high → medium → low)

---

#### SafetyIssue Fields

##### `type` (required)

**Type**: enum
**Values**: `'pii'` | `'secret'` | `'malicious_content'` | `'inappropriate_content'` | `'policy_violation'`
**Description**: Category of the detected issue

**Type Definitions**:

**pii** - Personally Identifiable Information
- Email addresses
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- Passport numbers
- IP addresses
- Full names with addresses
- Driver's license numbers

**secret** - Credentials and API Keys
- OpenAI API keys (`sk-...`)
- AWS access keys (`AKIA...`)
- GitHub tokens (`ghp_...`, `gho_...`)
- JWT tokens
- Passwords in plaintext
- Private keys (RSA, SSH)
- Database connection strings

**malicious_content** - Code Injection
- SQL injection attempts
- XSS payloads (`<script>`, `javascript:`)
- Shell injection (`; rm -rf /`)
- Command injection
- Path traversal (`../../../`)

**inappropriate_content** - Policy Violations
- Offensive language
- Hate speech
- Threats of violence
- Spam patterns

**policy_violation** - Usage Policy Violations
- Prohibited use cases
- Terms of service violations

---

##### `risk_level` (required)

**Type**: enum - `'low'` | `'medium'` | `'high'` | `'critical'`
**Description**: Risk level for this specific issue

**Risk Levels by Pattern**:

| Pattern | Risk Level | Rationale |
|---------|------------|-----------|
| Email address | medium | Moderate PII, should redact |
| Phone number | medium | Moderate PII, should redact |
| First name only | low | Low sensitivity, informational |
| SSN | high | High-sensitivity PII, must redact |
| Credit card | high | Financial data, must redact |
| API key | critical | Security credential, must block |
| Password | critical | Security credential, must block |
| SQL injection | critical | Malicious code, must block |
| XSS payload | critical | Malicious code, must block |

---

##### `message` (required)

**Type**: string
**Constraints**: 10-200 characters
**Description**: Human-readable description of the issue

**Format**: `"{Type} detected: {pattern}"`

**Examples**:
```json
"PII detected: email"
"PII detected: phone"
"Secret detected: openai_api_key"
"Malicious content detected: sql_injection"
"Inappropriate content detected: offensive_language"
```

---

##### `matched_pattern` (required)

**Type**: string
**Description**: Specific pattern that matched (for logging and debugging)

**Common PII Patterns**:
- `email` - Email address
- `phone` - Phone number (various formats)
- `ssn` - Social Security Number
- `credit_card` - Credit card number
- `ip_address` - IPv4/IPv6 address
- `full_name_with_address` - Name + address combo
- `passport_number` - Passport number
- `drivers_license` - Driver's license number

**Common Secret Patterns**:
- `openai_api_key` - OpenAI key (sk-...)
- `aws_access_key` - AWS access key (AKIA...)
- `github_token` - GitHub token (ghp_..., gho_...)
- `jwt_token` - JSON Web Token
- `password_in_plaintext` - Obvious password
- `private_key` - RSA/SSH private key
- `database_connection_string` - DB credentials

**Common Malicious Content Patterns**:
- `sql_injection` - SQL injection attempt
- `xss_script_tag` - XSS with <script>
- `xss_javascript_protocol` - XSS with javascript:
- `shell_injection` - Shell command injection
- `path_traversal` - Directory traversal

**Example**:
```json
{
  "type": "pii",
  "matched_pattern": "email",
  "message": "PII detected: email"
}
```

---

##### `position` (required)

**Type**: integer
**Constraints**: >= 0
**Description**: Character position (0-indexed) where the issue was found in the original text

**Purpose**:
- Enables precise location tracking
- Useful for debugging
- Allows context extraction

**Example**:
```json
{
  "text": "My email is john@example.com and my phone is 555-1234",
  "issues": [
    {"matched_pattern": "email", "position": 12},  // "john@example.com" starts at position 12
    {"matched_pattern": "phone", "position": 48}   // "555-1234" starts at position 48
  ]
}
```

---

##### `redaction` (optional)

**Type**: string
**Description**: Replacement text used for redaction

**Common Redaction Formats**:
- `[EMAIL-REDACTED]`
- `[PHONE-REDACTED]`
- `[SSN-REDACTED]`
- `[OPENAI-KEY-REDACTED]`
- `[AWS-KEY-REDACTED]`
- `[REDACTED]` (generic)

**Example**:
```json
{
  "type": "pii",
  "matched_pattern": "email",
  "redaction": "[EMAIL-REDACTED]"
}
```

---

### `sanitized_text` (required)

**Type**: string
**Description**: Original text with all detected PII and secrets redacted

**Behavior**:
- If `redact_pii: true` in request → all PII/secrets replaced with redaction tokens
- If `redact_pii: false` → unchanged text (same as input)
- Redactions are deterministic (same input → same redactions)

**Examples**:

**Input**:
```
"Contact me at john.doe@example.com or call 555-123-4567"
```

**Output** (`redact_pii: true`):
```json
{
  "sanitized_text": "Contact me at [EMAIL-REDACTED] or call [PHONE-REDACTED]"
}
```

**Output** (`redact_pii: false`):
```json
{
  "sanitized_text": "Contact me at john.doe@example.com or call 555-123-4567"
}
```

---

### `blocked` (required)

**Type**: boolean
**Description**: Whether the request was blocked due to high/critical risk

**Blocking Logic**:
```typescript
blocked = (risk_level === 'high' || risk_level === 'critical') && block_on_high_risk === true
```

**Examples**:
```json
// Not blocked - low risk
{"blocked": false, "risk_level": "low"}

// Not blocked - high risk but blocking disabled
{"blocked": false, "risk_level": "high"}  // block_on_high_risk: false

// Blocked - critical risk
{"blocked": true, "risk_level": "critical"}  // block_on_high_risk: true
```

---

### `metadata` (optional)

**Type**: object
**Description**: Additional information about the safety check process

**Common Metadata Fields**:

**`checks_performed`** - Array of check types executed:
```json
{"checks_performed": ["pii", "secrets", "content"]}
```

**`pii_types_found`** - Array of detected PII types:
```json
{"pii_types_found": ["email", "phone", "ssn"]}
```

**`secret_types_found`** - Array of detected secret types:
```json
{"secret_types_found": ["openai_api_key", "aws_access_key"]}
```

**`processing_time_ms`** - Execution time:
```json
{"processing_time_ms": 45.3}
```

**`block_reason`** - Why request was blocked:
```json
{"block_reason": "critical_risk_level"}
{"block_reason": "policy_violation"}
```

**Complete Metadata Example**:
```json
{
  "metadata": {
    "checks_performed": ["pii", "secrets"],
    "pii_types_found": ["email", "phone"],
    "secret_types_found": ["openai_api_key"],
    "processing_time_ms": 62.8,
    "block_reason": "critical_risk_level"
  }
}
```

---

## Complete Examples

### Example 1: No Issues Detected

```json
{
  "safe": true,
  "risk_level": "none",
  "issues": [],
  "sanitized_text": "Hello, this is a test message with no sensitive data.",
  "blocked": false,
  "metadata": {
    "checks_performed": ["pii", "secrets", "content"],
    "processing_time_ms": 12.5
  }
}
```

---

### Example 2: PII Detected and Redacted

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
      "position": 48,
      "redaction": "[PHONE-REDACTED]"
    }
  ],
  "sanitized_text": "My email is [EMAIL-REDACTED] and my phone is [PHONE-REDACTED]",
  "blocked": false,
  "metadata": {
    "checks_performed": ["pii"],
    "pii_types_found": ["email", "phone"],
    "processing_time_ms": 23.7
  }
}
```

---

### Example 3: High-Risk PII (SSN + Credit Card)

```json
{
  "safe": false,
  "risk_level": "high",
  "issues": [
    {
      "type": "pii",
      "risk_level": "high",
      "message": "PII detected: ssn",
      "matched_pattern": "ssn",
      "position": 11,
      "redaction": "[SSN-REDACTED]"
    },
    {
      "type": "pii",
      "risk_level": "high",
      "message": "PII detected: credit_card",
      "matched_pattern": "credit_card",
      "position": 35,
      "redaction": "[CREDIT-CARD-REDACTED]"
    }
  ],
  "sanitized_text": "My SSN is [SSN-REDACTED] and card is [CREDIT-CARD-REDACTED]",
  "blocked": true,
  "metadata": {
    "checks_performed": ["pii"],
    "pii_types_found": ["ssn", "credit_card"],
    "processing_time_ms": 28.4,
    "block_reason": "high_risk_pii_detected"
  }
}
```

---

### Example 4: Critical - API Key Detected

```json
{
  "safe": false,
  "risk_level": "critical",
  "issues": [
    {
      "type": "secret",
      "risk_level": "critical",
      "message": "Secret detected: openai_api_key",
      "matched_pattern": "openai_api_key",
      "position": 15,
      "redaction": "[OPENAI-KEY-REDACTED]"
    }
  ],
  "sanitized_text": "My API key is [OPENAI-KEY-REDACTED]",
  "blocked": true,
  "metadata": {
    "checks_performed": ["secrets"],
    "secret_types_found": ["openai_api_key"],
    "processing_time_ms": 18.3,
    "block_reason": "critical_risk_level"
  }
}
```

---

### Example 5: Malicious Content (SQL Injection)

```json
{
  "safe": false,
  "risk_level": "critical",
  "issues": [
    {
      "type": "malicious_content",
      "risk_level": "critical",
      "message": "Malicious content detected: sql_injection",
      "matched_pattern": "sql_injection",
      "position": 34,
      "redaction": "[MALICIOUS-CONTENT-REMOVED]"
    }
  ],
  "sanitized_text": "SELECT * FROM users WHERE id = '[MALICIOUS-CONTENT-REMOVED]'",
  "blocked": true,
  "metadata": {
    "checks_performed": ["content"],
    "processing_time_ms": 15.6,
    "block_reason": "malicious_content_detected"
  }
}
```

---

### Example 6: Multiple Issues (Mixed Risk Levels)

```json
{
  "safe": false,
  "risk_level": "critical",
  "issues": [
    {
      "type": "pii",
      "risk_level": "medium",
      "message": "PII detected: email",
      "matched_pattern": "email",
      "position": 20,
      "redaction": "[EMAIL-REDACTED]"
    },
    {
      "type": "secret",
      "risk_level": "critical",
      "message": "Secret detected: aws_access_key",
      "matched_pattern": "aws_access_key",
      "position": 58,
      "redaction": "[AWS-KEY-REDACTED]"
    },
    {
      "type": "pii",
      "risk_level": "high",
      "message": "PII detected: credit_card",
      "matched_pattern": "credit_card",
      "position": 95,
      "redaction": "[CREDIT-CARD-REDACTED]"
    }
  ],
  "sanitized_text": "Contact me at [EMAIL-REDACTED], my AWS key is [AWS-KEY-REDACTED], card number [CREDIT-CARD-REDACTED]",
  "blocked": true,
  "metadata": {
    "checks_performed": ["pii", "secrets"],
    "pii_types_found": ["email", "credit_card"],
    "secret_types_found": ["aws_access_key"],
    "processing_time_ms": 42.1,
    "block_reason": "critical_risk_level"
  }
}
```

---

## Usage Patterns

### Pattern 1: Input Sanitization Before Processing

Sanitize user input before passing to LLMs or other services.

```python
from octollm_sdk import SafetyGuardianClient

guardian = SafetyGuardianClient(bearer_token="service_token_abc123")

async def sanitize_user_input(text: str) -> str:
    """Sanitize user input, removing PII and secrets."""
    result = await guardian.check({
        "text": text,
        "check_types": ["pii", "secrets"],
        "redact_pii": True,
        "block_on_high_risk": True
    })

    if result.blocked:
        raise ValueError(f"Input blocked: {result.metadata.get('block_reason')}")

    return result.sanitized_text

# Example usage
user_input = "My email is john@example.com and API key is sk-1234567890"
safe_input = await sanitize_user_input(user_input)
# Output: "My email is [EMAIL-REDACTED] and API key is [OPENAI-KEY-REDACTED]"
```

---

### Pattern 2: Output Validation Before Returning to User

Check LLM output for accidental PII leakage.

```typescript
import { SafetyGuardianClient } from 'octollm-sdk';

const guardian = new SafetyGuardianClient({
  bearerToken: process.env.SERVICE_TOKEN
});

async function validateOutput(output: string): Promise<string> {
  const result = await guardian.check({
    text: output,
    checkTypes: ['pii', 'secrets'],
    redactPii: true,
    blockOnHighRisk: false  // Don't block, just redact
  });

  if (result.issues.length > 0) {
    console.warn(`⚠️ ${result.issues.length} PII/secret issues found in output`);
    result.issues.forEach(issue => {
      console.warn(`  - ${issue.message} at position ${issue.position}`);
    });
  }

  return result.sanitized_text;
}

// Example usage
const llmOutput = "User john@example.com requested access to API key sk-abc123";
const safeOutput = await validateOutput(llmOutput);
// Output: "User [EMAIL-REDACTED] requested access to API key [OPENAI-KEY-REDACTED]"
```

---

### Pattern 3: Risk-Based Handling

Handle different risk levels appropriately.

```python
async def process_with_risk_handling(text: str):
    """Process text with risk-appropriate handling."""
    result = await guardian.check({
        "text": text,
        "check_types": ["all"],
        "redact_pii": True,
        "block_on_high_risk": False  # Manual handling
    })

    if result.risk_level == "none":
        # Safe to process as-is
        return process_text(text)

    elif result.risk_level in ["low", "medium"]:
        # Use sanitized text
        logger.info(f"Using sanitized text ({result.risk_level} risk)")
        return process_text(result.sanitized_text)

    elif result.risk_level == "high":
        # Require manual review
        logger.warning(f"High risk detected, sending for manual review")
        await send_for_manual_review(text, result)
        return None

    elif result.risk_level == "critical":
        # Block immediately
        logger.error(f"Critical risk detected, blocking request")
        raise SecurityError(f"Request blocked: {result.metadata.get('block_reason')}")
```

---

### Pattern 4: Compliance Reporting

Generate compliance reports for PII handling.

```typescript
interface ComplianceReport {
  totalChecks: number;
  piiDetected: number;
  secretsDetected: number;
  blocked: number;
  byRiskLevel: Record<string, number>;
}

async function generateComplianceReport(
  checks: PIIDetection[]
): Promise<ComplianceReport> {
  const report: ComplianceReport = {
    totalChecks: checks.length,
    piiDetected: 0,
    secretsDetected: 0,
    blocked: 0,
    byRiskLevel: {
      none: 0,
      low: 0,
      medium: 0,
      high: 0,
      critical: 0
    }
  };

  for (const check of checks) {
    // Count PII and secrets
    const piiIssues = check.issues.filter(i => i.type === 'pii');
    const secretIssues = check.issues.filter(i => i.type === 'secret');

    if (piiIssues.length > 0) report.piiDetected++;
    if (secretIssues.length > 0) report.secretsDetected++;

    // Count blocked requests
    if (check.blocked) report.blocked++;

    // Count by risk level
    report.byRiskLevel[check.risk_level]++;
  }

  return report;
}

// Example usage
const report = await generateComplianceReport(safetyCheckResults);
console.log(`PII Detection Summary:
  Total Checks: ${report.totalChecks}
  PII Detected: ${report.piiDetected} (${(report.piiDetected / report.totalChecks * 100).toFixed(1)}%)
  Secrets Detected: ${report.secretsDetected}
  Blocked: ${report.blocked}
  Risk Levels:
    Critical: ${report.byRiskLevel.critical}
    High: ${report.byRiskLevel.high}
    Medium: ${report.byRiskLevel.medium}
    Low: ${report.byRiskLevel.low}
    None: ${report.byRiskLevel.none}
`);
```

---

## Best Practices

### 1. Always Sanitize User Input

**Why**: Prevents PII leakage to LLMs and logs
**How**: Check all user input before processing

```python
user_input = get_user_input()
result = await guardian.check({"text": user_input, "check_types": ["all"], "redact_pii": True})
safe_input = result.sanitized_text
```

---

### 2. Validate Output Before Returning to Users

**Why**: LLMs may inadvertently generate or repeat PII
**How**: Check all LLM output before returning

```typescript
const llmOutput = await generateResponse(prompt);
const result = await guardian.check({text: llmOutput, checkTypes: ['pii', 'secrets'], redactPii: true});
return result.sanitized_text;
```

---

### 3. Handle Different Risk Levels Appropriately

**Why**: Not all risks require blocking
**How**: Use risk levels for decision-making

```python
if result.risk_level in ["none", "low", "medium"]:
    process_normally(result.sanitized_text)
elif result.risk_level == "high":
    require_manual_review(result)
else:  # critical
    block_immediately(result)
```

---

### 4. Log Safety Issues for Compliance

**Why**: Demonstrates PII protection for audits
**How**: Log all detected issues

```typescript
if (result.issues.length > 0) {
  logger.info('Safety issues detected', {
    riskLevel: result.risk_level,
    issueCount: result.issues.length,
    issueTypes: result.issues.map(i => i.type)
  });
}
```

---

## Related Documentation

- [Safety Guardian Arm API Reference](../services/safety-guardian.md)
- [TaskContract Schema](./TaskContract.md)
- [PII Protection Guide](../../guides/pii-protection.md) (coming soon)
- [Compliance Best Practices](../../guides/compliance.md) (coming soon)

---

## JSON Schema

Complete JSON Schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PIIDetection",
  "type": "object",
  "required": ["safe", "risk_level", "issues", "sanitized_text", "blocked"],
  "properties": {
    "safe": {
      "type": "boolean",
      "description": "Whether content is safe (no high/critical risks)"
    },
    "risk_level": {
      "type": "string",
      "enum": ["none", "low", "medium", "high", "critical"],
      "description": "Highest risk level detected"
    },
    "issues": {
      "type": "array",
      "items": {"$ref": "#/definitions/SafetyIssue"},
      "description": "List of detected issues"
    },
    "sanitized_text": {
      "type": "string",
      "description": "Text with PII/secrets redacted"
    },
    "blocked": {
      "type": "boolean",
      "description": "Whether request was blocked"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "checks_performed": {
          "type": "array",
          "items": {"type": "string"}
        },
        "pii_types_found": {
          "type": "array",
          "items": {"type": "string"}
        },
        "secret_types_found": {
          "type": "array",
          "items": {"type": "string"}
        },
        "processing_time_ms": {"type": "number"},
        "block_reason": {"type": "string"}
      }
    }
  },
  "definitions": {
    "SafetyIssue": {
      "type": "object",
      "required": ["type", "risk_level", "message", "matched_pattern", "position"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["pii", "secret", "malicious_content", "inappropriate_content", "policy_violation"],
          "description": "Issue type"
        },
        "risk_level": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"],
          "description": "Risk level for this issue"
        },
        "message": {
          "type": "string",
          "minLength": 10,
          "maxLength": 200,
          "description": "Human-readable description"
        },
        "matched_pattern": {
          "type": "string",
          "description": "Pattern that matched"
        },
        "position": {
          "type": "integer",
          "minimum": 0,
          "description": "Character position in text"
        },
        "redaction": {
          "type": "string",
          "description": "Replacement text for redaction"
        }
      }
    }
  }
}
```
