# Judge Arm API Reference

**Service**: Judge Arm (Output Validation & Quality Assurance)
**Port**: 8006
**Base URL**: `http://localhost:8006` (development), `http://judge:8006` (internal)
**Technology**: Python 3.11+ / FastAPI
**Cost Tier**: 2 (Medium - uses GPT-3.5-turbo)
**Average Latency**: 0.5-2 seconds

## Overview

The Judge Arm is the quality gatekeeper of OctoLLM. It validates outputs through multi-layer checks including schema validation, fact-checking, acceptance criteria evaluation, hallucination detection, and quality assessment. Think of it as the quality control inspector ensuring every output meets standards before delivery.

### Capabilities

- **Schema Validation**: Verify structure and data types match expected format
- **Fact-Checking**: Cross-reference claims against trusted sources
- **Criteria Evaluation**: Check outputs meet acceptance criteria
- **Hallucination Detection**: Identify unsupported or fabricated claims
- **Quality Assessment**: Overall quality scoring (0.0-1.0)

### Key Features

- **Multi-Layer Validation**: Run 1-5 validation types in single request
- **Issue Classification**: Errors, warnings, and info suggestions with severity levels
- **Confidence Scoring**: Returns confidence level (0.0-1.0) for validation result
- **Actionable Suggestions**: Provides fix recommendations for each issue
- **Fast Iteration**: GPT-3.5-turbo enables sub-2s validation
- **Cost-Effective**: Medium-tier LLM usage for high-volume validation

---

## Authentication

All Judge endpoints require Bearer token authentication (inter-service communication):

```bash
curl http://judge:8006/validate \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "output": {
      "code": "def sort_list(lst): return sorted(lst)",
      "tests": "assert sort_list([3,1,2]) == [1,2,3]"
    },
    "validation_types": ["schema", "criteria", "quality"],
    "acceptance_criteria": [
      "Code implements sorting functionality",
      "Tests are included"
    ]
  }'
```

**Note**: The Judge is typically called by the Orchestrator after arm execution, not directly by external clients. External clients should use the [Orchestrator API](./orchestrator.md).

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details on capability-based tokens.

---

## Endpoints

### POST /validate

Validate output using one or more validation types (schema, facts, criteria, hallucination, quality).

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "output": {
    "code": "def sort_list(lst): return sorted(lst)",
    "tests": "assert sort_list([3,1,2]) == [1,2,3]"
  },
  "validation_types": [
    "schema",
    "criteria",
    "quality"
  ],
  "acceptance_criteria": [
    "Code implements sorting functionality",
    "Tests are included",
    "Function has proper naming"
  ],
  "expected_schema": {
    "type": "object",
    "required": ["code", "tests"],
    "properties": {
      "code": {"type": "string"},
      "tests": {"type": "string"}
    }
  }
}
```

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `output` | any | ✅ | - | Output to validate (object, string, array, etc.) |
| `validation_types` | array | ✅ | One or more: `schema`, `facts`, `criteria`, `quality`, `hallucination` | Types of validation to perform |
| `acceptance_criteria` | array | ❌ | - | Criteria that must be met (required for `criteria` validation) |
| `expected_schema` | object | ❌ | JSON Schema format | Expected structure (required for `schema` validation) |
| `trusted_sources` | array | ❌ | URLs | Trusted sources for fact-checking (required for `facts` validation) |
| `context` | object | ❌ | - | Context for hallucination detection |

#### Response

**Status**: 200 OK

```json
{
  "valid": true,
  "confidence": 0.92,
  "issues": [
    {
      "severity": "info",
      "type": "style_suggestion",
      "message": "Consider adding docstring to function",
      "location": "function:sort_list",
      "suggestion": "Add docstring explaining parameters and return value"
    }
  ],
  "passed_criteria": [
    "Code implements sorting functionality",
    "Tests are included",
    "Function has proper naming"
  ],
  "failed_criteria": [],
  "quality_score": 0.85,
  "metadata": {
    "validation_types_run": ["schema", "criteria", "quality"],
    "total_issues": 1,
    "error_count": 0,
    "warning_count": 0,
    "info_count": 1,
    "duration_ms": 1250
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | Whether output is valid (no errors, warnings OK) |
| `confidence` | number | Confidence in validation result (0.0-1.0) |
| `issues` | array | List of issues found (errors, warnings, info) |
| `issues[].severity` | string | `error`, `warning`, or `info` |
| `issues[].type` | string | Issue type (e.g., `schema_violation`, `criteria_not_met`) |
| `issues[].message` | string | Human-readable issue description |
| `issues[].location` | string | Where the issue was found |
| `issues[].suggestion` | string | How to fix the issue |
| `passed_criteria` | array | Acceptance criteria that passed |
| `failed_criteria` | array | Acceptance criteria that failed |
| `quality_score` | number | Overall quality score (0.0-1.0) |
| `metadata` | object | Additional info (validation types run, issue counts, duration) |

#### Examples

**Example 1: Schema + Criteria Validation (Bash)**

```bash
curl -X POST http://judge:8006/validate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "output": {
      "code": "def sort_list(lst): return sorted(lst)",
      "tests": "assert sort_list([3,1,2]) == [1,2,3]"
    },
    "validation_types": ["schema", "criteria", "quality"],
    "acceptance_criteria": [
      "Code implements sorting functionality",
      "Tests are included",
      "Function has proper naming"
    ],
    "expected_schema": {
      "type": "object",
      "required": ["code", "tests"],
      "properties": {
        "code": {"type": "string"},
        "tests": {"type": "string"}
      }
    }
  }'

# Response:
{
  "valid": true,
  "confidence": 0.92,
  "issues": [
    {
      "severity": "info",
      "type": "style_suggestion",
      "message": "Consider adding docstring to function",
      "location": "function:sort_list",
      "suggestion": "Add docstring explaining parameters and return value"
    }
  ],
  "passed_criteria": [
    "Code implements sorting functionality",
    "Tests are included",
    "Function has proper naming"
  ],
  "failed_criteria": [],
  "quality_score": 0.85,
  "metadata": {
    "validation_types_run": ["schema", "criteria", "quality"],
    "total_issues": 1,
    "error_count": 0,
    "warning_count": 0,
    "info_count": 1
  }
}
```

**Example 2: Failed Validation (Python SDK)**

```python
from octollm_sdk import JudgeClient

client = JudgeClient(bearer_token="service_token_abc123")

result = await client.validate({
    "output": {
        "code": "def sort_list(lst): return sorted(lst)"
        # Missing "tests" field
    },
    "validation_types": ["schema", "criteria"],
    "acceptance_criteria": [
        "Code implements sorting functionality",
        "Tests are included"
    ],
    "expected_schema": {
        "type": "object",
        "required": ["code", "tests"],
        "properties": {
            "code": {"type": "string"},
            "tests": {"type": "string"}
        }
    }
})

print(f"Valid: {result.valid}")
print(f"Confidence: {result.confidence:.2f}")

print("\n=== ISSUES ===")
for issue in result.issues:
    print(f"[{issue.severity.upper()}] {issue.message}")
    print(f"  Location: {issue.location}")
    print(f"  Suggestion: {issue.suggestion}\n")

print(f"Passed Criteria: {result.passed_criteria}")
print(f"Failed Criteria: {result.failed_criteria}")

# Output:
# Valid: False
# Confidence: 0.45
#
# === ISSUES ===
# [ERROR] Missing required field 'tests'
#   Location: root
#   Suggestion: Add 'tests' field to output
#
# [ERROR] Acceptance criterion not met: Tests are included
#   Location: N/A
#   Suggestion: Review output and ensure tests are included
#
# Passed Criteria: ['Code implements sorting functionality']
# Failed Criteria: ['Tests are included']
```

**Example 3: Hallucination Detection (TypeScript SDK)**

```typescript
import { JudgeClient } from 'octollm-sdk';

const client = new JudgeClient({
  bearerToken: process.env.SERVICE_TOKEN
});

const result = await client.validate({
  output: {
    summary: "Nginx CVE-2024-12345 has a CVSS score of 9.8 and affects all versions prior to 1.24.0. The vulnerability was discovered by Alice Smith in March 2024.",
    sources: [
      "https://nvd.nist.gov/vuln/detail/CVE-2024-12345"
    ]
  },
  validationTypes: ['facts', 'hallucination'],
  trustedSources: [
    "https://nvd.nist.gov/vuln/detail/CVE-2024-12345"
  ],
  context: {
    // Retrieved context from sources
    facts: [
      "CVE-2024-12345 CVSS score is 7.5",
      "Affects versions prior to 1.24.1",
      "Discovered in February 2024"
    ]
  }
});

console.log(`Valid: ${result.valid}`);
console.log(`Confidence: ${result.confidence.toFixed(2)}`);

// Check for hallucinations
const hallucinations = result.issues.filter(i => i.type === 'hallucination');
if (hallucinations.length > 0) {
  console.log('\n⚠️ HALLUCINATIONS DETECTED:');
  hallucinations.forEach(h => {
    console.log(`  - ${h.message}`);
  });
}

// Output:
// Valid: false
// Confidence: 0.65
//
// ⚠️ HALLUCINATIONS DETECTED:
//   - CVSS score stated as 9.8 but actual score is 7.5
//   - Affected versions claim "prior to 1.24.0" but actually "prior to 1.24.1"
//   - Discovery date stated as March but actual date is February
//   - Discoverer "Alice Smith" not found in sources
```

**Example 4: Quality Assessment (Python SDK)**

```python
from octollm_sdk import JudgeClient

client = JudgeClient(bearer_token="service_token_abc123")

code_output = {
    "code": """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)
""",
    "tests": """
def test_calculate_average():
    assert calculate_average([1, 2, 3]) == 2.0
"""
}

result = await client.validate({
    "output": code_output,
    "validation_types": ["quality"],
    "context": {
        "language": "python",
        "type": "function"
    }
})

print(f"Quality Score: {result.quality_score:.2f}")
print(f"\n=== ISSUES ===")
for issue in result.issues:
    if issue.severity == "error":
        print(f"❌ {issue.message}")
    elif issue.severity == "warning":
        print(f"⚠️ {issue.message}")
    else:
        print(f"ℹ️ {issue.message}")

# Output:
# Quality Score: 0.65
#
# === ISSUES ===
# ❌ Division by zero error if numbers list is empty
# ⚠️ No type hints on function parameters
# ⚠️ Missing docstring
# ℹ️ Consider using built-in sum() function
# ℹ️ Test coverage incomplete (missing edge cases)
```

**Example 5: Fact-Checking with Sources (Bash)**

```bash
curl -X POST http://judge:8006/validate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "output": {
      "claim": "SQL injection is ranked #1 in OWASP Top 10 2021",
      "supporting_text": "According to OWASP, SQL injection vulnerabilities remain the most critical web application security risk."
    },
    "validation_types": ["facts"],
    "trusted_sources": [
      "https://owasp.org/www-project-top-ten/"
    ],
    "context": {
      "topic": "web_security",
      "source_date": "2021"
    }
  }'

# Response:
{
  "valid": false,
  "confidence": 0.85,
  "issues": [
    {
      "severity": "error",
      "type": "factual_error",
      "message": "SQL injection is ranked #3 in OWASP Top 10 2021, not #1",
      "location": "claim",
      "suggestion": "Update ranking to #3 (Injection) or verify against official OWASP Top 10 2021"
    }
  ],
  "passed_criteria": [],
  "failed_criteria": [],
  "quality_score": 0.70,
  "metadata": {
    "validation_types_run": ["facts"],
    "sources_checked": 1,
    "claims_verified": 1,
    "claims_correct": 0
  }
}
```

#### Error Responses

**400 Bad Request** (invalid request):

```json
{
  "error": "ValidationError",
  "message": "expected_schema required when validation_types includes 'schema'",
  "details": {
    "validation_types": ["schema"],
    "missing_field": "expected_schema"
  }
}
```

**401 Unauthorized** (missing or invalid token):

```json
{
  "error": "Unauthorized",
  "message": "Bearer token required for validation operations"
}
```

---

### GET /capabilities

Retrieve judge capabilities and supported validation types.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "capabilities": [
    "schema_validation",
    "fact_checking",
    "criteria_evaluation",
    "hallucination_detection",
    "quality_assessment"
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
# HELP judge_validations_total Total number of validations
# TYPE judge_validations_total counter
judge_validations_total{validation_type="schema",result="valid"} 8234
judge_validations_total{validation_type="criteria",result="valid"} 7421
judge_validations_total{validation_type="quality",result="invalid"} 1892

# HELP judge_avg_quality_score Average quality score
# TYPE judge_avg_quality_score gauge
judge_avg_quality_score 0.82

# HELP judge_issues_by_severity Issues by severity
# TYPE judge_issues_by_severity counter
judge_issues_by_severity{severity="error"} 523
judge_issues_by_severity{severity="warning"} 1892
judge_issues_by_severity{severity="info"} 3421
```

---

## Data Models

### ValidationRequest

```typescript
type ValidationType = 'schema' | 'facts' | 'criteria' | 'quality' | 'hallucination';

interface ValidationRequest {
  output: any;                      // Any type (object, string, array, etc.)
  validation_types: ValidationType[];
  acceptance_criteria?: string[];   // Required for 'criteria' validation
  expected_schema?: object;         // JSON Schema, required for 'schema' validation
  trusted_sources?: string[];       // URLs, required for 'facts' validation
  context?: {
    [key: string]: any;
  };
}
```

### ValidationResult

```typescript
interface ValidationResult {
  valid: boolean;                   // No errors (warnings/info OK)
  confidence: number;               // 0.0-1.0
  issues: ValidationIssue[];
  passed_criteria: string[];
  failed_criteria: string[];
  quality_score: number;            // 0.0-1.0
  metadata: {
    validation_types_run: string[];
    total_issues: number;
    error_count: number;
    warning_count: number;
    info_count: number;
    duration_ms?: number;
    [key: string]: any;
  };
}
```

### ValidationIssue

```typescript
type IssueSeverity = 'error' | 'warning' | 'info';

interface ValidationIssue {
  severity: IssueSeverity;
  type: string;                     // e.g., "schema_violation", "hallucination"
  message: string;                  // Human-readable description
  location: string;                 // Where the issue was found
  suggestion: string;               // How to fix it
}
```

---

## Integration Patterns

### Pattern 1: Validation-Driven Retry Loop

Retry arm execution until output passes validation.

```python
from octollm_sdk import CoderClient, JudgeClient

coder = CoderClient(bearer_token="service_token_abc123")
judge = JudgeClient(bearer_token="service_token_abc123")

async def generate_until_valid(instruction: str, criteria: list, max_attempts: int = 3):
    for attempt in range(max_attempts):
        # Generate code
        code_response = await coder.process_code({
            "request_type": "generate",
            "language": "python",
            "instruction": instruction
        })

        # Validate
        validation = await judge.validate({
            "output": {"code": code_response.code},
            "validation_types": ["criteria", "quality"],
            "acceptance_criteria": criteria
        })

        if validation.valid and validation.quality_score >= 0.80:
            print(f"✓ Valid output (quality: {validation.quality_score:.2f})")
            return code_response.code

        print(f"Attempt {attempt + 1}: {len(validation.issues)} issues")
        # Retry with feedback
        instruction += f"\\n\\nPrevious attempt failed with: {validation.issues[0].message}"

    raise ValueError("Could not generate valid output after 3 attempts")
```

### Pattern 2: Progressive Validation (Fail Fast)

Run cheaper validations first, expensive ones only if needed.

```typescript
import { JudgeClient } from 'octollm-sdk';

const client = new JudgeClient({ bearerToken: '...' });

async function progressiveValidation(
  output: any,
  criteria: string[]
): Promise<ValidationResult> {
  // Stage 1: Schema validation (fast, no LLM)
  const schemaResult = await client.validate({
    output,
    validationTypes: ['schema'],
    expectedSchema: {
      type: 'object',
      required: ['code', 'tests']
    }
  });

  if (!schemaResult.valid) {
    console.log('Failed schema validation, skipping expensive checks');
    return schemaResult;
  }

  // Stage 2: Criteria evaluation (medium cost)
  const criteriaResult = await client.validate({
    output,
    validationTypes: ['criteria'],
    acceptanceCriteria: criteria
  });

  if (!criteriaResult.valid) {
    console.log('Failed criteria check');
    return criteriaResult;
  }

  // Stage 3: Quality assessment (expensive)
  const qualityResult = await client.validate({
    output,
    validationTypes: ['quality']
  });

  return qualityResult;
}
```

### Pattern 3: Aggregated Multi-Output Validation

Validate multiple outputs in parallel, aggregate results.

```python
from octollm_sdk import JudgeClient
import asyncio

client = JudgeClient(bearer_token="service_token_abc123")

async def batch_validate(outputs: list[dict], criteria: list):
    validation_tasks = [
        client.validate({
            "output": output,
            "validation_types": ["criteria", "quality"],
            "acceptance_criteria": criteria
        })
        for output in outputs
    ]

    results = await asyncio.gather(*validation_tasks)

    # Aggregate statistics
    valid_count = sum(1 for r in results if r.valid)
    avg_quality = sum(r.quality_score for r in results) / len(results)
    total_issues = sum(len(r.issues) for r in results)

    print(f"Valid: {valid_count}/{len(outputs)}")
    print(f"Avg Quality: {avg_quality:.2f}")
    print(f"Total Issues: {total_issues}")

    return results
```

---

## Performance Characteristics

| Validation Type | P50 | P95 | P99 | Max | Notes |
|-----------------|-----|-----|-----|-----|-------|
| Schema | 50ms | 100ms | 150ms | 300ms | No LLM (jsonschema) |
| Criteria | 800ms | 1.5s | 2s | 4s | GPT-3.5-turbo |
| Facts | 1s | 2s | 3s | 6s | Retrieval + LLM |
| Hallucination | 900ms | 1.8s | 2.5s | 5s | GPT-3.5-turbo |
| Quality | 1.2s | 2.2s | 3s | 6s | Detailed analysis |

### Cost by Validation Type

| Validation Type | Avg Tokens | Cost (GPT-3.5) | Notes |
|-----------------|------------|----------------|-------|
| Schema | 0 | $0.000 | No LLM calls |
| Criteria | ~400 | $0.0004 | Simple evaluation |
| Facts | ~600 | $0.0006 | + retrieval cost |
| Hallucination | ~500 | $0.0005 | Context comparison |
| Quality | ~800 | $0.0008 | Comprehensive analysis |

---

## Troubleshooting

### Issue 1: Low Confidence Validation (<0.70)

**Symptoms**: Validation returns confidence <0.70, results unreliable

**Possible Causes**:
- Ambiguous acceptance criteria
- Missing trusted sources for fact-checking
- Insufficient context for hallucination detection

**Solutions**:
```python
# Make criteria more specific
# Bad: "Code is good"
# Good: "Code implements bubble sort algorithm with O(n²) complexity, includes error handling for empty arrays, and has comprehensive docstring"

# Provide sufficient context
validation = await judge.validate({
    "output": output,
    "validation_types": ["hallucination"],
    "context": {
        "source_documents": [...],  # Actual retrieved documents
        "original_query": "...",
        "topic": "web_security"
    }
})
```

### Issue 2: False Positives (Valid Output Marked Invalid)

**Symptoms**: Judge incorrectly marks valid output as invalid

**Possible Causes**:
- Over-strict acceptance criteria
- Schema too rigid
- Fact-checking against outdated sources

**Solutions**:
```python
# Loosen criteria or schema
# Remove overly specific requirements

# Check trusted sources are current
# Update source URLs to latest versions

# Review validation issues
for issue in result.issues:
    if issue.severity == "error":
        print(f"Review: {issue.message}")
        # Manually verify if this is truly an error
```

### Issue 3: Missed Hallucinations

**Symptoms**: Judge doesn't detect known hallucinations

**Possible Causes**:
- Missing context for comparison
- Trusted sources incomplete
- Hallucination too subtle

**Solutions**:
```python
# Provide comprehensive context
validation = await judge.validate({
    "output": output,
    "validation_types": ["hallucination", "facts"],
    "trusted_sources": [
        "https://source1.com",
        "https://source2.com",
        "https://source3.com"  # Multiple sources
    ],
    "context": {
        "retrieved_documents": [...],  # ALL source documents
        "ground_truth_facts": [...]    # Known facts
    }
})
```

### Issue 4: High Latency (>5s)

**Symptoms**: Validation taking >5 seconds

**Possible Causes**:
- Running all validation types simultaneously
- Large output being validated
- Fact-checking with many sources

**Solutions**:
```bash
# Use progressive validation (see Integration Patterns)
# Run cheap validations first, expensive ones only if needed

# Reduce validation scope
# Don't validate entire codebase, only changed parts

# Scale horizontally
kubectl scale deployment judge --replicas=10

# Monitor latency
curl http://judge:8006/metrics | grep judge_validation_latency
```

### Issue 5: Schema Validation Too Strict

**Symptoms**: Outputs fail schema validation for minor differences

**Possible Causes**:
- Schema requires exact structure
- No support for optional fields
- additionalProperties set to false

**Solutions**:
```python
# Use flexible schema
flexible_schema = {
    "type": "object",
    "required": ["code"],  # Only truly required fields
    "properties": {
        "code": {"type": "string"},
        "tests": {"type": "string"}  # Optional (not in required)
    },
    "additionalProperties": True  # Allow extra fields
}

validation = await judge.validate({
    "output": output,
    "validation_types": ["schema"],
    "expected_schema": flexible_schema
})
```

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Orchestrator API](./orchestrator.md)
- [Coder Arm API](./coder.md)
- [Safety Guardian API](./safety-guardian.md)
- [OpenAPI Specification](../openapi/judge.yaml)

---

## Support

For issues with the Judge Arm:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `kubectl logs -l app=judge`
3. Check metrics: `curl http://judge:8006/metrics`
4. File issue: https://github.com/octollm/octollm/issues
